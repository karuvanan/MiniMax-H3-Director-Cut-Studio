"""One-job JSON service for Kim_Vocal_2 vocal separation.

This process intentionally exits after one request.  ONNX Runtime, its model,
RAM and any provider allocations therefore cannot remain resident while H3 is
subsequently rendered.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import traceback
import types


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def configure_runtime(runtime: Path, studio_site_packages: Path) -> None:
    if not runtime.is_dir():
        raise FileNotFoundError(f"audio-separator runtime missing: {runtime}")
    # The service is launched with -S.  Put the isolated NumPy/ONNX packages
    # first, then reuse the Studio's Torch/librosa/soundfile dependencies.
    sys.path.insert(0, str(runtime))
    if studio_site_packages.is_dir():
        sys.path.append(str(studio_site_packages))
    dll_dirs = (
        runtime / "onnxruntime" / "capi",
        runtime / "numpy.libs",
    )
    os.environ["PATH"] = os.pathsep.join(
        [str(path) for path in dll_dirs if path.is_dir()] + [os.environ.get("PATH", "")]
    )
    if hasattr(os, "add_dll_directory"):
        for path in dll_dirs:
            if path.is_dir():
                os.add_dll_directory(str(path))


def validate_cuda_provider(model: Path) -> dict:
    """Prove that this runtime can create a real Kim CUDA session."""

    if not model.is_file():
        raise FileNotFoundError(f"Kim_Vocal_2 model missing: {model}")
    # ONNX Runtime officially supports reusing PyTorch's CUDA/cuDNN DLLs.
    # Importing Torch first makes those DLLs visible before ORT creates a
    # CUDAExecutionProvider session.
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("PyTorch CUDA is unavailable on this computer")
    import onnxruntime as ort
    if hasattr(ort, "preload_dlls"):
        ort.preload_dlls()
    providers = list(ort.get_available_providers())
    if "CUDAExecutionProvider" not in providers:
        raise RuntimeError(
            "onnxruntime-gpu is not active; CUDAExecutionProvider is missing: "
            + ", ".join(providers)
        )
    options = ort.SessionOptions()
    options.log_severity_level = 3
    session = ort.InferenceSession(
        str(model),
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        sess_options=options,
    )
    active = list(session.get_providers())
    if not active or active[0] != "CUDAExecutionProvider":
        raise RuntimeError(
            "Kim_Vocal_2 did not activate CUDAExecutionProvider: " + ", ".join(active)
        )
    del session
    torch.cuda.empty_cache()
    return {
        "cuda_provider": True,
        "provider": "CUDAExecutionProvider",
        "onnxruntime": str(ort.__version__),
        "torch": str(torch.__version__),
        "torch_cuda": str(torch.version.cuda or ""),
        "gpu": str(torch.cuda.get_device_name(0)),
    }


def prepare_soundfile_samples(stem_source):
    """Return an explicit samples-by-channels float array for libsndfile."""

    import numpy as np

    samples = np.asarray(stem_source)
    if samples.ndim == 1:
        pass
    elif samples.ndim == 2:
        if samples.shape[0] in {1, 2} and samples.shape[1] > samples.shape[0]:
            samples = samples.T
        elif samples.shape[1] not in {1, 2}:
            raise RuntimeError(
                f"Unexpected separated-audio shape {samples.shape}; expected samples x channels"
            )
    else:
        raise RuntimeError(f"Unexpected separated-audio rank {samples.ndim}")
    return np.nan_to_num(samples.astype(np.float32, copy=False))


def install_safe_soundfile_writer() -> None:
    """Replace audio-separator 0.30's lossy stereo interleave path.

    Upstream's SoundFile branch casts a C-contiguous float stereo array to
    int16 *before* scaling and flattens it into one channel.  Typical samples
    in [-1, 1] consequently become zeros, while the apparent duration doubles.
    Keep channel/sample axes explicit and let libsndfile perform PCM scaling.
    """

    import soundfile as sf
    from audio_separator.separator.common_separator import CommonSeparator

    def write_audio_soundfile(separator, stem_path: str, stem_source) -> None:
        samples = prepare_soundfile_samples(stem_source)
        target = Path(stem_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(target), samples, int(separator.sample_rate), subtype="PCM_16")

    CommonSeparator.write_audio_soundfile = write_audio_soundfile


def audio_metrics(path: Path) -> dict:
    """Measure a rendered stem so silent/corrupt files cannot pass unnoticed."""

    import math
    import numpy as np
    import soundfile as sf

    sample_sum = 0.0
    sample_count = 0
    peak = 0.0
    with sf.SoundFile(str(path)) as audio:
        frames = int(audio.frames)
        sample_rate = int(audio.samplerate)
        channels = int(audio.channels)
        for block in audio.blocks(blocksize=262144, dtype="float32", always_2d=True):
            values = np.asarray(block, dtype=np.float64)
            if values.size:
                sample_sum += float(np.square(values).sum())
                sample_count += int(values.size)
                peak = max(peak, float(np.max(np.abs(values))))
    rms = math.sqrt(sample_sum / sample_count) if sample_count else 0.0
    return {
        "duration_seconds": round(frames / sample_rate, 4) if sample_rate else 0.0,
        "sample_rate": sample_rate,
        "channels": channels,
        "rms_dbfs": round(20.0 * math.log10(max(rms, 1e-6)), 2),
        "peak_dbfs": round(20.0 * math.log10(max(peak, 1e-6)), 2),
        "near_silent": peak < 1e-4,
    }


def _move_stem(candidate: Path | None, destination: Path, label: str) -> Path:
    if candidate is None or not candidate.is_file():
        raise RuntimeError(f"Kim_Vocal_2 completed without a readable {label} stem")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if candidate.resolve() != destination.resolve():
        destination.unlink(missing_ok=True)
        shutil.move(str(candidate), str(destination))
    if not destination.is_file() or destination.stat().st_size < 1024:
        raise RuntimeError(f"Kim_Vocal_2 produced an empty {label} stem")
    return destination


def separate_vocals(request: dict, args: argparse.Namespace) -> dict:
    source = Path(str(request.get("source_audio", ""))).resolve()
    vocal_destination = Path(
        str(request.get("vocal_destination") or request.get("destination") or "")
    ).resolve()
    music_destination = Path(
        str(request.get("music_destination") or vocal_destination.with_name("music.wav"))
    ).resolve()
    mix_destination_value = str(request.get("mix_destination") or "").strip()
    mix_destination = Path(mix_destination_value).resolve() if mix_destination_value else None
    model = Path(str(request.get("model", args.model))).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"A1 source audio missing: {source}")
    if not model.is_file():
        raise FileNotFoundError(f"Kim_Vocal_2 model missing: {model}")
    vocal_destination.parent.mkdir(parents=True, exist_ok=True)
    vocal_working = vocal_destination.with_name(vocal_destination.stem + ".working.wav")
    music_working = music_destination.with_name(music_destination.stem + ".working.wav")
    vocal_working.unlink(missing_ok=True)
    music_working.unlink(missing_ok=True)

    emit({"job": request.get("job"), "progress": 0.08, "stage": "loading Kim_Vocal_2"})
    cuda = validate_cuda_provider(model)
    emit({
        "job": request.get("job"),
        "progress": 0.14,
        "stage": f"CUDA ready · {cuda['gpu']} · ONNX Runtime {cuda['onnxruntime']}",
    })
    # audio-separator 0.30 imports onnx2torch (and therefore torchvision) even
    # when the MDX model runs directly through ONNX Runtime. Kim_Vocal_2 uses
    # its native 256-frame shape, so conversion is never needed. Avoid pulling
    # an unrelated multi-gigabyte torchvision stack into this isolated CUDA
    # worker; fail explicitly if a future model unexpectedly requests it.
    onnx2torch_stub = types.ModuleType("onnx2torch")
    def _unsupported_conversion(*_args, **_kwargs):
        raise RuntimeError("This isolated Kim_Vocal_2 runtime requires native ONNX execution")
    onnx2torch_stub.convert = _unsupported_conversion
    sys.modules["onnx2torch"] = onnx2torch_stub
    from audio_separator.separator import Separator
    install_safe_soundfile_writer()

    separator = Separator(
        log_level=logging.WARNING,
        model_file_dir=str(model.parent),
        output_dir=str(vocal_destination.parent),
        output_format="WAV",
        output_single_stem=None,
        normalization_threshold=0.9,
        use_soundfile=True,
        mdx_params={
            "hop_length": 1024,
            "segment_size": 256,
            "overlap": 0.25,
            "batch_size": 1,
            "enable_denoise": False,
        },
    )
    separator.load_model(model_filename=model.name)
    emit({"job": request.get("job"), "progress": 0.25, "stage": "separating vocal and music stems"})
    outputs = separator.separate(
        str(source),
        custom_output_names={
            "Vocals": str(vocal_working.with_suffix("")),
            "Instrumental": str(music_working.with_suffix("")),
        },
    )
    candidates = [Path(value) for value in outputs or []]
    vocal_candidate = vocal_working if vocal_working.is_file() else next(
        (path for path in candidates if path.is_file() and "vocal" in path.name.casefold()),
        None,
    )
    music_candidate = music_working if music_working.is_file() else next(
        (
            path for path in candidates
            if path.is_file()
            and any(token in path.name.casefold() for token in ("instrument", "music"))
        ),
        None,
    )
    vocal_path = _move_stem(vocal_candidate, vocal_destination, "vocal")
    music_path = _move_stem(music_candidate, music_destination, "music")
    vocal_metrics = audio_metrics(vocal_path)
    music_metrics = audio_metrics(music_path)
    duration_tolerance = max(
        0.25,
        0.02 * max(
            vocal_metrics["duration_seconds"],
            music_metrics["duration_seconds"],
        ),
    )
    if abs(
        vocal_metrics["duration_seconds"] - music_metrics["duration_seconds"]
    ) > duration_tolerance:
        raise RuntimeError(
            "Separated stems have mismatched durations: "
            f"Vocal {vocal_metrics['duration_seconds']:.2f}s, "
            f"Music {music_metrics['duration_seconds']:.2f}s"
        )
    if vocal_metrics["channels"] != music_metrics["channels"]:
        raise RuntimeError(
            "Separated stems have mismatched channel layouts: "
            f"Vocal {vocal_metrics['channels']}ch, Music {music_metrics['channels']}ch"
        )
    if mix_destination is not None:
        mix_destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != mix_destination.resolve():
            shutil.copy2(source, mix_destination)
    return {
        "vocal_path": str(vocal_path),
        "music_path": str(music_path),
        "mix_path": str(mix_destination) if mix_destination else str(source),
        "provider": "CUDAExecutionProvider",
        "gpu": cuda["gpu"],
        "onnxruntime": cuda["onnxruntime"],
        "metrics": {
            "vocal": vocal_metrics,
            "music": music_metrics,
        },
        "warnings": (
            ["Vocal stem is near-silent; confirm that the source contains singing"]
            if vocal_metrics["near_silent"]
            else []
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--studio-site-packages", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    configure_runtime(Path(args.runtime).resolve(), Path(args.studio_site_packages).resolve())
    if args.probe:
        try:
            emit({"ready": True, **validate_cuda_provider(Path(args.model).resolve())})
        except Exception as exc:
            emit({"ready": False, "cuda_provider": False, "error": str(exc)})
            raise SystemExit(2) from exc
        return
    emit({"ready": True, "service": "vocal-separator", "one_shot": True})
    line = sys.stdin.readline()
    if not line:
        return
    request: dict = {}
    try:
        request = json.loads(line)
        result = separate_vocals(request, args)
        emit({"job": request.get("job"), "progress": 1.0, "result": result})
    except Exception as exc:
        emit({
            "job": request.get("job"),
            "error": str(exc),
            "traceback": traceback.format_exc(limit=8),
        })


if __name__ == "__main__":
    main()

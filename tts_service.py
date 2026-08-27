"""Crash-isolated Windows Mandarin TTS and exact Timeline WAV compositor."""

from __future__ import annotations

import argparse
import asyncio
import gc
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import subprocess
import uuid
import wave

from voxcpm_runtime import (
    VOXCPM_MODEL_DIR,
    voxcpm_missing_message,
    voxcpm_model_missing,
)


TTS_ENGINE_LABELS = {
    "edge_tts": "Edge neural Mandarin TTS with Windows SAPI fallback",
    "voxcpm2_local": "VoxCPM2 Local offline neural TTS",
}


def normalize_tts_engine(value: object) -> str:
    engine = str(value or "edge_tts").strip().lower()
    if engine not in TTS_ENGINE_LABELS:
        raise ValueError(
            f"Unsupported Dialogue Text Layer TTS engine: {engine or '<empty>'}"
        )
    return engine


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as source:
        rate = source.getframerate()
        return source.getnframes() / rate if rate else 0.0


def atempo_filters(speed: float) -> list[str]:
    """Split an arbitrary speed into FFmpeg's supported 0.5..2.0 factors."""
    speed = max(0.01, float(speed))
    values: list[float] = []
    while speed > 2.0 + 1e-9:
        values.append(2.0)
        speed /= 2.0
    while speed < 0.5 - 1e-9:
        values.append(0.5)
        speed /= 0.5
    if abs(speed - 1.0) > 1e-6 or not values:
        values.append(speed)
    return [f"atempo={value:.6f}" for value in values if abs(value - 1.0) > 1e-6]


def _powershell() -> str:
    return shutil.which("powershell.exe") or shutil.which("powershell") or ""


def synthesize_line(
    *,
    text: str,
    language: str,
    output: Path,
    script: Path,
    ffmpeg: Path,
    speaker: str = "S1",
) -> None:
    edge_error = ""
    try:
        import edge_tts

        encoded = output.with_suffix(".mp3")
        voice_name = (
            "zh-CN-YunxiNeural"
            if str(speaker).upper() == "S2"
            else "zh-CN-XiaoxiaoNeural"
        )
        asyncio.run(edge_tts.Communicate(text, voice_name).save(str(encoded)))
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        converted = subprocess.run(
            [
                str(ffmpeg), "-y", "-i", str(encoded),
                "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(output),
            ],
            capture_output=True,
            creationflags=creation_flags,
            timeout=180,
        )
        if converted.returncode or not output.is_file() or output.stat().st_size <= 44:
            detail = converted.stderr.decode("utf-8", errors="replace")[-1000:]
            raise RuntimeError(f"Edge TTS conversion failed: {detail}")
        return
    except Exception as exc:
        edge_error = str(exc)

    powershell = _powershell()
    if not powershell:
        raise RuntimeError(
            f"Edge neural TTS failed ({edge_error}); Windows PowerShell fallback is unavailable"
        )
    text_path = output.with_suffix(".txt")
    text_path.write_text(text, encoding="utf-8-sig")
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-TextFile",
            str(text_path),
            "-OutputPath",
            str(output),
            "-Language",
            language,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creation_flags,
        timeout=180,
    )
    if completed.returncode or not output.is_file() or output.stat().st_size <= 44:
        detail = (completed.stderr or completed.stdout or "SAPI produced no audio").strip()
        raise RuntimeError(
            f"Edge neural TTS failed ({edge_error}); Windows SAPI fallback failed: "
            + detail[-1200:]
        )


def voxcpm_voice_control(layer: dict) -> str:
    """Build a stable Voice Design instruction without changing authored words."""
    speaker = str(layer.get("speaker", "S1")).strip().upper() or "S1"
    digits = "".join(character for character in speaker if character.isdigit())
    speaker_number = int(digits) if digits else 1
    identity = (
        "A young adult Mandarin Chinese male voice"
        if speaker_number % 2 == 0
        else "A young adult Mandarin Chinese female voice"
    )
    delivery = str(layer.get("delivery", "")).replace("(", "").replace(")", "")
    delivery = " ".join(delivery.split())[:160]
    parts = [identity, "natural cinematic dialogue", "clear articulation", "moderate pace"]
    if delivery:
        parts.append(delivery)
    return ", ".join(parts)


def voxcpm_speaker_seed(speaker: object) -> int:
    digest = hashlib.sha256(str(speaker or "S1").upper().encode("utf-8")).digest()
    return 1000 + int.from_bytes(digest[:4], "big") % 2_000_000_000


class VoxCPM2LocalSynthesizer:
    """Load VoxCPM2 once per isolated job, preferring CUDA with CPU fallback."""

    def __init__(self, job: dict):
        self.model_id = str(job.get("voxcpm_model") or VOXCPM_MODEL_DIR).strip()
        requested_device = str(job.get("voxcpm_device") or "auto").strip() or "auto"
        self.local_only = bool(job.get("voxcpm_local_files_only", True))
        missing = voxcpm_model_missing(self.model_id)
        if missing:
            raise RuntimeError(voxcpm_missing_message(self.model_id))
        try:
            import soundfile
            from voxcpm import VoxCPM
        except Exception as exc:
            raise RuntimeError(
                "VoxCPM2 Local is not available in ai_libraries_common/python_env: "
                f"{exc}"
            ) from exc
        self._voxcpm_class = VoxCPM
        self.soundfile = soundfile
        self.model = None
        self.device = self._resolve_device(requested_device)

        try:
            self._load_model(self.device)
        except Exception as first_exc:
            if not self.device.startswith("cuda"):
                raise RuntimeError(
                    "VoxCPM2 Local model could not be loaded from the project models "
                    f"folder. Details: {first_exc}"
                ) from first_exc
            self._clear_model_and_cuda()
            emit({
                "progress": (
                    "VoxCPM2 Local · CUDA model load failed; releasing GPU memory and "
                    f"retrying on CPU ({self._short_error(first_exc)})"
                )
            })
            self.device = "cpu"
            try:
                self._load_model("cpu", fallback_reason=self._short_error(first_exc))
            except Exception as cpu_exc:
                raise RuntimeError(
                    "VoxCPM2 Local model failed on both CUDA and CPU. "
                    f"CUDA: {first_exc}; CPU: {cpu_exc}"
                ) from cpu_exc

    @staticmethod
    def _resolve_device(requested_device: str) -> str:
        requested = str(requested_device or "auto").strip().lower() or "auto"
        if requested != "auto":
            return requested
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    @staticmethod
    def _short_error(exc: Exception) -> str:
        detail = " ".join(str(exc).split()) or exc.__class__.__name__
        return detail[:240]

    def _load_model(self, device: str, *, fallback_reason: str = "") -> None:
        stage = f"VoxCPM2 Local · loading model on {device}"
        if fallback_reason:
            stage += f" · CUDA fallback reason: {fallback_reason}"
        emit({"progress": stage})
        self.model = self._voxcpm_class.from_pretrained(
            self.model_id,
            load_denoiser=False,
            local_files_only=self.local_only,
            optimize=False,
            device=device,
        )
        self.device = device
        emit({"progress": f"VoxCPM2 Local · model ready on {device}"})

    def _clear_model_and_cuda(self) -> None:
        model = getattr(self, "model", None)
        self.model = None
        if model is not None:
            del model
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except Exception:
            pass

    def _generate(self, layer: dict):
        text = str(layer.get("content", "")).strip()
        control = voxcpm_voice_control(layer)
        seed = voxcpm_speaker_seed(layer.get("speaker", "S1"))
        # VoxCPM 2.0.3 (PyPI) does not accept ``seed=`` while newer GitHub
        # revisions do.  Seed this isolated worker's RNGs instead, then pass
        # only the arguments shared by both official APIs.
        random.seed(seed)
        try:
            import numpy as np

            np.random.seed(seed % (2**32))
        except Exception:
            pass
        try:
            import torch

            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
        except Exception:
            pass
        return self.model.generate(
            text=f"({control}){text}",
            cfg_value=2.0,
            inference_timesteps=10,
            normalize=True,
            denoise=False,
            retry_badcase=True,
        )

    def _fallback_after_cuda_inference(self, cuda_exc: Exception) -> None:
        self._clear_model_and_cuda()
        emit({
            "progress": (
                "VoxCPM2 Local · CUDA synthesis failed; releasing GPU memory and "
                f"retrying the current dialogue on CPU ({self._short_error(cuda_exc)})"
            )
        })
        self.device = "cpu"
        try:
            self._load_model("cpu", fallback_reason=self._short_error(cuda_exc))
        except Exception as cpu_exc:
            raise RuntimeError(
                "VoxCPM2 Local CUDA synthesis failed and the CPU fallback model "
                f"could not be loaded. CUDA: {cuda_exc}; CPU: {cpu_exc}"
            ) from cpu_exc

    def synthesize(self, layer: dict, output: Path) -> None:
        try:
            wav = self._generate(layer)
        except Exception as first_exc:
            if not self.device.startswith("cuda"):
                raise
            self._fallback_after_cuda_inference(first_exc)
            try:
                wav = self._generate(layer)
            except Exception as cpu_exc:
                raise RuntimeError(
                    "VoxCPM2 Local synthesis failed on both CUDA and CPU. "
                    f"CUDA: {first_exc}; CPU: {cpu_exc}"
                ) from cpu_exc
        sample_rate = int(self.model.tts_model.sample_rate)
        self.soundfile.write(
            str(output), wav, sample_rate, format="WAV", subtype="PCM_16"
        )
        if not output.is_file() or output.stat().st_size <= 44:
            raise RuntimeError("VoxCPM2 Local produced no usable audio")

    def release(self) -> None:
        self._clear_model_and_cuda()


class EdgeTTSSynthesizer:
    def __init__(self, *, script: Path, ffmpeg: Path):
        self.script = script
        self.ffmpeg = ffmpeg

    def synthesize(self, layer: dict, output: Path) -> None:
        synthesize_line(
            text=str(layer.get("content", "")).strip(),
            language=str(layer.get("language", "Mandarin Chinese")),
            output=output,
            script=self.script,
            ffmpeg=self.ffmpeg,
            speaker=str(layer.get("speaker", "S1")),
        )

    def release(self) -> None:
        return None


def synthesize_timeline(job: dict) -> dict:
    ffmpeg = Path(str(job["ffmpeg"]))
    if not ffmpeg.is_file():
        raise FileNotFoundError(f"FFmpeg not found: {ffmpeg}")
    output = Path(str(job["output_path"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.5, float(job.get("duration_seconds", 0.5)))
    layers = [
        dict(item) for item in job.get("text_layers") or []
        if str(item.get("role", "")) in {"dialogue", "voice_over", "lyrics"}
        and str(item.get("content", "")).strip()
    ]
    if not layers:
        raise ValueError("No authored Dialogue, Voice-over or Lyrics are available for TTS")
    engine = normalize_tts_engine(job.get("engine"))
    script = Path(str(job.get("sapi_script", "")))
    if engine == "edge_tts" and not script.is_file():
        raise FileNotFoundError(f"SAPI TTS script not found: {script}")

    # ``tempfile.mkdtemp`` may apply a private Windows ACL that a child SAPI
    # COM process cannot reopen inside a OneDrive workspace. Inherit the
    # Design folder ACL explicitly instead.
    work = output.parent / f".h3_tts_{uuid.uuid4().hex}"
    work.mkdir(parents=False, exist_ok=False)
    inputs: list[Path] = []
    filters: list[str] = []
    transcript_rows: list[dict] = []
    synthesizer = None
    try:
        synthesizer = (
            VoxCPM2LocalSynthesizer(job)
            if engine == "voxcpm2_local"
            else EdgeTTSSynthesizer(script=script, ffmpeg=ffmpeg)
        )
        for index, layer in enumerate(layers):
            start = max(0.0, float(layer.get("start_seconds", 0.0)))
            end = min(duration, max(start + 0.1, float(layer.get("end_seconds", duration))))
            text = str(layer.get("content", "")).strip()
            language = str(layer.get("language", "Mandarin Chinese"))
            utterance = work / f"utterance_{index + 1:02d}.wav"
            emit({
                "progress": (
                    f"{TTS_ENGINE_LABELS[engine]} {index + 1}/{len(layers)} · "
                    f"{start:.2f}-{end:.2f}s"
                ),
                "index": index,
                "total": len(layers),
            })
            synthesizer.synthesize(layer, utterance)
            spoken_duration = wav_duration(utterance)
            available = max(0.1, end - start)
            speed = max(1.0, spoken_duration / max(0.1, available * 0.96))
            chain = atempo_filters(speed)
            chain.extend((
                "aresample=24000",
                f"adelay={max(0, round(start * 1000))}:all=1",
            ))
            filters.append(f"[{index}:a]" + ",".join(chain) + f"[speech{index}]")
            inputs.append(utterance)
            transcript_rows.append({
                "start_seconds": start,
                "end_seconds": end,
                "role": layer.get("role"),
                "speaker": layer.get("speaker", "S1"),
                "language": language,
                "content": text,
                "native_duration_seconds": round(spoken_duration, 4),
                "tempo_factor": round(speed, 4),
                "tts_engine": engine,
            })

        labels = "".join(f"[speech{index}]" for index in range(len(inputs)))
        filters.append(
            f"{labels}amix=inputs={len(inputs)}:duration=longest:normalize=0,"
            "alimiter=limit=0.95[out]"
        )
        command = [str(ffmpeg), "-y"]
        for source in inputs:
            command.extend(("-i", str(source)))
        command.extend((
            "-filter_complex", ";".join(filters),
            "-map", "[out]", "-t", f"{duration:.6f}",
            "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(output),
        ))
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        completed = subprocess.run(
            command,
            capture_output=True,
            creationflags=creation_flags,
            timeout=max(180, math.ceil(duration * 10)),
        )
        if completed.returncode or not output.is_file() or output.stat().st_size <= 44:
            detail = completed.stderr.decode("utf-8", errors="replace")[-1600:]
            raise RuntimeError(f"FFmpeg TTS composition failed: {detail}")
        return {
            "completed": True,
            "output_path": str(output.resolve()),
            "duration_seconds": duration,
            "transcript": transcript_rows,
            "engine": TTS_ENGINE_LABELS[engine],
        }
    finally:
        if synthesizer is not None:
            synthesizer.release()
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job")
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    emit(synthesize_timeline(job))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        emit({"error": str(exc)})
        raise SystemExit(1)

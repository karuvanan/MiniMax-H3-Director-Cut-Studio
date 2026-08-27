"""Persistent offline BLIP caption service for the PySide6 application."""

from __future__ import annotations

import argparse
import gc
import json
import os
from pathlib import Path
import sys


_CUDA_FALLBACK_MARKERS = (
    "no kernel image is available",
    "cudaerrornokernelimagefordevice",
    "invalid device function",
    "not compatible with the current pytorch installation",
    "cuda error",
    "cuda out of memory",
    "cudnn",
    "cublas",
    "acceleratorerror",
)


def is_cuda_fallback_error(exc: BaseException) -> bool:
    """Return True for GPU runtime/architecture failures safe to retry on CPU."""
    detail = f"{type(exc).__name__}: {exc}".lower()
    return any(marker in detail for marker in _CUDA_FALLBACK_MARKERS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    try:
        from PIL import Image
        import torch
        from transformers import BlipForConditionalGeneration, BlipProcessor

        model_path = Path(args.model).resolve()
        processor = BlipProcessor.from_pretrained(model_path, local_files_only=True)
        device = "cpu" if args.cpu or not torch.cuda.is_available() else "cuda"

        def load_model(target_device: str):
            loaded = BlipForConditionalGeneration.from_pretrained(
                model_path, local_files_only=True
            ).to(target_device)
            loaded.eval()
            return loaded

        startup_warning = ""
        try:
            model = load_model(device)
        except Exception as cuda_exc:
            if device != "cuda" or not is_cuda_fallback_error(cuda_exc):
                raise
            gc.collect()
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
            device = "cpu"
            model = load_model(device)
            startup_warning = (
                "CUDA BLIP startup is incompatible with this GPU/Torch build; "
                f"using CPU: {type(cuda_exc).__name__}: {cuda_exc}"
            )
    except Exception as exc:
        print(
            json.dumps({"fatal": True, "stage": "startup", "error": f"{type(exc).__name__}: {exc}"}),
            flush=True,
        )
        return 1
    ready_payload = {"ready": True, "device": device}
    if startup_warning:
        ready_payload.update({
            "fallback_from": "cuda",
            "warning": startup_warning,
        })
    print(json.dumps(ready_payload, ensure_ascii=False), flush=True)

    for raw in sys.stdin:
        job: dict = {}
        try:
            job = json.loads(raw)
            prompt = str(job.get("prompt", "")).strip()
            for attempt in range(2):
                try:
                    with Image.open(job["image"]) as source_image:
                        image = source_image.convert("RGB")
                    inputs = {
                        key: value.to(device)
                        for key, value in processor(
                            images=image,
                            text=prompt or None,
                            return_tensors="pt",
                        ).items()
                    }
                    with torch.inference_mode():
                        output = model.generate(**inputs, max_new_tokens=50)
                    caption = processor.decode(output[0], skip_special_tokens=True).strip()
                    break
                except Exception as cuda_exc:
                    if (
                        attempt > 0
                        or device != "cuda"
                        or not is_cuda_fallback_error(cuda_exc)
                    ):
                        raise
                    del model
                    inputs = None
                    output = None
                    gc.collect()
                    try:
                        torch.cuda.empty_cache()
                    except Exception:
                        pass
                    device = "cpu"
                    model = load_model(device)
                    print(
                        json.dumps({
                            "ready": True,
                            "device": device,
                            "fallback_from": "cuda",
                            "warning": (
                                "CUDA BLIP inference is incompatible with this GPU/Torch build; "
                                f"retried on CPU: {type(cuda_exc).__name__}: {cuda_exc}"
                            ),
                        }, ensure_ascii=False),
                        flush=True,
                    )
            print(
                json.dumps(
                    {
                        "job": job["job"],
                        "caption": caption,
                        "prompt": prompt,
                        "device": device,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        except Exception as exc:
            print(
                json.dumps({"job": job.get("job", ""), "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False),
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

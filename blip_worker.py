"""Small isolated BLIP caption worker; emits one JSON object to stdout."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from blip_service import is_cuda_fallback_error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--model", required=True)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    from PIL import Image
    import torch
    from transformers import BlipForConditionalGeneration, BlipProcessor

    model_path = Path(args.model).resolve()
    processor = BlipProcessor.from_pretrained(model_path, local_files_only=True)
    device = "cpu" if args.cpu or not torch.cuda.is_available() else "cuda"
    warning = ""

    def caption_on(target_device: str) -> str:
        model = BlipForConditionalGeneration.from_pretrained(
            model_path,
            local_files_only=True,
        ).to(target_device)
        model.eval()
        with Image.open(args.image) as source_image:
            image = source_image.convert("RGB")
        inputs = {
            key: value.to(target_device)
            for key, value in processor(images=image, return_tensors="pt").items()
        }
        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=50)
        return processor.decode(output[0], skip_special_tokens=True).strip()

    try:
        caption = caption_on(device)
    except Exception as cuda_exc:
        if device != "cuda" or not is_cuda_fallback_error(cuda_exc):
            raise
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass
        device = "cpu"
        warning = (
            "CUDA BLIP is incompatible with this GPU/Torch build; "
            f"retried on CPU: {type(cuda_exc).__name__}: {cuda_exc}"
        )
        caption = caption_on(device)
    payload = {"caption": caption, "device": device}
    if warning:
        payload.update({"fallback_from": "cuda", "warning": warning})
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)

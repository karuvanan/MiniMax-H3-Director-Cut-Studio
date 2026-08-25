"""Persistent offline BLIP caption service for the PySide6 application."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


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

        device = "cpu" if args.cpu or not torch.cuda.is_available() else "cuda"
        model_path = Path(args.model).resolve()
        processor = BlipProcessor.from_pretrained(model_path, local_files_only=True)
        model = BlipForConditionalGeneration.from_pretrained(model_path, local_files_only=True).to(device)
        model.eval()
    except Exception as exc:
        print(
            json.dumps({"fatal": True, "stage": "startup", "error": f"{type(exc).__name__}: {exc}"}),
            flush=True,
        )
        return 1
    print(json.dumps({"ready": True, "device": device}), flush=True)

    for raw in sys.stdin:
        job: dict = {}
        try:
            job = json.loads(raw)
            with Image.open(job["image"]) as source_image:
                image = source_image.convert("RGB")
            prompt = str(job.get("prompt", "")).strip()
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

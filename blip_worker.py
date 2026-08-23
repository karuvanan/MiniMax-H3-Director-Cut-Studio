"""Small isolated BLIP caption worker; emits one JSON object to stdout."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


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

    device = "cpu" if args.cpu or not torch.cuda.is_available() else "cuda"
    model_path = Path(args.model).resolve()
    processor = BlipProcessor.from_pretrained(model_path, local_files_only=True)
    model = BlipForConditionalGeneration.from_pretrained(
        model_path,
        local_files_only=True,
    ).to(device)
    image = Image.open(args.image).convert("RGB")
    inputs = {key: value.to(device) for key, value in processor(images=image, return_tensors="pt").items()}
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=50)
    caption = processor.decode(output[0], skip_special_tokens=True).strip()
    print(json.dumps({"caption": caption, "device": device}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)

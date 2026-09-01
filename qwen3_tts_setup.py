"""Install-time verification and optional model download for Qwen3-TTS."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from qwen3_tts_runtime import (
    QWEN3_TTS_MODEL_DIR,
    QWEN3_TTS_RUNTIME_DIR,
    QWEN3_TTS_SUPPORT_DIR,
    qwen3_tts_missing_message,
    qwen3_tts_model_missing,
    qwen3_tts_runtime_missing,
    qwen3_tts_support_missing,
)


MODEL_REPO = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"


def activate_runtime() -> None:
    runtime = str(QWEN3_TTS_RUNTIME_DIR.resolve())
    if runtime not in sys.path:
        sys.path.insert(0, runtime)
    support = str(QWEN3_TTS_SUPPORT_DIR.resolve())
    if support not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = support + os.pathsep + os.environ.get("PATH", "")


def verify() -> int:
    runtime_missing = qwen3_tts_runtime_missing()
    support_missing = qwen3_tts_support_missing()
    if runtime_missing or support_missing:
        print(qwen3_tts_missing_message())
        return 1
    activate_runtime()
    import accelerate
    import huggingface_hub
    import qwen_tts
    import transformers
    from qwen_tts import Qwen3TTSModel

    print("Qwen3-TTS isolated runtime is ready")
    print("  qwen_tts:", Path(qwen_tts.__file__).resolve())
    print("  transformers:", transformers.__version__)
    print("  accelerate:", accelerate.__version__)
    print("  huggingface_hub:", huggingface_hub.__version__)
    print("  API:", Qwen3TTSModel.__name__)
    model_missing = qwen3_tts_model_missing()
    if model_missing:
        print("Qwen3-TTS model is not downloaded yet")
        print("  expected:", QWEN3_TTS_MODEL_DIR)
        print("  missing:", ", ".join(model_missing))
        return 2
    print("Qwen3-TTS model is ready:", QWEN3_TTS_MODEL_DIR)
    return 0


def download_model() -> int:
    if qwen3_tts_runtime_missing() or qwen3_tts_support_missing():
        print(qwen3_tts_missing_message())
        return 1
    activate_runtime()
    from huggingface_hub import snapshot_download

    QWEN3_TTS_MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL_REPO} to {QWEN3_TTS_MODEL_DIR}")
    snapshot_download(repo_id=MODEL_REPO, local_dir=str(QWEN3_TTS_MODEL_DIR))
    return verify()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("verify", "download-model"))
    args = parser.parse_args()
    return verify() if args.action == "verify" else download_model()


if __name__ == "__main__":
    raise SystemExit(main())

"""Project-local Qwen3-TTS runtime and model discovery.

Qwen3-TTS pins an older Transformers stack than the Studio's BLIP runtime.
The package is therefore vendored into an isolated import directory and is
loaded only inside the crash-isolated ``tts_service.py`` worker.
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
QWEN3_TTS_RUNTIME_DIR = PROJECT_ROOT / "ai_libraries_common" / "qwen_tts_runtime"
QWEN3_TTS_SUPPORT_DIR = (
    PROJECT_ROOT / "ai_libraries_common" / "qwen_tts_support" / "sox-14.4.2"
)
QWEN3_TTS_MODEL_DIR = (
    PROJECT_ROOT / "models" / "Qwen3-TTS-12Hz-0.6B-CustomVoice"
)

QWEN3_TTS_RUNTIME_FILES = (
    "qwen_tts/__init__.py",
    "transformers/__init__.py",
    "accelerate/__init__.py",
    "huggingface_hub/__init__.py",
)

QWEN3_TTS_MODEL_FILES = (
    "config.json",
    "generation_config.json",
    "preprocessor_config.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "speech_tokenizer/config.json",
)


def _usable_file(path: Path, minimum_bytes: int = 32) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= minimum_bytes
    except OSError:
        return False


def qwen3_tts_runtime_missing(
    runtime_dir: str | Path | None = None,
) -> list[str]:
    root = Path(runtime_dir).expanduser() if runtime_dir else QWEN3_TTS_RUNTIME_DIR
    if not root.is_dir():
        return ["isolated runtime folder"]
    return [name for name in QWEN3_TTS_RUNTIME_FILES if not _usable_file(root / name)]


def qwen3_tts_support_missing(
    support_dir: str | Path | None = None,
) -> list[str]:
    root = Path(support_dir).expanduser() if support_dir else QWEN3_TTS_SUPPORT_DIR
    if not root.is_dir():
        return ["SoX support folder"]
    required = ("sox.exe", "libsox-3.dll")
    return [name for name in required if not _usable_file(root / name, 10_000)]


def qwen3_tts_model_missing(model_dir: str | Path | None = None) -> list[str]:
    root = Path(model_dir).expanduser() if model_dir else QWEN3_TTS_MODEL_DIR
    if not root.is_dir():
        return ["model folder"]
    missing = [
        name for name in QWEN3_TTS_MODEL_FILES
        if not _usable_file(root / name, 100 if name.endswith(".json") else 32)
    ]
    if not _usable_file(root / "model.safetensors", 100_000_000):
        missing.append("model.safetensors")
    speech_weights = list((root / "speech_tokenizer").glob("*.safetensors"))
    if not any(_usable_file(path, 100_000_000) for path in speech_weights):
        missing.append("speech_tokenizer/*.safetensors")
    return missing


def qwen3_tts_ready(
    model_dir: str | Path | None = None,
    runtime_dir: str | Path | None = None,
) -> bool:
    return not qwen3_tts_runtime_missing(runtime_dir) and not qwen3_tts_model_missing(
        model_dir
    ) and not qwen3_tts_support_missing()


def qwen3_tts_missing_message(
    model_dir: str | Path | None = None,
    runtime_dir: str | Path | None = None,
) -> str:
    model_root = Path(model_dir).expanduser() if model_dir else QWEN3_TTS_MODEL_DIR
    runtime_root = (
        Path(runtime_dir).expanduser() if runtime_dir else QWEN3_TTS_RUNTIME_DIR
    )
    runtime_missing = qwen3_tts_runtime_missing(runtime_root)
    support_missing = qwen3_tts_support_missing()
    model_missing = qwen3_tts_model_missing(model_root)
    parts: list[str] = []
    if runtime_missing:
        parts.append(
            f"runtime {runtime_root} missing: {', '.join(runtime_missing)}"
        )
    if support_missing:
        parts.append(
            f"SoX support {QWEN3_TTS_SUPPORT_DIR} missing: {', '.join(support_missing)}"
        )
    if model_missing:
        parts.append(f"model {model_root} missing: {', '.join(model_missing)}")
    detail = "; ".join(parts) if parts else "none"
    return (
        "Qwen3-TTS Local is not ready. Install the isolated runtime and download "
        "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice. " + detail + "."
    )

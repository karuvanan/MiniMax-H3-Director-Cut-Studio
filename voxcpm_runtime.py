"""Project-local VoxCPM2 model discovery shared by the UI and TTS worker."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VOXCPM_MODEL_DIR = PROJECT_ROOT / "models" / "VoxCPM2"

VOXCPM_REQUIRED_FILES = (
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
)
VOXCPM_MODEL_WEIGHTS = ("model.safetensors", "pytorch_model.bin")
VOXCPM_AUDIO_WEIGHTS = ("audiovae.safetensors", "audiovae.pth")


def _usable_file(path: Path, minimum_bytes: int) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= minimum_bytes
    except OSError:
        return False


def voxcpm_model_missing(model_dir: str | Path | None = None) -> list[str]:
    """Return user-facing missing requirements for a local VoxCPM2 snapshot."""
    root = Path(model_dir).expanduser() if model_dir else VOXCPM_MODEL_DIR
    if not root.is_dir():
        return ["model folder"]
    minimum_sizes = {
        "config.json": 100,
        "tokenizer.json": 1000,
        "tokenizer_config.json": 100,
    }
    missing = [
        name
        for name in VOXCPM_REQUIRED_FILES
        if not _usable_file(root / name, minimum_sizes[name])
    ]
    if not any(_usable_file(root / name, 100_000_000) for name in VOXCPM_MODEL_WEIGHTS):
        missing.append("model.safetensors or pytorch_model.bin")
    if not any(_usable_file(root / name, 10_000_000) for name in VOXCPM_AUDIO_WEIGHTS):
        missing.append("audiovae.safetensors or audiovae.pth")
    return missing


def voxcpm_model_ready(model_dir: str | Path | None = None) -> bool:
    return not voxcpm_model_missing(model_dir)


def voxcpm_missing_message(model_dir: str | Path | None = None) -> str:
    root = Path(model_dir).expanduser() if model_dir else VOXCPM_MODEL_DIR
    missing = voxcpm_model_missing(root)
    detail = ", ".join(missing) if missing else "none"
    return (
        "VoxCPM2 model is not ready. Download openbmb/VoxCPM2 into "
        f"{root}. Missing: {detail}."
    )

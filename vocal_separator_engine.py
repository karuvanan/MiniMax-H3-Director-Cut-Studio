"""Installation and deterministic path helpers for explicit audio separation.

The separator model is deliberately outside the Studio process and is now
invoked only from the Audio Separator Server after a user action. Legacy cache
helpers remain readable so older Project data can be inspected without loading
ONNX Runtime, Torch, or a separation model into the H3 process.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


SEPARATOR_MODEL_NAME = "Kim_Vocal_2.onnx"
AUTO_VOCAL_REFERENCE_MARKER = "MTV AUTO VOCAL REFERENCE"


def separator_installation(project_root: str | Path) -> dict[str, Path]:
    root = Path(project_root).resolve() / "models" / "audio-separator"
    return {
        "root": root,
        "runtime": root / "runtime",
        "model": root / SEPARATOR_MODEL_NAME,
    }


def validate_separator_installation(project_root: str | Path) -> list[str]:
    paths = separator_installation(project_root)
    missing: list[str] = []
    if not paths["model"].is_file():
        missing.append(str(paths["model"]))
    for filename in ("download_checks.json", "mdx_model_data.json", "vr_model_data.json"):
        if not (paths["root"] / filename).is_file():
            missing.append(str(paths["root"] / filename))
    for package in ("audio_separator", "onnxruntime"):
        if not (paths["runtime"] / package).is_dir():
            missing.append(str(paths["runtime"] / package))
    return missing


def _file_digest(path: Path, *, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def vocal_stem_cache_key(
    source_audio: str | Path,
    model_path: str | Path,
) -> str:
    """Key stems by actual source/model bytes, never by a mutable filename."""

    source = Path(source_audio).resolve()
    model = Path(model_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if not model.is_file():
        raise FileNotFoundError(model)
    digest = hashlib.sha256()
    digest.update(b"h3-mtv-vocal-stem-v1\0")
    digest.update(_file_digest(source).encode("ascii"))
    digest.update(b"\0")
    digest.update(_file_digest(model).encode("ascii"))
    return digest.hexdigest()[:24]


def vocal_stem_paths(workspace: str | Path, cache_key: str) -> dict[str, Path]:
    folder = Path(workspace).resolve() / "media" / "audio" / "vocal_stems"
    return {
        "folder": folder,
        "vocal": folder / f"A1_{cache_key}_Vocals.wav",
        "manifest": folder / f"A1_{cache_key}.json",
    }


def cached_vocal_stem(
    workspace: str | Path,
    cache_key: str,
) -> Path | None:
    paths = vocal_stem_paths(workspace, cache_key)
    if not paths["vocal"].is_file() or not paths["manifest"].is_file():
        return None
    try:
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if manifest.get("cache_key") != cache_key:
        return None
    return paths["vocal"]


def auto_vocal_reference_recognition(source_a1: str | Path, cache_key: str) -> str:
    return (
        f"{AUTO_VOCAL_REFERENCE_MARKER}\n"
        "Role: isolated A2 singing-vocal performance reference for H3 lip motion only.\n"
        "Final mix: excluded; the untouched A1 remains the exact final master audio.\n"
        f"Source A1: {Path(source_a1).name}\nCache key: {cache_key}"
    )


def is_auto_vocal_reference(value: object) -> bool:
    return AUTO_VOCAL_REFERENCE_MARKER in str(value or "")

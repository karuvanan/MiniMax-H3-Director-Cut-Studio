"""Resolve the self-contained H3 Director Cut runtime."""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
COMMON_ROOT = PROJECT_ROOT / "ai_libraries_common"


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    python: Path
    ffmpeg: Path
    ffprobe: Path
    blip_model_cache: Path
    blip_snapshot: Path
    blip_model_id: str
    speech_model: Path

    def missing(self) -> list[Path]:
        return [
            path
            for path in (
                self.python,
                self.ffmpeg,
                self.ffprobe,
                self.blip_model_cache,
                self.blip_snapshot,
                self.speech_model,
            )
            if not path.exists()
        ]


def _resolve_tool(command: str, fallbacks: tuple[str, ...] = ()) -> Path:
    found = shutil.which(command)
    if found:
        return Path(found)
    for candidate in fallbacks:
        path = Path(candidate)
        if path.is_file():
            return path
    raise FileNotFoundError(f"Could not locate {command} on PATH")


def _load_macos_runtime_paths() -> RuntimePaths:
    blip_cache = COMMON_ROOT / "models/models--Salesforce--blip-image-captioning-base"
    blip_snapshot = (
        blip_cache
        / "snapshots/82a37760796d32b1411fe092ab5d4e227313294b"
    )
    return RuntimePaths(
        python=Path(sys.executable),
        ffmpeg=_resolve_tool("ffmpeg", ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg")),
        ffprobe=_resolve_tool("ffprobe", ("/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe")),
        blip_model_cache=blip_cache,
        blip_snapshot=blip_snapshot,
        blip_model_id="Salesforce/blip-image-captioning-base",
        speech_model=COMMON_ROOT / "models/openai--whisper-small",
    )


def _load_bundled_runtime_paths() -> RuntimePaths:
    config_path = COMMON_ROOT / "runtime_config.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))

    def absolute(key: str) -> Path:
        return (COMMON_ROOT / data[key]).resolve()

    return RuntimePaths(
        python=absolute("python"),
        ffmpeg=absolute("ffmpeg"),
        ffprobe=absolute("ffprobe"),
        blip_model_cache=absolute("blip_model_cache"),
        blip_snapshot=absolute("blip_snapshot"),
        blip_model_id=data["blip_model_id"],
        speech_model=absolute("speech_model"),
    )


def load_runtime_paths() -> RuntimePaths:
    loader = {
        "darwin": _load_macos_runtime_paths,
    }.get(sys.platform, _load_bundled_runtime_paths)
    return loader()

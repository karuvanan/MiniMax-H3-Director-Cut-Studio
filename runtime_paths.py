"""Resolve the self-contained H3 Director Cut runtime."""

from __future__ import annotations

import json
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


def load_runtime_paths() -> RuntimePaths:
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

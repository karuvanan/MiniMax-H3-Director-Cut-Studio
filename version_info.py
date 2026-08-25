"""Single source of truth for Studio and project-format versions."""

from __future__ import annotations

from pathlib import Path


VERSION_FILE = Path(__file__).resolve().with_name("VERSION")
FALLBACK_APP_VERSION = "0.0.0-unknown"
PROJECT_FORMAT_VERSION = 14


def read_app_version(version_file: Path = VERSION_FILE) -> str:
    """Read the release version without making startup depend on the file."""
    try:
        value = version_file.read_text(encoding="utf-8-sig").strip()
    except OSError:
        return FALLBACK_APP_VERSION
    return value or FALLBACK_APP_VERSION


APP_VERSION = read_app_version()

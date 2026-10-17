"""Read-only size accounting for H3 Relay's window checkpoint cache."""

from __future__ import annotations

import os
import json
from pathlib import Path


CACHE_DIRECTORY_NAME = "__h3_removal_cache"
CACHE_BUDGET_BYTES = 100 * 1024**3
DEFAULT_CACHE_REFRESH_SECONDS = 120
DEFAULT_RESOURCE_REFRESH_SECONDS = 5


def _settings_payload(settings_path: str | Path) -> dict:
    try:
        payload = json.loads(Path(settings_path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def configured_cache_directory(
    default_root: str | Path,
    settings_path: str | Path,
) -> Path:
    """Resolve the locally-authored cache path without accepting it via HTTP."""

    fallback = Path(default_root)
    payload = _settings_payload(settings_path)
    configured = str(payload.get("cache_path", "") or "").strip()
    if not configured:
        return fallback
    try:
        return Path(configured).expanduser().resolve(strict=False)
    except OSError:
        return fallback


def configured_refresh_seconds(
    settings_path: str | Path,
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    """Read and clamp a locally-authored monitoring interval."""

    payload = _settings_payload(settings_path)
    try:
        value = int(payload.get(key, default))
    except (TypeError, ValueError, OverflowError):
        value = default
    return max(minimum, min(maximum, value))


def configured_cache_refresh_seconds(settings_path: str | Path) -> int:
    return configured_refresh_seconds(
        settings_path,
        "cache_refresh_seconds",
        DEFAULT_CACHE_REFRESH_SECONDS,
        minimum=5,
        maximum=3600,
    )


def configured_resource_refresh_seconds(settings_path: str | Path) -> int:
    return configured_refresh_seconds(
        settings_path,
        "resource_refresh_seconds",
        DEFAULT_RESOURCE_REFRESH_SECONDS,
        minimum=2,
        maximum=300,
    )


def measure_cache_directory(root: str | Path) -> dict:
    """Measure regular files without following links outside the cache root."""

    directory = Path(root)
    totals: dict[str, int] = {}
    used_bytes = 0
    file_count = 0
    error_count = 0
    if not directory.is_dir():
        return {
            "ok": True,
            "used_bytes": 0,
            "budget_bytes": CACHE_BUDGET_BYTES,
            "file_count": 0,
            "error_count": 0,
            "breakdown_bytes": {},
        }

    stack: list[tuple[Path, str]] = [(directory, "other")]
    while stack:
        current, bucket = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        entry_bucket = (
                            entry.name
                            if current == directory and entry.is_dir(follow_symlinks=False)
                            else bucket
                        )
                        if entry.is_dir(follow_symlinks=False):
                            stack.append((Path(entry.path), entry_bucket))
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            continue
                        size = max(0, int(entry.stat(follow_symlinks=False).st_size))
                        used_bytes += size
                        file_count += 1
                        totals[entry_bucket] = totals.get(entry_bucket, 0) + size
                    except OSError:
                        error_count += 1
        except OSError:
            error_count += 1

    return {
        "ok": True,
        "used_bytes": used_bytes,
        "budget_bytes": CACHE_BUDGET_BYTES,
        "file_count": file_count,
        "error_count": error_count,
        "breakdown_bytes": totals,
    }


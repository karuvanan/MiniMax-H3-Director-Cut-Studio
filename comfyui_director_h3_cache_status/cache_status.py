"""Read-only size accounting for H3 Relay's window checkpoint cache."""

from __future__ import annotations

import os
import json
from pathlib import Path


CACHE_DIRECTORY_NAME = "__h3_removal_cache"
CACHE_BUDGET_BYTES = 100 * 1024**3


def configured_cache_directory(
    default_root: str | Path,
    settings_path: str | Path,
) -> Path:
    """Resolve the locally-authored cache path without accepting it via HTTP."""

    fallback = Path(default_root)
    try:
        payload = json.loads(Path(settings_path).read_text(encoding="utf-8-sig"))
        configured = str(payload.get("cache_path", "") or "").strip()
    except (OSError, ValueError, TypeError, AttributeError):
        return fallback
    if not configured:
        return fallback
    try:
        return Path(configured).expanduser().resolve(strict=False)
    except OSError:
        return fallback


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


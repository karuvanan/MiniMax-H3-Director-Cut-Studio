"""ComfyUI read-only API used by Director Cut Studio's H3 cache meter."""

from __future__ import annotations

import asyncio
from pathlib import Path
import threading
import time

from .cache_status import (
    CACHE_DIRECTORY_NAME,
    configured_cache_directory,
    measure_cache_directory,
)
from .system_status import collect_system_resources


NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
_CACHE_LOCK = threading.Lock()
_CACHE_SAMPLE: dict = {}
_CACHE_SAMPLED_AT = 0.0
_CACHE_TTL_SECONDS = 30.0
_CACHE_ROOT_KEY = ""


def _combined_status(root: Path) -> dict:
    global _CACHE_SAMPLE, _CACHE_SAMPLED_AT, _CACHE_ROOT_KEY
    now = time.monotonic()
    root_key = str(root.resolve(strict=False))
    with _CACHE_LOCK:
        if (
            not _CACHE_SAMPLE
            or root_key != _CACHE_ROOT_KEY
            or now - _CACHE_SAMPLED_AT >= _CACHE_TTL_SECONDS
        ):
            _CACHE_SAMPLE = measure_cache_directory(root)
            _CACHE_SAMPLED_AT = now
            _CACHE_ROOT_KEY = root_key
        cache = dict(_CACHE_SAMPLE)
    cache["cache_path"] = root_key
    cache["cache_path_exists"] = root.is_dir()
    cache["resources"] = collect_system_resources()
    cache["cache_sample_age_seconds"] = round(
        max(0.0, time.monotonic() - _CACHE_SAMPLED_AT), 3
    )
    return cache


def _register_route() -> None:
    from aiohttp import web
    import folder_paths
    from server import PromptServer

    async def cache_status(_request):
        default_root = (
            Path(folder_paths.get_output_directory()) / CACHE_DIRECTORY_NAME
        )
        root = configured_cache_directory(
            default_root,
            Path(__file__).with_name("status-settings.json"),
        )
        payload = await asyncio.to_thread(_combined_status, root)
        return web.json_response(payload)

    PromptServer.instance.routes.get(
        "/director_studio/h3-relay-cache-status"
    )(cache_status)


try:
    _register_route()
except ModuleNotFoundError as exc:
    # Permit the pure size-accounting module to be unit-tested outside a
    # ComfyUI process. Inside ComfyUI these modules are always available.
    if exc.name not in {"aiohttp", "folder_paths", "server"}:
        raise

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]


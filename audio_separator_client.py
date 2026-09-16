"""HTTP client for the standalone Audio Separator server."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
import urllib.request
import urllib.error


DEFAULT_AUDIO_SEPARATOR_SERVER = os.getenv(
    "AUDIO_SEPARATOR_API_URL", "http://192.168.0.185:7862"
)


def normalize_server(server: str) -> str:
    value = str(server or "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Audio Separator API must be an http:// or https:// address")
    return value


def _opener(server: str):
    hostname = (urlparse(server).hostname or "").casefold()
    if hostname in {"localhost", "127.0.0.1", "::1"} or hostname.startswith(("10.", "192.168.")):
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request


def _json_request(request: urllib.request.Request, timeout: float) -> dict[str, Any]:
    server = f"{urlparse(request.full_url).scheme}://{urlparse(request.full_url).netloc}"
    try:
        with _opener(server).open(request, timeout=max(1.0, float(timeout))) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw).get("detail", raw)
        except ValueError:
            detail = raw
        raise RuntimeError(f"Audio Separator API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Audio Separator connection failed: {exc.reason}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Audio Separator API returned invalid JSON")
    return payload


def fetch_separator_health(server: str, timeout: float = 8.0) -> dict[str, Any]:
    base = normalize_server(server)
    request = urllib.request.Request(base + "/health", headers={"Accept": "application/json"})
    return _json_request(request, timeout)


def separate_audio(server: str, source: str | Path, timeout: float = 7200.0) -> dict[str, Any]:
    base = normalize_server(server)
    source_path = Path(source).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    url = base + "/separate?filename=" + quote(source_path.name)
    request = urllib.request.Request(
        url,
        data=source_path.read_bytes(),
        method="POST",
        headers={
            "Content-Type": "application/octet-stream",
            "Accept": "application/json",
        },
    )
    return _json_request(request, timeout)


def download_separator_file(
    server: str,
    remote_url: str,
    destination: str | Path,
    timeout: float = 600.0,
) -> Path:
    base = normalize_server(server)
    url = str(remote_url or "").strip()
    if url.startswith("/"):
        url = base + url
    parsed_base = urlparse(base)
    parsed_url = urlparse(url)
    if (parsed_url.scheme, parsed_url.netloc) != (parsed_base.scheme, parsed_base.netloc):
        raise RuntimeError("Audio Separator returned a download URL for another server")
    target = Path(destination).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
    with _opener(base).open(request, timeout=max(1.0, float(timeout))) as response:
        with target.open("wb") as handle:
            while block := response.read(1024 * 1024):
                handle.write(block)
    if not target.is_file() or target.stat().st_size < 1024:
        target.unlink(missing_ok=True)
        raise RuntimeError("Audio Separator download is empty")
    return target

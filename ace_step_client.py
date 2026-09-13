"""Small dependency-free client for an ACE-Step 1.5 LAN API server."""

from __future__ import annotations

import ipaddress
import json
import mimetypes
from pathlib import Path
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import uuid


DEFAULT_SERVER = "http://192.168.0.185:8001"
_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _urlopen(request: urllib.request.Request, timeout: float):
    """Open LAN requests without routing them through a configured web proxy."""

    hostname = (urllib.parse.urlparse(request.full_url).hostname or "").lower()
    direct = hostname in {"localhost", "127.0.0.1", "::1"}
    try:
        direct = direct or ipaddress.ip_address(hostname).is_private
    except ValueError:
        pass
    opener = _DIRECT_OPENER if direct else urllib.request
    return opener.open(request, timeout=max(1.0, timeout))


def _endpoint(server: str, suffix: str) -> str:
    """Join an ACE-Step server origin and endpoint path."""

    origin = str(server or "").strip().rstrip("/")
    if not origin:
        raise ValueError("ACE-Step server URL is required")
    return origin + "/" + suffix.lstrip("/")


def _auth_headers(api_key: str) -> dict[str, str]:
    """Build optional bearer authentication headers."""

    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


def request_json(
    server: str,
    suffix: str,
    *,
    api_key: str = "",
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Send a JSON request and return the decoded response object."""

    headers = {"Accept": "application/json", **_auth_headers(api_key)}
    body = None
    method = "GET"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        method = "POST"
    request = urllib.request.Request(
        _endpoint(server, suffix), data=body, headers=headers, method=method
    )
    try:
        with _urlopen(request, timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ACE-Step HTTP {exc.code}: {detail[:1200]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ACE-Step connection failed: {exc.reason}") from exc


def _multipart(
    fields: dict[str, str], files: dict[str, Path]
) -> tuple[bytes, str]:
    """Encode string fields and local files as multipart/form-data."""

    boundary = "----AceStep" + uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")
    for name, path in files.items():
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body.extend(f"--{boundary}\r\n".encode())
        disposition = f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"'
        body.extend((disposition + "\r\n").encode("utf-8"))
        body.extend(f"Content-Type: {media_type}\r\n\r\n".encode())
        body.extend(path.read_bytes())
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def submit_audio_task(
    source_audio: str | Path,
    *,
    server: str = DEFAULT_SERVER,
    prompt: str = "",
    lyrics: str = "",
    task_type: str = "cover",
    model: str = "acestep-v15-turbo",
    instruction: str = "",
    track_name: str = "",
    cover_strength: float = 0.9,
    repainting_start: float = 0.0,
    repainting_end: float | None = None,
    chunk_mask_mode: str = "auto",
    repaint_mode: str = "balanced",
    repaint_strength: float = 0.5,
    reference_audio: str | Path | None = None,
    full_analysis_only: bool = False,
    bpm: int | None = None,
    key_scale: str = "",
    time_signature: str = "",
    audio_duration: float | None = None,
    inference_steps: int = 8,
    seed: int | None = None,
    api_key: str = "",
    timeout: float = 180.0,
) -> str:
    """Upload audio and return the queued ACE-Step task identifier."""

    source = Path(source_audio).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source audio does not exist: {source}")
    files = {"src_audio": source}
    if reference_audio:
        reference = Path(reference_audio).expanduser().resolve()
        if not reference.is_file():
            raise FileNotFoundError(f"Reference audio does not exist: {reference}")
        files["reference_audio"] = reference
    normalized_task = str(task_type or "cover").strip().lower()
    normalized_model = str(model or "acestep-v15-turbo").strip()
    direct_conditioning_tasks = {
        "cover",
        "cover-nofsq",
        "repaint",
        "extract",
        "lego",
        "complete",
    }
    max_steps = 200 if "base" in normalized_model.lower() else 20
    fields = {
        "prompt": prompt,
        "lyrics": lyrics,
        "task_type": normalized_task,
        "audio_cover_strength": str(max(0.0, min(1.0, cover_strength))),
        "full_analysis_only": str(bool(full_analysis_only)).lower(),
        "thinking": "false" if normalized_task in direct_conditioning_tasks else "true",
        "use_cot_caption": "true",
        "use_cot_language": "true",
        "model": normalized_model,
        "batch_size": "1",
        "inference_steps": str(max(1, min(max_steps, int(inference_steps)))),
        "audio_format": "mp3",
    }
    if instruction.strip():
        fields["instruction"] = instruction.strip()
    if track_name.strip():
        fields["track_name"] = track_name.strip()
    if normalized_task == "repaint":
        fields["repainting_start"] = str(max(0.0, float(repainting_start)))
        if repainting_end is not None:
            fields["repainting_end"] = str(max(0.0, float(repainting_end)))
        fields["chunk_mask_mode"] = (
            chunk_mask_mode if chunk_mask_mode in {"auto", "explicit"} else "explicit"
        )
        fields["repaint_mode"] = (
            repaint_mode
            if repaint_mode in {"conservative", "balanced", "aggressive"}
            else "balanced"
        )
        fields["repaint_strength"] = str(
            max(0.0, min(1.0, float(repaint_strength)))
        )
    if bpm is not None:
        fields["bpm"] = str(max(30, min(300, int(bpm))))
    if key_scale.strip():
        fields["key_scale"] = key_scale.strip()
    if time_signature.strip():
        fields["time_signature"] = time_signature.strip()
    if audio_duration is not None:
        fields["audio_duration"] = str(max(10.0, min(600.0, float(audio_duration))))
    if seed is not None:
        fields["use_random_seed"] = "false"
        fields["seed"] = str(int(seed))
    body, content_type = _multipart(fields, files)
    headers = {"Accept": "application/json", "Content-Type": content_type, **_auth_headers(api_key)}
    request = urllib.request.Request(
        _endpoint(server, "release_task"), data=body, headers=headers, method="POST"
    )
    with _urlopen(request, timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    task_id = str((payload.get("data") or {}).get("task_id") or "")
    if not task_id:
        raise RuntimeError(f"ACE-Step did not return a task_id: {payload}")
    return task_id


def query_task(task_id: str, *, server: str = DEFAULT_SERVER, api_key: str = "") -> dict[str, Any]:
    """Return normalized status and result fields for one ACE-Step task."""

    payload = request_json(
        server, "query_result", api_key=api_key, payload={"task_id_list": [task_id]}
    )
    records = payload.get("data") or []
    if not records:
        raise RuntimeError(f"ACE-Step task was not found: {task_id}")
    record = dict(records[0])
    raw_result = record.get("result")
    if isinstance(raw_result, str) and raw_result:
        decoded = json.loads(raw_result)
        record["outputs"] = decoded if isinstance(decoded, list) else [decoded]
    return record


def wait_for_task(
    task_id: str,
    *,
    server: str = DEFAULT_SERVER,
    api_key: str = "",
    timeout: float = 3600.0,
    poll_seconds: float = 3.0,
) -> dict[str, Any]:
    """Poll until a task succeeds, fails, or reaches the timeout."""

    deadline = time.monotonic() + max(1.0, timeout)
    while time.monotonic() < deadline:
        record = query_task(task_id, server=server, api_key=api_key)
        status = int(record.get("status", 0))
        if status == 1:
            return record
        if status == 2:
            raise RuntimeError(f"ACE-Step task failed: {record}")
        time.sleep(max(0.2, poll_seconds))
    raise TimeoutError(f"ACE-Step task timed out: {task_id}")


def download_audio(
    file_url: str,
    destination: str | Path,
    *,
    server: str = DEFAULT_SERVER,
    api_key: str = "",
    timeout: float = 180.0,
) -> Path:
    """Download one generated audio URL to a local destination path."""

    url = file_url if urllib.parse.urlparse(file_url).scheme else _endpoint(server, file_url)
    output = Path(destination).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers=_auth_headers(api_key), method="GET")
    try:
        with _urlopen(request, timeout) as response:
            output.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ACE-Step audio download failed: HTTP {exc.code}: {detail[:600]}") from exc
    return output

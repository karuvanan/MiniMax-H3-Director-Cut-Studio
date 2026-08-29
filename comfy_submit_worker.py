"""Upload local references and queue a compiled API workflow in ComfyUI."""

from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from workflow_engine import validate_portable_media_manifest


_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _direct_urlopen(request, timeout: int):
    """ComfyUI is normally a LAN service and must not be routed through web proxies."""
    return _DIRECT_OPENER.open(request, timeout=timeout)


def _request_json(request: urllib.request.Request, timeout: int = 600) -> dict:
    with _direct_urlopen(request, timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def upload_file(
    server: str,
    path: Path,
    timeout: int,
    upload_name: str | None = None,
) -> dict:
    boundary = "----H3Director" + uuid.uuid4().hex
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    remote_name = str(upload_name or path.name)
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{remote_name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    tail = (
        f"\r\n--{boundary}\r\n"
        'Content-Disposition: form-data; name="type"\r\n\r\ninput'
        f"\r\n--{boundary}\r\n"
        'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue'
        f"\r\n--{boundary}--\r\n"
    ).encode("utf-8")
    parsed = urllib.parse.urlparse(server)
    connection_type = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    connection = connection_type(parsed.hostname, parsed.port, timeout=timeout)
    endpoint = (parsed.path.rstrip("/") if parsed.path else "") + "/upload/image"
    connection.putrequest("POST", endpoint)
    connection.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
    connection.putheader("Content-Length", str(len(head) + path.stat().st_size + len(tail)))
    connection.endheaders()
    connection.send(head)
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            connection.send(chunk)
    connection.send(tail)
    response = connection.getresponse()
    payload = response.read().decode("utf-8")
    connection.close()
    if response.status >= 400:
        raise RuntimeError(f"Upload failed ({response.status}): {payload[:500]}")
    return json.loads(payload)


def test_connection(server: str, timeout: int) -> dict:
    request = urllib.request.Request(server + "/system_stats", method="GET")
    result = _request_json(request, timeout)
    return {
        "connected": True,
        "server": server,
        "system": result.get("system", {}),
        "devices": result.get("devices", []),
    }


def _history_outputs(history_item: dict) -> list[dict]:
    files: list[dict] = []
    for node_id, node_outputs in (history_item.get("outputs") or {}).items():
        if not isinstance(node_outputs, dict):
            continue
        for output_kind, values in node_outputs.items():
            if not isinstance(values, list):
                continue
            for value in values:
                if isinstance(value, dict) and value.get("filename"):
                    files.append({"node_id": str(node_id), "kind": output_kind, **value})
    return files


def wait_for_history(
    server: str,
    prompt_id: str,
    *,
    poll_interval: float,
    generation_timeout: int,
    http_timeout: int,
) -> tuple[dict, list[dict]]:
    started = time.monotonic()
    last_notice = -10.0
    encoded_id = urllib.parse.quote(prompt_id, safe="")
    while True:
        elapsed = time.monotonic() - started
        if elapsed > generation_timeout:
            raise TimeoutError(
                f"Generation timed out after {generation_timeout}s (prompt_id {prompt_id})"
            )
        request = urllib.request.Request(server + "/history/" + encoded_id, method="GET")
        history = _request_json(request, http_timeout)
        item = history.get(prompt_id) if isinstance(history, dict) else None
        if isinstance(item, dict):
            outputs = _history_outputs(item)
            status = item.get("status") or {}
            if status.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI reported an execution error for {prompt_id}")
            if status.get("completed") or outputs:
                return item, outputs
        if elapsed - last_notice >= 5.0:
            print(
                json.dumps(
                    {"progress": f"Generating… {elapsed:.0f}s", "prompt_id": prompt_id},
                    ensure_ascii=False,
                ),
                flush=True,
            )
            last_notice = elapsed
        time.sleep(poll_interval)


def download_outputs(
    server: str,
    outputs: list[dict],
    destination: Path,
    timeout: int,
) -> list[dict]:
    destination.mkdir(parents=True, exist_ok=True)
    downloaded: list[dict] = []
    for index, item in enumerate(outputs):
        query = urllib.parse.urlencode(
            {
                "filename": item["filename"],
                "subfolder": item.get("subfolder", ""),
                "type": item.get("type", "output"),
            }
        )
        request = urllib.request.Request(server + "/view?" + query, method="GET")
        suffix = Path(str(item["filename"])).suffix
        local_path = destination / f"{index:02d}_{item['node_id']}{suffix}"
        with _direct_urlopen(request, timeout) as response:
            local_path.write_bytes(response.read())
        downloaded.append({**item, "local_path": str(local_path.resolve())})
        print(json.dumps({"progress": f"Downloaded {item['filename']}"}, ensure_ascii=False), flush=True)
    return downloaded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job")
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    server = job["server"].rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    if job.get("action") == "test_connection":
        print(json.dumps(test_connection(server, http_timeout), ensure_ascii=False), flush=True)
        return 0
    validate_portable_media_manifest(
        job.get("workflow") or {},
        [item for item in (job.get("media") or []) if isinstance(item, dict)],
    )
    uploaded: list[dict] = []
    seen_uploads: set[tuple[str, str]] = set()
    for item in job.get("media", []):
        if isinstance(item, dict):
            path = Path(str(item.get("path", "")))
            upload_name = str(item.get("upload_name") or path.name)
        else:
            path = Path(str(item))
            upload_name = path.name
        upload_key = (str(path.resolve()) if path.exists() else str(path), upload_name)
        if upload_key in seen_uploads:
            continue
        seen_uploads.add(upload_key)
        if not path.is_file():
            raise FileNotFoundError(
                f"Reference media is missing before ComfyUI upload: {path}"
            )
        result = upload_file(server, path, http_timeout, upload_name)
        uploaded.append({"file": path.name, "upload_name": upload_name, "result": result})
        print(json.dumps({"progress": f"Uploaded {path.name} as {upload_name}"}, ensure_ascii=False), flush=True)
    payload = json.dumps(
        {"prompt": job["workflow"], "client_id": "h3-director-" + uuid.uuid4().hex},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        server + "/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    queued = _request_json(request, http_timeout)
    prompt_id = str(queued.get("prompt_id", ""))
    print(json.dumps({"progress": f"Queued prompt {prompt_id}", "queued": queued}, ensure_ascii=False), flush=True)
    if not prompt_id or not job.get("wait_for_completion", True):
        print(json.dumps({"uploaded": uploaded, "queued": queued}, ensure_ascii=False), flush=True)
        return 0
    history, outputs = wait_for_history(
        server,
        prompt_id,
        poll_interval=max(0.1, float(job.get("history_poll_interval", 1.0))),
        generation_timeout=max(10, int(job.get("generation_timeout", 1800))),
        http_timeout=http_timeout,
    )
    downloaded = outputs
    if job.get("download_dir") and outputs:
        downloaded = download_outputs(server, outputs, Path(job["download_dir"]), http_timeout)
    print(
        json.dumps(
            {
                "uploaded": uploaded,
                "queued": queued,
                "completed": True,
                "outputs": downloaded,
                "status": history.get("status", {}),
                "request_kind": job.get("request_kind", "final"),
                "seed": job.get("seed"),
                "megapixels": job.get("megapixels"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), flush=True)
        raise SystemExit(1)

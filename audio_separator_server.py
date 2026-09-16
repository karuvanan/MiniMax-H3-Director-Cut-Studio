"""LAN API for Kim_Vocal_2 separation with disposable model workers."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
import uvicorn

from runtime_paths import PROJECT_ROOT
from vocal_separator_engine import separator_installation, validate_separator_installation


OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "audio_separator_server"
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024
ALLOWED_SUFFIXES = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}
app = FastAPI(title="H3 Audio Separator", version="1.0")
CUDA_STATUS: dict = {
    "ready": False,
    "cuda_provider": False,
    "provider": "",
    "error": "CUDA runtime has not been validated",
}


def _safe_name(value: str) -> str:
    name = Path(str(value or "source.wav")).name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem).strip("._") or "source"
    suffix = Path(name).suffix.casefold()
    if suffix not in ALLOWED_SUFFIXES:
        suffix = ".wav"
    return stem[:80] + suffix


def _run_worker(source: Path, folder: Path, job_id: str) -> dict:
    installation = separator_installation(PROJECT_ROOT)
    python = Path(sys.executable).resolve()
    site_packages = python.parent / "Lib" / "site-packages"
    vocal = folder / "vocal.wav"
    music = folder / "music.wav"
    mix = folder / ("mix" + source.suffix.casefold())
    command = [
        str(python), "-S", str(PROJECT_ROOT / "vocal_separator_service.py"),
        "--runtime", str(installation["runtime"]),
        "--studio-site-packages", str(site_packages),
        "--model", str(installation["model"]),
    ]
    request = {
        "job": job_id,
        "source_audio": str(source),
        "vocal_destination": str(vocal),
        "music_destination": str(music),
        "mix_destination": str(mix),
    }
    completed = subprocess.run(
        command,
        input=json.dumps(request, ensure_ascii=False) + "\n",
        capture_output=True,
        text=True,
        timeout=7200,
    )
    messages: list[dict] = []
    for line in completed.stdout.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            messages.append(item)
    error = next((item for item in reversed(messages) if item.get("error")), None)
    result_message = next((item for item in reversed(messages) if item.get("result")), None)
    if completed.returncode or error or not result_message:
        detail = str((error or {}).get("error") or completed.stderr[-1500:] or "separator worker failed")
        raise RuntimeError(detail)
    result = dict(result_message["result"])
    for key in ("vocal_path", "music_path", "mix_path"):
        if not Path(str(result.get(key) or "")).is_file():
            raise RuntimeError(f"separator worker did not create {key}")
    return result


def _probe_cuda_runtime() -> dict:
    """Validate CUDA in a disposable subprocess so the API keeps no GPU context."""

    installation = separator_installation(PROJECT_ROOT)
    python = Path(sys.executable).resolve()
    site_packages = python.parent / "Lib" / "site-packages"
    command = [
        str(python), "-S", str(PROJECT_ROOT / "vocal_separator_service.py"),
        "--runtime", str(installation["runtime"]),
        "--studio-site-packages", str(site_packages),
        "--model", str(installation["model"]),
        "--probe",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=180,
    )
    messages: list[dict] = []
    for line in completed.stdout.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            messages.append(item)
    status = next((item for item in reversed(messages) if "ready" in item), {})
    if completed.returncode or not status.get("ready"):
        detail = str(status.get("error") or completed.stderr[-1500:] or "CUDA probe failed")
        return {
            "ready": False,
            "cuda_provider": False,
            "provider": "",
            "error": detail,
        }
    return dict(status)


@app.get("/health")
def health() -> dict:
    missing = validate_separator_installation(PROJECT_ROOT)
    return {
        "service": "h3-audio-separator",
        "model": "Kim_Vocal_2.onnx",
        "execution": "disposable CUDA ONNX worker",
        "missing": missing,
        **CUDA_STATUS,
        "ready": not missing and bool(CUDA_STATUS.get("ready")),
    }


@app.post("/separate")
async def separate(request: Request, filename: str = Query(default="source.wav")) -> dict:
    missing = validate_separator_installation(PROJECT_ROOT)
    if missing:
        raise HTTPException(status_code=503, detail={"missing": missing})
    if not CUDA_STATUS.get("ready") or not CUDA_STATUS.get("cuda_provider"):
        raise HTTPException(
            status_code=503,
            detail=str(CUDA_STATUS.get("error") or "CUDAExecutionProvider is not ready"),
        )
    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=400, detail="empty audio upload")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="audio upload exceeds 2 GB")
    job_id = f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:10]}"
    folder = OUTPUT_ROOT / job_id
    folder.mkdir(parents=True, exist_ok=False)
    source = folder / _safe_name(filename)
    source.write_bytes(payload)
    try:
        result = _run_worker(source, folder, job_id)
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    files = {}
    for kind, key in (("vocal", "vocal_path"), ("music", "music_path"), ("mix", "mix_path")):
        path = Path(str(result[key]))
        files[kind] = {
            "filename": path.name,
            "bytes": path.stat().st_size,
            "url": f"/download/{job_id}/{kind}",
        }
    return {
        "ok": True,
        "job_id": job_id,
        "model": "Kim_Vocal_2.onnx",
        "provider": result.get("provider", "CUDAExecutionProvider"),
        "gpu": result.get("gpu", ""),
        "metrics": result.get("metrics", {}),
        "warnings": result.get("warnings", []),
        "files": files,
    }


@app.get("/download/{job_id}/{kind}")
def download(job_id: str, kind: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", job_id) or kind not in {"vocal", "music", "mix"}:
        raise HTTPException(status_code=404, detail="unknown result")
    folder = OUTPUT_ROOT / job_id
    patterns = {"vocal": "vocal.*", "music": "music.*", "mix": "mix.*"}
    path = next((item for item in folder.glob(patterns[kind]) if item.is_file()), None)
    if path is None:
        raise HTTPException(status_code=404, detail="result has expired")
    return FileResponse(path, filename=path.name, media_type="application/octet-stream")


def main() -> None:
    global CUDA_STATUS
    parser = argparse.ArgumentParser(description="H3 Audio Separator LAN server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7862)
    args = parser.parse_args()
    missing = validate_separator_installation(PROJECT_ROOT)
    if missing:
        raise SystemExit("Audio Separator installation incomplete: " + ", ".join(missing))
    CUDA_STATUS = (
        {
            "ready": True,
            "cuda_provider": True,
            "provider": "CUDAExecutionProvider",
            "gpu": "validated CUDA GPU",
            "onnxruntime": "1.23.2",
        }
        if str(os.environ.get("AUDIO_SEPARATOR_CUDA_PREVALIDATED", "")).strip() == "1"
        else _probe_cuda_runtime()
    )
    if not CUDA_STATUS.get("ready"):
        raise SystemExit("Audio Separator CUDA validation failed: " + str(CUDA_STATUS.get("error")))
    print(
        "[Audio Separator] CUDA ready · "
        f"{CUDA_STATUS.get('gpu')} · ONNX Runtime {CUDA_STATUS.get('onnxruntime')}",
        flush=True,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()

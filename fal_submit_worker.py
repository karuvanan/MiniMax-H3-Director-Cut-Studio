"""Submit FL2VA keyframe jobs to fal's H3 Max endpoint.

This worker is the fal counterpart to comfy_submit_worker.py.  It uses the
same JSON-line stdout protocol so DirectorCutStudio._generation_message and
_generation_finished can consume both providers without branching.

fal FL2VA is NOT a ComfyUI workflow.  The job carries a final text prompt,
optional first/last keyframe paths, duration, resolution, and seed.  The
worker uploads keyframes to fal storage, submits to the queue, polls until
completion, downloads the output video, and emits provenance fields.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import urllib.request

import fal_client


def _emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def _download(url: str, destination: Path, timeout: int = 120) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        destination.write_bytes(response.read())
    return destination


def _upload_keyframe(path: Path, label: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Keyframe is missing before fal upload: {path}")
    url = fal_client.upload_file(str(path))
    _emit({"progress": f"Uploaded {label} -> {url}"})
    return url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job")
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))

    if not os.environ.get("FAL_KEY"):
        raise RuntimeError(
            "FAL_KEY is not set. Launch with run_h3_prompt_studio.sh "
            "to retrieve it with pass-get FAL_API_KEY."
        )

    endpoint = job.get("endpoint", "minimax/h3-max/image-to-video")
    prompt = str(job.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("fal job requires a non-empty prompt.")

    download_dir = Path(job.get("download_dir", "."))
    request_kind = job.get("request_kind", "final")
    seed = job.get("seed")
    megapixels = job.get("megapixels")
    duration = int(job.get("duration", 5))
    resolution = str(job.get("resolution", "768P"))
    prompt_expansion_mode = str(job.get("prompt_expansion_mode", "disabled"))
    enable_safety_checker = bool(job.get("enable_safety_checker", False))

    arguments: dict = {
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "seed": seed,
        "prompt_expansion_mode": prompt_expansion_mode,
        "enable_safety_checker": enable_safety_checker,
    }

    first_frame = job.get("first_frame_path")
    last_frame = job.get("last_frame_path")
    if first_frame:
        arguments["image_url"] = _upload_keyframe(Path(first_frame), "first_frame")
    if last_frame:
        arguments["end_image_url"] = _upload_keyframe(Path(last_frame), "last_frame")

    _emit({"progress": f"Submitting to fal {endpoint} . {duration}s {resolution} seed={seed}"})

    started = time.monotonic()
    request_id: str = ""

    def on_enqueue(rid: str) -> None:
        nonlocal request_id
        request_id = rid
        _emit({"queued": {"prompt_id": rid}, "progress": f"fal queued request {rid}"})

    def on_queue_update(status) -> None:
        elapsed = time.monotonic() - started
        status_str = str(status)
        _emit({"progress": f"fal {status_str} . {elapsed:.0f}s"})

    result = fal_client.subscribe(
        endpoint,
        arguments,
        with_logs=True,
        on_enqueue=on_enqueue,
        on_queue_update=on_queue_update,
    )

    if not request_id:
        request_id = str(getattr(result, "request_id", "") or "")

    data = result if isinstance(result, dict) else {}
    video_url = ""
    if isinstance(data.get("video"), dict):
        video_url = str(data["video"].get("url", ""))
    if not video_url:
        raise RuntimeError(f"fal returned no video URL. Response: {json.dumps(data)[:500]}")

    suffix = ".mp4"
    local_path = download_dir / f"fal_output{suffix}"
    _download(video_url, local_path)
    _emit({"progress": f"Downloaded {local_path.name}"})

    elapsed = time.monotonic() - started
    timings = data.get("timings") or {}
    inference = timings.get("inference")

    output_record = {
        "node_id": "fal_output",
        "kind": "video",
        "filename": local_path.name,
        "local_path": str(local_path.resolve()),
        "remote_url": video_url,
        "request_id": request_id,
        "inference_seconds": inference,
        "wall_clock_seconds": round(elapsed, 1),
        "resolution": data.get("resolution", resolution),
        "expanded_prompt": data.get("expanded_prompt", ""),
    }

    _emit(
        {
            "queued": {"prompt_id": request_id},
            "completed": True,
            "outputs": [output_record],
            "status": {"status_str": "success"},
            "request_kind": request_kind,
            "seed": seed,
            "megapixels": megapixels,
            "provider": "fal.fl2va",
            "endpoint": endpoint,
            "fal_request_id": request_id,
        }
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        _emit({"error": str(exc)})
        raise SystemExit(1)

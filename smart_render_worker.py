"""Run hidden H3 segments sequentially and assemble one continuous master.

This worker intentionally keeps only one ComfyUI prompt in flight.  Between
segments it asks ComfyUI to release models/VRAM, persists a resumable manifest,
and can inject a preceding-segment continuity anchor into a free reference slot.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid

from comfy_submit_worker import (
    _direct_urlopen,
    _request_json,
    download_outputs,
    upload_file,
    wait_for_history,
)


VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
MINIMUM_FREE_DISK_BYTES = 2 * 1024**3
SMART_RENDER_POLICY_VERSION = 7


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def _segment_core_bounds(segment: dict) -> tuple[float, float]:
    """Return the non-overlapping timeline range represented by a segment."""
    core_start = segment.get("core_start_seconds")
    core_end = segment.get("core_end_seconds")
    start = float(segment.get("start_seconds", 0.0) if core_start is None else core_start)
    end = float(segment.get("end_seconds", start) if core_end is None else core_end)
    return start, max(start, end)


def _shot_progress_rows(job: dict, segments: list[dict]) -> list[dict]:
    """Normalize authored Shot weights and map each Shot to all of its segments."""
    raw_rows = [row for row in (job.get("progress_shots") or []) if isinstance(row, dict)]
    if not raw_rows:
        return []

    segment_ids = {
        str(segment.get("segment_id", "")): index
        for index, segment in enumerate(segments)
        if segment.get("segment_id")
    }
    normalized: list[dict] = []
    for row_index, source in enumerate(raw_rows):
        shot_id = str(
            source.get("cue_id")
            or source.get("shot_id")
            or source.get("id")
            or f"shot_{row_index + 1}"
        )
        start_value = source.get("start_seconds")
        end_value = source.get("end_seconds")
        start = float(start_value) if start_value is not None else None
        end = float(end_value) if end_value is not None else None
        duration_value = source.get("duration_seconds")
        duration = (
            max(0.0, float(duration_value))
            if duration_value is not None
            else max(0.0, float(end or 0.0) - float(start or 0.0))
        )

        required: set[int] = set()
        explicit_segment_ids = source.get("segment_ids") or []
        if isinstance(explicit_segment_ids, (list, tuple, set)):
            required.update(
                segment_ids[str(segment_id)]
                for segment_id in explicit_segment_ids
                if str(segment_id) in segment_ids
            )
        if not required:
            required.update(
                index
                for index, segment in enumerate(segments)
                if shot_id in {str(value) for value in (segment.get("shot_ids") or [])}
            )
        if not required and start is not None and end is not None:
            for index, segment in enumerate(segments):
                core_start, core_end = _segment_core_bounds(segment)
                if start < core_end - 1e-9 and end > core_start + 1e-9:
                    required.add(index)
            # A zero-duration marker belongs to the segment beginning at that
            # instant, or the final segment when it sits at the timeline end.
            if not required and abs(end - start) <= 1e-9:
                for index, segment in enumerate(segments):
                    core_start, core_end = _segment_core_bounds(segment)
                    if core_start - 1e-9 <= start < core_end - 1e-9:
                        required.add(index)
                        break
                if not required and segments:
                    _, final_end = _segment_core_bounds(segments[-1])
                    if abs(start - final_end) <= 1e-9:
                        required.add(len(segments) - 1)
        if not required and segments:
            # Keep malformed legacy metadata finishable instead of leaving a
            # Shot permanently pending.
            required.add(min(row_index, len(segments) - 1))
        normalized.append(
            {
                "shot_id": shot_id,
                "duration_seconds": duration,
                "required_segment_indexes": required,
            }
        )
    return normalized


def build_render_progress(
    job: dict,
    segments: list[dict],
    completed_indexes: set[int],
    *,
    stage: str,
    current_index: int | None = None,
) -> dict:
    """Build truthful duration-weighted progress for one smart-render event.

    Authored ``progress_shots`` are preferred when supplied by the Studio. A
    Shot spanning multiple internal segments is complete only after every one
    of those segments has completed. Older jobs fall back to non-overlapping
    segment core durations while still reporting unique Shot IDs when present.
    """
    completed_set = {
        int(index) for index in completed_indexes if 0 <= int(index) < len(segments)
    }
    shot_rows = _shot_progress_rows(job, segments)

    shot_requirements: dict[str, set[int]] = {}
    if shot_rows:
        for row in shot_rows:
            shot_requirements.setdefault(str(row["shot_id"]), set()).update(
                row["required_segment_indexes"]
            )
    else:
        for index, segment in enumerate(segments):
            ids = [str(value) for value in (segment.get("shot_ids") or []) if str(value)]
            if not ids:
                ids = [str(segment.get("segment_id") or f"segment_{index + 1}")]
            for shot_id in ids:
                shot_requirements.setdefault(shot_id, set()).add(index)

    completed_shot_ids = [
        shot_id
        for shot_id, required in shot_requirements.items()
        if required and required.issubset(completed_set)
    ]
    total_shots = len(shot_requirements)
    completed_shots = len(completed_shot_ids)

    segment_weights = [
        max(0.0, core_end - core_start)
        for core_start, core_end in (_segment_core_bounds(segment) for segment in segments)
    ]
    if shot_rows and sum(float(row["duration_seconds"]) for row in shot_rows) > 1e-9:
        total_weight = sum(float(row["duration_seconds"]) for row in shot_rows)
        completed_weight = sum(
            float(row["duration_seconds"])
            for row in shot_rows
            if row["required_segment_indexes"]
            and row["required_segment_indexes"].issubset(completed_set)
        )
        weight_source = "shots"
    else:
        total_weight = sum(segment_weights)
        completed_weight = sum(
            weight for index, weight in enumerate(segment_weights) if index in completed_set
        )
        weight_source = "segment_core"

    if total_weight <= 1e-9:
        percent_complete = 100.0 if len(completed_set) == len(segments) else 0.0
    else:
        percent_complete = min(100.0, max(0.0, completed_weight / total_weight * 100.0))
    percent_complete = round(percent_complete, 2)

    current_segment = (
        segments[current_index]
        if current_index is not None and 0 <= current_index < len(segments)
        else None
    )
    current_shot_ids: list[str] = []
    if current_segment is not None:
        current_shot_ids = [
            str(value) for value in (current_segment.get("shot_ids") or []) if str(value)
        ]
        if not current_shot_ids and shot_rows:
            current_shot_ids = [
                str(row["shot_id"])
                for row in shot_rows
                if current_index in row["required_segment_indexes"]
            ]

    return {
        "stage": str(stage),
        "current_segment_index": current_index,
        "current_segment_number": current_index + 1 if current_index is not None else None,
        "current_segment_id": (
            str(current_segment.get("segment_id", "")) if current_segment is not None else ""
        ),
        "segment_count": len(segments),
        "completed_segments": len(completed_set),
        "remaining_segments": max(0, len(segments) - len(completed_set)),
        "current_shot_ids": current_shot_ids,
        "completed_shot_ids": completed_shot_ids,
        "completed_shots": completed_shots,
        "total_shots": total_shots,
        "remaining_shots": max(0, total_shots - completed_shots),
        "weight_source": weight_source,
        "completed_weight_seconds": round(completed_weight, 6),
        "total_weight_seconds": round(total_weight, 6),
        "percent_complete": percent_complete,
        "percent_remaining": round(max(0.0, 100.0 - percent_complete), 2),
    }


def _post_json(server: str, endpoint: str, payload: dict, timeout: int) -> dict:
    request = urllib.request.Request(
        server + endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with _direct_urlopen(request, timeout) as response:
        body = response.read().decode("utf-8").strip()
    return json.loads(body) if body else {}


def release_comfy_memory(server: str, timeout: int) -> str:
    """Best-effort model/VRAM cleanup supported by current ComfyUI releases."""
    try:
        _post_json(
            server,
            "/free",
            {"unload_models": True, "free_memory": True},
            timeout,
        )
        return "ComfyUI models and VRAM released"
    except Exception as exc:  # cleanup must never discard a completed segment
        return f"ComfyUI cleanup skipped: {exc}"


def _primary_video(outputs: list[dict]) -> Path | None:
    for item in outputs:
        local_path = Path(str(item.get("local_path", "")))
        if local_path.is_file() and local_path.suffix.lower() in VIDEO_SUFFIXES:
            return local_path.resolve()
    return None


def _write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def preflight_smart_render(job: dict) -> dict:
    """Fail before media upload if a long render cannot complete on this host."""
    segments = list(job.get("segments") or [])
    if len(segments) < 2:
        raise ValueError("Smart Long Render requires at least two internal segments.")
    for index, segment in enumerate(segments, 1):
        duration = float(segment.get("end_seconds", 0.0)) - float(
            segment.get("start_seconds", 0.0)
        )
        if duration <= 0.0 or duration > 15.0 + 1e-6:
            raise ValueError(
                f"Segment {index} has invalid duration {duration:.3f}s; expected 0–15s."
            )

    ffmpeg = Path(str(job.get("ffmpeg", "")))
    ffprobe = Path(str(job.get("ffprobe", "")))
    if not ffmpeg.is_file() or not ffprobe.is_file():
        raise FileNotFoundError("Bundled FFmpeg or FFprobe is missing.")

    output_parent = Path(job["master_output"]).parent
    output_parent.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(output_parent).free
    if free_bytes < MINIMUM_FREE_DISK_BYTES:
        raise OSError(
            f"Smart Long Render needs at least 2GB free disk space; only "
            f"{free_bytes / 1024**3:.2f}GB is available."
        )

    required_classes = {
        str(node.get("class_type", ""))
        for segment in segments
        for node in (segment.get("workflow") or {}).values()
        if isinstance(node, dict) and node.get("class_type")
    }
    server = str(job["server"]).rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    object_info = _request_json(
        urllib.request.Request(server + "/object_info", method="GET"),
        http_timeout,
    )
    missing = sorted(required_classes - set(object_info))
    if missing:
        raise RuntimeError(
            "ComfyUI is missing required workflow node classes: " + ", ".join(missing)
        )
    return {
        "segment_count": len(segments),
        "node_class_count": len(required_classes),
        "free_disk_gb": round(free_bytes / 1024**3, 2),
    }


def _patch_continuity(workflow: dict, continuity: dict, uploaded_name: str) -> None:
    loader_id = str(continuity.get("loader_node_id", ""))
    h3_id = str(continuity.get("h3_node_id", ""))
    binding = str(continuity.get("binding", ""))
    connection = continuity.get("connection")
    if not loader_id or not h3_id or not binding or not isinstance(connection, list):
        return
    loader = workflow.get(loader_id)
    h3_node = workflow.get(h3_id)
    if not isinstance(loader, dict) or not isinstance(h3_node, dict):
        return
    loader_input = str(continuity.get("loader_input", "file"))
    loader.setdefault("inputs", {})[loader_input] = uploaded_name
    h3_inputs = h3_node.setdefault("inputs", {})
    occupied = h3_inputs.get(binding)
    if occupied is not None and occupied != connection:
        raise RuntimeError(
            "Continuity reference slot collision at " + binding
            + "; refusing to overwrite an active Timeline reference."
        )
    h3_inputs[binding] = connection
    paired = str(continuity.get("paired_audio_binding", ""))
    paired_connection = continuity.get("paired_audio_connection")
    if paired and isinstance(paired_connection, list):
        h3_node["inputs"][paired] = paired_connection
    _canonicalize_reference_input_order(h3_node)


def _canonicalize_reference_input_order(h3_node: dict) -> None:
    """Keep Autogrow references contiguous and deterministic at runtime.

    The continuity binding was disconnected during compilation and is added
    back at runtime. Rebuilding and compacting the mapping removes any
    ambiguity between JSON insertion order, sparse physical loader slots, and
    Autogrow suffix order, so prompt ordinals always match the exact fields
    consumed by MiniMaxH3ReferenceToVideo.
    """
    inputs = h3_node.get("inputs") or {}
    prefixes = {
        "ref_images.ref_image_": 0,
        "ref_videos.ref_video_": 1,
        "ref_video_audios.ref_video_audio_": 2,
        "ref_audios.ref_audio_": 3,
    }

    ordinary = [item for item in inputs.items() if not any(item[0].startswith(p) for p in prefixes)]
    references: list[tuple[str, object]] = []
    for prefix, _group in sorted(prefixes.items(), key=lambda item: item[1]):
        rows = [item for item in inputs.items() if item[0].startswith(prefix)]
        rows.sort(
            key=lambda item: int(re.search(r"_(\d+)$", item[0]).group(1))
            if re.search(r"_(\d+)$", item[0]) else 10_000
        )
        references.extend(
            (f"{prefix}{request_index}", value)
            for request_index, (_name, value) in enumerate(rows)
        )
    h3_node["inputs"] = dict(ordinary + references)


def extract_tail_frames(
    ffmpeg: Path,
    ffprobe: Path,
    source: Path,
    destination: Path,
    *,
    frame_count: int = 24,
    fps: int = 24,
) -> Path:
    """Extract exact motion-only tail frames for the next H3 segment."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame_count = max(1, int(frame_count))
    fps = max(1, int(fps))
    source_duration = _probe_duration(ffprobe, source)
    tail_seconds = frame_count / fps
    start = max(0.0, source_duration - tail_seconds)
    command = [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{start:.6f}", "-i", str(source),
        "-an", "-vf", f"fps={fps}", "-frames:v", str(frame_count),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(destination),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if completed.returncode or not destination.is_file():
        raise RuntimeError("Could not extract continuity tail: " + completed.stderr[-800:])
    return destination.resolve()


def _probe_duration(ffprobe: Path, source: Path) -> float:
    completed = subprocess.run(
        [
            str(ffprobe), "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(source),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode:
        raise RuntimeError("Could not probe continuity source: " + completed.stderr[-800:])
    try:
        return max(0.0, float(completed.stdout.strip()))
    except ValueError as exc:
        raise RuntimeError("Continuity source has no readable duration.") from exc


def extract_last_frame(
    ffmpeg: Path,
    ffprobe: Path,
    source: Path,
    destination: Path,
) -> Path:
    """Extract a still near the real media end without carrying prior motion."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    duration = _probe_duration(ffprobe, source)
    # H3 output durations are quantized to valid frame counts and are often
    # longer than the requested seconds. Probe the file rather than trusting
    # the requested segment duration, otherwise this would not be its tail.
    seek = max(0.0, duration - 0.08)
    command = [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{seek:.6f}", "-i", str(source),
        "-frames:v", "1", "-q:v", "2", str(destination),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if completed.returncode or not destination.is_file():
        raise RuntimeError("Could not extract continuity frame: " + completed.stderr[-800:])
    return destination.resolve()


def _has_audio(ffprobe: Path, source: Path) -> bool:
    completed = subprocess.run(
        [
            str(ffprobe), "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=index", "-of", "csv=p=0", str(source),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return completed.returncode == 0 and bool(completed.stdout.strip())


def build_assembly_command(
    ffmpeg: Path,
    ffprobe: Path,
    segments: list[dict],
    destination: Path,
    target_duration: float,
) -> list[str]:
    """Build a trim/concat command that removes duplicated overlap frames."""
    paths = [Path(str(row["output_path"])) for row in segments]
    if not paths or not all(path.is_file() for path in paths):
        raise FileNotFoundError("One or more generated segment files are missing.")
    include_audio = all(_has_audio(ffprobe, path) for path in paths)
    command = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y"]
    for path in paths:
        command.extend(["-i", str(path)])

    filters: list[str] = []
    concat_inputs: list[str] = []
    for index, row in enumerate(segments):
        trim = max(0.0, float(row.get("overlap_before_seconds", 0.0)))
        core_start = row.get("core_start_seconds")
        core_end = row.get("core_end_seconds")
        if core_start is None or core_end is None:
            core_duration = max(
                0.0,
                float(row.get("end_seconds", 0.0))
                - float(row.get("start_seconds", 0.0))
                - trim,
            )
        else:
            core_duration = max(0.0, float(core_end) - float(core_start))
        if core_duration <= 0.0:
            raise ValueError(f"Segment {index + 1} has no positive core duration.")
        trim_end = trim + core_duration
        filters.append(
            f"[{index}:v]trim=start={trim:.6f}:end={trim_end:.6f},"
            f"setpts=PTS-STARTPTS[v{index}]"
        )
        concat_inputs.append(f"[v{index}]")
        if include_audio:
            filters.append(
                f"[{index}:a]atrim=start={trim:.6f}:end={trim_end:.6f},"
                f"asetpts=PTS-STARTPTS[a{index}]"
            )
            concat_inputs.append(f"[a{index}]")
    filters.append(
        "".join(concat_inputs)
        + f"concat=n={len(paths)}:v=1:a={1 if include_audio else 0}"
        + ("[vout][aout]" if include_audio else "[vout]")
    )
    command.extend(["-filter_complex", ";".join(filters), "-map", "[vout]"])
    if include_audio:
        command.extend(["-map", "[aout]"])
    command.extend(
        [
            "-t", f"{target_duration:.6f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
        ]
    )
    if include_audio:
        command.extend(["-c:a", "aac", "-b:a", "192k"])
    else:
        command.append("-an")
    command.extend(["-movflags", "+faststart", str(destination)])
    return command


def assemble_master(job: dict, segments: list[dict]) -> Path:
    destination = Path(job["master_output"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = build_assembly_command(
        Path(job["ffmpeg"]),
        Path(job["ffprobe"]),
        segments,
        destination,
        float(job["target_duration_seconds"]),
    )
    emit({"progress": f"Assembling {len(segments)} segments into the master video…"})
    completed = subprocess.run(command, capture_output=True, text=True, timeout=1800)
    if completed.returncode:
        raise RuntimeError("FFmpeg master assembly failed: " + completed.stderr[-1200:])
    return destination.resolve()


def queue_segment(job: dict, segment: dict, workflow: dict, uploaded: list[dict]) -> dict:
    server = job["server"].rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    attempts = max(1, int(job.get("segment_attempts", 2)))
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            payload = json.dumps(
                {"prompt": workflow, "client_id": "h3-smart-render-" + uuid.uuid4().hex},
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
            if not prompt_id:
                raise RuntimeError("ComfyUI did not return a prompt_id.")
            emit({
                "progress": f"Segment {segment['index'] + 1}/{job['segment_count']} queued · {prompt_id}",
                "segment_index": segment["index"],
                "queued": queued,
            })
            history, outputs = wait_for_history(
                server,
                prompt_id,
                poll_interval=max(0.1, float(job.get("history_poll_interval", 1.0))),
                generation_timeout=max(10, int(job.get("generation_timeout", 1800))),
                http_timeout=http_timeout,
            )
            downloaded = download_outputs(
                server,
                outputs,
                Path(segment["download_dir"]),
                http_timeout,
            )
            video = _primary_video(downloaded)
            if video is None:
                raise RuntimeError(f"Segment {segment['index'] + 1} produced no downloadable video.")
            persisted_segment = {key: value for key, value in segment.items() if key != "workflow"}
            return {
                **persisted_segment,
                "status": "complete",
                "output_path": str(video),
                "prompt_id": prompt_id,
                "outputs": downloaded,
                "history_status": history.get("status", {}),
                "uploaded": uploaded,
                "error": "",
            }
        except Exception as exc:
            last_error = exc
            emit({
                "progress": f"Segment {segment['index'] + 1} attempt {attempt}/{attempts} failed: {exc}",
                "segment_index": segment["index"],
            })
            emit({"progress": release_comfy_memory(server, http_timeout)})
            if attempt < attempts:
                time.sleep(1.0)
    raise RuntimeError(str(last_error or "Unknown segment generation error"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job")
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    server = str(job["server"]).rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    manifest_path = Path(job["manifest_path"])
    segments = [dict(row) for row in job.get("segments", [])]
    job["segment_count"] = len(segments)
    if not segments:
        raise ValueError("The smart-render job has no segments.")

    preflight = preflight_smart_render(job)
    completed_indexes: set[int] = set()
    emit({
        "preflight": preflight,
        "render_progress": build_render_progress(
            job, segments, completed_indexes, stage="preflight"
        ),
        "progress": (
            f"Long-render preflight passed · {preflight['segment_count']} segments · "
            f"{preflight['node_class_count']} node classes · "
            f"{preflight['free_disk_gb']:.1f}GB disk free"
        ),
    })

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
        if path.is_file():
            result = upload_file(server, path, http_timeout, upload_name)
            uploaded.append({
                "file": path.name,
                "upload_name": upload_name,
                "result": result,
            })
            emit({"progress": f"Uploaded {path.name} as {upload_name}"})

    completed: list[dict] = []
    previous_video: Path | None = None
    for index, segment in enumerate(segments):
        cached = Path(str(segment.get("output_path", "")))
        if segment.get("status") == "cached" and cached.is_file():
            segment["output_path"] = str(cached.resolve())
            completed.append({key: value for key, value in segment.items() if key != "workflow"})
            completed_indexes.add(index)
            previous_video = cached.resolve()
            emit({
                "segment_status": {
                    "segment_id": segment["segment_id"],
                    "status": "reusable",
                },
                "render_progress": build_render_progress(
                    job, segments, completed_indexes, stage="cached", current_index=index
                ),
                "progress": f"Segment {index + 1}/{len(segments)} reused from cache",
            })
            continue

        workflow = deepcopy(segment["workflow"])
        continuity = segment.get("continuity") or {}
        if previous_video is not None and continuity:
            kind = str(continuity.get("kind", "image")).lower()
            if kind == "video":
                anchor_path = Path(segment["download_dir"]) / "continuity_tail.mp4"
                extract_tail_frames(
                    Path(job["ffmpeg"]),
                    Path(job["ffprobe"]),
                    previous_video,
                    anchor_path,
                    frame_count=int(continuity.get("frame_count", 24)),
                    fps=int(continuity.get("fps", 24)),
                )
            else:
                anchor_path = Path(segment["download_dir"]) / "continuity_frame.jpg"
                extract_last_frame(
                    Path(job["ffmpeg"]),
                    Path(job["ffprobe"]),
                    previous_video,
                    anchor_path,
                )
            upload = upload_file(server, anchor_path, http_timeout)
            uploaded_name = str((upload or {}).get("name") or anchor_path.name)
            _patch_continuity(workflow, continuity, uploaded_name)
            label = "24-frame motion tail" if kind == "video" else "last-frame still"
            emit({"progress": f"Segment {index + 1}: previous {label} continuity attached"})

        emit({
            "segment_status": {
                "segment_id": segment["segment_id"],
                "status": "running",
            },
            "render_progress": build_render_progress(
                job, segments, completed_indexes, stage="running", current_index=index
            ),
            "progress": (
                f"Generating segment {index + 1}/{len(segments)} · "
                f"{segment['start_seconds']:.2f}–{segment['end_seconds']:.2f}s"
            )
        })
        try:
            result = queue_segment(job, segment, workflow, uploaded)
        except Exception as exc:
            failed = {
                key: value for key, value in segment.items() if key != "workflow"
            }
            failed.update(status="failed", error=str(exc))
            manifest = {
                "format": "h3-smart-render-manifest",
                "version": 1,
                "render_policy_version": int(
                    job.get("render_policy_version", SMART_RENDER_POLICY_VERSION)
                ),
                "request_kind": job.get("request_kind", "final"),
                "master_seed": job.get("seed"),
                "megapixels": job.get("megapixels"),
                "target_duration_seconds": job.get("target_duration_seconds"),
                "segments": completed + [failed] + [
                    {key: value for key, value in row.items() if key != "workflow"}
                    for row in segments[index + 1 :]
                ],
            }
            _write_manifest(manifest_path, manifest)
            emit({
                "segment_status": {
                    "segment_id": segment["segment_id"],
                    "status": "failed",
                    "error": str(exc),
                },
                "partial_manifest": manifest,
                "render_progress": build_render_progress(
                    job, segments, completed_indexes, stage="failed", current_index=index
                ),
                "progress": f"Segment {index + 1}/{len(segments)} failed",
            })
            raise
        completed.append(result)
        completed_indexes.add(index)
        previous_video = Path(result["output_path"])
        manifest = {
            "format": "h3-smart-render-manifest",
            "version": 1,
            "render_policy_version": int(
                job.get("render_policy_version", SMART_RENDER_POLICY_VERSION)
            ),
            "request_kind": job.get("request_kind", "final"),
            "master_seed": job.get("seed"),
            "megapixels": job.get("megapixels"),
            "target_duration_seconds": job.get("target_duration_seconds"),
            "segments": completed + [
                {key: value for key, value in row.items() if key != "workflow"}
                for row in segments[index + 1 :]
            ],
        }
        _write_manifest(manifest_path, manifest)
        emit({
            "segment_status": {
                "segment_id": segment["segment_id"],
                "status": "reusable",
            },
            "segment_completed": result,
            "partial_manifest": manifest,
            "render_progress": build_render_progress(
                job, segments, completed_indexes, stage="complete", current_index=index
            ),
            "progress": f"Segment {index + 1}/{len(segments)} complete · " + release_comfy_memory(server, http_timeout),
        })

    emit({
        "render_progress": build_render_progress(
            job, segments, completed_indexes, stage="assembling"
        ),
        "progress": f"Preparing to assemble {len(completed)} completed segments",
    })
    master = assemble_master(job, completed)
    final_manifest = {
        "format": "h3-smart-render-manifest",
        "version": 1,
        "render_policy_version": int(
            job.get("render_policy_version", SMART_RENDER_POLICY_VERSION)
        ),
        "request_kind": job.get("request_kind", "final"),
        "master_seed": job.get("seed"),
        "megapixels": job.get("megapixels"),
        "target_duration_seconds": job.get("target_duration_seconds"),
        "master_output": str(master),
        "segments": completed,
    }
    _write_manifest(manifest_path, final_manifest)
    emit({
        "smart_render": True,
        "queued": {"prompt_id": "smart-render-master"},
        "completed": True,
        "outputs": [{"kind": "videos", "local_path": str(master)}],
        "master_output": str(master),
        "manifest": final_manifest,
        "request_kind": job.get("request_kind", "final"),
        "seed": job.get("seed"),
        "megapixels": job.get("megapixels"),
        "render_progress": build_render_progress(
            job, segments, completed_indexes, stage="final"
        ),
    })
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        ValueError,
        RuntimeError,
        TimeoutError,
        subprocess.SubprocessError,
        urllib.error.URLError,
        urllib.error.HTTPError,
    ) as exc:
        emit({"error": str(exc), "smart_render": True})
        raise SystemExit(1)

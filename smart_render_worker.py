"""Run hidden H3 segments sequentially and assemble one continuous master.

This worker intentionally keeps only one ComfyUI prompt in flight while keeping
the H3 model resident across normal Segment boundaries.  It persists a resumable
manifest, can inject a preceding-segment continuity anchor into a free reference
slot, releases memory mid-job only for a real CUDA OOM, and performs one final
ComfyUI model/VRAM release after the assembled Master is complete.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid

from native_speech_guard import NativeSpeechGuard
from datetime import datetime, timezone

from comfy_submit_worker import (
    ComfyConnectionRecoveryTimeout,
    DEFAULT_RECONNECT_TIMEOUT_SECONDS,
    _direct_urlopen,
    _request_json,
    download_outputs,
    upload_file,
    wait_for_history,
)
from native_audio_engine import CINEMATIC_DIALOGUE_ACOUSTIC_INTEGRATION_CONTRACT
from workflow_engine import validate_portable_media_manifest


VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
MINIMUM_FREE_DISK_BYTES = 2 * 1024**3
SMART_RENDER_POLICY_VERSION = 32
AUDIO_JOIN_FADE_SECONDS = 0.04
LOCATION_SOUND_REFERENCE_VERSION = 1
COMPLETE_LOCATION_SOUND_CONTRACT = (
    "COMPLETE LOCATION-SOUND REFERENCE CONTRACT — MANDATORY. The supplied authored "
    "speech Audio reference is one authoritative, already synchronized production "
    "recording containing the exact authored words together with continuous native "
    "ambience and physical Foley in one acoustic space. Preserve the entire reference "
    "soundtrack continuously, including its environment before, under, between and "
    "after spoken words. Never isolate the voice, denoise or gate the ambience, replace "
    "non-speech intervals with silence, duplicate dialogue, paraphrase words or invent "
    "narration. Additional visible contact sounds may be generated only when physically "
    "required by the picture and must join the same acoustic space. "
)


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
    payload = dict(payload)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def classify_generation_error(error: object) -> str:
    """Classify retry/failure evidence without weakening output quality."""
    text = str(error or "").casefold()
    if any(
        marker in text
        for marker in (
            "out of memory",
            "oom",
            "cuda oom",
            "allocation on device",
            "not enough memory",
            "memory allocation",
        )
    ):
        return "oom"
    if any(marker in text for marker in ("timed out", "timeout")):
        return "timeout"
    if any(
        marker in text
        for marker in (
            "connection reset",
            "connection refused",
            "connection did not recover",
            "remote end closed",
            "temporarily unavailable",
            "urlopen error",
        )
    ):
        return "transport"
    if any(
        marker in text
        for marker in ("no such file", "missing media", "produced no downloadable video")
    ):
        return "media"
    return "unknown"


def preflight_smart_render(job: dict) -> dict:
    """Fail before media upload if a long render cannot complete on this host."""
    segments = list(job.get("segments") or [])
    if not segments:
        raise ValueError("Smart Render requires at least one internal segment.")
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

    missing_media = []
    for item in job.get("media", []):
        raw_path = item.get("path", "") if isinstance(item, dict) else item
        media_path = Path(str(raw_path))
        if not media_path.is_file():
            missing_media.append(str(media_path))
    if missing_media:
        preview = "\n".join(missing_media[:8])
        raise FileNotFoundError(
            "Reference media is missing before ComfyUI upload. Re-link the "
            "Media Pool source or reopen the portable project folder:\n" + preview
        )
    final_hold_plate = str(job.get("final_hold_plate", "")).strip()
    if final_hold_plate and not Path(final_hold_plate).is_file():
        raise FileNotFoundError(
            "Immutable P1 final-hold plate is missing before render: "
            + final_hold_plate
        )

    manifest_rows = [
        item for item in (job.get("media") or []) if isinstance(item, dict)
    ]
    for segment in segments:
        continuity = segment.get("continuity") or {}
        runtime_ids = (
            {str(continuity.get("loader_node_id"))}
            if continuity.get("loader_node_id")
            else set()
        )
        validate_portable_media_manifest(
            segment.get("workflow") or {},
            manifest_rows,
            runtime_loader_node_ids=runtime_ids,
        )

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
    # The preceding tail exists strictly as visual motion context.  Even a
    # loader capable of exposing synchronized sound must never feed old audio
    # into the next H3 segment, where it can duplicate dialogue or create an
    # audible tail.
    if bool(continuity.get("visual_only", False)):
        _canonicalize_reference_input_order(h3_node)
        return
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


def _h3_prompt_nodes(workflow: dict) -> tuple[dict, dict] | tuple[None, None]:
    """Return the H3 generation node and its connected text node."""

    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        if "MiniMaxH3" not in str(node.get("class_type", "")):
            continue
        connection = (node.get("inputs") or {}).get("prompt")
        if not isinstance(connection, list) or not connection:
            continue
        prompt_node = workflow.get(str(connection[0]))
        if isinstance(prompt_node, dict):
            return node, prompt_node
    return None, None


def _prompt_section(prompt: str, heading: str) -> str:
    pattern = re.compile(
        rf"(?ims)^{re.escape(heading)}:\s*(.*?)(?=^[a-z_]+:\s*$|\Z)"
    )
    match = pattern.search(str(prompt or ""))
    return match.group(1).strip() if match else ""


def build_native_ambience_workflow(
    workflow: dict,
    *,
    duration_seconds: float,
    cache_token: str,
) -> dict:
    """Create a low-cost, speech-free H3 pass that generates native location sound.

    A dry TTS stem is a strong acoustic condition: real H3 tests showed that merely
    asking for ambience, or even adding a second ambience Audio reference, still lets
    the dry stem gate the location bed.  This auxiliary pass deliberately has no Audio
    reference.  Its output audio becomes part of one complete reference before the
    final H3 request.
    """

    result = deepcopy(workflow)
    h3_node, prompt_node = _h3_prompt_nodes(result)
    if h3_node is None or prompt_node is None:
        raise RuntimeError("Could not locate the MiniMax H3 prompt connection.")

    h3_inputs = h3_node.setdefault("inputs", {})
    for key in list(h3_inputs):
        if key.startswith("ref_audios.ref_audio_") or key.startswith(
            "ref_video_audios.ref_video_audio_"
        ):
            h3_inputs.pop(key, None)
    _canonicalize_reference_input_order(h3_node)

    original = str((prompt_node.get("inputs") or {}).get("value", ""))
    visual_definitions = "\n".join(
        line
        for line in _prompt_section(original, "subject_definitions").splitlines()
        if not re.match(r"\s*<Audio\s+\d+>", line, re.I)
    ).strip()
    soundscape = _prompt_section(original, "overall_soundscape")
    # The opening soundscape paragraph carries the scene acoustics. Timestamped
    # Native Audio blocks also repeat authored-speaker instructions, so they are
    # intentionally excluded from this speech-free pass.
    soundscape = re.split(r"(?im)^\[Native Audio\b", soundscape, maxsplit=1)[0].strip()
    if not soundscape:
        soundscape = (
            "Continuous room tone or outdoor atmosphere derived from the visible "
            "location, with picture-motivated movement, surface contact and object Foley."
        )
    duration = max(0.01, float(duration_seconds))
    prompt_node.setdefault("inputs", {})["value"] = (
        "subject_definitions:\n"
        + visual_definitions
        + "\n\nsummary:\nCreate a speech-free native location-sound pass for the exact "
        f"same scene and duration ({duration:.3f} seconds). All visible people remain "
        "silent with closed non-speaking mouths. Preserve the active visual references "
        "only to infer the correct physical environment and synchronized non-vocal Foley.\n\n"
        "detailed_description:\nHUMAN VOCAL CHANNEL: EMPTY. No dialogue, narration, "
        "voice-over, lyrics, singing, whisper, gasp, laugh, chant, intelligible crowd "
        "voice or spoken word in any language. Generate only real diegetic atmosphere, "
        "weather, room tone, material contact, movement and object sounds. The continuous "
        "environment bed begins on frame one, remains clearly audible through every frame "
        "and never gates or drops to digital silence. No non-diegetic music.\n\n"
        "overall_soundscape:\n"
        + soundscape
        + "\nContinuous non-vocal ambience and physically synchronized Foley only; no human voice.\n\n"
        "non_diegetic_music:\nN/A"
    )

    # Audio behavior is independent of final image resolution.  The verified 0.2 MP
    # pass is materially faster and its picture is discarded after audio extraction.
    for node in result.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs") or {}
        if isinstance(inputs.get("megapixels"), (int, float)):
            inputs["megapixels"] = min(0.2, float(inputs["megapixels"]))
        if isinstance(inputs.get("resize_type.scale"), (int, float)):
            inputs["resize_type.scale"] = 1.0
        if str(node.get("class_type", "")) == "SaveVideo":
            inputs["filename_prefix"] = f"video/H3_native_ambience_{cache_token}"
    return result


def patch_complete_location_reference(
    workflow: dict,
    *,
    loader_node_id: str,
    upload_name: str,
) -> None:
    """Replace the dry TTS loader with one complete on-location audio reference."""

    loader = workflow.get(str(loader_node_id))
    if not isinstance(loader, dict) or str(loader.get("class_type", "")) != "LoadAudio":
        raise RuntimeError("The authored TTS LoadAudio node is unavailable.")
    loader.setdefault("inputs", {})["audio"] = str(upload_name)
    _h3_node, prompt_node = _h3_prompt_nodes(workflow)
    if prompt_node is None:
        raise RuntimeError("Could not locate the MiniMax H3 prompt text node.")
    original = str((prompt_node.get("inputs") or {}).get("value", ""))
    if "COMPLETE LOCATION-SOUND REFERENCE CONTRACT" not in original:
        prompt_node.setdefault("inputs", {})["value"] = (
            COMPLETE_LOCATION_SOUND_CONTRACT
            + CINEMATIC_DIALOGUE_ACOUSTIC_INTEGRATION_CONTRACT
            + "\n\n"
            + original
        )


def _extract_video_audio(ffmpeg: Path, source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(source), "-vn", "-ac", "2", "-ar", "32000",
            "-c:a", "pcm_s16le", str(destination),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    if completed.returncode or not destination.is_file() or destination.stat().st_size <= 44:
        detail = completed.stderr.decode("utf-8", errors="replace")[-1200:]
        raise RuntimeError("Could not extract H3 native ambience: " + detail)
    return destination


def _audio_mean_volume_db(ffmpeg: Path, source: Path) -> float:
    completed = subprocess.run(
        [
            str(ffmpeg), "-hide_banner", "-i", str(source),
            "-af", "volumedetect", "-f", "null", "NUL",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    report = completed.stderr.decode("utf-8", errors="replace")
    match = re.search(r"mean_volume:\s*(-?(?:inf|\d+(?:\.\d+)?))\s*dB", report, re.I)
    if not match or match.group(1).casefold() == "-inf":
        return float("-inf")
    return float(match.group(1))


def _mix_complete_location_reference(
    ffmpeg: Path,
    *,
    speech: Path,
    ambience: Path,
    destination: Path,
    duration_seconds: float,
    ambience_gain: float,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.01, float(duration_seconds))
    gain = max(0.05, min(1.5, float(ambience_gain)))
    filter_graph = (
        f"[0:a]aresample=32000,apad=whole_dur={duration:.6f},"
        f"atrim=duration={duration:.6f},volume=1.0[voice];"
        f"[1:a]aresample=32000,apad=whole_dur={duration:.6f},"
        f"atrim=duration={duration:.6f},volume={gain:.4f}[amb];"
        "[voice][amb]amix=inputs=2:duration=longest:normalize=0,"
        "alimiter=limit=0.95[mix]"
    )
    completed = subprocess.run(
        [
            str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(speech), "-i", str(ambience),
            "-filter_complex", filter_graph, "-map", "[mix]", "-t", f"{duration:.6f}",
            "-ac", "2", "-ar", "32000", "-c:a", "pcm_s16le", str(destination),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    if completed.returncode or not destination.is_file() or destination.stat().st_size <= 44:
        detail = completed.stderr.decode("utf-8", errors="replace")[-1200:]
        raise RuntimeError("Could not build complete location-sound reference: " + detail)
    return destination


def _queue_auxiliary_workflow(
    job: dict,
    segment: dict,
    workflow: dict,
    destination: Path,
) -> Path:
    server = str(job["server"]).rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    reconnect_timeout = max(
        1, int(job.get("connection_recovery_timeout", DEFAULT_RECONNECT_TIMEOUT_SECONDS))
    )
    payload = json.dumps(
        {"prompt": workflow, "client_id": "h3-native-ambience-" + uuid.uuid4().hex},
        ensure_ascii=False,
    ).encode("utf-8")
    queued = _request_json(
        urllib.request.Request(
            server + "/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        ),
        http_timeout,
    )
    prompt_id = str(queued.get("prompt_id", ""))
    if not prompt_id:
        raise RuntimeError("ComfyUI did not return a prompt_id for native ambience.")
    emit({
        "progress": (
            f"Segment {segment['index'] + 1}/{job['segment_count']} · "
            f"native ambience pass queued · {prompt_id}"
        ),
        "segment_index": segment["index"],
        "native_ambience_prompt_id": prompt_id,
    })
    _history, outputs = wait_for_history(
        server,
        prompt_id,
        poll_interval=max(0.1, float(job.get("history_poll_interval", 1.0))),
        generation_timeout=max(10, int(job.get("generation_timeout", 1800))),
        http_timeout=http_timeout,
        reconnect_timeout=reconnect_timeout,
        segment_id=str(segment.get("segment_id", "")) + ":native-ambience",
    )
    downloaded = download_outputs(
        server,
        outputs,
        destination,
        http_timeout,
        reconnect_timeout=reconnect_timeout,
        prompt_id=prompt_id,
        segment_id=str(segment.get("segment_id", "")) + ":native-ambience",
    )
    video = _primary_video(downloaded)
    if video is None:
        raise RuntimeError("Native ambience pass produced no downloadable video.")
    return video


def prepare_complete_location_sound_reference(
    job: dict,
    segment: dict,
    workflow: dict,
) -> dict | None:
    """Generate/cache ambience, combine it with TTS, and patch the final H3 graph."""

    spec = dict(segment.get("location_sound_reference") or {})
    if not bool(spec.get("enabled")):
        return None
    speech = Path(str(spec.get("speech_path", "")))
    if not speech.is_file() or speech.stat().st_size <= 44:
        raise FileNotFoundError("Authored segment TTS is missing: " + str(speech))
    ambience = Path(str(spec.get("ambience_cache_path", "")))
    complete = Path(str(spec.get("complete_cache_path", "")))
    duration = max(0.01, float(spec.get("duration_seconds", 0.0)))
    token = str(spec.get("cache_token", "location"))
    ffmpeg = Path(str(job.get("ffmpeg", "")))

    ambience_valid = (
        ambience.is_file()
        and ambience.stat().st_size > 44
        and _audio_mean_volume_db(ffmpeg, ambience) > -55.0
    )
    if not ambience_valid:
        ambience.unlink(missing_ok=True)
        last_ambience_error: Exception | None = None
        for ambience_attempt in range(1, 3):
            try:
                ambience_workflow = build_native_ambience_workflow(
                    workflow, duration_seconds=duration, cache_token=token
                )
                ambience_workflow = _workflow_for_attempt(
                    ambience_workflow,
                    int(segment.get("seed", 0) or 0),
                    ambience_attempt,
                )
                auxiliary_dir = ambience.parent / (
                    ambience.stem + f"_render_{ambience_attempt}"
                )
                video = _queue_auxiliary_workflow(
                    job, segment, ambience_workflow, auxiliary_dir
                )
                _extract_video_audio(ffmpeg, video, ambience)
                mean_db = _audio_mean_volume_db(ffmpeg, ambience)
                if mean_db <= -55.0:
                    raise RuntimeError(
                        f"H3 native ambience is effectively silent ({mean_db:.1f} dB)."
                    )
                emit({
                    "progress": (
                        f"Segment {segment['index'] + 1}/{job['segment_count']} · "
                        f"native ambience cached ({mean_db:.1f} dB mean)"
                    ),
                    "segment_index": segment["index"],
                })
                last_ambience_error = None
                break
            except Exception as exc:
                last_ambience_error = exc
                ambience.unlink(missing_ok=True)
                if ambience_attempt < 2:
                    emit({
                        "progress": (
                            f"Segment {segment['index'] + 1}/{job['segment_count']} · "
                            "native ambience was unavailable or silent; retrying once"
                        ),
                        "segment_index": segment["index"],
                    })
        if last_ambience_error is not None:
            raise RuntimeError(
                "Could not create an audible native location bed after two attempts: "
                + str(last_ambience_error)
            )

    if not complete.is_file() or complete.stat().st_size <= 44:
        _mix_complete_location_reference(
            ffmpeg,
            speech=speech,
            ambience=ambience,
            destination=complete,
            duration_seconds=duration,
            ambience_gain=float(spec.get("ambience_gain", 0.55)),
        )

    server = str(job["server"]).rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    desired_name = str(spec.get("upload_name") or complete.name)
    uploaded = upload_file(server, complete, http_timeout, desired_name)
    remote_name = str((uploaded or {}).get("name") or desired_name)
    patch_complete_location_reference(
        workflow,
        loader_node_id=str(spec.get("loader_node_id", "")),
        upload_name=remote_name,
    )
    emit({
        "progress": (
            f"Segment {segment['index'] + 1}/{job['segment_count']} · "
            "complete dialogue + location-sound reference attached"
        ),
        "segment_index": segment["index"],
    })
    return {
        "file": complete.name,
        "upload_name": remote_name,
        "result": uploaded,
        "kind": "complete_location_sound_reference",
    }


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
            audio_filters = [
                f"[{index}:a]atrim=start={trim:.6f}:end={trim_end:.6f}",
                "asetpts=PTS-STARTPTS",
            ]
            fade = min(AUDIO_JOIN_FADE_SECONDS, core_duration / 4.0)
            if index > 0 and fade > 0.0:
                audio_filters.append(f"afade=t=in:st=0:d={fade:.6f}")
            if index < len(segments) - 1 and fade > 0.0:
                audio_filters.append(
                    f"afade=t=out:st={max(0.0, core_duration - fade):.6f}:d={fade:.6f}"
                )
            filters.append(
                ",".join(audio_filters) + f"[a{index}]"
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
    # Preserve the assembled native ending, including for older saved jobs.
    return destination.resolve()


def _workflow_for_attempt(workflow: dict, base_seed: int, attempt: int) -> dict:
    """Return a deterministic fresh-seed workflow for a speech-guard retry."""

    result = deepcopy(workflow)
    if attempt <= 1:
        return result
    digest = hashlib.sha256(
        f"native-speech-guard:{int(base_seed)}:{int(attempt)}".encode("utf-8")
    ).digest()
    retry_seed = int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)
    for node in result.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs") or {}
        if not isinstance(inputs, dict):
            continue
        if isinstance(inputs.get("noise_seed"), int):
            inputs["noise_seed"] = retry_seed
        elif isinstance(inputs.get("seed"), int):
            inputs["seed"] = retry_seed
    return result


def speech_guard_result_score(result: dict) -> float:
    """Rank failed guarded takes so retry exhaustion keeps the least-bad take.

    The guard remains non-blocking, but returning the final random retry made a
    mildly imperfect first take regress into a take with a long invented line.
    Lower scores are better; a passing take always wins immediately.
    """

    if bool(result.get("passed", True)):
        return 0.0
    score = 0.0
    weights = {
        "unauthorized_speech_in_silence_window": 200.0,
        "materially_changed_or_unrelated_authored_line": 175.0,
        "unauthorized_extra_inside_authored_window": 125.0,
        "repeated_authored_phrase": 100.0,
    }
    violations = [row for row in (result.get("violations") or []) if isinstance(row, dict)]
    for row in violations:
        score += weights.get(str(row.get("kind", "")), 150.0)
        transcript = re.sub(r"\s+", "", str(row.get("transcript", "")))
        score += min(80.0, float(len(transcript)) * 2.0)
        score += min(30.0, max(0.0, float(row.get("voice_ratio", 0.0))) * 30.0)
    return score if violations else 1.0


def queue_segment(
    job: dict,
    segment: dict,
    workflow: dict,
    uploaded: list[dict],
    *,
    on_queued=None,
    speech_guard: NativeSpeechGuard | None = None,
) -> dict:
    server = job["server"].rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    attempts = max(1, min(5, int(job.get("segment_attempts", 3))))
    reconnect_timeout = max(
        1,
        int(job.get("connection_recovery_timeout", DEFAULT_RECONNECT_TIMEOUT_SECONDS)),
    )
    last_error: Exception | None = None
    resumed_prompt_id = str(segment.get("prompt_id", "")).strip()
    resume_status = str(segment.get("status", "")).strip().lower()
    resume_existing = bool(
        resumed_prompt_id
        and resume_status in {"queued", "monitoring", "reconnecting", "running"}
    )
    first_attempt = max(1, int(segment.get("attempts_used", 1) or 1))
    attempt_range = [first_attempt] if resume_existing else range(1, attempts + 1)
    guarded_candidates: list[dict] = []
    for attempt in attempt_range:
        prompt_id = resumed_prompt_id if resume_existing else ""
        attempt_workflow = _workflow_for_attempt(
            workflow, int(segment.get("seed", 0) or 0), attempt
        )
        try:
            if resume_existing:
                emit({
                    "progress": (
                        f"Segment {segment['index'] + 1}/{job['segment_count']} resumed from "
                        f"server prompt · {prompt_id}"
                    ),
                    "segment_index": segment["index"],
                    "connection_state": "reconnected",
                    "segment_status": {
                        "segment_id": segment["segment_id"],
                        "status": "running",
                        "prompt_id": prompt_id,
                    },
                })
            else:
                payload = json.dumps(
                    {
                        "prompt": attempt_workflow,
                        "client_id": "h3-smart-render-" + uuid.uuid4().hex,
                    },
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
                if on_queued is not None:
                    on_queued(prompt_id, attempt, queued)
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
                reconnect_timeout=reconnect_timeout,
                segment_id=str(segment.get("segment_id", "")),
            )
            downloaded = download_outputs(
                server,
                outputs,
                Path(segment["download_dir"]),
                http_timeout,
                reconnect_timeout=reconnect_timeout,
                prompt_id=prompt_id,
                segment_id=str(segment.get("segment_id", "")),
            )
            video = _primary_video(downloaded)
            if video is None:
                raise RuntimeError(f"Segment {segment['index'] + 1} produced no downloadable video.")
            speech_guard_result: dict = {}
            speech_guard_spec = dict(segment.get("native_speech_guard") or {})
            if speech_guard is not None and speech_guard_spec.get("enabled"):
                emit({
                    "progress": (
                        f"Segment {segment['index'] + 1}/{job['segment_count']} · "
                        "checking authored-line fidelity and unauthorized speech gaps"
                    ),
                    "segment_index": segment["index"],
                })
                speech_guard_result = speech_guard.inspect(video, speech_guard_spec)
                if not bool(speech_guard_result.get("passed", True)):
                    snapshot = Path(segment["download_dir"]) / (
                        f".speech_guard_attempt_{attempt}_{Path(video).name}"
                    )
                    shutil.copy2(video, snapshot)
                    guarded_candidates.append({
                        "attempt": attempt,
                        "score": speech_guard_result_score(speech_guard_result),
                        "snapshot": snapshot,
                        "prompt_id": prompt_id,
                        "history_status": history.get("status", {}),
                        "result": deepcopy(speech_guard_result),
                    })
                guard_retries = max(
                    0,
                    min(
                        attempts - 1,
                        int(
                            job.get(
                                "native_speech_guard_retries",
                                job.get("native_speech_guard_attempts", 2),
                            )
                        ),
                    ),
                )
                guard_attempts = 1 + guard_retries
                if not bool(speech_guard_result.get("passed", True)):
                    violation_preview = "; ".join(
                        str(row.get("transcript", ""))[:80]
                        for row in speech_guard_result.get("violations") or []
                    )
                    if attempt < guard_attempts and not resume_existing:
                        emit({
                            "progress": (
                                f"Segment {segment['index'] + 1}/{job['segment_count']} "
                                "contained repeated or unauthorized H3 speech; retrying with a fresh seed · "
                                + violation_preview
                            ),
                            "segment_index": segment["index"],
                            "native_speech_guard": speech_guard_result,
                            "attempt": attempt,
                            "attempts": guard_attempts,
                        })
                        time.sleep(0.25)
                        continue
                    emit({
                        "progress": (
                            f"Segment {segment['index'] + 1}/{job['segment_count']} "
                            "speech guard warning; retry budget exhausted, continuing without "
                            "Hard Block"
                        ),
                        "segment_index": segment["index"],
                        "native_speech_guard": speech_guard_result,
                    })
                    best = min(
                        guarded_candidates,
                        key=lambda row: (float(row["score"]), int(row["attempt"])),
                    )
                    shutil.copy2(best["snapshot"], video)
                    prompt_id = str(best["prompt_id"])
                    speech_guard_result = dict(best["result"])
                    history = {"status": dict(best["history_status"])}
                    emit({
                        "progress": (
                            f"Segment {segment['index'] + 1}/{job['segment_count']} "
                            f"kept guarded take {best['attempt']} as the least-risk result "
                            f"after {attempt} attempts"
                        ),
                        "segment_index": segment["index"],
                        "selected_guard_attempt": int(best["attempt"]),
                        "native_speech_guard": speech_guard_result,
                    })
                else:
                    best = None
                for candidate in guarded_candidates:
                    Path(candidate["snapshot"]).unlink(missing_ok=True)
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
                "attempts_used": attempt,
                "selected_guard_attempt": (
                    int(best["attempt"]) if speech_guard_result and best is not None else attempt
                ),
                "failure_class": "",
                "native_speech_guard_result": speech_guard_result,
            }
        except Exception as exc:
            last_error = exc
            failure_class = classify_generation_error(exc)
            emit({
                "progress": f"Segment {segment['index'] + 1} attempt {attempt}/{attempts} failed: {exc}",
                "segment_index": segment["index"],
                "failure_class": failure_class,
                "attempt": attempt,
                "attempts": attempts,
            })
            # The remote server may still be rendering this accepted prompt.
            # Never submit a duplicate merely because the monitoring channel
            # exceeded its recovery window; preserve prompt_id for later resume.
            if isinstance(exc, ComfyConnectionRecoveryTimeout):
                raise
            if failure_class == "oom":
                released = release_comfy_memory(server, http_timeout)
                emit({
                    "progress": (
                        f"{released} · CUDA OOM retry"
                        if attempt < attempts
                        else f"{released} · CUDA OOM retry budget exhausted"
                    ),
                    "failure_class": failure_class,
                })
            else:
                emit({
                    "progress": (
                        f"H3 kept resident · retry class {failure_class}"
                        if attempt < attempts
                        else f"H3 kept resident · retry budget exhausted ({failure_class})"
                    ),
                    "failure_class": failure_class,
                })
            if attempt < attempts:
                # OOM often needs a little longer for ComfyUI/PyTorch to return
                # released allocations to the driver. Never lower megapixels
                # or silently change the accepted quality contract.
                time.sleep(2.0 if failure_class == "oom" else 1.0)
        finally:
            resume_existing = False
    raise RuntimeError(str(last_error or "Unknown segment generation error"))


def uploaded_media_for_workflow(workflow: dict, uploaded: list[dict]) -> list[dict]:
    """Return only uploads actually referenced by this Segment workflow.

    Files may be uploaded once for the whole job, but the manifest is a
    mapping audit.  Recording the global upload union on every Segment made
    inactive Pictures appear active and concealed reference-slot leaks.
    """
    referenced: set[str] = set()
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs") or {}
        if not isinstance(inputs, dict):
            continue
        for value in inputs.values():
            if isinstance(value, str):
                referenced.add(value.replace("\\", "/").rsplit("/", 1)[-1])
    return [
        row for row in uploaded
        if str(row.get("upload_name") or row.get("file") or "")
        .replace("\\", "/").rsplit("/", 1)[-1] in referenced
    ]


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

    speech_guard: NativeSpeechGuard | None = None
    if any(
        bool((segment.get("native_speech_guard") or {}).get("enabled"))
        for segment in segments
    ):
        speech_guard = NativeSpeechGuard(
            str(job.get("native_speech_guard_model", "")),
            str(job.get("ffmpeg", "")),
        )
        emit({
            "progress": (
                "Native Speech Guard armed · Whisper checks only unauthorized "
                "human-vocal gaps · no Hard Block"
            )
        })

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
        resume_existing = bool(
            str(segment.get("prompt_id", "")).strip()
            and str(segment.get("status", "")).strip().lower()
            in {"queued", "monitoring", "reconnecting", "running"}
        )
        continuity = segment.get("continuity") or {}
        if previous_video is not None and continuity and not resume_existing:
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

        # External authored TTS is intentionally dry and, in real H3 API tests,
        # suppresses native ambience even when the prompt explicitly requires it.
        # Before queuing the final Segment, create one complete production-sound
        # reference (exact TTS + H3-native speech-free ambience). A reconnecting
        # final prompt is already accepted by ComfyUI and must not be altered.
        if not resume_existing:
            location_upload = prepare_complete_location_sound_reference(
                job, segment, workflow
            )
            if location_upload is not None:
                uploaded.append(location_upload)

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
            def checkpoint_queued(prompt_id: str, attempt: int, queued: dict) -> None:
                pending = {
                    key: value for key, value in segment.items() if key != "workflow"
                }
                pending.update(
                    status="monitoring",
                    prompt_id=prompt_id,
                    attempts_used=attempt,
                    queued_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    error="",
                    failure_class="",
                )
                checkpoint_manifest = {
                    "format": "h3-smart-render-manifest",
                    "version": 1,
                    "render_policy_version": int(
                        job.get("render_policy_version", SMART_RENDER_POLICY_VERSION)
                    ),
                    "server": server,
                    "request_kind": job.get("request_kind", "final"),
                    "master_seed": job.get("seed"),
                    "megapixels": job.get("megapixels"),
                    "target_duration_seconds": job.get("target_duration_seconds"),
                    "active_prompt_id": prompt_id,
                    "segments": completed + [pending] + [
                        {key: value for key, value in row.items() if key != "workflow"}
                        for row in segments[index + 1 :]
                    ],
                }
                _write_manifest(manifest_path, checkpoint_manifest)
                emit({
                    "segment_status": {
                        "segment_id": segment["segment_id"],
                        "status": "running",
                        "prompt_id": prompt_id,
                    },
                    "partial_manifest": checkpoint_manifest,
                    "connection_state": "monitoring",
                    "progress": (
                        f"Segment {index + 1}/{len(segments)} server Job checkpointed · "
                        f"prompt_id {prompt_id}"
                    ),
                })

            result = queue_segment(
                job,
                segment,
                workflow,
                uploaded_media_for_workflow(workflow, uploaded),
                on_queued=checkpoint_queued,
                speech_guard=speech_guard,
            )
        except Exception as exc:
            failure_class = classify_generation_error(exc)
            failed = {
                key: value for key, value in segment.items() if key != "workflow"
            }
            recovery_pending = isinstance(exc, ComfyConnectionRecoveryTimeout)
            accepted_prompt_id = (
                str(getattr(exc, "prompt_id", ""))
                or str(segment.get("prompt_id", ""))
            )
            failed.update(
                status="monitoring" if recovery_pending else "failed",
                error=str(exc),
                failure_class=failure_class,
                retry_budget=max(1, min(5, int(job.get("segment_attempts", 3)))),
            )
            if accepted_prompt_id:
                failed["prompt_id"] = accepted_prompt_id
            manifest = {
                "format": "h3-smart-render-manifest",
                "version": 1,
                "render_policy_version": int(
                    job.get("render_policy_version", SMART_RENDER_POLICY_VERSION)
                ),
                "server": server,
                "request_kind": job.get("request_kind", "final"),
                "master_seed": job.get("seed"),
                "megapixels": job.get("megapixels"),
                "target_duration_seconds": job.get("target_duration_seconds"),
                "active_prompt_id": accepted_prompt_id if recovery_pending else "",
                "segments": completed + [failed] + [
                    {key: value for key, value in row.items() if key != "workflow"}
                    for row in segments[index + 1 :]
                ],
            }
            _write_manifest(manifest_path, manifest)
            emit({
                "segment_status": {
                    "segment_id": segment["segment_id"],
                    "status": "reconnecting" if recovery_pending else "failed",
                    "error": str(exc),
                    "failure_class": failure_class,
                },
                "partial_manifest": manifest,
                "render_progress": build_render_progress(
                    job,
                    segments,
                    completed_indexes,
                    stage="reconnecting" if recovery_pending else "failed",
                    current_index=index,
                ),
                "progress": (
                    f"Segment {index + 1}/{len(segments)} saved for prompt reconnect"
                    if recovery_pending
                    else f"Segment {index + 1}/{len(segments)} failed"
                ),
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
            "server": server,
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
            "progress": (
                f"Segment {index + 1}/{len(segments)} complete · "
                "H3 kept resident for the next Segment"
            ),
        })

    emit({
        "render_progress": build_render_progress(
            job, segments, completed_indexes, stage="assembling"
        ),
        "progress": f"Preparing to assemble {len(completed)} completed segments",
    })
    master = assemble_master(job, completed)
    final_release = release_comfy_memory(server, http_timeout)
    final_manifest = {
        "format": "h3-smart-render-manifest",
        "version": 1,
        "render_policy_version": int(
            job.get("render_policy_version", SMART_RENDER_POLICY_VERSION)
        ),
        "server": server,
        "request_kind": job.get("request_kind", "final"),
        "master_seed": job.get("seed"),
        "megapixels": job.get("megapixels"),
        "target_duration_seconds": job.get("target_duration_seconds"),
        "master_output": str(master),
        "final_model_release": final_release,
        "segments": completed,
    }
    _write_manifest(manifest_path, final_manifest)
    # The full workflow-bearing job can be large. Keep it only for interrupted
    # recovery; a successful final manifest is the compact durable record.
    Path(args.job).unlink(missing_ok=True)
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
        "progress": f"Master complete · {final_release}",
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

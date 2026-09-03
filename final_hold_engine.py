"""Deterministically replace a video's last frames with an approved still plate."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


def _video_geometry(ffprobe: Path, source: Path) -> tuple[int, int, float]:
    completed = subprocess.run(
        [
            str(ffprobe), "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height:format=duration",
            "-of", "json", str(source),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode:
        raise RuntimeError("Could not inspect final-hold video: " + completed.stderr[-800:])
    payload = json.loads(completed.stdout or "{}")
    stream = next(iter(payload.get("streams") or []), {})
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    duration = float((payload.get("format") or {}).get("duration") or 0.0)
    if width <= 0 or height <= 0 or duration <= 0.0:
        raise RuntimeError("Final-hold video has no readable geometry or duration.")
    return width, height, duration


def build_final_hold_command(
    ffmpeg: Path,
    ffprobe: Path,
    source: Path,
    plate: Path,
    destination: Path,
    *,
    hold_seconds: float = 1.0,
    target_duration: float | None = None,
) -> list[str]:
    """Build an effect-only tail overlay that preserves the source audio stream."""

    if not source.is_file():
        raise FileNotFoundError(f"Final-hold source video is missing: {source}")
    if not plate.is_file():
        raise FileNotFoundError(f"Immutable final-hold plate is missing: {plate}")
    width, height, source_duration = _video_geometry(ffprobe, source)
    duration = source_duration
    if target_duration is not None and float(target_duration) > 0.0:
        duration = min(source_duration, float(target_duration))
    hold = min(max(0.04, float(hold_seconds)), duration)
    start = max(0.0, duration - hold)
    filter_graph = (
        f"[1:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1[plate];"
        f"[0:v][plate]overlay=0:0:enable='gte(t,{start:.6f})'[vout]"
    )
    return [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-loop", "1", "-framerate", "24", "-i", str(plate),
        "-filter_complex", filter_graph,
        "-map", "[vout]", "-map", "0:a?",
        "-t", f"{duration:.6f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
        str(destination),
    ]


def apply_final_hold_plate(
    ffmpeg: Path,
    ffprobe: Path,
    source: Path,
    plate: Path,
    *,
    hold_seconds: float = 1.0,
    target_duration: float | None = None,
) -> Path:
    """Apply the immutable plate atomically; no duplicate production MP4 remains."""

    source = source.resolve()
    temporary = source.with_name(f"{source.stem}.{os.getpid()}.final-hold.mp4")
    temporary.unlink(missing_ok=True)
    command = build_final_hold_command(
        ffmpeg,
        ffprobe,
        source,
        plate.resolve(),
        temporary,
        hold_seconds=hold_seconds,
        target_duration=target_duration,
    )
    completed = subprocess.run(command, capture_output=True, text=True, timeout=1800)
    if completed.returncode or not temporary.is_file():
        temporary.unlink(missing_ok=True)
        raise RuntimeError("Could not apply immutable final hold: " + completed.stderr[-1200:])
    os.replace(temporary, source)
    return source

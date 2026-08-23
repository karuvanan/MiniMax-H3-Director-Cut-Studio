"""FFmpeg/Pillow helpers used by the Director Cut media panels."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

from PIL import Image

from runtime_paths import RuntimePaths, load_runtime_paths


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".aac", ".m4a", ".flac", ".ogg", ".opus"}


def media_type_for_path(path: str | Path) -> str | None:
    suffix = Path(path).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    return None


def _run(command: list[str], timeout: int = 45) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def probe_media(path: str | Path, runtime: RuntimePaths | None = None) -> dict[str, Any]:
    source = Path(path)
    kind = media_type_for_path(source)
    if kind == "image":
        with Image.open(source) as image:
            return {
                "media_type": "image",
                "format": image.format or source.suffix.lstrip(".").upper(),
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "duration": 0.0,
                "size_bytes": source.stat().st_size,
            }

    runtime = runtime or load_runtime_paths()
    result = _run(
        [
            str(runtime.ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration,format_name,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(source),
        ]
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "FFprobe failed")
    payload = json.loads(result.stdout)
    format_info = payload.get("format", {})
    duration = float(format_info.get("duration") or 0.0)
    return {
        "media_type": kind or "unknown",
        "format": format_info.get("format_name", ""),
        "duration": duration,
        "bit_rate": int(format_info.get("bit_rate") or 0),
        "size_bytes": source.stat().st_size,
        "streams": payload.get("streams", []),
    }


def create_video_thumbnail(
    path: str | Path,
    destination: str | Path,
    seek_seconds: float = 0.0,
    runtime: RuntimePaths | None = None,
) -> Path:
    runtime = runtime or load_runtime_paths()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = _run(
        [
            str(runtime.ffmpeg),
            "-y",
            "-ss",
            f"{max(0.0, seek_seconds):.3f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=960:-2:force_original_aspect_ratio=decrease",
            str(destination),
        ]
    )
    if result.returncode or not destination.exists():
        raise RuntimeError(result.stderr.strip() or "Unable to create video thumbnail")
    return destination


def create_video_analysis_frames(
    path: str | Path,
    destination_dir: str | Path,
    duration: float,
    runtime: RuntimePaths | None = None,
) -> list[tuple[str, Path]]:
    """Extract opening, middle and ending frames for temporal visual analysis."""
    runtime = runtime or load_runtime_paths()
    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    duration = max(0.05, duration)
    samples = (("opening 10%", duration * 0.10), ("middle 50%", duration * 0.50), ("ending 90%", duration * 0.90))
    frames: list[tuple[str, Path]] = []
    for index, (label, seconds) in enumerate(samples, 1):
        destination = destination_dir / f"frame_{index}.jpg"
        if not destination.exists():
            create_video_thumbnail(path, destination, seconds, runtime)
        frames.append((f"{label} @ {seconds:.2f}s", destination))
    return frames


def create_audio_waveform(
    path: str | Path,
    destination: str | Path,
    runtime: RuntimePaths | None = None,
    max_seconds: float | None = None,
) -> Path:
    runtime = runtime or load_runtime_paths()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
            str(runtime.ffmpeg),
            "-y",
            "-i",
            str(path),
    ]
    if max_seconds is not None:
        command.extend(["-t", f"{max(0.05, float(max_seconds)):.3f}"])
    command.extend(
        [
            "-filter_complex",
            "aformat=channel_layouts=mono,showwavespic=s=1200x260:colors=0x55D6BE",
            "-frames:v",
            "1",
            str(destination),
        ]
    )
    result = _run(command)
    if result.returncode or not destination.exists():
        raise RuntimeError(result.stderr.strip() or "Unable to create audio waveform")
    return destination


def human_probe_summary(info: dict[str, Any]) -> str:
    size_mb = info.get("size_bytes", 0) / (1024 * 1024)
    lines = [f"Type: {info.get('media_type', 'unknown')}", f"Format: {info.get('format', '-')}"]
    if info.get("media_type") == "image":
        lines.extend(
            [
                f"Frame: {info.get('width', 0)} x {info.get('height', 0)}",
                f"Color: {info.get('mode', '-')}",
            ]
        )
    else:
        lines.append(f"Duration: {info.get('duration', 0.0):.2f}s")
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                lines.append(
                    f"Video: {stream.get('codec_name', '-')}  {stream.get('width', 0)} x {stream.get('height', 0)}  {stream.get('r_frame_rate', '-') } fps"
                )
            elif stream.get("codec_type") == "audio":
                lines.append(
                    f"Audio: {stream.get('codec_name', '-')}  {stream.get('sample_rate', '-')} Hz  {stream.get('channels', '-')} ch"
                )
    lines.append(f"File size: {size_mb:.2f} MB")
    return "\n".join(lines)

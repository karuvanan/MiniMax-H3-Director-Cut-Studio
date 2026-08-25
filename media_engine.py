"""FFmpeg/Pillow helpers used by the Director Cut media panels."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from runtime_paths import RuntimePaths, load_runtime_paths


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".aac", ".m4a", ".flac", ".ogg", ".opus"}


def remove_solid_background(
    source: str | Path,
    destination: str | Path,
    *,
    border_tolerance: int = 22,
    flood_tolerance: int = 36,
    min_border_ratio: float = 0.92,
    feather_radius: float = 0.8,
) -> dict[str, Any] | None:
    """Create a transparent derivative when an image has a uniform backdrop.

    The original file is never modified.  Detection is intentionally strict:
    most sampled edge pixels must agree with one robust background colour,
    then only edge-connected pixels are removed.  Complex photographs are
    returned unchanged instead of risking destructive subject masking.
    """
    source_path = Path(source)
    destination_path = Path(destination)
    with Image.open(source_path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
    if image.width < 8 or image.height < 8:
        return None
    alpha_extrema = image.getchannel("A").getextrema()
    if alpha_extrema[0] < 250:
        return None

    rgb = image.convert("RGB")
    pixels = rgb.load()
    step_x = max(1, image.width // 64)
    step_y = max(1, image.height // 64)
    samples: list[tuple[int, int, int]] = []
    for x in range(0, image.width, step_x):
        samples.extend((pixels[x, 0], pixels[x, image.height - 1]))
    for y in range(step_y, image.height - 1, step_y):
        samples.extend((pixels[0, y], pixels[image.width - 1, y]))
    if not samples:
        return None
    background = tuple(
        sorted(sample[channel] for sample in samples)[len(samples) // 2]
        for channel in range(3)
    )

    def close_to_background(value: tuple[int, int, int]) -> bool:
        return max(abs(value[index] - background[index]) for index in range(3)) <= border_tolerance

    border_ratio = sum(close_to_background(value) for value in samples) / len(samples)
    if border_ratio < min_border_ratio:
        return None

    sentinel = (1, 2, 3)
    if background == sentinel:
        sentinel = (252, 1, 253)
    flood = rgb.copy()
    seeds: list[tuple[int, int]] = []
    seed_count = 16
    for index in range(seed_count + 1):
        x = round(index * (image.width - 1) / seed_count)
        y = round(index * (image.height - 1) / seed_count)
        seeds.extend(((x, 0), (x, image.height - 1), (0, y), (image.width - 1, y)))
    flood_pixels = flood.load()
    for seed in seeds:
        value = flood_pixels[seed[0], seed[1]]
        if value != sentinel and close_to_background(value):
            ImageDraw.floodfill(flood, seed, sentinel, thresh=max(0, flood_tolerance))

    difference = ImageChops.difference(flood, Image.new("RGB", flood.size, sentinel))
    bands = difference.split()
    nonzero = ImageChops.lighter(ImageChops.lighter(bands[0], bands[1]), bands[2])
    alpha = nonzero.point(lambda value: 0 if value == 0 else 255)
    histogram = alpha.histogram()
    removed_ratio = histogram[0] / max(1, image.width * image.height)
    if removed_ratio < 0.08 or removed_ratio > 0.96:
        return None
    if feather_radius > 0:
        alpha = alpha.filter(ImageFilter.GaussianBlur(float(feather_radius)))
    image.putalpha(alpha)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination_path, format="PNG", optimize=True)
    return {
        "path": str(destination_path.resolve()),
        "background_color": list(background),
        "border_consistency": round(border_ratio, 4),
        "removed_ratio": round(removed_ratio, 4),
        "method": "strict_edge_connected_solid_background",
    }


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


def create_image_analysis_regions(
    path: str | Path,
    destination_dir: str | Path,
) -> list[tuple[str, Path]]:
    """Create complementary crops so title cards do not dominate BLIP.

    The full frame remains evidence, while three broad scene crops suppress
    common lower-third captions, corner logos and poster-like typography.  The
    crops deliberately overlap so no single crop is treated as authoritative.
    """

    source = Path(path)
    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    regions: list[tuple[str, Path]] = [("full frame", source)]
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        width, height = image.size
        definitions = (
            ("upper scene excluding lower titles", (0.02, 0.02, 0.98, 0.74)),
            ("central scene excluding edge overlays", (0.08, 0.08, 0.92, 0.78)),
            ("central subject detail", (0.18, 0.12, 0.82, 0.76)),
        )
        for index, (label, bounds) in enumerate(definitions, 1):
            left = max(0, min(width - 1, round(width * bounds[0])))
            top = max(0, min(height - 1, round(height * bounds[1])))
            right = max(left + 1, min(width, round(width * bounds[2])))
            bottom = max(top + 1, min(height, round(height * bounds[3])))
            if right - left < 48 or bottom - top < 48:
                continue
            destination = destination_dir / f"region_{index}.jpg"
            if not destination.is_file():
                image.crop((left, top, right, bottom)).save(
                    destination,
                    format="JPEG",
                    quality=92,
                    optimize=True,
                )
            regions.append((label, destination))
    return regions


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

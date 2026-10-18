"""FFmpeg/Pillow helpers used by the Director Cut media panels."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import shutil
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from runtime_paths import RuntimePaths, load_runtime_paths


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".aac", ".m4a", ".flac", ".ogg", ".opus"}

# Source-Video Cast Remake uses a richer, versioned frame plan than ordinary
# Media Pool video.  Six 4x4 sheets keep each panel readable while giving Qwen
# enough temporal coverage to discover brief performers near either edge of a
# detected source scene.
SOURCE_VIDEO_ROLE_DISCOVERY_PROFILE = "role_discovery_v2"
SOURCE_VIDEO_ROLE_DISCOVERY_MAX_FRAMES = 96
SOURCE_VIDEO_ROLE_DISCOVERY_MAX_SHEETS = 6


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


def plan_scene_analysis_samples(
    scenes: list[tuple[int, float, float]],
    max_frames: int = SOURCE_VIDEO_ROLE_DISCOVERY_MAX_FRAMES,
) -> list[tuple[str, float]]:
    """Plan role-discovery frames without a midpoint-only quality cliff.

    Up to 32 scenes receive early/mid/late coverage.  Medium scene counts keep
    both temporal edges, adding midpoints while capacity remains.  When there
    are more scenes than can receive two frames, every scene keeps one anchor
    and the spare budget is spread chronologically across early/late edges.
    Only an extreme source with more scenes than the complete frame budget is
    uniformly thinned, and even then the retained panels cycle through early,
    midpoint and late instead of sampling every scene at the same phase.
    """

    normalized = [
        (int(index), float(start), float(end))
        for index, start, end in scenes
        if float(end) - float(start) >= 0.12
    ]
    if not normalized:
        return []
    budget = max(3, int(max_frames))

    def evenly_selected_positions(length: int, count: int) -> list[int]:
        count = max(0, min(int(count), length))
        if count <= 0:
            return []
        if count >= length:
            return list(range(length))
        if count == 1:
            return [length // 2]
        return sorted({
            round(offset * (length - 1) / (count - 1))
            for offset in range(count)
        })

    fractions = {"early": 0.15, "midpoint": 0.50, "late": 0.85}
    panel_order = ("early", "midpoint", "late")

    if len(normalized) > budget:
        retained_positions = evenly_selected_positions(len(normalized), budget)
        samples: list[tuple[str, float]] = []
        for retained_order, position in enumerate(retained_positions):
            index, start, end = normalized[position]
            panel = panel_order[retained_order % len(panel_order)]
            samples.append((
                f"source scene {index:02d} {start:.2f}-{end:.2f}s {panel}",
                start + (end - start) * fractions[panel],
            ))
        return samples

    selected_panels: list[set[str]] = [{"midpoint"} for _scene in normalized]
    spare = budget - len(normalized)
    if spare >= len(normalized):
        # Two samples per scene should favour the temporal edges; these expose
        # entrances, exits and reaction cuts that one midpoint commonly misses.
        selected_panels = [{"early", "late"} for _scene in normalized]
        spare -= len(normalized)
        for position in evenly_selected_positions(
            len(normalized), min(spare, len(normalized))
        ):
            selected_panels[position].add("midpoint")
    elif spare:
        # No abrupt all-midpoint fallback: distribute the available edge views
        # over the full chronology, alternating early and late evidence.
        for order, position in enumerate(
            evenly_selected_positions(len(normalized), spare)
        ):
            selected_panels[position].add("early" if order % 2 == 0 else "late")

    samples = []
    for (index, start, end), panels in zip(normalized, selected_panels):
        span = end - start
        for panel in panel_order:
            if panel not in panels:
                continue
            samples.append((
                f"source scene {index:02d} {start:.2f}-{end:.2f}s {panel}",
                start + span * fractions[panel],
            ))
    return samples


def create_video_analysis_frames(
    path: str | Path,
    destination_dir: str | Path,
    duration: float,
    runtime: RuntimePaths | None = None,
    *,
    scene_aware: bool = False,
    max_frames: int = 18,
) -> list[tuple[str, Path]]:
    """Extract representative frames for temporal visual analysis.

    Ordinary Media Pool video keeps the inexpensive opening/middle/ending
    scan.  A source-video remake requests ``scene_aware`` so the design model
    sees the complete edit instead of extrapolating a long video from its
    first few seconds.
    """
    runtime = runtime or load_runtime_paths()
    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    duration = max(0.05, duration)
    if scene_aware:
        cuts = detect_video_scene_changes(path, duration, runtime=runtime)
        boundaries = [0.0, *cuts, duration]
        scenes = [
            (index, start, end)
            for index, (start, end) in enumerate(zip(boundaries, boundaries[1:]), 1)
            if end - start >= 0.12
        ]
        samples = plan_scene_analysis_samples(scenes, max_frames=max_frames)
        if not samples:
            samples = [
                ("source opening 10%", duration * 0.10),
                ("source middle 50%", duration * 0.50),
                ("source ending 90%", duration * 0.90),
            ]
    else:
        samples = [
            ("opening 10%", duration * 0.10),
            ("middle 50%", duration * 0.50),
            ("ending 90%", duration * 0.90),
        ]
    frames: list[tuple[str, Path]] = []
    for index, (label, seconds) in enumerate(samples, 1):
        destination = destination_dir / f"frame_{index}.jpg"
        if not destination.exists():
            create_video_thumbnail(path, destination, seconds, runtime)
            if scene_aware:
                # Social-video captions and edge UI are not story evidence.
                # Obscure the usual overlay zones before BLIP/Qwen sees them,
                # while retaining faces, staging and the central environment.
                with Image.open(destination) as opened:
                    image = ImageOps.exif_transpose(opened).convert("RGB")
                blurred = image.filter(ImageFilter.GaussianBlur(radius=12.0))
                right = round(image.width * 0.88)
                bottom = round(image.height * 0.76)
                image.paste(
                    blurred.crop((right, 0, image.width, image.height)),
                    (right, 0),
                )
                image.paste(
                    blurred.crop((0, bottom, image.width, image.height)),
                    (0, bottom),
                )
                image.save(destination, format="JPEG", quality=90, optimize=True)
        frames.append((f"{label} @ {seconds:.2f}s", destination))
    return frames


def create_video_shot_frame_scan(
    path: str | Path,
    destination_dir: str | Path,
    start_seconds: float,
    end_seconds: float,
    runtime: RuntimePaths | None = None,
    *,
    scan_fps: float = 24.0,
    max_frames: int = 720,
) -> list[dict[str, Any]]:
    """Decode every H3/V1 relay frame inside one authored Shot.

    Source Video Cast Remake renders against a 24fps V1 relay plate, so this
    intentionally scans every frame on that same clock rather than sparsely
    sampling the Shot.  A hard ceiling fails visibly instead of silently
    dropping frames; unusually long Shots should be split before analysis.
    """

    runtime = runtime or load_runtime_paths()
    source = Path(path)
    start = max(0.0, float(start_seconds or 0.0))
    end = max(start + 1.0 / max(1.0, scan_fps), float(end_seconds or 0.0))
    fps = max(1.0, min(60.0, float(scan_fps or 24.0)))
    expected = max(1, int(round((end - start) * fps)))
    ceiling = max(1, int(max_frames))
    if expected > ceiling:
        raise ValueError(
            f"Shot contains {expected} relay frames; the per-Shot Qwen scan limit "
            f"is {ceiling}. Split the Shot before DETECT V1 PEOPLE."
        )
    destination = Path(destination_dir)
    destination.mkdir(parents=True, exist_ok=True)
    manifest = destination / "manifest.json"
    signature = {
        "source": str(source.resolve()),
        "mtime_ns": source.stat().st_mtime_ns,
        "start_seconds": round(start, 6),
        "end_seconds": round(end, 6),
        "scan_fps": round(fps, 6),
    }
    if manifest.is_file():
        try:
            cached = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            cached = {}
        cached_rows = cached.get("frames") or []
        if cached.get("signature") == signature and cached_rows and all(
            Path(str(row.get("path", ""))).is_file()
            for row in cached_rows if isinstance(row, dict)
        ):
            return [dict(row) for row in cached_rows if isinstance(row, dict)]
    for stale in destination.glob("frame_*.jpg"):
        stale.unlink(missing_ok=True)
    result = _run(
        [
            str(runtime.ffmpeg), "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(source), "-ss", f"{start:.6f}", "-t", f"{end - start:.6f}",
            "-map", "0:v:0", "-an",
            "-vf", f"fps={fps:.6f},scale=768:-2:force_original_aspect_ratio=decrease",
            "-q:v", "3", "-start_number", "0",
            str(destination / "frame_%06d.jpg"),
        ],
        timeout=max(45, round((end - start) * 8)),
    )
    files = sorted(destination.glob("frame_*.jpg"))
    if result.returncode or not files:
        raise RuntimeError(result.stderr.strip() or "Unable to decode Shot frames")
    if len(files) > ceiling:
        for extra in files[ceiling:]:
            extra.unlink(missing_ok=True)
        raise ValueError(
            f"Shot decoded to more than {ceiling} relay frames. Split the Shot "
            "before DETECT V1 PEOPLE."
        )
    rows = [
        {
            "frame_index": index,
            "time_seconds": round(start + index / fps, 6),
            "label": f"frame {index:04d} · {start + index / fps:.3f}s",
            "path": str(frame.resolve()),
        }
        for index, frame in enumerate(files)
    ]
    temporary = manifest.with_suffix(".writing.json")
    temporary.write_text(
        json.dumps({"signature": signature, "frames": rows}, ensure_ascii=False),
        encoding="utf-8",
    )
    shutil.move(str(temporary), str(manifest))
    return rows


def create_labeled_contact_sheet(
    sources: list[tuple[str, str | Path]],
    destination: str | Path,
    *,
    columns: int = 4,
    cell_size: tuple[int, int] = (320, 180),
) -> Path:
    """Pack chronological visual evidence into one model-readable image.

    The Design client intentionally limits the number of attached images. A
    contact sheet therefore exposes every detected source scene, or all cast
    portraits, without silently dropping later evidence. These labels are
    planning metadata only and never enter H3 rendering.
    """

    rows = [
        (str(label).strip(), Path(path))
        for label, path in sources
        if Path(path).is_file()
    ]
    if not rows:
        raise ValueError("A contact sheet requires at least one existing image")
    columns = max(1, int(columns))
    cell_width = max(96, int(cell_size[0]))
    cell_height = max(72, int(cell_size[1]))
    label_height = 30
    row_count = (len(rows) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (columns * cell_width, row_count * (cell_height + label_height)),
        (18, 20, 24),
    )
    draw = ImageDraw.Draw(sheet)
    for index, (label, path) in enumerate(rows):
        x = (index % columns) * cell_width
        y = (index // columns) * (cell_height + label_height)
        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
        image.thumbnail((cell_width, cell_height), Image.Resampling.LANCZOS)
        paste_x = x + (cell_width - image.width) // 2
        paste_y = y + (cell_height - image.height) // 2
        sheet.paste(image, (paste_x, paste_y))
        caption = label if len(label) <= 52 else label[:49] + "..."
        draw.rectangle(
            (x, y + cell_height, x + cell_width, y + cell_height + label_height),
            fill=(8, 10, 13),
        )
        draw.text((x + 7, y + cell_height + 7), caption, fill=(238, 241, 246))
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="JPEG", quality=91, optimize=True)
    return destination


def detect_video_scene_changes(
    path: str | Path,
    duration: float,
    *,
    runtime: RuntimePaths | None = None,
    threshold: float = 0.28,
) -> list[float]:
    """Return reliable source edit points detected by FFmpeg scene scoring."""

    runtime = runtime or load_runtime_paths()
    duration = max(0.05, float(duration))
    result = _run(
        [
            str(runtime.ffmpeg),
            "-hide_banner",
            "-loglevel",
            "info",
            "-i",
            str(path),
            "-t",
            f"{duration:.3f}",
            "-vf",
            f"select=gt(scene\\,{max(0.05, min(0.95, float(threshold))):.3f}),showinfo",
            "-an",
            "-f",
            "null",
            os.devnull,
        ]
    )
    values: list[float] = []
    for raw in re.findall(r"pts_time:([0-9]+(?:\.[0-9]+)?)", result.stderr or ""):
        seconds = float(raw)
        if seconds <= 0.12 or seconds >= duration - 0.12:
            continue
        if values and seconds - values[-1] < 0.18:
            continue
        values.append(seconds)
    return values


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

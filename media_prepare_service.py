"""Crash-isolated FFprobe/FFmpeg preparation service for Media Pool assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

from media_engine import (
    create_audio_waveform,
    create_image_analysis_regions,
    create_video_analysis_frames,
    human_probe_summary,
    probe_media,
    remove_solid_background,
)
from runtime_paths import RuntimePaths


def _emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", required=True)
    args = parser.parse_args()
    ffmpeg = Path(args.ffmpeg)
    runtime = RuntimePaths(
        python=Path(sys.executable),
        ffmpeg=ffmpeg,
        ffprobe=ffmpeg.with_name("ffprobe.exe"),
        blip_model_cache=Path(),
        blip_snapshot=Path(),
        blip_model_id="",
        speech_model=Path(),
    )
    _emit({"ready": True, "engine": "media-prepare"})

    for raw in sys.stdin:
        job: dict = {}
        try:
            job = json.loads(raw)
            source = Path(job["media"]).resolve()
            operation = job.get("operation", "prepare")
            if operation == "audio-pan":
                timeline_seconds = max(0.05, float(job.get("timeline_seconds", 60.0)))
                pan = max(-1.0, min(1.0, float(job.get("pan", 0.0))))
                angle = (pan + 1.0) * math.pi / 4.0
                left_gain = math.cos(angle)
                right_gain = math.sin(angle)
                destination = Path(job["destination"])
                destination.parent.mkdir(parents=True, exist_ok=True)
                audio_filter = (
                    "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                    f"pan=stereo|c0={left_gain:.6f}*c0|c1={right_gain:.6f}*c1"
                )
                _emit({"job": job["job"], "progress": 0.2, "stage": "rendering pan proxy"})
                result = subprocess.run(
                    [
                        str(runtime.ffmpeg), "-y", "-hide_banner", "-loglevel", "error",
                        "-i", str(source), "-t", f"{timeline_seconds:.3f}",
                        "-vn", "-af", audio_filter, str(destination),
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode or not destination.is_file():
                    raise RuntimeError(result.stderr.strip() or "Unable to create pan proxy")
                _emit(
                    {
                        "job": job["job"],
                        "progress": 1.0,
                        "stage": "ready",
                        "result": {"pan_proxy_path": str(destination)},
                    }
                )
                continue
            media_type = str(job["media_type"])
            timeline_seconds = max(0.05, float(job.get("timeline_seconds", 60.0)))
            cache_root = Path(job["cache_root"])
            cache_root.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha1(
                (str(source) + str(source.stat().st_mtime_ns)).encode()
            ).hexdigest()[:16]
            cache_base = cache_root / f"{media_type}_{job['node_id']}_{digest}"

            _emit({"job": job["job"], "progress": 0.10, "stage": "probing"})
            info = probe_media(source, runtime)
            analysis_sources: list[list[str]] = []
            background_removal: dict | None = None
            if media_type == "image":
                analysis_source = source
                transparent_path = Path(str(cache_base) + "_nobg.png")
                _emit({"job": job["job"], "progress": 0.18, "stage": "checking background"})
                background_removal = remove_solid_background(
                    source, transparent_path
                )
                if background_removal:
                    analysis_source = transparent_path
                preview_path = analysis_source
                region_dir = Path(str(cache_base) + "_regions")
                regions = create_image_analysis_regions(analysis_source, region_dir)
                analysis_sources = [[label, str(path)] for label, path in regions]
            elif media_type == "video":
                source_duration = max(0.05, float(info.get("duration", 0.0)))
                analysis_duration = min(source_duration, timeline_seconds)
                frame_dir = Path(str(cache_base) + "_frames")
                _emit({"job": job["job"], "progress": 0.25, "stage": "extracting frames"})
                frames = create_video_analysis_frames(
                    source,
                    frame_dir,
                    analysis_duration,
                    runtime,
                )
                analysis_sources = [[label, str(path)] for label, path in frames]
                preview_path = frames[len(frames) // 2][1]
            elif media_type == "audio":
                preview_path = Path(str(cache_base) + ".png")
                if not preview_path.exists():
                    _emit({"job": job["job"], "progress": 0.25, "stage": "building waveform"})
                    create_audio_waveform(
                        source,
                        preview_path,
                        runtime,
                        max_seconds=timeline_seconds,
                    )
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

            _emit(
                {
                    "job": job["job"],
                    "progress": 1.0,
                    "stage": "ready",
                    "result": {
                        "info": info,
                        "metadata": human_probe_summary(info),
                        "preview_path": str(preview_path),
                        "analysis_sources": analysis_sources,
                        "background_removal": background_removal,
                    },
                }
            )
        except Exception as exc:
            _emit({"job": job.get("job", ""), "error": f"{type(exc).__name__}: {exc}"})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        _emit({"fatal": True, "error": f"{type(exc).__name__}: {exc}"})
        raise SystemExit(1)

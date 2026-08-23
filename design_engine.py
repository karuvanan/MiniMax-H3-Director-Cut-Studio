"""Schema, validation and placeholder materialization for AI Director Design."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import textwrap
import wave


DESIGN_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title", "duration_seconds", "theme_text", "theme_text_explicit_user_requested", "creative_brief",
        "global_visual_style", "shots", "text_layers", "transitions",
        "markers", "media_requests", "overall_soundscape", "non_diegetic_music",
        "constraints",
    ],
    "properties": {
        "title": {"type": "string"},
        "duration_seconds": {"type": "number", "minimum": 0.5, "maximum": 60},
        "theme_text": {"type": "string"},
        "theme_text_explicit_user_requested": {"type": "boolean"},
        "creative_brief": {"type": "string"},
        "global_visual_style": {"type": "string"},
        "overall_soundscape": {"type": "string"},
        "non_diegetic_music": {"type": "string"},
        "constraints": {"type": "string"},
        "shots": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "start_seconds", "end_seconds", "track", "preset", "framing",
                    "camera_angle", "camera_movement", "movement_speed",
                    "movement_amplitude", "subject_action", "environment_response",
                    "additional_direction",
                ],
                "properties": {
                    "start_seconds": {"type": "number"},
                    "end_seconds": {"type": "number"},
                    "track": {"type": "string"},
                    "preset": {"type": "string"},
                    "framing": {"type": "string"},
                    "camera_angle": {"type": "string"},
                    "camera_movement": {"type": "string"},
                    "movement_speed": {"type": "string"},
                    "movement_amplitude": {"type": "string"},
                    "subject_action": {"type": "string"},
                    "environment_response": {"type": "string"},
                    "additional_direction": {"type": "string"},
                },
            },
        },
        "text_layers": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "start_seconds", "end_seconds", "track", "content", "role",
                    "speaker", "language", "delivery", "lip_sync",
                    "explicit_user_requested",
                ],
                "properties": {
                    "start_seconds": {"type": "number"},
                    "end_seconds": {"type": "number"},
                    "track": {"type": "string"},
                    "content": {"type": "string"},
                    "role": {
                        "type": "string",
                        "enum": ["on_screen_text", "dialogue", "voice_over", "lyrics"],
                    },
                    "speaker": {"type": "string", "enum": ["S1", "S2"]},
                    "language": {"type": "string"},
                    "delivery": {"type": "string"},
                    "lip_sync": {"type": "boolean"},
                    "explicit_user_requested": {"type": "boolean"},
                },
            },
        },
        "transitions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["time_seconds", "preset", "direction"],
                "properties": {
                    "time_seconds": {"type": "number"},
                    "preset": {"type": "string"},
                    "direction": {"type": "string"},
                },
            },
        },
        "markers": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["time_seconds", "preset", "direction"],
                "properties": {
                    "time_seconds": {"type": "number"},
                    "preset": {"type": "string"},
                    "direction": {"type": "string"},
                },
            },
        },
        "media_requests": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "media_type", "start_seconds", "end_seconds", "track",
                    "subject_keywords", "prompt", "usage",
                ],
                "properties": {
                    "media_type": {"type": "string", "enum": ["image", "video", "audio"]},
                    "usage": {
                        "type": "string",
                        "enum": ["h3_reference", "timeline_visual"],
                    },
                    "start_seconds": {"type": "number"},
                    "end_seconds": {"type": "number"},
                    "track": {"type": "string"},
                    "subject_keywords": {"type": "array", "items": {"type": "string"}},
                    "prompt": {"type": "string"},
                },
            },
        },
    },
}


def snap_half_second(value: object, duration: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return round(min(duration, max(0.0, int(number / 0.5 + 0.5) * 0.5)), 2)


def _interval(item: dict, duration: float) -> tuple[float, float]:
    start = snap_half_second(item.get("start_seconds", 0), duration)
    end = snap_half_second(item.get("end_seconds", start + 0.5), duration)
    if end <= start:
        if start + 0.5 <= duration:
            end = start + 0.5
        else:
            end = duration
            start = max(0.0, duration - 0.5)
    return start, end


def extract_design_json(value: object) -> dict:
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S | re.I)
    if fence:
        text = fence.group(1)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI response is not valid JSON: line {exc.lineno}, column {exc.colno}") from exc
    if not isinstance(payload, dict):
        raise ValueError("AI design JSON must be an object")
    return payload


def normalize_design_plan(payload: object, capacities: dict[str, int]) -> dict:
    source = extract_design_json(payload)
    duration = snap_half_second(source.get("duration_seconds", 5.0), 60.0)
    duration = max(0.5, duration)
    required_text = (
        "title", "creative_brief", "global_visual_style", "overall_soundscape",
        "non_diegetic_music", "constraints",
    )
    plan = {key: str(source.get(key, "")).strip() for key in required_text}
    plan["theme_text"] = str(source.get("theme_text", "")).strip()
    plan["theme_text_explicit_user_requested"] = bool(
        source.get("theme_text_explicit_user_requested", False)
    )
    plan["duration_seconds"] = duration
    if not plan["title"]:
        plan["title"] = "AI Director Design"
    if not plan["creative_brief"]:
        raise ValueError("Design JSON is missing creative_brief")
    if not plan["global_visual_style"]:
        raise ValueError("Design JSON is missing global_visual_style")

    shots: list[dict] = []
    for index, raw in enumerate(source.get("shots") or [], 1):
        if not isinstance(raw, dict):
            continue
        start, end = _interval(raw, duration)
        shots.append({
            "id": f"S{index}",
            "start_seconds": start,
            "end_seconds": end,
            "track": str(raw.get("track", "V1")).strip() or "V1",
            "preset": str(raw.get("preset", "Product Demonstration")).strip(),
            "framing": str(raw.get("framing", "Medium-wide")).strip(),
            "camera_angle": str(raw.get("camera_angle", "Eye level")).strip(),
            "camera_movement": str(raw.get("camera_movement", "Static")).strip(),
            "movement_speed": str(raw.get("movement_speed", "Slow")).strip(),
            "movement_amplitude": str(raw.get("movement_amplitude", "Small")).strip(),
            "subject_action": str(raw.get("subject_action", "")).strip(),
            "environment_response": str(raw.get("environment_response", "")).strip(),
            "additional_direction": str(raw.get("additional_direction", "")).strip(),
        })
    if not shots:
        raise ValueError("Design JSON must contain at least one shot")
    plan["shots"] = sorted(shots, key=lambda item: (item["start_seconds"], item["end_seconds"]))

    roles = {"on_screen_text", "dialogue", "voice_over", "lyrics"}
    text_layers: list[dict] = []
    for raw in source.get("text_layers") or []:
        if (
            not isinstance(raw, dict)
            or not bool(raw.get("explicit_user_requested", False))
            or not str(raw.get("content", "")).strip()
        ):
            continue
        start, end = _interval(raw, duration)
        role = str(raw.get("role", "on_screen_text"))
        text_layers.append({
            "start_seconds": start,
            "end_seconds": end,
            "track": str(raw.get("track", "V1")).strip() or "V1",
            "content": str(raw.get("content", "")).strip(),
            "role": role if role in roles else "on_screen_text",
            "speaker": str(raw.get("speaker", "S1")) if str(raw.get("speaker", "S1")) in {"S1", "S2"} else "S1",
            "language": str(raw.get("language", "English")).strip() or "English",
            "delivery": str(raw.get("delivery", "Natural")).strip() or "Natural",
            "lip_sync": role == "dialogue" and bool(raw.get("lip_sync", False)),
            "explicit_user_requested": True,
        })
    plan["text_layers"] = text_layers

    for family in ("transitions", "markers"):
        entries: list[dict] = []
        for raw in source.get(family) or []:
            if not isinstance(raw, dict):
                continue
            cue_time = snap_half_second(raw.get("time_seconds", 0), duration)
            if cue_time >= duration:
                cue_time = max(0.0, duration - 0.5)
            entries.append({
                "time_seconds": cue_time,
                "preset": str(raw.get("preset", "Hard Cut" if family == "transitions" else "Camera Cue")).strip(),
                "direction": str(raw.get("direction", "")).strip(),
            })
        plan[family] = entries
    has_final_hold = any(
        any(word in item["preset"].lower() for word in ("final", "ending", "hold"))
        for item in plan["markers"]
    )
    if not has_final_hold:
        plan["markers"].append({
            "time_seconds": snap_half_second(max(0.0, duration - 1.0), duration),
            "preset": "Final Hold",
            "direction": (
                "Settle all camera motion and hold the final hero composition through the last frame."
            ),
        })

    media_requests: list[dict] = []
    counts = {"image": 0, "video": 0, "audio": 0}
    for raw in source.get("media_requests") or []:
        if not isinstance(raw, dict):
            continue
        media_type = str(raw.get("media_type", "image")).lower()
        if media_type not in counts:
            continue
        counts[media_type] += 1
        if counts[media_type] > int(capacities.get(media_type, 0)):
            raise ValueError(
                f"Design requests {counts[media_type]} {media_type} assets, but the API has only "
                f"{capacities.get(media_type, 0)} slots"
            )
        start, end = _interval(raw, duration)
        keywords = raw.get("subject_keywords") or []
        if isinstance(keywords, str):
            keywords = [item.strip() for item in keywords.split(",") if item.strip()]
        media_requests.append({
            "media_type": media_type,
            "usage": (
                str(raw.get("usage", "h3_reference"))
                if str(raw.get("usage", "h3_reference")) in {"h3_reference", "timeline_visual"}
                else "h3_reference"
            ),
            "start_seconds": start,
            "end_seconds": end,
            "track": str(raw.get("track", "A1" if media_type == "audio" else "V1")).strip(),
            "subject_keywords": [str(item).strip() for item in keywords if str(item).strip()],
            "prompt": str(raw.get("prompt", "")).strip(),
        })
    plan["media_requests"] = media_requests
    return plan


def build_design_system_prompt(context: dict) -> str:
    return (
        "You are the AI Design Planner inside a MiniMax H3 Director Cut application. "
        "Convert the user's concept into one production-ready JSON object that exactly matches the supplied schema. "
        "The bound Default H3 skill and optional Special skill in the workspace context are authoritative. "
        "Apply their planning, continuity, reference-retention, shot, audio and technical rules while producing the JSON; "
        "the application will compile this JSON into the final H3 Ref2VA prompt. "
        "Use 0.5-second boundaries. Build chronological Shot Blocks with explicit framing, camera angle, camera movement, "
        "For media_requests, use h3_reference when an asset supplies subject, product, wardrobe, environment or composition guidance; "
        "use timeline_visual only when the user explicitly asks to composite the literal file into the editorial preview. "
        "Only create a text_layer or theme_text when the user explicitly requests visible text, dialogue, voice-over or lyrics, and set "
        "explicit_user_requested=true only in that case. Never turn the creative brief or scene description into on-screen text. "
        "Always include a Final Hold marker before the final frame; cue timestamps must be earlier than duration_seconds. "
        "subject action, environmental response and additional direction. Media requests are reference requirements, not final generated media. "
        "Keep exact product/subject continuity, realistic object interaction and H3-friendly concise directions. "
        "Do not include markdown or commentary. Available workspace context: "
        + json.dumps(context, ensure_ascii=False)
    )


def _slug(value: str, fallback: str) -> str:
    ascii_value = value.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", ascii_value).strip("_")[:48] or fallback


def _font(size: int):
    from PIL import ImageFont
    for path in (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/arial.ttf")):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _slate(path: Path, request: dict, title: str) -> None:
    from PIL import Image, ImageDraw
    image = Image.new("RGB", (1280, 720), (17, 24, 31))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1280, 14), fill=(36, 188, 215))
    draw.text((58, 54), "AI DESIGN PLACEHOLDER", font=_font(42), fill=(73, 210, 231))
    draw.text((58, 126), title, font=_font(34), fill=(245, 247, 249))
    timing = f"{request['start_seconds']:.2f}s - {request['end_seconds']:.2f}s | {request['track']}"
    draw.text((58, 188), timing, font=_font(25), fill=(190, 198, 207))
    keywords = ", ".join(request.get("subject_keywords") or []) or "No subject keywords"
    draw.text((58, 242), "KEYWORDS: " + keywords, font=_font(25), fill=(244, 194, 78))
    lines = textwrap.wrap(request.get("prompt", "Replace with final reference media"), width=62)
    draw.multiline_text((58, 310), "\n".join(lines[:8]), font=_font(24), fill=(226, 230, 234), spacing=12)
    draw.text((58, 666), "Replace this placeholder with approved production media.", font=_font(19), fill=(128, 139, 150))
    image.save(path)


def materialize_design_media(
    plan: dict, example_root: Path, ffmpeg: Path
) -> tuple[Path, list[dict]]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    design_dir = example_root / f"{_slug(plan.get('title', ''), 'ai_design')}_{stamp}"
    design_dir.mkdir(parents=True, exist_ok=False)
    (design_dir / "design_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    outputs: list[dict] = []
    for index, request in enumerate(plan.get("media_requests") or [], 1):
        keywords = "_".join(request.get("subject_keywords") or [])
        stem = (
            f"{index:02d}_{request['start_seconds']:05.2f}-{request['end_seconds']:05.2f}_"
            f"{_slug(keywords, request['media_type'])}"
        )
        media_type = request["media_type"]
        if media_type == "image":
            output = design_dir / f"{stem}.png"
            _slate(output, request, plan["title"])
            preview_path = output
        elif media_type == "video":
            slate = design_dir / f"{stem}_source.png"
            output = design_dir / f"{stem}.mp4"
            _slate(slate, request, plan["title"])
            preview_path = slate
            duration = max(0.5, request["end_seconds"] - request["start_seconds"])
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.run(
                [
                    str(ffmpeg), "-y", "-loop", "1", "-i", str(slate), "-t", str(duration),
                    "-vf", "scale=1280:720,format=yuv420p", "-r", "24", "-an", str(output),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
                timeout=60,
            )
        else:
            output = design_dir / f"{stem}.wav"
            preview_path = None
            duration = max(0.5, request["end_seconds"] - request["start_seconds"])
            sample_rate = 24000
            with wave.open(str(output), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(sample_rate)
                audio.writeframes(b"\x00\x00" * int(duration * sample_rate))
        metadata = output.with_suffix(output.suffix + ".request.json")
        metadata.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append({
            **request,
            "local_path": str(output.resolve()),
            "preview_path": str(preview_path.resolve()) if preview_path else "",
            "design_dir": str(design_dir.resolve()),
        })
    return design_dir, outputs

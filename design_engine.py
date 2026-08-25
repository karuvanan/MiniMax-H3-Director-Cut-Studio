"""Schema, validation and placeholder materialization for AI Director Design."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import textwrap
import wave


MAX_DESIGN_DURATION_SECONDS = 600.0


_PICTURE_REFERENCE_RE = re.compile(r"<\s*picture\s+\d+\s*>", flags=re.I)
_MEDIA_ID_RE = re.compile(r"^@?([PVA])(\d+)$", flags=re.I)
_H3_MEDIA_TAG_RE = re.compile(r"^<\s*(Picture|Video|Audio)\s+(\d+)\s*>$", flags=re.I)
_DEPENDENT_IMAGE_WORDING_RE = re.compile(
    r"(?:"
    r"\b(?:as\s+(?:seen|shown|depicted)\s+in|based\s+on|copied\s+from|derived\s+from|"
    r"continue(?:d)?\s+from|match(?:ing)?|same\s+as)\s+(?:the\s+)?"
    r"(?:previous|next|future|above|below|generated|output|reference|source|input|this)\s+"
    r"(?:image|picture|frame)\b"
    r"|\b(?:previous|next|future|above|below)\s+(?:image|picture|frame)\b"
    r"|\b(?:image|picture|frame)\s+(?:above|below|that\s+will\s+be\s+generated|to\s+be\s+generated)\b"
    r")",
    flags=re.I,
)
_ACTION_OR_BOUNDARY_RE = re.compile(
    r"\b(?:action[- ]state|boundary[- ]continuity|continuity[- ]anchor|boundary[- ]frame|"
    r"first[- ]frame|last[- ]frame|near[- ]impact|impact[- ]pose|mid[- ]air|airborne|"
    r"wall[- ]run(?:ning)?|water[- ]run(?:ning)?|spear[- ]run(?:ning)?|weapon[- ]contact)\b",
    flags=re.I,
)
_NON_STORY_BACKGROUND_RE = re.compile(
    r"\b(?:neutral|blank|plain|empty|isolated|generic|seamless)(?:\s+studio)?\s+background\b"
    r"|\b(?:on|against)\s+(?:a\s+)?(?:neutral|blank|plain|empty|isolated|generic|seamless)\s+"
    r"(?:backdrop|studio)\b"
    r"|\bstudio\s+(?:background|backdrop)\b",
    flags=re.I,
)


DESIGN_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title", "duration_seconds", "theme_text", "theme_text_explicit_user_requested", "creative_brief",
        "global_visual_style", "shots", "text_layers", "transitions",
        "markers", "existing_media_uses", "media_requests", "overall_soundscape", "non_diegetic_music",
        "constraints",
    ],
    "properties": {
        "title": {"type": "string"},
        "duration_seconds": {
            "type": "number",
            "minimum": 0.5,
            "maximum": MAX_DESIGN_DURATION_SECONDS,
        },
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
        "existing_media_uses": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "requirement_id", "media_id", "media_type", "usage",
                    "reuse_policy", "start_seconds", "end_seconds", "track",
                    "subject_keywords", "instruction",
                ],
                "properties": {
                    "requirement_id": {"type": "string"},
                    "media_id": {"type": "string", "pattern": "^[PVA][1-9][0-9]*$"},
                    "media_type": {"type": "string", "enum": ["image", "video", "audio"]},
                    "usage": {
                        "type": "string",
                        "enum": ["h3_reference", "timeline_visual"],
                    },
                    "reuse_policy": {
                        "type": "string",
                        "enum": ["whole_design", "time_scoped"],
                    },
                    "start_seconds": {"type": "number"},
                    "end_seconds": {"type": "number"},
                    "track": {"type": "string"},
                    "subject_keywords": {"type": "array", "items": {"type": "string"}},
                    "instruction": {"type": "string"},
                },
            },
        },
        "media_requests": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "requirement_id", "media_type", "start_seconds", "end_seconds", "track",
                    "subject_keywords", "prompt", "usage", "reuse_policy",
                ],
                "properties": {
                    "requirement_id": {"type": "string"},
                    "media_type": {"type": "string", "enum": ["image", "video", "audio"]},
                    "usage": {
                        "type": "string",
                        "enum": ["h3_reference", "timeline_visual"],
                    },
                    "reuse_policy": {
                        "type": "string",
                        "enum": ["whole_design", "time_scoped"],
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


def _validate_t2i_media_prompt(
    prompt: str,
    *,
    request_number: int,
    start_seconds: float,
    end_seconds: float,
    duration_seconds: float,
) -> None:
    """Reject image-generation instructions that cannot stand on their own.

    ``<Picture N>`` is an H3 reference token.  A Z-Image/T2I request runs
    before those H3 slots exist, so allowing that token (especially a token
    naming the image currently being generated) makes the prompt circular.
    Time-scoped images are composition/action/boundary references in the
    Director planner; those frames must be staged in the story location rather
    than on a catalog-style neutral backdrop.
    """

    label = f"Image media_request {request_number}"
    if not prompt:
        raise ValueError(
            f"{label} has no T2I prompt. Replan it as a complete standalone visual description."
        )
    if _PICTURE_REFERENCE_RE.search(prompt):
        raise ValueError(
            f"{label} contains an H3 <Picture N> token. Z-Image/T2I prompts must be standalone; "
            "replan the request without current, self or future Picture references."
        )
    if _DEPENDENT_IMAGE_WORDING_RE.search(prompt):
        raise ValueError(
            f"{label} depends on another image or frame. Z-Image/T2I prompts must restate every "
            "required subject, prop, owner, action and environment explicitly."
        )

    is_time_scoped = start_seconds > 0.0 or end_seconds < duration_seconds
    is_action_or_boundary = is_time_scoped or bool(_ACTION_OR_BOUNDARY_RE.search(prompt))
    if is_action_or_boundary and _NON_STORY_BACKGROUND_RE.search(prompt):
        raise ValueError(
            f"{label} is an action/boundary reference with a neutral, blank or studio background. "
            "Replan it inside the story's real in-world environment and preserve character/prop ownership."
        )


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


def _normalized_requirement_id(value: object, fallback: str) -> str:
    text = "" if value is None else str(value).strip().lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "_", text).strip("_")
    return normalized[:80] or fallback


def _normalized_media_id(value: object) -> str:
    text = str(value).strip()
    direct = _MEDIA_ID_RE.fullmatch(text)
    if direct:
        ordinal = int(direct.group(2))
        return f"{direct.group(1).upper()}{ordinal}" if ordinal >= 1 else ""
    tag = _H3_MEDIA_TAG_RE.fullmatch(text)
    if tag:
        prefix = {"picture": "P", "video": "V", "audio": "A"}[tag.group(1).lower()]
        ordinal = int(tag.group(2))
        return f"{prefix}{ordinal}" if ordinal >= 1 else ""
    return ""


def _media_type_for_id(media_id: str) -> str:
    return {"P": "image", "V": "video", "A": "audio"}.get(media_id[:1], "")


def _media_inventory(items: list[dict] | None) -> dict[str, dict]:
    inventory: dict[str, dict] = {}
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        media_id = _normalized_media_id(
            raw.get("media_id") or raw.get("asset_id") or raw.get("tag") or ""
        )
        if not media_id:
            continue
        row = dict(raw)
        row["media_id"] = media_id
        row["media_type"] = str(
            row.get("media_type") or row.get("type") or _media_type_for_id(media_id)
        ).strip().lower()
        row["loaded"] = bool(row.get("loaded", row.get("available", True)))
        inventory[media_id] = row
    return inventory


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        value = [item.strip() for item in value.split(",")]
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_design_plan(
    payload: object,
    capacities: dict[str, int],
    *,
    existing_media: list[dict] | None = None,
    strict_t2i_prompts: bool = False,
) -> dict:
    source = extract_design_json(payload)
    duration = snap_half_second(
        source.get("duration_seconds", 5.0),
        MAX_DESIGN_DURATION_SECONDS,
    )
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
        role = role if role in roles else "on_screen_text"
        requested_track = str(raw.get("track", "")).strip().upper()
        if role == "on_screen_text":
            track = requested_track if requested_track.startswith("V") else "V4"
        else:
            role_tracks = {"dialogue": "A4", "voice_over": "A5", "lyrics": "A6"}
            track = requested_track if requested_track.startswith("A") else role_tracks.get(role, "A4")
        text_layers.append({
            "start_seconds": start,
            "end_seconds": end,
            "track": track,
            "content": str(raw.get("content", "")).strip(),
            "role": role,
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

    inventory = _media_inventory(existing_media)
    inventory_was_supplied = existing_media is not None
    existing_media_uses: list[dict] = []
    reused_requirement_ids: set[str] = set()
    reused_media_ids: set[str] = set()
    for use_number, raw in enumerate(source.get("existing_media_uses") or [], 1):
        if not isinstance(raw, dict):
            continue
        media_id = _normalized_media_id(raw.get("media_id", ""))
        if not media_id:
            raise ValueError(
                f"Existing media use {use_number} has an invalid media_id; use P1, V1 or A1."
            )
        inferred_type = _media_type_for_id(media_id)
        media_type = str(raw.get("media_type") or inferred_type).strip().lower()
        if media_type != inferred_type:
            raise ValueError(
                f"Existing media {media_id} is {inferred_type}, not {media_type}."
            )
        ordinal = int(media_id[1:])
        if ordinal > int(capacities.get(media_type, 0)):
            raise ValueError(
                f"Existing media {media_id} is outside the API's {capacities.get(media_type, 0)} "
                f"{media_type} slots."
            )
        inventory_row = inventory.get(media_id)
        if inventory_was_supplied:
            if inventory_row is None:
                raise ValueError(f"Existing media {media_id} is not present in the Media Pool inventory.")
            if not inventory_row.get("loaded", False):
                raise ValueError(f"Existing media {media_id} is empty and cannot be reused.")
            inventory_type = str(inventory_row.get("media_type", "")).strip().lower()
            if inventory_type and inventory_type != media_type:
                raise ValueError(
                    f"Media Pool {media_id} is {inventory_type}, not {media_type}."
                )
        requirement_id = _normalized_requirement_id(
            raw.get("requirement_id"), f"reuse_{media_id.lower()}"
        )
        if requirement_id in reused_requirement_ids:
            raise ValueError(
                f"Existing media requirement_id {requirement_id!r} is used more than once."
            )
        if media_id in reused_media_ids:
            raise ValueError(f"Existing media {media_id} is assigned more than once.")
        start, end = _interval(raw, duration)
        reuse_policy = str(raw.get("reuse_policy", "")).strip().lower()
        if reuse_policy not in {"whole_design", "time_scoped"}:
            reuse_policy = (
                "whole_design"
                if start <= 0.0 and end >= duration
                else "time_scoped"
            )
        if reuse_policy == "whole_design":
            start, end = 0.0, duration
        keywords = _string_list(raw.get("subject_keywords") or [])
        fallback_instruction = ""
        if inventory_row:
            fallback_instruction = str(
                inventory_row.get("clip_prompt")
                or inventory_row.get("caption")
                or inventory_row.get("analysis_summary")
                or ""
            ).strip()
        existing_media_uses.append({
            "requirement_id": requirement_id,
            "media_id": media_id,
            "media_type": media_type,
            "usage": (
                str(raw.get("usage", "h3_reference"))
                if str(raw.get("usage", "h3_reference")) in {"h3_reference", "timeline_visual"}
                else "h3_reference"
            ),
            "reuse_policy": reuse_policy,
            "start_seconds": start,
            "end_seconds": end,
            "track": str(
                raw.get("track", "A1" if media_type == "audio" else "V1")
            ).strip() or ("A1" if media_type == "audio" else "V1"),
            "subject_keywords": keywords,
            "instruction": str(raw.get("instruction") or fallback_instruction).strip(),
        })
        reused_requirement_ids.add(requirement_id)
        reused_media_ids.add(media_id)
    plan["existing_media_uses"] = existing_media_uses

    media_requests: list[dict] = []
    counts = {"image": 0, "video": 0, "audio": 0}
    occupied_counts = {"image": 0, "video": 0, "audio": 0}
    if inventory_was_supplied:
        for row in inventory.values():
            media_type = str(row.get("media_type", "")).strip().lower()
            if row.get("loaded", False) and media_type in occupied_counts:
                occupied_counts[media_type] += 1
    available_counts = {
        media_type: max(0, int(capacities.get(media_type, 0)) - occupied_counts[media_type])
        for media_type in counts
    }
    requested_requirement_ids: set[str] = set()
    for request_number, raw in enumerate(source.get("media_requests") or [], 1):
        if not isinstance(raw, dict):
            continue
        media_type = str(raw.get("media_type", "image")).lower()
        if media_type not in counts:
            continue
        requirement_id = _normalized_requirement_id(
            raw.get("requirement_id"), f"request_{request_number}"
        )
        # A reusable Media Pool asset is authoritative for a requirement.  A
        # model may still emit the same requirement in media_requests; silently
        # discard that duplicate instead of wasting a slot or a generation.
        if requirement_id in reused_requirement_ids:
            continue
        if requirement_id in requested_requirement_ids:
            raise ValueError(
                f"Media requirement_id {requirement_id!r} is requested more than once."
            )
        counts[media_type] += 1
        slot_limit = available_counts[media_type]
        if counts[media_type] > slot_limit:
            if inventory_was_supplied:
                raise ValueError(
                    f"Design requests {counts[media_type]} new {media_type} assets, but the API has "
                    f"only {slot_limit} free slots ({occupied_counts[media_type]} already loaded)."
                )
            raise ValueError(
                f"Design requests {counts[media_type]} {media_type} assets, but the API has only "
                f"{capacities.get(media_type, 0)} slots"
            )
        start, end = _interval(raw, duration)
        reuse_policy = str(raw.get("reuse_policy", "")).strip().lower()
        if reuse_policy not in {"whole_design", "time_scoped"}:
            reuse_policy = (
                "whole_design"
                if start <= 0.0 and end >= duration
                else "time_scoped"
            )
        if reuse_policy == "whole_design":
            start, end = 0.0, duration
        prompt = str(raw.get("prompt", "")).strip()
        if media_type == "image" and strict_t2i_prompts:
            _validate_t2i_media_prompt(
                prompt,
                request_number=request_number,
                start_seconds=start,
                end_seconds=end,
                duration_seconds=duration,
            )
        keywords = _string_list(raw.get("subject_keywords") or [])
        media_requests.append({
            "requirement_id": requirement_id,
            "media_type": media_type,
            "usage": (
                str(raw.get("usage", "h3_reference"))
                if str(raw.get("usage", "h3_reference")) in {"h3_reference", "timeline_visual"}
                else "h3_reference"
            ),
            "reuse_policy": reuse_policy,
            "start_seconds": start,
            "end_seconds": end,
            "track": str(raw.get("track", "A1" if media_type == "audio" else "V1")).strip(),
            "subject_keywords": keywords,
            "prompt": prompt,
        })
        requested_requirement_ids.add(requirement_id)
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
        "subject action, environmental response and additional direction. "
        "Timeline tracks are editorial lanes, not the physical H3 reference-slot count. You may plan V4, V5 and higher "
        "visual lanes for overlapping action states, titles or compositing, and A4, A5 and higher audio lanes for dialogue, "
        "voice-over, lyrics, ambience or music stems; the Studio creates those tracks automatically. Keep on-screen text on "
        "a V track and place dialogue, voice-over and lyrics on A tracks. The renderer will select only the temporally relevant "
        "references for each native 15-second H3 window, so never exceed the supplied physical media_capacity merely because "
        "additional editorial tracks exist. "
        "Before requesting any new material, audit the loaded existing_media inventory in the workspace context. The user may "
        "refer to its stable Media Pool IDs as @P1, @P2, @V1 or @A1; write the ID without @ in existing_media_uses.media_id. "
        "Reuse only loaded assets that genuinely satisfy the story requirement, and never invent an ID, select an empty slot, "
        "or force every existing asset into the design. Give every logical media need a concise stable requirement_id. "
        "Treat each asset's caption, clip_prompt and analysis_summary as the evidence for its content, including video-frame "
        "captions, beat/VAD and transcript observations. If analysis_status is pending or the evidence is ambiguous, do not "
        "invent unseen people, objects, speech or actions; use a neutral preserve-the-supplied-asset instruction instead. "
        "When a loaded asset satisfies that need, put it in existing_media_uses and do not emit a media_request with the same "
        "requirement_id. existing_media_uses instructions describe how H3 should preserve or use the supplied asset; they do not "
        "ask Z-Image to regenerate it. Use reuse_policy=whole_design for identity, product, wardrobe, environment or audio references "
        "needed throughout the story, and reuse_policy=time_scoped for one contiguous action or editorial interval. An existing "
        "Media Pool asset may appear at most once in existing_media_uses; widen its single range when it must cover several Shots. "
        "media_requests must contain only genuinely missing assets after this reuse audit. Choose that missing count dynamically from "
        "the concept and available empty slots; never duplicate a requirement already fulfilled by @P1/@V1/@A1. "
        "For media_requests, use h3_reference when an asset supplies subject, product, wardrobe, environment or composition guidance; "
        "use timeline_visual only when the user explicitly asks to composite the literal file into the editorial preview. "
        "Plan reference media dynamically from the story: reusable identity and environment references are valid, and time-scoped "
        "composition, action-state or boundary-continuity references are also valid when they reduce ambiguity between story phases. "
        "Choose the useful count and exact timeline ranges yourself. Never force one image per Shot, never fill all available slots merely "
        "because they exist, and never make redundant copies; distinct temporal states of the same subject are allowed when they prevent "
        "a later segment from replaying an earlier action. "
        "Every image media_request sent to Z-Image/T2I must contain a complete standalone visual prompt. Never put an H3 <Picture N> "
        "token in a T2I prompt and never ask it to copy, match, continue from or depend on a previous, current/self, next/future, generated "
        "or output image; those H3 slots do not exist when reference images are generated. Restate all required identity, appearance, wardrobe, "
        "prop, action, composition, lighting and environment facts directly inside each image prompt. "
        "For every time-scoped action-state or segment-boundary reference, stage the requested moment inside the story's exact real in-world "
        "location with its recognizable geography and lighting; never use a neutral, blank, plain, isolated or studio background for those "
        "action/boundary images. First infer and preserve an exact character/prop ownership ledger from the story: name which character wears "
        "or holds each item in every affected prompt, keep counts exact, and never swap, duplicate or transfer ownership unless the story "
        "explicitly performs that transfer. "
        "During a BLIP-backed refinement pass, use BLIP only as visual QA. Compare each caption against the intended identity, character/prop "
        "ownership, counts, action state and in-world environment. If BLIP conflicts on any of those facts, reject that generated reference "
        "and replan the affected media_request with a corrected standalone prompt for regeneration; never alter the story or ownership ledger "
        "to agree with an incorrect BLIP observation, and never approve the conflicting image as an H3 reference. "
        "Only create a text_layer or theme_text when the user explicitly requests visible text, dialogue, voice-over or lyrics, and set "
        "explicit_user_requested=true only in that case. Never turn the creative brief or scene description into on-screen text. "
        "Always include a Final Hold marker before the final frame; cue timestamps must be earlier than duration_seconds. "
        "Media requests are reference requirements, not final generated media. "
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

"""Structured, reviewable Timeline edits for the in-Studio Qwen assistant.

The assistant is intentionally not allowed to rewrite a compiled H3 prompt.  It
can only propose small operations against authored Timeline objects.  The GUI
validates these operations, shows them to the user, and applies the selected
ones through the normal undo stack.
"""

from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any, Iterable


ASSISTANT_SCOPES = (
    "shot_only",
    "linked_continuity",
    "whole_segment",
    "work_area",
    "whole_timeline",
)

SHOT_PATCH_FIELDS = (
    "preset",
    "detail",
    "framing",
    "camera_angle",
    "camera_movement",
    "movement_speed",
    "movement_amplitude",
    "subject_action",
    "environment_response",
    "continuity_mode",
    "continuity_state",
    "optional_flourish",
    "incoming_environment_state",
    "outgoing_environment_state",
    "environment_interaction",
    "crowd_reaction",
    "location_transition",
    "native_audio_direction",
    "environment_continuity",
    "audio_reference_intent",
    "speech_visual_mode",
    "mouth_behavior",
    "voice_position",
    "lip_sync_mode",
    "lip_sync_target",
    "lip_sync_source",
)

TEXT_PATCH_FIELDS = (
    "text",
    "speaker",
    "language",
    "delivery",
    "overlap_policy",
    "track_id",
    "start_seconds",
    "end_seconds",
)

TRACK_PATCH_FIELDS = (
    "name",
    "enabled",
    "visible",
    "muted",
    "solo",
    "volume",
    "pan",
)

WORK_AREA_PATCH_FIELDS = ("start_seconds", "end_seconds")

PATCH_FIELDS_BY_KIND = {
    "shot": frozenset(SHOT_PATCH_FIELDS),
    "text_layer": frozenset(TEXT_PATCH_FIELDS),
    "track": frozenset(TRACK_PATCH_FIELDS),
    "work_area": frozenset(WORK_AREA_PATCH_FIELDS),
}

HIGH_IMPACT_FIELDS = frozenset(
    {
        "text",
        "speaker",
        "language",
        "start_seconds",
        "end_seconds",
        "track_id",
    }
)

TIMELINE_ASSISTANT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "scope", "operations", "warnings"],
    "properties": {
        "summary": {"type": "string"},
        "scope": {"type": "string", "enum": list(ASSISTANT_SCOPES)},
        "operations": {
            "type": "array",
            "maxItems": 96,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "target_kind",
                    "target_id",
                    "field",
                    "value_json",
                    "reason",
                    "risk_level",
                    "requires_confirmation",
                ],
                "properties": {
                    "target_kind": {
                        "type": "string",
                        "enum": ["shot", "text_layer", "track", "work_area"],
                    },
                    "target_id": {"type": "string"},
                    "field": {"type": "string"},
                    "value_json": {
                        "type": "string",
                        "description": "The replacement value encoded as one JSON scalar.",
                    },
                    "reason": {"type": "string"},
                    "risk_level": {
                        "type": "string",
                        "enum": ["safe", "review", "high"],
                    },
                    "requires_confirmation": {"type": "boolean"},
                },
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}


def _json_scalar(value_json: str) -> Any:
    """Decode one scalar while rejecting nested objects and arrays."""

    try:
        value = json.loads(str(value_json))
    except json.JSONDecodeError:
        value = str(value_json)
    if isinstance(value, (dict, list)):
        raise ValueError("Timeline patch values must be JSON scalars")
    return value


def parse_assistant_response(raw: str | dict[str, Any]) -> dict[str, Any]:
    """Parse and normalize a provider response without trusting its targets."""

    if isinstance(raw, dict):
        payload = deepcopy(raw)
    else:
        text = str(raw or "").strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
        payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Timeline assistant response must be a JSON object")
    scope = str(payload.get("scope", "linked_continuity")).strip()
    if scope not in ASSISTANT_SCOPES:
        scope = "linked_continuity"
    operations: list[dict[str, Any]] = []
    for index, raw_operation in enumerate(payload.get("operations") or []):
        if not isinstance(raw_operation, dict):
            continue
        kind = str(raw_operation.get("target_kind", "")).strip()
        field = str(raw_operation.get("field", "")).strip()
        if kind not in PATCH_FIELDS_BY_KIND:
            continue
        if field not in PATCH_FIELDS_BY_KIND[kind]:
            continue
        try:
            value = _json_scalar(str(raw_operation.get("value_json", "null")))
        except ValueError:
            continue
        high_impact = field in HIGH_IMPACT_FIELDS or kind in {"text_layer", "work_area"}
        operation = {
            "operation_id": f"patch-{index + 1:03d}",
            "target_kind": kind,
            "target_id": str(raw_operation.get("target_id", "")).strip(),
            "field": field,
            "value": value,
            "reason": str(raw_operation.get("reason", "")).strip(),
            "risk_level": str(raw_operation.get("risk_level", "review")).strip(),
            "requires_confirmation": bool(
                raw_operation.get("requires_confirmation", False) or high_impact
            ),
        }
        if operation["risk_level"] not in {"safe", "review", "high"}:
            operation["risk_level"] = "review"
        operations.append(operation)
    return {
        "summary": str(payload.get("summary", "")).strip(),
        "scope": scope,
        "operations": operations,
        "warnings": [str(item).strip() for item in payload.get("warnings") or [] if str(item).strip()],
    }


def validate_operations(
    proposal: dict[str, Any],
    *,
    shot_ids: Iterable[str],
    text_layer_ids: Iterable[str],
    track_ids: Iterable[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Drop hallucinated targets and return human-readable validation notes."""

    valid_ids = {
        "shot": set(shot_ids),
        "text_layer": set(text_layer_ids),
        "track": set(track_ids),
        "work_area": {"work_area", "timeline"},
    }
    accepted: list[dict[str, Any]] = []
    rejected: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for operation in proposal.get("operations") or []:
        kind = str(operation.get("target_kind", ""))
        target_id = str(operation.get("target_id", ""))
        field = str(operation.get("field", ""))
        key = (kind, target_id, field)
        if target_id not in valid_ids.get(kind, set()):
            rejected.append(f"Unknown {kind} target {target_id or '(empty)'}")
            continue
        if key in seen:
            rejected.append(f"Duplicate patch for {target_id}.{field}")
            continue
        seen.add(key)
        accepted.append(deepcopy(operation))
    return accepted, rejected


def _compact_rows(rows: Iterable[dict[str, Any]], fields: Iterable[str]) -> list[dict[str, Any]]:
    return [
        {field: row.get(field) for field in fields if field in row}
        for row in rows
    ]


def build_timeline_assistant_prompts(
    *,
    request: str,
    scope: str,
    target_shot_id: str,
    shots: list[dict[str, Any]],
    text_layers: list[dict[str, Any]],
    tracks: list[dict[str, Any]],
    work_area: dict[str, float],
    media_inventory: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    """Build a compact fact-ledger prompt for the global Timeline assistant."""

    normalized_scope = scope if scope in ASSISTANT_SCOPES else "linked_continuity"
    system_prompt = (
        "You are the non-destructive Timeline Qwen Assistant inside MiniMax H3 Director Cut Studio. "
        "Return only the requested JSON schema. Never rewrite a compiled H3 prompt. Propose the "
        "smallest sufficient field patches against existing object IDs. Preserve user-authored media "
        "references, exact dialogue words, cast identity, accepted render state and duration unless the "
        "user explicitly requests a change. Camera and VFX edits must preserve physical cause, incoming "
        "state, outgoing state, screen direction, voice origin and environmental continuity. For a Shot "
        "edit, inspect the previous and next Shot; include neighbor patches only when a boundary fact must "
        "change. value_json must be one valid JSON scalar encoded as text. Mark dialogue, timing, track, "
        "identity or destructive changes requires_confirmation=true and risk_level=high. For lip-sync "
        "routing use lip_sync_mode auto/enabled/disabled, lip_sync_target as a loaded P# or empty for "
        "automatic cast assignment, and lip_sync_source as auto, text_layers, or an active A#/V# reference."
    )
    context = {
        "request": str(request).strip(),
        "requested_scope": normalized_scope,
        "target_shot_id": target_shot_id,
        "work_area": work_area,
        "shots": _compact_rows(
            shots,
            (
                "cue_id", "start_seconds", "end_seconds", "preset", "framing",
                "camera_angle", "camera_movement", "movement_speed",
                "movement_amplitude", "subject_action", "environment_response",
                "continuity_state", "incoming_environment_state",
                "outgoing_environment_state", "native_audio_direction",
                "environment_continuity", "speech_visual_mode", "mouth_behavior",
                "voice_position", "lip_sync_mode", "lip_sync_target",
                "lip_sync_source",
            ),
        ),
        "text_layers": _compact_rows(
            text_layers,
            (
                "layer_id", "content_role", "start_seconds", "end_seconds", "track_id",
                "speaker", "language", "delivery", "overlap_policy", "text",
            ),
        ),
        "tracks": _compact_rows(
            tracks,
            ("track_id", "name", "kind", "enabled", "visible", "muted", "solo", "volume", "pan"),
        ),
        "media_inventory": _compact_rows(
            media_inventory or [],
            ("media_id", "media_type", "recognition", "timeline_start", "timeline_end"),
        ),
    }
    user_prompt = (
        "Review this authoritative Studio state and return a minimal structured patch plan. "
        "Do not invent IDs or alter anything outside the requested scope.\n\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )
    return system_prompt, user_prompt


def affected_shot_ids(
    operations: Iterable[dict[str, Any]],
    *,
    text_layers: Iterable[dict[str, Any]],
) -> set[str]:
    """Resolve direct and speech-layer changes to the Shot IDs they affect."""

    layer_to_shot = {
        str(layer.get("layer_id", "")): str(layer.get("shot_id", ""))
        for layer in text_layers
    }
    result: set[str] = set()
    for operation in operations:
        kind = str(operation.get("target_kind", ""))
        target_id = str(operation.get("target_id", ""))
        if kind == "shot":
            result.add(target_id)
        elif kind == "text_layer" and layer_to_shot.get(target_id):
            result.add(layer_to_shot[target_id])
    return {item for item in result if item}

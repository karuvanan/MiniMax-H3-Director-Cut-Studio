"""Qwen vision analysis contract for source-video director reconstruction.

The ordinary Media Pool BLIP pass is intentionally lightweight.  This module
defines the stronger, full-storyboard analysis used by
``source-video-cast-remake-h3`` before Director Design is allowed to run.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
import re
from typing import Any


SOURCE_VIDEO_QWEN_ANALYSIS_MARKER = "QWEN SOURCE VIDEO DIRECTOR ANALYSIS V5"
SOURCE_VIDEO_QWEN_ANALYSIS_MARKER_RE = re.compile(
    r"QWEN SOURCE VIDEO DIRECTOR ANALYSIS V(?P<version>\d+)",
    flags=re.I,
)


SOURCE_VIDEO_DIRECTOR_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "media_id", "evidence_fingerprint", "duration_seconds",
        "location_ledger", "principal_roles", "scenes",
        "global_camera_grammar", "edit_rhythm",
        "continuity_constraints", "uncertain_inferences",
    ],
    "properties": {
        "media_id": {"type": "string"},
        "evidence_fingerprint": {"type": "string"},
        "duration_seconds": {"type": "number"},
        "location_ledger": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "location_id", "description", "defining_elements",
                    "first_scene_index", "last_scene_index", "confidence",
                ],
                "properties": {
                    "location_id": {"type": "string"},
                    "description": {"type": "string", "maxLength": 320},
                    "defining_elements": {
                        "type": "array", "maxItems": 10,
                        "items": {"type": "string", "maxLength": 120},
                    },
                    "first_scene_index": {"type": "integer"},
                    "last_scene_index": {"type": "integer"},
                    "confidence": {"type": "string", "maxLength": 40},
                },
            },
        },
        "principal_roles": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "role_id", "visual_identity", "wardrobe",
                    "narrative_function", "scene_indexes", "confidence",
                    "representative_scene_index", "representative_panel",
                    "thumbnail_bbox_normalized", "appearance_evidence",
                ],
                "properties": {
                    "role_id": {"type": "string"},
                    "visual_identity": {"type": "string", "maxLength": 320},
                    "wardrobe": {"type": "string", "maxLength": 240},
                    "narrative_function": {"type": "string", "maxLength": 240},
                    "scene_indexes": {"type": "array", "items": {"type": "integer"}},
                    "confidence": {"type": "string", "maxLength": 40},
                    "representative_scene_index": {"type": "integer"},
                    "representative_panel": {
                        "type": "string",
                        "enum": ["early", "late", "midpoint"],
                    },
                    "thumbnail_bbox_normalized": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                    "appearance_evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "scene_index", "panel",
                                "thumbnail_bbox_normalized", "face_visibility",
                            ],
                            "properties": {
                                "scene_index": {"type": "integer"},
                                "panel": {
                                    "type": "string",
                                    "enum": ["early", "late", "midpoint"],
                                },
                                "thumbnail_bbox_normalized": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "minItems": 4,
                                    "maxItems": 4,
                                },
                                "face_visibility": {"type": "string", "maxLength": 48},
                            },
                        },
                    },
                },
            },
        },
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "scene_index", "start_seconds", "end_seconds", "location_id",
                    "active_source_roles", "visible_event", "action_causality",
                    "speaker_role", "listener_roles", "framing", "camera_angle",
                    "camera_movement", "environment_elements", "transition_out",
                    "confidence",
                ],
                "properties": {
                    "scene_index": {"type": "integer"},
                    "start_seconds": {"type": "number"},
                    "end_seconds": {"type": "number"},
                    "location_id": {"type": "string"},
                    "active_source_roles": {"type": "array", "items": {"type": "string"}},
                    "visible_event": {"type": "string", "maxLength": 320},
                    "action_causality": {"type": "string", "maxLength": 320},
                    "speaker_role": {"type": "string"},
                    "listener_roles": {"type": "array", "items": {"type": "string"}},
                    "framing": {"type": "string", "maxLength": 100},
                    "camera_angle": {"type": "string", "maxLength": 100},
                    "camera_movement": {"type": "string", "maxLength": 140},
                    "environment_elements": {
                        "type": "array", "maxItems": 10,
                        "items": {"type": "string", "maxLength": 120},
                    },
                    "transition_out": {"type": "string", "maxLength": 160},
                    "confidence": {"type": "string", "maxLength": 40},
                },
            },
        },
        "global_camera_grammar": {"type": "string", "maxLength": 500},
        "edit_rhythm": {"type": "string", "maxLength": 400},
        "continuity_constraints": {
            "type": "array", "maxItems": 20,
            "items": {"type": "string", "maxLength": 240},
        },
        "uncertain_inferences": {
            "type": "array", "maxItems": 20,
            "items": {"type": "string", "maxLength": 240},
        },
    },
}


SOURCE_VIDEO_DIRECTOR_ANALYSIS_SYSTEM_PROMPT = """You are a forensic visual director analysing complete source-video storyboard sheets for a MiniMax H3 cast reconstruction.

The attached images are consecutive chronological contact sheets. Read every labelled panel left-to-right and top-to-bottom on sheet 1, then continue with sheet 2 and sheet 3. Each panel label contains a source scene number and time range. A scene may have both an early and a late panel; compare them as one interval to recover facial performance, mouth activity, blocking changes and environment detail. The pixels are primary evidence. Metadata and automatic captions are secondary and may be wrong.

Return exactly one compact JSON object matching the supplied schema. Copy media_id and evidence_fingerprint verbatim. Produce one scenes row for every supplied source interval, in chronological order. Never merge away a short reaction cut and never invent an interval. Keep descriptive values to one short, evidence-based clause; do not repeat the same visual description across fields. Output size is a reliability constraint: complete every required row before adding detail.

Track recurring source people with stable neutral role IDs R1, R2, R3 and so on. Use clothing, face, body, screen position and adjacent-shot continuity together. Do not identify real people. Do not map roles to P1-P4; that happens later.

For every principal role, appearance_evidence must contain exactly one record for every scene_index in which that role appears. For each appearance choose the early, late or midpoint panel from that exact source interval where the role's face is largest and clearest. Return a tight approximately square normalized [left, top, right, bottom] crop around the face, hair and a small amount of shoulders. The coordinates are relative to the CONTENT OF THAT ONE LABELLED PANEL, not the complete contact sheet: [0,0] is the upper-left pixel inside the selected panel image and [1,1] is its lower-right pixel. Exclude the contact-sheet label, borders, neighbouring panels and background wherever possible. Never return a thin strip, a door, wall or full-body box when a readable face exists. face_visibility must briefly state front, three-quarter, profile, occluded or not-readable.

Also select the clearest appearance as representative_scene_index, representative_panel and thumbnail_bbox_normalized. Those representative coordinates obey the same single-panel coordinate system. Every crop is analysis UI evidence; only when the user explicitly chooses Keep original V1 face may Studio materialize the representative crop as a new P identity reference for H3.

Describe only visually supported events. A uniform or white coat does not prove a laboratory, hospital or office. Create a new location only when consecutive panels visibly establish different architecture. The user payload may contain audio timing evidence but never transcript words. Use its voice-active ranges only to decide whether speech exists in an interval; assign speaker_role only when the visible mouth/performance and stable role tracking support the assignment. A reaction shot must not automatically become the speaker merely because speech is audible. If evidence is ambiguous, retain the last established location, keep speaker_role empty, lower confidence and record the uncertainty.

For each scene, describe the visible setup/action/reaction/consequence rather than dialogue words. action_causality must state how the visible action enters from the preceding panel and hands off to the next one. camera_movement must be "static or indeterminate from sampled frames" unless the sequence provides visual evidence of a move. Do not infer camera motion from a crop change caused by an edit.

Do not reproduce subtitles, social-media UI, logos, transcript text, filenames, model names or analysis instructions. Do not use Markdown and do not add commentary outside the JSON object."""


def scene_intervals_from_breakdown(
    recognition: object,
    duration_seconds: float,
) -> list[tuple[float, float]]:
    """Return the authoritative chronological scene intervals in V1."""

    duration = max(0.0, float(duration_seconds or 0.0))
    marker = re.search(
        r"SOURCE VIDEO BREAKDOWN\s*·\s*full_duration=yes[^\n]*scene_cuts=([^\n]+)",
        str(recognition or ""),
        flags=re.I,
    )
    cuts: list[float] = []
    if marker and marker.group(1).strip().casefold() != "none":
        for value in re.findall(r"\d+(?:\.\d+)?", marker.group(1)):
            cut = float(value)
            if 0.01 < cut < duration - 0.01 and not any(abs(cut - prior) < 0.01 for prior in cuts):
                cuts.append(cut)
    boundaries = [0.0, *sorted(cuts), duration]
    return [
        (start, end)
        for start, end in zip(boundaries, boundaries[1:])
        if end > start + 0.01
    ]


def build_source_video_analysis_prompts(
    *,
    media_id: str,
    evidence_fingerprint: str,
    duration_seconds: float,
    scene_intervals: list[tuple[float, float]],
    recognition: object = "",
) -> tuple[str, str]:
    ledger = [
        {
            "scene_index": index,
            "start_seconds": round(float(start), 3),
            "end_seconds": round(float(end), 3),
        }
        for index, (start, end) in enumerate(scene_intervals, 1)
    ]
    payload = {
        "task": "Analyse every attached chronological V1 storyboard sheet in order.",
        "media_id": str(media_id).strip().upper(),
        "evidence_fingerprint": str(evidence_fingerprint).strip().lower(),
        "duration_seconds": round(float(duration_seconds), 6),
        "required_scene_intervals": ledger,
        "audio_timing_evidence": source_audio_timing_evidence(recognition),
    }
    return (
        SOURCE_VIDEO_DIRECTOR_ANALYSIS_SYSTEM_PROMPT,
        json.dumps(payload, ensure_ascii=False, indent=2),
    )


def source_audio_timing_evidence(recognition: object) -> dict[str, list[float] | list[list[float]]]:
    """Return timing-only speech evidence without leaking transcript words."""

    text = str(recognition or "")
    ranges: list[list[float]] = []
    match = re.search(r"Voice-active ranges:\s*([^\n]+)", text, flags=re.I)
    if match:
        for start, end in re.findall(
            r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)s", match.group(1)
        ):
            left, right = float(start), float(end)
            if right > left:
                ranges.append([round(left, 3), round(right, 3)])
    transcript_onsets = [
        round(float(minutes) * 60.0 + float(seconds), 3)
        for minutes, seconds in re.findall(
            r"^\[(\d{2}):(\d{2}(?:\.\d+)?)\]",
            text,
            flags=re.M,
        )
    ]
    return {
        "voice_active_ranges_seconds": ranges,
        "detected_utterance_onsets_seconds": transcript_onsets,
    }


def _plain(value: object, limit: int = 3000) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit]


def _string_list(value: object, maximum: int = 32, limit: int = 800) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value[:maximum]:
        text = _plain(item, limit)
        if text and text not in result:
            result.append(text)
    return result


def _decode(payload: Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(payload, Mapping):
        return dict(payload)
    text = str(payload or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, count=1, flags=re.I)
        text = re.sub(r"\s*```$", "", text, count=1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Qwen source-video analysis did not return a JSON object")
    candidate = text[start : end + 1]
    # LM Studio occasionally returns an otherwise schema-complete object with
    # one omitted comma in very long structured outputs. Repair only that
    # unambiguous parser condition, then let the strict normalizer validate all
    # scene counts, fingerprints and field types. Never guess missing text,
    # braces, quotes or truncated arrays.
    for _attempt in range(64):
        try:
            value = json.loads(candidate)
            break
        except json.JSONDecodeError as exc:
            if exc.msg != "Expecting ',' delimiter" or not (0 < exc.pos < len(candidate)):
                raise
            before = candidate[:exc.pos].rstrip()
            after = candidate[exc.pos:].lstrip()
            if (
                not before
                or not after
                or before[-1] in "[{,:"
                or after[0] in "]}:,"
            ):
                raise
            candidate = candidate[:exc.pos] + "," + candidate[exc.pos:]
    else:
        raise ValueError("Qwen source-video JSON contains too many missing delimiters")
    if not isinstance(value, dict):
        raise ValueError("Qwen source-video analysis must be a JSON object")
    return value


def normalize_source_video_analysis(
    payload: Mapping[str, Any] | str,
    *,
    expected_media_id: str,
    expected_fingerprint: str,
    duration_seconds: float,
    scene_intervals: list[tuple[float, float]],
) -> dict[str, Any]:
    source = _decode(payload)
    media_id = _plain(source.get("media_id"), 32).upper()
    fingerprint = _plain(source.get("evidence_fingerprint"), 128).lower()
    if media_id != str(expected_media_id).strip().upper():
        raise ValueError(f"Qwen analysis media_id {media_id!r} does not match {expected_media_id!r}")
    if fingerprint != str(expected_fingerprint).strip().lower():
        raise ValueError("Qwen source-video evidence changed while analysis was running")

    raw_scenes = source.get("scenes")
    if not isinstance(raw_scenes, list) or len(raw_scenes) != len(scene_intervals):
        raise ValueError(
            "Qwen source-video analysis must return exactly "
            f"{len(scene_intervals)} chronological scenes"
        )
    scenes: list[dict[str, Any]] = []
    for index, ((expected_start, expected_end), raw) in enumerate(
        zip(scene_intervals, raw_scenes), 1
    ):
        if not isinstance(raw, Mapping):
            raise ValueError(f"Qwen source-video scene {index} is not an object")
        scenes.append({
            "scene_index": index,
            "start_seconds": round(float(expected_start), 3),
            "end_seconds": round(float(expected_end), 3),
            "location_id": _plain(raw.get("location_id"), 64) or "L1",
            "active_source_roles": _string_list(raw.get("active_source_roles"), 12, 32),
            "visible_event": _plain(raw.get("visible_event")),
            "action_causality": _plain(raw.get("action_causality")),
            "speaker_role": _plain(raw.get("speaker_role"), 32),
            "listener_roles": _string_list(raw.get("listener_roles"), 12, 32),
            "framing": _plain(raw.get("framing"), 500),
            "camera_angle": _plain(raw.get("camera_angle"), 500),
            "camera_movement": _plain(raw.get("camera_movement"), 500),
            "environment_elements": _string_list(raw.get("environment_elements"), 24, 500),
            "transition_out": _plain(raw.get("transition_out"), 500),
            "confidence": _plain(raw.get("confidence"), 100) or "uncertain",
        })

    locations: list[dict[str, Any]] = []
    for raw in source.get("location_ledger") or []:
        if not isinstance(raw, Mapping):
            continue
        locations.append({
            "location_id": _plain(raw.get("location_id"), 64),
            "description": _plain(raw.get("description"), 2000),
            "defining_elements": _string_list(raw.get("defining_elements"), 32, 500),
            "first_scene_index": int(raw.get("first_scene_index", 1) or 1),
            "last_scene_index": int(raw.get("last_scene_index", len(scenes)) or len(scenes)),
            "confidence": _plain(raw.get("confidence"), 100) or "uncertain",
        })
    roles: list[dict[str, Any]] = []
    for raw in source.get("principal_roles") or []:
        if not isinstance(raw, Mapping):
            continue
        indexes = [
            int(value) for value in raw.get("scene_indexes") or []
            if isinstance(value, (int, float)) and 1 <= int(value) <= len(scenes)
        ]
        representative_scene_index = int(
            raw.get("representative_scene_index")
            or (indexes[0] if indexes else 1)
        )
        representative_scene_index = min(
            len(scenes), max(1, representative_scene_index)
        )
        representative_panel = _plain(
            raw.get("representative_panel"), 16
        ).casefold()
        if representative_panel not in {"early", "late", "midpoint"}:
            representative_panel = "midpoint"
        raw_bbox = raw.get("thumbnail_bbox_normalized")
        bbox = [0.0, 0.0, 1.0, 1.0]
        if isinstance(raw_bbox, list) and len(raw_bbox) == 4:
            try:
                left, top, right, bottom = (
                    min(1.0, max(0.0, float(value))) for value in raw_bbox
                )
            except (TypeError, ValueError):
                pass
            else:
                if right > left + 0.02 and bottom > top + 0.02:
                    bbox = [left, top, right, bottom]
        appearance_evidence: list[dict[str, Any]] = []
        for evidence in raw.get("appearance_evidence") or []:
            if not isinstance(evidence, Mapping):
                continue
            scene_index = int(evidence.get("scene_index", 0) or 0)
            if scene_index not in indexes:
                continue
            panel = _plain(evidence.get("panel"), 16).casefold()
            if panel not in {"early", "late", "midpoint"}:
                panel = "midpoint"
            evidence_bbox = [0.0, 0.0, 1.0, 1.0]
            raw_evidence_bbox = evidence.get("thumbnail_bbox_normalized")
            if isinstance(raw_evidence_bbox, list) and len(raw_evidence_bbox) == 4:
                try:
                    e_left, e_top, e_right, e_bottom = (
                        min(1.0, max(0.0, float(value)))
                        for value in raw_evidence_bbox
                    )
                except (TypeError, ValueError):
                    pass
                else:
                    if e_right > e_left + 0.02 and e_bottom > e_top + 0.02:
                        evidence_bbox = [e_left, e_top, e_right, e_bottom]
            appearance_evidence.append({
                "scene_index": scene_index,
                "panel": panel,
                "thumbnail_bbox_normalized": [
                    round(value, 4) for value in evidence_bbox
                ],
                "face_visibility": _plain(
                    evidence.get("face_visibility"), 120
                ) or "uncertain",
            })
        evidence_by_scene = {
            int(row["scene_index"]): row for row in appearance_evidence
        }
        for scene_index in sorted(set(indexes)):
            if scene_index not in evidence_by_scene:
                evidence_by_scene[scene_index] = {
                    "scene_index": scene_index,
                    "panel": (
                        representative_panel
                        if scene_index == representative_scene_index else "midpoint"
                    ),
                    "thumbnail_bbox_normalized": [round(value, 4) for value in bbox],
                    "face_visibility": "fallback representative crop",
                }
        roles.append({
            "role_id": _plain(raw.get("role_id"), 32),
            "visual_identity": _plain(raw.get("visual_identity"), 1600),
            "wardrobe": _plain(raw.get("wardrobe"), 1600),
            "narrative_function": _plain(raw.get("narrative_function"), 1600),
            "scene_indexes": sorted(set(indexes)),
            "confidence": _plain(raw.get("confidence"), 100) or "uncertain",
            "representative_scene_index": representative_scene_index,
            "representative_panel": representative_panel,
            "thumbnail_bbox_normalized": [round(value, 4) for value in bbox],
            "appearance_evidence": [
                evidence_by_scene[scene_index]
                for scene_index in sorted(evidence_by_scene)
            ],
        })
    return {
        "media_id": media_id,
        "evidence_fingerprint": fingerprint,
        "duration_seconds": round(float(duration_seconds), 6),
        "location_ledger": locations,
        "principal_roles": roles,
        "scenes": scenes,
        "global_camera_grammar": _plain(source.get("global_camera_grammar"), 3000),
        "edit_rhythm": _plain(source.get("edit_rhythm"), 3000),
        "continuity_constraints": _string_list(source.get("continuity_constraints"), 48, 1000),
        "uncertain_inferences": _string_list(source.get("uncertain_inferences"), 48, 1000),
    }


def render_source_video_analysis(payload: Mapping[str, Any]) -> str:
    return (
        SOURCE_VIDEO_QWEN_ANALYSIS_MARKER
        + "\n"
        + json.dumps(dict(payload), ensure_ascii=False, indent=2)
    )


def parse_source_video_analysis(value: object) -> dict[str, Any]:
    """Decode an embedded V1 ledger and upgrade older marker revisions.

    The marker version describes the analysis schema, not the source-media
    version.  Saved projects must therefore remain readable after the schema
    advances (for example V4 -> V5).  Some early/partial Qwen responses also
    contained valid scene role evidence without a top-level
    ``principal_roles`` array; recover that ledger deterministically so Apply
    does not report a false missing-analysis hard block.
    """

    text = str(value or "")
    matches = list(SOURCE_VIDEO_QWEN_ANALYSIS_MARKER_RE.finditer(text))
    for marker in reversed(matches):
        object_index = text.find("{", marker.end())
        if object_index < 0:
            continue
        try:
            decoded, _end = json.JSONDecoder().raw_decode(text[object_index:])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(decoded, dict):
            continue
        return _upgrade_parsed_source_video_analysis(decoded)
    return {}


def _upgrade_parsed_source_video_analysis(decoded: Mapping[str, Any]) -> dict[str, Any]:
    """Supply UI-critical role metadata missing from legacy/partial ledgers."""

    def _positive_int(value: object) -> int:
        try:
            parsed = int(value or 0)
        except (TypeError, ValueError, OverflowError):
            return 0
        return parsed if parsed > 0 else 0

    result = dict(decoded)
    scenes = [row for row in result.get("scenes") or [] if isinstance(row, dict)]
    valid_scene_indexes = {
        _positive_int(row.get("scene_index", 0))
        for row in scenes
        if _positive_int(row.get("scene_index", 0)) > 0
    }
    role_scene_indexes: dict[str, set[int]] = {}
    for scene in scenes:
        scene_index = _positive_int(scene.get("scene_index", 0))
        if scene_index <= 0:
            continue
        referenced = list(scene.get("active_source_roles") or [])
        referenced.extend(scene.get("listener_roles") or [])
        referenced.append(scene.get("speaker_role", ""))
        for value in referenced:
            role_id = str(value or "").strip().upper()
            if re.fullmatch(r"R[1-9][0-9]*", role_id):
                role_scene_indexes.setdefault(role_id, set()).add(scene_index)

    raw_roles = [
        dict(row) for row in result.get("principal_roles") or []
        if isinstance(row, dict)
    ]
    roles_by_id = {
        str(row.get("role_id", "")).strip().upper(): row
        for row in raw_roles
        if re.fullmatch(r"R[1-9][0-9]*", str(row.get("role_id", "")).strip().upper())
    }
    for role_id in sorted(role_scene_indexes, key=lambda value: int(value[1:])):
        roles_by_id.setdefault(role_id, {
            "role_id": role_id,
            "visual_identity": "Recovered from V1 scene evidence",
            "wardrobe": "",
            "narrative_function": "Principal source-video role recovered from scene evidence",
            "confidence": "recovered",
        })

    upgraded_roles: list[dict[str, Any]] = []
    for role_id, role in sorted(
        roles_by_id.items(), key=lambda item: int(item[0][1:])
    ):
        role["role_id"] = role_id
        indexes = {
            _positive_int(value) for value in role.get("scene_indexes") or []
            if _positive_int(value) in valid_scene_indexes
        }
        indexes.update(role_scene_indexes.get(role_id, set()))
        if not indexes:
            continue
        ordered_indexes = sorted(indexes)
        role["scene_indexes"] = ordered_indexes
        representative_scene_index = int(
            role.get("representative_scene_index", 0) or ordered_indexes[0]
        )
        if representative_scene_index not in indexes:
            representative_scene_index = ordered_indexes[0]
        role["representative_scene_index"] = representative_scene_index
        role.setdefault("representative_panel", "midpoint")
        role.setdefault("thumbnail_bbox_normalized", [0.0, 0.0, 1.0, 1.0])
        evidence_by_scene = {
            _positive_int(row.get("scene_index", 0)): dict(row)
            for row in role.get("appearance_evidence") or []
            if isinstance(row, dict)
            and _positive_int(row.get("scene_index", 0)) in indexes
        }
        for scene_index in ordered_indexes:
            evidence_by_scene.setdefault(scene_index, {
                "scene_index": scene_index,
                "panel": (
                    str(role.get("representative_panel") or "midpoint")
                    if scene_index == representative_scene_index else "midpoint"
                ),
                "thumbnail_bbox_normalized": list(
                    role.get("thumbnail_bbox_normalized") or [0.0, 0.0, 1.0, 1.0]
                ),
                "face_visibility": "legacy analysis fallback",
            })
        role["appearance_evidence"] = [
            evidence_by_scene[index] for index in ordered_indexes
        ]
        upgraded_roles.append(role)
    result["principal_roles"] = upgraded_roles
    return result

"""Akatz H3 Character Swap workflow integration helpers.

The published LoRA/workflow replaces one selected source character per pass.
Studio therefore compiles one deterministic pass per mapped V1 role that is
actually visible in the current Shot.  Multiple roles are processed
sequentially; the previous pass becomes the next pass's source video.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


CHARACTER_SWAP_WORKFLOW_NAME = (
    "akatz-labs-character-swap-turbo8-adaptive-window-api.json"
)
CHARACTER_SWAP_LORA_NAME = "h3_character_swap_v1.5.safetensors"
CHARACTER_SWAP_RELAY_CLASS = "H3RelayWindowedEdit"
CHARACTER_SWAP_PREPARE_CLASS = "LabsH3PrepareVideo"

SOURCE_REMAKE_MODE_CHARACTER_SWAP = "adaptive_character_swap"
SOURCE_REMAKE_MODE_DIRECTED_SWAP = "adaptive_character_swap_directed"
SOURCE_REMAKE_MODE_CREATIVE_H3 = "creative_h3"
SOURCE_REMAKE_MODES = {
    SOURCE_REMAKE_MODE_CHARACTER_SWAP,
    SOURCE_REMAKE_MODE_DIRECTED_SWAP,
    SOURCE_REMAKE_MODE_CREATIVE_H3,
}
SOURCE_VIDEO_CAST_REMAKE_SKILL_KEY = "source-video-cast-remake-h3"
KEEP_V1_TARGET = "KEEP_V1"

RELAY_FPS = 24
RELAY_WINDOW_FRAMES = 124
RELAY_HISTORY_FRAMES = 18
H3_FRAME_MODULUS = 17
H3_FRAME_REMAINDER = 5


def character_swap_relay_window_count(duration_seconds: float) -> int:
    """Return the adaptive Relay window count for one H3 Shot pass."""

    requested = max(5, round(max(0.0, float(duration_seconds)) * RELAY_FPS))
    frame_count = requested + (
        H3_FRAME_REMAINDER - (requested % H3_FRAME_MODULUS)
    ) % H3_FRAME_MODULUS
    advance = max(1, RELAY_WINDOW_FRAMES - RELAY_HISTORY_FRAMES)
    if frame_count <= RELAY_WINDOW_FRAMES:
        return 1
    return 1 + max(
        0,
        (frame_count - RELAY_WINDOW_FRAMES + advance - 1) // advance,
    )


def automatic_remake_engine_for_skill(special_skill_key: object) -> str:
    """Select the only valid Remake Engine for the active Special Skill.

    Character Swap Relay is intentionally exclusive to Source Video Cast
    Remake H3 because that Skill supplies the V1 role ledger, exact source
    Shot plate and synchronized source-audio contract. Every other selection,
    including no Special Skill, stays on Studio's ordinary Create H3 Remake
    compiler.
    """

    normalized = str(special_skill_key or "").strip().casefold()
    if normalized == SOURCE_VIDEO_CAST_REMAKE_SKILL_KEY:
        return SOURCE_REMAKE_MODE_CHARACTER_SWAP
    return SOURCE_REMAKE_MODE_CREATIVE_H3


def load_character_swap_workflow(path: str | Path) -> dict[str, dict[str, Any]]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    if isinstance(payload.get("prompt"), dict):
        payload = payload["prompt"]
    if not isinstance(payload, dict):
        raise ValueError("Character Swap workflow is not an API-format object.")
    nodes = {
        str(node_id): deepcopy(node)
        for node_id, node in payload.items()
        if isinstance(node, dict) and isinstance(node.get("class_type"), str)
    }
    classes = {str(node.get("class_type", "")) for node in nodes.values()}
    required = {
        "LoadVideo", "LoadImage", "PrimitiveStringMultiline",
        CHARACTER_SWAP_PREPARE_CLASS, CHARACTER_SWAP_RELAY_CLASS, "SaveVideo",
    }
    missing = sorted(required - classes)
    if missing:
        raise ValueError(
            "Character Swap API workflow is missing required nodes: "
            + ", ".join(missing)
        )
    return nodes


def node_id_for_class(
    workflow: Mapping[str, Mapping[str, Any]],
    class_type: str,
) -> str:
    matches = [
        str(node_id) for node_id, node in workflow.items()
        if str(node.get("class_type", "")) == class_type
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Character Swap workflow requires exactly one {class_type}; "
            f"found {len(matches)}."
        )
    return matches[0]


def _role_rows(analysis: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("role_id", "")).strip().upper(): row
        for row in analysis.get("principal_roles") or []
        if isinstance(row, Mapping) and str(row.get("role_id", "")).strip()
    }


def _normalized_person_bbox(value: object) -> list[float]:
    """Return a usable source-frame bbox and reject synthetic full-frame crops."""

    try:
        left, top, right, bottom = [float(item) for item in value][:4]
    except (TypeError, ValueError, OverflowError):
        return []
    left, top = max(0.0, left), max(0.0, top)
    right, bottom = min(1.0, right), min(1.0, bottom)
    if right <= left or bottom <= top:
        return []
    # Qwen and old Shot scans used [0,0,1,1] when localization failed. Passing
    # that to Relay makes it interpret the complete scene as the actor and may
    # insert Picture 1 beside the source performer instead of replacing them.
    if left <= 0.001 and top <= 0.001 and right >= 0.999 and bottom >= 0.999:
        return []
    return [left, top, right, bottom]


def character_swap_passes_for_window(
    analysis: Mapping[str, Any],
    bindings: Iterable[Mapping[str, Any]],
    start_seconds: float,
    end_seconds: float,
    *,
    selected_role_ids: Iterable[str] | None = None,
    source_bbox_overrides: Mapping[str, object] | None = None,
) -> list[dict[str, Any]]:
    """Return one ordered character-swap pass per visible, mapped V1 role."""

    selected_roles = {
        str(role or "").strip().upper()
        for role in (selected_role_ids or [])
        if str(role or "").strip()
    }
    bbox_overrides = {
        str(role or "").strip().upper(): _normalized_person_bbox(value)
        for role, value in (source_bbox_overrides or {}).items()
        if str(role or "").strip()
    }
    bbox_overrides = {
        role: bbox for role, bbox in bbox_overrides.items() if bbox
    }

    scenes: list[Mapping[str, Any]] = []
    for scene in analysis.get("scenes") or []:
        if not isinstance(scene, Mapping):
            continue
        try:
            left = float(scene.get("start_seconds", 0.0) or 0.0)
            right = float(scene.get("end_seconds", left) or left)
        except (TypeError, ValueError, OverflowError):
            continue
        if left < end_seconds - 1e-9 and right > start_seconds + 1e-9:
            scenes.append(scene)
    scene_indexes = {
        int(scene.get("scene_index", 0) or 0) for scene in scenes
    }
    visible_roles: list[str] = []
    speaker_roles: set[str] = set()
    events_by_role: dict[str, list[str]] = {}
    for scene in scenes:
        speaker = str(scene.get("speaker_role", "") or "").strip().upper()
        if speaker:
            speaker_roles.add(speaker)
        visible_event = " ".join(str(scene.get("visible_event", "") or "").split())
        for role in scene.get("active_source_roles") or []:
            normalized = str(role or "").strip().upper()
            if not normalized:
                continue
            if normalized not in visible_roles:
                visible_roles.append(normalized)
            if visible_event:
                events_by_role.setdefault(normalized, []).append(visible_event)
    # Keep the complete cast before applying the user's SWAP subset.  The old
    # code filtered first and then called a selected actor "the only existing
    # foreground person".  In a two-person frame that instruction authorizes
    # H3 to absorb or redraw the listener and is a major source of cross-role
    # interference.
    all_visible_roles = list(visible_roles)
    if selected_roles:
        visible_roles = [role for role in visible_roles if role in selected_roles]
    sole_visible_role = len(all_visible_roles) == 1

    mapped: dict[str, str] = {}
    keep_v1_roles: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, Mapping):
            continue
        role = str(binding.get("source_role_id", "") or "").strip().upper()
        target = str(binding.get("target_media_id", "") or "").strip().upper()
        indexes = {
            int(value) for value in binding.get("scene_indexes") or []
            if isinstance(value, (int, float))
        }
        keep_v1 = bool(binding.get("source_thumbnail", False)) or (
            target == KEEP_V1_TARGET
        )
        if (
            role in all_visible_roles
            and (not indexes or bool(indexes & scene_indexes))
            and keep_v1
        ):
            keep_v1_roles.add(role)
            # KEEP V1 is authoritative for this role/scene.  It must never be
            # materialized as a P Picture or compiled into a LoRA pass.
            mapped.pop(role, None)
            continue
        if (
            role in visible_roles
            and target.startswith("P")
            and (not indexes or bool(indexes & scene_indexes))
            and role not in keep_v1_roles
        ):
            mapped.setdefault(role, target)

    roles = _role_rows(analysis)
    role_passes: list[dict[str, Any]] = []
    for role in visible_roles:
        target = mapped.get(role, "")
        if not target:
            continue
        evidence = roles.get(role, {})
        track_samples: list[dict[str, Any]] = []
        rejected_full_frame_track = False
        for track in evidence.get("shot_scan_tracks") or []:
            if not isinstance(track, Mapping):
                continue
            for sample in track.get("samples") or []:
                if not isinstance(sample, Mapping):
                    continue
                try:
                    sample_time = float(sample.get("time_seconds", 0.0) or 0.0)
                except (TypeError, ValueError, OverflowError):
                    continue
                if sample_time < start_seconds - 0.25 or sample_time > end_seconds + 0.25:
                    continue
                raw_bbox = sample.get("bbox_normalized") or []
                bbox_values = _normalized_person_bbox(raw_bbox)
                if not bbox_values:
                    try:
                        raw_values = [float(value) for value in raw_bbox][:4]
                    except (TypeError, ValueError, OverflowError):
                        raw_values = []
                    rejected_full_frame_track = rejected_full_frame_track or (
                        raw_values == [0.0, 0.0, 1.0, 1.0]
                    )
                    continue
                track_samples.append({
                    "frame_index": int(sample.get("frame_index", 0) or 0),
                    "time_seconds": sample_time,
                    "bbox_normalized": bbox_values,
                })
        track_samples.sort(key=lambda row: row["time_seconds"])
        if len(track_samples) > 6:
            positions = {
                round(index * (len(track_samples) - 1) / 5)
                for index in range(6)
            }
            track_samples = [track_samples[index] for index in sorted(positions)]
        scene_bbox: list[float] = []
        for appearance in evidence.get("appearance_evidence") or []:
            if not isinstance(appearance, Mapping):
                continue
            try:
                appearance_scene = int(appearance.get("scene_index", 0) or 0)
            except (TypeError, ValueError, OverflowError):
                continue
            if appearance_scene not in scene_indexes:
                continue
            scene_bbox = _normalized_person_bbox(
                appearance.get("thumbnail_bbox_normalized") or []
            )
            if scene_bbox:
                break
        if not scene_bbox:
            scene_bbox = _normalized_person_bbox(
                evidence.get("thumbnail_bbox_normalized") or []
            )
        source_bbox = (
            list(track_samples[0]["bbox_normalized"])
            if track_samples else ([] if sole_visible_role else scene_bbox)
        )
        if role in bbox_overrides:
            # Shot Visual Editor owns the explicit manual rectangle. Remove
            # older Qwen anchors from the prompt so they cannot compete with
            # the box the user deliberately placed on this Shot.
            source_bbox = list(bbox_overrides[role])
            track_samples = []
        edge_truncated = bool(rejected_full_frame_track)
        for bbox in [source_bbox, *[
            row.get("bbox_normalized") or [] for row in track_samples
        ]]:
            if len(bbox) == 4:
                edge_truncated = edge_truncated or (
                    float(bbox[0]) <= 0.015 or float(bbox[1]) <= 0.015
                    or float(bbox[2]) >= 0.985 or float(bbox[3]) >= 0.985
                )
        role_passes.append({
            "source_role_id": role,
            "target_media_id": target,
            "source_visual_identity": " ".join(
                str(evidence.get("visual_identity", "") or "").split()
            ),
            "source_wardrobe": " ".join(
                str(evidence.get("wardrobe", "") or "").split()
            ),
            "source_narrative_function": " ".join(
                str(evidence.get("narrative_function", "") or "").split()
            ),
            "source_bbox_normalized": source_bbox,
            "source_track_samples": track_samples,
            "source_is_sole_visible_person": sole_visible_role,
            "source_edge_truncated": edge_truncated,
            "source_events": list(dict.fromkeys(events_by_role.get(role, [])))[:4],
            "scene_indexes": sorted(scene_indexes),
            "speaker": role in speaker_roles,
        })

    # A single P Picture is one requested identity, even when the user assigns
    # it to several source bodies. Running a complete Relay generation once per
    # role made duplicate mappings both prohibitively slow and destructive:
    # later passes could redraw a replacement already established by an earlier
    # pass. Group those roles into one explicit multi-person identity pass.
    grouped: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in role_passes:
        target = str(row["target_media_id"])
        if target not in grouped:
            grouped[target] = {
                "source_role_id": "",
                "source_role_ids": [],
                "source_roles": [],
                "target_media_id": target,
                "source_events": [],
                "scene_indexes": sorted(scene_indexes),
                "speaker": False,
            }
            order.append(target)
        group = grouped[target]
        group["source_role_ids"].append(row["source_role_id"])
        group["source_roles"].append({
            key: row.get(key)
            for key in (
                "source_role_id", "source_visual_identity", "source_wardrobe",
                "source_narrative_function", "source_bbox_normalized",
                "source_track_samples", "source_is_sole_visible_person",
                "source_edge_truncated",
            )
        })
        group["source_events"] = list(dict.fromkeys(
            [*group["source_events"], *row.get("source_events", [])]
        ))[:6]
        group["speaker"] = bool(group["speaker"] or row.get("speaker"))
    def protected_role_row(role_id: str) -> dict[str, Any]:
        evidence = roles.get(role_id, {})
        source_bbox = list(bbox_overrides.get(role_id) or [])
        if not source_bbox:
            for track in evidence.get("shot_scan_tracks") or []:
                if not isinstance(track, Mapping):
                    continue
                for sample in track.get("samples") or []:
                    if not isinstance(sample, Mapping):
                        continue
                    try:
                        sample_time = float(sample.get("time_seconds", 0.0) or 0.0)
                    except (TypeError, ValueError, OverflowError):
                        continue
                    if (
                        sample_time >= start_seconds - 0.25
                        and sample_time <= end_seconds + 0.25
                    ):
                        source_bbox = _normalized_person_bbox(
                            sample.get("bbox_normalized") or []
                        )
                        if source_bbox:
                            break
                if source_bbox:
                    break
        if not source_bbox:
            for appearance in evidence.get("appearance_evidence") or []:
                if not isinstance(appearance, Mapping):
                    continue
                try:
                    appearance_scene = int(appearance.get("scene_index", 0) or 0)
                except (TypeError, ValueError, OverflowError):
                    continue
                if appearance_scene not in scene_indexes:
                    continue
                source_bbox = _normalized_person_bbox(
                    appearance.get("thumbnail_bbox_normalized") or []
                )
                if source_bbox:
                    break
        if not source_bbox:
            source_bbox = _normalized_person_bbox(
                evidence.get("thumbnail_bbox_normalized") or []
            )
        return {
            "source_role_id": role_id,
            "source_visual_identity": " ".join(
                str(evidence.get("visual_identity", "") or "").split()
            ),
            "source_bbox_normalized": source_bbox,
            "keep_v1": role_id in keep_v1_roles,
        }

    protection_rows = {
        role_id: protected_role_row(role_id) for role_id in all_visible_roles
    }
    result = [grouped[target] for target in order]
    for row in result:
        row["source_role_id"] = "+".join(row["source_role_ids"])
        target_roles = set(row["source_role_ids"])
        row["protected_source_roles"] = [
            protection_rows[role_id]
            for role_id in all_visible_roles
            if role_id not in target_roles
        ]
    # Replace non-speakers first. The final pass owns the visible speaking
    # face(s), so it receives the cleanest source-audio/mouth alignment.
    result.sort(key=lambda row: (
        bool(row.get("speaker")),
        min(visible_roles.index(role) for role in row["source_role_ids"]),
    ))
    return result


def build_character_swap_prompt(
    pass_spec: Mapping[str, Any],
    *,
    directed_scene_text: str = "",
    live_action_adaptation: bool = False,
) -> str:
    role = str(pass_spec.get("source_role_id", "") or "").strip().upper()
    source_roles = [
        row for row in pass_spec.get("source_roles") or []
        if isinstance(row, Mapping)
    ]
    if not source_roles:
        source_roles = [{
            "source_role_id": role,
            "source_visual_identity": pass_spec.get("source_visual_identity", ""),
            "source_wardrobe": pass_spec.get("source_wardrobe", ""),
            "source_narrative_function": pass_spec.get("source_narrative_function", ""),
            "source_bbox_normalized": pass_spec.get("source_bbox_normalized", []),
            "source_track_samples": pass_spec.get("source_track_samples", []),
            "source_is_sole_visible_person": pass_spec.get(
                "source_is_sole_visible_person", False
            ),
            "source_edge_truncated": pass_spec.get("source_edge_truncated", False),
        }]
    events = [
        str(value).strip()
        for value in pass_spec.get("source_events") or []
        if str(value).strip()
    ]

    selectors: list[str] = []
    for source_role in source_roles:
        source_role_id = str(source_role.get("source_role_id", "") or "").strip().upper()
        identity = " ".join(str(source_role.get("source_visual_identity", "") or "").split())
        wardrobe = " ".join(str(source_role.get("source_wardrobe", "") or "").split())
        function = " ".join(str(source_role.get("source_narrative_function", "") or "").split())
        sole_visible = bool(source_role.get("source_is_sole_visible_person", False))
        edge_truncated = bool(source_role.get("source_edge_truncated", False))
        bbox = source_role.get("source_bbox_normalized") or []
        location = ""
        if len(bbox) == 4:
            try:
                x1, y1, x2, y2 = (float(value) for value in bbox)
                location = (
                    f"source-frame box x={round(x1 * 100)}-{round(x2 * 100)}%, "
                    f"y={round(y1 * 100)}-{round(y2 * 100)}%"
                )
            except (TypeError, ValueError):
                location = ""
        track_anchors: list[str] = []
        for sample in source_role.get("source_track_samples") or []:
            if not isinstance(sample, Mapping):
                continue
            sample_bbox = sample.get("bbox_normalized") or []
            if len(sample_bbox) != 4:
                continue
            try:
                time_seconds = float(sample.get("time_seconds", 0.0) or 0.0)
                x1, y1, x2, y2 = (float(value) for value in sample_bbox)
            except (TypeError, ValueError, OverflowError):
                continue
            track_anchors.append(
                f"{time_seconds:.3f}s box x={round(x1 * 100)}-{round(x2 * 100)}%, "
                f"y={round(y1 * 100)}-{round(y2 * 100)}%"
            )
        tracking = (
            "tracked anchors " + " | ".join(track_anchors[:6])
            if track_anchors else ""
        )
        source_position = (
            "the only existing physical foreground performer in Video 1"
            if sole_visible else ""
        )
        crop_state = (
            "intentionally cropped by the source frame edge"
            if edge_truncated else ""
        )
        description = ", ".join(part for part in (
            source_position, function, identity, wardrobe, crop_state,
            location, tracking,
        ) if part)
        selectors.append(f"{source_role_id}: {description}" if description else source_role_id)
    selector = "; ".join(selectors) or f"the source performer tracked as {role}"
    event_selector = " ".join(events[:2])
    directed = " ".join(str(directed_scene_text or "").split())
    protected_rows = [
        row for row in pass_spec.get("protected_source_roles") or []
        if isinstance(row, Mapping)
    ]
    protected_selectors: list[str] = []
    for protected in protected_rows:
        protected_role = str(
            protected.get("source_role_id", "") or ""
        ).strip().upper()
        protected_identity = " ".join(
            str(protected.get("source_visual_identity", "") or "").split()
        )
        keep_v1 = bool(protected.get("keep_v1", False))
        protected_bbox = protected.get("source_bbox_normalized") or []
        protected_location = ""
        if len(protected_bbox) == 4:
            try:
                x1, y1, x2, y2 = (float(value) for value in protected_bbox)
                protected_location = (
                    f"protected box x={round(x1 * 100)}-{round(x2 * 100)}%, "
                    f"y={round(y1 * 100)}-{round(y2 * 100)}%"
                )
            except (TypeError, ValueError, OverflowError):
                protected_location = ""
        protected_description = ", ".join(
            value for value in (
                "KEEP V1 — preserve the original source actor exactly" if keep_v1 else "",
                protected_identity,
                protected_location,
            ) if value
        )
        protected_selectors.append(
            f"{protected_role}: {protected_description}"
            if protected_description else protected_role
        )
    protected_contract = ""
    if protected_selectors:
        protected_contract = """

MULTI-PERSON IDENTITY ISOLATION — MANDATORY:
This pass may modify only the selected source performer(s) named above. Every other visible person is a protected non-target and must remain pixel-position, face, body, wardrobe, pose, expression and identity stable through this pass: %s. Do not transfer Picture 1 identity, face, hair, clothing or colour into a protected person. Do not merge adjacent bodies, exchange faces, duplicate the target, or use a protected person's mouth or head as the replacement destination. When target and protected boxes overlap, follow the selected performer's original body contour inside the selected target box; preserve the person outside that contour. A later character-swap pass may already have replaced a protected person, so preserve the current input pixels rather than restoring the original V1 actor.
""" % "; ".join(protected_selectors)
    # Keep the author workflow's explicit Subject contract.  A previous compact
    # rewrite let H3 keep the V1 face while importing Picture 1's room, which is
    # exactly the inverse of a character swap.  The separation below makes the
    # identity-only and source-world responsibilities unambiguous.
    if len(source_roles) > 1:
        target_clause = (
            f"Replace each of these {len(source_roles)} distinct selected source "
            f"performers in <Video 1> with the same character from <Picture 1>: "
            f"{selector}. Keep them as separate bodies in their original screen positions."
        )
    else:
        sole_visible = bool(source_roles[0].get(
            "source_is_sole_visible_person", False
        ))
        target_clause = (
            "Replace only this selected source performer in <Video 1> with the "
            f"character shown in <Picture 1>: {selector}."
        )
        if sole_visible:
            target_clause += (
                " The target is the only existing foreground person in the source "
                "frame, including when only half of that person is visible."
            )
    if event_selector:
        target_clause += " Target-performance evidence: " + event_selector

    medium_contract = ""
    if live_action_adaptation:
        medium_contract = """

ILLUSTRATED-CAST TO LIVE-ACTION CONTRACT:
<Picture 1> may be a cartoon, anime, comic, cel-shaded or otherwise illustrated design. Preserve its semantic identity cues—apparent age, moustache or facial-hair design, hairstyle silhouette and colour, facial proportions, wardrobe design, colour blocking and signature accessories—but do not preserve its drawing medium as pixels. Reconstruct Subject 1 as a physically plausible live-action human photographed in the same production as <Video 1>. Use realistic anatomy and head-to-body scale, dimensional skin, individual hair, real cloth weave, natural pores, subsurface skin colour, scene-matched highlights and shadows, lens softness, depth of field, motion blur and film grain. Match Video 1 exposure, white balance, shadow direction, edge softness and occlusion. No pasted cartoon head, sticker edge, black ink outline, flat cel shading, paper cutout, oversized head, illustrated hands or mixed 2D/photographic surfaces. The result must remain recognisable as the Picture 1 character's live-action film interpretation.
"""

    prompt = f"""{target_clause}

IN-PLACE REPLACEMENT — MANDATORY:
This is an identity transformation of the already-visible source performer, not an insertion, compositing or cast-addition request. Transform that performer's original pixels at the original screen coordinates. Never add Picture 1 as a second person elsewhere in the frame, never leave the original actor beside the replacement, and never move the replacement toward the centre or an empty side of the image. If the source performer is partially outside the frame, preserve the exact frame-edge truncation: replace only the visible face/body portion and keep the missing portion outside the image. Do not complete the cropped body, zoom out, reframe or create an extra full-body figure.

subject_definitions:
<Subject 1> is the replacement character. Its identity comes exclusively from the person visible in <Picture 1>: facial structure, apparent age, skin tone, hairstyle, body identity, clothing, colours and distinctive character design. <Picture 1> supplies identity only. Discard every reference-image pixel outside that character. Never import Picture 1's room, background, lighting, camera, crop, pose, expression or props.
<Subject 2> is the source world from <Video 1>: background, architecture, lighting, objects, framing, camera movement and every non-target person. Preserve it from the source video.
<Video 1> supplies the selected performer's position, scale, body pose, gestures, head turns, gaze, blinking, expression, visible mouth timing and complete action clock. It does not supply the selected performer's identity after replacement.
{medium_contract}
{protected_contract}

summary:
[video editing + reference character replacement] Replace the selected source identity with <Subject 1>. Preserve <Subject 2> and the exact source performance. The final face must be recognisably the Picture 1 character, never the original Video 1 actor. The final environment must remain the Video 1 environment, never the Picture 1 background.

retention_analysis:
<Subject 1> (throughout [Shot 1]): fully_preserved identity from Picture 1.
<Subject 2> (throughout [Shot 1]): fully_preserved source scene from Video 1.
<Video 1>: preserve composition, camera, motion, expressions, mouth timing, action timing, duration and soundtrack; replace only the selected identity.

[Shot 1]
Begin with the same composition and viewpoint as <Video 1>. Put <Subject 1> exactly where the selected source performer stands and transfer the performance moment by moment. Maintain Picture 1 facial identity through every expression, occlusion and viewing angle. Adapt only Subject 1's illumination and perspective so the replacement belongs naturally in the Video 1 scene. Preserve interactions and foreground/background occlusion order. Do not replace, blend, merge, duplicate or restyle any non-target person. Do not show Picture 1 itself or any part of its background.

overall_soundscape:
Retain Video 1's existing synchronized sound without adding dialogue, narration or effects.

non_diegetic_music:
Retain Video 1's existing music, if present; add no new music."""
    if directed:
        prompt += (
            " After the identity swap, apply only this authored direction without changing "
            "the performance clock or protected cast: " + directed
        )
    if live_action_adaptation:
        prompt += (
            " FINAL MEDIUM PRIORITY: whenever another instruction says preserve the Picture "
            "exactly, preserve its character identity and signature design only; the visible "
            "rendering medium must remain physically realistic live-action cinema."
        )
    return prompt


def compile_character_swap_pass(
    template: Mapping[str, Mapping[str, Any]],
    *,
    source_filename: str,
    reference_filename: str,
    prompt: str,
    seed: int,
    megapixels: float,
    output_prefix: str,
    runtime_source: bool = False,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Patch one API-format adaptive-window workflow for one character pass."""

    workflow = deepcopy(dict(template))
    video_id = node_id_for_class(workflow, "LoadVideo")
    image_id = node_id_for_class(workflow, "LoadImage")
    prompt_id = node_id_for_class(workflow, "PrimitiveStringMultiline")
    prepare_id = node_id_for_class(workflow, CHARACTER_SWAP_PREPARE_CLASS)
    relay_id = node_id_for_class(workflow, CHARACTER_SWAP_RELAY_CLASS)
    save_id = node_id_for_class(workflow, "SaveVideo")

    workflow[video_id].setdefault("inputs", {})["file"] = (
        "__H3_RELAY_PREVIOUS_PASS__.mp4" if runtime_source else source_filename
    )
    workflow[image_id].setdefault("inputs", {})["image"] = reference_filename
    workflow[prompt_id].setdefault("inputs", {})["value"] = prompt
    prepare = workflow[prepare_id].setdefault("inputs", {})
    prepare["resolution"] = "768" if float(megapixels) >= 0.75 else "480"
    prepare["duration_seconds"] = 0
    relay = workflow[relay_id].setdefault("inputs", {})
    relay.update({
        "window_frames": str(RELAY_WINDOW_FRAMES),
        "history_frames": str(RELAY_HISTORY_FRAMES),
        "seed": int(seed),
        "steps": 8,
        "cfg": 1,
        "scheduler": "simple",
        "denoise": 1,
        # Never reuse record ids exported from another Project/source clip.
        "window_controls": "{}",
    })
    workflow[save_id].setdefault("inputs", {})["filename_prefix"] = output_prefix
    return workflow, {
        "source_loader_node_id": video_id,
        "source_loader_input": "file",
        "reference_loader_node_id": image_id,
        "reference_loader_input": "image",
        "relay_node_id": relay_id,
    }


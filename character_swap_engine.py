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


def character_swap_passes_for_window(
    analysis: Mapping[str, Any],
    bindings: Iterable[Mapping[str, Any]],
    start_seconds: float,
    end_seconds: float,
) -> list[dict[str, Any]]:
    """Return one ordered character-swap pass per visible, mapped V1 role."""

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

    mapped: dict[str, str] = {}
    for binding in bindings:
        if not isinstance(binding, Mapping):
            continue
        role = str(binding.get("source_role_id", "") or "").strip().upper()
        target = str(binding.get("target_media_id", "") or "").strip().upper()
        indexes = {
            int(value) for value in binding.get("scene_indexes") or []
            if isinstance(value, (int, float))
        }
        if (
            role in visible_roles
            and target.startswith("P")
            and (not indexes or bool(indexes & scene_indexes))
        ):
            mapped.setdefault(role, target)

    roles = _role_rows(analysis)
    role_passes: list[dict[str, Any]] = []
    for role in visible_roles:
        target = mapped.get(role, "")
        if not target:
            continue
        evidence = roles.get(role, {})
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
            "source_bbox_normalized": list(
                evidence.get("thumbnail_bbox_normalized") or []
            )[:4],
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
            )
        })
        group["source_events"] = list(dict.fromkeys(
            [*group["source_events"], *row.get("source_events", [])]
        ))[:6]
        group["speaker"] = bool(group["speaker"] or row.get("speaker"))
    result = [grouped[target] for target in order]
    for row in result:
        row["source_role_id"] = "+".join(row["source_role_ids"])
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
        description = ", ".join(
            part for part in (function, identity, wardrobe, location) if part
        )
        selectors.append(f"{source_role_id}: {description}" if description else source_role_id)
    selector = "; ".join(selectors) or f"the source performer tracked as {role}"
    event_selector = " ".join(events[:2])
    directed = " ".join(str(directed_scene_text or "").split())
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
        target_clause = (
            "Replace only this selected source performer in <Video 1> with the "
            f"character shown in <Picture 1>: {selector}."
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

subject_definitions:
<Subject 1> is the replacement character. Its identity comes exclusively from the person visible in <Picture 1>: facial structure, apparent age, skin tone, hairstyle, body identity, clothing, colours and distinctive character design. <Picture 1> supplies identity only. Discard every reference-image pixel outside that character. Never import Picture 1's room, background, lighting, camera, crop, pose, expression or props.
<Subject 2> is the source world from <Video 1>: background, architecture, lighting, objects, framing, camera movement and every non-target person. Preserve it from the source video.
<Video 1> supplies the selected performer's position, scale, body pose, gestures, head turns, gaze, blinking, expression, visible mouth timing and complete action clock. It does not supply the selected performer's identity after replacement.
{medium_contract}

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
        "window_frames": "124",
        "history_frames": "18",
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


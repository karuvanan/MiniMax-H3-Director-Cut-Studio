"""Deterministic planning and exact-master-audio rules for singing MVs."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import subprocess


MTV_SINGING_SPECIAL_SKILL = "mtv-singing-h3"
MTV_A1_DURATION_TEMPLATE_TOKEN = "{{MTV_A1_DURATION}}"

MTV_MASTER_AUDIO_CONTRACT = (
    "A1 EXACT MASTER AUDIO: @A1 is the only soundtrack and the authoritative sung "
    "performance. Preserve its original vocal, lyrics, melody, pitch, key, tempo, rhythm, "
    "phrasing, breaths, timing, instrumentation and duration window. Use it to drive visible "
    "performance and lip motion, but never regenerate, imitate, transpose, time-stretch, loop, "
    "restart, replace or layer a second song or singer over it. The final movie must carry the "
    "original A1 Timeline window instead of H3's newly synthesized song audio."
)

MTV_CAST_SCENE_CONTRACT = (
    "MTV REFERENCE ROLE LOCK: S1 is exactly @P1 and is the sole lead singer. Preserve P1's "
    "recognizable face, age, hair, body, complete wardrobe and accessories in every frame; keep "
    "P1's mouth, jaw, breath, expression and gestures visibly synchronized to A1. @P2 and @P3 "
    "are supporting people only and must keep their own identities; they do not sing or copy P1's "
    "mouth motion unless separately authored. @P4 is the authoritative scene plate for geometry, "
    "camera axis, colour, colour temperature, weather, lighting and atmosphere. Never exchange "
    "the roles of P1-P4 and never generate a substitute lead singer."
)


def is_mtv_singing_skill(value: object) -> bool:
    return str(value or "").strip().casefold() == MTV_SINGING_SPECIAL_SKILL


def _media_id(value: object) -> str:
    return str(value or "").strip().upper().lstrip("@").replace("<", "").replace(">", "")


def _row_value(row: object, name: str, default=None):
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def _inventory(existing_media: list[dict] | None) -> dict[str, object]:
    result: dict[str, object] = {}
    for row in existing_media or []:
        media_id = _media_id(
            _row_value(row, "media_id", "") or _row_value(row, "reference_id", "")
        )
        if media_id:
            result[media_id] = row
    return result


def _loaded(row: object | None) -> bool:
    if row is None:
        return False
    path = str(_row_value(row, "local_path", "") or "").strip()
    return bool(
        _row_value(
            row,
            "loaded",
            _row_value(row, "locally_available", bool(path)),
        )
        or path
    )


def mtv_master_audio_duration(existing_media: list[object] | None) -> float | None:
    """Return A1's authoritative playable source duration for MTV planning.

    The source recording length outranks the current Timeline length. This is
    important when a 120-second A1 is first loaded into a 12-second workspace:
    media preparation temporarily clips its Timeline placement, but the MTV
    Design must still expand to the complete song before Apply.
    """

    for row in existing_media or []:
        media_id = _media_id(
            _row_value(row, "media_id", "")
            or _row_value(row, "reference_id", "")
        )
        media_type = str(_row_value(row, "media_type", "") or "").casefold()
        if media_id != "A1" or media_type != "audio" or not _loaded(row):
            continue
        source_duration = float(
            _row_value(row, "source_duration_seconds", 0.0) or 0.0
        )
        source_in = max(
            0.0, float(_row_value(row, "source_in_seconds", 0.0) or 0.0)
        )
        source_out = float(_row_value(row, "source_out_seconds", 0.0) or 0.0)
        # An explicit source trim is an authored A1 window. Otherwise the
        # complete probed recording is the duration authority.
        if source_out > source_in + 0.01:
            available = source_out - source_in
        elif source_duration > source_in + 0.01:
            available = source_duration - source_in
        else:
            start = float(_row_value(row, "start_seconds", 0.0) or 0.0)
            end = float(_row_value(row, "end_seconds", 0.0) or 0.0)
            available = end - start
        if available > 0.01:
            return round(max(0.5, available), 3)
    return None


def _append_once(text: object, clause: str) -> str:
    source = str(text or "").strip()
    if clause.casefold() in source.casefold():
        return source
    return source.rstrip(" .") + (". " if source else "") + clause


def _compact_text(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def _lyrics_are_authored(requirement: str, content: object) -> bool:
    """Accept only lyric words that are actually present in the user requirement.

    Models sometimes mark invented lines as explicit_user_requested.  Presence in the
    authored requirement is the stable source-of-truth and prevents an instrumental or
    already-vocal A1 from receiving a second fabricated singer.
    """

    words = _compact_text(content)
    source = _compact_text(requirement)
    return bool(words and len(words) >= 2 and words in source)


def _upsert_use(
    uses: list[dict],
    inventory: dict[str, object],
    *,
    media_id: str,
    media_type: str,
    duration: float,
    track: str,
    requirement_id: str,
    instruction: str,
    identity_anchor: bool = False,
) -> None:
    if not _loaded(inventory.get(media_id)):
        return
    retained = [
        row for row in uses
        if _media_id(row.get("media_id")) != media_id
        and str(row.get("requirement_id", "")) != requirement_id
    ]
    retained.append({
        "requirement_id": requirement_id,
        "media_id": media_id,
        "media_type": media_type,
        "usage": "h3_reference",
        "reuse_policy": "whole_design",
        "start_seconds": 0.0,
        "end_seconds": duration,
        "track": track,
        "subject_keywords": [],
        "instruction": instruction,
        **({"identity_anchor": True} if identity_anchor else {}),
    })
    uses[:] = retained


def enforce_mtv_singing_plan(
    plan: dict,
    existing_media: list[dict] | None,
    *,
    special_skill_key: str,
    authored_requirement: str,
) -> dict:
    """Lock P1-P4/A1 roles and reject model-invented singing text."""

    if not is_mtv_singing_skill(special_skill_key):
        return plan
    duration = max(0.5, float(plan.get("duration_seconds", 12.0) or 12.0))
    inventory = _inventory(existing_media)
    uses = [deepcopy(row) for row in plan.get("existing_media_uses") or [] if isinstance(row, dict)]

    _upsert_use(
        uses, inventory, media_id="P1", media_type="image", duration=duration,
        track="V1", requirement_id="mtv_p1_lead_singer",
        instruction=(
            "Use @P1 as S1, the sole authoritative lead-singer identity for the complete MV. "
            "Preserve the exact face, hair, body, clothing and accessories. P1 performs directly "
            "to A1 with readable mouth, jaw, breath, facial and gesture timing."
        ), identity_anchor=True,
    )
    for media_id, track in (("P2", "V2"), ("P3", "V3")):
        _upsert_use(
            uses, inventory, media_id=media_id, media_type="image", duration=duration,
            track=track, requirement_id=f"mtv_{media_id.lower()}_support_person",
            instruction=(
                f"Use @{media_id} only as a distinct supporting person. Preserve that person's "
                "own face, body, wardrobe and accessories. The supporting person reacts, dances "
                "or occupies the scene but does not sing, replace P1 or copy P1's mouth motion."
            ), identity_anchor=True,
        )
    _upsert_use(
        uses, inventory, media_id="P4", media_type="image", duration=duration,
        track="V4", requirement_id="mtv_p4_scene_master",
        instruction=(
            "Use @P4 as the authoritative scene master for location geometry, camera axis, palette, "
            "colour temperature, weather, practical light direction, surfaces and atmosphere. It "
            "does not own or redesign P1-P3 identities."
        ),
    )
    _upsert_use(
        uses, inventory, media_id="A1", media_type="audio", duration=duration,
        track="A1", requirement_id="mtv_a1_exact_master_audio",
        instruction=MTV_MASTER_AUDIO_CONTRACT,
    )
    plan["existing_media_uses"] = uses

    retained_text: list[dict] = []
    removed_speech = 0
    for raw in plan.get("text_layers") or []:
        if not isinstance(raw, dict):
            continue
        role = str(raw.get("role", "")).strip().lower()
        if role in {"lyrics", "dialogue", "voice_over"}:
            if role != "lyrics" or not _lyrics_are_authored(
                authored_requirement, raw.get("content", "")
            ):
                removed_speech += 1
                continue
            row = deepcopy(raw)
            row.update({
                "role": "lyrics",
                "speaker": "S1",
                "track": "A6",
                "lip_sync": True,
                "explicit_user_requested": True,
            })
            retained_text.append(row)
        else:
            retained_text.append(deepcopy(raw))
    plan["text_layers"] = retained_text

    plan["creative_brief"] = _append_once(
        plan.get("creative_brief"), MTV_CAST_SCENE_CONTRACT
    )
    plan["overall_soundscape"] = MTV_MASTER_AUDIO_CONTRACT
    plan["non_diegetic_music"] = (
        "@A1 exact Timeline Master Audio only. Preserve the original recording at 1x and use no "
        "generated replacement song, added singer, TTS vocal, pitch correction or alternate score."
    )
    plan["constraints"] = _append_once(
        plan.get("constraints"),
        MTV_MASTER_AUDIO_CONTRACT + " " + MTV_CAST_SCENE_CONTRACT,
    )
    for shot in plan.get("shots") or []:
        if not isinstance(shot, dict):
            continue
        shot["subject_action"] = _append_once(
            shot.get("subject_action"),
            "S1 is P1, the sole lead singer, and performs the current A1 source window with clearly visible, frame-matched "
            "mouth shapes, jaw motion, breaths, eye expression and musical gestures. P2 and P3 remain "
            "non-singing support performers when visible.",
        )
        shot["additional_direction"] = _append_once(
            shot.get("additional_direction"),
            "Synchronize all visible performance accents and editorial beats to the matching A1 "
            "Timeline window. P4 owns the scene; never replace the singer, scene or soundtrack.",
        )
        shot["native_audio_direction"] = MTV_MASTER_AUDIO_CONTRACT
        shot["environment_continuity"] = (
            "Continue P4's visible acoustic space and advance A1 source time continuously across "
            "the cut; never restart A1 at a Segment boundary."
        )
        shot["audio_reference_intent"] = (
            "@A1 is performance timing and the exact final Master Audio, not a timbre suggestion. "
            "Do not copy it into a newly synthesized voice; use it unchanged in final assembly."
        )
    if removed_speech:
        warnings = [str(value) for value in plan.get("design_warnings") or []]
        warnings.append(
            f"Removed {removed_speech} model-invented speech/lyric layer(s); A1 remains the sole "
            "vocal and music source. Add exact lyrics to the Design Requirement only when editable "
            "lyric timing is required."
        )
        plan["design_warnings"] = list(dict.fromkeys(warnings))
    plan["mtv_audio_policy"] = {
        "schema_version": 1,
        "master_audio_id": "A1",
        "final_audio_mode": "replace_h3_with_exact_timeline_master",
        "lead_singer_id": "P1",
        "support_ids": ["P2", "P3"],
        "scene_master_id": "P4",
    }
    return plan


def enforce_mtv_scene_keyframes(
    plan: dict,
    existing_media: list[dict] | None,
    *,
    special_skill_key: str,
) -> dict:
    """Reserve P5-P9 as five P4-derived, character-free scene-state plates."""

    if not is_mtv_singing_skill(special_skill_key):
        return plan
    duration = max(0.5, float(plan.get("duration_seconds", 12.0) or 12.0))
    inventory = _inventory(existing_media)
    uses = [deepcopy(row) for row in plan.get("existing_media_uses") or [] if isinstance(row, dict)]
    requests: list[dict] = []
    states = (
        ("opening", "establishing performance light with clear foreground space for the singer"),
        ("verse", "a restrained first musical change in practical light and atmospheric depth"),
        ("lift", "a stronger rhythmic light state with motivated reflections and layered depth"),
        ("climax", "the peak lighting and environmental energy of the selected location"),
        ("final", "a resolved final performance light state with a stable hero-frame composition"),
    )
    source_loaded = _loaded(inventory.get("P4"))
    step = duration / len(states)
    for index, (label, direction) in enumerate(states, 5):
        media_id = f"P{index}"
        start = (index - 5) * step
        end = duration if index == 9 else (index - 4) * step
        if _loaded(inventory.get(media_id)):
            uses = [row for row in uses if _media_id(row.get("media_id")) != media_id]
            uses.append({
                "requirement_id": f"mtv_{media_id.lower()}_{label}_scene_state",
                "media_id": media_id,
                "media_type": "image",
                "usage": "h3_reference",
                "reuse_policy": "time_scoped",
                "start_seconds": start,
                "end_seconds": end,
                "track": f"V{index}",
                "subject_keywords": ["MTV scene state", label],
                "instruction": (
                    f"Use @{media_id} only as the {label} P4-derived environment and lighting state. "
                    "It owns no principal character identity and cannot replace P1, P2 or P3."
                ),
            })
            continue
        request = {
            "requirement_id": f"mtv_{media_id.lower()}_{label}_scene_state",
            "media_type": "image",
            "usage": "h3_reference",
            "reuse_policy": "time_scoped",
            "start_seconds": start,
            "end_seconds": end,
            "track": f"V{index}",
            "preferred_media_id": media_id,
            "subject_keywords": ["MTV scene state", label, "character-free environment"],
            "prompt": (
                "Photoreal cinematic music-video environment plate derived from the supplied source "
                "scene. Preserve the source location's architecture, spatial layout, camera axis, lens "
                "perspective, palette, colour temperature, weather, surface materials and practical-light "
                f"logic. Create only this timed visual state: {direction}. Keep generous, correctly lit "
                "foreground and middle-ground space for later P1-P3 compositing. No principal singer, no "
                "featured person, no duplicate body, no text, lyrics, logo, watermark, UI, montage or split screen."
            ),
            "negative_prompt": (
                "principal singer, featured person, duplicate people, cloned face, changed architecture, "
                "changed location, wrong colour temperature, unrelated landmark, text, lyrics, logo, "
                "watermark, UI, montage, split screen"
            ),
        }
        if source_loaded:
            request.update({
                "source_plate_media_id": "P4",
                "source_plate_mode": "source_img2img",
                "derived_from_media_id": "P4",
                "source_image_denoise": 0.38,
            })
        requests.append(request)
    plan["existing_media_uses"] = uses
    # This Skill owns a fixed P5-P9 scene-state budget.  Discard model-created
    # replacement faces and one-image-per-Shot requests that would inflate P-count.
    plan["media_requests"] = requests
    return plan


def exact_master_audio_asset(
    assets: list[object],
    *,
    special_skill_key: str,
    timeline_start: float,
    duration: float,
) -> dict | None:
    """Return the physical A1 slice that must replace generated H3 audio."""

    if not is_mtv_singing_skill(special_skill_key):
        return None
    for asset in assets or []:
        media_id = _media_id(
            _row_value(asset, "reference_id", "") or _row_value(asset, "media_id", "")
        )
        if media_id != "A1" or str(_row_value(asset, "media_type", "")).lower() != "audio":
            continue
        path = Path(str(_row_value(asset, "local_path", "") or ""))
        if not path.is_file():
            continue
        asset_start = float(_row_value(asset, "start_seconds", 0.0) or 0.0)
        asset_end = float(_row_value(asset, "end_seconds", 0.0) or 0.0)
        if asset_end <= timeline_start or asset_start >= timeline_start + duration:
            continue
        source_in = float(_row_value(asset, "source_in_seconds", 0.0) or 0.0)
        source_offset = max(0.0, source_in + timeline_start - asset_start)
        source_out = float(_row_value(asset, "source_out_seconds", 0.0) or 0.0)
        source_duration = float(_row_value(asset, "source_duration_seconds", 0.0) or 0.0)
        available_end = source_out if source_out > source_in else source_duration
        if available_end > 0.0 and source_offset + duration > available_end + 0.05:
            continue
        return {
            "path": str(path.resolve()),
            "source_offset_seconds": source_offset,
            "duration_seconds": max(0.01, float(duration)),
        }
    return None


def build_exact_master_audio_command(
    ffmpeg: str | Path,
    source_video: str | Path,
    master_audio: str | Path,
    destination: str | Path,
    *,
    source_offset_seconds: float,
    duration_seconds: float,
) -> list[str]:
    """Build a no-loop, no-time-stretch A1 replacement command."""

    duration = max(0.01, float(duration_seconds))
    offset = max(0.0, float(source_offset_seconds))
    audio_filter = (
        f"[1:a:0]atrim=start={offset:.6f}:duration={duration:.6f},"
        f"asetpts=PTS-STARTPTS,apad=whole_dur={duration:.6f},"
        f"atrim=duration={duration:.6f}[master]"
    )
    return [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source_video), "-i", str(master_audio),
        "-filter_complex", audio_filter,
        "-map", "0:v:0", "-map", "[master]", "-t", f"{duration:.6f}",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
        "-movflags", "+faststart", str(destination),
    ]


def replace_video_audio_with_exact_master(
    ffmpeg: str | Path,
    source_video: str | Path,
    master_spec: dict,
    destination: str | Path,
) -> Path:
    """Publish video with A1 as its sole audio stream, preserving video bytes."""

    source = Path(source_video)
    target = Path(destination)
    if not source.is_file():
        raise FileNotFoundError(source)
    master = Path(str(master_spec.get("path", "")))
    if not master.is_file():
        raise FileNotFoundError(master)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.stem + ".mtv-master.tmp" + target.suffix)
    command = build_exact_master_audio_command(
        ffmpeg, source, master, temporary,
        source_offset_seconds=float(master_spec.get("source_offset_seconds", 0.0)),
        duration_seconds=float(master_spec.get("duration_seconds", 0.0)),
    )
    completed = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if completed.returncode or not temporary.is_file():
        temporary.unlink(missing_ok=True)
        raise RuntimeError("Could not preserve exact MTV Master Audio: " + completed.stderr[-1000:])
    temporary.replace(target)
    return target.resolve()

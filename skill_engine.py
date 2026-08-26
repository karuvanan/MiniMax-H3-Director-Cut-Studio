"""Load local H3 prompt profiles and compile skill-aware Ref2VA prompts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

from media_semantic_enrichment import enrichment_fingerprint
from prompt_engine import PromptSpec
from workflow_engine import (
    MediaAsset,
    paired_audio_reference_tags,
    remap_reference_tokens,
    remap_reference_value,
    stable_reference_id,
)


DEFAULT_SKILL = "h3-prompt-writing"
SPECIAL_SKILL = "minimalist-product-ad-generator"
NONE_SPECIAL = "__none__"


@dataclass(slots=True)
class SkillProfile:
    key: str
    display_name: str
    path: Path
    instruction: str
    h3_reference_guide: str
    special: bool = False
    description: str = ""
    standalone: bool = False

    @property
    def summary(self) -> str:
        prefix = "Special" if self.special else "Default"
        detail = self.description.strip() or self.display_name
        detail = " ".join(detail.split())
        if len(detail) > 118:
            detail = detail[:115].rstrip() + "..."
        return f"{prefix} · {self.display_name} · {detail}"


def load_skill_profiles(workspace: str | Path) -> dict[str, SkillProfile]:
    workspace_path = Path(workspace)
    default_folder_candidates = (
        workspace_path / "skill default" / DEFAULT_SKILL,
        workspace_path / "skill minimax h3" / DEFAULT_SKILL,
    )
    default_folder = next((path for path in default_folder_candidates if path.is_dir()), None)
    if default_folder is None:
        raise FileNotFoundError(
            "找不到 Default Skill。预期位置：skill default/h3-prompt-writing/SKILL.md"
        )
    default_path = default_folder / "SKILL.md"
    ref_path = default_folder / "references" / "ref-en.txt"
    missing = [path for path in (default_path, ref_path) if not path.exists()]
    if missing:
        raise FileNotFoundError("缺少 Skill 文件：" + ", ".join(str(path) for path in missing))

    default_instruction = default_path.read_text(encoding="utf-8-sig")
    reference_guide = ref_path.read_text(encoding="utf-8-sig")
    default_name, default_description = _frontmatter(default_instruction, DEFAULT_SKILL)
    profiles = {
        DEFAULT_SKILL: SkillProfile(
            DEFAULT_SKILL,
            _display_name(default_name),
            default_path.resolve(),
            default_instruction,
            reference_guide,
            description=default_description,
        ),
    }

    special_root_candidates = (
        workspace_path / "skill special",
        workspace_path / "skill minimax h3",
    )
    special_root = next((path for path in special_root_candidates if path.is_dir()), None)
    if special_root:
        for folder in sorted(special_root.iterdir(), key=lambda path: path.name.casefold()):
            if not folder.is_dir() or folder.name == DEFAULT_SKILL:
                continue
            skill_path = folder / "SKILL.md"
            if not skill_path.is_file():
                continue
            instruction = skill_path.read_text(encoding="utf-8-sig")
            name, description = _frontmatter(instruction, folder.name)
            key = folder.name
            profiles[key] = SkillProfile(
                key=key,
                display_name=_display_name(name),
                path=skill_path.resolve(),
                instruction=instruction,
                h3_reference_guide=reference_guide,
                special=True,
                description=description,
                standalone=bool(
                    re.search(
                        r"<!--\s*h3-studio-binding:\s*standalone\s*-->",
                        instruction,
                        flags=re.I,
                    )
                ),
            )
    return profiles


def _display_name(value: str) -> str:
    return " ".join(part.capitalize() for part in value.replace("_", "-").split("-"))


def _frontmatter(text: str, fallback_name: str) -> tuple[str, str]:
    """Extract name and description without requiring a YAML dependency."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, flags=re.S)
    if not match:
        return fallback_name, ""
    lines = match.group(1).splitlines()
    name = fallback_name
    description = ""
    index = 0
    while index < len(lines):
        line = lines[index]
        name_match = re.match(r"^name:\s*(.+?)\s*$", line)
        if name_match:
            name = name_match.group(1).strip().strip('"\'')
        desc_match = re.match(r"^description:\s*(.*?)\s*$", line)
        if desc_match:
            value = desc_match.group(1)
            if value in ("|", ">", ""):
                collected: list[str] = []
                index += 1
                while index < len(lines) and (lines[index].startswith(" ") or not lines[index].strip()):
                    collected.append(lines[index].strip())
                    index += 1
                description = " ".join(part for part in collected if part)
                continue
            description = value.strip().strip('"\'')
        index += 1
    return name, description


def profile_system_prompt(
    default_profile: SkillProfile,
    special_profile: SkillProfile | None = None,
) -> str:
    """Bind the official H3 writing skill with an optional scene-specific skill."""
    if special_profile is not None and special_profile.standalone:
        return "\n\n".join(
            (
                "Follow the selected standalone Special Skill exactly.",
                f"STANDALONE SPECIAL SKILL ({special_profile.key}):\n"
                + special_profile.instruction,
                "Do not merge, inject, quote or infer rules from the Default H3 skill. "
                "The production brief in the app counts as the completed start gate. "
                "Do not ask follow-up questions. Return only the output required by the "
                "selected standalone skill and the current task.",
            )
        )
    parts = [
        "Follow the official MiniMax H3 prompt-writing skill exactly.",
        "DEFAULT H3 SKILL:\n" + default_profile.instruction,
        "H3 REF2VA FORMAT GUIDE:\n" + default_profile.h3_reference_guide,
    ]
    if special_profile is not None:
        parts.append(
            f"SPECIAL SCENE SKILL ({special_profile.key}):\n" + special_profile.instruction
        )
        parts.append(
            "The production brief in the app counts as the completed start gate. "
            "Do not ask follow-up questions. Apply the special scene workflow and constraints, "
            "then translate the approved plan into the official H3 full-reference six-section output. "
            "The special skill may shape content, style, planning, shots, transitions, typography, "
            "and audio, but it must not replace or reorder the Default H3 output format."
        )
    else:
        parts.append(
            "SPECIAL SCENE SKILL: None. Do not inject any style-specific or scenario-specific workflow."
        )
    parts.append("Return only the final six-section Ref2VA prompt in English.")
    return "\n\n".join(parts)


def _timecode(seconds: float) -> str:
    millis = round(seconds * 1000)
    minutes, remainder = divmod(millis, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{minutes:02d}:{secs:02d}.{ms:03d}"


def _dialogue_by_cut(text: str) -> dict[int, list[str]]:
    result: dict[int, list[str]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = re.match(r"^(\d+)\s*[|｜:]\s*(.+)$", line)
        cut, words = (int(match.group(1)), match.group(2)) if match else (1, line)
        result.setdefault(cut, []).append(words.strip())
    return result


def _positive_shot_index(value: object) -> int | None:
    """Return a one-based shot index, or None for missing/invalid values."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _transition_direction(row: dict) -> str:
    """Compile one structured transition row into a ready-to-emit direction."""
    for key in ("description", "direction", "text"):
        value = str(row.get(key, "")).strip()
        if value:
            return value
    preset = str(row.get("preset", "")).strip()
    detail = str(row.get("detail", "")).strip()
    if preset and detail:
        return f"{preset}: {detail}"
    return preset or detail


def _transition_rows_by_boundary(
    rows: list[dict],
    timed_shots: list[dict],
    shot_count: int,
) -> dict[int, list[str]]:
    """Map transition rows to the outgoing shot at each internal boundary.

    Explicit shot IDs are preferred, followed by one-based shot indexes. A
    timestamp-only row is matched to the nearest adjacent shot edge. Ordered
    rows without any routing metadata fall back to boundary order.
    """
    if shot_count < 2:
        return {}

    shot_ids = {
        str(row.get("cue_id", "")).strip(): index
        for index, row in enumerate(timed_shots, 1)
        if str(row.get("cue_id", "")).strip()
    }
    boundary_edges: dict[int, tuple[float, float]] = {}
    if len(timed_shots) == shot_count:
        for index in range(1, shot_count):
            left = timed_shots[index - 1]
            right = timed_shots[index]
            try:
                left_end = float(left.get("end_seconds", 0.0))
                right_start = float(right.get("start_seconds", left_end))
            except (TypeError, ValueError):
                continue
            boundary_edges[index] = (left_end, right_start)

    mapped: dict[int, list[str]] = {}
    sequential_boundary = 1
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        direction = _transition_direction(raw)
        if not direction:
            continue

        after_index: int | None = None
        from_id = str(raw.get("from_shot_id", "")).strip()
        to_id = str(raw.get("to_shot_id", "")).strip()
        if from_id in shot_ids:
            after_index = shot_ids[from_id]
        elif to_id in shot_ids:
            after_index = shot_ids[to_id] - 1

        if after_index is None:
            for key in ("after_shot_index", "from_shot_index", "boundary_after_shot"):
                after_index = _positive_shot_index(raw.get(key))
                if after_index is not None:
                    break
        if after_index is None:
            to_index = _positive_shot_index(raw.get("to_shot_index"))
            if to_index is not None:
                after_index = to_index - 1

        timing_keys = ("boundary_seconds", "start_seconds", "end_seconds")
        has_timing = any(raw.get(key) not in (None, "") for key in timing_keys)
        if after_index is None and has_timing and boundary_edges:
            try:
                start = float(
                    raw.get(
                        "boundary_seconds",
                        raw.get("start_seconds", raw.get("end_seconds")),
                    )
                )
                end = float(raw.get("end_seconds", start))
            except (TypeError, ValueError):
                start = end = float("nan")
            if start == start and end == end:  # NaN-safe without another dependency.
                low, high = sorted((start, end))

                def edge_distance(edges: tuple[float, float]) -> float:
                    distances = []
                    for edge in edges:
                        if low <= edge <= high:
                            distances.append(0.0)
                        else:
                            distances.append(min(abs(edge - low), abs(edge - high)))
                    return min(distances)

                candidate, distance = min(
                    ((index, edge_distance(edges)) for index, edges in boundary_edges.items()),
                    key=lambda item: item[1],
                )
                # Do not attach a transition at a segment entrance to an
                # unrelated later boundary merely because it is nearest.
                if distance <= 0.5:
                    after_index = candidate

        if after_index is None and not has_timing:
            after_index = sequential_boundary
            sequential_boundary += 1

        if after_index is None or not 1 <= after_index < shot_count:
            continue
        mapped.setdefault(after_index, []).append(direction)
    return mapped


def _asset_definition(
    asset: MediaAsset,
    source_assets: list[MediaAsset] | None = None,
    effective_assets: list[MediaAsset] | None = None,
    paired_audio_tag: str = "",
) -> str:
    def display(value: str) -> str:
        if source_assets is None or effective_assets is None:
            return value
        return remap_reference_tokens(value, source_assets, effective_assets)

    source_asset = asset
    if source_assets is not None:
        source_node_id = asset.source_node_id or asset.node_id
        source_asset = next(
            (
                item for item in source_assets
                if item.media_type == asset.media_type
                and (item.source_node_id or item.node_id) == source_node_id
                and item.binding == asset.binding
            ),
            asset,
        )
    source = f' loaded from "{asset.filename}"' if asset.filename else ""
    analyzed_rows = []
    include_transcript = False
    for raw in asset.recognition.splitlines():
        line = raw.strip()
        if line.startswith("WHISPER TRANSCRIPT"):
            include_transcript = True
            continue
        if line.startswith("[") and include_transcript:
            analyzed_rows.append("machine transcript: " + display(line))
            continue
        include_transcript = False
        if line.startswith(("BLIP visual caption", "BLIP video frame", "Beat estimate", "VAD voice ratio")):
            analyzed_rows.append(display(line))
    analysis = ""
    if analyzed_rows:
        guidance = " | ".join(analyzed_rows)
        analysis = f" Analyzed planning guidance: {guidance[:1200]}."
    # Semantic enrichment belongs to the permanent Media Pool source.  Its
    # fingerprint must not change when P4 is request-locally numbered as
    # <Picture 1> in a later segment.
    current_semantic_hash = enrichment_fingerprint(
        media_id=stable_reference_id(source_asset),
        media_type=source_asset.media_type,
        filename=source_asset.filename,
        recognition=source_asset.recognition,
        clip_prompt=source_asset.clip_prompt,
        duration_seconds=source_asset.source_duration_seconds,
        timeline_start_seconds=(
            source_asset.start_seconds if source_asset.timeline_placed else 0.0
        ),
        timeline_end_seconds=(
            source_asset.end_seconds if source_asset.timeline_placed else 0.0
        ),
    )
    if (
        source_asset.semantic_enrichment.strip()
        and source_asset.semantic_enrichment_source_hash == current_semantic_hash
    ):
        semantic_lines = [
            line.strip()
            for line in source_asset.semantic_enrichment.splitlines()
            if line.strip()
            and not line.startswith(("AI PROVIDER:", "AI MODEL:", "EVIDENCE FINGERPRINT"))
        ]
        semantic = display(" | ".join(semantic_lines))
        if len(semantic) > 2200:
            semantic = semantic[:1450].rstrip() + " … " + semantic[-700:].lstrip()
        analysis += (
            " AI semantic enrichment (derived guidance; preserve its uncertainty labels): "
            + semantic
            + "."
        )
    director_prompt = display(asset.clip_prompt.strip())
    if director_prompt:
        analysis += f" Director clip instruction: {director_prompt[:1200]}."
    if asset.media_type == "image":
        return f"{asset.tag} is a reference image{source} used as a concrete visual and shot-planning anchor.{analysis}"
    if asset.media_type == "video":
        audio_note = (
            f" Its synchronized soundtrack is enabled as {paired_audio_tag}."
            if paired_audio_tag
            else ""
        )
        return f"{asset.tag} is a reference video{source} providing motion, camera, and temporal guidance.{audio_note}{analysis}"
    return f"{asset.tag} is a standalone reference audio asset{source} reused according to the target timeline.{analysis}"


def build_ref2va_prompt(
    spec: PromptSpec,
    assets: list[MediaAsset],
    duration: float,
    default_profile: SkillProfile,
    special_profile: SkillProfile | None = None,
    source_assets: list[MediaAsset] | None = None,
) -> str:
    """Deterministically build the six sections required by h3-prompt-writing."""
    if source_assets is not None:
        spec = PromptSpec(
            **remap_reference_value(asdict(spec), source_assets, assets)
        )

    def source_key(asset: MediaAsset) -> tuple[str, str, str]:
        return (asset.media_type, asset.source_node_id or asset.node_id, asset.binding)

    grouped: dict[tuple[str, str, str], list[MediaAsset]] = {}
    for asset in assets:
        grouped.setdefault(source_key(asset), []).append(asset)
    unique_assets = [instances[0] for instances in grouped.values()]
    paired_audio_tags = paired_audio_reference_tags(unique_assets)
    visual_assets = [asset for asset in unique_assets if asset.media_type in ("image", "video")]
    audio_assets = [asset for asset in unique_assets if asset.media_type == "audio"]
    has_reused_audio = bool(audio_assets or any(a.paired_audio_binding for a in assets))
    task_types = "reference generation + audio reuse" if has_reused_audio else "reference generation"

    definition_rows: list[str] = []
    for representative in unique_assets:
        instances = grouped[source_key(representative)]
        paired_audio_tag = paired_audio_tags.get(source_key(representative), "")
        row = _asset_definition(
            representative,
            source_assets,
            assets,
            paired_audio_tag,
        )
        if len(instances) > 1:
            uses = "; ".join(
                f"{asset.start_seconds:.2f}s-{asset.end_seconds:.2f}s"
                + (
                    f" ({remap_reference_tokens(asset.clip_prompt.strip(), source_assets, assets)[:300]})"
                    if asset.clip_prompt.strip() and source_assets is not None
                    else f" ({asset.clip_prompt.strip()[:300]})" if asset.clip_prompt.strip()
                    else ""
                )
                for asset in instances
            )
            row += f" Reused Timeline instances: {uses}."
        definition_rows.append(row)
        if paired_audio_tag:
            definition_rows.append(
                f"{paired_audio_tag} is the enabled synchronized soundtrack from "
                f"{representative.tag}; it follows the same active Timeline ranges."
            )
    definitions = "\n".join(definition_rows)
    if not definitions:
        definitions = "No active reference asset is assigned to this time window."

    profile_phrase = (
        f"{special_profile.display_name} full-reference video"
        if special_profile is not None
        else "full-reference video"
    )
    summary = (
        f"[{task_types}] The target is a {duration:.2f}-second {profile_phrase}. "
        f"{spec.brief.strip()}"
    )

    retention_rows: list[str] = []
    for asset in visual_assets:
        instances = grouped[source_key(asset)]
        ranges = ", ".join(
            f"{item.start_seconds:.2f}s to {item.end_seconds:.2f}s" for item in instances
        )
        role = "visual identity, composition, and referenced attributes are retained"
        if asset.media_type == "video":
            role = "motion, camera, and temporal characteristics guide the target sequence"
        retention_rows.append(
            f"{asset.tag} (active from {ranges}): "
            f"fully_preserved - {role}."
        )
    for asset in audio_assets:
        instances = grouped[source_key(asset)]
        ranges = ", ".join(
            f"{item.start_seconds:.2f}s to {item.end_seconds:.2f}s" for item in instances
        )
        retention_rows.append(
            f"{asset.tag}: fully_copy - the assigned signal is reused during its "
            f"{ranges} timeline range."
        )
    for asset in visual_assets:
        paired_audio_tag = paired_audio_tags.get(source_key(asset), "")
        if not paired_audio_tag:
            continue
        instances = grouped[source_key(asset)]
        ranges = ", ".join(
            f"{item.start_seconds:.2f}s to {item.end_seconds:.2f}s"
            for item in instances
        )
        retention_rows.append(
            f"{paired_audio_tag}: fully_copy - the synchronized soundtrack from "
            f"{asset.tag} is reused during its {ranges} timeline range."
        )
    if not retention_rows:
        retention_rows.append("No active reference relationship is retained in this time window.")

    timed_shots = spec.shot_ranges or []
    shots = (
        [str(row.get("description", "")).strip() for row in timed_shots]
        if timed_shots
        else spec.shots or [spec.brief.strip()]
    )
    dialogue = _dialogue_by_cut(spec.dialogue)
    shot_duration = duration / max(1, len(shots))
    detailed_rows: list[str] = []
    style = spec.style.strip() or "The target uses a coherent, concrete visual style."
    detailed_rows.append(style.rstrip(".。") + ".")
    if special_profile is not None:
        detailed_rows.append(
            "Apply the bound special-scene direction consistently: "
            f"{special_profile.description or special_profile.display_name}."
        )
    if special_profile is not None and special_profile.key == SPECIAL_SKILL:
        detailed_rows.append(
            "The product body color, material, silhouette, functional details, negative space, "
            "and premium restrained motion remain consistent; every visible copy line stays on one line."
        )
    active_labels = ", ".join(
        [asset.tag for asset in unique_assets]
        + list(paired_audio_tags.values())
    )
    structured_transitions = _transition_rows_by_boundary(
        spec.transition_ranges,
        timed_shots,
        len(shots),
    )
    for index, shot in enumerate(shots, 1):
        if timed_shots:
            timed = timed_shots[index - 1]
            start = float(timed.get("start_seconds", 0.0))
            end = float(timed.get("end_seconds", start))
            prefix = f"[Shot {index} | {_timecode(start)}-{_timecode(end)}]"
        else:
            prefix = f"[Shot {index}]"
        if index > 1 and not timed_shots:
            prefix += f" At {_timecode((index - 1) * shot_duration)},"
        sentence = shot.strip().rstrip(".。") + "."
        if index == 1 and active_labels:
            sentence += f" The active references are {active_labels}."
        if index in dialogue:
            for words in dialogue[index]:
                sentence += f" The exact audible or visible wording is <d>[Original] {words}</d>."
        detailed_rows.append(f"{prefix} {sentence}")
        if index < len(shots):
            if spec.transition_ranges:
                transition_directions = structured_transitions.get(index, [])
            else:
                # Backward compatibility for callers that only provide the
                # original global transition string.
                transition_directions = [spec.transition.strip()] if spec.transition.strip() else []
            for direction in transition_directions:
                detailed_rows.append(
                    f"The transition into [Shot {index + 1}] is "
                    f"{direction.rstrip('.')} with continuous motion and sound."
                )
    if spec.ending.strip():
        detailed_rows.append(spec.ending.strip().rstrip(".。") + ".")
    if spec.must_keep.strip():
        detailed_rows.append("Hard constraints: " + spec.must_keep.strip().rstrip(".。") + ".")

    soundscape = spec.audio.strip() or "N/A"
    music = spec.music.strip() or (
        "Around 100 BPM with crisp pluck, restrained kick and sub-bass, airy noise, tactile wooden percussion, and no vocals."
        if special_profile is not None and special_profile.key == SPECIAL_SKILL
        else "N/A"
    )
    return "\n\n".join(
        (
            "subject_definitions:\n" + definitions,
            "summary:\n" + summary,
            "retention_analysis:\n" + "\n".join(retention_rows),
            "detailed_description:\n" + "\n".join(detailed_rows),
            "overall_soundscape:\n" + soundscape,
            "non_diegetic_music:\n" + music,
        )
    )

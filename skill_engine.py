"""Load local H3 prompt profiles and compile skill-aware Ref2VA prompts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from prompt_engine import PromptSpec
from workflow_engine import MediaAsset


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


def _asset_definition(asset: MediaAsset) -> str:
    source = f' loaded from "{asset.filename}"' if asset.filename else ""
    analyzed_rows = []
    include_transcript = False
    for raw in asset.recognition.splitlines():
        line = raw.strip()
        if line.startswith("WHISPER TRANSCRIPT"):
            include_transcript = True
            continue
        if line.startswith("[") and include_transcript:
            analyzed_rows.append("machine transcript: " + line)
            continue
        include_transcript = False
        if line.startswith(("BLIP visual caption", "BLIP video frame", "Beat estimate", "VAD voice ratio")):
            analyzed_rows.append(line)
    analysis = ""
    if analyzed_rows:
        guidance = " | ".join(analyzed_rows)
        analysis = f" Analyzed planning guidance: {guidance[:1200]}."
    director_prompt = asset.clip_prompt.strip()
    if director_prompt:
        analysis += f" Director clip instruction: {director_prompt[:1200]}."
    if asset.media_type == "image":
        return f"{asset.tag} is a reference image{source} used as a concrete visual and shot-planning anchor.{analysis}"
    if asset.media_type == "video":
        audio_note = " Its synchronized soundtrack is enabled." if asset.paired_audio_binding else ""
        return f"{asset.tag} is a reference video{source} providing motion, camera, and temporal guidance.{audio_note}{analysis}"
    return f"{asset.tag} is a standalone reference audio asset{source} reused according to the target timeline.{analysis}"


def build_ref2va_prompt(
    spec: PromptSpec,
    assets: list[MediaAsset],
    duration: float,
    default_profile: SkillProfile,
    special_profile: SkillProfile | None = None,
) -> str:
    """Deterministically build the six sections required by h3-prompt-writing."""
    visual_assets = [asset for asset in assets if asset.media_type in ("image", "video")]
    audio_assets = [asset for asset in assets if asset.media_type == "audio"]
    has_reused_audio = bool(audio_assets or any(a.paired_audio_binding for a in assets))
    task_types = "reference generation + audio reuse" if has_reused_audio else "reference generation"

    definitions = "\n".join(_asset_definition(asset) for asset in assets)
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
        role = "visual identity, composition, and referenced attributes are retained"
        if asset.media_type == "video":
            role = "motion, camera, and temporal characteristics guide the target sequence"
        retention_rows.append(
            f"{asset.tag} (active from {asset.start_seconds:.2f}s to {asset.end_seconds:.2f}s): "
            f"fully_preserved - {role}."
        )
    for asset in audio_assets:
        retention_rows.append(
            f"{asset.tag}: fully_copy - the assigned signal is reused during its "
            f"{asset.start_seconds:.2f}s to {asset.end_seconds:.2f}s timeline range."
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
    active_labels = ", ".join(asset.tag for asset in assets)
    for index, shot in enumerate(shots, 1):
        if timed_shots:
            timed = timed_shots[index - 1]
            start = float(timed.get("start_seconds", 0.0))
            end = float(timed.get("end_seconds", start))
            prefix = f"[Shot {index} · {_timecode(start)}–{_timecode(end)}]"
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
        if index < len(shots) and spec.transition.strip():
            detailed_rows.append(
                f"The transition into [Shot {index + 1}] is {spec.transition.strip().rstrip('.')} with continuous motion and sound."
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

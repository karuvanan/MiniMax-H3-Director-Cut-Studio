"""Schema, validation and placeholder materialization for AI Director Design."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import math
import json
from pathlib import Path
import re
import subprocess
import textwrap
import wave


MAX_DESIGN_DURATION_SECONDS = 600.0
ACTION_BUDGET_WINDOW_SECONDS = 5.0
MAX_CORE_ACTIONS_PER_WINDOW = 3
MAX_REQUIRED_RESPONSES_PER_WINDOW = 2
MAX_OPTIONAL_ACTIONS_PER_WINDOW = 2
DEFAULT_SPEECH_CHARACTERS_PER_SECOND = 3.6
DEFAULT_SPEECH_WORDS_PER_SECOND = 2.7
ANALYSIS_ONLY_MEDIA_USAGES = frozenset({
    "analysis_only",
    "route_control_analysis_only",
})

H3_STABLE_DIALOGUE_LANGUAGES = (
    "Arabic",
    "Chinese",
    "English",
    "French",
    "German",
    "Italian",
    "Japanese",
    "Korean",
    "Portuguese",
    "Russian",
    "Spanish",
)


class DesignDurationContractError(ValueError):
    """The model changed a duration that the user specified explicitly."""


class DesignDialogueLanguageContractError(ValueError):
    """The model ignored the dialogue language selected in Design."""


class DesignSpeechLayerContractError(ValueError):
    """The model described requested speech without creating editable Text Layers."""


class DesignJSONDecodeError(ValueError):
    """The model returned a malformed or completion-truncated Design JSON object."""

    def __init__(self, message: str, *, line: int, column: int, position: int) -> None:
        super().__init__(message)
        self.line = int(line)
        self.column = int(column)
        self.position = int(position)


def is_analysis_only_media_use(value: object) -> bool:
    """Return True when a Media Pool row is planning evidence, never H3 input."""

    row = value if isinstance(value, dict) else {}
    return str(row.get("usage", "")).strip().casefold() in ANALYSIS_ONLY_MEDIA_USAGES


def speech_timing_budget(
    content: object,
    language: object = "",
    delivery: object = "",
    allocated_seconds: float = 0.0,
) -> dict:
    """Estimate whether exact authored speech can fit its Timeline interval.

    This is deliberately deterministic and conservative.  It is not a TTS
    duration oracle; it protects H3 native dialogue from being asked to speak
    so quickly that words are advanced, reordered, omitted or paraphrased.
    """
    text = " ".join(str(content or "").split())
    allocated = max(0.0, float(allocated_seconds or 0.0))
    if not text:
        return {
            "required_seconds": 0.0,
            "allocated_seconds": allocated,
            "overflow_seconds": 0.0,
            "risk": False,
            "rate_label": "empty",
        }
    language_text = str(language or "").lower()
    delivery_text = str(delivery or "").lower()
    cjk_count = len(re.findall(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]", text))
    latin_words = len(re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?", text))
    is_cjk = bool(cjk_count) or any(
        token in language_text
        for token in ("chinese", "mandarin", "japanese", "korean", "中文", "普通话")
    )
    pace = 1.0
    if re.search(r"fast|rapid|urgent|agitated|angry|激动|急促|快速", delivery_text):
        pace = 1.16
    elif re.search(
        r"slow|tearful|hesitant|whisper|controlled|emotional|低声|哭|迟疑|缓慢",
        delivery_text,
    ):
        pace = 0.86
    if is_cjk:
        units = cjk_count + latin_words * 2.0
        base_seconds = units / max(0.1, DEFAULT_SPEECH_CHARACTERS_PER_SECOND * pace)
        rate_label = f"{DEFAULT_SPEECH_CHARACTERS_PER_SECOND * pace:.2f} chars/s"
    else:
        words = max(latin_words, len(text.split()))
        base_seconds = words / max(0.1, DEFAULT_SPEECH_WORDS_PER_SECOND * pace)
        rate_label = f"{DEFAULT_SPEECH_WORDS_PER_SECOND * pace:.2f} words/s"
    pause_seconds = (
        len(re.findall(r"[,，、;；:]", text)) * 0.10
        + len(re.findall(r"[.!?。！？]", text)) * 0.22
        + len(re.findall(r"…|\.\.\.", text)) * 0.32
    )
    required = max(0.5, math.ceil((base_seconds + pause_seconds) * 2.0) / 2.0)
    overflow = max(0.0, required - allocated)
    return {
        "required_seconds": round(required, 3),
        "allocated_seconds": round(allocated, 3),
        "overflow_seconds": round(overflow, 3),
        "risk": overflow > 0.01,
        "rate_label": rate_label,
    }


def _shift_interval_at_boundary(row: dict, boundary: float, delta: float) -> None:
    start = float(row.get("start_seconds", 0.0))
    end = float(row.get("end_seconds", start))
    if start >= boundary - 1e-9:
        row["start_seconds"] = round(start + delta, 6)
        row["end_seconds"] = round(end + delta, 6)
    elif end > boundary + 1e-9:
        row["end_seconds"] = round(end + delta, 6)


def _owning_shot_for_interval(shots: list[dict], start: float, end: float) -> dict | None:
    """Return the Shot that owns the largest part of a timed speech event.

    A line may end exactly on a Shot boundary.  The previous implementation
    shifted only rows *after* that boundary, so a final line could extend the
    project duration without extending its Shot.  Selecting the owner before
    ripple editing lets the Shot absorb the complete authored performance.
    """

    midpoint = (start + end) / 2.0
    candidates: list[tuple[float, int, dict]] = []
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            continue
        shot_start = float(shot.get("start_seconds", 0.0) or 0.0)
        shot_end = float(shot.get("end_seconds", shot_start) or shot_start)
        overlap = max(0.0, min(end, shot_end) - max(start, shot_start))
        contains_midpoint = shot_start - 1e-9 <= midpoint <= shot_end + 1e-9
        if overlap > 0.0 or contains_midpoint or (
            shot_start - 1e-9 <= start <= shot_end + 1e-9
        ):
            candidates.append((overlap, -index, shot))
    if candidates:
        return max(candidates, key=lambda row: (row[0], row[1]))[2]
    preceding = [
        shot for shot in shots
        if isinstance(shot, dict)
        and float(shot.get("end_seconds", 0.0) or 0.0) <= start + 1e-9
    ]
    return max(
        preceding,
        key=lambda shot: float(shot.get("end_seconds", 0.0) or 0.0),
        default=(shots[-1] if shots else None),
    )


def ensure_complete_shot_coverage(plan: dict) -> dict:
    """Guarantee exactly one chronological Shot lane across the full duration.

    Media and Text tracks may overlap.  Camera Shot blocks may not, and no
    renderable time is allowed to exist without a Shot.  Gaps are resolved at
    their nearest shared boundary; the first and last Shots absorb leading or
    trailing time.  Timed speech is then rebound deterministically by midpoint.
    """

    duration = max(0.5, float(plan.get("duration_seconds", 0.5) or 0.5))
    shots = sorted(
        [row for row in (plan.get("shots") or []) if isinstance(row, dict)],
        key=lambda row: (
            float(row.get("start_seconds", 0.0) or 0.0),
            float(row.get("end_seconds", 0.0) or 0.0),
        ),
    )
    if not shots:
        return plan
    warnings = [str(value) for value in plan.get("design_warnings") or []]
    first_start = float(shots[0].get("start_seconds", 0.0) or 0.0)
    if first_start > 1e-9:
        shots[0]["start_seconds"] = 0.0
        warnings.append(
            f"Extended the first Shot backward from {first_start:.2f}s to 0.00s so no render time is Shot-less."
        )
    previous = shots[0]
    for current in shots[1:]:
        previous_end = float(previous.get("end_seconds", 0.0) or 0.0)
        current_start = float(current.get("start_seconds", 0.0) or 0.0)
        if abs(current_start - previous_end) > 1e-9:
            boundary = round((previous_end + current_start) / 2.0 * 2.0) / 2.0
            minimum = float(previous.get("start_seconds", 0.0) or 0.0) + 0.5
            maximum = float(current.get("end_seconds", current_start) or current_start) - 0.5
            boundary = round(min(max(boundary, minimum), maximum), 6)
            previous["end_seconds"] = boundary
            current["start_seconds"] = boundary
            warnings.append(
                f"Closed a Shot-lane gap/overlap at {boundary:.2f}s; every renderable frame now belongs to one Shot."
            )
        previous = current
    last_end = float(shots[-1].get("end_seconds", 0.0) or 0.0)
    if last_end < duration - 1e-9:
        shots[-1]["end_seconds"] = duration
        warnings.append(
            f"Extended the final Shot from {last_end:.2f}s to {duration:.2f}s so dialogue expansion cannot create a Shot-less Segment."
        )
    elif last_end > duration + 1e-9:
        shots[-1]["end_seconds"] = duration
    for index, shot in enumerate(shots, 1):
        shot["id"] = f"S{index}"
    for layer in plan.get("text_layers") or []:
        if not isinstance(layer, dict):
            continue
        start = float(layer.get("start_seconds", 0.0) or 0.0)
        end = float(layer.get("end_seconds", start) or start)
        owner = _owning_shot_for_interval(shots, start, end)
        if owner is not None:
            layer["shot_id"] = str(owner.get("id", ""))
    plan["shots"] = shots
    plan["design_warnings"] = list(dict.fromkeys(warnings))
    return plan


def auto_adjust_speech_shot_timing(plan: dict) -> dict:
    """Extend overloaded speech, its owning Shot and every later cue coherently."""
    result = plan
    original_duration = float(result.get("duration_seconds", 0.0) or 0.0)
    result.setdefault("_speech_timing_base_duration", original_duration)
    speech_layers = [
        row for row in result.get("text_layers") or []
        if isinstance(row, dict)
        and str(row.get("role", "")).lower() in {"dialogue", "voice_over", "lyrics"}
        and str(row.get("content", "")).strip()
    ]
    warnings = [str(value) for value in result.get("design_warnings") or []]
    for layer in sorted(speech_layers, key=lambda row: (float(row["start_seconds"]), float(row["end_seconds"]))):
        start = float(layer["start_seconds"])
        end = float(layer["end_seconds"])
        budget = speech_timing_budget(
            layer.get("content", ""), layer.get("language", ""),
            layer.get("delivery", ""), end - start,
        )
        layer["speech_budget"] = dict(budget)
        if not budget["risk"]:
            continue
        if bool(layer.get("authored_timing_locked", False)):
            layer["speech_budget"]["authored_timing_locked"] = True
            warnings.append(
                f"Exact authored speech at {start:.2f}-{end:.2f}s needs about "
                f"{budget['required_seconds']:.2f}s. Its user timecode is locked, so the "
                "Timeline clip remains red until the Shot is lengthened or the words are shortened."
            )
            continue
        delta = math.ceil(float(budget["overflow_seconds"]) * 2.0) / 2.0
        if float(result.get("duration_seconds", 0.0)) + delta > MAX_DESIGN_DURATION_SECONDS:
            layer["speech_budget"]["blocked_by_max_duration"] = True
            warnings.append(
                f"Speech at {start:.2f}-{end:.2f}s needs about {budget['required_seconds']:.2f}s "
                "and remains over budget because the 600-second Design limit was reached."
            )
            continue
        boundary = end
        shots = [row for row in result.get("shots") or [] if isinstance(row, dict)]
        owning_shot = _owning_shot_for_interval(shots, start, end)
        layer.setdefault("authored_start_seconds", start)
        layer.setdefault("authored_end_seconds", end)
        layer["end_seconds"] = round(end + delta, 6)
        layer["speech_timing_auto_adjusted"] = True
        layer["speech_budget_was_overloaded"] = True
        for candidate in result.get("text_layers") or []:
            if candidate is not layer and isinstance(candidate, dict):
                _shift_interval_at_boundary(candidate, boundary, delta)
        for family in ("shots", "existing_media_uses", "media_requests"):
            for candidate in result.get(family) or []:
                if isinstance(candidate, dict):
                    if family == "shots" and candidate is owning_shot:
                        candidate["end_seconds"] = round(
                            max(float(candidate.get("end_seconds", end)), end) + delta,
                            6,
                        )
                    else:
                        _shift_interval_at_boundary(candidate, boundary, delta)
        for family in ("transitions", "markers"):
            for candidate in result.get(family) or []:
                if not isinstance(candidate, dict):
                    continue
                cue_time = float(candidate.get("time_seconds", 0.0))
                if cue_time >= boundary - 1e-9:
                    candidate["time_seconds"] = round(cue_time + delta, 6)
        result["duration_seconds"] = round(
            float(result.get("duration_seconds", 0.0)) + delta, 6
        )
        layer["speech_budget"] = speech_timing_budget(
            layer.get("content", ""), layer.get("language", ""),
            layer.get("delivery", ""), float(layer["end_seconds"]) - start,
        )
        warnings.append(
            f"Speech at {start:.2f}-{boundary:.2f}s exceeded its safe delivery budget; "
            f"extended the owning Shot and all later Timeline events by {delta:.2f}s."
        )
    result["design_warnings"] = warnings
    return ensure_complete_shot_coverage(result)


_VISIBLE_PERSON_RE = re.compile(
    r"\b(?:woman|man|girl|boy|female|male|person|protagonist|hero|heroine|actor|character)\b|"
    r"女人|女子|女性|男人|男子|男性|女孩|男孩|主角|人物|角色|刺客|将军|將軍",
    re.I,
)

_IDENTITY_REFERENCE_RE = re.compile(
    r"(?:strict|primary|authoritative).{0,40}(?:identity|face)|"
    r"(?:identity|face).{0,40}(?:anchor|match|consistent|preserv)|"
    r"(?:preserv|keep).{0,40}(?:facial|face|identity)|"
    r"人脸.{0,20}(?:保持|一致|相同)|"
    r"(?:脸|面孔|身份).{0,20}(?:锚点|錨點|保持|一致|匹配)",
    re.I | re.S,
)

_IDENTITY_WORD_RE = re.compile(
    r"\b(?:face|facial|identity|same\s+person|same\s+character|look\s+exactly|consistent|match(?:es|ing)?)\b|"
    r"人脸|面孔|长相|長相|样子|樣子|身份|"
    r"同一人|同一人物|全程保持|保持一致",
    re.I,
)

_GENERATED_IDENTITY_PREFIX = (
    "PRIMARY RECURRING CHARACTER IDENTITY ANCHOR. Show one clear, unobstructed, "
    "recognizable face with exact age range, facial structure, hair, skin tone, wardrobe "
    "and owned props suitable for reuse through the full story. "
)

_CHARACTER_CONTINUITY_CONTRACT = {
    "fixed": [
        "face and recognizable identity",
        "age",
        "skin tone",
        "hairstyle and hair color",
        "body proportions and stable anatomy",
        "top/outerwear style, material and color",
        "trousers, skirt or other lower-body garment style and color",
        "shoes style and color",
        "accessory ownership",
    ],
    "variable": [
        "facial expression",
        "pose",
        "arm angle",
        "leg angle",
        "walking and running phase",
        "physically plausible hair and clothing motion caused by movement or wind",
    ],
    "story_only": [
        "wardrobe change",
        "hairstyle change",
        "injury",
        "dirt or stains",
        "clothing or prop damage",
        "removing shoes",
        "losing or transferring an accessory",
    ],
}

_SUPPORT_CONTINUITY_DIRECTION = (
    " Preserve the anchor's current hairstyle, hair color, skin tone, body proportions, "
    "top/outerwear, lower-body garment, shoes and accessory ownership. Expression, pose, "
    "arm/leg angles, gait phase and physical cloth/hair motion may change. Never invent a "
    "wardrobe or hairstyle change, injury, dirt, damage, shoe removal or accessory loss."
)


def _character_continuity_contract_text(anchor_label: str) -> str:
    fixed = ", ".join(_CHARACTER_CONTINUITY_CONTRACT["fixed"])
    variable = ", ".join(_CHARACTER_CONTINUITY_CONTRACT["variable"])
    story_only = ", ".join(_CHARACTER_CONTINUITY_CONTRACT["story_only"])
    return (
        f"CHARACTER CONTINUITY CONTRACT for {anchor_label}. FIXED unless an explicitly authored "
        f"Shot changes state: {fixed}. FREE TO VARY with the physical action: {variable}. "
        f"STORY-ONLY CHANGES: {story_only}; never invent these changes. Every authored change must "
        "name its exact trigger Shot, enter that Shot's outgoing continuity state, and persist as "
        "the incoming state of every following Shot until another explicit change occurs."
    )


def _attach_character_continuity_contract(
    plan: dict,
    anchor: dict,
    *,
    anchor_label: str,
    prompt_field: str,
) -> None:
    contract = _character_continuity_contract_text(anchor_label)
    anchor["character_continuity_contract"] = deepcopy(
        _CHARACTER_CONTINUITY_CONTRACT
    )
    if "CHARACTER CONTINUITY CONTRACT" not in str(anchor.get(prompt_field, "")):
        anchor[prompt_field] = (
            str(anchor.get(prompt_field, "")).rstrip(" .")
            + (". " if str(anchor.get(prompt_field, "")).strip() else "")
            + contract
        )
    plan["character_continuity_contract"] = deepcopy(
        _CHARACTER_CONTINUITY_CONTRACT
    )
    if "CHARACTER CONTINUITY CONTRACT" not in str(plan.get("constraints", "")):
        plan["constraints"] = (
            str(plan.get("constraints", "")).rstrip(" .")
            + (". " if str(plan.get("constraints", "")).strip() else "")
            + contract
        )


def _existing_identity_anchor(plan: dict) -> dict | None:
    """Prefer a loaded user Picture whenever it is declared as the face source."""
    image_uses = [
        row for row in plan.get("existing_media_uses") or []
        if isinstance(row, dict)
        and row.get("media_type") == "image"
        and not is_analysis_only_media_use(row)
    ]
    return next(
        (row for row in image_uses if bool(row.get("identity_anchor", False))),
        None,
    ) or next(
        (
            row for row in image_uses
            if _IDENTITY_REFERENCE_RE.search(
                " ".join(
                    [str(row.get("instruction", ""))]
                    + [str(value) for value in row.get("subject_keywords") or []]
                )
            )
        ),
        None,
    )


def _authored_identity_picture_ids(requirement: str) -> list[str]:
    """Find @P references that the user explicitly binds to face identity."""
    text = str(requirement or "")
    found: list[str] = []
    for match in re.finditer(r"@P([1-9]\d*)\b", text, re.I):
        start = max(0, match.start() - 140)
        end = min(len(text), match.end() + 140)
        if _IDENTITY_WORD_RE.search(text[start:end]):
            media_id = f"P{int(match.group(1))}"
            if media_id not in found:
                found.append(media_id)
    return found


def _request_recreates_existing_anchor(request: dict, media_id: str) -> bool:
    """Return True for an independently generated pose of an existing identity.

    A T2I model cannot guarantee the exact face from a textual ``face matching
    @P1`` instruction.  Passing that independently synthesized face to H3 makes
    it compete with the real P1, so these redundant action-state Pictures are
    omitted and the Shot prose supplies the pose instead.
    """
    text = " ".join(
        [str(request.get("prompt", ""))]
        + [str(value) for value in request.get("subject_keywords") or []]
    )
    ordinal_match = re.search(r"(\d+)$", media_id)
    picture_tag = (
        rf"|<Picture\s+{ordinal_match.group(1)}>"
        if ordinal_match else ""
    )
    token = re.compile(
        rf"(?:@?{re.escape(media_id)}\b{picture_tag})",
        re.I,
    )
    for match in token.finditer(text):
        start = max(0, match.start() - 140)
        end = min(len(text), match.end() + 140)
        if _IDENTITY_WORD_RE.search(text[start:end]):
            return True
    return False


def _strip_generated_anchor_augmentation(prompt: str) -> str:
    """Remove identity/support text appended by an earlier normalization pass."""
    text = str(prompt or "")
    lower = text.casefold()
    markers = (
        "the authoritative recurring face identity is the user-supplied",
        "supporting environment or action-state reference only",
        "distinct secondary character reference only",
        "distinct secondary character identity",
    )
    positions = [lower.find(marker) for marker in markers if lower.find(marker) >= 0]
    if positions:
        text = text[:min(positions)]
    return text.rstrip(" .")


def _direct_request_text(request: dict) -> str:
    """Return only the requested still, excluding appended story-wide prose."""

    prompt = _strip_generated_anchor_augmentation(str(request.get("prompt", "")))
    prompt = re.split(r"\bStory identity ledger\s*:", prompt, maxsplit=1, flags=re.I)[0]
    return " ".join(
        [str(request.get("requirement_id", ""))]
        + [str(value) for value in request.get("subject_keywords") or []]
        + [prompt]
    )


def _request_visible_person_count(request: dict) -> int:
    text = _direct_request_text(request).lower()
    if re.search(
        r"\b(?:two|2)\s+(?:people|persons|figures|characters|actors|fighters|warriors)\b",
        text,
    ):
        return 2
    if re.search(
        r"\b(?:one|single|1|exactly\s+one)\s+"
        r"(?:woman|man|girl|boy|person|figure|character|actor|general|assassin|fighter|warrior)\b",
        text,
    ):
        return 1
    named_roles = set()
    if re.search(r"\b(?:woman|female|girl|heroine)\b|女人|女性|女孩", text, re.I):
        named_roles.add("female")
    if re.search(r"\b(?:man|male|boy|hero)\b|男人|男性|男孩", text, re.I):
        named_roles.add("male")
    if not named_roles and re.search(
        r"\b(?:general|assassin|fighter|warrior|soldier|guard|officer|protagonist)\b|"
        r"将军|將軍|刺客|战士|戰士|士兵|守卫|守衛|主角",
        text,
        re.I,
    ):
        named_roles.add("person")
    return len(named_roles)


def _request_is_distinct_character(request: dict, anchor: dict) -> bool:
    """Distinguish another actor from another pose of the anchor.

    Auto reference repair commonly emits several frozen states containing the
    *same woman*.  Treating every person-bearing still after the first as a new
    actor destroys identity continuity.  A different gender or an explicit
    secondary/different-person declaration is authoritative; otherwise the
    reference remains support for the established recurring identity.
    """
    if bool(request.get("distinct_character_identity", False)):
        return True
    text = _direct_request_text(request).lower()
    if re.search(
        r"\b(?:different|separate|secondary|another|other|second)\s+"
        r"(?:woman|man|girl|boy|person|character|actor)\b|"
        r"不同(?:的)?(?:女人|男人|人物|角色)|另一(?:个|個)(?:女人|男人|人物|角色)",
        text,
        re.I,
    ):
        return True
    if re.search(r"\bthe\s+same\s+(?:woman|man|girl|boy|person|character)\b|同一(?:人物|角色|女人|男人)", text, re.I):
        return False
    anchor_text = _direct_request_text(anchor).lower()
    request_female = bool(re.search(r"\b(?:woman|female|girl|heroine)\b|女人|女性|女孩", text))
    request_male = bool(re.search(r"\b(?:man|male|boy|hero)\b|男人|男性|男孩", text))
    anchor_female = bool(re.search(r"\b(?:woman|female|girl|heroine)\b|女人|女性|女孩", anchor_text))
    anchor_male = bool(re.search(r"\b(?:man|male|boy|hero)\b|男人|男性|男孩", anchor_text))
    return bool(
        (request_female and anchor_male and not anchor_female)
        or (request_male and anchor_female and not anchor_male)
    )


def _append_subject_count_guard(request: dict, *, identity: bool = False) -> None:
    """Make T2I reference people deterministic and safe for later H3 reuse."""

    prompt = str(request.get("prompt", "")).strip()
    count = _request_visible_person_count(request)
    if identity:
        guard = (
            " EXACT SUBJECT COUNT LOCK: exactly one visible identity subject. Use a clean "
            "single-person composition with no background people, crowd, staff, silhouettes, "
            "human reflections, portraits, mannequins, duplicated bodies or face-like figures."
        )
    elif count == 2:
        guard = (
            " EXACT SUBJECT COUNT LOCK: exactly two unique visible people and no one else. "
            "Never duplicate either person; no crowd, staff, silhouettes, human reflections, "
            "portraits, mannequins, split-screen copies or background figures."
        )
    elif count == 1:
        guard = (
            " EXACT SUBJECT COUNT LOCK: exactly one visible person and no one else. No crowd, "
            "staff, silhouettes, human reflections, portraits, mannequins or duplicated bodies."
        )
    else:
        guard = (
            " ENVIRONMENT-ONLY COUNT LOCK: no visible people, human silhouettes, reflections, "
            "portraits, mannequins or face-like figures."
        )
    if "SUBJECT COUNT LOCK:" not in prompt and "ENVIRONMENT-ONLY COUNT LOCK:" not in prompt:
        request["prompt"] = prompt.rstrip(" .") + "." + guard


def _scope_generated_environment_reference(plan: dict, request: dict) -> None:
    """Prevent a project-wide environment still from contaminating every Segment."""

    if str(request.get("reuse_policy", "")) != "whole_design":
        return
    if _request_visible_person_count(request):
        return
    shots = [row for row in plan.get("shots") or [] if isinstance(row, dict)]
    if not shots:
        return
    keywords = {
        token
        for token in re.findall(r"[a-z0-9]{3,}", _direct_request_text(request).lower())
        if token not in {
            "reference", "image", "scene", "shot", "cinematic", "wide", "close",
            "lighting", "background", "supporting", "environment", "action", "state",
        }
    }
    def score(shot: dict) -> tuple[int, float]:
        text = " ".join(
            str(shot.get(key, ""))
            for key in (
                "preset", "subject_action", "environment_response",
                "continuity_state", "additional_direction",
            )
        ).lower()
        return (
            sum(1 for token in keywords if token in text),
            -float(shot.get("start_seconds", 0.0) or 0.0),
        )
    best = max(shots, key=score)
    if score(best)[0] <= 0:
        best = shots[0]
    request["reuse_policy"] = "time_scoped"
    request["start_seconds"] = float(best.get("start_seconds", 0.0) or 0.0)
    request["end_seconds"] = float(
        best.get("end_seconds", request.get("end_seconds", 0.5)) or 0.5
    )
    warnings = [str(value) for value in plan.get("design_warnings") or []]
    warnings.append(
        f"Scoped generated environment reference {request.get('requirement_id', '?')} to "
        f"{request['start_seconds']:.2f}-{request['end_seconds']:.2f}s; environment stills "
        "may not remain globally active and leak earlier locations into later Segments."
    )
    plan["design_warnings"] = warnings


def stabilize_generated_identity_references(plan: dict) -> dict:
    """Make one generated image authoritative for a recurring human identity.

    Independent T2I calls cannot genuinely copy one another.  Letting every
    action-state image define a prominent face therefore causes actor changes.
    One face-bearing request is promoted to a whole-design identity anchor;
    later reference requests become environment/pose support and may not
    introduce a competing face.
    """
    requests = [
        row for row in plan.get("media_requests") or []
        if isinstance(row, dict) and row.get("media_type") == "image"
    ]
    existing_anchor = _existing_identity_anchor(plan)
    if existing_anchor is not None:
        duration = float(plan.get("duration_seconds", 0.0) or 0.0)
        existing_anchor["reuse_policy"] = "whole_design"
        existing_anchor["start_seconds"] = 0.0
        existing_anchor["end_seconds"] = duration
        existing_anchor["identity_anchor"] = True
        media_id = str(existing_anchor.get("media_id") or "P1")
        requirement_id = str(
            existing_anchor.get("requirement_id") or f"identity_{media_id.lower()}"
        )
        anchor_label = f"@{media_id}"
        _attach_character_continuity_contract(
            plan,
            existing_anchor,
            anchor_label=anchor_label,
            prompt_field="instruction",
        )
        omitted_request_ids: list[str] = []
        kept_image_requests: list[dict] = []
        for request in requests:
            request.pop("identity_anchor", None)
            prompt = _strip_generated_anchor_augmentation(
                str(request.get("prompt", ""))
            )
            if prompt.startswith(_GENERATED_IDENTITY_PREFIX):
                prompt = prompt[len(_GENERATED_IDENTITY_PREFIX):]
            request["prompt"] = prompt
            if _request_recreates_existing_anchor(request, media_id):
                omitted_request_ids.append(str(request.get("requirement_id") or "generated_pose"))
                continue
            kept_image_requests.append(request)
            if _request_visible_person_count(request) > 0:
                request.pop("identity_anchor_requirement_id", None)
                request.pop("identity_anchor_media_id", None)
                distinct = (
                    " DISTINCT SECONDARY CHARACTER REFERENCE ONLY. This Picture may define the "
                    f"face of a separate story character, but its face belongs only to that character "
                    f"and must never replace or blend with the user-supplied {anchor_label} identity."
                )
                if distinct.strip() not in request["prompt"]:
                    request["prompt"] = request["prompt"].rstrip(" .") + "." + distinct
                _append_subject_count_guard(request)
                continue
            request["identity_anchor_requirement_id"] = requirement_id
            request["identity_anchor_media_id"] = media_id
            authority = (
                f" The authoritative recurring face identity is the user-supplied {anchor_label}; "
                f"this generated Picture must never replace, reinterpret or compete with {anchor_label}. "
                "If the recurring character is visible, keep the face fully out of frame, turned "
                "away, motion-obscured or otherwise unreadable; never synthesize a substitute "
                "front-facing face. H3 must derive the recognizable face exclusively from the "
                f"user-supplied {anchor_label}."
            )
            if authority.strip() not in request["prompt"]:
                request["prompt"] = request["prompt"].rstrip(" .") + "." + authority
            if _SUPPORT_CONTINUITY_DIRECTION.strip() not in request["prompt"]:
                request["prompt"] += _SUPPORT_CONTINUITY_DIRECTION
            if "SUPPORTING ENVIRONMENT OR ACTION-STATE REFERENCE ONLY" not in request["prompt"]:
                request["prompt"] += (
                    " SUPPORTING ENVIRONMENT OR ACTION-STATE REFERENCE ONLY. Do not define a "
                    "different prominent human face and do not introduce another actor; prefer rear, "
                    "profile, wide or partially obscured staging whenever a face is not essential."
                )
            _scope_generated_environment_reference(plan, request)
            _append_subject_count_guard(request)
        kept_object_ids = {id(row) for row in kept_image_requests}
        omitted_objects = {id(row) for row in requests if id(row) not in kept_object_ids}
        plan["media_requests"] = [
            row for row in plan.get("media_requests") or []
            if id(row) not in omitted_objects
        ]
        warnings = [str(value) for value in plan.get("design_warnings") or []]
        warnings = [
            value for value in warnings
            if not value.startswith("Promoted ")
            or "generated Pictures cannot redefine" not in value
        ]
        notice = (
            f"Locked user-supplied {media_id} as the whole-design primary face identity anchor; "
            "generated Pictures are support references and cannot redefine a competing face."
        )
        if notice not in warnings:
            warnings.append(notice)
        if omitted_request_ids:
            warnings.append(
                "Omitted independently generated action-state Picture request(s) "
                + ", ".join(omitted_request_ids)
                + f" because they attempted to recreate {media_id}; the real {media_id} remains the "
                "only face source and Shot prose supplies those poses."
            )
        plan["design_warnings"] = warnings
        return plan
    if not requests:
        return plan
    # A planner can incorrectly label a landscape/prop still as an identity
    # anchor. Identity metadata is valid only when the requested frozen frame
    # positively contains a person; negative wording such as ``no people`` is
    # not evidence of a character.
    for request in requests:
        if bool(request.get("identity_anchor", False)) and not _request_visible_person_count(request):
            request.pop("identity_anchor", None)
            request.pop("identity_anchor_requirement_id", None)
            request.pop("identity_anchor_media_id", None)
            request.pop("character_continuity_contract", None)
            request["prompt"] = _strip_generated_anchor_augmentation(
                str(request.get("prompt", ""))
            )
            if request["prompt"].startswith(_GENERATED_IDENTITY_PREFIX):
                request["prompt"] = request["prompt"][len(_GENERATED_IDENTITY_PREFIX):]
            request["prompt"] = re.split(
                r"\s+(?:EXACT SUBJECT COUNT LOCK:|CHARACTER CONTINUITY CONTRACT for )",
                request["prompt"],
                maxsplit=1,
                flags=re.I,
            )[0].rstrip(" .")
    explicit_anchor = next(
        (
            row for row in requests
            if bool(row.get("identity_anchor", False))
            and _request_visible_person_count(row) > 0
        ),
        None,
    )
    # Normalization may run more than once (Plan, Apply, project reload).  Strip
    # an earlier promotion from every non-authoritative request first so an
    # environment still can never retain an identity-anchor prefix.
    for request in requests:
        if request is explicit_anchor:
            continue
        request["prompt"] = _strip_generated_anchor_augmentation(
            str(request.get("prompt", ""))
        )
        request.pop("identity_anchor", None)
    anchor = explicit_anchor or next(
        (
            row for row in requests
            if _request_visible_person_count(row) > 0
        ),
        None,
    )
    if anchor is None:
        for request in requests:
            _scope_generated_environment_reference(plan, request)
            _append_subject_count_guard(request)
        return plan
    duration = float(plan.get("duration_seconds", 0.0) or 0.0)
    anchor["reuse_policy"] = "whole_design"
    anchor["start_seconds"] = 0.0
    anchor["end_seconds"] = duration
    anchor["identity_anchor"] = True
    anchor_id = str(anchor.get("requirement_id", "primary_identity"))
    anchor["prompt"] = _strip_generated_anchor_augmentation(
        str(anchor.get("prompt", ""))
    )
    if "PRIMARY RECURRING CHARACTER IDENTITY ANCHOR" not in anchor["prompt"]:
        anchor["prompt"] = _GENERATED_IDENTITY_PREFIX + anchor["prompt"]
    _append_subject_count_guard(anchor, identity=True)
    _attach_character_continuity_contract(
        plan,
        anchor,
        anchor_label=f"generated reference {anchor_id}",
        prompt_field="prompt",
    )
    ledger = " ".join(str(plan.get("creative_brief", "")).split())[:700]
    for request in requests:
        if request is anchor:
            continue
        person_count = _request_visible_person_count(request)
        if person_count and _request_is_distinct_character(request, anchor):
            # A second actor is a separate identity source, not pose support
            # for the primary character.  Binding it to the primary anchor
            # causes face blending and duplicated dialogue partners.
            request.pop("identity_anchor_requirement_id", None)
            request.pop("identity_anchor_media_id", None)
            request["distinct_character_identity"] = True
            distinct = (
                " DISTINCT SECONDARY CHARACTER IDENTITY. This Picture defines only this separate "
                "story character. Never blend, replace or duplicate the primary character with it."
            )
            if "DISTINCT SECONDARY CHARACTER IDENTITY" not in str(request.get("prompt", "")):
                request["prompt"] = str(request.get("prompt", "")).rstrip(" .") + "." + distinct
            _append_subject_count_guard(request)
            continue
        request["identity_anchor_requirement_id"] = anchor_id
        if "SUPPORTING ENVIRONMENT OR ACTION-STATE REFERENCE ONLY" not in str(
            request.get("prompt", "")
        ):
            request["prompt"] = (
                str(request.get("prompt", "")).rstrip(" .")
                + ". SUPPORTING ENVIRONMENT OR ACTION-STATE REFERENCE ONLY. Do not define a "
                "different prominent human face and do not introduce another actor. If the recurring "
                "character is visible, keep the same age, facial structure, hair, wardrobe and prop "
                "ownership established by the primary identity anchor; prefer rear, profile, wide or "
                "partially obscured staging when exact face consistency cannot be guaranteed."
                + (f" Story identity ledger: {ledger}." if ledger else "")
                + _SUPPORT_CONTINUITY_DIRECTION
            )
        elif _SUPPORT_CONTINUITY_DIRECTION.strip() not in str(request.get("prompt", "")):
            request["prompt"] = str(request.get("prompt", "")).rstrip() + _SUPPORT_CONTINUITY_DIRECTION
        _scope_generated_environment_reference(plan, request)
        _append_subject_count_guard(request)
    warnings = [str(value) for value in plan.get("design_warnings") or []]
    notice = (
        f"Promoted {anchor_id} to the whole-design primary character identity anchor; "
        "later generated Pictures cannot redefine a competing face."
    )
    if notice not in warnings:
        warnings.append(notice)
    plan["design_warnings"] = warnings
    return plan


_DIALOGUE_LANGUAGE_ALIASES = {
    "arabic": "Arabic",
    "chinese": "Chinese",
    "mandarin": "Chinese",
    "mandarin chinese": "Chinese",
    "english": "English",
    "french": "French",
    "german": "German",
    "italian": "Italian",
    "japanese": "Japanese",
    "korean": "Korean",
    "portuguese": "Portuguese",
    "russian": "Russian",
    "spanish": "Spanish",
}


def canonical_dialogue_language(value: object) -> str:
    """Return an official H3 language label, ``auto``, or an empty value."""
    text = str(value or "").strip()
    if not text:
        return ""
    if text.lower().startswith("auto"):
        return "auto"
    return _DIALOGUE_LANGUAGE_ALIASES.get(text.lower(), "")


_EXPLICIT_DIALOGUE_LANGUAGE_PATTERNS = {
    "Arabic": re.compile(r"\bArabic\b|\u963f\u62c9\u4f2f\u8bed|\u963f\u62c9\u4f2f\u8a9e", re.I),
    "Chinese": re.compile(
        r"\b(?:Chinese|Mandarin(?:\s+Chinese)?)\b|\u666e\u901a\u8bdd|\u666e\u901a\u8a71|"
        r"\u56fd\u8bed|\u570b\u8a9e|\u4e2d\u6587|\u534e\u8bed|\u83ef\u8a9e",
        re.I,
    ),
    "English": re.compile(r"\bEnglish\b|\u82f1\u8bed|\u82f1\u8a9e", re.I),
    "French": re.compile(r"\bFrench\b|\u6cd5\u8bed|\u6cd5\u8a9e", re.I),
    "German": re.compile(r"\bGerman\b|\u5fb7\u8bed|\u5fb7\u8a9e", re.I),
    "Italian": re.compile(r"\bItalian\b|\u610f\u5927\u5229\u8bed|\u610f\u5927\u5229\u8a9e", re.I),
    "Japanese": re.compile(r"\bJapanese\b|\u65e5\u8bed|\u65e5\u8a9e|\u65e5\u672c\u8a9e", re.I),
    "Korean": re.compile(r"\bKorean\b|\u97e9\u8bed|\u97d3\u8a9e|\u671d\u9c9c\u8bed|\u671d\u9bae\u8a9e", re.I),
    "Portuguese": re.compile(r"\bPortuguese\b|\u8461\u8404\u7259\u8bed|\u8461\u8404\u7259\u8a9e", re.I),
    "Russian": re.compile(r"\bRussian\b|\u4fc4\u8bed|\u4fc4\u8a9e", re.I),
    "Spanish": re.compile(r"\bSpanish\b|\u897f\u73ed\u7259\u8bed|\u897f\u73ed\u7259\u8a9e", re.I),
}


def infer_design_dialogue_language(requirement: str, preferred: object = "auto") -> str:
    """Resolve Design's language selector without delegating the default to the LM."""
    selected = canonical_dialogue_language(preferred)
    if selected and selected != "auto":
        return selected
    text = str(requirement or "")
    explicit: list[tuple[int, str]] = []
    for language, pattern in _EXPLICIT_DIALOGUE_LANGUAGE_PATTERNS.items():
        explicit.extend((match.end(), language) for match in pattern.finditer(text))
    if explicit:
        return max(explicit, key=lambda item: item[0])[1]
    if re.search(r"[\u3040-\u30ff]", text):
        return "Japanese"
    if re.search(r"[\uac00-\ud7af]", text):
        return "Korean"
    if re.search(r"[\u0600-\u06ff]", text):
        return "Arabic"
    if re.search(r"[\u0400-\u04ff]", text):
        return "Russian"
    if re.search(r"[\u3400-\u9fff]", text):
        return "Chinese"
    return "English"


def _dialogue_text_matches_language(text: str, language: str) -> bool:
    """Catch obvious script mismatches; Latin-language nuance remains an LM task."""
    value = str(text or "").strip()
    if not value:
        return True
    if language == "Chinese":
        return bool(re.search(r"[\u3400-\u9fff]", value)) and not bool(
            re.search(r"[\u3040-\u30ff\uac00-\ud7af]", value)
        )
    if language == "Japanese":
        return bool(re.search(r"[\u3040-\u30ff]", value))
    if language == "Korean":
        return bool(re.search(r"[\uac00-\ud7af]", value))
    if language == "Arabic":
        return bool(re.search(r"[\u0600-\u06ff]", value))
    if language == "Russian":
        return bool(re.search(r"[\u0400-\u04ff]", value))
    if language == "English":
        return bool(re.search(r"[A-Za-z]", value)) and not bool(
            re.search(r"[\u0400-\u04ff\u0600-\u06ff\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]", value)
        )
    return True


def enforce_design_dialogue_language(
    plan: dict,
    language: object,
    *,
    authored_requirement: str = "",
) -> dict:
    """Reject silently wrong generated dialogue and normalize H3 language labels."""
    selected = canonical_dialogue_language(language)
    if not selected or selected == "auto":
        selected = infer_design_dialogue_language(authored_requirement, "auto")
    result = deepcopy(plan)
    authored_contents = {
        str(item.get("content", "")).strip()
        for item in extract_explicit_timed_text_layers(
            authored_requirement,
            float(result.get("duration_seconds", 0.0) or 0.0) or None,
        )
    }
    for index, layer in enumerate(result.get("text_layers") or [], 1):
        if not isinstance(layer, dict) or str(layer.get("role", "")).lower() not in {
            "dialogue", "voice_over", "lyrics",
        }:
            continue
        content = str(layer.get("content", "")).strip()
        current = canonical_dialogue_language(layer.get("language"))
        is_exact_authored = content in authored_contents
        if is_exact_authored:
            if current:
                layer["language"] = current
            elif _dialogue_text_matches_language(content, selected):
                layer["language"] = selected
            else:
                layer["language"] = infer_design_dialogue_language(content, "auto")
            continue
        if current and current != selected:
            raise DesignDialogueLanguageContractError(
                f"Dialogue language contract mismatch in text layer {index}: Design selected "
                f"{selected}, but the AI returned {current}. Regenerate the dialogue in {selected}."
            )
        if not _dialogue_text_matches_language(content, selected):
            raise DesignDialogueLanguageContractError(
                f"Dialogue language contract mismatch in text layer {index}: Design selected "
                f"{selected}, but the generated words do not use the expected script. "
                f"Regenerate the words in {selected}; do not merely relabel English text."
            )
        layer["language"] = selected
    result["_dialogue_language"] = selected
    return result


_REQUESTED_SPEECH_ROLE_PATTERNS = {
    "dialogue": re.compile(
        r"\b(?:dialogue|conversation|spoken\s+lines?)\b|"
        r"\u5bf9\u767d|\u5c0d\u767d|\u5bf9\u8bdd|\u5c0d\u8a71",
        re.I,
    ),
    "voice_over": re.compile(
        r"\b(?:voice[ -]?over|narration|narrator)\b|"
        r"\u65c1\u767d|\u753b\u5916\u97f3|\u756b\u5916\u97f3",
        re.I,
    ),
    "lyrics": re.compile(
        r"\blyrics?\b|\u6b4c\u8bcd|\u6b4c\u8a5e",
        re.I,
    ),
}

_SHOT_EMBEDDED_SPEECH_RE = re.compile(
    r"\b(?:the\s+)?(?:narrator|voice[ -]?over|s[12]|woman|man|character)\s+"
    r"(?:says?|speaks?|continues?|asks?|replies?|whispers?|shouts?)\s*[:\u2014-]|"
    r"\u65c1\u767d\s*(?:\u8bf4|\u8aaa|\u7ee7\u7eed|\u7e7c\u7e8c)?\s*[:\uff1a]",
    re.I,
)


def requested_speech_roles(requirement: str) -> set[str]:
    """Return speech roles that the user explicitly asked Design to author."""
    text = str(requirement or "")
    return {
        role for role, pattern in _REQUESTED_SPEECH_ROLE_PATTERNS.items()
        if pattern.search(text)
    }


SPEECH_TIMELINE_REMINDER_PREFIX = "[TIMELINE REMINDER]"
SPEECH_TIMELINE_MARKER_PREFIX = "⚠ ADD EDITABLE "


def missing_requested_speech_roles(requirement: str, plan: dict) -> set[str]:
    """Return requested spoken roles that have no editable authored layer."""
    requested = requested_speech_roles(requirement)
    present = {
        str(item.get("role", "")).strip().lower()
        for item in plan.get("text_layers") or []
        if isinstance(item, dict)
        and str(item.get("content", "")).strip()
        and bool(item.get("explicit_user_requested", False))
    }
    return requested.difference(present)


def reconcile_requested_speech_layer_contract(requirement: str, plan: dict) -> dict:
    """Make missing AI-authored speech non-blocking without silently losing it.

    Exact time-coded user wording remains protected by
    :func:`validate_explicit_timed_text_contract`.  This fallback is only for a
    broader request such as "add suitable dialogue" where the LM returned no
    editable words.  The workspace can still be applied, while a red Timeline
    marker makes the omission impossible to overlook.  The marker is UI-only
    and the Studio compiler excludes it from H3 technical instructions.
    """
    result = deepcopy(plan)
    missing = sorted(missing_requested_speech_roles(requirement, result))
    marker_rows = [
        item for item in result.get("markers") or []
        if isinstance(item, dict)
        and not str(item.get("preset", "")).startswith(SPEECH_TIMELINE_MARKER_PREFIX)
    ]
    warnings = [
        str(item) for item in result.get("design_warnings") or []
        if not str(item).startswith(SPEECH_TIMELINE_REMINDER_PREFIX)
    ]
    if not missing:
        result.pop("_missing_speech_roles", None)
        result["markers"] = marker_rows
        result["design_warnings"] = warnings
        return result

    # If the user supplied exact timed words, losing them is still fatal.  The
    # deterministic protection pass should normally have restored them first.
    exact_roles = {
        str(item.get("role", ""))
        for item in extract_explicit_timed_text_layers(
            requirement,
            float(result.get("duration_seconds", 0.0) or 0.0) or None,
        )
    }
    exact_missing = sorted(set(missing).intersection(exact_roles))
    if exact_missing:
        raise DesignSpeechLayerContractError(
            "Exact user-authored "
            + ", ".join(role.replace("_", "-") for role in exact_missing)
            + " could not be restored as editable Text Layers. Apply remains blocked to "
              "prevent loss or rewriting of the supplied words."
        )

    role_names = [role.replace("_", "-").upper() for role in missing]
    readable_roles = " / ".join(role_names)
    direction = (
        f"Design requested {readable_roles}, but the AI supplied no editable words. "
        "Use the Type Tool to add or confirm the spoken line before Preview/Run. "
        "Workspace Apply is allowed; this UI reminder is never sent to H3."
    )
    marker_rows.append({
        "time_seconds": 0.0,
        "preset": SPEECH_TIMELINE_MARKER_PREFIX + readable_roles,
        "direction": direction,
    })
    warning = f"{SPEECH_TIMELINE_REMINDER_PREFIX} {direction}"
    warnings.append(warning)
    result["markers"] = marker_rows
    result["design_warnings"] = warnings
    result["_missing_speech_roles"] = missing
    return result


def validate_requested_speech_layer_contract(requirement: str, plan: dict) -> set[str]:
    """Require editable Dialogue/Voice-over/Lyrics tracks whenever speech was requested.

    This closes the failure mode where an LM writes ``The narrator says ...`` inside a
    Shot direction.  Shot prose cannot be edited as dialogue and H3 is free to omit,
    paraphrase or translate it, so such a plan must be regenerated rather than applied.
    """
    requested = requested_speech_roles(requirement)
    if not requested:
        return set()
    missing = sorted(missing_requested_speech_roles(requirement, plan))
    if missing:
        embedded: list[str] = []
        for shot in plan.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            prose = " ".join(
                str(shot.get(key, ""))
                for key in ("subject_action", "additional_direction", "optional_flourish")
            )
            if _SHOT_EMBEDDED_SPEECH_RE.search(prose):
                embedded.append(str(shot.get("id") or "Shot"))
        detail = (
            " Speech was incorrectly embedded in Shot prose at " + ", ".join(embedded) + "."
            if embedded else ""
        )
        raise DesignSpeechLayerContractError(
            "The Design Requirement explicitly requests "
            + ", ".join(role.replace("_", "-") for role in missing)
            + ", but the AI returned no editable Text Layer for that role."
            + detail
            + " Regenerate with every spoken line in text_layers, "
              "explicit_user_requested=true, and keep spoken words out of Shot prompts."
        )
    return requested


_VISIBLE_TEXT_REQUEST_RE = re.compile(
    r"\b(?:on[ -]?screen\s+text|title\s+card|show\s+(?:the\s+)?title|subtitles?|captions?)\b|"
    r"\u5c4f\u5e55\u6587\u5b57|\u87a2\u5e55\u6587\u5b57|\u753b\u9762\u6587\u5b57|\u756b\u9762\u6587\u5b57|"
    r"\u663e\u793a\u6807\u9898|\u986f\u793a\u6a19\u984c|\u5b57\u5e55",
    re.I,
)

_AI_VISIBLE_TEXT_SHOT_RE = re.compile(
    r"\b(?:theme\s+text|hashtags?|subtitles?|captions?|on[ -]?screen\s+text|"
    r"overlay\s+text)\b|\u5b57\u5e55|\u4e3b\u9898\u6587\u5b57|\u4e3b\u984c\u6587\u5b57|"
    r"\u8bdd\u9898\u6807\u7b7e|\u8a71\u984c\u6a19\u7c64",
    re.I,
)


def _remove_ai_visible_text_directions(value: object) -> str:
    clauses = re.split(r"(?<=[.!?;\u3002\uff01\uff1f\uff1b])\s*", str(value or "").strip())
    return " ".join(
        clause.strip() for clause in clauses
        if clause.strip() and not _AI_VISIBLE_TEXT_SHOT_RE.search(clause)
    ).strip()


def enforce_design_subtitle_policy(
    plan: dict,
    enabled: bool,
    *,
    authored_requirement: str = "",
) -> dict:
    """Apply the Design subtitle switch deterministically.

    With subtitles off, AI-invented captions/theme hashtags are removed. Explicitly
    authored title/on-screen-text instructions remain valid. With subtitles on, every
    speech Text Layer receives a synchronized editable On-screen Text layer.
    """
    result = deepcopy(plan)
    explicit_visible = [
        item for item in extract_explicit_timed_text_layers(
            authored_requirement,
            float(result.get("duration_seconds", 0.0) or 0.0) or None,
        )
        if item.get("role") == "on_screen_text"
    ]
    exact_visible = {
        (
            str(item.get("content", "")).strip(),
            round(float(item.get("start_seconds", 0.0)), 3),
            round(float(item.get("end_seconds", 0.0)), 3),
        )
        for item in explicit_visible
    }
    retained: list[dict] = []
    for layer in result.get("text_layers") or []:
        if not isinstance(layer, dict):
            continue
        if str(layer.get("role", "")).strip().lower() != "on_screen_text":
            retained.append(deepcopy(layer))
            continue
        identity = (
            str(layer.get("content", "")).strip(),
            round(float(layer.get("start_seconds", 0.0)), 3),
            round(float(layer.get("end_seconds", 0.0)), 3),
        )
        if (
            enabled
            or identity in exact_visible
            or (
                not str(authored_requirement or "").strip()
                and bool(layer.get("explicit_user_requested", False))
            )
        ):
            retained.append(deepcopy(layer))

    if enabled:
        existing = {
            (
                str(item.get("content", "")).strip(),
                round(float(item.get("start_seconds", 0.0)), 3),
                round(float(item.get("end_seconds", 0.0)), 3),
            )
            for item in retained
            if str(item.get("role", "")).strip().lower() == "on_screen_text"
        }
        for speech in result.get("text_layers") or []:
            if not isinstance(speech, dict) or str(speech.get("role", "")).lower() not in {
                "dialogue", "voice_over", "lyrics",
            }:
                continue
            identity = (
                str(speech.get("content", "")).strip(),
                round(float(speech.get("start_seconds", 0.0)), 3),
                round(float(speech.get("end_seconds", 0.0)), 3),
            )
            if not identity[0] or identity in existing:
                continue
            retained.append({
                "start_seconds": float(speech.get("start_seconds", 0.0)),
                "end_seconds": float(speech.get("end_seconds", 0.0)),
                "track": "V4",
                "content": identity[0],
                "role": "on_screen_text",
                "speaker": str(speech.get("speaker", "S1")),
                "language": str(speech.get("language", "")),
                "delivery": "Readable synchronized subtitle; preserve exact spoken words",
                "lip_sync": False,
                "explicit_user_requested": True,
            })
            existing.add(identity)

    result["text_layers"] = retained
    visible_requested = bool(_VISIBLE_TEXT_REQUEST_RE.search(str(authored_requirement or "")))
    if (
        not enabled
        and str(authored_requirement or "").strip()
        and not visible_requested
    ):
        result["theme_text"] = ""
        result["theme_text_explicit_user_requested"] = False
        for shot in result.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            for field in (
                "subject_action", "continuity_state", "optional_flourish",
                "additional_direction",
            ):
                original = str(shot.get(field, ""))
                cleaned = _remove_ai_visible_text_directions(original)
                if cleaned != original.strip():
                    shot[field] = cleaned or (
                        "None."
                        if field == "optional_flourish"
                        else "Preserve the established physical and camera continuity."
                    )
    subtitle_contract = (
        "VISIBLE TEXT WHITELIST: render subtitles only from synchronized Timeline "
        "on_screen_text layers, at their exact authored times and with their exact words. "
        "Never invent, burn in or repeat any other subtitle, caption, lower-third or dialogue text."
        if enabled else
        "VISIBLE TEXT LOCK: do not render spoken Dialogue or Voice-over as visible words. "
        "No subtitles, captions, lower-thirds or burned-in speech text are permitted unless an "
        "explicit Timeline on_screen_text layer exists."
    )
    constraints = str(result.get("constraints", "")).strip()
    constraints = re.sub(
        r"(?:VISIBLE TEXT WHITELIST|VISIBLE TEXT LOCK):.*?(?=(?:CHARACTER CONTINUITY CONTRACT|$))",
        "",
        constraints,
        flags=re.I | re.S,
    ).strip(" .")
    result["constraints"] = (
        constraints + (". " if constraints else "") + subtitle_contract
    )
    result["_subtitles_enabled"] = bool(enabled)
    return result


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

_ACTION_BEAT_SPLIT_RE = re.compile(
    r"(?:[.!?;:\u3002\uff01\uff1f\uff1b\uff1a]+|"
    r",\s*(?=(?:then|next|after(?:ward)?|immediately|simultaneously)\b)|"
    r"\b(?:and\s+then|then|next|afterwards?|simultaneously)\b|"
    r"\s*(?:\u7136\u540e|\u968f\u540e|\u7d27\u63a5\u7740|\u7acb\u5373|\u540c\u65f6|\u4e0e\u6b64\u540c\u65f6)\s*)",
    flags=re.I,
)
_DECORATIVE_ACTION_RE = re.compile(
    r"\b(?:leaf|leaves|spark|sparks|dust|mist|smoke|cloth|cape|hair|debris|"
    r"glow|glitter|particle|petal|rain|lightning|lens flare|motion blur)\b|"
    r"(?:\u843d\u53f6|\u706b\u82b1|\u7070\u5c18|\u70df\u96fe|\u8863\u6446|\u62ab\u98ce|\u5934\u53d1|"
    r"\u788e\u5c51|\u7c92\u5b50|\u82b1\u74e3|\u95ea\u7535|\u5149\u6655|\u8fd0\u52a8\u6a21\u7cca)",
    flags=re.I,
)
_CRITICAL_ACTION_RE = re.compile(
    r"\b(?:strike|slash|stab|thrust|block|parry|deflect|impact|contact|collide|"
    r"land|grip|release|catch|break|fall|escape|exit|finish|end|hold|wound|"
    r"ricochet|redirect|launch|leap|jump|run|step)\b|"
    r"(?:\u653b\u51fb|\u65a9|\u523a|\u6321|\u683c\u6321|\u53cd\u5f39|\u78b0\u649e|\u547d\u4e2d|"
    r"\u843d\u5730|\u6293\u4f4f|\u677e\u5f00|\u6298\u65ad|\u5760\u843d|\u9003\u79bb|\u7ed3\u675f|"
    r"\u505c\u4f4f|\u8df3|\u8dc3|\u8dd1|\u8e0f|\u8f6c\u5411)",
    flags=re.I,
)
_DECISIVE_CONTACT_RE = re.compile(
    r"\b(?:strikes?|blocks?|parries|deflects?|hits?|collides?|breaks?|catches)\b|"
    r"\b(?:strike|slash|stab|thrust|block|parry|deflect|impact|contact|collide|"
    r"hit|wound|break|ricochet|catch)\b|"
    r"(?:\u653b\u51fb|\u65a9|\u523a|\u6321|\u683c\u6321|\u53cd\u5f39|\u78b0\u649e|"
    r"\u547d\u4e2d|\u4f24|\u6298\u65ad|\u6293\u4f4f)",
    flags=re.I,
)
_ACTION_SETUP_RE = re.compile(
    r"\b(?:draws?|unsheathes?|grips?|raises?|aims?|plants?|crouches?|winds?\s+up|"
    r"loads?|hooks?)\b|(?:\u62d4|\u63e1|\u4e3e|\u62ac|\u7784|\u8e72|\u84c4\u529b|\u4e0a\u5f26|\u52fe\u4f4f)",
    flags=re.I,
)

_EXPLICIT_ACTION_ACTOR_RE = re.compile(
    r"\b(?:the\s+)?(?:assassin|general|fighter|warrior|swordsman|swordswoman|"
    r"hero|villain|attacker|defender|guard|soldier|woman|man|girl|boy|subject|"
    r"character)\b|(?:刺客|将军|將軍|刀客|剑客|劍客|侠客|俠客|武士|守卫|守衛|"
    r"士兵|女子|男人|女人|少女|少年|主角|反派)",
    flags=re.I,
)
_LEADING_OUTGOING_RE = re.compile(
    r"^\s*(?:outgoing|exit|end(?:ing)?\s+state|final\s+state)\s*:\s*",
    flags=re.I,
)

_TIMED_TEXT_RANGE_RE = re.compile(
    r"[\[【(（]?\s*"
    r"(?P<start>(?:\d{1,2}:){1,2}\d{1,2}(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:s|秒)?\s*"
    r"(?:-|–|—|~|～|至|到)\s*"
    r"(?P<end>(?:\d{1,2}:){1,2}\d{1,2}(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:s|秒)?\s*"
    r"[\]】)）]?",
    flags=re.I,
)
_TIMED_TEXT_LABEL_RE = re.compile(
    r"^\s*(?:[-*#>]+\s*)?"
    r"(?:(?P<speaker>S[12])\s*)?"
    r"(?P<label>"
    r"(?:(?:普通话|普通話|国语|國語|Mandarin)\s*)?(?:对白|對白|台词|台詞|dialogue)"
    r"|(?:(?:普通话|普通話|国语|國語|Mandarin)\s*)?(?:旁白|画外音|畫外音|voice[\s-]*over|voiceover|narration)"
    r"|(?:歌词|歌詞|lyrics?)"
    r"|(?:屏幕文字|螢幕文字|画面文字|畫面文字|字幕|标题文字|標題文字|on[\s-]*screen\s*text)"
    r")\s*[：:]\s*(?P<content>.*)$",
    flags=re.I,
)
_CJK_RE = re.compile(r"[\u3400-\u9fff]")


def _parse_design_timecode(value: str) -> float:
    parts = [float(item) for item in str(value).strip().split(":")]
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return parts[0] * 60.0 + parts[1]
    return parts[-3] * 3600.0 + parts[-2] * 60.0 + parts[-1]


_EXPLICIT_VIDEO_DURATION_PATTERNS = (
    re.compile(
        r"(?:时长|時長|片长|片長|总长|總長|总时长|總時長|"
        r"创作|創作|制作|製作|生成|我要|我想要|需要|duration|length)"
        r"[^\n。！？.!?]{0,28}?"
        r"(?P<value>\d+(?:\.\d+)?)\s*"
        r"(?P<unit>秒|秒钟|秒鐘|s|sec(?:ond)?s?|分钟|分鐘|min(?:ute)?s?)",
        flags=re.I,
    ),
    re.compile(
        r"(?P<value>\d+(?:\.\d+)?)\s*"
        r"(?P<unit>秒|秒钟|秒鐘|s|sec(?:ond)?s?|分钟|分鐘|min(?:ute)?s?)"
        r"[^\n。！？.!?]{0,16}?(?:视频|影片|短片|片段|video|film)",
        flags=re.I,
    ),
)


def infer_explicit_design_duration(requirement: str) -> float | None:
    """Return an explicit user duration, preferring the latest authored timecode.

    Workspace Timeline duration is deliberately excluded: it is editing context, not
    authority to shorten a newly requested Design.
    """
    text = str(requirement or "")
    candidates: list[float] = []
    for pattern in _EXPLICIT_VIDEO_DURATION_PATTERNS:
        for match in pattern.finditer(text):
            value = float(match.group("value"))
            unit = match.group("unit").lower()
            if unit.startswith("分") or unit.startswith("min"):
                value *= 60.0
            if value > 0.0:
                candidates.append(value)
    for match in _TIMED_TEXT_RANGE_RE.finditer(text):
        end = _parse_design_timecode(match.group("end"))
        if end > 0.0:
            candidates.append(end)
    if not candidates:
        return None
    duration = min(MAX_DESIGN_DURATION_SECONDS, max(candidates))
    return round(round(duration * 2.0) / 2.0, 6)


def _strip_authored_text_quotes(value: str) -> str:
    text = str(value).strip()
    quote_pairs = (("「", "」"), ("『", "』"), ("“", "”"), ('"', '"'), ("'", "'"))
    changed = True
    while changed and len(text) >= 2:
        changed = False
        for left, right in quote_pairs:
            if text.startswith(left) and text.endswith(right):
                text = text[len(left):len(text) - len(right)].strip()
                changed = True
                break
    return text


def _timed_text_role(label: str) -> str:
    lowered = str(label).lower().replace("-", " ")
    if any(token in lowered for token in ("旁白", "画外音", "畫外音", "voice over", "voiceover", "narration")):
        return "voice_over"
    if any(token in lowered for token in ("歌词", "歌詞", "lyric")):
        return "lyrics"
    if any(token in lowered for token in ("屏幕文字", "螢幕文字", "画面文字", "畫面文字", "字幕", "标题文字", "標題文字", "on screen text")):
        return "on_screen_text"
    return "dialogue"


def _timed_text_delivery(context: str, role: str) -> str:
    if role == "on_screen_text":
        return "Readable and precisely timed"
    if re.search(r"委屈|含泪|含淚|眼泪|眼淚|哭|tearful|cry", context, flags=re.I):
        return "Natural, tearful and emotionally controlled"
    if re.search(r"坚定|堅定|坚决|堅決|determined|firm", context, flags=re.I):
        return "Natural, firm and determined"
    if re.search(r"激昂|爆发|爆發|愤怒|憤怒|angry|intense", context, flags=re.I):
        return "Natural and emotionally intense"
    return "Natural"


def extract_explicit_timed_text_layers(
    requirement: str,
    duration_seconds: float | None = None,
) -> list[dict]:
    """Deterministically recover exact, timed authored speech/text from Design prose.

    This parser intentionally runs before and after the language model.  The model may
    refine cinematography, but it is never allowed to decide whether a user's verbatim
    Dialogue, Voice-over, Lyrics or On-screen Text exists.
    """
    text = str(requirement or "")
    if not text.strip():
        return []
    lines = text.splitlines()
    active_range: tuple[float, float] | None = None
    active_context: list[str] = []
    layers: list[dict] = []
    for line_number, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue
        range_match = _TIMED_TEXT_RANGE_RE.search(line)
        if range_match:
            start = _parse_design_timecode(range_match.group("start"))
            end = _parse_design_timecode(range_match.group("end"))
            if end > start:
                if duration_seconds is not None:
                    start = min(max(0.0, start), float(duration_seconds))
                    end = min(max(start, end), float(duration_seconds))
                active_range = (start, end) if end > start else None
                active_context = [line]
        label_line = _TIMED_TEXT_RANGE_RE.sub("", line).strip(" -–—[]【】()（）")
        label_match = _TIMED_TEXT_LABEL_RE.match(label_line)
        if not label_match:
            if active_range:
                active_context.append(line)
            continue
        if not active_range:
            # Untimed narrative labels are not enough to build a deterministic layer.
            continue
        content = _strip_authored_text_quotes(label_match.group("content"))
        if not content and line_number + 1 < len(lines):
            candidate = _strip_authored_text_quotes(lines[line_number + 1])
            if candidate and not _TIMED_TEXT_RANGE_RE.search(candidate):
                content = candidate
        if not content or content.lower() in {"如下", "as follows"}:
            continue
        label = label_match.group("label")
        role = _timed_text_role(label)
        language = (
            "Mandarin Chinese"
            if re.search(r"普通话|普通話|国语|國語|Mandarin", label, flags=re.I)
            else "Chinese"
            if _CJK_RE.search(content)
            else "Original language"
        )
        start, end = active_range
        layer = {
            "start_seconds": round(start, 6),
            "end_seconds": round(end, 6),
            "track": {
                "dialogue": "A4", "voice_over": "A5", "lyrics": "A6",
                "on_screen_text": "V4",
            }[role],
            "content": content,
            "role": role,
            "speaker": (label_match.group("speaker") or "S1").upper(),
            # Kept only through the pre-normalization protection pass.  An
            # omitted speaker means the planner may assign S1/S2 from the
            # speaking character's gender; an explicit S1/S2 remains binding.
            "_speaker_explicit": bool(label_match.group("speaker")),
            "language": language,
            "delivery": _timed_text_delivery(" ".join(active_context), role),
            "lip_sync": role == "dialogue",
            "explicit_user_requested": True,
            "authored_timing_locked": True,
        }
        identity = (role, round(start, 3), round(end, 3), content)
        if not any(
            (item["role"], round(item["start_seconds"], 3), round(item["end_seconds"], 3), item["content"])
            == identity
            for item in layers
        ):
            layers.append(layer)
    return layers


def authored_text_layers_with_plan_assignments(
    requirement: str,
    plan: dict,
    duration_seconds: float | None = None,
) -> list[dict]:
    """Restore exact authored words while retaining safe LM voice assignments.

    Qwen is allowed to decide S1 (female) versus S2 (male) only when the user
    did not write an explicit S1/S2 label.  Timing and verbatim content always
    remain owned by the deterministic parser.
    """
    required = extract_explicit_timed_text_layers(requirement, duration_seconds)
    candidates = [
        item for item in plan.get("text_layers") or [] if isinstance(item, dict)
    ]
    for authored in required:
        if authored.get("_speaker_explicit"):
            continue
        matches = [
            item for item in candidates
            if str(item.get("role", "")) == authored["role"]
            and float(item.get("start_seconds", 0.0)) < authored["end_seconds"] - 1e-6
            and float(item.get("end_seconds", 0.0)) > authored["start_seconds"] + 1e-6
        ]
        if not matches:
            continue
        best = max(
            matches,
            key=lambda item: min(
                authored["end_seconds"], float(item.get("end_seconds", 0.0))
            ) - max(
                authored["start_seconds"], float(item.get("start_seconds", 0.0))
            ),
        )
        speaker = str(best.get("speaker", "")).strip().upper()
        if speaker in {"S1", "S2"}:
            authored["speaker"] = speaker
        for key in ("delivery", "language"):
            value = str(best.get(key, "")).strip()
            if value:
                authored[key] = value
        if authored["role"] == "dialogue":
            authored["lip_sync"] = bool(best.get("lip_sync", True))
    return required


def protect_explicit_timed_text_layers(plan: dict, requirement: str) -> dict:
    """Merge deterministic authored text into a plan, overriding LM paraphrases."""
    result = deepcopy(plan)
    authored_duration = infer_explicit_design_duration(requirement)
    required = authored_text_layers_with_plan_assignments(
        requirement,
        result,
        authored_duration
        or float(result.get("duration_seconds", 0.0) or 0.0)
        or None,
    )
    if not required:
        return result
    # A prior deterministic speech-budget pass may have lengthened the exact
    # authored line without changing a single word. Preserve that safe timing
    # when this protection pass runs again during Validate and Apply.
    for authored in required:
        adjusted = next(
            (
                item for item in result.get("text_layers") or []
                if isinstance(item, dict)
                and bool(item.get("speech_timing_auto_adjusted", False))
                and str(item.get("role", "")) == authored["role"]
                and str(item.get("content", "")).strip() == authored["content"]
                and abs(
                    float(item.get("authored_start_seconds", item.get("start_seconds", -1.0)))
                    - authored["start_seconds"]
                ) <= 0.01
                and abs(
                    float(item.get("authored_end_seconds", item.get("end_seconds", -1.0)))
                    - authored["end_seconds"]
                ) <= 0.01
            ),
            None,
        )
        if adjusted is not None:
            authored.update(deepcopy(adjusted))
    retained: list[dict] = []
    for existing in result.get("text_layers") or []:
        if not isinstance(existing, dict):
            continue
        role = str(existing.get("role", ""))
        start = float(existing.get("start_seconds", 0.0))
        end = float(existing.get("end_seconds", start))
        conflicts = any(
            role == authored["role"]
            and start < authored["end_seconds"] - 1e-6
            and end > authored["start_seconds"] + 1e-6
            for authored in required
        )
        if not conflicts:
            retained.append(deepcopy(existing))
    result["text_layers"] = required + retained
    warnings = [str(item) for item in result.get("design_warnings") or []]
    notice = f"Protected {len(required)} exact timed user-authored text layer(s) from LM rewriting."
    if notice not in warnings:
        warnings.append(notice)
    result["design_warnings"] = warnings
    return result


def validate_explicit_timed_text_contract(requirement: str, plan: dict) -> list[dict]:
    """Raise if a plan silently loses exact text explicitly supplied by the user."""
    authored_duration = infer_explicit_design_duration(requirement)
    required = extract_explicit_timed_text_layers(
        requirement,
        authored_duration
        or float(plan.get("duration_seconds", 0.0) or 0.0)
        or None,
    )
    if not required:
        return []
    actual = [item for item in plan.get("text_layers") or [] if isinstance(item, dict)]
    matched: list[dict] = []
    missing: list[dict] = []
    for item in required:
        candidate = next(
            (
                row for row in actual
                if str(row.get("role", "")) == item["role"]
                and str(row.get("content", "")).strip() == item["content"]
                and (
                    (
                        abs(float(row.get("start_seconds", -1.0)) - item["start_seconds"]) <= 0.01
                        and abs(float(row.get("end_seconds", -1.0)) - item["end_seconds"]) <= 0.01
                    )
                    or (
                        bool(row.get("speech_timing_auto_adjusted", False))
                        and abs(float(row.get("authored_start_seconds", -1.0)) - item["start_seconds"]) <= 0.01
                        and abs(float(row.get("authored_end_seconds", -1.0)) - item["end_seconds"]) <= 0.01
                    )
                )
            ),
            None,
        )
        if candidate is None:
            missing.append(item)
        else:
            matched.append(deepcopy(candidate))
    if missing:
        raise ValueError(
            "The Design requirement contains explicit timed Dialogue/Voice-over/Lyrics/On-screen "
            f"Text, but {len(missing)} exact layer(s) are missing. Apply/Run is blocked to prevent "
            "silent video generation. Regenerate or restore the authored text layers."
        )
    return matched


_AUTO_SOUND_MIX_MARKER = "Production mix contract:"
_AUTO_MUSIC_MIX_MARKER = "Music mix contract:"
_SPATIAL_ACOUSTICS_MARKER = "Spatial acoustics contract:"
DESIGN_MUSIC_MODES = ("off", "auto", "timeline")


def _audio_design_evidence(plan: dict) -> str:
    shots = [item for item in plan.get("shots") or [] if isinstance(item, dict)]
    return " ".join(
        str(value or "")
        for value in (
            plan.get("creative_brief"),
            *(item.get("environment_response", "") for item in shots),
            *(item.get("subject_action", "") for item in shots),
            *(item.get("additional_direction", "") for item in shots),
        )
    ).lower()


def _without_generated_mix_contract(value: object, marker: str) -> str:
    normalized = " ".join(str(value or "").split())
    index = normalized.lower().find(marker.lower())
    return normalized[:index].rstrip(" .") if index >= 0 else normalized.rstrip(" .")


def _location_ambience(evidence: str) -> str:
    if any(word in evidence for word in ("vehicle", "car", "taxi", "van", "bus", "train", "车", "車")):
        return "Natural vehicle-cabin tone, engine and road vibration, exterior traffic filtered by the windows."
    if any(word in evidence for word in ("cave", "tunnel", "地下", "洞穴", "山洞")):
        return "Dark enclosed-space ambience with air movement, distant water and physically plausible cave reflections."
    if any(word in evidence for word in ("office", "desk", "computer", "workspace", "办公室", "辦公室")):
        return "Natural office room tone, restrained HVAC, distant activity and subtle desk presence."
    if any(word in evidence for word in ("city", "street", "traffic", "road", "城市", "街", "公路")):
        return "Natural city location tone with layered distant traffic, pedestrians and perspective-correct exterior activity."
    if any(word in evidence for word in ("water", "pond", "river", "sea", "rain", "pool", "水", "雨", "池", "河", "海")):
        return "Continuous outdoor location tone with wind, nearby water movement and natural distant environmental detail."
    if any(word in evidence for word in ("forest", "mountain", "garden", "courtyard", "roof", "tree", "森林", "山", "庭院", "屋顶", "屋頂", "树", "樹")):
        return "Natural outdoor ambience with wind through the environment, foliage movement and a stable distant location bed."
    if any(word in evidence for word in ("room", "interior", "home", "hotel", "shop", "室内", "室內", "房间", "房間", "酒店")):
        return "Natural interior room tone with subtle air movement, exterior bleed and room-size-appropriate reflections."
    return "Natural location room tone with a continuous, perspective-correct environmental bed."


def _foley_priorities(evidence: str) -> list[str]:
    priorities: list[str] = []

    def add(label: str, words: tuple[str, ...]) -> None:
        if any(word in evidence for word in words) and label not in priorities:
            priorities.append(label)

    add("footsteps, landings and surface contact", ("walk", "run", "step", "jump", "land", "追", "跑", "走", "跳", "踏"))
    add("cloth, costume and body-movement rustle", ("cloth", "cape", "coat", "dress", "robe", "衣", "披风", "披風", "裙"))
    add("weapon movement, metallic contact and impact transients", ("sword", "spear", "knife", "dart", "weapon", "gun", "blade", "剑", "劍", "刀", "枪", "槍", "暗器"))
    add("vehicle engine, tires, brakes and door contact", ("vehicle", "car", "taxi", "van", "drive", "车", "車", "驾驶", "駕駛"))
    add("water splashes, droplets and surface disturbance", ("water", "pond", "river", "rain", "pool", "水", "雨", "池", "河"))
    add("doors, latches and object handling", ("door", "handle", "open", "close", "门", "門", "开门", "開門"))
    add("phone taps, handling and interface cues", ("phone", "smartphone", "手机", "手機"))
    add("glass, bottle, can and liquid handling", ("glass", "bottle", "can", "drink", "pour", "杯", "瓶", "罐", "喝", "倒"))
    add("fire, debris and pressure impacts", ("fire", "explosion", "debris", "spark", "火", "爆炸", "碎片", "火花"))
    return priorities[:4]


def spatial_acoustics_profile(evidence: object) -> tuple[str, str]:
    """Infer a concise, executable acoustic space from visible-scene evidence."""
    text = " ".join(str(evidence or "").lower().split())

    def has(*words: str) -> bool:
        return any(word in text for word in words)

    if has("small reflective room", "bathroom", "washroom", "tile", "tiled", "浴室", "洗手间", "瓷砖"):
        return (
            "small reflective room",
            "use bright short reflections, 0.35-0.65s decay and restrained 6-10% wetness; "
            "control metallic flutter so consonants remain precise",
        )
    if has("cave", "tunnel", "cavern", "underground", "洞穴", "隧道", "地下"):
        return (
            "cave or tunnel",
            "use sparse directional echoes and a dark 1.2-2.2s decay at 10-16% wetness; "
            "keep the direct voice dominant and place each return behind the visible surfaces",
        )
    if has("car", "vehicle", "taxi", "van", "bus", "train cabin", "车内", "汽车", "的士"):
        return (
            "vehicle cabin",
            "use very short 0.12-0.28s upholstered cabin reflections at 3-6% wetness, "
            "with close low-level road and body-panel resonance but no audible echo repeat",
        )
    if has(
        "large interior", "grand hall", "large hall", "ballroom", "auditorium", "warehouse", "hangar",
        "cathedral", "station concourse", "大堂", "大厅", "礼堂", "仓库", "车站大厅",
    ):
        return (
            "large interior",
            "use a clear 20-45ms pre-delay, broad early reflections and a controlled 0.9-1.8s "
            "tail at 10-16% wetness; reduce the tail beneath speech endings so words stay intelligible",
        )
    if has("corridor", "hallway", "stairwell", "passage", "走廊", "楼梯间", "通道"):
        return (
            "corridor or stairwell",
            "use narrow directional early reflections and one restrained 0.6-1.1s return at "
            "7-12% wetness; avoid rhythmic multi-tap echo on dialogue",
        )
    if has(
        "small furnished room", "living room", "bedroom", "small room", "office", "hotel room", "apartment",
        "客厅", "卧室", "小房间", "办公室", "酒店房间", "公寓",
    ):
        return (
            "small furnished room",
            "use close bright early reflections, a short 0.18-0.45s decay and subtle 4-8% "
            "wetness; retain high-frequency room detail without making the voice hollow",
        )
    if has(
        "medium furnished interior", "restaurant", "cafe interior", "coffee shop interior", "classroom", "shop interior",
        "studio apartment", "餐厅", "咖啡店室内", "教室", "商店室内",
    ):
        return (
            "medium furnished interior",
            "use diffuse early reflections and a moderate 0.35-0.75s decay at 6-11% wetness; "
            "keep foreground dialogue centered and clearly ahead of the room tail",
        )
    if has(
        "covered semi-outdoor space", "awning", "covered stall", "coffee stall", "street stall", "pavilion", "veranda",
        "covered platform", "雨棚", "摊位", "凉亭", "骑楼", "有盖站台",
    ):
        return (
            "covered semi-outdoor space",
            "use only short 0.12-0.32s early reflections from the nearby roof, counter and wall "
            "at 3-6% wetness; keep the street-facing side open with no long enclosed-room tail",
        )
    if has(
        "open exterior", "outdoor", "exterior", "street", "road", "courtyard", "rooftop", "field", "forest",
        "mountain", "beach", "garden", "pond", "户外", "街道", "道路", "庭院", "屋顶",
        "田野", "森林", "山", "海边", "花园", "池塘",
    ):
        return (
            "open exterior",
            "use almost no reverb (0-0.15s, 0-3% wetness), no discrete echo and no enclosed tail; "
            "reduce low-mid body and proximity fullness slightly, preserving a thinner direct voice "
            "with distance, wind and open-air diffusion",
        )
    return (
        "neutral visible location",
        "derive only subtle early reflections from visible nearby surfaces, keep the direct sound "
        "dominant, and never invent a large enclosed acoustic space",
    )


def spatial_acoustics_schedule(plan: dict) -> str:
    """Build a time-scoped acoustic schedule, collapsing adjacent equal spaces."""
    shots = [item for item in plan.get("shots") or [] if isinstance(item, dict)]
    if not shots:
        profile, direction = spatial_acoustics_profile(_audio_design_evidence(plan))
        return f"{profile}: {direction}."

    rows: list[dict] = []
    for shot in shots:
        evidence = " ".join(
            str(shot.get(field, "") or "")
            for field in (
                "framing", "camera_angle", "subject_action", "environment_response",
                "additional_direction", "detail", "continuity_state",
            )
        )
        profile, direction = spatial_acoustics_profile(evidence)
        if profile == "neutral visible location" and rows:
            profile = rows[-1]["profile"]
            direction = rows[-1]["direction"]
        start = float(shot.get("start_seconds", 0.0) or 0.0)
        end = float(shot.get("end_seconds", start) or start)
        if rows and rows[-1]["profile"] == profile and abs(rows[-1]["end"] - start) <= 0.05:
            rows[-1]["end"] = end
        else:
            rows.append({
                "start": start,
                "end": end,
                "profile": profile,
                "direction": direction,
            })
    return " ".join(
        f"{row['start']:.2f}-{row['end']:.2f}s {row['profile']}: {row['direction']}."
        for row in rows
    )


def automatic_background_soundscape(plan: dict) -> str:
    """Build an audible three-layer production mix for any Design/Timeline."""
    evidence = _audio_design_evidence(plan)
    base = _without_generated_mix_contract(
        plan.get("overall_soundscape", ""), _AUTO_SOUND_MIX_MARKER
    )
    # Remove the obsolete auto-authored phrase used by early Design plans. It
    # conflicts with the deterministic space profile below; explicit authored
    # instructions such as "dry voice" or "no reverb" remain untouched.
    base = re.sub(
        r"(?i)\bno artificial reverb tails(?:\s+or\s+studio dryness on the voice)?\b[\s,;:.]*",
        "",
        base,
    ).strip()
    if not base:
        base = _location_ambience(evidence).rstrip(".")
    priorities = _foley_priorities(evidence)
    spatial = spatial_acoustics_schedule(plan)
    foley = (
        " Prioritize exact-frame, contact-synchronized " + ", ".join(priorities) + "."
        if priorities
        else " Add exact-frame Foley only for visible footsteps, cloth, handled objects and physical contacts."
    )
    contract = (
        f" {_AUTO_SOUND_MIX_MARKER} Maintain three clearly audible layers in every Shot: "
        "a continuous diegetic location bed, close contact-synchronized Foley/one-shot SFX, "
        "and foreground speech when authored."
        + foley
        + " On-screen dialogue sounds like live production audio captured in the visible space: "
          "natural breath, conversational micro-pauses, matching camera distance, subtle early "
          "reflections and low environmental bleed; never a dry announcer or studio voice-over. "
        + f" {_SPATIAL_ACOUSTICS_MARKER} {spatial} Apply this profile separately to direct speech, "
          "Foley and ambience according to their visible distance. Crossfade smoothly when the camera "
          "moves between spaces; do not carry an earlier room tail into a later exterior Shot. Acoustic "
          "echo means only physically plausible reflections, never a second performance or repeated words. "
          "Reduce ambience and non-diegetic music by about 6 dB during speech but never mute them; "
          "restore their level naturally between phrases. Keep ambience audible in silent gaps. "
          "Do not duplicate, echo, paraphrase or mask authored words, and do not add generic impacts "
          "without a visible cause."
    )
    return base.rstrip(". ") + "." + contract


def automatic_background_music(plan: dict) -> str:
    """Return a story-aware, always-audible but dialogue-safe music direction."""
    evidence = _audio_design_evidence(plan)
    base = _without_generated_mix_contract(
        plan.get("non_diegetic_music", ""), _AUTO_MUSIC_MIX_MARKER
    )
    if base.strip().lower() in {"n/a", "na", "none", "no music", "no score"}:
        base = ""
    if not base:
        if any(word in evidence for word in ("fight", "battle", "chase", "assassin", "wuxia", "武侠", "武俠", "刺杀", "刺殺", "追捕")):
            base = "Tense cinematic action score with restrained percussion, low strings and short accents that follow major physical beats"
        elif any(word in evidence for word in ("thriller", "kidnap", "police", "danger", "恐怖", "绑架", "綁架", "警方", "危险", "危險")):
            base = "Low suspense pulse with sparse percussion and evolving dark tonal texture"
        elif any(word in evidence for word in ("romance", "love", "emotional", "warm", "爱情", "愛情", "感动", "感動", "温暖", "溫暖")):
            base = "Restrained warm piano and soft strings with an intimate emotional arc"
        elif any(word in evidence for word in ("comedy", "funny", "playful", "幽默", "搞笑", "喜剧", "喜劇")):
            base = "Light rhythmic pizzicato and restrained playful percussion"
        elif any(word in evidence for word in ("product", "commercial", "advert", "品牌", "广告", "廣告", "产品", "產品")):
            base = "Clean contemporary commercial pulse with minimal bass, crisp percussion and a polished final resolve"
        else:
            base = "Subtle cinematic underscore shaped to the story's emotional rise and final resolution"
    contract = (
        f" {_AUTO_MUSIC_MIX_MARKER} Keep the score clearly audible as a separate non-diegetic layer, "
        "but subordinate to dialogue and important diegetic effects. Duck it about 8 dB under speech, "
        "let it rise smoothly in dialogue gaps and transitions, and place only a few motivated accents "
        "on major reveals, impacts or emotional turns. Preserve continuity across cuts, avoid wall-to-wall "
        "maximum loudness, and use no vocals unless authored Lyrics explicitly require them."
    )
    return base.rstrip(". ") + "." + contract


def normalize_design_music_mode(value: object) -> str:
    """Return the persistent Design/H3 music policy, defaulting to AUTO."""
    normalized = str(value or "auto").strip().lower()
    return normalized if normalized in DESIGN_MUSIC_MODES else "auto"


def enforce_design_music_mode(plan: dict, mode: object) -> dict:
    """Apply the selected music policy without changing visual or speech data."""
    result = deepcopy(plan)
    resolved = normalize_design_music_mode(mode)
    if resolved == "auto":
        result["non_diegetic_music"] = automatic_background_music(result)
    else:
        result["non_diegetic_music"] = "N/A"
    if resolved == "off":
        result["markers"] = [
            row for row in result.get("markers") or []
            if "music" not in str(row.get("preset", "")).lower()
        ]
    result["_music_mode"] = resolved
    return result


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
                    "continuity_state", "optional_flourish", "additional_direction",
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
                    "continuity_state": {"type": "string"},
                    "optional_flourish": {"type": "string"},
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
                        "enum": [
                            "h3_reference",
                            "timeline_visual",
                            "analysis_only",
                            "route_control_analysis_only",
                        ],
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
                    "preferred_media_id": {
                        "type": "string",
                        "pattern": "^P[1-9][0-9]*$",
                    },
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


def _repair_overlapping_camera_shots(
    shots: list[dict],
    duration: float,
    warnings: list[str],
) -> None:
    """Move ambiguous adjacent camera cuts onto one shared 0.5s boundary.

    Design models occasionally return ranges such as S5 20.0-26.0 and
    S6 25.5-31.0 even though the Director Shot lane is sequential. Rejecting
    the whole plan makes an otherwise usable Design impossible to Apply. A
    camera cut has no overlap semantics, so split the disputed interval at the
    nearest half-second midpoint while keeping at least one grid cell in both
    Shots. Media and authored text layers are deliberately untouched: those
    are allowed to overlap on their own Timeline tracks.
    """
    index = 1
    while index < len(shots):
        previous = shots[index - 1]
        current = shots[index]
        previous_end = float(previous["end_seconds"])
        current_start = float(current["start_seconds"])
        if current_start >= previous_end - 1e-6:
            index += 1
            continue

        previous_start = float(previous["start_seconds"])
        current_end = float(current["end_seconds"])
        minimum_boundary = round(previous_start + 0.5, 2)
        maximum_boundary = round(current_end - 0.5, 2)
        if minimum_boundary > maximum_boundary + 1e-6:
            merged_fields = (
                "subject_action", "environment_response", "continuity_state",
                "optional_flourish", "additional_direction",
            )
            for field_name in merged_fields:
                first = str(previous.get(field_name, "")).strip()
                second = str(current.get(field_name, "")).strip()
                if second and second not in first:
                    previous[field_name] = ". ".join(
                        item.rstrip(" .") for item in (first, second) if item
                    ) + "."
            previous["start_seconds"] = min(previous_start, float(current["start_seconds"]))
            previous["end_seconds"] = max(previous_end, current_end)
            shots.pop(index)
            warnings.append(
                f"Auto-merged overlapping camera Shots S{index}/S{index + 1}: their "
                "combined range was too short to preserve two 0.50s camera cells. "
                "Core actions and continuity were retained in one executable Shot; "
                "overlapping media/text tracks were preserved."
            )
            continue

        boundary = snap_half_second(
            (previous_end + current_start) / 2.0,
            duration,
        )
        boundary = min(max(boundary, minimum_boundary), maximum_boundary)
        boundary = round(boundary, 2)
        previous["end_seconds"] = boundary
        current["start_seconds"] = boundary
        warnings.append(
            f"Auto-repaired overlapping camera Shots S{index}/S{index + 1}: "
            f"S{index} ended at {previous_end:.2f}s and S{index + 1} started at "
            f"{current_start:.2f}s; both now share the {boundary:.2f}s cut boundary. "
            "Only the Shot lane was repaired; overlapping media/text tracks were preserved."
        )
        index += 1


def _retime_design_payload(source: dict, target_duration: float) -> str:
    """Scale a model's complete timing plan onto an explicit user duration."""

    original_duration = max(
        0.5,
        snap_half_second(
            source.get("duration_seconds", target_duration),
            MAX_DESIGN_DURATION_SECONDS,
        ),
    )
    if abs(original_duration - target_duration) <= 0.01:
        source["duration_seconds"] = target_duration
        return ""
    ratio = target_duration / original_duration
    for family in ("shots", "text_layers", "existing_media_uses", "media_requests"):
        for row in source.get(family) or []:
            if not isinstance(row, dict):
                continue
            for key in ("start_seconds", "end_seconds"):
                if key in row:
                    row[key] = snap_half_second(
                        float(row.get(key, 0.0) or 0.0) * ratio,
                        target_duration,
                    )
    for family in ("transitions", "markers"):
        for row in source.get(family) or []:
            if isinstance(row, dict) and "time_seconds" in row:
                row["time_seconds"] = snap_half_second(
                    float(row.get("time_seconds", 0.0) or 0.0) * ratio,
                    target_duration,
                )
    source["duration_seconds"] = target_duration
    return (
        f"Auto-retimed the complete Design from {original_duration:.2f}s to the "
        f"explicit {target_duration:.2f}s contract on the 0.5s Timeline grid."
    )


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
        raise DesignJSONDecodeError(
            f"AI response is not valid JSON: line {exc.lineno}, column {exc.colno}",
            line=exc.lineno,
            column=exc.colno,
            position=exc.pos,
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError("AI design JSON must be an object")
    return payload


def _standalone_image_text(value: object) -> str:
    """Remove H3-only or circular image references from a T2I description."""

    text = " ".join(str(value or "").split())
    text = _PICTURE_REFERENCE_RE.sub("the described subject", text)
    text = re.sub(r"(?<![A-Za-z0-9_])@?[PVA]\d+\b", "the described subject", text, flags=re.I)
    text = _DEPENDENT_IMAGE_WORDING_RE.sub("a fully described standalone composition", text)
    text = _NON_STORY_BACKGROUND_RE.sub("the story's real in-world environment", text)
    return " ".join(text.split()).strip(" ,.;")


def _auto_image_request(
    source: dict,
    shot: dict,
    duration: float,
    *,
    requirement_id: str,
    preferred_media_id: str = "",
    instruction: str = "",
) -> dict:
    """Build a deterministic standalone Z-Image request from one story Shot."""

    start, end = _interval(shot, duration)
    preset = _standalone_image_text(shot.get("preset", "Story action")) or "Story action"
    framing = _standalone_image_text(shot.get("framing", "Cinematic medium-wide shot"))
    angle = _standalone_image_text(shot.get("camera_angle", "Eye-level camera"))
    subject_requirement = _standalone_image_text(instruction)
    frozen_state = _single_frame_shot_state(shot)
    story_context = _standalone_image_text(source.get("creative_brief", ""))
    style = _standalone_image_text(source.get("global_visual_style", "cinematic realism"))
    prompt = ". ".join(
        part.rstrip(" .")
        for part in (
            f"Standalone cinematic production frame for {preset}",
            f"Composition: {framing}, {angle}" if framing or angle else "",
            (
                f"Required identity, wardrobe and prop ownership: {subject_requirement}"
                if subject_requirement else ""
            ),
            f"Frozen outgoing physical state: {frozen_state}" if frozen_state else "",
            f"Story location and context: {story_context}" if story_context else "",
            f"Visual treatment: {style}" if style else "",
            (
                "Show exactly one frozen instant with exact subject count, consistent identity, "
                "wardrobe, props, ownership, geography and lighting. Do not show a temporal montage, "
                "repeated body positions, duplicate fighters, or multiple stages of one action"
            ),
        )
        if part
    ) + "."
    request = {
        "requirement_id": requirement_id,
        "media_type": "image",
        "usage": "h3_reference",
        "reuse_policy": "time_scoped",
        "start_seconds": start,
        "end_seconds": end,
        "track": (
            str(shot.get("track", "V1")).strip()
            if str(shot.get("track", "V1")).strip().upper().startswith("V")
            else "V1"
        ),
        "subject_keywords": [preset[:48], requirement_id[:48]],
        "prompt": prompt,
    }
    if preferred_media_id:
        request["preferred_media_id"] = preferred_media_id
    return request


def repair_design_media_plan(
    payload: object,
    capacities: dict[str, int],
    existing_media: list[dict] | None,
) -> tuple[dict, list[str]]:
    """Repair common LM media-planning omissions before strict validation.

    Empty Picture slots are generation capacity, not reusable Media Pool
    assets.  Some local models nevertheless emit them in
    ``existing_media_uses``.  Convert those rows into Z-Image requests and add
    enough time-scoped references to cover the Shot plan at roughly one useful
    state per five seconds, bounded by Shot count and physical API capacity.
    """

    source = deepcopy(extract_design_json(payload))
    duration = max(
        0.5,
        snap_half_second(
            source.get("duration_seconds", 5.0), MAX_DESIGN_DURATION_SECONDS
        ),
    )
    inventory = _media_inventory(existing_media)
    analysis_only_media_ids = {
        _normalized_media_id(row.get("media_id", ""))
        for row in source.get("existing_media_uses") or []
        if isinstance(row, dict) and is_analysis_only_media_use(row)
    }
    loaded_image_count = sum(
        bool(row.get("loaded", False))
        and row.get("media_type") == "image"
        and media_id not in analysis_only_media_ids
        for media_id, row in inventory.items()
    )
    free_image_slots = max(
        0, int(capacities.get("image", 0)) - loaded_image_count
    )
    warnings: list[str] = []
    requests = [
        dict(row) for row in source.get("media_requests") or []
        if isinstance(row, dict)
    ]
    shots = [dict(row) for row in source.get("shots") or [] if isinstance(row, dict)]
    request_ids_seen: set[str] = set()
    for request_index, request in enumerate(requests):
        requirement_id = _normalized_requirement_id(
            request.get("requirement_id"), f"request_{request_index + 1}"
        )
        original_requirement_id = requirement_id
        suffix = 2
        while requirement_id in request_ids_seen:
            requirement_id = f"{original_requirement_id}_{suffix}"
            suffix += 1
        if requirement_id != original_requirement_id:
            warnings.append(
                f"Renamed duplicate media requirement_id {original_requirement_id!r} "
                f"to {requirement_id!r}."
            )
        request["requirement_id"] = requirement_id
        request_ids_seen.add(requirement_id)
        internal_auto = re.fullmatch(r"auto_image_s(\d+)(?:_\d+)?", requirement_id)
        if (
            internal_auto
            and str(request.get("media_type", "")).strip().lower() == "image"
            and 1 <= int(internal_auto.group(1)) <= len(shots)
        ):
            requests[request_index] = _auto_image_request(
                source,
                shots[int(internal_auto.group(1)) - 1],
                duration,
                requirement_id=requirement_id,
                preferred_media_id=str(request.get("preferred_media_id", "")).strip(),
            )
            continue
        if str(request.get("media_type", "")).strip().lower() == "image":
            start, end = _interval(request, duration)
            try:
                _validate_t2i_media_prompt(
                    str(request.get("prompt", "")).strip(),
                    request_number=request_index + 1,
                    start_seconds=start,
                    end_seconds=end,
                    duration_seconds=duration,
                )
            except ValueError as exc:
                shot = max(
                    shots or [{"start_seconds": start, "end_seconds": end}],
                    key=lambda row: max(
                        0.0,
                        min(end, _interval(row, duration)[1])
                        - max(start, _interval(row, duration)[0]),
                    ),
                )
                rebuilt = _auto_image_request(
                    source,
                    shot,
                    duration,
                    requirement_id=requirement_id,
                    preferred_media_id=str(request.get("preferred_media_id", "")).strip(),
                    instruction=" ".join(_string_list(request.get("subject_keywords") or [])),
                )
                rebuilt["start_seconds"], rebuilt["end_seconds"] = start, end
                requests[request_index] = rebuilt
                warnings.append(
                    f"Rebuilt unsafe Z-Image request {requirement_id!r} as a standalone "
                    f"in-world frozen frame: {exc}"
                )
    request_ids = {
        _normalized_requirement_id(row.get("requirement_id"), f"request_{index}")
        for index, row in enumerate(requests, 1)
    }
    valid_uses: list[dict] = []
    has_authored_speech = any(
        isinstance(row, dict)
        and str(row.get("role", "")).strip().lower()
        in {"dialogue", "voice_over", "lyrics"}
        and str(row.get("content", "")).strip()
        for row in source.get("text_layers") or []
    )

    for use_number, raw in enumerate(source.get("existing_media_uses") or [], 1):
        if not isinstance(raw, dict):
            continue
        media_id = _normalized_media_id(raw.get("media_id", ""))
        media_type = _media_type_for_id(media_id) if media_id else ""
        ordinal = int(media_id[1:]) if media_id and media_id[1:].isdigit() else 0
        inventory_row = inventory.get(media_id)
        is_loaded = bool(inventory_row and inventory_row.get("loaded", False))
        within_capacity = bool(
            media_type and 1 <= ordinal <= int(capacities.get(media_type, 0))
        )
        authored_audio_hint = " ".join((
            str(raw.get("requirement_id", "")),
            str(raw.get("instruction", "")),
            " ".join(_string_list(raw.get("subject_keywords") or [])),
        ))
        if (
            not is_loaded
            and within_capacity
            and media_type == "audio"
            and has_authored_speech
            and re.search(
                r"dialogue|voice[-_ ]?over|speech|spoken|narrat|tts|lip[-_ ]?sync|"
                r"台词|臺詞|对白|對白|旁白|语音|語音|普通话|普通話|口型",
                authored_audio_hint,
                flags=re.I,
            )
        ):
            warnings.append(
                f"{media_id} was empty and described authored speech, so its mistaken "
                "existing-media reuse was removed; Apply will reserve a generated TTS Audio slot."
            )
            continue
        if is_loaded or not within_capacity or media_type != "image":
            valid_uses.append(dict(raw))
            continue

        requirement_id = _normalized_requirement_id(
            raw.get("requirement_id"), f"recovered_{media_id.lower()}_{use_number}"
        )
        if requirement_id not in request_ids:
            start, end = _interval(raw, duration)
            shot = max(
                shots or [{"start_seconds": start, "end_seconds": end}],
                key=lambda row: max(
                    0.0,
                    min(end, _interval(row, duration)[1])
                    - max(start, _interval(row, duration)[0]),
                ),
            )
            recovered = _auto_image_request(
                source,
                shot,
                duration,
                requirement_id=requirement_id,
                preferred_media_id=media_id,
                instruction=str(raw.get("instruction", "")),
            )
            recovered["start_seconds"], recovered["end_seconds"] = start, end
            recovered["reuse_policy"] = str(
                raw.get("reuse_policy", "time_scoped")
            )
            requests.append(recovered)
            request_ids.add(requirement_id)
        warnings.append(
            f"{media_id} was empty, so its mistaken existing-media reuse was converted "
            "into a Z-Image generation request."
        )

    unique_uses: list[dict] = []
    use_ids_seen: set[str] = set()
    for use_number, raw in enumerate(valid_uses, 1):
        row = dict(raw)
        requirement_id = _normalized_requirement_id(
            row.get("requirement_id"), f"reuse_{use_number}"
        )
        original_requirement_id = requirement_id
        suffix = 2
        while requirement_id in use_ids_seen:
            requirement_id = f"{original_requirement_id}_{suffix}"
            suffix += 1
        if requirement_id != original_requirement_id:
            warnings.append(
                f"Renamed duplicate existing-media requirement_id "
                f"{original_requirement_id!r} to {requirement_id!r}."
            )
        row["requirement_id"] = requirement_id
        use_ids_seen.add(requirement_id)
        unique_uses.append(row)
    valid_uses = unique_uses
    source["existing_media_uses"] = valid_uses

    valid_picture_ids = {
        _normalized_media_id(row.get("media_id", ""))
        for row in valid_uses
        if _media_type_for_id(_normalized_media_id(row.get("media_id", ""))) == "image"
        and not is_analysis_only_media_use(row)
    }
    image_requests = [row for row in requests if row.get("media_type") == "image"]
    shot_count = len(shots)
    desired_total = min(
        int(capacities.get("image", 0)),
        shot_count,
        max(1, math.ceil(duration / 5.0)),
    ) if shot_count else 0
    usable_total = len(valid_picture_ids) + len(image_requests)
    remaining_capacity = max(0, free_image_slots - len(image_requests))
    needed = min(max(0, desired_total - usable_total), remaining_capacity)

    covered_shots: set[int] = set()
    coverage_rows = [
        row for row in (*valid_uses, *image_requests)
        if str(row.get("media_type", "")) == "image"
        and not is_analysis_only_media_use(row)
    ]
    for row in coverage_rows:
        row_start, row_end = _interval(row, duration)
        best = max(
            range(len(shots)),
            key=lambda index: max(
                0.0,
                min(row_end, _interval(shots[index], duration)[1])
                - max(row_start, _interval(shots[index], duration)[0]),
            ),
            default=-1,
        )
        if best >= 0:
            covered_shots.add(best)
    candidates = [index for index in range(len(shots)) if index not in covered_shots]
    candidates.extend(index for index in range(len(shots)) if index in covered_shots)
    for shot_index in candidates[:needed]:
        requirement_id = f"auto_image_s{shot_index + 1}"
        suffix = 2
        while requirement_id in request_ids:
            requirement_id = f"auto_image_s{shot_index + 1}_{suffix}"
            suffix += 1
        requests.append(
            _auto_image_request(
                source,
                shots[shot_index],
                duration,
                requirement_id=requirement_id,
            )
        )
        request_ids.add(requirement_id)
        warnings.append(
            f"Added {requirement_id} to prevent the Shot plan from having too few visual references."
        )

    final_usable = len(valid_picture_ids) + sum(
        row.get("media_type") == "image" for row in requests
    )
    if desired_total and final_usable < desired_total:
        warnings.append(
            f"Visual reference coverage is {final_usable}/{desired_total}; no more empty Picture slots are available."
        )
    source["media_requests"] = requests
    return source, warnings


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


def collect_design_preflight_blockers(
    payload: object,
    capacities: dict[str, int],
    *,
    existing_media: list[dict] | None = None,
    authored_requirement: str = "",
    selected_media_ids: list[str] | None = None,
) -> list[str]:
    """Collect independent unrecoverable Design defects in one pass.

    This deliberately excludes defects repaired by ``normalize_design_plan``
    (duration, brief/style defaults, duplicate requirement IDs, unsafe T2I
    prompts and camera overlap).  The UI can therefore show every real media /
    structure Hard Block at once instead of revealing one modal per retry.
    """

    try:
        source = extract_design_json(payload)
    except ValueError as exc:
        return [str(exc)]
    blockers: list[str] = []
    shots = [row for row in source.get("shots") or [] if isinstance(row, dict)]
    if not shots:
        blockers.append("Design JSON must contain at least one executable Shot.")

    inventory = _media_inventory(existing_media)
    inventory_was_supplied = existing_media is not None
    selection_was_supplied = selected_media_ids is not None
    selected = {
        _normalized_media_id(value) for value in selected_media_ids or []
        if _normalized_media_id(value)
    }
    explicit_ids = {
        _normalized_media_id(f"{match.group(1)}{match.group(2)}")
        for match in re.finditer(
            r"(?<![A-Za-z0-9_])@([PVA])(\d+)\b",
            str(authored_requirement or ""),
            flags=re.I,
        )
    }
    has_authored_speech = bool(
        extract_explicit_timed_text_layers(authored_requirement)
        or re.search(
            r"dialogue|voice[- ]?over|narration|对白|對白|旁白|台词|台詞|普通话|普通話",
            str(authored_requirement or ""),
            flags=re.I,
        )
    )

    for use_number, raw in enumerate(source.get("existing_media_uses") or [], 1):
        if not isinstance(raw, dict):
            continue
        media_id = _normalized_media_id(raw.get("media_id", ""))
        if not media_id:
            blockers.append(
                f"Existing media use {use_number} has an invalid media_id; use P1, V1 or A1."
            )
            continue
        inferred_type = _media_type_for_id(media_id)
        declared_type = str(raw.get("media_type") or inferred_type).strip().lower()
        if declared_type != inferred_type:
            blockers.append(
                f"Existing media {media_id} is {inferred_type}, not {declared_type}."
            )
            continue
        ordinal = int(media_id[1:])
        if ordinal > int(capacities.get(inferred_type, 0)):
            blockers.append(
                f"Existing media {media_id} is outside the API's "
                f"{capacities.get(inferred_type, 0)} {inferred_type} slots."
            )
            continue
        if inventory_was_supplied:
            inventory_row = inventory.get(media_id)
            if inventory_row is None:
                blockers.append(
                    f"Existing media {media_id} is not present in the Media Pool inventory."
                )
                continue
            inventory_type = str(inventory_row.get("media_type", "")).strip().lower()
            if inventory_type and inventory_type != inferred_type:
                blockers.append(
                    f"Media Pool {media_id} is {inventory_type}, not {inferred_type}."
                )
                continue
            if not inventory_row.get("loaded", False):
                authored_audio_placeholder = (
                    inferred_type == "audio" and has_authored_speech
                )
                recoverable_picture_slot = inferred_type == "image"
                if not authored_audio_placeholder and not recoverable_picture_slot:
                    blockers.append(
                        f"Existing media {media_id} is empty and cannot be reused."
                    )

    for media_id in sorted(explicit_ids):
        row = inventory.get(media_id)
        if not row or not row.get("loaded", False):
            blockers.append(
                f"Explicit reference @{media_id} has no loaded Media Pool file."
            )
        elif selection_was_supplied and media_id not in selected:
            blockers.append(
                f"Explicit reference @{media_id} is not enabled for this Design."
            )

    return list(dict.fromkeys(blockers))


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        value = [item.strip() for item in value.split(",")]
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _canonicalize_design_media_mentions(text: object, media_ids: list[str]) -> str:
    """Canonicalize bare IDs only for media explicitly reused by the plan."""
    result = str(text or "")
    for media_id in media_ids:
        result = re.sub(
            rf"(?<![@\w]){re.escape(media_id)}(?!\w)",
            f"@{media_id}",
            result,
            flags=re.I,
        )
    return result


def _replace_analysis_only_media_mentions(text: object, media_ids: list[str]) -> str:
    """Remove control-image labels from prose that will be compiled for H3.

    Analysis-only images may guide planning, but naming their stable ID inside
    a Shot can cause later reference-token parsing to reactivate that source.
    Replace the ID with its already extracted abstract instruction instead.
    """

    result = str(text or "")
    for media_id in sorted(set(media_ids), key=len, reverse=True):
        match = re.fullmatch(r"([PVA])(\d+)", media_id, flags=re.I)
        if not match:
            continue
        family = {"P": "Picture", "V": "Video", "A": "Audio"}[match.group(1).upper()]
        ordinal = match.group(2)
        for pattern in (
            rf"(?<![A-Za-z0-9_])@?{re.escape(media_id)}\b",
            rf"<\s*{family}\s+{ordinal}\s*>",
        ):
            result = re.sub(
                pattern,
                "the pre-analysed non-visual control instructions",
                result,
                flags=re.I,
            )
    return " ".join(result.split())


def _remove_control_artifact_priming(text: object) -> str:
    """Keep control-image artifact vocabulary out of a single H3 prompt field."""

    result = str(text or "")
    result = re.sub(
        r"\b(?:red\s+(?:route\s+)?line|red\s+route|red\s+waypoint|route\s+graphics?|"
        r"route\s+path\s+overlays?|flight\s+path\s+lines?|map\s+(?:line|overlay)s?|"
        r"visible\s+(?:control\s+path|route\s+guide))\b",
        "the planned camera trajectory",
        result,
        flags=re.I,
    )
    result = re.sub(
        r"\b(?:red\s+arrows?|waypoint\s+markers?|navigation\s+markers?|HUD|UI\s+overlays?|"
        r"graphic\s+overlays?|red\s+scribbles?|red\s+strokes?)\b",
        "editing-only data",
        result,
        flags=re.I,
    )
    return " ".join(result.split())


_DARK_RESCUE_POV_LOCK = (
    "Strict first-person POV from S2's eye line. The camera is physically inside "
    "S2's body and never leaves S2's point of view."
)
_DARK_RESCUE_POV_FORBIDDEN_RE = re.compile(
    r"\b(?:third[- ]person(?:\s+(?:view|shot|camera))?|external\s+camera|"
    r"over[- ]the[- ]shoulder(?:\s+shot)?|hero\s+shot|drone\s+shot|"
    r"crane\s+shot|orbit(?:ing)?\s+shot|security[- ]camera\s+view|"
    r"wide[- ]observer\s+view|camera\s+outside\s+S2(?:'s)?\s+body)\b",
    flags=re.I,
)


def _dark_rescue_pov_sanitize(value: object) -> str:
    """Remove camera language that can pull a rescue Shot outside S2's body."""

    text = str(value or "").strip()
    text = _DARK_RESCUE_POV_FORBIDDEN_RE.sub(
        "body-mounted S2 eye-line composition", text
    )
    text = re.sub(
        r"\b(?:the\s+)?camera\s+(?:follows|tracks)\s+S2\b",
        "S2 moves and the eye-line view moves with S2's body",
        text,
        flags=re.I,
    )
    return " ".join(text.split())


def enforce_dark_rescue_first_person(plan: dict) -> dict:
    """Turn the dark-rescue camera contract into visible, executable POV evidence.

    Language models often retain the words ``first-person`` globally while still
    returning external establishing shots.  H3 receives Shot fields separately,
    so every generated Shot and image request needs both an absolute eye-line lock
    and positive objects that prove the viewpoint in-frame.
    """

    anchors = (
        "the lower edge of S2's wet or dusty glove and flashlight beam",
        "S2's gloved forearm and one role-correct rescue tool in extreme foreground",
        "the edge of S2's helmet and a gloved hand at the lower frame boundary",
    )
    proof_tail = (
        "S2's face, full body, back, observer silhouette and reflection remain off-screen. "
        "All parallax is body-motivated: perspective, head turns, footstep bob, crouching "
        "height and contact recoil are generated only by S2's physically plausible movement."
    )
    for index, shot in enumerate(plan.get("shots") or []):
        if not isinstance(shot, dict):
            continue
        anchor = anchors[index % len(anchors)]
        original_framing = _dark_rescue_pov_sanitize(shot.get("framing"))
        if not original_framing.casefold().startswith(
            "strict first-person pov from s2's eye line"
        ):
            shot["framing"] = (
                f"Strict first-person POV from S2's eye line; {anchor} visibly anchors "
                "near-field depth"
                + (f"; {original_framing}" if original_framing else "")
            )
        else:
            shot["framing"] = original_framing
        original_angle = _dark_rescue_pov_sanitize(shot.get("camera_angle"))
        shot["camera_angle"] = (
            original_angle
            if original_angle.casefold().startswith("s2 body-mounted natural human eye line")
            else "S2 body-mounted natural human eye line"
            + (f"; {original_angle}" if original_angle else "")
        )
        original_movement = _dark_rescue_pov_sanitize(shot.get("camera_movement"))
        shot["camera_movement"] = (
            original_movement
            if original_movement.casefold().startswith(
                "body-motivated first-person movement caused only by s2"
            )
            else "Body-motivated first-person movement caused only by S2"
            + (f"; {original_movement}" if original_movement else "")
        )
        action = _dark_rescue_pov_sanitize(
            shot.get("h3_executable_action") or shot.get("subject_action")
        )
        executable = (
            action
            if action.casefold().startswith("s2's first-person pov")
            else f"S2's first-person POV visibly includes {anchor}. "
            + (action or "Continue the current rescue action from S2's eye line.")
        )
        shot["subject_action"] = executable
        shot["h3_executable_action"] = executable
        budget = shot.get("action_budget")
        if isinstance(budget, dict):
            original = _dark_rescue_pov_sanitize(
                budget.get("original_subject_action") or action
            )
            budget["original_subject_action"] = (
                original
                if original.casefold().startswith("s2's first-person pov")
                else (
                    "S2's first-person POV visibly includes " + anchor + ". " + original
                ).strip()
            )
        detail = _dark_rescue_pov_sanitize(shot.get("additional_direction"))
        if detail.casefold().startswith(_DARK_RESCUE_POV_LOCK.casefold()):
            shot["additional_direction"] = detail
        else:
            shot["additional_direction"] = " ".join(
                part for part in (
                    _DARK_RESCUE_POV_LOCK,
                    f"POV proof in this Shot: {anchor} remains optically near the lens.",
                    proof_tail,
                    detail,
                ) if part
            )
        continuity = _dark_rescue_pov_sanitize(shot.get("continuity_state"))
        pov_continuity = (
            f"Preserve first-person eye height and the screen-side continuity of {anchor}; "
            "the next Shot inherits S2's head direction, hand/tool state and body momentum."
        )
        shot["continuity_state"] = (
            continuity
            if "preserve first-person eye height" in continuity.casefold()
            else " ".join(part for part in (continuity, pov_continuity) if part)
        )

    for request in plan.get("media_requests") or []:
        if not isinstance(request, dict) or request.get("media_type") != "image":
            continue
        prompt = _dark_rescue_pov_sanitize(request.get("prompt"))
        prefix = (
            "A strict first-person POV reference image from S2's physical eye line, "
            "with one wet or dusty gloved hand, flashlight, helmet rim, uniform sleeve "
            "or role-correct rescue tool visible in extreme foreground as perspective proof. "
            "S2's face, full body, back, reflection and observer view are absent."
        )
        if not prompt.casefold().startswith("a strict first-person pov reference image"):
            request["prompt"] = f"{prefix} {prompt}".strip()
        else:
            request["prompt"] = prompt

    for use in plan.get("existing_media_uses") or []:
        if not isinstance(use, dict) or use.get("media_type") != "image":
            continue
        instruction = _dark_rescue_pov_sanitize(use.get("instruction"))
        camera_contract = (
            "Use this image only for its assigned identity, place, prop or damage state; "
            "do not inherit an external camera angle. Render the active Shot from S2's "
            "strict first-person physical eye line."
        )
        use["instruction"] = (
            instruction
            if "do not inherit an external camera angle" in instruction.casefold()
            else " ".join(part for part in (instruction, camera_contract) if part)
        )

    constraint = (
        _DARK_RESCUE_POV_LOCK
        + " Every Shot must visibly prove the viewpoint with a near-lens glove, forearm, "
          "flashlight/tool or helmet rim and body-motivated parallax; never render S2 as an "
          "externally visible subject."
    )
    current = _dark_rescue_pov_sanitize(plan.get("constraints"))
    if _DARK_RESCUE_POV_LOCK.casefold() not in current.casefold():
        plan["constraints"] = " ".join(part for part in (current, constraint) if part)
    else:
        plan["constraints"] = current
    warnings = plan.setdefault("design_warnings", [])
    note = (
        "dark-rescue-h3 enforced physical first-person POV evidence in every Shot and "
        "generated image reference."
    )
    if note not in warnings:
        warnings.append(note)
    return plan


def enforce_drone_scene_keyframe_chain(
    plan: dict,
    existing_media: list[dict] | None,
    selected_media_ids: list[str] | None = None,
) -> dict:
    """Build an isolated user-anchor chain plus one generated terminal frame.

    MiniMax sees every Picture supplied to one native request, even when the
    Pictures occupy different Shot ranges. For the drone route Skill, multiple
    user-authored scene Pictures must therefore own disjoint Timeline ranges;
    the renderer can split those ranges into separate native requests and use
    its visual-only 24-frame continuity handoff between them.

    P2 remains analysis-only. Existing Design-generated Pictures are not
    promoted into new user anchors. The one terminal request intentionally has
    no preferred_media_id, so normal Virtual Media Pool allocation gives it
    the next truly empty Picture number (P4 after P1/P2/P3, P6 after P1-P5).
    """

    result = plan
    duration = float(result.get("duration_seconds", 0.0) or 0.0)
    if duration < 1.5:
        return result
    inventory = {
        str(row.get("media_id", "")).strip().upper(): row
        for row in existing_media or []
        if isinstance(row, dict)
    }

    def ordinal(row: dict) -> int:
        match = re.fullmatch(r"P(\d+)", str(row.get("media_id", "")).upper())
        return int(match.group(1)) if match else 10**9

    def is_generated(media_id: str) -> bool:
        row = inventory.get(media_id, {})
        evidence = " ".join(
            str(row.get(key, ""))
            for key in ("filename", "raw_analysis_summary", "analysis_summary", "clip_prompt")
        ).casefold()
        return bool(
            "ai design generated reference" in evidence
            or "auto terminal keyframe" in evidence
            or "generated_references" in evidence
            or "regenerated_references" in evidence
        )

    uses = [row for row in result.get("existing_media_uses") or [] if isinstance(row, dict)]
    selected_ids = {
        _normalized_media_id(value) for value in selected_media_ids or []
        if _normalized_media_id(value)
    }
    if selected_media_ids is not None:
        declared_ids = {
            str(row.get("media_id", "")).strip().upper() for row in uses
        }
        if "P2" in selected_ids and "P2" not in declared_ids and "P2" in inventory:
            uses.append({
                "requirement_id": "route_control_p2",
                "media_id": "P2",
                "media_type": "image",
                "usage": "analysis_only",
                "reuse_policy": "whole_design",
                "start_seconds": 0.0,
                "end_seconds": duration,
                "track": "V2",
                "subject_keywords": ["off-screen route geometry"],
                "instruction": "Use @P2 only to derive abstract camera motion; never render or upload it.",
            })
            declared_ids.add("P2")
        for media_id in sorted(selected_ids, key=lambda value: int(value[1:]) if value[1:].isdigit() else 10**9):
            if not media_id.startswith("P") or media_id == "P2" or media_id in declared_ids:
                continue
            row = inventory.get(media_id)
            if not row or not bool(row.get("loaded", False)) or is_generated(media_id):
                continue
            evidence = str(
                row.get("semantic_enrichment")
                or row.get("caption")
                or row.get("analysis_summary")
                or row.get("raw_analysis_summary")
                or row.get("filename")
                or "the supplied city scene"
            ).strip()
            uses.append({
                "requirement_id": f"authored_scene_{media_id.lower()}",
                "media_id": media_id,
                "media_type": "image",
                "usage": "h3_reference",
                "reuse_policy": "time_scoped",
                "start_seconds": 0.0,
                "end_seconds": duration,
                "track": "V1",
                "subject_keywords": ["user-authored scene keyframe", media_id],
                "instruction": (
                    f"Use @{media_id} as an authoritative user-authored scene keyframe. "
                    f"Preserve its real environment: {evidence[:900]}"
                ),
            })
            declared_ids.add(media_id)
    result["existing_media_uses"] = uses

    image_uses = [
        row for row in result.get("existing_media_uses") or []
        if isinstance(row, dict)
        and row.get("media_type") == "image"
        and not is_analysis_only_media_use(row)
    ]
    authored_anchors: list[dict] = []
    anchor_ids_seen: set[str] = set()
    for row in sorted(image_uses, key=ordinal):
        media_id = str(row.get("media_id", "")).upper()
        if media_id in anchor_ids_seen:
            continue
        if media_id != "P1" and is_generated(media_id):
            continue
        authored_anchors.append(row)
        anchor_ids_seen.add(media_id)
    # P1 alone remains the ordinary scene-master workflow. The chain activates
    # only after the user supplies at least one additional visual scene.
    if len(authored_anchors) < 2:
        return result
    if duration + 1e-6 < (len(authored_anchors) + 1) * 0.5:
        result.setdefault("design_warnings", []).append(
            "Drone keyframe chain needs at least 0.5s for every user scene and its terminal frame; "
            "the current duration is too short, so automatic terminal generation was skipped."
        )
        return result

    boundaries = [0.0]
    for index in range(1, len(authored_anchors) + 1):
        boundary = snap_half_second(
            duration * index / (len(authored_anchors) + 1), duration
        )
        boundary = max(boundaries[-1] + 0.5, boundary)
        boundaries.append(min(duration - 0.5, boundary))
    boundaries.append(duration)

    authored_ids = {
        str(row.get("media_id", "")).upper() for row in authored_anchors
    }
    authored_row_objects = {id(row) for row in authored_anchors}
    retained_uses: list[dict] = []
    for row in result.get("existing_media_uses") or []:
        if not isinstance(row, dict):
            continue
        media_id = str(row.get("media_id", "")).upper()
        if row.get("media_type") == "image" and not is_analysis_only_media_use(row):
            if media_id not in authored_ids or id(row) not in authored_row_objects:
                continue
        retained_uses.append(row)
    result["existing_media_uses"] = retained_uses

    for index, anchor in enumerate(authored_anchors):
        start = boundaries[index]
        end = boundaries[index + 1]
        media_id = str(anchor.get("media_id", "")).upper()
        anchor["reuse_policy"] = "time_scoped"
        anchor["start_seconds"] = start
        anchor["end_seconds"] = end
        anchor["track"] = "V1"
        anchor.pop("identity_anchor", None)
        marker = (
            f"SCENE KEYFRAME CHAIN ANCHOR {index + 1}/{len(authored_anchors)}. "
            f"User-authored {media_id} owns only {start:.2f}-{end:.2f}s; reconstruct it as the "
            "authoritative real scene for this interval and do not let later scene anchors alter "
            "any earlier frame."
        )
        instruction = str(anchor.get("instruction", "")).strip()
        if "SCENE KEYFRAME CHAIN ANCHOR" in instruction:
            instruction = instruction.split("SCENE KEYFRAME CHAIN ANCHOR", 1)[0].rstrip(" .")
        anchor["instruction"] = (
            instruction.rstrip(" .") + (". " if instruction else "") + marker
        )

    last_anchor = authored_anchors[-1]
    last_id = str(last_anchor.get("media_id", "")).upper()
    last_inventory = inventory.get(last_id, {})
    evidence = str(
        last_inventory.get("semantic_enrichment")
        or last_inventory.get("caption")
        or last_inventory.get("analysis_summary")
        or last_anchor.get("instruction")
        or result.get("creative_brief", "")
    )
    evidence = _remove_control_artifact_priming(
        _replace_analysis_only_media_mentions(evidence, ["P2"])
    )[:1800].strip()
    terminal_start = boundaries[-2]
    terminal_prompt = (
        "AUTO TERMINAL KEYFRAME. ENVIRONMENT-ONLY FINAL FRAME. Create one photoreal settled "
        "closing view continuing the latest user-authored city scene and its exact architecture, "
        "landmark layout, weather, time of day, lighting direction, colour grade, exposure, "
        "atmosphere and lens character. The drone has completed its planned movement, decelerated "
        "naturally and now holds a stable level horizon with coherent aerial parallax. Do not "
        "introduce a person, face, figure, statue-like portrait or rooftop character. Scene evidence: "
        + evidence
    )
    non_image_requests = [
        row for row in result.get("media_requests") or []
        if isinstance(row, dict) and row.get("media_type") != "image"
    ]
    non_image_requests.append({
        "requirement_id": f"auto_terminal_keyframe_after_{last_id.lower()}",
        "media_type": "image",
        "usage": "h3_reference",
        "reuse_policy": "time_scoped",
        "start_seconds": terminal_start,
        "end_seconds": duration,
        "track": "V1",
        "subject_keywords": [
            "automatic terminal keyframe",
            "environment-only closing view",
            "stable drone final hold",
        ],
        "prompt": terminal_prompt,
    })
    result["media_requests"] = non_image_requests
    warning = (
        "Drone scene keyframe chain: "
        + " -> ".join(str(row.get("media_id", "")) for row in authored_anchors)
        + " -> AUTO TERMINAL. User scene anchors were isolated into disjoint native render ranges; "
        "the terminal frame will use the next empty Virtual Media Pool Picture ID."
    )
    warnings = result.setdefault("design_warnings", [])
    if warning not in warnings:
        warnings.append(warning)
    return result


def split_action_beats(value: object) -> list[str]:
    """Return conservative, ordered physical-action clauses for budget checks."""
    text = " ".join(str(value or "").split()).strip(" ,")
    if not text:
        return []
    return [
        part.strip(" ,")
        for part in _ACTION_BEAT_SPLIT_RE.split(text)
        if part and part.strip(" ,")
    ]


def _join_action_beats(beats: list[str]) -> str:
    return ". ".join(beat.strip().rstrip(".") for beat in beats if beat.strip()).strip()


def _bind_action_subjects(beats: list[str]) -> list[str]:
    """Replace ambiguous actor pronouns before budget compression.

    Selecting only a subset of a multi-fighter action can otherwise detach a
    clause such as ``He runs`` from its original antecedent and silently assign
    it to the wrong fighter in the compiled H3 prompt.
    """

    bound: list[str] = []
    current_actor = ""
    for raw in beats:
        beat = raw.strip()
        actors = list(_EXPLICIT_ACTION_ACTOR_RE.finditer(beat))
        if actors:
            current_actor = actors[0].group(0).strip()
        elif current_actor:
            has_subject_pronoun = bool(
                re.search(r"\b(?:he|she|they)\b", beat, flags=re.I)
            )
            if has_subject_pronoun:
                beat = re.sub(r"\b(?:he|she|they)\b", current_actor, beat, flags=re.I)
            else:
                possessive = (
                    re.sub(r"(?:'s|’s)$", "", current_actor, flags=re.I) + "'s"
                )
                beat = re.sub(r"\b(?:his|her|their)\b", possessive, beat, flags=re.I)
            if re.match(r"^(?:他|她|他们|她们|其)", beat):
                beat = re.sub(r"^(?:他|她|他们|她们|其)", current_actor, beat, count=1)
        bound.append(beat)
    return bound


def _single_frame_shot_state(shot: dict) -> str:
    """Return one frozen physical state suitable for a T2I reference."""

    continuity = _standalone_image_text(shot.get("continuity_state", ""))
    if continuity:
        outgoing_match = re.search(
            r"\bOutgoing\s*:\s*(.+)$", continuity, flags=re.I
        )
        state = outgoing_match.group(1).strip() if outgoing_match else continuity
        state = _LEADING_OUTGOING_RE.sub("", state).strip(" ,.;")
        if state:
            return state

    beats = _bind_action_subjects(split_action_beats(shot.get("subject_action", "")))
    return _standalone_image_text(beats[-1] if beats else "")


def _merge_causal_setup_beats(beats: list[str]) -> list[str]:
    """Keep a weapon/setup dependency attached to the decisive action it enables."""
    merged: list[str] = []
    index = 0
    while index < len(beats):
        beat = beats[index]
        if (
            index + 1 < len(beats)
            and _ACTION_SETUP_RE.search(beat)
            and _DECISIVE_CONTACT_RE.search(beats[index + 1])
        ):
            following = beats[index + 1].strip()
            following = following[:1].lower() + following[1:] if following else following
            merged.append(f"{beat.rstrip(' .')}, then {following}")
            index += 2
            continue
        merged.append(beat)
        index += 1
    return merged


def _action_priority(beat: str, index: int, total: int) -> tuple[int, int]:
    score = 0
    if index == 0:
        score += 5
    if index == total - 1:
        score += 6
    if _CRITICAL_ACTION_RE.search(beat):
        score += 4
    if _DECISIVE_CONTACT_RE.search(beat):
        score += 5
    if _DECORATIVE_ACTION_RE.search(beat):
        score -= 3
    return score, index


def normalize_shot_action_budget(shot: dict) -> dict:
    """Compress a Shot into a deterministic H3-executable action hierarchy.

    ``subject_action`` is the must-complete core.  Decorative or lower-priority
    clauses that exceed the three-actions-per-five-seconds budget are moved to
    ``optional_flourish``.  The original wording remains inspectable in the
    action_budget metadata instead of disappearing silently.
    """
    result = dict(shot)
    start = float(result.get("start_seconds", 0.0) or 0.0)
    end = float(result.get("end_seconds", start + 0.5) or start + 0.5)
    duration = max(0.5, end - start)
    core_limit = max(
        1,
        int(math.ceil(duration / ACTION_BUDGET_WINDOW_SECONDS * MAX_CORE_ACTIONS_PER_WINDOW)),
    )
    optional_limit = max(
        1,
        int(math.ceil(duration / ACTION_BUDGET_WINDOW_SECONDS * MAX_OPTIONAL_ACTIONS_PER_WINDOW)),
    )
    original_core = str(result.get("subject_action", "")).strip()
    original_environment = str(result.get("environment_response", "")).strip()
    continuity = str(result.get("continuity_state", "")).strip()
    optional_text = str(result.get("optional_flourish", "")).strip()
    raw_core_beats = split_action_beats(original_core)
    bound_core_beats = _bind_action_subjects(raw_core_beats)
    core_beats = _merge_causal_setup_beats(bound_core_beats)
    causal_merge_count = len(raw_core_beats) - len(core_beats)
    optional_beats = split_action_beats(optional_text)
    environment_beats = split_action_beats(original_environment)
    response_limit = max(
        1,
        int(math.ceil(
            duration / ACTION_BUDGET_WINDOW_SECONDS * MAX_REQUIRED_RESPONSES_PER_WINDOW
        )),
    )

    decorative_core = [
        beat
        for beat in core_beats
        if _DECORATIVE_ACTION_RE.search(beat) and not _CRITICAL_ACTION_RE.search(beat)
    ]
    essential_core = [beat for beat in core_beats if beat not in decorative_core]
    demoted: list[str] = list(decorative_core)
    if len(essential_core) > core_limit:
        ranked = sorted(
            range(len(essential_core)),
            key=lambda index: _action_priority(
                essential_core[index], index, len(essential_core)
            ),
            reverse=True,
        )
        keep = {len(essential_core) - 1}
        if core_limit > 1:
            keep.add(0)
        for candidate in ranked:
            if len(keep) >= core_limit:
                break
            keep.add(candidate)
        selected_core = [
            beat for index, beat in enumerate(essential_core) if index in keep
        ]
        demoted.extend(
            beat for index, beat in enumerate(essential_core) if index not in keep
        )
    else:
        selected_core = essential_core

    if len(environment_beats) > response_limit:
        ranked_environment = sorted(
            range(len(environment_beats)),
            key=lambda index: _action_priority(
                environment_beats[index], index, len(environment_beats)
            ),
            reverse=True,
        )
        keep_environment = {len(environment_beats) - 1}
        if response_limit > 1:
            keep_environment.add(0)
        for candidate in ranked_environment:
            if len(keep_environment) >= response_limit:
                break
            keep_environment.add(candidate)
        selected_environment = [
            beat for index, beat in enumerate(environment_beats)
            if index in keep_environment
        ]
        demoted_environment = [
            beat for index, beat in enumerate(environment_beats)
            if index not in keep_environment
        ]
    else:
        selected_environment = environment_beats
        demoted_environment = []

    # A purely decorative legacy action still needs one visible executable beat.
    if not selected_core and core_beats:
        selected_core = [core_beats[0]]
        demoted = [beat for beat in demoted if beat != core_beats[0]]

    core_was_demoted = bool(demoted) or len(essential_core) > core_limit
    demoted.extend(demoted_environment)
    combined_optional = list(dict.fromkeys((*optional_beats, *demoted)))
    executable_optional = combined_optional[:optional_limit]
    status = "within_budget"
    if demoted or len(essential_core) > core_limit or len(raw_core_beats) > core_limit:
        status = "priority_compressed"
    elif len(combined_optional) > optional_limit:
        status = "optional_trimmed"

    result["subject_action"] = (
        original_core
        if selected_core == core_beats and not core_was_demoted and not causal_merge_count
        else _join_action_beats(selected_core)
    )
    result["continuity_state"] = continuity or (
        "Preserve the incoming body positions, exact subject and weapon ownership, "
        "screen direction, velocity and camera trajectory; end on the final physical "
        "state created by the core action."
    )
    result["environment_response"] = (
        original_environment
        if selected_environment == environment_beats
        else _join_action_beats(selected_environment)
    )
    result["optional_flourish"] = (
        optional_text
        if combined_optional == optional_beats
        else _join_action_beats(combined_optional)
    )
    result["h3_executable_action"] = result["subject_action"]
    result["h3_optional_flourish"] = (
        optional_text
        if executable_optional == optional_beats
        else _join_action_beats(executable_optional)
    )
    notes: list[str] = []
    if demoted:
        notes.append(
            f"Demoted {len(demoted)} lower-priority action(s); omit them before delaying the core action."
        )
    if causal_merge_count:
        notes.append(
            f"Merged {causal_merge_count} causal setup beat(s) into the decisive action they enable."
        )
    if demoted_environment:
        notes.append(
            f"Required environment responses were limited to {response_limit} contact consequence(s)."
        )
    if len(combined_optional) > optional_limit:
        notes.append(
            f"Only {optional_limit} optional flourish(s) fit this Shot's duration."
        )
    if start < math.ceil(start / 15.0) * 15.0 < end:
        notes.append(
            "Shot crosses a native 15-second boundary; continuity_state is mandatory on both sides."
        )
    result["action_budget"] = {
        "window_seconds": ACTION_BUDGET_WINDOW_SECONDS,
        "core_action_count": len(raw_core_beats),
        "core_action_limit": core_limit,
        "required_response_count": len(environment_beats),
        "required_response_limit": response_limit,
        "optional_action_count": len(combined_optional),
        "optional_action_limit": optional_limit,
        "status": status,
        "demoted_actions": demoted,
        "notes": " ".join(notes),
        "original_subject_action": original_core,
        "original_environment_response": original_environment,
    }
    return result


def normalize_design_plan(
    payload: object,
    capacities: dict[str, int],
    *,
    existing_media: list[dict] | None = None,
    strict_t2i_prompts: bool = False,
    repair_media_plan: bool = False,
    authored_requirement: str = "",
    special_skill_key: str = "",
    selected_media_ids: list[str] | None = None,
) -> dict:
    media_repair_warnings: list[str] = []
    prepared_payload = deepcopy(extract_design_json(payload))
    authored_duration = infer_explicit_design_duration(authored_requirement)
    if authored_duration is not None:
        returned_duration = snap_half_second(
            prepared_payload.get("duration_seconds", 5.0),
            MAX_DESIGN_DURATION_SECONDS,
        )
        speech_base_duration = float(
            prepared_payload.get("_speech_timing_base_duration", 0.0) or 0.0
        )
        speech_adjusted_duration = bool(
            returned_duration >= authored_duration
            and abs(speech_base_duration - authored_duration) <= 0.01
        )
        if (
            abs(returned_duration - authored_duration) > 0.01
            and not speech_adjusted_duration
        ):
            if repair_media_plan:
                repair_note = _retime_design_payload(
                    prepared_payload, authored_duration
                )
                if repair_note:
                    media_repair_warnings.append(repair_note)
            else:
                raise DesignDurationContractError(
                    "Duration contract mismatch: the user explicitly requested "
                    f"{authored_duration:.2f}s, but Design JSON returned "
                    f"{returned_duration:.2f}s. Do not condense, summarize, stretch or "
                    "inherit the current workspace Timeline duration; regenerate every Shot, "
                    "text layer, cue and media range for the exact requested duration."
                )
    if authored_requirement.strip():
        prepared_payload = protect_explicit_timed_text_layers(
            prepared_payload, authored_requirement
        )
    if repair_media_plan:
        source, repaired_media_warnings = repair_design_media_plan(
            prepared_payload, capacities, existing_media
        )
        media_repair_warnings.extend(repaired_media_warnings)
    else:
        source = prepared_payload
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
        if not repair_media_plan:
            raise ValueError("Design JSON is missing creative_brief")
        plan["creative_brief"] = (
            str(authored_requirement).strip()
            or plan["title"]
            or "Execute the supplied Shot plan as one continuous story."
        )
        media_repair_warnings.append(
            "Inserted a Creative Brief from the authored requirement/title."
        )
    if not plan["global_visual_style"]:
        if not repair_media_plan:
            raise ValueError("Design JSON is missing global_visual_style")
        plan["global_visual_style"] = (
            "Cinematic realism with physically coherent lighting, identity, geography and motion."
        )
        media_repair_warnings.append(
            "Inserted a safe cinematic Visual Style because the model omitted it."
        )
    plan["overall_soundscape"] = automatic_background_soundscape({
        **plan,
        "shots": source.get("shots") or [],
    })
    plan["non_diegetic_music"] = automatic_background_music({
        **plan,
        "shots": source.get("shots") or [],
    })
    budget_guardrail = (
        "Complete every Shot's core action before any optional flourish. Preserve the stated "
        "continuity state, exact subject count and identity, prop and weapon ownership, screen "
        "direction, geography and momentum. Omit optional decoration whenever it would delay "
        "a core action. No replay, neutral reset, teleportation, duplicated subjects or morphing props."
    )
    if not plan["constraints"]:
        plan["constraints"] = budget_guardrail
    elif "optional flourish" not in plan["constraints"].lower():
        plan["constraints"] = plan["constraints"].rstrip(" .") + ". " + budget_guardrail

    design_warnings: list[str] = list(media_repair_warnings)
    shots: list[dict] = []
    for index, raw in enumerate(source.get("shots") or [], 1):
        if not isinstance(raw, dict):
            continue
        start, end = _interval(raw, duration)
        prior_budget = raw.get("action_budget") if isinstance(raw.get("action_budget"), dict) else {}
        authored_subject_action = str(
            prior_budget.get("original_subject_action") or raw.get("subject_action", "")
        ).strip()
        authored_environment_response = str(
            prior_budget.get("original_environment_response")
            or raw.get("environment_response", "")
        ).strip()
        shots.append({
            "start_seconds": start,
            "end_seconds": end,
            "track": str(raw.get("track", "V1")).strip() or "V1",
            "preset": str(raw.get("preset", "Product Demonstration")).strip(),
            "framing": str(raw.get("framing", "Medium-wide")).strip(),
            "camera_angle": str(raw.get("camera_angle", "Eye level")).strip(),
            "camera_movement": str(raw.get("camera_movement", "Static")).strip(),
            "movement_speed": str(raw.get("movement_speed", "Slow")).strip(),
            "movement_amplitude": str(raw.get("movement_amplitude", "Small")).strip(),
            "subject_action": authored_subject_action,
            "environment_response": authored_environment_response,
            "continuity_state": str(raw.get("continuity_state", "")).strip(),
            "optional_flourish": str(raw.get("optional_flourish", "")).strip(),
            "additional_direction": str(raw.get("additional_direction", "")).strip(),
        })
    if not shots:
        raise ValueError("Design JSON must contain at least one shot")
    plan["shots"] = sorted(shots, key=lambda item: (item["start_seconds"], item["end_seconds"]))
    _repair_overlapping_camera_shots(plan["shots"], duration, design_warnings)
    for index, shot in enumerate(plan["shots"], 1):
        shot["id"] = f"S{index}"
        if not shot["subject_action"]:
            shot["subject_action"] = (
                "Continue the established physical motion and finish on the stated continuity state."
            )
            design_warnings.append(
                f"S{index} had no core action; inserted a continuity-only executable action."
            )
        if index == 1 and shot["start_seconds"] > 0.0:
            design_warnings.append(
                f"Timeline has no structured Shot from 0.00s to {shot['start_seconds']:.2f}s."
            )
        if index > 1:
            previous = plan["shots"][index - 2]
            if shot["start_seconds"] < previous["end_seconds"] - 1e-6:
                raise ValueError(
                    f"Shot {previous['id']} still overlaps S{index} after automatic boundary repair. "
                    "H3 camera Shots must be chronological and non-overlapping; use overlapping "
                    "V tracks only for media layers."
                )
            if shot["start_seconds"] > previous["end_seconds"] + 1e-6:
                design_warnings.append(
                    f"Timeline has no structured Shot from {previous['end_seconds']:.2f}s "
                    f"to {shot['start_seconds']:.2f}s."
                )
    if plan["shots"][-1]["end_seconds"] < duration - 1e-6:
        design_warnings.append(
            f"Timeline has no structured Shot from {plan['shots'][-1]['end_seconds']:.2f}s "
            f"to {duration:.2f}s."
        )

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
        content = str(raw.get("content", "")).strip()
        language = str(raw.get("language", "English")).strip() or "English"
        if re.search(r"[\u3400-\u9fff]", content) and language.lower() in {
            "english", "original language", "auto",
        }:
            language = "Mandarin Chinese"
        normalized_layer = {
            "start_seconds": start,
            "end_seconds": end,
            "track": track,
            "content": content,
            "role": role,
            "speaker": str(raw.get("speaker", "S1")) if str(raw.get("speaker", "S1")) in {"S1", "S2"} else "S1",
            "language": language,
            "delivery": str(raw.get("delivery", "Natural")).strip() or "Natural",
            "lip_sync": role == "dialogue" and bool(raw.get("lip_sync", False)),
            "explicit_user_requested": True,
        }
        for metadata_key in (
            "authored_start_seconds", "authored_end_seconds",
            "speech_timing_auto_adjusted", "speech_budget_was_overloaded",
            "speech_budget", "authored_timing_locked",
        ):
            if metadata_key in raw:
                normalized_layer[metadata_key] = deepcopy(raw[metadata_key])
        text_layers.append(normalized_layer)
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
        if not inventory_was_supplied and ordinal > int(capacities.get(media_type, 0)):
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
            raw.get("requirement_id"), f"reuse_{media_id.lower()}_{use_number}"
        )
        if requirement_id in reused_requirement_ids:
            raise ValueError(
                f"Existing media requirement_id {requirement_id!r} is used more than once."
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
        keywords = _string_list(raw.get("subject_keywords") or [])
        fallback_instruction = ""
        if inventory_row:
            fallback_instruction = str(
                inventory_row.get("clip_prompt")
                or inventory_row.get("caption")
                or inventory_row.get("analysis_summary")
                or ""
            ).strip()
        raw_usage = str(raw.get("usage", "h3_reference")).strip().casefold()
        normalized_use = {
            "requirement_id": requirement_id,
            "media_id": media_id,
            "media_type": media_type,
            "usage": (
                "analysis_only"
                if raw_usage in ANALYSIS_ONLY_MEDIA_USAGES
                else raw_usage
                if raw_usage in {"h3_reference", "timeline_visual"}
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
        }
        if "identity_anchor" in raw:
            normalized_use["identity_anchor"] = bool(raw.get("identity_anchor"))
        existing_media_uses.append(normalized_use)
        reused_requirement_ids.add(requirement_id)

    for media_id in _authored_identity_picture_ids(authored_requirement):
        inventory_row = inventory.get(media_id)
        if inventory_was_supplied and not bool(
            inventory_row and inventory_row.get("loaded", False)
        ):
            # Existing validation will give the actionable missing/empty error
            # when the model emitted the use.  Do not manufacture a valid row
            # for an absent Picture here.
            continue
        identity_use = next(
            (row for row in existing_media_uses if row.get("media_id") == media_id),
            None,
        )
        if identity_use is None:
            requirement_id = _normalized_requirement_id(
                f"authored_identity_{media_id.lower()}",
                f"authored_identity_{media_id.lower()}",
            )
            suffix = 2
            while requirement_id in reused_requirement_ids:
                requirement_id = f"authored_identity_{media_id.lower()}_{suffix}"
                suffix += 1
            fallback_instruction = ""
            if inventory_row:
                fallback_instruction = str(
                    inventory_row.get("clip_prompt")
                    or inventory_row.get("caption")
                    or inventory_row.get("analysis_summary")
                    or ""
                ).strip()
            identity_use = {
                "requirement_id": requirement_id,
                "media_id": media_id,
                "media_type": "image",
                "usage": "h3_reference",
                "reuse_policy": "whole_design",
                "start_seconds": 0.0,
                "end_seconds": duration,
                "track": "V1",
                "subject_keywords": [],
                "instruction": fallback_instruction,
            }
            existing_media_uses.append(identity_use)
            reused_requirement_ids.add(requirement_id)
        identity_use["identity_anchor"] = True
        identity_use["reuse_policy"] = "whole_design"
        identity_use["start_seconds"] = 0.0
        identity_use["end_seconds"] = duration
        identity_contract = (
            f"Use @{media_id} as the authoritative whole-design face identity anchor. "
            "Preserve the exact recognizable facial geometry, age, hair and identity in every appearance."
        )
        if identity_contract not in str(identity_use.get("instruction", "")):
            identity_use["instruction"] = (
                str(identity_use.get("instruction", "")).rstrip(" .")
                + (". " if str(identity_use.get("instruction", "")).strip() else "")
                + identity_contract
            )
    plan["existing_media_uses"] = existing_media_uses
    reused_media_ids = sorted({
        row["media_id"] for row in existing_media_uses
        if not is_analysis_only_media_use(row)
    })
    if reused_media_ids:
        for field_name in (
            "creative_brief", "global_visual_style", "overall_soundscape",
            "non_diegetic_music", "constraints",
        ):
            plan[field_name] = _canonicalize_design_media_mentions(
                plan.get(field_name, ""), reused_media_ids
            )
        for row in plan.get("shots") or []:
            for field_name in (
                "framing", "camera_angle", "camera_movement", "subject_action",
                "environment_response", "continuity_state", "optional_flourish",
                "additional_direction",
            ):
                row[field_name] = _canonicalize_design_media_mentions(
                    row.get(field_name, ""), reused_media_ids
                )
        for row in plan.get("transitions") or []:
            row["direction"] = _canonicalize_design_media_mentions(
                row.get("direction", ""), reused_media_ids
            )
        for row in plan.get("markers") or []:
            row["direction"] = _canonicalize_design_media_mentions(
                row.get("direction", ""), reused_media_ids
            )
        for row in existing_media_uses:
            row["instruction"] = _canonicalize_design_media_mentions(
                row.get("instruction", ""), reused_media_ids
            )

    analysis_only_ids = sorted({
        row["media_id"] for row in existing_media_uses
        if is_analysis_only_media_use(row)
    })
    if analysis_only_ids:
        for field_name in (
            "creative_brief", "global_visual_style", "overall_soundscape",
            "non_diegetic_music", "constraints",
        ):
            plan[field_name] = _remove_control_artifact_priming(
                _replace_analysis_only_media_mentions(
                    plan.get(field_name, ""), analysis_only_ids
                )
            )
        for row in plan.get("shots") or []:
            for field_name in (
                "framing", "camera_angle", "camera_movement", "subject_action",
                "environment_response", "continuity_state", "optional_flourish",
                "additional_direction",
            ):
                row[field_name] = _remove_control_artifact_priming(
                    _replace_analysis_only_media_mentions(
                        row.get(field_name, ""), analysis_only_ids
                    )
                )
        for family in ("transitions", "markers"):
            for row in plan.get(family) or []:
                row["direction"] = _remove_control_artifact_priming(
                    _replace_analysis_only_media_mentions(
                        row.get("direction", ""), analysis_only_ids
                    )
                )
        clean_frame_contract = (
            "Keep the photoreal scene clean and unobstructed; all planning controls remain "
            "non-visual and entirely off-screen."
        )
        if clean_frame_contract not in plan["constraints"]:
            plan["constraints"] = (
                plan["constraints"].rstrip(" .")
                + (". " if plan["constraints"].strip() else "")
                + clean_frame_contract
            )
        design_warnings.append(
            "Analysis-only Media Pool control sources "
            + ", ".join(analysis_only_ids)
            + " were retained for planning but removed from all H3-renderable prose and reference slots."
        )

    budgeted_shots: list[dict] = []
    for shot in plan["shots"]:
        budgeted = normalize_shot_action_budget(shot)
        budget = budgeted["action_budget"]
        if budget["status"] != "within_budget":
            design_warnings.append(
                f"{budgeted['id']} {budget['status']}: {budget['notes']}"
            )
        budgeted_shots.append(budgeted)
    plan["shots"] = budgeted_shots
    plan["design_warnings"] = design_warnings

    media_requests: list[dict] = []
    counts = {"image": 0, "video": 0, "audio": 0}
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
        # The Media Pool is logical and unlimited.  Physical 9/3/3 H3 slots
        # are allocated dynamically per Segment during compilation; total
        # project request count must never be compared with physical capacity.
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
        if analysis_only_ids:
            prompt = _remove_control_artifact_priming(
                _replace_analysis_only_media_mentions(prompt, analysis_only_ids)
            )
        if media_type == "image" and strict_t2i_prompts:
            _validate_t2i_media_prompt(
                prompt,
                request_number=request_number,
                start_seconds=start,
                end_seconds=end,
                duration_seconds=duration,
            )
        keywords = _string_list(raw.get("subject_keywords") or [])
        if analysis_only_ids:
            keywords = [
                _remove_control_artifact_priming(
                    _replace_analysis_only_media_mentions(value, analysis_only_ids)
                )
                for value in keywords
            ]
        normalized_request = {
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
        }
        for metadata_key in (
            "identity_anchor", "identity_anchor_requirement_id", "identity_anchor_media_id",
        ):
            if metadata_key in raw:
                normalized_request[metadata_key] = deepcopy(raw[metadata_key])
        preferred_media_id = _normalized_media_id(raw.get("preferred_media_id", ""))
        if media_type == "image" and preferred_media_id.startswith("P"):
            preferred_row = inventory.get(preferred_media_id)
            if (
                not bool(preferred_row and preferred_row.get("loaded", False))
            ):
                normalized_request["preferred_media_id"] = preferred_media_id
        media_requests.append(normalized_request)
        requested_requirement_ids.add(requirement_id)
    plan["media_requests"] = media_requests
    if "_speech_timing_base_duration" in source:
        plan["_speech_timing_base_duration"] = float(
            source.get("_speech_timing_base_duration", duration)
        )
    if str(special_skill_key).strip().casefold() == "drone-fly-on-city":
        enforce_drone_scene_keyframe_chain(
            plan, existing_media, selected_media_ids=selected_media_ids
        )
    if str(special_skill_key).strip().casefold() == "dark-rescue-h3":
        enforce_dark_rescue_first_person(plan)
    stabilize_generated_identity_references(plan)
    return auto_adjust_speech_shot_timing(plan)


def build_design_system_prompt(context: dict) -> str:
    bound_skills = context.get("bound_h3_skills") or {}
    if bound_skills.get("binding_mode") == "standalone_special":
        skill_direction = (
            "The selected standalone Special skill in the workspace context is authoritative. "
            "Apply only that skill's planning, continuity, reference, shot, audio and technical rules. "
            "Do not merge or infer rules from the Default H3 skill; it is intentionally absent from this Design request. "
        )
    else:
        skill_direction = (
            "The bound Default H3 skill and optional Special skill in the workspace context are authoritative. "
            "Apply their planning, continuity, reference-retention, shot, audio and technical rules while producing the JSON. "
        )
    requested_duration = context.get("requested_duration_seconds")
    duration_contract = ""
    if requested_duration is not None:
        duration_contract = (
            f"DURATION CONTRACT: The user explicitly requested exactly {float(requested_duration):.2f} seconds. "
            f"Set duration_seconds to {float(requested_duration):.2f}; preserve all authored timecodes through that "
            "final timestamp. Never condense, summarize, stretch or replace this duration with "
            "current_duration_seconds from the workspace. The current Timeline duration is context only. "
        )
    selected_dialogue_language = canonical_dialogue_language(
        context.get("dialogue_language")
    )
    language_contract = (
        "H3 has stable native dialogue support for exactly 11 languages: "
        + ", ".join(H3_STABLE_DIALOGUE_LANGUAGES)
        + ". "
    )
    if selected_dialogue_language and selected_dialogue_language != "auto":
        language_contract += (
            "DIALOGUE LANGUAGE CONTRACT: Design selected "
            f"{selected_dialogue_language}. Write every newly authored Dialogue, Voice-over "
            f"and Lyrics line naturally in {selected_dialogue_language}, and set every matching "
            f"text_layers.language value to exactly '{selected_dialogue_language}'. Never default "
            "to English and never place English words under a non-English language label. Exact "
            "verbatim words supplied by the user remain authoritative and must not be translated. "
        )
    subtitles_enabled = bool(context.get("subtitles_enabled", False))
    subtitle_contract = (
        "SUBTITLE CONTRACT: subtitles are ON. Keep all speech in editable audio text_layers "
        "and also create synchronized on_screen_text subtitle layers with the same exact words. "
        "Do not burn subtitles into generated reference images. "
        if subtitles_enabled else
        "SUBTITLE CONTRACT: subtitles are OFF. Do not create subtitle/caption on_screen_text "
        "layers, do not invent theme hashtags, and never ask generated reference images to show "
        "spoken words. Explicit non-subtitle title or on-screen text requested by the user is the "
        "only visible text exception. "
    )
    music_mode = normalize_design_music_mode(context.get("music_mode", "auto"))
    if music_mode == "off":
        music_contract = (
            "MUSIC POLICY: OFF. Set non_diegetic_music to exactly 'N/A', do not create Music Cue "
            "markers, and rely only on diegetic ambience, Foley and authored speech. "
        )
    elif music_mode == "timeline":
        music_contract = (
            "MUSIC POLICY: TIMELINE. Set non_diegetic_music to exactly 'N/A' and do not invent "
            "automatic score or Music Cue markers. Music will be enabled later only where the user "
            "authors a Timeline Music Cue. "
        )
    else:
        music_contract = (
            "MUSIC POLICY: AUTO. Analyse every scene's genre, emotion, pacing and transitions, then "
            "write a useful time-aware non_diegetic_music direction with suitable instrumentation "
            "and dramatic development. Keep it subordinate to speech and important diegetic sound, "
            "let it rise naturally between spoken lines, and use no vocals unless authored Lyrics "
            "explicitly require them. "
        )
    return (
        "You are the AI Design Planner inside a MiniMax H3 Director Cut application. "
        "Convert the user's concept into one production-ready JSON object that exactly matches the supplied schema. "
        + skill_direction
        + duration_contract
        + language_contract
        + subtitle_contract
        + music_contract
        + "the application will compile this JSON into the final H3 Ref2VA prompt. "
        "Use 0.5-second boundaries. Build chronological Shot Blocks with explicit framing, camera angle, camera movement, "
        "subject action, environmental response, continuity state, optional flourish and additional direction. "
        "Treat subject_action as the must-complete physical core only. Put the exact incoming and outgoing body pose, "
        "subject and weapon ownership, velocity, screen direction, geography and camera trajectory in continuity_state. "
        "In every multi-character action clause, repeat the explicit character name or role before its verb and weapon. "
        "Do not rely on he, she, they, his or her across action beats: action-budget compression must never transfer an "
        "attack, escape, landing or weapon from one character to another. "
        "Put leaves, sparks, dust, cloth motion, secondary feints, ornamental camera moves and other dispensable detail in "
        "optional_flourish. Keep contact-driven consequences that are necessary for causality in environment_response, not "
        "in optional_flourish. For every five seconds, budget at most three must-complete physical action beats, two required "
        "contact consequences and two optional flourishes. If a draft exceeds that budget, first split it into consecutive non-overlapping Shot Blocks "
        "on 0.5-second boundaries when the timeline has enough time; otherwise demote secondary beats to optional_flourish "
        "and rewrite subject_action as a concise causal chain that H3 can fully complete. Never label more actions mandatory "
        "than the duration can render. Reserve the last 0.5 to 1.0 second before every native 15-second boundary for one "
        "simple outgoing state; do not introduce a new multi-beat technique there. Shots must be chronological and must not "
        "overlap; editorial V tracks may overlap for reference/compositing media, but simultaneous conflicting camera Shots may not. "
        "The Shot lane must cover every frame from 0.00 through duration_seconds exactly once, with no gap and no overlap. "
        "If speech timing lengthens the project, extend its owning Shot and ripple every later Shot, text layer, cue and media range; "
        "never create a tail Segment that contains speech but no Shot. Do not compress several unrelated locations or editorial cuts "
        "into one Shot: a private aircraft, hotel floor and cinema, for example, require separate chronological Shot Blocks even when "
        "one voice-over sentence describes all three. "
        "Timeline tracks are editorial lanes, not the physical H3 reference-slot count. You may plan V4, V5 and higher "
        "visual lanes for overlapping action states, titles or compositing, and A4, A5 and higher audio lanes for dialogue, "
        "voice-over, lyrics, ambience or music stems; the Studio creates those tracks automatically. Keep on-screen text on "
        "a V track and place dialogue, voice-over and lyrics on A tracks. "
        "An editorial A-track label such as A1 is not proof that an Audio asset exists. When the user supplies authored "
        "Dialogue, Voice-over or Lyrics without an explicitly loaded @A reference, put the exact words in text_layers only; "
        "never invent A1 in existing_media_uses and never create a placeholder speech-audio request. The application reserves "
        "the generated TTS Audio slot after validation. "
        "The Media Pool is virtual and may contain unlimited logical P/A/V sources. The renderer dynamically loads only the "
        "temporally relevant sources into physical H3 slots for each native Segment. Never exceed the supplied "
        "physical_segment_capacity (normally 9 images, 3 videos and 3 audios) within any one Segment, even though the whole "
        "project may use P10+, V4+ and A4+. Additional editorial tracks do not increase that per-Segment limit. "
        "Never treat P9, V3 or A3 as a project-wide stopping point. Continue assigning stable logical IDs P10+, V4+ and A4+ when "
        "new story needs occur later in the Timeline; capacity is validated only among references whose time ranges overlap the same Segment. "
        "Before requesting any new material, audit the loaded existing_media inventory in the workspace context. The user may "
        "refer to its stable Media Pool IDs as @P1, @P2, @V1 or @A1; write the ID without @ in existing_media_uses.media_id. "
        "Inside creative_brief, Shot subject_action, environment_response, additional_direction, marker direction and every other "
        "authored instruction, always cite an existing Media Pool source with its stable @P/@V/@A ID, for example @P4. Never write "
        "a raw <Picture N>, <Video N> or <Audio N> token in authored Design JSON: those angle-bracket tags are request-local H3 "
        "ordinals assigned only when the Studio compiles one render segment, and their numbers can change between segments. "
        "Reuse only loaded assets that genuinely satisfy the story requirement, and never invent an ID, select an empty slot, "
        "or force every existing asset into the design. Give every logical media need a concise stable requirement_id. "
        "Treat each asset's caption, clip_prompt and analysis_summary as the evidence for its content, including video-frame "
        "captions, beat/VAD and transcript observations. If analysis_status is pending or the evidence is ambiguous, do not "
        "invent unseen people, objects, speech or actions; use a neutral preserve-the-supplied-asset instruction instead. "
        "When a loaded asset satisfies that need, put it in existing_media_uses and do not emit a media_request with the same "
        "requirement_id. existing_media_uses instructions describe how H3 should preserve or use the supplied asset; they do not "
        "ask Z-Image to regenerate it. Use reuse_policy=whole_design for identity, product, wardrobe, environment or audio references "
        "needed throughout the story, and reuse_policy=time_scoped for one contiguous action or editorial interval. The same "
        "Media Pool asset may appear in multiple existing_media_uses rows when it returns in separate non-contiguous intervals; "
        "give every occurrence a unique requirement_id, exact range, track and instruction. Do not widen across an interval where "
        "the reference should be inactive. Repeated uses share one physical H3 reference slot. "
        "When a loaded image is only a map, route drawing, mask, depth guide, annotation or other planning control, set its "
        "existing_media_uses.usage to analysis_only (route_control_analysis_only is accepted as a compatibility alias). The "
        "application exposes its analysed information to Design but never places it on the Timeline, counts it against an "
        "H3 Segment reference slot, or uploads it to MiniMax H3. Never cite that control asset ID or its visible graphics in "
        "Shot prose; describe only the abstract motion or staging extracted from it. "
        "media_requests must contain only genuinely missing assets after this reuse audit. Choose that missing count dynamically from "
        "the concept and the time-local Segment budget; never duplicate a requirement already fulfilled by @P1/@V1/@A1. "
        "For media_requests, use h3_reference when an asset supplies subject, product, wardrobe, environment or composition guidance; "
        "use timeline_visual only when the user explicitly asks to composite the literal file into the editorial preview. "
        "Plan reference media dynamically from the story: reusable identity and environment references are valid, and time-scoped "
        "composition, action-state or boundary-continuity references are also valid when they reduce ambiguity between story phases. "
        "Choose the useful count and exact timeline ranges yourself. Never force one image per Shot, never fill all available slots merely "
        "because they exist, and never make redundant copies; distinct temporal states of the same subject are allowed when they prevent "
        "a later segment from replaying an earlier action. Do not return zero image references when the plan has visual Shots and empty "
        "Picture capacity. As a coverage floor, provide approximately one useful image state per five seconds, never more than one per "
        "Shot, while counting genuinely reused Picture assets toward that floor and staying within the per-Segment physical capacity. "
        "For a recurring human character, designate one clear face-bearing Picture as the whole-design identity anchor. A user-supplied "
        "Media Pool Picture explicitly cited for face or identity consistency is always authoritative and must win over every generated "
        "Picture. Later generated Pictures are environment, prop or action-state support and must not redefine a competing face. When the "
        "authoritative face comes from existing media, keep faces fully out of frame, turned away, motion-obscured or otherwise unreadable "
        "in independent T2I support requests; H3 must derive the recognizable face only from that existing Picture. "
        "Before planning references, build an exact cast ledger. Every Shot and every person-bearing image request must state the exact "
        "number and identity of visible people. A one-person identity reference must show exactly that one foreground person with no crowd, "
        "staff, silhouette, reflection, portrait, mannequin, double or background figure. A two-person conversation must show exactly the "
        "two named speakers and no duplicate or third person. Secondary characters require their own distinct identity reference and must "
        "never inherit or blend with the primary character anchor. Environment and prop references must contain no visible people unless the "
        "Shot explicitly needs them. Only recurring identity references may span the whole design; scope environment, location, montage and "
        "action-state references to the exact Shots where they are needed so an earlier airport, hotel, computer or other scene cannot leak "
        "into a later Segment. "
        "For every identity-anchored character, keep face, age, skin tone, hairstyle, hair color, body proportions, complete top and lower-body "
        "wardrobe, shoes and accessory ownership fixed by default. Expressions, poses, arm/leg angles, gait phase and physically caused hair or "
        "cloth motion may vary freely. Wardrobe or hairstyle changes, injury, dirt, damage, shoe removal and accessory loss may occur only when "
        "the story explicitly authors the trigger in a Shot; write the changed outgoing state and carry it into every later incoming continuity "
        "state until another explicit story change. Never invent an unrequested appearance reset between Shots or Segments. "
        "Every image media_request sent to Z-Image/T2I must contain a complete standalone visual prompt. Never put an H3 <Picture N> "
        "token in a T2I prompt and never ask it to copy, match, continue from or depend on a previous, current/self, next/future, generated "
        "or output image; those H3 slots do not exist when reference images are generated. Restate all required identity, appearance, wardrobe, "
        "prop, action, composition, lighting and environment facts directly inside each image prompt. "
        "An action-state image must depict exactly one frozen instant: one body position per character and one physically "
        "consistent weapon state. Never describe a temporal montage, several sequential moves, repeated poses, duplicate fighters, "
        "afterimages that resemble extra people, or both the setup and the later outcome in the same still. "
        "For every time-scoped action-state or segment-boundary reference, stage the requested moment inside the story's exact real in-world "
        "location with its recognizable geography and lighting; never use a neutral, blank, plain, isolated or studio background for those "
        "action/boundary images. First infer and preserve an exact character/prop ownership ledger from the story: name which character wears "
        "or holds each item in every affected prompt, keep counts exact, and never swap, duplicate or transfer ownership unless the story "
        "explicitly performs that transfer. "
        "During a BLIP-backed refinement pass, use BLIP only as visual QA. Compare each caption against the intended identity, character/prop "
        "ownership, counts, action state and in-world environment. If BLIP conflicts on any of those facts, reject that generated reference "
        "and replan the affected media_request with a corrected standalone prompt for regeneration; never alter the story or ownership ledger "
        "to agree with an incorrect BLIP observation, and never approve the conflicting image as an H3 reference. "
        "When the user asks for Dialogue, Voice-over, narration or Lyrics, create editable text_layers for every spoken line, set "
        "explicit_user_requested=true, and keep the spoken words exclusively in those text_layers. Never hide, quote or paraphrase spoken "
        "words inside Shot subject_action, environment_response, continuity_state, optional_flourish or additional_direction. "
        "Budget spoken language before fixing Shot boundaries: use a natural conversational rate, give emotional or hesitant "
        "delivery extra time, and lengthen the owning Shot instead of compressing exact dialogue. If a line cannot fit, shift "
        "all later Shots, text layers, cues and media ranges together; never solve overload by speaking early, reordering, "
        "omitting or paraphrasing authored words. "
        "Only create a text_layer or theme_text when the user explicitly requests visible text, dialogue, voice-over or lyrics, and set "
        "explicit_user_requested=true only in that case. Never turn the creative brief or scene description into on-screen text. "
        "For every dialogue text_layer, infer the gender of the speaking on-screen character from the user's story, Shot action and "
        "reference-media evidence. Assign S1 to a female speaker and S2 to a male speaker, keep the assignment consistent across every "
        "Shot, and never use the narrator's gender when the visible character is speaking. If the user explicitly writes S1 or S2, "
        "preserve that explicit assignment. Put the intended emotion and pace in delivery without changing the authored words. "
        "Always design a useful overall_soundscape with three audible layers: continuous diegetic location ambience, exact-frame "
        "contact-synchronized Foley/one-shot SFX, and foreground speech. On-screen Dialogue must sound like live production audio "
        "captured in the visible location, with natural breath, conversational micro-pauses, camera-distance perspective, subtle room "
        "or outdoor reflections and low environmental bleed; never request a dry announcer or studio voice-over performance. Infer a "
        "time-scoped acoustic profile from every visible Shot: short bright decay for small furnished rooms, moderate diffuse decay for "
        "ordinary interiors, longer controlled tails for large halls, directional returns for corridors/caves, very short roof/surface "
        "reflections for covered semi-outdoor spaces, and almost no reverb with reduced low-mid fullness for open exteriors. Never carry "
        "a previous room's tail across a location change. Keep "
        "dialogue in the foreground, duck ambience beneath speech without muting it, and never replace or echo authored dialogue. "
        "Always include a Final Hold marker before the final frame; cue timestamps must be earlier than duration_seconds. "
        "Never leave constraints blank. It must explicitly state that core actions and continuity states outrank optional "
        "flourishes, and that optional detail is dropped before a Shot is delayed or replayed. The Final Hold must resolve "
        "the last Shot's outgoing physical state rather than introduce a new action. "
        "Media requests are reference requirements, not final generated media. "
        "Keep exact product/subject continuity, realistic object interaction and H3-friendly concise directions. "
        "OUTPUT SIZE CONTRACT: Return one compact but complete JSON object. Do not repeat the same prose across fields, "
        "do not add indentation for readability, and keep directions concise while preserving every required Shot, "
        "text layer, continuity state and media range. Close every string, array and object. "
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
    plan: dict,
    example_root: Path,
    ffmpeg: Path,
    *,
    design_dir: Path | None = None,
    media_dir: Path | None = None,
    audio_dir: Path | None = None,
) -> tuple[Path, list[dict]]:
    if design_dir is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        design_dir = example_root / f"{_slug(plan.get('title', ''), 'ai_design')}_{stamp}"
        design_dir.mkdir(parents=True, exist_ok=False)
    else:
        design_dir = Path(design_dir)
        design_dir.mkdir(parents=True, exist_ok=False)
    media_output_dir = Path(media_dir) if media_dir is not None else design_dir
    audio_output_dir = Path(audio_dir) if audio_dir is not None else media_output_dir
    media_output_dir.mkdir(parents=True, exist_ok=True)
    audio_output_dir.mkdir(parents=True, exist_ok=True)
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
            output = media_output_dir / f"{stem}.png"
            _slate(output, request, plan["title"])
            preview_path = output
        elif media_type == "video":
            slate = media_output_dir / f"{stem}_source.png"
            output = media_output_dir / f"{stem}.mp4"
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
            output = audio_output_dir / f"{stem}.wav"
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

"""Portable H3 Director Project integrity repairs.

The repair is deliberately data-only so it can run both during Project load
and from the command line when a clean, rerender-ready JSON is required.
"""

from __future__ import annotations

from copy import deepcopy
import argparse
import json
import math
from pathlib import Path
import re
from typing import Any


SPEECH_ROLES = {"dialogue", "voice_over", "lyrics"}
SAFE_CJK_CHARACTERS_PER_SECOND = 3.6
SAFE_LATIN_WORDS_PER_SECOND = 2.4
FINAL_SPEECH_TAIL_SECONDS = 1.5
NATIVE_SPEECH_RELEASE_GAP_SECONDS = 1.0

_GENERATED_IDENTITY_PREFIX = (
    "PRIMARY RECURRING CHARACTER IDENTITY ANCHOR. Show one clear, unobstructed, "
    "recognizable face with exact age range, facial structure, hair, skin tone, wardrobe "
    "and owned props suitable for reuse through the full story. "
)

_REFERENCE_AUGMENTATION_MARKERS = (
    "SUPPORTING ENVIRONMENT OR ACTION-STATE REFERENCE ONLY",
    "DISTINCT SECONDARY CHARACTER REFERENCE ONLY",
    "DISTINCT SECONDARY CHARACTER IDENTITY",
    "CHARACTER CONTINUITY CONTRACT",
    "EXACT SUBJECT COUNT LOCK:",
    "ENVIRONMENT-ONLY COUNT LOCK:",
    "REFERENCE PERSON COUNT CONTRACT:",
)


def _number(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def _speech_required_seconds(row: dict) -> float:
    """Conservative native-H3 speech budget used while repairing old Projects."""
    text = " ".join(str(row.get("text", row.get("content", "")) or "").split())
    if not text:
        return 0.0
    language = str(row.get("language", "")).lower()
    delivery = str(row.get("delivery", "")).lower()
    cjk_count = len(re.findall(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]", text))
    latin_words = len(re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?", text))
    is_cjk = bool(cjk_count) or any(
        token in language
        for token in ("chinese", "mandarin", "japanese", "korean", "中文", "普通话")
    )
    pace = 1.0
    if re.search(r"fast|rapid|urgent|agitated|angry|激动|急促|快速", delivery):
        pace = 1.16
    elif re.search(
        r"slow|tearful|hesitant|whisper|controlled|emotional|低声|哭|迟疑|缓慢",
        delivery,
    ):
        pace = 0.86
    if is_cjk:
        units = cjk_count + latin_words * 2.0
        base = units / max(0.1, SAFE_CJK_CHARACTERS_PER_SECOND * pace)
    else:
        words = max(latin_words, len(text.split()))
        base = words / max(0.1, SAFE_LATIN_WORDS_PER_SECOND * pace)
    pauses = (
        len(re.findall(r"[,，、;；:]", text)) * 0.10
        + len(re.findall(r"[.!?。！？]", text)) * 0.22
        + len(re.findall(r"…|\.\.\.", text)) * 0.32
    )
    return max(0.5, math.ceil((base + pauses) * 2.0) / 2.0)


def _shift_timed_row(row: dict, boundary: float, delta: float) -> None:
    start = _number(row.get("start_seconds"))
    end = _number(row.get("end_seconds"), start)
    if start >= boundary - 1e-9:
        row["start_seconds"] = round(start + delta, 6)
        row["end_seconds"] = round(end + delta, 6)
    elif end > boundary + 1e-9:
        row["end_seconds"] = round(end + delta, 6)


def _repair_native_speech_timing(
    payload: dict,
    shots: list[dict],
    report: list[str],
) -> float:
    """Ripple unsafe speech and reserve a real tail at the Project endpoint."""
    duration = max(0.5, _number(payload.get("timeline_duration_seconds"), 0.5))
    initial_duration = duration
    layers = [
        row for row in (payload.get("text_layers") or [])
        if isinstance(row, dict)
        and str(row.get("content_role", row.get("role", ""))).lower() in SPEECH_ROLES
        and str(row.get("text", row.get("content", ""))).strip()
    ]
    assets = payload.get("assets") or {}
    asset_rows = list(assets.values()) if isinstance(assets, dict) else []
    clip_rows = [row for row in (payload.get("timeline_clips") or []) if isinstance(row, dict)]
    authored_rows = [
        row for row in (payload.get("authored_text_requirements") or [])
        if isinstance(row, dict)
    ]
    cues = [row for row in (payload.get("director_cues") or []) if isinstance(row, dict)]

    for layer in sorted(
        layers,
        key=lambda row: (_number(row.get("start_seconds")), _number(row.get("end_seconds"))),
    ):
        text = str(layer.get("text", layer.get("content", "")))
        language = str(layer.get("language", ""))
        if re.search(r"[\u3400-\u9fff]", text) and (
            not re.search(
                r"chinese|mandarin|cantonese|中文|普通话|广东话|廣東話",
                language,
                re.I,
            )
            or language.strip().casefold() in {"chinese", "中文"}
        ):
            layer["language"] = "Mandarin Chinese"
            report.append(
                f"Corrected {layer.get('layer_id', 'Text Layer')} language from "
                f"{language or 'unspecified'} to Mandarin Chinese."
            )
        original_voice_gender = str(layer.get("voice_gender", "auto")).strip().casefold()
        voice_gender = original_voice_gender
        if voice_gender not in {"male", "female"}:
            delivery = str(layer.get("delivery", "")).casefold()
            if re.search(r"\b(?:male|man|boy)\b|男声|男聲|男性", delivery):
                voice_gender = "male"
            elif re.search(r"\b(?:female|woman|girl)\b|女声|女聲|女性", delivery):
                voice_gender = "female"
            else:
                voice_gender = "auto"
        layer["voice_gender"] = voice_gender
        if voice_gender != original_voice_gender:
            report.append(
                f"Set {layer.get('layer_id', 'Text Layer')} voice gender to {voice_gender} "
                "from its authored delivery direction."
            )
        start = _number(layer.get("start_seconds"))
        end = _number(layer.get("end_seconds"), start)
        required = _speech_required_seconds(layer)
        allocated = max(0.0, end - start)
        if required <= allocated + 1e-6:
            continue
        delta = math.ceil((required - allocated) * 2.0) / 2.0
        owner = _shot_owner(shots, start, end)
        layer["end_seconds"] = round(end + delta, 6)
        layer["speech_timing_auto_adjusted"] = True
        for other in layers:
            if other is not layer:
                _shift_timed_row(other, end, delta)
        for cue in cues:
            if cue is owner:
                cue["end_seconds"] = round(
                    max(_number(cue.get("end_seconds")), end) + delta,
                    6,
                )
            else:
                _shift_timed_row(cue, end, delta)
        for row in (*asset_rows, *clip_rows, *authored_rows):
            _shift_timed_row(row, end, delta)
        duration = round(duration + delta, 6)
        report.append(
            f"Extended native speech at {start:.2f}-{end:.2f}s by {delta:.2f}s "
            "and rippled the owning Shot and later Timeline events."
        )

    if bool(payload.get("enforce_native_speech_release_gap", False)):
        release_layers = [
            row for row in layers
            if str(row.get("content_role", row.get("role", ""))).lower()
            in {"dialogue", "voice_over"}
        ]
        latest_release_end: float | None = None
        for layer in sorted(
            release_layers,
            key=lambda row: (
                _number(row.get("start_seconds")),
                _number(row.get("end_seconds")),
            ),
        ):
            start = _number(layer.get("start_seconds"))
            end = _number(layer.get("end_seconds"), start)
            policy = str(layer.get("overlap_policy", "auto")).strip().lower()
            if policy in {"allow", "allow_overlap", "intentional", "intentional_overlap"}:
                policy = "overlap"
            elif policy in {"no_overlap", "no overlap", "sequence"}:
                policy = "sequential"
            if latest_release_end is not None and policy != "overlap":
                safe_start = latest_release_end + NATIVE_SPEECH_RELEASE_GAP_SECONDS
                if start < safe_start - 1e-6:
                    delta = round(safe_start - start, 6)
                    boundary = start
                    previous_shot = max(
                        (
                            shot for shot in shots
                            if _number(shot.get("end_seconds")) <= boundary + 1e-6
                        ),
                        key=lambda shot: _number(shot.get("end_seconds")),
                        default=None,
                    )
                    for other in layers:
                        if _number(other.get("start_seconds")) >= boundary - 1e-9:
                            _shift_timed_row(other, boundary, delta)
                    for cue in cues:
                        if cue is previous_shot:
                            cue["end_seconds"] = round(
                                _number(cue.get("end_seconds")) + delta, 6
                            )
                        else:
                            _shift_timed_row(cue, boundary, delta)
                    for row in (*asset_rows, *clip_rows, *authored_rows):
                        _shift_timed_row(row, boundary, delta)
                    duration = round(duration + delta, 6)
                    start += delta
                    end += delta
                    layer["speech_timing_auto_adjusted"] = True
                    layer["native_speech_release_gap_seconds"] = (
                        NATIVE_SPEECH_RELEASE_GAP_SECONDS
                    )
                    report.append(
                        f"Moved native speech {layer.get('layer_id', 'Text Layer')} "
                        f"by {delta:.2f}s to preserve a "
                        f"{NATIVE_SPEECH_RELEASE_GAP_SECONDS:.2f}s non-vocal release gap."
                    )
            latest_release_end = max(latest_release_end or 0.0, end)

    if layers:
        latest_end = max(_number(row.get("end_seconds")) for row in layers)
        required_end = math.ceil(
            (latest_end + FINAL_SPEECH_TAIL_SECONDS) * 2.0
        ) / 2.0
        if duration < required_end - 1e-6:
            old_duration = duration
            duration = round(required_end, 6)
            final_shot = max(
                shots,
                key=lambda row: _number(row.get("end_seconds")),
                default=None,
            )
            if final_shot is not None:
                final_shot["end_seconds"] = duration
            for row in (*asset_rows, *clip_rows):
                if _number(row.get("end_seconds")) >= initial_duration - 1e-6:
                    row["end_seconds"] = duration
            report.append(
                f"Extended the Project endpoint from {old_duration:.2f}s to {duration:.2f}s "
                f"to preserve a {FINAL_SPEECH_TAIL_SECONDS:.1f}s final breath/room-tone tail."
            )
    work_area = payload.get("work_area")
    if isinstance(work_area, list) and len(work_area) >= 2:
        if _number(work_area[1]) >= initial_duration - 1e-6:
            work_area[1] = duration
    payload["timeline_duration_seconds"] = duration
    return duration


def repair_speech_timing_payload(payload: dict) -> tuple[dict, list[str]]:
    """Repair only speech timing/language and dependent Timeline positions."""
    result = deepcopy(payload)
    report: list[str] = []
    shots = sorted(
        (
            row for row in (result.get("director_cues") or [])
            if isinstance(row, dict) and str(row.get("cue_type", "")) == "shot"
        ),
        key=lambda row: (_number(row.get("start_seconds")), _number(row.get("end_seconds"))),
    )
    duration = _repair_native_speech_timing(result, shots, report)
    for layer in result.get("text_layers") or []:
        if not isinstance(layer, dict):
            continue
        owner = _shot_owner(
            shots,
            _number(layer.get("start_seconds")),
            _number(layer.get("end_seconds"), _number(layer.get("start_seconds"))),
        )
        if owner is not None:
            layer["shot_id"] = str(owner.get("cue_id", ""))
    if shots and abs(_number(shots[-1].get("end_seconds")) - duration) > 1e-6:
        shots[-1]["end_seconds"] = duration
    return result, report


def _shot_owner(shots: list[dict], start: float, end: float) -> dict | None:
    midpoint = (start + end) / 2.0
    containing = [
        shot for shot in shots
        if _number(shot.get("start_seconds")) - 1e-9
        <= midpoint
        <= _number(shot.get("end_seconds")) + 1e-9
    ]
    if containing:
        return min(
            containing,
            key=lambda shot: (
                _number(shot.get("end_seconds")) - _number(shot.get("start_seconds")),
                _number(shot.get("start_seconds")),
            ),
        )
    overlaps = [
        (
            max(
                0.0,
                min(end, _number(shot.get("end_seconds")))
                - max(start, _number(shot.get("start_seconds"))),
            ),
            shot,
        )
        for shot in shots
    ]
    positive = [row for row in overlaps if row[0] > 0.0]
    if positive:
        return max(positive, key=lambda row: row[0])[1]
    return min(
        shots,
        key=lambda shot: abs(_number(shot.get("end_seconds")) - start),
        default=None,
    )


def _explicit_cast_count(text: str) -> int | None:
    """Return only a cast count that the saved design states explicitly."""
    source = " ".join(str(text or "").split())
    if not source:
        return None
    patterns = (
        r"\b(?:exactly|actual(?:ly)?|visible|complete|principal|main)?\s*"
        r"(\d{1,2})\s*(?:people|persons|characters|principals|speakers|cast members)\b",
        r"\b(one|two|three|four|five|six|seven|eight|nine)\s*[- ]?"
        r"(?:person|people|character|speaker|member|cast)\b",
        r"(?:恰好|正好|实际|實際|共有|共|画面中|畫面中|P1中|P1 中)?\s*"
        r"([一二两兩三四五六七八九十\d]{1,2})\s*"
        r"(?:个|個|名|位)?(?:人|人物|角色|主角|发言者|發言者)",
    )
    word_numbers = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9,
        "一": 1, "二": 2, "两": 2, "兩": 2, "三": 3, "四": 4,
        "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    }
    for pattern in patterns:
        match = re.search(pattern, source, re.I)
        if not match:
            continue
        token = match.group(1).strip().casefold()
        value = int(token) if token.isdigit() else word_numbers.get(token)
        if value is not None and 1 <= value <= 20:
            return value
    return None


def _repair_comic_talk_show_speakers(
    payload: dict,
    shots: list[dict],
    report: list[str],
) -> None:
    """Keep saved Comic Talk Show speakers inside the explicitly detected P1 cast."""
    if str(payload.get("special_skill", "")).strip().casefold() != "comic-talk-show-h3":
        return
    prompt = payload.get("prompt") or {}
    evidence_parts: list[str] = []
    if isinstance(prompt, dict):
        for key in ("brief", "creative_brief", "constraints"):
            value = prompt.get(key)
            if isinstance(value, list):
                evidence_parts.extend(str(row) for row in value)
            elif value:
                evidence_parts.append(str(value))
    for key in ("design_requirement", "design_requirements", "creative_brief"):
        value = payload.get(key)
        if isinstance(value, list):
            evidence_parts.extend(str(row) for row in value)
        elif value:
            evidence_parts.append(str(value))
    cast_count = _explicit_cast_count("\n".join(evidence_parts))
    if cast_count is None:
        return

    speech_layers = [
        row for row in (payload.get("text_layers") or [])
        if isinstance(row, dict)
        and str(row.get("content_role", row.get("role", ""))).strip().lower()
        in {"dialogue", "voice_over"}
        and str(row.get("text", row.get("content", ""))).strip()
    ]
    speech_layers.sort(
        key=lambda row: (_number(row.get("start_seconds")), _number(row.get("end_seconds")))
    )
    authored = [
        row for row in (payload.get("authored_text_requirements") or [])
        if isinstance(row, dict)
    ]
    cue_changes: list[tuple[dict, str, str]] = []
    repaired_count = 0
    for index, layer in enumerate(speech_layers):
        old_speaker = str(layer.get("speaker", "")).strip()
        match = re.fullmatch(r"S(\d+)", old_speaker, re.I)
        if not match or int(match.group(1)) <= cast_count:
            continue
        new_number = index % cast_count + 1
        new_speaker = f"S{new_number}"
        layer["speaker"] = new_speaker
        start = _number(layer.get("start_seconds"))
        end = _number(layer.get("end_seconds"), start)
        owner = _shot_owner(shots, start, end)
        if owner is not None:
            cue_changes.append((owner, old_speaker, new_speaker))
        for authored_row in authored:
            authored_text = str(
                authored_row.get("text", authored_row.get("content", ""))
            ).strip()
            if authored_text != str(layer.get("text", layer.get("content", ""))).strip():
                continue
            if abs(_number(authored_row.get("start_seconds")) - start) > 0.05:
                continue
            authored_row["speaker"] = new_speaker
        repaired_count += 1
        report.append(
            f"Remapped {layer.get('layer_id', 'Text Layer')} speaker from {old_speaker} "
            f"to {new_speaker}; saved P1 evidence explicitly contains {cast_count} people."
        )

    if not repaired_count:
        return
    for cue, old_speaker, new_speaker in cue_changes:
        for key in (
            "subject_action", "detail", "continuity_state", "environment_response",
            "native_audio_direction", "additional_direction",
        ):
            value = cue.get(key)
            if not isinstance(value, str) or not value:
                continue
            value = re.sub(
                rf"\b{re.escape(old_speaker)}\s*=\s*the\s+\d+(?:st|nd|rd|th)\s+complete",
                f"{new_speaker}=the {new_speaker[1:]} complete",
                value,
                flags=re.I,
            )
            cue[key] = re.sub(rf"\b{re.escape(old_speaker)}\b", new_speaker, value)


def _person_guard(text: str) -> str:
    lower = text.lower()
    female = bool(re.search(r"\b(?:woman|female|girl|heroine)\b|女人|女性|女孩", lower))
    male = bool(re.search(r"\b(?:man|male|boy|hero)\b|男人|男性|男孩", lower))
    explicit_two = bool(re.search(r"\b(?:two|2)\s+(?:people|persons|figures|characters)\b", lower))
    if female and male:
        return (
            "EXACT CAST LOCK: exactly one man and exactly one woman are visible; no third person, "
            "duplicate actor, double, crowd, staff, silhouette, human reflection, portrait, mannequin, "
            "split-screen copy or background figure."
        )
    if explicit_two:
        return (
            "EXACT CAST LOCK: exactly two unique people are visible and no one else; never duplicate "
            "either person or introduce background figures."
        )
    if female:
        return (
            "EXACT CAST LOCK: exactly one woman is visible and no one else; no duplicate, crowd, "
            "staff, silhouette, human reflection, portrait or background figure."
        )
    if male:
        return (
            "EXACT CAST LOCK: exactly one man is visible and no one else; no duplicate, crowd, staff, "
            "silhouette, human reflection, portrait or background figure."
        )
    return ""


def _append_once(text: str, contract: str, marker: str) -> str:
    value = str(text or "").strip()
    if not contract or marker in value:
        return value
    return value.rstrip(" .") + ". " + contract


def _base_asset_prompt(asset: dict) -> str:
    prompt = str(asset.get("clip_prompt", "")).strip()
    if prompt.startswith(_GENERATED_IDENTITY_PREFIX):
        prompt = prompt[len(_GENERATED_IDENTITY_PREFIX):]
    positions = [
        prompt.find(marker) for marker in _REFERENCE_AUGMENTATION_MARKERS
        if prompt.find(marker) >= 0
    ]
    if positions:
        prompt = prompt[:min(positions)]
    return prompt.rstrip(" .") + ("." if prompt.strip() else "")


def _asset_gender(asset: dict) -> str:
    text = (str(asset.get("filename", "")) + " " + _base_asset_prompt(asset)).lower()
    female = bool(re.search(r"\b(?:woman|female|girl|heroine)\b|女人|女性|女孩", text))
    male = bool(re.search(r"\b(?:man|male|boy|hero)\b|男人|男性|男孩", text))
    if female and not male:
        return "female"
    if male and not female:
        return "male"
    return ""


def _asset_has_content(asset: dict) -> bool:
    return bool(
        str(asset.get("local_path", "")).strip()
        or str(asset.get("clip_prompt", "")).strip()
        or str(asset.get("recognition", "")).strip()
        or bool(asset.get("timeline_placed", False))
    )


def _asset_count_guard(asset: dict, *, primary_identity: bool = False) -> str:
    filename = str(asset.get("filename", "")).lower()
    direct = _base_asset_prompt(asset)
    combined = filename + " " + direct
    if re.search(r"two[_ -]people|two\s+figures", combined, re.I):
        return (
            "REFERENCE PERSON COUNT CONTRACT: use exactly the two unique foreground people and no "
            "one else; never duplicate either person or reproduce background figures."
        )
    if primary_identity:
        return (
            "REFERENCE PERSON COUNT CONTRACT: use only the single primary foreground identity "
            "subject. Ignore and never reproduce every background person, crowd member, reflection, "
            "portrait, mannequin or face-like figure present in the source image."
        )
    if not re.search(r"\b(?:woman|man|girl|boy|person|people|figure|character)\b", direct, re.I):
        return (
            "REFERENCE PERSON COUNT CONTRACT: environment/prop reference only; render no visible "
            "people, silhouettes, human reflections, portraits, mannequins or face-like figures."
        )
    return _person_guard(direct).replace("EXACT CAST LOCK", "REFERENCE PERSON COUNT CONTRACT")


def _primary_identity_asset(payload: dict) -> dict | None:
    duration = _number(payload.get("timeline_duration_seconds"), 0.0)
    images = [
        row for row in (payload.get("assets") or {}).values()
        if isinstance(row, dict) and str(row.get("media_type")) == "image"
        and _asset_has_content(row) and _asset_gender(row)
    ]
    if not images:
        return None
    def score(asset: dict) -> tuple[int, float]:
        text = (str(asset.get("filename", "")) + " " + _base_asset_prompt(asset)).lower()
        points = 0
        if re.search(r"\bportrait\b|identity|headshot|close-up", text):
            points += 4
        if _number(asset.get("start_seconds")) <= 1e-6 and _number(asset.get("end_seconds")) >= duration - 1e-6:
            points += 3
        if str(asset.get("clip_prompt", "")).startswith(_GENERATED_IDENTITY_PREFIX):
            points += 2
        return points, -_number(asset.get("start_seconds"))
    return max(images, key=score)


def _normalize_asset_reference_contracts(payload: dict, report: list[str]) -> None:
    assets = payload.get("assets") or {}
    if not isinstance(assets, dict):
        return
    primary = _primary_identity_asset(payload)
    primary_gender = _asset_gender(primary) if primary else ""
    for asset in assets.values():
        if not isinstance(asset, dict) or str(asset.get("media_type")) != "image":
            continue
        if not _asset_has_content(asset):
            continue
        base = _base_asset_prompt(asset)
        gender = _asset_gender(asset)
        is_primary = asset is primary
        if is_primary:
            contract = (
                _GENERATED_IDENTITY_PREFIX
                + base
                + " "
                + _asset_count_guard(asset, primary_identity=True)
            )
        elif gender:
            distinct = bool(primary_gender and gender != primary_gender)
            role = (
                "DISTINCT SECONDARY CHARACTER IDENTITY: this reference belongs only to the separate "
                "story character and must never replace, blend with or duplicate the primary identity. "
                if distinct else
                "SUPPORTING ACTION-STATE REFERENCE ONLY: preserve the established primary identity; "
                "do not invent a second actor or a competing face. "
            )
            contract = base + " " + role + _asset_count_guard(asset)
        else:
            contract = base + " " + _asset_count_guard(asset)
        contract = " ".join(contract.split())
        if str(asset.get("clip_prompt", "")).strip() != contract:
            asset["clip_prompt"] = contract
            report.append(
                f"Rebuilt reference ownership/count contract for {asset.get('reference_id', '?')}."
            )
        recognition = str(asset.get("recognition", ""))
        if "Requirement:" in recognition:
            recognition = recognition.split("Requirement:", 1)[0].rstrip() + "\nRequirement: " + contract
        elif recognition:
            recognition = recognition.rstrip() + "\nRequirement: " + contract
        asset["recognition"] = recognition


def _scope_global_environment_assets(payload: dict, shots: list[dict], report: list[str]) -> None:
    duration = _number(payload.get("timeline_duration_seconds"), 0.0)
    if not shots or duration <= 0.0:
        return
    assets = payload.get("assets") or {}
    if not isinstance(assets, dict):
        return
    for asset in assets.values():
        if not isinstance(asset, dict) or str(asset.get("media_type")) != "image":
            continue
        if "AI DESIGN GENERATED REFERENCE" not in str(asset.get("recognition", "")):
            continue
        start = _number(asset.get("start_seconds"), 0.0)
        end = _number(asset.get("end_seconds"), 0.0)
        if start > 1e-6 or end < duration - 1e-6:
            continue
        guard = _asset_count_guard(asset, primary_identity=(asset is _primary_identity_asset(payload)))
        if "single primary foreground identity" in guard:
            continue
        words = {
            word for word in re.findall(r"[a-z0-9]{3,}", str(asset.get("filename", "")).lower())
            if word not in {"png", "webp", "image", "second", "reference", "generated"}
        }
        def score(shot: dict) -> tuple[int, float]:
            body = " ".join(
                str(shot.get(key, ""))
                for key in ("preset", "subject_action", "environment_response", "continuity_state", "detail")
            ).lower()
            return sum(word in body for word in words), -_number(shot.get("start_seconds"))
        best = max(shots, key=score)
        asset["start_seconds"] = _number(best.get("start_seconds"))
        asset["end_seconds"] = _number(best.get("end_seconds"))
        report.append(
            f"Scoped global environment reference {asset.get('reference_id', '?')} to "
            f"{asset['start_seconds']:.2f}-{asset['end_seconds']:.2f}s."
        )


def _split_multi_location_montage_shots(payload: dict, report: list[str]) -> None:
    """Turn explicit multi-cut montage prose into executable Shot Blocks.

    One H3 camera Shot cannot reliably visit an airport, hotel and cinema in a
    single continuous generation.  When the authored action explicitly says
    ``Cut to`` more than once, reference boundaries are used when available;
    otherwise the interval is divided on the 0.5-second grid.  This is a
    structural repair, not a story rewrite: every authored beat is retained.
    """
    cues = payload.get("director_cues") or []
    if not isinstance(cues, list):
        return
    image_boundaries: set[float] = set()
    changed = False
    for asset in (payload.get("assets") or {}).values():
        if not isinstance(asset, dict) or str(asset.get("media_type")) != "image":
            continue
        image_boundaries.update(
            (_number(asset.get("start_seconds")), _number(asset.get("end_seconds")))
        )
    rebuilt: list[dict] = []
    for cue in cues:
        if not isinstance(cue, dict) or str(cue.get("cue_type")) != "shot":
            rebuilt.append(cue)
            continue
        action = str(cue.get("subject_action", "")).strip()
        parts = [
            row.strip().rstrip(".") + "."
            for row in re.split(r"(?=\bCut\s+to\b)", action, flags=re.I)
            if row.strip()
        ]
        if len(parts) < 2:
            rebuilt.append(cue)
            continue
        start = _number(cue.get("start_seconds"))
        end = _number(cue.get("end_seconds"), start)
        internal = sorted(value for value in image_boundaries if start < value < end)
        if len(internal) == len(parts) - 1:
            boundaries = [start, *internal, end]
        else:
            boundaries = [start]
            for index in range(1, len(parts)):
                value = start + (end - start) * index / len(parts)
                boundaries.append(round(value * 2.0) / 2.0)
            boundaries.append(end)
        if any(boundaries[index + 1] - boundaries[index] < 0.5 for index in range(len(parts))):
            rebuilt.append(cue)
            continue
        base_detail = re.split(r"\s+EXACT CAST LOCK:", str(cue.get("detail", "")), maxsplit=1)[0].strip()
        for index, (part, part_start, part_end) in enumerate(
            zip(parts, boundaries, boundaries[1:]), 1
        ):
            row = deepcopy(cue)
            row["start_seconds"] = part_start
            row["end_seconds"] = part_end
            row["subject_action"] = part
            row["continuity_state"] = (
                "Incoming: preserve the exact outgoing state and screen direction from the previous Shot. "
                "Outgoing: complete only this Shot's single-location beat; do not begin the next montage location."
            )
            detail = (
                base_detail.rstrip(" .")
                + ". SINGLE-LOCATION SHOT: no simultaneous location, split-screen or extra montage beat."
            )
            guard = _person_guard(part)
            row["detail"] = _append_once(detail, guard, "EXACT CAST LOCK:")
            rebuilt.append(row)
        report.append(
            f"Split multi-location montage {cue.get('cue_id', 'Shot')} into {len(parts)} executable Shots."
        )
        changed = True
    shots = sorted(
        [row for row in rebuilt if isinstance(row, dict) and str(row.get("cue_type")) == "shot"],
        key=lambda row: (_number(row.get("start_seconds")), _number(row.get("end_seconds"))),
    )
    if changed:
        for index, shot in enumerate(shots, 1):
            shot["cue_id"] = f"S{index}"
    payload["director_cues"] = rebuilt


def repair_project_payload(
    source: dict,
    *,
    invalidate_stale_renders: bool = True,
) -> tuple[dict, list[str]]:
    """Repair Shot coverage, Text ownership and reference count contracts."""

    payload = deepcopy(source)
    report: list[str] = []
    duration = max(0.5, _number(payload.get("timeline_duration_seconds"), 0.5))
    _split_multi_location_montage_shots(payload, report)
    cues = [row for row in (payload.get("director_cues") or []) if isinstance(row, dict)]
    shots = sorted(
        [row for row in cues if str(row.get("cue_type")) == "shot"],
        key=lambda row: (_number(row.get("start_seconds")), _number(row.get("end_seconds"))),
    )
    if shots:
        if _number(shots[0].get("start_seconds")) > 1e-9:
            shots[0]["start_seconds"] = 0.0
            report.append("Extended the first Shot to 0.00s.")
        previous = shots[0]
        for current in shots[1:]:
            previous_end = _number(previous.get("end_seconds"))
            current_start = _number(current.get("start_seconds"))
            if abs(previous_end - current_start) > 1e-9:
                boundary = round((previous_end + current_start) * 2.0) / 2.0
                boundary = min(
                    max(boundary, _number(previous.get("start_seconds")) + 0.5),
                    _number(current.get("end_seconds")) - 0.5,
                )
                previous["end_seconds"] = boundary
                current["start_seconds"] = boundary
                report.append(f"Closed Shot-lane gap/overlap at {boundary:.2f}s.")
            previous = current
        if _number(shots[-1].get("end_seconds")) != duration:
            old = _number(shots[-1].get("end_seconds"))
            shots[-1]["end_seconds"] = duration
            report.append(f"Extended the final Shot from {old:.2f}s to {duration:.2f}s.")

        for shot in shots:
            body = " ".join(
                str(shot.get(key, ""))
                for key in ("subject_action", "continuity_state", "environment_response")
            )
            guard = _person_guard(body)
            if guard:
                shot["detail"] = _append_once(
                    str(shot.get("detail", "")), guard, "EXACT CAST LOCK:"
                )

        valid_ids = {str(shot.get("cue_id", "")) for shot in shots}
        for layer in payload.get("text_layers") or []:
            if not isinstance(layer, dict):
                continue
            role = str(layer.get("content_role", layer.get("role", "")))
            start = _number(layer.get("start_seconds"))
            end = _number(layer.get("end_seconds"), start)
            owner = _shot_owner(shots, start, end)
            old_id = str(layer.get("shot_id", ""))
            if owner is not None:
                new_id = str(owner.get("cue_id", ""))
                if old_id != new_id or old_id not in valid_ids:
                    layer["shot_id"] = new_id
                    if role in SPEECH_ROLES:
                        report.append(
                            f"Rebound {layer.get('layer_id', 'Text Layer')} to {new_id}."
                        )

        duration = _repair_native_speech_timing(payload, shots, report)
        _repair_comic_talk_show_speakers(payload, shots, report)
        for layer in payload.get("text_layers") or []:
            if not isinstance(layer, dict):
                continue
            start = _number(layer.get("start_seconds"))
            end = _number(layer.get("end_seconds"), start)
            owner = _shot_owner(shots, start, end)
            if owner is not None:
                layer["shot_id"] = str(owner.get("cue_id", ""))
        if shots and _number(shots[-1].get("end_seconds")) != duration:
            shots[-1]["end_seconds"] = duration

    _normalize_asset_reference_contracts(payload, report)
    _scope_global_environment_assets(payload, shots, report)
    assets = payload.get("assets") or {}
    if isinstance(assets, dict):
        for asset in assets.values():
            if not isinstance(asset, dict) or str(asset.get("media_type")) != "image":
                continue
            if not _asset_has_content(asset):
                continue
            guard = _asset_count_guard(
                asset, primary_identity=(asset is _primary_identity_asset(payload))
            )
            if not guard:
                continue
            before = str(asset.get("clip_prompt", ""))
            asset["clip_prompt"] = _append_once(
                before, guard, "REFERENCE PERSON COUNT CONTRACT:"
            )
            recognition = str(asset.get("recognition", ""))
            asset["recognition"] = _append_once(
                recognition, guard, "REFERENCE PERSON COUNT CONTRACT:"
            )
            if asset["clip_prompt"] != before:
                report.append(
                    f"Added reference person-count protection to {asset.get('reference_id', '?')}."
                )

    if report and invalidate_stale_renders:
        payload["smart_render"] = {}
        payload["smart_render_manifests"] = {}
        payload["render_dirty_segment_ids"] = []
        payload["shot_take_states"] = {}
        payload["segment_take_states"] = {}
        payload["generated_output"] = ""
        payload["generated_output_timeline_start"] = 0.0
        prompt = payload.get("prompt")
        if isinstance(prompt, dict):
            prompt["output"] = ""
        report.append("Invalidated stale generated takes; the repaired Timeline requires a new render.")
    payload["integrity_repair_report"] = list(dict.fromkeys(report))
    return payload, list(dict.fromkeys(report))


def rebase_project_media_paths(
    payload: dict,
    project_path: Path,
) -> list[str]:
    """Replace unavailable saved paths with unique files in the Project workspace.

    Canonical Project JSON is stored in ``Workspace/project`` while generated
    references live below the sibling ``Workspace/media`` tree.  A Project
    copied from another computer therefore cannot rely on its former absolute
    drive path even though the files are present in the portable workspace.
    """

    project_dir = Path(project_path).expanduser().resolve().parent
    workspace_dir = (
        project_dir.parent
        if project_dir.name.casefold() == "project"
        else project_dir
    )
    search_roots = list(dict.fromkeys((project_dir, workspace_dir)))
    assets = payload.get("assets") or {}
    if not isinstance(assets, dict):
        return []

    report: list[str] = []
    for node_id, asset in assets.items():
        if not isinstance(asset, dict):
            continue
        raw_path = str(asset.get("local_path") or "").strip()
        current = Path(raw_path).expanduser() if raw_path else None
        if current is not None and current.is_file():
            continue
        basename = str(asset.get("filename") or "").strip()
        if not basename and current is not None:
            basename = current.name
        if not basename:
            continue

        matches: list[Path] = []
        seen: set[str] = set()
        for root in search_roots:
            if not root.exists():
                continue
            for candidate in root.rglob(basename):
                if not candidate.is_file():
                    continue
                resolved = candidate.resolve()
                key = str(resolved).casefold()
                if key in seen:
                    continue
                seen.add(key)
                matches.append(resolved)
        if len(matches) != 1:
            continue
        asset["local_path"] = str(matches[0])
        asset["filename"] = matches[0].name
        report.append(
            f"Rebased media loader {node_id} to portable workspace file {matches[0].name}."
        )
    return report


def rebase_project_workspace_metadata(payload: dict, project_path: Path) -> str:
    """Point canonical workspace metadata at the exported Project's location."""

    project_dir = Path(project_path).expanduser().resolve().parent
    workspace_dir = (
        project_dir.parent
        if project_dir.name.casefold() == "project"
        else project_dir
    )
    payload["workspace_root"] = str(workspace_dir)
    payload["example_work_dir"] = str(workspace_dir)
    return f"Rebased canonical workspace metadata to {workspace_dir}."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    source = Path(args.source).resolve()
    destination = Path(args.destination).resolve()
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    repaired, report = repair_project_payload(payload)
    report.append(rebase_project_workspace_metadata(repaired, destination))
    report.extend(rebase_project_media_paths(repaired, destination))
    report = list(dict.fromkeys(report))
    repaired["integrity_repair_report"] = report
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(repaired, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"destination": str(destination), "repairs": report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

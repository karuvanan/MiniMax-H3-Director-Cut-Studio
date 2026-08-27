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


class DesignDurationContractError(ValueError):
    """The model changed a duration that the user specified explicitly."""


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
    missing = [
        item for item in required
        if not any(
            str(candidate.get("role", "")) == item["role"]
            and str(candidate.get("content", "")).strip() == item["content"]
            and abs(float(candidate.get("start_seconds", -1.0)) - item["start_seconds"]) <= 0.01
            and abs(float(candidate.get("end_seconds", -1.0)) - item["end_seconds"]) <= 0.01
            for candidate in actual
        )
    ]
    if missing:
        raise ValueError(
            "The Design requirement contains explicit timed Dialogue/Voice-over/Lyrics/On-screen "
            f"Text, but {len(missing)} exact layer(s) are missing. Apply/Run is blocked to prevent "
            "silent video generation. Regenerate or restore the authored text layers."
        )
    return required


def automatic_background_soundscape(plan: dict) -> str:
    """Return a concise H3-ready ambience bed when the LM omitted one."""
    existing = " ".join(str(plan.get("overall_soundscape", "")).split())
    if existing:
        base = existing
    else:
        evidence = " ".join(
            str(value or "")
            for value in (
                plan.get("creative_brief"),
                *(item.get("environment_response", "") for item in plan.get("shots") or []),
                *(item.get("subject_action", "") for item in plan.get("shots") or []),
            )
        ).lower()
        if any(word in evidence for word in ("office", "desk", "computer", "workspace")):
            base = "Natural office room tone, restrained HVAC, subtle keyboard and desk foley."
        elif any(word in evidence for word in ("city", "street", "traffic", "car", "road")):
            base = "Natural city ambience, distant traffic, location room tone and synchronized movement foley."
        elif any(word in evidence for word in ("forest", "mountain", "garden", "courtyard", "roof")):
            base = "Natural outdoor ambience, wind through the environment, footsteps, cloth and contact-driven foley."
        else:
            base = "Natural location room tone with synchronized footsteps, cloth, object and environmental foley."
    guard = (
        " Keep authored speech in the foreground unchanged; duck ambience and music under every spoken line."
    )
    if "authored speech" not in base.lower():
        base = base.rstrip(". ") + "." + guard
    return base.strip()


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
    loaded_image_count = sum(
        bool(row.get("loaded", False)) and row.get("media_type") == "image"
        for row in inventory.values()
    )
    free_image_slots = max(
        0, int(capacities.get("image", 0)) - loaded_image_count
    )
    requests = [
        dict(row) for row in source.get("media_requests") or []
        if isinstance(row, dict)
    ]
    shots = [dict(row) for row in source.get("shots") or [] if isinstance(row, dict)]
    for request_index, request in enumerate(requests):
        requirement_id = _normalized_requirement_id(
            request.get("requirement_id"), f"request_{request_index + 1}"
        )
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
    request_ids = {
        _normalized_requirement_id(row.get("requirement_id"), f"request_{index}")
        for index, row in enumerate(requests, 1)
    }
    valid_uses: list[dict] = []
    warnings: list[str] = []
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

    source["existing_media_uses"] = valid_uses

    valid_picture_ids = {
        _normalized_media_id(row.get("media_id", ""))
        for row in valid_uses
        if _media_type_for_id(_normalized_media_id(row.get("media_id", ""))) == "image"
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
) -> dict:
    media_repair_warnings: list[str] = []
    prepared_payload = extract_design_json(payload)
    authored_duration = infer_explicit_design_duration(authored_requirement)
    if authored_duration is not None:
        returned_duration = snap_half_second(
            prepared_payload.get("duration_seconds", 5.0),
            MAX_DESIGN_DURATION_SECONDS,
        )
        if abs(returned_duration - authored_duration) > 0.01:
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
        source, media_repair_warnings = repair_design_media_plan(
            prepared_payload, capacities, existing_media
        )
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
        raise ValueError("Design JSON is missing creative_brief")
    if not plan["global_visual_style"]:
        raise ValueError("Design JSON is missing global_visual_style")
    plan["overall_soundscape"] = automatic_background_soundscape({
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
                    f"Shot {previous['id']} overlaps S{index}. H3 camera Shots must be chronological "
                    "and non-overlapping; use overlapping V tracks only for media layers."
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
    plan["existing_media_uses"] = existing_media_uses
    reused_media_ids = sorted({row["media_id"] for row in existing_media_uses})
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
        preferred_media_id = _normalized_media_id(raw.get("preferred_media_id", ""))
        if media_type == "image" and preferred_media_id.startswith("P"):
            preferred_ordinal = int(preferred_media_id[1:])
            preferred_row = inventory.get(preferred_media_id)
            if (
                preferred_ordinal <= int(capacities.get("image", 0))
                and not bool(preferred_row and preferred_row.get("loaded", False))
            ):
                normalized_request["preferred_media_id"] = preferred_media_id
        media_requests.append(normalized_request)
        requested_requirement_ids.add(requirement_id)
    plan["media_requests"] = media_requests
    return plan


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
    return (
        "You are the AI Design Planner inside a MiniMax H3 Director Cut application. "
        "Convert the user's concept into one production-ready JSON object that exactly matches the supplied schema. "
        + skill_direction
        + duration_contract
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
        "Timeline tracks are editorial lanes, not the physical H3 reference-slot count. You may plan V4, V5 and higher "
        "visual lanes for overlapping action states, titles or compositing, and A4, A5 and higher audio lanes for dialogue, "
        "voice-over, lyrics, ambience or music stems; the Studio creates those tracks automatically. Keep on-screen text on "
        "a V track and place dialogue, voice-over and lyrics on A tracks. "
        "An editorial A-track label such as A1 is not proof that an Audio asset exists. When the user supplies authored "
        "Dialogue, Voice-over or Lyrics without an explicitly loaded @A reference, put the exact words in text_layers only; "
        "never invent A1 in existing_media_uses and never create a placeholder speech-audio request. The application reserves "
        "the generated TTS Audio slot after validation. "
        "The renderer will select only the temporally relevant references for each native 15-second H3 window, so never exceed "
        "the supplied physical media_capacity merely because "
        "additional editorial tracks exist. "
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
        "media_requests must contain only genuinely missing assets after this reuse audit. Choose that missing count dynamically from "
        "the concept and available empty slots; never duplicate a requirement already fulfilled by @P1/@V1/@A1. "
        "For media_requests, use h3_reference when an asset supplies subject, product, wardrobe, environment or composition guidance; "
        "use timeline_visual only when the user explicitly asks to composite the literal file into the editorial preview. "
        "Plan reference media dynamically from the story: reusable identity and environment references are valid, and time-scoped "
        "composition, action-state or boundary-continuity references are also valid when they reduce ambiguity between story phases. "
        "Choose the useful count and exact timeline ranges yourself. Never force one image per Shot, never fill all available slots merely "
        "because they exist, and never make redundant copies; distinct temporal states of the same subject are allowed when they prevent "
        "a later segment from replaying an earlier action. Do not return zero image references when the plan has visual Shots and empty "
        "Picture capacity. As a coverage floor, provide approximately one useful image state per five seconds, never more than one per "
        "Shot, while counting genuinely reused Picture assets toward that floor and staying within free capacity. "
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
        "Only create a text_layer or theme_text when the user explicitly requests visible text, dialogue, voice-over or lyrics, and set "
        "explicit_user_requested=true only in that case. Never turn the creative brief or scene description into on-screen text. "
        "For every dialogue text_layer, infer the gender of the speaking on-screen character from the user's story, Shot action and "
        "reference-media evidence. Assign S1 to a female speaker and S2 to a male speaker, keep the assignment consistent across every "
        "Shot, and never use the narrator's gender when the visible character is speaking. If the user explicitly writes S1 or S2, "
        "preserve that explicit assignment. Put the intended emotion and pace in delivery without changing the authored words. "
        "Always design a useful overall_soundscape containing diegetic location ambience and contact-synchronized foley. Keep dialogue "
        "in the foreground, duck background ambience and non-diegetic music beneath speech, and never replace or echo authored dialogue "
        "as part of the background sound. "
        "Always include a Final Hold marker before the final frame; cue timestamps must be earlier than duration_seconds. "
        "Never leave constraints blank. It must explicitly state that core actions and continuity states outrank optional "
        "flourishes, and that optional detail is dropped before a Shot is delayed or replayed. The Final Hold must resolve "
        "the last Shot's outgoing physical state rather than introduce a new action. "
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

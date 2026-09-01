"""Core prompt-building and validation logic for H3 Prompt Studio."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Iterable
from urllib import error, request


DEFAULT_SYSTEM_PROMPT = """You are a professional prompt architect for MiniMax H3 reference-to-video generation.
Turn the user's production brief into ONE polished, production-ready video prompt in English.

Required order:
1. A concise global visual-style sentence.
2. Exact reference-image, character-continuity, and audio-use instructions.
3. Sequential sections named CUT 1, CUT 2, and so on.
4. Every CUT must state framing/angle, subject, action/performance, camera movement, environment response, and audio/dialogue synchronization when relevant.
5. Put TRANSITION sections only between cuts. Make each transition visually connect the outgoing and incoming shots.
6. End with an explicit final hold or end-frame instruction.

Rules:
- Preserve every <Picture N>, <Video N>, and <Audio N> tag exactly.
- Never invent new reference tags, spoken dialogue, on-screen words, brands, or characters.
- If dialogue is supplied, preserve its wording exactly and specify accurate lip sync.
- If on-screen text is supplied, preserve spelling exactly and describe its timing, style, and placement.
- Distinguish camera motion from subject motion. Use chronological action order.
- Keep identity, costume, props, scale, palette, lighting, and geography continuous.
- Resolve ambiguity conservatively; do not add new plot events.
- Avoid explanations, headings outside the production prompt, markdown fences, and negative-prompt boilerplate.
- Use forceful but readable film language. Prefer concrete visible actions over abstract adjectives.
Return only the final prompt."""


@dataclass(slots=True)
class PromptSpec:
    brief: str
    style: str = "cinematic, cohesive visual direction"
    references: str = ""
    audio: str = ""
    music: str = ""
    shots: list[str] = field(default_factory=list)
    shot_ranges: list[dict] = field(default_factory=list)
    # Timeline-authored Type clips remain independent from visual Shot prompts.
    # The H3 compiler places these timed events in detailed_description without
    # copying their exact wording into a Director Shot's action prose.
    text_ranges: list[dict] = field(default_factory=list)
    dialogue: str = ""
    transition: str = ""
    ending: str = "Hold on the final image. Do not add another cut."
    must_keep: str = ""
    technical: str = ""
    transition_ranges: list[dict] = field(default_factory=list)
    has_supplied_dialogue_audio: bool = False
    # Prompt-only H3 native soundtrack direction.  These rows never create an
    # external audio node or alter the generated H3 soundtrack.
    native_audio_ranges: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class ValidationResult:
    score: int
    items: list[tuple[str, str]]

    def as_text(self) -> str:
        rows = [f"结构完整度：{self.score}/100"]
        icons = {"ok": "✓", "warning": "!", "error": "×"}
        rows.extend(f"{icons.get(level, '•')} {message}" for level, message in self.items)
        return "\n".join(rows)


def split_shots(text: str) -> list[str]:
    """Split one-shot-per-line input while accepting CUT labels and blank spacing."""
    shots: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^(?:CUT|镜头)\s*\d+\s*[:：.、-]?\s*", "", line, flags=re.I)
        if line:
            shots.append(line)
    return shots


def _sentence(text: str) -> str:
    text = " ".join(text.strip().split())
    if text and text[-1] not in ".!?。！？":
        text += "."
    return text


def _dialogue_by_cut(text: str) -> dict[int, list[str]]:
    """Parse `1|dialogue` lines; unnumbered lines attach to CUT 1."""
    result: dict[int, list[str]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = re.match(r"^(\d+)\s*[|｜:]\s*(.+)$", line)
        cut_no, words = (int(match.group(1)), match.group(2)) if match else (1, line)
        result.setdefault(cut_no, []).append(words.strip())
    return result


def build_structured_prompt(spec: PromptSpec) -> str:
    """Create a deterministic H3-ready structure without translating user content."""
    blocks: list[str] = []
    blocks.append(_sentence(spec.style or "cinematic, cohesive visual direction"))

    setup: list[str] = []
    if spec.references.strip():
        setup.append(_sentence(spec.references))
    if spec.audio.strip():
        setup.append(_sentence(spec.audio))
    if spec.technical.strip():
        setup.append(_sentence(spec.technical))
    if setup:
        blocks.append(" ".join(setup))

    if spec.brief.strip():
        blocks.append(f"STORY AND CONTINUITY: {_sentence(spec.brief)}")
    if spec.must_keep.strip():
        blocks.append(f"MUST KEEP: {_sentence(spec.must_keep)}")

    if spec.text_ranges:
        rows = [
            "TIMELINE TYPE / DIALOGUE TRACK: execute every independently timed clip exactly once; "
            "never move its wording into Shot action prose."
        ]
        for item in sorted(
            spec.text_ranges,
            key=lambda row: (
                float(row.get("start_seconds", 0.0)),
                float(row.get("end_seconds", 0.0)),
            ),
        ):
            start = float(item.get("start_seconds", 0.0))
            end = float(item.get("end_seconds", start))
            role = str(item.get("content_role", "on_screen_text"))
            text = str(item.get("text", "")).strip()
            track = str(item.get("track_id", "Type"))
            if role == "on_screen_text":
                rows.append(
                    f'[{track} {start:.3f}-{end:.3f}s] Show exact text "{text}".'
                )
            else:
                speaker = str(item.get("speaker", "S1"))
                language = str(item.get("language", "Original"))
                rows.append(
                    f"[{track} {start:.3f}-{end:.3f}s] ({speaker}) "
                    f"<d>[{language}] {text}</d>"
                )
        blocks.append("\n".join(rows))

    if spec.native_audio_ranges:
        rows = [
            "NATIVE H3 AUDIO DIRECTIONS: generate these sounds natively with each picture interval; "
            "do not treat them as post-production effects."
        ]
        for item in sorted(
            spec.native_audio_ranges,
            key=lambda row: float(row.get("start_seconds", 0.0)),
        ):
            start = float(item.get("start_seconds", 0.0))
            end = float(item.get("end_seconds", start))
            rows.append(
                f"[{start:.3f}-{end:.3f}s] {str(item.get('native_audio_direction', '')).strip()} "
                f"{str(item.get('environment_continuity', '')).strip()} "
                f"{str(item.get('audio_reference_intent', '')).strip()}"
            )
        blocks.append("\n".join(rows))

    shots = spec.shots or [spec.brief.strip() or "Describe the intended shot action."]
    dialogue = _dialogue_by_cut(spec.dialogue)
    for index, shot in enumerate(shots, start=1):
        cut_parts = [_sentence(shot)]
        if index in dialogue:
            exact_lines = " / ".join(f'"{line}"' for line in dialogue[index])
            if spec.has_supplied_dialogue_audio:
                cut_parts.append(
                    f"Spoken dialogue: {exact_lines}. Preserve the wording exactly and synchronize "
                    "the visible lip movement and phoneme timing to the supplied audio."
                )
            else:
                cut_parts.append(
                    f"Generate the exact spoken dialogue in its authored language: {exact_lines}. "
                    "Use a natural native voice with accurate visible lip sync; do not paraphrase, "
                    "translate, omit or replace any word."
                )
        blocks.append(f"CUT {index}: {' '.join(cut_parts)}")
        if index < len(shots):
            transition = spec.transition.strip() or "Use a motivated cinematic transition that preserves screen direction and visual continuity."
            blocks.append(f"TRANSITION: {_sentence(transition)}")

    ending = spec.ending.strip() or "Hold on the final image. Do not add another cut."
    blocks.append(f"END: {_sentence(ending)}")
    return "\n\n".join(blocks)


def build_ai_brief(spec: PromptSpec) -> str:
    """Serialize the form data for a language model without losing field boundaries."""
    payload = {
        "creative_brief": spec.brief,
        "global_visual_style": spec.style,
        "reference_and_continuity_rules": spec.references,
        "audio_rules": spec.audio,
        "non_diegetic_music": spec.music,
        "shots_in_chronological_order": [
            {"cut": index, "idea": shot} for index, shot in enumerate(spec.shots, 1)
        ],
        "exact_dialogue_or_on_screen_text": spec.dialogue,
        "preferred_transition_between_cuts": spec.transition,
        "transitions_between_shots": spec.transition_ranges,
        "final_hold": spec.ending,
        "must_keep_or_avoid": spec.must_keep,
        "technical_delivery": spec.technical,
    }
    return "PRODUCTION BRIEF\n" + json.dumps(payload, ensure_ascii=False, indent=2)


def _extract_response_text(data: dict) -> str:
    # OpenAI Responses-style output.
    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()
    for item in data.get("output", []):
        for content in item.get("content", []):
            if isinstance(content.get("text"), str):
                return content["text"].strip()
    # OpenAI-compatible chat-completions output.
    choices = data.get("choices") or []
    if choices:
        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            return "".join(part.get("text", "") for part in content).strip()
    raise ValueError("接口已返回数据，但找不到生成文字。请检查接口类型。")


def call_compatible_api(
    endpoint: str,
    api_key: str,
    model: str,
    spec: PromptSpec,
    timeout: int = 90,
    system_prompt: str | None = None,
) -> str:
    """Call either a Responses endpoint or a chat-completions compatible endpoint."""
    endpoint = endpoint.strip()
    if not endpoint.startswith(("http://", "https://")):
        raise ValueError("API 地址必须以 http:// 或 https:// 开头。")
    if not model.strip():
        raise ValueError("请填写模型名称。")

    user_text = build_ai_brief(spec)
    instructions = system_prompt or DEFAULT_SYSTEM_PROMPT
    if endpoint.rstrip("/").endswith("/responses"):
        body = {
            "model": model.strip(),
            "instructions": instructions,
            "input": user_text,
        }
    else:
        body = {
            "model": model.strip(),
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.35,
        }

    headers = {"Content-Type": "application/json"}
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    http_request = request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"API 请求失败（HTTP {exc.code}）：{detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"无法连接 API：{exc.reason}") from exc
    return _extract_response_text(data)


def _tag_set(text: str) -> set[str]:
    return set(re.findall(r"<(?:Picture|Video|Audio)\s+\d+>", text, flags=re.I))


def validate_prompt(prompt: str, expected_tags: Iterable[str] = ()) -> ValidationResult:
    """Give actionable structural feedback, not a claim about model quality."""
    items: list[tuple[str, str]] = []
    score = 100
    cuts = re.findall(r"\bCUT\s+(\d+)\s*:", prompt, flags=re.I)
    transitions = re.findall(r"\bTRANSITION\s*:", prompt, flags=re.I)
    h3_sections = (
        "subject_definitions:",
        "summary:",
        "retention_analysis:",
        "detailed_description:",
        "overall_soundscape:",
        "non_diegetic_music:",
    )
    is_ref2va = all(section in prompt for section in h3_sections)

    if is_ref2va:
        positions = [prompt.index(section) for section in h3_sections]
        if positions == sorted(positions):
            items.append(("ok", "H3 Ref2VA 六个区段齐全且顺序正确。"))
        else:
            score -= 20
            items.append(("error", "H3 Ref2VA 六个区段的顺序不正确。"))
        shots = [int(value) for value in re.findall(r"\[Shot\s+(\d+)\]", prompt, flags=re.I)]
        unique_shots = list(dict.fromkeys(shots))
        if unique_shots == list(range(1, len(unique_shots) + 1)) and unique_shots:
            items.append(("ok", f"镜头编号连续，共 {len(unique_shots)} 个 Shot。"))
        else:
            score -= 15
            items.append(("error", "没有检测到连续的 [Shot N] 结构。"))
    elif cuts:
        numbers = [int(value) for value in cuts]
        expected = list(range(1, len(numbers) + 1))
        if numbers == expected:
            items.append(("ok", f"镜头编号连续，共 {len(cuts)} 个 CUT。"))
        else:
            score -= 15
            items.append(("error", f"CUT 编号不是连续的：{numbers}。"))
    else:
        score -= 30
        items.append(("error", "没有检测到 CUT 1: 结构。"))

    if not is_ref2va:
        ideal_transitions = max(0, len(cuts) - 1)
        if len(transitions) == ideal_transitions:
            items.append(("ok", "转场数量与镜头数量匹配。"))
        else:
            score -= 10
            items.append(("warning", f"检测到 {len(transitions)} 个转场，{len(cuts)} 个镜头通常需要 {ideal_transitions} 个。"))

    expected = set(expected_tags)
    present = _tag_set(prompt)
    missing = expected - present
    invented = present - expected if expected else set()
    if missing:
        score -= min(25, 8 * len(missing))
        items.append(("error", "缺少参考标签：" + ", ".join(sorted(missing))))
    elif expected:
        items.append(("ok", "所有输入的参考标签均已保留。"))
    if invented:
        score -= min(15, 5 * len(invented))
        items.append(("warning", "输出出现未在素材栏声明的标签：" + ", ".join(sorted(invented))))

    if re.search(r"\b(?:END|Hold|freeze|final (?:shot|frame))\b", prompt, flags=re.I):
        items.append(("ok", "包含明确的结尾保持指令。"))
    else:
        score -= 10
        items.append(("warning", "建议补充最终画面保持或禁止追加镜头的指令。"))

    if len(prompt) > 8000:
        score -= 8
        items.append(("warning", "提示词超过 8,000 字符，建议删除重复形容词和次要特效。"))
    else:
        items.append(("ok", f"当前长度 {len(prompt):,} 字符。"))

    if re.search(r"\bthree words\b", prompt, flags=re.I):
        quoted = re.findall(r'"[^"]+"', prompt)
        if len(quoted) != 3:
            score -= 7
            items.append(("warning", "文字数量描述可能与引号中的文字单元数量不一致。"))

    return ValidationResult(max(0, score), items)


def reference_tags_from_spec(spec: PromptSpec) -> set[str]:
    return _tag_set(" ".join((spec.references, spec.audio, spec.brief, *spec.shots)))

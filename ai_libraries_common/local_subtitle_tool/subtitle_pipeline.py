#!/usr/bin/env python3
"""Create script-accurate English subtitles from a Chinese video and script.

Timing comes from faster-whisper.  A local LM Studio model is used only for
matching the transcript to the supplied script and translating the matched
script text; it never invents timestamps.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

# Dependencies may be installed privately in this tool folder so the shared
# ai_libraries_common environment remains untouched.
VENDOR_DIR = Path(__file__).with_name("vendor")
if VENDOR_DIR.is_dir():
    sys.path.insert(0, str(VENDOR_DIR))

from faster_whisper import WhisperModel
from openai import OpenAI


@dataclass
class AsrSegment:
    id: int
    start: float
    end: float
    text: str


@dataclass
class Cue:
    start: float
    end: float
    chinese: str
    english: str
    asr_ids: list[int]
    script_ids: list[int]


def timestamp(seconds: float) -> str:
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def write_srt(path: Path, cues: list[Cue], language: str) -> None:
    blocks: list[str] = []
    for index, cue in enumerate(cues, start=1):
        text = cue.chinese if language == "zh" else cue.english
        blocks.append(f"{index}\n{timestamp(cue.start)} --> {timestamp(cue.end)}\n{text}")
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def ass_color(value: str) -> str:
    value = value.lstrip("#")
    return "&H00" + value[4:6] + value[2:4] + value[0:2]


def language_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\s]+', '_', value).strip('._')
    return cleaned or "target"


def video_size(video: Path) -> tuple[int, int]:
    result = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(video)], text=True)
    stream = json.loads(result)["streams"][0]
    return int(stream["width"]), int(stream["height"])


def write_ass(path: Path, cues: list[Cue], width: int, height: int, font: str, size: int, color: str, outline_color: str, outline: int, bold: bool, x: float, y: float) -> None:
    header = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}", "", "[V4+ Styles]", "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding", f"Style: Default,{font},{size},{ass_color(color)},&H00000000,{ass_color(outline_color)},&H00000000,{-1 if bold else 0},0,0,0,100,100,0,0,1,{outline},0,5,0,0,0,1", "", "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"]
    def ass_time(seconds: float) -> str:
        return f"{int(seconds // 3600)}:{int(seconds % 3600 // 60):02}:{seconds % 60:05.2f}"
    px, py = round(width * x / 100), round(height * y / 100)
    for cue in cues:
        text = cue.english.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")
        header.append(f"Dialogue: 0,{ass_time(cue.start)},{ass_time(cue.end)},Default,,0,0,0,,{{\\pos({px},{py})}}{text}")
    path.write_text("\n".join(header) + "\n", encoding="utf-8-sig")


def read_srt_cues(path: Path) -> list[Cue]:
    def seconds(value: str) -> float:
        hours, minutes, rest = value.replace(",", ".").split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(rest)
    cues: list[Cue] = []
    for block in re.split(r"\r?\n\r?\n", path.read_text(encoding="utf-8-sig").strip()):
        lines = block.splitlines()
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start, end = (item.strip() for item in lines[1].split("-->"))
        cues.append(Cue(seconds(start), seconds(end), "", "\n".join(lines[2:]), [], []))
    if not cues:
        raise RuntimeError("The edited SRT has no valid subtitle cues.")
    return cues


def read_script(path: Path) -> list[str]:
    if path.suffix.lower() == ".docx":
        try:
            from docx import Document
        except ImportError as error:
            raise RuntimeError("Reading .docx needs python-docx. Run: pip install python-docx") from error
        raw = "\n".join(p.text for p in Document(path).paragraphs)
    else:
        raw = path.read_text(encoding="utf-8-sig")

    raw = html.unescape(raw).replace("\\", "").replace("\r", "\n")
    # A script often arrives as one pasted paragraph such as "…： 1. … 2. …".
    # Split numbered instructions, while leaving decimal UI values such as 0.2MP intact.
    raw = re.sub(r"(?<!^)(?=\s*\d+[.)、]\s+)", "\n", raw)
    # Treat punctuation, bullets, and line breaks as potential subtitle units.
    chunks = re.split(r"(?<=[。！？；])|\n+", raw)
    lines: list[str] = []
    for chunk in chunks:
        clean = re.sub(r"^\s*(?:[-•*]|\d+[.)、])\s*", "", chunk).strip()
        clean = re.sub(r"\s+", " ", clean)
        if clean:
            lines.append(clean)
    if not lines:
        raise RuntimeError("The script contains no usable text.")
    return lines


def transcribe(video: Path, model_name: str, device: str, compute_type: str, language: str | None, use_vad: bool = True, vad_threshold: float | None = None) -> list[AsrSegment]:
    print(f"[1/4] Transcribing audio with faster-whisper ({model_name}) …")
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    kwargs: dict[str, Any] = {
        "language": language, "beam_size": 5, "word_timestamps": True,
        "condition_on_previous_text": False,
    }
    if use_vad:
        # VAD keeps only detected speech. Sung or music-heavy audio is often cut
        # away (or merged into one chunk that Whisper hallucinates on), so it can
        # be disabled or its Silero threshold lowered for such videos.
        kwargs["vad_filter"] = True
        if vad_threshold is not None:
            kwargs["vad_parameters"] = {"threshold": vad_threshold}
    segments, _info = model.transcribe(str(video), **kwargs)
    result: list[AsrSegment] = []
    for index, segment in enumerate(segments, start=1):
        text = segment.text.strip()
        if text:
            result.append(AsrSegment(index, float(segment.start), float(segment.end), text))
    if not result:
        raise RuntimeError("No Chinese speech was detected in the video.")
    return result


def response_json(client: OpenAI, model: str, prompt: str, max_tokens: int = 8192) -> dict[str, Any]:
    """Accept JSON wrapped in prose as some local model templates do that."""
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": 0.1,
        # Long scripts need a long JSON response.  LM Studio's server default
        # can be too short, which otherwise leaves only the first few cues.
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": "You are a precise subtitle-localization engine. Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
    }
    try:
        completion = client.chat.completions.create(**kwargs, response_format={"type": "json_object"})
    except Exception:
        completion = client.chat.completions.create(**kwargs)
    text = completion.choices[0].message.content or ""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise RuntimeError("LM Studio did not return JSON. Try a Qwen Instruct model and retry.")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"LM Studio returned invalid JSON: {text[:300]}") from error


def make_prompt(script_lines: list[str], asr: list[AsrSegment], source_language: str, target_language: str) -> str:
    script_json = [{"id": i + 1, "text": text} for i, text in enumerate(script_lines)]
    asr_json = [asdict(segment) for segment in asr]
    return f"""
Match the production script to the ASR transcript from the same video, then translate the matched script into concise, natural {target_language} subtitles. The source language is {source_language}.

Rules:
1. The script is reference material, not a mandatory subtitle list. Use it to improve wording and translation only where it matches spoken audio. Do not create a subtitle merely because a script line exists.
2. ASR segments are authoritative for timing and determine which subtitles appear. For every cue, use only ASR ids supplied below. Do not invent timestamps or ids.
3. Keep ids in increasing order. `script_ids` may be an empty list when no script line clearly matches the spoken audio. Never force every script id to appear; silently omit unused script material.
4. Preserve UI labels, model names, buttons, filenames, numbers, units, and symbols exactly (for example NEXT, RUN+QUEUE, 0.2MP, generated_output.mp4).
5. Subtitle text must be written in {target_language} (even when the field name below is generic): at most two lines, with a target of 42 characters per line. Split overly long content into adjacent cues when possible.
6. Return JSON only in this exact schema:
{{"cues":[{{"asr_ids":[1],"script_ids":[1],"text":"…"}},{{"asr_ids":[2],"script_ids":[],"text":"…"}}]}}

SCRIPT:
{json.dumps(script_json, ensure_ascii=False)}

ASR:
{json.dumps(asr_json, ensure_ascii=False)}
""".strip()


def cues_from_model(payload: dict[str, Any], script_lines: list[str], asr: list[AsrSegment]) -> list[Cue]:
    by_asr = {item.id: item for item in asr}
    script_count = len(script_lines)
    raw_cues = payload.get("cues")
    if not isinstance(raw_cues, list) or not raw_cues:
        raise RuntimeError("LM Studio response has no cues.")

    cues: list[Cue] = []
    used_script: list[int] = []
    used_asr: list[int] = []
    for item in raw_cues:
        asr_ids = item.get("asr_ids")
        script_ids = item.get("script_ids")
        # The prompt asks for a generic "text" field; accept the legacy
        # "english" name too, since some models copy it from examples.
        english = str(item.get("text") or item.get("english") or "").strip()
        if not isinstance(asr_ids, list) or not isinstance(script_ids, list) or not english:
            raise RuntimeError("A cue is missing ASR ids, script ids, or subtitle text.")
        if any(not isinstance(i, int) or i not in by_asr for i in asr_ids):
            raise RuntimeError("A cue references an unknown ASR id.")
        if any(not isinstance(i, int) or not 1 <= i <= script_count for i in script_ids):
            raise RuntimeError("A cue references an unknown script id.")
        if asr_ids != sorted(asr_ids) or script_ids != sorted(script_ids):
            raise RuntimeError("Cue ids must be in chronological order.")
        start = min(by_asr[i].start for i in asr_ids)
        end = max(by_asr[i].end for i in asr_ids)
        chinese = "\n".join(script_lines[i - 1] for i in script_ids) if script_ids else "\n".join(by_asr[i].text for i in asr_ids)
        cues.append(Cue(start, end, chinese, english, asr_ids, script_ids))
        used_script.extend(script_ids)
        used_asr.extend(asr_ids)

    if any(a.end > b.start for a, b in zip(cues, cues[1:])):
        raise RuntimeError("Model created overlapping cue timing; rerun with a cleaner script or transcript.")
    return cues


def burn_subtitles(video: Path, ass: Path, output: Path) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is not on PATH. Install FFmpeg, then rerun without deleting the SRT.")
    # Use a forward-slash relative filename where possible; this avoids FFmpeg's Windows drive-letter parsing.
    subtitle_arg = ass.resolve().as_posix().replace(":", r"\:")
    command = [
        "ffmpeg", "-y", "-i", str(video), "-vf", f"ass='{subtitle_arg}'",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "copy", str(output),
    ]
    print("[4/4] Burning English subtitles into MP4 …")
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path, help="Input video file")
    parser.add_argument("--script", type=Path, help="Source .txt or .docx script")
    parser.add_argument("--render-srt", type=Path, help="Render an edited SRT into MP4, without transcribing or translating")
    parser.add_argument("--render-ass", type=Path, help="Render an edited ASS into MP4 without changing its styles")
    parser.add_argument("--output", type=Path, default=Path("output_subtitles"), help="Output folder")
    parser.add_argument("--output-prefix", help="Filename prefix for all generated artifacts")
    parser.add_argument("--lm-url", default="http://127.0.0.1:1234/v1", help="LM Studio OpenAI-compatible endpoint")
    parser.add_argument("--model", default="qwen3-8b", help="Loaded LM Studio model id")
    parser.add_argument("--whisper-model", default="large-v3", help="faster-whisper model name or local model folder")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--compute-type", default="int8", help="e.g. int8, float16, int8_float16")
    parser.add_argument("--font-size", type=int, default=9, help="Burned-in subtitle font size")
    parser.add_argument("--subtitle-font", default="Arial")
    parser.add_argument("--subtitle-size", type=int, default=50)
    parser.add_argument("--subtitle-color", default="#FFFFFF")
    parser.add_argument("--outline-color", default="#000000")
    parser.add_argument("--outline-width", type=int, default=10)
    parser.add_argument("--subtitle-bold", action="store_true")
    parser.add_argument("--subtitle-x", type=float, default=50)
    parser.add_argument("--subtitle-y", type=float, default=88)
    parser.add_argument("--source-language", default="zh", help="Whisper language code, or auto")
    parser.add_argument("--target-language", default="English", help="Translation target language")
    parser.add_argument("--no-vad", action="store_true", help="Disable the voice-activity filter; useful for sung or music-heavy audio that VAD cuts away")
    parser.add_argument("--vad-threshold", type=float, default=None, help="Silero VAD speech probability threshold (default 0.5); lower it to keep more of sung audio")
    parser.add_argument("--no-burn", action="store_true", help="Create SRT files only")
    args = parser.parse_args()

    if not args.video.is_file():
        parser.error(f"Video not found: {args.video}")
    if not args.render_srt and not args.render_ass and (not args.script or not args.script.is_file()):
        parser.error(f"Script not found: {args.script}")
    args.output.mkdir(parents=True, exist_ok=True)
    prefix = args.output_prefix or f"{args.video.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    translated_name = f"translated_{language_filename(args.target_language)}"

    if args.render_ass:
        if not args.render_ass.is_file():
            parser.error(f"ASS not found: {args.render_ass}")
        print("[4/4] Rendering edited ASS into MP4 …")
        burn_subtitles(args.video, args.render_ass, args.output / f"{prefix}_{translated_name}_subtitled.mp4")
        print(f"Done. Files are in: {args.output.resolve()}")
        return 0

    if args.render_srt:
        if not args.render_srt.is_file():
            parser.error(f"SRT not found: {args.render_srt}")
        print("[4/4] Rendering edited SRT into MP4 …")
        cues = read_srt_cues(args.render_srt)
        width, height = video_size(args.video)
        styled_ass = args.output / f"{prefix}_{translated_name}_styled.ass"
        write_ass(styled_ass, cues, width, height, args.subtitle_font, args.subtitle_size, args.subtitle_color, args.outline_color, args.outline_width, args.subtitle_bold, args.subtitle_x, args.subtitle_y)
        burn_subtitles(args.video, styled_ass, args.output / f"{prefix}_{translated_name}_subtitled.mp4")
        print(f"Done. Files are in: {args.output.resolve()}")
        return 0

    script_lines = read_script(args.script)
    source_language = None if args.source_language.lower() == "auto" else args.source_language
    asr = transcribe(args.video, args.whisper_model, args.device, args.compute_type, source_language, not args.no_vad, args.vad_threshold)
    write_srt(args.output / f"{prefix}_asr_raw_zh.srt", [Cue(x.start, x.end, x.text, x.text, [x.id], []) for x in asr], "zh")

    print(f"[2/4] Matching {len(script_lines)} script units to {len(asr)} spoken segments with LM Studio …")
    client = OpenAI(base_url=args.lm_url, api_key="lm-studio")
    prompt = make_prompt(script_lines, asr, args.source_language, args.target_language)
    cues: list[Cue] | None = None
    last_error: RuntimeError | None = None
    # Thinking models (e.g. Qwen MTP builds) can spend 10k-20k reasoning tokens
    # before any visible output, so the first budget must already clear that.
    for attempt, max_tokens in enumerate((16384, 32768), start=1):
        try:
            request_prompt = prompt
            if attempt > 1:
                request_prompt += "\n\nCRITICAL CORRECTION: Your previous response was incomplete. Rebuild the entire JSON from scratch and return valid JSON only."
            payload = response_json(client, args.model, request_prompt, max_tokens=max_tokens)
            cues = cues_from_model(payload, script_lines, asr)
            break
        except RuntimeError as error:
            last_error = error
            # Both wordings mean the JSON was not usable, so both deserve the
            # one retry with a larger output limit.
            incomplete = "returned invalid JSON" in str(error) or "did not return JSON" in str(error)
            if attempt == 1 and incomplete:
                print("[2/4] LM Studio returned an incomplete response; retrying with a larger output limit …")
                continue
            raise
    if cues is None:
        raise last_error or RuntimeError("LM Studio did not produce subtitle cues.")

    print("[3/4] Writing subtitle files …")
    write_srt(args.output / f"{prefix}_script_matched_zh.srt", cues, "zh")
    write_srt(args.output / f"{prefix}_{translated_name}.srt", cues, "en")
    (args.output / f"{prefix}_alignment.json").write_text(json.dumps([asdict(cue) for cue in cues], ensure_ascii=False, indent=2), encoding="utf-8")
    width, height = video_size(args.video)
    styled_ass = args.output / f"{prefix}_{translated_name}_styled.ass"
    write_ass(styled_ass, cues, width, height, args.subtitle_font, args.subtitle_size, args.subtitle_color, args.outline_color, args.outline_width, args.subtitle_bold, args.subtitle_x, args.subtitle_y)

    if not args.no_burn:
        burn_subtitles(args.video, styled_ass, args.output / f"{prefix}_{translated_name}_subtitled.mp4")
    print(f"Done. Files are in: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)

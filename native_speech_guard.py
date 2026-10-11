"""Targeted, non-blocking Whisper guard for unauthorized H3 speech gaps."""

from __future__ import annotations

from difflib import SequenceMatcher
import math
from pathlib import Path
import re
from typing import Any

from audio_engine import SAMPLE_RATE, decode_audio, voice_activity


_NON_WORD = re.compile(r"[^0-9A-Za-z\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]+")


class NativeSpeechGuard:
    """Transcribe only Timeline ranges where no human voice is authorized.

    The model is loaded lazily on CPU and kept for the lifetime of one render
    worker. A missing model or inference failure disables the guard for that
    take; it never blocks an otherwise completed render.
    """

    def __init__(self, model_path: str | Path, ffmpeg_path: str | Path):
        self.model_path = Path(model_path)
        self.ffmpeg_path = Path(ffmpeg_path)
        self._processor = None
        self._model = None
        self._torch = None
        self._disabled_reason = ""

    @property
    def available(self) -> bool:
        return self.model_path.is_dir() and not self._disabled_reason

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        if not self.model_path.is_dir():
            raise FileNotFoundError(f"Whisper model is missing: {self.model_path}")
        import torch
        from transformers import WhisperForConditionalGeneration, WhisperProcessor

        self._torch = torch
        self._processor = WhisperProcessor.from_pretrained(
            self.model_path, local_files_only=True
        )
        self._model = WhisperForConditionalGeneration.from_pretrained(
            self.model_path, local_files_only=True
        ).to("cpu").float()
        self._model.eval()

    @staticmethod
    def _meaningful_text(value: object) -> str:
        text = str(value or "").strip()
        normalized = _NON_WORD.sub("", text)
        if len(normalized) < 2:
            return ""
        # Whisper-small commonly hallucinates very short English tokens such
        # as "you" or "so" from impacts, breaths and room noise. They are not
        # reliable evidence of an invented spoken line. Two CJK characters are
        # already meaningful; Latin-only evidence must be at least four.
        if not re.search(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]", normalized):
            if len(normalized) < 4:
                return ""
        return text

    @staticmethod
    def _normalized_words(value: object) -> str:
        return _NON_WORD.sub("", str(value or "")).casefold()

    @staticmethod
    def _longest_non_overlapping_repeat(value: str) -> str:
        """Return the longest exact repeated fragment without overlapping itself."""
        best_start = 0
        best_size = 0
        length = len(value)
        for left in range(length):
            for right in range(left + 1, length):
                size = 0
                while (
                    right + size < length
                    and left + size < right
                    and value[left + size] == value[right + size]
                ):
                    size += 1
                if size > best_size:
                    best_start = left
                    best_size = size
        return value[best_start:best_start + best_size]

    @classmethod
    def line_fidelity_violation(
        cls,
        expected: object,
        transcript: object,
    ) -> dict[str, Any] | None:
        """Detect a repeated/extra phrase inside one authorized speech window.

        Whisper character substitutions are tolerated. The guard fires only
        when most of the authored line is present *and* the transcript carries
        a substantial repeated or additional phrase.
        """

        authored = cls._normalized_words(expected)
        heard = cls._normalized_words(transcript)
        if len(authored) < 2 or len(heard) < 2:
            return None
        matcher = SequenceMatcher(None, authored, heard, autojunk=False)
        matched = sum(block.size for block in matcher.get_matching_blocks())
        coverage = matched / max(1, len(authored))
        excess = max(0, len(heard) - matched)
        repeated = cls._longest_non_overlapping_repeat(heard)
        repeat_threshold = max(4, min(8, math.ceil(len(authored) * 0.35)))
        has_new_repeat = (
            len(repeated) >= repeat_threshold
            and authored.count(repeated) < 2
            and len(heard) >= math.ceil(len(authored) * 1.15)
        )
        has_material_extra = (
            coverage >= 0.65
            and excess >= max(4, math.ceil(len(authored) * 0.22))
            and len(heard) >= math.ceil(len(authored) * 1.20)
        )
        if not has_new_repeat and not has_material_extra:
            return None
        return {
            "kind": (
                "repeated_authored_phrase"
                if has_new_repeat
                else "unauthorized_extra_inside_authored_window"
            ),
            "coverage": round(coverage, 4),
            "excess_characters": excess,
            "repeated_fragment": repeated if has_new_repeat else "",
        }

    def _transcribe_window(
        self,
        media: str | Path,
        runtime: Any,
        start: float,
        end: float,
    ) -> tuple[str, float]:
        samples = decode_audio(
            media,
            runtime,
            start_seconds=start,
            duration_seconds=end - start,
        )
        if len(samples) < SAMPLE_RATE // 2:
            return "", 0.0
        vad = voice_activity(samples)
        voice_ratio = float(vad.get("voice_ratio", 0.0))
        if not vad.get("segments") or voice_ratio < 0.035:
            return "", voice_ratio
        inputs = self._processor(samples, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        with self._torch.inference_mode():
            predicted = self._model.generate(
                inputs.input_features.to("cpu"),
                task="transcribe",
                max_new_tokens=96,
            )
        transcript = self._processor.batch_decode(
            predicted, skip_special_tokens=True
        )[0].strip()
        return self._meaningful_text(transcript), voice_ratio

    def inspect(self, media: str | Path, spec: dict[str, Any]) -> dict[str, Any]:
        windows = [
            row for row in (spec.get("silence_windows") or [])
            if isinstance(row, (list, tuple)) and len(row) >= 2
            and float(row[1]) - float(row[0]) >= 0.45
        ]
        result: dict[str, Any] = {
            "enabled": bool(spec.get("enabled", False)),
            "passed": True,
            "violations": [],
            "checked_windows": windows,
            "checked_lines": [],
            "engine": "whisper-small-cpu",
        }
        line_specs = [
            row for row in (spec.get("authorized_lines") or [])
            if isinstance(row, dict)
            and float(row.get("end_seconds", 0.0))
            - float(row.get("start_seconds", 0.0)) >= 0.45
            and str(row.get("text", "")).strip()
        ]
        if not result["enabled"] or (not windows and not line_specs):
            return result
        overlapping_line_indexes: set[int] = set()
        duplicate_unison_indexes: set[int] = set()
        for left_index, left in enumerate(line_specs):
            left_start = float(left.get("start_seconds", 0.0))
            left_end = float(left.get("end_seconds", left_start))
            for right_index in range(left_index + 1, len(line_specs)):
                right = line_specs[right_index]
                right_start = float(right.get("start_seconds", 0.0))
                right_end = float(right.get("end_seconds", right_start))
                authored_overlap = (
                    str(left.get("overlap_policy", "auto")).strip().casefold()
                    == "overlap"
                    or str(right.get("overlap_policy", "auto")).strip().casefold()
                    == "overlap"
                )
                if (
                    authored_overlap
                    and min(left_end, right_end) - max(left_start, right_start) > 0.10
                ):
                    same_unison_line = (
                        self._normalized_words(left.get("text", ""))
                        == self._normalized_words(right.get("text", ""))
                        and abs(left_start - right_start) <= 1e-6
                        and abs(left_end - right_end) <= 1e-6
                    )
                    if same_unison_line:
                        duplicate_unison_indexes.add(right_index)
                    else:
                        overlapping_line_indexes.update((left_index, right_index))
        try:
            self._ensure_model()
            from runtime_paths import RuntimePaths

            runtime = RuntimePaths(
                python=Path(),
                ffmpeg=self.ffmpeg_path,
                ffprobe=self.ffmpeg_path.with_name("ffprobe.exe"),
                blip_model_cache=Path(),
                blip_snapshot=Path(),
                blip_model_id="",
                speech_model=self.model_path,
            )
            for raw_start, raw_end in windows:
                start = max(0.0, float(raw_start))
                end = max(start, float(raw_end))
                transcript, voice_ratio = self._transcribe_window(
                    media, runtime, start, end
                )
                if transcript:
                    result["violations"].append({
                        "kind": "unauthorized_speech_in_silence_window",
                        "start_seconds": round(start, 3),
                        "end_seconds": round(end, 3),
                        "transcript": transcript,
                        "voice_ratio": voice_ratio,
                    })
            for line_index, row in enumerate(line_specs):
                start = max(0.0, float(row.get("start_seconds", 0.0)))
                end = max(start, float(row.get("end_seconds", start)))
                if line_index in overlapping_line_indexes:
                    result["checked_lines"].append({
                        "layer_id": str(row.get("layer_id", "")),
                        "start_seconds": round(start, 3),
                        "end_seconds": round(end, 3),
                        "expected": str(row.get("text", "")),
                        "transcript": "",
                        "voice_ratio": 0.0,
                        "fidelity_check_skipped": "authored_overlap",
                    })
                    continue
                if line_index in duplicate_unison_indexes:
                    result["checked_lines"].append({
                        "layer_id": str(row.get("layer_id", "")),
                        "start_seconds": round(start, 3),
                        "end_seconds": round(end, 3),
                        "expected": str(row.get("text", "")),
                        "transcript": "",
                        "voice_ratio": 0.0,
                        "fidelity_check_skipped": "same_line_unison_checked_once",
                    })
                    continue
                transcript, voice_ratio = self._transcribe_window(
                    media, runtime, start, end
                )
                check = {
                    "layer_id": str(row.get("layer_id", "")),
                    "start_seconds": round(start, 3),
                    "end_seconds": round(end, 3),
                    "expected": str(row.get("text", "")),
                    "transcript": transcript,
                    "voice_ratio": voice_ratio,
                }
                result["checked_lines"].append(check)
                violation = self.line_fidelity_violation(row.get("text", ""), transcript)
                if violation is None and transcript:
                    authored = self._normalized_words(row.get("text", ""))
                    heard = self._normalized_words(transcript)
                    matcher = SequenceMatcher(None, authored, heard, autojunk=False)
                    matched = sum(block.size for block in matcher.get_matching_blocks())
                    coverage = matched / max(1, len(authored))
                    if (
                        len(authored) >= 4
                        and len(heard) >= 4
                        and voice_ratio >= 0.06
                        and coverage < 0.42
                    ):
                        violation = {
                            "kind": "materially_changed_or_unrelated_authored_line",
                            "coverage": round(coverage, 4),
                            "excess_characters": max(0, len(heard) - matched),
                            "repeated_fragment": "",
                        }
                if violation:
                    result["violations"].append({**check, **violation})
            result["passed"] = not bool(result["violations"])
        except Exception as exc:
            self._disabled_reason = f"{type(exc).__name__}: {exc}"
            result.update(
                passed=True,
                available=False,
                warning=(
                    "Native speech guard unavailable; render was not blocked: "
                    + self._disabled_reason
                ),
            )
        return result

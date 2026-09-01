"""Dependency-light beat and voice-activity analysis for audio and video files."""

from __future__ import annotations

from pathlib import Path
from difflib import SequenceMatcher
import re
import subprocess

import numpy as np

from runtime_paths import RuntimePaths, load_runtime_paths


SAMPLE_RATE = 16_000


def decode_audio(
    path: str | Path,
    runtime: RuntimePaths | None = None,
    *,
    start_seconds: float = 0.0,
    duration_seconds: float | None = None,
) -> np.ndarray:
    """Decode one bounded mono PCM window instead of loading a whole long file."""
    runtime = runtime or load_runtime_paths()
    command = [
        str(runtime.ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{max(0.0, start_seconds):.3f}",
        "-i",
        str(path),
        "-vn",
    ]
    if duration_seconds is not None:
        command.extend(["-t", f"{max(0.05, duration_seconds):.3f}"])
    command.extend(
        [
            "-ac",
            "1",
            "-ar",
            str(SAMPLE_RATE),
            "-f",
            "f32le",
            "pipe:1",
        ]
    )
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(detail or "Unable to decode the audio stream")
    return np.frombuffer(result.stdout, dtype=np.float32).copy()


def voice_activity(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> dict:
    frame_size = max(1, round(sample_rate * 0.03))
    usable = len(samples) // frame_size * frame_size
    if usable == 0:
        return {"segments": [], "voice_ratio": 0.0, "threshold": 0.0}
    frames = samples[:usable].reshape(-1, frame_size)
    rms = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
    noise = float(np.percentile(rms, 25))
    peak = float(np.percentile(rms, 95))
    threshold = max(0.004, noise * 2.6, peak * 0.075)
    active = rms >= threshold
    if len(active) >= 5:
        active = np.convolve(active.astype(np.int8), np.ones(5, dtype=np.int8), mode="same") >= 2

    raw_segments: list[list[float]] = []
    start: int | None = None
    for index, is_active in enumerate(active):
        if is_active and start is None:
            start = index
        if start is not None and (not is_active or index == len(active) - 1):
            stop = index + 1 if is_active else index
            begin_s, end_s = start * 0.03, stop * 0.03
            if end_s - begin_s >= 0.18:
                raw_segments.append([begin_s, end_s])
            start = None

    merged: list[list[float]] = []
    for segment in raw_segments:
        if merged and segment[0] - merged[-1][1] <= 0.30:
            merged[-1][1] = segment[1]
        else:
            merged.append(segment)
    voiced = sum(end - start for start, end in merged)
    duration = len(samples) / sample_rate
    return {
        "segments": [[round(start, 3), round(end, 3)] for start, end in merged],
        "voice_ratio": round(voiced / duration, 4) if duration else 0.0,
        "threshold": threshold,
    }


def estimate_tempo(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> dict:
    frame_size, hop = 1024, 256
    if len(samples) < frame_size * 4:
        return {"bpm": None, "confidence": 0.0}
    count = 1 + (len(samples) - frame_size) // hop
    energy = np.empty(count, dtype=np.float32)
    window = np.hanning(frame_size).astype(np.float32)
    for index in range(count):
        frame = samples[index * hop : index * hop + frame_size] * window
        energy[index] = np.sqrt(np.mean(frame * frame) + 1e-12)
    onset = np.maximum(0.0, np.diff(energy, prepend=energy[0]))
    onset -= onset.mean()
    if float(np.max(np.abs(onset))) < 1e-5:
        return {"bpm": None, "confidence": 0.0}
    # FFT autocorrelation is O(n log n); np.correlate becomes prohibitively slow
    # for long media even when decoding happens outside the UI process.
    fft_size = 1 << max(1, (2 * len(onset) - 1).bit_length())
    spectrum = np.fft.rfft(onset, fft_size)
    correlation = np.fft.irfft(spectrum * np.conjugate(spectrum), fft_size)[: len(onset)]
    envelope_rate = sample_rate / hop
    min_lag = max(1, round(envelope_rate * 60 / 200))
    max_lag = min(len(correlation) - 1, round(envelope_rate * 60 / 55))
    if max_lag <= min_lag or correlation[0] <= 0:
        return {"bpm": None, "confidence": 0.0}
    lag = min_lag + int(np.argmax(correlation[min_lag : max_lag + 1]))
    bpm = 60 * envelope_rate / lag
    while bpm < 70:
        bpm *= 2
    while bpm > 180:
        bpm /= 2
    confidence = max(0.0, min(1.0, float(correlation[lag] / correlation[0])))
    return {"bpm": round(bpm, 1), "confidence": round(confidence, 3)}


def analyze_audio(path: str | Path, runtime: RuntimePaths | None = None) -> dict:
    samples = decode_audio(path, runtime)
    vad = voice_activity(samples)
    tempo = estimate_tempo(samples)
    return {
        "samples": samples,
        "sample_rate": SAMPLE_RATE,
        "duration": round(len(samples) / SAMPLE_RATE, 3),
        "vad": vad,
        "tempo": tempo,
    }


def stream_audio_chunks(
    path: str | Path,
    max_seconds: float,
    runtime: RuntimePaths | None = None,
    *,
    chunk_seconds: float = 8.0,
):
    """Yield 5-10 second PCM windows, stopping at the Timeline duration."""
    runtime = runtime or load_runtime_paths()
    limit = max(0.05, float(max_seconds))
    chunk_seconds = min(10.0, max(5.0, float(chunk_seconds)))
    offset = 0.0
    while offset < limit - 1e-6:
        requested = min(chunk_seconds, limit - offset)
        samples = decode_audio(
            path,
            runtime,
            start_seconds=offset,
            duration_seconds=requested,
        )
        if not len(samples):
            break
        yield offset, samples
        decoded_seconds = len(samples) / SAMPLE_RATE
        offset += requested
        if decoded_seconds + 0.05 < requested:
            break


def audio_analysis_summary(result: dict) -> str:
    tempo = result["tempo"]
    vad = result["vad"]
    bpm = f"{tempo['bpm']:.1f} BPM" if tempo.get("bpm") else "not confidently detected"
    segments = vad.get("segments", [])
    segment_text = ", ".join(f"{start:.2f}-{end:.2f}s" for start, end in segments[:12]) or "none"
    if len(segments) > 12:
        segment_text += f" … +{len(segments) - 12}"
    return (
        "\n\nAUDIO INTELLIGENCE"
        f"\nBeat estimate: {bpm} · confidence {tempo.get('confidence', 0):.2f}"
        f"\nVAD voice ratio: {vad.get('voice_ratio', 0) * 100:.1f}%"
        f"\nVoice-active ranges: {segment_text}"
    )


def ambient_presence(
    samples: np.ndarray,
    vad_segments: list[list[float]] | None = None,
    sample_rate: int = SAMPLE_RATE,
) -> dict:
    """Estimate whether unchanged generated audio contains a non-speech bed.

    This is analysis only.  No denoising, gain, filtering, or resynthesis is
    performed.  The result is deliberately conservative because quiet rooms
    may have a very low but still valid location bed.
    """
    if not len(samples):
        return {"present": False, "nonvoice_rms": 0.0, "overall_rms": 0.0}
    overall_rms = float(np.sqrt(np.mean(samples * samples) + 1e-12))
    mask = np.ones(len(samples), dtype=bool)
    for start, end in vad_segments or []:
        left = max(0, min(len(mask), int(float(start) * sample_rate)))
        right = max(left, min(len(mask), int(float(end) * sample_rate)))
        mask[left:right] = False
    nonvoice = samples[mask]
    nonvoice_rms = (
        float(np.sqrt(np.mean(nonvoice * nonvoice) + 1e-12))
        if len(nonvoice) >= sample_rate // 10 else 0.0
    )
    return {
        "present": bool(nonvoice_rms >= 0.00045 or overall_rms >= 0.0025),
        "nonvoice_rms": round(nonvoice_rms, 7),
        "overall_rms": round(overall_rms, 7),
    }


def _normalized_words(value: object) -> str:
    return re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", str(value or "").lower())


def evaluate_native_audio_qc(
    expected_dialogue: list[str],
    transcript: str,
    vad: dict,
    ambient: dict,
) -> dict:
    """Evaluate H3's untouched generated soundtrack against Timeline intent."""
    expected = [_normalized_words(item) for item in expected_dialogue if _normalized_words(item)]
    heard = _normalized_words(re.sub(r"\[[^\]]+\]", "", transcript or ""))
    missing: list[str] = []
    for raw, normalized in zip(
        [item for item in expected_dialogue if _normalized_words(item)], expected,
    ):
        if normalized not in heard and SequenceMatcher(None, normalized, heard).ratio() < 0.55:
            missing.append(raw)
    if expected:
        authorized_text = "".join(expected)
        similarity = SequenceMatcher(None, authorized_text, heard).ratio() if heard else 0.0
        extra_dialogue = bool(heard and authorized_text not in heard and similarity < 0.52 and len(heard) > len(authorized_text) * 1.12)
    else:
        extra_dialogue = bool(heard or float(vad.get("voice_ratio", 0.0) or 0.0) > 0.025)
    ambience_missing = not bool(ambient.get("present", False))
    warnings: list[str] = []
    if missing:
        warnings.append(f"missing or materially changed authored line(s): {len(missing)}")
    if extra_dialogue:
        warnings.append("unauthorized extra dialogue may be present")
    if ambience_missing:
        warnings.append("continuous environment sound may be missing")
    status = "PASS" if not warnings else "WARNING"
    return {
        "status": status,
        "target_dialogue_present": not missing,
        "unauthorized_extra_dialogue": extra_dialogue,
        "environment_sound_missing": ambience_missing,
        "missing_dialogue": missing,
        "message": (
            "Native Audio QC PASS · exact dialogue/voice authorization and environment bed look consistent."
            if not warnings
            else "Native Audio QC WARNING · " + "; ".join(warnings) + ". Regenerate if the audible result confirms this."
        ),
    }

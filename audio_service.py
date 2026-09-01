"""Persistent beat, VAD and offline Whisper transcription service."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys

from audio_engine import (
    SAMPLE_RATE,
    ambient_presence,
    audio_analysis_summary,
    estimate_tempo,
    stream_audio_chunks,
    voice_activity,
)


def _timecode(seconds: float) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes):02d}:{secs:05.2f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    from runtime_paths import RuntimePaths
    runtime = RuntimePaths(
        python=Path(sys.executable),
        ffmpeg=Path(args.ffmpeg),
        ffprobe=Path(args.ffmpeg).with_name("ffprobe.exe"),
        blip_model_cache=Path(),
        blip_snapshot=Path(),
        blip_model_id="",
        speech_model=Path(args.model),
    )
    processor = model = torch = None
    device = "cpu"
    print(json.dumps({"ready": True, "engine": "beat+vad"}), flush=True)

    for raw in sys.stdin:
        job: dict = {}
        try:
            job = json.loads(raw)
            max_seconds = max(0.05, float(job.get("max_seconds", 60.0)))
            chunk_seconds = min(10.0, max(5.0, float(job.get("chunk_seconds", 8.0))))
            expected_chunks = max(1, math.ceil(max_seconds / chunk_seconds))
            all_segments: list[list[float]] = []
            tempo_candidates: list[dict] = []
            transcript_rows: list[str] = []
            decoded_seconds = 0.0
            voiced_seconds = 0.0
            ambient_weighted_rms = 0.0
            ambient_sample_seconds = 0.0
            ambient_detected = False
            for chunk_index, (offset, samples) in enumerate(
                stream_audio_chunks(
                    job["media"],
                    max_seconds,
                    runtime,
                    chunk_seconds=chunk_seconds,
                ),
                1,
            ):
                local_duration = len(samples) / SAMPLE_RATE
                decoded_seconds += local_duration
                local_vad = voice_activity(samples)
                local_segments = local_vad["segments"]
                local_ambient = ambient_presence(samples, local_segments)
                ambient_detected = ambient_detected or bool(local_ambient["present"])
                ambient_weighted_rms += float(local_ambient["nonvoice_rms"]) * local_duration
                ambient_sample_seconds += local_duration
                for start, end in local_segments:
                    all_segments.append([round(offset + start, 3), round(offset + end, 3)])
                    voiced_seconds += end - start
                tempo_candidates.append(estimate_tempo(samples))

                if local_segments:
                    if model is None:
                        import torch as torch_module
                        from transformers import WhisperForConditionalGeneration, WhisperProcessor

                        torch = torch_module
                        processor = WhisperProcessor.from_pretrained(args.model, local_files_only=True)
                        model = WhisperForConditionalGeneration.from_pretrained(args.model, local_files_only=True)
                        if not args.cpu and torch.cuda.is_available():
                            try:
                                model = model.to("cuda").half()
                                device = "cuda"
                            except RuntimeError:
                                model = model.to("cpu").float()
                                device = "cpu"
                        model.eval()
                        print(json.dumps({"speech_ready": True, "device": device}), flush=True)

                    for start, end in local_segments:
                        padded_start = max(0.0, start - 0.20)
                        padded_end = min(local_duration, end + 0.20)
                        clip = samples[
                            int(padded_start * SAMPLE_RATE) : int(padded_end * SAMPLE_RATE)
                        ]
                        if len(clip) < SAMPLE_RATE // 2 or float(abs(clip).mean()) < 0.002:
                            continue
                        inputs = processor(clip, sampling_rate=SAMPLE_RATE, return_tensors="pt")
                        features = inputs.input_features.to(device)
                        if device == "cuda":
                            features = features.half()
                        try:
                            with torch.inference_mode():
                                predicted = model.generate(features, task="transcribe", max_new_tokens=160)
                        except RuntimeError:
                            if device != "cuda":
                                raise
                            model = model.to("cpu").float()
                            device = "cpu"
                            features = inputs.input_features.to("cpu")
                            with torch.inference_mode():
                                predicted = model.generate(features, task="transcribe", max_new_tokens=160)
                        text = processor.batch_decode(predicted, skip_special_tokens=True)[0].strip()
                        if text:
                            transcript_rows.append(f"[{_timecode(offset + start)}] {text}")

                print(
                    json.dumps(
                        {
                            "job": job["job"],
                            "progress": min(0.99, chunk_index / expected_chunks),
                            "decoded_seconds": round(decoded_seconds, 3),
                            "max_seconds": max_seconds,
                        }
                    ),
                    flush=True,
                )

            confident_tempos = [item for item in tempo_candidates if item.get("bpm")]
            if confident_tempos:
                best_tempo = max(confident_tempos, key=lambda item: item.get("confidence", 0.0))
            else:
                best_tempo = {"bpm": None, "confidence": 0.0}
            analysis = {
                "duration": round(decoded_seconds, 3),
                "tempo": best_tempo,
                "vad": {
                    "segments": all_segments,
                    "voice_ratio": round(voiced_seconds / decoded_seconds, 4) if decoded_seconds else 0.0,
                    "threshold": 0.0,
                },
                "ambient": {
                    "present": ambient_detected,
                    "nonvoice_rms": round(
                        ambient_weighted_rms / ambient_sample_seconds, 7
                    ) if ambient_sample_seconds else 0.0,
                },
            }
            summary = audio_analysis_summary(analysis)
            print(
                json.dumps(
                    {
                        "job": job["job"],
                        "summary": summary,
                        "tempo": analysis["tempo"],
                        "vad": analysis["vad"],
                        "ambient": analysis["ambient"],
                        "transcript": "\n".join(transcript_rows),
                        "speech_device": device,
                        "decoded_seconds": round(decoded_seconds, 3),
                        "max_seconds": max_seconds,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        except Exception as exc:
            print(json.dumps({"job": job.get("job", ""), "error": str(exc)}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            json.dumps({"fatal": True, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False),
            flush=True,
        )
        raise SystemExit(1)

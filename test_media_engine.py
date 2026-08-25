from pathlib import Path
import unittest

import numpy as np
from PIL import Image

from audio_engine import SAMPLE_RATE, estimate_tempo, stream_audio_chunks, voice_activity
from media_engine import (
    create_image_analysis_regions,
    create_video_analysis_frames,
    media_type_for_path,
    probe_media,
)
from runtime_paths import PROJECT_ROOT, load_runtime_paths


class MediaEngineTests(unittest.TestCase):
    def test_common_runtime_is_self_contained(self):
        runtime = load_runtime_paths()
        self.assertEqual(runtime.missing(), [])
        self.assertTrue(runtime.python.is_file())
        self.assertTrue(runtime.ffmpeg.is_file())
        self.assertTrue(runtime.blip_snapshot.is_dir())
        self.assertTrue(runtime.speech_model.is_dir())

    def test_media_extension_routing(self):
        self.assertEqual(media_type_for_path("frame.webp"), "image")
        self.assertEqual(media_type_for_path("motion.MP4"), "video")
        self.assertEqual(media_type_for_path("dialogue.wav"), "audio")
        self.assertIsNone(media_type_for_path("notes.txt"))

    def test_probe_generated_runtime_samples(self):
        root = PROJECT_ROOT / ".director_cache" / "runtime_smoke"
        image, video, audio = root / "sample.png", root / "sample.mp4", root / "sample.wav"
        if not all(path.exists() for path in (image, video, audio)):
            self.skipTest("runtime smoke assets are not present")
        self.assertEqual(probe_media(image)["width"], 640)
        self.assertAlmostEqual(probe_media(video)["duration"], 1.5, places=1)
        self.assertAlmostEqual(probe_media(audio)["duration"], 1.5, places=1)

    def test_three_temporal_video_frames_are_extracted(self):
        source = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "sample.mp4"
        if not source.exists():
            self.skipTest("runtime smoke video is not present")
        target = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "three_frames"
        frames = create_video_analysis_frames(source, target, 1.5)
        self.assertEqual(len(frames), 3)
        self.assertTrue(all(path.is_file() for _, path in frames))
        self.assertIn("10%", frames[0][0])
        self.assertIn("90%", frames[-1][0])

    def test_image_analysis_regions_include_overlay_resistant_scene_crops(self):
        root = PROJECT_ROOT / ".director_cache" / "image_region_test"
        root.mkdir(parents=True, exist_ok=True)
        source = root / "portrait_with_lower_title.png"
        Image.new("RGB", (400, 600), (12, 42, 68)).save(source)
        target = root / "regions"

        regions = create_image_analysis_regions(source, target)

        self.assertEqual(len(regions), 4)
        self.assertEqual(regions[0], ("full frame", source))
        self.assertTrue(all(path.is_file() for _label, path in regions))
        self.assertTrue(any("lower titles" in label for label, _path in regions))
        self.assertTrue(any("edge overlays" in label for label, _path in regions))
        for _label, path in regions[1:]:
            path.unlink(missing_ok=True)
        target.rmdir()
        source.unlink(missing_ok=True)
        root.rmdir()

    def test_tempo_estimator_finds_synthetic_120_bpm_clicks(self):
        samples = np.zeros(SAMPLE_RATE * 10, dtype=np.float32)
        for position in range(0, len(samples), SAMPLE_RATE // 2):
            samples[position : position + 200] = np.linspace(1.0, 0.0, 200, dtype=np.float32)
        result = estimate_tempo(samples)
        self.assertIsNotNone(result["bpm"])
        self.assertGreater(result["bpm"], 105)
        self.assertLess(result["bpm"], 135)

    def test_vad_finds_generated_speech(self):
        source = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "speech.wav"
        if not source.exists():
            self.skipTest("runtime smoke speech is not present")
        from audio_engine import decode_audio

        result = voice_activity(decode_audio(source))
        self.assertGreater(result["voice_ratio"], 0.4)
        self.assertGreaterEqual(len(result["segments"]), 1)

    def test_streaming_audio_never_decodes_beyond_timeline_limit(self):
        source = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "sample.wav"
        if not source.exists():
            self.skipTest("runtime smoke audio is not present")
        chunks = list(stream_audio_chunks(source, 1.0, chunk_seconds=8.0))
        self.assertEqual(len(chunks), 1)
        decoded_seconds = sum(len(samples) / SAMPLE_RATE for _, samples in chunks)
        self.assertLessEqual(decoded_seconds, 1.02)
        self.assertAlmostEqual(chunks[0][0], 0.0)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest

from settings_engine import RenderSettings, load_settings, save_settings


class SettingsEngineTests(unittest.TestCase):
    def test_env_round_trip_preserves_unrelated_values(self):
        cache = Path(__file__).parent / ".director_cache"
        cache.mkdir(exist_ok=True)
        path = cache / "settings_engine_test.env"
        path.write_text("UNRELATED=keep\nH3_MEGAPIXELS=0.5\n", encoding="utf-8")
        settings = RenderSettings(
            aspect_ratio="9:16",
            megapixels=1.25,
            sampling_steps=12,
            denoise=0.8,
            rtx_video_super_resolution=False,
            history_poll_interval=2.5,
            generation_timeout=900,
            http_request_timeout=45,
        )
        save_settings(path, settings)
        restored = load_settings(path)
        self.assertEqual(restored.aspect_ratio, "9:16")
        self.assertEqual(restored.megapixels, 1.25)
        self.assertEqual(restored.sampling_steps, 12)
        self.assertFalse(restored.rtx_video_super_resolution)
        self.assertIn("UNRELATED=keep", path.read_text(encoding="utf-8"))

    def test_invalid_ranges_are_clamped(self):
        settings = RenderSettings.from_mapping(
            {"megapixels": 0, "denoise": 5, "generation_timeout": 1}
        )
        self.assertEqual(settings.megapixels, 0.1)
        self.assertEqual(settings.denoise, 1.0)
        self.assertEqual(settings.generation_timeout, 10)


if __name__ == "__main__":
    unittest.main()

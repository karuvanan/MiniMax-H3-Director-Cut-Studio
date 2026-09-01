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
            dialogue_tts_engine="voxcpm2_local",
            music_mode="timeline",
            blip_device="cuda",
            workspace_free_disk_reserve_gb=75.0,
        )
        save_settings(path, settings)
        restored = load_settings(path)
        self.assertEqual(restored.aspect_ratio, "9:16")
        self.assertEqual(restored.megapixels, 1.25)
        self.assertEqual(restored.sampling_steps, 12)
        self.assertFalse(restored.rtx_video_super_resolution)
        self.assertEqual(restored.dialogue_tts_engine, "voxcpm2_local")
        self.assertEqual(restored.music_mode, "timeline")
        self.assertEqual(restored.blip_device, "cuda")
        self.assertEqual(restored.workspace_free_disk_reserve_gb, 75.0)
        self.assertIn(
            "H3_DIALOGUE_TTS_ENGINE=voxcpm2_local",
            path.read_text(encoding="utf-8"),
        )
        self.assertIn("H3_MUSIC_MODE=timeline", path.read_text(encoding="utf-8"))
        self.assertIn("H3_BLIP_DEVICE=cuda", path.read_text(encoding="utf-8"))
        self.assertIn(
            "H3_WORKSPACE_FREE_DISK_RESERVE_GB=75.0",
            path.read_text(encoding="utf-8"),
        )
        self.assertIn("UNRELATED=keep", path.read_text(encoding="utf-8"))

    def test_invalid_ranges_are_clamped(self):
        settings = RenderSettings.from_mapping(
            {"megapixels": 0, "denoise": 5, "generation_timeout": 1}
        )
        self.assertEqual(settings.megapixels, 0.1)
        self.assertEqual(settings.denoise, 1.0)
        self.assertEqual(settings.generation_timeout, 10)

    def test_unknown_tts_engine_returns_to_safe_default(self):
        settings = RenderSettings.from_mapping({"dialogue_tts_engine": "mystery"})
        self.assertEqual(settings.dialogue_tts_engine, "h3_native")

    def test_native_h3_dialogue_is_the_default_and_valid_choice(self):
        self.assertEqual(RenderSettings.defaults().dialogue_tts_engine, "h3_native")
        self.assertEqual(
            RenderSettings.from_mapping({"dialogue_tts_engine": "h3_native"}).dialogue_tts_engine,
            "h3_native",
        )

    def test_music_mode_defaults_to_auto_and_rejects_unknown_values(self):
        self.assertEqual(RenderSettings.defaults().music_mode, "auto")
        self.assertEqual(
            RenderSettings.from_mapping({"music_mode": "timeline"}).music_mode,
            "timeline",
        )
        self.assertEqual(
            RenderSettings.from_mapping({"music_mode": "mystery"}).music_mode,
            "auto",
        )

    def test_qwen3_tts_local_is_a_valid_persistent_engine(self):
        self.assertEqual(
            RenderSettings.from_mapping(
                {"dialogue_tts_engine": "qwen3_tts_local"}
            ).dialogue_tts_engine,
            "qwen3_tts_local",
        )

    def test_blip_device_defaults_to_safe_auto(self):
        self.assertEqual(RenderSettings.defaults().blip_device, "auto")
        self.assertEqual(
            RenderSettings.from_mapping({"blip_device": "mystery"}).blip_device,
            "auto",
        )


if __name__ == "__main__":
    unittest.main()

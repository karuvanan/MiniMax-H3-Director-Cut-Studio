"""Tests for the Studio-managed SoulX unload/lazy-reload boundary."""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from soulx_server import _call_upstream_start_svc, _wrap_start_svc, release_soulx_models


class SoulXServerTest(unittest.TestCase):
    def test_wrapper_preserves_name_and_forwards_extended_parameters(self) -> None:
        calls = []

        def _start_svc(value, device_choice="auto", use_fp16=False):
            return value, device_choice, use_fp16

        wrapped = _wrap_start_svc(_start_svc, lambda: calls.append("loaded"))
        self.assertEqual(wrapped.__name__, "_start_svc")
        self.assertEqual(wrapped("audio", "cuda", True), ("audio", "cuda", True))
        self.assertEqual(calls, ["loaded"])

    def test_wrapper_serializes_load_and_inference_when_lock_is_supplied(self) -> None:
        events = []

        class Lock:
            def __enter__(self):
                events.append("lock")

            def __exit__(self, _kind, _value, _traceback):
                events.append("unlock")

        wrapped = _wrap_start_svc(
            lambda: events.append("inference"),
            lambda: events.append("load"),
            Lock(),
        )
        wrapped()
        self.assertEqual(events, ["lock", "load", "inference", "unlock"])

    def test_stable_dispatch_supports_official_ten_parameter_callback(self) -> None:
        def _start_svc(
            prompt_audio,
            target_audio,
            prompt_vocal_sep,
            target_vocal_sep,
            auto_shift,
            auto_mix_acc,
            pitch_shift,
            n_step,
            cfg,
            seed,
        ):
            return pitch_shift, n_step, cfg, seed

        values = {
            "prompt_audio": "voice.wav",
            "target_audio": "song.wav",
            "prompt_vocal_sep": False,
            "target_vocal_sep": True,
            "auto_shift": True,
            "auto_mix_acc": True,
            "device_choice": "cuda",
            "use_fp16": True,
            "pitch_shift": 0,
            "n_step": 32,
            "cfg": 1.0,
            "seed": 42,
        }
        self.assertEqual(
            _call_upstream_start_svc(_start_svc, values),
            (0, 32, 1.0, 42),
        )

    def test_stable_dispatch_supports_extended_twelve_parameter_callback(self) -> None:
        def _start_svc(
            prompt_audio,
            target_audio,
            prompt_vocal_sep,
            target_vocal_sep,
            auto_shift,
            auto_mix_acc,
            device_choice,
            use_fp16,
            pitch_shift,
            n_step,
            cfg,
            seed,
        ):
            return device_choice, use_fp16, pitch_shift, seed

        values = {
            "prompt_audio": "voice.wav",
            "target_audio": "song.wav",
            "prompt_vocal_sep": False,
            "target_vocal_sep": True,
            "auto_shift": True,
            "auto_mix_acc": True,
            "device_choice": "cuda",
            "use_fp16": True,
            "pitch_shift": 0,
            "n_step": 32,
            "cfg": 1.0,
            "seed": 42,
        }
        self.assertEqual(
            _call_upstream_start_svc(_start_svc, values),
            ("cuda", True, 0, 42),
        )

    @patch("soulx_server._clear_device_cache", return_value=True)
    def test_release_drops_svc_and_preprocess_state(self, _cache) -> None:
        state = SimpleNamespace(
            svc_model=object(),
            preprocess_pipeline=object(),
            device="cuda:0",
            svc_config=object(),
        )
        upstream = SimpleNamespace(APP_STATE=state)
        result = release_soulx_models(upstream)
        self.assertIsNone(upstream.APP_STATE)
        self.assertIsNone(state.svc_model)
        self.assertIsNone(state.preprocess_pipeline)
        self.assertIsNone(state.device)
        self.assertIsNone(state.svc_config)
        self.assertIn("svc_model", result["released_attributes"])
        self.assertTrue(result["model_was_loaded"])
        self.assertTrue(result["lazy_reload"])
        self.assertTrue(result["device_cache_cleared"])


if __name__ == "__main__":
    unittest.main()

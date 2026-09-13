"""Tests for the Studio-managed SoulX unload/lazy-reload boundary."""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from functools import wraps
from unittest.mock import patch

from soulx_server import release_soulx_models


class SoulXServerTest(unittest.TestCase):
    def test_wraps_preserves_canonical_svc_callback_name(self) -> None:
        def _start_svc(value):
            return value

        @wraps(_start_svc)
        def lazy_start_svc(value):
            return _start_svc(value)

        self.assertEqual(lazy_start_svc.__name__, "_start_svc")

    @patch("soulx_server._clear_device_cache", return_value=True)
    def test_release_drops_svc_and_preprocess_state(self, _cache) -> None:
        state = SimpleNamespace(svc_model=object(), preprocess_pipeline=object())
        upstream = SimpleNamespace(APP_STATE=state)
        result = release_soulx_models(upstream)
        self.assertIsNone(upstream.APP_STATE)
        self.assertIsNone(state.svc_model)
        self.assertIsNone(state.preprocess_pipeline)
        self.assertTrue(result["model_was_loaded"])
        self.assertTrue(result["lazy_reload"])
        self.assertTrue(result["device_cache_cleared"])


if __name__ == "__main__":
    unittest.main()

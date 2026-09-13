"""Tests for ACE-Step Client/Server mode detection."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ace_step_runtime import (
    LOCAL_ACE_SERVER,
    REMOTE_ACE_SERVER,
    _parse_vram_output,
    detect_ace_step_runtime,
)


class AceStepRuntimeTest(unittest.TestCase):
    def test_vram_parser_uses_largest_gpu(self) -> None:
        self.assertAlmostEqual(_parse_vram_output("16384\n32768\n"), 32.0)
        self.assertEqual(_parse_vram_output("N/A"), 0.0)

    @patch("ace_step_runtime.detect_gpu_vram_gb", return_value=24.0)
    @patch("ace_step_runtime._has_local_server_installation", return_value=False)
    def test_missing_installation_stays_client_but_is_install_eligible(self, _install, _gpu) -> None:
        state = detect_ace_step_runtime()
        self.assertEqual(state.mode, "client")
        self.assertEqual(state.api_url, REMOTE_ACE_SERVER)
        self.assertFalse(state.installed)
        self.assertTrue(state.install_eligible)

    @patch("ace_step_runtime.detect_gpu_vram_gb", return_value=16.0)
    @patch("ace_step_runtime._has_local_server_installation", return_value=False)
    def test_installation_requires_strictly_more_than_16gb(self, _install, _gpu) -> None:
        state = detect_ace_step_runtime()
        self.assertEqual(state.mode, "client")
        self.assertFalse(state.install_eligible)

    @patch("ace_step_runtime.detect_gpu_vram_gb", return_value=31.9)
    @patch("ace_step_runtime._has_local_server_installation", return_value=True)
    def test_runtime_and_checkpoint_enable_server_mode(self, _install, _gpu) -> None:
        state = detect_ace_step_runtime()
        self.assertEqual(state.mode, "server")
        self.assertEqual(state.api_url, LOCAL_ACE_SERVER)
        self.assertTrue(state.installed)


if __name__ == "__main__":
    unittest.main()

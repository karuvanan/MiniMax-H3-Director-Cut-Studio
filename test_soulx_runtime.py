"""Tests for SoulX automatic Client/Server runtime selection."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from runtime_paths import PROJECT_ROOT
from soulx_runtime import (
    LOCAL_SOULX_SERVER,
    REMOTE_SOULX_SERVER,
    _has_local_server_installation,
    detect_soulx_runtime,
    install_local_soulx_server,
)


class SoulXRuntimeTest(unittest.TestCase):
    def test_missing_installation_stays_client_without_installing(self) -> None:
        with patch("soulx_runtime._has_local_server_installation", return_value=False):
            state = detect_soulx_runtime(gpu_vram_gb=24.0)
        self.assertEqual(state.mode, "client")
        self.assertEqual(state.api_url, REMOTE_SOULX_SERVER)
        self.assertFalse(state.installed)
        self.assertTrue(state.install_eligible)

    def test_installation_requires_strictly_more_than_16gb(self) -> None:
        with patch("soulx_runtime._has_local_server_installation", return_value=False):
            state = detect_soulx_runtime(gpu_vram_gb=16.0)
        self.assertEqual(state.mode, "client")
        self.assertFalse(state.install_eligible)

    def test_complete_source_runtime_and_models_enable_server_mode(self) -> None:
        temp_root = PROJECT_ROOT / ".codex_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory, patch.dict(
            os.environ, {"COMPUTERNAME": "SOULX-TEST"}
        ):
            home = Path(directory)
            files = (
                home / "webui_svc.py",
                home / ".runtime" / "SOULX-TEST" / ".venv" / "Scripts" / "python.exe",
                home / "pretrained_models" / "SoulX-Singer" / "model-svc.pt",
                home / "pretrained_models" / "SoulX-Singer-Preprocess" / "separator.bin",
            )
            for path in files:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"ready")
            self.assertTrue(_has_local_server_installation(home))
            state = detect_soulx_runtime(home, gpu_vram_gb=24.0)
        self.assertEqual(state.mode, "server")
        self.assertEqual(state.api_url, LOCAL_SOULX_SERVER)
        self.assertTrue(state.installed)

    @patch("soulx_runtime.detect_gpu_vram_gb", return_value=16.0)
    def test_install_action_rechecks_vram_gate(self, _gpu) -> None:
        with self.assertRaisesRegex(RuntimeError, "more than 16 GB"):
            install_local_soulx_server()


if __name__ == "__main__":
    unittest.main()


"""Tests for SoulX automatic Client/Server runtime selection."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from runtime_paths import PROJECT_ROOT
from soulx_runtime import (
    LOCAL_SOULX_SERVER,
    REMOTE_SOULX_SERVER,
    _has_local_server_installation,
    _stable_api_ready,
    detect_soulx_runtime,
    install_local_soulx_server,
    read_soulx_startup_progress,
    stop_local_soulx_server,
)


class SoulXRuntimeTest(unittest.TestCase):
    def test_windows_soulx_launchers_keep_cmd_compatible_line_endings(self) -> None:
        for name in ("start_soulx_server.bat", "restart_soulx_server.bat"):
            payload = (PROJECT_ROOT / name).read_bytes()
            self.assertIn(b"\r\n", payload, name)
            self.assertNotIn(b"\n", payload.replace(b"\r\n", b""), name)

    def test_restart_launcher_keeps_powershell_pipeline_on_one_line(self) -> None:
        payload = (PROJECT_ROOT / "restart_soulx_server.bat").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("-Command ^", payload)
        self.assertIn("stop_soulx_server.ps1", payload)
        self.assertIn("-WaitSeconds 20", payload)

    def test_launcher_repairs_unsupported_cuda_architecture(self) -> None:
        payload = (PROJECT_ROOT / "start_soulx_server.bat").read_text(
            encoding="utf-8"
        )
        self.assertIn("torch.cuda.get_device_capability", payload)
        self.assertIn("torch.cuda.get_arch_list", payload)
        self.assertIn(":RepairTorch", payload)
        self.assertIn("torch==%SOULX_TORCH_VERSION%", payload)
        self.assertIn("https://download.pytorch.org/whl/cu128", payload)

    def test_old_lazy_wrapper_is_not_considered_healthy(self) -> None:
        parameters = [
            "prompt_audio",
            "target_audio",
            "prompt_vocal_sep",
            "target_vocal_sep",
            "auto_shift",
            "auto_mix_acc",
            "pitch_shift",
            "n_step",
            "cfg",
            "seed",
            "param_10",
            "param_11",
        ]
        payload = {
            "named_endpoints": {
                "/lazy_start_svc": {
                    "parameters": [
                        {"parameter_name": name} for name in parameters
                    ]
                }
            }
        }
        self.assertFalse(_stable_api_ready(payload))

    def test_studio_endpoint_is_considered_healthy(self) -> None:
        payload = {
            "named_endpoints": {
                "/_studio_start_svc": {
                    "parameters": [
                        {"parameter_name": "prompt_audio"},
                        {"parameter_name": "target_audio"},
                    ]
                }
            }
        }
        self.assertTrue(_stable_api_ready(payload))

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

    @patch("soulx_runtime.subprocess.run")
    def test_stop_local_server_uses_project_scoped_controller(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = "[SoulX] Port 7861 is free."
        run.return_value.stderr = ""
        self.assertTrue(stop_local_soulx_server())
        command = run.call_args.args[0]
        self.assertIn(str(PROJECT_ROOT / "stop_soulx_server.ps1"), command)
        self.assertIn(str(PROJECT_ROOT), command)
        self.assertIn("7861", command)

    def test_startup_progress_reports_latest_launcher_phase(self) -> None:
        stdout = MagicMock()
        stdout.is_file.return_value = True
        stdout.read_text.return_value = (
            "[SoulX] Building the isolated Python 3.10 runtime\n"
            "[SoulX] Models: pretrained_models\n"
            "* Running on local URL: http://0.0.0.0:7861\n"
        )
        stderr = MagicMock()
        stderr.is_file.return_value = True
        stderr.read_text.return_value = ""
        with patch("soulx_runtime.SOULX_STDOUT_LOG", stdout), patch(
            "soulx_runtime.SOULX_STDERR_LOG", stderr
        ):
            message = read_soulx_startup_progress()
        self.assertIn("validating contract", message)


if __name__ == "__main__":
    unittest.main()

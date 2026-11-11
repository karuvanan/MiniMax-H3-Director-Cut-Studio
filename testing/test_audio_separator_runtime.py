"""Tests for automatic Kim_Vocal_2 Client/Server selection."""

from __future__ import annotations

from pathlib import Path
import shutil
import unittest
import uuid
from unittest.mock import MagicMock, patch

from audio_separator_runtime import (
    LOCAL_AUDIO_SEPARATOR_SERVER,
    REMOTE_AUDIO_SEPARATOR_SERVER,
    _has_local_server_installation,
    detect_audio_separator_runtime,
    read_audio_separator_startup_progress,
    stop_local_audio_separator_server,
)
from runtime_paths import PROJECT_ROOT


class AudioSeparatorRuntimeTests(unittest.TestCase):
    def test_windows_launchers_keep_cmd_compatible_line_endings(self):
        for name in (
            "start_audio_separator_server.bat",
            "install_audio_separator_cuda_runtime.bat",
        ):
            payload = (PROJECT_ROOT / name).read_bytes()
            self.assertIn(b"\r\n", payload, name)
            self.assertNotIn(b"\n", payload.replace(b"\r\n", b""), name)

    def test_runtime_requires_gpu_onnx_and_real_model_probe(self):
        requirements = (
            PROJECT_ROOT / "models" / "audio-separator" / "requirements.txt"
        ).read_text(encoding="utf-8")
        launcher = (PROJECT_ROOT / "start_audio_separator_server.bat").read_text(
            encoding="utf-8"
        )
        self.assertIn("onnxruntime-gpu==1.23.2", requirements)
        self.assertNotIn("\nonnxruntime==", "\n" + requirements)
        self.assertIn("--probe", launcher)
        self.assertIn("install_audio_separator_cuda_runtime.bat", launcher)

    def test_missing_local_installation_stays_client(self):
        with patch(
            "audio_separator_runtime._has_local_server_installation", return_value=False
        ):
            state = detect_audio_separator_runtime(gpu_vram_gb=4.0)
        self.assertEqual(state.mode, "client")
        self.assertEqual(state.api_url, REMOTE_AUDIO_SEPARATOR_SERVER)
        self.assertFalse(state.installed)

    def test_local_files_without_cuda_gpu_stay_client(self):
        with patch(
            "audio_separator_runtime._has_local_server_installation", return_value=True
        ):
            state = detect_audio_separator_runtime(gpu_vram_gb=0.0)
        self.assertEqual(state.mode, "client")
        self.assertFalse(state.installed)
        self.assertIn("no CUDA GPU", state.detail)

    def test_complete_local_installation_selects_server(self):
        root = PROJECT_ROOT / ".director_cache" / f"audio-runtime-{uuid.uuid4().hex}"
        root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, root, True)
        try:
            install = root / "models" / "audio-separator"
            for path in (
                install / "Kim_Vocal_2.onnx",
                install / "download_checks.json",
                install / "mdx_model_data.json",
                install / "vr_model_data.json",
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"ready")
            for package in ("audio_separator", "onnxruntime"):
                (install / "runtime" / package).mkdir(parents=True)
            self.assertTrue(_has_local_server_installation(root))
            state = detect_audio_separator_runtime(root, gpu_vram_gb=12.0)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(state.mode, "server")
        self.assertEqual(state.api_url, LOCAL_AUDIO_SEPARATOR_SERVER)

    @patch("audio_separator_runtime.subprocess.run")
    def test_stop_uses_project_scoped_controller(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = "Port 7862 is free"
        run.return_value.stderr = ""
        self.assertTrue(stop_local_audio_separator_server())
        command = run.call_args.args[0]
        self.assertIn(str(PROJECT_ROOT / "stop_audio_separator_server.ps1"), command)
        self.assertIn("7862", command)

    def test_startup_progress_reports_cuda_validation(self):
        stdout = MagicMock()
        stdout.is_file.return_value = True
        stdout.read_text.return_value = (
            "[Audio Separator] Installing CUDA runtime\n"
            "[Audio Separator] Validating CUDAExecutionProvider\n"
        )
        stderr = MagicMock()
        stderr.is_file.return_value = False
        with patch("audio_separator_runtime.STDOUT_LOG", stdout), patch(
            "audio_separator_runtime.STDERR_LOG", stderr
        ):
            self.assertIn("validating GPU provider", read_audio_separator_startup_progress())


if __name__ == "__main__":
    unittest.main()

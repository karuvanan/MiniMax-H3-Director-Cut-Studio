"""Focused UI tests for the standalone SoulX voice-clone workbench."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from soulx_client import DEFAULT_SOULX_SERVER
from soulx_dialog import SoulXSingerDialog
from soulx_runtime import LOCAL_SOULX_SERVER, SoulXRuntimeState
from runtime_paths import PROJECT_ROOT


class SoulXSingerDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.unload_patcher = patch(
            "soulx_dialog.request_server_unload",
            return_value={
                "supported": True,
                "unloaded": True,
                "endpoint": "/_unload_svc",
                "warning": "",
            },
        )
        cls.request_unload = cls.unload_patcher.start()
        cls.stop_patcher = patch("soulx_dialog.stop_local_soulx_server", return_value=True)
        cls.stop_local = cls.stop_patcher.start()
        cls.start_patcher = patch(
            "soulx_dialog.start_local_soulx_server_if_installed", return_value=True
        )
        cls.start_local = cls.start_patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.start_patcher.stop()
        cls.stop_patcher.stop()
        cls.unload_patcher.stop()

    def setUp(self) -> None:
        self.request_unload.reset_mock()
        self.stop_local.reset_mock()
        self.start_local.reset_mock()

    def test_leaving_dialog_requests_server_model_unload(self) -> None:
        dialog = SoulXSingerDialog()
        server = dialog.server_edit.text()
        dialog.reject()
        self.request_unload.assert_called_once_with(server, timeout=4.0)
        dialog.deleteLater()

    def test_leaving_local_server_mode_stops_hidden_server(self) -> None:
        state = SoulXRuntimeState(
            mode="server",
            api_url=LOCAL_SOULX_SERVER,
            installed=True,
            gpu_vram_gb=31.9,
            install_eligible=True,
            detail="Installed",
        )
        dialog = SoulXSingerDialog(runtime_state=state)
        dialog.reject()
        self.request_unload.assert_called_once_with(LOCAL_SOULX_SERVER, timeout=4.0)
        self.stop_local.assert_called_once_with()
        dialog.deleteLater()

    def test_leaving_client_mode_never_stops_shared_remote_server(self) -> None:
        state = SoulXRuntimeState(
            mode="client",
            api_url="http://192.168.0.185:7861",
            installed=False,
            gpu_vram_gb=8.0,
            install_eligible=False,
            detail="Client",
        )
        dialog = SoulXSingerDialog(runtime_state=state)
        dialog.reject()
        self.request_unload.assert_called_once_with(state.api_url, timeout=4.0)
        self.stop_local.assert_not_called()
        dialog.deleteLater()

    def test_readiness_result_updates_bottom_status_and_enables_conversion(self) -> None:
        dialog = SoulXSingerDialog()
        dialog._handle_readiness_result(
            {
                "ready": True,
                "message": "SoulX API ready · http://127.0.0.1:7861 · 12 SVC controls detected",
            }
        )
        self.assertIn("SoulX API ready", dialog.status_label.text())
        self.assertTrue(dialog.convert_button.isEnabled())
        dialog.reject()
        dialog.deleteLater()

    def test_safe_defaults_match_official_svc_workflow(self) -> None:
        dialog = SoulXSingerDialog()
        self.assertEqual(dialog.server_edit.text(), DEFAULT_SOULX_SERVER)
        self.assertFalse(dialog.prompt_vocal_sep_check.isChecked())
        self.assertTrue(dialog.target_vocal_sep_check.isChecked())
        self.assertTrue(dialog.auto_shift_check.isChecked())
        self.assertTrue(dialog.auto_mix_check.isChecked())
        self.assertTrue(dialog.auto_unload_check.isChecked())
        self.assertIn("closing always unloads", dialog.auto_unload_check.text())
        self.assertEqual(dialog.device_combo.currentText(), "cuda")
        self.assertEqual(dialog.steps_spin.value(), 32)
        self.assertEqual(dialog.cfg_spin.value(), 1.0)
        self.assertEqual(dialog.seed_spin.maximum(), 10_000)
        dialog.close()
        dialog.deleteLater()

    def test_server_mode_uses_local_api_and_disables_installer(self) -> None:
        state = SoulXRuntimeState(
            mode="server",
            api_url=LOCAL_SOULX_SERVER,
            installed=True,
            gpu_vram_gb=31.9,
            install_eligible=True,
            detail="Installed",
        )
        dialog = SoulXSingerDialog(runtime_state=state)
        self.assertEqual(dialog.server_edit.text(), LOCAL_SOULX_SERVER)
        self.assertIn("SERVER MODE", dialog.runtime_mode_label.text())
        self.assertFalse(dialog.install_local_button.isEnabled())
        dialog.close()
        dialog.deleteLater()

    def test_clone_busy_state_shows_full_window_cyan_spinner(self) -> None:
        dialog = SoulXSingerDialog()
        dialog._api_ready = True
        self.assertTrue(dialog.busy_overlay.isHidden())
        dialog._set_busy(
            True,
            "SoulX conversion running",
            "CLONING SINGING VOICE…",
        )
        self.assertFalse(dialog.busy_overlay.isHidden())
        self.assertTrue(dialog.busy_overlay._timer.isActive())
        self.assertEqual(dialog.busy_overlay.geometry(), dialog.rect())
        self.assertIsNotNone(dialog.busy_overlay._background)
        self.assertFalse(dialog.convert_button.isEnabled())
        dialog._set_busy(False)
        self.assertTrue(dialog.busy_overlay.isHidden())
        self.assertFalse(dialog.busy_overlay._timer.isActive())
        self.assertTrue(dialog.convert_button.isEnabled())
        dialog.close()
        dialog.deleteLater()

    def test_completed_output_is_not_auto_imported_into_h3(self) -> None:
        dialog = SoulXSingerDialog()
        temp_root = PROJECT_ROOT / ".codex_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            output = Path(directory) / "clone.mp3"
            output.write_bytes(b"ID3")
            dialog._handle_success(
                "conversion",
                {
                    "output": str(output),
                    "unload": {"supported": False, "unloaded": False, "warning": "unsupported"},
                },
            )
            self.assertEqual(dialog.output_path, output)
            self.assertTrue(dialog.save_button.isEnabled())
            self.assertIn("manually", dialog.status_label.text())
            self.assertFalse(hasattr(dialog, "media_pool"))
            dialog.player.setSource(QUrl())
        dialog.close()
        dialog.deleteLater()

    @patch("soulx_dialog.QFileDialog.getSaveFileName")
    def test_save_as_forces_mp3_extension(self, get_save_file_name) -> None:
        dialog = SoulXSingerDialog()
        temp_root = PROJECT_ROOT / ".codex_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            root = Path(directory)
            output = root / "clone.mp3"
            output.write_bytes(b"ID3")
            dialog.output_path = output
            get_save_file_name.return_value = (str(root / "approved_clone"), "")
            dialog.save_output_as()
            self.assertTrue((root / "approved_clone.mp3").is_file())
        dialog.close()
        dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()

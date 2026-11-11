import os
from pathlib import Path
import shutil
import unittest
import uuid
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from audio_separator_client import normalize_server, separate_audio
from audio_separator_dialog import AudioSeparatorDialog
from audio_separator_runtime import AudioSeparatorRuntimeState, LOCAL_AUDIO_SEPARATOR_SERVER
from audio_separator_server import _safe_name


class AudioSeparatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_server_url_is_validated(self):
        self.assertEqual(normalize_server("http://192.168.0.185:7862/"), "http://192.168.0.185:7862")
        with self.assertRaises(ValueError):
            normalize_server("192.168.0.185:7862")

    def test_server_sanitizes_uploaded_filename(self):
        self.assertEqual(_safe_name("../../My Song?.MP3"), "My_Song.mp3")
        self.assertEqual(_safe_name("unsafe.exe"), "unsafe.wav")

    @patch("audio_separator_client._json_request", return_value={"ok": True})
    def test_unicode_source_filename_is_url_encoded_not_put_in_http_header(self, request_json):
        folder = Path(__file__).resolve().parent / ".director_cache" / f"unicode-audio-{uuid.uuid4().hex}"
        folder.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, folder, True)
        source = folder / "鳳凰飛翔_不得不愛_日本語.mp3"
        source.write_bytes(b"ID3 unicode filename")
        result = separate_audio("http://127.0.0.1:7862", source)
        self.assertTrue(result["ok"])
        request = request_json.call_args.args[0]
        self.assertIn("%E9%B3%B3%E5%87%B0", request.full_url)
        self.assertNotIn("X-source-filename", request.headers)
        request.full_url.encode("latin-1")

    def test_dialog_exposes_three_downloads_and_explicit_mapping(self):
        dialog = AudioSeparatorDialog(server_url="http://127.0.0.1:7862")
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(set(dialog.download_buttons), {"vocal", "music", "mix"})
        self.assertEqual(set(dialog.play_buttons), {"vocal", "music", "mix"})
        self.assertEqual(set(dialog.stop_buttons), {"vocal", "music", "mix"})
        self.assertTrue(all(button.text() == "PLAY" for button in dialog.play_buttons.values()))
        self.assertTrue(all(button.text() == "STOP" for button in dialog.stop_buttons.values()))
        self.assertEqual(dialog.add_button.text(), "ADD TO A1 & A2")
        self.assertIn("Music → A1", dialog.add_button.toolTip())

    def test_add_signal_order_is_music_vocal_mix(self):
        dialog = AudioSeparatorDialog(server_url="http://127.0.0.1:7862")
        self.addCleanup(dialog.deleteLater)
        folder = Path(__file__).resolve().parent / ".director_cache" / f"audio-separator-{uuid.uuid4().hex}"
        folder.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, folder, True)
        try:
            paths = {}
            for kind in ("music", "vocal", "mix"):
                path = Path(folder) / f"{kind}.wav"
                path.write_bytes(b"audio-data")
                paths[kind] = path
            dialog.result_paths = paths
            received = []
            dialog.add_requested.connect(lambda music, vocal, mix: received.append((music, vocal, mix)))
            dialog.add_to_media_pool()
            self.assertEqual(received, [(str(paths["music"]), str(paths["vocal"]), str(paths["mix"]))])
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    @patch("audio_separator_dialog.start_local_audio_separator_server_if_installed", return_value=True)
    @patch("audio_separator_dialog.stop_local_audio_separator_server", return_value=True)
    def test_server_mode_auto_starts_and_closing_stops_local_api(self, stop_local, start_local):
        state = AudioSeparatorRuntimeState(
            mode="server",
            api_url=LOCAL_AUDIO_SEPARATOR_SERVER,
            installed=True,
            gpu_vram_gb=24.0,
            detail="Installed",
        )
        dialog = AudioSeparatorDialog(runtime_state=state)
        self.addCleanup(dialog.deleteLater)
        self.assertIn("SERVER MODE", dialog.runtime_mode_label.text())
        self.assertFalse(dialog.separate_button.isEnabled())
        start_local.assert_called()
        dialog.reject()
        stop_local.assert_called_once_with()

    def test_cuda_health_is_required_before_separation_is_enabled(self):
        dialog = AudioSeparatorDialog(server_url="http://192.168.0.185:7862")
        self.addCleanup(dialog.deleteLater)
        dialog._handle_readiness_result(
            {
                "ready": True,
                "message": "Audio Separator API ready · CUDAExecutionProvider",
            }
        )
        self.assertTrue(dialog.separate_button.isEnabled())
        dialog.reject()


if __name__ == "__main__":
    unittest.main()

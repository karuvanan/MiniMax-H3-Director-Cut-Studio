"""Focused tests for the standalone SoulX-Singer client."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import soulx_client
from runtime_paths import PROJECT_ROOT


def _info(parameters: list[str], *extra_endpoints: str) -> dict:
    named = {
        soulx_client.SVC_API_NAME: {
            "parameters": [{"parameter_name": name} for name in parameters]
        }
    }
    for endpoint in extra_endpoints:
        named[endpoint] = {"parameters": []}
    return {"named_endpoints": named}


class SoulXClientTest(unittest.TestCase):
    def test_official_ten_parameter_api_is_supported(self) -> None:
        parameters = list(soulx_client.EXPECTED_CORE_PARAMETERS)
        self.assertEqual(soulx_client.validate_svc_api(_info(parameters)), parameters)

    def test_extended_device_and_fp16_api_is_supported(self) -> None:
        parameters = list(soulx_client.EXPECTED_CORE_PARAMETERS[:6])
        parameters.extend(["device_choice", "use_fp16"])
        parameters.extend(soulx_client.EXPECTED_CORE_PARAMETERS[6:])
        self.assertEqual(soulx_client.validate_svc_api(_info(parameters)), parameters)

    def test_missing_required_parameter_is_rejected(self) -> None:
        parameters = [
            name for name in soulx_client.EXPECTED_CORE_PARAMETERS if name != "target_audio"
        ]
        with self.assertRaisesRegex(RuntimeError, "target_audio"):
            soulx_client.validate_svc_api(_info(parameters))

    def test_unload_is_never_claimed_when_endpoint_is_absent(self) -> None:
        with patch.object(soulx_client, "fetch_api_info", return_value=_info(list(soulx_client.EXPECTED_CORE_PARAMETERS))):
            result = soulx_client.request_server_unload("http://127.0.0.1:7861")
        self.assertFalse(result["supported"])
        self.assertFalse(result["unloaded"])
        self.assertIn("no unload endpoint", result["warning"])

    def test_unload_calls_discovered_server_endpoint(self) -> None:
        client = MagicMock()
        info = _info(list(soulx_client.EXPECTED_CORE_PARAMETERS), "/_unload_svc")
        with patch.object(soulx_client, "fetch_api_info", return_value=info), patch.object(
            soulx_client, "_gradio_client", return_value=client
        ):
            result = soulx_client.request_server_unload("http://127.0.0.1:7861")
        self.assertTrue(result["unloaded"])
        client.predict.assert_called_once_with(api_name="/_unload_svc")

    @patch("soulx_client.subprocess.run")
    @patch("soulx_client.load_runtime_paths")
    def test_wav_result_is_exported_as_320k_mp3(self, runtime_paths, run) -> None:
        temp_root = PROJECT_ROOT / ".codex_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            root = Path(directory)
            source = root / "result.wav"
            source.write_bytes(b"RIFF")
            ffmpeg = root / "ffmpeg.exe"
            ffmpeg.write_bytes(b"exe")
            runtime_paths.return_value.ffmpeg = ffmpeg
            with patch.object(soulx_client, "OUTPUT_DIR", root / "outputs"):
                output = soulx_client._to_mp3(source)
        command = run.call_args.args[0]
        self.assertEqual(output.suffix, ".mp3")
        self.assertIn("libmp3lame", command)
        self.assertIn("320k", command)

    @patch("soulx_client._to_mp3")
    @patch("soulx_client._gradio_client")
    @patch("soulx_client.fetch_api_info")
    def test_conversion_maps_extended_server_controls_by_name(
        self, fetch_info, gradio_client, to_mp3
    ) -> None:
        temp_root = PROJECT_ROOT / ".codex_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        parameters = list(soulx_client.EXPECTED_CORE_PARAMETERS[:6])
        parameters.extend(["device_choice", "use_fp16"])
        parameters.extend(soulx_client.EXPECTED_CORE_PARAMETERS[6:])
        fetch_info.return_value = _info(parameters)
        client = gradio_client.return_value
        with tempfile.TemporaryDirectory(dir=temp_root) as directory, patch(
            "gradio_client.handle_file", side_effect=lambda value: f"upload:{value}"
        ):
            root = Path(directory)
            voice = root / "voice.wav"
            song = root / "song.mp3"
            generated = root / "generated.wav"
            for path in (voice, song, generated):
                path.write_bytes(b"audio")
            client.predict.return_value = str(generated)
            to_mp3.return_value = root / "approved.mp3"
            output = soulx_client.convert_singing_voice(
                "http://127.0.0.1:7861",
                voice_reference=voice,
                source_song=song,
            )
        kwargs = client.predict.call_args.kwargs
        self.assertEqual(kwargs["api_name"], soulx_client.SVC_API_NAME)
        self.assertEqual(kwargs["device_choice"], "cuda")
        self.assertTrue(kwargs["use_fp16"])
        self.assertTrue(str(kwargs["prompt_audio"]).startswith("upload:"))
        self.assertTrue(str(kwargs["target_audio"]).startswith("upload:"))
        self.assertEqual(output.name, "approved.mp3")


if __name__ == "__main__":
    unittest.main()

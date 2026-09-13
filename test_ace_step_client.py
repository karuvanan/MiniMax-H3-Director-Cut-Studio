"""Focused unit tests for the ACE-Step LAN client."""

from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import ace_step_client


class AceStepClientTest(unittest.TestCase):
    """Validate multipart encoding and task response normalization."""

    def test_multipart_contains_fields_and_audio(self) -> None:
        """Multipart payload should preserve UTF-8 prompts and binary audio."""

        audio = Path("reference.mp3")
        with patch.object(Path, "read_bytes", return_value=b"ID3-audio"):
            body, content_type = ace_step_client._multipart(
                {"prompt": "高能电子舞曲"}, {"src_audio": audio}
            )
        self.assertIn("multipart/form-data; boundary=", content_type)
        self.assertIn("高能电子舞曲".encode("utf-8"), body)
        self.assertIn(b"ID3-audio", body)
        self.assertIn(b'filename="reference.mp3"', body)

    @patch("ace_step_client.request_json")
    def test_query_task_decodes_nested_result(self, request_json) -> None:
        """The API's JSON-string result should be exposed as output records."""

        request_json.return_value = {
            "data": [{"task_id": "task-1", "status": 1, "result": json.dumps([{"file": "/v1/audio"}])}]
        }
        record = ace_step_client.query_task("task-1")
        self.assertEqual(record["status"], 1)
        self.assertEqual(record["outputs"][0]["file"], "/v1/audio")

    @patch("ace_step_client._urlopen")
    @patch("ace_step_client._multipart")
    def test_submit_base_lego_includes_track_instruction_and_base_steps(
        self, multipart, urlopen
    ) -> None:
        """Lego requests should preserve Base-only controls in the multipart body."""

        multipart.return_value = (b"multipart", "multipart/form-data; boundary=test")
        response = MagicMock()
        response.read.return_value = b'{"data":{"task_id":"lego-1"}}'
        urlopen.return_value.__enter__.return_value = response
        with patch.object(Path, "is_file", return_value=True):
            task_id = ace_step_client.submit_audio_task(
                "source.wav",
                task_type="lego",
                model="acestep-v15-base",
                instruction="Generate the guitar track based on the audio context:",
                track_name="guitar",
                inference_steps=64,
            )

        fields = multipart.call_args.args[0]
        self.assertEqual(task_id, "lego-1")
        self.assertEqual(fields["task_type"], "lego")
        self.assertEqual(fields["model"], "acestep-v15-base")
        self.assertEqual(fields["track_name"], "guitar")
        self.assertEqual(fields["inference_steps"], "64")
        self.assertEqual(fields["thinking"], "false")

    @patch("ace_step_client._urlopen")
    @patch("ace_step_client._multipart")
    def test_submit_repaint_includes_explicit_segment_controls(
        self, multipart, urlopen
    ) -> None:
        """Repaint requests should send the exact edit window and preservation mode."""

        multipart.return_value = (b"multipart", "multipart/form-data; boundary=test")
        response = MagicMock()
        response.read.return_value = b'{"data":{"task_id":"repaint-1"}}'
        urlopen.return_value.__enter__.return_value = response
        with patch.object(Path, "is_file", return_value=True):
            ace_step_client.submit_audio_task(
                "source.wav",
                task_type="repaint",
                repainting_start=12.5,
                repainting_end=31.75,
                chunk_mask_mode="explicit",
                repaint_mode="conservative",
                repaint_strength=0.25,
            )

        fields = multipart.call_args.args[0]
        self.assertEqual(fields["repainting_start"], "12.5")
        self.assertEqual(fields["repainting_end"], "31.75")
        self.assertEqual(fields["chunk_mask_mode"], "explicit")
        self.assertEqual(fields["repaint_mode"], "conservative")
        self.assertEqual(fields["repaint_strength"], "0.25")


if __name__ == "__main__":
    unittest.main()

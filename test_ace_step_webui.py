"""Focused behavior tests for the standalone ACE-Step Music Cover WebUI."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import ace_step_webui


class AceStepWebUiTest(unittest.TestCase):
    @patch("ace_step_webui.wait_for_task")
    @patch("ace_step_webui.submit_audio_task")
    def test_analysis_returns_editable_metadata_and_full_api_record(
        self, submit_audio_task, wait_for_task
    ) -> None:
        submit_audio_task.return_value = "analysis-task"
        wait_for_task.return_value = {
            "status": 1,
            "server_marker": "complete-record",
            "outputs": [
                {
                    "prompt": "detailed electronic cover",
                    "lyrics": "[Instrumental]",
                    "bpm": 130,
                    "keyscale": "E minor",
                    "timesignature": "4",
                    "duration": 20,
                }
            ],
        }

        values = ace_step_webui.analyze_source("source.mp3", "http://server", "")

        self.assertEqual(values[:6], (
            "detailed electronic cover", "[Instrumental]", 130,
            "E minor", "4", 20,
        ))
        self.assertEqual(json.loads(values[-1])["server_marker"], "complete-record")

    @patch("ace_step_webui.download_audio")
    @patch("ace_step_webui.wait_for_task")
    @patch("ace_step_webui.submit_audio_task")
    def test_independent_timbre_reference_overrides_default_source_reference(
        self, submit_audio_task, wait_for_task, download_audio
    ) -> None:
        submit_audio_task.return_value = "cover-task"
        wait_for_task.return_value = {
            "status": 1,
            "server_marker": "complete-record",
            "outputs": [{"file": "/v1/audio/result", "generation_info": "done"}],
        }

        values = ace_step_webui.generate_cover(
            "source.mp3", "voice.mp3", True, "prompt", "[Instrumental]",
            130, "E minor", "4", 20, 0.9, 8, False, 42,
            "http://server", "",
        )

        self.assertEqual(submit_audio_task.call_args.kwargs["reference_audio"], "voice.mp3")
        self.assertEqual(values[0], values[1])
        self.assertEqual(json.loads(values[-1])["server_marker"], "complete-record")
        download_audio.assert_called_once()

    @patch("ace_step_webui.download_audio")
    @patch("ace_step_webui.wait_for_task")
    @patch("ace_step_webui.submit_audio_task")
    def test_source_audio_is_default_timbre_reference(
        self, submit_audio_task, wait_for_task, _download_audio
    ) -> None:
        submit_audio_task.return_value = "cover-task"
        wait_for_task.return_value = {
            "status": 1,
            "outputs": [{"file": "/v1/audio/result"}],
        }

        ace_step_webui.generate_cover(
            "source.mp3", None, True, "prompt", "[Instrumental]",
            130, "E minor", "4", 20, 1.0, 8, False, 42,
            "http://server", "",
        )

        self.assertEqual(submit_audio_task.call_args.kwargs["reference_audio"], "source.mp3")


if __name__ == "__main__":
    unittest.main()

"""Focused tests for the native ACE-Step Music Cover Studio dialog."""

from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ace_step_dialog import (
    ANIMAL_SOUND_PRESETS,
    AceStepMusicCoverDialog,
    INSTRUMENT_PRESETS,
    KEY_SCALE_PRESETS,
    LANGUAGE_FAMILY_PRESETS,
    VOCAL_PRESETS,
    _apply_volume_gain,
    _fit_output_duration_and_volume,
    _instrument_remix_prompt,
    _music_key_notation,
    _prepare_source_for_duration,
    _remix_palette_prompt,
)
from ace_step_runtime import AceStepRuntimeState, LOCAL_ACE_SERVER


class AceStepMusicCoverDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_dialog_displays_configured_remote_api_and_editable_fields(self) -> None:
        dialog = AceStepMusicCoverDialog()
        self.assertEqual(dialog.server_edit.text(), "http://192.168.0.185:8001")
        self.assertFalse(dialog.prompt_edit.isReadOnly())
        self.assertFalse(dialog.lyrics_edit.isReadOnly())
        self.assertTrue(dialog.use_source_reference_check.isChecked())
        self.assertEqual(dialog.cover_strength_spin.value(), 1.0)
        self.assertEqual(dialog.steps_spin.value(), 8)
        self.assertEqual(dialog.volume_db_spin.value(), 0.0)
        self.assertEqual(dialog.volume_db_spin.minimum(), -24.0)
        self.assertEqual(dialog.volume_db_spin.maximum(), 12.0)
        self.assertEqual(dialog.duration_spin.minimum(), 10.0)
        dialog.close()
        dialog.deleteLater()

    def test_server_mode_uses_local_api_and_disables_installer(self) -> None:
        state = AceStepRuntimeState(
            mode="server",
            api_url=LOCAL_ACE_SERVER,
            installed=True,
            gpu_vram_gb=31.9,
            install_eligible=True,
            detail="Local runtime detected",
        )
        dialog = AceStepMusicCoverDialog(runtime_state=state)
        self.assertEqual(dialog.server_edit.text(), LOCAL_ACE_SERVER)
        self.assertIn("SERVER MODE", dialog.runtime_mode_label.text())
        self.assertFalse(dialog.install_local_button.isEnabled())
        dialog.close()
        dialog.deleteLater()

    def test_key_input_has_all_24_major_minor_presets_with_music_accidentals(self) -> None:
        dialog = AceStepMusicCoverDialog()
        choices = [dialog.key_edit.itemText(index) for index in range(dialog.key_edit.count())]
        self.assertEqual(tuple(choices), KEY_SCALE_PRESETS)
        self.assertEqual(len(choices), 24)
        self.assertEqual(sum(name.endswith(" major") for name in choices), 12)
        self.assertEqual(sum(name.endswith(" minor") for name in choices), 12)
        self.assertIn("F♯ major", choices)
        self.assertIn("E♭ major", choices)
        self.assertIn("C♯ minor", choices)
        self.assertIn("B♭ minor", choices)
        self.assertTrue(dialog.key_edit.isEditable())
        self.assertEqual(_music_key_notation("C# minor"), "C♯ minor")
        self.assertEqual(_music_key_notation("Eb major"), "E♭ major")
        dialog.close()
        dialog.deleteLater()

    def test_mode_selector_exposes_cover_repaint_lego_and_extract_controls(self) -> None:
        dialog = AceStepMusicCoverDialog()
        modes = [dialog.mode_combo.itemData(index) for index in range(dialog.mode_combo.count())]
        self.assertEqual(modes, ["cover", "repaint", "lego", "extract"])

        dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData("repaint"))
        self.assertFalse(dialog.repaint_start_spin.isHidden())
        self.assertFalse(dialog.repaint_end_spin.isHidden())
        self.assertTrue(dialog.track_combo.isHidden())
        self.assertEqual(dialog.generate_button.text(), "REPAINT SELECTED SEGMENT")

        dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData("lego"))
        self.assertEqual(dialog.model_combo.currentText(), "acestep-v15-base")
        self.assertFalse(dialog.model_combo.isEnabled())
        self.assertEqual(dialog.steps_spin.maximum(), 200)
        self.assertEqual(dialog.steps_spin.value(), 64)
        self.assertFalse(dialog.track_combo.isHidden())
        dialog.track_combo.setCurrentText("guitar")
        self.assertEqual(
            dialog.instruction_edit.text(),
            "Generate the guitar track based on the audio context:",
        )

        dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData("extract"))
        dialog.track_combo.setCurrentText("vocals")
        self.assertEqual(
            dialog.instruction_edit.text(), "Extract the vocals track from the audio:"
        )
        self.assertEqual(dialog.generate_button.text(), "EXTRACT TRACK")
        dialog.close()
        dialog.deleteLater()

    def test_remix_palette_is_multi_select_across_all_four_tabs(self) -> None:
        dialog = AceStepMusicCoverDialog()
        dialog.prompt_edit.setPlainText("High-energy electronic dance arrangement.")
        self.assertEqual(len(dialog.instrument_buttons), len(INSTRUMENT_PRESETS))
        self.assertEqual(len(dialog.instrument_buttons), 24)
        self.assertEqual(len(dialog.vocal_buttons), len(VOCAL_PRESETS))
        self.assertEqual(len(dialog.vocal_buttons), 6)
        self.assertIn("young boy vocal", dialog.vocal_buttons)
        self.assertIn("young girl vocal", dialog.vocal_buttons)
        self.assertEqual(len(dialog.language_family_buttons), len(LANGUAGE_FAMILY_PRESETS))
        self.assertEqual(len(dialog.language_family_buttons), 8)
        self.assertEqual(len(dialog.animal_sound_buttons), len(ANIMAL_SOUND_PRESETS))
        self.assertEqual(len(dialog.animal_sound_buttons), 16)

        dialog.instrument_buttons["grand piano"].click()
        dialog.instrument_buttons["Chinese guzheng"].click()
        dialog.vocal_buttons["young female vocal"].click()
        dialog.language_family_buttons[
            "Sino-Tibetan language-family vocal character"
        ].click()
        dialog.animal_sound_buttons["bird chirps"].click()

        self.assertTrue(dialog.instrument_buttons["grand piano"].isChecked())
        self.assertTrue(dialog.instrument_buttons["Chinese guzheng"].isChecked())
        self.assertTrue(dialog.vocal_buttons["young female vocal"].isChecked())
        prompt = dialog.prompt_edit.toPlainText()
        self.assertIn("Instrumentation: feature grand piano, Chinese guzheng", prompt)
        self.assertIn("Vocal casting: feature young female vocal", prompt)
        self.assertIn("Sino-Tibetan language-family vocal character", prompt)
        self.assertIn("Animal sound design: integrate bird chirps", prompt)
        self.assertEqual(prompt.count("[REMIX PALETTE]"), 1)
        self.assertFalse(dialog._busy)
        self.assertIn("no API request sent", dialog.status_label.text())

        dialog.instrument_buttons["grand piano"].click()
        prompt = dialog.prompt_edit.toPlainText()
        self.assertNotIn("grand piano", prompt)
        self.assertIn("Instrumentation: feature Chinese guzheng", prompt)
        remixed = _remix_palette_prompt(
            "Original",
            ["Indian sitar", "Indian tabla"],
            ["elderly male vocal"],
            ["Indo-European language-family vocal character"],
            ["owl hoots", "frog ribbits"],
        )
        self.assertIn("Original\n\n[REMIX PALETTE]", remixed)
        self.assertIn("Indian sitar, Indian tabla", remixed)
        self.assertIn("elderly male vocal", remixed)
        self.assertIn("Indo-European", remixed)
        self.assertIn("owl hoots, frog ribbits", remixed)
        self.assertEqual(remixed.count("[REMIX PALETTE]"), 1)
        self.assertIn("Instrumentation: feature Indian sitar", _instrument_remix_prompt("", ["Indian sitar"]))
        dialog.close()
        dialog.deleteLater()

    @patch.object(AceStepMusicCoverDialog, "generate_cover")
    def test_palette_selection_waits_for_explicit_remix_button(self, generate_cover) -> None:
        dialog = AceStepMusicCoverDialog()
        dialog.prompt_edit.setPlainText("Electronic dance arrangement.")

        dialog.instrument_buttons["grand piano"].click()
        dialog.vocal_buttons["young female vocal"].click()
        self.app.processEvents()

        generate_cover.assert_not_called()
        self.assertIn("no API request sent", dialog.status_label.text())
        dialog.remix_selected_button.click()
        generate_cover.assert_called_once()
        dialog.close()
        dialog.deleteLater()

    @patch("ace_step_dialog.QMessageBox.information")
    def test_generate_automatically_applies_unsubmitted_palette(self, information) -> None:
        dialog = AceStepMusicCoverDialog()
        dialog.instrument_buttons["Chinese guzheng"].setChecked(True)
        dialog.prompt_edit.setPlainText("Original analyzed prompt.")

        dialog.generate_cover()

        self.assertIn(
            "Instrumentation: feature Chinese guzheng",
            dialog.prompt_edit.toPlainText(),
        )
        information.assert_called_once()
        dialog.close()
        dialog.deleteLater()

    @patch("ace_step_dialog.subprocess.run")
    def test_positive_volume_gain_uses_ffmpeg_with_peak_limiter(self, run) -> None:
        _apply_volume_gain(
            Path("raw.mp3"),
            Path("boosted.mp3"),
            6.0,
            Path("ffmpeg.exe"),
        )

        command = run.call_args.args[0]
        self.assertIn("volume=6.00dB,alimiter=limit=0.98", command)
        self.assertEqual(command[-1], "boosted.mp3")
        self.assertTrue(run.call_args.kwargs["check"])

    @patch("ace_step_dialog.subprocess.run")
    def test_duration_guide_loops_or_trims_source_to_exact_target(self, run) -> None:
        _prepare_source_for_duration(
            Path("source.mp3"),
            Path("structure.wav"),
            120.0,
            Path("ffmpeg.exe"),
        )

        command = run.call_args.args[0]
        self.assertEqual(command[command.index("-stream_loop") + 1], "-1")
        self.assertEqual(command[command.index("-t") + 1], "120.000")
        self.assertEqual(command[-1], "structure.wav")

    @patch("ace_step_dialog.subprocess.run")
    def test_output_duration_fallback_repeats_music_to_exact_target(self, run) -> None:
        _fit_output_duration_and_volume(
            Path("api.mp3"),
            Path("final.mp3"),
            120.0,
            0.0,
            Path("ffmpeg.exe"),
        )

        command = run.call_args.args[0]
        self.assertEqual(command[command.index("-stream_loop") + 1], "-1")
        self.assertEqual(command[command.index("-t") + 1], "120.000")
        self.assertEqual(command[-1], "final.mp3")

    def test_analysis_and_generation_busy_states_show_spinner_overlay(self) -> None:
        dialog = AceStepMusicCoverDialog()
        self.assertTrue(dialog.busy_overlay.isHidden())

        dialog._set_busy(True, "ANALYZING AUDIO · AUTO-FILLING MUSIC FIELDS…")
        self.assertFalse(dialog.busy_overlay.isHidden())
        self.assertTrue(dialog.busy_overlay._timer.isActive())
        self.assertEqual(dialog.busy_overlay.geometry(), dialog.rect())
        self.assertIsNotNone(dialog.busy_overlay._background)
        self.assertFalse(dialog.analyze_button.isEnabled())
        self.assertFalse(dialog.generate_button.isEnabled())

        dialog._set_busy(False)
        self.assertTrue(dialog.busy_overlay.isHidden())
        self.assertFalse(dialog.busy_overlay._timer.isActive())
        self.assertTrue(dialog.analyze_button.isEnabled())
        self.assertTrue(dialog.generate_button.isEnabled())
        dialog.close()
        dialog.deleteLater()

    @patch("ace_step_dialog.request_json")
    def test_base_model_is_initialized_on_first_lego_or_extract_run(self, request_json) -> None:
        request_json.side_effect = [
            {
                "code": 200,
                "data": {
                    "models": [
                        {"name": "acestep-v15-turbo", "is_loaded": True}
                    ]
                },
            },
            {
                "code": 200,
                "data": {"loaded_model": "acestep-v15-base"},
                "error": None,
            },
        ]

        result = AceStepMusicCoverDialog._ensure_model_loaded(
            "http://192.168.0.185:8001", "", "acestep-v15-base"
        )

        self.assertTrue(result["initialized"])
        self.assertEqual(request_json.call_args_list[0].args[1], "v1/model_inventory")
        self.assertEqual(request_json.call_args_list[1].args[1], "v1/init")
        self.assertEqual(
            request_json.call_args_list[1].kwargs["payload"],
            {"model": "acestep-v15-base", "slot": 1, "init_llm": False},
        )

    @patch("ace_step_dialog.download_audio")
    @patch("ace_step_dialog.wait_for_task")
    @patch("ace_step_dialog.submit_audio_task")
    def test_generation_defaults_to_source_as_timbre_reference(
        self, submit_audio_task, wait_for_task, download_audio
    ) -> None:
        submit_audio_task.return_value = "task-source"
        wait_for_task.return_value = {
            "status": 1,
            "outputs": [{"file": "/v1/audio/result"}],
        }
        request = {
            "source": "source.mp3",
            "reference": "",
            "use_source_reference": True,
            "prompt": "detailed prompt",
            "lyrics": "[Instrumental]",
            "bpm": 130,
            "key_scale": "E minor",
            "time_signature": "4",
            "duration": 20,
            "cover_strength": 1.0,
            "steps": 8,
            "random_seed": False,
            "seed": 42,
            "server": "http://192.168.0.185:8001",
            "api_key": "",
        }

        with patch.object(
            AceStepMusicCoverDialog, "_ensure_model_loaded", return_value={}
        ), patch("ace_step_dialog._prepare_source_for_duration") as prepare, patch(
            "ace_step_dialog._probe_audio_duration", return_value=19.0
        ), patch("ace_step_dialog._fit_output_duration_and_volume") as fit_output:
            payload = AceStepMusicCoverDialog._perform_generation(request)

        self.assertEqual(submit_audio_task.call_args.kwargs["reference_audio"], "source.mp3")
        self.assertEqual(submit_audio_task.call_args.kwargs["audio_duration"], 20.0)
        prepared_argument = Path(submit_audio_task.call_args.args[0])
        self.assertTrue(prepared_argument.name.startswith(".duration_guide_"))
        self.assertEqual(prepared_argument.suffix, ".wav")
        self.assertEqual(payload["record"]["status"], 1)
        self.assertTrue(payload["duration_adjusted"])
        prepare.assert_called_once()
        fit_output.assert_called_once()
        download_audio.assert_called_once()

    @patch("ace_step_dialog.download_audio")
    @patch("ace_step_dialog.wait_for_task")
    @patch("ace_step_dialog.submit_audio_task")
    def test_separate_timbre_reference_has_priority(
        self, submit_audio_task, wait_for_task, _download_audio
    ) -> None:
        submit_audio_task.return_value = "task-timbre"
        wait_for_task.return_value = {
            "status": 1,
            "outputs": [{"file": "/v1/audio/result"}],
        }
        request = {
            "source": "source.mp3",
            "reference": "timbre.wav",
            "use_source_reference": True,
            "prompt": "detailed prompt",
            "lyrics": "[Instrumental]",
            "bpm": 130,
            "key_scale": "E minor",
            "time_signature": "4",
            "duration": 20,
            "cover_strength": 0.8,
            "steps": 12,
            "random_seed": False,
            "seed": 99,
            "server": "http://192.168.0.185:8001",
            "api_key": "",
        }

        with patch.object(
            AceStepMusicCoverDialog, "_ensure_model_loaded", return_value={}
        ), patch("ace_step_dialog._prepare_source_for_duration"), patch(
            "ace_step_dialog._probe_audio_duration", return_value=19.0
        ), patch("ace_step_dialog._fit_output_duration_and_volume"):
            AceStepMusicCoverDialog._perform_generation(request)

        self.assertEqual(submit_audio_task.call_args.kwargs["reference_audio"], "timbre.wav")


if __name__ == "__main__":
    unittest.main()

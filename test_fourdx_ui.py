import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from director_cut_studio import DesignPageDialog, DirectorCue, DirectorCutStudio, TextLayer
from fourdx_engine import AI_MOVIE_MAKING_OF_4DX_SKILL, enforce_making_of_fourdx_plan


class FourDXUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = DirectorCutStudio()
        index = self.window.special_combo.findData("ai-movie-making-of-4dx")
        self.assertGreaterEqual(index, 0)
        self.window.special_combo.setCurrentIndex(index)

    def tearDown(self):
        self.window.project_dirty = False
        self.window.close()

    def test_design_controls_update_only_the_managed_block(self):
        context = self.window._design_context()
        dialog = DesignPageDialog(
            self.window.runtime,
            context,
            context["media_capacity"],
            self.window,
            context_provider=self.window._design_context,
        )
        self.assertEqual(len(dialog.fourdx_effect_checks), 10)
        self.assertTrue(all(box.isChecked() for box in dialog.fourdx_effect_checks.values()))
        story = "USER STORY SENTINEL"
        dialog.requirement_edit.appendPlainText(story)
        dialog.fourdx_effect_checks["water_rain"].setChecked(True)
        text = dialog.requirement_edit.toPlainText()
        self.assertIn(story, text)
        self.assertIn("WATER / RAIN", text)
        self.assertEqual(
            dialog._selected_design_context()["fourdx_preferences"]["intensity"],
            "medium",
        )
        dialog.close()

    def test_effect_buttons_recalculate_the_authored_duration_budget(self):
        context = self.window._design_context()
        context["design_requirement"] = "帮我创作15秒的沉浸式4DX影片。"
        dialog = DesignPageDialog(
            self.window.runtime,
            context,
            context["media_capacity"],
            self.window,
            context_provider=self.window._design_context,
        )
        for effect_id, checkbox in dialog.fourdx_effect_checks.items():
            checkbox.setChecked(effect_id == "pitch")
        self.assertIn("resolved 15s", dialog.fourdx_duration_label.text())
        dialog.requirement_edit.setPlainText(
            dialog.requirement_edit.toPlainText().replace("15秒", "12秒", 1)
        )
        self.app.processEvents()
        self.assertIn("authored 12s", dialog.fourdx_duration_label.text())
        self.assertIn("resolved 15s", dialog.fourdx_duration_label.text())
        for checkbox in dialog.fourdx_effect_checks.values():
            checkbox.setChecked(True)
        self.assertIn("minimum 60s", dialog.fourdx_duration_label.text())
        self.assertIn(
            "Resolved design duration: 60.00 seconds",
            dialog.requirement_edit.toPlainText(),
        )
        dialog.close()

    def test_workspace_snapshot_and_project_payload_keep_structured_events(self):
        self.window.fourdx_preferences = {
            "selected_effects": ["impact"], "intensity": "high", "density": "dense",
        }
        self.window.fourdx_experience_design = {"schema_version": 1}
        self.window.fourdx_physical_events = [{"event_id": "PE-001"}]
        self.window.fourdx_events = [{"event_id": "4DX-001", "physical_event_id": "PE-001"}]
        snapshot = self.window._design_workspace_state()
        payload = self.window._project_payload()
        self.assertEqual(snapshot["fourdx_physical_events"][0]["event_id"], "PE-001")
        self.assertEqual(payload["fourdx_events"][0]["physical_event_id"], "PE-001")
        self.assertEqual(payload["version"], 25)

    def test_studio_graphics_label_does_not_ask_h3_to_draw_text(self):
        self.window.text_layers = [TextLayer(
            "T1", "SOURCE PHOTOGRAPHY", 0.0, 1.0, "V4",
            timeline_visible_text_kind="making_of_stage_label",
            render_owner="studio_graphics",
        )]
        spec = self.window._prompt_spec_with_director_cues(
            self.window.prompt_panel.spec(), window_start=0.0, window_end=5.0
        )
        self.assertEqual(spec.text_ranges, [])
        self.assertIn("no Timeline on_screen_text event", spec.must_keep)

    def test_screen_plane_breakout_reaches_the_compiled_h3_prompt(self):
        plan = enforce_making_of_fourdx_plan(
            {
                "duration_seconds": 15.0,
                "shots": [],
                "text_layers": [],
                "design_warnings": [],
            },
            existing_media=[],
            preferences={
                "selected_effects": ["pitch"],
                "requested_duration_seconds": 15.0,
            },
            special_skill_key=AI_MOVIE_MAKING_OF_4DX_SKILL,
        )
        row = next(
            shot for shot in plan["shots"]
            if shot.get("screen_plane_breakout_required")
        )
        self.window.director_cues = [DirectorCue(
            cue_id=str(row["id"]),
            cue_type="shot",
            start_seconds=float(row["start_seconds"]),
            end_seconds=float(row["end_seconds"]),
            preset=str(row["preset"]),
            detail=str(row["additional_direction"]),
            framing=str(row["framing"]),
            camera_angle=str(row["camera_angle"]),
            camera_movement=str(row["camera_movement"]),
            movement_speed=str(row["movement_speed"]),
            movement_amplitude=str(row["movement_amplitude"]),
            subject_action=str(row["subject_action"]),
            environment_response=str(row["environment_response"]),
            h3_executable_action=str(row["h3_executable_action"]),
        )]
        spec = self.window._prompt_spec_with_director_cues(
            self.window.prompt_panel.spec(),
            window_start=0.5,
            window_end=14.5,
        )
        rendered = " ".join(spec.shots)
        self.assertIn("SCREEN-PLANE BREAKOUT", rendered)
        self.assertIn("occlude", rendered)
        self.assertIn("front-row", rendered)
        self.assertIn("do not duplicate the source object", rendered.lower())
        self.assertEqual(spec.music, "N/A")
        native_audio = " ".join(
            row.get("native_audio_direction", "")
            for row in spec.native_audio_ranges
        )
        self.assertIn("large purpose-built 4DX cinema auditorium", native_audio)
        self.assertIn("four simultaneously audible diegetic layers", native_audio)
        self.assertNotIn("furnished office interior", native_audio)

    def test_user_edited_fourdx_native_audio_direction_is_preserved(self):
        cue = DirectorCue(
            "S1", "shot", 0.0, 5.0, "PITCH",
            detail="LIVE 4DX EFFECT CHAPTER PITCH · FIGHTER-JET TAKEOFF",
            native_audio_direction="CUSTOM USER 4DX SOUND DIRECTION",
            native_audio_direction_user_edited=True,
        )
        self.window.director_cues = [cue]
        self.window._refresh_native_audio_directions()
        self.assertEqual(
            cue.native_audio_direction,
            "CUSTOM USER 4DX SOUND DIRECTION",
        )


if __name__ == "__main__":
    unittest.main()

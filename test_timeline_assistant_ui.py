import os
import unittest
from dataclasses import asdict

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from director_cut_studio import (
    DirectorCutStudio,
    DirectorCue,
    ShotVisualEditorDialog,
    TimelineQwenAssistantPanel,
    director_cue_from_mapping,
)


class TimelineAssistantUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_visual_speech_fields_round_trip_through_project_mapping(self):
        cue = director_cue_from_mapping({
            "cue_id": "S8",
            "cue_type": "shot",
            "start_seconds": 17.0,
            "end_seconds": 19.0,
            "preset": "Listener",
            "speech_visual_mode": "silent_listener",
            "mouth_behavior": "lips together",
            "voice_position": "behind_camera",
            "lip_sync_mode": "disabled",
            "lip_sync_target": "P2",
            "lip_sync_source": "A2",
            "future_field": "ignored",
        })
        self.assertEqual(cue.speech_visual_mode, "silent_listener")
        self.assertEqual(cue.mouth_behavior, "lips together")
        self.assertEqual(cue.voice_position, "behind_camera")
        self.assertEqual(cue.lip_sync_mode, "disabled")
        self.assertEqual(cue.lip_sync_target, "P2")
        self.assertEqual(cue.lip_sync_source, "A2")

    def test_character_identity_override_round_trips_through_project_mapping(self):
        cue = director_cue_from_mapping({
            "cue_id": "S4",
            "cue_type": "shot",
            "start_seconds": 6.0,
            "end_seconds": 8.0,
            "preset": "Encounter",
            "character_identity_overrides": {"@p2": "P4", "bad": "P3"},
        })
        self.assertEqual(cue.character_identity_overrides, {"P2": "P4"})

    def test_identity_override_replaces_exact_picture_and_preserves_other_ids(self):
        cue = DirectorCue(
            "S4", "shot", 6.0, 8.0, "Encounter",
            subject_action="@P2 turns toward @P20.",
            authored_subject_action="@P2 turns toward @P20.",
            detail="Keep @P2 on the established eyeline.",
            semantic_reference_directions={"P2": "old identity"},
            lip_sync_mode="enabled",
            lip_sync_target="P2",
            lip_sync_source="A2",
        )
        updated = DirectorCutStudio._apply_identity_override_to_state(
            asdict(cue),
            {
                "source_reference": "P2",
                "target_reference": "P4",
                "target_direction": "uploaded P4 identity",
            },
        )
        self.assertIn("@P4 turns toward @P20", updated["authored_subject_action"])
        self.assertNotIn("@P2 turns", updated["authored_subject_action"])
        self.assertEqual(updated["character_identity_overrides"], {"P2": "P4"})
        self.assertEqual(updated["lip_sync_target"], "P4")
        self.assertIn("P4", updated["semantic_reference_directions"])
        self.assertNotIn("P2", updated["semantic_reference_directions"])

    def test_all_character_swap_is_atomic_in_one_shot(self):
        cue = DirectorCue(
            "S5", "shot", 8.0, 10.0, "Two shot",
            subject_action="@P1 confronts @P2 while @P20 watches.",
            authored_subject_action="@P1 confronts @P2 while @P20 watches.",
            semantic_reference_directions={
                "P1": "first original identity",
                "P2": "second original identity",
            },
        )
        updated = DirectorCutStudio._apply_identity_overrides_to_state(
            asdict(cue),
            [
                {"source_reference": "P1", "target_reference": "P2"},
                {"source_reference": "P2", "target_reference": "P1"},
            ],
        )
        self.assertIn(
            "@P2 confronts @P1 while @P20 watches",
            updated["authored_subject_action"],
        )
        self.assertEqual(
            updated["character_identity_overrides"],
            {"P1": "P2", "P2": "P1"},
        )
        self.assertEqual(set(updated["semantic_reference_directions"]), {"P1", "P2"})

    def test_all_character_swap_updates_v1_bindings_without_cascade(self):
        fake = type("FakeStudio", (), {})()
        fake.source_video_role_bindings = [
            {
                "source_role_id": "R1", "target_media_id": "P1",
                "scene_indexes": [1], "identity_lock": "strict",
                "source_thumbnail": False,
            },
            {
                "source_role_id": "R2", "target_media_id": "P2",
                "scene_indexes": [1], "identity_lock": "strict",
                "source_thumbnail": False,
            },
        ]
        fake._reference_asset = lambda _reference: None
        shot = DirectorCue("S1", "shot", 0.0, 5.0, "Two shot")
        updated = DirectorCutStudio._updated_source_role_bindings_for_identity_changes(
            fake,
            [
                ({
                    "source_reference": "P1", "target_reference": "P2",
                    "scope": "all_role_appearances",
                }, [shot]),
                ({
                    "source_reference": "P2", "target_reference": "P1",
                    "scope": "all_role_appearances",
                }, [shot]),
            ],
        )
        mapped = {
            row["source_role_id"]: row["target_media_id"] for row in updated
        }
        self.assertEqual(mapped, {"R1": "P2", "R2": "P1"})

    def test_shot_visual_editor_exposes_structured_controls(self):
        cue = DirectorCue(
            "S8", "shot", 17.0, 19.0, "Listener",
            subject_action="P2 listens.",
            speech_visual_mode="silent_listener",
            mouth_behavior="closed mouth",
            voice_position="behind_camera",
            lip_sync_mode="enabled",
            lip_sync_target="P2",
            lip_sync_source="A2",
        )
        dialog = ShotVisualEditorDialog(cue, 30.0)
        try:
            state = dialog.state()
            self.assertEqual(state["speech_visual_mode"], "silent_listener")
            self.assertEqual(state["mouth_behavior"], "closed mouth")
            self.assertEqual(state["voice_position"], "behind_camera")
            self.assertEqual(state["lip_sync_mode"], "enabled")
            self.assertEqual(state["lip_sync_target"], "P2")
            self.assertEqual(state["lip_sync_source"], "A2")
            self.assertIn("@P2 follows @A2", dialog.lip_sync_value.text())
            self.assertEqual(dialog.repair_scope(), "linked_continuity")
            self.assertEqual(dialog.identity_changes(), [])
        finally:
            dialog.close()

    def test_assistant_panel_renders_checkable_patch_review(self):
        panel = TimelineQwenAssistantPanel()
        try:
            panel.set_proposal({
                "summary": "Keep S8 silent",
                "warnings": [],
                "operations": [{
                    "target_kind": "shot",
                    "target_id": "S8",
                    "field": "speech_visual_mode",
                    "value": "silent_listener",
                    "reason": "Voice remains behind camera",
                    "requires_confirmation": False,
                }],
            })
            self.assertEqual(panel.patch_list.count(), 1)
            self.assertEqual(len(panel.selected_operations()), 1)
            self.assertTrue(panel.apply_button.isEnabled())
        finally:
            panel.close()

    def test_structured_silent_listener_reaches_compiled_h3_shot(self):
        window = DirectorCutStudio()
        try:
            self.assertTrue(window.settings_pre_generation_unload.isChecked())
            window.director_cues = [DirectorCue(
                "S8", "shot", 0.0, 5.0, "Reaction",
                subject_action="P2 reacts to the voice behind camera.",
                speech_visual_mode="silent_listener",
                mouth_behavior="lips naturally together; jaw still",
                voice_position="behind_camera",
            )]
            spec = window._prompt_spec_with_director_cues(window.prompt_panel.spec())
            compiled = spec.shots[0]
            self.assertIn("VISIBLE SPEECH STATE", compiled)
            self.assertIn("silent listener", compiled)
            self.assertIn("MOUTH PERFORMANCE", compiled)
            self.assertIn("behind camera", compiled)
            self.assertIn(
                "VISIBLE LISTENER LOCK",
                spec.native_audio_ranges[0]["native_audio_direction"],
            )
        finally:
            window.project_dirty = False
            window.close()

    def test_reviewed_patch_is_one_undoable_transaction(self):
        window = DirectorCutStudio()
        try:
            cue = DirectorCue("S2", "shot", 0.0, 5.0, "Reaction")
            window.director_cues = [cue]
            window._refresh_director_cues()
            window.timeline_assistant_target_shot_id = "S2"
            window.timeline_assistant_last_scope = "linked_continuity"
            window._apply_timeline_assistant_operations([{
                "target_kind": "shot",
                "target_id": "S2",
                "field": "speech_visual_mode",
                "value": "silent_listener",
                "reason": "Voice is behind camera",
                "requires_confirmation": False,
            }])
            self.assertEqual(cue.speech_visual_mode, "silent_listener")
            self.assertTrue(window.undo_stack.canUndo())
            window.undo_stack.undo()
            self.assertEqual(cue.speech_visual_mode, "auto")
        finally:
            window.project_dirty = False
            window.close()

    def test_linked_qwen_performance_patch_dirties_only_its_segment(self):
        window = DirectorCutStudio()
        try:
            window._set_design_duration(45.0)
            window.director_cues = [
                DirectorCue("S1", "shot", 1.0, 4.0, "Opening"),
                DirectorCue("S2", "shot", 16.0, 19.0, "Middle"),
                DirectorCue("S3", "shot", 31.0, 34.0, "Ending"),
            ]
            window._refresh_director_cues()
            window.render_dirty_segment_ids.clear()
            window.render_dirty_previewed_segment_ids.clear()
            window.timeline_assistant_target_shot_id = "S2"
            window.timeline_assistant_last_scope = "linked_continuity"
            window._apply_timeline_assistant_operations([{
                "target_kind": "shot",
                "target_id": "S2",
                "field": "camera_movement",
                "value": "slow lateral track",
                "reason": "Refine only this Shot's camera",
                "requires_confirmation": False,
            }])
            dirty = [
                segment for segment in window._planned_render_segments()
                if segment.segment_id in window.render_dirty_segment_ids
            ]
            self.assertEqual(len(dirty), 1)
            self.assertLess(dirty[0].start_seconds, 19.0)
            self.assertGreater(dirty[0].end_seconds, 16.0)
        finally:
            window.project_dirty = False
            window.close()

    def test_regenerate_dirty_action_appears_only_for_stale_segments(self):
        window = DirectorCutStudio()
        try:
            self.assertFalse(window.regenerate_dirty_action.isVisible())
            window.render_dirty_segment_ids.add("seg_0_15")
            window._refresh_regenerate_dirty_button()
            self.assertTrue(window.regenerate_dirty_action.isVisible())
            self.assertEqual(window.regenerate_dirty_button.text(), "REGENERATE DIRTY")
            window.render_dirty_segment_ids.add("seg_15_30")
            window._refresh_regenerate_dirty_button()
            self.assertIn("(2)", window.regenerate_dirty_button.text())
            window.render_dirty_previewed_segment_ids.add("seg_0_15")
            window._refresh_regenerate_dirty_button()
            self.assertTrue(window.regenerate_dirty_action.isVisible())
            self.assertEqual(window.regenerate_dirty_button.text(), "REGENERATE DIRTY")
            window.render_dirty_previewed_segment_ids.add("seg_15_30")
            window._refresh_regenerate_dirty_button()
            self.assertFalse(window.regenerate_dirty_action.isVisible())
            window.render_dirty_previewed_segment_ids.remove("seg_15_30")
            window._refresh_regenerate_dirty_button()
            self.assertTrue(window.regenerate_dirty_action.isVisible())
            window.render_dirty_segment_ids.clear()
            window._refresh_regenerate_dirty_button()
            self.assertFalse(window.regenerate_dirty_action.isVisible())
        finally:
            window.project_dirty = False
            window.close()

    def test_regenerate_dirty_preserves_already_previewed_repairs(self):
        window = DirectorCutStudio()
        try:
            window._set_design_duration(45.0)
            planned = window._planned_render_segments()
            first_id = planned[0].segment_id
            second_id = planned[1].segment_id
            window.render_dirty_segment_ids = {first_id, second_id}
            window.render_dirty_previewed_segment_ids = {first_id}
            calls = []
            window.generate_pre_run_preview = lambda reuse_clean_segments=False: calls.append(
                reuse_clean_segments
            )

            window.regenerate_dirty_segments()

            self.assertEqual(window.active_dirty_regeneration_ids, {second_id})
            self.assertEqual(window.render_dirty_previewed_segment_ids, {first_id})
            self.assertEqual(calls, [True])
        finally:
            window.project_dirty = False
            window.close()


if __name__ == "__main__":
    unittest.main()

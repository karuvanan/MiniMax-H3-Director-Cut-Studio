"""Release-gate regressions for the complete H3 Director pipeline.

Run this file before generating a new project whenever Timeline, Design,
reference mapping, track handling or long-render continuity code changes.
The four tests intentionally describe user-visible invariants instead of
individual helper implementations.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtWidgets import QApplication

from design_engine import normalize_design_plan
from director_cut_studio import (
    DirectorCue,
    DirectorCutStudio,
    media_shortcut,
    timeline_state,
)
from test_design_engine import sample_design
from runtime_paths import PROJECT_ROOT
from workflow_engine import assign_local_media


class StandardPipelineRegressions(unittest.TestCase):
    """The small, mandatory release gate for the four highest-risk flows."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _place(asset, start: float, end: float, track: str, prompt: str):
        asset.timeline_placed = True
        asset.timeline_track_id = track
        asset.start_seconds = float(start)
        asset.end_seconds = float(end)
        asset.clip_prompt = prompt
        return asset

    @staticmethod
    def _h3_inputs(window: DirectorCutStudio, workflow: dict) -> dict:
        return workflow[window.scan.h3_node_ids[0]]["inputs"]

    @staticmethod
    def _prompt(workflow: dict) -> str:
        return next(
            node["inputs"]["value"]
            for node in workflow.values()
            if node.get("class_type") == "PrimitiveStringMultiline"
        )

    @staticmethod
    def _close(window: DirectorCutStudio) -> None:
        window.project_dirty = False
        window.close()

    def test_01_sparse_picture_video_audio_mapping_matches_executable_slots(self):
        """Stable P/V/A IDs must compile to the exact request-local H3 slots."""

        window = DirectorCutStudio()
        self.addCleanup(self._close, window)
        window._set_design_duration(30.0)
        pictures = [asset for asset in window.scan.assets if asset.media_type == "image"]
        videos = [asset for asset in window.scan.assets if asset.media_type == "video"]
        audios = [asset for asset in window.scan.assets if asset.media_type == "audio"]
        p4 = self._place(pictures[3], 0.0, 15.0, "V1", "Opening identity @P4.")
        p7 = self._place(pictures[6], 15.0, 30.0, "V2", "Later location @P7.")
        v2 = self._place(videos[1], 15.0, 30.0, "V3", "Follow @V2 motion.")
        a3 = self._place(audios[2], 15.0, 30.0, "A2", "Use @A3 sound.")

        first, first_assets = window._compiled_window_job(
            0.0, 15.0, megapixels=0.2, seed=4101,
            enable_rtx_vsr=False, is_final_window=False,
            continuity_mode="none",
        )[:2]
        second, second_assets = window._compiled_window_job(
            15.0, 30.0, megapixels=0.2, seed=4102,
            enable_rtx_vsr=False, is_final_window=True,
            continuity_mode="none",
        )[:2]

        self.assertEqual(first_assets, [p4])
        self.assertEqual({media_shortcut(asset) for asset in second_assets}, {"P7", "V2", "A3"})
        first_h3 = self._h3_inputs(window, first)
        second_h3 = self._h3_inputs(window, second)
        self.assertEqual(first_h3["ref_images.ref_image_0"], [p4.node_id, 0])
        self.assertEqual(second_h3["ref_images.ref_image_0"], [p7.node_id, 0])
        self.assertEqual(
            second_h3["ref_videos.ref_video_0"],
            window.scan.nodes[window.scan.h3_node_ids[0]]["inputs"][v2.binding],
        )
        self.assertEqual(
            second_h3["ref_audios.ref_audio_0"],
            window.scan.nodes[window.scan.h3_node_ids[0]]["inputs"][a3.binding],
        )
        self.assertNotIn("ref_images.ref_image_1", second_h3)
        self.assertNotIn("ref_videos.ref_video_1", second_h3)
        self.assertNotIn("ref_audios.ref_audio_1", second_h3)
        first_prompt, second_prompt = self._prompt(first), self._prompt(second)
        self.assertIn("<Picture 1>", first_prompt)
        self.assertIn("<Picture 1>", second_prompt)
        self.assertIn("<Video 1>", second_prompt)
        self.assertIn("<Audio 2>", second_prompt)
        self.assertNotIn("@P", first_prompt + second_prompt)
        self.assertNotIn("@V", first_prompt + second_prompt)
        self.assertNotIn("@A", first_prompt + second_prompt)

    def test_02_design_apply_then_media_move_reconciles_shots_and_prompt(self):
        """A post-Design clip edit must immediately become Timeline truth."""

        window = DirectorCutStudio()
        self.addCleanup(self._close, window)
        root = PROJECT_ROOT / ".director_cache" / "standard_pipeline_regressions"
        root.mkdir(parents=True, exist_ok=True)
        picture_path = root / "subject.png"
        audio_path = root / "voice.wav"
        self.addCleanup(picture_path.unlink, missing_ok=True)
        self.addCleanup(audio_path.unlink, missing_ok=True)
        try:
            Image.new("RGB", (40, 40), (28, 52, 76)).save(picture_path)
            audio_path.write_bytes(b"test fixture")
            picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
            audio = next(asset for asset in window.scan.assets if asset.media_type == "audio")
            assign_local_media(window.scan, picture, picture_path)
            assign_local_media(window.scan, audio, audio_path)

            payload = sample_design()
            payload["media_requests"] = []
            payload["existing_media_uses"] = [
                {
                    "requirement_id": "subject",
                    "media_id": "P1",
                    "media_type": "image",
                    "usage": "h3_reference",
                    "reuse_policy": "time_scoped",
                    "start_seconds": 0.1,
                    "end_seconds": 4.2,
                    "track": "A2",  # Deliberately wrong; Design must repair it.
                    "subject_keywords": ["subject"],
                    "instruction": "Original Design subject reference.",
                },
                {
                    "requirement_id": "voice",
                    "media_id": "A1",
                    "media_type": "audio",
                    "usage": "h3_reference",
                    "reuse_policy": "whole_design",
                    "start_seconds": 0.0,
                    "end_seconds": 12.1,
                    "track": "V2",  # Deliberately wrong; Design must repair it.
                    "subject_keywords": ["voice"],
                    "instruction": "Keep the supplied voice synchronized.",
                },
            ]
            plan = normalize_design_plan(
                payload,
                window.scan.counts,
                existing_media=window._design_context()["existing_media"],
            )
            self.assertEqual(window._apply_ai_design_direct(plan, [], replace=True), [])
            self.assertTrue(picture.timeline_track_id.startswith("V"))
            self.assertTrue(audio.timeline_track_id.startswith("A"))

            semantic = {
                "summary": "The supplied subject stands in a grounded interior.",
                "observed_facts": ["One supplied subject is visible."],
                "subjects": [],
                "objects_and_props": [],
                "environment": "A grounded interior.",
                "composition_and_camera": "Medium composition.",
                "lighting_and_color": "Soft neutral light.",
                "motion_and_temporal_changes": "",
                "audio_and_speech": "",
                "h3_prompt_keywords": ["grounded subject"],
                "suggested_h3_usage": "Use as the subject reference.",
                "shot_adaptations": [],
            }
            self.assertEqual(
                window._sync_semantic_enrichment_to_existing_shots(picture, semantic),
                ["S1"],
            )
            self.assertIn("P1", window.director_cues[0].semantic_reference_directions)

            before = timeline_state(picture)
            original_range = (before["start_seconds"], before["end_seconds"])
            after = dict(before)
            after.update(
                timeline_track_id="V3",
                timeline_lane=next(
                    index for index, track in enumerate(window.tracks) if track.track_id == "V3"
                ),
                start_seconds=6.0,
                end_seconds=10.0,
                clip_prompt="Replacement timing and role after Design Apply.",
            )
            window.commit_asset_edit(picture, before, after)
            self.app.processEvents()

            self.assertEqual((picture.start_seconds, picture.end_seconds), (6.0, 10.0))
            self.assertEqual(picture.timeline_track_id, "V3")
            first_shot = next(cue for cue in window.director_cues if cue.cue_id == "S1")
            second_shot = next(cue for cue in window.director_cues if cue.cue_id == "S2")
            self.assertNotIn("P1", first_shot.semantic_reference_directions)
            self.assertIn(
                "P1",
                second_shot.semantic_reference_directions,
                msg=str([
                    (
                        cue.cue_id,
                        cue.start_seconds,
                        cue.end_seconds,
                        cue.semantic_reference_directions,
                    )
                    for cue in window.director_cues
                ]),
            )
            brief = window.prompt_panel.brief.toPlainText()
            self.assertIn("@P1 at 6.00-10.00s", brief)
            self.assertIn("Replacement timing and role", brief)
            self.assertNotIn("Original Design subject reference", brief)

            window.undo_stack.undo()
            self.app.processEvents()
            self.assertEqual((picture.start_seconds, picture.end_seconds), original_range)
            self.assertIn("P1", first_shot.semantic_reference_directions)
            self.assertNotIn("P1", second_shot.semantic_reference_directions)
            window.undo_stack.redo()
            self.app.processEvents()
            self.assertEqual((picture.start_seconds, picture.end_seconds), (6.0, 10.0))
            self.assertNotIn("P1", first_shot.semantic_reference_directions)
            self.assertIn("P1", second_shot.semantic_reference_directions)

            early_assets = window._compiled_window_job(
                0.0, 4.2, megapixels=0.2, seed=4201,
                enable_rtx_vsr=False, is_final_window=False,
                continuity_mode="none",
            )[1]
            late_workflow, late_assets = window._compiled_window_job(
                6.0, 10.0, megapixels=0.2, seed=4202,
                enable_rtx_vsr=False, is_final_window=True,
                continuity_mode="none",
            )[:2]
            self.assertNotIn(picture, early_assets)
            self.assertIn(picture, late_assets)
            self.assertIn("<Picture 1>", self._prompt(late_workflow))
        finally:
            picture_path.unlink(missing_ok=True)
            audio_path.unlink(missing_ok=True)

    def test_03_visual_and_audio_assets_cannot_survive_on_wrong_track_kind(self):
        """Corrupt/legacy lane data must be repaired before display or render."""

        window = DirectorCutStudio()
        self.addCleanup(self._close, window)
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        audio = next(asset for asset in window.scan.assets if asset.media_type == "audio")
        a2_index = next(index for index, track in enumerate(window.tracks) if track.track_id == "A2")
        v2_index = next(index for index, track in enumerate(window.tracks) if track.track_id == "V2")
        self._place(picture, 0.0, 5.0, "A2", "Visual fixture.")
        picture.timeline_lane = a2_index
        self._place(audio, 0.0, 5.0, "V2", "Audio fixture.")
        audio.timeline_lane = v2_index

        self.assertEqual(window._track_for_asset(picture).kind, "visual")
        self.assertEqual(window._track_for_asset(audio).kind, "audio")
        window.timeline.rebuild()
        self.app.processEvents()
        self.assertTrue(picture.timeline_track_id.startswith("V"))
        self.assertTrue(audio.timeline_track_id.startswith("A"))
        picture_track = next(track for track in window.tracks if track.track_id == picture.timeline_track_id)
        audio_track = next(track for track in window.tracks if track.track_id == audio.timeline_track_id)
        self.assertEqual(picture_track.kind, "visual")
        self.assertEqual(audio_track.kind, "audio")

    def test_04_native_15_second_boundaries_use_context_without_replay_or_collision(self):
        """Each native job starts new action and reserves a non-colliding 24-frame context."""

        window = DirectorCutStudio()
        self.addCleanup(self._close, window)
        window._set_design_duration(45.0)
        for asset in window.scan.timeline_assets():
            asset.timeline_placed = False
        pictures = [asset for asset in window.scan.assets if asset.media_type == "image"]
        videos = [asset for asset in window.scan.assets if asset.media_type == "video"]
        self._place(pictures[3], 0.0, 15.0, "V1", "Phase one identity @P4.")
        self._place(pictures[6], 15.0, 30.0, "V1", "Phase two location @P7.")
        self._place(pictures[8], 30.0, 45.0, "V1", "Phase three finish @P9.")
        phase_two_video = self._place(videos[1], 15.0, 30.0, "V2", "Phase two motion @V2.")
        phase_three_video = self._place(videos[2], 30.0, 45.0, "V2", "Phase three motion @V3.")
        window.director_cues = [
            DirectorCue(
                "S1", "shot", 0.0, 15.0, "PHASE_ONE_UNIQUE",
                subject_action="The hero launches the first attack and remains airborne at the boundary.",
                continuity_state="At 15 seconds the hero is airborne, moving screen-right.",
                track_id="V1",
            ),
            DirectorCue(
                "S2", "shot", 15.0, 30.0, "PHASE_TWO_UNIQUE",
                subject_action="Begin with the hero still airborne, then land and pursue across the roof.",
                continuity_state="At 30 seconds both fighters leave the roof toward the pond.",
                track_id="V1",
            ),
            DirectorCue(
                "S3", "shot", 30.0, 45.0, "PHASE_THREE_UNIQUE",
                subject_action="Begin above the pond, complete the final pass and escape upward.",
                continuity_state="Finish after the final pass; do not restart an earlier attack.",
                track_id="V1",
            ),
        ]
        window.clip_start.setValue(0.0)
        window.clip_end.setValue(45.0)

        job_path, count = window._build_smart_render_job(
            request_kind="preview", megapixels=0.2, seed=4300,
            enable_rtx_vsr=False,
        )
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(count, 3)
        self.assertEqual(
            [(row["start_seconds"], row["end_seconds"]) for row in job["segments"]],
            [(0.0, 15.0), (15.0, 30.0), (30.0, 45.0)],
        )
        self.assertTrue(all(row["overlap_before_seconds"] == 0.0 for row in job["segments"]))
        prompts = [self._prompt(row["workflow"]) for row in job["segments"]]
        for index, unique in enumerate(
            ("PHASE_ONE_UNIQUE", "PHASE_TWO_UNIQUE", "PHASE_THREE_UNIQUE")
        ):
            self.assertIn(unique, prompts[index])
            self.assertTrue(
                all(unique not in prompt for other, prompt in enumerate(prompts) if other != index)
            )
        for segment, active_video in zip(job["segments"][1:], (phase_two_video, phase_three_video)):
            continuity = segment["continuity"]
            h3 = self._h3_inputs(window, segment["workflow"])
            prompt = self._prompt(segment["workflow"])
            self.assertEqual(continuity["kind"], "video")
            self.assertEqual(continuity["frame_count"], 24)
            self.assertEqual(continuity["binding"], "ref_videos.ref_video_1")
            self.assertEqual(continuity["tag"], "<Video 2>")
            self.assertIn("Do not replay", prompt)
            self.assertIn("ref_videos.ref_video_0", h3)
            self.assertNotIn("ref_videos.ref_video_1", h3)
            self.assertEqual(
                h3["ref_videos.ref_video_0"],
                window.scan.nodes[window.scan.h3_node_ids[0]]["inputs"][active_video.binding],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

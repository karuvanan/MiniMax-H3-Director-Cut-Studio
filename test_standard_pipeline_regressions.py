"""Release-gate regressions for the complete H3 Director pipeline.

Run this file before generating a new project whenever Timeline, Design,
reference mapping, track handling or long-render continuity code changes.
The five tests intentionally describe user-visible invariants instead of
individual helper implementations.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtWidgets import QApplication

import comfy_submit_worker
from design_engine import normalize_design_plan
from director_cut_studio import (
    DirectorCue,
    DirectorCutStudio,
    media_shortcut,
    resolve_project_media_path,
    timeline_state,
)
from test_design_engine import sample_design
from runtime_paths import PROJECT_ROOT
import smart_render_worker
from workflow_engine import (
    assign_local_media,
    create_virtual_media_asset,
    media_upload_manifest,
    patch_media_upload_names,
    validate_portable_media_manifest,
)


class StandardPipelineRegressions(unittest.TestCase):
    """The small, mandatory release gate for the five highest-risk flows."""

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
        """P/V/A mapping and copied image/audio/video files must stay executable."""

        window = DirectorCutStudio()
        self.addCleanup(self._close, window)
        portable_root = (
            PROJECT_ROOT / ".director_cache" / "standard_release_gate_media"
        )
        portable_root.mkdir(parents=True, exist_ok=True)
        window._set_design_duration(30.0)
        pictures = [asset for asset in window.scan.assets if asset.media_type == "image"]
        videos = [asset for asset in window.scan.assets if asset.media_type == "video"]
        audios = [asset for asset in window.scan.assets if asset.media_type == "audio"]
        p10 = create_virtual_media_asset(window.scan, "image")
        v4 = create_virtual_media_asset(window.scan, "video")
        a4 = create_virtual_media_asset(window.scan, "audio")
        local_files = {
            pictures[3].node_id: portable_root / "copied_subject.png",
            pictures[6].node_id: portable_root / "copied_location.webp",
            videos[1].node_id: portable_root / "copied_motion.mp4",
            audios[2].node_id: portable_root / "copied_dialogue.wav",
            p10.node_id: portable_root / "virtual_p10.png",
            v4.node_id: portable_root / "virtual_v4.mp4",
            a4.node_id: portable_root / "virtual_a4.wav",
        }
        for fixture in local_files.values():
            self.addCleanup(fixture.unlink, missing_ok=True)
        Image.new("RGB", (16, 16), (22, 44, 66)).save(
            local_files[pictures[3].node_id]
        )
        Image.new("RGB", (16, 16), (66, 44, 22)).save(
            local_files[pictures[6].node_id]
        )
        Image.new("RGB", (16, 16), (22, 66, 44)).save(local_files[p10.node_id])
        local_files[videos[1].node_id].write_bytes(b"portable-video-fixture")
        local_files[audios[2].node_id].write_bytes(b"portable-audio-fixture")
        local_files[v4.node_id].write_bytes(b"virtual-video-fixture")
        local_files[a4.node_id].write_bytes(b"virtual-audio-fixture")
        for asset in (pictures[3], pictures[6], videos[1], audios[2], p10, v4, a4):
            assign_local_media(window.scan, asset, local_files[asset.node_id])

        # Simulate a project copied from an unavailable drive.  All supported
        # media types must resolve beside the moved project by basename rather
        # than retaining the former machine's absolute path.
        moved_project = portable_root / "director_project.h3director.json"
        old_root = Path("Z:/old-computer/example/portable_project")
        for asset in (pictures[3], pictures[6], videos[1], audios[2], p10, v4, a4):
            resolved = resolve_project_media_path(
                moved_project,
                {
                    "filename": local_files[asset.node_id].name,
                    "local_path": str(old_root / local_files[asset.node_id].name),
                },
                old_root,
            )
            self.assertEqual(resolved, local_files[asset.node_id].resolve())
        p4 = self._place(pictures[3], 0.0, 15.0, "V1", "Opening identity @P4.")
        p7 = self._place(pictures[6], 15.0, 30.0, "V2", "Later location @P7.")
        v2 = self._place(videos[1], 15.0, 30.0, "V3", "Follow @V2 motion.")
        a3 = self._place(audios[2], 15.0, 30.0, "A2", "Use @A3 sound.")
        self._place(p10, 20.0, 30.0, "V1", "Virtual later reference @P10.")
        self._place(v4, 20.0, 30.0, "V2", "Virtual motion @V4.")
        self._place(a4, 20.0, 30.0, "A1", "Virtual sound @A4.")

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
        self.assertEqual(
            {media_shortcut(asset) for asset in second_assets},
            {"P7", "P10", "V2", "V4", "A3", "A4"},
        )
        first_h3 = self._h3_inputs(window, first)
        second_h3 = self._h3_inputs(window, second)
        self.assertEqual(first_h3["ref_images.ref_image_0"], [pictures[0].node_id, 0])
        self.assertEqual(second_h3["ref_images.ref_image_0"], [pictures[0].node_id, 0])
        self.assertEqual(second_h3["ref_images.ref_image_1"], [pictures[1].node_id, 0])
        self.assertEqual(
            second_h3["ref_videos.ref_video_0"],
            window.scan.nodes[window.scan.h3_node_ids[0]]["inputs"][videos[0].binding],
        )
        self.assertEqual(
            second_h3["ref_audios.ref_audio_0"],
            window.scan.nodes[window.scan.h3_node_ids[0]]["inputs"][audios[0].binding],
        )
        self.assertIn("ref_videos.ref_video_1", second_h3)
        self.assertIn("ref_audios.ref_audio_1", second_h3)
        first_prompt, second_prompt = self._prompt(first), self._prompt(second)
        self.assertIn("<Picture 1>", first_prompt)
        self.assertIn("<Picture 1>", second_prompt)
        self.assertIn("<Picture 2>", second_prompt)
        self.assertIn("<Video 1>", second_prompt)
        self.assertIn("<Video 2>", second_prompt)
        self.assertIn("<Audio 3>", second_prompt)
        self.assertIn("<Audio 4>", second_prompt)
        self.assertNotIn("@P", first_prompt + second_prompt)
        self.assertNotIn("@V", first_prompt + second_prompt)
        self.assertNotIn("@A", first_prompt + second_prompt)

        first_uploads = media_upload_manifest(first_assets)
        second_uploads = media_upload_manifest(second_assets)
        patch_media_upload_names(first, first_uploads)
        patch_media_upload_names(second, second_uploads)
        validate_portable_media_manifest(first, first_uploads)
        validate_portable_media_manifest(second, second_uploads)

        # Ori/native dialogue and every other inactive pool slot must not carry
        # a stale WAV/image/video widget into the compiled ComfyUI request.
        stale_audio = audios[0]
        window.scan.nodes[stale_audio.node_id]["inputs"]["audio"] = (
            r"Z:\old-computer\ComfyUI\input\authored_timeline_dialogue_30.00s.wav"
        )
        stale_audio.local_path = ""
        stale_audio.timeline_placed = False
        native_workflow = window._compiled_window_job(
            0.0, 15.0, megapixels=0.2, seed=4103,
            enable_rtx_vsr=False, is_final_window=False,
            continuity_mode="none",
        )[0]
        self.assertNotIn(stale_audio.node_id, native_workflow)
        self.assertNotIn("old-computer", json.dumps(native_workflow))

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
        media_root = (
            PROJECT_ROOT / ".director_cache" / "standard_release_gate_segments"
        )
        media_root.mkdir(parents=True, exist_ok=True)
        for index, asset in enumerate(
            (pictures[3], pictures[6], pictures[8], videos[1], videos[2]), 1
        ):
            suffix = ".mp4" if asset.media_type == "video" else ".png"
            fixture = media_root / f"{asset.media_type}_{index}{suffix}"
            if asset.media_type == "image":
                Image.new("RGB", (16, 16), (index * 20, 30, 40)).save(fixture)
            else:
                fixture.write_bytes(b"portable-segment-video")
            self.addCleanup(fixture.unlink, missing_ok=True)
            assign_local_media(window.scan, asset, fixture)
        self._place(pictures[3], 0.0, 15.0, "V1", "Phase one identity @P4.")
        self._place(pictures[6], 15.0, 30.0, "V1", "Phase two location @P7.")
        self._place(pictures[8], 30.0, 45.0, "V1", "Phase three finish @P9.")
        phase_two_video = self._place(videos[1], 15.0, 30.0, "V2", "Phase two motion @V2.")
        phase_three_video = self._place(videos[2], 30.0, 45.0, "V2", "Phase three motion @V3.")
        window.director_cues = [
            DirectorCue(
                "S1", "shot", 0.0, 15.0, "PHASE_ONE_UNIQUE",
                subject_action="The hero launches the first attack and remains airborne at the boundary.",
                environment_response="The action is inside a small furnished office with close walls.",
                continuity_state="At 15 seconds the hero is airborne, moving screen-right.",
                track_id="V1",
            ),
            DirectorCue(
                "S2", "shot", 15.0, 30.0, "PHASE_TWO_UNIQUE",
                subject_action="Begin with the hero still airborne, then land and pursue across the roof.",
                environment_response="The action crosses a vast enclosed station concourse and large hall.",
                continuity_state="At 30 seconds both fighters leave the roof toward the pond.",
                track_id="V1",
            ),
            DirectorCue(
                "S3", "shot", 30.0, 45.0, "PHASE_THREE_UNIQUE",
                subject_action="Begin above the pond, complete the final pass and escape upward.",
                environment_response="The finish occurs in an open exterior courtyard beside the pond.",
                continuity_state="Finish after the final pass; do not restart an earlier attack.",
                track_id="V1",
            ),
        ]
        window.prompt_panel.style.setPlainText(
            "EARLY_STYLE cotton daylight (0-15s). "
            "MIDDLE_STYLE neon rain (15-30s). "
            "LATE_STYLE moonlit courtyard (30-45s). TIMELESS_STYLE cinematic realism."
        )
        window.prompt_panel.soundscape.setPlainText(
            "EARLY_SOUND market crowd (0-15s). "
            "MIDDLE_SOUND rooftop rain (15-30s). "
            "LATE_SOUND quiet wind (30-45s)."
        )
        window.prompt_panel.music.setPlainText(
            "EARLY_MUSIC drums (0-15s). MIDDLE_MUSIC strings (15-30s). "
            "LATE_MUSIC silence (30-45s)."
        )
        window.prompt_panel.constraints.setPlainText(
            "Keep identity stable. EARLY_BOUNDARY_CHANGE occurs at 14s. "
            "MIDDLE_BOUNDARY_CHANGE occurs at 22s. LATE_BOUNDARY_CHANGE occurs at 38s."
        )
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
        for field_tokens in (
            ("EARLY_STYLE", "MIDDLE_STYLE", "LATE_STYLE"),
            ("EARLY_SOUND", "MIDDLE_SOUND", "LATE_SOUND"),
            ("EARLY_MUSIC", "MIDDLE_MUSIC", "LATE_MUSIC"),
            ("EARLY_BOUNDARY_CHANGE", "MIDDLE_BOUNDARY_CHANGE", "LATE_BOUNDARY_CHANGE"),
        ):
            for index, unique in enumerate(field_tokens):
                self.assertIn(unique, prompts[index])
                self.assertTrue(
                    all(
                        unique not in prompt
                        for other, prompt in enumerate(prompts)
                        if other != index
                    ),
                    msg=f"{unique} leaked across segment prompts",
                )
        self.assertTrue(all("SEGMENT-LOCAL VISUAL STYLE SCHEDULE" in prompt for prompt in prompts))
        self.assertTrue(all("TIMELESS_STYLE" in prompt for prompt in prompts))
        self.assertTrue(all("Production mix contract" in prompt for prompt in prompts))
        self.assertTrue(all("Spatial acoustics contract" in prompt for prompt in prompts))
        self.assertTrue(all("Music mix contract" in prompt for prompt in prompts))
        self.assertTrue(all("SHOT SOUND EXECUTION" in prompt for prompt in prompts))
        self.assertTrue(all("SHOT SPATIAL ACOUSTICS" in prompt for prompt in prompts))
        acoustic_tokens = (
            "small furnished room",
            "large interior",
            "open exterior",
        )
        for index, unique in enumerate(acoustic_tokens):
            self.assertIn(unique, prompts[index])
            self.assertTrue(
                all(unique not in prompt for other, prompt in enumerate(prompts) if other != index),
                msg=f"{unique} leaked across native acoustic schedules",
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
                window.scan.nodes[window.scan.h3_node_ids[0]]["inputs"][videos[0].binding],
            )

        # A Shot-local acoustic edit must change only its own Segment prompt and
        # fingerprint. It must never renumber P/V/A references or continuity.
        reference_maps_before = [
            {
                key: value
                for key, value in self._h3_inputs(window, segment["workflow"]).items()
                if key.startswith(("ref_images.", "ref_videos.", "ref_audios."))
            }
            for segment in job["segments"]
        ]
        fingerprints_before = [segment["fingerprint"] for segment in job["segments"]]
        continuity_before = [
            {
                key: value
                for key, value in segment["continuity"].items()
                if key in {"kind", "frame_count", "binding", "tag"}
            }
            for segment in job["segments"]
        ]
        window.director_cues[1].environment_response = (
            "The same middle action now moves through a narrow enclosed corridor and stairwell."
        )
        edited_path, edited_count = window._build_smart_render_job(
            request_kind="preview", megapixels=0.2, seed=4300,
            enable_rtx_vsr=False,
        )
        edited = json.loads(edited_path.read_text(encoding="utf-8"))
        self.assertEqual(edited_count, 3)
        reference_maps_after = [
            {
                key: value
                for key, value in self._h3_inputs(window, segment["workflow"]).items()
                if key.startswith(("ref_images.", "ref_videos.", "ref_audios."))
            }
            for segment in edited["segments"]
        ]
        continuity_after = [
            {
                key: value
                for key, value in segment["continuity"].items()
                if key in {"kind", "frame_count", "binding", "tag"}
            }
            for segment in edited["segments"]
        ]
        fingerprints_after = [segment["fingerprint"] for segment in edited["segments"]]
        self.assertEqual(reference_maps_after, reference_maps_before)
        self.assertEqual(continuity_after, continuity_before)
        self.assertEqual(
            [
                index
                for index, (before, after) in enumerate(
                    zip(fingerprints_before, fingerprints_after)
                )
                if before != after
            ],
            [1],
        )
        edited_prompts = [self._prompt(row["workflow"]) for row in edited["segments"]]
        self.assertIn("corridor or stairwell", edited_prompts[1])
        self.assertNotIn("corridor or stairwell", edited_prompts[0] + edited_prompts[2])

    def test_05_backend_rejects_missing_or_stale_media_before_comfyui_queue(self):
        """No missing cross-computer media or inactive Loader may reach Queue."""

        gate_root = PROJECT_ROOT / ".director_cache" / "standard_release_gate_backend"
        gate_root.mkdir(parents=True, exist_ok=True)

        # Compiling a Segment must prune every inactive physical Loader even if
        # a reopened project still contains an absolute path from another PC.
        window = DirectorCutStudio()
        self.addCleanup(self._close, window)
        stale_assets = {
            media_type: next(
                asset
                for asset in window.scan.assets
                if asset.media_type == media_type and not asset.is_virtual
            )
            for media_type in ("image", "audio", "video")
        }
        old_paths = {
            "image": r"Z:\old-computer\ComfyUI\input\missing_subject.png",
            "audio": r"Z:\old-computer\ComfyUI\input\missing_dialogue.wav",
            "video": r"Z:\old-computer\ComfyUI\input\missing_motion.mp4",
        }
        loader_inputs = {"image": "image", "audio": "audio", "video": "file"}
        for media_type, asset in stale_assets.items():
            asset.local_path = ""
            asset.timeline_placed = False
            asset.timeline_track_id = ""
            loader_input = loader_inputs[media_type]
            window.scan.nodes[asset.node_id]["inputs"][loader_input] = old_paths[media_type]
        compiled = window._compiled_window_job(
            0.0, 5.0, megapixels=0.2, seed=4501,
            enable_rtx_vsr=False, is_final_window=True,
            continuity_mode="none",
        )[0]
        compiled_json = json.dumps(compiled, ensure_ascii=False)
        self.assertNotIn("old-computer", compiled_json)
        for asset in stale_assets.values():
            self.assertNotIn(asset.node_id, compiled)

        # PNG/WEBP, WAV/audio and MP4/video must all fail in the ordinary
        # Preview/Run worker before upload or /prompt can be contacted.
        loader_cases = (
            ("LoadImage", "image", "image", ".png"),
            ("LoadAudio", "audio", "audio", ".wav"),
            ("LoadVideo", "video", "file", ".mp4"),
        )
        for class_type, media_type, loader_input, suffix in loader_cases:
            missing = gate_root / f"missing_{media_type}{suffix}"
            missing.unlink(missing_ok=True)
            upload_name = f"h3ref_{media_type}_999_missing{suffix}"
            workflow = {
                "999": {
                    "class_type": class_type,
                    "inputs": {loader_input: upload_name},
                }
            }
            manifest = [{
                "path": str(missing),
                "loader_node_id": "999",
                "loader_input": loader_input,
                "upload_name": upload_name,
            }]

            # Keep a direct contract assertion so an error-message or worker
            # refactor cannot silently weaken the shared validator.
            with self.subTest(worker="manifest", media_type=media_type):
                with self.assertRaisesRegex(
                    FileNotFoundError, "missing on this computer"
                ):
                    validate_portable_media_manifest(workflow, manifest)

            ordinary_job_path = gate_root / f"ordinary_missing_{media_type}.json"
            ordinary_job_path.write_text(
                json.dumps({
                    "server": "http://127.0.0.1:8188",
                    "http_timeout": 1,
                    "wait_for_completion": False,
                    "workflow": workflow,
                    "media": manifest,
                }),
                encoding="utf-8",
            )
            self.addCleanup(ordinary_job_path.unlink, missing_ok=True)
            with self.subTest(worker="preview_run", media_type=media_type):
                with (
                    patch.object(comfy_submit_worker, "upload_file") as upload_mock,
                    patch.object(comfy_submit_worker, "_request_json") as request_mock,
                    patch.object(sys, "argv", ["comfy_submit_worker.py", str(ordinary_job_path)]),
                ):
                    with self.assertRaises(FileNotFoundError):
                        comfy_submit_worker.main()
                    upload_mock.assert_not_called()
                    request_mock.assert_not_called()

            # Smart Render must stop during preflight, before object_info,
            # upload or any Segment queue operation can start.
            smart_job = {
                "server": "http://127.0.0.1:8188",
                "http_timeout": 1,
                "ffmpeg": str(Path(smart_render_worker.__file__).resolve()),
                "ffprobe": str(Path(smart_render_worker.__file__).resolve()),
                "master_output": str(gate_root / f"missing_{media_type}_master.mp4"),
                "media": manifest,
                "segments": [
                    {
                        "index": index,
                        "start_seconds": float(index * 5),
                        "end_seconds": float((index + 1) * 5),
                        "workflow": workflow,
                        "continuity": {},
                    }
                    for index in range(2)
                ],
            }
            with self.subTest(worker="smart_render", media_type=media_type):
                with patch.object(smart_render_worker, "_request_json") as request_mock:
                    with self.assertRaisesRegex(
                        FileNotFoundError, "missing before ComfyUI upload"
                    ):
                        smart_render_worker.preflight_smart_render(smart_job)
                    request_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)

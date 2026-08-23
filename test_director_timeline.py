import os
import json
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QGraphicsView, QPushButton, QWidget

from PIL import Image

from director_cut_studio import (
    ContentLayerDialog,
    DesignPageDialog,
    DirectorCutStudio,
    DirectorCue,
    DirectorCueDialog,
    JsonLineProcess,
    MIME_SLOT,
    TimelineClip,
    TimelineCueItem,
    TimelineTextClip,
    TextLayer,
    TrackHeaderWidget,
    snap_timeline_range,
    snap_timeline_seconds,
)
from runtime_paths import PROJECT_ROOT
from design_settings import DesignAISettings
from prompt_presets import (
    CONSTRAINT_PRESETS,
    CREATIVE_BRIEF_PRESETS,
    MUSIC_PRESETS,
    SOUNDSCAPE_PRESETS,
    TRANSITION_STYLE_PRESETS,
    VISUAL_STYLE_PRESETS,
)
from workflow_engine import assign_local_media
from test_design_engine import sample_design


class DirectorTimelineDragTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _send_drop(self, window, asset, seconds=2.0):
        mime = QMimeData()
        mime.setData(MIME_SLOT, asset.node_id.encode("utf-8"))
        point = window.timeline.mapFromScene(
            QPointF(
                window.timeline.origin_x + seconds * window.timeline.pps,
                36 + 2 * 46 + 20,
            )
        )
        enter = QDragEnterEvent(point, Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        move = QDragMoveEvent(point, Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        drop = QDropEvent(QPointF(point), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        self.app.sendEvent(window.timeline.viewport(), enter)
        self.app.sendEvent(window.timeline.viewport(), move)
        self.app.sendEvent(window.timeline.viewport(), drop)
        self.app.processEvents()
        self.app.processEvents()
        return enter, move, drop

    def test_ai_design_button_applies_timeline_and_is_undoable(self):
        window = DirectorCutStudio()
        window.show()
        self.app.processEvents()
        design_button = window.findChild(QPushButton, "designButton")
        self.assertIsNotNone(design_button)
        design_context = window._design_context()
        self.assertEqual(design_context["bound_h3_skills"]["default"]["key"], "h3-prompt-writing")
        self.assertIn("ref2va_format_guide", design_context["bound_h3_skills"]["default"])

        payload = sample_design()
        payload["media_requests"] = payload["media_requests"][:1]
        placeholder = PROJECT_ROOT / ".director_cache" / "ai_design_ui_test.png"
        placeholder.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (64, 36), (20, 40, 60)).save(placeholder)
        material = {
            **payload["media_requests"][0],
            "start_seconds": 0.0,
            "end_seconds": 4.0,
            "local_path": str(placeholder),
            "preview_path": str(placeholder),
        }
        original_duration = window.scan.duration_seconds
        with (
            patch(
                "director_cut_studio.materialize_design_media",
                return_value=(placeholder.parent, [material]),
            ),
            patch(
                "director_cut_studio.load_design_settings",
                return_value=DesignAISettings(generate_comfy_images=False),
            ),
        ):
            window.apply_ai_design(payload, True)

        asset = next(item for item in window.scan.assets if item.media_type == "image")
        self.assertEqual(window.scan.duration_seconds, 12.0)
        self.assertTrue(asset.timeline_placed)
        self.assertEqual(asset.start_seconds, 0.0)
        self.assertEqual(asset.end_seconds, 4.0)
        self.assertFalse(asset.monitor_visible)
        self.assertEqual(len([cue for cue in window.director_cues if cue.cue_type == "shot"]), 2)
        self.assertTrue(any(layer.text == "OPEN HAPPINESS" for layer in window.text_layers))
        self.assertEqual(window._project_payload()["timeline_duration_seconds"], 12.0)

        window.undo_stack.undo()
        self.assertEqual(window.scan.duration_seconds, original_duration)
        self.assertFalse(asset.timeline_placed)
        window.undo_stack.redo()
        self.assertEqual(window.scan.duration_seconds, 12.0)
        self.assertTrue(asset.timeline_placed)
        placeholder.unlink(missing_ok=True)
        window.project_dirty = False
        window.close()

    def test_design_page_fits_screen_scrolls_and_uses_compact_checkpoint_controls(self):
        window = DirectorCutStudio()
        with patch.object(DesignPageDialog, "refresh_checkpoints", autospec=True):
            dialog = DesignPageDialog(
                window.runtime, window._design_context(), window.scan.counts, window
            )
            dialog.show()
            self.app.processEvents()
            self.assertLessEqual(
                dialog.height(), QApplication.primaryScreen().availableGeometry().height()
            )
            self.assertTrue(dialog.image_checkpoint_combo.isEditable())
            self.assertAlmostEqual(
                dialog.comfy_server_label.geometry().center().y(),
                dialog.image_checkpoint_combo.geometry().center().y(),
                delta=4,
            )
            parameter_y = [
                widget.geometry().center().y()
                for widget in (
                    dialog.image_width_spin,
                    dialog.image_height_spin,
                    dialog.image_steps_spin,
                    dialog.image_cfg_spin,
                )
            ]
            self.assertLessEqual(max(parameter_y) - min(parameter_y), 4)
            dialog.design_scroll.ensureWidgetVisible(dialog.apply_button)
            self.app.processEvents()
            center = dialog.apply_button.mapTo(
                dialog.design_scroll.viewport(), dialog.apply_button.rect().center()
            )
            self.assertTrue(dialog.design_scroll.viewport().rect().contains(center))
            dialog.close()
        window.project_dirty = False
        window.close()

    def test_design_uses_lm_plan_then_blip_grounded_refinement(self):
        window = DirectorCutStudio()
        with patch.object(DesignPageDialog, "refresh_checkpoints", autospec=True):
            dialog = DesignPageDialog(
                window.runtime, window._design_context(), window.scan.counts, window
            )
        dialog.pending_requirement = "A hand holds a cold cola bottle, then zoom out."
        with patch.object(dialog, "_submit") as submit:
            dialog._start_lm_design()
        payload = submit.call_args.args[1]
        self.assertTrue(dialog.design_busy_overlay.timer.isActive())
        self.assertIn("Stage 1/4", dialog.design_busy_overlay.message)
        self.assertTrue(
            payload["user_prompt"].startswith(
                "A hand holds a cold cola bottle, then zoom out."
            )
        )
        self.assertIn("Decide how many distinct reference photos", payload["user_prompt"])
        self.assertEqual(dialog.pipeline_stage, "lm_plan")

        dialog.planned_plan = sample_design()
        dialog.generated_references = [{
            "request_index": 0,
            "local_path": "picture_01.png",
            "caption": "a close up of a wet glass cola bottle held by a person's hand",
        }]
        with (
            patch.object(dialog.runner, "is_running", return_value=True),
            patch.object(dialog.runner, "write_json") as unload_request,
        ):
            dialog._start_lm_refinement()
        self.assertEqual(dialog.pipeline_stage, "release_comfy")
        self.assertEqual(unload_request.call_args.args[0]["action"], "unload_comfy")
        self.assertIn("releasing Z-Image", dialog.design_busy_overlay.message)
        with (
            patch.object(dialog, "_submit") as submit,
            patch(
                "director_cut_studio.QTimer.singleShot",
                side_effect=lambda _delay, callback: callback(),
            ),
        ):
            dialog._service_message({"comfy_unloaded": True})
        payload = submit.call_args.args[1]
        self.assertIn("GENERATED Z-IMAGE MATERIAL OBSERVATIONS", payload["user_prompt"])
        self.assertIn("wet glass cola bottle", payload["user_prompt"])
        self.assertIn("written requirement remains authoritative", payload["user_prompt"])
        self.assertGreaterEqual(payload["timeout"], 900)
        self.assertEqual(dialog.pipeline_stage, "lm_refine")
        self.assertIn("Stage 4/4", dialog.design_busy_overlay.message)
        dialog._finish_design_pipeline(sample_design())
        self.assertFalse(dialog.design_busy_overlay.timer.isActive())
        dialog.close()
        window.project_dirty = False
        window.close()

    def test_lm_planned_image_count_drives_z_image_material_jobs(self):
        window = DirectorCutStudio()
        with patch.object(DesignPageDialog, "refresh_checkpoints", autospec=True):
            dialog = DesignPageDialog(
                window.runtime, window._design_context(), window.scan.counts, window
            )
        plan = sample_design()
        second_image = dict(plan["media_requests"][0])
        second_image["prompt"] = "A wider view revealing the woman and the room."
        second_image["subject_keywords"] = ["woman", "room"]
        second_image["start_seconds"] = 4.0
        second_image["end_seconds"] = 12.0
        plan["media_requests"].insert(1, second_image)
        dialog.pipeline_stage = "lm_plan"
        with (
            patch.object(dialog.runner, "is_running", return_value=True),
            patch.object(dialog, "_request_lm_unload") as release_lm,
        ):
            dialog._handle_design_generated({"text": json.dumps(plan)})
        self.assertEqual(dialog.pipeline_stage, "release_lm_for_images")
        release_lm.assert_called_once()
        dialog.planned_plan = plan
        with patch.object(dialog.concept_media_runner, "start", return_value=True) as start:
            dialog._start_plan_images(plan)
        job_path = Path(start.call_args.args[1][1])
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(len(job["materials"]), 2)
        self.assertEqual(job["materials"][0]["request_index"], 0)
        self.assertEqual(job["materials"][1]["request_index"], 1)
        self.assertTrue(job["workflow_path"].endswith("Z-Image_Text2Image_for_webui_t2i_api.json"))
        dialog.close()
        window.project_dirty = False
        window.close()

    def test_media_card_drag_is_accepted_through_timeline_viewport(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        self.app.processEvents()
        asset = next(item for item in window.scan.assets if item.media_type == "image")
        card = window.cards[asset.node_id]
        self.assertTrue(card.thumb.testAttribute(Qt.WA_TransparentForMouseEvents))
        enter, move, drop = self._send_drop(window, asset)

        self.assertTrue(enter.isAccepted())
        self.assertTrue(move.isAccepted())
        self.assertTrue(drop.isAccepted())
        self.assertTrue(asset.timeline_placed)
        self.assertEqual(asset.timeline_lane, 2)
        self.assertAlmostEqual(asset.start_seconds, 2.0, places=1)
        window.project_dirty = False
        window.close()

    def test_timeline_uses_half_second_snap_grid(self):
        self.assertEqual(snap_timeline_seconds(0.24), 0.0)
        self.assertEqual(snap_timeline_seconds(0.26), 0.5)
        self.assertEqual(snap_timeline_seconds(1.74), 1.5)
        self.assertEqual(snap_timeline_seconds(1.76), 2.0)
        self.assertEqual(snap_timeline_range(1.24, 1.26, 12.0), (1.0, 1.5))

        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        self.app.processEvents()
        asset = next(item for item in window.scan.assets if item.media_type == "image")
        self._send_drop(window, asset, 2.26)
        self.assertEqual(asset.start_seconds, 2.5)
        self.assertEqual(asset.end_seconds, 5.5)
        self.assertEqual(window.timeline_snap_label.text(), "SNAP 0.5s")
        window.project_dirty = False
        window.close()

    def test_truly_empty_slot_is_rejected_without_scene_mutation(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        self.app.processEvents()
        asset = next(item for item in window.scan.assets if item.media_type == "image")
        asset.filename = ""
        asset.local_path = ""
        enter, move, drop = self._send_drop(window, asset)
        self.assertTrue(enter.isAccepted())
        self.assertTrue(move.isAccepted())
        self.assertTrue(drop.isAccepted())
        self.assertFalse(asset.timeline_placed)
        self.assertIn("is empty", window.statusBar().currentMessage())
        window.project_dirty = False
        window.close()

    def test_media_pool_reflows_and_cards_resize_with_panel(self):
        window = DirectorCutStudio()
        window.show()
        window.media_scroll.setFixedWidth(255)
        self.app.processEvents()
        window._reflow_media_pool()
        narrow_positions = [window.media_grid.getItemPosition(index) for index in range(5)]
        narrow_width = window.media_card_order[0].width()
        self.assertEqual([position[1] for position in narrow_positions[:2]], [0, 1])
        self.assertEqual(narrow_positions[2][0], 1)
        shortcuts = {
            card.asset.media_type: card.tag.text()
            for card in window.media_card_order
        }
        self.assertEqual(shortcuts["image"], "P9")
        self.assertEqual(shortcuts["video"], "V3")
        self.assertEqual(shortcuts["audio"], "A3")
        self.assertEqual(window.media_card_order[0].tag.toolTip(), "<Picture 1>")
        self.assertFalse(window.media_card_order[0].mode.isVisible())

        window.media_scroll.setFixedWidth(1100)
        self.app.processEvents()
        window._reflow_media_pool()
        wide_positions = [window.media_grid.getItemPosition(index) for index in range(8)]
        wide_width = window.media_card_order[0].width()
        self.assertGreaterEqual(max(position[1] for position in wide_positions), 7)
        self.assertNotEqual(narrow_width, wide_width)
        window.project_dirty = False
        window.close()

    def test_existing_clip_can_move_between_compatible_tracks_without_scene_crash(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        asset = next(item for item in window.scan.assets if item.media_type == "image")
        asset.filename = "timeline-placeholder.png"
        asset.timeline_placed = True
        asset.timeline_lane = 2
        asset.start_seconds = 1.0
        asset.end_seconds = 4.0
        window.timeline.rebuild()
        self.app.processEvents()
        clip = next(item for item in window.timeline.scene_obj.items() if isinstance(item, TimelineClip))
        source = window.timeline.mapFromScene(clip.sceneBoundingRect().center())
        destination_scene = QPointF(
            clip.sceneBoundingRect().center().x() + window.timeline.pps,
            36 + 19,
        )
        destination = window.timeline.mapFromScene(destination_scene)

        QTest.mousePress(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, source)
        QTest.mouseMove(window.timeline.viewport(), destination, 40)
        self.assertTrue(window.timeline.interaction_active)
        window.timeline.rebuild()
        self.assertTrue(window.timeline.rebuild_pending)
        self.assertIsNotNone(clip.scene())
        QTest.mouseRelease(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, destination)
        QTest.qWait(60)

        self.assertEqual(asset.timeline_lane, 0)
        self.assertGreater(asset.start_seconds, 1.5)
        self.assertEqual(window.undo_stack.count(), 1)
        window.undo_stack.undo()
        self.assertEqual(asset.timeline_lane, 2)
        window.undo_stack.redo()
        self.assertEqual(asset.timeline_lane, 0)
        window.project_dirty = False
        window.close()

    def test_program_monitor_follows_timeline_image_video_and_audio(self):
        root = PROJECT_ROOT / ".director_cache" / "runtime_smoke"
        image_path, video_path, audio_path = root / "sample.png", root / "sample.mp4", root / "sample.wav"
        if not all(path.exists() for path in (image_path, video_path, audio_path)):
            self.skipTest("runtime smoke media is not present")
        window = DirectorCutStudio()
        images = [asset for asset in window.scan.assets if asset.media_type == "image"]
        videos = [asset for asset in window.scan.assets if asset.media_type == "video"]
        audios = [asset for asset in window.scan.assets if asset.media_type == "audio"]
        image, video, audio = images[0], videos[0], audios[0]
        image.local_path = str(image_path.resolve())
        image.timeline_placed, image.timeline_lane = True, 2
        image.start_seconds, image.end_seconds = 0.0, 1.0
        window.preview_paths[image.node_id] = image_path.resolve()
        video.local_path = str(video_path.resolve())
        video.timeline_placed, video.timeline_lane = True, 1
        video.start_seconds, video.end_seconds = 1.0, 2.5
        audio.local_path = str(audio_path.resolve())
        audio.timeline_placed, audio.timeline_lane = True, 3
        audio.start_seconds, audio.end_seconds = 1.0, 2.5
        window.timeline.rebuild()

        window.seek_timeline(0.5)
        self.assertIs(window.monitor_stack.currentWidget(), window.monitor_image)
        self.assertFalse(window.monitor_image.pixmap().isNull())
        window.seek_timeline(1.2)
        self.assertIs(window.monitor_stack.currentWidget(), window.video_widget)
        self.assertEqual(Path(window.player.source().toLocalFile()).resolve(), Path(video.local_path).resolve())
        self.assertIn(audio.node_id, window.timeline_audio_players)
        self.assertEqual(
            Path(window.timeline_audio_players[audio.node_id].source().toLocalFile()).resolve(),
            Path(audio.local_path).resolve(),
        )

        window.audio_output.setMuted(True)
        for output in window.timeline_audio_outputs.values():
            output.setMuted(True)
        before = window.playhead_seconds
        window.toggle_playback()
        for _ in range(12):
            QTest.qWait(35)
        self.assertGreater(window.playhead_seconds, before)
        self.assertGreater(window.player.position(), 150)
        self.assertGreater(window.timeline_audio_players[audio.node_id].position(), 150)
        window.toggle_playback()
        window.project_dirty = False
        window.close()

    def test_video_preparation_runs_outside_ui_and_finishes(self):
        source = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "sample.mp4"
        if not source.exists():
            self.skipTest("runtime smoke video is not present")
        window = DirectorCutStudio()
        video = next(asset for asset in window.scan.assets if asset.media_type == "video")
        assign_local_media(window.scan, video, source)
        window.queue_media_preparation(video, auto_analyze=False, preserve_recognition=False)
        responsive_ticks = 0
        for _ in range(200):
            QTest.qWait(25)
            responsive_ticks += 1
            if not window.media_jobs:
                break
        self.assertGreater(responsive_ticks, 0)
        self.assertFalse(window.media_jobs)
        self.assertIn(video.node_id, window.preview_paths)
        self.assertEqual(len(window.analysis_paths[video.node_id]), 3)
        window.project_dirty = False
        window.close()

    def test_json_worker_waits_for_ready_and_returns_failure_without_crashing_ui(self):
        runner = JsonLineProcess(name="ready-gate-test")
        messages = []
        finished = []
        runner.message.connect(messages.append)
        runner.finished.connect(lambda code, log: finished.append((code, log)))
        program = str(PROJECT_ROOT / "ai_libraries_common" / "python_env" / "python.exe")
        script = (
            "import json,sys;"
            "print(json.dumps({'ready':True}),flush=True);"
            "job=json.loads(sys.stdin.readline());"
            "print(json.dumps({'job':job['job'],'error':'expected failure'}),flush=True)"
        )
        self.assertTrue(runner.start(program, ["-c", script]))
        runner.write_json({"job": "queued-before-ready"})
        for _ in range(100):
            QTest.qWait(20)
            if finished:
                break
        self.assertTrue(finished)
        self.assertTrue(any(item.get("ready") for item in messages))
        self.assertTrue(any(item.get("error") == "expected failure" for item in messages))

    def test_dynamic_tracks_properties_and_clip_properties_are_undoable(self):
        window = DirectorCutStudio()
        self.assertEqual(len(window.tracks), 6)
        window.add_video_track()
        self.assertEqual(window.tracks[0].track_id, "V4")
        window.add_audio_track()
        self.assertEqual(window.tracks[-1].track_id, "A4")
        window.undo_stack.undo()
        self.assertFalse(any(track.track_id == "A4" for track in window.tracks))
        window.undo_stack.redo()
        self.assertTrue(any(track.track_id == "A4" for track in window.tracks))

        track = window.tracks[0]
        window.select_track(track)
        window.change_track_property(track, "name", "Overlay Graphics")
        window.change_track_property(track, "opacity", 0.55)
        window.change_track_property(track, "height", 72)
        header = window.track_header_widgets[track.track_id]
        header.blend_combo.setCurrentText("Screen")
        QTest.qWait(30)
        self.assertEqual(track.name, "Overlay Graphics")
        self.assertAlmostEqual(track.opacity, 0.55)
        self.assertEqual(track.blend_mode, "Screen")
        self.assertEqual(track.height, 72)
        window.undo_stack.undo()
        self.assertEqual(track.blend_mode, "Normal")
        window.undo_stack.redo()
        self.assertEqual(track.blend_mode, "Screen")

        asset = next(item for item in window.scan.assets if item.media_type == "video")
        window.select_asset(asset)
        window.asset_speed.setValue(1.5)
        window.asset_source_in.setValue(0.25)
        window.asset_source_out.setValue(1.25)
        window.asset_fade_in.setValue(0.2)
        window.asset_transition_out.setCurrentText("Cross Dissolve")
        window.apply_clip_properties()
        self.assertAlmostEqual(asset.playback_speed, 1.5)
        self.assertAlmostEqual(asset.source_in_seconds, 0.25)
        self.assertEqual(asset.transition_out, "Cross Dissolve")
        payload = window._project_payload()
        self.assertEqual(payload["version"], 11)
        self.assertEqual(len(payload["tracks"]), 8)
        self.assertIn("playback_speed", payload["assets"][asset.node_id])
        window.project_dirty = False
        window.close()

    def test_clicking_visual_clip_selects_its_track_and_timeline_zoom_resizes_clip(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        asset = next(item for item in window.scan.assets if item.media_type == "image")
        asset.filename = "selected-track.png"
        asset.timeline_placed = True
        asset.timeline_lane = 1
        asset.timeline_track_id = window.tracks[1].track_id
        asset.start_seconds = 1.0
        asset.end_seconds = 4.0
        window.timeline.rebuild()
        self.app.processEvents()
        clip = next(item for item in window.timeline.scene_obj.items() if isinstance(item, TimelineClip))
        original_width = clip.rect().width()
        point = window.timeline.mapFromScene(clip.sceneBoundingRect().center())

        QTest.mouseClick(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, point)
        self.assertIs(window.selected_track, window.tracks[1])

        window.timeline_zoom.setValue(140)
        self.app.processEvents()
        zoomed_clip = next(item for item in window.timeline.scene_obj.items() if isinstance(item, TimelineClip))
        self.assertAlmostEqual(window.timeline.pps, 140.0)
        self.assertAlmostEqual(zoomed_clip.rect().width(), original_width * 2.0)
        self.assertEqual(window.timeline_zoom_label.text(), "200%")
        self.assertAlmostEqual(window.timeline.playhead_seconds, 0.0)
        window.project_dirty = False
        window.close()

    def test_track_icons_refresh_in_place_and_prompt_tool_targets_clip(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        self.app.processEvents()
        track = window.tracks[0]
        header = window.track_header_widgets[track.track_id]
        self.assertLess(window.timeline.origin_x, 300)
        self.assertIsInstance(header, TrackHeaderWidget)
        self.assertEqual(header.layout().count(), 9)

        header.visible_button.click()
        QTest.qWait(30)
        self.assertFalse(track.visible)
        self.assertIs(window.track_header_widgets[track.track_id], header)
        window.timeline.rebuild()
        self.app.processEvents()
        self.assertIs(window.track_header_widgets[track.track_id], header)

        asset = next(item for item in window.scan.assets if item.media_type == "image")
        asset.filename = "prompt-target.png"
        asset.timeline_placed = True
        asset.timeline_lane = 0
        asset.timeline_track_id = track.track_id
        asset.start_seconds, asset.end_seconds = 0.5, 3.0
        window.timeline.rebuild()
        self.app.processEvents()
        targeted = []
        window.timeline.prompt_requested.disconnect(window.edit_clip_prompt)
        window.timeline.prompt_requested.connect(targeted.append)
        window.set_timeline_tool("prompt")
        clip = next(item for item in window.timeline.scene_obj.items() if isinstance(item, TimelineClip))
        point = window.timeline.mapFromScene(clip.sceneBoundingRect().center())
        QTest.mouseClick(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, point)
        self.assertEqual(targeted, [asset])
        self.assertEqual(window.timeline.tool_mode, "prompt")
        self.assertTrue(window.timeline_tool_buttons["prompt"].isChecked())

        window.set_clip_prompt(asset, "Keep the product centered; add a slow clockwise orbit.")
        self.assertIn("slow clockwise orbit", asset.clip_prompt)
        self.assertEqual(window._project_payload()["assets"][asset.node_id]["clip_prompt"], asset.clip_prompt)
        window.undo_stack.undo()
        self.assertEqual(asset.clip_prompt, "")
        window.undo_stack.redo()
        self.assertIn("slow clockwise orbit", asset.clip_prompt)
        window.project_dirty = False
        window.close()

    def test_type_tool_edits_persistent_text_layer_and_monitor_overlay(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        layer = TextLayer("T1", "Hero Title", 0.5, 3.0, "V3", 52, "#ffdd33")
        window.text_layers.append(layer)
        window._refresh_text_layers(layer)
        self.app.processEvents()
        text_clip = next(
            item for item in window.timeline.scene_obj.items() if isinstance(item, TimelineTextClip)
        )
        requested = []
        window.timeline.text_edit_requested.disconnect(window.edit_text_layer)
        window.timeline.text_edit_requested.connect(requested.append)
        window.set_timeline_tool("type")
        point = window.timeline.mapFromScene(text_clip.sceneBoundingRect().center())
        QTest.mouseClick(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, point)
        self.assertEqual(requested, [layer])

        window.render_timeline_at(1.0, force_seek=True)
        overlay = window.monitor_text_labels[layer.layer_id]
        self.assertTrue(overlay.isVisible())
        self.assertIn("Hero Title", overlay.text())
        window.set_timeline_tool("selection")
        old_position = (layer.position_x, layer.position_y)
        center = overlay.rect().center()
        QTest.mousePress(overlay, Qt.LeftButton, Qt.NoModifier, center)
        QTest.mouseMove(overlay, center + QPoint(70, 35), 40)
        QTest.mouseRelease(overlay, Qt.LeftButton, Qt.NoModifier, center + QPoint(70, 35))
        QTest.qWait(20)
        self.assertNotEqual((layer.position_x, layer.position_y), old_position)
        moved_position = (layer.position_x, layer.position_y)
        window.undo_stack.undo()
        self.assertEqual((layer.position_x, layer.position_y), old_position)
        window.undo_stack.redo()
        self.assertEqual((layer.position_x, layer.position_y), moved_position)
        payload = window._project_payload()
        self.assertEqual(payload["version"], 11)
        self.assertEqual(payload["text_layers"][0]["font_size"], 52)

        before = layer.__dict__ if hasattr(layer, "__dict__") else {
            "layer_id": layer.layer_id,
            "text": layer.text,
            "start_seconds": layer.start_seconds,
            "end_seconds": layer.end_seconds,
            "track_id": layer.track_id,
            "font_size": layer.font_size,
            "color": layer.color,
        }
        after = dict(before)
        after["text"] = "Updated Hero Title"
        window.commit_text_layer_edit(layer, before, after)
        self.assertEqual(layer.text, "Updated Hero Title")
        window.undo_stack.undo()
        self.assertEqual(layer.text, "Hero Title")
        window.undo_stack.redo()
        self.assertEqual(layer.text, "Updated Hero Title")
        window.project_dirty = False
        window.close()

    def test_monitor_text_drag_uses_deferred_scene_refresh(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        layer = TextLayer("T-safe", "SAFE TITLE", 0.0, 5.0, "V3")
        window.text_layers.append(layer)
        window._refresh_text_layers(layer)
        window.render_timeline_at(1.0, force_seek=True)
        self.app.processEvents()
        window.set_timeline_tool("selection")
        overlay = window.monitor_text_labels[layer.layer_id]
        for index in range(12):
            center = overlay.rect().center()
            delta = QPoint(4 if index % 2 == 0 else -4, 2 if index % 2 == 0 else -2)
            QTest.mousePress(overlay, Qt.LeftButton, Qt.NoModifier, center)
            QTest.mouseMove(overlay, center + delta, 5)
            QTest.mouseRelease(overlay, Qt.LeftButton, Qt.NoModifier, center + delta)
            QTest.qWait(10)
        self.assertEqual(window.undo_stack.count(), 12)
        self.assertFalse(window.timeline.interaction_active)
        window.project_dirty = False
        window.close()

    def test_hand_tool_pans_timeline_without_moving_playhead(self):
        window = DirectorCutStudio()
        window.resize(1200, 800)
        window.show()
        window.timeline.set_zoom(240)
        self.app.processEvents()
        bar = window.timeline.horizontalScrollBar()
        self.assertGreater(bar.maximum(), 0)
        bar.setValue(min(300, bar.maximum()))
        before_scroll = bar.value()
        before_playhead = window.timeline.playhead_seconds
        window.set_timeline_tool("hand")
        self.assertEqual(window.timeline.dragMode(), QGraphicsView.ScrollHandDrag)
        start = QPoint(650, 120)
        end = QPoint(500, 120)
        QTest.mousePress(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, start)
        QTest.mouseMove(window.timeline.viewport(), end, 50)
        QTest.mouseRelease(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, end)
        self.assertGreater(bar.value(), before_scroll)
        self.assertEqual(window.timeline.playhead_seconds, before_playhead)
        window.project_dirty = False
        window.close()

    def test_director_tools_are_resizable_explained_and_use_compact_defaults(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        self.app.processEvents()
        self.assertEqual(set(window.timeline_tool_buttons), {
            "selection", "hand", "razor", "shot", "type", "prompt", "transition", "marker"
        })
        self.assertTrue(all(button.toolTip().strip() for button in window.timeline_tool_buttons.values()))
        self.assertTrue(all(track.height == 20 for track in window.tracks))
        header = window.findChild(QWidget, "directorTimelineHeader")
        self.assertIsNotNone(header)
        self.assertEqual(header.height(), 20)

        window.timeline_body_splitter.setSizes([150, 222, 900])
        self.app.processEvents()
        window._refresh_timeline_tool_labels()
        self.assertGreaterEqual(window.timeline_tool_palette.width(), 92)
        self.assertEqual(
            window.timeline_tool_buttons["shot"].toolButtonStyle(), Qt.ToolButtonTextBesideIcon
        )
        window.timeline_body_splitter.setSizes([43, 222, 1000])
        self.app.processEvents()
        window._refresh_timeline_tool_labels()
        self.assertEqual(window.timeline_tool_buttons["shot"].toolButtonStyle(), Qt.ToolButtonIconOnly)

        window.timeline_tool_scroll.setFixedHeight(150)
        self.app.processEvents()
        scroll_bar = window.timeline_tool_scroll.verticalScrollBar()
        self.assertGreater(scroll_bar.maximum(), 0)
        wheel = QWheelEvent(
            QPointF(15, 80), QPointF(15, 80), QPoint(0, 0), QPoint(0, -120),
            Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False,
        )
        self.app.sendEvent(window.timeline_tool_scroll.viewport(), wheel)
        self.assertGreater(scroll_bar.value(), 0)
        window.project_dirty = False
        window.close()

    def test_track_header_add_delete_icons_migrate_content_and_undo(self):
        window = DirectorCutStudio()
        source = next(track for track in window.tracks if track.track_id == "V1")
        header = window.track_header_widgets[source.track_id]
        self.assertTrue(header.add_button.toolTip())
        self.assertTrue(header.delete_button.toolTip())

        QTest.mouseClick(header.add_button, Qt.LeftButton)
        QTest.qWait(30)
        added = next(track for track in window.tracks if track.track_id == "V4")
        self.assertEqual(window.tracks.index(added), window.tracks.index(source) + 1)

        asset = next(item for item in window.scan.assets if item.media_type == "image")
        asset.timeline_placed = True
        asset.timeline_track_id = source.track_id
        asset.timeline_lane = window.tracks.index(source)
        layer = TextLayer("T99", "TRACK TITLE", 0.0, 1.0, source.track_id)
        window.text_layers.append(layer)
        header = window.track_header_widgets[source.track_id]
        QTest.mouseClick(header.delete_button, Qt.LeftButton)
        QTest.qWait(30)
        self.assertNotIn(source, window.tracks)
        self.assertNotEqual(asset.timeline_track_id, source.track_id)
        self.assertEqual(layer.track_id, asset.timeline_track_id)

        window.undo_stack.undo()
        self.assertIn(source, window.tracks)
        self.assertEqual(asset.timeline_track_id, source.track_id)
        self.assertEqual(layer.track_id, source.track_id)
        window.undo_stack.redo()
        self.assertNotIn(source, window.tracks)
        window.project_dirty = False
        window.close()

    def test_director_cues_razor_and_prompt_merge_are_undoable(self):
        window = DirectorCutStudio()
        shot = window.add_director_cue("shot", 1.0, "Hero Reveal", "Low hero angle", 4.0)
        transition = window.add_director_cue("transition", 4.0, "Whip Pan", "Smear into next shot", 4.12)
        self.assertIsNotNone(shot)
        self.assertIsNotNone(transition)
        self.assertEqual(len(window.director_cues), 2)
        QTest.qWait(20)
        self.assertEqual(
            len([item for item in window.timeline.scene_obj.items() if isinstance(item, TimelineCueItem)]),
            2,
        )

        window.razor_director_cue(shot, 2.5)
        self.assertEqual(len([cue for cue in window.director_cues if cue.cue_type == "shot"]), 2)
        window.undo_stack.undo()
        self.assertEqual(len([cue for cue in window.director_cues if cue.cue_type == "shot"]), 1)
        window.undo_stack.redo()

        layer = TextLayer("T1", "GET READY", 1.0, 4.0, "V1")
        window.text_layers.append(layer)
        window._refresh_text_layers()
        window.razor_text_layer(layer, 2.0)
        self.assertEqual(len(window.text_layers), 2)
        window.undo_stack.undo()
        self.assertEqual(len(window.text_layers), 1)
        window.undo_stack.redo()

        spec = window._prompt_spec_with_director_cues(window.prompt_panel.spec())
        self.assertIn("Hero Reveal", " ".join(spec.shots))
        self.assertIn("Whip Pan", spec.transition)
        self.assertIn("GET READY", " ".join(spec.shots))
        payload = window._project_payload()
        self.assertEqual(payload["version"], 11)
        self.assertEqual(len(payload["director_cues"]), 3)
        window.project_dirty = False
        window.close()

    def test_shot_tool_drags_visual_range_and_shot_dialog_is_structured(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        self.app.processEvents()
        requested = []
        window.timeline.shot_range_requested.disconnect(window.create_shot_range)
        window.timeline.shot_range_requested.connect(
            lambda start, end, track_id: requested.append((start, end, track_id))
        )
        window.set_timeline_tool("shot")
        y = window.timeline._track_top(0) + 10
        start = window.timeline.mapFromScene(QPointF(window.timeline.pps * 1.0, y))
        end = window.timeline.mapFromScene(QPointF(window.timeline.pps * 4.5, y))
        QTest.mousePress(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, start)
        QTest.mouseMove(window.timeline.viewport(), end, 40)
        QTest.mouseRelease(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, end)
        QTest.qWait(20)
        self.assertEqual(len(requested), 1)
        self.assertAlmostEqual(requested[0][0], 1.0, places=1)
        self.assertAlmostEqual(requested[0][1], 4.5, places=1)
        self.assertEqual(requested[0][2], window.tracks[0].track_id)

        cue = DirectorCue(
            "S1", "shot", 1.0, 4.5, "Hero Reveal", track_id=window.tracks[0].track_id,
            framing="Medium-wide", camera_angle="Low angle", camera_movement="Push in",
            movement_speed="Slow", movement_amplitude="Small",
            subject_action="Subject turns toward camera",
            environment_response="The cape reacts to the wind",
        )
        dialog = DirectorCueDialog(cue, window.scan.duration_seconds)
        state = dialog.state()
        self.assertEqual(state["framing"], "Medium-wide")
        self.assertEqual(state["camera_angle"], "Low angle")
        self.assertEqual(state["camera_movement"], "Push in")
        self.assertEqual(state["subject_action"], "Subject turns toward camera")
        dialog.close()
        window.project_dirty = False
        window.close()

    def test_shot_drag_modal_commit_rebuilds_scene_after_event_unwinds(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        self.app.processEvents()
        window.set_timeline_tool("shot")

        def accept_when_ready(attempt=0):
            dialog = QApplication.activeModalWidget()
            if dialog is not None:
                dialog.accept()
            elif attempt < 20:
                QTimer.singleShot(5, lambda: accept_when_ready(attempt + 1))

        y = window.timeline._track_top(0) + 10
        for index in range(6):
            start_seconds = 0.2 + index * 0.3
            end_seconds = start_seconds + 0.2
            start = window.timeline.mapFromScene(QPointF(window.timeline.pps * start_seconds, y))
            end = window.timeline.mapFromScene(QPointF(window.timeline.pps * end_seconds, y))
            QTest.mousePress(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, start)
            QTest.mouseMove(window.timeline.viewport(), end, 10)
            QTimer.singleShot(5, accept_when_ready)
            QTest.mouseRelease(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, end)
            QTest.qWait(45)

        self.assertEqual(len([cue for cue in window.director_cues if cue.cue_type == "shot"]), 6)
        QTest.qWait(30)
        self.assertEqual(
            len([item for item in window.timeline.scene_obj.items() if isinstance(item, TimelineCueItem)]),
            6,
        )
        window.undo_stack.undo()
        QTest.qWait(20)
        self.assertEqual(len(window.director_cues), 5)
        window.undo_stack.redo()
        QTest.qWait(20)
        self.assertEqual(len(window.director_cues), 6)
        window.project_dirty = False
        window.close()

    def test_type_content_roles_dialogue_fields_and_shot_binding(self):
        window = DirectorCutStudio()
        shot = DirectorCue("S1", "shot", 0.0, 3.5, "Hero Reveal", track_id="V1")
        layer = TextLayer(
            "T1", "Get ready", 0.5, 2.0, "V1", content_role="dialogue",
            speaker="S2", language="Cantonese", delivery="Urgent", lip_sync=True, shot_id="S1",
        )
        dialog = ContentLayerDialog(layer, window.scan.duration_seconds, [shot])
        self.assertEqual(dialog.role_combo.currentData(), "dialogue")
        self.assertTrue(all(not widget.isHidden() for _label, widget in dialog.dialogue_rows))
        state = dialog.state()
        self.assertEqual(state["speaker"], "S2")
        self.assertEqual(state["language"], "Cantonese")
        self.assertTrue(state["lip_sync"])
        self.assertEqual(state["shot_id"], "S1")
        window.director_cues = [shot]
        window.text_layers = [layer]
        spec = window._prompt_spec_with_director_cues(window.prompt_panel.spec())
        self.assertEqual(spec.shot_ranges[0]["start_seconds"], 0.0)
        self.assertEqual(spec.shot_ranges[0]["end_seconds"], 3.5)
        self.assertIn("S2 speaks in Cantonese", spec.shot_ranges[0]["description"])
        self.assertIn("accurate visible lip sync", spec.shot_ranges[0]["description"])
        dialog.role_combo.setCurrentIndex(dialog.role_combo.findData("voice_over"))
        self.assertTrue(all(widget.isHidden() for _label, widget in dialog.dialogue_rows))
        self.assertFalse(dialog.state()["lip_sync"])
        dialog.close()
        window.project_dirty = False
        window.close()

    def test_visual_tracks_composite_and_audio_tracks_respect_mute_solo(self):
        root = PROJECT_ROOT / ".director_cache" / "runtime_smoke"
        image_path = root / "sample.png"
        audio_path = root / "sample.wav"
        if not image_path.exists() or not audio_path.exists():
            self.skipTest("runtime smoke media is not present")
        window = DirectorCutStudio()
        images = [asset for asset in window.scan.assets if asset.media_type == "image"][:2]
        for lane, asset in enumerate(images):
            asset.local_path = str(image_path.resolve())
            asset.timeline_placed = True
            asset.timeline_lane = lane
            asset.timeline_track_id = window.tracks[lane].track_id
            asset.start_seconds, asset.end_seconds = 0.0, 2.0
            window.preview_paths[asset.node_id] = image_path.resolve()
        window.tracks[0].opacity = 0.5
        window.tracks[0].blend_mode = "Screen"
        window.render_timeline_at(0.5, force_seek=True)
        self.assertIs(window.monitor_stack.currentWidget(), window.monitor_image)
        self.assertFalse(window.monitor_image.pixmap().isNull())
        visuals, _ = window._assets_at_playhead(0.5)
        self.assertEqual(len(visuals), 2)
        window.tracks[0].visible = False
        visuals, _ = window._assets_at_playhead(0.5)
        self.assertEqual(visuals, [images[1]])

        audios = [asset for asset in window.scan.assets if asset.media_type == "audio"][:2]
        for lane, asset in zip((3, 4), audios):
            asset.local_path = str(audio_path.resolve())
            asset.timeline_placed = True
            asset.timeline_lane = lane
            asset.timeline_track_id = window.tracks[lane].track_id
            asset.start_seconds, asset.end_seconds = 0.0, 1.5
        window.tracks[3].solo = True
        _, active_audio = window._assets_at_playhead(0.5)
        self.assertEqual(active_audio, [audios[0]])
        window.tracks[3].muted = True
        _, active_audio = window._assets_at_playhead(0.5)
        self.assertEqual(active_audio, [])
        _compiled, active_references = window._compiled_job()
        self.assertNotIn(images[0], active_references)
        self.assertIn(images[1], active_references)
        self.assertNotIn(audios[0], active_references)
        self.assertNotIn(audios[1], active_references)
        window.project_dirty = False
        window.close()

    def test_generation_settings_compile_and_accept_reuses_preview_seed(self):
        window = DirectorCutStudio()
        compiled, _ = window._compiled_job(
            megapixels=0.2,
            seed=987654321,
            enable_rtx_vsr=False,
        )
        self.assertEqual(compiled["115"]["inputs"]["megapixels"], 0.2)
        self.assertEqual(compiled["129"]["inputs"]["noise_seed"], 987654321)
        self.assertEqual(compiled["130"]["inputs"]["images"], ["122", 0])
        calls = []
        window._start_generation = lambda *args: calls.append(args)
        window.preview_seed = 987654321
        window.preview_ready = True
        window.accept_pre_run_preview()
        self.assertEqual(calls[0][0], "accepted")
        self.assertEqual(calls[0][1], 1.0)
        self.assertEqual(calls[0][2], 987654321)
        payload = window._project_payload()
        self.assertIn("render_settings", payload)
        window.project_dirty = False
        window.close()

    def test_prompt_presets_caption_seed_and_timeline_auto_sync(self):
        self.assertTrue(all(len(items) == 32 for items in (
            CREATIVE_BRIEF_PRESETS,
            VISUAL_STYLE_PRESETS,
            TRANSITION_STYLE_PRESETS,
            CONSTRAINT_PRESETS,
            SOUNDSCAPE_PRESETS,
            MUSIC_PRESETS,
        )))
        window = DirectorCutStudio()
        self.assertEqual(window.prompt_panel.style_preset.count(), 33)
        asset = next(item for item in window.scan.assets if item.media_type == "image")
        asset.recognition = "MEDIA\n\nBLIP visual caption: a woman with long black hair"
        self.assertEqual(
            window._blip_caption_for_asset(asset),
            "a woman with long black hair",
        )
        asset.timeline_placed = True
        asset.timeline_track_id = "V1"
        asset.clip_prompt = "Use this picture only for the woman's facial identity."
        shot = DirectorCue(
            "S1", "shot", 0.0, 6.0, "Product Demonstration",
            subject_action="The woman presents the bag.",
            environment_response="A light breeze moves her hair.",
            track_id="V1",
        )
        ending = DirectorCue("M1", "marker", 5.5, 6.0, "Ending Hold", "Hold the hero pose.")
        layer = TextLayer(
            "T1", "Ready", 1.0, 2.0, "V1", content_role="dialogue",
            speaker="S1", language="English", delivery="Confident", lip_sync=True,
            shot_id="S1",
        )
        window.director_cues = [shot, ending]
        window.text_layers = [layer]
        window._sync_prompt_panel_from_timeline(force=True)
        self.assertIn("facial identity", window.prompt_panel.brief.toPlainText())
        self.assertIn("Product Demonstration", window.prompt_panel.shots.toPlainText())
        self.assertIn("S1 [English, Confident, lip sync]", window.prompt_panel.dialogue.toPlainText())
        self.assertIn("Hold the hero pose", window.prompt_panel.ending.toPlainText())
        QTest.qWait(250)
        self.assertTrue(window.prompt_panel.output.toPlainText().strip())
        self.assertEqual(window.prompt_panel.brief_preset.count(), 33)
        self.assertEqual(window.prompt_panel.style_preset.count(), 33)
        self.assertEqual(window.prompt_panel.transition_preset.count(), 33)
        self.assertEqual(window.prompt_panel.constraints_preset.count(), 33)
        self.assertEqual(window.prompt_panel.soundscape_preset.count(), 33)
        self.assertEqual(window.prompt_panel.music_preset.count(), 33)
        self.assertEqual(window.prompt_panel.creative_brief_preset_button.text(), "EDIT")
        self.assertEqual(window.prompt_panel.global_visual_style_preset_button.text(), "EDIT")
        self.assertEqual(window.prompt_panel.transition_language_preset_button.text(), "EDIT")
        self.assertEqual(window.prompt_panel.constraints_and_technical_rules_preset_button.text(), "EDIT")
        self.assertEqual(window.prompt_panel.overall_soundscape_preset_button.text(), "EDIT")
        self.assertEqual(window.prompt_panel.non_diegetic_music_preset_button.text(), "EDIT")
        window.project_dirty = False
        window.close()

    def test_cue_recommendations_and_generated_output_lock_until_new_project(self):
        window = DirectorCutStudio()
        shot = DirectorCue("S1", "shot", 0.0, 3.0, "Product Demonstration")
        dialog = DirectorCueDialog(shot, 12.0)
        self.assertIn("real function", dialog.subject_action_edit.toPlainText())
        self.assertTrue(dialog.environment_response_edit.toPlainText())
        self.assertTrue(dialog.detail_edit.toPlainText())
        dialog.close()
        marker = DirectorCue("M1", "marker", 10.0, 10.1, "Ending Hold")
        marker_dialog = DirectorCueDialog(marker, 12.0)
        self.assertIn("final frame", marker_dialog.detail_edit.toPlainText())
        marker_dialog.close()
        video = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "sample.mp4"
        if video.exists():
            window._show_generated_output([{"local_path": str(video)}])
            self.assertTrue(window.generated_output_locked)
            self.assertEqual(window.generated_output_path, video.resolve())
            self.assertTrue(window.export_generated_button.isEnabled())
            final_monitor = window.monitor_stack.currentWidget()
            window.generation_previous_monitor = final_monitor
            window.monitor_stack.setCurrentWidget(window.generation_overlay)
            window.generation_overlay.start("ComfyUI running · sampling")
            self.assertIs(window.monitor_stack.currentWidget(), window.generation_overlay)
            self.assertFalse(window.generation_overlay.isHidden())
            window.generation_overlay.set_message("Rendering frames 50%")
            self.assertEqual(window.generation_overlay.message, "Rendering frames 50%")
            window.render_timeline_at(0.0, force_seek=True)
            self.assertIs(window.monitor_stack.currentWidget(), window.generation_overlay)
            window.generation_overlay.stop()
            window._restore_monitor_after_generation()
            self.assertIs(window.monitor_stack.currentWidget(), final_monitor)
            window.new_project(confirm=False)
            self.assertFalse(window.generated_output_locked)
            self.assertIsNone(window.generated_output_path)
            self.assertFalse(window.export_generated_button.isEnabled())
        window.project_dirty = False
        window.close()


if __name__ == "__main__":
    unittest.main()

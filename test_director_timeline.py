import os
import json
from copy import deepcopy
from pathlib import Path
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QImage, QWheelEvent
from PySide6.QtMultimedia import QMediaPlayer
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
    PrecisionScrubSlider,
    SpecialSkillCreatorDialog,
    TimelineClip,
    TimelineCueItem,
    TimelineTextClip,
    TextLayer,
    TrackHeaderWidget,
    media_shortcut,
    resolve_project_media_path,
    snap_timeline_range,
    snap_timeline_seconds,
    timeline_state,
)
from runtime_paths import PROJECT_ROOT
from design_engine import normalize_design_plan
from design_settings import DesignAISettings
from prompt_presets import (
    CONSTRAINT_PRESETS,
    CREATIVE_BRIEF_PRESETS,
    MUSIC_PRESETS,
    SOUNDSCAPE_PRESETS,
    TRANSITION_STYLE_PRESETS,
    VISUAL_STYLE_PRESETS,
)
from workflow_engine import MEDIA_LOADERS, assign_local_media, create_virtual_media_asset
from test_design_engine import sample_design
from version_info import APP_VERSION, PROJECT_FORMAT_VERSION


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

    @staticmethod
    def _workflow_prompt(workflow):
        return next(
            node["inputs"]["value"]
            for node in workflow.values()
            if node.get("class_type") == "PrimitiveStringMultiline"
        )

    @staticmethod
    def _h3_inputs(window, workflow):
        return workflow[window.scan.h3_node_ids[0]]["inputs"]

    @staticmethod
    def _place(asset, start, end, track_id="V1", prompt=""):
        asset.timeline_placed = True
        asset.timeline_track_id = track_id
        asset.start_seconds = float(start)
        asset.end_seconds = float(end)
        asset.clip_prompt = prompt
        return asset

    @staticmethod
    def _semantic_result(asset, fingerprint, summary="Grounded semantic summary."):
        return {
            "media_id": media_shortcut(asset),
            "media_type": asset.media_type,
            "evidence_fingerprint": fingerprint,
            "summary": summary,
            "observed_facts": ["A directly supported visual observation."],
            "subjects": [],
            "objects_and_props": ["one supported prop"],
            "environment": "A supported environment description.",
            "composition_and_camera": "Static framed composition.",
            "lighting_and_color": "Lighting described only from evidence.",
            "motion_and_temporal_changes": "",
            "audio_and_speech": "",
            "h3_prompt_keywords": ["grounded reference"],
            "suggested_h3_usage": "Use as an evidence-bound H3 reference.",
            "shot_adaptations": [],
            "uncertain_inferences": ["A possible intent remains unconfirmed."],
        }

    def test_ai_design_button_applies_timeline_and_is_undoable(self):
        window = DirectorCutStudio()
        window.show()
        self.app.processEvents()
        design_button = window.findChild(QPushButton, "designButton")
        self.assertIsNotNone(design_button)
        design_context = window._design_context()
        self.assertEqual(design_context["bound_h3_skills"]["default"]["key"], "h3-prompt-writing")
        self.assertIn("ref2va_format_guide", design_context["bound_h3_skills"]["default"])

        wuxia_index = window.special_combo.findData("wuxia-blade-film")
        self.assertGreaterEqual(wuxia_index, 0)
        window.special_combo.setCurrentIndex(wuxia_index)
        wuxia_context = window._design_context()["bound_h3_skills"]
        self.app.processEvents()
        self.assertEqual(wuxia_context["binding_mode"], "default_plus_special")
        self.assertEqual(wuxia_context["default"]["key"], "h3-prompt-writing")
        self.assertEqual(wuxia_context["special"]["key"], "wuxia-blade-film")
        self.assertFalse(wuxia_context["special"]["standalone"])
        self.assertNotIn("not bound", window.default_skill_label.text().lower())
        self.assertEqual(window.special_skill_label.text(), "+ Special")
        window.special_combo.setCurrentIndex(0)

        creator_button = window.findChild(QPushButton, "specialSkillCreatorButton")
        self.assertIsNotNone(creator_button)
        self.assertIs(
            creator_button.parentWidget(),
            window.default_skill_combo.parentWidget(),
        )
        self.assertIs(
            creator_button.parentWidget(),
            window.special_combo.parentWidget(),
        )

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

    def test_authored_dialogue_reserves_tts_audio_and_run_guard_detects_loss(self):
        window = DirectorCutStudio()
        window.render_settings.dialogue_tts_engine = "edge_tts"
        plan = normalize_design_plan(
            sample_design(), window.scan.counts,
            existing_media=window._design_context().get("existing_media") or [],
        )
        authored = {
            "start_seconds": 0.0,
            "end_seconds": 7.0,
            "track": "A4",
            "content": "我今年三十九岁了。",
            "role": "dialogue",
            "speaker": "S1",
            "language": "Mandarin Chinese",
            "delivery": "Natural",
            "lip_sync": True,
            "explicit_user_requested": True,
        }
        plan["_required_text_layers"] = [authored]
        self.assertTrue(window._ensure_authored_tts_request(plan, "普通话对白"))
        audio_requests = [
            item for item in plan["media_requests"] if item["media_type"] == "audio"
        ]
        self.assertEqual(audio_requests[0]["requirement_id"], "authored_speech_tts")
        self.assertEqual(audio_requests[0]["track"], "A1")

        window.authored_text_requirements = [authored]
        window.text_layers = []
        with patch("director_cut_studio.QMessageBox.critical") as warning:
            self.assertFalse(window._validate_authored_text_before_run())
        warning.assert_called_once()
        window.text_layers = [TextLayer(
            "T1", authored["content"], 0.0, 7.0, "A4",
            content_role="dialogue", speaker="S1", language="Mandarin Chinese",
            delivery="Natural", lip_sync=True,
        )]
        self.assertTrue(window._validate_authored_text_before_run())
        window.project_dirty = False
        window.close()

    def test_dialogue_prompt_names_supplied_audio_only_when_present(self):
        window = DirectorCutStudio()
        window.director_cues = [DirectorCue(
            "S1", "shot", 0.0, 5.0, "Dialogue close-up", "", "V1",
            "Close-up", "Eye level", "Static", "Slow", "Small",
            "The woman looks into the camera.", "",
        )]
        window.text_layers = [TextLayer(
            "T1", "请听我说。", 0.0, 5.0, "A4",
            content_role="dialogue", speaker="S1", language="Mandarin Chinese",
            delivery="Natural", lip_sync=True, shot_id="S1",
        )]
        without_audio = window._prompt_spec_with_director_cues(
            window.prompt_panel.spec()
        )
        self.assertEqual(without_audio.text_ranges[0]["supplied_audio_tag"], "")
        self.assertNotIn(window.text_layers[0].text, without_audio.shots[0])
        self.assertIn("SHOT SOUND EXECUTION", without_audio.shots[0])
        self.assertIn("SHOT SPATIAL ACOUSTICS", without_audio.shots[0])
        with_audio = window._prompt_spec_with_director_cues(
            window.prompt_panel.spec(), supplied_dialogue_audio_tag="<Audio 2>"
        )
        self.assertEqual(
            with_audio.text_ranges[0]["supplied_audio_tag"], "<Audio 2>"
        )
        self.assertNotIn(window.text_layers[0].text, with_audio.shots[0])
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
            self.assertTrue(
                any(
                    button.text() == "LOAD JSON"
                    for button in dialog.findChildren(QPushButton)
                )
            )
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

    def test_manually_loaded_design_json_generates_missing_reference_images_on_apply(self):
        window = DirectorCutStudio()
        with patch.object(DesignPageDialog, "refresh_checkpoints", autospec=True):
            dialog = DesignPageDialog(
                window.runtime, window._design_context(), window.scan.counts, window
            )
        dialog.json_edit.setPlainText(json.dumps(sample_design(), ensure_ascii=False))
        self.assertTrue(dialog.validate_json())
        dialog.generate_images_check.setChecked(True)
        dialog.generated_references = []
        emitted = []
        dialog.apply_requested.connect(lambda plan, replace: emitted.append((plan, replace)))
        dialog.apply_design()
        self.assertEqual(len(emitted), 1)
        self.assertFalse(emitted[0][0]["_design_images_pre_generated"])
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
        self.assertIn("Decide how many reference images are genuinely useful", payload["user_prompt"])
        self.assertIn("do not force one image per Shot", payload["user_prompt"])
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

    def test_design_context_exposes_only_local_media_with_bounded_intelligence(self):
        window = DirectorCutStudio()
        image_assets = [
            asset for asset in window.scan.assets if asset.media_type == "image"
        ]
        self.assertGreaterEqual(len(image_assets), 2)
        default_asset = image_assets[1]
        self.assertTrue(default_asset.filename)
        self.assertFalse(default_asset.local_path)
        initial_context = window._design_context()
        self.assertNotIn(
            default_asset.node_id,
            {row["node_id"] for row in initial_context["existing_media"]},
        )

        media_root = PROJECT_ROOT / ".director_cache" / "media_pool_design_tests"
        media_root.mkdir(parents=True, exist_ok=True)
        picture_path = media_root / "director_identity_p1.png"
        Image.new("RGB", (48, 48), (28, 52, 76)).save(picture_path)
        self.addCleanup(lambda: picture_path.unlink(missing_ok=True))
        picture = image_assets[0]
        assign_local_media(window.scan, picture, picture_path)
        picture.recognition = (
            "MEDIA ANALYSIS\n"
            "BLIP visual caption: a black-clad Tang assassin beside a bronze cauldron\n"
            "Video semantic summary: crimson leaves move across the courtyard"
        )
        picture.clip_prompt = "Preserve the assassin's face, costume and twin short swords."
        picture.timeline_placed = True
        picture.timeline_track_id = "V2"
        picture.start_seconds = 1.0
        picture.end_seconds = 7.5

        context = window._design_context()
        row = next(item for item in context["existing_media"] if item["media_id"] == "P1")
        self.assertNotIn("h3_tag", row)
        self.assertNotIn("tag", row)
        self.assertEqual(row["filename"], picture_path.name)
        self.assertEqual(
            row["caption"],
            "a black-clad Tang assassin beside a bronze cauldron",
        )
        self.assertIn("crimson leaves", row["analysis_summary"])
        self.assertEqual(row["timeline_track_id"], "V2")
        self.assertEqual((row["start_seconds"], row["end_seconds"]), (1.0, 7.5))
        self.assertEqual(context["loaded_media_counts"]["image"], 1)
        self.assertEqual(
            context["available_new_media_capacity"]["image"],
            context["media_capacity"]["image"] - 1,
        )
        serialized = json.dumps(context, ensure_ascii=False)
        self.assertNotIn(
            "<Picture 1>",
            json.dumps(context["existing_media"], ensure_ascii=False),
        )
        self.assertNotIn(str(picture_path.resolve()), serialized)
        self.assertNotIn(str(media_root.resolve()), serialized)
        window.project_dirty = False
        window.close()

    def test_media_semantic_ui_keeps_raw_and_ai_analysis_in_separate_tabs(self):
        window = DirectorCutStudio()
        media_root = PROJECT_ROOT / ".director_cache" / "media_semantic_ui_tests"
        media_root.mkdir(parents=True, exist_ok=True)
        picture_path = media_root / "separate_tabs_p1.png"
        Image.new("RGB", (40, 40), (42, 57, 73)).save(picture_path)
        self.addCleanup(lambda: picture_path.unlink(missing_ok=True))
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        assign_local_media(window.scan, picture, picture_path)
        raw = "BLIP visual caption: a black-clad figure beside a bronze vessel"
        semantic = "SUMMARY\nA detailed but explicitly AI-derived interpretation."
        picture.recognition = raw
        picture.semantic_enrichment = semantic
        picture.semantic_enrichment_source_hash = window._semantic_source_fingerprint(picture)
        picture.semantic_enrichment_model = "lm_studio · unit-model"

        window.select_asset(picture)

        self.assertEqual(window.recognition_tabs.count(), 2)
        self.assertEqual(window.recognition_tabs.tabText(0), "RAW ANALYSIS")
        self.assertIn("AI SEMANTIC", window.recognition_tabs.tabText(1))
        self.assertEqual(window.recognition_text.toPlainText(), raw)
        self.assertEqual(window.semantic_text.toPlainText(), semantic)
        self.assertNotIn("AI-derived interpretation", window.recognition_text.toPlainText())
        self.assertNotIn("BLIP visual caption", window.semantic_text.toPlainText())
        self.assertIn("Ready", window.semantic_status_label.text())
        self.assertTrue(window.semantic_status_label.isHidden())
        self.assertEqual(window.run_recognition.text(), "ANALYZE MEDIA")
        self.assertEqual(window.semantic_auto_check.text(), "AUTO AI ENRICH")
        self.assertEqual(window.cancel_recognition_button.text(), "CANCEL ANALYSIS")
        window.project_dirty = False
        window.close()

    def test_ai_enrich_shows_and_clears_media_card_busy_overlay(self):
        window = DirectorCutStudio()
        window.show()
        self.app.processEvents()
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        card = window.cards[picture.node_id]

        self.assertTrue(card.busy_overlay.isHidden())
        window.semantic_waiting_assets.add(picture.node_id)
        window._refresh_semantic_card(picture)
        self.app.processEvents()
        self.assertFalse(card.busy_overlay.isHidden())
        self.assertTrue(card.busy_overlay.timer.isActive())
        self.assertEqual(card.busy_overlay.message, "AI ENRICH")

        window.semantic_waiting_assets.discard(picture.node_id)
        window._refresh_semantic_card(picture)
        self.app.processEvents()
        self.assertTrue(card.busy_overlay.isHidden())
        self.assertFalse(card.busy_overlay.timer.isActive())
        window.project_dirty = False
        window.close()

    def test_manual_semantic_enrichment_uses_design_settings_and_redacts_absolute_path(self):
        settings = DesignAISettings(
            provider="lm_studio",
            lm_studio_base_url="http://127.0.0.1:1234/v1",
            lm_studio_model="unit-semantic-model",
            timeout=77,
            auto_semantic_enrichment=False,
            unload_lm_after_semantic_enrichment=False,
        )
        with patch("director_cut_studio.load_design_settings", return_value=settings):
            window = DirectorCutStudio()
            media_root = PROJECT_ROOT / ".director_cache" / "media_semantic_ui_tests"
            media_root.mkdir(parents=True, exist_ok=True)
            picture_path = media_root / "private_semantic_source.png"
            Image.new("RGB", (40, 40), (66, 39, 51)).save(picture_path)
            self.addCleanup(lambda: picture_path.unlink(missing_ok=True))
            picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
            assign_local_media(window.scan, picture, picture_path)
            picture.recognition = (
                f"Source file: {picture_path.resolve()}\n"
                "BLIP visual caption: a person holding a polished metal prop"
            )
            picture.clip_prompt = "Preserve the supplied person's visible wardrobe."

            with (
                patch.object(window.semantic_runner, "is_running", return_value=True),
                patch.object(window.semantic_runner, "write_json") as write_json,
            ):
                self.assertTrue(
                    window.start_semantic_enrichment(
                        picture, force=True, interactive=False
                    )
                )

            request = write_json.call_args.args[0]
            serialized_request = json.dumps(request, ensure_ascii=False)
            self.assertEqual(request["provider"], "lm_studio")
            self.assertEqual(request["base_url"], settings.lm_studio_base_url)
            self.assertEqual(request["model"], settings.lm_studio_model)
            self.assertEqual(request["timeout"], 77)
            self.assertEqual(request["api_key"], "")
            self.assertEqual(request["schema_name"], "h3_media_semantic_enrichment")
            self.assertNotIn(str(picture_path.resolve()), serialized_request)
            self.assertNotIn(str(media_root.resolve()), serialized_request)
            self.assertIn(picture_path.name, request["user_prompt"])
            self.assertIn("[local path omitted]", request["user_prompt"])
            self.assertIn(picture.clip_prompt, request["user_prompt"])
            window.semantic_jobs.clear()
            window.semantic_last_lm_request = {}
            window.project_dirty = False
            window.close()

    def test_video_semantic_enrichment_waits_for_blip_and_audio_jobs(self):
        window = DirectorCutStudio()
        video = next(asset for asset in window.scan.assets if asset.media_type == "video")
        video_path = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "sample.mp4"
        if not video_path.is_file():
            window.project_dirty = False
            window.close()
            self.skipTest("runtime smoke video is not present")
        assign_local_media(window.scan, video, video_path)
        video.recognition = (
            "BLIP video frame · 0.00s: a figure enters the courtyard\n"
            "BEAT ANALYSIS\nEstimated tempo: 112 BPM"
        )
        window.semantic_auto_check.blockSignals(True)
        window.semantic_auto_check.setChecked(True)
        window.semantic_auto_check.blockSignals(False)
        window.blip_jobs["blip:test"] = (video, "0.00s", video_path)
        window.audio_jobs["audio:test"] = video

        with patch.object(window, "start_semantic_enrichment", return_value=True) as start:
            window._maybe_auto_enrich(video)
            start.assert_not_called()

            window.blip_jobs.clear()
            window._maybe_auto_enrich(video)
            start.assert_not_called()

            window.audio_jobs.clear()
            window._maybe_auto_enrich(video)
            start.assert_called_once_with(video, force=False, interactive=False)

        window.project_dirty = False
        window.close()

    def test_semantic_result_writes_independent_fields_and_discards_stale_response(self):
        window = DirectorCutStudio()
        media_root = PROJECT_ROOT / ".director_cache" / "media_semantic_ui_tests"
        media_root.mkdir(parents=True, exist_ok=True)
        picture_path = media_root / "semantic_result_p1.png"
        Image.new("RGB", (40, 40), (27, 61, 44)).save(picture_path)
        self.addCleanup(lambda: picture_path.unlink(missing_ok=True))
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        assign_local_media(window.scan, picture, picture_path)
        raw = "BLIP visual caption: a woman walking beside a koi pond"
        picture.recognition = raw
        fingerprint = window._semantic_source_fingerprint(picture)
        job_id = "media-enrich:success"
        window.semantic_jobs[job_id] = {
            "asset": picture,
            "path": picture.local_path,
            "fingerprint": fingerprint,
            "provider": "lm_studio",
            "base_url": "http://127.0.0.1:1234/v1",
            "model": "unit-model",
            "timeout": 30,
            "unload_lm": False,
        }

        window._handle_semantic_payload({
            "job": job_id,
            "text": json.dumps(
                self._semantic_result(picture, fingerprint, "Grounded first result."),
                ensure_ascii=False,
            ),
        })

        self.assertEqual(picture.recognition, raw)
        self.assertIn("Grounded first result.", picture.semantic_enrichment)
        self.assertIn("UNCERTAIN INFERENCES", picture.semantic_enrichment)
        self.assertEqual(picture.semantic_enrichment_source_hash, fingerprint)
        self.assertIn("unit-model", picture.semantic_enrichment_model)
        self.assertTrue(picture.semantic_enrichment_updated_at)
        accepted_semantic = picture.semantic_enrichment

        stale_job_id = "media-enrich:stale"
        window.semantic_jobs[stale_job_id] = {
            "asset": picture,
            "path": picture.local_path,
            "fingerprint": fingerprint,
            "provider": "lm_studio",
            "base_url": "http://127.0.0.1:1234/v1",
            "model": "unit-model",
            "timeout": 30,
            "unload_lm": False,
        }
        picture.recognition += "\nBLIP visual caption: the source evidence changed"
        window._handle_semantic_payload({
            "job": stale_job_id,
            "text": json.dumps(
                self._semantic_result(picture, fingerprint, "This stale result must be rejected."),
                ensure_ascii=False,
            ),
        })

        self.assertEqual(picture.semantic_enrichment, accepted_semantic)
        self.assertNotIn("This stale result", picture.semantic_enrichment)
        self.assertIn("Stale AI response discarded", window.semantic_errors[picture.node_id])
        self.assertEqual(window._semantic_asset_status_key(picture), "stale")
        window.project_dirty = False
        window.close()

    def test_ai_enrich_auto_syncs_only_existing_overlapping_shots_and_is_undoable(self):
        window = DirectorCutStudio()
        media_root = PROJECT_ROOT / ".director_cache" / "media_semantic_ui_tests"
        media_root.mkdir(parents=True, exist_ok=True)
        picture_path = media_root / "shot_sync_p3.png"
        Image.new("RGB", (48, 48), (11, 38, 57)).save(picture_path)
        self.addCleanup(lambda: picture_path.unlink(missing_ok=True))
        pictures = [asset for asset in window.scan.assets if asset.media_type == "image"]
        picture = pictures[2]
        assign_local_media(window.scan, picture, picture_path)
        picture.recognition = "BLIP visual caption: a cave opening beneath a star field"
        picture.timeline_placed = True
        picture.timeline_track_id = "V3"
        picture.start_seconds = 8.5
        picture.end_seconds = 12.0
        early_shot = DirectorCue(
            "S1", "shot", 0.0, 4.5, "Opening", subject_action="Descend on a rope."
        )
        final_shot = DirectorCue(
            "S3",
            "shot",
            8.5,
            12.0,
            "Final reveal",
            detail="Use P3 as a generic cave entrance with the Southern Cross.",
            subject_action="Hold on the completed photograph.",
            environment_response="The old P3 interpretation is a plain blue night sky.",
        )
        window.director_cues.extend((early_shot, final_shot))
        fingerprint = window._semantic_source_fingerprint(picture)
        result = self._semantic_result(picture, fingerprint, "Glowworms frame a centered Milky Way.")
        result.update({
            "observed_facts": ["Cyan glow points cover both vertical cave walls."],
            "environment": "A narrow cave opening frames the sky.",
            "composition_and_camera": "Vertical composition with the Milky Way centered in the opening.",
            "lighting_and_color": "Cyan bioluminescence contrasts with a pale galactic core.",
            "h3_prompt_keywords": ["cyan glowworms", "centered Milky Way"],
            "suggested_h3_usage": "Preserve the supplied final composition as the reveal.",
            "shot_adaptations": [{
                "cue_id": "S3",
                "framing": "Extreme wide",
                "camera_angle": "Low angle",
                "camera_movement": "Slow push in",
                "movement_speed": "Slow",
                "movement_amplitude": "Small",
                "subject_action": "The living cave scene opens naturally around the centered Milky Way.",
                "environment_response": "Cyan glowworms illuminate a narrow cave opening around the galaxy.",
                "additional_direction": "Preserve P3's vertical spatial composition while adding subtle atmospheric motion.",
                "integration_strategy": "Animate mist, foliage and glow intensity without showing a still photograph.",
            }],
        })
        job_id = "media-enrich:shot-sync"
        window.semantic_jobs[job_id] = {
            "asset": picture,
            "path": picture.local_path,
            "fingerprint": fingerprint,
            "provider": "lm_studio",
            "base_url": "http://127.0.0.1:1234/v1",
            "model": "unit-model",
            "timeout": 30,
            "unload_lm": False,
        }

        window._handle_semantic_payload({"job": job_id, "text": json.dumps(result)})

        self.assertEqual(early_shot.semantic_reference_directions, {})
        self.assertIn("P3", final_shot.semantic_reference_directions)
        synced = final_shot.semantic_reference_directions["P3"]
        self.assertIn("Milky Way", synced)
        self.assertIn("instead of replacing it", synced)
        self.assertNotIn("generic cave entrance", final_shot.detail)
        self.assertIn("vertical spatial composition", final_shot.detail)
        self.assertIn("never display it as a flat photo", final_shot.detail)
        self.assertNotIn("plain blue night sky", final_shot.environment_response)
        self.assertIn("narrow cave opening", final_shot.environment_response)
        self.assertIn("living cave scene", final_shot.subject_action)
        self.assertEqual(final_shot.camera_movement, "Slow push in")
        window._sync_prompt_panel_from_timeline(force=True)
        self.assertIn("AI reference @P3", window.prompt_panel.shots.toPlainText())
        compiled_spec = window._prompt_spec_with_director_cues(window.prompt_panel.spec())
        self.assertTrue(
            any("AI-enriched media reference @P3" in shot for shot in compiled_spec.shots)
        )
        saved_cue = next(
            row for row in window._project_payload()["director_cues"] if row["cue_id"] == "S3"
        )
        self.assertIn("P3", saved_cue["semantic_reference_directions"])
        window.undo_stack.undo()
        self.assertEqual(final_shot.semantic_reference_directions, {})
        self.assertEqual(final_shot.subject_action, "Hold on the completed photograph.")
        self.assertIn("generic cave entrance", final_shot.detail)
        window.undo_stack.redo()
        self.assertIn("P3", final_shot.semantic_reference_directions)
        self.assertIn("living cave scene", final_shot.subject_action)
        window.project_dirty = False
        window.close()

    def test_ai_enrich_without_timeline_shot_does_not_create_or_modify_shots(self):
        window = DirectorCutStudio()
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        picture.timeline_placed = True
        picture.start_seconds = 2.0
        picture.end_seconds = 5.0
        semantic = self._semantic_result(
            picture,
            "a" * 64,
            "A detailed semantic result with no authored Shot to receive it.",
        )

        updated = window._sync_semantic_enrichment_to_existing_shots(picture, semantic)

        self.assertEqual(updated, [])
        self.assertEqual(window.director_cues, [])
        self.assertEqual(window.undo_stack.count(), 0)
        window.project_dirty = False
        window.close()

    def test_ai_enrich_collects_one_purposeful_blip_observation_per_region(self):
        window = DirectorCutStudio()
        media_root = PROJECT_ROOT / ".director_cache" / "media_semantic_ui_tests"
        media_root.mkdir(parents=True, exist_ok=True)
        picture_path = media_root / "multi_region_source.png"
        Image.new("RGB", (64, 80), (19, 43, 67)).save(picture_path)
        self.addCleanup(lambda: picture_path.unlink(missing_ok=True))
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        assign_local_media(window.scan, picture, picture_path)
        picture.recognition = "BLIP visual caption: a misleading poster classification"
        window.select_asset(picture)
        window.analysis_paths[picture.node_id] = [
            ("full frame", picture_path),
            ("upper scene excluding lower titles", picture_path),
            ("central scene excluding edge overlays", picture_path),
            ("central subject detail", picture_path),
        ]

        with (
            patch.object(window.blip_runner, "is_running", return_value=True),
            patch.object(window.blip_runner, "write_json") as write_json,
        ):
            window.enrich_selected_media()

        requests = [call.args[0] for call in write_json.call_args_list]
        self.assertEqual(len(requests), 4)
        self.assertEqual(sum("prompt" in request for request in requests), 3)
        self.assertEqual(
            {request.get("prompt") for request in requests if request.get("prompt")},
            {
                "the scene shows",
                "the lighting and environment show",
                "the central subject is",
            },
        )
        self.assertIn(picture.node_id, window.semantic_waiting_assets)
        self.assertEqual(window.semantic_jobs, {})
        window.blip_jobs.clear()
        window.semantic_waiting_assets.clear()
        window.project_dirty = False
        window.close()

    def test_replacing_timeline_media_clears_old_prompt_and_forces_shot_adaptation(self):
        window = DirectorCutStudio()
        media_root = PROJECT_ROOT / ".director_cache" / "media_replacement_tests"
        media_root.mkdir(parents=True, exist_ok=True)
        old_path = media_root / "old_reference.png"
        new_path = media_root / "new_reference.png"
        Image.new("RGB", (64, 64), (66, 22, 18)).save(old_path)
        Image.new("RGB", (64, 64), (11, 58, 81)).save(new_path)
        self.addCleanup(lambda: old_path.unlink(missing_ok=True))
        self.addCleanup(lambda: new_path.unlink(missing_ok=True))
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        assign_local_media(window.scan, picture, old_path)
        picture.timeline_placed = True
        picture.timeline_track_id = "V3"
        picture.start_seconds = 3.0
        picture.end_seconds = 7.0
        picture.clip_prompt = "Old reference instruction that must not survive replacement."
        shot = DirectorCue("S2", "shot", 3.0, 7.0, "Designed shot", detail="Use P1 as the old room.")
        window.director_cues.append(shot)

        with patch.object(window, "queue_media_preparation") as prepare:
            window.load_asset_file(picture, str(new_path))

        self.assertEqual(picture.local_path, str(new_path.resolve()))
        self.assertEqual(picture.clip_prompt, "")
        self.assertTrue(picture.timeline_placed)
        self.assertEqual((picture.start_seconds, picture.end_seconds), (3.0, 7.0))
        self.assertIn(picture.node_id, window.semantic_waiting_assets)
        prepare.assert_called_once_with(
            picture,
            auto_analyze=True,
            preserve_recognition=False,
        )
        context = window._semantic_job_context(picture)
        self.assertEqual([row["cue_id"] for row in context["existing_shots"]], ["S2"])
        self.assertEqual(len(window.director_cues), 1)
        window.project_dirty = False
        window.close()

    def test_project_payload_persists_media_semantic_fields(self):
        window = DirectorCutStudio()
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        picture.semantic_enrichment = "SUMMARY\nPersist this semantic analysis."
        picture.semantic_enrichment_source_hash = "a" * 64
        picture.semantic_enrichment_model = "lm_studio · persistent-model"
        picture.semantic_enrichment_updated_at = "2026-08-25 12:34:56 UTC"

        saved = window._project_payload()["assets"][picture.node_id]

        self.assertEqual(saved["recognition"], picture.recognition)
        self.assertEqual(saved["semantic_enrichment"], picture.semantic_enrichment)
        self.assertEqual(
            saved["semantic_enrichment_source_hash"],
            picture.semantic_enrichment_source_hash,
        )
        self.assertEqual(saved["semantic_enrichment_model"], picture.semantic_enrichment_model)
        self.assertEqual(
            saved["semantic_enrichment_updated_at"],
            picture.semantic_enrichment_updated_at,
        )
        window.project_dirty = False
        window.close()

    def test_project_roundtrip_restores_virtual_p10_source_and_timeline_use(self):
        root = PROJECT_ROOT / ".director_cache" / "virtual_pool_project_test"
        root.mkdir(parents=True, exist_ok=True)
        media_path = root / "p10.png"
        project_path = root / "virtual.h3director.json"
        Image.new("RGB", (32, 32), (21, 44, 88)).save(media_path)
        self.addCleanup(lambda: media_path.unlink(missing_ok=True))
        self.addCleanup(lambda: project_path.unlink(missing_ok=True))

        window = DirectorCutStudio()
        window._set_design_duration(30.0)
        p10 = create_virtual_media_asset(window.scan, "image")
        window._append_media_card(p10)
        assign_local_media(window.scan, p10, media_path)
        self._place(p10, 20.0, 25.0, "V1", "Use @P10 as the later scene.")
        payload = window._project_payload()
        project_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        window.project_dirty = False
        window.close()

        restored = DirectorCutStudio()
        with patch.object(restored, "queue_media_preparation"):
            restored.load_project_path(project_path)
        recovered = next(
            asset for asset in restored.scan.assets if media_shortcut(asset) == "P10"
        )
        self.assertTrue(recovered.is_virtual)
        self.assertEqual(recovered.local_path, str(media_path.resolve()))
        self.assertTrue(recovered.timeline_placed)
        self.assertEqual((recovered.start_seconds, recovered.end_seconds), (20.0, 25.0))
        self.assertIn(recovered.node_id, restored.cards)
        restored.project_dirty = False
        restored.close()

    def test_design_context_does_not_inject_stale_media_semantic_enrichment(self):
        window = DirectorCutStudio()
        media_root = PROJECT_ROOT / ".director_cache" / "media_semantic_ui_tests"
        media_root.mkdir(parents=True, exist_ok=True)
        picture_path = media_root / "design_context_stale_p1.png"
        Image.new("RGB", (40, 40), (54, 42, 78)).save(picture_path)
        self.addCleanup(lambda: picture_path.unlink(missing_ok=True))
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        assign_local_media(window.scan, picture, picture_path)
        picture.recognition = "BLIP visual caption: a supplied courtyard reference"
        picture.semantic_enrichment = "UNIQUE CURRENT SEMANTIC GUIDANCE"
        picture.semantic_enrichment_source_hash = window._semantic_source_fingerprint(picture)

        ready_row = next(
            row for row in window._design_context()["existing_media"]
            if row["media_id"] == media_shortcut(picture)
        )
        self.assertEqual(ready_row["semantic_enrichment_status"], "ready")
        self.assertIn("UNIQUE CURRENT SEMANTIC GUIDANCE", ready_row["analysis_summary"])

        picture.recognition += "\nBLIP visual caption: changed raw evidence"
        stale_row = next(
            row for row in window._design_context()["existing_media"]
            if row["media_id"] == media_shortcut(picture)
        )
        self.assertEqual(stale_row["semantic_enrichment_status"], "stale")
        self.assertEqual(stale_row["semantic_enrichment"], "")
        self.assertNotIn("UNIQUE CURRENT SEMANTIC GUIDANCE", stale_row["analysis_summary"])
        self.assertIn("changed raw evidence", stale_row["raw_analysis_summary"])
        window.project_dirty = False
        window.close()

    def test_design_media_inventory_inserts_reference_and_filters_selected_context(self):
        window = DirectorCutStudio()
        media_root = PROJECT_ROOT / ".director_cache" / "media_pool_design_tests"
        media_root.mkdir(parents=True, exist_ok=True)
        picture_path = media_root / "inventory_p1.png"
        Image.new("RGB", (48, 48), (45, 62, 31)).save(picture_path)
        self.addCleanup(lambda: picture_path.unlink(missing_ok=True))
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        assign_local_media(window.scan, picture, picture_path)
        picture.recognition = "BLIP visual caption: a Tang general in red armour"

        with patch.object(DesignPageDialog, "refresh_checkpoints", autospec=True):
            dialog = DesignPageDialog(
                window.runtime,
                window._design_context(),
                window.scan.counts,
                window,
                context_provider=window._design_context,
            )
        self.assertEqual(dialog.design_media_list.count(), 1)
        item = dialog.design_media_list.item(0)
        self.assertIn("P1", item.text())
        self.assertIn("Tang general", item.toolTip())

        dialog.requirement_edit.setPlainText("Use the supplied general")
        cursor = dialog.requirement_edit.textCursor()
        cursor.setPosition(len(dialog.requirement_edit.toPlainText()))
        dialog.requirement_edit.setTextCursor(cursor)
        dialog._insert_media_reference(item)
        self.assertIn("@P1", dialog.requirement_edit.toPlainText())
        selected = dialog._selected_design_context()
        self.assertEqual(selected["selected_existing_media_ids"], ["P1"])
        self.assertEqual(selected["existing_media"][0]["media_id"], "P1")

        item.setCheckState(Qt.Unchecked)
        selected = dialog._selected_design_context()
        self.assertEqual(selected["selected_existing_media_ids"], [])
        self.assertEqual(selected["existing_media"], [])
        dialog.close()
        window.project_dirty = False
        window.close()

    def test_lm_design_prompt_requires_media_reuse_before_gap_generation(self):
        window = DirectorCutStudio()
        media_root = PROJECT_ROOT / ".director_cache" / "media_pool_design_tests"
        media_root.mkdir(parents=True, exist_ok=True)
        picture_path = media_root / "prompt_p1.png"
        Image.new("RGB", (48, 48), (70, 45, 32)).save(picture_path)
        self.addCleanup(lambda: picture_path.unlink(missing_ok=True))
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        assign_local_media(window.scan, picture, picture_path)
        picture.recognition = "BLIP visual caption: a bronze cauldron in a Tang courtyard"

        with patch.object(DesignPageDialog, "refresh_checkpoints", autospec=True):
            dialog = DesignPageDialog(
                window.runtime, window._design_context(), window.scan.counts, window
            )
        dialog.pending_requirement = "Use @P1 for the courtyard and add only missing action media."
        dialog.active_design_context = dialog._selected_design_context()
        with patch.object(dialog, "_submit") as submit:
            dialog._start_lm_design()
        payload = submit.call_args.args[1]
        user_prompt = payload["user_prompt"]
        system_prompt = payload["system_prompt"]
        self.assertIn("First audit and reuse", user_prompt)
        self.assertIn("existing_media_uses", user_prompt)
        self.assertIn("Never emit a replacement media_request", user_prompt)
        self.assertIn("currently free", user_prompt)
        self.assertIn(
            "media_requests must contain only genuinely missing assets",
            system_prompt,
        )
        self.assertIn("@P1", system_prompt)
        dialog.design_busy_overlay.stop()
        dialog.close()
        window.project_dirty = False
        window.close()

    def test_apply_design_reuses_p1_and_assigns_missing_media_only_to_empty_p2(self):
        window = DirectorCutStudio()
        image_assets = [
            asset for asset in window.scan.assets if asset.media_type == "image"
        ]
        self.assertGreaterEqual(len(image_assets), 3)
        p1, p2, p3 = image_assets[:3]
        media_root = PROJECT_ROOT / ".director_cache" / "media_pool_design_tests"
        media_root.mkdir(parents=True, exist_ok=True)
        p1_path = media_root / "reuse_p1.png"
        p3_path = media_root / "reserved_p3.png"
        generated_path = media_root / "generated_for_p2.png"
        Image.new("RGB", (48, 48), (31, 49, 68)).save(p1_path)
        Image.new("RGB", (48, 48), (75, 40, 28)).save(p3_path)
        Image.new("RGB", (48, 48), (22, 78, 53)).save(generated_path)
        for path in (p1_path, p3_path, generated_path):
            self.addCleanup(lambda target=path: target.unlink(missing_ok=True))

        assign_local_media(window.scan, p1, p1_path)
        p1.recognition = (
            "BLIP visual caption: a black-clad assassin\n"
            "Identity embedding and timeline analysis must survive Apply"
        )
        p1.clip_prompt = "Preserve the original assassin identity."
        p1_original_path = p1.local_path
        p1_original_recognition = p1.recognition

        p2.local_path = ""
        p2.timeline_placed = False
        assign_local_media(window.scan, p3, p3_path)
        p3.recognition = "BLIP visual caption: an already loaded but unselected koi pond"
        p3.timeline_placed = True
        p3_original_path = p3.local_path
        p3_original_filename = p3.filename
        p3_original_recognition = p3.recognition

        plan = sample_design()
        plan["existing_media_uses"] = [{
            "requirement_id": "assassin_identity",
            "media_id": "P1",
            "media_type": "image",
            "usage": "h3_reference",
            "reuse_policy": "whole_design",
            "start_seconds": 0.0,
            "end_seconds": 12.0,
            "track": "V1",
            "subject_keywords": ["assassin", "black_clothing"],
            "instruction": "Use the supplied assassin identity throughout the design.",
        }]
        generated_request = {
            **plan["media_requests"][0],
            "requirement_id": "courtyard_action_state",
            "reuse_policy": "time_scoped",
            "start_seconds": 4.0,
            "end_seconds": 8.0,
            "track": "V2",
            "local_path": str(generated_path.resolve()),
            "preview_path": str(generated_path.resolve()),
            "generated_by_comfyui": True,
        }

        warnings = window._apply_ai_design_direct(plan, [generated_request], replace=True)
        self.assertEqual(warnings, [])
        self.assertEqual(p1.local_path, p1_original_path)
        self.assertEqual(p1.recognition, p1_original_recognition)
        self.assertTrue(p1.timeline_placed)
        self.assertEqual((p1.start_seconds, p1.end_seconds), (0.0, 12.0))
        self.assertEqual(p2.local_path, str(generated_path.resolve()))
        self.assertEqual(p2.filename, generated_path.name)
        self.assertTrue(p2.timeline_placed)
        self.assertIn("AI DESIGN GENERATED REFERENCE", p2.recognition)
        self.assertEqual(p3.local_path, p3_original_path)
        self.assertEqual(p3.filename, p3_original_filename)
        self.assertEqual(p3.recognition, p3_original_recognition)
        self.assertFalse(p3.timeline_placed)
        window.project_dirty = False
        window.close()

    def test_recovered_empty_picture_request_uses_its_preferred_physical_slot(self):
        window = DirectorCutStudio()
        media_root = PROJECT_ROOT / ".director_cache" / "preferred_design_slot_test"
        media_root.mkdir(parents=True, exist_ok=True)
        generated_path = media_root / "recovered_p4.png"
        Image.new("RGB", (48, 48), (62, 31, 84)).save(generated_path)
        self.addCleanup(lambda: generated_path.unlink(missing_ok=True))
        pictures = [
            asset for asset in window.scan.assets if asset.media_type == "image"
        ]
        plan = normalize_design_plan(
            sample_design(), window.scan.counts
        )
        material = {
            **plan["media_requests"][0],
            "preferred_media_id": "P4",
            "local_path": str(generated_path.resolve()),
            "preview_path": str(generated_path.resolve()),
            "generated_by_comfyui": True,
        }

        warnings = window._apply_ai_design_direct(plan, [material], replace=True)

        self.assertEqual(warnings, [])
        self.assertFalse(bool(pictures[0].local_path))
        self.assertEqual(pictures[3].local_path, str(generated_path.resolve()))
        self.assertTrue(pictures[3].timeline_placed)
        window.project_dirty = False
        window.close()

    def test_two_design_rounds_reuse_p4_and_fill_p4_through_p9_without_renumbering(self):
        window = DirectorCutStudio()
        media_root = PROJECT_ROOT / ".director_cache" / "two_round_design_media_test"
        media_root.mkdir(parents=True, exist_ok=True)
        paths = []
        for number in range(1, 10):
            path = media_root / f"round_media_p{number}.png"
            Image.new("RGB", (32, 32), (number * 17, 40, 90)).save(path)
            paths.append(path)
            self.addCleanup(lambda target=path: target.unlink(missing_ok=True))

        pictures = sorted(
            (asset for asset in window.scan.assets if asset.media_type == "image"),
            key=lambda asset: int(media_shortcut(asset)[1:]),
        )
        for asset, path in zip(pictures[:3], paths[:3]):
            assign_local_media(window.scan, asset, str(path.resolve()))

        base_plan = normalize_design_plan(sample_design(), window._design_context()["media_capacity"])
        base_plan["existing_media_uses"] = []

        def generated_material(path, requirement_id, start, end):
            return {
                "requirement_id": requirement_id,
                "media_type": "image",
                "usage": "h3_reference",
                "reuse_policy": "time_scoped",
                "start_seconds": start,
                "end_seconds": end,
                "track": "V1",
                "subject_keywords": [requirement_id],
                "prompt": f"One frozen story instant for {requirement_id}.",
                "local_path": str(path.resolve()),
                "preview_path": str(path.resolve()),
                "generated_by_comfyui": True,
            }

        first_materials = [
            generated_material(paths[3], "round1_p4", 0.0, 4.0),
            generated_material(paths[4], "round1_p5", 4.0, 8.0),
            generated_material(paths[5], "round1_p6", 8.0, 12.0),
        ]
        self.assertEqual(
            window._apply_ai_design_direct(base_plan, first_materials, replace=True),
            [],
        )
        first_loaded = {
            media_shortcut(asset)
            for asset in window.scan.assets
            if asset.media_type == "image" and str(asset.local_path or "").strip()
        }
        self.assertEqual(first_loaded, {f"P{number}" for number in range(1, 7)})

        second_plan = deepcopy(base_plan)
        second_plan["existing_media_uses"] = [{
            "requirement_id": "reuse_p4",
            "media_id": "P4",
            "media_type": "image",
            "usage": "h3_reference",
            "reuse_policy": "time_scoped",
            "start_seconds": 0.0,
            "end_seconds": 4.0,
            "track": "V1",
            "subject_keywords": ["p4 identity"],
            "instruction": "Preserve @P4 exactly in the opening Shot.",
        }]
        second_materials = [
            generated_material(paths[6], "round2_p7", 0.0, 4.0),
            generated_material(paths[7], "round2_p8", 4.0, 8.0),
            generated_material(paths[8], "round2_p9", 8.0, 12.0),
        ]
        self.assertEqual(
            window._apply_ai_design_direct(second_plan, second_materials, replace=True),
            [],
        )
        loaded_by_path = {
            Path(str(asset.local_path)).name: media_shortcut(asset)
            for asset in window.scan.assets
            if asset.media_type == "image" and str(asset.local_path or "").strip()
        }
        self.assertEqual(loaded_by_path[paths[3].name], "P4")
        self.assertEqual(loaded_by_path[paths[6].name], "P7")
        self.assertEqual(loaded_by_path[paths[7].name], "P8")
        self.assertEqual(loaded_by_path[paths[8].name], "P9")
        second_context_ids = {
            row["media_id"] for row in window._design_context()["existing_media"]
            if row["type"] == "image"
        }
        self.assertEqual(second_context_ids, {f"P{number}" for number in range(1, 10)})
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

    def test_ai_design_auto_creates_higher_visual_and_audio_tracks(self):
        window = DirectorCutStudio()
        plan = sample_design()
        plan["shots"][0]["track"] = "V5"
        plan["text_layers"] = [{
            "start_seconds": 0.0,
            "end_seconds": 4.0,
            "track": "V1",
            "content": "Keep moving through the reveal.",
            "role": "voice_over",
            "speaker": "S1",
            "language": "English",
            "delivery": "Urgent",
            "lip_sync": False,
            "explicit_user_requested": True,
        }]
        plan = normalize_design_plan(plan, window.scan.counts)
        warnings = window._apply_ai_design_direct(plan, [], replace=True)
        self.assertTrue(any(track.track_id == "V5" for track in window.tracks))
        self.assertTrue(any(track.track_id == "A5" for track in window.tracks))
        self.assertEqual(window.director_cues[0].track_id, "V5")
        self.assertEqual(window.text_layers[0].track_id, "A5")
        self.assertEqual(warnings, [])
        window.project_dirty = False
        window.close()

    def test_ai_design_apply_undo_redo_rebuilds_dynamic_track_headers(self):
        window = DirectorCutStudio()
        plan = sample_design()
        plan["shots"][0]["track"] = "V6"
        plan = normalize_design_plan(plan, window.scan.counts)
        before = window._design_workspace_state()
        design_dir = PROJECT_ROOT / ".director_cache" / "dynamic_track_header_state_test"
        design_dir.mkdir(parents=True, exist_ok=True)

        window._commit_ai_design(plan, [], True, before, design_dir)
        self.app.processEvents()
        self.app.processEvents()
        self.assertIn("V6", [track.track_id for track in window.tracks])
        self.assertEqual(
            list(window.track_header_widgets),
            [track.track_id for track in window.tracks],
        )
        self.assertEqual(window.track_header_widgets["V6"].track.kind, "visual")

        window.undo_stack.undo()
        self.app.processEvents()
        self.assertNotIn("V6", [track.track_id for track in window.tracks])
        self.assertEqual(
            list(window.track_header_widgets),
            [track.track_id for track in window.tracks],
        )

        window.undo_stack.redo()
        self.app.processEvents()
        self.app.processEvents()
        self.assertIn("V6", window.track_header_widgets)
        self.assertEqual(
            list(window.track_header_widgets),
            [track.track_id for track in window.tracks],
        )
        window.project_dirty = False
        window.close()

    def test_ai_design_places_repeated_media_uses_as_independent_clips(self):
        window = DirectorCutStudio()
        media_root = PROJECT_ROOT / ".director_cache" / "repeated_design_media"
        media_root.mkdir(parents=True, exist_ok=True)
        picture_path = media_root / "p1.png"
        Image.new("RGB", (48, 48), (30, 50, 70)).save(picture_path)
        self.addCleanup(lambda: picture_path.unlink(missing_ok=True))
        source = next(asset for asset in window.scan.assets if asset.media_type == "image")
        assign_local_media(window.scan, source, picture_path)
        payload = sample_design()
        payload["existing_media_uses"] = [
            {
                "requirement_id": "p1_opening", "media_id": "P1", "media_type": "image",
                "usage": "h3_reference", "reuse_policy": "time_scoped",
                "start_seconds": 1.0, "end_seconds": 5.0, "track": "V1",
                "subject_keywords": ["hero"], "instruction": "Opening identity view.",
            },
            {
                "requirement_id": "p1_return", "media_id": "P1", "media_type": "image",
                "usage": "h3_reference", "reuse_policy": "time_scoped",
                "start_seconds": 8.0, "end_seconds": 12.0, "track": "V2",
                "subject_keywords": ["hero"], "instruction": "Return from a low angle.",
            },
        ]
        plan = normalize_design_plan(
            payload,
            window.scan.counts,
            existing_media=window._design_context()["existing_media"],
        )
        window._apply_ai_design_direct(plan, [], replace=True)
        self.assertEqual((source.start_seconds, source.end_seconds), (1.0, 5.0))
        self.assertEqual(source.clip_prompt, "Opening identity view.")
        self.assertEqual(len(window.scan.timeline_clips), 1)
        repeated = window.scan.timeline_clips[0]
        self.assertEqual((repeated.start_seconds, repeated.end_seconds), (8.0, 12.0))
        self.assertEqual(repeated.timeline_track_id, "V2")
        self.assertEqual(repeated.clip_prompt, "Return from a low angle.")
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

    def test_media_pool_source_can_be_dropped_twice_as_independent_clips(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        self.app.processEvents()
        asset = next(item for item in window.scan.assets if item.media_type == "image")

        self._send_drop(window, asset, 1.0)
        first_range = (asset.start_seconds, asset.end_seconds)
        self._send_drop(window, asset, 8.0)

        self.assertEqual(first_range, (1.0, 4.0))
        self.assertEqual((asset.start_seconds, asset.end_seconds), first_range)
        self.assertEqual(len(window.scan.timeline_clips), 1)
        repeated = window.scan.timeline_clips[0]
        self.assertEqual(repeated.source_node_id, asset.node_id)
        self.assertTrue(repeated.clip_id.startswith("clip-"))
        self.assertEqual((repeated.start_seconds, repeated.end_seconds), (8.0, 11.0))
        self.assertEqual(len(window._project_payload()["timeline_clips"]), 1)

        window.undo_stack.undo()
        self.assertEqual(window.scan.timeline_clips, [])
        window.undo_stack.redo()
        self.assertEqual(window.scan.timeline_clips, [repeated])
        window.project_dirty = False
        window.close()

    def test_repeated_media_clips_round_trip_in_project_format_15(self):
        project = PROJECT_ROOT / ".director_cache" / "repeated_clip_project_test.h3director.json"
        self.addCleanup(lambda: project.unlink(missing_ok=True))
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        self.app.processEvents()
        source = next(item for item in window.scan.assets if item.media_type == "image")
        self._send_drop(window, source, 1.0)
        self._send_drop(window, source, 8.0)
        repeated_id = window.scan.timeline_clips[0].clip_id
        project.write_text(
            json.dumps(window._project_payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        window.project_dirty = False
        window.close()

        restored = DirectorCutStudio()
        restored.load_project_path(project)
        restored_source = next(
            item for item in restored.scan.assets if item.node_id == source.node_id
        )
        self.assertEqual((restored_source.start_seconds, restored_source.end_seconds), (1.0, 4.0))
        self.assertEqual(len(restored.scan.timeline_clips), 1)
        repeated = restored.scan.timeline_clips[0]
        self.assertEqual(repeated.clip_id, repeated_id)
        self.assertEqual(repeated.source_node_id, restored_source.node_id)
        self.assertEqual((repeated.start_seconds, repeated.end_seconds), (8.0, 11.0))
        restored.project_dirty = False
        restored.close()

    def test_portable_project_media_path_rebases_from_old_work_folder(self):
        root = PROJECT_ROOT / ".director_cache" / "portable_media_restore_test"
        nested = root / "3d"
        nested.mkdir(parents=True, exist_ok=True)
        media = nested / "reference.png"
        media.write_bytes(b"portable-reference")
        project = root / "director_project.h3director.json"
        old_root = Path("D:/old-machine/example/project")
        saved = {
            "filename": media.name,
            "local_path": str(old_root / "3d" / media.name),
        }
        try:
            resolved = resolve_project_media_path(project, saved, old_root)
            self.assertEqual(resolved, media.resolve())
        finally:
            media.unlink(missing_ok=True)
            nested.rmdir()
            root.rmdir()

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
        window.prompt_generation_timer.stop()
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
        self.app.processEvents()
        window._reflow_media_pool()
        self.assertEqual(window._media_grid_columns, 3)
        self.assertEqual(
            [window.add_media_buttons[kind].text() for kind in ("image", "video", "audio")],
            ["+I", "+V", "+A"],
        )
        self.assertTrue(all(button.width() == 30 for button in window.add_media_buttons.values()))
        self.assertLessEqual(window.media_header.font().pointSizeF(), 10.0)

        window.media_scroll.setFixedWidth(255)
        self.app.processEvents()
        window._reflow_media_pool()
        narrow_positions = [window.media_grid.getItemPosition(index) for index in range(5)]
        narrow_width = window.media_card_order[0].width()
        self.assertEqual([position[1] for position in narrow_positions[:3]], [0, 1, 2])
        self.assertEqual(narrow_positions[3][0], 1)
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
        self.assertEqual(max(position[1] for position in wide_positions), 2)
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

    def test_json_worker_pipe_backpressure_never_blocks_ui_request_queue(self):
        runner = JsonLineProcess(name="pipe-backpressure-test")
        messages = []
        finished = []
        runner.message.connect(messages.append)
        runner.finished.connect(lambda code, log: finished.append((code, log)))
        program = str(PROJECT_ROOT / "ai_libraries_common" / "python_env" / "python.exe")
        script = (
            "import json,sys,time;"
            "print(json.dumps({'ready':True}),flush=True);"
            "time.sleep(1.0);"
            "jobs=[json.loads(sys.stdin.readline())['job'] for _ in range(3)];"
            "print(json.dumps({'received':jobs}),flush=True)"
        )
        self.assertTrue(runner.start(program, ["-c", script]))
        for _ in range(100):
            QTest.qWait(10)
            if runner.is_ready():
                break
        self.assertTrue(runner.is_ready())

        large_prompt = "semantic evidence " * 45_000
        started = time.perf_counter()
        for index in range(3):
            runner.write_json({"job": f"enrich-{index}", "prompt": large_prompt})
        enqueue_elapsed = time.perf_counter() - started
        # The child deliberately does not read stdin for one second.  A direct
        # pipe write on the Qt thread would therefore take about one second;
        # queuing all three requests must remain effectively immediate.
        self.assertLess(enqueue_elapsed, 0.35)

        for _ in range(250):
            QTest.qWait(10)
            if finished:
                break
        self.assertTrue(finished)
        received = next(item["received"] for item in messages if "received" in item)
        self.assertEqual(received, ["enrich-0", "enrich-1", "enrich-2"])

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
        self.assertEqual(payload["version"], PROJECT_FORMAT_VERSION)
        self.assertEqual(payload["application_version"], APP_VERSION)
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
        self.assertEqual(payload["version"], PROJECT_FORMAT_VERSION)
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

    def test_type_text_clip_bright_edges_trim_and_are_undoable(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        layer = TextLayer("T-trim", "Trim me", 1.0, 4.0, "V3")
        window.text_layers.append(layer)
        window._refresh_text_layers(layer)
        window.set_timeline_tool("selection")
        self.app.processEvents()

        text_clip = next(
            item for item in window.timeline.scene_obj.items()
            if isinstance(item, TimelineTextClip) and item.layer is layer
        )
        right = window.timeline.mapFromScene(
            text_clip.mapToScene(QPointF(text_clip.rect().width() - 2, text_clip.rect().height() / 2))
        )
        right_target = right + QPoint(round(window.timeline.pps), 0)
        QTest.mousePress(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, right)
        QTest.mouseMove(window.timeline.viewport(), right_target, 40)
        QTest.mouseRelease(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, right_target)
        QTest.qWait(30)
        self.assertAlmostEqual(layer.start_seconds, 1.0)
        self.assertAlmostEqual(layer.end_seconds, 5.0)

        window.undo_stack.undo()
        self.assertAlmostEqual(layer.end_seconds, 4.0)
        window.undo_stack.redo()
        self.assertAlmostEqual(layer.end_seconds, 5.0)
        self.app.processEvents()

        text_clip = next(
            item for item in window.timeline.scene_obj.items()
            if isinstance(item, TimelineTextClip) and item.layer is layer
        )
        left = window.timeline.mapFromScene(
            text_clip.mapToScene(QPointF(2, text_clip.rect().height() / 2))
        )
        left_target = left + QPoint(round(window.timeline.pps / 2), 0)
        QTest.mousePress(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, left)
        QTest.mouseMove(window.timeline.viewport(), left_target, 40)
        QTest.mouseRelease(window.timeline.viewport(), Qt.LeftButton, Qt.NoModifier, left_target)
        QTest.qWait(30)
        self.assertAlmostEqual(layer.start_seconds, 1.5)
        self.assertAlmostEqual(layer.end_seconds, 5.0)
        window.project_dirty = False
        window.close()

    def test_type_tool_places_media_targeted_text_on_nearest_empty_visual_track(self):
        window = DirectorCutStudio()
        window.resize(1400, 900)
        window.show()
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        for asset in window.scan.assets:
            asset.timeline_placed = False
        picture.timeline_placed = True
        picture.timeline_track_id = "V1"
        picture.timeline_lane = next(
            index for index, track in enumerate(window.tracks) if track.track_id == "V1"
        )
        picture.start_seconds = 0.0
        picture.end_seconds = 4.0
        window.timeline.rebuild()

        with (
            patch.object(ContentLayerDialog, "exec", return_value=1),
            patch.object(ContentLayerDialog, "state", return_value={"text": "Independent title"}),
        ):
            window._type_tool_targeted(picture)

        self.assertEqual(len(window.text_layers), 1)
        layer = window.text_layers[0]
        self.assertEqual(layer.track_id, "V2")
        self.assertNotEqual(layer.track_id, picture.timeline_track_id)
        window.render_timeline_at(1.0, force_seek=True)
        self.app.processEvents()
        self.assertTrue(window.monitor_text_labels[layer.layer_id].isVisible())
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
        self.assertGreaterEqual(
            window.timeline_tool_scroll.width(), window.timeline_tools_minimum_width
        )
        self.assertEqual(
            window.timeline_tool_buttons["shot"].toolButtonStyle(), Qt.ToolButtonTextBesideIcon
        )

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

    def test_track_headers_resync_after_dynamic_visual_tracks_rebuild(self):
        window = DirectorCutStudio()
        window.resize(1400, 650)
        window._design_track("V12", "visual")
        picture = next(asset for asset in window.scan.assets if asset.media_type == "image")
        picture.timeline_placed = True
        picture.timeline_track_id = "V5"
        picture.timeline_lane = 0
        window.timeline.set_tracks(window.tracks)
        window._rebuild_track_headers()
        window.show()
        self.app.processEvents()

        timeline_bar = window.timeline.verticalScrollBar()
        header_bar = window.track_header_scroll.verticalScrollBar()
        self.assertGreater(header_bar.maximum(), 0)
        header_bar.blockSignals(True)
        header_bar.setValue(min(header_bar.maximum(), 40))
        header_bar.blockSignals(False)
        timeline_bar.setValue(0)
        self.assertNotEqual(header_bar.value(), timeline_bar.value())

        window._rebuild_track_headers()
        self.app.processEvents()
        self.app.processEvents()

        self.assertEqual(header_bar.value(), timeline_bar.value())
        self.assertEqual(picture.timeline_track_id, "V5")
        self.assertEqual(
            window.tracks[picture.timeline_lane].kind,
            "visual",
        )
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
        self.assertNotIn("GET READY", " ".join(spec.shots))
        self.assertEqual(
            [row["text"] for row in spec.text_ranges],
            ["GET READY", "GET READY"],
        )
        payload = window._project_payload()
        self.assertEqual(payload["version"], PROJECT_FORMAT_VERSION)
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
        self.assertIn("core", dialog.action_budget_label.text().lower())
        self.assertTrue(state["continuity_state"])
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
            # Allow both queued boundaries (mouse release -> modal -> undo
            # command) to unwind on slower Windows CI/event loops.
            QTest.qWait(80)

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
        self.assertNotIn("Get ready", spec.shot_ranges[0]["description"])
        self.assertEqual(spec.text_ranges[0]["text"], "Get ready")
        self.assertEqual(spec.text_ranges[0]["speaker"], "S2")
        self.assertEqual(spec.text_ranges[0]["language"], "Cantonese")
        self.assertTrue(spec.text_ranges[0]["lip_sync"])
        dialog.role_combo.setCurrentIndex(dialog.role_combo.findData("voice_over"))
        self.assertTrue(all(widget.isHidden() for _label, widget in dialog.dialogue_rows))
        self.assertFalse(dialog.state()["lip_sync"])
        dialog.close()
        window.project_dirty = False
        window.close()

    def test_dialogue_type_clip_repairs_from_visual_track_to_visible_audio_track(self):
        window = DirectorCutStudio()
        layer = TextLayer(
            "T1", "这句话必须逐字说完。", 0.0, 3.0, "V3",
            content_role="dialogue", speaker="S1", language="Mandarin Chinese",
            delivery="Natural", lip_sync=True,
        )
        window.text_layers = [layer]
        window._refresh_text_layers(layer)
        self.app.processEvents()

        self.assertEqual(layer.track_id, "A4")
        dialogue_track = next(track for track in window.tracks if track.track_id == "A4")
        self.assertEqual(dialogue_track.kind, "audio")
        self.assertEqual(dialogue_track.name, "A4 Dialogue")
        clip = next(
            item for item in window.timeline.scene_obj.items()
            if isinstance(item, TimelineTextClip) and item.layer is layer
        )
        self.assertIn("DIA", clip.label.text())
        self.assertAlmostEqual(
            clip.y(),
            window.timeline._track_top(window.tracks.index(dialogue_track)) + 2,
        )
        window.project_dirty = False
        window.close()

    def test_timeline_prompt_reconcile_replaces_stale_design_brief_with_current_media_shots_and_voiceover(self):
        window = DirectorCutStudio()
        for asset in window.scan.assets:
            asset.timeline_placed = False
        picture = [asset for asset in window.scan.assets if asset.media_type == "image"][2]
        picture.timeline_placed = True
        picture.timeline_track_id = "V1"
        picture.start_seconds = 8.0
        picture.end_seconds = 12.0
        audio = next(asset for asset in window.scan.assets if asset.media_type == "audio")
        audio.timeline_placed = True
        audio.timeline_track_id = "A1"
        audio.start_seconds = 0.0
        audio.end_seconds = 12.0
        audio.recognition = "WHISPER TRANSCRIPT · unit\n[00:00.000–00:12.000] stale machine words"
        shot = DirectorCue(
            "S3", "shot", 8.0, 12.0, "Celestial reveal", track_id="V1",
            subject_action="Tom reveals glowworms aligned beneath the Southern Cross",
            environment_response="The latest P3 night-sky reference fills the cave opening",
            semantic_reference_directions={"P3": "Use the newly replaced real night-sky photograph."},
        )
        voiceover = TextLayer(
            "T1", "螢光蟲同南十字座上下呼應", 0.0, 12.0, "V2",
            content_role="voice_over", shot_id="S3",
        )
        window.director_cues = [shot]
        window.text_layers = [voiceover]
        window.prompt_panel.brief.setPlainText(
            "Old AI Design placeholder: show a generic Milky Way cave image."
        )

        window._refresh_director_cues()

        brief = window.prompt_panel.brief.toPlainText()
        self.assertNotIn("generic Milky Way cave image", brief)
        self.assertIn("Southern Cross", brief)
        self.assertIn("螢光蟲同南十字座上下呼應", brief)
        self.assertIn("ignore superseded AI Design placeholder descriptions", brief)
        self.assertIn("@P3", brief)
        self.assertIn("@A1", brief)
        spec = window._prompt_spec_with_director_cues(window.prompt_panel.spec())
        self.assertNotIn(voiceover.text, spec.shot_ranges[0]["description"])
        self.assertEqual(spec.text_ranges[0]["content_role"], "voice_over")
        self.assertEqual(spec.text_ranges[0]["text"], voiceover.text)
        segment_prompt = window._prompt_for_window(
            8.0,
            12.0,
            [picture, audio],
            is_final_window=True,
        )
        self.assertIn("AI-enriched media reference <Picture 1>", segment_prompt)
        self.assertNotIn("@P3", segment_prompt)
        self.assertNotIn("@A1", segment_prompt)
        # A Type/Dialogue clip is owned by the hidden Segment containing its
        # start time; later overlapping windows must not replay the full line.
        self.assertNotIn(voiceover.text, segment_prompt)
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

    def test_active_api_export_rebuilds_dynamic_mapping_before_compile(self):
        window = DirectorCutStudio()
        window.prompt_panel.brief.setPlainText("Use the current Timeline references.")
        with (
            patch.object(window, "generate_prompt", wraps=window.generate_prompt) as regenerate,
            patch(
                "director_cut_studio.QFileDialog.getSaveFileName",
                return_value=("", ""),
            ),
        ):
            window.export_active_api()
        regenerate.assert_called_once_with(interactive=False)
        window.project_dirty = False
        window.close()

    def test_native_render_track_filters_and_prompt_ordinals_stay_aligned(self):
        window = DirectorCutStudio()
        pictures = [asset for asset in window.scan.assets if asset.media_type == "image"]
        videos = [asset for asset in window.scan.assets if asset.media_type == "video"]
        audios = [asset for asset in window.scan.assets if asset.media_type == "audio"]
        selected = (pictures[0], pictures[3], videos[1], audios[0], audios[2])
        track_ids = ("V1", "V2", "V3", "A1", "A2")
        for asset, track_id in zip(selected, track_ids):
            asset.timeline_placed = True
            asset.timeline_track_id = track_id
            asset.start_seconds = 0.0
            asset.end_seconds = 12.0
        next(track for track in window.tracks if track.track_id == "V1").visible = False
        next(track for track in window.tracks if track.track_id == "A1").muted = True
        window.prompt_panel.brief.setPlainText(
            "Use @P1 and @P4 with @V2 motion, @A1 dialogue and @A3 music."
        )

        compiled, active = window._compiled_job(
            megapixels=0.2,
            seed=123,
            enable_rtx_vsr=False,
        )
        self.assertNotIn(pictures[0], active)
        self.assertIn(pictures[3], active)
        self.assertIn(videos[1], active)
        self.assertNotIn(audios[0], active)
        self.assertIn(audios[2], active)
        prompt = next(
            node["inputs"]["value"]
            for node in compiled.values()
            if node.get("class_type") == "PrimitiveStringMultiline"
        )
        self.assertIn("[P1 reference is inactive in this segment]", prompt)
        self.assertIn("<Picture 1>", prompt)
        self.assertNotIn("<Picture 2>", prompt)
        self.assertIn("<Video 1>", prompt)
        self.assertIn("[A1 reference is inactive in this segment]", prompt)
        # V2's synchronized soundtrack is Audio 1, so standalone A3 is Audio 2.
        self.assertIn("<Audio 2>", prompt)
        h3_inputs = compiled[window.scan.h3_node_ids[0]]["inputs"]
        self.assertEqual(
            h3_inputs["ref_images.ref_image_0"], [pictures[0].node_id, 0]
        )
        self.assertNotEqual(h3_inputs["ref_images.ref_image_0"], [pictures[3].node_id, 0])
        self.assertEqual(
            h3_inputs["ref_videos.ref_video_0"],
            window.scan.nodes[window.scan.h3_node_ids[0]]["inputs"][videos[0].binding],
        )
        self.assertEqual(
            h3_inputs["ref_video_audios.ref_video_audio_0"],
            window.scan.nodes[window.scan.h3_node_ids[0]]["inputs"]
            [videos[0].paired_audio_binding],
        )
        self.assertEqual(
            h3_inputs["ref_audios.ref_audio_0"],
            window.scan.nodes[window.scan.h3_node_ids[0]]["inputs"][audios[0].binding],
        )
        window.project_dirty = False
        window.close()

    def test_partial_native_rerender_uses_local_shot_time_and_only_its_references(self):
        window = DirectorCutStudio()
        window._set_design_duration(30.0)
        pictures = [asset for asset in window.scan.assets if asset.media_type == "image"]
        pictures[0].timeline_placed = True
        pictures[0].timeline_track_id = "V1"
        pictures[0].start_seconds, pictures[0].end_seconds = 0.0, 10.0
        pictures[3].timeline_placed = True
        pictures[3].timeline_track_id = "V2"
        pictures[3].start_seconds, pictures[3].end_seconds = 16.0, 22.0
        window.director_cues = [
            DirectorCue("S1", "shot", 0.0, 8.0, "Opening action", track_id="V1"),
            DirectorCue(
                "S2",
                "shot",
                16.0,
                22.0,
                "Escape action",
                subject_action="Use @P4 while the subject escapes.",
                track_id="V2",
            ),
        ]
        window.prompt_panel.brief.setPlainText("Create the complete 30-second story.")
        window.clip_start.setValue(15.0)
        window.clip_end.setValue(23.0)

        compiled, active = window._compiled_job(
            megapixels=0.2,
            seed=456,
            enable_rtx_vsr=False,
        )
        self.assertNotIn(pictures[0], active)
        self.assertIn(pictures[3], active)
        prompt = next(
            node["inputs"]["value"]
            for node in compiled.values()
            if node.get("class_type") == "PrimitiveStringMultiline"
        )
        self.assertIn("Generate only the timeline interval from 15.00s to 23.00s", prompt)
        self.assertIn("[Shot 1 | 00:01.000-00:07.000]", prompt)
        self.assertIn("<Picture 1>", prompt)
        self.assertNotIn("Opening action", prompt)
        self.assertNotIn("00:16.000", prompt)
        window.project_dirty = False
        window.close()

    def test_end_to_end_smart_job_keeps_segment_mapping_and_upload_loaders_aligned(self):
        image = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "sample.png"
        video = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "sample.mp4"
        audio = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "sample.wav"
        if not all(path.is_file() for path in (image, video, audio)):
            self.skipTest("runtime smoke media is not present")
        window = DirectorCutStudio()
        window._set_design_duration(30.0)
        pictures = [asset for asset in window.scan.assets if asset.media_type == "image"]
        videos = [asset for asset in window.scan.assets if asset.media_type == "video"]
        audios = [asset for asset in window.scan.assets if asset.media_type == "audio"]
        rows = (
            (pictures[3], image, "V1", 0.0, 15.0, "Opening identity @P4."),
            (pictures[6], image, "V1", 15.0, 30.0, "Later environment @P7."),
            (videos[1], video, "V2", 15.0, 30.0, "Follow @V2 motion."),
            (audios[2], audio, "A2", 15.0, 30.0, "Use @A3 exactly."),
        )
        for asset, local, track_id, start, end, clip_prompt in rows:
            assign_local_media(window.scan, asset, local)
            asset.timeline_placed = True
            asset.timeline_track_id = track_id
            asset.start_seconds, asset.end_seconds = start, end
            asset.clip_prompt = clip_prompt
        window.prompt_panel.brief.setPlainText(
            "Use @P4 in the opening, then @P7, @V2 and @A3 in the second half."
        )
        window.clip_start.setValue(0.0)
        window.clip_end.setValue(30.0)

        job_path, count = window._build_smart_render_job(
            request_kind="preview",
            megapixels=0.2,
            seed=789,
            enable_rtx_vsr=False,
        )
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(count, 2)
        self.assertTrue(job["media"])
        self.assertTrue(all(isinstance(row, dict) for row in job["media"]))
        self.assertEqual(
            len({row["upload_name"] for row in job["media"]}), len(job["media"])
        )

        first, second = job["segments"]
        first_prompt = next(
            node["inputs"]["value"]
            for node in first["workflow"].values()
            if node.get("class_type") == "PrimitiveStringMultiline"
        )
        second_prompt = next(
            node["inputs"]["value"]
            for node in second["workflow"].values()
            if node.get("class_type") == "PrimitiveStringMultiline"
        )
        self.assertIn("<Picture 1>", first_prompt)
        self.assertNotIn("<Picture 2>", first_prompt)
        self.assertIn("<Picture 1>", second_prompt)
        self.assertIn("<Video 2> contains exactly the preceding segment", second_prompt)
        self.assertIn("<Video 1>", second_prompt)
        self.assertIn("<Audio 1> is the enabled synchronized soundtrack", second_prompt)
        self.assertIn("<Audio 2>", second_prompt)
        self.assertNotIn("@P", first_prompt + second_prompt)
        self.assertNotIn("@V", first_prompt + second_prompt)
        self.assertNotIn("@A", first_prompt + second_prompt)
        uploads_by_node = {
            row["loader_node_id"]: row for row in job["media"]
        }
        # Every loader retained by a Segment must be backed by the current
        # local upload. Inactive loaders are removed completely so an old
        # computer's image/audio/video filename cannot be validated by ComfyUI.
        for segment in job["segments"]:
            continuity_loader = str(
                (segment.get("continuity") or {}).get("loader_node_id", "")
            )
            for node_id, node in segment["workflow"].items():
                loader = MEDIA_LOADERS.get(str(node.get("class_type", "")))
                if loader is None or node_id == continuity_loader:
                    continue
                upload = uploads_by_node[node_id]
                self.assertEqual(
                    node["inputs"][upload["loader_input"]],
                    upload["upload_name"],
                )
        window.project_dirty = False
        window.close()

    def test_mapping_matrix_single_native_window_1_to_15(self):
        window = DirectorCutStudio()
        window._set_design_duration(30.0)
        picture = [a for a in window.scan.assets if a.media_type == "image"][3]
        self._place(picture, 1.0, 15.0, "V1", "Use @P4 as the only subject reference.")
        window.clip_start.setValue(1.0)
        window.clip_end.setValue(15.0)

        workflow, active = window._compiled_job(
            megapixels=0.2, seed=101, enable_rtx_vsr=False
        )
        prompt = self._workflow_prompt(workflow)
        h3 = self._h3_inputs(window, workflow)
        self.assertEqual(active, [picture])
        self.assertIn("<Picture 1>", prompt)
        self.assertNotIn("<Picture 2>", prompt)
        physical = [a for a in window.scan.assets if a.media_type == "image"][0]
        self.assertEqual(h3["ref_images.ref_image_0"], [physical.node_id, 0])
        self.assertNotIn("ref_images.ref_image_1", h3)
        window.project_dirty = False
        window.close()

    def test_mapping_matrix_partial_14_to_20_crosses_reference_boundary(self):
        window = DirectorCutStudio()
        window._set_design_duration(30.0)
        pictures = [a for a in window.scan.assets if a.media_type == "image"]
        first = self._place(pictures[3], 10.0, 16.0, "V1", "Opening uses @P4.")
        second = self._place(pictures[6], 16.0, 24.0, "V2", "Continuation uses @P7.")
        window.director_cues = [
            DirectorCue("S1", "shot", 14.0, 16.0, "First half", track_id="V1"),
            DirectorCue("S2", "shot", 16.0, 20.0, "Second half", track_id="V2"),
        ]
        window.clip_start.setValue(14.0)
        window.clip_end.setValue(20.0)

        workflow, active = window._compiled_job(
            megapixels=0.2, seed=102, enable_rtx_vsr=False
        )
        prompt = self._workflow_prompt(workflow)
        h3 = self._h3_inputs(window, workflow)
        self.assertEqual(active, [first, second])
        self.assertIn("[Shot 1 | 00:00.000-00:02.000]", prompt)
        self.assertIn("[Shot 2 | 00:02.000-00:06.000]", prompt)
        self.assertIn("<Picture 1>", prompt)
        self.assertIn("<Picture 2>", prompt)
        self.assertEqual(h3["ref_images.ref_image_0"], [pictures[0].node_id, 0])
        self.assertEqual(h3["ref_images.ref_image_1"], [pictures[1].node_id, 0])
        window.project_dirty = False
        window.close()

    def test_mapping_matrix_long_1_to_30_builds_two_local_jobs(self):
        window = DirectorCutStudio()
        window._set_design_duration(31.0)
        pictures = [a for a in window.scan.assets if a.media_type == "image"]
        first = self._place(pictures[3], 1.0, 16.0, "V1", "First half uses @P4.")
        second = self._place(pictures[6], 16.0, 30.0, "V2", "Second half uses @P7.")
        window.clip_start.setValue(1.0)
        window.clip_end.setValue(30.0)

        job_path, count = window._build_smart_render_job(
            request_kind="preview", megapixels=0.2, seed=103,
            enable_rtx_vsr=False,
        )
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(count, 2)
        self.assertEqual(job["target_duration_seconds"], 29.0)
        self.assertEqual(
            [(s["start_seconds"], s["end_seconds"]) for s in job["segments"]],
            [(1.0, 16.0), (16.0, 30.0)],
        )
        first_job, second_job = job["segments"]
        self.assertIn("<Picture 1>", self._workflow_prompt(first_job["workflow"]))
        self.assertIn("First half", self._workflow_prompt(first_job["workflow"]))
        self.assertNotIn("Second half", self._workflow_prompt(first_job["workflow"]))
        self.assertIn("<Picture 1>", self._workflow_prompt(second_job["workflow"]))
        self.assertIn("Second half", self._workflow_prompt(second_job["workflow"]))
        self.assertNotIn("First half", self._workflow_prompt(second_job["workflow"]))
        self.assertEqual(
            self._h3_inputs(window, first_job["workflow"])["ref_images.ref_image_0"],
            [pictures[0].node_id, 0],
        )
        self.assertEqual(
            self._h3_inputs(window, second_job["workflow"])["ref_images.ref_image_0"],
            [pictures[0].node_id, 0],
        )
        window.project_dirty = False
        window.close()

    def test_mapping_matrix_long_context_reserves_video_1_without_renumbering_media(self):
        window = DirectorCutStudio()
        window._set_design_duration(30.0)
        videos = [a for a in window.scan.assets if a.media_type == "video"]
        video = self._place(videos[1], 15.0, 30.0, "V2", "Follow @V2 motion.")
        window.clip_start.setValue(0.0)
        window.clip_end.setValue(30.0)

        job_path, _ = window._build_smart_render_job(
            request_kind="preview", megapixels=0.2, seed=104,
            enable_rtx_vsr=False,
        )
        second = json.loads(job_path.read_text(encoding="utf-8"))["segments"][1]
        prompt = self._workflow_prompt(second["workflow"])
        h3 = self._h3_inputs(window, second["workflow"])
        self.assertEqual(second["continuity"]["kind"], "video")
        self.assertEqual(second["continuity"]["frame_count"], 24)
        self.assertEqual(second["continuity"]["tag"], "<Video 2>")
        self.assertEqual(second["continuity"]["binding"], "ref_videos.ref_video_1")
        self.assertIn("<Video 2> contains exactly the preceding segment", prompt)
        self.assertIn("<Video 1>", prompt)
        self.assertIn("ref_videos.ref_video_0", h3)
        self.assertNotIn("ref_videos.ref_video_1", h3)
        self.assertEqual(
            h3["ref_videos.ref_video_0"],
            window.scan.nodes[window.scan.h3_node_ids[0]]["inputs"][videos[0].binding],
        )
        window.project_dirty = False
        window.close()

    def test_mapping_regression_third_segment_compacts_p5_to_picture_4(self):
        """Reproduce the sparse P1/P2/P3/P5 layout from One Leaf Kill."""
        window = DirectorCutStudio()
        window._set_design_duration(45.0)
        pictures = [a for a in window.scan.assets if a.media_type == "image"]
        for asset in window.scan.assets:
            asset.timeline_placed = False
        for index, asset in enumerate(pictures[:3], 1):
            self._place(asset, 0.0, 45.0, f"V{index}", f"Global identity @P{index}.")
        water = self._place(
            pictures[4], 35.0, 40.0, "V4",
            "Use @P5 only as the single water-step action reference.",
        )
        water.recognition = "AI DESIGN GENERATED REFERENCE\nUsage: h3_reference"
        window.director_cues = [
            DirectorCue("S1", "shot", 0.0, 15.0, "Opening", track_id="V1"),
            DirectorCue(
                "S2", "shot", 15.0, 30.0, "Roof pursuit",
                detail="Final frame: both fighters remain airborne and rising.",
                track_id="V1",
            ),
            DirectorCue("S3", "shot", 30.0, 45.0, "Finish", track_id="V1"),
        ]
        window.clip_start.setValue(0.0)
        window.clip_end.setValue(45.0)

        job_path, count = window._build_smart_render_job(
            request_kind="preview", megapixels=0.2, seed=111,
            enable_rtx_vsr=False,
        )
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(count, 3)
        third = job["segments"][2]
        prompt = self._workflow_prompt(third["workflow"])
        h3 = self._h3_inputs(window, third["workflow"])

        self.assertIn("<Picture 4>", prompt)
        self.assertIn("single water-step", prompt)
        self.assertEqual(h3["ref_images.ref_image_3"], [pictures[3].node_id, 0])
        self.assertNotIn("ref_images.ref_image_4", h3)
        self.assertEqual(third["continuity"]["tag"], "<Video 1>")
        self.assertEqual(
            third["continuity"]["binding"], "ref_videos.ref_video_0"
        )
        self.assertIn("<Video 1> contains exactly the preceding segment", prompt)
        self.assertNotIn("No previous rendered frame is supplied", prompt)
        window.project_dirty = False
        window.close()

    def test_boundary_state_keeps_pose_positions_and_camera_not_generic_label(self):
        cue = DirectorCue(
            "S6", "shot", 25.0, 30.0, "Airborne boundary",
            subject_action=(
                "The Assassin kicks off the wall. Both characters are now "
                "airborne, rising vertically above the courtyard."
            ),
            environment_response="Red leaves swirl upward from their leap.",
            detail=(
                "At 30.0s, both characters must be clearly separated in the sky: "
                "Assassin upper-left, General lower-right. The camera is pointing "
                "at the sky. This is the boundary for Part 3."
            ),
            track_id="V1",
        )
        state = DirectorCutStudio._terminal_state_from_shot(cue)
        self.assertIn("airborne, rising vertically", state)
        self.assertIn("Assassin upper-left, General lower-right", state)
        self.assertIn("camera is pointing at the sky", state)
        self.assertNotIn("boundary for Part 3", state)

    def test_mapping_matrix_edit_each_segment_changes_only_its_fingerprint(self):
        window = DirectorCutStudio()
        window._set_design_duration(45.0)
        pictures = [a for a in window.scan.assets if a.media_type == "image"]
        placed = [
            self._place(pictures[0], 0.0, 15.0, "V1", "Segment one @P1."),
            self._place(pictures[3], 15.0, 30.0, "V1", "Segment two @P4."),
            self._place(pictures[6], 30.0, 45.0, "V1", "Segment three @P7."),
        ]
        windows = [(0.0, 15.0), (15.0, 30.0), (30.0, 45.0)]

        def fingerprints():
            return [
                window._compiled_window_job(
                    start, end, megapixels=0.2, seed=105,
                    enable_rtx_vsr=False, is_final_window=index == 2,
                    continuity_mode="none",
                )[3]
                for index, (start, end) in enumerate(windows)
            ]

        baseline = fingerprints()
        for changed_index, asset in enumerate(placed):
            original = asset.clip_prompt
            asset.clip_prompt = original + " Edited locally."
            changed = fingerprints()
            self.assertEqual(
                [index for index, pair in enumerate(zip(baseline, changed)) if pair[0] != pair[1]],
                [changed_index],
            )
            asset.clip_prompt = original
        window.project_dirty = False
        window.close()

    def test_mapping_matrix_edit_packed_small_segment_stays_local(self):
        window = DirectorCutStudio()
        window._set_design_duration(30.0)
        window.director_cues = [
            DirectorCue("S1", "shot", 0.0, 10.0, "Part one", track_id="V1"),
            DirectorCue("S2", "shot", 10.0, 20.0, "Part two", track_id="V1"),
            DirectorCue("S3", "shot", 20.0, 30.0, "Part three", track_id="V1"),
        ]
        pictures = [a for a in window.scan.assets if a.media_type == "image"]
        self._place(pictures[0], 0.0, 10.0, "V1", "Small segment @P1.")
        middle = self._place(pictures[3], 10.0, 20.0, "V1", "Small segment @P4.")
        self._place(pictures[6], 20.0, 30.0, "V1", "Small segment @P7.")
        window.clip_start.setValue(0.0)
        window.clip_end.setValue(30.0)
        first_path, _ = window._build_smart_render_job(
            request_kind="preview", megapixels=0.2, seed=106,
            enable_rtx_vsr=False,
        )
        first = json.loads(first_path.read_text(encoding="utf-8"))
        self.assertEqual(
            [(s["start_seconds"], s["end_seconds"]) for s in first["segments"]],
            [(0.0, 10.0), (10.0, 20.0), (20.0, 30.0)],
        )
        middle.clip_prompt += " Changed only here."
        second_path, _ = window._build_smart_render_job(
            request_kind="preview", megapixels=0.2, seed=106,
            enable_rtx_vsr=False,
        )
        second = json.loads(second_path.read_text(encoding="utf-8"))
        changed = [
            index for index, (before, after) in enumerate(zip(first["segments"], second["segments"]))
            if before["fingerprint"] != after["fingerprint"]
        ]
        self.assertEqual(changed, [1])
        for index, segment in enumerate(second["segments"]):
            h3 = self._h3_inputs(window, segment["workflow"])
            self.assertEqual(
                len([key for key in h3 if key.startswith("ref_images.ref_image_")]),
                1,
            )
            self.assertIn("<Picture 1>", self._workflow_prompt(segment["workflow"]))
        window.project_dirty = False
        window.close()

    def test_mapping_matrix_delete_then_readd_preserves_stable_source_identity(self):
        window = DirectorCutStudio()
        window._set_design_duration(15.0)
        picture = [a for a in window.scan.assets if a.media_type == "image"][3]
        self._place(picture, 2.0, 8.0, "V1", "Use @P4.")

        before, active_before = window._compiled_window_job(
            0.0, 15.0, megapixels=0.2, seed=107, enable_rtx_vsr=False,
            is_final_window=True, continuity_mode="none",
        )[:2]
        picture.timeline_placed = False
        deleted, active_deleted = window._compiled_window_job(
            0.0, 15.0, megapixels=0.2, seed=107, enable_rtx_vsr=False,
            is_final_window=True, continuity_mode="none",
        )[:2]
        self._place(picture, 9.0, 14.0, "V2", "Reuse @P4 later.")
        readded, active_readded = window._compiled_window_job(
            0.0, 15.0, megapixels=0.2, seed=107, enable_rtx_vsr=False,
            is_final_window=True, continuity_mode="none",
        )[:2]

        self.assertEqual(active_before, [picture])
        self.assertEqual(active_deleted, [])
        self.assertEqual(active_readded, [picture])
        physical = [a for a in window.scan.assets if a.media_type == "image"][0]
        self.assertEqual(
            self._h3_inputs(window, before)["ref_images.ref_image_0"],
            [physical.node_id, 0],
        )
        self.assertNotIn("ref_images.ref_image_0", self._h3_inputs(window, deleted))
        self.assertEqual(
            self._h3_inputs(window, readded)["ref_images.ref_image_0"],
            [physical.node_id, 0],
        )
        self.assertIn("<Picture 1>", self._workflow_prompt(readded))
        window.project_dirty = False
        window.close()

    def test_mapping_matrix_move_between_segments_dirties_old_and_new_windows(self):
        window = DirectorCutStudio()
        window._set_design_duration(30.0)
        picture = [a for a in window.scan.assets if a.media_type == "image"][3]
        self._place(picture, 2.0, 8.0, "V1", "Move @P4.")
        window.clip_start.setValue(0.0)
        window.clip_end.setValue(30.0)
        before_state = timeline_state(picture)
        early_before = window._compiled_window_job(
            0.0, 15.0, megapixels=0.2, seed=108, enable_rtx_vsr=False,
            is_final_window=False, continuity_mode="none",
        )[1]
        picture.start_seconds, picture.end_seconds = 22.0, 28.0
        after_state = timeline_state(picture)
        window._mark_render_states_dirty(before_state, after_state)
        early_after = window._compiled_window_job(
            0.0, 15.0, megapixels=0.2, seed=108, enable_rtx_vsr=False,
            is_final_window=False, continuity_mode="none",
        )[1]
        late_after = window._compiled_window_job(
            15.0, 30.0, megapixels=0.2, seed=108, enable_rtx_vsr=False,
            is_final_window=True, continuity_mode="none",
        )[1]

        self.assertEqual(early_before, [picture])
        self.assertEqual(early_after, [])
        self.assertEqual(late_after, [picture])
        self.assertEqual(
            window.render_dirty_segment_ids,
            {segment.segment_id for segment in window._planned_render_segments()},
        )
        window.project_dirty = False
        window.close()

    def test_mapping_matrix_move_between_visible_tracks_keeps_binding(self):
        window = DirectorCutStudio()
        window._set_design_duration(15.0)
        picture = [a for a in window.scan.assets if a.media_type == "image"][3]
        self._place(picture, 0.0, 15.0, "V1", "Track move @P4.")
        first, first_assets, _, first_fingerprint = window._compiled_window_job(
            0.0, 15.0, megapixels=0.2, seed=109, enable_rtx_vsr=False,
            is_final_window=True, continuity_mode="none",
        )
        picture.timeline_track_id = "V2"
        second, second_assets, _, second_fingerprint = window._compiled_window_job(
            0.0, 15.0, megapixels=0.2, seed=109, enable_rtx_vsr=False,
            is_final_window=True, continuity_mode="none",
        )
        next(track for track in window.tracks if track.track_id == "V2").visible = False
        hidden, hidden_assets = window._compiled_window_job(
            0.0, 15.0, megapixels=0.2, seed=109, enable_rtx_vsr=False,
            is_final_window=True, continuity_mode="none",
        )[:2]

        self.assertEqual(first_assets, [picture])
        self.assertEqual(second_assets, [picture])
        self.assertEqual(first_fingerprint, second_fingerprint)
        self.assertEqual(
            self._h3_inputs(window, first)["ref_images.ref_image_0"],
            self._h3_inputs(window, second)["ref_images.ref_image_0"],
        )
        self.assertEqual(hidden_assets, [])
        self.assertNotIn("ref_images.ref_image_0", self._h3_inputs(window, hidden))
        window.project_dirty = False
        window.close()

    def test_mapping_matrix_repeated_source_on_same_track_maps_once_per_window(self):
        window = DirectorCutStudio()
        window._set_design_duration(30.0)
        picture = [a for a in window.scan.assets if a.media_type == "image"][3]
        self._place(picture, 1.0, 4.0, "V1", "Opening occurrence @P4.")
        repeat = deepcopy(picture)
        repeat.clip_id = "repeat-p4-25s"
        repeat.source_node_id = picture.node_id
        repeat.start_seconds, repeat.end_seconds = 25.0, 30.0
        repeat.clip_prompt = "Closing occurrence @P4."
        window.scan.timeline_clips.append(repeat)
        window.clip_start.setValue(0.0)
        window.clip_end.setValue(30.0)

        job_path, count = window._build_smart_render_job(
            request_kind="preview", megapixels=0.2, seed=110,
            enable_rtx_vsr=False,
        )
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(count, 2)
        first, second = job["segments"]
        for segment in (first, second):
            prompt = self._workflow_prompt(segment["workflow"])
            h3 = self._h3_inputs(window, segment["workflow"])
            self.assertIn("<Picture 1>", prompt)
            self.assertEqual(
                [key for key in h3 if key.startswith("ref_images.ref_image_")],
                ["ref_images.ref_image_0"],
            )
            physical = [a for a in window.scan.assets if a.media_type == "image"][0]
            self.assertEqual(h3["ref_images.ref_image_0"], [physical.node_id, 0])
        self.assertIn("Opening occurrence", self._workflow_prompt(first["workflow"]))
        self.assertNotIn("Closing occurrence", self._workflow_prompt(first["workflow"]))
        self.assertIn("Closing occurrence", self._workflow_prompt(second["workflow"]))
        self.assertNotIn("Opening occurrence", self._workflow_prompt(second["workflow"]))
        window.project_dirty = False
        window.close()

    def test_smart_long_render_builds_hidden_local_time_jobs(self):
        window = DirectorCutStudio()
        window._set_design_duration(60.0)
        for asset in [
            item for item in window.scan.assets if item.media_type == "image"
        ][:5]:
            asset.timeline_placed = True
            asset.start_seconds = 0.0
            asset.end_seconds = 60.0
        window.clip_start.setValue(0.0)
        window.clip_end.setValue(60.0)
        window.director_cues = [
            DirectorCue(
                "S1", "shot", 0.0, 5.0, "Opening",
                detail="Final frame: the hero remains airborne with forward momentum.",
                track_id="V1",
            ),
            DirectorCue("S2", "shot", 16.0, 22.0, "Reveal", track_id="V1"),
            DirectorCue("M1", "marker", 59.0, 59.0, "Final Hold", detail="Hold", track_id="V1"),
        ]
        window.prompt_panel.brief.setPlainText(
            "GLOBAL WHOLE-STORY BRIEF THAT MUST NOT LEAK INTO EVERY SEGMENT"
        )
        window.prompt_panel.transition.setPlainText(
            "GLOBAL WHOLE-TIMELINE TRANSITIONS THAT MUST STAY OUT OF LOCAL JOBS"
        )
        job_path, count = window._build_smart_render_job(
            request_kind="preview",
            megapixels=0.2,
            seed=123456,
            enable_rtx_vsr=False,
        )
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(count, 4)
        self.assertEqual(
            [(row["start_seconds"], row["end_seconds"]) for row in job["segments"]],
            [(0.0, 15.0), (15.0, 30.0), (30.0, 45.0), (45.0, 60.0)],
        )
        second_prompt = next(
            node["inputs"]["value"]
            for node in job["segments"][1]["workflow"].values()
            if node.get("class_type") == "PrimitiveStringMultiline"
        )
        self.assertIn("[Shot 1 | 00:01.000-00:07.000]", second_prompt)
        self.assertNotIn("Opening", second_prompt)
        self.assertNotIn("GLOBAL WHOLE-STORY", second_prompt)
        self.assertNotIn("GLOBAL WHOLE-TIMELINE", second_prompt)
        self.assertIn("Generate only the timeline interval", second_prompt)
        self.assertIn("clean continuity handoff", second_prompt)
        self.assertIn("final 24 motion-only frames", second_prompt)
        self.assertIn("Do not replay", second_prompt)
        self.assertIn("Timeline checkpoint", second_prompt)
        self.assertIn("already completed off-screen", second_prompt)
        self.assertNotIn("final-state continuity still", second_prompt)
        self.assertNotIn("<Picture 9>", second_prompt)
        self.assertEqual(job["segments"][1]["continuity"]["kind"], "video")
        self.assertEqual(job["segments"][1]["continuity"]["frame_count"], 24)
        self.assertEqual(job["segments"][1]["continuity"]["fps"], 24)
        self.assertEqual(job["segments"][-1]["overlap_before_seconds"], 0.0)
        self.assertEqual(job["render_policy_version"], 11)
        window.project_dirty = False
        window.close()

    def test_ai_action_reference_is_owned_by_only_its_start_segment(self):
        window = DirectorCutStudio()
        window._set_design_duration(45.0)
        images = [asset for asset in window.scan.assets if asset.media_type == "image"]
        for asset in window.scan.assets:
            asset.timeline_placed = False
        global_reference, action_reference = images[:2]
        for asset in (global_reference, action_reference):
            asset.timeline_placed = True
            asset.timeline_track_id = "V1"
            asset.recognition = "AI DESIGN GENERATED REFERENCE\nUsage: h3_reference"
            asset.activation_mode = "auto"
        global_reference.start_seconds = 0.0
        global_reference.end_seconds = 45.0
        global_reference.clip_prompt = "Courtyard identity reference."
        action_reference.start_seconds = 10.0
        action_reference.end_seconds = 20.0
        action_reference.clip_prompt = "Assassin final action state."
        window.director_cues = [
            DirectorCue("S1", "shot", 0.0, 15.0, "Opening", track_id="V1"),
            DirectorCue("S2", "shot", 15.0, 30.0, "Continuation", track_id="V1"),
            DirectorCue("S3", "shot", 30.0, 45.0, "Finish", track_id="V1"),
        ]
        job_path, _ = window._build_smart_render_job(
            request_kind="preview", megapixels=0.2, seed=2468,
            enable_rtx_vsr=False,
        )
        job = json.loads(job_path.read_text(encoding="utf-8"))

        def active_image_names(segment):
            workflow = segment["workflow"]
            h3 = next(
                row for row in workflow.values()
                if row.get("class_type") == "MiniMaxH3ReferenceToVideo"
            )
            names = []
            for key, connection in h3["inputs"].items():
                if not key.startswith("ref_images."):
                    continue
                names.append(workflow[str(connection[0])]["inputs"]["image"])
            return names

        first_names = active_image_names(job["segments"][0])
        second_names = active_image_names(job["segments"][1])
        third_names = active_image_names(job["segments"][2])
        self.assertIn(action_reference.filename, first_names)
        self.assertNotIn(action_reference.filename, second_names)
        self.assertNotIn(action_reference.filename, third_names)
        self.assertTrue(all(global_reference.filename in names for names in (
            first_names, second_names, third_names,
        )))
        self.assertEqual(job["segments"][1]["continuity"]["frame_count"], 24)
        self.assertEqual(job["segments"][2]["continuity"]["frame_count"], 24)
        window.project_dirty = False
        window.close()

    def test_hard_cut_boundary_does_not_attach_previous_segment(self):
        window = DirectorCutStudio()
        window._set_design_duration(30.0)
        window.director_cues = [
            DirectorCue("S1", "shot", 0.0, 15.0, "Opening", track_id="V1"),
            DirectorCue(
                "S2", "shot", 15.0, 30.0, "Reveal", track_id="V1",
                continuity_mode="Hard Cut",
            ),
        ]
        job_path, _ = window._build_smart_render_job(
            request_kind="preview", megapixels=0.2, seed=5678,
            enable_rtx_vsr=False,
        )
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(job["segments"][1]["continuity_mode"], "hard_cut")
        self.assertEqual(job["segments"][1]["continuity"], {})
        window.project_dirty = False
        window.close()

    def test_motion_context_reserves_one_auto_video_slot_but_not_force_active(self):
        window = DirectorCutStudio()
        window._set_design_duration(30.0)
        videos = [asset for asset in window.scan.assets if asset.media_type == "video"]
        self.assertEqual(len(videos), 3)
        for asset in window.scan.assets:
            asset.timeline_placed = False
        for index, asset in enumerate(videos, 1):
            asset.timeline_placed = True
            asset.timeline_track_id = f"V{index}"
            asset.start_seconds = 0.0
            asset.end_seconds = 30.0
            asset.activation_mode = "auto"
        window.director_cues = [
            DirectorCue("S1", "shot", 0.0, 15.0, "Opening", track_id="V1"),
            DirectorCue("S2", "shot", 15.0, 30.0, "Continue", track_id="V1"),
        ]

        job_path, _ = window._build_smart_render_job(
            request_kind="preview", megapixels=0.2, seed=97531,
            enable_rtx_vsr=False,
        )
        second = json.loads(job_path.read_text(encoding="utf-8"))["segments"][1]
        self.assertEqual(second["continuity"]["frame_count"], 24)
        self.assertTrue(second["continuity"].get("reserved_from_media", "").startswith("V"))
        h3 = next(
            node for node in second["workflow"].values()
            if node.get("class_type") == "MiniMaxH3ReferenceToVideo"
        )
        active_video_inputs = [
            key for key in h3["inputs"] if key.startswith("ref_videos.ref_video_")
        ]
        self.assertEqual(len(active_video_inputs), 2)

        for asset in videos:
            asset.activation_mode = "active"
        forced_path, _ = window._build_smart_render_job(
            request_kind="preview", megapixels=0.2, seed=97531,
            enable_rtx_vsr=False,
        )
        forced_second = json.loads(
            forced_path.read_text(encoding="utf-8")
        )["segments"][1]
        self.assertEqual(forced_second["continuity"], {})
        window.project_dirty = False
        window.close()

    def test_local_shot_edit_keeps_unrelated_segment_fingerprint_stable(self):
        window = DirectorCutStudio()
        window._set_design_duration(45.0)
        window.director_cues = [
            DirectorCue("S1", "shot", 0.0, 5.0, "Opening", track_id="V1"),
            DirectorCue("S2", "shot", 16.0, 22.0, "Reveal", track_id="V1"),
        ]
        window._sync_prompt_panel_from_timeline(force=True)
        first_path, _ = window._build_smart_render_job(
            request_kind="preview",
            megapixels=0.2,
            seed=24680,
            enable_rtx_vsr=False,
        )
        first = json.loads(first_path.read_text(encoding="utf-8"))
        window.director_cues[1].preset = "Fast low-angle attack"
        window._sync_prompt_panel_from_timeline(force=True)
        second_path, _ = window._build_smart_render_job(
            request_kind="preview",
            megapixels=0.2,
            seed=24680,
            enable_rtx_vsr=False,
        )
        second = json.loads(second_path.read_text(encoding="utf-8"))
        self.assertEqual(
            first["segments"][0]["fingerprint"],
            second["segments"][0]["fingerprint"],
        )
        self.assertNotEqual(
            first["segments"][1]["fingerprint"],
            second["segments"][1]["fingerprint"],
        )
        window.project_dirty = False
        window.close()

    def test_dense_shot_timeline_packs_micro_shots_into_native_windows(self):
        window = DirectorCutStudio()
        window._set_design_duration(45.0)
        demo = json.loads(
            (PROJECT_ROOT / "example" / "tang_ting_ci_ying_45s_demo" / "design_plan.json").read_text(
                encoding="utf-8"
            )
        )
        window.director_cues = [
            DirectorCue(
                f"S{index}",
                "shot",
                float(row["start_seconds"]),
                float(row["end_seconds"]),
                str(row["preset"]),
                track_id="V1",
            )
            for index, row in enumerate(demo["shots"], 1)
        ]
        planned = window._planned_render_segments()
        self.assertEqual(len(planned), 3)
        self.assertEqual(
            (planned[1].core_start_seconds, planned[1].core_end_seconds),
            (15.0, 30.0),
        )
        self.assertEqual(planned[0].shot_ids, [f"S{index}" for index in range(1, 8)])
        self.assertEqual(max(row.duration_seconds for row in planned), 15.0)
        window.project_dirty = False
        window.close()

    def test_one_second_shot_edit_reuses_all_other_shot_units(self):
        window = DirectorCutStudio()
        window._set_design_duration(45.0)
        demo = json.loads(
            (PROJECT_ROOT / "example" / "tang_ting_ci_ying_45s_demo" / "design_plan.json").read_text(
                encoding="utf-8"
            )
        )
        window.director_cues = [
            DirectorCue(
                f"S{index}", "shot", float(row["start_seconds"]),
                float(row["end_seconds"]), str(row["preset"]), track_id="V1",
            )
            for index, row in enumerate(demo["shots"], 1)
        ]
        window._sync_prompt_panel_from_timeline(force=True)
        first_path, _ = window._build_smart_render_job(
            request_kind="final", megapixels=1.0, seed=13579,
            enable_rtx_vsr=False,
        )
        first = json.loads(first_path.read_text(encoding="utf-8"))
        folder = PROJECT_ROOT / ".director_cache" / "shot_reuse_test"
        folder.mkdir(parents=True, exist_ok=True)
        cached_rows = []
        for row in first["segments"]:
            output = folder / f"{row['segment_id']}.mp4"
            output.write_bytes(b"cached")
            cached_rows.append(
                {
                    **{key: value for key, value in row.items() if key != "workflow"},
                    "status": "complete",
                    "output_path": str(output),
                }
            )
        window.smart_render_manifests["production"] = {
            "render_policy_version": 11,
            "segments": cached_rows,
        }
        changed = next(cue for cue in window.director_cues if cue.start_seconds == 8.0)
        changed.preset += " · revised eye reaction"
        window._sync_prompt_panel_from_timeline(force=True)
        window._mark_render_range_dirty(8.0, 9.0)
        second_path, _ = window._build_smart_render_job(
            request_kind="final", megapixels=1.0, seed=13579,
            enable_rtx_vsr=False,
        )
        second = json.loads(second_path.read_text(encoding="utf-8"))
        pending = [row for row in second["segments"] if row.get("status") != "cached"]
        self.assertEqual(len(pending), 1)
        self.assertEqual(
            (pending[0]["core_start_seconds"], pending[0]["core_end_seconds"]),
            (0.0, 15.0),
        )
        self.assertEqual(len(second["segments"]) - len(pending), 2)
        for output in folder.glob("*.mp4"):
            output.unlink(missing_ok=True)
        folder.rmdir()
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
            continuity_state="Keep the bag in her right hand and finish facing screen-right.",
            optional_flourish="Loose hair catches one soft highlight.",
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
        self.assertIn("Core action (must complete)", window.prompt_panel.shots.toPlainText())
        self.assertIn("State to preserve", window.prompt_panel.shots.toPlainText())
        self.assertIn("Optional (omit before delaying core)", window.prompt_panel.shots.toPlainText())
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
            self.assertIs(
                window.generated_monitor_stack.currentWidget(),
                window.generated_video_widget,
            )
            self.assertIs(
                window.monitor_display_stack.currentWidget(),
                window.monitor_compare_splitter,
            )
            final_monitor = window.monitor_display_stack.currentWidget()
            window.generation_previous_monitor = final_monitor
            window.generation_overlay.start("ComfyUI running · sampling")
            self.assertIs(window.monitor_display_stack.currentWidget(), final_monitor)
            self.assertFalse(window.generation_overlay.isHidden())
            window.generation_overlay.set_message("Rendering frames 50%")
            self.assertEqual(window.generation_overlay.message, "Rendering frames 50%")
            window.render_timeline_at(0.0, force_seek=True)
            self.assertIs(window.monitor_display_stack.currentWidget(), final_monitor)
            self.assertFalse(window.generation_overlay.isHidden())
            window.generation_overlay.stop()
            window._restore_monitor_after_generation()
            self.assertIs(window.monitor_display_stack.currentWidget(), final_monitor)
            window.new_project(confirm=False)
            self.assertFalse(window.generated_output_locked)
            self.assertIsNone(window.generated_output_path)
            self.assertFalse(window.export_generated_button.isEnabled())
        window.project_dirty = False
        window.close()

    def test_generated_master_drives_timeline_and_archived_project_restores_compare_view(self):
        video = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "sample.mp4"
        if not video.exists():
            self.skipTest("runtime smoke video is not present")
        archive = PROJECT_ROOT / ".director_cache" / "generated_project_restore_test"
        archive.mkdir(parents=True, exist_ok=True)
        preview = archive / "save_image_preview.png"
        QImage(32, 18, QImage.Format_RGB32).save(str(preview))
        window = DirectorCutStudio()
        window.example_work_dir = archive
        outputs = window._archive_generated_outputs(
            [
                {"kind": "images", "local_path": str(preview)},
                {"kind": "videos", "local_path": str(video)},
            ],
            "final",
        )
        self.assertTrue(window._show_generated_output(outputs, autoplay=False))
        self.assertEqual(window.generated_output_path, (archive / "generated_output.mp4").resolve())
        window._generated_position_changed(750)
        self.assertAlmostEqual(window.playhead_seconds, 0.75, places=2)
        self.assertEqual(window.position_slider.value(), 750)
        self.assertAlmostEqual(window.timeline.playhead_seconds, 0.75, places=2)
        window.smart_render_manifest = {
            "format": "h3-smart-render-manifest",
            "segments": [{"segment_id": "shot_test", "status": "complete"}],
        }
        project = window._auto_save_example_project()
        self.assertIsNotNone(project)
        self.assertTrue((archive / "generated_output.mp4").is_file())
        self.assertTrue((archive / "render_manifest.json").is_file())
        self.assertTrue(project.is_file())
        payload = json.loads(project.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], PROJECT_FORMAT_VERSION)
        self.assertEqual(payload["generated_output_timeline_start"], 0.0)
        self.assertEqual(len(payload["monitor_compare_sizes"]), 2)
        # Simulate the user's portable version 12 example folder: its saved
        # output points into cache, while the usable master is beside the project.
        payload["version"] = 12
        payload["generated_output"] = str(archive / "missing_cache_master.mp4")
        payload.pop("generated_output_timeline_start", None)
        payload.pop("monitor_compare_sizes", None)
        payload.pop("example_work_dir", None)
        project.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        window.project_dirty = False
        window.close()

        restored = DirectorCutStudio()
        restored.load_project_path(project)
        self.assertEqual(
            restored.generated_output_path,
            (archive / "generated_output.mp4").resolve(),
        )
        self.assertEqual(restored.position_slider.value(), 750)
        self.assertEqual(restored.position_slider.maximum(), 12000)
        self.assertIs(
            restored.monitor_display_stack.currentWidget(),
            restored.monitor_compare_splitter,
        )
        self.assertFalse(restored.monitor_compare_splitter.childrenCollapsible())
        restored.resize(1400, 900)
        restored.show()
        self.app.processEvents()
        restored.monitor_compare_splitter.setSizes([1, 1000])
        self.app.processEvents()
        self.assertEqual(restored.monitor_compare_splitter.sizes()[0], 1)
        restored.monitor_compare_splitter.setSizes([1000, 1])
        self.app.processEvents()
        self.assertEqual(restored.monitor_compare_splitter.sizes()[1], 1)
        restored.monitor_compare_splitter.setSizes([500, 500])
        self.app.processEvents()
        left_size, right_size = restored.monitor_compare_splitter.sizes()
        self.assertLessEqual(abs(left_size - right_size), 1)
        self.assertIs(
            restored.generated_monitor_stack.currentWidget(),
            restored.generated_video_widget,
        )
        restored.project_dirty = False
        restored.close()

    def test_completed_shot_previews_under_translucent_running_overlay(self):
        video = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "sample.mp4"
        if not video.exists():
            self.skipTest("runtime smoke video is not present")
        window = DirectorCutStudio()
        window.generation_overlay.start("Rendering Shot")
        window._show_render_segment_preview(
            {
                "segment_id": "shot_006000_009000",
                "start_seconds": 5.0,
                "end_seconds": 9.0,
                "core_start_seconds": 6.0,
                "core_end_seconds": 9.0,
                "shot_ids": ["S3", "S4"],
                "output_path": str(video),
            }
        )
        self.app.processEvents()
        self.assertIs(
            window.monitor_display_stack.currentWidget(),
            window.monitor_compare_splitter,
        )
        self.assertEqual(window.monitor_display_stack.indexOf(window.generation_overlay), -1)
        self.assertFalse(window.generation_overlay.isHidden())
        self.assertEqual(
            window.generation_overlay.geometry(),
            window.monitor_display_stack.rect(),
        )
        self.assertTrue(window.generated_video_widget.inherits("QLabel"))
        self.assertFalse(window.generated_video_widget.inherits("QVideoWidget"))
        self.assertEqual(window.generated_playback_path, video.resolve())
        self.assertAlmostEqual(window.generated_output_timeline_start, 6.0)
        self.assertIn("S3, S4", window.generated_output_label.text())
        window.generation_overlay.stop()
        window.project_dirty = False
        window.close()

    def test_generation_overlay_accumulates_elapsed_and_weighted_shot_progress(self):
        window = DirectorCutStudio()
        overlay = window.generation_overlay
        overlay.start("Generating segment 1")
        started = overlay.started_monotonic
        overlay.set_message("Generating segment 2")
        self.assertEqual(overlay.started_monotonic, started)
        overlay.set_progress(
            completed_shots=2,
            total_shots=3,
            completed_weight_seconds=5.0,
            total_weight_seconds=15.0,
            active_shots=["S3"],
        )
        self.assertEqual(overlay.completed_shots, 2)
        self.assertEqual(overlay.total_shots, 3)
        self.assertEqual(overlay.active_shots, ["S3"])
        self.assertAlmostEqual(overlay.weighted_percent(), 100.0 / 3.0, places=4)
        self.assertGreaterEqual(overlay.elapsed_seconds(), 0.0)
        window._generation_message(
            {
                "render_progress": {
                    "completed_shots": 2,
                    "total_shots": 3,
                    "completed_weight_seconds": 12.0,
                    "total_weight_seconds": 15.0,
                    "current_shot_ids": ["S3"],
                }
            }
        )
        self.assertAlmostEqual(overlay.weighted_percent(), 80.0)
        overlay.stop()
        window.project_dirty = False
        window.close()

    def test_generation_progress_rows_use_each_shot_actual_duration(self):
        window = DirectorCutStudio()
        window.director_cues = [
            DirectorCue("S1", "shot", 0.0, 2.0, "Two seconds", track_id="V1"),
            DirectorCue("S2", "shot", 2.0, 5.0, "Three seconds", track_id="V1"),
            DirectorCue("S3", "shot", 5.0, 15.0, "Ten seconds", track_id="V1"),
        ]
        rows = window._progress_shot_rows(0.0, 15.0)
        self.assertEqual([row["shot_id"] for row in rows], ["S1", "S2", "S3"])
        self.assertEqual([row["duration_seconds"] for row in rows], [2.0, 3.0, 10.0])
        window.project_dirty = False
        window.close()

    def test_hidden_h3_reference_is_source_monitor_fallback(self):
        folder = PROJECT_ROOT / ".director_cache" / "source_monitor_fallback_test"
        folder.mkdir(parents=True, exist_ok=True)
        image = folder / "reference.png"
        QImage(64, 36, QImage.Format_RGB32).save(str(image))
        window = DirectorCutStudio()
        asset = next(item for item in window.scan.assets if item.media_type == "image")
        assign_local_media(window.scan, asset, image)
        asset.timeline_placed = True
        asset.timeline_track_id = "V1"
        asset.timeline_lane = next(
            index for index, track in enumerate(window.tracks) if track.track_id == "V1"
        )
        asset.start_seconds = 0.0
        asset.end_seconds = window.scan.duration_seconds
        asset.monitor_visible = False
        window.render_timeline_at(0.5, force_seek=True)
        self.assertIs(window.monitor_stack.currentWidget(), window.monitor_image)
        self.assertFalse(window.monitor_image.pixmap().isNull())
        window.seek_timeline(window.scan.duration_seconds)
        self.assertEqual(window.position_slider.value(), window.position_slider.maximum())
        self.assertFalse(window.monitor_image.pixmap().isNull())
        window.project_dirty = False
        window.close()

    def test_playhead_slider_is_unsnapped_and_timeline_scene_uses_project_duration(self):
        window = DirectorCutStudio()
        self.assertIsInstance(window.position_slider, PrecisionScrubSlider)
        self.assertEqual(window.position_slider.singleStep(), 1)
        self.assertTrue(window.position_slider.hasTracking())
        window.position_slider.resize(1001, 24)
        window.position_slider.setRange(0, 45000)
        window.position_slider.setValue(22500)
        window.position_slider._drag_anchor_x = 500.0
        window.position_slider._drag_anchor_value = 22500
        self.assertEqual(window.position_slider._drag_value_at_x(500.0), 22500)
        self.assertGreater(window.position_slider._drag_value_at_x(499.0), 22000)
        self.assertEqual(window.position_slider._drag_value_at_x(0.0), 0)
        self.assertEqual(window.position_slider._drag_value_at_x(1000.0), 45000)
        window._set_design_duration(45.0)
        self.assertEqual(window.timeline.duration, 45.0)
        self.assertGreaterEqual(
            window.timeline.scene_obj.sceneRect().width(),
            window.timeline.origin_x + 45.0 * window.timeline.pps,
        )
        window._begin_timeline_slider_scrub()
        window.position_slider.setValue(17237)
        window._preview_timeline_slider_scrub(17237)
        self.assertAlmostEqual(window.playhead_seconds, 17.237, places=3)
        self.assertAlmostEqual(window.timeline.playhead_seconds, 17.237, places=3)
        self.assertEqual(window.position_slider.value(), 17237)
        window._end_timeline_slider_scrub()
        self.assertAlmostEqual(window.playhead_seconds, 17.237, places=3)
        window.project_dirty = False
        window.close()

    def test_render_status_bar_tracks_local_dirty_running_failed_and_reusable_segments(self):
        window = DirectorCutStudio()
        window._set_design_duration(45.0)
        planned = window._planned_render_segments()
        self.assertEqual(len(planned), 3)
        cache = PROJECT_ROOT / ".director_cache" / "render_status_test"
        cache.mkdir(parents=True, exist_ok=True)
        completed = []
        for segment in planned:
            output = cache / f"{segment.segment_id}.mp4"
            output.write_bytes(b"cached-segment")
            row = segment.to_dict()
            row.update(status="complete", output_path=str(output))
            completed.append(row)
        window.smart_render_manifests["production"] = {
            "render_policy_version": 11,
            "segments": completed,
        }
        window._refresh_render_status_bar()
        self.app.processEvents()
        self.assertEqual(
            [row["display_status"] for row in window.timeline.render_segments],
            ["reusable", "reusable", "reusable"],
        )

        # A Shot beginning exactly at 15s belongs to the next core window,
        # not the completed 0-15s window.
        window.add_director_cue("shot", 15.0, "Medium-wide", end_seconds=18.0)
        self.app.processEvents()
        statuses = {
            row["segment_id"]: row["display_status"]
            for row in window.timeline.render_segments
        }
        second_id = planned[1].segment_id
        self.assertEqual(statuses[planned[0].segment_id], "reusable")
        self.assertEqual(statuses[second_id], "dirty")

        window._generation_message(
            {"segment_status": {"segment_id": second_id, "status": "running"}}
        )
        self.app.processEvents()
        self.assertEqual(
            next(row for row in window.timeline.render_segments if row["segment_id"] == second_id)["display_status"],
            "running",
        )
        window._generation_message(
            {"segment_status": {"segment_id": second_id, "status": "failed"}}
        )
        self.app.processEvents()
        self.assertEqual(
            next(row for row in window.timeline.render_segments if row["segment_id"] == second_id)["display_status"],
            "failed",
        )
        scene_statuses = {
            str(item.data(1)): str(item.data(2))
            for item in window.timeline.scene_obj.items()
            if item.data(0) == "render-status"
        }
        self.assertEqual(scene_statuses[second_id], "failed")
        self.assertIn(second_id, window._project_payload()["render_dirty_segment_ids"])
        for output in cache.glob("*.mp4"):
            output.unlink(missing_ok=True)
        cache.rmdir()
        window.project_dirty = False
        window.close()

    def test_high_resolution_output_uses_monitor_proxy_and_buffered_does_not_reseek(self):
        folder = PROJECT_ROOT / ".director_cache" / "monitor_proxy_test"
        folder.mkdir(parents=True, exist_ok=True)
        source = folder / "large.mp4"
        source.write_bytes(b"monitor-proxy-probe")
        window = DirectorCutStudio()
        with patch(
            "director_cut_studio.probe_media",
            return_value={
                "bit_rate": 29_000_000,
                "streams": [{"codec_type": "video", "width": 2752, "height": 1536}],
            },
        ):
            proxy = window._generated_monitor_proxy_path(source)
        self.assertIsNotNone(proxy)
        self.assertEqual(proxy.parent.name, "monitor_proxies")
        window.generated_pending_position_ms = window.generated_player.position()
        with patch.object(window.generated_player, "setPosition") as set_position:
            window._generated_media_status_changed(QMediaPlayer.BufferedMedia)
        set_position.assert_not_called()
        window.project_dirty = False
        window.close()

    def test_edited_dialogue_invalidates_tts_contract_and_unmutes_reference_track(self):
        window = DirectorCutStudio()
        audio = next(asset for asset in window.scan.assets if asset.media_type == "audio")
        audio.local_path = str(PROJECT_ROOT / "authored-dialogue-test.wav")
        audio.filename = "authored-dialogue-test.wav"
        audio.timeline_placed = True
        audio.timeline_track_id = "A1"
        audio.start_seconds = 0.0
        audio.end_seconds = 3.0
        audio.recognition = "AI DESIGN AUTHORED SPEECH TTS\nAUTHORED TTS TRANSCRIPT:"
        track = next(item for item in window.tracks if item.track_id == "A1")
        track.muted = True
        layer = TextLayer(
            "T1", "Updated exact words", 0.0, 3.0, "A4",
            content_role="dialogue", speaker="S2", language="Mandarin Chinese",
            delivery="Low adult male voice", lip_sync=True, shot_id="",
        )
        window.text_layers = [layer]
        window._refresh_text_layers(layer)
        window.timeline_tts_refresh_timer.stop()

        self.assertTrue(window.timeline_tts_stale)
        self.assertEqual(window.authored_text_requirements[0]["content"], "Updated exact words")
        self.assertEqual(window.authored_text_requirements[0]["speaker"], "S2")
        signature = window._timeline_tts_signature()
        window._write_tts_signature(audio, signature)
        self.assertEqual(window._stored_tts_signature(audio), signature)
        self.assertTrue(window._activate_authored_speech_reference(audio))
        self.assertFalse(track.muted)
        window.project_dirty = False
        window.close()

    def test_design_dialogue_mode_buttons_and_native_to_vox_asset_reservation(self):
        window = DirectorCutStudio()
        context = window._design_context()
        context["dialogue_tts_engine"] = "h3_native"
        with patch(
            "director_cut_studio.voxcpm_model_missing",
            return_value=["model folder"],
        ):
            dialog = DesignPageDialog(
                window.runtime, context, window.scan.counts, window,
                context_provider=window._design_context,
            )
            self.assertEqual(dialog.design_tts_engine, "h3_native")
            self.assertTrue(dialog.dialogue_mode_buttons["h3_native"].isChecked())
            self.assertIn(
                "ffad42",
                dialog.dialogue_mode_buttons["voxcpm2_local"].styleSheet(),
            )
            dialog.dialogue_mode_buttons["voxcpm2_local"].click()
            self.assertEqual(dialog.design_tts_engine, "voxcpm2_local")
            self.assertTrue(dialog.dialogue_mode_buttons["voxcpm2_local"].isChecked())
            self.assertFalse(dialog.dialogue_model_warning.isHidden())
            self.assertIn("MODEL MISSING", dialog.dialogue_model_warning.text())
            dialog.close()

        with patch(
            "director_cut_studio.voxcpm_model_missing",
            return_value=["model.safetensors or pytorch_model.bin"],
        ):
            window.settings_dialogue_tts.setCurrentIndex(
                window.settings_dialogue_tts.findData("voxcpm2_local")
            )
            self.assertFalse(window._refresh_voxcpm_model_status_ui())
            self.assertIn(
                "MODEL MISSING", window.settings_voxcpm_model_status.text()
            )
            self.assertIn("ff9d38", window.settings_dialogue_tts.styleSheet())

        window.text_layers = [TextLayer(
            "T1", "Exact words", 0.0, 3.0, "A4",
            content_role="dialogue", speaker="S2", language="Mandarin Chinese",
        )]
        window.render_settings.dialogue_tts_engine = "voxcpm2_local"
        asset = window._ensure_timeline_tts_asset()
        self.assertIsNotNone(asset)
        self.assertTrue(asset.timeline_placed)
        self.assertIn("AI DESIGN AUTHORED SPEECH TTS", asset.recognition)

        window.render_settings.dialogue_tts_engine = "h3_native"
        window._use_h3_native_dialogue()
        self.assertEqual(asset.activation_mode, "bypass")
        self.assertFalse(asset.enabled)
        window.project_dirty = False
        window.close()

    def test_design_tts_failure_preserves_timeline_plan_without_silent_audio(self):
        window = DirectorCutStudio()
        plan = {
            "media_requests": [
                {"requirement_id": "authored_speech_tts", "media_type": "audio"},
                {"requirement_id": "scene_image", "media_type": "image"},
            ]
        }
        materials = [
            {"requirement_id": "authored_speech_tts", "media_type": "audio"},
            {"requirement_id": "scene_image", "media_type": "image"},
        ]
        window.pending_design_tts = {
            "plan": plan,
            "materials": materials,
            "replace": True,
            "before": {},
            "design_dir": Path("example") / "tts_recovery",
            "settings": None,
            "warnings": [],
            "generate_images": False,
            "tts_material": materials[0],
        }
        window.design_tts_result = {
            "error": "VoxCPM._generate() got an unexpected keyword argument 'seed'"
        }
        with (
            patch.object(window, "_commit_ai_design") as commit,
            patch.object(window, "_restore_monitor_after_generation"),
        ):
            window._design_tts_finished(1, "")
        self.assertEqual(commit.call_count, 1)
        args, kwargs = commit.call_args
        committed_plan = args[0]
        committed_materials = args[1]
        self.assertFalse(any(
            item.get("requirement_id") == "authored_speech_tts"
            for item in committed_plan["media_requests"]
        ))
        self.assertFalse(any(
            item.get("requirement_id") == "authored_speech_tts"
            for item in committed_materials
        ))
        self.assertTrue(kwargs["timeline_tts_stale"])
        self.assertIn("Text Layers were preserved", args[5][0])
        window.project_dirty = False
        window.close()


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from design_ai_service import generate
from source_video_analysis import (
    SOURCE_VIDEO_QWEN_ANALYSIS_MARKER,
    build_source_video_analysis_prompts,
    build_source_video_shot_people_scan_prompts,
    normalize_source_video_analysis,
    normalize_source_video_shot_people_scan,
    parse_source_video_analysis,
    render_source_video_analysis,
    scene_intervals_from_breakdown,
)


def _analysis_payload(intervals):
    return {
        "media_id": "V1",
        "evidence_fingerprint": "abc123",
        "duration_seconds": 12.0,
        "location_ledger": [{
            "location_id": "L1",
            "description": "A visible restaurant interior.",
            "defining_elements": ["tables", "service counter"],
            "first_scene_index": 1,
            "last_scene_index": len(intervals),
            "confidence": "high",
        }],
        "principal_roles": [{
            "role_id": "R1",
            "visual_identity": "Recurring lead",
            "wardrobe": "blue jacket",
            "narrative_function": "initiates the encounter",
            "scene_indexes": list(range(1, len(intervals) + 1)),
            "representative_scene_index": 1,
            "representative_panel": "midpoint",
            "thumbnail_bbox_normalized": [0.2, 0.1, 0.8, 0.95],
            "appearance_evidence": [
                {
                    "scene_index": index,
                    "panel": "midpoint",
                    "thumbnail_bbox_normalized": [0.2, 0.1, 0.8, 0.95],
                    "face_visibility": "front",
                }
                for index in range(1, len(intervals) + 1)
            ],
            "confidence": "high",
        }],
        "scenes": [{
            "scene_index": index,
            "start_seconds": start,
            "end_seconds": end,
            "location_id": "L1",
            "active_source_roles": ["R1"],
            "visible_event": f"Event {index}",
            "action_causality": "Continues the preceding visible action.",
            "speaker_role": "",
            "listener_roles": [],
            "framing": "medium shot",
            "camera_angle": "eye level",
            "camera_movement": "static or indeterminate from sampled frames",
            "environment_elements": ["table"],
            "transition_out": "cut",
            "confidence": "high",
        } for index, (start, end) in enumerate(intervals, 1)],
        "global_camera_grammar": "Reaction-led coverage.",
        "edit_rhythm": "Short alternating cuts.",
        "continuity_constraints": ["Keep R1 in the same location."],
        "uncertain_inferences": [],
    }


class SourceVideoAnalysisTests(unittest.TestCase):
    def test_shot_people_scan_prompt_and_normalizer_preserve_frame_evidence(self):
        system, user = build_source_video_shot_people_scan_prompts(
            media_id="V1",
            shot_id="S8",
            batch_index=2,
            frame_indexes=list(range(32, 64)),
            known_roles=[{
                "role_id": "R1",
                "visual_identity": "woman with long dark hair",
                "wardrobe": "blue dress",
            }],
        )
        self.assertIn("every 24fps V1 relay frame", system)
        self.assertIn("cut off by the left, right, top or bottom frame edge", system)
        self.assertIn("Never return [0,0,1,1]", system)
        self.assertIn('"shot_id":"S8"', user)
        normalized = normalize_source_video_shot_people_scan(
            {
                "media_id": "V1",
                "shot_id": "S8",
                "batch_index": 2,
                "people": [{
                    "matched_role_id": "R1",
                    "visual_identity": "same woman",
                    "wardrobe": "blue dress",
                    "first_frame_index": 35,
                    "last_frame_index": 62,
                    "best_frame_index": 48,
                    "bbox_normalized": [-0.1, 0.1, 0.62, 1.2],
                    "face_visibility": "front",
                    "confidence": "high",
                }],
            },
            expected_media_id="V1",
            expected_shot_id="S8",
            expected_batch_index=2,
            valid_frame_indexes=set(range(32, 64)),
        )
        self.assertEqual(normalized["people"][0]["matched_role_id"], "R1")
        self.assertEqual(
            normalized["people"][0]["bbox_normalized"],
            [0.0, 0.1, 0.62, 1.0],
        )

    def test_shot_people_scan_rejects_full_frame_uncertainty_bbox(self):
        normalized = normalize_source_video_shot_people_scan(
            {
                "media_id": "V1",
                "shot_id": "S6",
                "batch_index": 0,
                "people": [{
                    "matched_role_id": "R2",
                    "visual_identity": "edge-cropped man",
                    "wardrobe": "white coat",
                    "first_frame_index": 0,
                    "last_frame_index": 23,
                    "best_frame_index": 12,
                    "bbox_normalized": [0, 0, 1, 1],
                    "face_visibility": "edge-cropped",
                    "confidence": "medium",
                }],
            },
            expected_media_id="V1",
            expected_shot_id="S6",
            expected_batch_index=0,
            valid_frame_indexes=set(range(24)),
        )

        self.assertEqual(normalized["people"][0]["bbox_normalized"], [])

    def test_scene_intervals_follow_full_duration_breakdown(self):
        intervals = scene_intervals_from_breakdown(
            "SOURCE VIDEO BREAKDOWN · full_duration=yes scene_cuts=2.5, 7.0, 9.25",
            12.0,
        )
        self.assertEqual(intervals, [(0.0, 2.5), (2.5, 7.0), (7.0, 9.25), (9.25, 12.0)])

    def test_normalizer_preserves_every_authoritative_interval(self):
        intervals = [(0.0, 4.0), (4.0, 7.5), (7.5, 12.0)]
        source = _analysis_payload(intervals)
        # Model-provided times are advisory; the detected boundaries remain exact.
        source["scenes"][1]["start_seconds"] = 99.0
        normalized = normalize_source_video_analysis(
            json.dumps(source),
            expected_media_id="V1",
            expected_fingerprint="abc123",
            duration_seconds=12.0,
            scene_intervals=intervals,
        )
        self.assertEqual(len(normalized["scenes"]), 3)
        self.assertEqual(normalized["scenes"][1]["start_seconds"], 4.0)
        self.assertTrue(render_source_video_analysis(normalized).startswith(
            SOURCE_VIDEO_QWEN_ANALYSIS_MARKER
        ))
        reparsed = parse_source_video_analysis(render_source_video_analysis(normalized))
        self.assertEqual(reparsed["principal_roles"][0]["role_id"], "R1")
        self.assertEqual(
            reparsed["principal_roles"][0]["thumbnail_bbox_normalized"],
            [0.2, 0.1, 0.8, 0.95],
        )
        self.assertEqual(
            [row["scene_index"] for row in reparsed["principal_roles"][0]["appearance_evidence"]],
            [1, 2, 3],
        )

    def test_normalizer_repairs_missing_comma_in_long_qwen_json(self):
        intervals = [(0.0, 4.0), (4.0, 8.0)]
        text = json.dumps(_analysis_payload(intervals), ensure_ascii=False, indent=2)
        broken = text.replace("},\n    {", "}\n    {", 1)
        self.assertNotEqual(text, broken)
        normalized = normalize_source_video_analysis(
            broken,
            expected_media_id="V1",
            expected_fingerprint="abc123",
            duration_seconds=8.0,
            scene_intervals=intervals,
        )
        self.assertEqual(len(normalized["scenes"]), 2)

    def test_parser_accepts_saved_legacy_schema_marker(self):
        payload = _analysis_payload([(0.0, 4.0), (4.0, 8.0)])
        legacy = (
            "QWEN SOURCE VIDEO DIRECTOR ANALYSIS V4\n"
            + json.dumps(payload, ensure_ascii=False)
        )
        parsed = parse_source_video_analysis(legacy)
        self.assertEqual(len(parsed["principal_roles"]), 1)
        self.assertEqual(parsed["principal_roles"][0]["role_id"], "R1")
        self.assertEqual(parsed["principal_roles"][0]["scene_indexes"], [1, 2])

    def test_parser_recovers_role_ledger_from_scene_evidence(self):
        payload = _analysis_payload([(0.0, 4.0), (4.0, 8.0)])
        payload["principal_roles"] = []
        payload["scenes"][0]["active_source_roles"] = ["R2"]
        payload["scenes"][0]["speaker_role"] = "R2"
        payload["scenes"][1]["active_source_roles"] = ["R2"]
        payload["scenes"][1]["listener_roles"] = ["R2"]
        parsed = parse_source_video_analysis(
            "QWEN SOURCE VIDEO DIRECTOR ANALYSIS V5\n"
            + json.dumps(payload, ensure_ascii=False)
        )
        self.assertEqual(len(parsed["principal_roles"]), 1)
        self.assertEqual(parsed["principal_roles"][0]["role_id"], "R2")
        self.assertEqual(parsed["principal_roles"][0]["scene_indexes"], [1, 2])
        self.assertEqual(
            [row["scene_index"] for row in parsed["principal_roles"][0]["appearance_evidence"]],
            [1, 2],
        )

    def test_prompt_requires_all_storyboard_sheets_in_order(self):
        system, user = build_source_video_analysis_prompts(
            media_id="V1",
            evidence_fingerprint="abc123",
            duration_seconds=12.0,
            scene_intervals=[(0.0, 6.0), (6.0, 12.0)],
            recognition=(
                "AUDIO INTELLIGENCE\n"
                "Voice-active ranges: 0.20-1.40s, 6.10-7.20s\n"
                "WHISPER TRANSCRIPT\n[00:00.20] secret words\n[00:06.10] more words"
            ),
        )
        self.assertIn("sheet 1", system)
        self.assertIn("sheet 2", system)
        self.assertIn("relative to the CONTENT OF THAT ONE LABELLED PANEL", system)
        self.assertIn("required_scene_intervals", user)
        self.assertIn('"voice_active_ranges_seconds"', user)
        self.assertIn("0.2", user)
        self.assertIn('"detected_utterance_onsets_seconds"', user)
        self.assertNotIn("secret words", user)
        self.assertNotIn("more words", user)

    def test_required_visual_analysis_never_falls_back_to_text_only(self):
        cache_root = Path(__file__).parent / ".director_cache"
        cache_root.mkdir(parents=True, exist_ok=True)
        image = cache_root / "source_video_required_visual_test.jpg"
        image.write_bytes(b"storyboard-pixels")
        try:
            calls = []

            def fake_request(url, *, api_key, timeout, payload=None):
                calls.append((url, payload))
                if url.endswith("/models"):
                    return {"data": [{"id": "qwen-vision"}]}
                raise RuntimeError("vision request rejected")

            with patch("design_ai_service.request_json", side_effect=fake_request):
                with self.assertRaisesRegex(RuntimeError, "vision request rejected"):
                    generate({
                        "provider": "lm_studio",
                        "base_url": "http://127.0.0.1:1234/v1",
                        "model": "qwen-vision",
                        "system_prompt": "Inspect pixels.",
                        "user_prompt": "Return JSON.",
                        "schema": {"type": "object"},
                        "input_image_paths": [str(image)],
                        "require_image_input": True,
                    })
            chat_calls = [item for item in calls if item[0].endswith("/chat/completions")]
            self.assertEqual(len(chat_calls), 1)
            self.assertIsInstance(chat_calls[0][1]["messages"][-1]["content"], list)
        finally:
            image.unlink(missing_ok=True)

    def test_required_visual_analysis_rejects_missing_sheet(self):
        with self.assertRaisesRegex(ValueError, "requires direct image input"):
            generate({
                "provider": "lm_studio",
                "base_url": "http://127.0.0.1:1234/v1",
                "model": "qwen-vision",
                "system_prompt": "Inspect pixels.",
                "user_prompt": "Return JSON.",
                "schema": {"type": "object"},
                "input_image_paths": ["missing.jpg"],
                "require_image_input": True,
            })

    def test_source_analysis_does_not_substitute_another_lm_model(self):
        def fake_request(url, *, api_key, timeout, payload=None):
            if url.endswith("/models"):
                return {"data": [{"id": "some-other-model"}]}
            raise AssertionError("chat completion must not run with a substituted model")

        with patch("design_ai_service.request_json", side_effect=fake_request):
            with self.assertRaisesRegex(RuntimeError, "not loaded or available"):
                generate({
                    "provider": "lm_studio",
                    "base_url": "http://127.0.0.1:1234/v1",
                    "model": "qwen3.8-uncensored-nvfp4-mtp",
                    "system_prompt": "Inspect pixels.",
                    "user_prompt": "Return JSON.",
                    "schema": {"type": "object"},
                    "require_exact_model": True,
                })

    def test_source_analysis_caps_oversized_output_request(self):
        calls = []

        def fake_request(url, *, api_key, timeout, payload=None):
            calls.append((url, payload))
            if url.endswith("/models"):
                return {"data": [{"id": "qwen-vision"}]}
            return {
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": "{}"},
                }]
            }

        with patch("design_ai_service.request_json", side_effect=fake_request):
            result = generate({
                "provider": "lm_studio",
                "base_url": "http://127.0.0.1:1234/v1",
                "model": "qwen-vision",
                "system_prompt": "Inspect pixels.",
                "user_prompt": "Return compact JSON.",
                "schema": {"type": "object"},
                "max_output_tokens": 65536,
                "temperature": 0.0,
            })

        chat_payload = next(
            payload for url, payload in calls if url.endswith("/chat/completions")
        )
        self.assertEqual(chat_payload["max_tokens"], 32768)
        self.assertEqual(chat_payload["temperature"], 0.0)
        self.assertEqual(result["max_output_tokens"], 32768)
        self.assertEqual(result["finish_reason"], "stop")

    def test_long_form_source_analysis_may_use_64k_output_budget(self):
        calls = []

        def fake_request(url, *, api_key, timeout, payload=None):
            calls.append((url, payload))
            if url.endswith("/models"):
                return {"data": [{"id": "qwen-vision"}]}
            return {
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": "{}"},
                }]
            }

        with patch("design_ai_service.request_json", side_effect=fake_request):
            result = generate({
                "provider": "lm_studio",
                "base_url": "http://127.0.0.1:1234/v1",
                "model": "qwen-vision",
                "system_prompt": "Inspect a 90-second storyboard.",
                "user_prompt": "Return the complete compact role ledger.",
                "schema": {"type": "object"},
                "max_output_tokens": 65536,
                "allow_large_structured_output": True,
                "temperature": 0.0,
            })

        chat_payload = next(
            payload for url, payload in calls if url.endswith("/chat/completions")
        )
        self.assertEqual(chat_payload["max_tokens"], 65536)
        self.assertEqual(result["max_output_tokens"], 65536)
        self.assertEqual(result["finish_reason"], "stop")


if __name__ == "__main__":
    unittest.main()

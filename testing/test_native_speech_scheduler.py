import unittest
from unittest.mock import patch

from native_speech_guard import NativeSpeechGuard
from project_integrity import repair_project_payload, repair_speech_timing_payload


class NativeSpeechSchedulerTests(unittest.TestCase):
    def test_short_latin_whisper_noise_is_not_treated_as_dialogue(self):
        self.assertEqual(NativeSpeechGuard._meaningful_text("you"), "")
        self.assertEqual(NativeSpeechGuard._meaningful_text("so"), "")
        self.assertEqual(NativeSpeechGuard._meaningful_text("hello"), "hello")
        self.assertEqual(NativeSpeechGuard._meaningful_text("旁白"), "旁白")

    def test_line_fidelity_detects_repeated_phrase_inside_authorized_window(self):
        expected = "明明是我先拔剑的，怎么变成我害了雄霸？"
        transcript = "明明是我先拔箭的怎么变成我害了熊霸，怎么变成我害了熊霸？"
        violation = NativeSpeechGuard.line_fidelity_violation(expected, transcript)
        self.assertIsNotNone(violation)
        self.assertIn(
            violation["kind"],
            {"repeated_authored_phrase", "unauthorized_extra_inside_authored_window"},
        )

    def test_line_fidelity_tolerates_whisper_character_substitutions(self):
        expected = "都怪摄影师！你拍得太帅，雄霸才没死！"
        transcript = "都怪摄影師你拍得太帥熊霸才沒死"
        self.assertIsNone(
            NativeSpeechGuard.line_fidelity_violation(expected, transcript)
        )

    def test_same_line_unison_is_checked_once_instead_of_skipped(self):
        guard = NativeSpeechGuard("models/whisper-small", "ffmpeg.exe")
        spec = {
            "enabled": True,
            "authorized_lines": [
                {
                    "layer_id": "T3", "start_seconds": 0.0, "end_seconds": 4.0,
                    "text": "都怪那个拍照的", "overlap_policy": "overlap",
                },
                {
                    "layer_id": "T4", "start_seconds": 0.0, "end_seconds": 4.0,
                    "text": "都怪那个拍照的", "overlap_policy": "overlap",
                },
            ],
        }
        with (
            patch.object(guard, "_ensure_model"),
            patch.object(
                guard,
                "_transcribe_window",
                return_value=("完全不相关的句子", 0.5),
            ) as transcribe,
        ):
            result = guard.inspect("unused.mp4", spec)
        self.assertEqual(transcribe.call_count, 1)
        self.assertFalse(result["passed"])
        self.assertEqual(
            result["violations"][0]["kind"],
            "materially_changed_or_unrelated_authored_line",
        )
        self.assertEqual(
            result["checked_lines"][1]["fidelity_check_skipped"],
            "same_line_unison_checked_once",
        )

    def test_auto_dialogue_reserves_release_gap_and_ripples_timeline(self):
        payload = {
            "timeline_duration_seconds": 12.0,
            "work_area": [0.0, 12.0],
            "enforce_native_speech_release_gap": True,
            "director_cues": [
                {
                    "cue_id": "S1", "cue_type": "shot",
                    "start_seconds": 0.0, "end_seconds": 6.0,
                },
                {
                    "cue_id": "S2", "cue_type": "shot",
                    "start_seconds": 6.0, "end_seconds": 12.0,
                },
            ],
            "text_layers": [
                {
                    "layer_id": "T1", "content_role": "dialogue",
                    "text": "第一句对白说完。", "language": "Chinese",
                    "delivery": "calm Chinese male voice",
                    "start_seconds": 0.0, "end_seconds": 6.0,
                    "overlap_policy": "auto",
                },
                {
                    "layer_id": "T2", "content_role": "dialogue",
                    "text": "第二句对白接着说。", "language": "Chinese",
                    "start_seconds": 6.0, "end_seconds": 12.0,
                    "overlap_policy": "auto",
                },
            ],
            "assets": {},
            "timeline_clips": [],
            "authored_text_requirements": [],
        }
        repaired, report = repair_speech_timing_payload(payload)
        first, second = repaired["text_layers"]
        self.assertEqual((first["start_seconds"], first["end_seconds"]), (0.0, 6.0))
        self.assertEqual(
            (second["start_seconds"], second["end_seconds"]), (7.0, 13.0)
        )
        self.assertEqual(repaired["director_cues"][0]["end_seconds"], 7.0)
        self.assertEqual(repaired["director_cues"][1]["start_seconds"], 7.0)
        self.assertGreaterEqual(repaired["timeline_duration_seconds"], 14.5)
        self.assertTrue(any("non-vocal release gap" in row for row in report))
        self.assertEqual(first["language"], "Mandarin Chinese")
        self.assertEqual(first["voice_gender"], "male")

    def test_explicit_overlap_is_not_sequentially_shifted(self):
        payload = {
            "timeline_duration_seconds": 8.0,
            "work_area": [0.0, 8.0],
            "enforce_native_speech_release_gap": True,
            "director_cues": [{
                "cue_id": "S1", "cue_type": "shot",
                "start_seconds": 0.0, "end_seconds": 8.0,
            }],
            "text_layers": [
                {
                    "layer_id": "T1", "content_role": "dialogue",
                    "text": "第一句", "language": "Chinese",
                    "start_seconds": 0.0, "end_seconds": 4.0,
                    "overlap_policy": "auto",
                },
                {
                    "layer_id": "T2", "content_role": "dialogue",
                    "text": "同时说", "language": "Chinese",
                    "start_seconds": 2.0, "end_seconds": 5.0,
                    "overlap_policy": "overlap",
                },
            ],
            "assets": {},
            "timeline_clips": [],
            "authored_text_requirements": [],
        }
        repaired, _report = repair_speech_timing_payload(payload)
        self.assertEqual(repaired["text_layers"][1]["start_seconds"], 2.0)

    def test_two_person_comic_talk_show_repairs_invalid_third_speaker(self):
        payload = {
            "special_skill": "comic-talk-show-h3",
            "timeline_duration_seconds": 12.0,
            "work_area": [0.0, 12.0],
            "prompt": {
                "brief": "A two-person comic talk show based on the two complete people in P1.",
                "constraints": ["Preserve exactly two people from P1."],
            },
            "director_cues": [
                {"cue_id": "S1", "cue_type": "shot", "start_seconds": 0.0,
                 "end_seconds": 4.0, "subject_action": "S1 speaks."},
                {"cue_id": "S2", "cue_type": "shot", "start_seconds": 4.0,
                 "end_seconds": 8.0, "subject_action": "S2 speaks."},
                {"cue_id": "S3", "cue_type": "shot", "start_seconds": 8.0,
                 "end_seconds": 12.0,
                 "subject_action": "S1 returns for the payoff.",
                 "detail": "S3=the 3rd complete P1 principal speaks."},
            ],
            "text_layers": [
                {"layer_id": "T1", "content_role": "dialogue", "speaker": "S1",
                 "text": "甲", "language": "Chinese", "start_seconds": 0.5,
                 "end_seconds": 2.0},
                {"layer_id": "T2", "content_role": "dialogue", "speaker": "S2",
                 "text": "乙", "language": "Chinese", "start_seconds": 4.5,
                 "end_seconds": 6.0},
                {"layer_id": "T3", "content_role": "dialogue", "speaker": "S3",
                 "text": "丙", "language": "Chinese", "start_seconds": 8.5,
                 "end_seconds": 10.0},
            ],
            "authored_text_requirements": [
                {"content_role": "dialogue", "speaker": "S3", "text": "丙",
                 "start_seconds": 8.5, "end_seconds": 10.0},
            ],
            "assets": {},
            "timeline_clips": [],
        }
        repaired, report = repair_project_payload(payload, invalidate_stale_renders=False)
        self.assertEqual(
            [row["speaker"] for row in repaired["text_layers"]],
            ["S1", "S2", "S1"],
        )
        self.assertEqual(repaired["authored_text_requirements"][0]["speaker"], "S1")
        self.assertIn("S1=the 1 complete", repaired["director_cues"][2]["detail"])
        self.assertTrue(any("explicitly contains 2 people" in row for row in report))


if __name__ == "__main__":
    unittest.main()

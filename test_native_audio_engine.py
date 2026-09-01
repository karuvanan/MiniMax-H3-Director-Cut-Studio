import unittest

from audio_engine import evaluate_native_audio_qc
from native_audio_engine import (
    audio_reference_intent_text,
    build_native_audio_profile,
    environment_continuity_text,
    native_audio_direction_text,
)


class NativeAudioDirectionTests(unittest.TestCase):
    def test_close_indoor_dialogue_contains_required_native_contract(self):
        profile = build_native_audio_profile(
            {
                "framing": "Close-up",
                "subject_action": "A woman speaks softly in a furnished office.",
                "environment_response": "The computer fan continues behind her.",
            },
            [{"delivery": "low voice", "content_role": "dialogue"}],
        )
        prompt = native_audio_direction_text(profile)
        self.assertIn("furnished office interior", prompt)
        self.assertIn("approximately 0.6-1.2 metres", prompt)
        self.assertIn("Continuous environment", prompt)
        self.assertIn("diegetic sound", prompt)
        self.assertIn("recording-booth close-mic", prompt)
        self.assertIn("dry studio voice", prompt)
        self.assertIn("Generate no background music", prompt)

    def test_wide_outdoor_dialogue_has_distance_attenuation_and_open_bed(self):
        profile = build_native_audio_profile(
            {
                "framing": "Extreme wide",
                "subject_action": "A man calls across an open exterior street.",
            },
            [{"delivery": "shout", "content_role": "dialogue"}],
        )
        prompt = native_audio_direction_text(profile)
        self.assertIn("open exterior", prompt)
        self.assertIn("distance attenuation", prompt)
        self.assertIn("continuous open-air ambience", prompt)

    def test_same_space_preserves_environment_and_close_cut_changes_perspective(self):
        wide = build_native_audio_profile(
            {"framing": "Wide", "subject_action": "Two people talk in an office."},
            [{"content_role": "dialogue"}],
        )
        close = build_native_audio_profile(
            {"framing": "Close-up", "subject_action": "The woman answers in the same office."},
            [{"content_role": "dialogue"}],
        )
        continuity = environment_continuity_text(wide, close)
        self.assertIn("same furnished office interior", continuity)
        self.assertIn("continuous ambience", continuity)
        self.assertIn("closer framing", continuity)
        self.assertIn("reflections become proportionally less prominent", continuity)

    def test_scene_change_explicitly_changes_acoustic_space(self):
        indoor = build_native_audio_profile(
            {"framing": "Medium", "subject_action": "A woman waits in a small hotel room."}
        )
        outdoor = build_native_audio_profile(
            {"framing": "Wide", "subject_action": "She steps onto an outdoor street."}
        )
        continuity = environment_continuity_text(indoor, outdoor)
        self.assertIn("Acoustic-space transition", continuity)
        self.assertIn("small furnished interior", continuity)
        self.assertIn("open exterior", continuity)
        self.assertIn("do not carry the earlier room tail", continuity)

    def test_reference_intent_never_copies_dialogue_or_voice_identity(self):
        direction = audio_reference_intent_text(True)
        self.assertIn("spatial acoustics", direction)
        self.assertIn("Do not copy, replay or imitate any words", direction)
        self.assertIn("Do not use a reference character's voice", direction)
        self.assertIn("preceding generated segment", direction)

    def test_native_audio_qc_is_analysis_only(self):
        result = evaluate_native_audio_qc(
            ["我明明还在公司"],
            "[00:01.00] 我明明还在公司",
            {"voice_ratio": 0.3},
            {"present": True},
        )
        self.assertEqual(result["status"], "PASS")
        warning = evaluate_native_audio_qc(
            [],
            "[00:01.00] unauthorized speech",
            {"voice_ratio": 0.2},
            {"present": False},
        )
        self.assertEqual(warning["status"], "WARNING")
        self.assertTrue(warning["unauthorized_extra_dialogue"])
        self.assertTrue(warning["environment_sound_missing"])


if __name__ == "__main__":
    unittest.main()

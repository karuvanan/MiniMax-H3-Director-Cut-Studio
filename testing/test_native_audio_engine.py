import unittest

from audio_engine import evaluate_native_audio_qc
from native_audio_engine import (
    CINEMATIC_DIALOGUE_ACOUSTIC_INTEGRATION_CONTRACT,
    NO_AUTHORED_SPEECH_CONTRACT,
    SPEECH_ENVIRONMENT_FUSION_CONTRACT,
    audio_reference_intent_text,
    build_native_audio_profile,
    enforce_no_authored_speech,
    environment_continuity_text,
    infer_acoustic_space,
    infer_foley,
    native_audio_direction_text,
)


class NativeAudioDirectionTests(unittest.TestCase):
    def test_empty_vocal_channel_keeps_ambience_and_removes_speech_priming(self):
        direction = (
            "Acoustic space: furnished office interior. "
            "Speaker-to-camera distance: one metre. "
            "Speaking state: natural conversational volume. "
            "Continuous environment: stable computer-fan room tone. "
            "Picture-synchronous Foley: keyboard taps and cloth movement. "
            "No narration or extra dialogue is permitted."
        )
        locked = enforce_no_authored_speech(direction)
        self.assertIn("furnished office interior", locked)
        self.assertIn("computer-fan room tone", locked)
        self.assertIn("keyboard taps", locked)
        self.assertIn(NO_AUTHORED_SPEECH_CONTRACT, locked)
        self.assertNotIn("Speaker-to-camera", locked)
        self.assertNotIn("natural conversational volume", locked)

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
        self.assertIn(SPEECH_ENVIRONMENT_FUSION_CONTRACT, prompt)
        self.assertIn("ordinary acoustic masking rather than gain ducking", prompt)
        self.assertIn("never to ambience or Foley", prompt)
        self.assertIn("ADR-like centre isolation", prompt)

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
        self.assertIn("direct-to-ambient ratio", prompt)

    def test_turning_character_changes_vocal_direction_without_extra_words(self):
        profile = build_native_audio_profile(
            {
                "framing": "Medium close-up",
                "subject_action": "S1 turns his head away while finishing the line in the rain.",
            },
            [{"delivery": "conversational", "content_role": "dialogue"}],
        )
        prompt = native_audio_direction_text(profile)
        self.assertIn("off-axis directionality", prompt)
        self.assertIn("high-frequency loss", prompt)
        self.assertIn("without adding any unauthorised word", prompt)

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

    def test_picture_scene_reset_outranks_negated_previous_location(self):
        profile = build_native_audio_profile({
            "framing": "Composition strictly from P4",
            "additional_direction": (
                "REFERENCE SCENE RESET TO P4. Do not import the previous corridor geometry."
            ),
            "location_transition": (
                "REFERENCE SCENE RESET: establish only the independent P4 location."
            ),
        })
        self.assertEqual(
            profile.acoustic_space,
            "the independent location visibly established by the active Picture reference",
        )
        self.assertNotIn("corridor", profile.ambience)
        previous = build_native_audio_profile({
            "framing": "Wide",
            "subject_action": "People move through a narrow corridor.",
        })
        continuity = environment_continuity_text(previous, profile)
        self.assertIn("Acoustic-space transition", continuity)
        self.assertIn("do not carry the earlier room tail", continuity)

    def test_wet_market_to_rain_alley_uses_distinct_native_spaces(self):
        indoor = build_native_audio_profile({
            "framing": "Close-up",
            "subject_action": "S1 blocks a kick in the indoor seafood aisle.",
            "environment_response": "Fish-tank pumps and market drainage continue.",
        })
        outdoor = build_native_audio_profile({
            "framing": "Close-up",
            "subject_action": "S2 counters in the outdoor rainy Hong Kong alley.",
            "additional_direction": "OUTDOOR CONTINUATION beyond the same market gate.",
        })
        self.assertEqual(indoor.acoustic_space, "cramped indoor wet market")
        self.assertIn("fish-tank pumps", indoor.ambience)
        self.assertEqual(outdoor.acoustic_space, "open rainy market alley")
        self.assertIn("open-air rain", outdoor.ambience)
        continuity = environment_continuity_text(indoor, outdoor)
        self.assertIn("Acoustic-space transition", continuity)
        self.assertIn("do not carry the earlier room tail", continuity)

    def test_reference_intent_never_copies_dialogue_or_voice_identity(self):
        direction = audio_reference_intent_text(True)
        self.assertIn("spatial acoustics", direction)
        self.assertIn("Do not copy, replay or imitate any words", direction)
        self.assertIn("Do not use a reference character's voice", direction)
        self.assertIn("preceding generated segment", direction)

    def test_authored_tts_is_declared_as_speech_stem_not_complete_soundtrack(self):
        direction = audio_reference_intent_text(
            [], authored_speech_references=["<Audio 1>"]
        )
        self.assertIn("Authored speech reference(s): <Audio 1>", direction)
        self.assertIn("exact authored words", direction)
        self.assertIn("not the complete soundtrack", direction)
        self.assertIn("continuous visible ambience", direction)
        self.assertIn("Digital silence between supplied utterances", direction)
        self.assertIn("not a silent-soundtrack instruction", direction)
        self.assertIn("not a final dry waveform mix", direction)
        self.assertIn("scene-matched direct-to-ambient ratio", direction)
        self.assertIn("never duplicate or replace the voice", direction)
        self.assertNotIn("No Audio or Video reference", direction)

    def test_foley_terms_do_not_match_stands_punchline_or_speaker_lock(self):
        foley = infer_foley(
            "Both principals stand in rain for the final visual punchline. "
            "Apply the speaker lock while the puddle ripples."
        )
        self.assertIn("water, rain and wet-surface contact", foley)
        self.assertNotIn("attack air-displacement", foley)
        self.assertNotIn("sharp contact transient", foley)
        self.assertNotIn("rock fracture", foley)
        self.assertNotIn("doors, locks", foley)

    def test_rain_scene_infers_open_rainy_exterior(self):
        profile = build_native_audio_profile({
            "framing": "Medium two-shot",
            "subject_action": "Two people stand in a puddle during steady rain.",
        })
        self.assertEqual(profile.acoustic_space, "open rainy exterior")
        self.assertIn("open-air rain", profile.ambience)

    def test_cinematic_dialogue_contract_forbids_adr_and_preserves_action_coupling(self):
        self.assertIn("never like ADR", CINEMATIC_DIALOGUE_ACOUSTIC_INTEGRATION_CONTRACT)
        self.assertIn("direct-to-ambient ratio", CINEMATIC_DIALOGUE_ACOUSTIC_INTEGRATION_CONTRACT)
        self.assertIn("turning away changes directionality", CINEMATIC_DIALOGUE_ACOUSTIC_INTEGRATION_CONTRACT)
        self.assertIn("add no new line", CINEMATIC_DIALOGUE_ACOUSTIC_INTEGRATION_CONTRACT)

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

    def test_character_action_words_do_not_false_match_vehicle_cabin(self):
        space, _ambience = infer_acoustic_space(
            "Open mountain exterior. The scarred fighter carries momentum and gains advantage "
            "while a distant helicopter crosses the sky."
        )
        self.assertEqual(space, "open rocky mountain exterior")

    def test_negative_wet_market_skill_rule_cannot_pollute_mountain_audio(self):
        profile = build_native_audio_profile({
            "framing": "Close-up",
            "subject_action": "S1 launches a solar palm on a rocky mountain cliff.",
            "environment_response": (
                "Stone fractures and sand scatters after the compressed-air detonation."
            ),
            "additional_direction": "No default wet market unless visible or explicitly requested.",
        })
        self.assertEqual(profile.acoustic_space, "open rocky mountain exterior")
        self.assertIn("exposed wind", profile.ambience)
        self.assertIn("attack air-displacement", profile.foley)
        self.assertIn("sharp contact transient", profile.foley)
        self.assertIn("compressed-air detonation", profile.foley)
        self.assertIn("rock fracture", profile.foley)
        self.assertIn("solar-corona charge", profile.foley)


if __name__ == "__main__":
    unittest.main()

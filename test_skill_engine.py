from pathlib import Path
import unittest

from media_semantic_enrichment import enrichment_fingerprint
from prompt_engine import PromptSpec
from skill_engine import (
    DEFAULT_SKILL,
    SPECIAL_SKILL,
    build_ref2va_prompt,
    load_skill_profiles,
    profile_system_prompt,
)
from workflow_engine import MediaAsset


class SkillEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = load_skill_profiles(Path(__file__).parent)

    def test_loads_default_and_special_profiles(self):
        self.assertIn(DEFAULT_SKILL, self.profiles)
        self.assertIn(SPECIAL_SKILL, self.profiles)
        folder_names = {
            folder.name
            for folder in (Path(__file__).parent / "skill special").iterdir()
            if folder.is_dir() and (folder / "SKILL.md").is_file()
        }
        discovered = {key for key, profile in self.profiles.items() if profile.special}
        self.assertEqual(discovered, folder_names)
        self.assertIn("subject_definitions", self.profiles[DEFAULT_SKILL].h3_reference_guide)
        self.assertIn("Typography Rules", self.profiles[SPECIAL_SKILL].instruction)

    def test_special_profile_metadata_comes_from_each_folder(self):
        profile = self.profiles["music-video-subtitle-generator"]
        self.assertEqual(profile.path.parent.name, "music-video-subtitle-generator")
        self.assertTrue(profile.description)
        self.assertIn("Music Video", profile.display_name)

    def test_ref_prompt_preserves_six_section_order(self):
        spec = PromptSpec(brief="A product rotates.", shots=["Hero product view", "Final hold"])
        asset = MediaAsset("1", "LoadImage", "image", "product.png", "<Picture 1>", "ref_images.ref_image_0", end_seconds=10)
        prompt = build_ref2va_prompt(spec, [asset], 10, self.profiles[DEFAULT_SKILL])
        sections = [
            "subject_definitions:",
            "summary:",
            "retention_analysis:",
            "detailed_description:",
            "overall_soundscape:",
            "non_diegetic_music:",
        ]
        positions = [prompt.index(section) for section in sections]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("[Shot 2] At 00:05.000", prompt)

    def test_repeated_timeline_uses_share_one_h3_tag_and_keep_both_ranges(self):
        spec = PromptSpec(brief="A subject returns later in the story.")
        first = MediaAsset(
            "1", "LoadImage", "image", "subject.png", "<Picture 1>",
            "ref_images.ref_image_0", timeline_placed=True,
            start_seconds=1.0, end_seconds=10.0,
        )
        second = MediaAsset(
            "1", "LoadImage", "image", "subject.png", "<Picture 1>",
            "ref_images.ref_image_0", timeline_placed=True,
            start_seconds=25.0, end_seconds=30.0,
            clip_prompt="Return from a new camera angle.",
            clip_id="clip-repeat", source_node_id="1",
        )
        prompt = build_ref2va_prompt(
            spec, [first, second], 30.0, self.profiles[DEFAULT_SKILL]
        )
        self.assertEqual(prompt.count("is a reference image"), 1)
        self.assertIn("1.00s to 10.00s, 25.00s to 30.00s", prompt)
        self.assertIn("Return from a new camera angle", prompt)
        self.assertNotIn("<Picture 2>", prompt)

    def test_structured_shot_ranges_drive_exact_detailed_description_timing(self):
        spec = PromptSpec(
            brief="A hero turns toward camera.",
            shots=["fallback shot"],
            shot_ranges=[
                {
                    "cue_id": "S1",
                    "track_id": "V1",
                    "start_seconds": 0.0,
                    "end_seconds": 3.5,
                    "description": (
                        "Hero Reveal. Medium-wide framing. Low angle camera angle. "
                        "Camera movement: Push in, slow speed, small amplitude. "
                        "Subject action: Subject turns toward camera"
                    ),
                },
                {
                    "cue_id": "S2",
                    "track_id": "V1",
                    "start_seconds": 3.5,
                    "end_seconds": 7.0,
                    "description": "Reaction Close-up. Static camera",
                },
            ],
        )
        prompt = build_ref2va_prompt(spec, [], 7.0, self.profiles[DEFAULT_SKILL])
        self.assertIn("[Shot 1 | 00:00.000-00:03.500]", prompt)
        self.assertIn("[Shot 2 | 00:03.500-00:07.000]", prompt)
        self.assertIn("Camera movement: Push in", prompt)
        self.assertNotIn("fallback shot", prompt)

    def test_structured_transitions_emit_only_at_their_own_boundary(self):
        spec = PromptSpec(
            brief="A continuous pursuit.",
            transition="Global transition one; global transition two",
            shot_ranges=[
                {"cue_id": "S1", "start_seconds": 0.0, "end_seconds": 3.0, "description": "First move"},
                {"cue_id": "S2", "start_seconds": 3.0, "end_seconds": 7.0, "description": "Second move"},
                {"cue_id": "S3", "start_seconds": 7.0, "end_seconds": 10.0, "description": "Final move"},
            ],
            transition_ranges=[
                {
                    "from_shot_id": "S1",
                    "to_shot_id": "S2",
                    "start_seconds": 3.0,
                    "description": "Whip pan through the falling leaves",
                },
                {
                    "from_shot_id": "S2",
                    "to_shot_id": "S3",
                    "start_seconds": 7.0,
                    "preset": "Spark match cut",
                    "detail": "match the sword flash to the next angle",
                },
            ],
        )
        prompt = build_ref2va_prompt(spec, [], 10.0, self.profiles[DEFAULT_SKILL])
        first_transition = prompt.index("Whip pan through the falling leaves")
        second_shot = prompt.index("[Shot 2 |")
        second_transition = prompt.index("Spark match cut: match the sword flash")
        third_shot = prompt.index("[Shot 3 |")
        self.assertLess(first_transition, second_shot)
        self.assertLess(second_shot, second_transition)
        self.assertLess(second_transition, third_shot)
        self.assertEqual(prompt.count("Whip pan through the falling leaves"), 1)
        self.assertEqual(prompt.count("Spark match cut"), 1)
        self.assertNotIn("Global transition one", prompt)

    def test_global_transition_string_remains_the_legacy_fallback(self):
        spec = PromptSpec(
            brief="Three linked shots.",
            shots=["First", "Second", "Third"],
            transition="Match the outgoing motion",
        )
        prompt = build_ref2va_prompt(spec, [], 9.0, self.profiles[DEFAULT_SKILL])
        self.assertEqual(prompt.count("Match the outgoing motion"), 2)

    def test_timestamp_transition_maps_only_to_the_nearest_boundary(self):
        spec = PromptSpec(
            brief="Three linked shots.",
            shot_ranges=[
                {"cue_id": "S1", "start_seconds": 0.0, "end_seconds": 3.0, "description": "First"},
                {"cue_id": "S2", "start_seconds": 3.0, "end_seconds": 6.0, "description": "Second"},
                {"cue_id": "S3", "start_seconds": 6.0, "end_seconds": 9.0, "description": "Third"},
            ],
            transition_ranges=[
                {"start_seconds": 5.75, "end_seconds": 6.0, "description": "Fast cut on impact"}
            ],
        )
        prompt = build_ref2va_prompt(spec, [], 9.0, self.profiles[DEFAULT_SKILL])
        self.assertGreater(prompt.index("Fast cut on impact"), prompt.index("[Shot 2 |"))
        self.assertLess(prompt.index("Fast cut on impact"), prompt.index("[Shot 3 |"))

    def test_special_profile_injects_product_rules(self):
        system = profile_system_prompt(
            self.profiles[DEFAULT_SKILL], self.profiles[SPECIAL_SKILL]
        )
        self.assertIn("DEFAULT H3 SKILL", system)
        self.assertIn("SPECIAL SCENE SKILL", system)
        self.assertIn("three independent anchor photos", system)
        prompt = build_ref2va_prompt(
            PromptSpec(brief="Show the watch.", shots=["The watch turns"]),
            [],
            5,
            self.profiles[DEFAULT_SKILL],
            self.profiles[SPECIAL_SKILL],
        )
        self.assertIn("product body color", prompt)
        self.assertIn("Around 100 BPM", prompt)

    def test_none_special_uses_only_default(self):
        system = profile_system_prompt(self.profiles[DEFAULT_SKILL], None)
        self.assertIn("SPECIAL SCENE SKILL: None", system)
        self.assertNotIn("three independent anchor photos", system)
        prompt = build_ref2va_prompt(
            PromptSpec(brief="A neutral scene.", shots=["One shot"]),
            [],
            5,
            self.profiles[DEFAULT_SKILL],
            None,
        )
        self.assertNotIn("product body color", prompt)

    def test_soundscape_and_music_presets_reach_the_six_section_prompt(self):
        prompt = build_ref2va_prompt(
            PromptSpec(
                brief="A model crosses a court.",
                shots=["One continuous shot"],
                audio="Soft tropical court ambience and synchronized footsteps.",
                music="A restrained fashion-electronic beat with no vocals.",
            ),
            [],
            6,
            self.profiles[DEFAULT_SKILL],
        )
        self.assertIn("Soft tropical court ambience", prompt)
        self.assertIn("restrained fashion-electronic beat", prompt)

    def test_media_recognition_is_embedded_as_planning_guidance(self):
        asset = MediaAsset(
            "1",
            "LoadVideo",
            "video",
            "reference.mp4",
            "<Video 1>",
            "ref_videos.ref_video_0",
            end_seconds=5,
            recognition=(
                "BLIP video frame · opening 10% @ 0.50s: a runner enters a tunnel\n"
                "Beat estimate: 120.0 BPM · confidence 0.82\n"
                "WHISPER TRANSCRIPT · cuda\n[00:00.00] Run now"
            ),
            clip_prompt="Keep the runner centered and use a low tracking angle",
        )
        prompt = build_ref2va_prompt(
            PromptSpec(brief="Follow the reference.", shots=["Track the runner"]),
            [asset],
            5,
            self.profiles[DEFAULT_SKILL],
        )
        self.assertIn("Analyzed planning guidance", prompt)
        self.assertIn("120.0 BPM", prompt)
        self.assertIn("machine transcript", prompt)
        self.assertIn("Director clip instruction", prompt)
        self.assertIn("low tracking angle", prompt)

    def test_fresh_semantic_enrichment_reaches_h3_prompt_but_stale_does_not(self):
        asset = MediaAsset(
            "1",
            "LoadImage",
            "image",
            "woman.png",
            "<Picture 1>",
            "ref_images.ref_image_0",
            end_seconds=5,
            recognition="BLIP visual caption: a woman beside a window",
            clip_prompt="Use as the subject identity reference.",
        )
        asset.semantic_enrichment = (
            "SUMMARY\nA waist-up identity reference.\n\n"
            "OBSERVED FACTS\n- Long dark hair and soft side lighting.\n\n"
            "UNCERTAIN INFERENCES (NOT OBSERVED FACTS)\n- Exact location is unknown."
        )
        asset.semantic_enrichment_source_hash = enrichment_fingerprint(
            media_id="P1",
            media_type="image",
            filename=asset.filename,
            recognition=asset.recognition,
            clip_prompt=asset.clip_prompt,
        )
        prompt = build_ref2va_prompt(
            PromptSpec(brief="Frame the subject.", shots=["Slow push in"]),
            [asset],
            5,
            self.profiles[DEFAULT_SKILL],
        )
        self.assertIn("AI semantic enrichment", prompt)
        self.assertIn("Long dark hair", prompt)
        self.assertIn("Exact location is unknown", prompt)

        asset.recognition += "\nBLIP visual caption: a newly changed source"
        stale_prompt = build_ref2va_prompt(
            PromptSpec(brief="Frame the subject.", shots=["Slow push in"]),
            [asset],
            5,
            self.profiles[DEFAULT_SKILL],
        )
        self.assertNotIn("AI semantic enrichment", stale_prompt)


if __name__ == "__main__":
    unittest.main()

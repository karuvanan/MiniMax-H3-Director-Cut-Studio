from pathlib import Path
import unittest

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
        self.assertIn("[Shot 1 · 00:00.000–00:03.500]", prompt)
        self.assertIn("[Shot 2 · 00:03.500–00:07.000]", prompt)
        self.assertIn("Camera movement: Push in", prompt)
        self.assertNotIn("fallback shot", prompt)

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


if __name__ == "__main__":
    unittest.main()

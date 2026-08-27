import unittest

from prompt_engine import (
    PromptSpec,
    build_ai_brief,
    build_structured_prompt,
    reference_tags_from_spec,
    split_shots,
    validate_prompt,
)


class PromptEngineTests(unittest.TestCase):
    def setUp(self):
        self.spec = PromptSpec(
            brief="A hero confronts a mech.",
            style="Graphic ink style",
            references="Use <Picture 1> for the hero and <Picture 2> for the mech",
            audio="Use <Audio 1> exactly as supplied",
            shots=["Top-down hero shot", "Low-angle mech shot"],
            dialogue="1|READY\n2|ROAR",
            transition="Whip pan",
            ending="Hold on the mech until <Audio 1> ends",
        )

    def test_split_shots_accepts_labels(self):
        text = "CUT 1: First shot\n\n镜头2：第二镜头"
        self.assertEqual(split_shots(text), ["First shot", "第二镜头"])

    def test_offline_prompt_has_ordered_structure(self):
        result = build_structured_prompt(self.spec)
        self.assertLess(result.index("CUT 1:"), result.index("TRANSITION:"))
        self.assertLess(result.index("TRANSITION:"), result.index("CUT 2:"))
        self.assertIn('"READY"', result)
        self.assertIn("END:", result)

    def test_dialogue_without_audio_requests_exact_native_generation(self):
        result = build_structured_prompt(self.spec)
        self.assertIn("Generate the exact spoken dialogue", result)
        self.assertIn("natural native voice", result)
        self.assertNotIn("to the supplied audio", result)

    def test_dialogue_with_audio_requests_exact_supplied_sync(self):
        self.spec.has_supplied_dialogue_audio = True
        result = build_structured_prompt(self.spec)
        self.assertIn("phoneme timing to the supplied audio", result)

    def test_validation_keeps_reference_tags(self):
        prompt = build_structured_prompt(self.spec)
        report = validate_prompt(prompt, reference_tags_from_spec(self.spec))
        self.assertEqual(report.score, 100)
        self.assertIn("所有输入的参考标签", report.as_text())

    def test_validation_detects_missing_tag(self):
        prompt = build_structured_prompt(self.spec).replace("<Picture 2>", "the mech")
        report = validate_prompt(prompt, reference_tags_from_spec(self.spec))
        self.assertLess(report.score, 100)
        self.assertIn("<Picture 2>", report.as_text())

    def test_ai_brief_is_unicode_json(self):
        brief = build_ai_brief(self.spec)
        self.assertIn("A hero confronts a mech", brief)
        self.assertIn('"cut": 2', brief)

    def test_ai_brief_serializes_structured_transition_ranges(self):
        self.spec.transition_ranges = [
            {
                "from_shot_id": "S1",
                "to_shot_id": "S2",
                "start_seconds": 3.5,
                "description": "Whip pan through the falling leaves",
            }
        ]
        brief = build_ai_brief(self.spec)
        self.assertIn('"transitions_between_shots"', brief)
        self.assertIn('"from_shot_id": "S1"', brief)
        self.assertIn("Whip pan through the falling leaves", brief)

    def test_validation_accepts_h3_ref2va_six_sections(self):
        prompt = """subject_definitions:
<Picture 1> is a reference.

summary:
[reference generation] A test.

retention_analysis:
<Picture 1>: fully_preserved - retained.

detailed_description:
[Shot 1] A product appears. Hold the final frame.

overall_soundscape:
N/A

non_diegetic_music:
N/A"""
        report = validate_prompt(prompt, {"<Picture 1>"})
        self.assertEqual(report.score, 100)
        self.assertIn("六个区段", report.as_text())


if __name__ == "__main__":
    unittest.main()

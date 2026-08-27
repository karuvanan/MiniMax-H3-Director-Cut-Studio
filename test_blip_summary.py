import unittest

from blip_summary import (
    clean_blip_caption,
    concise_blip_entries,
    remove_previous_blip_output,
    render_blip_summary,
)


class BlipSummaryTests(unittest.TestCase):
    def test_prompt_echo_is_removed_repeatedly(self):
        self.assertEqual(
            clean_blip_caption(
                "a photograph of a photograph of a woman in a chinese dress",
                "a photograph of",
            ),
            "a woman in a chinese dress",
        )

    def test_similar_regions_collapse_to_one_useful_observation(self):
        entries = concise_blip_entries([
            ("Overview", "a woman in a chinese dress"),
            ("Upper scene", "a photograph of a woman in a chinese dress"),
            ("Scene context", "the beauty of the chinese girl"),
            ("Subject detail", "the chinese lady in a traditional dress"),
        ])
        self.assertEqual(entries, [("Overview", "a woman in a chinese dress")])

    def test_region_with_new_evidence_is_preserved(self):
        entries = concise_blip_entries([
            ("Overview", "a woman in a chinese dress"),
            ("Scene context", "red lanterns beside an ancient stone courtyard"),
        ])
        self.assertEqual(len(entries), 2)

    def test_summary_shows_device_once_and_legacy_lines_are_replaceable(self):
        summary = render_blip_summary(
            [("Overview", "a woman in a chinese dress")],
            ["cuda", "cuda"],
        )
        self.assertEqual(summary.count("CUDA"), 1)
        legacy = (
            "Type: image\n\n"
            "BLIP visual caption · full frame: duplicate\n"
            "Inference device: cuda\n\n"
            + summary
        )
        cleaned = remove_previous_blip_output(legacy)
        self.assertEqual(cleaned, "Type: image")


if __name__ == "__main__":
    unittest.main()

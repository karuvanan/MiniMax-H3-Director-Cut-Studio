import json
import unittest
from pathlib import Path

from character_swap_engine import (
    SOURCE_REMAKE_MODE_CHARACTER_SWAP,
    SOURCE_REMAKE_MODE_CREATIVE_H3,
    automatic_remake_engine_for_skill,
    build_character_swap_prompt,
    character_swap_passes_for_window,
    compile_character_swap_pass,
    load_character_swap_workflow,
)
from runtime_paths import PROJECT_ROOT


class CharacterSwapEngineTests(unittest.TestCase):
    def setUp(self):
        self.template_path = (
            PROJECT_ROOT / "akatz-labs-character-swap-turbo8-adaptive-window-api.json"
        )

    def test_remake_engine_is_selected_only_from_special_skill(self):
        self.assertEqual(
            automatic_remake_engine_for_skill(""),
            SOURCE_REMAKE_MODE_CREATIVE_H3,
        )
        self.assertEqual(
            automatic_remake_engine_for_skill("none"),
            SOURCE_REMAKE_MODE_CREATIVE_H3,
        )
        self.assertEqual(
            automatic_remake_engine_for_skill("mtv-singing-h3"),
            SOURCE_REMAKE_MODE_CREATIVE_H3,
        )
        self.assertEqual(
            automatic_remake_engine_for_skill("SOURCE-VIDEO-CAST-REMAKE-H3"),
            SOURCE_REMAKE_MODE_CHARACTER_SWAP,
        )

    def test_multi_role_window_compiles_non_speaker_then_speaker(self):
        analysis = {
            "principal_roles": [
                {"role_id": "R1", "visual_identity": "woman in black", "wardrobe": "black coat"},
                {"role_id": "R2", "visual_identity": "man in white", "wardrobe": "white coat"},
            ],
            "scenes": [{
                "scene_index": 3,
                "start_seconds": 3.5,
                "end_seconds": 5.0,
                "active_source_roles": ["R1", "R2"],
                "speaker_role": "R2",
                "visible_event": "R1 watches while R2 speaks.",
            }],
        }
        passes = character_swap_passes_for_window(
            analysis,
            [
                {"source_role_id": "R1", "target_media_id": "P1", "scene_indexes": [3]},
                {"source_role_id": "R2", "target_media_id": "P2", "scene_indexes": [3]},
            ],
            3.5,
            5.0,
        )
        self.assertEqual(
            [(row["source_role_id"], row["target_media_id"]) for row in passes],
            [("R1", "P1"), ("R2", "P2")],
        )
        self.assertFalse(passes[0]["speaker"])
        self.assertTrue(passes[1]["speaker"])

    def test_compiled_pass_resets_foreign_relay_checkpoints(self):
        template = load_character_swap_workflow(self.template_path)
        prompt = build_character_swap_prompt({
            "source_role_id": "R2",
            "source_visual_identity": "man in a white coat",
            "source_wardrobe": "white coat",
            "source_events": ["standing on the right and speaking"],
        })
        workflow, contract = compile_character_swap_pass(
            template,
            source_filename="source.mp4",
            reference_filename="p2.png",
            prompt=prompt,
            seed=123,
            megapixels=1.0,
            output_prefix="studio/s2_r2",
            runtime_source=True,
        )
        relay = workflow[contract["relay_node_id"]]["inputs"]
        character_loras = [
            str(node.get("inputs", {}).get("lora_name", ""))
            for node in workflow.values()
            if node.get("class_type") == "LoraLoaderModelOnly"
            and "character_swap" in str(
                node.get("inputs", {}).get("lora_name", "")
            ).replace("-", "_")
        ]
        self.assertEqual(character_loras, ["h3_character_swap_v1.5.safetensors"])
        self.assertEqual(relay["window_controls"], "{}")
        self.assertEqual(relay["window_frames"], "124")
        self.assertEqual(relay["history_frames"], "18")
        self.assertEqual(relay["steps"], 8)
        self.assertEqual(
            workflow[contract["source_loader_node_id"]]["inputs"]["file"],
            "__H3_RELAY_PREVIOUS_PASS__.mp4",
        )
        prepare = next(
            row for row in workflow.values()
            if row.get("class_type") == "LabsH3PrepareVideo"
        )
        self.assertEqual(prepare["inputs"]["resolution"], "768")
        self.assertIn("Do not replace", prompt)
        self.assertIn("visible mouth timing", prompt)
        self.assertIn("<Picture 1> supplies identity only", prompt)
        self.assertIn("Never import Picture 1's room", prompt)
        self.assertIn("The final face must be recognisably", prompt)
        self.assertLess(len(prompt), 4000)

    def test_duplicate_picture_roles_compile_as_one_spatially_identified_pass(self):
        analysis = {
            "principal_roles": [
                {
                    "role_id": "R1",
                    "visual_identity": "man in a gold robe",
                    "wardrobe": "gold robe",
                    "narrative_function": "central lead",
                    "thumbnail_bbox_normalized": [0.45, 0.2, 0.6, 0.7],
                },
                {
                    "role_id": "R2",
                    "visual_identity": "girl in a blue dress",
                    "wardrobe": "blue dress",
                    "narrative_function": "foreground left dancer",
                    "thumbnail_bbox_normalized": [0.2, 0.3, 0.4, 0.8],
                },
            ],
            "scenes": [{
                "scene_index": 1,
                "start_seconds": 0.0,
                "end_seconds": 10.0,
                "active_source_roles": ["R1", "R2"],
                "speaker_role": "",
                "visible_event": "Both performers dance.",
            }],
        }
        passes = character_swap_passes_for_window(
            analysis,
            [
                {"source_role_id": "R1", "target_media_id": "P4", "scene_indexes": [1]},
                {"source_role_id": "R2", "target_media_id": "P4", "scene_indexes": [1]},
            ],
            0.0,
            10.0,
        )

        self.assertEqual(len(passes), 1)
        self.assertEqual(passes[0]["source_role_ids"], ["R1", "R2"])
        self.assertEqual(passes[0]["target_media_id"], "P4")
        prompt = build_character_swap_prompt(passes[0])
        self.assertIn("2 distinct selected source performers", prompt)
        self.assertIn("central lead", prompt)
        self.assertIn("foreground left dancer", prompt)
        self.assertIn("x=45-60%", prompt)
        self.assertIn("separate bodies", prompt)

    def test_illustrated_reference_can_be_adapted_as_live_action_identity(self):
        prompt = build_character_swap_prompt(
            {
                "source_role_id": "R1",
                "source_visual_identity": "lead singer under stage lights",
                "source_wardrobe": "black concert jacket",
                "source_events": ["raises sunglasses toward his face"],
            },
            live_action_adaptation=True,
        )

        self.assertIn("ILLUSTRATED-CAST TO LIVE-ACTION CONTRACT", prompt)
        self.assertIn("physically plausible live-action human", prompt)
        self.assertIn("moustache or facial-hair design", prompt)
        self.assertIn("Match Video 1 exposure", prompt)
        self.assertIn("No pasted cartoon head", prompt)
        self.assertIn("FINAL MEDIUM PRIORITY", prompt)


if __name__ == "__main__":
    unittest.main()

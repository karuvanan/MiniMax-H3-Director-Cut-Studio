import unittest

from smart_cut_engine import (
    build_dependency_graph,
    normalize_lm_hints,
    plan_smart_cut,
    smart_cut_lm_schema,
    smart_cut_lm_prompts,
)


def shot(shot_id, start, end, preset, *, action="", optional="", speech=0.0, media=None, continuity=""):
    return {
        "cue_id": shot_id,
        "start_seconds": start,
        "end_seconds": end,
        "preset": preset,
        "subject_action": action,
        "optional_flourish": optional,
        "speech_duration": speech,
        "speech_count": 1 if speech else 0,
        "explicit_speech": bool(speech),
        "media_ids": list(media or []),
        "continuity_state": continuity,
        "track_id": "V1",
    }


class SmartCutEngineTests(unittest.TestCase):
    def test_balanced_plan_hits_grid_target_without_cutting_dialogue(self):
        rows = [
            shot("S1", 0, 5, "Opening Hook", action="Woman receives an impossible alert.", speech=3.5),
            shot("S2", 5, 10, "Reaction", optional="Long silent reaction and decorative push-in."),
            shot("S3", 10, 15, "Reveal", action="The monitor reveals the duplicate.", speech=3.0),
        ]
        plan = plan_smart_cut(rows, 12.0, mode="balanced")
        self.assertEqual(plan["edited_duration"], 12.0)
        self.assertTrue(plan["on_target"])
        by_id = {row["shot_id"]: row for row in plan["decisions"]}
        self.assertNotIn(by_id["S1"]["action"], {"remove", "merge"})
        self.assertNotIn(by_id["S3"]["action"], {"remove", "merge"})
        self.assertGreaterEqual(by_id["S1"]["proposed_duration"], 3.5)

    def test_dependency_graph_protects_shared_media_and_continuity(self):
        rows = [
            shot("S1", 0, 5, "Clue", continuity="S1 holds the cracked red umbrella", media=["P1", "P4"]),
            shot("S2", 5, 10, "Bridge", action="She enters the lift holding the cracked red umbrella", media=["P1", "P4"]),
        ]
        edges = build_dependency_graph(rows)
        self.assertEqual(len(edges), 1)
        self.assertGreaterEqual(edges[0]["strength"], 5)
        self.assertTrue(any("shared references" in reason for reason in edges[0]["reasons"]))

    def test_redundant_optional_shot_becomes_merge_not_silent_delete(self):
        rows = [
            shot("S1", 0, 5, "Opening Hook", action="Woman studies the monitor.", media=["P1"]),
            shot("S2", 5, 10, "Reaction", action="Woman studies the monitor again.", optional="Repeated reaction.", media=["P1"]),
            shot("S3", 10, 15, "Final Hook", action="The duplicate turns toward camera.", media=["P2"]),
        ]
        hints = {"S2": {"story_role": "optional", "importance_delta": -15, "redundancy_with": "S1"}}
        plan = plan_smart_cut(rows, 10.0, mode="aggressive", semantic_hints=hints)
        decision = next(row for row in plan["decisions"] if row["shot_id"] == "S2")
        self.assertEqual(decision["action"], "merge")
        self.assertEqual(decision["merge_into"], "S1")

    def test_lm_hints_are_bounded_and_cannot_author_timings(self):
        hints = normalize_lm_hints({"shots": [{
            "shot_id": "S1",
            "story_role": "delete_everything",
            "importance_delta": -999,
            "redundancy_with": "S1",
            "protect": True,
            "reason": " useful   clue ",
            "proposed_duration": 0,
        }]}, ["S1"])
        self.assertEqual(hints["S1"]["story_role"], "bridge")
        self.assertEqual(hints["S1"]["importance_delta"], -15.0)
        self.assertEqual(hints["S1"]["redundancy_with"], "")
        self.assertNotIn("proposed_duration", hints["S1"])
        self.assertTrue(hints["S1"]["protect"])

    def test_impossible_speech_target_returns_warning_instead_of_cutting_words(self):
        rows = [
            shot("S1", 0, 7, "Opening Hook", speech=6.5),
            shot("S2", 7, 15, "Final Hook", speech=7.5),
        ]
        plan = plan_smart_cut(rows, 10.0, mode="aggressive")
        self.assertGreater(plan["edited_duration"], 10.0)
        self.assertTrue(plan["warnings"])
        self.assertTrue(all(row["proposed_duration"] >= row["speech_duration"] for row in plan["decisions"]))

    def test_lm_cannot_demote_an_explicit_clue_to_optional(self):
        rows = [
            shot("S1", 0, 5, "Opening Hook", action="The warning appears."),
            shot("S2", 5, 10, "Clue Evidence", action="She finds the cracked access card."),
            shot("S3", 10, 15, "Final Hook", action="The duplicate looks back."),
        ]
        plan = plan_smart_cut(
            rows,
            10.0,
            mode="aggressive",
            semantic_hints={"S2": {
                "story_role": "optional", "importance_delta": -15,
                "redundancy_with": "S1", "protect": False,
            }},
        )
        decision = next(row for row in plan["decisions"] if row["shot_id"] == "S2")
        self.assertEqual(decision["story_role"], "clue")
        self.assertTrue(decision["protected"])
        self.assertNotIn(decision["action"], {"remove", "merge"})

    def test_lm_schema_and_prompt_do_not_delegate_timeline_authority(self):
        schema = smart_cut_lm_schema()
        system, user = smart_cut_lm_prompts(
            [shot("S1", 0, 5, "Opening Hook")], 4.0
        )
        self.assertIn("shots", schema["required"])
        self.assertNotIn("proposed_duration", str(schema))
        self.assertIn("deterministic", system.lower())
        self.assertIn("4.00s", user)


if __name__ == "__main__":
    unittest.main()

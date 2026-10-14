import json
import unittest

from timeline_assistant_engine import (
    TIMELINE_ASSISTANT_SCHEMA,
    affected_shot_ids,
    build_timeline_assistant_prompts,
    parse_assistant_response,
    validate_operations,
)


class TimelineAssistantEngineTests(unittest.TestCase):
    def test_schema_is_strict_and_structured(self):
        self.assertFalse(TIMELINE_ASSISTANT_SCHEMA["additionalProperties"])
        self.assertIn("operations", TIMELINE_ASSISTANT_SCHEMA["required"])
        operation = TIMELINE_ASSISTANT_SCHEMA["properties"]["operations"]["items"]
        self.assertFalse(operation["additionalProperties"])
        self.assertIn("value_json", operation["required"])

    def test_parser_drops_unknown_fields_and_forces_confirmation(self):
        proposal = parse_assistant_response({
            "summary": "Keep S8 silent",
            "scope": "linked_continuity",
            "warnings": [],
            "operations": [
                {
                    "target_kind": "shot",
                    "target_id": "S8",
                    "field": "speech_visual_mode",
                    "value_json": json.dumps("silent_listener"),
                    "reason": "The voice is behind camera",
                    "risk_level": "safe",
                    "requires_confirmation": False,
                },
                {
                    "target_kind": "text_layer",
                    "target_id": "T1",
                    "field": "text",
                    "value_json": json.dumps("changed words"),
                    "reason": "Rewrite",
                    "risk_level": "safe",
                    "requires_confirmation": False,
                },
                {
                    "target_kind": "shot",
                    "target_id": "S8",
                    "field": "not_a_real_field",
                    "value_json": "1",
                    "reason": "hallucinated",
                    "risk_level": "safe",
                    "requires_confirmation": False,
                },
            ],
        })
        self.assertEqual(len(proposal["operations"]), 2)
        self.assertEqual(proposal["operations"][0]["value"], "silent_listener")
        self.assertTrue(proposal["operations"][1]["requires_confirmation"])

    def test_validator_rejects_unknown_and_duplicate_targets(self):
        proposal = parse_assistant_response({
            "summary": "",
            "scope": "shot_only",
            "warnings": [],
            "operations": [
                {
                    "target_kind": "shot", "target_id": "S8", "field": "framing",
                    "value_json": json.dumps("Close-up"), "reason": "face",
                    "risk_level": "safe", "requires_confirmation": False,
                },
                {
                    "target_kind": "shot", "target_id": "S8", "field": "framing",
                    "value_json": json.dumps("Wide"), "reason": "duplicate",
                    "risk_level": "safe", "requires_confirmation": False,
                },
                {
                    "target_kind": "shot", "target_id": "S99", "field": "framing",
                    "value_json": json.dumps("Wide"), "reason": "unknown",
                    "risk_level": "safe", "requires_confirmation": False,
                },
            ],
        })
        accepted, rejected = validate_operations(
            proposal, shot_ids=["S8"], text_layer_ids=[], track_ids=[]
        )
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(rejected), 2)

    def test_prompt_contains_neighbor_state_and_no_compiled_prompt_rewrite(self):
        system, user = build_timeline_assistant_prompts(
            request="Add rain impact to S2",
            scope="linked_continuity",
            target_shot_id="S2",
            shots=[
                {"cue_id": "S1", "start_seconds": 0, "end_seconds": 5,
                 "outgoing_environment_state": "dry"},
                {"cue_id": "S2", "start_seconds": 5, "end_seconds": 10,
                 "incoming_environment_state": "dry"},
                {"cue_id": "S3", "start_seconds": 10, "end_seconds": 15,
                 "incoming_environment_state": "wet"},
            ],
            text_layers=[],
            tracks=[],
            work_area={"start_seconds": 0, "end_seconds": 15},
        )
        self.assertIn("Never rewrite a compiled H3 prompt", system)
        self.assertIn('"target_shot_id": "S2"', user)
        self.assertIn('"cue_id": "S1"', user)
        self.assertIn('"cue_id": "S3"', user)

    def test_affected_shots_resolve_text_binding(self):
        result = affected_shot_ids(
            [
                {"target_kind": "shot", "target_id": "S2"},
                {"target_kind": "text_layer", "target_id": "T4"},
            ],
            text_layers=[{"layer_id": "T4", "shot_id": "S3"}],
        )
        self.assertEqual(result, {"S2", "S3"})


if __name__ == "__main__":
    unittest.main()


import unittest
from copy import deepcopy

from combat_environment_engine import (
    CAUSALITY_CONTRACT,
    ENVIRONMENT_PHYSICS_SCHEMA_VERSION,
    INDOOR_PLATE_ID,
    LEGACY_PLATE_ID,
    OUTDOOR_PLATE_ID,
    apply_environmental_combat_physics,
    environmental_combat_prompt_clause,
    environment_transition_time,
    reconcile_environmental_combat_rows,
)


def shot(shot_id, start, end, action):
    return {
        "id": shot_id,
        "start_seconds": start,
        "end_seconds": end,
        "subject_action": action,
        "environment_response": "",
        "continuity_state": "",
        "additional_direction": "",
    }


class EnvironmentalCombatEngineTests(unittest.TestCase):
    def test_default_transition_is_thirty_seconds(self):
        self.assertEqual(environment_transition_time(45.0), 30.0)

    def test_non_street_fighter_plan_is_unchanged(self):
        original = {"duration_seconds": 5.0, "shots": [shot("S1", 0, 5, "A quiet room.")]}
        plan = deepcopy(original)
        returned = apply_environmental_combat_physics(plan, special_skill_key="")
        self.assertIs(returned, plan)
        self.assertEqual(returned, original)

    def test_contact_creates_ordered_bounded_response_and_persistent_state(self):
        rows, warnings = reconcile_environmental_combat_rows(
            [
                shot("S1", 0.0, 5.0, "S1 checks S2's kick and counters with a foot sweep."),
                shot("S2", 5.0, 10.0, "S2 uses a clinch throw against S1."),
                shot("S3", 16.0, 19.0, "S1 parries and drives S2 into a seafood tray."),
                shot("S4", 30.0, 35.0, "S2 lands a controlled takedown in the alley."),
            ],
            45.0,
        )
        self.assertFalse(warnings)
        first = rows[0]
        self.assertIn("cause_actor=S1", first["environment_interaction"])
        self.assertIn("contact_target_id=env_", first["environment_interaction"])
        self.assertIn("contact_time=", first["environment_interaction"])
        self.assertIn("primary_response=", first["environment_interaction"])
        self.assertEqual(first["environment_interaction"].count("secondary_response="), 1)
        self.assertIn("after the visible contact", first["crowd_reaction"])
        self.assertIn("Location=indoor_seafood_aisle", first["incoming_environment_state"])
        self.assertIn("Location=fish_vegetable_junction", rows[2]["incoming_environment_state"])
        self.assertIn("persistent state:", rows[2]["outgoing_environment_state"])
        self.assertIn("Location=outdoor_rain_alley", rows[3]["incoming_environment_state"])
        self.assertIn("OUTDOOR CONTINUATION", rows[3]["location_transition"])

    def test_shot_without_combat_contact_cannot_create_destruction(self):
        rows, warnings = reconcile_environmental_combat_rows(
            [shot("S1", 0.0, 5.0, "P1 and P2 stand still and look at the market.")],
            45.0,
        )
        self.assertEqual(rows[0]["environment_interaction"], "")
        self.assertEqual(rows[0]["crowd_reaction"], "")
        self.assertNotIn("persistent state:", rows[0]["outgoing_environment_state"])
        self.assertEqual(rows[0]["environment_state_status"], "continuous")
        self.assertEqual(warnings, [])
        self.assertIn("no object moves or breaks", rows[0]["event_causality_chain"])

    def test_user_authored_environment_effect_without_cause_stays_red_risk(self):
        value = shot("S1", 0.0, 5.0, "P1 and P2 hold a stable final guard.")
        value["environment_interaction"] = "A metal gate explodes outward."
        value["environment_interaction_user_edited"] = True
        rows, warnings = reconcile_environmental_combat_rows([value], 45.0)
        self.assertEqual(rows[0]["environment_state_status"], "warning")
        self.assertEqual(rows[0]["environment_interaction"], "A metal gate explodes outward.")
        self.assertEqual(len(warnings), 1)

    def test_submission_release_gets_subtle_physical_feedback_auto_fix(self):
        rows, warnings = reconcile_environmental_combat_rows(
            [shot("S1", 42.5, 45.0, "S1 releases the choke and resets to guarded pressure.")],
            45.0,
        )
        self.assertFalse(warnings)
        self.assertIn("cause_actor=S1", rows[0]["environment_interaction"])
        self.assertIn("puddle", rows[0]["environment_interaction"])
        self.assertEqual(rows[0]["causal_risk_repair_status"], "auto_fixed")
        self.assertIn("EVENT CAUSE", rows[0]["event_causality_chain"])
        self.assertIn("PHYSICAL FEEDBACK", rows[0]["physical_feedback_chain"])

    def test_user_overrides_are_preserved_during_reconciliation(self):
        value = shot("S1", 0.0, 5.0, "S1 blocks a kick from S2.")
        value.update({
            "environment_interaction": "USER CONTACT",
            "environment_interaction_user_edited": True,
            "crowd_reaction": "USER CROWD",
            "crowd_reaction_user_edited": True,
            "incoming_environment_state": "USER IN",
            "incoming_environment_state_user_edited": True,
            "outgoing_environment_state": "USER OUT",
            "outgoing_environment_state_user_edited": True,
            "location_transition": "USER ROUTE",
            "location_transition_user_edited": True,
        })
        rows, _ = reconcile_environmental_combat_rows([value], 45.0)
        result = rows[0]
        self.assertEqual(result["environment_interaction"], "USER CONTACT")
        self.assertEqual(result["crowd_reaction"], "USER CROWD")
        self.assertEqual(result["incoming_environment_state"], "USER IN")
        self.assertEqual(result["outgoing_environment_state"], "USER OUT")
        self.assertEqual(result["location_transition"], "USER ROUTE")

    def test_two_time_scoped_plates_replace_legacy_plate(self):
        plan = {
            "duration_seconds": 45.0,
            "constraints": "",
            "shots": [shot("S1", 0.0, 45.0, "S1 and S2 exchange kicks and throws.")],
            "existing_media_uses": [{"requirement_id": LEGACY_PLATE_ID, "media_id": "P3"}],
            "media_requests": [{"requirement_id": LEGACY_PLATE_ID, "media_type": "image"}],
        }
        apply_environmental_combat_physics(
            plan, special_skill_key="street-fighter-live-action-h3"
        )
        self.assertEqual(plan["environment_physics_schema_version"], ENVIRONMENT_PHYSICS_SCHEMA_VERSION)
        self.assertEqual(plan["environment_transition_time_seconds"], 30.0)
        uses = {row["requirement_id"]: row for row in plan["existing_media_uses"]}
        self.assertIn(INDOOR_PLATE_ID, uses)
        self.assertEqual((uses[INDOOR_PLATE_ID]["start_seconds"], uses[INDOOR_PLATE_ID]["end_seconds"]), (0.0, 30.0))
        requests = {row["requirement_id"]: row for row in plan["media_requests"]}
        self.assertEqual(set(requests), {OUTDOOR_PLATE_ID})
        self.assertEqual((requests[OUTDOOR_PLATE_ID]["start_seconds"], requests[OUTDOOR_PLATE_ID]["end_seconds"]), (30.0, 45.0))
        self.assertNotIn(LEGACY_PLATE_ID, str(plan))

    def test_new_plan_installs_exactly_two_environment_plates_idempotently(self):
        plan = {
            "duration_seconds": 45.0,
            "constraints": "",
            "shots": [shot("S1", 0.0, 45.0, "S1 blocks, clinches and throws S2.")],
            "existing_media_uses": [],
            "media_requests": [],
        }
        for _ in range(2):
            apply_environmental_combat_physics(
                plan, special_skill_key="street-fighter-live-action-h3"
            )
        requests = plan["media_requests"]
        self.assertEqual([row["requirement_id"] for row in requests], [INDOOR_PLATE_ID, OUTDOOR_PLATE_ID])
        self.assertEqual(str(plan["constraints"]).count(CAUSALITY_CONTRACT), 1)
        self.assertEqual(plan["shots"][0]["environment_response"].count("[ENV-PHYSICS]"), 1)

    def test_speech_extension_does_not_move_authored_environment_threshold(self):
        plan = {
            "duration_seconds": 48.5,
            "_speech_timing_base_duration": 45.0,
            "constraints": "",
            "shots": [shot("S1", 27.5, 30.0, "S1 drives S2 through the market gate latch.")],
            "existing_media_uses": [],
            "media_requests": [],
        }
        apply_environmental_combat_physics(
            plan, special_skill_key="street-fighter-live-action-h3"
        )
        self.assertEqual(plan["environment_transition_time_seconds"], 30.0)
        requests = {row["requirement_id"]: row for row in plan["media_requests"]}
        self.assertEqual(requests[INDOOR_PLATE_ID]["end_seconds"], 30.0)
        self.assertEqual(requests[OUTDOOR_PLATE_ID]["start_seconds"], 30.0)
        self.assertEqual(requests[OUTDOOR_PLATE_ID]["end_seconds"], 48.5)
        self.assertIn("metal market gate and latch", plan["shots"][0]["environment_interaction"])

    def test_authored_stall_contact_overrides_round_robin_target(self):
        rows, _ = reconcile_environmental_combat_rows(
            [shot("S5", 10.0, 12.5, "S2 drives S1's shoulder into the metal stall panel.")],
            45.0,
        )
        self.assertIn("aged metal stall side panel", rows[0]["environment_interaction"])

    def test_real_h3_clause_contains_all_environment_fields(self):
        rows, _ = reconcile_environmental_combat_rows(
            [shot("S1", 29.0, 31.0, "S1 clinches and throws S2 through the market gate.")],
            45.0,
        )
        clause = environmental_combat_prompt_clause(rows[0])
        for phrase in (
            "ENVIRONMENT INTERACTION",
            "CROWD REACTION",
            "INCOMING ENVIRONMENT STATE",
            "OUTGOING ENVIRONMENT STATE",
            "LOCATION TRANSITION",
            "No spontaneous damage",
            "EVENT CAUSALITY",
            "PHYSICAL FEEDBACK",
        ):
            self.assertIn(phrase, clause)

    def test_material_response_follows_structured_force_vector(self):
        row = shot("S1", 0.0, 5.0, "S1 drives S2 into the metal stall panel")
        row["combat_force_vector"] = {
            "horizontal": "screen-left", "vertical": "downward", "depth": "forward",
            "magnitude": "heavy", "label": "screen-left, downward, forward",
        }
        rows, warnings = reconcile_environmental_combat_rows([row], 45.0)
        self.assertFalse(warnings)
        self.assertEqual(rows[0]["contact_material"], "aged_metal")
        self.assertIn("force_direction=screen-left, downward, forward", rows[0]["environment_interaction"])
        self.assertIn("responds along screen-left, downward, forward", rows[0]["environment_interaction"])
        self.assertEqual(rows[0]["environment_force_vector"]["magnitude"], "heavy")

    def test_environment_updates_combat_aftermath_without_rewriting_user_state(self):
        row = shot("S1", 0.0, 5.0, "S1 drives S2 into the fish tank support frame")
        row["outgoing_combat_state_vector"] = {
            "positions": "S1 left; S2 right", "facing": "mutual", "velocity": "forward",
            "support": "grounded", "guard_or_grip": "open", "advantage": "S1",
            "environment_aftermath": "pending",
        }
        rows, _ = reconcile_environmental_combat_rows([row], 45.0)
        self.assertIn("fish-tank support frame", rows[0]["outgoing_combat_state_vector"]["environment_aftermath"])


if __name__ == "__main__":
    unittest.main()

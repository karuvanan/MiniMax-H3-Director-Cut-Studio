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
    HONG_KONG_COMIC_FIGHTER_SKILL,
    REFERENCE_WORLD_CAUSALITY_CONTRACT,
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

    def test_hong_kong_comic_world_uses_picture_environment_and_never_installs_market_plates(self):
        plan = {
            "duration_seconds": 12.0,
            "creative_brief": "Two legendary fighters collide on the source mountain.",
            "global_visual_style": "Photoreal rocky cliff beneath a blue sky.",
            "constraints": "",
            "shots": [shot("S1", 0.0, 6.0, "S1 drives an electric palm into S2's counter fist."),
                      shot("S2", 6.0, 12.0, "S2 redirects the force and S1 recoils across loose rock.")],
            "existing_media_uses": [],
            "media_requests": [],
        }
        media = [{
            "media_id": "P1", "media_type": "image", "loaded": True,
            "raw_analysis_summary": "BLIP · Overview: two martial artists on a rocky mountain cliff under a blue sky",
        }, {
            "media_id": "P4", "media_type": "image", "loaded": True,
            "local_path": "project/media/generated_references/old_market.png",
            "recognition": "AI DESIGN GENERATED REFERENCE; Hong Kong wet market with fish tanks",
        }]
        apply_environmental_combat_physics(
            plan,
            special_skill_key=HONG_KONG_COMIC_FIGHTER_SKILL,
            existing_media=media,
            authored_requirement=(
                "world-class power distorts air and drives dust through the mountain scene; "
                "加入太阳招式、超级英雄光效和真实动态阴影"
            ),
        )
        self.assertEqual(plan["media_requests"], [])
        self.assertEqual(plan["reference_environment_fact_ledger"]["location"], "rocky mountain or cliff terrain")
        self.assertEqual([row["media_id"] for row in plan["reference_environment_fact_ledger"]["source_evidence"]], ["P1"])
        rendered = str(plan)
        self.assertIn("localized space-lensing", rendered)
        self.assertIn("compressed-air detonation", rendered)
        self.assertIn("rock face and ground strata crack", rendered)
        self.assertIn("white-gold corona", rendered)
        self.assertIn("moving hard-edged shadows", rendered)
        self.assertIn("deep localized crater", rendered)
        self.assertIn("three readable depth layers", rendered)
        self.assertIn("no lens zoom", rendered)
        self.assertTrue(plan["reference_environment_fact_ledger"]["solar_signature_requested"])
        self.assertIn(REFERENCE_WORLD_CAUSALITY_CONTRACT, plan["constraints"])
        self.assertNotIn("fish tank", rendered.casefold())
        self.assertNotIn("indoor_seafood_aisle", rendered)
        self.assertNotIn(INDOOR_PLATE_ID, rendered)

    def test_hong_kong_comic_final_settle_preserves_aftermath_without_new_blast(self):
        plan = {
            "duration_seconds": 5.0,
            "constraints": "",
            "shots": [shot(
                "S1", 0.0, 5.0,
                "FINAL SETTLE: both fighters hold a readable supported stance; no new attack.",
            )],
            "existing_media_uses": [],
            "media_requests": [],
        }
        apply_environmental_combat_physics(
            plan,
            special_skill_key=HONG_KONG_COMIC_FIGHTER_SKILL,
            existing_media=[{
                "media_id": "P1", "media_type": "image", "loaded": True,
                "raw_analysis_summary": "rocky mountain, gravel and sand beneath storm clouds",
            }],
        )
        result = plan["shots"][0]
        self.assertIn("AFTERMATH ONLY", result["environment_response"])
        self.assertIn("no new strike or explosion", result["event_causality_chain"])
        self.assertNotIn("force_magnitude=world-class", result["environment_interaction"])

    def test_hong_kong_comic_final_strike_then_settle_keeps_world_response(self):
        plan = {
            "duration_seconds": 5.0,
            "constraints": "",
            "shots": [shot(
                "S1", 0.0, 5.0,
                "S1 releases a solar palm; it contacts S2 and drives him backward. "
                "FINAL SETTLE: both fighters recover to stable support; no new attack.",
            )],
            "existing_media_uses": [],
            "media_requests": [],
        }
        apply_environmental_combat_physics(
            plan,
            special_skill_key=HONG_KONG_COMIC_FIGHTER_SKILL,
            existing_media=[{
                "media_id": "P1", "media_type": "image", "loaded": True,
                "raw_analysis_summary": "rocky mountain, gravel and sand beneath storm clouds",
            }],
            authored_requirement="加入太阳招式",
        )
        result = plan["shots"][0]
        self.assertNotIn("AFTERMATH ONLY", result["environment_response"])
        self.assertIn("force_magnitude=world-class", result["environment_interaction"])
        self.assertIn("white-gold corona", result["environment_interaction"])

    def test_hong_kong_power_field_is_present_from_first_shot(self):
        plan = {
            "duration_seconds": 12.0, "constraints": "",
            "shots": [
                shot("S1", 0.0, 3.0, "S1 drives a palm into S2's guard."),
                shot("S2", 3.0, 6.0, "S2 kicks and S1 checks the kick."),
            ],
            "existing_media_uses": [], "media_requests": [{
                "requirement_id": "early_action", "media_type": "image",
                "reuse_policy": "time_scoped", "start_seconds": 0.0, "end_seconds": 3.0,
                "prompt": "Photoreal frozen action state: two fighters clash on the source mountain."
            }],
        }
        apply_environmental_combat_physics(
            plan, special_skill_key=HONG_KONG_COMIC_FIGHTER_SKILL,
            existing_media=[{"media_id": "P1", "media_type": "image", "loaded": True,
                             "raw_analysis_summary": "rocky mountain with gravel and storm clouds"}],
        )
        self.assertIn("CONTINUOUS LEGENDARY POWER FIELD", plan["shots"][0]["continuous_power_field"])
        self.assertIn("continuous_power_field=", plan["shots"][0]["environment_interaction"])
        self.assertIn("CONTINUOUS LEGENDARY POWER FIELD", plan["media_requests"][0]["prompt"])
        self.assertIn("no ordinary unpowered punch", plan["media_requests"][0]["prompt"])

    def test_hong_kong_power_field_keeps_identity_anchor_clean(self):
        plan = {
            "duration_seconds": 5.0, "constraints": "", "shots": [],
            "existing_media_uses": [], "media_requests": [{
                "requirement_id": "identity", "media_type": "image",
                "reuse_policy": "whole_design", "identity_anchor": True,
                "prompt": "PRIMARY RECURRING CHARACTER IDENTITY ANCHOR. One clear face."
            }],
        }
        apply_environmental_combat_physics(
            plan, special_skill_key=HONG_KONG_COMIC_FIGHTER_SKILL,
            existing_media=[{"media_id": "P1", "media_type": "image", "loaded": True,
                             "raw_analysis_summary": "rocky mountain"}],
        )
        self.assertNotIn("CONTINUOUS LEGENDARY POWER FIELD", plan["media_requests"][0]["prompt"])

    def test_hong_kong_comic_environment_changes_with_source_evidence(self):
        plan = {
            "duration_seconds": 6.0, "constraints": "",
            "shots": [shot("S1", 0.0, 6.0, "S1 kicks; S2 checks and counters.")],
            "existing_media_uses": [], "media_requests": [],
        }
        apply_environmental_combat_physics(
            plan,
            special_skill_key=HONG_KONG_COMIC_FIGHTER_SKILL,
            existing_media=[{
                "media_id": "P4", "media_type": "image", "loaded": True,
                "raw_analysis_summary": "BLIP · Overview: fighters beside a stormy open sea",
            }],
        )
        self.assertEqual(plan["reference_environment_fact_ledger"]["location"], "open waterside terrain")
        self.assertIn("water surface", plan["shots"][0]["environment_interaction"])
        self.assertNotIn("Kowloon", plan["shots"][0]["environment_interaction"])

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

import unittest
from copy import deepcopy

from combat_action_engine import (
    ACTION_CAUSALITY_CONTRACT,
    COMBAT_ACTION_SCHEMA_VERSION,
    apply_combat_action_continuity,
    combat_action_prompt_clause,
    combat_baseline_duration,
    compact_street_fighter_prompt_field,
    reconcile_combat_action_rows,
    build_combat_fact_ledger,
    combat_fact_prompt_context,
    route_action_carrier,
    infer_force_vector,
    HONG_KONG_COMIC_FIGHTER_SKILL,
    reconcile_final_combat_markers,
)


def shot(index, start, end, action):
    return {
        "id": f"S{index}",
        "start_seconds": start,
        "end_seconds": end,
        "subject_action": action,
    }


class CombatActionEngineTests(unittest.TestCase):
    def test_other_skills_are_unchanged(self):
        original = {"duration_seconds": 5.0, "shots": [shot(1, 0, 5, "S1 looks at S2.")]}
        plan = deepcopy(original)
        self.assertIs(
            apply_combat_action_continuity(plan, special_skill_key="dark-rescue-h3"),
            plan,
        )
        self.assertEqual(plan, original)

    def test_six_shots_become_twelve_numbered_causal_beats(self):
        rows = [
            shot(index + 1, index * 2.5, (index + 1) * 2.5,
                 "S1 launches a low kick at S2. S2 checks the kick and pivots outside.")
            for index in range(6)
        ]
        result, warnings = reconcile_combat_action_rows(rows, 15.0)
        self.assertEqual(len(result), 6)
        rendered = " ".join(row["subject_action"] for row in result)
        self.assertEqual(rendered.count("[BEAT "), 12)
        self.assertIn("[BEAT 12", rendered)
        self.assertFalse(any("self-defence" in warning for warning in warnings))
        self.assertEqual(result[1]["incoming_combat_state"], result[0]["outgoing_combat_state"])
        self.assertIn("directly triggers BEAT 03", result[0]["next_action_trigger"])

    def test_clear_self_defence_actor_is_auto_fixed(self):
        rows, warnings = reconcile_combat_action_rows(
            [shot(1, 0, 2.5, "S2 kicks toward S1. S2 parries and pivots away.")],
            2.5,
        )
        self.assertIn("S1 parries", rows[0]["subject_action"])
        self.assertEqual(rows[0]["combat_continuity_status"], "auto_fixed")
        self.assertTrue(any("self-defence" in warning for warning in warnings))

    def test_unexplained_ground_ownership_change_is_auto_fixed(self):
        rows, warnings = reconcile_combat_action_rows(
            [
                shot(1, 0, 2.5, "S2 captures S1's single leg. S1 sprawls and frames."),
                shot(2, 2.5, 5.0, "S1 establishes side control. S2 frames from below."),
            ],
            5.0,
        )
        self.assertEqual(rows[1]["combat_continuity_status"], "auto_fixed")
        self.assertIn("hip-escapes", rows[1]["subject_action"])
        self.assertTrue(any("explicit ground reversal" in warning for warning in warnings))

    def test_repeated_action_is_replaced_with_causal_continuation(self):
        rows, warnings = reconcile_combat_action_rows(
            [
                shot(1, 0, 2.5, "S1 attacks S2. S2 blocks and counters."),
                shot(2, 2.5, 5.0, "S1 attacks S2. S2 blocks and counters."),
            ],
            5.0,
        )
        self.assertEqual(rows[1]["combat_continuity_status"], "auto_fixed")
        self.assertIn("causal continuation", rows[1]["causal_risk_repair_notes"])
        self.assertNotEqual(rows[0]["subject_action"], rows[1]["subject_action"])
        self.assertTrue(any("replaced repeated action" in warning for warning in warnings))

    def test_outcome_only_landing_is_repaired_into_a_causal_attack(self):
        rows, warnings = reconcile_combat_action_rows(
            [shot(1, 0, 2.0, "S1 maintains close range. S2 lands on his back; S1 stands over him.")],
            2.0,
        )
        row = rows[0]
        self.assertEqual(row["combat_continuity_status"], "auto_fixed")
        self.assertIn("foot sweep", row["subject_action"])
        self.assertIn("force vector", row["subject_action"])
        self.assertTrue(any("outcome-only" in warning for warning in warnings))

    def test_hong_kong_comic_auto_repair_never_inherits_wet_market_target(self):
        plan = {
            "duration_seconds": 5.0,
            "constraints": "",
            "shots": [{
                **shot(1, 0.0, 5.0, "S2 lands on his back; S1 stands over him."),
                "environment_interaction": (
                    "source-visible rocky mountain; stale nearest wet produce crate metadata"
                ),
            }],
        }
        apply_combat_action_continuity(
            plan,
            special_skill_key=HONG_KONG_COMIC_FIGHTER_SKILL,
        )
        action = plan["shots"][0]["subject_action"]
        self.assertIn("source-visible rock surface", action)
        self.assertNotIn("produce crate", action)
        self.assertNotIn("wet market", action)
        incoming = plan["shots"][0]["incoming_combat_state"]
        self.assertIn("source-image terrain", incoming)
        self.assertNotIn("wet floor", incoming)

    def test_final_combat_marker_reanchors_after_duration_extension(self):
        markers = [{
            "time_seconds": 29.0,
            "preset": "Ending Hold",
            "direction": "Old pre-extension ending.",
        }]
        repaired = reconcile_final_combat_markers(markers, 41.5)
        self.assertEqual(repaired[0]["time_seconds"], 40.5)
        self.assertEqual(repaired[0]["preset"], "Final Combat Resolve")

    def test_user_edited_repeated_action_remains_a_warning(self):
        value = shot(2, 2.5, 5.0, "S1 attacks S2. S2 blocks and counters.")
        value["combat_action_chain_user_edited"] = True
        rows, warnings = reconcile_combat_action_rows(
            [shot(1, 0, 2.5, "S1 attacks S2. S2 blocks and counters."), value],
            5.0,
        )
        self.assertEqual(rows[1]["combat_continuity_status"], "warning")
        self.assertTrue(any("repeats the preceding Shot" in warning for warning in warnings))

    def test_dialogue_extension_preserves_authored_baseline(self):
        plan = {
            "duration_seconds": 48.5,
            "_speech_timing_base_duration": 45.0,
            "constraints": "",
            "shots": [shot(1, 0, 48.5, "S1 attacks S2. S2 blocks and counters.")],
        }
        apply_combat_action_continuity(
            plan, special_skill_key="street-fighter-live-action-h3"
        )
        self.assertEqual(combat_baseline_duration(plan), 45.0)
        self.assertEqual(plan["combat_baseline_duration_seconds"], 45.0)
        self.assertEqual(plan["combat_action_schema_version"], COMBAT_ACTION_SCHEMA_VERSION)
        self.assertEqual(str(plan["constraints"]).count(ACTION_CAUSALITY_CONTRACT), 1)
        self.assertIn("45.00s]", plan["shots"][0]["subject_action"])
        self.assertNotIn("48.50s]", plan["shots"][0]["subject_action"])

    def test_hong_kong_comic_skill_reuses_action_engine_without_p1_p2_cast_assumption(self):
        plan = {
            "duration_seconds": 12.0,
            "constraints": "",
            "shots": [shot(1, 0.0, 12.0, "龙界 intercepts 神武不死's electric fist; 神武不死 redirects the contact.")],
            "existing_media_uses": [{"media_id": "P1"}, {"media_id": "P2"}],
        }
        media = [
            {"media_id": "P1", "media_type": "image", "loaded": True,
             "raw_analysis_summary": "BLIP · Overview: one comic page containing both fighters on a mountain"},
            {"media_id": "P2", "media_type": "image", "loaded": True,
             "raw_analysis_summary": "BLIP · Overview: the same two fighters collide"},
        ]
        apply_combat_action_continuity(
            plan,
            special_skill_key=HONG_KONG_COMIC_FIGHTER_SKILL,
            existing_media=media,
            authored_requirement="神武不死与龙界使用无界紫电拳和极霸之拳。",
        )
        self.assertEqual(plan["combat_action_schema_version"], COMBAT_ACTION_SCHEMA_VERSION)
        self.assertTrue(plan["combat_fact_ledger"]["permissions"]["supernatural_carriers"])
        self.assertTrue(all(not row["media_id"] for row in plan["combat_fact_ledger"]["subjects"]))
        self.assertIn("P1/P2 numbering does not imply", plan["combat_fact_ledger"]["subjects"][0]["description"])

    def test_prompt_clause_is_state_delta_not_duplicate_action_chain(self):
        rows, _ = reconcile_combat_action_rows(
            [shot(1, 0, 2.5, "S1 attacks S2. S2 blocks and counters.")], 2.5
        )
        clause = combat_action_prompt_clause(rows[0])
        self.assertIn("INCOMING COMBAT STATE", clause)
        self.assertIn("NEXT ACTION TRIGGER", clause)
        self.assertNotIn("COMBAT ACTION CHAIN", clause)

    def test_prompt_compaction_removes_only_engine_owned_duplicates(self):
        value = (
            "User-authored close action.\n"
            "[ENV-IN] generated state\n"
            "HONG KONG KOWLOON WET-MARKET ARENA: long global contract. "
            "P1/P2 ABSOLUTE CAST LOCK: another global contract."
        )
        self.assertEqual(
            compact_street_fighter_prompt_field(
                value,
                global_contracts=(
                    "HONG KONG KOWLOON WET-MARKET ARENA: long global contract.",
                    "P1/P2 ABSOLUTE CAST LOCK: another global contract.",
                ),
            ),
            "User-authored close action",
        )

    def test_fact_ledger_ranks_pixels_above_blip_and_keeps_subjects_separate(self):
        ledger = build_combat_fact_ledger(
            {"existing_media_uses": [{"media_id": "P1"}, {"media_id": "P2"}]},
            [
                {"media_id": "P1", "media_type": "image", "loaded": True,
                 "raw_analysis_summary": "BLIP · Overview: woman in white shirt"},
                {"media_id": "P2", "media_type": "image", "loaded": True,
                 "raw_analysis_summary": "BLIP · Overview: man in red jacket"},
            ],
            authored_requirement="S1 is the karate fighter; S2 is the judo fighter.",
        )
        self.assertEqual(ledger["authority_order"][0], "explicit_user_direction")
        self.assertEqual(ledger["subjects"][0]["identity_authority"], "loaded_picture_pixels")
        self.assertEqual(ledger["subjects"][0]["media_id"], "P1")
        self.assertEqual(ledger["subjects"][1]["media_id"], "P2")
        self.assertIn("P1", combat_fact_prompt_context(ledger))

    def test_action_router_and_force_vector_are_structured(self):
        carrier, warnings = route_action_carrier("S1 drives a double-leg takedown into S2")
        self.assertEqual(carrier, "throw_takedown")
        self.assertFalse(warnings)
        force = infer_force_vector("S1 drives S2 down toward screen-left", actor="S1", carrier=carrier)
        self.assertEqual(force["horizontal"], "screen-left")
        self.assertEqual(force["vertical"], "downward")
        self.assertEqual(force["magnitude"], "heavy")

    def test_each_shot_has_duty_carrier_camera_and_concrete_state(self):
        rows, _ = reconcile_combat_action_rows(
            [shot(1, 0, 2.5, "S1 launches a low kick at S2. S2 parries and pivots outside.")], 2.5
        )
        row = rows[0]
        self.assertIn(row["combat_story_duty"], {"state_pickup", "escalation", "advantage_shift", "environment_consequence", "outgoing_relay"})
        self.assertEqual(row["combat_action_carrier"], "kick")
        self.assertIn("BEAT 01", row["camera_action_trigger"])
        self.assertIn("screen-", row["combat_force_vector"]["label"])
        self.assertGreaterEqual(len(row["incoming_combat_state_vector"]), 4)
        self.assertIn("EVENT CAUSE", row["event_causality_chain"])
        self.assertIn("PHYSICAL FEEDBACK", row["physical_feedback_chain"])

    def test_silent_causal_validator_checks_every_required_beat_field(self):
        rows, _ = reconcile_combat_action_rows(
            [
                shot(1, 0, 2.5, "S1 drives a palm toward S2. S2 parries and shifts right."),
                shot(2, 2.5, 5.0, "S2 clinches S1. S1 frames and pivots clear."),
            ],
            5.0,
        )
        required = {
            "load_weight", "trajectory", "defensive_response", "contact_kind",
            "force_vector", "displacement", "next_trigger",
        }
        for row in rows:
            for beat in row["combat_action_beats"]:
                self.assertTrue(required.issubset(beat))
            self.assertNotEqual(row["causal_validation_status"], "warning")
        self.assertGreaterEqual(len(rows[1]["causal_validation_inherited_fields"]), 4)

    def test_unrequested_weapon_is_auto_routed_but_user_edit_stays_warning(self):
        generated, _ = reconcile_combat_action_rows(
            [shot(1, 0, 3.0, "S1 swings a sword at S2. S2 blocks the blade.")], 3.0
        )
        self.assertEqual(generated[0]["causal_risk_repair_status"], "auto_fixed")
        self.assertNotIn("sword", generated[0]["subject_action"].casefold())
        self.assertNotEqual(generated[0]["causal_validation_status"], "warning")

        authored = shot(1, 0, 3.0, "S1 swings a sword at S2. S2 blocks the blade.")
        authored["combat_action_chain_user_edited"] = True
        preserved, _ = reconcile_combat_action_rows([authored], 3.0)
        self.assertIn("sword", preserved[0]["subject_action"].casefold())
        self.assertEqual(preserved[0]["causal_validation_status"], "warning")

    def test_generic_pose_and_exchange_are_replaced_by_concrete_choreography(self):
        rows, warnings = reconcile_combat_action_rows(
            [
                shot(1, 0, 2.5, "S1 looks directly at S2 and raises his right fist."),
                shot(2, 2.5, 5.0, "S1 and S2 execute an immediate full-speed attack and defence exchange."),
            ],
            5.0,
        )
        rendered = " ".join(row["subject_action"] for row in rows).casefold()
        self.assertNotIn("looks directly", rendered)
        self.assertNotIn("immediate full-speed attack", rendered)
        self.assertIn("auto_fixed", {row["combat_continuity_status"] for row in rows})
        self.assertTrue(any("generic choreography" in warning for warning in warnings))
        self.assertNotEqual(
            rows[0]["causal_risk_original_action"],
            rows[1]["causal_risk_original_action"],
        )

    def test_dialogue_extension_tail_preserves_final_state_without_new_attack(self):
        plan = {
            "duration_seconds": 17.0,
            "_speech_timing_base_duration": 15.0,
            "shots": [
                shot(1, 0, 7.5, "S1 drives a palm toward S2. S2 parries and shifts right."),
                shot(2, 7.5, 15.0, "S2 sweeps S1. S1 braces and completes the fall."),
                shot(3, 15.0, 17.0, "Wind carries fine grit through the final frame."),
            ],
            "markers": [],
            "constraints": "",
            "design_warnings": [],
        }
        apply_combat_action_continuity(
            plan,
            special_skill_key=HONG_KONG_COMIC_FIGHTER_SKILL,
        )
        tail = plan["shots"][-1]
        self.assertEqual(tail["combat_continuity_status"], "speech_tail_hold")
        self.assertIn("No new attack begins", tail["subject_action"])
        self.assertNotIn("[BEAT", tail["subject_action"])
        self.assertEqual(tail["movement_speed"], "Settled")

    def test_final_shot_completes_into_stable_action_and_camera_state(self):
        rows, _ = reconcile_combat_action_rows(
            [
                shot(1, 0, 2.5, "S1 kicks toward S2. S2 checks and circles outside."),
                shot(2, 2.5, 5.0, "S2 sweeps S1. S1 braces and completes the fall."),
            ],
            5.0,
        )
        final = rows[-1]
        self.assertTrue(final["final_action_stable"])
        self.assertIn("[FINAL SETTLE", final["subject_action"])
        self.assertIn("no next Beat", final["next_action_trigger"])
        self.assertIn("stable", final["final_camera_resolution"])
        self.assertIn("settled", final["outgoing_combat_state_vector"]["velocity"])


if __name__ == "__main__":
    unittest.main()

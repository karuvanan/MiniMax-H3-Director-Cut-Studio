import unittest

from design_engine import enforce_design_subtitle_policy

from fourdx_engine import (
    AI_MOVIE_MAKING_OF_4DX_SKILL,
    FOURDX_EFFECT_IDS,
    build_reference_role_ledger,
    enforce_making_of_fourdx_plan,
    fourdx_preferences_from_requirement,
    minimum_fourdx_duration,
    requested_fourdx_duration,
    scaled_making_of_stages,
    update_fourdx_requirement_block,
)


def _plan() -> dict:
    return {
        "title": "Making-of",
        "duration_seconds": 45.0,
        "creative_brief": "A vehicle accelerates, hits debris and causes dust, sparks and a pressure wave.",
        "global_visual_style": "Photoreal cinematic VFX breakdown.",
        "overall_soundscape": "Engine rumble, impact and wind.",
        "constraints": "No invented UI.",
        "shots": [
            {
                "id": f"S{index + 1}",
                "start_seconds": index * 5.0,
                "end_seconds": (index + 1) * 5.0,
                "additional_direction": "",
                "subject_action": "The vehicle accelerates and collides with debris.",
                "environment_response": "Dust, sparks, vibration and a pressure wave follow impact.",
            }
            for index in range(9)
        ],
        "text_layers": [],
        "design_warnings": [],
    }


class FourDXEngineTests(unittest.TestCase):
    def test_requirement_control_round_trip_preserves_story(self):
        original = "My story remains exactly here."
        updated = update_fourdx_requirement_block(original, {
            "selected_effects": ["wind", "flash", "water_rain"],
            "intensity": "high",
            "density": "sparse",
        })
        self.assertIn(original, updated)
        prefs = fourdx_preferences_from_requirement(updated)
        self.assertEqual(prefs["selected_effects"], ["wind", "flash", "water_rain"])
        self.assertEqual(prefs["intensity"], "high")
        self.assertEqual(prefs["density"], "sparse")
        replaced = update_fourdx_requirement_block(updated, {
            "selected_effects": ["impact"], "intensity": "low", "density": "dense",
        })
        self.assertEqual(replaced.count("4DX EXPERIENCE CONTROL"), 2)  # begin + end marker
        self.assertEqual(fourdx_preferences_from_requirement(replaced)["selected_effects"], ["impact"])

    def test_reference_ledger_never_uses_filename_as_authority(self):
        ledger = build_reference_role_ledger([{
            "media_id": "P1", "media_type": "image", "loaded": True,
            "filename": "petronas-klcc.png",
            "caption": "a woman beside a red vehicle",
        }])
        self.assertEqual(ledger[0]["media_id"], "P1")
        self.assertFalse(ledger[0]["filename_is_evidence"])
        self.assertNotIn("petronas", ledger[0]["evidence"].lower())

    def test_complete_ten_effect_showcase_reaches_h3_and_builds_linked_events(self):
        plan = enforce_making_of_fourdx_plan(
            _plan(),
            existing_media=[{
                "media_id": "P1", "media_type": "image", "loaded": True,
                "caption": "a vehicle in a dusty street",
            }],
            preferences={
                "selected_effects": list(FOURDX_EFFECT_IDS),
                "intensity": "high", "density": "balanced",
            },
            special_skill_key=AI_MOVIE_MAKING_OF_4DX_SKILL,
        )
        self.assertEqual(len(plan["experience_design"]["stages"]), 12)
        self.assertEqual(len(plan["shots"]), 12)
        self.assertEqual(len(plan["media_requests"]), 10)
        self.assertEqual(len(plan["transitions"]), 11)
        self.assertEqual(plan["markers"][-1]["preset"], "Final Hold")
        self.assertFalse(any(
            row.get("role") in {"voice_over", "dialogue", "lyrics"}
            for row in plan["text_layers"]
        ))
        rendered_shots = " ".join(row["additional_direction"] for row in plan["shots"])
        self.assertIn("PITCH · FIGHTER-JET TAKEOFF", rendered_shots)
        self.assertIn("WATER / RAIN · OCEAN IMPACT", rendered_shots)
        self.assertNotIn("CHARACTER EXTRACTION", rendered_shots)
        labels = [
            row for row in plan["text_layers"]
            if row.get("timeline_visible_text_kind") == "making_of_stage_label"
        ]
        self.assertEqual(len(labels), 12)
        subtitles_off = enforce_design_subtitle_policy(
            plan, False, authored_requirement="Create a 45-second making-of film."
        )
        self.assertEqual(sum(
            row.get("timeline_visible_text_kind") == "making_of_stage_label"
            for row in subtitles_off["text_layers"]
        ), 12)
        physical_ids = {row["event_id"] for row in plan["physical_events"]}
        self.assertEqual(len(plan["fourdx_events"]), 10)
        self.assertTrue(all(
            row["physical_event_id"] in physical_ids
            and row["camera_motion_is_source"] is False
            for row in plan["fourdx_events"]
        ))
        status = {
            row["effect_id"]: row["status"]
            for row in plan["experience_design"]["effect_status"]
        }
        self.assertTrue(all(status[key] == "used" for key in FOURDX_EFFECT_IDS))
        self.assertEqual(
            plan["experience_design"]["rules"]["sound_source_policy"],
            "diegetic_4dx_auditorium_only",
        )
        self.assertIn(
            "four clearly audible spatial layers",
            plan["overall_soundscape"],
        )
        self.assertIn("No background music", plan["overall_soundscape"])
        self.assertTrue(plan["experience_design"]["rules"]["audience_reaction_required"])
        self.assertTrue(
            plan["experience_design"]["rules"]["screen_plane_breakout_required"]
        )
        self.assertTrue(
            plan["experience_design"]["rules"]["screen_border_occlusion_required"]
        )
        self.assertTrue(
            plan["experience_design"]["rules"]["audience_startle_causality_required"]
        )
        self.assertEqual(plan["experience_design"]["schema_version"], 3)
        effect_shots = [
            row for row in plan["shots"]
            if row.get("screen_plane_breakout_required")
        ]
        self.assertEqual(len(effect_shots), 10)
        self.assertTrue(all(
            row.get("screen_plane_breakout")
            and "screen border" in row.get("framing", "").lower()
            and "audience faces" in row.get("framing", "").lower()
            and "front-row" in row.get("audience_startle_chain", "")
            and "SCREEN-PLANE BREAKOUT" in row.get("h3_executable_action", "")
            and "four simultaneously audible diegetic layers" in row.get(
                "native_audio_direction", ""
            )
            and "No song, score" in row.get("native_audio_direction", "")
            for row in effect_shots
        ))
        self.assertTrue(all(
            row.get("screen_plane_bridge")
            and row.get("audience_reaction_trigger")
            for row in plan["physical_events"]
            if row.get("generated_by") == "AUTO"
        ))
        self.assertTrue(all(
            row.get("requirement_id", "").startswith("fourdx_screen_breakout_v3_")
            and
            "screen-plane breakout" in row.get("prompt", "").lower()
            and "duplicated source subject" in row.get("negative_prompt", "").lower()
            for row in plan["media_requests"]
        ))
        self.assertTrue(all(
            row["duration_ms"] >= 0.95 * (
                next(
                    stage["end_seconds"] - stage["start_seconds"]
                    for stage in plan["experience_design"]["stages"]
                    if stage.get("effect_id") == row["effect_id"]
                ) * 1000
            )
            for row in plan["fourdx_events"]
            if row.get("generated_by") == "AUTO"
        ))

    def test_default_preferences_and_chapters_include_all_ten_effects(self):
        updated = update_fourdx_requirement_block("story", None)
        self.assertEqual(
            fourdx_preferences_from_requirement(updated)["selected_effects"],
            list(FOURDX_EFFECT_IDS),
        )
        stages = scaled_making_of_stages(60.0)
        effect_stages = [row for row in stages if row.get("effect_id")]
        self.assertEqual([row["effect_id"] for row in effect_stages], list(FOURDX_EFFECT_IDS))
        self.assertEqual(stages[0]["start_seconds"], 0.0)
        self.assertEqual(stages[-1]["end_seconds"], 60.0)

    def test_effect_count_duration_budget_resolves_authored_fifteen_seconds(self):
        self.assertEqual(minimum_fourdx_duration(1), 15.0)
        self.assertEqual(minimum_fourdx_duration(10), 60.0)
        requirement = "帮我创作15秒的沉浸式4DX影片。"
        one = update_fourdx_requirement_block(requirement, {
            "selected_effects": ["pitch"],
        })
        self.assertEqual(requested_fourdx_duration(one), 15.0)
        self.assertEqual(
            fourdx_preferences_from_requirement(one)["resolved_duration_seconds"],
            15.0,
        )
        all_ten = update_fourdx_requirement_block(requirement, {
            "selected_effects": list(FOURDX_EFFECT_IDS),
        })
        prefs = fourdx_preferences_from_requirement(all_ten)
        self.assertEqual(prefs["minimum_duration_seconds"], 60.0)
        self.assertEqual(prefs["resolved_duration_seconds"], 60.0)
        self.assertIn("Resolved design duration: 60.00 seconds", all_ten)
        longer = update_fourdx_requirement_block(
            "帮我创作90秒、16:9的沉浸式4DX影片。",
            {"selected_effects": list(FOURDX_EFFECT_IDS)},
        )
        self.assertEqual(
            fourdx_preferences_from_requirement(longer)["resolved_duration_seconds"],
            90.0,
        )

    def test_one_effect_authored_fifteen_seconds_builds_exact_fifteen_second_timeline(self):
        source = _plan()
        source["duration_seconds"] = 45.0
        result = enforce_making_of_fourdx_plan(
            source, existing_media=[],
            preferences={
                "selected_effects": ["wind"],
                "requested_duration_seconds": 15.0,
            },
            special_skill_key=AI_MOVIE_MAKING_OF_4DX_SKILL,
        )
        self.assertEqual(result["duration_seconds"], 15.0)
        self.assertEqual(len(result["shots"]), 3)
        self.assertEqual(result["shots"][-1]["end_seconds"], 15.0)

    def test_selected_subset_builds_only_selected_effect_chapters(self):
        plan = enforce_making_of_fourdx_plan(
            _plan(), existing_media=[],
            preferences={"selected_effects": ["wind", "water_rain"]},
            special_skill_key=AI_MOVIE_MAKING_OF_4DX_SKILL,
        )
        self.assertEqual(
            [row.get("effect_id") for row in plan["experience_design"]["stages"] if row.get("effect_id")],
            ["wind", "water_rain"],
        )
        self.assertEqual(len(plan["shots"]), 4)
        self.assertEqual(len(plan["fourdx_events"]), 2)

    def test_unrelated_skill_is_unchanged(self):
        plan = _plan()
        result = enforce_making_of_fourdx_plan(
            plan, existing_media=[], preferences=None, special_skill_key="other-skill"
        )
        self.assertIs(result, plan)
        self.assertNotIn("experience_design", result)

    def test_manual_events_survive_automatic_replanning(self):
        plan = _plan()
        plan["physical_events"] = [{
            "event_id": "PE-900", "generated_by": "MANUAL", "event_type": "impact",
        }]
        plan["fourdx_events"] = [{
            "event_id": "4DX-900", "physical_event_id": "PE-900",
            "generated_by": "MANUAL", "effect_id": "impact",
        }]
        result = enforce_making_of_fourdx_plan(
            plan, existing_media=[],
            preferences={"selected_effects": ["impact"]},
            special_skill_key=AI_MOVIE_MAKING_OF_4DX_SKILL,
        )
        self.assertTrue(any(
            row.get("event_id") == "PE-900" for row in result["physical_events"]
        ))
        self.assertTrue(any(
            row.get("event_id") == "4DX-900" for row in result["fourdx_events"]
        ))


if __name__ == "__main__":
    unittest.main()

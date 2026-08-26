import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from design_cleanup_service import cleanup, lm_origin, unload_lm_studio
from design_ai_service import handle as handle_design_ai_job
from design_engine import (
    DESIGN_JSON_SCHEMA,
    build_design_system_prompt,
    materialize_design_media,
    normalize_shot_action_budget,
    normalize_design_plan,
)
from design_media_service import generate as generate_design_media, image_workflow
from design_settings import DesignAISettings, load_design_settings, save_design_settings
from runtime_paths import PROJECT_ROOT, load_runtime_paths


def sample_design() -> dict:
    return {
        "title": "Cola Reveal",
        "duration_seconds": 12.1,
        "theme_text": "OPEN HAPPINESS",
        "theme_text_explicit_user_requested": True,
        "creative_brief": "A tactile cola reveal becomes a confident lifestyle moment.",
        "global_visual_style": "Premium sunlit commercial realism with crisp condensation.",
        "overall_soundscape": "Can handling, fizz, room tone and a clean final sip.",
        "non_diegetic_music": "Minimal upbeat pulse building after the reveal.",
        "constraints": "Keep the can, hand and woman consistent; preserve readable branding.",
        "shots": [
            {
                "start_seconds": 0.1,
                "end_seconds": 4.2,
                "track": "V1",
                "preset": "Product Reveal",
                "framing": "Extreme close-up",
                "camera_angle": "Eye level",
                "camera_movement": "Zoom out",
                "movement_speed": "Slow",
                "movement_amplitude": "Large",
                "subject_action": "A hand firmly grips a cold cola can.",
                "environment_response": "Condensation beads catch the light.",
                "additional_direction": "Begin on the fingers and logo, then reveal context.",
            },
            {
                "start_seconds": 4.2,
                "end_seconds": 12.1,
                "track": "V1",
                "preset": "Lifestyle Payoff",
                "framing": "Medium-wide",
                "camera_angle": "Eye level",
                "camera_movement": "Dolly out",
                "movement_speed": "Slow",
                "movement_amplitude": "Medium",
                "subject_action": "The woman raises the can and drinks.",
                "environment_response": "Soft highlights travel across the can.",
                "additional_direction": "End on a relaxed satisfied expression.",
            },
        ],
        "text_layers": [],
        "transitions": [{"time_seconds": 4.2, "preset": "Match Reveal", "direction": "Continue the outward move."}],
        "markers": [{"time_seconds": 10.8, "preset": "Final Hold", "direction": "Settle camera and hold product."}],
        "media_requests": [
            {
                "media_type": "image",
                "usage": "h3_reference",
                "start_seconds": 0.1,
                "end_seconds": 4.2,
                "track": "V1",
                "subject_keywords": ["hand", "cola_can"],
                "prompt": "Reference image: hand gripping a cold cola can, logo visible.",
            },
            {
                "media_type": "audio",
                "usage": "h3_reference",
                "start_seconds": 0,
                "end_seconds": 12.1,
                "track": "A1",
                "subject_keywords": ["fizz", "music"],
                "prompt": "Clean cola fizz followed by a restrained upbeat pulse.",
            },
        ],
    }


class DesignEngineTests(unittest.TestCase):
    def test_design_ai_worker_releases_comfy_models_before_refinement(self):
        with patch("design_ai_service.request_json", return_value={}) as request:
            result = handle_design_ai_job({
                "action": "unload_comfy",
                "base_url": "http://127.0.0.1:8188",
                "timeout": 30,
            })
        self.assertTrue(result["comfy_unloaded"])
        request.assert_called_once_with(
            "http://127.0.0.1:8188/free",
            api_key="",
            timeout=30.0,
            payload={"unload_models": True, "free_memory": True},
        )

    def test_lm_origin_removes_openai_compatible_v1_path(self):
        self.assertEqual(
            lm_origin("http://192.168.0.185:1234/v1"),
            "http://192.168.0.185:1234",
        )

    def test_cleanup_unloads_only_selected_lm_loaded_instance(self):
        calls = []

        def fake_request(url, timeout, payload=None):
            calls.append((url, payload))
            if url.endswith("/api/v1/models"):
                return {
                    "models": [
                        {
                            "key": "selected/model.gguf",
                            "loaded_instances": [{"id": "selected/model.gguf:2"}],
                        },
                        {
                            "key": "other/model.gguf",
                            "loaded_instances": [{"id": "other/model.gguf:1"}],
                        },
                    ]
                }
            return {}

        with patch("design_cleanup_service.request", side_effect=fake_request):
            unloaded = unload_lm_studio(
                "http://127.0.0.1:1234/v1", "selected/model.gguf", 10
            )
        self.assertEqual(unloaded, ["selected/model.gguf:2"])
        self.assertEqual(
            calls[-1],
            (
                "http://127.0.0.1:1234/api/v1/models/unload",
                {"instance_id": "selected/model.gguf:2"},
            ),
        )

    def test_cleanup_requests_comfy_free_and_skips_lm_for_openai(self):
        with patch("design_cleanup_service.request", return_value={}) as mocked:
            result = cleanup({
                "provider": "openai",
                "comfyui_server": "http://127.0.0.1:8188",
                "timeout": 10,
            })
        self.assertTrue(result["comfyui_unloaded"])
        mocked.assert_called_once_with(
            "http://127.0.0.1:8188/free",
            10.0,
            {"unload_models": True, "free_memory": True},
        )

    def test_non_secret_connection_settings_round_trip(self):
        target = PROJECT_ROOT / ".director_cache" / "design_settings_test.env"
        settings = DesignAISettings(
            provider="lm_studio",
            openai_model="gpt-5.6-sol",
            lm_studio_base_url="http://127.0.0.1:1234/v1",
            lm_studio_model="local-model",
            timeout=240,
        )
        try:
            save_design_settings(target, settings)
            saved_text = target.read_text(encoding="utf-8")
            self.assertNotIn("API_KEY", saved_text)
            restored = load_design_settings(target)
            self.assertEqual(restored.provider, "lm_studio")
            self.assertEqual(restored.lm_studio_model, "local-model")
            self.assertEqual(restored.timeout, 240)
            self.assertTrue(restored.generate_comfy_images)
            self.assertEqual(restored.image_checkpoint, "z_image_turbo_bf16.safetensors")
        finally:
            target.unlink(missing_ok=True)

    def test_comfy_reference_workflow_uses_standard_txt2img_nodes(self):
        request = {
            "prompt": "A hand holding a cold cola bottle",
            "subject_keywords": ["hand", "cola bottle"],
        }
        settings = {
            "checkpoint": "epicrealismXL_vxviLastfameRealism.safetensors",
            "width": 1024,
            "height": 576,
            "steps": 24,
            "cfg": 5.5,
            "negative_prompt": "blurry",
        }
        workflow = image_workflow(request, settings, 1234, "h3_design/test")
        self.assertEqual(workflow["1"]["class_type"], "CheckpointLoaderSimple")
        self.assertEqual(workflow["4"]["inputs"]["width"], 1024)
        self.assertEqual(workflow["5"]["inputs"]["seed"], 1234)
        self.assertEqual(workflow["7"]["class_type"], "SaveImage")

    def test_z_image_template_is_patched_without_replacing_its_model_stack(self):
        template = json.loads(
            (PROJECT_ROOT / "Z-Image_Text2Image_for_webui_t2i_api.json").read_text(
                encoding="utf-8-sig"
            )
        )
        request = {
            "prompt": "A woman walking through a tennis court",
            "subject_keywords": ["woman", "tennis court"],
        }
        settings = {
            "checkpoint": "z_image_turbo_bf16.safetensors",
            "width": 768,
            "height": 1024,
            "steps": 8,
            "cfg": 1.0,
            "negative_prompt": "",
        }
        workflow = image_workflow(
            request, settings, 9876, "h3_design/z_test", template
        )
        self.assertEqual(workflow["16"]["class_type"], "UNETLoader")
        self.assertEqual(workflow["16"]["inputs"]["unet_name"], "z_image_turbo_bf16.safetensors")
        self.assertEqual(workflow["18"]["inputs"]["clip_name"], "qwen_3_4b.safetensors")
        self.assertEqual(workflow["17"]["inputs"]["vae_name"], "ae.safetensors")
        self.assertEqual(workflow["3"]["inputs"]["seed"], 9876)
        self.assertEqual(workflow["13"]["inputs"]["width"], 768)
        self.assertIn("tennis court", workflow["6"]["inputs"]["text"])
        self.assertEqual(workflow["33"]["class_type"], "RAMCleanup")
        self.assertEqual(workflow["34"]["class_type"], "VRAMCleanup")
        self.assertEqual(workflow["37"]["class_type"], "VRAM_Debug")
        self.assertEqual(workflow["11"]["inputs"]["model"], ["34", 0])
        self.assertEqual(workflow["37"]["inputs"]["any_input"], ["3", 0])
        self.assertEqual(workflow["8"]["inputs"]["samples"], ["36", 0])
        # The user's latest Z-Image template deliberately removed RTX upscaling.
        # Patching settings must preserve whichever decoded-image connection the
        # current template defines instead of restoring an obsolete node id.
        self.assertEqual(
            workflow["9"]["inputs"]["images"],
            template["9"]["inputs"]["images"],
        )
        self.assertFalse(
            any("RTXVideoSuperResolution" in row.get("class_type", "") for row in workflow.values())
        )

    def test_z_image_patching_finds_nodes_by_class_type_not_fixed_ids(self):
        template = {
            "prompt-any-id": {"class_type": "CLIPTextEncode", "inputs": {"text": "old"}},
            "sampler-any-id": {
                "class_type": "KSampler",
                "inputs": {"seed": 1, "steps": 1, "cfg": 1},
            },
            "latent-any-id": {
                "class_type": "EmptySD3LatentImage",
                "inputs": {"width": 256, "height": 256, "batch_size": 1},
            },
            "save-any-id": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "old"},
            },
            "unet-any-id": {
                "class_type": "UNETLoader",
                "inputs": {"unet_name": "old.safetensors"},
            },
            "cleanup-untouched": {
                "class_type": "VRAMCleanup",
                "inputs": {"offload_model": True, "anything": ["sampler-any-id", 0]},
            },
        }
        workflow = image_workflow(
            {"prompt": "dynamic node test", "subject_keywords": []},
            {
                "checkpoint": "z_image_turbo_bf16.safetensors",
                "width": 640,
                "height": 384,
                "steps": 8,
                "cfg": 1.0,
                "negative_prompt": "",
            },
            456,
            "h3_design/dynamic",
            template,
        )
        self.assertEqual(workflow["prompt-any-id"]["inputs"]["text"], "dynamic node test")
        self.assertEqual(workflow["sampler-any-id"]["inputs"]["seed"], 456)
        self.assertEqual(workflow["latent-any-id"]["inputs"]["width"], 640)
        self.assertEqual(workflow["save-any-id"]["inputs"]["filename_prefix"], "h3_design/dynamic")
        self.assertEqual(
            workflow["cleanup-untouched"]["inputs"]["anything"],
            ["sampler-any-id", 0],
        )

    def test_z_image_generation_retries_one_transient_failure(self):
        generated = {
            "local_path": "recovered.png",
            "original_local_path": "recovered.png",
            "seed": 42,
            "prompt_id": "prompt-ok",
            "generated": True,
            "request_index": 0,
            "background_removal": {},
        }
        job = {
            "server": "http://127.0.0.1:8188",
            "workflow_path": "",
            "materials": [{
                "media_type": "image",
                "local_path": "recovered.png",
                "prompt": "A complete standalone production frame.",
                "subject_keywords": [],
            }],
            "settings": {},
            "poll_interval": 1.0,
            "generation_timeout": 30,
            "http_timeout": 10,
        }
        with (
            patch(
                "design_media_service._generate_request",
                side_effect=[RuntimeError("transient queue error"), generated],
            ) as request,
            patch("design_media_service.emit") as emit,
        ):
            result = generate_design_media(job)

        self.assertEqual(request.call_count, 2)
        self.assertEqual(result["outputs"], [generated])
        self.assertEqual(result["warnings"], [])
        self.assertTrue(
            any(
                "retrying" in str(call.args[0].get("progress", ""))
                for call in emit.call_args_list
            )
        )
    def test_normalize_snaps_director_plan_to_half_seconds(self):
        plan = normalize_design_plan(sample_design(), {"image": 9, "video": 3, "audio": 3})
        self.assertEqual(plan["duration_seconds"], 12.0)
        self.assertEqual((plan["shots"][0]["start_seconds"], plan["shots"][0]["end_seconds"]), (0.0, 4.0))
        self.assertEqual(plan["transitions"][0]["time_seconds"], 4.0)
        self.assertEqual(plan["markers"][0]["time_seconds"], 11.0)

    def test_schema_v2_requires_explicit_existing_media_uses(self):
        self.assertIn("existing_media_uses", DESIGN_JSON_SCHEMA["required"])
        media_use = DESIGN_JSON_SCHEMA["properties"]["existing_media_uses"]["items"]
        self.assertIn("media_id", media_use["required"])
        self.assertIn("requirement_id", media_use["required"])
        media_request = DESIGN_JSON_SCHEMA["properties"]["media_requests"]["items"]
        self.assertIn("requirement_id", media_request["required"])
        self.assertIn("reuse_policy", media_request["required"])

    def test_shot_schema_separates_core_state_and_optional_flourish(self):
        shot = DESIGN_JSON_SCHEMA["properties"]["shots"]["items"]
        self.assertIn("continuity_state", shot["required"])
        self.assertIn("optional_flourish", shot["required"])
        self.assertNotIn("h3_executable_action", shot["properties"])
        self.assertNotIn("action_budget", shot["properties"])

    def test_five_second_action_budget_demotes_secondary_beats(self):
        budgeted = normalize_shot_action_budget({
            "start_seconds": 0.0,
            "end_seconds": 5.0,
            "subject_action": (
                "The assassin leaps. The assassin throws one dart. The general blocks. "
                "The assassin draws a sword. The assassin strikes. Red leaves swirl."
            ),
            "continuity_state": "End with both fighters moving screen-right.",
            "optional_flourish": "The cape snaps. Dust drifts.",
        })
        budget = budgeted["action_budget"]
        self.assertEqual(budget["core_action_limit"], 3)
        self.assertEqual(budget["status"], "priority_compressed")
        self.assertLessEqual(
            len(normalize_shot_action_budget({
                **budgeted,
                "subject_action": budgeted["h3_executable_action"],
            })["h3_executable_action"].split(". ")),
            3,
        )
        self.assertIn("Red leaves swirl", budgeted["optional_flourish"])
        self.assertIn("omit", budget["notes"].lower())

    def test_action_budget_survives_normalizing_an_already_normalized_plan(self):
        payload = sample_design()
        payload["shots"][0]["end_seconds"] = 5.0
        payload["shots"][1]["start_seconds"] = 5.0
        payload["shots"][0]["subject_action"] = (
            "The assassin leaps. The assassin throws. The general blocks. "
            "The assassin lands. The assassin strikes."
        )
        payload["shots"][0]["environment_response"] = (
            "Tiles crack. Dust erupts. Leaves scatter. Water ripples."
        )
        first = normalize_design_plan(payload, {"image": 9, "video": 3, "audio": 3})
        second = normalize_design_plan(first, {"image": 9, "video": 3, "audio": 3})
        self.assertEqual(
            second["shots"][0]["action_budget"]["original_subject_action"],
            first["shots"][0]["action_budget"]["original_subject_action"],
        )
        self.assertEqual(second["shots"][0]["action_budget"]["status"], "priority_compressed")
        self.assertEqual(
            second["shots"][0]["action_budget"]["original_environment_response"],
            first["shots"][0]["action_budget"]["original_environment_response"],
        )

    def test_budget_keeps_causal_setup_with_contact_and_limits_required_responses(self):
        budgeted = normalize_shot_action_budget({
            "start_seconds": 0.0,
            "end_seconds": 5.0,
            "subject_action": (
                "The assassin launches. The assassin feints. The assassin draws both blades. "
                "He strikes. He lands behind the general."
            ),
            "environment_response": (
                "Tiles crack. Sparks burst. Leaves scatter. Dust erupts."
            ),
            "continuity_state": "End behind the general.",
            "optional_flourish": "",
        })
        self.assertIn("draws both blades, then he strikes", budgeted["subject_action"])
        self.assertEqual(budgeted["action_budget"]["required_response_limit"], 2)
        self.assertLessEqual(
            len(budgeted["environment_response"].split(". ")),
            2,
        )

    def test_legacy_shot_gets_continuity_state_and_blank_constraints_get_guardrail(self):
        payload = sample_design()
        payload["constraints"] = ""
        plan = normalize_design_plan(payload, {"image": 9, "video": 3, "audio": 3})
        self.assertIn("Preserve the incoming body positions", plan["shots"][0]["continuity_state"])
        self.assertIn("core action", plan["constraints"])
        self.assertIn("action_budget", plan["shots"][0])

    def test_overlapping_camera_shots_are_rejected(self):
        payload = sample_design()
        payload["shots"][1]["start_seconds"] = 3.0
        with self.assertRaisesRegex(ValueError, "overlaps"):
            normalize_design_plan(payload, {"image": 9, "video": 3, "audio": 3})

    def test_legacy_design_defaults_new_media_planning_fields(self):
        plan = normalize_design_plan(sample_design(), {"image": 9, "video": 3, "audio": 3})
        self.assertEqual(plan["existing_media_uses"], [])
        self.assertEqual(plan["media_requests"][0]["requirement_id"], "request_1")
        self.assertEqual(plan["media_requests"][0]["reuse_policy"], "time_scoped")
        self.assertEqual(plan["media_requests"][1]["reuse_policy"], "whole_design")

    def test_existing_media_reuse_wins_over_duplicate_generation_requirement(self):
        payload = sample_design()
        payload["existing_media_uses"] = [{
            "requirement_id": "hero_product",
            "media_id": "@P1",
            "media_type": "image",
            "usage": "h3_reference",
            "reuse_policy": "whole_design",
            "start_seconds": 3.0,
            "end_seconds": 6.0,
            "track": "V1",
            "subject_keywords": ["cola can", "hand"],
            "instruction": "",
        }]
        payload["media_requests"][0]["requirement_id"] = "hero_product"
        payload["media_requests"][0]["prompt"] = "Invalid duplicate from <Picture 1>."
        plan = normalize_design_plan(
            payload,
            {"image": 9, "video": 3, "audio": 3},
            existing_media=[{
                "tag": "<Picture 1>",
                "type": "image",
                "loaded": True,
                "clip_prompt": "Preserve the exact supplied can and hand.",
            }],
            strict_t2i_prompts=True,
        )
        self.assertEqual(len(plan["existing_media_uses"]), 1)
        self.assertEqual(plan["existing_media_uses"][0]["media_id"], "P1")
        self.assertEqual(
            plan["existing_media_uses"][0]["instruction"],
            "Preserve the exact supplied can and hand.",
        )
        self.assertEqual(
            (plan["existing_media_uses"][0]["start_seconds"], plan["existing_media_uses"][0]["end_seconds"]),
            (0.0, 12.0),
        )
        self.assertFalse(any(
            item["requirement_id"] == "hero_product" for item in plan["media_requests"]
        ))
        self.assertEqual([item["media_type"] for item in plan["media_requests"]], ["audio"])

    def test_design_normalization_canonicalizes_bare_reused_media_ids(self):
        payload = sample_design()
        payload["shots"][0]["additional_direction"] = "Use P1 as the exact product reference."
        payload["existing_media_uses"] = [{
            "requirement_id": "product_reference",
            "media_id": "P1",
            "media_type": "image",
            "usage": "h3_reference",
            "reuse_policy": "whole_design",
            "start_seconds": 0.0,
            "end_seconds": 12.0,
            "track": "V1",
            "subject_keywords": ["product"],
            "instruction": "Preserve P1 without replacement.",
        }]
        plan = normalize_design_plan(
            payload,
            {"image": 9, "video": 3, "audio": 3},
            existing_media=[{
                "media_id": "P1",
                "media_type": "image",
                "loaded": True,
            }],
        )
        self.assertIn("Use @P1", plan["shots"][0]["additional_direction"])
        self.assertIn("Preserve @P1", plan["existing_media_uses"][0]["instruction"])

    def test_existing_media_can_return_in_separate_timeline_intervals(self):
        payload = sample_design()
        payload["existing_media_uses"] = [
            {
                "requirement_id": "p1_opening",
                "media_id": "P1",
                "media_type": "image",
                "usage": "h3_reference",
                "reuse_policy": "time_scoped",
                "start_seconds": 1.0,
                "end_seconds": 5.0,
                "track": "V1",
                "subject_keywords": ["hero"],
                "instruction": "Establish the hero.",
            },
            {
                "requirement_id": "p1_return",
                "media_id": "P1",
                "media_type": "image",
                "usage": "h3_reference",
                "reuse_policy": "time_scoped",
                "start_seconds": 8.0,
                "end_seconds": 12.0,
                "track": "V2",
                "subject_keywords": ["hero"],
                "instruction": "Return to the hero from a new angle.",
            },
        ]
        plan = normalize_design_plan(
            payload,
            {"image": 9, "video": 3, "audio": 3},
            existing_media=[{
                "media_id": "P1", "media_type": "image", "loaded": True,
            }],
        )
        self.assertEqual(
            [(row["media_id"], row["start_seconds"], row["end_seconds"])
             for row in plan["existing_media_uses"]],
            [("P1", 1.0, 5.0), ("P1", 8.0, 12.0)],
        )

    def test_existing_media_inventory_rejects_unknown_empty_or_wrong_type(self):
        base_use = {
            "requirement_id": "hero",
            "media_id": "P1",
            "media_type": "image",
            "usage": "h3_reference",
            "reuse_policy": "whole_design",
            "start_seconds": 0,
            "end_seconds": 12,
            "track": "V1",
            "subject_keywords": ["hero"],
            "instruction": "Preserve the hero.",
        }
        for inventory, error in (
            ([], "not present"),
            ([{"media_id": "P1", "media_type": "image", "loaded": False}], "empty"),
            ([{"media_id": "P1", "media_type": "video", "loaded": True}], "not image"),
        ):
            payload = sample_design()
            payload["existing_media_uses"] = [dict(base_use)]
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                normalize_design_plan(
                    payload,
                    {"image": 9, "video": 3, "audio": 3},
                    existing_media=inventory,
                )

    def test_media_repair_converts_empty_p1_reuse_into_z_image_request(self):
        payload = sample_design()
        payload["media_requests"] = []
        payload["existing_media_uses"] = [{
            "requirement_id": "opening_subject",
            "media_id": "P1",
            "media_type": "image",
            "usage": "h3_reference",
            "reuse_policy": "time_scoped",
            "start_seconds": 0.0,
            "end_seconds": 4.0,
            "track": "V1",
            "subject_keywords": ["woman", "product"],
            "instruction": "Use @P1 for the woman holding the product.",
        }]

        plan = normalize_design_plan(
            payload,
            {"image": 9, "video": 3, "audio": 3},
            existing_media=[],
            strict_t2i_prompts=True,
            repair_media_plan=True,
        )

        self.assertEqual(plan["existing_media_uses"], [])
        images = [
            row for row in plan["media_requests"] if row["media_type"] == "image"
        ]
        self.assertEqual(len(images), 2)
        recovered = next(
            row for row in images if row["requirement_id"] == "opening_subject"
        )
        self.assertEqual(recovered["preferred_media_id"], "P1")
        self.assertNotIn("@P1", recovered["prompt"])
        self.assertTrue(any("P1 was empty" in row for row in plan["design_warnings"]))

    def test_media_repair_adds_visual_coverage_when_lm_returns_no_images(self):
        payload = sample_design()
        payload["media_requests"] = []
        payload["existing_media_uses"] = []

        plan = normalize_design_plan(
            payload,
            {"image": 9, "video": 3, "audio": 3},
            existing_media=[],
            strict_t2i_prompts=True,
            repair_media_plan=True,
        )

        images = [
            row for row in plan["media_requests"] if row["media_type"] == "image"
        ]
        self.assertEqual(len(images), 2)
        self.assertEqual(
            [row["requirement_id"] for row in images],
            ["auto_image_s1", "auto_image_s2"],
        )
        self.assertTrue(all(row["prompt"] for row in images))
        self.assertTrue(all(row["reuse_policy"] == "time_scoped" for row in images))

    def test_loaded_media_reserves_slots_for_missing_media_requests(self):
        payload = sample_design()
        with self.assertRaisesRegex(ValueError, "only 0 free slots"):
            normalize_design_plan(
                payload,
                {"image": 1, "video": 3, "audio": 3},
                existing_media=[{
                    "media_id": "P1",
                    "media_type": "image",
                    "loaded": True,
                }],
            )

    def test_system_prompt_guards_standalone_t2i_and_blip_replanning(self):
        prompt = build_design_system_prompt({"image_capacity": 9}).lower()
        self.assertIn("complete standalone visual prompt", prompt)
        self.assertIn("h3 <picture n>", prompt)
        self.assertIn("exact real in-world location", prompt)
        self.assertIn("character/prop ownership ledger", prompt)
        self.assertIn("if blip conflicts", prompt)
        self.assertIn("reject that generated reference", prompt)
        self.assertIn("never force one image per shot", prompt)
        self.assertIn("@p1", prompt)
        self.assertIn("existing_media_uses", prompt)
        self.assertIn("only genuinely missing assets", prompt)
        self.assertIn("timeline tracks are editorial lanes", prompt)
        self.assertIn("v4, v5 and higher", prompt)
        self.assertIn("a4, a5 and higher", prompt)
        self.assertIn("treat each asset's caption", prompt)
        self.assertIn("when a loaded asset satisfies that need", prompt)
        self.assertIn("multiple existing_media_uses rows", prompt)
        self.assertIn("stable @p/@v/@a id", prompt)
        self.assertIn("never write a raw <picture n>", prompt)
        self.assertIn("request-local h3 ordinals", prompt)
        self.assertIn("three must-complete physical action beats", prompt)
        self.assertIn("continuity_state", prompt)
        self.assertIn("optional_flourish", prompt)
        self.assertIn("shots must be chronological and must not overlap", prompt)
        self.assertNotIn("when a treat each asset", prompt)

    def test_system_prompt_honors_standalone_special_binding(self):
        prompt = build_design_system_prompt({
            "bound_h3_skills": {
                "binding_mode": "standalone_special",
                "default": None,
                "special": {
                    "key": "wuxia-blade-film",
                    "standalone": True,
                    "instruction": "Ground every aerial action in physical contact.",
                },
            }
        }).lower()
        self.assertIn("selected standalone special skill", prompt)
        self.assertIn("default h3 skill", prompt)
        self.assertIn("intentionally absent", prompt)
        self.assertNotIn("bound default h3 skill and optional special", prompt)

    def test_t2i_prompt_rejects_h3_picture_token(self):
        payload = sample_design()
        payload["media_requests"][0]["prompt"] = (
            "Action reference of the assassin from <Picture 3> landing in the courtyard."
        )
        with self.assertRaisesRegex(ValueError, "Picture N"):
            normalize_design_plan(
                payload,
                {"image": 9, "video": 3, "audio": 3},
                strict_t2i_prompts=True,
            )

    def test_legacy_design_json_with_picture_tokens_still_loads_non_strict(self):
        payload = sample_design()
        payload["media_requests"][0]["prompt"] = (
            "Legacy identity reference based on <Picture 1>."
        )
        plan = normalize_design_plan(
            payload,
            {"image": 9, "video": 3, "audio": 3},
        )
        self.assertEqual(
            plan["media_requests"][0]["prompt"],
            "Legacy identity reference based on <Picture 1>.",
        )

    def test_t2i_prompt_rejects_self_or_future_image_dependency(self):
        payload = sample_design()
        payload["media_requests"][0]["prompt"] = (
            "Match the next image and preserve whatever character it will generate."
        )
        with self.assertRaisesRegex(ValueError, "depends on another image"):
            normalize_design_plan(
                payload,
                {"image": 9, "video": 3, "audio": 3},
                strict_t2i_prompts=True,
            )

    def test_time_scoped_action_reference_rejects_neutral_background(self):
        payload = sample_design()
        payload["media_requests"][0].update({
            "start_seconds": 4.0,
            "end_seconds": 8.0,
            "prompt": (
                "Action-state reference of the assassin rotating around the general's spear, "
                "dual swords extended, neutral background, no text."
            ),
        })
        with self.assertRaisesRegex(ValueError, "story's real in-world environment"):
            normalize_design_plan(
                payload,
                {"image": 9, "video": 3, "audio": 3},
                strict_t2i_prompts=True,
            )

    def test_global_identity_reference_may_keep_catalog_background(self):
        payload = sample_design()
        payload["media_requests"][0].update({
            "start_seconds": 0.0,
            "end_seconds": payload["duration_seconds"],
            "prompt": (
                "Full-body identity reference of one Tang general wearing dark-gold armor and "
                "holding his one rigid long spear, plain studio background, no text."
            ),
        })
        plan = normalize_design_plan(payload, {"image": 9, "video": 3, "audio": 3})
        self.assertEqual(len(plan["shots"]), 2)
        self.assertEqual(
            len([row for row in plan["media_requests"] if row["media_type"] == "image"]),
            1,
        )

    def test_design_plan_supports_two_minute_long_form_timeline(self):
        payload = sample_design()
        payload["duration_seconds"] = 120.0
        payload["shots"][-1]["end_seconds"] = 120.0
        plan = normalize_design_plan(payload, {"image": 9, "video": 3, "audio": 3})
        self.assertEqual(plan["duration_seconds"], 120.0)

    def test_tang_ting_ci_ying_demo_preserves_all_twenty_one_action_beats(self):
        demo = json.loads(
            (
                PROJECT_ROOT
                / "example"
                / "tang_ting_ci_ying_45s_demo"
                / "design_plan.json"
            ).read_text(encoding="utf-8")
        )
        plan = normalize_design_plan(demo, {"image": 9, "video": 3, "audio": 3})
        self.assertEqual(plan["duration_seconds"], 45.0)
        self.assertEqual(len(plan["shots"]), 21)
        self.assertEqual(len(plan["media_requests"]), 5)
        self.assertEqual(plan["shots"][0]["start_seconds"], 0.0)
        self.assertEqual(plan["shots"][-1]["end_seconds"], 45.0)
        for previous, current in zip(plan["shots"], plan["shots"][1:]):
            self.assertEqual(previous["end_seconds"], current["start_seconds"])

    def test_end_marker_is_clamped_and_final_hold_is_guaranteed(self):
        payload = sample_design()
        payload["markers"] = [{
            "time_seconds": 12.0,
            "preset": "End",
            "direction": "Complete the action",
        }]
        plan = normalize_design_plan(payload, {"image": 9, "video": 3, "audio": 3})
        self.assertEqual(plan["markers"][0]["time_seconds"], 11.5)
        self.assertTrue(any(item["preset"] == "Final Hold" for item in plan["markers"]))

    def test_unrequested_caption_is_removed_and_final_hold_is_added(self):
        payload = sample_design()
        payload["theme_text"] = "An invented advertising caption"
        payload["theme_text_explicit_user_requested"] = False
        payload["text_layers"] = [{
            "start_seconds": 9.5,
            "end_seconds": 12.0,
            "track": "V3",
            "content": "A description that should not be printed on screen",
            "role": "on_screen_text",
            "speaker": "S1",
            "language": "English",
            "delivery": "Natural",
            "lip_sync": True,
            "explicit_user_requested": False,
        }]
        payload["markers"] = []
        plan = normalize_design_plan(payload, {"image": 9, "video": 3, "audio": 3})
        self.assertEqual(plan["text_layers"], [])
        self.assertFalse(plan["theme_text_explicit_user_requested"])
        self.assertEqual(plan["markers"][0]["preset"], "Final Hold")
        self.assertEqual(plan["markers"][0]["time_seconds"], 11.0)

    def test_capacity_is_enforced_before_material_creation(self):
        payload = sample_design()
        payload["media_requests"].append(dict(payload["media_requests"][0]))
        with self.assertRaisesRegex(ValueError, "only 1 slots"):
            normalize_design_plan(payload, {"image": 1, "video": 3, "audio": 3})

    def test_materialize_creates_timed_keyword_placeholders_and_sidecars(self):
        plan = normalize_design_plan(sample_design(), {"image": 9, "video": 3, "audio": 3})
        root = PROJECT_ROOT / ".director_cache" / "design_engine_test"
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        try:
            design_dir, outputs = materialize_design_media(
                plan, root, load_runtime_paths().ffmpeg
            )
            self.assertTrue((design_dir / "design_plan.json").is_file())
            self.assertEqual(len(outputs), 2)
            image = Path(outputs[0]["local_path"])
            audio = Path(outputs[1]["local_path"])
            self.assertTrue(image.is_file())
            self.assertTrue(audio.is_file())
            self.assertIn("00.00-04.00_hand_cola_can", image.name)
            self.assertTrue(image.with_suffix(image.suffix + ".request.json").is_file())
            saved = json.loads((design_dir / "design_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["theme_text"], "OPEN HAPPINESS")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_materialize_only_creates_missing_requests_not_existing_media(self):
        payload = sample_design()
        payload["existing_media_uses"] = [{
            "requirement_id": "hero_product",
            "media_id": "P1",
            "media_type": "image",
            "usage": "h3_reference",
            "reuse_policy": "whole_design",
            "start_seconds": 0,
            "end_seconds": 12,
            "track": "V1",
            "subject_keywords": ["cola can"],
            "instruction": "Preserve the exact supplied product.",
        }]
        payload["media_requests"][0]["requirement_id"] = "hero_product"
        plan = normalize_design_plan(
            payload,
            {"image": 9, "video": 3, "audio": 3},
            existing_media=[{
                "media_id": "P1",
                "media_type": "image",
                "loaded": True,
            }],
        )
        root = PROJECT_ROOT / ".director_cache" / "design_existing_media_test"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        try:
            design_dir, outputs = materialize_design_media(
                plan, root, load_runtime_paths().ffmpeg
            )
            self.assertEqual([item["media_type"] for item in outputs], ["audio"])
            saved = json.loads((design_dir / "design_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["existing_media_uses"][0]["media_id"], "P1")
            self.assertEqual(len(saved["media_requests"]), 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

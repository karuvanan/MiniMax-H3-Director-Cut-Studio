import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from design_cleanup_service import cleanup, lm_origin, unload_lm_studio
from design_ai_service import handle as handle_design_ai_job
from design_engine import materialize_design_media, normalize_design_plan
from design_media_service import image_workflow
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
        self.assertEqual(workflow["9"]["inputs"]["images"], ["32", 0])

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

    def test_normalize_snaps_director_plan_to_half_seconds(self):
        plan = normalize_design_plan(sample_design(), {"image": 9, "video": 3, "audio": 3})
        self.assertEqual(plan["duration_seconds"], 12.0)
        self.assertEqual((plan["shots"][0]["start_seconds"], plan["shots"][0]["end_seconds"]), (0.0, 4.0))
        self.assertEqual(plan["transitions"][0]["time_seconds"], 4.0)
        self.assertEqual(plan["markers"][0]["time_seconds"], 11.0)

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


if __name__ == "__main__":
    unittest.main()

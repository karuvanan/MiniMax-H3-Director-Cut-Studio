from pathlib import Path
import unittest
from unittest.mock import patch

from design_ai_service import generate as generate_structured_ai
from design_settings import DesignAISettings, load_design_settings, save_design_settings
from media_semantic_enrichment import (
    MEDIA_SEMANTIC_ENRICHMENT_SCHEMA,
    SEMANTIC_ENRICHMENT_START,
    build_enrichment_job_context,
    build_media_enrichment_prompts,
    enrichment_fingerprint,
    extract_semantic_enrichment,
    merge_semantic_enrichment,
    normalize_semantic_enrichment,
    strip_semantic_enrichment,
    truncate_evidence,
)
from runtime_paths import PROJECT_ROOT


def sample_enrichment() -> dict:
    return {
        "media_id": "P1",
        "media_type": "image",
        "evidence_fingerprint": "a" * 64,
        "summary": "A black-clad Tang assassin prepares an ambush in a courtyard.",
        "observed_facts": [
            "One person wears dark clothing.",
            "A bronze cauldron stands beside a white wall.",
        ],
        "subjects": [
            {
                "label": "assassin",
                "appearance": "slim adult figure with tied dark hair",
                "wardrobe": "layered black Tang-style clothing",
                "action": "leans forward in a ready stance",
            }
        ],
        "objects_and_props": ["bronze cauldron", "two short swords"],
        "environment": "White courtyard wall and black roof tiles.",
        "composition_and_camera": "Medium-wide view from a slightly low camera angle.",
        "lighting_and_color": "Warm side light with a black, bronze and white palette.",
        "motion_and_temporal_changes": "Red leaves move from left to right.",
        "audio_and_speech": "No audio evidence was supplied.",
        "h3_prompt_keywords": ["Tang courtyard", "black-clad assassin", "bronze cauldron"],
        "suggested_h3_usage": "Use as the assassin identity and courtyard reference.",
        "shot_adaptations": [],
        "uncertain_inferences": ["The figure may be preparing to attack."],
    }


class MediaSemanticEnrichmentTests(unittest.TestCase):
    def test_schema_requires_fact_inference_and_uncertainty_layers(self):
        required = set(MEDIA_SEMANTIC_ENRICHMENT_SCHEMA["required"])
        self.assertIn("observed_facts", required)
        self.assertIn("uncertain_inferences", required)
        self.assertIn("h3_prompt_keywords", required)
        self.assertIn("shot_adaptations", required)
        self.assertFalse(MEDIA_SEMANTIC_ENRICHMENT_SCHEMA["additionalProperties"])

    def test_prompt_uses_bounded_evidence_and_never_exposes_absolute_path(self):
        private_root = PROJECT_ROOT / "private" / "characters"
        private_file = private_root / "assassin_identity.png"
        recognition = (
            "MEDIA ANALYSIS\n"
            f"Source file: {private_file}\n"
            "BLIP visual caption: a black-clad assassin beside a bronze cauldron\n"
            "The white courtyard wall and black roof tiles are visible."
        )
        context = build_enrichment_job_context(
            media_id="p1",
            media_type="image",
            filename=str(private_file),
            recognition=recognition,
            duration_seconds=12.0,
            timeline_start_seconds=1.0,
            timeline_end_seconds=8.0,
            clip_prompt="Preserve only details supported by the supplied identity image.",
            max_evidence_chars=500,
        )
        system_prompt, user_prompt = build_media_enrichment_prompts(context)
        serialized = system_prompt + "\n" + user_prompt

        self.assertEqual(context["media_id"], "P1")
        self.assertEqual(context["filename"], private_file.name)
        self.assertNotIn(str(private_root), serialized)
        self.assertNotIn(str(private_file), serialized)
        self.assertIn(private_file.name, user_prompt)
        self.assertIn("directly supported observations", system_prompt)
        self.assertIn("uncertain_inferences", system_prompt)
        self.assertIn("labelled spatial", system_prompt)
        self.assertIn("not direct visual evidence", system_prompt)
        self.assertIn("BLIP visual caption", user_prompt)
        self.assertLessEqual(len(context["machine_evidence"]), 500)

    def test_long_evidence_is_bounded_but_preserves_both_ends(self):
        source = "HEAD-OBSERVATION\n" + ("middle evidence " * 5000) + "\nTAIL-OBSERVATION"
        result = truncate_evidence(source, 800)
        self.assertLessEqual(len(result), 800)
        self.assertTrue(result.startswith("HEAD-OBSERVATION"))
        self.assertTrue(result.endswith("TAIL-OBSERVATION"))
        self.assertIn("truncated", result.lower())

    def test_normalize_rejects_invalid_field_types_and_drops_unknown_properties(self):
        payload = sample_enrichment()
        payload["observed_facts"] = {"not": "an array"}
        with self.assertRaisesRegex(ValueError, "observed_facts"):
            normalize_semantic_enrichment(payload)

        payload = sample_enrichment()
        payload["unrequested_field"] = "must not pass strict normalization"
        self.assertNotIn("unrequested_field", normalize_semantic_enrichment(payload))

    def test_context_rejects_invalid_media_id_and_type(self):
        common = {
            "filename": "reference.png",
            "recognition": "BLIP visual caption: a person",
        }
        with self.assertRaisesRegex(ValueError, "media_id|Media ID"):
            build_enrichment_job_context(
                media_id="V1",
                media_type="image",
                **common,
            )
        with self.assertRaisesRegex(ValueError, "media_type|media type"):
            build_enrichment_job_context(
                media_id="P1",
                media_type="document",
                **common,
            )

    def test_normalize_rejects_response_for_another_asset_or_stale_evidence(self):
        payload = sample_enrichment()
        with self.assertRaisesRegex(ValueError, "media_id|media id|P2"):
            normalize_semantic_enrichment(payload, expected_media_id="P2")
        with self.assertRaisesRegex(ValueError, "media_type|media type|video"):
            normalize_semantic_enrichment(payload, expected_media_type="video")
        with self.assertRaisesRegex(ValueError, "fingerprint|stale|changed"):
            normalize_semantic_enrichment(payload, expected_fingerprint="b" * 64)

        normalized = normalize_semantic_enrichment(
            payload,
            expected_media_id="p1",
            expected_media_type="image",
            expected_fingerprint="a" * 64,
        )
        self.assertEqual(normalized["media_id"], "P1")

    def test_merge_is_idempotent_and_preserves_raw_recognition_verbatim(self):
        raw = (
            "MEDIA ANALYSIS\n"
            "BLIP visual caption: a black-clad assassin\n"
            "Inference device: cuda:0\n"
            "WHISPER TRANSCRIPT\nNo confident speech was transcribed."
        )
        first = merge_semantic_enrichment(raw, sample_enrichment())
        updated = sample_enrichment()
        updated["summary"] = "Updated grounded summary."
        second = merge_semantic_enrichment(first, updated)

        self.assertEqual(strip_semantic_enrichment(second), raw)
        self.assertEqual(second.count(SEMANTIC_ENRICHMENT_START), 1)
        self.assertNotIn(sample_enrichment()["summary"], extract_semantic_enrichment(second))
        self.assertIn("Updated grounded summary.", extract_semantic_enrichment(second))

    def test_fingerprint_is_stable_and_changes_with_any_source_evidence(self):
        base = {
            "media_id": "P1",
            "media_type": "image",
            "filename": "assassin.png",
            "recognition": "BLIP visual caption: a black-clad assassin",
            "clip_prompt": "Preserve identity.",
        }
        first = enrichment_fingerprint(**base)
        self.assertEqual(first, enrichment_fingerprint(**base))
        self.assertNotEqual(
            first,
            enrichment_fingerprint(**{**base, "recognition": base["recognition"] + " beside a cauldron"}),
        )
        self.assertNotEqual(
            first,
            enrichment_fingerprint(**{**base, "clip_prompt": "Preserve wardrobe."}),
        )
        self.assertNotEqual(
            first,
            enrichment_fingerprint(
                **base,
                timeline_start_seconds=4.0,
                timeline_end_seconds=8.0,
            ),
        )
        self.assertRegex(first, r"^[0-9a-f]{64}$")

    def test_design_ai_service_uses_custom_schema_name_and_clamps_token_budget(self):
        response = {
            "choices": [{"message": {"content": "{}"}}],
        }
        with patch("design_ai_service.request_json", return_value=response) as request:
            generate_structured_ai({
                "provider": "lm_studio",
                "base_url": "http://127.0.0.1:1234/v1",
                "model": "local-model",
                "system_prompt": "system",
                "user_prompt": "user",
                "schema": MEDIA_SEMANTIC_ENRICHMENT_SCHEMA,
                "schema_name": "media semantic/enrichment!",
                "max_output_tokens": 99999,
                "timeout": 30,
            })
        request_payload = request.call_args.kwargs["payload"]
        self.assertEqual(request_payload["max_tokens"], 12000)
        self.assertEqual(
            request_payload["response_format"]["json_schema"]["name"],
            "media_semantic_enrichment_",
        )

        with patch("design_ai_service.request_json", return_value=response) as request:
            generate_structured_ai({
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-test",
                "system_prompt": "system",
                "user_prompt": "user",
                "schema": MEDIA_SEMANTIC_ENRICHMENT_SCHEMA,
                "schema_name": "semantic",
                "max_output_tokens": 1,
            })
        request_payload = request.call_args.kwargs["payload"]
        self.assertEqual(request_payload["max_output_tokens"], 512)

    def test_design_settings_semantic_enrichment_booleans_round_trip(self):
        target = PROJECT_ROOT / ".director_cache" / "semantic_enrichment_settings_test.env"
        settings = DesignAISettings(
            auto_semantic_enrichment=True,
            unload_lm_after_semantic_enrichment=False,
        )
        try:
            save_design_settings(target, settings)
            saved = target.read_text(encoding="utf-8")
            self.assertIn("H3_DESIGN_AUTO_SEMANTIC_ENRICHMENT=true", saved)
            self.assertIn("H3_DESIGN_UNLOAD_LM_AFTER_SEMANTIC_ENRICHMENT=false", saved)
            restored = load_design_settings(target)
            self.assertTrue(restored.auto_semantic_enrichment)
            self.assertFalse(restored.unload_lm_after_semantic_enrichment)
        finally:
            target.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

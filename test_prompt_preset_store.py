from pathlib import Path
import unittest
import uuid

from prompt_preset_store import (
    delete_prompt_preset,
    ensure_prompt_presets,
    family_env_path,
    load_prompt_presets,
    save_prompt_preset,
)
from runtime_paths import PROJECT_ROOT


class PromptPresetStoreTests(unittest.TestCase):
    def test_requested_prompt_families_have_exact_env_filenames(self):
        root = Path("preset_env")
        expected = {
            "creative_brief": "creative_brief.env",
            "global_visual_style": "global_visual_style.env",
            "transition_language": "transition_language.env",
            "constraints_and_technical_rules": "constraints_and_technical_rules.env",
            "overall_soundscape": "overall_soundscape.env",
            "non_diegetic_music": "non_diegetic_music.env",
        }
        self.assertEqual(
            {family: family_env_path(root, family).name for family in expected},
            expected,
        )

    def test_each_prompt_family_uses_one_env_file_and_presets_remain_editable(self):
        root = PROJECT_ROOT / ".director_cache" / "preset_store_tests"
        family = f"test_{uuid.uuid4().hex}"
        try:
            ensure_prompt_presets(
                root,
                family,
                {"Scene One": "First scene direction", "Scene Two": "Second scene direction"},
            )
            records = load_prompt_presets(root, family)
            self.assertEqual(len(records), 2)
            self.assertEqual(len({record.path for record in records}), 1)
            self.assertTrue(all(record.path.suffix == ".env" for record in records))
            self.assertEqual(records[0].path, family_env_path(root, family))

            first = records[0]
            save_prompt_preset(
                root,
                family,
                first.name,
                "Edited scene direction",
                previous_name=first.name,
            )
            edited = next(item for item in load_prompt_presets(root, family) if item.path == first.path)
            self.assertEqual(edited.text, "Edited scene direction")

            custom = save_prompt_preset(
                root,
                family,
                "My Custom Scene",
                "A user-authored scene",
            )
            self.assertEqual(custom.path, first.path)
            self.assertEqual(len(load_prompt_presets(root, family)), 3)
            self.assertTrue(delete_prompt_preset(root, custom))
            self.assertEqual(len(load_prompt_presets(root, family)), 2)
        finally:
            path = family_env_path(root, family)
            if path.is_file():
                path.unlink()


if __name__ == "__main__":
    unittest.main()

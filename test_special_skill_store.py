from pathlib import Path
import unittest

from special_skill_store import (
    STANDALONE_MARKER,
    SpecialSkillDocument,
    load_special_skill_document,
    save_special_skill_document,
    validate_special_skill_document,
)


class SpecialSkillStoreTests(unittest.TestCase):
    @staticmethod
    def _root(key: str) -> Path:
        root = Path(__file__).parent / ".director_cache" / "special_skill_store_tests"
        folder = root / key
        folder.mkdir(parents=True, exist_ok=True)
        for filename in (
            "SKILL.md", "SKILL.cn.md", "SKILL.md.tmp", "SKILL.cn.md.tmp",
            "DESIGN_REQUIREMENT.txt", "DESIGN_REQUIREMENT.txt.tmp",
        ):
            target = folder / filename
            if target.is_file():
                target.unlink()
        return root

    def test_default_plus_special_round_trip_writes_english_and_chinese(self):
        key = "night-market-drama"
        root = self._root(key)
        saved = save_special_skill_document(
            root,
            SpecialSkillDocument(
                key=key,
                description="Direct a compact night-market drama for H3.",
                body="# Night Market Drama\n\nPreserve exact dialogue in `text_layers`.",
                chinese_body="# 夜市短剧\n\n逐字保留 `text_layers` 对白。",
                design_requirement_template="Create a 30-second night-market drama.",
            ),
            editing_key=key,
        )
        english = saved.path.read_text(encoding="utf-8")
        chinese = (saved.path.parent / "SKILL.cn.md").read_text(encoding="utf-8")
        self.assertIn("name: night-market-drama", english)
        self.assertIn("Direct a compact night-market drama", english)
        self.assertNotIn(STANDALONE_MARKER, english)
        self.assertIn("夜市短剧", chinese)
        self.assertEqual(
            (saved.path.parent / "DESIGN_REQUIREMENT.txt").read_text(encoding="utf-8").strip(),
            "Create a 30-second night-market drama.",
        )
        loaded = load_special_skill_document(saved.path.parent)
        self.assertEqual(loaded.key, "night-market-drama")
        self.assertFalse(loaded.standalone)
        self.assertEqual(
            loaded.design_requirement_template,
            "Create a 30-second night-market drama.",
        )

    def test_standalone_round_trip_uses_explicit_binding_marker(self):
        key = "standalone-layout"
        root = self._root(key)
        saved = save_special_skill_document(
            root,
            SpecialSkillDocument(
                key=key,
                description="Produce a standalone layout document.",
                body="# Standalone Layout\n\nReturn only the requested layout.",
                standalone=True,
            ),
            editing_key=key,
        )
        text = saved.path.read_text(encoding="utf-8")
        self.assertIn(STANDALONE_MARKER, text)
        self.assertTrue(load_special_skill_document(saved.path.parent).standalone)

    def test_edit_can_remove_optional_chinese_version(self):
        key = "editable-drama"
        root = self._root(key)
        document = SpecialSkillDocument(
            key=key,
            description="An editable drama skill.",
            body="# Editable Drama\n\nPlan the drama.",
            chinese_body="# 可编辑短剧\n\n规划短剧。",
            design_requirement_template="Create an editable drama.",
        )
        saved = save_special_skill_document(root, document, editing_key=key)
        self.assertTrue((saved.path.parent / "SKILL.cn.md").is_file())
        document.chinese_body = ""
        document.design_requirement_template = ""
        save_special_skill_document(root, document, editing_key=document.key)
        self.assertFalse((saved.path.parent / "SKILL.cn.md").exists())
        self.assertFalse((saved.path.parent / "DESIGN_REQUIREMENT.txt").exists())

    def test_rejects_invalid_or_reserved_keys(self):
        for key in ("../escape", "Uppercase", "two--hyphens", "h3-prompt-writing"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_special_skill_document(
                    SpecialSkillDocument(
                        key=key,
                        description="Invalid key test.",
                        body="# Invalid\n\nBody.",
                    )
                )

    def test_every_bundled_special_skill_is_creator_valid_and_has_a_template(self):
        root = Path(__file__).parent / "skill special"
        folders = sorted(
            folder for folder in root.iterdir()
            if folder.is_dir() and (folder / "SKILL.md").is_file()
        )
        self.assertTrue(folders)
        for folder in folders:
            with self.subTest(skill=folder.name):
                document = load_special_skill_document(folder)
                validate_special_skill_document(document)
                self.assertTrue(document.design_requirement_template.strip())


if __name__ == "__main__":
    unittest.main()

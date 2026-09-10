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

    def test_street_fighter_skill_enforces_full_speed_and_visible_camera_displacement(self):
        root = Path(__file__).parent / "skill special" / "street-fighter-live-action-h3"
        english = (root / "SKILL.md").read_text(encoding="utf-8")
        chinese = (root / "SKILL.cn.md").read_text(encoding="utf-8")
        template = (root / "DESIGN_REQUIREMENT.txt").read_text(encoding="utf-8")

        self.assertIn("physical FPV", english)
        self.assertIn("实体FPV", chinese)
        self.assertIn("实体飞行", template)
        self.assertIn("very fast", english)
        self.assertIn("very fast", chinese)
        self.assertIn("very fast", template)
        self.assertIn("0.5", english)
        self.assertIn("0.5", chinese)
        self.assertIn("0.45", template)
        self.assertIn("FULL-SPEED FIGHT ONLY", english)
        self.assertIn("FULL-SPEED FIGHT ONLY", chinese)
        self.assertIn("Dialogue-aware timing", english)
        self.assertIn("Dialogue Track", template)
        self.assertIn("18 executable action Shots", english)
        self.assertIn("18个可执行动作Shot", chinese)
        self.assertIn("全片18个Shot", template)
        self.assertIn("bare-handed by default", english)
        self.assertIn("no more than **two closed-fist punches**", english)
        self.assertIn("默认**完全徒手**", chinese)
        self.assertIn("闭拳Punch总数最多**两次**", chinese)
        self.assertIn("严禁拳套", template)
        self.assertIn("每15秒闭拳Punch最多两次", template)
        self.assertIn("at least five orbital camera sectors", english)
        self.assertIn("五种肉眼可分的摄影角度", chinese)

    def test_hong_kong_comic_fighter_is_source_led_and_has_reusable_template(self):
        root = Path(__file__).parent / "skill special" / "hong-kong-comic-fighter"
        document = load_special_skill_document(root)
        validate_special_skill_document(document)
        english = (root / "SKILL.md").read_text(encoding="utf-8")
        chinese = (root / "SKILL.cn.md").read_text(encoding="utf-8")
        template = (root / "DESIGN_REQUIREMENT.txt").read_text(encoding="utf-8")
        self.assertEqual(document.key, "hong-kong-comic-fighter")
        self.assertIn("Source-derived world-scale force", english)
        self.assertIn("世界级力量与背景因果链", chinese)
        self.assertIn("{{HONG_KONG_COMIC_SOURCE_EVIDENCE}}", template)
        self.assertIn("禁止从Skill硬塞九龙菜市场", template)
        self.assertIn("source_img2img", template)
        self.assertIn("局部热浪式空间透镜扭曲", template)
        self.assertIn("每个完整招式", template)
        self.assertIn("太阳系力量", template)
        self.assertIn("on_screen_text", template)
        self.assertIn("港漫旁白", chinese)
        self.assertIn("solar signature technique", english)

    def test_cinematic_story_60s_skill_has_adaptation_and_overlap_contract(self):
        root = Path(__file__).parent / "skill special" / "cinematic-story-60s-director"
        document = load_special_skill_document(root)
        validate_special_skill_document(document)
        english = (root / "SKILL.md").read_text(encoding="utf-8")
        chinese = (root / "SKILL.cn.md").read_text(encoding="utf-8")
        template = (root / "DESIGN_REQUIREMENT.txt").read_text(encoding="utf-8")
        self.assertEqual(document.key, "cinematic-story-60s-director")
        self.assertIn("60.00 seconds as the initial target", english)
        self.assertIn("约60秒的MiniMax H3电影短剧", chinese)
        self.assertIn("故事内容如下", template)
        self.assertIn("explicit_user_requested=true", template)
        self.assertNotIn(r"explicit\_user\_requested", template)
        self.assertIn("Overlap Policy默认使用AUTO", template)
        self.assertIn("只有语音却没有Shot", template)
        self.assertIn("不得虚构素材编号", template)

    def test_beat_synced_entrance_skill_locks_master_audio_and_reference_roles(self):
        root = Path(__file__).parent / "skill special" / "beat-synced-entrance-18s"
        document = load_special_skill_document(root)
        validate_special_skill_document(document)
        english = (root / "SKILL.md").read_text(encoding="utf-8")
        chinese = (root / "SKILL.cn.md").read_text(encoding="utf-8")
        template = (root / "DESIGN_REQUIREMENT.txt").read_text(encoding="utf-8")
        self.assertEqual(document.key, "beat-synced-entrance-18s")
        self.assertIn("0.00–6.50s", english)
        self.assertIn("P3 is a person or featured visual beat", english)
        self.assertIn("P3不是走廊图", chinese)
        for reference in ("@P1", "@P2", "@P3", "@P4", "@A1"):
            self.assertIn(reference, template)
        self.assertIn("P3不是走廊图", template)
        self.assertIn("P3用于9.00–11.00秒", template)
        self.assertIn("走廊由H3生成", chinese)
        self.assertIn("Source In 15.00秒", template)
        self.assertIn("45–60%", template)
        self.assertIn("non_diegetic_music设为N/A", template)
        self.assertIn("不得生成额外背景音乐", template)
        self.assertIn("禁止播放按钮", template)


if __name__ == "__main__":
    unittest.main()

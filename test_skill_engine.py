from pathlib import Path
from copy import deepcopy
import re
import unittest

from design_engine import (
    build_design_system_prompt,
    normalize_design_plan,
    render_special_design_requirement_template,
    street_fighter_character_bindings,
)

from media_semantic_enrichment import enrichment_fingerprint
from prompt_engine import PromptSpec
from skill_engine import (
    DEFAULT_SKILL,
    SPECIAL_SKILL,
    build_ref2va_prompt,
    load_skill_profiles,
    profile_system_prompt,
)
from workflow_engine import MediaAsset


class SkillEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = load_skill_profiles(Path(__file__).parent)

    def test_loads_default_and_special_profiles(self):
        self.assertIn(DEFAULT_SKILL, self.profiles)
        self.assertIn(SPECIAL_SKILL, self.profiles)
        folder_names = {
            folder.name
            for folder in (Path(__file__).parent / "skill special").iterdir()
            if folder.is_dir() and (folder / "SKILL.md").is_file()
        }
        discovered = {key for key, profile in self.profiles.items() if profile.special}
        self.assertEqual(discovered, folder_names)
        self.assertIn("subject_definitions", self.profiles[DEFAULT_SKILL].h3_reference_guide)
        self.assertIn("Typography Rules", self.profiles[SPECIAL_SKILL].instruction)

    def test_timed_dialogue_track_is_independent_and_emitted_once(self):
        spec = PromptSpec(
            brief="A woman speaks directly to camera.",
            shots=["Medium close-up; she maintains eye contact."],
            shot_ranges=[{
                "start_seconds": 0.0,
                "end_seconds": 3.0,
                "description": "Medium close-up; she maintains eye contact.",
            }],
            text_ranges=[{
                "layer_id": "T1",
                "track_id": "A4",
                "start_seconds": 0.0,
                "end_seconds": 3.0,
                "content_role": "dialogue",
                "text": "你好，这句话不能改。",
                "speaker": "S1",
                "language": "Mandarin Chinese",
                "delivery": "Natural",
                "lip_sync": True,
                "supplied_audio_tag": "",
            }],
        )
        prompt = build_ref2va_prompt(
            spec,
            [],
            3.0,
            self.profiles[DEFAULT_SKILL],
        )
        self.assertIn("TIMELINE TYPE / DIALOGUE TRACK EVENTS", prompt)
        self.assertIn("[Dialogue Track A4/T1", prompt)
        self.assertEqual(prompt.count("你好，这句话不能改。"), 1)
        self.assertIn("increasing speaking pace rather than editing words", prompt)

    def test_special_profile_metadata_comes_from_each_folder(self):
        profile = self.profiles["music-video-subtitle-generator"]
        self.assertEqual(profile.path.parent.name, "music-video-subtitle-generator")
        self.assertTrue(profile.description)
        self.assertIn("Music Video", profile.display_name)

    def test_analysis_only_special_discovery_text_never_primes_h3_pixels(self):
        special = self.profiles["drone-fly-on-city"]
        self.assertIn("red route", special.description.lower())
        skill_text = special.path.read_text(encoding="utf-8-sig")
        self.assertIn(
            "Clean photographic scene with unobstructed architecture",
            skill_text,
        )
        self.assertIn("visible flight path, orbit ring, circular light trail", skill_text)
        self.assertIn("Still-reference Isolation", skill_text)
        self.assertIn("专用Z-Image负面词", special.design_requirement_template)
        self.assertIn("P3至P9", special.design_requirement_template)
        self.assertNotIn("Kuala Lumpur", special.instruction)
        self.assertNotIn("Petronas", special.instruction)
        prompt = build_ref2va_prompt(
            PromptSpec(
                brief="A clean city flyover.",
                style="Photoreal skyline. No visible route graphics or waypoint markers.",
                shots=["Camera arcs left, then right with a stable horizon."],
            ),
            [],
            6.0,
            self.profiles[DEFAULT_SKILL],
            special,
        )
        self.assertNotIn("red route", prompt.lower())
        self.assertNotIn("route graphics", prompt.lower())
        self.assertNotIn("waypoint marker", prompt.lower())
        self.assertNotIn(special.description, prompt)
        self.assertIn("approved Drone Fly On City Director cues", prompt)

    def test_drone_fireworks_profile_preserves_route_isolation_and_effect_ledger(self):
        special = self.profiles["drone-fly-on-city-fireworks"]
        self.assertFalse(special.standalone)
        self.assertIn("fireworks", special.description.lower())
        self.assertIn("Fireworks Physics and Continuity Ledger", special.instruction)
        self.assertIn("separate radial particle bursts", special.instruction)
        self.assertIn("analysis_only/whole_design", special.instruction)
        self.assertIn("P3至P9", special.design_requirement_template)
        self.assertRegex(special.design_requirement_template, r"离散(?:烟花|粒子)")
        self.assertIn("绿色圆点标记起点", special.design_requirement_template)
        self.assertIn("蓝色圆点标记终点", special.design_requirement_template)
        self.assertIn("P1实际图片", special.design_requirement_template)
        self.assertIn("ROUTE NEEDS REVIEW", special.design_requirement_template)
        self.assertNotIn("Kuala Lumpur", special.instruction)
        self.assertNotIn("Petronas", special.instruction)
        prompt = build_ref2va_prompt(
            PromptSpec(
                brief="A photoreal night skyline celebration.",
                style="Cool blue city light with warm gold fireworks.",
                shots=[
                    "A smooth clockwise orbit rises while discrete fireworks bloom behind the towers."
                ],
            ),
            [],
            15.0,
            self.profiles[DEFAULT_SKILL],
            special,
        )
        self.assertNotIn("red route", prompt.lower())
        self.assertNotIn("route graphics", prompt.lower())
        self.assertIn("approved Drone Fly On City Fireworks Director cues", prompt)

    def test_every_special_skill_has_an_editable_design_requirement_template(self):
        special_profiles = [profile for profile in self.profiles.values() if profile.special]
        self.assertTrue(special_profiles)
        for profile in special_profiles:
            with self.subTest(skill=profile.key):
                self.assertTrue(profile.design_requirement_template.strip())
                self.assertLessEqual(len(profile.design_requirement_template), 20_000)

    def test_wuxia_special_binds_default_h3_skill(self):
        profile = self.profiles["wuxia-blade-film"]
        self.assertTrue(profile.special)
        self.assertFalse(profile.standalone)
        self.assertIn("45秒的唐朝写实高速武侠刺杀视频", profile.design_requirement_template)
        self.assertIn("没有明确写出的 @P／@V／@A 时不得虚构素材编号", profile.design_requirement_template)
        system = profile_system_prompt(self.profiles[DEFAULT_SKILL], profile)
        self.assertIn("DEFAULT H3 SKILL", system)
        self.assertIn("SPECIAL SCENE SKILL (wuxia-blade-film)", system)
        self.assertIn("weapon-driven causality", system)
        self.assertIn("Broken-blade inner-circle fighter", system)
        self.assertIn("Airborne twin-blade predator", system)
        self.assertIn("one frozen instant", system)
        self.assertIn("never depend on `he`", system)
        self.assertIn("Limb ledger", system)
        self.assertIn("Weapon-geometry ledger", system)
        self.assertIn("Damage ledger", system)
        self.assertIn("Feral collapse", system)
        self.assertIn(self.profiles[DEFAULT_SKILL].h3_reference_guide, system)

    def test_short_drama_special_is_default_bound_and_production_ready(self):
        profile = self.profiles["short-drama-h3-director"]
        self.assertTrue(profile.special)
        self.assertFalse(profile.standalone)
        system = profile_system_prompt(self.profiles[DEFAULT_SKILL], profile)
        self.assertIn("DEFAULT H3 SKILL", system)
        self.assertIn("SPECIAL SCENE SKILL (short-drama-h3-director)", system)
        for phrase in (
            "Preserve Authored Speech Verbatim",
            "text_layers",
            "existing_media_uses",
            "media_requests",
            "three must-complete physical beats",
            "episode hook",
            "one frozen instant",
        ):
            self.assertIn(phrase, system)
    def test_short_drama_special_has_chinese_mirror_and_upstream_license(self):
        folder = self.profiles["short-drama-h3-director"].path.parent
        chinese = (folder / "SKILL.cn.md").read_text(encoding="utf-8-sig")
        license_text = (folder / "THIRD_PARTY_LICENSE.txt").read_text(encoding="utf-8-sig")
        for phrase in ("短剧", "逐字", "text_layers", "existing_media_uses", "media_requests"):
            self.assertIn(phrase, chinese)
        self.assertIn("MIT License", license_text)
        self.assertIn("POUND0423/AI-drama-pound", license_text)

    def test_dark_rescue_special_is_default_bound_and_uses_proven_scene_grammar(self):
        profile = self.profiles["dark-rescue-h3"]
        self.assertTrue(profile.special)
        self.assertFalse(profile.standalone)
        self.assertIn("华尔街建筑风格", profile.design_requirement_template)
        self.assertIn("45秒救援视频", profile.design_requirement_template)
        system = profile_system_prompt(self.profiles[DEFAULT_SKILL], profile)
        self.assertIn("DEFAULT H3 SKILL", system)
        self.assertIn("SPECIAL SCENE SKILL (dark-rescue-h3)", system)
        for phrase in (
            "Use Only the Proven Visual-effect Palette",
            "Abandoned academic building",
            "Bangkok Yaowarat back lanes",
            "Kuala Lumpur Petaling Street back lanes",
            "Historical Kowloon dense interior",
            "Damaged high-rise office or Wall Street-inspired tower",
            "MUSIC AUTO",
            "must never cause the Skill to invent `@P1`",
            "preceding 24 frames are visual motion context only",
            "Director Design JSON",
        ):
            self.assertIn(phrase, system)

    def test_dark_rescue_special_has_matching_chinese_operational_contract(self):
        folder = self.profiles["dark-rescue-h3"].path.parent
        chinese = (folder / "SKILL.cn.md").read_text(encoding="utf-8-sig")
        for phrase in (
            "只使用已验证的光影效果库",
            "曼谷耀华力路后巷",
            "吉隆坡茨厂街后巷",
            "历史九龙密集室内",
            "受损高层办公室／华尔街风格大楼",
            "不能自行发明 `@P1`",
            "MUSIC TIMELINE",
            "Director Design JSON",
        ):
            self.assertIn(phrase, chinese)

    def test_dark_rescue_profiles_separate_physical_pov_from_external_camera(self):
        pov = self.profiles["dark-rescue-h3"]
        no_pov = self.profiles["dark-rescue-h3-no-pov"]
        for phrase in (
            "Prove POV Positively in the Image",
            "POV proof object",
            "extreme foreground",
            "body-caused parallax",
            "victim looks toward S2's eye line",
        ):
            self.assertIn(phrase, pov.instruction)
        self.assertIn("严格第一人称视角", pov.design_requirement_template)
        self.assertIn("External-camera Contract", no_pov.instruction)
        self.assertIn("No rescuer-eye POV", no_pov.instruction)
        self.assertIn("no-POV外部电影摄影机", no_pov.design_requirement_template)
        self.assertNotIn("The camera is physically inside S2", no_pov.instruction)

    def test_live_action_arcade_fighter_special_has_executable_short_fight_contract(self):
        profile = self.profiles["street-fighter-live-action-h3"]
        self.assertTrue(profile.special)
        self.assertFalse(profile.standalone)
        self.assertIn("准确45.00秒的电影级真人街机格斗短片", profile.design_requirement_template)
        self.assertIn("12个编号近身攻防Beat", profile.design_requirement_template)
        self.assertIn("36个编号动作且不得重复", profile.design_requirement_template)
        self.assertIn("MMA抱摔", profile.design_requirement_template)
        self.assertIn("受控降服", profile.design_requirement_template)
        self.assertIn("两人全程完全徒手", profile.design_requirement_template)
        self.assertIn("每15秒闭拳Punch最多两次", profile.design_requirement_template)
        self.assertIn("三个连续15秒Segment", profile.design_requirement_template)
        self.assertIn("香港九龙城寨风格的湿滑鱼类／海鲜／蔬菜市场", profile.design_requirement_template)
        self.assertIn("动作节奏为之前全速设定的2倍", profile.design_requirement_template)
        self.assertIn("Z-Image只生成两张", profile.design_requirement_template)
        self.assertIn("围绕S1与S2共同中点持续实体飞行", profile.design_requirement_template)
        self.assertIn("每个Shot都必须是正在发生的格斗", profile.design_requirement_template)
        self.assertIn("每15秒累计完成一次", profile.design_requirement_template)
        self.assertIn("Environmental Combat Physics", profile.design_requirement_template)
        self.assertIn("室外雨夜后巷", profile.design_requirement_template)
        self.assertIn("舞台Spot Light", profile.design_requirement_template)
        system = profile_system_prompt(self.profiles[DEFAULT_SKILL], profile)
        for phrase in (
            "Live-action Arcade Fighter H3 Director",
            "15-second structure",
            "30-second structure",
            "45-second structure — three different phases, 36 non-repeating beats",
            "Action Ledger",
            "bare-handed by default",
            "Action-variety contract",
            "Hong Kong Kowloon wet-market arena",
            "Environment Ledger",
            "fish, seafood and vegetable wet market",
            "exactly 12 numbered combat beats",
            "Four-style Close-combat Grammar",
            "Karate",
            "Judo",
            "Jeet Kune Do",
            "Wing Chun",
            "MMA Ground-game Variant",
            "single- or double-leg capture",
            "Grappling control",
            "Ground-and-pound",
            "Submission",
            "visible tap and immediate release",
            "At least 80%",
            "no more than 1.0 second",
            "Camera Ledger",
            "Visible continuous FPV-orbit contract",
            "Full 360-degree fight orbit",
            "physically flies clockwise",
            "same straight-on frontal angle in consecutive Shots",
            "Arcade combat coverage inside the FPV orbit",
            "Side-axis exchange",
            "Signature-move detail",
            "Full 360-degree fight orbit",
            "Do not use a theatre spotlight",
            "body load → release trajectory → contact point → recovery/result",
            "Projectile palm burst",
            "Rotating kick",
            "preceding 24 frames are silent visual motion context only",
            "two principal fighters only",
            "Never bake uncontrolled text",
            "Director Design JSON Contract",
        ):
            self.assertIn(phrase, system)
        folder = profile.path.parent
        chinese = (folder / "SKILL.cn.md").read_text(encoding="utf-8-sig")
        for phrase in (
            "15秒", "30秒", "45秒——三个不同阶段、36个不重复Beat",
            "Action Ledger", "默认**完全徒手**", "动作多样性合约",
            "香港九龙城寨湿货市场格斗场", "Environment Ledger", "海鲜通道",
            "准确12个", "四种近身攻防语法", "空手道", "柔道", "截拳道", "咏春",
            "MMA地面战变体", "抱摔（Takedown）", "地面压制（Grappling Control）",
            "地面打击（Ground and Pound）", "关节／绞技（Submission）", "至少80%",
            "Camera Ledger", "持续可见的FPV实体环绕合约", "每个15秒Segment至少依次经过五个机位区域",
            "FPV环绕中的街机格斗覆盖", "侧轴对拆", "招牌技局部",
            "全速360度格斗环绕",
            "舞台Spot Light", "身体蓄力", "掌心能量弹", "旋转踢", "Virtual Media Pool",
        ):
            self.assertIn(phrase, chinese)

    def test_street_fighter_template_binds_p1_p2_from_blip_then_ai_enrich(self):
        profile = self.profiles["street-fighter-live-action-h3"]
        media = [
            {
                "media_id": "P1", "media_type": "image", "loaded": True,
                "raw_analysis_summary": (
                    "BLIP VISUAL SUMMARY · CUDA\n"
                    "BLIP · Overview: a focused woman with braided black hair in a white gi"
                ),
                "semantic_enrichment": "SUMMARY\nThis fallback must not replace BLIP.",
            },
            {
                "media_id": "P2", "media_type": "image", "loaded": True,
                "raw_analysis_summary": "MEDIA\nNo BLIP overview yet.",
                "semantic_enrichment": (
                    "MEDIA: P2 (image)\n\nSUMMARY\nA muscular man in a red jacket.\n\n"
                    "SUBJECTS\n- fighter | appearance: muscular man with cropped hair | "
                    "wardrobe: red jacket and black trousers\n\nOBJECTS / PROPS\nNone established."
                ),
            },
        ]
        bindings = street_fighter_character_bindings(media)
        self.assertEqual([row["media_id"] for row in bindings], ["P1", "P2"])
        self.assertEqual(bindings[0]["evidence_source"], "BLIP · Overview")
        self.assertEqual(bindings[1]["evidence_source"], "AI Enrich")
        rendered = render_special_design_requirement_template(
            profile.design_requirement_template,
            profile.key,
            media,
        )
        self.assertNotIn("{{STREET_FIGHTER_CAST_BINDINGS}}", rendered)
        self.assertIn("S1是@P1（BLIP · Overview：a focused woman", rendered)
        self.assertIn("S2是@P2（AI Enrich：fighter | appearance: muscular man", rendered)
        self.assertIn("@P1只定义S1，@P2只定义S2", rendered)

    def test_street_fighter_normalization_forces_whole_design_cast_references(self):
        media = [
            {
                "media_id": "P1", "media_type": "image", "loaded": True,
                "raw_analysis_summary": "BLIP · Overview: a woman in a white sleeveless gi",
            },
            {
                "media_id": "P2", "media_type": "image", "loaded": True,
                "semantic_enrichment": "SUMMARY\nA man in a dark red jacket and black trousers.",
            },
        ]
        source = {
            "title": "Reference fighters",
            "creative_brief": "S1 and S2 exchange one close-range technique.",
            "global_visual_style": "Photoreal live-action fight.",
            "overall_soundscape": "Diegetic room tone and contact Foley.",
            "non_diegetic_music": "N/A",
            "constraints": "Two fighters only.",
            "duration_seconds": 5.0,
            "shots": [{
                "start_seconds": 0.0, "end_seconds": 5.0, "track": "V1",
                "preset": "Fight", "framing": "Close-up", "camera_angle": "Side",
                "camera_movement": "Lateral track", "movement_speed": "Fast",
                "movement_amplitude": "Medium", "subject_action": "S1 parries S2.",
                "environment_response": "Cloth snaps once.",
                "continuity_state": "S1 left, S2 right.", "optional_flourish": "",
                "additional_direction": "Keep the fight axis clear.",
            }],
            "text_layers": [], "transitions": [], "markers": [],
            "existing_media_uses": [], "media_requests": [{
                "requirement_id": "generic_male_female_fighters",
                "media_type": "image", "usage": "h3_reference",
                "reuse_policy": "whole_design", "start_seconds": 0.0,
                "end_seconds": 5.0, "track": "V3",
                "subject_keywords": ["two generic fighters"],
                "prompt": "Two generic fighters, one man and one woman, in a fighting pose.",
            }],
        }
        plan = normalize_design_plan(
            source,
            {"image": 9, "video": 3, "audio": 3},
            existing_media=media,
            special_skill_key="street-fighter-live-action-h3",
        )
        uses = {row["media_id"]: row for row in plan["existing_media_uses"]}
        self.assertEqual(set(uses), {"P1", "P2"})
        for media_id in ("P1", "P2"):
            self.assertEqual(uses[media_id]["reuse_policy"], "whole_design")
            self.assertEqual((uses[media_id]["start_seconds"], uses[media_id]["end_seconds"]), (0.0, 5.0))
            self.assertTrue(uses[media_id]["identity_anchor"])
        self.assertIn("S1 is exclusively @P1", plan["shots"][0]["additional_direction"])
        self.assertIn("S2 is exclusively @P2", plan["shots"][0]["additional_direction"])
        self.assertIn("P1/P2 ABSOLUTE CAST LOCK", plan["shots"][0]["additional_direction"])
        self.assertIn("HONG KONG KOWLOON WET-MARKET ARENA", plan["shots"][0]["additional_direction"])
        self.assertIn("2X ACTION CADENCE", plan["shots"][0]["additional_direction"])
        self.assertEqual(
            [row["requirement_id"] for row in plan["media_requests"]],
            [
                "street_fighter_kowloon_market_indoor_spectators",
                "street_fighter_kowloon_alley_outdoor_spectators",
            ],
        )
        indoor, outdoor = plan["media_requests"]
        self.assertEqual(indoor["reuse_policy"], "time_scoped")
        self.assertEqual((indoor["start_seconds"], indoor["end_seconds"]), (0.0, 3.5))
        self.assertIn("Twelve to eighteen", indoor["prompt"])
        self.assertIn("no principal fighter", indoor["prompt"])
        self.assertEqual(outdoor["reuse_policy"], "time_scoped")
        self.assertEqual((outdoor["start_seconds"], outdoor["end_seconds"]), (3.5, 5.0))
        self.assertIn("rainy Hong Kong", outdoor["prompt"])
        self.assertNotIn("generic_male_female_fighters", str(plan["media_requests"]))
        self.assertEqual(plan["environment_physics_schema_version"], 1)
        self.assertIn("environment_interaction", plan["shots"][0])
        self.assertIn("contact_target_id=env_", plan["shots"][0]["environment_interaction"])
        self.assertEqual(plan["markers"][-1]["preset"], "Final Combat Resolve")
        self.assertIn("settle both fighters", plan["markers"][-1]["direction"])
        system = build_design_system_prompt({
            "character_reference_bindings": street_fighter_character_bindings(media),
        })
        self.assertIn("CHARACTER REFERENCE BINDING CONTRACT", system)
        self.assertIn("S1 is exclusively @P1", system)
        self.assertIn("S2 is exclusively @P2", system)

    def test_street_fighter_normalization_forces_full_speed_fpv_combat_only(self):
        source = {
            "title": "Legacy camera repair",
            "creative_brief": "Two fighters in one arena.",
            "global_visual_style": "Photoreal live-action fight.",
            "overall_soundscape": "Diegetic contact Foley.",
            "non_diegetic_music": "N/A",
            "constraints": "Two fighters only.",
            "duration_seconds": 5.0,
            "shots": [{
                "start_seconds": 0.0, "end_seconds": 5.0, "track": "V1",
                "preset": "Fight", "framing": "Medium", "camera_angle": "Front",
                "camera_movement": "Slow pull-back zoom out", "movement_speed": "Slow",
                "movement_amplitude": "Small", "subject_action": "S1 walks slowly into frame.",
                "environment_response": "Room tone.", "continuity_state": "S1 left, S2 right.",
                "optional_flourish": "Bullet-time impact freeze.",
                "additional_direction": "Use slow motion and then walk away.",
            }],
            "text_layers": [], "transitions": [],
            "markers": [{
                "time_seconds": 4.0, "preset": "Final Hold",
                "direction": "Settle into a stable hold.",
            }],
            "existing_media_uses": [], "media_requests": [],
        }
        plan = normalize_design_plan(
            source,
            {"image": 9, "video": 3, "audio": 3},
            special_skill_key="street-fighter-live-action-h3",
        )
        shot = plan["shots"][0]
        self.assertEqual(shot["movement_speed"], "Very fast")
        self.assertEqual(shot["movement_amplitude"], "Large")
        self.assertIn("physical FPV clockwise orbital translation", shot["camera_movement"])
        self.assertNotIn("pull-back", shot["camera_movement"].casefold())
        self.assertNotIn("zoom out", shot["camera_movement"].casefold())
        self.assertIn("immediate full-speed attack", shot["subject_action"])
        self.assertNotIn("walk", shot["subject_action"].casefold())
        self.assertNotIn("slowly", shot["subject_action"].casefold())
        self.assertIn("CONTINUOUS FPV COMBAT ORBIT:", shot["additional_direction"])
        self.assertEqual(plan["markers"][0]["preset"], "Final Combat Resolve")
        self.assertNotIn("Final Hold", [row["preset"] for row in plan["markers"]])
        system = build_design_system_prompt({
            "bound_h3_skills": {
                "binding_mode": "default_plus_special",
                "special": {"key": "street-fighter-live-action-h3"},
            }
        })
        self.assertIn("STREET FIGHTER ENDING CONTRACT", system)
        self.assertIn("Add a Final Combat Resolve marker", system)
        self.assertIn("stable eye-level three-quarter composition", system)

    def test_ref2va_prompt_emits_two_exclusive_subject_definitions_for_fighters(self):
        p1 = MediaAsset(
            "137", "LoadImage", "image", "p1.png", "<Picture 1>",
            reference_id="P1", end_seconds=15.0,
            clip_prompt=(
                "CAST IDENTITY LOCK: S1 is exclusively @P1. Use @P1 as S1's authoritative "
                "face, hair, body, complete wardrobe, footwear and accessory reference."
            ),
        )
        p2 = MediaAsset(
            "139", "LoadImage", "image", "p2.png", "<Picture 2>",
            reference_id="P2", end_seconds=15.0,
            clip_prompt=(
                "CAST IDENTITY LOCK: S2 is exclusively @P2. Use @P2 as S2's authoritative "
                "face, hair, body, complete wardrobe, footwear and accessory reference."
            ),
        )
        prompt = build_ref2va_prompt(
            PromptSpec(
                brief="S1 and S2 perform one close-range exchange.",
                shots=["S1 parries S2 while both identities remain stable."],
            ),
            [p1, p2],
            15.0,
            self.profiles[DEFAULT_SKILL],
            self.profiles["street-fighter-live-action-h3"],
        )
        self.assertIn("<Subject 1> is the fighter", prompt)
        self.assertIn("come exclusively from <Picture 1>", prompt)
        self.assertIn("<Subject 2> is the fighter", prompt)
        self.assertIn("come exclusively from <Picture 2>", prompt)
        self.assertIn("Never assign this identity to <Subject 2>", prompt)
        self.assertIn("Never assign this identity to <Subject 1>", prompt)
        self.assertIn("never swap or blend the assigned fighters", prompt)

    def test_long_form_special_is_default_bound_and_batch_boundary_safe(self):
        profile = self.profiles["long-form-h3-director"]
        self.assertTrue(profile.special)
        self.assertFalse(profile.standalone)
        system = profile_system_prompt(self.profiles[DEFAULT_SKILL], profile)
        self.assertIn("DEFAULT H3 SKILL", system)
        self.assertIn("SPECIAL SCENE SKILL (long-form-h3-director)", system)
        for phrase in (
            "Plan Approval Horizons",
            "24 frames at 24 fps",
            "Incoming and Outgoing State",
            "never repeat, recap or re-perform",
            "exactly one Final Hold",
            "Segment-scoped media use",
            "one schema-valid Director Design JSON",
        ):
            self.assertIn(phrase, system)

    def test_long_form_special_has_chinese_mirror(self):
        folder = self.profiles["long-form-h3-director"].path.parent
        chinese = (folder / "SKILL.cn.md").read_text(encoding="utf-8-sig")
        for phrase in (
            "长片 H3 导演",
            "30 秒作为批准点",
            "最后 24 帧",
            "Incoming State",
            "Outgoing State",
            "逐字放进 `text_layers`",
            "Final Hold 只存在于真正项目终点",
        ):
            self.assertIn(phrase, chinese)

    def test_wuxia_english_and_chinese_skills_share_asymmetry_guardrails(self):
        profile = self.profiles["wuxia-blade-film"]
        english = profile.instruction
        chinese = (profile.path.parent / "SKILL.cn.md").read_text(encoding="utf-8-sig")
        for phrase in (
            "phantom grip",
            "no usable point",
            "Damage ledger",
            "Footing ledger",
            "Feral collapse",
            "orientation anchor",
        ):
            self.assertIn(phrase, english)
        for phrase in (
            "幽灵握持",
            "没有可用刀尖",
            "伤势账本",
            "脚下账本",
            "野兽式崩解",
            "方向锚点",
        ):
            self.assertIn(phrase, chinese)

    def test_wuxia_skill_repairs_unsuitable_input_before_design(self):
        profile = self.profiles["wuxia-blade-film"]
        english = profile_system_prompt(self.profiles[DEFAULT_SKILL], profile)
        chinese = (profile.path.parent / "SKILL.cn.md").read_text(encoding="utf-8-sig")
        for phrase in (
            "Repair Unsuitable Input Before Planning",
            "Always run an input-repair pass",
            "Do not preserve the raw Shot count",
            "nine five-second Shots",
            "roughly 60–120 degrees",
            "one primary camera movement per Shot",
            "zero budget warnings",
        ):
            self.assertIn(phrase, english)
        for phrase in (
            "规划前自动修正不合适的输入",
            "必须先执行输入修正",
            "原始 Shot 数量",
            "九个 5 秒 Shot",
            "大约 60–120 度",
            "每个 Shot 只选择一种主要镜头运动",
            "零条预算警告",
        ):
            self.assertIn(phrase, chinese)

    def test_wuxia_v3_design_brief_has_three_native_segments_and_nine_budgeted_shots(self):
        brief = (
            Path(__file__).parent / "example" / "one_leaf_kill_45s_design_requirement_v3.txt"
        ).read_text(encoding="utf-8-sig")
        headings = re.findall(
            r"^SHOT\s+(\d+)｜(\d+\.\d{2})–(\d+\.\d{2})s｜",
            brief,
            flags=re.M,
        )
        self.assertEqual(
            headings,
            [
                (str(index), f"{(index - 1) * 5:.2f}", f"{index * 5:.2f}")
                for index in range(1, 10)
            ],
        )
        self.assertIn("三个原生 15 秒 Segment", brief)
        self.assertIn("每个 Shot 的 `subject_action` 最多三个", brief)
        self.assertIn("飞镖始终飞向将军", brief)
        self.assertIn("禁止人物或武器复制", brief)
        self.assertIn("每张动作参考图只能表现一个冻结瞬间", brief)

    def test_wuxia_v3_design_json_loads_as_nine_exact_shots(self):
        import json

        source = json.loads(
            (Path(__file__).parent / "example" / "one_leaf_kill_45s_design_plan_v3.json")
            .read_text(encoding="utf-8")
        )
        plan = normalize_design_plan(
            source,
            {"image": 9, "video": 3, "audio": 3},
        )
        self.assertEqual(plan["duration_seconds"], 45.0)
        self.assertEqual(len(plan["shots"]), 9)
        self.assertEqual(
            [(shot["start_seconds"], shot["end_seconds"]) for shot in plan["shots"]],
            [(float(start), float(start + 5)) for start in range(0, 45, 5)],
        )
        self.assertEqual(
            [row["preferred_media_id"] for row in plan["media_requests"]],
            ["P1", "P2", "P3", "P4", "P5", "P6"],
        )
        self.assertEqual(plan["existing_media_uses"], [])
        self.assertTrue(
            any("primary character identity anchor" in row for row in plan["design_warnings"])
        )
        self.assertEqual(
            [row["time_seconds"] for row in plan["transitions"]],
            [15.0, 30.0],
        )
        self.assertTrue(
            all("<Picture" not in row["prompt"] for row in plan["media_requests"])
        )

    def test_ref_prompt_preserves_six_section_order(self):
        spec = PromptSpec(brief="A product rotates.", shots=["Hero product view", "Final hold"])
        asset = MediaAsset("1", "LoadImage", "image", "product.png", "<Picture 1>", "ref_images.ref_image_0", end_seconds=10)
        prompt = build_ref2va_prompt(spec, [asset], 10, self.profiles[DEFAULT_SKILL])
        sections = [
            "subject_definitions:",
            "summary:",
            "retention_analysis:",
            "detailed_description:",
            "overall_soundscape:",
            "non_diegetic_music:",
        ]
        positions = [prompt.index(section) for section in sections]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("summary:\n[reference generation]", prompt)
        self.assertIn("[Shot 2] At 00:05.000", prompt)

    def test_user_face_anchor_is_authoritative_and_support_picture_cannot_compete(self):
        spec = PromptSpec(brief="The same child runs throughout.", shots=["She runs."])
        face = MediaAsset(
            "1", "LoadImage", "image", "child.png", "<Picture 1>",
            "ref_images.ref_image_0", end_seconds=5.0,
            clip_prompt=(
                "Use this image as the strict identity anchor. Preserve the exact face throughout."
            ),
        )
        support = MediaAsset(
            "2", "LoadImage", "image", "track.png", "<Picture 2>",
            "ref_images.ref_image_1", end_seconds=5.0,
            clip_prompt=(
                "PRIMARY RECURRING CHARACTER IDENTITY ANCHOR. Show one clear, unobstructed, "
                "recognizable face with exact age range, facial structure, hair, skin tone, wardrobe "
                "and owned props suitable for reuse through the full story. "
                "SUPPORTING ENVIRONMENT OR ACTION-STATE REFERENCE ONLY. "
                "Do not define a different prominent human face."
            ),
        )
        prompt = build_ref2va_prompt(
            spec, [face, support], 5.0, self.profiles[DEFAULT_SKILL]
        )
        self.assertIn(
            "<Picture 1> is a reference image", prompt
        )
        self.assertIn(
            "<Subject 1> is the recurring human character whose exact recognizable face identity",
            prompt,
        )
        self.assertIn("come exclusively from <Picture 1>", prompt)
        self.assertIn("<Picture 2> may provide environment, prop, body-pose", prompt)
        self.assertIn("authoritative recurring face-identity source", prompt)
        self.assertIn("must not redefine the recurring character's face identity", prompt)
        self.assertIn("CHARACTER CONTINUITY CONTRACT", prompt)
        self.assertIn("upper and lower wardrobe style/color", prompt)
        self.assertIn("Expression, pose, arm/leg angles", prompt)
        self.assertIn("Never invent an appearance reset", prompt)
        self.assertNotIn("PRIMARY RECURRING CHARACTER IDENTITY ANCHOR", prompt)
        self.assertIn("summary:\n[reference generation]", prompt)

    def test_support_prompt_quoting_authority_cannot_steal_user_picture_identity(self):
        spec = PromptSpec(brief="The same child runs throughout.", shots=["She runs."])
        face = MediaAsset(
            "1", "LoadImage", "image", "child.png", "<Picture 1>",
            "ref_images.ref_image_0", end_seconds=5.0,
            clip_prompt=(
                "Use <Picture 1> as the authoritative identity reference. "
                "Use <Picture 1> as the authoritative whole-design face identity anchor."
            ),
        )
        support = MediaAsset(
            "2", "LoadImage", "image", "pose.png", "<Picture 2>",
            "ref_images.ref_image_1", end_seconds=5.0,
            clip_prompt=(
                "The authoritative recurring face identity is the user-supplied <Picture 1>. "
                "SUPPORTING ENVIRONMENT OR ACTION-STATE REFERENCE ONLY."
            ),
        )
        prompt = build_ref2va_prompt(
            spec, [face, support], 5.0, self.profiles[DEFAULT_SKILL]
        )
        self.assertIn("come exclusively from <Picture 1>", prompt)
        self.assertNotIn("come exclusively from <Picture 2>", prompt)
        self.assertIn(
            "<Picture 2> may provide environment, prop, body-pose or composition guidance",
            prompt,
        )
        picture_2_retention = next(
            line for line in prompt.splitlines()
            if line.startswith("<Picture 2> (active from")
        )
        self.assertIn("does not redefine", picture_2_retention)
        self.assertNotIn("authoritative recurring face-identity source", picture_2_retention)

    def test_repeated_timeline_uses_share_one_h3_tag_and_keep_both_ranges(self):
        spec = PromptSpec(brief="A subject returns later in the story.")
        first = MediaAsset(
            "1", "LoadImage", "image", "subject.png", "<Picture 1>",
            "ref_images.ref_image_0", timeline_placed=True,
            start_seconds=1.0, end_seconds=10.0,
        )
        second = MediaAsset(
            "1", "LoadImage", "image", "subject.png", "<Picture 1>",
            "ref_images.ref_image_0", timeline_placed=True,
            start_seconds=25.0, end_seconds=30.0,
            clip_prompt="Return from a new camera angle.",
            clip_id="clip-repeat", source_node_id="1",
        )
        prompt = build_ref2va_prompt(
            spec, [first, second], 30.0, self.profiles[DEFAULT_SKILL]
        )
        self.assertEqual(prompt.count("is a reference image"), 1)
        self.assertIn("1.00s to 10.00s, 25.00s to 30.00s", prompt)
        self.assertIn("Return from a new camera angle", prompt)
        self.assertNotIn("<Picture 2>", prompt)

    def test_compiler_remaps_stable_ids_and_keeps_source_owned_enrichment(self):
        source_p4 = MediaAsset(
            "4", "LoadImage", "image", "woman.png", "<Picture 4>",
            "ref_images.ref_image_3", timeline_placed=True,
            start_seconds=25.0, end_seconds=30.0,
            recognition="BLIP visual caption: a woman escaping a car",
            clip_prompt="Use @P4 for identity and @P7 only for the salon location.",
        )
        source_p7 = MediaAsset(
            "7", "LoadImage", "image", "salon.png", "<Picture 7>",
            "ref_images.ref_image_6", timeline_placed=True,
            start_seconds=25.0, end_seconds=30.0,
        )
        source_p4.semantic_enrichment = "IDENTITY: preserve the escaping woman."
        source_p4.semantic_enrichment_source_hash = enrichment_fingerprint(
            media_id="P4",
            media_type="image",
            filename="woman.png",
            recognition=source_p4.recognition,
            clip_prompt=source_p4.clip_prompt,
            duration_seconds=0.0,
            timeline_start_seconds=25.0,
            timeline_end_seconds=30.0,
        )
        effective_p4 = deepcopy(source_p4)
        effective_p7 = deepcopy(source_p7)
        effective_p4.tag = "<Picture 1>"
        effective_p7.tag = "<Picture 2>"
        spec = PromptSpec(
            brief="@P4 escapes toward the location in legacy <Picture 7>.",
            shots=["Show @P4 opening the car door before reaching @P7."],
        )
        prompt = build_ref2va_prompt(
            spec,
            [effective_p4, effective_p7],
            5.0,
            self.profiles[DEFAULT_SKILL],
            source_assets=[source_p4, source_p7],
        )
        self.assertIn("<Picture 1> escapes toward the location in legacy <Picture 2>", prompt)
        self.assertIn("Show <Picture 1> opening the car door before reaching <Picture 2>", prompt)
        self.assertIn("AI semantic enrichment", prompt)
        self.assertIn("Director clip instruction: Use <Picture 1>", prompt)

    def test_structured_shot_ranges_drive_exact_detailed_description_timing(self):
        spec = PromptSpec(
            brief="A hero turns toward camera.",
            shots=["fallback shot"],
            shot_ranges=[
                {
                    "cue_id": "S1",
                    "track_id": "V1",
                    "start_seconds": 0.0,
                    "end_seconds": 3.5,
                    "description": (
                        "Hero Reveal. Medium-wide framing. Low angle camera angle. "
                        "Camera movement: Push in, slow speed, small amplitude. "
                        "Subject action: Subject turns toward camera"
                    ),
                },
                {
                    "cue_id": "S2",
                    "track_id": "V1",
                    "start_seconds": 3.5,
                    "end_seconds": 7.0,
                    "description": "Reaction Close-up. Static camera",
                },
            ],
        )
        prompt = build_ref2va_prompt(spec, [], 7.0, self.profiles[DEFAULT_SKILL])
        self.assertIn("[Shot 1 | 00:00.000-00:03.500]", prompt)
        self.assertIn("[Shot 2 | 00:03.500-00:07.000]", prompt)
        self.assertIn("Camera movement: Push in", prompt)
        self.assertNotIn("fallback shot", prompt)

    def test_structured_transitions_emit_only_at_their_own_boundary(self):
        spec = PromptSpec(
            brief="A continuous pursuit.",
            transition="Global transition one; global transition two",
            shot_ranges=[
                {"cue_id": "S1", "start_seconds": 0.0, "end_seconds": 3.0, "description": "First move"},
                {"cue_id": "S2", "start_seconds": 3.0, "end_seconds": 7.0, "description": "Second move"},
                {"cue_id": "S3", "start_seconds": 7.0, "end_seconds": 10.0, "description": "Final move"},
            ],
            transition_ranges=[
                {
                    "from_shot_id": "S1",
                    "to_shot_id": "S2",
                    "start_seconds": 3.0,
                    "description": "Whip pan through the falling leaves",
                },
                {
                    "from_shot_id": "S2",
                    "to_shot_id": "S3",
                    "start_seconds": 7.0,
                    "preset": "Spark match cut",
                    "detail": "match the sword flash to the next angle",
                },
            ],
        )
        prompt = build_ref2va_prompt(spec, [], 10.0, self.profiles[DEFAULT_SKILL])
        first_transition = prompt.index("Whip pan through the falling leaves")
        second_shot = prompt.index("[Shot 2 |")
        second_transition = prompt.index("Spark match cut: match the sword flash")
        third_shot = prompt.index("[Shot 3 |")
        self.assertLess(first_transition, second_shot)
        self.assertLess(second_shot, second_transition)
        self.assertLess(second_transition, third_shot)
        self.assertEqual(prompt.count("Whip pan through the falling leaves"), 1)
        self.assertEqual(prompt.count("Spark match cut"), 1)
        self.assertNotIn("Global transition one", prompt)

    def test_global_transition_string_remains_the_legacy_fallback(self):
        spec = PromptSpec(
            brief="Three linked shots.",
            shots=["First", "Second", "Third"],
            transition="Match the outgoing motion",
        )
        prompt = build_ref2va_prompt(spec, [], 9.0, self.profiles[DEFAULT_SKILL])
        self.assertEqual(prompt.count("Match the outgoing motion"), 2)

    def test_timestamp_transition_maps_only_to_the_nearest_boundary(self):
        spec = PromptSpec(
            brief="Three linked shots.",
            shot_ranges=[
                {"cue_id": "S1", "start_seconds": 0.0, "end_seconds": 3.0, "description": "First"},
                {"cue_id": "S2", "start_seconds": 3.0, "end_seconds": 6.0, "description": "Second"},
                {"cue_id": "S3", "start_seconds": 6.0, "end_seconds": 9.0, "description": "Third"},
            ],
            transition_ranges=[
                {"start_seconds": 5.75, "end_seconds": 6.0, "description": "Fast cut on impact"}
            ],
        )
        prompt = build_ref2va_prompt(spec, [], 9.0, self.profiles[DEFAULT_SKILL])
        self.assertGreater(prompt.index("Fast cut on impact"), prompt.index("[Shot 2 |"))
        self.assertLess(prompt.index("Fast cut on impact"), prompt.index("[Shot 3 |"))

    def test_special_profile_injects_product_rules(self):
        system = profile_system_prompt(
            self.profiles[DEFAULT_SKILL], self.profiles[SPECIAL_SKILL]
        )
        self.assertIn("DEFAULT H3 SKILL", system)
        self.assertIn("SPECIAL SCENE SKILL", system)
        self.assertIn("three independent anchor photos", system)
        prompt = build_ref2va_prompt(
            PromptSpec(brief="Show the watch.", shots=["The watch turns"]),
            [],
            5,
            self.profiles[DEFAULT_SKILL],
            self.profiles[SPECIAL_SKILL],
        )
        self.assertIn("product body color", prompt)
        self.assertIn("Around 100 BPM", prompt)

    def test_none_special_uses_only_default(self):
        system = profile_system_prompt(self.profiles[DEFAULT_SKILL], None)
        self.assertIn("SPECIAL SCENE SKILL: None", system)
        self.assertNotIn("three independent anchor photos", system)
        prompt = build_ref2va_prompt(
            PromptSpec(brief="A neutral scene.", shots=["One shot"]),
            [],
            5,
            self.profiles[DEFAULT_SKILL],
            None,
        )
        self.assertNotIn("product body color", prompt)

    def test_soundscape_and_music_presets_reach_the_six_section_prompt(self):
        prompt = build_ref2va_prompt(
            PromptSpec(
                brief="A model crosses a court.",
                shots=["One continuous shot"],
                audio="Soft tropical court ambience and synchronized footsteps.",
                music="A restrained fashion-electronic beat with no vocals.",
            ),
            [],
            6,
            self.profiles[DEFAULT_SKILL],
        )
        self.assertIn("Soft tropical court ambience", prompt)
        self.assertIn("restrained fashion-electronic beat", prompt)

    def test_authored_tts_is_a_dialogue_stem_not_the_finished_soundtrack(self):
        speech = MediaAsset(
            "101", "LoadAudio", "audio", "authored_dialogue.wav", "<Audio 1>",
            "ref_audios.ref_audio_0", end_seconds=5.0,
            recognition="AI DESIGN AUTHORED SPEECH TTS\nUsage: h3_reference",
        )
        prompt = build_ref2va_prompt(
            PromptSpec(
                brief="A woman speaks inside a busy station.",
                shots=["She delivers the exact line to camera"],
                audio="Station ambience, footsteps and luggage handling.",
                music="Restrained suspense pulse.",
            ),
            [speech],
            5.0,
            self.profiles[DEFAULT_SKILL],
        )
        self.assertIn("authored_dialogue_stem", prompt)
        self.assertIn("not a finished full mix", prompt)
        self.assertIn("diegetic ambience", prompt)
        self.assertIn("synchronized Foley/SFX", prompt)
        self.assertIn("ducked non-diegetic music", prompt)

    def test_media_recognition_is_embedded_as_planning_guidance(self):
        asset = MediaAsset(
            "1",
            "LoadVideo",
            "video",
            "reference.mp4",
            "<Video 1>",
            "ref_videos.ref_video_0",
            end_seconds=5,
            recognition=(
                "BLIP video frame · opening 10% @ 0.50s: a runner enters a tunnel\n"
                "Beat estimate: 120.0 BPM · confidence 0.82\n"
                "WHISPER TRANSCRIPT · cuda\n[00:00.00] Run now"
            ),
            clip_prompt="Keep the runner centered and use a low tracking angle",
        )
        prompt = build_ref2va_prompt(
            PromptSpec(brief="Follow the reference.", shots=["Track the runner"]),
            [asset],
            5,
            self.profiles[DEFAULT_SKILL],
        )
        self.assertIn("Analyzed planning guidance", prompt)
        self.assertIn("120.0 BPM", prompt)
        self.assertIn("machine transcript", prompt)
        self.assertIn("Director clip instruction", prompt)
        self.assertIn("low tracking angle", prompt)

    def test_video_soundtrack_audio_ordinal_is_explicit_in_h3_prompt(self):
        video = MediaAsset(
            "20", "LoadVideo", "video", "reference.mp4", "<Video 1>",
            "ref_videos.ref_video_1",
            paired_audio_binding="ref_video_audios.ref_video_audio_1",
            start_seconds=0.0, end_seconds=5.0,
        )
        audio = MediaAsset(
            "30", "LoadAudio", "audio", "music.wav", "<Audio 2>",
            "ref_audios.ref_audio_2", start_seconds=0.0, end_seconds=5.0,
        )
        prompt = build_ref2va_prompt(
            PromptSpec(brief="Use the motion and both active audio signals."),
            [video, audio],
            5.0,
            self.profiles[DEFAULT_SKILL],
        )
        self.assertIn("synchronized soundtrack is enabled as <Audio 1>", prompt)
        self.assertIn("<Audio 1> is the enabled synchronized soundtrack", prompt)
        self.assertIn("<Audio 1>: fully_copy", prompt)
        self.assertIn("<Audio 2>: fully_copy", prompt)

    def test_native_acoustic_reference_does_not_copy_words_or_voice_identity(self):
        video = MediaAsset(
            "20", "LoadVideo", "video", "location.mp4", "<Video 1>",
            "ref_videos.ref_video_0",
            paired_audio_binding="ref_video_audios.ref_video_audio_0",
            start_seconds=0.0, end_seconds=5.0,
        )
        audio = MediaAsset(
            "30", "LoadAudio", "audio", "room-tone.wav", "<Audio 2>",
            "ref_audios.ref_audio_1", start_seconds=0.0, end_seconds=5.0,
        )
        spec = PromptSpec(
            brief="A conversation in the referenced location.",
            native_audio_ranges=[{
                "cue_id": "S1",
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "native_audio_direction": "Generate diegetic location sound.",
                "environment_continuity": "Establish this room from frame one.",
                "audio_reference_intent": (
                    "Active acoustic references: <Video 1>, <Audio 2>. Use active real-world "
                    "Audio or Video reference sound only to infer spatial acoustics."
                ),
            }],
        )
        prompt = build_ref2va_prompt(
            spec, [video, audio], 5.0, self.profiles[DEFAULT_SKILL]
        )
        self.assertIn("reference generation + acoustic reference", prompt)
        self.assertIn("<Audio 1>: acoustic_reference_only", prompt)
        self.assertIn("<Audio 2>: acoustic_reference_only", prompt)
        self.assertIn("Never copy its dialogue or voice identity", prompt)
        self.assertNotIn("<Audio 1>: fully_copy", prompt)
        self.assertNotIn("<Audio 2>: fully_copy", prompt)

    def test_fresh_semantic_enrichment_reaches_h3_prompt_but_stale_does_not(self):
        asset = MediaAsset(
            "1",
            "LoadImage",
            "image",
            "woman.png",
            "<Picture 1>",
            "ref_images.ref_image_0",
            end_seconds=5,
            recognition="BLIP visual caption: a woman beside a window",
            clip_prompt="Use as the subject identity reference.",
        )
        asset.semantic_enrichment = (
            "SUMMARY\nA waist-up identity reference.\n\n"
            "OBSERVED FACTS\n- Long dark hair and soft side lighting.\n\n"
            "UNCERTAIN INFERENCES (NOT OBSERVED FACTS)\n- Exact location is unknown."
        )
        asset.semantic_enrichment_source_hash = enrichment_fingerprint(
            media_id="P1",
            media_type="image",
            filename=asset.filename,
            recognition=asset.recognition,
            clip_prompt=asset.clip_prompt,
        )
        prompt = build_ref2va_prompt(
            PromptSpec(brief="Frame the subject.", shots=["Slow push in"]),
            [asset],
            5,
            self.profiles[DEFAULT_SKILL],
        )
        self.assertIn("AI semantic enrichment", prompt)
        self.assertIn("Long dark hair", prompt)
        self.assertIn("Exact location is unknown", prompt)

        asset.recognition += "\nBLIP visual caption: a newly changed source"
        stale_prompt = build_ref2va_prompt(
            PromptSpec(brief="Frame the subject.", shots=["Slow push in"]),
            [asset],
            5,
            self.profiles[DEFAULT_SKILL],
        )
        self.assertNotIn("AI semantic enrichment", stale_prompt)


if __name__ == "__main__":
    unittest.main()

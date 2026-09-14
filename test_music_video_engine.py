import unittest
from pathlib import Path

from design_engine import normalize_design_plan, render_special_design_requirement_template
from skill_engine import load_skill_profiles
from music_video_engine import (
    MTV_SINGING_SPECIAL_SKILL,
    build_exact_master_audio_command,
    enforce_mtv_scene_keyframes,
    enforce_mtv_singing_plan,
    exact_master_audio_asset,
    mtv_master_audio_duration,
)


def _media(media_id: str, media_type: str, path: str = "") -> dict:
    return {
        "media_id": media_id,
        "reference_id": media_id,
        "media_type": media_type,
        "loaded": True,
        "local_path": path,
        "start_seconds": 0.0,
        "end_seconds": 12.0,
        "source_in_seconds": 0.0,
    }


def _plan() -> dict:
    return {
        "duration_seconds": 12.0,
        "creative_brief": "A singer performs.",
        "overall_soundscape": "Generated singing.",
        "non_diegetic_music": "A similar song.",
        "constraints": "Keep continuity.",
        "shots": [{
            "id": "S1", "start_seconds": 0.0, "end_seconds": 12.0,
            "subject_action": "A performer stands in frame.",
            "additional_direction": "",
        }],
        "text_layers": [{
            "role": "lyrics", "content": "invented lyric", "speaker": "S2",
            "track": "A1", "lip_sync": False, "explicit_user_requested": True,
        }],
        "existing_media_uses": [],
        "media_requests": [{"requirement_id": "invented_face", "media_type": "image"}],
        "design_warnings": [],
    }


class MusicVideoEngineTests(unittest.TestCase):
    def test_mtv_special_skill_is_discoverable_with_editable_template(self):
        profile = load_skill_profiles(Path(__file__).resolve().parent)[
            MTV_SINGING_SPECIAL_SKILL
        ]
        self.assertEqual(profile.display_name, "MTV Singing H3")
        self.assertIn("P5至P9", profile.design_requirement_template)
        self.assertIn("{{MTV_A1_DURATION}}", profile.design_requirement_template)

    def test_mtv_duration_uses_complete_a1_source_not_short_workspace_clip(self):
        a1 = _media("A1", "audio")
        a1.update(
            start_seconds=0.0,
            end_seconds=12.0,
            source_duration_seconds=87.347,
            source_out_seconds=0.0,
        )
        self.assertEqual(mtv_master_audio_duration([a1]), 87.347)

    def test_mtv_template_displays_resolved_a1_duration(self):
        a1 = _media("A1", "audio")
        a1.update(source_duration_seconds=42.75, source_out_seconds=0.0)
        rendered = render_special_design_requirement_template(
            "A1自动时长：{{MTV_A1_DURATION}}。",
            MTV_SINGING_SPECIAL_SKILL,
            [a1],
        )
        self.assertEqual(rendered, "A1自动时长：42.75秒。")

    def test_mtv_contract_maps_roles_and_removes_invented_lyrics(self):
        media = [
            _media("P1", "image"), _media("P2", "image"),
            _media("P3", "image"), _media("P4", "image"),
            _media("A1", "audio"),
        ]
        plan = enforce_mtv_singing_plan(
            _plan(), media, special_skill_key=MTV_SINGING_SPECIAL_SKILL,
            authored_requirement="帮我创作12秒视频，人物参考@P1，歌曲参考@A1",
        )
        uses = {row["media_id"]: row for row in plan["existing_media_uses"]}
        self.assertEqual(set(uses), {"P1", "P2", "P3", "P4", "A1"})
        self.assertEqual(uses["P1"]["requirement_id"], "mtv_p1_lead_singer")
        self.assertEqual(uses["A1"]["requirement_id"], "mtv_a1_exact_master_audio")
        self.assertEqual(plan["text_layers"], [])
        self.assertIn("sole lead singer", plan["shots"][0]["subject_action"])
        self.assertEqual(plan["mtv_audio_policy"]["final_audio_mode"], "replace_h3_with_exact_timeline_master")

    def test_authored_lyrics_are_kept_as_p1_lip_sync_metadata(self):
        plan = _plan()
        plan["text_layers"][0]["content"] = "月光照进来"
        result = enforce_mtv_singing_plan(
            plan, [], special_skill_key=MTV_SINGING_SPECIAL_SKILL,
            authored_requirement="逐字歌词：月光照进来",
        )
        lyric = result["text_layers"][0]
        self.assertEqual(lyric["speaker"], "S1")
        self.assertEqual(lyric["track"], "A6")
        self.assertTrue(lyric["lip_sync"])

    def test_exactly_five_p4_derived_scene_states_are_reserved(self):
        plan = enforce_mtv_scene_keyframes(
            _plan(), [_media("P4", "image")],
            special_skill_key=MTV_SINGING_SPECIAL_SKILL,
        )
        self.assertEqual(len(plan["media_requests"]), 5)
        self.assertEqual(
            [row["preferred_media_id"] for row in plan["media_requests"]],
            ["P5", "P6", "P7", "P8", "P9"],
        )
        self.assertTrue(all(
            row["source_plate_media_id"] == "P4"
            and row["source_plate_mode"] == "source_img2img"
            for row in plan["media_requests"]
        ))

    def test_exact_master_command_drops_h3_audio_and_never_loops_or_stretches(self):
        command = build_exact_master_audio_command(
            "ffmpeg", "h3.mp4", "A1.mp3", "final.mp4",
            source_offset_seconds=2.0, duration_seconds=12.0,
        )
        joined = " ".join(command)
        self.assertIn("-map 0:v:0 -map [master]", joined)
        self.assertNotIn("0:a", joined)
        self.assertNotIn("-stream_loop", joined)
        self.assertNotIn("atempo", joined)
        self.assertIn("atrim=start=2.000000:duration=12.000000", joined)

    def test_exact_master_asset_uses_timeline_source_offset(self):
        asset = _media("A1", "audio", __file__)
        asset.update(start_seconds=3.0, end_seconds=30.0, source_in_seconds=5.0)
        spec = exact_master_audio_asset(
            [asset], special_skill_key=MTV_SINGING_SPECIAL_SKILL,
            timeline_start=10.0, duration=8.0,
        )
        self.assertEqual(spec["source_offset_seconds"], 12.0)
        self.assertEqual(spec["duration_seconds"], 8.0)

    def test_exact_master_asset_rejects_a_timeline_range_beyond_source_audio(self):
        asset = _media("A1", "audio", __file__)
        asset.update(
            start_seconds=0.0, end_seconds=22.0,
            source_in_seconds=0.0, source_duration_seconds=12.6,
        )
        self.assertIsNone(exact_master_audio_asset(
            [asset], special_skill_key=MTV_SINGING_SPECIAL_SKILL,
            timeline_start=0.0, duration=22.0,
        ))

    def test_normalize_pipeline_applies_mtv_roles_before_speech_extension(self):
        payload = {
            "title": "MTV",
            "duration_seconds": 12.0,
            "creative_brief": "P1 sings to A1.",
            "global_visual_style": "Photoreal cinematic performance.",
            "overall_soundscape": "A similar generated song.",
            "non_diegetic_music": "Generated score.",
            "constraints": "Keep continuity.",
            "shots": [{
                "start_seconds": 0.0, "end_seconds": 12.0, "track": "V1",
                "subject_action": "A singer performs.",
            }],
            "text_layers": [{
                "start_seconds": 0.0, "end_seconds": 12.0, "role": "lyrics",
                "content": "A very long invented lyric that would extend the timeline",
                "speaker": "S2", "explicit_user_requested": True,
            }],
            "existing_media_uses": [],
            "media_requests": [],
        }
        media = [
            _media("P1", "image"), _media("P2", "image"),
            _media("P3", "image"), _media("P4", "image"),
            _media("A1", "audio"),
        ]
        result = normalize_design_plan(
            payload, {"image": 9, "video": 3, "audio": 3},
            existing_media=media, repair_media_plan=True,
            authored_requirement=(
                "帮我创作12秒MTV，主角@P1，身边人物@P2和@P3，场景@P4，歌曲@A1"
            ),
            special_skill_key=MTV_SINGING_SPECIAL_SKILL,
        )
        self.assertEqual(result["duration_seconds"], 12.0)
        self.assertFalse(any(
            row.get("role") in {"lyrics", "dialogue", "voice_over"}
            for row in result["text_layers"]
        ))
        self.assertEqual(len(result["media_requests"]), 5)
        self.assertEqual(result["shots"][-1]["end_seconds"], 12.0)

    def test_normalize_pipeline_overrides_old_12s_template_with_a1_duration(self):
        payload = _plan()
        payload.update({
            "title": "Full A1 MTV",
            "global_visual_style": "Photoreal cinematic performance.",
        })
        a1 = _media("A1", "audio")
        a1.update(
            source_duration_seconds=18.347,
            source_out_seconds=0.0,
        )
        media = [
            _media("P1", "image"), _media("P2", "image"),
            _media("P3", "image"), _media("P4", "image"), a1,
        ]
        result = normalize_design_plan(
            payload,
            {"image": 9, "video": 3, "audio": 3},
            existing_media=media,
            repair_media_plan=True,
            authored_requirement="帮我创作12秒MTV，歌曲参考@A1",
            special_skill_key=MTV_SINGING_SPECIAL_SKILL,
        )
        self.assertEqual(result["duration_seconds"], 18.347)
        self.assertEqual(result["shots"][0]["start_seconds"], 0.0)
        self.assertEqual(result["shots"][-1]["end_seconds"], 18.347)
        a1_use = next(
            row for row in result["existing_media_uses"]
            if row.get("media_id") == "A1"
        )
        self.assertEqual(a1_use["end_seconds"], 18.347)


if __name__ == "__main__":
    unittest.main()

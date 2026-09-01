from pathlib import Path
import json
import shutil
import unittest

from project_workspace import (
    QUALITY_PROFILES,
    WORKSPACE_DIRECTORIES,
    design_requirement_project_name,
    ensure_workspace_layout,
    estimate_resources,
    locate_workspace_for_project,
    migrate_legacy_shot_takes,
    next_design_revision,
    normalize_segment_take_states,
    normalize_shot_take_states,
    picture_overview_project_name,
    project_display_name_for_plan,
    refine_provisional_workspace_root,
    rebase_workspace_take_states,
    record_segment_take,
    update_resource_calibration,
    write_shot_manifests,
    workspace_project_path,
)
from runtime_paths import PROJECT_ROOT


class ProjectWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.root = (
            PROJECT_ROOT / ".director_cache" / "project_workspace_tests"
            / self._testMethodName
        )
        if self.root.is_dir():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def test_fixed_layout_and_manifest_are_stable(self):
        manifest = ensure_workspace_layout(
            self.root,
            display_name="Urban Suspense",
            workspace_id="workspace-test-id",
        )
        second = ensure_workspace_layout(self.root, display_name="Urban Suspense")
        self.assertEqual(manifest["workspace_id"], "workspace-test-id")
        self.assertEqual(second["workspace_id"], "workspace-test-id")
        for relative in WORKSPACE_DIRECTORIES:
            self.assertTrue((self.root / relative).is_dir(), relative)
        self.assertEqual(
            workspace_project_path(self.root),
            self.root / "project" / "director_project.h3director.json",
        )

    def test_design_revisions_stay_inside_one_workspace(self):
        ensure_workspace_layout(self.root, display_name="Revision Test")
        first, first_media, first_audio = next_design_revision(self.root)
        first.mkdir(parents=True, exist_ok=True)
        second, second_media, second_audio = next_design_revision(self.root)
        self.assertEqual(first.name, "R0001")
        self.assertEqual(second.name, "R0002")
        self.assertEqual(first.parent, second.parent)
        self.assertEqual(first_media.name, "R0001")
        self.assertEqual(second_media.name, "R0002")
        self.assertEqual(first_audio.name, "R0001")
        self.assertEqual(second_audio.name, "R0002")

    def test_non_ascii_title_uses_descriptive_media_keyword(self):
        plan = {
            "title": "\u4e2d\u6587\u6587\u5316\u8bc4\u8bba",
            "creative_brief": "A cultural commentary.",
            "media_requests": [{
                "subject_keywords": ["female protagonist", "S1"],
            }],
        }
        self.assertEqual(
            project_display_name_for_plan(plan),
            "female_protagonist",
        )

    def test_instructional_title_uses_complete_generated_reference_keywords(self):
        plan = {
            "title": (
                "Create a 12.00-second full-reference video. Treat the current "
                "Timeline and its active media as authoritative."
            ),
            "creative_brief": "A young runner completes a marathon.",
            "media_requests": [{
                "media_type": "image",
                "subject_keywords": [
                    "marathon track", "morning sunlight", "trees",
                ],
            }],
        }
        self.assertEqual(
            project_display_name_for_plan(plan),
            "marathon_track_morning_sunlight_trees",
        )

    def test_first_picture_blip_overview_names_workspace(self):
        recognition = (
            "Type: image\n\n"
            "BLIP VISUAL SUMMARY · CUDA\n"
            "BLIP · Overview: a young girl running with a red flag\n"
        )
        self.assertEqual(
            picture_overview_project_name(recognition),
            "a_young_girl_running_with_a_red_flag",
        )

    def test_requirement_first_story_sentence_names_workspace_without_picture(self):
        requirement = (
            "帮我创作30秒的视频，内容是深夜办公室里的林玥收到异常门锁通知。"
            "她随后前往公寓调查。"
        )
        self.assertEqual(
            design_requirement_project_name(requirement),
            "深夜办公室里的林玥收到异常门锁通知。",
        )

    def test_chinese_generation_command_is_skipped_before_story_sentence(self):
        requirement = (
            "帮我生成45秒视频，加上中文对白，普通话，加入合适场景，"
            "加入合适旁白，总结以下内容如下\n"
            "八月二十三日，David Senra的播客上线了一期新对谈。\n"
            "主角是Sam Altman。"
        )
        self.assertEqual(
            design_requirement_project_name(requirement),
            "八月二十三日，David_Senra的播客上线了一期新对谈。",
        )

    def test_unused_instruction_named_workspace_is_refined_after_design(self):
        provisional = self.root / (
            "Create_a_12.00-second_full-reference_video._Treat_the_current_Timeline"
        )
        ensure_workspace_layout(provisional, display_name=provisional.name)
        calibration = provisional / "project" / "resource_calibration.json"
        calibration.write_text("{}", encoding="utf-8")
        imported = provisional / "media" / "imported" / "P1.png"
        imported.parent.mkdir(parents=True, exist_ok=True)
        imported.write_bytes(b"source")
        refined = refine_provisional_workspace_root(
            provisional,
            self.root,
            "marathon_track_morning_sunlight_trees",
        )
        self.assertEqual(refined.name, "marathon_track_morning_sunlight_trees")
        self.assertFalse(provisional.exists())
        manifest = json.loads(
            (refined / "project_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["display_name"], "marathon_track_morning_sunlight_trees")
        self.assertTrue((refined / "media" / "imported" / "P1.png").is_file())

    def test_workspace_with_materialized_reference_is_never_auto_renamed(self):
        provisional = self.root / "h3_project_create_a_video"
        ensure_workspace_layout(provisional, display_name=provisional.name)
        reference = provisional / "media" / "generated_references" / "R0001" / "P1.png"
        reference.parent.mkdir(parents=True, exist_ok=True)
        reference.write_bytes(b"durable")
        refined = refine_provisional_workspace_root(
            provisional,
            self.root,
            "marathon_track_morning_sunlight_trees",
        )
        self.assertEqual(refined, provisional.resolve())
        self.assertTrue(reference.is_file())

    def test_shot_manifest_points_to_segment_without_copying_movie(self):
        ensure_workspace_layout(self.root, display_name="Shot Manifest")
        segment_movie = self.root / "segments" / "segment_001" / "takes" / "motion_preview.mp4"
        segment_movie.parent.mkdir(parents=True, exist_ok=True)
        segment_movie.write_bytes(b"one canonical movie")
        state = {
            "S1": {
                "shot_id": "S1",
                "status": "preview",
                "render_profile": "motion_preview",
                "take_count": 1,
                "latest_take": "T0001",
                "latest_output_relative_path": "segments/segment_001/takes/motion_preview.mp4",
                "preview_segment_refs": [{
                    "segment_id": "segment_001",
                    "output_path": str(segment_movie),
                    "output_relative_path": "segments/segment_001/takes/motion_preview.mp4",
                    "timeline_start_seconds": 0.0,
                    "timeline_end_seconds": 4.0,
                    "source_in_seconds": 0.0,
                    "source_out_seconds": 4.0,
                }],
            },
        }
        written = write_shot_manifests(self.root, state, {"S1": (0.0, 4.0)})
        self.assertEqual(written, [self.root / "shots" / "S1" / "shot_manifest.json"])
        payload = json.loads(written[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["timeline_end_seconds"], 4.0)
        self.assertEqual(
            payload["preview_segment_refs"][0]["output_relative_path"],
            "segments/segment_001/takes/motion_preview.mp4",
        )
        self.assertEqual(list((self.root / "shots").rglob("*.mp4")), [])

    def test_legacy_project_adopts_parent_without_rewriting_source(self):
        legacy_root = self.root / "legacy"
        legacy_root.mkdir(parents=True, exist_ok=True)
        project = legacy_root / "old.h3director.json"
        source_text = json.dumps({"format": "h3-director-project", "version": 18})
        project.write_text(source_text, encoding="utf-8")
        resolved = locate_workspace_for_project(project, {})
        ensure_workspace_layout(
            resolved,
            display_name="Legacy",
            legacy_project_path=project,
        )
        self.assertEqual(resolved, legacy_root.resolve())
        self.assertEqual(project.read_text(encoding="utf-8"), source_text)
        self.assertNotEqual(workspace_project_path(resolved), project)

    def test_copied_project_ignores_obsolete_absolute_workspace(self):
        copied_root = self.root / "copied_workspace"
        project = copied_root / "project" / "director_project.h3director.json"
        project.parent.mkdir(parents=True)
        project.write_text("{}", encoding="utf-8")
        stale = self.root / "old_machine_workspace"
        ensure_workspace_layout(stale, workspace_id="stale-id")
        resolved = locate_workspace_for_project(
            project,
            {"workspace_root": str(stale), "workspace_id": "stale-id"},
        )
        self.assertEqual(resolved, copied_root.resolve())

    def test_quality_profiles_and_resource_calibration(self):
        ensure_workspace_layout(self.root, display_name="Budget")
        self.assertFalse(QUALITY_PROFILES["storyboard"].requires_h3)
        self.assertEqual(QUALITY_PROFILES["motion_preview"].megapixels, 0.2)
        self.assertTrue(QUALITY_PROFILES["approved_final"].requires_accepted_seed)
        initial = estimate_resources(
            self.root,
            profile="motion_preview",
            total_duration_seconds=120,
            reusable_duration_seconds=45,
            shot_count=18,
            segment_count=12,
            reserve_disk_gb=0,
        )
        self.assertEqual(initial.render_duration_seconds, 75)
        self.assertFalse(initial.calibrated)
        update_resource_calibration(
            self.root,
            "motion_preview",
            output_duration_seconds=10,
            wall_seconds=100,
            output_bytes=50_000_000,
        )
        calibrated = estimate_resources(
            self.root,
            profile="motion_preview",
            total_duration_seconds=120,
            reusable_duration_seconds=45,
            shot_count=18,
            segment_count=12,
            reserve_disk_gb=0,
        )
        self.assertTrue(calibrated.calibrated)
        self.assertAlmostEqual(calibrated.gpu_seconds, 750)

    def test_shot_state_migration_preserves_approved_take(self):
        states = normalize_shot_take_states(
            {
                "SHOT 1": {
                    "status": "approved",
                    "take_count": 3,
                    "approved_take": "T0002",
                    "approved_output_path": "approved.mp4",
                }
            },
            ["SHOT 1", "SHOT 2"],
        )
        self.assertEqual(states["SHOT 1"]["approved_take"], "T0002")
        self.assertEqual(states["SHOT 1"]["take_count"], 3)
        self.assertEqual(states["SHOT 2"]["status"], "unrendered")

    def test_segment_store_keeps_one_preview_and_one_final_for_shared_shots(self):
        ensure_workspace_layout(self.root, display_name="Compact Segments")
        source_preview = self.root / "source_preview.mp4"
        source_final = self.root / "source_final.mp4"
        source_preview.write_bytes(b"preview-segment")
        source_final.write_bytes(b"approved-segment")
        row = {
            "segment_id": "segment_001_000000000_000015000",
            "start_seconds": 0.0,
            "end_seconds": 15.0,
            "core_start_seconds": 0.0,
            "core_end_seconds": 15.0,
            "shot_ids": ["S1", "S2", "S3"],
        }
        shots = normalize_shot_take_states({}, ["S1", "S2", "S3"])
        ranges = {"S1": (0.0, 5.0), "S2": (5.0, 10.0), "S3": (10.0, 15.0)}
        segments = {}
        preview = record_segment_take(
            self.root,
            segment=row,
            source=source_preview,
            request_kind="preview",
            seed=11,
            segment_states=segments,
            shot_states=shots,
            shot_ranges=ranges,
        )
        final = record_segment_take(
            self.root,
            segment=row,
            source=source_final,
            request_kind="accepted",
            seed=11,
            segment_states=segments,
            shot_states=shots,
            shot_ranges=ranges,
        )
        self.assertEqual(preview.name, "motion_preview.mp4")
        self.assertEqual(final.name, "approved_final.mp4")
        self.assertEqual(
            len(list((self.root / "segments").rglob("*.mp4"))), 2
        )
        self.assertEqual(len(list((self.root / "shots").rglob("*.mp4"))), 0)
        for shot_id in ("S1", "S2", "S3"):
            self.assertEqual(
                shots[shot_id]["approved_segment_refs"][0]["segment_id"],
                row["segment_id"],
            )
        self.assertEqual(
            shots["S2"]["approved_segment_refs"][0]["source_in_seconds"], 5.0
        )

    def test_segment_take_overwrites_stable_profile_without_growing_history(self):
        ensure_workspace_layout(self.root, display_name="Stable Take")
        source = self.root / "source.mp4"
        source.write_bytes(b"first")
        row = {
            "segment_id": "segment_001_000000000_000005000",
            "start_seconds": 0.0,
            "end_seconds": 5.0,
            "shot_ids": ["S1"],
        }
        shots = normalize_shot_take_states({}, ["S1"])
        segments = {}
        first = record_segment_take(
            self.root, segment=row, source=source, request_kind="preview", seed=1,
            segment_states=segments, shot_states=shots,
            shot_ranges={"S1": (0.0, 5.0)},
        )
        source.write_bytes(b"second")
        second = record_segment_take(
            self.root, segment=row, source=source, request_kind="preview", seed=2,
            segment_states=segments, shot_states=shots,
            shot_ranges={"S1": (0.0, 5.0)},
        )
        self.assertEqual(first, second)
        self.assertEqual(second.read_bytes(), b"second")
        self.assertEqual(len(list((self.root / "segments").rglob("*.mp4"))), 1)
        self.assertEqual(segments[row["segment_id"]]["take_count"], 2)

    def test_copied_segment_state_rebases_to_new_workspace(self):
        ensure_workspace_layout(self.root, display_name="Portable Segment")
        take = (
            self.root / "segments" / "seg-1" / "takes" / "approved_final.mp4"
        )
        take.parent.mkdir(parents=True)
        take.write_bytes(b"portable")
        stale = Path("D:/old-pc/project/segments/seg-1/takes/approved_final.mp4")
        segments, shots = rebase_workspace_take_states(
            self.root,
            {
                "seg-1": {
                    "segment_id": "seg-1",
                    "approved_output_path": str(stale),
                    "approved_output_relative_path": "segments/seg-1/takes/approved_final.mp4",
                }
            },
            {
                "S1": {
                    "approved_segment_refs": [{
                        "segment_id": "seg-1",
                        "output_path": str(stale),
                        "output_relative_path": "segments/seg-1/takes/approved_final.mp4",
                    }]
                }
            },
        )
        self.assertEqual(Path(segments["seg-1"]["approved_output_path"]), take)
        self.assertEqual(
            Path(shots["S1"]["approved_segment_refs"][0]["output_path"]), take
        )

    def test_v1_shot_aliases_migrate_only_after_hash_verification(self):
        ensure_workspace_layout(self.root, display_name="Legacy Compact")
        cache = self.root / "legacy_segment.mp4"
        cache.write_bytes(b"one-segment-for-three-shots")
        for shot_id in ("S1", "S2", "S3"):
            takes = self.root / "shots" / shot_id / "takes"
            takes.mkdir(parents=True)
            shutil.copy2(cache, takes / "T0001_approved_final.mp4")
            shutil.copy2(cache, self.root / "shots" / shot_id / "approved.mp4")
        manifest = {
            "render_policy_version": 12,
            "segments": [{
                "segment_id": "segment_001_000000000_000015000",
                "start_seconds": 0.0,
                "end_seconds": 15.0,
                "shot_ids": ["S1", "S2", "S3"],
                "output_path": str(cache),
            }],
        }
        segments, shots, report = migrate_legacy_shot_takes(
            self.root,
            manifests={"production": manifest},
            shot_states=normalize_shot_take_states({}, ["S1", "S2", "S3"]),
            shot_ranges={"S1": (0, 5), "S2": (5, 10), "S3": (10, 15)},
        )
        self.assertEqual(report["migrated_segments"], 1)
        self.assertEqual(report["removed_legacy_files"], 6)
        self.assertEqual(len(list((self.root / "shots").rglob("*.mp4"))), 0)
        canonical = Path(manifest["segments"][0]["output_path"])
        self.assertTrue(canonical.is_file())
        self.assertEqual(canonical.read_bytes(), cache.read_bytes())
        self.assertIn("segment_001_000000000_000015000", segments)
        self.assertEqual(shots["S3"]["approved_segment_refs"][0]["source_in_seconds"], 10.0)


if __name__ == "__main__":
    unittest.main()

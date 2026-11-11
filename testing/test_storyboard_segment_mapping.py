"""Focused regressions for structural editing and Project-scoped render jobs."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtWidgets import QApplication

from director_cut_studio import (
    DirectorCue,
    DirectorCutStudio,
    SMART_RENDER_POLICY_VERSION,
)
from project_storage import safe_cleanup_plan
from runtime_paths import PROJECT_ROOT
from workflow_engine import MEDIA_LOADERS, assign_local_media


class StoryboardSegmentMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _root(self, name: str) -> Path:
        root = PROJECT_ROOT / ".director_cache" / name
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def _close(self, window: DirectorCutStudio) -> None:
        window.project_dirty = False
        window.close()

    def _window_with_shot_pictures(
        self, name: str, shot_count: int
    ) -> tuple[DirectorCutStudio, list[Path]]:
        root = self._root(name)
        window = DirectorCutStudio()
        self.addCleanup(self._close, window)
        window.example_work_dir = root
        duration = shot_count * 5.0
        window._set_design_duration(duration)
        window.director_cues = [
            DirectorCue(
                f"S{index + 1}",
                "shot",
                index * 5.0,
                (index + 1) * 5.0,
                f"Beat {index + 1}",
                subject_action=f"Action {index + 1}",
                authored_subject_action=f"Action {index + 1}",
            )
            for index in range(shot_count)
        ]
        pictures = [asset for asset in window.scan.assets if asset.media_type == "image"]
        paths: list[Path] = []
        for index in range(shot_count):
            path = root / f"shot_{index + 1}_p{index + 1}.png"
            Image.new("RGB", (32, 32), (30 + index * 40, 60, 90)).save(path)
            paths.append(path)
            asset = pictures[index]
            assign_local_media(window.scan, asset, path)
            asset.timeline_placed = True
            asset.timeline_track_id = f"V{index % 3 + 1}"
            asset.start_seconds = index * 5.0
            asset.end_seconds = (index + 1) * 5.0
            asset.clip_prompt = f"Use @{asset.reference_id} only for Shot S{index + 1}."
        window.clip_start.setValue(0.0)
        window.clip_end.setValue(duration)
        window.render_dirty_segment_ids.clear()
        return window, paths

    @staticmethod
    def _install_completed_manifest(
        window: DirectorCutStudio, job: dict, root: Path
    ) -> dict:
        rows = []
        for row in job["segments"]:
            cached = {
                key: deepcopy(value)
                for key, value in row.items()
                if key not in {"workflow", "continuity", "download_dir"}
            }
            output = root / "segments" / row["segment_id"] / "takes" / "approved_final.mp4"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(f"approved-{row['segment_id']}".encode("utf-8"))
            cached.update({"status": "complete", "output_path": str(output)})
            rows.append(cached)
        manifest = {
            "format": "h3-smart-render-manifest",
            "render_policy_version": SMART_RENDER_POLICY_VERSION,
            "request_kind": "final",
            "target_duration_seconds": float(job["target_duration_seconds"]),
            "segments": rows,
        }
        window.smart_render_manifest = manifest
        window.smart_render_manifests = {"production": manifest}
        return manifest

    @staticmethod
    def _segment_image_sources(job: dict) -> list[set[str]]:
        upload_sources = {
            row["upload_name"]: Path(row["path"]).name for row in job["media"]
        }
        result: list[set[str]] = []
        for segment in job["segments"]:
            sources: set[str] = set()
            for node in segment["workflow"].values():
                loader = MEDIA_LOADERS.get(str(node.get("class_type", "")))
                if loader is None or loader[0] != "image":
                    continue
                loader_input = loader[1]
                upload_name = str(node.get("inputs", {}).get(loader_input, ""))
                if upload_name in upload_sources:
                    sources.add(upload_sources[upload_name])
            result.append(sources)
        return result

    @staticmethod
    def _active_picture_for_windows(
        window: DirectorCutStudio, windows: list[tuple[float, float]]
    ) -> list[set[str]]:
        result: list[set[str]] = []
        for index, (start, end) in enumerate(windows):
            _workflow, assets, _continuity, _fingerprint = window._compiled_window_job(
                start,
                end,
                megapixels=1.0,
                seed=9000 + index,
                enable_rtx_vsr=False,
                is_final_window=index == len(windows) - 1,
                continuity_mode="none",
            )
            result.append(
                {
                    Path(asset.local_path).name
                    for asset in assets
                    if asset.media_type == "image" and asset.local_path
                }
            )
        return result

    def test_storyboard_reorder_remaps_picture_windows_and_preserves_checkpoints(self):
        window, paths = self._window_with_shot_pictures(
            "storyboard_mapping_release_audit", 3
        )
        initial_path, _ = window._build_smart_render_job(
            request_kind="final", megapixels=1.0, seed=701, enable_rtx_vsr=False
        )
        initial = json.loads(initial_path.read_text(encoding="utf-8"))
        manifest = self._install_completed_manifest(window, initial, window.example_work_dir)

        window._apply_storyboard_entries(
            [
                {"cue_id": "S3", "duration": 5.0, "preset": "Beat 3", "subject_action": "Action 3"},
                {"cue_id": "S1", "duration": 5.0, "preset": "Beat 1", "subject_action": "Action 1"},
                {"cue_id": "S2", "duration": 5.0, "preset": "Beat 2", "subject_action": "Action 2"},
            ],
            15.0,
        )
        self.assertIs(window.smart_render_manifests["production"], manifest)
        placed = {
            Path(asset.local_path).name: (asset.start_seconds, asset.end_seconds)
            for asset in window.scan.timeline_assets()
            if asset.media_type == "image" and asset.timeline_placed
        }
        self.assertEqual(placed[paths[2].name], (0.0, 5.0))
        self.assertEqual(placed[paths[0].name], (5.0, 10.0))
        self.assertEqual(placed[paths[1].name], (10.0, 15.0))
        dirty_after_apply = set(window.render_dirty_segment_ids)
        self.assertTrue(dirty_after_apply)
        window.undo_stack.undo()
        self.assertFalse(window.render_dirty_segment_ids)
        original = {
            Path(asset.local_path).name: (asset.start_seconds, asset.end_seconds)
            for asset in window.scan.timeline_assets()
            if asset.media_type == "image" and asset.timeline_placed
        }
        self.assertEqual(original[paths[0].name], (0.0, 5.0))
        self.assertEqual(original[paths[2].name], (10.0, 15.0))
        window.undo_stack.redo()
        self.assertEqual(window.render_dirty_segment_ids, dirty_after_apply)

        remapped_path, _ = window._build_smart_render_job(
            request_kind="final", megapixels=1.0, seed=701, enable_rtx_vsr=False
        )
        remapped = json.loads(remapped_path.read_text(encoding="utf-8"))
        self.assertEqual(
            self._segment_image_sources(remapped),
            [{paths[2].name, paths[0].name, paths[1].name}],
        )
        self.assertEqual(
            self._active_picture_for_windows(window, [(0, 5), (5, 10), (10, 15)]),
            [{paths[2].name}, {paths[0].name}, {paths[1].name}],
        )
        self.assertTrue(window.render_dirty_segment_ids)
        self.assertTrue(all(row.get("status") != "cached" for row in remapped["segments"]))

    def test_smart_cut_keeps_unchanged_prefix_cached_and_dirties_shifted_mapping(self):
        window, paths = self._window_with_shot_pictures(
            "smart_cut_mapping_release_audit", 9
        )
        initial_path, _ = window._build_smart_render_job(
            request_kind="final", megapixels=1.0, seed=702, enable_rtx_vsr=False
        )
        initial = json.loads(initial_path.read_text(encoding="utf-8"))
        self._install_completed_manifest(window, initial, window.example_work_dir)
        plan = {
            "format": "h3-smart-cut-plan",
            "mode": "balanced",
            "target_duration": 43.0,
            "saved_seconds": 2.0,
            "affected_ranges": [[15.0, 20.0]],
            "decisions": [
                {
                    "shot_id": f"S{index + 1}",
                    "action": "trim" if index == 3 else "keep",
                    "proposed_duration": 3.0 if index == 3 else 5.0,
                }
                for index in range(9)
            ],
        }
        window._apply_smart_cut_plan(plan)
        self.assertEqual(window.scan.duration_seconds, 43.0)
        placed = {
            Path(asset.local_path).name: (asset.start_seconds, asset.end_seconds)
            for asset in window.scan.timeline_assets()
            if asset.media_type == "image" and asset.timeline_placed
        }
        self.assertEqual(placed[paths[0].name], (0.0, 5.0))
        self.assertEqual(placed[paths[1].name], (5.0, 10.0))
        self.assertEqual(placed[paths[2].name], (10.0, 15.0))
        self.assertEqual(placed[paths[3].name], (15.0, 18.0))
        self.assertEqual(placed[paths[4].name], (18.0, 23.0))
        self.assertEqual(placed[paths[8].name], (38.0, 43.0))

        remapped_path, _ = window._build_smart_render_job(
            request_kind="final", megapixels=1.0, seed=702, enable_rtx_vsr=False
        )
        remapped = json.loads(remapped_path.read_text(encoding="utf-8"))
        self.assertEqual(len(remapped["segments"]), 3)
        self.assertEqual(
            self._active_picture_for_windows(
                window,
                [(0, 5), (5, 10), (10, 15), (15, 18), (18, 23), (38, 43)],
            ),
            [
                {paths[0].name},
                {paths[1].name},
                {paths[2].name},
                {paths[3].name},
                {paths[4].name},
                {paths[8].name},
            ],
        )
        self.assertEqual(
            remapped["segments"][0]["status"],
            "cached",
            (sorted(window.render_dirty_segment_ids), remapped["segments"]),
        )
        self.assertTrue(all(row.get("status") != "cached" for row in remapped["segments"][1:]))

    def test_same_seed_two_projects_keep_jobs_manifests_and_recovery_isolated(self):
        windows: list[DirectorCutStudio] = []
        roots: list[Path] = []
        jobs: list[tuple[Path, dict]] = []
        for suffix in ("A", "B"):
            root = self._root(f"project_scoped_render_simulation_{suffix}")
            roots.append(root)
            window = DirectorCutStudio()
            windows.append(window)
            self.addCleanup(self._close, window)
            window.example_work_dir = root
            window._set_design_duration(12.0)
            shared_name = root / "shared.png"
            Image.new(
                "RGB", (24, 24), (220 if suffix == "A" else 20, 40, 80)
            ).save(shared_name)
            picture = next(
                asset for asset in window.scan.assets if asset.media_type == "image"
            )
            assign_local_media(window.scan, picture, shared_name)
            picture.timeline_placed = True
            picture.timeline_track_id = "V1"
            picture.start_seconds = 0.0
            picture.end_seconds = 12.0
            window.clip_start.setValue(0.0)
            window.clip_end.setValue(12.0)
            path, _ = window._build_smart_render_job(
                request_kind="final", megapixels=1.0, seed=8888, enable_rtx_vsr=False
            )
            jobs.append((path, json.loads(path.read_text(encoding="utf-8"))))

        self.assertNotEqual(jobs[0][0], jobs[1][0])
        self.assertNotEqual(
            jobs[0][1]["media"][0]["upload_name"],
            jobs[1][1]["media"][0]["upload_name"],
        )
        for index, (job_path, job) in enumerate(jobs):
            root = roots[index]
            self.assertTrue(job_path.is_relative_to(root / "project" / "render_jobs"))
            self.assertTrue(Path(job["manifest_path"]).is_relative_to(root))
            self.assertTrue(Path(job["master_output"]).is_relative_to(root / "cache"))
            self.assertTrue(
                all(Path(row["download_dir"]).is_relative_to(root / "cache") for row in job["segments"])
            )
            output = Path(job["segments"][0]["download_dir"]) / "segment.mp4"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(f"project-{index}".encode("ascii"))
            manifest = {
                "request_kind": "final",
                "updated_at": f"2026-09-01T12:00:0{index}+00:00",
                "segments": [
                    {
                        "segment_id": job["segments"][0]["segment_id"],
                        "status": "complete",
                        "output_path": str(output),
                    }
                ],
            }
            Path(job["manifest_path"]).write_text(json.dumps(manifest), encoding="utf-8")

        recovered_a = DirectorCutStudio._recover_workspace_render_manifest(roots[0])
        recovered_b = DirectorCutStudio._recover_workspace_render_manifest(roots[1])
        output_a = Path(recovered_a["segments"][0]["output_path"])
        output_b = Path(recovered_b["segments"][0]["output_path"])
        self.assertTrue(output_a.is_relative_to(roots[0]))
        self.assertTrue(output_b.is_relative_to(roots[1]))
        self.assertNotEqual(output_a.read_bytes(), output_b.read_bytes())
        for root, output in zip(roots, (output_a, output_b)):
            cleanup_paths = {row["path"] for row in safe_cleanup_plan(root)["candidates"]}
            self.assertNotIn(output.relative_to(root).as_posix(), cleanup_paths)


if __name__ == "__main__":
    unittest.main(verbosity=2)

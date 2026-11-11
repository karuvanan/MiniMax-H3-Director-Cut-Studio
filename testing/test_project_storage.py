import json
import os
from pathlib import Path
import shutil
import unittest
import zipfile

from project_storage import (
    archive_workspace,
    build_storage_report,
    safe_cleanup_plan,
    safe_cleanup_workspace,
)
from director_cut_studio import resolve_project_media_path


PROJECT_ROOT = Path(__file__).resolve().parent
CACHE_ROOT = PROJECT_ROOT / ".director_cache"


class ProjectStorageTests(unittest.TestCase):
    def _test_root(self, name: str) -> Path:
        root = CACHE_ROOT / name
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def _workspace(self, root: Path) -> Path:
        workspace = root / "project_alpha"
        (workspace / "project").mkdir(parents=True)
        (workspace / "segments" / "SEG1" / "takes").mkdir(parents=True)
        (workspace / "media" / "imported").mkdir(parents=True)
        (workspace / "cache").mkdir(parents=True)
        (workspace / "proxies").mkdir(parents=True)
        (workspace / "renders" / "final").mkdir(parents=True)
        (workspace / "shots" / "S1" / "takes").mkdir(parents=True)
        (workspace / "logs").mkdir(parents=True)
        (workspace / "project" / "director_project.h3director.json").write_text(
            json.dumps(
                {
                    "format": "h3-director-project",
                    "workflow_path": "workflow.json",
                    "assets": {},
                }
            ),
            encoding="utf-8",
        )
        return workspace

    def test_storage_report_counts_hardlinks_without_double_physical_bytes(self):
        workspace = self._workspace(self._test_root("project_storage_report_test"))
        source = workspace / "media" / "imported" / "P1.png"
        source.write_bytes(b"picture" * 100)
        linked = workspace / "media" / "imported" / "P1_alias.png"
        try:
            os.link(source, linked)
        except OSError:
            self.skipTest("Hard links are unavailable on this filesystem")
        report = build_storage_report(workspace)
        self.assertGreater(report["logical_bytes"], report["physical_bytes"])
        self.assertEqual(report["hardlink_saved_bytes"], source.stat().st_size)
        self.assertEqual(report["categories"]["media"]["files"], 2)

    def test_safe_cleanup_dry_run_and_apply_never_delete_masters_or_segment_takes(self):
        workspace = self._workspace(self._test_root("project_storage_cleanup_test"))
        master = workspace / "generated_output.mp4"
        master.write_bytes(b"durable-master")
        take = workspace / "segments" / "SEG1" / "takes" / "approved_final.mp4"
        take.write_bytes(b"durable-segment")
        duplicate = workspace / "renders" / "final" / "old_master.mp4"
        duplicate.write_bytes(master.read_bytes())
        legacy_take = workspace / "shots" / "S1" / "takes" / "old.mp4"
        legacy_take.write_bytes(take.read_bytes())
        cache = workspace / "cache" / "old.bin"
        cache.write_bytes(b"cache")
        partial = workspace / "proxies" / "monitor.building.mp4"
        partial.write_bytes(b"partial")

        plan = safe_cleanup_plan(workspace)
        paths = {row["path"] for row in plan["candidates"]}
        self.assertIn("cache/old.bin", paths)
        self.assertIn("proxies/monitor.building.mp4", paths)
        self.assertIn("renders/final/old_master.mp4", paths)
        self.assertIn("shots/S1/takes/old.mp4", paths)
        self.assertNotIn("generated_output.mp4", paths)
        self.assertNotIn("segments/SEG1/takes/approved_final.mp4", paths)

        result = safe_cleanup_workspace(workspace, dry_run=False)
        self.assertEqual(result["removed_count"], 4)
        self.assertTrue(master.is_file())
        self.assertTrue(take.is_file())
        self.assertFalse(duplicate.exists())
        self.assertFalse(legacy_take.exists())

    def test_archive_is_verified_portable_and_excludes_disposable_cache(self):
        base = self._test_root("project_storage_archive_test")
        workspace = self._workspace(base)
        external_media = base / "outside_reference.png"
        external_media.write_bytes(b"external-picture")
        external_workflow = base / "outside_workflow.json"
        external_workflow.write_text("{}", encoding="utf-8")
        project = workspace / "project" / "director_project.h3director.json"
        payload = json.loads(project.read_text(encoding="utf-8"))
        payload["workflow_path"] = str(external_workflow)
        payload["assets"] = {
            "137": {
                "filename": external_media.name,
                "local_path": str(external_media),
            }
        }
        project.write_text(json.dumps(payload), encoding="utf-8")
        (workspace / "generated_output.mp4").write_bytes(b"master")
        (workspace / "cache" / "throwaway.bin").write_bytes(b"cache")
        (workspace / "proxies" / "throwaway.mp4").write_bytes(b"proxy")
        (workspace / "logs" / "private.log").write_text("log", encoding="utf-8")

        destination = base / "portable.h3project.zip"
        result = archive_workspace(workspace, destination)
        self.assertTrue(result["verified"])
        self.assertEqual(result["external_source_count"], 2)
        with zipfile.ZipFile(destination, "r") as archive:
            names = set(archive.namelist())
            self.assertIn("project/director_project.h3director.json", names)
            self.assertIn("generated_output.mp4", names)
            self.assertNotIn("cache/throwaway.bin", names)
            self.assertNotIn("proxies/throwaway.mp4", names)
            self.assertNotIn("logs/private.log", names)
            manifest = json.loads(archive.read("archive_manifest.json"))
            self.assertEqual(len(manifest["external_sources"]), 2)
            for row in manifest["external_sources"]:
                self.assertIn(row["archive_path"], names)
            extracted = base / "moved_computer" / "project_alpha"
            archive.extractall(extracted)
        external_media.unlink()
        moved_project = extracted / "project" / "director_project.h3director.json"
        moved_payload = json.loads(moved_project.read_text(encoding="utf-8"))
        resolved_media = resolve_project_media_path(
            moved_project,
            moved_payload["assets"]["137"],
            Path("D:/unavailable/source/computer"),
        )
        self.assertIsNotNone(resolved_media)
        self.assertEqual(resolved_media.name, external_media.name)
        self.assertTrue(resolved_media.is_relative_to(extracted / "media"))

    def test_interrupted_render_cache_is_protected_and_blocks_archive(self):
        workspace = self._workspace(self._test_root("project_storage_recovery_test"))
        render_dir = workspace / "cache" / "generated_outputs" / "final" / "run1"
        render_dir.mkdir(parents=True)
        resumable = render_dir / "SEG1" / "segment.mp4"
        resumable.parent.mkdir(parents=True)
        resumable.write_bytes(b"recoverable-segment")
        abandoned = workspace / "cache" / "old.bin"
        abandoned.write_bytes(b"abandoned")
        render_jobs = workspace / "project" / "render_jobs"
        render_jobs.mkdir(parents=True)
        manifest_path = render_jobs / "final_run1.manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "segments": [
                        {
                            "segment_id": "SEG1",
                            "status": "complete",
                            "download_dir": str(resumable.parent),
                            "output_path": str(resumable),
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        job_path = render_jobs / "final_run1.job.json"
        job_path.write_text(
            json.dumps(
                {
                    "manifest_path": str(manifest_path),
                    "segments": [{"download_dir": str(resumable.parent)}],
                }
            ),
            encoding="utf-8",
        )

        plan = safe_cleanup_plan(workspace)
        paths = {row["path"] for row in plan["candidates"]}
        self.assertNotIn("cache/generated_outputs/final/run1/SEG1/segment.mp4", paths)
        self.assertIn("cache/old.bin", paths)
        with self.assertRaisesRegex(RuntimeError, "interrupted render job"):
            archive_workspace(workspace, workspace.parent / "blocked.zip")


if __name__ == "__main__":
    unittest.main()

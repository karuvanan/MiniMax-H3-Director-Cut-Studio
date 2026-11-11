import json
import os
from pathlib import Path
import shutil
import subprocess
import tracemalloc
import unittest

from media_engine import probe_media
from project_storage import archive_workspace, build_storage_report
from project_workspace import normalize_segment_take_states, normalize_shot_take_states
from runtime_paths import PROJECT_ROOT, load_runtime_paths
from segment_engine import RenderSegment, content_fingerprint, plan_shot_render_segments
from smart_render_worker import assemble_master


class LongProductionReliabilityTests(unittest.TestCase):
    def test_120_second_selective_assembly_storage_and_archive_acceptance(self):
        runtime = load_runtime_paths()
        root = PROJECT_ROOT / ".director_cache" / "long_120_second_acceptance_test"
        shutil.rmtree(root, ignore_errors=True)
        workspace = root / "workspace"
        (workspace / "project").mkdir(parents=True)
        (workspace / "cache").mkdir(parents=True)
        source = root / "source_15s.mp4"
        command = [
            str(runtime.ffmpeg), "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=160x90:r=24:d=15",
            "-f", "lavfi", "-i", "anullsrc=r=32000:cl=stereo",
            "-shortest", "-t", "15", "-c:v", "libx264", "-preset", "ultrafast",
            "-crf", "35", "-pix_fmt", "yuv420p", "-c:a", "aac", str(source),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
        self.assertEqual(completed.returncode, 0, completed.stderr[-1000:])

        segments: list[dict] = []
        outer_hashes: dict[int, str] = {}

        def publish_segment(index: int) -> None:
            segment_id = f"SEG{index + 1:02d}"
            destination = workspace / "segments" / segment_id / "takes" / "approved_final.mp4"
            destination.parent.mkdir(parents=True)
            try:
                os.link(source, destination)
            except OSError:
                shutil.copy2(source, destination)
            start, end = index * 15.0, (index + 1) * 15.0
            row = RenderSegment(
                segment_id=segment_id,
                index=index,
                start_seconds=start,
                end_seconds=end,
                core_start_seconds=start,
                core_end_seconds=end,
                shot_ids=[f"S{index + 1:02d}"],
                status="complete",
                output_path=str(destination),
            ).to_dict()
            segments.append(row)
            if index != 3:
                outer_hashes[index] = content_fingerprint(destination.read_bytes())

        # Start with a previously approved 45-second production, then extend
        # the same fixed Workspace to 120 seconds without touching that prefix.
        for index in range(3):
            publish_segment(index)
        approved_prefix = {
            index: content_fingerprint(Path(segments[index]["output_path"]).read_bytes())
            for index in range(3)
        }
        for index in range(3, 8):
            publish_segment(index)
        self.assertEqual(len(segments), 8)
        for index, digest in approved_prefix.items():
            self.assertEqual(
                content_fingerprint(Path(segments[index]["output_path"]).read_bytes()),
                digest,
            )

        master = workspace / "generated_output.mp4"
        result = assemble_master(
            {
                "ffmpeg": str(runtime.ffmpeg),
                "ffprobe": str(runtime.ffprobe),
                "master_output": str(master),
                "target_duration_seconds": 120.0,
            },
            segments,
        )
        self.assertEqual(result, master.resolve())
        info = probe_media(master, runtime)
        self.assertAlmostEqual(info["duration"], 120.0, delta=0.1)

        # A local middle-Segment replacement must not rewrite any outer Take.
        middle = Path(segments[3]["output_path"])
        replacement = root / "replacement_15s.mp4"
        replace_command = list(command)
        replace_command[replace_command.index("color=c=black:s=160x90:r=24:d=15")] = (
            "color=c=red:s=160x90:r=24:d=15"
        )
        replace_command[-1] = str(replacement)
        replaced = subprocess.run(
            replace_command, capture_output=True, text=True, timeout=120
        )
        self.assertEqual(replaced.returncode, 0, replaced.stderr[-1000:])
        middle.unlink()
        shutil.copy2(replacement, middle)
        for index, digest in outer_hashes.items():
            self.assertEqual(
                content_fingerprint(Path(segments[index]["output_path"]).read_bytes()),
                digest,
            )

        project_payload = {
            "format": "h3-director-project",
            "version": 20,
            "timeline_duration_seconds": 120.0,
            "workflow_path": str(PROJECT_ROOT / "video_minimax_h3_r2v_9image_3audio_3video_api.json"),
            "assets": {},
            "smart_render_manifests": {
                "production": {
                    "request_kind": "final",
                    "target_duration_seconds": 120.0,
                    "master_output": str(master),
                    "segments": segments,
                }
            },
            "generated_output": str(master),
        }
        project = workspace / "project" / "director_project.h3director.json"
        project.write_text(json.dumps(project_payload, indent=2), encoding="utf-8")
        report = build_storage_report(workspace)
        self.assertEqual(report["categories"]["master"]["files"], 1)
        self.assertEqual(report["categories"]["segment_take"]["files"], 8)
        archive = archive_workspace(workspace, root / "acceptance.h3project.zip")
        self.assertTrue(archive["verified"])
        self.assertGreater(archive["file_count"], 9)
        shutil.rmtree(root)

    def test_90_minute_metadata_plan_save_reload_has_complete_bounded_coverage(self):
        """Architecture stress only: no H3/VRAM/network work is invoked."""
        duration = 90.0 * 60.0
        shots = [
            {
                "cue_id": f"S{index + 1:04d}",
                "start_seconds": index * 6.0,
                "end_seconds": (index + 1) * 6.0,
                "continuity_mode": "match_action" if index else "none",
            }
            for index in range(900)
        ]
        tracemalloc.start()
        segments = plan_shot_render_segments(0.0, duration, shots)
        peak_after_plan = tracemalloc.get_traced_memory()[1]
        self.assertEqual(len(segments), 900)
        self.assertEqual(segments[0].core_start_seconds, 0.0)
        self.assertEqual(segments[-1].core_end_seconds, duration)
        self.assertEqual(len({row.segment_id for row in segments}), len(segments))
        for index, row in enumerate(segments):
            self.assertEqual(row.core_start_seconds, index * 6.0)
            self.assertEqual(row.core_end_seconds, (index + 1) * 6.0)
            self.assertEqual(row.shot_ids, [f"S{index + 1:04d}"])
            row.fingerprint = content_fingerprint(
                {
                    "segment_id": row.segment_id,
                    "shot_ids": row.shot_ids,
                    "window": [row.core_start_seconds, row.core_end_seconds],
                }
            )

        shot_states = normalize_shot_take_states({}, [row["cue_id"] for row in shots])
        segment_states = normalize_segment_take_states(
            {
                row.segment_id: {
                    "segment_id": row.segment_id,
                    "status": "unrendered",
                    "start_seconds": row.start_seconds,
                    "end_seconds": row.end_seconds,
                    "core_start_seconds": row.core_start_seconds,
                    "core_end_seconds": row.core_end_seconds,
                    "shot_ids": row.shot_ids,
                }
                for row in segments
            }
        )
        payload = {
            "format": "h3-long-production-architecture-fixture",
            "duration_seconds": duration,
            "shots": shots,
            "segments": [row.to_dict() for row in segments],
            "shot_take_states": shot_states,
            "segment_take_states": segment_states,
        }
        root = PROJECT_ROOT / ".director_cache" / "long_90_minute_architecture_test"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        path = root / "metadata.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        restored = json.loads(path.read_text(encoding="utf-8"))
        peak_after_reload = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()

        self.assertEqual(restored["duration_seconds"], 5400.0)
        self.assertEqual(len(restored["shots"]), 900)
        self.assertEqual(len(restored["segments"]), 900)
        self.assertEqual(len(restored["shot_take_states"]), 900)
        self.assertEqual(len(restored["segment_take_states"]), 900)
        # Metadata planning must remain small enough for the 96GB production
        # host and ordinary lower-memory contributor machines.
        self.assertLess(max(peak_after_plan, peak_after_reload), 64 * 1024 * 1024)
        shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()

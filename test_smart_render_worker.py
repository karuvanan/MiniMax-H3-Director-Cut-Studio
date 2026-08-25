import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from smart_render_worker import (
    _patch_continuity,
    build_render_progress,
    build_assembly_command,
    extract_tail_frames,
    main,
    preflight_smart_render,
)
from runtime_paths import PROJECT_ROOT, load_runtime_paths


class SmartRenderWorkerTests(unittest.TestCase):
    def test_render_progress_uses_authored_shot_duration_weights(self):
        segments = [
            {
                "segment_id": "seg-1", "start_seconds": 0.0, "end_seconds": 3.0,
                "core_start_seconds": 0.0, "core_end_seconds": 3.0,
                "shot_ids": ["S1"],
            },
            {
                "segment_id": "seg-2", "start_seconds": 3.0, "end_seconds": 10.0,
                "core_start_seconds": 3.0, "core_end_seconds": 10.0,
                "shot_ids": ["S2"],
            },
            {
                "segment_id": "seg-3", "start_seconds": 10.0, "end_seconds": 20.0,
                "core_start_seconds": 10.0, "core_end_seconds": 20.0,
                "shot_ids": ["S3"],
            },
        ]
        job = {
            "progress_shots": [
                {"cue_id": "S1", "duration_seconds": 3.0, "segment_ids": ["seg-1"]},
                {"cue_id": "S2", "duration_seconds": 7.0, "segment_ids": ["seg-2"]},
                {"cue_id": "S3", "duration_seconds": 10.0, "segment_ids": ["seg-3"]},
            ]
        }

        first = build_render_progress(job, segments, {0}, stage="complete", current_index=0)
        self.assertEqual(first["weight_source"], "shots")
        self.assertEqual(first["completed_shots"], 1)
        self.assertEqual(first["remaining_shots"], 2)
        self.assertEqual(first["completed_weight_seconds"], 3.0)
        self.assertEqual(first["total_weight_seconds"], 20.0)
        self.assertEqual(first["percent_complete"], 15.0)
        self.assertEqual(first["percent_remaining"], 85.0)

        second = build_render_progress(job, segments, {0, 1}, stage="complete", current_index=1)
        self.assertEqual(second["completed_shots"], 2)
        self.assertEqual(second["percent_complete"], 50.0)
        self.assertEqual(second["current_shot_ids"], ["S2"])

    def test_render_progress_waits_for_last_segment_of_spanning_shot(self):
        segments = [
            {
                "segment_id": "seg-1", "start_seconds": 0.0, "end_seconds": 4.0,
                "shot_ids": ["S1"],
            },
            {
                "segment_id": "seg-2", "start_seconds": 4.0, "end_seconds": 8.0,
                "shot_ids": ["S1"],
            },
            {
                "segment_id": "seg-3", "start_seconds": 8.0, "end_seconds": 10.0,
                "shot_ids": ["S2"],
            },
        ]
        job = {
            "progress_shots": [
                {
                    "cue_id": "S1", "duration_seconds": 8.0,
                    "segment_ids": ["seg-1", "seg-2"],
                },
                {"cue_id": "S2", "duration_seconds": 2.0, "segment_ids": ["seg-3"]},
            ]
        }

        partial = build_render_progress(job, segments, {0}, stage="complete", current_index=0)
        self.assertEqual(partial["completed_shots"], 0)
        self.assertEqual(partial["percent_complete"], 0.0)

        finished_shot = build_render_progress(
            job, segments, {0, 1}, stage="complete", current_index=1
        )
        self.assertEqual(finished_shot["completed_shot_ids"], ["S1"])
        self.assertEqual(finished_shot["completed_shots"], 1)
        self.assertEqual(finished_shot["percent_complete"], 80.0)

    def test_render_progress_falls_back_to_non_overlapping_core_duration(self):
        segments = [
            {
                "segment_id": "seg-1", "start_seconds": 0.0, "end_seconds": 4.0,
                "core_start_seconds": 0.0, "core_end_seconds": 3.0,
                "shot_ids": ["S1"],
            },
            {
                "segment_id": "seg-2", "start_seconds": 2.0, "end_seconds": 11.0,
                "core_start_seconds": 3.0, "core_end_seconds": 10.0,
                "shot_ids": ["S2"],
            },
            {
                "segment_id": "seg-3", "start_seconds": 9.0, "end_seconds": 20.0,
                "core_start_seconds": 10.0, "core_end_seconds": 20.0,
                "shot_ids": ["S3"],
            },
        ]
        progress = build_render_progress({}, segments, {0, 1}, stage="complete")
        self.assertEqual(progress["weight_source"], "segment_core")
        self.assertEqual(progress["completed_weight_seconds"], 10.0)
        self.assertEqual(progress["total_weight_seconds"], 20.0)
        self.assertEqual(progress["percent_complete"], 50.0)
        self.assertEqual(progress["completed_shots"], 2)

    def test_image_continuity_patches_load_image_without_audio_binding(self):
        workflow = {
            "9": {"inputs": {"image": "old.png"}, "class_type": "LoadImage"},
            "136": {
                "inputs": {
                    "prompt": ["138", 0],
                    "ref_images.ref_image_0": ["1", 0],
                    "ref_images.ref_image_4": ["5", 0],
                },
                "class_type": "MiniMaxH3ReferenceToVideo",
            },
        }
        continuity = {
            "kind": "image",
            "loader_node_id": "9",
            "loader_input": "image",
            "h3_node_id": "136",
            "binding": "ref_images.ref_image_1",
            "connection": ["9", 0],
        }
        _patch_continuity(workflow, continuity, "continuity_frame.jpg")
        self.assertEqual(workflow["9"]["inputs"]["image"], "continuity_frame.jpg")
        self.assertEqual(
            workflow["136"]["inputs"]["ref_images.ref_image_1"],
            ["9", 0],
        )
        reference_keys = [
            name for name in workflow["136"]["inputs"]
            if name.startswith("ref_images.ref_image_")
        ]
        self.assertEqual(
            reference_keys,
            [
                "ref_images.ref_image_0",
                "ref_images.ref_image_1",
                "ref_images.ref_image_4",
            ],
        )

    def test_motion_continuity_extracts_exact_silent_24_frame_tail(self):
        runtime = load_runtime_paths()
        source = PROJECT_ROOT / ".director_cache" / "runtime_smoke" / "sample.mp4"
        if not source.is_file():
            self.skipTest("runtime smoke video is not present")
        destination = PROJECT_ROOT / ".director_cache" / "continuity_24_frames.mp4"
        destination.unlink(missing_ok=True)

        extract_tail_frames(
            runtime.ffmpeg,
            runtime.ffprobe,
            source,
            destination,
            frame_count=24,
            fps=24,
        )

        import subprocess
        probe = subprocess.run(
            [
                str(runtime.ffprobe), "-v", "error", "-count_frames",
                "-select_streams", "v:0", "-show_entries",
                "stream=nb_read_frames", "-of",
                "default=noprint_wrappers=1:nokey=1", str(destination),
            ],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(int(probe.stdout.strip()), 24)
        audio = subprocess.run(
            [
                str(runtime.ffprobe), "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=index", "-of", "csv=p=0",
                str(destination),
            ],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(audio.stdout.strip(), "")
        destination.unlink(missing_ok=True)

    def test_preflight_rejects_internal_segment_over_native_limit(self):
        job = {
            "segments": [
                {"start_seconds": 0.0, "end_seconds": 16.0, "workflow": {}},
                {"start_seconds": 15.0, "end_seconds": 20.0, "workflow": {}},
            ]
        }
        with self.assertRaisesRegex(ValueError, "invalid duration"):
            preflight_smart_render(job)

    def test_assembly_trims_each_leading_overlap(self):
        root = Path("assembly-test")
        paths = [root / f"segment{index}.mp4" for index in range(3)]
        rows = [
            {
                "output_path": str(paths[0]), "overlap_before_seconds": 0.0,
                "core_start_seconds": 0.0, "core_end_seconds": 15.0,
            },
            {
                "output_path": str(paths[1]), "overlap_before_seconds": 1.0,
                "core_start_seconds": 15.0, "core_end_seconds": 29.0,
            },
            {
                "output_path": str(paths[2]), "overlap_before_seconds": 1.0,
                "core_start_seconds": 29.0, "core_end_seconds": 43.0,
            },
        ]
        with patch("pathlib.Path.is_file", return_value=True):
            with patch("smart_render_worker._has_audio", return_value=True):
                command = build_assembly_command(
                    Path("ffmpeg"), Path("ffprobe"), rows, root / "master.mp4", 43.0
                )
        filters = command[command.index("-filter_complex") + 1]
        self.assertIn("[0:v]trim=start=0.000000:end=15.000000", filters)
        self.assertIn("[1:v]trim=start=1.000000:end=15.000000", filters)
        self.assertIn("[2:a]atrim=start=1.000000:end=15.000000", filters)
        self.assertIn("concat=n=3:v=1:a=1", filters)
        self.assertIn("43.000000", command)

    def test_worker_emits_running_and_failed_segment_status(self):
        events = []
        root = PROJECT_ROOT / ".director_cache" / "smart_render_status_test"
        root.mkdir(parents=True, exist_ok=True)
        try:
            job_path = root / "job.json"
            job_path.write_text(
                json.dumps(
                    {
                        "server": "http://127.0.0.1:8188",
                        "manifest_path": str(root / "manifest.json"),
                        "media": [],
                        "segments": [
                            {
                                "segment_id": "segment_001_000000000_000015000",
                                "index": 0,
                                "start_seconds": 0.0,
                                "end_seconds": 15.0,
                                "workflow": {},
                                "download_dir": str(root / "segment"),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            preflight = {
                "segment_count": 1,
                "node_class_count": 0,
                "free_disk_gb": 100.0,
            }
            with (
                patch.object(sys, "argv", ["smart_render_worker.py", str(job_path)]),
                patch("smart_render_worker.preflight_smart_render", return_value=preflight),
                patch("smart_render_worker.queue_segment", side_effect=RuntimeError("OOM")),
                patch("smart_render_worker.emit", side_effect=events.append),
            ):
                with self.assertRaisesRegex(RuntimeError, "OOM"):
                    main()
            statuses = [
                event["segment_status"]["status"]
                for event in events
                if "segment_status" in event
            ]
            self.assertEqual(statuses, ["running", "failed"])
            progress_events = [
                event["render_progress"] for event in events if "render_progress" in event
            ]
            self.assertEqual(
                [event["stage"] for event in progress_events],
                ["preflight", "running", "failed"],
            )
            self.assertEqual(progress_events[-1]["percent_complete"], 0.0)
            self.assertEqual(progress_events[-1]["remaining_shots"], 1)
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["segments"][0]["status"], "failed")
        finally:
            (root / "job.json").unlink(missing_ok=True)
            (root / "manifest.json").unlink(missing_ok=True)
            root.rmdir()

    def test_worker_emits_cached_complete_assembling_and_final_progress(self):
        events = []
        root = PROJECT_ROOT / ".director_cache" / "smart_render_progress_test"
        root.mkdir(parents=True, exist_ok=True)
        cached_output = root / "cached.mp4"
        generated_output = root / "generated.mp4"
        master_output = root / "master.mp4"
        cached_output.write_bytes(b"cached")
        generated_output.write_bytes(b"generated")
        job_path = root / "job.json"
        job_path.write_text(
            json.dumps(
                {
                    "server": "http://127.0.0.1:8188",
                    "manifest_path": str(root / "manifest.json"),
                    "master_output": str(master_output),
                    "media": [],
                    "progress_shots": [
                        {
                            "cue_id": "S1", "duration_seconds": 4.0,
                            "segment_ids": ["seg-1"],
                        },
                        {
                            "cue_id": "S2", "duration_seconds": 6.0,
                            "segment_ids": ["seg-2"],
                        },
                    ],
                    "segments": [
                        {
                            "segment_id": "seg-1", "index": 0,
                            "start_seconds": 0.0, "end_seconds": 4.0,
                            "shot_ids": ["S1"], "workflow": {},
                            "status": "cached", "output_path": str(cached_output),
                            "download_dir": str(root / "seg-1"),
                        },
                        {
                            "segment_id": "seg-2", "index": 1,
                            "start_seconds": 4.0, "end_seconds": 10.0,
                            "shot_ids": ["S2"], "workflow": {},
                            "download_dir": str(root / "seg-2"),
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        second_result = {
            "segment_id": "seg-2", "index": 1,
            "start_seconds": 4.0, "end_seconds": 10.0,
            "shot_ids": ["S2"], "status": "complete",
            "output_path": str(generated_output),
        }
        preflight = {"segment_count": 2, "node_class_count": 0, "free_disk_gb": 100.0}
        try:
            with (
                patch.object(sys, "argv", ["smart_render_worker.py", str(job_path)]),
                patch("smart_render_worker.preflight_smart_render", return_value=preflight),
                patch("smart_render_worker.queue_segment", return_value=second_result),
                patch("smart_render_worker.release_comfy_memory", return_value="released"),
                patch("smart_render_worker.assemble_master", return_value=master_output),
                patch("smart_render_worker.emit", side_effect=events.append),
            ):
                self.assertEqual(main(), 0)
            progress_events = [
                event["render_progress"] for event in events if "render_progress" in event
            ]
            self.assertEqual(
                [event["stage"] for event in progress_events],
                ["preflight", "cached", "running", "complete", "assembling", "final"],
            )
            self.assertEqual(progress_events[1]["percent_complete"], 40.0)
            self.assertEqual(progress_events[1]["completed_shots"], 1)
            self.assertEqual(progress_events[2]["percent_complete"], 40.0)
            self.assertEqual(progress_events[3]["percent_complete"], 100.0)
            self.assertEqual(progress_events[-1]["remaining_shots"], 0)
        finally:
            for path in (
                job_path, root / "manifest.json", cached_output,
                generated_output, master_output,
            ):
                path.unlink(missing_ok=True)
            root.rmdir()


if __name__ == "__main__":
    unittest.main()

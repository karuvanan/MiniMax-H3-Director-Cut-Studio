import json
import sys
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from smart_render_worker import (
    _character_swap_composite_bbox,
    _mix_complete_location_reference,
    best_envelope_offset,
    _patch_continuity,
    build_native_ambience_workflow,
    build_render_progress,
    build_assembly_command,
    canvas_for_megapixels,
    assemble_master,
    classify_generation_error,
    extract_tail_frames,
    identity_frame_metrics,
    main,
    patch_complete_location_reference,
    prefer_server_character_swap_lora,
    preflight_smart_render,
    queue_character_swap_passes,
    queue_segment,
    speech_guard_result_score,
    temporal_frame_motion,
)
from runtime_paths import PROJECT_ROOT, load_runtime_paths


class SmartRenderWorkerTests(unittest.TestCase):
    def test_preview_canvas_is_a_real_aspect_preserving_point_two_megapixels(self):
        canvas = canvas_for_megapixels((832, 1184), 0.2)
        self.assertIsNotNone(canvas)
        width, height = canvas
        self.assertLessEqual(width * height, 200_000)
        self.assertEqual(width % 2, 0)
        self.assertEqual(height % 2, 0)
        self.assertAlmostEqual(width / height, 832 / 1184, delta=0.01)

    def test_temporal_motion_detects_articulation_but_accepts_still_mouth(self):
        closed = bytes([80]) * 64
        speaking = bytes([220]) * 64
        self.assertEqual(temporal_frame_motion([closed, closed, closed]), 0.0)
        self.assertGreater(
            temporal_frame_motion([closed, speaking, closed, speaking]), 0.4
        )

    def test_identity_metrics_separate_noop_from_material_replacement(self):
        source = bytes(range(256)) * 36
        unchanged = identity_frame_metrics(source, source)
        changed = identity_frame_metrics(source, bytes(reversed(source)))

        self.assertGreater(unchanged["correlation"], 0.99)
        self.assertGreater(unchanged["similarity"], 0.99)
        self.assertLess(unchanged["mae"], 0.001)
        self.assertLess(changed["correlation"], 0.0)
        self.assertGreater(changed["mae"], 0.2)

    def test_character_swap_prefers_server_v15_and_preserves_turbo_lora(self):
        job = {
            "segments": [{
                "character_swap_passes": [{
                    "workflow": {
                        "4": {
                            "class_type": "LoraLoaderModelOnly",
                            "inputs": {
                                "lora_name": "h3_character_swap_pro4500_1000.safetensors"
                            },
                        },
                        "204": {
                            "class_type": "LoraLoaderModelOnly",
                            "inputs": {"lora_name": "minimax_h3_fl2v_turbo_8step.safetensors"},
                        },
                    }
                }]
            }]
        }
        object_info = {
            "LoraLoaderModelOnly": {
                "input": {"required": {"lora_name": [[
                    "h3-character-swap-v1/h3_character_swap_pro4500_1000.safetensors",
                    "h3-character-swap-v1.5/h3_character_swap_v1.5.safetensors",
                    "minimax_h3_fl2v_turbo_8step.safetensors",
                ]]}}
            }
        }

        selected = prefer_server_character_swap_lora(job, object_info)

        pass_row = job["segments"][0]["character_swap_passes"][0]
        self.assertEqual(
            pass_row["workflow"]["4"]["inputs"]["lora_name"],
            "h3-character-swap-v1.5/h3_character_swap_v1.5.safetensors",
        )
        self.assertEqual(
            pass_row["workflow"]["204"]["inputs"]["lora_name"],
            "minimax_h3_fl2v_turbo_8step.safetensors",
        )
        self.assertEqual(selected, [
            "h3-character-swap-v1.5/h3_character_swap_v1.5.safetensors"
        ])

    def test_character_swap_runs_visible_roles_as_sequential_source_passes(self):
        root = PROJECT_ROOT / ".director_cache" / "character_swap_pass_test"
        shutil.rmtree(root, ignore_errors=True)

    def test_character_swap_composite_bbox_prefers_full_track_samples(self):
        bbox = _character_swap_composite_bbox({
            "composite_bboxes_normalized": [
                [0.10, 0.20, 0.30, 0.80],
                [0.15, 0.18, 0.36, 0.82],
            ],
            "identity_audit": {
                "source_bboxes_normalized": [[0.60, 0.10, 0.90, 0.90]],
            },
        })
        self.assertLess(bbox[0], 0.10)
        self.assertLess(bbox[1], 0.18)
        self.assertGreater(bbox[2], 0.36)
        self.assertGreater(bbox[3], 0.82)
        self.assertLess(bbox[2], 0.45)

    def test_independent_character_swap_passes_use_clean_v1_and_are_composited(self):
        root = PROJECT_ROOT / ".director_cache" / "character_swap_composite_test"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        source = root / "v1.mp4"
        first = root / "pass1.mp4"
        second = root / "pass2.mp4"
        composite = root / "composite.mp4"
        for path, content in (
            (source, b"source"), (first, b"first"), (second, b"second"),
            (composite, b"composite"),
        ):
            path.write_bytes(content)
        workflows = []

        def fake_queue(_job, _segment, workflow, _uploaded, **_kwargs):
            workflows.append(workflow)
            output = first if len(workflows) == 1 else second
            return {"output_path": str(output), "prompt_id": f"p{len(workflows)}"}

        segment = {
            "segment_id": "S1",
            "index": 0,
            "seed": 10,
            "download_dir": str(root),
            "character_swap_passes": [
                {
                    "source_role_id": "R1", "target_media_id": "P1", "seed": 11,
                    "runtime_source": False, "independent_role_composite": True,
                    "identity_audit": {"source_video_path": str(source)},
                    "workflow": {"30": {"class_type": "LoadVideo", "inputs": {"file": "v1.mp4"}}},
                },
                {
                    "source_role_id": "R2", "target_media_id": "P2", "seed": 12,
                    "runtime_source": False, "independent_role_composite": True,
                    "identity_audit": {"source_video_path": str(source)},
                    "workflow": {"30": {"class_type": "LoadVideo", "inputs": {"file": "v1.mp4"}}},
                },
            ],
            "shot_ids": ["S1"],
        }
        with (
            patch("smart_render_worker.queue_segment", side_effect=fake_queue),
            patch(
                "smart_render_worker.composite_independent_character_swap_roles",
                return_value=composite.resolve(),
            ) as composite_roles,
            patch("smart_render_worker.upload_file") as runtime_upload,
            patch("smart_render_worker.emit"),
        ):
            result = queue_character_swap_passes(
                {"server": "http://127.0.0.1:8188", "http_timeout": 1},
                segment,
                [],
            )
        self.assertEqual(len(workflows), 2)
        runtime_upload.assert_not_called()
        composite_roles.assert_called_once()
        self.assertEqual(result["output_path"], str(composite.resolve()))
        self.assertEqual(
            result["character_swap_composite"]["mode"],
            "independent_role_boxes",
        )
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        first = root / "pass1.mp4"
        second = root / "pass2.mp4"
        first.write_bytes(b"first")
        second.write_bytes(b"second")
        workflows = []
        progress_events = []

        def fake_queue(_job, _segment, workflow, _uploaded, **_kwargs):
            workflows.append(workflow)
            output = first if len(workflows) == 1 else second
            return {"output_path": str(output), "prompt_id": f"p{len(workflows)}"}

        segment = {
            "segment_id": "S1",
            "index": 0,
            "seed": 10,
            "download_dir": str(root),
            "character_swap_passes": [
                {
                    "source_role_id": "R1", "target_media_id": "P1", "seed": 11,
                    "relay_window_count": 3,
                    "runtime_source": False,
                    "workflow": {"30": {"class_type": "LoadVideo", "inputs": {"file": "v1.mp4"}}},
                },
                {
                    "source_role_id": "R2", "target_media_id": "P2", "seed": 12,
                    "relay_window_count": 3,
                    "runtime_source": True,
                    "runtime_source_loader_node_id": "30",
                    "runtime_source_loader_input": "file",
                    "workflow": {"30": {"class_type": "LoadVideo", "inputs": {"file": "placeholder.mp4"}}},
                },
            ],
            "shot_ids": ["S3"],
        }
        with (
            patch("smart_render_worker.queue_segment", side_effect=fake_queue),
            patch("smart_render_worker.upload_file", return_value={"name": "runtime-pass1.mp4"}),
            patch("smart_render_worker.emit", side_effect=progress_events.append),
        ):
            result = queue_character_swap_passes(
                {"server": "http://127.0.0.1:8188", "http_timeout": 1},
                segment,
                [],
            )
        self.assertEqual(result["output_path"], str(second.resolve()))
        self.assertEqual(len(workflows), 2)
        self.assertEqual(workflows[1]["30"]["inputs"]["file"], "runtime-pass1.mp4")
        labels = [str(row.get("progress") or "") for row in progress_events]
        self.assertIn("Segment S3 · Role R1 · Pass 1/2 · Window 1/3", labels)
        self.assertIn(
            "Segment S3 · Role R2 · Pass 2/2 · Window 3/3 · complete",
            labels,
        )
        shutil.rmtree(root, ignore_errors=True)

    def test_timing_audit_detects_offset_without_requesting_regeneration(self):
        expected = [0.0] * 20 + [1.0, 3.0, 2.0, 0.0] + [0.0] * 20
        actual = [0.0] * 5 + expected
        offset, correlation = best_envelope_offset(
            expected, actual, bucket_seconds=0.01, maximum_offset_seconds=0.2
        )
        self.assertAlmostEqual(offset, 0.05, places=6)
        self.assertGreater(correlation, 0.99)

    def test_tail_padding_trim_starts_at_zero_and_ends_at_authored_core(self):
        root = PROJECT_ROOT / ".director_cache" / "tail_padding_trim_test"
        root.mkdir(parents=True, exist_ok=True)
        source = root / "segment.mp4"
        source.write_bytes(b"video")
        destination = root / "master.mp4"
        segment = {
            "output_path": str(source),
            "start_seconds": 0.0,
            "end_seconds": 9.42,
            "core_start_seconds": 0.0,
            "core_end_seconds": 8.833333,
            "overlap_before_seconds": 1.0,
            "assembly_trim_strategy": "tail_padding_only",
        }
        with patch("smart_render_worker._has_audio", return_value=False):
            command = build_assembly_command(
                Path("ffmpeg"), Path("ffprobe"), [segment], destination, 8.833333
            )
        filters = command[command.index("-filter_complex") + 1]
        self.assertIn("trim=start=0.000000:end=8.833333", filters)
        source.unlink(missing_ok=True)
        root.rmdir()

    def test_source_remake_assembly_uses_authoritative_a999_audio(self):
        root = PROJECT_ROOT / ".director_cache" / "a999_authoritative_audio_test"
        root.mkdir(parents=True, exist_ok=True)
        source = root / "segment.mp4"
        source.write_bytes(b"video")
        a999 = root / "A999.wav"
        a999.write_bytes(b"audio")
        destination = root / "master.mp4"
        segment = {
            "output_path": str(source),
            "start_seconds": 0.0,
            "end_seconds": 9.42,
            "core_start_seconds": 0.0,
            "core_end_seconds": 8.833333,
            "assembly_trim_strategy": "tail_padding_only",
            "source_audio_timing_audit": {
                "enabled": True,
                "expected_path": str(a999),
                "authored_duration_seconds": 8.833333,
                "padded_duration_seconds": 9.42,
            },
        }
        with patch("smart_render_worker._has_audio", return_value=False):
            command = build_assembly_command(
                Path("ffmpeg"), Path("ffprobe"), [segment], destination, 8.833333
            )
        filters = command[command.index("-filter_complex") + 1]
        self.assertEqual(command.count("-i"), 2)
        self.assertIn(str(a999), command)
        self.assertIn("[1:a]atrim=start=0.000000:end=8.833333", filters)
        self.assertNotIn("[0:a]atrim", filters)
        self.assertNotIn("afade=", filters)
        source.unlink(missing_ok=True)
        a999.unlink(missing_ok=True)
        root.rmdir()

    @staticmethod
    def _location_sound_workflow():
        return {
            "10": {
                "class_type": "MiniMaxH3ReferenceToVideo",
                "inputs": {
                    "prompt": ["11", 0],
                    "ref_images.ref_image_0": ["12", 0],
                    "ref_audios.ref_audio_0": ["13", 0],
                    "ref_video_audios.ref_video_audio_0": ["14", 2],
                },
            },
            "11": {
                "class_type": "Text Multiline",
                "inputs": {
                    "value": (
                        "subject_definitions:\n"
                        "<Picture 1> is the rainy street.\n"
                        "<Audio 1> contains exact dialogue.\n\n"
                        "summary:\nA person speaks in rain.\n\n"
                        "overall_soundscape:\nHeavy rain, wind and puddle splashes.\n"
                        "[Native Audio S1 | 00:00.000-00:03.000] exact dialogue.\n\n"
                        "non_diegetic_music:\nSoft score."
                    )
                },
            },
            "12": {"class_type": "LoadImage", "inputs": {"image": "p1.png"}},
            "13": {"class_type": "LoadAudio", "inputs": {"audio": "dry.wav"}},
            "14": {"class_type": "LoadVideo", "inputs": {"video": "v1.mp4"}},
            "15": {
                "class_type": "Resolution",
                "inputs": {"megapixels": 1.0, "resize_type.scale": 2.0},
            },
            "16": {
                "class_type": "SaveVideo",
                "inputs": {"filename_prefix": "video/original"},
            },
        }

    def test_native_ambience_pass_removes_audio_references_and_forbids_voice(self):
        original = self._location_sound_workflow()
        result = build_native_ambience_workflow(
            original, duration_seconds=3.0, cache_token="abc123"
        )
        h3_inputs = result["10"]["inputs"]
        self.assertIn("ref_images.ref_image_0", h3_inputs)
        self.assertNotIn("ref_audios.ref_audio_0", h3_inputs)
        self.assertNotIn("ref_video_audios.ref_video_audio_0", h3_inputs)
        prompt = result["11"]["inputs"]["value"]
        self.assertIn("HUMAN VOCAL CHANNEL: EMPTY", prompt)
        self.assertIn("Heavy rain, wind and puddle splashes", prompt)
        self.assertNotIn("exact dialogue", prompt)
        self.assertEqual(result["15"]["inputs"]["megapixels"], 0.2)
        self.assertEqual(result["15"]["inputs"]["resize_type.scale"], 1.0)
        self.assertEqual(
            result["16"]["inputs"]["filename_prefix"],
            "video/H3_native_ambience_abc123",
        )
        self.assertEqual(original["13"]["inputs"]["audio"], "dry.wav")

    def test_complete_location_reference_replaces_dry_tts_and_injects_contract(self):
        workflow = self._location_sound_workflow()
        patch_complete_location_reference(
            workflow,
            loader_node_id="13",
            upload_name="complete_location.wav",
        )
        self.assertEqual(workflow["13"]["inputs"]["audio"], "complete_location.wav")
        prompt = workflow["11"]["inputs"]["value"]
        self.assertIn("COMPLETE LOCATION-SOUND REFERENCE CONTRACT", prompt)
        self.assertIn("CINEMATIC DIALOGUE ACOUSTIC INTEGRATION", prompt)

    def test_native_speech_guard_retries_with_fresh_seed_without_hard_block(self):
        root = PROJECT_ROOT / ".director_cache" / "smart_render_speech_guard_test"
        root.mkdir(parents=True, exist_ok=True)
        video = root / "segment.mp4"
        video.write_bytes(b"video")
        job = {
            "server": "http://127.0.0.1:8188",
            "http_timeout": 1,
            "segment_attempts": 3,
            "native_speech_guard_retries": 2,
            "segment_count": 1,
            "history_poll_interval": 0.1,
            "generation_timeout": 10,
        }
        segment = {
            "segment_id": "seg-speech",
            "index": 0,
            "seed": 123,
            "download_dir": str(root),
            "native_speech_guard": {
                "enabled": True,
                "silence_windows": [[4.0, 5.0]],
            },
        }
        workflow = {
            "1": {
                "class_type": "RandomNoise",
                "inputs": {"noise_seed": 123},
            }
        }

        class Guard:
            def __init__(self):
                self.calls = 0

            def inspect(self, _video, _spec):
                self.calls += 1
                return {
                    "passed": self.calls > 1,
                    "violations": (
                        [] if self.calls > 1
                        else [{"transcript": "额外对白"}]
                    ),
                }

        guard = Guard()
        queued_workflows = []

        def queue(request, _timeout):
            payload = json.loads(request.data.decode("utf-8"))
            queued_workflows.append(payload["prompt"])
            return {"prompt_id": f"p{len(queued_workflows)}"}

        with (
            patch("smart_render_worker._request_json", side_effect=queue),
            patch("smart_render_worker.wait_for_history", return_value=({}, {})),
            patch(
                "smart_render_worker.download_outputs",
                return_value=[{"kind": "videos", "local_path": str(video)}],
            ),
            patch("smart_render_worker.time.sleep"),
            patch("smart_render_worker.emit"),
        ):
            result = queue_segment(
                job, segment, workflow, [], speech_guard=guard
            )
        self.assertEqual(guard.calls, 2)
        self.assertEqual(result["attempts_used"], 2)
        self.assertTrue(result["native_speech_guard_result"]["passed"])
        self.assertNotEqual(
            queued_workflows[0]["1"]["inputs"]["noise_seed"],
            queued_workflows[1]["1"]["inputs"]["noise_seed"],
        )
        video.unlink(missing_ok=True)
        root.rmdir()

    def test_native_speech_guard_allows_two_regenerations_then_warns(self):
        root = PROJECT_ROOT / ".director_cache" / "smart_render_speech_guard_budget_test"
        root.mkdir(parents=True, exist_ok=True)
        video = root / "segment.mp4"
        video.write_bytes(b"video")
        job = {
            "server": "http://127.0.0.1:8188",
            "http_timeout": 1,
            "segment_attempts": 3,
            "native_speech_guard_retries": 2,
            "segment_count": 1,
            "history_poll_interval": 0.1,
            "generation_timeout": 10,
        }
        segment = {
            "segment_id": "seg-speech-budget",
            "index": 0,
            "seed": 123,
            "download_dir": str(root),
            "native_speech_guard": {
                "enabled": True,
                "silence_windows": [[4.0, 5.0]],
            },
        }
        workflow = {
            "1": {"class_type": "RandomNoise", "inputs": {"noise_seed": 123}}
        }

        class Guard:
            def __init__(self):
                self.calls = 0

            def inspect(self, _video, _spec):
                self.calls += 1
                return {
                    "passed": False,
                    "violations": [{"transcript": "额外对白"}],
                }

        guard = Guard()
        emitted = []
        with (
            patch(
                "smart_render_worker._request_json",
                side_effect=lambda *_args: {"prompt_id": f"p{guard.calls + 1}"},
            ),
            patch("smart_render_worker.wait_for_history", return_value=({}, {})),
            patch(
                "smart_render_worker.download_outputs",
                return_value=[{"kind": "videos", "local_path": str(video)}],
            ),
            patch("smart_render_worker.time.sleep"),
            patch("smart_render_worker.emit", side_effect=emitted.append),
        ):
            result = queue_segment(job, segment, workflow, [], speech_guard=guard)
        self.assertEqual(guard.calls, 3)
        self.assertEqual(result["attempts_used"], 3)
        self.assertFalse(result["native_speech_guard_result"]["passed"])
        self.assertTrue(
            any("without Hard Block" in str(row.get("progress", "")) for row in emitted)
        )
        video.unlink(missing_ok=True)
        root.rmdir()

    def test_character_swap_identity_failure_retries_with_fresh_seed(self):
        root = PROJECT_ROOT / ".director_cache" / "identity_retry_test"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        video = root / "segment.mp4"
        source = root / "source.mp4"
        source.write_bytes(b"source")
        job = {
            "server": "http://127.0.0.1:8188",
            "http_timeout": 1,
            "segment_attempts": 3,
            "segment_count": 1,
            "history_poll_interval": 0.1,
            "generation_timeout": 10,
            "ffmpeg": "ffmpeg",
            "ffprobe": "ffprobe",
        }
        segment = {
            "segment_id": "seg-identity",
            "index": 0,
            "seed": 456,
            "download_dir": str(root),
            "character_swap_identity_audit": {
                "enabled": True,
                "source_video_path": str(source),
                "source_bboxes_normalized": [[0.1, 0.1, 0.8, 0.9]],
                "maximum_attempts": 3,
            },
        }
        workflows = []
        audit_results = [
            {
                "passed": False,
                "available": True,
                "retention_score": 0.93,
                "action": "retry_fresh_seed",
            },
            {
                "passed": True,
                "available": True,
                "retention_score": 0.31,
                "action": "accept",
            },
        ]

        def queue(request, _timeout):
            payload = json.loads(request.data.decode("utf-8"))
            workflows.append(payload["prompt"])
            return {"prompt_id": f"identity-{len(workflows)}"}

        def download(*_args, **_kwargs):
            video.write_bytes(f"attempt-{len(workflows)}".encode("ascii"))
            return [{"kind": "videos", "local_path": str(video)}]

        with (
            patch("smart_render_worker._request_json", side_effect=queue),
            patch("smart_render_worker.wait_for_history", return_value=({}, {})),
            patch("smart_render_worker.download_outputs", side_effect=download),
            patch(
                "smart_render_worker.inspect_character_swap_identity",
                side_effect=audit_results,
            ) as inspect_identity,
            patch("smart_render_worker.time.sleep"),
            patch("smart_render_worker.emit"),
        ):
            result = queue_segment(
                job,
                segment,
                {"1": {"inputs": {"seed": 456}}},
                [],
            )

        self.assertEqual(inspect_identity.call_count, 2)
        self.assertEqual(result["attempts_used"], 2)
        self.assertTrue(result["character_swap_identity_audit_result"]["passed"])
        self.assertNotEqual(
            workflows[0]["1"]["inputs"]["seed"],
            workflows[1]["1"]["inputs"]["seed"],
        )
        self.assertEqual(video.read_bytes(), b"attempt-2")
        shutil.rmtree(root, ignore_errors=True)

    def test_retry_exhaustion_keeps_lowest_risk_guarded_take(self):
        root = PROJECT_ROOT / ".director_cache" / "smart_render_best_speech_take_test"
        root.mkdir(parents=True, exist_ok=True)
        video = root / "segment.mp4"
        job = {
            "server": "http://127.0.0.1:8188", "http_timeout": 1,
            "segment_attempts": 3, "native_speech_guard_retries": 2,
            "segment_count": 1, "history_poll_interval": 0.1,
            "generation_timeout": 10,
        }
        segment = {
            "segment_id": "seg-best", "index": 0, "seed": 123,
            "download_dir": str(root),
            "native_speech_guard": {"enabled": True, "silence_windows": [[4.0, 5.0]]},
        }

        class Guard:
            calls = 0

            def inspect(self, _video, _spec):
                self.calls += 1
                transcripts = ["啊", "这是很长而且完全不相干的额外对白", "又一条不相干对白"]
                return {
                    "passed": False,
                    "violations": [{
                        "kind": "unauthorized_speech_in_silence_window",
                        "transcript": transcripts[self.calls - 1],
                        "voice_ratio": [0.08, 0.8, 0.4][self.calls - 1],
                    }],
                }

        guard = Guard()

        def download(*_args, **_kwargs):
            video.write_bytes(f"attempt-{guard.calls + 1}".encode("ascii"))
            return [{"kind": "videos", "local_path": str(video)}]

        with (
            patch("smart_render_worker._request_json", side_effect=lambda *_: {"prompt_id": f"p{guard.calls + 1}"}),
            patch("smart_render_worker.wait_for_history", return_value=({}, {})),
            patch("smart_render_worker.download_outputs", side_effect=download),
            patch("smart_render_worker.time.sleep"),
            patch("smart_render_worker.emit"),
        ):
            result = queue_segment(job, segment, {"1": {"inputs": {"seed": 123}}}, [], speech_guard=guard)
        self.assertEqual(result["attempts_used"], 3)
        self.assertEqual(result["selected_guard_attempt"], 1)
        self.assertEqual(video.read_bytes(), b"attempt-1")
        self.assertLess(
            speech_guard_result_score({"passed": False, "violations": [{
                "kind": "unauthorized_speech_in_silence_window", "transcript": "啊", "voice_ratio": 0.08,
            }]}),
            speech_guard_result_score({"passed": False, "violations": [{
                "kind": "unauthorized_speech_in_silence_window", "transcript": "很长的不相干对白", "voice_ratio": 0.8,
            }]}),
        )
        video.unlink(missing_ok=True)
        root.rmdir()

    def test_oom_is_classified_released_and_retried_without_quality_change(self):
        root = PROJECT_ROOT / ".director_cache" / "smart_render_oom_retry_test"
        root.mkdir(parents=True, exist_ok=True)
        video = root / "segment.mp4"
        video.write_bytes(b"video")
        job = {
            "server": "http://127.0.0.1:8188",
            "http_timeout": 1,
            "segment_attempts": 3,
            "segment_count": 1,
            "history_poll_interval": 0.1,
            "generation_timeout": 10,
        }
        segment = {
            "segment_id": "seg-oom",
            "index": 0,
            "download_dir": str(root),
        }
        with (
            patch(
                "smart_render_worker._request_json",
                side_effect=[
                    RuntimeError("CUDA out of memory"),
                    RuntimeError("allocation on device failed"),
                    {"prompt_id": "recovered"},
                ],
            ) as request_json,
            patch("smart_render_worker.wait_for_history", return_value=({}, {})),
            patch(
                "smart_render_worker.download_outputs",
                return_value=[{"kind": "videos", "local_path": str(video)}],
            ),
            patch("smart_render_worker.release_comfy_memory", return_value="released") as release,
            patch("smart_render_worker.time.sleep"),
            patch("smart_render_worker.emit"),
        ):
            result = queue_segment(job, segment, {}, [])
        self.assertEqual(classify_generation_error("CUDA out of memory"), "oom")
        self.assertEqual(result["attempts_used"], 3)
        self.assertEqual(result["failure_class"], "")
        self.assertEqual(request_json.call_count, 3)
        self.assertEqual(release.call_count, 2)
        video.unlink(missing_ok=True)
        root.rmdir()

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
                "ref_images.ref_image_2",
            ],
        )

    def test_visual_continuity_never_patches_paired_audio(self):
        workflow = {
            "9": {"inputs": {"file": "old.mp4"}, "class_type": "LoadVideo"},
            "136": {
                "inputs": {"prompt": ["138", 0]},
                "class_type": "MiniMaxH3ReferenceToVideo",
            },
        }
        continuity = {
            "kind": "video",
            "visual_only": True,
            "loader_node_id": "9",
            "loader_input": "file",
            "h3_node_id": "136",
            "binding": "ref_videos.ref_video_0",
            "connection": ["9", 0],
            "paired_audio_binding": "ref_video_audios.ref_video_audio_0",
            "paired_audio_connection": ["9", 1],
        }
        _patch_continuity(workflow, continuity, "visual_tail.mp4")
        inputs = workflow["136"]["inputs"]
        self.assertEqual(inputs["ref_videos.ref_video_0"], ["9", 0])
        self.assertNotIn("ref_video_audios.ref_video_audio_0", inputs)
    def test_continuity_never_overwrites_an_active_compacted_video_slot(self):
        workflow = {
            "9": {"inputs": {"file": "old.mp4"}, "class_type": "LoadVideo"},
            "136": {
                "inputs": {"ref_videos.ref_video_0": ["3", 0]},
                "class_type": "MiniMaxH3ReferenceToVideo",
            },
        }
        continuity = {
            "kind": "video",
            "loader_node_id": "9",
            "loader_input": "file",
            "h3_node_id": "136",
            "binding": "ref_videos.ref_video_0",
            "connection": ["9", 0],
        }
        with self.assertRaisesRegex(RuntimeError, "slot collision"):
            _patch_continuity(workflow, continuity, "continuity_tail.mp4")
        self.assertEqual(
            workflow["136"]["inputs"]["ref_videos.ref_video_0"], ["3", 0]
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

    def test_preflight_rejects_declared_missing_reference_before_queue(self):
        runtime = load_runtime_paths()
        missing = PROJECT_ROOT / ".director_cache" / "missing_reference.png"
        missing.unlink(missing_ok=True)
        job = {
            "segments": [
                {"start_seconds": 0.0, "end_seconds": 10.0, "workflow": {}},
                {"start_seconds": 10.0, "end_seconds": 20.0, "workflow": {}},
            ],
            "media": [{"path": str(missing)}],
            "ffmpeg": str(runtime.ffmpeg),
            "ffprobe": str(runtime.ffprobe),
            "master_output": str(
                PROJECT_ROOT / ".director_cache" / "missing_preflight" / "master.mp4"
            ),
            "server": "http://127.0.0.1:8188",
        }
        with self.assertRaisesRegex(FileNotFoundError, "Reference media is missing"):
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
        self.assertIn("afade=t=out:st=14.960000:d=0.040000", filters)
        self.assertIn("afade=t=in:st=0:d=0.040000", filters)
        self.assertIn("concat=n=3:v=1:a=1", filters)
        self.assertIn("43.000000", command)

    def test_assembly_normalizes_mixed_video_geometry_and_sar(self):
        runtime = load_runtime_paths()
        root = PROJECT_ROOT / ".director_cache" / "mixed_geometry_assembly_test"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        small = root / "small.mp4"
        large = root / "large.mp4"
        output = root / "master.mp4"
        try:
            for path, size, color in (
                (small, "160x120", "blue"),
                (large, "320x240", "red"),
            ):
                created = subprocess.run(
                    [
                        str(runtime.ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "lavfi", "-i", f"color=c={color}:s={size}:r=24:d=1",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                self.assertEqual(created.returncode, 0, created.stderr)

            result = assemble_master(
                {
                    "master_output": str(output),
                    "ffmpeg": str(runtime.ffmpeg),
                    "ffprobe": str(runtime.ffprobe),
                    "target_duration_seconds": 2.0,
                },
                [
                    {
                        "output_path": str(small),
                        "start_seconds": 0.0,
                        "end_seconds": 1.0,
                    },
                    {
                        "output_path": str(large),
                        "start_seconds": 1.0,
                        "end_seconds": 2.0,
                    },
                ],
            )
            probe = subprocess.run(
                [
                    str(runtime.ffprobe), "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height,sample_aspect_ratio,r_frame_rate",
                    "-of", "json", str(result),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(probe.returncode, 0, probe.stderr)
            stream = json.loads(probe.stdout)["streams"][0]
            self.assertEqual((stream["width"], stream["height"]), (320, 240))
            self.assertEqual(stream["sample_aspect_ratio"], "1:1")
            self.assertEqual(stream["r_frame_rate"], "24/1")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_large_master_assembly_is_split_into_safe_batches(self):
        root = PROJECT_ROOT / ".director_cache" / "large_staged_assembly_test"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        output = root / "master.mp4"
        segments = []
        for index in range(20):
            source = root / f"segment_{index + 1:03d}.mp4"
            source.write_bytes(b"segment")
            segments.append({
                "output_path": str(source),
                "start_seconds": float(index),
                "end_seconds": float(index + 1),
                "overlap_before_seconds": 0.0,
            })
        calls = []

        def fake_run(command, destination, **kwargs):
            calls.append((list(command), Path(destination), dict(kwargs)))
            Path(destination).write_bytes(b"assembled")

        try:
            with patch(
                "smart_render_worker._assembly_canvas", return_value=(704, 704)
            ), patch(
                "smart_render_worker._has_audio", return_value=True
            ), patch(
                "smart_render_worker._run_assembly_command", side_effect=fake_run
            ):
                result = assemble_master(
                    {
                        "master_output": str(output),
                        "ffmpeg": "ffmpeg",
                        "ffprobe": "ffprobe",
                        "target_duration_seconds": 20.0,
                    },
                    segments,
                )
            self.assertEqual(result, output.resolve())
            self.assertEqual(len(calls), 5)
            self.assertTrue(all(path.name.startswith("chunk_") for _, path, _ in calls[:4]))
            self.assertIn("concat", calls[-1][0])
            self.assertEqual(output.read_bytes(), b"assembled")
            self.assertFalse(any(root.glob(".master.assembly-*")))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_assembly_ignores_legacy_plate_and_preserves_native_tail(self):
        from PIL import Image

        runtime = load_runtime_paths()
        root = PROJECT_ROOT / ".director_cache" / "final_hold_video_test"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        source = root / "source.mp4"
        plate = root / "plate.png"
        Image.new("RGB", (160, 90), (20, 80, 220)).save(plate)
        try:
            created = subprocess.run(
                [
                    str(runtime.ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=red:s=160x90:r=24:d=2",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", str(source),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            original_bytes = source.read_bytes()
            result = assemble_master({
                "master_output": str(root / "out.mp4"),
                "ffmpeg": str(runtime.ffmpeg), "ffprobe": str(runtime.ffprobe),
                "target_duration_seconds": 2.0,
                "final_hold_plate": str(plate), "final_hold_seconds": .5,
            }, [{"output_path": str(source), "start_seconds": 0.0, "end_seconds": 2.0}])
            self.assertEqual(source.read_bytes(), original_bytes)
            audio_probe = subprocess.run(
                [
                    str(runtime.ffprobe), "-v", "error", "-select_streams", "a:0",
                    "-show_entries", "stream=index", "-of", "csv=p=0", str(result),
                ],
                capture_output=True, text=True, timeout=30,
            )
            self.assertTrue(audio_probe.stdout.strip())
            frame = root / "tail.png"
            extracted = subprocess.run(
                [
                    str(runtime.ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", "1.75", "-i", str(result), "-frames:v", "1", str(frame),
                ],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(extracted.returncode, 0, extracted.stderr)
            pixel = Image.open(frame).convert("RGB").getpixel((80, 45))
            self.assertGreater(pixel[0], 180)
            self.assertLess(pixel[2], 80)
        finally:
            shutil.rmtree(root, ignore_errors=True)

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
            self.assertEqual(manifest["segments"][0]["failure_class"], "oom")
            self.assertEqual(manifest["segments"][0]["retry_budget"], 3)
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
                patch(
                    "smart_render_worker.release_comfy_memory",
                    return_value="released",
                ) as release,
                patch("smart_render_worker.assemble_master", return_value=master_output),
                patch("smart_render_worker.emit", side_effect=events.append),
            ):
                self.assertEqual(main(), 0)
            self.assertEqual(release.call_count, 1)
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

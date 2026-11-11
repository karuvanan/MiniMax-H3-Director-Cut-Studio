"""Regression coverage for LAN disconnect recovery without duplicate prompts."""

from io import BytesIO
import json
from pathlib import Path
import shutil
import sys
import unittest
import urllib.error
from unittest.mock import MagicMock, patch
import uuid

from comfy_submit_worker import (
    ComfyConnectionRecoveryTimeout,
    download_outputs,
    main as submit_main,
    wait_for_history,
)
from smart_render_worker import queue_character_swap_passes, queue_segment


class ComfyConnectionRecoveryTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parent / ".director_cache"
        cache.mkdir(exist_ok=True)
        self.root = cache / ("comfy_reconnect_" + uuid.uuid4().hex)
        self.root.mkdir()
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_history_poll_reconnects_to_same_prompt_after_transport_loss(self):
        completed = {
            "prompt-1": {
                "status": {"completed": True, "status_str": "success"},
                "outputs": {
                    "9": {"videos": [{"filename": "finished.mp4", "type": "output"}]}
                },
            }
        }
        with (
            patch(
                "comfy_submit_worker._request_json",
                side_effect=[urllib.error.URLError("LAN down"), completed],
            ) as request_json,
            patch("comfy_submit_worker.time.sleep"),
            patch("comfy_submit_worker._connection_event") as event,
        ):
            history, outputs = wait_for_history(
                "http://remote:8188",
                "prompt-1",
                poll_interval=0.1,
                generation_timeout=30,
                http_timeout=1,
                reconnect_timeout=60,
                segment_id="SEG-1",
            )
        self.assertTrue(history["status"]["completed"])
        self.assertEqual(outputs[0]["filename"], "finished.mp4")
        self.assertEqual(request_json.call_count, 2)
        self.assertEqual([call.args[0] for call in event.call_args_list], [
            "disconnected", "reconnected",
        ])

    def test_output_download_retries_same_file_and_replaces_partial_atomically(self):
        response = MagicMock()
        response.__enter__.return_value = BytesIO(b"complete-mp4")
        response.__exit__.return_value = False
        with (
            patch(
                "comfy_submit_worker._direct_urlopen",
                side_effect=[urllib.error.URLError("temporary loss"), response],
            ) as urlopen,
            patch("comfy_submit_worker.time.sleep"),
            patch("comfy_submit_worker._connection_event"),
        ):
            rows = download_outputs(
                "http://remote:8188",
                [{"node_id": "9", "kind": "videos", "filename": "out.mp4"}],
                self.root,
                1,
                reconnect_timeout=60,
                prompt_id="prompt-2",
            )
        destination = Path(rows[0]["local_path"])
        self.assertEqual(destination.read_bytes(), b"complete-mp4")
        self.assertFalse(destination.with_suffix(".mp4.part").exists())
        self.assertEqual(urlopen.call_count, 2)

    def test_output_download_refreshes_history_descriptor_without_requeue(self):
        response = MagicMock()
        response.__enter__.return_value = BytesIO(b"refreshed-output")
        response.__exit__.return_value = False
        history = {
            "prompt-3": {
                "status": {"completed": True, "status_str": "success"},
                "outputs": {
                    "9": {
                        "videos": [
                            {
                                "filename": "new.mp4",
                                "subfolder": "fresh",
                                "type": "output",
                            }
                        ]
                    }
                },
            }
        }
        with (
            patch(
                "comfy_submit_worker._direct_urlopen",
                side_effect=[urllib.error.URLError("stale view socket"), response],
            ) as urlopen,
            patch("comfy_submit_worker._request_json", return_value=history) as refresh,
            patch("comfy_submit_worker.time.monotonic", side_effect=[0.0, 6.0, 7.0]),
            patch("comfy_submit_worker.time.sleep"),
            patch("comfy_submit_worker._connection_event"),
        ):
            rows = download_outputs(
                "http://remote:8188",
                [
                    {
                        "node_id": "9",
                        "kind": "videos",
                        "filename": "old.mp4",
                        "subfolder": "stale",
                    }
                ],
                self.root,
                1,
                reconnect_timeout=3600,
                download_recovery_timeout=120,
                history_refresh_interval=5.0,
                prompt_id="prompt-3",
            )
        self.assertEqual(Path(rows[0]["local_path"]).read_bytes(), b"refreshed-output")
        self.assertEqual(rows[0]["filename"], "new.mp4")
        self.assertIn("filename=new.mp4", urlopen.call_args_list[1].args[0].full_url)
        self.assertEqual(refresh.call_count, 1)

    def test_output_download_has_bounded_recovery_but_preserves_prompt(self):
        with (
            patch(
                "comfy_submit_worker._direct_urlopen",
                side_effect=urllib.error.URLError("LAN down"),
            ),
            patch("comfy_submit_worker.time.monotonic", side_effect=[0.0, 1.0, 122.0]),
            patch("comfy_submit_worker.time.sleep"),
        ):
            with self.assertRaises(ComfyConnectionRecoveryTimeout) as raised:
                download_outputs(
                    "http://remote:8188",
                    [{"node_id": "9", "kind": "videos", "filename": "out.mp4"}],
                    self.root,
                    1,
                    reconnect_timeout=3600,
                    download_recovery_timeout=120,
                    prompt_id="prompt-bounded",
                )
        self.assertEqual(raised.exception.prompt_id, "prompt-bounded")
        self.assertIn("was not re-queued", str(raised.exception))

    def test_smart_segment_does_not_requeue_accepted_prompt_after_recovery_timeout(self):
        job = {
            "server": "http://remote:8188",
            "http_timeout": 1,
            "segment_attempts": 3,
            "segment_count": 1,
            "history_poll_interval": 0.1,
            "generation_timeout": 30,
            "connection_recovery_timeout": 60,
        }
        segment = {"segment_id": "SEG-1", "index": 0, "download_dir": str(self.root)}
        with (
            patch("smart_render_worker._request_json", return_value={"prompt_id": "known"}) as queue,
            patch(
                "smart_render_worker.wait_for_history",
                side_effect=ComfyConnectionRecoveryTimeout("known", "still disconnected"),
            ),
            patch("smart_render_worker.release_comfy_memory") as release,
            patch("smart_render_worker.emit"),
        ):
            with self.assertRaises(ComfyConnectionRecoveryTimeout):
                queue_segment(job, segment, {}, [])
        self.assertEqual(queue.call_count, 1)
        release.assert_not_called()

    def test_smart_segment_resumes_persisted_prompt_without_posting_again(self):
        video = self.root / "recovered.mp4"
        video.write_bytes(b"video")
        job = {
            "server": "http://remote:8188",
            "http_timeout": 1,
            "segment_attempts": 3,
            "segment_count": 1,
            "history_poll_interval": 0.1,
            "generation_timeout": 30,
        }
        segment = {
            "segment_id": "SEG-1",
            "index": 0,
            "download_dir": str(self.root),
            "status": "monitoring",
            "prompt_id": "persisted-prompt",
            "attempts_used": 1,
        }
        with (
            patch("smart_render_worker._request_json") as queue,
            patch(
                "smart_render_worker.wait_for_history",
                return_value=({"status": {"completed": True}}, [{"filename": "x.mp4"}]),
            ),
            patch(
                "smart_render_worker.download_outputs",
                return_value=[{"kind": "videos", "local_path": str(video)}],
            ),
            patch("smart_render_worker.emit"),
        ):
            result = queue_segment(job, segment, {}, [])
        queue.assert_not_called()
        self.assertEqual(result["prompt_id"], "persisted-prompt")
        self.assertEqual(result["status"], "complete")

    def test_character_swap_resumes_download_prompt_instead_of_requeueing(self):
        video = self.root / "relay-recovered.mp4"
        video.write_bytes(b"video")
        segment = {
            "segment_id": "SEG-SWAP",
            "index": 0,
            "download_dir": str(self.root),
            "status": "monitoring",
            "prompt_id": "relay-prompt",
            "attempts_used": 1,
            "active_character_swap_pass_index": 0,
            "character_swap_engine": "akatz-h3-relay",
            "character_swap_passes": [
                {
                    "source_role_id": "R1",
                    "target_media_id": "P1",
                    "workflow": {},
                }
            ],
        }

        def resumed(_job, pass_segment, _workflow, _uploaded, **_kwargs):
            self.assertEqual(pass_segment["status"], "monitoring")
            self.assertEqual(pass_segment["prompt_id"], "relay-prompt")
            return {
                "status": "complete",
                "output_path": str(video),
                "prompt_id": "relay-prompt",
                "outputs": [],
                "uploaded": [],
                "attempts_used": 1,
            }

        with patch("smart_render_worker.queue_segment", side_effect=resumed) as queue:
            result = queue_character_swap_passes(
                {"server": "http://remote:8188", "http_timeout": 1},
                segment,
                [],
            )
        self.assertEqual(queue.call_count, 1)
        self.assertEqual(result["output_path"], str(video.resolve()))

    def test_native_job_checkpoints_prompt_id_and_reuses_it_on_worker_restart(self):
        job_path = self.root / "native.job.json"
        job_path.write_text(
            json.dumps(
                {
                    "server": "http://remote:8188",
                    "workflow": {},
                    "media": [],
                    "wait_for_completion": True,
                    "download_dir": str(self.root / "downloads"),
                }
            ),
            encoding="utf-8",
        )
        with (
            patch.object(sys, "argv", ["comfy_submit_worker.py", str(job_path)]),
            patch("comfy_submit_worker._request_json", return_value={"prompt_id": "native-prompt"}) as queue,
            patch("comfy_submit_worker.wait_for_history", return_value=({"status": {"completed": True}}, [])),
        ):
            self.assertEqual(submit_main(), 0)
        checkpoint = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(checkpoint["queued_prompt_id"], "native-prompt")
        self.assertEqual(queue.call_count, 1)

        with (
            patch.object(sys, "argv", ["comfy_submit_worker.py", str(job_path)]),
            patch("comfy_submit_worker._request_json") as duplicate_queue,
            patch("comfy_submit_worker.wait_for_history", return_value=({"status": {"completed": True}}, [])),
            patch("comfy_submit_worker._connection_event"),
        ):
            self.assertEqual(submit_main(), 0)
        duplicate_queue.assert_not_called()


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest

from workflow_engine import (
    assign_local_media,
    compile_active_workflow,
    load_workflow,
    scan_workflow_data,
    suggested_reference_rules,
)


class WorkflowEngineTests(unittest.TestCase):
    def test_scans_direct_image_audio_and_video_graph(self):
        payload = {
            "1": {"class_type": "LoadImage", "inputs": {"image": "hero.png"}},
            "2": {"class_type": "LoadVideo", "inputs": {"file": "move.mp4"}},
            "3": {"class_type": "GetVideoComponents", "inputs": {"video": ["2", 0]}},
            "4": {"class_type": "LoadAudio", "inputs": {"audio": "line.wav"}},
            "9": {
                "class_type": "MiniMaxH3ReferenceToVideo",
                "inputs": {
                    "ref_images.ref_image_0": ["1", 0],
                    "ref_videos.ref_video_0": ["3", 0],
                    "ref_video_audios.ref_video_audio_0": ["3", 1],
                    "ref_audios.ref_audio_0": ["4", 0],
                },
            },
        }
        scan = scan_workflow_data(payload)
        self.assertEqual(scan.counts, {"image": 1, "video": 1, "audio": 1})
        tags = [asset.tag for asset in scan.assets]
        self.assertIn("<Picture 1>", tags)
        self.assertIn("<Video 1>", tags)
        self.assertIn("<Audio 1>", tags)
        video = next(asset for asset in scan.assets if asset.media_type == "video")
        self.assertEqual(video.paired_audio_binding, "ref_video_audios.ref_video_audio_0")
        visual, audio = suggested_reference_rules(scan)
        self.assertIn("hero.png", visual)
        self.assertIn("line.wav", audio)

    def test_warns_when_bypassed_nodes_were_removed(self):
        payload = {
            "1": {"class_type": "LoadImage", "inputs": {"image": "hero.png"}},
            "9": {
                "class_type": "MiniMaxH3ReferenceToVideo",
                "inputs": {"ref_images.ref_image_0": ["1", 0]},
            },
        }
        scan = scan_workflow_data(payload)
        warnings = " ".join(scan.warnings)
        self.assertIn("LoadVideo", warnings)
        self.assertIn("LoadAudio", warnings)

    def test_current_three_image_api_maps_picture_order(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v API 3IMAGE 1AUDIO 1VIDEO.json"
        if not path.exists():
            self.skipTest("sample workflow not available")
        scan = load_workflow(path)
        pictures = [asset for asset in scan.assets if asset.media_type == "image"]
        self.assertEqual(len(pictures), 3)
        self.assertEqual([asset.tag for asset in pictures], ["<Picture 1>", "<Picture 2>", "<Picture 3>"])
        self.assertEqual(scan.counts["video"], 0)
        self.assertEqual(scan.counts["audio"], 0)

    def test_latest_max_pool_api_has_nine_three_three(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        self.assertEqual(scan.counts, {"image": 9, "video": 3, "audio": 3})
        self.assertEqual(scan.duration_seconds, 12.0)
        self.assertTrue(all(asset.paired_audio_binding for asset in scan.assets if asset.media_type == "video"))

    def test_time_window_disconnects_irrelevant_reference_bindings(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        pictures = [asset for asset in scan.assets if asset.media_type == "image"]
        pictures[0].start_seconds, pictures[0].end_seconds = 0.0, 4.0
        pictures[1].start_seconds, pictures[1].end_seconds = 6.0, 10.0
        pictures[0].timeline_placed = True
        pictures[1].timeline_placed = True
        compiled, active = compile_active_workflow(scan, 0.0, 5.0)
        h3_inputs = compiled[scan.h3_node_ids[0]]["inputs"]
        self.assertIn("ref_images.ref_image_0", h3_inputs)
        self.assertNotIn("ref_images.ref_image_1", h3_inputs)
        self.assertIn(pictures[0], active)
        self.assertNotIn(pictures[1], active)
        duration_values = [
            node["inputs"]["value"]
            for node in compiled.values()
            if node.get("class_type") == "PrimitiveFloat"
            and "duration" in node.get("_meta", {}).get("title", "").lower()
        ]
        self.assertEqual(duration_values, [5.0])

    def test_activation_modes_override_auto_window(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        first, second, third = [asset for asset in scan.assets if asset.media_type == "image"][:3]
        first.start_seconds, first.end_seconds = 0.0, 2.0
        second.start_seconds, second.end_seconds = 8.0, 10.0
        third.start_seconds, third.end_seconds = 0.0, 2.0
        first.timeline_placed = second.timeline_placed = third.timeline_placed = True
        second.activation_mode = "active"
        third.activation_mode = "bypass"
        _, active = compile_active_workflow(scan, 0.0, 3.0)
        self.assertIn(first, active)
        self.assertIn(second, active)
        self.assertNotIn(third, active)

    def test_asset_outside_timeline_can_never_activate(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        asset = next(item for item in scan.assets if item.media_type == "image")
        asset.activation_mode = "active"
        asset.timeline_placed = False
        compiled, active = compile_active_workflow(scan, 0.0, 3.0)
        self.assertNotIn(asset, active)
        inputs = compiled[scan.h3_node_ids[0]]["inputs"]
        self.assertNotIn(asset.binding, inputs)

    def test_assign_local_media_keeps_editor_path_but_sets_loader_basename(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        asset = next(item for item in scan.assets if item.media_type == "image")
        source = Path(__file__).parent / ".director_cache" / "runtime_smoke" / "sample.png"
        if not source.exists():
            self.skipTest("runtime smoke image not available")
        assign_local_media(scan, asset, source)
        self.assertEqual(asset.local_path, str(source.resolve()))
        self.assertEqual(asset.filename, "sample.png")
        self.assertEqual(scan.nodes[asset.node_id]["inputs"]["image"], "sample.png")

    def test_generation_parameters_patch_latest_nodes_and_bypass_rtx_for_preview(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        compiled, _ = compile_active_workflow(
            scan,
            0.0,
            3.0,
            generation={
                "aspect_ratio": "9:16",
                "megapixels": 0.2,
                "sampling_steps": 6,
                "denoise": 0.75,
                "seed": 123456,
                "enable_rtx_vsr": False,
            },
        )
        self.assertEqual(
            compiled["115"]["inputs"]["aspect_ratio"],
            "9:16 (Portrait Widescreen)",
        )
        self.assertEqual(compiled["115"]["inputs"]["megapixels"], 0.2)
        self.assertEqual(compiled["124"]["inputs"]["steps"], 6)
        self.assertEqual(compiled["124"]["inputs"]["denoise"], 0.75)
        self.assertEqual(compiled["129"]["inputs"]["noise_seed"], 123456)
        self.assertEqual(compiled["130"]["inputs"]["images"], ["122", 0])
        self.assertEqual(scan.nodes["130"]["inputs"]["images"], ["147", 0])


if __name__ == "__main__":
    unittest.main()

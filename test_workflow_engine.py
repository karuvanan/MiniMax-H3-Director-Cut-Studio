from pathlib import Path
from copy import deepcopy
import unittest

from workflow_engine import (
    assign_local_media,
    compile_active_workflow,
    create_virtual_media_asset,
    effective_reference_assets,
    load_workflow,
    media_upload_manifest,
    paired_audio_reference_tags,
    patch_media_upload_names,
    remap_reference_tokens,
    scan_workflow_data,
    stable_reference_id,
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

    def test_effective_tags_follow_connected_r2v_order_not_pool_slot(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        pictures = [asset for asset in scan.assets if asset.media_type == "image"]
        videos = [asset for asset in scan.assets if asset.media_type == "video"]
        audios = [asset for asset in scan.assets if asset.media_type == "audio"]

        # Physical Picture 1 and Picture 5 become the first two connected
        # references.  A hidden continuity still appended by the worker is the
        # third, regardless of which free loader slot stores it.
        effective, continuity_tag = effective_reference_assets(
            [pictures[0], pictures[4], videos[1], audios[2]],
            extra_kind="image",
        )
        self.assertEqual(
            [asset.tag for asset in effective if asset.media_type == "image"],
            ["<Picture 1>", "<Picture 2>"],
        )
        self.assertEqual(continuity_tag, "<Picture 3>")
        self.assertEqual(
            next(asset.tag for asset in effective if asset.media_type == "video"),
            "<Video 1>",
        )
        # The active video's paired soundtrack receives <Audio 1>; the
        # standalone audio therefore becomes <Audio 2>.
        self.assertEqual(
            next(asset.tag for asset in effective if asset.media_type == "audio"),
            "<Audio 2>",
        )

        effective, continuity_tag = effective_reference_assets(
            [pictures[0], pictures[4]],
            extra_kind="image",
            extra_binding=pictures[1].binding,
        )
        # Hidden context is always appended after ordinary request references;
        # its spare physical loader slot must not renumber active media.
        self.assertEqual(continuity_tag, "<Picture 3>")
        self.assertEqual(
            [asset.tag for asset in effective if asset.media_type == "image"],
            ["<Picture 1>", "<Picture 2>"],
        )

    def test_stable_reference_ids_come_from_physical_bindings(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        picture_4 = [asset for asset in scan.assets if asset.media_type == "image"][3]
        video_2 = [asset for asset in scan.assets if asset.media_type == "video"][1]
        audio_3 = [asset for asset in scan.assets if asset.media_type == "audio"][2]
        picture_4.tag = "<Picture 1>"
        video_2.tag = "<Video 1>"
        audio_3.tag = "<Audio 1>"
        self.assertEqual(stable_reference_id(picture_4), "P4")
        self.assertEqual(stable_reference_id(video_2), "V2")
        self.assertEqual(stable_reference_id(audio_3), "A3")

    def test_reference_remapping_uses_active_p4_and_p7_effective_ordinals(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        pictures = [asset for asset in scan.assets if asset.media_type == "image"]
        effective, _ = effective_reference_assets([pictures[3], pictures[6]])
        authored = (
            "Preserve @P4 for the escaping woman and use legacy <Picture 7> "
            "for the beauty salon entrance."
        )
        compiled = remap_reference_tokens(authored, scan.assets, effective)
        self.assertIn("<Picture 1> for the escaping woman", compiled)
        self.assertIn("<Picture 2> for the beauty salon entrance", compiled)

    def test_inactive_legacy_reference_cannot_alias_an_active_effective_tag(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        pictures = [asset for asset in scan.assets if asset.media_type == "image"]
        effective, _ = effective_reference_assets([pictures[3], pictures[6]])
        compiled = remap_reference_tokens(
            "Use <Picture 1> for the salon signage and @P99 for a prop.",
            scan.assets,
            effective,
        )
        self.assertIn("[P1 reference is inactive in this segment]", compiled)
        self.assertIn("[P99 reference is unavailable]", compiled)
        self.assertNotIn("<Picture 1>", compiled)

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

    def test_same_pool_source_can_have_multiple_independent_timeline_uses(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        source = next(asset for asset in scan.assets if asset.media_type == "image")
        source.timeline_placed = True
        source.start_seconds, source.end_seconds = 1.0, 5.0
        repeated = deepcopy(source)
        repeated.clip_id = "clip-repeat-p1"
        repeated.source_node_id = source.node_id
        repeated.start_seconds, repeated.end_seconds = 8.0, 11.0
        repeated.clip_prompt = "Return to the same subject from a new angle."
        scan.timeline_clips.append(repeated)

        _, early = compile_active_workflow(scan, 1.0, 4.0)
        _, late = compile_active_workflow(scan, 8.0, 11.0)
        self.assertEqual(early, [source])
        self.assertEqual(late, [repeated])

        effective, _ = effective_reference_assets([source, repeated])
        self.assertEqual([asset.tag for asset in effective], ["<Picture 1>", "<Picture 1>"])

    def test_repeated_clip_with_editor_node_id_still_shares_one_effective_tag(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        source = next(asset for asset in scan.assets if asset.media_type == "image")
        repeated = deepcopy(source)
        repeated.node_id = "timeline-instance-only"
        repeated.source_node_id = source.node_id
        repeated.clip_id = "clip-distinct-editor-id"
        effective, _ = effective_reference_assets([source, repeated])
        self.assertEqual([asset.tag for asset in effective], ["<Picture 1>", "<Picture 1>"])

    def test_paired_video_soundtracks_receive_effective_audio_tags(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        videos = [asset for asset in scan.assets if asset.media_type == "video"]
        audios = [asset for asset in scan.assets if asset.media_type == "audio"]
        effective, _ = effective_reference_assets([videos[1], videos[2], audios[2]])
        paired = paired_audio_reference_tags(effective)
        self.assertEqual(list(paired.values()), ["<Audio 1>", "<Audio 2>"])
        standalone = next(asset for asset in effective if asset.media_type == "audio")
        self.assertEqual(standalone.tag, "<Audio 3>")

    def test_mixed_picture_video_audio_window_compiles_stable_ids_together(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        pictures = [asset for asset in scan.assets if asset.media_type == "image"]
        videos = [asset for asset in scan.assets if asset.media_type == "video"]
        audios = [asset for asset in scan.assets if asset.media_type == "audio"]
        active = [pictures[3], pictures[6], videos[1], audios[2]]
        for asset in active:
            asset.timeline_placed = True
            asset.start_seconds = 20.0
            asset.end_seconds = 25.0

        compiled_workflow, compiled_assets = compile_active_workflow(scan, 20.0, 25.0)
        inputs = compiled_workflow[scan.h3_node_ids[0]]["inputs"]
        # Stable P4/P7 identities are dynamically loaded into the first two
        # physical image templates for this Segment.
        self.assertEqual(inputs["ref_images.ref_image_0"], [pictures[0].node_id, 0])
        self.assertEqual(inputs["ref_images.ref_image_1"], [pictures[1].node_id, 0])
        self.assertEqual(
            inputs["ref_videos.ref_video_0"],
            scan.nodes[scan.h3_node_ids[0]]["inputs"][videos[0].binding],
        )
        self.assertEqual(
            inputs["ref_video_audios.ref_video_audio_0"],
            scan.nodes[scan.h3_node_ids[0]]["inputs"][videos[0].paired_audio_binding],
        )
        self.assertEqual(
            inputs["ref_audios.ref_audio_0"],
            scan.nodes[scan.h3_node_ids[0]]["inputs"][audios[0].binding],
        )
        self.assertNotIn("ref_images.ref_image_2", inputs)
        self.assertNotIn("ref_videos.ref_video_1", inputs)
        self.assertNotIn("ref_audios.ref_audio_1", inputs)

        effective, _ = effective_reference_assets(compiled_assets)
        compiled_prompt = remap_reference_tokens(
            "Use @P4 and @P7 with @V2 motion and @A3 sound. "
            "Do not alias inactive @P1, @V1 or @A1.",
            scan.assets,
            effective,
        )
        self.assertIn("<Picture 1> and <Picture 2>", compiled_prompt)
        self.assertIn("<Video 1> motion", compiled_prompt)
        # V2's enabled synchronized soundtrack is Audio 1, so standalone A3
        # correctly becomes the second Audio signal in this request.
        self.assertIn("<Audio 2> sound", compiled_prompt)
        self.assertIn("[P1 reference is inactive in this segment]", compiled_prompt)
        self.assertIn("[V1 reference is inactive in this segment]", compiled_prompt)
        self.assertIn("[A1 reference is inactive in this segment]", compiled_prompt)

    def test_virtual_pool_p10_v4_a4_are_loaded_per_segment(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        scan.duration_seconds = 30.0
        p10 = create_virtual_media_asset(scan, "image")
        v4 = create_virtual_media_asset(scan, "video")
        a4 = create_virtual_media_asset(scan, "audio")
        self.assertEqual((stable_reference_id(p10), stable_reference_id(v4), stable_reference_id(a4)), ("P10", "V4", "A4"))
        self.assertEqual(scan.counts, {"image": 9, "video": 3, "audio": 3})
        self.assertEqual(scan.logical_counts, {"image": 10, "video": 4, "audio": 4})

        for asset in (p10, v4, a4):
            asset.timeline_placed = True
            asset.start_seconds = 15.0
            asset.end_seconds = 30.0
        compiled, active = compile_active_workflow(scan, 15.0, 30.0)
        inputs = compiled[scan.h3_node_ids[0]]["inputs"]
        self.assertIn("ref_images.ref_image_0", inputs)
        self.assertIn("ref_videos.ref_video_0", inputs)
        self.assertIn("ref_audios.ref_audio_0", inputs)
        self.assertEqual({stable_reference_id(asset) for asset in active}, {"P10", "V4", "A4"})
        effective, _ = effective_reference_assets(active)
        prompt = remap_reference_tokens("Use @P10, @V4 and @A4.", scan.assets, effective)
        self.assertIn("<Picture 1>", prompt)
        self.assertIn("<Video 1>", prompt)
        # V4 carries paired audio as Audio 1, so A4 is Audio 2.
        self.assertIn("<Audio 2>", prompt)

    def test_virtual_pool_rejects_more_than_nine_overlapping_images(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        pictures = [asset for asset in scan.assets if asset.media_type == "image"]
        p10 = create_virtual_media_asset(scan, "image")
        for asset in [*pictures, p10]:
            asset.timeline_placed = True
            asset.start_seconds = 0.0
            asset.end_seconds = 5.0
        with self.assertRaisesRegex(ValueError, "supports only 9 physical image slots"):
            compile_active_workflow(scan, 0.0, 5.0)

    def test_same_basename_uploads_receive_distinct_loader_names(self):
        path = Path(__file__).parent / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
        scan = load_workflow(path)
        pictures = [asset for asset in scan.assets if asset.media_type == "image"][:2]
        root = Path(__file__).parent / ".director_cache" / "upload_collision_test"
        first = root / "one" / "image.png"
        second = root / "two" / "image.png"
        first.parent.mkdir(parents=True, exist_ok=True)
        second.parent.mkdir(parents=True, exist_ok=True)
        first.write_bytes(b"first")
        second.write_bytes(b"second")
        for asset, local in zip(pictures, (first, second)):
            asset.local_path = str(local.resolve())
            asset.timeline_placed = True
            asset.start_seconds = 0.0
            asset.end_seconds = 5.0

        compiled, active = compile_active_workflow(scan, 0.0, 5.0)
        uploads = media_upload_manifest(active)
        patch_media_upload_names(compiled, uploads)
        self.assertEqual(len(uploads), 2)
        self.assertEqual(len({row["upload_name"] for row in uploads}), 2)
        self.assertNotEqual(uploads[0]["upload_name"], "image.png")
        for row in uploads:
            node = compiled[row["loader_node_id"]]
            self.assertEqual(
                node["inputs"][row["loader_input"]], row["upload_name"]
            )

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

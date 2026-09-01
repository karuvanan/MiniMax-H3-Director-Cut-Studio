import unittest

from segment_engine import (
    align_segments_to_dialogue_turns,
    content_fingerprint,
    derive_segment_seed,
    derive_named_segment_seed,
    dirty_segment_indexes,
    plan_render_segments,
    plan_shot_render_segments,
    protect_segment_boundaries_from_speech,
    rebase_timed_rows,
    reuse_cached_segments,
    scope_timed_prompt_text,
)


class SegmentEngineTests(unittest.TestCase):
    def test_native_length_keeps_one_exact_segment(self):
        rows = plan_render_segments(0.0, 12.0)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].start_seconds, rows[0].end_seconds), (0.0, 12.0))
        self.assertEqual(rows[0].overlap_before_seconds, 0.0)

    def test_sixty_seconds_uses_hidden_fifteen_second_windows(self):
        rows = plan_render_segments(0.0, 60.0)
        self.assertEqual(
            [(row.start_seconds, row.end_seconds) for row in rows],
            [(0.0, 15.0), (14.0, 29.0), (28.0, 43.0), (42.0, 57.0), (56.0, 60.0)],
        )
        self.assertTrue(all(row.duration_seconds <= 15.0 for row in rows))

    def test_nonzero_work_area_remains_in_global_time(self):
        rows = plan_render_segments(10.0, 42.0)
        self.assertEqual(
            [(row.start_seconds, row.end_seconds) for row in rows],
            [(10.0, 25.0), (24.0, 39.0), (38.0, 42.0)],
        )

    def test_segment_seeds_are_stable_and_distinct(self):
        seeds = [derive_segment_seed(12345, index) for index in range(4)]
        self.assertEqual(seeds, [derive_segment_seed(12345, index) for index in range(4)])
        self.assertEqual(len(set(seeds)), 4)
        self.assertEqual(
            derive_named_segment_seed(12345, "shot_006000_009000"),
            derive_named_segment_seed(12345, "shot_006000_009000"),
        )

    def test_shot_planner_merges_micro_beats_without_replaying_leading_handles(self):
        shots = [
            {"cue_id": "S1", "start_seconds": 0.0, "end_seconds": 3.0},
            {"cue_id": "S2", "start_seconds": 3.0, "end_seconds": 6.0},
            {"cue_id": "S3", "start_seconds": 6.0, "end_seconds": 8.0},
            {"cue_id": "S4", "start_seconds": 8.0, "end_seconds": 9.0},
            {"cue_id": "S5", "start_seconds": 9.0, "end_seconds": 11.0},
            {"cue_id": "S6", "start_seconds": 11.0, "end_seconds": 13.0},
            {"cue_id": "S7", "start_seconds": 13.0, "end_seconds": 15.0},
        ]
        rows = plan_shot_render_segments(0.0, 15.0, shots)
        self.assertEqual(
            [(row.core_start_seconds, row.core_end_seconds) for row in rows],
            [(0.0, 3.0), (3.0, 6.0), (6.0, 9.0), (9.0, 15.0)],
        )
        self.assertEqual(rows[2].shot_ids, ["S3", "S4"])
        self.assertTrue(all(row.duration_seconds <= 15.0 for row in rows))
        self.assertEqual(rows[1].overlap_before_seconds, 0.0)
        self.assertEqual(rows[1].continuity_mode, "match_action")

    def test_explicit_shot_boundary_mode_is_preserved(self):
        rows = plan_shot_render_segments(
            0.0,
            20.0,
            [
                {"cue_id": "S1", "start_seconds": 0.0, "end_seconds": 10.0},
                {
                    "cue_id": "S2",
                    "start_seconds": 10.0,
                    "end_seconds": 20.0,
                    "continuity_mode": "hard_cut",
                },
            ],
        )
        self.assertEqual(rows[1].continuity_mode, "hard_cut")
        self.assertEqual(rows[1].start_seconds, rows[1].core_start_seconds)

    def test_native_speech_moves_internal_boundaries_past_line_and_decay_tail(self):
        planned = plan_shot_render_segments(
            0.0,
            70.0,
            [
                {"cue_id": "S1", "start_seconds": 0.0, "end_seconds": 8.0},
                {"cue_id": "S2", "start_seconds": 8.0, "end_seconds": 20.0},
                {"cue_id": "S3", "start_seconds": 20.0, "end_seconds": 32.5},
                {"cue_id": "S4", "start_seconds": 32.5, "end_seconds": 40.5},
                {"cue_id": "S5", "start_seconds": 40.5, "end_seconds": 53.0},
                {"cue_id": "S6", "start_seconds": 53.0, "end_seconds": 59.5},
                {"cue_id": "S7", "start_seconds": 59.5, "end_seconds": 70.0},
            ],
            min_segment_seconds=15.0,
            overlap_seconds=0.0,
        )
        protected = protect_segment_boundaries_from_speech(
            planned,
            [
                {"content_role": "voice_over", "start_seconds": 0.5, "end_seconds": 7.5},
                {"content_role": "voice_over", "start_seconds": 8.5, "end_seconds": 19.5},
                {"content_role": "voice_over", "start_seconds": 33.0, "end_seconds": 40.0},
                {"content_role": "dialogue", "start_seconds": 58.0, "end_seconds": 60.0},
            ],
            tail_seconds=1.0,
        )
        self.assertEqual(
            [row.core_end_seconds for row in protected[:-1]],
            [8.5, 20.5, 32.5, 41.0, 53.0, 61.0],
        )
        self.assertTrue(all(row.duration_seconds <= 15.0 for row in protected))
        self.assertTrue(
            all(
                not (line[0] < row.core_end_seconds < line[1])
                for row in protected[:-1]
                for line in [(0.5, 7.5), (8.5, 19.5), (33.0, 40.0), (58.0, 60.0)]
            )
        )

    def test_speech_boundary_uses_backward_safe_cut_when_forward_exceeds_h3_limit(self):
        planned = plan_render_segments(0.0, 25.0, overlap_seconds=0.0)
        protected = protect_segment_boundaries_from_speech(
            planned,
            [{
                "content_role": "dialogue",
                "start_seconds": 14.0,
                "end_seconds": 16.0,
            }],
            tail_seconds=1.0,
        )
        self.assertEqual(protected[0].core_end_seconds, 14.0)
        self.assertEqual(protected[1].core_start_seconds, 14.0)
        self.assertTrue(all(row.duration_seconds <= 15.0 for row in protected))

    def test_decay_tail_never_pushes_cut_across_next_speech_start(self):
        shots = [
            {"cue_id": f"S{index + 1}", "start_seconds": start, "end_seconds": end}
            for index, (start, end) in enumerate((
                (0.0, 8.5), (8.5, 22.0), (22.0, 32.5), (32.5, 41.0),
                (41.0, 49.5), (49.5, 60.0), (60.0, 70.0),
            ))
        ]
        planned = plan_shot_render_segments(
            0.0, 70.0, shots, min_segment_seconds=15.0,
            max_segment_seconds=15.0, overlap_seconds=0.0,
        )
        speech = [
            {"content_role": role, "start_seconds": start, "end_seconds": end}
            for role, start, end in (
                ("voice_over", 0.5, 8.0),
                ("voice_over", 8.5, 21.5),
                ("dialogue", 22.0, 25.0),
                ("dialogue", 25.5, 27.5),
                ("dialogue", 28.0, 31.5),
                ("voice_over", 32.5, 40.5),
                ("voice_over", 41.0, 48.5),
                ("dialogue", 50.5, 51.5),
                ("dialogue", 54.0, 56.5),
                ("voice_over", 60.0, 70.0),
            )
        ]
        dialogue_speakers = iter(("S2", "S1", "S2", "S2", "S1"))
        for row in speech:
            if row["content_role"] == "dialogue":
                row["speaker"] = next(dialogue_speakers)
        protected = protect_segment_boundaries_from_speech(
            planned, speech, max_segment_seconds=15.0,
            tail_seconds=1.0, grid_seconds=0.5,
        )
        self.assertEqual(
            [row.core_end_seconds for row in protected[:-1]],
            [8.5, 22.0, 32.5, 41.0, 49.5, 60.0],
        )
        for line in speech:
            owners = [
                row for row in protected
                if row.core_start_seconds <= line["start_seconds"] + 1e-6
                and row.core_end_seconds >= line["end_seconds"] - 1e-6
            ]
            self.assertEqual(len(owners), 1, line)
        aligned = align_segments_to_dialogue_turns(
            protected, speech, max_segment_seconds=15.0, grid_seconds=0.5
        )
        self.assertEqual(
            [row.core_end_seconds for row in aligned[:-1]],
            [8.5, 22.0, 25.5, 28.0, 32.5, 41.0, 50.5, 54.0, 60.0],
        )

    def test_packed_native_windows_add_a_safe_segment_instead_of_cutting_speech(self):
        planned = plan_render_segments(0.0, 45.0, overlap_seconds=0.0)
        protected = protect_segment_boundaries_from_speech(
            planned,
            [{
                "content_role": "dialogue",
                "start_seconds": 29.0,
                "end_seconds": 31.0,
            }],
            tail_seconds=1.0,
        )
        self.assertEqual(
            [row.core_end_seconds for row in protected],
            [15.0, 29.0, 44.0, 45.0],
        )
        self.assertTrue(all(row.duration_seconds <= 15.0 for row in protected))
        self.assertTrue(all(
            not (29.0 < row.core_end_seconds < 32.0)
            for row in protected[:-1]
        ))

    def test_dirty_range_only_selects_intersecting_segments(self):
        rows = plan_render_segments(0.0, 60.0)
        self.assertEqual(dirty_segment_indexes(rows, 30.0, 32.0), [2])
        self.assertEqual(dirty_segment_indexes(rows, 14.5, 14.75), [0, 1])

    def test_timed_rows_are_filtered_clamped_and_rebased(self):
        rows = rebase_timed_rows(
            [
                {"name": "before", "start_seconds": 0.0, "end_seconds": 4.0},
                {"name": "crossing", "start_seconds": 13.0, "end_seconds": 18.0},
                {"name": "inside", "start_seconds": 20.0, "end_seconds": 22.0},
            ],
            14.0,
            29.0,
        )
        self.assertEqual(
            [(row["name"], row["start_seconds"], row["end_seconds"]) for row in rows],
            [("crossing", 0.0, 4.0), ("inside", 6.0, 8.0)],
        )

    def test_timed_prompt_text_keeps_only_the_active_story_phase(self):
        scoped = scope_timed_prompt_text(
            "Bright Xinjiang cotton fields (0-16s) transitioning to cool "
            "moonlit Nanyang rubber plantation (16-30s). Realistic cinema.",
            25.0,
            30.0,
            field_name="visual style",
        )
        self.assertNotIn("Xinjiang", scoped)
        self.assertNotIn("cotton", scoped)
        self.assertIn("Nanyang rubber plantation", scoped)
        self.assertIn("segment-local 00:00.000", scoped)
        self.assertIn("00:05.000", scoped)
        self.assertIn("Off-window earlier and later phases were removed", scoped)

    def test_timed_prompt_text_clips_ranges_and_rebases_point_events(self):
        scoped = scope_timed_prompt_text(
            "Fog builds from 00:10 to 00:20. Cut to black at 18s. "
            "The film was restored in 2020-2024.",
            15.0,
            19.0,
            field_name="technical rule",
        )
        self.assertIn("segment-local 00:00.000", scoped)
        self.assertIn("segment-local 00:03.000", scoped)
        self.assertIn("2020-2024", scoped)
        self.assertNotIn("00:10", scoped)
        self.assertNotIn("00:20", scoped)

    def test_timed_prompt_text_drops_an_off_window_point_without_story_keywords(self):
        scoped = scope_timed_prompt_text(
            "Maintain the same hero. Ensure the day-to-night change occurs at 16s.",
            25.0,
            30.0,
            field_name="constraint",
        )
        self.assertIn("Maintain the same hero", scoped)
        self.assertNotIn("day-to-night", scoped)
        self.assertNotIn("16s", scoped)

    def test_cache_reuse_requires_matching_fingerprint(self):
        rows = plan_render_segments(0.0, 30.0)
        rows[0].fingerprint = content_fingerprint({"prompt": "same"})
        rows[1].fingerprint = content_fingerprint({"prompt": "new"})
        cached = [
            {**rows[0].to_dict(), "status": "complete", "output_path": "one.mp4"},
            {**rows[1].to_dict(), "fingerprint": "old", "output_path": "two.mp4"},
        ]
        reused = reuse_cached_segments(rows, cached)
        self.assertEqual(reused[0].status, "cached")
        self.assertEqual(reused[0].output_path, "one.mp4")
        self.assertEqual(reused[1].status, "pending")


if __name__ == "__main__":
    unittest.main()

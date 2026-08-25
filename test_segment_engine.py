import unittest

from segment_engine import (
    content_fingerprint,
    derive_segment_seed,
    derive_named_segment_seed,
    dirty_segment_indexes,
    plan_render_segments,
    plan_shot_render_segments,
    rebase_timed_rows,
    reuse_cached_segments,
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

"""Planning and cache helpers for hidden long-form H3 rendering.

The editor always exposes one continuous timeline.  This module turns a work
area into internal, overlapping ComfyUI jobs only when it is longer than the
native H3 limit.  It deliberately has no Qt or ComfyUI dependencies so the
behaviour can be regression-tested without starting the application.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping


MAX_NATIVE_SECONDS = 15.0
DEFAULT_OVERLAP_SECONDS = 1.0
DEFAULT_MIN_SHOT_SECONDS = 3.0
TIMELINE_GRID_SECONDS = 0.5
MAX_SEED = 2**63 - 1
CONTINUITY_MODES = {"none", "hard_cut", "match_action", "motion_reference", "transition"}


def snap_seconds(value: float, grid: float = TIMELINE_GRID_SECONDS) -> float:
    """Snap seconds to the timeline grid while avoiding floating-point noise."""
    if grid <= 0:
        return round(float(value), 6)
    return round(round(float(value) / grid) * grid, 6)


@dataclass(slots=True)
class RenderSegment:
    """One hidden generation unit within a continuous user-visible work area."""

    segment_id: str
    index: int
    start_seconds: float
    end_seconds: float
    overlap_before_seconds: float = 0.0
    overlap_after_seconds: float = 0.0
    seed: int | None = None
    fingerprint: str = ""
    status: str = "pending"
    output_path: str = ""
    error: str = ""
    core_start_seconds: float | None = None
    core_end_seconds: float | None = None
    shot_ids: list[str] | None = None
    continuity_mode: str = "none"

    @property
    def duration_seconds(self) -> float:
        return round(self.end_seconds - self.start_seconds, 6)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RenderSegment":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value[key] for key in allowed if key in value})


def _segment_id(index: int, start: float, end: float) -> str:
    return f"segment_{index + 1:03d}_{round(start * 1000):09d}_{round(end * 1000):09d}"


def plan_render_segments(
    start_seconds: float,
    end_seconds: float,
    *,
    max_segment_seconds: float = MAX_NATIVE_SECONDS,
    overlap_seconds: float = DEFAULT_OVERLAP_SECONDS,
    grid_seconds: float = TIMELINE_GRID_SECONDS,
) -> list[RenderSegment]:
    """Plan internal overlapping jobs for one continuous work area.

    A work area at or below the native limit is returned unchanged as one
    segment.  This is the compatibility guarantee for existing short projects.
    """
    start = snap_seconds(start_seconds, grid_seconds)
    end = snap_seconds(end_seconds, grid_seconds)
    maximum = snap_seconds(max_segment_seconds, grid_seconds)
    overlap = snap_seconds(overlap_seconds, grid_seconds)
    if end <= start:
        raise ValueError("Work-area end must be later than its start.")
    if maximum <= 0:
        raise ValueError("Maximum segment duration must be positive.")
    if overlap < 0 or overlap >= maximum:
        raise ValueError("Segment overlap must be at least zero and shorter than a segment.")

    if end - start <= maximum + 1e-6:
        return [RenderSegment(_segment_id(0, start, end), 0, start, end)]

    rows: list[RenderSegment] = []
    cursor = start
    while cursor < end - 1e-6:
        segment_end = min(end, snap_seconds(cursor + maximum, grid_seconds))
        index = len(rows)
        rows.append(
            RenderSegment(
                _segment_id(index, cursor, segment_end),
                index,
                cursor,
                segment_end,
                overlap_before_seconds=overlap if index else 0.0,
                continuity_mode="match_action" if index else "none",
            )
        )
        if segment_end >= end - 1e-6:
            break
        next_cursor = snap_seconds(segment_end - overlap, grid_seconds)
        if next_cursor <= cursor:
            raise ValueError("Segment settings do not advance the render cursor.")
        cursor = next_cursor

    for index, row in enumerate(rows[:-1]):
        row.overlap_after_seconds = round(
            max(0.0, row.end_seconds - rows[index + 1].start_seconds), 6
        )
    return rows


def plan_shot_render_segments(
    start_seconds: float,
    end_seconds: float,
    shots: Iterable[Mapping[str, Any]],
    *,
    min_segment_seconds: float = DEFAULT_MIN_SHOT_SECONDS,
    max_segment_seconds: float = MAX_NATIVE_SECONDS,
    overlap_seconds: float = DEFAULT_OVERLAP_SECONDS,
    grid_seconds: float = TIMELINE_GRID_SECONDS,
) -> list[RenderSegment]:
    """Plan stable render units around authored Shot boundaries.

    Very short beats (for example a one-second bullet-time cue) are merged
    forward until the minimum useful generation duration is reached. Gaps are
    covered, long ranges are split, and a leading continuity handle is added
    only when it still keeps the H3 request within the native duration limit.
    """
    start = snap_seconds(start_seconds, grid_seconds)
    end = snap_seconds(end_seconds, grid_seconds)
    minimum = max(grid_seconds, snap_seconds(min_segment_seconds, grid_seconds))
    maximum = snap_seconds(max_segment_seconds, grid_seconds)
    overlap = max(0.0, snap_seconds(overlap_seconds, grid_seconds))
    if end <= start:
        raise ValueError("Work-area end must be later than its start.")
    if maximum <= 0.0 or minimum > maximum:
        raise ValueError("Shot render minimum must be positive and no longer than its maximum.")

    clipped_shots: list[dict[str, Any]] = []
    boundaries = {start, end}
    for source in shots:
        shot_start = max(start, snap_seconds(float(source.get("start_seconds", start)), grid_seconds))
        shot_end = min(end, snap_seconds(float(source.get("end_seconds", shot_start)), grid_seconds))
        if shot_end <= shot_start:
            continue
        clipped_shots.append(
            {
                "cue_id": str(source.get("cue_id", source.get("shot_id", ""))),
                "start_seconds": shot_start,
                "end_seconds": shot_end,
                "continuity_mode": str(source.get("continuity_mode", "auto")),
            }
        )
        boundaries.update((shot_start, shot_end))

    # No internal Shot boundary means the established 15-second planner is
    # still the most efficient and fully backward-compatible choice.
    ordered_boundaries = sorted(boundaries)
    if not clipped_shots or len(ordered_boundaries) <= 2:
        return plan_render_segments(
            start,
            end,
            max_segment_seconds=maximum,
            overlap_seconds=overlap,
            grid_seconds=grid_seconds,
        )

    atoms: list[tuple[float, float]] = []
    for atom_start, atom_end in zip(ordered_boundaries, ordered_boundaries[1:]):
        cursor = atom_start
        while atom_end - cursor > maximum + 1e-6:
            split = snap_seconds(cursor + maximum, grid_seconds)
            atoms.append((cursor, split))
            cursor = split
        if atom_end > cursor + 1e-6:
            atoms.append((cursor, atom_end))

    cores: list[list[float]] = []
    index = 0
    while index < len(atoms):
        core_start, core_end = atoms[index]
        while (
            core_end - core_start < minimum - 1e-6
            and index + 1 < len(atoms)
            and atoms[index + 1][1] - core_start <= maximum + 1e-6
        ):
            index += 1
            core_end = atoms[index][1]
        if (
            core_end - core_start < minimum - 1e-6
            and cores
            and core_end - cores[-1][0] <= maximum + 1e-6
        ):
            cores[-1][1] = core_end
        else:
            cores.append([core_start, core_end])
        index += 1

    result: list[RenderSegment] = []
    for index, (core_start, core_end) in enumerate(cores):
        # Continuity references describe the state immediately before this
        # core. They are not story time, so do not include the prior Shot as a
        # leading generation handle. This prevents H3 from replaying it.
        render_start = core_start
        boundary_shot = next(
            (
                row for row in clipped_shots
                if abs(row["start_seconds"] - core_start) <= 1e-6
            ),
            None,
        )
        requested_mode = str(
            (boundary_shot or {}).get("continuity_mode", "auto")
        ).strip().lower().replace(" ", "_").replace("-", "_")
        continuity_mode = requested_mode if requested_mode in CONTINUITY_MODES else "match_action"
        if continuity_mode == "auto":
            continuity_mode = "match_action"
        if index == 0:
            continuity_mode = "none"
        shot_ids = [
            row["cue_id"]
            for row in clipped_shots
            if row["cue_id"] and ranges_intersect(
                row["start_seconds"], row["end_seconds"], core_start, core_end
            )
        ]
        segment_id = (
            f"shot_{round(core_start * 1000):09d}_{round(core_end * 1000):09d}"
        )
        result.append(
            RenderSegment(
                segment_id=segment_id,
                index=index,
                start_seconds=render_start,
                end_seconds=core_end,
                overlap_before_seconds=round(core_start - render_start, 6),
                core_start_seconds=core_start,
                core_end_seconds=core_end,
                shot_ids=shot_ids,
                continuity_mode=continuity_mode,
            )
        )
    for index, row in enumerate(result[:-1]):
        row.overlap_after_seconds = result[index + 1].overlap_before_seconds
    return result


def derive_segment_seed(master_seed: int, segment_index: int) -> int:
    """Derive stable per-segment seeds so preview acceptance can reuse all seeds."""
    digest = hashlib.sha256(f"h3-smart-render:{int(master_seed)}:{segment_index}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % MAX_SEED


def derive_named_segment_seed(master_seed: int, segment_id: str) -> int:
    """Keep a Shot unit's seed stable when an unrelated earlier Shot changes."""
    digest = hashlib.sha256(
        f"h3-smart-render:{int(master_seed)}:{segment_id}".encode()
    ).digest()
    return int.from_bytes(digest[:8], "big") % MAX_SEED


def ranges_intersect(start_a: float, end_a: float, start_b: float, end_b: float) -> bool:
    """Return true for intervals and zero-duration markers inside a range."""
    if abs(end_a - start_a) <= 1e-9:
        return start_b <= start_a < end_b
    return start_a < end_b and end_a > start_b


def dirty_segment_indexes(
    segments: Iterable[RenderSegment], change_start: float, change_end: float
) -> list[int]:
    """Find only the hidden jobs touched by a timeline edit."""
    if change_end < change_start:
        change_start, change_end = change_end, change_start
    if abs(change_end - change_start) <= 1e-9:
        change_end = change_start
    return [
        segment.index
        for segment in segments
        if ranges_intersect(
            change_start,
            change_end,
            segment.start_seconds,
            segment.end_seconds,
        )
    ]


def rebase_timed_rows(
    rows: Iterable[Mapping[str, Any]],
    window_start: float,
    window_end: float,
    *,
    clamp: bool = True,
) -> list[dict[str, Any]]:
    """Filter timeline dictionaries to a segment and convert times to local time."""
    result: list[dict[str, Any]] = []
    for source in rows:
        row_start = float(source.get("start_seconds", 0.0))
        row_end = float(source.get("end_seconds", row_start))
        if not ranges_intersect(row_start, row_end, window_start, window_end):
            continue
        local = dict(source)
        if clamp:
            row_start = max(window_start, row_start)
            row_end = min(window_end, row_end)
        local["start_seconds"] = round(max(0.0, row_start - window_start), 6)
        local["end_seconds"] = round(max(0.0, row_end - window_start), 6)
        result.append(local)
    return result


def content_fingerprint(value: Any) -> str:
    """Create a stable hash for workflow, prompt, assets, and render parameters."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def reuse_cached_segments(
    planned: Iterable[RenderSegment], cached: Iterable[Mapping[str, Any]]
) -> list[RenderSegment]:
    """Copy completed outputs only when a segment fingerprint still matches."""
    cache_by_id = {str(row.get("segment_id", "")): row for row in cached}
    result: list[RenderSegment] = []
    for segment in planned:
        old = cache_by_id.get(segment.segment_id)
        if old and old.get("fingerprint") == segment.fingerprint and old.get("output_path"):
            segment.output_path = str(old["output_path"])
            segment.status = "cached"
        result.append(segment)
    return result

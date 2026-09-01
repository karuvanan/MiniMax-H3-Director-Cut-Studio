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
import re
from typing import Any, Iterable, Mapping


MAX_NATIVE_SECONDS = 15.0
DEFAULT_OVERLAP_SECONDS = 1.0
DEFAULT_MIN_SHOT_SECONDS = 3.0
TIMELINE_GRID_SECONDS = 0.5
MAX_SEED = 2**63 - 1
CONTINUITY_MODES = {"none", "hard_cut", "match_action", "motion_reference", "transition"}


_TIME_TOKEN = r"(?:\d{1,2}:\d{2}(?::\d{2})?(?:\.\d{1,3})?|\d+(?:\.\d+)?)"
_TIMED_TEXT_RANGE_RE = re.compile(
    rf"""
    (?P<open>[\[(]?)\s*
    (?:(?:from|between)\s+)?
    (?P<start>{_TIME_TOKEN})\s*
    (?P<start_unit>hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s|\u79d2)?\s*
    (?:-|\u2013|\u2014|to|through|until|and|\u81f3|\u5230)\s*
    (?P<end>{_TIME_TOKEN})\s*
    (?P<end_unit>hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s|\u79d2)?\s*
    (?P<close>[\]\)]?)
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)
_TIMED_TEXT_POINT_RE = re.compile(
    rf"""
    (?:(?:\bat\s+|@\s*)
       (?P<time>{_TIME_TOKEN})\s*
       (?P<unit>hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s|\u79d2)
      |
       (?P<time_cn>{_TIME_TOKEN})\s*(?P<unit_cn>\u79d2)(?:\u65f6|\u6642|\u5904|\u8655)?
    )
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)
_LEADING_PHASE_CONNECTOR_RE = re.compile(
    r"^\s*(?:(?:and\s+)?(?:then|afterwards|subsequently)|"
    r"(?:and\s+)?transition(?:s|ed|ing)?\s+to|"
    r"(?:and\s+)?shift(?:s|ed|ing)?\s+to|followed\s+by|"
    r"while|whereas|\u7136\u540e|\u7136\u5f8c|\u968f\u540e|\u96a8\u5f8c|\u4e4b\u540e|\u4e4b\u5f8c|\u8f6c\u4e3a|\u8f49\u70ba)\b\s*[:,\uff1a]?\s*",
    flags=re.IGNORECASE,
)


def _time_token_seconds(token: str, unit: str = "") -> float:
    """Parse common H3 prompt time tokens into seconds."""
    value = token.strip()
    if ":" in value:
        parts = [float(part) for part in value.split(":")]
        if len(parts) == 2:
            return parts[0] * 60.0 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600.0 + parts[1] * 60.0 + parts[2]
        raise ValueError(f"Unsupported time token: {token}")
    seconds = float(value)
    normalized_unit = unit.strip().lower()
    if normalized_unit in {"h", "hr", "hrs", "hour", "hours"}:
        seconds *= 3600.0
    elif normalized_unit in {"m", "min", "mins", "minute", "minutes"}:
        seconds *= 60.0
    return seconds


def _is_prompt_time_range(match: re.Match[str]) -> bool:
    """Reject bare year/number ranges while accepting normal timeline notation."""
    raw = match.group(0)
    return bool(
        match.group("start_unit")
        or match.group("end_unit")
        or ":" in match.group("start")
        or ":" in match.group("end")
        or match.group("open")
        or match.group("close")
        or "\u79d2" in raw
    )


def _segment_local_timecode(seconds: float) -> str:
    value = max(0.0, float(seconds))
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    remainder = value % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{remainder:06.3f}"
    return f"{minutes:02d}:{remainder:06.3f}"


def scope_timed_prompt_text(
    text: str,
    window_start: float,
    window_end: float,
    *,
    field_name: str = "direction",
) -> str:
    """Filter project-global timed prose and rebase it to one render segment.

    Design presets often mix chronology into otherwise global fields, for
    example ``daylight cotton fields (0-16s) transitioning to a night rubber
    plantation (16-30s)``. Hidden H3 jobs use local timestamps, so passing that
    sentence unchanged makes a 25-30s job look like a new 0-5s cotton-field
    clip. This helper removes off-window phases, clips intersecting phases and
    emits one authoritative segment-local schedule without knowing anything
    about the story, language, location or media IDs.
    """
    source = str(text or "").strip()
    if not source or window_end <= window_start:
        return source

    sentences = [
        row.strip()
        for row in re.split(r"[\r\n]+|(?<=[.!?;\u3002\uff01\uff1f\uff1b])", source)
        if row.strip()
    ]
    output: list[str] = []
    found_schedule = False
    retained_schedule = False
    for sentence in sentences:
        matches = [
            match for match in _TIMED_TEXT_RANGE_RE.finditer(sentence)
            if _is_prompt_time_range(match)
        ]
        point_matches = [] if matches else list(_TIMED_TEXT_POINT_RE.finditer(sentence))
        if not matches and not point_matches:
            output.append(sentence)
            continue

        found_schedule = True
        cursor = 0
        retained_chunks: list[str] = []
        last_match_retained = False
        for match in matches:
            chunk = sentence[cursor:match.end()]
            cursor = match.end()
            start_unit = match.group("start_unit") or match.group("end_unit") or ""
            end_unit = match.group("end_unit") or match.group("start_unit") or ""
            range_start = _time_token_seconds(match.group("start"), start_unit)
            range_end = _time_token_seconds(match.group("end"), end_unit)
            if range_end < range_start:
                range_start, range_end = range_end, range_start
            if not ranges_intersect(
                range_start, range_end, float(window_start), float(window_end)
            ):
                last_match_retained = False
                continue
            local_start = max(range_start, window_start) - window_start
            local_end = min(range_end, window_end) - window_start
            local_range = (
                "[segment-local "
                + _segment_local_timecode(local_start)
                + "\u2013"
                + _segment_local_timecode(local_end)
                + "]"
            )
            relative_start = match.start() - (match.end() - len(chunk))
            relative_end = relative_start + len(match.group(0))
            chunk = chunk[:relative_start] + local_range + chunk[relative_end:]
            chunk = _LEADING_PHASE_CONNECTOR_RE.sub("", chunk).strip()
            if chunk:
                retained_chunks.append(chunk)
                retained_schedule = True
                last_match_retained = True
        for match in point_matches:
            chunk = sentence[cursor:match.end()]
            cursor = match.end()
            token = match.group("time") or match.group("time_cn") or "0"
            unit = match.group("unit") or match.group("unit_cn") or ""
            point = _time_token_seconds(token, unit)
            if point < window_start - 1e-6 or point > window_end + 1e-6:
                last_match_retained = False
                continue
            local_point = min(window_end - window_start, max(0.0, point - window_start))
            local_tag = "at [segment-local " + _segment_local_timecode(local_point) + "]"
            relative_start = match.start() - (match.end() - len(chunk))
            relative_end = relative_start + len(match.group(0))
            chunk = chunk[:relative_start] + local_tag + chunk[relative_end:]
            chunk = _LEADING_PHASE_CONNECTOR_RE.sub("", chunk).strip()
            if chunk:
                retained_chunks.append(chunk)
                retained_schedule = True
                last_match_retained = True
        if retained_chunks and last_match_retained:
            retained_chunks[-1] = (retained_chunks[-1] + sentence[cursor:]).strip()
        if retained_chunks:
            output.extend(retained_chunks)

    scoped = " ".join(row for row in output if row).strip()
    if not found_schedule:
        return scoped
    duration = window_end - window_start
    authority = (
        f"SEGMENT-LOCAL {field_name.upper()} SCHEDULE (authoritative, "
        f"00:00.000\u2013{_segment_local_timecode(duration)}): "
    )
    if retained_schedule:
        return (
            authority
            + scoped
            + " The retained timed phase overrides every untimed modifier in this field; apply "
              "an untimed modifier only when it is compatible with that active phase."
            + " Off-window earlier and later phases were removed; do not depict, replay, "
              "foreshadow or blend any omitted phase into this segment."
        ).strip()
    if scoped:
        return (
            authority
            + scoped
            + " No time-scoped phase from this field is active in this segment; do not infer "
              "one from an earlier or later phase."
        ).strip()
    return ""


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
        if clipped_shots and not shot_ids:
            raise ValueError(
                f"Shot-less render Segment {core_start:.2f}-{core_end:.2f}s. "
                "Repair the Director Shot lane so it covers the complete Timeline."
            )
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


def protect_segment_boundaries_from_speech(
    segments: Iterable[RenderSegment],
    speech_rows: Iterable[Mapping[str, Any]],
    *,
    max_segment_seconds: float = MAX_NATIVE_SECONDS,
    tail_seconds: float = 1.0,
    grid_seconds: float = TIMELINE_GRID_SECONDS,
) -> list[RenderSegment]:
    """Move internal render cuts away from authored speech and its decay tail.

    Native H3 speech cannot continue one utterance across two independently
    generated requests.  This keeps a complete Dialogue/Voice-over/Lyrics row
    on one side of every feasible boundary and reserves a short ambience/room
    decay tail before the edit.  Timeline coverage remains continuous and no
    Segment is allowed to exceed H3's native duration.
    """

    rows = [RenderSegment.from_dict(row.to_dict()) for row in segments]
    if len(rows) < 2:
        return rows
    maximum = max(grid_seconds, snap_seconds(max_segment_seconds, grid_seconds))
    tail = max(0.0, snap_seconds(tail_seconds, grid_seconds))
    speech = sorted(
        (
            snap_seconds(float(item.get("start_seconds", 0.0)), grid_seconds),
            snap_seconds(
                float(item.get("end_seconds", item.get("start_seconds", 0.0))),
                grid_seconds,
            ),
        )
        for item in speech_rows
        if str(item.get("content_role", item.get("role", "")))
        in {"dialogue", "voice_over", "lyrics"}
    )
    speech = [(start, end) for start, end in speech if end > start + 1e-6]
    if not speech:
        return rows

    boundaries = [
        float(rows[0].core_start_seconds if rows[0].core_start_seconds is not None else rows[0].start_seconds)
    ]
    boundaries.extend(
        float(row.core_end_seconds if row.core_end_seconds is not None else row.end_seconds)
        for row in rows
    )
    moved: set[int] = set()
    for index in range(1, len(boundaries) - 1):
        boundary = boundaries[index]
        hard_blockers = [
            (start, end)
            for start, end in speech
            if start < boundary - 1e-6 and boundary < end - 1e-6
        ]
        tail_blockers = [
            (start, end)
            for start, end in speech
            if start < boundary - 1e-6
            and end - 1e-6 <= boundary < end + tail - 1e-6
        ]
        # A decay-tail preference must never move an already speech-safe cut
        # across the beginning of the next authored line.  Doing that put the
        # next line into the preceding H3 request and removed it from its own
        # request because Text Ranges are owned by their start time.
        if not hard_blockers and tail_blockers:
            preferred = snap_seconds(
                max(end + tail for _start, end in tail_blockers), grid_seconds
            )
            if any(
                start >= boundary - 1e-6
                and start < preferred - 1e-6
                and end > boundary + 1e-6
                for start, end in speech
            ):
                continue
        blockers = hard_blockers or tail_blockers
        if not blockers:
            continue
        lower = max(
            boundaries[index - 1] + grid_seconds,
            boundaries[index + 1] - maximum,
        )
        upper = min(
            boundaries[index + 1] - grid_seconds,
            boundaries[index - 1] + maximum,
        )
        forward = snap_seconds(max(end + tail for _start, end in blockers), grid_seconds)
        backward = snap_seconds(min(start for start, _end in blockers), grid_seconds)
        forward_crosses_new_speech = any(
            start >= boundary - 1e-6
            and start < forward - 1e-6
            and (start, end) not in blockers
            for start, end in speech
        )
        candidate = None
        if (
            not forward_crosses_new_speech
            and lower - 1e-6 <= forward <= upper + 1e-6
        ):
            candidate = forward
        elif lower - 1e-6 <= backward <= upper + 1e-6:
            candidate = backward
        elif (
            boundaries[index - 1] + grid_seconds - 1e-6
            <= backward
            <= boundaries[index - 1] + maximum + 1e-6
            and backward < boundaries[index + 1] - 1e-6
        ):
            # Moving backward keeps the current native request valid but may
            # make the following interval longer than 15 seconds. The rebuild
            # pass below inserts a new safe boundary into that following span.
            candidate = backward
        if candidate is None or abs(candidate - boundary) <= 1e-6:
            continue
        boundaries[index] = candidate
        moved.add(index)

    # A completely packed sequence (for example 0-15, 15-30, 30-45)
    # cannot always move one boundary without making its neighbour longer than
    # H3's native limit. In that case keep the safe earlier cut and insert an
    # additional native window later. This is preferable to splitting one
    # authored utterance across two independent H3 requests.
    safe_boundaries = [boundaries[0]]
    for target in boundaries[1:]:
        cursor = safe_boundaries[-1]
        while target - cursor > maximum + 1e-6:
            candidate = snap_seconds(cursor + maximum, grid_seconds)
            blockers = [
                (start, end)
                for start, end in speech
                if start < candidate - 1e-6 and candidate < end + tail - 1e-6
            ]
            if blockers:
                backward = snap_seconds(min(start for start, _end in blockers), grid_seconds)
                forward = snap_seconds(max(end + tail for _start, end in blockers), grid_seconds)
                if backward > cursor + 1e-6:
                    candidate = backward
                elif forward <= cursor + maximum + 1e-6:
                    candidate = forward
                else:
                    # One authored line itself exceeds a native H3 window. The
                    # Text Layer is still compiled into every intersecting
                    # window; UI timing validation is responsible for asking
                    # the editor to split such an exceptional line.
                    candidate = snap_seconds(cursor + maximum, grid_seconds)
            if candidate <= cursor + 1e-6:
                candidate = snap_seconds(cursor + maximum, grid_seconds)
            safe_boundaries.append(candidate)
            cursor = candidate
        if target > safe_boundaries[-1] + 1e-6:
            safe_boundaries.append(target)
    boundaries = safe_boundaries

    source_rows = rows
    rebuilt: list[RenderSegment] = []
    original_starts = {
        snap_seconds(
            float(row.core_start_seconds if row.core_start_seconds is not None else row.start_seconds),
            grid_seconds,
        ): row
        for row in source_rows
    }
    for index in range(len(boundaries) - 1):
        core_start = snap_seconds(boundaries[index], grid_seconds)
        core_end = snap_seconds(boundaries[index + 1], grid_seconds)
        template = original_starts.get(core_start)
        if template is None:
            template = next(
                (
                    row for row in source_rows
                    if ranges_intersect(
                        float(row.core_start_seconds if row.core_start_seconds is not None else row.start_seconds),
                        float(row.core_end_seconds if row.core_end_seconds is not None else row.end_seconds),
                        core_start,
                        core_end,
                    )
                ),
                source_rows[-1],
            )
        row = RenderSegment.from_dict(template.to_dict())
        row.index = index
        row.start_seconds = core_start
        row.end_seconds = core_end
        row.core_start_seconds = core_start
        row.core_end_seconds = core_end
        row.overlap_before_seconds = 0.0
        row.overlap_after_seconds = 0.0
        row.segment_id = (
            f"shot_{round(core_start * 1000):09d}_{round(core_end * 1000):09d}"
        )
        if index and (index in moved or core_start not in original_starts):
            row.continuity_mode = "motion_reference"
        elif index == 0:
            row.continuity_mode = "none"
        rebuilt.append(row)
    return rebuilt


def align_segments_to_dialogue_turns(
    segments: Iterable[RenderSegment],
    speech_rows: Iterable[Mapping[str, Any]],
    *,
    max_segment_seconds: float = MAX_NATIVE_SECONDS,
    grid_seconds: float = TIMELINE_GRID_SECONDS,
) -> list[RenderSegment]:
    """Give alternating on-camera speakers separate H3 request boundaries.

    H3 native dialogue may compress multiple timed turns toward the beginning
    of one request and animate the listener's mouth.  A dialogue turn that
    starts a request has an unambiguous local zero and speaker identity.  This
    pass moves a nearby silent boundary to the first turn when safe, then
    inserts boundaries at later speaker changes without cutting any line.
    """
    rows = [RenderSegment.from_dict(row.to_dict()) for row in segments]
    if not rows:
        return rows
    speech = sorted(
        (
            snap_seconds(float(item.get("start_seconds", 0.0)), grid_seconds),
            snap_seconds(
                float(item.get("end_seconds", item.get("start_seconds", 0.0))),
                grid_seconds,
            ),
            str(item.get("content_role", item.get("role", ""))),
            str(item.get("speaker", "S1")),
        )
        for item in speech_rows
        if str(item.get("content_role", item.get("role", "")))
        in {"dialogue", "voice_over", "lyrics"}
    )
    dialogue = [row for row in speech if row[2] == "dialogue" and row[1] > row[0]]
    if not dialogue:
        return rows

    boundaries = [float(rows[0].core_start_seconds or rows[0].start_seconds)]
    boundaries.extend(
        float(row.core_end_seconds if row.core_end_seconds is not None else row.end_seconds)
        for row in rows
    )
    maximum = max(grid_seconds, snap_seconds(max_segment_seconds, grid_seconds))

    # Move an internal boundary forward through genuine silence so the first
    # on-camera line starts at local 0.00s. Never exceed H3's native duration.
    for index in range(1, len(boundaries) - 1):
        start, end = boundaries[index], boundaries[index + 1]
        turns = [row for row in dialogue if start < row[0] < end - 1e-6]
        if not turns:
            continue
        first = turns[0][0]
        has_prior_speech = any(
            speech_start < first - 1e-6 and speech_end > start + 1e-6
            for speech_start, speech_end, _role, _speaker in speech
        )
        if (
            not has_prior_speech
            and first - boundaries[index - 1] <= maximum + 1e-6
        ):
            boundaries[index] = first

    # A later change of speaking face receives its own request. Same-speaker
    # continuation can stay together unless a long authored silence separates it.
    inserts: set[float] = set()
    for start, end in zip(boundaries, boundaries[1:]):
        turns = [row for row in dialogue if start - 1e-6 <= row[0] < end - 1e-6]
        for previous, current in zip(turns, turns[1:]):
            silent_gap = current[0] - previous[1]
            if current[3] != previous[3] or silent_gap >= 1.5 - 1e-6:
                if current[0] - start >= grid_seconds - 1e-6:
                    inserts.add(current[0])
    boundaries = sorted(set(boundaries).union(inserts))

    rebuilt: list[RenderSegment] = []
    original_starts = {
        snap_seconds(
            float(row.core_start_seconds if row.core_start_seconds is not None else row.start_seconds),
            grid_seconds,
        ): row
        for row in rows
    }
    for index, (core_start, core_end) in enumerate(zip(boundaries, boundaries[1:])):
        template = next(
            (
                row for row in rows
                if ranges_intersect(
                    float(row.core_start_seconds if row.core_start_seconds is not None else row.start_seconds),
                    float(row.core_end_seconds if row.core_end_seconds is not None else row.end_seconds),
                    core_start,
                    core_end,
                )
            ),
            rows[-1],
        )
        row = RenderSegment.from_dict(template.to_dict())
        row.index = index
        row.start_seconds = row.core_start_seconds = core_start
        row.end_seconds = row.core_end_seconds = core_end
        row.overlap_before_seconds = row.overlap_after_seconds = 0.0
        row.segment_id = f"shot_{round(core_start * 1000):09d}_{round(core_end * 1000):09d}"
        if index == 0:
            row.continuity_mode = "none"
        elif core_start in original_starts:
            row.continuity_mode = original_starts[core_start].continuity_mode
        else:
            row.continuity_mode = "motion_reference"
        rebuilt.append(row)
    return rebuilt


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

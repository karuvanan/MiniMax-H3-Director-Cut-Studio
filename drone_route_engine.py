"""Deterministic red-route extraction for the drone Special Skills.

P2 is editor control data, not a visual generation reference.  This module
turns its red stroke into a compact ordered path that can be translated into
camera language before H3 compilation.  It deliberately has no dependency on
OpenCV so the route contract behaves the same in the Studio and test runtime.
"""

from __future__ import annotations

from collections import deque
import math
from pathlib import Path


def _thin(binary):
    """Return a one-pixel Zhang-Suen skeleton for a uint8/boolean mask."""

    import numpy as np

    image = binary.astype(np.uint8).copy()
    for _iteration in range(96):
        changed = False
        for phase in (0, 1):
            padded = np.pad(image, 1)
            p2 = padded[:-2, 1:-1]
            p3 = padded[:-2, 2:]
            p4 = padded[1:-1, 2:]
            p5 = padded[2:, 2:]
            p6 = padded[2:, 1:-1]
            p7 = padded[2:, :-2]
            p8 = padded[1:-1, :-2]
            p9 = padded[:-2, :-2]
            neighbours = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            transitions = (
                ((p2 == 0) & (p3 == 1)).astype(np.uint8)
                + ((p3 == 0) & (p4 == 1)).astype(np.uint8)
                + ((p4 == 0) & (p5 == 1)).astype(np.uint8)
                + ((p5 == 0) & (p6 == 1)).astype(np.uint8)
                + ((p6 == 0) & (p7 == 1)).astype(np.uint8)
                + ((p7 == 0) & (p8 == 1)).astype(np.uint8)
                + ((p8 == 0) & (p9 == 1)).astype(np.uint8)
                + ((p9 == 0) & (p2 == 1)).astype(np.uint8)
            )
            if phase == 0:
                side_a = p2 * p4 * p6
                side_b = p4 * p6 * p8
            else:
                side_a = p2 * p4 * p8
                side_b = p2 * p6 * p8
            remove = (
                (image == 1)
                & (neighbours >= 2)
                & (neighbours <= 6)
                & (transitions == 1)
                & (side_a == 0)
                & (side_b == 0)
            )
            if bool(remove.any()):
                image[remove] = 0
                changed = True
        if not changed:
            break
    return image.astype(bool)


def _largest_component(mask):
    import numpy as np

    height, width = mask.shape
    seen = np.zeros(mask.shape, dtype=bool)
    largest: list[tuple[int, int]] = []
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        queue = [(int(y), int(x))]
        seen[y, x] = True
        component: list[tuple[int, int]] = []
        while queue:
            cy, cx = queue.pop()
            component.append((cy, cx))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if not (dx or dy):
                        continue
                    ny, nx = cy + dy, cx + dx
                    if (
                        0 <= ny < height and 0 <= nx < width
                        and mask[ny, nx] and not seen[ny, nx]
                    ):
                        seen[ny, nx] = True
                        queue.append((ny, nx))
        if len(component) > len(largest):
            largest = component
    result = np.zeros(mask.shape, dtype=bool)
    if largest:
        ys, xs = zip(*largest)
        result[list(ys), list(xs)] = True
    return result


def _neighbours(node: tuple[int, int], nodes: set[tuple[int, int]]):
    y, x = node
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            candidate = (y + dy, x + dx)
            if (dx or dy) and candidate in nodes:
                yield candidate


def _farthest(
    start: tuple[int, int], nodes: set[tuple[int, int]]
) -> tuple[tuple[int, int], dict[tuple[int, int], tuple[int, int] | None]]:
    queue = deque([start])
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    distance = {start: 0}
    farthest = start
    while queue:
        node = queue.popleft()
        if distance[node] > distance[farthest]:
            farthest = node
        for candidate in _neighbours(node, nodes):
            if candidate in parent:
                continue
            parent[candidate] = node
            distance[candidate] = distance[node] + 1
            queue.append(candidate)
    return farthest, parent


def _sample_path(
    path: list[tuple[int, int]], count: int
) -> list[tuple[int, int]]:
    if len(path) <= count:
        return path
    # Keep the largest bends first; uniform index sampling silently cut corners.
    indices = [0, len(path) - 1]
    while len(indices) < count:
        candidates = []
        for start, end in zip(indices, indices[1:]):
            ay, ax = path[start]
            by, bx = path[end]
            length = max(1.0, math.hypot(by - ay, bx - ax))
            for index in range(start + 1, end):
                y, x = path[index]
                distance = abs((bx-ax)*(y-ay) - (by-ay)*(x-ax)) / length
                candidates.append((distance, index))
        if not candidates:
            break
        distance, index = max(candidates)
        if distance < 2.0:
            break
        indices.append(index)
        indices.sort()
    return [path[index] for index in indices]


def _direction(dx: float, dy: float) -> str:
    horizontal = ""
    vertical = ""
    if dx > 0.07:
        horizontal = "veer right"
    elif dx < -0.07:
        horizontal = "veer left"
    if dy < -0.07:
        vertical = "advance deeper into the established scene"
    elif dy > 0.07:
        vertical = "continue forward while sweeping toward the near side of the established scene"
    parts = [part for part in (vertical, horizontal) if part]
    return " while ".join(parts) if parts else "continue forward on a level heading"


def analyse_red_route(path: str | Path, waypoint_count: int = 7) -> dict:
    """Extract ordered normalized waypoints from the largest red stroke in P2.

    Green/blue dots close to the endpoints verify start/end direction. Legacy
    unmarked strokes may be inspected but are explicitly unverified; consumers
    must not render inferred travel from them. Closed or branched shapes need
    user review instead of centroid sorting or a made-up default circle.
    """

    import numpy as np
    from PIL import Image

    source = Path(path)
    if not source.is_file():
        return {"detected": False, "reason": "P2 local file is unavailable"}
    try:
        with Image.open(source) as opened:
            image = opened.convert("RGB")
            image.thumbnail((640, 640))
            rgb = np.asarray(image, dtype=np.int16)
    except (OSError, ValueError):
        return {"detected": False, "reason": "P2 is not a readable image"}
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mask = (red >= 135) & (red >= green + 38) & (red >= blue + 38)
    if int(mask.sum()) < 18:
        return {"detected": False, "reason": "no continuous red route was detected"}
    component = _largest_component(mask)
    if int(component.sum()) < 18:
        return {"detected": False, "reason": "red route component is too small"}
    if int(component.sum()) < int(mask.sum()) * 0.9:
        return {"detected": False, "reason":
                "Multiple disconnected red strokes detected; use one continuous route."}
    skeleton = _thin(component)
    nodes = {(int(y), int(x)) for y, x in zip(*np.nonzero(skeleton))}
    if len(nodes) < 4:
        return {"detected": False, "reason": "red route could not be skeletonized"}

    endpoints = [node for node in nodes if len(list(_neighbours(node, nodes))) <= 1]
    closed_loop = len(endpoints) == 0
    if closed_loop:
        return {"detected": False, "closed_loop": True, "reason":
                "Closed route has ambiguous start/direction. Leave a small gap and mark green start / blue end."}
    else:
        if len(endpoints) != 2:
            return {"detected": False, "reason":
                    "Route branches or arrowheads are ambiguous. Use one unbranched red stroke and separate green/blue endpoint dots."}
        seed = endpoints[0] if endpoints else next(iter(nodes))
        end_a, _ = _farthest(seed, nodes)
        end_b, parent = _farthest(end_a, nodes)
        ordered = []
        cursor: tuple[int, int] | None = end_b
        while cursor is not None:
            ordered.append(cursor)
            cursor = parent.get(cursor)
        ordered.reverse()

        if len(ordered) < len(nodes) * 0.9:
            return {"detected": False, "reason":
                    "Route contains crossings, loops or branches; draw one simple open stroke."}

        radius = max(4, round(max(component.shape) * 0.025))
        def density(node: tuple[int, int]) -> int:
            y, x = node
            return int(component[max(0, y-radius):y+radius+1, max(0, x-radius):x+radius+1].sum())
        first_density, last_density = density(ordered[0]), density(ordered[-1])
        if last_density + max(4, int(first_density * 0.12)) < first_density:
            ordered.reverse()
        elif abs(first_density - last_density) <= max(4, int(max(first_density, last_density) * 0.12)):
            # Deterministic fallback for a line with no visible arrow head.
            first_key = (-ordered[0][0], ordered[0][1])
            last_key = (-ordered[-1][0], ordered[-1][1])
            if last_key < first_key:
                ordered.reverse()

    def marker(channel):
        other = [i for i in range(3) if i != channel]
        colour_mask = ((rgb[..., channel] >= 160)
                       & (rgb[..., channel] >= rgb[..., other[0]] + 75)
                       & (rgb[..., channel] >= rgb[..., other[1]] + 75))
        if int(colour_mask.sum()) < 5:
            return None
        yy, xx = np.nonzero(_largest_component(colour_mask))
        return (float(yy.mean()), float(xx.mean()))

    start_marker, end_marker = marker(1), marker(2)
    verified = False
    if start_marker is not None and end_marker is not None:
        def distance(a, b):
            return math.hypot(a[0]-b[0], a[1]-b[1])
        direct = distance(start_marker, ordered[0]) + distance(end_marker, ordered[-1])
        reverse = distance(start_marker, ordered[-1]) + distance(end_marker, ordered[0])
        if reverse < direct:
            ordered.reverse()
        tolerance = max(component.shape) * 0.08
        verified = (distance(start_marker, ordered[0]) <= tolerance
                    and distance(end_marker, ordered[-1]) <= tolerance)

    sampled = _sample_path(ordered, max(3, min(9, int(waypoint_count))))
    height, width = component.shape
    points = [
        {
            "x": round(x / max(1, width - 1), 4),
            "y": round(y / max(1, height - 1), 4),
        }
        for y, x in sampled
    ]
    legs = [
        _direction(points[index + 1]["x"] - point["x"], points[index + 1]["y"] - point["y"])
        for index, point in enumerate(points[:-1])
    ]
    return {
        "detected": True,
        "direction_verified": verified,
        "closed_loop": bool(closed_loop),
        "waypoints": points,
        "camera_legs": legs,
        "red_pixel_count": int(component.sum()),
        "source_size": {"width": int(width), "height": int(height)},
        "direction_basis": ("green start / blue end" if verified else
                            "Unverified direction: add green start / blue end dots near the red endpoints"),
    }


def route_stage_language(analysis: dict, stage_count: int = 7) -> list[str]:
    """Return route-following camera clauses distributed over stage_count."""
    return [route_span_language(analysis, index / stage_count, (index + 1) / stage_count)
            for index in range(stage_count)]


def route_span_language(analysis: dict, start: float, end: float) -> str:
    """Describe ALL overlapping legs, not just the Shot midpoint's leg.

    Fractions refer to progress through the motion interval, not to altitude.
    """
    if not analysis.get("direction_verified"):
        return "Hold the established camera position with a stable horizon."
    points = analysis.get("waypoints") or []
    legs = analysis.get("camera_legs") or []
    lengths = [math.hypot(b['x']-a['x'], b['y']-a['y']) for a,b in zip(points, points[1:])]
    total = sum(lengths) or 1.0
    cursor = 0.0
    clauses = []
    for leg, length in zip(legs, lengths):
        finish = cursor + length / total
        if finish > start and cursor < end:
            lo = max(start, cursor)
            hi = min(end, finish)
            clauses.append(f"During {100*(lo-start)/max(end-start, 1e-6):.0f}–"
                           f"{100*(hi-start)/max(end-start, 1e-6):.0f}% of this Shot, {leg}")
        cursor = finish
    return "; then ".join(clauses) + ". Maintain level altitude, continuous translation and gentle heading changes."

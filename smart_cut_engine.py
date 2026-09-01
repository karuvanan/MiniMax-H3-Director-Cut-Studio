"""Deterministic, constraint-aware Storyboard compression planning.

The engine never edits a Timeline.  It produces an inspectable plan that the
Studio may preview, modify and apply as one undoable workspace operation.  LM
output is accepted only as a bounded semantic hint; timing, protection and
dependency decisions remain deterministic.
"""

from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Iterable, Mapping


GRID_SECONDS = 0.5
SMART_CUT_MODES = {"safe", "balanced", "aggressive"}
PROTECTED_ROLE_WORDS = {
    "hook": ("hook", "opening", "开场", "钩子"),
    "clue": ("clue", "evidence", "proof", "线索", "证据", "伏笔"),
    "reveal": ("reveal", "reversal", "twist", "反转", "揭露", "真相"),
    "climax": ("climax", "confrontation", "决战", "高潮", "对决"),
    "final_hook": ("final", "ending", "final hold", "结尾", "终局", "悬念"),
}
LOW_VALUE_WORDS = (
    "optional", "flourish", "establishing", "b-roll", "reaction", "pause",
    "hold", "过场", "装饰", "空镜", "反应", "停顿", "环境建立",
)


def snap_seconds(value: float, grid: float = GRID_SECONDS) -> float:
    if grid <= 0:
        return round(float(value), 6)
    return round(round(float(value) / grid) * grid, 6)


def _ceil_grid(value: float, grid: float) -> float:
    if value <= 0:
        return 0.0
    return round(math.ceil((float(value) - 1e-9) / grid) * grid, 6)


def _tokens(value: object) -> set[str]:
    text = str(value or "").casefold()
    return set(re.findall(r"[a-z0-9]+|[\u3400-\u9fff]", text))


def _combined_text(row: Mapping[str, object]) -> str:
    return " ".join(
        str(row.get(key, "") or "")
        for key in (
            "preset", "detail", "subject_action", "environment_response",
            "continuity_state", "optional_flourish", "h3_optional_flourish",
        )
    ).strip()


def estimate_action_count(value: object) -> int:
    """Estimate physical action density without trusting a language model."""
    text = str(value or "").strip()
    if not text:
        return 0
    chunks = [
        item.strip()
        for item in re.split(
            r"(?:[.!?;。！？；]|\bthen\b|\bwhile\b|\band then\b|随后|然后|同时|接着)",
            text,
            flags=re.I,
        )
        if item.strip()
    ]
    return max(1, len(chunks))


def _story_role(row: Mapping[str, object], hint: Mapping[str, object]) -> str:
    text = _combined_text(row).casefold()
    # Deterministic evidence is the safety floor.  An LM may add semantics,
    # but cannot demote an explicit hook/clue/reveal/climax/final hook into an
    # optional beat and thereby make critical story information removable.
    for role, words in PROTECTED_ROLE_WORDS.items():
        if any(word in text for word in words):
            return role
    hinted = str(hint.get("story_role", "")).strip().lower()
    if hinted in {"hook", "clue", "reveal", "climax", "final_hook", "bridge", "optional"}:
        return hinted
    if any(word in text for word in LOW_VALUE_WORDS):
        return "optional"
    return "bridge"


def build_dependency_graph(shots: Iterable[Mapping[str, object]]) -> list[dict]:
    """Build inspectable adjacent continuity/media dependency edges."""
    rows = [dict(row) for row in shots]
    edges: list[dict] = []
    for left, right in zip(rows, rows[1:]):
        reasons: list[str] = []
        strength = 0
        left_state = str(left.get("continuity_state", "") or "").strip()
        right_text = _combined_text(right)
        overlap = _tokens(left_state).intersection(_tokens(right_text))
        if left_state:
            strength += 2
            reasons.append("outgoing continuity state")
        if overlap:
            strength += min(3, len(overlap))
            reasons.append("shared state tokens: " + ", ".join(sorted(overlap)[:5]))
        left_media = {str(value) for value in (left.get("media_ids") or []) if str(value)}
        right_media = {str(value) for value in (right.get("media_ids") or []) if str(value)}
        shared_media = sorted(left_media.intersection(right_media))
        if shared_media:
            strength += 2
            reasons.append("shared references: " + ", ".join(shared_media[:5]))
        if str(left.get("track_id", "")) and left.get("track_id") == right.get("track_id"):
            strength += 1
            reasons.append("same visual track")
        edges.append({
            "from": str(left.get("cue_id", "")),
            "to": str(right.get("cue_id", "")),
            "strength": min(10, strength),
            "reasons": reasons or ["adjacent story order"],
        })
    return edges


def _normalize_shot(
    source: Mapping[str, object],
    index: int,
    *,
    grid: float,
    hint: Mapping[str, object],
) -> dict:
    row = deepcopy(dict(source))
    start = float(row.get("start_seconds", 0.0) or 0.0)
    end = float(row.get("end_seconds", start + grid) or start + grid)
    duration = max(grid, snap_seconds(end - start, grid))
    row["cue_id"] = str(row.get("cue_id") or row.get("shot_id") or f"S{index + 1}")
    row["start_seconds"] = start
    row["end_seconds"] = end
    row["original_duration"] = duration
    row["speech_duration"] = max(0.0, float(row.get("speech_duration", 0.0) or 0.0))
    row["speech_count"] = max(0, int(row.get("speech_count", 0) or 0))
    row["explicit_speech"] = bool(row.get("explicit_speech", row["speech_count"] > 0))
    row["locked"] = bool(row.get("locked", False))
    row["story_role"] = _story_role(row, hint)
    row["lm_reason"] = str(hint.get("reason", "") or "").strip()
    row["lm_importance_delta"] = max(
        -15.0,
        min(15.0, float(hint.get("importance_delta", 0.0) or 0.0)),
    )
    row["lm_protect"] = bool(hint.get("protect", False))
    row["redundancy_with"] = str(hint.get("redundancy_with", "") or "")
    return row


def _importance(row: Mapping[str, object], index: int, count: int) -> float:
    role = str(row.get("story_role", "bridge"))
    role_score = {
        "hook": 88,
        "clue": 82,
        "reveal": 94,
        "climax": 92,
        "final_hook": 96,
        "bridge": 55,
        "optional": 28,
    }.get(role, 55)
    if index == 0:
        role_score = max(role_score, 86)
    if index == count - 1:
        role_score = max(role_score, 90)
    if row.get("explicit_speech"):
        role_score += 22
    if str(row.get("continuity_state", "")).strip():
        role_score += 8
    if str(row.get("subject_action", "")).strip():
        role_score += 5
    if row.get("locked") or row.get("lm_protect"):
        role_score = 100
    role_score += float(row.get("lm_importance_delta", 0.0) or 0.0)
    return max(0.0, min(100.0, role_score))


def _duration_constraints(row: Mapping[str, object], mode: str, grid: float) -> tuple[float, float]:
    duration = float(row["original_duration"])
    speech_min = _ceil_grid(float(row.get("speech_duration", 0.0) or 0.0), grid)
    actions = estimate_action_count(
        str(row.get("h3_executable_action", "") or row.get("subject_action", ""))
    )
    action_min = _ceil_grid(max(grid, actions * 1.5) if actions else grid, grid)
    protected_min = max(grid, speech_min, action_min)
    protected_min = min(duration, protected_min)
    floor_ratio = {"safe": 0.75, "balanced": 0.5, "aggressive": 0.0}[mode]
    mode_min = max(protected_min, _ceil_grid(duration * floor_ratio, grid))
    if row.get("locked"):
        mode_min = duration
    return protected_min, min(duration, mode_min)


def _boundary_cost(row: Mapping[str, object], segment_seconds: float) -> float:
    if segment_seconds <= 0:
        return 0.0
    tolerance = GRID_SECONDS / 2 + 1e-6
    values = (float(row["start_seconds"]), float(row["end_seconds"]))
    return 12.0 if any(abs(value % segment_seconds) <= tolerance for value in values if value > 0) else 0.0


def _remove_allowed(row: Mapping[str, object], mode: str, dependency_strength: int) -> bool:
    if row.get("locked") or row.get("lm_protect") or row.get("explicit_speech"):
        return False
    role = str(row.get("story_role", "bridge"))
    if role in {"hook", "clue", "reveal", "climax", "final_hook"}:
        return False
    score = float(row.get("importance", 100.0))
    if mode == "safe":
        return role == "optional" and score <= 38 and dependency_strength <= 2
    if mode == "balanced":
        return score <= 62 and dependency_strength <= 5
    return score <= 78 and dependency_strength <= 7


def _similarity(left: Mapping[str, object], right: Mapping[str, object]) -> float:
    left_tokens = _tokens(_combined_text(left))
    right_tokens = _tokens(_combined_text(right))
    if not left_tokens or not right_tokens:
        return 0.0
    union = left_tokens.union(right_tokens)
    lexical = len(left_tokens.intersection(right_tokens)) / max(1, len(union))
    left_media = {str(value) for value in (left.get("media_ids") or [])}
    right_media = {str(value) for value in (right.get("media_ids") or [])}
    media_bonus = 0.25 if left_media.intersection(right_media) else 0.0
    preset_bonus = 0.2 if str(left.get("preset", "")).casefold() == str(right.get("preset", "")).casefold() else 0.0
    return min(1.0, lexical + media_bonus + preset_bonus)


def normalize_lm_hints(payload: Mapping[str, object], valid_ids: Iterable[str]) -> dict[str, dict]:
    """Bound untrusted LM semantics; direct edit/timing instructions are ignored."""
    allowed = {str(value) for value in valid_ids}
    result: dict[str, dict] = {}
    for source in payload.get("shots", []) if isinstance(payload, Mapping) else []:
        if not isinstance(source, Mapping):
            continue
        shot_id = str(source.get("shot_id", ""))
        if shot_id not in allowed:
            continue
        redundancy = str(source.get("redundancy_with", "") or "")
        if redundancy not in allowed or redundancy == shot_id:
            redundancy = ""
        try:
            delta = float(source.get("importance_delta", 0.0) or 0.0)
        except (TypeError, ValueError):
            delta = 0.0
        role = str(source.get("story_role", "bridge") or "bridge").lower()
        if role not in {"hook", "clue", "reveal", "climax", "final_hook", "bridge", "optional"}:
            role = "bridge"
        raw_protect = source.get("protect", False)
        protect = (
            raw_protect
            if isinstance(raw_protect, bool)
            else str(raw_protect).strip().casefold() in {"1", "true", "yes", "on"}
        )
        result[shot_id] = {
            "story_role": role,
            "importance_delta": max(-15.0, min(15.0, delta)),
            "redundancy_with": redundancy,
            "protect": protect,
            "reason": " ".join(str(source.get("reason", "") or "").split())[:400],
        }
    return result


def smart_cut_lm_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["shots"],
        "properties": {
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "shot_id", "story_role", "importance_delta",
                        "redundancy_with", "protect", "reason",
                    ],
                    "properties": {
                        "shot_id": {"type": "string"},
                        "story_role": {
                            "type": "string",
                            "enum": ["hook", "clue", "reveal", "climax", "final_hook", "bridge", "optional"],
                        },
                        "importance_delta": {"type": "number", "minimum": -15, "maximum": 15},
                        "redundancy_with": {"type": "string"},
                        "protect": {"type": "boolean"},
                        "reason": {"type": "string"},
                    },
                },
            }
        },
    }


def smart_cut_lm_prompts(shots: Iterable[Mapping[str, object]], target_seconds: float) -> tuple[str, str]:
    rows = []
    for shot in shots:
        rows.append({
            "shot_id": shot.get("cue_id"),
            "time": [shot.get("start_seconds"), shot.get("end_seconds")],
            "preset": shot.get("preset"),
            "core_action": shot.get("subject_action"),
            "continuity": shot.get("continuity_state"),
            "optional": shot.get("optional_flourish") or shot.get("h3_optional_flourish"),
            "speech_count": shot.get("speech_count", 0),
            "speech_duration": shot.get("speech_duration", 0),
            "media_ids": shot.get("media_ids", []),
        })
    system = (
        "You are a story-editing analyst. Classify narrative roles, redundancy and protection only. "
        "Do not provide new timings, do not delete text, and do not rewrite dialogue. The deterministic "
        "Smart Cut engine remains the only authority allowed to change the Timeline."
    )
    user = (
        f"Target duration: {float(target_seconds):.2f}s. Analyze these ordered Shot records and return "
        "only the requested JSON semantic hints:\n" + str(rows)
    )
    return system, user


def plan_smart_cut(
    shots: Iterable[Mapping[str, object]],
    target_seconds: float,
    *,
    mode: str = "balanced",
    semantic_hints: Mapping[str, Mapping[str, object]] | None = None,
    grid_seconds: float = GRID_SECONDS,
    segment_seconds: float = 15.0,
) -> dict:
    """Return the minimum-story-loss plan on a fixed Timeline grid."""
    mode = str(mode or "balanced").lower()
    if mode not in SMART_CUT_MODES:
        mode = "balanced"
    grid = max(0.1, float(grid_seconds))
    hints = semantic_hints or {}
    normalized = [
        _normalize_shot(source, index, grid=grid, hint=hints.get(str(source.get("cue_id", "")), {}))
        for index, source in enumerate(shots)
    ]
    if not normalized:
        raise ValueError("Smart Cut requires at least one Shot.")
    edges = build_dependency_graph(normalized)
    dependency_by_id: dict[str, int] = {row["cue_id"]: 0 for row in normalized}
    for edge in edges:
        dependency_by_id[edge["from"]] = max(dependency_by_id.get(edge["from"], 0), int(edge["strength"]))
        dependency_by_id[edge["to"]] = max(dependency_by_id.get(edge["to"], 0), int(edge["strength"]))

    for index, row in enumerate(normalized):
        row["importance"] = _importance(row, index, len(normalized))
        protected_min, mode_min = _duration_constraints(row, mode, grid)
        row["protected_min_duration"] = protected_min
        row["minimum_duration"] = mode_min
        row["boundary_cost"] = _boundary_cost(row, segment_seconds)
        row["dependency_strength"] = dependency_by_id.get(row["cue_id"], 0)
        row["remove_allowed"] = _remove_allowed(row, mode, row["dependency_strength"])

    current = snap_seconds(sum(float(row["original_duration"]) for row in normalized), grid)
    target = max(grid, snap_seconds(float(target_seconds), grid))
    target = min(current, target)
    target_units = round(target / grid)

    # Dynamic programming over every legal 0.5-second duration choice.  Cost
    # reflects story importance, dependency risk and native 15s boundaries.
    states: dict[int, tuple[float, list[int]]] = {0: (0.0, [])}
    for row in normalized:
        original_units = max(1, round(float(row["original_duration"]) / grid))
        minimum_units = max(1, round(float(row["minimum_duration"]) / grid))
        options = list(range(minimum_units, original_units + 1))
        if row["remove_allowed"]:
            options.insert(0, 0)
        next_states: dict[int, tuple[float, list[int]]] = {}
        for total, (cost, choices) in states.items():
            for units in options:
                removed_fraction = (original_units - units) / original_units
                option_cost = removed_fraction * (8.0 + float(row["importance"]))
                if units == 0:
                    option_cost += (
                        float(row["importance"]) * 2.5
                        + float(row["dependency_strength"]) * 14.0
                        + float(row["boundary_cost"])
                    )
                    if row.get("redundancy_with"):
                        option_cost *= 0.22
                    elif row.get("story_role") == "optional":
                        option_cost *= 0.55
                elif units < original_units:
                    option_cost += float(row["dependency_strength"]) * 1.5
                key = total + units
                candidate = (cost + option_cost, choices + [units])
                existing = next_states.get(key)
                if existing is None or candidate[0] < existing[0]:
                    next_states[key] = candidate
        states = next_states

    if target_units in states:
        chosen_units = states[target_units][1]
    else:
        # Prefer the closest non-destructive result; when equally close, stay
        # above target to avoid silently dropping extra authored content.
        selected_total = min(
            states,
            key=lambda total: (abs(total - target_units), total < target_units, states[total][0]),
        )
        chosen_units = states[selected_total][1]

    decisions: list[dict] = []
    for row, units in zip(normalized, chosen_units):
        proposed = round(units * grid, 6)
        original = float(row["original_duration"])
        if units == 0:
            action = "remove"
            reason = "Lowest protected story value within the selected mode."
        elif proposed < original - 1e-6:
            action = "trim"
            reason = "Remove optional time while preserving speech and must-complete action budget."
        else:
            action = "keep"
            reason = "Protected by story value, speech, action budget or continuity."
        if row.get("lm_reason"):
            reason += " AI semantic note: " + str(row["lm_reason"])
        decisions.append({
            "shot_id": row["cue_id"],
            "action": action,
            "original_duration": original,
            "proposed_duration": proposed,
            "minimum_duration": float(row["minimum_duration"]),
            "protected_min_duration": float(row["protected_min_duration"]),
            "saved_seconds": round(original - proposed, 6),
            "importance": round(float(row["importance"]), 1),
            "story_role": row["story_role"],
            "protected": not bool(row["remove_allowed"]),
            "locked": bool(row["locked"]),
            "speech_count": int(row["speech_count"]),
            "speech_duration": float(row["speech_duration"]),
            "dependency_strength": int(row["dependency_strength"]),
            "boundary_cost": float(row["boundary_cost"]),
            "merge_into": "",
            "reason": reason,
            "source": deepcopy(row),
        })

    # Phase 2: express safe redundant removals as merges.  The removed Shot is
    # still omitted from the Timeline, but its reason/reference ownership is
    # attached to a surviving neighbor for audit and prompt reconciliation.
    by_id = {decision["shot_id"]: decision for decision in decisions}
    for index, decision in enumerate(decisions):
        if decision["action"] != "remove":
            continue
        candidates = []
        for neighbor_index in (index - 1, index + 1):
            if not (0 <= neighbor_index < len(decisions)):
                continue
            neighbor = decisions[neighbor_index]
            if neighbor["action"] == "remove":
                continue
            similarity = _similarity(decision["source"], neighbor["source"])
            hinted = str(decision["source"].get("redundancy_with", "")) == neighbor["shot_id"]
            if hinted:
                similarity = max(similarity, 0.75)
            candidates.append((similarity, neighbor))
        if candidates:
            similarity, neighbor = max(candidates, key=lambda item: item[0])
            if similarity >= 0.35:
                decision["action"] = "merge"
                decision["merge_into"] = neighbor["shot_id"]
                decision["reason"] = (
                    f"Redundant beat merges into {neighbor['shot_id']} "
                    f"(similarity {similarity:.0%}); deterministic timing still omits this interval."
                )

    edited = snap_seconds(sum(float(row["proposed_duration"]) for row in decisions), grid)
    protected_minimum = snap_seconds(
        sum(
            float(row["protected_min_duration"])
            for row in decisions
            if row["protected"] or row["speech_count"]
        ),
        grid,
    )
    warnings: list[str] = []
    speech_total = snap_seconds(sum(float(row["speech_duration"]) for row in decisions), grid)
    if speech_total > target + 1e-6:
        warnings.append(
            f"Authored speech alone requires about {speech_total:.1f}s, above the {target:.1f}s target."
        )
    if edited > target + 1e-6:
        warnings.append(
            f"Selected protections prevent an exact target; safest plan remains {edited:.1f}s."
        )
    if edited < target - 1e-6:
        warnings.append(f"Grid constraints produce {edited:.1f}s, {target - edited:.1f}s under target.")

    affected_ranges: list[list[float]] = []
    for index, decision in enumerate(decisions):
        if decision["action"] == "keep":
            continue
        left = decisions[max(0, index - 1)]["source"]["start_seconds"]
        right = decisions[min(len(decisions) - 1, index + 1)]["source"]["end_seconds"]
        affected_ranges.append([float(left), float(right)])

    return {
        "format": "h3-smart-cut-plan",
        "version": 1,
        "mode": mode,
        "grid_seconds": grid,
        "segment_seconds": float(segment_seconds),
        "current_duration": current,
        "target_duration": target,
        "edited_duration": edited,
        "saved_seconds": round(current - edited, 6),
        "minimum_protected_duration": protected_minimum,
        "on_target": abs(edited - target) <= 1e-6,
        "warnings": warnings,
        "dependency_graph": edges,
        "affected_ranges": affected_ranges,
        "decisions": decisions,
        "lm_semantics_applied": bool(hints),
    }

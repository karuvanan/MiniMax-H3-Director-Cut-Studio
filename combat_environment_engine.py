"""Stateful environmental combat causality for the Street Fighter H3 Skill.

This module does not simulate rigid bodies or post-process rendered video.  It
turns Timeline-owned combat, location and reference state into deterministic,
bounded instructions that are compiled into the real MiniMax H3 prompt.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Iterable


STREET_FIGHTER_SKILL = "street-fighter-live-action-h3"
# Additive fields remain readable by alpha.5 projects; keep the persisted
# schema number stable so old project loaders do not reject the new vectors.
ENVIRONMENT_PHYSICS_SCHEMA_VERSION = 1

INDOOR_PLATE_ID = "street_fighter_kowloon_market_indoor_spectators"
OUTDOOR_PLATE_ID = "street_fighter_kowloon_alley_outdoor_spectators"
LEGACY_PLATE_ID = "street_fighter_kowloon_market_spectators"

CAUSALITY_CONTRACT = (
    "ENVIRONMENTAL COMBAT CAUSALITY: show the fighter action and exact contact first; only then "
    "show one primary physical response and at most one secondary response. Preserve every "
    "displaced, dented, leaking, open or broken state in all later shots. No spontaneous damage, "
    "instant repair, unrelated explosion, reset prop, duplicate fighter or crowd member entering "
    "the central combat lane."
)


def _skill_enabled(special_skill_key: object) -> bool:
    return str(special_skill_key or "").strip().casefold() == STREET_FIGHTER_SKILL


def _snap_half(value: float) -> float:
    return round(float(value) * 2.0) / 2.0


def environment_transition_time(duration_seconds: object) -> float:
    """Return the indoor/outdoor threshold on the native half-second grid."""

    duration = max(0.5, float(duration_seconds or 0.5))
    # The default 45-second production crosses at 30 seconds. Shorter supported
    # fights use the same two-thirds story duty rather than losing the exterior.
    transition = _snap_half(duration * 2.0 / 3.0)
    return min(max(0.5, transition), max(0.5, duration - 0.5))


def _append_once(value: object, contract: str) -> str:
    text = str(value or "").strip()
    signature = contract.split(":", 1)[0].strip().casefold()
    if signature and signature in text.casefold():
        return text
    return text.rstrip(" .") + (". " if text else "") + contract


def _replace_generated_line(value: object, marker: str, content: str) -> str:
    """Replace an engine-owned line without touching user-authored prose."""

    prefix = f"[{marker}]"
    rows = [
        row.rstrip()
        for row in str(value or "").splitlines()
        if not row.strip().startswith(prefix)
    ]
    rows.append(f"{prefix} {content.strip()}")
    return "\n".join(row for row in rows if row.strip()).strip()


def _compact_action(value: object, limit: int = 150) -> str:
    text = " ".join(str(value or "").split()).strip(" .")
    text = re.sub(r"\[BEAT\s+\d+[^\]]*\]", "", text, flags=re.I)
    text = " ".join(text.split()).strip(" .")
    if len(text) > limit:
        text = text[: limit - 1].rstrip(" ,;:") + "…"
    return text or "active close-combat contact"


def _cause_actor(action: str, index: int) -> str:
    match = re.search(r"\b(S[12])\b", action, flags=re.I)
    return match.group(1).upper() if match else ("S1" if index % 2 == 0 else "S2")


def _has_combat_cause(value: object) -> bool:
    text = str(value or "").casefold()
    if not text.strip():
        return False
    return any(word in text for word in (
        "punch", "kick", "strike", "parry", "parries", "block", "throw", "takedown", "clinch",
        "grip", "elbow", "forearm", "palm", "sweep", "slam", "drive", "driving", "ground", "bridge",
        "attack", "defence", "defense", "impact", "contact", "exchange", "counter",
        "拳", "踢", "击", "擊", "挡", "擋", "摔", "抱", "抓", "掌", "肘", "扫",
        "掃", "攻", "防", "格斗", "格鬥", "反击", "反擊", "压制", "壓制",
        # Release, submission and recovery actions still have a visible
        # physical cause.  They previously fell through as "no contact",
        # producing a red environment warning on otherwise valid final Shots.
        "submission", "choke", "armbar", "wrist", "grip", "release", "recover",
        "tap", "guarded base", "绞", "絞", "关节", "關節", "腕", "松开", "松開",
        "hip-turn", "hip turn", "redirect", "brace", "latch", "gate",
        "髋转", "髖轉", "转向", "轉向", "支撑", "支撐", "闸门", "閘門",
    ))


def _object_id(target: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", target.casefold()).strip("_")
    return "env_" + (token or "contact_target")


def _mechanic(action: str) -> str:
    lowered = action.casefold()
    rows = (
        (("takedown", "throw", "hip-turn", "foot-sweep", "抱摔", "投技", "足扫", "摔"), "throw or takedown momentum"),
        (("kick", "shin", "踢", "胫"), "committed kick or checked-kick momentum"),
        (("clinch", "underhook", "overhook", "grip", "夹抱", "抓", "锁臂"), "clinch or grip drive"),
        (("palm", "forearm", "elbow", "parry", "掌", "前臂", "肘", "拨挡"), "redirected palm, forearm or elbow contact"),
        (("ground", "bridge", "side control", "地面", "桥式", "压制"), "grounded body-pressure shift"),
        (("submission", "choke", "armbar", "wrist", "release", "recover", "tap", "绞", "絞", "关节", "關節"), "controlled submission release and recovery"),
    )
    for words, label in rows:
        if any(word in lowered for word in words):
            return label
    return "active close-combat momentum"


def _location_for_shot(start: float, end: float, transition: float) -> str:
    transition_window = max(0.0, transition - 2.5)
    if start >= transition - 1e-6:
        return "outdoor_rain_alley"
    if end > transition_window + 1e-6:
        return "market_loading_threshold"
    if start >= transition / 2.0:
        return "fish_vegetable_junction"
    return "indoor_seafood_aisle"


def _location_description(location: str) -> str:
    return {
        "indoor_seafood_aisle": (
            "the connected indoor Kowloon-style seafood aisle with fish tanks, crushed-ice trays, "
            "metal counters, hanging scales, overhead pipes and yellow-green practical lamps"
        ),
        "fish_vegetable_junction": (
            "the connected indoor fish-to-vegetable junction with wet produce crates, tarpaulins, "
            "the same drain and overhead pipe landmarks"
        ),
        "market_loading_threshold": (
            "the visible loading passage and metal-gate threshold connecting the indoor market to "
            "the rainy exterior alley"
        ),
        "outdoor_rain_alley": (
            "the outdoor Hong Kong service alley immediately beyond the same market gate, with rain, "
            "neon and vehicle spill, drains, wet concrete, awnings and exterior market crates"
        ),
    }[location]


_INDOOR_EFFECTS = (
    ("shallow floor puddle", "a low directional splash follows the planted foot", "water spreads along the existing drain", "light"),
    ("hanging scale chain", "the scale swings once from the transferred vibration", "nearby hooks rattle briefly", "light"),
    ("crushed-ice seafood tray", "the tray shifts and loose ice scatters away from the contact", "one fish basket tips against the counter", "medium"),
    ("stacked wet produce crates", "the upper crate overturns toward the wall", "vegetables roll along the sloped wet floor", "medium"),
    ("aged metal stall side panel", "the panel dents inward at the contact point", "rust dust falls only after the impact", "medium"),
    ("fish-tank support frame", "the frame vibrates while the intact tank water sloshes", "cyan reflections tremble across the puddle", "light"),
)

_THRESHOLD_EFFECTS = (
    ("hanging loading-strip curtain", "the strips snap apart around the moving fighters", "indoor steam spills toward the doorway", "light"),
    ("stacked loading crates", "two crates slide toward the wall and remain displaced", "the clear route to the gate becomes visible", "medium"),
    ("metal market gate and latch", "the latch bends and the gate is forced outward by the visible body momentum", "the gate remains open onto the rainy alley", "heavy"),
)

_OUTDOOR_EFFECTS = (
    ("rain-filled alley puddle", "a broad directional splash follows the visible landing", "runoff carries loose ice toward the street drain", "light"),
    ("exterior plastic fish crate", "the crate skids to the brick wall and remains there", "its loose lid spins once then settles", "medium"),
    ("corrugated market awning support", "the support shudders without collapsing", "rain sheets briefly from the awning edge", "light"),
    ("metal refuse bin", "the bin tips onto its side after contact", "empty plastic baskets scatter away from P1 and P2", "medium"),
    ("delivery handcart", "the handcart rolls a short distance and stops against a bollard", "its chain rattles after the stop", "medium"),
)

_MATERIAL_RESPONSE = {
    "water": "fans low across the floor, then follows the existing drain gradient",
    "loose_ice": "scatters and slides with low friction before settling",
    "wet_plastic": "skids first, then yaws and stops against the nearest fixed obstacle",
    "aged_metal": "dents or flexes at the contact point before vibration travels through its supports",
    "hanging_metal": "swings from its suspension point and returns with diminishing amplitude",
    "glass_water_frame": "the frame vibrates first and the contained water sloshes after it",
    "fabric_strip": "snaps away from the moving bodies and trails behind their passage",
    "rubber_wheel_cart": "rolls along the applied horizontal force until a visible stop arrests it",
}

_RECOVERY_ACTION_RE = re.compile(
    r"(?i)\b(?:submission|choke|armbar|wrist|release|recover|tap|guarded\s+base|"
    r"reset(?:s|ting)?|hip[- ]escape)\b|绞|絞|关节|關節|腕|松开|松開|复位|復位"
 )


def _material_for_target(target: str) -> str:
    lowered = target.casefold()
    if "puddle" in lowered:
        return "water"
    if "ice" in lowered:
        return "loose_ice"
    if "plastic" in lowered or "crate" in lowered:
        return "wet_plastic"
    if "tank" in lowered:
        return "glass_water_frame"
    if "curtain" in lowered:
        return "fabric_strip"
    if "cart" in lowered:
        return "rubber_wheel_cart"
    if "chain" in lowered or "scale" in lowered or "hook" in lowered:
        return "hanging_metal"
    return "aged_metal"


def _force_from_shot(shot: dict, action: str, actor: str) -> dict:
    stored = shot.get("combat_force_vector")
    if isinstance(stored, dict) and stored.get("label"):
        return dict(stored)
    # Local fallback keeps this module usable on older projects and direct tests.
    lowered = action.casefold()
    horizontal = "screen-left" if actor == "S2" else "screen-right"
    if " left" in lowered or "向左" in lowered:
        horizontal = "screen-left"
    elif " right" in lowered or "向右" in lowered:
        horizontal = "screen-right"
    vertical = "downward" if any(word in lowered for word in ("slam", "floor", "ground", "向下", "落地")) else "level"
    if any(word in lowered for word in ("rising", "uppercut", "lift", "向上", "上挑")):
        vertical = "upward"
    depth = "backward" if any(word in lowered for word in ("recoil", "retreat", "backward", "backwards", "后退", "後退")) else "forward"
    magnitude = "heavy" if any(word in lowered for word in ("throw", "takedown", "slam", "drive", "摔", "猛推")) else "medium"
    return {
        "horizontal": horizontal,
        "vertical": vertical,
        "depth": depth,
        "magnitude": magnitude,
        "label": f"{horizontal}, {vertical}, {depth}",
    }


def _directional_responses(
    target: str,
    primary: str,
    secondary: str,
    material: str,
    force: dict,
) -> tuple[str, str]:
    direction = str(force.get("label") or "screen-right, level, forward")
    physical_rule = _MATERIAL_RESPONSE.get(material, "moves away from the visible contact and then settles")
    directed_primary = (
        f"{primary.rstrip(' .')}; {target} responds along {direction}: {physical_rule}"
    )
    directed_secondary = (
        f"{secondary.rstrip(' .')}; all loose secondary material continues along {direction} "
        "with less energy and never travels against the applied force"
    )
    return directed_primary, directed_secondary


def _effect_for(location: str, index: int, *, threshold_exit: bool) -> tuple[str, str, str, str]:
    if threshold_exit:
        return _THRESHOLD_EFFECTS[-1]
    if location == "market_loading_threshold":
        return _THRESHOLD_EFFECTS[index % (len(_THRESHOLD_EFFECTS) - 1)]
    if location == "outdoor_rain_alley":
        return _OUTDOOR_EFFECTS[index % len(_OUTDOOR_EFFECTS)]
    return _INDOOR_EFFECTS[index % len(_INDOOR_EFFECTS)]


def _effect_for_action(
    action: str,
    location: str,
    index: int,
    *,
    threshold_exit: bool,
) -> tuple[str, str, str, str]:
    """Honor an authored contact object before using deterministic variety."""

    lowered = action.casefold()
    if any(word in lowered for word in (
        "submission", "choke", "armbar", "wrist", "release", "recover", "tap",
        "绞", "絞", "关节", "關節", "腕", "松开", "松開",
    )):
        # A release or recovery should not randomly destroy a stall.  Use the
        # least disruptive material and let the force vector describe a small
        # splash/foot adjustment instead.
        return _OUTDOOR_EFFECTS[0] if location == "outdoor_rain_alley" else _INDOOR_EFFECTS[0]
    if any(word in lowered for word in ("puddle", "wet floor", "水洼", "水窪", "湿地", "濕地")):
        return _OUTDOOR_EFFECTS[0] if location == "outdoor_rain_alley" else _INDOOR_EFFECTS[0]
    if any(word in lowered for word in ("crate", "produce", "vegetable", "菜箱", "货箱", "貨箱")):
        return _OUTDOOR_EFFECTS[1] if location == "outdoor_rain_alley" else _INDOOR_EFFECTS[3]
    explicit = (
        (("gate", "latch", "闸门", "閘門", "门闩", "門閂"), _THRESHOLD_EFFECTS[-1]),
        (("stall", "metal panel", "档口", "檔口", "摊位", "攤位"), _INDOOR_EFFECTS[4]),
        (("fish tank", "tank frame", "鱼缸", "魚缸"), _INDOOR_EFFECTS[5]),
        (("ice tray", "seafood tray", "crushed ice", "冰盘", "冰盤"), _INDOOR_EFFECTS[2]),
        (("scale", "hook", "秤", "吊钩", "吊鉤"), _INDOOR_EFFECTS[1]),
        (("awning", "雨棚"), _OUTDOOR_EFFECTS[2]),
        (("handcart", "cart", "手推车", "手推車"), _OUTDOOR_EFFECTS[4]),
        (("refuse bin", "trash bin", "垃圾桶"), _OUTDOOR_EFFECTS[3]),
    )
    for words, effect in explicit:
        if any(word in lowered for word in words):
            return effect
    return _effect_for(location, index, threshold_exit=threshold_exit)


def _crowd_response(location: str, damage_level: str, index: int) -> str:
    delay = (0.25, 0.35, 0.45)[index % 3]
    if location == "market_loading_threshold":
        action = (
            "the nearest vendors recoil and pull one companion clear of the opening while the rest "
            "part toward both sides of the gate"
        )
    elif location == "outdoor_rain_alley":
        action = (
            "alley spectators retreat against the shopfronts and keep the centre route clear; none "
            "approaches or joins the fight"
        )
    elif damage_level in {"medium", "heavy"}:
        action = (
            "the nearest vendors shield their faces and pull one another one step behind the stalls; "
            "distant spectators remain at the perimeter"
        )
    else:
        action = (
            "the nearest spectators flinch and shift one step away while the distant crowd keeps its "
            "established perimeter positions"
        )
    return f"About {delay:.2f}s after the visible contact, {action}."


def _persistent_update(target: str, primary: str, secondary: str, damage_level: str) -> str:
    if damage_level == "light" and not any(
        word in primary.casefold() for word in ("remain", "spreads", "displaced", "open")
    ):
        return ""
    return f"{target}: {primary}; {secondary}"


def _bounded_state(location: str, ledger: list[str]) -> str:
    base = "Location=" + location
    if not ledger:
        return base + "; all tracked fixtures retain their established state"
    # H3 needs the current irreversible state, not an unbounded history dump.
    prefix = (
        "; all earlier tracked changes also persist unchanged; recent persistent state: "
        if len(ledger) > 6
        else "; persistent state: "
    )
    return base + prefix + " | ".join(ledger[-6:])


def reconcile_environmental_combat_rows(
    rows: Iterable[dict],
    duration_seconds: object,
    *,
    transition_basis_seconds: object | None = None,
) -> tuple[list[dict], list[str]]:
    """Apply a bounded causal/state chain to chronological Shot dictionaries."""

    duration = max(0.5, float(duration_seconds or 0.5))
    transition = environment_transition_time(
        duration if transition_basis_seconds is None else transition_basis_seconds
    )
    shots = sorted(
        (deepcopy(row) for row in rows if isinstance(row, dict)),
        key=lambda row: (
            float(row.get("start_seconds", 0.0)),
            float(row.get("end_seconds", 0.0)),
            str(row.get("id") or row.get("cue_id") or ""),
        ),
    )
    ledger: list[str] = []
    warnings: list[str] = []
    for index, shot in enumerate(shots):
        start = max(0.0, float(shot.get("start_seconds", 0.0) or 0.0))
        end = max(start + 0.05, float(shot.get("end_seconds", start + 0.5) or start + 0.5))
        location = _location_for_shot(start, end, transition)
        threshold_exit = start < transition <= end + 1e-6 or (
            end >= transition - 1e-6 and location == "market_loading_threshold"
        )
        raw_action = shot.get("subject_action", "")
        has_cause = _has_combat_cause(raw_action)
        action = _compact_action(raw_action)
        actor = _cause_actor(action, index)
        target, primary, secondary, damage_level = _effect_for_action(
            action, location, index, threshold_exit=threshold_exit
        )
        force = _force_from_shot(shot, action, actor)
        material = _material_for_target(target)
        primary, secondary = _directional_responses(
            target, primary, secondary, material, force
        )
        contact_time = min(end - 0.05, start + max(0.15, min(0.65, (end - start) * 0.45)))
        automatic_interaction = (
            f"cause_actor={actor}; action={_mechanic(action)}; contact_target_id={_object_id(target)}; "
            f"contact_target={target}; contact_material={material}; contact_time={contact_time:.2f}s; "
            f"force_direction={force.get('label')}; force_magnitude={force.get('magnitude')}; "
            f"primary_response={primary}; secondary_response={secondary}. "
            "Show the action and exact contact before either response."
        ) if has_cause else ""
        crowd = _crowd_response(location, damage_level, index) if has_cause else ""
        if bool(shot.get("environment_interaction_user_edited", False)):
            interaction = str(shot.get("environment_interaction", "")).strip()
        else:
            interaction = automatic_interaction
        if bool(shot.get("crowd_reaction_user_edited", False)):
            crowd = str(shot.get("crowd_reaction", "")).strip()

        incoming = _bounded_state(location, ledger)
        update = _persistent_update(target, primary, secondary, damage_level) if has_cause else ""
        if update and update not in ledger:
            ledger.append(update)
        outgoing = _bounded_state(location, ledger)

        if location == "market_loading_threshold":
            transition_text = (
                f"INDOOR→OUTDOOR ROUTE: active attack, defence, clinch or throw carries P1/S1 and "
                f"P2/S2 through the visible market loading passage toward the gate at {transition:.2f}s; "
                "never insert walking coverage, an establishing cut or teleportation."
            )
        elif location == "outdoor_rain_alley":
            transition_text = (
                "OUTDOOR CONTINUATION: remain immediately outside the same now-open market gate; "
                "preserve screen direction, wetness, carried debris, fighter momentum and the FPV orbit."
            )
        else:
            transition_text = (
                "INDOOR CONTINUITY: remain inside the visibly connected market aisle; any movement "
                "between stalls is caused only by the ongoing exchange."
            )

        for field_name, generated in (
            ("incoming_environment_state", incoming),
            ("outgoing_environment_state", outgoing),
            ("location_transition", transition_text),
        ):
            if not bool(shot.get(f"{field_name}_user_edited", False)):
                shot[field_name] = generated
        shot["environment_interaction"] = interaction
        shot["crowd_reaction"] = crowd
        shot["contact_material"] = material if has_cause else ""
        shot["environment_force_vector"] = force if has_cause else {}
        outgoing_combat = shot.get("outgoing_combat_state_vector")
        if has_cause and isinstance(outgoing_combat, dict):
            outgoing_combat["environment_aftermath"] = (
                f"{target} responds {force.get('label')} and remains in the resulting state"
            )
            shot["outgoing_combat_state_vector"] = outgoing_combat
            if not bool(shot.get("outgoing_combat_state_user_edited", False)):
                shot["outgoing_combat_state"] = "; ".join(
                    f"{key}={value}" for key, value in outgoing_combat.items()
                )
        user_authored_uncaused_interaction = (
            not has_cause
            and bool(shot.get("environment_interaction_user_edited", False))
            and bool(str(shot.get("environment_interaction", "")).strip())
        )
        shot["environment_state_status"] = (
            "warning" if user_authored_uncaused_interaction
            else "transition" if location == "market_loading_threshold"
            else "continuous"
        )
        shot["environment_physics_schema_version"] = ENVIRONMENT_PHYSICS_SCHEMA_VERSION

        shot["environment_response"] = _replace_generated_line(
            shot.get("environment_response", ""),
            "ENV-PHYSICS",
            (
                f"{interaction} CROWD RESPONSE - {crowd}"
                if interaction
                else "No material contact is authored in this Shot; preserve the established environment state without spontaneous damage."
            ),
        )
        shot["continuity_state"] = _replace_generated_line(
            shot.get("continuity_state", ""),
            "ENV-IN",
            str(shot.get("incoming_environment_state", incoming)),
        )
        shot["continuity_state"] = _replace_generated_line(
            shot.get("continuity_state", ""),
            "ENV-OUT",
            str(shot.get("outgoing_environment_state", outgoing)),
        )
        shot["additional_direction"] = _replace_generated_line(
            shot.get("additional_direction", ""),
            "LOCATION",
            str(shot.get("location_transition", transition_text)),
        )
        shot["additional_direction"] = _append_once(
            shot.get("additional_direction", ""), CAUSALITY_CONTRACT
        )

        if has_cause:
            shot["event_causality_chain"] = (
                f"EVENT CAUSE: {actor} performs {_mechanic(action)}; "
                f"EVENT RESPONSE: {target} receives the visible contact; "
                f"EVENT CONSEQUENCE: {primary}; NEXT EVENT: the resulting state persists into the following Shot."
            )
            shot["physical_feedback_chain"] = (
                f"PHYSICAL FEEDBACK: {material} responds along {force.get('label')} with "
                f"{force.get('magnitude')} magnitude; show contact before the response and preserve the result."
            )
        else:
            shot["event_causality_chain"] = (
                "EVENT CAUSE: no fighter-to-material contact is authored; EVENT RESPONSE: no object "
                "moves or breaks; NEXT EVENT: preserve the incoming environment state unchanged."
            )
            shot["physical_feedback_chain"] = (
                "PHYSICAL FEEDBACK: none required without visible contact; stable fighter recovery is not damage."
            )

        if (
            _RECOVERY_ACTION_RE.search(str(raw_action or ""))
            and not bool(shot.get("environment_interaction_user_edited", False))
        ):
            shot["causal_risk_repair_status"] = "auto_fixed"
            shot["causal_risk_repair_notes"] = (
                "Added a minimal recovery contact and directional physical feedback; no destructive event was invented."
            )

        if user_authored_uncaused_interaction:
            warnings.append(
                f"{shot.get('id') or shot.get('cue_id') or f'Shot {index + 1}'} has no visible "
                "environmental contact cause for its user-edited interaction."
            )

    return shots, warnings


def _environment_plate_request(
    requirement_id: str,
    *,
    start: float,
    end: float,
    outdoor: bool,
) -> dict:
    if outdoor:
        prompt = (
            "Cinematic photoreal live-action environment and spectator reference, rainy Hong Kong "
            "service alley immediately outside a dense Kowloon Walled City-style fish, seafood and "
            "vegetable wet market. Preserve the visible open metal market gate, matching drain, pipes, "
            "exterior crates and material language from the indoor market. Wet concrete, rain runoff, "
            "neon and vehicle-light reflections, corrugated awnings, delivery handcart and narrow shopfronts. "
            "Eight to twelve distinct adult Hong Kong vendors and bystanders remain only against the far "
            "perimeter, leaving one unobstructed central combat route. Environment/background crowd only; "
            "no principal fighter, no P1/P2 substitute, no generic central man/woman pair."
        )
    else:
        prompt = (
            "Cinematic photoreal live-action environment and spectator reference, one coherent Hong Kong "
            "Kowloon Walled City-style fish, seafood and vegetable wet market. Cramped tiled and aged-concrete "
            "aisles, metal fish stalls, tanks, hanging scales, crushed-ice trays, wet produce crates, drainage, "
            "dense overhead pipes/cables, humid steam and wet reflective floor. Twelve to eighteen distinct "
            "adult Hong Kong vendors and spectators stand only around the far perimeter, leaving one clean "
            "unobstructed central combat lane. Environment/background crowd only; no principal fighter, no "
            "P1/P2 substitute, no generic central man/woman pair."
        )
    prompt += (
        " Stable architecture, practical cyan, yellow-green and warm market lighting, varied faces and "
        "wardrobe, no cloned crowd, no readable sign, no subtitle, no text, no logo, no watermark."
    )
    return {
        "requirement_id": requirement_id,
        "media_type": "image",
        "usage": "h3_reference",
        "reuse_policy": "time_scoped",
        "start_seconds": start,
        "end_seconds": end,
        "track": "V3",
        "subject_keywords": [
            "Hong Kong Kowloon wet market" if not outdoor else "rainy Hong Kong market alley",
            "background spectators and vendors",
            "clear central combat route",
        ],
        "prompt": prompt,
        "negative_prompt": (
            "principal fighter, foreground fighter, two central fighters, P1 substitute, P2 substitute, "
            "duplicate person, cloned crowd face, crowd inside fight lane, boxing ring, clean supermarket, "
            "dry floor, empty market, stage spotlight, readable sign, subtitle, text, logo, watermark"
        ),
    }


def _install_environment_plates(plan: dict, *, transition_basis_seconds: object | None = None) -> None:
    duration = max(0.5, float(plan.get("duration_seconds", 0.5) or 0.5))
    transition = environment_transition_time(
        duration if transition_basis_seconds is None else transition_basis_seconds
    )
    requests = [
        row for row in plan.get("media_requests") or []
        if isinstance(row, dict)
        and str(row.get("requirement_id", ""))
        not in {LEGACY_PLATE_ID, INDOOR_PLATE_ID, OUTDOOR_PLATE_ID}
    ]
    uses = [row for row in plan.get("existing_media_uses") or [] if isinstance(row, dict)]
    legacy = next(
        (row for row in uses if str(row.get("requirement_id", "")) == LEGACY_PLATE_ID),
        None,
    )
    if legacy is not None:
        legacy["requirement_id"] = INDOOR_PLATE_ID

    for requirement_id, start, end, outdoor in (
        (INDOOR_PLATE_ID, 0.0, transition, False),
        (OUTDOOR_PLATE_ID, transition, duration, True),
    ):
        use = next(
            (row for row in uses if str(row.get("requirement_id", "")) == requirement_id),
            None,
        )
        if use is not None:
            use.update({
                "usage": "h3_reference",
                "reuse_policy": "time_scoped",
                "start_seconds": start,
                "end_seconds": end,
                "track": "V3",
            })
        else:
            requests.append(
                _environment_plate_request(
                    requirement_id,
                    start=start,
                    end=end,
                    outdoor=outdoor,
                )
            )
    plan["existing_media_uses"] = uses
    plan["media_requests"] = requests


def apply_environmental_combat_physics(
    plan: dict,
    *,
    special_skill_key: object,
) -> dict:
    """Enrich a normalized Street Fighter plan with alpha.5 state and media."""

    if not _skill_enabled(special_skill_key):
        return plan
    actual_duration = max(0.5, float(plan.get("duration_seconds", 0.5) or 0.5))
    try:
        baseline_duration = float(
            plan.get("_speech_timing_base_duration", actual_duration) or actual_duration
        )
    except (TypeError, ValueError):
        baseline_duration = actual_duration
    baseline_duration = min(actual_duration, max(0.5, baseline_duration))
    shots, warnings = reconcile_environmental_combat_rows(
        plan.get("shots") or [],
        actual_duration,
        transition_basis_seconds=baseline_duration,
    )
    plan["shots"] = shots
    plan["environment_physics_schema_version"] = ENVIRONMENT_PHYSICS_SCHEMA_VERSION
    plan["environment_transition_time_seconds"] = environment_transition_time(
        baseline_duration
    )
    plan["constraints"] = _append_once(plan.get("constraints", ""), CAUSALITY_CONTRACT)
    _install_environment_plates(plan, transition_basis_seconds=baseline_duration)
    notices = [str(value) for value in plan.get("design_warnings") or []]
    notices.extend(warnings)
    notice = (
        "Environmental Combat Physics is active: persistent damage, delayed perimeter-crowd reaction "
        "and the indoor-market to outdoor-alley threshold are compiled into H3 Segment prompts."
    )
    if notice not in notices:
        notices.append(notice)
    plan["design_warnings"] = list(dict.fromkeys(notices))
    return plan


def environmental_combat_prompt_clause(row: dict, *, include_global_contract: bool = True) -> str:
    """Return one compact, explicit H3 clause for a Timeline Shot."""

    if not isinstance(row, dict) or not int(row.get("environment_physics_schema_version", 0) or 0):
        return ""
    parts = [
        "ENVIRONMENT INTERACTION - " + str(row.get("environment_interaction", "")).strip(),
        "CROWD REACTION - " + str(row.get("crowd_reaction", "")).strip(),
        "INCOMING ENVIRONMENT STATE - " + str(row.get("incoming_environment_state", "")).strip(),
        "OUTGOING ENVIRONMENT STATE - " + str(row.get("outgoing_environment_state", "")).strip(),
        "LOCATION TRANSITION - " + str(row.get("location_transition", "")).strip(),
        "EVENT CAUSALITY - " + str(row.get("event_causality_chain", "")).strip(),
        "PHYSICAL FEEDBACK - " + str(row.get("physical_feedback_chain", "")).strip(),
    ]
    if include_global_contract:
        parts.append(CAUSALITY_CONTRACT)
    return " ".join(part for part in parts if not part.endswith(" - "))

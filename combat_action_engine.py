"""Deterministic action continuity for the Street Fighter H3 Special Skill.

The engine translates dense choreography into an executable two-beat Shot
contract.  It does not invent a separate render path: the resulting fields are
Timeline data and are compiled into the existing MiniMax H3 prompt.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Iterable


STREET_FIGHTER_SKILL = "street-fighter-live-action-h3"
HONG_KONG_COMIC_FIGHTER_SKILL = "hong-kong-comic-fighter"
COMBAT_ACTION_SKILLS = frozenset({
    STREET_FIGHTER_SKILL,
    HONG_KONG_COMIC_FIGHTER_SKILL,
})
COMBAT_ACTION_SCHEMA_VERSION = 3
COMBAT_FACT_LEDGER_SCHEMA_VERSION = 1
COMBAT_FACT_AUTHORITY = (
    "explicit_user_direction",
    "loaded_picture_pixels",
    "explicit_role_binding",
    "blip_overview",
    "ai_enrich",
    "special_skill_default",
)
ACTION_CAUSALITY_CONTRACT = (
    "COMBAT ACTION CONTINUITY: every exchange follows load and weight, acceleration, attack line, "
    "contact or visible miss, defender response, force and displacement, then one environment result "
    "that triggers the next Beat. Preserve position, facing, velocity, height/support, guard or grip, "
    "advantage and visible aftermath across Shot boundaries; no neutral reset or unexplained ownership change."
)
FACT_LEDGER_CONTRACT = (
    "COMBAT FACT LEDGER: explicit user direction outranks loaded P1/P2 pixels, explicit role "
    "bindings, BLIP Overview, AI Enrich and Skill defaults in that order. Text metadata may "
    "describe but never replace loaded pixels. Every explicitly bound character identity, wardrobe "
    "and action ownership remains stable unless the user changes it; P numbering alone never "
    "creates an S1/P1 or S2/P2 binding."
)
FIVE_DUTY_CONTRACT = (
    "FIVE-DUTY ACTION WINDOW: each 15-second combat window progresses through state pickup, "
    "escalation, advantage shift, environment consequence and outgoing relay without adding "
    "new Segments or resetting the fight."
)
ACTION_CARRIER_CONTRACT = (
    "ACTION CARRIER ROUTING: route each Beat through bare-hand strike, kick, grapple, throw or "
    "ground control. Do not introduce a weapon, giant object or supernatural carrier unless "
    "the user explicitly requested it."
)
DYNAMIC_CAMERA_CONTRACT = (
    "ACTION-TRIGGERED CAMERA: the one principal physical FPV move in each Shot is selected by "
    "the active strike, defence, grip, throw, ground exchange or reversal and continues from "
    "the preceding camera sector; no fixed frontal reset, in-place spin or lens zoom."
)
CAUSAL_VALIDATION_CONTRACT = (
    "CAUSAL RISK VALIDATION: silently verify every Beat's load, trajectory, response, contact, "
    "force, displacement and next trigger; verify each following Shot inherits at least four of "
    "position, facing, velocity, support, advantage and environment aftermath. Deterministic "
    "generated defects are repaired automatically; ambiguous user-authored conflicts remain visible warnings."
)
FINAL_COMBAT_RESOLUTION_CONTRACT = (
    "FINAL COMBAT RESOLUTION: complete the last authored technique at real-time speed, visibly "
    "dissipate its momentum, settle both fighters on readable support with no new attack, and let "
    "the action-triggered FPV camera decelerate into a stable three-quarter composition for the "
    "last 0.75-1.00 second. No zoom, in-place spin, walk-away, replay or slow-motion contact."
)

_REQUIRED_BEAT_FIELDS = (
    "load_weight", "trajectory", "defensive_response", "contact_kind",
    "force_vector", "displacement", "next_trigger",
)
_STATE_RELAY_KEYS = (
    "positions", "facing", "velocity", "support", "advantage", "environment_aftermath",
)
_ALLOWED_ACTION_CARRIERS = {
    "bare_hand_strike", "kick", "grapple_clinch", "throw_takedown", "ground_control",
}

_BEAT_TAG_RE = re.compile(r"\[BEAT\s+\d+[^\]]*\]", re.I)
_ACTOR_RE = re.compile(r"\b(S[12])\b", re.I)
_DEFENCE_RE = re.compile(
    r"(?i)\b(?:parr(?:y|ies|ied)|block(?:s|ed)?|evad(?:e|es|ed)|duck(?:s|ed)?|"
    r"slip(?:s|ped)?|check(?:s|ed)?|sprawl(?:s|ed)?|frame(?:s|d)?|guard(?:s|ed)?)\b|"
    r"招架|格挡|格擋|闪避|閃避|下潜|下潛|防守|防御|防禦"
)
_SAFE_ACTOR_FIX_RE = re.compile(
    r"(?i)\b(?:parr(?:y|ies|ied)|block(?:s|ed)?|check(?:s|ed)?)\b|"
    r"招架|格挡|格擋|提胫|提脛"
)
_GROUND_CAPTURE_RE = re.compile(
    r"(?i)single[- ]leg|double[- ]leg|captures?\s+(?:the\s+)?leg|takedown|抱腿|抱摔"
)
_TOP_CONTROL_RE = re.compile(
    r"(?i)side control|mount(?:ed)?|top control|ground[- ]and[- ]pound|上位压制|上位壓制|侧压|側壓"
)
_REVERSAL_RE = re.compile(
    r"(?i)reversal|reverses?|scramble|bridge|hip escape|counter|switch(?:es)?|"
    r"反转|反轉|逆转|逆轉|桥式|橋式|虾行|蝦行"
)

_WEAPON_RE = re.compile(
    r"(?i)\b(?:sword|knife|blade|gun|pistol|rifle|staff|bat|hammer|weapon)\b|"
    r"剑|劍|刀|枪|槍|棍|棒|锤|錘|武器"
)
_SUPERNATURAL_RE = re.compile(
    r"(?i)\b(?:superpower|magic|spell|telekinesis|giant|kaiju|energy beam|laser beam)\b|"
    r"超能力|魔法|法术|法術|巨人|怪兽|怪獸|能量光束|激光"
)
_GROUND_RE = re.compile(
    r"(?i)\b(?:ground[- ]and[- ]pound|side control|mount|half guard|submission|choke|armbar|"
    r"bridge|hip escape|mat[- ]level|tap(?:s|ped)?)\b|地面|压制|壓制|绞|絞|关节|關節|拍地"
)
_THROW_RE = re.compile(
    r"(?i)\b(?:throw|takedown|hip turn|hip-turn|foot sweep|single[- ]leg|double[- ]leg|slam)\b|"
    r"抱摔|摔投|投技|足扫|足掃|扫摔|掃摔"
)
_GRAPPLE_RE = re.compile(
    r"(?i)\b(?:grapple|clinch|underhook|overhook|whizzer|grip|arm drag|wrist capture)\b|"
    r"擒拿|缠抱|纏抱|抓握|抱腿|锁臂|鎖臂|腕抓"
)
_KICK_RE = re.compile(
    r"(?i)\b(?:kick|knee|shin|foot|leg attack|roundhouse|side kick|oblique)\b|踢|膝|胫|脛|腿"
)
_STRIKE_RE = re.compile(
    r"(?i)\b(?:punch|palm|elbow|forearm|strike|parry|block|trap|uppercut|jab|cross)\b|"
    r"拳|掌|肘|前臂|击|擊|格挡|格擋|招架|截击|截擊"
)
_ACTION_INITIATION_RE = re.compile(
    r"(?i)\b(?:attack|strike|punch|kick|palm|elbow|forearm|jab|cross|uppercut|"
    r"parr(?:y|ies|ied)|block|check|sweep|clinch|grip|capture|throw|takedown|slam|"
    r"drive|redirect|counter|evade|dodge|frame|sprawl|bridge|hip[- ]?escape|"
    r"contact|impact|launch|charges?)\b|"
    r"拳|踢|掌|肘|击|擊|格挡|格擋|招架|闪避|閃避|扫|掃|擒拿|抓握|摔|抱|压制|壓制|反击|反擊"
 )
_OUTCOME_ONLY_RE = re.compile(
    r"(?i)\b(?:lands?\s+(?:on|back)|falls?|is\s+down|lies?|stands?\s+over|"
    r"ends?\s+up|gets?\s+knocked|is\s+thrown|recoils?|is\s+sent|remains?\s+on\s+the\s+ground)\b|"
    r"blood (?:appears|starts|becomes visible)|starts? bleeding|"
    r"倒地|躺下|站在.+上方|被击飞|被擊飛|落地|趴在地上|躺在地上|退到|"
    r"出现血|出現血|开始流血|開始流血"
 )
_GENERIC_ACTION_RE = re.compile(
    r"(?i)already within arm'?s reach.*(?:attack|defence|counter).*exchange|"
    r"combat footwork carries|immediate full-speed attack|brief held moment|"
    r"fighters? hold a tense standoff|looks? directly(?: at)?|raises? (?:his|her|their) "
    r"(?:right |left )?fist|generic (?:attack|defence|combat)|"
    r"(?:continue|continues) (?:its|their) backward trajectory|"
    r"摆出格斗架势|保持对峙|短暂停顿|互相看着|举起拳头"
)
_AFTERMATH_ONLY_RE = re.compile(
    r"(?i)final settle|final hold|aftermath|no new attack|dust settles|"
    r"wind carries|debris (?:falls|settles)|camera (?:settles|holds)|"
    r"余波|尘埃落下|塵埃落下|风沙消散|風沙消散|不再攻击|不再攻擊|最终定格|最終定格"
)

_DUTIES = (
    ("state_pickup", "inherit the exact incoming pose, distance, grip and momentum, then apply immediate pressure"),
    ("escalation", "raise speed or technical complexity with a different attack-response mechanism"),
    ("advantage_shift", "change angle, height, grip or top/bottom advantage through a visible cause"),
    ("environment_consequence", "make one authored contact affect the current material after impact"),
    ("outgoing_relay", "resolve the collision into a precise state that directly launches the next window"),
)

_CAMERA_SECTORS = (
    "front three-quarter eye level",
    "low left-side profile",
    "rear-left shoulder level",
    "high rear oblique",
    "right-side hip level",
    "opposite front three-quarter eye level",
    "low front shin level",
    "left-side shoulder level",
    "rear three-quarter hip level",
    "opposite high oblique",
    "right-side eye level",
    "front three-quarter hip level",
)


def _skill_enabled(value: object) -> bool:
    return str(value or "").strip().casefold() in COMBAT_ACTION_SKILLS


def combat_baseline_duration(plan: dict) -> float:
    """Return authored fight duration, excluding dialogue-only tail extension."""

    actual = max(0.5, float(plan.get("duration_seconds", 0.5) or 0.5))
    try:
        authored = float(plan.get("_speech_timing_base_duration", actual) or actual)
    except (TypeError, ValueError):
        authored = actual
    return min(actual, max(0.5, authored))


def _without_beat_tags(value: object) -> str:
    return " ".join(_BEAT_TAG_RE.sub("", str(value or "")).split()).strip()


def _split_two_beats(value: object) -> list[str]:
    """Split authored choreography without discarding any trailing instruction."""

    text = _without_beat_tags(value)
    if not text:
        return []
    parts = [
        row.strip(" \t\r\n.;；。")
        for row in re.split(r"(?<=[.!?。！？；;])\s+|\n+", text)
        if row.strip(" \t\r\n.;；。")
    ]
    if len(parts) <= 2:
        return parts
    return [parts[0], ". ".join(parts[1:])]


def _first_actor(value: str) -> str:
    match = _ACTOR_RE.search(value)
    return match.group(1).upper() if match else ""


def _opponent(actor: str) -> str:
    return "S2" if actor == "S1" else "S1"


def _replace_first_actor(value: str, actor: str) -> str:
    return _ACTOR_RE.sub(actor, value, count=1)


def _time_tag(beat_number: int, start: float, end: float) -> str:
    return f"[BEAT {beat_number:02d} | {start:.2f}-{end:.2f}s]"


def _compact(value: object, limit: int = 210) -> str:
    text = " ".join(str(value or "").split()).strip(" .")
    if len(text) > limit:
        text = text[: limit - 1].rstrip(" ,;:") + "…"
    return text


def _action_signature(value: object) -> str:
    text = _without_beat_tags(value).casefold()
    return re.sub(r"\bS[12]\b|[^a-z0-9\u3400-\u9fff]+", " ", text).strip()


def _action_was_user_edited(shot: dict) -> bool:
    """Return whether the user owns the current combat choreography text.

    Older projects only persisted ``combat_action_chain_user_edited``.  The
    additional aliases make the repair pass safe for projects created by newer
    Timeline editors without changing their schema.
    """

    return any(
        bool(shot.get(key, False))
        for key in (
            "combat_action_chain_user_edited",
            "subject_action_user_edited",
            "action_user_edited",
        )
    )


def _causal_target_hint(shot: dict, *, source_world_only: bool = False) -> str:
    text = " ".join(
        str(shot.get(key, ""))
        for key in ("environment_interaction", "environment_response", "location_transition")
    ).casefold()
    if source_world_only:
        # Hong Kong comic conversion must never inherit the fixed Kowloon wet-
        # market props used by the live-action Street Fighter profile.  Use
        # only a material visibly established by the source-page fact ledger.
        if any(token in text for token in ("rock", "stone", "cliff", "mountain", "岩", "石", "山")):
            return "the established source-visible rock surface"
        if any(token in text for token in ("water", "river", "sea", "lake", "水", "河", "海", "湖")):
            return "the established source-visible water edge"
        if any(token in text for token in ("wall", "column", "building", "structure", "墙", "牆", "柱", "建筑", "建築")):
            return "the established source-visible structural surface"
        return "the established source-image combat surface"
    if any(token in text for token in ("gate", "latch", "闸", "閘", "门闩", "門閂")):
        return "the loading gate latch"
    if any(token in text for token in ("crate", "produce", "菜箱", "货箱", "貨箱")):
        return "the nearest wet produce crate"
    if any(token in text for token in ("puddle", "wet floor", "水洼", "水窪", "积水", "積水")):
        return "the shallow floor puddle"
    return "the established combat lane"


def _synthesize_distinct_causal_action(
    shot: dict,
    *,
    actor: str,
    previous_action: str,
    source_world_only: bool = False,
) -> str:
    """Create a small, physically staged continuation for a repeated Shot.

    This is deliberately a bounded repair, not a creative rewrite.  It keeps
    the two existing fighters, changes the action carrier from the previous
    exchange and names one visible target when the event chain already has one.
    """

    defender = _opponent(actor)
    previous_carrier, _ = route_action_carrier(previous_action)
    target = _causal_target_hint(shot, source_world_only=source_world_only)
    if target == "the loading gate latch":
        return (
            f"{actor} uses a controlled hip-turn to redirect {defender} toward the loading gate; "
            f"{defender} braces against the latch and the shared momentum opens the route."
        )
    if previous_carrier == "kick":
        return (
            f"{actor} captures {defender}'s wrist and upper arm, turning the checked kick into a close clinch; "
            f"{defender} posts a forearm and pivots to keep balance beside {target}."
        )
    if previous_carrier == "grapple_clinch":
        return (
            f"{actor} changes level into a controlled outside foot sweep against {defender}; "
            f"{defender} hops, releases the grip and regains a guarded base beside {target}."
        )
    if previous_carrier == "throw_takedown":
        return (
            f"{actor} posts a forearm and frames against {defender}'s shoulder to stop the throw follow-through; "
            f"{defender} circles out and re-establishes a standing guard beside {target}."
        )
    if previous_carrier == "ground_control":
        return (
            f"{actor} bridges and hip-escapes from the grounded pressure, turning the bodies toward {target}; "
            f"{defender} follows the rotation and keeps one readable grip without a neutral reset."
        )
    return (
        f"{actor} angles off with a short open-palm entry toward {defender}'s guard; "
        f"{defender} parries outward and shifts one step along the established combat lane."
    )


def _synthesize_high_density_combat_action(
    shot: dict,
    index: int,
    *,
    source_world_only: bool = False,
) -> str:
    """Replace vague fight placeholders with a distinct renderable cause chain."""

    actor = "S1" if index % 2 == 0 else "S2"
    defender = _opponent(actor)
    target = _causal_target_hint(shot, source_world_only=source_world_only)
    exchanges = (
        f"{actor} plants the rear foot and fires a straight lead palm along the centreline; "
        f"{defender} checks the wrist with the outside forearm, slips off-line and drives a compact counter elbow that turns both bodies toward {target}",
        f"{actor} snaps a jab-cross at head and ribs without resetting the feet; "
        f"{defender} parries the jab, absorbs the cross on a tight elbow shield and answers with a rising knee that forces one diagonal recovery step",
        f"{actor} catches the near wrist and collar during the incoming strike, steps hip-to-hip and rotates through a controlled hip throw; "
        f"{defender} posts the free hand, redirects the fall and lands on one knee still facing {actor}",
        f"{actor} attacks the planted lead leg with a low outside kick; "
        f"{defender} shin-checks the kick, drops the checking foot forward and whips a short roundhouse across the opened shoulder line",
        f"{actor} closes into an underhook-and-wrist clinch, loads weight through the hips and drives laterally; "
        f"{defender} widens the base, frames at the jaw and pivots the pressure into a shoulder throw beside {target}",
        f"{actor} launches a body hook from a low level change; "
        f"{defender} seals the ribs with an elbow frame, traps the punching arm and reaps the support foot so the missed force becomes a visible stumble",
        f"{actor} shoots for a single-leg capture after the opponent's forward step; "
        f"{defender} sprawls the hips, circles behind the shoulder and converts the stopped takedown into a standing back-control turn",
        f"{actor} bridges from the grounded pressure and hip-escapes toward {target}; "
        f"{defender} follows the rotation, releases the failing grip and both regain unequal standing guards without a neutral reset",
    )
    return exchanges[index % len(exchanges)] + "."


def _synthesize_ground_reversal(current_action: str, previous_action: str) -> str:
    """Make an implicit top/bottom ownership change explicit."""

    top_actor = _first_actor(current_action) or _first_actor(previous_action) or "S1"
    bottom_actor = _opponent(top_actor)
    return (
        f"{bottom_actor} visibly bridges and hip-escapes to reverse the previous ground position; "
        f"{top_actor} follows the reversal and re-establishes control without a neutral reset."
    )


def _synthesize_outcome_cause_action(
    shot: dict,
    index: int,
    *,
    source_world_only: bool = False,
) -> str:
    """Bridge a model-written result ("S2 lands...") back to its physical cause."""

    attacker = "S1" if index % 2 == 0 else "S2"
    defender = _opponent(attacker)
    target = _causal_target_hint(shot, source_world_only=source_world_only)
    return (
        f"{attacker} catches {defender}'s advancing guard, changes level and completes a controlled "
        f"outside foot sweep into {target}; {defender} loses the support foot, lands on the back along "
        f"the force vector, and {attacker} follows into a readable standing-over position without a reset."
    )


def _media_evidence(row: dict) -> tuple[str, str]:
    raw = str(
        row.get("raw_analysis_summary")
        or row.get("recognition")
        or row.get("analysis_summary")
        or ""
    )
    for pattern in (
        r"^BLIP\s*[·-]?\s*Overview\s*[:：]\s*(.+)$",
        r"^BLIP\s+visual\s+caption\s*[·-]?\s*full\s+frame\s*[:：]\s*(.+)$",
        r"^Overview\s*[:：]\s*(.+)$",
    ):
        match = re.search(pattern, raw, flags=re.I | re.M)
        if match:
            return "blip_overview", _compact(match.group(1), 320)
    enriched = str(row.get("semantic_enrichment") or "").strip()
    if enriched:
        return "ai_enrich", _compact(enriched, 320)
    return "loaded_picture_pixels", "loaded visual reference; descriptive analysis unavailable"


def build_combat_fact_ledger(
    plan: dict,
    existing_media: Iterable[dict] | None = None,
    *,
    authored_requirement: object = "",
    special_skill_key: object = STREET_FIGHTER_SKILL,
) -> dict:
    """Build one provenance-aware fact ledger without letting metadata replace pixels."""

    skill_key = str(special_skill_key or "").strip().casefold()
    inventory: dict[str, dict] = {}
    for row in existing_media or []:
        if not isinstance(row, dict) or not bool(row.get("loaded", False)):
            continue
        media_id = str(row.get("media_id") or "").strip().upper().lstrip("@")
        media_type = str(row.get("media_type") or row.get("type") or "").casefold()
        if media_id in {"P1", "P2"} and media_type == "image":
            inventory[media_id] = row

    bound = {
        str(row.get("media_id") or "").upper().lstrip("@")
        for row in plan.get("existing_media_uses") or []
        if isinstance(row, dict)
    }
    subjects: list[dict] = []
    for speaker, media_id in (("S1", "P1"), ("S2", "P2")):
        if skill_key == HONG_KONG_COMIC_FIGHTER_SKILL:
            subjects.append({
                "speaker": speaker,
                "media_id": "",
                "loaded": False,
                "identity_authority": "explicit_user_direction_and_source_panel_evidence",
                "descriptive_evidence_source": "loaded comic Pictures",
                "description": (
                    "resolve this fighter from explicit names/roles and all source panels; "
                    "P1/P2 numbering does not imply one Picture per fighter"
                ),
                "source_chain": [
                    "explicit_user_direction", "loaded_picture_pixels", "shot_continuity",
                ],
                "locked_attributes": [
                    "face", "apparent_age", "skin_tone", "hair", "body_proportions",
                    "upper_wardrobe", "lower_wardrobe", "footwear", "accessories",
                    "signature_ability",
                ],
            })
            continue
        row = inventory.get(media_id)
        evidence_source, description = _media_evidence(row or {})
        loaded = row is not None
        source_chain = ["special_skill_default"]
        if media_id in bound:
            source_chain.insert(0, "explicit_role_binding")
        if loaded:
            source_chain.insert(0, "loaded_picture_pixels")
            if evidence_source in {"blip_overview", "ai_enrich"}:
                source_chain.append(evidence_source)
        subjects.append({
            "speaker": speaker,
            "media_id": media_id,
            "loaded": loaded,
            "identity_authority": "loaded_picture_pixels" if loaded else "special_skill_default",
            "descriptive_evidence_source": evidence_source,
            "description": description,
            "source_chain": list(dict.fromkeys(source_chain)),
            "locked_attributes": [
                "face", "apparent_age", "skin_tone", "hair", "body_proportions",
                "upper_wardrobe", "lower_wardrobe", "footwear", "accessories",
            ],
        })

    request = _compact(authored_requirement, 500)
    ledger = {
        "schema_version": COMBAT_FACT_LEDGER_SCHEMA_VERSION,
        "authority_order": list(COMBAT_FACT_AUTHORITY),
        "user_direction": request,
        "subjects": subjects,
        "permissions": {
            "weapons": bool(_WEAPON_RE.search(request)),
            "supernatural_carriers": (
                skill_key == HONG_KONG_COMIC_FIGHTER_SKILL
                or bool(_SUPERNATURAL_RE.search(request))
            ),
        },
        "environment": {
            "source": (
                "loaded_picture_pixels"
                if skill_key == HONG_KONG_COMIC_FIGHTER_SKILL
                else "special_skill_default"
            ),
            "value": (
                "derive location, terrain, weather, light and materials from the current comic Pictures"
                if skill_key == HONG_KONG_COMIC_FIGHTER_SKILL
                else "connected Kowloon-style wet seafood and vegetable market to rainy exterior alley"
            ),
        },
        "conflicts": [],
    }
    return ledger


def combat_fact_prompt_context(ledger: dict) -> str:
    subjects = []
    for row in ledger.get("subjects") or []:
        if not isinstance(row, dict):
            continue
        subjects.append(
            f"{row.get('speaker')}={'@' + str(row.get('media_id')) if row.get('loaded') else 'Skill default'}; "
            f"identity authority={row.get('identity_authority')}; description only={row.get('description')}"
        )
    permissions = ledger.get("permissions") or {}
    return _compact(
        "FACT AUTHORITY " + " > ".join(ledger.get("authority_order") or COMBAT_FACT_AUTHORITY)
        + ". " + "; ".join(subjects)
        + f". weapons={'allowed' if permissions.get('weapons') else 'not requested'}"
        + f"; supernatural carriers={'allowed' if permissions.get('supernatural_carriers') else 'not requested'}",
        760,
    )


def combat_story_duty(start_seconds: float, end_seconds: float) -> tuple[int, str, str]:
    midpoint = (max(0.0, start_seconds) + max(start_seconds, end_seconds)) / 2.0
    relative = midpoint % 15.0
    index = min(4, int(relative // 3.0))
    name, instruction = _DUTIES[index]
    return index + 1, name, instruction


def route_action_carrier(value: object, *, permissions: dict | None = None) -> tuple[str, list[str]]:
    """Classify the physical carrier and flag unsupported invention."""

    text = str(value or "")
    permissions = permissions or {}
    warnings: list[str] = []
    if _WEAPON_RE.search(text) and not bool(permissions.get("weapons", False)):
        warnings.append("weapon carrier was not explicitly requested")
    if _SUPERNATURAL_RE.search(text) and not bool(permissions.get("supernatural_carriers", False)):
        warnings.append("supernatural or giant carrier was not explicitly requested")
    if _GROUND_RE.search(text):
        return "ground_control", warnings
    if _THROW_RE.search(text):
        return "throw_takedown", warnings
    if _GRAPPLE_RE.search(text):
        return "grapple_clinch", warnings
    if _KICK_RE.search(text):
        return "kick", warnings
    return "bare_hand_strike", warnings


def infer_force_vector(value: object, *, actor: str = "S1", carrier: str = "") -> dict:
    """Return a coarse screen-space force vector that downstream material rules can obey."""

    text = str(value or "").casefold()
    if re.search(r"\b(?:left|leftward)\b|向左|左侧|左側", text):
        horizontal = "screen-left"
    elif re.search(r"\b(?:right|rightward)\b|向右|右侧|右側", text):
        horizontal = "screen-right"
    else:
        horizontal = "screen-right" if actor == "S1" else "screen-left"
    if re.search(r"\b(?:down|downward|slam|drop|floor|ground)\b|向下|落地|地面|压下|壓下", text):
        vertical = "downward"
    elif re.search(r"\b(?:up|upward|rising|uppercut|lift)\b|向上|上挑|抬起", text):
        vertical = "upward"
    else:
        vertical = "level"
    # Do not confuse anatomical phrases such as "back leg" with a force
    # direction; only explicit retreat/recoil wording changes depth.
    depth = "backward" if re.search(
        r"\b(?:backward|backwards|retreat|recoil|toward the back|back toward)\b|向后|向後|后退|後退",
        text,
    ) else "forward"
    magnitude = "heavy" if carrier in {"throw_takedown", "ground_control"} or re.search(
        r"\b(?:heavy|hard|explosive|slam|driv(?:e|es|en|ing))\b|重击|重擊|爆发|爆發|猛推", text
    ) else "medium"
    return {
        "horizontal": horizontal,
        "vertical": vertical,
        "depth": depth,
        "magnitude": magnitude,
        "label": f"{horizontal}, {vertical}, {depth}",
    }


def _structured_beat(
    text: str,
    beat_id: int,
    *,
    fallback_actor: str,
    permissions: dict,
) -> tuple[dict, list[str]]:
    actor = _first_actor(text) or fallback_actor
    defender = _opponent(actor)
    carrier, warnings = route_action_carrier(text, permissions=permissions)
    force = infer_force_vector(text, actor=actor, carrier=carrier)
    miss = bool(re.search(r"(?i)\b(?:miss|evad|duck|slip|withdraw)\w*\b|闪避|閃避|落空|躲开|躲開", text))
    return {
        "beat_id": beat_id,
        "attacker": actor,
        "defender": defender,
        "carrier": carrier,
        "mechanic": _compact(text, 220),
        "load_weight": "committed body weight" if force["magnitude"] == "heavy" else "balanced body weight",
        "trajectory": force["label"],
        "contact_kind": "visible_miss" if miss else "visible_contact_or_guard_contact",
        "defensive_response": "evade and angle change" if miss else "absorb, parry, frame or redirect visibly",
        "force_vector": force,
        "displacement": f"{defender} displaces {force['label']} while {actor} recovers without resetting",
        "next_trigger": "recoil, grip or displacement becomes the next Beat's load",
    }, warnings


def _dynamic_camera_route(
    carrier: str,
    action: str,
    start_sector: str,
    end_sector: str,
    beat_id: int,
) -> tuple[str, str, str]:
    lowered = action.casefold()
    orbit_direction = "clockwise" if ((beat_id - 1) // 2) % 2 == 0 else "counterclockwise"
    if _REVERSAL_RE.search(lowered):
        relation = "counter"
        motion = f"a tight {orbit_direction} reframe arc around the visible advantage reversal"
    elif carrier == "kick":
        relation = "follow"
        motion = f"a low-to-hip {orbit_direction} lateral FPV arc following the planted foot and kick line"
    elif carrier == "grapple_clinch":
        relation = "follow"
        motion = f"a tight shoulder-height {orbit_direction} FPV arc tracking the grip and torso drive"
    elif carrier == "throw_takedown":
        relation = "counter"
        motion = f"a descending hip-to-floor {orbit_direction} FPV arc countering the throw momentum"
    elif carrier == "ground_control":
        relation = "follow"
        motion = f"a mat-level {orbit_direction} lateral FPV orbit keeping grip and top/bottom ownership readable"
    elif _DEFENCE_RE.search(lowered):
        relation = "counter"
        motion = f"a short {orbit_direction} counter-move into the parry line with one restrained contact shake"
    else:
        relation = "follow"
        motion = f"a shoulder-height {orbit_direction} lateral FPV pass following the strike line"
    trigger = f"BEAT {beat_id:02d} load starts the move; contact or visible miss completes it"
    direction = (
        f"physical FPV {orbit_direction} orbital translation: {motion}, physically translating from {start_sector} to {end_sector}; {trigger}. "
        "Maintain close subject scale, visible parallax and a readable horizon; no lens retreat or in-place rotation."
    )
    return relation, trigger, direction


def _state_text(vector: dict) -> str:
    return "; ".join(f"{key}={value}" for key, value in vector.items())


def _synthesize_allowed_carrier_action(
    shot: dict,
    actor: str,
    previous_action: str,
    *,
    source_world_only: bool = False,
) -> str:
    """Replace an unrequested fantasy/weapon carrier with bounded physical choreography."""

    return _synthesize_distinct_causal_action(
        shot,
        actor=actor,
        previous_action=previous_action or "standing bare-hand exchange",
        source_world_only=source_world_only,
    )


def _stable_final_resolution(result_actor: str, carrier: str) -> str:
    defender = _opponent(result_actor)
    if carrier in {"ground_control", "throw_takedown"}:
        return (
            f"{result_actor} completes the current control and settles on a planted kneeling base; "
            f"{defender} completes the displacement into a stable guarded recovery on the same support "
            "surface. Both stop changing position; no new strike, submission or reset begins"
        )
    return (
        f"{result_actor} completes the current recoil into a planted guard while {defender} finishes "
        "the caused displacement and braces in a stable guarded stance. Both stop changing position; "
        "no new attack, exit movement or pose reset begins"
    )


def _causal_validation_issues(
    structured_beats: list[dict],
    incoming_vector: dict,
    previous_outgoing_vector: dict | None,
    *,
    camera_trigger: str,
) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    for beat in structured_beats:
        missing = [field for field in _REQUIRED_BEAT_FIELDS if not beat.get(field)]
        if missing:
            issues.append(
                f"BEAT {int(beat.get('beat_id', 0)):02d} lacks " + ", ".join(missing)
            )
        if str(beat.get("carrier", "")) not in _ALLOWED_ACTION_CARRIERS:
            issues.append(f"unsupported action carrier {beat.get('carrier')}")
    inherited: list[str] = []
    if previous_outgoing_vector:
        inherited = [
            key for key in _STATE_RELAY_KEYS
            if key in incoming_vector
            and key in previous_outgoing_vector
            and incoming_vector.get(key) == previous_outgoing_vector.get(key)
        ]
        if len(inherited) < 4:
            issues.append(
                "next Shot inherits fewer than four state fields from the preceding outgoing state"
            )
    if "BEAT" not in str(camera_trigger or "").upper():
        issues.append("camera move is not bound to a concrete Beat")
    return issues, inherited


def reconcile_final_combat_markers(
    markers: Iterable[dict], duration_seconds: object
) -> list[dict]:
    """Migrate legacy active-through-last-frame markers to a stable resolution."""

    duration = max(0.5, float(duration_seconds or 0.5))
    result = [deepcopy(row) for row in markers if isinstance(row, dict)]
    final_rows: list[dict] = []
    for marker in result:
        marker_text = " ".join(
            (str(marker.get("preset", "")), str(marker.get("direction", "")))
        ).casefold()
        if any(token in marker_text for token in ("final", "ending", "terminal", "最后", "最終")):
            final_rows.append(marker)
    if not final_rows:
        final_rows.append({
            "time_seconds": round(max(0.0, duration - 1.0) * 2.0) / 2.0,
        })
        result.append(final_rows[0])
    for marker in final_rows:
        # A Final Combat Resolve cue is a tail-state instruction, not a story
        # event that should remain at its pre-speech-expansion timestamp.
        marker["time_seconds"] = round(max(0.0, duration - 1.0) * 2.0) / 2.0
        marker["preset"] = "Final Combat Resolve"
        marker["direction"] = (
            "Complete the final authored technique at real-time speed, show recoil and caused "
            "displacement, then settle both fighters on readable support while the physical FPV "
            "camera decelerates into a stable eye-level three-quarter composition through the last frame."
        )
    return result


def reconcile_combat_action_rows(
    rows: Iterable[dict],
    duration_seconds: object,
    *,
    action_baseline_seconds: object | None = None,
    fact_ledger: dict | None = None,
    auto_repair: bool = True,
    source_world_only: bool = False,
) -> tuple[list[dict], list[str]]:
    """Number action beats and relay fighter state across chronological Shots.

    Known, deterministic causal defects are repaired by default.  User-edited
    choreography remains authoritative and is reported instead of being
    silently rewritten.
    """

    duration = max(0.5, float(duration_seconds or 0.5))
    baseline = min(
        duration,
        max(0.5, float(duration if action_baseline_seconds is None else action_baseline_seconds)),
    )
    raw_rows = [deepcopy(row) for row in rows if isinstance(row, dict)]
    shots = sorted(
        raw_rows,
        key=lambda row: (
            float(row.get("start_seconds", 0.0) or 0.0),
            float(row.get("end_seconds", 0.0) or 0.0),
            str(row.get("id") or row.get("cue_id") or ""),
        ),
    )
    warnings: list[str] = []
    fact_ledger = fact_ledger or {
        "authority_order": list(COMBAT_FACT_AUTHORITY),
        "subjects": [],
        "permissions": {"weapons": False, "supernatural_carriers": False},
    }
    fact_context = combat_fact_prompt_context(fact_ledger)
    if not fact_ledger.get("subjects"):
        inherited_context = next(
            (
                str(row.get("combat_fact_context", "")).strip()
                for row in raw_rows
                if str(row.get("combat_fact_context", "")).strip()
            ),
            "",
        )
        if inherited_context:
            fact_context = inherited_context
    permissions = fact_ledger.get("permissions") or {}
    previous_outgoing = ""
    previous_outgoing_vector: dict | None = None
    previous_signature = ""
    previous_action = ""
    previous_camera_sector = _CAMERA_SECTORS[0]
    beat_number = 1

    for index, shot in enumerate(shots):
        shot_id = str(shot.get("id") or shot.get("cue_id") or f"Shot {index + 1}")
        start = max(0.0, float(shot.get("start_seconds", 0.0) or 0.0))
        end = min(duration, max(start + 0.05, float(shot.get("end_seconds", start + 0.5) or start + 0.5)))
        action_end = min(end, baseline) if start < baseline else end
        midpoint = start + (action_end - start) / 2.0
        raw_action = _without_beat_tags(shot.get("subject_action", ""))
        if (
            raw_action
            and _GENERIC_ACTION_RE.search(raw_action)
            and not _AFTERMATH_ONLY_RE.search(raw_action)
            and auto_repair
            and not _action_was_user_edited(shot)
        ):
            shot["causal_risk_original_action"] = raw_action
            raw_action = _synthesize_high_density_combat_action(
                shot, index, source_world_only=source_world_only
            )
            shot["causal_risk_repair_status"] = "auto_fixed"
            shot["causal_risk_repair_notes"] = (
                "Replaced a vague pose/standoff/generic exchange with one concrete load, "
                "attack line, defence, contact response and displacement chain."
            )
        beats = _split_two_beats(raw_action)
        status = "continuous"
        notes: list[str] = []

        if shot.get("causal_risk_repair_status") == "auto_fixed":
            status = "auto_fixed"
            notes.append("replaced generic choreography with a distinct causal exchange")

        if not beats:
            beats = [
                "S1 initiates one committed close-range attack toward S2",
                "S2 visibly defends and immediately redirects the resulting momentum",
            ]
            status = "auto_fixed"
            notes.append("missing choreography replaced by one attack-response exchange")
        elif len(beats) == 1:
            attacker = _first_actor(beats[0]) or ("S1" if index % 2 == 0 else "S2")
            defender = _opponent(attacker)
            beats.append(
                f"{defender} visibly absorbs, evades or redirects that exact attack and remains engaged"
            )
            status = "auto_fixed"
            notes.append("missing defender response was added")

        # A common H3 failure is to emit only the result of a strike (for
        # example, "S2 lands on his back; S1 stands over him").  That result
        # has no renderable contact, force vector or environment trigger, so
        # rebuild one bounded cause chain unless the user explicitly owns the
        # choreography.  This keeps the later effects causal instead of
        # making the model merely enlarge a still frame.
        joined_beats = " ".join(beats)
        if (
            _OUTCOME_ONLY_RE.search(joined_beats)
            and not _ACTION_INITIATION_RE.search(joined_beats)
        ):
            if auto_repair and not _action_was_user_edited(shot):
                original_action = joined_beats
                repaired_action = _synthesize_outcome_cause_action(
                    shot, index, source_world_only=source_world_only
                )
                shot["causal_risk_original_action"] = original_action
                shot["causal_risk_repair_status"] = "auto_fixed"
                shot["causal_risk_repair_notes"] = (
                    "Inserted the missing initiation, contact, force direction and displacement "
                    "before the authored outcome-only landing/standing result."
                )
                beats = _split_two_beats(repaired_action)
                status = "auto_fixed"
                notes.append("inserted a physical cause before an outcome-only action")
            else:
                status = "warning"
                notes.append("outcome-only action has no explicit initiating contact")

        attacker = _first_actor(beats[0]) or ("S1" if index % 2 == 0 else "S2")
        response_actor = _first_actor(beats[1])
        if response_actor == attacker and _DEFENCE_RE.search(beats[1]):
            opponent = _opponent(attacker)
            if not re.search(rf"\b{opponent}\b", beats[1], flags=re.I):
                if _SAFE_ACTOR_FIX_RE.search(beats[1]):
                    beats[1] = _replace_first_actor(beats[1], opponent)
                    status = "auto_fixed"
                    notes.append("clear self-defence actor was corrected to the opponent")
                else:
                    status = "warning"
                    notes.append("possible self-response needs an explicit opponent attack or actor correction")

        current_action = " ".join(beats)
        if (
            previous_action
            and _GROUND_CAPTURE_RE.search(previous_action)
            and _TOP_CONTROL_RE.search(current_action)
            and not _REVERSAL_RE.search(current_action)
        ):
            if auto_repair and not _action_was_user_edited(shot):
                original_action = current_action
                repaired_action = _synthesize_ground_reversal(
                    current_action,
                    previous_action,
                )
                shot["causal_risk_original_action"] = original_action
                shot["causal_risk_repair_status"] = "auto_fixed"
                shot["causal_risk_repair_notes"] = (
                    "Inserted an explicit bridge/hip-escape reversal before the ownership change."
                )
                beats = _split_two_beats(repaired_action)
                current_action = " ".join(beats)
                attacker = _first_actor(beats[0]) or attacker
                status = "auto_fixed"
                notes.append("inserted an explicit ground reversal to preserve top/bottom ownership")
            else:
                status = "warning"
                notes.append("ground-control ownership changes without an explicit reversal")

        signature = _action_signature(current_action)
        if signature and signature == previous_signature:
            if auto_repair and not _action_was_user_edited(shot):
                original_action = current_action
                repaired_action = _synthesize_distinct_causal_action(
                    shot,
                    actor=attacker,
                    previous_action=previous_action,
                    source_world_only=source_world_only,
                )
                repaired_signature = _action_signature(repaired_action)
                if repaired_signature and repaired_signature != previous_signature:
                    shot["causal_risk_original_action"] = original_action
                    shot["causal_risk_repair_status"] = "auto_fixed"
                    shot["causal_risk_repair_notes"] = (
                        "Replaced a repeated action with a distinct causal continuation while preserving actors and direction."
                    )
                    beats = _split_two_beats(repaired_action)
                    current_action = " ".join(beats)
                    signature = repaired_signature
                    attacker = _first_actor(beats[0]) or attacker
                    status = "auto_fixed"
                    notes.append("replaced repeated action with a distinct causal continuation")
                else:
                    status = "warning"
                    notes.append("action exchange repeats the preceding Shot")
            else:
                status = "warning"
                notes.append("action exchange repeats the preceding Shot")

        # The model sometimes leaves a one-line action with an actor omitted
        # after a repair.  Recompute the response actor only after all repairs
        # so the next Beat cannot accidentally assign a fighter to herself.
        response_actor = _first_actor(beats[1])

        duty_index, duty_name, duty_instruction = combat_story_duty(start, action_end)
        structured_beats: list[dict] = []
        carrier_warnings: list[str] = []
        for beat_offset, beat_text in enumerate(beats[:2]):
            fallback_actor = attacker if beat_offset == 0 else _opponent(attacker)
            structured, routed_warnings = _structured_beat(
                beat_text,
                beat_number + beat_offset,
                fallback_actor=fallback_actor,
                permissions=permissions,
            )
            structured_beats.append(structured)
            carrier_warnings.extend(routed_warnings)
        if carrier_warnings:
            if auto_repair and not _action_was_user_edited(shot):
                original_action = current_action
                repaired_action = _synthesize_allowed_carrier_action(
                    shot,
                    attacker,
                    previous_action,
                    source_world_only=source_world_only,
                )
                beats = _split_two_beats(repaired_action)
                current_action = " ".join(beats)
                signature = _action_signature(current_action)
                attacker = _first_actor(beats[0]) or attacker
                structured_beats = []
                remaining_warnings: list[str] = []
                for beat_offset, beat_text in enumerate(beats[:2]):
                    fallback_actor = attacker if beat_offset == 0 else _opponent(attacker)
                    structured, routed_warnings = _structured_beat(
                        beat_text,
                        beat_number + beat_offset,
                        fallback_actor=fallback_actor,
                        permissions=permissions,
                    )
                    structured_beats.append(structured)
                    remaining_warnings.extend(routed_warnings)
                shot["causal_risk_original_action"] = original_action
                shot["causal_risk_repair_status"] = "auto_fixed"
                shot["causal_risk_repair_notes"] = (
                    "Replaced an unrequested weapon, giant-object or supernatural carrier with "
                    "an allowed bare-hand, kick, grapple, throw or ground continuation."
                )
                if remaining_warnings:
                    status = "warning"
                    notes.extend(dict.fromkeys(remaining_warnings))
                else:
                    status = "auto_fixed"
                    notes.append("routed an unrequested carrier back to allowed physical combat")
            else:
                status = "warning"
                notes.extend(dict.fromkeys(carrier_warnings))

        primary_beat = structured_beats[0]
        result_beat = structured_beats[-1]
        carrier = str(primary_beat["carrier"])
        force_vector = dict(result_beat["force_vector"])
        next_sector = _CAMERA_SECTORS[(index + 1) % len(_CAMERA_SECTORS)]
        motion_relation, camera_trigger, camera_direction = _dynamic_camera_route(
            carrier,
            current_action,
            previous_camera_sector,
            next_sector,
            beat_number,
        )

        is_final_shot = index == len(shots) - 1
        if is_final_shot:
            settle_duration = min(1.0, max(0.25, (action_end - start) * 0.25))
            settle_start = max(start + 0.1, action_end - settle_duration)
            action_midpoint = start + max(0.05, settle_start - start) / 2.0
        else:
            settle_start = action_end
            action_midpoint = midpoint
        labelled = (
            f"{_time_tag(beat_number, start, action_midpoint)} {beats[0].rstrip(' .')}. "
            f"{_time_tag(beat_number + 1, action_midpoint, settle_start)} {beats[1].rstrip(' .')}."
        )
        incoming_vector = deepcopy(previous_outgoing_vector) if previous_outgoing_vector else {
            "positions": "S1 screen-left and S2 screen-right at arm's reach",
            "facing": "S1 and S2 face each other on the established combat axis",
            "velocity": "both already moving inside the exchange",
            "support": "both have one readable planted support foot",
            "guard_or_grip": "separate live guards; no unexplained grip",
            "advantage": "contested",
            "environment_aftermath": (
                "established source-image terrain and visible materials unchanged"
                if source_world_only else "established wet floor and fixtures unchanged"
            ),
            "wetness_damage": (
                "preserve only source-visible weathering, damage and non-graphic contact marks"
                if source_world_only else
                "preserve existing sweat, wetness and visible non-graphic contact marks"
            ),
        }
        result_actor = str(result_beat.get("attacker") or _opponent(attacker))
        outgoing_vector = {
            "positions": str(result_beat.get("displacement")),
            "facing": f"{attacker} and {_opponent(attacker)} remain mutually oriented after the angle change",
            "velocity": str(force_vector.get("label")),
            "support": (
                "one fighter low/grounded and the other base remains readable"
                if carrier in {"throw_takedown", "ground_control"}
                else "support foot and recovery step remain visible"
            ),
            "guard_or_grip": (
                f"{attacker} retains the authored grip until visibly released"
                if carrier in {"grapple_clinch", "throw_takedown", "ground_control"}
                else "guard recovers from the visible contact line"
            ),
            "advantage": f"temporary initiative={result_actor}; no unexplained ownership swap",
            "environment_aftermath": "pending the exact contact consequence assigned to this Shot",
            "wetness_damage": (
                "carry only source-visible weathering, damage and contact marks into the next Beat"
                if source_world_only else
                "carry visible sweat, wetness and contact marks into the next Beat"
            ),
        }
        incoming = previous_outgoing or _state_text(incoming_vector)
        outgoing = _state_text(outgoing_vector)
        next_trigger = (
            f"The displacement, recoil, grip or failed defence from BEAT {beat_number + 1:02d} "
            f"directly triggers BEAT {beat_number + 2:02d}; camera movement follows that action cause."
        )

        event_chain = (
            f"EVENT CAUSE: {attacker} initiates {carrier}; "
            f"EVENT RESPONSE: {result_beat.get('defender')} visibly responds; "
            f"EVENT CONSEQUENCE: {result_beat.get('displacement')}; "
            f"NEXT EVENT: BEAT {beat_number + 2:02d} starts from this state."
        )
        physical_feedback = (
            f"PHYSICAL FEEDBACK: force travels {force_vector.get('label')} with "
            f"{force_vector.get('magnitude')} magnitude; only a visible contact can affect the environment."
        )

        final_action_resolution = ""
        final_camera_resolution = ""
        if is_final_shot:
            final_action_resolution = _stable_final_resolution(result_actor, carrier)
            final_camera_resolution = (
                "After the final contact and recoil are complete, decelerate the physical FPV orbit "
                "and settle into one stable eye-level three-quarter composition with a level horizon "
                "for the last 0.75-1.00 second; no zoom, in-place spin, replay or slow motion."
            )
            labelled += (
                f" [FINAL SETTLE | {settle_start:.2f}-{action_end:.2f}s] "
                f"{final_action_resolution}."
            )
            outgoing_vector["velocity"] = "settled; no further displacement after final recovery"
            outgoing_vector["support"] = "both final support states are planted and readable"
            outgoing_vector["advantage"] = (
                f"resolved final initiative={result_actor}; no new exchange begins"
            )
            outgoing = _state_text(outgoing_vector)
            next_trigger = (
                "FINAL RESOLUTION: no next Beat; preserve the completed contact, settled support, "
                "fighter orientation and environment aftermath through the last frame."
            )
            camera_trigger = (
                f"BEAT {beat_number:02d} initiates the camera move; BEAT {beat_number + 1:02d} contact "
                "completes it; FINAL SETTLE begins only "
                "after recoil and displacement finish"
            )
            camera_direction = camera_direction.rstrip(" .") + ". " + final_camera_resolution
            event_chain = (
                f"EVENT CAUSE: {attacker} initiates {carrier}; "
                f"EVENT RESPONSE: {result_beat.get('defender')} visibly responds; "
                f"EVENT CONSEQUENCE: {result_beat.get('displacement')}; "
                "FINAL EVENT: momentum visibly dissipates into one stable supported end state."
            )

        validation_issues, inherited_fields = _causal_validation_issues(
            structured_beats,
            incoming_vector,
            previous_outgoing_vector,
            camera_trigger=camera_trigger,
        )
        if status == "warning":
            validation_issues.extend(note for note in notes if note not in validation_issues)
        causal_validation_status = (
            "warning" if validation_issues
            else "auto_fixed" if status == "auto_fixed" or shot.get("causal_risk_repair_status") == "auto_fixed"
            else "continuous"
        )

        if not bool(shot.get("combat_action_chain_user_edited", False)):
            shot["combat_action_chain"] = labelled
            shot["subject_action"] = labelled
            # The Timeline compiler prefers h3_executable_action when present;
            # keep the normalized chain authoritative in the real render path.
            shot["h3_executable_action"] = labelled
        if not bool(shot.get("incoming_combat_state_user_edited", False)):
            shot["incoming_combat_state"] = incoming
        if not bool(shot.get("outgoing_combat_state_user_edited", False)):
            shot["outgoing_combat_state"] = outgoing
        if not bool(shot.get("next_action_trigger_user_edited", False)):
            shot["next_action_trigger"] = next_trigger
        shot["event_causality_chain"] = event_chain
        shot["physical_feedback_chain"] = physical_feedback
        shot["combat_fact_context"] = fact_context
        shot["combat_story_duty_index"] = duty_index
        shot["combat_story_duty"] = duty_name
        shot["combat_story_duty_instruction"] = duty_instruction
        shot["combat_action_beats"] = structured_beats
        shot["combat_action_carrier"] = carrier
        shot["combat_force_vector"] = force_vector
        shot["incoming_combat_state_vector"] = incoming_vector
        shot["outgoing_combat_state_vector"] = outgoing_vector
        shot["camera_position_sector"] = f"{previous_camera_sector} -> {next_sector}"
        shot["camera_motion_relation"] = motion_relation
        shot["camera_action_trigger"] = camera_trigger
        shot["dynamic_camera_direction"] = camera_direction
        shot["camera_movement"] = camera_direction
        shot["movement_speed"] = "Very fast"
        shot["movement_amplitude"] = "Large"
        shot["combat_continuity_status"] = status
        shot["combat_continuity_notes"] = "; ".join(notes)
        shot["causal_validation_status"] = causal_validation_status
        shot["causal_validation_issues"] = validation_issues
        shot["causal_validation_inherited_fields"] = inherited_fields
        shot["final_action_resolution"] = final_action_resolution
        shot["final_camera_resolution"] = final_camera_resolution
        shot["final_action_stable"] = is_final_shot and not validation_issues
        shot["combat_action_schema_version"] = COMBAT_ACTION_SCHEMA_VERSION

        if notes:
            warnings.append(f"{shot_id} combat continuity {status}: " + "; ".join(notes) + ".")
        previous_outgoing = str(shot.get("outgoing_combat_state", outgoing)).strip()
        previous_outgoing_vector = deepcopy(outgoing_vector)
        previous_signature = signature
        previous_action = current_action
        previous_camera_sector = next_sector
        beat_number += 2

    return shots, warnings


def apply_combat_action_continuity(
    plan: dict,
    *,
    special_skill_key: object,
    existing_media: Iterable[dict] | None = None,
    authored_requirement: object = "",
) -> dict:
    """Apply the shared causal combat pass to supported fight-director Skills."""

    if not _skill_enabled(special_skill_key):
        return plan
    baseline = combat_baseline_duration(plan)
    existing_ledger = plan.get("combat_fact_ledger")
    if isinstance(existing_ledger, dict) and bool(existing_ledger.get("user_edited", False)):
        fact_ledger = deepcopy(existing_ledger)
    else:
        fact_ledger = build_combat_fact_ledger(
            plan,
            existing_media,
            authored_requirement=authored_requirement,
            special_skill_key=special_skill_key,
        )
    source_shots = [
        deepcopy(row) for row in plan.get("shots") or [] if isinstance(row, dict)
    ]
    active_shots = [
        row for row in source_shots
        if float(row.get("start_seconds", 0.0) or 0.0) < baseline - 1e-6
    ]
    speech_tail_shots = [
        row for row in source_shots
        if float(row.get("start_seconds", 0.0) or 0.0) >= baseline - 1e-6
    ]
    shots, warnings = reconcile_combat_action_rows(
        active_shots,
        plan.get("duration_seconds", baseline),
        action_baseline_seconds=baseline,
        fact_ledger=fact_ledger,
        source_world_only=(
            str(special_skill_key or "").strip().casefold()
            == HONG_KONG_COMIC_FIGHTER_SKILL
        ),
    )
    if speech_tail_shots:
        last_state = str(
            shots[-1].get("outgoing_combat_state", "") if shots else ""
        ).strip()
        last_vector = deepcopy(
            shots[-1].get("outgoing_combat_state_vector", {}) if shots else {}
        )
        for tail in speech_tail_shots:
            inherited = last_state or (
                "Both fighters preserve the completed final contact, readable support, "
                "screen orientation and persistent environmental aftermath."
            )
            settle = (
                "No new attack begins. Both fighters hold the completed causal end state while "
                "dust, debris, wind and light reactions decay naturally behind the remaining speech."
            )
            if not _action_was_user_edited(tail):
                tail["subject_action"] = settle
                tail["h3_executable_action"] = settle
                tail["combat_action_chain"] = settle
            tail["incoming_combat_state"] = inherited
            tail["outgoing_combat_state"] = inherited
            tail["incoming_combat_state_vector"] = deepcopy(last_vector)
            tail["outgoing_combat_state_vector"] = deepcopy(last_vector)
            tail["next_action_trigger"] = "FINAL RESOLUTION: no next Beat and no replay."
            tail["camera_movement"] = (
                "Stable eye-level three-quarter hold with a level horizon; no zoom, pull-back, "
                "orbit, in-place spin or slow motion."
            )
            tail["movement_speed"] = "Settled"
            tail["movement_amplitude"] = "None"
            tail["combat_continuity_status"] = "speech_tail_hold"
            tail["causal_validation_status"] = "continuous"
            tail["causal_validation_issues"] = []
            tail["final_action_resolution"] = settle
            tail["final_camera_resolution"] = tail["camera_movement"]
            tail["final_action_stable"] = True
            tail["combat_action_schema_version"] = COMBAT_ACTION_SCHEMA_VERSION
        shots.extend(speech_tail_shots)
        shots.sort(key=lambda row: float(row.get("start_seconds", 0.0) or 0.0))
        warnings.append(
            "Dialogue-only duration extension preserves the completed combat end state; "
            "no synthetic attack Beat is added after the authored action baseline."
        )
    plan["shots"] = shots
    plan["markers"] = reconcile_final_combat_markers(
        plan.get("markers") or [], plan.get("duration_seconds", baseline)
    )
    plan["combat_fact_ledger"] = fact_ledger
    plan["combat_fact_ledger_schema_version"] = COMBAT_FACT_LEDGER_SCHEMA_VERSION
    plan["combat_action_schema_version"] = COMBAT_ACTION_SCHEMA_VERSION
    plan["combat_baseline_duration_seconds"] = baseline
    constraints = str(plan.get("constraints", "")).strip()
    for contract in (
        FACT_LEDGER_CONTRACT,
        FIVE_DUTY_CONTRACT,
        ACTION_CARRIER_CONTRACT,
        DYNAMIC_CAMERA_CONTRACT,
        ACTION_CAUSALITY_CONTRACT,
        CAUSAL_VALIDATION_CONTRACT,
        FINAL_COMBAT_RESOLUTION_CONTRACT,
    ):
        if contract.split(":", 1)[0].casefold() not in constraints.casefold():
            constraints = constraints.rstrip(" .") + (". " if constraints else "") + contract
    plan["constraints"] = constraints

    counts: dict[int, int] = {}
    for row in shots:
        start = max(0.0, float(row.get("start_seconds", 0.0) or 0.0))
        if start >= baseline - 1e-6:
            continue
        segment = max(0, int(start // 15.0))
        counts[segment] = counts.get(segment, 0) + 2
    for segment, count in sorted(counts.items()):
        segment_start = segment * 15.0
        if segment_start >= baseline:
            continue
        expected = 12
        if count != expected:
            warnings.append(
                f"Combat density risk at {segment_start:.2f}-{min(baseline, segment_start + 15.0):.2f}s: "
                f"{count} executable beats are present; the stable target is {expected}."
            )

    notices = [str(value) for value in plan.get("design_warnings") or []]
    notices.extend(warnings)
    active = (
        "Combat Action Continuity v3 is active: authority-ranked facts, five duties, routed action "
        "carriers, action-triggered camera motion, force vectors, silent causal validation and a stable final resolution are compiled into H3 prompts."
    )
    if active not in notices:
        notices.append(active)
    plan["design_warnings"] = list(dict.fromkeys(notices))
    return plan


def combat_action_prompt_clause(row: dict) -> str:
    """Render only Shot-local combat deltas; global Skill invariants stay Segment-level."""

    if not isinstance(row, dict) or not int(row.get("combat_action_schema_version", 0) or 0):
        return ""
    parts = [
        "FACT LEDGER - " + _compact(row.get("combat_fact_context", ""), 760),
        "STORY DUTY - " + _compact(
            f"{row.get('combat_story_duty', '')}: {row.get('combat_story_duty_instruction', '')}", 300
        ),
        "ACTION CARRIER - " + _compact(row.get("combat_action_carrier", ""), 80),
        "ACTION STATUS - " + _compact(
            f"{row.get('combat_continuity_status', '')}: {row.get('combat_continuity_notes', '')}", 260
        ),
        "FORCE VECTOR - " + _compact((row.get("combat_force_vector") or {}).get("label", ""), 120),
        "ACTION-TRIGGERED CAMERA - " + _compact(row.get("dynamic_camera_direction", ""), 480),
        "INCOMING COMBAT STATE - " + _compact(row.get("incoming_combat_state", ""), 300),
        "OUTGOING COMBAT STATE - " + _compact(row.get("outgoing_combat_state", ""), 300),
        "NEXT ACTION TRIGGER - " + _compact(row.get("next_action_trigger", ""), 260),
        "EVENT CAUSALITY - " + _compact(row.get("event_causality_chain", ""), 360),
        "PHYSICAL FEEDBACK - " + _compact(row.get("physical_feedback_chain", ""), 260),
        "CAUSAL QC - " + _compact(
            f"{row.get('causal_validation_status', '')}: "
            + "; ".join(str(value) for value in row.get("causal_validation_issues") or []),
            300,
        ),
        "FINAL ACTION RESOLUTION - " + _compact(row.get("final_action_resolution", ""), 360),
        "FINAL CAMERA RESOLUTION - " + _compact(row.get("final_camera_resolution", ""), 360),
    ]
    return " ".join(part for part in parts if not part.endswith(" - "))


_ENGINE_LINE_PREFIXES = ("[ENV-PHYSICS]", "[ENV-IN]", "[ENV-OUT]", "[LOCATION]")
_CAST_LOCK_SENTENCE_RE = re.compile(r"(?is)CAST REFERENCE LOCK:[^.]*\.")


def compact_street_fighter_prompt_field(
    value: object,
    *,
    global_contracts: Iterable[str] = (),
) -> str:
    """Remove engine-owned duplicate prose before assembling a Segment prompt.

    The original Timeline fields stay intact and editable.  Only the compiled
    prompt copy is compacted; one global contract remains in the Segment-level
    constraints and each Shot receives its own explicit state clause.
    """

    rows = [
        row for row in str(value or "").splitlines()
        if not row.strip().startswith(_ENGINE_LINE_PREFIXES)
    ]
    text = "\n".join(rows).strip()
    # Environment/action engines also store editable state as inline labelled
    # clauses in legacy projects.  Those clauses are emitted once by the
    # dedicated compact prompt builders below; keeping the editable copy here
    # multiplied a 15-second H3 prompt into tens of thousands of characters.
    text = re.sub(
        r"(?is)\[(?:ENV-PHYSICS|ENV-IN|ENV-OUT|LOCATION)\]\s*.*?"
        r"(?=\[(?:ENV-PHYSICS|ENV-IN|ENV-OUT|LOCATION)\]|$)",
        " ",
        text,
    )
    for contract in global_contracts:
        text = text.replace(str(contract or ""), "")
    text = _CAST_LOCK_SENTENCE_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" .\n")
    # Full facts remain editable on the Timeline.  The H3 generation copy uses
    # the beginning plus tail so it retains the authored action and any final
    # prohibition without drowning exact dialogue/native-audio instructions.
    if len(text) > 1200:
        text = text[:850].rstrip(" ,;:") + " … " + text[-320:].lstrip()
    return text

"""Deterministic Making-of / VFX Breakdown / 4DX planning helpers.

The engine plans visible physical causes for MiniMax H3 and keeps the resulting
4DX device intents as separate, editable project data.  It never treats camera
motion as seat motion and never adds a post-production audio/effect chain.
"""

from __future__ import annotations

from copy import deepcopy
import re


AI_MOVIE_MAKING_OF_4DX_SKILL = "ai-movie-making-of-4dx"
FOURDX_SCHEMA_VERSION = 3
FOURDX_REQUIREMENT_BEGIN = "4DX EXPERIENCE CONTROL"
FOURDX_REQUIREMENT_END = "END 4DX EXPERIENCE CONTROL"

FOURDX_EFFECTS = (
    ("pitch", "PITCH", "前后倾斜 / acceleration, braking and steep elevation change"),
    ("roll", "ROLL", "左右倾斜 / lateral force and banking"),
    ("heave", "HEAVE", "垂直升降 / lift, fall and landing"),
    ("wind", "WIND", "持续风 / speed, storm and pressure wave"),
    ("air_shot", "AIR SHOT", "瞬时喷气 / near-miss and directed burst"),
    ("vibration", "VIBRATION", "连续震动 / machinery, collapse and rumble"),
    ("impact", "IMPACT", "背部冲击 / collision, hit and explosion"),
    ("flash", "FLASH", "闪光 / lightning, ignition and energy release"),
    ("fog_smoke", "FOG / SMOKE", "烟雾 / fire, dust and atmosphere"),
    ("water_rain", "WATER / RAIN", "水雨 / rain, spray and splash"),
)
FOURDX_EFFECT_IDS = tuple(item[0] for item in FOURDX_EFFECTS)
FOURDX_EFFECT_LABELS = {item[0]: item[1] for item in FOURDX_EFFECTS}
FOURDX_EFFECT_DESCRIPTIONS = {item[0]: item[2] for item in FOURDX_EFFECTS}
FOURDX_BASE_DURATION_SECONDS = 15.0
FOURDX_ADDITIONAL_EFFECT_SECONDS = 5.0

_DEFAULT_SELECTED = FOURDX_EFFECT_IDS
_LEVELS = {"low", "medium", "high"}
_DENSITIES = {"sparse", "balanced", "dense"}

_SHOWCASE_EFFECTS = {
    "pitch": {
        "chapter": "PITCH · FIGHTER-JET TAKEOFF",
        "practical": "A full-size cockpit section sits on a forward-and-back motion gimbal while wind machines spool up beside a runway set.",
        "final": "Match-cut to an original carrier fighter accelerating, lifting from the deck and entering one steep controlled climb; the horizon and aircraft geometry remain coherent.",
        "camera": "Rigid cockpit-adjacent tracking camera; acceleration and climb are visible, but camera motion is not the physical-event source.",
        "cause": "engine thrust accelerates the aircraft and changes its elevation",
        "response": "pilot and loose straps load backward during acceleration, then downward during the climb",
        "device": "seat pitches backward for acceleration and forward during the dive/braking demonstration",
        "audio": "turbine spool, deck rumble, rushing wind and one clean transition into flight",
        "voice": "俯仰：加速与爬升带动前后倾。",
    },
    "roll": {
        "chapter": "ROLL · HIGH-SPEED CORNER",
        "practical": "A rain-soaked rally-car cabin is mounted on a lateral roll rig while tyre and wet-road plates are aligned behind it.",
        "final": "Match-cut to the same original rally car entering one fast mountain hairpin, gripping, drifting laterally and recovering without overturning.",
        "camera": "Low lateral tracking shot that preserves the road axis and shows the car's sideways force clearly.",
        "cause": "the car changes direction sharply through a wet high-speed corner",
        "response": "suspension compresses, tyres spray water outward and occupants load toward the outside of the turn",
        "device": "seat rolls toward the outside of the corner and recentres during recovery",
        "audio": "engine rise, tyre scrub, wet spray and suspension compression",
        "voice": "侧倾：高速过弯模拟横向惯性。",
    },
    "heave": {
        "chapter": "HEAVE · DROP AND LANDING",
        "practical": "A rescue capsule and performers are secured to a vertical drop rig above a marked landing platform.",
        "final": "Match-cut to the same capsule dropping through cloud, decelerating hard and completing one heavy landing with correct vertical weight transfer.",
        "camera": "Stable three-quarter view with a readable vertical axis; no artificial zoom or floating camera.",
        "cause": "the capsule loses altitude, decelerates and contacts the landing platform",
        "response": "bodies become briefly light, harnesses tighten, landing legs compress and dust moves radially",
        "device": "seat heaves downward during the drop and rises sharply at landing compression",
        "audio": "air rush, structural strain, thruster brake and one grounded landing thump",
        "voice": "升降：同步坠落、减速与着陆。",
    },
    "wind": {
        "chapter": "WIND · TORNADO PURSUIT",
        "practical": "Large directional wind machines drive rain, cloth and lightweight debris across a storm-chase vehicle set.",
        "final": "Match-cut to the same vehicle escaping the edge of an original tornado as sustained crosswind bends trees and drives rain consistently across frame.",
        "camera": "Vehicle-mounted forward three-quarter shot with a level, readable escape path.",
        "cause": "the rotating storm front and vehicle speed produce sustained directional airflow",
        "response": "rain, vegetation, clothing and loose debris all move in the same wind direction",
        "device": "continuous theatre wind follows storm direction and speed, then decays after escape",
        "audio": "sustained gale, rain on metal, engine load and distant thunder",
        "voice": "强风：方向与风暴气流同步。",
    },
    "air_shot": {
        "chapter": "AIR SHOT · NEAR MISS",
        "practical": "Timed pneumatic air nozzles and a safely tethered lightweight debris element are aimed past, never at, the performer.",
        "final": "Match-cut to an original action scene where one fast fragment crosses close beside the performer and camera before striking a wall behind them.",
        "camera": "Tight eye-level reaction shot that preserves the fragment's entry, near-miss path and exit impact.",
        "cause": "one visible fragment passes close to the performer before hitting the rear wall",
        "response": "hair and clothing snap once along the passing direction, followed by a small rear-wall dust puff",
        "device": "one short directional air burst fires at the exact near-miss, never continuously",
        "audio": "single high-speed whoosh, cloth snap and delayed wall tick",
        "voice": "喷气：擦身瞬间触发一次气流。",
    },
    "vibration": {
        "chapter": "VIBRATION · STRUCTURAL RUMBLE",
        "practical": "A practical tunnel floor sits on low-frequency shakers while lamps and dust trays are independently rigged.",
        "final": "Match-cut to the same tunnel as a massive underground machine approaches; vibration builds, bolts chatter and ceiling dust falls before the machine passes.",
        "camera": "Locked low-angle frame with only physically motivated micro-shake from the floor.",
        "cause": "a heavy underground machine transfers repeated low-frequency force into the tunnel",
        "response": "floor, lamps, bolts, puddles and dust respond together with increasing then decreasing amplitude",
        "device": "continuous low-frequency seat vibration follows the machine's approach and departure envelope",
        "audio": "sub-bass machinery rumble, metal chatter, water ripples and falling grit",
        "voice": "震动：低频先增强，再随距离衰减。",
    },
    "impact": {
        "chapter": "IMPACT · COLLISION",
        "practical": "A stunt vehicle shell, breakaway barrier and compressed-air debris cannons are aligned for one safe collision beat.",
        "final": "Match-cut to the same original vehicle striking the barrier once; the bonnet crumples, fragments travel away from contact and the vehicle stops with believable mass.",
        "camera": "Three-quarter impact view that keeps source, contact point, force direction and vehicle displacement readable.",
        "cause": "the moving vehicle makes one visible contact with the breakaway barrier",
        "response": "metal deforms at contact, fragments travel forward and outward, and the vehicle decelerates abruptly",
        "device": "one sharp back-impact pulse lands after visible contact, followed by a short decay",
        "audio": "tyre scrub, single metal impact, glass fragments and chassis settling",
        "voice": "冲击：碰撞之后，座椅准确落点。",
    },
    "flash": {
        "chapter": "FLASH · LIGHTNING STRIKE",
        "practical": "High-output practical flash units and interactive light panels surround a rain-safe rooftop antenna set.",
        "final": "Match-cut to the same rooftop as one lightning branch strikes the antenna, briefly overexposes wet surfaces and leaves a fading electrical glow.",
        "camera": "Stable wide-to-medium rooftop composition; the flash comes from the visible lightning source, never from an arbitrary edit.",
        "cause": "one visible lightning branch contacts the rooftop antenna",
        "response": "wet metal and cloud illuminate instantly, sparks fall with gravity and exposure recovers naturally",
        "device": "one brief theatre flash follows visible electrical contact and does not strobe without cause",
        "audio": "electrical crack, delayed thunder and rain ambience",
        "voice": "闪光：雷击接触一刻同步触发。",
    },
    "fog_smoke": {
        "chapter": "FOG / SMOKE · FIRE CORRIDOR",
        "practical": "A controlled film-set corridor uses safe haze, directional fans and warm interactive firelight outside frame.",
        "final": "Match-cut to the same corridor as a rescuer pushes through layered smoke; a door opens, pressure moves the smoke and visibility changes continuously.",
        "camera": "Shoulder-height forward follow with a stable spatial axis and no impossible smoke teleportation.",
        "cause": "a hot-room door opens and releases a pressure-driven smoke layer into the corridor",
        "response": "smoke rolls along the ceiling, curls around the rescuer and thins behind the airflow",
        "device": "theatre fog begins only after the visible door release and dissipates with the scene",
        "audio": "muffled fire, alarm, respirator breath, door latch and moving air",
        "voice": "烟雾：开门后按扩散过程出现。",
    },
    "water_rain": {
        "chapter": "WATER / RAIN · OCEAN IMPACT",
        "practical": "A boat deck section, overhead rain bars and side water cannons reproduce one controlled wave impact.",
        "final": "Match-cut to the same original rescue boat meeting a storm wave; spray crosses the bow, strikes the deck and drains in physically consistent directions.",
        "camera": "Deck-level forward view that shows the wave approach, bow contact and water travel without hiding causality.",
        "cause": "the boat bow visibly contacts one incoming storm wave",
        "response": "water splits around the bow, spray travels rearward and rain continues under the same wind",
        "device": "front water spray triggers at wave contact while lighter rain continues through the storm beat",
        "audio": "wave approach, hull slap, deck spray, rain and engine strain",
        "voice": "水雨：浪花与持续降雨分层同步。",
    },
}

_AUDIENCE_REACTIONS = {
    "pitch": "seat backs pitch with the aircraft load; torsos press backward, then brace forward, while hands grip individual armrests",
    "roll": "motion seats bank laterally; bodies lean and counterbalance in the same force direction with varied timing",
    "heave": "seat bases lift and drop; shoulders become briefly light, hands clamp down and bodies settle heavily after landing",
    "wind": "hair, loose clothing and jacket collars stream with the same directional wind while several viewers shield their faces",
    "air_shot": "the near-side audience blinks, flinches and turns toward one sharply localized air burst while farther viewers react less",
    "vibration": "seat frames and shoulders visibly tremble, hands tighten on armrests and drink surfaces ripple with the low-frequency envelope",
    "impact": "one sharp seat-back impulse jolts torsos only after screen contact; viewers exhale, recoil and then recover individually",
    "flash": "faces and the auditorium illuminate from the screen-side strike; viewers blink, squint or turn away with varied natural delay",
    "fog_smoke": "low fog enters from visible theatre outlets, curls around shoes and seat bases, and viewers point, lean or wave through it",
    "water_rain": "front and middle rows receive visible droplets; viewers shield faces, laugh, wipe water away and check nearby companions",
}

_AUDITORIUM_MECHANISM_SOUNDS = {
    "pitch": "near-field gimbal servos, seat-frame pitch motors, armrest creaks, clothing tension and a brief wind-machine rise",
    "roll": "lateral seat actuators, chassis flex, damp tyre spray from the screen and bodies shifting across seat cushions",
    "heave": "vertical lift actuators, harness tension, seat-base travel, air displacement and one heavy synchronized landing thump",
    "wind": "broad directional fan wash, hair and loose clothing flutter, rain striking surfaces and seats creaking under braced bodies",
    "air_shot": "one localized pneumatic burst, a close passing whoosh, cloth snap and individual startled breaths",
    "vibration": "continuous low-frequency seat and floor transducer rumble, bolts and cup surfaces rattling, then a distance-based decay",
    "impact": "one contact-synchronized seat-back impulse, metal collision through the front speakers, seat-frame knock and body recoil",
    "flash": "one sharp electrical crack from the screen, a brief practical-unit discharge, delayed thunder and scattered audience gasps",
    "fog_smoke": "fog-machine airflow, ceiling-level moving air, muffled fire through the screen speakers, coughing and clothing movement",
    "water_rain": "front water-nozzle spray, droplets hitting clothing and seat surfaces, wave impact through the speakers and startled laughter",
}

# A screen event alone reads as an ordinary cinema projection. Each chapter
# therefore owns one restrained stereoscopic depth bridge: a single
# effect-bearing element crosses the visible screen plane, occludes part of the
# screen border and continues into the air above the front rows. This is a
# projection illusion plus a practical auditorium response, never a duplicate
# full-size subject physically placed among the audience.
_SCREEN_BREAKOUTS = {
    "pitch": "the single fighter's nose, leading wing edge and compressed vapour visually project just beyond the screen plane as it climbs",
    "roll": "the single rally car's leading corner, tyre spray and road grit visually project just beyond the screen plane through the outside of the turn",
    "heave": "the single rescue capsule's landing struts, dust ring and downward pressure visually project just beyond the screen plane during deceleration",
    "wind": "one coherent stream of rain, leaves and lightweight storm debris visually projects from the screen into the auditorium airflow",
    "air_shot": "the single fast fragment visually crosses the screen plane and passes above the front-row sightline before its off-axis exit",
    "vibration": "one coherent floor-pressure ripple, falling grit and dust wave visually projects beyond the bottom screen edge toward the front rows",
    "impact": "one bounded burst of barrier fragments, dust and pressure visually projects beyond the screen plane only after vehicle contact",
    "flash": "one lightning branch and its short corona visually project beyond the upper screen plane while the source remains anchored to the rooftop",
    "fog_smoke": "one continuous smoke layer rolls beyond the bottom and side screen borders into matching practical auditorium haze",
    "water_rain": "one wave crest and its spray visually project beyond the lower screen plane into matching real droplets above the front rows",
}

_SCREEN_BREAKOUT_CONTRACT = (
    "SCREEN-PLANE BREAKOUT: begin with the event spatially anchored inside the visible movie screen, "
    "then let exactly one effect-bearing foreground element cross the screen plane toward the audience. "
    "Keep the physical screen frame visible and let that element briefly occlude one part of the screen "
    "border; this border occlusion is the required depth proof. Continue the same direction, timing, light, "
    "particles and atmosphere into the auditorium above the front rows. Preserve one subject only: never "
    "duplicate the aircraft, vehicle, person, creature or source object, never place a second full-size copy "
    "inside the theatre, and never turn the image into a detached hologram, portal or floating rectangular panel."
)


def _screen_breakout_direction(effect_id: str) -> str:
    return f"{_SCREEN_BREAKOUT_CONTRACT} Specifically, {_SCREEN_BREAKOUTS[effect_id]}."


def fourdx_effect_id_from_text(*values: object) -> str:
    """Recover the active 4DX chapter from its stable authored direction."""

    text = " ".join(str(value or "") for value in values).casefold()
    for effect_id, label, _description in FOURDX_EFFECTS:
        if f"chapter {label.casefold()}" in text:
            return effect_id
    return ""


def fourdx_native_audio_fields(effect_id: str = "", *, phase: str = "effect") -> dict:
    """Return prompt-only, unprocessed live-auditorium sound direction."""

    if effect_id in _SHOWCASE_EFFECTS:
        scene = _SHOWCASE_EFFECTS[effect_id]
        mechanism = _AUDITORIUM_MECHANISM_SOUNDS[effect_id]
        direction = (
            "Acoustic space: a large purpose-built 4DX cinema auditorium, never an office, with front-wall "
            "screen speakers, reflective side walls, absorptive seating and clearly localized near-field "
            "mechanisms. Maintain four simultaneously audible diegetic layers: (1) the movie event from the "
            f"front screen speakers—{scene['audio']}; (2) close auditorium hardware—{mechanism}; (3) the "
            "screen-plane breakout continuing into the room as directional air, particles, spray, haze or "
            "pressure that matches the visible event; and (4) unscripted audience gasps, startled breaths, "
            "short cries, laughter, clothing movement and seat contact. Front-row reactions sound closest and "
            "first, middle rows follow slightly later, and rear rows remain quieter and more diffuse. Every "
            "onset follows its visible cause and every tail decays naturally. Keep the location effects and "
            "human reactions clearly louder and more detailed than any neutral room bed. No song, score, "
            "musical drone, trailer music, voice-over, announcer, scripted dialogue or studio sound. H3 creates "
            "this native production audio directly; do not replace, separate, remix or post-process it."
        )
    elif phase == "final_hold":
        direction = (
            "Acoustic space: the same large purpose-built 4DX cinema auditorium. Continue only the audible "
            "decay of the preceding screen event, seat motors returning to neutral, settling mechanisms, "
            "dripping water or fading airflow when visible, clothing movement, audience breathing, scattered "
            "nervous laughter and short recovery reactions. Begin no new sound event. No music, score, musical "
            "drone, voice-over, announcer or dialogue."
        )
    else:
        direction = (
            "Acoustic space: a large purpose-built 4DX cinema auditorium with front screen speakers and "
            "near-field motion seats. From the first frame, make projector airflow, active seat motors, the "
            "current screen event, environmental equipment, clothing movement and varied audience breaths or "
            "gasps distinctly audible as live diegetic sound. No music, score, musical drone, voice-over, "
            "announcer or dialogue."
        )
    return {
        "native_audio_direction": direction,
        "environment_continuity": (
            "Remain inside the same large 4DX auditorium. Preserve the front-speaker direction, near-field "
            "seat and device positions, broad room reflections, audience depth and ongoing mechanical/location "
            "bed across cuts without restarting or copying a previous generated audio tail."
        ),
        "audio_reference_intent": (
            "No Audio or Video reference is copied as dialogue or music. Any mapped reference may guide only "
            "auditorium spatial acoustics, effect timing, distance and live texture; H3 generates new native "
            "screen-event, mechanism and audience sound."
        ),
    }


def fourdx_overall_soundscape() -> str:
    """Return the format-owned H3-native mix hierarchy."""

    return (
        "H3-native diegetic 4DX auditorium sound only. In every active effect chapter keep four clearly "
        "audible spatial layers at the same time: front-screen movie-event sound; close motion-seat motors "
        "and mechanism contact; directional wind, air, water, fog, vibration or impact equipment matching "
        "the visible breakout; and varied audience gasps, startled breaths, short cries, laughter, clothing "
        "movement and seat contact. Foreground physical effects and human reactions outrank the quiet projector "
        "and room-tone bed. Preserve front-to-rear distance, direction, onset and natural decay. No background "
        "music, song, score, musical drone, trailer cue, voice-over, announcer, scripted dialogue or studio "
        "sound. Generate this sound natively with the H3 picture; do not add TTS, source separation, replacement "
        "audio, FFmpeg effects, EQ, convolution reverb or post mix."
    )


def minimum_fourdx_duration(effect_count: int) -> float:
    """Return the production floor: one effect is 15s, all ten are 60s."""

    count = max(1, min(len(FOURDX_EFFECT_IDS), int(effect_count or 0)))
    return FOURDX_BASE_DURATION_SECONDS + (count - 1) * FOURDX_ADDITIONAL_EFFECT_SECONDS


def _requirement_without_control_block(requirement: str) -> str:
    return re.sub(
        rf"(?ms)^\s*{re.escape(FOURDX_REQUIREMENT_BEGIN)}\s*$.*?"
        rf"^\s*{re.escape(FOURDX_REQUIREMENT_END)}\s*$",
        "",
        str(requirement or ""),
    ).strip()


def requested_fourdx_duration(requirement: str) -> float | None:
    """Read an authored film duration without trusting numbers inside the control block."""

    text = _requirement_without_control_block(requirement)
    patterns = (
        r"(?:总时长|總時長|目标时长|目標時長|影片时长|影片時長|视频时长|視頻時長|时长|時長)\s*"
        r"(?:为|為|是|[:：=])?\s*(\d+(?:\.\d+)?)\s*(?:秒|s(?:ec(?:ond)?s?)?)",
        r"(?:创作|製作|制作|生成|create|make)\D{0,24}(\d+(?:\.\d+)?)\s*"
        r"(?:秒|s(?:ec(?:ond)?s?)?|[- ]second)",
        r"\b(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)\b",
        r"(\d+(?:\.\d+)?)\s*秒",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            value = float(match.group(1))
            if 1.0 <= value <= 7200.0:
                return value
    return None


def normalize_fourdx_preferences(value: object | None) -> dict:
    raw = value if isinstance(value, dict) else {}
    selected = raw.get("selected_effects", _DEFAULT_SELECTED)
    if isinstance(selected, str):
        selected = re.split(r"[,;|\s]+", selected)
    selected_ids = []
    for item in selected or []:
        key = str(item).strip().lower().replace(" ", "_").replace("/", "_")
        aliases = {
            "airshot": "air_shot", "fog": "fog_smoke", "smoke": "fog_smoke",
            "fog___smoke": "fog_smoke", "water": "water_rain", "rain": "water_rain",
            "water___rain": "water_rain", "back_punch": "impact",
        }
        key = aliases.get(key, key)
        if key in FOURDX_EFFECT_IDS and key not in selected_ids:
            selected_ids.append(key)
    intensity = str(raw.get("intensity", "medium")).strip().lower()
    density = str(raw.get("density", "balanced")).strip().lower()
    minimum_duration = minimum_fourdx_duration(len(selected_ids))
    requested_duration = raw.get("requested_duration_seconds")
    try:
        requested_duration = float(requested_duration) if requested_duration is not None else None
    except (TypeError, ValueError):
        requested_duration = None
    if requested_duration is not None and requested_duration <= 0.0:
        requested_duration = None
    resolved_duration = max(minimum_duration, requested_duration or minimum_duration)
    return {
        "selected_effects": selected_ids,
        "intensity": intensity if intensity in _LEVELS else "medium",
        "density": density if density in _DENSITIES else "balanced",
        "selected_effect_count": len(selected_ids),
        "minimum_duration_seconds": minimum_duration,
        "requested_duration_seconds": requested_duration,
        "resolved_duration_seconds": resolved_duration,
    }


def update_fourdx_requirement_block(requirement: str, preferences: object | None) -> str:
    """Replace the Studio-owned block while preserving the user's story text."""

    authored_duration = requested_fourdx_duration(requirement)
    raw_preferences = dict(preferences) if isinstance(preferences, dict) else {}
    raw_preferences["requested_duration_seconds"] = authored_duration
    prefs = normalize_fourdx_preferences(raw_preferences)
    labels = [FOURDX_EFFECT_LABELS[key] for key in prefs["selected_effects"]]
    block = "\n".join((
        FOURDX_REQUIREMENT_BEGIN,
        "Selected effects: " + (", ".join(labels) if labels else "NONE"),
        f"Selected effect count: {prefs['selected_effect_count']}",
        (
            f"Authored target duration: {prefs['requested_duration_seconds']:.2f} seconds"
            if prefs["requested_duration_seconds"] is not None
            else "Authored target duration: AUTO"
        ),
        f"Calculated minimum duration: {prefs['minimum_duration_seconds']:.2f} seconds",
        f"Resolved design duration: {prefs['resolved_duration_seconds']:.2f} seconds",
        "Duration rule: 15 seconds for the first effect, plus 5 seconds for every additional selected effect. A longer authored target is preserved; a shorter one is raised to the calculated minimum.",
        f"Intensity: {prefs['intensity'].upper()}",
        f"Event density: {prefs['density'].upper()}",
        "Each selected effect becomes one immersive live-auditorium chapter. Keep the movie-screen cause, active theatre mechanism and varied audience reaction visible together for at least 99% of the chapter.",
        "Screen-depth policy: one effect-bearing element must visibly cross and occlude the movie-screen border, continue into the auditorium as a coherent stereoscopic/practical effect, and trigger directional audience surprise. Never duplicate the source subject.",
        "Sound policy: DIEGETIC 4DX AUDITORIUM ONLY. Keep four audible layers: screen event, close seat/mechanism Foley, directional environmental effect, and staggered audience reactions. No voice-over, dialogue, announcer, score or background music; this Skill overrides a global MUSIC AUTO setting during H3 compilation.",
        "Camera policy: immersive FPV translation and a wide spatial orbit around reacting audience rows; no visible drone, in-place spin, barrel roll or zoom-out.",
        "Camera movement is never seat movement. Keep H3 visual/audio direction separate from structured Physical Events and 4DX Events.",
        FOURDX_REQUIREMENT_END,
    ))
    text = str(requirement or "").strip()
    pattern = re.compile(
        rf"(?ms)^\s*{re.escape(FOURDX_REQUIREMENT_BEGIN)}\s*$.*?^\s*{re.escape(FOURDX_REQUIREMENT_END)}\s*$"
    )
    if pattern.search(text):
        return pattern.sub(block, text).strip()
    return (text + "\n\n" + block).strip() if text else block


def fourdx_preferences_from_requirement(requirement: str) -> dict:
    """Read the managed control block; return defaults for legacy templates."""

    text = str(requirement or "")
    match = re.search(
        rf"(?ms)^\s*{re.escape(FOURDX_REQUIREMENT_BEGIN)}\s*$"
        rf"(.*?)^\s*{re.escape(FOURDX_REQUIREMENT_END)}\s*$",
        text,
    )
    if not match:
        return normalize_fourdx_preferences(None)
    body = match.group(1)
    labels_match = re.search(r"(?im)^\s*Selected effects\s*:\s*(.+)$", body)
    selected: list[str] = []
    if labels_match and labels_match.group(1).strip().upper() != "NONE":
        requested_labels = [part.strip().upper() for part in labels_match.group(1).split(",")]
        for effect_id, label, _description in FOURDX_EFFECTS:
            if label.upper() in requested_labels:
                selected.append(effect_id)
    intensity_match = re.search(r"(?im)^\s*Intensity\s*:\s*(\w+)", body)
    density_match = re.search(r"(?im)^\s*Event density\s*:\s*(\w+)", body)
    authored_match = re.search(
        r"(?im)^\s*Authored target duration\s*:\s*(\d+(?:\.\d+)?)\s*seconds",
        body,
    )
    authored_duration = (
        float(authored_match.group(1))
        if authored_match else requested_fourdx_duration(text)
    )
    return normalize_fourdx_preferences({
        "selected_effects": selected,
        "intensity": intensity_match.group(1) if intensity_match else "medium",
        "density": density_match.group(1) if density_match else "balanced",
        "requested_duration_seconds": authored_duration,
    })


def build_reference_role_ledger(existing_media: list[dict] | None) -> list[dict]:
    """Build a conservative reference ledger without trusting filenames."""

    rows: list[dict] = []
    for raw in existing_media or []:
        if not isinstance(raw, dict) or not bool(raw.get("loaded", False)):
            continue
        media_id = str(raw.get("media_id") or "").strip().upper().lstrip("@")
        if not re.fullmatch(r"[PVA][1-9]\d*", media_id):
            continue
        media_type = str(raw.get("media_type") or raw.get("type") or "").lower()
        evidence = " ".join(str(raw.get(key) or "") for key in (
            "clip_prompt", "caption", "semantic_enrichment", "analysis_summary",
        )).strip()
        compact = " ".join(evidence.split())[:520]
        lowered = compact.casefold()
        if media_type == "audio":
            role = "master_audio_or_acoustic_reference"
        elif media_type == "video":
            role = "motion_or_live_action_reference"
        elif re.search(r"route|path|map|mask|depth|control|路线|路線|轨迹|軌跡|遮罩|深度", lowered):
            role = "analysis_only_control"
        elif re.search(r"person|woman|man|girl|boy|face|character|人物|角色|男人|女人|女孩|男孩|脸|臉", lowered):
            role = "character_or_subject_reference"
        elif re.search(r"building|street|room|landscape|environment|scene|建筑|建築|街|房间|房間|环境|環境|场景|場景", lowered):
            role = "environment_or_scene_plate"
        else:
            role = "unresolved_visual_reference"
        rows.append({
            "media_id": media_id,
            "media_type": media_type,
            "role": role,
            "authority": "user_mapping" if raw.get("clip_prompt") else "pixel_evidence",
            "evidence": compact or "Loaded media; detailed analysis unavailable.",
            "filename_is_evidence": False,
        })
    return rows


def scaled_making_of_stages(
    duration_seconds: float,
    selected_effects: object | None = None,
) -> list[dict]:
    """Build an intro, one causal demo chapter per effect, and a final hold."""

    if selected_effects is None:
        effect_ids = list(FOURDX_EFFECT_IDS)
    else:
        effect_ids = normalize_fourdx_preferences({
            "selected_effects": selected_effects,
        })["selected_effects"]
    duration_floor = minimum_fourdx_duration(len(effect_ids))
    duration = max(duration_floor, float(duration_seconds or duration_floor))
    # The requested experience is the film: reserve only two half-second
    # boundary beats and keep a visible effect or its residual response in
    # essentially every frame.
    intro_duration = 0.5
    final_duration = 0.5
    stages = [{
        "stage_id": "showcase_intro",
        "label": "10 4DX EFFECTS · MAKING OF",
        "start_seconds": 0.0,
        "end_seconds": round(intro_duration, 3),
        "direction": (
            "Enter an already-active premium 4DX auditorium; screen action, theatre effects and "
            "audience response are all visible from the first frame."
        ),
        "stage_kind": "intro",
    }]
    if effect_ids:
        available = max(1.0, duration - intro_duration - final_duration)
        chapter_duration = available / len(effect_ids)
        for index, effect_id in enumerate(effect_ids):
            start = intro_duration + index * chapter_duration
            end = intro_duration + (index + 1) * chapter_duration
            scene = _SHOWCASE_EFFECTS[effect_id]
            stages.append({
                "stage_id": f"effect_{effect_id}",
                "effect_id": effect_id,
                "label": f"{index + 1:02d} · {scene['chapter']}",
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "direction": (
                    "Keep the finished screen event, active theatre mechanism and varied audience "
                    "reaction visible together for nearly the complete chapter."
                ),
                "stage_kind": "effect_demo",
            })
    stages.append({
        "stage_id": "final_hold",
        "label": "VISIBLE CAUSE → SYNCHRONIZED EXPERIENCE",
        "start_seconds": round(duration - final_duration, 3),
        "end_seconds": round(duration, 3),
        "direction": (
            "Hold the integrated auditorium as the final effect decays; begin no new event."
        ),
        "stage_kind": "final_hold",
    })
    return stages


def _showcase_shot(stage: dict, *, shot_id: str) -> dict:
    start = float(stage["start_seconds"])
    end = float(stage["end_seconds"])
    kind = str(stage.get("stage_kind", ""))
    if kind == "intro":
        audio_fields = fourdx_native_audio_fields(phase="intro")
        action = (
            "From the first frame, a dedicated premium 4DX cinema auditorium is already alive: a "
            "large movie screen, rows of black motion seats, active environmental-effect outlets and "
            "a diverse adult audience are all readable in one immersive view."
        )
        environment = (
            "Screen light washes naturally across audience faces and wet or hazy air; seats, clothing "
            "and bodies already carry the residual motion of an active 4DX demonstration."
        )
        return {
            "id": shot_id, "start_seconds": start, "end_seconds": end, "track": "V1",
            "preset": "", "framing": "Wide cinematic establishing shot",
            "camera_angle": "Human eye level between seat rows",
            "camera_movement": (
                "Immersive FPV translation through the aisle into a wide spatial arc around the central "
                "audience group; keep the horizon level and never spin in place."
            ),
            "movement_speed": "Immersive and continuous", "movement_amplitude": "Wide spatial arc",
            "subject_action": action, "environment_response": environment,
            "continuity_state": "Incoming: active auditorium. Outgoing: camera enters the first effect chapter without stopping the live experience.",
            "optional_flourish": "Projector haze and physically motivated interactive light.",
            "additional_direction": (
                "IMMERSIVE 4DX AUDITORIUM LOCK. Show a purpose-built cinema, never a banquet hall, "
                "conference room, computer lab, gaming simulator or office. No narrator, dialogue, "
                "announcer or background music. All audio is diegetic auditorium sound: screen event, "
                "theatre speakers, motion-seat mechanisms, environmental rigs and audience reactions. "
                "Technical wording is owned by editable Studio graphics; H3 renders no text, UI, HUD, "
                "chart or logo."
            ),
            "h3_executable_action": action,
            "h3_optional_flourish": "Projector haze and physically motivated interactive light.",
            **audio_fields,
        }
    if kind == "final_hold":
        audio_fields = fourdx_native_audio_fields(phase="final_hold")
        action = (
            "The FPV camera finishes its spatial arc beside the audience while the last screen event, "
            "seat motion, environmental effect and human reactions complete together and begin to settle."
        )
        environment = (
            "Residual haze, droplets, reflected light, moving clothing and seat oscillation remain visible "
            "during the hold and decay naturally without a new trigger."
        )
        return {
            "id": shot_id, "start_seconds": start, "end_seconds": end, "track": "V1",
            "preset": "", "framing": "Stable wide final composition",
            "camera_angle": "Audience eye level", "camera_movement": "FPV arc settles into a locked final hold",
            "movement_speed": "Decelerating to zero", "movement_amplitude": "Wide arc resolving to zero",
            "subject_action": action, "environment_response": environment,
            "continuity_state": "Incoming: tenth demonstration decays. Outgoing: stable resolved final frame.",
            "optional_flourish": "None.",
            "additional_direction": (
                "FINAL HOLD LOCK: keep the live audience and residual 4DX atmosphere visible, but start no "
                "new action or effect. No narration, dialogue or music; retain only diegetic auditorium "
                "decay, seat mechanisms and audience breath/reaction. H3 renders no technical text."
            ),
            "h3_executable_action": action, "h3_optional_flourish": "None.",
            **audio_fields,
        }
    effect_id = str(stage["effect_id"])
    scene = _SHOWCASE_EFFECTS[effect_id]
    audience = _AUDIENCE_REACTIONS[effect_id]
    breakout = _screen_breakout_direction(effect_id)
    audio_fields = fourdx_native_audio_fields(effect_id)
    action = (
        "From the first frame of this chapter, keep one dedicated premium 4DX auditorium, its giant screen, "
        "at least three staggered rows of real black motion seats and multiple distinct adult audience "
        f"members visible together. The screen presents this finished original cinematic event: {scene['final']} "
        f"The corresponding physical theatre mechanism remains visibly active around them: {scene['practical']} "
        f"{breakout} Audience response is mandatory and event-specific: {audience}. Front-row viewers "
        "notice the screen-plane crossing first and recoil, duck, blink or shield themselves in its travel "
        "direction; middle rows react a fraction later; rear rows gasp, point or lean with smaller delayed motion."
    )
    environment = (
        f"Visible physical chain: {scene['cause']}; therefore {scene['response']}. "
        "The breakout element occludes one screen-border segment before matching light, air, particles or "
        "moisture continue across the front-row airspace. The screen's direction, interactive auditorium light, environmental output, seat response, audience "
        "body response and sound all share the same onset, direction, magnitude and decay. The effect is "
        "visibly active for at least ninety-nine percent of the chapter."
    )
    return {
        "id": shot_id, "start_seconds": start, "end_seconds": end, "track": "V1",
        "preset": "", "framing": (
            "Wide three-quarter side-aisle depth composition with the visible screen border, breakout "
            "foreground element and reacting audience faces readable together in the same frame"
        ),
        "camera_angle": "Side-aisle audience eye level looking diagonally across front rows toward the screen",
        "camera_movement": (
            "Immersive FPV camera physically translates between seat rows, then makes one smooth wide "
            "spatial arc around the central reacting audience cluster while keeping the screen readable. "
            "During the screen-plane crossing, hold the three-quarter side-aisle axis long enough to keep "
            "the screen border, protruding element and audience faces visible together; do not cut to an "
            "isolated front-facing crowd shot or pass behind the audience and lose the screen. "
            "No in-place rotation, barrel roll, zoom-out or visible drone. " + scene["camera"]
        ),
        "movement_speed": "Energetic spatial FPV translation", "movement_amplitude": "Wide audience-centred arc",
        "screen_plane_breakout_required": True,
        "screen_plane_breakout": breakout,
        "audience_startle_chain": (
            "visible screen-plane crossing -> immediate directional front-row avoidance -> "
            "slightly delayed middle-row recoil -> smaller rear-row gasp and pointing -> natural recovery"
        ),
        "subject_action": action, "environment_response": environment,
        "continuity_state": (
            f"Incoming: auditorium and audience already active. Outgoing: {effect_id} response flows into "
            "the next chapter through matched audience eyelines, seat position and atmospheric residue."
        ),
        "optional_flourish": "Physically caused particles, droplets, haze, reflections and interactive screen light remain integrated with audience bodies.",
        "additional_direction": (
            f"LIVE 4DX EFFECT CHAPTER {scene['chapter']}. Device mapping: {scene['device']}. SOUND LOCK: no "
            f"voice-over, dialogue, announcer, studio voice or background music. Generate only synchronized "
            f"diegetic cinema sound from the screen and auditorium: {scene['audio']}; add spatial motion-seat "
            "motors, air/water/fog equipment when relevant, clothing movement, seat creaks and varied audience "
            "gasps, breaths, laughs or flinches caused by this exact event. Audience members must not sit "
            "motionless, react identically or look like duplicated extras. Screen action, theatre light, "
            "physical effect and human response must remain visible in the same continuous immersive space. "
            "DEPTH LOCK: keep the screen frame readable while one foreground effect element visibly crosses "
            "and occludes its border, enters the air above the front rows and causes a directional wave of "
            "surprise. Do not keep all action trapped inside the flat screen; do not duplicate the source object. "
            "Never imitate a copyrighted film or character. Chapter titles are silent Studio graphics; H3 and "
            "Z-Image draw no text, arrows, UI, HUD or split-screen interface chrome. Camera motion is not seat force."
        ),
        "h3_executable_action": action,
        "h3_optional_flourish": "Physically caused particles, droplets, haze, reflections and interactive screen light remain integrated with audience bodies.",
        **audio_fields,
    }


def _showcase_media_requests(stages: list[dict]) -> list[dict]:
    """Request at most one time-scoped scene plate per selected effect."""

    rows: list[dict] = []
    for stage in stages:
        if stage.get("stage_kind") != "effect_demo":
            continue
        effect_id = str(stage["effect_id"])
        scene = _SHOWCASE_EFFECTS[effect_id]
        rows.append({
            # v3 uses a new stable identity so a reopened project cannot reuse a
            # pre-breakout flat-screen plate generated by the earlier format.
            "requirement_id": f"fourdx_screen_breakout_v3_{effect_id}_scene_plate",
            "media_type": "image",
            "usage": "h3_reference",
            "reuse_policy": "time_scoped",
            "start_seconds": float(stage["start_seconds"]),
            "end_seconds": float(stage["end_seconds"]),
            "track": "V2",
            "subject_keywords": ["4DX making-of", effect_id, scene["chapter"]],
            "prompt": (
                f"One photoreal 16:9 immersive live 4DX cinema scene plate for {scene['chapter']}. "
                "Show a real purpose-built dark premium cinema auditorium, a large bright movie screen, "
                "three or more staggered rows of black motion seats and multiple distinct adult audience "
                "members with readable frontal or three-quarter faces and different natural reactions. "
                f"The screen and visible environmental equipment are already presenting: {scene['final']} "
                f"Integrate the active practical mechanism into the same space: {scene['practical']} "
                f"Create one unmistakable stereoscopic screen-plane breakout: {_SCREEN_BREAKOUTS[effect_id]}. "
                "The breakout element must occlude a small part of the still-visible screen frame and continue "
                "into the air above the front rows with matching perspective, illumination and atmosphere. "
                "Front-row viewers react first and directionally; middle and rear rows follow with varied delay. "
                "Screen light must illuminate audience faces, seats, particles and atmosphere consistently. "
                "If compatible loaded Media Pool references are mapped into this range, preserve their "
                "pixel-defined identity, wardrobe, object and environment facts; otherwise use entirely "
                "original fictional subjects. No copied movie character, no technical text, UI, HUD, arrows, "
                "diagram, logo or watermark."
            ),
            "negative_prompt": (
                "banquet hall, conference room, computer lab, office, gaming simulator, dining tables, desks, "
                "desktop monitors, static audience, audience facing away, cloned people, identical reactions, "
                "empty cinema, visible drone, camera spinning in place, barrel roll, zoom out, copyrighted movie "
                "character, copied franchise costume, contradictory force direction, effect before cause, "
                "arbitrary camera shake, all action trapped inside a flat screen, no depth crossing, detached "
                "hologram, portal, floating rectangular panel, duplicated source subject, second aircraft, second "
                "vehicle, full-size object colliding with audience, motionless spectators, identical synchronized "
                "reactions, split screen UI, diagram, technical lettering, caption, logo, watermark"
            ),
        })
    return rows


def _showcase_text_layers(stages: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for index, stage in enumerate(stages):
        start = float(stage["start_seconds"])
        end = float(stage["end_seconds"])
        rows.append({
            "start_seconds": start,
            "end_seconds": min(end, start + max(0.9, min(1.5, end - start))),
            "track": f"V{4 + index % 3}",
            "content": stage["label"],
            "role": "on_screen_text", "speaker": "S1", "language": "English",
            "delivery": "Studio technical label; never spoken", "lip_sync": False,
            "overlap_policy": "auto", "explicit_user_requested": True,
            "timeline_visible_text_kind": "making_of_stage_label",
            "render_owner": "studio_graphics",
        })
    return rows


def enforce_making_of_fourdx_plan(
    plan: dict,
    *,
    existing_media: list[dict] | None,
    preferences: object | None,
    special_skill_key: str,
) -> dict:
    """Convert this Special Skill into a deterministic effect-showcase film."""

    if str(special_skill_key or "").strip().casefold() != AI_MOVIE_MAKING_OF_4DX_SKILL:
        return plan
    result = deepcopy(plan)
    original_duration = max(0.5, float(result.get("duration_seconds", 45.0) or 45.0))
    prefs = normalize_fourdx_preferences(
        preferences or result.get("experience_design") or {}
    )
    requested_duration = prefs.get("requested_duration_seconds")
    minimum_duration = float(prefs["minimum_duration_seconds"])
    duration = (
        max(minimum_duration, float(requested_duration))
        if requested_duration is not None
        else max(minimum_duration, original_duration)
    )
    if abs(original_duration - duration) > 1e-6:
        scale = duration / original_duration
        for family in ("shots", "text_layers", "existing_media_uses", "media_requests"):
            for row in result.get(family) or []:
                if not isinstance(row, dict):
                    continue
                for key in ("start_seconds", "end_seconds"):
                    if key in row:
                        row[key] = round(float(row[key]) * scale, 3)
        for family in ("transitions", "markers"):
            for row in result.get(family) or []:
                if isinstance(row, dict) and "time_seconds" in row:
                    row["time_seconds"] = round(float(row["time_seconds"]) * scale, 3)
    result["duration_seconds"] = duration
    stages = scaled_making_of_stages(duration, prefs["selected_effects"])
    ledger = build_reference_role_ledger(existing_media)

    # The prior alpha trusted Qwen to invent the film structure and merely
    # annotated it.  That produced a generic extraction/compositing tutorial.
    # This format owns its chronology: one intro, one chapter for every chosen
    # effect, and one final hold.  All chapters reach the actual H3 prompt.
    shots = [
        _showcase_shot(stage, shot_id=f"S{index + 1}")
        for index, stage in enumerate(stages)
    ]
    result["shots"] = shots
    result["text_layers"] = _showcase_text_layers(stages)
    result["media_requests"] = _showcase_media_requests(stages)
    result["transitions"] = [
        {
            "time_seconds": float(stage["start_seconds"]),
            "preset": "cut",
            "direction": "forward",
        }
        for stage in stages[1:]
    ]
    result["markers"] = [
        {"time_seconds": 0.0, "preset": "marker", "direction": "showcase_start"},
        *[
            {
                "time_seconds": float(stage["start_seconds"]),
                "preset": "marker",
                "direction": str(stage["label"]),
            }
            for stage in stages if stage.get("effect_id")
        ],
        {
            "time_seconds": float(stages[-1]["start_seconds"]),
            "preset": "Final Hold",
            "direction": "All camera, action and environmental effects settle before the last frame.",
        },
    ]
    result["title"] = "10种4DX电影效果 Making-of"
    result["creative_brief"] = (
        "A complete immersive live 4DX cinema showcase. The auditorium, movie-screen event, active "
        "environmental mechanism and varied audience response coexist in nearly every frame. Each selected "
        "effect has a visible cause, one unmistakable stereoscopic screen-plane breakout and a synchronized "
        "physical, lighting, sound and staggered human surprise reaction."
    )
    result["global_visual_style"] = (
        "Photoreal 16:9 premium cinema making-of documentary; original genre scenes, consistent "
        "subject geometry across each match cut, high dynamic range, realistic materials and no "
        "copyrighted characters, interface graphics or AI lettering."
    )
    result["overall_soundscape"] = fourdx_overall_soundscape()
    result["non_diegetic_music"] = "None. MUSIC OFF for this live 4DX auditorium showcase."
    constraints = str(result.get("constraints", "")).strip()
    sound_lock = (
        "LIVE 4DX IMMERSION LOCK: at least 99% of visible runtime retains an active 4DX effect or its "
        "physically decaying residue together with readable audience response. No narration, dialogue, "
        "announcer, non-diegetic music, banquet hall, conference room, computer lab, static audience, "
        "flat screen-only action, duplicated source subject, detached hologram, visible drone, in-place camera "
        "spin, barrel roll or zoom-out. Every effect chapter must prove forward depth by briefly occluding the "
        "visible screen border and continuing the same effect into the front-row airspace."
    )
    result["constraints"] = (constraints.rstrip(" .") + ". " + sound_lock).strip(" .") + "."
    physical_events: list[dict] = [
        deepcopy(row) for row in result.get("physical_events") or []
        if isinstance(row, dict)
        and str(row.get("generated_by", "")).strip().upper() == "MANUAL"
    ]
    fourdx_events: list[dict] = [
        deepcopy(row) for row in result.get("fourdx_events") or []
        if isinstance(row, dict)
        and str(row.get("generated_by", "")).strip().upper() == "MANUAL"
    ]
    used_physical_ids = {str(row.get("event_id", "")) for row in physical_events}
    used_fourdx_ids = {str(row.get("event_id", "")) for row in fourdx_events}
    effect_status: list[dict] = []
    magnitude = {"low": 0.35, "medium": 0.6, "high": 0.85}[prefs["intensity"]]
    for effect_id in prefs["selected_effects"]:
        stage = next(row for row in stages if row.get("effect_id") == effect_id)
        scene = _SHOWCASE_EFFECTS[effect_id]
        effect_status.append({
            "effect_id": effect_id,
            "status": "used",
            "chapter_start_seconds": stage["start_seconds"],
            "chapter_end_seconds": stage["end_seconds"],
            "visible_effect_presence_target": 0.99,
        })
        chapter_start = float(stage["start_seconds"])
        chapter_end = float(stage["end_seconds"])
        chapter_duration = chapter_end - chapter_start
        start = round(chapter_start + chapter_duration * 0.005, 3)
        event_duration_ms = round(max(350.0, chapter_duration * 0.99 * 1000.0))
        shot = next((
            row for row in shots
            if float(row.get("start_seconds", 0.0)) <= start
            < float(row.get("end_seconds", duration))
        ), shots[-1] if shots else {})
        shot_id = str(shot.get("id", ""))
        pe_number = 1
        while f"PE-{pe_number:03d}" in used_physical_ids:
            pe_number += 1
        pe_id = f"PE-{pe_number:03d}"
        used_physical_ids.add(pe_id)
        physical_events.append({
            "event_id": pe_id,
            "source_shot_id": shot_id,
            "event_type": effect_id,
            "start_ms": round(start * 1000),
            "duration_ms": event_duration_ms,
            "magnitude": magnitude,
            "source": scene["cause"],
            "target": scene["response"],
            "screen_plane_bridge": _SCREEN_BREAKOUTS[effect_id],
            "audience_reaction_trigger": "visible screen-border crossing before directional staggered surprise",
            "direction": scene["device"],
            "onset": "after_visible_trigger",
            "decay": "natural_scene_motivated_decay",
            "material_response": scene["response"],
            "status": "planned",
            "generated_by": "AUTO",
        })
        fourdx_number = 1
        while f"4DX-{fourdx_number:03d}" in used_fourdx_ids:
            fourdx_number += 1
        fourdx_id = f"4DX-{fourdx_number:03d}"
        used_fourdx_ids.add(fourdx_id)
        fourdx_events.append({
            "event_id": fourdx_id,
            "physical_event_id": pe_id,
            "effect_id": effect_id,
            "start_ms": round(start * 1000),
            "duration_ms": event_duration_ms,
            "intensity": magnitude,
            "density": prefs["density"],
            "actuator_intent": scene["device"],
            "camera_motion_is_source": False,
            "generated_by": "AUTO",
            "status": "planned",
        })

    result["reference_role_ledger"] = ledger
    result["physical_events"] = physical_events
    result["fourdx_events"] = fourdx_events
    result["experience_design"] = {
        "schema_version": FOURDX_SCHEMA_VERSION,
        "format": "ten_effect_4dx_cinema_making_of_showcase",
        **prefs,
        "stages": stages,
        "effect_status": effect_status,
        "rules": {
            "camera_motion_is_seat_motion": False,
            "h3_audio_is_rewritten": False,
            "technical_text_owner": "studio_timeline_graphics",
            "manual_events_preserved": True,
            "voice_over_policy": "off",
            "sound_source_policy": "diegetic_4dx_auditorium_only",
            "audience_reaction_required": True,
            "screen_plane_breakout_required": True,
            "screen_border_occlusion_required": True,
            "audience_startle_causality_required": True,
            "duplicate_source_subject_forbidden": True,
            "effect_visible_runtime_target": 0.99,
            "fpv_audience_orbit_required": True,
            "fpv_in_place_spin_forbidden": True,
        },
    }
    warnings = [str(item) for item in result.get("design_warnings") or []]
    if abs(original_duration - duration) > 1e-6:
        warnings.append(
            f"Resolved the 4DX showcase from the model's {original_duration:.2f}s plan to {duration:.2f}s "
            f"for {len(prefs['selected_effects'])} selected effect(s); the calculated minimum is "
            f"{minimum_duration:.2f}s."
        )
    if requested_duration is not None and float(requested_duration) < minimum_duration:
        warnings.append(
            f"The authored {float(requested_duration):.2f}s target is below the {minimum_duration:.2f}s "
            "4DX effect-count specification and was raised automatically."
        )
    if len(prefs["selected_effects"]) < len(FOURDX_EFFECT_IDS):
        warnings.append(
            "The showcase contains only the selected 4DX effect chapters. Select all ten controls "
            "in Design to generate the complete ten-effect demonstration."
        )
    warnings.append(
        "Rebuilt the Special Skill as one causal Making-of chapter per selected 4DX effect; replaced "
        "the previous generic source-analysis/extraction/compositing stage sequence."
    )
    result["design_warnings"] = list(dict.fromkeys(warnings))
    return result

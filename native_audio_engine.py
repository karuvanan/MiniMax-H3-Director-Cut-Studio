"""Prompt-only native H3 audio direction and read-only QC helpers.

This module never renders, replaces, filters, mixes, or writes audio.  It only
describes the sound H3 should generate with the picture and evaluates the
unchanged generated soundtrack through analysis supplied by ``audio_engine``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class NativeAudioProfile:
    acoustic_space: str
    camera_distance: str
    screen_position: str
    speech_state: str
    ambience: str
    foley: str


def _evidence(shot: Mapping[str, object]) -> str:
    return " ".join(
        str(shot.get(key, "") or "")
        for key in (
            "preset", "framing", "camera_angle", "camera_movement",
            "subject_action", "environment_response", "continuity_state",
            "optional_flourish", "detail", "additional_direction",
        )
    ).lower()


def infer_acoustic_space(evidence: str) -> tuple[str, str]:
    text = evidence.lower()

    def has(*words: str) -> bool:
        return any(word in text for word in words)

    if has("car interior", "vehicle cabin", "inside the car", "taxi", "van", "车内", "車內"):
        return (
            "vehicle cabin",
            "continuous enclosed cabin tone, engine and road vibration, with exterior traffic filtered through the windows",
        )
    if has("elevator", "lift interior", "电梯", "電梯"):
        return (
            "small elevator interior",
            "continuous ventilation and lift-motor hum with restrained hard-surface reflections",
        )
    if has("corridor", "hallway", "stairwell", "passage", "走廊", "楼梯间", "樓梯間", "通道"):
        return (
            "narrow corridor",
            "continuous building room tone with directional footsteps and short reflections from the corridor walls",
        )
    if has("cafe", "coffee shop", "restaurant", "咖啡馆", "咖啡館", "餐厅", "餐廳"):
        return (
            "occupied cafe interior",
            "continuous low cafe room tone, restrained tableware and distant non-intelligible patron movement",
        )
    if has("lobby", "grand hall", "large hall", "ballroom", "大堂", "大厅", "大廳", "礼堂", "禮堂"):
        return (
            "large interior hall",
            "continuous spacious interior room tone with audible but controlled early reflections",
        )
    if has("office", "control room", "monitor room", "办公室", "辦公室", "监控室", "監控室"):
        return (
            "furnished office interior",
            "continuous HVAC, computer and practical appliance room tone with short furnished-room reflections",
        )
    if has("hotel room", "bedroom", "apartment", "living room", "small room", "房间", "房間", "卧室", "臥室", "公寓", "客厅", "客廳"):
        return (
            "small furnished interior",
            "continuous quiet room tone, subtle exterior bleed and short reflections from the visible furnishings",
        )
    if has(
        "outdoor", "exterior", "street", "road", "rooftop", "courtyard", "forest",
        "field", "garden", "harbour", "harbor", "airport tarmac", "户外", "戶外", "街道",
        "道路", "屋顶", "屋頂", "庭院", "森林", "田野", "花园", "花園", "海港",
    ):
        return (
            "open exterior",
            "continuous open-air ambience with perspective-correct wind and distant location activity, without an enclosed-room tail",
        )
    return (
        "the visible real-world location",
        "continuous location tone inferred only from visible surfaces, weather, machinery and activity",
    )


def infer_camera_distance(framing: str) -> str:
    text = framing.lower()
    if "extreme close" in text or "micro" in text or "微距" in text:
        return "very close to camera, approximately 0.3-0.6 metres"
    if "close-up" in text or "close up" in text or "近景" in text or "特写" in text or "特寫" in text:
        return "close to camera, approximately 0.6-1.2 metres"
    if "medium close" in text:
        return "near camera, approximately 1-1.8 metres"
    if "extreme wide" in text or "远景" in text or "遠景" in text:
        return "far from camera, approximately 10 metres or more, with natural distance attenuation and reduced vocal detail"
    if "wide" in text or "全景" in text:
        return "several metres from camera, approximately 5-10 metres, with audible distance attenuation"
    if "medium" in text or "中景" in text:
        return "at conversational camera distance, approximately 2-3 metres"
    return "at the distance visibly implied by the framing, with matching perspective and attenuation"


def infer_screen_position(evidence: str) -> str:
    text = evidence.lower()
    if re.search(r"\b(?:screen|frame)\s+left\b|画面左|畫面左|左侧|左側", text):
        return "on screen left; localize the voice and Foley slightly left"
    if re.search(r"\b(?:screen|frame)\s+right\b|画面右|畫面右|右侧|右側", text):
        return "on screen right; localize the voice and Foley slightly right"
    if re.search(r"\b(?:off[ -]?screen|outside (?:the )?frame)\b|画外|畫外", text):
        return "off screen in the explicitly indicated direction; preserve plausible distance and obstruction"
    if re.search(r"\bbackground\b|远处|遠處|后方|後方", text):
        return "in the background of the frame; keep the voice more distant than foreground Foley"
    return "near the visible subject position, normally centre unless the composition clearly places the speaker left or right"


def infer_speech_state(evidence: str, dialogue_rows: Iterable[Mapping[str, object]]) -> str:
    rows = list(dialogue_rows)
    text = " ".join(
        [evidence.lower()]
        + [str(row.get("delivery", "") or "").lower() for row in rows]
    )
    if any(word in text for word in ("whisper", "under breath", "压低", "壓低", "耳语", "耳語", "低声", "低聲")):
        return "low, guarded conversation with natural breath and restrained projection"
    if any(word in text for word in ("shout", "yell", "scream", "叫喊", "大喊", "呼救", "吼")):
        return "an emotionally motivated shout with real projection into the visible space, never clipped or studio-clean"
    if any(word in text for word in ("phone", "telephone", "手机", "手機", "电话", "電話")):
        return "natural conversational speech appropriate to the visible phone interaction and its actual on-screen source"
    if rows:
        return "natural conversational volume and performance, with breathing, micro-pauses and emotion matching the authored delivery"
    return "no human speech unless an exact Timeline Dialogue, Voice-over or Lyrics event is present"


def infer_foley(evidence: str) -> str:
    text = evidence.lower()
    rows: list[str] = []

    def add(label: str, *words: str) -> None:
        if any(word in text for word in words) and label not in rows:
            rows.append(label)

    add("footsteps, landings and surface contact", "walk", "run", "step", "foot", "跑", "走", "踏", "脚步", "腳步")
    add("cloth and body-movement rustle", "coat", "dress", "cloth", "shirt", "衣", "裙", "外套")
    add("phone handling, taps and authored interface cues", "phone", "smartphone", "手机", "手機")
    add("doors, locks, latches and handle contact", "door", "lock", "latch", "门", "門", "门锁", "門鎖")
    add("keyboard, desk and object handling", "keyboard", "desk", "computer", "键盘", "鍵盤", "桌", "电脑", "電腦")
    add("vehicle controls, doors, engine and tire contact", "car", "vehicle", "taxi", "drive", "车", "車", "驾驶", "駕駛")
    add("water, rain and wet-surface contact", "water", "rain", "pond", "river", "水", "雨", "池", "河")
    add("weapon movement and exact contact transients", "sword", "knife", "gun", "blade", "剑", "劍", "刀", "枪", "槍")
    if not rows:
        return "exact-frame Foley only for the visible body movement, handled objects and surface contacts in this Shot"
    return ", ".join(rows[:4])


def build_native_audio_profile(
    shot: Mapping[str, object],
    dialogue_rows: Iterable[Mapping[str, object]] = (),
    *,
    inherited_space: tuple[str, str] | None = None,
) -> NativeAudioProfile:
    evidence = _evidence(shot)
    space, ambience = infer_acoustic_space(evidence)
    if space == "the visible real-world location" and inherited_space is not None:
        space, ambience = inherited_space
    return NativeAudioProfile(
        acoustic_space=space,
        camera_distance=infer_camera_distance(str(shot.get("framing", "") or "")),
        screen_position=infer_screen_position(evidence),
        speech_state=infer_speech_state(evidence, dialogue_rows),
        ambience=ambience,
        foley=infer_foley(evidence),
    )


def native_audio_direction_text(
    profile: NativeAudioProfile,
    *,
    has_authored_voice_over: bool = False,
    music_requested: bool = False,
) -> str:
    narration_rule = (
        "Only the exact authored Voice-over Timeline event may sound off-screen; no other narration or extra dialogue."
        if has_authored_voice_over
        else "No narration, announcer voice, voice-over character or extra dialogue is permitted."
    )
    music_rule = (
        "Use only the non-diegetic music defined by the active music policy and the "
        "non_diegetic_music section, subordinate to exact dialogue."
        if music_requested
        else "Generate no background music or score."
    )
    return (
        f"Acoustic space: {profile.acoustic_space}. Speaker-to-camera distance: {profile.camera_distance}. "
        f"Speaker screen position: {profile.screen_position}. Speaking state: {profile.speech_state}. "
        f"Continuous environment: {profile.ambience}. Picture-synchronous Foley: {profile.foley}. "
        "Every voice, ambience and Foley event is diegetic sound emitted by a real source inside the visible scene, "
        "except an explicitly authored Voice-over or Music Timeline event. Preserve natural production-sound perspective, "
        "location bleed and physically plausible early reflections. Never use an intimate recording-booth close-mic sound, "
        "dry studio voice, announcer delivery, artificial word echo or repeated performance. "
        f"{narration_rule} {music_rule}"
    )


def environment_continuity_text(
    previous: NativeAudioProfile | None,
    current: NativeAudioProfile,
) -> str:
    if previous is None:
        return (
            f"Establish {current.acoustic_space} ambience from the first frame; its room tone or outdoor bed begins naturally "
            "without borrowing any sound from an earlier generated segment."
        )
    if previous.acoustic_space != current.acoustic_space:
        return (
            f"Acoustic-space transition: change from {previous.acoustic_space} to {current.acoustic_space} at the visual cut. "
            "End the earlier space naturally and establish the new ambience immediately; do not carry the earlier room tail, "
            "dialogue, music or audio texture into this Shot."
        )
    distance_changed = previous.camera_distance != current.camera_distance
    if distance_changed:
        near_now = any(word in current.camera_distance for word in ("very close", "close to camera", "near camera"))
        perspective = (
            "The closer framing makes the direct voice more immediate and detailed while reflections become proportionally less prominent."
            if near_now
            else "The wider framing adds natural distance attenuation and environmental proportion without changing the location."
        )
        return (
            f"Remain in the same {current.acoustic_space}; preserve the continuous ambience and source positions from the preceding Shot. "
            f"Only camera perspective changes. {perspective}"
        )
    return (
        f"Remain in the same {current.acoustic_space}; continue the same environmental bed, acoustic character, "
        "speaker distance and screen-localized source positions across the cut without restarting or duplicating any sound."
    )


def audio_reference_intent_text(
    references: bool | Iterable[str],
) -> str:
    if isinstance(references, bool):
        tags: list[str] = ["the active reference"] if references else []
    else:
        tags = [str(item).strip() for item in references if str(item).strip()]
    if not tags:
        return "No Audio or Video reference is used as a sound source for this Shot."
    return (
        "Active acoustic references: " + ", ".join(tags) + ". "
        "Use active real-world Audio or Video reference sound only to infer spatial acoustics, environmental bed, "
        "speaker distance and on-location texture. Do not copy, replay or imitate any words from the reference. "
        "Do not use a reference character's voice or timbre to replace the Timeline Speaker/Dialogue, and do not treat "
        "a preceding generated segment as an audio reference."
    )


def profile_as_dict(profile: NativeAudioProfile) -> dict[str, str]:
    return asdict(profile)

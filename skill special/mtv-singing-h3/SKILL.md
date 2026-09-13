---
name: mtv-singing-h3
description: |
  Create a MiniMax H3 singing music video with P1 as the exact lead singer, P2/P3 as identity-locked supporting people, P4 as the scene master, A1 as the unchanged song and final Master Audio, and exactly five P4-derived scene-state references in P5-P9. Use for lip-synced MTV, performance video, singing video, music performance, 对嘴唱歌, 唱歌视频 and 音乐MV requests.
---

# MTV Singing H3

Apply this Special Skill with the bound Default H3 Prompt Writing Skill. The task is a performance-directed music video, not a request for H3 to compose or imitate a new song.

## Required reference contract

- `@P1` is S1 and the only lead singer. Preserve P1's exact recognizable face, age, skin, hairstyle, body, full wardrobe and accessories in every frame.
- `@P2` and `@P3` are distinct supporting people. Preserve each identity separately. They may react, dance or share the scene, but they do not sing, inherit P1's face or copy P1's lip motion unless the user explicitly authors another singer.
- `@P4` is the scene master. It owns location geometry, camera axis, perspective, colour, colour temperature, weather, surface materials, practical-light direction and atmosphere. It owns no P1-P3 identity.
- `@A1` is the only continuous Master Audio and the authoritative sung performance.

If any explicitly referenced source is not loaded, report the exact missing ID before Apply. Never substitute another slot.

## A1 exact-master rule

Use the original A1 recording without changing its singer, lyrics, melody, pitch, key, tempo, rhythm, phrasing, breaths, instrumentation or selected Timeline window. A1 is not merely a BPM, mood, timbre or composition suggestion.

H3 receives the matching A1 source window to drive performance timing. P1's visible mouth shapes, jaw, breaths, eye expression, head accents and gestures follow that exact window. After generation, the Studio replaces H3's synthesized audio stream with the unchanged A1 Timeline master. Do not regenerate, imitate, transpose, pitch-correct, time-stretch, loop, restart, remix or layer a second song, singer, TTS voice or score over A1.

When a later hidden Segment starts, its A1 source time equals that Segment's Timeline start. Never replay the beginning of A1 at a cut.

## Lyrics and lip-sync

Do not invent lyrics from the scene or from an instrumental analysis. If the user did not write exact lyrics in the Design Requirement, create no Lyrics, Dialogue or Voice-over Text Layer; follow A1 acoustically and visually.

If the user supplies exact lyrics, preserve them verbatim in independent `lyrics` Text Layers on A6, assign `speaker=S1`, `lip_sync=true`, and align them to A1. Never use TTS to replace the sung performance. A lyric layer is timing/edit metadata; A1 remains the audible master.

Keep P1's face and mouth readable during active vocals. Use frontal or three-quarter close-up and medium framing for key phrases, with natural performance coverage between them. Never make P2/P3 appear to sing P1's line.

## P5-P9 scene-state generation

Reserve exactly five image references, P5 through P9. Generate them from P4 by source-image transformation when P4 is loaded. They are time-scoped environment and lighting states, not replacement people:

1. P5: establishing performance light and clear singer foreground;
2. P6: restrained verse light variation;
3. P7: musical lift with motivated reflections and depth;
4. P8: peak performance lighting and environmental energy;
5. P9: resolved final hero-frame light state.

Every state preserves P4's architecture, layout, camera axis, lens perspective, palette, colour temperature, weather and material logic. Leave compositing space for P1-P3. Do not draw a principal singer, clone a person, add an unrelated location or create one new image per Shot. If a requested P5-P9 already exists, reuse it in its time range.

## MTV camera and editing grammar

Analyze A1 beats, onsets, vocal phrases, breaths and accents. Use 2-4 second performance Shots, cutting at musical boundaries without cutting an active vowel. Each Shot receives one primary camera move. Mix stable frontal performance, restrained lateral tracking, motivated push-in, profile/three-quarter coverage, support reaction and a final hero composition. Movement responds to A1; it never becomes random visual motion.

Use P4/P5-P9 to preserve one coherent world across cuts. Keep P1-P3 grounded with consistent scale, contact shadows, colour temperature and light direction. The final 0.5-1.0 seconds resolves the performance in a stable pose without starting a new lyric or large action.

## Delivery gate

Before returning Studio Director Design JSON, verify:

- P1 is S1 and the only lead singer;
- `lip_sync=true` for every user-authored lyric layer;
- P2/P3 remain support identities and do not replace or merge with P1;
- P4 controls the scene and P5-P9 are P4-derived environment states;
- A1 is the sole exact final soundtrack, not a style reference;
- no invented lyrics, second singer, TTS vocal or replacement score exists;
- target duration remains the requested A1 window and is not extended by invented lyrics;
- Shots cover the complete duration without gaps or overlap;
- final hold is stable and A1 is never restarted at Segment boundaries.

---
name: ai-movie-making-of-4dx
description: |
  Create a duration-budgeted immersive live 4DX cinema showcase: 15 seconds for one selected effect plus 5 seconds per additional effect, up to 60 seconds for all ten. Keep the movie-screen event, active theatre effects, spatial light and sound, and varied audience reactions visible together without narration or non-diegetic music.
---

# AI Movie Making-of / VFX Breakdown / 4DX Scene Composer

Apply this Special Skill together with the Default H3 Prompt Writing Skill. This is an audience-centred live 4DX experience film, not a voice-over tutorial, character-extraction explanation, ordinary story with decorative effects, or list of movie titles.

## Required Film Format

Build one chronological film at the effect-count duration floor. A complete ten-effect film requires 60 seconds. Use this order:

1. a half-second active-auditorium entry;
2. Pitch — an original fighter-jet takeoff or steep elevation-change demonstration;
3. Roll — an original high-speed corner or banking demonstration;
4. Heave — an original vertical drop, lift or landing demonstration;
5. Wind — an original tornado, storm or high-speed airflow demonstration;
6. Air Shot — one original visible near-miss with a short directional air burst;
7. Vibration — an original machine, creature or structural-rumble demonstration;
8. Impact — one original collision or hit with a precise impulse;
9. Flash — one original lightning, ignition or energy-release demonstration;
10. Fog / Smoke — an original fire, dust or atmospheric-pressure demonstration;
11. Water / Rain — an original rain, spray or wave-impact demonstration;
12. a half-second residual-effect hold.

If the user deselects an effect in Design, omit only that effect chapter and redistribute time across the remaining chapters. When all ten are selected, all ten must be visibly demonstrated; none may be skipped merely because Qwen's draft omitted a causal source.

Resolve the minimum duration from the selection count: the first selected effect requires 15 seconds and every additional effect adds 5 seconds. This gives 1=15s, 2=20s, 3=25s through 10=60s. Preserve a longer authored target. If an authored target is shorter than this floor, raise it automatically and write the authored target, selected count, calculated minimum and resolved duration into the managed `4DX EXPERIENCE CONTROL` block. The resolved value owns the actual Director Timeline duration.

Every effect chapter is a compact live Making-of unit:

1. keep a purpose-built premium 4DX auditorium, movie screen, three or more motion-seat rows and multiple distinct adult viewers readable together;
2. show the polished original movie event and visible physical cause on the screen;
3. let exactly one effect-bearing foreground element visibly cross the screen plane, occlude a small part of the still-readable screen border and continue into the air above the front rows;
4. keep the corresponding wind, water, fog, flash, seat or air mechanism visibly active in the auditorium;
5. give viewers varied, effect-specific body, face, clothing and social reactions rather than identical or static responses;
6. make front-row viewers react first in the incoming direction, middle rows a fraction later and rear rows with a smaller delayed response;
7. synchronize screen direction, theatre mechanism, interactive light, sound and human response for at least 99% of the chapter;
8. store the causal Physical Event and editable 4DX Event separately.

## Screen-Plane Breakout

An ordinary movie playing inside a rectangular screen is a failure. Begin the event inside a visibly framed screen, then create one continuous stereoscopic depth bridge into the auditorium. A leading edge, spray, smoke layer, fragment, pressure ripple or light branch must briefly overlap the physical screen border; border occlusion proves that the element has moved in front of the screen plane. Continue the same direction, illumination, particles and atmosphere above the front rows and into the matching practical effect.

Keep one source subject. Never duplicate an aircraft, vehicle, person, creature or source object, never place a second full-size copy among the seats, and never substitute a detached hologram, portal or floating rectangular panel. The projected extension must not collide with a viewer. It triggers directional surprise and avoidance while the real auditorium devices supply the physically readable wind, mist, smoke, flash, vibration or seat response.

The result must read as ten different film-effect demonstrations. Never return the older sequence of Source Photography, Reference Analysis, Character Extraction, Environment Reconstruction and Scene Assembly as the main story.

## Reference Authority

Read every enabled `@P`, `@V` and `@A` through this authority order:

1. explicit user mapping;
2. user lock and authored Clip Prompt;
3. uploaded pixels or samples;
4. AI Enrich;
5. BLIP, VAD, Whisper or beat analysis;
6. conservative Skill inference.

Never infer a landmark, character, object, style or location from a filename. Do not assign fixed meanings to P1-P9. A Picture can be a character, object, environment, source plate, action state, matte or analysis-only control according to evidence. Reuse compatible loaded media first. Each selected demonstration may request at most one time-scoped Z-Image scene plate, with no alternate takes or one-image-per-Shot expansion.

## Visible Film and Studio Graphics

H3 renders the screen event, visible theatre mechanism, interactive auditorium light, environmental output and audience reaction in one continuous space. Exact chapter names, arrows, parameter values and comparison labels belong to editable Studio `on_screen_text` or graphic layers. Do not ask H3 or Z-Image to draw UI, HUD, charts or technical lettering.

## Physical Events

For each candidate event identify:

- source and target;
- contact, near-miss or environmental trigger;
- direction, magnitude, onset, duration and decay;
- material and environmental response;
- source Shot and exact Timeline range.

A response cannot begin before its visible cause. Camera movement is not physical force and is never seat movement.

## 4DX Preferences

The Design page owns ten selectable chapters: Pitch, Roll, Heave, Wind, Air Shot, Vibration, Impact, Flash, Fog/Smoke and Water/Rain. All ten are selected by default. Selecting an effect requires a visible screen cause, active auditorium output and audience feedback throughout its chapter.

## Immersive Camera

Use an FPV camera as an invisible spectator moving through the auditorium. Translate physically between rows, then make smooth wide spatial arcs around the central reacting audience cluster while keeping the screen readable. During the screen-plane crossing, hold a three-quarter side-aisle composition where the screen border, protruding element and audience faces are simultaneously readable. Do not cut to an isolated front-facing crowd shot that loses the screen. Never show a drone. Never spin the camera in place, barrel-roll, zoom out as padding or lose the level spatial relationship between screen, seats and viewers.

Keep Physical Events and 4DX Events separate and link them with stable IDs. Automatic events use `generated_by=AUTO`. Manual Timeline events outrank automatic suggestions and may not be silently replaced. Intensity controls event strength; density controls frequency. Do not conflate them.

## Native Audio Boundary

Use H3 native audio exclusively. Every active chapter must keep four spatial layers clearly audible together: the movie event from the front screen speakers; close motion-seat motors and mechanism Foley; directional wind/water/fog/air/vibration/impact equipment synchronized with the visible breakout; and staggered audience breaths, gasps, short cries, laughter, clothing and seat contact. Foreground physical effects and audience reactions outrank the quiet projector or room-tone bed. Generate no voice-over, dialogue, announcer, studio voice, soundtrack, score or background music. This Skill owns `MUSIC OFF` and overrides a global `MUSIC AUTO` setting during actual H3 compilation. Do not add TTS replacement, source separation, FFmpeg reverb, EQ, convolution reverb or post-generation remixing.

## Delivery Gate

Before returning Director Design JSON, verify:

- duration satisfies the selected-effect budget and every frame is covered by one chronological Shot;
- every selected effect owns one dedicated Making-of chapter and all ten chapters exist under the default selection;
- enabled Media Pool evidence is represented in a reference-role ledger without filename inference;
- missing references are minimal and time-scoped;
- every used 4DX event links to a visible Physical Event;
- each selected effect keeps screen cause, active theatre mechanism and readable audience response visible together for at least 99% of its chapter;
- the venue is a purpose-built cinema, never a banquet hall, conference room, computer lab, office or gaming simulator;
- no Voice-over, Dialogue, Lyrics or non-diegetic music layer exists;
- audience reactions are varied, directional and caused by the current effect;
- every effect chapter proves forward depth by occluding part of the visible screen border, while preserving exactly one source subject and a staggered front-to-rear audience response;
- FPV camera movement translates around audience rows without an in-place 360-degree spin or visible drone;
- no copyrighted character, logo, title or exact scene recreation is requested; the film examples are original genre archetypes;
- camera motion is never mapped as seat motion;
- exact technical labels are editable Timeline graphics, not generated-image text;
- H3 native audio remains unmodified;
- the final second is a stable hold with no new speech, action or effect.

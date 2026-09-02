---
name: dark-rescue-h3
description: |
  Design production-ready MiniMax H3 first-person police or firefighter rescue stories from a short place-based request, using the user's proven dark rain-soaked industrial lighting, physical-damage, location-sound, original Mandarin dialogue and restrained first-person narration grammar. Use for fictional abandoned buildings, damaged offices, schools, alleys, Chinatown lanes, dense historical urban interiors and non-graphic disaster rescue scenes that must become editable Studio Director Design JSON.
---

# Dark Rescue H3 Director

Apply this Special Skill together with the bound Default H3 Prompt Writing Skill. This Skill owns story invention, location adaptation, first-person rescue staging, the proven light/effect vocabulary and editable Timeline design. The Default Skill owns the final MiniMax H3 Ref2VA structure and request-local reference tags.

## Interpret a Short Request

Expand a request such as “create a 45-second rescue inside an abandoned Wall Street building with suitable dialogue and narration” without asking for details that can be inferred safely.

Preserve every user-specified duration, location, role, language, aspect ratio, character, reference, ending and safety limit. When omitted, use these defaults:

- 45.00 seconds on the 0.5-second grid;
- live-action cinematic realism;
- Mandarin Chinese for all spoken words;
- one first-person rescuer and one adult trapped person as the only intelligible human voices;
- a fictional damaged or decommissioned place inspired by the named real location, never a claim that a real school, street, landmark or building is abandoned or suffered a disaster;
- non-graphic danger, rescue and a transition from oppressive darkness to a small physically motivated exterior light.

Choose the responder from the hazard. Use a police officer for a locked, abandoned, alley, missing-person or search environment. Use a firefighter for active smoke, fire alarms, burst sprinklers, major structural damage or a damaged high-rise. Do not switch profession midway.

Create a new title, exact rescue problem, obstruction, route change, dialogue and narration for every request. The five proven stories are a visual and structural library, not lines to copy. Never reuse “follow my light,” “do not look back,” or the same final aphorism automatically.

## Keep the Speaking Cast Executable

Default to two stable vocal identities:

- `S1`: the trapped adult, normally female when the story does not specify otherwise;
- `S2`: the first-person rescuer, normally male when the story does not specify otherwise; the same S2 voice may deliver restrained first-person internal narration.

Use radio squelch, coded beeps and indistinct dispatch texture as sound design instead of inventing a third intelligible dispatcher voice. Add a third speaking identity only when the user explicitly requires it and the current Studio schema supports it.

Write every Dialogue and Voice-over line as an independent timed `text_layers` row with `explicit_user_requested=true`. Keep exact spoken words out of `subject_action`, `environment_response`, `continuity_state`, `optional_flourish`, image prompts and visible signage. Use `dialogue` for audible in-scene speech and `voice_over` only for S2’s brief internal reflection. Do not create Lyrics.

Generate original, concise speech that a person under pressure could actually say. Across a default 45-second story, use approximately:

- one short arrival or status line from S2;
- one location-specific plea or orientation clue from S1;
- one practical reassurance or movement instruction from S2;
- one route-change acknowledgement when the obstruction changes;
- one short final line from S1 or S2;
- no more than two short S2 Voice-over passages, each one or two sentences.

Budget the words at a natural Mandarin rate with breath and hesitation. Extend or rebalance the owning Shot if needed; never accelerate unnaturally, paraphrase, repeat, start early, change speaker or cut off the final word.

Respect the Design subtitle switch. When subtitles are OFF, do not create `on_screen_text` from speech and do not burn words into generated images. When subtitles are ON, create editable synchronized subtitle Text Layers only; never ask H3 or Z-Image to invent typography. Add a final slogan only when the user explicitly asks for visible ending text.

## Build the Rescue as Causal Shots

For a 45-second request, default to nine chronological five-second Shots grouped into three native 15-second movements. Vary a boundary only when speech needs it, while retaining complete 0.00–45.00 coverage.

1. **0–5 — exterior hook and arrival:** establish the named location’s wet exterior, the responder’s role and one concrete sign that somebody is inside.
2. **5–10 — threshold crossing:** open, force or navigate one entrance; exterior sound closes down as the interior acoustic space takes over.
3. **10–15 — first search clue:** flashlight reveals location-specific damage and one audible or physical clue. End on a simple readable direction, not a new multi-beat action.
4. **15–20 — obstacle and deeper route:** climb, crawl or pass one damaged obstruction with visible contact physics.
5. **20–25 — locate the trapped adult:** reveal exactly one trapped person and establish the obstruction without rescuing and evacuating in the same instant.
6. **25–30 — controlled release:** remove no more than two blocking elements, make contact and end with the trapped person able to move.
7. **30–35 — route change:** one physically caused failure blocks the known exit; the rescuer chooses one alternate route.
8. **35–40 — final ascent or exit approach:** move through the alternate route and open the final door, hatch or broken threshold.
9. **40–45 — exterior release and Final Hold:** establish open-air distance, the rescued person’s stable position and one location-linked view; finish with a quiet consequence, not a fresh hazard.

For other durations, preserve the same causal order but scale the number of Shots. Never squeeze all nine beats into 15 seconds. Each five-second interval permits at most three must-complete physical beats, two contact consequences and two optional flourishes.

For every Shot state:

- one story responsibility;
- one primary camera movement or a stable camera;
- `subject_action` as the must-complete causal action only;
- `environment_response` as a visible result of contact, force, water, wind, electricity or structural movement;
- `continuity_state` with incoming and outgoing rescuer hand/tool state, victim pose, travel direction, door/obstruction state, flashlight direction and unresolved motion;
- `optional_flourish` containing expendable mist, drifting paper, small sparks or secondary light motion;
- `additional_direction` containing first-person visibility, performance, exposure and location rules.

At 15- and 30-second native boundaries, leave one clean outgoing physical state. The next Segment inherits it and immediately advances; it must not replay the door opening, climb, discovery, hand grasp, collapse or route decision. The preceding 24 frames are visual motion context only, never an audio reference.

## Lock First-person Continuity

The camera remains the rescuer’s eye line. It may show only physically plausible fragments of the rescuer: wet or dusty gloves, a flashlight, radio, helmet rim, uniform sleeve, reflective strip, firefighter axe or one role-correct tool. Never cut to a third-person hero view, reveal the rescuer’s face, float outside the body or show both of the rescuer’s hands while one hand is holding the camera/tool impossibly.

Maintain these ledgers across every Shot and Segment:

- exact count and identity of visible people;
- responder profession, gloves, sleeve, helmet, radio, flashlight and tool ownership;
- trapped person identity, clothing, dirt/wetness, mobility and hand contact;
- door, debris, staircase, pipe, cable, water and route states;
- flashlight on/off state, beam direction and exposure adaptation;
- room geography, elevation, screen direction and distance already travelled.

A blocked route remains blocked. A moved cabinet stays moved. A broken lock stays broken. Water continues downhill. Dust follows a collapse and settles. A person cannot appear upstairs without a visible path.

## Use Only the Proven Visual-effect Palette

Select effects from the following closed palette. Every chosen effect must have an established physical source and narrative job. Do not stack every effect into every Shot and do not invent supernatural energy, creatures, impossible light or unexplained spectacle.

1. **Claustrophobic low-key lighting:** keep roughly 80–90% of the image in deep shadow while exposing the active hand, obstacle, face or route clearly enough to read.
2. **Flashlight as weapon:** the tactical flashlight is the stable visual window; cold white inside the beam, near-black outside it. The beam reveals one clue or action at a time.
3. **Dynamic lighting:** flashlight, patrol searchlight, practical sign or alarm reflections move across wet walls, metal doors, glass and standing water as their real source moves.
4. **Volumetric lighting and scattering:** show visible beams only through established rain mist, steam, dust, smoke or water vapour.
5. **Chiaroscuro and hard terminating lines:** use hard-edged local highlights and deep negative space instead of uniform fill light.
6. **Silhouette and backlighting:** use a real doorway, broken window, moonlight, streetlight or rescue light to produce a restrained rim-lit silhouette; never imply a monster.
7. **Malfunctioning neon or tube-light flicker:** use short, irregular, physically motivated failure from water or damaged wiring. Never use continuous high-frequency strobing, especially during critical action or speech.
8. **Moving mechanical shadows:** a previously visible fan or vent blade may cut and stretch a fixed practical light across the walls.
9. **Emergency red beacon:** use only after an alarm or backup circuit has been established; its rotation periodically colours mist and wet surfaces, then returns them to shadow.
10. **Wet high-specular surfaces:** rainwater, condensation, leaking pipes, oil film and damp industrial residue create local specular hits. “Organic wetness” means material texture only—never slime, flesh or an alien organism.
11. **Industrial IES tube light:** one damaged practical fixture may briefly expose a local zone while the remaining space stays dark.
12. **Retro-industrial grunge:** use real rust, peeling paint, mould, soaked paper, bent mesh, old machinery and damaged utilities; keep the result photoreal and non-supernatural.

Light changes must preserve exposure continuity. A light can fail, rotate or be occluded only after its source is shown or described. Use no random flicker to disguise a face, teleport or continuity error.

## Choose a Proven Location Module

Use the closest module, then adapt it to the user’s actual place. Never claim a real named location is currently damaged or abandoned.

### Abandoned academic building

For a fictional Harvard-style, British, American or other old college building, use red brick, stone arches, lecture hall, library, laboratory, old stair and roof access. Proven debris includes soaked books and papers, fallen shelving, cracked blackboard, broken glassware, metal cabinets, burst pipes and failed tube lights. Keep real institution names out of disaster claims.

### Bangkok Yaowarat back lanes

Move from a wet night-market threshold into narrow service alleys, an old hotel or shophouse stair. Use physically plausible Thai and Chinese signage, red lanterns, food carts, plastic stools, rolling shutters, wet boxes, drainage pipes and distant tuk-tuk or motorcycle sound. Keep cultural detail observational rather than stereotyped.

### Kuala Lumpur Petaling Street back lanes

Use red lanterns, old Chinese shop signs, closing stalls, a tea-room or shophouse upper floor, timber stairs, shutters, wet newspapers, fruit crates, drainage roar and distant city/police sound. The rooftop release may suggest Kuala Lumpur’s city glow without inventing a false landmark position.

### Historical Kowloon dense interior

Treat Kowloon Walled City as a clearly fictional historical reconstruction. Use extremely narrow stacked corridors, dense wiring, leaking pipes, rusty doors, timber/metal stairs, small rooms, residual neon and layered roof access. Do not present the historical site as a current inhabited disaster location.

### Damaged high-rise office or Wall Street-inspired tower

Use a fictional decommissioned or damaged office tower inspired by Lower Manhattan or the named financial district. Choose a firefighter when smoke, alarms, sprinklers or major structural damage is active. Proven details include fallen partitions, exposed metal studs, hanging cables, burst sprinklers, pooled water, overturned desks, broken monitors, soaked documents, bent stair rails and a wind-exposed roof or broken-window exit. The final skyline is atmospheric orientation, not a claim about a real building.

For an unlisted place, combine only the nearest structural module with verified generic local materials, weather, signage system and sound. Do not transplant Thai lanterns, British police equipment, Chinese shop signs or American office debris into the wrong place without a story reason.

## Native Location Sound

Build `overall_soundscape` and each Shot’s native audio direction from visible sources. The soundtrack is generated natively by H3; do not request external TTS replacement, source separation, FFmpeg reverb, EQ, convolution or post-production remixing.

Maintain three layers:

1. continuous diegetic ambience appropriate to the visible space;
2. exact-frame Foley from visible contact;
3. foreground Dialogue or S2 Voice-over at the authored time only.

Use the proven sounds that the scene actually supports: post-rain dripping, wet boots, wind through broken windows, distant thunder or siren, radio squelch, damaged electrical buzz, neon/tube-light crackle, metal door impact, timber stair creak, drainage or pipe roar, steam release, fan machinery, alarm pulse, axe/lock contact, debris fall, breathing and open-roof wind.

Match acoustics to space. Alleys and stairwells have short directional reflections; small rooms have brief close reflections; large lecture halls or office floors have longer controlled decay; rooftops and open streets have almost no room tail and less low-mid fullness. When a door closes, exterior ambience becomes filtered and quieter. When the final door opens, the interior tail ends and wind/city distance begins. Never use echo to repeat a word.

Dialogue must sound like live production audio at the visible camera distance, with natural breath and low environmental bleed—not a studio announcer. Keep effects intelligible but below exact speech. Never copy dialogue or voice identity from an Audio/Video reference, and never carry generated audio from the previous Segment.

Respect the Studio music selector:

- `MUSIC AUTO`: plan a low, restrained industrial score with sparse low-frequency pulse or metal texture; increase tension only at the route failure, then introduce a very small warm harmonic release at the final exterior without becoming triumphant.
- `MUSIC OFF`: set `non_diegetic_music` to `N/A` and rely on ambience, Foley and speech.
- `MUSIC TIMELINE`: do not invent automatic score or Music Cues; follow only user-authored Timeline Music Cues.

Music never masks speech and uses no vocals unless the user explicitly requests Lyrics.

## Reference-media Discipline

Use a stable Media Pool source only when it is actually loaded and selected. Cite it only by the exact authored `@P`, `@V` or `@A` ID. A simple request with no explicit `@ID` must never cause the Skill to invent `@P1`, `@P2`, `@V1` or `@A1`.

Reuse valid loaded media before requesting new material. For first-person stories, do not waste an identity image on the unseen rescuer’s face; prioritize the trapped person’s stable identity, the location, a critical obstruction or a native boundary state. Every generated image request depicts exactly one frozen instant, the exact visible person count and the story’s real environment—not a neutral studio background or a sequence of actions.

Time-scope location, damage, victim-pose and boundary references to the Shots that need them. Never let an earlier school, alley, hotel, tea room or office reference leak into a later location. The Virtual Media Pool may hold many logical sources, but each native Segment must remain within the actual 9 Picture / 3 Video / 3 Audio physical reference limit.

## Deliver Studio Director Design JSON

Return one schema-valid Director Design JSON object covering the exact requested duration. Do not return screenplay Markdown or the final six-section H3 prompt from Design; the bound Default Skill and Studio compiler perform that handoff.

Use existing schema fields only. Keep Shots chronological and non-overlapping, cover every frame, and use the 0.5-second grid. Include one Final Hold marker only at the actual ending. Put all speech in `text_layers`, all reusable/generative material in `existing_media_uses` or `media_requests`, and all sound/music direction in the supported sound fields.

Constraints must explicitly preserve first-person camera, identity, uniforms, tools, victim count, route geography, wetness/damage state, light sources, exact speech, non-graphic realism and core-action priority. Optional atmosphere is removed before any core action is delayed or replayed.

## Quality Gate

Before returning the Design JSON, verify:

- the named location is fictionalized responsibly and uses the correct cultural/architectural module;
- the responder profession matches the hazard and stays fixed;
- the camera never leaves first person or reveals an impossible body configuration;
- exactly one trapped person exists unless the user explicitly requests otherwise;
- only S1 and S2 speak by default, and every exact line appears once in editable `text_layers`;
- every five-second action budget is executable;
- every obstruction, tool, door, hand contact, route and light source remains continuous;
- chosen visual effects come only from the proven palette and have visible physical causes;
- no segment replays the preceding boundary action or audio;
- references are real loaded IDs or valid missing-media requests, never invented empty slots;
- subtitles and music follow their Design selectors;
- no blood, corpse, wound close-up, torture, monster, ghost, supernatural event, gratuitous explosion, malformed anatomy, extra limb, excessive strobe, random camera shake, animation, watermark or invented garbled text;
- the Final Hold preserves the completed rescue state and introduces no new action.

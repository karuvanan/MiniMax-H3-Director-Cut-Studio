---
name: beat-synced-entrance-19s
description: |
  Create an exact 19-second cinematic music-led entrance in which P1 meets P2 and P2 meets P3 through visible corridor-corner reveals, then P1 exits toward camera, shows a readable surprise reaction and discovers P4 after an architectural wipe. Generate one P5 populated school-exterior plate and integrate P4's final subjects into it. A1 is the only continuous Master Audio.
---

# Beat-Synced Entrance 19s

Apply this Special Skill with the bound Default H3 Prompt Writing Skill. Reproduce editorial grammar only; never copy copyrighted characters, locations, clothing, logos, social UI or exact pixels from an example film.

## Required Media Contract

Require five loaded sources and never substitute IDs:

- `@P1`: opening subject, first-corner encounter subject and returning campus-exit subject;
- `@P2`: second subject, revealed after P1's corner and carried into P3's corner encounter;
- `@P3`: third featured subject inside the generated corridor;
- `@P4`: final visible subject identities, count, appearance and relative arrangement only;
- `@A1`: full music excerpt and the only Master Audio.

Reserve P5 for one Z-Image environment-population keyframe. If P5 is already loaded, reuse it as the campus environment instead of regenerating it. P5 owns school architecture, road, bus-stop zone, daylight, ground plane, camera axis and secondary school-life people; it never owns a P1-P4 identity.

P3 is a person or featured visual beat, never an environment plate. H3 generates the passage and corners from the Design direction. P1/P2 and P2/P3 intentionally overlap during their encounter beats, but their face, body, wardrobe and accessories remain separate and source-locked.

P4 controls only the final visible subjects: their identities, faces, bodies, hair or fur, wardrobe, accessories, count and relative arrangement. Discard P4's original background. P5 exclusively controls the outdoor environment and background-life population across Beats 4-5. The preceding bridge's final 24 silent frames control only wipe timing and camera-motion continuity.

## Analyze A1 Before Fixing Cuts

Treat A1 as one continuous Timeline master from 0.00 to 19.00 seconds. Analyze beats, onsets, accents, drops and phrase boundaries, then snap cuts to the nearest musically valid 0.5-second grid point.

Use this five-beat fallback when analysis is unavailable:

1. `0.00–6.50s`: P1 entrance and arrival at the first visible corner;
2. `6.50–9.50s`: P1 rounds the corner, meets P2 and hands the camera follow to P2;
3. `9.50–12.00s`: P2 rounds the next corner, meets P3 and hands the camera follow to P3;
4. `12.00–14.00s`: an eyeline cut returns to P1, who exits into campus and completes an architectural wipe at its corner;
5. `14.00–19.00s`: P4 true slow-motion reveal and Final Hold.

Every identity change needs a visible cause: walking reaches a real corner, the wall temporarily occludes the far space, clearing the corner reveals the next already-present subject, and the camera visibly transfers its follow. A person never materializes, morphs from the previous subject or replaces them between adjacent frames.

## Five-Beat Shot Grammar

### Beat 1 — P1 and front-readable models

Generate a coherent cinematic corridor. P1 walks directly toward the camera while it physically tracks backward at stable subject scale. Keep the fashion-model extras unhurried and stationed across natural corridor activities rather than racing past: opening or closing lockers and arranging books; holding books while side-stepping through foot traffic and checking a watch; reading; or leaning near lockers to chat and briefly pat a friend's shoulder. A playful door-frame or ceiling touch is optional only when it does not overload the beat. Every selected model naturally turns head and upper torso to present a frontal or three-quarter face for 1.0–1.5 seconds, with both eyes and facial features unobstructed. End only after P1 reaches a visible corner whose wall enters the composition.

### Beat 2 — P1 meets P2 at a corner

Follow P1 physically around the first corner. The wall briefly occludes the far passage; P2 becomes visible only as the camera clears that geometry and must already be walking in the revealed space. P1 and P2 acknowledge and pass one another, then the camera transfers its follow to P2.

### Beat 3 — P2 meets P3 at a corner

Follow P2 to a second visible corner. Real wall occlusion and lateral parallax reveal P3 already present beyond it; P2 acknowledges P3 and the camera settles on P3. Do not use a hard identity-replacement cut.

### Beat 4 — P1 exits to campus and discovers P4

Make this an indispensable standalone 12.00–14.00-second H3 Render Segment with a Hard Cut at its beginning and no P2/P3 motion-reference frames. Load P1, P5 and the matching A1 source window. P5 fixes the school exterior, background-life people, daylight and camera axis. Place the camera outside at eye level and facing P1. From local 0.00–0.70, P1 crosses the visible threshold toward camera with a clear frontal or three-quarter face and both eyes readable. From 0.70–1.45, P1 sees the off-camera next subject and gives an unmistakable surprise reaction: widened eyes, raised brows and slightly open mouth. From 1.45–2.00, slide behind the adjacent solid wall or door frame until it covers every pixel. Do not deliver a back-only exit.

### Beat 5 — P4 physical slow motion

Carry the final 24 silent frames of Beat 4 into Beat 5 only as wipe and camera-motion reference. P5 remains the immutable environment plate. Use P4 only for its visible subject identities, bodies, wardrobe, accessories, count and relative arrangement; discard P4's source background. Relight and ground P4 naturally inside P5 with consistent scale, foot contact, shared shadows, colour temperature and atmospheric depth. Keep P5's secondary people alive with varied dismissal-time actions such as leaving with backpacks, waiting for a bus, talking in small groups and crossing the road. They remain background scale and never replace or obscure P4. Slow P4's source-consistent motion to 45–60% while A1 remains normal, use only a very small horizontal slide along the P5 camera axis, and lock the final 0.5 seconds.

## Continuous Music Across Segments

A1 plays once. Every hidden H3 Segment receives only the matching A1 source window: its source position equals the Segment Timeline start. Never upload the full A1 opening again for a later Segment, restart it, duplicate it, time-stretch it, replace it or crossfade a second copy.

For example, an H3 Segment beginning at 14.00 seconds receives A1 beginning at source time 14.00 seconds. If the Studio creates a native 15.00-second boundary, the following Segment begins with A1 source time 15.00 seconds. A1 remains at 1x even while P4 action is visually slow.

H3 may generate subtle diegetic corridor room tone, footsteps and cloth movement below A1. Generate no dialogue, voice-over, lyrics or replacement score unless explicitly authored. Set `non_diegetic_music` to `N/A` because A1 already owns the soundtrack.

## Reference Isolation and Image Budget

Do not request Z-Image replacements for P1–P4 and do not generate a corridor Picture. Create exactly one standalone P5 Z-Image environment-population request unless P5 is already loaded. Time-scope the references:

- P1: 0.00–9.50 and 12.00–14.00;
- P2: 6.50–12.00;
- P3: 9.50–12.00;
- P4: 14.00–19.00;
- P5: 12.00–19.00, school-exterior environment and background-life plate;
- A1: 0.00–19.00, continuous.

A Segment may contain multiple timed references, but its compiled prompt and loader set must respect those ranges. Beat 4 uses P1+P5+A1. Beat 5 uses P4+P5+A1 plus Beat 4's final 24 silent frames as motion-only continuity.

Compile exactly three hidden generation windows: 0.00–12.00, 12.00–14.00 and 14.00–19.00 seconds. The middle window executes only Beat 4 with P1, P5 and the matching A1 source slice; the final window uses P4, P5, its matching A1 slice and Beat 4's final 24-frame motion reference. Never merge Beat 4 back into the opening request.

## Visible-Image Exclusions

No play buttons, transport controls, like counters, comments, app chrome, subtitles, logos, watermarks or unrelated words. No visible drone, camera, phone, gimbal, operator, crew or equipment reflection.

## Delivery Gate

Return one schema-valid Director Design JSON covering exactly 0.00–19.00 seconds with five chronological, non-overlapping Shots. Before delivery verify:

- P3 is visible as the third featured subject and is never a corridor;
- the corridor is generated by H3 and remains coherent through Beats 1–3; Beat 4 visibly crosses its exit into the outdoor campus;
- corridor models move slowly, perform varied grounded activities and show readable frontal or three-quarter faces for 1.0–1.5 seconds;
- P1→P2 and P2→P3 introductions visibly use walking, corner occlusion, reveal and camera-follow handoff;
- P1's frontal face, surprised expression, outdoor-campus reveal and complete architectural wipe all occur inside their dedicated 12.00–14.00-second Render Segment;
- P5 appears in the Media Pool as the sole outdoor environment-population plate and is active only from Beat 4 onward;
- P4 subjects retain exact identity and arrangement but are relit and grounded inside P5, with no P4 source background remaining;
- overlapping encounter ranges never blend P1/P2/P3 identities;
- A1 source time advances continuously through every Segment;
- P4 begins with Beat 4's final 24 silent frames as wipe/camera-motion continuity rather than an environment source;
- P4's source background is absent while its subjects keep their exact identity, count and arrangement;
- P5 campus geometry, light, background life, ground plane and camera axis remain stable through a small horizontal slide;
- the last 0.5 second is a stable Final Hold with no new action.

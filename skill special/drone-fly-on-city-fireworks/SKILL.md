---
name: drone-fly-on-city-fireworks
description: Create cinematic photoreal MiniMax H3 night-city drone flights with a route-controlled 360-degree landmark orbit and physically continuous fireworks, smoke, reflections, exposure and native sound. Use when the user wants an aerial skyline celebration with loaded scene and route references; not for daylight flights, static images or character-led scenes.
---

# Drone City Fireworks Director for MiniMax H3

Apply this Special Skill with the bound Default H3 Prompt Writing Skill. Produce an editable, chronological Director Design whose camera flight and fireworks can be compiled directly into H3. Preserve the user's exact duration, aspect ratio, named city, landmark, weather, start/end composition and MUSIC setting.

## 1. Required Reference Roles

Require two genuinely loaded Media Pool Pictures:

- `@P1` is the scene master and opening frame. Preserve its real skyline geometry, landmark count and spacing, roads, weather, time, light direction, exposure, colour grade, atmosphere, lens height and visual effects.
- `@P2` is route-only analysis data. Extract only its start, meaningful turns, curve direction and endpoint, then express those as abstract camera movement. It must never become an H3/Z-Image visual reference, Timeline clip, start/end frame, style source, composition source or identity anchor.

If either reference is missing, hard-block and name the missing Picture. Never invent a Media Pool ID.

For Design JSON, explicitly register P1 as `media_type="image"`, `usage="h3_reference"`; register P2 as `media_type="image"`, `usage="analysis_only"`, `reuse_policy="whole_design"`. P2 may remain in the Virtual Media Pool but consumes no physical H3 Picture slot and is absent from all uploads and loaders.

## 2. Route and Orbit

Reduce P2 into 3–6 meaningful planning waypoints in normalized screen coordinates. Preserve every important bend and the original start/end direction; never claim GPS, metres or real telemetry from a 2D drawing. Before rendering, translate waypoint data into natural physical camera language without P2, WP labels, coordinates, red lines, map graphics or navigation terminology.

Default to one smooth wide clockwise orbit around the named landmark while gradually rising. Unless the user asks otherwise:

- begin low and forward-left, facing the landmark;
- advance with stable altitude transition and realistic drone inertia;
- complete exactly one continuous 360-degree orbital yaw;
- keep the target readable and the horizon level;
- use natural parallax and exposure adaptation;
- avoid towers, roofs, cables, trees, traffic and people;
- finish high on the right, centre the landmark, decelerate and hold for one second.

Never reverse direction, repeat the orbit, teleport, pass through architecture or allow the skyline geometry to flicker.

## 3. Shot and Segment Plan

Use chronological, gap-free, non-overlapping Shot Blocks on the 0.5-second grid. Use roughly one Shot per 4–6 seconds and one primary camera movement per Shot. Each Shot must state:

- must-complete camera/subject action;
- environment response;
- incoming continuity state;
- outgoing continuity state;
- optional flourish that may be dropped before any required action.

For 15 seconds, prefer three phases:

1. **Approach / ignition**: establish the landmark and begin the orbit; only a few distant rooftop launches appear.
2. **Side reveal / escalation**: gold, white and deep-red bursts expand behind and above the towers; glass and wet streets respond.
3. **High-right finale**: the orbit resolves; one large golden chrysanthemum blooms behind the spires, followed by a stable one-second Final Hold.

Scale the phases proportionally for other durations. Do not make every Shot a new location or reset the fireworks between cuts.

## 4. Fireworks Physics and Continuity Ledger

Fireworks are visible environmental events, never graphic overlays. For every Shot record and preserve:

- launch zone and burst position relative to the landmark;
- colour and burst family;
- ignition, radial expansion, spark falloff and extinction phase;
- smoke amount, wind direction and carried position;
- reflection state on glass façades, wet roofs and streets;
- exposure response and return to the cool-blue night baseline;
- last audible boom/crackle state at the outgoing boundary.

Each shell follows physical order: a distant launch source or rising spark, aerial burst, expanding particles, delayed boom according to distance, falling embers, smoke drift and fading reflections. Bursts occur behind or above the landmark and must not touch, wrap around, emerge from, replace or deform the towers. Avoid a continuous wall of fireworks: keep skyline depth, negative space and readable architecture.

The final golden chrysanthemum is a discrete radial particle blossom behind the spires. It is not an orbit ring, halo, solid disc, neon loop, energy circle or light ribbon. Smoke left by earlier bursts remains and drifts consistently instead of vanishing at a cut.

## 5. Scene Keyframe Chain

With only P1/P2, use one visual scene and do not force extra keyframes. If the user has loaded and selected P3/P4/P5 or later city-scene Pictures, treat them as an ordered user-authored chain while skipping analysis-only P2:

- each scene Picture owns one disjoint `time_scoped` interval;
- no future Picture is loaded while an earlier interval renders;
- each ownership interval is a separate native H3 Job;
- only the preceding final 24 silent video frames cross a boundary as motion context;
- no previous audio crosses the boundary;
- create exactly one automatic environment-only terminal keyframe after the latest user anchor;
- leave its Picture ID unassigned so Studio chooses the next genuinely empty P slot.

The automatic terminal image inherits the last scene's skyline, fireworks phase, smoke, reflections, exposure and outgoing camera position. It never introduces a person or changes the city.

## 6. Z-Image Still Isolation

Every generated Picture is one frozen photographic moment, never a motion diagram. Remove 360-degree, orbit, orbital yaw, circle-path, trajectory, route and waypoint clauses from ordinary still-image prompt sentences and `subject_keywords`. Keep the city, architecture, weather, lighting, fireworks state, smoke, reflections, lens and one frozen camera position.

Append exactly:

`The drone flight path is implied only through camera motion and must never be visible in the image. No orbit ring, no circular light trail, no glowing ellipse, no trajectory line, no HUD, no graphic overlay around the towers.`

Also append this fireworks clarification:

`Fireworks are separate radial particle bursts located behind and above the skyline, with individual sparks, natural smoke and physically plausible reflections; they never form a continuous ring, ribbon, ellipse or flight path around any building.`

Store this request-scoped Z-Image negative prompt:

`visible flight path, orbit ring, circular light trail, glowing ellipse, light ribbon, trajectory line, energy ring, HUD overlay, graphic circle, neon loop around buildings, continuous firework ring around buildings, fireworks forming a flight path, fireworks wrapped around towers, solid neon fireworks, duplicated landmark, fused towers`

Never copy that negative list into an H3 video prompt. P2 is never a visual parent of any generated Picture.

## 7. H3 Prompt Contract

Compile each Segment into a single chronological English H3 prompt. Match visual description, camera movement, fireworks state and sound to the same time order. The prompt must:

1. establish P1's city geometry, landmark, cool-blue night grade, realistic architecture and wide-angle aerial lens;
2. describe the continuous physical flight and one clockwise orbit;
3. describe distinct gold, white and deep-red particle bursts behind/above the skyline, smoke drift, glass/wet-street reflections and natural exposure adaptation;
4. resolve at the high-right finale with the golden chrysanthemum and one-second hold;
5. end with positive clean-frame language: realistic unobstructed city imagery, non-visual planning controls kept off-screen, stable horizon, coherent city geometry and continuous aerial inertia.

Do not name P2, red routes, waypoint graphics or the Z-Image negative list in the final H3 prompt. Do not add people, text, subtitles, logos, watermarks, duplicate towers, cartoon styling, unexplained spotlights or extra landmarks.

## 8. Native Audio and Music

Treat sound as diegetic and distance-aware: continuous high-altitude wind, distant city traffic bed, launch hiss, delayed low-frequency firework booms, short crackle tails and reflections from nearby towers. Preserve ambience across Shot boundaries; do not restart or abruptly cut a boom, crackle or smoke-related event at a Segment edge. Do not add dialogue, narration or studio voice unless the Timeline explicitly contains it.

Music follows the homepage `MUSIC: OFF / AUTO / TIMELINE` mode. `OFF` means no score. `AUTO` may use restrained cinematic celebratory music that ducks beneath major firework impacts. `TIMELINE` uses only the authored music instruction.

## 9. Apply Quality Gate

Before returning a Design:

- P1 is the only scene master; P2 is registered `analysis_only` and absent from visual loaders.
- Shots cover the complete duration without gaps/overlap and use one main camera movement each.
- There is exactly one continuous 360-degree orbit and one final one-second hold.
- Landmark count, spacing and architecture remain stable; no collision or geometry flicker occurs.
- Fireworks remain discrete sky particles behind/above buildings, with continuous smoke, reflections and exposure state.
- Generated Pictures contain no orbit/yaw/trajectory clause in ordinary prompt text or keywords and carry both still contracts plus the dedicated negative prompt.
- The final H3 prompt retains the true camera orbit but contains no route graphics, negative-prompt catalogue or visible control layer.
- Multi-scene keyframes own disjoint ranges; future Pictures and previous audio never cross the wrong Segment boundary.
- Native firework sound belongs to visible events and is not cut at Shot boundaries.


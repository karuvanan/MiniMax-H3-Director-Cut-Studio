---
name: drone-fly-on-city-fireworks
description: "Direct a three-phase MiniMax H3 fireworks FPV flight: launch near ground in P1, complete one translated 360-degree orbit around P1's primary scene subject, then follow verified P2 bends to its endpoint; use a collision-safe FPV scene fallback when P2 is unreadable. Generate P3 onward every five seconds from P1 pixels without assuming a city."
---

# P1-Locked Drone Fireworks Director

Use with the Default H3 Prompt Writing Skill. P1 determines what exists; P2 determines how the camera travels; the fireworks profile determines only celebration effects. A location or landmark named in an example must never override P1.

## 1. Reference Roles

- `@P1` is the sole scene master and opening composition. Keep it active in every Segment. Preserve the actual location, landmark identity/count/spacing, architecture, roads, objects, weather, time, lighting, colour, exposure, atmosphere, horizon, camera height and lens character visible in P1.
- `@P2` is local route-analysis data only. Extract its red stroke's start, bends, direction and endpoint. Never put P2 in the Timeline, upload list, H3/Z-Image Loader, start/end frame, style, composition or identity reference.
- Hard-block a genuinely missing P1 or P2; never invent a label.

Register P1 as full-duration `h3_reference/whole_design` and P2 as full-duration `analysis_only/whole_design`.

P1 also determines the sky and time of day. Do not turn a daylight, sunset or warm-coloured P1 into a cool-blue night scene merely because fireworks were requested. Keep the base palette and exposure; allow only temporary illumination from visible bursts. An authored time-of-day change must be explicit, not inherited from a Skill example.

## 2. Ground Launch, P1 Orbit, Then P2 Route

Studio locally extracts the largest continuous red stroke in P2 and reduces it to ordered path points. Every Shot must show forward translation through those bends with realistic inertia, parallax and a stable horizon. Route-follow is the default. An open S-curve, zig-zag or point-to-point path must never become an in-place rotation or generic circle.

Execute the movement in three non-overlapping phases: launch from a physically safe near-ground point in the P1 scene; physically fly one complete, smooth, wide clockwise lap around P1's primary subject at a constant safe radius, translating in order past the front/start side, right side, rear, left side and back near the front/start side while the rigid FPV camera stays aligned with the drone nose and instantaneous forward tangent. It must never independently yaw, pan or gimbal-lock toward the subject. Let the landmark travel naturally along the inside edge, pass behind the camera when geometry requires it, and reappear as the aircraft advances; use strong background parallax to prove translation. Only after the lap, enter the verified route at its green start, follow every bend, and reach its blue endpoint. This is never an in-place camera rotation, continuous subject-centred look-at, panoramic yaw, barrel roll, optical spin or rotating background. Fireworks timing must not override this order.

For the 15-second template, allocate 0–2 seconds to launch, 2–10 seconds to the complete physical lap and only 10–15 seconds to the route. Lock all route-exit motion until the aircraft has visibly returned near the lap's front starting side.

Use a fully immersive first-person FPV camera rigidly attached to the aircraft, with mild GoPro-like ultra-wide fisheye, speed-driven motion blur, strong inertia and physically motivated banking. During the P1 lap, use moderate coordinated banking only and keep the horizon readable. Dives, inversion and up to 180-degree rolls are permitted only after the full lap is complete and the verified route or fallback phase has begun. Keep architecture, fireworks and trees geometrically stable through every permitted roll; no frame tearing, slow mechanical god view or ordinary camera push.

If P2 is unverified, report `ROUTE NEEDS REVIEW`, retain the launch and 360-degree P1 orbit, and replace only the route phase with a collision-safe FPV scene flight: low ground skim; hard left bank and climbing arc; brief inverted crest into a dive; right counter-roll around visible obstacles; tight figure-eight crossover; level sprint toward a safe opening or distant horizon. Do not invent a P2 route endpoint.

## 3. P1-Derived Five-Second Scene References

Create P3 as the frozen 0–5 second opening scene anchor using the lowest denoise, then create P4 onward at exact five-second boundaries. A 35-second design uses P3–P9; a 45-second design continues through P11. Build every Picture using actual P1 image pixels via `source_plate_mode=p1_img2img` and `source_plate_media_id=P1`. BLIP/AI descriptions are supplementary only. Every Picture must preserve P1's primary subject building, place identity, landmark count, architecture, composition, surrounding scene, roads, sky, weather, time, colour palette, colour temperature, light, exposure, atmosphere and lens.

P1 remains active for the whole video; each five-second interval may add only its current scene reference. P3 and P4 onward are supporting scene states of P1, not new scene masters. P3 contains no drawn motion; the 360-degree orbit exists only in H3 Shot motion. P2 is never their visual parent.

At execution time, each P1-derived stage exclusively replaces the direct P1 loader for its interval. Split rendering at every five-second boundary and send only the current stage Picture to H3; never send P1, P3, P4 and P5 together. All stage Pictures describe the same single scene instance over time. Render one instance of the primary landmark or landmark group only. If P1 contains a paired landmark, preserve the original pair exactly once; no second pair, mirrored copy, cloned building or repeated landmark is allowed.

Each stage is a frozen photograph, not a movement diagram. Remove orbit, 360-degree, yaw, route, trajectory and waypoint motion from still prompts and keywords. Append exactly:

`Clean photographic scene with unobstructed architecture, natural sky and physically plausible lighting. Preserve the source image's scene, colour palette and exposure.`

Append this fireworks still contract:

`Fireworks are separate radial particle bursts located behind and above the skyline, with individual sparks, natural smoke and physically plausible reflections. Keep architectural silhouettes clearly readable.`

Use the request-scoped negative prompt:

`visible flight path, orbit ring, circular light trail, glowing ellipse, light ribbon, trajectory line, energy ring, HUD overlay, graphic circle, neon loop around buildings, continuous firework ring around buildings, fireworks forming a flight path, fireworks wrapped around towers, solid neon fireworks, duplicated landmark, fused towers`

Never copy this negative list into an H3 video prompt.

## 4. Fireworks Physics and Continuity Ledger

For each Shot track burst location relative to existing P1 architecture, colour, launch/expansion/falloff/extinction phase, smoke amount and wind direction, surface reflections, exposure response and delayed boom/crackle state. Use the physical order: launch spark, aerial burst, discrete radial particles, distance-delayed boom, falling embers, drifting smoke and fading reflections.

Fireworks remain behind or above existing scene geometry. They never touch, cover, wrap around, emerge from, replace or deform a building. Keep negative sky space and readable architecture; do not create a continuous ring or wall of effects.

## 5. Native Continuous Ending

Let the H3-generated camera reach the authored endpoint naturally. Keep fireworks, smoke and environmental motion continuous. No automatic terminal image, forced P1 return, one-second freeze or local fireworks composite is requested. Do not reserve an extra final Segment for a still image. Preserve the generated ending during output assembly.

## 6. H3 Prompt and Native Sound

Each H3 Segment prompt follows one chronology: P1 scene facts, ground-launch phase, proportional physical lap progress with front/right/rear/left/front position checkpoints, later verified route displacement or FPV fallback, fireworks state, environment response, continuity state and diegetic audio. Lap degrees apply only before the route begins. During the lap, keep the camera rigidly forward along the flight tangent, let the building cross the inside edge naturally, use background parallax to prove translation, and explicitly reject subject-centred look-at, independent yaw, camera spin, panoramic pan and barrel roll. Reach the route endpoint only when P2 is verified. Never name P2 or expose control graphics in renderable prose.

Use continuous high-altitude wind, distant local ambience, launch hiss, distance-delayed low-frequency booms and short crackle tails. Do not restart or cut effects at Shot boundaries. Add no dialogue or narration unless the Timeline contains it. Music obeys `MUSIC: OFF / AUTO / TIMELINE`.

## 7. Apply Gate

1. P1 is active in every Segment and the first generated moment establishes a near-ground takeoff inside its world; no example location replaces it.
2. P2 is analysis-only and absent from every visual Loader.
3. H3 launches first, completes one translated 360-degree orbit around P1's primary building second, then follows every verified P2 bend to its endpoint; these phases are never simultaneous.
4. P3 is the 0–5 second opening anchor; P4 onward are five-second P1-derived scene states with no new scene identity.
5. Current intervals use P1 plus only the relevant stage Pictures; future stages do not leak backward.
6. Fireworks, smoke, reflection, exposure and audio states remain physically continuous.

## Supported P2 Drawing and Fidelity Limits

Use a clean white control canvas with the same aspect ratio as P1. Draw one solid red (#FF0000) stroke, about 6–10 px at 1000 px width, without arrows, crossings, branches or extra coloured decorations. Place a green (#00FF00) start dot and blue (#0000FF) end dot beside the corresponding endpoints, close to the line but not painting over it. Use 3–6 clear bends. A loop needs a small gap with separate endpoint dots. These are screen-relative approximate directions, not GPS or a 3D trajectory: write altitude and look direction separately in Requirement. Up on the control canvas does not mean climb.

Local extraction must report verified direction before assigning P2 route movement. If missing, corrupt, branched, closed or unmarked, show ROUTE NEEDS REVIEW, retain the ground launch and 360-degree P1 orbit, then use the documented collision-safe FPV scene fallback. Do not invent P2 coordinates or endpoint. Preserve every overlapping verified path leg within each route-phase Shot, not just its midpoint. P2 pixels must never enter generation.

Actual P1-conditioned img2img is best-effort, not pixel-exact multi-view reconstruction. It preserves the source framing as a supporting scene reference. Do not promise recovery of hidden building sides or exact path execution by a text-conditioned video model. Inspect P3 and every five-second scene reference before Preview. If P1 already contains a ring, request a clean P1; ordinary img2img may retain that artifact.

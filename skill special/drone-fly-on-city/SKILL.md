---
name: drone-fly-on-city
description: "Direct a three-phase MiniMax H3 first-person FPV flight: take off near the ground inside P1, complete one 360-degree orbit around P1's primary scene subject, then follow the verified P2 red route bends to its endpoint; use a fast collision-safe FPV scene flight when P2 is unreadable. Generate P3 onward every five seconds from P1 pixels without assuming a city."
---

# Drone Flight Route Control for MiniMax H3

Turn a user-drawn red line into an editable **waypoint mission** and an H3-ready English camera-motion prompt. The red line is data for route analysis only: it determines camera movement but must never enter the visual-generation reference set or appear in the generated video.

## 1. Interpret the Request

Accept a P1 scene image and a P2 route drawing. Treat P2's red line as route data only and reduce it to textual waypoints. Do not use the route image as a location, composition, or visual-style reference. Use `@P1`, the required scene master, for every visual decision. The mission order is fixed: launch near the ground in P1, complete one 360-degree orbit around P1's primary scene subject, then follow the verified P2 path to its endpoint. If P2 or its direction is unverified, report ROUTE NEEDS REVIEW; retain the launch and orbit, then use the defined collision-safe FPV scene-flight fallback without inventing P2 coordinates or an endpoint.

Preserve the user's duration, aspect ratio, location, weather, time of day, drone type, target landmark, speed, and start/end frame. When omitted, use a smooth medium-speed aerial move, matching reference lighting, and a clearly identifiable anchor subject near the middle of the route.

## 2. Mandatory Reference Roles and Visual Isolation

The workflow requires two loaded Media Pool images before an H3 video prompt can be produced:

- `@P1` is the **mandatory scene master**. It is the opening environment and the sole source of visual truth: preserve its location, landmarks, architecture, layout, weather, time of day, lighting direction and intensity, colour palette, colour grade, exposure, contrast, atmosphere, lens character, camera height, and special visual effects.
- `@P2` is **route-only control data**. Read only its red-line start point, turns, curves, and end point, then convert those into textual waypoints. `@P2` is forbidden from every visual input: it must not be used as an H3 image reference, Z-Image reference, start frame, end frame, style reference, composition reference, or media-request source. Never copy any object, text, graphic, colour, overlay, annotation, or visual element from `@P2` into the video. Its only permitted output is abstract waypoint data.

If either `@P1` or `@P2` is absent, return a hard block requesting the missing reference. Do not create `@P1` from `@P2`, and do not create a final H3 prompt from `@P2` alone.

### Design JSON Preflight Contract
Whenever the output is a Design JSON, its `existing_media_uses` array must explicitly register both loaded images. This registration is mandatory even though `@P2` is non-visual. Use this exact role separation:

```json
"existing_media_uses": [
  {
    "requirement_id": "scene_master_visual",
    "media_id": "P1",
    "media_type": "image",
    "usage": "h3_reference",
    "reuse_policy": "whole_design",
    "start_seconds": 0.0,
    "end_seconds": "<DURATION>",
    "track": "V1",
    "instruction": "Use @P1 as the mandatory visual scene master for the entire video. Preserve its setting, layout, weather, lighting, colour grade, mood, exposure, atmosphere, lens character, and effects."
  },
  {
    "requirement_id": "route_control_nonvisual",
    "media_id": "P2",
    "media_type": "image",
    "usage": "analysis_only",
    "reuse_policy": "whole_design",
    "start_seconds": 0.0,
    "end_seconds": "<DURATION>",
    "track": "V1",
    "instruction": "Use @P2 ONLY to extract abstract route waypoints (start, turn points, end). It is NON-VISUAL control data: do not use it as an H3 or Z-Image image reference, start/end frame, style, composition, or scene source. Do NOT copy any of its pixels, red lines, arrows, labels, colours, text, or overlays into the video."
  }
]
```
Replace <DURATION> with the requested numerical video duration (e.g., 15.0).

## 3. P1-Derived Five-Second Scene Chain

P1 remains the sole scene master and is loaded for the complete duration. Never replace it with a city, landmark, building, weather condition or composition found only in this Skill, a template or an example. The first generated moment must establish a physically plausible near-ground FPV takeoff point inside the P1 world while retaining P1's primary subject, place identity, light, colour, weather and geometry.

Studio locally extracts the red stroke in P2 and distributes its ordered bends across the H3 Shots. It creates P3 as the frozen opening scene anchor for 0–5 seconds, then creates P4 onward at exact five-second intervals. A 35-second design therefore uses P3–P9; a 45-second design continues through P11 instead of leaving the tail uncovered. Every generated Picture must use actual P1 image pixels through `source_plate_mode=p1_img2img` and `source_plate_media_id=P1`. BLIP/AI descriptions supplement, but never replace, image conditioning. Every Picture must retain P1's primary subject building, exact place identity, landmark count, architecture, composition, surrounding scene, road geometry, sky, weather, time, lighting, colour palette, colour temperature, exposure, atmosphere and lens character. They are supporting scene states, never independent scene masters.

P2 remains analysis-only and is never a visual parent. P3 must be visually closest to P1 and use the lowest denoise; it contains no drawn motion. Each later five-second subrange uses P1 plus its current stage. A Segment spanning several subranges may load their intersecting references; temporal influence is directed by the compiled prompt, not a pixel-level guarantee. Do not let a future stage alter an earlier interval.




Every Z-Image/T2I request is a frozen still, not a camera-motion diagram. Remove `360-degree`, `orbit`, `orbital yaw`, `circle`, `trajectory`, `route`, `waypoint` and equivalent motion-planning phrases from its ordinary prompt sentences and `subject_keywords`; retain only the actual P1 environment, composition, weather, light, colour, exposure, lens and the single frozen camera position. Then append exactly: `Clean photographic scene with unobstructed architecture, natural sky and physically plausible lighting. Preserve the source image's scene, colour palette and exposure.` Store this dedicated Z-Image negative prompt: `visible flight path, orbit ring, circular light trail, glowing ellipse, light ribbon, trajectory line, energy ring, HUD overlay, graphic circle, neon loop around buildings`. Never copy that negative list into an H3 video prompt.

When only `@P1` and control-only `@P2` are supplied, this automatic five-second chain is the normal workflow. P3 is the opening P1 anchor and P4 onward continue from P1 at five-second boundaries; they never introduce a named city or landmark absent from P1.

Each P1-derived stage is an **exclusive scene-state replacement** for that interval. Split rendering at every five-second boundary and send only the current stage Picture to H3, not P1 plus several derived Pictures together. Every stage is the same single P1 scene instance over time. Render exactly one instance of the primary landmark or landmark group; if P1 contains a paired landmark, preserve that original pair exactly once and never create a second pair, mirrored copy, cloned building or repeated landmark.

## 4. Three-Phase First-Person FPV Movement

Execute these phases sequentially, never simultaneously:

1. **Ground launch:** begin at a safe near-ground point in the P1-established scene, accelerate just above the ground and pitch into clear air. In the 12-second template this owns 0–2 seconds.
2. **P1 orbit:** physically fly one complete, smooth, wide clockwise lap around P1's primary building or scene subject at a constant safe radius. Translate in order past the front/start side, right side, rear, left side and back near the front/start side. Keep the rigid FPV camera aligned with the drone nose and instantaneous forward tangent; never independently yaw, pan or gimbal-lock toward the subject. Let the landmark move naturally along the inside edge, pass behind the camera when geometry requires it, and reappear as the aircraft advances. Prove translation through strong natural parallax. Use moderate coordinated banking only; no inversion, barrel roll, optical spin, yaw-only panorama or rotating background. The route is locked until the aircraft visibly returns near its starting side. In the 12-second template this owns 2–9 seconds.
3. **P2 route exit:** only after the orbit is visibly complete, enter the verified route at its green start, retain every ordered bend, and finish at its blue endpoint. In the 12-second template this begins at 9 seconds.

Use a fully immersive first-person FPV camera rigidly attached to the aircraft. Use a mild GoPro-like ultra-wide fisheye, speed-driven motion blur and physically motivated banking. During the P1 orbit, use moderate coordinated banking only and keep the horizon readable. Dives, inversion and up to 180-degree rolls are permitted only after the full lap is complete and the verified route or fallback phase has begun. Keep architecture and trees geometrically stable. Do not use a smooth god-view crane, mechanical pan or ordinary slow push.

If P2 cannot be verified, show `ROUTE NEEDS REVIEW` but still execute phases 1 and 2. Replace only phase 3 with this proportional FPV fallback: skim low over the established ground; bank hard left and pull into a broad climbing arc; pass a brief inverted crest and dive; counter-roll right around visible obstacles; complete a tight figure-eight crossover; level out and sprint through a safe narrow opening or toward the distant horizon. Do not claim that this fallback reached P2's endpoint.

## 5. Convert the Red Line into Waypoints (Critical for Path Following)
Interpret the image plane as an approximate screen-relative control surface: left/right changes screen direction; upward/downward denotes approach/recession in this screen-space convention, not altitude. Do not claim precise GPS, altitude, metres, or real-world coordinates from a 2D image.

Simplify the route into up to nine meaningful waypoints that strictly follow the red line's geometry:

WP0 — start position and initial heading (must match the red line's start).
Intermediate WPs — placed at every significant curve apex, turn, or direction change in the red line. Do not skip curves; if the red line bends left, the waypoint must reflect a leftward travel vector.
Final WP — end position, final target framing, and settled heading (must match the red line's end).
For every waypoint, define:

screen_position: normalized x and y from 0.00 to 1.00 matching the red line's location on the map/image.
travel_vector: The direction of movement along the red line (e.g., "forward-left", "curving right"). This is crucial for ensuring the drone follows the path, not just rotates in place.
altitude_relation: level, higher, or lower relative to previous WP.
look_target: The forward flight corridor; the landmark is an inside-side spatial anchor, never a gimbal-locked look target.
yaw_progress_degrees: Optional accumulated yaw required by the actual bends; it is not forced to 360.
speed: medium/slow/fast.
continuity_note: Ensure smooth transition from the previous waypoint.
Constraint: The sequence of waypoints must visually trace the red line's shape. If the red line is an S-curve, the waypoints must form an S-shape in screen space. Do not straighten curves unless the user asks for a "direct flight." Yaw follows the real bends; do not add a complete rotation unless the verified path actually traverses it.

## 6. Direction Mapping (Camera Motion Language)
Use these mappings to translate the red line's geometry into H3 motion language:

Red route behaviour	H3 motion language
bottom to top, subject grows	fly forward at unchanged altitude
top to bottom, subject shrinks	recede at unchanged altitude
left to right	drift or pan left-to-right while maintaining forward momentum
right to left	drift or pan right-to-left while maintaining forward momentum
broad curve (e.g., U-shape)	follow a sweeping curved aerial path, banking slightly into the turn
circle around landmark	maintain a controlled orbital radius around the landmark
S-curve	execute a smooth S-curve with eased yaw, no sudden reversals
line toward skyline	advance toward the skyline, gradually reveal open distance
line toward a street or alley	advance along the street axis; change altitude only if separately authored
When route direction conflicts with visible geography, preserve the route direction but adapt wording to avoid impossible flight through walls, traffic, roofs, trees, cables, or pedestrians.

## 7. Required H3 Prompt Construction
The final generation prompt must be one continuous paragraph in the same language as the user's input. When the user writes in Chinese, output a continuous Chinese prompt; output English only when the user explicitly requests English. It serves as the instruction for MiniMax H3 to generate a video based on @P1 (Visual Master) and the textual waypoints derived from @P2 (Route Data).

### 7.1 Mandatory Visual Anchor (@P1)
The prompt MUST begin by explicitly describing the visual environment of @P1 to lock the style, lighting, and atmosphere. Do not just say "use @P1"; describe its key attributes:

Location & Layout: Specific landmarks, building arrangement, street layout.
Lighting & Time: Exact time of day (e.g., golden hour, midday), sun direction, shadow length, intensity.
Atmosphere & Weather: Clear, foggy, rainy, overcast; air clarity/haze level.
Color Grade & Lens: Color palette (warm/cool/desaturated), contrast, exposure, lens character (wide-angle distortion vs. telephoto compression).
Example Opening: "Aerial view of [Location] at [Time of Day], featuring [Key Landmarks]. The scene is bathed in [Lighting Description] with a [Weather/Atmosphere] atmosphere. Maintain the exact color grade, exposure, and lens character of the reference image."

### 7.2 Route-Following Action (Textual Waypoints)
Describe the drone's movement using the extracted waypoints from @P2, but activate those waypoints only after the ground launch and 360-degree P1 orbit are complete.

Do NOT mention "red line", "map", or "route graphic" in this section.
DO describe the physical motion: "Starting from [WP0 position], the drone moves [travel_vector] while maintaining a stable altitude. It then curves [direction] around [Target Landmark], passing by [Intermediate Feature], and finally advances toward [Final Framing]."
Ensure the description implies smooth, continuous flight with realistic inertia (acceleration/deceleration).
### 7.3 Movement Mode & Target Lock
Specify the sequence explicitly: "Launch from near ground inside the P1 scene. Physically fly one complete, smooth, wide clockwise lap around P1's primary building at a constant safe radius, passing the front, right, rear, left and front sides with strong natural parallax. Keep the rigid FPV camera facing the drone's forward tangent; never pan, independently yaw or gimbal-lock toward the building. Let the building cross the inside edge of frame naturally. Do not rotate in place, perform a panoramic yaw, barrel-roll or spin the background. After the lap is complete, release into the verified authored path, retain every bend and reach its endpoint." Assign each Shot only the phase(s) that intersect it. Orbit degrees apply only to the orbit interval; P2 progress applies only to the later route interval.
### 7.4 Native Continuous Ending
Complete the authored camera movement naturally at its endpoint. Do not force a return to P1, insert an automatic terminal image, reserve a one-second freeze or replace H3's final frames during assembly.

### 7.5 Clean Frame Contract
MiniMax H3 receives a single video prompt, so do not append the Z-Image negative-prompt catalogue to H3: repeating those visual terms can prime the video model to draw them. End the H3 prompt with this positive instruction instead: `The photoreal city image remains clean and unobstructed; all navigation control stays non-visual and entirely off-screen, with a stable horizon and physically continuous aerial parallax.` The exact still-image exclusion sentence and artifact list belong only to Z-Image reference generation; Studio removes them before H3 compilation.

### 7.6 Audio Description (Optional)
If audio generation is enabled, append a brief description of the ambient sound matching the scene (e.g., "soft wind, distant city hum") to ensure the native audio aligns with the visual atmosphere. Do not include dialogue unless explicitly requested.

## 8. Editable Camera Trajectory JSON
Use this example only to explain route data when requested. For Studio Design, use the host application's Director Design schema instead. This JSON is an illustrative route worksheet, not the Studio Director Design schema and not a claim that MiniMax H3 accepts native coordinate controls. Ensure end_seconds matches the requested duration.

```json
{
  "mission_type": "camera_trajectory_control",
  "existing_media_uses": [
    {
      "requirement_id": "scene_master_visual",
      "media_id": "P1",
      "media_type": "image",
      "usage": "h3_reference",
      "reuse_policy": "whole_design",
      "start_seconds": 0.0,
      "end_seconds": 15.0,
      "track": "V1",
      "instruction": "Use @P1 as the mandatory visual scene master; preserve all of its scene and visual attributes."
    },
    {
      "requirement_id": "route_control_nonvisual",
      "media_id": "P2",
      "media_type": "image",
      "usage": "analysis_only",
      "reuse_policy": "whole_design",
      "start_seconds": 0.0,
      "end_seconds": 15.0,
      "track": "V1",
      "instruction": "Use @P2 only to extract abstract route waypoints; never use it as visual input or copy red-line graphics into the video."
    }
  ],
  "route_overlay": "hidden",
  "rotation_mode": "ground_launch_then_360_orbit_then_route",
  "rotation_cycles": 1,
  "orbit_path_degrees": 360,
  "camera_spin_degrees": 0,
  "target_lock": "none; rigid forward-tangent FPV camera",
  "waypoints": [
    {
      "id": "WP0",
      "screen_position": { "x": 0.15, "y": 0.78 },
      "travel_vector": "forward and gently right (following the initial curve of the route)",
      "altitude_relation": "level",
      "look_target": "named visible landmark",
      "yaw_progress_degrees": 0,
      "speed": "medium",
      "continuity_note": "Start at the red line's origin. Ensure forward momentum begins immediately."
    },
    {
      "id": "WP1",
      "screen_position": { "x": 0.52, "y": 0.46 },
      "travel_vector": "sweeping curve to the left (following the route's bend)",
      "altitude_relation": "level",
      "look_target": "named visible landmark",
      "yaw_progress_degrees": "derived",
      "speed": "medium",
      "continuity_note": "Maintain level altitude. Lateral travel follows the verified bends."
    },
    {
      "id": "WP2",
      "screen_position": { "x": 0.86, "y": 0.22 },
      "travel_vector": "advance toward the final skyline framing (following the route's exit)",
      "altitude_relation": "level",
      "look_target": "named visible landmark and skyline",
      "yaw_progress_degrees": "derived",
      "speed": "slow",
      "continuity_note": "Ease to a stable endpoint at the red line's terminus. Ease the camera speed naturally."
    }
  ],
  "safety_constraints": [
    "stable horizon",
    "no collision with buildings, cables, trees, traffic, or people",
    "no abrupt teleportation or direction reversal",
    "realistic aerial parallax and inertia",
    "path strictly follows the extracted waypoints"
  ]
}
```

## 9. Output Rules
If the user asks only for a video prompt, output it in the requested language.
For Studio Design, output exactly one schema-valid Director Design JSON. The trajectory example is explanatory planning data, not a second JSON object or an alternative Studio schema.
Require both loaded @P1 and @P2. If either is missing, return only the hard block for the missing reference; never invent or pre-cite an unloaded label. @P1 is the required scene master; @P2 supplies route data only.
Every Design JSON must include both loaded images in existing_media_uses: P1 with usage: h3_reference, and P2 with usage: analysis_only. Studio must retain P2 for planning while excluding it from Timeline placement, Segment capacity, ComfyUI upload and every H3 reference slot.
Keep P1 loaded across every Segment and generate only the time-scoped P1-derived stages. Do not append an automatic terminal request.
Treat the red-route image as non-visual control-only: extract waypoint data, then exclude it entirely from H3 and Z-Image visual references. The red control path, arrows, labels, colours, and overlay graphics from @P2 must not be copied or visible in the final video under any circumstance.
Do not state that the model has executed a real drone flight, collected GPS data, or performed physical mission control.

## 10. Quality Gate (Checklist)
Before returning, verify:

Phase Order: Near-ground P1 launch comes first, the complete P1-subject orbit comes second, and P2 route travel begins only after the orbit.
Path Fidelity: When P2 is verified, the later route phase strictly traces its shape and reaches its endpoint. When unverified, only the documented FPV fallback is used and no P2 endpoint is claimed.
Visual Isolation: The final H3 prompt contains no P2 label and no description of its visible control graphics. It uses only the clean-frame sentence from section 7.5.
Rotation Accuracy: The orbit is a physical front-right-rear-left-front flight around P1 at a safe radius with strong background parallax. The FPV camera stays rigidly aligned to the forward tangent and never performs subject-centred look-at, independent yaw, in-place spin, panoramic pan, barrel roll or rotating-background motion; P2 bends control only the later route-exit phase.
Mode Clarity: Rotation mode (Orbit vs. Spin) is unambiguous and matches user intent.
Physical Plausibility: The move avoids scene geometry (buildings, trees). Stable horizon, realistic parallax/inertia.
Language: Follow the user's requested language; Studio Design must remain one valid JSON object.
JSON Integrity: @P1 and @P2 are correctly registered in existing_media_uses. Normalized screen-space controls used (no real-world telemetry claims).
Keyframe Isolation: P1 remains the full-duration scene master; P3 is the 0–5 second opening anchor and P4 onward are five-second P1-derived scene states; no forced terminal request follows the final stage; P2 never enters a Loader.
Still-reference Isolation: Every generated city Picture is a frozen environment frame. Its ordinary prompt and keywords contain no orbit/yaw/trajectory instruction, it includes the exact clean-frame sentence, and its dedicated negative prompt includes the orbit-ring/light-trail artifact list.

## 11. Control-Data Hygiene
Keep detailed route-artifact vocabulary inside P2's `analysis_only` registration and the dedicated Z-Image `negative_prompt` only. Keep the positive still prompt photographic; no prohibited ring/path vocabulary belongs there. Never copy the negative catalogue into creative_brief, Shot fields, constraints, markers, transitions or the final H3 prompt. Express H3 motion quality positively: stable horizon, continuous inertia, clean photoreal frame, collision-free path and coherent city geometry.

## Supported P2 Drawing and Fidelity Limits

Use a clean white control canvas with the same aspect ratio as P1. Draw one solid red (#FF0000) stroke, about 6–10 px at 1000 px width, without arrows, crossings, branches or extra coloured decorations. Place a green (#00FF00) start dot and blue (#0000FF) end dot beside the corresponding endpoints, close to the line but not painting over it. Use 3–6 clear bends. A loop needs a small gap with separate endpoint dots. These are screen-relative approximate directions, not GPS or a 3D trajectory: write altitude and look direction separately in Requirement. Up on the control canvas does not mean climb.

Local extraction must report verified direction before assigning P2 route movement. If missing, corrupt, branched, closed or unmarked, show ROUTE NEEDS REVIEW, retain the ground launch and 360-degree P1 orbit, then use the documented collision-safe FPV scene fallback. Do not invent P2 coordinates, direction or endpoint. Preserve every overlapping verified path leg within each route-phase Shot, not just its midpoint. P2 pixels must never enter generation.

Actual P1-conditioned img2img is best-effort, not pixel-exact multi-view reconstruction. It preserves the source framing as a supporting scene reference. Do not promise recovery of hidden building sides or exact path execution by a text-conditioned video model. Inspect P3–P9 before Preview. If P1 already contains a ring, request a clean P1; ordinary img2img may retain that artifact.

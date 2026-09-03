---
name: drone-fly-on-city
description: Convert a user-drawn red route on a map, image, or video frame into a MiniMax H3 drone waypoint mission with continuous route-following and a 360-degree orbit or rotation. Use for city flyovers, map-to-aerial transitions, real-estate flythroughs, tourism shots, and controlled aerial camera trajectories; not for static images or unrelated character videos.
---

# Drone Flight Route Control for MiniMax H3

Turn a user-drawn red line into an editable **waypoint mission** and an H3-ready English camera-motion prompt. The red line is data for route analysis only: it determines camera movement but must never enter the visual-generation reference set or appear in the generated video.

## 1. Interpret the Request

Accept an image, map, satellite image, city photo, or video frame with a red line; a spoken route; or a simple instruction such as “fly along the red route while rotating 360 degrees.” If a route image is present, treat its red line as the authoritative flight path, then reduce it to textual waypoints. Do not use the route image as a location, composition, or visual-style reference. Use `@P1`, the required scene-master image, for all visual decisions. If no route is visible, infer a minimal route from the user's text; do not ask follow-up questions unless the target, endpoint, or rotation mode is materially ambiguous.

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

## 3. Optional Continuation References (@P3–@P9)
The Skill may create route midpoint, orbit-target, or final-frame references only when they improve continuity. Create them as unlabeled Z-Image media requests first; after each image is actually loaded, use the next available label from @P3 through @P9. Every continuation image must use @P1 as its sole visual parent and preserve the exact same location, layout, landmarks, buildings, objects, weather, time, lighting direction and intensity, colour palette, grade, exposure, contrast, atmosphere, lens character, and visual effects. Only the route-consistent camera position, framing, or target view may change. @P2 must never be used as a visual parent. The final H3 reference bundle may contain @P1 plus loaded @P3–@P9, and must contain zero visual uses of @P2.

## 4. Choose the Rotation Mode
Do not treat aircraft body spin and camera orbit as the same action. Use one mode unless the user explicitly asks for both.

Orbit mode — default: The drone follows the red route while the camera smoothly yaws around a target landmark. This is the most stable, readable H3 result.
Aircraft yaw-spin mode: The drone body continuously rotates through 360 degrees while continuing forward along the route. Use only when the user explicitly asks for “drone body rotation,” “self-spin,” or “barrel-like yaw rotation.” Keep the horizon readable and do not roll the frame unless requested.
Lens pan mode: The drone follows the route while the camera pans, tilts, or looks at a target; use when the user requests camera movement but not a full orbit.
Orbit-plus-follow mode: The drone translates along the red route and completes one measured 360-degree orbit around a stable landmark. Use only when the path physically supports circling the target.
Default to exactly one full 360-degree cycle over the whole requested move. Do not repeat 360-degree turns unless the user specifies multiple rotations. Keep rotation speed constant, physically plausible, and synchronized with forward travel.

## 5. Convert the Red Line into Waypoints (Critical for Path Following)
Interpret the image plane as a normalized control surface: left/right changes screen direction; upward/downward changes relative elevation or approach/recession only when supported by visible perspective. Do not claim precise GPS, altitude, metres, or real-world coordinates from a 2D image.

Simplify the route into 3–6 meaningful waypoints that strictly follow the red line's geometry:

WP0 — start position and initial heading (must match the red line's start).
Intermediate WPs — placed at every significant curve apex, turn, or direction change in the red line. Do not skip curves; if the red line bends left, the waypoint must reflect a leftward travel vector.
Final WP — end position, final target framing, and settled heading (must match the red line's end).
For every waypoint, define:

screen_position: normalized x and y from 0.00 to 1.00 matching the red line's location on the map/image.
travel_vector: The direction of movement along the red line (e.g., "forward-left", "curving right"). This is crucial for ensuring the drone follows the path, not just rotates in place.
altitude_relation: level, higher, or lower relative to previous WP.
look_target: The landmark being orbited or followed.
yaw_progress_degrees: Accumulated rotation from 0 to 360.
speed: medium/slow/fast.
continuity_note: Ensure smooth transition from the previous waypoint.
Constraint: The sequence of waypoints must visually trace the red line's shape. If the red line is an S-curve, the waypoints must form an S-shape in screen space. Do not straighten curves unless the user asks for a "direct flight." Distribute the 360 degrees proportionally across route length. The final waypoint must reach exactly 360°.

## 6. Direction Mapping (Camera Motion Language)
Use these mappings to translate the red line's geometry into H3 motion language:

Red route behaviour	H3 motion language
bottom to top, subject grows	fly forward, push in, gently rise
top to bottom, subject shrinks	pull back, recede, gently descend
left to right	drift or pan left-to-right while maintaining forward momentum
right to left	drift or pan right-to-left while maintaining forward momentum
broad curve (e.g., U-shape)	follow a sweeping curved aerial path, banking slightly into the turn
circle around landmark	maintain a controlled orbital radius around the landmark
S-curve	execute a smooth S-curve with eased yaw, no sudden reversals
line toward skyline	advance toward the skyline, gradually reveal open distance
line toward a street or alley	descend or push forward along the street axis without clipping buildings
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
Describe the drone's movement using the extracted waypoints from @P2.

Do NOT mention "red line", "map", or "route graphic" in this section.
DO describe the physical motion: "Starting from [WP0 position], the drone moves [travel_vector] while maintaining a stable altitude. It then curves [direction] around [Target Landmark], passing by [Intermediate Feature], and finally advances toward [Final Framing]."
Ensure the description implies smooth, continuous flight with realistic inertia (acceleration/deceleration).
### 7.3 Rotation Mode & Target Lock
Specify the rotation mode clearly:

Orbit Mode: "While translating along the path, the camera completes one seamless full 360-degree orbital yaw around [Target Landmark], keeping the target continuously readable and the horizon stable."
Yaw-Spin Mode: "While translating along the path, the drone body completes one controlled full 360-degree yaw rotation around its own vertical axis, with no barrel roll and a stable horizon."
### 7.4 Final Framing & Hold
Describe the final composition: "The shot settles on [Final Target], holding steady for the last second to ensure a clean ending frame."

### 7.5 Clean Frame Contract
MiniMax H3 receives a single generative prompt, so do not append a catalogue of forbidden route graphics: repeating those visual terms can prime the model to draw them. End with this positive instruction instead: `The photoreal city image remains clean and unobstructed; all navigation control stays non-visual and entirely off-screen, with a stable horizon and physically continuous aerial parallax.` Keep specific artifact names only inside the `analysis_only` P2 registration, which Studio removes before H3 compilation.

### 7.6 Audio Description (Optional)
If audio generation is enabled, append a brief description of the ambient sound matching the scene (e.g., "soft wind, distant city hum") to ensure the native audio aligns with the visual atmosphere. Do not include dialogue unless explicitly requested.

## 8. Editable Camera Trajectory JSON
When the user asks for Design, a plan, JSON, or editable controls, return this JSON before the English H3 prompt. This JSON is an editable design plan, not a claim that MiniMax H3 accepts native coordinate controls. Ensure end_seconds matches the requested duration.

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
  "rotation_mode": "orbit",
  "rotation_cycles": 1,
  "total_yaw_degrees": 360,
  "target_lock": "named visible landmark",
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
      "altitude_relation": "higher",
      "look_target": "named visible landmark",
      "yaw_progress_degrees": 180,
      "speed": "medium",
      "continuity_note": "Maintain orbital radius. The lateral movement must match the red line's curvature."
    },
    {
      "id": "WP2",
      "screen_position": { "x": 0.86, "y": 0.22 },
      "travel_vector": "advance toward the final skyline framing (following the route's exit)",
      "altitude_relation": "higher",
      "look_target": "named visible landmark and skyline",
      "yaw_progress_degrees": 360,
      "speed": "slow",
      "continuity_note": "Ease to a stable endpoint at the red line's terminus. Hold for 1 second."
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
If the user asks only for a video prompt, output only the finished English H3 prompt.
If the user asks for a plan, design, JSON, or route explanation, output the editable trajectory JSON first, then H3 Prompt: and the final English prompt.
Require both loaded @P1 and @P2. If either is missing, return only the hard block for the missing reference; never invent or pre-cite an unloaded label. @P1 is the required scene master; @P2 supplies route data only.
Every Design JSON must include both loaded images in existing_media_uses: P1 with usage: h3_reference, and P2 with usage: analysis_only. Studio must retain P2 for planning while excluding it from Timeline placement, Segment capacity, ComfyUI upload and every H3 reference slot.
The skill may create optional continuation images for the next available labels from @P3 through @P9, but it must first issue unlabeled media requests and wait for the results to be loaded. Each optional image must be derived visually from @P1 alone, preserving every scene, grading, lighting, mood, exposure, atmosphere, lens, and effect attribute except the route-consistent view change.
Treat the red-route image as non-visual control-only: extract waypoint data, then exclude it entirely from H3 and Z-Image visual references. The red control path, arrows, labels, colours, and overlay graphics from @P2 must not be copied or visible in the final video under any circumstance.
Do not state that the model has executed a real drone flight, collected GPS data, or performed physical mission control.

## 10. Quality Gate (Checklist)
Before returning, verify:

Path Fidelity: The waypoints in the JSON and prompt strictly trace the red line's shape (curves, turns). No straight-line shortcuts unless requested.
Visual Isolation: The final H3 prompt contains no P2 label and no description of its visible control graphics. It uses only the clean-frame sentence from section 7.5.
Rotation Accuracy: Final accumulated yaw is exactly 360° for one requested rotation.
Mode Clarity: Rotation mode (Orbit vs. Spin) is unambiguous and matches user intent.
Physical Plausibility: The move avoids scene geometry (buildings, trees). Stable horizon, realistic parallax/inertia.
Language: Final prompt is English-only, no implementation explanation.
JSON Integrity: @P1 and @P2 are correctly registered in existing_media_uses. Normalized screen-space controls used (no real-world telemetry claims).

## 11. Control-Data Hygiene
Keep the detailed route-artifact vocabulary inside P2's `analysis_only` registration for planning QA only. Never copy that vocabulary into creative_brief, Shot fields, constraints, markers, transitions, generated-image prompts or the final H3 prompt. Express motion quality positively: stable horizon, continuous inertia, clean photoreal frame, collision-free path and coherent city geometry.

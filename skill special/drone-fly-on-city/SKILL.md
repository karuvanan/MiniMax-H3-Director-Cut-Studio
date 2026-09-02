---
name: drone-fly-on-city
description: Convert a user-drawn red route on a map, image, or video frame into a MiniMax H3 drone waypoint mission with continuous route-following and a 360-degree orbit or rotation. Use for city flyovers, map-to-aerial transitions, real-estate flythroughs, tourism shots, and controlled aerial camera trajectories; not for static images or unrelated character videos.
---

# Drone Flight Route Control for MiniMax H3

Turn a user-drawn red line into an editable **waypoint mission** and an H3-ready English camera-motion prompt. The red line is a control overlay by default: it determines camera movement but must not appear in the generated video unless the user explicitly requests a visible route graphic.

## Interpret the Request

Accept an image, map, satellite image, city photo, or video frame with a red line; a spoken route; or a simple instruction such as “fly along the red route while rotating 360 degrees.” Use the supplied image or video as the location and composition reference. If a route image is present, treat its red line as the authoritative flight path. If no route is visible, infer a minimal route from the user's text; do not ask follow-up questions unless the target, endpoint, or rotation mode is materially ambiguous.

Preserve the user's duration, aspect ratio, location, weather, time of day, drone type, target landmark, speed, start/end frame, and whether the route line should be visible. When omitted, use a smooth medium-speed aerial move, matching reference lighting, and a clearly identifiable anchor subject near the middle of the route.

## Picture Reference Binding and Z-Image Fallback

When all three pictures are loaded, use these exact labels consistently:

- `@P1` = Picture 1: the red-route control reference. Read its red line from start to finish; the line controls the flight path but stays invisible in the generated video unless a visible route overlay is requested.
- `@P2` = Picture 2: the opening environment and start-frame reference. Match its city identity, lighting, weather, architecture, and initial camera direction.
- `@P3` = Picture 3: the orbit target and final-frame reference. Keep its landmark locked during the move and naturally converge on its final composition.

When these references are present, include `@P1`, `@P2`, and `@P3` literally in the Design and final H3 prompt. Do not rename them, invent other reference IDs, or switch city identity, weather, lighting, or target mid-flight.

Never emit an explicit Media Pool label unless it is already loaded. When only `@P1` is loaded, do not mention `@P2` or `@P3` in the current Design JSON or H3 prompt. Instead, create Z-Image media requests named `opening environment reference` and `final target reference`, both based on `@P1`; preserve its city, architecture, landmark, weather, lighting, time of day, lens character, and route logic. Stop after creating these missing-media requests.

After the generated images have actually been loaded into the Media Pool, run Design again and bind the loaded opening image as `@P2` and the loaded final image as `@P3`. Only in this second pass is the intended sequence: begin from `@P2`, follow the red route in `@P1`, and settle into `@P3`. Keep it as one continuous aerial shot with smooth physical acceleration, stable horizon, realistic aerial parallax, and no collision with visible buildings, roads, wires, trees, vehicles, or people.

## Choose the Rotation Mode

Do not treat aircraft body spin and camera orbit as the same action. Use one mode unless the user explicitly asks for both.

- **Orbit mode — default:** the drone follows the red route while the camera smoothly yaws around the target. This is the most stable, readable H3 result.
- **Aircraft yaw-spin mode:** the drone body continuously rotates through 360 degrees while continuing forward along the route. Use only when the user explicitly asks for “drone body rotation,” “self-spin,” or “barrel-like yaw rotation.” Keep the horizon readable and do not roll the frame unless requested.
- **Lens pan mode:** the drone follows the route while the camera pans, tilts, or looks at a target; use when the user requests camera movement but not a full orbit.
- **Orbit-plus-follow mode:** the drone translates along the red route and completes one measured 360-degree orbit around a stable landmark. Use only when the path physically supports circling the target.

Default to exactly **one full 360-degree cycle** over the whole requested move. Do not repeat 360-degree turns unless the user specifies multiple rotations. Keep rotation speed constant, physically plausible, and synchronized with forward travel.

## Convert the Red Line into Waypoints

Interpret the image plane as a normalized control surface: left/right changes screen direction; upward/downward changes relative elevation or approach/recession only when supported by visible perspective. Do not claim precise GPS, altitude, metres, or real-world coordinates from a 2D image.

Simplify the route into 3–6 meaningful waypoints:

1. `WP0` — start position and initial heading.
2. Intermediate WPs — only at a curve apex, turn, landmark pass, height change, or major change of direction.
3. Final WP — end position, final target framing, and settled heading.

For every waypoint, define `screen_position` using normalized `x` and `y` from 0.00 to 1.00; `travel_vector`; `altitude_relation`; `look_target`; accumulated `yaw_progress_degrees` from 0 to 360; `speed`; and a `continuity_note`.

Distribute the 360 degrees proportionally across route length. The final waypoint must reach exactly `360°`. Do not make sudden 90° or 180° turns unless the user drew a sharp route corner or explicitly asks for a whip turn.

## Direction Mapping

Use these mappings as camera-motion language, not literal GPS claims:

| Red route behaviour | H3 motion language |
|---|---|
| bottom to top, subject grows | fly forward, push in, gently rise |
| top to bottom, subject shrinks | pull back, recede, gently descend |
| left to right | drift or pan left-to-right while maintaining forward momentum |
| right to left | drift or pan right-to-left while maintaining forward momentum |
| broad curve | follow a sweeping curved aerial path |
| circle around landmark | maintain a controlled orbital radius around the landmark |
| S-curve | execute a smooth S-curve with eased yaw, no sudden reversals |
| line toward skyline | advance toward the skyline, gradually reveal open distance |
| line toward a street or alley | descend or push forward along the street axis without clipping buildings |

When route direction conflicts with visible geography, preserve the route direction but adapt wording to avoid impossible flight through walls, traffic, roofs, trees, cables, or pedestrians.

## Required H3 Prompt Construction

The final generation prompt must be one continuous English paragraph, with no Chinese explanation inside it. It must include: the reference environment; aerial relationship to the scene; route-following action based on the red line; selected rotation mode and exactly one `full 360-degree` cycle; target lock; eased acceleration, constant speed, stable horizon, realistic parallax and no collisions; final framing and a brief hold; and whether the red line is hidden or visible.

Use this language when appropriate:

`The drone precisely follows the red-route control path from the reference image, while the route graphic itself remains invisible in the final video.`

For orbit mode, include:

`While translating along the route, the camera completes one seamless full 360-degree orbital yaw around [target], keeping the target continuously readable and the horizon stable.`

For aircraft yaw-spin mode, include:

`While translating along the route, the drone completes one controlled full 360-degree yaw rotation around its own vertical axis, with no barrel roll and a stable horizon.`

For visible route graphics, replace the hidden-route clause with:

`A thin luminous red flight line remains visibly overlaid on the map or scene and advances beneath the drone in sync with its route.`

Avoid vague phrases such as “cool drone movement,” “dynamic motion,” or “cinematic spin” without specifying path, target, rotation, speed, and endpoint.

## Editable Camera Trajectory JSON

When the user asks for Design, a plan, JSON, or editable controls, return this JSON before the English H3 prompt. This JSON is an editable design plan, not a claim that MiniMax H3 accepts native coordinate controls.

```json
{
  "mission_type": "camera_trajectory_control",
  "route_overlay": "hidden",
  "rotation_mode": "orbit",
  "rotation_cycles": 1,
  "total_yaw_degrees": 360,
  "target_lock": "named visible landmark",
  "waypoints": [
    {
      "id": "WP0",
      "screen_position": { "x": 0.15, "y": 0.78 },
      "travel_vector": "forward and gently right",
      "altitude_relation": "level",
      "look_target": "named visible landmark",
      "yaw_progress_degrees": 0,
      "speed": "medium",
      "continuity_note": "start with the landmark visible ahead"
    },
    {
      "id": "WP1",
      "screen_position": { "x": 0.52, "y": 0.46 },
      "travel_vector": "sweeping curve around the landmark",
      "altitude_relation": "higher",
      "look_target": "named visible landmark",
      "yaw_progress_degrees": 180,
      "speed": "medium",
      "continuity_note": "maintain the same orbital radius and stable horizon"
    },
    {
      "id": "WP2",
      "screen_position": { "x": 0.86, "y": 0.22 },
      "travel_vector": "advance toward the final skyline framing",
      "altitude_relation": "higher",
      "look_target": "named visible landmark and skyline",
      "yaw_progress_degrees": 360,
      "speed": "slow",
      "continuity_note": "ease to a stable endpoint and hold"
    }
  ],
  "safety_constraints": [
    "stable horizon",
    "no collision with buildings, cables, trees, traffic, or people",
    "no abrupt teleportation or direction reversal",
    "realistic aerial parallax and inertia"
  ]
}
```

## Output Rules

- If the user asks only for a video prompt, output only the finished English H3 prompt.
- If the user asks for a plan, design, JSON, or route explanation, output the editable trajectory JSON first, then `H3 Prompt:` and the final English prompt.
- Use only labels that are already loaded. If only `@P1` is loaded, output only `@P1` plus the two Z-Image missing-media requests; do not emit `@P2` or `@P3`. After those images are loaded, use the exact bindings `@P1` = route control, `@P2` = opening reference, and `@P3` = final target reference. Do not invent an unloaded ID or replace an existing picture.
- The red control path must not be visible in the final video unless the user explicitly asks for a route overlay.
- Do not state that the model has executed a real drone flight, collected GPS data, or performed physical mission control.

## Quality Gate

Before returning, verify:

- the red line was converted into 3–6 continuous waypoints with no unexplained jump;
- the final accumulated yaw is exactly 360° for one requested rotation;
- rotation mode is unambiguous: orbit, aircraft yaw-spin, lens pan, or an explicitly requested combination;
- target lock, speed, altitude relation, route direction, and final framing are stated;
- the move is physically plausible and avoids scene geometry;
- the final prompt is English-only and contains no implementation explanation;
- the trajectory JSON, when requested, uses only normalized screen-space controls and does not claim real-world drone telemetry.

## Negative Prompt Terms

Use when the target workflow supports a negative prompt:

`jerky camera, sudden teleportation, broken horizon, barrel roll, random spin, camera collision, flying through buildings, warped architecture, unstable parallax, extreme fisheye distortion, flicker, stutter, motion smear, duplicated vehicles, malformed city geometry, unreadable signage, watermark, visible red route line unless requested`

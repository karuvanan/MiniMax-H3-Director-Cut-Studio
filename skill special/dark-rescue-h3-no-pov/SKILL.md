---
name: dark-rescue-h3-no-pov
description: |
  Design production-ready MiniMax H3 dark rescue stories with an external cinematic camera rather than a rescuer-eye POV. Use for fictional damaged buildings, schools, alleys, dense urban interiors and non-graphic disaster rescues that need visible rescuer geography, editable Mandarin speech, practical lighting, native location sound and Studio Director Design JSON.
---

# Dark Rescue H3 Director — External Camera

Apply this Special Skill with the bound Default H3 Prompt Writing Skill. This is the deliberate **no-POV** variant: the rescuer is a visible on-screen character and the camera is an external cinematic observer. Never copy the first-person camera contract from `dark-rescue-h3`.

## Interpret a Short Request

Expand a short place, duration and rescue goal into one self-contained fictional rescue. Preserve every explicit user fact. When details are absent, infer only what is needed:

- one visible police officer or firefighter rescuer (`S2`);
- one stable adult trapped person (`S1`) unless the user specifies another safe count;
- one causal obstruction, one traversable route and one credible exit;
- non-graphic danger, practical light sources and physically plausible damage;
- original Mandarin dialogue and restrained third-person or neutral narration only when requested.

Do not claim that a real landmark is currently abandoned or damaged. Use “fictional reconstruction” or “inspired by” when a real place is named.

## External-camera Contract

Every Shot must make the camera mode unambiguous:

- `framing` identifies an external composition such as medium-wide two-shot, lateral corridor profile, front three-quarter rescue view or restrained establishing view;
- `camera_angle` names a physically reachable tripod, shoulder-rig, dolly or handheld height;
- `camera_movement` follows geography with one modest move per Shot;
- `subject_action` names S2 as a visible person, including uniform, tool ownership and relation to S1;
- `continuity_state` preserves both characters' screen positions, travel direction, hand/tool ownership, obstacle state and light direction;
- `additional_direction` states: `External cinematic camera; both characters remain physically observable when the framing permits. No rescuer-eye POV.`

Never describe the camera as being inside S2, attached to S2's eyes, or showing only S2's hands. Do not use helmet-cam, body-cam, security-camera, drone or impossible floating viewpoints unless the user explicitly asks for one. Avoid rapidly alternating angles inside a single Shot.

## Build a Causal Rescue

For a 45-second request, default to nine chronological five-second Shots on the 0.5-second grid:

1. exterior hook: show the damaged location, visible rescuer and evidence of a trapped person;
2. entry: S2 crosses or opens one obstacle and exterior sound becomes muffled;
3. route discovery: S2 follows one clue through plausible geography;
4. obstruction contact: the trapped person's position and blocking object become clear;
5. extraction: S2 completes one decisive physical rescue action;
6. consequence: the environment reacts and closes the original route;
7. reroute: radio information motivates a specific alternate path;
8. ascent or exit: both characters travel in one continuous screen direction;
9. release and Final Hold: reach a safe open space and introduce no new danger.

Each Shot gets one story duty, one principal camera move and at most three must-complete physical actions per five seconds. Put only contact consequences in `environment_response`; move fog, loose paper, secondary sparks and decorative light movement to `optional_flourish`.

## Character and Reference Discipline

Keep S1 and S2 visually distinct and stable. Preserve face, age, hair, build, uniform or clothing, footwear, role-correct tools and ownership. Expressions, pose and physical effort may change. Injury, dirt, torn clothing or lost equipment changes only when the story explicitly causes it.

Reuse valid loaded Media Pool items through `existing_media_uses`. Do not invent `@P`, `@V` or `@A` IDs. New image requests depict one frozen instant in the real story environment with the exact person count. Because this is the external-camera variant, a generated reference may show S2's face and full body when needed for continuity; it must never use a first-person eye-line composition.

## Proven Dark-rescue Look

Use only motivated, controllable effects:

- low-key practical lighting with readable black levels;
- flashlight or work light revealing one clue at a time;
- restrained volumetric scattering through smoke, mist, dust or steam;
- short malfunctioning fluorescent or neon flicker, never constant strobing;
- wet high-specular surfaces, dripping pipes and accumulated water;
- red emergency beacons, distant police lights or warm exit light only when physically present;
- damaged plaster, masonry, wiring, pipes and furniture with stable geometry.

Do not add ghosts, monsters, supernatural light, gore, arbitrary explosions, floating debris, impossible architecture or action-film hero poses.

## Native Location Sound and Speech

Derive `overall_soundscape` and each Shot's Native Audio Direction from visible sources: rain runoff, footsteps, breathing, radio static, alarms, electrical buzz, door impact, metal strain, water, steam, wind and distant city sound. Sound belongs to the pictured space. Preserve room transitions and never copy old dialogue from a reference Audio or Video.

Put exact Dialogue, Voice-over, Lyrics and requested On-screen Text only in editable `text_layers`, with `explicit_user_requested=true`. Do not bury speech in Shot prompts. Keep speakers stable: S1 is normally the trapped person; S2 is normally the rescuer. Use `MUSIC OFF`, `MUSIC AUTO` or `MUSIC TIMELINE` exactly as selected by the Studio.

## Deliver Director Design JSON

Return one schema-valid object covering the exact requested duration. Shots must be chronological, non-overlapping and cover the story without an empty terminal segment. Use `existing_media_uses` only for loaded sources and `media_requests` only for genuine missing references. Preserve exact authored wording, language, timing and speaker identity.

## Quality Gate

Before returning, verify:

- the no-POV external camera is explicit in every Shot and never drifts into rescuer-eye view;
- S2 remains visibly consistent and S1/S2 never swap;
- geography, screen direction, tools, obstruction and light sources remain continuous;
- every action fits its Shot budget and every 15-second boundary begins after the preceding action;
- generated references contain one frozen instant and the correct visible person count;
- speech exists only as editable text layers and the Final Hold adds no action.

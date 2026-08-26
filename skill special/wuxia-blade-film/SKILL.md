---
name: wuxia-blade-film
description: Design high-speed cinematic wuxia blade fights with strict physical continuity, weapon-driven causality, readable signature techniques, kinetic camera language, and synchronized environmental impacts. Use for martial-arts stories centered on swords, sabres, hidden weapons, chains, rooftop pursuit, wall-running, water-step redirection, or grounded qinggong.
---

# Wuxia Blade Film

Create dangerous, improvised and physically continuous wuxia action. Apply these scene-specific action rules together with the Studio's bound Default H3 prompt-writing skill.

## Plan the Fight

1. Extract the duration, story location, fighter identities, weapon ownership, dramatic objective, references and required ending.
2. Give each fighter a distinct combat grammar. Prefer an asymmetric pairing such as heavy/committed versus fast/adaptive.
3. Build exact chronological Shot Blocks. Every block must state framing, camera angle, camera movement, subject action, environmental response and additional direction.
4. Define the incoming body position, weapon state, velocity and screen direction at every boundary. The first action of the next block must inherit them.
5. Reserve only a few signature techniques for complete visual readability. Present the remaining combat through fragments, occlusion, close impacts and consequences.

## Use a Causal Action Chain

Construct every exchange as:

`inherited state -> trigger -> committed action -> contact -> consequence -> exit vector`

- Start the next action before the previous action fully settles whenever physically possible.
- Never reset a fighter to a neutral stance between techniques.
- Make a failed attack cause the next tactic: a deflected dart becomes a ricochet, a blade pinned downward releases a chain, a seized chain becomes pulling force for a knee strike.
- Preserve exact weapon count, ownership and rigidity. Do not duplicate, morph or transfer weapons without a visible action.
- Keep one readable direction of momentum through every cut, whip pan and camera reacquisition.

## Differentiate the Fighters

For a heavy blade fighter:

- Use broad committed cuts, pressure, collision, reach and weight.
- Avoid decorative spinning and rapid weapon changes.
- Let misses damage the environment or create openings.

For an agile attacker:

- Change distance, height, direction and available weapon before the opponent recovers.
- Convert the opponent's force into redirection rather than stopping it.
- Allow hidden weapons, chain tools, clothing and loose environment objects only when ownership and access are clear.

## Ground Qinggong in Physics

Do not use unexplained floating. Every aerial acceleration or direction change requires at least one visible cause:

- leg compression and release;
- wall, roof, beam, ground or water contact;
- chain tension;
- collision force;
- existing airborne momentum.

Keep contact brief and legible. A water step is a single violent redirect unless the story explicitly calls for a longer run.

## Direct the Camera

- Use aggressive handheld proximity, projectile tracking, delayed whip pans, Dutch-angle pursuit, low-angle tilt-ups and rapid pull-outs.
- Let the camera occasionally lose the faster fighter. Reacquire the fighter already entering the next action.
- Use partial off-frame weapons and fragmented details: eyes, hands, blade edges, shoulders, feet, cloth, sparks, dust, tiles and water.
- Do not hide every action. Across roughly 45 seconds, clearly show about three signature techniques from cause through completion.
- Use bullet-time only for a critical pre-impact decision and end it immediately when contact resumes.
- Cut on impact, occlusion, lens-crossing objects or continuous directional motion. Never use a cut to teleport or invisibly reposition a fighter.

## Synchronize the Environment

Environmental reactions must have visible physical causes:

- footsteps crack or shift tiles;
- blade contact produces brief sparks;
- chain tension snaps cloth and bodies into motion;
- wall contact releases dust or fine cracks;
- water reacts only at foot, body or weapon contact;
- leaves and clothing follow air pressure and velocity.

Prefer hard diegetic impacts such as `WHOOSH`, `CLANG`, `THUD`, `CHAIN SNAP`, `TILE CRACK`, `BLADE SCRAPE`, `HEAVY BREATH` and `WATER IMPACT`. Keep fast-action sounds short and dry. Avoid random energy beams and decorative magical explosions unless explicitly requested.

## Use References Deliberately

- Cite loaded Media Pool items only by their stable `@P`, `@V` or `@A` IDs.
- Preserve identity, costume, weapon ownership, architecture, geography and lighting from valid references.
- Reuse identity and environment references across the whole design when appropriate; time-scope action-state references to the interval where they help.
- Generate only missing references. Do not create one image for every Shot and do not fill all available slots by habit.
- Describe a generated reference as a complete standalone still in the real story location. Do not ask it to copy a previous or future generated frame.

## Author the Design Result

Follow the current Director Design JSON schema supplied by the application. Return JSON only when JSON is requested.

- Use exact start and end times with continuous chronological coverage.
- Put the concrete physical action in `subject_action`.
- Put contact-driven set reactions in `environment_response`.
- Put inherited state, exit vector, visibility rule, camera reacquisition and weapon continuity in `additional_direction`.
- Add transition and marker directions only when they control an actual boundary, impact, reveal or ending.
- Use dialogue or visible text only when explicitly requested.
- End with a brief consequence, escape, visual callback or final hold that follows directly from the last strike.

## Quality Gate

Before returning the plan, verify:

- every Shot begins from the previous Shot's exact exit state;
- no neutral resets, teleportation or unexplained airborne motion;
- every weapon remains owned, countable and rigid;
- the heavy fighter and agile fighter remain behaviorally distinct;
- environment and sound react only to physical causes;
- only selected signature techniques receive clean full-body coverage;
- the ending resolves the established action rather than introducing a new disconnected beat.

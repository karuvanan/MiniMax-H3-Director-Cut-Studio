---
name: wuxia-blade-film
description: Design high-speed cinematic wuxia blade fights with strict physical continuity, weapon-driven causality, 15-second boundary planning, readable signature techniques, kinetic camera language, and synchronized environmental impacts. Use for martial-arts stories centered on swords, sabres, hidden weapons, chains, rooftop pursuit, wall-running, water-step redirection, grounded qinggong, or long-form H3 action assembled from shorter render segments.
---

# Wuxia Blade Film

Create dangerous, improvised and physically continuous wuxia action. Apply these scene-specific action rules together with the Studio's bound Default H3 prompt-writing skill.

## Plan the Fight

1. Extract the duration, story location, fighter identities, weapon ownership, dramatic objective, references and required ending.
2. Give each fighter a distinct combat grammar. Prefer an asymmetric pairing such as heavy/committed versus fast/adaptive.
3. Build exact chronological Shot Blocks. Every block must state framing, camera angle, camera movement, subject action, environmental response and additional direction.
4. Define the incoming body position, weapon state, velocity and screen direction at every boundary. The first action of the next block must inherit them.
5. Reserve only a few signature techniques for complete visual readability. Present the remaining combat through fragments, occlusion, close impacts and consequences.
6. For timelines longer than 15 seconds, plan major dramatic phases around native 15-second windows when the rhythm allows it. Never let a render boundary erase an action's physical state.

## Prepare a Clean Design Handoff

- Provide one authoritative requirement layer. Do not repeat the same Shot as a Chinese outline, an English prompt and a global action prompt when the bound skills already supply the shared rules.
- State duration, exact Shot ranges, visible-text/dialogue policy, character and weapon ledger, spatial ledger, boundary contracts, sound and media policy once.
- Keep Shot instructions concrete enough for `subject_action`, `environment_response` and `additional_direction`; omit discussion about how to force the model.

## Enforce the H3 Generation Budget

Classify every Shot instruction before writing it:

- **Must-complete core (`subject_action`):** the minimum causal action that must visibly finish. Keep no more than three physical beats per five seconds.
- **Must-preserve state (`continuity_state`):** incoming and outgoing body pose, weapon ownership and position, velocity, screen direction, geography, camera trajectory and any unresolved contact.
- **Optional flourish (`optional_flourish`):** leaves, sparks, dust, cloth motion, secondary feints, ornamental camera motion and other detail that may disappear without breaking the story.
- **Required consequence (`environment_response`):** a contact-driven reaction needed to prove cause and effect. Keep no more than two per five seconds. Do not misclassify a necessary impact, landing, break or water contact as decoration.

Budget each five-second interval for at most three must-complete physical beats, two required contact consequences and two optional flourishes. When over budget:

1. Split the material into consecutive, non-overlapping Shot Blocks on the 0.5-second grid when enough duration exists.
2. Otherwise preserve the trigger, committed action, decisive contact/consequence and exit state; move secondary attacks, repeated counters and decorative reactions to `optional_flourish`.
3. Rewrite the remaining core as one concise executable causal chain. Never keep an impossible list merely because every source idea was labelled important.
4. In the final 0.5 to 1.0 second before a native 15-second boundary, introduce no new multi-beat technique. Establish one clean outgoing state for the next segment.

Priority is always: identity/geography/weapon ownership and continuity state, then core action, then required contact consequence, then optional flourish. H3 must omit optional detail before delaying, weakening or replaying a core action.

## Lock Continuity Ledgers

Before authoring Shots, freeze four ledgers:

- **Character ledger:** exact character count, identity, costume and combat grammar.
- **Weapon ledger:** exact weapon count, owner, hand, shape and permitted use. Choose one term for each weapon and never alternate ambiguous names such as chain, chain blade and grappling line.
- **Consumable/prop ledger:** count darts or other expendables and assign every use. Track the complete lifetime of delayed callbacks such as a thrown hat; give them a physical landing, snag or recovery state instead of impossible hang time.
- **Spatial ledger:** define the relative geography of roofs, walls, bridge, pond, trees and landmarks. Give every fighter a visible travel path between elevations and locations.

Resolve ambiguous verbs explicitly. Write "release blocking pressure while retaining the blade" instead of "release the blade"; write "unhook and retract the same chain" instead of "release the chain"; state whether a blade flash is a feint, armor scrape or actual wound.

## Write Boundary Contracts

For every Shot boundary, and especially each native 15-second boundary, record:

1. the outgoing body positions, weapon positions, velocity, screen direction and relevant environment state;
2. the first new action after the boundary;
3. the exact preceding action that must not be replayed.

Prefer impact occlusion, a lens-crossing prop or continuous directional motion at native render boundaries. A following segment may inherit the last motion frames, but it must advance from them rather than regenerate the launch, strike or landing. If a fighter reaches a roof or bridge off camera, establish the contact or launch path before the cut.

## Use a Causal Action Chain

Construct every exchange as:

`inherited state -> trigger -> committed action -> contact -> consequence -> exit vector`

- Start the next action before the previous action fully settles whenever physically possible.
- Never reset a fighter to a neutral stance between techniques.
- Make a failed attack cause the next tactic: a deflected dart becomes a ricochet, a blade pinned downward releases a chain, a seized chain becomes pulling force for a knee strike.
- Preserve exact weapon count, ownership and rigidity. Do not duplicate, morph or transfer weapons without a visible action.
- Count expendable weapons explicitly and forbid any use beyond that count.
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
- Put only the must-complete physical core in `subject_action`.
- Put contact-driven set reactions in `environment_response`.
- Put inherited and outgoing physical state in `continuity_state`.
- Put dispensable atmosphere, secondary motion and ornamental camera detail in `optional_flourish`.
- Put visibility rules, camera reacquisition and any remaining execution note in `additional_direction`.
- Add transition and marker directions only when they control an actual boundary, impact, reveal or ending.
- Use dialogue or visible text only when explicitly requested.
- End with a brief consequence, escape, visual callback or final hold that follows directly from the last strike.

## Quality Gate

Before returning the plan, verify:

- every Shot begins from the previous Shot's exact exit state;
- every five-second interval contains no more than three must-complete physical beats, two required contact consequences and two optional flourishes;
- every over-budget Shot has been split or priority-compressed, never passed through as an impossible action list;
- every 15-second segment begins with a new action and does not replay its continuity handle;
- no neutral resets, teleportation or unexplained airborne motion;
- every weapon remains owned, countable and rigid;
- every delayed prop callback has a physically plausible intermediate state;
- every character change of location follows the spatial ledger;
- the heavy fighter and agile fighter remain behaviorally distinct;
- environment and sound react only to physical causes;
- only selected signature techniques receive clean full-body coverage;
- the ending resolves the established action rather than introducing a new disconnected beat.

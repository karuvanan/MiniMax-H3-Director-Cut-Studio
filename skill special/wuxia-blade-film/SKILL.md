---
name: wuxia-blade-film
description: Design high-speed cinematic wuxia blade fights with strict physical continuity, one-armed or asymmetric body mechanics, fixed weapon geometry, cumulative injury, weapon-driven causality, 15-second boundary planning, readable signature techniques, kinetic camera language, and synchronized environmental impacts. Use for brutal survival-oriented martial-arts stories centered on broken blades, swords, sabres, twin blades, hidden weapons, chains, rooftop pursuit, wall-running, water-step redirection, grounded qinggong, or long-form H3 action assembled from shorter render segments.
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

## Use Brutal Blade Combat Grammar

Extract the reusable principles of raw 1990s Hong Kong blade combat without reproducing any film shot for shot. Reject polished duel choreography, symmetrical attack-counter exchanges, ornamental poses and clean superhero flight. The fight should feel improvised, breathless and physically costly: a committed miss creates danger, an injury changes the next movement, and a fighter survives by entering a weapon's unusable range or stealing its momentum.

Never copy game-facing frame counts, cooldowns, damage percentages, buffs or resource meters into an H3 prompt. Use them only as private choreography priority. Translate them into visible distance, body mechanics, contact, consequence and recovery.

### Lock body asymmetry, weapon geometry and damage

Freeze these ledgers before choosing a technique:

- **Limb ledger:** state every missing, injured, occupied or usable limb. For a one-armed fighter, name the remaining arm and blade hand, keep the absent sleeve empty, and forbid a regenerated hand, phantom grip, two-handed guard or invisible off-hand balance. Generate an identity reference that makes this silhouette unmistakable when the source image does not.
- **Weapon-geometry ledger:** record blade length, curvature, weight, point condition, edge condition, hand and attachment. If the broken blade has no usable point, forbid clean thrusts or impalement; use draw-cuts, push-slices, upward rakes, trapping pressure and strikes with the broken spine. If a jagged point can penetrate, state that once and preserve the same shape.
- **Attachment ledger:** define exactly where a chain or rope begins, what it wraps or hooks, whether it is taut or slack, which hand controls it and how it releases or retracts. Do not let one chain become a second weapon or pass through a body.
- **Damage ledger:** carry every cut, bruise, torn sleeve, damaged armor plate, weakened leg, breath loss, blood, mud and grip failure into later Shots. Damage changes stance, speed, reach or willingness to block; it never vanishes at a cut or 15-second boundary.
- **Footing ledger:** track dry stone, loose tiles, mud, blood, pond edges and broken debris. A skid, stumble, grounded roll or failed launch must follow from the visible surface.

Do not describe a one-armed fighter as universally faster or immune to control. Show the tradeoff: reduced reach and balance, compensated by lower profile, compact blade inertia, torso rotation, aggressive foot placement and entering before the longer weapon can recover.

### Escalate from technique into survival

Use a controlled degradation curve rather than maintaining clean martial-arts form for the whole fight:

1. **Threat:** establish unequal reach, height, numbers or footing in one brief spatial view.
2. **Commitment:** one fighter makes an attack too heavy or too fast to cancel; the opponent survives by changing range, not by posing in a perfect block.
3. **Damage adaptation:** a wound, broken weapon, trapped arm or lost footing forces a new body mechanic in the very next exchange.
4. **Feral collapse:** only near the climax, reduce technique into shoulder rams, forearm traps, kicks, grounded scrambles, weapon recovery and desperate short cuts. Keep exact anatomy and weapon ownership; "animalistic" never authorizes random extra limbs or unreadable chaos.
5. **Cost:** finish on breathlessness, collapse, an unusable weapon, persistent injury or a compromised escape. Victory must visibly cost something.

Do not use every stage in every five-second Shot. Distribute the curve across the sequence and let each Shot advance exactly one irreversible combat state.

### Make fragmented editing preserve causality

- Establish geography once, then cut among eyes, planted foot, gripping hand, blade edge, torn cloth, impact and recoil. Each fragment must be adjacent in the same physical exchange.
- Let a weapon or body cross the lens to hide only the instant of impact; reveal the new wound, displaced guard or changed position immediately afterward.
- Use camera shake only after footfall, collision, blade contact or camera evasion. Random continuous shake does not create speed.
- Depict a long flurry as `first readable lane -> compressed impact fragments -> final readable consequence`. Never show the attacker restarting the flurry from the same pose.
- Keep one orientation anchor per exchange: screen direction, a fixed landmark, the opponent's shoulder line or the visible chain axis.

### Broken-blade inner-circle fighter

Lock this grammar when a short or broken blade fights a longer weapon:

- Work mostly inside one body length. The short blade stays close to the forearm; attacks travel in compact lines rather than broad display arcs.
- Enter beneath or beside a committed long-weapon swing. Do not parry at the strongest outer third of the opponent's blade.
- Use shoulder checks, forearm pressure, low sliding steps, torso rotation and a wall, rope or taut chain as the source of redirection.
- Treat every rotation as a new cut angle or escape vector, not decorative spinning.
- Once inside, keep chest-to-shoulder pressure so the long weapon cannot fully retract. Finish or exit within the same short exchange.

Use these renderable signature chains:

1. **Inner-gate entry:** incoming low crouch outside reach -> opponent commits one broad cut -> short-blade fighter drops under the cutting line and shoulder-checks into the weapon arm -> compact upward rake or draw-cut lands inside one metre; use a thrust only if the ledger confirms a fixed usable jagged point -> exit beside the opponent's rear shoulder.
2. **Tension-axis turn:** visible rope or chain becomes taut around a fixed beam, trunk or body axis -> fighter plants one foot and rotates once -> short blade intercepts the incoming weapon on the compact inner arc -> tension pulls the fighter into a new angle -> chain remains visibly owned and taut or is visibly retracted.
3. **Adhesive short combination:** shoulder pressure jams the opponent's elbow -> one short upward cut forces the torso open -> one wrist-reversal push-cut crosses a nearby target line -> blade spine, pommel or forearm creates the exit impact. Show at most three contacts; imply any faster continuation through fragments, sound and the opponent's reaction.
4. **Ground-skimming counter:** opponent attacks high from reach -> short-blade fighter folds at hips and knees, one hand or foot briefly bracing on ground -> body slides past the weapon's recovery line -> one low cut attacks the exposed flank or lead leg -> fighter rises only after passing the opponent.

### Airborne twin-blade predator

Lock this grammar when a longer twin-blade fighter controls height:

- Every ascent needs a visible launch contact. Use a wall, roof edge, beam, ground compression or collision; never write prolonged unsupported hovering.
- The aerial fighter gains danger from height and gravity. Use one readable X-shaped descent, alternating blade envelope or downward driving strike, not a weightless ballet sequence.
- Twin blades must occupy different lanes. State left-blade path and right-blade path when both matter; never let them merge, multiply or change length.
- A dense flurry is represented by two or three readable contacts plus partial off-frame blade passes, sparks, torn cloth, breath and camera recoil. Do not ask H3 to count nine distinct strikes.
- Landing immediately becomes pursuit, stumble, skid or recoil. Do not reset to a balanced pose after a violent descent.

Use these renderable signature chains:

1. **Predator launch and X descent:** feet crush one visible launch point -> body folds and rises above the target -> twin blades open on separate sides -> gravity drives one crossing downward attack -> ground, guard or shoulder receives the impact -> fighter lands in a forward skid.
2. **Overlapping blade envelope:** left blade commits high while right blade closes the middle line -> target's guard is forced inward -> a third low or reverse pass breaks the stance -> camera is struck or occluded by cloth/sparks -> reacquire on the physical consequence, not another fresh flurry.
3. **Low pursuit after landing:** descent ends with one foot and one hand near ground -> fighter immediately advances with irregular short steps -> one blade occupies the opponent's vision while the other attacks the escape lane -> end on collision or a clearly failed attack that exposes the fighter.

### Resolve the speed paradox

For the decisive clash between long/high power and short/inside speed, do not choreograph a prolonged equal exchange. Build one causal contest:

`long or twin blades commit outside -> short-blade fighter accepts a minor graze or narrowly clears one line -> body enters inside the opponent's elbows -> one compact decisive cut lands before the long weapon can retract -> both pass or collapse into the consequence`

Use bullet-time only at the final decision gap, preferably less than half a second of story time. Resume full speed at contact. Show the losing weapon still physically committed so the victory reads as range and timing, not unexplained superiority.

### Translate timing into H3

- Treat 6–18 choreography frames as **near-instant preparation**, 8–36 active frames as **one brief committed technique**, and 12–30 recovery frames as **one visible consequence or vulnerable exit**. Do not write literal frame counts unless the user is documenting choreography rather than generating video.
- Give one signature technique roughly three to five seconds. Its H3 core remains three beats: entry/commitment, decisive contact, exit consequence.
- Represent faster secondary attacks with a hand close-up, blade crossing lens, sparks, cloth damage, a body recoil or sound. Do not add them as extra mandatory moves.
- Prefer close handheld fragments and impact cuts. Use a wide frame only to establish geography, show a physically caused launch/landing, or prove the final spatial result.

### Keep actor and still-reference integrity

- Start every action clause with the explicit role: `The Assassin...`, `The General...`. In a two-person Shot, never depend on `he`, `his` or `they` across clauses.
- Write each generated action-state reference as one frozen instant with one body position per fighter. Do not describe setup, mid-action and outcome in the same image prompt; this creates duplicate fighters and contradictory weapon states.
- Verify every projectile direction as `owner -> release point -> target -> contact/deflection -> final location`. A knife thrown by the Assassin must never appear travelling toward the Assassin.
- Identity references may span the design. A pose/action reference must be time-scoped only to the Shot or segment where that state is useful.

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
- Put inherited and outgoing physical state in `continuity_state`, including limb availability, blade geometry, chain attachment, accumulated damage, footing and unresolved body contact.
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
- every limb remains present, absent, injured or occupied exactly as established, with no phantom grip;
- every blade action is compatible with its fixed length, edge and point condition;
- every wound, damaged armor part, weakened leg, breath loss and unstable surface persists until visibly resolved;
- every delayed prop callback has a physically plausible intermediate state;
- every character change of location follows the spatial ledger;
- the heavy fighter and agile fighter remain behaviorally distinct;
- environment and sound react only to physical causes;
- only selected signature techniques receive clean full-body coverage;
- fragmented edits retain one orientation anchor and reveal the physical consequence immediately after impact occlusion;
- no game-stat, cooldown, buff, immunity or guaranteed-hit language reaches the H3 prompt;
- the ending resolves the established action rather than introducing a new disconnected beat.

---
name: street-fighter-live-action-h3
description: |
  Design 15-45 second MiniMax H3 live-action arcade martial-arts movie scenes with two readable fighters, grounded striking and MMA ground-game choreography, non-repeating multi-Segment action and a continuously translating full-speed FPV camera orbiting around the fighters. Use when the user asks for a Street Fighter-like live-action fight, world-warrior tournament, arcade combat film or stylized one-on-one martial-arts showdown; do not use for ordinary realistic fights without signature-move spectacle.
---

# Live-action Arcade Fighter H3 Director

Apply this Special Skill with the bound Default H3 Prompt Writing Skill. This Skill translates the visual grammar of a live-action arcade fighting movie into an original, editable H3 production. It may honour the requested franchise language, but it must not copy the supplied trailer shot-for-shot or invent the likeness of a real actor. When no licensed character/reference is explicitly requested, create original tournament fighters with distinct silhouettes and abilities.

## Read the Request

Preserve the user's exact duration, aspect ratio, location, fighters, dialogue, references and ending. Default to:

- 15 seconds for one decisive exchange, 30 seconds for setup/reversal, or 45 seconds for a three-phase non-repeating fight;
- two principal fighters only, `S1` and `S2`;
- one coherent arena, street, dojo, industrial ring or tournament space;
- cinematic live-action bodies, skin, cloth, sweat, dust and impact physics;
- bold arcade readability with restrained humour, not parody unless requested;
- dialogue must remain sparse enough for the fight: the Skill may create one concise Mandarin challenge, warning or recognition line per 15-second phase when it improves the rivalry;
- every supplied or generated spoken line belongs in editable `text_layers`. Dialogue-aware timing may visibly extend the Timeline when needed, but it must not slow or time-stretch the combat beats.

Do not fill a short fight with introductions for many famous characters. Background spectators may remain soft, distant and non-speaking; they never become extra foreground fighters.

## Character Bible

Give each fighter one compact identity line containing face, age range, hair, build, costume colours, footwear, signature stance and one ability. Preserve these across every Shot and generated reference.

Lock:

- face, age, skin tone, hair, build and body proportions;
- costume design and colour blocks, bare-hand/wrist state, footwear and accessories;
- left/right handedness, stance, ability ownership and current injury/dirt state.

Both fighters are **bare-handed by default**. Do not generate boxing gloves, MMA gloves, padded gauntlets, hand wraps or wrist tape unless the user explicitly requests that equipment. Keep five anatomically distinct fingers, natural knuckles, palms and wrists visible whenever a hand is shown; a grip must close around the real wrist, sleeve, arm or leg without padded equipment appearing between cuts. Wet dirt may accumulate on the palm heel, fingertips or wrist only after visible floor contact; record it in the continuity state so it persists.

Allow expression, pose, limb angle, breathing, cloth movement and physically caused damage to change. Never swap costume colours, abilities or screen identity. A fighter cannot teleport, duplicate, change face, gain extra limbs or recover a torn costume without a visible cause.

When loaded P1 and P2 character Pictures are available, bind them deterministically: **S1 is exclusively P1 and S2 is exclusively P2**. This order overrides every generic male/female convention: do not replace P1/P2 with an invented man/woman cast. Use the actual uploaded P1/P2 pixels as the sole authoritative principal-fighter identity and wardrobe sources. P1's `BLIP · Overview` and P2's `BLIP · Overview` are compact descriptive metadata only; if absent, AI Enrich may describe that same Picture, but text never replaces its pixels. Register both Pictures as whole-design `h3_reference` identity anchors and cite the correct `@P1` or `@P2` in every Shot where that fighter appears. Preserve 100% of each visible face, facial geometry, age, skin tone, hairstyle, hair colour, body proportions, complete upper/lower wardrobe, materials, colours, shoes and accessories. Never blend, swap, duplicate, transfer, reinterpret or change gender presentation, and never let an independently generated action-state Picture override either loaded identity.

If only one of P1/P2 is loaded, bind only its matching fighter and retain the default original-character description for the other fighter; never invent the absent ID. For any other user-assigned loaded Picture, use it only for its explicitly assigned identity/costume/environment. Never invent an unloaded `@P/@V/@A` ID or assume an actor likeness that the reference does not contain.

## Build an Executable Fight

### 15-second structure — exactly 12 close-combat beats

Treat an attack, block, parry, trapping contact, grip, throw entry/completion, top-control establishment, short ground-strike burst, submission entry or intercepting counter as one **combat beat**. Produce exactly 12 numbered combat beats in every 15-second Segment. A visible tap-and-immediate-release may serve as the final result beat. Do not count establishing poses, camera moves, facial reactions, water splashes, smoke or recovery holds as combat beats.

Use **six chronological, non-overlapping executable action windows** per 15-second Segment on the 0.5-second grid. Each window contains exactly two numbered must-complete beats, giving 12 beats without adding separate establishment or result-only Shots. The first window starts mid-exchange at arm's reach; ordinary sixth windows resolve their collision into guarded recovery and immediate pressure while the camera keeps moving. In the final Shot only, the completed recoil must settle into a readable supported state during the last 0.75–1.00 second. There is no walking entrance, scenic travel, neutral establishment, slow-motion insert or result-only Shot.

Distribute the six windows across the full 15 seconds according to the authored action and dialogue budget, normally around 2.0–2.5 seconds each. Every window contains two short action sentences: the first commits an attack or grip and the second is the other fighter's visible defence, counter or positional result. Put the exact global time range beside every `[BEAT NN]`. Never assign a fighter to defend against their own attack, never jump from a captured leg directly to the opposite fighter's top control without an explicit reversal, never describe all 12 beats in one Shot, and never hide a required beat in `optional_flourish`.

### Combat Action Continuity contract

For every beat, reason in this causal order: **load/weight → acceleration → attack line or grip → contact or visible miss → defender response → force/deformation → displacement → one environment result → next-beat trigger**. Camera movement is caused by and follows the active body mechanics; it cannot replace a missing action.

Every Shot carries an editable combat state relay: `combat_action_chain`, `incoming_combat_state`, `outgoing_combat_state` and `next_action_trigger`. Inherit at least position, facing, velocity/direction, body height/support, guard or grip ownership, advantage state and visible wetness/damage. The next Shot begins from the exact outgoing state with no neutral reset. Mark an action risk for a repeated exchange, self-defence actor, unexplained top/bottom swap or missing reversal; deterministic corrections may repair the clear actor error but must never silently rewrite user-authored dialogue.

### Structured combat ledger and routing

The Studio materializes a versioned `combat_fact_ledger` for this Skill. Its authority order is
`explicit_user_direction > loaded_picture_pixels > explicit_role_binding > blip_overview > ai_enrich > special_skill_default`.
Keep S1/P1 and S2/P2 as separate immutable identity facts; BLIP and AI Enrich are descriptive
evidence only. Every Shot also receives a five-duty label (`state_pickup`, `escalation`,
`advantage_shift`, `environment_consequence`, `outgoing_relay`) based on its position inside the
15-second window. Do not add Segments to satisfy these duties.

Route each Beat through exactly one physical carrier: `bare_hand_strike`, `kick`, `grapple_clinch`,
`throw_takedown` or `ground_control`. Weapons, giant objects and supernatural carriers require an
explicit user request; otherwise surface an action risk and keep the principal exchange grounded.
Each Beat records attacker, defender, load/weight, trajectory, contact or miss, defence, force
vector, displacement and next trigger in the Action Ledger. The same mechanic/target/outcome is a
duplicate even when the camera angle or effects change.

The Camera Ledger is action-triggered, not a fixed angle loop. Select one physical clockwise FPV
translation per Shot from the active carrier and defence: follow a kick line, counter a parry,
track a grip, descend with a throw, stay mat-level for ground control, or tighten around a reversal.
Carry the incoming/outgoing sector forward and keep close subject scale; never imitate travel with
an in-place spin, zoom or pull-back.

### Double-speed execution contract

Words such as “dynamic”, “rapid” or “intense” are not sufficient by themselves. The choreography cadence is **2× the previous full-speed baseline**. Every action Shot must make the following executable in the actual H3 prompt:

- state **2× action cadence, real-time martial-arts execution with explosive acceleration**; complete each load, attack or defence, contact and recoil in roughly half the previous screen time, then flow immediately into the next exchange;
- keep both fighters in continuous purposeful footwork; the recovery of one beat becomes the load for the next beat, with no neutral reset, stare-down, repeated wind-up or posed pause between beats;
- cap a stance/read at 0.25 seconds and a signature charge at 0.5 seconds; do not stretch a one-second beat into slow rehearsal, floating motion or prolonged anticipation;
- keep every frame at real-time full speed, including decisive contact and recovery; never use slow motion, bullet time, impact freeze, speed ramping or a frozen hero pose;
- use the requested 15.00 seconds as the full-speed combat baseline. Dialogue-aware Timeline logic may extend it for intelligibility; keep the numbered combat beats at full speed rather than spreading them over the added speech time, and never mark Skill-generated words as `explicit_user_requested`.

In each Shot `subject_action`, write each numbered beat as one compact load/trajectory/contact-or-defence/result chain and finish its physical mechanics in approximately 0.45–0.65 seconds. Use the remaining interval to start the next distinct guard change or combat transition, never to hold or walk. In `additional_direction`, include: `2X ACTION CADENCE: every load, strike or defence, contact and recoil completes in roughly half the previous screen time with continuous explosive acceleration; no artificial fast-forward artifact. FULL-SPEED FIGHT ONLY: every frame is active real-time combat; no walking, entrance, exit, neutral travel, idle pose, anticipation pause, repeated wind-up, slow motion, bullet time, impact freeze, speed ramp, slow rehearsal or floaty motion.`

### Action-variety contract

This is a mixed martial-arts screen fight, not a boxing exchange. In each 12-beat Segment:

- use no more than **two closed-fist punches** in total and never place punches in consecutive beats;
- include at least two distinct leg attacks, two footwork/evasion mechanics, two open-hand or forearm parries/traps, two grip/clinch/takedown mechanics and one knee or elbow action;
- vary target level and body geometry across high, middle and low lines, upright, crouched and ground-adjacent positions;
- let defence change angle or position—slip, duck, pivot, sidestep, check, frame, sprawl or breakfall—instead of answering every attack with another punch/block;
- never repeat the same limb, target, trajectory and result combination merely from a different camera angle.

When the user asks for no gloves, bare-handed continuity is absolute. Gloves and wraps are not an optional flourish and must not appear in generated references, Shot prompts, negative-space descriptions or H3 output constraints.

### 30-second structure

Use two complete 15-second, 12-beat phases: 24 combat beats total. Segment 1 establishes the rivalry through combat and ends with its twelfth collision. Segment 2 inherits the exact guard, contact distance, screen side, wetness, smoke, lighting and FPV orbital camera phase, then begins immediately with a new `[BEAT 13]`; it never replays `[BEAT 01]`, the opening exchange or the first collision. A second eye-level wide re-anchor is permitted only from 15.0–15.5s, must remain an active attack/defence exchange and must not reset positions.

The preceding 24 frames are silent visual motion context only; never copy old dialogue, impact sound or music into the next Segment. If the user requests fewer actions, preserve their explicit count instead of forcing this 12-beat mode.

### 45-second structure — three different phases, 36 non-repeating beats

Use three continuous 15-second Segments and six executable action windows in each Segment. This creates a stable 18-Shot baseline and exactly 36 numbered combat beats. At 15.0s and 30.0s, the next action window remains inside the ongoing exchange, inherits body positions and the outgoing FPV orbital sector, and cannot become walking, travel, a neutral establishment or a replay. Dialogue-aware extension may lengthen the final Shot, but the indoor-to-outdoor threshold remains locked to 30.0s from the authored 45-second combat baseline.

Maintain a global **Action Ledger** for all 36 beats with: `beat_id`, `attacker`, `technique/mechanic`, `target_or_grip`, `defensive_response`, `resulting_position`, `environment_contact`. Before returning the design, compare every beat against all previous beats. A beat is duplicated if the same fighter uses the same mechanic on the same target/grip with the same outcome; merely renaming it, changing camera angle or adding sparks does not make it new. Rewrite duplicates before output.

Use this default three-phase ledger unless the user supplies a different non-repeating choreography:

- **Segment 1 · 0–15s · bare-hand standing style collision:** `[01]` JKD oblique low kick, `[02]` karate shin check with outside step, `[03]` karate open-palm heel counter to the guard, `[04]` Wing Chun tan-sau redirect with outside pivot, `[05]` JKD elbow frame, `[06]` judo wrist-and-upper-arm clinch, `[07]` judo outside foot-sweep entry, `[08]` JKD hopping balance recovery, `[09]` turning back kick, `[10]` karate duck-and-side-step evasion, `[11]` compact clinch knee stopped on the body guard, `[12]` judo hip-turn reversal into the signature collision.
- **Segment 2 · 15–30s · clinch, takedown and top pressure:** `[13]` Wing Chun lap-sau arm drag, `[14]` judo overhook clamp, `[15]` single-leg capture, `[16]` sprawl defence, `[17]` switch to double-leg capture, `[18]` whizzer pivot defence, `[19]` corner-turn finish, `[20]` controlled takedown landing, `[21]` stable side control, `[22]` bottom forearm frame, `[23]` one guarded open-palm shoulder post, `[24]` one controlled short-elbow contact to the body guard.
- **Segment 3 · 30–45s · escape, positional reversal and submission:** `[25]` bottom hip bridge, `[26]` hip escape to half guard, `[27]` top fighter re-centres the base, `[28]` bottom knee shield creates distance, `[29]` bottom underhook reversal, `[30]` completed top/bottom position swap, `[31]` new top fighter isolates one wrist, `[32]` controlled straight-arm submission alignment, `[33]` defender clasps hands to stop extension, `[34]` attacker changes to a controlled choke position, `[35]` defender clearly taps, `[36]` attacker immediately releases and both fighters continue guarded combat pressure while the FPV orbit completes.

Do not replay punches, blocks, takedown entries, falls, ground contacts, reversals or tap shots as filler at Segment boundaries. Continue the outgoing body state and introduce the next unused mechanic.

## Four-style Close-combat Grammar

Keep both fighters mostly within arm's reach. Briefly open distance only for the low side kick or a compact signature collision; close it again through visible footwork. Assign stable style ownership—by default S1 uses karate plus judo and S2 uses Jeet Kune Do plus Wing Chun—so H3 does not randomly change technique between cuts.

- **Karate:** hard outside/inside forearm check, low shin check, open-palm heel counter, ducking angle step and compact front, round or side kick. A reverse straight punch is optional and counts toward the two-punch cap. Show hip rotation, planted heel, clean line and immediate recoil; no decorative aerial kata.
- **Judo:** wrist-and-sleeve capture, balance break, hip placement and throw entry. In this rapid mode, the opponent may frame the hip and escape before a full throw so both faces remain available for the next close-up. Grip ownership cannot switch hands between Shots.
- **Jeet Kune Do:** oblique/low side kick, stop-kick, outside pivot, economical hand trap and elbow/forearm frame. An intercepting lead straight is optional and counts toward the punch cap. Use shortest-path timing: the counter starts while the opponent commits, not after a long pause.
- **Wing Chun:** pak sau, tan sau or bong sau deflection, palm strike, short elbow and one compact trapping exchange. A centre-line vertical punch is optional and counts toward the punch cap. Hands remain anatomically separate; never generate a many-arm chain-punch smear.

The default 12-beat order must demonstrate all four systems as a varied causal chain: JKD low kick → karate shin check/angle step → karate open-palm counter → Wing Chun redirect/pivot → elbow frame → judo clinch → foot-sweep entry → hopping/breakfall recovery → turning kick → duck-and-pivot evasion → clinch knee → hip-turn reversal/signature collision. Do not convert these into a chain of jabs and blocks.

## MMA Ground-game Variant

When the request mentions MMA, takedown, ground game, grappling control, ground-and-pound or submission, preserve the six-window/12-Beat budget but replace the latter half of the standing chain with one readable standing-to-ground sequence. Do not add ground actions on top of the existing 12 beats.

Use this default mixed chain: `[BEAT 01]` Jeet Kune Do low kick → `[BEAT 02]` karate shin check and pivot → `[BEAT 03]` karate open-palm counter → `[BEAT 04]` Wing Chun redirect and elbow frame → `[BEAT 05]` body-angle evasion → `[BEAT 06]` judo/MMA clinch or underhook entry → `[BEAT 07]` single- or double-leg capture → `[BEAT 08]` balance break and controlled takedown landing → `[BEAT 09]` stable top-position control → `[BEAT 10]` one guarded palm/forearm ground contact → `[BEAT 11]` controlled submission position → `[BEAT 12]` visible tap and immediate release.

Apply these cinematic mechanics:

- **Takedown:** show a visible level change, hands capturing the assigned single leg or both legs, the standing fighter's balance breaking, one controlled descent and one floor impact. Split entry and completion across consecutive beats; never teleport from standing to the floor.
- **Grappling control:** after landing, explicitly lock the top fighter, bottom fighter, head direction, screen side, grip hand and one simple position such as half guard or side control. The top fighter uses a wide base and body weight; the bottom fighter visibly frames or bridges. Never swap top/bottom identity between cuts.
- **Ground-and-pound:** only when explicitly requested, show one compact beat containing no more than one readable closed-fist or short-elbow contact to a guarded body target, followed by a visible defensive frame. Prefer positional pressure, an open-palm post or forearm control when ground strikes were not requested. Do not create an endless barrage, graphic injury, extra arms or contacts hidden by smoke.
- **Submission:** use one visually simple, controlled arm or choke position without graphic joint deformation. Show the defender's free hand tapping the floor or opponent clearly, then show the attacker immediately releasing. A submission cannot begin before control is established.
- **Reversal option:** if the story requires an escape instead of a submission, replace Beats 11–12 with a visible hip bridge/frame, top-position reversal or return to one knee. Preserve the same hand, leg and screen-direction ledger.

Ground-camera coverage remains close and spatially legible: mat-level eye-line close-ups of the level change and landing, extreme close-ups of the assigned grip, hip/shoulder pressure, guarded strike contact and tapping hand. Use no more than one short side-on geography insert, capped at 1.0 second; avoid overhead views that obscure identity or limb ownership.

## Convert Arcade Moves into Physical Cinema

Each signature technique must have four readable states: **body load → release trajectory → contact point → recovery/result**. Across a five-second Shot, show at most one full signature technique.

- **Projectile palm burst:** feet plant, hips and shoulders compress, hands gather a compact luminous pressure pulse, arms release it on one straight line, the pulse travels once, contacts the opponent or wall, disperses, and leaves a single physical consequence. Never create an endless beam or a second unexplained projectile.
- **Rotating kick:** support foot plants, knee chambers, hips turn, one leg follows a clean arc, shin/foot contacts or misses, then the fighter lands in a stable recoverable stance. Do not spin indefinitely.
- **Forward rolling attack:** crouched compression, one rapid forward airborne rotation, one contact or evasive pass, then a visible landing. Preserve body mass and direction; never turn the fighter into an amorphous ball.
- **Electric close-range strike:** electricity originates from the assigned fighter and stays close to skin/limbs until physical contact. It briefly illuminates sweat and fabric, produces one contact flash, then decays. Do not fill the whole arena with unrelated lightning.
- **Rapid hand strike:** establish the torso base and shoulder rhythm, show a brief controlled burst aimed at one target zone, then a clear finishing palm and recovery. Avoid extra arms, smeared hands or dozens of independent impacts.

If H3 cannot execute every requested technique inside the budget, keep the technique that changes the outcome. Move secondary hits to `optional_flourish` or split them into the next Shot; never weaken the main contact.

## Camera and Edit Grammar

The default camera is a **full-speed physical FPV orbit around the shared midpoint of S1 and S2**. It continuously flies around the fighters while they exchange attacks and defences. The camera changes real position in space, producing foreground occlusion changes and continuous background parallax; it never spins, yaws or rolls 360 degrees in place. Keep a clear fight axis and stable identity: an axis crossing is allowed only when the viewer sees the FPV camera physically travel around both fighters. Each Shot has exactly one principal movement—the continuing FPV orbital translation—and it must be motivated by the active combat beat.

Maintain a **Camera Ledger** across the complete film with: `shot_id`, `camera_position_sector`, `framing`, `principal_camera_movement`, `motion_relation` (`follow`, `counter` or `neutral`), `action_trigger`, `screen_direction`, and `end_frame`. Write the chosen movement into the Shot's `camera_movement`; write its trigger and end-frame duty into `additional_direction`. Do not create unsupported root JSON fields. Before returning the Design, reject these patterns:

- the same straight-on frontal angle in consecutive Shots;
- more than two frontal views among the six action windows of one Segment;
- fewer than five visibly different camera-angle families in one 15-second Segment;
- the FPV orbit restarting from the same front sector after a Cut instead of continuing from its outgoing sector;
- a moving camera with no named fighter action to trigger it;
- an axis crossing, screen-side swap or reverse strike direction without a visible motivated passage around a fighter.

### Visible continuous FPV-orbit contract

For every Shot, set `movement_speed` to `very fast` and `movement_amplitude` to `large`. Keep subject scale close and broadly stable: **optical zoom, digital zoom, zoom-out, dolly-out and pull-back are prohibited**. Write a measurable physical sector change into `camera_movement` and repeat its trigger/result in `additional_direction`:

- translate clockwise around the two-fighter shared midpoint by roughly 35–70 degrees per action Shot;
- vary only the physical flight height and radius—low shin level, hip level, eye level or high three-quarter—without retreating away from the fight;
- keep both fighters and their active contact geometry readable; pass behind a foreground pipe or shoulder only briefly, then restore both identities;
- prove physical travel with changing foreground occlusion, background parallax and viewpoint; keep a level readable horizon except for a small FPV bank caused by the flight arc;
- never rotate, pan, yaw, roll or spin the image in place to imitate an orbit;
- never interrupt the orbit for walking, entering, leaving, scenic coverage or a static hero frame.

At a Cut or Segment boundary, the next Shot starts from the previous Shot's outgoing camera sector and continues the same clockwise flight. It may change altitude or tighten the radius through physical translation, but may never reset to a frontal master or reverse merely to create variety. Add this exact sentence to every Shot: `CONTINUOUS FPV COMBAT ORBIT: the camera physically flies clockwise around the shared midpoint of S1 and S2 with visible parallax and changing occlusion; constant close combat distance, stable subject scale, no in-place rotation, no zoom-out, no pull-back, no slow motion, and no non-combat walking.`

Across each 15-second Segment, pass through at least five camera-position sectors: front three-quarter, side profile, rear three-quarter/over-shoulder, opposite side profile and opposite front three-quarter. Blend low shin-level, hip-level, eye-level and high three-quarter arcs into the orbit. These are different positions along one continuous FPV path, not unrelated camera tricks.

### Arcade combat coverage inside the FPV orbit

Use these framings only while the camera keeps physically travelling around the fighters. They never override the one-principal-movement rule and never pause combat.

1. **Side-axis exchange:** while the FPV path crosses the side sector, keep both fighters in a cinematic medium-close profile two-shot for no longer than 1.5 seconds, showing a live parry-and-counter rather than a pose.
2. **Signature-move detail:** tighten orbital radius physically as the fighter loads a palm, kick, elbow or rising uppercut, preserving lateral parallax and the opponent in frame. This is a fast close pass, not a lens zoom. Contact stays real-time and the orbit continues through the result.
3. **Full 360-degree fight orbit:** over the complete exchange, the physical FPV path must cumulatively pass front → side → rear → opposite side → front around the shared midpoint. Both fighters keep attacking, defending and repositioning with combat footwork throughout. The orbit is never bullet time, never an in-place 360 camera spin and never a circular background rotation.

For a 15-second fight, complete at least one full physical circuit while varying height and radius. For 30/45 seconds, each Segment continues the outgoing orbital phase and completes another circuit without repeating the same attacks. If there is no supernatural signature move, keep the same FPV combat grammar without inventing one.

The first action window starts mid-exchange from a three-quarter sector and immediately joins the clockwise FPV orbit. Across six action windows, continue through low side, high three-quarter, over-shoulder, mat/foot level, rear/opposite side and opposite front sectors. Later Segments begin at the inherited sector and continue forward; they never restart with a frontal master.

Default physical orbit for one 15-second Segment: front three-quarter → low side profile → rear three-quarter → high rear oblique → opposite side at hip level → opposite front at eye level → low front three-quarter → complete the circuit at the inherited starting sector. The visible background, horizon height and occlusion order change because the camera has travelled, not because the image rotated in place.

At least 80% of each 15-second Segment uses close-up, extreme close-up or eye-level close-up framing. Use eye-level face/shoulder and guard-interaction close-ups, extreme close-ups of eyes choosing a counter, fingers securing/releasing a grip, planted wet footwear, sweat, forearm contact and the final collision, plus mat-level close-ups for takedowns. Every wide or medium-wide image, including a boundary re-anchor, lasts no more than 1.0 second and cannot serve as the main fight coverage.

Favour hard cuts, match-on-action and sound bridges between contiguous FPV sectors. Preserve readable load, trajectory, contact and recovery during vigorous motion. Avoid impossible overhead cameras, unmotivated crane shots, whip-pan detours, continuous shaky cam, every form of slow motion, repeated neutral poses and cuts that hide whether an attack connected.

Do not render game HUD, health bars, button prompts, “KO”, “FIGHT”, subtitles or logos unless the user explicitly requests editable on-screen text. Never bake uncontrolled text into generated images.

For hand close-ups, show bare fingers closing around the real wrist, sleeve or leg, with natural knuckles, nails, palm creases and wrist anatomy. No glove, padded ridge, wrap or wrist tape may appear between an extreme close-up and the following body Shot unless explicitly requested by the user.

## Live-action Visual Language

Use photoreal skin, sweat, fabric strain, practical dust, concrete, timber, metal and real lens depth. The location is grounded cyberpunk rather than a stage: practical neon signs, damaged fluorescent tubes, wall-mounted emissive panels and wet architectural reflections provide motivated colour. Do not use a theatre spotlight, follow spot, overhead performance cone or isolated stage beam.

Water and smoke obey contact physics. Every forceful foot plant, skid or throw entry may create one low floor-level splash after the foot touches the wet surface. Splash direction follows the foot and never erupts before contact. Thin steam or smoke comes from a visible vent, pipe or damaged machine, retains slow background drift and parallax, and never hides faces, hands or the exact strike contact.

Use only two or three deliberate practical-light changes per 15 seconds: a brief power dip may darken the architecture during a block, and neon/fluorescent sources may snap back brighter on a decisive collision. Exposure recovers quickly enough to keep hands and identity readable. This is a motivated electrical failure, not rapid strobing and not stage lighting.

Heightened energy is selective. One move owns one colour, source and trajectory. Light from the effect must illuminate nearby skin, clothing and surfaces; dust, sparks, cloth and debris respond after contact. The environment cannot break before the hit, rebuild itself between Shots or produce unrelated explosions.

Use an arcade effect palette only around assigned signature techniques: a compact clean energy sphere between visible palms, a body-bound flaming trail on one committed kick, a restrained glowing aura during the visible load, one directional contact flash and sparks flying away from the collision point. Effects must preserve hand anatomy and never become a full-screen aura wall, endless beam, detached random fire, duplicate projectile or decorative sparks before contact.

### Hong Kong Kowloon wet-market arena

The default location is one coherent Hong Kong Kowloon Walled City-style fish, seafood and vegetable wet market. It is a fictional fight venue with authentic Hong Kong material density rather than a copy of a protected storefront or readable historic sign. Combine cramped tiled and weathered-concrete aisles, aged metal stalls, fish tanks, seafood trays on crushed ice, wet produce crates, drainage channels, hanging practical lamps, exposed overhead pipes/cables, humid steam and a continuously wet slippery reflective floor. Even daytime interiors require practical lamps because the dense structure blocks direct sun.

Keep a per-Shot Environment Ledger containing: current combat zone, locked gate/door state, persistent cable and pipe landmarks, wetness/puddle position, mould and rust pattern, practical-light sources and colours, smoke/steam source, and debris moved by contact. Environment detail may evolve, but architecture cannot rearrange between cuts. Fighters never walk between zones; any location change occurs only because a throw, clinch drive, evasive burst or counter carries the ongoing fight through a visibly connected threshold.

Use these visibly connected market zones for a 45-second design:

1. **0–15s · seafood aisle:** narrow wet tiled lane between fish tanks, hanging scales, crushed-ice seafood trays and dripping metal counters. Yellow-green practical tubes are the visible key source; weak cyan tank light crosses the puddles.
2. **15–30s · fish-to-vegetable junction:** the ongoing clinch or evasive counter visibly carries the fight past the same stall corner into wet produce crates, tarpaulins and one red market warning lamp. No walking transition.
3. **30–45s · rainy exterior market alley:** the preceding combat visibly forces the loading gate outward at the 30-second threshold. Continue immediately into the Hong Kong service alley beyond the same gate, drain and overhead pipes, with rain, corrugated awnings, delivery handcarts, exterior crates, cyan-blue night ambience and warm vehicle/neon spill. Architecture, wetness, displaced objects, fighter momentum and crowd positions remain traceable; never cut directly from an indoor pose to an unrelated exterior.

Z-Image creates exactly two time-isolated **environment-and-background-spectator plates** for a 45-second production: one connected indoor market plate for 0–30 seconds and one matching rainy exterior alley plate for 30–45 seconds. The exterior plate retains the visible open market gate, drain, pipes and material language that prove it is immediately outside the same location. The indoor plate shows twelve to eighteen distinct adult Hong Kong market vendors and spectators; the exterior plate shows eight to twelve. Everyone remains at the far perimeter, leaving a clean central combat route. Spectators never obscure P1/P2, duplicate a fighter or become a third combatant. Neither plate may contain P1, P2, substitute principal fighters or a generic central man/woman pair; H3 receives the real uploaded P1 and P2 separately.

### Environmental Combat Physics and Crowd Causality

Every Shot uses this visible order: **fighter load/action → exact contact point → one primary object/environment response → at most one secondary response → delayed crowd reaction → persistent outgoing state**. A prop never moves, breaks, spills or collapses before contact. Light feedback may include a directional puddle splash, scale swing, tank-water slosh or metal rattle. Medium feedback may include a shifted ice tray, overturned produce crate, dented stall panel or displaced handcart. Heavy feedback is reserved for the authored threshold climax, such as the loading-gate latch bending and the gate remaining open. Never auto-author critical building collapse or unrelated explosion.

Track stable object IDs and states in the Environment Ledger. Once a tray moves, a crate overturns, a panel dents, a tank leaks, a gate opens, debris spreads or clothing becomes wet/dirty, that state survives every later Shot, native 15-second boundary, Storyboard reorder, save/reload and local rerender until an explicit visible change occurs. Do not repair or reset it between cuts. Limit each Combat Beat to one primary and one secondary environment response so the principal martial-arts action remains readable.

Crowd reaction begins approximately 0.2–0.6 seconds after the visible impact. Nearby vendors may flinch, shield their face, pull a companion behind a stall or retreat against a wall; distant spectators may step back, watch or raise a phone. At the loading gate they part to both sides of the exit, and outdoors they remain against the shopfronts. Crowd members never move before the cause, block the fight, cross through P1/P2, clone themselves, disappear as a group or become extra fighters.

The indoor-to-outdoor transition is a continuous combat event. A throw, clinch drive, evasive burst or counter carries P1/P2 through the visible loading passage and forces the gate at the two-thirds point of the requested duration (30.0 seconds in the default 45-second film). Preserve screen direction, FPV orbital phase, fighter scale, carried debris, wetness and the open-gate state. Indoor practical light progressively yields to rainy cyan-blue exterior light and warm vehicle/neon spill. Indoor tank pumps, drains, stall rattle and short reflections transition at the visible doorway into rain, traffic and open-alley ambience; do not copy preceding generated audio or repeat an impact across the boundary.

The Studio owns editable `environment_interaction`, `incoming_environment_state`, `outgoing_environment_state`, `crowd_reaction` and `location_transition` fields. These instructions must reach the actual per-Segment H3 prompt. User-edited values remain authoritative. Use hard-edged shadows, controlled volumetric light and coarse film grain while preserving skin tone, hands and contact points. Wet high-gloss response belongs only to wet floor/metal patches. No stage spotlight, impossible light shaft, decorative smoke wall or clean futuristic corridor.

## Dialogue and Native Sound

Keep speech brief enough to preserve action. A fighter may deliver one short challenge, warning or recognition line before the exchange; do not make both fighters lip-sync while striking. Put exact Dialogue, Voice-over, Lyrics and requested On-screen Text only in `text_layers` with `explicit_user_requested=true`. Preserve wording, language, speaker and timing.

Build H3-native diegetic sound from the visible scene: foot plants, shoe slide, cloth snap, breath, bare-hand movement, skin/cloth grip, body contact, checked kick, parry, one wet-floor/mat landing, grappling fabric strain, guarded ground contact, one audible tap, debris, crowd distance, room or arena reflections and the assigned signature effect. Each Foley event occurs once at its matching visual contact. Reference audio may guide acoustic space and impact texture only; it never supplies old words or replaces the assigned speaker.

Obey the Studio music mode:

- `MUSIC OFF`: no score;
- `MUSIC AUTO`: restrained 1990s tournament-action pulse shaped around the fight, ducking under speech and impact;
- `MUSIC TIMELINE`: use only explicit Timeline music cues.

## Media and Mapping

Reuse valid loaded media through `existing_media_uses`. When both P1 and P2 are loaded, do not generate fighter identity or action-state Pictures at all: independently synthesized people would compete with the real cast. Request only the reusable Kowloon wet-market environment-and-spectator plate or a genuinely person-free prop/effect reference. A generated image contains one frozen environment state and never substitutes a generic male/female pair for P1/P2.

For the P1/P2 cast mode, keep two explicit whole-design rows: P1 is the immutable S1 identity-and-complete-wardrobe reference and P2 is the immutable S2 identity-and-complete-wardrobe reference. Their BLIP/AI text supplements the actual image conditioning; it never replaces the uploaded pixels. Every Segment loads both Pictures plus only its time-relevant indoor or outdoor Z-Image environment/spectator plate. Indoor and outdoor plates never share an ordinary Segment except a deliberately bounded threshold context. Character labels in `subject_action`, `continuity_state`, `additional_direction`, speech layers and reference instructions must keep the same S1/P1 and S2/P2 ownership.

Keep identity images active only where their fighter appears. Environment references are time-scoped to their arena. Action-state references belong only to their Shot. Analysis/control images never enter H3 loaders. Per Segment, load only the references used by that Segment; the Virtual Media Pool remains logically unlimited while H3's physical slots are dynamically allocated.

Treat every action-state reference as an identity/contact-state anchor, never as a static camera lock. The generated H3 prompt must explicitly depart from the still reference through the Shot's required physical camera displacement and full-speed body motion; do not hold the reference composition or merely animate hands inside a frozen master frame.

## Director Design JSON Contract

Return one schema-valid Director Design JSON object for the exact requested duration. Shots cover the Timeline without overlap or empty terminal ranges and stay on the 0.5-second grid. Every Shot separates:

- `subject_action`: must-complete body mechanics;
- `environment_response`: contact consequence only;
- `continuity_state`: incoming/outgoing stance, screen side, facing, distance, momentum, ability charge and damage;
- `optional_flourish`: expendable dust, sparks, crowd reaction or secondary light;
- `additional_direction`: identity, camera-axis, live-action and effect limits.

The ending completes the last authored technique at real-time speed, shows recoil and caused displacement, then preserves the resulting fighter positions and environment state in one stable supported resolution for the final 0.75–1.00 second. The FPV camera follows the contact, decelerates and settles at an eye-level three-quarter angle with a level horizon. Add a `Final Combat Resolve` marker. Do not start another attack, walk away, zoom, spin in place, replay, slow the impact, add dialogue or transform either fighter.

## Quality Gate

Before returning, verify:

- an exact 15.00, 30.00 or 45.00-second full-speed combat baseline; any dialogue-aware extension is reported and adds speech/reaction room without retiming the combat beats;
- a 45.00-second baseline contains three contiguous 15-second Segments, 18 executable action Shots and 36 globally unique numbered beats;
- both fighters remain bare-handed with five stable fingers, natural wrists and no boxing/MMA gloves, padded gauntlets, wraps or tape unless explicitly requested;
- exactly 12 numbered combat beats per 15 seconds, distributed as two causally linked beats across each of six close-range action Shots with the result contained in the sixth Shot;
- no more than two closed-fist punches per 15 seconds, never consecutive, with required kick, evasion, open-hand/parry, clinch/takedown and knee/elbow variety;
- every Shot explicitly says 2× action cadence and full-speed fight only; each action mechanic completes in roughly 0.45–0.65 seconds with no walking/entrance/exit, idle/reset pause, slow motion, bullet time, impact freeze or speed ramp;
- two stable fighters with no face, costume, ability or screen-side swap;
- when P1/P2 are loaded, S1 is only the actual P1 pixels and S2 is only the actual P2 pixels; both complete appearances and wardrobes remain locked regardless of gender, BLIP wording or generated support media;
- karate, judo, Jeet Kune Do and Wing Chun each appear with stable ownership and readable attack/defence causality;
- when MMA is requested, takedown entry/completion, top/bottom control, limited ground-and-pound and submission/tap occur in order without identity or limb swaps;
- the Action Ledger contains no duplicate mechanic/target/outcome combination across 45 seconds;
- every Shot's attacker, defender and top/bottom ownership are physically coherent; any self-defence, unexplained reversal or repeated exchange is shown as an `ACTION RISK` in Storyboard/Timeline before rendering;
- every signature technique has load, trajectory, contact and recovery;
- no Shot exceeds the action budget or uses more than one main camera move;
- every 15-second Segment physically passes through at least five orbital camera sectors and completes a clockwise FPV circuit without resetting to a frontal master;
- every Shot uses very-fast, large-amplitude physical FPV translation around the two-fighter midpoint, named incoming/outgoing sectors and a readable combat trigger/result;
- subject scale stays close and stable: there is no zoom-out, pull-back, dolly-out, lens retreat or in-place 360 spin;
- the cumulative orbit proves front → side → rear → opposite side → front using genuine parallax and changing occlusion while every contact remains real-time;
- at least 80% close-up/eye-level/extreme close-up coverage and no wide Shot longer than 1.0 second;
- water follows foot/body contact, smoke has a visible source, and practical cyberpunk lights change only two or three times without any stage spotlight;
- the Kowloon Walled City-style fish, seafood and vegetable wet market remains visibly connected by ongoing combat only, with wet floor, stalls, tanks, produce crates, pipes/cables, practical lights and displaced debris persisting until visibly changed;
- one 0–two-thirds indoor Z-Image plate and one final-third exterior-alley plate supply background spectators around a clear central fight route with no substitute/duplicate P1 or P2;
- every environment response follows a named visible cause, contains at most one primary and one secondary response, and hands its persistent state into the next Shot;
- red `ACTION RISK` / `STATE CONFLICT` markers first enter the causal auto-repair pass: the engine uses the fact ledger, combat causality, event causality, environmental causality, force direction and physical feedback to add only a deterministic opponent response, reversal or minimal contact feedback; it never changes user dialogue, cast bindings or user-edited fields, records the repair as `CAUSAL AUTO-FIX`, and keeps the red risk only when a safe inference is impossible;
- the silent causal validator confirms all seven Beat fields, action-triggered camera binding and at least four inherited state fields; a stable no-contact final recovery is valid and must not create a false red environment warning;
- the final Shot contains a `FINAL SETTLE` action clause, a stable outgoing support/velocity state and no next-Beat trigger;
- displaced, dented, leaking, open, wet or broken objects never self-repair at a Cut or Segment boundary;
- crowd reactions begin after impact, remain at the perimeter and never add a third fighter;
- active combat crosses a visible market gate into the matching rainy Hong Kong alley at the two-thirds threshold with continuous FPV phase, screen direction, lighting and native sound space;
- the 15-second boundary inherits state and never repeats the first Segment;
- energy light and destruction follow contact rather than precede it;
- all spoken words exist as editable text layers and no unwanted visible text is generated;
- media references are type-correct, time-scoped and mapped only to the active Segment.

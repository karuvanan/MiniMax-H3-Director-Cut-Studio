---
name: street-fighter-live-action-h3
description: |
  Design 15-45 second MiniMax H3 live-action arcade martial-arts movie scenes with two readable fighters, grounded striking and MMA ground-game choreography, non-repeating multi-Segment action, selectively heightened signature attacks, editable speech, native impact sound and dense industrial cyberpunk environments. Use when the user asks for a Street Fighter-like live-action fight, world-warrior tournament, arcade combat film or stylized one-on-one martial-arts showdown; do not use for ordinary realistic fights without signature-move spectacle.
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
- Mandarin dialogue in editable `text_layers` when speech is requested.

Do not fill a short fight with introductions for many famous characters. Background spectators may remain soft, distant and non-speaking; they never become extra foreground fighters.

## Character Bible

Give each fighter one compact identity line containing face, age range, hair, build, costume colours, footwear, signature stance and one ability. Preserve these across every Shot and generated reference.

Lock:

- face, age, skin tone, hair, build and body proportions;
- costume design and colour blocks, gloves, footwear and accessories;
- left/right handedness, stance, ability ownership and current injury/dirt state.

Both fighters wear compact **open-finger MMA gloves**, never closed boxing gloves. Lock each glove's colour and design: exposed separate fingers for gripping, a thick but compact foam ridge over the knuckles, a rounded streamlined outer shell without sharp corners, flexible palm/inside-finger openings and a secured wrist wrap. Keep five anatomically distinct digits visible when a hand is shown. Padding stays on the back of the knuckles and never turns into a mitten, covers the fingertips or prevents a visible grappling grip. Wet grime may accumulate along the lower glove cuff after floor contact; record it in the continuity state so it persists and never jumps to the clean upper knuckle pad without contact.

Allow expression, pose, limb angle, breathing, cloth movement and physically caused damage to change. Never swap costume colours, abilities or screen identity. A fighter cannot teleport, duplicate, change face, gain extra limbs or recover a torn costume without a visible cause.

If the user assigns `@P1` or another loaded Picture, use it only for the assigned identity/costume/environment. Never invent an unloaded `@P/@V/@A` ID or assume an actor likeness that the reference does not contain.

## Build an Executable Fight

### 15-second structure — exactly 12 close-combat beats

Treat an attack, block, parry, trapping contact, grip, throw entry/completion, top-control establishment, short ground-strike burst, submission entry or intercepting counter as one **combat beat**. Produce exactly 12 numbered combat beats in every 15-second Segment. A visible tap-and-immediate-release may serve as the final result beat. Do not count establishing poses, camera moves, facial reactions, water splashes, smoke or recovery holds as combat beats.

Use seven chronological, non-overlapping Shots on the 0.5-second grid:

1. **0.0–1.0s · eye-level wide geography:** establish the two fighters, wet floor, screen sides, arm's-reach route and fight axis. No combat beat. This is the only default wide Shot.
2. **1.0–3.5s · close-up:** `[BEAT 01]` committed attack and `[BEAT 02]` immediate defence.
3. **3.5–6.0s · extreme close-up / eye-level close-up:** `[BEAT 03]` counterattack and `[BEAT 04]` parry or trapping reversal.
4. **6.0–8.5s · close-up:** `[BEAT 05]` centre-line strike and `[BEAT 06]` judo grip capture.
5. **8.5–11.0s · extreme close-up:** `[BEAT 07]` judo throw entry and `[BEAT 08]` body-frame escape that stops the throw.
6. **11.0–13.0s · eye-level close-up:** `[BEAT 09]` low intercepting kick and `[BEAT 10]` karate low deflection.
7. **13.0–15.0s · close-up to extreme close-up:** `[BEAT 11]` final straight counter and `[BEAT 12]` short elbow/forearm signature collision. Complete contact by 14.5s and hold the resulting faces, guard positions and water/smoke state for the final 0.5s.

Every action Shot contains exactly two short must-complete action sentences, one for each numbered beat. Two beats share one causal exchange: attack then defence/counter. Never describe all 12 beats in one Shot, never put a third required action into a 2–2.5 second Shot, and never hide a required beat in `optional_flourish`.

### 30-second structure

Use two complete 15-second, 12-beat phases: 24 combat beats total. Segment 1 establishes the rivalry and ends with its twelfth collision. Segment 2 inherits the exact guard, contact distance, screen side, wetness, smoke and lighting state, then begins with a new `[BEAT 13]`; it never replays `[BEAT 01]`, the opening stance or the first collision. A second eye-level wide re-anchor is permitted only from 15.0–16.0s and must not reset positions.

The preceding 24 frames are silent visual motion context only; never copy old dialogue, impact sound or music into the next Segment. If the user requests fewer actions, preserve their explicit count instead of forcing this 12-beat mode.

### 45-second structure — three different phases, 36 non-repeating beats

Use three continuous 15-second Segments and the same seven-Shot timing grid in each Segment. This creates 21 chronological Shots and exactly 36 numbered combat beats. At 15.0–16.0s and 30.0–31.0s, the one-second eye-level geography Shot must reveal the next connected architectural zone and inherited body positions; it cannot replay the opening stance or add a combat beat.

Maintain a global **Action Ledger** for all 36 beats with: `beat_id`, `attacker`, `technique/mechanic`, `target_or_grip`, `defensive_response`, `resulting_position`, `environment_contact`. Before returning the design, compare every beat against all previous beats. A beat is duplicated if the same fighter uses the same mechanic on the same target/grip with the same outcome; merely renaming it, changing camera angle or adding sparks does not make it new. Rewrite duplicates before output.

Use this default three-phase ledger unless the user supplies a different non-repeating choreography:

- **Segment 1 · 0–15s · standing probe and style collision:** `[01]` JKD lead stop-hit, `[02]` karate inward forearm block, `[03]` karate reverse straight, `[04]` Wing Chun pak-sau redirect, `[05]` Wing Chun centre-line vertical punch, `[06]` judo wrist-and-sleeve capture, `[07]` judo forward balance break, `[08]` JKD elbow frame cancelling the throw, `[09]` JKD low side kick, `[10]` karate low deflection, `[11]` compact karate hammerfist, `[12]` Wing Chun bong-sau signature collision.
- **Segment 2 · 15–30s · clinch, takedown and top pressure:** `[13]` Wing Chun lap-sau arm drag, `[14]` judo overhook clamp, `[15]` single-leg capture, `[16]` sprawl defence, `[17]` switch to double-leg capture, `[18]` whizzer pivot defence, `[19]` corner-turn finish, `[20]` controlled takedown landing, `[21]` stable side control, `[22]` bottom forearm frame, `[23]` one guarded straight ground contact, `[24]` one guarded short-elbow ground contact.
- **Segment 3 · 30–45s · escape, positional reversal and submission:** `[25]` bottom hip bridge, `[26]` hip escape to half guard, `[27]` top fighter re-centres the base, `[28]` bottom knee shield creates distance, `[29]` bottom underhook reversal, `[30]` completed top/bottom position swap, `[31]` new top fighter isolates one wrist, `[32]` controlled straight-arm submission alignment, `[33]` defender clasps hands to stop extension, `[34]` attacker changes to a controlled choke position, `[35]` defender clearly taps, `[36]` attacker immediately releases into the final hold.

Do not replay punches, blocks, takedown entries, falls, ground contacts, reversals or tap shots as filler at Segment boundaries. Continue the outgoing body state and introduce the next unused mechanic.

## Four-style Close-combat Grammar

Keep both fighters mostly within arm's reach. Briefly open distance only for the low side kick or a compact signature collision; close it again through visible footwork. Assign stable style ownership—by default S1 uses karate plus judo and S2 uses Jeet Kune Do plus Wing Chun—so H3 does not randomly change technique between cuts.

- **Karate:** hard outside/inside forearm block, low deflection, reverse straight punch and compact front or side kick. Show hip rotation, planted heel, straight line and immediate recoil; no decorative aerial kata.
- **Judo:** wrist-and-sleeve capture, balance break, hip placement and throw entry. In this rapid mode, the opponent may frame the hip and escape before a full throw so both faces remain available for the next close-up. Grip ownership cannot switch hands between Shots.
- **Jeet Kune Do:** intercepting lead straight, stop-hit, economical low side kick and elbow/forearm frame. Use shortest-path timing: the counter starts while the opponent commits, not after a long pause.
- **Wing Chun:** pak sau, tan sau or bong sau deflection, centre-line vertical punch, short elbow and one compact trapping exchange. Hands remain anatomically separate; never generate a many-arm chain-punch smear.

The default 12-beat order must demonstrate all four systems as one causal attack/defence reversal: Jeet Kune Do attack → karate defence → karate counter → Wing Chun parry → Wing Chun centre-line attack → judo capture → judo throw entry → Jeet Kune Do frame escape → Jeet Kune Do low kick → karate low deflection → karate straight counter → Wing Chun short-elbow signature collision.

## MMA Ground-game Variant

When the request mentions MMA, takedown, ground game, grappling control, ground-and-pound or submission, preserve the seven-Shot/12-Beat budget but replace the latter half of the standing chain with one readable standing-to-ground sequence. Do not add ground actions on top of the existing 12 beats.

Use this default mixed chain: `[BEAT 01]` Jeet Kune Do lead attack → `[BEAT 02]` karate defence → `[BEAT 03]` karate reverse-straight signature counter → `[BEAT 04]` Wing Chun pak/bong-sau signature collision → `[BEAT 05]` Wing Chun centre-line strike → `[BEAT 06]` judo/MMA clinch or underhook entry → `[BEAT 07]` single- or double-leg capture → `[BEAT 08]` balance break and controlled takedown landing → `[BEAT 09]` stable top-position control → `[BEAT 10]` one short ground-and-pound burst → `[BEAT 11]` controlled submission position → `[BEAT 12]` visible tap and immediate release.

Apply these cinematic mechanics:

- **Takedown:** show a visible level change, hands capturing the assigned single leg or both legs, the standing fighter's balance breaking, one controlled descent and one floor impact. Split entry and completion across consecutive beats; never teleport from standing to the floor.
- **Grappling control:** after landing, explicitly lock the top fighter, bottom fighter, head direction, screen side, grip hand and one simple position such as half guard or side control. The top fighter uses a wide base and body weight; the bottom fighter visibly frames or bridges. Never swap top/bottom identity between cuts.
- **Ground-and-pound:** show one compact burst containing no more than two readable fist or short-elbow contacts to a guarded target, followed by a visible defensive frame. Do not create an endless barrage, graphic injury, extra arms or contacts hidden by smoke.
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

Keep a clear fight axis and stable screen direction: S1 begins on one side, S2 on the other, and an axis crossing requires a visible motivated move. Each Shot has one principal camera movement.

At least 80% of each 15-second Segment uses close-up, extreme close-up or eye-level close-up framing. Use a compact sequence of:

- one eye-level wide two-shot lasting no more than 1.0 second to establish distance and footwork;
- eye-level close-ups of faces, shoulders and guard interaction;
- extreme close-ups of eyes choosing a counter, fingers securing/releasing a grip, planted wet footwear, sweat, forearm contact and the final collision;
- short lateral close-up movement for a committed advance;
- a controlled close-up settle for the final positions.

Favour hard cuts, match-on-action and sound bridges. Avoid constant orbiting, impossible overhead cameras, excessive whip pans, long slow motion, repeated neutral poses and cuts that hide whether an attack connected. Slow motion may occupy only the decisive contact moment, then immediately return to real-time recovery.

Every wide or medium-wide image, including a boundary re-anchor, is capped at 1.0 second. Never use a wide master as the main fight coverage. Maintain the eye-level axis across close-ups so rapid cutting does not swap S1/S2 or reverse the strike direction.

Do not render game HUD, health bars, button prompts, “KO”, “FIGHT”, subtitles or logos unless the user explicitly requests editable on-screen text. Never bake uncontrolled text into generated images.

For glove close-ups, show the exposed fingers closing around the real wrist, sleeve or leg while the padded knuckle ridge remains on the back of the hand. The glove shape, cuff dirt and colour cannot change between an extreme close-up and the following body shot.

## Live-action Visual Language

Use photoreal skin, sweat, fabric strain, practical dust, concrete, timber, metal and real lens depth. The location is grounded cyberpunk rather than a stage: practical neon signs, damaged fluorescent tubes, wall-mounted emissive panels and wet architectural reflections provide motivated colour. Do not use a theatre spotlight, follow spot, overhead performance cone or isolated stage beam.

Water and smoke obey contact physics. Every forceful foot plant, skid or throw entry may create one low floor-level splash after the foot touches the wet surface. Splash direction follows the foot and never erupts before contact. Thin steam or smoke comes from a visible vent, pipe or damaged machine, retains slow background drift and parallax, and never hides faces, hands or the exact strike contact.

Use only two or three deliberate practical-light changes per 15 seconds: a brief power dip may darken the architecture during a block, and neon/fluorescent sources may snap back brighter on a decisive collision. Exposure recovers quickly enough to keep hands and identity readable. This is a motivated electrical failure, not rapid strobing and not stage lighting.

Heightened energy is selective. One move owns one colour, source and trajectory. Light from the effect must illuminate nearby skin, clothing and surfaces; dust, sparks, cloth and debris respond after contact. The environment cannot break before the hit, rebuild itself between Shots or produce unrelated explosions.

### Sealed industrial vertical-maze environment

When the user requests the supplied reference mood, derive material, density and lighting grammar only; do not reproduce real signage, readable historical text, named storefronts or an exact identifiable layout. Build one fictional sealed abandoned megastructure whose lower levels are permanently sun-blocked by dense construction. Even daytime interiors require practical lamps.

Keep a per-Shot Environment Ledger containing: current connected zone, locked gate/door state, persistent cable and pipe landmarks, wetness/puddle position, mould and rust pattern, practical-light sources and colours, smoke/steam source, debris moved by contact, and the fighters' route. Environment detail may evolve, but architecture cannot rearrange between cuts.

Use these connected zones for a 45-second design:

1. **0–15s · sealed lower service corridor:** narrow weathered concrete, locked folding grille and steel service door, dense overhead cable canopy, exposed water pipes, rusted electrical boxes, mould patches and scattered domestic remnants. Yellow-green sodium/IES-profiled industrial tubes are the visible key source; weak cyan spill enters from the next passage.
2. **15–30s · flooded utility landing:** reveal the same corridor turning onto a cramped stair/pump landing. The wet floor becomes locally high-gloss, reflecting cyan-blue utility light and one red warning lamp. A struck valve or already leaking pipe may intensify the drip only after visible contact; low steam has a visible pipe or machine source.
3. **30–45s · upper maintenance catwalk:** the visible stair leads upward into a vertical maze of grilles, corroded steel, exposed pipework, hanging cable bundles and accumulated living/industrial debris. Purple-blue practical neon leaks through slats; hard backlight can create a brief silhouette while face identity remains recoverable in the next close-up.

Allow at most one causal environment change per Shot: a tube dies after vibration, a red alarm activates after a damaged switch, a puddle ripples after impact, rust dust falls after wall contact, steam thickens after a valve strike, or a locked grille rattles without opening. Carry every change forward. Use hard-edged shadows, controlled volumetric light and coarse film grain, but preserve skin tone, hands and exact contact points. Wet high-gloss response belongs only to wet floor/metal patches, never to every surface. No stage spotlight, impossible light shaft, decorative smoke wall, clean futuristic corridor or unrelated exterior daylight.

## Dialogue and Native Sound

Keep speech brief enough to preserve action. A fighter may deliver one short challenge, warning or recognition line before the exchange; do not make both fighters lip-sync while striking. Put exact Dialogue, Voice-over, Lyrics and requested On-screen Text only in `text_layers` with `explicit_user_requested=true`. Preserve wording, language, speaker and timing.

Build H3-native diegetic sound from the visible scene: foot plants, shoe slide, cloth snap, breath, glove movement, body contact, blocked strike, one wet-floor/mat landing, grappling fabric strain, guarded ground contacts, one audible tap, debris, crowd distance, room or arena reflections and the assigned signature effect. Each Foley event occurs once at its matching visual contact. Reference audio may guide acoustic space and impact texture only; it never supplies old words or replaces the assigned speaker.

Obey the Studio music mode:

- `MUSIC OFF`: no score;
- `MUSIC AUTO`: restrained 1990s tournament-action pulse shaped around the fight, ducking under speech and impact;
- `MUSIC TIMELINE`: use only explicit Timeline music cues.

## Media and Mapping

Reuse valid loaded media through `existing_media_uses`. Request only missing fighter identity, arena identity or a genuinely necessary signature-state reference. A generated image contains exactly one frozen instant, the correct two-fighter count, stable costume/ability ownership and the real arena. Never ask one image to show a complete combo, multiple time states or a neutral studio background.

Keep identity images active only where their fighter appears. Environment references are time-scoped to their arena. Action-state references belong only to their Shot. Analysis/control images never enter H3 loaders. Per Segment, load only the references used by that Segment; the Virtual Media Pool remains logically unlimited while H3's physical slots are dynamically allocated.

## Director Design JSON Contract

Return one schema-valid Director Design JSON object for the exact requested duration. Shots cover the Timeline without overlap or empty terminal ranges and stay on the 0.5-second grid. Every Shot separates:

- `subject_action`: must-complete body mechanics;
- `environment_response`: contact consequence only;
- `continuity_state`: incoming/outgoing stance, screen side, facing, distance, momentum, ability charge and damage;
- `optional_flourish`: expendable dust, sparks, crowd reaction or secondary light;
- `additional_direction`: identity, camera-axis, live-action and effect limits.

Final Hold preserves the two resulting fighter positions and environment state without a new attack, dialogue or transformation.

## Quality Gate

Before returning, verify:

- exact 15.00, 30.00 or 45.00 seconds as requested;
- exact 45.00 seconds when requested, with three contiguous 15-second Segments, 21 Shots and 36 globally unique numbered beats;
- both fighters retain open-finger MMA gloves with visible separate fingers, compact padded knuckles, rounded shell, stable wrist wrap/colour and persistent lower-cuff grime;
- exactly 12 numbered combat beats per 15 seconds, distributed as two beats across each of six close-range action Shots;
- two stable fighters with no face, costume, ability or screen-side swap;
- karate, judo, Jeet Kune Do and Wing Chun each appear with stable ownership and readable attack/defence causality;
- when MMA is requested, takedown entry/completion, top/bottom control, limited ground-and-pound and submission/tap occur in order without identity or limb swaps;
- the Action Ledger contains no duplicate mechanic/target/outcome combination across 45 seconds;
- every signature technique has load, trajectory, contact and recovery;
- no Shot exceeds the action budget or uses more than one main camera move;
- at least 80% close-up/eye-level/extreme close-up coverage and no wide Shot longer than 1.0 second;
- water follows foot/body contact, smoke has a visible source, and practical cyberpunk lights change only two or three times without any stage spotlight;
- the three industrial zones remain one connected route, and every gate, cable/pipe landmark, wet patch, light failure, alarm, steam source and displaced debris state persists until visibly changed;
- the 15-second boundary inherits state and never repeats the first Segment;
- energy light and destruction follow contact rather than precede it;
- all spoken words exist as editable text layers and no unwanted visible text is generated;
- media references are type-correct, time-scoped and mapped only to the active Segment.

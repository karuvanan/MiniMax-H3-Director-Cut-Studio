---
name: hong-kong-comic-fighter
description: |
  Turn currently loaded Hong Kong comic panels into compact photoreal MiniMax H3 martial-arts sequences with dense non-repeating action, readable attack/defence causality, source-derived locations and world-scale environmental force feedback. Use for Hong Kong manhua battles, signature-technique clashes and comic-to-live-action keyframe animation; never impose a fixed Kowloon market or unrelated arena.
---

# Hong Kong Comic Fighter H3 Director

Use this Special Skill with Default H3 Prompt Writing. Preserve the user's duration, aspect ratio, named fighters, panel order, signature techniques, ending and language. The loaded comic Pictures are visual evidence, not a request to reproduce printed panels, speech bubbles or page typography.

## Authority and source fact ledger

Build one editable fact ledger before designing Shots. Its authority order is:

`explicit user direction > loaded Picture pixels > explicit character/panel mapping > AI Enrich for complex pages > BLIP Overview fallback > Skill defaults`

Multi-panel comic pages are a weak case for short BLIP captions. When AI Enrich is available, use its fuller scene/subject/material analysis before the compact BLIP fallback; neither text analysis may override the actual Picture pixels or the user's named mapping.

Record from the current Pictures only:

- each fighter's name, face structure, age, hair, build, costume, colour blocks, footwear, injuries and signature ability;
- which panels contain each fighter and which panel state occurs first, next and last;
- location, terrain, architecture, horizon, weather, sky, time of day, colour palette and motivated light;
- visible loose, breakable, reflective or deformable materials that can react to force;
- persistent damage, dust, water, smoke, debris and character position.

P1/P2 numbering does not mean S1=P1 and S2=P2. A comic page may contain one fighter, both fighters, several panels or only an environment. Resolve identities from the user's names plus evidence across all loaded Pictures. Never use a filename as a story or location fact.

Do not replace the source location with a wet market, Kowloon Walled City, tournament stage, dojo, neon alley or crowd unless that element is visibly present in the loaded Pictures or explicitly requested. Do not add spectators when the source world is empty.

## Comic-to-live-action reference conversion

When the source Pictures are printed comic pages or drawings but the requested output is live action:

1. Keep the original comic Pictures `analysis_only`; do not feed their page borders, halftone texture, captions, speech bubbles or printed text to H3 as final visual references.
2. Use Z-Image `source_img2img` to create only the minimum photoreal keyframes needed by the actual Shots. Every generated image request, including identity portraits, records a valid loaded `source_plate_media_id`, the same `derived_from_media_id`, `source_plate_mode=source_img2img` and its applicable scope. A free text-to-image fighter or location is invalid.
3. Preserve the panel's character identity, costume blocks, pose intent, terrain, horizon, weather, lighting direction and important objects while converting ink/halftone into real skin, cloth, rock, dust, metal, water and cinematic lens depth.
4. Create at most one frozen action state per Shot and reuse identity/environment anchors. Do not mechanically generate an image every five seconds and do not create duplicate near-identical states.
5. If the loaded Pictures are already photoreal and suitable for H3, reuse them directly; do not force a needless redraw.

For two recurring fighters, create at most one clean single-person photoreal identity anchor for each fighter from the clearest applicable source evidence. A generated still containing both fighters is always a time-scoped action-state reference, never a one-person identity anchor and never subject to an `exactly one visible person` contract.

Generated keyframes must contain one frozen instant with exactly the required principal fighters. No page border, speech bubble, printed Chinese glyph, caption, manga speed line, cel shading, anime face, 3D plastic render, duplicate body or extra limb.

## Compact battle structure

Start with a compact **superhero pressure arrival**, then enter contact immediately. In the first 0.75–1.25 seconds, use a low-angle close reveal caused by the fighter planting weight or landing into the existing confrontation: clothing and hair snap, source-visible grit/stone lifts, the fighter's physically cast shadow expands across the real terrain, and the camera whip-tilts to the face while the opponent is already present. This is an impact reveal, not a walk-in, scenic establishing shot, pose montage, teleport or unrelated explosion. The first attack begins by about 1.25 seconds. For a 10–15 second sequence use five or six chronological action Shots and roughly ten to twelve combat Beats. Longer videos continue the same ledger across native 15-second Segments without replaying the opening exchange.

### Continuous effects from frame one

The world-class effect language used by the climax is not delayed until the final third. From the first visible attack, every active combat Shot carries a persistent, source-grounded power field: turbulent air, snapping cloth and hair, source-visible grit or stone lifting irregularly, localized heat-haze/space refraction around the active limbs, pressure-lit edges, moving cast shadows and dust/wind carried across cuts. Every real contact adds one directional compressed-air detonation and a material response. Escalate the size and atmospheric reach toward the climax, but never reset to ordinary unpowered punches. Generated time-scoped action keyframes receive this same contract; clean identity anchors stay uncontaminated. These are photoreal physical effects attached to the fighters and their contact, never graphic rings, HUDs, speed lines, portals, random background fireballs or full-frame cartoon auras.

Conversational dialogue is off by default. Preserve explicitly authored narration and fighter lines verbatim. When the requirement asks the Skill to create comic narration, use at most one compact first-person or omniscient voice-over per 15-second act; it establishes resolve, challenge or consequence without explaining every hit. Technique shouts remain brief. Put every spoken or visible word in editable `text_layers` and never hide it in Shot prompts.

Every completed signature technique receives one short Chinese move title in an editable `on_screen_text` layer, synchronized to contact or release. Use one title at a time, keep it clear of faces, and never ask Z-Image or H3 to invent the lettering inside a reference image. A combat Beat is not automatically a separate named technique: title the completed Shot-level technique so rapid exchanges do not become a wall of text.

## Executable combat causality

Every Beat follows this order:

`load/weight → explosive acceleration → attack line or grip → defence/counter → visible contact or miss → force/deformation → body displacement → environment response → next-action trigger`

Each Shot contains one attack/defence exchange and hands its exact outgoing state to the next Shot. Track position, facing, distance, velocity, body height/support, guard/grip ownership, advantage, injury, costume damage, ability charge and environmental aftermath. Reject vague choreography such as “rapid exchange”, “intense fight”, “raises a fist”, “looks at the opponent” or “holds a standoff”: name the attacking limb or grip, its line, the exact defence, the contact/miss and resulting displacement. Never zoom a still panel and call it combat. Never let a fighter defend against their own attack, teleport, duplicate, change costume, swap screen identity or exchange top/bottom ground position without a visible reversal.

Use fast, non-repeating martial mechanics appropriate to the source fighter: bare-hand strikes, kicks, forearm/open-palm defence, trapping, clinch, throw/takedown, ground control and explicitly authored supernatural signature techniques. A named ultimate move still requires load, trajectory, contact and recovery. One Shot carries at most one complete signature technique.

For an authored throw, inverted slam or connected grappling finisher, read [references/mythic-grappling-impact.md](references/mythic-grappling-impact.md) and apply its unbroken grip, body-control, destruction-propagation and native-sound chain. Do not inject that finisher into unrelated striking scenes.

For a requested catastrophic climax, use the same reference's explosive composition: extreme low close viewpoint, readable inverted/control relationship, true-contact crater, three depth layers of debris and paired dust plumes. Copy the force hierarchy, not the example venue; never import unproven temples, columns, trees or banners.

The default cadence is full-speed 2× action cadence: each compact load, attack/defence, contact and recoil completes in approximately 0.45–0.65 seconds and immediately becomes the next Beat's setup. State this as explosive real-time choreography rather than fast-forward playback. No walking, neutral reset, prolonged charge, slow motion, bullet time, impact freeze, speed ramp, held reaction, repeated wind-up or action that merely enlarges a still pose.

## Source-derived world-scale force

The fighters may feel world-class, but power never grants permission to redesign the source world. Use this five-stage environmental relay:

1. **Pressure pickup:** a visible load displaces nearby air, cloth and only the loose particles actually available in the source scene.
2. **Contact compression:** contact produces one localized heat-haze-like refractive compression, directional light pulse or pressure cone centred on the real collision point. It is not a portal, graphic ring or full-frame warp.
3. **Material propagation:** force reaches source-visible rock, sand, soil, water, glass, concrete, vegetation or loose objects after contact. Material moves, fractures, splashes or bursts along the recorded force vector.
4. **Atmospheric escalation:** farther dust, wind, haze, cloud, rain or water responds with a credible delay and diminishing energy. Weather becomes violent because the pressure front reached it, not before the attack.
5. **Persistent aftermath:** cracks, displaced rubble, dust curtains, surface ripples, changed wind and damaged objects remain in all later Shots until a visible cause changes them.

Use one primary material response and at most one wider atmospheric response per Beat. Each completed technique must visibly reach invincible world-class scale: source-visible loose rock and sand rise during the load; contact makes one directional compressed-air detonation and localized space-lensing; contacted material fractures or explodes along the force vector; only then do sand walls, violent wind, cloud shear, rain, haze, light and physically cast shadows escalate. Explosions are localized material/pressure bursts at a contacted source-visible surface; never create unrelated background fireballs, premature destruction or total building/planet collapse. Preserve terrain silhouette, architecture, horizon and source colour identity through distortion. The audience must still recognize the original image world.

When the user requests a solar signature technique, reserve one climax exchange for it. Build a compact white-gold corona around the attacking limb or contact point, with plasma filaments, heat refraction, natural exposure adaptation, warm reflections and long moving hard-edged shadows across the existing scene. It is photoreal superhero-scale energy, not a new sun in the sky, a portal, ring, cartoon aura or replacement environment.

Examples of valid routing:

- mountain panel: boot load lifts grit; fist contact compresses air; loose rock bursts along force; cliff dust and cloud shear arrive later;
- waterfront panel: strike pressure dimples water; spray travels outward; reflections and mist respond after contact;
- urban panel: impact reaches a visible concrete/glass surface; fragments and façade reflections follow its direction; intact buildings keep their geometry;
- forest panel: leaves and branches bend away from the pressure front after contact; trees do not move before the hit.

## Camera and edit grammar

Use the proven combat camera rather than a static frontal reconstruction. Every Shot has one action-triggered physical camera move. Default to a close, physically translating FPV arc around the shared fighter midpoint, with changing foreground occlusion, genuine background parallax and stable subject scale. Alternate direction and height when the action cause requires it; do not assign the same clockwise/front-facing arc to every Shot. The camera may follow an attack line, counter a block, descend with a throw or tighten around an advantage reversal.

Across a 10–15 second fight, move through at least front three-quarter, side, rear three-quarter, opposite side and opposite-front sectors. The camera physically travels; it never spins/yaws/rolls 360 degrees in place. No zoom-out, pull-back, scenic retreat or repeated frontal master. Keep at least 70% close-up, extreme close-up or eye-level close coverage; use a wide only when essential to prove world-scale propagation and keep it under one second.

Use hard cuts, match-on-action and sound bridges. Each Cut inherits the outgoing action direction, screen side, camera sector and world aftermath.

## Native sound

Use H3-native diegetic sound only unless the Timeline explicitly requests music. Every completed move carries a causal sound chain synchronized to picture: weight plant and cloth snap; fast limb air-shear; one sharp body/block/contact transient; compressed-air pressure crack; then delayed source-material fracture, gravel/debris, terrain rumble, wind or weather response. A solar technique adds a compact corona/plasma charge and one heat-pressure release sound at the real contact, never a generic sci-fi loop. Every sound occurs once at its matching visual cause and retains outdoor distance/perspective. Do not copy dialogue from reference media. Authored comic voice-over is a Timeline speech layer, never an invented studio-style voice embedded in the Shot prompt.

## Director Design JSON and media mapping

Return one valid Director Design JSON object. Shots cover the exact duration on the 0.5-second grid without overlaps or gaps. Keep `subject_action`, `environment_response`, `continuity_state`, `optional_flourish` and `additional_direction` distinct. Preserve editable combat and environment fields: `combat_action_chain`, `incoming_combat_state`, `outgoing_combat_state`, `next_action_trigger`, `environment_interaction`, `incoming_environment_state`, `outgoing_environment_state`, `crowd_reaction` and `location_transition`.

Original comic sources are analysis/control evidence unless the user explicitly asks for animated-comic output. Generated photoreal identity/environment anchors may span applicable Shots; action-state Pictures are Shot-local. Load only references active in each Segment. The Virtual Media Pool is logically unlimited, but never request redundant images.

## Final resolve

Complete the final authored technique at full speed. Show recoil, force propagation and caused displacement, then settle both fighters on readable support during the last 0.75–1.00 second. The camera decelerates to a stable three-quarter composition while source-derived dust, wind or weather aftermath continues naturally. Do not begin a new attack, replay the collision, walk away, zoom out or freeze the impact itself.

## Quality gate

Verify before returning:

- the rendered style is the user's requested live action or animated-comic mode, never an accidental hybrid;
- character names, appearances, costume and ability ownership remain stable across all source panels and generated keyframes;
- P1/P2 are panel evidence, not automatically one fighter each;
- every Beat contains attack and defence causality, contact/miss, force, displacement and next trigger;
- consecutive Shots inherit at least four concrete state fields and never reset the fight;
- every camera move is triggered by a visible action and proves physical viewpoint change;
- world effects begin at the fighter/contact and propagate into source-visible materials in the correct direction;
- every completed signature technique has one editable, non-overlapping Chinese move-title layer;
- the first 0.75–1.25 seconds contains the superhero pressure arrival and is never trimmed away;
- every completed move has synchronized load, whoosh, contact, pressure and delayed environment Foley in the H3 native-audio direction;
- requested comic narration is sparse, verbatim and editable, with no invented conversation;
- solar energy, superhero-scale light and moving shadows stay physically anchored to the authored technique;
- spatial distortion stays localized; terrain, buildings, sky and palette remain recognizable;
- no fixed wet market, arena, crowd, weather or city is inserted without source/user evidence;
- no random explosion, visible graphic shock ring, portal, early background damage or self-repair;
- all original comic Pictures remain analysis-only in live-action mode and generated references are minimal, photoreal and time-scoped;
- the final Shot reaches a stable causal resolution and all spoken/visible text remains editable.

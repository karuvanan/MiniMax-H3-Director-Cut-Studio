---
name: source-video-cast-remake-h3
description: |
  Analyse a loaded V1, bind every principal-role appearance to the loaded P-image cast pool, then use the automatically selected LoRA Preserve V1 engine to replace those identities while retaining V1 performance, scene, camera, timing and soundtrack. V1 plus P1 are the minimum inputs; every additional loaded Picture is optional role capacity.
---

# Source Video Cast Reconstruction H3

Use this Special Skill with the bound Default H3 Prompt Writing Skill and only with source footage the user is authorized to transform.

## Remake Engine

Remake Engine selection is automatic and read-only. With no Special Skill, or with any other Special Skill, Studio displays **Create H3 Remake** and uses the ordinary H3 reconstruction compiler. Selecting this Skill displays **LoRA Preserve V1** and is the only route that loads `MiniMax-H3-Character-Swap-LoRA`, `LabsH3PrepareVideo` and `H3RelayWindowedEdit`. Legacy Project files that saved a manual Creative or Directed mode are migrated to the engine required by the currently selected Skill.

Director Design always creates the complete source-role, Shot, speaker/listener, scene and timing ledger; it must not emit ComfyUI node JSON or Relay checkpoint IDs. Studio cuts each exact 24 fps V1 Shot at runtime. The LoRA replaces one selected source performer per pass, so a multi-character Shot is processed sequentially: protected/listening roles first and the active speaker last. The preceding pass output becomes the next pass source.

`@V1` remains `analysis_only` in Design and is excluded from every ordinary H3 reference loader. The sole exception is a runtime-only, Shot-local clip sent through the dedicated Relay source input. This prevents the legacy reference compiler from competing with the cast while allowing Character Swap to retain the real source performance, scene, framing, camera, timing and soundtrack.

## Media Contract

- `@V1`: analysis-only inside Design; at runtime Studio alone creates the Shot-local 24 fps Relay plate that preserves story, scene, action, camera, edit and soundtrack timing;
- `@P1`: the only required replacement identity; it may intentionally be reused for every detected V1 role;
- `@P2` to `@P9`: optional replacement identities chosen in the V1 Principal Role Bindings table.
- Additional loaded P images: optional later principals, activated only when V1 contains a real corresponding role.

### Illustrated Cast → Live-Action Cinema

When Studio's `ILLUSTRATED CAST → LIVE-ACTION CINEMA` option is enabled, a mapped P Picture identified by its visual evidence as cartoon, anime, comic, cel-shaded or illustrated is treated as a character-design identity rather than a literal rendering-medium plate. Preserve the character's recognisable apparent age, moustache or facial-hair design, hairstyle silhouette and colour, facial proportions, wardrobe design, colour blocking and signature accessories, but reconstruct physically plausible human anatomy, skin, hair and cloth inside V1's photographic lighting, lens softness, depth of field, motion blur, grain, shadows and occlusion. Never produce a pasted 2D head, sticker edge, ink outline, flat cel shading, paper cutout, oversized head or mixed illustrated/photographic body. Photographic P references are not restyled by this option. Turning the option off restores literal source-medium preservation.

Qwen assigns stable internal source IDs such as R1, R2 and R3. After analysis, Studio pauses and displays every appearance as its own chronological square face card, six cards per row. Each card contains only its own source interval and a crop taken from that exact interval; the internal R ID is not shown. Cards belonging to the same recurring person initially inherit the same suggested P Picture, but they are not locked or synchronized after creation. If there are more detected roles than loaded P Pictures, Studio automatically cycles through the available actor pool; with only P1 loaded, every card initially uses P1. The user may independently assign each time card to any loaded P Picture, reuse the same P across cards, or choose `V1 DEFAULT · Keep source actor`. The saved role-plus-scene ledger is authoritative for each Shot, speaker turn and Segment; never fall back to ordinal P1/P2 assumptions. A source role keeps its event responsibility, speaking turn and reaction function even when the user intentionally chooses a different P identity for a later appearance. When the user selects V1 Default, Studio materializes that appearance's square crop as a new controlled P identity reference. Other analysis thumbnails remain UI-only and must never be sent to H3.

When additional P images such as P5 are loaded, treat them as optional cast capacity. Automatically create a time-scoped `existing_media_uses` row only when a real V1 principal role is assigned to that P image; otherwise leave it unused. If a Shot requires an unloaded P identity, stop with a precise missing-Picture message instead of substituting or inventing a face.

## Analyse V1 Before Design

Analyse the complete V1 duration and build a chronological event ledger containing:

1. scene and Shot boundaries;
2. principal entrances, exits and role handoffs;
3. action setup, response, consequence and next-state continuity;
4. visible speaker and listener timing;
5. shot scale, angle, camera-motion purpose and cut rhythm;
6. defining architecture, props, weather, time, lighting and background-population function;
7. soundtrack timing, pauses, overlaps, music, ambience and Foley.

Use one analysis frame from every detected source scene, not only the opening scenes. Split long videos into up to three readable labelled storyboard sheets rather than shrinking every scene into one dense image. Before Director Design runs, send those sheets directly to the configured LM Studio vision model (`qwen3.8-uncensored-nvfp4-mtp` at the configured `/v1` endpoint) and require a schema-validated Qwen source-video director ledger. The ledger must contain one ordered row per detected source interval, stable source-role IDs, and one exact-panel tight square face crop for every role appearance, plus a clearest representative crop per principal, a location ledger, visible events, action handoffs, camera grammar and continuity constraints. Crop coordinates are relative to the selected individual panel, never the whole contact sheet. Design must wait for this ledger, show the chronological six-column face-binding grid, and use every row only after all roles have an assignment. Present the assigned P cast separately as a labelled cast contact sheet. BPM, VAD, Whisper, confidence, filenames and timestamps remain internal evidence and must never appear as visible or spoken content.

Storyboard pixels and the schema-validated Qwen ledger outrank ambiguous BLIP captions or transcript fragments. BLIP remains a low-level fallback and thumbnail aid; it is not the director-level story interpreter. A Qwen vision request may never silently fall back to text-only analysis. Infer a location change only when consecutive storyboard panels visibly establish different architecture. A uniform-like costume never proves that the scene moved to a laboratory, office, hospital or other new place. When evidence is uncertain, preserve the last clearly established location and describe only the visible action.

## Analysis Ledger and Dedicated Relay Plate

V1 must use `analysis_only` and must never occupy an ordinary H3 video-reference slot. Studio alone may materialize the current V1 Shot as the dedicated Relay source; Design must never insert that clip into `existing_media_uses` or a general-purpose reference slot.

Preserve V1 as the visual and performance plate while replacing only mapped identities:

- retain event order, role handoffs, action causality and scene purpose;
- retain the actual camera movement, such as reveal, follow, reaction, push, pan or transition;
- preserve V1's location, architectural topology, dominant background objects, object adjacency, depth layers, palette, practical-light direction, lens impression, framing, screen direction and blocking;
- H3 may redraw pixels while synthesising the replacement performer, but must not deliberately rebuild or substitute the background, extras, props, weather or lighting;
- no unselected source actor face, hair, body or wardrobe may survive; a role explicitly set to `V1 DEFAULT · Keep source actor` preserves only its materialized P face identity.

The supplied P images replace the mapped actors inside the retained source performance and environment; they do not trigger a newly invented world.

## Timeline and Segments

Use V1's exact playable duration. Begin at 0.000 seconds and end at its true endpoint. Do not loop, stretch, round, trim or extend it.

Create chronological non-overlapping Shots at real source scene or event boundaries. LoRA Preserve V1 keeps every source Shot isolated and lets H3 Relay process long Shots with its adaptive 124-frame windows and 18-frame generated history. Never carry a Relay window across a source hard cut. Each later Segment continues the preceding physical state and never replays an earlier event.

Time-scope and render only the roles belonging to each beat. Never load an absent P identity merely because it exists in the cast dictionary. Other people beyond the loaded cast capacity are anonymous non-speaking extras and must not inherit a P identity.

Write only the visible P identities into each Shot action. Never repeat the full cast dictionary inside every Shot, because Studio derives the Segment upload set from those Shot-local role mentions.

## Soundtrack

Before each H3 Segment is generated, Studio extracts V1's exact matching soundtrack window and supplies it as the sole standalone audio performance clock. The mapped P speaker follows its phoneme, jaw, lip-closure, breath, pause and overlap timing; visible listeners keep non-speaking mouths. The audio contributes no source visual identity. V1's untouched embedded soundtrack is restored during final assembly and remains the sole final master. Keep `text_layers` empty. Do not transcribe, translate, paraphrase, repeat or add dialogue, narration, lyrics or replacement music.

Plan mouth activity from analysed speaking turns: only the active mapped P-character speaks; listeners and extras keep natural non-speaking mouths. Never mention the V1 filename, UI or transcript inside render prompts; Studio supplies its visual Relay plate separately.

## Media Budget

Do not generate new P identities, replacement actors, pose references, reaction portraits, environment plates or per-Shot images. Already loaded optional P images may be used only for real source-role assignments. H3 retains the environment from the dedicated V1 Relay plate. `media_requests` remains empty.

## Delivery Gate

Return one schema-valid Director Design JSON and verify:

- exact V1 duration with continuous Shot coverage;
- every Qwen R role has one user-confirmed binding saved in `source_role_bindings`; duplicate P targets are permitted;
- V1 is retained only as `analysis_only` planning evidence;
- loaded P images are time-scoped H3 identity anchors, active only in the source-role intervals they replace, and are the only principals;
- the Relay result preserves source event order, cause-effect logic, performance, scene, camera and cut rhythm while replacing only mapped identities;
- no unselected source actor, unintended duplicate person, new speaking role, unrequested generated reference image or Text Layer exists;
- the final soundtrack is the untouched V1 master;
- in LoRA modes, each visible mapped role has exactly one sequential replacement pass in that Shot, with non-target people protected from identity bleed;
- the final Shot resolves the source-derived event and starts no new action.

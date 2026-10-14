---
name: source-video-cast-remake-h3
description: |
  Analyse a loaded V1 as a director blueprint, extract its principal-role order, events, scene vocabulary, camera grammar, edit rhythm and soundtrack timing, then restage the film with the loaded P-image cast pool. P1-P4 are the baseline cast and later loaded Pictures such as P5 are optional role capacity. V1 is analysis-only rather than an immutable pixel plate.
---

# Source Video Cast Reconstruction H3

Use this Special Skill with the bound Default H3 Prompt Writing Skill and only with source footage the user is authorized to transform.

## Media Contract

- `@V1`: analysis-only story, scene, action, camera, edit and soundtrack blueprint;
- `@P1`–`@P9`: replacement identities chosen explicitly in the V1 Principal Role Bindings table.
- Additional loaded P images: optional later principals, activated only when V1 contains a real corresponding role.

Qwen assigns stable internal source IDs such as R1, R2 and R3. After analysis, Studio pauses and displays every appearance as its own chronological square face card, six cards per row. Each card contains only its own source interval and a crop taken from that exact interval; the internal R ID is not shown. Cards belonging to the same recurring person initially inherit the same suggested P Picture, but they are not locked or synchronized after creation. The user may independently assign each time card to any loaded P Picture, reuse the same P across cards, or choose `Keep original V1 face`. The saved role-plus-scene ledger is authoritative for each Shot, speaker turn and Segment; never fall back to ordinal P1/P2 assumptions. A source role keeps its event responsibility, speaking turn and reaction function even when the user intentionally chooses a different P identity for a later appearance. When the user keeps an original V1 face, Studio materializes that appearance's square crop as a new P identity reference. Other analysis thumbnails remain UI-only and must never be sent to H3.

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

## Blueprint, Not Pixel Plate

V1 must use `analysis_only` and must never occupy an H3 video-reference slot. Do not ask H3 to preserve V1 pixels or replace a face inside the source frames. This avoids competition between the source actors and the loaded P cast.

Restage the same narrative and editorial functions as a new coherent production whose set remains recognisably close to V1:

- retain event order, role handoffs, action causality and scene purpose;
- retain the camera movement's function, such as reveal, follow, reaction, push, pan or transition;
- preserve V1's location type, architectural topology, dominant background objects, object adjacency, depth layers, palette, practical-light direction, lens impression, framing, screen direction and blocking;
- source pixels and source people must not be copied, but the set may not collapse into a generic substitute that merely serves the same story function;
- no unselected source actor face, hair, body or wardrobe may survive; a role explicitly set to `Keep original V1 face` preserves only its materialized P face identity.

This is the same successful principle used by beat-synced entrance films: reference the source's directing grammar, then let supplied P images perform inside a newly generated, internally consistent world.

## Timeline and Segments

Use V1's exact playable duration. Begin at 0.000 seconds and end at its true endpoint. Do not loop, stretch, round, trim or extend it.

Create chronological non-overlapping Shots at real source scene or event boundaries. Pack them into 5-to-15-second H3 render windows. Each later Segment continues the reconstructed world's last physical state and never replays an earlier event.

Time-scope and render only the roles belonging to each beat. Never load an absent P identity merely because it exists in the cast dictionary. Other people beyond the loaded cast capacity are anonymous non-speaking extras and must not inherit a P identity.

Write only the visible P identities into each Shot action. Never repeat the full cast dictionary inside every Shot, because Studio derives the Segment upload set from those Shot-local role mentions.

## Soundtrack

Before each H3 Segment is generated, Studio extracts V1's exact matching soundtrack window and supplies it as the sole standalone audio performance clock. The mapped P speaker follows its phoneme, jaw, lip-closure, breath, pause and overlap timing; visible listeners keep non-speaking mouths. The audio contributes no source visual identity. V1's untouched embedded soundtrack is restored during final assembly and remains the sole final master. Keep `text_layers` empty. Do not transcribe, translate, paraphrase, repeat or add dialogue, narration, lyrics or replacement music.

Plan mouth activity from analysed speaking turns: only the active mapped P-character speaks; listeners and extras keep natural non-speaking mouths. Because V1 is not a visual H3 reference, never mention its filename, UI or transcript inside render prompts.

## Media Budget

Do not generate new P identities, replacement actors, pose references, reaction portraits, environment plates or per-Shot images. Already loaded optional P images may be used only for real source-role assignments. H3 constructs the source-derived environments directly from the Shot descriptions. `media_requests` remains empty.

## Delivery Gate

Return one schema-valid Director Design JSON and verify:

- exact V1 duration with continuous Shot coverage;
- every Qwen R role has one user-confirmed binding saved in `source_role_bindings`; duplicate P targets are permitted;
- V1 is retained only as `analysis_only` planning evidence;
- loaded P images are time-scoped H3 identity anchors, active only in the source-role intervals they replace, and are the only principals;
- the rebuilt film preserves source event order, cause-effect logic, scene vocabulary, camera purpose and cut rhythm without copying source pixels;
- no unselected source actor, unintended duplicate person, new speaking role, unrequested generated reference image or Text Layer exists;
- the final soundtrack is the untouched V1 master;
- the final Shot resolves the source-derived event and starts no new action.

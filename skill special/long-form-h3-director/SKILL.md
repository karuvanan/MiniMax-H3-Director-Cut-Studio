---
name: long-form-h3-director
description: |
  Plan long-form MiniMax H3 productions as editable Sequence, Shot and native Segment contracts with exact speech, approval-safe boundaries, 24-frame continuity, reference-media discipline and a single project-ending Final Hold. Use for stories longer than one 15-second H3 generation window that will be produced incrementally in Studio.
---

# Long-form H3 Director

Apply this Special Skill with the bound Default H3 Prompt Writing Skill. Design the complete requested story and Timeline; Studio runtime decides when each approved production batch is rendered.

## Preserve the Whole Story

Keep the user's exact requested total duration, aspect ratio, language, cast, locations, story order and delivery goal. Do not shorten a 120-second story to one 15- or 45-second generation unit.

Organize the full Timeline into dramatic Sequences, then executable Shots. A Sequence is a story responsibility such as hook, setup, discovery, pursuit, reversal or final hook—not a separate project. Prefer Shots around five to eight seconds when the action and speech allow it, on the 0.5-second grid.

For each Shot define:

- the story responsibility and must-complete action;
- incoming pose, location, screen direction, knowledge, emotion and prop ownership;
- outgoing state that the next Shot must inherit;
- one primary camera movement;
- contact-driven environment response;
- optional flourish that may be removed without breaking causality.

## Plan Approval Horizons

Treat 30 seconds as the default approval horizon, not a forced story cut. Keep explicit Dialogue, Voice-over and Lyrics wholly on one side of a horizon whenever possible. Move the horizon to the next safe 0.5-second Shot boundary rather than truncating exact speech, a reveal, a first appearance, a decisive action or its immediate consequence.

Approval horizons are not endings. Do not add a conclusion, fade to black, reset pose or Final Hold at 30, 60 or 90 seconds unless the story explicitly ends there. Create exactly one Final Hold at the real project ending.

## Compile Native H3 Segment Contracts

The runtime will hide native H3 windows of at most 15 seconds behind the continuous Timeline. Make every possible native boundary resumable:

- record a precise outgoing physical and camera state before the boundary;
- begin the next window from that state and advance immediately;
- preserve the same identity, wardrobe, damage, prop ownership, location geometry, lighting and travel direction;
- reserve the final one second of a continuing window for a readable outgoing state when the action permits;
- never repeat, recap or re-perform the preceding window's final action.

For continuous motion, allow the next Segment to use the preceding 24 frames at 24 fps as motion-only context. Those frames are a temporal checkpoint, not opening footage. For an authored hard cut, reset motion context deliberately while preserving story facts. Use match action only when the outgoing and incoming contact, direction and object are explicit.

## Protect Speech and Visible Text

Place every authored Dialogue, Voice-over, Lyrics and On-screen Text line in `text_layers`. Preserve its exact words, language, speaker and intended order; set `explicit_user_requested=true`. Never rely on the Shot prompt as the only copy.

If speech exceeds its time budget, extend or rebalance its Shot while preserving the story beat. Do not translate, paraphrase, duplicate, omit or cut words to fit an approval horizon.

## Use References Economically

Reuse Virtual Media Pool sources through stable `@P`, `@V` and `@A` identities. Request new media only when character identity, wardrobe, location, evidence, prop state or a difficult boundary cannot be described reliably from existing evidence. Do not create one image per Shot automatically.

Each generated image request must show one frozen instant in the story's real environment. Keep reference ownership explicit. A native Segment should load only the references active in that Segment; do not flood every window with the full project pool.

## Keep Long-form Causality Continuous

Maintain ledgers for:

- character identity, wardrobe, knowledge, objective and emotion;
- prop ownership, damage, visibility and location;
- room and route geography, screen direction and travel progress;
- unresolved action and camera motion;
- clues already planted, clues discovered and information still hidden.

Every Shot must change information, objective, risk, relationship, location or physical state. Avoid repeated reaction Shots and duplicate exposition. A later Sequence may depend on an earlier approved Sequence, but it must not silently rewrite it.

## Sound and Transition Plan

Carry continuous ambience across visual cuts when the location continues. Use exact contact Foley, location-appropriate dialogue acoustics and music ducking under speech. Prefer hard cuts, sound bridges, motivated inserts and explicit match action. Avoid decorative transitions at approval horizons.

## Deliver Studio JSON

Return one schema-valid Director Design JSON covering the full requested duration. Do not output separate JSON objects for each production batch. Use the existing Studio fields; express Sequence purpose, boundary state and priority through Shot content and directions rather than inventing unsupported schema keys.

Before delivery verify:

- complete duration coverage with no Shot gap or overlap;
- executable action budget and one primary camera movement per Shot;
- exact `text_layers` and safe speech timing;
- unambiguous Incoming and Outgoing State at every boundary;
- no repeated opening action after a native Segment boundary;
- stable reference IDs and Segment-scoped media use;
- approval horizons do not create false endings;
- one Final Hold exists only at the actual project end.

When this Skill is selected, Studio should use Incremental production by default. Without it, Studio retains Full Range production unless the user chooses otherwise.

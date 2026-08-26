# Changelog

Every user-visible correction receives an application version and a dated entry in this file. Application versions follow Semantic Versioning pre-release notation. The `.h3director.json` project-format version is maintained separately and changes only when the saved schema changes.

## [0.2.4-alpha.5] - 2026-08-26

### Added

- Added `test_standard_pipeline_regressions.py` as a four-part release gate for sparse P/V/A mapping, post-Design Timeline reconciliation, V/A track-type integrity and native 15-second continuity boundaries.
- The Design/Timeline gate also verifies that Shot-reference reassociation remains correct through Undo and Redo.

### Fixed

- Timeline media edits now immediately run Prompt Reconcile, so moving, trimming, changing track or editing a Clip Prompt after Design Apply updates the Creative Brief and generated H3 Prompt without reopening Design.
- Existing AI Semantic reference directions now follow every occurrence of their Media Pool source to the currently overlapping Shot and are removed from Shots that no longer overlap it.
- Runtime track lookup now validates media kind as well as `track_id`; Picture/Video cannot survive on an Audio track, and Audio cannot survive on a Visual track even when an old/corrupt project stores mismatched track data.

### Verification

- The four mandatory release-gate scenarios passed.
- The complete bundled test suite passed: `209` tests.
- The Director Project format remains version `16`; no saved-project migration is required.

## [0.2.4-alpha.4] - 2026-08-26

### Added

- Added an H3 action-generation budget shared by AI Design, manual Shot editing, AI Semantic Enrichment and final Prompt compilation: at most three must-complete physical beats, two required contact consequences and two optional flourishes per five seconds.
- Added structured Shot fields for `continuity_state` and `optional_flourish`, plus deterministic `h3_executable_action` and `action_budget` metadata with visible Design Summary warnings.
- Added English and Chinese generation-budget rules to `wuxia-blade-film`, including native 15-second boundary reservations and an explicit priority ladder.

### Changed

- `subject_action` now represents only the must-complete physical core. Contact-driven consequences remain in `environment_response`; dispensable particles, cloth motion, secondary feints and ornamental camera work are compiled as optional detail.
- Over-budget Shots are priority-compressed: secondary/decorative beats are demoted before the core action can be delayed or replayed. The authored action is retained in budget metadata for review.
- AI Design now rejects overlapping camera Shot Blocks, repairs blank constraints with continuity guardrails, fills legacy continuity state safely and assigns Shot IDs after chronological sorting.
- BLIP refinement and replacement-media Shot adaptations preserve the same core/state/optional hierarchy instead of expanding the action list again.

### Verification

- Added regressions for the new Design JSON fields, legacy-plan defaults, blank-constraint repair, causal setup merging, required-response limits, five-second overload compression, overlap rejection and Timeline Prompt hierarchy output.
- Validated the English and Chinese `wuxia-blade-film` Skill package.
- `205` automated tests passed with the bundled Python environment.
- Increased the Director Project format to `16` because saved Shot cues now include action-priority and continuity fields; older projects load with backward-compatible defaults.

## [0.2.4-alpha.3] - 2026-08-26

### Fixed

- Compacted every active Picture, Video, paired-video-audio and standalone Audio connection into contiguous request-local H3 input slots, so prompt labels and executable ComfyUI fields cannot diverge when Media Pool slots are sparse.
- Kept permanent Media Pool identities such as P5/V2/A3 separate from request-local H3 ordinals, preserving stable Timeline editing, repeated Clip Instances and saved-project references.
- Appended hidden 24-frame continuity video after ordinary active video references and added a hard collision guard that refuses to overwrite Timeline media.
- Removed the false `No previous rendered frame is supplied` sentence whenever the render pipeline may attach previous-segment motion context.
- Improved boundary-state extraction to retain the prior Shot's actual terminal pose, screen positions and camera direction instead of generic text such as `This is the boundary for Part 3`.
- Filled blank structured Shot labels with their stable Shot IDs instead of emitting empty names.

### Changed

- Increased the Smart Render policy to `7`, intentionally invalidating older cached segments compiled with sparse reference bindings or contradictory continuity text.

### Verification

- Added the One Leaf Kill P1/P2/P3/P5 third-segment regression: P5 is described as `<Picture 4>` and is now physically connected to `ref_images.ref_image_3`.
- Added mixed Picture/Video/Audio sparse-slot coverage, hidden-video append ordering, runtime collision protection and concrete boundary-state tests.
- Recompiled the real `one_leaf_kill_20260826_113835_147104` project and confirmed four contiguous image inputs, `<Picture 4>` for P5, `<Video 1>` for the 24-frame context and no contradictory no-frame sentence.
- `199` automated tests passed with the bundled Python environment.
- The Director Project format remains version `15`; existing projects can be opened without migration.

## [0.2.4-alpha.2] - 2026-08-26

### Added

- Rewrote `example/one_leaf_kill_45s_design_requirement.txt` as a Design-ready V2 with three aligned native 15-second phases and nine exact Shot Blocks.
- Added explicit character, weapon, consumable/prop and spatial ledgers; four-dart accounting; physically tracked chain and hat states; exact 15s/30s exit states; first-new-action instructions; and no-replay boundary rules.

### Changed

- Expanded both `wuxia-blade-film/SKILL.md` and `SKILL.cn.md` with clean Design-handoff guidance, native H3 boundary contracts, spatial travel paths, unambiguous weapon verbs and delayed-prop lifetime rules.
- Updated the Skill UI metadata to reflect multi-segment continuity planning.

### Verification

- Validated the updated Skill package with `quick_validate.py`.
- Verified that the V2 Requirement covers exactly 45.00 seconds as `0–15 / 15–30 / 30–45`, defines exactly nine non-overlapping Shot ranges, and contains explicit no-replay rules at both native boundaries.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.2.4-alpha.1] - 2026-08-26

### Added

- Added the complete Chinese companion document `skill special/wuxia-blade-film/SKILL.cn.md`.

### Changed

- Small optimizations now increment only the suffix after `alpha`, leaving the three-part base version unchanged.

### Verification

- Verified the Chinese Skill companion covers the complete English workflow, action continuity, camera, physical qinggong, reference planning and quality gate sections.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.2.4-alpha] - 2026-08-26

### Documentation

- Added the public MiniMax H3 Director Cut Studio tutorial link to the README quick-start section.
- Converted application releases to the `v0.2.4-alpha` numbering style, with each numeric position limited to `0–9` and carrying into the position on its left.

### Verification

- Verified that the README displays the tutorial as a direct clickable link.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.2.3-alpha] - 2026-08-26

### Changed

- Changed `wuxia-blade-film` to the standard `Default + Special` binding requested for production use.
- AI Design now receives both `h3-prompt-writing` with its Ref2VA guide and the scene-specific wuxia blade-action rules whenever this Special Skill is selected.
- Kept the optional standalone marker mechanism available for future Special Skills, but `wuxia-blade-film` no longer declares it.

### Verification

- Updated the Skill loader and Director Design-context regressions to verify the Default and wuxia Special instructions are both bound.
- `196` automated tests passed with the bundled Python environment.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.2.2-alpha] - 2026-08-26

### Added

- Added the standalone `wuxia-blade-film` Special Skill for fast, physically grounded blade combat, weapon-driven causality, readable signature techniques, kinetic camera loss/reacquisition, synchronized environmental impacts and hard diegetic sound.
- Added a Design-ready 45-second, nine-Shot adaptation of 《一叶杀》 at `example/one_leaf_kill_45s_design_requirement.txt`.
- Added per-Skill `standalone` binding metadata through the `<!-- h3-studio-binding: standalone -->` marker.

### Changed

- When a standalone Special Skill is selected, AI Design receives only that Special Skill; `h3-prompt-writing` and its Ref2VA guide are intentionally omitted from the Design context.
- Updated H3 Prompt Studio binding labels and source preview so standalone Special Skills are no longer presented as `Default + Special`.
- Existing Special Skills remain `Default + Special`, and `None` remains Default-only.

### Verification

- Added regressions for standalone Skill discovery, AI system-prompt isolation and Director Design context isolation.
- `196` automated tests passed with the bundled Python environment.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.2.1-alpha] - 2026-08-26

### Fixed

- Fixed the Studio UI freezing when AI ENRICH was started consecutively for three or more Media Pool items.
- Removed all worker stdin writes and flushes from the Qt main thread. Large BLIP evidence, semantic schemas and LM Studio prompts now enter an in-memory queue immediately and are drained by a dedicated background writer thread.
- Applied the non-blocking queue to every persistent JSON worker, including media preparation, multi-region/video BLIP, audio analysis and AI Semantic Enrichment, so a busy child process can apply Windows pipe backpressure without freezing selection, scrolling or further clicks.
- Preserved ready-gating, FIFO request order, crash isolation, pending-job cancellation and worker error logging.

### Verification

- Added a Windows-pipe backpressure regression worker that intentionally refuses to read stdin for one second while the Studio queues three approximately 810 KB requests. All three UI-side enqueue calls return immediately and the worker later receives them in exact order.
- Re-ran multi-region image AI Enrich, video BLIP/audio waiting, manual LM Studio semantic enrichment and worker startup/failure tests.
- `194` automated tests passed with the bundled Python environment.
- The Director Project format remains version `15`.

## [0.2.0-alpha] - 2026-08-26

### Fixed

- Fixed AI Design Apply/Undo/Redo leaving the Track Header on the original V3/V2/V1 model after the Timeline had dynamically created V4/V5/V6. Picture clips remained correctly assigned to visual tracks internally but appeared beside A1/A2/A3 labels because the two panes displayed different track lists.
- Added the complete dynamic Track list to the AI Design workspace command state, so Undo restores the earlier track model and Redo restores all Design-created V/A tracks together with their media, text and Shot assignments.
- Rebuilt and resynchronized the fixed Track Header pane whenever an AI Design workspace state is restored.

### Verification

- Reloaded `bangkok_to_meiktila_the_midnight_escape_20260826_080038_515906` and confirmed that both panes expose `V6, V5, V4, V3, V2, V1, A1, A2, A3`; all six placed Picture assets resolve to tracks whose type is `visual`.
- Added an AI Design dynamic-track Apply/Undo/Redo regression test.
- `193` automated tests passed with the bundled Python environment.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.1.9-alpha] - 2026-08-26

### Verified

- Added an explicit end-to-end reference-mapping matrix for a single native 1.00-15.00s render, a 14.00-20.00s partial render crossing a reference boundary, and a hidden two-window 1.00-30.00s Smart Render.
- Verified that the second long-form window reserves `<Video 1>` for exactly 24 preceding motion frames while active Timeline video references and synchronized/standalone audio references retain their correct effective ordinals.
- Verified local edits independently in the first, middle and final Segment, plus an authored 30-second Timeline split into three ten-second Shot render units; only the edited unit's content fingerprint changes.
- Verified delete/re-add, movement from an old Segment into a new Segment, movement between compatible visible Tracks, and Track visibility filtering without changing the permanent Media Pool identity.
- Verified two non-contiguous uses of the same physical Media Pool source on one Track (1.00-4.00s and 25.00-30.00s): each window receives one correct H3 connection and its own Clip Prompt, without duplicate loader execution or ordinal drift.
- Re-ran project-format-15 save/restore, mixed Picture/Video/Audio compilation, collision-safe ComfyUI uploads, local cache reuse, 24-frame continuity generation and final Smart Render assembly as part of the complete suite.

### Verification

- `192` automated tests passed with the bundled Python environment.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.1.8-alpha] - 2026-08-26

### Fixed

- Re-audited the complete workflow from API discovery and Media Pool assignment through AI Design, Timeline Prompt Reconcile, native/Smart Render compilation, ComfyUI upload, segment assembly, generated MP4 archiving and Director Project restore.
- Applied Visual Track visibility and Audio Track Mute/Solo/enable state before compiling both the Prompt ordinals and H3 input connections for native renders and Active API exports; the two sides can no longer disagree after a track is disabled.
- Recompiled every native render directly from the filtered Timeline state so a stale visible Prompt cannot leak an earlier reference map into the queued workflow.
- Converted partial native work areas to segment-local Shot timestamps, preventing a 15.00-23.00s Timeline repair from sending global 16.00-22.00s timestamps into an eight-second H3 request.
- Assigned a deterministic collision-safe ComfyUI upload name to every physical image/video/audio loader and patched each compiled workflow accordingly. Different local files with the same basename can no longer overwrite or impersonate one another during `overwrite=true` uploads.
- Added structured upload manifests to both native and Smart Render workers while retaining backward compatibility with legacy string-only jobs.

### Verification

- Added an end-to-end 30-second Smart Render simulation that validates Segment Prompt tags, active H3 connections, 24-frame continuity Video numbering, paired Video Audio numbering, standalone Audio offset and loader upload names together.
- Added native hidden/Mute mapping, partial-work-area local-time and duplicate-basename upload regression tests.
- `182` automated tests passed with the bundled Python environment.

## [0.1.7-alpha] - 2026-08-26

### Fixed

- Completed a repository-wide Python mapping audit covering Picture, Video and Audio references across Media Pool, repeated Timeline Clip Instances, AI Design, Timeline Prompt Reconcile, classic H3 Studio, native generation, Smart Render and Active API export.
- Canonicalized internally generated bare media mentions such as `P3`, `V2` and `A1` into stable `@P3`, `@V2` and `@A1` references before per-Segment compilation, without rewriting literal product/model names globally.
- Prevented classic H3 Studio AI output and Director Active API exports from reusing a prompt compiled for a different work-area reference map.
- Deduplicated repeated Timeline instances by their physical source node and binding even when an editor instance carries its own node ID.
- Made enabled soundtracks from reference videos explicit in `subject_definitions` and `retention_policy`, and correctly offset standalone `<Audio N>` ordinals behind those synchronized video-audio signals.
- Removed request-local H3 angle-bracket tags from the AI Design Media Pool inventory so Design can author only permanent Media Pool IDs.

### Verification

- All `36` project Python files were statically inspected for reference-number construction, prompt compilation and workflow-binding paths.
- `178` automated tests passed with the bundled Python environment, including a mixed P4/P7/V2/A3 Segment test and inactive-reference anti-alias checks.

## [0.1.6-alpha] - 2026-08-26

### Fixed

- Separated permanent Studio media IDs (`@P4`, `@V2`, `@A1`) from MiniMax H3's request-local `<Picture N>`, `<Video N>` and `<Audio N>` ordinals.
- Remapped authored stable IDs and legacy angle-bracket references only when compiling each active render Segment, including Shot fields, Creative Brief, transition/marker instructions and Clip Prompts.
- Prevented inactive or unavailable legacy references from silently aliasing another connected asset after H3 renumbering; they now compile to an explicit non-reference diagnostic instead.
- Kept AI Semantic Enrichment fingerprints attached to the physical Media Pool source when that source receives a different effective ordinal or is used through a repeated Timeline Clip Instance.
- Updated the Director Cut and classic H3 Studio UI shortcuts to derive numbering from permanent physical bindings rather than mutable prompt tags.

### Changed

- AI Design now writes stable `@P/@V/@A` references in authored JSON and reserves angle-bracket H3 tags for the final per-Segment compiler.

### Verification

- `172` automated tests passed with the bundled Python environment.

## [0.1.5-alpha] - 2026-08-26

### Added

- Added independent Timeline Clip Instances so one Media Pool source can be reused in any number of non-contiguous ranges, tracks or overlapping layers.
- Added per-instance timing, activation, source trim, playback speed, fades, transitions, monitor visibility and Clip Prompt persistence with Undo/Redo.
- Allowed AI Design JSON to route the same `P`/`V`/`A` Media Pool ID into multiple time-scoped `existing_media_uses` rows.

### Changed

- Kept recognition and AI Semantic Enrichment source-owned and automatically shared across all repeated instances.
- Deduplicated repeated instances when assigning effective MiniMax H3 reference ordinals, uploading media and compiling subject definitions, while retaining every time range and per-instance direction in the generated prompt.
- Updated Program Monitor video/audio player keys and Smart Render fingerprints so repeated clips remain independently seekable and locally editable.
- Raised the Director Project format to version `15`; version 14 and older projects continue loading with their original media placements as first-use clips.

### Verification

- `168` automated tests passed with the bundled Python environment.

## [0.1.4-alpha] - 2026-08-25

### Fixed

- Resynchronized the Track Header vertical offset after project loading, dynamic V-track creation and header rebuilding. Picture clips with valid V-track IDs can no longer appear visually aligned with A1/A2/A3 labels because the two panes retained different scroll positions.

### Verification

- `162` automated tests passed with the bundled Python environment.

## [0.1.3-alpha] - 2026-08-25

### Fixed

- Gave the Timeline Tools palette a DPI-aware minimum width based on its longest button and scrollbar, so every icon keeps its visible Selection/Hand/Razor/Shot/Type/Prompt/Transition/Marker label even when the splitter is dragged left.

### Verification

- `161` automated tests passed with the bundled Python environment.

## [0.1.2-alpha] - 2026-08-25

### Added

- Allowed AI Design plans to create and populate editorial tracks beyond V3/A3 (up to V16/A16), including separate visual title and dialogue/voice-over/lyrics lanes.
- Added automatic cross-segment motion context using exactly the preceding 24 frames at 24 fps, without carrying prior audio.
- Added strict single-colour, edge-connected background detection and non-destructive transparent PNG derivatives for Media Pool and Design-generated images.

### Changed

- Reserved one of the three physical H3 video reference inputs for hidden continuity when possible; if all are occupied, the least-specific Auto reference is released for that segment while force-active references remain untouched.
- Raised the Smart Render policy version to `6`, invalidating older segment manifests whose continuity assumptions are no longer safe to reuse.

### Verification

- `161` automated tests passed with the bundled Python environment.

## [0.1.1-alpha] - 2026-08-25

### Added

- Added the machine-readable `VERSION` file and shared `version_info.py` loader.
- Displayed the application version in the main Studio title and Qt application metadata.
- Saved `application_version` beside the independent project-format `version` in every Director Project JSON.
- Added repository-wide line-ending and binary-file rules through `.gitattributes`.
- Documented versioning, runtime downloads, Timeline Prompt Reconcile, semantic Shot adaptation and the current 156-test baseline.

### Fixed

- Corrected a broken Design system-prompt sentence that previously produced `When a Treat each asset...` and weakened Media Pool reuse instructions.
- Updated public README examples to avoid development-machine LAN addresses and accurately describe the Z-Image workflow without RTX upscaling.

### Verification

- `156` automated tests passed with the bundled Python environment.

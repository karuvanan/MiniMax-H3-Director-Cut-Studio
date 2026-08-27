# Changelog

Every user-visible correction receives an application version and a dated entry in this file. Application versions follow Semantic Versioning pre-release notation. The `.h3director.json` project-format version is maintained separately and changes only when the saved schema changes.

## [0.2.5-alpha.4] - 2026-08-27

### Added

- Added `Auto`, `CUDA preferred` and `CPU only` BLIP inference choices to the main Settings page and the persistent `H3_BLIP_DEVICE` environment setting.
- Auto is the safe first-run default: it loads BLIP on CPU, verifies a real CUDA operation, moves the model to CUDA when supported, and retains the existing same-job CPU fallback for any later inference failure.

### Changed

- Image BLIP analysis now runs one purposeful observation per crop instead of three repetitive conditional prompts per crop.
- Raw Recognition now removes echoed prompt prefixes, merges captions that add no meaningful visual evidence, replaces older BLIP blocks on re-analysis, and reports the inference device once in one compact summary.

### Verification

- Added deterministic tests for repeated prompt cleanup, semantic deduplication, preservation of genuinely new region evidence, legacy-output replacement, and the safe Auto settings default.
- Confirmed the actual local BLIP model loads CPU-first in Auto mode, selects CUDA after its runtime probe, and completes an image caption on CUDA.
- The complete bundled test suite passed: `241` tests.

## [0.2.5-alpha.3] - 2026-08-27

### Fixed

- BLIP now detects incompatible CUDA runtime／GPU-kernel failures during both model startup and individual image inference.
- The exact pending BLIP job is automatically retried with a freshly loaded CPU model instead of returning a permanent `no kernel image is available for execution on the device` error.
- Studio remembers an internal BLIP CUDA fallback for the current session, so later worker restarts begin directly on CPU.
- The legacy one-shot BLIP worker now follows the same safe CPU fallback policy.

### Documentation

- Added cross-computer deployment guidance explaining why the destination driver's CUDA version does not replace the CUDA runtime bundled with its copied PyTorch environment.

### Verification

- Added regression coverage for CUDA architecture errors and confirmed unrelated media errors do not trigger a misleading CPU retry.
- The complete bundled test suite passed: `236` tests.

## [0.2.5-alpha.2] - 2026-08-27

### Fixed

- Explicit Design duration now comes deterministically from phrases such as `30秒的视频`／`2分钟的视频` and the latest authored timecode, rather than the current workspace Timeline duration.
- Added an immutable Duration Contract to LM planning; an initial mismatch receives one automatic full-plan retry, while a refinement mismatch retains the validated first plan.
- Normalize, Load JSON, Apply and Run now reject plans that condense or stretch an explicitly requested duration.
- Timed Dialogue, Voice-over, Lyrics and On-screen Text now use the user-authored duration when preserving and validating cues, preventing all text after an incorrect LM duration from being silently clipped.

### Verification

- Added the exact 30-second four-dialogue regression and a 12-second workspace precedence regression.
- Confirmed explicit 30-second, 2-minute, final-timecode-only and 45-second Chinese duration inference while rejecting age text such as `39岁` as a duration.
- The complete bundled test suite passed: `235` tests.

## [0.2.5-alpha.1] - 2026-08-27

### Documentation

- Added a Common Issues explanation for action／boundary image requests that incorrectly use neutral, blank or studio backgrounds.
- Clarified that `Image media request N` is the ordinal image request in Design JSON and is not necessarily Media Pool `PN`.
- Added incorrect and corrected Prompt examples, the global Identity Reference exception and exact repair steps.

### Verification

- Confirmed README version and complete-suite count now match `v0.2.5-alpha.1` and the latest `233`-test result.

## [0.2.4-alpha.9.6] - 2026-08-27

### Added

- Added a persistent `Dialogue Text Layer TTS` selector to the main Settings page with `Edge TTS` and `VoxCPM2 Local` choices.
- Added the first native VoxCPM2 adapter to `tts_service.py`: local-only model loading, deterministic per-Speaker Voice Design, exact Timeline WAV composition and provider metadata in the generated sidecar.

### Changed

- VoxCPM2 is loaded once for all authored lines in one Design Apply job. The crash-isolated worker releases the model and CUDA cache after composition.
- Auto device selection uses safe CPU mode below 8 GB VRAM instead of attempting a likely GPU out-of-memory load.
- A selected VoxCPM2 failure now stops Apply explicitly instead of silently falling back to Edge; Edge retains its existing Windows SAPI fallback.

### Verification

- Added Settings persistence, invalid-provider, provider-selection and deterministic VoxCPM2 voice-control regressions.
- Confirmed the cached `openbmb/VoxCPM2` checkpoint loads through the bundled runtime in safe CPU mode; the complete waveform/compositor path is covered by an isolated provider integration test.
- The complete bundled test suite passed: `233` tests.

## [0.2.4-alpha.9.5] - 2026-08-27

### Added

- Added `run_voxcpm2_webui.bat`, which always launches VoxCPM2 through the bundled `ai_libraries_common/python_env` and defaults to the local-only `127.0.0.1:8088` endpoint.

### Fixed

- Documented that `app -port 8088` invokes the wrong Python association and uses an invalid single-dash argument; the supported direct form is `python app.py --port 8088`.

### Verification

- Confirmed `funasr 1.4.3`, `voxcpm 2.0.0` and the VoxCPM2 `app.py` argument parser through the bundled runtime.

## [0.2.4-alpha.9.4] - 2026-08-26

### Fixed

- AI Design no longer treats an editorial `A1` track chosen for authored Dialogue, Voice-over or Lyrics as proof that a real Media Pool `@A1` asset exists.
- Deterministically extracted timed text is now restored before media-plan repair, allowing an empty hallucinated A1 speech reuse to be removed and replaced later by the real `authored_speech_tts` request during Apply.
- Missing non-TTS Audio references remain strict validation errors, so the repair cannot hide a genuinely missing ambience, music or supplied-audio dependency.

### Verification

- Added regressions for the exact empty-A1 dialogue failure and for preservation of strict missing-audio validation.
- The complete bundled test suite passed: `229` tests.

## [0.2.4-alpha.9.3] - 2026-08-26

### Added

- Installed the complete official VoxCPM2 source dependency set into the bundled `ai_libraries_common/python_env`, including audio I/O, text normalization, ModelScope, FunASR, Gradio and voice-cloning support libraries.
- Installed the local `ai_libraries_common/VoxCPM-main` checkout as editable package `voxcpm 2.0.0`; the ZIP checkout receives a local build-version override because it does not contain Git metadata for `setuptools-scm`.

### Changed

- Replaced the unmatched `torch 2.12.1+cu126` runtime with the official ABI-matched `torch 2.11.0+cu126` and `torchaudio 2.11.0+cu126` pair. CUDA 12.6 remains active.

### Verification

- Verified imports for `voxcpm`, `torchcodec`, `torchaudio`, `librosa`, `soundfile`, `einops`, `pydantic`, `gradio`, `funasr`, `modelscope` and `wetext`.
- Verified that BLIP classes still import after the Torch change, CUDA remains available, and `pip check` reports no broken requirements.
- VoxCPM2 model weights are not part of this dependency installation; Edge TTS remains the active Studio engine until the local VoxCPM2 adapter is enabled.

## [0.2.4-alpha.9.2] - 2026-08-26

### Added

- Added a deterministic, timecode-aware Design parser for exact `Dialogue`, `普通话对白`, `旁白`, `Voice-over`, `Lyrics` and `On-screen Text`; these cues are created with `explicit_user_requested=true` before LM planning.
- Added an authored-text contract saved in Director projects. Apply and Preview / Run now stop with a precise error if explicit timed words have been lost or silently changed.
- Added asynchronous Mandarin neural TTS through `edge-tts 7.2.7`, with S1/S2 Mandarin voices, Windows SAPI fallback, exact Timeline placement, long-line tempo fitting, WAV composition and automatic A Track loading.
- Added hidden-segment TTS window extraction, so Smart Long Render and local Segment re-renders receive the correct part of the full authored speech instead of replaying the first line.

### Fixed

- LM image-caption Refinement can no longer erase or paraphrase Dialogue, Voice-over, Lyrics, On-screen Text or an explicitly requested theme from the first Design Plan.
- H3 prompts no longer claim that supplied audio exists when no valid Audio reference is active. Without Audio they request exact native-language speech; with Audio they identify the actual request-local `<Audio N>` and require precise phoneme/lip synchronization.
- AI Design no longer commits the old silent audio placeholder when explicit speech synthesis fails; Apply is stopped and the failure is shown to the user.

### Verification

- Added deterministic text-role, exact-word protection, Apply/Run contract, audio-conditional prompt, TTS tempo-chain and A-slot reservation regressions.
- Confirmed a real `zh-CN-XiaoxiaoNeural` Mandarin WAV through the bundled runtime and FFmpeg compositor.
- The complete bundled test suite passed: `227` tests.
- Director Project format is now version `17`; older projects remain loadable, and newly saved projects retain the authored-text contract.

## [0.2.4-alpha.9.1] - 2026-08-26

### Added

- Added a mandatory input-repair compiler to the English and Chinese `wuxia-blade-film` Skill. User-supplied Shot wording is now treated as creative intent rather than an immutable execution contract.
- Added preflight detection for missing or uneven timing, overloaded five-second windows, conflicting slow/fast instructions, repeated bullet-time, qi used as a movement shortcut, unsupported flight, full 360-degree combat orbits, competing camera programs and multi-phase still-reference prompts.
- Added deterministic rewrite rules that translate those failure patterns into exact 0.5-second ranges, contact-driven environmental reactions, visible launch and landing mechanics, 60–120-degree orientation-preserving coverage, two or three readable contacts and one primary camera movement per Shot.

### Changed

- Action-heavy 45-second inputs now default to nine five-second Shots across three native 15-second movements when the source timing is unusable; the user's story goal, identities, required weapons, key outcome and intensity remain protected while raw Shot count and unrenderable decoration may be restructured.
- The Skill now performs a final clause-level compiler pass and must simplify or split the causal chain until mandatory actions are unlikely to be demoted and the normalized Design is expected to produce zero action-budget warnings.
- Updated the Skill picker metadata so its default prompt explicitly requests diagnosis and repair before H3 choreography.

### Verification

- Added English/Chinese parity coverage for the new repair stage, timing fallback, 360-degree rewrite, camera limit and zero-warning compiler target.
- Validated the updated Skill package in UTF-8 mode.
- The complete bundled test suite passed: `219` tests.
- The Director Project format remains version `16`; no saved-project migration is required.

## [0.2.4-alpha.9] - 2026-08-26

### Added

- Added `example/one_leaf_kill_45s_design_requirement_v3.txt` and the directly loadable `example/one_leaf_kill_45s_design_plan_v3.json`, organized as nine exact 5-second Shots across three native 15-second render segments.
- Added stable character, weapon, projectile, hat, wound and footing ledgers, plus explicit 15-second boundary states so separately generated segments continue the same physical action without replay.
- Added one-frozen-instant reference-image rules and per-Shot reference budgets to prevent multi-action collages from becoming contradictory H3 guidance.

### Changed

- Replaced visible qi, magical aura, unsupported hovering, long aerial freezes and full 360-degree hero orbits with contact-driven airflow, grounded wall steps, gravity, tile breakage and a short orientation-preserving orbit.
- Limited each Shot to at most three mandatory physical beats and moved leaves, sparks, dust, cloth motion and secondary camera decoration outside the core action budget.

### Verification

- Added regressions for the V3 Shot count, exact timing, native-boundary continuity, projectile direction, duplication guard, frozen-reference rule and direct Design JSON normalization.
- Validated the updated Skill package in UTF-8 mode.
- The complete bundled test suite passed: `218` tests.
- The Director Project format remains version `16`; no saved-project migration is required.

## [0.2.4-alpha.8] - 2026-08-26

### Added

- Expanded `wuxia-blade-film` with limb, weapon-geometry, attachment, cumulative-damage and footing ledgers for asymmetric survival combat.
- Added an irreversible combat-degradation curve: unequal threat, committed attack, injury adaptation, feral collapse and visibly costly resolution.
- Added causal fragmented-editing rules that preserve one orientation anchor, reveal the physical result immediately after impact occlusion and prohibit random camera shake as a substitute for speed.

### Fixed

- A one-armed fighter can no longer regenerate a hand, use a phantom grip, perform a two-handed guard or gain unexplained balance from an absent limb.
- A broken blade with no usable point can no longer perform a clean thrust or impalement; its permitted actions are constrained to its fixed geometry unless a stable jagged point is explicitly established.
- Chain/rope actions must now preserve origin, attachment point, controlling hand, tension state and visible release or retraction instead of behaving as a duplicated or intangible weapon.
- Damage, damaged armor, breath loss, weakened footing, blood, mud and grip failure must persist through subsequent Shots and native 15-second boundaries.

### Verification

- Added an English/Chinese parity regression for the new limb, blade-geometry, attachment, damage, footing and feral-collapse rules.
- Validated the updated Skill package in UTF-8 mode.
- The complete bundled test suite passed: `216` tests.
- The Director Project format remains version `16`; no saved-project migration is required.

## [0.2.4-alpha.7] - 2026-08-26

### Added

- Expanded the English and Chinese `wuxia-blade-film` Skill with a renderable brutal-blade grammar: broken-blade inner-circle entry, tension-axis rotation, adhesive short combinations, grounded twin-blade aerial pressure, the decisive speed paradox and H3 timing translation.
- Added explicit direction for dense flurries, range asymmetry, gravity-driven attacks, recovery vulnerability, projectile ownership and close handheld impact coverage without copying game stats into generation prompts.

### Fixed

- Action-budget compression now resolves actor pronouns before selecting mandatory beats. An Assassin's throw, low slide or escape can no longer be silently reassigned to the General when intervening clauses are demoted.
- Automatically recovered or coverage-floor Z-Image requests now describe one frozen outgoing physical state instead of copying a whole multi-action Shot into one still.
- Legacy internal `auto_image_sN` requests are upgraded to the same atomic still format when an older Design JSON is validated or applied.
- Generated action-state references explicitly forbid temporal montages, repeated body positions and duplicate fighters, reducing contradictory pose anchors and character multiplication.

### Changed

- AI Design now requires every multi-character action clause to repeat the explicit role before its verb and weapon; cross-clause `he`, `his`, `she` and `they` are rejected as unsafe choreography notation.
- Action-state image planning now separates identity/ownership requirements, one frozen pose state and story location instead of treating a static reference as a miniature action sequence.

### Verification

- Re-examined the 45-second `one_leaf_kill_20260826_163317_529371` preview at one and three frames per second across all three native segments.
- Validated the updated Skill package in UTF-8 mode.
- The complete bundled test suite passed: `215` tests.
- The Director Project format remains version `16`; no saved-project migration is required.

## [0.2.4-alpha.6] - 2026-08-26

### Fixed

- AI Design no longer rejects Apply when the model incorrectly lists an empty Media Pool slot such as P1 under `existing_media_uses`; the row is repaired into a Z-Image request and keeps its intended physical Picture slot.
- AI Design now enforces a bounded visual-reference coverage floor when LM Studio returns too few or zero image requests: approximately one useful Picture state per five seconds, never more than one per Shot and never beyond the available Picture capacity.
- Z-Image generation now retries each requested Picture once after a transient ComfyUI failure before falling back to a placeholder, reducing partially populated or image-free Design results.

### Changed

- Design validation, JSON loading, LM Studio completion and Apply all use the same media-plan repair path, so an already generated but repairable Design JSON can be validated and applied after restarting Studio.
- The Design system prompt now explicitly requires visual Shots to receive generated or reused Picture coverage while respecting the nine-Picture physical limit.

### Verification

- Added regressions for empty-Picture recovery, zero-image visual coverage, transient Z-Image retry and preservation of the requested physical Picture slot.
- The complete bundled test suite passed: `213` tests.
- The Director Project format remains version `16`; no saved-project migration is required.

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

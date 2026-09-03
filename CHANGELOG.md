# Changelog

Every user-visible correction receives an application version and a dated entry in this file. Application versions follow Semantic Versioning pre-release notation. The `.h3director.json` project-format version is maintained separately and changes only when the saved schema changes.

## [0.3.2-alpha.3] - 2026-09-03

### Drone still-reference orbit-ring isolation

- Split camera-motion planning from Z-Image still composition for `drone-fly-on-city`. Sentences and subject keywords describing a 360-degree orbit, orbital yaw, route or trajectory are removed from generated still-reference requests while the real H3 video Shot keeps its intended orbit movement.
- Added a mandatory clean-frame contract stating that the drone path is implied only through camera motion, plus a request-scoped Z-Image negative prompt covering visible flight paths, orbit rings, circular light trails, glowing ellipses, HUD graphics and neon loops.
- The active Z-Image ComfyUI template now receives request-specific negative conditioning instead of silently ignoring it. Right-click Z-Image regeneration applies the same protection to old drone reference Pictures without changing their stable `P` mapping.

### Drone city-fireworks Special Skill

- Added `drone-fly-on-city-fireworks`, a Default-bound night-city aerial celebration Skill that combines the proven P1 scene-master/P2 analysis-only route contract with one physically plausible 360-degree landmark orbit.
- Added a per-Shot fireworks continuity ledger covering launch and burst position, gold/white/deep-red particle phase, smoke drift, façade/wet-street reflections, exposure response and distance-delayed native firework sound.
- Added fireworks-aware Z-Image still isolation. Static references retain discrete chrysanthemum bursts and smoke while camera-orbit clauses are removed; an additional request-scoped negative contract rejects continuous firework rings, tower-wrapping effects, fused landmarks and solid neon fireworks.
- Added English/Chinese Skill instructions, an editable 15-second Petronas Twin Towers Design Requirement template, common Scene Keyframe Chain support and regression coverage for Design normalization, H3 motion retention and right-click Z-Image regeneration.

### Live-action arcade fighter Special Skill

- Added `street-fighter-live-action-h3`, a Default-bound Special Skill for 15-45 second live-action arcade martial-arts film scenes. It distils the supplied 2026 trailer reference into reusable original production grammar rather than copying its edit: two readable fighters, grounded live-action materials, bold tournament staging and selectively heightened signature attacks.
- Added a deterministic seven-Shot, 12-Beat close-combat structure per 15 seconds: one eye-level establishing Wide capped at 1.0 second followed by six Close-up/Extreme close-up action Shots carrying two beats each. A 30-second design uses two continuous, non-repeating 12-Beat Segments and a stable two-fighter identity/style/ability ledger.
- Added move-specific execution rules for compact palm projectiles, rotating kicks, forward rolling attacks, close electric strikes and rapid hand strikes, with physically motivated light, Foley and post-contact environment response.
- Added English/Chinese Skill instructions, an editable 15-second Design Requirement template and regression coverage for profile loading, binding, action budgeting, Segment continuity, visible-text control and Virtual Media Pool mapping.
- Added fixed Karate, Judo, Jeet Kune Do and Wing Chun attack/defence reversals, contact-driven water splashes, sourced smoke, grounded cyberpunk practical lighting and an explicit ban on stage spotlights.
- Added an optional MMA ground-game branch inside the same 12-Beat budget: visible level change and single/double-leg capture, controlled takedown, locked top/bottom control, a maximum two-contact ground-and-pound burst, controlled submission, visible tap and immediate release. Ground-state continuity now records top/bottom identity, head direction, screen side, grip ownership and simple leg position across cuts.
- Extended the Skill to 45 seconds using three connected native Segments, 21 Shots and a 36-entry global Action Ledger. Duplicate technique/target/outcome combinations must be rewritten rather than disguised through a new camera angle or visual effect.
- Replaced generic gloves with locked open-finger MMA glove geometry: visible separate fingers for grappling, compact padded knuckles, rounded streamlined shell, secured wrist wrap and persistent wet grime along the lower cuff.
- Added a reference-derived fictional sealed industrial vertical-maze environment across a lower service corridor, flooded utility landing and upper maintenance catwalk. Per-Shot environment state now preserves gates, cable/pipe landmarks, wet patches, mould/rust, IES-profiled practical lights, alarms, steam sources and contact-displaced debris while allowing one causal environment change per Shot.

## [0.3.2-alpha.2] - 2026-09-03

### Dark rescue camera-mode repair

- Repaired the invalid mixed-case `dark-rescue-h3-no-POV` folder as the creator-valid `dark-rescue-h3-no-pov` profile and separated its behavior from the first-person Skill. The no-POV version now explicitly uses an external cinematic observer camera with a visible rescuer instead of accidentally inheriting rescuer-eye instructions.
- Strengthened `dark-rescue-h3` with positive in-frame POV evidence distilled from the five supplied production references: near-lens glove/forearm/tool/helmet anchors, eye-height geometry, body-motivated parallax, victim-to-eye-line interaction and reachable exterior/Final Hold viewpoints.
- Added deterministic Design normalization for `dark-rescue-h3`. Every Shot's framing, angle, movement, executable action, continuity and additional direction now carries the physical S2 eye-line contract; generated image references receive the same perspective proof and external-camera language is neutralized before H3 compilation.
- Updated both English/Chinese Skill files and their distinct Design Requirement templates, plus regression coverage proving the first-person and no-POV profiles cannot collapse into the same camera mode.

### Drone scene keyframe chain

- Added an ordered user-authored scene chain for `drone-fly-on-city`: P1 and later selected P3/P4/P5 Pictures now own disjoint Timeline ranges instead of being loaded together for the complete clip. A future Picture can no longer alter the earlier P1 scene.
- Added exactly one environment-only automatic terminal keyframe after the latest user scene. It has no forced Picture number, so the Virtual Media Pool assigns the next truly empty slot automatically: P4 after P1/P2/P3, or P6 after P1-P5.
- Each keyframe interval is compiled as an independent native H3 Job even inside a 12-second work area. Only the preceding final 24 silent video frames cross the boundary as motion context; future Pictures and previous audio never cross it.
- Replaced automatic terminal Pictures remain inactive history. If the user manually replaces one with a local image, stale generated-reference analysis is cleared and the new image becomes an authored scene anchor.
- Updated the English/Chinese Skill and `DESIGN_REQUIREMENT.txt` with the new keyframe ownership, terminal-frame and continuity contracts.

### Analysis-only route controls

- Added a real `analysis_only` Media Pool usage for planning maps, route drawings, masks and other control images. The compatibility alias `route_control_analysis_only` is accepted and normalized automatically.
- Analysis-only sources remain available to Design intelligence but are never placed on the Timeline, counted against per-Segment H3 capacity, uploaded to ComfyUI/MiniMax, treated as identity anchors or assigned an H3 Picture slot. Reapplying a Design also removes a control image that an older build mistakenly placed on a V track.
- Removed analysis-only `@P/@V/@A` labels from every H3-renderable Shot, cue and creative field, replacing them with the already extracted abstract control instruction so reference-token parsing cannot reactivate the source.
- Updated `drone-fly-on-city` in English, Chinese and its Design Requirement template. The former long negative-prompt catalogue repeated route-artifact vocabulary inside H3's single prompt and could visually prime the model; it is now replaced by a positive clean-frame/off-screen-control contract.
- Fixed a second prompt-priming path found during real-output acceptance: Special Skill frontmatter descriptions are discovery metadata and are no longer copied verbatim into the H3 render prompt. Control-only Skills also scrub legacy route-graphic vocabulary from loaded older Projects at final prompt compilation.
- Extended analysis-only isolation to generated-reference prompts and subject keywords, preventing a Z-Image continuation reference from inheriting control-image labels or visual annotation vocabulary.
- Reject incorrect `identity_anchor=true` metadata on environment-only image requests. Pure skyline, room, prop and landscape references now receive an environment-only subject-count guard instead of generating an unrelated prominent person.
- Added Design normalization and end-to-end workflow regressions proving a loaded P2 route-control picture remains in the Media Pool while its filename, loader and pixels are absent from the compiled H3 job.

### Design JSON completion reliability

- Removed the hidden 12,000-token completion bottleneck that could truncate a valid 45-second Special Skill plan even when LM Studio had a 100k context window. Director Design now allows up to 32,768 output tokens for its schema response.
- Added provider-neutral `finish_reason`, output-size and usage diagnostics so a completion stopped by `length` is distinguishable from a Design Requirement text-box problem.
- Added one automatic compact full-plan recovery pass when Qwen returns malformed or truncated JSON. The first failure no longer immediately blocks Apply; a second failure reports its exact line, column, finish reason and output size.
- Added a compact-output contract to every Design planning and BLIP-refinement prompt: required Shots, editable speech, continuity and media ranges are preserved while repeated prose and formatting overhead are removed.
- Refinement JSON failure is non-destructive: the already validated first Design Plan is retained instead of being replaced by incomplete BLIP-refinement output.

### Special Skill Design Requirement templates

- Added optional per-Skill `DESIGN_REQUIREMENT.txt` starter templates. Selecting a Special Skill and opening `DESIGN` now fills an empty Design Requirement with that Skill's editable production example.
- Existing authored Design Requirement text always has priority and is never overwritten. Skills without a template remain compatible and continue to open with an empty requirement.
- Added a `DESIGN REQUIREMENT TEMPLATE` editor to `SPECIAL SKILL CREATOR`; templates are loaded and saved independently from `SKILL.md` and the optional `SKILL.cn.md`.
- Added tailored templates for all 12 bundled Special Skills: 3D animation, brand promo, co-op game intro, dark rescue, hand-drawn/live-action fusion, long-form production, minimalist product advertising, music video, paper collage, papercraft stop-motion, short drama and wuxia blade film.
- Added the new `dark-rescue-h3` Default-bound Special Skill, distilled from five user-tested first-person rescue structures and their proven environmental-lighting vocabulary. Its starter request demonstrates a fictional Wall Street-inspired damaged office tower without inventing unloaded Media Pool IDs.
- Added a 45-second Tang-dynasty courtyard starter requirement to `wuxia-blade-film`, including executable action budgets, character/weapon/prop ledgers, native 15-second boundary contracts and non-magical physical combat constraints.
- Increased the Studio Special Skill Creator description limit from 600 to 1,200 characters so every bundled Skill can be edited and saved without rejecting its existing metadata.

### Verification and compatibility

- Added regressions proving every bundled Special Skill has a non-empty editable template, all templates load through the Studio profile system, and `dark-rescue-h3` opens Design with the expected starter requirement under `Default + Special` binding.
- All 38 focused Skill store, profile, creator compatibility and Design UI tests pass.
- Project format remains `21`; Workspace layout, Timeline mapping, Segment compilation, render policy, saved Projects and generated media are unchanged.

## [0.3.2-alpha.1] - 2026-09-01

### MiniMax H3 native production sound

- Added a three-state `MUSIC AUTO / OFF / TIMELINE` selector beside Design Requirement, defaulting to AUTO. AUTO sends Qwen's scene-aware score direction into every actual H3 segment prompt, OFF deterministically compiles `non_diegetic_music: N/A`, and TIMELINE enables music only for active Timeline Music Cues. The project-scoped policy persists through save/load and safely defaults old projects to AUTO.
- Added per-Shot prompt-only `Native Audio Direction`, `Environment Continuity`, `Audio Reference Intent`, and `Native Audio QC status` fields. Auto-derived values survive Timeline/segment compilation, while user edits are protected from automatic refresh.
- H3 Ref2VA prompts now time-align acoustic space, speaker-to-camera distance, screen position, natural speaking state, continuous ambience, picture-synchronous Foley and explicit diegetic-source rules with exact Dialogue Text Layers.
- Prohibited narration/announcer tone, recording-booth close-mic sound, dry studio voice and extra dialogue. Background music now follows the explicit project policy: AUTO, OFF or TIMELINE-only.
- Long renders preserve written acoustic continuity across same-space cuts, describe perspective changes for wide/close cuts, and declare interior/exterior acoustic transitions. The preceding 24-frame continuity clip is explicitly visual-only and never attaches paired audio.
- Real-world Audio/Video assets marked as acoustic references guide space, room tone, distance and location texture only; their words and voice identity cannot replace Timeline Dialogue/Speaker assignments.
- Reused the existing VAD/Whisper service for read-only Native Audio QC of expected dialogue, unauthorized speech and missing ambience. No repair, remix, filtering, TTS substitution or generated-audio rewrite was added.

### Compatibility and verification

- Project format is `21`; format 20 projects load with safe defaults for every new field. Smart Render policy is `16`, so cached segments built before the native-audio prompt contract are regenerated instead of silently reused.
- Added native-audio unit, workflow-prompt, user-override, visual-only continuity and no-external-effects regressions. Mapping, long-segment scheduling and MP4 assembly behavior remain unchanged.

## [0.3.2] - 2026-09-01

### Qwen3-TTS Local

- Added Qwen3-TTS Local as a fourth editable Dialogue Text Layer engine beside Ori, VoxCPM2 and Edge TTS. Design exposes a `Qwen` button and Settings exposes runtime/model health.
- Integrated the official `qwen-tts 0.1.1` API with the resource-efficient `Qwen3-TTS-12Hz-0.6B-CustomVoice` model, deterministic Studio Speaker mapping, exact authored words and Timeline WAV rebuilding.
- Isolated Qwen's pinned `transformers 4.57.3` / `accelerate 1.12.0` stack under `ai_libraries_common/qwen_tts_runtime` so the existing BLIP/Vox environment is not downgraded.
- Added CUDA-first loading, same-line CPU retry after CUDA load/inference failure, and immediate VRAM/RAM release before FFmpeg Timeline composition.
- Fixed the shared authored-TTS compositor so Edge, VoxCPM2 and Qwen WAV stems are padded to the exact Timeline duration instead of ending a fraction of a second early after the final line.
- Added verified Windows SoX support, runtime/model readiness warnings, one-command runtime/model setup helpers and a cross-computer transfer procedure. Large model weights remain outside GitHub under `models/`.

### Long Production Reliability

- Promoted the 120-second Long Timeline pipeline to a formal reliability baseline: approved prefixes remain reusable, Segment-local rerenders replace only the affected Take, and Preview/Final masters assemble selectively.
- Moved Smart Render jobs and worker manifests into each fixed Workspace under `project/render_jobs/`, using unique run tokens so two Projects or Studio instances cannot overwrite one another.
- Added a source fingerprint to every ComfyUI media upload name. Two concurrent Projects may now use different files with the same logical ID and basename (for example `P1/shared.png`) without colliding in the server's shared input directory.
- Added a bounded three-attempt Segment policy. CUDA out-of-memory, timeout, transport, media and unknown failures are classified; ComfyUI memory is released between retries, and the final failure class/retry budget is persisted without silently reducing quality.
- Project Load now evaluates every canonical and worker checkpoint and prefers the checkpoint containing the most durable completed Segment Takes. A newer failed/empty manifest can no longer hide an older recoverable run.
- Successful durable publication removes the large job file; interrupted or failed jobs remain available for diagnosis and resume.
- Storyboard and Smart Cut structural edits now detach the obsolete assembled Master while retaining reusable Segment checkpoints. Changed Shots dirty both their previous and remapped ranges; unchanged prefix Segments remain eligible for fingerprint reuse.
- Removed a UI-signal side effect that conservatively marked the entire Timeline dirty whenever the structural editor restored its Undo/Redo snapshot.

### Storage Optimization & Acceptance

- Added the `STORAGE` workspace with logical/physical byte reporting, Hard Link savings, category totals, SHA-256 duplicate groups and a conservative reclaim estimate.
- Added `SAFE CLEANUP` with dry-run output and confirmation. Masters, Media Pool sources, Project data, Segment Preview/Approved Takes and cache referenced by an interrupted job or standalone worker manifest are protected.
- Added verified `.h3project.zip` archives. Disposable cache/proxy/logs are excluded by default; external workflow/media are consolidated while preserving media basenames; `archive_manifest.json` records SHA-256 for every archived file.
- Archive is blocked while active/interrupted recovery data still lives only in excluded cache, preventing an apparently valid but non-resumable backup.

### Verification

- Added Standard Pipeline Release Gate 11 for interrupted cache protection, Archive blocking, durable publication and OOM classification. All eleven gates pass independently.
- Added a deterministic 120-second H.264/AAC acceptance fixture: an approved 45-second prefix is extended by five 15-second Segments, the complete Master is assembled, one middle Segment is replaced, and every outer Take hash remains unchanged.
- Added a 90-minute metadata-only stress fixture covering 900 Shots, Segment planning, fingerprints, Take state normalization, JSON save/reload and a 64 MB peak-memory ceiling without invoking H3 or the network.
- Added three focused simulations covering Storyboard reorder mapping, Smart Cut ripple/local reuse, and two separate Projects creating same-seed jobs/manifests without path or recovery contamination.
- All `401` bundled tests pass after adding Qwen runtime, CUDA fallback, exact WAV composition, Settings and Design UI regressions. A separate 31-test global Segment Mapping suite also passes.

### Compatibility and scope

- Project format remains `20`, Workspace layout remains `2`, and Smart Render policy remains `15`; existing saved Projects remain forward-compatible.
- One Studio instance still executes one ComfyUI job at a time. Centralized concurrent multi-Project scheduling and a full Scene/Sequence editing UI are explicitly deferred; project-scoped recovery and separate Studio instances are safe.

## [0.3.1-alpha.4.8.0] - 2026-09-01

### Fixed

- Fixed Qt playback failing with `moov atom not found` after Studio was closed while a high-resolution Monitor Proxy was still being encoded.
- Cached Monitor Proxies are now validated with FFprobe for a video stream, positive duration and duration agreement with the source master before Qt is allowed to open them. A non-empty filename alone is no longer considered a valid cache hit.
- Monitor Proxy encoding now writes to a process-specific `.building.mp4` and publishes the final cache path only with an atomic replace after successful validation. Closing Studio removes the active temporary proxy without touching the generated master.
- Existing interrupted／truncated proxies are automatically discarded and rebuilt from the intact `generated_output.mp4` or `generated_preview.mp4`.

### Compatibility

- Generated masters, Segment Takes, Project JSON, Reference Mapping and Timeline timing are unchanged. Only disposable `.director_cache/monitor_proxies` files are repaired.
- Project format remains `20`, Workspace layout remains `2`, and Smart Render policy remains `15`.

### Verification

- Confirmed the original `the_black_panther_in_the_sun_3A/generated_output.mp4` is a valid 30.00-second H.264/AAC 2752×1536 master.
- Reproduced the failure in its 1.31 MB proxy, which FFprobe reported as missing the `moov` atom, then rebuilt and validated a 30.016-second H.264/AAC 1280×714 proxy.
- Added regressions for interrupted proxy rejection and atomic publication.
- All `380` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.9] - 2026-09-01

### Fixed

- Fixed completed Preview／Final masters reopening as `No generated output` when the Project JSON's `generated_output`, `smart_render` and `smart_render_manifests` fields were empty or stale even though durable Workspace files still existed.
- Project Load now treats `generated_output.mp4`, `generated_preview.mp4`, `project/render_manifest.json`, root `render_manifest.json` and durable Segment Takes as authoritative recovery sources without requiring a non-empty saved output path first.
- Copied／renamed Workspaces automatically rebase a recovered manifest's master and Segment output paths away from the previous computer or source folder.
- Recovered output immediately restores Program Monitor playback, Export, request kind and render status. The Project is marked modified so one Save persists the canonical paths.

### Compatibility

- No MP4 is duplicated, moved or regenerated. Recovery reads the existing master and Take files in place.
- Project format remains `20`, Workspace layout remains `2`, and Smart Render policy remains `15`.

### Verification

- Confirmed `the_black_panther_in_the_sun_3A` contains a valid 30.00-second 2752×1536 `generated_output.mp4` despite empty output fields. It now reopens as the active generated output, enables Export, restores the Production manifest and prepares its Monitor Proxy.
- Added a current-format Project regression with deliberately empty output/manifest fields and a stale `D:\\...` manifest path; the Workspace master is recovered without regeneration.
- All `378` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.8] - 2026-08-31

### Fixed

- Picture cards now display a valid local image immediately and no longer depend on the asynchronous Media Preparation worker to obtain their first thumbnail.
- The direct-image fallback runs for old-Project path rebasing, Design-generated references, manual replacement, Z-Image regeneration and automatic transparent-background derivatives.
- The original source Picture is registered in the in-memory preview cache immediately. Media Preparation may later replace it with an optimized or transparent derivative without flashing `DROP MEDIA` or changing the logical P mapping.

### Compatibility

- This is a UI-preview correction only. It does not modify Picture files, Reference Mapping, Timeline placement, Segment fingerprints or generated video.
- Project format remains `20`, Workspace layout remains `2`, and Smart Render policy remains `15`.

### Verification

- Reopened `the_black_panther_in_the_sun_3` with its old `D:\\...` paths on the current `C:\\...` Workspace. P1 was visible immediately while Media Preparation jobs were still active.
- Added a regression proving a newly resolved local P1 is placed into both the MediaCard pixmap and preview cache before any background preparation response.
- All `377` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.7] - 2026-08-31

### Added

- Generation Work Area End is no longer capped by the current Timeline endpoint. A default 12-second project can be extended directly by typing or clicking 45s, 120s or another larger End value.
- Increasing End beyond the current endpoint expands the Timeline, mapped workflow duration node, transport range and saved Project duration together. Reducing End only selects a shorter render range and never trims existing Timeline content.
- Manual Timeline extension supports up to six hours for future long-form structures. End is automatically kept at least one 0.5-second grid step after Start.
- Added a complete tooltip explaining the editable End behavior and a status message when the Timeline is extended.

### Compatibility

- New Project default remains `12.0s`. Existing Project Work Area values and Timeline durations remain unchanged when loaded.
- Project format remains `20`, Workspace layout remains `2`, and Smart Render policy remains `15`.

### Verification

- Added a UI regression covering `12s → 120s` Timeline expansion, non-destructive `120s → 45s` Work Area reduction, workflow duration-node synchronization and invalid End-before-Start correction.
- All `376` bundled tests passed; the focused post-validation for the final input guard also passed.

## [0.3.1-alpha.4.7.6] - 2026-08-31

### Fixed

- Fixed native H3 speech-tail protection moving a safe Segment boundary forward across the next authored line. A line starting at 8.50, 22.00 or 41.00 seconds can no longer be compiled into the preceding Segment and then disappear from its own Segment.
- Added dialogue-turn-aware Segment planning. Nearby safe boundaries align to on-camera speaker changes, so alternating S1/S2 lines are not compressed into one H3 generation window when a clean split is available.
- Added an explicit speaker-to-face identity contract to every native H3 Segment prompt: S1 is the female character and S2 is the male character; each is bound to the actual dynamically mapped Picture reference. Only the scheduled speaker may move lips or jaw, while listeners keep a closed, still mouth and voice-over never drives visible lip sync.
- Added a Run／Preview speech preflight against the live Timeline. Unsafe Dialogue／Voice-over／Lyrics durations, CJK layers mislabeled as English, downstream timing and the final 1.5-second breath／room-tone tail are repaired even when the Project was already open before this version.
- Fixed endpoint repair leaving Work Area and ending media at the old duration. Projects whose Work Area previously reached the endpoint now expand through the repaired final speech and decay tail.

### Compatibility

- Smart Render policy is now `15`; policy 14 Segment caches with shifted speech ownership or ambiguous speaker-face animation are intentionally invalidated.
- Project format remains `20` and Workspace layout remains `2`. Existing Projects are repaired in memory and remain loadable; Save Project persists the corrected Timeline.

### Verification

- Offline transcription of `那个替他说“不”的_AI_4/generated_preview.mp4` confirmed the 8.50-second narration had been pulled into the first Segment, the 41.00-second narration began around 38 seconds, later dialogue was compressed early, and the final phrase remained active through 69.99 seconds before the 70.00-second hard cut.
- The repaired Project is 72.00 seconds with render windows `0–8.5 / 8.5–22 / 22–25.5 / 25.5–28 / 28–32.5 / 32.5–41 / 41–50.5 / 50.5–54.5 / 54.5–60.5 / 60.5–72s`; every authored speech layer belongs to exactly one Segment and the last line has a 1.5-second tail.
- All `375` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.5] - 2026-08-31

### Fixed

- Fixed `Project load error: TextLayer.__init__() got an unexpected keyword argument 'speech_timing_auto_adjusted'` after the final-speech timing repair.
- `speech_timing_auto_adjusted` is now a first-class persisted Text Layer field.
- Project, Undo/Redo and Storyboard Text Layer restoration now accept known fields while safely ignoring additive metadata from newer Project versions, preventing future repair markers from blocking Load Project.
- Added a short retry for atomic provisional-workspace renames when Windows, OneDrive or a thumbnail scanner briefly retains a directory handle.

### Verification

- Added a real old-Project load regression that creates an undersized final Mandarin voice-over, runs automatic endpoint repair, then restores the resulting Text Layer into the Timeline.
- All `372` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.4] - 2026-08-31

### Fixed

- Fixed a confirmed hard cut at the 70.00-second Project endpoint while the final authored Mandarin voice-over was still active.
- Existing Projects now receive conservative speech-budget repair at 3.6 CJK characters per second. Unsafe Dialogue／Voice-over／Lyrics extends on the 0.5-second grid and ripples its owning Shot, later Shots, Text Layers, authored requirements, media clips and Work Area.
- The Project endpoint now reserves a 1.5-second final breath, room-tone and reverb tail after the last authored utterance.
- Fixed stale Prompt timing after an automatic Project repair; editable Prompt fields are rebuilt from the repaired Timeline during Load Project.
- Native H3 Segment prompts now include an exact speech-window whitelist and explicitly forbid filler syllables, false starts, repeated or translated words, commentary, whisper, crowd speech and phone voices in every vocal-silence gap.
- Removed orphan quoted words and all untracked visible-text directions from compiled Shot and global prompts. Exact visible text must be owned by an editable `on_screen_text` Timeline layer.

### Compatibility

- Smart Render policy is now `14`; policy 12/13 Segment caches containing cut dialogue, polluted speech or burned typography are intentionally invalidated.
- Project format remains `20` and Workspace layout remains `2`. Opening the affected 70-second Project repairs it in memory; Save Project persists the new timing.

### Verification

- Offline transcription of the supplied output confirmed non-authored speech at 25.23–26.91, 27.30–29.01, 32.00–32.63 and 55.08–55.83 seconds, plus active final speech through the exact 70.00-second endpoint.
- Verified `那个替他说“不”的_AI_2` repairs from 70.0 to 77.5 seconds; its final voice-over moves to 66.5–76.0 seconds and receives a 1.5-second tail.
- All `371` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.3] - 2026-08-31

### Fixed

- Fixed abrupt native dialogue／voice-over starts and cut-offs at independently generated H3 Segment boundaries.
- Authored Dialogue／Voice-over／Lyrics now protect every internal render cut through the complete utterance plus a 1.0-second breath, room-reverb and ambience decay tail when Timeline capacity permits.
- A fully packed 15-second sequence now inserts an additional safe Segment when moving one boundary would exceed H3's native limit; it no longer cuts the authored line merely to preserve the old Segment count.
- Every native Segment prompt now forbids unlisted speech, requires continuous location ambience, completes authored words by the Text Layer end, and forbids a new word, music cue or Foley transient in the final second.
- Preview／Final assembly applies a 40ms audio de-click fade at internal joins without changing video timing, Segment duration or Reference Mapping.

### Compatibility

- Smart Render policy is now `13`; old Preview／Final Segment caches are intentionally invalidated so already-encoded hard audio cuts cannot be reused.
- Project format remains `20` and Workspace layout remains `2`; existing Projects load without migration.

### Verification

- Extended Standard Pipeline Release Gate 4 with the speech-boundary case, including a fully packed 45-second Timeline that must add a fourth safe Segment.
- Verified `那个替他说“不”的_AI_2` now plans `0-8.5`, `8.5-20.5`, `20.5-32.5`, `32.5-41`, `41-53`, `53-61`, and `61-70` seconds. The 58-60 second line belongs only to the `53-61` Segment.
- All `371` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.2] - 2026-08-31

### Added

- Added `REGENERATE WITH Z-IMAGE` to the right-click menu of eligible Media Pool Picture cards.
- Regeneration reuses the Picture's original Design request metadata, including subject keywords, exact cast/count contract, identity-anchor relationship, environment, composition, time range and preferred stable P identifier.
- Successful output replaces the same logical Picture source without changing its Loader node, P mapping, repeated Timeline occurrences or Clip Prompt. Only intersecting render Segments are marked dirty.
- Every regenerated take is non-destructive and stored below `media/regenerated_references/P#/`; BLIP and optional semantic analysis are then refreshed against the new image.
- Added a per-card translucent Z-Image progress overlay and worker timeout/close protection.

### Verification

- Verified project `那个替他说“不”的_AI_2` P5 resolves as node 153, remains P5, retains 20.00–32.50s scope, `req_man_identity`, and the exact-two-person contract.
- Added regressions for Picture-only context-menu activation and in-place regeneration without Reference Mapping changes.
- All `368` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.1] - 2026-08-31

### Fixed

- Fixed cross-computer Queue failure when canonical Project JSON lives in `Workspace/project` while generated image, video or audio sources live in sibling `Workspace/media` trees.
- Runtime media recovery now searches both the JSON directory and the complete canonical workspace, then accepts only a unique basename match.
- Clean Project export now rewrites unavailable absolute paths to verified local workspace files instead of preserving another computer's drive path.

### Verification

- Strengthened Standard Pipeline Release Gate 1 with the canonical `project/` plus sibling-media layout.
- Added regressions for runtime sibling-tree recovery and Clean Project path rebasing.
- Rebuilt `那个替他说“不”的_AI/project/director_project.clean.h3director.json`; all nine image Loader paths exist locally.
- Real 7-Segment Queue preflight passes with no missing media and no unresolved Loader.
- All `366` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7] - 2026-08-31

### Fixed

- Closed a Reference Mapping leak where a generated environment still could be promoted as a whole-project character anchor and earlier airport/hotel/computer references could remain active in later story phases.
- Added exact cast/count contracts for identity, secondary-character, two-person and environment reference images. Existing malformed project references are repaired on load without overwriting the source JSON.
- Fixed dialogue timing expansion that increased Timeline duration without extending the owning final Shot, producing a render Segment with `shot_ids=[]` and allowing an earlier scene to reappear.
- Preserved normalized `text_layers.shot_id` during Apply instead of ambiguously recomputing ownership on an inclusive Shot boundary.
- Segment manifests now report only media Loader files actually connected in that Segment workflow, while uploads remain deduplicated job-wide.
- Clean projects with invalidated render state no longer auto-load a stale root `generated_output.mp4` into Program Monitor.

### Changed

- Removed project-total media-request capacity checks. Virtual Media Pool IDs may continue beyond P9/V3/A3; physical 9/3/3 limits are enforced only for simultaneously active references per Segment.
- Design/Qwen rules now require exact cast ledgers, one-location Shot Blocks, time-scoped environment references and complete Shot coverage after speech ripple.
- Strong multi-location `Cut to` montage prose is split into executable single-location Shots during project integrity repair.
- Added `project_integrity.py` for data-only portable Project repair and clean JSON export.
- Smart Render policy is now `12`, so older Segment caches compiled before the mapping/coverage correction are not silently reused.

### Verification

- Added Standard Pipeline Release Gate 9 for Reference Mapping isolation, P10+ virtual media and Segment-local manifest reporting.
- Added Standard Pipeline Release Gate 10 for dialogue-duration ripple, Text-to-Shot ownership and zero Shot-less render Segments.
- Project format remains `20`; Workspace layout remains `2`.
- All `364` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.6] - 2026-08-31

### Changed

- Replaced the seven AI Design Apply popup entry families with one inline `APPLY PREFLIGHT REPORT`, grouping all findings into Auto-fix, Warning and Hard Block sections.
- Made Apply transactional: the Design page stays open and duplicate submission stays disabled until Timeline/Workspace commit succeeds. Runtime failure returns the same JSON and page to a retryable state; only `_commit_ai_design` closes it.
- Routed generation-state, missing model/input, unknown explicit media, invalid generated JSON, Load JSON and downstream Workspace errors into the inline report instead of modal warning chains.

### Auto-repair and degradation

- Explicit duration mismatch now retimes the complete Shot/Text/Media/Cue plan onto the requested duration's 0.5-second grid during Apply preflight.
- Missing Creative Brief and Visual Style receive deterministic safe defaults; duplicate media `requirement_id` values receive stable suffixes.
- Unsafe Z-Image requests containing H3 Picture tokens, dependent-frame wording or neutral/studio action backgrounds are rebuilt as standalone in-world frozen frames.
- Camera overlap that cannot preserve two 0.5-second cells now merges both actions and continuity states into one executable Shot instead of blocking the whole Design.
- Disabled non-explicit model-selected Media Pool references are removed. Explicit missing `@P/@V/@A` references remain Hard Blocks.
- Missing VoxCPM2 models or fully occupied Audio slots now preserve exact editable speech Text Layers, defer WAV creation and mark Timeline TTS pending instead of aborting the visual Design.

### Compatibility

- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`. Existing projects and Design JSON remain loadable without migration.

### Verification

- Added [`APPLY_ARCHITECTURE_ACCEPTANCE_CHECKLIST.md`](APPLY_ARCHITECTURE_ACCEPTANCE_CHECKLIST.md) with the complete 17-family policy and lifecycle contract.
- Added Standard Pipeline Release Gate 8 for safe repair, no modal Apply chain, retry-after-failure and close-after-commit behavior.
- All `362` bundled tests pass.
- All eight Standard Pipeline Release Gates pass independently.

## [0.3.1-alpha.4.5] - 2026-08-31

### Fixed

- Replaced the blocking `Shot Sx overlaps Sy` failure for repairable AI Design output with deterministic camera-cut boundary repair on the 0.5-second Timeline grid.
- Adjacent overlapping Shots now share the nearest feasible midpoint boundary while retaining at least 0.50 seconds for each Shot. The warning records both original ranges and the repaired cut.
- Kept Media Pool clips and Dialogue／Voice-over／Lyrics／On-screen Text ranges untouched because those layers may legitimately overlap on separate V/A tracks.
- Retained a hard validation error only when the combined interval cannot preserve one 0.5-second Timeline cell for both camera Shots.

### Compatibility

- No project schema, Workspace layout or render-policy fields changed. Existing Design JSON and saved projects remain loadable; normalization repairs eligible overlap during Load／Apply.

### Verification

- Added regressions for automatic shared-boundary repair and irreparable sub-second overlap protection.
- All `356` bundled tests pass.
- All seven Standard Pipeline Release Gates pass in the complete suite.

## [0.3.1-alpha.4.4] - 2026-08-31

### Changed

- Rebuilt Generation Work Area in the exact requested order: start, end, Aspect, Mode, Batch seconds, Next, approved seconds, Export API, server address, Test, Run+Queue, Storyboard, story duration, Auto Cut, Preview, Accept, Reject and Estimate.
- Removed the custom `MORE ▾` control and all hover-to-expand behavior. When row one reaches the available width, every remaining control stays visible automatically on a persistent second row.
- Added compact Work Area formatting (`0s`, `15s`, `0.5s`) without losing sub-second values, and shortened the visible controls to `TEST`, `PREVIEW 0.2M` and `ACCEPT 1.0M`.
- Kept Batch seconds, Next and approval progress visible in both modes for a stable layout; they remain disabled in FULL and become active in BATCH.

### Compatibility

- No project schema or render-policy fields changed. Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

### Verification

- Replaced the hover-overflow regression with an ordered persistent-wrap regression that checks both rows, compact second formatting and the absence of native Qt `»` overflow buttons.
- All `355` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.

## [0.3.1-alpha.4.3] - 2026-08-31

### Fixed

- Fixed the real Generation toolbar failure shown at wide desktop resolution: Qt's native `»` extension no longer captures `AUTO CUT` or the custom `MORE ▾` control.
- Moved `AUTO CUT` and `MORE ▾` ahead of optional server/render groups, added DPI/layout safety reserve, and allowed Batch controls to move as one complete overflow group only at constrained widths.
- Preserved FULL/BATCH widget visibility through QWidgetAction transfers. FULL no longer re-shows Batch seconds, NEXT and progress after a responsive reflow.
- Clicking the custom `MORE ▾` now explicitly opens the complete second row; hovering continues to open it automatically.

### Compatibility

- No project schema or render-policy fields changed. Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

### Verification

- Extended the toolbar regression to reject a visible native Qt extension button, keep `AUTO CUT` visible, retain the populated primary row, and verify both hover and click open the custom overflow row.
- All `355` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.

## [0.3.1-alpha.4.2] - 2026-08-31

### Fixed

- Restored the missing Auto Cut entry point at constrained window widths. The compact `AUTO CUT` control is now pinned to the primary Generation Work Area row instead of being moved into the hidden overflow toolbar.
- Renamed the visible Smart Cut trigger and its Safe, Balanced and Aggressive menu entries to `AUTO CUT`, while preserving the existing protected Smart Cut planner and Manual Ripple Cut workflow.
- Kept the entry label stable as `AUTO CUT` even when the Timeline already matches the target, and corrected the responsive `MORE ▾` action/widget visibility synchronization.

### Compatibility

- No project schema or render-policy fields changed. Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

### Verification

- Extended the responsive-toolbar regression to require `AUTO CUT` on the primary row at the minimum supported window width and to ensure it is never placed in the hidden overflow row.
- All `355` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.

## [0.3.1-alpha.4.1] - 2026-08-31

### Added

- Added a responsive two-row Generation Work Area. Complete control groups move to a hidden second toolbar row when the available window width cannot display them safely; Work Area, Aspect and Production Mode remain on the primary row.
- Hovering the Generation toolbar or its `MORE ▾` affordance now expands the second row immediately. Moving outside both rows starts a short delayed collapse so the row does not disappear while the pointer crosses between toolbars.
- Added immediate rich Hover Help to every compact Generation control, including complete name, purpose and expected effect for Work Area, Aspect, Full/Batch production, Export, ComfyUI connection, Run, Storyboard, Smart Cut, Preview/Accept/Reject and Estimate.

### Compatibility

- No project schema or render-policy fields changed. Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

### Verification

- Added a UI regression that forces the minimum supported window width, verifies complete control groups move to the secondary toolbar, triggers its Hover Enter event and checks rich help metadata on compact controls.
- All `355` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.

## [0.3.1-alpha.4] - 2026-08-31

### Added

- Added compact `MODE: FULL / BATCH` production controls, a configurable 30-second default Batch size, `NEXT` and live approved/total status to the Generation Work Area.
- Incremental production previews only the next unapproved range. Accept switches to a cumulative 0-to-horizon render, reuses approved Smart Render Segments and publishes one continuous Preview/Final master in Program Monitor.
- Added speech-safe approval horizons. A proposed Batch boundary moves past intersecting Dialogue, Voice-over or Lyrics and prefers a nearby Shot boundary instead of cutting exact authored speech.
- Persisted the approved horizon, pending range, Batch phase, Preview seed and Preview-ready state in Project and Design Undo/Redo state. Smart Render checkpoints therefore resume an interrupted Batch without returning to all-at-once production.
- Added the Default-bound `long-form-h3-director` English/Chinese Special Skill. It preserves the full story, plans Sequence/Shot responsibilities, Incoming/Outgoing State, 24-frame motion context, exact text layers, Segment-local references and exactly one real project-ending Final Hold.
- Selecting `long-form-h3-director` automatically selects Incremental production; selecting None or another Special returns to Full Range while retaining manual strategy controls.

### Compatibility

- Existing projects without the optional Incremental fields open in `FULL RANGE` with no behavioral change.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

### Verification

- Added nine regressions for bilingual Skill discovery/binding, automatic strategy switching, speech-safe Batch boundaries, next-range-only Preview, cumulative Accept, durable approval advancement, project payload state and Open Project resume.
- All `354` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.

## [0.3.1-alpha.3] - 2026-08-30

### Added

- Added the three-stage Smart Cut workflow. Phase 1 uses a deterministic dynamic-programming planner on the Studio's 0.5-second grid with Safe, Balanced and Aggressive modes, explicit speech/action minimums, protected narrative roles and impossible-target warnings.
- Added a non-destructive Smart Cut review window with Original/Edited/Target totals, per-Shot KEEP/TRIM/MERGE/REMOVE decisions, importance/risk/reason columns, manual Shot locks and duration overrides. Cancel never mutates the Timeline; Apply is one Undo/Redo transaction.
- Added Phase 2 dependency analysis for adjacent continuity state, shared P/V/A references, visible track relationships and native 15-second boundary risk. Accepted plans remap Shot-owned cues, text, media Source In/Out and local render-dirty ranges, then save `smart_cut_plan.json` in the fixed project Workspace.
- Added Phase 3 semantic refinement through the currently configured Design provider. Online GPT or LM Studio may classify story role, bounded importance, protection and redundancy only; its JSON schema contains no timing/edit authority and all durations are recalculated locally.
- Preserved the original manual purple-Shot Ripple Cut in the `SMART CUT` arrow menu alongside direct Safe/Balanced/Aggressive planning and the Storyboard Editor shortcut.

### Fixed

- Smart Cut LM cleanup now unloads the model instance actually resolved by LM Studio when a saved/deleted model identifier was automatically replaced, preventing a stale `model_not_found` unload request.
- Authored Dialogue, Voice-over and Lyrics cannot be removed or merged by either automatic planning or reviewed Apply. An unsafe target remains visibly over target instead of cutting words.

### Verification

- Added seven pure Smart Cut engine regressions and four Timeline/UI integration regressions covering exact grid targets, protected speech, deterministic critical-role floors, dependency graphs, merge audit, bounded LM hints, Cancel safety, Apply/Undo/local dirty state, legacy Manual Ripple Cut and resolved-model unload behavior.
- All `345` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.7] - 2026-08-30

### Changed

- Storyboard cards now lift three pixels with a raised border and shadow while the pointer hovers over them.
- Starting a drag now displays a 94%-opaque lifted card ghost with a layered soft shadow under the pointer while the real grid position remains a visible `DROP HERE` target.
- Neighboring cards now slide for 190ms as the target position changes. Releasing a card adds a 260ms lift-and-settle pulse with a fading cyan landing outline; arrow-button moves use the same landing feedback.

### Verification

- Expanded Storyboard interaction regressions to verify hover tracking, the dedicated card delegate, enlarged shadow ghost, reflow timing and drop-settle timing/state.
- All `334` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.6] - 2026-08-30

### Added

- Added selected-Shot left and right arrow buttons to the Storyboard Inspector. Each click moves the selected card exactly one position, animates the neighboring-card reflow and disables the unavailable direction at the first or last position.
- Added an Explorer-style `VIEW` menu with Extra large icons, Large icons, Medium icons, Small icons, List, Details, Tiles and Content layouts. Each mode changes both card geometry and information density without modifying Timeline data.

### Changed

- Large icons remains the default three-column Storyboard layout. The chosen view is remembered in Undo/Redo workspace state and in saved `.h3director.json` projects; New Project restores the default.

### Verification

- Added regression coverage for all eight display modes, left/right reordering, boundary button states and view preference persistence.
- All `334` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.5] - 2026-08-30

### Fixed

- Fixed Storyboard cards repeatedly selecting a global full-Timeline identity Picture such as P1. Thumbnail selection now prioritizes explicit Shot semantic direction, then a Picture whose start/end exactly matches that Shot, and only falls back to the global P1 identity anchor when no dedicated Shot frame exists.
- Verified the reported `Sam_Altman_The_Human_in_the_Machine` mapping: S2→P5, S3→P6, S4→P3, S5→P7, S6→P8, S7→P4 and S8→P9; S1/S9 correctly fall back to P1 because they have no dedicated Shot Picture.

### Changed

- Storyboard Drag & Drop now lifts a real card ghost under the pointer and leaves a visible `DROP HERE` placeholder in the board.
- Crossing another card moves the placeholder immediately, reflows neighboring cards into the vacated grid position and runs a 150ms OutCubic slide animation. Releasing commits the draft order; cancelling restores the original row.
- Every Storyboard card now displays `FRAME P#` so the exact thumbnail source is inspectable instead of being inferred from the broader `MEDIA` list.

### Verification

- Added a regression with a full-duration P1 plus an exact-range P5, proving S2 selects P5 and the drag placeholder changes `[S1,S2,S3]` to `[S2,S3,S1]` while preserving the selected card.
- All `333` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.4] - 2026-08-30

### Changed

- Rebuilt the Storyboard center pane as a responsive three-column visual card grid matching the requested film-board layout while retaining the duration header, selected-Shot Inspector, Add/Delete controls and Apply/Cancel workflow.
- Every Shot card now displays its Timeline time range, duration, preset, core action, environment response, speech count and active P/V/A IDs over a 16:9 visual reference thumbnail.
- Shot thumbnails prefer the actual overlapping Timeline image or cached video preview. A deterministic `NO VISUAL REFERENCE` card is used when that Shot has no valid visual source, preventing a neighboring Shot's image from being shown incorrectly.
- Upgraded Shot movement to real Qt Internal Move drag-and-drop with a visible drop indicator, snap layout and immediate order/time/duration refresh after Drop.

### Verification

- Expanded Storyboard UI coverage to require Icon Mode, Internal Move, enabled drag/drop, a three-column wide layout and non-empty card artwork.
- All `332` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.3] - 2026-08-30

### Added

- Replaced the main `STORYBOARD` action with a dedicated Storyboard Editor window built from the current Timeline Shot, speech and media state.
- Added draggable Shot blocks with live original duration, edited duration, target duration and over/under-target calculations.
- Added draft-only Shot creation, deletion, title/core-action editing and 0.5-second duration adjustment. `Cancel` leaves Timeline untouched; `APPLY TO TIMELINE` commits the entire board as one Undo/Redo operation.
- Storyboard cards report each Shot's current time range, must-complete action, editable speech-layer count and active P/V/A reference IDs.

### Changed

- Storyboard Apply now remaps downstream Shot ranges, Transition/Marker cues, Dialogue/Voice-over/Lyrics layers and media clips to the new order and duration.
- Audio and video spanning multiple reordered Shots are split with adjusted source in/out and playback speed; Media Pool originals remain intact. New Story Beats intentionally return as empty Timeline Shots ready for new media or Type Tool content.
- Any Storyboard structural edit invalidates generated output and marks render Segments dirty, while Cancel never changes render state.

### Verification

- Added UI coverage for live duration accounting, add/delete/reorder and the real Apply button.
- Added dependency-remapping coverage for Shot reorder, deletion, insertion, media splitting and Undo.
- All `332` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.2] - 2026-08-30

### Added

- Added `STORY CUT` beside Storyboard with an editable target duration. Editors can select an unwanted purple Shot Block and press Delete to perform a non-destructive ripple cut across Shots, cues, speech layers and source media while retaining the original Media Pool assets.
- Expanded Design plans now retain their original requested duration as the Storyboard target. Legacy projects recover this value from the latest Design revision, so a 107.5-second speech-safe plan can be reduced back toward the requested 45 seconds without another LM Studio pass.
- Added a render-time visible-text whitelist. Subtitles are permitted only when a synchronized Timeline `on_screen_text` layer exists; otherwise H3 receives a hard visible-text lock that forbids captions, lower thirds and speech burned into pixels.

### Fixed

- Chinese generation commands such as `帮我生成45秒视频...总结以下内容如下` no longer become Workspace names. A valid AI story title now outranks the instruction, and the fallback scanner skips the command to find the first meaningful story sentence.
- Storyboard Shot deletion now updates downstream timecodes, splits spanning audio/video safely, refreshes Shot ownership for Text Layers, invalidates only affected render state and remains fully Undo/Redo capable.

### Verification

- Added naming, subtitle-policy, render-whitelist, legacy-target recovery and Storyboard ripple-cut regressions.
- All `330` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.1] - 2026-08-30

### Changed

- Missing AI-authored Dialogue／Voice-over／Lyrics is no longer a dead end. Studio still retries LM Studio once; if a broad speech request returns no editable words again, the visual Director Design remains valid and can be applied to the H3 Workspace.
- Added a red `⚠ ADD EDITABLE DIALOGUE / VOICE-OVER / LYRICS` Timeline marker at 0.00s for every unresolved requested role. The marker tells the editor to use the Type Tool, remains visible in saved projects and is deliberately excluded from H3 Prompt, TTS and technical directions.
- Exact time-coded user-authored wording remains a hard contract: Studio deterministically restores it, and Apply/Run is still blocked only if those supplied words genuinely cannot be recovered.
- Speech-reminder warnings are non-modal. Apply completes normally and reports the reminder in the Design Summary, Timeline and status bar instead of opening the former blocking `Invalid AI Design speech tracks` dialog.

### Verification

- Added regressions for generic missing-speech reconciliation, exact authored-speech protection, red Timeline rendering and exclusion of UI-only reminders from H3 Prompt compilation.
- All `325` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2] - 2026-08-30

### Added

- Completed the Long Timeline Foundation for 120-second projects. Extending a 45-second Timeline now retains the existing production master seed, locks every unchanged Approved 0–45-second Segment for reuse and schedules only the new 75 seconds. Editing an older range explicitly dirties and unlocks only its affected Segment.
- Added automatic partial Smart Render checkpoints after every completed or failed hidden Segment. The canonical Director Project and project render manifest are updated before a full Master exists, so reopening the Project can reuse valid completed work.
- Added deterministic Workspace naming from the first loaded Picture's BLIP `Overview`. When no Picture exists, the first meaningful authored story sentence in Design Requirement becomes the name.

### Fixed

- Fixed provisional Workspace folders remaining named after `Create a 12.00-second full-reference video...` even though the manifest later had a descriptive name. A workspace containing only manifest/calibration/imported sources may now be safely renamed, and all in-memory imported paths are rebased to the new root.
- Prevented imported filenames from becoming project titles when BLIP or Design subject evidence is available.
- Expanded competing identity-reference detection to recognize `matching P1`, bare `P1` and `<Picture 1>` as well as `@P1`; old Design plans can no longer load a separately generated P1-lookalike action frame merely because the `@` was omitted.

### Changed

- Program Monitor, Timeline scene, millisecond scrubber, Render Status Bar and duration-weighted Shot progress now have explicit 120-second regression coverage.
- Resource Estimate now reports cached, non-dirty Segment core time as reusable; the 45→120-second regression reports exactly `75s new / 45s reusable`.
- The existing `_4` project folder is intentionally not moved automatically because it already contains a saved Project and approved render. The new naming policy applies to new or imported-only provisional Workspaces without risking broken saved paths.

### Verification

- Added regressions for P1 Overview extraction, Unicode story-sentence naming, imported-only Workspace rename/rebase, bare-P1 identity filtering, 45-to-120-second approved Segment reuse and partial-render resume checkpoints.
- All `321` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.9] - 2026-08-30

### Fixed

- Fixed the real P1 identity-routing defect found in `Create_a_12.00-second_full-reference_video._Treat_the_current_Timeline_its_activ_3`: support prompts that quoted the words “authoritative recurring face identity” could be promoted ahead of P1. The compiler now gives the explicit support declaration precedence and recognizes `authoritative identity reference` / `authoritative whole-design face identity anchor` on the actual user Picture.
- Prevented an independently generated action-state Picture such as “girl, face matching @P1” from entering the H3 request as a competing face. The real P1 remains the only face source; the Shot action supplies pose and movement. This filter also protects previously saved projects at compile time.
- Kept genuinely separate generated actors available as distinct secondary-character references instead of incorrectly forcing their faces to replace P1 or hiding them as P1 support art.
- Fixed instruction-derived Workspace folders that were allocated before Design completed. If the provisional Workspace contains only its manifest/resource estimate, Apply now renames it to the descriptive generated-reference keyword name before references or project files are written. Durable, saved and legacy Workspaces are never moved automatically.

### Verification

- Replayed the reported project data. Before the fix, the prompt stated that `<Subject 1>` came from `<Picture 2>` and marked Pictures 2-5 as authoritative; after the fix, `<Subject 1>` comes exclusively from `<Picture 1>` and only P1 is authoritative.
- Recompiled the saved project: the two independently generated P1 pose images are excluded, leaving P1 plus the separate adult runner and environment references in the H3 request.
- Added regressions for quoted-authority support prompts, redundant P1 pose generation, distinct secondary actors, provisional Workspace refinement and durable-Workspace protection.
- All `314` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.8] - 2026-08-30

### Added

- Upgraded every recurring-character identity anchor into a deterministic Character Continuity Contract. Face, age, skin tone, hairstyle and hair color, body proportions, upper/lower wardrobe style and color, trousers or skirt, shoes and accessory ownership are fixed by default.
- Explicitly separated motion-safe variation: expressions, poses, arm/leg angles, walking/running phase and physically caused hair or clothing motion remain free to change with each Shot.
- Restricted wardrobe/hairstyle changes, injury, dirt, damage, shoe removal and accessory loss or transfer to explicitly authored story events. The changed outgoing state must persist as every later Shot's incoming state until another authored change.

### Changed

- The contract is written into the identity reference, Design Constraints, independent T2I support-reference prompts and the final H3 `subject_definitions`/`detailed_description`. Supporting generated Pictures inherit the current wardrobe and prop ledger but remain unable to redefine the face.
- The Design system prompt now requires appearance-state transitions to cross Shot and Segment boundaries without an unexplained reset.

### Verification

- Replayed both user-supplied P1 and generated-only identity-anchor paths; each produces the fixed/variable/story-only contract idempotently, while support images receive the same current-state guardrails.
- All `309` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.7] - 2026-08-30

### Fixed

- Rejected copied instruction prose such as `Create a 12-second full-reference video...` as a Workspace title. Generic, corrupted and non-ASCII-only titles now use the complete first generated-reference keyword group, for example `marathon_track_morning_sunlight_trees`.
- Made an explicitly authored user Picture face/identity reference authoritative over every independently generated Picture. The supplied Picture is widened to the whole Design; generated references lose any accidental identity-anchor flag and become environment, prop or action-state support with no readable competing face.
- Clarified the final Ref2VA subject definitions and retention analysis so the authoritative face Picture and support-only Pictures cannot be interpreted as equal identity sources. The official `summary:\n[reference generation]` first-line contract remains enforced.
- Added lightweight `shots/SHOT_ID/shot_manifest.json` mirrors. Shot folders now expose Timeline/source ranges and portable Preview/Final Segment references while keeping each MP4 stored only once under `segments/SEGMENT_ID/takes/`.

### Verification

- Replayed the reported marathon Design plan: its Workspace name resolves to `marathon_track_morning_sunlight_trees`, `P1` is the sole whole-design identity anchor, and all four generated Pictures point back to P1 without retaining a generated identity anchor.
- Added Shot manifests to the reported Workspace for S1-S4 without creating any per-Shot MP4 copy.
- All `309` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.6] - 2026-08-30

### Fixed

- Fixed a universal Smart Render mapping defect where the global `unique_media` upload union repatched every Segment Workflow. When different Segments reused the same physical Loader node, the final Segment's file could overwrite every earlier Segment and replay the wrong reference. Segment Workflows now retain their own active upload names; the union is used only for one-time upload.
- Updated portable-media validation to support several valid virtual assets sharing one physical Loader across different Segments while still rejecting missing, unbacked and stale files.
- Added one whole-design generated character identity anchor when three or more independently generated Pictures contain a recurring person. Supporting action/environment references can no longer define a competing prominent face.

### Added

- Added a deterministic speech-duration budget based on language, punctuation and Delivery. Unlocked over-dense generated speech extends its owning Shot and shifts all later Shots, Text Layers, cues and media ranges on the 0.5-second grid.
- User-authored exact timecodes remain locked. Over-budget Dialogue, Voice-over and Lyrics clips render deep red with a bright-red edge so the user can see where H3 may speak early, reorder, omit or change words.
- Added Standard Pipeline Release Gate 6 for the `unique_media`/Segment Workflow collision. The previous compact Segment storage/reload gate is now Gate 7.

### Verification

- All `304` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.5] - 2026-08-29

### Fixed

- Fixed Storyboard appearing unresponsive when a loaded project saved its Playhead exactly on the exclusive Work Area end. Storyboard now rewinds to the Work Area start, switches to Timeline source/audio and begins playback immediately while preserving the generated Final on the comparison side.
- Fixed `RUN+QUEUE` being silently redirected back into Storyboard or Motion Preview by a hidden persisted quality-profile state. `RUN+QUEUE` is now an independent settings-quality Final render; `PREVIEW 0.2MP` and `ACCEPT>1.0MP` retain their dedicated seed-reuse workflow.
- Removed the unreachable legacy upload branch that remained after the old Preview gate, leaving one authoritative ComfyUI generation path.

### Verification

- Reproduced the correction against `h3_project_young_male_influencer`: a saved 45.00-second Playhead rewinds to 0.00 and plays in Storyboard; the following `RUN+QUEUE` enters the Final generation path exactly once.
- All `299` bundled tests and all six Standard Pipeline Release Gates pass.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.4] - 2026-08-29

### Added

- Added Workspace layout 2 compact Segment storage. Every actual Render Segment now owns at most one `motion_preview.mp4` and one `approved_final.mp4`; Shot state stores portable Segment references plus Timeline and source in/out ranges.
- Added verified layout 1 migration. Legacy per-Shot Takes and `approved.mp4` aliases are removed only after their SHA-256 matches a successfully archived canonical Segment asset.
- Added relative Take paths for cross-computer project restoration and a post-save cache reclaimer that removes only an exact completed `.director_cache/generated_outputs/<kind>/<seed>` run after the Master and every Segment asset are verified inside the Workspace.
- Added Standard Pipeline Release Gate 6 covering a 45-second three-Segment/nine-Shot Preview and Final, middle-Segment rerender, unchanged outer Segments, project reload and cache cleanup.

### Changed

- Smart Render manifests now point to durable `segments/SEGMENT_ID/takes` outputs instead of disposable cache paths, preserving future reuse after cache cleanup.
- Full Preview and Final masters remain the two stable root files `generated_preview.mp4` and `generated_output.mp4`.

### Verification

- The real `h3_project_young_male_influencer` structure was exercised through a hard-linked shadow migration: 29 MP4 paths / 714.60 MB logical size became 8 MP4 paths / 244.33 MB, with all six Segment tier assets and all nine Shot references verified.
- All `298` bundled tests and all six Standard Pipeline Release Gates pass.
- Project format is `20`; Workspace layout is `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.3] - 2026-08-29

### Added

- Added a persistent `SUB OFF / SUB ON` switch beside Design Requirement and `LANG`. It defaults to off; on creates synchronized, editable subtitle Text Layers from Dialogue, Voice-over and Lyrics.
- Added a deterministic editable-speech contract. A Requirement that asks for Dialogue, Voice-over/narration or Lyrics must produce matching A-track `text_layers` with `explicit_user_requested=true`.
- Added descriptive fallback Workspace naming for non-ASCII titles. When a Chinese title cannot form an ASCII folder slug, Design now uses the first useful subject-media keyword, for example `h3_project_female_protagonist`.

### Fixed

- Reset the shipped and local Design language default to `Auto`. The previous persisted `English` selection could override a Chinese Requirement before Qwen was called.
- Dialogue and narration can no longer be hidden as English quotations inside Shot instructions. Missing editable speech tracks or wrong-language generated lines are rejected and retried once; Apply remains blocked if the retry still violates the contract.
- With subtitles off, AI-invented caption layers and theme hashtags are removed deterministically. Explicitly requested non-subtitle title/on-screen text remains supported.
- Preview and final publication now maintain only the stable user-facing Workspace masters `generated_preview.mp4` and `generated_output.mp4`; assembled full-length masters are no longer duplicated into an additional render-take history. Per-Shot Takes remain intact for editable Smart Render.
- Portable project reload now prefers the matching root Preview/Final master.

### Verification

- Added regressions for missing Voice-over tracks, speech hidden in Shot prose, subtitle off/on behavior, Auto language UI state, setting persistence and non-ASCII project naming.
- All `293` bundled tests and all five Standard Pipeline Release Gates pass.
- Project format remains `19`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.2] - 2026-08-29

### Added

- Added a compact `LANG` selector beside the Design Requirement dialogue-engine buttons with Auto plus MiniMax H3's 11 stably supported dialogue languages: Arabic, Chinese, English, French, German, Italian, Japanese, Korean, Portuguese, Russian and Spanish.
- Added persistent `H3_DESIGN_DIALOGUE_LANGUAGE` storage in `design_ai.env`.

### Fixed

- Auto language now deterministically resolves explicit language wording and the requirement's writing system before the LM request; a Chinese requirement therefore defaults generated dialogue to Chinese instead of English.
- Design planning and BLIP refinement now receive a mandatory dialogue-language contract. Generated Dialogue, Voice-over and Lyrics with an obvious wrong language/script are rejected and retried once instead of silently reaching Apply.
- Exact user-authored words remain protected and are never translated by the new language selector.

### Verification

- Added language-catalog, automatic-detection, wrong-script rejection, prompt-contract, setting-round-trip and Design UI regressions.
- All `289` bundled tests and all five Standard Pipeline Release Gates pass.
- Project format remains `19`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.1] - 2026-08-29

### Changed

- Reordered the Generation Work Area controls as: Work Area, Aspect, Export API, ComfyUI address, Test Connect, Run+Queue, Storyboard, Preview 0.2MP, Accept 1.0MP, Reject and Estimate.
- Replaced the long quality selector with direct `STORYBOARD`, `PREVIEW 0.2MP` and `ACCEPT>1.0MP` actions while retaining the same persisted quality-profile state.
- Compacted `EXPORT ACTIVE API`, `TEST CONNECTION` and `UPLOAD + QUEUE` to `EXPORT API`, `TEST CONNECT` and `RUN+QUEUE`; full descriptions remain available through hover tooltips.

### Verification

- Added a toolbar-order regression covering all eleven requested control groups, compact labels, hover descriptions, hidden persisted quality state and direct Storyboard activation.
- All `286` bundled tests and all five Standard Pipeline Release Gates pass.
- Project format remains `19`; Smart Render policy remains `11`.

## [0.3.1-alpha.1] - 2026-08-29

### Added

- Added the first budget-aware long-form production foundation: one project now owns one stable Workspace containing project snapshots, Design revisions, imported and generated media, audio, Shot Takes, Preview/Final renders, proxies, cache and logs.
- Added non-destructive project-format 19 migration. Opening a format 18 or older project preserves the original JSON and records it in `project_manifest.json`; future saves use `project/director_project.h3director.json`.
- Added immutable per-Shot Take state with seed, quality profile, latest Take and approved Take. Preview, accepted and final outputs are archived with hard links when possible so historical Takes do not multiply video storage.
- Added visible Storyboard, Motion Preview 0.2MP and Approved Final 1.0MP quality tiers. Approved Final requires a completed preview and reuses its seed.
- Added per-Workspace resource estimates, observed render calibration and a configurable free-disk reserve that blocks unsafe generation before TTS/H3 work starts.
- Added `V0.3.1_ACCEPTANCE_CHECKLIST.md` as the staged release contract for the 45-to-120-second and future long-form workflow.

### Changed

- Repeated Design operations now create `R####` revisions inside the same Workspace instead of timestamped top-level project folders.
- Newly loaded Media Pool sources are hard-linked or copied into `media/imported`; legacy sources remain untouched until explicitly replaced.
- Preview and final masters use separate render directories while root-level compatibility links remain available to older scripts and portable projects.

### Verification

- Project Workspace, portable relocation, legacy preservation, quality-tier dispatch, resource calibration, Shot Take persistence and Settings `.env` round-trip regressions are included.
- All `285` bundled tests pass. All five Standard Pipeline Release Gates pass: P/V/A mapping, post-Design Timeline reconciliation, track-kind repair, 15-second continuity without replay and backend rejection of missing/stale cross-computer media.
- Project format is `19`; Smart Render policy remains `11`.

## [0.3.0-alpha.5] - 2026-08-29

### Added

- Added `short-drama-h3-director`, a Studio-native adaptation of the MIT-licensed `POUND0423/AI-drama-pound` short-drama screenwriting workflow. The new Default-bound Special Skill adds causal conflict, planted reversals, character/prop continuity, exact authored `text_layers`, vertical composition, executable Shot budgets, reference-media planning, location sound and episode-hook validation for H3 Director Design JSON.
- Added the full Chinese mirror `SKILL.cn.md` and retained the upstream MIT notice in `THIRD_PARTY_LICENSE.txt`.
- Added `SPECIAL SKILL CREATOR` beside the Default and Special selectors. It can create or edit English/Chinese Special Skill files, choose `Default + Special` or Standalone binding, validate metadata and instructions, then reload and apply the saved Skill without restarting Studio.
- Added automatic storage, binding, bilingual-content, attribution and toolbar regressions for the new Skill workflow.
- Added a two-round Design regression proving that loaded P1–P3 remain stable, first-round generated images occupy P4–P6, an explicit second-round `@P4` is reused, and three further generated images occupy P7–P9 without renumbering.

### Verification

- The adapted Skill passes the bundled `skill-creator` validator.
- All `276` bundled tests pass, including the new Skill storage/binding/bilingual-attribution checks, Creator toolbar assertion and two-round Media Pool allocation regression. All five Standard Pipeline Release Gates pass.
- Project format remains `18` and Smart Render policy remains `11`.

## [0.3.0-alpha.4] - 2026-08-29

### Changed

- Restored the compact legacy Media Pool header proportions while retaining Virtual Media Pool support.
- Reduced the header typography and padding, compacted logical/Segment totals, and replaced `+ IMAGE / + VIDEO / + AUDIO` with same-row `+I / +V / +A` buttons. Full descriptions remain available through hover tooltips.

### Verification

- Added UI assertions for the compact labels, fixed 30px controls and reduced header typography together with the fixed three-column material grid.
- All `94` Timeline/UI tests and all five Standard Pipeline Release Gates pass.
- Project format remains `18` and Smart Render policy remains `11`.

## [0.3.0-alpha.3] - 2026-08-29

### Changed

- Media Pool now uses exactly three material cards per complete row. Resizing the panel changes card width without silently increasing the grid to four or more columns.

### Verification

- Updated the Media Pool UI regression to require columns `0, 1, 2` at default, narrow and wide panel sizes.
- All `94` Timeline/UI tests and all five Standard Pipeline Release Gates pass.
- Project format remains `18` and Smart Render policy remains `11`.

## [0.3.0-alpha.2] - 2026-08-29

### Changed

- Media Pool now opens in a three-column layout by default, using larger cards for easier visual identification.
- Responsive reflow remains enabled: a narrow panel can use two columns, while widening the panel continues to add columns automatically.

### Verification

- Added a UI regression assertion for the default three-column layout while retaining narrow- and wide-panel reflow coverage.
- All `94` Timeline/UI tests and all five Standard Pipeline Release Gates pass.
- Project format remains `18` and Smart Render policy remains `11`.

## [0.3.0-alpha.1] - 2026-08-29

### Added

- Promoted cross-computer missing-media protection into the independent fifth mandatory Standard Pipeline Release Gate.
- Gate 5 now verifies PNG/WEBP pictures, WAV/other audio and MP4/other video across both ordinary Preview/Run and Smart Render. A missing local source must stop before upload, `/object_info` or `/prompt`, and inactive LoadImage/LoadAudio/LoadVideo nodes containing stale paths from another computer must be absent from the compiled Segment workflow.

### Verification

- All five mandatory Standard Pipeline Release Gates pass.
- All `14` bundled test modules pass independently: `269 tests` total. The Program Monitor Qt Multimedia smoke test also passes when rerun directly.
- Project format remains `18` and Smart Render policy remains `11`; this patch adds release verification and documentation without changing saved-project compatibility or render-cache semantics.

## [0.3.0-alpha] - 2026-08-29

### Added

- Introduced the unlimited Virtual Media Pool. Projects may now own stable `P10+`, `V4+` and `A4+` logical sources while the existing ComfyUI workflow remains the per-Segment execution backend with 9 image, 3 video and 3 audio loader templates.
- Added `+ IMAGE`, `+ VIDEO` and `+ AUDIO` controls to the Media Pool. AI Director Design and authored TTS also create a new logical source automatically when every original workflow card is occupied.
- Added deterministic Segment allocation: active logical sources are sorted by permanent `P/V/A` identity, assigned to free physical loaders, uploaded under collision-safe names and compiled into request-local H3 ordinals. Permanent Media Pool IDs never change when a physical loader changes.
- Added pre-generation capacity validation. The project library is unlimited, but a time interval that exceeds the current workflow's physical 9/3/3 Segment capacity is rejected with the exact interval and media type before Z-Image/TTS/H3 work begins.

### Changed

- Design planning no longer treats empty workflow Loader cards as a project-wide generation ceiling. Long designs can create different reference sets for later Segments, and the Design prompt now distinguishes unlimited logical media from per-Segment physical capacity.
- Smart Render continuity reserves its 24-frame motion loader after dynamic allocation and, when necessary, releases only one eligible automatic video reference for that request. User references and the hidden continuity video cannot collide.
- Director Project format is now `18`, persisting logical source type, permanent reference ID and virtual-source status. Existing format-17 projects remain loadable; v0.3 projects containing P10+/V4+/A4+ require this or a later Studio version.
- Smart Render policy version is now `11`, invalidating Segment caches compiled with physical-loader-owned media identity.

### Verification

- Expanded Standard Pipeline Release Gate 1 to compile and validate P10, V4 and A4 together with sparse legacy P7/V2/A3 references, including copied-file rebasing, upload manifests and physical Loader alignment.
- Added virtual-pool regressions for per-Segment P10/V4/A4 remapping, more-than-nine overlapping-image rejection, repeated logical sources and format-18 project save/reload.
- All four mandatory Standard Pipeline Release Gates pass. The complete bundled suite passes `268` tests.

## [0.2.6-alpha.2] - 2026-08-28

### Fixed

- Removed inactive image, audio and video loader branches from every compiled H3 request, so an old computer's ComfyUI `input` filename can no longer leak into a reopened project's Preview/Run. This specifically fixes stale `authored_timeline_dialogue_*.wav` warnings when Ori / MiniMax H3 Native Dialogue is selected.
- Added a universal pre-Queue portability check for every retained `LoadImage`, `LoadAudio` and `LoadVideo`: each must resolve to a real local file, appear in the upload manifest and use the current deterministic upload name. Missing copied media is reported before ComfyUI generation instead of surfacing later as a background `[Errno 2]` warning.
- Preserved Smart Render's dedicated runtime video loader for the preceding silent 24-frame continuity tail while removing all other inactive loaders. Continuity injection therefore remains compatible with the stricter portability rules.
- Smart Render policy version is now `10`; old compiled Segment cache entries cannot bypass the new loader policy.

### Verification

- Expanded the first mandatory Standard Pipeline Release Gate to simulate a project copied from an unavailable old drive and verify local rebasing, upload rewriting and missing-file rejection for pictures, WAV/audio and MP4/video.
- Added an explicit Ori regression proving an old absolute `authored_timeline_dialogue_30.00s.wav` path and its loader are absent from the compiled request.
- All four Standard Pipeline Release Gates pass. The complete bundled suite passes `265` tests, including all long-render mapping, repeated-media, packed-shot, local-Segment edit and 24-frame continuity regressions.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.6-alpha.1] - 2026-08-28

### Changed

- Rebuilt authored speech as visible Timeline Type clips instead of hidden text appended to visual Shot prompts. Dialogue, Voice-over and Lyrics now remain independently editable on `A4 Dialogue`, `A5 Voice-over` and `A6 Lyrics`; On-screen Text remains on a V track.
- Changing a Type clip's Content Role automatically moves it to the matching visual/audio track. Loading an older project now repairs Dialogue clips previously mutated onto V tracks back to their correct A track.
- H3 prompt compilation now emits one independent, time-coded `TIMELINE TYPE / DIALOGUE TRACK EVENTS` contract. Exact text is emitted only once and is no longer duplicated inside Shot Action prose, reducing Ori paraphrase, omission and repeated-line pressure.
- Each hidden Segment receives only the Type/Dialogue events it owns. Editing the clip text, timing, Speaker, Language, Delivery or Lip Sync continues to invalidate the affected render range and regenerate the current Ori prompt automatically.
- Smart Render policy version is now `9`, so cached Segments compiled with the former Shot-embedded dialogue policy are not reused.

### Verification

- Added regression coverage for old V-track Dialogue migration, visible `DIA` clips on `A4 Dialogue`, independent timed-dialogue prompt compilation and single-occurrence exact text.
- The complete bundled test suite passed: `265` tests. All four Standard Pipeline Release Gates passed.
- Director Project format remains version `17`; existing projects are migrated in memory and need no manual JSON edit.

## [0.2.6-alpha] - 2026-08-28

### Release

- Promoted the latest Director Cut Studio build to `v0.2.6-alpha`.
- This alpha includes visible-scene-driven spatial acoustics, production ambience/Foley/music mixing, natural on-location dialogue treatment, safe LM Studio model replacement/unload handling, and the expanded Segment-mapping Release Gate.
- The complete bundled test suite passed: `263` tests. All four Standard Pipeline Release Gates and all ten Timeline mapping-matrix regressions passed.
- Director Project format remains version `17`; existing projects require no migration.

### Documentation

- Updated README highlights, LM Studio setup and `.env` examples to use the live model alias instead of a deleted quantized GGUF path.
- Documented the three-layer Production Mix, visible-space Reverb/Echo profiles, acoustic inheritance across cuts, Segment-local sound schedules and their isolation from P/V/A mapping.
- Added troubleshooting for LM Studio `model_not_found`, automatic model-family fallback/unload behavior, spatial-acoustics rerendering and the expanded `263`-test Release Gate.

## [0.2.5-alpha.9.6.1] - 2026-08-28

### Verification

- Expanded the mandatory fourth Release Gate with a spatial-audio/Segment-mapping cross-test covering three native windows with small-room, large-hall and open-exterior acoustic profiles.
- Changing only the middle Shot from a large hall to a corridor changed only the middle Segment fingerprint. All request-local image/video/audio bindings, physical H3 reference inputs, effective tags and 24-frame continuity metadata remained byte-for-byte equivalent across the acoustic edit.
- Verified that room profiles and their time ranges remain Segment-local: small-room, large-interior, open-exterior and corridor acoustics do not leak into adjacent native windows.
- All four Standard Pipeline Release Gates passed, followed by all ten Timeline mapping-matrix regressions. The complete `263`-test suite from `0.2.5-alpha.9.6` remains valid because this patch adds verification coverage only and does not change production code.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9.6] - 2026-08-28

### Added

- Added deterministic, visible-scene-driven spatial acoustics for small reflective rooms, furnished rooms/offices, medium interiors, large halls, corridors/stairwells, caves/tunnels, vehicle cabins, covered semi-outdoor spaces and open exteriors.
- Every generated Soundscape now contains a time-scoped `Spatial acoustics contract` with space-appropriate decay, early-reflection character and restrained wetness. Every Shot also receives its own `SHOT SPATIAL ACOUSTICS` execution rule for dialogue, Foley and ambience.
- Acoustic spaces persist across close-up/cut changes when no location change is visible, then crossfade only when a later Shot explicitly enters a different space.

### Changed

- Small furnished rooms use close, brighter 0.18-0.45s reflections; large interiors use controlled 0.9-1.8s tails; corridors and caves receive directional returns rather than generic wash.
- Open exteriors use nearly dry 0-0.15s acoustics, no discrete echo and slightly reduced low-mid/proximity fullness, allowing distance, wind and open-air diffusion to replace indoor body.
- Covered stalls and awnings use only short 0.12-0.32s roof/counter/wall reflections while their open street-facing side remains free of an enclosed-room tail.
- The obsolete auto-authored `no artificial reverb tails` phrase is removed from older Design soundscapes before recompilation. Physically plausible acoustic reflections are now explicitly distinguished from duplicated or repeated dialogue performances.
- Time-local Segment audio planning now carries actual Shot start/end times, framing, camera angle and continuity evidence into the acoustic schedule.

### Verification

- Recompiled the reported `rainy_night_confession_20260828_095847_902149` sound design as one continuous `0.00-5.00s covered semi-outdoor space`; the former contradictory no-reverb direction is absent.
- Added regressions for room-size profiles, outdoor de-fullness, covered-space reflections, acoustic location changes, same-location inheritance, legacy no-reverb cleanup and per-Shot/Release-Gate prompt presence.
- The complete bundled test suite passed: `263` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9.5] - 2026-08-28

### Fixed

- LM Studio generation now validates a saved model ID against the live `/v1/models` catalogue. If the GGUF was deleted or replaced, Studio selects the closest available model family/alias and persists the repaired selection instead of repeatedly using the stale path.
- Test Connection now replaces an unavailable editable model value with the resolved live model rather than silently retaining text that is absent from the discovered model list.
- LM Studio cleanup now unloads only instance IDs explicitly reported in `loaded_instances`; an unloaded or deleted saved model is already considered released and no longer causes repeated `model_not_found` requests.
- Saved full GGUF paths and LM Studio's shorter model aliases are matched safely during cleanup, while unrelated models with similar basenames remain isolated.
- Media Pool AI Semantic Enrichment receives and persists the same resolved LM Studio model, so Design and background enrichment cannot drift onto different stale identifiers.

### Verification

- Verified against the configured live LM Studio server at `192.168.0.185:1234`: 28 models were discovered and the deleted/stale GGUF path resolved to `qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp`.
- Added regressions for deleted models, unloaded catalogue entries, quantized-family fallback, full-path-to-alias cleanup and unrelated-model isolation.
- The complete bundled test suite passed: `261` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9.4] - 2026-08-28

### Added

- Added a universal three-layer production-audio contract to every Design and Timeline render: continuous diegetic location ambience, exact-frame contact Foley/one-shot SFX, and foreground authored speech.
- Added automatic story-aware non-diegetic music when the field is blank, plus a stable mix contract that keeps music audible between lines and transitions while ducking it beneath dialogue and important diegetic effects.
- Every Shot now receives an executable sound instruction requiring continuous location tone and physically caused, perspective-correct Foley/SFX with natural decay.

### Changed

- Native H3 Dialogue is now directed as live on-location production sound with conversational timing, natural breath and micro-pauses, camera-distance perspective, subtle early reflections and low environmental bleed instead of a dry announcer or studio voice-over.
- VoxCPM2 Voice Design now favors organic on-location film performance, restrained everyday projection and phrasing-driven emotion; Edge TTS applies a small delivery-aware rate/pitch adjustment instead of one fixed cadence.
- VoxCPM2/Edge authored WAVs are now classified as clean dialogue stems rather than finished soundtracks. H3 preserves their exact wording, speaker identity, timing and phoneme rhythm while spatializing them and generating ambience, Foley/SFX and ducked music around them.
- The Timeline TTS signature now includes the `on_location_production_v1` voice policy, so an older dry authored WAV is rebuilt automatically before Preview/Run.

### Verification

- Added regressions for sound/music contract idempotence, story-aware Foley and score selection, on-location VoxCPM instructions, native and supplied-dialogue spatialization, and authored-TTS stem retention semantics.
- Expanded the mandatory fourth Release Gate to require the production-mix, music-mix and per-Shot sound contracts in every native Segment prompt.
- The complete bundled test suite passed: `258` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9.3] - 2026-08-28

### Fixed

- Hidden Segment prompts now filter project-global time-scoped visual style, reference rules, soundscape, music, constraints, technical rules and ending directions to the active render window, then rebase retained ranges onto the Segment's local clock.
- Earlier and later phases are removed from the executable Segment prompt instead of being reinterpreted from local `00:00`; this prevents a later Shot from blending an earlier location, lighting state, ambience or music phase into its opening frames.
- Segment prompts now state that the retained timed phase overrides incompatible untimed modifiers and that only subjects, locations, props, lighting states and actions present in the local Shots or active references may become visible.
- Smart Render policy version is now `8`, invalidating cached Segments compiled with the older leaking prompt policy while leaving the saved Director Project schema unchanged.

### Verification

- Added deterministic parser regressions for English numeric ranges, clock timecodes, point events, partial-window clipping, year-range safety and removal of off-window phases.
- Expanded the mandatory fourth Release Gate to verify that visual style, soundscape, music and constraint schedules never leak across native 15-second boundaries.
- Recompiled the reported `ai_design_20260828_014726_319700` final 25-30s window: P6 remains the sole active image, physical node `154` remains request-local `<Picture 1>`, the previous 24 frames remain `<Video 1>`, and the cotton-field schedule is absent from the final Segment prompt.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9.2] - 2026-08-27

### Fixed

- Reopened long projects now patch every physical image/video/audio loader in every Segment to its collision-safe ComfyUI upload name. Inactive H3 references remain disconnected, but ComfyUI validation no longer reports misleading missing original basenames for orphan loader widgets.
- Portable project loading now rebases missing absolute media paths against the loaded project folder, including paths relative to the former `example_work_dir` and unambiguous nested matches. A recovered local file is no longer overwritten by the stale saved absolute path.
- Reopened projects continue saving beside the project that was actually opened instead of writing into an old work folder from another machine or drive.
- Regular and Smart Render workers now stop before queueing when a declared local reference is genuinely missing, with an actionable re-link error instead of silently skipping its upload.

### Verification

- Added regressions for all-loader Segment patching, portable nested-media rebasing and missing-reference preflight.
- Thirty-three relevant workflow, Smart Render, portable-project and project-round-trip regressions passed.
- The mandatory four-part Standard Pipeline Release Gate passed: sparse P/V/A executable mapping, post-Design Timeline reconciliation, V/A track-kind integrity, and native 15-second 24-frame continuity without replay or slot collision.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9.1] - 2026-08-27

### Changed

- VoxCPM2 now unloads immediately after the final source utterance WAV is written, before FFmpeg Timeline composition begins, so the multi-gigabyte model is not retained during audio post-processing.
- Model release is explicit and idempotent: it drops model references, runs Python garbage collection, clears CUDA cache/IPC, and reports both the unloading and released stages. All success and exception paths still terminate the isolated worker, allowing Windows to reclaim any remaining VRAM and DRAM.

### Verification

- Five focused provider lifecycle regressions passed, covering Timeline composition, CUDA-load fallback, CUDA-inference fallback, missing-model validation and idempotent model release.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9] - 2026-08-27

### Fixed

- VoxCPM PyPI `2.0.3` compatibility: Studio no longer passes the unsupported `seed=` keyword to `VoxCPM._generate()`. The isolated worker seeds Python, NumPy and Torch RNGs before each line, preserving deterministic Speaker voices across both the PyPI and newer GitHub APIs.
- A Design-authored TTS failure no longer leaves a new project with an empty Timeline. Studio commits the planned Shots, visual materials and exact Text Layers, excludes the failed/silent Audio placeholder, and marks authored speech stale so the user can switch to `Etts` and rebuild on Preview/Run without loading the Design JSON again.
- CPU fallback progress now retains the CUDA failure reason instead of immediately overwriting it with a generic `loading model on cpu` message.

### Verification

- Added regressions for the seedless VoxCPM 2.0.3 API and recoverable Design Apply after authored TTS failure.
- A project-local VoxCPM2 CPU smoke run loaded the complete model and entered waveform inference without the previous `unexpected keyword argument 'seed'` exception; the long CPU benchmark was then stopped intentionally.
- The complete bundled test suite passed: `250` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.8] - 2026-08-27

### Added

- Added one explicit project-local VoxCPM2 weight location: `models/VoxCPM2/`. Large weights are excluded from GitHub and the bundled `ai_libraries_common` runtime so users can download them separately.
- Design highlights the `Vox` button and shows a `VOXCPM2 MODEL MISSING` panel when the required snapshot is absent or incomplete.
- Main Settings now displays a persistent ready/missing VoxCPM2 model status with the exact expected path and missing files.
- Apply, Preview and Run now preflight the local snapshot before reserving or rebuilding authored speech.

### Changed

- The VoxCPM2 worker no longer resolves `openbmb/VoxCPM2` through a hidden Hugging Face cache and never downloads model weights during generation.
- Added `models/README.md` with the accepted weight and AudioVAE filename alternatives; `.gitignore` retains the instructions while excluding downloaded weights.

### Verification

- Added regression coverage for the missing-model worker guard and both highlighted UI entry points.
- The complete bundled test suite passed: `249` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.7] - 2026-08-27

### Changed

- VoxCPM2 Local `auto` mode now attempts explicit CUDA whenever the bundled PyTorch runtime reports CUDA availability; the previous automatic CPU selection below 8 GB VRAM has been removed.
- If CUDA fails while loading VoxCPM2 or while synthesizing a dialogue line, the isolated worker releases the model and CUDA cache, reloads on CPU and retries the same line automatically.
- Runtime progress now identifies the attempted device, the ready device and any CUDA-to-CPU fallback stage.

### Verification

- Added regressions for CUDA model-load failure and CUDA inference failure, including exact CPU retry behavior.
- The complete bundled test suite passed: `248` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.6] - 2026-08-27

### Added

- Added three exclusive Dialogue mode buttons beside `DESIGN REQUIREMENT`: `Ori` (MiniMax H3 Native Dialogue), `Vox` (VoxCPM2 Local) and `Etts` (Edge TTS).
- Added `h3_native` as the persistent Settings／`.env` mode and made it the safe default for new workspaces.
- Switching an Ori Design to Vox／Etts from Timeline Settings now reserves an empty physical Audio slot, builds the authored WAV and restores it to Timeline automatically before Preview／Run.

### Changed

- The Design button choice is applied to the current project and persisted to `.env`; users can still override it later from the main Settings page without reopening Design.
- Ori mode explicitly bypasses and disables any previous authored-speech WAV while retaining the editable Text Layers for native H3 dialogue generation.
- Vox／Etts mode restores a deleted Timeline authored-speech clip when its reusable Media Pool source remains, or creates a fresh authored Audio reference when a free slot exists.

### Verification

- Added regressions for the three Design buttons, native default validation, Ori-to-Vox Audio reservation and native exclusion of an old TTS reference.
- The complete bundled test suite passed: `246` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.5] - 2026-08-27

### Added

- Qwen Design planning now assigns female on-screen speakers to `S1` and male on-screen speakers to `S2`, keeps the identity stable across Shots, and preserves an explicit user Speaker override.
- Added automatic diegetic ambience and contact-foley planning, with dialogue foregrounding and background/music ducking instructions.

### Fixed

- Exact-text protection no longer overwrites Qwen's valid gender-aware Speaker assignment with default `S1`.
- Editing Timeline Dialogue, Voice-over or Lyrics now makes the previous authored WAV stale, rebuilds it through the selected Edge/VoxCPM2 provider, refreshes the Shot/H3 Prompt, and prevents generation from resuming with an intermediate obsolete WAV.
- Preview and Run automatically enable, un-bypass and unmute the generated authored-speech Audio reference; if other A Tracks are soloed, the speech track joins the solo set.
- The current Timeline text becomes the updated authored-text contract after an intentional edit, so validation protects the edited words instead of demanding the superseded Design wording.

### Verification

- Added regressions for gender-aware Speaker preservation, explicit Speaker priority, automatic soundscape generation, edited-dialogue TTS invalidation/signatures and authored A Track recovery.
- The complete bundled test suite passed: `244` tests.
- Director Project format remains version `17`; no saved-project migration is required.

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

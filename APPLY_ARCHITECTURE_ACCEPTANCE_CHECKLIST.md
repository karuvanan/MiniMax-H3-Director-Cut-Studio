# Apply Architecture Upgrade · Acceptance Checklist

This checklist is the release contract for the transactional AI Design → H3 Workspace Apply path. A predictable planning problem must never produce a chain of modal dialogs or make the Design page disappear before the Workspace commit succeeds.

## Apply lifecycle

- [x] `VALIDATE JSON` produces one aggregated `APPLY PREFLIGHT REPORT` with `AUTO-FIX`, `WARNING` and `HARD BLOCK` counts.
- [x] Auto-fixes are written into normalized Director Design JSON and recorded in `design_warnings`.
- [x] Warnings remain visible in the Design page and do not disable Apply.
- [x] Hard Blocks are shown in the Design page instead of a modal popup chain.
- [x] Clicking Apply disables duplicate submission and keeps the Design page open while Timeline, TTS, image generation and Workspace materialization run.
- [x] The Design page closes only after `_commit_ai_design` has durably updated Timeline and Workspace state.
- [x] A synchronous or asynchronous failure returns the Design page to an editable/retryable state.
- [x] Successful Apply warnings use the status bar/preflight report rather than a second modal popup.

## Seventeen predictable blocker families

| # | Input / runtime condition | Policy | Acceptance result |
|---|---|---|---|
| 1 | Invalid JSON syntax or non-object root | **Hard Block** | One inline parse error; editor remains open. |
| 2 | Explicit duration differs from returned Design | **Auto-fix** | Scale all Shot/Text/Media/Cue times onto the explicit duration on the 0.5s grid. |
| 3 | Missing Creative Brief or Visual Style | **Auto-fix** | Recover Brief from requirement/title and insert a safe cinematic style. No executable Shots remains a Hard Block. |
| 4 | Camera Shots overlap | **Auto-fix** | Move to a common 0.5s cut; if two cells cannot fit, merge actions/states into one Shot. |
| 5 | Exact authored Dialogue/VO/Lyrics/On-screen Text is lost | **Hard Block** | Restore from authored requirement where deterministic; otherwise stop inline and retain JSON. |
| 6 | Dialogue language/script mismatch | **Warning** | Preserve editable Text Layers, highlight mismatch, never silently rewrite exact words. |
| 7 | Unsafe Z-Image prompt | **Auto-fix** | Rebuild as a standalone in-world frozen production frame without H3 Picture tokens/dependent frames/blank studio action backgrounds. |
| 8 | Invalid P/V/A identifier or media type mismatch | **Hard Block** | Report the exact logical ID/type conflict inline. |
| 9 | Referenced Media Pool file absent, empty or wrong type | **Hard Block** | Explicit real references cannot be fabricated; retain editor for relink/removal. |
| 10 | Duplicate `requirement_id` | **Auto-fix** | Deterministically suffix duplicate occurrences while preserving order and ranges. |
| 11 | Model selected a disabled asset or ignored explicit `@P/@V/@A` | **Auto-fix / Hard Block** | Remove non-explicit disabled selections; missing/disabled explicit user references remain Hard Block. |
| 12 | Logical request exceeds available API capacity | **Hard Block** | Report type/count before materialization; Virtual Pool itself remains unlimited. |
| 13 | One Segment exceeds physical 9 Image / 3 Video / 3 Audio | **Hard Block** | Report the exact interval, type and unique count before Queue. |
| 14 | TTS needs an Audio slot but all three are occupied | **Warning** | Preserve exact Text Layers, defer WAV, mark Timeline TTS stale; do not create a silent placeholder. |
| 15 | VoxCPM2 selected but model files are missing | **Warning** | Preserve Text Layers, defer Vox WAV and highlight model requirement; Apply remains available. |
| 16 | ComfyUI/TTS/image worker busy or stopping | **Retryable Hard Block** | Inline execution-state report; no duplicate job and no closed Design page. |
| 17 | Workspace/FFmpeg/filesystem/unexpected runtime failure | **Hard Block** | One inline error, rollback/no false success, Design page remains open for retry. |

## Non-regression gates

- [x] Existing `.h3director.json` files remain loadable; no project-format migration is required.
- [x] Media Mapping, Segment 9/3/3 packing and 24-frame context rules are unchanged.
- [x] Failed Vox/Edge TTS still commits exact Text Layers without a silent audio placeholder when the visual plan is otherwise valid.
- [x] Failed Z-Image generation still commits labeled placeholders and warnings when the Timeline plan is otherwise valid.
- [x] Standard Pipeline Release Gate 8 covers safe repair, no modal Apply chain, failure retry and close-after-success behavior.
- [x] Complete bundled automated suite passes: `362` tests on 2026-08-31.
- [x] All eight Standard Pipeline Release Gates pass independently.

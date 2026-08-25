# Changelog

Every user-visible correction receives an application version and a dated entry in this file. Application versions follow Semantic Versioning pre-release notation. The `.h3director.json` project-format version is maintained separately and changes only when the saved schema changes.

## [0.1.0-alpha.5] - 2026-08-26

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

## [0.1.0-alpha.4] - 2026-08-25

### Fixed

- Resynchronized the Track Header vertical offset after project loading, dynamic V-track creation and header rebuilding. Picture clips with valid V-track IDs can no longer appear visually aligned with A1/A2/A3 labels because the two panes retained different scroll positions.

### Verification

- `162` automated tests passed with the bundled Python environment.

## [0.1.0-alpha.3] - 2026-08-25

### Fixed

- Gave the Timeline Tools palette a DPI-aware minimum width based on its longest button and scrollbar, so every icon keeps its visible Selection/Hand/Razor/Shot/Type/Prompt/Transition/Marker label even when the splitter is dragged left.

### Verification

- `161` automated tests passed with the bundled Python environment.

## [0.1.0-alpha.2] - 2026-08-25

### Added

- Allowed AI Design plans to create and populate editorial tracks beyond V3/A3 (up to V16/A16), including separate visual title and dialogue/voice-over/lyrics lanes.
- Added automatic cross-segment motion context using exactly the preceding 24 frames at 24 fps, without carrying prior audio.
- Added strict single-colour, edge-connected background detection and non-destructive transparent PNG derivatives for Media Pool and Design-generated images.

### Changed

- Reserved one of the three physical H3 video reference inputs for hidden continuity when possible; if all are occupied, the least-specific Auto reference is released for that segment while force-active references remain untouched.
- Raised the Smart Render policy version to `6`, invalidating older segment manifests whose continuity assumptions are no longer safe to reuse.

### Verification

- `161` automated tests passed with the bundled Python environment.

## [0.1.0-alpha.1] - 2026-08-25

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

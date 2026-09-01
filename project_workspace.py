"""Fixed project Workspace, Shot Take and resource-budget helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import time
import uuid


WORKSPACE_LAYOUT_VERSION = 2
WORKSPACE_DIRECTORIES = (
    "project",
    "design/revisions",
    "media/imported",
    "media/generated_references",
    "media/audio",
    "shots",
    "segments",
    "renders/preview",
    "renders/final",
    "proxies",
    "cache",
    "logs",
)


@dataclass(frozen=True, slots=True)
class QualityProfile:
    key: str
    label: str
    megapixels: float
    enable_rtx_vsr: bool
    requires_h3: bool
    requires_accepted_seed: bool
    default_gpu_seconds_per_output_second: float
    default_bytes_per_output_second: int


QUALITY_PROFILES = {
    "storyboard": QualityProfile(
        "storyboard",
        "Storyboard · instant · no H3",
        0.0,
        False,
        False,
        False,
        0.0,
        0,
    ),
    "motion_preview": QualityProfile(
        "motion_preview",
        "Motion Preview · 0.2MP",
        0.2,
        False,
        True,
        False,
        20.0,
        2 * 1024**2,
    ),
    "approved_final": QualityProfile(
        "approved_final",
        "Approved Final · 1.0MP",
        1.0,
        True,
        True,
        True,
        80.0,
        7 * 1024**2,
    ),
}


@dataclass(slots=True)
class ResourceEstimate:
    profile: str
    total_duration_seconds: float
    reusable_duration_seconds: float
    render_duration_seconds: float
    shot_count: int
    segment_count: int
    gpu_seconds: float
    additional_disk_bytes: int
    free_disk_bytes: int
    reserve_disk_bytes: int
    calibrated: bool

    @property
    def fits_disk_budget(self) -> bool:
        return (
            self.free_disk_bytes - self.additional_disk_bytes
            >= self.reserve_disk_bytes
        )

    @property
    def gpu_minutes(self) -> float:
        return self.gpu_seconds / 60.0


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify_project_name(value: str, fallback: str = "h3_project") -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._-")
    return normalized[:80] or fallback


def workspace_folder_name(value: str, fallback: str = "h3_project") -> str:
    """Create a Windows-safe Workspace folder name while preserving Unicode."""
    normalized = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", str(value or ""))
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip(" ._")
    return normalized[:80].rstrip(" ._") or fallback


def picture_overview_project_name(recognition: str) -> str:
    """Return a Workspace name from the first Picture's BLIP Overview."""
    text = str(recognition or "")
    patterns = (
        r"^BLIP\s*[·-]?\s*Overview\s*[:：]\s*(.+)$",
        r"^BLIP\s+visual\s+caption\s*[·-]?\s*full\s+frame\s*[:：]\s*(.+)$",
        r"^Overview\s*[:：]\s*(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.M)
        if match:
            caption = " ".join(match.group(1).strip().split())
            if caption:
                return workspace_folder_name(caption, "")
    return ""


def design_requirement_project_name(requirement: str) -> str:
    """Choose the first meaningful story sentence from a Design Requirement."""
    text = str(requirement or "").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in text.split("\n") if line.strip()]
    for line in lines:
        title = re.match(
            r"^(?:project\s+name|title|项目名称|項目名稱|题目|題目|标题|標題)\s*[:：]\s*(.+)$",
            line,
            re.I,
        )
        if title and title.group(1).strip():
            return workspace_folder_name(title.group(1).strip())
    candidates: list[str] = []
    for line in lines:
        content = re.search(
            r"(?:故事内容|故事內容|剧情内容|劇情內容|内容是|內容是)\s*[:：]?\s*(.+)$",
            line,
            re.I,
        )
        if content and content.group(1).strip():
            story_text = content.group(1).strip()
            first_story_sentence = next(
                (
                    part.strip(" -—:：")
                    for part in re.split(r"(?<=[。！？.!?])\s*", story_text)
                    if part.strip(" -—:：")
                ),
                "",
            )
            if first_story_sentence:
                candidates.append(first_story_sentence)
        candidates.extend(
            part.strip(" -—:：")
            for part in re.split(r"(?<=[。！？.!?])\s*", line)
            if part.strip(" -—:：")
        )
    for candidate in candidates:
        if re.fullmatch(r"\[?\d{1,2}:\d{2}.*", candidate):
            continue
        if _instructional_project_title(candidate):
            continue
        return workspace_folder_name(candidate)
    return "h3_project"


def _instructional_project_title(value: str) -> bool:
    """Return True when an LM copied an instruction instead of naming the story."""
    text = " ".join(str(value or "").split())
    slug = slugify_project_name(text, "").casefold()
    if not slug:
        return not bool(workspace_folder_name(text, ""))
    if "\ufffd" in text:
        return True
    compact = re.sub(r"\s+", "", text)
    chinese_instruction = bool(re.match(
        r"^(?:请|請|帮我|幫我|我想|我要|需要)?"
        r"(?:生成|创作|創作|制作|做)(?:一个|一個|一段)?"
        r"\d*(?:\.\d+)?(?:秒|分钟|分鐘)?(?:的)?(?:视频|影片|短片|短剧)",
        compact,
        re.I,
    ))
    return (
        len(slug) > 64
        or slug.startswith(("create_a_", "create_an_", "create_the_"))
        or "full-reference_video" in slug
        or "full_reference_video" in slug
        or "treat_the_current_timeline" in slug
        or chinese_instruction
        or compact.endswith("总结以下内容如下")
        or compact.endswith("總結以下內容如下")
    )


def project_name_is_provisional(value: str) -> bool:
    """Return True for generic or instruction-derived temporary Workspace names."""
    text = str(value or "").strip()
    slug = slugify_project_name(text, "").casefold()
    safe_name = workspace_folder_name(text, "")
    if safe_name and not slug and "\ufffd" not in text:
        return False
    return (
        _instructional_project_title(text)
        or slug in {"h3_project", "h3_director_project", "ai_director_design"}
        or slug.startswith("h3_project_")
    )


def _reference_keyword_project_name(plan: dict) -> str:
    """Build one compact name from the first useful generated reference request."""
    ignored = {
        "s1", "s2", "reference", "image", "scene", "shot", "picture",
        "generated", "generation",
    }
    for request in plan.get("media_requests") or []:
        if not isinstance(request, dict) or str(request.get("media_type", "image")) != "image":
            continue
        parts: list[str] = []
        for keyword in request.get("subject_keywords") or []:
            keyword_slug = slugify_project_name(str(keyword), "").lower()
            if keyword_slug and keyword_slug not in ignored:
                parts.append(keyword_slug)
        if parts:
            return "_".join(parts)[:80].strip("._-")
    return ""


def project_display_name_for_plan(plan: dict) -> str:
    """Return a stable descriptive Workspace name even when the title is non-ASCII."""
    title = str(plan.get("title", "")).strip()
    title_slug = slugify_project_name(title, "")
    if (
        title_slug
        and not _instructional_project_title(title)
        and title_slug.casefold() not in {
        "h3_project", "h3_director_project", "ai_director_design",
        }
    ):
        return title
    reference_name = _reference_keyword_project_name(plan)
    if reference_name:
        return reference_name
    brief_words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", str(plan.get("creative_brief", "")))
    ignored = {"the", "and", "with", "from", "into", "video", "second", "seconds"}
    useful = [word.lower() for word in brief_words if word.lower() not in ignored][:3]
    return "h3_project_" + "_".join(useful) if useful else "h3_project"


def workspace_manifest_path(root: str | Path) -> Path:
    return Path(root) / "project_manifest.json"


def workspace_project_path(root: str | Path) -> Path:
    return Path(root) / "project" / "director_project.h3director.json"


def ensure_workspace_layout(
    root: str | Path,
    *,
    display_name: str = "H3 Director Project",
    workspace_id: str = "",
    legacy_project_path: str | Path | None = None,
) -> dict:
    root_path = Path(root).expanduser().resolve()
    root_path.mkdir(parents=True, exist_ok=True)
    for relative in WORKSPACE_DIRECTORIES:
        (root_path / relative).mkdir(parents=True, exist_ok=True)
    manifest_path = workspace_manifest_path(root_path)
    existing: dict = {}
    if manifest_path.is_file():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            if isinstance(loaded, dict):
                existing = loaded
        except (OSError, ValueError):
            existing = {}
    now = utc_now_text()
    existing_display_name = str(existing.get("display_name") or "").strip()
    requested_display_name = str(display_name or "").strip()
    selected_display_name = existing_display_name or requested_display_name or root_path.name
    if (
        requested_display_name
        and project_name_is_provisional(selected_display_name)
        and not project_name_is_provisional(requested_display_name)
    ):
        selected_display_name = requested_display_name
    manifest = {
        "format": "h3-director-workspace",
        "layout_version": WORKSPACE_LAYOUT_VERSION,
        "workspace_id": str(
            existing.get("workspace_id") or workspace_id or uuid.uuid4().hex
        ),
        "display_name": selected_display_name,
        "created_at": str(existing.get("created_at") or now),
        "updated_at": now,
        "legacy_project_path": str(
            existing.get("legacy_project_path")
            or (Path(legacy_project_path).resolve() if legacy_project_path else "")
        ),
    }
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(manifest_path)
    return manifest


def allocate_workspace_root(parent: str | Path, display_name: str) -> Path:
    parent_path = Path(parent).expanduser().resolve()
    parent_path.mkdir(parents=True, exist_ok=True)
    stem = workspace_folder_name(display_name)
    candidate = parent_path / stem
    suffix = 2
    while candidate.exists():
        candidate = parent_path / f"{stem}_{suffix}"
        suffix += 1
    return candidate


def refine_provisional_workspace_root(
    root: str | Path,
    parent: str | Path,
    display_name: str,
) -> Path:
    """Rename an unused provisional Workspace once Design has a real name.

    Imported source media may already exist because BLIP discovers the P1
    Overview after import. Any saved project, generated reference, render, log
    or other durable file still blocks the rename, preserving open/legacy paths.
    """
    root_path = Path(root).expanduser().resolve()
    parent_path = Path(parent).expanduser().resolve()
    requested = str(display_name or "").strip()
    if (
        not requested
        or project_name_is_provisional(requested)
        or not project_name_is_provisional(root_path.name)
        or root_path.parent != parent_path
        or not root_path.is_dir()
    ):
        return root_path
    allowed_files = {"project_manifest.json", "project/resource_calibration.json"}
    durable_files = []
    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root_path).as_posix()
        if relative not in allowed_files and not relative.startswith("media/imported/"):
            durable_files.append(relative)
    if durable_files:
        return root_path
    target = allocate_workspace_root(parent_path, requested)
    # Windows/OneDrive and thumbnail scanners can retain a directory handle
    # for a few milliseconds after imported media is attached to the UI.
    # Retry the same atomic rename briefly instead of failing project setup.
    for attempt in range(6):
        try:
            root_path.rename(target)
            break
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.05 * (attempt + 1))
    ensure_workspace_layout(target, display_name=requested)
    return target.resolve()


def locate_workspace_for_project(project_path: str | Path, payload: dict) -> Path:
    """Resolve a portable Workspace without trusting an obsolete absolute path."""
    path = Path(project_path).expanduser().resolve()
    candidates: list[Path] = []
    if path.parent.name.casefold() == "project":
        candidates.append(path.parent.parent)
    candidates.append(path.parent)
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if workspace_manifest_path(resolved).is_file():
            return resolved
    # Legacy projects adopt their containing folder. The original project file
    # remains untouched; new snapshots are written below ``project``.
    return path.parent.parent if path.parent.name.casefold() == "project" else path.parent


def next_design_revision(root: str | Path) -> tuple[Path, Path, Path]:
    root_path = Path(root).resolve()
    design_parent = root_path / "design" / "revisions"
    reference_parent = root_path / "media" / "generated_references"
    audio_parent = root_path / "media" / "audio"
    design_parent.mkdir(parents=True, exist_ok=True)
    numbers = []
    for folder in design_parent.glob("R[0-9][0-9][0-9][0-9]"):
        match = re.fullmatch(r"R(\d{4})", folder.name)
        if match:
            numbers.append(int(match.group(1)))
    revision = f"R{max(numbers, default=0) + 1:04d}"
    return (
        design_parent / revision,
        reference_parent / revision,
        audio_parent / revision,
    )


def load_resource_calibration(root: str | Path) -> dict:
    path = Path(root) / "project" / "resource_calibration.json"
    if not path.is_file():
        return {"profiles": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {"profiles": {}}
    except (OSError, ValueError):
        return {"profiles": {}}


def update_resource_calibration(
    root: str | Path,
    profile: str,
    *,
    output_duration_seconds: float,
    wall_seconds: float,
    output_bytes: int,
) -> dict:
    if output_duration_seconds <= 0 or profile not in QUALITY_PROFILES:
        return load_resource_calibration(root)
    data = load_resource_calibration(root)
    profiles = data.setdefault("profiles", {})
    old = profiles.get(profile) if isinstance(profiles.get(profile), dict) else {}
    samples = max(0, int(old.get("samples", 0)))
    weight = min(0.35, 1.0 / (samples + 1)) if samples else 1.0
    gpu_rate = max(0.0, float(wall_seconds) / float(output_duration_seconds))
    byte_rate = max(0.0, float(output_bytes) / float(output_duration_seconds))
    profiles[profile] = {
        "samples": samples + 1,
        "gpu_seconds_per_output_second": (
            gpu_rate if not samples else float(old.get("gpu_seconds_per_output_second", gpu_rate)) * (1 - weight) + gpu_rate * weight
        ),
        "bytes_per_output_second": (
            byte_rate if not samples else float(old.get("bytes_per_output_second", byte_rate)) * (1 - weight) + byte_rate * weight
        ),
        "updated_at": utc_now_text(),
    }
    path = Path(root) / "project" / "resource_calibration.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return data


def estimate_resources(
    root: str | Path,
    *,
    profile: str,
    total_duration_seconds: float,
    reusable_duration_seconds: float,
    shot_count: int,
    segment_count: int,
    reserve_disk_gb: float,
) -> ResourceEstimate:
    quality = QUALITY_PROFILES.get(profile, QUALITY_PROFILES["motion_preview"])
    total_duration = max(0.0, float(total_duration_seconds))
    reusable = min(total_duration, max(0.0, float(reusable_duration_seconds)))
    render_duration = max(0.0, total_duration - reusable)
    calibration = load_resource_calibration(root)
    row = (calibration.get("profiles") or {}).get(quality.key) or {}
    calibrated = bool(int(row.get("samples", 0)))
    gpu_rate = float(
        row.get(
            "gpu_seconds_per_output_second",
            quality.default_gpu_seconds_per_output_second,
        )
    )
    byte_rate = float(
        row.get("bytes_per_output_second", quality.default_bytes_per_output_second)
    )
    # Includes master, Shot Take metadata/proxies and temporary assembly headroom.
    additional_bytes = int(max(0.0, render_duration * byte_rate * 2.5))
    usage = shutil.disk_usage(Path(root).resolve())
    return ResourceEstimate(
        profile=quality.key,
        total_duration_seconds=total_duration,
        reusable_duration_seconds=reusable,
        render_duration_seconds=render_duration,
        shot_count=max(0, int(shot_count)),
        segment_count=max(0, int(segment_count)),
        gpu_seconds=max(0.0, render_duration * gpu_rate),
        additional_disk_bytes=additional_bytes,
        free_disk_bytes=int(usage.free),
        reserve_disk_bytes=max(0, int(float(reserve_disk_gb) * 1024**3)),
        calibrated=calibrated,
    )


def normalize_shot_take_states(raw: object, shot_ids: list[str]) -> dict[str, dict]:
    source = raw if isinstance(raw, dict) else {}
    states: dict[str, dict] = {}
    for shot_id in shot_ids:
        old = source.get(shot_id) if isinstance(source.get(shot_id), dict) else {}
        states[shot_id] = {
            "shot_id": shot_id,
            "status": str(old.get("status") or "unrendered"),
            "render_profile": str(old.get("render_profile") or "storyboard"),
            "seed": old.get("seed"),
            "take_count": max(0, int(old.get("take_count", 0))),
            "latest_take": str(old.get("latest_take") or ""),
            "latest_output_path": str(old.get("latest_output_path") or ""),
            "approved_take": str(old.get("approved_take") or ""),
            "approved_output_path": str(old.get("approved_output_path") or ""),
            "latest_output_relative_path": str(
                old.get("latest_output_relative_path") or ""
            ),
            "approved_output_relative_path": str(
                old.get("approved_output_relative_path") or ""
            ),
            "segment_id": str(old.get("segment_id") or ""),
            "segment_refs": list(old.get("segment_refs") or []),
            "preview_segment_refs": list(old.get("preview_segment_refs") or []),
            "approved_segment_refs": list(old.get("approved_segment_refs") or []),
            "updated_at": str(old.get("updated_at") or ""),
        }
    return states


def write_shot_manifests(
    root: str | Path,
    shot_states: object,
    shot_ranges: dict[str, tuple[float, float]] | None = None,
) -> list[Path]:
    """Mirror canonical Shot state as small, portable JSON files.

    Layout v2 deliberately stores movies once under ``segments``.  These
    manifests make every ``shots/SHOT_ID`` folder inspectable without copying
    the same MP4 once per Shot; the Director Project remains the source of truth.
    """
    root_path = Path(root).expanduser().resolve()
    ranges = shot_ranges or {}
    source = shot_states if isinstance(shot_states, dict) else {}
    written: list[Path] = []

    def portable_refs(raw_refs: object) -> list[dict]:
        refs: list[dict] = []
        for raw_ref in raw_refs or []:
            if not isinstance(raw_ref, dict):
                continue
            ref = {
                "segment_id": str(raw_ref.get("segment_id") or ""),
                "output_relative_path": str(
                    raw_ref.get("output_relative_path") or ""
                ),
                "timeline_start_seconds": float(
                    raw_ref.get("timeline_start_seconds", 0.0)
                ),
                "timeline_end_seconds": float(
                    raw_ref.get("timeline_end_seconds", 0.0)
                ),
                "source_in_seconds": float(raw_ref.get("source_in_seconds", 0.0)),
                "source_out_seconds": float(raw_ref.get("source_out_seconds", 0.0)),
            }
            if not ref["output_relative_path"]:
                resolved = _resolved_state_path(
                    root_path, raw_ref.get("output_path"), ""
                )
                if resolved is not None:
                    ref["output_relative_path"] = _portable_path(root_path, resolved)
            refs.append(ref)
        return refs

    for raw_shot_id, raw_state in source.items():
        if not isinstance(raw_state, dict):
            continue
        shot_id = str(raw_state.get("shot_id") or raw_shot_id).strip()
        if not shot_id:
            continue
        start, end = ranges.get(shot_id, (0.0, 0.0))
        payload = {
            "format": "h3-director-shot-manifest",
            "version": 1,
            "shot_id": shot_id,
            "timeline_start_seconds": float(start),
            "timeline_end_seconds": float(end),
            "status": str(raw_state.get("status") or "unrendered"),
            "render_profile": str(raw_state.get("render_profile") or "storyboard"),
            "seed": raw_state.get("seed"),
            "take_count": max(0, int(raw_state.get("take_count", 0))),
            "latest_take": str(raw_state.get("latest_take") or ""),
            "approved_take": str(raw_state.get("approved_take") or ""),
            "latest_output_relative_path": str(
                raw_state.get("latest_output_relative_path") or ""
            ),
            "approved_output_relative_path": str(
                raw_state.get("approved_output_relative_path") or ""
            ),
            "preview_segment_refs": portable_refs(
                raw_state.get("preview_segment_refs")
            ),
            "approved_segment_refs": portable_refs(
                raw_state.get("approved_segment_refs")
            ),
            "canonical_movie_storage": "segments/SEGMENT_ID/takes",
            "updated_at": str(raw_state.get("updated_at") or utc_now_text()),
        }
        shot_root = root_path / "shots" / slugify_project_name(shot_id, "shot")
        shot_root.mkdir(parents=True, exist_ok=True)
        target = shot_root / "shot_manifest.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(target)
        written.append(target)
    return written


def normalize_segment_take_states(raw: object) -> dict[str, dict]:
    """Normalize the v2 Segment asset index without discarding future fields."""
    source = raw if isinstance(raw, dict) else {}
    states: dict[str, dict] = {}
    for raw_segment_id, raw_state in source.items():
        if not isinstance(raw_state, dict):
            continue
        segment_id = str(raw_state.get("segment_id") or raw_segment_id).strip()
        if not segment_id:
            continue
        old = dict(raw_state)
        old.update(
            {
                "segment_id": segment_id,
                "status": str(old.get("status") or "unrendered"),
                "render_profile": str(old.get("render_profile") or "storyboard"),
                "seed": old.get("seed"),
                "take_count": max(0, int(old.get("take_count", 0))),
                "latest_take": str(old.get("latest_take") or ""),
                "latest_output_path": str(old.get("latest_output_path") or ""),
                "latest_output_relative_path": str(
                    old.get("latest_output_relative_path") or ""
                ),
                "approved_take": str(old.get("approved_take") or ""),
                "approved_output_path": str(old.get("approved_output_path") or ""),
                "approved_output_relative_path": str(
                    old.get("approved_output_relative_path") or ""
                ),
                "start_seconds": float(old.get("start_seconds", 0.0)),
                "end_seconds": float(old.get("end_seconds", 0.0)),
                "core_start_seconds": float(
                    old.get("core_start_seconds", old.get("start_seconds", 0.0))
                ),
                "core_end_seconds": float(
                    old.get("core_end_seconds", old.get("end_seconds", 0.0))
                ),
                "shot_ids": [str(value) for value in old.get("shot_ids") or []],
                "updated_at": str(old.get("updated_at") or ""),
            }
        )
        states[segment_id] = old
    return states


def segment_take_relative_path(segment_id: str, profile: str) -> Path:
    """Return the sole durable movie path for one Segment and quality tier."""
    filename = (
        "motion_preview.mp4" if profile == "motion_preview" else "approved_final.mp4"
    )
    return Path("segments") / slugify_project_name(segment_id, "segment") / "takes" / filename


def _portable_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return ""


def _resolved_state_path(root: Path, absolute: object, relative: object) -> Path | None:
    relative_text = str(relative or "").strip()
    if relative_text:
        candidate = (root / Path(relative_text)).resolve()
        if candidate.is_file():
            return candidate
    absolute_text = str(absolute or "").strip()
    if absolute_text:
        candidate = Path(absolute_text).expanduser()
        if candidate.is_file():
            return candidate.resolve()
        # Recover a v2 path after copying the entire Workspace to another PC.
        lowered = [part.casefold() for part in candidate.parts]
        for marker in ("segments", "shots"):
            if marker in lowered:
                index = lowered.index(marker)
                portable = (root / Path(*candidate.parts[index:])).resolve()
                if portable.is_file():
                    return portable
    return None


def rebase_workspace_take_states(
    root: str | Path,
    segment_states: object,
    shot_states: object,
) -> tuple[dict[str, dict], dict[str, dict]]:
    """Repair saved Take paths after a Workspace is copied to another computer."""
    root_path = Path(root).expanduser().resolve()
    segments = normalize_segment_take_states(segment_states)
    shots = shot_states if isinstance(shot_states, dict) else {}

    def repair_state(state: dict) -> None:
        for prefix in ("latest", "approved"):
            path_key = f"{prefix}_output_path"
            relative_key = f"{prefix}_output_relative_path"
            resolved = _resolved_state_path(
                root_path, state.get(path_key), state.get(relative_key)
            )
            if resolved is not None:
                state[path_key] = str(resolved)
                state[relative_key] = _portable_path(root_path, resolved)
        for refs_key in (
            "segment_refs", "preview_segment_refs", "approved_segment_refs"
        ):
            repaired: list[dict] = []
            for raw_ref in state.get(refs_key) or []:
                if not isinstance(raw_ref, dict):
                    continue
                ref = dict(raw_ref)
                resolved = _resolved_state_path(
                    root_path,
                    ref.get("output_path"),
                    ref.get("output_relative_path"),
                )
                if resolved is not None:
                    ref["output_path"] = str(resolved)
                    ref["output_relative_path"] = _portable_path(root_path, resolved)
                repaired.append(ref)
            state[refs_key] = repaired

    for state in segments.values():
        repair_state(state)
    normalized_shots = {
        str(key): dict(value)
        for key, value in shots.items()
        if isinstance(value, dict)
    }
    for state in normalized_shots.values():
        repair_state(state)
    return segments, normalized_shots


def clear_shot_segment_refs_for_window(
    shot_states: dict[str, dict],
    *,
    profile: str,
    start_seconds: float,
    end_seconds: float,
) -> None:
    """Remove only references replaced by the current partial render window."""
    refs_key = (
        "preview_segment_refs"
        if profile == "motion_preview"
        else "approved_segment_refs"
    )
    start = float(start_seconds)
    end = float(end_seconds)
    for state in shot_states.values():
        retained = []
        for ref in state.get(refs_key) or []:
            if not isinstance(ref, dict):
                continue
            ref_start = float(ref.get("timeline_start_seconds", 0.0))
            ref_end = float(ref.get("timeline_end_seconds", ref_start))
            if ref_end <= start + 1e-9 or ref_start >= end - 1e-9:
                retained.append(ref)
        state[refs_key] = retained


def record_segment_take(
    root: str | Path,
    *,
    segment: dict,
    source: str | Path,
    request_kind: str,
    seed: int | None,
    segment_states: dict[str, dict],
    shot_states: dict[str, dict],
    shot_ranges: dict[str, tuple[float, float]],
) -> Path:
    """Archive one generated Segment once and attach lightweight Shot references."""
    root_path = Path(root).expanduser().resolve()
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Segment output is missing: {source_path}")
    segment_id = str(segment.get("segment_id") or "").strip()
    if not segment_id:
        raise ValueError("Segment output has no segment_id.")
    profile = "motion_preview" if request_kind == "preview" else "approved_final"
    relative = segment_take_relative_path(segment_id, profile)
    destination = (root_path / relative).resolve()
    link_or_copy(source_path, destination)

    previous = normalize_segment_take_states(segment_states).get(segment_id, {})
    take_count = max(0, int(previous.get("take_count", 0))) + 1
    take_id = f"T{take_count:04d}"
    start = float(segment.get("start_seconds", 0.0))
    end = float(segment.get("end_seconds", start))
    core_start = float(segment.get("core_start_seconds", start) or start)
    core_end = float(segment.get("core_end_seconds", end) or end)
    shot_ids = [str(value) for value in segment.get("shot_ids") or []]
    now = utc_now_text()
    state = dict(previous)
    state.update(
        {
            "segment_id": segment_id,
            "status": "preview" if profile == "motion_preview" else "approved",
            "render_profile": profile,
            "seed": seed,
            "take_count": take_count,
            "latest_take": take_id,
            "latest_output_path": str(destination),
            "latest_output_relative_path": relative.as_posix(),
            "start_seconds": start,
            "end_seconds": end,
            "core_start_seconds": core_start,
            "core_end_seconds": core_end,
            "shot_ids": shot_ids,
            "updated_at": now,
        }
    )
    if profile == "approved_final":
        state.update(
            {
                "approved_take": take_id,
                "approved_output_path": str(destination),
                "approved_output_relative_path": relative.as_posix(),
            }
        )
    segment_states[segment_id] = state
    metadata = {
        "segment_id": segment_id,
        "take_id": take_id,
        "profile": profile,
        "request_kind": request_kind,
        "seed": seed,
        "start_seconds": start,
        "end_seconds": end,
        "core_start_seconds": core_start,
        "core_end_seconds": core_end,
        "shot_ids": shot_ids,
        "source_output": str(source_path),
        "created_at": now,
    }
    metadata_path = destination.with_suffix(".json")
    temporary = metadata_path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(metadata_path)

    refs_key = (
        "preview_segment_refs"
        if profile == "motion_preview"
        else "approved_segment_refs"
    )
    for shot_id in shot_ids:
        if shot_id not in shot_states or shot_id not in shot_ranges:
            continue
        shot_start, shot_end = shot_ranges[shot_id]
        timeline_start = max(float(shot_start), core_start)
        timeline_end = min(float(shot_end), core_end)
        if timeline_end <= timeline_start + 1e-9:
            continue
        ref = {
            "segment_id": segment_id,
            "output_path": str(destination),
            "output_relative_path": relative.as_posix(),
            "timeline_start_seconds": timeline_start,
            "timeline_end_seconds": timeline_end,
            "source_in_seconds": max(0.0, timeline_start - start),
            "source_out_seconds": max(0.0, timeline_end - start),
        }
        shot_state = shot_states[shot_id]
        refs = [
            item for item in shot_state.get(refs_key) or []
            if isinstance(item, dict) and str(item.get("segment_id")) != segment_id
        ]
        refs.append(ref)
        refs.sort(key=lambda item: float(item.get("timeline_start_seconds", 0.0)))
        shot_state[refs_key] = refs
        shot_state["segment_id"] = str(refs[0].get("segment_id") or "")
        shot_state["segment_refs"] = list(refs)
        shot_state.update(
            {
                "status": state["status"],
                "render_profile": profile,
                "seed": seed,
                "latest_take": take_id,
                "latest_output_path": str(destination),
                "latest_output_relative_path": relative.as_posix(),
                "updated_at": now,
            }
        )
        if profile == "approved_final":
            shot_state.update(
                {
                    "approved_take": take_id,
                    "approved_output_path": str(destination),
                    "approved_output_relative_path": relative.as_posix(),
                }
            )
    return destination


def next_take_id(state: dict) -> str:
    return f"T{max(0, int(state.get('take_count', 0))) + 1:04d}"


def link_or_copy(source: str | Path, destination: str | Path) -> Path:
    source_path = Path(source).resolve()
    destination_path = Path(destination).resolve()
    if destination_path.is_file():
        try:
            if os.path.samefile(source_path, destination_path):
                return destination_path
        except OSError:
            pass
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination_path.with_name(destination_path.name + ".tmp")
    if temporary.exists():
        temporary.unlink()
    try:
        os.link(source_path, temporary)
    except OSError:
        shutil.copy2(source_path, temporary)
    temporary.replace(destination_path)
    return destination_path


def _file_digest(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def migrate_legacy_shot_takes(
    root: str | Path,
    *,
    manifests: dict[str, dict],
    shot_states: dict[str, dict],
    shot_ranges: dict[str, tuple[float, float]],
    segment_states: dict[str, dict] | None = None,
    remove_verified_legacy_files: bool = True,
) -> tuple[dict[str, dict], dict[str, dict], dict]:
    """Migrate v1 per-Shot movie aliases into one canonical file per Segment.

    Only legacy files whose SHA-256 matches a successfully archived canonical
    Segment are removed. Unmatched Takes are left untouched and reported.
    """
    root_path = Path(root).expanduser().resolve()
    segments = normalize_segment_take_states(segment_states or {})
    shots = normalize_shot_take_states(shot_states, list(shot_ranges))
    report = {
        "migrated_segments": 0,
        "removed_legacy_files": 0,
        "retained_unmatched_files": 0,
        "logical_bytes_removed": 0,
    }
    canonical_digests: set[str] = set()
    represented_profiles: set[str] = set()

    for cache_key, profile, request_kind in (
        ("preview", "motion_preview", "preview"),
        ("production", "approved_final", "accepted"),
    ):
        manifest = manifests.get(cache_key) if isinstance(manifests, dict) else None
        if not isinstance(manifest, dict):
            continue
        stable_master = root_path / (
            "generated_preview.mp4"
            if profile == "motion_preview"
            else "generated_output.mp4"
        )
        if stable_master.is_file():
            manifest["master_output"] = str(stable_master.resolve())
        rows = [row for row in manifest.get("segments") or [] if isinstance(row, dict)]
        if not rows:
            continue
        represented_profiles.add(profile)
        clear_shot_segment_refs_for_window(
            shots,
            profile=profile,
            start_seconds=min(float(row.get("core_start_seconds", row.get("start_seconds", 0.0)) or row.get("start_seconds", 0.0)) for row in rows),
            end_seconds=max(float(row.get("core_end_seconds", row.get("end_seconds", 0.0)) or row.get("end_seconds", 0.0)) for row in rows),
        )
        for row in rows:
            segment_id = str(row.get("segment_id") or "").strip()
            if not segment_id:
                continue
            candidates: list[Path] = []
            raw_output = str(row.get("output_path") or "").strip()
            if raw_output:
                candidates.append(Path(raw_output))
            for shot_id in [str(value) for value in row.get("shot_ids") or []]:
                shot_root = root_path / "shots" / slugify_project_name(shot_id, "shot")
                candidates.extend(sorted((shot_root / "takes").glob(f"*_{profile}.mp4")))
                if profile == "approved_final":
                    candidates.append(shot_root / "approved.mp4")
            source = next((path.resolve() for path in candidates if path.is_file()), None)
            if source is None:
                continue
            destination = record_segment_take(
                root_path,
                segment=row,
                source=source,
                request_kind=request_kind,
                seed=row.get("seed"),
                segment_states=segments,
                shot_states=shots,
                shot_ranges=shot_ranges,
            )
            digest = _file_digest(destination)
            if digest != _file_digest(source):
                raise OSError(f"Segment migration verification failed: {segment_id}")
            canonical_digests.add(digest)
            row["output_path"] = str(destination)
            row["download_dir"] = ""
            row["outputs"] = [
                {"kind": "videos", "local_path": str(destination)}
            ]
            report["migrated_segments"] += 1

    legacy_files = list((root_path / "shots").glob("*/takes/*.mp4"))
    legacy_files.extend((root_path / "shots").glob("*/approved.mp4"))
    for legacy in legacy_files:
        try:
            resolved = legacy.resolve()
            resolved.relative_to((root_path / "shots").resolve())
        except (OSError, ValueError):
            report["retained_unmatched_files"] += 1
            continue
        profile = (
            "motion_preview" if "motion_preview" in legacy.name else "approved_final"
        )
        if profile not in represented_profiles:
            report["retained_unmatched_files"] += 1
            continue
        try:
            digest = _file_digest(resolved)
        except OSError:
            report["retained_unmatched_files"] += 1
            continue
        if digest not in canonical_digests or not remove_verified_legacy_files:
            report["retained_unmatched_files"] += 1
            continue
        size = resolved.stat().st_size
        resolved.unlink()
        sidecar = resolved.with_suffix(".json")
        sidecar.unlink(missing_ok=True)
        report["removed_legacy_files"] += 1
        report["logical_bytes_removed"] += size

    return segments, shots, report

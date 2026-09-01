"""Auditable storage reporting, safe cleanup and portable Workspace archives."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import zipfile


TEMP_SUFFIXES = (".tmp", ".part", ".partial", ".building.mp4")
DISPOSABLE_ROOTS = {"cache", "proxies"}
EXCLUDED_ARCHIVE_ROOTS = {"cache", "proxies", "logs"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _category(relative: Path) -> str:
    if not relative.parts:
        return "other"
    name = relative.name.casefold()
    first = relative.parts[0].casefold()
    if name in {"generated_output.mp4", "generated_preview.mp4"}:
        return "master"
    if first == "segments" and "takes" in {part.casefold() for part in relative.parts}:
        return "segment_take"
    if first == "media":
        return "media"
    if first == "project" or name == "project_manifest.json":
        return "project"
    if first == "design":
        return "design_revision"
    if first == "shots":
        return "shot_metadata"
    if first in DISPOSABLE_ROOTS:
        return "disposable_cache"
    if first == "renders":
        return "legacy_render"
    if first == "logs":
        return "logs"
    return "other"


def _is_temp(relative: Path) -> bool:
    lowered = relative.name.casefold()
    return any(lowered.endswith(suffix) for suffix in TEMP_SUFFIXES)


def workspace_files(root: str | Path) -> list[Path]:
    """Return regular in-Workspace files without following escaping symlinks."""
    workspace = Path(root).expanduser().resolve()
    if not workspace.is_dir():
        raise FileNotFoundError(f"Workspace does not exist: {workspace}")
    files: list[Path] = []
    for path in workspace.rglob("*"):
        if path.is_file() and _inside(workspace, path):
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(workspace).as_posix())


def build_storage_report(root: str | Path, *, hash_duplicates: bool = True) -> dict:
    """Measure logical, physical and duplicate bytes by durable category."""
    workspace = Path(root).expanduser().resolve()
    rows: list[dict] = []
    physical: dict[tuple[int, int], int] = {}
    size_groups: dict[int, list[Path]] = defaultdict(list)
    category_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"files": 0, "logical_bytes": 0}
    )
    for path in workspace_files(workspace):
        relative = path.relative_to(workspace)
        stat = path.stat()
        category = _category(relative)
        disposable = category == "disposable_cache" or _is_temp(relative)
        rows.append(
            {
                "path": relative.as_posix(),
                "category": category,
                "bytes": int(stat.st_size),
                "disposable": disposable,
            }
        )
        category_totals[category]["files"] += 1
        category_totals[category]["logical_bytes"] += int(stat.st_size)
        physical.setdefault((int(stat.st_dev), int(stat.st_ino)), int(stat.st_size))
        if stat.st_size > 0:
            size_groups[int(stat.st_size)].append(path)

    duplicate_groups: list[dict] = []
    if hash_duplicates:
        for size, paths in size_groups.items():
            if len(paths) < 2:
                continue
            by_digest: dict[str, list[Path]] = defaultdict(list)
            for path in paths:
                by_digest[_digest(path)].append(path)
            for digest, matches in by_digest.items():
                physical_keys = {
                    (int(path.stat().st_dev), int(path.stat().st_ino))
                    for path in matches
                }
                if len(matches) < 2:
                    continue
                duplicate_groups.append(
                    {
                        "sha256": digest,
                        "bytes_each": size,
                        "logical_copies": len(matches),
                        "physical_copies": len(physical_keys),
                        "reclaimable_physical_bytes": max(
                            0, (len(physical_keys) - 1) * size
                        ),
                        "paths": [
                            path.relative_to(workspace).as_posix()
                            for path in matches
                        ],
                    }
                )

    logical_bytes = sum(row["bytes"] for row in rows)
    physical_bytes = sum(physical.values())
    disposable_bytes = sum(row["bytes"] for row in rows if row["disposable"])
    return {
        "format": "h3-workspace-storage-report",
        "version": 1,
        "workspace": str(workspace),
        "created_at": _utc_now(),
        "file_count": len(rows),
        "logical_bytes": logical_bytes,
        "physical_bytes": physical_bytes,
        "hardlink_saved_bytes": max(0, logical_bytes - physical_bytes),
        "disposable_bytes": disposable_bytes,
        "duplicate_physical_bytes": sum(
            row["reclaimable_physical_bytes"] for row in duplicate_groups
        ),
        "categories": dict(sorted(category_totals.items())),
        "duplicate_groups": duplicate_groups,
        "files": rows,
    }


def _canonical_duplicate_sources(workspace: Path) -> dict[str, list[Path]]:
    protected: list[Path] = []
    for name in ("generated_output.mp4", "generated_preview.mp4"):
        candidate = workspace / name
        if candidate.is_file():
            protected.append(candidate)
    protected.extend(
        path
        for path in (workspace / "segments").glob("*/takes/*.mp4")
        if path.is_file() and _inside(workspace, path)
    )
    by_size: dict[int, list[Path]] = defaultdict(list)
    for path in protected:
        by_size[path.stat().st_size].append(path)
    digests: dict[str, list[Path]] = defaultdict(list)
    for paths in by_size.values():
        for path in paths:
            digests[_digest(path)].append(path)
    return digests


def _recovery_protection(workspace: Path) -> tuple[set[Path], set[Path]]:
    """Return files/directories required to resume an interrupted render.

    Render caches are normally disposable, but a retained ``*.job.json`` or
    worker manifest makes its referenced outputs part of crash recovery.  The
    cleanup planner must therefore distinguish abandoned cache from resumable
    cache instead of deleting the entire cache tree unconditionally.
    """
    protected_files: set[Path] = set()
    protected_dirs: set[Path] = set()
    render_jobs = workspace / "project" / "render_jobs"
    if not render_jobs.is_dir():
        return protected_files, protected_dirs

    def collect(value: object, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                collect(child, str(child_key).casefold())
            return
        if isinstance(value, list):
            for child in value:
                collect(child, key)
            return
        if key not in {"download_dir", "output_path", "local_path"}:
            return
        text = str(value or "").strip()
        if not text:
            return
        candidate = Path(text).expanduser()
        try:
            candidate = candidate.resolve()
        except OSError:
            return
        if not _inside(workspace, candidate):
            return
        if key == "download_dir" or candidate.is_dir():
            protected_dirs.add(candidate)
        else:
            protected_files.add(candidate)

    loaded_manifests: set[Path] = set()
    for source in sorted(render_jobs.glob("*.job.json")):
        try:
            payload = json.loads(source.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError, TypeError):
            continue
        collect(payload)
        protected_files.add(source.resolve())
        manifest_text = str(payload.get("manifest_path") or "").strip() if isinstance(payload, dict) else ""
        if manifest_text:
            manifest_path = Path(manifest_text).expanduser()
            if manifest_path.is_file() and _inside(workspace, manifest_path):
                protected_files.add(manifest_path.resolve())
                loaded_manifests.add(manifest_path.resolve())
                try:
                    collect(json.loads(manifest_path.read_text(encoding="utf-8-sig")))
                except (OSError, ValueError, TypeError):
                    pass
    # The worker deliberately removes its large job file after it completes.
    # Until the UI has published durable Segment Takes, its standalone
    # manifest is the only crash-recovery pointer to completed cache outputs.
    for manifest_path in sorted(render_jobs.glob("*.manifest.json")):
        resolved_manifest = manifest_path.resolve()
        if resolved_manifest in loaded_manifests:
            continue
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError, TypeError):
            continue
        collect(payload)
    return protected_files, protected_dirs


def _is_recovery_protected(
    path: Path,
    protected_files: set[Path],
    protected_dirs: set[Path],
) -> bool:
    resolved = path.resolve()
    if resolved in protected_files:
        return True
    for directory in protected_dirs:
        try:
            resolved.relative_to(directory)
            return True
        except ValueError:
            continue
    return False


def safe_cleanup_plan(root: str | Path) -> dict:
    """Build a conservative deletion plan; Approved Takes are never candidates."""
    workspace = Path(root).expanduser().resolve()
    canonical_digests = _canonical_duplicate_sources(workspace)
    protected_files, protected_dirs = _recovery_protection(workspace)
    candidates: list[dict] = []
    for path in workspace_files(workspace):
        if _is_recovery_protected(path, protected_files, protected_dirs):
            continue
        relative = path.relative_to(workspace)
        first = relative.parts[0].casefold() if relative.parts else ""
        reason = ""
        if first in DISPOSABLE_ROOTS:
            reason = "disposable_workspace_cache"
        elif _is_temp(relative):
            reason = "interrupted_temporary_file"
        elif (
            first == "renders" and path.suffix.casefold() in {".mp4", ".mov", ".mkv"}
        ) or (
            first == "shots"
            and path.suffix.casefold() == ".mp4"
        ):
            digest = _digest(path)
            if digest in canonical_digests and all(
                path.resolve() != source.resolve()
                for source in canonical_digests[digest]
            ):
                reason = "verified_duplicate_of_canonical_master_or_segment_take"
        if reason:
            candidates.append(
                {
                    "path": relative.as_posix(),
                    "bytes": int(path.stat().st_size),
                    "reason": reason,
                }
            )
    return {
        "format": "h3-workspace-cleanup-plan",
        "version": 1,
        "workspace": str(workspace),
        "created_at": _utc_now(),
        "dry_run": True,
        "candidate_count": len(candidates),
        "reclaimable_bytes": sum(row["bytes"] for row in candidates),
        "candidates": candidates,
        "protected_contract": [
            "generated_output.mp4",
            "generated_preview.mp4",
            "segments/*/takes/approved_final.mp4",
            "segments/*/takes/motion_preview.mp4",
            "project/**",
            "media/**",
            "cache paths referenced by project/render_jobs/*.job.json",
        ],
    }


def safe_cleanup_workspace(root: str | Path, *, dry_run: bool = True) -> dict:
    """Delete only the exact files emitted by :func:`safe_cleanup_plan`."""
    workspace = Path(root).expanduser().resolve()
    plan = safe_cleanup_plan(workspace)
    if dry_run:
        return plan
    removed: list[dict] = []
    for row in plan["candidates"]:
        path = (workspace / Path(row["path"])).resolve()
        if not _inside(workspace, path) or not path.is_file():
            continue
        path.unlink()
        removed.append(row)
    # Remove only empty directories and never the Workspace root itself.
    for path in sorted(
        (item for item in workspace.rglob("*") if item.is_dir()),
        key=lambda item: len(item.parts),
        reverse=True,
    ):
        if path == workspace or not _inside(workspace, path):
            continue
        try:
            path.rmdir()
        except OSError:
            pass
    plan.update(
        {
            "dry_run": False,
            "removed_count": len(removed),
            "removed_bytes": sum(row["bytes"] for row in removed),
            "removed": removed,
        }
    )
    return plan


def _external_project_sources(workspace: Path) -> list[tuple[str, Path]]:
    project = workspace / "project" / "director_project.h3director.json"
    if not project.is_file():
        return []
    try:
        payload = json.loads(project.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    raw_paths: list[tuple[str, object]] = [("workflow", payload.get("workflow_path"))]
    raw_paths.extend(
        ("media", row.get("local_path"))
        for row in (payload.get("assets") or {}).values()
        if isinstance(row, dict)
    )
    external: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for kind, raw in raw_paths:
        text = str(raw or "").strip()
        if not text:
            continue
        path = Path(text).expanduser()
        if not path.is_file() or _inside(workspace, path):
            continue
        key = os.path.normcase(str(path.resolve()))
        if key not in seen:
            seen.add(key)
            external.append((kind, path.resolve()))
    return external


def archive_workspace(
    root: str | Path,
    destination: str | Path | None = None,
    *,
    include_logs: bool = False,
) -> dict:
    """Create and verify one portable archive, excluding disposable caches."""
    workspace = Path(root).expanduser().resolve()
    if not (workspace / "project" / "director_project.h3director.json").is_file():
        raise FileNotFoundError("Canonical project is missing; save the Project before Archive.")
    active_jobs = sorted((workspace / "project" / "render_jobs").glob("*.job.json"))
    recovery_files, recovery_dirs = _recovery_protection(workspace)
    excluded_roots = [
        (workspace / root_name).resolve() for root_name in EXCLUDED_ARCHIVE_ROOTS
    ]

    def in_excluded_root(path: Path) -> bool:
        for excluded in excluded_roots:
            try:
                path.resolve().relative_to(excluded)
                return True
            except ValueError:
                continue
        return False

    resumable_cache = any(
        path.exists() and in_excluded_root(path)
        for path in recovery_files | recovery_dirs
    )
    if active_jobs or resumable_cache:
        raise RuntimeError(
            "Archive is blocked because an active or interrupted render job still exists. "
            "Resume or finish that render before creating a portable archive."
        )
    target = (
        Path(destination).expanduser().resolve()
        if destination
        else workspace.parent / f"{workspace.name}.h3project.zip"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.unlink(missing_ok=True)
    entries: list[dict] = []
    written_names: set[str] = set()

    def add_file(archive: zipfile.ZipFile, source: Path, archive_name: str) -> None:
        normalized = Path(archive_name).as_posix().lstrip("/")
        if not normalized or ".." in Path(normalized).parts or normalized in written_names:
            return
        archive.write(source, normalized)
        written_names.add(normalized)
        entries.append(
            {
                "path": normalized,
                "bytes": int(source.stat().st_size),
                "sha256": _digest(source),
            }
        )

    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
        ) as archive:
            for source in workspace_files(workspace):
                if source.resolve() in {target.resolve(), temporary.resolve()}:
                    continue
                relative = source.relative_to(workspace)
                first = relative.parts[0].casefold() if relative.parts else ""
                if first in EXCLUDED_ARCHIVE_ROOTS and not (
                    include_logs and first == "logs"
                ):
                    continue
                if _is_temp(relative):
                    continue
                add_file(archive, source, relative.as_posix())

            external_map: list[dict] = []
            for source_kind, source in _external_project_sources(workspace):
                digest = _digest(source)
                archive_name = (
                    f"workflow/{source.name}"
                    if source_kind == "workflow"
                    else f"media/consolidated/{digest[:16]}/{source.name}"
                )
                add_file(archive, source, archive_name)
                external_map.append(
                    {
                        "kind": source_kind,
                        "original_path": str(source),
                        "archive_path": archive_name,
                        "sha256": digest,
                    }
                )
            manifest = {
                "format": "h3-project-archive",
                "version": 1,
                "created_at": _utc_now(),
                "workspace_name": workspace.name,
                "cache_excluded": True,
                "logs_included": bool(include_logs),
                "external_sources": external_map,
                "entries": entries,
            }
            archive.writestr(
                "archive_manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    with zipfile.ZipFile(target, "r") as archive:
        names = set(archive.namelist())
        if "archive_manifest.json" not in names:
            raise OSError("Archive verification failed: manifest is missing.")
        loaded = json.loads(archive.read("archive_manifest.json"))
        for row in loaded.get("entries") or []:
            name = str(row.get("path") or "")
            if not name or name not in names or name.startswith("/") or ".." in Path(name).parts:
                raise OSError(f"Archive verification failed: unsafe or missing entry {name!r}.")
            digest = hashlib.sha256(archive.read(name)).hexdigest()
            if digest != row.get("sha256"):
                raise OSError(f"Archive verification failed: hash mismatch for {name}.")
    return {
        "archive": str(target),
        "file_count": len(entries),
        "logical_bytes": sum(row["bytes"] for row in entries),
        "archive_bytes": int(target.stat().st_size),
        "external_source_count": len(manifest["external_sources"]),
        "verified": True,
    }

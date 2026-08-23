"""Editable prompt presets persisted as one .env file per prompt family."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re


FAMILY_ENV_FILENAMES = {
    "creative_brief": "creative_brief.env",
    "global_visual_style": "global_visual_style.env",
    "transition_language": "transition_language.env",
    "constraints_and_technical_rules": "constraints_and_technical_rules.env",
    "overall_soundscape": "overall_soundscape.env",
    "non_diegetic_music": "non_diegetic_music.env",
}


@dataclass(frozen=True, slots=True)
class PromptPresetRecord:
    family: str
    name: str
    text: str
    path: Path


def _safe_family(family: str) -> str:
    value = re.sub(r"[^a-z0-9_-]+", "_", family.strip().lower()).strip("_")
    if not value:
        raise ValueError("Preset family is required")
    return value


def family_env_path(root: str | Path, family: str) -> Path:
    family = _safe_family(family)
    return Path(root) / FAMILY_ENV_FILENAMES.get(family, f"{family}.env")


def _read_env(path: Path) -> dict[str, object]:
    values: dict[str, object] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw = stripped.split("=", 1)
        raw = raw.strip()
        try:
            value: object = json.loads(raw)
        except json.JSONDecodeError:
            value = raw.strip('"\'')
        values[key.strip()] = value
    return values


def _load_family_mapping(root: str | Path, family: str) -> dict[str, str]:
    family = _safe_family(family)
    path = family_env_path(root, family)
    if not path.is_file():
        return {}
    try:
        values = _read_env(path)
        raw = values.get("H3_PRESETS_JSON", {})
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, dict):
            return {}
        return {
            " ".join(str(name).split()).strip(): str(text).strip()
            for name, text in raw.items()
            if str(name).strip() and str(text).strip()
        }
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def _save_family_mapping(root: str | Path, family: str, presets: dict[str, str]) -> Path:
    family = _safe_family(family)
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    destination = family_env_path(root_path, family)
    ordered = dict(sorted(presets.items(), key=lambda item: item[0].casefold()))
    destination.write_text(
        "\n".join(
            (
                "# MiniMax H3 prompt presets — one env file for this entire prompt category",
                f"H3_PRESET_FAMILY={json.dumps(family, ensure_ascii=False)}",
                f"H3_PRESETS_JSON={json.dumps(ordered, ensure_ascii=False, separators=(',', ':'))}",
                "",
            )
        ),
        encoding="utf-8",
    )
    return destination


def _legacy_presets(root: Path, legacy_family: str) -> dict[str, str]:
    directory = root / _safe_family(legacy_family)
    presets: dict[str, str] = {}
    if not directory.is_dir():
        return presets
    for path in directory.glob("*.env"):
        try:
            values = _read_env(path)
            name = str(values.get("H3_PRESET_NAME", "")).strip()
            text = str(values.get("H3_PRESET_TEXT", "")).strip()
            if name and text:
                presets[name] = text
        except (OSError, UnicodeError):
            continue
    return presets


def _remove_legacy_env_directory(root: Path, legacy_family: str) -> None:
    directory = root / _safe_family(legacy_family)
    if not directory.is_dir():
        return
    try:
        directory.resolve().relative_to(root.resolve())
    except ValueError:
        return
    for path in directory.glob("*.env"):
        path.unlink()
    try:
        directory.rmdir()
    except OSError:
        pass


def ensure_prompt_presets(
    root: str | Path,
    family: str,
    defaults: dict[str, str],
    *,
    legacy_families: tuple[str, ...] = (),
) -> None:
    """Create one family env, migrating the earlier one-file-per-preset layout."""
    family = _safe_family(family)
    root_path = Path(root)
    destination = family_env_path(root_path, family)
    if destination.is_file():
        for legacy_family in legacy_families:
            _remove_legacy_env_directory(root_path, legacy_family)
        return
    merged = dict(defaults)
    for legacy_family in legacy_families:
        merged.update(_legacy_presets(root_path, legacy_family))
    _save_family_mapping(root_path, family, merged)
    for legacy_family in legacy_families:
        _remove_legacy_env_directory(root_path, legacy_family)


def load_prompt_presets(root: str | Path, family: str) -> list[PromptPresetRecord]:
    family = _safe_family(family)
    path = family_env_path(root, family)
    return [
        PromptPresetRecord(family, name, text, path)
        for name, text in sorted(
            _load_family_mapping(root, family).items(), key=lambda item: item[0].casefold()
        )
    ]


def save_prompt_preset(
    root: str | Path,
    family: str,
    name: str,
    text: str,
    *,
    previous_name: str | None = None,
) -> PromptPresetRecord:
    family = _safe_family(family)
    name = " ".join(name.split()).strip()
    text = text.strip()
    if not name or not text:
        raise ValueError("Preset name and content are required")
    presets = _load_family_mapping(root, family)
    if previous_name and previous_name != name:
        presets.pop(previous_name, None)
    presets[name] = text
    path = _save_family_mapping(root, family, presets)
    return PromptPresetRecord(family, name, text, path)


def delete_prompt_preset(root: str | Path, record: PromptPresetRecord) -> bool:
    presets = _load_family_mapping(root, record.family)
    if record.name not in presets:
        return False
    presets.pop(record.name)
    _save_family_mapping(root, record.family, presets)
    return True

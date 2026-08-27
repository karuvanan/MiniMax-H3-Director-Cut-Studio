"""Compact, deterministic rendering for raw BLIP observations."""

from __future__ import annotations

import re
from typing import Iterable


_GENERIC_PREFIXES = (
    "a photograph of",
    "a photo of",
    "the central scene shows",
    "the scene shows",
    "the lighting reveals",
    "the central subject is",
)
_TOKEN_ALIASES = {
    "girl": "woman",
    "lady": "woman",
    "female": "woman",
    "women": "woman",
    "girls": "woman",
    "ladies": "woman",
    "men": "man",
    "boys": "man",
}
_LOW_INFORMATION_TOKENS = {
    "a", "an", "and", "are", "at", "beautiful", "beauty", "by", "central",
    "detail", "frame", "from", "in", "is", "it", "lighting", "of", "on",
    "photo", "photograph", "scene", "shows", "the", "this", "traditional",
    "view", "with",
}


def clean_blip_caption(caption: object, prompt: object = "") -> str:
    """Remove conditional prompt echo and normalize whitespace/punctuation."""
    result = re.sub(r"\s+", " ", str(caption or "")).strip(" .,:;-\t\r\n")
    candidates = [str(prompt or "").strip(), *_GENERIC_PREFIXES]
    changed = True
    while result and changed:
        changed = False
        lowered = result.casefold()
        for prefix in candidates:
            normalized = re.sub(r"\s+", " ", prefix).strip(" .,:;-").casefold()
            if normalized and lowered.startswith(normalized):
                result = result[len(normalized):].lstrip(" .,:;-\t")
                changed = True
                break
    return result.strip()


def _meaningful_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for token in re.findall(r"[a-z0-9]+|[\u3400-\u9fff]+", text.casefold()):
        token = _TOKEN_ALIASES.get(token, token)
        if len(token) > 1 and token not in _LOW_INFORMATION_TOKENS:
            tokens.add(token)
    return tokens


def concise_blip_entries(
    entries: Iterable[tuple[str, str]],
    *,
    maximum: int = 5,
) -> list[tuple[str, str]]:
    """Keep the overview plus only region captions that add useful evidence."""
    kept: list[tuple[str, str]] = []
    signatures: list[set[str]] = []
    known_tokens: set[str] = set()
    exact: set[str] = set()
    for label, raw_caption in entries:
        caption = clean_blip_caption(raw_caption)
        folded = caption.casefold()
        if not caption or folded in exact:
            continue
        tokens = _meaningful_tokens(caption)
        duplicate = any(
            tokens
            and previous
            and len(tokens & previous) / max(1, len(tokens | previous)) >= 0.67
            for previous in signatures
        )
        novelty = tokens - known_tokens
        if kept and (duplicate or len(novelty) < 2):
            continue
        kept.append((str(label), caption))
        exact.add(folded)
        signatures.append(tokens)
        known_tokens.update(tokens)
        if len(kept) >= maximum:
            break
    return kept


def remove_previous_blip_output(recognition: object) -> str:
    """Remove current and legacy BLIP display lines without touching other analysis."""
    kept: list[str] = []
    for line in str(recognition or "").splitlines():
        stripped = line.strip()
        lowered = stripped.casefold()
        if (
            lowered.startswith("blip visual ")
            or lowered.startswith("blip video frame")
            or lowered.startswith("blip error")
            or lowered.startswith("blip service stopped")
            or lowered.startswith("blip visual summary")
            or lowered.startswith("blip ·")
            or lowered.startswith("inference device:")
        ):
            continue
        kept.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def render_blip_summary(
    entries: Iterable[tuple[str, str]],
    devices: Iterable[str],
    errors: Iterable[str] = (),
) -> str:
    concise = concise_blip_entries(entries)
    device_names = []
    for value in devices:
        name = str(value or "").strip().upper()
        if name and name not in device_names:
            device_names.append(name)
    device_text = " → ".join(device_names) or "UNKNOWN"
    if not concise:
        reason = next((str(error).strip() for error in errors if str(error).strip()), "No caption returned")
        return f"BLIP ERROR · {reason}"
    lines = [f"BLIP VISUAL SUMMARY · {device_text}"]
    lines.extend(f"BLIP · {label}: {caption}" for label, caption in concise)
    return "\n".join(lines)

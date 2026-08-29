"""Validated local storage for H3 Studio Special Skills."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


STANDALONE_MARKER = "<!-- h3-studio-binding: standalone -->"
SPECIAL_KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

DEFAULT_SPECIAL_SKILL_BODY = """# New H3 Special Skill

Apply this scene-specific skill together with the bound Default H3 prompt-writing skill.

## Plan

- Preserve the user's exact duration, story intent, references and authored dialogue.
- Convert the concept into chronological, non-overlapping Shot Blocks on the 0.5-second grid.
- State framing, camera angle, camera movement, subject action, environment response, continuity state, optional flourish and additional direction.

## H3 Handoff

- Keep must-complete actions concise and physically continuous.
- Put exact Dialogue, Voice-over, Lyrics and On-screen Text in `text_layers`.
- Reuse valid Media Pool sources through `existing_media_uses` before adding `media_requests`.
- Let the bound Default Skill compile the final MiniMax H3 Ref2VA structure.

## Validate

- No missing or overlapping time range.
- No identity, ownership, geography or dialogue contradiction.
- No new action during the Final Hold.
"""


@dataclass(slots=True)
class SpecialSkillDocument:
    key: str
    description: str
    body: str
    chinese_body: str = ""
    standalone: bool = False
    path: Path | None = None


def _split_frontmatter(text: str) -> tuple[str, str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, flags=re.S)
    if not match:
        return "", "", text.strip()
    frontmatter = match.group(1)
    name_match = re.search(r"^name:\s*(.+?)\s*$", frontmatter, flags=re.M)
    name = name_match.group(1).strip().strip("\"'") if name_match else ""
    description = ""
    lines = frontmatter.splitlines()
    for index, line in enumerate(lines):
        desc_match = re.match(r"^description:\s*(.*?)\s*$", line)
        if not desc_match:
            continue
        value = desc_match.group(1)
        if value in {"|", ">", ""}:
            collected: list[str] = []
            for continuation in lines[index + 1 :]:
                if continuation.startswith(" ") or not continuation.strip():
                    if continuation.strip():
                        collected.append(continuation.strip())
                else:
                    break
            description = " ".join(collected)
        else:
            description = value.strip().strip("\"'")
        break
    return name, description, text[match.end() :].strip()


def validate_special_skill_document(document: SpecialSkillDocument) -> None:
    key = document.key.strip()
    if not SPECIAL_KEY_RE.fullmatch(key):
        raise ValueError(
            "Skill folder/name must use lowercase letters, digits and single hyphens only."
        )
    if len(key) > 63:
        raise ValueError("Skill folder/name must contain at most 63 characters.")
    if key == "h3-prompt-writing":
        raise ValueError("h3-prompt-writing is reserved for the Default Skill.")
    description = " ".join(document.description.split())
    if not description:
        raise ValueError("Skill description is required so the Studio can explain its purpose.")
    if len(description) > 600:
        raise ValueError("Skill description must contain at most 600 characters.")
    body = document.body.strip()
    if not body:
        raise ValueError("English SKILL.md instructions cannot be empty.")
    if body.startswith("---"):
        raise ValueError("Edit only the instruction body; frontmatter is generated automatically.")
    if document.standalone and "Default H3" in body and "not bound" not in body:
        raise ValueError(
            "Standalone mode conflicts with instructions that bind the Default H3 Skill."
        )


def render_special_skill(document: SpecialSkillDocument, *, chinese: bool = False) -> str:
    validate_special_skill_document(document)
    body = (document.chinese_body if chinese else document.body).strip()
    if chinese and not body:
        return ""
    body = body.replace(STANDALONE_MARKER, "").strip()
    description = " ".join(document.description.split())
    rows = [
        "---",
        f"name: {document.key.strip()}",
        "description: |",
        f"  {description}",
        "---",
        "",
    ]
    if document.standalone:
        rows.extend((STANDALONE_MARKER, ""))
    rows.append(body)
    return "\n".join(rows).rstrip() + "\n"


def load_special_skill_document(folder: str | Path) -> SpecialSkillDocument:
    folder_path = Path(folder)
    skill_path = folder_path / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8-sig")
    name, description, body = _split_frontmatter(text)
    chinese_path = folder_path / "SKILL.cn.md"
    chinese_body = ""
    if chinese_path.is_file():
        _cn_name, _cn_description, chinese_body = _split_frontmatter(
            chinese_path.read_text(encoding="utf-8-sig")
        )
    return SpecialSkillDocument(
        key=folder_path.name,
        description=description,
        body=body.replace(STANDALONE_MARKER, "").strip(),
        chinese_body=chinese_body.replace(STANDALONE_MARKER, "").strip(),
        standalone=STANDALONE_MARKER in text,
        path=skill_path.resolve(),
    )


def save_special_skill_document(
    root: str | Path,
    document: SpecialSkillDocument,
    *,
    editing_key: str = "",
) -> SpecialSkillDocument:
    validate_special_skill_document(document)
    root_path = Path(root).resolve()
    root_path.mkdir(parents=True, exist_ok=True)
    key = document.key.strip()
    folder = (root_path / key).resolve()
    if folder.parent != root_path:
        raise ValueError("Skill folder escapes the Special Skill root.")
    if editing_key and editing_key != key:
        raise ValueError("Renaming an existing Special Skill is not supported; create a new one.")
    if folder.exists() and not editing_key:
        raise FileExistsError(f"Special Skill already exists: {key}")
    folder.mkdir(parents=True, exist_ok=True)

    skill_text = render_special_skill(document)
    skill_path = folder / "SKILL.md"
    temporary = folder / "SKILL.md.tmp"
    temporary.write_text(skill_text, encoding="utf-8")
    temporary.replace(skill_path)

    chinese_text = render_special_skill(document, chinese=True)
    chinese_path = folder / "SKILL.cn.md"
    if chinese_text:
        chinese_temporary = folder / "SKILL.cn.md.tmp"
        chinese_temporary.write_text(chinese_text, encoding="utf-8")
        chinese_temporary.replace(chinese_path)
    elif chinese_path.is_file():
        chinese_path.unlink()

    return load_special_skill_document(folder)

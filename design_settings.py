"""Persistent, non-secret settings for the AI Design page."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(slots=True)
class DesignAISettings:
    provider: str = "openai"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-5.6-sol"
    lm_studio_base_url: str = "http://127.0.0.1:1234/v1"
    lm_studio_model: str = (
        "hauhaucs/qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp-gguf/"
        "qwen3.8-27b-uncensored-hauhaucs-aggressive-q5_k_p.gguf"
    )
    timeout: int = 900
    generate_comfy_images: bool = True
    image_checkpoint: str = "z_image_turbo_bf16.safetensors"
    image_width: int = 1024
    image_height: int = 576
    image_steps: int = 8
    image_cfg: float = 1.0
    image_negative_prompt: str = (
        "low quality, blurry, distorted hands, extra fingers, duplicate person, "
        "deformed anatomy, unreadable label, watermark, text artifacts"
    )


KEYS = {
    "H3_DESIGN_PROVIDER": "provider",
    "H3_DESIGN_OPENAI_BASE_URL": "openai_base_url",
    "H3_DESIGN_OPENAI_MODEL": "openai_model",
    "H3_DESIGN_LM_STUDIO_BASE_URL": "lm_studio_base_url",
    "H3_DESIGN_LM_STUDIO_MODEL": "lm_studio_model",
    "H3_DESIGN_TIMEOUT": "timeout",
    "H3_DESIGN_GENERATE_COMFY_IMAGES": "generate_comfy_images",
    "H3_DESIGN_IMAGE_CHECKPOINT": "image_checkpoint",
    "H3_DESIGN_IMAGE_WIDTH": "image_width",
    "H3_DESIGN_IMAGE_HEIGHT": "image_height",
    "H3_DESIGN_IMAGE_STEPS": "image_steps",
    "H3_DESIGN_IMAGE_CFG": "image_cfg",
    "H3_DESIGN_IMAGE_NEGATIVE_PROMPT": "image_negative_prompt",
}


def load_design_settings(path: str | Path) -> DesignAISettings:
    settings = DesignAISettings()
    source = Path(path)
    if not source.is_file():
        return settings
    for line in source.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, raw = line.split("=", 1)
        field = KEYS.get(key.strip())
        if not field:
            continue
        try:
            value = json.loads(raw.strip())
        except json.JSONDecodeError:
            value = raw.strip().strip('"\'')
        if field in {"timeout", "image_width", "image_height", "image_steps"}:
            try:
                value = int(value)
            except (TypeError, ValueError):
                continue
        elif field == "image_cfg":
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
        elif field == "generate_comfy_images":
            value = value if isinstance(value, bool) else str(value).lower() in {"1", "true", "yes", "on"}
        setattr(settings, field, value)
    if settings.provider not in {"openai", "lm_studio"}:
        settings.provider = "openai"
    settings.timeout = max(10, settings.timeout)
    settings.image_width = max(256, min(2048, settings.image_width // 8 * 8))
    settings.image_height = max(256, min(2048, settings.image_height // 8 * 8))
    settings.image_steps = max(1, min(100, settings.image_steps))
    settings.image_cfg = max(0.0, min(30.0, settings.image_cfg))
    return settings


def save_design_settings(path: str | Path, settings: DesignAISettings) -> None:
    destination = Path(path)
    destination.write_text(
        "\n".join(
            [
                "# AI Design connection settings (API keys are never stored here)",
                *[
                    f"{key}={json.dumps(getattr(settings, field), ensure_ascii=False)}"
                    for key, field in KEYS.items()
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )

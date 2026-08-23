"""Persistent generation settings for the H3 Director desktop app."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


ENV_KEYS = {
    "server_url": "H3_COMFYUI_URL",
    "aspect_ratio": "H3_ASPECT_RATIO",
    "megapixels": "H3_MEGAPIXELS",
    "sampling_steps": "H3_SAMPLING_STEPS",
    "denoise": "H3_DENOISE",
    "rtx_video_super_resolution": "H3_RTX_VIDEO_SUPER_RESOLUTION",
    "history_poll_interval": "H3_HISTORY_POLL_INTERVAL",
    "generation_timeout": "H3_GENERATION_TIMEOUT",
    "http_request_timeout": "H3_HTTP_REQUEST_TIMEOUT",
}


@dataclass(slots=True)
class RenderSettings:
    server_url: str = "http://192.168.0.185:8189"
    aspect_ratio: str = "16:9"
    megapixels: float = 1.0
    sampling_steps: int = 8
    denoise: float = 1.0
    rtx_video_super_resolution: bool = True
    history_poll_interval: float = 1.0
    generation_timeout: int = 1800
    http_request_timeout: int = 30

    @classmethod
    def defaults(cls) -> "RenderSettings":
        return cls()

    @classmethod
    def from_mapping(cls, values: dict) -> "RenderSettings":
        defaults = asdict(cls.defaults())
        merged = {**defaults, **{key: value for key, value in values.items() if key in defaults}}
        def number(name: str, cast):
            try:
                return cast(merged[name])
            except (TypeError, ValueError):
                return cast(defaults[name])

        return cls(
            server_url=str(merged["server_url"]).strip() or defaults["server_url"],
            aspect_ratio=str(merged["aspect_ratio"]),
            megapixels=min(16.0, max(0.1, number("megapixels", float))),
            sampling_steps=max(1, number("sampling_steps", int)),
            denoise=min(1.0, max(0.0, number("denoise", float))),
            rtx_video_super_resolution=_as_bool(merged["rtx_video_super_resolution"]),
            history_poll_interval=max(0.1, number("history_poll_interval", float)),
            generation_timeout=max(10, number("generation_timeout", int)),
            http_request_timeout=max(1, number("http_request_timeout", int)),
        )


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def load_settings(env_path: str | Path) -> RenderSettings:
    path = Path(env_path)
    raw: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            raw[key.strip()] = _unquote(value)
    inverse = {env_key: field for field, env_key in ENV_KEYS.items()}
    return RenderSettings.from_mapping(
        {inverse[key]: value for key, value in raw.items() if key in inverse}
    )


def save_settings(env_path: str | Path, settings: RenderSettings) -> None:
    """Update only Director-owned keys and preserve unrelated .env content."""
    path = Path(env_path)
    existing = path.read_text(encoding="utf-8-sig").splitlines() if path.is_file() else []
    owned = set(ENV_KEYS.values())
    kept = [
        line
        for line in existing
        if not (
            "=" in line
            and line.split("=", 1)[0].strip() in owned
        )
    ]
    values = asdict(settings)
    generated = ["", "# MiniMax H3 Director settings"] if kept else ["# MiniMax H3 Director settings"]
    for field, env_key in ENV_KEYS.items():
        value = values[field]
        if isinstance(value, bool):
            text = "true" if value else "false"
        else:
            text = str(value)
        generated.append(f"{env_key}={text}")
    path.write_text("\n".join([*kept, *generated]).strip() + "\n", encoding="utf-8")

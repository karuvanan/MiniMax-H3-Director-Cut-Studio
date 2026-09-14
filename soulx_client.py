"""Small, independent client for the SoulX-Singer SVC Gradio API."""

from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from runtime_paths import PROJECT_ROOT, load_runtime_paths


DEFAULT_SOULX_SERVER = os.getenv("SOULX_API_URL", "http://192.168.0.185:7861")
SVC_API_NAME = "/_studio_start_svc"
SVC_ENDPOINT_ALIASES = (
    SVC_API_NAME,
    "/_start_svc",
    "/lazy_start_svc",
    "/start_svc",
    "/predict",
)
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "soulx_singer"
EXPECTED_CORE_PARAMETERS = (
    "prompt_audio",
    "target_audio",
    "prompt_vocal_sep",
    "target_vocal_sep",
    "auto_shift",
    "auto_mix_acc",
    "pitch_shift",
    "n_step",
    "cfg",
    "seed",
)
OPTIONAL_UNLOAD_ENDPOINTS = (
    "/_unload_svc",
    "/_unload_models",
    "/_unload",
    "/unload",
)

_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def normalize_server(server: str) -> str:
    value = str(server or "").strip().rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("SoulX API must be an http:// or https:// server address")
    return value


def _open(request: urllib.request.Request, timeout: float):
    hostname = (urllib.parse.urlparse(request.full_url).hostname or "").lower()
    direct = hostname in {"localhost", "127.0.0.1", "::1"}
    try:
        direct = direct or ipaddress.ip_address(hostname).is_private
    except ValueError:
        pass
    opener = _DIRECT_OPENER if direct else urllib.request
    return opener.open(request, timeout=max(1.0, float(timeout)))


def fetch_api_info(server: str, timeout: float = 10.0) -> dict[str, Any]:
    url = normalize_server(server) + "/gradio_api/info"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with _open(request, timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"SoulX API HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"SoulX connection failed: {exc.reason}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("SoulX API returned an invalid information response")
    return payload


def endpoint_parameters(info: dict[str, Any], api_name: str = SVC_API_NAME) -> list[str]:
    endpoints = info.get("named_endpoints") if isinstance(info, dict) else None
    endpoint = (endpoints or {}).get(api_name) if isinstance(endpoints, dict) else None
    parameters = endpoint.get("parameters") if isinstance(endpoint, dict) else None
    return [
        str(item.get("parameter_name") or "").strip()
        for item in (parameters or [])
        if isinstance(item, dict) and str(item.get("parameter_name") or "").strip()
    ]


def discover_svc_endpoint(info: dict[str, Any]) -> tuple[str, list[str]]:
    """Find the SVC endpoint by name first, then by its parameter contract.

    Gradio derives an API name from the callback name when the upstream UI does
    not provide ``api_name`` explicitly. Older Studio wrappers therefore exposed
    ``/lazy_start_svc`` while the original callback normally exposes
    ``/_start_svc``. The parameter contract is the stable part of this API.
    """

    endpoints = info.get("named_endpoints") if isinstance(info, dict) else None
    if not isinstance(endpoints, dict):
        return "", []

    by_folded = {str(name).casefold(): str(name) for name in endpoints}
    for candidate in SVC_ENDPOINT_ALIASES:
        actual = by_folded.get(candidate.casefold())
        if actual:
            return actual, endpoint_parameters(info, actual)

    best_name = ""
    best_parameters: list[str] = []
    best_score = 0
    for name in endpoints:
        parameters = endpoint_parameters(info, str(name))
        score = sum(parameter in parameters for parameter in EXPECTED_CORE_PARAMETERS)
        if score > best_score:
            best_name = str(name)
            best_parameters = parameters
            best_score = score
    if best_score >= max(6, len(EXPECTED_CORE_PARAMETERS) - 2):
        return best_name, best_parameters
    return "", []


def validate_svc_api(info: dict[str, Any]) -> list[str]:
    endpoint, parameters = discover_svc_endpoint(info)
    if not parameters:
        raise RuntimeError(f"SoulX endpoint {SVC_API_NAME} is not available")
    if (
        endpoint.casefold() == "/lazy_start_svc"
        and len(parameters) == 12
        and parameters[:10] == list(EXPECTED_CORE_PARAMETERS)
        and parameters[10:] == ["param_10", "param_11"]
    ):
        raise RuntimeError(
            "SoulX Server is running the outdated broken wrapper (/lazy_start_svc, "
            "12 inputs on a 10-parameter callback). Run restart_soulx_server.bat "
            "on the Server host, then reconnect."
        )
    missing = [name for name in EXPECTED_CORE_PARAMETERS if name not in parameters]
    if missing:
        raise RuntimeError("SoulX SVC endpoint is incompatible; missing: " + ", ".join(missing))
    return parameters


def find_unload_endpoint(info: dict[str, Any]) -> str:
    endpoints = info.get("named_endpoints") if isinstance(info, dict) else None
    if not isinstance(endpoints, dict):
        return ""
    by_folded = {str(name).casefold(): str(name) for name in endpoints}
    for candidate in OPTIONAL_UNLOAD_ENDPOINTS:
        if candidate.casefold() in by_folded:
            return by_folded[candidate.casefold()]
    return ""


def _result_path(value: Any) -> Path | None:
    if isinstance(value, (str, os.PathLike)):
        path = Path(value)
        return path if path.is_file() else None
    if isinstance(value, dict):
        for key in ("path", "name", "file", "url"):
            path = _result_path(value.get(key))
            if path:
                return path
        for nested in value.values():
            path = _result_path(nested)
            if path:
                return path
    if isinstance(value, (tuple, list)):
        for nested in value:
            path = _result_path(nested)
            if path:
                return path
    return None


def _unique_output_path(suffix: str = ".mp3") -> Path:
    from datetime import datetime

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return OUTPUT_DIR / f"soulx_clone_{stamp}{suffix}"


def _gradio_client(server: str, *, downloads: bool = True):
    from gradio_client import Client

    normalized = normalize_server(server)
    parsed = urllib.parse.urlparse(normalized)
    hostname = parsed.hostname or ""
    direct = hostname.casefold() in {"localhost", "127.0.0.1", "::1"}
    try:
        direct = direct or ipaddress.ip_address(hostname).is_private
    except ValueError:
        pass
    options: dict[str, Any] = {"verbose": False}
    if direct:
        options["httpx_kwargs"] = {"trust_env": False}
    if downloads:
        download_dir = OUTPUT_DIR / "_gradio_downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        options["download_files"] = download_dir
    return Client(normalized, **options)


def _to_mp3(source: Path) -> Path:
    target = _unique_output_path(".mp3")
    if source.suffix.casefold() == ".mp3":
        shutil.copy2(source, target)
        return target
    ffmpeg = load_runtime_paths().ffmpeg
    if not ffmpeg.is_file():
        raise RuntimeError(f"Bundled FFmpeg is missing: {ffmpeg}")
    subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "320k",
            str(target),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return target


def _request_kwargs(parameters: list[str], values: dict[str, Any]) -> dict[str, Any]:
    """Map logical values onto the endpoint's published component order."""

    anonymous_extended = (
        len(parameters) == 12
        and parameters[:10] == list(EXPECTED_CORE_PARAMETERS)
        and parameters[10:] == ["param_10", "param_11"]
    )
    if anonymous_extended:
        # This schema is produced when a 10-argument wrapper is attached to a
        # 12-input Gradio event. Names after auto_mix_acc are shifted by two,
        # but Gradio still validates values against the real component order.
        logical_order = [
            *EXPECTED_CORE_PARAMETERS[:6],
            "device_choice",
            "use_fp16",
            "pitch_shift",
            "n_step",
            "cfg",
            "seed",
        ]
        return {
            parameter: values[logical_name]
            for parameter, logical_name in zip(parameters, logical_order)
        }
    return {name: values[name] for name in parameters if name in values}


def convert_singing_voice(
    server: str,
    *,
    voice_reference: str | Path,
    source_song: str | Path,
    prompt_vocal_sep: bool = False,
    target_vocal_sep: bool = True,
    auto_shift: bool = True,
    auto_mix_acc: bool = True,
    pitch_shift: int = 0,
    n_step: int = 32,
    cfg: float = 1.0,
    seed: int = 42,
    device: str = "cuda",
    use_fp16: bool = True,
    timeout: float = 15.0,
) -> Path:
    """Convert source-song vocals to the voice-reference timbre and return an MP3."""

    prompt_path = Path(voice_reference)
    target_path = Path(source_song)
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Voice reference is missing: {prompt_path}")
    if not target_path.is_file():
        raise FileNotFoundError(f"Source song is missing: {target_path}")

    endpoint_info = fetch_api_info(server, timeout)
    endpoint_name, _ = discover_svc_endpoint(endpoint_info)
    parameters = validate_svc_api(endpoint_info)
    try:
        from gradio_client import handle_file
    except ImportError as exc:
        raise RuntimeError("gradio_client is not installed in the Studio runtime") from exc

    values: dict[str, Any] = {
        "prompt_audio": handle_file(str(prompt_path.resolve())),
        "target_audio": handle_file(str(target_path.resolve())),
        "prompt_vocal_sep": bool(prompt_vocal_sep),
        "target_vocal_sep": bool(target_vocal_sep),
        "auto_shift": bool(auto_shift),
        "auto_mix_acc": bool(auto_mix_acc),
        "pitch_shift": int(pitch_shift),
        "n_step": int(n_step),
        "cfg": float(cfg),
        "seed": int(seed),
        # Some server deployments expose these two additional controls while
        # the official WebUI fixes them at launch time. Send them only when the
        # discovered endpoint requests them.
        "device": str(device or "cuda"),
        "device_choice": str(device or "cuda"),
        "use_fp16": bool(use_fp16),
    }
    kwargs = _request_kwargs(parameters, values)
    missing_values = [name for name in parameters if name not in kwargs]
    if missing_values:
        raise RuntimeError(
            "SoulX server requires unsupported parameter(s): " + ", ".join(missing_values)
        )
    client = _gradio_client(server)
    result = client.predict(api_name=endpoint_name, **kwargs)
    generated = _result_path(result)
    if not generated:
        raise RuntimeError("SoulX completed without returning a downloadable audio file")
    return _to_mp3(generated)


def request_server_unload(server: str, timeout: float = 15.0) -> dict[str, Any]:
    """Ask an enhanced SoulX server to unload; never claim success if unsupported."""

    info = fetch_api_info(server, timeout)
    endpoint = find_unload_endpoint(info)
    if not endpoint:
        return {
            "supported": False,
            "unloaded": False,
            "endpoint": "",
            "warning": (
                "SoulX server has no unload endpoint. Stop/restart its launcher before "
                "running MiniMax H3 if GPU memory is tight."
            ),
        }
    try:
        import gradio_client  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("gradio_client is not installed in the Studio runtime") from exc
    client = _gradio_client(server, downloads=False)
    response = client.predict(api_name=endpoint)
    return {
        "supported": True,
        "unloaded": True,
        "endpoint": endpoint,
        "response": response,
        "warning": "",
    }

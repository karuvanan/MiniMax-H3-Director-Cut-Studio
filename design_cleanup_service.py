"""Release AI Design models after a design is applied to the workspace."""

from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request


_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def _open(request: urllib.request.Request, timeout: float):
    hostname = (urllib.parse.urlparse(request.full_url).hostname or "").lower()
    direct = hostname in {"localhost", "127.0.0.1", "::1"}
    try:
        direct = direct or ipaddress.ip_address(hostname).is_private
    except ValueError:
        pass
    opener = _DIRECT_OPENER if direct else urllib.request
    return opener.open(request, timeout=max(1.0, timeout))


def request(url: str, timeout: float, payload: dict | None = None) -> dict:
    data = None
    method = "GET"
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _open(req, timeout) as response:
            raw = response.read().decode("utf-8", errors="replace").strip()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:800]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Connection failed: {exc.reason}") from exc


def lm_origin(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url.strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid LM Studio base URL")
    return f"{parsed.scheme}://{parsed.netloc}"


def _lm_model_aliases(value: str) -> set[str]:
    normalized = str(value or "").strip().casefold().replace("\\", "/")
    normalized = re.sub(r"\.gguf$", "", normalized)
    aliases = {normalized}
    parts = [part for part in normalized.split("/") if part]
    if len(parts) > 1:
        parent = re.sub(r"(?:[-_.]gguf)$", "", parts[-2])
        if parent != parts[-2]:
            aliases.add(parent)
    return {item for item in aliases if item}


def unload_lm_studio(base_url: str, selected_model: str, timeout: float) -> list[str]:
    origin = lm_origin(base_url)
    catalog = request(origin + "/api/v1/models", timeout)
    selected = selected_model.strip().casefold()
    selected_aliases = _lm_model_aliases(selected_model)
    instances: list[str] = []
    for model in catalog.get("models") or []:
        model_keys = {
            str(model.get("key", "")).casefold(),
            str(model.get("selected_variant", "")).casefold(),
        }
        catalog_aliases: set[str] = set()
        for key in model_keys:
            catalog_aliases.update(_lm_model_aliases(key))
        if selected and not selected_aliases.intersection(catalog_aliases):
            continue
        for instance in model.get("loaded_instances") or []:
            if isinstance(instance, str):
                instance_id = instance
            else:
                instance_id = str(
                    instance.get("id")
                    or instance.get("instance_id")
                    or instance.get("identifier")
                    or ""
                )
            if instance_id:
                instances.append(instance_id)
    # Never guess an instance id from the saved model name. The saved model may
    # have been deleted or replaced since the previous Studio session, and an
    # unloaded catalogue entry legitimately has no loaded_instances. Only IDs
    # explicitly reported as loaded are safe unload targets.
    unloaded: list[str] = []
    errors: list[str] = []
    for instance_id in dict.fromkeys(instances):
        try:
            request(
                origin + "/api/v1/models/unload",
                timeout,
                {"instance_id": instance_id},
            )
            unloaded.append(instance_id)
        except Exception as exc:
            detail = str(exc).casefold()
            # A model can disappear between catalogue discovery and unload. In
            # that race it is already in the desired state.
            if "model_not_found" in detail or "is not loaded" in detail:
                continue
            errors.append(f"{instance_id}: {exc}")
    if errors and not unloaded:
        raise RuntimeError("; ".join(errors))
    return unloaded


def cleanup(job: dict) -> dict:
    timeout = float(job.get("timeout", 30))
    result = {"completed": True, "comfyui_unloaded": False, "lm_unloaded": [], "warnings": []}
    comfy_url = str(job.get("comfyui_server", "")).strip().rstrip("/")
    if comfy_url:
        try:
            request(
                comfy_url + "/free",
                timeout,
                {"unload_models": True, "free_memory": True},
            )
            result["comfyui_unloaded"] = True
        except Exception as exc:
            result["warnings"].append(f"ComfyUI unload failed: {exc}")
    if str(job.get("provider", "")).lower() == "lm_studio":
        try:
            result["lm_unloaded"] = unload_lm_studio(
                str(job.get("base_url", "")),
                str(job.get("model", "")),
                timeout,
            )
        except Exception as exc:
            result["warnings"].append(f"LM Studio unload failed: {exc}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job")
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    emit(cleanup(job))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        emit({"error": str(exc)})
        raise SystemExit(1)

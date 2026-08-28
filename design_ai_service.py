"""Crash-isolated OpenAI / LM Studio client for the AI Design page."""

from __future__ import annotations

import ipaddress
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from design_cleanup_service import unload_lm_studio


_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _urlopen(request: urllib.request.Request, timeout: float):
    hostname = (urllib.parse.urlparse(request.full_url).hostname or "").lower()
    direct = hostname in {"localhost", "127.0.0.1", "::1"}
    try:
        direct = direct or ipaddress.ip_address(hostname).is_private
    except ValueError:
        pass
    if direct:
        return _DIRECT_OPENER.open(request, timeout=timeout)
    return urllib.request.urlopen(request, timeout=timeout)


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def endpoint(base_url: str, suffix: str) -> str:
    base = base_url.strip().rstrip("/")
    if not base:
        raise ValueError("Base URL is required")
    return base + "/" + suffix.lstrip("/")


def request_json(url: str, *, api_key: str, timeout: float, payload: dict | None = None) -> dict:
    headers = {"Accept": "application/json"}
    data = None
    method = "GET"
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _urlopen(request, max(1.0, timeout)) as response:
            raw = response.read().decode("utf-8").strip()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:1200]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Connection failed: {exc.reason}") from exc


def response_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    chunks: list[str] = []
    for output in payload.get("output") or []:
        for content in output.get("content") or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(str(content["text"]))
    if chunks:
        return "\n".join(chunks)
    choices = payload.get("choices") or []
    if choices:
        content = (choices[0].get("message") or {}).get("content")
        if isinstance(content, str):
            return content
    raise RuntimeError("The model response did not contain text output")


def _model_family(value: str) -> str:
    """Return a stable family key after removing a GGUF quantization suffix."""
    text = str(value or "").strip().casefold().replace("\\", "/")
    text = re.sub(r"\.gguf$", "", text)
    text = re.sub(
        r"[-_.](?:q\d+(?:[_-][a-z0-9]+)*|f16|f32|bf16|iq\d+(?:[_-][a-z0-9]+)*)$",
        "",
        text,
    )
    return text


def _model_aliases(value: str) -> set[str]:
    normalized = str(value or "").strip().casefold().replace("\\", "/")
    aliases = {_model_family(normalized)}
    parts = [part for part in normalized.split("/") if part]
    if len(parts) > 1:
        parent = re.sub(r"(?:[-_.]gguf)$", "", parts[-2])
        if parent != parts[-2]:
            aliases.add(_model_family(parent))
    return {item for item in aliases if item}


def select_available_model(requested: str, models: list[str]) -> str:
    """Resolve a deleted LM Studio model to the closest available chat model."""
    available = [str(item).strip() for item in models if str(item).strip()]
    if not available:
        return ""
    requested_key = str(requested or "").strip().casefold()
    exact = next((item for item in available if item.casefold() == requested_key), "")
    if exact:
        return exact

    requested_aliases = _model_aliases(requested)
    same_family = [
        item for item in available if requested_aliases.intersection(_model_aliases(item))
    ]
    if same_family:
        return same_family[0]

    requested_parent = requested_key.rsplit("/", 1)[0] if "/" in requested_key else ""
    if requested_parent:
        same_parent = [
            item
            for item in available
            if item.casefold().rsplit("/", 1)[0] == requested_parent
        ]
        if same_parent:
            return same_parent[0]

    excluded = ("embed", "rerank", "clip", "vision", "whisper", "tts")
    chat_models = [
        item
        for item in available
        if not any(token in item.casefold() for token in excluded)
    ]
    return (chat_models or available)[0]


def available_openai_models(base_url: str, api_key: str, timeout: float) -> list[str]:
    payload = request_json(
        endpoint(base_url, "models"),
        api_key=api_key,
        timeout=timeout,
    )
    return [
        str(item.get("id", "")).strip()
        for item in payload.get("data") or []
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    ]


def generate(job: dict) -> dict:
    provider = str(job.get("provider", "openai")).lower()
    base_url = str(job.get("base_url", ""))
    api_key = str(job.get("api_key", ""))
    timeout = float(job.get("timeout", 120))
    model = str(job.get("model", "")).strip()
    system_prompt = str(job.get("system_prompt", ""))
    user_prompt = str(job.get("user_prompt", ""))
    schema = job.get("schema") or {}
    raw_schema_name = str(job.get("schema_name", "h3_director_design")).strip()
    schema_name = re.sub(r"[^A-Za-z0-9_-]", "_", raw_schema_name)[:64]
    schema_name = schema_name or "structured_response"
    try:
        max_output_tokens = int(job.get("max_output_tokens", 12000))
    except (TypeError, ValueError):
        max_output_tokens = 12000
    max_output_tokens = max(512, min(12000, max_output_tokens))
    if not model:
        raise ValueError("Model is required")
    if provider == "openai":
        payload = request_json(
            endpoint(base_url, "responses"),
            api_key=api_key,
            timeout=timeout,
            payload={
                "model": model,
                "input": [
                    {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                    {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "strict": True,
                        "schema": schema,
                    }
                },
                "max_output_tokens": max_output_tokens,
            },
        )
    else:
        models = available_openai_models(base_url, api_key, min(timeout, 30.0))
        # Older OpenAI-compatible local servers may return no model catalogue
        # even though chat/completions works. Keep the authored model in that
        # compatibility case; when a catalogue exists, stale IDs are repaired.
        model = select_available_model(model, models) or model
        chat_payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": max_output_tokens,
            # LM Studio reasoning models can spend the entire completion budget on
            # hidden thinking and return an empty content field. Director Design
            # needs the schema object itself, so request direct output mode.
            "reasoning_effort": "none",
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        try:
            payload = request_json(
                endpoint(base_url, "chat/completions"),
                api_key=api_key,
                timeout=timeout,
                payload=chat_payload,
            )
        except RuntimeError as exc:
            if "response_format" not in str(exc) and "json_schema" not in str(exc):
                raise
            chat_payload["response_format"] = {"type": "json_object"}
            payload = request_json(
                endpoint(base_url, "chat/completions"),
                api_key=api_key,
                timeout=timeout,
                payload=chat_payload,
            )
    return {"response": payload, "text": response_text(payload), "resolved_model": model}


def handle(job: dict) -> dict:
    action = job.get("action")
    if action == "comfy_checkpoints":
        payload = request_json(
            endpoint(str(job.get("base_url", "")), "object_info/CheckpointLoaderSimple"),
            api_key="",
            timeout=float(job.get("timeout", 20)),
        )
        values = (
            (((payload.get("CheckpointLoaderSimple") or {}).get("input") or {}).get("required") or {})
            .get("ckpt_name", [[]])[0]
        )
        checkpoints = [str(item) for item in values if isinstance(item, str)]
        return {"checkpoints": checkpoints}
    if action == "comfy_zimage_models":
        payload = request_json(
            endpoint(str(job.get("base_url", "")), "object_info/UNETLoader"),
            api_key="",
            timeout=float(job.get("timeout", 20)),
        )
        values = (
            (((payload.get("UNETLoader") or {}).get("input") or {}).get("required") or {})
            .get("unet_name", [[]])[0]
        )
        return {"zimage_models": [str(item) for item in values if isinstance(item, str)]}
    if action == "unload_comfy":
        request_json(
            endpoint(str(job.get("base_url", "")), "free"),
            api_key="",
            timeout=float(job.get("timeout", 30)),
            payload={"unload_models": True, "free_memory": True},
        )
        return {"comfy_unloaded": True}
    if action == "test":
        models = available_openai_models(
            str(job.get("base_url", "")),
            str(job.get("api_key", "")),
            float(job.get("timeout", 20)),
        )
        requested = str(job.get("model", "")).strip()
        return {
            "connected": True,
            "models": models[:100],
            "resolved_model": select_available_model(requested, models),
            "model_replaced": bool(requested)
            and requested.casefold() not in {item.casefold() for item in models},
        }
    if action == "generate":
        return {"generated": True, **generate(job)}
    if action == "unload_lm":
        return {
            "lm_unloaded": unload_lm_studio(
                str(job.get("base_url", "")),
                str(job.get("model", "")),
                float(job.get("timeout", 30)),
            )
        }
    raise ValueError(f"Unknown action: {action}")


def main() -> int:
    emit({"ready": True})
    for line in sys.stdin:
        try:
            job = json.loads(line)
            result = handle(job)
            emit({"job": job.get("job", ""), **result})
        except Exception as exc:
            emit({"job": locals().get("job", {}).get("job", ""), "error": str(exc)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

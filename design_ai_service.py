"""Crash-isolated OpenAI / LM Studio client for the AI Design page."""

from __future__ import annotations

import ipaddress
import json
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


def generate(job: dict) -> dict:
    provider = str(job.get("provider", "openai")).lower()
    base_url = str(job.get("base_url", ""))
    api_key = str(job.get("api_key", ""))
    timeout = float(job.get("timeout", 120))
    model = str(job.get("model", "")).strip()
    system_prompt = str(job.get("system_prompt", ""))
    user_prompt = str(job.get("user_prompt", ""))
    schema = job.get("schema") or {}
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
                        "name": "h3_director_design",
                        "strict": True,
                        "schema": schema,
                    }
                },
                "max_output_tokens": 12000,
            },
        )
    else:
        chat_payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            # LM Studio reasoning models can spend the entire completion budget on
            # hidden thinking and return an empty content field. Director Design
            # needs the schema object itself, so request direct output mode.
            "reasoning_effort": "none",
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "h3_director_design",
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
    return {"response": payload, "text": response_text(payload)}


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
        payload = request_json(
            endpoint(str(job.get("base_url", "")), "models"),
            api_key=str(job.get("api_key", "")),
            timeout=float(job.get("timeout", 20)),
        )
        models = [str(item.get("id", "")) for item in payload.get("data") or [] if item.get("id")]
        return {"connected": True, "models": models[:100]}
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

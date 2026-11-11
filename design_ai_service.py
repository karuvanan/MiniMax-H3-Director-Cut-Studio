"""Crash-isolated OpenAI / LM Studio client for the AI Design page."""

from __future__ import annotations

import base64
import ipaddress
import json
import mimetypes
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from design_cleanup_service import unload_lm_studio


_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
DEFAULT_STRUCTURED_OUTPUT_TOKENS = 32768
# Structured plans stay bounded so a local LM cannot spend tens of minutes
# filling an oversized prediction budget.  Source-video analysis reduces its
# prose through schema/prompt constraints and retries compactly instead.
MAX_STRUCTURED_OUTPUT_TOKENS = 32768
# A long source-video role ledger is different from an ordinary Design Plan:
# every source interval and every visible-role appearance is evidence that the
# UI must retain.  Permit a larger budget only when the caller explicitly opts
# into this forensic-analysis path; all normal Design/semantic jobs remain at
# the conservative 32K ceiling above.
MAX_LONG_FORM_STRUCTURED_OUTPUT_TOKENS = 65536


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


def response_finish_reason(payload: dict) -> str:
    """Normalize completion/truncation metadata across supported providers."""

    choices = payload.get("choices") or []
    if choices and isinstance(choices[0], dict):
        reason = str(choices[0].get("finish_reason", "")).strip()
        if reason:
            return reason
    status = str(payload.get("status", "")).strip()
    if status == "incomplete":
        details = payload.get("incomplete_details") or {}
        if isinstance(details, dict):
            return str(details.get("reason", "incomplete")).strip() or "incomplete"
    return status


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


# A Strata/LM Studio endpoint that is reachable but has nothing loaded answers
# the design request with a model-lookup failure, not a generation failure.  The
# Strata native host does this in two dialects: the OpenAI layer answers
# "Choose a loaded model ID.", and the runtime layer answers with its
# load/resolve wording (HTTP 409 "That model ID is not loaded. Choose one from
# /v1/models."), which the AI Design page used to publish verbatim as an opaque
# Hard Block.  Recognising the family lets the page load the model instead of
# blocking, and keeps the wording actionable when it cannot.
_MODEL_NOT_LOADED_MARKERS = (
    "that model id is not loaded",
    "choose one from /v1/models",
    "choose a loaded model id",
    "no model is loaded",
    "load a native strata model",
    "is not loaded or available",
)

# A host that rejects the *shape* of a completion is different from a host that
# failed to answer.  Strata answers, e.g.
#   HTTP 502 {"error":{"code":"structured_output_failed",
#     "message":"model did not return valid JSON: duplicate JSON key:
#     overall_soundscape"}}
# when a small local model writes one key twice, and llama.cpp-style servers say
# it differently.  In every dialect the design content may well be sound, so the
# request is relaxed a tier at a time rather than turned into a Hard Block.
_STRUCTURED_OUTPUT_MARKERS = (
    "structured_output_failed",
    "structured output failed",
    "did not return valid json",
    "duplicate json key",
    "invalid json",
    "json parse",
    "failed to parse",
    "not valid json",
    "exceeded max attempts",
)

# The server also refuses the contract outright when it cannot honour
# ``response_format`` at all, which the page already used to survive.
_SCHEMA_CAPABILITY_MARKERS = (
    "response_format",
    "json_schema",
    "json_object",
    "structured output",
)


def is_structured_output_error(message: object) -> bool:
    text = str(message or "").casefold()
    return any(marker in text for marker in _STRUCTURED_OUTPUT_MARKERS)


def is_schema_capability_error(message: object) -> bool:
    text = str(message or "").casefold()
    return any(marker in text for marker in _SCHEMA_CAPABILITY_MARKERS)


def reported_duplicate_key(message: object) -> str:
    """Return the key a host blamed for a duplicate, or ``""``.

    Naming it in the retry prompt is what stops a small model from repeating the
    same accident on the next attempt.
    """
    match = re.search(
        r"duplicate json key:\s*[\"']?([A-Za-z0-9_ -]{2,64})", str(message or ""), re.I
    )
    return match.group(1).strip() if match else ""


def unique_key_reminder(failure: RuntimeError) -> str:
    """The note that keeps a small model from repeating the same accident.

    Naming the key the host blamed (``overall_soundscape`` in the reported
    failure) is far more effective than a generic instruction.
    """
    offender = reported_duplicate_key(failure)
    return (
        "\n\nReturn one JSON object only. Write every key exactly once at each "
        "level"
        + (f", including {offender!r}" if offender else "")
        + "; never repeat a key."
    )


def with_unique_key_instruction(messages: list[dict], reminder: str) -> list[dict]:
    """Copy the chat turns with the no-duplicate-keys note on the last turn."""
    turns = [dict(item) for item in messages]
    if not turns:
        return turns
    content = turns[-1].get("content")
    if isinstance(content, list):
        turns[-1]["content"] = [*content, {"type": "text", "text": reminder.strip()}]
    else:
        turns[-1]["content"] = f"{str(content or '')}{reminder}"
    return turns


def run_structured_ladder(
    ask: object, first: RuntimeError, ladder: list[tuple[str, object, list[str], object]]
) -> tuple[object, str, list[str], RuntimeError | None]:
    """Work down the fallback tiers until the host accepts the completion.

    Each tier says when it is worth trying (``allowed``), so an unrelated
    failure such as an out-of-memory answer is reported once instead of burning
    several more generations.  Returns ``(payload, tier, images, failure)``.
    """
    exc: RuntimeError | None = first
    for label, body, images, allowed in ladder:
        if not allowed(exc if exc is not None else first):
            continue
        try:
            payload = ask(body)
        except RuntimeError as retry_exc:
            exc = retry_exc
            continue
        return payload, label, list(images), None
    return None, "", [], exc


def structured_output_failure(base_url: str, failure: RuntimeError) -> RuntimeError:
    """One honest sentence when no output tier was accepted."""
    return RuntimeError(
        f"{str(base_url or '').strip()} rejected every attempt at structured "
        f"output: {failure}. Try Create Director Design again, or pick a local "
        f"model that follows JSON instructions more reliably."
    )

# Strata starts a native instance in about a minute for a small model and a few
# minutes for an 80 GB GGUF, so the reload that clears this failure is polled
# with the page's own timeout, capped here so a stuck engine ends with a
# sentence instead of a Design page that waits forever.
NATIVE_LOAD_POLL_SECONDS = 2.0
NATIVE_LOAD_BUDGET_SECONDS = 900.0


def is_model_not_loaded_error(message: object) -> bool:
    text = str(message or "").casefold()
    return any(marker in text for marker in _MODEL_NOT_LOADED_MARKERS)


def strata_origin(base_url: str) -> str:
    parsed = urllib.parse.urlparse(str(base_url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def strata_library(base_url: str, api_key: str = "", timeout: float = 15.0) -> dict:
    """Return Strata's model library, or ``{}`` for a host that is not Strata.

    Only Strata answers ``GET /api/models`` with a variant list; LM Studio and
    plain llama.cpp servers answer 404, which keeps this probe side-effect free.
    """
    origin = strata_origin(base_url)
    if not origin:
        return {}
    try:
        payload = request_json(
            origin + "/api/models", api_key=api_key, timeout=min(20.0, max(1.0, timeout))
        )
    except Exception:
        return {}
    return payload if isinstance(payload.get("variants"), list) else {}


def strata_native_state(base_url: str, api_key: str = "", timeout: float = 20.0) -> dict:
    """Return Strata's own engine snapshot, or ``{}`` for a host that is not Strata.

    ``GET /api/native`` is the native host's whole picture: which models are
    installed (``installed.models``), which instances are serving (``instances``
    with ``apiModelId``/``aliases``/``status``), any server running outside the
    UI (``external``), and the recent engine jobs.  This is the only place that
    knows how to bring the model back; ``GET /api/models`` is the separate
    download catalogue for Strata's preview runtime and does not list what a
    native instance serves — this machine's ``iq3_s`` is installed natively and
    absent there, which is why the preview catalogue alone cannot reload it.
    """
    origin = strata_origin(base_url)
    if not origin:
        return {}
    try:
        payload = request_json(
            origin + "/api/native", api_key=api_key, timeout=min(30.0, max(1.0, timeout))
        )
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload if ("instances" in payload or "installed" in payload) else {}


def strata_recommendation(state: dict) -> str:
    """Return the model Strata's own sizing verdict suggests, or ``""``.

    Quoting it turns "load a model in Strata" into the one thing the user can
    actually click.
    """
    catalog = state.get("catalog") if isinstance(state.get("catalog"), dict) else {}
    recommendation = catalog.get("recommendation")
    if isinstance(recommendation, dict):
        label = str(recommendation.get("title") or recommendation.get("model") or "").strip()
        if label:
            return label
    if isinstance(recommendation, str) and recommendation.strip():
        return recommendation.strip()
    match = re.search(
        r"recommended for this PC:\s*([^;]+)", str(catalog.get("summary") or ""), re.I
    )
    return match.group(1).strip() if match else ""


def _variant_search_keys(variant: dict) -> list[str]:
    source = variant.get("source") if isinstance(variant.get("source"), dict) else {}
    values = [
        variant.get("id"),
        variant.get("name"),
        variant.get("label"),
        source.get("file"),
        source.get("repo"),
    ]
    keys: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        keys.append(text)
        if "/" in text or text.lower().endswith(".gguf"):
            keys.append(text.rsplit("/", 1)[-1])
    return keys


def pick_strata_variant(model: str, library: dict) -> tuple[str, list[str]]:
    """Find the installed Strata variant that serves ``model``.

    Strata's ``apiModelId`` for a loaded instance is the variant ID, so the
    saved Model ID is matched against the catalogue identity first, then
    against quantisation-stripped families and finally by containment.  Only
    installed/downloaded variants qualify; a model that still has to be
    downloaded is reported back so the page can say so.
    """
    variants = [item for item in (library.get("variants") or []) if isinstance(item, dict)]
    installed = [
        str(item.get("id") or "").strip()
        for item in variants
        if str(item.get("state") or "").casefold() in {"installed", "loaded"}
    ]
    wanted = str(model or "").strip().casefold()
    if not wanted:
        return "", installed
    wanted_aliases = {str(item).casefold() for item in _model_aliases(model)}

    def rank(variant: dict) -> int:
        keys = [key.casefold() for key in _variant_search_keys(variant)]
        if wanted in keys:
            return 0
        if any(alias in keys for alias in wanted_aliases):
            return 1
        if any(wanted in key or key in wanted for key in keys):
            return 2
        # 4 means "no match": the caller admits only scores below it, so a
        # merely unrelated variant can never win the fallback.
        return 4

    best_id = ""
    best_rank = 4
    for variant in variants:
        if str(variant.get("state") or "").casefold() not in {"installed", "loaded"}:
            continue
        variant_id = str(variant.get("id") or "").strip()
        if not variant_id:
            continue
        score = rank(variant)
        if score < best_rank:
            best_rank = score
            best_id = variant_id
    return (best_id if best_rank < 4 else ""), installed


def _instance_ids(instance: dict) -> set[str]:
    aliases = instance.get("aliases") if isinstance(instance.get("aliases"), list) else []
    values = [instance.get("apiModelId"), instance.get("model"), *aliases]
    return {str(item).strip().casefold() for item in values if str(item or "").strip()}


def pick_native_model(model: str, state: dict) -> tuple[str, list[str]]:
    """Match the page's Model ID to a model installed in the native host.

    A native host keys its installed models by the very ID a ready instance
    answers on ``/v1/models`` (``iq3_s`` on this machine), so matching goes
    installed ID → model_name/config file → quantisation-stripped family →
    containment.  The installed IDs are returned either way, so a refusal can
    name what the host actually has.
    """
    installed_block = state.get("installed") if isinstance(state.get("installed"), dict) else {}
    entries = [
        item for item in (installed_block.get("models") or []) if isinstance(item, dict)
    ]
    installed = [
        str(item.get("model") or "").strip()
        for item in entries
        if str(item.get("model") or "").strip()
    ]
    wanted = str(model or "").strip().casefold()
    if not wanted:
        return "", installed
    wanted_aliases = {str(item).casefold() for item in _model_aliases(model)}

    def rank(entry: dict) -> int:
        keys = [
            str(item or "").strip().casefold()
            for item in (entry.get("model"), entry.get("model_name"), entry.get("config"))
            if str(item or "").strip()
        ]
        if wanted in keys:
            return 0
        if any(alias in keys for alias in wanted_aliases):
            return 1
        if any(wanted in key or key in wanted for key in keys):
            return 2
        # 4 means "no match": only scores below it are ever admitted.
        return 4

    best_id, best_rank = "", 4
    for entry in entries:
        model_id = str(entry.get("model") or "").strip()
        if not model_id:
            continue
        score = rank(entry)
        if score < best_rank:
            best_rank, best_id = score, model_id
    return (best_id if best_rank < 4 else ""), installed


def wait_for_native_instance(
    base_url: str, api_key: str, wanted: str, budget: float, job_id: str
) -> tuple[bool, str]:
    """Poll Strata until an instance is ready, the load job fails, or time runs out.

    A native load takes about a minute for a small model and a few minutes for
    an 80 GB one; the budget is the page's own timeout capped at
    ``NATIVE_LOAD_BUDGET_SECONDS``, so a stuck engine ends with a sentence
    instead of a hung Design page.
    """
    deadline = time.monotonic() + max(10.0, float(budget))
    seen_label = ""
    while True:
        state = strata_native_state(base_url, api_key, timeout=10.0)
        instances = state.get("instances") if isinstance(state.get("instances"), list) else []
        for instance in instances:
            if (
                not isinstance(instance, dict)
                or str(instance.get("status") or "").casefold() != "ready"
            ):
                continue
            name = str(instance.get("label") or instance.get("apiModelId") or "").strip()
            if wanted.casefold() in _instance_ids(instance):
                return True, name or wanted
            # The native host runs one instance at a time and the caller only
            # arrives here when nothing was loaded, so any ready instance is the
            # one just started; generate_once() re-reads /v1/models afterwards,
            # which also tolerates Strata's "--2" suffix on an ID collision.
            seen_label = seen_label or name
        jobs = state.get("jobs") if isinstance(state.get("jobs"), list) else []
        for item in jobs:
            if not isinstance(item, dict) or str(item.get("id") or "") != job_id:
                continue
            status = str(item.get("state") or "").casefold()
            if status == "error":
                return False, str(
                    item.get("error") or item.get("summary") or "the load job failed"
                )
            if status in {"cancelled", "canceled"}:
                return False, "the load was cancelled"
        if time.monotonic() >= deadline:
            return False, (
                f"Strata was still starting {wanted!r} after {int(budget)} seconds"
                + (f" (last report: {seen_label})" if seen_label else "")
            )
        time.sleep(NATIVE_LOAD_POLL_SECONDS)


def load_native_model(
    base_url: str, api_key: str, model: str, timeout: float, state: dict | None = None
) -> tuple[bool, str]:
    """Start an installed model through Strata's native engine.

    ``POST /api/native/operations {kind:"load"}`` is the call the Strata
    window's Load button makes.  It answers 202 with the job and starts the
    engine; the instance shows up on ``/v1/models`` when it is ready, which is
    what lets a Design run continue after the model was unloaded for ComfyUI.
    """
    origin = strata_origin(base_url)
    if not origin:
        return False, "the base URL is not reachable"
    state = strata_native_state(base_url, api_key) if state is None else state
    if not state:
        return False, "this endpoint is not a Strata native host"
    native_id, installed = pick_native_model(model, state)
    if not native_id:
        if installed:
            return False, (
                f"no native Strata model matches {model!r} "
                f"(installed: {', '.join(installed)})"
            )
        return False, f"Strata has no model installed, so {model!r} cannot be started"
    external = [
        item for item in (state.get("external") or []) if isinstance(item, (dict, str)) and item
    ]
    if external:
        return False, (
            "a Strata server is already running outside the Strata window, so this "
            "host will not load a model of its own"
        )
    try:
        started = request_json(
            origin + "/api/native/operations",
            api_key=api_key,
            timeout=30.0,
            payload={"kind": "load", "args": {"model": native_id}},
        )
    except Exception as exc:
        return False, f"Strata refused to start {native_id}: {exc}"
    job_id = str(started.get("id") or "") if isinstance(started, dict) else ""
    budget = min(max(120.0, float(timeout or 120.0)), NATIVE_LOAD_BUDGET_SECONDS)
    return wait_for_native_instance(base_url, api_key, native_id, budget, job_id)


def load_strata_model(
    base_url: str, api_key: str, model: str, timeout: float, state: dict | None = None
) -> tuple[bool, str]:
    """Start ``model`` in Strata: native engine first, preview runtime second.

    The native engine is what serves the model an agent session is using;
    ``POST /api/models/{id}/load`` belongs to Strata's preview runtime and only
    knows its download catalogue, so it is the fallback for a host that runs
    that runtime instead.
    """
    origin = strata_origin(base_url)
    if not origin:
        return False, "the base URL is not reachable"
    state = strata_native_state(base_url, api_key) if state is None else state
    library = strata_library(base_url, api_key)
    if not state and not library:
        return False, "this endpoint is not a Strata host, so the app cannot load a model in it"
    loaded, detail = load_native_model(base_url, api_key, model, timeout, state=state)
    if loaded:
        return True, detail
    if not library:
        return False, detail
    variant_id, _installed = pick_strata_variant(model, library)
    if not variant_id:
        return False, detail
    try:
        request_json(
            f"{origin}/api/models/{urllib.parse.quote(variant_id)}/load",
            api_key=api_key,
            timeout=max(120.0, min(max(1.0, timeout), 1800.0)),
            payload={},
        )
    except Exception as exc:
        return False, f"{detail}; the preview runtime also refused {variant_id}: {exc}"
    return True, variant_id


def recover_unloaded_model(job: dict) -> RuntimeError | None:
    """Load the requested model locally when nothing is loaded; else explain.

    Returns ``None`` when the caller should retry the generation, and a
    replacement error when the user has to act.  A *different* model that is
    already loaded is never evicted: silently replacing a working model would
    cost a long reload for whoever else is using the endpoint, so the page is
    told to pick the loaded ID instead.
    """
    base_url = str(job.get("base_url", ""))
    api_key = str(job.get("api_key", ""))
    model = str(job.get("model", "")).strip()
    timeout = float(job.get("timeout", 120) or 120)
    loaded_ids: list[str] = []
    try:
        loaded_ids = available_openai_models(base_url, api_key, min(timeout, 15.0))
    except Exception:
        loaded_ids = []
    if loaded_ids:
        return RuntimeError(
            f"Model {model!r} is not loaded at {base_url}. Loaded model ID(s): "
            f"{', '.join(loaded_ids)}. Pick one of those as Model ID, or load "
            f"{model!r} in the model host first."
        )
    state = strata_native_state(base_url, api_key)
    loaded, detail = load_strata_model(base_url, api_key, model, timeout, state=state)
    if not loaded:
        hint = strata_recommendation(state)
        advice = (
            f"Load {hint!r} in Strata (Models -> Load)"
            if hint and hint.casefold() != model.casefold()
            else "Load a model in Strata (Models -> Load)"
        )
        return RuntimeError(
            f"No model is loaded at {base_url}, and the app could not start "
            f"{model!r}: {detail}. {advice}, then run Test Connection."
        )
    # Strata publishes the new instance on /v1/models as soon as the load
    # returns; poll briefly so the retry sees a real catalogue.
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        try:
            if available_openai_models(base_url, api_key, 5.0):
                break
        except Exception:
            pass
        time.sleep(0.5)
    return None


def generate(job: dict) -> dict:
    """Ask the design model for structured JSON, starting it locally if needed.

    A reachable model host that has nothing loaded answers with a model-lookup
    failure instead of a generation failure, so the request is retried once
    after ``recover_unloaded_model`` has started the model — or after the user
    has been told what to load.  Every other failure propagates unchanged.
    """
    try:
        return generate_once(job)
    except RuntimeError as first:
        if not is_model_not_loaded_error(first):
            raise
        failure = recover_unloaded_model(job)
        if failure is not None:
            raise failure from first
        try:
            return generate_once(job)
        except RuntimeError as retry:
            if not is_model_not_loaded_error(retry):
                raise
            raise RuntimeError(
                f"{str(job.get('base_url', '')).strip()} still reports no loaded "
                f"model for {str(job.get('model', '')).strip()!r} after Strata "
                f"started it: {retry}"
            ) from retry


def generate_once(job: dict) -> dict:
    provider = str(job.get("provider", "openai")).lower()
    base_url = str(job.get("base_url", ""))
    api_key = str(job.get("api_key", ""))
    timeout = float(job.get("timeout", 120))
    model = str(job.get("model", "")).strip()
    system_prompt = str(job.get("system_prompt", ""))
    user_prompt = str(job.get("user_prompt", ""))
    require_image_input = bool(job.get("require_image_input", False))
    try:
        max_input_images = int(job.get("max_input_images", 3) or 3)
    except (TypeError, ValueError, OverflowError):
        max_input_images = 3
    # Ordinary Design stays at the proven three-image ceiling. The caller must
    # explicitly opt into a larger forensic storyboard request; six images are
    # enough for 96 readable 4x4 panels without sending an unbounded payload.
    max_input_images = max(1, min(6, max_input_images))
    input_images: list[str] = []
    for raw_path in job.get("input_image_paths") or []:
        path = Path(str(raw_path)).expanduser()
        if not path.is_file():
            continue
        mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        input_images.append(f"data:{mime_type};base64,{encoded}")
        if len(input_images) >= max_input_images:
            break
    if require_image_input and not input_images:
        raise ValueError(
            "This analysis requires direct image input, but no readable image was attached"
        )
    schema = job.get("schema") or {}
    raw_schema_name = str(job.get("schema_name", "h3_director_design")).strip()
    schema_name = re.sub(r"[^A-Za-z0-9_-]", "_", raw_schema_name)[:64]
    schema_name = schema_name or "structured_response"
    try:
        max_output_tokens = int(
            job.get("max_output_tokens", DEFAULT_STRUCTURED_OUTPUT_TOKENS)
        )
    except (TypeError, ValueError):
        max_output_tokens = DEFAULT_STRUCTURED_OUTPUT_TOKENS
    output_token_ceiling = (
        MAX_LONG_FORM_STRUCTURED_OUTPUT_TOKENS
        if bool(job.get("allow_large_structured_output", False))
        else MAX_STRUCTURED_OUTPUT_TOKENS
    )
    max_output_tokens = max(512, min(output_token_ceiling, max_output_tokens))
    if not model:
        raise ValueError("Model is required")
    if provider == "openai":
        strict_format = {
            "type": "json_schema",
            "name": schema_name,
            "strict": True,
            "schema": schema,
        }

        def openai_payload(
            images: list[str], prompt: str, output_format: dict | None
        ) -> dict:
            user_content = [{"type": "input_text", "text": prompt}]
            user_content.extend(
                {"type": "input_image", "image_url": image_url}
                for image_url in images
            )
            body = {
                "model": model,
                "input": [
                    {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                    {"role": "user", "content": user_content},
                ],
                "max_output_tokens": max_output_tokens,
            }
            if output_format is not None:
                # The Responses API puts its structured-output contract here.
                body["text"] = {"format": output_format}
            return body

        def ask_responses(body: dict) -> dict:
            return request_json(
                endpoint(base_url, "responses"),
                api_key=api_key,
                timeout=timeout,
                payload=body,
            )

        def accepts_relaxed_format(failure: RuntimeError) -> bool:
            return is_structured_output_error(failure) or is_schema_capability_error(failure)

        keep_images = bool(input_images) and not require_image_input
        plain_images = input_images if keep_images else []
        structured_mode = "json_schema"
        try:
            payload = ask_responses(openai_payload(input_images, user_prompt, strict_format))
        except RuntimeError as first:
            # A rejected shape is relaxed one tier at a time: unconstrained
            # JSON object, then plain JSON text, each asking for the keys once.
            # The page still gets a design it can normalise instead of stopping.
            reminder = unique_key_reminder(first)
            ladder = [
                (
                    "json_object",
                    openai_payload(
                        input_images, user_prompt + reminder, {"type": "json_object"}
                    ),
                    input_images,
                    accepts_relaxed_format,
                ),
            ]
            if keep_images:
                ladder.append(
                    (
                        "json_object_text_only",
                        openai_payload([], user_prompt + reminder, {"type": "json_object"}),
                        [],
                        # A model that cannot see the P1 plates is worth one
                        # text-only try, whatever the first answer said.
                        lambda failure: True,
                    )
                )
            ladder.append(
                (
                    "plain_json",
                    openai_payload(plain_images, user_prompt + reminder, None),
                    plain_images,
                    accepts_relaxed_format,
                )
            )
            payload, tier, images_used, failure = run_structured_ladder(
                ask_responses, first, ladder
            )
            if payload is None:
                assert failure is not None
                if is_structured_output_error(failure):
                    raise structured_output_failure(base_url, failure) from failure
                raise failure
            structured_mode, input_images = tier, images_used
    else:
        models = available_openai_models(base_url, api_key, min(timeout, 30.0))
        if bool(job.get("require_exact_model", False)) and models and not any(
            item.casefold() == model.casefold() for item in models
        ):
            raise RuntimeError(
                f"Required LM Studio model {model!r} is not loaded or available"
            )
        # Older OpenAI-compatible local servers may return no model catalogue
        # even though chat/completions works. Keep the authored model in that
        # compatibility case; when a catalogue exists, stale IDs are repaired.
        model = select_available_model(model, models) or model
        user_content: str | list[dict] = user_prompt
        if input_images:
            user_content = [{"type": "text", "text": user_prompt}] + [
                {"type": "image_url", "image_url": {"url": image_url}}
                for image_url in input_images
            ]
        try:
            temperature = float(job.get("temperature", 0.3))
        except (TypeError, ValueError):
            temperature = 0.3
        temperature = min(2.0, max(0.0, temperature))
        chat_payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
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
        def ask_chat(body: dict) -> dict:
            return request_json(
                endpoint(base_url, "chat/completions"),
                api_key=api_key,
                timeout=timeout,
                payload=body,
            )

        def accepts_relaxed_format(failure: RuntimeError) -> bool:
            return is_structured_output_error(failure) or is_schema_capability_error(failure)

        def relaxed_payload(
            output_format: dict | None, images: list[str], reminder: str
        ) -> dict:
            """Copy the chat request with another output contract and the note.

            The P1 plates are kept while the schema is loosened, because the
            model still has to count the real cast; only the text-only tier
            gives them up.
            """
            body = dict(chat_payload)
            if output_format is None:
                body.pop("response_format", None)
            else:
                body["response_format"] = output_format
            turns = with_unique_key_instruction(chat_payload["messages"], reminder)
            if not images:
                turns[-1]["content"] = user_prompt + reminder
            body["messages"] = turns
            return body

        keep_images = bool(input_images) and not require_image_input
        structured_mode = "json_schema"
        try:
            payload = ask_chat(chat_payload)
        except RuntimeError as first:
            # The host answered but threw the completion away, most often
            # because a small local model wrote one key twice:
            #   HTTP 502 {"code":"structured_output_failed","message":"model did
            #   not return valid JSON: duplicate JSON key: overall_soundscape"}
            # That is a formatting accident, not a failed design, so relax the
            # contract one tier at a time instead of stopping the page with a
            # Hard Block.  ``normalize_design_plan`` repairs the looser shape.
            reminder = unique_key_reminder(first)
            json_object = {"type": "json_object"}
            ladder = [
                (
                    "json_object",
                    relaxed_payload(json_object, input_images, reminder),
                    input_images,
                    accepts_relaxed_format,
                ),
            ]
            if keep_images:
                ladder.append(
                    (
                        "json_object_text_only",
                        relaxed_payload(json_object, [], reminder),
                        [],
                        # A model that cannot take the P1 plates still deserves
                        # one text-only attempt, whatever the first answer said.
                        lambda failure: True,
                    )
                )
            plain_images = [] if keep_images else input_images
            ladder.append(
                (
                    "plain_json",
                    relaxed_payload(None, plain_images, reminder),
                    plain_images,
                    accepts_relaxed_format,
                )
            )
            payload, tier, images_used, failure = run_structured_ladder(
                ask_chat, first, ladder
            )
            if payload is None:
                assert failure is not None
                if is_structured_output_error(failure):
                    raise structured_output_failure(base_url, failure) from failure
                raise failure
            structured_mode, input_images = tier, images_used
    finish_reason = response_finish_reason(payload)
    try:
        text = response_text(payload)
    except RuntimeError:
        # A provider may report a length/incomplete stop before publishing even
        # a partial content field.  Preserve that state for the UI recovery
        # path instead of collapsing it into an opaque worker error.
        if finish_reason.casefold() not in {
            "length", "incomplete", "max_output_tokens", "max_tokens"
        }:
            raise
        text = ""
    return {
        "response": payload,
        "text": text,
        "resolved_model": model,
        "finish_reason": finish_reason,
        "output_characters": len(text),
        "max_output_tokens": max_output_tokens,
        "usage": payload.get("usage") or {},
        "input_images_used": len(input_images),
        # Which output contract was finally accepted.  "json_schema" is the
        # normal case; anything else means the host refused a stricter answer
        # and the page is working from a looser shape it still repairs.
        "structured_mode": structured_mode,
    }


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

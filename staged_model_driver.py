"""Staged model driver: serialize LM Studio (Qwen3.8) and ComfyUI (H3) on one machine.

Solves the model-unload problem for live verification runs with three rules:

1. Python staged driving - every stage is a separate subcommand, and ``run``
   chains them in order instead of letting one long process hold both models.
2. ComfyUI and Qwen3.8 are never loaded at the same time - ``run`` unloads
   every loaded Qwen3.8 instance from LM Studio *before* the H3 worker starts,
   and verifies the unload through the live model catalogue plus VRAM telemetry
   (the catalogue can lag behind a successful unload, or an open LM Studio chat
   tab may auto-reload the model).
3. ``/free`` after every test - after the worker exits (success or failure) the
   driver POSTs ComfyUI ``/free`` with ``unload_models=true`` and verifies that
   VRAM actually dropped before reporting the manifest.

Subcommands:
  status            Read-only snapshot of LM Studio instances, ComfyUI queue and VRAM.
  unload-qwen       Unload every loaded Qwen3.8 instance, then verify it is clean.
  load-qwen         Explicitly load the configured Qwen model (agent side), verified via catalogue.
  wait-comfy        Wait until the H3 node classes are registered in object_info.
  free              POST /free to ComfyUI and verify the VRAM release.
  run JOB.json      Staged pipeline: unload-qwen -> wait-comfy -> worker -> /free -> report.
  report JOB.json   Read and print the job manifest summary (no GPU work).

Usage:
  python staged_model_driver.py status
  python staged_model_driver.py unload-qwen
  python staged_model_driver.py wait-comfy --timeout 900
  python staged_model_driver.py free
  python staged_model_driver.py run "example\\...\\preview_....job.json"
  python staged_model_driver.py report "example\\...\\preview_....job.json"

Environment overrides:
  H3_COMFYUI_URL            ComfyUI base URL (default http://192.168.0.185:8189)
  H3_LM_STUDIO_ORIGIN       LM Studio origin without /v1 (default from design_ai.env,
                            else http://192.168.0.185:1234)
  H3_STAGE_QWEN_KEY_FILTER  catalogue key substring that marks a Qwen instance ("qwen3")
  H3_STAGE_QWEN_LOAD_MODEL  model name for load-qwen (default from design_ai.env's
                            H3_DESIGN_LM_STUDIO_MODEL, else qwen3.8-uncensored-mtp)
  H3_LM_ENGINE_KIND         force the host API dialect: "strata" or "lmstudio"
                            (default: probe GET /api/v1/models then GET /api/models)
  H3_STAGE_QWEN_FORCE_CANCEL  "1" (default) cancels in-flight host requests when
                             an unload is refused 409; "0" keeps the polite
                             wait-only behaviour.

Supersedes the scratch copy at _dsh_verify_9/staged_driver.py for new runs.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent
DEFAULT_COMFY_URL = "http://192.168.0.185:8189"
DEFAULT_LM_ORIGIN = "http://127.0.0.1:47831"
MIN_VRAM_DROP_GB = 8.0
MAX_VRAM_PERCENT = 50.0
VRAM_CHECK_WAIT_SECONDS = 30.0
DEFAULT_QWEN_LOAD_MODEL = "iq3_s"
LOAD_POLL_SECONDS = 180.0
LOAD_REQUEST_TIMEOUT = 300.0
# The DSH tray proxy keeps /responses completions open on the Qwen instance for
# 8-17s right after it reloads the model, so a short window routinely ended the
# whole staged run on HTTP 409 (2026-10-25 round 17: both jobs aborted before
# ComfyUI ever saw them). The cancel sweeps below make a longer window cheap.
UNLOAD_POLL_SECONDS = 90.0
# Host request states that still occupy the instance (i.e. block an unload).
# Measured live on 2026-10-26 (working/_strata_states_live_probe_20261026.py):
# the tray proxy's warm-up completion sits in "queued" and then "generating",
# both with cancellable=true, while finished rows linger in the ledger forever
# as state="done", cancellable=false.  Round 18's S10 Job burned 90 seconds of
# HTTP 409 because "generating" was missing here, so the cancel sweep matched
# nothing and the whole staged run aborted before ComfyUI saw the Job.
INFLIGHT_REQUEST_STATES = {
    "queued", "starting", "started", "running", "waiting", "pending",
    "in_progress", "generating", "streaming", "processing",
}
# Ledger states that are finished.  A cancellable row in any *other* state is
# still treated as live, so a host build that renames a state cannot push us
# back into the 409 loop that just cost a render.
TERMINAL_REQUEST_STATES = {
    "done", "completed", "complete", "finished", "failed", "error",
    "cancelled", "canceled", "aborted", "closed", "removed",
}

import design_cleanup_service


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def comfy_url() -> str:
    return (os.environ.get("H3_COMFYUI_URL") or DEFAULT_COMFY_URL).rstrip("/")


def lm_origin() -> str:
    override = os.environ.get("H3_LM_STUDIO_ORIGIN", "").strip()
    if override:
        return design_cleanup_service.lm_origin(override)
    env_file = ROOT / "design_ai.env"
    try:
        text = env_file.read_text(encoding="utf-8")
    except OSError:
        return DEFAULT_LM_ORIGIN
    for line in text.splitlines():
        entry = line.strip().strip('"')
        if entry.startswith("H3_DESIGN_LM_STUDIO_BASE_URL="):
            value = entry.split("=", 1)[1].strip().strip('"')
            try:
                return design_cleanup_service.lm_origin(value)
            except ValueError:
                return DEFAULT_LM_ORIGIN
    return DEFAULT_LM_ORIGIN


def qwen_key_filter() -> str:
    return (os.environ.get("H3_STAGE_QWEN_KEY_FILTER") or "qwen3").casefold()


def qwen_load_model() -> str:
    override = os.environ.get("H3_STAGE_QWEN_LOAD_MODEL", "").strip()
    if override:
        return override
    env_file = ROOT / "design_ai.env"
    try:
        text = env_file.read_text(encoding="utf-8")
    except OSError:
        return DEFAULT_QWEN_LOAD_MODEL
    for line in text.splitlines():
        entry = line.strip().strip('"')
        if entry.startswith("H3_DESIGN_LM_STUDIO_MODEL="):
            value = entry.split("=", 1)[1].strip().strip('"')
            if value:
                return value
    return DEFAULT_QWEN_LOAD_MODEL

# Liveness window for comfy_claim.json, matching the H3 tray and the DSH tray guard.
# A claim is a phase lock, not a lease: 5400s meant one crashed run hid the GPU from
# Qwen for 90 minutes (measured 2026-11-10: unload 12:42:47 -> reload 14:13:03).
COMFY_CLAIM_TTL_SECONDS = 900


def comfy_claim_path() -> Path:
    override = os.environ.get("H3_COMFY_CLAIM_PATH", "").strip()
    if override:
        return Path(override)
    return ROOT / "ai_libraries_common" / "director_studio_h3_status_tray" / "comfy_claim.json"


def write_comfy_claim(note: str = "phase") -> None:
    """Tell the status tray that a ComfyUI phase is starting (pause its Qwen auto-load)."""
    try:
        path = comfy_claim_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"ts": int(time.time()), "note": note}), encoding="utf-8")
    except OSError as exc:
        emit({"stage": "comfy-claim", "warn": f"could not write claim ({exc})"})


def clear_comfy_claim() -> None:
    try:
        path = comfy_claim_path()
        if path.is_file():
            path.unlink()
    except OSError as exc:
        emit({"stage": "comfy-claim", "warn": f"could not clear claim ({exc})"})


def comfy_claim_age_seconds() -> float | None:
    try:
        raw = comfy_claim_path().read_text(encoding="utf-8")
        if not raw.strip():
            return None
        ts = int(json.loads(raw)["ts"])
        return max(0.0, time.time() - ts)
    except (OSError, ValueError, KeyError):
        return None


# --- Round 113: a claim the GPU phase keeps, instead of a note it writes once ------------------
# The status tray honours comfy_claim.json only while its ts is younger than its 120-second liveness
# grace, or while ComfyUI really has queue work, or while active_run.json says a job is live
# (h3_status_tray.ps1 Test-ComfyClaimActive, rewritten on 2026-11-10 away from the 5400-second lease
# that parked Qwen for 90 minutes).  A Studio-launched take writes the claim once before generation
# and never writes active_run.json at all, so the first queue-idle stretch past two minutes - the
# reference upload, the SAM3.1 aux gap, the ffmpeg composite - let the tray delete the claim and load
# a ~20 GB Qwen straight back into the phase that still needed the VRAM (owner flips measured
# 2026-11-10: 19:35/19:36, 21:32/21:37, 21:39/21:40, 22:09/22:10, each reload 45-57 seconds).
# The process that owns the GPU now renews the claim for as long as it lives.  A process that died
# simply stops renewing, which is what the tray's own liveness rule asks for: Qwen returns inside the
# grace window instead of an hour and a half later.
COMFY_CLAIM_HEARTBEAT_SECONDS = 45
# The tray's grace is 120 seconds; an interval at or above it lets one slow tick release the GPU.
COMFY_CLAIM_HEARTBEAT_MAX_SECONDS = 110

_claim_lease: dict[str, Any] | None = None


def comfy_claim_heartbeat_seconds() -> int:
    """Renewal interval for the GPU claim; ``0`` puts the old write-it-once behaviour back."""

    raw = os.environ.get("H3_COMFY_CLAIM_HEARTBEAT_SECONDS", "").strip()
    if not raw:
        return COMFY_CLAIM_HEARTBEAT_SECONDS
    try:
        value = int(float(raw))
    except ValueError:
        return COMFY_CLAIM_HEARTBEAT_SECONDS
    return max(0, min(COMFY_CLAIM_HEARTBEAT_MAX_SECONDS, value))


def read_comfy_claim() -> dict[str, Any] | None:
    """The claim exactly as the tray reads it, or None when it is missing or unreadable."""

    try:
        raw = comfy_claim_path().read_text(encoding="utf-8")
    except OSError:
        return None
    if not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def touch_comfy_claim(note: str = "") -> bool:
    """Renew the claim, re-arming it when the tray has already released it.

    The process that still owns the GPU is the authority on who owns the GPU, so a claim the tray
    dropped is written again rather than treated as gone; the tray re-reads it on its next tick.
    Keys the tray does not care about (the owner, the job file) survive the rewrite.
    """

    path = comfy_claim_path()
    payload = read_comfy_claim() or {}
    payload["ts"] = int(time.time())
    if note:
        payload["note"] = note
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return True
    except OSError as exc:
        emit({"stage": "comfy-claim", "warn": f"could not renew claim ({exc})"})
        return False


def claim_lease_state() -> dict[str, Any]:
    """What the tray can see right now, for the manifest: a take must be able to prove who held the GPU."""

    claim = read_comfy_claim()
    if claim is None:
        return {"claim": "none", "claim_note": "", "claim_age_s": None}
    age = comfy_claim_age_seconds()
    return {
        "claim": "held",
        "claim_note": str(claim.get("note", "")),
        "claim_age_s": round(age, 1) if age is not None else None,
    }


def _comfy_claim_lease_loop(lease: dict[str, Any], interval: int, extra) -> None:
    waiter = lease.get("stop_event")
    while waiter is None or not waiter.wait(interval):
        if touch_comfy_claim(str(lease.get("note", ""))):
            lease["renewals"] = int(lease.get("renewals", 0)) + 1
        if extra is None:
            continue
        try:
            extra()
        except Exception as exc:  # a lease must never fail a Shot
            emit({"stage": "comfy-claim", "warn": f"lease side effect failed ({exc})"})


def start_comfy_claim_lease(note: str = "phase", extra=None) -> dict[str, Any]:
    """Hold the GPU for as long as this process lives. Idempotent; returns the live counters.

    ``extra`` runs on every renewal tick; the staged driver uses it to keep its own
    active_run.json fresh, which is the second liveness signal the tray accepts.
    """

    global _claim_lease
    if _claim_lease is not None:
        return _claim_lease
    interval = comfy_claim_heartbeat_seconds()
    lease: dict[str, Any] = {
        "note": str(note or "phase"),
        "interval_seconds": interval,
        "renewals": 0,
        "threaded": False,
        "stopped": False,
    }
    if touch_comfy_claim(lease["note"]):
        lease["renewals"] = 1
    if interval > 0:
        lease["stop_event"] = threading.Event()
        lease["threaded"] = True
        threading.Thread(
            target=_comfy_claim_lease_loop,
            args=(lease, interval, extra),
            name="h3-gpu-claim-lease",
            daemon=True,
        ).start()
    _claim_lease = lease
    return {key: value for key, value in lease.items() if key != "stop_event"}


def stop_comfy_claim_lease() -> dict[str, Any]:
    """Stop renewing; the caller still decides when the GPU phase itself is over.

    Stopping before ``clear_comfy_claim`` is the required order: a live lease would re-arm the file
    the clear has just deleted, and Qwen would never come back.
    """

    global _claim_lease
    lease = _claim_lease
    if lease is None:
        return {
            "note": "",
            "interval_seconds": 0,
            "renewals": 0,
            "threaded": False,
            "stopped": True,
        }
    lease["stopped"] = True
    waiter = lease.get("stop_event")
    if waiter is not None:
        waiter.set()
    _claim_lease = None
    return {key: value for key, value in lease.items() if key != "stop_event"}


def active_run_path() -> Path:
    override = os.environ.get("H3_ACTIVE_RUN_PATH", "").strip()
    if override:
        return Path(override)
    return ROOT / "ai_libraries_common" / "director_studio_h3_status_tray" / "active_run.json"


def write_active_run(status: str, job_file: str = "") -> None:
    """Register this staged run with the tray so it can auto-resume a dead agent thread."""
    try:
        path = active_run_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": int(time.time()),
            "status": status,
            "thread_id": os.environ.get("CODEX_THREAD_ID", "").strip(),
            "job": job_file,
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError as exc:
        emit({"stage": "active-run", "warn": f"could not write active_run ({exc})"})


def clear_active_run() -> None:
    try:
        path = active_run_path()
        if path.is_file():
            path.unlink()
    except OSError as exc:
        emit({"stage": "active-run", "warn": f"could not clear active_run ({exc})"})


def sibling_manifest(job_file: str) -> Path:
    """Manifest that a finished run left behind after unlinking its Job JSON.

    ``smart_render_worker`` deletes the submitted Job on success and keeps only
    ``<same stem>.manifest.json``, so replaying a consumed Job path used to look
    like a GPU crash (2026-10-30 tray report on ``preview_923011007_...job.json``).
    """
    text = str(job_file)
    if text.endswith(".job.json"):
        return Path(text[: -len(".job.json")] + ".manifest.json")
    return Path(text)

# Readiness set covers the standard H3 path and the Character Swap Relay V2 graph.
H3_READY_NODES = ("MiniMaxH3SigmaShift", "LabsH3PrepareVideo", "H3RelayWindowPlan")


def http(url: str, timeout: float = 15.0, payload: dict | None = None) -> dict:
    return design_cleanup_service.request(url, timeout, payload)


def vram_state(server: str | None = None) -> dict | None:
    """Optional VRAM telemetry from the ComfyUI cache-status companion."""
    url = (server or comfy_url()).rstrip("/")
    try:
        data = http(url + "/director_studio/h3-relay-cache-status", timeout=15.0)
    except Exception:
        return None
    resources = data.get("resources") if isinstance(data, dict) else None
    if not isinstance(resources, dict):
        return None
    used_bytes = resources.get("vram_used_bytes")
    percent = resources.get("vram_percent")
    if used_bytes is None and percent is None:
        return None
    return {
        "used_bytes": int(used_bytes or 0),
        "percent": float(percent) if percent is not None else None,
        "gpu_name": str(resources.get("gpu_name") or ""),
    }


_ENGINE_KIND: str | None = None


def engine_kind() -> str:
    """Which host API dialect to speak: 'strata' (native host) or 'lmstudio'.

    Discriminator is cheap and definitive: LM Studio answers GET /api/v1/models,
    Strata 404s that route but answers GET /api/models (library state). Cached per
    process so a driver run never re-probes mid-flight.
    """
    global _ENGINE_KIND
    override = os.environ.get("H3_LM_ENGINE_KIND", "").strip().casefold()
    if override in ("strata", "lmstudio"):
        _ENGINE_KIND = override
        return _ENGINE_KIND
    if _ENGINE_KIND:
        return _ENGINE_KIND
    kind = "lmstudio"
    try:
        http(lm_origin() + "/api/v1/models", 4.0)
    except Exception:
        probe: Any = None
        try:
            probe = http(lm_origin() + "/api/models", 4.0)
        except Exception:
            probe = None
        if isinstance(probe, dict) and ("variants" in probe or "mode" in probe):
            kind = "strata"
    _ENGINE_KIND = kind
    return kind


def _lmstudio_loaded_instances() -> list[tuple[str, str]]:
    """LM Studio management API: (model_key, instance_id) for loaded Qwen instances."""
    catalog = http(lm_origin() + "/api/v1/models", 15.0)
    needle = qwen_key_filter()
    out: list[tuple[str, str]] = []
    for model in catalog.get("models") or []:
        key = str(model.get("key", ""))
        if not key or needle not in key.casefold():
            continue
        for inst in model.get("loaded_instances") or []:
            iid = (
                inst
                if isinstance(inst, str)
                else str(
                    inst.get("id")
                    or inst.get("instance_id")
                    or inst.get("identifier")
                    or ""
                )
            )
            if iid:
                out.append((key, iid))
    return out


def _strata_loaded_instances() -> list[tuple[str, str]]:
    """Strata native host: the OpenAI-shaped /v1/models entry is the live instance.

    Strata serves one model on automatic GPU placement, so the loaded list is that
    one instance. Its id for load/unload routes lives in meta.instanceId; the key
    filter matches id + aliases + human label, because a Strata model id ("iq3_s")
    does not contain the family name while its label ("Qwen3.8-Flash-Next IQ3_S")
    does.
    """
    payload = http(lm_origin() + "/v1/models", 15.0)
    needle = qwen_key_filter()
    out: list[tuple[str, str]] = []
    for entry in payload.get("data") or []:
        if not isinstance(entry, dict):
            continue
        meta = entry.get("meta") if isinstance(entry.get("meta"), dict) else {}
        model_id = str(entry.get("id") or "")
        label = str(meta.get("label") or "")
        aliases = [str(a) for a in (meta.get("aliases") or [])]
        haystack = " ".join([model_id, label, *aliases]).casefold()
        if needle and needle not in haystack:
            continue
        iid = str(meta.get("instanceId") or meta.get("instance_id") or "")
        if iid:
            out.append((model_id or label, iid))
    return out


def _qwen_loaded_instances() -> list[tuple[str, str]]:
    """Return (model_key, instance_id) for every loaded Qwen instance."""
    if engine_kind() == "strata":
        return _strata_loaded_instances()
    return _lmstudio_loaded_instances()


def _unload_instance(iid: str) -> None:
    """Unload one instance through the host's own management route."""
    if engine_kind() == "strata":
        http(f"{lm_origin()}/api/native/instances/{iid}/unload", 30.0, {})
        return
    http(lm_origin() + "/api/v1/models/unload", 30.0, {"instance_id": iid})


def _unload_busy_error(exc: Exception) -> bool:
    """True when the host refused to unload because a request is still in flight.

    The tray loads Qwen back and immediately warms it, so ``run`` often starts
    while that warm completion is still open.  Both hosts then answer
    ``HTTP 409 ... Finish or cancel this model's requests first.``  The request
    ends on its own a second or two later, so the correct response is a bounded
    retry rather than aborting the whole staged run (which is what happened to
    every ``preview_*.job.json`` crash on 2026-10-25).
    """

    detail = str(exc).casefold()
    return "409" in detail or "finish or cancel" in detail or "requests first" in detail


def force_cancel_enabled() -> bool:
    """Whether cancelling in-flight host requests is allowed (default on)."""
    return os.environ.get("H3_STAGE_QWEN_FORCE_CANCEL", "1").strip().casefold() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _serving_requests() -> list[dict]:
    """Strata only: live request ledger from GET /api/serving (empty when absent).

    LM Studio has no equivalent route, so the caller must treat an empty list as
    "no visibility", never as "nothing is running".
    """
    if engine_kind() != "strata":
        return []
    try:
        data = http(lm_origin() + "/api/serving", 8.0)
    except Exception:
        return []
    rows = data.get("requests") if isinstance(data, dict) else None
    return [row for row in rows or [] if isinstance(row, dict)]


def _request_state(row: dict) -> str:
    return str(row.get("state") or "").casefold()


def _request_is_live(row: dict) -> bool:
    """True when the host still holds this ledger row open on the instance.

    The host is the authority on what it can abort, so ``cancellable`` gates the
    sweep and only the states that are demonstrably finished are excluded.  A
    whitelist alone regressed twice: 2026-10-26 showed the tray proxy parked in
    "generating", a state nobody had listed.
    """

    if not row.get("cancellable"):
        return False
    return _request_state(row) not in TERMINAL_REQUEST_STATES


def _inflight_request_ids(rows: list[dict] | None = None) -> list[str]:
    """Request ids the host is willing to abort and has not aborted yet."""
    rows = _serving_requests() if rows is None else rows
    out: list[str] = []
    for row in rows:
        if not _request_is_live(row):
            continue
        rid = str(row.get("id") or "")
        if rid:
            out.append(rid)
    return out


def _cancel_inflight_requests() -> dict:
    """Abort every in-flight host request so the unload stops being refused.

    Why this is safe: the requests that block the unload are our own traffic -
    the DSH tray proxy re-warming Qwen after it reloaded the model (client
    ``DSH-Tray-Proxy/1.0``, endpoint ``/responses``). No H3 render is running at
    this point, and the tray simply retries. Tolerates 404/405 so a host build
    without the route degrades to the old polite-wait behaviour.
    """
    summary: dict[str, Any] = {"attempted": 0, "cancelled": [], "errors": [], "observed": []}
    if not force_cancel_enabled():
        summary["note"] = "skipped (H3_STAGE_QWEN_FORCE_CANCEL=0)"
        return summary
    if engine_kind() != "strata":
        summary["note"] = "no per-request cancel route on this host"
        return summary
    rows = _serving_requests()
    # Even when nothing matches, the raw ledger is the only way to learn why the
    # host still answers 409, so it is reported once per unload attempt.
    for row in rows[:8]:
        state = _request_state(row)
        summary["observed"].append(
            {
                "id": str(row.get("id") or ""),
                "state": state,
                "cancellable": bool(row.get("cancellable")),
                "client": str(row.get("client") or row.get("clientName") or ""),
                "recognised": state in INFLIGHT_REQUEST_STATES
                or state in TERMINAL_REQUEST_STATES,
            }
        )
    for rid in _inflight_request_ids(rows):
        summary["attempted"] += 1
        try:
            http(f"{lm_origin()}/api/serving/requests/{rid}/cancel", 8.0, {})
            summary["cancelled"].append(rid)
        except Exception as exc:
            detail = str(exc)
            folded = detail.casefold()
            if "404" in detail or "405" in detail or "no route" in folded:
                continue
            summary["errors"].append(f"{rid}: {detail}")
    return summary


def _load_instance(model: str) -> None:
    """Start the model.

    LM Studio loads lazily on the first chat completion, so a tiny probe request
    was enough. Strata does not auto-load on request (it answers "No models
    loaded"), so load is an explicit native job: POST /api/native/operations
    {kind:"load", args:{model:...}} which returns 202 and warms the engine in the
    background. The call is idempotent - if the instance is already ready with the
    same fingerprint it returns immediately.
    """
    if engine_kind() == "strata":
        http(
            lm_origin() + "/api/native/operations",
            LOAD_REQUEST_TIMEOUT,
            {"kind": "load", "args": {"model": model}},
        )
        return
    http(
        lm_origin() + "/v1/chat/completions",
        timeout=LOAD_REQUEST_TIMEOUT,
        payload={
            "model": model,
            "messages": [{"role": "user", "content": "reply with the single word ok"}],
            "max_tokens": 6,
        },
    )


def _poll_vram_drop(baseline_used_bytes: int, server: str | None = None) -> tuple[bool | None, dict | None]:
    """Wait for VRAM to drop after an unload.

    Returns (passed, final_state). ``passed`` is None when telemetry is
    unavailable so the caller can fall back to catalogue-only verification.
    Passes on a sufficient absolute drop OR a low residual percentage: ComfyUI
    may legitimately keep its own models resident next to the freed Qwen slot.
    """
    deadline = time.monotonic() + VRAM_CHECK_WAIT_SECONDS
    last: dict | None = None
    while True:
        state = vram_state(server)
        if state is None:
            return None, None
        last = state
        drop_gb = max(0.0, (baseline_used_bytes - state["used_bytes"]) / 1024**3)
        percent_ok = state["percent"] is not None and state["percent"] <= MAX_VRAM_PERCENT
        if drop_gb >= MIN_VRAM_DROP_GB or percent_ok:
            return True, last
        if time.monotonic() >= deadline:
            return False, last
        _sleep(5.0)


def unload_qwen(poll_seconds: float = UNLOAD_POLL_SECONDS, verify: bool = True) -> dict:
    """Unload every loaded Qwen3.8 instance and verify the GPU is actually clean."""
    write_comfy_claim("phase")
    result: dict[str, Any] = {
        "stage": "unload-qwen",
        "unloaded": [],
        "verified_clean": False,
        "remaining": [],
        "cancelled_requests": [],
        "note": "",
    }
    try:
        targets = _qwen_loaded_instances()
    except Exception as exc:
        # If LM Studio is down no Qwen instance can be resident in VRAM.
        result["verified_clean"] = True
        result["note"] = f"LM Studio unreachable ({exc}); no Qwen3.8 instance can be loaded"
        emit(result)
        return result

    baseline = vram_state() if verify else None
    retry: list[tuple[str, str]] = []
    for key, iid in targets:
        try:
            _unload_instance(iid)
            result["unloaded"].append(iid)
            emit({"stage": "unload-qwen", "unloaded_instance": iid, "model_key": key})
        except Exception as exc:
            if _unload_busy_error(exc):
                # The host is finishing a live request (usually the tray's warm
                # call).  Queue it: the verification loop below re-attempts every
                # round until either the request ends or the poll window closes.
                retry.append((key, iid))
                emit(
                    {
                        "stage": "unload-qwen",
                        "retry_queued": iid,
                        "model_key": key,
                        "reason": str(exc),
                    }
                )
                continue
            detail = str(exc).casefold()
            # A model can disappear between catalogue discovery and unload; in
            # that race it is already in the desired state.
            if (
                "model_not_found" not in detail
                and "is not loaded" not in detail
                and "no longer loaded" not in detail
            ):
                emit({"stage": "unload-qwen", "error": str(exc), "instance": iid})
    if not targets:
        result["note"] = "no loaded Qwen instances found"

    verified = False
    remaining = list(targets)
    rounds = max(1, int(poll_seconds // 3))
    for attempt in range(rounds):
        _sleep(3.0)
        if retry and (attempt == 0 or attempt % 6 == 0 or attempt == rounds - 1):
            # Politeness has a deadline: the tray proxy will hold its warm-up
            # completion open long past any reasonable render window, so abort
            # whatever is occupying the instance and re-attempt immediately.
            sweep = _cancel_inflight_requests()
            result["cancelled_requests"].extend(sweep["cancelled"])
            if sweep["attempted"]:
                emit(
                    {
                        "stage": "unload-qwen",
                        "cancel_requests": sweep["cancelled"],
                        "attempt": attempt + 1,
                        **({"errors": sweep["errors"]} if sweep["errors"] else {}),
                    }
                )
            elif sweep.get("observed") and (attempt in (0, 6) or attempt == rounds - 1):
                # The sweep found nothing cancellable yet the unload is still
                # being refused: surface the host's own ledger instead of
                # letting the run die on an unexplained HTTP 409.
                emit(
                    {
                        "stage": "unload-qwen",
                        "cancel_sweep_empty": True,
                        "observed_requests": sweep["observed"],
                        "attempt": attempt + 1,
                    }
                )
            if sweep["cancelled"]:
                _sleep(1.5)
        for key, iid in list(retry):
            try:
                _unload_instance(iid)
            except Exception as exc:
                if _unload_busy_error(exc):
                    continue
                emit({"stage": "unload-qwen", "error": str(exc), "instance": iid})
            retry.remove((key, iid))
            result["unloaded"].append(iid)
            emit(
                {
                    "stage": "unload-qwen",
                    "retry_unloaded": iid,
                    "model_key": key,
                    "attempt": attempt + 1,
                }
            )
        try:
            remaining = _qwen_loaded_instances()
        except Exception as exc:
            result["note"] = f"LM Studio unreachable during verification ({exc}); treating as clean"
            verified = True
            break
        if not remaining:
            verified = True
            break

    vram_ok: bool | None = None
    final_vram: dict | None = None
    if verify and baseline is not None and baseline["used_bytes"] > 0:
        vram_ok, final_vram = _poll_vram_drop(baseline["used_bytes"])
        result["vram_before_gb"] = round(baseline["used_bytes"] / 1024**3, 2)
        if final_vram is not None:
            result["vram_after_gb"] = round(final_vram["used_bytes"] / 1024**3, 2)

    result["verified_clean"] = verified and (vram_ok is not False)
    result["remaining"] = [iid for _, iid in remaining]
    if not result["cancelled_requests"]:
        result.pop("cancelled_requests", None)
    if not result["verified_clean"]:
        hint = "close the LM Studio chat tab holding this model"
        if vram_ok is False:
            hint += "; VRAM did not drop after unload (check other GPU consumers)"
        if retry:
            hint += (
                f"; {len(retry)} instance(s) refused unload because requests were "
                "still in flight for the whole poll window"
            )
        if result.get("cancelled_requests"):
            hint += (
                f"; {len(result['cancelled_requests'])} in-flight request(s) were "
                "cancelled but the instance stayed resident"
            )
        result["hint"] = hint
    emit(result)
    return result


def load_qwen(model: str | None = None, poll_seconds: float = LOAD_POLL_SECONDS) -> dict:
    """Explicitly load the Qwen model so the agent side never races an auto-load.

    LM Studio loads a model on first chat completion; we send one minimal probe
    request and then verify through the live catalogue (the same source of truth
    unload-qwen uses). VRAM telemetry is reported but not gating: loading only
    needs the instance resident, ComfyUI may keep its own models alongside.
    """
    clear_comfy_claim()
    result: dict[str, Any] = {
        "stage": "load-qwen",
        "model": model or qwen_load_model(),
        "loaded_instance": "",
        "verified_loaded": False,
        "note": "",
    }
    try:
        existing = _qwen_loaded_instances()
    except Exception as exc:
        result["note"] = f"LM Studio unreachable ({exc})"
        emit(result)
        return result

    baseline = vram_state()
    if existing:
        key, iid = existing[0]
        result["loaded_instance"] = iid
        result["verified_loaded"] = True
        result["note"] = f"already loaded ({key}) - no-op"
    else:
        try:
            _load_instance(result["model"])
        except Exception as exc:
            result["note"] = f"load request failed ({exc})"
            emit(result)
            return result

        verified = False
        rounds = max(1, int(poll_seconds // 5))
        for _ in range(rounds):
            _sleep(5.0)
            try:
                now = _qwen_loaded_instances()
            except Exception as exc:
                result["note"] = f"LM Studio unreachable during verification ({exc})"
                break
            if now:
                verified = True
                key, iid = now[0]
                result["loaded_instance"] = iid
                break

        result["verified_loaded"] = verified
        if not verified and not result["note"]:
            result["note"] = "load request accepted but no Qwen instance appeared in the catalogue"

    after = vram_state()
    if baseline is not None and after is not None:
        result["vram_before_gb"] = round(baseline["used_bytes"] / 1024**3, 2)
        result["vram_after_gb"] = round(after["used_bytes"] / 1024**3, 2)

    emit(result)
    return result


def wait_comfy(timeout_s: float = 1500.0, server: str | None = None, note: str = "phase") -> bool:
    write_comfy_claim(note)
    url = (server or comfy_url()).rstrip("/")
    deadline = time.monotonic() + timeout_s
    last_err = ""
    while time.monotonic() < deadline:
        try:
            info = http(url + "/object_info", 30.0)
            missing = [n for n in H3_READY_NODES if n not in info]
            if not missing:
                emit({"stage": "wait-comfy", "ready": True, "node_classes": len(info)})
                return True
            last_err = f"missing {missing}"
        except Exception as exc:
            last_err = str(exc)
        emit({"stage": "wait-comfy", "waiting": True, "detail": last_err})
        _sleep(20.0)
    emit({"stage": "wait-comfy", "ready": False, "detail": last_err})
    return False


def free_comfy(server: str | None = None) -> bool:
    clear_comfy_claim()
    url = (server or comfy_url()).rstrip("/")
    try:
        http(url + "/free", 30.0, {"unload_models": True, "free_memory": True})
        emit({"stage": "comfy-free", "ok": True})
        return True
    except Exception as exc:
        emit({"stage": "comfy-free", "error": str(exc)})
        return False


def read_manifest(job_file: str, job: dict | None = None) -> dict | None:
    if job is None:
        try:
            job = json.loads(Path(job_file).read_text(encoding="utf-8"))
        except OSError as exc:
            fallback = sibling_manifest(job_file)
            if not fallback.is_file():
                emit({"stage": "report", "error": f"job file unreadable ({exc}) and no manifest beside it"})
                return None
            emit({"stage": "report", "warn": f"job file unreadable ({exc}); reading the manifest the finished run left behind"})
            job = {}
            manifest_path = fallback
        else:
            manifest_path = Path(str(job.get("manifest_path") or ""))
    else:
        manifest_path = Path(str(job.get("manifest_path") or ""))
    if not manifest_path.is_file():
        emit({"stage": "report", "error": f"manifest missing: {manifest_path}"})
        return None
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = []
    for seg in m.get("segments") or []:
        row: dict[str, Any] = {
            "segment_id": seg.get("segment_id"),
            "shots": seg.get("shot_ids"),
            "range": [seg.get("start_seconds"), seg.get("end_seconds")],
            "status": seg.get("status"),
            "error": str(seg.get("error") or "")[:300],
            "output_path": seg.get("output_path", ""),
        }
        for p in seg.get("character_swap_passes") or []:
            ia = p.get("identity_audit") or {}
            row.setdefault("audits", []).append({
                "pass": p.get("pass_index"),
                "roles": p.get("source_role_ids"),
                "target": p.get("target_media_id"),
                "speaker": p.get("speaker"),
                "strict_cov": ia.get("strict_temporal_coverage"),
            })
        rows.append(row)
    emit({
        "stage": "report",
        "manifest": str(manifest_path),
        "master_output": m.get("master_output") or job.get("master_output"),
        "segments": rows,
    })
    return m


def wait_qwen_reloaded(timeout_s: float = 180.0) -> bool:
    """Wait for the tray's forward-enforcer to reload Qwen after /free.

    Without this, ``run`` returns while Qwen is still unloaded and the agent's
    next LLM call dies with 'No models loaded' (the thread then needs a manual
    nudge). The tray reloads ~20-30s after free + idle queue; poll a bounded
    number of rounds until the instance shows up in the live catalogue. The round
    cap (not a wall-clock deadline around a patched sleep) keeps the loop honest
    in tests: without it a mocked ``_sleep`` turned the wait into a 180s hot spin
    of millions of catalogue probes.
    """
    rounds = max(1, int(timeout_s // 5))
    for _ in range(rounds):
        try:
            if _qwen_loaded_instances():
                emit({"stage": "wait-qwen-reload", "ready": True})
                return True
        except Exception as exc:
            emit({"stage": "wait-qwen-reload", "warn": f"LM unreachable ({exc})"})
        _sleep(5.0)
    emit({"stage": "wait-qwen-reload", "ready": False, "note": "Qwen not reloaded yet; tray should bring it back within ~30s"})
    return False


def run_job(
    job_file: str,
    keep_qwen: bool = False,
    wait_timeout_s: float = 1500.0,
    log_dir: Path | None = None,
) -> int:
    """Staged pipeline: unload-qwen -> wait-comfy -> worker -> /free -> report.

    Registers the run in active_run.json so the tray can auto-resume this agent
    thread (``codex queue``) if we crash after unloading Qwen. On success tied to
    an agent thread the registry is left as 'completed' so the tray wakes us even
    when our turn died mid-run; standalone runs clear it. We wait for the tray to
    reload Qwen before returning, so the caller's next LLM call never hits
    'No models loaded'.
    """
    if not Path(job_file).is_file():
        # A successful worker run unlinks its Job JSON, so replaying that path (a re-typed
        # command, or the tray replaying its last active run) used to die with exit 2, which
        # this wrapper then recorded as 'crashed' -> the tray woke the agent with a phantom
        # GPU failure even though nothing was unloaded and no generation happened (observed
        # 2026-10-30 on preview_923011007_1793291935999553700.job.json). Refusing before the
        # registry is written means no auto-resume message and no GPU stage at all.
        manifest = sibling_manifest(job_file)
        emit(
            {
                "stage": "run-refused",
                "reason": "job-file-missing",
                "job": job_file,
                "manifest": str(manifest) if manifest.is_file() else "",
                "note": "a finished run unlinks its Job JSON and keeps only the manifest; "
                "build a fresh Job (working\\_r38_buildjob.py <seed> <MP> <windows>) instead "
                "of replaying a consumed path",
            }
        )
        return 4
    write_active_run("running", job_file)
    try:
        code = _run_job_inner(job_file, keep_qwen=keep_qwen, wait_timeout_s=wait_timeout_s, log_dir=log_dir)
        if not keep_qwen and not wait_qwen_reloaded():
            # Tray did not bring Qwen back in time (tray dead / grace period): same situation as a
            # crash - leave the crashed registry for auto-resume and spawn the detached safety net.
            emit({"stage": "run-note", "note": "Qwen not reloaded within timeout; leaving crashed registry for auto-resume"})
            write_active_run("crashed", job_file)
            _spawn_resume_watcher()
        elif code == 0 and not keep_qwen:
            # Success after the tray brought Qwen back. If this run belongs to an agent thread, leave a
            # 'completed' marker so the tray can wake us even when our turn died mid-run (the finally
            # below only unlinks status=running); standalone runs clear the registry directly.
            if os.environ.get("CODEX_THREAD_ID", "").strip():
                write_active_run("completed", job_file)
            else:
                clear_active_run()
        elif code != 0:
            # Worker failed with a non-zero exit (no exception raised): the agent turn still needs waking to
            # report/handle it - same situation as a crash. Leave the crashed registry for auto-resume and
            # spawn the detached safety net (2026-10-22 S7: KeyError 'workflow' died this exact gap).
            emit({"stage": "run-note", "note": f"worker exited {code}; leaving crashed registry for auto-resume"})
            write_active_run("crashed", job_file)
            _spawn_resume_watcher()
        return code
    except Exception as exc:
        emit({"stage": "run-crashed", "error": str(exc), "note": "tray (or the detached safety net) will auto-resume this agent thread once Qwen is reloaded"})
        write_active_run("crashed", job_file)
        _spawn_resume_watcher()
        return 3
    finally:
        # The phase claim must never outlive the run: on every exit path (exception, non-zero
        # worker, Qwen-reload timeout) drop it so the tray can reload Qwen immediately instead
        # of waiting for the TTL. Idempotent; the tray releases leftovers after the grace window.
        clear_comfy_claim()
        # Only clear the registry while this run still owns it (status=running); a crashed/timeout
        # handoff must survive so the tray or the detached watcher can resume the agent thread.
        try:
            reg_path = active_run_path()
            if reg_path.is_file():
                reg = json.loads(reg_path.read_text(encoding="utf-8"))
                if str(reg.get("status", "")) == "running" and reg.get("thread_id") == os.environ.get("CODEX_THREAD_ID", "").strip():
                    reg_path.unlink()
        except (OSError, ValueError):
            pass


def _run_job_inner(
    job_file: str,
    keep_qwen: bool = False,
    wait_timeout_s: float = 1500.0,
    log_dir: Path | None = None,
) -> int:
    """Staged pipeline body (see run_job for the crash/auto-resume wrapper)."""
    try:
        job = json.loads(Path(job_file).read_text(encoding="utf-8"))
    except OSError as exc:
        emit({"stage": "run-aborted", "reason": f"job-file-unreadable ({exc})"})
        return 2
    server = str(job.get("server") or "").rstrip("/") or comfy_url()
    emit({"stage": "run-start", "job": job_file, "server": server})

    if keep_qwen:
        emit({"stage": "unload-qwen", "skipped": True, "note": "--keep-qwen"})
    else:
        stage = unload_qwen()
        if not stage["verified_clean"]:
            emit({"stage": "run-aborted", "reason": "qwen-not-clean", **{k: v for k, v in stage.items() if k != "stage"}})
            return 2

    if not wait_comfy(wait_timeout_s, server, "keep-qwen" if keep_qwen else "phase"):
        emit({"stage": "run-aborted", "reason": "comfy-not-ready"})
        return 2

    log_root = Path(log_dir) if log_dir else ROOT / "logs" / "staged_model_driver"
    log_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    stem = Path(job_file).stem[:40]
    log_path = log_root / f"{stem}_{stamp}.log"

    before_vram = vram_state(server)
    env = dict(os.environ, PYTHONIOENCODING="utf8")
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [sys.executable, str(ROOT / "smart_render_worker.py"), job_file],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in proc.stdout:
            log.write(line)
            log.flush()
            try:
                payload = json.loads(line)
                if any(k in payload for k in ("progress", "segment_status", "error", "connection_state")) and not str(payload.get("progress", "")).startswith("Generating…"):
                    print(line.rstrip(), flush=True)
            except Exception:
                pass
        code = proc.wait()
    emit({"stage": "worker-exit", "code": code, "log": str(log_path)})

    # 每次测完 /free：release ComfyUI models/VRAM after every test run.
    released = free_comfy(server)
    if before_vram is not None:
        after_vram = vram_state(server)
        if after_vram is not None:
            emit({
                "stage": "vram-release",
                "before_gb": round(before_vram["used_bytes"] / 1024**3, 2),
                "after_gb": round(after_vram["used_bytes"] / 1024**3, 2),
                "freed_gb": round(max(0.0, (before_vram["used_bytes"] - after_vram["used_bytes"]) / 1024**3), 2),
            })
    if not released:
        emit({"stage": "run-note", "note": "worker finished but ComfyUI /free failed; run `free` manually"})

    read_manifest(job_file, job)
    return code


def _resolve_codex_cli() -> str | None:
    """Locate codex.exe (PATH first, then the newest versioned Codex desktop bin folder)."""
    import shutil
    found = shutil.which("codex") or shutil.which("codex.exe")
    if found:
        return found
    try:
        local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
        if local_appdata:
            bin_root = Path(local_appdata) / "OpenAI" / "Codex" / "bin"
            if bin_root.is_dir():
                candidates = [d for d in bin_root.iterdir() if (d / "codex.exe").is_file()]
                if candidates:
                    newest = max(candidates, key=lambda d: d.stat().st_mtime)
                    return str(newest / "codex.exe")
    except OSError:
        pass
    return None


def _spawn_resume_watcher(timeout_s: float = 600.0) -> None:
    """Detached last-resort safety net: if the tray is dead, it waits for Qwen and queues 'continue' itself."""
    try:
        kwargs: dict[str, Any] = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | 0x00000010  # DETACHED_PROCESS
        log_root = ROOT / "logs" / "staged_model_driver"
        log_root.mkdir(parents=True, exist_ok=True)
        log_file = (log_root / f"resume_wait_{time.strftime('%Y%m%d_%H%M%S')}.log").open("w", encoding="utf-8")
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "resume-wait", "--timeout", str(timeout_s)],
            cwd=str(ROOT), stdout=log_file, stderr=subprocess.STDOUT, **kwargs,
        )
    except OSError as exc:
        emit({"stage": "resume-watcher", "warn": f"could not spawn ({exc})"})


def resume_wait(timeout_s: float = 600.0) -> int:
    """Last-resort safety net (spawned detached by run on crash/timeout).

    Waits for Qwen to be loaded (by the tray or anyone), then queues a continue
    message into the registered Codex thread - so a dead tray cannot strand the
    agent. The registry status guard prevents double-firing with the tray.
    """
    reg_path = active_run_path()
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        emit({"stage": "resume-wait", "error": f"registry unreadable ({exc})"})
        return 2
    if str(reg.get("status", "")) != "crashed":
        emit({"stage": "resume-wait", "note": f"registry status={reg.get('status')!r}, nothing to do"})
        return 0
    thread_id = str(reg.get("thread_id") or "").strip()
    if not thread_id:
        emit({"stage": "resume-wait", "note": "no thread_id registered; nothing to wake"})
        return 0
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            if _qwen_loaded_instances():
                break
        except Exception as exc:
            emit({"stage": "resume-wait", "warn": f"LM unreachable ({exc})"})
        if time.monotonic() >= deadline:
            emit({"stage": "resume-wait", "note": "Qwen not loaded within timeout; giving up (tray should handle)"})
            return 2
        _sleep(5.0)
    # Qwen is back - queue the resume, but only if we still own the crashed state (the tray may have beaten us).
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        if str(reg.get("status", "")) != "crashed":
            emit({"stage": "resume-wait", "note": f"already handled (status={reg.get('status')!r})"})
            return 0
    except (OSError, ValueError):
        emit({"stage": "resume-wait", "note": "registry gone; run restarted or cleared"})
        return 0
    codex_exe = _resolve_codex_cli()
    if not codex_exe:
        emit({"stage": "resume-wait", "error": "codex.exe not found; send 'continue' manually"})
        return 2
    try:
        proc = subprocess.run(
            [
                codex_exe, "queue", "--thread", thread_id, "--message",
                f"Tray auto-resume (driver safety net): staged driver crashed on job {reg.get('job')}. Qwen is loaded. Continue from where you stopped.",
            ],
            capture_output=True, text=True, timeout=60,
        )
        ok = proc.returncode == 0
    except Exception as exc:
        emit({"stage": "resume-wait", "error": f"codex queue failed ({exc})"})
        return 2
    if ok:
        reg["status"] = "resumed"
        reg["ts"] = int(time.time())
        try:
            reg_path.write_text(json.dumps(reg), encoding="utf-8")
        except OSError as exc:
            emit({"stage": "resume-wait", "warn": f"could not mark resumed ({exc})"})
    emit({"stage": "resume-wait", "queued": ok, "thread_id": thread_id})
    return 0 if ok else 2


def status() -> int:
    payload: dict[str, Any] = {"stage": "status", "comfy_url": comfy_url(), "lm_origin": lm_origin()}
    try:
        payload["qwen_loaded"] = [iid for _, iid in _qwen_loaded_instances()]
    except Exception as exc:
        payload["lm_unreachable"] = str(exc)
    try:
        queue = http(comfy_url() + "/queue", timeout=10.0).get("queue") or []
        payload["comfy_queue"] = "busy" if (isinstance(queue, list) and queue and queue[0]) else "free"
    except Exception as exc:
        payload["comfy_unreachable"] = str(exc)
    age = comfy_claim_age_seconds()
    if age is not None:
        payload["comfy_claim"] = "active" if age < COMFY_CLAIM_TTL_SECONDS else "stale"
        payload["comfy_claim_age_s"] = round(age)
    else:
        payload["comfy_claim"] = "none"
    state = vram_state()
    if state is not None:
        payload["vram_percent"] = state["percent"]
        payload["vram_used_gb"] = round(state["used_bytes"] / 1024**3, 2)
        payload["gpu_name"] = state["gpu_name"]
    emit(payload)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")

    p_unload = sub.add_parser("unload-qwen")
    p_unload.add_argument("--no-verify", action="store_true")
    p_unload.add_argument("--poll-seconds", type=float, default=UNLOAD_POLL_SECONDS)

    p_load = sub.add_parser("load-qwen")
    p_load.add_argument("--model", default=None)
    p_load.add_argument("--poll-seconds", type=float, default=LOAD_POLL_SECONDS)

    p_wait = sub.add_parser("wait-comfy")
    p_wait.add_argument("--timeout", type=float, default=1500.0)

    p_free = sub.add_parser("free")
    p_free.add_argument("--server", default=None)

    p_run = sub.add_parser("run")
    p_run.add_argument("job")
    p_run.add_argument("--keep-qwen", action="store_true")
    p_run.add_argument("--wait-timeout", type=float, default=1500.0)
    p_run.add_argument("--log-dir", default=None)

    p_resume = sub.add_parser("resume-wait")
    p_resume.add_argument("--timeout", type=float, default=600.0)

    p_report = sub.add_parser("report")
    p_report.add_argument("job")

    args = parser.parse_args(argv)
    if args.cmd == "status":
        return status()
    if args.cmd == "unload-qwen":
        result = unload_qwen(poll_seconds=args.poll_seconds, verify=not args.no_verify)
        return 0 if result["verified_clean"] else 2
    if args.cmd == "load-qwen":
        result = load_qwen(model=args.model, poll_seconds=args.poll_seconds)
        return 0 if result["verified_loaded"] else 2
    if args.cmd == "wait-comfy":
        return 0 if wait_comfy(args.timeout) else 2
    if args.cmd == "free":
        before = vram_state(args.server)
        ok = free_comfy(args.server)
        after = vram_state(args.server)
        if ok and before is not None and after is not None:
            emit({
                "stage": "vram-release",
                "before_gb": round(before["used_bytes"] / 1024**3, 2),
                "after_gb": round(after["used_bytes"] / 1024**3, 2),
                "freed_gb": round(max(0.0, (before["used_bytes"] - after["used_bytes"]) / 1024**3), 2),
            })
        return 0 if ok else 2
    if args.cmd == "run":
        return run_job(args.job, keep_qwen=args.keep_qwen, wait_timeout_s=args.wait_timeout, log_dir=Path(args.log_dir) if args.log_dir else None)
    if args.cmd == "resume-wait":
        return resume_wait(timeout_s=args.timeout)
    if args.cmd == "report":
        read_manifest(args.job)
        return 0


if __name__ == "__main__":
    sys.exit(main())

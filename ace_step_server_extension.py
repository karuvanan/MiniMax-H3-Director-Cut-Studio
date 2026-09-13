"""Studio-owned ACE-Step API extensions.

The upstream ACE-Step API can initialize and switch models, but it does not
currently expose a complete inference-model unload endpoint.  Studio launches
ACE-Step through :mod:`ace_step_server`, which registers the endpoint below
without modifying the cloned upstream repository.
"""

from __future__ import annotations

import asyncio
import gc
from typing import Any, Callable


_MODEL_ATTRIBUTES = (
    "model",
    "vae",
    "text_encoder",
    "text_tokenizer",
    "silence_latent",
    "reward_model",
    "_base_decoder",
    "mlx_decoder",
    "mlx_vae",
)


def _job_stats(app_state: Any) -> dict[str, int]:
    store = getattr(app_state, "job_store", None)
    if store is None or not hasattr(store, "get_stats"):
        return {}
    return dict(store.get_stats() or {})


def _clear_device_caches() -> bool:
    """Collect Python objects and release allocator caches when available."""

    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        elif hasattr(torch, "xpu") and torch.xpu.is_available():
            torch.xpu.empty_cache()
            torch.xpu.synchronize()
        elif (
            hasattr(torch, "backends")
            and hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
        ):
            if hasattr(torch.mps, "empty_cache"):
                torch.mps.empty_cache()
            if hasattr(torch.mps, "synchronize"):
                torch.mps.synchronize()
        return True
    except Exception:
        # Dropping the final model references still releases the allocations;
        # explicit allocator-cache cleanup is best-effort across backends.
        return False


def release_ace_step_models(app_state: Any) -> dict[str, Any]:
    """Unload every ACE-Step inference handler and its language model.

    Configuration paths and ``last_init_params`` are deliberately retained so
    the existing lazy initialization path can restore the selected model on the
    next analysis or generation request.
    """

    stats = _job_stats(app_state)
    queued = int(stats.get("queued", 0) or 0)
    running = int(stats.get("running", 0) or 0)
    if queued or running:
        raise RuntimeError(
            f"ACE-Step is busy ({running} running, {queued} queued); wait for all tasks to finish"
        )

    released_slots: list[int] = []
    for slot in (1, 2, 3):
        handler = getattr(app_state, "handler" if slot == 1 else f"handler{slot}", None)
        if handler is None:
            continue
        was_loaded = bool(
            getattr(app_state, "_initialized" if slot == 1 else f"_initialized{slot}", False)
            or any(getattr(handler, name, None) is not None for name in _MODEL_ATTRIBUTES)
        )
        for name in _MODEL_ATTRIBUTES:
            if hasattr(handler, name):
                setattr(handler, name, None)
        for name, value in (
            ("compiled", False),
            ("mlx_dit_compiled", False),
            ("lora_loaded", False),
            ("use_lora", False),
            ("_lora_active_adapter", None),
        ):
            if hasattr(handler, name):
                setattr(handler, name, value)
        active_loras = getattr(handler, "_active_loras", None)
        if hasattr(active_loras, "clear"):
            active_loras.clear()
        initialized_attr = "_initialized" if slot == 1 else f"_initialized{slot}"
        error_attr = "_init_error" if slot == 1 else f"_init_error{slot}"
        setattr(app_state, initialized_attr, False)
        setattr(app_state, error_attr, None)
        if was_loaded:
            released_slots.append(slot)

    llm = getattr(app_state, "llm_handler", None)
    llm_was_loaded = bool(
        getattr(app_state, "_llm_initialized", False)
        or (llm is not None and getattr(llm, "llm", None) is not None)
    )
    if llm is not None and hasattr(llm, "unload"):
        llm.unload()
    app_state._llm_initialized = False
    app_state._llm_init_error = None
    app_state._llm_lazy_load_disabled = False

    cache_cleared = _clear_device_caches()
    return {
        "message": "ACE-Step inference models unloaded",
        "released_slots": released_slots,
        "llm_unloaded": llm_was_loaded,
        "device_cache_cleared": cache_cleared,
        "lazy_reload": True,
    }


def register_unload_route(
    app: Any,
    *,
    verify_api_key: Callable[..., Any],
    wrap_response: Callable[..., dict[str, Any]],
) -> None:
    """Register ``POST /v1/unload`` on an upstream ACE-Step FastAPI app."""

    from fastapi import Depends, HTTPException

    @app.post("/v1/unload")
    async def unload_models(_: None = Depends(verify_api_key)):
        async with app.state._init_lock:
            try:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    app.state.executor,
                    lambda: release_ace_step_models(app.state),
                )
                return wrap_response(result)
            except RuntimeError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            except Exception as exc:
                return wrap_response(None, code=500, error=f"Model unload failed: {exc}")

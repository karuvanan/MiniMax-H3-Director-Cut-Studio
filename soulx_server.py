"""Launch SoulX-Singer SVC with Studio-managed lazy reload and unload API."""

from __future__ import annotations

import argparse
from functools import wraps
import gc
import inspect
import os
from pathlib import Path
import sys
import threading
import traceback
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
SOULX_HOME = PROJECT_ROOT / "models" / "SoulX-Singer-main"
if str(SOULX_HOME) not in sys.path:
    sys.path.insert(0, str(SOULX_HOME))


def _clear_device_cache() -> bool:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        return True
    except Exception:
        return False


def _cuda_memory_mb() -> dict[str, float]:
    try:
        import torch

        if not torch.cuda.is_available():
            return {"allocated": 0.0, "reserved": 0.0}
        divisor = 1024.0 * 1024.0
        return {
            "allocated": round(float(torch.cuda.memory_allocated()) / divisor, 1),
            "reserved": round(float(torch.cuda.memory_reserved()) / divisor, 1),
        }
    except Exception:
        return {"allocated": 0.0, "reserved": 0.0}


def release_soulx_models(upstream: Any) -> dict[str, Any]:
    """Drop the global SVC/preprocess state so the next request reloads it."""

    memory_before = _cuda_memory_mb()
    state = getattr(upstream, "APP_STATE", None)
    was_loaded = state is not None
    released_attributes: list[str] = []
    if state is not None:
        # The official AppState owns both the 698M SVC model and all
        # preprocessing models. Clear every instance attribute so an upstream
        # release cannot add another GPU holder that this boundary overlooks.
        try:
            state_attributes = tuple(vars(state))
        except TypeError:
            state_attributes = ("svc_model", "preprocess_pipeline")
        for name in state_attributes:
            if hasattr(state, name):
                try:
                    setattr(state, name, None)
                    released_attributes.append(str(name))
                except Exception:
                    pass
    upstream.APP_STATE = None
    state = None
    cache_cleared = _clear_device_cache()
    memory_after = _cuda_memory_mb()
    result = {
        "message": "SoulX-Singer models unloaded",
        "model_was_loaded": was_loaded,
        "released_attributes": released_attributes,
        "device_cache_cleared": cache_cleared,
        "cuda_allocated_before_mb": memory_before["allocated"],
        "cuda_reserved_before_mb": memory_before["reserved"],
        "cuda_allocated_after_mb": memory_after["allocated"],
        "cuda_reserved_after_mb": memory_after["reserved"],
        "lazy_reload": True,
    }
    print(
        "[SoulX] models unloaded · "
        f"allocated {memory_before['allocated']:.1f} -> {memory_after['allocated']:.1f} MB · "
        f"reserved {memory_before['reserved']:.1f} -> {memory_after['reserved']:.1f} MB",
        flush=True,
    )
    return result


def _wrap_start_svc(callback, ensure_state, execution_lock=None):
    """Preserve the upstream API signature while adding lazy model loading."""

    @wraps(callback)
    def lazy_start_svc(*args, **kwargs):
        if execution_lock is None:
            ensure_state()
            return callback(*args, **kwargs)
        with execution_lock:
            ensure_state()
            return callback(*args, **kwargs)

    return lazy_start_svc


def _call_upstream_start_svc(callback, values: dict[str, Any]):
    """Call official or extended SoulX callbacks without trusting Gradio labels."""

    signature = inspect.signature(callback)
    parameters = list(signature.parameters.values())
    if not any(item.kind == inspect.Parameter.VAR_POSITIONAL for item in parameters):
        supported = {
            item.name: values[item.name]
            for item in parameters
            if item.name in values
            and item.kind
            in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        }
        required = [
            item.name
            for item in parameters
            if item.default is inspect.Parameter.empty
            and item.kind
            in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        ]
        if all(name in supported for name in required):
            return callback(**supported)

    core_order = (
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
    extended_order = (
        *core_order[:6],
        "device_choice",
        "use_fp16",
        *core_order[6:],
    )
    positional_count = sum(
        item.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for item in parameters
    )
    order = extended_order if positional_count >= 12 else core_order
    return callback(*(values[name] for name in order))


def build_page(*, use_fp16: bool = True):
    import gradio as gr
    import webui_svc as upstream

    load_lock = threading.RLock()
    original_start_svc = upstream._start_svc

    def ensure_state(device_choice: str = "auto", request_fp16: bool = use_fp16) -> None:
        with load_lock:
            if getattr(upstream, "APP_STATE", None) is None:
                state_parameters = inspect.signature(upstream.AppState).parameters
                state_kwargs: dict[str, Any] = {}
                if "use_fp16" in state_parameters:
                    state_kwargs["use_fp16"] = bool(request_fp16)
                if "device_choice" in state_parameters:
                    state_kwargs["device_choice"] = str(device_choice or "auto")
                upstream.APP_STATE = upstream.AppState(**state_kwargs)

    upstream._start_svc = _wrap_start_svc(original_start_svc, ensure_state, load_lock)
    page = upstream.render_interface()
    with page:
        stable_prompt_audio = gr.Audio(type="filepath", visible=False)
        stable_target_audio = gr.Audio(type="filepath", visible=False)
        stable_prompt_vocal_sep = gr.Checkbox(value=False, visible=False)
        stable_target_vocal_sep = gr.Checkbox(value=True, visible=False)
        stable_auto_shift = gr.Checkbox(value=True, visible=False)
        stable_auto_mix_acc = gr.Checkbox(value=True, visible=False)
        stable_device_choice = gr.Dropdown(
            choices=["auto", "cuda", "directml", "cpu"], value="cuda", visible=False
        )
        stable_use_fp16 = gr.Checkbox(value=True, visible=False)
        stable_pitch_shift = gr.Number(value=0, precision=0, visible=False)
        stable_n_step = gr.Number(value=32, precision=0, visible=False)
        stable_cfg = gr.Number(value=1.0, visible=False)
        stable_seed = gr.Number(value=42, precision=0, visible=False)
        stable_output_audio = gr.Audio(type="filepath", visible=False)
        stable_trigger = gr.Button(visible=False)

        def studio_start_svc(
            prompt_audio,
            target_audio,
            prompt_vocal_sep,
            target_vocal_sep,
            auto_shift,
            auto_mix_acc,
            device_choice,
            use_fp16,
            pitch_shift,
            n_step,
            cfg,
            seed,
        ):
            values = {
                "prompt_audio": prompt_audio,
                "target_audio": target_audio,
                "prompt_vocal_sep": bool(prompt_vocal_sep),
                "target_vocal_sep": bool(target_vocal_sep),
                "auto_shift": bool(auto_shift),
                "auto_mix_acc": bool(auto_mix_acc),
                "device_choice": str(device_choice or "auto"),
                "device": str(device_choice or "auto"),
                "use_fp16": bool(use_fp16),
                "pitch_shift": int(pitch_shift),
                "n_step": int(n_step),
                "cfg": float(cfg),
                "seed": int(seed),
            }
            try:
                with load_lock:
                    ensure_state(values["device_choice"], values["use_fp16"])
                    result = _call_upstream_start_svc(original_start_svc, values)
            except Exception as exc:
                traceback.print_exc()
                raise gr.Error(f"SoulX backend {type(exc).__name__}: {exc}") from exc
            if not result:
                raise gr.Error(
                    "SoulX backend returned no audio. Review logs/soulx_api.stderr.log "
                    "for the preprocessing or inference exception."
                )
            return result

        stable_trigger.click(
            fn=studio_start_svc,
            inputs=[
                stable_prompt_audio,
                stable_target_audio,
                stable_prompt_vocal_sep,
                stable_target_vocal_sep,
                stable_auto_shift,
                stable_auto_mix_acc,
                stable_device_choice,
                stable_use_fp16,
                stable_pitch_shift,
                stable_n_step,
                stable_cfg,
                stable_seed,
            ],
            outputs=[stable_output_audio],
            api_name="_studio_start_svc",
            queue=True,
        )
        def unload_models():
            with load_lock:
                return release_soulx_models(upstream)

        unload_result = gr.JSON(visible=False)
        unload_trigger = gr.Button(visible=False)
        unload_trigger.click(
            fn=unload_models,
            inputs=[],
            outputs=[unload_result],
            api_name="_unload_svc",
            queue=True,
        )
    # Upstream constructs APP_STATE eagerly during import. Drop that initial
    # state after binding the callbacks so an idle API consumes no model VRAM;
    # the first web or Studio request will reload it under the same lock.
    with load_lock:
        release_soulx_models(upstream)
    return page


def main() -> None:
    parser = argparse.ArgumentParser(description="Studio SoulX-Singer SVC server")
    parser.add_argument("--host", default=os.getenv("SOULX_API_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("SOULX_API_PORT", "7861")))
    parser.add_argument("--fp16", action="store_true")
    args = parser.parse_args()
    page = build_page(use_fp16=bool(args.fp16))
    page.queue()
    page.launch(
        server_name=str(args.host),
        server_port=int(args.port),
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()

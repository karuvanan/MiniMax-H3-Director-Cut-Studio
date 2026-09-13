"""Launch SoulX-Singer SVC with Studio-managed lazy reload and unload API."""

from __future__ import annotations

import argparse
import gc
import os
from pathlib import Path
import sys
import threading
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
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        return True
    except Exception:
        return False


def release_soulx_models(upstream: Any) -> dict[str, Any]:
    """Drop the global SVC/preprocess state so the next request reloads it."""

    state = getattr(upstream, "APP_STATE", None)
    was_loaded = state is not None
    if state is not None:
        for name in ("svc_model", "preprocess_pipeline"):
            if hasattr(state, name):
                setattr(state, name, None)
    upstream.APP_STATE = None
    return {
        "message": "SoulX-Singer models unloaded",
        "model_was_loaded": was_loaded,
        "device_cache_cleared": _clear_device_cache(),
        "lazy_reload": True,
    }


def build_page(*, use_fp16: bool = True):
    import gradio as gr
    import webui_svc as upstream

    load_lock = threading.RLock()
    original_start_svc = upstream._start_svc

    def ensure_state() -> None:
        with load_lock:
            if getattr(upstream, "APP_STATE", None) is None:
                upstream.APP_STATE = upstream.AppState(use_fp16=use_fp16)

    def lazy_start_svc(
        prompt_audio,
        target_audio,
        prompt_vocal_sep,
        target_vocal_sep,
        auto_shift,
        auto_mix_acc,
        pitch_shift,
        n_step,
        cfg,
        seed,
    ):
        ensure_state()
        return original_start_svc(
            prompt_audio,
            target_audio,
            prompt_vocal_sep,
            target_vocal_sep,
            auto_shift,
            auto_mix_acc,
            pitch_shift,
            n_step,
            cfg,
            seed,
        )

    upstream._start_svc = lazy_start_svc
    page = upstream.render_interface()
    with page:
        unload_result = gr.JSON(visible=False)
        unload_trigger = gr.Button(visible=False)
        unload_trigger.click(
            fn=lambda: release_soulx_models(upstream),
            inputs=[],
            outputs=[unload_result],
            api_name="_unload_svc",
            queue=True,
        )
    return page


def main() -> None:
    parser = argparse.ArgumentParser(description="Studio SoulX-Singer SVC server")
    parser.add_argument("--host", default=os.getenv("SOULX_API_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("SOULX_API_PORT", "7861")))
    parser.add_argument("--fp16", action="store_true")
    args = parser.parse_args()
    page = build_page(use_fp16=bool(args.fp16))
    page.queue()
    page.launch(server_name=str(args.host), server_port=int(args.port), share=False)


if __name__ == "__main__":
    main()


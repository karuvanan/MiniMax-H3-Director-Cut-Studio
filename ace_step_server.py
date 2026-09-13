"""Launch the ACE-Step API with Studio-managed compatibility extensions."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
ACE_STEP_HOME = PROJECT_ROOT / "models" / "ACE-Step-1.5"
if str(ACE_STEP_HOME) not in sys.path:
    sys.path.insert(0, str(ACE_STEP_HOME))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Studio ACE-Step 1.5 API server")
    parser.add_argument("--host", default=os.getenv("ACESTEP_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("ACESTEP_API_PORT", "8001")))
    parser.add_argument("--api-key", default=os.getenv("ACESTEP_API_KEY", ""))
    parser.add_argument(
        "--download-source",
        choices=("huggingface", "modelscope", "auto"),
        default=os.getenv("ACESTEP_DOWNLOAD_SOURCE", "auto"),
    )
    parser.add_argument("--init-llm", action="store_true")
    parser.add_argument("--lm-model-path", default=os.getenv("ACESTEP_LM_MODEL_PATH", ""))
    parser.add_argument("--no-init", action="store_true")
    return parser.parse_args()


def _apply_environment(args: argparse.Namespace) -> None:
    if args.api_key:
        os.environ["ACESTEP_API_KEY"] = str(args.api_key)
    if args.download_source and args.download_source != "auto":
        os.environ["ACESTEP_DOWNLOAD_SOURCE"] = str(args.download_source)
        print(f"Using preferred download source: {args.download_source}")
    if args.init_llm:
        os.environ["ACESTEP_INIT_LLM"] = "true"
        print("[API Server] LLM initialization enabled via --init-llm")
    if args.lm_model_path:
        os.environ["ACESTEP_LM_MODEL_PATH"] = str(args.lm_model_path)
        print(f"[API Server] Using LM model: {args.lm_model_path}")
    if args.no_init:
        os.environ["ACESTEP_NO_INIT"] = "true"
        print("[API Server] --no-init: models will lazy-load on first request")


def build_app():
    from acestep.api.http.auth import verify_api_key
    from acestep.api_server import _wrap_response, create_app
    from ace_step_server_extension import register_unload_route

    app = create_app()
    register_unload_route(
        app,
        verify_api_key=verify_api_key,
        wrap_response=_wrap_response,
    )
    return app


def main() -> None:
    args = _parse_args()
    _apply_environment(args)
    import uvicorn

    uvicorn.run(build_app(), host=str(args.host), port=int(args.port), workers=1)


if __name__ == "__main__":
    main()

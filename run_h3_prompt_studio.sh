#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

VENV_PYTHON=".venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Missing Studio venv: $VENV_PYTHON" >&2
  echo "Create it with: uv venv .venv && uv pip install --python .venv/bin/python -r requirements-macos.txt" >&2
  exit 1
fi

# Retrieve credentials from the system password store, not .env.
if [[ -z "${FAL_KEY:-}" ]]; then
  export FAL_KEY="$(pass-get FAL_API_KEY 2>/dev/null || true)"
  if [[ -z "$FAL_KEY" ]]; then
    echo "Warning: FAL_KEY not set and pass-get FAL_API_KEY returned empty." >&2
    echo "fal FL2VA/I2VA/L2VA modes will not work without it." >&2
  fi
fi

exec "$VENV_PYTHON" director_cut_studio.py "$@"

"""Standalone worker that calls the toyxyz MinimaxH3Prompter enhance endpoint.

Reads a job JSON from argv[1], uploads reference media to the local ComfyUI,
calls the enhance endpoint, and emits the result as a JSON line on stdout.

Job JSON fields:
    server: str           - local ComfyUI URL (e.g. http://127.0.0.1:8188)
    project_data: str     - toyxyz project_data JSON string
    model: str            - enhance model ID
    image_model: str      - image analysis model ID
    reference_images: list[dict] - media to upload before enhancing
        local_path: str   - local file path
        binding: str      - first_frame, last_frame, frame, subject
        media_type: str   - "image" or "video"
        strength: str     - "weak", "normal", "strong" (for subject)

Emits JSON lines:
    {"progress": "Uploading first_frame.png..."}
    {"progress": "Analyzing references and generating prompt..."}
    {"completed": true, "enhanced_prompt": "...", "reference_analyses": [...]}
    or
    {"error": "message"}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add the Studio directory to path so we can import the client
sys.path.insert(0, str(Path(__file__).parent))

from toyxyz_prompt_client import (
    compile_project,
    enhance_project,
    upload_references,
    DEFAULT_ENHANCE_MODEL,
    DEFAULT_IMAGE_MODEL,
)


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: toyxyz_prompt_worker.py <job.json>"}))
        return 1

    job_path = Path(sys.argv[1])
    job = json.loads(job_path.read_text(encoding="utf-8"))
    server = job["server"].rstrip("/")
    project_data = job["project_data"]
    model = job.get("model", DEFAULT_ENHANCE_MODEL)
    image_model = job.get("image_model", DEFAULT_IMAGE_MODEL)
    reference_assets = job.get("reference_images", [])

    # Upload reference media
    if reference_assets:
        print(json.dumps({"progress": f"Uploading {len(reference_assets)} reference item(s)..."}, ensure_ascii=False), flush=True)
        try:
            references = upload_references(server, reference_assets)
            # Rebuild project_data with uploaded reference info
            project = json.loads(project_data)
            project["references"] = references
            project_data = json.dumps(project, ensure_ascii=False)
        except Exception as exc:
            print(json.dumps({"error": f"Reference upload failed: {exc}"}, ensure_ascii=False), flush=True)
            return 1

    # Compile to check for validation errors
    print(json.dumps({"progress": "Validating project..."}, ensure_ascii=False), flush=True)
    try:
        compile_result = compile_project(server, project_data)
        if compile_result.get("errors"):
            print(json.dumps({"error": "Validation: " + "; ".join(compile_result["errors"])}, ensure_ascii=False), flush=True)
            return 1
    except Exception as exc:
        print(json.dumps({"error": f"Compile failed: {exc}"}, ensure_ascii=False), flush=True)
        return 1

    # Enhance (runs LLM, blocking)
    print(json.dumps({"progress": "Analyzing references and generating prompt..."}, ensure_ascii=False), flush=True)
    try:
        result = enhance_project(
            server, project_data,
            model=model,
            image_model=image_model,
            timeout=600,
        )
    except Exception as exc:
        print(json.dumps({"error": f"Enhance failed: {exc}"}, ensure_ascii=False), flush=True)
        return 1

    if result.get("status") != "success":
        print(json.dumps({"error": result.get("message", "unknown error")}, ensure_ascii=False), flush=True)
        return 1

    print(json.dumps({
        "completed": True,
        "enhanced_prompt": result.get("enhanced_prompt", ""),
        "reference_analyses": result.get("reference_analyses", []),
        "raw_model_prompt": result.get("raw_model_prompt", ""),
    }, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), flush=True)
        raise SystemExit(1)

"""Client for the toyxyz MinimaxH3Prompter ComfyUI node.

Talks to the local Mac ComfyUI instance where the toyxyz node is installed.
The node runs llama.cpp (Qwen3.8-27B) to generate H3 IR prompts from a
structured project_data JSON, optionally analyzing reference images first.
"""

from __future__ import annotations

import json
import urllib.request
import uuid
from pathlib import Path

from comfy_submit_worker import upload_file

# Mode mapping: Studio H3 mode -> toyxyz mode string
MODE_MAP = {
    "Ref2VA": "REF2VA",
    "FL2VA": "FL2VA",
    "I2VA": "I2VA",
    "L2VA": "L2VA",
    "T2VA": "T2VA",
}

# Default model IDs (matching the toyxyz node's constants)
DEFAULT_ENHANCE_MODEL = "hf:JonathanColetti/Qwen3.8-27B-Uncensored-GGUF/Qwen3.8-27B-Uncensored-Q4_K_M.gguf"
DEFAULT_IMAGE_MODEL = "hf:JonathanColetti/Qwen3.8-27B-Uncensored-GGUF/Q4_K_M+vision-f16"

# Binding -> toyxyz picture role
BINDING_TO_ROLE = {
    "first_frame": "first_frame",
    "last_frame": "last_frame",
    "frame": "frame",
    "subject": "subject_identity",
    "subject_identity": "subject_identity",
}


def _post_json(url: str, payload: dict, timeout: int = 600) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_project_data(
    *,
    mode: str,
    duration: float,
    user_request: str,
    shots: list[dict],
    references: list[dict] | None = None,
    constraints: str = "",
    verbatim_content: str = "",
    enhance_level: str = "normal",
    enhance_model: str = DEFAULT_ENHANCE_MODEL,
    image_model: str = DEFAULT_IMAGE_MODEL,
) -> str:
    """Build a toyxyz project_data JSON string from Studio state.

    shots: list of dicts with keys:
        - visual_action: str
        - duration: float
        - presets: dict with camera_angle, camera_motion, camera_shot,
          camera_amplitude, camera_speed, style (all optional, default "none")

    references: list of dicts with keys:
        - id: str (e.g. "ref-1")
        - type: "picture" | "video" | "audio"
        - label: str (e.g. "Picture 1")
        - role: str (first_frame, last_frame, frame, subject_identity, etc.)
        - image_filename: str (for pictures, uploaded to ComfyUI input)
        - image_subfolder: str (usually "")
        - strength: str ("weak", "normal", "strong") for subject_identity
        - video_filename: str (for videos)
        - video_subfolder: str
        - duration: float (for videos)
    """
    toyxyz_mode = MODE_MAP.get(mode, "AUTO")
    project = {
        "version": 26,
        "mode": toyxyz_mode,
        "requested_duration": duration,
        "user_request": user_request,
        "shots": [],
        "references": references or [],
        "constraints": constraints,
        "verbatim_content": verbatim_content,
        "enhance_model": enhance_model,
        "image_model": image_model,
        "auto_run": False,
        "enhance": True,
        "enhance_level": enhance_level,
        "enhanced_prompt": "",
    }
    for i, shot in enumerate(shots, 1):
        presets = shot.get("presets", {})
        project["shots"].append({
            "id": f"shot-{i}",
            "duration": shot.get("duration", duration),
            "visual_action": shot.get("visual_action", ""),
            "presets": {
                "camera_angle": presets.get("camera_angle", "none"),
                "camera_motion": presets.get("camera_motion", "none"),
                "camera_shot": presets.get("camera_shot", "none"),
                "camera_amplitude": presets.get("camera_amplitude", "none"),
                "camera_speed": presets.get("camera_speed", "none"),
                "style": presets.get("style", "none"),
            },
        })
    return json.dumps(project, ensure_ascii=False)


def compile_project(server: str, project_data: str, timeout: int = 30) -> dict:
    """Call the toyxyz compile endpoint (deterministic, no LLM)."""
    return _post_json(
        server.rstrip("/") + "/toyxyz/minimax_h3_prompter/compile",
        {"project_data": project_data},
        timeout=timeout,
    )


def enhance_project(
    server: str,
    project_data: str,
    *,
    model: str = DEFAULT_ENHANCE_MODEL,
    image_model: str = DEFAULT_IMAGE_MODEL,
    job_id: str = "",
    timeout: int = 600,
) -> dict:
    """Call the toyxyz enhance endpoint (runs LLM, blocking).

    Returns dict with keys: status, enhanced_prompt, model, model_path,
    reference_analyses, raw_model_prompt.
    """
    if not job_id:
        job_id = str(uuid.uuid4())
    return _post_json(
        server.rstrip("/") + "/toyxyz/minimax_h3_prompter/enhance",
        {
            "project_data": project_data,
            "model": model,
            "image_model": image_model,
            "job_id": job_id,
        },
        timeout=timeout,
    )


def check_enhance_status(server: str, job_id: str, timeout: int = 10) -> dict:
    """Poll the enhance job status."""
    return _get_json(
        server.rstrip("/") + f"/toyxyz/minimax_h3_prompter/enhance/status?job_id={job_id}",
        timeout=timeout,
    )


def upload_references(
    server: str,
    assets: list[dict],
    timeout: int = 60,
) -> list[dict]:
    """Upload reference media to local ComfyUI and return enriched reference dicts.

    Each asset dict should have:
        - local_path: str (path to the image file on disk)
        - binding: str (first_frame, last_frame, frame, subject)
        - media_type: str ("image" or "video")
        - label: str (e.g. "Picture 1")
    """
    references = []
    pic_num = 0
    vid_num = 0
    for asset in assets:
        media_type = asset.get("media_type", "image")
        if media_type == "image":
            pic_num += 1
            local_path = asset.get("local_path", "")
            if not local_path:
                continue
            upload_result = upload_file(server, Path(local_path), timeout)
            role = BINDING_TO_ROLE.get(asset.get("binding", ""), "subject_identity")
            references.append({
                "id": f"ref-{pic_num}",
                "type": "picture",
                "label": f"Picture {pic_num}",
                "role": role,
                "image_filename": upload_result.get("name", ""),
                "image_subfolder": upload_result.get("subfolder", ""),
                "strength": asset.get("strength", "normal"),
            })
        elif media_type == "video":
            vid_num += 1
            local_path = asset.get("local_path", "")
            if not local_path:
                continue
            upload_result = upload_file(server, Path(local_path), timeout)
            references.append({
                "id": f"ref-{pic_num + vid_num}",
                "type": "video",
                "label": f"Video {vid_num}",
                "role": asset.get("role", "motion"),
                "video_filename": upload_result.get("name", ""),
                "video_subfolder": upload_result.get("subfolder", ""),
                "duration": asset.get("duration", 0.0),
            })
    return references


def generate_prompt(
    server: str,
    *,
    mode: str,
    duration: float,
    user_request: str,
    shots: list[dict],
    reference_assets: list[dict] | None = None,
    constraints: str = "",
    verbatim_content: str = "",
    enhance_level: str = "normal",
    enhance_model: str = DEFAULT_ENHANCE_MODEL,
    image_model: str = DEFAULT_IMAGE_MODEL,
    upload_timeout: int = 60,
    enhance_timeout: int = 600,
) -> str:
    """Full pipeline: upload references, build project, enhance, return prompt text.

    Returns the enhanced H3 prompt string.
    Raises RuntimeError on failure.
    """
    # Upload reference images to local ComfyUI
    references = []
    if reference_assets:
        references = upload_references(server, reference_assets, timeout=upload_timeout)

    # Build project data
    project_data = build_project_data(
        mode=mode,
        duration=duration,
        user_request=user_request,
        shots=shots,
        references=references,
        constraints=constraints,
        verbatim_content=verbatim_content,
        enhance_level=enhance_level,
        enhance_model=enhance_model,
        image_model=image_model,
    )

    # First compile to check for validation errors
    compile_result = compile_project(server, project_data)
    if compile_result.get("errors"):
        raise ValueError(
            "toyxyz project validation failed: " + "; ".join(compile_result["errors"])
        )

    # Enhance (runs LLM)
    enhance_result = enhance_project(
        server, project_data,
        model=enhance_model,
        image_model=image_model,
        timeout=enhance_timeout,
    )

    if enhance_result.get("status") != "success":
        raise RuntimeError(
            f"toyxyz enhance failed: {enhance_result.get('message', 'unknown error')}"
        )

    return enhance_result.get("enhanced_prompt", "")

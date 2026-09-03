"""Generate AI Design reference images through ComfyUI without blocking Qt."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import secrets
import sys
import urllib.parse
import urllib.request
import uuid

from comfy_submit_worker import _direct_urlopen, _request_json, wait_for_history
from media_engine import remove_solid_background


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def image_workflow(
    request: dict,
    settings: dict,
    seed: int,
    prefix: str,
    template: dict | None = None,
) -> dict:
    positive = request.get("prompt", "").strip()
    negative_parts = [
        str(value).strip(" ,")
        for value in (
            settings.get("negative_prompt", ""),
            request.get("negative_prompt", ""),
        )
        if str(value).strip(" ,")
    ]
    negative = ", ".join(dict.fromkeys(negative_parts))
    keywords = ", ".join(request.get("subject_keywords") or [])
    if keywords:
        positive = f"{positive}. Key subjects: {keywords}."
    if template:
        workflow = deepcopy(template)

        def nodes_of_type(class_type: str) -> list[tuple[str, dict]]:
            return [
                (node_id, node)
                for node_id, node in workflow.items()
                if node.get("class_type") == class_type
            ]

        def require_node(class_type: str) -> tuple[str, dict]:
            matches = nodes_of_type(class_type)
            if not matches:
                raise ValueError(f"Z-Image workflow is missing required node {class_type}")
            return matches[0]

        _prompt_id, prompt_node = require_node("CLIPTextEncode")
        _sampler_id, sampler_node = require_node("KSampler")
        _latent_id, latent_node = require_node("EmptySD3LatentImage")
        _save_id, save_node = require_node("SaveImage")
        prompt_node["inputs"]["text"] = positive
        if negative:
            numeric_ids = [int(node_id) for node_id in workflow if str(node_id).isdigit()]
            negative_id = str(max(numeric_ids, default=0) + 1)
            workflow[negative_id] = {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative,
                    "clip": deepcopy(prompt_node["inputs"].get("clip")),
                },
            }
            sampler_node["inputs"]["negative"] = [negative_id, 0]
        sampler_node["inputs"].update({
            "seed": seed,
            "steps": int(settings["steps"]),
            "cfg": float(settings["cfg"]),
        })
        latent_node["inputs"].update({
            "width": int(settings["width"]),
            "height": int(settings["height"]),
            "batch_size": 1,
        })
        save_node["inputs"]["filename_prefix"] = prefix
        unet_name = str(settings.get("checkpoint", "")).strip()
        unet_nodes = nodes_of_type("UNETLoader")
        if unet_name and unet_nodes:
            unet_nodes[0][1]["inputs"]["unet_name"] = unet_name
        return workflow
    positive += (
        " Professional commercial photography, coherent subject identity, realistic hands, "
        "cinematic natural lighting, production-ready reference frame."
    )
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": settings["checkpoint"]},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive, "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": int(settings["width"]),
                "height": int(settings["height"]),
                "batch_size": 1,
            },
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "seed": seed,
                "steps": int(settings["steps"]),
                "cfg": float(settings["cfg"]),
                "sampler_name": "dpmpp_2m_sde",
                "scheduler": "karras",
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "denoise": 1.0,
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["6", 0], "filename_prefix": prefix},
        },
    }


def queue_workflow(server: str, workflow: dict, timeout: int) -> str:
    data = json.dumps(
        {"prompt": workflow, "client_id": "h3-design-" + uuid.uuid4().hex},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        server + "/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    queued = _request_json(request, timeout)
    prompt_id = str(queued.get("prompt_id", ""))
    if not prompt_id:
        raise RuntimeError(f"ComfyUI did not return a prompt_id: {queued}")
    return prompt_id


def download_image(server: str, output: dict, destination: Path, timeout: int) -> None:
    query = urllib.parse.urlencode({
        "filename": output["filename"],
        "subfolder": output.get("subfolder", ""),
        "type": output.get("type", "output"),
    })
    with _direct_urlopen(server + "/view?" + query, timeout) as response:
        destination.write_bytes(response.read())


def _generate_request(
    job: dict,
    item: dict,
    settings: dict,
    workflow_template: dict | None,
    *,
    number: int,
) -> dict:
    server = str(job["server"]).rstrip("/")
    destination = Path(item["local_path"])
    seed = secrets.randbits(63)
    workflow = image_workflow(
        item,
        settings,
        seed,
        f"h3_design/{destination.stem}",
        workflow_template,
    )
    prompt_id = queue_workflow(server, workflow, int(job["http_timeout"]))
    _history, outputs = wait_for_history(
        server,
        prompt_id,
        poll_interval=float(job["poll_interval"]),
        generation_timeout=int(job["generation_timeout"]),
        http_timeout=int(job["http_timeout"]),
    )
    image_output = next(
        (
            output for output in outputs
            if str(output.get("filename", "")).lower().endswith(
                (".png", ".jpg", ".jpeg", ".webp")
            )
        ),
        None,
    )
    if image_output is None:
        raise RuntimeError("ComfyUI completed without an image output")
    download_image(server, image_output, destination, int(job["http_timeout"]))
    transparent_destination = destination.with_name(destination.stem + "_nobg.png")
    background_removal = remove_solid_background(destination, transparent_destination)
    effective_destination = transparent_destination if background_removal else destination
    sidecar = destination.with_suffix(destination.suffix + ".request.json")
    if sidecar.is_file():
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        metadata["comfyui_generation"] = {
            "generated": True,
            "seed": seed,
            "prompt_id": prompt_id,
            "checkpoint": settings["checkpoint"],
            "width": int(settings["width"]),
            "height": int(settings["height"]),
            "steps": int(settings["steps"]),
            "cfg": float(settings["cfg"]),
        }
        sidecar.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return {
        "local_path": str(effective_destination.resolve()),
        "original_local_path": str(destination.resolve()),
        "seed": seed,
        "prompt_id": prompt_id,
        "generated": True,
        "request_index": item.get("request_index", number - 1),
        "background_removal": background_removal,
    }


def generate(job: dict) -> dict:
    settings = dict(job["settings"])
    workflow_path = Path(str(job.get("workflow_path", "")))
    workflow_template = (
        json.loads(workflow_path.read_text(encoding="utf-8-sig"))
        if workflow_path.is_file()
        else None
    )
    requests = [item for item in job.get("materials", []) if item.get("media_type") == "image"]
    results: list[dict] = []
    warnings: list[str] = []
    max_attempts = max(1, min(3, int(job.get("attempts_per_image", 2))))
    for number, item in enumerate(requests, 1):
        destination = Path(item["local_path"])
        for attempt in range(1, max_attempts + 1):
            emit({
                "progress": (
                    f"Generating reference image {number}/{len(requests)} · {destination.name}"
                    + (f" · retry {attempt}/{max_attempts}" if attempt > 1 else "")
                ),
                "index": number - 1,
            })
            try:
                generated = _generate_request(
                    job,
                    item,
                    settings,
                    workflow_template,
                    number=number,
                )
            except Exception as exc:
                if attempt < max_attempts:
                    emit({
                        "progress": (
                            f"Reference {number}/{len(requests)} failed once · retrying · {exc}"
                        ),
                        "index": number - 1,
                    })
                    continue
                warning = f"{destination.name}: failed after {max_attempts} attempt(s): {exc}"
                warnings.append(warning)
                emit({"progress": f"Using placeholder · {warning}", "index": number - 1})
                break
            results.append(generated)
            emit({"generated_output": generated, "index": number - 1})
            emit({"progress": f"Generated {destination.name}", "index": number - 1})
            break
    return {"completed": True, "outputs": results, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job")
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    emit(generate(job))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        emit({"error": str(exc)})
        raise SystemExit(1)

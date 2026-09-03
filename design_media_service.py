"""Generate AI Design reference images through ComfyUI without blocking Qt."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import random
import secrets
import sys
import urllib.parse
import urllib.request
import uuid

from comfy_submit_worker import _direct_urlopen, _request_json, wait_for_history
from media_engine import remove_solid_background


def render_immutable_source_plate(
    request: dict,
    destination: Path,
    seed: int,
) -> dict:
    """Copy P1 exactly, optionally adding only a deterministic effect layer."""

    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

    source = Path(str(request.get("source_plate_local_path", "")))
    if not source.is_file():
        raise FileNotFoundError(
            "Immutable terminal frame requires the loaded P1 local image."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    profile = str(request.get("source_plate_effect_profile", "preserve_existing"))
    if profile != "fireworks":
        ImageOps.exif_transpose(Image.open(source)).convert("RGB").save(
            destination,
            format="PNG",
        )
        return {
            "mode": "immutable_copy",
            "source_plate": str(source.resolve()),
            "effect_profile": profile,
        }

    base = ImageOps.exif_transpose(Image.open(source)).convert("RGBA")
    width, height = base.size
    scale = 2
    canvas = (width * scale, height * scale)
    rng = random.Random(seed)

    glow = Image.new("RGBA", canvas, (0, 0, 0, 0))
    particles = Image.new("RGBA", canvas, (0, 0, 0, 0))
    smoke = Image.new("RGBA", canvas, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow, "RGBA")
    particle_draw = ImageDraw.Draw(particles, "RGBA")
    smoke_draw = ImageDraw.Draw(smoke, "RGBA")
    colours = [
        (255, 196, 72),
        (255, 244, 220),
        (188, 38, 45),
        (255, 215, 120),
    ]
    centres = [
        (0.17, 0.19),
        (0.82, 0.22),
        (0.34, 0.10),
        (0.68, 0.11),
        (0.50, 0.055),
    ]
    burst_records: list[dict] = []
    for burst_index, (cx_ratio, cy_ratio) in enumerate(centres):
        cx = int(cx_ratio * canvas[0])
        cy = int(cy_ratio * canvas[1])
        colour = colours[burst_index % len(colours)]
        radius = int(min(canvas) * (0.075 if burst_index < 4 else 0.095))
        rays = 52 if burst_index < 4 else 72
        glow_draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=(*colour, 38),
        )
        for ray in range(rays):
            angle = (math.tau * ray / rays) + rng.uniform(-0.035, 0.035)
            inner = radius * rng.uniform(0.10, 0.22)
            outer = radius * rng.uniform(0.70, 1.08)
            x1 = cx + math.cos(angle) * inner
            y1 = cy + math.sin(angle) * inner
            x2 = cx + math.cos(angle) * outer
            y2 = cy + math.sin(angle) * outer + rng.uniform(0, radius * 0.10)
            particle_draw.line(
                (x1, y1, x2, y2),
                fill=(*colour, rng.randint(145, 235)),
                width=max(1, scale),
            )
            particle_draw.ellipse(
                (x2 - scale, y2 - scale, x2 + scale, y2 + scale),
                fill=(255, 248, 225, rng.randint(155, 245)),
            )
        smoke_width = radius * rng.uniform(0.9, 1.5)
        smoke_height = radius * rng.uniform(0.45, 0.75)
        smoke_draw.ellipse(
            (
                cx - smoke_width * 0.15,
                cy - smoke_height * 0.10,
                cx + smoke_width,
                cy + smoke_height,
            ),
            fill=(155, 158, 170, rng.randint(20, 42)),
        )
        burst_records.append({
            "centre": [round(cx_ratio, 3), round(cy_ratio, 3)],
            "colour": list(colour),
        })

    glow = glow.filter(ImageFilter.GaussianBlur(max(5, int(min(canvas) * 0.025))))
    smoke = smoke.filter(ImageFilter.GaussianBlur(max(7, int(min(canvas) * 0.018))))
    effects = Image.alpha_composite(glow, smoke)
    effects = Image.alpha_composite(effects, particles)
    effects = effects.resize((width, height), Image.Resampling.LANCZOS)

    # Protect existing high-contrast architecture edges in the upper frame so
    # particles read as behind the P1 skyline rather than painted over it.
    luminance = base.convert("L")
    edges = luminance.filter(ImageFilter.FIND_EDGES)
    threshold = edges.point(lambda value: 255 if value > 28 else 0)
    threshold = threshold.filter(ImageFilter.MaxFilter(7))
    protect = Image.new("L", (width, height), 0)
    protect.paste(threshold.crop((0, 0, width, int(height * 0.62))), (0, 0))
    effect_alpha = effects.getchannel("A")
    effect_alpha = ImageChops.subtract(effect_alpha, protect)
    effects.putalpha(effect_alpha)

    composite = Image.alpha_composite(base, effects)

    # Low-opacity warm illumination changes colour only; it never moves or
    # replaces P1 geometry. The original cool-blue plate remains dominant.
    warm = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    warm_draw = ImageDraw.Draw(warm, "RGBA")
    warm_draw.rectangle(
        (0, int(height * 0.38), width, height),
        fill=(255, 142, 52, 12),
    )
    warm = warm.filter(ImageFilter.GaussianBlur(max(3, int(height * 0.03))))
    composite = Image.alpha_composite(composite, warm).convert("RGB")
    composite.save(destination, format="PNG")
    return {
        "mode": "immutable_effect_composite",
        "source_plate": str(source.resolve()),
        "effect_profile": profile,
        "bursts": burst_records,
        "geometry_source": "unchanged P1 pixels",
    }


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
    source_plate_mode = str(item.get("source_plate_mode", "")).strip()
    if source_plate_mode in {"immutable_copy", "immutable_effect_composite"}:
        plate_result = render_immutable_source_plate(item, destination, seed)
        sidecar = destination.with_suffix(destination.suffix + ".request.json")
        if sidecar.is_file():
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
            metadata["immutable_source_plate_generation"] = {
                **plate_result,
                "seed": seed,
            }
            sidecar.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return {
            "local_path": str(destination.resolve()),
            "original_local_path": str(destination.resolve()),
            "seed": seed,
            "prompt_id": "local-immutable-source-plate",
            "generated": True,
            "request_index": item.get("request_index", number - 1),
            "background_removal": {},
            "immutable_source_plate_generation": plate_result,
        }
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

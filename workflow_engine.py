"""Inspect ComfyUI API-format workflows and discover reference media nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any


MEDIA_LOADERS = {
    "LoadImage": ("image", "image"),
    "LoadVideo": ("video", "file"),
    "LoadAudio": ("audio", "audio"),
}


@dataclass(slots=True)
class MediaAsset:
    node_id: str
    class_type: str
    media_type: str
    filename: str
    tag: str = "—"
    binding: str = "unassigned"
    paired_audio_binding: str = ""
    state: str = "active"
    start_seconds: float = 0.0
    end_seconds: float = 0.0
    enabled: bool = True
    activation_mode: str = "auto"
    local_path: str = ""
    recognition: str = ""
    # Keep evidence produced by FFprobe/BLIP/VAD/Whisper separate from the
    # optional language-model interpretation.  This prevents inferred details
    # from being fed back into a later recognition pass as if they were facts.
    semantic_enrichment: str = ""
    semantic_enrichment_source_hash: str = ""
    semantic_enrichment_model: str = ""
    semantic_enrichment_updated_at: str = ""
    timeline_placed: bool = False
    timeline_lane: int = 0
    timeline_track_id: str = ""
    source_duration_seconds: float = 0.0
    playback_speed: float = 1.0
    source_in_seconds: float = 0.0
    source_out_seconds: float = 0.0
    fade_in_seconds: float = 0.0
    fade_out_seconds: float = 0.0
    transition_in: str = "None"
    transition_out: str = "None"
    clip_prompt: str = ""
    # H3 references may remain active for generation without being composited as
    # literal picture layers in the Program Monitor.
    monitor_visible: bool = True
    # A Media Pool source may be used more than once on the Timeline.  The
    # original loader asset keeps an empty clip_id; additional editorial uses
    # carry a stable clip_id while source_node_id points back to the one
    # physical ComfyUI loader/reference slot.
    clip_id: str = ""
    source_node_id: str = ""

    def overlaps(self, clip_start: float, clip_end: float) -> bool:
        """Return whether this reference participates in the current generation clip."""
        if (
            not self.enabled
            or not self.timeline_placed
            or self.activation_mode == "bypass"
            or self.state != "active"
            or self.binding == "unassigned"
        ):
            return False
        if self.activation_mode == "active":
            return True
        return self.start_seconds < clip_end and self.end_seconds > clip_start


@dataclass(slots=True)
class WorkflowScan:
    path: Path
    nodes: dict[str, dict[str, Any]]
    h3_node_ids: list[str]
    assets: list[MediaAsset] = field(default_factory=list)
    timeline_clips: list[MediaAsset] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 5.0

    @property
    def counts(self) -> dict[str, int]:
        return {
            kind: sum(asset.media_type == kind for asset in self.assets)
            for kind in ("image", "video", "audio")
        }

    def active_assets(self, clip_start: float, clip_end: float) -> list[MediaAsset]:
        return [asset for asset in self.timeline_assets() if asset.overlaps(clip_start, clip_end)]

    def timeline_assets(self) -> list[MediaAsset]:
        """Return legacy first uses plus independent repeated clip instances."""
        return [*self.assets, *self.timeline_clips]


def load_workflow(path: str | Path) -> WorkflowScan:
    workflow_path = Path(path)
    try:
        payload = json.loads(workflow_path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        payload = json.loads(workflow_path.read_text(encoding="utf-16"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"不是有效的 ComfyUI JSON：第 {exc.lineno} 行，第 {exc.colno} 列。") from exc

    return scan_workflow_data(payload, workflow_path)


def scan_workflow_data(payload: Any, path: str | Path = "workflow.json") -> WorkflowScan:
    """Scan an already decoded workflow payload (also useful for API clients/tests)."""
    workflow_path = Path(path)
    nodes = _normalize_nodes(payload)
    if not nodes:
        raise ValueError("JSON 中没有找到 ComfyUI 节点。请使用 Save (API Format) 导出的文件。")

    h3_ids = [
        node_id
        for node_id, node in nodes.items()
        if node.get("class_type") == "MiniMaxH3ReferenceToVideo"
    ]
    scan = WorkflowScan(
        workflow_path.resolve(), nodes, h3_ids, duration_seconds=_find_duration(nodes)
    )
    _discover_assets(scan)
    for asset in scan.assets:
        asset.end_seconds = scan.duration_seconds
    _add_warnings(scan)
    return scan


def _normalize_nodes(payload: Any) -> dict[str, dict[str, Any]]:
    """Accept API format and the common `{prompt: ...}` wrapper."""
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("prompt"), dict):
        payload = payload["prompt"]
    return {
        str(node_id): node
        for node_id, node in payload.items()
        if isinstance(node, dict) and isinstance(node.get("class_type"), str)
    }


def _find_duration(nodes: dict[str, dict[str, Any]]) -> float:
    candidates: list[float] = []
    for node in nodes.values():
        if node.get("class_type") != "PrimitiveFloat":
            continue
        value = (node.get("inputs") or {}).get("value")
        if not isinstance(value, (int, float)):
            continue
        title = str((node.get("_meta") or {}).get("title", "")).lower()
        if "duration" in title:
            return max(0.01, float(value))
        candidates.append(float(value))
    return max(0.01, candidates[0]) if candidates else 5.0


def _node_state(node: dict[str, Any]) -> str:
    # LiteGraph modes: 0=always, 2=never/muted, 4=bypass. API-format
    # exports normally eliminate bypassed nodes before writing the graph.
    mode = node.get("mode")
    if mode == 4 or node.get("bypass") is True:
        return "bypassed"
    if mode == 2 or node.get("disabled") is True:
        return "muted"
    return "active"


def _connection(value: Any) -> tuple[str, int] | None:
    if (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], (str, int))
        and isinstance(value[1], int)
    ):
        return str(value[0]), value[1]
    return None


def _loader_info(node_id: str, nodes: dict[str, dict[str, Any]]) -> MediaAsset | None:
    node = nodes.get(node_id, {})
    class_type = node.get("class_type", "")
    loader = MEDIA_LOADERS.get(class_type)
    if loader is None:
        # Be tolerant of custom loader names if they expose conventional fields.
        lowered = class_type.lower()
        if "load" in lowered and "image" in lowered:
            loader = ("image", "image")
        elif "load" in lowered and "video" in lowered:
            loader = ("video", "file")
        elif "load" in lowered and "audio" in lowered:
            loader = ("audio", "audio")
        else:
            return None
    media_type, field_name = loader
    inputs = node.get("inputs") or {}
    filename = inputs.get(field_name, "")
    if not isinstance(filename, str):
        filename = str(filename)
    return MediaAsset(
        node_id=node_id,
        class_type=class_type,
        media_type=media_type,
        filename=filename,
        state=_node_state(node),
    )


def _find_upstream_loader(
    start_node_id: str,
    nodes: dict[str, dict[str, Any]],
    wanted_type: str,
) -> MediaAsset | None:
    pending = [start_node_id]
    visited: set[str] = set()
    fallback: MediaAsset | None = None
    while pending:
        node_id = pending.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)
        asset = _loader_info(node_id, nodes)
        if asset:
            if asset.media_type == wanted_type:
                return asset
            fallback = fallback or asset
        for value in (nodes.get(node_id, {}).get("inputs") or {}).values():
            connection = _connection(value)
            if connection:
                pending.append(connection[0])
    return fallback


def _binding_details(input_name: str) -> tuple[str, str, int] | None:
    patterns = (
        (r"^ref_images\.ref_image_(\d+)$", "image", "Picture"),
        (r"^ref_videos\.ref_video_(\d+)$", "video", "Video"),
        (r"^ref_audios\.ref_audio_(\d+)$", "audio", "Audio"),
        (r"^ref_video_audios\.ref_video_audio_(\d+)$", "video_audio", "Video Audio"),
    )
    for pattern, media_type, label in patterns:
        match = re.match(pattern, input_name)
        if match:
            return media_type, label, int(match.group(1))
    return None


def _discover_assets(scan: WorkflowScan) -> None:
    assigned_node_ids: set[str] = set()
    for h3_id in scan.h3_node_ids:
        inputs = scan.nodes[h3_id].get("inputs") or {}
        binding_items = [
            (input_name, value, _binding_details(input_name))
            for input_name, value in inputs.items()
            if _binding_details(input_name)
        ]
        # Discover video frames before their paired soundtrack so both bindings
        # are represented by a single timeline asset.
        priority = {"image": 0, "video": 1, "video_audio": 2, "audio": 3}
        binding_items.sort(key=lambda item: priority[item[2][0]])
        for input_name, value, details in binding_items:
            details = _binding_details(input_name)
            connection = _connection(value)
            if not details or not connection:
                continue
            binding_type, label, zero_index = details
            wanted_type = "video" if binding_type == "video_audio" else binding_type
            asset = _find_upstream_loader(connection[0], scan.nodes, wanted_type)
            if not asset:
                scan.warnings.append(
                    f"H3 节点 {h3_id} 的 {input_name} 已连接，但找不到上游素材加载节点。"
                )
                continue
            asset.tag = f"<{label} {zero_index + 1}>"
            asset.binding = input_name
            if binding_type == "video_audio":
                existing = next(
                    (
                        item
                        for item in scan.assets
                        if item.node_id == asset.node_id and item.media_type == "video"
                    ),
                    None,
                )
                if existing:
                    existing.paired_audio_binding = input_name
                    continue
                asset.media_type = "video"
                asset.tag = f"<Video {zero_index + 1}>"
                asset.paired_audio_binding = input_name
            if asset.node_id not in assigned_node_ids:
                scan.assets.append(asset)
                assigned_node_ids.add(asset.node_id)

    assigned_loader_ids = {asset.node_id for asset in scan.assets}
    for node_id in scan.nodes:
        asset = _loader_info(node_id, scan.nodes)
        if asset and node_id not in assigned_loader_ids:
            scan.assets.append(asset)

    order = {"image": 0, "video": 1, "audio": 2}
    scan.assets.sort(key=lambda item: (order.get(item.media_type, 9), item.tag, int(item.node_id) if item.node_id.isdigit() else item.node_id))


def _add_warnings(scan: WorkflowScan) -> None:
    if not scan.h3_node_ids:
        scan.warnings.append("没有检测到 MiniMaxH3ReferenceToVideo 节点。")
    counts = scan.counts
    if counts["video"] == 0:
        scan.warnings.append(
            "没有检测到 LoadVideo。若视频节点在 ComfyUI 中处于 bypass，API 导出会将它从可执行图中移除。"
        )
    if counts["audio"] == 0 and not any(asset.paired_audio_binding for asset in scan.assets):
        scan.warnings.append(
            "没有检测到 LoadAudio 或视频配套音轨。若音频节点处于 bypass，API 文件无法保存其素材文件名。"
        )


def suggested_reference_rules(scan: WorkflowScan) -> tuple[str, str]:
    """Build editable reference/audio mapping text for the prompt form."""
    visual: list[str] = []
    audio: list[str] = []
    for asset in scan.assets:
        if asset.tag == "—":
            continue
        source = f'"{asset.filename}"' if asset.filename else f"node {asset.node_id}"
        if asset.tag.startswith("<Picture"):
            visual.append(f"Use {asset.tag} from {source} as a reference image.")
        elif asset.tag.startswith("<Video "):
            visual.append(f"Use {asset.tag} from {source} as a reference video.")
            if asset.paired_audio_binding:
                audio.append(f"Use the synchronized soundtrack paired with {asset.tag} from {source}.")
        elif asset.tag.startswith("<Audio"):
            audio.append(f"Use {asset.tag} from {source} exactly as supplied.")
    return " ".join(visual), " ".join(audio)


REFERENCE_INPUT_PREFIXES = (
    "ref_images.ref_image_",
    "ref_videos.ref_video_",
    "ref_video_audios.ref_video_audio_",
    "ref_audios.ref_audio_",
)


REFERENCE_INPUT_GROUPS = (
    "ref_images.ref_image_",
    "ref_videos.ref_video_",
    "ref_video_audios.ref_video_audio_",
    "ref_audios.ref_audio_",
)


def compact_h3_reference_inputs(
    workflow: dict[str, dict[str, Any]],
    h3_node_ids: list[str] | tuple[str, ...],
) -> None:
    """Rewrite active H3 reference inputs into contiguous request-local slots.

    Media Pool identities remain permanently tied to their loader/binding (P5,
    V2, A3, and so on), but MiniMax prompt labels describe the references in a
    *single compiled request*.  Leaving a sparse physical field such as
    ``ref_image_4`` connected while calling it ``<Picture 4>`` makes the prompt
    and graph disagree.  This pass preserves each upstream connection and its
    relative source order while removing every gap independently for pictures,
    videos, paired video audio, and standalone audio.
    """

    def suffix(name: str) -> int:
        match = re.search(r"_(\d+)$", name)
        return int(match.group(1)) if match else 10_000

    for h3_id in h3_node_ids:
        node = workflow.get(str(h3_id))
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue
        ordinary = [
            (name, value)
            for name, value in inputs.items()
            if not name.startswith(REFERENCE_INPUT_GROUPS)
        ]
        compacted: list[tuple[str, Any]] = []
        for prefix in REFERENCE_INPUT_GROUPS:
            rows = sorted(
                (
                    (name, value)
                    for name, value in inputs.items()
                    if name.startswith(prefix)
                ),
                key=lambda row: suffix(row[0]),
            )
            compacted.extend(
                (f"{prefix}{request_index}", value)
                for request_index, (_name, value) in enumerate(rows)
            )
        node["inputs"] = dict(ordinary + compacted)


ASPECT_RATIO_NODE_VALUES = {
    "16:9": "16:9 (Widescreen)",
    "9:16": "9:16 (Portrait Widescreen)",
    "1:1": "1:1 (Square)",
    "4:3": "4:3 (Standard)",
    "3:4": "3:4 (Portrait Standard)",
    "21:9": "21:9 (Ultrawide)",
}


def apply_generation_parameters(
    workflow: dict[str, dict[str, Any]],
    *,
    aspect_ratio: str,
    megapixels: float,
    sampling_steps: int,
    denoise: float,
    seed: int,
    enable_rtx_vsr: bool,
) -> dict[str, list[str]]:
    """Patch known generation nodes in a compiled workflow copy.

    RTX VSR is disabled by rewiring its consumers directly to its image input.
    This is the API-format equivalent of bypass and avoids mutating the source graph.
    """
    touched: dict[str, list[str]] = {
        "resolution": [], "sampler": [], "seed": [], "rtx_vsr": []
    }
    rtx_nodes: dict[str, list[Any]] = {}
    for node_id, node in workflow.items():
        class_type = str(node.get("class_type", ""))
        inputs = node.setdefault("inputs", {})
        if class_type == "ResolutionSelector":
            inputs["aspect_ratio"] = ASPECT_RATIO_NODE_VALUES.get(aspect_ratio, aspect_ratio)
            inputs["megapixels"] = float(megapixels)
            touched["resolution"].append(node_id)
        if class_type in {"BasicScheduler", "KSampler", "KSamplerAdvanced"}:
            if "steps" in inputs:
                inputs["steps"] = int(sampling_steps)
            if "denoise" in inputs:
                inputs["denoise"] = float(denoise)
            touched["sampler"].append(node_id)
        if class_type == "RandomNoise" and "noise_seed" in inputs:
            inputs["noise_seed"] = int(seed)
            touched["seed"].append(node_id)
        elif "seed" in inputs and isinstance(inputs["seed"], int):
            inputs["seed"] = int(seed)
            touched["seed"].append(node_id)
        if "RTXVideoSuperResolution" in class_type:
            touched["rtx_vsr"].append(node_id)
            source = inputs.get("images")
            if isinstance(source, list) and len(source) == 2:
                rtx_nodes[node_id] = list(source)

    if not enable_rtx_vsr:
        for node in workflow.values():
            inputs = node.get("inputs") or {}
            for name, value in list(inputs.items()):
                if (
                    isinstance(value, list)
                    and len(value) == 2
                    and str(value[0]) in rtx_nodes
                ):
                    inputs[name] = list(rtx_nodes[str(value[0])])
    return touched


def compile_active_workflow(
    scan: WorkflowScan,
    clip_start: float = 0.0,
    clip_end: float | None = None,
    prompt: str | None = None,
    generation: dict[str, Any] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[MediaAsset]]:
    """Compile a copy containing only references relevant to a generation time window.

    The source workflow is never mutated. Inactive loader nodes may remain in the
    JSON, but their H3 reference connections are removed, so ComfyUI will not
    execute them as part of the output graph.
    """
    if clip_end is None:
        clip_end = scan.duration_seconds
    if clip_start < 0 or clip_end <= clip_start:
        raise ValueError("生成时间窗必须满足 0 ≤ 开始时间 < 结束时间。")

    compiled = deepcopy(scan.nodes)
    active_assets = scan.active_assets(clip_start, clip_end)
    active_bindings: set[str] = set()
    for asset in active_assets:
        active_bindings.add(asset.binding)
        if asset.paired_audio_binding:
            active_bindings.add(asset.paired_audio_binding)

    for h3_id in scan.h3_node_ids:
        inputs = compiled[h3_id].setdefault("inputs", {})
        for input_name in list(inputs):
            if input_name.startswith(REFERENCE_INPUT_PREFIXES) and input_name not in active_bindings:
                inputs.pop(input_name)

    # Prompt ordinals are request-local, so the executable graph must use the
    # same contiguous ordering.  Asset objects deliberately retain their
    # permanent Media Pool bindings for stable @P/@V/@A identity remapping.
    compact_h3_reference_inputs(compiled, scan.h3_node_ids)

    clip_duration = clip_end - clip_start
    for node in compiled.values():
        if node.get("class_type") != "PrimitiveFloat":
            continue
        title = str((node.get("_meta") or {}).get("title", "")).lower()
        if "duration" in title:
            (node.setdefault("inputs", {}))["value"] = clip_duration

    if prompt is not None:
        for node in compiled.values():
            if node.get("class_type") == "PrimitiveStringMultiline":
                (node.setdefault("inputs", {}))["value"] = prompt
                break
    if generation:
        apply_generation_parameters(compiled, **generation)
    return compiled, active_assets


def effective_reference_assets(
    assets: list[MediaAsset],
    *,
    extra_kind: str = "",
    extra_binding: str = "",
    extra_has_paired_audio: bool = False,
) -> tuple[list[MediaAsset], str]:
    """Return prompt-only clones carrying H3's effective reference ordinals.

    MiniMaxH3ReferenceToVideo numbers only the references that are actually
    connected for a request.  A physical ``ref_image_8`` therefore becomes
    ``<Picture 6>`` when only five earlier image inputs are present.  Timeline
    windows routinely disconnect inactive inputs, so the editor's permanent
    pool labels cannot safely be used in a compiled prompt.

    ``extra_kind`` represents the hidden previous-segment continuity reference,
    which is always appended after ordinary Timeline references. The retained
    ``extra_binding`` argument is compatibility metadata only; a spare physical
    loader can never renumber active request references. The returned string is
    the hidden reference's effective H3 tag. Source assets are never mutated.
    """
    clones = [deepcopy(asset) for asset in assets]

    def binding_index(asset: MediaAsset) -> int:
        match = re.search(r"_(\d+)$", asset.binding)
        return int(match.group(1)) if match else 10_000

    extra_tag = ""

    def unique_binding_rows(kind: str) -> list[tuple[int, list[MediaAsset] | None]]:
        groups: dict[tuple[str, str], list[MediaAsset]] = {}
        for asset in clones:
            if asset.media_type != kind:
                continue
            key = (asset.source_node_id or asset.node_id, asset.binding)
            groups.setdefault(key, []).append(asset)
        return [
            (binding_index(group[0]), group)
            for group in groups.values()
        ]

    images = sorted(unique_binding_rows("image"), key=lambda row: row[0])
    for ordinal, (_index, group) in enumerate(images, 1):
        for asset in group or []:
            asset.tag = f"<Picture {ordinal}>"
    if extra_kind == "image":
        extra_tag = f"<Picture {len(images) + 1}>"

    videos = sorted(unique_binding_rows("video"), key=lambda row: row[0])
    for ordinal, (_index, group) in enumerate(videos, 1):
        for asset in group or []:
            asset.tag = f"<Video {ordinal}>"
    if extra_kind == "video":
        extra_tag = f"<Video {len(videos) + 1}>"

    paired_audio_count = sum(
        bool(group and group[0].paired_audio_binding) for _index, group in videos
    )
    if extra_kind == "video" and extra_has_paired_audio:
        paired_audio_count += 1
    audios = sorted(unique_binding_rows("audio"), key=lambda row: row[0])
    for ordinal, (_index, group) in enumerate(audios, paired_audio_count + 1):
        for asset in group or []:
            asset.tag = f"<Audio {ordinal}>"
    if extra_kind == "audio":
        extra_tag = f"<Audio {paired_audio_count + len(audios) + 1}>"
    return clones, extra_tag


_REFERENCE_TOKEN_RE = re.compile(
    r"@(?P<short_kind>[PVA])\s*(?P<short_number>\d+)"
    r"|<\s*(?P<long_kind>Picture|Video|Audio)\s+"
    r"(?P<long_number>\d+)\s*>",
    flags=re.IGNORECASE,
)


def stable_reference_id(asset: MediaAsset) -> str:
    """Return the permanent Media Pool ID for an asset (P4/V2/A1).

    ``asset.tag`` is request-local after :func:`effective_reference_assets`, so
    it cannot be used as an editor identity.  The physical H3 binding remains
    stable and is also shared by repeated Timeline Clip Instances.
    """
    prefixes = {"image": "P", "video": "V", "audio": "A"}
    prefix = prefixes.get(asset.media_type, "M")
    binding_patterns = {
        "image": r"ref_images\.ref_image_(\d+)$",
        "video": r"ref_videos\.ref_video_(\d+)$",
        "audio": r"ref_audios\.ref_audio_(\d+)$",
    }
    match = re.search(binding_patterns.get(asset.media_type, r"$^"), asset.binding)
    if match:
        return f"{prefix}{int(match.group(1)) + 1}"
    tag_number = re.search(r"(\d+)", asset.tag)
    return f"{prefix}{tag_number.group(1) if tag_number else '?'}"


def _reference_source_key(asset: MediaAsset) -> tuple[str, str, str]:
    return (
        asset.media_type,
        asset.source_node_id or asset.node_id,
        asset.binding,
    )


def paired_audio_reference_tags(
    effective_assets: list[MediaAsset],
) -> dict[tuple[str, str, str], str]:
    """Return effective ``<Audio N>`` labels for enabled video soundtracks.

    H3 numbers visual video references independently from audio signals.  An
    active video's explicitly connected ``ref_video_audio`` output enters the
    Audio sequence before standalone ``ref_audio`` inputs in this workflow.
    The result is keyed by the same permanent source identity used by dynamic
    reference remapping, so repeated Clip Instances share one audio label.
    """
    groups: dict[tuple[str, str, str], MediaAsset] = {}
    for asset in effective_assets:
        if asset.media_type != "video" or not asset.paired_audio_binding:
            continue
        groups.setdefault(_reference_source_key(asset), asset)

    def binding_index(asset: MediaAsset) -> int:
        match = re.search(r"_(\d+)$", asset.paired_audio_binding)
        return int(match.group(1)) if match else 10_000

    return {
        key: f"<Audio {ordinal}>"
        for ordinal, (key, _asset) in enumerate(
            sorted(groups.items(), key=lambda item: binding_index(item[1])),
            1,
        )
    }


def remap_reference_tokens(
    text: str,
    source_assets: list[MediaAsset],
    effective_assets: list[MediaAsset],
) -> str:
    """Compile stable/legacy editor references into request-local H3 tags.

    Authored ``@P4`` and legacy ``<Picture 4>`` both mean the permanent
    physical Media Pool source P4.  If P4 is connected in the current request,
    it is replaced with its actual H3 ordinal (which may be ``<Picture 1>``).
    An inactive or unknown source is rendered as non-token text so it can never
    silently bind to a different active reference with the same request-local
    ordinal.
    """
    if not text:
        return text

    source_by_id = {
        stable_reference_id(asset).upper(): asset
        for asset in source_assets
        if stable_reference_id(asset) not in {"P?", "V?", "A?", "M?"}
    }
    effective_by_source = {
        _reference_source_key(asset): asset.tag
        for asset in effective_assets
        if asset.tag and asset.tag != "—"
    }
    long_prefix = {"PICTURE": "P", "VIDEO": "V", "AUDIO": "A"}

    def replace(match: re.Match[str]) -> str:
        if match.group("short_kind"):
            stable_id = (
                match.group("short_kind").upper()
                + str(int(match.group("short_number")))
            )
        else:
            stable_id = (
                long_prefix[match.group("long_kind").upper()]
                + str(int(match.group("long_number")))
            )
        source = source_by_id.get(stable_id)
        if source is None:
            return f"[{stable_id} reference is unavailable]"
        effective_tag = effective_by_source.get(_reference_source_key(source))
        if effective_tag:
            return effective_tag
        return f"[{stable_id} reference is inactive in this segment]"

    return _REFERENCE_TOKEN_RE.sub(replace, str(text))


def remap_reference_value(
    value: Any,
    source_assets: list[MediaAsset],
    effective_assets: list[MediaAsset],
) -> Any:
    """Recursively remap reference tokens inside PromptSpec-compatible data."""
    if isinstance(value, str):
        return remap_reference_tokens(value, source_assets, effective_assets)
    if isinstance(value, list):
        return [
            remap_reference_value(item, source_assets, effective_assets)
            for item in value
        ]
    if isinstance(value, tuple):
        return tuple(
            remap_reference_value(item, source_assets, effective_assets)
            for item in value
        )
    if isinstance(value, dict):
        return {
            key: remap_reference_value(item, source_assets, effective_assets)
            for key, item in value.items()
        }
    return value


def media_upload_manifest(assets: list[MediaAsset]) -> list[dict[str, str]]:
    """Describe unique local uploads for the physical loader sources.

    ComfyUI uploads use ``overwrite=true``. Two unrelated local files can share
    a basename, so sending only ``image.png`` would let the later upload replace
    the first one. Each physical loader receives a deterministic request-local
    name and repeated Timeline instances collapse back to that same source.
    """
    loader_inputs = {"image": "image", "video": "file", "audio": "audio"}
    rows: dict[tuple[str, str], dict[str, str]] = {}
    for asset in assets:
        local_path = str(asset.local_path or "").strip()
        if not local_path:
            continue
        source_node_id = str(asset.source_node_id or asset.node_id)
        key = (asset.media_type, source_node_id)
        if key in rows:
            continue
        basename = Path(local_path).name
        safe_node = re.sub(r"[^A-Za-z0-9_-]+", "_", source_node_id).strip("_") or "node"
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", basename).strip("_") or "media"
        upload_name = f"h3ref_{asset.media_type}_{safe_node}_{safe_name}"
        rows[key] = {
            "path": local_path,
            "loader_node_id": source_node_id,
            "loader_input": loader_inputs.get(asset.media_type, "file"),
            "upload_name": upload_name,
        }
    return list(rows.values())


def patch_media_upload_names(
    workflow: dict[str, dict[str, Any]],
    uploads: list[dict[str, str]],
) -> None:
    """Point compiled loader nodes at their collision-safe uploaded names."""
    for row in uploads:
        node = workflow.get(str(row.get("loader_node_id", "")))
        upload_name = str(row.get("upload_name", "")).strip()
        loader_input = str(row.get("loader_input", "")).strip()
        if not isinstance(node, dict) or not upload_name or not loader_input:
            continue
        node.setdefault("inputs", {})[loader_input] = upload_name


def timed_reference_rules(assets: list[MediaAsset]) -> tuple[str, str]:
    """Build reference rules including the timeline range where each asset applies."""
    visual: list[str] = []
    audio: list[str] = []
    for asset in assets:
        window = f"from {asset.start_seconds:.2f}s to {asset.end_seconds:.2f}s"
        if asset.media_type == "image":
            visual.append(f"Use {asset.tag} {window} as an image reference.")
        elif asset.media_type == "video":
            visual.append(f"Use {asset.tag} {window} as a motion and temporal reference.")
            if asset.paired_audio_binding:
                audio.append(f"Use {asset.tag}'s synchronized soundtrack {window}.")
        elif asset.media_type == "audio":
            audio.append(f"Use {asset.tag} {window} exactly as supplied.")
    return " ".join(visual), " ".join(audio)


def assign_local_media(scan: WorkflowScan, asset: MediaAsset, path: str | Path) -> None:
    """Bind a local media file to a discovered loader node.

    ComfyUI API workflows store the uploaded filename rather than an absolute
    editor path. The local path is retained for preview/analysis while the
    workflow loader receives only the basename.
    """
    local_path = Path(path).expanduser().resolve()
    if not local_path.is_file():
        raise FileNotFoundError(local_path)
    if asset.local_path != str(local_path):
        asset.semantic_enrichment = ""
        asset.semantic_enrichment_source_hash = ""
        asset.semantic_enrichment_model = ""
        asset.semantic_enrichment_updated_at = ""
    node = scan.nodes.get(asset.node_id)
    if node is None:
        raise KeyError(f"Unknown media node: {asset.node_id}")
    field_name = MEDIA_LOADERS.get(asset.class_type, (asset.media_type, "file"))[1]
    if asset.media_type == "image":
        field_name = "image"
    elif asset.media_type == "audio":
        field_name = "audio"
    elif asset.media_type == "video":
        field_name = "file"
    node.setdefault("inputs", {})[field_name] = local_path.name
    asset.local_path = str(local_path)
    asset.filename = local_path.name

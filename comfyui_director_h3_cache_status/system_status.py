"""Read-only host resource telemetry for Director Studio and its tray app."""

from __future__ import annotations

import csv
import io
import shutil
import subprocess
import time
from typing import Any, Callable


def _percent(value: object) -> float | None:
    try:
        return round(min(100.0, max(0.0, float(value))), 1)
    except (TypeError, ValueError, OverflowError):
        return None


def parse_nvidia_smi_csv(text: str) -> dict[str, Any]:
    """Normalize one or more NVIDIA GPUs without exposing process details."""

    devices: list[dict[str, Any]] = []
    for row in csv.reader(io.StringIO(str(text or ""))):
        if len(row) < 5:
            continue
        try:
            index = int(row[0].strip())
            used_bytes = max(0, int(float(row[2].strip()) * 1024**2))
            total_bytes = max(0, int(float(row[3].strip()) * 1024**2))
        except (TypeError, ValueError, OverflowError):
            continue
        gpu_percent = _percent(row[4].strip())
        vram_percent = _percent(
            used_bytes * 100.0 / total_bytes if total_bytes else None
        )
        devices.append({
            "index": index,
            "name": row[1].strip(),
            "vram_used_bytes": used_bytes,
            "vram_total_bytes": total_bytes,
            "vram_percent": vram_percent,
            "gpu_percent": gpu_percent,
        })
    if not devices:
        return {
            "gpu_available": False,
            "gpu_percent": None,
            "vram_percent": None,
            "vram_used_bytes": None,
            "vram_total_bytes": None,
            "gpu_name": "",
            "gpus": [],
        }
    # ComfyUI normally uses the busiest adapter. Reporting the busiest device
    # avoids hiding load on GPU 1 behind an idle display GPU 0.
    primary = max(
        devices,
        key=lambda device: (
            float(device.get("gpu_percent") or 0.0),
            float(device.get("vram_percent") or 0.0),
        ),
    )
    return {
        "gpu_available": True,
        "gpu_percent": primary["gpu_percent"],
        "vram_percent": primary["vram_percent"],
        "vram_used_bytes": primary["vram_used_bytes"],
        "vram_total_bytes": primary["vram_total_bytes"],
        "gpu_name": primary["name"],
        "gpu_index": primary["index"],
        "gpus": devices,
    }


def query_nvidia_smi(
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> dict[str, Any]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return parse_nvidia_smi_csv("")
    try:
        result = runner(
            [
                executable,
                "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return parse_nvidia_smi_csv("")
    if int(getattr(result, "returncode", 1) or 0) != 0:
        return parse_nvidia_smi_csv("")
    return parse_nvidia_smi_csv(getattr(result, "stdout", ""))


def collect_system_resources(
    *,
    psutil_module: object | None = None,
    gpu_query: Callable[[], dict[str, Any]] = query_nvidia_smi,
) -> dict[str, Any]:
    """Collect percentages only; never enumerate processes or user files."""

    if psutil_module is None:
        try:
            import psutil as psutil_module  # type: ignore[no-redef]
        except ImportError:
            psutil_module = None
    cpu_percent = None
    dram_percent = None
    dram_used_bytes = None
    dram_total_bytes = None
    if psutil_module is not None:
        try:
            cpu_percent = _percent(psutil_module.cpu_percent(interval=0.05))
        except Exception:
            cpu_percent = None
        try:
            memory = psutil_module.virtual_memory()
            dram_percent = _percent(memory.percent)
            dram_used_bytes = max(0, int(memory.used))
            dram_total_bytes = max(0, int(memory.total))
        except Exception:
            dram_percent = None
            dram_used_bytes = None
            dram_total_bytes = None
    gpu = gpu_query()
    return {
        "sampled_at_unix": round(time.time(), 3),
        "cpu_percent": cpu_percent,
        "dram_percent": dram_percent,
        "dram_used_bytes": dram_used_bytes,
        "dram_total_bytes": dram_total_bytes,
        **gpu,
    }


__all__ = [
    "collect_system_resources", "parse_nvidia_smi_csv", "query_nvidia_smi",
]

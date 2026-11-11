from __future__ import annotations

from typing import Any

import torch


def _directml_device() -> Any:
    try:
        import torch_directml  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "DirectML was requested, but torch-directml is not installed. "
            "Install it in the active Python environment with: pip install torch-directml"
        ) from exc
    return torch_directml.device()


def _try_directml_device() -> Any | None:
    try:
        return _directml_device()
    except Exception:
        return None


def resolve_device(device: Any = "auto") -> Any:
    """Resolve user-facing device names to values accepted by torch.Tensor.to().

    CUDA/CPU are returned as strings to preserve compatibility with libraries that
    expect those exact values. DirectML returns the torch-directml device object.
    """
    if device is None:
        device = "auto"
    if not isinstance(device, str):
        return device

    requested = device.strip()
    name = requested.lower()
    if name in {"", "auto"}:
        if torch.cuda.is_available():
            return "cuda:0"
        dml = _try_directml_device()
        return dml if dml is not None else "cpu"

    if name in {"dml", "directml"}:
        return _directml_device()

    if name == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA was requested, but this PyTorch environment cannot see CUDA. "
                "Install a CUDA-enabled torch build in the environment used to launch SoulX-Singer."
            )
        return "cuda:0"

    if name.startswith("cuda"):
        if not torch.cuda.is_available():
            raise RuntimeError(
                f"{requested} was requested, but this PyTorch environment cannot see CUDA. "
                "Install a CUDA-enabled torch build in the environment used to launch SoulX-Singer."
            )
        return requested

    if name == "cpu":
        return "cpu"

    return requested


def is_cuda_device(device: Any) -> bool:
    device_type = getattr(device, "type", None)
    return device_type == "cuda" or str(device).lower().startswith("cuda")


def is_directml_device(device: Any) -> bool:
    device_text = str(device).lower()
    device_type = getattr(device, "type", None)
    return device_type == "privateuseone" or device_text.startswith(("privateuseone", "dml", "directml"))


def empty_device_cache(device: Any) -> None:
    if is_cuda_device(device) and torch.cuda.is_available():
        torch.cuda.empty_cache()

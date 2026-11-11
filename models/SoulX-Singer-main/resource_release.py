"""Unload model weights and reclaim RAM / VRAM for the SoulX-Singer desktop GUIs.

The Gradio front-ends keep every heavy object on a module-level singleton
(``webui.APP_STATE`` for synthesis, ``webui_svc._APP_STATES`` for conversion), so
closing a Tk window only makes the window disappear: the interpreter still owns
the weights and the CUDA context, and the GPU keeps showing several GB of memory
until the process finally exits.

These helpers do the opposite, so a window-close handler (or the 「卸载模型」
button) can drop the references, force a real reclaim, and report how much was
freed:

    import resource_release as rr

    lines = rr.unload_all(modules=[webui], device=state_device, log=self._log)
    rr.force_exit()          # guarantees the CUDA context dies with the process

``force_exit`` matters: after a CUDA run, lingering worker threads (torchaudio,
funasr, Nemo, the Tk queue poller) can keep the interpreter alive, which would
leave the GPU occupied by a process that has no visible window.
"""

from __future__ import annotations

import ctypes
import gc
import os
import sys
from typing import Any, Callable, Iterable, NoReturn

__all__ = [
    "cuda_footprint",
    "process_working_set",
    "drop_state",
    "release_singletons",
    "reclaim",
    "unload_all",
    "force_exit",
]

# Module-level model registries created by the front-ends. ``APP_STATE`` is a
# single object (webui.py), ``_APP_STATES`` is a device-keyed dict (webui_svc.py).
STATE_ATTRS = ("APP_STATE", "_APP_STATES", "app_state")


def _gib(value: float) -> str:
    return f"{float(value) / 1024 ** 3:.2f} GiB"


def cuda_footprint() -> dict | None:
    """Return this process's GPU usage in bytes, or ``None`` without CUDA.

    ``free`` is the whole-device figure, so it also reflects what other programs
    hold — useful because the point of this module is to hand VRAM back.
    """
    try:
        import torch
    except Exception:
        return None
    try:
        if not torch.cuda.is_available():
            return None
        free, total = torch.cuda.mem_get_info()
        return {
            "allocated": int(torch.cuda.memory_allocated()),
            "reserved": int(torch.cuda.memory_reserved()),
            "free": int(free),
            "total": int(total),
        }
    except Exception:
        return None


def process_working_set() -> int | None:
    """Working set of this process in bytes (``None`` when it cannot be read)."""
    if os.name == "nt":
        try:
            from ctypes import wintypes

            class _PMC(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = _PMC()
            counters.cb = ctypes.sizeof(_PMC)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            if ctypes.windll.psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(counters), counters.cb
            ):
                return int(counters.WorkingSetSize)
        except Exception:
            return None
    try:
        import resource

        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    except Exception:
        return None


def _iter_states(obj: Any) -> Iterable[Any]:
    """Yield the state objects behind a registry value (object, or dict of them)."""
    if obj is None:
        return ()
    if isinstance(obj, dict):
        return [value for value in list(obj.values()) if value is not None]
    return (obj,)


def drop_state(states: Iterable[Any], *, skip: Iterable[str] = ("device", "use_fp16")) -> int:
    """None out every attribute held by the loaded state objects.

    That is what actually releases the weights: the ``AppState`` objects own the
    separation / ASR / note-transcription / synthesis models, and Python can only
    collect them once nothing references them any more. Scalar settings
    (``device``, ``use_fp16`` …) are kept so the object can still be inspected.
    """
    dropped = 0
    skip = set(skip)
    for state in states:
        for name in list(getattr(state, "__dict__", {}) or {}):
            if name in skip:
                continue
            try:
                if getattr(state, name, None) is not None:
                    dropped += 1
                setattr(state, name, None)
            except Exception:
                pass
    return dropped


def release_singletons(modules: Iterable[Any], attrs: Iterable[str] = STATE_ATTRS) -> int:
    """Clear the front-end model registries and drop the weights they hold.

    ``webui.APP_STATE`` is set to ``None`` and ``webui_svc._APP_STATES`` to ``{}``
    so a later request builds a fresh state instead of touching freed models.
    """
    dropped = 0
    for module in modules:
        if module is None:
            continue
        for attr in attrs:
            if not hasattr(module, attr):
                continue
            registry = getattr(module, attr)
            dropped += drop_state(_iter_states(registry))
            try:
                setattr(module, attr, {} if isinstance(registry, dict) else None)
            except Exception:
                pass
    return dropped


def reclaim(device: Any = None, log: Callable[[str], None] | None = None) -> dict:
    """Force a real reclaim and report the before/after numbers.

    Order matters: ``gc.collect()`` first (torch frees a CUDA block only when the
    tensor's last reference dies), then ``empty_cache()`` returns the now-empty
    caching-allocator segments to the driver, then ``ipc_collect()``.
    """
    emit = log or (lambda message: None)
    before_cuda = cuda_footprint()
    before_rss = process_working_set()

    gc.collect()
    try:
        from soulxsinger.utils.device_utils import empty_device_cache

        empty_device_cache(device)
    except Exception:
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.ipc_collect()
            torch.cuda.empty_cache()
    except Exception:
        pass
    gc.collect()

    after_cuda = cuda_footprint()
    after_rss = process_working_set()

    if before_cuda and after_cuda:
        emit(
            "显存 VRAM: reserved "
            f"{_gib(before_cuda['reserved'])} -> {_gib(after_cuda['reserved'])}, "
            f"tensors {_gib(before_cuda['allocated'])} -> {_gib(after_cuda['allocated'])}, "
            f"空闲 free {_gib(before_cuda['free'])} -> {_gib(after_cuda['free'])}"
        )
    if before_rss and after_rss:
        emit(f"进程内存 RSS: {_gib(before_rss)} -> {_gib(after_rss)}")
    elif before_rss:
        emit(f"进程内存 RSS: {_gib(before_rss)}")

    return {
        "cuda_before": before_cuda,
        "cuda_after": after_cuda,
        "rss_before": before_rss,
        "rss_after": after_rss,
    }


def unload_all(
    modules: Iterable[Any] = (),
    device: Any = None,
    log: Callable[[str], None] | None = None,
) -> dict:
    """One call for "unload everything now": drop the weights, then reclaim.

    Returns the numbers from :func:`reclaim`; progress goes to ``log``.
    """
    emit = log or (lambda message: None)
    dropped = release_singletons(modules)
    emit(f"已释放模型引用 dropped_models={dropped}")
    stats = reclaim(device=device, log=emit)
    stats["dropped"] = dropped
    return stats


def force_exit(code: int = 0) -> NoReturn:
    """Exit hard after flushing the streams.

    Used on window close: CUDA / third-party threads can outlive the Tk mainloop
    and keep a windowless process holding gigabytes, which is exactly what the
    "close the window and free the GPU" behaviour is meant to avoid.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:
            pass
    os._exit(code)

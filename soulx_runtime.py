"""Detect, install and start the optional local SoulX-Singer SVC server."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Callable
import urllib.error
import urllib.request

from ace_step_runtime import detect_gpu_vram_gb
from runtime_paths import PROJECT_ROOT


LOCAL_SOULX_SERVER = "http://127.0.0.1:7861"
REMOTE_SOULX_SERVER = "http://192.168.0.185:7861"
MINIMUM_SERVER_VRAM_GB = 16.0
SOULX_REPOSITORY = "https://github.com/Soul-AILab/SoulX-Singer.git"
SOULX_HOME = PROJECT_ROOT / "models" / "SoulX-Singer-main"
SERVER_MARKER = SOULX_HOME / ".studio_server_mode.json"
HIDDEN_LAUNCHER = PROJECT_ROOT / "run_soulx_api_hidden.ps1"
STOPPER = PROJECT_ROOT / "stop_soulx_server.ps1"
SOULX_STDOUT_LOG = PROJECT_ROOT / "logs" / "soulx_api.stdout.log"
SOULX_STDERR_LOG = PROJECT_ROOT / "logs" / "soulx_api.stderr.log"
SVC_CHECKPOINT = SOULX_HOME / "pretrained_models" / "SoulX-Singer" / "model-svc.pt"
PREPROCESS_HOME = SOULX_HOME / "pretrained_models" / "SoulX-Singer-Preprocess"
_LOCAL_START_REQUESTED_AT = 0.0


@dataclass(frozen=True, slots=True)
class SoulXRuntimeState:
    mode: str
    api_url: str
    installed: bool
    gpu_vram_gb: float
    install_eligible: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _runtime_python_candidates(soulx_home: Path = SOULX_HOME) -> tuple[Path, ...]:
    computer_name = os.environ.get("COMPUTERNAME", "local").strip() or "local"
    return (
        soulx_home / ".runtime" / computer_name / ".venv" / "Scripts" / "python.exe",
        soulx_home / ".venv" / "Scripts" / "python.exe",
    )


def _preprocess_models_present(path: Path = PREPROCESS_HOME) -> bool:
    if not path.is_dir():
        return False
    try:
        return any(item.is_file() for item in path.rglob("*"))
    except OSError:
        return False


def _has_local_server_installation(soulx_home: Path = SOULX_HOME) -> bool:
    """Require source, a local runtime, SVC weights and preprocessing weights."""

    source_ready = (soulx_home / "webui_svc.py").is_file()
    runtime_ready = any(path.is_file() for path in _runtime_python_candidates(soulx_home))
    checkpoint = soulx_home / "pretrained_models" / "SoulX-Singer" / "model-svc.pt"
    preprocess = soulx_home / "pretrained_models" / "SoulX-Singer-Preprocess"
    return source_ready and runtime_ready and checkpoint.is_file() and _preprocess_models_present(preprocess)


def detect_soulx_runtime(
    soulx_home: Path = SOULX_HOME,
    *,
    gpu_vram_gb: float | None = None,
) -> SoulXRuntimeState:
    """Classify this computer without downloading or installing anything."""

    vram = detect_gpu_vram_gb() if gpu_vram_gb is None else max(0.0, float(gpu_vram_gb))
    if _has_local_server_installation(soulx_home):
        return SoulXRuntimeState(
            mode="server",
            api_url=LOCAL_SOULX_SERVER,
            installed=True,
            gpu_vram_gb=vram,
            install_eligible=True,
            detail="Local SoulX runtime, SVC checkpoint and preprocessing models detected",
        )
    eligible = vram > MINIMUM_SERVER_VRAM_GB
    detail = (
        f"Client mode · local installation available ({vram:.1f} GB VRAM)"
        if eligible
        else f"Client mode · installation requires more than {MINIMUM_SERVER_VRAM_GB:.0f} GB VRAM"
    )
    return SoulXRuntimeState(
        mode="client",
        api_url=REMOTE_SOULX_SERVER,
        installed=False,
        gpu_vram_gb=vram,
        install_eligible=eligible,
        detail=detail,
    )


def _local_health_ready(timeout: float = 2.0) -> bool:
    request = urllib.request.Request(LOCAL_SOULX_SERVER + "/gradio_api/info", method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=max(0.2, timeout)) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
            status = int(response.status)
        return 200 <= status < 300 and _stable_api_ready(payload)
    except (OSError, ValueError, urllib.error.URLError):
        return False


def _stable_api_ready(payload: dict[str, object]) -> bool:
    """Accept only the Studio-owned API, never an old upstream wrapper.

    Older SoulX processes may still answer ``/gradio_api/info`` while exposing
    the broken 12-component/10-parameter ``/lazy_start_svc`` callback. Treating
    that response as healthy prevents the hidden launcher from replacing the
    stale process, so local Server Mode must require the stable endpoint.
    """

    from soulx_client import SVC_API_NAME, discover_svc_endpoint

    endpoint, parameters = discover_svc_endpoint(payload)
    return endpoint.casefold() == SVC_API_NAME.casefold() and bool(parameters)


def start_local_soulx_server_if_installed(
    state: SoulXRuntimeState | None = None,
) -> bool:
    """Start local SoulX invisibly only after a complete installation is detected."""

    global _LOCAL_START_REQUESTED_AT

    runtime = state or detect_soulx_runtime()
    if runtime.mode != "server" or not runtime.installed:
        return False
    if _local_health_ready():
        _LOCAL_START_REQUESTED_AT = 0.0
        return True
    if _LOCAL_START_REQUESTED_AT and time.monotonic() - _LOCAL_START_REQUESTED_AT < 120.0:
        return True
    if not HIDDEN_LAUNCHER.is_file():
        return False
    powershell = (
        Path(os.environ.get("SystemRoot", r"C:\Windows"))
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    _LOCAL_START_REQUESTED_AT = time.monotonic()
    try:
        subprocess.Popen(
            [
                str(powershell),
                "-NoProfile",
                "-WindowStyle",
                "Hidden",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(HIDDEN_LAUNCHER),
            ],
            cwd=str(PROJECT_ROOT),
            creationflags=creation_flags,
        )
    except Exception:
        _LOCAL_START_REQUESTED_AT = 0.0
        raise
    return True


def stop_local_soulx_server(*, timeout: float = 30.0) -> bool:
    """Stop only this project's local SoulX process tree and release port 7861."""

    global _LOCAL_START_REQUESTED_AT

    if not STOPPER.is_file():
        raise RuntimeError(f"SoulX process controller is missing: {STOPPER}")
    powershell = (
        Path(os.environ.get("SystemRoot", r"C:\Windows"))
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(
        [
            str(powershell),
            "-NoProfile",
            "-WindowStyle",
            "Hidden",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(STOPPER),
            "-ProjectRoot",
            str(PROJECT_ROOT),
            "-Port",
            "7861",
            "-WaitSeconds",
            "20",
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=max(5.0, float(timeout)),
        creationflags=creation_flags,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown stop failure").strip()
        raise RuntimeError(f"SoulX local server stop failed: {detail}")
    _LOCAL_START_REQUESTED_AT = 0.0
    return True


def read_soulx_startup_progress() -> str:
    """Return the newest useful hidden-launcher phase for the dialog status line."""

    chunks: list[str] = []
    for path in (SOULX_STDOUT_LOG, SOULX_STDERR_LOG):
        try:
            if path.is_file():
                chunks.append(path.read_text(encoding="utf-8", errors="replace")[-65536:])
        except OSError:
            pass
    text = "\n".join(chunks)
    phases = (
        ("Installing PyTorch", "SoulX Server · updating GPU runtime (PyTorch CUDA)…"),
        ("Building the isolated Python", "SoulX Server · preparing isolated Python runtime…"),
        ("Downloading official SVC", "SoulX Server · downloading required models…"),
        ("capability sm_", "SoulX Server · CUDA architecture validated…"),
        ("[SoulX] Models:", "SoulX Server · loading API and binding model paths…"),
        ("Running on local URL", "SoulX Server · API process online, validating contract…"),
        ("models unloaded", "SoulX Server · idle model state released, validating API…"),
    )
    latest_position = -1
    latest_message = "SoulX Server · waiting for local API startup…"
    for marker, message in phases:
        position = text.rfind(marker)
        if position > latest_position:
            latest_position = position
            latest_message = message
    return latest_message


def install_local_soulx_server(
    progress: Callable[[str], None] | None = None,
    *,
    timeout: float = 7200.0,
) -> SoulXRuntimeState:
    """Install SoulX only after an explicit, strictly >16GB VRAM-gated action."""

    vram = detect_gpu_vram_gb()
    if vram <= MINIMUM_SERVER_VRAM_GB:
        raise RuntimeError(
            f"Local SoulX installation requires more than {MINIMUM_SERVER_VRAM_GB:.0f} GB "
            f"VRAM; detected {vram:.1f} GB. This computer remains in Client Mode."
        )
    if not HIDDEN_LAUNCHER.is_file():
        raise RuntimeError(f"SoulX hidden launcher is missing: {HIDDEN_LAUNCHER}")

    if progress:
        progress(f"Installing local SoulX · GPU VRAM {vram:.1f} GB…")
    if not (SOULX_HOME / "webui_svc.py").is_file():
        if SOULX_HOME.exists() and any(SOULX_HOME.iterdir()):
            raise RuntimeError(
                f"SoulX source directory is incomplete and not empty: {SOULX_HOME}. "
                "Repair or move that folder before installing."
            )
        if progress:
            progress("Downloading SoulX-Singer source from the official GitHub repository…")
        SOULX_HOME.parent.mkdir(parents=True, exist_ok=True)
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["git", "clone", "--depth", "1", SOULX_REPOSITORY, str(SOULX_HOME)],
            check=True,
            capture_output=True,
            text=True,
            timeout=900,
            creationflags=creation_flags,
        )

    provisional = SoulXRuntimeState(
        mode="server",
        api_url=LOCAL_SOULX_SERVER,
        installed=True,
        gpu_vram_gb=vram,
        install_eligible=True,
        detail="Local installation in progress",
    )
    start_local_soulx_server_if_installed(provisional)
    deadline = time.monotonic() + max(60.0, timeout)
    while time.monotonic() < deadline:
        if progress:
            progress("SoulX setup/model loading in progress · waiting for local API…")
        if _local_health_ready(timeout=3.0):
            SERVER_MARKER.write_text(
                json.dumps(
                    {
                        "mode": "server",
                        "installed_at": datetime.now(timezone.utc).isoformat(),
                        "gpu_vram_gb": round(vram, 2),
                        "api_url": LOCAL_SOULX_SERVER,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            return SoulXRuntimeState(
                mode="server",
                api_url=LOCAL_SOULX_SERVER,
                installed=True,
                gpu_vram_gb=vram,
                install_eligible=True,
                detail="Local SoulX server installed and running",
            )
        time.sleep(3.0)
    raise TimeoutError(
        "Local SoulX installation did not become ready within the timeout. "
        f"Review {PROJECT_ROOT / 'logs' / 'soulx_api.stderr.log'}."
    )

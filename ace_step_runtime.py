"""Detect and manage the optional local ACE-Step 1.5 server runtime."""

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

from runtime_paths import PROJECT_ROOT


LOCAL_ACE_SERVER = "http://127.0.0.1:8001"
REMOTE_ACE_SERVER = "http://192.168.0.185:8001"
MINIMUM_SERVER_VRAM_GB = 16.0
ACE_STEP_REPOSITORY = "https://github.com/ace-step/ACE-Step.git"
ACE_HOME = PROJECT_ROOT / "models" / "ACE-Step-1.5"
SERVER_MARKER = ACE_HOME / ".studio_server_mode.json"
HIDDEN_LAUNCHER = PROJECT_ROOT / "run_ace_step_api_hidden.ps1"


@dataclass(frozen=True, slots=True)
class AceStepRuntimeState:
    mode: str
    api_url: str
    installed: bool
    gpu_vram_gb: float
    install_eligible: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _runtime_python_candidates(ace_home: Path) -> tuple[Path, ...]:
    computer_name = os.environ.get("COMPUTERNAME", "local").strip() or "local"
    return (
        ace_home / ".runtime" / computer_name / ".venv" / "Scripts" / "python.exe",
        ace_home / ".venv" / "Scripts" / "python.exe",
    )


def _has_local_server_installation(ace_home: Path = ACE_HOME) -> bool:
    """Require both a runnable environment and the primary model checkpoint."""

    runtime_ready = any(path.is_file() for path in _runtime_python_candidates(ace_home))
    checkpoint = ace_home / "checkpoints" / "acestep-v15-turbo" / "config.json"
    install_marker = ace_home / ".studio_server_mode.json"
    return runtime_ready and (checkpoint.is_file() or install_marker.is_file())


def _parse_vram_output(output: str) -> float:
    values: list[float] = []
    for raw_line in str(output or "").splitlines():
        token = raw_line.strip().split()[0].replace(",", "") if raw_line.strip() else ""
        try:
            values.append(float(token) / 1024.0)
        except ValueError:
            continue
    return max(values, default=0.0)


def detect_gpu_vram_gb() -> float:
    """Return the largest NVIDIA GPU VRAM capacity reported by nvidia-smi."""

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=creation_flags,
        )
    except (OSError, subprocess.SubprocessError):
        return 0.0
    return _parse_vram_output(completed.stdout)


def detect_ace_step_runtime(ace_home: Path = ACE_HOME) -> AceStepRuntimeState:
    """Classify this computer without installing or downloading anything."""

    if _has_local_server_installation(ace_home):
        return AceStepRuntimeState(
            mode="server",
            api_url=LOCAL_ACE_SERVER,
            installed=True,
            gpu_vram_gb=detect_gpu_vram_gb(),
            install_eligible=True,
            detail="Local ACE-Step runtime and Turbo checkpoint detected",
        )
    vram = detect_gpu_vram_gb()
    eligible = vram > MINIMUM_SERVER_VRAM_GB
    detail = (
        f"Client mode · local installation available ({vram:.1f} GB VRAM)"
        if eligible
        else f"Client mode · installation requires more than {MINIMUM_SERVER_VRAM_GB:.0f} GB VRAM"
    )
    return AceStepRuntimeState(
        mode="client",
        api_url=REMOTE_ACE_SERVER,
        installed=False,
        gpu_vram_gb=vram,
        install_eligible=eligible,
        detail=detail,
    )


def _local_health_ready(timeout: float = 2.0) -> bool:
    request = urllib.request.Request(LOCAL_ACE_SERVER + "/health", method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=max(0.2, timeout)) as response:
            return 200 <= int(response.status) < 300
    except (OSError, urllib.error.URLError):
        return False


def start_local_server_if_installed(
    state: AceStepRuntimeState | None = None,
) -> bool:
    """Start the local server invisibly only when installation is complete."""

    runtime = state or detect_ace_step_runtime()
    if runtime.mode != "server" or not runtime.installed:
        return False
    if _local_health_ready():
        return True
    if not HIDDEN_LAUNCHER.is_file():
        return False
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
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
    return True


def install_local_server(
    progress: Callable[[str], None] | None = None,
    *,
    timeout: float = 3600.0,
) -> AceStepRuntimeState:
    """Install/start local ACE-Step after an explicit, VRAM-gated user action."""

    vram = detect_gpu_vram_gb()
    if vram <= MINIMUM_SERVER_VRAM_GB:
        raise RuntimeError(
            f"Local ACE-Step installation requires more than {MINIMUM_SERVER_VRAM_GB:.0f} GB "
            f"VRAM; detected {vram:.1f} GB. This computer remains in Client Mode."
        )
    if not HIDDEN_LAUNCHER.is_file():
        raise RuntimeError(f"ACE-Step hidden launcher is missing: {HIDDEN_LAUNCHER}")

    if progress:
        progress(f"Installing local ACE-Step · GPU VRAM {vram:.1f} GB…")
    if not (ACE_HOME / "pyproject.toml").is_file():
        if ACE_HOME.exists() and any(ACE_HOME.iterdir()):
            raise RuntimeError(
                f"ACE-Step source directory is incomplete and not empty: {ACE_HOME}. "
                "Move or repair that folder before installing."
            )
        if progress:
            progress("Downloading ACE-Step 1.5 source from the official GitHub repository…")
        ACE_HOME.parent.mkdir(parents=True, exist_ok=True)
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["git", "clone", "--depth", "1", ACE_STEP_REPOSITORY, str(ACE_HOME)],
            check=True,
            capture_output=True,
            text=True,
            timeout=900,
            creationflags=creation_flags,
        )
    provisional = AceStepRuntimeState(
        mode="server",
        api_url=LOCAL_ACE_SERVER,
        installed=True,
        gpu_vram_gb=vram,
        install_eligible=True,
        detail="Local installation in progress",
    )
    start_local_server_if_installed(provisional)

    deadline = time.monotonic() + max(30.0, timeout)
    while time.monotonic() < deadline:
        if _local_health_ready(timeout=2.0):
            SERVER_MARKER.write_text(
                json.dumps(
                    {
                        "mode": "server",
                        "installed_at": datetime.now(timezone.utc).isoformat(),
                        "gpu_vram_gb": round(vram, 2),
                        "api_url": LOCAL_ACE_SERVER,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            return AceStepRuntimeState(
                mode="server",
                api_url=LOCAL_ACE_SERVER,
                installed=True,
                gpu_vram_gb=vram,
                install_eligible=True,
                detail="Local ACE-Step server installed and running",
            )
        time.sleep(2.0)
    raise TimeoutError(
        "Local ACE-Step installation did not become ready within the timeout. "
        f"Review {PROJECT_ROOT / 'logs' / 'ace_step_api.stderr.log'}."
    )

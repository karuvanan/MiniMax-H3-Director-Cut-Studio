"""Automatic Client/Server selection for the Kim_Vocal_2 separator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

from ace_step_runtime import detect_gpu_vram_gb
from runtime_paths import PROJECT_ROOT
from vocal_separator_engine import validate_separator_installation


LOCAL_AUDIO_SEPARATOR_SERVER = "http://127.0.0.1:7862"
REMOTE_AUDIO_SEPARATOR_SERVER = os.getenv(
    "AUDIO_SEPARATOR_API_URL", "http://192.168.0.185:7862"
)
HIDDEN_LAUNCHER = PROJECT_ROOT / "run_audio_separator_api_hidden.ps1"
STOPPER = PROJECT_ROOT / "stop_audio_separator_server.ps1"
STDOUT_LOG = PROJECT_ROOT / "logs" / "audio_separator_api.stdout.log"
STDERR_LOG = PROJECT_ROOT / "logs" / "audio_separator_api.stderr.log"
_LOCAL_START_REQUESTED_AT = 0.0


@dataclass(frozen=True, slots=True)
class AudioSeparatorRuntimeState:
    mode: str
    api_url: str
    installed: bool
    gpu_vram_gb: float
    detail: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _has_local_server_installation(project_root: Path = PROJECT_ROOT) -> bool:
    return not validate_separator_installation(project_root)


def detect_audio_separator_runtime(
    project_root: Path = PROJECT_ROOT,
    *,
    gpu_vram_gb: float | None = None,
) -> AudioSeparatorRuntimeState:
    """Choose local Server Mode only when Kim and its runtime are present."""

    vram = detect_gpu_vram_gb() if gpu_vram_gb is None else max(0.0, float(gpu_vram_gb))
    local_installation = _has_local_server_installation(project_root)
    if local_installation and vram > 0.0:
        return AudioSeparatorRuntimeState(
            mode="server",
            api_url=LOCAL_AUDIO_SEPARATOR_SERVER,
            installed=True,
            gpu_vram_gb=vram,
            detail="Local Kim_Vocal_2 model and isolated separator runtime detected",
        )
    detail = (
        "Local Kim files were found but no CUDA GPU was detected; using the remote CUDA server"
        if local_installation
        else "No local Kim_Vocal_2 installation; using the remote CUDA server"
    )
    return AudioSeparatorRuntimeState(
        mode="client",
        api_url=REMOTE_AUDIO_SEPARATOR_SERVER,
        installed=False,
        gpu_vram_gb=vram,
        detail=detail,
    )


def _local_health_ready(timeout: float = 2.0) -> bool:
    request = urllib.request.Request(LOCAL_AUDIO_SEPARATOR_SERVER + "/health", method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=max(0.2, timeout)) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
            status = int(response.status)
        return (
            200 <= status < 300
            and bool(payload.get("ready"))
            and bool(payload.get("cuda_provider"))
            and payload.get("provider") == "CUDAExecutionProvider"
        )
    except (OSError, ValueError, urllib.error.URLError):
        return False


def start_local_audio_separator_server_if_installed(
    state: AudioSeparatorRuntimeState | None = None,
) -> bool:
    """Start the local CUDA API invisibly when this computer is a Server."""

    global _LOCAL_START_REQUESTED_AT
    runtime = state or detect_audio_separator_runtime()
    if runtime.mode != "server" or not runtime.installed:
        return False
    if _local_health_ready():
        _LOCAL_START_REQUESTED_AT = 0.0
        return True
    if _LOCAL_START_REQUESTED_AT and time.monotonic() - _LOCAL_START_REQUESTED_AT < 180.0:
        return True
    if not HIDDEN_LAUNCHER.is_file():
        return False
    powershell = (
        Path(os.environ.get("SystemRoot", r"C:\Windows"))
        / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    )
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    _LOCAL_START_REQUESTED_AT = time.monotonic()
    try:
        subprocess.Popen(
            [
                str(powershell), "-NoProfile", "-WindowStyle", "Hidden",
                "-ExecutionPolicy", "Bypass", "-File", str(HIDDEN_LAUNCHER),
            ],
            cwd=str(PROJECT_ROOT),
            creationflags=creation_flags,
        )
    except Exception:
        _LOCAL_START_REQUESTED_AT = 0.0
        raise
    return True


def stop_local_audio_separator_server(*, timeout: float = 30.0) -> bool:
    """Stop only this Project's local API and disposable Kim worker."""

    global _LOCAL_START_REQUESTED_AT
    if not STOPPER.is_file():
        raise RuntimeError(f"Audio Separator process controller is missing: {STOPPER}")
    powershell = (
        Path(os.environ.get("SystemRoot", r"C:\Windows"))
        / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    )
    completed = subprocess.run(
        [
            str(powershell), "-NoProfile", "-WindowStyle", "Hidden",
            "-ExecutionPolicy", "Bypass", "-File", str(STOPPER),
            "-ProjectRoot", str(PROJECT_ROOT), "-Port", "7862", "-WaitSeconds", "20",
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=max(5.0, float(timeout)),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown stop failure").strip()
        raise RuntimeError(f"Audio Separator local server stop failed: {detail}")
    _LOCAL_START_REQUESTED_AT = 0.0
    return True


def read_audio_separator_startup_progress() -> str:
    """Return the latest useful hidden-start phase for the dialog footer."""

    chunks: list[str] = []
    for path in (STDOUT_LOG, STDERR_LOG):
        try:
            if path.is_file():
                chunks.append(path.read_text(encoding="utf-8", errors="replace")[-65536:])
        except OSError:
            pass
    text = "\n".join(chunks)
    phases = (
        ("Installing CUDA runtime", "Audio Separator Server · installing ONNX Runtime CUDA…"),
        ("Validating CUDAExecutionProvider", "Audio Separator Server · validating GPU provider and Kim model…"),
        ("CUDA ready", "Audio Separator Server · CUDA validated, starting API…"),
        ("Uvicorn running", "Audio Separator Server · API online, validating health…"),
        ("Application startup complete", "Audio Separator Server · API online, validating CUDA health…"),
    )
    latest_position = -1
    latest_message = "Audio Separator Server · waiting for local CUDA API startup…"
    for marker, message in phases:
        position = text.rfind(marker)
        if position > latest_position:
            latest_position = position
            latest_message = message
    return latest_message

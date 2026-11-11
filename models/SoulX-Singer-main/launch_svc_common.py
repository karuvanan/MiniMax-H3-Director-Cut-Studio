from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from tkinter import messagebox


ROOT = Path(__file__).resolve().parent
ENV_NAME = "soulxsinger"
DEFAULT_WEBUI_ARGS = ["--device", "cuda", "--fp16"]
WEBUI_PORT = 7861


def _candidate_env_roots() -> list[Path]:
    home = Path.home()
    roots = [
        ROOT / ".venv",
        home / "anaconda3" / "envs" / ENV_NAME,
        home / "miniconda3" / "envs" / ENV_NAME,
        home / "mambaforge" / "envs" / ENV_NAME,
        home / ".conda" / "envs" / ENV_NAME,
    ]
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        roots.insert(0, Path(conda_prefix))
    # A Studio-managed install keeps its own interpreter under
    # .runtime/<computer name>/.venv; that curated environment must win over a
    # stray conda env so the GUI runs on the same torch build as the SOULX API.
    installed = []
    runtime_root = ROOT / ".runtime"
    if runtime_root.is_dir():
        installed = [
            machine / ".venv"
            for machine in sorted(runtime_root.iterdir())
            if (machine / ".venv").is_dir()
        ]
    roots = installed + roots
    return roots


def find_env_python(prefer_windowed: bool) -> Path:
    exe_names = ["pythonw.exe", "python.exe"] if prefer_windowed else ["python.exe", "pythonw.exe"]
    for env_root in _candidate_env_roots():
        # A venv keeps its interpreters in Scripts/, a conda env at the root.
        for exe_dir in (env_root, env_root / "Scripts"):
            for exe_name in exe_names:
                candidate = exe_dir / exe_name
                if candidate.exists():
                    return candidate

    messagebox.showerror(
        "SoulX-Singer launcher",
        "Cannot find the soulxsinger Python environment.\n\n"
        "Expected one of:\n"
        "- <this folder>\\.runtime\\<computer name>\\.venv\\Scripts\\python.exe\n"
        "- %USERPROFILE%\\anaconda3\\envs\\soulxsinger\\python.exe\n"
        "- %USERPROFILE%\\miniconda3\\envs\\soulxsinger\\python.exe\n\n"
        "Create it first with:\n"
        "conda create -n soulxsinger -y python=3.10\n"
        "conda activate soulxsinger\n"
        "pip install -r requirements-cuda.txt",
    )
    raise SystemExit(1)


def ensure_script(script_name: str) -> Path:
    script = ROOT / script_name
    if not script.exists():
        messagebox.showerror("SoulX-Singer launcher", f"Missing script:\n{script}")
        raise SystemExit(1)
    return script


def _log_path(name: str) -> Path:
    log_dir = ROOT / "outputs" / "launcher_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / name


def launch_gui() -> None:
    python = find_env_python(prefer_windowed=True)
    script = ensure_script("gui_svc.py")
    log_path = _log_path("gui_svc.log")
    with open(log_path, "a", encoding="utf-8") as log:
        subprocess.Popen(
            [str(python), str(script)],
            cwd=str(ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


def launch_gui_svs() -> None:
    """Launch the desktop lyrics/MIDI synthesis GUI (gui.py)."""
    python = find_env_python(prefer_windowed=True)
    script = ensure_script("gui.py")
    log_path = _log_path("gui.log")
    with open(log_path, "a", encoding="utf-8") as log:
        subprocess.Popen(
            [str(python), "-u", str(script)],
            cwd=str(ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


def _wait_for_port(port: int, timeout_sec: int = 60) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(1)
    return False


def launch_webui() -> None:
    python = find_env_python(prefer_windowed=True)
    script = ensure_script("webui_svc.py")
    log_path = _log_path("webui_svc.log")
    args = [str(python), str(script), "--port", str(WEBUI_PORT), *DEFAULT_WEBUI_ARGS]
    with open(log_path, "a", encoding="utf-8") as log:
        subprocess.Popen(
            args,
            cwd=str(ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    url = f"http://127.0.0.1:{WEBUI_PORT}"
    if _wait_for_port(WEBUI_PORT, timeout_sec=90):
        webbrowser.open(url)
    else:
        messagebox.showwarning(
            "SoulX-Singer WebUI",
            "WebUI is taking longer than expected to start.\n\n"
            f"Try opening {url}\n\n"
            f"Log file:\n{log_path}",
        )


def main(kind: str) -> None:
    if kind == "gui":
        launch_gui()
    elif kind == "gui_svs":
        launch_gui_svs()
    elif kind == "webui":
        launch_webui()
    else:
        messagebox.showerror("SoulX-Singer launcher", f"Unknown launcher kind: {kind}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "gui")

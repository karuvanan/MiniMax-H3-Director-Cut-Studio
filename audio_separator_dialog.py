"""Explicit client/server Audio Separator workbench for Director Cut Studio."""

from __future__ import annotations

from pathlib import Path
import shutil
import threading
import time

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from audio_separator_client import (
    DEFAULT_AUDIO_SEPARATOR_SERVER,
    download_separator_file,
    fetch_separator_health,
    separate_audio,
)
from audio_separator_runtime import (
    AudioSeparatorRuntimeState,
    LOCAL_AUDIO_SEPARATOR_SERVER,
    REMOTE_AUDIO_SEPARATOR_SERVER,
    detect_audio_separator_runtime,
    read_audio_separator_startup_progress,
    start_local_audio_separator_server_if_installed,
    stop_local_audio_separator_server,
)
from runtime_paths import PROJECT_ROOT


AUDIO_FILTER = "Audio (*.mp3 *.wav *.flac *.m4a *.aac *.ogg);;All files (*)"


class AudioSeparatorDialog(QDialog):
    """Separate a song deliberately, preview/save stems, then bind A1/A2."""

    task_succeeded = Signal(str, object)
    task_failed = Signal(str, str)
    add_requested = Signal(str, str, str)
    readiness_checked = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        server_url: str = "",
        runtime_state: AudioSeparatorRuntimeState | None = None,
    ) -> None:
        super().__init__(parent)
        self._busy = False
        self._closed = False
        self._close_release_completed = False
        self._api_ready = False
        self._readiness_probe_running = False
        self._readiness_started = time.monotonic()
        self._threads: set[threading.Thread] = set()
        self.result_paths: dict[str, Path] = {}
        if runtime_state is not None:
            self.runtime_state = runtime_state
        elif server_url:
            self.runtime_state = AudioSeparatorRuntimeState(
                mode="client",
                api_url=server_url,
                installed=False,
                gpu_vram_gb=0.0,
                detail="Explicit API address",
            )
        else:
            self.runtime_state = detect_audio_separator_runtime()
        self.setWindowTitle("AUDIO SEPARATOR · Vocal / Music / Mix")
        self.resize(840, 520)
        self.setMinimumSize(720, 460)

        layout = QVBoxLayout(self)
        explanation = QLabel(
            "Explicit preprocessing only. Kim_Vocal_2 separates one source into Vocal and Music; "
            "Mix preserves the untouched uploaded master. Nothing is sent to H3 until you click "
            "ADD TO A1 & A2."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color:#cdd7e6; font-weight:600;")
        layout.addWidget(explanation)

        server_box = QGroupBox("AUDIO SEPARATOR SERVER")
        server_layout = QGridLayout(server_box)
        self.server_edit = QLineEdit(
            self.runtime_state.api_url or server_url or DEFAULT_AUDIO_SEPARATOR_SERVER
        )
        self.server_edit.setObjectName("audioSeparatorApiEdit")
        self.test_button = QPushButton("TEST")
        self.test_button.clicked.connect(self.test_connection)
        server_layout.addWidget(QLabel("API"), 0, 0)
        server_layout.addWidget(self.server_edit, 0, 1)
        server_layout.addWidget(self.test_button, 0, 2)
        self.runtime_mode_label = QLabel()
        self.runtime_mode_label.setWordWrap(True)
        server_layout.addWidget(self.runtime_mode_label, 1, 0, 1, 3)
        layout.addWidget(server_box)

        input_box = QGroupBox("SOURCE MIX")
        input_layout = QGridLayout(input_box)
        self.source_edit = QLineEdit()
        self.source_edit.setReadOnly(True)
        self.source_edit.setPlaceholderText("Select the original full song or soundtrack")
        select_button = QPushButton("SELECT AUDIO")
        select_button.clicked.connect(self.select_source)
        input_layout.addWidget(QLabel("Source"), 0, 0)
        input_layout.addWidget(self.source_edit, 0, 1)
        input_layout.addWidget(select_button, 0, 2)
        layout.addWidget(input_box)

        action_row = QHBoxLayout()
        self.separate_button = QPushButton("SEPARATE AUDIO")
        self.separate_button.setEnabled(False)
        self.separate_button.setStyleSheet("background:#13758a; font-weight:700;")
        self.separate_button.clicked.connect(self.start_separation)
        action_row.addWidget(self.separate_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        results = QGroupBox("RESULTS")
        results_layout = QGridLayout(results)
        self.result_edits: dict[str, QLineEdit] = {}
        self.play_buttons: dict[str, QPushButton] = {}
        self.stop_buttons: dict[str, QPushButton] = {}
        self.download_buttons: dict[str, QPushButton] = {}
        labels = {"vocal": "Vocal", "music": "Music", "mix": "Mix"}
        for row, kind in enumerate(("vocal", "music", "mix")):
            edit = QLineEdit()
            edit.setReadOnly(True)
            edit.setPlaceholderText(f"{labels[kind]} result will appear here")
            play_button = QPushButton("PLAY")
            stop_button = QPushButton("STOP")
            download_button = QPushButton(f"DOWNLOAD {labels[kind].upper()}")
            for button in (play_button, stop_button, download_button):
                button.setEnabled(False)
            play_button.clicked.connect(
                lambda _checked=False, value=kind: self.play_result(value)
            )
            stop_button.clicked.connect(self.stop_playback)
            download_button.clicked.connect(
                lambda _checked=False, value=kind: self.download_result(value)
            )
            self.result_edits[kind] = edit
            self.play_buttons[kind] = play_button
            self.stop_buttons[kind] = stop_button
            self.download_buttons[kind] = download_button
            results_layout.addWidget(QLabel(labels[kind]), row, 0)
            results_layout.addWidget(edit, row, 1)
            results_layout.addWidget(play_button, row, 2)
            results_layout.addWidget(stop_button, row, 3)
            results_layout.addWidget(download_button, row, 4)
        layout.addWidget(results)

        bind_row = QHBoxLayout()
        self.add_button = QPushButton("ADD TO A1 & A2")
        self.add_button.setEnabled(False)
        self.add_button.setStyleSheet("background:#6e46a8; font-weight:700;")
        self.add_button.setToolTip(
            "Music → A1, Vocal → A2. Mix is retained by the Project as the exact final MTV master."
        )
        self.add_button.clicked.connect(self.add_to_media_pool)
        bind_row.addStretch(1)
        bind_row.addWidget(self.add_button)
        layout.addLayout(bind_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        layout.addWidget(self.progress)
        self.status_label = QLabel("Detecting Audio Separator Client / Server mode…")
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        self.task_succeeded.connect(self._handle_success)
        self.task_failed.connect(self._handle_failure)
        self.readiness_checked.connect(self._handle_readiness_result)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.9)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.readiness_timer = QTimer(self)
        self.readiness_timer.setInterval(900)
        self.readiness_timer.timeout.connect(self._probe_server_readiness)
        self.server_edit.editingFinished.connect(self._server_address_changed)
        self._update_runtime_label()
        self._start_readiness_monitor()

    def server_url(self) -> str:
        return self.server_edit.text().strip().rstrip("/")

    def select_source(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Select source mix", "", AUDIO_FILTER)
        if filename:
            self.source_edit.setText(filename)

    def _update_runtime_label(self) -> None:
        state = self.runtime_state
        if state.mode == "server":
            self.server_edit.setReadOnly(True)
            self.runtime_mode_label.setText(
                f"SERVER MODE · Local Kim_Vocal_2 CUDA · {state.gpu_vram_gb:.1f} GB VRAM · "
                f"{LOCAL_AUDIO_SEPARATOR_SERVER}"
            )
            self.runtime_mode_label.setStyleSheet("color:#55d69e; font-weight:700;")
        else:
            self.server_edit.setReadOnly(False)
            self.runtime_mode_label.setText(
                f"CLIENT MODE · Remote Kim_Vocal_2 CUDA API · {self.server_url()} · {state.detail}"
            )
            self.runtime_mode_label.setStyleSheet("color:#6ddce8; font-weight:700;")

    def _server_address_changed(self) -> None:
        if self._busy or self.runtime_state.mode == "server":
            return
        self._start_readiness_monitor()

    def _start_readiness_monitor(self) -> None:
        self._api_ready = False
        self._readiness_started = time.monotonic()
        self.separate_button.setEnabled(False)
        if self.runtime_state.mode == "server":
            try:
                start_local_audio_separator_server_if_installed(self.runtime_state)
                self.status_label.setText(
                    "Audio Separator Server · starting locally and validating CUDAExecutionProvider…"
                )
            except Exception as exc:
                self.status_label.setText(f"Audio Separator Server start failed · {exc}")
        else:
            self.status_label.setText(
                f"Audio Separator Client · connecting remote CUDA API · {self.server_url()}"
            )
        self.readiness_timer.start()
        QTimer.singleShot(0, self._probe_server_readiness)

    def _probe_server_readiness(self) -> None:
        if self._closed or self._api_ready or self._readiness_probe_running:
            return
        self._readiness_probe_running = True
        server = self.server_url()
        mode = self.runtime_state.mode
        elapsed = max(0, int(time.monotonic() - self._readiness_started))

        def run() -> None:
            try:
                health = fetch_separator_health(server, timeout=1.5)
                ready = (
                    bool(health.get("ready"))
                    and bool(health.get("cuda_provider"))
                    and health.get("provider") == "CUDAExecutionProvider"
                )
                if not ready:
                    raise RuntimeError(
                        str(health.get("error") or "server has not activated CUDAExecutionProvider")
                    )
                result = {
                    "ready": True,
                    "message": (
                        f"Audio Separator API ready · CUDAExecutionProvider · "
                        f"{health.get('gpu', 'GPU')} · {server}"
                    ),
                }
            except Exception as exc:
                progress = (
                    read_audio_separator_startup_progress()
                    if mode == "server"
                    else f"Audio Separator Client · waiting for remote CUDA API · {server}"
                )
                result = {
                    "ready": False,
                    "message": f"{progress} · {elapsed}s",
                    "error": str(exc),
                }
            self.readiness_checked.emit(result)

        thread = threading.Thread(target=run, name="audio-separator-readiness", daemon=True)
        self._threads.add(thread)
        thread.start()

    def _handle_readiness_result(self, result: object) -> None:
        self._readiness_probe_running = False
        self._threads = {item for item in self._threads if item.is_alive()}
        if self._closed:
            return
        data = result if isinstance(result, dict) else {}
        self.status_label.setText(str(data.get("message") or "Audio Separator API status unknown"))
        if not data.get("ready"):
            return
        self._api_ready = True
        self.readiness_timer.stop()
        self.separate_button.setEnabled(not self._busy)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._busy = bool(busy)
        self.test_button.setEnabled(not busy)
        self.separate_button.setEnabled(not busy and self._api_ready)
        self.add_button.setEnabled(not busy and len(self.result_paths) == 3)
        if busy:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(100 if self.result_paths else 0)
        if message:
            self.status_label.setText(message)

    def _launch(self, kind: str, function, message: str) -> None:
        if self._busy:
            return
        self._set_busy(True, message)

        def run() -> None:
            thread = threading.current_thread()
            try:
                self.task_succeeded.emit(kind, function())
            except Exception as exc:
                self.task_failed.emit(kind, str(exc))
            finally:
                self._threads.discard(thread)

        thread = threading.Thread(target=run, name=f"audio-separator-{kind}", daemon=True)
        self._threads.add(thread)
        thread.start()

    def test_connection(self) -> None:
        server = self.server_url()
        self._launch(
            "connection",
            lambda: fetch_separator_health(server),
            f"Testing Audio Separator API · {server}",
        )

    def start_separation(self) -> None:
        source = Path(self.source_edit.text().strip())
        if not source.is_file():
            QMessageBox.information(self, "Audio Separator", "Select a valid source audio file first.")
            return
        server = self.server_url()
        self.result_paths.clear()
        for edit in self.result_edits.values():
            edit.clear()
        for button in self.download_buttons.values():
            button.setEnabled(False)
        for button in (*self.play_buttons.values(), *self.stop_buttons.values()):
            button.setEnabled(False)
        self.stop_playback()

        def work() -> dict:
            result = separate_audio(server, source)
            job_id = str(result.get("job_id") or "result")
            folder = PROJECT_ROOT / "outputs" / "audio_separator" / job_id
            files = result.get("files") if isinstance(result.get("files"), dict) else {}
            local: dict[str, str] = {}
            for kind in ("vocal", "music", "mix"):
                info = files.get(kind) if isinstance(files.get(kind), dict) else {}
                filename = Path(str(info.get("filename") or f"{kind}.wav")).name
                target = folder / filename
                download_separator_file(server, str(info.get("url") or ""), target)
                local[kind] = str(target.resolve())
            result["local"] = local
            return result

        self._launch(
            "separation",
            work,
            "Uploading source and separating Vocal / Music · Kim_Vocal_2 runs on the Server…",
        )

    def _handle_success(self, kind: str, result: object) -> None:
        data = result if isinstance(result, dict) else {}
        if kind == "connection":
            ready = (
                bool(data.get("ready"))
                and bool(data.get("cuda_provider"))
                and data.get("provider") == "CUDAExecutionProvider"
            )
            self._api_ready = ready
            self._set_busy(False, (
                f"Audio Separator API ready · CUDAExecutionProvider · {data.get('gpu', 'GPU')} · {self.server_url()}"
                if ready else
                "Audio Separator API is online but CUDA is not ready · "
                + str(data.get("error") or ", ".join(data.get("missing") or []))
            ))
            return
        local = data.get("local") if isinstance(data.get("local"), dict) else {}
        paths = {kind: Path(str(local.get(kind) or "")) for kind in ("vocal", "music", "mix")}
        if not all(path.is_file() for path in paths.values()):
            self._handle_failure(kind, "Server returned an incomplete Vocal / Music / Mix set")
            return
        self.result_paths = paths
        for name, path in paths.items():
            self.result_edits[name].setText(str(path))
            self.play_buttons[name].setEnabled(True)
            self.stop_buttons[name].setEnabled(True)
            self.download_buttons[name].setEnabled(True)
        metrics = data.get("metrics") if isinstance(data.get("metrics"), dict) else {}
        vocal_metrics = metrics.get("vocal") if isinstance(metrics.get("vocal"), dict) else {}
        music_metrics = metrics.get("music") if isinstance(metrics.get("music"), dict) else {}
        warnings = [str(value) for value in (data.get("warnings") or []) if str(value)]
        levels = ""
        if vocal_metrics and music_metrics:
            levels = (
                f" · Vocal {vocal_metrics.get('duration_seconds', '?')}s / "
                f"{vocal_metrics.get('channels', '?')}ch / {vocal_metrics.get('rms_dbfs', '?')} dBFS"
                f" · Music {music_metrics.get('duration_seconds', '?')}s / "
                f"{music_metrics.get('channels', '?')}ch / {music_metrics.get('rms_dbfs', '?')} dBFS"
            )
        warning_text = (" · WARNING: " + " | ".join(warnings)) if warnings else ""
        self._set_busy(
            False,
            "Separation complete · audition or download each result; Add maps Music→A1 and Vocal→A2"
            + levels
            + warning_text,
        )
        self.add_button.setEnabled(True)

    def _handle_failure(self, kind: str, message: str) -> None:
        self._set_busy(False, f"Audio Separator {kind} failed · {message}")
        QMessageBox.critical(self, "Audio Separator failed", message)

    def download_result(self, kind: str) -> None:
        source = self.result_paths.get(kind)
        if source is None or not source.is_file():
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Save {kind.title()}",
            str(source),
            "Audio (*.wav *.mp3 *.flac *.m4a *.aac *.ogg);;All files (*)",
        )
        if not filename:
            return
        target = Path(filename)
        if target.resolve() != source.resolve():
            shutil.copy2(source, target)
        self.status_label.setText(f"Saved {kind.title()} · {target}")

    def play_result(self, kind: str) -> None:
        source = self.result_paths.get(kind)
        if source is None or not source.is_file():
            return
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(source.resolve())))
        self.player.play()
        self.status_label.setText(f"Playing {kind.title()} · {source.name}")

    def stop_playback(self) -> None:
        self.player.stop()

    def add_to_media_pool(self) -> None:
        if not all(self.result_paths.get(kind, Path()).is_file() for kind in ("vocal", "music", "mix")):
            return
        self.add_requested.emit(
            str(self.result_paths["music"]),
            str(self.result_paths["vocal"]),
            str(self.result_paths["mix"]),
        )
        self.status_label.setText(
            "Added request sent · Music→A1, Vocal→A2, untouched Mix→Project exact master."
        )

    def _block_busy_close(self) -> bool:
        if self._busy:
            QMessageBox.information(
                self,
                "Audio Separator is running",
                "Wait for the Server separation and downloads to finish before closing.",
            )
            return True
        return False

    def _release_before_close(self) -> None:
        if self._close_release_completed:
            return
        self.readiness_timer.stop()
        self.stop_playback()
        if self.runtime_state.mode == "server":
            try:
                self.status_label.setText(
                    "Leaving Audio Separator · stopping local API and releasing CUDA memory…"
                )
                stop_local_audio_separator_server()
            except Exception as exc:
                print(f"[Audio Separator] local server stop failed: {exc}", flush=True)
        self._close_release_completed = True

    def reject(self) -> None:
        if self._block_busy_close():
            return
        self._release_before_close()
        self._closed = True
        super().reject()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._block_busy_close():
            event.ignore()
            return
        self._release_before_close()
        self._closed = True
        super().closeEvent(event)

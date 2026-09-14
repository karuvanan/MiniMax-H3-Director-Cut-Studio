"""Standalone SoulX-Singer SVC workbench for Director Cut Studio."""

from __future__ import annotations

import math
from pathlib import Path
import shutil
import threading
import time

from PySide6.QtCore import QPointF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from soulx_client import (
    DEFAULT_SOULX_SERVER,
    convert_singing_voice,
    fetch_api_info,
    request_server_unload,
    validate_svc_api,
)
from soulx_runtime import (
    LOCAL_SOULX_SERVER,
    REMOTE_SOULX_SERVER,
    SoulXRuntimeState,
    detect_soulx_runtime,
    install_local_soulx_server,
    read_soulx_startup_progress,
    start_local_soulx_server_if_installed,
    stop_local_soulx_server,
)


AUDIO_FILTER = "Audio (*.mp3 *.wav *.flac *.m4a *.aac *.ogg);;All files (*)"


class _BusySpinnerOverlay(QWidget):
    """Full-window translucent veil with a centered cyan spinner."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._phase = 0
        self._message = "Working…"
        self._background: QPixmap | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(70)
        self._timer.timeout.connect(self._advance)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setCursor(Qt.WaitCursor)
        self.hide()

    def start(self, message: str) -> None:
        self._message = str(message or "Working…")
        self._phase = 0
        parent = self.parentWidget()
        self._background = parent.grab()
        self.setGeometry(parent.rect())
        self.raise_()
        self.show()
        self._timer.start()
        self.update()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _advance(self) -> None:
        self._phase = (self._phase + 1) % 12
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        if self._background and not self._background.isNull():
            painter.drawPixmap(self.rect(), self._background)
        painter.fillRect(self.rect(), QColor(5, 11, 18, 148))
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        for index in range(12):
            step = (index - self._phase) % 12
            alpha = max(45, 255 - step * 18)
            angle = math.radians(index * 30.0 - 90.0)
            start = QPointF(center.x() + math.cos(angle) * 24.0, center.y() + math.sin(angle) * 24.0)
            end = QPointF(center.x() + math.cos(angle) * 44.0, center.y() + math.sin(angle) * 44.0)
            painter.setPen(QPen(QColor(74, 218, 232, alpha), 6.0, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(start, end)
        painter.setPen(QColor(245, 249, 255))
        font = QFont(painter.font())
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        text_rect = self.rect().adjusted(24, int(center.y() + 58), -24, -24)
        painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, self._message)


class SoulXSingerDialog(QDialog):
    """Convert a song independently; the result is never injected into H3."""

    task_succeeded = Signal(str, object)
    task_failed = Signal(str, str)
    task_progress = Signal(str)
    runtime_mode_changed = Signal(object)
    readiness_checked = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        runtime_state: SoulXRuntimeState | None = None,
    ) -> None:
        super().__init__(parent)
        self._busy = False
        self._closed = False
        self._close_unload_attempted = False
        self._close_release_completed = False
        self._readiness_probe_running = False
        self._api_ready = False
        self._readiness_started = time.monotonic()
        self._threads: set[threading.Thread] = set()
        self.output_path: Path | None = None
        self.runtime_state = runtime_state or detect_soulx_runtime()

        self.setWindowTitle("SOULX · Singing Voice Clone")
        self.resize(820, 560)
        self.setMinimumSize(700, 500)
        layout = QVBoxLayout(self)

        explanation = QLabel(
            "Independent SVC workflow: clone the voice, audition it, then Save As MP3. "
            "The result is not added to Media Pool, Timeline or H3 automatically."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color:#cdd7e6; font-weight:600;")
        layout.addWidget(explanation)

        connection = QGroupBox("SOULX SERVER")
        connection_layout = QGridLayout(connection)
        self.server_edit = QLineEdit(self.runtime_state.api_url or DEFAULT_SOULX_SERVER)
        self.server_edit.setObjectName("soulxApiEdit")
        self.test_button = QPushButton("TEST")
        self.test_button.clicked.connect(self.test_connection)
        self.runtime_mode_label = QLabel()
        self.runtime_mode_label.setWordWrap(True)
        self.install_local_button = QPushButton("INSTALL LOCAL SOULX")
        self.install_local_button.clicked.connect(self.install_local_runtime)
        connection_layout.addWidget(QLabel("API"), 0, 0)
        connection_layout.addWidget(self.server_edit, 0, 1)
        connection_layout.addWidget(self.test_button, 0, 2)
        connection_layout.addWidget(self.runtime_mode_label, 1, 0, 1, 2)
        connection_layout.addWidget(self.install_local_button, 1, 2)
        layout.addWidget(connection)

        inputs = QGroupBox("SINGING VOICE CONVERSION")
        inputs_layout = QGridLayout(inputs)
        self.voice_reference_edit = QLineEdit()
        self.voice_reference_edit.setReadOnly(True)
        self.voice_reference_edit.setPlaceholderText(
            "Target voice/timbre reference · e.g. the older male voice to clone"
        )
        voice_button = QPushButton("SELECT VOICE")
        voice_button.clicked.connect(self.choose_voice_reference)
        self.source_song_edit = QLineEdit()
        self.source_song_edit.setReadOnly(True)
        self.source_song_edit.setPlaceholderText(
            "Original song · melody, rhythm, lyrics and accompaniment source"
        )
        song_button = QPushButton("SELECT SONG")
        song_button.clicked.connect(self.choose_source_song)
        inputs_layout.addWidget(QLabel("Voice reference"), 0, 0)
        inputs_layout.addWidget(self.voice_reference_edit, 0, 1)
        inputs_layout.addWidget(voice_button, 0, 2)
        inputs_layout.addWidget(QLabel("Source song"), 1, 0)
        inputs_layout.addWidget(self.source_song_edit, 1, 1)
        inputs_layout.addWidget(song_button, 1, 2)
        layout.addWidget(inputs)

        options = QGroupBox("SVC SETTINGS")
        options_layout = QGridLayout(options)
        self.prompt_vocal_sep_check = QCheckBox("Separate voice-reference vocals")
        self.prompt_vocal_sep_check.setChecked(False)
        self.target_vocal_sep_check = QCheckBox("Separate source-song vocals")
        self.target_vocal_sep_check.setChecked(True)
        self.auto_shift_check = QCheckBox("Auto pitch shift")
        self.auto_shift_check.setChecked(True)
        self.auto_mix_check = QCheckBox("Mix original accompaniment")
        self.auto_mix_check.setChecked(True)
        self.fp16_check = QCheckBox("FP16 (server option)")
        self.fp16_check.setChecked(True)
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cuda", "directml", "cpu"])
        self.device_combo.setCurrentText("cuda")
        self.auto_unload_check = QCheckBox(
            "Unload server models after conversion (closing always unloads)"
        )
        self.auto_unload_check.setChecked(True)
        self.auto_unload_check.setToolTip(
            "Releases SoulX models after each conversion. Closing this window always "
            "unloads the models; Local Server Mode also stops its hidden server process."
        )
        self.pitch_shift_spin = QSpinBox()
        self.pitch_shift_spin.setRange(-36, 36)
        self.pitch_shift_spin.setValue(0)
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 200)
        self.steps_spin.setValue(32)
        self.cfg_spin = QDoubleSpinBox()
        self.cfg_spin.setRange(0.0, 10.0)
        self.cfg_spin.setSingleStep(0.1)
        self.cfg_spin.setValue(1.0)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 10_000)
        self.seed_spin.setValue(42)
        options_layout.addWidget(self.prompt_vocal_sep_check, 0, 0, 1, 2)
        options_layout.addWidget(self.target_vocal_sep_check, 0, 2, 1, 2)
        options_layout.addWidget(self.auto_shift_check, 1, 0, 1, 2)
        options_layout.addWidget(self.auto_mix_check, 1, 2, 1, 2)
        options_layout.addWidget(QLabel("Manual pitch (semitones)"), 2, 0)
        options_layout.addWidget(self.pitch_shift_spin, 2, 1)
        options_layout.addWidget(QLabel("Steps"), 2, 2)
        options_layout.addWidget(self.steps_spin, 2, 3)
        options_layout.addWidget(QLabel("CFG"), 3, 0)
        options_layout.addWidget(self.cfg_spin, 3, 1)
        options_layout.addWidget(QLabel("Seed"), 3, 2)
        options_layout.addWidget(self.seed_spin, 3, 3)
        options_layout.addWidget(QLabel("Server device"), 4, 0)
        options_layout.addWidget(self.device_combo, 4, 1)
        options_layout.addWidget(self.fp16_check, 4, 2, 1, 2)
        options_layout.addWidget(self.auto_unload_check, 5, 0, 1, 4)
        layout.addWidget(options)

        action_row = QHBoxLayout()
        self.convert_button = QPushButton("CLONE SINGING VOICE")
        self.convert_button.setStyleSheet("background:#6e46a8; font-weight:700;")
        self.convert_button.clicked.connect(self.start_conversion)
        self.play_button = QPushButton("PLAY")
        self.pause_button = QPushButton("PAUSE")
        self.stop_button = QPushButton("STOP")
        self.save_button = QPushButton("SAVE AS MP3")
        for button in (self.play_button, self.pause_button, self.stop_button, self.save_button):
            button.setEnabled(False)
        self.play_button.clicked.connect(self.play_output)
        self.pause_button.clicked.connect(self.player_pause)
        self.stop_button.clicked.connect(self.player_stop)
        self.save_button.clicked.connect(self.save_output_as)
        action_row.addWidget(self.convert_button)
        action_row.addStretch(1)
        action_row.addWidget(self.play_button)
        action_row.addWidget(self.pause_button)
        action_row.addWidget(self.stop_button)
        action_row.addWidget(self.save_button)
        layout.addLayout(action_row)

        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("Converted MP3 will appear here")
        layout.addWidget(self.output_edit)
        self.status_label = QLabel("Ready · Select a voice reference and an original song")
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.9)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.busy_overlay = _BusySpinnerOverlay(self)
        self.task_succeeded.connect(self._handle_success)
        self.task_failed.connect(self._handle_failure)
        self.task_progress.connect(self.status_label.setText)
        self.readiness_checked.connect(self._handle_readiness_result)
        self.readiness_timer = QTimer(self)
        self.readiness_timer.setInterval(900)
        self.readiness_timer.timeout.connect(self._probe_server_readiness)
        self._update_runtime_controls()
        self._start_readiness_monitor()

    def _server(self) -> str:
        return self.server_edit.text().strip().rstrip("/")

    def _update_runtime_controls(self) -> None:
        state = self.runtime_state
        if state.mode == "server":
            self.runtime_mode_label.setText(
                f"SERVER MODE · Local SoulX · {state.gpu_vram_gb:.1f} GB VRAM · "
                f"{LOCAL_SOULX_SERVER}"
            )
            self.runtime_mode_label.setStyleSheet("color:#55d69e; font-weight:700;")
            self.install_local_button.setText("LOCAL SERVER INSTALLED")
            self.install_local_button.setEnabled(False)
            return
        self.runtime_mode_label.setText(
            f"CLIENT MODE · Remote API {REMOTE_SOULX_SERVER} · {state.detail}"
        )
        self.runtime_mode_label.setStyleSheet("color:#6ddce8; font-weight:700;")
        if state.install_eligible:
            self.install_local_button.setText("INSTALL LOCAL SOULX")
            self.install_local_button.setEnabled(not self._busy)
        else:
            self.install_local_button.setText("LOCAL INSTALL REQUIRES >16 GB VRAM")
            self.install_local_button.setEnabled(False)

    def _start_readiness_monitor(self) -> None:
        self._api_ready = False
        self._readiness_started = time.monotonic()
        self.convert_button.setEnabled(False)
        if self.runtime_state.mode == "server":
            try:
                start_local_soulx_server_if_installed(self.runtime_state)
                self.status_label.setText("SoulX Server · starting local service…")
            except Exception as exc:
                self.status_label.setText(f"SoulX Server start failed · {exc}")
        else:
            self.status_label.setText(
                f"SoulX Client · connecting remote API · {self._server()}"
            )
        self.readiness_timer.start()
        QTimer.singleShot(0, self._probe_server_readiness)

    def _probe_server_readiness(self) -> None:
        if self._closed or self._api_ready or self._readiness_probe_running:
            return
        self._readiness_probe_running = True
        server = self._server()
        mode = self.runtime_state.mode
        elapsed = max(0, int(time.monotonic() - self._readiness_started))

        def run() -> None:
            try:
                info = fetch_api_info(server, timeout=1.5)
                parameters = validate_svc_api(info)
                result = {
                    "ready": True,
                    "server": server,
                    "parameters": parameters,
                    "message": (
                        f"SoulX API ready · {server} · "
                        f"{len(parameters)} SVC controls detected"
                    ),
                }
            except Exception as exc:
                progress = (
                    read_soulx_startup_progress()
                    if mode == "server"
                    else f"SoulX Client · waiting for remote API · {server}"
                )
                result = {
                    "ready": False,
                    "server": server,
                    "message": f"{progress} · {elapsed}s",
                    "error": str(exc),
                }
            self.readiness_checked.emit(result)

        thread = threading.Thread(target=run, name="soulx-readiness", daemon=True)
        self._threads.add(thread)
        thread.start()

    def _handle_readiness_result(self, result: object) -> None:
        self._readiness_probe_running = False
        self._threads = {item for item in self._threads if item.is_alive()}
        if self._closed:
            return
        data = result if isinstance(result, dict) else {}
        self.status_label.setText(str(data.get("message") or "SoulX API status unknown"))
        if not data.get("ready"):
            return
        self._api_ready = True
        self.readiness_timer.stop()
        self.convert_button.setEnabled(not self._busy)

    def install_local_runtime(self) -> None:
        if self.runtime_state.mode == "server":
            return
        if not self.runtime_state.install_eligible:
            QMessageBox.information(
                self,
                "SoulX Client Mode",
                "This computer remains a Client. Local SoulX installation requires "
                "a GPU with more than 16 GB VRAM.",
            )
            return
        answer = QMessageBox.question(
            self,
            "Install local SoulX server",
            f"Detected {self.runtime_state.gpu_vram_gb:.1f} GB VRAM.\n\n"
            "Install the isolated SoulX Python 3.10 runtime and official SVC/preprocessing "
            "models now? The download is large and may take considerable time. Nothing is "
            "installed unless you choose Yes.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._launch(
            "installation",
            lambda: install_local_soulx_server(progress=self.task_progress.emit).to_dict(),
            status_message="Installing local SoulX server…",
            overlay_message="INSTALLING SOULX SERVER · DOWNLOADING RUNTIME AND MODELS…",
        )

    def choose_voice_reference(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Select target voice reference", "", AUDIO_FILTER)
        if filename:
            self.voice_reference_edit.setText(filename)

    def choose_source_song(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Select original song", "", AUDIO_FILTER)
        if filename:
            self.source_song_edit.setText(filename)

    def _set_busy(
        self,
        busy: bool,
        message: str = "",
        overlay_message: str = "",
    ) -> None:
        self._busy = bool(busy)
        self.convert_button.setEnabled(not busy and self._api_ready)
        self.test_button.setEnabled(not busy)
        self.install_local_button.setEnabled(
            not busy
            and self.runtime_state.mode != "server"
            and self.runtime_state.install_eligible
        )
        if busy and overlay_message:
            self.busy_overlay.start(overlay_message)
        elif not busy:
            self.busy_overlay.stop()
        if message:
            self.status_label.setText(message)

    def _launch(
        self,
        kind: str,
        function,
        *,
        status_message: str,
        overlay_message: str = "",
    ) -> None:
        if self._busy:
            return
        self._set_busy(True, status_message, overlay_message)

        def run() -> None:
            thread = threading.current_thread()
            try:
                result = function()
                self.task_succeeded.emit(kind, result)
            except Exception as exc:
                self.task_failed.emit(kind, str(exc))
            finally:
                self._threads.discard(thread)

        thread = threading.Thread(target=run, name=f"soulx-{kind}", daemon=True)
        self._threads.add(thread)
        thread.start()

    def test_connection(self) -> None:
        server = self._server()

        def work() -> dict:
            info = fetch_api_info(server)
            parameters = validate_svc_api(info)
            return {"parameters": parameters}

        self._launch(
            "connection",
            work,
            status_message=f"Testing SoulX API · {server}",
        )

    def start_conversion(self) -> None:
        voice_reference = self.voice_reference_edit.text().strip()
        source_song = self.source_song_edit.text().strip()
        if not voice_reference or not Path(voice_reference).is_file():
            QMessageBox.information(self, "SoulX", "Select a valid target voice reference first.")
            return
        if not source_song or not Path(source_song).is_file():
            QMessageBox.information(self, "SoulX", "Select a valid original song first.")
            return
        server = self._server()
        settings = {
            "prompt_vocal_sep": self.prompt_vocal_sep_check.isChecked(),
            "target_vocal_sep": self.target_vocal_sep_check.isChecked(),
            "auto_shift": self.auto_shift_check.isChecked(),
            "auto_mix_acc": self.auto_mix_check.isChecked(),
            "pitch_shift": self.pitch_shift_spin.value(),
            "n_step": self.steps_spin.value(),
            "cfg": self.cfg_spin.value(),
            "seed": self.seed_spin.value(),
            "device": self.device_combo.currentText(),
            "use_fp16": self.fp16_check.isChecked(),
        }
        request_unload = self.auto_unload_check.isChecked()
        def work() -> dict:
            output = convert_singing_voice(
                server,
                voice_reference=voice_reference,
                source_song=source_song,
                **settings,
            )
            unload = None
            if request_unload:
                try:
                    unload = request_server_unload(server)
                except Exception as exc:
                    unload = {"supported": False, "unloaded": False, "warning": str(exc)}
            return {"output": str(output), "unload": unload}

        self._launch(
            "conversion",
            work,
            status_message="SoulX conversion running · keep this window open…",
            overlay_message="CLONING SINGING VOICE…",
        )

    def _handle_success(self, kind: str, result: object) -> None:
        if self._closed:
            return
        self._set_busy(False)
        data = result if isinstance(result, dict) else {}
        if kind == "installation":
            self.runtime_state = SoulXRuntimeState(
                mode=str(data.get("mode") or "server"),
                api_url=str(data.get("api_url") or LOCAL_SOULX_SERVER),
                installed=bool(data.get("installed", True)),
                gpu_vram_gb=float(data.get("gpu_vram_gb") or 0.0),
                install_eligible=bool(data.get("install_eligible", True)),
                detail=str(data.get("detail") or "Local SoulX server installed"),
            )
            self.server_edit.setText(self.runtime_state.api_url)
            self._update_runtime_controls()
            self.status_label.setText(
                f"Local SoulX installed · SERVER MODE · {self.runtime_state.api_url}"
            )
            self.runtime_mode_changed.emit(self.runtime_state)
            self._start_readiness_monitor()
            return
        if kind == "connection":
            parameters = data.get("parameters") or []
            self.status_label.setText(
                f"SoulX API ready · {self._server()} · {len(parameters)} SVC controls detected"
            )
            self._api_ready = True
            self.readiness_timer.stop()
            self.convert_button.setEnabled(not self._busy)
            return
        output = Path(str(data.get("output") or ""))
        if not output.is_file():
            self._handle_failure(kind, "SoulX returned no valid output file")
            return
        self.output_path = output
        self.output_edit.setText(str(output))
        self.player.setSource(QUrl.fromLocalFile(str(output)))
        for button in (self.play_button, self.pause_button, self.stop_button, self.save_button):
            button.setEnabled(True)
        unload = data.get("unload") if isinstance(data.get("unload"), dict) else None
        if unload and unload.get("unloaded"):
            unload_text = f"server model unloaded via {unload.get('endpoint')}"
        elif unload:
            unload_text = str(unload.get("warning") or "server model was not unloaded")
        else:
            unload_text = "automatic server unload disabled"
        self.status_label.setText(
            f"Conversion complete · MP3 ready · {unload_text} · use Save As, then load it into A1 manually"
        )

    def _handle_failure(self, kind: str, message: str) -> None:
        if self._closed:
            return
        self._set_busy(False)
        title = {
            "connection": "SoulX connection failed",
            "installation": "SoulX installation failed",
        }.get(kind, "SoulX conversion failed")
        self.status_label.setText(f"{title} · {message}")
        QMessageBox.critical(self, title, message)

    def play_output(self) -> None:
        if self.output_path and self.output_path.is_file():
            self.player.play()

    def player_pause(self) -> None:
        self.player.pause()

    def player_stop(self) -> None:
        self.player.stop()

    def save_output_as(self) -> None:
        if not self.output_path or not self.output_path.is_file():
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save SoulX converted singing",
            str(self.output_path),
            "MP3 audio (*.mp3)",
        )
        if not filename:
            return
        target = Path(filename)
        if target.suffix.casefold() != ".mp3":
            target = target.with_suffix(".mp3")
        if target.resolve() != self.output_path.resolve():
            shutil.copy2(self.output_path, target)
        self.status_label.setText(
            f"Saved MP3 · {target} · manually load this file into A1 for MTV generation"
        )

    def unload_connection(self) -> str:
        return self._server()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "busy_overlay"):
            self.busy_overlay.setGeometry(self.rect())

    def _block_busy_close(self) -> bool:
        if not self._busy:
            return False
        self.status_label.setText("Please wait for the active SoulX task to finish before closing")
        return True

    def _release_before_close(self) -> None:
        if self._close_release_completed:
            return
        self._close_unload_attempted = True
        server = self._server()
        self.status_label.setText(f"Leaving SoulX · unloading server models · {server}")
        try:
            result = request_server_unload(server, timeout=4.0)
            if not result.get("unloaded"):
                warning = str(result.get("warning") or "server did not confirm unload")
                print(f"[SoulX] close unload warning: {warning}", flush=True)
        except Exception as exc:
            # Closing the independent workbench must remain possible if a
            # remote server disappeared; preserve the diagnostic in stdout.
            print(f"[SoulX] close unload failed: {exc}", flush=True)
        if self.runtime_state.mode == "server":
            try:
                stop_local_soulx_server()
                print("[SoulX] local server stopped after leaving SoulX", flush=True)
            except Exception as exc:
                print(f"[SoulX] local server stop failed: {exc}", flush=True)
        self._close_release_completed = True

    def reject(self) -> None:
        if self._block_busy_close():
            return
        self.readiness_timer.stop()
        self.busy_overlay.stop()
        self.player.stop()
        self._release_before_close()
        self._closed = True
        super().reject()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._block_busy_close():
            event.ignore()
            return
        self.readiness_timer.stop()
        self.busy_overlay.stop()
        self.player.stop()
        self._release_before_close()
        self._closed = True
        super().closeEvent(event)

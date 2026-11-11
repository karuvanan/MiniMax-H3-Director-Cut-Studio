#!/usr/bin/env python3
"""PyQt6 desktop interface for subtitle_pipeline.py."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen

# PyQt6 can be installed privately in this tool folder, leaving the shared
# ai_libraries_common Python environment unchanged.
VENDOR_DIR = Path(__file__).with_name("vendor")
if VENDOR_DIR.is_dir():
    sys.path.insert(0, str(VENDOR_DIR))

from PyQt6.QtCore import QSettings, QThread, QTimer, QUrl, Qt, QtMsgType, qInstallMessageHandler, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QColorDialog, QFileDialog, QFontComboBox, QFormLayout, QFrame, QScrollArea,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QPlainTextEdit, QProgressBar, QSpinBox,
    QVBoxLayout, QWidget, QDialog,
)


APP_NAME = "Local Subtitle Tool"


def translation_filename(language: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\s]+', '_', language).strip('._')
    return f"translated_{cleaned or 'target'}"


def qt_message_handler(mode, context, message) -> None:
    """Suppress a harmless Qt/Windows invalid-default-font warning at startup."""
    if message.startswith(("QFont::setPointSize: Point size <= 0", "QFontDatabase: Cannot find font directory")):
        return
    if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        sys.stderr.write(message + "\n")


class SubtitlePositionPreview(QWidget):
    position_changed = pyqtSignal(float, float)

    def __init__(self) -> None:
        super().__init__()
        self.x, self.y = 50.0, 88.0
        self.font_name, self.font_size = "Arial", 32
        self.color, self.outline_color, self.outline = QColor("#FFFFFF"), QColor("#000000"), 2
        self.bold = False
        self.video_width, self.video_height = 1920, 1080
        self.background = QPixmap()
        self.dragging = False
        self.setMinimumSize(1, 1)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_style(self, font_name: str, font_size: int, color: QColor, outline_color: QColor, outline: int, bold: bool) -> None:
        self.font_name, self.font_size = font_name, font_size
        self.color, self.outline_color, self.outline, self.bold = color, outline_color, outline, bold
        self.update()

    def set_position(self, x: float, y: float) -> None:
        self.x, self.y = x, y
        self.update()

    def set_video_resolution(self, width: int, height: int) -> None:
        self.video_width, self.video_height = width, height
        self.update()

    def set_background(self, image_path: Path) -> None:
        self.background = QPixmap(str(image_path))
        self.update()

    def move_caption(self, point) -> None:
        self.x = max(4, min(96, point.x() / self.width() * 100))
        self.y = max(5, min(95, point.y() / self.height() * 100))
        self.position_changed.emit(self.x, self.y)
        self.update()

    def mousePressEvent(self, event) -> None:
        self.dragging = True
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.move_caption(event.position())

    def mouseMoveEvent(self, event) -> None:
        if self.dragging:
            self.move_caption(event.position())

    def mouseReleaseEvent(self, event) -> None:
        self.dragging = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        if self.background.isNull():
            painter.fillRect(self.rect(), QColor("#1D232B"))
        else:
            painter.drawPixmap(self.rect(), self.background)
        painter.setPen(QPen(QColor("#45515F"), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.setPen(QPen(QColor("#526170"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(self.width() // 2, 0, self.width() // 2, self.height())
        painter.drawLine(0, self.height() // 2, self.width(), self.height() // 2)
        font = QFont(self.font_name)
        scale = min(self.width() / self.video_width, self.height() / self.video_height)
        font.setPixelSize(max(7, round(self.font_size * scale)))
        font.setBold(self.bold)
        path = QPainterPath()
        text = "Sample subtitle"
        path.addText(0, 0, font, text)
        bounds = path.boundingRect()
        x = self.width() * self.x / 100 - bounds.width() / 2
        y = self.height() * self.y / 100 - bounds.height() / 2
        painter.translate(x, y)
        painter.setPen(QPen(self.outline_color, max(1, round(self.outline * scale)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        # Draw the fill in a separate, second pass so a thick outline can
        # never cover the chosen text colour.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.color)
        painter.drawPath(path)


class AspectPreviewContainer(QWidget):
    def __init__(self, preview: SubtitlePositionPreview) -> None:
        super().__init__()
        self.preview = preview
        self.preview.setParent(self)
        self.ratio = 16 / 9
        self.setMinimumSize(360, 210)

    def set_video_resolution(self, width: int, height: int) -> None:
        self.ratio = width / height
        self.preview.set_video_resolution(width, height)
        self.update_preview_geometry()

    def resizeEvent(self, event) -> None:
        self.update_preview_geometry()

    def update_preview_geometry(self) -> None:
        available_w, available_h = self.width(), self.height()
        width = min(available_w, round(available_h * self.ratio))
        height = round(width / self.ratio)
        if height > available_h:
            height = available_h
            width = round(height * self.ratio)
        self.preview.setGeometry((available_w - width) // 2, (available_h - height) // 2, width, height)


class PipelineWorker(QThread):
    log = pyqtSignal(str)
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, command: list[str], output_dir: Path) -> None:
        super().__init__()
        self.command = command
        self.output_dir = output_dir
        self.process: subprocess.Popen[str] | None = None

    def run(self) -> None:
        try:
            self.process = subprocess.Popen(
                self.command,
                cwd=str(Path(__file__).parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.log.emit(line.rstrip())
            code = self.process.wait()
            if code == 0:
                self.completed.emit(str(self.output_dir))
            else:
                self.failed.emit(f"The pipeline stopped with exit code {code}.")
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            self.process = None

    def cancel(self) -> None:
        if self.process and self.process.poll() is None:
            self.log.emit("Stopping the current job …")
            self.process.terminate()


class ModelsWorker(QThread):
    loaded = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, endpoint: str) -> None:
        super().__init__()
        self.endpoint = endpoint.rstrip("/")

    def run(self) -> None:
        try:
            root = self.endpoint[:-3] if self.endpoint.endswith("/v1") else self.endpoint
            with urlopen(root + "/v1/models", timeout=8) as response:
                payload = json.load(response)
            models = [item.get("id", "") for item in payload.get("data", []) if item.get("id")]
            if not models:
                raise RuntimeError("LM Studio returned no loaded models.")
            self.loaded.emit(models)
        except Exception as error:
            self.failed.emit(str(error))


class UnloadModelWorker(QThread):
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, endpoint: str, instance_id: str) -> None:
        super().__init__()
        self.endpoint, self.instance_id = endpoint.rstrip("/"), instance_id

    def run(self) -> None:
        try:
            root = self.endpoint[:-3] if self.endpoint.endswith("/v1") else self.endpoint
            request = Request(root + "/api/v1/models/unload", data=json.dumps({"instance_id": self.instance_id}).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request, timeout=15):
                pass
            self.completed.emit(self.instance_id)
        except Exception as error:
            self.failed.emit(str(error))


class ScriptEditor(QPlainTextEdit):
    file_dropped = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(110)
        self.setPlaceholderText("Paste or type a script here. You can also drag a .txt or .docx file into this box.")

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.file_dropped.emit(urls[0].toLocalFile())
        elif event.mimeData().hasText():
            self.insertPlainText(event.mimeData().text())
        event.acceptProposedAction()


class PreviewDialog(QDialog):
    def __init__(self, video: Path, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Subtitle preview")
        self.resize(900, 560)
        self.player, self.audio = QMediaPlayer(self), QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.8)
        view = QVideoWidget()
        self.player.setVideoOutput(view)
        self.player.setSource(QUrl.fromLocalFile(str(video)))
        toggle = QPushButton("Play / Pause")
        toggle.clicked.connect(self.toggle)
        layout = QVBoxLayout(self)
        layout.addWidget(view, 1)
        layout.addWidget(toggle)
        self.player.play()

    def toggle(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()


class SrtEditorDialog(QDialog):
    render_requested = pyqtSignal()

    def __init__(self, srt: Path, parent: QWidget) -> None:
        super().__init__(parent)
        self.srt = srt
        self.setWindowTitle("Edit subtitles before MP4 render")
        self.resize(900, 620)
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(srt.read_text(encoding="utf-8"))
        save = QPushButton("Save SRT")
        render = QPushButton("Save and render MP4")
        save.clicked.connect(self.save)
        render.clicked.connect(self.render)
        buttons = QHBoxLayout(); buttons.addWidget(save); buttons.addStretch(); buttons.addWidget(render)
        layout = QVBoxLayout(self); layout.addWidget(QLabel("Edit subtitle text and timecodes, then render the final MP4.")); layout.addWidget(self.editor, 1); layout.addLayout(buttons)

    def save(self) -> None:
        self.srt.write_text(self.editor.toPlainText().strip() + "\n", encoding="utf-8")

    def render(self) -> None:
        self.save()
        self.render_requested.emit()
        self.accept()


class AssEditorDialog(SrtEditorDialog):
    def __init__(self, ass: Path, parent: QWidget) -> None:
        super().__init__(ass, parent)
        self.srt = ass
        self.setWindowTitle("Edit ASS before MP4 render")


class PathField(QWidget):
    path_changed = pyqtSignal(str)

    def __init__(self, title: str, file_filter: str, directory: bool = False) -> None:
        super().__init__()
        self.file_filter = file_filter
        self.directory = directory
        self.setAcceptDrops(not directory)
        self.edit = QLineEdit()
        self.edit.setAcceptDrops(False)
        self.edit.editingFinished.connect(lambda: self.path_changed.emit(self.text()))
        self.button = QPushButton("Browse…")
        self.button.clicked.connect(self.choose)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.button)
        self.setToolTip(title)

    def choose(self) -> None:
        current = self.edit.text().strip() or str(Path.home())
        if self.directory:
            path = QFileDialog.getExistingDirectory(self, "Choose output folder", current)
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Choose file", current, self.file_filter)
        if path:
            self.edit.setText(os.path.normpath(path))
            self.path_changed.emit(self.text())

    def dragEnterEvent(self, event) -> None:
        if not self.directory and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile() and not self.directory:
            self.edit.setText(os.path.normpath(urls[0].toLocalFile()))
            self.path_changed.emit(self.text())
            event.acceptProposedAction()

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, text: str) -> None:
        self.edit.setText(text)


class VideoDropBox(QLabel):
    path_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.video_path = ""
        self.setAcceptDrops(True)
        self.setMinimumHeight(165)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setText("")
        self.setStyleSheet("QLabel { padding: 18px; background: #FFFFFF; border: 1px dashed #7B8A9A; border-radius: 6px; color: #526170; }")

    def text(self) -> str:
        return self.video_path

    def setText(self, path: str) -> None:
        self.video_path = path
        if path:
            super().setText(f"Loaded video\n{Path(path).name}\n\n{path}")
        else:
            super().setText("Drag a video here\nor double-click to browse…")

    def choose(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose video", self.video_path or str(Path.home()), "Video files (*.mp4 *.mov *.mkv *.avi *.webm);;All files (*.*)")
        if path:
            self.setText(os.path.normpath(path))
            self.path_changed.emit(self.video_path)

    def mouseDoubleClickEvent(self, event) -> None:
        self.choose()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.setText(os.path.normpath(urls[0].toLocalFile()))
            self.path_changed.emit(self.video_path)
            event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("LocalAI", "LocalSubtitleTool")
        self.worker: PipelineWorker | None = None
        self.models_worker: ModelsWorker | None = None
        self.unload_worker: UnloadModelWorker | None = None
        self.started_at = 0.0
        self.estimated_seconds = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.setWindowTitle(APP_NAME)
        self.resize(1120, 900)
        self.setMinimumSize(900, 700)
        self.build_ui()
        self.restore_settings()

    def build_ui(self) -> None:
        root = QWidget()
        root.setMinimumWidth(1000)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)
        layout = QVBoxLayout(root)
        layout.setSpacing(12)

        intro = QLabel("Local subtitle translation")
        intro.setObjectName("title")
        layout.addWidget(intro)
        layout.addWidget(QLabel("Audio timing comes from faster-whisper. LM Studio matches your script and translates it to the selected language."))

        files = QGroupBox("1. Source files")
        files.setMinimumHeight(285)
        source_layout = QHBoxLayout(files)
        video_box = QGroupBox("Video")
        video_layout = QVBoxLayout(video_box)
        self.video = VideoDropBox()
        self.video.path_changed.connect(self.update_preview_from_video)
        video_layout.addWidget(QLabel("Drag a video here, or double-click to browse."))
        video_layout.addWidget(self.video, 1)
        script_box = QGroupBox("Script")
        script_box.setMinimumHeight(225)
        script_layout = QVBoxLayout(script_box)
        self.script = ScriptEditor()
        self.script.setMinimumHeight(165)
        self.script.file_dropped.connect(self.load_script)
        script_layout.addWidget(QLabel("Type, paste, or drag a .txt / .docx script here."))
        script_layout.addWidget(self.script, 1)
        source_layout.addWidget(video_box, 1)
        source_layout.addWidget(script_box, 2)
        # Output is managed automatically in this program's output folder.
        self.output = PathField("Output folder", "", directory=True)
        layout.addWidget(files)

        settings = QGroupBox("2. Local AI settings")
        settings.setMinimumHeight(205)
        grid = QGridLayout(settings)
        self.lm_url = QLineEdit("http://127.0.0.1:1234/v1")
        self.lm_url.setMinimumWidth(320)
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.addItem("qwen3-8b")
        self.model.setMinimumWidth(440)
        self.load_models_button = QPushButton("Load models")
        self.load_models_button.clicked.connect(self.load_models)
        self.source_language = QComboBox()
        self.source_language.addItem("Auto detect", "auto")
        self.source_language.addItem("Chinese", "zh")
        self.source_language.addItem("English", "en")
        self.target_language = QLineEdit("English")
        self.target_language.setPlaceholderText("Type any target language, e.g. English / 中文 / Bahasa Melayu")
        self.target_language.setMinimumWidth(190)  # Keeps roughly 20 Latin characters visible beside shortcuts.
        target_language_widget = QWidget()
        target_language_layout = QHBoxLayout(target_language_widget)
        target_language_layout.setContentsMargins(0, 0, 0, 0)
        target_language_layout.setSpacing(2)
        target_language_layout.addWidget(self.target_language, 1)
        self.language_shortcuts = []
        for label, language, width in [
            ("Eng", "English", 34), ("Chi", "Chinese", 32), ("Jp", "Japanese", 25),
            ("Kor", "Korean", 32), ("Mel", "Bahasa Melayu", 32), ("India", "Hindi", 38),
            ("Thai", "Thai", 33), ("繁体", "繁體中文", 34),
        ]:
            button = QPushButton(label)
            button.setFixedSize(width, 22)
            button.setStyleSheet("padding: 0px; font-size: 9px;")
            button.setToolTip(f"Set translation language to {language}")
            button.clicked.connect(lambda checked=False, value=language: self.target_language.setText(value))
            target_language_layout.addWidget(button)
            self.language_shortcuts.append(button)
        self.whisper = QComboBox()
        self.whisper.setEditable(True)
        self.whisper.addItems(["large-v3", "medium", "small"])
        self.device = QComboBox()
        self.device.addItems(["auto", "cuda", "cpu"])
        self.compute = QComboBox()
        self.compute.setEditable(True)
        self.compute.addItems(["int8", "float16", "int8_float16"])
        grid.addWidget(QLabel("LM Studio URL"), 0, 0)
        grid.addWidget(self.lm_url, 0, 1, 1, 2)
        grid.addWidget(self.load_models_button, 0, 3)
        grid.addWidget(self.model, 0, 4, 1, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(4, 1)
        grid.addWidget(QLabel("Script language"), 1, 0)
        grid.addWidget(self.source_language, 1, 1)
        grid.addWidget(QLabel("Translate to"), 1, 2)
        grid.addWidget(target_language_widget, 1, 3, 1, 3)
        grid.addWidget(QLabel("Whisper model"), 2, 0)
        grid.addWidget(self.whisper, 2, 1)
        grid.addWidget(QLabel("Device"), 2, 2)
        grid.addWidget(self.device, 2, 3)
        grid.addWidget(QLabel("Compute type"), 2, 4)
        grid.addWidget(self.compute, 2, 5)
        self.vad_enabled = QCheckBox("Voice filter (VAD)")
        self.vad_enabled.setChecked(True)
        self.vad_enabled.setToolTip("Uncheck for sung or music-heavy audio: the voice-activity filter can cut away singing, leaving Whisper to hallucinate on what remains.")
        self.vad_threshold = QLineEdit()
        self.vad_threshold.setPlaceholderText("0.5")
        self.vad_threshold.setMaximumWidth(90)
        self.vad_threshold.setToolTip("Optional Silero VAD speech probability threshold (default 0.5). Lower it, e.g. 0.35, to keep more of sung audio.")
        grid.addWidget(QLabel("VAD"), 3, 0)
        grid.addWidget(self.vad_enabled, 3, 1)
        grid.addWidget(QLabel("Threshold"), 3, 2)
        grid.addWidget(self.vad_threshold, 3, 3)
        self.auto_unload = QCheckBox("Unload the LM Studio model after completion or error (release model VRAM)")
        self.auto_unload.setChecked(True)
        grid.addWidget(self.auto_unload, 4, 0, 1, 4)
        layout.addWidget(settings)

        style_box = QGroupBox("3. Subtitle style and position")
        style_box.setMinimumHeight(365)
        style_layout = QHBoxLayout(style_box)
        self.position_preview = SubtitlePositionPreview()
        self.position_preview.position_changed.connect(self.on_position_changed)
        self.aspect_preview = AspectPreviewContainer(self.position_preview)
        style_layout.addWidget(self.aspect_preview, 1)
        controls = QGridLayout()
        controls.setHorizontalSpacing(12)
        controls.setVerticalSpacing(10)
        self.subtitle_font = QFontComboBox()
        self.subtitle_font.setCurrentFont(QFont("Arial"))
        self.subtitle_size = QSpinBox(); self.subtitle_size.setRange(12, 96); self.subtitle_size.setValue(50)
        self.outline_width = QSpinBox(); self.outline_width.setRange(0, 12); self.outline_width.setValue(10)
        self.bold = QCheckBox("Bold")
        self.text_color = QPushButton(); self.outline_color = QPushButton()
        self.subtitle_x = QSpinBox(); self.subtitle_x.setRange(4, 96); self.subtitle_x.setValue(50); self.subtitle_x.setSuffix(" %")
        self.subtitle_y = QSpinBox(); self.subtitle_y.setRange(5, 95); self.subtitle_y.setValue(88); self.subtitle_y.setSuffix(" %")
        self.preview_info = QLabel("1920 × 1080 · 16:9")

        def tile(icon: str, title: str, widget: QWidget) -> QWidget:
            card = QWidget()
            row = QHBoxLayout(card); row.setContentsMargins(8, 6, 8, 6); row.setSpacing(8)
            glyph = QLabel(icon); glyph.setObjectName("styleIcon"); glyph.setMinimumWidth(34); glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
            words = QVBoxLayout(); words.setContentsMargins(0, 0, 0, 0); words.setSpacing(2)
            label = QLabel(title); label.setObjectName("styleLabel")
            words.addWidget(label); words.addWidget(widget)
            row.addWidget(glyph); row.addLayout(words, 1)
            card.setObjectName("styleCard")
            return card

        outline_control = QWidget(); outline_row = QHBoxLayout(outline_control); outline_row.setContentsMargins(0, 0, 0, 0); outline_row.addWidget(self.outline_width); outline_row.addWidget(self.outline_color)
        controls.addWidget(tile("A", "Font", self.subtitle_font), 0, 0, 1, 2)
        controls.addWidget(tile("↕", "Size", self.subtitle_size), 1, 0)
        controls.addWidget(tile("●", "Text color", self.text_color), 1, 1)
        controls.addWidget(tile("◎", "Outline", outline_control), 2, 0)
        controls.addWidget(tile("↔", "Position X", self.subtitle_x), 2, 1)
        controls.addWidget(tile("↕", "Position Y", self.subtitle_y), 3, 0)
        controls.addWidget(tile("B", "Weight", self.bold), 3, 1)
        controls.addWidget(tile("▣", "Video preview", self.preview_info), 4, 0, 1, 2)
        style_layout.addLayout(controls, 1)
        self.subtitle_font.currentFontChanged.connect(self.update_style_preview)
        self.subtitle_size.valueChanged.connect(self.update_style_preview)
        self.outline_width.valueChanged.connect(self.update_style_preview)
        self.bold.toggled.connect(self.update_style_preview)
        self.text_color.clicked.connect(lambda: self.pick_color("text"))
        self.outline_color.clicked.connect(lambda: self.pick_color("outline"))
        self.subtitle_x.valueChanged.connect(lambda value: self.position_preview.set_position(value, self.subtitle_y.value()))
        self.subtitle_y.valueChanged.connect(lambda value: self.position_preview.set_position(self.subtitle_x.value(), value))
        self.text_qcolor, self.outline_qcolor = QColor("#FFFFFF"), QColor("#000000")
        self.update_style_preview()
        layout.addWidget(style_box)

        render = QGroupBox("4. Export")
        render_layout = QHBoxLayout(render)
        self.output_mode = QComboBox()
        self.output_mode.addItem("Automatic: create MP4 immediately", "auto")
        self.output_mode.addItem("Manual: edit SRT before creating MP4", "manual")
        self.font_size = QSpinBox()
        self.font_size.setRange(5, 48)
        self.font_size.setValue(9)
        render_layout.addWidget(QLabel("Output mode"))
        render_layout.addWidget(self.output_mode)
        render_layout.addStretch(1)
        render_layout.addWidget(QLabel("Burned subtitle size"))
        render_layout.addWidget(self.font_size)
        layout.addWidget(render)

        buttons = QHBoxLayout()
        self.start_button = QPushButton("Start subtitle job")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start_job)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_job)
        self.open_button = QPushButton("Open output folder")
        self.open_button.clicked.connect(self.open_output)
        self.open_project_button = QPushButton("Open subtitle job")
        self.open_project_button.clicked.connect(self.choose_project)
        self.preview_button = QPushButton("Preview result")
        self.preview_button.clicked.connect(self.show_preview)
        self.preview_button.setEnabled(False)
        self.edit_srt_button = QPushButton("Edit SRT")
        self.edit_srt_button.clicked.connect(self.edit_srt)
        self.edit_srt_button.setEnabled(False)
        self.edit_ass_button = QPushButton("Edit ASS")
        self.edit_ass_button.clicked.connect(self.edit_ass)
        self.edit_ass_button.setEnabled(False)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.preview_button)
        buttons.addWidget(self.edit_srt_button)
        buttons.addWidget(self.edit_ass_button)
        buttons.addStretch(1)
        buttons.addWidget(self.open_project_button)
        buttons.addWidget(self.open_button)
        layout.addLayout(buttons)

        self.progress = QProgressBar()
        self.progress.setRange(0, 4)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.stage_label = QLabel("Ready")
        self.timer_label = QLabel("Elapsed 00:00 · Estimated remaining —")
        layout.addWidget(self.stage_label)
        layout.addWidget(self.timer_label)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Job messages will appear here. Start LM Studio's local server before running.")
        layout.addWidget(self.log, 1)
        self.download_link = QLabel()
        self.download_link.setOpenExternalLinks(False)
        self.download_link.linkActivated.connect(self.save_result_copy)
        layout.addWidget(self.download_link)

        self.statusBar().showMessage("Ready")
        menu = self.menuBar().addMenu("Help")
        about = QAction("About this tool", self)
        about.triggered.connect(self.show_about)
        menu.addAction(about)
        self.setStyleSheet("""
            QWidget { font-size: 13px; } QGroupBox { font-weight: 600; margin-top: 10px; padding: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QLabel#title { font-size: 22px; font-weight: 700; } QPushButton#primary { font-weight: 700; padding: 7px 16px; }
            QWidget#styleCard { background: #F4F6F8; border: 1px solid #D8DEE5; border-radius: 7px; }
            QLabel#styleIcon { font-size: 24px; font-weight: 700; color: #1769AA; }
            QLabel#styleLabel { font-weight: 700; color: #475569; }
        """)

    def restore_settings(self) -> None:
        for key, widget in [("lm_url", self.lm_url)]:
            value = self.settings.value(key, "")
            if value:
                widget.setText(str(value))
        self.model.setCurrentText(str(self.settings.value("model", "qwen3-8b")))
        self.whisper.setCurrentText(str(self.settings.value("whisper", "large-v3")))
        self.device.setCurrentText(str(self.settings.value("device", "auto")))
        self.compute.setCurrentText(str(self.settings.value("compute", "int8")))
        self.vad_enabled.setChecked(bool(self.settings.value("vad_enabled", True)))
        self.vad_threshold.setText(str(self.settings.value("vad_threshold", "")))
        last_output = str(self.settings.value("output", ""))
        self.output.setText(last_output or str(Path(__file__).with_name("output")))

    def save_settings(self) -> None:
        self.settings.setValue("lm_url", self.lm_url.text().strip())
        self.settings.setValue("model", self.model.currentText().strip())
        self.settings.setValue("whisper", self.whisper.currentText())
        self.settings.setValue("device", self.device.currentText())
        self.settings.setValue("compute", self.compute.currentText())
        self.settings.setValue("vad_enabled", self.vad_enabled.isChecked())
        self.settings.setValue("vad_threshold", self.vad_threshold.text().strip())
        self.settings.setValue("output", self.output.text())

    def save_project_manifest(self, script_file: Path) -> None:
        project = {
            "video": str(self.active_video), "script_file": str(script_file), "output": str(self.active_output),
            "output_prefix": self.output_prefix, "lm_url": self.lm_url.text(), "model": self.model.currentText(),
            "whisper": self.whisper.currentText(), "device": self.device.currentText(), "compute": self.compute.currentText(),
            "vad": self.vad_enabled.isChecked(), "vad_threshold": self.vad_threshold.text().strip(),
            "source_language": self.source_language.currentData(), "target_language": self.target_language.text(),
            "output_mode": self.output_mode.currentData(), "font": self.subtitle_font.currentFont().family(),
            "font_size": self.subtitle_size.value(), "text_color": self.text_qcolor.name(), "outline_color": self.outline_qcolor.name(),
            "outline_width": self.outline_width.value(), "bold": self.bold.isChecked(), "x": self.subtitle_x.value(), "y": self.subtitle_y.value(),
        }
        self.project_file.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
        self.settings.setValue("last_project", str(self.project_file))

    def choose_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open subtitle job", self.output.text() or str(Path.home()), "Subtitle job (*.json)")
        if path:
            self.load_project(Path(path), quiet=False)

    def load_project(self, path: Path, quiet: bool) -> None:
        try:
            project = json.loads(path.read_text(encoding="utf-8"))
            self.video.setText(project["video"])
            self.output.setText(project["output"])
            script_file = Path(project["script_file"])
            if script_file.is_file(): self.script.setPlainText(script_file.read_text(encoding="utf-8-sig"))
            self.active_video, self.active_output = Path(project["video"]), Path(project["output"])
            self.output_prefix = project["output_prefix"]
            self.lm_url.setText(project.get("lm_url", self.lm_url.text())); self.model.setCurrentText(project.get("model", self.model.currentText()))
            self.whisper.setCurrentText(project.get("whisper", self.whisper.currentText())); self.device.setCurrentText(project.get("device", self.device.currentText())); self.compute.setCurrentText(project.get("compute", self.compute.currentText()))
            self.vad_enabled.setChecked(bool(project.get("vad", True))); self.vad_threshold.setText(str(project.get("vad_threshold", "")))
            self.source_language.setCurrentIndex(max(0, self.source_language.findData(project.get("source_language", "auto")))); self.target_language.setText(project.get("target_language", ""))
            self.translation_suffix = translation_filename(self.target_language.text().strip())
            self.output_mode.setCurrentIndex(max(0, self.output_mode.findData(project.get("output_mode", "auto"))))
            self.subtitle_font.setCurrentFont(QFont(project.get("font", "Arial"))); self.subtitle_size.setValue(int(project.get("font_size", 50))); self.text_qcolor = QColor(project.get("text_color", "#FFFFFF")); self.outline_qcolor = QColor(project.get("outline_color", "#000000")); self.outline_width.setValue(int(project.get("outline_width", 10))); self.bold.setChecked(bool(project.get("bold", False))); self.subtitle_x.setValue(int(project.get("x", 50))); self.subtitle_y.setValue(int(project.get("y", 88))); self.update_style_preview()
            self.project_file = path; self.settings.setValue("last_project", str(path)); self.update_preview_from_video(str(self.active_video))
            self.edit_srt_button.setEnabled((self.active_output / f"{self.output_prefix}_{self.translation_suffix}.srt").is_file()); self.edit_ass_button.setEnabled((self.active_output / f"{self.output_prefix}_{self.translation_suffix}_styled.ass").is_file()); self.preview_button.setEnabled((self.active_output / f"{self.output_prefix}_{self.translation_suffix}_subtitled.mp4").is_file())
            self.stage_label.setText(f"Opened subtitle job: {path.name}")
            if not quiet: QMessageBox.information(self, APP_NAME, f"Opened subtitle job:\n{path.name}")
        except Exception as error:
            if not quiet: QMessageBox.warning(self, APP_NAME, f"Could not open subtitle job:\n{error}")

    def update_style_preview(self) -> None:
        self.text_color.setStyleSheet(f"background: {self.text_qcolor.name()}; min-width: 74px; min-height: 28px;")
        self.outline_color.setStyleSheet(f"background: {self.outline_qcolor.name()}; min-width: 52px; min-height: 28px;")
        self.position_preview.set_style(self.subtitle_font.currentFont().family(), self.subtitle_size.value(), self.text_qcolor, self.outline_qcolor, self.outline_width.value(), self.bold.isChecked())

    def update_preview_from_video(self, path: str) -> None:
        video = Path(path)
        if not video.is_file():
            return
        try:
            result = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(video)], text=True)
            stream = json.loads(result)["streams"][0]
            width, height = int(stream["width"]), int(stream["height"])
            self.aspect_preview.set_video_resolution(width, height)
            preview_dir = Path(__file__).with_name("output")
            preview_dir.mkdir(parents=True, exist_ok=True)
            first_frame = preview_dir / "subtitle_preview_first_frame.jpg"
            subprocess.run(["ffmpeg", "-y", "-ss", "0", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(first_frame)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            self.position_preview.set_background(first_frame)
            self.preview_info.setText(f"{width} × {height} · {width / height:.2f}:1")
            self.stage_label.setText("Preview updated with the first video frame")
        except Exception as error:
            self.stage_label.setText(f"Could not read video resolution: {error}")

    def pick_color(self, kind: str) -> None:
        current = self.text_qcolor if kind == "text" else self.outline_qcolor
        chosen = QColorDialog.getColor(current, self, "Choose subtitle color")
        if chosen.isValid():
            if kind == "text": self.text_qcolor = chosen
            else: self.outline_qcolor = chosen
            self.update_style_preview()

    def on_position_changed(self, x: float, y: float) -> None:
        self.subtitle_x.blockSignals(True); self.subtitle_y.blockSignals(True)
        self.subtitle_x.setValue(round(x)); self.subtitle_y.setValue(round(y))
        self.subtitle_x.blockSignals(False); self.subtitle_y.blockSignals(False)

    def start_job(self) -> None:
        video, output = Path(self.video.text()), Path(self.output.text())
        script_text = self.script.toPlainText().strip()
        if not video.is_file() or not script_text or not self.output.text() or not self.target_language.text().strip():
            QMessageBox.warning(self, APP_NAME, "Choose a video, enter or drop a script, and type the target translation language.")
            return
        pipeline = Path(__file__).with_name("subtitle_pipeline.py")
        if not pipeline.is_file():
            QMessageBox.critical(self, APP_NAME, "subtitle_pipeline.py is missing from this folder.")
            return
        output.mkdir(parents=True, exist_ok=True)
        self.active_video = video
        self.active_output = output
        self.output_prefix = f"{video.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.translation_suffix = translation_filename(self.target_language.text().strip())
        self.rendering_manual = False
        script = output / f"{self.output_prefix}_input_script.txt"
        script.write_text(script_text, encoding="utf-8")
        self.project_file = output / f"{self.output_prefix}_subtitle_job.json"
        self.save_project_manifest(script)
        command = [
            sys.executable, str(pipeline), "--video", str(video), "--script", str(script), "--output", str(output),
            "--lm-url", self.lm_url.text().strip(), "--model", self.model.currentText().strip(),
            "--whisper-model", self.whisper.currentText(), "--device", self.device.currentText(),
            "--compute-type", self.compute.currentText(), "--font-size", str(self.font_size.value()),
            "--source-language", str(self.source_language.currentData()),
            "--target-language", self.target_language.text().strip(),
            "--output-prefix", self.output_prefix,
            "--subtitle-font", self.subtitle_font.currentFont().family(),
            "--subtitle-size", str(self.subtitle_size.value()),
            "--subtitle-color", self.text_qcolor.name(),
            "--outline-color", self.outline_qcolor.name(),
            "--outline-width", str(self.outline_width.value()),
            "--subtitle-x", str(self.subtitle_x.value()), "--subtitle-y", str(self.subtitle_y.value()),
        ]
        if self.bold.isChecked():
            command.append("--subtitle-bold")
        if not self.vad_enabled.isChecked():
            command.append("--no-vad")
        vad_threshold = self.vad_threshold.text().strip()
        if self.vad_enabled.isChecked() and vad_threshold:
            try:
                command.extend(["--vad-threshold", str(float(vad_threshold))])
            except ValueError:
                pass  # Unparseable threshold falls back to faster-whisper's default.
        if self.output_mode.currentData() == "manual":
            command.append("--no-burn")
        self.save_settings()
        self.log.clear()
        self.log.appendPlainText("Starting local subtitle pipeline …")
        self.progress.setValue(0)
        self.stage_label.setText("Preparing job …")
        self.started_at = time.monotonic()
        # A rough local estimate; it adjusts as stages are reached and excludes first model downloads.
        self.estimated_seconds = max(45, video.stat().st_size / 1024 / 1024 * (1.2 if self.device.currentText() == "cpu" else 0.45) + 20)
        self.timer.start(1000)
        self.set_running(True)
        self.worker = PipelineWorker(command, output)
        self.worker.log.connect(self.on_log)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def cancel_job(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.cancel_button.setEnabled(False)

    def on_log(self, line: str) -> None:
        self.log.appendPlainText(line)
        if "[1/4]" in line:
            self.progress.setValue(1)
            self.stage_label.setText("1 / 4 · Transcribing audio")
        elif "[2/4]" in line:
            self.progress.setValue(2)
            self.stage_label.setText("2 / 4 · Matching script and translating")
        elif "[3/4]" in line:
            self.progress.setValue(3)
            self.stage_label.setText("3 / 4 · Writing subtitle files")
        elif "[4/4]" in line:
            self.progress.setValue(4)
            self.stage_label.setText("4 / 4 · Burning subtitles into video")
        if self.progress.value() > 0:
            elapsed = time.monotonic() - self.started_at
            self.estimated_seconds = max(self.estimated_seconds, elapsed / (self.progress.value() / 4))

    def on_completed(self, output: str) -> None:
        self.timer.stop()
        self.set_running(False)
        if getattr(self, "rendering_manual", False):
            self.rendering_manual = False
            self.progress.setValue(4)
            self.stage_label.setText("Completed · MP4 rendered from edited SRT")
            self.preview_button.setEnabled(True)
            self.show_preview()
            return
        if self.output_mode.currentData() == "manual":
            self.progress.setValue(3)
            self.stage_label.setText("SRT ready · Edit it, then render the MP4")
            self.edit_srt_button.setEnabled(True)
            self.edit_ass_button.setEnabled((Path(output) / f"{self.output_prefix}_{self.translation_suffix}_styled.ass").is_file())
            if self.auto_unload.isChecked():
                self.release_model_memory()
            self.open_srt_editor(Path(output) / f"{self.output_prefix}_{self.translation_suffix}.srt")
            return
        self.progress.setValue(4)
        self.stage_label.setText("Completed")
        self.timer_label.setText(f"Completed in {self.format_time(time.monotonic() - self.started_at)}")
        video_result = Path(output) / f"{self.output_prefix}_{self.translation_suffix}_subtitled.mp4"
        self.result_file = video_result if video_result.is_file() else Path(output) / f"{self.output_prefix}_{self.translation_suffix}.srt"
        self.download_link.setText(f'<a href="save">Save a copy of {self.result_file.name} to another folder…</a>')
        self.preview_button.setEnabled(video_result.is_file())
        self.edit_srt_button.setEnabled((Path(output) / f"{self.output_prefix}_{self.translation_suffix}.srt").is_file())
        self.edit_ass_button.setEnabled((Path(output) / f"{self.output_prefix}_{self.translation_suffix}_styled.ass").is_file())
        self.statusBar().showMessage("Completed")
        if self.auto_unload.isChecked():
            self.release_model_memory()
        if self.preview_button.isEnabled():
            self.show_preview()
        else:
            QMessageBox.information(self, APP_NAME, f"Completed.\n\nFiles are in:\n{output}")

    def on_failed(self, message: str) -> None:
        self.timer.stop()
        self.set_running(False)
        self.stage_label.setText("Stopped with an error")
        self.statusBar().showMessage("Stopped with an error")
        if self.auto_unload.isChecked():
            self.release_model_memory("Stopped with an error")
        QMessageBox.critical(self, APP_NAME, f"The job did not finish.\n\n{message}\n\nCheck the job log for details.")

    def set_running(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        self.video.setEnabled(not running)
        self.script.setEnabled(not running)
        self.output.setEnabled(not running)
        self.statusBar().showMessage("Running …" if running else "Ready")

    def format_time(self, seconds: float) -> str:
        seconds = max(0, int(seconds))
        return f"{seconds // 60:02}:{seconds % 60:02}"

    def update_timer(self) -> None:
        elapsed = time.monotonic() - self.started_at
        remaining = max(0, self.estimated_seconds - elapsed)
        self.timer_label.setText(f"Elapsed {self.format_time(elapsed)} · Estimated remaining {self.format_time(remaining)} (estimate)")

    def load_script(self, path: str) -> None:
        try:
            if Path(path).suffix.lower() == ".docx":
                from docx import Document
                text = "\n".join(paragraph.text for paragraph in Document(path).paragraphs)
            else:
                text = Path(path).read_text(encoding="utf-8-sig")
            self.script.setPlainText(text)
            self.stage_label.setText(f"Loaded script: {Path(path).name}")
        except Exception as error:
            QMessageBox.warning(self, APP_NAME, f"Could not read script:\n{error}")

    def load_models(self) -> None:
        self.stage_label.setText("Reading LM Studio models …")
        self.models_worker = ModelsWorker(self.lm_url.text())
        self.models_worker.loaded.connect(self.on_models_loaded)
        self.models_worker.failed.connect(lambda error: QMessageBox.warning(self, APP_NAME, f"Could not load LM Studio models:\n{error}"))
        self.models_worker.start()

    def on_models_loaded(self, models: list[str]) -> None:
        current = self.model.currentText()
        self.model.clear()
        self.model.addItems(models)
        self.model.setCurrentText(current if current in models else models[0])
        self.stage_label.setText(f"Loaded {len(models)} model(s) from LM Studio")

    def show_preview(self) -> None:
        video = Path(self.output.text()) / f"{getattr(self, 'output_prefix', '')}_{getattr(self, 'translation_suffix', '')}_subtitled.mp4"
        if video.is_file():
            PreviewDialog(video, self).exec()
        else:
            QMessageBox.information(self, APP_NAME, "No burned-in MP4 is available yet. Turn off ‘SRT only’ and run a job first.")

    def open_srt_editor(self, srt: Path) -> None:
        if not srt.is_file():
            QMessageBox.warning(self, APP_NAME, "English SRT was not created.")
            return
        editor = SrtEditorDialog(srt, self)
        editor.render_requested.connect(self.render_edited_srt)
        editor.exec()

    def render_edited_srt(self) -> None:
        srt = self.active_output / f"{self.output_prefix}_{self.translation_suffix}.srt"
        self.rendering_manual = True
        self.started_at = time.monotonic()
        self.timer.start(1000)
        self.set_running(True)
        self.stage_label.setText("Rendering MP4 from edited SRT …")
        command = [sys.executable, str(Path(__file__).with_name("subtitle_pipeline.py")), "--render-srt", str(srt), "--video", str(self.active_video), "--output", str(self.active_output), "--output-prefix", self.output_prefix, "--target-language", self.target_language.text().strip(), "--subtitle-font", self.subtitle_font.currentFont().family(), "--subtitle-size", str(self.subtitle_size.value()), "--subtitle-color", self.text_qcolor.name(), "--outline-color", self.outline_qcolor.name(), "--outline-width", str(self.outline_width.value()), "--subtitle-x", str(self.subtitle_x.value()), "--subtitle-y", str(self.subtitle_y.value())]
        if self.bold.isChecked(): command.append("--subtitle-bold")
        self.worker = PipelineWorker(command, self.active_output)
        self.worker.log.connect(self.on_log); self.worker.completed.connect(self.on_completed); self.worker.failed.connect(self.on_failed); self.worker.start()

    def render_edited_ass(self, ass: Path) -> None:
        if not getattr(self, "active_video", None):
            QMessageBox.warning(self, APP_NAME, "Edit-and-render ASS is available for the current job. Start a new job if this session was restarted.")
            return
        self.rendering_manual = True
        self.started_at = time.monotonic()
        self.timer.start(1000)
        self.set_running(True)
        self.stage_label.setText("Rendering MP4 from edited ASS …")
        command = [sys.executable, str(Path(__file__).with_name("subtitle_pipeline.py")), "--render-ass", str(ass), "--video", str(self.active_video), "--output", str(self.active_output), "--output-prefix", self.output_prefix, "--target-language", self.target_language.text().strip()]
        self.worker = PipelineWorker(command, self.active_output)
        self.worker.log.connect(self.on_log); self.worker.completed.connect(self.on_completed); self.worker.failed.connect(self.on_failed); self.worker.start()

    def release_model_memory(self, status_prefix: str = "Completed") -> None:
        """Unload only the selected LM Studio model; do not force a DRAM cleanup."""
        model = self.model.currentText().strip()
        if not model:
            return
        self.unload_status_prefix = status_prefix
        self.stage_label.setText(f"{status_prefix} · Unloading LM Studio model to release VRAM …")
        self.unload_worker = UnloadModelWorker(self.lm_url.text(), model)
        self.unload_worker.completed.connect(self.on_model_unloaded)
        self.unload_worker.failed.connect(self.on_unload_failed)
        self.unload_worker.start()

    def on_model_unloaded(self, model: str) -> None:
        prefix = getattr(self, "unload_status_prefix", "Completed")
        self.stage_label.setText(f"{prefix} · Model unloaded: {model}")
        self.log.appendPlainText(f"LM Studio unloaded {model}; model VRAM release was requested.")

    def on_unload_failed(self, error: str) -> None:
        prefix = getattr(self, "unload_status_prefix", "Completed")
        self.stage_label.setText(f"{prefix} · LM Studio model was not unloaded")
        self.log.appendPlainText(f"Could not unload LM Studio model: {error}")

    def save_result_copy(self) -> None:
        result = getattr(self, "result_file", None)
        if not result or not Path(result).is_file():
            return
        target, _ = QFileDialog.getSaveFileName(self, "Save a copy", str(Path.home() / Path(result).name), "Video (*.mp4);;Subtitle (*.srt);;All files (*.*)")
        if target:
            try:
                shutil.copy2(result, target)
                self.stage_label.setText(f"Saved a copy: {Path(target).name}")
            except OSError as error:
                QMessageBox.warning(self, APP_NAME, f"Could not save the copy:\n{error}")

    def open_output(self) -> None:
        folder = Path(self.output.text())
        if folder.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        else:
            QMessageBox.information(self, APP_NAME, "Choose or create an output folder first.")

    def latest_artifact(self, suffix: str) -> Path | None:
        if hasattr(self, "output_prefix"):
            candidate = Path(self.output.text()) / f"{self.output_prefix}{suffix}"
            if candidate.is_file():
                return candidate
        candidates = list(Path(self.output.text()).glob(f"*{suffix}")) if Path(self.output.text()).is_dir() else []
        return max(candidates, key=lambda item: item.stat().st_mtime) if candidates else None

    def edit_srt(self) -> None:
        srt = self.latest_artifact("_translated_*.srt")
        if not srt:
            QMessageBox.information(self, APP_NAME, "No generated SRT file is available yet.")
            return
        self.active_output = Path(self.output.text())
        self.active_video = getattr(self, "active_video", None)
        self.open_srt_editor(srt)

    def edit_ass(self) -> None:
        ass = self.latest_artifact("_translated_*_styled.ass")
        if not ass:
            QMessageBox.information(self, APP_NAME, "No generated ASS file is available yet.")
            return
        editor = AssEditorDialog(ass, self)
        editor.render_requested.connect(lambda: self.render_edited_ass(ass))
        editor.exec()

    def show_about(self) -> None:
        QMessageBox.information(self, APP_NAME, "Local Subtitle Tool\n\nTiming: faster-whisper\nScript matching and translation: LM Studio\nSubtitle rendering: FFmpeg")


def main() -> int:
    qInstallMessageHandler(qt_message_handler)
    app = QApplication(sys.argv)
    font = app.font()
    if font.pointSize() <= 0:
        font.setPointSize(10)
        app.setFont(font)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

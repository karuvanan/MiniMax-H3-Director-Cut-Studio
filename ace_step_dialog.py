"""Native Studio dialog for ACE-Step Music Cover generation."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import threading
from typing import Any, Callable
import uuid

from PySide6.QtCore import QPointF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
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
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ace_step_client import (
    DEFAULT_SERVER,
    download_audio,
    request_json,
    submit_audio_task,
    wait_for_task,
)
from ace_step_runtime import (
    AceStepRuntimeState,
    LOCAL_ACE_SERVER,
    REMOTE_ACE_SERVER,
    install_local_server,
)
from runtime_paths import PROJECT_ROOT, load_runtime_paths


OUTPUT_DIR = PROJECT_ROOT / "outputs" / "ace_step_music_cover"
AUDIO_FILTER = "Audio (*.mp3 *.wav *.flac *.m4a *.aac *.ogg);;All files (*)"
KEY_SCALE_PRESETS = (
    "C major",
    "D♭ major",
    "D major",
    "E♭ major",
    "E major",
    "F major",
    "F♯ major",
    "G major",
    "A♭ major",
    "A major",
    "B♭ major",
    "B major",
    "C minor",
    "C♯ minor",
    "D minor",
    "E♭ minor",
    "E minor",
    "F minor",
    "F♯ minor",
    "G minor",
    "G♯ minor",
    "A minor",
    "B♭ minor",
    "B minor",
)
INSTRUMENT_PRESETS = (
    ("🎹", "Piano", "grand piano"),
    ("🎸", "E. Guitar", "electric guitar"),
    ("🪕", "A. Guitar", "acoustic guitar"),
    ("🎸", "Bass", "electric bass guitar"),
    ("🥁", "Drums", "acoustic drum kit"),
    ("🎛", "Synth", "analog synthesizer"),
    ("🎻", "Violin", "violin"),
    ("🎻", "Cello", "cello"),
    ("🎺", "Trumpet", "trumpet"),
    ("🎷", "Saxophone", "saxophone"),
    ("🪈", "Flute", "concert flute"),
    ("🪉", "Harp", "concert harp"),
    ("胡", "Erhu", "Chinese erhu"),
    ("筝", "Guzheng", "Chinese guzheng"),
    ("琵", "Pipa", "Chinese pipa"),
    ("箏", "Koto", "Japanese koto"),
    ("三", "Shamisen", "Japanese shamisen"),
    ("太", "Taiko", "Japanese taiko drums"),
    ("🪕", "Sitar", "Indian sitar"),
    ("◉", "Tabla", "Indian tabla"),
    ("عود", "Oud", "Middle Eastern oud"),
    ("♬", "Ney", "Middle Eastern ney flute"),
    ("🪘", "Djembe", "West African djembe"),
    ("♫", "Mbira", "African mbira"),
)
VOCAL_PRESETS = (
    ("👦", "小孩子男", "young boy vocal"),
    ("👧", "小孩子女", "young girl vocal"),
    ("👩", "年轻女", "young female vocal"),
    ("👨", "年轻男", "young male vocal"),
    ("👵", "老人女", "elderly female vocal"),
    ("👴", "老人男", "elderly male vocal"),
)
LANGUAGE_FAMILY_PRESETS = (
    ("🌍", "印欧语系", "Indo-European language-family vocal character"),
    ("漢", "汉藏语系", "Sino-Tibetan language-family vocal character"),
    ("🐎", "阿尔泰语系", "Altaic language-family vocal character"),
    ("🏜", "闪含语系", "Afro-Asiatic language-family vocal character"),
    ("❄", "乌拉尔语系", "Uralic language-family vocal character"),
    ("🏔", "高加索语系", "Caucasian language-family vocal character"),
    ("🪷", "南亚语系", "Austroasiatic language-family vocal character"),
    ("🌊", "南岛语系", "Austronesian language-family vocal character"),
)
ANIMAL_SOUND_PRESETS = (
    ("🐦", "chirp", "bird chirps"),
    ("🐔", "cluck", "chicken clucks"),
    ("🐓", "cock-a-doodle-doo", "rooster cock-a-doodle-doo calls"),
    ("🐤", "cuckoo", "cuckoo bird calls"),
    ("🫏", "hee-haw", "donkey hee-haw calls"),
    ("🦉", "hoot", "owl hoots"),
    ("🐈", "meow", "cat meows"),
    ("🐖", "oink", "pig oinks"),
    ("🐄", "moo", "cow moos"),
    ("🐎", "neigh", "horse neighs"),
    ("😺", "purr", "cat purrs"),
    ("🦆", "quack", "duck quacks"),
    ("🐸", "ribbit", "frog ribbits"),
    ("🦁", "roar", "bear or lion roars"),
    ("🐦", "tweet", "bird tweets"),
    ("🐕", "woof", "dog woofs"),
)
MODE_PRESETS = (
    ("Cover", "cover"),
    ("Repaint", "repaint"),
    ("Lego", "lego"),
    ("Extract", "extract"),
)
MODEL_PRESETS = ("acestep-v15-turbo", "acestep-v15-base")
TRACK_PRESETS = (
    "vocals",
    "backing_vocals",
    "drums",
    "bass",
    "guitar",
    "keyboard",
    "percussion",
    "strings",
    "synth",
    "fx",
    "brass",
    "woodwinds",
)
REMIX_PALETTE_START = "[REMIX PALETTE]"
REMIX_PALETTE_END = "[/REMIX PALETTE]"
LEGACY_REMIX_START = "[INSTRUMENT REMIX]"
LEGACY_REMIX_END = "[/INSTRUMENT REMIX]"


def _music_key_notation(value: Any) -> str:
    """Render ASCII accidentals from API metadata as musical glyphs."""

    text = str(value or "").strip().replace("#", "♯")
    for note in "ABCDEFG":
        text = text.replace(f"{note}b", f"{note}♭")
    return text


def _remix_palette_prompt(
    prompt: str,
    instruments: list[str],
    vocals: list[str],
    language_families: list[str],
    animal_sounds: list[str],
) -> str:
    """Replace the managed remix-palette clause while preserving user-authored text."""

    base = str(prompt or "")
    for start, end in (
        (REMIX_PALETTE_START, REMIX_PALETTE_END),
        (LEGACY_REMIX_START, LEGACY_REMIX_END),
    ):
        pattern = re.compile(
            rf"\s*{re.escape(start)}.*?{re.escape(end)}\s*",
            re.DOTALL,
        )
        base = pattern.sub("\n\n", base)
    base = base.strip()
    if not any((instruments, vocals, language_families, animal_sounds)):
        return base
    sections: list[str] = []
    if instruments:
        sections.append(
            "Instrumentation: feature " + ", ".join(instruments)
            + " as clearly audible lead or supporting instruments."
        )
    if vocals:
        sections.append(
            "Vocal casting: feature " + ", ".join(vocals)
            + " with a natural, expressive performance."
        )
    if language_families:
        sections.append(
            "Regional and language-family character: " + ", ".join(language_families)
            + "; reflect the selected phonetic and musical character without stereotypes."
        )
    if animal_sounds:
        sections.append(
            "Animal sound design: integrate " + ", ".join(animal_sounds)
            + " as intentional rhythmic, melodic, or atmospheric accents."
        )
    sections.append(
        "Re-orchestrate the arrangement around the selected palette while preserving the "
        "source melody, tempo, meter, section timing, and harmonic progression."
    )
    clause = f"{REMIX_PALETTE_START}\n" + "\n".join(sections) + f"\n{REMIX_PALETTE_END}"
    return f"{base}\n\n{clause}" if base else clause


def _instrument_remix_prompt(prompt: str, instruments: list[str]) -> str:
    """Compatibility wrapper for instrument-only remix prompts."""

    return _remix_palette_prompt(prompt, instruments, [], [], [])


def _first_output(record: dict[str, Any]) -> dict[str, Any]:
    outputs = record.get("outputs") or []
    if not outputs or not isinstance(outputs[0], dict):
        raise RuntimeError(f"ACE-Step task completed without an output: {record}")
    return dict(outputs[0])


def _apply_volume_gain(
    source: Path,
    target: Path,
    volume_db: float,
    ffmpeg: Path,
) -> None:
    """Apply an audible output gain adjustment with peak protection when boosting."""

    audio_filter = f"volume={volume_db:.2f}dB"
    if volume_db > 0:
        audio_filter += ",alimiter=limit=0.98"
    subprocess.run(
        [
            str(ffmpeg),
            "-y",
            "-i",
            str(source),
            "-vn",
            "-filter:a",
            audio_filter,
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(target),
        ],
        check=True,
        capture_output=True,
    )


def _prepare_source_for_duration(
    source: Path,
    target: Path,
    target_duration: float,
    ffmpeg: Path,
) -> None:
    """Create an exact-length structural guide by trimming or looping source music."""

    subprocess.run(
        [
            str(ffmpeg),
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(source),
            "-t",
            f"{target_duration:.3f}",
            "-map",
            "0:a:0",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(target),
        ],
        check=True,
        capture_output=True,
    )


def _probe_audio_duration(path: Path, ffprobe: Path) -> float:
    """Return the decoded audio duration in seconds."""

    completed = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(completed.stdout.strip())


def _fit_output_duration_and_volume(
    source: Path,
    target: Path,
    target_duration: float,
    volume_db: float,
    ffmpeg: Path,
) -> None:
    """Guarantee exact output length, looping only as a last-resort server fallback."""

    command = [
        str(ffmpeg),
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(source),
        "-t",
        f"{target_duration:.3f}",
        "-vn",
    ]
    audio_filter = ""
    if abs(volume_db) >= 0.01:
        audio_filter = f"volume={volume_db:.2f}dB"
        if volume_db > 0:
            audio_filter += ",alimiter=limit=0.98"
    if audio_filter:
        command.extend(["-filter:a", audio_filter])
    command.extend(["-codec:a", "libmp3lame", "-q:a", "2", str(target)])
    subprocess.run(command, check=True, capture_output=True)


class _BusySpinnerOverlay(QWidget):
    """Semi-transparent modal veil with a lightweight animated spinner."""

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
        self._message = message
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
        inner_radius = 24.0
        outer_radius = 44.0
        for index in range(12):
            step = (index - self._phase) % 12
            alpha = max(45, 255 - step * 18)
            angle = math.radians(index * 30.0 - 90.0)
            start = QPointF(
                center.x() + math.cos(angle) * inner_radius,
                center.y() + math.sin(angle) * inner_radius,
            )
            end = QPointF(
                center.x() + math.cos(angle) * outer_radius,
                center.y() + math.sin(angle) * outer_radius,
            )
            pen = QPen(QColor(74, 218, 232, alpha), 6.0, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(start, end)

        painter.setPen(QColor(245, 249, 255))
        font = QFont(painter.font())
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        text_rect = self.rect().adjusted(24, int(center.y() + 58), -24, -24)
        painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, self._message)


class AceStepMusicCoverDialog(QDialog):
    """Design-style native client for ACE-Step source-audio workflows."""

    job_progress = Signal(str)
    job_succeeded = Signal(str, object)
    job_failed = Signal(str, str)
    runtime_mode_changed = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        runtime_state: AceStepRuntimeState | None = None,
    ) -> None:
        super().__init__(parent)
        self._closed = False
        self._busy = False
        self._threads: set[threading.Thread] = set()
        self._available_models: set[str] = set()
        self.output_path: Path | None = None
        self.runtime_state = runtime_state or AceStepRuntimeState(
            mode="client",
            api_url=REMOTE_ACE_SERVER,
            installed=False,
            gpu_vram_gb=0.0,
            install_eligible=False,
            detail="Client mode",
        )

        self.setWindowTitle("MUSIC WORKBENCH · ACE-Step 1.5")
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        width = min(1180, max(720, (available.width() - 40) if available else 1180))
        height = min(820, max(560, (available.height() - 40) if available else 780))
        self.resize(width, height)
        self.setMinimumSize(720, 560)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)
        scroll.setWidget(page)
        outer.addWidget(scroll)

        connection = QGroupBox("ACE-STEP API CONNECTION")
        connection_layout = QGridLayout(connection)
        self.server_edit = QLineEdit(self.runtime_state.api_url or DEFAULT_SERVER)
        self.server_edit.setObjectName("aceStepApiEdit")
        self.server_edit.setToolTip("Remote ACE-Step API used for analysis and generation")
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Optional")
        self.test_button = QPushButton("TEST API")
        self.test_button.clicked.connect(self.test_connection)
        self.runtime_mode_label = QLabel()
        self.runtime_mode_label.setWordWrap(True)
        self.install_local_button = QPushButton("INSTALL LOCAL ACE-STEP")
        self.install_local_button.clicked.connect(self.install_local_runtime)
        connection_layout.addWidget(QLabel("API"), 0, 0)
        connection_layout.addWidget(self.server_edit, 0, 1, 1, 4)
        connection_layout.addWidget(QLabel("API Key"), 1, 0)
        connection_layout.addWidget(self.api_key_edit, 1, 1, 1, 3)
        connection_layout.addWidget(self.test_button, 1, 4)
        connection_layout.addWidget(self.runtime_mode_label, 2, 0, 1, 4)
        connection_layout.addWidget(self.install_local_button, 2, 4)
        layout.addWidget(connection)

        body = QSplitter(Qt.Horizontal)
        source_group = QGroupBox("REFERENCE AUDIO")
        source_layout = QGridLayout(source_group)
        self.source_edit = QLineEdit()
        self.source_edit.setReadOnly(True)
        self.source_edit.setPlaceholderText("Required · controls melody, rhythm and structure")
        source_browse = QPushButton("UPLOAD SOURCE")
        source_browse.clicked.connect(self.choose_source_audio)
        self.reference_edit = QLineEdit()
        self.reference_edit.setReadOnly(True)
        self.reference_edit.setPlaceholderText("Optional · controls timbre, mix and performance")
        reference_browse = QPushButton("UPLOAD TIMBRE")
        reference_browse.clicked.connect(self.choose_reference_audio)
        self.use_source_reference_check = QCheckBox(
            "Fallback: use source audio for timbre/mix"
        )
        self.use_source_reference_check.setChecked(True)
        self.use_source_reference_check.setToolTip(
            "When no separate timbre reference is uploaded, use the source audio for "
            "both structure and timbre/mix control"
        )
        self.analyze_button = QPushButton("ANALYZE + AUTO FILL")
        self.analyze_button.setStyleSheet("background:#415b8f; font-weight:700;")
        self.analyze_button.clicked.connect(self.analyze_source)
        source_layout.addWidget(QLabel("Source audio"), 0, 0)
        source_layout.addWidget(self.source_edit, 0, 1)
        source_layout.addWidget(source_browse, 0, 2)
        source_layout.addWidget(QLabel("Timbre reference"), 1, 0)
        source_layout.addWidget(self.reference_edit, 1, 1)
        source_layout.addWidget(reference_browse, 1, 2)
        source_layout.addWidget(self.use_source_reference_check, 2, 0, 1, 3)
        source_layout.addWidget(self.analyze_button, 3, 0, 1, 3)
        body.addWidget(source_group)

        settings_group = QGroupBox("MODE SETTINGS")
        settings_layout = QGridLayout(settings_group)
        self.mode_combo = QComboBox()
        for label, task_type in MODE_PRESETS:
            self.mode_combo.addItem(label, task_type)
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODEL_PRESETS)
        self.model_status_label = QLabel("Turbo ready · Base required for Lego / Extract")
        self.model_status_label.setWordWrap(True)
        self.mode_help_label = QLabel()
        self.mode_help_label.setWordWrap(True)

        self.cover_strength_spin = QDoubleSpinBox()
        self.cover_strength_spin.setRange(0.0, 1.0)
        self.cover_strength_spin.setSingleStep(0.05)
        self.cover_strength_spin.setDecimals(2)
        self.cover_strength_spin.setValue(1.0)
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 20)
        self.steps_spin.setValue(8)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 2_147_483_647)
        self.seed_spin.setValue(20_260_913)
        self.random_seed_check = QCheckBox("Random Seed")
        self.random_seed_check.toggled.connect(self.seed_spin.setDisabled)

        self.repaint_start_spin = QDoubleSpinBox()
        self.repaint_start_spin.setRange(0.0, 600.0)
        self.repaint_start_spin.setDecimals(2)
        self.repaint_start_spin.setSuffix(" s")
        self.repaint_end_spin = QDoubleSpinBox()
        self.repaint_end_spin.setRange(0.01, 600.0)
        self.repaint_end_spin.setDecimals(2)
        self.repaint_end_spin.setValue(20.0)
        self.repaint_end_spin.setSuffix(" s")
        self.repaint_mode_combo = QComboBox()
        self.repaint_mode_combo.addItems(["conservative", "balanced", "aggressive"])
        self.repaint_mode_combo.setCurrentText("balanced")
        self.repaint_strength_spin = QDoubleSpinBox()
        self.repaint_strength_spin.setRange(0.0, 1.0)
        self.repaint_strength_spin.setSingleStep(0.05)
        self.repaint_strength_spin.setDecimals(2)
        self.repaint_strength_spin.setValue(0.5)

        self.track_combo = QComboBox()
        self.track_combo.addItems(TRACK_PRESETS)
        self.instruction_edit = QLineEdit()
        self.instruction_edit.setPlaceholderText("ACE-Step task instruction")

        self.cover_strength_label = QLabel("Cover strength")
        self.repaint_start_label = QLabel("Repaint start")
        self.repaint_end_label = QLabel("Repaint end")
        self.repaint_mode_label = QLabel("Repaint mode")
        self.repaint_strength_label = QLabel("Repaint strength")
        self.track_label = QLabel("Track")
        self.instruction_label = QLabel("Instruction")

        settings_layout.addWidget(QLabel("Mode"), 0, 0)
        settings_layout.addWidget(self.mode_combo, 0, 1)
        settings_layout.addWidget(QLabel("Model"), 1, 0)
        settings_layout.addWidget(self.model_combo, 1, 1)
        settings_layout.addWidget(self.model_status_label, 2, 0, 1, 2)
        settings_layout.addWidget(self.cover_strength_label, 3, 0)
        settings_layout.addWidget(self.cover_strength_spin, 3, 1)
        settings_layout.addWidget(QLabel("Steps"), 4, 0)
        settings_layout.addWidget(self.steps_spin, 4, 1)
        settings_layout.addWidget(QLabel("Seed"), 5, 0)
        settings_layout.addWidget(self.seed_spin, 5, 1)
        settings_layout.addWidget(self.random_seed_check, 6, 0, 1, 2)
        settings_layout.addWidget(self.repaint_start_label, 7, 0)
        settings_layout.addWidget(self.repaint_start_spin, 7, 1)
        settings_layout.addWidget(self.repaint_end_label, 8, 0)
        settings_layout.addWidget(self.repaint_end_spin, 8, 1)
        settings_layout.addWidget(self.repaint_mode_label, 9, 0)
        settings_layout.addWidget(self.repaint_mode_combo, 9, 1)
        settings_layout.addWidget(self.repaint_strength_label, 10, 0)
        settings_layout.addWidget(self.repaint_strength_spin, 10, 1)
        settings_layout.addWidget(self.track_label, 11, 0)
        settings_layout.addWidget(self.track_combo, 11, 1)
        settings_layout.addWidget(self.instruction_label, 12, 0)
        settings_layout.addWidget(self.instruction_edit, 12, 1)
        settings_layout.addWidget(self.mode_help_label, 13, 0, 1, 2)
        body.addWidget(settings_group)
        body.setStretchFactor(0, 3)
        body.setStretchFactor(1, 2)
        body.setSizes([720, 340])
        layout.addWidget(body)

        metadata = QGroupBox("EDITABLE ANALYSIS")
        metadata_layout = QGridLayout(metadata)
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText("Analyze source audio or enter a detailed Music Prompt")
        self.prompt_edit.setMinimumHeight(250)
        prompt_splitter = QSplitter(Qt.Horizontal)
        prompt_panel = QWidget()
        prompt_layout = QVBoxLayout(prompt_panel)
        prompt_layout.setContentsMargins(0, 0, 4, 0)
        prompt_layout.addWidget(QLabel("Prompt"))
        prompt_layout.addWidget(self.prompt_edit)
        prompt_panel.setMinimumWidth(480)
        prompt_splitter.addWidget(prompt_panel)

        instrument_group = QGroupBox("REMIX PALETTE · MULTI-SELECT")
        instrument_group.setMinimumWidth(360)
        instrument_group.setMaximumWidth(410)
        instrument_layout = QVBoxLayout(instrument_group)
        instrument_layout.setSpacing(4)
        self.remix_palette_tabs = QTabWidget()
        self.instrument_buttons: dict[str, QToolButton] = {}
        self.vocal_buttons: dict[str, QToolButton] = {}
        self.language_family_buttons: dict[str, QToolButton] = {}
        self.animal_sound_buttons: dict[str, QToolButton] = {}

        def add_palette_tab(
            title: str,
            presets: tuple[tuple[str, str, str], ...],
            target: dict[str, QToolButton],
        ) -> None:
            page = QWidget()
            grid = QGridLayout(page)
            grid.setContentsMargins(4, 4, 4, 4)
            grid.setHorizontalSpacing(4)
            grid.setVerticalSpacing(4)
            for index, (icon, label, prompt_name) in enumerate(presets):
                button = QToolButton()
                button.setText(f"{icon}\n{label}")
                button.setCheckable(True)
                button.setToolTip(f"Add {prompt_name} to the automatic remix")
                button.setFixedSize(86, 54)
                button.setStyleSheet(
                    "QToolButton { border:1px solid #4b5565; border-radius:7px; padding:3px; }"
                    "QToolButton:hover { border-color:#4adae8; background:#263744; }"
                    "QToolButton:checked { border:2px solid #4adae8; background:#176b78; "
                    "color:white; font-weight:700; }"
                )
                button.toggled.connect(self._remix_palette_selection_changed)
                target[prompt_name] = button
                grid.addWidget(button, index // 4, index % 4)
            grid.setRowStretch((len(presets) + 3) // 4, 1)
            self.remix_palette_tabs.addTab(page, title)

        add_palette_tab("乐器", INSTRUMENT_PRESETS, self.instrument_buttons)
        add_palette_tab("人声", VOCAL_PRESETS, self.vocal_buttons)
        add_palette_tab("地区·语系", LANGUAGE_FAMILY_PRESETS, self.language_family_buttons)
        add_palette_tab("动物", ANIMAL_SOUND_PRESETS, self.animal_sound_buttons)
        instrument_layout.addWidget(self.remix_palette_tabs)
        self.remix_selected_button = QPushButton("REMIX SELECTED PALETTE")
        self.remix_selected_button.clicked.connect(self._remix_selected_palette)
        palette_hint = QLabel(
            "Selections do not call the API. Click the button below, or Generate, when ready."
        )
        palette_hint.setWordWrap(True)
        instrument_layout.addWidget(palette_hint)
        instrument_layout.addWidget(self.remix_selected_button)
        prompt_splitter.addWidget(instrument_group)
        prompt_splitter.setCollapsible(0, False)
        prompt_splitter.setCollapsible(1, False)
        prompt_splitter.setStretchFactor(0, 3)
        prompt_splitter.setStretchFactor(1, 2)
        prompt_splitter.setSizes([680, 390])

        self.lyrics_edit = QPlainTextEdit("[Instrumental]")
        self.lyrics_edit.setMinimumHeight(80)
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(1, 300)
        self.bpm_spin.setValue(120)
        self.volume_db_spin = QDoubleSpinBox()
        self.volume_db_spin.setRange(-24.0, 12.0)
        self.volume_db_spin.setSingleStep(0.5)
        self.volume_db_spin.setDecimals(1)
        self.volume_db_spin.setValue(0.0)
        self.volume_db_spin.setSuffix(" dB")
        self.volume_db_spin.setToolTip(
            "Adjust final downloaded audio volume · positive values are peak-limited"
        )
        self.key_edit = QComboBox()
        self.key_edit.setEditable(True)
        self.key_edit.addItems(KEY_SCALE_PRESETS)
        self.key_edit.setCurrentIndex(-1)
        self.key_edit.lineEdit().setPlaceholderText("Select one of 24 keys or type a custom key")
        self.time_signature_edit = QLineEdit("4")
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(10.0, 600.0)
        self.duration_spin.setDecimals(2)
        self.duration_spin.setValue(20.0)
        self.duration_spin.setSuffix(" s")
        self.duration_spin.setToolTip(
            "Exact target output duration · source structure is automatically trimmed or extended"
        )
        metadata_layout.addWidget(prompt_splitter, 0, 0, 1, 10)
        metadata_layout.addWidget(QLabel("Lyrics"), 1, 0)
        metadata_layout.addWidget(self.lyrics_edit, 1, 1, 1, 9)
        metadata_layout.addWidget(QLabel("BPM"), 2, 0)
        metadata_layout.addWidget(self.bpm_spin, 2, 1)
        metadata_layout.addWidget(QLabel("Volume ±"), 2, 2)
        metadata_layout.addWidget(self.volume_db_spin, 2, 3)
        metadata_layout.addWidget(QLabel("Key (♯ / ♭)"), 2, 4)
        metadata_layout.addWidget(self.key_edit, 2, 5)
        metadata_layout.addWidget(QLabel("Time signature"), 2, 6)
        metadata_layout.addWidget(self.time_signature_edit, 2, 7)
        metadata_layout.addWidget(QLabel("Target Duration"), 2, 8)
        metadata_layout.addWidget(self.duration_spin, 2, 9)
        layout.addWidget(metadata)

        action_row = QHBoxLayout()
        self.generate_button = QPushButton("GENERATE COVER")
        self.generate_button.setStyleSheet("background:#156f7a; font-weight:700;")
        self.generate_button.clicked.connect(self.generate_cover)
        action_row.addStretch(1)
        action_row.addWidget(self.generate_button)
        layout.addLayout(action_row)

        output_group = QGroupBox("OUTPUT · PREVIEW AND DOWNLOAD")
        output_layout = QGridLayout(output_group)
        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.play_button = QPushButton("PLAY")
        self.pause_button = QPushButton("PAUSE")
        self.stop_button = QPushButton("STOP")
        self.download_button = QPushButton("DOWNLOAD / SAVE AS")
        self.play_button.clicked.connect(self.play_output)
        self.pause_button.clicked.connect(self.player_pause)
        self.stop_button.clicked.connect(self.player_stop)
        self.download_button.clicked.connect(self.save_output_as)
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.download_button.setEnabled(False)
        output_layout.addWidget(QLabel("Generated audio"), 0, 0)
        output_layout.addWidget(self.output_edit, 0, 1, 1, 4)
        output_layout.addWidget(self.play_button, 1, 1)
        output_layout.addWidget(self.pause_button, 1, 2)
        output_layout.addWidget(self.stop_button, 1, 3)
        output_layout.addWidget(self.download_button, 1, 4)
        layout.addWidget(output_group)

        self.status_label = QLabel(
            f"Ready · {self.runtime_state.mode.upper()} MODE · API: {self.runtime_state.api_url}"
        )
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.status_label)

        raw_group = QGroupBox("COMPLETE API RESPONSE")
        raw_layout = QVBoxLayout(raw_group)
        self.raw_result_edit = QPlainTextEdit()
        self.raw_result_edit.setReadOnly(True)
        self.raw_result_edit.setPlaceholderText("The full ACE-Step task response will appear here")
        self.raw_result_edit.setMinimumHeight(160)
        raw_layout.addWidget(self.raw_result_edit)
        layout.addWidget(raw_group)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("CLOSE")
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)
        layout.addLayout(close_row)

        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.85)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)

        self.busy_overlay = _BusySpinnerOverlay(self)

        self.job_progress.connect(self.status_label.setText)
        self.job_succeeded.connect(self._handle_success)
        self.job_failed.connect(self._handle_failure)
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        self.model_combo.currentTextChanged.connect(self._model_changed)
        self.track_combo.currentTextChanged.connect(self._refresh_task_instruction)
        self.duration_spin.valueChanged.connect(self._duration_changed)
        self._update_runtime_controls()
        self._mode_changed()

    def _server(self) -> str:
        return self.server_edit.text().strip().rstrip("/")

    def _api_key(self) -> str:
        return self.api_key_edit.text().strip()

    def _update_runtime_controls(self) -> None:
        state = self.runtime_state
        if state.mode == "server":
            self.runtime_mode_label.setText(
                f"SERVER MODE · Local ACE-Step · {state.gpu_vram_gb:.1f} GB VRAM · "
                f"{LOCAL_ACE_SERVER}"
            )
            self.runtime_mode_label.setStyleSheet("color:#55d69e; font-weight:700;")
            self.install_local_button.setText("LOCAL SERVER INSTALLED")
            self.install_local_button.setEnabled(False)
            return
        self.runtime_mode_label.setText(
            f"CLIENT MODE · Remote API {REMOTE_ACE_SERVER} · {state.detail}"
        )
        self.runtime_mode_label.setStyleSheet("color:#6ddce8; font-weight:700;")
        if state.install_eligible:
            self.install_local_button.setText("INSTALL LOCAL ACE-STEP")
            self.install_local_button.setEnabled(not self._busy)
        else:
            self.install_local_button.setText("LOCAL INSTALL REQUIRES >16 GB VRAM")
            self.install_local_button.setEnabled(False)

    def install_local_runtime(self) -> None:
        if self.runtime_state.mode == "server":
            return
        if not self.runtime_state.install_eligible:
            QMessageBox.information(
                self,
                "Client Mode",
                "This computer remains a Client. Local ACE-Step installation requires "
                "a GPU with more than 16 GB VRAM.",
            )
            return
        answer = QMessageBox.question(
            self,
            "Install local ACE-Step server",
            f"Detected {self.runtime_state.gpu_vram_gb:.1f} GB VRAM.\n\n"
            "Install the local ACE-Step runtime and Turbo model now? The download can "
            "take several minutes. Nothing is installed unless you choose Yes.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._start_job(
            "installation",
            "Installing local ACE-Step server…",
            lambda: install_local_server(progress=self.job_progress.emit).to_dict(),
        )

    def _task_type(self) -> str:
        return str(self.mode_combo.currentData() or "cover")

    def _refresh_task_instruction(self, _value: str = "") -> None:
        task_type = self._task_type()
        track = self.track_combo.currentText().strip()
        if task_type == "lego":
            self.instruction_edit.setText(
                f"Generate the {track} track based on the audio context:"
            )
        elif task_type == "extract":
            self.instruction_edit.setText(f"Extract the {track} track from the audio:")
        else:
            self.instruction_edit.clear()

    def _model_changed(self, model: str = "") -> None:
        is_base = "base" in str(model or self.model_combo.currentText()).lower()
        previous = self.steps_spin.value()
        self.steps_spin.setMaximum(200 if is_base else 20)
        if is_base and self._task_type() in {"lego", "extract"} and previous <= 20:
            self.steps_spin.setValue(64)
        elif not is_base and previous > 20:
            self.steps_spin.setValue(8)

    def _duration_changed(self, value: float) -> None:
        previous = getattr(self, "_last_duration_value", 20.0)
        repaint_end = self.repaint_end_spin.value()
        if abs(repaint_end - previous) < 0.02 or repaint_end > value:
            self.repaint_end_spin.setValue(value)
        self.repaint_start_spin.setMaximum(max(0.0, value - 0.01))
        self.repaint_end_spin.setMaximum(value)
        self._last_duration_value = value

    def _mode_changed(self, _index: int = -1) -> None:
        task_type = self._task_type()
        is_repaint = task_type == "repaint"
        is_track_mode = task_type in {"lego", "extract"}
        for widget in (self.cover_strength_label, self.cover_strength_spin):
            widget.setVisible(task_type == "cover")
        for widget in (
            self.repaint_start_label,
            self.repaint_start_spin,
            self.repaint_end_label,
            self.repaint_end_spin,
            self.repaint_mode_label,
            self.repaint_mode_combo,
            self.repaint_strength_label,
            self.repaint_strength_spin,
        ):
            widget.setVisible(is_repaint)
        for widget in (
            self.track_label,
            self.track_combo,
            self.instruction_label,
            self.instruction_edit,
        ):
            widget.setVisible(is_track_mode)

        if is_track_mode:
            self.model_combo.setCurrentText("acestep-v15-base")
            self.model_combo.setEnabled(False)
        else:
            self.model_combo.setEnabled(True)
        self._model_changed(self.model_combo.currentText())
        self._refresh_task_instruction()

        button_text = {
            "cover": "GENERATE COVER",
            "repaint": "REPAINT SELECTED SEGMENT",
            "lego": "GENERATE LEGO TRACK",
            "extract": "EXTRACT TRACK",
        }[task_type]
        help_text = {
            "cover": "以源音频控制结构与风格；可另加独立音色参考。",
            "repaint": "只重新生成指定时间段，其余部分尽量保留。",
            "lego": "在源音频上下文中生成一个新轨道 · 首次使用会下载/载入 Base 模型。",
            "extract": "从源混音中提取所选轨道 · 首次使用会下载/载入 Base 模型。",
        }[task_type]
        self.generate_button.setText(button_text)
        self.mode_help_label.setText(help_text)
        self.status_label.setText(
            f"{button_text.title()} ready · API: {self._server()}"
        )

    def _choose_audio(self, target: QLineEdit, title: str) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, title, str(PROJECT_ROOT), AUDIO_FILTER)
        if filename:
            target.setText(filename)

    def choose_source_audio(self) -> None:
        self._choose_audio(self.source_edit, "Choose source audio")

    def choose_reference_audio(self) -> None:
        self._choose_audio(self.reference_edit, "Choose optional timbre reference")

    def _selected_instruments(self) -> list[str]:
        return [
            prompt_name
            for prompt_name, button in self.instrument_buttons.items()
            if button.isChecked()
        ]

    @staticmethod
    def _selected_button_values(buttons: dict[str, QToolButton]) -> list[str]:
        return [name for name, button in buttons.items() if button.isChecked()]

    def _selected_remix_palette(self) -> dict[str, list[str]]:
        return {
            "instruments": self._selected_instruments(),
            "vocals": self._selected_button_values(self.vocal_buttons),
            "language_families": self._selected_button_values(
                self.language_family_buttons
            ),
            "animal_sounds": self._selected_button_values(self.animal_sound_buttons),
        }

    @staticmethod
    def _palette_has_selection(palette: dict[str, list[str]]) -> bool:
        return any(palette.values())

    def _update_remix_palette_prompt(self) -> dict[str, list[str]]:
        selected = self._selected_remix_palette()
        remixed = _remix_palette_prompt(
            self.prompt_edit.toPlainText(),
            selected["instruments"],
            selected["vocals"],
            selected["language_families"],
            selected["animal_sounds"],
        )
        self.prompt_edit.setPlainText(remixed)
        return selected

    def _remix_palette_selection_changed(self, _checked: bool = False) -> None:
        selected = self._update_remix_palette_prompt()
        if not self._palette_has_selection(selected):
            self.status_label.setText("Remix palette cleared")
            return
        names = [name for values in selected.values() for name in values]
        self.status_label.setText(
            f"Palette ready · {', '.join(names)} · no API request sent"
        )

    def _remix_selected_palette(self) -> None:
        selected = self._update_remix_palette_prompt()
        if not self._palette_has_selection(selected):
            QMessageBox.information(
                self,
                "Remix Palette",
                "Select at least one instrument, voice, language family, or animal sound first.",
            )
            return
        self.generate_cover()

    def _set_busy(self, busy: bool, overlay_message: str = "") -> None:
        self._busy = busy
        self.test_button.setEnabled(not busy)
        self.analyze_button.setEnabled(not busy)
        self.generate_button.setEnabled(not busy)
        self.install_local_button.setEnabled(
            not busy
            and self.runtime_state.mode != "server"
            and self.runtime_state.install_eligible
        )
        self.remix_selected_button.setEnabled(not busy)
        for buttons in (
            self.instrument_buttons,
            self.vocal_buttons,
            self.language_family_buttons,
            self.animal_sound_buttons,
        ):
            for button in buttons.values():
                button.setEnabled(not busy)
        if busy and overlay_message:
            self.busy_overlay.start(overlay_message)
        else:
            self.busy_overlay.stop()

    def _start_job(self, kind: str, message: str, operation: Callable[[], object]) -> None:
        if self._busy:
            return
        overlay_message = {
            "analysis": "ANALYZING AUDIO · AUTO-FILLING MUSIC FIELDS…",
            "generation": f"RUNNING {self._task_type().upper()}…",
            "installation": "INSTALLING LOCAL ACE-STEP SERVER…",
        }.get(kind, "")
        self._set_busy(True, overlay_message)
        self.status_label.setText(message)

        def run() -> None:
            try:
                result = operation()
            except Exception as exc:  # network/model failures must reach the UI intact
                if not self._closed:
                    self.job_failed.emit(kind, str(exc))
            else:
                if not self._closed:
                    self.job_succeeded.emit(kind, result)
            finally:
                self._threads.discard(threading.current_thread())

        worker = threading.Thread(target=run, name=f"ace-step-{kind}", daemon=True)
        self._threads.add(worker)
        worker.start()

    @staticmethod
    def _perform_connection(server: str, api_key: str) -> dict[str, Any]:
        health = request_json(server, "health", api_key=api_key, timeout=15)
        try:
            inventory = request_json(
                server, "v1/model_inventory", api_key=api_key, timeout=30
            )
        except Exception as exc:
            inventory = {"inventory_error": str(exc)}
        return {"health": health, "model_inventory": inventory}

    @staticmethod
    def _perform_analysis(source: str, server: str, api_key: str) -> dict[str, Any]:
        task_id = submit_audio_task(
            source,
            server=server,
            task_type="cover",
            full_analysis_only=True,
            api_key=api_key,
        )
        record = wait_for_task(task_id, server=server, api_key=api_key, timeout=3600)
        return {"task_id": task_id, "record": record}

    @staticmethod
    def _ensure_model_loaded(server: str, api_key: str, model: str) -> dict[str, Any]:
        """Load the selected DiT model, downloading it on first use when required."""

        try:
            inventory = request_json(
                server, "v1/model_inventory", api_key=api_key, timeout=30
            )
        except Exception as exc:
            return {"inventory_error": str(exc), "initialized": False}
        records = ((inventory.get("data") or {}).get("models") or [])
        selected = next(
            (
                record
                for record in records
                if isinstance(record, dict) and record.get("name") == model
            ),
            None,
        )
        if selected and selected.get("is_loaded"):
            return {"inventory": inventory, "initialized": False}
        initialized = request_json(
            server,
            "v1/init",
            api_key=api_key,
            payload={"model": model, "slot": 1, "init_llm": False},
            timeout=1800,
        )
        if initialized.get("code") not in {None, 200} or initialized.get("error"):
            raise RuntimeError(f"ACE-Step could not load {model}: {initialized}")
        return {
            "inventory_before": inventory,
            "initialized": True,
            "init_response": initialized,
        }

    @staticmethod
    def _perform_generation(request: dict[str, Any]) -> dict[str, Any]:
        source = str(request["source"])
        task_type = str(request.get("task_type") or "cover")
        model = str(request.get("model") or "acestep-v15-turbo")
        api_key = str(request.get("api_key") or "")
        server = str(request["server"])
        model_setup = AceStepMusicCoverDialog._ensure_model_loaded(
            server, api_key, model
        )
        target_duration = max(10.0, min(600.0, float(request["duration"])))
        runtime = load_runtime_paths()
        separate_reference = str(request.get("reference") or "")
        reference = None
        if task_type in {"cover", "repaint"}:
            reference = separate_reference or (
                source if request.get("use_source_reference", True) else None
            )
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        prepared_source = OUTPUT_DIR / f".duration_guide_{uuid.uuid4().hex}.wav"
        try:
            _prepare_source_for_duration(
                Path(source),
                prepared_source,
                target_duration,
                runtime.ffmpeg,
            )
            task_id = submit_audio_task(
                prepared_source,
                server=server,
                prompt=str(request["prompt"]),
                lyrics=str(request["lyrics"]),
                task_type=task_type,
                model=model,
                instruction=str(request.get("instruction") or ""),
                track_name=str(request.get("track_name") or ""),
                cover_strength=float(request["cover_strength"]),
                repainting_start=float(request.get("repainting_start") or 0.0),
                repainting_end=request.get("repainting_end"),
                chunk_mask_mode=str(request.get("chunk_mask_mode") or "auto"),
                repaint_mode=str(request.get("repaint_mode") or "balanced"),
                repaint_strength=float(request.get("repaint_strength") or 0.5),
                reference_audio=reference,
                bpm=int(request["bpm"]),
                key_scale=str(request["key_scale"]),
                time_signature=str(request["time_signature"]),
                audio_duration=target_duration,
                inference_steps=int(request["steps"]),
                seed=None if request.get("random_seed") else int(request["seed"]),
                api_key=api_key,
            )
            record = wait_for_task(
                task_id,
                server=server,
                api_key=api_key,
                timeout=3600,
            )
        finally:
            prepared_source.unlink(missing_ok=True)
        result = _first_output(record)
        file_url = str(result.get("file") or "")
        if not file_url:
            raise RuntimeError(f"ACE-Step returned no audio URL: {result}")
        output_path = OUTPUT_DIR / f"ace_{task_type}_{task_id[:8]}.mp3"
        volume_db = float(request.get("volume_db") or 0.0)
        raw_path = OUTPUT_DIR / f"ace_{task_type}_{task_id[:8]}_api.mp3"
        download_audio(
            file_url,
            raw_path,
            server=server,
            api_key=api_key,
        )
        try:
            api_duration = _probe_audio_duration(raw_path, runtime.ffprobe)
            duration_adjusted = abs(api_duration - target_duration) > 0.15
            if duration_adjusted or abs(volume_db) >= 0.01:
                _fit_output_duration_and_volume(
                    raw_path,
                    output_path,
                    target_duration,
                    volume_db,
                    runtime.ffmpeg,
                )
            else:
                raw_path.replace(output_path)
        finally:
            raw_path.unlink(missing_ok=True)
        return {
            "task_id": task_id,
            "record": record,
            "output_path": str(output_path),
            "volume_db": volume_db,
            "target_duration": target_duration,
            "api_duration": api_duration,
            "duration_adjusted": duration_adjusted,
            "task_type": task_type,
            "model": model,
            "model_setup": model_setup,
        }

    def test_connection(self) -> None:
        server = self._server()
        if not server:
            QMessageBox.information(self, "ACE-Step API", "Enter the API address first.")
            return
        api_key = self._api_key()
        self._start_job(
            "connection",
            f"Testing ACE-Step API · {server}",
            lambda: self._perform_connection(server, api_key),
        )

    def analyze_source(self) -> None:
        source = self.source_edit.text().strip()
        server = self._server()
        if not source or not Path(source).is_file():
            QMessageBox.information(self, "Music Cover", "Upload a valid source audio file first.")
            return
        if not server:
            QMessageBox.information(self, "ACE-Step API", "Enter the API address first.")
            return
        api_key = self._api_key()
        self._start_job(
            "analysis",
            f"Analyzing source audio through {server}…",
            lambda: self._perform_analysis(source, server, api_key),
        )

    def generate_cover(self) -> None:
        source = self.source_edit.text().strip()
        reference = self.reference_edit.text().strip()
        self._update_remix_palette_prompt()
        prompt = self.prompt_edit.toPlainText().strip()
        task_type = self._task_type()
        model = self.model_combo.currentText().strip()
        if not source or not Path(source).is_file():
            QMessageBox.information(self, "Music Cover", "Upload a valid source audio file first.")
            return
        if reference and not Path(reference).is_file():
            QMessageBox.information(self, "Music Cover", "The timbre reference file is not valid.")
            return
        if not prompt:
            QMessageBox.information(self, "ACE-Step", "Analyze the audio or enter a Prompt first.")
            return
        if task_type in {"lego", "extract"} and "base" not in model.lower():
            QMessageBox.warning(
                self,
                "Base model required",
                "Lego and Extract require acestep-v15-base.",
            )
            return
        repaint_start = self.repaint_start_spin.value()
        repaint_end = self.repaint_end_spin.value()
        if task_type == "repaint" and repaint_end <= repaint_start:
            QMessageBox.information(
                self,
                "Invalid repaint range",
                "Repaint end must be later than Repaint start.",
            )
            return
        request = {
            "source": source,
            "reference": reference,
            "use_source_reference": self.use_source_reference_check.isChecked(),
            "prompt": prompt,
            "lyrics": self.lyrics_edit.toPlainText().strip() or "[Instrumental]",
            "bpm": self.bpm_spin.value(),
            "volume_db": self.volume_db_spin.value(),
            "key_scale": _music_key_notation(self.key_edit.currentText()),
            "time_signature": self.time_signature_edit.text().strip() or "4",
            "duration": self.duration_spin.value(),
            "cover_strength": self.cover_strength_spin.value(),
            "task_type": task_type,
            "model": model,
            "instruction": self.instruction_edit.text().strip(),
            "track_name": self.track_combo.currentText().strip() if task_type in {"lego", "extract"} else "",
            "repainting_start": repaint_start,
            "repainting_end": repaint_end if task_type == "repaint" else None,
            "chunk_mask_mode": "explicit" if task_type == "repaint" else "auto",
            "repaint_mode": self.repaint_mode_combo.currentText(),
            "repaint_strength": self.repaint_strength_spin.value(),
            "steps": self.steps_spin.value(),
            "random_seed": self.random_seed_check.isChecked(),
            "seed": self.seed_spin.value(),
            "server": self._server(),
            "api_key": self._api_key(),
        }
        if not request["server"]:
            QMessageBox.information(self, "ACE-Step API", "Enter the API address first.")
            return
        self._start_job(
            "generation",
            f"Running {task_type.title()} through {request['server']}…",
            lambda: self._perform_generation(request),
        )

    def _show_record(self, record: dict[str, Any]) -> None:
        self.raw_result_edit.setPlainText(json.dumps(record, ensure_ascii=False, indent=2, default=str))

    @staticmethod
    def _number(value: Any, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _handle_success(self, kind: str, payload: object) -> None:
        self._set_busy(False)
        data = dict(payload) if isinstance(payload, dict) else {}
        if kind == "installation":
            self.runtime_state = AceStepRuntimeState(
                mode=str(data.get("mode") or "server"),
                api_url=str(data.get("api_url") or LOCAL_ACE_SERVER),
                installed=bool(data.get("installed", True)),
                gpu_vram_gb=self._number(data.get("gpu_vram_gb"), 0.0),
                install_eligible=bool(data.get("install_eligible", True)),
                detail=str(data.get("detail") or "Local ACE-Step server installed"),
            )
            self.server_edit.setText(self.runtime_state.api_url)
            self._update_runtime_controls()
            self._show_record(data)
            self.status_label.setText(
                f"Local ACE-Step installed · SERVER MODE · {self.runtime_state.api_url}"
            )
            self.runtime_mode_changed.emit(self.runtime_state)
            return
        if kind == "connection":
            self._show_record(data)
            health_response = data.get("health") or data
            health = health_response.get("data") or {}
            service = health.get("service", "ACE-Step") if isinstance(health, dict) else "ACE-Step"
            version = health.get("version", "") if isinstance(health, dict) else ""
            inventory_response = data.get("model_inventory") or {}
            inventory = inventory_response.get("data") or {}
            model_records = inventory.get("models") or [] if isinstance(inventory, dict) else []
            self._available_models = {
                str(record.get("name") or "")
                for record in model_records
                if isinstance(record, dict) and record.get("name")
            }
            if "acestep-v15-base" in self._available_models:
                self.model_status_label.setText("Turbo + Base available")
                self.model_status_label.setStyleSheet("color:#55d69e;")
            elif self._available_models:
                self.model_status_label.setText(
                    "Base not loaded · first Lego / Extract run will download/load it"
                )
                self.model_status_label.setStyleSheet("color:#ffb45b;")
            self.status_label.setText(
                f"Connected · {self._server()} · {service} {version} · "
                f"Models: {', '.join(sorted(self._available_models)) or 'unknown'}".strip()
            )
            return

        record = data.get("record") or {}
        result = _first_output(record)
        task_id = str(data.get("task_id") or "")
        if kind == "analysis":
            self._show_record(record)
            self.prompt_edit.setPlainText(str(result.get("prompt") or ""))
            self._update_remix_palette_prompt()
            self.lyrics_edit.setPlainText(str(result.get("lyrics") or "[Instrumental]"))
            self.bpm_spin.setValue(round(self._number(result.get("bpm"), 120)))
            self.key_edit.setCurrentText(_music_key_notation(result.get("keyscale")))
            self.time_signature_edit.setText(str(result.get("timesignature") or "4"))
            self.duration_spin.setValue(self._number(result.get("duration"), 20.0))
            self.status_label.setText(
                f"Analysis complete · API {self._server()} · task {task_id}"
            )
            return

        self._show_record(
            {
                "model_setup": data.get("model_setup") or {},
                "task_response": record,
            }
        )
        output_path = Path(str(data.get("output_path") or ""))
        self.output_path = output_path
        self.output_edit.setText(str(output_path))
        self.player.setSource(QUrl.fromLocalFile(str(output_path)))
        for button in (
            self.play_button,
            self.pause_button,
            self.stop_button,
            self.download_button,
        ):
            button.setEnabled(True)
        volume_db = self._number(data.get("volume_db"), 0.0)
        target_duration = self._number(data.get("target_duration"), 0.0)
        task_type = str(data.get("task_type") or "cover")
        model = str(data.get("model") or "")
        self.status_label.setText(
            f"{task_type.title()} complete · {model} · Target {target_duration:.2f}s · "
            f"Volume {volume_db:+.1f} dB · "
            f"API {self._server()} · task {task_id}"
        )

    def _handle_failure(self, kind: str, message: str) -> None:
        self._set_busy(False)
        title = {
            "connection": "ACE-Step connection failed",
            "analysis": "ACE-Step analysis failed",
            "generation": "ACE-Step generation failed",
            "installation": "Local ACE-Step installation failed",
        }.get(kind, "ACE-Step error")
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
            f"Save {self._task_type().title()} Audio",
            str(self.output_path),
            AUDIO_FILTER,
        )
        if not filename:
            return
        target = Path(filename)
        if target.resolve() != self.output_path.resolve():
            shutil.copy2(self.output_path, target)
        self.status_label.setText(f"Saved {self._task_type().title()} audio · {target}")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "busy_overlay"):
            self.busy_overlay.setGeometry(self.rect())

    def closeEvent(self, event) -> None:  # noqa: N802
        self._closed = True
        self.busy_overlay.stop()
        self.player.stop()
        super().closeEvent(event)

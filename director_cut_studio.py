"""Premiere-inspired PySide6 workspace for MiniMax H3 reference-to-video."""

from __future__ import annotations

import faulthandler
from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import traceback
from urllib.parse import urlparse

from PySide6.QtCore import (
    QEvent, QEasingCurve, QMimeData, QObject, QPoint, QRectF, QSize, Qt,
    QTimer, QUrl, QVariantAnimation, Signal,
)
from PySide6.QtGui import QBrush, QColor, QDrag, QIcon, QImage, QKeySequence, QPainter, QPen, QPixmap, QPolygon, QUndoCommand, QUndoStack
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QListView,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QToolBar,
    QToolTip,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from blip_summary import (
    clean_blip_caption,
    remove_previous_blip_output,
    render_blip_summary,
)
from media_engine import (
    media_type_for_path,
    probe_media,
)
from audio_engine import evaluate_native_audio_qc
from native_audio_engine import (
    NativeAudioProfile,
    audio_reference_intent_text,
    build_native_audio_profile,
    environment_continuity_text,
    native_audio_direction_text,
)
from media_semantic_enrichment import (
    MEDIA_SEMANTIC_ENRICHMENT_SCHEMA,
    build_enrichment_job_context,
    build_media_enrichment_prompts,
    enrichment_fingerprint,
    normalize_semantic_enrichment,
    render_semantic_enrichment,
)
from design_engine import (
    DESIGN_JSON_SCHEMA,
    H3_STABLE_DIALOGUE_LANGUAGES,
    DesignDialogueLanguageContractError,
    DesignDurationContractError,
    DesignJSONDecodeError,
    DesignSpeechLayerContractError,
    automatic_background_music,
    automatic_background_soundscape,
    authored_text_layers_with_plan_assignments,
    build_design_system_prompt,
    collect_design_preflight_blockers,
    enforce_design_dialogue_language,
    enforce_design_music_mode,
    enforce_design_subtitle_policy,
    extract_explicit_timed_text_layers,
    infer_design_dialogue_language,
    infer_explicit_design_duration,
    is_drone_special_skill,
    is_analysis_only_media_use,
    materialize_design_media,
    normalize_shot_action_budget,
    normalize_design_plan,
    normalize_design_music_mode,
    protect_explicit_timed_text_layers,
    reconcile_requested_speech_layer_contract,
    requested_speech_roles,
    sanitize_drone_still_image_request,
    SPEECH_TIMELINE_MARKER_PREFIX,
    SPEECH_TIMELINE_REMINDER_PREFIX,
    speech_timing_budget,
    spatial_acoustics_profile,
    validate_explicit_timed_text_contract,
    validate_requested_speech_layer_contract,
)
from design_settings import DesignAISettings, load_design_settings, save_design_settings
from smart_cut_engine import (
    SMART_CUT_MODES,
    normalize_lm_hints,
    plan_smart_cut,
    smart_cut_lm_prompts,
    smart_cut_lm_schema,
)
from prompt_engine import PromptSpec, split_shots
from prompt_presets import (
    CONSTRAINT_PRESETS,
    CREATIVE_BRIEF_PRESETS,
    MARKER_RECOMMENDATIONS,
    MUSIC_PRESETS,
    SHOT_RECOMMENDATIONS,
    SOUNDSCAPE_PRESETS,
    TRANSITION_RECOMMENDATIONS,
    TRANSITION_STYLE_PRESETS,
    VISUAL_STYLE_PRESETS,
)
from prompt_preset_store import (
    PromptPresetRecord,
    delete_prompt_preset,
    ensure_prompt_presets,
    load_prompt_presets,
    save_prompt_preset,
)
from project_workspace import (
    QUALITY_PROFILES,
    WORKSPACE_LAYOUT_VERSION,
    allocate_workspace_root,
    ensure_workspace_layout,
    estimate_resources,
    link_or_copy,
    locate_workspace_for_project,
    migrate_legacy_shot_takes,
    next_design_revision,
    normalize_segment_take_states,
    normalize_shot_take_states,
    design_requirement_project_name,
    picture_overview_project_name,
    project_display_name_for_plan,
    refine_provisional_workspace_root,
    rebase_workspace_take_states,
    record_segment_take,
    clear_shot_segment_refs_for_window,
    slugify_project_name,
    workspace_folder_name,
    update_resource_calibration,
    utc_now_text,
    write_shot_manifests,
    workspace_project_path,
)
from project_storage import (
    archive_workspace,
    build_storage_report,
    safe_cleanup_plan,
    safe_cleanup_workspace,
)
from project_integrity import repair_project_payload, repair_speech_timing_payload
from runtime_paths import PROJECT_ROOT, load_runtime_paths
from settings_engine import RenderSettings, load_settings, save_settings
from version_info import APP_VERSION, PROJECT_FORMAT_VERSION
from qwen3_tts_runtime import (
    QWEN3_TTS_MODEL_DIR,
    QWEN3_TTS_RUNTIME_DIR,
    qwen3_tts_missing_message,
    qwen3_tts_model_missing,
    qwen3_tts_runtime_missing,
    qwen3_tts_support_missing,
)
from voxcpm_runtime import (
    VOXCPM_MODEL_DIR,
    voxcpm_missing_message,
    voxcpm_model_missing,
)
from skill_engine import (
    DEFAULT_SKILL,
    NONE_SPECIAL,
    build_ref2va_prompt,
    load_skill_profiles,
)
from special_skill_store import (
    DEFAULT_SPECIAL_SKILL_BODY,
    SpecialSkillDocument,
    load_special_skill_document,
    render_special_skill,
    save_special_skill_document,
)
from segment_engine import (
    MAX_NATIVE_SECONDS,
    align_segments_to_dialogue_turns,
    content_fingerprint,
    derive_named_segment_seed,
    plan_render_segments,
    plan_shot_render_segments,
    protect_segment_boundaries_from_speech,
    ranges_intersect,
    scope_timed_prompt_text,
)
from workflow_engine import (
    MediaAsset,
    WorkflowScan,
    assign_local_media,
    compile_active_workflow,
    create_virtual_media_asset,
    effective_reference_assets,
    load_workflow,
    media_upload_manifest,
    patch_media_upload_names,
    stable_reference_id,
    validate_portable_media_manifest,
)


LATEST_WORKFLOW = PROJECT_ROOT / "video_minimax_h3_r2v_9image_3audio_3video_api.json"
CACHE_ROOT = PROJECT_ROOT / ".director_cache"
SETTINGS_ENV = PROJECT_ROOT / ".env"
DESIGN_SETTINGS_ENV = PROJECT_ROOT / "design_ai.env"
DESIGN_EXAMPLE_ROOT = PROJECT_ROOT / "example"
Z_IMAGE_WORKFLOW = PROJECT_ROOT / "Z-Image_Text2Image_for_webui_t2i_api.json"
PROMPT_PRESET_ENV_ROOT = PROJECT_ROOT / "preset_env"
MIME_SLOT = "application/x-h3-media-slot"
MEDIA_POOL_COLUMNS = 3
MEDIA_CARD_MIN_WIDTH = 80


def _canonical_special_skill_key(value: object) -> str:
    """Migrate historical Special Skill keys without breaking saved projects."""

    key = str(value or "").strip()
    if key.casefold() == "dark-rescue-h3-no-pov":
        return "dark-rescue-h3-no-pov"
    return key


def _bound_special_skill_key(context: dict | None) -> str:
    """Return the selected Special Skill key from a Design context."""

    bound = (context or {}).get("bound_h3_skills") or {}
    special = bound.get("special") or {}
    return _canonical_special_skill_key(special.get("key", ""))
TIMELINE_RULER_HEIGHT = 20
RENDER_STATUS_BAR_HEIGHT = 6
DIRECTOR_LANE_HEIGHT = 20
DIRECTOR_LANE_TYPES = ("shot", "transition", "marker")
DIRECTOR_LANES_TOP = TIMELINE_RULER_HEIGHT + RENDER_STATUS_BAR_HEIGHT
TIMELINE_TRACKS_TOP = DIRECTOR_LANES_TOP + DIRECTOR_LANE_HEIGHT * len(DIRECTOR_LANE_TYPES)
TIMELINE_SNAP_SECONDS = 0.5
# The Work Area end is also a deliberate manual Timeline-extension control.
# Keep it independent from the currently loaded endpoint so a new 12-second
# project can be expanded to 45s, 120s or a future long-form duration directly
# from the Generation toolbar.  Six hours remains safely inside Qt's
# millisecond slider integer range while covering the planned 90-minute mode.
MAX_MANUAL_TIMELINE_SECONDS = 6.0 * 60.0 * 60.0
SMART_RENDER_POLICY_VERSION = 16

_UNTRACKED_VISIBLE_TEXT_TOKEN_RE = re.compile(
    r"\b(?:text|words?|subtitle|caption|title|lower[- ]?third|hashtag|typography|legible)\b|"
    r"字幕|文字|字样|字樣|标题|標題|可读|可讀",
    re.I,
)
_VISIBLE_DISPLAY_CONTEXT_RE = re.compile(
    r"\b(?:screen|monitor|display|overlay|visible|show|render|appear|reveal|center)\b|"
    r"屏幕|螢幕|画面|畫面|显示|顯示|出现|出現|呈现|呈現|中央",
    re.I,
)
_QUOTED_VISIBLE_WORD_RE = re.compile(
    r"(?:['\"‘“「『《])"
    r"[^'\"‘’“”「」『』《》]{1,120}"
    r"(?:['\"’”」』》])"
)


def strip_untracked_visible_text_directions(value: object) -> str:
    """Remove visible-word requests unless a Timeline on_screen_text layer owns them."""
    clauses = re.split(
        r"(?<=[.!?;])\s+|(?<=[。！？；])\s*|\n+",
        str(value or "").strip(),
    )
    return " ".join(
        clause.strip()
        for clause in clauses
        if clause.strip()
        and clause.strip(" \t\r\n'\"‘’“”「」『』《》")
        and not (
            (
                _UNTRACKED_VISIBLE_TEXT_TOKEN_RE.search(clause)
                and _VISIBLE_DISPLAY_CONTEXT_RE.search(clause)
            )
            or _QUOTED_VISIBLE_WORD_RE.search(clause)
        )
    ).strip()
CONTINUITY_MODE_LABELS = (
    "Auto", "Hard Cut", "Match Action", "Motion Reference", "Transition",
)


def snap_timeline_seconds(seconds: float, duration: float | None = None) -> float:
    """Quantize a timeline position to the nearest half-second grid line."""
    value = max(0.0, float(seconds))
    snapped = int(value / TIMELINE_SNAP_SECONDS + 0.5) * TIMELINE_SNAP_SECONDS
    if duration is not None:
        snapped = min(max(0.0, float(duration)), snapped)
    return round(snapped, 6)


def snap_timeline_range(
    start_seconds: float,
    end_seconds: float,
    duration: float,
) -> tuple[float, float]:
    """Snap both interval edges while preserving at least one timeline cell."""
    duration = max(TIMELINE_SNAP_SECONDS, float(duration))
    start = snap_timeline_seconds(start_seconds, duration)
    end = snap_timeline_seconds(end_seconds, duration)
    if end - start < TIMELINE_SNAP_SECONDS:
        if start + TIMELINE_SNAP_SECONDS <= duration:
            end = start + TIMELINE_SNAP_SECONDS
        else:
            end = duration
            start = max(0.0, end - TIMELINE_SNAP_SECONDS)
    return round(start, 6), round(end, 6)


def media_shortcut(asset: MediaAsset) -> str:
    """Return a compact UI label without changing the API reference tag."""
    return stable_reference_id(asset)


def resolve_project_media_path(
    project_path: Path,
    saved: dict,
    saved_work_dir: Path | None = None,
) -> Path | None:
    """Recover a saved media path after a portable project folder is moved."""
    project_dir = project_path.expanduser().resolve().parent
    # Canonical workspaces store the JSON in ``Workspace/project`` while
    # media lives in sibling trees such as ``Workspace/media/generated_references``.
    # Searching only below the JSON directory made every copied generated
    # reference look missing even though it was visible in the Media Pool.
    workspace_dir = (
        project_dir.parent
        if project_dir.name.casefold() == "project"
        else project_dir
    )
    search_roots = list(dict.fromkeys((project_dir, workspace_dir)))
    raw_path = str(saved.get("local_path") or "").strip()
    filename = str(saved.get("filename") or "").strip()
    original = Path(raw_path).expanduser() if raw_path else None
    candidates: list[Path] = []
    if original is not None:
        candidates.append(original)
    if original is not None and saved_work_dir:
        try:
            relative = original.relative_to(saved_work_dir)
        except (ValueError, OSError):
            relative = None
        if relative is not None:
            candidates.extend(root / relative for root in search_roots)
    if filename:
        candidates.extend(root / filename for root in search_roots)
    if original is not None and original.name:
        candidates.extend(root / original.name for root in search_roots)

    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(str(candidate))
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_file():
            return candidate.resolve()

    basename = filename or (original.name if original is not None else "")
    if basename:
        matches: list[Path] = []
        matched_keys: set[str] = set()
        for root in search_roots:
            for item in root.rglob(basename):
                if not item.is_file():
                    continue
                key = os.path.normcase(str(item.resolve()))
                if key not in matched_keys:
                    matched_keys.add(key)
                    matches.append(item)
        if len(matches) == 1:
            return matches[0].resolve()
    return None


def canonicalize_cue_reference_ids(text: str, media_ids: object) -> str:
    """Add ``@`` to explicit stable IDs owned by one Director Cue.

    Older AI Enrichment results wrote ``P3`` inside Shot prose while keeping
    ``P3`` as the cue's structured reference key. Bare IDs are not globally
    rewritten because values such as product model ``A1`` may be literal text;
    the cue-owned key makes this targeted migration unambiguous.
    """
    result = str(text or "")
    for raw_media_id in media_ids or []:
        media_id = str(raw_media_id).strip().upper().lstrip("@")
        if not re.fullmatch(r"[PVA]\d+", media_id):
            continue
        result = re.sub(
            rf"(?<![@\w]){re.escape(media_id)}(?!\w)",
            f"@{media_id}",
            result,
            flags=re.I,
        )
    return result


APP_STYLE = """
QWidget { background: #181a1d; color: #d8d8d8; font-family: "Segoe UI"; font-size: 12px; }
QMainWindow, QDialog { background: #111315; }
QToolBar { background: #202327; border: 0; border-bottom: 1px solid #050607; spacing: 7px; padding: 5px; }
QPushButton { background: #30343a; border: 1px solid #444951; border-radius: 3px; padding: 6px 10px; }
QPushButton:hover { background: #3c4148; border-color: #646b75; }
QPushButton:pressed, QPushButton:checked { background: #137d91; border-color: #28b5cc; color: white; }
QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit { background: #282b30; border: 1px solid #444951; border-radius: 3px; padding: 4px 7px; }
QPlainTextEdit { background: #111315; border: 1px solid #30343a; selection-background-color: #187f93; }
QTabWidget::pane { border: 1px solid #2e3237; }
QTabBar::tab { background: #23262a; padding: 7px 12px; border-right: 1px solid #101214; }
QTabBar::tab:selected { background: #34383e; border-top: 2px solid #38a9bd; }
QGroupBox { border: 1px solid #30343a; margin-top: 8px; padding-top: 8px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QScrollArea { border: 0; }
QSplitter::handle { background: #08090a; width: 3px; height: 3px; }
QSlider::groove:horizontal { height: 4px; background: #393d43; }
QSlider::handle:horizontal { width: 12px; margin: -5px 0; background: #52c4d8; border-radius: 6px; }
"""


def _media_filter(kind: str) -> str:
    return {
        "image": "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff)",
        "video": "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.m4v)",
        "audio": "Audio (*.wav *.mp3 *.aac *.m4a *.flac *.ogg *.opus)",
    }[kind]


def _asset_color(kind: str) -> QColor:
    return {
        "image": QColor("#7864c9"),
        "video": QColor("#3978ba"),
        "audio": QColor("#258a70"),
    }.get(kind, QColor("#5f6670"))


def editor_icon(name: str, color: str = "#d8dde3") -> QIcon:
    """Draw small dependency-free editor icons that stay crisp in dark UI."""
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    if name == "selection":
        painter.setBrush(QColor(color))
        painter.drawPolygon(QPolygon([QPoint(5, 3), QPoint(18, 13), QPoint(11, 14), QPoint(8, 21)]))
    elif name == "type":
        painter.drawLine(5, 5, 19, 5)
        painter.drawLine(12, 5, 12, 20)
        painter.drawLine(8, 20, 16, 20)
    elif name == "prompt":
        painter.drawRoundedRect(3, 4, 18, 14, 3, 3)
        painter.drawLine(8, 18, 6, 22)
        for x in (8, 12, 16):
            painter.drawPoint(x, 11)
    elif name == "hand":
        painter.drawLine(7, 12, 7, 7)
        painter.drawLine(10, 12, 10, 4)
        painter.drawLine(13, 12, 13, 3)
        painter.drawLine(16, 13, 16, 6)
        painter.drawLine(7, 11, 4, 10)
        painter.drawLine(4, 10, 4, 13)
        painter.drawLine(4, 13, 9, 20)
        painter.drawLine(9, 20, 17, 20)
        painter.drawLine(17, 20, 20, 13)
        painter.drawLine(20, 13, 20, 9)
        painter.drawLine(20, 9, 18, 8)
    elif name == "razor":
        painter.drawLine(4, 18, 18, 4)
        painter.drawLine(6, 20, 20, 6)
        painter.drawLine(4, 18, 9, 21)
        painter.drawLine(18, 4, 21, 9)
    elif name == "shot":
        painter.drawRect(3, 5, 18, 14)
        painter.drawLine(8, 5, 8, 19)
        painter.drawLine(16, 5, 16, 19)
        painter.drawLine(3, 10, 21, 10)
    elif name == "transition":
        painter.drawRect(3, 6, 10, 12)
        painter.drawRect(11, 6, 10, 12)
        painter.drawLine(9, 4, 15, 20)
    elif name == "marker":
        painter.setBrush(QColor(color))
        painter.drawPolygon(QPolygon([QPoint(6, 3), QPoint(18, 3), QPoint(18, 15), QPoint(12, 21), QPoint(6, 15)]))
    elif name == "track_add":
        painter.drawRect(3, 6, 18, 12)
        painter.drawLine(12, 8, 12, 16)
        painter.drawLine(8, 12, 16, 12)
    elif name == "track_delete":
        painter.drawRect(6, 8, 12, 12)
        painter.drawLine(5, 6, 19, 6)
        painter.drawLine(9, 3, 15, 3)
        painter.drawLine(10, 10, 10, 17)
        painter.drawLine(14, 10, 14, 17)
    elif name == "power":
        painter.drawArc(5, 5, 14, 14, 35 * 16, 290 * 16)
        painter.drawLine(12, 2, 12, 11)
    elif name == "lock":
        painter.drawRoundedRect(5, 10, 14, 11, 2, 2)
        painter.drawArc(8, 3, 8, 12, 0, 180 * 16)
    elif name == "eye":
        painter.drawEllipse(3, 7, 18, 11)
        painter.setBrush(QColor(color))
        painter.drawEllipse(10, 10, 4, 4)
    elif name == "settings":
        for y, x in ((6, 9), (12, 15), (18, 7)):
            painter.drawLine(3, y, 21, y)
            painter.setBrush(QColor(color))
            painter.drawEllipse(x - 2, y - 2, 4, 4)
            painter.setBrush(Qt.NoBrush)
    elif name == "mute":
        painter.drawLine(4, 10, 8, 10)
        painter.drawLine(8, 10, 13, 6)
        painter.drawLine(13, 6, 13, 18)
        painter.drawLine(13, 18, 8, 14)
        painter.drawLine(8, 14, 4, 14)
        painter.drawLine(16, 9, 21, 15)
        painter.drawLine(21, 9, 16, 15)
    elif name == "solo":
        painter.drawText(QRectF(2, 1, 20, 22), Qt.AlignCenter, "S")
    painter.end()
    return QIcon(pixmap)


class GenerationBusyOverlay(QWidget):
    """Lightweight animated overlay used while ComfyUI is executing."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.angle = 0
        self.started_monotonic = 0.0
        self.completed_shots = 0
        self.total_shots = 0
        self.completed_weight_seconds = 0.0
        self.total_weight_seconds = 0.0
        self.active_shots: list[str] = []
        self.message = "ComfyUI running…"
        self.timer = QTimer(self)
        self.timer.setInterval(45)
        self.timer.timeout.connect(self._advance)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        parent.installEventFilter(self)
        self.hide()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.parent() and event.type() == QEvent.Resize:
            self.setGeometry(self.parent().rect())
        return False

    def start(self, message: str = "ComfyUI running…") -> None:
        self.message = message
        self.started_monotonic = time.monotonic()
        self.completed_shots = 0
        self.total_shots = 0
        self.completed_weight_seconds = 0.0
        self.total_weight_seconds = 0.0
        self.active_shots = []
        self.setGeometry(self.parent().rect())
        self.angle = 0
        self.show()
        self.raise_()
        self.timer.start()
        self.update()

    def set_message(self, message: str) -> None:
        self.message = message
        self.update()

    def set_progress(
        self,
        *,
        completed_shots: int,
        total_shots: int,
        completed_weight_seconds: float,
        total_weight_seconds: float,
        active_shots: list[str] | None = None,
    ) -> None:
        self.completed_shots = max(0, int(completed_shots))
        self.total_shots = max(self.completed_shots, int(total_shots))
        self.total_weight_seconds = max(0.0, float(total_weight_seconds))
        self.completed_weight_seconds = min(
            self.total_weight_seconds,
            max(0.0, float(completed_weight_seconds)),
        )
        self.active_shots = [str(value) for value in (active_shots or []) if str(value)]
        self.update()

    def elapsed_seconds(self) -> float:
        if self.started_monotonic <= 0.0:
            return 0.0
        return max(0.0, time.monotonic() - self.started_monotonic)

    def weighted_percent(self) -> float:
        if self.total_weight_seconds <= 1e-9:
            return 0.0
        return min(
            100.0,
            max(0.0, self.completed_weight_seconds / self.total_weight_seconds * 100.0),
        )

    def stop(self) -> None:
        self.timer.stop()
        self.hide()

    def _advance(self) -> None:
        self.angle = (self.angle + 20) % 360
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Keep the source/master visible during long renders. The compact dark
        # status card carries the spinner without replacing Program Monitor.
        painter.fillRect(self.rect(), QColor(5, 7, 9, 62))
        center = self.rect().center()
        card_width = min(max(300, self.width() // 2), max(300, self.width() - 36))
        card_height = 244 if self.total_shots else 190
        card = QRectF(
            center.x() - card_width / 2,
            center.y() - card_height / 2,
            card_width,
            card_height,
        )
        painter.setPen(QPen(QColor(83, 207, 223, 150), 1))
        painter.setBrush(QColor(8, 12, 16, 218))
        painter.drawRoundedRect(card, 10, 10)
        radius = 25
        spinner_center_y = card.top() + 48
        spinner_rect = QRectF(
            center.x() - radius,
            spinner_center_y - radius,
            radius * 2,
            radius * 2,
        )
        background_pen = QPen(QColor("#3d454d"), 6)
        background_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(background_pen)
        painter.drawArc(spinner_rect, 0, 360 * 16)
        active_pen = QPen(QColor("#36bfd7"), 6)
        active_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(active_pen)
        painter.drawArc(spinner_rect, -self.angle * 16, 105 * 16)
        elapsed = round(self.elapsed_seconds())
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        painter.setPen(QColor("#f1f5f7"))
        painter.drawText(
            QRectF(card.left() + 12, card.top() + 80, card.width() - 24, 22),
            Qt.AlignHCenter | Qt.AlignVCenter,
            f"GENERATING  ·  ELAPSED {hours:02d}:{minutes:02d}:{seconds:02d}",
        )
        painter.drawText(
            QRectF(card.left() + 18, card.top() + 105, card.width() - 36, 42),
            Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
            self.message,
        )
        if self.total_shots:
            completed_percent = self.weighted_percent()
            remaining_percent = max(0.0, 100.0 - completed_percent)
            remaining_shots = max(0, self.total_shots - self.completed_shots)
            active = ", ".join(self.active_shots)
            active_text = f"  ·  Processing {active}" if active else ""
            painter.setPen(QColor("#b9c5cc"))
            painter.drawText(
                QRectF(card.left() + 18, card.top() + 150, card.width() - 36, 22),
                Qt.AlignHCenter | Qt.AlignVCenter,
                f"Shots {self.completed_shots}/{self.total_shots} completed  ·  "
                f"{remaining_shots} remaining{active_text}",
            )
            painter.drawText(
                QRectF(card.left() + 18, card.top() + 174, card.width() - 36, 22),
                Qt.AlignHCenter | Qt.AlignVCenter,
                f"Completed {completed_percent:.1f}%  ·  Remaining {remaining_percent:.1f}%",
            )
            bar = QRectF(card.left() + 26, card.top() + 207, card.width() - 52, 10)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#303942"))
            painter.drawRoundedRect(bar, 5, 5)
            if completed_percent > 0.0:
                fill = QRectF(
                    bar.left(),
                    bar.top(),
                    bar.width() * completed_percent / 100.0,
                    bar.height(),
                )
                painter.setBrush(QColor("#36bfd7"))
                painter.drawRoundedRect(fill, 5, 5)


class JsonLineProcess(QObject):
    """Supervise one crash-isolated JSON worker with non-blocking queued input.

    Worker requests can contain large BLIP evidence, schemas and prompts.  A
    Windows anonymous pipe applies backpressure while the child is busy with
    an earlier inference, so writing/flushing that pipe from the Qt thread can
    freeze the whole Studio on the third consecutive request.  Only the
    dedicated writer thread below may touch worker stdin.
    """

    message = Signal(dict)
    finished = Signal(int, str)

    def __init__(self, parent: QObject | None = None, name: str = "worker") -> None:
        super().__init__(parent)
        self.name = name
        self.process: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None
        self._writer_thread: threading.Thread | None = None
        self._write_lock = threading.Lock()
        self._write_event = threading.Event()
        self._pending: list[dict] = []
        self._writer_error = ""
        self._ready = False
        self._stopping = False
        self.generation = 0
        self.started_monotonic = 0.0
        self.last_output_monotonic = 0.0

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def is_ready(self) -> bool:
        return self.is_running() and self._ready

    def start(self, program: str, arguments: list[str]) -> bool:
        if self.process is not None:
            return self.is_running()
        self._ready = False
        self._stopping = False
        self._writer_error = ""
        self._write_event.clear()
        self.generation += 1
        self.started_monotonic = time.monotonic()
        self.last_output_monotonic = self.started_monotonic
        process = subprocess.Popen(
            [program, *arguments],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
            creationflags=(
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
            ),
        )
        self.process = process
        generation = self.generation
        self._writer_thread = threading.Thread(
            target=self._write_loop,
            args=(process, generation),
            name=f"{self.name}-writer-{generation}",
            daemon=True,
        )
        self._writer_thread.start()
        self._thread = threading.Thread(
            target=self._read_loop,
            args=(process, generation),
            name=f"{self.name}-reader-{generation}",
            daemon=True,
        )
        self._thread.start()
        return True

    def _read_loop(self, process: subprocess.Popen[str], generation: int) -> None:
        log: list[str] = []
        assert process.stdout is not None
        for raw in process.stdout:
            self.last_output_monotonic = time.monotonic()
            line = raw.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                if payload.get("ready"):
                    with self._write_lock:
                        if self.process is process and generation == self.generation:
                            self._ready = True
                            self._write_event.set()
                self.message.emit(payload)
            except json.JSONDecodeError:
                log.append(line)
            except (BrokenPipeError, OSError) as exc:
                log.append(f"input queue failed: {exc}")
        exit_code = process.wait()
        try:
            process.stdout.close()
        except OSError:
            pass
        try:
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
        except OSError:
            pass
        with self._write_lock:
            is_current = self.process is process and generation == self.generation
            if is_current:
                self.process = None
                self._ready = False
                self._write_event.set()
                if not self._stopping:
                    log.append(f"{self.name} exited with code {exit_code}")
                if self._writer_error:
                    log.append(self._writer_error)
        if log:
            try:
                CACHE_ROOT.mkdir(parents=True, exist_ok=True)
                with (CACHE_ROOT / "recognition_workers.log").open("a", encoding="utf-8") as handle:
                    handle.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {self.name}\n")
                    handle.write("\n".join(log[-100:]) + "\n")
            except OSError:
                pass
        if is_current:
            self.finished.emit(exit_code, "\n".join(log[-30:]))

    def _write_loop(self, process: subprocess.Popen[str], generation: int) -> None:
        """Drain requests without ever blocking the GUI or stdout reader."""
        while True:
            self._write_event.wait()
            while True:
                with self._write_lock:
                    if (
                        self.process is not process
                        or generation != self.generation
                        or self._stopping
                    ):
                        return
                    if not self._ready or not self._pending:
                        # Clearing under the same lock used by write_json avoids
                        # losing a wake-up between the empty check and clear.
                        self._write_event.clear()
                        break
                    payload = self._pending.pop(0)
                try:
                    if process.stdin is None:
                        raise BrokenPipeError("worker stdin is unavailable")
                    process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
                    process.stdin.flush()
                except (BrokenPipeError, OSError) as exc:
                    with self._write_lock:
                        self._writer_error = (
                            f"input queue failed while writing in background: {exc}"
                        )
                        self._pending.clear()
                    try:
                        process.terminate()
                    except OSError:
                        pass
                    return

    def write_json(self, payload: dict) -> None:
        if not self.is_running() or self.process is None or self.process.stdin is None:
            raise RuntimeError("Background worker is not running")
        with self._write_lock:
            # Always enqueue.  Even a ready child may be busy processing its
            # previous line and unable to drain the OS pipe yet.
            self._pending.append(payload)
            self._write_event.set()

    def discard_pending(self) -> None:
        with self._write_lock:
            self._pending.clear()

    def terminate_now(self) -> None:
        process = self.process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    def stop(self) -> None:
        process = self.process
        if process is None:
            return
        self._stopping = True
        with self._write_lock:
            self._pending.clear()
            self._write_event.set()
        try:
            if process.stdin:
                process.stdin.close()
            process.wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=0.8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=0.8)
        thread = self._thread
        if thread and thread is not threading.current_thread() and thread.is_alive():
            thread.join(timeout=0.5)
        writer = self._writer_thread
        if writer and writer is not threading.current_thread() and writer.is_alive():
            writer.join(timeout=0.5)


TIMELINE_STATE_FIELDS = (
    "timeline_placed",
    "timeline_lane",
    "start_seconds",
    "end_seconds",
    "activation_mode",
    "timeline_track_id",
    "playback_speed",
    "source_in_seconds",
    "source_out_seconds",
    "fade_in_seconds",
    "fade_out_seconds",
    "transition_in",
    "transition_out",
    "clip_prompt",
    "monitor_visible",
)


@dataclass(slots=True)
class TimelineTrack:
    track_id: str
    name: str
    kind: str
    color: str
    enabled: bool = True
    locked: bool = False
    height: int = 20
    visible: bool = True
    opacity: float = 1.0
    blend_mode: str = "Normal"
    muted: bool = False
    solo: bool = False
    volume: float = 1.0
    pan: float = 0.0

    def __post_init__(self) -> None:
        self.height = max(20, min(140, int(self.height)))
        self.opacity = max(0.0, min(1.0, float(self.opacity)))
        self.volume = max(0.0, min(1.0, float(self.volume)))
        self.pan = max(-1.0, min(1.0, float(self.pan)))


@dataclass(slots=True)
class TextLayer:
    layer_id: str
    text: str
    start_seconds: float
    end_seconds: float
    track_id: str
    font_size: int = 48
    color: str = "#ffffff"
    position_x: float = 0.5
    position_y: float = 0.5
    content_role: str = "on_screen_text"
    speaker: str = "S1"
    language: str = "English"
    delivery: str = "Natural"
    lip_sync: bool = True
    shot_id: str = ""
    speech_timing_auto_adjusted: bool = False

    def __post_init__(self) -> None:
        self.font_size = max(8, min(240, int(self.font_size)))
        self.start_seconds = max(0.0, float(self.start_seconds))
        self.end_seconds = max(self.start_seconds + 0.1, float(self.end_seconds))
        self.position_x = max(0.0, min(1.0, float(self.position_x)))
        self.position_y = max(0.0, min(1.0, float(self.position_y)))
        if self.content_role not in {"on_screen_text", "dialogue", "voice_over", "lyrics"}:
            self.content_role = "on_screen_text"
        self.speaker = self.speaker if self.speaker in {"S1", "S2"} else "S1"
        self.language = str(self.language).strip() or "English"
        if re.search(r"[\u3400-\u9fff]", self.text) and self.language.lower() in {
            "english", "original language", "auto",
        }:
            self.language = "Mandarin Chinese"
        self.delivery = str(self.delivery).strip() or "Natural"
        self.lip_sync = bool(self.lip_sync)
        self.speech_timing_auto_adjusted = bool(self.speech_timing_auto_adjusted)


def text_layer_from_mapping(value: dict) -> TextLayer:
    """Load current or future Text Layer JSON without rejecting extra metadata."""
    allowed = TextLayer.__dataclass_fields__.keys()
    return TextLayer(**{key: value[key] for key in allowed if key in value})


def text_layer_track_kind(content_role: str) -> str:
    """Map visible titles to V tracks and authored speech to A tracks."""
    return "visual" if content_role == "on_screen_text" else "audio"


def default_text_layer_track(content_role: str) -> str:
    return {
        "on_screen_text": "V4",
        "dialogue": "A4",
        "voice_over": "A5",
        "lyrics": "A6",
    }.get(content_role, "V4")


def text_layer_track_name(track_id: str, content_role: str) -> str:
    role_name = {
        "on_screen_text": "Type",
        "dialogue": "Dialogue",
        "voice_over": "Voice-over",
        "lyrics": "Lyrics",
    }.get(content_role, "Type")
    return f"{track_id} {role_name}"


@dataclass(slots=True)
class DirectorCue:
    cue_id: str
    cue_type: str
    start_seconds: float
    end_seconds: float
    preset: str
    detail: str = ""
    track_id: str = ""
    framing: str = "Medium-wide"
    camera_angle: str = "Eye level"
    camera_movement: str = "Static"
    movement_speed: str = "Slow"
    movement_amplitude: str = "Small"
    subject_action: str = ""
    environment_response: str = ""
    continuity_mode: str = "Auto"
    semantic_reference_directions: dict[str, str] = field(default_factory=dict)
    continuity_state: str = ""
    optional_flourish: str = ""
    h3_executable_action: str = ""
    h3_optional_flourish: str = ""
    action_budget_status: str = "within_budget"
    action_budget_notes: str = ""
    authored_subject_action: str = ""
    authored_environment_response: str = ""
    native_audio_direction: str = ""
    environment_continuity: str = ""
    audio_reference_intent: str = ""
    native_audio_qc_status: str = "Not analyzed"
    native_audio_direction_user_edited: bool = False
    environment_continuity_user_edited: bool = False
    audio_reference_intent_user_edited: bool = False
    native_audio_qc_user_edited: bool = False

    def __post_init__(self) -> None:
        if self.cue_type not in DIRECTOR_LANE_TYPES and self.cue_type != "cut":
            self.cue_type = "marker"
        self.start_seconds = max(0.0, float(self.start_seconds))
        self.end_seconds = max(self.start_seconds + 0.05, float(self.end_seconds))
        if self.continuity_mode not in CONTINUITY_MODE_LABELS:
            self.continuity_mode = "Auto"
        if not isinstance(self.semantic_reference_directions, dict):
            self.semantic_reference_directions = {}
        else:
            self.semantic_reference_directions = {
                str(node_id): str(direction).strip()
                for node_id, direction in self.semantic_reference_directions.items()
                if str(node_id).strip() and str(direction).strip()
            }
        if self.cue_type == "shot" and not self.h3_executable_action:
            self.authored_subject_action = self.authored_subject_action or self.subject_action
            self.authored_environment_response = (
                self.authored_environment_response or self.environment_response
            )
            budgeted = normalize_shot_action_budget({
                "start_seconds": self.start_seconds,
                "end_seconds": self.end_seconds,
                "subject_action": self.authored_subject_action,
                "environment_response": self.authored_environment_response,
                "continuity_state": self.continuity_state,
                "optional_flourish": self.optional_flourish,
            })
            self.subject_action = budgeted["subject_action"]
            self.environment_response = budgeted["environment_response"]
            self.continuity_state = budgeted["continuity_state"]
            self.optional_flourish = budgeted["optional_flourish"]
            self.h3_executable_action = budgeted["h3_executable_action"]
            self.h3_optional_flourish = budgeted["h3_optional_flourish"]
            self.action_budget_status = budgeted["action_budget"]["status"]
            self.action_budget_notes = budgeted["action_budget"]["notes"]
        elif self.cue_type == "shot":
            self.authored_subject_action = self.authored_subject_action or self.subject_action
            self.authored_environment_response = (
                self.authored_environment_response or self.environment_response
            )


def default_timeline_tracks() -> list[TimelineTrack]:
    return [
        TimelineTrack("V3", "V3", "visual", "#3978ba"),
        TimelineTrack("V2", "V2", "visual", "#3978ba"),
        TimelineTrack("V1", "V1", "visual", "#3978ba"),
        TimelineTrack("A1", "A1", "audio", "#258a70"),
        TimelineTrack("A2", "A2", "audio", "#258a70"),
        TimelineTrack("A3", "A3", "audio", "#258a70"),
    ]


def timeline_state(asset: MediaAsset) -> dict:
    return {name: getattr(asset, name) for name in TIMELINE_STATE_FIELDS}


class AssetEditCommand(QUndoCommand):
    def __init__(self, asset: MediaAsset, before: dict, after: dict, refresh, text: str) -> None:
        super().__init__(text)
        self.asset = asset
        self.before = before
        self.after = after
        self.refresh = refresh

    def _apply(self, state: dict) -> None:
        for name, value in state.items():
            setattr(self.asset, name, value)
        self.refresh(self.asset)

    def undo(self) -> None:
        self._apply(self.before)

    def redo(self) -> None:
        self._apply(self.after)


class AddTimelineClipCommand(QUndoCommand):
    """Add/remove one independent Timeline use of a Media Pool source."""

    def __init__(self, clips: list[MediaAsset], clip: MediaAsset, refresh) -> None:
        super().__init__("Add repeated media clip")
        self.clips = clips
        self.clip = clip
        self.refresh = refresh

    def undo(self) -> None:
        if self.clip in self.clips:
            self.clips.remove(self.clip)
        self.refresh(self.clip)

    def redo(self) -> None:
        if self.clip not in self.clips:
            self.clips.append(self.clip)
        self.refresh(self.clip)


class RemoveTimelineClipCommand(AddTimelineClipCommand):
    def __init__(self, clips: list[MediaAsset], clip: MediaAsset, refresh) -> None:
        super().__init__(clips, clip, refresh)
        self.setText("Remove repeated media clip")

    def undo(self) -> None:
        AddTimelineClipCommand.redo(self)

    def redo(self) -> None:
        AddTimelineClipCommand.undo(self)


class TrackEditCommand(QUndoCommand):
    def __init__(self, track: TimelineTrack, before: dict, after: dict, refresh, text: str) -> None:
        super().__init__(text)
        self.track = track
        self.before = before
        self.after = after
        self.refresh = refresh

    def _apply(self, state: dict) -> None:
        for name, value in state.items():
            setattr(self.track, name, value)
        self.refresh(self.track)

    def undo(self) -> None:
        self._apply(self.before)

    def redo(self) -> None:
        self._apply(self.after)


class AddTrackCommand(QUndoCommand):
    def __init__(self, tracks: list[TimelineTrack], track: TimelineTrack, index: int, refresh) -> None:
        super().__init__(f"Add {track.kind} track")
        self.tracks = tracks
        self.track = track
        self.index = index
        self.refresh = refresh

    def undo(self) -> None:
        if self.track in self.tracks:
            self.tracks.remove(self.track)
        self.refresh(self.track)

    def redo(self) -> None:
        if self.track not in self.tracks:
            self.tracks.insert(min(self.index, len(self.tracks)), self.track)
        self.refresh(self.track)


class RemoveTrackCommand(QUndoCommand):
    """Remove a track and safely move its clips to a same-kind fallback track."""

    def __init__(
        self,
        tracks: list[TimelineTrack],
        track: TimelineTrack,
        fallback: TimelineTrack,
        assets: list[MediaAsset],
        text_layers: list[TextLayer],
        director_cues: list[DirectorCue],
        refresh,
    ) -> None:
        super().__init__(f"Delete {track.kind} track")
        self.tracks = tracks
        self.track = track
        self.fallback = fallback
        self.index = tracks.index(track)
        self.refresh = refresh
        self.asset_states = [
            (asset, asset.timeline_track_id, asset.timeline_lane)
            for asset in assets
            if asset.timeline_track_id == track.track_id
        ]
        self.text_states = [
            (layer, layer.track_id)
            for layer in text_layers
            if layer.track_id == track.track_id
        ]
        self.cue_states = [
            (cue, cue.track_id)
            for cue in director_cues
            if cue.cue_type == "shot" and cue.track_id == track.track_id
        ]

    def undo(self) -> None:
        if self.track not in self.tracks:
            self.tracks.insert(min(self.index, len(self.tracks)), self.track)
        for asset, track_id, lane in self.asset_states:
            asset.timeline_track_id = track_id
            asset.timeline_lane = lane
        for layer, track_id in self.text_states:
            layer.track_id = track_id
        for cue, track_id in self.cue_states:
            cue.track_id = track_id
        self.refresh(self.track)

    def redo(self) -> None:
        if self.track in self.tracks:
            self.tracks.remove(self.track)
        fallback_lane = self.tracks.index(self.fallback)
        for asset, _track_id, _lane in self.asset_states:
            asset.timeline_track_id = self.fallback.track_id
            asset.timeline_lane = fallback_lane
        for layer, _track_id in self.text_states:
            layer.track_id = self.fallback.track_id
        for cue, _track_id in self.cue_states:
            cue.track_id = self.fallback.track_id
        self.refresh(self.track)


class TextLayerEditCommand(QUndoCommand):
    def __init__(self, layer: TextLayer, before: dict, after: dict, refresh, text: str) -> None:
        super().__init__(text)
        self.layer = layer
        self.before = before
        self.after = after
        self.refresh = refresh

    def _apply(self, state: dict) -> None:
        for name, value in state.items():
            setattr(self.layer, name, value)
        self.refresh(self.layer)

    def undo(self) -> None:
        self._apply(self.before)

    def redo(self) -> None:
        self._apply(self.after)


class AddTextLayerCommand(QUndoCommand):
    def __init__(self, layers: list[TextLayer], layer: TextLayer, refresh) -> None:
        super().__init__("Add text layer")
        self.layers = layers
        self.layer = layer
        self.refresh = refresh

    def undo(self) -> None:
        if self.layer in self.layers:
            self.layers.remove(self.layer)
        self.refresh(self.layer)

    def redo(self) -> None:
        if self.layer not in self.layers:
            self.layers.append(self.layer)
        self.refresh(self.layer)


class RemoveTextLayerCommand(AddTextLayerCommand):
    def __init__(self, layers: list[TextLayer], layer: TextLayer, refresh) -> None:
        super().__init__(layers, layer, refresh)
        self.setText("Remove text layer")

    def undo(self) -> None:
        AddTextLayerCommand.redo(self)

    def redo(self) -> None:
        AddTextLayerCommand.undo(self)


class DirectorCueEditCommand(QUndoCommand):
    def __init__(self, cue: DirectorCue, before: dict, after: dict, refresh, text: str) -> None:
        super().__init__(text)
        self.cue = cue
        self.before = before
        self.after = after
        self.refresh = refresh

    def _apply(self, state: dict) -> None:
        for name, value in state.items():
            setattr(self.cue, name, value)
        self.refresh(self.cue)

    def undo(self) -> None:
        self._apply(self.before)

    def redo(self) -> None:
        self._apply(self.after)


class AddDirectorCueCommand(QUndoCommand):
    def __init__(self, cues: list[DirectorCue], cue: DirectorCue, refresh, text: str = "Add director cue") -> None:
        super().__init__(text)
        self.cues = cues
        self.cue = cue
        self.refresh = refresh

    def undo(self) -> None:
        if self.cue in self.cues:
            self.cues.remove(self.cue)
        self.refresh(self.cue)

    def redo(self) -> None:
        if self.cue not in self.cues:
            self.cues.append(self.cue)
        self.refresh(self.cue)


class RemoveDirectorCueCommand(AddDirectorCueCommand):
    def __init__(
        self,
        cues: list[DirectorCue],
        cue: DirectorCue,
        refresh,
        text_layers: list[TextLayer] | None = None,
    ) -> None:
        super().__init__(cues, cue, refresh, "Remove director cue")
        self.bindings = [
            layer for layer in (text_layers or []) if layer.shot_id == cue.cue_id
        ]

    def undo(self) -> None:
        AddDirectorCueCommand.redo(self)
        for layer in self.bindings:
            layer.shot_id = self.cue.cue_id

    def redo(self) -> None:
        for layer in self.bindings:
            layer.shot_id = ""
        AddDirectorCueCommand.undo(self)


class SplitTextLayerCommand(QUndoCommand):
    """Split one title block into two independently editable title blocks."""

    def __init__(self, layers: list[TextLayer], original: TextLayer, clone: TextLayer, cut: float, refresh) -> None:
        super().__init__("Razor text layer")
        self.layers = layers
        self.original = original
        self.clone = clone
        self.cut = cut
        self.original_end = original.end_seconds
        self.refresh = refresh

    def undo(self) -> None:
        self.original.end_seconds = self.original_end
        if self.clone in self.layers:
            self.layers.remove(self.clone)
        self.refresh(self.original)

    def redo(self) -> None:
        self.original.end_seconds = self.cut
        if self.clone not in self.layers:
            self.layers.append(self.clone)
        self.refresh(self.original)


class SplitDirectorCueCommand(QUndoCommand):
    """Split a ranged director cue while keeping both halves undoable."""

    def __init__(self, cues: list[DirectorCue], original: DirectorCue, clone: DirectorCue, cut: float, refresh) -> None:
        super().__init__("Razor director cue")
        self.cues = cues
        self.original = original
        self.clone = clone
        self.cut = cut
        self.original_end = original.end_seconds
        self.refresh = refresh

    def undo(self) -> None:
        self.original.end_seconds = self.original_end
        if self.clone in self.cues:
            self.cues.remove(self.clone)
        self.refresh(self.original)

    def redo(self) -> None:
        self.original.end_seconds = self.cut
        if self.clone not in self.cues:
            self.cues.append(self.clone)
        self.refresh(self.original)


class MonitorTextLabel(QLabel):
    """A Program Monitor title that can be positioned with Selection Tool."""

    def __init__(self, layer: TextLayer, committed, parent: QWidget) -> None:
        super().__init__(parent)
        self.layer = layer
        self.committed = committed
        self.selection_enabled = False
        self.drag_offset = QPoint()
        self.before_position: dict | None = None
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)

    def set_selection_enabled(self, enabled: bool) -> None:
        self.selection_enabled = enabled
        self.setAttribute(Qt.WA_TransparentForMouseEvents, not enabled)
        self.setCursor(Qt.OpenHandCursor if enabled else Qt.ArrowCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.selection_enabled and event.button() == Qt.LeftButton:
            self.drag_offset = event.position().toPoint()
            self.before_position = {
                "position_x": self.layer.position_x,
                "position_y": self.layer.position_y,
            }
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self.selection_enabled or self.before_position is None:
            return super().mouseMoveEvent(event)
        parent = self.parentWidget()
        if parent is None:
            return
        pointer = self.mapToParent(event.position().toPoint())
        x = max(0, min(parent.width() - self.width(), pointer.x() - self.drag_offset.x()))
        y = max(0, min(parent.height() - self.height(), pointer.y() - self.drag_offset.y()))
        self.move(x, y)
        self.layer.position_x = (x + self.width() / 2) / max(1, parent.width())
        self.layer.position_y = (y + self.height() / 2) / max(1, parent.height())
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self.selection_enabled and self.before_position is not None:
            before = self.before_position
            after = {
                "position_x": self.layer.position_x,
                "position_y": self.layer.position_y,
            }
            self.before_position = None
            self.setCursor(Qt.OpenHandCursor)
            if before != after:
                layer = self.layer
                callback = self.committed
                QTimer.singleShot(
                    0,
                    lambda item=layer, old=before, new=after, commit=callback: commit(
                        item, old, new
                    ),
                )
            event.accept()
            return
        super().mouseReleaseEvent(event)


class MediaCardBusyOverlay(QWidget):
    """Compact translucent spinner shown over one Media Pool card."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.angle = 0
        self.message = "AI ENRICH"
        self.timer = QTimer(self)
        self.timer.setInterval(45)
        self.timer.timeout.connect(self._advance)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()

    def start(self, message: str = "AI ENRICH") -> None:
        self.message = str(message).strip() or "AI ENRICH"
        self.angle = 0
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        self.show()
        self.raise_()
        self.timer.start()
        self.update()

    def stop(self) -> None:
        self.timer.stop()
        self.hide()

    def _advance(self) -> None:
        self.angle = (self.angle + 20) % 360
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(4, 7, 10, 158))
        center = self.rect().center()
        radius = max(9, min(16, min(self.width(), self.height()) // 7))
        spinner_y = center.y() - 8
        spinner_rect = QRectF(
            center.x() - radius,
            spinner_y - radius,
            radius * 2,
            radius * 2,
        )
        background_pen = QPen(QColor(116, 132, 142, 115), 3)
        background_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(background_pen)
        painter.drawArc(spinner_rect, 0, 360 * 16)
        active_pen = QPen(QColor("#39c6df"), 3)
        active_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(active_pen)
        painter.drawArc(spinner_rect, -self.angle * 16, 105 * 16)
        painter.setPen(QColor("#eefcff"))
        painter.drawText(
            QRectF(4, spinner_rect.bottom() + 6, max(1, self.width() - 8), 18),
            Qt.AlignHCenter | Qt.AlignTop,
            self.message if self.width() >= 102 else "AI",
        )
        painter.end()


class MediaCard(QFrame):
    selected = Signal(object)
    file_dropped = Signal(object, str)
    z_image_regeneration_requested = Signal(object)

    def __init__(self, asset: MediaAsset) -> None:
        super().__init__()
        self.asset = asset
        self._drag_start = QPoint()
        self.preview_pixmap: QPixmap | None = None
        self.last_active_in_window: bool | None = None
        self.analysis_status = ""
        self.setAcceptDrops(True)
        self.setMinimumHeight(118)
        self.setMinimumWidth(MEDIA_CARD_MIN_WIDTH)
        self.setObjectName("mediaCard")
        self.setStyleSheet(
            "QFrame#mediaCard { background:#22252a; border:1px solid #363a40; border-radius:4px; }"
            "QFrame#mediaCard:hover { border-color:#5dabb9; background:#282c31; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 6, 7, 6)
        layout.setSpacing(4)
        head = QHBoxLayout()
        self.tag = QLabel(media_shortcut(asset))
        self.tag.setToolTip(asset.tag)
        self.tag.setMinimumWidth(0)
        self.tag.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.tag.setStyleSheet("font-weight:700; color:#f0f0f0;")
        self.mode = QLabel("AUTO")
        self.mode.setAlignment(Qt.AlignCenter)
        self.mode.setFixedWidth(52)
        head.addWidget(self.tag, 1)
        head.addWidget(self.mode)
        layout.addLayout(head)
        self.thumb = QLabel("Double-click or drop\nto load media")
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setMinimumHeight(66)
        self.thumb.setStyleSheet("background:#101214; color:#757b84; border:0;")
        layout.addWidget(self.thumb)
        foot = QHBoxLayout()
        self.filename = QLabel(asset.filename or f"Load{asset.media_type.title()} node {asset.node_id}")
        self.filename.setMinimumWidth(0)
        self.filename.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.filename.setToolTip(asset.filename)
        self.filename.setStyleSheet("color:#aeb3ba;")
        self.ai_badge = QLabel("识别 --")
        self.ai_badge.setStyleSheet("color:#68c9d8; font-size:10px;")
        foot.addWidget(self.filename, 1)
        foot.addWidget(self.ai_badge)
        layout.addLayout(foot)
        # Child labels otherwise consume the initial mouse press on Windows,
        # preventing the parent card from starting a QDrag reliably.
        for child in (self.tag, self.mode, self.thumb, self.filename, self.ai_badge):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.busy_overlay = MediaCardBusyOverlay(self)
        self.refresh_mode()
        # A Picture with a valid local file must never wait for the asynchronous
        # preparation worker merely to become visible in Media Pool.
        self.set_local_image_fallback()

    def refresh_mode(self, active_in_window: bool | None = None) -> None:
        if active_in_window is not None:
            self.last_active_in_window = active_in_window
        names = {"auto": "AUTO", "active": "ACTIVE", "bypass": "BYPASS"}
        colors = {"auto": "#ba8e2f", "active": "#178b65", "bypass": "#8c3d49"}
        mode = self.asset.activation_mode
        text = "MEDIA" if not self.asset.timeline_placed else names.get(mode, mode.upper())
        if self.asset.timeline_placed and mode == "auto" and self.last_active_in_window is not None:
            text = "AUTO ON" if self.last_active_in_window else "AUTO OFF"
        if not self.asset.timeline_placed:
            colors[mode] = "#50555c"
        compact = self.width() < 140
        if compact:
            text = {
                "MEDIA": "M",
                "AUTO ON": "ON",
                "AUTO OFF": "OFF",
                "AUTO": "A",
                "ACTIVE": "ACT",
                "BYPASS": "BYP",
            }.get(text, text[:3])
            self.mode.setFixedWidth(34)
            self.mode.hide()
        else:
            self.mode.setFixedWidth(52)
            self.mode.show()
        self.mode.setText(text)
        self.mode.setStyleSheet(
            f"background:{colors.get(mode, '#555')}; color:white; border-radius:3px; padding:2px; font-size:9px; font-weight:700;"
        )

    def set_preview(self, pixmap: QPixmap | None) -> None:
        if pixmap and not pixmap.isNull():
            self.preview_pixmap = QPixmap(pixmap)
            self._scale_preview()
        self._refresh_filename()
        self.filename.setToolTip(self.asset.local_path or self.asset.filename)
        self.set_analysis_status(
            "AI ✓"
            if self.asset.semantic_enrichment
            else "识别 ✓"
            if self.asset.recognition
            else "识别 …"
        )

    def set_local_image_fallback(self) -> bool:
        """Display the source Picture immediately, before derived preview work."""
        if self.asset.media_type != "image":
            return False
        source = Path(str(self.asset.local_path or ""))
        if not source.is_file():
            return False
        pixmap = QPixmap(str(source))
        if pixmap.isNull():
            return False
        self.set_preview(pixmap)
        return True

    def set_analysis_status(self, text: str) -> None:
        self.analysis_status = text
        self.ai_badge.setText(text)

    def set_processing(self, processing: bool, message: str = "AI ENRICH") -> None:
        if processing:
            self.busy_overlay.start(message)
        else:
            self.busy_overlay.stop()

    def _scale_preview(self) -> None:
        if self.preview_pixmap and not self.preview_pixmap.isNull():
            self.thumb.setPixmap(
                self.preview_pixmap.scaled(
                    max(80, self.width() - 18),
                    90,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

    def _refresh_filename(self) -> None:
        full = self.asset.filename or f"Node {self.asset.node_id}"
        default_status = (
            "AI ✓"
            if self.asset.semantic_enrichment
            else "识别 ✓"
            if self.asset.recognition
            else "识别 --"
        )
        status = self.analysis_status or default_status
        if self.width() < 125:
            self.filename.hide()
            self.ai_badge.setText(status)
        else:
            self.filename.show()
            self.ai_badge.setText(status)
        available = max(55, self.width() - self.ai_badge.width() - 34)
        self.filename.setText(self.filename.fontMetrics().elidedText(full, Qt.ElideMiddle, available))

    def _refresh_header(self) -> None:
        compact = self.width() < 140
        available = max(
            38,
            self.width() - (18 if compact else self.mode.width() + 30),
        )
        title = media_shortcut(self.asset)
        self.tag.setText(self.tag.fontMetrics().elidedText(title, Qt.ElideRight, available))
        if self.preview_pixmap is None:
            self.thumb.setText("DROP\nMEDIA" if self.width() < 140 else "Double-click or drop\nto load media")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "busy_overlay"):
            self.busy_overlay.setGeometry(self.rect())
            if not self.busy_overlay.isHidden():
                self.busy_overlay.raise_()
        self._scale_preview()
        self._refresh_filename()
        self.refresh_mode()
        self._refresh_header()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            filename, _ = QFileDialog.getOpenFileName(self, f"Load {self.asset.tag}", "", _media_filter(self.asset.media_type))
            if filename:
                self.file_dropped.emit(self.asset, filename)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
            self.selected.emit(self.asset)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < QApplication.startDragDistance():
            return
        mime = QMimeData()
        mime.setData(MIME_SLOT, self.asset.node_id.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            if paths and media_type_for_path(paths[0]) == self.asset.media_type:
                event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        path = event.mimeData().urls()[0].toLocalFile()
        self.file_dropped.emit(self.asset, path)
        event.acceptProposedAction()

    def create_context_menu(self) -> QMenu:
        """Build the small Media Pool menu used by mouse and UI tests."""
        menu = QMenu(self)
        regenerate = menu.addAction("REGENERATE WITH Z-IMAGE")
        regenerate.setObjectName("regenerateWithZImageAction")
        regenerate.setToolTip(
            "Generate a new image from this Picture's existing prompt, identity, "
            "subject-count, Shot relationship and Timeline range"
        )
        regenerate.setEnabled(
            self.asset.media_type == "image"
            and bool(
                str(self.asset.clip_prompt).strip()
                or str(self.asset.recognition).strip()
            )
        )
        regenerate.triggered.connect(
            lambda _checked=False: self.z_image_regeneration_requested.emit(self.asset)
        )
        return menu

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        menu = self.create_context_menu()
        menu.exec(event.globalPos())
        event.accept()


class TrackHeaderWidget(QWidget):
    """Single-row icon controls embedded at the left of each track."""

    BLEND_MODES = ("Normal", "Multiply", "Screen", "Overlay", "Additive", "Difference")

    def __init__(self, track: TimelineTrack, width: int, selected, changed, added, removed) -> None:
        super().__init__()
        self.track = track
        self.selected = selected
        self.changed = changed
        self.added = added
        self.removed = removed
        self.setObjectName(f"trackHeader_{track.track_id}")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(width, track.height)
        self.setToolTip(f"{track.kind.title()} track {track.track_id}")
        row = QHBoxLayout(self)
        row.setContentsMargins(3, 1, 2, 1)
        row.setSpacing(1)

        self.name_button = QPushButton(track.name)
        self.name_button.setObjectName("trackName")
        self.name_button.setFixedSize(48, 18)
        self.name_button.setStyleSheet("padding:0 2px; font-size:10px;")
        self.name_button.setToolTip("Track name · click to rename")
        self.name_button.clicked.connect(self._rename)
        row.addWidget(self.name_button)

        self.color_button = QToolButton()
        self.color_button.setObjectName("trackColor")
        self.color_button.setFixedSize(16, 16)
        self.color_button.setToolTip("Track color")
        self.color_button.clicked.connect(self._choose_color)
        row.addWidget(self.color_button)

        self.enabled_button = self._tool_button("power", "Enable / disable track", track.enabled)
        self.locked_button = self._tool_button("lock", "Lock track", track.locked)
        self.enabled_button.clicked.connect(lambda checked: self._request("enabled", checked))
        self.locked_button.clicked.connect(lambda checked: self._request("locked", checked))
        row.addWidget(self.enabled_button)
        row.addWidget(self.locked_button)

        self.options_button = self._tool_button("settings", "Track options")
        self.options_button.setPopupMode(QToolButton.InstantPopup)
        self.options_menu = QMenu(self.options_button)
        options_panel = QWidget()
        form = QFormLayout(options_panel)
        form.setContentsMargins(8, 7, 8, 7)
        self.height_spin = QSpinBox()
        self.height_spin.setObjectName("trackHeight")
        self.height_spin.setRange(20, 140)
        self.height_spin.setValue(track.height)
        self.height_spin.setSuffix(" px")
        self.height_spin.setToolTip("Track height in pixels")
        self.height_spin.editingFinished.connect(lambda: self._request("height", self.height_spin.value()))
        form.addRow("Height", self.height_spin)

        if track.kind == "visual":
            self.visible_button = self._tool_button("eye", "Show / hide visual track", track.visible)
            self.visible_button.clicked.connect(lambda checked: self._request("visible", checked))
            row.addWidget(self.visible_button)
            self.opacity_spin = QSpinBox()
            self.opacity_spin.setObjectName("trackOpacity")
            self.opacity_spin.setRange(0, 100)
            self.opacity_spin.setSuffix(" %")
            self.opacity_spin.setValue(round(track.opacity * 100))
            self.opacity_spin.editingFinished.connect(
                lambda: self._request("opacity", self.opacity_spin.value() / 100.0)
            )
            form.addRow("Opacity", self.opacity_spin)
            self.blend_combo = QComboBox()
            self.blend_combo.setObjectName("trackBlendMode")
            self.blend_combo.addItems(self.BLEND_MODES)
            self.blend_combo.setCurrentText(track.blend_mode)
            self.blend_combo.currentTextChanged.connect(lambda value: self._request("blend_mode", value))
            form.addRow("Blend Mode", self.blend_combo)
        else:
            self.mute_button = self._tool_button("mute", "Mute track", track.muted)
            self.solo_button = self._tool_button("solo", "Solo track", track.solo)
            self.mute_button.clicked.connect(lambda checked: self._request("muted", checked))
            self.solo_button.clicked.connect(lambda checked: self._request("solo", checked))
            row.addWidget(self.mute_button)
            row.addWidget(self.solo_button)
            self.volume_spin = QSpinBox()
            self.volume_spin.setObjectName("trackVolume")
            self.volume_spin.setRange(0, 100)
            self.volume_spin.setSuffix(" %")
            self.volume_spin.setValue(round(track.volume * 100))
            self.volume_spin.editingFinished.connect(
                lambda: self._request("volume", self.volume_spin.value() / 100.0)
            )
            form.addRow("Volume", self.volume_spin)
            self.pan_spin = QSpinBox()
            self.pan_spin.setObjectName("trackPan")
            self.pan_spin.setRange(-100, 100)
            self.pan_spin.setSuffix(" %")
            self.pan_spin.setValue(round(track.pan * 100))
            self.pan_spin.editingFinished.connect(lambda: self._request("pan", self.pan_spin.value() / 100.0))
            form.addRow("Pan", self.pan_spin)

        action = QWidgetAction(self.options_menu)
        action.setDefaultWidget(options_panel)
        self.options_menu.addAction(action)
        self.options_button.setMenu(self.options_menu)
        row.addWidget(self.options_button)

        self.add_button = self._tool_button("track_add", f"Add {track.kind} track beside {track.track_id}")
        self.add_button.clicked.connect(
            lambda: QTimer.singleShot(0, lambda item=self.track: self.added(item))
        )
        row.addWidget(self.add_button)
        self.delete_button = self._tool_button("track_delete", f"Delete {track.track_id} track")
        self.delete_button.clicked.connect(
            lambda: QTimer.singleShot(0, lambda item=self.track: self.removed(item))
        )
        row.addWidget(self.delete_button)
        row.addStretch()
        self.sync_from_track()

    @staticmethod
    def _tool_button(icon_name: str, tooltip: str, checked: bool | None = None) -> QToolButton:
        button = QToolButton()
        button.setIcon(editor_icon(icon_name))
        button.setIconSize(QSize(14, 14))
        button.setAutoRaise(True)
        button.setToolTip(tooltip)
        button.setFixedSize(18, 18)
        if checked is not None:
            button.setCheckable(True)
            button.setChecked(checked)
        button.setStyleSheet(
            "QToolButton { border:1px solid transparent; border-radius:2px; } "
            "QToolButton:hover { background:#353b42; border-color:#59616b; } "
            "QToolButton:checked { background:#126f86; border-color:#29a9c2; }"
        )
        return button

    def sync_from_track(self) -> None:
        self.name_button.setText(self.track.name)
        self.name_button.setToolTip(f"{self.track.track_id} · click to rename")
        self.color_button.setStyleSheet(
            f"background:{self.track.color}; border:1px solid #c8d0d8; border-radius:2px;"
        )
        self.setStyleSheet(
            f"#trackHeader_{self.track.track_id} {{ background:#20242a; "
            f"border-left:3px solid {self.track.color}; border-bottom:1px solid #090b0d; }}"
        )
        values = (
            (self.enabled_button, self.track.enabled),
            (self.locked_button, self.track.locked),
            (getattr(self, "visible_button", None), self.track.visible),
            (getattr(self, "mute_button", None), self.track.muted),
            (getattr(self, "solo_button", None), self.track.solo),
        )
        for widget, value in values:
            if widget is not None:
                widget.blockSignals(True)
                widget.setChecked(value)
                widget.blockSignals(False)
        for widget, value in (
            (self.height_spin, self.track.height),
            (getattr(self, "opacity_spin", None), round(self.track.opacity * 100)),
            (getattr(self, "volume_spin", None), round(self.track.volume * 100)),
            (getattr(self, "pan_spin", None), round(self.track.pan * 100)),
        ):
            if widget is not None:
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)
        if hasattr(self, "blend_combo"):
            self.blend_combo.blockSignals(True)
            self.blend_combo.setCurrentText(self.track.blend_mode)
            self.blend_combo.blockSignals(False)

    def _request(self, property_name: str, value) -> None:
        self.selected(self.track)
        # Editing a track rebuilds this graphics scene. Defer until the
        # originating widget signal returns so its proxy survives the callback.
        QTimer.singleShot(
            0,
            lambda item=self.track, name=property_name, new_value=value: self.changed(
                item, name, new_value
            ),
        )

    def _choose_color(self) -> None:
        self.selected(self.track)
        color = QColorDialog.getColor(QColor(self.track.color), self, "Track color")
        if color.isValid():
            self._request("color", color.name())

    def _rename(self) -> None:
        self.selected(self.track)
        name, accepted = QInputDialog.getText(self, "Rename track", "Track name", text=self.track.name)
        if accepted:
            self._request("name", name.strip() or self.track.track_id)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.selected(self.track)
        super().mousePressEvent(event)


class TimelineClip(QGraphicsRectItem):
    def __init__(
        self,
        asset: MediaAsset,
        pixels_per_second: float,
        origin_x: float,
        y: float,
        changed,
        committed,
        interaction_changed,
        resolve_track,
        locked: bool,
        clip_height: float,
        timeline_duration: float,
    ) -> None:
        self.asset = asset
        self.pps = pixels_per_second
        self.origin_x = origin_x
        self.changed = changed
        self.committed = committed
        self.interaction_changed = interaction_changed
        self.resolve_track = resolve_track
        self.locked = locked
        self.clip_height = clip_height
        self.timeline_duration = timeline_duration
        self.resize_edge: str | None = None
        self.press_scene_x = 0.0
        self.press_pos_x = 0.0
        self.press_width = 0.0
        self.before_state: dict | None = None
        width = max(30.0, (asset.end_seconds - asset.start_seconds) * self.pps)
        super().__init__(0, 0, width, clip_height)
        self.setPos(self.origin_x + asset.start_seconds * self.pps, y)
        self.setBrush(_asset_color(asset.media_type))
        self.setPen(QPen(QColor("#aab4c0"), 1))
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setFlag(QGraphicsItem.ItemIsMovable, not locked)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.OpenHandCursor)
        clip_flags: list[str] = []
        if abs(asset.playback_speed - 1.0) > 0.001:
            clip_flags.append(f"{asset.playback_speed:.2f}×")
        if asset.transition_in != "None" or asset.transition_out != "None":
            clip_flags.append("FX")
        if asset.clip_prompt.strip():
            clip_flags.append("PROMPT")
        suffix = f"  [{' · '.join(clip_flags)}]" if clip_flags else ""
        self.label = QGraphicsSimpleTextItem(f"{asset.tag}  {asset.filename or 'empty'}{suffix}", self)
        self.label.setBrush(QColor("white"))
        self.label.setPos(6, max(0.0, (clip_height - 14) / 2))
        self.left_handle = QGraphicsRectItem(self)
        self.right_handle = QGraphicsRectItem(self)
        for handle in (self.left_handle, self.right_handle):
            handle.setBrush(QColor(255, 255, 255, 145))
            handle.setPen(QPen(Qt.NoPen))
        self._position_handles()
        self.setOpacity(0.45 if locked else 1.0)
        self.setToolTip(
            "Track locked"
            if locked
            else "Drag body to move · drag either bright edge to trim · Delete removes clip"
            + (f"\nPrompt: {asset.clip_prompt}" if asset.clip_prompt.strip() else "")
        )

    def _position_handles(self) -> None:
        width = self.rect().width()
        handle_height = max(8.0, self.clip_height - 2)
        self.left_handle.setRect(QRectF(1, 1, 4, handle_height))
        self.right_handle.setRect(QRectF(max(1.0, width - 5), 1, 4, handle_height))

    def hoverMoveEvent(self, event) -> None:  # noqa: N802
        x = event.pos().x()
        if x <= 9 or x >= self.rect().width() - 9:
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.locked:
            super().mousePressEvent(event)
            return
        self.interaction_changed(True)
        self.before_state = timeline_state(self.asset)
        self.press_scene_x = event.scenePos().x()
        self.press_pos_x = self.x()
        self.press_width = self.rect().width()
        local_x = event.pos().x()
        if local_x <= 9:
            self.resize_edge = "left"
        elif local_x >= self.rect().width() - 9:
            self.resize_edge = "right"
        else:
            self.resize_edge = None
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self.locked:
            super().mouseMoveEvent(event)
            return
        if not self.resize_edge:
            super().mouseMoveEvent(event)
            return
        delta = event.scenePos().x() - self.press_scene_x
        min_width = TIMELINE_SNAP_SECONDS * self.pps
        if self.resize_edge == "left":
            right = self.press_pos_x + self.press_width
            proposed_seconds = (self.press_pos_x + delta - self.origin_x) / self.pps
            snapped_seconds = snap_timeline_seconds(proposed_seconds, self.timeline_duration)
            new_x = min(right - min_width, self.origin_x + snapped_seconds * self.pps)
            new_x = max(self.origin_x, new_x)
            self.setPos(new_x, self.y())
            self.setRect(0, 0, right - new_x, self.clip_height)
        else:
            proposed_end = (self.press_pos_x + self.press_width + delta - self.origin_x) / self.pps
            snapped_end = snap_timeline_seconds(proposed_end, self.timeline_duration)
            start_seconds = max(0.0, (self.press_pos_x - self.origin_x) / self.pps)
            snapped_end = max(start_seconds + TIMELINE_SNAP_SECONDS, snapped_end)
            snapped_end = min(self.timeline_duration, snapped_end)
            available_width = max(
                1.0,
                (self.timeline_duration - start_seconds) * self.pps,
            )
            self.setRect(
                0,
                0,
                min(
                    available_width,
                    max(min_width, self.origin_x + snapped_end * self.pps - self.press_pos_x),
                ),
                self.clip_height,
            )
        self.asset.start_seconds = max(0.0, (self.x() - self.origin_x) / self.pps)
        self.asset.end_seconds = self.asset.start_seconds + self.rect().width() / self.pps
        self._position_handles()
        self.changed(self.asset)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self.locked:
            super().mouseReleaseEvent(event)
            return
        super().mouseReleaseEvent(event)
        self.setCursor(Qt.OpenHandCursor)
        after = timeline_state(self.asset)
        before = dict(self.before_state) if self.before_state else None
        asset = self.asset
        committed = self.committed
        self.before_state = None
        self.resize_edge = None
        self.interaction_changed(False)
        if before and after != before:
            # Pushing the undo command rebuilds the QGraphicsScene. Defer it
            # until Qt has completely unwound this item's native mouse event;
            # rebuilding synchronously here deletes `self` mid-callback.
            QTimer.singleShot(
                0,
                lambda item=asset, old=before, new=after, callback=committed: callback(
                    item, old, new
                ),
            )

    def itemChange(self, change, value):  # noqa: N802
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            point = value
            clip_duration = max(
                TIMELINE_SNAP_SECONDS,
                self.asset.end_seconds - self.asset.start_seconds,
            )
            max_start = max(0.0, self.timeline_duration - clip_duration)
            proposed_seconds = (point.x() - self.origin_x) / self.pps
            snapped_seconds = min(max_start, snap_timeline_seconds(proposed_seconds, self.timeline_duration))
            point.setX(self.origin_x + snapped_seconds * self.pps)
            lane, track_id, clip_y, clip_height = self.resolve_track(self.asset, point.y())
            point.setY(clip_y)
            self.clip_height = clip_height
            self.asset.timeline_lane = lane
            self.asset.timeline_track_id = track_id
            return point
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            duration = self.asset.end_seconds - self.asset.start_seconds
            self.asset.start_seconds = (self.x() - self.origin_x) / self.pps
            self.asset.end_seconds = self.asset.start_seconds + duration
            lane, track_id, _clip_y, _clip_height = self.resolve_track(self.asset, self.y())
            self.asset.timeline_lane = lane
            self.asset.timeline_track_id = track_id
            self.changed(self.asset)
        return super().itemChange(change, value)


class TimelineTextClip(QGraphicsRectItem):
    def __init__(
        self,
        layer: TextLayer,
        pixels_per_second: float,
        y: float,
        resolve_track,
        interaction_changed,
        committed,
        locked: bool,
        clip_height: float,
        timeline_duration: float,
    ) -> None:
        self.layer = layer
        self.pps = pixels_per_second
        self.resolve_track = resolve_track
        self.interaction_changed = interaction_changed
        self.committed = committed
        self.locked = locked
        self.clip_height = clip_height
        self.timeline_duration = timeline_duration
        self.resize_edge: str | None = None
        self.press_scene_x = 0.0
        self.press_start_seconds = 0.0
        self.press_end_seconds = 0.0
        self.before_state: dict | None = None
        width = max(42.0, (layer.end_seconds - layer.start_seconds) * self.pps)
        super().__init__(0, 0, width, clip_height)
        self.setPos(layer.start_seconds * self.pps, y)
        fill, edge = {
            "on_screen_text": ("#a34f9e", "#efb5ea"),
            "dialogue": ("#167f77", "#7fe4d8"),
            "voice_over": ("#9a6530", "#efbd78"),
            "lyrics": ("#6d55a5", "#cbb8f5"),
        }.get(layer.content_role, ("#a34f9e", "#efb5ea"))
        speech_budget = (
            speech_timing_budget(
                layer.text,
                layer.language,
                layer.delivery,
                layer.end_seconds - layer.start_seconds,
            )
            if layer.content_role in {"dialogue", "voice_over", "lyrics"}
            else None
        )
        if speech_budget and speech_budget["risk"]:
            fill, edge = "#8f1d25", "#ff4b55"
        self.setBrush(QColor(fill))
        self.setPen(QPen(QColor(edge), 1))
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.ItemIsMovable, not locked)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.OpenHandCursor)
        label = self.layer.text.replace("\n", " ").strip() or "Text"
        role_prefix = {
            "on_screen_text": "TXT", "dialogue": "DIA", "voice_over": "VO", "lyrics": "LYR"
        }.get(layer.content_role, "TXT")
        if speech_budget and speech_budget["risk"]:
            role_prefix = "! " + role_prefix
        self.label = QGraphicsSimpleTextItem(f"{role_prefix}  {label}", self)
        self.label.setBrush(QColor("white"))
        self.label.setPos(5, max(0.0, (clip_height - 14) / 2))
        self.left_handle = QGraphicsRectItem(self)
        self.right_handle = QGraphicsRectItem(self)
        for handle in (self.left_handle, self.right_handle):
            handle.setBrush(QColor(255, 255, 255, 165))
            handle.setPen(QPen(Qt.NoPen))
        self._position_handles()
        self.setToolTip(
            "Text layer · use Type Tool to edit · drag body to move · "
            "drag either bright edge to trim · Delete removes"
        )

    def _position_handles(self) -> None:
        width = self.rect().width()
        handle_height = max(8.0, self.clip_height - 2)
        self.left_handle.setRect(QRectF(1, 1, 4, handle_height))
        self.right_handle.setRect(QRectF(max(1.0, width - 5), 1, 4, handle_height))

    def hoverMoveEvent(self, event) -> None:  # noqa: N802
        x = event.pos().x()
        if x <= 9 or x >= self.rect().width() - 9:
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.locked:
            super().mousePressEvent(event)
            return
        self.interaction_changed(True)
        self.before_state = asdict(self.layer)
        self.press_scene_x = event.scenePos().x()
        self.press_start_seconds = self.layer.start_seconds
        self.press_end_seconds = self.layer.end_seconds
        local_x = event.pos().x()
        if local_x <= 9:
            self.resize_edge = "left"
        elif local_x >= self.rect().width() - 9:
            self.resize_edge = "right"
        else:
            self.resize_edge = None
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self.locked:
            super().mouseMoveEvent(event)
            return
        if not self.resize_edge:
            super().mouseMoveEvent(event)
            return
        delta_seconds = (event.scenePos().x() - self.press_scene_x) / self.pps
        if self.resize_edge == "left":
            proposed_start = snap_timeline_seconds(
                self.press_start_seconds + delta_seconds,
                self.timeline_duration,
            )
            new_start = min(
                self.press_end_seconds - TIMELINE_SNAP_SECONDS,
                proposed_start,
            )
            new_start = max(0.0, new_start)
            self.layer.start_seconds = new_start
            self.layer.end_seconds = self.press_end_seconds
            self.setPos(new_start * self.pps, self.y())
        else:
            proposed_end = snap_timeline_seconds(
                self.press_end_seconds + delta_seconds,
                self.timeline_duration,
            )
            new_end = max(
                self.press_start_seconds + TIMELINE_SNAP_SECONDS,
                proposed_end,
            )
            self.layer.start_seconds = self.press_start_seconds
            self.layer.end_seconds = min(self.timeline_duration, new_end)
        width = max(
            42.0,
            (self.layer.end_seconds - self.layer.start_seconds) * self.pps,
        )
        self.setRect(0, 0, width, self.clip_height)
        self._position_handles()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self.locked:
            super().mouseReleaseEvent(event)
            return
        super().mouseReleaseEvent(event)
        self.setCursor(Qt.OpenHandCursor)
        before = dict(self.before_state) if self.before_state else None
        after = asdict(self.layer)
        layer = self.layer
        callback = self.committed
        self.before_state = None
        self.resize_edge = None
        self.interaction_changed(False)
        if before and before != after:
            QTimer.singleShot(
                0,
                lambda item=layer, old=before, new=after: callback(item, old, new),
            )

    def itemChange(self, change, value):  # noqa: N802
        if self.resize_edge and change in {
            QGraphicsItem.ItemPositionChange,
            QGraphicsItem.ItemPositionHasChanged,
        }:
            return super().itemChange(change, value)
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            point = value
            layer_duration = max(
                TIMELINE_SNAP_SECONDS,
                self.layer.end_seconds - self.layer.start_seconds,
            )
            max_start = max(0.0, self.timeline_duration - layer_duration)
            snapped_seconds = min(
                max_start,
                snap_timeline_seconds(point.x() / self.pps, self.timeline_duration),
            )
            point.setX(snapped_seconds * self.pps)
            track_id, clip_y, _height = self.resolve_track(point.y())
            point.setY(clip_y)
            self.layer.track_id = track_id
            return point
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            duration = self.layer.end_seconds - self.layer.start_seconds
            self.layer.start_seconds = max(0.0, self.x() / self.pps)
            self.layer.end_seconds = self.layer.start_seconds + duration
            self.layer.track_id, _y, _height = self.resolve_track(self.y())
        return super().itemChange(change, value)


class TimelineCueItem(QGraphicsRectItem):
    COLORS = {
        "shot": "#7b57b5",
        "transition": "#b57537",
        "marker": "#3b8a88",
        "cut": "#c75252",
    }

    def __init__(self, cue: DirectorCue, pixels_per_second: float, lane_y: float) -> None:
        self.cue = cue
        duration = max(0.10, cue.end_seconds - cue.start_seconds)
        width = max(10.0, duration * pixels_per_second)
        super().__init__(0, 0, width, DIRECTOR_LANE_HEIGHT - 2)
        self.setPos(cue.start_seconds * pixels_per_second, lane_y + 1)
        speech_reminder = cue.preset.startswith(SPEECH_TIMELINE_MARKER_PREFIX)
        self.setBrush(QColor("#c43d4b" if speech_reminder else self.COLORS.get(cue.cue_type, "#5f6670")))
        self.setPen(QPen(QColor("#ffd7dc" if speech_reminder else "#d7dde4"), 1))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        shot_number = cue.cue_id[1:] if cue.cue_id.startswith("S") else cue.cue_id
        label = (
            f"SHOT {shot_number} · {cue.start_seconds:.2f}–{cue.end_seconds:.2f}s"
            if cue.cue_type == "shot"
            else cue.preset or cue.cue_type.upper()
        )
        self.label = QGraphicsSimpleTextItem(label, self)
        self.label.setBrush(QColor("white"))
        self.label.setPos(4, 0)
        self.setToolTip(
            f"{cue.cue_type.title()} · {cue.start_seconds:.2f}s–{cue.end_seconds:.2f}s"
            + (f"\n{cue.detail}" if cue.detail else "")
        )
        if cue.cue_type == "shot":
            self.setToolTip(
                "\n".join(
                    row
                    for row in (
                        label,
                        f"{cue.framing} · {cue.camera_angle}",
                        f"{cue.camera_movement} · {cue.movement_speed} · {cue.movement_amplitude} amplitude",
                        cue.subject_action,
                        cue.environment_response,
                        *(
                            f"AI media reference: {direction}"
                            for direction in cue.semantic_reference_directions.values()
                        ),
                        f"Preset: {cue.preset}",
                    )
                    if row
                )
            )


class TimelineView(QGraphicsView):
    asset_selected = Signal(object)
    asset_changed = Signal(object)
    playhead_changed = Signal(float)
    asset_edit_committed = Signal(object, object, object)
    clip_instance_created = Signal(object)
    remove_requested = Signal(object)
    empty_slot_dropped = Signal(object)
    track_selected = Signal(object)
    track_property_requested = Signal(object, str, object)
    zoom_changed = Signal(float)
    prompt_requested = Signal(object)
    type_targeted = Signal(object)
    text_create_requested = Signal(float, str)
    text_selected = Signal(object)
    text_edit_requested = Signal(object)
    text_edit_committed = Signal(object, object, object)
    text_remove_requested = Signal(object)
    cue_create_requested = Signal(str, float)
    shot_range_requested = Signal(float, float, str)
    cue_edit_requested = Signal(object)
    cue_remove_requested = Signal(object)
    razor_asset_requested = Signal(object, float)
    razor_text_requested = Signal(object, float)
    razor_cue_requested = Signal(object, float)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor("#111315"))
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.pps = 70.0
        self.origin_x = 0.0
        self.duration = 12.0
        self.playhead_seconds = 0.0
        self.tool_mode = "selection"
        self.tracks = default_timeline_tracks()
        self.text_layers: list[TextLayer] = []
        # Exact user-authored timed text is retained separately from editable
        # Timeline objects so Apply/Run can detect accidental silent loss.
        self.authored_text_requirements: list[dict] = []
        self.director_cues: list[DirectorCue] = []
        self.render_segments: list[dict] = []
        self.scan: WorkflowScan | None = None
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        self.scene_rebuild_timer = QTimer(self)
        self.scene_rebuild_timer.setSingleShot(True)
        self.scene_rebuild_timer.timeout.connect(self._run_scheduled_rebuild)
        self.interaction_active = False
        self.rebuild_pending = False
        self.rendered_track_heights: dict[str, int] = {}
        self.playhead = QGraphicsLineItem()
        self.playhead.setPen(QPen(QColor("#e2c74f"), 2))
        self.shot_drag_start_seconds: float | None = None
        self.shot_drag_track_id = ""
        self.shot_drag_item: QGraphicsRectItem | None = None
        self.playhead_scrub_active = False

    def set_workflow(self, scan: WorkflowScan) -> None:
        self.scan = scan
        self.duration = max(scan.duration_seconds, 1.0)
        self.playhead_seconds = 0.0
        self.rebuild()

    def set_duration(self, duration: float) -> None:
        """Resize the Timeline scene without resetting the current playhead."""
        self.duration = max(float(duration), 1.0)
        self.playhead_seconds = min(self.playhead_seconds, self.duration)
        self.rebuild()

    def set_tracks(self, tracks: list[TimelineTrack]) -> None:
        self.tracks = tracks
        self.schedule_rebuild()

    def set_text_layers(self, layers: list[TextLayer]) -> None:
        self.text_layers = layers
        self.schedule_rebuild()

    def set_director_cues(self, cues: list[DirectorCue]) -> None:
        self.director_cues = cues
        # Cue edits often finish from a modal dialog that itself was opened by
        # a mouse-release callback. Clearing a QGraphicsScene synchronously in
        # that nested Qt stack can corrupt the Windows heap. Rebuild only after
        # the originating event/dialog has completely unwound.
        self.schedule_rebuild()

    def set_render_segments(self, segments: list[dict]) -> None:
        self.render_segments = [dict(row) for row in segments]
        self.schedule_rebuild()

    def schedule_rebuild(self, delay_ms: int = 0) -> None:
        self.rebuild_pending = True
        if not self.scene_rebuild_timer.isActive():
            self.scene_rebuild_timer.start(max(0, delay_ms))

    def _run_scheduled_rebuild(self) -> None:
        if self.interaction_active:
            self.scene_rebuild_timer.start(10)
            return
        self.rebuild()

    def set_tool_mode(self, mode: str) -> None:
        allowed_modes = {
            "selection", "type", "prompt", "hand", "razor", "shot", "transition", "marker"
        }
        self.tool_mode = mode if mode in allowed_modes else "selection"
        self.setInteractive(self.tool_mode != "hand")
        if self.tool_mode == "selection":
            self.setDragMode(QGraphicsView.RubberBandDrag)
        elif self.tool_mode == "hand":
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QGraphicsView.NoDrag)
        self.viewport().setCursor(
            Qt.ArrowCursor
            if self.tool_mode == "selection"
            else Qt.IBeamCursor
            if self.tool_mode == "type"
            else Qt.OpenHandCursor
            if self.tool_mode == "hand"
            else Qt.CrossCursor
        )

    def set_zoom(self, pixels_per_second: float) -> None:
        pixels_per_second = max(20.0, min(240.0, float(pixels_per_second)))
        if abs(pixels_per_second - self.pps) < 0.01:
            return
        viewport_center = self.mapToScene(self.viewport().rect().center())
        center_seconds = max(0.0, (viewport_center.x() - self.origin_x) / self.pps)
        self.pps = pixels_per_second
        self.rebuild()
        self.centerOn(self.origin_x + center_seconds * self.pps, viewport_center.y())
        self.zoom_changed.emit(self.pps)

    def _track_top(self, index: int) -> float:
        return float(TIMELINE_TRACKS_TOP + sum(track.height for track in self.tracks[:index]))

    def _track_for_asset(self, asset: MediaAsset) -> tuple[int, TimelineTrack]:
        wanted_kind = "audio" if asset.media_type == "audio" else "visual"
        for index, track in enumerate(self.tracks):
            if track.track_id == asset.timeline_track_id and track.kind == wanted_kind:
                return index, track
        lane = self._compatible_lane(asset, asset.timeline_lane)
        return lane, self.tracks[lane]

    def _resolve_track(self, asset: MediaAsset, scene_y: float) -> tuple[int, str, float, float]:
        wanted_kind = "audio" if asset.media_type == "audio" else "visual"
        allowed = [
            (index, track)
            for index, track in enumerate(self.tracks)
            if track.kind == wanted_kind and not track.locked
        ]
        if not allowed:
            allowed = [
                (index, track)
                for index, track in enumerate(self.tracks)
                if track.kind == wanted_kind
            ]
        index, track = min(
            allowed,
            key=lambda item: abs(
                self._track_top(item[0]) + item[1].height / 2 - scene_y
            ),
        )
        return index, track.track_id, self._track_top(index) + 2, max(12.0, track.height - 4)

    def _resolve_text_track(
        self,
        scene_y: float,
        content_role: str = "on_screen_text",
    ) -> tuple[str, float, float]:
        wanted_kind = text_layer_track_kind(content_role)
        allowed = [
            (index, track)
            for index, track in enumerate(self.tracks)
            if track.kind == wanted_kind and not track.locked
        ]
        if not allowed:
            allowed = [
                (index, track)
                for index, track in enumerate(self.tracks)
                if track.kind == wanted_kind
            ]
        index, track = min(
            allowed,
            key=lambda item: abs(self._track_top(item[0]) + item[1].height / 2 - scene_y),
        )
        return track.track_id, self._track_top(index) + 2, max(12.0, track.height - 4)

    def _visual_track_at(self, scene_y: float) -> tuple[int, TimelineTrack] | None:
        for index, track in enumerate(self.tracks):
            top = self._track_top(index)
            if top <= scene_y < top + track.height and track.kind == "visual" and not track.locked:
                return index, track
        return None

    def rebuild(self) -> None:
        if self.interaction_active:
            self.rebuild_pending = True
            return
        if self.scene_rebuild_timer.isActive():
            self.scene_rebuild_timer.stop()
        self.rebuild_pending = False
        # Swap scenes instead of synchronously deleting every QGraphicsItem via
        # QGraphicsScene.clear(). PySide wrappers can outlive the originating
        # native event by one event-loop turn; deleteLater keeps their C++
        # ownership valid until Qt is safely idle and also avoids GC-time heap
        # corruption from stale item wrappers.
        old_scene = self.scene_obj
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        old_scene.deleteLater()
        self.rendered_track_heights = {track.track_id: track.height for track in self.tracks}
        scene_height = float(TIMELINE_TRACKS_TOP + sum(track.height for track in self.tracks))
        width = max(900.0, self.origin_x + self.duration * self.pps + 80)
        grid_steps = int(self.duration / TIMELINE_SNAP_SECONDS) + 2
        for step_index in range(grid_steps):
            seconds = step_index * TIMELINE_SNAP_SECONDS
            x = self.origin_x + seconds * self.pps
            is_full_second = step_index % 2 == 0
            grid_color = QColor("#2b3036" if is_full_second else "#20242a")
            self.scene_obj.addLine(x, DIRECTOR_LANES_TOP, x, scene_height, QPen(grid_color))
            tick_top = 10 if is_full_second else 14
            tick_color = QColor("#858c94" if is_full_second else "#596068")
            self.scene_obj.addLine(
                x, tick_top, x, TIMELINE_RULER_HEIGHT - 1, QPen(tick_color)
            )
            if is_full_second:
                label = self.scene_obj.addSimpleText(f"{int(seconds):02d}s")
                label.setBrush(QColor("#8c9299"))
                label.setPos(x + 3, 3)
        status_colors = {
            "reusable": QColor("#2f9d57"),
            "dirty": QColor("#d4a72c"),
            "running": QColor("#258bc4"),
            "failed": QColor("#c84d4d"),
            "pending": QColor("#596068"),
        }
        self.scene_obj.addRect(
            0,
            TIMELINE_RULER_HEIGHT,
            width,
            RENDER_STATUS_BAR_HEIGHT,
            QPen(Qt.NoPen),
            QBrush(QColor("#30343a")),
        )
        ordered_render = sorted(
            self.render_segments,
            key=lambda row: (float(row.get("start_seconds", 0.0)), int(row.get("index", 0))),
        )
        for index, row in enumerate(ordered_render):
            actual_start = float(row.get("start_seconds", 0.0))
            actual_end = float(row.get("end_seconds", actual_start))
            display_start = actual_start
            display_end = actual_end
            if index:
                previous_end = float(ordered_render[index - 1].get("end_seconds", actual_start))
                if actual_start < previous_end:
                    display_start = (actual_start + previous_end) / 2.0
            if index + 1 < len(ordered_render):
                next_start = float(ordered_render[index + 1].get("start_seconds", actual_end))
                if next_start < actual_end:
                    display_end = (next_start + actual_end) / 2.0
            status = str(row.get("display_status", row.get("status", "pending")))
            rect = self.scene_obj.addRect(
                self.origin_x + display_start * self.pps,
                TIMELINE_RULER_HEIGHT,
                max(1.0, (display_end - display_start) * self.pps),
                RENDER_STATUS_BAR_HEIGHT,
                QPen(QColor("#151719"), 0.5),
                QBrush(status_colors.get(status, status_colors["pending"])),
            )
            rect.setData(0, "render-status")
            rect.setData(1, str(row.get("segment_id", "")))
            rect.setData(2, status)
            label = {
                "reusable": "Generated · reusable",
                "dirty": "Edited · needs render",
                "running": "Rendering",
                "failed": "Render failed",
                "pending": "Not generated",
            }.get(status, status)
            shot_ids = ", ".join(str(value) for value in (row.get("shot_ids") or []))
            shot_label = f" · Shots: {shot_ids}" if shot_ids else ""
            rect.setToolTip(
                f"{row.get('segment_id', 'Segment')} · {actual_start:.2f}–{actual_end:.2f}s"
                f" · {label}{shot_label}"
            )

        cue_lane_y = {
            "shot": DIRECTOR_LANES_TOP,
            "transition": DIRECTOR_LANES_TOP + DIRECTOR_LANE_HEIGHT,
            "marker": DIRECTOR_LANES_TOP + DIRECTOR_LANE_HEIGHT * 2,
            "cut": DIRECTOR_LANES_TOP,
        }
        for lane_index in range(len(DIRECTOR_LANE_TYPES) + 1):
            y = DIRECTOR_LANES_TOP + lane_index * DIRECTOR_LANE_HEIGHT
            self.scene_obj.addLine(0, y, width, y, QPen(QColor("#34383d")))
        for cue in self.director_cues:
            cue_item = TimelineCueItem(cue, self.pps, cue_lane_y.get(cue.cue_type, cue_lane_y["marker"]))
            cue_item.setZValue(2)
            self.scene_obj.addItem(cue_item)
        for index, track in enumerate(self.tracks):
            y = self._track_top(index)
            self.scene_obj.addLine(0, y, width, y, QPen(QColor("#34383d")))
            self.scene_obj.addLine(0, y + track.height - 1, width, y + track.height - 1, QPen(QColor("#292d31")))
        if self.scan:
            for asset in self.scan.timeline_assets():
                if not asset.timeline_placed:
                    continue
                lane, track = self._track_for_asset(asset)
                asset.timeline_lane = lane
                asset.timeline_track_id = track.track_id
                y = self._track_top(lane) + 2
                clip = TimelineClip(
                    asset,
                    self.pps,
                    self.origin_x,
                    y,
                    self.asset_changed.emit,
                    self.asset_edit_committed.emit,
                    self._set_interaction_active,
                    self._resolve_track,
                    track.locked,
                    max(12.0, track.height - 4),
                    self.duration,
                )
                clip.setBrush(QColor(track.color))
                if not track.enabled:
                    clip.setOpacity(0.25)
                self.scene_obj.addItem(clip)
        for layer in self.text_layers:
            wanted_kind = text_layer_track_kind(layer.content_role)
            track = next(
                (
                    item
                    for item in self.tracks
                    if item.track_id == layer.track_id and item.kind == wanted_kind
                ),
                next(item for item in self.tracks if item.kind == wanted_kind),
            )
            index = self.tracks.index(track)
            layer.track_id = track.track_id
            text_clip = TimelineTextClip(
                layer,
                self.pps,
                self._track_top(index) + 2,
                lambda scene_y, role=layer.content_role: self._resolve_text_track(
                    scene_y, role
                ),
                self._set_interaction_active,
                self.text_edit_committed.emit,
                track.locked,
                max(12.0, track.height - 4),
                self.duration,
            )
            text_clip.setOpacity(0.25 if not track.enabled or not track.visible else 0.45 if track.locked else 1.0)
            text_clip.setZValue(1)
            self.scene_obj.addItem(text_clip)
        playhead_x = self.origin_x + self.playhead_seconds * self.pps
        self.playhead = self.scene_obj.addLine(
            playhead_x, 0, playhead_x, scene_height, QPen(QColor("#f1d34f"), 2)
        )
        self.scene_obj.setSceneRect(0, 0, width, scene_height)

    def refresh_track(self, track: TimelineTrack) -> None:
        """Refresh clip visuals, rebuilding only when lane geometry changed."""
        if self.rendered_track_heights.get(track.track_id) != track.height:
            self.rebuild()
            return
        for item in self.scene_obj.items():
            if isinstance(item, TimelineClip):
                _lane, item_track = self._track_for_asset(item.asset)
                if item_track is not track:
                    continue
                item.locked = track.locked
                item.setFlag(QGraphicsItem.ItemIsMovable, not track.locked)
                item.setBrush(QColor(track.color))
                item.setOpacity(0.25 if not track.enabled else 0.45 if track.locked else 1.0)
            elif isinstance(item, TimelineTextClip) and item.layer.track_id == track.track_id:
                item.locked = track.locked
                item.setFlag(QGraphicsItem.ItemIsMovable, not track.locked)
                item.setOpacity(
                    0.25
                    if not track.enabled or not track.visible
                    else 0.45
                    if track.locked
                    else 1.0
                )
        self.viewport().update()

    def _set_interaction_active(self, active: bool) -> None:
        self.interaction_active = active
        if not active and self.rebuild_pending:
            self.schedule_rebuild()

    def set_playhead(
        self,
        seconds: float,
        emit_signal: bool = False,
        *,
        snap_to_grid: bool | None = None,
    ) -> None:
        if snap_to_grid is None:
            snap_to_grid = emit_signal
        self.playhead_seconds = (
            snap_timeline_seconds(seconds, self.duration) if snap_to_grid
            else min(self.duration, max(0.0, seconds))
        )
        x = self.origin_x + self.playhead_seconds * self.pps
        self.playhead.setLine(x, 0, x, self.scene_obj.sceneRect().height())
        if emit_signal:
            self.playhead_changed.emit(self.playhead_seconds)

    def _compatible_lane(self, asset: MediaAsset, requested: int) -> int:
        wanted_kind = "audio" if asset.media_type == "audio" else "visual"
        allowed = [index for index, track in enumerate(self.tracks) if track.kind == wanted_kind]
        return min(allowed, key=lambda lane: abs(lane - requested))

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(MIME_SLOT):
            event.setDropAction(Qt.CopyAction)
            event.accept()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(MIME_SLOT):
            event.setDropAction(Qt.CopyAction)
            event.accept()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        if not self.scan or not event.mimeData().hasFormat(MIME_SLOT):
            return super().dropEvent(event)
        node_id = bytes(event.mimeData().data(MIME_SLOT)).decode("utf-8")
        asset = next((item for item in self.scan.assets if item.node_id == node_id), None)
        if asset:
            if not asset.local_path and not asset.filename:
                event.setDropAction(Qt.CopyAction)
                event.accept()
                QTimer.singleShot(0, lambda item=asset: self.empty_slot_dropped.emit(item))
                return
            before = timeline_state(asset)
            scene_point = self.mapToScene(event.position().toPoint())
            seconds = snap_timeline_seconds(
                (scene_point.x() - self.origin_x) / self.pps,
                self.duration,
            )
            requested_lane, requested_track_id, _clip_y, _clip_height = self._resolve_track(
                asset, scene_point.y()
            )
            create_instance = asset.timeline_placed
            if create_instance:
                source = asset
                asset = deepcopy(source)
                asset.clip_id = f"clip-{secrets.token_hex(8)}"
                asset.source_node_id = source.node_id
                # Recognition and file identity remain source-owned. Timeline
                # properties below are independently editable on this clone.
                asset.timeline_placed = False
            if create_instance:
                length = max(0.25, source.end_seconds - source.start_seconds)
            elif asset.timeline_placed:
                length = max(0.25, asset.end_seconds - asset.start_seconds)
            elif asset.media_type == "image":
                length = 3.0
            else:
                length = asset.source_duration_seconds or 3.0
            after = dict(before)
            after["timeline_lane"] = requested_lane
            after["timeline_track_id"] = requested_track_id
            after["timeline_placed"] = True
            after["start_seconds"] = min(
                seconds,
                max(0.0, self.duration - TIMELINE_SNAP_SECONDS),
            )
            snapped_length = max(
                TIMELINE_SNAP_SECONDS,
                snap_timeline_seconds(length),
            )
            after["end_seconds"] = min(
                self.duration,
                after["start_seconds"] + snapped_length,
            )
            event.setDropAction(Qt.CopyAction)
            event.accept()
            self.viewport().update()
            # Never clear/rebuild a QGraphicsScene while Qt is still unwinding
            # the native drag/drop event. This is especially important when an
            # empty Media Pool slot has no preview object keeping the source
            # widget alive during QDrag.exec().
            QTimer.singleShot(
                0,
                lambda item=asset, old=before, new=after, created=create_instance: self._finish_media_drop(
                    item, old, new, created
                ),
            )
            return
        event.ignore()

    def _finish_media_drop(
        self, asset: MediaAsset, before: dict, after: dict, created: bool = False
    ) -> None:
        if self.scan is None:
            return
        if created:
            for name, value in after.items():
                setattr(asset, name, value)
            self.clip_instance_created.emit(asset)
        elif asset in self.scan.assets:
            self.asset_edit_committed.emit(asset, before, after)
        else:
            return
        self.asset_selected.emit(asset)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.tool_mode == "hand":
            super().mousePressEvent(event)
            return
        item = self.itemAt(event.position().toPoint())
        while item and not isinstance(item, (TimelineClip, TimelineTextClip, TimelineCueItem)):
            item = item.parentItem()
        scene_point = self.mapToScene(event.position().toPoint())
        raw_seconds = min(
            self.duration,
            max(0.0, (scene_point.x() - self.origin_x) / self.pps),
        )
        clicked_seconds = snap_timeline_seconds(
            raw_seconds,
            self.duration,
        )
        if isinstance(item, TimelineCueItem):
            if self.tool_mode == "razor":
                self.razor_cue_requested.emit(item.cue, clicked_seconds)
            elif self.tool_mode in {"selection", item.cue.cue_type}:
                self.cue_edit_requested.emit(item.cue)
            event.accept()
            return
        if self.tool_mode == "shot" and event.button() == Qt.LeftButton:
            visual_target = self._visual_track_at(scene_point.y())
            if visual_target is not None:
                track_index, track = visual_target
                self.shot_drag_start_seconds = clicked_seconds
                self.shot_drag_track_id = track.track_id
                preview_color = QColor("#956ad6")
                preview_color.setAlpha(150)
                self.shot_drag_item = self.scene_obj.addRect(
                    clicked_seconds * self.pps,
                    self._track_top(track_index) + 2,
                    2.0,
                    max(12.0, track.height - 4),
                    QPen(QColor("#e6d6ff"), 1),
                    QBrush(preview_color),
                )
                self.shot_drag_item.setZValue(20)
                self.interaction_active = True
                event.accept()
                return
        if isinstance(item, TimelineTextClip):
            if self.tool_mode == "razor":
                self.razor_text_requested.emit(item.layer, clicked_seconds)
                event.accept()
                return
            if self.tool_mode == "type":
                self.text_edit_requested.emit(item.layer)
                event.accept()
                return
            self.text_selected.emit(item.layer)
        elif isinstance(item, TimelineClip):
            if self.tool_mode == "razor":
                self.razor_asset_requested.emit(item.asset, clicked_seconds)
                event.accept()
                return
            if self.tool_mode == "prompt":
                self.prompt_requested.emit(item.asset)
                event.accept()
                return
            if self.tool_mode == "type":
                self.type_targeted.emit(item.asset)
                event.accept()
                return
            self.asset_selected.emit(item.asset)
            _lane, track = self._track_for_asset(item.asset)
            self.track_selected.emit(track)
        elif event.button() == Qt.LeftButton:
            if self.tool_mode in {"transition", "marker"}:
                self.cue_create_requested.emit(self.tool_mode, clicked_seconds)
                event.accept()
                return
            if self.tool_mode == "type":
                track_id, _y, _height = self._resolve_text_track(scene_point.y())
                seconds = clicked_seconds
                self.text_create_requested.emit(seconds, track_id)
                event.accept()
                return
            self.playhead_scrub_active = self.tool_mode == "selection"
            self.set_playhead(
                raw_seconds,
                emit_signal=True,
                snap_to_grid=False,
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self.playhead_scrub_active and self.tool_mode == "selection":
            scene_x = self.mapToScene(event.position().toPoint()).x()
            seconds = min(
                self.duration,
                max(0.0, (scene_x - self.origin_x) / self.pps),
            )
            self.set_playhead(seconds, emit_signal=True, snap_to_grid=False)
            event.accept()
            return
        if self.tool_mode == "shot" and self.shot_drag_start_seconds is not None:
            current = snap_timeline_seconds(
                (self.mapToScene(event.position().toPoint()).x() - self.origin_x) / self.pps,
                self.duration,
            )
            start = min(self.shot_drag_start_seconds, current)
            end = max(self.shot_drag_start_seconds, current)
            if end - start < TIMELINE_SNAP_SECONDS:
                end = min(self.duration, start + TIMELINE_SNAP_SECONDS)
            if self.shot_drag_item is not None:
                rect = self.shot_drag_item.rect()
                self.shot_drag_item.setRect(
                    start * self.pps,
                    rect.y(),
                    max(2.0, (end - start) * self.pps),
                    rect.height(),
                )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self.playhead_scrub_active:
            self.playhead_scrub_active = False
            event.accept()
            return
        if self.tool_mode == "shot" and self.shot_drag_start_seconds is not None:
            current = snap_timeline_seconds(
                (self.mapToScene(event.position().toPoint()).x() - self.origin_x) / self.pps,
                self.duration,
            )
            start = min(self.shot_drag_start_seconds, current)
            end = max(self.shot_drag_start_seconds, current)
            if end - start < TIMELINE_SNAP_SECONDS:
                end = min(self.duration, start + TIMELINE_SNAP_SECONDS)
            track_id = self.shot_drag_track_id
            preview = self.shot_drag_item
            self.shot_drag_start_seconds = None
            self.shot_drag_track_id = ""
            self.shot_drag_item = None
            self.interaction_active = False
            if preview is not None and preview.scene() is self.scene_obj:
                self.scene_obj.removeItem(preview)
            if end - start >= TIMELINE_SNAP_SECONDS:
                QTimer.singleShot(
                    0,
                    lambda shot_start=start, shot_end=end, target=track_id: self.shot_range_requested.emit(
                        shot_start, shot_end, target
                    ),
                )
            event.accept()
            if self.rebuild_pending:
                self.schedule_rebuild()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: N802
        if event.modifiers() & Qt.ControlModifier:
            direction = 1 if event.angleDelta().y() > 0 else -1
            self.set_zoom(self.pps * (1.12 if direction > 0 else 1 / 1.12))
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            text_selected = next(
                (item for item in self.scene_obj.selectedItems() if isinstance(item, TimelineTextClip)),
                None,
            )
            if text_selected:
                self.text_remove_requested.emit(text_selected.layer)
                event.accept()
                return
            cue_selected = next(
                (item for item in self.scene_obj.selectedItems() if isinstance(item, TimelineCueItem)),
                None,
            )
            if cue_selected:
                self.cue_remove_requested.emit(cue_selected.cue)
                event.accept()
                return
            selected = next((item for item in self.scene_obj.selectedItems() if isinstance(item, TimelineClip)), None)
            if selected:
                self.remove_requested.emit(selected.asset)
                event.accept()
                return
        super().keyPressEvent(event)


class CompactSecondsSpinBox(QDoubleSpinBox):
    """Keep sub-second values while displaying compact labels such as 0s/15s."""

    def textFromValue(self, value: float) -> str:  # noqa: N802
        text = f"{float(value):.2f}".rstrip("0").rstrip(".")
        return f"{text}s"

    def valueFromText(self, text: str) -> float:  # noqa: N802
        cleaned = str(text).strip().lower().removesuffix("s").strip()
        try:
            return float(cleaned)
        except ValueError:
            return self.value()


class PrecisionScrubSlider(QSlider):
    """A millisecond transport slider with anchored, non-jumping drag."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Horizontal, parent)
        self.setTracking(True)
        self.setSingleStep(1)
        self.setPageStep(100)
        self._drag_anchor_x = 0.0
        self._drag_anchor_value = 0

    def _drag_value_at_x(self, x: float) -> int:
        span = max(1.0, float(self.width() - 1))
        value_span = self.maximum() - self.minimum()
        delta = round((float(x) - self._drag_anchor_x) * value_span / span)
        return max(
            self.minimum(),
            min(self.maximum(), self._drag_anchor_value + delta),
        )

    def _drag_to_x(self, x: float) -> None:
        value = self._drag_value_at_x(x)
        self.setValue(value)
        self.sliderMoved.emit(value)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_anchor_x = float(event.position().x())
            self._drag_anchor_value = self.value()
            self.setSliderDown(True)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self.isSliderDown() and event.buttons() & Qt.LeftButton:
            self._drag_to_x(event.position().x())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self.isSliderDown():
            self._drag_to_x(event.position().x())
            self.setSliderDown(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class MonitorSplitPane(QWidget):
    """A splitter pane that can shrink smoothly without native collapse snapping."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(1, 1)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(1, 1)

class ProjectStorageDialog(QDialog):
    """Inspect, safely reclaim and archive one fixed Project Workspace."""

    def __init__(self, workspace: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = Path(workspace).expanduser().resolve()
        self.setWindowTitle("Project Storage · Report / Safe Cleanup / Archive")
        self.resize(820, 620)
        layout = QVBoxLayout(self)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(
            "color:#72d7e5; font-weight:600; padding:8px; "
            "background:#121619; border:1px solid #343a40;"
        )
        layout.addWidget(self.summary)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        layout.addWidget(self.details, 1)
        buttons = QHBoxLayout()
        refresh = QPushButton("REFRESH REPORT")
        refresh.clicked.connect(self.refresh_report)
        self.cleanup_button = QPushButton("SAFE CLEANUP")
        self.cleanup_button.clicked.connect(self.safe_cleanup)
        archive = QPushButton("ARCHIVE PROJECT")
        archive.clicked.connect(self.archive_project)
        close = QPushButton("CLOSE")
        close.clicked.connect(self.accept)
        buttons.addWidget(refresh)
        buttons.addWidget(self.cleanup_button)
        buttons.addWidget(archive)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self.refresh_report()

    @staticmethod
    def _size(value: int) -> str:
        amount = float(max(0, int(value)))
        for suffix in ("B", "KB", "MB", "GB", "TB"):
            if amount < 1024.0 or suffix == "TB":
                return f"{amount:.2f} {suffix}"
            amount /= 1024.0
        return f"{amount:.2f} TB"

    def refresh_report(self) -> None:
        try:
            report = build_storage_report(self.workspace)
            cleanup = safe_cleanup_plan(self.workspace)
        except Exception as exc:
            self.summary.setText(f"Storage Report failed · {exc}")
            self.details.setPlainText(str(exc))
            self.cleanup_button.setEnabled(False)
            return
        self.cleanup_button.setEnabled(bool(cleanup["candidate_count"]))
        self.summary.setText(
            f"{self.workspace.name} · {report['file_count']} files · "
            f"logical {self._size(report['logical_bytes'])} · "
            f"physical {self._size(report['physical_bytes'])} · "
            f"safe cleanup {self._size(cleanup['reclaimable_bytes'])}"
        )
        lines = [
            f"Workspace: {self.workspace}",
            f"Hard-link storage saved: {self._size(report['hardlink_saved_bytes'])}",
            f"Copied duplicate physical bytes: {self._size(report['duplicate_physical_bytes'])}",
            "",
            "CATEGORY                                  FILES          LOGICAL",
        ]
        for name, values in report["categories"].items():
            lines.append(
                f"{name:<40}{values['files']:>6}  {self._size(values['logical_bytes']):>16}"
            )
        lines.extend(
            [
                "",
                f"SAFE CLEANUP DRY RUN · {cleanup['candidate_count']} file(s) · "
                f"{self._size(cleanup['reclaimable_bytes'])}",
            ]
        )
        for row in cleanup["candidates"]:
            lines.append(
                f"- {row['path']} · {self._size(row['bytes'])} · {row['reason']}"
            )
        if not cleanup["candidates"]:
            lines.append("- Nothing disposable was found.")
        lines.extend(["", "PROTECTED"] + [f"- {item}" for item in cleanup["protected_contract"]])
        self.details.setPlainText("\n".join(lines))

    def safe_cleanup(self) -> None:
        plan = safe_cleanup_plan(self.workspace)
        if not plan["candidate_count"]:
            QMessageBox.information(self, "Safe Cleanup", "No verified disposable files were found.")
            return
        choice = QMessageBox.question(
            self,
            "Confirm Safe Cleanup",
            f"Remove {plan['candidate_count']} verified disposable file(s) and reclaim "
            f"{self._size(plan['reclaimable_bytes'])}?\n\n"
            "Generated Masters, Media Pool sources and all Segment Preview/Approved Takes are protected.",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if choice != QMessageBox.Yes:
            return
        result = safe_cleanup_workspace(self.workspace, dry_run=False)
        self.refresh_report()
        QMessageBox.information(
            self,
            "Safe Cleanup complete",
            f"Removed {result['removed_count']} file(s) · "
            f"reclaimed {self._size(result['removed_bytes'])}.",
        )

    def archive_project(self) -> None:
        suggested = self.workspace.parent / f"{self.workspace.name}.h3project.zip"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Archive Project",
            str(suggested),
            "H3 Project Archive (*.h3project.zip);;ZIP archive (*.zip)",
        )
        if not filename:
            return
        if not filename.casefold().endswith((".zip", ".h3project.zip")):
            filename += ".h3project.zip"
        try:
            result = archive_workspace(self.workspace, filename)
        except Exception as exc:
            QMessageBox.critical(self, "Archive Project failed", str(exc))
            return
        QMessageBox.information(
            self,
            "Archive Project complete",
            f"Verified archive: {result['archive']}\n"
            f"Files: {result['file_count']}\n"
            f"Archive size: {self._size(result['archive_bytes'])}\n"
            f"Consolidated external sources: {result['external_source_count']}",
        )


class PromptPresetDialog(QDialog):
    """Choose and edit presets stored together in one category .env file."""

    def __init__(self, root: Path, family: str, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.root = root
        self.family = family
        self.records: list[PromptPresetRecord] = []
        self.selected_record: PromptPresetRecord | None = None
        self.current_record: PromptPresetRecord | None = None
        self.setWindowTitle(title)
        self.resize(760, 520)
        layout = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel("PRESETS — this category uses one shared .env file"))
        self.preset_list = QListWidget()
        self.preset_list.currentRowChanged.connect(self._select_row)
        left.addWidget(self.preset_list, 1)
        new_button = QPushButton("+ NEW PRESET")
        new_button.clicked.connect(self._new_preset)
        left.addWidget(new_button)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("Preset name"))
        self.name_edit = QLineEdit()
        right.addWidget(self.name_edit)
        right.addWidget(QLabel("Preset content"))
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Editable H3 direction saved in this category's .env file")
        right.addWidget(self.text_edit, 1)
        self.path_label = QLabel("New preset — it will be added to this category's .env file")
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color:#7f8993;")
        right.addWidget(self.path_label)
        actions = QHBoxLayout()
        save_button = QPushButton("SAVE CATEGORY .ENV")
        save_button.clicked.connect(self._save_current)
        delete_button = QPushButton("DELETE")
        delete_button.clicked.connect(self._delete_current)
        close_button = QPushButton("CLOSE")
        close_button.clicked.connect(self.reject)
        apply_button = QPushButton("SAVE + APPLY")
        apply_button.setStyleSheet("background:#087f96; font-weight:700;")
        apply_button.clicked.connect(self._apply_current)
        actions.addWidget(save_button)
        actions.addWidget(delete_button)
        actions.addStretch(1)
        actions.addWidget(close_button)
        actions.addWidget(apply_button)
        right.addLayout(actions)
        layout.addLayout(right, 2)
        self._reload()

    def _reload(self, selected_name: str | None = None) -> None:
        self.records = load_prompt_presets(self.root, self.family)
        self.preset_list.blockSignals(True)
        self.preset_list.clear()
        selected_row = 0
        for index, record in enumerate(self.records):
            self.preset_list.addItem(record.name)
            if selected_name and record.name == selected_name:
                selected_row = index
        self.preset_list.blockSignals(False)
        if self.records:
            self.preset_list.setCurrentRow(selected_row)
            self._select_row(selected_row)
        else:
            self._new_preset()

    def _select_row(self, row: int) -> None:
        if not 0 <= row < len(self.records):
            return
        record = self.records[row]
        self.current_record = record
        self.name_edit.setText(record.name)
        self.text_edit.setPlainText(record.text)
        self.path_label.setText(str(record.path))

    def _new_preset(self) -> None:
        self.preset_list.clearSelection()
        self.current_record = None
        self.name_edit.clear()
        self.text_edit.clear()
        self.path_label.setText("New preset — it will be added to this category's .env file")
        self.name_edit.setFocus()

    def _save_current(self) -> PromptPresetRecord | None:
        try:
            record = save_prompt_preset(
                self.root,
                self.family,
                self.name_edit.text(),
                self.text_edit.toPlainText(),
                previous_name=self.current_record.name if self.current_record else None,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Preset not saved", str(exc))
            return None
        self.current_record = record
        self._reload(record.name)
        return self.current_record

    def _delete_current(self) -> None:
        if not self.current_record:
            return
        if QMessageBox.question(
            self,
            "Delete preset",
            f"Delete {self.current_record.name} from {self.current_record.path.name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        delete_prompt_preset(self.root, self.current_record)
        self.current_record = None
        self._reload()

    def _apply_current(self) -> None:
        record = self._save_current()
        if record:
            self.selected_record = record
            self.accept()


class SpecialSkillCreatorDialog(QDialog):
    """Create or edit Studio-native Special Skills without leaving the app."""

    NEW_SKILL = "__new_special_skill__"

    def __init__(self, special_root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.special_root = Path(special_root)
        self.saved_key = ""
        self.editing_key = ""
        self.setWindowTitle("Special Skill Creator")
        self.resize(980, 760)
        self.setMinimumSize(760, 560)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Create a scene-specific H3 planning skill. Default + Special keeps the "
            "official MiniMax H3 prompt structure; Standalone intentionally replaces it."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#aeb9c3;")
        layout.addWidget(intro)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("SPECIAL SKILL"))
        self.skill_selector = QComboBox()
        self.skill_selector.setObjectName("specialSkillCreatorSelector")
        self.skill_selector.setMinimumWidth(320)
        self.skill_selector.currentIndexChanged.connect(self._select_skill)
        selector_row.addWidget(self.skill_selector, 1)
        self.new_button = QPushButton("+ NEW")
        self.new_button.clicked.connect(self._new_skill)
        selector_row.addWidget(self.new_button)
        layout.addLayout(selector_row)

        metadata = QGridLayout()
        metadata.addWidget(QLabel("Folder / key"), 0, 0)
        self.key_edit = QLineEdit()
        self.key_edit.setObjectName("specialSkillKeyEdit")
        self.key_edit.setPlaceholderText("example: cinematic-food-commercial")
        metadata.addWidget(self.key_edit, 0, 1)
        metadata.addWidget(QLabel("Binding"), 0, 2)
        self.binding_combo = QComboBox()
        self.binding_combo.setObjectName("specialSkillBindingCombo")
        self.binding_combo.addItem("Default + Special (Recommended)", False)
        self.binding_combo.addItem("Standalone Special", True)
        metadata.addWidget(self.binding_combo, 0, 3)
        metadata.addWidget(QLabel("Description"), 1, 0)
        self.description_edit = QLineEdit()
        self.description_edit.setObjectName("specialSkillDescriptionEdit")
        self.description_edit.setPlaceholderText(
            "What this Skill does and when Design should use it"
        )
        metadata.addWidget(self.description_edit, 1, 1, 1, 3)
        metadata.setColumnStretch(1, 2)
        metadata.setColumnStretch(3, 1)
        layout.addLayout(metadata)

        template_label = QLabel(
            "DESIGN REQUIREMENT TEMPLATE · optional text inserted when this Special Skill opens Design"
        )
        template_label.setStyleSheet("color:#aeb9c3;")
        layout.addWidget(template_label)
        self.requirement_template_edit = QPlainTextEdit()
        self.requirement_template_edit.setObjectName("specialSkillRequirementTemplateEdit")
        self.requirement_template_edit.setPlaceholderText(
            "Example: Create a 45-second scene using this Skill's dialogue, sound and visual rules."
        )
        self.requirement_template_edit.setMaximumHeight(90)
        layout.addWidget(self.requirement_template_edit)

        editors = QSplitter(Qt.Horizontal)
        english_panel = QWidget()
        english_layout = QVBoxLayout(english_panel)
        english_layout.setContentsMargins(0, 0, 0, 0)
        english_layout.addWidget(QLabel("SKILL.md · English instructions used by Studio"))
        self.english_edit = QPlainTextEdit()
        self.english_edit.setObjectName("specialSkillEnglishEdit")
        self.english_edit.setPlaceholderText("Markdown instruction body (frontmatter is automatic)")
        english_layout.addWidget(self.english_edit, 1)
        editors.addWidget(english_panel)

        chinese_panel = QWidget()
        chinese_layout = QVBoxLayout(chinese_panel)
        chinese_layout.setContentsMargins(0, 0, 0, 0)
        chinese_layout.addWidget(QLabel("SKILL.cn.md · 中文对照版本（可选）"))
        self.chinese_edit = QPlainTextEdit()
        self.chinese_edit.setObjectName("specialSkillChineseEdit")
        self.chinese_edit.setPlaceholderText("中文说明；留空则不建立中文版本")
        chinese_layout.addWidget(self.chinese_edit, 1)
        editors.addWidget(chinese_panel)
        editors.setSizes([520, 420])
        layout.addWidget(editors, 1)

        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color:#7f8993;")
        layout.addWidget(self.path_label)

        actions = QHBoxLayout()
        validate_button = QPushButton("VALIDATE")
        validate_button.clicked.connect(self._validate)
        close_button = QPushButton("CLOSE")
        close_button.clicked.connect(self.reject)
        save_button = QPushButton("SAVE + APPLY")
        save_button.setObjectName("saveSpecialSkillButton")
        save_button.setStyleSheet("background:#087f96; font-weight:700;")
        save_button.clicked.connect(self._save_and_apply)
        actions.addWidget(validate_button)
        actions.addStretch(1)
        actions.addWidget(close_button)
        actions.addWidget(save_button)
        layout.addLayout(actions)

        self._reload_selector()

    def _available_skill_folders(self) -> list[Path]:
        if not self.special_root.is_dir():
            return []
        return sorted(
            (
                folder for folder in self.special_root.iterdir()
                if folder.is_dir() and (folder / "SKILL.md").is_file()
            ),
            key=lambda folder: folder.name.casefold(),
        )

    def _reload_selector(self, selected_key: str = "") -> None:
        self.skill_selector.blockSignals(True)
        self.skill_selector.clear()
        self.skill_selector.addItem("Create new Special Skill", self.NEW_SKILL)
        selected_index = 0
        for folder in self._available_skill_folders():
            self.skill_selector.addItem(folder.name, folder.name)
            if selected_key == folder.name:
                selected_index = self.skill_selector.count() - 1
        self.skill_selector.blockSignals(False)
        self.skill_selector.setCurrentIndex(selected_index)
        self._select_skill(selected_index)

    def _new_skill(self) -> None:
        self.skill_selector.setCurrentIndex(0)
        self._load_new_document()

    def _load_new_document(self) -> None:
        self.editing_key = ""
        self.key_edit.setEnabled(True)
        self.key_edit.clear()
        self.description_edit.clear()
        self.binding_combo.setCurrentIndex(0)
        self.english_edit.setPlainText(DEFAULT_SPECIAL_SKILL_BODY)
        self.chinese_edit.clear()
        self.requirement_template_edit.clear()
        self.path_label.setText(
            f"New folder will be saved under: {self.special_root.resolve()}"
        )
        self.key_edit.setFocus()

    def _select_skill(self, _index: int) -> None:
        key = str(self.skill_selector.currentData() or "")
        if not key or key == self.NEW_SKILL:
            self._load_new_document()
            return
        try:
            document = load_special_skill_document(self.special_root / key)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Special Skill not loaded", str(exc))
            self._load_new_document()
            return
        self.editing_key = key
        self.key_edit.setEnabled(False)
        self.key_edit.setText(document.key)
        self.description_edit.setText(document.description)
        self.binding_combo.setCurrentIndex(1 if document.standalone else 0)
        self.english_edit.setPlainText(document.body)
        self.chinese_edit.setPlainText(document.chinese_body)
        self.requirement_template_edit.setPlainText(
            document.design_requirement_template
        )
        self.path_label.setText(str(document.path or (self.special_root / key / "SKILL.md")))

    def _document(self) -> SpecialSkillDocument:
        return SpecialSkillDocument(
            key=self.key_edit.text().strip(),
            description=self.description_edit.text().strip(),
            body=self.english_edit.toPlainText().strip(),
            chinese_body=self.chinese_edit.toPlainText().strip(),
            standalone=bool(self.binding_combo.currentData()),
            design_requirement_template=(
                self.requirement_template_edit.toPlainText().strip()
            ),
        )

    def _validate(self) -> bool:
        try:
            document = self._document()
            render_special_skill(document)
            if document.chinese_body:
                render_special_skill(document, chinese=True)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Special Skill", str(exc))
            return False
        QMessageBox.information(
            self,
            "Special Skill valid",
            "The Skill metadata, binding mode and instruction files are valid.",
        )
        return True

    def _save_and_apply(self) -> None:
        try:
            document = save_special_skill_document(
                self.special_root,
                self._document(),
                editing_key=self.editing_key,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Special Skill not saved", str(exc))
            return
        self.saved_key = document.key
        self.accept()


class PromptPanel(QWidget):
    generate_requested = Signal()
    sync_requested = Signal()
    content_changed = Signal()

    def __init__(self, preset_env_root: Path = PROMPT_PRESET_ENV_ROOT) -> None:
        super().__init__()
        self.preset_env_root = preset_env_root
        self.last_timeline_brief = ""
        ensure_prompt_presets(
            self.preset_env_root, "creative_brief", CREATIVE_BRIEF_PRESETS,
            legacy_families=("creative_brief",),
        )
        ensure_prompt_presets(
            self.preset_env_root, "global_visual_style", VISUAL_STYLE_PRESETS,
            legacy_families=("visual_style",),
        )
        ensure_prompt_presets(
            self.preset_env_root, "transition_language", TRANSITION_STYLE_PRESETS
        )
        ensure_prompt_presets(
            self.preset_env_root, "constraints_and_technical_rules", CONSTRAINT_PRESETS
        )
        ensure_prompt_presets(
            self.preset_env_root, "overall_soundscape", SOUNDSCAPE_PRESETS
        )
        ensure_prompt_presets(
            self.preset_env_root, "non_diegetic_music", MUSIC_PRESETS
        )
        self._build_preset_ui()
        for field in (
            self.brief, self.style, self.shots, self.dialogue, self.transition,
            self.ending, self.constraints, self.soundscape, self.music,
        ):
            field.textChanged.connect(lambda: self.content_changed.emit())

    def _build_preset_ui(self) -> None:
        form = QVBoxLayout(self)
        sync_row = QHBoxLayout()
        self.auto_sync = QCheckBox("AUTO SYNC FROM TIMELINE")
        self.auto_sync.setChecked(True)
        self.auto_sync.setToolTip(
            "Keep Creative Brief, Shots, Dialogue and Ending synchronized with timeline content"
        )
        sync_button = QPushButton("SYNC NOW")
        sync_button.clicked.connect(self.sync_requested)
        sync_row.addWidget(self.auto_sync)
        sync_row.addStretch(1)
        sync_row.addWidget(sync_button)
        form.addLayout(sync_row)
        self.brief, self.brief_preset = self._preset_field(
            form, "Creative brief · automatically reconciled from the current Timeline",
            "Timeline clip prompts and director blocks are summarized here…", 82,
            CREATIVE_BRIEF_PRESETS,
            manage_family="creative_brief",
        )
        self.style, self.style_preset = self._preset_field(
            form, "Global visual style", "Choose one of 32 visual styles…", 68,
            VISUAL_STYLE_PRESETS,
            manage_family="global_visual_style",
        )
        self.shots = self._field(
            form, "Shots · synchronized from Shot Blocks",
            "Structured Shot Tool direction appears here…", 110,
        )
        self.dialogue = self._field(
            form, "Dialogue / on-screen copy · synchronized from Type layers",
            "Timeline dialogue, voice-over, lyrics and on-screen text appear here…", 75,
        )
        self.transition, self.transition_preset = self._preset_field(
            form, "Transition language", "Choose one of 32 transition styles…", 60,
            TRANSITION_STYLE_PRESETS,
            manage_family="transition_language",
        )
        self.ending = self._field(
            form, "Ending / final hold · synchronized from Ending Hold markers",
            "Ending Hold marker direction appears here…", 58,
        )
        self.constraints, self.constraints_preset = self._preset_field(
            form, "Constraints and technical rules",
            "Choose and combine consistency constraints…", 90,
            CONSTRAINT_PRESETS, append=True,
            manage_family="constraints_and_technical_rules",
        )
        self.soundscape, self.soundscape_preset = self._preset_field(
            form, "Overall soundscape", "Choose one of 32 soundscape styles…", 68,
            SOUNDSCAPE_PRESETS,
            manage_family="overall_soundscape",
        )
        self.music, self.music_preset = self._preset_field(
            form, "Non-diegetic music", "Choose one of 32 music styles…", 68,
            MUSIC_PRESETS,
            manage_family="non_diegetic_music",
        )
        button = QPushButton("PROMPT AUTO-GENERATES · REFRESH NOW")
        button.setStyleSheet("background:#087f96; font-weight:700; padding:9px;")
        button.clicked.connect(self.generate_requested)
        form.addWidget(button)
        self.output = QPlainTextEdit()
        self.output.setPlaceholderText("Six-section H3 prompt output")
        self.output.setMinimumHeight(180)
        form.addWidget(self.output, 1)

    def _preset_field(
        self,
        layout: QVBoxLayout,
        title: str,
        placeholder: str,
        height: int,
        presets: dict[str, str],
        *,
        append: bool = False,
        manage_family: str | None = None,
    ) -> tuple[QPlainTextEdit, QComboBox]:
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel(title))
        title_row.addStretch(1)
        manage_button: QPushButton | None = None
        if manage_family:
            manage_button = QPushButton("EDIT")
            manage_button.setToolTip(
                "Choose, add or edit presets stored in this prompt category's .env file"
            )
            title_row.addWidget(manage_button)
            setattr(self, f"{manage_family}_preset_button", manage_button)
        layout.addLayout(title_row)
        combo = QComboBox()
        combo.addItem("Custom / keep current", None)
        available_presets = (
            {record.name: record.text for record in load_prompt_presets(self.preset_env_root, manage_family)}
            if manage_family
            else presets
        )
        for name, text in available_presets.items():
            combo.addItem(name, text)
        combo.setToolTip("Preset content remains editable")
        layout.addWidget(combo)
        field = QPlainTextEdit()
        field.setPlaceholderText(placeholder)
        field.setFixedHeight(height)
        layout.addWidget(field)

        def apply_preset(index: int) -> None:
            text = combo.itemData(index)
            if not text:
                return
            if append and field.toPlainText().strip():
                existing = field.toPlainText().strip()
                if str(text) not in existing:
                    field.setPlainText(existing.rstrip(". ") + ". " + str(text))
            else:
                field.setPlainText(str(text))

        combo.currentIndexChanged.connect(apply_preset)
        if manage_button and manage_family:
            manage_button.setText("EDIT")
            manage_button.clicked.connect(
                lambda _checked=False, family=manage_family, target=combo, editor=field,
                button=manage_button, should_append=append:
                self._open_managed_presets(family, target, editor, button, should_append)
            )
        return field, combo

    def _open_managed_presets(
        self,
        family: str,
        combo: QComboBox,
        field: QPlainTextEdit,
        button: QPushButton,
        append: bool = False,
    ) -> None:
        titles = {
            "creative_brief": "Creative Brief Presets",
            "global_visual_style": "Global Visual Style Presets",
            "transition_language": "Transition Language Presets",
            "constraints_and_technical_rules": "Constraints and Technical Rules Presets",
            "overall_soundscape": "Overall Soundscape Presets",
            "non_diegetic_music": "Non-diegetic Music Presets",
        }
        title = titles.get(family, "Prompt Presets")
        dialog = PromptPresetDialog(self.preset_env_root, family, title, self)
        accepted = dialog.exec() == QDialog.Accepted
        selected = dialog.selected_record
        dialog.deleteLater()
        records = load_prompt_presets(self.preset_env_root, family)
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Custom / keep current", None)
        selected_index = 0
        for record in records:
            combo.addItem(record.name, record.text)
            if selected and record.name == selected.name:
                selected_index = combo.count() - 1
        combo.setCurrentIndex(selected_index)
        combo.blockSignals(False)
        button.setText("EDIT")
        if accepted and selected:
            if append and field.toPlainText().strip():
                existing = field.toPlainText().strip()
                if selected.text not in existing:
                    field.setPlainText(existing.rstrip(". ") + ". " + selected.text)
            else:
                field.setPlainText(selected.text)

    def clear_fields(self) -> None:
        self.last_timeline_brief = ""
        for name in (
            "brief", "style", "shots", "dialogue", "transition", "ending",
            "constraints", "soundscape", "music", "output",
        ):
            getattr(self, name).clear()
        for name in (
            "brief_preset", "style_preset", "transition_preset", "constraints_preset",
            "soundscape_preset", "music_preset",
        ):
            getattr(self, name).setCurrentIndex(0)

    @staticmethod
    def _field(layout: QVBoxLayout, title: str, placeholder: str, height: int) -> QPlainTextEdit:
        layout.addWidget(QLabel(title))
        field = QPlainTextEdit()
        field.setPlaceholderText(placeholder)
        field.setFixedHeight(height)
        layout.addWidget(field)
        return field

    def spec(self) -> PromptSpec:
        return PromptSpec(
            brief=self.brief.toPlainText().strip(),
            style=self.style.toPlainText().strip(),
            audio=self.soundscape.toPlainText().strip(),
            music=self.music.toPlainText().strip(),
            shots=split_shots(self.shots.toPlainText()),
            dialogue=self.dialogue.toPlainText().strip(),
            transition=self.transition.toPlainText().strip(),
            ending=self.ending.toPlainText().strip(),
            must_keep=self.constraints.toPlainText().strip(),
            technical=self.constraints.toPlainText().strip(),
        )


class TextLayerDialog(QDialog):
    def __init__(self, layer: TextLayer, duration: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Type Tool · {layer.layer_id}")
        self.setMinimumWidth(440)
        self._color = layer.color
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.text_edit = QPlainTextEdit(layer.text)
        self.text_edit.setPlaceholderText("Enter the title or on-screen text")
        self.text_edit.setFixedHeight(100)
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setRange(0.0, duration)
        self.start_spin.setDecimals(2)
        self.start_spin.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.start_spin.setSuffix(" s")
        self.start_spin.setValue(layer.start_seconds)
        self.end_spin = QDoubleSpinBox()
        self.end_spin.setRange(0.1, duration)
        self.end_spin.setDecimals(2)
        self.end_spin.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.end_spin.setSuffix(" s")
        self.end_spin.setValue(min(duration, layer.end_seconds))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 240)
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.setValue(layer.font_size)
        self.color_button = QPushButton()
        self.color_button.clicked.connect(self._choose_color)
        self._refresh_color_button()
        form.addRow("Text", self.text_edit)
        form.addRow("Start", self.start_spin)
        form.addRow("End", self.end_spin)
        form.addRow("Font Size", self.font_size_spin)
        form.addRow("Color", self.color_button)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "Text color")
        if color.isValid():
            self._color = color.name()
            self._refresh_color_button()

    def _refresh_color_button(self) -> None:
        self.color_button.setText(self._color)
        self.color_button.setStyleSheet(f"background:{self._color}; color:#111; font-weight:600;")

    def _validate(self) -> None:
        if not self.text_edit.toPlainText().strip():
            QMessageBox.warning(self, "Text required", "Enter text for this layer.")
            return
        if self.end_spin.value() <= self.start_spin.value():
            QMessageBox.warning(self, "Invalid range", "Text layer end must be later than its start.")
            return
        self.accept()

    def state(self) -> dict:
        start, end = snap_timeline_range(
            self.start_spin.value(), self.end_spin.value(), self.end_spin.maximum()
        )
        return {
            "text": self.text_edit.toPlainText().strip(),
            "start_seconds": start,
            "end_seconds": end,
            "font_size": self.font_size_spin.value(),
            "color": self._color,
        }


class ContentLayerDialog(QDialog):
    """Type Tool editor with semantic content roles for H3 direction."""

    ROLES = (
        ("On-screen Text", "on_screen_text"),
        ("Dialogue", "dialogue"),
        ("Voice-over", "voice_over"),
        ("Lyrics", "lyrics"),
    )

    def __init__(
        self,
        layer: TextLayer,
        duration: float,
        shots: list[DirectorCue] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Type Tool · {layer.layer_id}")
        self.setMinimumWidth(500)
        self._color = layer.color
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.role_combo = QComboBox()
        for label, value in self.ROLES:
            self.role_combo.addItem(label, value)
        self.role_combo.setCurrentIndex(max(0, self.role_combo.findData(layer.content_role)))
        self.role_combo.currentIndexChanged.connect(self._refresh_role_fields)
        self.text_edit = QPlainTextEdit(layer.text)
        self.text_edit.setPlaceholderText("Enter exact text, dialogue, voice-over, or lyrics")
        self.text_edit.setFixedHeight(90)
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setRange(0.0, duration)
        self.start_spin.setDecimals(2)
        self.start_spin.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.start_spin.setSuffix(" s")
        self.start_spin.setValue(layer.start_seconds)
        self.end_spin = QDoubleSpinBox()
        self.end_spin.setRange(0.1, duration)
        self.end_spin.setDecimals(2)
        self.end_spin.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.end_spin.setSuffix(" s")
        self.end_spin.setValue(min(duration, layer.end_seconds))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 240)
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.setValue(layer.font_size)
        self.color_button = QPushButton()
        self.color_button.clicked.connect(self._choose_color)
        self._refresh_color_button()

        self.speaker_combo = QComboBox()
        self.speaker_combo.addItems(("S1", "S2"))
        self.speaker_combo.setCurrentText(layer.speaker)
        self.language_combo = QComboBox()
        self.language_combo.setEditable(True)
        self.language_combo.addItems(("English", "Chinese", "Cantonese", "Malay", "Japanese", "Korean"))
        self.language_combo.setCurrentText(layer.language)
        self.delivery_combo = QComboBox()
        self.delivery_combo.setEditable(True)
        self.delivery_combo.addItems(("Natural", "Calm", "Whispered", "Urgent", "Confident", "Emotional"))
        self.delivery_combo.setCurrentText(layer.delivery)
        self.lip_sync_check = QCheckBox("Accurate visible lip synchronization")
        self.lip_sync_check.setChecked(layer.lip_sync)
        self.shot_combo = QComboBox()
        self.shot_combo.addItem("Auto · match by time range", "")
        for shot in sorted(shots or [], key=lambda cue: cue.start_seconds):
            if shot.cue_type == "shot":
                number = shot.cue_id[1:] if shot.cue_id.startswith("S") else shot.cue_id
                self.shot_combo.addItem(
                    f"SHOT {number} · {shot.start_seconds:.2f}–{shot.end_seconds:.2f}s",
                    shot.cue_id,
                )
        self.shot_combo.setCurrentIndex(max(0, self.shot_combo.findData(layer.shot_id)))

        form.addRow("Content Role", self.role_combo)
        form.addRow("Content", self.text_edit)
        form.addRow("Start", self.start_spin)
        form.addRow("End", self.end_spin)
        form.addRow("Font Size", self.font_size_spin)
        form.addRow("Color", self.color_button)
        self.dialogue_rows: list[tuple[QLabel, QWidget]] = []
        for title, widget in (
            ("Speaker", self.speaker_combo),
            ("Language", self.language_combo),
            ("Delivery", self.delivery_combo),
            ("Lip Sync", self.lip_sync_check),
            ("所属 Shot", self.shot_combo),
        ):
            label = QLabel(title)
            form.addRow(label, widget)
            self.dialogue_rows.append((label, widget))
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh_role_fields()

    def _refresh_role_fields(self) -> None:
        dialogue = self.role_combo.currentData() == "dialogue"
        for label, widget in self.dialogue_rows:
            label.setVisible(dialogue)
            widget.setVisible(dialogue)
        visible_text = self.role_combo.currentData() == "on_screen_text"
        self.font_size_spin.setEnabled(visible_text)
        self.color_button.setEnabled(visible_text)

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "Text color")
        if color.isValid():
            self._color = color.name()
            self._refresh_color_button()

    def _refresh_color_button(self) -> None:
        self.color_button.setText(self._color)
        self.color_button.setStyleSheet(f"background:{self._color}; color:#111; font-weight:600;")

    def _validate(self) -> None:
        if not self.text_edit.toPlainText().strip():
            QMessageBox.warning(self, "Content required", "Enter the exact content for this layer.")
            return
        if self.end_spin.value() <= self.start_spin.value():
            QMessageBox.warning(self, "Invalid range", "Layer end must be later than its start.")
            return
        self.accept()

    def state(self) -> dict:
        dialogue = self.role_combo.currentData() == "dialogue"
        start, end = snap_timeline_range(
            self.start_spin.value(), self.end_spin.value(), self.end_spin.maximum()
        )
        return {
            "text": self.text_edit.toPlainText().strip(),
            "start_seconds": start,
            "end_seconds": end,
            "font_size": self.font_size_spin.value(),
            "color": self._color,
            "content_role": self.role_combo.currentData(),
            "speaker": self.speaker_combo.currentText() if dialogue else "S1",
            "language": self.language_combo.currentText().strip() if dialogue else "English",
            "delivery": self.delivery_combo.currentText().strip() if dialogue else "Natural",
            "lip_sync": self.lip_sync_check.isChecked() if dialogue else False,
            "shot_id": self.shot_combo.currentData() if dialogue else "",
        }


class SmartCutDialog(QDialog):
    """Non-destructive review surface for deterministic and LM-assisted cuts."""

    ai_refine_requested = Signal(object)
    ACTION_LABELS = {
        "keep": "KEEP",
        "trim": "TRIM",
        "merge": "MERGE",
        "remove": "REMOVE",
    }
    ACTION_COLORS = {
        "keep": QColor("#255f43"),
        "trim": QColor("#8a6a22"),
        "merge": QColor("#285f8d"),
        "remove": QColor("#8f3340"),
    }

    def __init__(
        self,
        shot_inputs: list[dict],
        target_duration: float,
        mode: str = "balanced",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("smartCutDialog")
        self.setWindowTitle("SMART CUT · Story Constraint Planner")
        self.resize(1280, 760)
        self.setMinimumSize(980, 620)
        self.shot_inputs = deepcopy(shot_inputs)
        self.semantic_hints: dict[str, dict] = {}
        self.plan = plan_smart_cut(
            self.shot_inputs,
            target_duration,
            mode=mode,
            grid_seconds=TIMELINE_SNAP_SECONDS,
            segment_seconds=MAX_NATIVE_SECONDS,
        )
        self._loading = False

        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.original_label = QLabel()
        self.edited_label = QLabel()
        self.target_label = QLabel()
        self.delta_label = QLabel()
        for widget in (
            self.original_label,
            self.edited_label,
            self.target_label,
            self.delta_label,
        ):
            top.addWidget(widget)
            top.addSpacing(12)
        top.addStretch(1)
        top.addWidget(QLabel("MODE"))
        self.mode_combo = QComboBox()
        for key, label in (
            ("safe", "Safe"),
            ("balanced", "Balanced"),
            ("aggressive", "Aggressive"),
        ):
            self.mode_combo.addItem(label, key)
        self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(self.plan["mode"])))
        top.addWidget(self.mode_combo)
        self.auto_plan_button = QPushButton("AUTO PLAN")
        self.auto_plan_button.setToolTip(
            "Recalculate exact 0.5-second timing locally. No AI or Timeline edit is performed."
        )
        top.addWidget(self.auto_plan_button)
        self.ai_button = QPushButton("AI SEMANTIC REFINE")
        self.ai_button.setToolTip(
            "Ask the configured Design provider to classify story roles and redundancy. "
            "The AI cannot author timings or directly edit the Timeline."
        )
        top.addWidget(self.ai_button)
        root.addLayout(top)

        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color:#ffb65c; font-weight:600;")
        root.addWidget(self.warning_label)

        splitter = QSplitter(Qt.Horizontal)
        self.table = QTableWidget(0, 9)
        self.table.setObjectName("smartCutDecisionTable")
        self.table.setHorizontalHeaderLabels([
            "Action", "Shot", "Role", "Original", "Proposed", "Saved",
            "Importance", "Risk", "Reason",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().hide()
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.Stretch)
        splitter.addWidget(self.table)

        inspector = QWidget()
        inspector.setMinimumWidth(320)
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.addWidget(QLabel("SELECTED DECISION"))
        form = QFormLayout()
        self.action_combo = QComboBox()
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.0, 120.0)
        self.duration_spin.setDecimals(1)
        self.duration_spin.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.duration_spin.setSuffix(" s")
        self.lock_check = QCheckBox("LOCK · preserve this Shot")
        self.role_label = QLabel("—")
        self.dependency_label = QLabel("—")
        self.dependency_label.setWordWrap(True)
        form.addRow("Action", self.action_combo)
        form.addRow("Duration", self.duration_spin)
        form.addRow("Story role", self.role_label)
        form.addRow("Dependencies", self.dependency_label)
        form.addRow("", self.lock_check)
        inspector_layout.addLayout(form)
        inspector_layout.addWidget(QLabel("Reason / protection"))
        self.reason_text = QPlainTextEdit()
        self.reason_text.setReadOnly(True)
        inspector_layout.addWidget(self.reason_text, 1)
        self.ai_status = QLabel("Local deterministic plan · AI semantics not requested")
        self.ai_status.setWordWrap(True)
        self.ai_status.setStyleSheet("color:#8ea0af;")
        inspector_layout.addWidget(self.ai_status)
        splitter.addWidget(inspector)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        hint = QLabel(
            "KEEP preserves a Shot; TRIM shortens optional time; MERGE omits a redundant beat "
            "and records its surviving neighbor; REMOVE omits the complete Shot. Nothing changes "
            "on the Timeline until APPLY SMART CUT."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#91a0ad;")
        root.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.apply_button = buttons.addButton("APPLY SMART CUT", QDialogButtonBox.AcceptRole)
        self.apply_button.setObjectName("smartCutApply")
        root.addWidget(buttons)

        self.table.currentCellChanged.connect(self._load_selected)
        self.auto_plan_button.clicked.connect(self._replan)
        self.ai_button.clicked.connect(lambda: self.ai_refine_requested.emit(self))
        self.mode_combo.currentIndexChanged.connect(self._replan)
        self.action_combo.currentIndexChanged.connect(self._save_selected_action)
        self.duration_spin.valueChanged.connect(self._save_selected_duration)
        self.lock_check.toggled.connect(self._lock_selected)
        buttons.rejected.connect(self.reject)
        self.apply_button.clicked.connect(self._accept_plan)
        self._refresh_table()
        if self.table.rowCount():
            self.table.setCurrentCell(0, 0)

    def _decision(self, row: int | None = None) -> dict | None:
        index = self.table.currentRow() if row is None else row
        if not (0 <= index < len(self.plan.get("decisions", []))):
            return None
        return self.plan["decisions"][index]

    def _refresh_summary(self) -> None:
        current = float(self.plan["current_duration"])
        edited = sum(float(row["proposed_duration"]) for row in self.plan["decisions"])
        target = float(self.plan["target_duration"])
        self.plan["edited_duration"] = snap_timeline_seconds(edited)
        self.plan["saved_seconds"] = snap_timeline_seconds(current - edited)
        self.plan["on_target"] = abs(edited - target) <= 0.01
        self.original_label.setText(f"ORIGINAL  {current:.1f}s")
        self.edited_label.setText(f"EDITED  {edited:.1f}s")
        self.target_label.setText(f"TARGET  {target:.1f}s")
        delta = edited - target
        if abs(delta) <= 0.01:
            self.delta_label.setText("ON TARGET  0.0s")
            self.delta_label.setStyleSheet("color:#55d98b; font-weight:700;")
        else:
            self.delta_label.setText(
                f"{'OVER' if delta > 0 else 'UNDER'}  {abs(delta):.1f}s"
            )
            self.delta_label.setStyleSheet("color:#ffb65c; font-weight:700;")
        warnings = list(self.plan.get("warnings") or [])
        self.warning_label.setText("\n".join("⚠ " + value for value in warnings))
        self.warning_label.setVisible(bool(warnings))

    def _refresh_table(self) -> None:
        current_id = ""
        selected = self._decision()
        if selected:
            current_id = selected["shot_id"]
        self._loading = True
        self.table.setRowCount(len(self.plan["decisions"]))
        selected_row = 0
        for row_index, decision in enumerate(self.plan["decisions"]):
            action = str(decision["action"])
            risk = (
                "DIALOGUE"
                if decision["speech_count"] and action in {"remove", "merge"}
                else "HIGH"
                if decision["dependency_strength"] >= 6 and action != "keep"
                else "MEDIUM"
                if action in {"trim", "merge"}
                else "LOW"
            )
            values = [
                self.ACTION_LABELS.get(action, action.upper()),
                str(decision["shot_id"]),
                str(decision["story_role"]),
                f"{float(decision['original_duration']):.1f}s",
                f"{float(decision['proposed_duration']):.1f}s",
                f"{float(decision['saved_seconds']):.1f}s",
                f"{float(decision['importance']):.0f}",
                risk,
                str(decision["reason"]),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setBackground(self.ACTION_COLORS.get(action, QColor("#333333")))
                    item.setForeground(QColor("white"))
                self.table.setItem(row_index, column, item)
            if decision["shot_id"] == current_id:
                selected_row = row_index
        self._loading = False
        self._refresh_summary()
        if self.table.rowCount():
            self.table.setCurrentCell(selected_row, 0)

    def _load_selected(self, *_args) -> None:
        decision = self._decision()
        self._loading = True
        self.action_combo.clear()
        if decision is None:
            self._loading = False
            return
        actions = ["keep", "trim"]
        if not decision["protected"]:
            actions.append("remove")
            if decision.get("merge_into"):
                actions.append("merge")
        elif decision["action"] == "merge":
            actions.append("merge")
        for action in actions:
            self.action_combo.addItem(self.ACTION_LABELS[action], action)
        self.action_combo.setCurrentIndex(
            max(0, self.action_combo.findData(decision["action"]))
        )
        self.duration_spin.setMaximum(float(decision["original_duration"]))
        self.duration_spin.setMinimum(
            0.0 if decision["action"] in {"remove", "merge"} else float(decision["minimum_duration"])
        )
        self.duration_spin.setValue(float(decision["proposed_duration"]))
        self.duration_spin.setEnabled(decision["action"] == "trim" and not decision["locked"])
        self.lock_check.setChecked(bool(decision["locked"]))
        self.role_label.setText(
            f"{decision['story_role']} · importance {float(decision['importance']):.0f}"
        )
        self.dependency_label.setText(
            f"strength {decision['dependency_strength']}/10 · native-boundary cost "
            f"{float(decision['boundary_cost']):.0f}"
        )
        self.reason_text.setPlainText(str(decision["reason"]))
        self._loading = False

    def _replan(self, *_args) -> None:
        if self._loading:
            return
        mode = str(self.mode_combo.currentData() or "balanced")
        locked_ids = {
            row["shot_id"] for row in self.plan.get("decisions", []) if row.get("locked")
        }
        for source in self.shot_inputs:
            source["locked"] = str(source.get("cue_id")) in locked_ids
        self.plan = plan_smart_cut(
            self.shot_inputs,
            float(self.plan["target_duration"]),
            mode=mode,
            semantic_hints=self.semantic_hints,
            grid_seconds=TIMELINE_SNAP_SECONDS,
            segment_seconds=MAX_NATIVE_SECONDS,
        )
        self._refresh_table()

    def _save_selected_action(self, *_args) -> None:
        if self._loading:
            return
        decision = self._decision()
        if decision is None:
            return
        action = str(self.action_combo.currentData() or "keep")
        decision["action"] = action
        if action == "keep":
            decision["proposed_duration"] = float(decision["original_duration"])
        elif action == "trim":
            decision["proposed_duration"] = max(
                float(decision["minimum_duration"]),
                min(
                    float(decision["original_duration"]) - TIMELINE_SNAP_SECONDS,
                    float(decision["proposed_duration"]) or float(decision["minimum_duration"]),
                ),
            )
        else:
            decision["proposed_duration"] = 0.0
        decision["saved_seconds"] = round(
            float(decision["original_duration"]) - float(decision["proposed_duration"]), 6
        )
        self._refresh_table()

    def _save_selected_duration(self, value: float) -> None:
        if self._loading:
            return
        decision = self._decision()
        if decision is None or decision["action"] != "trim":
            return
        decision["proposed_duration"] = snap_timeline_seconds(max(
            float(decision["minimum_duration"]),
            min(float(decision["original_duration"]), float(value)),
        ))
        decision["saved_seconds"] = round(
            float(decision["original_duration"]) - float(decision["proposed_duration"]), 6
        )
        self._refresh_table()

    def _lock_selected(self, enabled: bool) -> None:
        if self._loading:
            return
        decision = self._decision()
        if decision is None:
            return
        decision["locked"] = bool(enabled)
        if enabled:
            decision["action"] = "keep"
            decision["proposed_duration"] = float(decision["original_duration"])
            decision["saved_seconds"] = 0.0
        self._refresh_table()

    def set_ai_running(self, running: bool, message: str) -> None:
        self.ai_button.setEnabled(not running)
        self.auto_plan_button.setEnabled(not running)
        self.ai_status.setText(message)

    def apply_ai_hints(self, hints: dict[str, dict], model: str = "") -> None:
        self.semantic_hints = deepcopy(hints)
        self.ai_status.setText(
            f"AI semantic hints applied from {model or 'configured model'} · "
            "all timings recalculated locally"
        )
        self._replan()

    def _accept_plan(self) -> None:
        edited = float(self.plan["edited_duration"])
        target = float(self.plan["target_duration"])
        if abs(edited - target) > 0.01:
            answer = QMessageBox.question(
                self,
                "Smart Cut target not exact",
                f"This protected plan is {edited:.1f}s while the target is {target:.1f}s. "
                "Apply the reviewed plan anyway?",
            )
            if answer != QMessageBox.Yes:
                return
        self.accept()

    def result_plan(self) -> dict:
        return deepcopy(self.plan)


class StoryboardCardDelegate(QStyledItemDelegate):
    """Paint Storyboard cards with lift, shadow and drop-settle feedback."""

    def __init__(self, board: "StoryboardBlockList") -> None:
        super().__init__(board)
        self.board = board

    def paint(self, painter, option, index) -> None:  # noqa: N802
        opt = QStyleOptionViewItem(option)
        item = self.board.itemFromIndex(index)
        hovered = bool(option.state & QStyle.State_MouseOver)
        dragging = item is self.board._drag_item
        settling = item is self.board._drop_item
        lift = 0
        if hovered and not dragging:
            lift = 3
        if settling:
            pulse = 1.0 - abs((self.board._drop_progress * 2.0) - 1.0)
            lift = max(lift, round(6.0 * pulse))

        if lift or settling:
            painter.save()
            shadow = QRectF(opt.rect.adjusted(5, 6, -3, 2))
            shadow.translate(0, -lift)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 105 if settling else 75))
            painter.drawRoundedRect(shadow, 6, 6)
            painter.restore()
            opt.rect.translate(0, -lift)

        super().paint(painter, opt, index)
        if settling:
            painter.save()
            alpha = max(0, round(220 * (1.0 - self.board._drop_progress)))
            painter.setPen(QPen(QColor(71, 215, 255, alpha), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(opt.rect).adjusted(1, 1, -2, -2), 5, 5)
            painter.restore()


class StoryboardBlockList(QListWidget):
    """Plain-item Shot board whose order can be changed safely by drag and drop."""

    order_changed = Signal()
    MIME_CARD = "application/x-h3-storyboard-card"
    DISPLAY_MODES = {
        "extra_large_icons": "Extra large icons",
        "large_icons": "Large icons",
        "medium_icons": "Medium icons",
        "small_icons": "Small icons",
        "list": "List",
        "details": "Details",
        "tiles": "Tiles",
        "content": "Content",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("storyboardBlockList")
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setViewMode(QListView.IconMode)
        self.setMovement(QListView.Snap)
        self.setResizeMode(QListView.Adjust)
        self.setFlow(QListView.LeftToRight)
        self.setWrapping(True)
        self.setWordWrap(True)
        self.setTextElideMode(Qt.ElideRight)
        self.setSpacing(10)
        self.setMouseTracking(True)
        self.viewport().setAcceptDrops(True)
        self.viewport().setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet(
            "QListWidget#storyboardBlockList { background:#0d1115; border:1px solid #303840; }"
            "QListWidget#storyboardBlockList::item { background:#111417; color:#edf2f6; "
            "border:1px solid #28313a; border-radius:4px; padding:8px; }"
            "QListWidget#storyboardBlockList::item:hover { background:#18212a; "
            "border:1px solid #557080; }"
            "QListWidget#storyboardBlockList::item:selected { background:#1c2730; "
            "border:2px solid #47d7ff; }"
        )
        self.model().rowsMoved.connect(lambda *_args: self.order_changed.emit())
        self._drag_item: QListWidgetItem | None = None
        self._drag_original_row = -1
        self._reflow_animation: QVariantAnimation | None = None
        self._drop_animation: QVariantAnimation | None = None
        self._drop_item: QListWidgetItem | None = None
        self._drop_progress = 0.0
        self.setItemDelegate(StoryboardCardDelegate(self))
        self.display_mode = "large_icons"
        self._update_card_geometry()

    def _update_card_geometry(self) -> None:
        available = max(320, self.viewport().width() - 28)
        mode = self.display_mode
        if mode in {"list", "details", "content"}:
            self.setViewMode(QListView.ListMode)
            self.setFlow(QListView.TopToBottom)
            self.setWrapping(False)
        else:
            self.setViewMode(QListView.IconMode)
            self.setFlow(QListView.LeftToRight)
            self.setWrapping(True)

        if mode == "extra_large_icons":
            columns, text_height = 2, 188
        elif mode == "large_icons":
            columns, text_height = 3, 172
        elif mode == "medium_icons":
            columns, text_height = 4, 138
        elif mode == "small_icons":
            columns, text_height = 5, 105
        elif mode == "tiles":
            columns, text_height = 2, 118
        elif mode == "content":
            columns, text_height = 1, 54
        elif mode == "details":
            columns, text_height = 1, 12
        else:  # List
            columns, text_height = 1, 28
        self.visual_columns = columns
        width = max(170, (available - (columns - 1) * 12) // columns)
        if mode == "extra_large_icons":
            width = min(540, width)
        elif mode == "large_icons":
            width = min(390, width)
        elif mode == "medium_icons":
            width = min(300, width)
        elif mode == "small_icons":
            width = min(230, width)
        elif mode == "tiles":
            width = min(510, width)
        else:
            width = available
        if mode == "details":
            icon_width, icon_height = 48, 27
        elif mode == "list":
            icon_width, icon_height = 96, 54
        elif mode == "content":
            icon_width, icon_height = 300, 169
        elif mode == "tiles":
            icon_width, icon_height = min(220, width // 2), min(124, round(min(220, width // 2) * 9 / 16))
        else:
            icon_width = max(140, width - 24)
            icon_height = max(79, round(icon_width * 9 / 16))
        self.setIconSize(QSize(icon_width, icon_height))
        row_height = icon_height + text_height if self.viewMode() == QListView.IconMode else max(icon_height + 18, text_height + 48)
        self.setGridSize(QSize(width, row_height))
        for index in range(self.count()):
            self.item(index).setSizeHint(QSize(width - 8, max(42, row_height - 10)))

    def set_display_mode(self, mode: str) -> None:
        normalized = str(mode or "large_icons").strip().lower()
        if normalized not in self.DISPLAY_MODES:
            normalized = "large_icons"
        self.display_mode = normalized
        self._update_card_geometry()
        self.doItemsLayout()
        self.viewport().update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_card_geometry()

    @staticmethod
    def _entry_key(item: QListWidgetItem) -> str:
        return str((item.data(Qt.UserRole) or {}).get("cue_id") or id(item))

    def _positions(self) -> dict[str, QPoint]:
        return {
            self._entry_key(self.item(index)): self.visualItemRect(self.item(index)).topLeft()
            for index in range(self.count())
            if self.item(index) is not self._drag_item
        }

    def _animate_reflow(self, before: dict[str, QPoint]) -> None:
        self.doItemsLayout()
        after = self._positions()
        moving: list[tuple[QListWidgetItem, QPoint, QPoint]] = []
        for index in range(self.count()):
            item = self.item(index)
            key = self._entry_key(item)
            if item is self._drag_item or key not in before or key not in after:
                continue
            if before[key] != after[key]:
                moving.append((item, before[key], after[key]))
        if not moving:
            return
        if self._reflow_animation is not None:
            self._reflow_animation.stop()
        animation = QVariantAnimation(self)
        self._reflow_animation = animation
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setDuration(190)
        animation.setEasingCurve(QEasingCurve.OutCubic)

        def update(value) -> None:
            progress = float(value)
            for item, start, end in moving:
                if self.row(item) < 0:
                    continue
                point = QPoint(
                    round(start.x() + (end.x() - start.x()) * progress),
                    round(start.y() + (end.y() - start.y()) * progress),
                )
                self.setPositionForIndex(point, self.indexFromItem(item))
            self.viewport().update()

        animation.valueChanged.connect(update)
        animation.finished.connect(lambda: self.doItemsLayout())
        animation.start()

    @staticmethod
    def _drag_ghost(source: QPixmap) -> QPixmap:
        """Return a lifted card preview with a soft layered shadow."""
        margin = 16
        ghost = QPixmap(source.width() + margin * 2, source.height() + margin * 2)
        ghost.fill(Qt.transparent)
        painter = QPainter(ghost)
        painter.setRenderHint(QPainter.Antialiasing)
        base = QRectF(margin, margin + 4, source.width(), source.height())
        painter.setPen(Qt.NoPen)
        for spread, alpha in ((10, 14), (7, 22), (4, 34), (2, 48)):
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.drawRoundedRect(base.adjusted(-spread, -spread, spread, spread), 9, 9)
        painter.setOpacity(0.94)
        painter.drawPixmap(margin, margin - 2, source)
        painter.end()
        return ghost

    def _animate_drop_settle(self, item: QListWidgetItem | None) -> None:
        """Pulse and settle the released card so the final position is explicit."""
        if item is None or self.row(item) < 0:
            return
        if self._drop_animation is not None:
            self._drop_animation.stop()
        self._drop_item = item
        self._drop_progress = 0.0
        animation = QVariantAnimation(self)
        self._drop_animation = animation
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setDuration(260)
        animation.setEasingCurve(QEasingCurve.OutCubic)

        def update(value) -> None:
            self._drop_progress = float(value)
            self.viewport().update(self.visualItemRect(item).adjusted(-8, -10, 8, 10))

        def finish() -> None:
            self._drop_progress = 0.0
            self._drop_item = None
            self.viewport().update()

        animation.valueChanged.connect(update)
        animation.finished.connect(finish)
        animation.start()

    def _placeholder_visual(self) -> None:
        if self._drag_item is None:
            return
        self._drag_item.setIcon(QIcon())
        self._drag_item.setText("DROP HERE\n\nRelease to place this Shot")
        self._drag_item.setTextAlignment(Qt.AlignCenter)
        self._drag_item.setBackground(QColor("#18232b"))
        self._drag_item.setForeground(QColor("#47d7ff"))

    def _move_drag_placeholder(self, target_row: int) -> None:
        if self._drag_item is None or self.count() < 2:
            return
        current_row = self.row(self._drag_item)
        target_row = max(0, min(int(target_row), self.count() - 1))
        if current_row < 0 or current_row == target_row:
            return
        before = self._positions()
        item = self.takeItem(current_row)
        self.insertItem(target_row, item)
        self.setCurrentItem(item)
        self.order_changed.emit()
        self._placeholder_visual()
        self._animate_reflow(before)

    def move_selected(self, offset: int) -> bool:
        item = self.currentItem()
        current_row = self.row(item) if item is not None else -1
        target_row = current_row + int(offset)
        if item is None or current_row < 0 or not (0 <= target_row < self.count()):
            return False
        before = self._positions()
        moved = self.takeItem(current_row)
        self.insertItem(target_row, moved)
        self.setCurrentItem(moved)
        self.order_changed.emit()
        self._animate_reflow(before)
        self._animate_drop_settle(moved)
        return True

    def startDrag(self, supported_actions) -> None:  # noqa: N802
        item = self.currentItem()
        if item is None:
            return
        self._drag_item = item
        self._drag_original_row = self.row(item)
        rect = self.visualItemRect(item)
        ghost = self._drag_ghost(self.viewport().grab(rect))
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self.MIME_CARD, self._entry_key(item).encode("utf-8"))
        drag.setMimeData(mime)
        drag.setPixmap(ghost)
        drag.setHotSpot(
            QPoint(
                min(rect.width() // 2, 90) + 16,
                min(rect.height() // 3, 70) + 14,
            )
        )
        self._placeholder_visual()
        result = drag.exec(Qt.MoveAction)
        if result != Qt.MoveAction and self.row(item) != self._drag_original_row:
            before = self._positions()
            moved = self.takeItem(self.row(item))
            self.insertItem(self._drag_original_row, moved)
            self._animate_reflow(before)
        self._drag_item = None
        self._drag_original_row = -1
        self.order_changed.emit()
        self.setCurrentItem(item)
        if result == Qt.MoveAction:
            self._animate_drop_settle(item)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(self.MIME_CARD):
            event.setDropAction(Qt.MoveAction)
            event.accept()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if not event.mimeData().hasFormat(self.MIME_CARD):
            super().dragMoveEvent(event)
            return
        point = event.position().toPoint()
        index = self.indexAt(point)
        target_row = index.row() if index.isValid() else self.count() - 1
        if index.isValid():
            rect = self.visualRect(index)
            if point.y() > rect.center().y() or point.x() > rect.center().x():
                target_row = min(self.count() - 1, target_row + 1)
        self._move_drag_placeholder(target_row)
        event.setDropAction(Qt.MoveAction)
        event.accept()

    def dropEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(self.MIME_CARD):
            point = event.position().toPoint()
            index = self.indexAt(point)
            if index.isValid():
                self._move_drag_placeholder(index.row())
            event.setDropAction(Qt.MoveAction)
            event.accept()
            self.order_changed.emit()
            return
        super().dropEvent(event)


class StoryboardEditorDialog(QDialog):
    """Non-destructive Shot-card editor committed to Timeline only on Apply."""

    def __init__(
        self,
        shots: list[DirectorCue],
        text_layers: list[TextLayer],
        media_assets: list[MediaAsset],
        current_duration: float,
        target_duration: float,
        parent: QWidget | None = None,
        preview_paths: dict[str, Path] | None = None,
        view_mode: str = "large_icons",
    ) -> None:
        super().__init__(parent)
        self.setObjectName("storyboardEditorDialog")
        self.setWindowTitle("Storyboard Editor · Shot Structure")
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else QRectF(0, 0, 1280, 800).toRect()
        self.resize(min(1480, available.width() - 48), min(900, available.height() - 48))
        self.setMinimumSize(1050, 620)
        self.original_duration = max(0.5, float(current_duration))
        self._loading_inspector = False
        self.preview_paths = {
            str(key): Path(value) for key, value in (preview_paths or {}).items()
        }
        self._icon_cache: dict[str, QIcon] = {}
        self.view_mode = (
            view_mode if view_mode in StoryboardBlockList.DISPLAY_MODES else "large_icons"
        )

        root = QVBoxLayout(self)
        summary = QHBoxLayout()
        self.original_label = QLabel()
        self.current_label = QLabel()
        self.delta_label = QLabel()
        self.target_spin = QDoubleSpinBox()
        self.target_spin.setObjectName("storyboardEditorTarget")
        self.target_spin.setRange(0.5, 3600.0)
        self.target_spin.setDecimals(1)
        self.target_spin.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.target_spin.setSuffix(" s")
        self.target_spin.setValue(max(0.5, float(target_duration)))
        summary.addWidget(self.original_label)
        summary.addSpacing(16)
        summary.addWidget(self.current_label)
        summary.addSpacing(16)
        summary.addWidget(QLabel("TARGET"))
        summary.addWidget(self.target_spin)
        summary.addSpacing(16)
        summary.addWidget(self.delta_label)
        summary.addStretch(1)
        self.view_button = QToolButton()
        self.view_button.setObjectName("storyboardViewButton")
        self.view_button.setPopupMode(QToolButton.InstantPopup)
        self.view_button.setToolTip("Choose Storyboard card size and layout")
        self.view_menu = QMenu(self.view_button)
        self.view_actions = {}
        view_symbols = {
            "extra_large_icons": "▣",
            "large_icons": "▣",
            "medium_icons": "▤",
            "small_icons": "▦",
            "list": "☷",
            "details": "≡",
            "tiles": "☷",
            "content": "☷",
        }
        for key, label in StoryboardBlockList.DISPLAY_MODES.items():
            action = self.view_menu.addAction(f"{view_symbols[key]}   {label}")
            action.setCheckable(True)
            action.triggered.connect(
                lambda _checked=False, selected=key: self._set_view_mode(selected)
            )
            self.view_actions[key] = action
        self.view_button.setMenu(self.view_menu)
        summary.addWidget(self.view_button)
        root.addLayout(summary)

        hint = QLabel(
            "Drag Shot blocks to reorder. Select a block to edit its title, must-complete action "
            "and duration. Add/Delete changes only this draft until APPLY TO TIMELINE."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#9aa7b3;")
        root.addWidget(hint)

        splitter = QSplitter(Qt.Horizontal)
        self.block_list = StoryboardBlockList()
        self.block_list.set_display_mode(self.view_mode)
        splitter.addWidget(self.block_list)

        inspector = QWidget()
        inspector.setMinimumWidth(315)
        inspector_layout = QVBoxLayout(inspector)
        inspector_header = QHBoxLayout()
        inspector_header.addWidget(QLabel("SELECTED SHOT"))
        inspector_header.addStretch(1)
        self.move_left_button = QToolButton()
        self.move_left_button.setObjectName("storyboardMoveLeft")
        self.move_left_button.setText("←")
        self.move_left_button.setToolTip("Move selected Shot one position left")
        self.move_right_button = QToolButton()
        self.move_right_button.setObjectName("storyboardMoveRight")
        self.move_right_button.setText("→")
        self.move_right_button.setToolTip("Move selected Shot one position right")
        inspector_header.addWidget(self.move_left_button)
        inspector_header.addWidget(self.move_right_button)
        inspector_layout.addLayout(inspector_header)
        form = QFormLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setObjectName("storyboardShotTitle")
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setObjectName("storyboardShotDuration")
        self.duration_spin.setRange(0.5, 120.0)
        self.duration_spin.setDecimals(1)
        self.duration_spin.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.duration_spin.setSuffix(" s")
        self.action_edit = QPlainTextEdit()
        self.action_edit.setObjectName("storyboardShotAction")
        self.action_edit.setPlaceholderText("Must-complete subject action")
        self.action_edit.setMaximumHeight(135)
        self.detail_label = QLabel("Select a Shot block.")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("color:#8ea0af;")
        form.addRow("Title / Preset", self.title_edit)
        form.addRow("Duration", self.duration_spin)
        form.addRow("Core action", self.action_edit)
        inspector_layout.addLayout(form)
        inspector_layout.addWidget(self.detail_label)
        inspector_layout.addStretch(1)
        splitter.addWidget(inspector)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        tools = QHBoxLayout()
        self.add_button = QPushButton("+ SHOT")
        self.add_button.setObjectName("storyboardAddShot")
        self.delete_button = QPushButton("DELETE SHOT")
        self.delete_button.setObjectName("storyboardDeleteShot")
        tools.addWidget(self.add_button)
        tools.addWidget(self.delete_button)
        tools.addStretch(1)
        root.addLayout(tools)
        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Cancel)
        apply_button = buttons.button(QDialogButtonBox.Apply)
        apply_button.setText("APPLY TO TIMELINE")
        apply_button.setObjectName("storyboardApply")
        apply_button.clicked.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        ordered = sorted(shots, key=lambda cue: (cue.start_seconds, cue.end_seconds))
        for cue in ordered:
            dialogue = [
                layer for layer in text_layers
                if layer.end_seconds > cue.start_seconds
                and layer.start_seconds < cue.end_seconds
                and layer.content_role in {"dialogue", "voice_over", "lyrics"}
            ]
            media = [
                asset for asset in media_assets
                if asset.timeline_placed
                and asset.end_seconds > cue.start_seconds
                and asset.start_seconds < cue.end_seconds
            ]
            refs = sorted({media_shortcut(asset) for asset in media if media_shortcut(asset)})
            preview_path, preview_ref = self._shot_preview_path(media, cue)
            self._insert_entry({
                "cue_id": cue.cue_id,
                "is_new": False,
                "original_start": float(cue.start_seconds),
                "original_end": float(cue.end_seconds),
                "duration": max(0.5, snap_timeline_seconds(cue.end_seconds - cue.start_seconds)),
                "preset": cue.preset or cue.cue_id,
                "subject_action": cue.authored_subject_action or cue.subject_action,
                "environment_response": cue.authored_environment_response or cue.environment_response,
                "framing": cue.framing,
                "dialogue_count": len(dialogue),
                "media_refs": refs,
                "preview_path": str(preview_path) if preview_path else "",
                "preview_ref": preview_ref,
            })
        self.block_list.currentItemChanged.connect(self._load_selected)
        self.block_list.order_changed.connect(self._refresh_all_cards)
        self.title_edit.textEdited.connect(self._save_selected)
        self.action_edit.textChanged.connect(self._save_selected)
        self.duration_spin.valueChanged.connect(self._save_selected)
        self.target_spin.valueChanged.connect(self._refresh_duration_summary)
        self.add_button.clicked.connect(self._add_shot)
        self.delete_button.clicked.connect(self._delete_shot)
        self.move_left_button.clicked.connect(lambda: self._move_selected(-1))
        self.move_right_button.clicked.connect(lambda: self._move_selected(1))
        self._set_view_mode(self.view_mode)
        if self.block_list.count():
            self.block_list.setCurrentRow(0)
        self._refresh_all_cards()

    def _set_view_mode(self, mode: str) -> None:
        normalized = (
            mode if mode in StoryboardBlockList.DISPLAY_MODES else "large_icons"
        )
        self.view_mode = normalized
        if hasattr(self, "block_list"):
            self.block_list.set_display_mode(normalized)
        for key, action in getattr(self, "view_actions", {}).items():
            action.blockSignals(True)
            action.setChecked(key == normalized)
            action.blockSignals(False)
        if hasattr(self, "view_button"):
            label = StoryboardBlockList.DISPLAY_MODES[normalized]
            self.view_button.setText(f"VIEW · {label.upper()}")
        if hasattr(self, "block_list") and self.block_list.count():
            self._refresh_all_cards()

    def _move_selected(self, offset: int) -> None:
        if self.block_list.move_selected(offset):
            self._refresh_all_cards()
        self._refresh_move_buttons()

    def _refresh_move_buttons(self) -> None:
        row = self.block_list.currentRow()
        count = self.block_list.count()
        self.move_left_button.setEnabled(row > 0)
        self.move_right_button.setEnabled(0 <= row < count - 1)

    def _insert_entry(self, entry: dict, row: int | None = None) -> QListWidgetItem:
        item = QListWidgetItem()
        item.setData(Qt.UserRole, deepcopy(entry))
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
        item.setSizeHint(QSize(320, 330))
        item.setFlags(
            item.flags()
            | Qt.ItemIsDragEnabled
            | Qt.ItemIsDropEnabled
            | Qt.ItemIsSelectable
            | Qt.ItemIsEnabled
        )
        if row is None:
            self.block_list.addItem(item)
        else:
            self.block_list.insertItem(max(0, min(row, self.block_list.count())), item)
        self.block_list._update_card_geometry()
        return item

    def _shot_preview_path(
        self,
        media: list[MediaAsset],
        shot: DirectorCue,
    ) -> tuple[Path | None, str]:
        preferred = {
            str(value).strip().upper()
            for value in (shot.semantic_reference_directions or {}).keys()
            if str(value).strip()
        }

        def preview_score(asset: MediaAsset) -> tuple:
            start_error = abs(float(asset.start_seconds) - float(shot.start_seconds))
            end_error = abs(float(asset.end_seconds) - float(shot.end_seconds))
            exact_shot_frame = start_error <= 0.05 and end_error <= 0.05
            ref = media_shortcut(asset).upper()
            node_id = str(asset.node_id).upper()
            explicitly_directed = ref in preferred or node_id in preferred
            duration = max(0.0, float(asset.end_seconds) - float(asset.start_seconds))
            identity_anchor = (
                ref == "P1"
                or "PRIMARY RECURRING CHARACTER IDENTITY ANCHOR"
                in str(asset.clip_prompt or "").upper()
            )
            return (
                0 if explicitly_directed else 1,
                0 if exact_shot_frame else 1,
                start_error + end_error,
                duration,
                0 if identity_anchor else 1,
                ref,
            )

        visual = sorted(
            (asset for asset in media if asset.media_type in {"image", "video"}),
            key=preview_score,
        )
        image_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        for asset in visual:
            keys = (
                str(asset.clip_id or ""),
                str(asset.node_id or ""),
                str(asset.source_node_id or ""),
            )
            for key in keys:
                candidate = self.preview_paths.get(key)
                if candidate and candidate.is_file():
                    return candidate, media_shortcut(asset)
            local = Path(str(asset.local_path or ""))
            if local.is_file() and local.suffix.lower() in image_suffixes:
                return local, media_shortcut(asset)
        return None, ""

    def _entry_icon(self, entry: dict, label: str) -> QIcon:
        path_text = str(entry.get("preview_path") or "")
        cache_key = path_text or f"placeholder:{label}"
        cached = self._icon_cache.get(cache_key)
        if cached is not None:
            return cached
        canvas = QPixmap(640, 360)
        source = QPixmap(path_text) if path_text and Path(path_text).is_file() else QPixmap()
        if source.isNull():
            canvas.fill(QColor("#090b0d"))
            painter = QPainter(canvas)
            painter.setPen(QColor("#64717c"))
            painter.drawText(canvas.rect(), Qt.AlignCenter, f"{label}\nNO VISUAL REFERENCE")
            painter.end()
        else:
            scaled = source.scaled(
                canvas.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            left = max(0, (scaled.width() - canvas.width()) // 2)
            top = max(0, (scaled.height() - canvas.height()) // 2)
            canvas = scaled.copy(left, top, canvas.width(), canvas.height())
        icon = QIcon(canvas)
        self._icon_cache[cache_key] = icon
        return icon

    def _refresh_all_cards(self) -> None:
        cursor = 0.0
        for index in range(self.block_list.count()):
            item = self.block_list.item(index)
            entry = dict(item.data(Qt.UserRole) or {})
            duration = max(0.5, snap_timeline_seconds(float(entry.get("duration", 5.0))))
            entry["duration"] = duration
            entry["new_start"] = cursor
            entry["new_end"] = cursor + duration
            item.setData(Qt.UserRole, entry)
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
            item.setBackground(QBrush())
            item.setForeground(QBrush())
            refs = ", ".join(entry.get("media_refs") or []) or "no media"
            action = str(entry.get("subject_action") or "No core action yet").strip()
            environment = str(entry.get("environment_response") or "").strip()
            if len(action) > 145:
                action = action[:142].rstrip() + "..."
            if len(environment) > 90:
                environment = environment[:87].rstrip() + "..."
            environment_text = f"\n\n{environment}" if environment else ""
            item.setIcon(self._entry_icon(entry, f"SHOT {index + 1}"))
            heading = (
                f"SHOT {index + 1}  ·  {cursor:.1f}–{cursor + duration:.1f}s  ·  "
                f"{duration:.1f}s"
            )
            preset = str(entry.get("preset") or "Untitled Shot")
            footer = (
                f"FRAME {entry.get('preview_ref') or '—'}  ·  "
                f"SPEECH {int(entry.get('dialogue_count', 0))}  ·  MEDIA {refs}"
            )
            mode = self.view_mode
            if mode == "details":
                card_text = f"{heading}  |  {preset}  |  {footer}"
            elif mode == "list":
                compact_action = action[:100].rstrip() + ("..." if len(action) > 100 else "")
                card_text = f"{heading}\n{preset} · {compact_action}\n{footer}"
            elif mode == "small_icons":
                card_text = f"{heading}\n{preset}\n{footer}"
            elif mode == "medium_icons":
                compact_action = action[:80].rstrip() + ("..." if len(action) > 80 else "")
                card_text = f"{heading}\n{preset}\n\n{compact_action}\n\n{footer}"
            elif mode == "tiles":
                compact_action = action[:120].rstrip() + ("..." if len(action) > 120 else "")
                card_text = f"{heading}\n{preset}\n{compact_action}\n{footer}"
            else:
                card_text = (
                    f"{heading}\n{preset}\n\n{action}{environment_text}\n\n{footer}"
                )
            item.setText(card_text)
            item.setToolTip(
                f"Drag and drop to reorder SHOT {index + 1}\n"
                f"{cursor:.1f}–{cursor + duration:.1f}s · {refs}"
            )
            cursor += duration
        self._refresh_duration_summary()
        self._load_selected(self.block_list.currentItem(), None)

    def _refresh_duration_summary(self) -> None:
        current = sum(
            float((self.block_list.item(index).data(Qt.UserRole) or {}).get("duration", 0.0))
            for index in range(self.block_list.count())
        )
        target = float(self.target_spin.value())
        delta = current - target
        self.original_label.setText(f"ORIGINAL  {self.original_duration:.1f}s")
        self.current_label.setText(f"EDITED  {current:.1f}s")
        self.delta_label.setText(
            f"{'OVER' if delta > 0.01 else 'UNDER' if delta < -0.01 else 'ON TARGET'}  "
            f"{abs(delta):.1f}s"
        )
        self.current_label.setStyleSheet(
            "color:#47d7ff; font-weight:700;" if abs(current - self.original_duration) > 0.01
            else "font-weight:700;"
        )
        self.delta_label.setStyleSheet(
            "color:#ffcb55; font-weight:700;" if abs(delta) > 0.01
            else "color:#65d48b; font-weight:700;"
        )

    def _load_selected(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        self._loading_inspector = True
        enabled = current is not None
        self.title_edit.setEnabled(enabled)
        self.duration_spin.setEnabled(enabled)
        self.action_edit.setEnabled(enabled)
        self.delete_button.setEnabled(enabled and self.block_list.count() > 1)
        self._refresh_move_buttons()
        if current is None:
            self.title_edit.clear()
            self.action_edit.clear()
            self.detail_label.setText("Select a Shot block.")
        else:
            entry = dict(current.data(Qt.UserRole) or {})
            self.title_edit.setText(str(entry.get("preset") or ""))
            self.duration_spin.setValue(float(entry.get("duration", 5.0)))
            self.action_edit.setPlainText(str(entry.get("subject_action") or ""))
            self.detail_label.setText(
                f"Source: {entry.get('cue_id') or 'New Shot'}\n"
                f"Original: {float(entry.get('original_start', 0.0)):.1f}–"
                f"{float(entry.get('original_end', 0.0)):.1f}s\n"
                f"Speech layers: {int(entry.get('dialogue_count', 0))}\n"
                f"Media: {', '.join(entry.get('media_refs') or []) or 'none'}"
            )
        self._loading_inspector = False

    def _save_selected(self, *_args) -> None:
        if self._loading_inspector:
            return
        item = self.block_list.currentItem()
        if item is None:
            return
        entry = dict(item.data(Qt.UserRole) or {})
        entry["preset"] = self.title_edit.text().strip() or "Untitled Shot"
        entry["subject_action"] = self.action_edit.toPlainText().strip()
        entry["duration"] = snap_timeline_seconds(self.duration_spin.value())
        item.setData(Qt.UserRole, entry)
        self._refresh_all_cards()

    def _add_shot(self) -> None:
        row = self.block_list.currentRow()
        insert_at = self.block_list.count() if row < 0 else row + 1
        item = self._insert_entry({
            "cue_id": f"story-new-{secrets.token_hex(6)}",
            "is_new": True,
            "original_start": 0.0,
            "original_end": 0.0,
            "duration": 5.0,
            "preset": "New Story Beat",
            "subject_action": "",
            "environment_response": "",
            "framing": "Medium-wide",
            "dialogue_count": 0,
            "media_refs": [],
            "preview_path": "",
            "preview_ref": "",
        }, insert_at)
        self.block_list.setCurrentItem(item)
        self._refresh_all_cards()
        self.title_edit.setFocus()
        self.title_edit.selectAll()

    def _delete_shot(self) -> None:
        if self.block_list.count() <= 1:
            return
        row = self.block_list.currentRow()
        if row < 0:
            return
        self.block_list.takeItem(row)
        self.block_list.setCurrentRow(min(row, self.block_list.count() - 1))
        self._refresh_all_cards()

    def entries(self) -> list[dict]:
        self._save_selected()
        self._refresh_all_cards()
        return [
            deepcopy(self.block_list.item(index).data(Qt.UserRole) or {})
            for index in range(self.block_list.count())
        ]

    def _accept_if_valid(self) -> None:
        if not self.block_list.count():
            QMessageBox.warning(self, "Storyboard", "At least one Shot is required.")
            return
        self.accept()


class DirectorCueDialog(QDialog):
    PRESETS = {
        "shot": (
            "Establishing Shot", "Hero Reveal", "Product Demonstration",
            "Action Beat", "Reaction Close-up", "Final Hero Shot",
        ),
        "transition": (
            "Hard Cut", "Match Cut", "Match-on-action", "Whip Pan",
            "Cross Dissolve", "Ink Wipe", "J-cut", "L-cut",
        ),
        "marker": (
            "SFX Cue", "Music Cue", "Beat", "Camera Cue", "Dialogue Cue", "Ending Hold",
        ),
        "cut": ("CUT",),
    }
    FRAMING = (
        "Extreme wide", "Wide", "Medium-wide", "Medium", "Medium close-up", "Close-up", "Extreme close-up"
    )
    CAMERA_ANGLES = (
        "Eye level", "Low angle", "High angle", "Top-down", "Dutch angle", "Over-the-shoulder", "POV"
    )
    CAMERA_MOVEMENTS = (
        "Static", "Push in", "Pull out", "Pan left", "Pan right", "Tilt up", "Tilt down",
        "Dolly", "Truck", "Crane", "Orbit", "Handheld", "Whip pan", "Rack focus",
    )
    MOVEMENT_SPEEDS = ("Very slow", "Slow", "Moderate", "Fast", "Very fast")
    MOVEMENT_AMPLITUDES = ("Tiny", "Small", "Medium", "Large", "Extreme")

    def __init__(self, cue: DirectorCue, duration: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cue_type = cue.cue_type
        self._native_audio_original = cue.native_audio_direction
        self._environment_continuity_original = cue.environment_continuity
        self._audio_reference_intent_original = cue.audio_reference_intent
        self._native_audio_qc_original = cue.native_audio_qc_status
        self._native_audio_override_flags = {
            "native_audio_direction": cue.native_audio_direction_user_edited,
            "environment_continuity": cue.environment_continuity_user_edited,
            "audio_reference_intent": cue.audio_reference_intent_user_edited,
            "native_audio_qc_status": cue.native_audio_qc_user_edited,
        }
        self.setWindowTitle(f"{cue.cue_type.title()} Tool · {cue.cue_id}")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.setEditable(True)
        self.preset_combo.addItems(self.PRESETS.get(cue.cue_type, (cue.cue_type.title(),)))
        self.preset_combo.setCurrentText(cue.preset)
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setRange(0.0, duration)
        self.start_spin.setDecimals(2)
        self.start_spin.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.start_spin.setSuffix(" s")
        self.start_spin.setValue(cue.start_seconds)
        self.end_spin = QDoubleSpinBox()
        self.end_spin.setRange(0.05, duration)
        self.end_spin.setDecimals(2)
        self.end_spin.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.end_spin.setSuffix(" s")
        self.end_spin.setValue(min(duration, cue.end_seconds))
        self.detail_edit = QPlainTextEdit(cue.detail)
        self.detail_edit.setPlaceholderText(
            "Describe framing, camera movement, action, transition mechanics, sound, or final hold."
        )
        self.detail_edit.setFixedHeight(100)
        form.addRow("Shot Prompt Preset" if cue.cue_type == "shot" else "Preset", self.preset_combo)
        form.addRow("Start", self.start_spin)
        form.addRow("End", self.end_spin)
        if cue.cue_type == "shot":
            self.framing_combo = self._editable_combo(self.FRAMING, cue.framing)
            self.angle_combo = self._editable_combo(self.CAMERA_ANGLES, cue.camera_angle)
            self.movement_combo = self._editable_combo(self.CAMERA_MOVEMENTS, cue.camera_movement)
            self.movement_combo.setToolTip("Camera movement path")
            movement_row = QWidget()
            movement_layout = QHBoxLayout(movement_row)
            movement_layout.setContentsMargins(0, 0, 0, 0)
            movement_layout.setSpacing(4)
            self.speed_combo = self._editable_combo(self.MOVEMENT_SPEEDS, cue.movement_speed)
            self.amplitude_combo = self._editable_combo(self.MOVEMENT_AMPLITUDES, cue.movement_amplitude)
            self.speed_combo.setToolTip("Movement speed")
            self.amplitude_combo.setToolTip("Movement amplitude")
            movement_layout.addWidget(self.movement_combo, 2)
            movement_layout.addWidget(self.speed_combo, 1)
            movement_layout.addWidget(self.amplitude_combo, 1)
            self.subject_action_edit = QPlainTextEdit(cue.subject_action)
            self.subject_action_edit.setPlaceholderText(
                "Must-complete core action only; maximum three physical beats per five seconds"
            )
            self.subject_action_edit.setFixedHeight(58)
            self.environment_response_edit = QPlainTextEdit(cue.environment_response)
            self.environment_response_edit.setPlaceholderText(
                "Required contact-driven reaction: impact, water, debris or sound"
            )
            self.environment_response_edit.setFixedHeight(58)
            self.continuity_state_edit = QPlainTextEdit(cue.continuity_state)
            self.continuity_state_edit.setPlaceholderText(
                "Incoming/outgoing body pose, weapon state, velocity, screen direction and camera trajectory"
            )
            self.continuity_state_edit.setFixedHeight(58)
            self.optional_flourish_edit = QPlainTextEdit(cue.optional_flourish)
            self.optional_flourish_edit.setPlaceholderText(
                "Dispensable leaves, sparks, cloth motion, secondary feints or ornamental camera detail"
            )
            self.optional_flourish_edit.setFixedHeight(58)
            self.detail_edit.setPlaceholderText("Optional additional shot instruction")
            self.detail_edit.setFixedHeight(58)
            self.continuity_combo = QComboBox()
            self.continuity_combo.addItems(CONTINUITY_MODE_LABELS)
            self.continuity_combo.setCurrentText(cue.continuity_mode)
            self.continuity_combo.setToolTip(
                "How this Shot continues from the preceding generated segment"
            )
            if cue.track_id:
                form.addRow("Visual Track", QLabel(cue.track_id))
            form.addRow("Framing", self.framing_combo)
            form.addRow("Camera angle", self.angle_combo)
            form.addRow("Camera movement", movement_row)
            form.addRow("Core action (required)", self.subject_action_edit)
            form.addRow("Required environment response", self.environment_response_edit)
            form.addRow("State to preserve", self.continuity_state_edit)
            form.addRow("Optional flourish", self.optional_flourish_edit)
            form.addRow("Additional direction", self.detail_edit)
            self.native_audio_direction_edit = QPlainTextEdit(cue.native_audio_direction)
            self.native_audio_direction_edit.setPlaceholderText(
                "Auto: acoustic space, camera distance, position, speaking state, ambience, Foley and diegetic-source rules"
            )
            self.native_audio_direction_edit.setFixedHeight(88)
            self.environment_continuity_edit = QPlainTextEdit(cue.environment_continuity)
            self.environment_continuity_edit.setPlaceholderText(
                "Auto: same-space continuity, distance change, or interior/exterior acoustic transition"
            )
            self.environment_continuity_edit.setFixedHeight(68)
            self.audio_reference_intent_edit = QPlainTextEdit(cue.audio_reference_intent)
            self.audio_reference_intent_edit.setPlaceholderText(
                "Auto: Audio/Video references guide location acoustics only; never copy words or voice identity"
            )
            self.audio_reference_intent_edit.setFixedHeight(68)
            self.native_audio_qc_edit = QPlainTextEdit(cue.native_audio_qc_status)
            self.native_audio_qc_edit.setPlaceholderText(
                "Automatic read-only analysis result; editing protects this note from later QC updates"
            )
            self.native_audio_qc_edit.setFixedHeight(58)
            form.addRow("Native Audio Direction", self.native_audio_direction_edit)
            form.addRow("Environment Continuity", self.environment_continuity_edit)
            form.addRow("Audio Reference Intent", self.audio_reference_intent_edit)
            form.addRow("Native Audio QC status", self.native_audio_qc_edit)
            budget_text = cue.action_budget_status.replace("_", " ").title()
            if cue.action_budget_notes:
                budget_text += " · " + cue.action_budget_notes
            self.action_budget_label = QLabel(budget_text)
            self.action_budget_label.setWordWrap(True)
            form.addRow("H3 action budget", self.action_budget_label)
            for editor in (
                self.subject_action_edit,
                self.environment_response_edit,
                self.optional_flourish_edit,
            ):
                editor.textChanged.connect(self._refresh_action_budget_preview)
            self.start_spin.valueChanged.connect(self._refresh_action_budget_preview)
            self.end_spin.valueChanged.connect(self._refresh_action_budget_preview)
            if cue.semantic_reference_directions:
                semantic_reference_text = QPlainTextEdit()
                semantic_reference_text.setReadOnly(True)
                semantic_reference_text.setFixedHeight(74)
                semantic_reference_text.setPlainText(
                    "\n\n".join(
                        f"{node_id}: {direction}"
                        for node_id, direction in cue.semantic_reference_directions.items()
                    )
                )
                semantic_reference_text.setToolTip(
                    "Automatically synchronized after AI ENRICH. Original authored Shot fields remain unchanged."
                )
                form.addRow("AI media references", semantic_reference_text)
            form.addRow("Continuity into Shot", self.continuity_combo)
        else:
            form.addRow("Direction", self.detail_edit)
        recommend_button = QPushButton("RECOMMEND DIRECTION FROM PRESET")
        recommend_button.setToolTip(
            "Fill Subject Action, Environment Response and Additional Direction from the selected preset"
        )
        recommend_button.clicked.connect(lambda: self._apply_recommendation(force=True))
        form.addRow(recommend_button)
        self.preset_combo.currentTextChanged.connect(
            lambda _text: self._apply_recommendation(force=False)
        )
        self._apply_recommendation(force=False)
        self._refresh_action_budget_preview()
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate(self) -> None:
        if not self.preset_combo.currentText().strip():
            QMessageBox.warning(self, "Preset required", "Choose or enter a director cue preset.")
            return
        if self.end_spin.value() <= self.start_spin.value():
            QMessageBox.warning(self, "Invalid range", "Cue end must be later than its start.")
            return
        self.accept()

    def _refresh_action_budget_preview(self, *_args) -> None:
        if self.cue_type != "shot" or not hasattr(self, "action_budget_label"):
            return
        budgeted = normalize_shot_action_budget({
            "start_seconds": self.start_spin.value(),
            "end_seconds": self.end_spin.value(),
            "subject_action": self.subject_action_edit.toPlainText().strip(),
            "environment_response": self.environment_response_edit.toPlainText().strip(),
            "continuity_state": self.continuity_state_edit.toPlainText().strip(),
            "optional_flourish": self.optional_flourish_edit.toPlainText().strip(),
        })
        budget = budgeted["action_budget"]
        label = (
            f"{budget['status'].replace('_', ' ').title()} · "
            f"core {budget['core_action_count']}/{budget['core_action_limit']} · "
            f"response {budget['required_response_count']}/{budget['required_response_limit']} · "
            f"optional {budget['optional_action_count']}/{budget['optional_action_limit']}"
        )
        if budget["notes"]:
            label += " · " + budget["notes"]
        self.action_budget_label.setText(label)

    def _apply_recommendation(self, *, force: bool) -> None:
        preset = self.preset_combo.currentText().strip()
        if self.cue_type == "shot":
            suggestion = SHOT_RECOMMENDATIONS.get(preset)
            if not suggestion:
                return
            targets = (
                (self.subject_action_edit, suggestion["subject_action"], "subject_action"),
                (self.environment_response_edit, suggestion["environment_response"], "environment_response"),
                (self.detail_edit, suggestion["detail"], "detail"),
            )
            for field, text, key in targets:
                current = field.toPlainText().strip()
                known = {item[key] for item in SHOT_RECOMMENDATIONS.values()}
                if force or not current or current in known:
                    field.setPlainText(text)
            return
        suggestions = (
            MARKER_RECOMMENDATIONS if self.cue_type == "marker" else TRANSITION_RECOMMENDATIONS
        )
        text = suggestions.get(preset, "")
        current = self.detail_edit.toPlainText().strip()
        known = set(MARKER_RECOMMENDATIONS.values()) | set(TRANSITION_RECOMMENDATIONS.values())
        if text and (force or not current or current in known):
            self.detail_edit.setPlainText(text)

    @staticmethod
    def _editable_combo(values: tuple[str, ...], current: str) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(values)
        combo.setCurrentText(current)
        return combo

    def state(self) -> dict:
        start, end = snap_timeline_range(
            self.start_spin.value(), self.end_spin.value(), self.end_spin.maximum()
        )
        state = {
            "preset": self.preset_combo.currentText().strip(),
            "start_seconds": start,
            "end_seconds": end,
            "detail": self.detail_edit.toPlainText().strip(),
        }
        if self.cue_type == "shot":
            state.update(
                framing=self.framing_combo.currentText().strip(),
                camera_angle=self.angle_combo.currentText().strip(),
                camera_movement=self.movement_combo.currentText().strip(),
                movement_speed=self.speed_combo.currentText().strip(),
                movement_amplitude=self.amplitude_combo.currentText().strip(),
                subject_action=self.subject_action_edit.toPlainText().strip(),
                environment_response=self.environment_response_edit.toPlainText().strip(),
                continuity_state=self.continuity_state_edit.toPlainText().strip(),
                optional_flourish=self.optional_flourish_edit.toPlainText().strip(),
                continuity_mode=self.continuity_combo.currentText(),
                native_audio_direction=self.native_audio_direction_edit.toPlainText().strip(),
                environment_continuity=self.environment_continuity_edit.toPlainText().strip(),
                audio_reference_intent=self.audio_reference_intent_edit.toPlainText().strip(),
                native_audio_qc_status=self.native_audio_qc_edit.toPlainText().strip(),
                native_audio_direction_user_edited=(
                    self._native_audio_override_flags["native_audio_direction"]
                    or self.native_audio_direction_edit.toPlainText().strip()
                    != self._native_audio_original.strip()
                ),
                environment_continuity_user_edited=(
                    self._native_audio_override_flags["environment_continuity"]
                    or self.environment_continuity_edit.toPlainText().strip()
                    != self._environment_continuity_original.strip()
                ),
                audio_reference_intent_user_edited=(
                    self._native_audio_override_flags["audio_reference_intent"]
                    or self.audio_reference_intent_edit.toPlainText().strip()
                    != self._audio_reference_intent_original.strip()
                ),
                native_audio_qc_user_edited=(
                    self._native_audio_override_flags["native_audio_qc_status"]
                    or self.native_audio_qc_edit.toPlainText().strip()
                    != self._native_audio_qc_original.strip()
                ),
            )
            budgeted = normalize_shot_action_budget({
                "start_seconds": start,
                "end_seconds": end,
                "subject_action": state["subject_action"],
                "environment_response": state["environment_response"],
                "continuity_state": state["continuity_state"],
                "optional_flourish": state["optional_flourish"],
            })
            state.update(
                subject_action=budgeted["subject_action"],
                authored_subject_action=self.subject_action_edit.toPlainText().strip(),
                environment_response=budgeted["environment_response"],
                authored_environment_response=self.environment_response_edit.toPlainText().strip(),
                continuity_state=budgeted["continuity_state"],
                optional_flourish=budgeted["optional_flourish"],
                h3_executable_action=budgeted["h3_executable_action"],
                h3_optional_flourish=budgeted["h3_optional_flourish"],
                action_budget_status=budgeted["action_budget"]["status"],
                action_budget_notes=budgeted["action_budget"]["notes"],
            )
        return state


class WorkspaceDesignCommand(QUndoCommand):
    def __init__(
        self,
        before: dict,
        after: dict,
        restore,
        label: str = "Apply AI Director Design",
    ) -> None:
        super().__init__(label)
        self.before = before
        self.after = after
        self.restore = restore

    def undo(self) -> None:
        self.restore(self.before)

    def redo(self) -> None:
        self.restore(self.after)


class DesignPageDialog(QDialog):
    """Standalone AI concept-to-Director-JSON design workspace."""

    apply_requested = Signal(object, bool)
    cleanup_requested = Signal(object)

    def __init__(
        self,
        runtime,
        context: dict,
        capacities: dict[str, int],
        parent: QWidget | None = None,
        context_provider=None,
    ) -> None:
        super().__init__(parent)
        self.runtime = runtime
        self.context = dict(context)
        self.context_provider = context_provider
        self.active_design_context: dict | None = None
        self.capacities = dict(capacities)
        self.settings = load_design_settings(DESIGN_SETTINGS_ENV)
        if self.settings.image_checkpoint == "epicrealismXL_vxviLastfameRealism.safetensors":
            self.settings.image_checkpoint = "z_image_turbo_bf16.safetensors"
            if self.settings.image_steps == 24:
                self.settings.image_steps = 8
            if abs(self.settings.image_cfg - 5.5) < 0.001:
                self.settings.image_cfg = 1.0
        self.runner = JsonLineProcess(self, "ai-design")
        self.runner.message.connect(self._service_message)
        self.runner.finished.connect(self._service_finished)
        self.concept_media_runner = JsonLineProcess(self, "design-concept-image")
        self.concept_media_runner.message.connect(self._concept_media_message)
        self.concept_media_runner.finished.connect(self._concept_media_finished)
        self.concept_blip_runner = JsonLineProcess(self, "design-concept-blip")
        self.concept_blip_runner.message.connect(self._concept_blip_message)
        self.concept_blip_runner.finished.connect(self._concept_blip_finished)
        self.pending_action = ""
        self.validated_plan: dict | None = None
        self.apply_in_progress = False
        self.apply_preflight_blockers: list[str] = []
        self.apply_preflight_warnings: list[str] = []
        self.pipeline_stage = ""
        self.pending_requirement = ""
        self.required_text_layers: list[dict] = []
        self.duration_contract_retry_count = 0
        self.dialogue_language_retry_count = 0
        self.speech_layer_retry_count = 0
        self.design_json_retry_count = 0
        self.concept_image_path: Path | None = None
        self.concept_blip_caption = ""
        self.concept_media_result: dict = {}
        self.planned_plan: dict | None = None
        self.generated_references: list[dict] = []
        self.design_image_warnings: list[str] = []
        self.concept_blip_jobs: dict[str, dict] = {}
        self.pending_refinement_prompt = ""
        self._last_provider = self.settings.provider
        self.setWindowTitle("AI DESIGN · Concept to H3 Director Workspace")
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else QRectF(0, 0, 1280, 800).toRect()
        target_width = max(560, min(1180, available.width() - 40))
        target_height = max(420, min(760, available.height() - 40))
        self.resize(target_width, target_height)
        self.setMinimumSize(560, 420)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(4, 4, 4, 4)
        self.design_scroll = QScrollArea()
        self.design_scroll.setWidgetResizable(True)
        self.design_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.design_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        design_page = QWidget()
        layout = QVBoxLayout(design_page)
        layout.setContentsMargins(6, 6, 6, 6)
        self.design_scroll.setWidget(design_page)
        outer_layout.addWidget(self.design_scroll)

        connection = QGroupBox("AI CONNECTION")
        connection_form = QGridLayout(connection)
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Online GPT · OpenAI", "openai")
        self.provider_combo.addItem("LM Studio · Local OpenAI-compatible", "lm_studio")
        self.provider_combo.setCurrentIndex(
            max(0, self.provider_combo.findData(self.settings.provider))
        )
        self.base_url_edit = QLineEdit()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText(
            "OpenAI API key or OPENAI_API_KEY environment variable · LM Studio usually leaves this empty"
        )
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 1800)
        self.timeout_spin.setValue(self.settings.timeout)
        self.timeout_spin.setSuffix(" s")
        self.test_button = QPushButton("TEST CONNECTION")
        self.test_button.clicked.connect(self.test_connection)
        connection_form.addWidget(QLabel("Provider"), 0, 0)
        connection_form.addWidget(self.provider_combo, 0, 1)
        connection_form.addWidget(QLabel("Base URL"), 0, 2)
        connection_form.addWidget(self.base_url_edit, 0, 3)
        connection_form.addWidget(QLabel("Model"), 1, 0)
        connection_form.addWidget(self.model_combo, 1, 1)
        connection_form.addWidget(QLabel("API Key"), 1, 2)
        connection_form.addWidget(self.api_key_edit, 1, 3)
        connection_form.addWidget(QLabel("Timeout"), 2, 0)
        connection_form.addWidget(self.timeout_spin, 2, 1)
        connection_form.addWidget(self.test_button, 2, 3)
        layout.addWidget(connection)

        media_generation = QGroupBox("COMFYUI REFERENCE IMAGE GENERATION")
        media_form = QGridLayout(media_generation)
        self.generate_images_check = QCheckBox(
            "Generate every image requested by the AI plan with Z-Image"
        )
        self.generate_images_check.setChecked(self.settings.generate_comfy_images)
        self.image_checkpoint_combo = QComboBox()
        self.image_checkpoint_combo.setEditable(True)
        self.image_checkpoint_combo.setMinimumWidth(290)
        self.image_checkpoint_combo.addItem(self.settings.image_checkpoint)
        self.image_checkpoint_combo.setCurrentText(self.settings.image_checkpoint)
        self.image_checkpoint_combo.setToolTip(
            "Choose a diffusion model reported by ComfyUI UNETLoader for the Z-Image workflow"
        )
        self.refresh_checkpoints_button = QToolButton()
        self.refresh_checkpoints_button.setText("↻")
        self.refresh_checkpoints_button.setToolTip("Refresh Z-Image UNETLoader models from ComfyUI")
        self.refresh_checkpoints_button.clicked.connect(self.refresh_checkpoints)
        self.image_width_spin = QSpinBox()
        self.image_width_spin.setRange(256, 2048)
        self.image_width_spin.setSingleStep(64)
        self.image_width_spin.setValue(self.settings.image_width)
        self.image_height_spin = QSpinBox()
        self.image_height_spin.setRange(256, 2048)
        self.image_height_spin.setSingleStep(64)
        self.image_height_spin.setValue(self.settings.image_height)
        self.image_steps_spin = QSpinBox()
        self.image_steps_spin.setRange(1, 100)
        self.image_steps_spin.setValue(self.settings.image_steps)
        self.image_cfg_spin = QDoubleSpinBox()
        self.image_cfg_spin.setRange(0.0, 30.0)
        self.image_cfg_spin.setSingleStep(0.5)
        self.image_cfg_spin.setValue(self.settings.image_cfg)
        self.image_negative_edit = QLineEdit(self.settings.image_negative_prompt)
        comfy_server = str(self.context.get("comfyui_server", ""))
        self.comfy_server_label = QLabel(comfy_server or "Use the ComfyUI URL from the main workspace")
        self.comfy_server_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        media_form.setHorizontalSpacing(6)
        media_form.setVerticalSpacing(4)
        media_form.addWidget(self.generate_images_check, 0, 0, 1, 9)
        media_form.addWidget(QLabel("Server"), 1, 0)
        media_form.addWidget(self.comfy_server_label, 1, 1, 1, 2)
        media_form.addWidget(QLabel("Z-Image UNET"), 1, 3)
        media_form.addWidget(self.image_checkpoint_combo, 1, 4, 1, 4)
        media_form.addWidget(self.refresh_checkpoints_button, 1, 8)
        media_form.addWidget(QLabel("Width"), 2, 0)
        media_form.addWidget(self.image_width_spin, 2, 1)
        media_form.addWidget(QLabel("Height"), 2, 2)
        media_form.addWidget(self.image_height_spin, 2, 3)
        media_form.addWidget(QLabel("Steps"), 2, 4)
        media_form.addWidget(self.image_steps_spin, 2, 5)
        media_form.addWidget(QLabel("CFG"), 2, 6)
        media_form.addWidget(self.image_cfg_spin, 2, 7, 1, 2)
        media_form.addWidget(QLabel("Negative"), 3, 0)
        media_form.addWidget(self.image_negative_edit, 3, 1, 1, 8)
        layout.addWidget(media_generation)

        body = QSplitter(Qt.Horizontal)
        concept_panel = QWidget()
        concept_layout = QVBoxLayout(concept_panel)
        concept_layout.setContentsMargins(0, 0, 4, 0)
        requirement_header = QHBoxLayout()
        requirement_header.addWidget(QLabel("DESIGN REQUIREMENT"))
        requirement_header.addStretch(1)
        self.dialogue_mode_group = QButtonGroup(self)
        self.dialogue_mode_group.setExclusive(True)
        self.dialogue_mode_buttons: dict[str, QPushButton] = {}
        dialogue_modes = (
            (
                "h3_native", "Ori",
                "MiniMax H3 Native Dialogue · no WAV; H3 generates the latest Timeline words",
            ),
            (
                "voxcpm2_local", "Vox",
                "VoxCPM2 Local · create an exact local authored-speech WAV",
            ),
            (
                "qwen3_tts_local", "Qwen",
                "Qwen3-TTS Local · fast offline CustomVoice authored-speech WAV",
            ),
            (
                "edge_tts", "Etts",
                "Edge TTS · create an exact online neural authored-speech WAV",
            ),
        )
        selected_dialogue_mode = str(
            self.context.get("dialogue_tts_engine", "h3_native")
        ).strip().lower()
        if selected_dialogue_mode not in {item[0] for item in dialogue_modes}:
            selected_dialogue_mode = "h3_native"
        self.design_tts_engine = selected_dialogue_mode
        for engine, short_label, tooltip in dialogue_modes:
            button = QPushButton(short_label)
            button.setObjectName(f"designDialogueMode_{short_label}")
            button.setCheckable(True)
            button.setChecked(engine == selected_dialogue_mode)
            button.setToolTip(tooltip)
            button.setMaximumWidth(54)
            button.clicked.connect(
                lambda checked, value=engine: self._select_design_dialogue_mode(value)
                if checked else None
            )
            self.dialogue_mode_group.addButton(button)
            self.dialogue_mode_buttons[engine] = button
            requirement_header.addWidget(button)
        requirement_header.addWidget(QLabel("LANG"))
        self.dialogue_language_combo = QComboBox()
        self.dialogue_language_combo.setObjectName("designDialogueLanguage")
        self.dialogue_language_combo.setToolTip(
            "Dialogue language for AI-authored Dialogue, Voice-over and Lyrics. "
            "Auto deterministically follows the Design Requirement language."
        )
        self.dialogue_language_combo.addItem("Auto", "auto")
        dialogue_language_labels = {
            "Arabic": "Arabic",
            "Chinese": "中文",
            "English": "English",
            "French": "Français",
            "German": "Deutsch",
            "Italian": "Italiano",
            "Japanese": "日本語",
            "Korean": "한국어",
            "Portuguese": "Português",
            "Russian": "Русский",
            "Spanish": "Español",
        }
        for language in H3_STABLE_DIALOGUE_LANGUAGES:
            self.dialogue_language_combo.addItem(
                dialogue_language_labels.get(language, language), language
            )
        language_index = self.dialogue_language_combo.findData(
            self.settings.dialogue_language
        )
        self.dialogue_language_combo.setCurrentIndex(max(0, language_index))
        self.dialogue_language_combo.setMaximumWidth(118)
        self.dialogue_language_combo.currentIndexChanged.connect(
            self._dialogue_language_changed
        )
        requirement_header.addWidget(self.dialogue_language_combo)
        self.subtitles_button = QPushButton()
        self.subtitles_button.setObjectName("designSubtitlesToggle")
        self.subtitles_button.setCheckable(True)
        self.subtitles_button.setChecked(bool(self.settings.subtitles_enabled))
        self.subtitles_button.setMaximumWidth(76)
        self.subtitles_button.setToolTip(
            "Subtitle switch. OFF keeps Dialogue/Voice-over editable on audio Text Layers "
            "without visible captions. ON adds synchronized editable subtitle layers."
        )
        self.subtitles_button.toggled.connect(self._subtitles_toggled)
        self._refresh_subtitles_button()
        requirement_header.addWidget(self.subtitles_button)
        requirement_header.addWidget(QLabel("MUSIC"))
        self.music_mode_combo = QComboBox()
        self.music_mode_combo.setObjectName("designMusicMode")
        self.music_mode_combo.addItem("AUTO", "auto")
        self.music_mode_combo.addItem("OFF", "off")
        self.music_mode_combo.addItem("TIMELINE", "timeline")
        self.music_mode_combo.setToolTip(
            "AUTO lets Qwen plan scene-appropriate music for H3. OFF forbids non-diegetic "
            "music. TIMELINE enables music only inside authored Timeline Music Cues."
        )
        music_mode_index = self.music_mode_combo.findData(
            normalize_design_music_mode(self.context.get("music_mode", "auto"))
        )
        self.music_mode_combo.setCurrentIndex(max(0, music_mode_index))
        self.music_mode_combo.setMaximumWidth(108)
        self.music_mode_combo.currentIndexChanged.connect(self._music_mode_changed)
        requirement_header.addWidget(self.music_mode_combo)
        concept_layout.addLayout(requirement_header)
        self.dialogue_model_warning = QLabel()
        self.dialogue_model_warning.setWordWrap(True)
        concept_layout.addWidget(self.dialogue_model_warning)
        self._refresh_design_voxcpm_model_status()
        self.requirement_edit = QPlainTextEdit()
        self.requirement_edit.setPlaceholderText(
            "Example: I need a 12-second video. Begin with a hand gripping a can of cola, "
            "then slowly zoom out to reveal a woman drinking it."
        )
        self.requirement_edit.setMinimumHeight(180)
        initial_requirement = str(self.context.get("design_requirement", "")).strip()
        special_skill_context = (
            (self.context.get("bound_h3_skills") or {}).get("special") or {}
        )
        requirement_template = str(
            special_skill_context.get("design_requirement_template", "")
        ).strip()
        if initial_requirement:
            self.requirement_edit.setPlainText(initial_requirement)
        elif requirement_template:
            self.requirement_edit.setPlainText(requirement_template)
            self.requirement_edit.setToolTip(
                "Starter template loaded from the selected Special Skill. You can edit or replace it."
            )
        concept_layout.addWidget(self.requirement_edit)

        media_intelligence = QGroupBox("MEDIA POOL INTELLIGENCE")
        media_intelligence_layout = QVBoxLayout(media_intelligence)
        media_intelligence_layout.setContentsMargins(6, 8, 6, 6)
        media_intelligence_layout.setSpacing(4)
        media_help = QLabel(
            "Checked assets are available to the AI. Insert @P1 / @V1 / @A1 into the "
            "requirement when an asset must be used; Design reuses matching media first and "
            "generates only missing material."
        )
        media_help.setWordWrap(True)
        media_help.setStyleSheet("color:#9aa7b1;")
        media_intelligence_layout.addWidget(media_help)
        self.design_media_list = QListWidget()
        self.design_media_list.setAlternatingRowColors(True)
        self.design_media_list.setMinimumHeight(82)
        self.design_media_list.setMaximumHeight(150)
        self.design_media_list.setToolTip(
            "Loaded Media Pool assets plus their BLIP, video-frame, beat/VAD and speech analysis"
        )
        self.design_media_list.itemDoubleClicked.connect(self._insert_media_reference)
        self.design_media_list.itemChanged.connect(lambda _item: self._invalidate_json())
        media_intelligence_layout.addWidget(self.design_media_list)
        media_actions = QHBoxLayout()
        self.refresh_media_button = QPushButton("REFRESH")
        self.refresh_media_button.setToolTip(
            "Refresh Media Pool files and the latest background recognition results"
        )
        self.refresh_media_button.clicked.connect(self.refresh_media_inventory)
        self.insert_media_button = QPushButton("INSERT @ID")
        self.insert_media_button.setToolTip(
            "Insert the selected stable Media Pool reference at the requirement cursor"
        )
        self.insert_media_button.clicked.connect(self._insert_selected_media_reference)
        self.select_all_media_button = QPushButton("ALL")
        self.select_all_media_button.setToolTip("Make every loaded Media Pool asset available to Design")
        self.select_all_media_button.clicked.connect(lambda: self._set_all_media_checked(True))
        self.select_no_media_button = QPushButton("NONE")
        self.select_no_media_button.setToolTip("Hide every Media Pool asset from this Design request")
        self.select_no_media_button.clicked.connect(lambda: self._set_all_media_checked(False))
        self.media_inventory_status = QLabel()
        self.media_inventory_status.setStyleSheet("color:#68c9d8;")
        media_actions.addWidget(self.refresh_media_button)
        media_actions.addWidget(self.insert_media_button)
        media_actions.addWidget(self.select_all_media_button)
        media_actions.addWidget(self.select_no_media_button)
        media_actions.addStretch(1)
        media_actions.addWidget(self.media_inventory_status)
        media_intelligence_layout.addLayout(media_actions)
        concept_layout.addWidget(media_intelligence)

        self.concept_preview_frame = QGroupBox("CONCEPT REFERENCE · COMFYUI → BLIP")
        concept_preview_layout = QVBoxLayout(self.concept_preview_frame)
        self.concept_thumbnail = QLabel("Concept thumbnail will appear here")
        self.concept_thumbnail.setAlignment(Qt.AlignCenter)
        self.concept_thumbnail.setMinimumSize(240, 135)
        self.concept_thumbnail.setMaximumHeight(190)
        self.concept_thumbnail.setStyleSheet(
            "background:#0e1114; border:1px solid #343a40; color:#7d8790;"
        )
        self.concept_caption_label = QLabel("BLIP visual caption: pending")
        self.concept_caption_label.setWordWrap(True)
        self.concept_caption_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        concept_preview_layout.addWidget(self.concept_thumbnail)
        concept_preview_layout.addWidget(self.concept_caption_label)
        self.concept_preview_frame.hide()
        concept_layout.addWidget(self.concept_preview_frame)
        self.replace_check = QCheckBox("Replace current timeline when applying")
        self.replace_check.setChecked(True)
        self.replace_check.setToolTip(
            "Enabled: clear current Shot/Text/Cue blocks and media placement before applying the design"
        )
        concept_layout.addWidget(self.replace_check)
        self.generate_button = QPushButton("CREATE DIRECTOR DESIGN JSON")
        self.generate_button.setStyleSheet("background:#087f96; font-weight:700; padding:10px;")
        self.generate_button.clicked.connect(self.generate_design)
        concept_layout.addWidget(self.generate_button)
        concept_layout.addWidget(QLabel("VALIDATION / APPLY PREVIEW"))
        self.summary_edit = QPlainTextEdit()
        self.summary_edit.setReadOnly(True)
        self.summary_edit.setMinimumHeight(180)
        concept_layout.addWidget(self.summary_edit, 1)
        body.addWidget(concept_panel)

        json_panel = QWidget()
        json_layout = QVBoxLayout(json_panel)
        json_layout.setContentsMargins(4, 0, 0, 0)
        json_layout.addWidget(QLabel("DIRECTOR DESIGN JSON · editable before Apply"))
        self.json_edit = QPlainTextEdit()
        self.json_edit.setPlaceholderText("AI-generated, schema-validated JSON appears here")
        self.json_edit.textChanged.connect(self._invalidate_json)
        json_layout.addWidget(self.json_edit, 1)
        json_actions = QHBoxLayout()
        load_json_button = QPushButton("LOAD JSON")
        load_json_button.setToolTip(
            "Load a prepared Director Design JSON file, then validate and apply it"
        )
        load_json_button.clicked.connect(self.load_design_json)
        validate_button = QPushButton("VALIDATE JSON")
        validate_button.clicked.connect(self.validate_json)
        self.apply_button = QPushButton("APPLY TO H3 WORKSPACE")
        self.apply_button.setEnabled(False)
        self.apply_button.setStyleSheet("background:#197b55; font-weight:700; padding:8px;")
        self.apply_button.clicked.connect(self.apply_design)
        json_actions.addWidget(load_json_button)
        json_actions.addWidget(validate_button)
        json_actions.addStretch(1)
        json_actions.addWidget(self.apply_button)
        json_layout.addLayout(json_actions)
        self.design_busy_overlay = GenerationBusyOverlay(json_panel)
        body.addWidget(json_panel)
        body.setSizes([430, 710])
        layout.addWidget(body, 1)

        self.status_label = QLabel("Ready · API keys are kept in memory only and are never saved")
        self.status_label.setStyleSheet("color:#78cddd; padding:4px;")
        layout.addWidget(self.status_label)
        self.provider_combo.currentIndexChanged.connect(self._provider_changed)
        self._load_provider_fields(self.settings.provider)
        self.refresh_media_inventory()
        QTimer.singleShot(0, self.refresh_checkpoints)

    @staticmethod
    def _inventory_media_id(row: dict) -> str:
        value = str(
            row.get("media_id")
            or row.get("shortcut")
            or row.get("tag")
            or ""
        ).strip()
        tag_match = re.fullmatch(r"<\s*(Picture|Video|Audio)\s+(\d+)\s*>", value, re.I)
        if tag_match:
            prefix = {"picture": "P", "video": "V", "audio": "A"}[
                tag_match.group(1).lower()
            ]
            return f"{prefix}{int(tag_match.group(2))}"
        direct = re.fullmatch(r"@?([PVA])(\d+)", value, re.I)
        return f"{direct.group(1).upper()}{int(direct.group(2))}" if direct else ""

    def refresh_media_inventory(self) -> None:
        """Refresh the Design grounding list without losing the user's checks."""
        previous_checks: dict[str, bool] = {}
        selected_id = ""
        if hasattr(self, "design_media_list"):
            current = self.design_media_list.currentItem()
            if current:
                selected_id = self._inventory_media_id(current.data(Qt.UserRole) or {})
            for index in range(self.design_media_list.count()):
                item = self.design_media_list.item(index)
                row = item.data(Qt.UserRole)
                if isinstance(row, dict):
                    media_id = self._inventory_media_id(row)
                    if media_id:
                        previous_checks[media_id] = item.checkState() == Qt.Checked

        if callable(self.context_provider):
            try:
                latest = self.context_provider()
            except Exception as exc:
                self.status_label.setText(f"Media Pool refresh warning: {exc}")
            else:
                if isinstance(latest, dict):
                    self.context = dict(latest)

        self.design_media_list.clear()
        rows = [
            dict(row) for row in self.context.get("existing_media") or []
            if isinstance(row, dict) and bool(row.get("loaded", False))
        ]
        rows.sort(
            key=lambda row: (
                {"image": 0, "video": 1, "audio": 2}.get(
                    str(row.get("media_type") or row.get("type") or ""), 9
                ),
                int(re.sub(r"\D", "", self._inventory_media_id(row)) or 999),
            )
        )
        for row in rows:
            media_id = self._inventory_media_id(row)
            if not media_id:
                continue
            row["media_id"] = media_id
            media_type = str(row.get("media_type") or row.get("type") or "media").lower()
            filename = str(row.get("filename") or "loaded media")
            analysis = str(row.get("analysis_summary") or row.get("analysis") or "").strip()
            caption = str(row.get("caption") or "").strip()
            clip_prompt = str(row.get("clip_prompt") or "").strip()
            status_bits = [
                "analysed"
                if str(row.get("analysis_status", "")).lower() == "ready"
                else "analysis pending"
            ]
            if row.get("timeline_placed"):
                status_bits.append(
                    f"{row.get('timeline_track_id') or '-'} "
                    f"{float(row.get('start_seconds', 0.0)):.2f}-"
                    f"{float(row.get('end_seconds', 0.0)):.2f}s"
                )
            item = QListWidgetItem(
                f"{media_id}  |  {media_type.upper()}  |  {filename}  |  {' / '.join(status_bits)}"
            )
            item.setData(Qt.UserRole, row)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item.setCheckState(
                Qt.Checked if previous_checks.get(media_id, True) else Qt.Unchecked
            )
            detail = [
                f"Stable reference: @{media_id}",
                f"File: {filename}",
            ]
            if caption:
                detail.append("Visual caption: " + caption)
            if clip_prompt:
                detail.append("Clip prompt: " + clip_prompt)
            if analysis:
                detail.append("Analysis:\n" + analysis[:2400])
            item.setToolTip("\n".join(detail))
            self.design_media_list.addItem(item)
            if media_id == selected_id:
                self.design_media_list.setCurrentItem(item)

        if self.design_media_list.count() and self.design_media_list.currentRow() < 0:
            self.design_media_list.setCurrentRow(0)
        loaded_counts = self.context.get("loaded_media_counts") or {}
        free_counts = self.context.get("available_new_media_capacity") or {}
        self.media_inventory_status.setText(
            f"{len(rows)} loaded  |  free P {int(free_counts.get('image', 0))} "
            f"V {int(free_counts.get('video', 0))} A {int(free_counts.get('audio', 0))}"
            if rows or free_counts
            else "No local media loaded"
        )
        self.design_media_list.setEnabled(bool(rows))
        self.insert_media_button.setEnabled(bool(rows))
        self.select_all_media_button.setEnabled(bool(rows))
        self.select_no_media_button.setEnabled(bool(rows))

    def _set_all_media_checked(self, checked: bool) -> None:
        state = Qt.Checked if checked else Qt.Unchecked
        for index in range(self.design_media_list.count()):
            item = self.design_media_list.item(index)
            if isinstance(item.data(Qt.UserRole), dict):
                item.setCheckState(state)

    def _insert_media_reference(self, item: QListWidgetItem, _column: int = 0) -> None:
        row = item.data(Qt.UserRole)
        if not isinstance(row, dict):
            return
        media_id = self._inventory_media_id(row)
        if not media_id:
            return
        item.setCheckState(Qt.Checked)
        cursor = self.requirement_edit.textCursor()
        before = self.requirement_edit.toPlainText()
        if before and cursor.position() and not before[cursor.position() - 1].isspace():
            cursor.insertText(" ")
        cursor.insertText(f"@{media_id} ")
        self.requirement_edit.setTextCursor(cursor)
        self.requirement_edit.setFocus()

    def _insert_selected_media_reference(self) -> None:
        item = self.design_media_list.currentItem()
        if item:
            self._insert_media_reference(item)

    def _selected_design_context(self) -> dict:
        context = dict(self.context)
        selected: list[dict] = []
        for index in range(self.design_media_list.count()):
            item = self.design_media_list.item(index)
            row = item.data(Qt.UserRole)
            if isinstance(row, dict) and item.checkState() == Qt.Checked:
                selected.append(dict(row))
        context["existing_media"] = selected
        context["selected_existing_media_ids"] = [
            self._inventory_media_id(row) for row in selected
        ]
        selected_language = self.dialogue_language_combo.currentData()
        requirement = self.requirement_edit.toPlainText().strip()
        context["dialogue_language_policy"] = str(selected_language or "auto")
        context["dialogue_language"] = infer_design_dialogue_language(
            requirement, selected_language
        )
        context["subtitles_enabled"] = self.subtitles_button.isChecked()
        context["music_mode"] = normalize_design_music_mode(
            self.music_mode_combo.currentData()
        )
        return context

    @staticmethod
    def _explicit_media_ids(requirement: str) -> set[str]:
        return {
            f"{match.group(1).upper()}{int(match.group(2))}"
            for match in re.finditer(r"(?<![A-Za-z0-9_])@([PVA])(\d+)\b", requirement, re.I)
        }

    def _select_explicit_media_references(self, requirement: str) -> bool:
        requested = self._explicit_media_ids(requirement)
        if not requested:
            return True
        known: dict[str, QListWidgetItem] = {}
        for index in range(self.design_media_list.count()):
            item = self.design_media_list.item(index)
            row = item.data(Qt.UserRole)
            if isinstance(row, dict):
                known[self._inventory_media_id(row)] = item
        missing = sorted(requested.difference(known))
        if missing:
            self._show_preflight_failure(
                "These references are not loaded in the Media Pool: "
                + ", ".join("@" + item for item in missing),
                category="Explicit Media Pool reference",
            )
            return False
        for media_id in requested:
            known[media_id].setCheckState(Qt.Checked)
        return True

    def _save_current_provider_fields(self, provider: str) -> None:
        if provider == "openai":
            self.settings.openai_base_url = self.base_url_edit.text().strip()
            self.settings.openai_model = self.model_combo.currentText().strip()
        else:
            self.settings.lm_studio_base_url = self.base_url_edit.text().strip()
            self.settings.lm_studio_model = self.model_combo.currentText().strip()

    def _load_provider_fields(self, provider: str) -> None:
        if provider == "openai":
            base, model = self.settings.openai_base_url, self.settings.openai_model
        else:
            base, model = self.settings.lm_studio_base_url, self.settings.lm_studio_model
        self.base_url_edit.setText(base)
        self.model_combo.clear()
        if model:
            self.model_combo.addItem(model)
        self.model_combo.setCurrentText(model)
        self.api_key_edit.setEnabled(True)

    def _provider_changed(self, _index: int) -> None:
        self._save_current_provider_fields(self._last_provider)
        provider = self.provider_combo.currentData()
        self._last_provider = provider
        self._load_provider_fields(provider)
        self.status_label.setText(
            "OpenAI Responses API mode" if provider == "openai"
            else "LM Studio local Chat Completions mode"
        )

    def _api_key(self) -> str:
        entered = self.api_key_edit.text().strip()
        if entered or self.provider_combo.currentData() != "openai":
            return entered
        hostname = (urlparse(self.base_url_edit.text().strip()).hostname or "").lower()
        return os.getenv("OPENAI_API_KEY", "") if hostname == "api.openai.com" else ""

    def _persist_settings(self) -> None:
        provider = self.provider_combo.currentData()
        self._save_current_provider_fields(provider)
        self.settings.provider = provider
        self.settings.timeout = self.timeout_spin.value()
        self.settings.dialogue_language = str(
            self.dialogue_language_combo.currentData() or "auto"
        )
        self.settings.subtitles_enabled = self.subtitles_button.isChecked()
        self.settings.generate_comfy_images = self.generate_images_check.isChecked()
        self.settings.image_checkpoint = self.image_checkpoint_combo.currentText().strip()
        self.settings.image_width = self.image_width_spin.value()
        self.settings.image_height = self.image_height_spin.value()
        self.settings.image_steps = self.image_steps_spin.value()
        self.settings.image_cfg = self.image_cfg_spin.value()
        self.settings.image_negative_prompt = self.image_negative_edit.text().strip()
        save_design_settings(DESIGN_SETTINGS_ENV, self.settings)

    def _submit(self, action: str, extra: dict | None = None) -> None:
        self._persist_settings()
        if not self.runner.is_running():
            if not self.runner.start(
                str(self.runtime.python), [str(PROJECT_ROOT / "design_ai_service.py")]
            ):
                self._show_preflight_failure(
                    "AI design service is still stopping; retry when the worker exits.",
                    category="Execution state",
                )
                return
        self.pending_action = action
        self.test_button.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.refresh_checkpoints_button.setEnabled(False)
        self.status_label.setText({
            "test": "Connecting…",
            "comfy_checkpoints": "Reading checkpoints from ComfyUI…",
        }.get(action, "AI is creating structured Director Design JSON…"))
        self.runner.write_json({
            "job": f"design:{time.time_ns()}",
            "action": action,
            "provider": self.provider_combo.currentData(),
            "base_url": self.base_url_edit.text().strip(),
            "model": self.model_combo.currentText().strip(),
            "api_key": self._api_key(),
            "timeout": self.timeout_spin.value(),
            **(extra or {}),
        })

    def _set_pipeline_busy(self, busy: bool) -> None:
        self.test_button.setEnabled(not busy)
        self.generate_button.setEnabled(not busy)
        self.refresh_checkpoints_button.setEnabled(not busy)
        has_media = self.design_media_list.count() > 0
        self.refresh_media_button.setEnabled(not busy)
        self.design_media_list.setEnabled(not busy and has_media)
        self.insert_media_button.setEnabled(not busy and has_media)
        self.select_all_media_button.setEnabled(not busy and has_media)
        self.select_no_media_button.setEnabled(not busy and has_media)
        if busy:
            self.apply_button.setEnabled(False)

    def _set_design_stage(self, message: str, *, start: bool = False) -> None:
        self.status_label.setText(message)
        if start or not self.design_busy_overlay.isVisible():
            self.design_busy_overlay.start(message)
        else:
            self.design_busy_overlay.set_message(message)

    def _show_concept_thumbnail(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.concept_thumbnail.setText("Generated image could not be previewed")
        else:
            self.concept_thumbnail.setPixmap(
                pixmap.scaled(
                    max(240, self.concept_thumbnail.width()),
                    180,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        self.concept_preview_frame.show()

    def _start_concept_image(self, requirement: str) -> None:
        CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        concept_root = CACHE_ROOT / "design_concepts"
        concept_root.mkdir(parents=True, exist_ok=True)
        destination = concept_root / f"concept_{time.time_ns()}.png"
        job_path = CACHE_ROOT / f"design_concept_job_{time.time_ns()}.json"
        job_path.write_text(json.dumps({
            "server": str(self.context.get("comfyui_server", "")).strip(),
            "materials": [{
                "media_type": "image",
                "local_path": str(destination),
                "prompt": requirement,
                "subject_keywords": [],
            }],
            "settings": {
                "checkpoint": self.image_checkpoint_combo.currentText().strip(),
                "width": self.image_width_spin.value(),
                "height": self.image_height_spin.value(),
                "steps": self.image_steps_spin.value(),
                "cfg": self.image_cfg_spin.value(),
                "negative_prompt": self.image_negative_edit.text().strip(),
            },
            "poll_interval": float(self.context.get("comfyui_history_poll_interval", 1.0)),
            "generation_timeout": int(self.context.get("comfyui_generation_timeout", 1800)),
            "http_timeout": int(self.context.get("comfyui_http_timeout", 30)),
        }, ensure_ascii=False), encoding="utf-8")
        self.pipeline_stage = "image"
        self.concept_media_result = {}
        self.concept_image_path = None
        self.concept_blip_caption = ""
        self.concept_preview_frame.show()
        self.concept_thumbnail.clear()
        self.concept_thumbnail.setText("Generating concept reference in ComfyUI…")
        self.concept_caption_label.setText("BLIP visual caption: waiting for image")
        self.status_label.setText("Stage 1/3 · ComfyUI is generating the concept reference…")
        if not self.concept_media_runner.start(
            str(self.runtime.python),
            [str(PROJECT_ROOT / "design_media_service.py"), str(job_path)],
        ):
            self._start_lm_design("Concept image worker was unavailable")

    def _concept_media_message(self, payload: dict) -> None:
        if payload.get("progress"):
            self.status_label.setText("Stage 1/3 · " + str(payload["progress"]))
        if payload.get("completed") or payload.get("error"):
            self.concept_media_result = payload

    def _concept_media_finished(self, exit_code: int, log: str) -> None:
        if self.pipeline_stage != "image":
            return
        outputs = self.concept_media_result.get("outputs") or []
        path = Path(str(outputs[0].get("local_path", ""))) if outputs else None
        if not exit_code and path and path.is_file():
            self.concept_image_path = path.resolve()
            self._show_concept_thumbnail(self.concept_image_path)
            self._start_concept_blip()
            return
        reason = str(self.concept_media_result.get("error") or log[-400:] or "no image output")
        self.concept_thumbnail.setText("Concept generation failed · continuing without image")
        self.concept_caption_label.setText("BLIP skipped: " + reason)
        self._start_lm_design("Concept image generation failed: " + reason)

    def _start_concept_blip(self) -> None:
        if not self.concept_image_path:
            self._start_lm_design("No concept image was available")
            return
        self.pipeline_stage = "blip"
        self.status_label.setText("Stage 2/3 · BLIP is reading the generated concept reference…")
        arguments = [
            str(PROJECT_ROOT / "blip_service.py"),
            "--model",
            str(self.runtime.blip_snapshot),
        ]
        if not self.concept_blip_runner.start(str(self.runtime.python), arguments):
            self._start_lm_design("BLIP worker was unavailable")
            return
        self.concept_blip_runner.write_json({
            "job": f"design-blip:{time.time_ns()}",
            "image": str(self.concept_image_path),
        })

    def _concept_blip_message(self, payload: dict) -> None:
        if payload.get("ready"):
            device = str(payload.get("device", ""))
            self.concept_caption_label.setText(f"BLIP visual caption: analysing on {device}…")
            return
        if self.pipeline_stage != "blip":
            return
        if payload.get("caption"):
            self.concept_blip_caption = str(payload["caption"]).strip()
            self.concept_caption_label.setText(
                "BLIP visual caption: " + self.concept_blip_caption
            )
            self.pipeline_stage = "lm"
            self.concept_blip_runner.stop()
            self._start_lm_design()
        elif payload.get("error") or payload.get("fatal"):
            reason = str(payload.get("error", "BLIP failed"))
            self.concept_caption_label.setText("BLIP failed · LM will use the original brief: " + reason)
            self.pipeline_stage = "lm"
            self.concept_blip_runner.stop()
            self._start_lm_design("BLIP analysis failed: " + reason)

    def _concept_blip_finished(self, exit_code: int, log: str) -> None:
        if self.pipeline_stage == "blip":
            self.pipeline_stage = "lm"
            self._start_lm_design(
                "BLIP stopped before returning a caption: "
                + (log[-300:] or f"worker exit {exit_code}")
            )

    def _start_lm_design(self, fallback_note: str = "") -> None:
        self.pipeline_stage = "lm"
        visual_context = self.concept_blip_caption.strip()
        enriched_requirement = self.pending_requirement
        if visual_context:
            enriched_requirement += (
                "\n\nGENERATED CONCEPT REFERENCE — BLIP VISUAL ANALYSIS:\n"
                + visual_context
                + "\nUse this observed visual content as grounding for subject keywords, media prompts, "
                  "shot continuity, framing, action and environment details. The user's written "
                  "requirement remains authoritative."
            )
        elif fallback_note:
            enriched_requirement += "\n\nREFERENCE PIPELINE NOTE: " + fallback_note
        self.status_label.setText("Stage 3/3 · LM Studio is creating Director Design JSON…")
        self._submit("generate", {
            "system_prompt": build_design_system_prompt(self.context),
            "user_prompt": enriched_requirement,
            "schema": DESIGN_JSON_SCHEMA,
        })

    # The active Z-Image pipeline intentionally starts with an LM planning pass.
    # These later definitions replace the original single-concept implementation
    # while retaining the old methods for project-file compatibility.
    def _show_concept_thumbnail(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.concept_thumbnail.setText("Generated image could not be previewed")
        else:
            self.concept_thumbnail.setPixmap(
                pixmap.scaled(
                    max(240, self.concept_thumbnail.width()),
                    180,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        self.concept_preview_frame.show()

    def _display_design_plan(self, plan: dict) -> None:
        self.json_edit.blockSignals(True)
        self.json_edit.setPlainText(json.dumps(plan, ensure_ascii=False, indent=2))
        self.json_edit.blockSignals(False)
        self._show_summary(plan)

    def _request_lm_unload(self) -> None:
        if self.provider_combo.currentData() != "lm_studio" or not self.runner.is_running():
            return
        self.runner.write_json({
            "job": f"design-unload:{time.time_ns()}",
            "action": "unload_lm",
            "provider": "lm_studio",
            "base_url": self.base_url_edit.text().strip(),
            "model": self.model_combo.currentText().strip(),
            "timeout": min(120, self.timeout_spin.value()),
        })

    def _finish_design_pipeline(self, plan: dict) -> None:
        self.pipeline_stage = "ready"
        self.validated_plan = plan
        self._display_design_plan(plan)
        self._set_pipeline_busy(False)
        self.design_busy_overlay.stop()
        self.apply_button.setEnabled(True)
        image_count = len(self.generated_references)
        self.status_label.setText(
            f"Director Design JSON ready · {image_count} Z-Image reference(s) · review or Apply"
        )
        self._request_lm_unload()

    def _start_plan_images(self, plan: dict) -> None:
        image_requests = [
            item for item in plan.get("media_requests") or []
            if item.get("media_type") == "image"
        ]
        if not image_requests:
            self._finish_design_pipeline(plan)
            return
        CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        concept_root = CACHE_ROOT / "design_materials" / str(time.time_ns())
        concept_root.mkdir(parents=True, exist_ok=True)
        materials: list[dict] = []
        for image_index, request in enumerate(image_requests):
            materials.append({
                **request,
                "request_index": image_index,
                "local_path": str(concept_root / f"picture_{image_index + 1:02d}.png"),
            })
        job_path = CACHE_ROOT / f"z_image_design_job_{time.time_ns()}.json"
        job_path.write_text(json.dumps({
            "server": str(self.context.get("comfyui_server", "")).strip(),
            "workflow_path": str(Z_IMAGE_WORKFLOW),
            "materials": materials,
            "settings": {
                "checkpoint": self.image_checkpoint_combo.currentText().strip(),
                "width": self.image_width_spin.value(),
                "height": self.image_height_spin.value(),
                "steps": self.image_steps_spin.value(),
                "cfg": self.image_cfg_spin.value(),
                "negative_prompt": self.image_negative_edit.text().strip(),
            },
            "poll_interval": float(self.context.get("comfyui_history_poll_interval", 1.0)),
            "generation_timeout": int(self.context.get("comfyui_generation_timeout", 1800)),
            "http_timeout": int(self.context.get("comfyui_http_timeout", 30)),
        }, ensure_ascii=False), encoding="utf-8")
        self.pipeline_stage = "image"
        self.concept_media_result = {}
        self.generated_references = []
        self.design_image_warnings = []
        self.concept_preview_frame.show()
        self.concept_thumbnail.clear()
        self.concept_thumbnail.setText(
            f"LM requested {len(materials)} image(s) · starting Z-Image…"
        )
        self.concept_caption_label.setText("BLIP begins after all requested images are generated")
        self._set_design_stage(
            f"Stage 2/4 · Z-Image is generating {len(materials)} requested reference(s)…"
        )
        if not self.concept_media_runner.start(
            str(self.runtime.python),
            [str(PROJECT_ROOT / "design_media_service.py"), str(job_path)],
        ):
            self.design_image_warnings.append("Z-Image worker was unavailable")
            self._finish_design_pipeline(plan)

    def _concept_media_message(self, payload: dict) -> None:
        if payload.get("progress"):
            self._set_design_stage("Stage 2/4 · " + str(payload["progress"]))
        generated = payload.get("generated_output")
        if generated and generated.get("local_path"):
            path = Path(str(generated["local_path"]))
            if path.is_file() and not any(
                item.get("local_path") == str(path.resolve()) for item in self.generated_references
            ):
                reference = {
                    **generated,
                    "local_path": str(path.resolve()),
                    "caption": "",
                }
                self.generated_references.append(reference)
                self.generated_references.sort(key=lambda item: int(item.get("request_index", 0)))
                self._show_concept_thumbnail(path)
                self.concept_caption_label.setText(
                    f"Generated {len(self.generated_references)} image(s) · BLIP pending"
                )
        if payload.get("completed") or payload.get("error"):
            self.concept_media_result = payload

    def _concept_media_finished(self, exit_code: int, log: str) -> None:
        if self.pipeline_stage != "image":
            return
        for output in self.concept_media_result.get("outputs") or []:
            path = Path(str(output.get("local_path", "")))
            if path.is_file() and not any(
                item.get("local_path") == str(path.resolve()) for item in self.generated_references
            ):
                self.generated_references.append({
                    **output,
                    "local_path": str(path.resolve()),
                    "caption": "",
                })
        self.generated_references.sort(key=lambda item: int(item.get("request_index", 0)))
        self.design_image_warnings.extend(self.concept_media_result.get("warnings") or [])
        if exit_code or self.concept_media_result.get("error"):
            self.design_image_warnings.append(
                str(self.concept_media_result.get("error") or log[-400:] or f"worker exit {exit_code}")
            )
        if self.generated_references:
            self._start_concept_blip()
        elif self.planned_plan:
            self._finish_design_pipeline(self.planned_plan)

    def _start_concept_blip(self) -> None:
        self.pipeline_stage = "blip"
        self._set_design_stage(
            f"Stage 3/4 · BLIP is analysing {len(self.generated_references)} Z-Image reference(s)…"
        )
        arguments = [
            str(PROJECT_ROOT / "blip_service.py"),
            "--model",
            str(self.runtime.blip_snapshot),
        ]
        if not self.concept_blip_runner.start(str(self.runtime.python), arguments):
            self.design_image_warnings.append("BLIP worker was unavailable")
            if self.planned_plan:
                self._finish_design_pipeline(self.planned_plan)
            return
        self.concept_blip_jobs.clear()
        for number, reference in enumerate(self.generated_references, 1):
            job_id = f"design-blip:{number}:{time.time_ns()}"
            self.concept_blip_jobs[job_id] = reference
            self.concept_blip_runner.write_json({
                "job": job_id,
                "image": reference["local_path"],
            })

    def _start_lm_refinement(self) -> None:
        if not self.planned_plan:
            return
        model_plan = deepcopy(self.planned_plan)
        model_plan.pop("design_warnings", None)
        for shot in model_plan.get("shots") or []:
            for field_name in (
                "id", "h3_executable_action", "h3_optional_flourish", "action_budget",
            ):
                shot.pop(field_name, None)
        observations = []
        image_requests = [
            item for item in self.planned_plan.get("media_requests") or []
            if item.get("media_type") == "image"
        ]
        for number, reference in enumerate(self.generated_references, 1):
            request = image_requests[number - 1] if number <= len(image_requests) else {}
            observations.append(
                f"Picture {number}: BLIP observed: {reference.get('caption') or 'caption unavailable'}. "
                f"Planned use: {request.get('prompt', '')}"
            )
        prompt = (
            self.pending_requirement
            + "\n\nCURRENT DIRECTOR DESIGN JSON:\n"
            + json.dumps(model_plan, ensure_ascii=False, indent=2)
            + "\n\nGENERATED Z-IMAGE MATERIAL OBSERVATIONS:\n"
            + "\n".join(observations)
            + "\n\nRefine the Director Design JSON using these real visual observations. Preserve the "
              "duration, image count, image ordering and timeline ranges. Improve subject_keywords, "
              "media prompts, shot continuity, framing, action and environment response. Preserve the "
              "core-action / continuity-state / optional-flourish hierarchy and never expand a Shot "
              "beyond its three-core-actions-per-five-seconds budget. The user's "
              "written requirement remains authoritative. Return the complete schema-valid JSON."
        )
        self.pending_refinement_prompt = prompt
        self.pipeline_stage = "release_comfy"
        self._set_design_stage(
            "Stage 4/4 · releasing Z-Image model memory before LM Studio refinement…"
        )
        if not self.runner.is_running():
            self._begin_lm_refinement()
            return
        self.runner.write_json({
            "job": f"design-comfy-unload:{time.time_ns()}",
            "action": "unload_comfy",
            "base_url": str(self.context.get("comfyui_server", "")).strip(),
            "timeout": max(30, int(self.context.get("comfyui_http_timeout", 30))),
        })

    def _begin_lm_refinement(self) -> None:
        prompt = self.pending_refinement_prompt
        if not prompt:
            if self.planned_plan:
                self._finish_design_pipeline(self.planned_plan)
            return
        self.pipeline_stage = "lm_refine"
        planning_context = self.active_design_context or self._selected_design_context()
        self._submit("generate", {
            "system_prompt": build_design_system_prompt(planning_context),
            "user_prompt": prompt,
            "schema": DESIGN_JSON_SCHEMA,
            "timeout": max(900, self.timeout_spin.value()),
        })
        self._set_design_stage(
            "Stage 4/4 · LM Studio is refining JSON from BLIP observations…"
        )

    def _concept_blip_message(self, payload: dict) -> None:
        if payload.get("ready"):
            self.concept_caption_label.setText(
                f"BLIP analysing on {payload.get('device', '')}…"
            )
            return
        if self.pipeline_stage != "blip":
            return
        reference = self.concept_blip_jobs.pop(str(payload.get("job", "")), None)
        if reference is not None:
            if payload.get("caption"):
                reference["caption"] = str(payload["caption"]).strip()
            else:
                reference["caption"] = ""
                self.design_image_warnings.append(
                    "BLIP: " + str(payload.get("error") or "caption unavailable")
                )
        completed = len(self.generated_references) - len(self.concept_blip_jobs)
        captions = [
            f"P{index + 1}: {item.get('caption') or 'pending'}"
            for index, item in enumerate(self.generated_references)
        ]
        self.concept_caption_label.setText(
            f"BLIP {completed}/{len(self.generated_references)} · " + " | ".join(captions)
        )
        self._set_design_stage(
            f"Stage 3/4 · BLIP analysed {completed}/{len(self.generated_references)} reference(s)"
        )
        if not self.concept_blip_jobs:
            self.pipeline_stage = "lm_refine_starting"
            self.concept_blip_runner.stop()
            QTimer.singleShot(0, self._start_lm_refinement)

    def _concept_blip_finished(self, exit_code: int, log: str) -> None:
        if self.pipeline_stage != "blip":
            return
        if self.concept_blip_jobs:
            self.design_image_warnings.append(
                "BLIP stopped early: " + (log[-300:] or f"worker exit {exit_code}")
            )
            self.concept_blip_jobs.clear()
        self.pipeline_stage = "lm_refine_starting"
        QTimer.singleShot(0, self._start_lm_refinement)

    def _start_lm_design(self, fallback_note: str = "") -> None:
        self.pipeline_stage = "lm_plan"
        planning_context = self.active_design_context or self._selected_design_context()
        free_capacity = planning_context.get("available_new_media_capacity") or self.capacities
        available_ids = [
            str(item) for item in planning_context.get("selected_existing_media_ids") or []
            if str(item).strip()
        ]
        inventory_rule = (
            " First audit and reuse the selected Media Pool inventory ("
            + ", ".join("@" + item for item in available_ids)
            + ") through existing_media_uses."
            if available_ids
            else " No Media Pool assets are selected, so request only the genuinely necessary missing material."
        )
        requested_duration = infer_explicit_design_duration(self.pending_requirement)
        duration_rule = (
            "\n\nMANDATORY DURATION CONTRACT: The requested output is exactly "
            f"{requested_duration:.2f} seconds. Set duration_seconds to exactly "
            f"{requested_duration:.2f}. Keep every authored time range through "
            f"{requested_duration:.2f}s. Do not condense the story to the current "
            "workspace Timeline duration and do not rewrite, merge or drop later Dialogue."
            if requested_duration is not None
            else ""
        )
        dialogue_language = infer_design_dialogue_language(
            self.pending_requirement,
            planning_context.get("dialogue_language_policy", "auto"),
        )
        planning_context["dialogue_language"] = dialogue_language
        dialogue_language_rule = (
            "\n\nMANDATORY DIALOGUE LANGUAGE CONTRACT: The selected language is "
            f"{dialogue_language}. Any Dialogue, Voice-over or Lyrics that you write must use "
            f"natural {dialogue_language} words, and its text_layers.language must be exactly "
            f"'{dialogue_language}'. Never default to English. Do not translate or rewrite exact "
            "verbatim lines already supplied by the user."
        )
        requested_roles = requested_speech_roles(self.pending_requirement)
        speech_layer_rule = (
            "\n\nMANDATORY EDITABLE SPEECH TRACK CONTRACT: The user requested "
            + ", ".join(sorted(role.replace("_", "-") for role in requested_roles))
            + ". Author every spoken line as a separate timed text_layers row, set "
              "explicit_user_requested=true, use an A track, and keep the spoken words out "
              "of all Shot prompt fields. Returning zero matching speech layers is invalid."
            if requested_roles else ""
        )
        prompt = (
            self.pending_requirement
            + duration_rule
            + dialogue_language_rule
            + speech_layer_rule
            + "\n\nMEDIA POOL RULE: @P1, @V1 and @A1 are stable references to the "
              "selected workspace assets, not generated placeholders. An explicit @ID in the "
              "requirement is mandatory: include it in existing_media_uses and preserve its "
              "analysed identity/content. Never emit a replacement media_request for the same "
              "requirement_id."
            + inventory_rule
            + "\n\nMEDIA PLANNING RULE: Decide how many reference images are genuinely useful "
              "before image generation. You may request reusable identity, product, wardrobe or "
              "environment references, and you may instead request time-scoped composition, action-"
              "state or continuity references when they materially reduce ambiguity between story "
              "phases. Choose their count, purpose and timeline ranges from the actual concept; do "
              "not force one image per Shot and do not automatically fill every slot. Create no more "
              f"than the currently free {int(free_capacity.get('image', 0))} image slots. "
              "When the plan contains visual Shots and Picture capacity is free, never return zero image "
              "references. Target approximately one useful visual state per five seconds, capped at one "
              "per Shot, and count genuinely reused Pictures toward that coverage floor. "
              "Avoid true duplicates, but allow visually distinct temporal states of the same subject "
              "when they help H3 advance instead of replaying an earlier action."
        )
        if fallback_note:
            prompt += "\n\nPIPELINE NOTE: " + fallback_note
        self._submit("generate", {
            "system_prompt": build_design_system_prompt(planning_context),
            "user_prompt": prompt,
            "schema": DESIGN_JSON_SCHEMA,
            "max_output_tokens": 32768,
        })
        self._set_design_stage(
            "Stage 1/4 · LM Studio is planning shots and requested image count…",
            start=True,
        )

    def _handle_design_generated(self, payload: dict) -> None:
        try:
            planning_context = (
                self.active_design_context or self._selected_design_context()
            )
            plan = normalize_design_plan(
                payload.get("text", ""),
                self.capacities,
                existing_media=planning_context.get("existing_media") or [],
                strict_t2i_prompts=True,
                repair_media_plan=True,
                authored_requirement=self.pending_requirement,
                special_skill_key=_bound_special_skill_key(
                    planning_context
                ),
                selected_media_ids=planning_context.get("selected_existing_media_ids"),
            )
            if self.pipeline_stage == "lm_refine" and self.planned_plan:
                # Refinement may improve generated-image prompts and shot language,
                # but the first Plan owns every explicit authored text cue.
                plan["text_layers"] = deepcopy(
                    self.planned_plan.get("text_layers") or []
                )
                plan["theme_text"] = str(
                    self.planned_plan.get("theme_text", "")
                )
                plan["theme_text_explicit_user_requested"] = bool(
                    self.planned_plan.get(
                        "theme_text_explicit_user_requested", False
                    )
                )
            plan = protect_explicit_timed_text_layers(
                plan, self.pending_requirement
            )
            validate_explicit_timed_text_contract(
                self.pending_requirement, plan
            )
            dialogue_language = (
                self.active_design_context or self._selected_design_context()
            ).get("dialogue_language", "")
            plan = enforce_design_dialogue_language(
                plan,
                dialogue_language,
                authored_requirement=self.pending_requirement,
            )
            plan = enforce_design_subtitle_policy(
                plan,
                bool((self.active_design_context or self._selected_design_context()).get(
                    "subtitles_enabled", False
                )),
                authored_requirement=self.pending_requirement,
            )
            plan = enforce_design_music_mode(
                plan,
                (self.active_design_context or self._selected_design_context()).get(
                    "music_mode", "auto"
                ),
            )
            required_media_ids = self._explicit_media_ids(self.pending_requirement)
            planned_media_ids = {
                str(item.get("media_id", "")).upper()
                for item in plan.get("existing_media_uses") or []
            }
            selected_media_ids = {
                str(item).upper()
                for item in (
                    self.active_design_context or self._selected_design_context()
                ).get("selected_existing_media_ids") or []
            }
            unselected_ids = sorted(planned_media_ids.difference(selected_media_ids))
            if unselected_ids:
                missing_explicit = sorted(
                    set(unselected_ids).intersection(required_media_ids)
                )
                if missing_explicit:
                    raise ValueError(
                        "Explicit Media Pool references are not enabled for this Design: "
                        + ", ".join("@" + item for item in missing_explicit)
                    )
                plan["existing_media_uses"] = [
                    item for item in plan.get("existing_media_uses") or []
                    if str(item.get("media_id", "")).upper() not in unselected_ids
                ]
                self.design_image_warnings.append(
                    "Removed model-selected Media Pool references that were not enabled: "
                    + ", ".join("@" + item for item in unselected_ids)
                )
            ignored_ids = sorted(required_media_ids.difference(planned_media_ids))
            if ignored_ids:
                raise ValueError(
                    "AI ignored explicit Media Pool references: "
                    + ", ".join("@" + item for item in ignored_ids)
                    + ". Regenerate or add them to existing_media_uses."
                )
            validate_requested_speech_layer_contract(
                self.pending_requirement, plan
            )
        except DesignJSONDecodeError as exc:
            finish_reason = str(payload.get("finish_reason", "")).strip() or "not reported"
            output_characters = int(payload.get("output_characters", 0) or 0)
            if self.pipeline_stage == "lm_refine" and self.planned_plan:
                self.design_image_warnings.append(
                    "LM refinement returned incomplete JSON; retained the validated first "
                    f"Design Plan. finish_reason={finish_reason}, output={output_characters:,} "
                    f"characters, error line {exc.line}, column {exc.column}."
                )
                self._finish_design_pipeline(self.planned_plan)
                return
            if self.pipeline_stage == "lm_plan" and self.design_json_retry_count < 1:
                self.design_json_retry_count += 1
                self._set_design_stage(
                    "Stage 1/4 · JSON was incomplete · automatically retrying a compact complete Plan…"
                )
                self._start_lm_design(
                    fallback_note=(
                        "JSON COMPLETION RECOVERY: The previous response could not be parsed "
                        f"at line {exc.line}, column {exc.column}; finish_reason={finish_reason}, "
                        f"output_characters={output_characters}. Rebuild the entire plan from the "
                        "original requirement. Return exactly one compact schema-valid JSON object "
                        "with no markdown or commentary. Preserve every required Shot, Dialogue, "
                        "Voice-over, continuity state and media range, but remove redundant prose. "
                        "Close every string, array and object and include the final Shot and Final Hold."
                    )
                )
                return
            self._set_pipeline_busy(False)
            self.design_busy_overlay.stop()
            self.json_edit.setPlainText(str(payload.get("text", "")))
            self._show_preflight_failure(
                (
                    f"{exc}. The model returned invalid JSON after one automatic retry. "
                    "This is not the Design Requirement text-box limit. "
                    f"finish_reason={finish_reason}; output={output_characters:,} characters; "
                    "completion budget=32,768 tokens. Try a structured-output-capable model or "
                    "reduce unusually repetitive Skill instructions."
                ),
                category="Design JSON completion",
            )
            return
        except DesignDurationContractError as exc:
            if self.pipeline_stage == "lm_refine" and self.planned_plan:
                self.design_image_warnings.append(
                    "LM refinement tried to change the protected duration; retained the "
                    "validated first Design Plan instead. " + str(exc)
                )
                self._finish_design_pipeline(self.planned_plan)
                return
            if self.pipeline_stage == "lm_plan" and self.duration_contract_retry_count < 1:
                self.duration_contract_retry_count += 1
                requested_duration = infer_explicit_design_duration(
                    self.pending_requirement
                )
                self._start_lm_design(
                    fallback_note=(
                        "DURATION CONTRACT CORRECTION: The previous response was rejected. "
                        f"Rebuild the complete plan at exactly {requested_duration:.2f}s, "
                        "including every later Shot, exact Dialogue cue, transition, marker "
                        "and media range. Do not return the workspace's old duration."
                    )
                )
                return
            self._set_pipeline_busy(False)
            self.design_busy_overlay.stop()
            self.json_edit.setPlainText(str(payload.get("text", "")))
            self._show_preflight_failure(str(exc), category="Duration contract")
            return
        except DesignDialogueLanguageContractError as exc:
            if self.pipeline_stage == "lm_refine" and self.planned_plan:
                self.design_image_warnings.append(
                    "LM refinement changed the protected dialogue language; retained the "
                    "validated first Design Plan instead. " + str(exc)
                )
                self._finish_design_pipeline(self.planned_plan)
                return
            if self.pipeline_stage == "lm_plan" and self.dialogue_language_retry_count < 1:
                self.dialogue_language_retry_count += 1
                selected = (
                    self.active_design_context or self._selected_design_context()
                ).get("dialogue_language", "Chinese")
                self._start_lm_design(
                    fallback_note=(
                        "DIALOGUE LANGUAGE CORRECTION: The previous response was rejected. "
                        f"Rewrite every AI-authored Dialogue, Voice-over and Lyrics line in "
                        f"{selected}, set text_layers.language to '{selected}', and do not "
                        "return English dialogue under another language label."
                    )
                )
                return
            self._set_pipeline_busy(False)
            self.design_busy_overlay.stop()
            warning = (
                "Dialogue language mismatch remains editable on the Timeline; the plan was "
                "preserved after one LM correction attempt. " + str(exc)
            )
            plan.setdefault("design_warnings", []).append(warning)
            self.design_image_warnings.append(warning)
            self.status_label.setText(
                "Dialogue language warning · editable Text Layers preserved"
            )
        except DesignSpeechLayerContractError as exc:
            if self.pipeline_stage == "lm_refine" and self.planned_plan:
                fallback_plan = reconcile_requested_speech_layer_contract(
                    self.pending_requirement, self.planned_plan
                )
                self.design_image_warnings.append(
                    f"{SPEECH_TIMELINE_REMINDER_PREFIX} LM refinement returned no editable "
                    "speech words; retained the first Design Plan and added a red Timeline reminder."
                )
                self._finish_design_pipeline(fallback_plan)
                return
            if self.pipeline_stage == "lm_plan" and self.speech_layer_retry_count < 1:
                self.speech_layer_retry_count += 1
                selected = (
                    self.active_design_context or self._selected_design_context()
                ).get("dialogue_language", "Chinese")
                self._start_lm_design(
                    fallback_note=(
                        "EDITABLE SPEECH TRACK CORRECTION: The previous response was rejected. "
                        "Do not describe speech inside Shot prompts. Create every requested "
                        "Dialogue/Voice-over/Lyrics line as a timed text_layers row on an A "
                        f"track in {selected}, with explicit_user_requested=true."
                    )
                )
                return
            # A generic request such as "add suitable dialogue" has no exact
            # user wording to restore. After one LM retry, preserve the visual
            # Design, add a red Timeline reminder and continue to Workspace.
            # Exact time-coded authored lines were validated above and remain
            # blocking if they cannot be recovered.
            plan = reconcile_requested_speech_layer_contract(
                self.pending_requirement, plan
            )
            self.design_image_warnings.append(
                f"{SPEECH_TIMELINE_REMINDER_PREFIX} AI returned no editable speech words after "
                "retry; Workspace Apply remains available and the Timeline is highlighted."
            )
            self.status_label.setText(
                "Speech track missing · continuing with a red Timeline reminder"
            )
        except ValueError as exc:
            self._set_pipeline_busy(False)
            self.design_busy_overlay.stop()
            self.json_edit.setPlainText(str(payload.get("text", "")))
            self._show_preflight_failure(str(exc), category="Design JSON")
            return
        if self.pipeline_stage == "lm_refine" and self.planned_plan:
            refined_images = [
                item for item in plan.get("media_requests") or []
                if item.get("media_type") == "image"
            ]
            image_number = 0
            preserved_media: list[dict] = []
            for original in self.planned_plan.get("media_requests") or []:
                if original.get("media_type") != "image":
                    preserved_media.append(dict(original))
                    continue
                merged = dict(original)
                if image_number < len(refined_images):
                    refined = refined_images[image_number]
                    merged["subject_keywords"] = list(
                        refined.get("subject_keywords") or original.get("subject_keywords") or []
                    )
                    merged["prompt"] = str(refined.get("prompt") or original.get("prompt") or "")
                preserved_media.append(merged)
                image_number += 1
            plan["media_requests"] = preserved_media
            plan["existing_media_uses"] = [
                dict(item) for item in self.planned_plan.get("existing_media_uses") or []
            ]
            plan["duration_seconds"] = self.planned_plan["duration_seconds"]
        self._display_design_plan(plan)
        if self.pipeline_stage == "lm_plan":
            self.planned_plan = plan
            image_count = sum(
                item.get("media_type") == "image" for item in plan.get("media_requests") or []
            )
            if (
                self.generate_images_check.isChecked()
                and image_count
                and Z_IMAGE_WORKFLOW.is_file()
                and self.image_checkpoint_combo.currentText().strip()
                and str(self.context.get("comfyui_server", "")).strip()
            ):
                if (
                    self.provider_combo.currentData() == "lm_studio"
                    and self.runner.is_running()
                ):
                    self.pipeline_stage = "release_lm_for_images"
                    self._set_design_stage(
                        "Stage 1/4 · plan ready · releasing LM Studio before Z-Image…"
                    )
                    self._request_lm_unload()
                else:
                    self._start_plan_images(plan)
            else:
                self._finish_design_pipeline(plan)
            return
        self._finish_design_pipeline(plan)

    def test_connection(self) -> None:
        self._submit("test")

    def refresh_checkpoints(self) -> None:
        server = str(self.context.get("comfyui_server", "")).strip()
        if not server:
            self.status_label.setText("No ComfyUI server URL is available from the workspace")
            return
        self._submit("comfy_zimage_models", {"base_url": server})

    def generate_design(self) -> None:
        requirement = self.requirement_edit.toPlainText().strip()
        if not requirement:
            self._show_preflight_failure(
                "Describe the video you want to create.", category="Design requirement"
            )
            return
        if not self.model_combo.currentText().strip():
            self._show_preflight_failure(
                "Enter or select a model name first.", category="AI model"
            )
            return
        self.refresh_media_inventory()
        if not self._select_explicit_media_references(requirement):
            return
        self.active_design_context = self._selected_design_context()
        requested_duration = infer_explicit_design_duration(requirement)
        if requested_duration is not None:
            self.active_design_context["requested_duration_seconds"] = requested_duration
        self._persist_settings()
        self.validated_plan = None
        self.pending_requirement = requirement
        self.required_text_layers = extract_explicit_timed_text_layers(requirement)
        self.duration_contract_retry_count = 0
        self.dialogue_language_retry_count = 0
        self.speech_layer_retry_count = 0
        self.design_json_retry_count = 0
        self.planned_plan = None
        self.generated_references = []
        self.design_image_warnings = []
        self.concept_blip_jobs.clear()
        self.pending_refinement_prompt = ""
        self._set_pipeline_busy(True)
        self.concept_preview_frame.hide()
        self.concept_image_path = None
        self.concept_blip_caption = ""
        self._start_lm_design()

    def _select_design_dialogue_mode(self, engine: str) -> None:
        if engine not in {
            "h3_native", "voxcpm2_local", "qwen3_tts_local", "edge_tts"
        }:
            return
        self.design_tts_engine = engine
        button = self.dialogue_mode_buttons.get(engine)
        if button and not button.isChecked():
            button.setChecked(True)
        self._refresh_design_voxcpm_model_status()
        self._invalidate_json()

    def _dialogue_language_changed(self, _index: int) -> None:
        resolved = infer_design_dialogue_language(
            self.requirement_edit.toPlainText().strip(),
            self.dialogue_language_combo.currentData(),
        )
        self.dialogue_language_combo.setToolTip(
            "H3 stable dialogue language. Current resolved language: " + resolved
        )
        self._invalidate_json()

    def _refresh_subtitles_button(self) -> None:
        enabled = self.subtitles_button.isChecked()
        self.subtitles_button.setText("SUB ON" if enabled else "SUB OFF")
        self.subtitles_button.setStyleSheet(
            "background:#155e75; border:1px solid #55cfdf;" if enabled else ""
        )

    def _subtitles_toggled(self, _checked: bool) -> None:
        self._refresh_subtitles_button()
        self._invalidate_json()

    def _music_mode_changed(self, _index: int) -> None:
        self.music_mode_combo.setToolTip({
            "off": (
                "MUSIC OFF: H3 receives no non-diegetic score; only dialogue, ambience and Foley."
            ),
            "auto": (
                "MUSIC AUTO: Qwen plans scene-appropriate instrumentation and dramatic development; "
                "H3 generates it natively and keeps it below dialogue."
            ),
            "timeline": (
                "MUSIC TIMELINE: H3 receives music only where a Timeline Music Cue is active."
            ),
        }[normalize_design_music_mode(self.music_mode_combo.currentData())])
        self._invalidate_json()

    def _refresh_design_voxcpm_model_status(self) -> None:
        missing = voxcpm_model_missing()
        button = self.dialogue_mode_buttons.get("voxcpm2_local")
        if button is not None:
            if missing:
                button.setStyleSheet(
                    "background:#6b321f; border:1px solid #ffad42; "
                    "color:#fff2dc; font-weight:700;"
                )
                button.setToolTip(
                    "VoxCPM2 MODEL MISSING · download openbmb/VoxCPM2 to "
                    + str(VOXCPM_MODEL_DIR)
                )
            else:
                button.setStyleSheet("")
                button.setToolTip(
                    "VoxCPM2 Local · model ready in " + str(VOXCPM_MODEL_DIR)
                )
        qwen_runtime_missing = qwen3_tts_runtime_missing()
        qwen_support_missing = qwen3_tts_support_missing()
        qwen_model_missing = qwen3_tts_model_missing()
        qwen_missing = [
            *(f"runtime/{item}" for item in qwen_runtime_missing),
            *(f"support/{item}" for item in qwen_support_missing),
            *(f"model/{item}" for item in qwen_model_missing),
        ]
        qwen_button = self.dialogue_mode_buttons.get("qwen3_tts_local")
        if qwen_button is not None:
            if qwen_missing:
                qwen_button.setStyleSheet(
                    "background:#6b321f; border:1px solid #ffad42; "
                    "color:#fff2dc; font-weight:700;"
                )
                qwen_button.setToolTip(
                    "QWEN3-TTS MISSING · runtime: "
                    + str(QWEN3_TTS_RUNTIME_DIR)
                    + " · model: "
                    + str(QWEN3_TTS_MODEL_DIR)
                )
            else:
                qwen_button.setStyleSheet("")
                qwen_button.setToolTip(
                    "Qwen3-TTS Local · model ready in " + str(QWEN3_TTS_MODEL_DIR)
                )
        selected_missing = (
            (bool(missing) and self.design_tts_engine == "voxcpm2_local")
            or (bool(qwen_missing) and self.design_tts_engine == "qwen3_tts_local")
        )
        self.dialogue_model_warning.setVisible(selected_missing)
        if selected_missing and self.design_tts_engine == "voxcpm2_local":
            self.dialogue_model_warning.setText(
                "⚠ VOXCPM2 MODEL MISSING · Download openbmb/VoxCPM2 to "
                f"{VOXCPM_MODEL_DIR}\nMissing: {', '.join(missing)}"
            )
            self.dialogue_model_warning.setStyleSheet(
                "background:#4a251a; color:#ffd28b; border:1px solid #ff9d38; "
                "padding:5px; font-weight:700;"
            )
        elif selected_missing:
            self.dialogue_model_warning.setText(
                "⚠ QWEN3-TTS MISSING · Run install_qwen3_tts_runtime.bat and "
                "download Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice to "
                f"{QWEN3_TTS_MODEL_DIR}\nMissing: {', '.join(qwen_missing)}"
            )
            self.dialogue_model_warning.setStyleSheet(
                "background:#4a251a; color:#ffd28b; border:1px solid #ff9d38; "
                "padding:5px; font-weight:700;"
            )

    def _service_message(self, payload: dict) -> None:
        if payload.get("ready"):
            return
        resolved_model = str(payload.get("resolved_model", "")).strip()
        if (
            resolved_model
            and self.provider_combo.currentData() == "lm_studio"
            and self.model_combo.currentText().strip() != resolved_model
        ):
            self.model_combo.setCurrentText(resolved_model)
            self.settings.lm_studio_model = resolved_model
            save_design_settings(DESIGN_SETTINGS_ENV, self.settings)
        if payload.get("zimage_models") is not None:
            self._set_pipeline_busy(False)
            models = [str(item) for item in payload.get("zimage_models") or []]
            current = self.image_checkpoint_combo.currentText().strip()
            preferred = "z_image_turbo_bf16.safetensors"
            self.image_checkpoint_combo.clear()
            self.image_checkpoint_combo.addItems(models)
            if current in models:
                self.image_checkpoint_combo.setCurrentText(current)
            elif preferred in models:
                self.image_checkpoint_combo.setCurrentText(preferred)
            elif models:
                self.image_checkpoint_combo.setCurrentIndex(0)
            self.status_label.setText(
                f"ComfyUI · {len(models)} Z-Image-compatible UNET model(s) available"
            )
            return
        if payload.get("generated"):
            self._handle_design_generated(payload)
            return
        if payload.get("comfy_unloaded"):
            self._set_design_stage(
                "Stage 4/4 · Z-Image memory released · preparing LM Studio refinement…"
            )
            QTimer.singleShot(1200, self._begin_lm_refinement)
            return
        if payload.get("lm_unloaded") is not None:
            count = len(payload.get("lm_unloaded") or [])
            if self.pipeline_stage == "release_lm_for_images" and self.planned_plan:
                self._set_design_stage(
                    f"Stage 1/4 · LM Studio released ({count}) · starting Z-Image…"
                )
                self._start_plan_images(self.planned_plan)
                return
            self.status_label.setText(
                f"Director Design JSON ready · LM Studio model released ({count} instance(s))"
            )
            return
        if payload.get("error"):
            if str(payload.get("job", "")).startswith("design-comfy-unload:"):
                self.design_image_warnings.append(
                    "ComfyUI model unload failed before refinement: " + str(payload["error"])
                )
                self._set_design_stage(
                    "Stage 4/4 · model release warning · continuing LM refinement with 900s timeout"
                )
                self._begin_lm_refinement()
                return
            if str(payload.get("job", "")).startswith("design-unload:"):
                if self.pipeline_stage == "release_lm_for_images" and self.planned_plan:
                    self.design_image_warnings.append(
                        "LM Studio unload failed before Z-Image: " + str(payload["error"])
                    )
                    self._set_design_stage(
                        "Stage 2/4 · LM release warning · continuing Z-Image generation"
                    )
                    self._start_plan_images(self.planned_plan)
                    return
                self.status_label.setText(
                    "Director Design JSON ready · LM Studio unload warning: "
                    + str(payload["error"])
                )
                return
            self.design_busy_overlay.stop()
            self._set_pipeline_busy(False)
            self._show_preflight_failure(
                str(payload["error"]), category="AI Design service"
            )
            return
        if payload.get("connected"):
            self._set_pipeline_busy(False)
            models = payload.get("models") or []
            current = self.model_combo.currentText().strip()
            resolved = str(payload.get("resolved_model", "")).strip()
            self.model_combo.clear()
            self.model_combo.addItems(models)
            if current in models:
                self.model_combo.setCurrentText(current)
            elif resolved in models:
                self.model_combo.setCurrentText(resolved)
            elif models:
                self.model_combo.setCurrentIndex(0)
            selected = self.model_combo.currentText().strip()
            if self.provider_combo.currentData() == "lm_studio" and selected:
                self.settings.lm_studio_model = selected
                save_design_settings(DESIGN_SETTINGS_ENV, self.settings)
            if payload.get("model_replaced") and selected:
                self.status_label.setText(
                    f"Connected: saved model was unavailable; switched to {selected}"
                )
                return
            self.status_label.setText(f"Connected · {len(models)} model(s) discovered")
            return
        if payload.get("checkpoints") is not None:
            self._set_pipeline_busy(False)
            checkpoints = [str(item) for item in payload.get("checkpoints") or []]
            current = self.image_checkpoint_combo.currentText().strip()
            self.image_checkpoint_combo.clear()
            self.image_checkpoint_combo.addItems(checkpoints)
            if current:
                self.image_checkpoint_combo.setCurrentText(current)
            elif checkpoints:
                self.image_checkpoint_combo.setCurrentIndex(0)
            self.status_label.setText(
                f"ComfyUI · {len(checkpoints)} image-generation checkpoint(s) available"
            )
            return
        if payload.get("generated"):
            self._set_pipeline_busy(False)
            try:
                plan = normalize_design_plan(
                    payload.get("text", ""),
                    self.capacities,
                    existing_media=(
                        self.active_design_context or self._selected_design_context()
                    ).get("existing_media") or [],
                    strict_t2i_prompts=True,
                    repair_media_plan=True,
                    authored_requirement=self.pending_requirement,
                    special_skill_key=_bound_special_skill_key(
                        self.active_design_context or self._selected_design_context()
                    ),
                    selected_media_ids=(
                        self.active_design_context or self._selected_design_context()
                    ).get("selected_existing_media_ids"),
                )
            except ValueError as exc:
                self.json_edit.setPlainText(str(payload.get("text", "")))
                self._show_preflight_failure(str(exc), category="Design JSON")
                return
            self.json_edit.blockSignals(True)
            self.json_edit.setPlainText(json.dumps(plan, ensure_ascii=False, indent=2))
            self.json_edit.blockSignals(False)
            self.validated_plan = plan
            self._show_summary(plan)
            self.apply_button.setEnabled(True)
            self.status_label.setText("Director Design JSON ready · review or Apply")

            if self.provider_combo.currentData() == "lm_studio" and self.runner.is_running():
                self.runner.write_json({
                    "job": f"design-unload:{time.time_ns()}",
                    "action": "unload_lm",
                    "provider": "lm_studio",
                    "base_url": self.base_url_edit.text().strip(),
                    "model": self.model_combo.currentText().strip(),
                    "timeout": min(120, self.timeout_spin.value()),
                })
            return
        if payload.get("lm_unloaded") is not None:
            count = len(payload.get("lm_unloaded") or [])
            self.status_label.setText(
                f"Director Design JSON ready · LM Studio model released ({count} instance(s))"
            )

    def _service_finished(self, exit_code: int, log: str) -> None:
        self.test_button.setEnabled(True)
        self.generate_button.setEnabled(True)
        self.refresh_checkpoints_button.setEnabled(True)
        if exit_code and self.isVisible():
            self.design_busy_overlay.stop()
            self.status_label.setText(f"AI design service stopped: {log[-300:]}")

    def _invalidate_json(self) -> None:
        self.validated_plan = None
        self.apply_preflight_blockers = []
        self.apply_preflight_warnings = []
        self.apply_button.setEnabled(False)

    @staticmethod
    def _preflight_lines(
        *,
        repairs: list[str] | None = None,
        warnings: list[str] | None = None,
        blockers: list[str] | None = None,
    ) -> list[str]:
        repairs = [str(item) for item in repairs or [] if str(item).strip()]
        warnings = [str(item) for item in warnings or [] if str(item).strip()]
        blockers = [str(item) for item in blockers or [] if str(item).strip()]
        lines = [
            "APPLY PREFLIGHT REPORT",
            "STATUS: " + ("HARD BLOCK" if blockers else "READY"),
            f"AUTO-FIX: {len(repairs)} · WARNING: {len(warnings)} · HARD BLOCK: {len(blockers)}",
        ]
        if repairs:
            lines.extend(["", "AUTO-FIXED", *(f"  ✓ {item}" for item in repairs)])
        if warnings:
            lines.extend(["", "WARNINGS · Apply remains available", *(f"  ⚠ {item}" for item in warnings)])
        if blockers:
            lines.extend(["", "HARD BLOCKERS · correct these before Apply", *(f"  ✕ {item}" for item in blockers)])
        return lines

    def _show_preflight_failure(self, message: str, *, category: str = "Validation") -> None:
        self.apply_in_progress = False
        self.design_busy_overlay.stop()
        self._set_pipeline_busy(False)
        self.apply_preflight_blockers = [f"{category}: {message}"]
        self.summary_edit.setPlainText("\n".join(self._preflight_lines(
            blockers=self.apply_preflight_blockers,
        )))
        self.apply_button.setEnabled(False)
        self.status_label.setText(
            "Apply stopped by one actionable Hard Block · Design remains open"
        )

    def mark_apply_failed(self, message: str, *, category: str = "Workspace") -> None:
        """Return an unsuccessful downstream Apply to the editable Design page."""

        self._show_preflight_failure(message, category=category)
        self.apply_button.setEnabled(self.validated_plan is not None)

    def mark_apply_succeeded(self, warnings: list[str] | None = None) -> None:
        """Close only after the Timeline/Workspace commit is actually durable."""

        self.apply_in_progress = False
        self.design_busy_overlay.stop()
        if warnings:
            self.apply_preflight_warnings.extend(str(item) for item in warnings)
        self.status_label.setText("Apply complete · H3 Workspace committed")
        self.concept_preview_frame.hide()
        self.concept_thumbnail.clear()
        self.concept_caption_label.clear()
        self.generated_references.clear()
        self.concept_blip_jobs.clear()
        self.accept()

    def load_design_json(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Director Design JSON",
            str(DESIGN_EXAMPLE_ROOT),
            "Director Design JSON (*.json);;JSON (*.json)",
        )
        if not filename:
            return
        try:
            text = Path(filename).read_text(encoding="utf-8-sig")
        except OSError as exc:
            self._show_preflight_failure(str(exc), category="Load Design JSON")
            return
        self.generated_references = []
        self.design_image_warnings = []
        self.planned_plan = None
        self.json_edit.setPlainText(text)
        if self.validate_json():
            self.status_label.setText(
                f"Loaded and validated · {Path(filename).name} · Apply when ready"
            )

    def validate_json(self) -> bool:
        preflight_warnings: list[str] = []
        try:
            context = self._selected_design_context()
            requirement = (
                self.pending_requirement
                or self.requirement_edit.toPlainText().strip()
            )
            blockers = collect_design_preflight_blockers(
                self.json_edit.toPlainText(),
                self.capacities,
                existing_media=self.context.get("existing_media") or [],
                authored_requirement=requirement,
                selected_media_ids=context.get("selected_existing_media_ids") or [],
            )
            if blockers:
                self.apply_in_progress = False
                self.design_busy_overlay.stop()
                self._set_pipeline_busy(False)
                self.apply_preflight_blockers = blockers
                self.summary_edit.setPlainText("\n".join(self._preflight_lines(
                    blockers=blockers,
                )))
                self.apply_button.setEnabled(False)
                self.status_label.setText(
                    f"Apply Preflight found {len(blockers)} Hard Block(s) · Design remains open"
                )
                return False
            plan = normalize_design_plan(
                self.json_edit.toPlainText(),
                self.capacities,
                existing_media=context.get("existing_media") or [],
                repair_media_plan=True,
                authored_requirement=requirement,
                special_skill_key=_bound_special_skill_key(context),
                selected_media_ids=context.get("selected_existing_media_ids"),
            )
            plan = protect_explicit_timed_text_layers(plan, requirement)
            validate_explicit_timed_text_contract(requirement, plan)
            try:
                plan = enforce_design_dialogue_language(
                    plan,
                    context.get("dialogue_language", ""),
                    authored_requirement=requirement,
                )
            except DesignDialogueLanguageContractError as exc:
                preflight_warnings.append(
                    "Dialogue language could not be deterministically rewritten locally; "
                    "the editable Text Layers were preserved for correction. " + str(exc)
                )
            plan = enforce_design_subtitle_policy(
                plan,
                context.get("subtitles_enabled", False),
                authored_requirement=requirement,
            )
            plan = enforce_design_music_mode(
                plan, context.get("music_mode", "auto")
            )
            plan = reconcile_requested_speech_layer_contract(requirement, plan)
            selected_ids = {
                str(item).upper()
                for item in context.get("selected_existing_media_ids") or []
            }
            planned_ids = {
                str(item.get("media_id", "")).upper()
                for item in plan.get("existing_media_uses") or []
            }
            unselected = sorted(planned_ids.difference(selected_ids))
            if unselected:
                explicit_ids = self._explicit_media_ids(requirement)
                missing_explicit = sorted(set(unselected).intersection(explicit_ids))
                if missing_explicit:
                    raise ValueError(
                        "Explicit Media Pool references are not enabled: "
                        + ", ".join("@" + item for item in missing_explicit)
                    )
                plan["existing_media_uses"] = [
                    item for item in plan.get("existing_media_uses") or []
                    if str(item.get("media_id", "")).upper() not in unselected
                ]
                preflight_warnings.append(
                    "Removed model-selected Media Pool references that were not enabled: "
                    + ", ".join("@" + item for item in unselected)
                )
        except ValueError as exc:
            self._show_preflight_failure(str(exc))
            return False
        plan.setdefault("design_warnings", []).extend(preflight_warnings)
        if (
            self.design_tts_engine == "voxcpm2_local"
            and voxcpm_model_missing()
            and any(
                str(item.get("role", "")).strip().lower()
                in {"dialogue", "voice_over", "lyrics"}
                for item in plan.get("text_layers") or []
            )
        ):
            plan["design_warnings"].append(
                "VoxCPM2 model is missing. Apply will preserve editable speech Text Layers, "
                "defer WAV generation and highlight dialogue as pending instead of stopping."
            )
        if (
            self.design_tts_engine == "qwen3_tts_local"
            and (
                qwen3_tts_runtime_missing()
                or qwen3_tts_support_missing()
                or qwen3_tts_model_missing()
            )
            and any(
                str(item.get("role", "")).strip().lower()
                in {"dialogue", "voice_over", "lyrics"}
                for item in plan.get("text_layers") or []
            )
        ):
            plan["design_warnings"].append(
                "Qwen3-TTS runtime/model is missing. Apply will preserve editable speech "
                "Text Layers, defer WAV generation and highlight dialogue as pending."
            )
        self.validated_plan = plan
        self.apply_preflight_blockers = []
        self.apply_preflight_warnings = preflight_warnings
        self._show_summary(plan)
        self.apply_button.setEnabled(True)
        return True

    def _show_summary(self, plan: dict) -> None:
        counts = {kind: 0 for kind in ("image", "video", "audio")}
        for request in plan["media_requests"]:
            counts[request["media_type"]] += 1
        reused = {kind: 0 for kind in ("image", "video", "audio")}
        reused_ids: list[str] = []
        analysis_only_ids: list[str] = []
        for use in plan.get("existing_media_uses") or []:
            if is_analysis_only_media_use(use):
                analysis_only_ids.append(str(use.get("media_id", "")))
                continue
            media_type = str(use.get("media_type", ""))
            if media_type in reused:
                reused[media_type] += 1
            reused_ids.append(str(use.get("media_id", "")))
        budget_statuses = {
            "within_budget": 0,
            "optional_trimmed": 0,
            "priority_compressed": 0,
        }
        for shot in plan.get("shots") or []:
            status = str((shot.get("action_budget") or {}).get("status", "within_budget"))
            budget_statuses[status] = budget_statuses.get(status, 0) + 1
        budget_warnings = [
            str(item) for item in plan.get("design_warnings") or [] if str(item).strip()
        ]
        auto_fix_prefixes = (
            "Auto-", "Inserted ", "Rebuilt ", "Renamed ", "Added ",
        )
        repairs = [
            warning for warning in budget_warnings
            if warning.startswith(auto_fix_prefixes)
        ]
        warnings = [
            warning for warning in budget_warnings
            if warning not in repairs
        ]
        self.summary_edit.setPlainText(
            "\n".join((
                *self._preflight_lines(
                    repairs=repairs,
                    warnings=warnings,
                    blockers=self.apply_preflight_blockers,
                ),
                "",
                "PLAN SUMMARY",
                f"TITLE: {plan['title']}",
                f"DURATION: {plan['duration_seconds']:.2f}s",
                f"SHOTS: {len(plan['shots'])}",
                f"TEXT / DIALOGUE: {len(plan['text_layers'])}",
                f"TRANSITIONS: {len(plan['transitions'])}",
                f"MARKERS: {len(plan['markers'])}",
                "MEDIA POOL REUSE: " + (", ".join(reused_ids) if reused_ids else "none"),
                "ANALYSIS-ONLY CONTROL: " + (
                    ", ".join(analysis_only_ids) if analysis_only_ids else "none"
                ),
                f"REUSED: {reused['image']} image / {reused['video']} video / {reused['audio']} audio",
                f"TO GENERATE: {counts['image']} image / {counts['video']} video / {counts['audio']} audio",
                (
                    "ACTION BUDGET: "
                    f"{budget_statuses.get('within_budget', 0)} within / "
                    f"{budget_statuses.get('optional_trimmed', 0)} optional trimmed / "
                    f"{budget_statuses.get('priority_compressed', 0)} priority compressed"
                ),
                f"MEDIA: {counts['image']} image · {counts['video']} video · {counts['audio']} audio",
                "",
                "LM Studio reuses matching Media Pool intelligence first; Z-Image creates only missing requests.",
            ))
        )

    def apply_design(self) -> None:
        if self.validated_plan is None and not self.validate_json():
            return
        plan = dict(self.validated_plan)
        requirement = (
            self.pending_requirement
            or self.requirement_edit.toPlainText().strip()
        )
        try:
            validate_explicit_timed_text_contract(requirement, plan)
        except ValueError as exc:
            self._show_preflight_failure(str(exc), category="Authored text")
            return
        plan = reconcile_requested_speech_layer_contract(requirement, plan)
        plan["_authored_requirement"] = requirement
        plan["_dialogue_tts_engine"] = self.design_tts_engine
        plan["_dialogue_language"] = infer_design_dialogue_language(
            requirement,
            self.dialogue_language_combo.currentData(),
        )
        plan["_subtitles_enabled"] = self.subtitles_button.isChecked()
        plan["_music_mode"] = normalize_design_music_mode(
            self.music_mode_combo.currentData()
        )
        plan["_required_text_layers"] = authored_text_layers_with_plan_assignments(
            requirement,
            plan,
            float(plan.get("duration_seconds", 0.0) or 0.0) or None,
        )
        plan["_design_images_pre_generated"] = bool(self.generated_references)
        plan["_generated_references"] = [dict(item) for item in self.generated_references]
        plan["_design_image_warnings"] = list(self.design_image_warnings)
        cleanup = {
            "provider": self.provider_combo.currentData(),
            "base_url": self.base_url_edit.text().strip(),
            "model": self.model_combo.currentText().strip(),
            "comfyui_server": str(self.context.get("comfyui_server", "")).strip(),
            "timeout": min(120, self.timeout_spin.value()),
        }
        self.apply_in_progress = True
        self._set_pipeline_busy(True)
        self.design_busy_overlay.start(
            "Apply preflight passed · committing Timeline and Workspace…"
        )
        self.status_label.setText(
            "Apply preflight passed · waiting for durable Workspace commit"
        )
        self.cleanup_requested.emit(cleanup)
        self.apply_requested.emit(plan, self.replace_check.isChecked())

    def closeEvent(self, event) -> None:  # noqa: N802
        self._persist_settings()
        self.design_busy_overlay.stop()
        self.concept_media_runner.stop()
        self.concept_blip_runner.stop()
        self.runner.stop()
        super().closeEvent(event)


class DirectorCutStudio(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.runtime = load_runtime_paths()
        self.render_settings = load_settings(SETTINGS_ENV)
        self.profiles = load_skill_profiles(PROJECT_ROOT)
        self.scan: WorkflowScan | None = None
        self.selected_asset: MediaAsset | None = None
        self.selected_timeline_asset: MediaAsset | None = None
        self.selected_track: TimelineTrack | None = None
        self.tracks = default_timeline_tracks()
        self.text_layers: list[TextLayer] = []
        self.director_cues: list[DirectorCue] = []
        self._pending_track_color = "#3978ba"
        self.cards: dict[str, MediaCard] = {}
        self.media_card_order: list[MediaCard] = []
        self.preview_paths: dict[str, Path] = {}
        self.monitor_source_pixmaps: dict[str, QPixmap] = {}
        self.media_jobs: dict[str, dict] = {}
        self.media_runner = JsonLineProcess(self, "media-prepare")
        self.media_runner.message.connect(self._handle_media_prepare_payload)
        self.media_runner.finished.connect(self._media_prepare_service_finished)
        self.blip_jobs: dict[str, tuple[MediaAsset, str, Path, str]] = {}
        self.blip_results: dict[str, list[dict[str, str]]] = {}
        self.analysis_paths: dict[str, list[tuple[str, Path]]] = {}
        self.blip_runner = JsonLineProcess(self, "blip")
        self.blip_runner.message.connect(self._handle_blip_payload)
        self.blip_runner.finished.connect(self._blip_service_finished)
        self.blip_cpu_fallback_attempted = False
        self.blip_cpu_mode = self.render_settings.blip_device == "cpu"
        self.blip_restart_after_jobs = False
        self.audio_jobs: dict[str, MediaAsset] = {}
        self.native_audio_qc_jobs: dict[str, dict] = {}
        self.audio_runner = JsonLineProcess(self, "audio")
        self.audio_runner.message.connect(self._handle_audio_payload)
        self.audio_runner.finished.connect(self._audio_service_finished)
        self.semantic_jobs: dict[str, dict] = {}
        self.semantic_errors: dict[str, str] = {}
        self.semantic_waiting_assets: set[str] = set()
        self.semantic_unload_job_id = ""
        self.semantic_last_lm_request: dict = {}
        self.semantic_runner = JsonLineProcess(self, "media-semantic-enrichment")
        self.semantic_runner.message.connect(self._handle_semantic_payload)
        self.semantic_runner.finished.connect(self._semantic_service_finished)
        self.smart_cut_runner = JsonLineProcess(self, "smart-cut-semantic")
        self.smart_cut_runner.message.connect(self._handle_smart_cut_payload)
        self.smart_cut_runner.finished.connect(self._smart_cut_service_finished)
        self.smart_cut_job_id = ""
        self.smart_cut_unload_job_id = ""
        self.smart_cut_active_request: dict = {}
        self.smart_cut_dialog: SmartCutDialog | None = None
        self.smart_cut_last_plan: dict = {}
        self.design_ai_settings = load_design_settings(DESIGN_SETTINGS_ENV)
        # API keys remain memory-only for the lifetime of this Studio window.
        self.semantic_openai_api_key = ""
        self._closing = False
        self._timed_out_generations: set[tuple[str, int]] = set()
        self.worker_watchdog = QTimer(self)
        self.worker_watchdog.setInterval(2000)
        self.worker_watchdog.timeout.connect(self._watch_worker_health)
        self.worker_watchdog.start()
        self.submit_runner: JsonLineProcess | None = None
        self.submit_result: dict = {}
        self.submit_request_kind = "final"
        self.design_media_runner: JsonLineProcess | None = None
        self.design_media_result: dict = {}
        self.pending_ai_design: dict | None = None
        self.media_regeneration_runner: JsonLineProcess | None = None
        self.media_regeneration_result: dict = {}
        self.pending_media_regeneration: dict | None = None
        self.design_tts_runner: JsonLineProcess | None = None
        self.design_tts_result: dict = {}
        self.pending_design_tts: dict | None = None
        self.active_design_apply_dialog: DesignPageDialog | None = None
        self.pending_generation_after_tts: dict | None = None
        self.timeline_tts_stale = False
        self.timeline_tts_refresh_timer = QTimer(self)
        self.timeline_tts_refresh_timer.setSingleShot(True)
        self.timeline_tts_refresh_timer.setInterval(450)
        self.timeline_tts_refresh_timer.timeout.connect(
            self._regenerate_timeline_tts_if_needed
        )
        self.design_cleanup_runner: JsonLineProcess | None = None
        self.design_cleanup_result: dict = {}
        self.preview_seed: int | None = None
        self.preview_ready = False
        # Long productions can remain a normal one-shot Work Area render or
        # advance through explicit approval horizons.  Incremental mode only
        # previews the new batch; Accept then assembles a cumulative master so
        # previously approved Segment outputs remain cache-reusable.
        self.production_strategy = "full_range"
        self.production_batch_seconds = 30.0
        self.incremental_approved_horizon = 0.0
        self.incremental_pending_start = 0.0
        self.incremental_pending_end = 0.0
        self.incremental_batch_phase = ""
        self.quality_profile = "approved_final"
        self.shot_take_states: dict[str, dict] = {}
        self.segment_take_states: dict[str, dict] = {}
        self.active_generation_started_at = 0.0
        self.active_generation_profile = ""
        self.active_generation_duration_seconds = 0.0
        self.active_generation_job_path: Path | None = None
        self.smart_render_manifest: dict = {}
        self.smart_render_manifests: dict[str, dict] = {}
        self.render_dirty_segment_ids: set[str] = set()
        self.render_runtime_status: dict[str, str] = {}
        self.generated_output_path: Path | None = None
        self.generated_playback_path: Path | None = None
        self.generated_output_locked = False
        self.storyboard_preview_active = False
        self.storyboard_trim_active = False
        self.storyboard_target_duration_seconds = 45.0
        self.storyboard_view_mode = "large_icons"
        self.generated_output_timeline_start = 0.0
        self.generated_pending_position_ms = 0
        self._syncing_generated_position = False
        self.generated_proxy_runner: JsonLineProcess | None = None
        self.generated_proxy_source: Path | None = None
        self.generated_proxy_target: Path | None = None
        self.generated_proxy_working: Path | None = None
        self.generated_proxy_autoplay_pending = False
        self.example_work_dir: Path | None = None
        self.project_workspace_id = ""
        self.legacy_project_source: Path | None = None
        self.generation_previous_monitor: QWidget | None = None
        self.connection_runner: JsonLineProcess | None = None
        self.connection_result: dict = {}
        self.undo_stack = QUndoStack(self)
        self.project_path: Path | None = None
        self.project_dirty = False
        self.restoring_project = False
        self.prompt_sync_in_progress = False
        self.prompt_generation_timer = QTimer(self)
        self.prompt_generation_timer.setSingleShot(True)
        self.prompt_generation_timer.setInterval(180)
        self.prompt_generation_timer.timeout.connect(
            lambda: self.generate_prompt(interactive=False)
        )
        self.playhead_seconds = 0.0
        self.timeline_playing = False
        self.playback_anchor_time = 0.0
        self.playback_anchor_seconds = 0.0
        self.current_visual_node = ""
        self.pending_video_position_ms = 0
        self.timeline_audio_players: dict[str, QMediaPlayer] = {}
        self.timeline_audio_outputs: dict[str, QAudioOutput] = {}
        self.pending_audio_positions: dict[str, int] = {}
        self.composite_video_players: dict[str, QMediaPlayer] = {}
        self.composite_video_sinks: dict[str, QVideoSink] = {}
        self.composite_video_frames: dict[str, QImage] = {}
        self.composite_visuals: list[MediaAsset] = []
        self.audio_pan_proxies: dict[str, Path] = {}
        self.audio_pan_pending: set[str] = set()
        self.timeline_timer = QTimer(self)
        self.timeline_timer.setInterval(33)
        self.timeline_timer.timeout.connect(self._timeline_tick)
        self.timeline_slider_scrubbing = False
        self.timeline_slider_was_playing = False
        self.timeline_slider_pending_seconds = 0.0
        self.timeline_slider_seek_timer = QTimer(self)
        self.timeline_slider_seek_timer.setSingleShot(True)
        self.timeline_slider_seek_timer.setInterval(45)
        self.timeline_slider_seek_timer.timeout.connect(self._apply_timeline_slider_seek)
        CACHE_ROOT.mkdir(exist_ok=True)
        self.setWindowTitle(f"MiniMax H3 Director Cut Studio v{APP_VERSION}")
        self.resize(1680, 980)
        self.setMinimumSize(1180, 720)
        self._build_toolbar()
        self._build_workspace()
        self.statusBar().showMessage("Director Cut runtime ready")
        if LATEST_WORKFLOW.exists():
            self.load_workflow_path(LATEST_WORKFLOW)
        self._connect_dirty_signals()

    def _build_toolbar(self) -> None:
        bar = QToolBar("Director Controls")
        bar.setMovable(False)
        self.addToolBar(bar)
        open_button = QPushButton("OPEN API WORKFLOW")
        open_button.clicked.connect(self.choose_workflow)
        bar.addWidget(open_button)
        self.design_button = QPushButton("DESIGN")
        self.design_button.setObjectName("designButton")
        self.design_button.setToolTip("Open AI Design · turn a concept into H3 timeline JSON")
        self.design_button.setStyleSheet("background:#563d86; font-weight:700;")
        self.design_button.clicked.connect(self.open_design_page)
        bar.addWidget(self.design_button)
        new_project_button = QPushButton("NEW PROJECT")
        new_project_button.clicked.connect(self.new_project)
        bar.addWidget(new_project_button)
        open_project = QPushButton("OPEN PROJECT")
        open_project.clicked.connect(self.open_project)
        bar.addWidget(open_project)
        save_project = QPushButton("SAVE PROJECT")
        save_project.clicked.connect(self.save_project)
        bar.addWidget(save_project)
        self.project_storage_button = QPushButton("STORAGE")
        self.project_storage_button.setToolTip(
            "Project Storage Report · verified Safe Cleanup · portable Archive Project"
        )
        self.project_storage_button.clicked.connect(self.open_project_storage)
        bar.addWidget(self.project_storage_button)
        undo_action = self.undo_stack.createUndoAction(self, "UNDO")
        undo_action.setShortcut(QKeySequence.Undo)
        redo_action = self.undo_stack.createRedoAction(self, "REDO")
        redo_action.setShortcut(QKeySequence.Redo)
        bar.addAction(undo_action)
        bar.addAction(redo_action)
        bar.addSeparator()
        self.default_skill_label = QLabel("Default Skill")
        bar.addWidget(self.default_skill_label)
        self.default_skill_combo = QComboBox()
        self.default_skill_combo.addItem(self.profiles[DEFAULT_SKILL].display_name, DEFAULT_SKILL)
        self.default_skill_combo.setEnabled(False)
        self.default_skill_combo.setMinimumWidth(180)
        bar.addWidget(self.default_skill_combo)
        self.special_skill_label = QLabel("+ Special")
        bar.addWidget(self.special_skill_label)
        self.special_combo = QComboBox()
        self.special_combo.addItem("None", NONE_SPECIAL)
        for key, profile in sorted(self.profiles.items()):
            if profile.special:
                self.special_combo.addItem(profile.display_name, key)
        self.special_combo.setMinimumWidth(240)
        bar.addWidget(self.special_combo)
        self.special_skill_creator_button = QPushButton("SPECIAL SKILL CREATOR")
        self.special_skill_creator_button.setObjectName("specialSkillCreatorButton")
        self.special_skill_creator_button.setToolTip(
            "Create or edit a Studio Special Skill, its Chinese version and binding mode"
        )
        self.special_skill_creator_button.clicked.connect(self.open_special_skill_creator)
        bar.addWidget(self.special_skill_creator_button)
        generation_bar = QToolBar("Generation Controls")
        generation_bar.setObjectName("generationToolbar")
        self.generation_toolbar = generation_bar
        generation_bar.setMovable(False)
        generation_bar.setStyleSheet(
            "QToolBar { spacing:3px; padding:3px 5px; }"
        )
        self.addToolBarBreak()
        self.addToolBar(generation_bar)
        self.generation_work_area_label = QLabel("GENERATION WORK AREA")
        self.generation_work_area_label.setFixedWidth(180)
        generation_bar.addWidget(self.generation_work_area_label)
        self.clip_start = CompactSecondsSpinBox()
        self.clip_start.setDecimals(2)
        self.clip_start.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.clip_start.setFixedWidth(70)
        self.clip_start.valueChanged.connect(self.refresh_activation)
        self.clip_end = CompactSecondsSpinBox()
        self.clip_end.setDecimals(2)
        self.clip_end.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.clip_end.setFixedWidth(70)
        self.clip_end.setToolTip(
            "Generation Work Area end. Type or click beyond the current Timeline endpoint "
            "to extend the project; new projects default to 12s."
        )
        self.clip_end.valueChanged.connect(self._generation_work_area_end_changed)
        generation_bar.addWidget(self.clip_start)
        generation_bar.addWidget(QLabel("→"))
        generation_bar.addWidget(self.clip_end)
        generation_bar.addSeparator()
        generation_bar.addWidget(QLabel("ASPECT"))
        self.aspect_ratio_combo = QComboBox()
        self.aspect_ratio_combo.setFixedWidth(68)
        for ratio in ("16:9", "9:16", "1:1", "4:3", "3:4", "21:9"):
            self.aspect_ratio_combo.addItem(ratio, ratio)
        ratio_index = self.aspect_ratio_combo.findData(self.render_settings.aspect_ratio)
        self.aspect_ratio_combo.setCurrentIndex(max(0, ratio_index))
        self.aspect_ratio_combo.setToolTip("Output aspect ratio used by ResolutionSelector")
        self.aspect_ratio_combo.currentIndexChanged.connect(self._aspect_ratio_changed)
        generation_bar.addWidget(self.aspect_ratio_combo)
        generation_bar.addSeparator()
        generation_bar.addWidget(QLabel("MODE"))
        self.production_strategy_combo = QComboBox()
        self.production_strategy_combo.setObjectName("productionStrategyCombo")
        self.production_strategy_combo.addItem("FULL", "full_range")
        self.production_strategy_combo.addItem("BATCH", "incremental")
        self.production_strategy_combo.setFixedWidth(72)
        self.production_strategy_combo.setToolTip(
            "Full Range renders the selected Work Area normally. Incremental previews only "
            "the next batch, then Accept assembles a cumulative master while reusing approved Segments."
        )
        self.production_strategy_combo.currentIndexChanged.connect(
            self._production_strategy_changed
        )
        generation_bar.addWidget(self.production_strategy_combo)
        self.production_batch_spin = QDoubleSpinBox()
        self.production_batch_spin.setObjectName("productionBatchSeconds")
        self.production_batch_spin.setRange(16.0, 600.0)
        self.production_batch_spin.setDecimals(1)
        self.production_batch_spin.setSingleStep(0.5)
        self.production_batch_spin.setSuffix("s")
        self.production_batch_spin.setFixedWidth(55)
        self.production_batch_spin.setValue(self.production_batch_seconds)
        self.production_batch_spin.setToolTip(
            "Target size of each approval batch. Explicit speech is never split at the approval horizon."
        )
        self.production_batch_spin.valueChanged.connect(
            self._production_batch_seconds_changed
        )
        generation_bar.addWidget(self.production_batch_spin)
        self.next_batch_button = QPushButton("NEXT")
        self.next_batch_button.setFixedWidth(60)
        self.next_batch_button.setObjectName("nextProductionBatchButton")
        self.next_batch_button.setToolTip(
            "Preview only the next unapproved range. Accept promotes it into the cumulative final master."
        )
        self.next_batch_button.clicked.connect(self.start_next_incremental_batch)
        generation_bar.addWidget(self.next_batch_button)
        self.production_progress_label = QLabel("0/0s")
        self.production_progress_label.setObjectName("productionProgressLabel")
        self.production_progress_label.setStyleSheet("color:#65d3df; padding:0 3px;")
        self.production_progress_label.setFixedWidth(100)
        generation_bar.addWidget(self.production_progress_label)
        generation_bar.addSeparator()
        # The three quality profiles are direct toolbar actions. Keep this
        # hidden combo as the persisted state model for project compatibility.
        self.quality_profile_combo = QComboBox(self)
        self.quality_profile_combo.setObjectName("qualityProfileCombo")
        for key in ("storyboard", "motion_preview", "approved_final"):
            profile = QUALITY_PROFILES[key]
            self.quality_profile_combo.addItem(profile.label, key)
        self.quality_profile_combo.setCurrentIndex(
            self.quality_profile_combo.findData(self.quality_profile)
        )
        self.quality_profile_combo.setToolTip(
            "Storyboard uses no H3; Motion Preview uses 0.2MP; Approved Final reuses the accepted seed at 1.0MP"
        )
        self.quality_profile_combo.currentIndexChanged.connect(
            self._quality_profile_changed
        )
        self.quality_profile_combo.hide()
        self.export_api_button = QPushButton("EXPORT API")
        self.export_api_button.setFixedWidth(95)
        self.export_api_button.setObjectName("exportApiButton")
        self.export_api_button.setToolTip(
            "Export Active API: save the currently compiled ComfyUI API workflow"
        )
        self.export_api_button.clicked.connect(self.export_active_api)
        generation_bar.addWidget(self.export_api_button)
        self.server_url = QLineEdit(self.render_settings.server_url)
        self.server_url.setFixedWidth(220)
        self.server_url.setPlaceholderText("ComfyUI server")
        self.server_url.setToolTip("ComfyUI server IP address and port")
        generation_bar.addWidget(self.server_url)
        self.test_connection_button = QPushButton("TEST")
        self.test_connection_button.setFixedWidth(55)
        self.test_connection_button.setToolTip(
            "Test Connection: verify that the configured ComfyUI server is reachable"
        )
        self.test_connection_button.clicked.connect(self.test_comfyui_connection)
        generation_bar.addWidget(self.test_connection_button)
        self.queue_button = QPushButton("RUN+QUEUE")
        self.queue_button.setFixedWidth(100)
        self.queue_button.setToolTip(
            "Upload active Segment media and queue the selected generation quality"
        )
        self.queue_button.clicked.connect(self.queue_to_comfyui)
        generation_bar.addWidget(self.queue_button)
        self.storyboard_button = QPushButton("STORYBOARD")
        self.storyboard_button.setFixedWidth(105)
        self.storyboard_button.setObjectName("storyboardButton")
        self.storyboard_button.setToolTip(
            "Open the Shot-card Storyboard Editor; drag, add, delete or resize blocks before Apply"
        )
        self.storyboard_button.clicked.connect(self.open_storyboard_editor)
        generation_bar.addWidget(self.storyboard_button)
        self.storyboard_target_spin = QDoubleSpinBox()
        self.storyboard_target_spin.setObjectName("storyboardTargetDuration")
        self.storyboard_target_spin.setRange(0.5, 3600.0)
        self.storyboard_target_spin.setDecimals(1)
        self.storyboard_target_spin.setSingleStep(0.5)
        self.storyboard_target_spin.setSuffix("s")
        self.storyboard_target_spin.setFixedWidth(65)
        self.storyboard_target_spin.setValue(self.storyboard_target_duration_seconds)
        self.storyboard_target_spin.setToolTip(
            "Desired edited Storyboard duration. Delete unwanted purple Shot Blocks in Story Cut mode; later Timeline content ripples left."
        )
        self.storyboard_target_spin.valueChanged.connect(
            self._storyboard_target_changed
        )
        generation_bar.addWidget(self.storyboard_target_spin)
        self.storyboard_trim_button = QToolButton()
        self.storyboard_trim_button.setObjectName("storyboardTrimButton")
        self.storyboard_trim_button.setText("AUTO CUT")
        self.storyboard_trim_button.setFixedWidth(106)
        self.storyboard_trim_button.setPopupMode(QToolButton.MenuButtonPopup)
        self.storyboard_trim_button.setToolTip(
            "Build a protected 0.5-second Smart Cut plan. The main button uses Balanced mode; "
            "the arrow also offers Safe, Aggressive and the original Manual Ripple Cut."
        )
        self.storyboard_trim_menu = QMenu(self.storyboard_trim_button)
        self.smart_cut_safe_action = self.storyboard_trim_menu.addAction("AUTO CUT · SAFE")
        self.smart_cut_balanced_action = self.storyboard_trim_menu.addAction("AUTO CUT · BALANCED")
        self.smart_cut_aggressive_action = self.storyboard_trim_menu.addAction("AUTO CUT · AGGRESSIVE")
        self.storyboard_trim_menu.addSeparator()
        self.manual_ripple_action = self.storyboard_trim_menu.addAction("MANUAL RIPPLE CUT")
        self.manual_ripple_action.setCheckable(True)
        self.storyboard_trim_menu.addAction("OPEN STORYBOARD EDITOR", self.open_storyboard_editor)
        self.storyboard_trim_button.setMenu(self.storyboard_trim_menu)
        self.storyboard_trim_button.clicked.connect(
            lambda: self.open_smart_cut("balanced")
        )
        self.smart_cut_safe_action.triggered.connect(lambda: self.open_smart_cut("safe"))
        self.smart_cut_balanced_action.triggered.connect(lambda: self.open_smart_cut("balanced"))
        self.smart_cut_aggressive_action.triggered.connect(lambda: self.open_smart_cut("aggressive"))
        self.manual_ripple_action.toggled.connect(self._toggle_storyboard_trim_mode)
        generation_bar.addWidget(self.storyboard_trim_button)
        self.preview_button = QPushButton("PREVIEW 0.2M")
        self.preview_button.setFixedWidth(115)
        self.preview_button.setToolTip(
            "Motion Preview 0.2MP - generate a low-resolution motion test without RTX upscaling"
        )
        self.preview_button.clicked.connect(self.generate_pre_run_preview)
        generation_bar.addWidget(self.preview_button)
        self.accept_preview_button = QPushButton("ACCEPT 1.0M")
        self.accept_preview_button.setFixedWidth(110)
        self.accept_preview_button.setToolTip(
            "Approved Final 1.0MP - render with exactly the accepted Motion Preview seed"
        )
        self.accept_preview_button.setEnabled(False)
        self.accept_preview_button.clicked.connect(self.accept_pre_run_preview)
        generation_bar.addWidget(self.accept_preview_button)
        self.reject_preview_button = QPushButton("REJECT")
        self.reject_preview_button.setFixedWidth(70)
        self.reject_preview_button.setToolTip(
            "Reject Preview - discard the current preview seed and generate a new 0.2MP motion test"
        )
        self.reject_preview_button.setEnabled(False)
        self.reject_preview_button.clicked.connect(self.reject_pre_run_preview)
        generation_bar.addWidget(self.reject_preview_button)
        self.resource_estimate_button = QPushButton("ESTIMATE")
        self.resource_estimate_button.setFixedWidth(85)
        self.resource_estimate_button.setObjectName("resourceEstimateButton")
        self.resource_estimate_button.setToolTip(
            "Estimate render duration, GPU time and additional Workspace disk use"
        )
        self.resource_estimate_button.clicked.connect(self.show_resource_estimate)
        generation_bar.addWidget(self.resource_estimate_button)
        self._configure_generation_hover_help()
        self._build_generation_overflow_toolbar()
        self._refresh_incremental_controls()

    def _configure_generation_hover_help(self) -> None:
        """Show the full control name and effect immediately on pointer hover."""
        help_rows = (
            (
                self.clip_start,
                "Generation Work Area Start",
                "First Timeline time included by Preview, Final, Export and Segment planning.",
            ),
            (
                self.clip_end,
                "Generation Work Area End",
                "Last Timeline time included. Long ranges are split into resumable native H3 Segments.",
            ),
            (
                self.aspect_ratio_combo,
                "Output Aspect Ratio",
                "Sets the generated frame shape used by the active ResolutionSelector.",
            ),
            (
                self.production_strategy_combo,
                "Production Mode · Full Range / Incremental Batch",
                "FULL processes the current complete Work Area in one operation. BATCH previews only the next unapproved range and builds a cumulative Master after Accept.",
            ),
            (
                self.production_batch_spin,
                "Incremental Approval Batch Duration",
                "Target seconds per batch. Studio extends a boundary when required to keep authored speech intact.",
            ),
            (
                self.next_batch_button,
                "Preview Next Incremental Batch",
                "Moves Work Area to the next unapproved range and starts its 0.2MP motion Preview.",
            ),
            (
                self.production_progress_label,
                "Incremental Approval Progress",
                "Shows approved seconds versus complete Timeline duration and the pending batch state.",
            ),
            (
                self.export_api_button,
                "Export Active API · ComfyUI Workflow",
                "Saves the currently compiled Segment workflow with active mapping and generation parameters.",
            ),
            (
                self.server_url,
                "ComfyUI Server Address",
                "HTTP address used for connection tests, media upload and queued generation.",
            ),
            (
                self.test_connection_button,
                "Test Connection · ComfyUI Server",
                "Checks that the configured server is reachable before a render is submitted.",
            ),
            (
                self.queue_button,
                "Run and Queue Current Work Area",
                "Uploads Segment-local media and starts a direct render using the current Settings quality.",
            ),
            (
                self.storyboard_button,
                "Storyboard Editor · Shot Structure",
                "Review, reorder, add, delete and resize Shot cards before applying them to Timeline.",
            ),
            (
                self.storyboard_target_spin,
                "Storyboard Target Duration",
                "Target edited story length used by Storyboard and Smart Cut planning.",
            ),
            (
                self.storyboard_trim_button,
                "Smart Cut and Manual Ripple Cut",
                "Opens protected Safe, Balanced or Aggressive compression; the arrow also contains Manual Ripple Cut.",
            ),
            (
                self.preview_button,
                "Motion Preview 0.2MP",
                "Generates a low-cost motion test without RTX upscaling and records its seed.",
            ),
            (
                self.accept_preview_button,
                "Accept Preview · Approved Final 1.0MP",
                "Renders with exactly the accepted Preview seed and promotes the result to the cumulative Final Master.",
            ),
            (
                self.reject_preview_button,
                "Reject Preview and Generate Another Take",
                "Keeps approved results, advances the Preview seed and creates a replacement motion test.",
            ),
            (
                self.resource_estimate_button,
                "Estimate Time, GPU Work and Disk Use",
                "Calculates new versus reusable duration and checks the protected Workspace disk reserve.",
            ),
        )
        for widget, title, description in help_rows:
            widget.setToolTip(f"<b>{title}</b><br>{description}")
            widget.setProperty("generation_hover_help", True)
            widget.installEventFilter(self)

    def _build_generation_overflow_toolbar(self) -> None:
        """Wrap the ordered Generation controls onto an automatic second row."""
        self.generation_overflow_toolbar = QToolBar("Generation Controls · Row 2")
        self.generation_overflow_toolbar.setObjectName("generationOverflowToolbar")
        self.generation_overflow_toolbar.setMovable(False)
        self.generation_overflow_toolbar.setFloatable(False)
        self.generation_overflow_toolbar.setStyleSheet(
            "QToolBar { background:#1b1e21; border-top:1px solid #343a40; "
            "border-bottom:1px solid #050607; spacing:3px; padding:3px 5px; }"
        )
        self.addToolBarBreak(Qt.TopToolBarArea)
        self.addToolBar(Qt.TopToolBarArea, self.generation_overflow_toolbar)
        self.generation_overflow_toolbar.hide()
        self.generation_toolbar.installEventFilter(self)
        self._generation_toolbar_original_actions = list(
            self.generation_toolbar.actions()
        )
        self._generation_widget_actions = {
            widget: action
            for action in self._generation_toolbar_original_actions
            if (widget := self.generation_toolbar.widgetForAction(action)) is not None
        }
        self._generation_overflow_actions: list[QWidgetAction] = []
        self._generation_reflowing = False
        QTimer.singleShot(0, self._reflow_generation_toolbar)

    def _generation_action_width(self, action, toolbar: QToolBar) -> int:
        if action.isSeparator():
            return 10
        widget = toolbar.widgetForAction(action)
        if widget is None:
            return 0
        hint = max(widget.minimumSizeHint().width(), widget.sizeHint().width())
        if widget.maximumWidth() < 16777215:
            hint = min(hint, widget.maximumWidth())
        hint = max(widget.minimumWidth(), hint)
        return hint + 4

    def _restore_generation_actions_to_primary(self) -> None:
        for action in self._generation_toolbar_original_actions:
            self.generation_toolbar.removeAction(action)
            self.generation_overflow_toolbar.removeAction(action)
            self.generation_toolbar.addAction(action)
        self._generation_overflow_actions = []

    def _reflow_generation_toolbar(self) -> None:
        if (
            not hasattr(self, "generation_overflow_toolbar")
            or self._generation_reflowing
            or not self.isVisible()
        ):
            return
        self._generation_reflowing = True
        try:
            self._restore_generation_actions_to_primary()
            self._refresh_incremental_controls()
            self.generation_overflow_toolbar.hide()
            available = max(0, self.generation_toolbar.width() - 24)
            used = 0
            overflow_started = False
            overflow_actions = []
            for action in self._generation_toolbar_original_actions:
                width = self._generation_action_width(action, self.generation_toolbar)
                if not overflow_started and (width <= 0 or used + width <= available):
                    used += width
                    continue
                overflow_started = True
                overflow_actions.append(action)
            if not overflow_actions:
                return
            for action in overflow_actions:
                self.generation_toolbar.removeAction(action)
                self.generation_overflow_toolbar.addAction(action)
            self._generation_overflow_actions = overflow_actions
            self._refresh_incremental_controls()
            self.generation_overflow_toolbar.show()
            self.generation_overflow_toolbar.raise_()
        finally:
            self._generation_reflowing = False

    def _show_generation_overflow(self) -> None:
        if not getattr(self, "_generation_overflow_actions", []):
            return
        self.generation_overflow_toolbar.show()
        self.generation_overflow_toolbar.raise_()

    def _aspect_ratio_changed(self, *_args) -> None:
        self.render_settings.aspect_ratio = str(self.aspect_ratio_combo.currentData())
        self.preview_ready = False
        self.accept_preview_button.setEnabled(False)
        self._mark_dirty()

    def _timeline_duration_seconds(self) -> float:
        return max(0.0, float(self.scan.duration_seconds)) if self.scan else 0.0

    def _generation_work_area_end_changed(self, value: float) -> None:
        """Keep Work Area End editable and grow, but never destructively shrink, Timeline.

        The old control maximum was the current Timeline duration.  That made a
        default 12-second project impossible to extend from the toolbar.  A
        larger End now becomes an explicit Timeline extension; a smaller End
        remains a non-destructive render-range selection.
        """
        if not self.scan:
            return
        requested_end = max(0.01, float(value))
        minimum_end = min(
            MAX_MANUAL_TIMELINE_SECONDS,
            float(self.clip_start.value()) + TIMELINE_SNAP_SECONDS,
        )
        if requested_end < minimum_end - 1e-6:
            self.clip_end.blockSignals(True)
            self.clip_end.setValue(minimum_end)
            self.clip_end.blockSignals(False)
            requested_end = minimum_end
            self.statusBar().showMessage(
                f"Work Area End adjusted to {minimum_end:.1f}s so it remains later than Start"
            )
        current_duration = self._timeline_duration_seconds()
        if requested_end > current_duration + 1e-6:
            previous_start = float(self.clip_start.value())
            self._set_design_duration(requested_end)
            self.clip_start.setValue(min(previous_start, requested_end))
            self.clip_end.setValue(requested_end)
            self._mark_all_render_segments_dirty()
            self._mark_dirty()
            self.statusBar().showMessage(
                f"Timeline extended from {current_duration:.1f}s to {requested_end:.1f}s · "
                "add or extend Shot and media blocks for the new range"
            )
        self.refresh_activation()

    def _production_strategy_changed(self, *_args) -> None:
        strategy = str(self.production_strategy_combo.currentData() or "full_range")
        if strategy not in {"full_range", "incremental"}:
            strategy = "full_range"
        self.production_strategy = strategy
        if strategy == "full_range" and self.scan:
            self.clip_start.setValue(0.0)
            self.clip_end.setValue(self._timeline_duration_seconds())
        elif strategy == "incremental" and self.incremental_approved_horizon <= 0.0:
            manifest = self.smart_render_manifests.get("production", {})
            rows = list(manifest.get("segments") or []) if isinstance(manifest, dict) else []
            if rows and all(
                str(row.get("status", "")).lower()
                in {"cached", "complete", "completed", "reusable"}
                for row in rows if isinstance(row, dict)
            ):
                self.incremental_approved_horizon = min(
                    self._timeline_duration_seconds(),
                    max(
                        0.0,
                        float(
                            manifest.get("timeline_end_seconds")
                            or manifest.get("target_duration_seconds")
                            or 0.0
                        ),
                    ),
                )
        self._refresh_incremental_controls()
        self._mark_dirty()

    def _production_batch_seconds_changed(self, value: float) -> None:
        self.production_batch_seconds = max(16.0, float(value))
        self._refresh_incremental_controls()
        self._mark_dirty()

    def _special_skill_production_strategy_changed(self, *_args) -> None:
        """Long-form Special selects safe batching; every other Skill stays one-shot."""
        desired = (
            "incremental"
            if str(self.special_combo.currentData() or "") == "long-form-h3-director"
            else "full_range"
        )
        index = self.production_strategy_combo.findData(desired)
        if index >= 0 and self.production_strategy_combo.currentIndex() != index:
            self.production_strategy_combo.setCurrentIndex(index)

    def _next_incremental_batch_end(self) -> float:
        """Return a 0.5s approval horizon without cutting explicit speech."""
        duration = self._timeline_duration_seconds()
        start = min(duration, max(0.0, self.incremental_approved_horizon))
        boundary = snap_timeline_seconds(
            min(duration, start + self.production_batch_seconds), duration
        )
        if boundary >= duration - 1e-6:
            return duration

        # Authored speech is protected even if this makes one batch longer
        # than its target.  Shot boundaries may extend the batch by up to eight
        # seconds so a very long Shot does not defeat incremental production.
        for _pass in range(4):
            extended = boundary
            for layer in self.text_layers:
                if (
                    layer.content_role in {"dialogue", "voice_over", "lyrics"}
                    and layer.start_seconds < boundary < layer.end_seconds
                ):
                    extended = max(extended, layer.end_seconds)
            for cue in self.director_cues:
                if (
                    cue.cue_type == "shot"
                    and cue.start_seconds < boundary < cue.end_seconds
                    and cue.end_seconds <= boundary + 8.0
                ):
                    extended = max(extended, cue.end_seconds)
            extended = snap_timeline_seconds(min(duration, extended), duration)
            if extended <= boundary + 1e-6:
                break
            boundary = extended
        return min(duration, boundary)

    def _refresh_incremental_controls(self) -> None:
        if not hasattr(self, "next_batch_button"):
            return
        duration = self._timeline_duration_seconds()
        approved = min(duration, max(0.0, self.incremental_approved_horizon))
        pending_start = min(duration, max(0.0, self.incremental_pending_start))
        pending_end = min(duration, max(pending_start, self.incremental_pending_end))
        incremental = self.production_strategy == "incremental"
        running = bool(self.submit_runner and self.submit_runner.is_running())
        self.production_batch_spin.setEnabled(incremental and not running)
        for widget in (
            self.production_batch_spin,
            self.production_progress_label,
            self.next_batch_button,
        ):
            action = getattr(self, "_generation_widget_actions", {}).get(widget)
            if action is not None:
                action.setVisible(True)
            widget.setVisible(True)
        if not incremental:
            self.next_batch_button.setEnabled(False)
            self.next_batch_button.setText("NEXT")
            self.production_progress_label.setText(
                f"✓{approved:.1f}/{duration:.1f}s"
            )
            self.production_progress_label.setToolTip(
                f"Approved {approved:.1f} of {duration:.1f} seconds · switch MODE to BATCH to continue incrementally"
            )
            return
        if approved >= duration - 1e-6 and duration > 0.0:
            self.next_batch_button.setText("DONE")
            self.next_batch_button.setEnabled(False)
            detail = "complete"
        elif self.incremental_batch_phase == "preview_ready":
            self.next_batch_button.setText("ACCEPT")
            self.next_batch_button.setEnabled(False)
            detail = f"preview {pending_start:.1f}–{pending_end:.1f}s ready"
        elif self.incremental_batch_phase == "accepting":
            self.next_batch_button.setText("RESUME")
            self.next_batch_button.setEnabled(
                not running and self.preview_seed is not None
            )
            detail = f"accepting 0–{pending_end:.1f}s"
        else:
            self.next_batch_button.setText("NEXT")
            self.next_batch_button.setEnabled(not running and duration > approved + 1e-6)
            next_end = self._next_incremental_batch_end() if duration else 0.0
            detail = f"next {approved:.1f}–{next_end:.1f}s" if next_end > approved else "ready"
        self.production_progress_label.setText(f"✓{approved:.1f}/{duration:.1f}s")
        self.production_progress_label.setToolTip(
            f"Approved {approved:.1f} of {duration:.1f} seconds · {detail}"
        )

    def start_next_incremental_batch(self) -> None:
        if not self.scan:
            QMessageBox.information(self, "Incremental production", "Load or create a project first.")
            return
        if self.production_strategy != "incremental":
            QMessageBox.information(
                self,
                "Incremental production",
                "Select INCREMENTAL or choose the Long-form H3 Director Special Skill first.",
            )
            return
        if self.incremental_batch_phase == "accepting":
            if self.preview_seed is None:
                self.incremental_batch_phase = ""
                self._refresh_incremental_controls()
                return
            self.clip_start.setValue(0.0)
            self.clip_end.setValue(self.incremental_pending_end)
            self.accept_pre_run_preview()
            return
        if self.incremental_batch_phase == "preview_ready":
            QMessageBox.information(
                self,
                "Batch preview ready",
                "Use ACCEPT 1.0M to approve this batch, or REJECT to create another motion take.",
            )
            return
        start = min(
            self._timeline_duration_seconds(),
            max(0.0, self.incremental_approved_horizon),
        )
        end = self._next_incremental_batch_end()
        if end <= start + 1e-6:
            self._refresh_incremental_controls()
            return
        self.incremental_pending_start = start
        self.incremental_pending_end = end
        self.incremental_batch_phase = "previewing"
        self.clip_start.setValue(start)
        self.clip_end.setValue(end)
        self._mark_dirty()
        self._refresh_incremental_controls()
        self.generate_pre_run_preview()

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.settings_megapixels = QDoubleSpinBox()
        self.settings_megapixels.setRange(0.1, 16.0)
        self.settings_megapixels.setDecimals(2)
        self.settings_megapixels.setSingleStep(0.1)
        self.settings_megapixels.setSuffix(" MP")
        self.settings_sampling_steps = QSpinBox()
        self.settings_sampling_steps.setRange(1, 200)
        self.settings_denoise = QDoubleSpinBox()
        self.settings_denoise.setRange(0.0, 1.0)
        self.settings_denoise.setDecimals(3)
        self.settings_denoise.setSingleStep(0.05)
        self.settings_rtx_vsr = QCheckBox("Enable RTX Video Super Resolution")
        self.settings_history_poll = QDoubleSpinBox()
        self.settings_history_poll.setRange(0.1, 60.0)
        self.settings_history_poll.setDecimals(1)
        self.settings_history_poll.setSuffix(" s")
        self.settings_generation_timeout = QSpinBox()
        self.settings_generation_timeout.setRange(10, 86400)
        self.settings_generation_timeout.setSuffix(" s")
        self.settings_http_timeout = QSpinBox()
        self.settings_http_timeout.setRange(1, 600)
        self.settings_http_timeout.setSuffix(" s")
        self.settings_workspace_disk_reserve = QDoubleSpinBox()
        self.settings_workspace_disk_reserve.setRange(0.0, 2000.0)
        self.settings_workspace_disk_reserve.setDecimals(1)
        self.settings_workspace_disk_reserve.setSingleStep(5.0)
        self.settings_workspace_disk_reserve.setSuffix(" GB")
        self.settings_workspace_disk_reserve.setToolTip(
            "Generation is blocked when estimated new files would leave less "
            "free space than this reserve. Approved Shot Takes are preserved."
        )
        self.settings_dialogue_tts = QComboBox()
        self.settings_dialogue_tts.addItem(
            "MiniMax H3 Native Dialogue · no authored WAV",
            "h3_native",
        )
        self.settings_dialogue_tts.addItem("Edge TTS · online neural voices", "edge_tts")
        self.settings_dialogue_tts.addItem("VoxCPM2 Local · offline model", "voxcpm2_local")
        self.settings_dialogue_tts.addItem(
            "Qwen3-TTS Local · offline CustomVoice model",
            "qwen3_tts_local",
        )
        self.settings_dialogue_tts.setToolTip(
            "Speech mode used for Dialogue, Voice-over and Lyrics text layers. "
            "H3 Native sends exact Timeline text without creating a WAV. "
            "VoxCPM2 loads only from project models/VoxCPM2, prefers CUDA, and "
            "automatically retries on CPU if CUDA fails. Qwen3-TTS uses its isolated "
            "runtime plus project models/Qwen3-TTS-12Hz-0.6B-CustomVoice."
        )
        self.settings_voxcpm_model_status = QLabel()
        self.settings_voxcpm_model_status.setWordWrap(True)
        self.settings_qwen3_tts_model_status = QLabel()
        self.settings_qwen3_tts_model_status.setWordWrap(True)
        self.settings_blip_device = QComboBox()
        self.settings_blip_device.addItem(
            "Auto · CPU-safe start, verified CUDA when available",
            "auto",
        )
        self.settings_blip_device.addItem(
            "CUDA preferred · automatic CPU fallback",
            "cuda",
        )
        self.settings_blip_device.addItem("CPU only", "cpu")
        self.settings_blip_device.setToolTip(
            "Auto is the first-run default: BLIP loads safely on CPU, verifies a real "
            "CUDA operation, then moves to CUDA. Any CUDA startup or inference failure "
            "automatically retries the same analysis on CPU."
        )
        self.settings_node_map = QLabel("Load an API workflow to inspect mapped nodes.")
        self.settings_node_map.setWordWrap(True)
        form.addRow("Mega pixels", self.settings_megapixels)
        form.addRow("Sampling steps", self.settings_sampling_steps)
        form.addRow("Denoise", self.settings_denoise)
        form.addRow(self.settings_rtx_vsr)
        form.addRow("History poll interval", self.settings_history_poll)
        form.addRow("Generation timeout", self.settings_generation_timeout)
        form.addRow("HTTP request timeout", self.settings_http_timeout)
        form.addRow("Workspace free disk reserve", self.settings_workspace_disk_reserve)
        form.addRow("Dialogue Text Layer TTS", self.settings_dialogue_tts)
        form.addRow("VoxCPM2 model", self.settings_voxcpm_model_status)
        form.addRow("Qwen3-TTS runtime/model", self.settings_qwen3_tts_model_status)
        form.addRow("BLIP inference device", self.settings_blip_device)
        form.addRow("Mapped API nodes", self.settings_node_map)
        buttons = QHBoxLayout()
        save_button = QPushButton("SAVE SETTINGS TO .ENV")
        save_button.clicked.connect(self.save_render_settings)
        restore_button = QPushButton("RESTORE DEFAULTS")
        restore_button.clicked.connect(self.restore_default_settings)
        buttons.addWidget(save_button)
        buttons.addWidget(restore_button)
        form.addRow(buttons)
        self._sync_settings_ui()
        for widget in (
            self.settings_megapixels,
            self.settings_sampling_steps,
            self.settings_denoise,
            self.settings_history_poll,
            self.settings_generation_timeout,
            self.settings_http_timeout,
            self.settings_workspace_disk_reserve,
        ):
            widget.valueChanged.connect(self._settings_ui_changed)
        self.settings_rtx_vsr.toggled.connect(self._settings_ui_changed)
        self.settings_dialogue_tts.currentIndexChanged.connect(
            self._dialogue_tts_ui_changed
        )
        self.settings_blip_device.currentIndexChanged.connect(self._blip_device_ui_changed)
        return page

    def _sync_settings_ui(self) -> None:
        settings = self.render_settings
        self.settings_megapixels.setValue(settings.megapixels)
        self.settings_sampling_steps.setValue(settings.sampling_steps)
        self.settings_denoise.setValue(settings.denoise)
        self.settings_rtx_vsr.setChecked(settings.rtx_video_super_resolution)
        self.settings_history_poll.setValue(settings.history_poll_interval)
        self.settings_generation_timeout.setValue(settings.generation_timeout)
        self.settings_http_timeout.setValue(settings.http_request_timeout)
        self.settings_workspace_disk_reserve.setValue(
            settings.workspace_free_disk_reserve_gb
        )
        tts_index = self.settings_dialogue_tts.findData(settings.dialogue_tts_engine)
        self.settings_dialogue_tts.setCurrentIndex(max(0, tts_index))
        blip_index = self.settings_blip_device.findData(settings.blip_device)
        self.settings_blip_device.setCurrentIndex(max(0, blip_index))
        self._refresh_voxcpm_model_status_ui()

    def _refresh_voxcpm_model_status_ui(self) -> bool:
        missing = voxcpm_model_missing()
        ready = not missing
        if ready:
            self.settings_voxcpm_model_status.setText(
                "READY · " + str(VOXCPM_MODEL_DIR)
            )
            self.settings_voxcpm_model_status.setStyleSheet(
                "color:#72d69a; font-weight:700; padding:3px;"
            )
            self.settings_dialogue_tts.setStyleSheet("")
        else:
            self.settings_voxcpm_model_status.setText(
                "⚠ MODEL MISSING · Download openbmb/VoxCPM2 to "
                f"{VOXCPM_MODEL_DIR}\nMissing: {', '.join(missing)}"
            )
            self.settings_voxcpm_model_status.setStyleSheet(
                "background:#4a251a; color:#ffd28b; border:1px solid #ff9d38; "
                "padding:4px; font-weight:700;"
            )
            if self.settings_dialogue_tts.currentData() == "voxcpm2_local":
                self.settings_dialogue_tts.setStyleSheet(
                    "border:2px solid #ff9d38; background:#3f261d; color:#ffe0ad;"
                )
            else:
                self.settings_dialogue_tts.setStyleSheet("")
        qwen_runtime_missing = qwen3_tts_runtime_missing()
        qwen_support_missing = qwen3_tts_support_missing()
        qwen_model_missing = qwen3_tts_model_missing()
        qwen_ready = (
            not qwen_runtime_missing
            and not qwen_support_missing
            and not qwen_model_missing
        )
        if qwen_ready:
            self.settings_qwen3_tts_model_status.setText(
                "READY · runtime "
                + str(QWEN3_TTS_RUNTIME_DIR)
                + " · model "
                + str(QWEN3_TTS_MODEL_DIR)
            )
            self.settings_qwen3_tts_model_status.setStyleSheet(
                "color:#72d69a; font-weight:700; padding:3px;"
            )
        else:
            missing = [
                *(f"runtime/{item}" for item in qwen_runtime_missing),
                *(f"support/{item}" for item in qwen_support_missing),
                *(f"model/{item}" for item in qwen_model_missing),
            ]
            self.settings_qwen3_tts_model_status.setText(
                "⚠ MISSING · Run install_qwen3_tts_runtime.bat; download "
                "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice to "
                f"{QWEN3_TTS_MODEL_DIR}\nMissing: {', '.join(missing)}"
            )
            self.settings_qwen3_tts_model_status.setStyleSheet(
                "background:#4a251a; color:#ffd28b; border:1px solid #ff9d38; "
                "padding:4px; font-weight:700;"
            )
        if self.settings_dialogue_tts.currentData() == "qwen3_tts_local":
            self.settings_dialogue_tts.setStyleSheet(
                "" if qwen_ready else
                "border:2px solid #ff9d38; background:#3f261d; color:#ffe0ad;"
            )
        return ready if self.settings_dialogue_tts.currentData() != "qwen3_tts_local" else qwen_ready

    def _settings_ui_changed(self, *_args) -> None:
        self._read_settings_ui()
        self.preview_ready = False
        self.accept_preview_button.setEnabled(False)
        self._mark_dirty()

    def _blip_device_ui_changed(self, *_args) -> None:
        previous = self.render_settings.blip_device
        self._settings_ui_changed()
        selected = self.render_settings.blip_device
        if selected == previous:
            return
        self.blip_cpu_mode = selected == "cpu"
        self.blip_cpu_fallback_attempted = False
        if self.blip_runner.is_running():
            if self.blip_jobs:
                self.blip_restart_after_jobs = True
            else:
                self.blip_runner.stop()
        self.statusBar().showMessage(
            f"BLIP device changed to {selected.upper()} · applies to the next analysis"
        )

    def _dialogue_tts_ui_changed(self, *_args) -> None:
        previous = self.render_settings.dialogue_tts_engine
        self._settings_ui_changed()
        selected = self.render_settings.dialogue_tts_engine
        model_ready = self._refresh_voxcpm_model_status_ui()
        if selected == previous:
            return
        if selected == "h3_native":
            self.timeline_tts_refresh_timer.stop()
            if (
                self.design_tts_runner
                and self.design_tts_runner.is_running()
                and (self.pending_design_tts or {}).get("mode") == "timeline_refresh"
            ):
                self.pending_design_tts = None
                self.pending_generation_after_tts = None
                self.design_tts_runner.stop()
            self._use_h3_native_dialogue()
            self.statusBar().showMessage(
                "Dialogue mode changed to Ori · MiniMax H3 will generate the latest Timeline dialogue",
                10000,
            )
            return
        if selected == "voxcpm2_local" and not model_ready:
            self.statusBar().showMessage(
                "VoxCPM2 MODEL MISSING · download openbmb/VoxCPM2 to "
                + str(VOXCPM_MODEL_DIR),
                15000,
            )
            return
        if selected == "qwen3_tts_local" and not model_ready:
            self.statusBar().showMessage(qwen3_tts_missing_message(), 15000)
            return
        if self._speech_layers_for_tts():
            self.timeline_tts_stale = True
        label = {
            "voxcpm2_local": "VoxCPM2 Local",
            "qwen3_tts_local": "Qwen3-TTS Local",
            "edge_tts": "Edge TTS",
        }.get(selected, selected)
        self.statusBar().showMessage(
            f"Dialogue mode changed to {label} · WAV will rebuild before Preview/Run",
            10000,
        )

    def _require_voxcpm_model(self, *, notify: bool = False) -> bool:
        missing = voxcpm_model_missing()
        self._refresh_voxcpm_model_status_ui()
        if not missing:
            return True
        message = voxcpm_missing_message()
        self.statusBar().showMessage(message, 15000)
        if notify:
            QMessageBox.warning(self, "VoxCPM2 model missing", message)
        return False

    def _require_qwen3_tts_model(self, *, notify: bool = False) -> bool:
        missing = (
            qwen3_tts_runtime_missing()
            or qwen3_tts_support_missing()
            or qwen3_tts_model_missing()
        )
        self._refresh_voxcpm_model_status_ui()
        if not missing:
            return True
        message = qwen3_tts_missing_message()
        self.statusBar().showMessage(message, 15000)
        if notify:
            QMessageBox.warning(self, "Qwen3-TTS runtime/model missing", message)
        return False

    def _read_settings_ui(self) -> None:
        self.render_settings = RenderSettings.from_mapping(
            {
                **asdict(self.render_settings),
                "server_url": self.server_url.text().strip(),
                "aspect_ratio": self.aspect_ratio_combo.currentData(),
                "megapixels": self.settings_megapixels.value(),
                "sampling_steps": self.settings_sampling_steps.value(),
                "denoise": self.settings_denoise.value(),
                "rtx_video_super_resolution": self.settings_rtx_vsr.isChecked(),
                "history_poll_interval": self.settings_history_poll.value(),
                "generation_timeout": self.settings_generation_timeout.value(),
                "http_request_timeout": self.settings_http_timeout.value(),
                "workspace_free_disk_reserve_gb": (
                    self.settings_workspace_disk_reserve.value()
                ),
                "dialogue_tts_engine": self.settings_dialogue_tts.currentData(),
                "blip_device": self.settings_blip_device.currentData(),
            }
        )

    def save_render_settings(self) -> None:
        self._read_settings_ui()
        save_settings(SETTINGS_ENV, self.render_settings)
        self.statusBar().showMessage(f"Settings saved to {SETTINGS_ENV.name}")

    def restore_default_settings(self) -> None:
        self.render_settings = RenderSettings.defaults()
        self.server_url.setText(self.render_settings.server_url)
        index = self.aspect_ratio_combo.findData(self.render_settings.aspect_ratio)
        self.aspect_ratio_combo.setCurrentIndex(max(0, index))
        self._sync_settings_ui()
        self.blip_cpu_mode = self.render_settings.blip_device == "cpu"
        self.blip_cpu_fallback_attempted = False
        if self.blip_runner.is_running():
            if self.blip_jobs:
                self.blip_restart_after_jobs = True
            else:
                self.blip_runner.stop()
        save_settings(SETTINGS_ENV, self.render_settings)
        self.statusBar().showMessage("Default settings restored and saved to .env")

    def _build_workspace(self) -> None:
        root = QSplitter(Qt.Vertical)
        upper = QSplitter(Qt.Horizontal)

        project_tabs = QTabWidget()
        media_page = QWidget()
        media_layout = QVBoxLayout(media_page)
        media_layout.setContentsMargins(5, 5, 5, 5)
        media_header_row = QHBoxLayout()
        media_header_row.setSpacing(3)
        self.media_header = QLabel("VIRTUAL MEDIA POOL · waiting for API")
        self.media_header.setStyleSheet(
            "font-size:10px; font-weight:700; color:#bfc4ca; padding:1px;"
        )
        self.media_header.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.media_header.setMinimumWidth(0)
        self.media_header.setToolTip(
            "Unlimited logical Media Pool. The compact header shows logical "
            "Image/Video/Audio totals and per-Segment physical H3 capacity."
        )
        media_header_row.addWidget(self.media_header, 1)
        self.add_media_buttons: dict[str, QPushButton] = {}
        for label, kind in (("+I", "image"), ("+V", "video"), ("+A", "audio")):
            button = QPushButton(label)
            button.setFixedSize(30, 22)
            button.setToolTip(
                f"Add {kind.upper()} to the unlimited Virtual Media Pool. "
                "H3 physical slots are assigned per Segment."
            )
            button.clicked.connect(
                lambda _checked=False, media_type=kind: self.add_virtual_media(media_type)
            )
            self.add_media_buttons[kind] = button
            media_header_row.addWidget(button)
        media_layout.addLayout(media_header_row)
        self.media_scroll = QScrollArea()
        self.media_scroll.setWidgetResizable(True)
        self.media_scroll.viewport().installEventFilter(self)
        self.media_container = QWidget()
        self.media_grid = QGridLayout(self.media_container)
        self.media_grid.setContentsMargins(4, 4, 4, 4)
        self.media_grid.setSpacing(8)
        self.media_grid.setAlignment(Qt.AlignTop)
        self.media_scroll.setWidget(self.media_container)
        media_layout.addWidget(self.media_scroll)
        project_tabs.addTab(media_page, "PROJECT / MEDIA")
        self.prompt_panel = PromptPanel()
        self.prompt_panel.generate_requested.connect(self.generate_prompt)
        self.prompt_panel.content_changed.connect(self.schedule_prompt_generation)
        self.prompt_panel.sync_requested.connect(
            lambda: self._sync_prompt_panel_from_timeline(force=True)
        )
        self.prompt_panel.auto_sync.toggled.connect(
            lambda enabled: self._sync_prompt_panel_from_timeline(force=True) if enabled else None
        )
        prompt_scroll = QScrollArea()
        prompt_scroll.setWidgetResizable(True)
        prompt_scroll.setWidget(self.prompt_panel)
        project_tabs.addTab(prompt_scroll, "H3 PROMPT")
        upper.addWidget(project_tabs)

        monitor = QWidget()
        monitor_layout = QVBoxLayout(monitor)
        monitor_layout.setContentsMargins(5, 5, 5, 5)
        title = QLabel("PROGRAM MONITOR")
        title.setStyleSheet("font-weight:700; padding:4px;")
        monitor_layout.addWidget(title)

        self.monitor_compare_splitter = QSplitter(Qt.Horizontal)
        self.monitor_compare_splitter.setChildrenCollapsible(False)
        self.monitor_compare_splitter.setHandleWidth(6)
        self.monitor_compare_splitter.setStyleSheet(
            "QSplitter::handle { background:#303841; } "
            "QSplitter::handle:hover { background:#39b8ca; }"
        )

        timeline_monitor_panel = MonitorSplitPane()
        timeline_monitor_layout = QVBoxLayout(timeline_monitor_panel)
        timeline_monitor_layout.setContentsMargins(0, 0, 0, 0)
        timeline_monitor_header = QLabel("TIMELINE SOURCE")
        timeline_monitor_header.setStyleSheet(
            "background:#1b1f24; color:#aeb7c0; padding:3px 6px; font-size:9px; font-weight:700;"
        )
        timeline_monitor_layout.addWidget(timeline_monitor_header)
        self.monitor_stack = QStackedWidget()
        self.monitor_image = QLabel("Load a media slot to preview")
        self.monitor_image.setAlignment(Qt.AlignCenter)
        self.monitor_image.setStyleSheet("background:#050607; color:#5d6269;")
        self.monitor_image.setMinimumHeight(300)
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background:black;")
        self.monitor_stack.addWidget(self.monitor_image)
        self.monitor_stack.addWidget(self.video_widget)
        self.monitor_text_labels: dict[str, MonitorTextLabel] = {}
        timeline_monitor_layout.addWidget(self.monitor_stack, 1)
        self.monitor_compare_splitter.addWidget(timeline_monitor_panel)

        generated_monitor_panel = MonitorSplitPane()
        generated_monitor_layout = QVBoxLayout(generated_monitor_panel)
        generated_monitor_layout.setContentsMargins(0, 0, 0, 0)
        generated_monitor_header = QLabel("GENERATED OUTPUT")
        generated_monitor_header.setStyleSheet(
            "background:#17272b; color:#65d3df; padding:3px 6px; font-size:9px; font-weight:700;"
        )
        generated_monitor_layout.addWidget(generated_monitor_header)
        self.generated_monitor_stack = QStackedWidget()
        self.generated_monitor_image = QLabel("Generate or open a project with an output video")
        self.generated_monitor_image.setAlignment(Qt.AlignCenter)
        self.generated_monitor_image.setStyleSheet("background:#050607; color:#5d6269;")
        # Render generated video through QVideoSink into a regular QLabel.
        # QVideoWidget can create a native child surface on Windows which sits
        # above sibling widgets and cuts holes in translucent overlays.
        self.generated_video_widget = QLabel()
        self.generated_video_widget.setAlignment(Qt.AlignCenter)
        self.generated_video_widget.setStyleSheet("background:black;")
        self.generated_frame_pixmap = QPixmap()
        self.generated_monitor_stack.addWidget(self.generated_monitor_image)
        self.generated_monitor_stack.addWidget(self.generated_video_widget)
        generated_monitor_layout.addWidget(self.generated_monitor_stack, 1)
        self.monitor_compare_splitter.addWidget(generated_monitor_panel)
        self.monitor_compare_splitter.setStretchFactor(0, 1)
        self.monitor_compare_splitter.setStretchFactor(1, 1)
        self.monitor_compare_splitter.setSizes([500, 500])

        self.monitor_display_stack = QStackedWidget()
        self.monitor_display_stack.addWidget(self.monitor_compare_splitter)
        self.generation_overlay = GenerationBusyOverlay(self.monitor_display_stack)
        monitor_layout.addWidget(self.monitor_display_stack, 1)
        generated_row = QHBoxLayout()
        self.generated_output_label = QLabel("No generated output")
        self.generated_output_label.setStyleSheet("color:#7f8992; padding:2px 4px;")
        self.generated_output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.export_generated_button = QPushButton("EXPORT GENERATED VIDEO…")
        self.export_generated_button.setToolTip("Save the generated Program Monitor video to another folder")
        self.export_generated_button.setEnabled(False)
        self.export_generated_button.clicked.connect(self.export_generated_output)
        generated_row.addWidget(self.generated_output_label, 1)
        generated_row.addWidget(self.export_generated_button)
        monitor_layout.addLayout(generated_row)
        controls = QHBoxLayout()
        self.play_button = QPushButton("▶")
        self.play_button.setFixedWidth(44)
        self.play_button.clicked.connect(self.toggle_playback)
        self.position_slider = PrecisionScrubSlider()
        self.position_slider.sliderPressed.connect(self._begin_timeline_slider_scrub)
        self.position_slider.sliderMoved.connect(self._preview_timeline_slider_scrub)
        self.position_slider.sliderReleased.connect(self._end_timeline_slider_scrub)
        self.time_label = QLabel("00:00.000")
        controls.addWidget(self.play_button)
        controls.addWidget(self.position_slider, 1)
        controls.addWidget(self.time_label)
        monitor_layout.addLayout(controls)
        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.mediaStatusChanged.connect(self._video_media_status_changed)
        self.generated_audio_output = QAudioOutput(self)
        self.generated_player = QMediaPlayer(self)
        self.generated_player.setAudioOutput(self.generated_audio_output)
        self.generated_video_sink = QVideoSink(self)
        self.generated_video_sink.videoFrameChanged.connect(
            self._generated_video_frame_changed
        )
        self.generated_player.setVideoOutput(self.generated_video_sink)
        self.generated_player.mediaStatusChanged.connect(
            self._generated_media_status_changed
        )
        self.generated_player.positionChanged.connect(
            self._generated_position_changed
        )
        upper.addWidget(monitor)

        right = QSplitter(Qt.Vertical)
        inspector_tabs = QTabWidget()
        inspector = QWidget()
        inspector_form = QFormLayout(inspector)
        self.inspect_tag = QLabel("—")
        self.inspect_node = QLabel("—")
        self.inspect_file = QLabel("—")
        self.inspect_file.setWordWrap(True)
        self.asset_start = QDoubleSpinBox()
        self.asset_start.setDecimals(2)
        self.asset_start.setSuffix(" s")
        self.asset_start.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.asset_end = QDoubleSpinBox()
        self.asset_end.setDecimals(2)
        self.asset_end.setSuffix(" s")
        self.asset_end.setSingleStep(TIMELINE_SNAP_SECONDS)
        self.asset_speed = QDoubleSpinBox()
        self.asset_speed.setRange(0.10, 4.0)
        self.asset_speed.setDecimals(2)
        self.asset_speed.setSingleStep(0.05)
        self.asset_speed.setSuffix(" ×")
        self.asset_source_in = QDoubleSpinBox()
        self.asset_source_in.setRange(0.0, 86400.0)
        self.asset_source_in.setDecimals(2)
        self.asset_source_in.setSuffix(" s")
        self.asset_source_out = QDoubleSpinBox()
        self.asset_source_out.setRange(0.0, 86400.0)
        self.asset_source_out.setDecimals(2)
        self.asset_source_out.setSuffix(" s")
        self.asset_fade_in = QDoubleSpinBox()
        self.asset_fade_in.setRange(0.0, 30.0)
        self.asset_fade_in.setDecimals(2)
        self.asset_fade_in.setSuffix(" s")
        self.asset_fade_out = QDoubleSpinBox()
        self.asset_fade_out.setRange(0.0, 30.0)
        self.asset_fade_out.setDecimals(2)
        self.asset_fade_out.setSuffix(" s")
        transitions = ["None", "Cross Dissolve", "Dip to Black", "Wipe"]
        self.asset_transition_in = QComboBox()
        self.asset_transition_in.addItems(transitions)
        self.asset_transition_out = QComboBox()
        self.asset_transition_out.addItems(transitions)
        apply_range = QPushButton("APPLY RANGE")
        apply_range.clicked.connect(self.apply_asset_range)
        apply_clip = QPushButton("APPLY CLIP PROPERTIES")
        apply_clip.clicked.connect(self.apply_clip_properties)
        self.remove_clip_button = QPushButton("REMOVE FROM TIMELINE")
        self.remove_clip_button.clicked.connect(
            lambda: self.remove_timeline_asset(self._selected_clip()) if self._selected_clip() else None
        )
        inspector_form.addRow("Reference", self.inspect_tag)
        inspector_form.addRow("Comfy node", self.inspect_node)
        inspector_form.addRow("Local file", self.inspect_file)
        inspector_form.addRow("Start", self.asset_start)
        inspector_form.addRow("End", self.asset_end)
        inspector_form.addRow("Speed", self.asset_speed)
        inspector_form.addRow("Source In", self.asset_source_in)
        inspector_form.addRow("Source Out", self.asset_source_out)
        inspector_form.addRow("Fade In", self.asset_fade_in)
        inspector_form.addRow("Fade Out", self.asset_fade_out)
        inspector_form.addRow("Transition In", self.asset_transition_in)
        inspector_form.addRow("Transition Out", self.asset_transition_out)
        inspector_form.addRow(apply_range)
        inspector_form.addRow(apply_clip)
        inspector_form.addRow(self.remove_clip_button)
        inspector_scroll = QScrollArea()
        inspector_scroll.setWidgetResizable(True)
        inspector_scroll.setWidget(inspector)
        inspector_tabs.addTab(inspector_scroll, "INSPECTOR")
        workflow_info = QPlainTextEdit()
        workflow_info.setReadOnly(True)
        self.workflow_info = workflow_info
        inspector_tabs.addTab(workflow_info, "API GRAPH")
        settings_page = self._build_settings_page()
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setWidget(settings_page)
        inspector_tabs.addTab(settings_scroll, "SETTINGS")
        right.addWidget(inspector_tabs)

        recognition_box = QGroupBox("RECOGNITION / ACTIVATION")
        rec_layout = QVBoxLayout(recognition_box)
        self.recognition_tabs = QTabWidget()
        self.recognition_text = QPlainTextEdit()
        self.recognition_text.setReadOnly(True)
        self.recognition_text.setPlaceholderText(
            "FFprobe, BLIP frames, beat, VAD and Whisper evidence appear here."
        )
        self.recognition_tabs.addTab(self.recognition_text, "RAW ANALYSIS")
        self.semantic_text = QPlainTextEdit()
        self.semantic_text.setReadOnly(True)
        self.semantic_text.setPlaceholderText(
            "Optional Qwen/GPT interpretation appears here. Inferences remain separate from raw evidence."
        )
        self.recognition_tabs.addTab(self.semantic_text, "AI SEMANTIC")
        rec_layout.addWidget(self.recognition_tabs, 1)
        self.semantic_status_label = QLabel("AI semantic enrichment: no media selected")
        self.semantic_status_label.setWordWrap(True)
        self.semantic_status_label.setStyleSheet("color:#8f9aa5; font-size:10px;")
        # Keep the state label as an internal status surface for automation/tests,
        # but do not let the optional-enrichment explanation consume inspector
        # space or cover the actual recognition evidence.
        self.semantic_status_label.hide()

        recognition_row = QHBoxLayout()
        recognition_row.setContentsMargins(0, 0, 0, 0)
        recognition_row.setSpacing(3)
        self.mode_buttons: dict[str, QPushButton] = {}
        for mode in ("auto", "active", "bypass"):
            button = QPushButton(mode.upper())
            button.setCheckable(True)
            button.setFixedHeight(24)
            button.setMinimumWidth(48)
            button.clicked.connect(lambda checked=False, value=mode: self.set_activation_mode(value))
            self.mode_buttons[mode] = button
            recognition_row.addWidget(button)
        self.run_recognition = QPushButton("ANALYZE MEDIA")
        self.run_recognition.setFixedHeight(24)
        self.run_recognition.setToolTip("Analyze the selected media with FFprobe, BLIP, beat/VAD and speech tools.")
        self.run_recognition.clicked.connect(self.recognize_selected)
        recognition_row.addWidget(self.run_recognition, 1)
        rec_layout.addLayout(recognition_row)

        semantic_controls = QHBoxLayout()
        semantic_controls.setContentsMargins(0, 0, 0, 0)
        semantic_controls.setSpacing(3)
        self.semantic_auto_check = QCheckBox("AUTO AI ENRICH")
        self.semantic_auto_check.setChecked(
            bool(self.design_ai_settings.auto_semantic_enrichment)
        )
        self.semantic_auto_check.setToolTip(
            "After raw analysis completes, send its bounded evidence to the provider/model saved by Design. "
            "Online GPT sends captions/transcripts to the configured remote endpoint."
        )
        self.semantic_auto_check.toggled.connect(self._semantic_auto_changed)
        semantic_controls.addWidget(self.semantic_auto_check, 1)
        self.semantic_enrich_button = QPushButton("AI ENRICH")
        self.semantic_enrich_button.setFixedHeight(24)
        self.semantic_enrich_button.setToolTip(
            "Create a detailed, evidence-bound semantic analysis for the selected media."
        )
        self.semantic_enrich_button.clicked.connect(self.enrich_selected_media)
        self.semantic_enrich_button.setEnabled(False)
        semantic_controls.addWidget(self.semantic_enrich_button)
        self.cancel_recognition_button = QPushButton("CANCEL ANALYSIS")
        self.cancel_recognition_button.setFixedHeight(24)
        self.cancel_recognition_button.setToolTip("Cancel recognition or AI enrichment for the selected media.")
        self.cancel_recognition_button.clicked.connect(self.cancel_selected_analysis)
        semantic_controls.addWidget(self.cancel_recognition_button)
        rec_layout.addLayout(semantic_controls)
        right.addWidget(recognition_box)
        right.setSizes([360, 330])
        upper.addWidget(right)
        upper.setSizes([430, 800, 390])

        timeline_panel = QWidget()
        timeline_layout = QVBoxLayout(timeline_panel)
        timeline_layout.setContentsMargins(5, 2, 5, 5)
        timeline_layout.setSpacing(2)
        timeline_header_bar = QWidget()
        timeline_header_bar.setObjectName("directorTimelineHeader")
        timeline_header_bar.setFixedHeight(20)
        timeline_header_bar.setStyleSheet(
            "#directorTimelineHeader { background:#202327; border-bottom:1px solid #08090a; } "
            "QPushButton { padding:0 5px; min-height:18px; max-height:18px; } "
            "QLabel { font-size:10px; }"
        )
        timeline_head = QHBoxLayout(timeline_header_bar)
        timeline_head.setContentsMargins(2, 0, 2, 0)
        timeline_head.setSpacing(3)
        timeline_head.addWidget(QLabel("DIRECTOR CUT TIMELINE"))
        hint = QLabel("Drag from Media Pool · trim either edge · Delete removes clip")
        hint.setStyleSheet("color:#707780;")
        timeline_head.addWidget(hint)
        add_video_track = QPushButton("+ V TRACK")
        add_video_track.clicked.connect(self.add_video_track)
        timeline_head.addWidget(add_video_track)
        add_audio_track = QPushButton("+ A TRACK")
        add_audio_track.clicked.connect(self.add_audio_track)
        timeline_head.addWidget(add_audio_track)
        timeline_head.addWidget(QLabel("ZOOM"))
        zoom_out = QPushButton("-")
        zoom_out.setToolTip("Zoom out timeline")
        zoom_out.setFixedWidth(28)
        timeline_head.addWidget(zoom_out)
        self.timeline_zoom = QSlider(Qt.Horizontal)
        self.timeline_zoom.setObjectName("timelineZoom")
        self.timeline_zoom.setRange(20, 240)
        self.timeline_zoom.setValue(70)
        self.timeline_zoom.setFixedWidth(130)
        self.timeline_zoom.setToolTip("Timeline zoom · Ctrl + mouse wheel")
        timeline_head.addWidget(self.timeline_zoom)
        zoom_in = QPushButton("+")
        zoom_in.setToolTip("Zoom in timeline")
        zoom_in.setFixedWidth(28)
        timeline_head.addWidget(zoom_in)
        self.timeline_zoom_label = QLabel("100%")
        self.timeline_zoom_label.setMinimumWidth(42)
        timeline_head.addWidget(self.timeline_zoom_label)
        self.timeline_snap_label = QLabel("SNAP 0.5s")
        self.timeline_snap_label.setToolTip("All timeline edits snap to half-second grid lines")
        self.timeline_snap_label.setStyleSheet(
            "color:#75d7e8; background:#16343a; border:1px solid #286775; padding:1px 5px;"
        )
        timeline_head.addWidget(self.timeline_snap_label)
        self.playhead_label = QLabel("PLAYHEAD 00:00.000")
        timeline_head.addStretch()
        timeline_head.addWidget(self.playhead_label)
        timeline_layout.addWidget(timeline_header_bar)

        self.timeline_body_splitter = QSplitter(Qt.Horizontal)
        self.timeline_body_splitter.setChildrenCollapsible(False)
        self.timeline_body_splitter.setHandleWidth(3)
        self.timeline_tool_scroll = QScrollArea()
        self.timeline_tool_scroll.setObjectName("timelineToolScroll")
        self.timeline_tool_scroll.setWidgetResizable(True)
        self.timeline_tool_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.timeline_tool_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Keep the palette wide enough to show every tool label.  The splitter
        # remains resizable, but it can no longer collapse back to icon-only
        # mode and hide names such as Selection or Transition.
        self.timeline_tool_scroll.setMinimumWidth(118)
        self.timeline_tool_scroll.setMaximumWidth(220)
        self.timeline_tool_scroll.setToolTip("Timeline tools · use the mouse wheel to scroll up or down")
        self.timeline_tool_scroll.setStyleSheet(
            "#timelineToolScroll { background:#24272b; border:1px solid #090a0c; } "
            "QScrollBar:vertical { width:6px; background:#191b1f; } "
            "QScrollBar::handle:vertical { background:#59616b; min-height:24px; border-radius:3px; }"
        )
        self.timeline_tool_palette = QFrame()
        self.timeline_tool_palette.setObjectName("timelineToolPalette")
        self.timeline_tool_palette.setStyleSheet(
            "#timelineToolPalette { background:#24272b; border:1px solid #090a0c; } "
            "QToolButton { border:1px solid transparent; border-radius:2px; } "
            "QToolButton:hover { background:#343940; border-color:#545c65; } "
            "QToolButton:checked { background:#101820; border-color:#1488a2; }"
        )
        tool_layout = QVBoxLayout(self.timeline_tool_palette)
        tool_layout.setContentsMargins(3, 5, 3, 5)
        tool_layout.setSpacing(4)
        self.timeline_tool_buttons: dict[str, QToolButton] = {}
        for mode, icon_name, label, tooltip in (
            ("selection", "selection", "Selection", "Selection Tool · select/move clips and drag Program Monitor text"),
            ("hand", "hand", "Hand", "Hand Tool · drag the Timeline without moving clips or playhead"),
            ("razor", "razor", "Razor", "Razor Tool · add a shot cut or split text/director blocks at the clicked time"),
            ("shot", "shot", "Shot", "Shot Tool · drag a time range on a visual track to create a structured Shot Block"),
            (
                "type", "type", "Type",
                "Type Tool · create an independent clip; On-screen Text uses V tracks, while Dialogue/Voice-over/Lyrics use dedicated A tracks",
            ),
            ("prompt", "prompt", "Prompt", "Prompt Tool · click a media clip to add a local director instruction"),
            ("transition", "transition", "Transition", "Transition Tool · add a transition preset at a cut point"),
            ("marker", "marker", "Marker", "Marker Tool · add SFX, music, beat, camera, or ending cues"),
        ):
            button = QToolButton()
            button.setText(label)
            button.setIcon(editor_icon(icon_name, "#2fb7ff" if mode == "selection" else "#d8dde3"))
            button.setIconSize(QSize(22, 22))
            button.setMinimumSize(35, 34)
            button.setMaximumHeight(34)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            button.setCheckable(True)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda _checked=False, value=mode: self.set_timeline_tool(value))
            self.timeline_tool_buttons[mode] = button
            tool_layout.addWidget(button)
        scroll_width = self.timeline_tool_scroll.verticalScrollBar().sizeHint().width()
        layout_width = tool_layout.contentsMargins().left() + tool_layout.contentsMargins().right()
        widest_button = max(
            button.sizeHint().width() for button in self.timeline_tool_buttons.values()
        )
        self.timeline_tools_minimum_width = max(
            118, widest_button + layout_width + scroll_width + 8
        )
        self.timeline_tool_scroll.setMinimumWidth(self.timeline_tools_minimum_width)
        self.timeline_tool_palette.setMinimumWidth(
            self.timeline_tools_minimum_width - scroll_width - 4
        )
        self.timeline_tool_buttons["selection"].setChecked(True)
        tool_layout.addStretch()
        self.timeline_tool_palette.setMinimumHeight(len(self.timeline_tool_buttons) * 38 + 10)
        self.timeline_tool_scroll.setWidget(self.timeline_tool_palette)
        self.timeline_body_splitter.addWidget(self.timeline_tool_scroll)

        self.track_header_scroll = QScrollArea()
        self.track_header_scroll.setObjectName("trackHeaderScroll")
        self.track_header_scroll.setWidgetResizable(True)
        self.track_header_scroll.setFixedWidth(222)
        self.track_header_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.track_header_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.track_header_scroll.setStyleSheet(
            "#trackHeaderScroll { background:#1b1e22; border:1px solid #090b0d; }"
        )
        self.track_header_container = QWidget()
        self.track_header_layout = QVBoxLayout(self.track_header_container)
        self.track_header_layout.setContentsMargins(0, 0, 0, 0)
        self.track_header_layout.setSpacing(0)
        self.track_header_scroll.setWidget(self.track_header_container)
        self.track_header_widgets: dict[str, TrackHeaderWidget] = {}
        self.timeline_body_splitter.addWidget(self.track_header_scroll)

        self.timeline = TimelineView()
        self.timeline.set_tracks(self.tracks)
        self.timeline.set_text_layers(self.text_layers)
        self.timeline.set_director_cues(self.director_cues)
        self.timeline.asset_selected.connect(self.select_timeline_asset)
        self.timeline.asset_changed.connect(self.asset_timing_changed)
        self.timeline.asset_edit_committed.connect(self.commit_asset_edit)
        self.timeline.clip_instance_created.connect(self.add_timeline_clip_instance)
        self.timeline.remove_requested.connect(self.remove_timeline_asset)
        self.timeline.empty_slot_dropped.connect(self.reject_empty_timeline_slot)
        self.timeline.playhead_changed.connect(self.playhead_changed)
        self.timeline.track_selected.connect(self.select_track)
        self.timeline.track_property_requested.connect(self.change_track_property)
        self.timeline.zoom_changed.connect(self._sync_timeline_zoom)
        self.timeline.prompt_requested.connect(self.edit_clip_prompt)
        self.timeline.type_targeted.connect(self._type_tool_targeted)
        self.timeline.text_create_requested.connect(self.create_text_layer)
        self.timeline.text_selected.connect(self.select_text_layer)
        self.timeline.text_edit_requested.connect(self.edit_text_layer)
        self.timeline.text_edit_committed.connect(self.commit_text_layer_edit)
        self.timeline.text_remove_requested.connect(self.remove_text_layer)
        self.timeline.cue_create_requested.connect(self.create_director_cue)
        self.timeline.shot_range_requested.connect(self.create_shot_range)
        self.timeline.cue_edit_requested.connect(self.edit_director_cue)
        self.timeline.cue_remove_requested.connect(self.remove_director_cue)
        self.timeline.razor_asset_requested.connect(self.razor_asset)
        self.timeline.razor_text_requested.connect(self.razor_text_layer)
        self.timeline.razor_cue_requested.connect(self.razor_director_cue)
        self.timeline_zoom.valueChanged.connect(lambda value: self.timeline.set_zoom(value))
        zoom_out.clicked.connect(lambda: self.timeline_zoom.setValue(self.timeline_zoom.value() - 10))
        zoom_in.clicked.connect(lambda: self.timeline_zoom.setValue(self.timeline_zoom.value() + 10))
        self.timeline.verticalScrollBar().valueChanged.connect(
            self.track_header_scroll.verticalScrollBar().setValue
        )
        self.track_header_scroll.verticalScrollBar().valueChanged.connect(
            self.timeline.verticalScrollBar().setValue
        )
        self.timeline.verticalScrollBar().rangeChanged.connect(
            lambda _minimum, _maximum: QTimer.singleShot(
                0, self._sync_timeline_track_scrolls
            )
        )
        self.track_header_scroll.verticalScrollBar().rangeChanged.connect(
            lambda _minimum, _maximum: QTimer.singleShot(
                0, self._sync_timeline_track_scrolls
            )
        )
        self._rebuild_track_headers()
        self.timeline_body_splitter.addWidget(self.timeline)
        self.timeline_body_splitter.setStretchFactor(0, 0)
        self.timeline_body_splitter.setStretchFactor(1, 0)
        self.timeline_body_splitter.setStretchFactor(2, 1)
        self.timeline_body_splitter.setSizes(
            [self.timeline_tools_minimum_width, 222, 1100]
        )
        self.timeline_body_splitter.splitterMoved.connect(
            lambda _position, _index: self._refresh_timeline_tool_labels()
        )
        self._refresh_timeline_tool_labels()
        timeline_layout.addWidget(self.timeline_body_splitter, 1)
        root.addWidget(upper)
        root.addWidget(timeline_panel)
        root.setSizes([610, 330])
        self.setCentralWidget(root)

    def _design_context(self) -> dict:
        scan = self.scan
        media: list[dict] = []
        loaded_counts = {kind: 0 for kind in ("image", "video", "audio")}
        if scan:
            for asset in scan.assets:
                local_path = str(asset.local_path or "").strip()
                locally_available = bool(local_path and Path(local_path).is_file())
                if not locally_available:
                    continue
                loaded_counts[asset.media_type] += 1
                caption = self._blip_caption_for_asset(asset)
                raw_analysis = str(asset.recognition or "").strip()
                if len(raw_analysis) > 5000:
                    raw_analysis = (
                        raw_analysis[:3500]
                        + "\n...[raw analysis truncated]...\n"
                        + raw_analysis[-1500:]
                    )
                semantic_status = self._semantic_asset_status_key(asset)
                semantic_analysis = (
                    str(asset.semantic_enrichment or "").strip()
                    if semantic_status == "ready"
                    else ""
                )
                if len(semantic_analysis) > 6000:
                    semantic_analysis = (
                        semantic_analysis[:4500]
                        + "\n...[semantic enrichment truncated]...\n"
                        + semantic_analysis[-1500:]
                    )
                analysis = raw_analysis
                if semantic_analysis:
                    analysis += (
                        "\n\nAI SEMANTIC ENRICHMENT (derived guidance; not raw evidence)\n"
                        + semantic_analysis
                    )
                analysis_ready = bool(
                    caption
                    or re.search(
                        r"BLIP (?:video frame|concept analysis)|WHISPER TRANSCRIPT|\bVAD\b|\bBEAT\b",
                        raw_analysis,
                        flags=re.I,
                    )
                )
                timeline_uses = [
                    {
                        "clip_id": item.clip_id or f"source-{asset.node_id}",
                        "track": item.timeline_track_id,
                        "start_seconds": float(item.start_seconds),
                        "end_seconds": float(item.end_seconds),
                        "instruction": item.clip_prompt,
                    }
                    for item in scan.timeline_assets()
                    if item.timeline_placed
                    and (item.source_node_id or item.node_id) == asset.node_id
                ]
                media.append({
                    "media_id": media_shortcut(asset),
                    "node_id": asset.node_id,
                    "media_type": asset.media_type,
                    "type": asset.media_type,
                    "filename": Path(local_path).name,
                    "loaded": True,
                    "locally_available": True,
                    "timeline_placed": bool(timeline_uses),
                    "timeline_track_id": asset.timeline_track_id,
                    "start_seconds": float(asset.start_seconds),
                    "end_seconds": float(asset.end_seconds),
                    "source_duration_seconds": float(asset.source_duration_seconds),
                    "caption": caption,
                    "clip_prompt": asset.clip_prompt,
                    "raw_analysis_summary": raw_analysis,
                    "semantic_enrichment": semantic_analysis,
                    "semantic_enrichment_status": semantic_status,
                    "analysis_summary": analysis,
                    "analysis_status": "ready" if analysis_ready else "pending",
                    "timeline_uses": timeline_uses,
                })
        # Logical assets are not globally capped.  Keep a high schema guard for
        # malformed plans; the real 9/3/3 rule is enforced independently for
        # every compiled Segment.
        total_capacity = {"image": 10000, "video": 10000, "audio": 10000}
        physical_segment_capacity = (
            dict(scan.counts) if scan else {"image": 9, "video": 3, "audio": 3}
        )
        free_capacity = {
            kind: max(0, int(total_capacity.get(kind, 0)) - loaded_counts[kind])
            for kind in loaded_counts
        }
        default_profile = self.profiles[DEFAULT_SKILL]
        special_key = self.special_combo.currentData()
        special_profile = (
            None if special_key == NONE_SPECIAL else self.profiles.get(special_key)
        )
        standalone_special = bool(special_profile and special_profile.standalone)
        return {
            "current_duration_seconds": scan.duration_seconds if scan else 5.0,
            "comfyui_server": self.server_url.text().strip(),
            "comfyui_history_poll_interval": self.render_settings.history_poll_interval,
            "comfyui_generation_timeout": self.render_settings.generation_timeout,
            "comfyui_http_timeout": self.render_settings.http_request_timeout,
            "dialogue_tts_engine": self.render_settings.dialogue_tts_engine,
            "music_mode": self.render_settings.music_mode,
            "aspect_ratio": self.aspect_ratio_combo.currentData(),
            "available_tracks": [track.track_id for track in self.tracks],
            "media_capacity": total_capacity,
            "physical_segment_capacity": physical_segment_capacity,
            "loaded_media_counts": loaded_counts,
            "available_new_media_capacity": free_capacity,
            "existing_media": media,
            "existing_shots_and_cues": [asdict(cue) for cue in self.director_cues],
            "existing_text_layers": [asdict(layer) for layer in self.text_layers],
            "current_prompt_fields": {
                name: getattr(self.prompt_panel, name).toPlainText()
                for name in (
                    "brief", "style", "shots", "dialogue", "transition", "ending",
                    "constraints", "soundscape", "music",
                )
            },
            "timeline_snap_seconds": TIMELINE_SNAP_SECONDS,
            "h3_prompt_sections": [
                "creative_brief", "global_visual_style", "shots", "dialogue",
                "transition_language", "ending_final_hold", "constraints",
                "overall_soundscape", "non_diegetic_music",
            ],
            "bound_h3_skills": {
                "binding_mode": (
                    "standalone_special" if standalone_special else "default_plus_special"
                ),
                "default": None if standalone_special else {
                    "key": default_profile.key,
                    "instruction": default_profile.instruction,
                    "ref2va_format_guide": default_profile.h3_reference_guide,
                },
                "special": None if special_profile is None else {
                    "key": special_profile.key,
                    "instruction": special_profile.instruction,
                    "standalone": special_profile.standalone,
                    "design_requirement_template": (
                        special_profile.design_requirement_template
                    ),
                },
            },
        }

    def open_design_page(self) -> None:
        if not self.scan:
            QMessageBox.information(self, "AI Design", "Load a ComfyUI API workflow first.")
            return
        dialog = DesignPageDialog(
            self.runtime,
            self._design_context(),
            self._design_context()["media_capacity"],
            self,
            context_provider=self._design_context,
        )
        if self.semantic_openai_api_key and dialog.provider_combo.currentData() == "openai":
            dialog.api_key_edit.setText(self.semantic_openai_api_key)
        self.active_design_apply_dialog = dialog
        dialog.apply_requested.connect(self.apply_ai_design)
        dialog.cleanup_requested.connect(self.start_design_cleanup)
        dialog.exec()
        if dialog.provider_combo.currentData() == "openai":
            self.semantic_openai_api_key = dialog.api_key_edit.text().strip()
        if self.active_design_apply_dialog is dialog:
            self.active_design_apply_dialog = None
        dialog.deleteLater()
        # Design owns the shared provider/model settings.  Reflect any changes
        # immediately in the normal Media Pool semantic controls.
        self.design_ai_settings = load_design_settings(DESIGN_SETTINGS_ENV)
        self.semantic_auto_check.blockSignals(True)
        self.semantic_auto_check.setChecked(
            bool(self.design_ai_settings.auto_semantic_enrichment)
        )
        self.semantic_auto_check.blockSignals(False)
        self._refresh_recognition_inspector()

    def _design_workspace_state(self) -> dict:
        if not self.scan:
            return {}
        duration_nodes = {
            node_id: (node.get("inputs") or {}).get("value")
            for node_id, node in self.scan.nodes.items()
            if node.get("class_type") == "PrimitiveFloat"
            and "duration" in str((node.get("_meta") or {}).get("title", "")).lower()
        }
        prompt_names = (
            "brief", "style", "transition", "constraints", "soundscape", "music"
        )
        return {
            "duration_seconds": self.scan.duration_seconds,
            "storyboard_target_duration_seconds": self.storyboard_target_duration_seconds,
            "storyboard_view_mode": self.storyboard_view_mode,
            "smart_cut_last_plan": deepcopy(self.smart_cut_last_plan),
            "production_strategy": self.production_strategy,
            "production_batch_seconds": self.production_batch_seconds,
            "incremental_production": {
                "approved_horizon_seconds": self.incremental_approved_horizon,
                "pending_start_seconds": self.incremental_pending_start,
                "pending_end_seconds": self.incremental_pending_end,
                "phase": self.incremental_batch_phase,
                "preview_seed": self.preview_seed,
                "preview_ready": self.preview_ready,
            },
            "duration_nodes": duration_nodes,
            # AI Design may create V4/V5... and A4/A5... dynamically.  Track
            # geometry is part of the workspace state: without it Undo/Redo
            # can restore clips whose real V-track rows exist only in the
            # Timeline scene while the Track Header still shows V3/V2/V1.
            "tracks": [asdict(track) for track in self.tracks],
            "assets": {asset.node_id: asdict(asset) for asset in self.scan.assets},
            "timeline_clips": [
                {
                    key: value
                    for key, value in asdict(clip).items()
                    if not key.startswith("request_")
                }
                for clip in self.scan.timeline_clips
            ],
            "text_layers": [asdict(layer) for layer in self.text_layers],
            "authored_text_requirements": deepcopy(
                self.authored_text_requirements
            ),
            "director_cues": [asdict(cue) for cue in self.director_cues],
            "prompt": {
                name: getattr(self.prompt_panel, name).toPlainText() for name in prompt_names
            },
            "work_area": [self.clip_start.value(), self.clip_end.value()],
            "preview_paths": {key: str(value) for key, value in self.preview_paths.items()},
            "render_dirty_segment_ids": sorted(self.render_dirty_segment_ids),
        }

    def _restore_design_workspace_state(self, state: dict) -> None:
        if not self.scan or not state:
            return
        duration = max(0.5, float(state["duration_seconds"]))
        self.storyboard_target_duration_seconds = max(
            0.5,
            float(state.get("storyboard_target_duration_seconds", duration)),
        )
        saved_view_mode = str(
            state.get("storyboard_view_mode", self.storyboard_view_mode)
        )
        self.storyboard_view_mode = (
            saved_view_mode
            if saved_view_mode in StoryboardBlockList.DISPLAY_MODES
            else "large_icons"
        )
        self.smart_cut_last_plan = deepcopy(state.get("smart_cut_last_plan") or {})
        self.production_strategy = str(
            state.get("production_strategy") or "full_range"
        )
        if self.production_strategy not in {"full_range", "incremental"}:
            self.production_strategy = "full_range"
        self.production_batch_seconds = max(
            16.0, float(state.get("production_batch_seconds", 30.0))
        )
        incremental = state.get("incremental_production") or {}
        self.incremental_approved_horizon = max(
            0.0, float(incremental.get("approved_horizon_seconds", 0.0))
        )
        self.incremental_pending_start = max(
            0.0, float(incremental.get("pending_start_seconds", 0.0))
        )
        self.incremental_pending_end = max(
            self.incremental_pending_start,
            float(incremental.get("pending_end_seconds", 0.0)),
        )
        self.incremental_batch_phase = str(incremental.get("phase") or "")
        raw_preview_seed = incremental.get("preview_seed")
        self.preview_seed = int(raw_preview_seed) if raw_preview_seed is not None else None
        self.preview_ready = bool(incremental.get("preview_ready", False))
        track_rows = state.get("tracks") or []
        if track_rows:
            self.tracks = [TimelineTrack(**values) for values in track_rows]
        self.scan.duration_seconds = duration
        for node_id, value in state.get("duration_nodes", {}).items():
            if node_id in self.scan.nodes:
                self.scan.nodes[node_id].setdefault("inputs", {})["value"] = value
        asset_states = state.get("assets", {})
        self.scan.assets[:] = [
            asset for asset in self.scan.assets
            if not asset.is_virtual or asset.node_id in asset_states
        ]
        existing_ids = {asset.node_id for asset in self.scan.assets}
        for node_id, values in asset_states.items():
            if node_id in existing_ids or not bool(values.get("is_virtual")):
                continue
            created = create_virtual_media_asset(
                self.scan,
                str(values.get("media_type", "")),
                reference_id=str(values.get("reference_id", "")),
                node_id=str(node_id),
            )
            existing_ids.add(created.node_id)
        for asset in self.scan.assets:
            values = asset_states.get(asset.node_id)
            if not values:
                continue
            for name, value in values.items():
                setattr(asset, name, value)
            input_name = {"image": "image", "video": "file", "audio": "audio"}[asset.media_type]
            if asset.node_id in self.scan.nodes:
                self.scan.nodes[asset.node_id].setdefault("inputs", {})[input_name] = asset.filename
        self.scan.timeline_clips = [
            MediaAsset(**values) for values in state.get("timeline_clips", [])
        ]
        self._sync_timeline_clip_sources()
        self.text_layers = [
            text_layer_from_mapping(values)
            for values in state.get("text_layers", [])
            if isinstance(values, dict)
        ]
        self._normalize_text_layer_tracks()
        self.authored_text_requirements = deepcopy(
            state.get("authored_text_requirements") or []
        )
        self.director_cues = [DirectorCue(**values) for values in state.get("director_cues", [])]
        self.preview_paths = {
            key: Path(value) for key, value in state.get("preview_paths", {}).items()
            if Path(value).is_file()
        }
        self.clip_start.blockSignals(True)
        self.clip_end.blockSignals(True)
        self.clip_start.setRange(0.0, duration)
        self.clip_end.setRange(0.01, MAX_MANUAL_TIMELINE_SECONDS)
        work_area = state.get("work_area", [0.0, duration])
        self.clip_start.setValue(min(duration, float(work_area[0])))
        self.clip_end.setValue(max(0.01, float(work_area[1])))
        self.clip_start.blockSignals(False)
        self.clip_end.blockSignals(False)
        self.asset_start.setRange(0.0, duration)
        self.asset_end.setRange(0.0, duration)
        self.position_slider.setRange(0, max(1, round(duration * 1000)))
        if hasattr(self, "storyboard_target_spin"):
            self.storyboard_target_spin.blockSignals(True)
            self.storyboard_target_spin.setValue(
                self.storyboard_target_duration_seconds
            )
            self.storyboard_target_spin.blockSignals(False)
            self._refresh_storyboard_trim_controls()
        for name, value in state.get("prompt", {}).items():
            field = getattr(self.prompt_panel, name, None)
            if isinstance(field, QPlainTextEdit):
                field.setPlainText(str(value))
        self.timeline.set_workflow(self.scan)
        self.timeline.set_tracks(self.tracks)
        # Keep the fixed Track Header pane and the QGraphics Timeline on the
        # same dynamic track model after Apply, Undo and Redo.
        self._rebuild_track_headers()
        self.timeline.set_text_layers(self.text_layers)
        self.timeline.set_director_cues(self.director_cues)
        self._rebuild_media_cards()
        for asset in self.scan.assets:
            card = self.cards.get(asset.node_id)
            if not card:
                continue
            preview = self.preview_paths.get(asset.node_id)
            card.set_preview(QPixmap(str(preview)) if preview and preview.is_file() else None)
        self.playhead_seconds = min(self.playhead_seconds, duration)
        self.timeline.set_playhead(self.playhead_seconds)
        self._sync_prompt_panel_from_timeline()
        self.refresh_activation()
        self.render_timeline_at(self.playhead_seconds, force_seek=True)
        strategy_index = self.production_strategy_combo.findData(
            self.production_strategy
        )
        self.production_strategy_combo.blockSignals(True)
        self.production_strategy_combo.setCurrentIndex(max(0, strategy_index))
        self.production_strategy_combo.blockSignals(False)
        self.production_batch_spin.blockSignals(True)
        self.production_batch_spin.setValue(self.production_batch_seconds)
        self.production_batch_spin.blockSignals(False)
        self.accept_preview_button.setEnabled(
            self.preview_ready and self.preview_seed is not None
        )
        self.reject_preview_button.setEnabled(
            self.preview_ready and self.preview_seed is not None
        )
        self._refresh_incremental_controls()
        # Prompt/media widgets emit conservative dirty signals while an
        # Undo/Redo snapshot is restored. The snapshot's audited Segment set
        # is authoritative and reinstated only after all UI refreshes finish.
        self.render_dirty_segment_ids = {
            str(value)
            for value in state.get("render_dirty_segment_ids", [])
            if str(value).strip()
        }
        self.render_runtime_status.clear()
        self._refresh_render_status_bar()

    def _set_design_duration(self, duration: float) -> None:
        if not self.scan:
            return
        self.scan.duration_seconds = duration
        for node in self.scan.nodes.values():
            if (
                node.get("class_type") == "PrimitiveFloat"
                and "duration" in str((node.get("_meta") or {}).get("title", "")).lower()
            ):
                node.setdefault("inputs", {})["value"] = duration
        self.clip_start.setRange(0.0, duration)
        self.clip_end.setRange(0.01, MAX_MANUAL_TIMELINE_SECONDS)
        self.clip_start.setValue(0.0)
        self.clip_end.setValue(duration)
        self.asset_start.setRange(0.0, duration)
        self.asset_end.setRange(0.0, duration)
        self.position_slider.setRange(0, max(1, round(duration * 1000)))
        self.timeline.set_duration(duration)
        self._refresh_render_status_bar()
        self._refresh_storyboard_trim_controls()
        self.incremental_approved_horizon = min(
            duration, self.incremental_approved_horizon
        )
        self.incremental_pending_start = min(
            duration, self.incremental_pending_start
        )
        self.incremental_pending_end = min(
            duration, max(self.incremental_pending_start, self.incremental_pending_end)
        )
        self._refresh_incremental_controls()

    def _design_track(self, track_id: str, kind: str) -> TimelineTrack:
        normalized = str(track_id or "").strip().upper()
        prefix = "A" if kind == "audio" else "V"
        match = re.fullmatch(rf"{prefix}(\d+)", normalized)
        if match:
            requested_number = min(16, max(1, int(match.group(1))))
            while self._next_track_number(prefix) <= requested_number:
                number = self._next_track_number(prefix)
                color = "#258a70" if kind == "audio" else "#3978ba"
                created = TimelineTrack(
                    f"{prefix}{number}", f"{prefix}{number}", kind, color
                )
                if kind == "audio":
                    self.tracks.append(created)
                else:
                    first_visual = next(
                        (index for index, item in enumerate(self.tracks) if item.kind == "visual"),
                        0,
                    )
                    self.tracks.insert(first_visual, created)
            normalized = f"{prefix}{requested_number}"
        track = next(
            (item for item in self.tracks if item.track_id == normalized and item.kind == kind),
            None,
        )
        if track:
            return track
        preferred = "A1" if kind == "audio" else "V1"
        return next(
            (item for item in self.tracks if item.track_id == preferred and item.kind == kind),
            next(item for item in self.tracks if item.kind == kind),
        )

    def _apply_ai_design_direct(self, plan: dict, materials: list[dict], replace: bool) -> list[str]:
        if not self.scan:
            return ["No workflow loaded"]
        duration = float(plan["duration_seconds"])
        target_duration = float(
            plan.get("_speech_timing_base_duration", duration) or duration
        )
        self.storyboard_target_duration_seconds = min(
            duration, max(0.5, target_duration)
        )
        if hasattr(self, "storyboard_target_spin"):
            self.storyboard_target_spin.blockSignals(True)
            self.storyboard_target_spin.setValue(
                self.storyboard_target_duration_seconds
            )
            self.storyboard_target_spin.blockSignals(False)
        self._set_design_duration(duration)
        if replace:
            # A replacement Design is a new edit decision list.  Prior final
            # files remain on disk, but no old approval horizon is claimed for
            # the new Timeline.
            self.incremental_approved_horizon = 0.0
            self.incremental_pending_start = 0.0
            self.incremental_pending_end = 0.0
            self.incremental_batch_phase = ""
            for asset in self.scan.timeline_assets():
                asset.timeline_placed = False
            self.scan.timeline_clips.clear()
            self.text_layers = []
            self.director_cues = []
            self._refresh_incremental_controls()

        required_rows = deepcopy(plan.get("_required_text_layers") or [])
        if replace:
            self.authored_text_requirements = required_rows
        else:
            identities = {
                (
                    str(item.get("role", "")),
                    round(float(item.get("start_seconds", 0.0)), 3),
                    round(float(item.get("end_seconds", 0.0)), 3),
                    str(item.get("content", "")).strip(),
                )
                for item in self.authored_text_requirements
            }
            for item in required_rows:
                identity = (
                    str(item.get("role", "")),
                    round(float(item.get("start_seconds", 0.0)), 3),
                    round(float(item.get("end_seconds", 0.0)), 3),
                    str(item.get("content", "")).strip(),
                )
                if identity not in identities:
                    self.authored_text_requirements.append(item)
                    identities.add(identity)

        warnings: list[str] = [
            str(item) for item in plan.get("design_warnings") or []
            if str(item).startswith(SPEECH_TIMELINE_REMINDER_PREFIX)
        ]
        used_nodes: set[str] = set()
        visual_occupancy: dict[str, list[tuple[float, float]]] = {}

        def place_asset(source: MediaAsset, request: dict, prompt_key: str) -> MediaAsset:
            asset = source
            if source.timeline_placed:
                asset = deepcopy(source)
                asset.clip_id = f"clip-{secrets.token_hex(8)}"
                asset.source_node_id = source.node_id
                asset.clip_prompt = ""
                self.scan.timeline_clips.append(asset)
            kind = "audio" if source.media_type == "audio" else "visual"
            track = self._design_track(request.get("track", ""), kind)
            request_start = float(request["start_seconds"])
            request_end = float(request["end_seconds"])
            if kind == "visual" and any(
                start < request_end and end > request_start
                for start, end in visual_occupancy.get(track.track_id, [])
            ):
                available = sorted(
                    (item for item in self.tracks if item.kind == "visual"),
                    key=lambda item: int(re.sub(r"\D", "", item.track_id) or 999),
                )
                available_track = next(
                    (
                        item for item in available
                        if not any(
                            start < request_end and end > request_start
                            for start, end in visual_occupancy.get(item.track_id, [])
                        )
                    ),
                    None,
                )
                track = available_track or self._design_track(
                    f"V{self._next_track_number('V')}", "visual"
                )
            if kind == "visual":
                visual_occupancy.setdefault(track.track_id, []).append(
                    (request_start, request_end)
                )
            asset.timeline_placed = True
            asset.timeline_track_id = track.track_id
            asset.timeline_lane = self.tracks.index(track)
            asset.start_seconds = request_start
            asset.end_seconds = request_end
            asset.activation_mode = "auto"
            direction = str(request.get(prompt_key, "")).strip()
            if prompt_key == "instruction" and direction:
                asset.clip_prompt = direction
            elif prompt_key == "prompt":
                asset.clip_prompt = direction
            asset.monitor_visible = (
                asset.media_type == "audio"
                or request.get("usage", "h3_reference") == "timeline_visual"
            )
            return asset

        assets_by_media_id = {
            media_shortcut(asset).upper(): asset for asset in self.scan.assets
        }
        all_reuse_rows = [dict(item) for item in plan.get("existing_media_uses") or []]
        reuse_rows = [
            item for item in all_reuse_rows
            if not is_analysis_only_media_use(item)
        ]
        reused_node_ids = {
            assets_by_media_id[media_id].node_id
            for item in all_reuse_rows
            if (media_id := str(item.get("media_id", "")).upper()) in assets_by_media_id
        }
        if reused_node_ids:
            self.scan.timeline_clips[:] = [
                clip for clip in self.scan.timeline_clips
                if (clip.source_node_id or clip.node_id) not in reused_node_ids
            ]
            for source in self.scan.assets:
                if source.node_id in reused_node_ids:
                    source.timeline_placed = False
        if not replace:
            for asset in self.scan.assets:
                if not asset.timeline_placed or asset.node_id in reused_node_ids:
                    continue
                used_nodes.add(asset.node_id)
                if asset.media_type != "audio":
                    visual_occupancy.setdefault(asset.timeline_track_id, []).append(
                        (float(asset.start_seconds), float(asset.end_seconds))
                    )

        # Existing Media Pool assets are bound by their stable P/V/A id.  They
        # are never copied, reassigned or re-analysed during Apply.
        for use in reuse_rows:
            media_id = str(use.get("media_id", "")).upper()
            asset = assets_by_media_id.get(media_id)
            if asset is None:
                warnings.append(f"Media Pool {media_id or '?'} no longer exists; reuse skipped")
                continue
            if asset.media_type != use.get("media_type"):
                warnings.append(
                    f"Media Pool {media_id} is {asset.media_type}, not {use.get('media_type')}; reuse skipped"
                )
                continue
            local_path = str(asset.local_path or "").strip()
            if not local_path or not Path(local_path).is_file():
                warnings.append(f"Media Pool {media_id} is not locally available; reuse skipped")
                continue
            used_nodes.add(asset.node_id)
            place_asset(asset, use, "instruction")

        for request in materials:
            candidates = [
                asset for asset in self.scan.assets
                if asset.media_type == request["media_type"]
                and asset.node_id not in used_nodes
                and not str(asset.local_path or "").strip()
                and (replace or not asset.timeline_placed)
            ]
            preferred_media_id = str(
                request.get("preferred_media_id", "")
            ).strip().upper()
            if preferred_media_id:
                preferred = assets_by_media_id.get(preferred_media_id)
                if preferred in candidates:
                    candidates = [preferred] + [
                        asset for asset in candidates if asset is not preferred
                    ]
            if not candidates:
                virtual = create_virtual_media_asset(
                    self.scan,
                    str(request["media_type"]),
                    reference_id=(preferred_media_id or None),
                )
                self._append_media_card(virtual)
                assets_by_media_id[stable_reference_id(virtual).upper()] = virtual
                candidates = [virtual]
            asset = candidates[0]
            used_nodes.add(asset.node_id)
            assign_local_media(self.scan, asset, request["local_path"])
            self._show_immediate_image_preview(asset)
            place_asset(asset, request, "prompt")
            if request.get("generated_by_tts"):
                source_heading = "AI DESIGN AUTHORED SPEECH TTS\n"
            elif request.get("generated_by_comfyui"):
                source_heading = "AI DESIGN GENERATED REFERENCE\n"
            else:
                source_heading = "AI DESIGN PLACEHOLDER\n"
            asset.recognition = (
                source_heading +
                f"Usage: {request.get('usage', 'h3_reference')}\n"
                f"Keywords: {', '.join(request.get('subject_keywords') or [])}\n"
                f"Requirement: {asset.clip_prompt}"
            )
            if request.get("tts_transcript"):
                asset.recognition += "\nAUTHORED TTS TRANSCRIPT:\n" + "\n".join(
                    f"[{float(row.get('start_seconds', 0.0)):.2f}-"
                    f"{float(row.get('end_seconds', 0.0)):.2f}] "
                    f"{row.get('speaker', 'S1')}: {row.get('content', '')}"
                    for row in request["tts_transcript"]
                )
            if request.get("tts_signature"):
                asset.recognition += "\nTTS SIGNATURE: " + str(request["tts_signature"])
            if request.get("concept_blip_caption"):
                asset.recognition += (
                    "\nBLIP concept analysis: " + str(request["concept_blip_caption"])
                )
            background_removal = request.get("background_removal") or {}
            if background_removal:
                asset.recognition += (
                    "\nAUTO BACKGROUND REMOVAL: uniform edge-connected background removed "
                    f"({round(float(background_removal.get('removed_ratio', 0.0)) * 100)}% transparent)."
                )
            preview_path = Path(request.get("preview_path", ""))
            if preview_path.is_file():
                self.preview_paths[asset.node_id] = preview_path

        self._refresh_virtual_media_header()

        for index, shot in enumerate(plan["shots"], 1):
            track = self._design_track(shot.get("track", ""), "visual")
            self.director_cues.append(DirectorCue(
                f"S{index}", "shot", shot["start_seconds"], shot["end_seconds"],
                shot["preset"], shot["additional_direction"], track.track_id,
                shot["framing"], shot["camera_angle"], shot["camera_movement"],
                shot["movement_speed"], shot["movement_amplitude"],
                shot["subject_action"], shot["environment_response"],
                continuity_state=shot.get("continuity_state", ""),
                optional_flourish=shot.get("optional_flourish", ""),
                h3_executable_action=shot.get("h3_executable_action", ""),
                h3_optional_flourish=shot.get("h3_optional_flourish", ""),
                action_budget_status=str(
                    (shot.get("action_budget") or {}).get("status", "within_budget")
                ),
                action_budget_notes=str(
                    (shot.get("action_budget") or {}).get("notes", "")
                ),
                authored_subject_action=str(
                    (shot.get("action_budget") or {}).get(
                        "original_subject_action", shot.get("subject_action", "")
                    )
                ),
                authored_environment_response=str(
                    (shot.get("action_budget") or {}).get(
                        "original_environment_response",
                        shot.get("environment_response", ""),
                    )
                ),
            ))
        for index, transition in enumerate(plan["transitions"], 1):
            start = float(transition["time_seconds"])
            self.director_cues.append(DirectorCue(
                f"X{index}", "transition", start, min(duration, start + 0.5),
                transition["preset"], transition["direction"],
            ))
        for index, marker in enumerate(plan["markers"], 1):
            start = float(marker["time_seconds"])
            self.director_cues.append(DirectorCue(
                f"M{index}", "marker", start, min(duration, start + 0.5),
                marker["preset"], marker["direction"],
            ))
        for index, item in enumerate(plan["text_layers"], 1):
            role = str(item.get("role", "on_screen_text"))
            track_kind = text_layer_track_kind(role)
            requested_track = str(item.get("track", ""))
            if track_kind == "audio" and not requested_track.upper().startswith("A"):
                requested_track = default_text_layer_track(role)
            elif track_kind == "visual" and not requested_track.upper().startswith("V"):
                requested_track = default_text_layer_track(role)
            track = self._design_track(requested_track, track_kind)
            if track.name == track.track_id or role != "on_screen_text":
                track.name = text_layer_track_name(track.track_id, role)
            # Normalization already owns the authoritative Text-to-Shot
            # relationship, including lines whose duration extended the final
            # Shot.  Preserve it instead of re-guessing at an inclusive
            # boundary where either adjacent Shot could win.
            planned_shot_id = str(item.get("shot_id", "")).strip()
            valid_shot_ids = {
                cue.cue_id for cue in self.director_cues if cue.cue_type == "shot"
            }
            if planned_shot_id in valid_shot_ids:
                shot_id = planned_shot_id
            else:
                midpoint = (item["start_seconds"] + item["end_seconds"]) / 2
                shot_id = next(
                    (
                        cue.cue_id for cue in self.director_cues
                        if cue.cue_type == "shot"
                        and cue.start_seconds <= midpoint < cue.end_seconds
                    ),
                    "",
                )
            self.text_layers.append(TextLayer(
                f"T{index}", item["content"], item["start_seconds"], item["end_seconds"],
                track.track_id, content_role=item["role"], speaker=item["speaker"],
                language=item["language"], delivery=item["delivery"],
                lip_sync=item["lip_sync"], shot_id=shot_id,
            ))
        if (
            plan.get("theme_text")
            and plan.get("theme_text_explicit_user_requested", False)
            and not any(
            layer.content_role == "on_screen_text" for layer in self.text_layers
            )
        ):
            track = self._design_track("V3", "visual")
            self.text_layers.append(TextLayer(
                f"T{len(self.text_layers) + 1}", plan["theme_text"],
                max(0.0, duration - 2.5), duration, track.track_id,
                content_role="on_screen_text",
            ))
        self.prompt_panel.brief.setPlainText(plan["creative_brief"])
        self.prompt_panel.style.setPlainText(plan["global_visual_style"])
        self.prompt_panel.constraints.setPlainText(plan["constraints"])
        self.prompt_panel.soundscape.setPlainText(plan["overall_soundscape"])
        self.prompt_panel.music.setPlainText(plan["non_diegetic_music"])
        self.prompt_panel.transition.setPlainText(
            "; ".join(
                f"{item['preset']} at {item['time_seconds']:.2f}s: {item['direction']}"
                for item in plan["transitions"]
            )
        )
        return warnings

    def _notify_design_apply_failed(
        self, message: str, *, category: str = "Workspace"
    ) -> None:
        dialog = self.active_design_apply_dialog
        if dialog is not None:
            dialog.mark_apply_failed(str(message), category=category)
        self.statusBar().showMessage(
            f"AI Design Apply stopped · {category}: {message}", 15000
        )

    def _notify_design_apply_succeeded(
        self, warnings: list[str] | None = None
    ) -> None:
        dialog = self.active_design_apply_dialog
        if dialog is not None:
            dialog.mark_apply_succeeded(warnings)

    def _commit_ai_design(
        self,
        plan: dict,
        materials: list[dict],
        replace: bool,
        before: dict,
        design_dir: Path,
        warnings: list[str] | None = None,
        timeline_tts_stale: bool = False,
    ) -> None:
        warnings = list(warnings or [])
        warnings.extend(self._apply_ai_design_direct(plan, materials, replace))
        after = self._design_workspace_state()
        self._restore_design_workspace_state(before)
        self._clear_generated_output()
        self.undo_stack.push(
            WorkspaceDesignCommand(before, after, self._restore_design_workspace_state)
        )
        workspace = self._ensure_project_workspace(project_display_name_for_plan(plan))
        self.timeline_tts_stale = bool(timeline_tts_stale)
        self._sync_shot_take_states()
        self._write_shot_state_manifests()
        self._mark_dirty()
        message = f"AI Design applied · {plan['duration_seconds']:.2f}s · {design_dir}"
        if warnings:
            message += f" · {len(warnings)} warning(s)"
        self.statusBar().showMessage(message, 12000)
        self._notify_design_apply_succeeded(warnings)

    def _start_design_tts_generation(
        self,
        plan: dict,
        materials: list[dict],
        replace: bool,
        before: dict,
        design_dir: Path,
        settings: DesignAISettings,
        warnings: list[str],
        generate_images: bool,
        tts_material: dict,
    ) -> None:
        if self.design_tts_runner and self.design_tts_runner.is_running():
            raise RuntimeError("AI Design Mandarin TTS is already running")
        if (
            self.render_settings.dialogue_tts_engine == "voxcpm2_local"
            and not self._require_voxcpm_model()
        ):
            raise RuntimeError(voxcpm_missing_message())
        if (
            self.render_settings.dialogue_tts_engine == "qwen3_tts_local"
            and not self._require_qwen3_tts_model()
        ):
            raise RuntimeError(qwen3_tts_missing_message())
        CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        job_path = CACHE_ROOT / f"design_tts_{time.time_ns()}.json"
        job_path.write_text(json.dumps({
            "output_path": tts_material["local_path"],
            "duration_seconds": plan["duration_seconds"],
            "text_layers": plan.get("_required_text_layers") or plan.get("text_layers") or [],
            "ffmpeg": str(self.runtime.ffmpeg),
            "sapi_script": str(PROJECT_ROOT / "tts_sapi.ps1"),
            "engine": self.render_settings.dialogue_tts_engine,
            "voxcpm_model": str(VOXCPM_MODEL_DIR),
            "voxcpm_device": "auto",
            "voxcpm_local_files_only": True,
            "qwen3_tts_model": str(QWEN3_TTS_MODEL_DIR),
            "qwen3_tts_runtime": str(QWEN3_TTS_RUNTIME_DIR),
            "qwen3_tts_device": "auto",
            "qwen3_tts_local_files_only": True,
        }, ensure_ascii=False), encoding="utf-8")
        self.pending_design_tts = {
            "plan": plan,
            "materials": materials,
            "replace": replace,
            "before": before,
            "design_dir": design_dir,
            "settings": settings,
            "warnings": list(warnings),
            "generate_images": bool(generate_images),
            "tts_material": tts_material,
        }
        self.design_tts_result = {}
        runner = JsonLineProcess(self, "design-mandarin-tts")
        runner.message.connect(self._design_tts_message)
        runner.finished.connect(self._design_tts_finished)
        self.design_tts_runner = runner
        self.design_button.setEnabled(False)
        self.generation_previous_monitor = self.monitor_display_stack.currentWidget()
        engine_label = {
            "voxcpm2_local": "VoxCPM2 Local",
            "qwen3_tts_local": "Qwen3-TTS Local",
            "edge_tts": "Edge TTS",
        }.get(self.render_settings.dialogue_tts_engine, "TTS")
        self.generation_overlay.start(
            f"{engine_label} · generating exact authored Mandarin speech"
        )
        self.statusBar().showMessage(
            f"Generating exact authored Mandarin speech WAV with {engine_label}"
        )
        if not runner.start(
            str(self.runtime.python),
            [str(PROJECT_ROOT / "tts_service.py"), str(job_path)],
        ):
            raise RuntimeError("Mandarin TTS worker is still stopping")

    def _speech_layers_for_tts(self) -> list[dict]:
        return [
            {
                "start_seconds": layer.start_seconds,
                "end_seconds": layer.end_seconds,
                "content": layer.text,
                "role": layer.content_role,
                "speaker": layer.speaker,
                "language": layer.language,
                "delivery": layer.delivery,
                "lip_sync": layer.lip_sync,
            }
            for layer in sorted(
                self.text_layers,
                key=lambda item: (item.start_seconds, item.end_seconds, item.layer_id),
            )
            if layer.content_role in {"dialogue", "voice_over", "lyrics"}
            and layer.text.strip()
        ]

    def _timeline_tts_signature(self, layers: list[dict] | None = None) -> str:
        payload = {
            "engine": self.render_settings.dialogue_tts_engine,
            "voice_policy": "on_location_production_v1",
            "duration_seconds": self.scan.duration_seconds if self.scan else 0.0,
            "text_layers": layers if layers is not None else self._speech_layers_for_tts(),
        }
        encoded = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _authored_tts_asset(self) -> MediaAsset | None:
        if not self.scan:
            return None
        return next(
            (
                asset for asset in self.scan.timeline_assets()
                if asset.media_type == "audio"
                and "AI DESIGN AUTHORED SPEECH TTS" in asset.recognition
                and str(asset.local_path or "").strip()
            ),
            None,
        )

    def _ensure_timeline_tts_asset(self) -> MediaAsset | None:
        asset = self._authored_tts_asset()
        authored_stem_prompt = (
            "Use this exact authored Timeline speech as a clean foreground dialogue stem for "
            "wording, speaker identity, timing and lip sync. Spatialize it as live on-location "
            "production sound, then generate audible diegetic ambience, contact-synchronized "
            "Foley/SFX and dialogue-ducked background music around it. Never treat this dry stem "
            "as the complete soundtrack and never duplicate the voice."
        )
        if asset is not None:
            asset.clip_prompt = authored_stem_prompt
            return asset
        if not self.scan:
            return asset
        asset = next(
            (
                item for item in self.scan.assets
                if item.media_type == "audio" and not str(item.local_path or "").strip()
            ),
            None,
        )
        if asset is None:
            asset = create_virtual_media_asset(self.scan, "audio")
            self._append_media_card(asset)
            self._refresh_virtual_media_header()
        output_root = (
            self.example_work_dir
            if self.example_work_dir is not None
            else CACHE_ROOT / "timeline_tts"
        )
        output_root.mkdir(parents=True, exist_ok=True)
        duration = self.scan.duration_seconds
        output = output_root / f"authored_timeline_dialogue_{duration:.2f}s.wav"
        track = self._design_track("A1", "audio")
        asset.local_path = str(output.resolve())
        asset.filename = output.name
        asset.timeline_placed = True
        asset.timeline_track_id = track.track_id
        asset.timeline_lane = self.tracks.index(track)
        asset.start_seconds = 0.0
        asset.end_seconds = duration
        asset.activation_mode = "auto"
        asset.enabled = True
        asset.monitor_visible = True
        asset.clip_prompt = authored_stem_prompt
        asset.recognition = (
            "AI DESIGN AUTHORED SPEECH TTS\n"
            "Usage: h3_reference\n"
            "Requirement: exact Timeline speech and lip sync"
        )
        self.timeline_tts_stale = True
        return asset

    def _use_h3_native_dialogue(self) -> None:
        if not self.scan:
            return
        changed = False
        for asset in self.scan.timeline_assets():
            if (
                asset.media_type == "audio"
                and "AI DESIGN AUTHORED SPEECH TTS" in asset.recognition
            ):
                if asset.activation_mode != "bypass":
                    asset.activation_mode = "bypass"
                    changed = True
                if asset.enabled:
                    asset.enabled = False
                    changed = True
        self.timeline_tts_stale = False
        if changed:
            self.refresh_activation()
            self._mark_dirty()
            self.statusBar().showMessage(
                "MiniMax H3 Native Dialogue active · authored TTS WAV excluded",
                8000,
            )

    @staticmethod
    def _stored_tts_signature(asset: MediaAsset) -> str:
        match = re.search(r"^TTS SIGNATURE:\s*([0-9a-f]{64})$", asset.recognition, re.M)
        return match.group(1) if match else ""

    @staticmethod
    def _write_tts_signature(asset: MediaAsset, signature: str) -> None:
        line = f"TTS SIGNATURE: {signature}"
        if re.search(r"^TTS SIGNATURE:.*$", asset.recognition, re.M):
            asset.recognition = re.sub(
                r"^TTS SIGNATURE:.*$", line, asset.recognition, flags=re.M
            )
        else:
            asset.recognition = asset.recognition.rstrip() + "\n" + line

    def _activate_authored_speech_reference(self, asset: MediaAsset) -> bool:
        track = self._track_for_asset(asset)
        if not track or track.kind != "audio":
            return False
        changed = False
        if not asset.timeline_placed:
            asset.timeline_placed = True
            asset.start_seconds = 0.0
            asset.end_seconds = self.scan.duration_seconds if self.scan else asset.end_seconds
            changed = True
        if not track.enabled:
            track.enabled = True
            changed = True
        if track.muted:
            track.muted = False
            changed = True
        if any(item.enabled and item.solo for item in self.tracks if item.kind == "audio"):
            if not track.solo:
                track.solo = True
                changed = True
        if not asset.enabled:
            asset.enabled = True
            changed = True
        if asset.activation_mode == "bypass":
            asset.activation_mode = "auto"
            changed = True
        if changed:
            self._rebuild_track_headers()
            self.refresh_activation()
            self._mark_dirty()
            self.statusBar().showMessage(
                f"Exact authored speech automatically enabled on {track.track_id} for H3 lip sync",
                8000,
            )
        return True

    def _start_timeline_tts_regeneration(self, resume: dict | None = None) -> bool:
        if not self.scan:
            return False
        if self.render_settings.dialogue_tts_engine == "h3_native":
            self._use_h3_native_dialogue()
            return False
        if (
            self.render_settings.dialogue_tts_engine == "voxcpm2_local"
            and not self._require_voxcpm_model(notify=bool(resume))
        ):
            return False
        if (
            self.render_settings.dialogue_tts_engine == "qwen3_tts_local"
            and not self._require_qwen3_tts_model(notify=bool(resume))
        ):
            return False
        layers = self._speech_layers_for_tts()
        if not layers:
            latest_signature = self._timeline_tts_signature()
            if latest_signature != str(pending["target_signature"]):
                # A second edit landed while VoxCPM/Edge was rendering.  Never
                # resume H3 with the now-obsolete intermediate WAV.
                self.timeline_tts_stale = True
                resume = self.pending_generation_after_tts
                self.pending_generation_after_tts = None
                QTimer.singleShot(
                    0,
                    lambda values=resume: self._start_timeline_tts_regeneration(values),
                )
                return
            self.timeline_tts_stale = False
            return False
        asset = self._ensure_timeline_tts_asset()
        if asset is None:
            return False
        if self.design_tts_runner and self.design_tts_runner.is_running():
            if resume:
                self.pending_generation_after_tts = dict(resume)
            return True
        target_signature = self._timeline_tts_signature(layers)
        CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        job_path = CACHE_ROOT / f"timeline_tts_{time.time_ns()}.json"
        job_path.write_text(json.dumps({
            "output_path": asset.local_path,
            "duration_seconds": self.scan.duration_seconds,
            "text_layers": layers,
            "ffmpeg": str(self.runtime.ffmpeg),
            "sapi_script": str(PROJECT_ROOT / "tts_sapi.ps1"),
            "engine": self.render_settings.dialogue_tts_engine,
            "voxcpm_model": str(VOXCPM_MODEL_DIR),
            "voxcpm_device": "auto",
            "voxcpm_local_files_only": True,
            "qwen3_tts_model": str(QWEN3_TTS_MODEL_DIR),
            "qwen3_tts_runtime": str(QWEN3_TTS_RUNTIME_DIR),
            "qwen3_tts_device": "auto",
            "qwen3_tts_local_files_only": True,
        }, ensure_ascii=False), encoding="utf-8")
        self.pending_design_tts = {
            "mode": "timeline_refresh",
            "asset_node_id": asset.node_id,
            "target_signature": target_signature,
        }
        self.pending_generation_after_tts = dict(resume) if resume else None
        self.design_tts_result = {}
        runner = JsonLineProcess(self, "timeline-dialogue-tts")
        runner.message.connect(self._design_tts_message)
        runner.finished.connect(self._design_tts_finished)
        self.design_tts_runner = runner
        self.generation_previous_monitor = self.monitor_display_stack.currentWidget()
        engine_label = {
            "voxcpm2_local": "VoxCPM2 Local",
            "qwen3_tts_local": "Qwen3-TTS Local",
            "edge_tts": "Edge TTS",
        }.get(self.render_settings.dialogue_tts_engine, "TTS")
        self.generation_overlay.start(
            f"{engine_label} · rebuilding edited Timeline dialogue"
        )
        self.statusBar().showMessage(
            f"Dialogue changed · rebuilding exact WAV with {engine_label}"
        )
        if not runner.start(
            str(self.runtime.python),
            [str(PROJECT_ROOT / "tts_service.py"), str(job_path)],
        ):
            self.design_tts_runner = None
            return False
        return True

    def _regenerate_timeline_tts_if_needed(self) -> None:
        if self.restoring_project or not self.timeline_tts_stale:
            return
        self._read_settings_ui()
        self._start_timeline_tts_regeneration()

    def _design_tts_message(self, payload: dict) -> None:
        if payload.get("progress"):
            message = str(payload["progress"])
            self.statusBar().showMessage(message)
            self.generation_overlay.set_message(message)
        if payload.get("completed") or payload.get("error"):
            self.design_tts_result = payload

    def _design_tts_finished(self, exit_code: int, log: str) -> None:
        pending = self.pending_design_tts
        result = self.design_tts_result
        runner = self.design_tts_runner
        self.design_tts_runner = None
        self.design_tts_result = {}
        self.pending_design_tts = None
        if runner:
            runner.deleteLater()
        if pending and pending.get("mode") == "timeline_refresh":
            self.generation_overlay.stop()
            self._restore_monitor_after_generation()
            if exit_code or result.get("error"):
                self.pending_generation_after_tts = None
                QMessageBox.critical(
                    self,
                    "Timeline dialogue TTS failed",
                    "The edited dialogue WAV could not be rebuilt, so H3 generation remains "
                    "blocked to prevent repeated, omitted or paraphrased speech.\n\n"
                    + str(result.get("error") or log[-1000:] or f"worker exit {exit_code}"),
                )
                return
            asset = next(
                (
                    item for item in (self.scan.timeline_assets() if self.scan else [])
                    if item.node_id == pending.get("asset_node_id")
                ),
                None,
            )
            if asset:
                transcript = list(result.get("transcript") or [])
                output_path = Path(str(result.get("output_path") or asset.local_path))
                if output_path.is_file() and self.scan:
                    placement = (
                        asset.timeline_placed,
                        asset.timeline_track_id,
                        asset.timeline_lane,
                        asset.start_seconds,
                        asset.end_seconds,
                    )
                    assign_local_media(self.scan, asset, output_path)
                    (
                        asset.timeline_placed,
                        asset.timeline_track_id,
                        asset.timeline_lane,
                        asset.start_seconds,
                        asset.end_seconds,
                    ) = placement
                prefix = asset.recognition.split("AUTHORED TTS TRANSCRIPT:", 1)[0].rstrip()
                asset.recognition = prefix + "\nAUTHORED TTS TRANSCRIPT:\n" + "\n".join(
                    f"[{float(row.get('start_seconds', 0.0)):.2f}-"
                    f"{float(row.get('end_seconds', 0.0)):.2f}] "
                    f"{row.get('speaker', 'S1')}: {row.get('content', '')}"
                    for row in transcript
                )
                self._write_tts_signature(asset, str(pending["target_signature"]))
                self._activate_authored_speech_reference(asset)
                sidecar = Path(asset.local_path).with_suffix(
                    Path(asset.local_path).suffix + ".request.json"
                )
                if sidecar.is_file():
                    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
                    metadata["tts_generation"] = {
                        "engine": result.get("engine", "Unknown TTS engine"),
                        "output_path": result.get("output_path", ""),
                        "transcript": transcript,
                        "signature": pending["target_signature"],
                    }
                    sidecar.write_text(
                        json.dumps(metadata, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
            self.timeline_tts_stale = False
            self._sync_prompt_panel_from_timeline(force=True, reconcile_brief=True)
            self._mark_all_render_segments_dirty()
            self._mark_dirty()
            resume = self.pending_generation_after_tts
            self.pending_generation_after_tts = None
            if resume:
                QTimer.singleShot(0, lambda values=resume: self._start_generation(**values))
            return
        if not pending:
            self.generation_overlay.stop()
            self.design_button.setEnabled(True)
            return
        if exit_code or result.get("error"):
            error_detail = str(
                result.get("error") or log[-1000:] or f"worker exit {exit_code}"
            )
            plan = pending["plan"]
            plan["media_requests"] = [
                item for item in plan.get("media_requests") or []
                if item.get("requirement_id") != "authored_speech_tts"
            ]
            materials = [
                item for item in pending["materials"]
                if item.get("requirement_id") != "authored_speech_tts"
            ]
            warnings = list(pending["warnings"])
            failed_engine = {
                "voxcpm2_local": "VoxCPM2",
                "qwen3_tts_local": "Qwen3-TTS",
                "edge_tts": "Edge TTS",
            }.get(self.render_settings.dialogue_tts_engine, "TTS")
            warnings.append(
                f"{failed_engine} authored speech failed, but the Design Timeline, Shots and exact "
                "Text Layers were preserved. The failed/silent Audio placeholder was not "
                "added to the Timeline. Change Dialogue Text Layer TTS to another provider "
                "(for example Edge TTS / Etts), then click Preview or Run to build a fresh "
                "WAV. Details: " + error_detail
            )
            if pending["generate_images"]:
                self._start_design_media_generation(
                    plan, materials, pending["replace"], pending["before"],
                    pending["design_dir"], pending["settings"],
                    initial_warnings=warnings,
                    timeline_tts_stale=True,
                )
                return
            self.generation_overlay.stop()
            self.design_button.setEnabled(True)
            self._commit_ai_design(
                plan, materials, pending["replace"], pending["before"],
                pending["design_dir"], warnings,
                timeline_tts_stale=True,
            )
            self._restore_monitor_after_generation()
            return
        material = pending["tts_material"]
        material["generated_by_tts"] = True
        material["tts_transcript"] = list(result.get("transcript") or [])
        signature_payload = {
            "engine": self.render_settings.dialogue_tts_engine,
            "voice_policy": "on_location_production_v1",
            "duration_seconds": float(pending["plan"].get("duration_seconds", 0.0)),
            "text_layers": [
                {
                    key: item.get(key)
                    for key in (
                        "start_seconds", "end_seconds", "content", "role", "speaker",
                        "language", "delivery", "lip_sync",
                    )
                }
                for item in (
                    pending["plan"].get("_required_text_layers")
                    or pending["plan"].get("text_layers")
                    or []
                )
                if str(item.get("role", "")) in {"dialogue", "voice_over", "lyrics"}
                and str(item.get("content", "")).strip()
            ],
        }
        material["tts_signature"] = hashlib.sha256(
            json.dumps(
                signature_payload, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        sidecar = Path(material["local_path"]).with_suffix(
            Path(material["local_path"]).suffix + ".request.json"
        )
        if sidecar.is_file():
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
            metadata["tts_generation"] = {
                "engine": result.get("engine", "Unknown TTS engine"),
                "output_path": result.get("output_path", ""),
                "transcript": material["tts_transcript"],
                "signature": material["tts_signature"],
            }
            sidecar.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if pending["generate_images"]:
            self._start_design_media_generation(
                pending["plan"], pending["materials"], pending["replace"],
                pending["before"], pending["design_dir"], pending["settings"],
                initial_warnings=pending["warnings"],
            )
            return
        self.generation_overlay.stop()
        self.design_button.setEnabled(True)
        self._commit_ai_design(
            pending["plan"], pending["materials"], pending["replace"],
            pending["before"], pending["design_dir"], pending["warnings"],
        )
        self._restore_monitor_after_generation()

    def _start_design_media_generation(
        self,
        plan: dict,
        materials: list[dict],
        replace: bool,
        before: dict,
        design_dir: Path,
        settings: DesignAISettings,
        initial_warnings: list[str] | None = None,
        timeline_tts_stale: bool = False,
    ) -> None:
        if self.submit_runner and self.submit_runner.is_running():
            raise RuntimeError("A ComfyUI video generation job is already running")
        if self.design_media_runner and self.design_media_runner.is_running():
            raise RuntimeError("AI Design reference image generation is already running")
        CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        job_path = CACHE_ROOT / "design_media_job.json"
        job_path.write_text(json.dumps({
            "server": self.server_url.text().strip(),
            "workflow_path": str(Z_IMAGE_WORKFLOW),
            "materials": materials,
            "settings": {
                "checkpoint": settings.image_checkpoint,
                "width": settings.image_width,
                "height": settings.image_height,
                "steps": settings.image_steps,
                "cfg": settings.image_cfg,
                "negative_prompt": settings.image_negative_prompt,
            },
            "poll_interval": self.render_settings.history_poll_interval,
            "generation_timeout": self.render_settings.generation_timeout,
            "http_timeout": self.render_settings.http_request_timeout,
        }, ensure_ascii=False), encoding="utf-8")
        self.pending_ai_design = {
            "plan": plan,
            "materials": materials,
            "replace": replace,
            "before": before,
            "design_dir": design_dir,
            "warnings": list(initial_warnings or []),
            "timeline_tts_stale": bool(timeline_tts_stale),
        }
        self.design_media_result = {}
        runner = JsonLineProcess(self, "design-media")
        runner.message.connect(self._design_media_message)
        runner.finished.connect(self._design_media_finished)
        self.design_media_runner = runner
        self.design_button.setEnabled(False)
        self.generation_previous_monitor = self.monitor_display_stack.currentWidget()
        self.generation_overlay.start("ComfyUI · generating AI Design reference images")
        self.statusBar().showMessage("Generating AI Design reference images in ComfyUI")
        if not runner.start(
            str(self.runtime.python),
            [str(PROJECT_ROOT / "design_media_service.py"), str(job_path)],
        ):
            raise RuntimeError("AI Design media worker is still stopping")

    def _design_media_message(self, payload: dict) -> None:
        if payload.get("progress"):
            message = str(payload["progress"])
            self.statusBar().showMessage(message)
            self.generation_overlay.set_message(message)
        if payload.get("completed") or payload.get("error"):
            self.design_media_result = payload

    def _design_media_finished(self, exit_code: int, log: str) -> None:
        self.generation_overlay.stop()
        self.design_button.setEnabled(True)
        pending = self.pending_ai_design
        result = self.design_media_result
        warnings = list((pending or {}).get("warnings") or [])
        warnings.extend(result.get("warnings") or [])
        generated_paths = {
            str(Path(item["local_path"]).resolve())
            for item in result.get("outputs") or []
            if item.get("generated") and item.get("local_path")
        }
        if pending:
            for material in pending["materials"]:
                material["generated_by_comfyui"] = (
                    str(Path(material["local_path"]).resolve()) in generated_paths
                )
        if exit_code or result.get("error"):
            warnings.append(
                "ComfyUI image generation failed; retained the generated requirement placeholders. "
                + str(result.get("error") or log[-500:] or f"worker exit {exit_code}")
            )
        try:
            if pending:
                self._commit_ai_design(
                    pending["plan"], pending["materials"], pending["replace"],
                    pending["before"], pending["design_dir"], warnings,
                    timeline_tts_stale=bool(pending.get("timeline_tts_stale")),
                )
        finally:
            self.pending_ai_design = None
            self._restore_monitor_after_generation()
            if self.design_media_runner:
                self.design_media_runner.deleteLater()
            self.design_media_runner = None
            self.design_media_result = {}

    def apply_ai_design(self, plan: dict, replace: bool = True) -> None:
        if not self.scan:
            self._notify_design_apply_failed(
                "No executable ComfyUI workflow is loaded.", category="Workflow"
            )
            return
        if (
            (self.design_media_runner and self.design_media_runner.is_running())
            or (
                self.media_regeneration_runner
                and self.media_regeneration_runner.is_running()
            )
            or (self.design_tts_runner and self.design_tts_runner.is_running())
            or (self.submit_runner and self.submit_runner.is_running())
        ):
            self._notify_design_apply_failed(
                "A ComfyUI, TTS or image-generation task is still running. "
                "Wait for it to finish, then retry Apply.",
                category="Execution state",
            )
            return
        try:
            selected_tts_engine = str(
                plan.pop("_dialogue_tts_engine", self.render_settings.dialogue_tts_engine)
            ).strip().lower()
            selected_music_mode = normalize_design_music_mode(
                plan.pop("_music_mode", self.render_settings.music_mode)
            )
            self.render_settings = RenderSettings.from_mapping({
                **asdict(self.render_settings),
                "dialogue_tts_engine": selected_tts_engine,
                "music_mode": selected_music_mode,
            })
            tts_index = self.settings_dialogue_tts.findData(
                self.render_settings.dialogue_tts_engine
            )
            self.settings_dialogue_tts.blockSignals(True)
            self.settings_dialogue_tts.setCurrentIndex(max(0, tts_index))
            self.settings_dialogue_tts.blockSignals(False)
            save_settings(SETTINGS_ENV, self.render_settings)
            authored_requirement = str(plan.get("_authored_requirement", ""))
            subtitles_enabled = bool(plan.get("_subtitles_enabled", False))
            dialogue_language = str(plan.get("_dialogue_language", "") or "")
            required_text_layers = deepcopy(
                plan.get("_required_text_layers") or []
            )
            generated_pipeline = bool(plan.get("_design_images_pre_generated", False))
            generated_references = [
                dict(item) for item in plan.get("_generated_references") or []
            ]
            pipeline_warnings = [
                str(item) for item in plan.get("_design_image_warnings") or []
            ]
            plan = normalize_design_plan(
                plan,
                self._design_context()["media_capacity"],
                existing_media=self._design_context().get("existing_media") or [],
                repair_media_plan=True,
                authored_requirement=authored_requirement,
                special_skill_key=str(self.special_combo.currentData() or ""),
            )
            plan = enforce_design_music_mode(plan, selected_music_mode)
            plan = protect_explicit_timed_text_layers(
                plan, authored_requirement
            )
            validated_required = validate_explicit_timed_text_contract(
                authored_requirement, plan
            )
            plan["_required_text_layers"] = (
                validated_required or required_text_layers
            )
            tts_required = self._ensure_authored_tts_request(
                plan, authored_requirement
            )
            deferred_tts_reason = str(plan.pop("_tts_deferred_reason", "")).strip()
            if deferred_tts_reason:
                pipeline_warnings.append(deferred_tts_reason)
            self._validate_design_segment_capacity(plan)
            if (
                tts_required
                and self.render_settings.dialogue_tts_engine == "voxcpm2_local"
                and not self._require_voxcpm_model()
            ):
                plan["media_requests"] = [
                    item for item in plan.get("media_requests") or []
                    if item.get("requirement_id") != "authored_speech_tts"
                ]
                tts_required = False
                deferred_tts_reason = (
                    "VoxCPM2 model is missing. Exact editable Text Layers were preserved; "
                    "WAV generation is deferred and the Timeline dialogue remains pending. "
                    + voxcpm_missing_message()
                )
                pipeline_warnings.append(deferred_tts_reason)
            if (
                tts_required
                and self.render_settings.dialogue_tts_engine == "qwen3_tts_local"
                and not self._require_qwen3_tts_model()
            ):
                plan["media_requests"] = [
                    item for item in plan.get("media_requests") or []
                    if item.get("requirement_id") != "authored_speech_tts"
                ]
                tts_required = False
                deferred_tts_reason = (
                    "Qwen3-TTS runtime/model is missing. Exact editable Text Layers were "
                    "preserved; WAV generation is deferred and Timeline dialogue remains "
                    "pending. " + qwen3_tts_missing_message()
                )
                pipeline_warnings.append(deferred_tts_reason)
            try:
                plan = enforce_design_dialogue_language(
                    plan,
                    dialogue_language,
                    authored_requirement=authored_requirement,
                )
            except DesignDialogueLanguageContractError as exc:
                pipeline_warnings.append(
                    "Dialogue language mismatch remains editable on the Timeline; Apply "
                    "continued without silently rewriting authored words. " + str(exc)
                )
            plan = enforce_design_subtitle_policy(
                plan,
                subtitles_enabled,
                authored_requirement=authored_requirement,
            )
            plan = reconcile_requested_speech_layer_contract(
                authored_requirement, plan
            )
            workspace = self._ensure_project_workspace(
                self._preferred_workspace_display_name(plan, authored_requirement)
            )
            design_revision, media_revision, audio_revision = next_design_revision(
                workspace
            )
            design_dir, materials = materialize_design_media(
                plan,
                workspace,
                self.runtime.ffmpeg,
                design_dir=design_revision,
                media_dir=media_revision,
                audio_dir=audio_revision,
            )
            before = self._design_workspace_state()
            settings = load_design_settings(DESIGN_SETTINGS_ENV)
            warnings: list[str] = pipeline_warnings
            image_materials = [
                item for item in materials if item.get("media_type") == "image"
            ]
            reused_count = 0
            for reference in sorted(
                generated_references,
                key=lambda item: int(item.get("request_index", 0)),
            ):
                image_index = int(reference.get("request_index", reused_count))
                source = Path(str(reference.get("local_path", "")))
                if not source.is_file() or not 0 <= image_index < len(image_materials):
                    continue
                material = image_materials[image_index]
                destination = Path(material["local_path"])
                shutil.copy2(source, destination)
                material["generated_by_comfyui"] = True
                material["preview_path"] = str(destination)
                material["concept_blip_caption"] = str(reference.get("caption", ""))
                material["background_removal"] = dict(reference.get("background_removal") or {})
                reused_count += 1
                sidecar = destination.with_suffix(destination.suffix + ".request.json")
                if sidecar.is_file():
                    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
                    metadata["z_image_generation"] = {
                        "source": str(source),
                        "seed": reference.get("seed"),
                        "prompt_id": reference.get("prompt_id"),
                        "blip_caption": reference.get("caption", ""),
                    }
                    sidecar.write_text(
                        json.dumps(metadata, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
            missing_count = len(image_materials) - reused_count
            if generated_pipeline and missing_count:
                warnings.append(
                    f"Z-Image generated {reused_count}/{len(image_materials)} requested image(s); "
                    f"{missing_count} failed request(s) remain labeled placeholders."
                )
            generate_images = (
                not generated_pipeline
                and settings.generate_comfy_images
                and bool(settings.image_checkpoint)
                and any(item.get("media_type") == "image" for item in materials)
            )
            tts_material = next(
                (
                    item for item in materials
                    if item.get("requirement_id") == "authored_speech_tts"
                ),
                None,
            ) if tts_required else None
            if tts_material:
                self._start_design_tts_generation(
                    plan, materials, replace, before, design_dir, settings,
                    warnings, generate_images, tts_material,
                )
            elif generate_images:
                self._start_design_media_generation(
                    plan, materials, replace, before, design_dir, settings,
                    initial_warnings=warnings,
                    timeline_tts_stale=bool(deferred_tts_reason),
                )
            else:
                self._commit_ai_design(
                    plan, materials, replace, before, design_dir, warnings,
                    timeline_tts_stale=bool(deferred_tts_reason),
                )
        except Exception as exc:
            self.generation_overlay.stop()
            self._restore_monitor_after_generation()
            self.design_button.setEnabled(True)
            if self.design_media_runner and not self.design_media_runner.is_running():
                self.design_media_runner.deleteLater()
                self.design_media_runner = None
            self.pending_ai_design = None
            self.pending_design_tts = None
            self._notify_design_apply_failed(str(exc))

    def _validate_design_segment_capacity(self, plan: dict) -> None:
        """Fail before generation when one time range cannot fit H3 9/3/3."""
        if not self.scan:
            return
        duration = float(plan.get("duration_seconds", self.scan.duration_seconds))
        rows: list[tuple[str, str, float, float]] = []
        for index, item in enumerate(plan.get("existing_media_uses") or [], 1):
            if is_analysis_only_media_use(item):
                continue
            media_type = str(item.get("media_type", "")).lower()
            identity = str(item.get("media_id") or f"existing-{index}").upper()
            rows.append((
                media_type,
                identity,
                float(item.get("start_seconds", 0.0)),
                float(item.get("end_seconds", duration)),
            ))
        for index, item in enumerate(plan.get("media_requests") or [], 1):
            media_type = str(item.get("media_type", "")).lower()
            identity = "REQUEST:" + str(item.get("requirement_id") or index)
            rows.append((
                media_type,
                identity,
                float(item.get("start_seconds", 0.0)),
                float(item.get("end_seconds", duration)),
            ))
        boundaries = sorted({0.0, duration, *[value for row in rows for value in row[2:]]})
        for left, right in zip(boundaries, boundaries[1:]):
            if right <= left:
                continue
            midpoint = (left + right) / 2.0
            for media_type, limit in self.scan.counts.items():
                active_ids = {
                    identity
                    for kind, identity, start, end in rows
                    if kind == media_type and start <= midpoint < end
                }
                if len(active_ids) > limit:
                    raise ValueError(
                        f"Design interval {left:.2f}-{right:.2f}s needs "
                        f"{len(active_ids)} unique {media_type} references, but one H3 "
                        f"Segment has only {limit} physical slots. Split or shorten the "
                        "references; the Virtual Media Pool itself remains unlimited."
                    )

    def _ensure_authored_tts_request(
        self,
        plan: dict,
        authored_requirement: str,
    ) -> bool:
        """Reserve one real Audio slot for exact authored speech when needed."""
        if self.render_settings.dialogue_tts_engine == "h3_native":
            plan["media_requests"] = [
                item for item in plan.get("media_requests") or []
                if item.get("requirement_id") != "authored_speech_tts"
            ]
            return False
        speech_layers = [
            item for item in plan.get("_required_text_layers") or plan.get("text_layers") or []
            if str(item.get("role", "")) in {"dialogue", "voice_over", "lyrics"}
            and str(item.get("content", "")).strip()
        ]
        if not speech_layers:
            return False
        explicit_audio_ids = {
            f"A{match}"
            for match in re.findall(r"@\s*A\s*(\d+)", authored_requirement, flags=re.I)
        }
        supplied_ids = {
            str(item.get("media_id", "")).upper()
            for item in plan.get("existing_media_uses") or []
            if item.get("media_type") == "audio"
        }
        if explicit_audio_ids.intersection(supplied_ids):
            return False

        requests = list(plan.get("media_requests") or [])
        if any(
            item.get("requirement_id") == "authored_speech_tts"
            for item in requests
        ):
            return True
        empty_slots = sum(
            asset.media_type == "audio" and not str(asset.local_path or "").strip()
            for asset in self.scan.assets
        ) if self.scan else 0
        audio_requests = [item for item in requests if item.get("media_type") == "audio"]
        if len(audio_requests) >= empty_slots:
            replaceable = next(
                (
                    item for item in audio_requests
                    if re.search(
                        r"dialogue|voice|speech|narrat|monologue|对白|對白|旁白|台词|台詞",
                        str(item.get("prompt", "")), flags=re.I,
                    )
                ),
                None,
            )
            if replaceable is None:
                plan["_tts_deferred_reason"] = (
                    "Exact authored speech needs one empty Audio reference slot for Mandarin TTS, "
                    "but all three physical Audio slots are occupied or reserved. Apply continued "
                    "with exact editable Text Layers; clear one A slot or use H3 Native Dialogue "
                    "before Preview/Run to build speech audio."
                )
                return False
            requests.remove(replaceable)
        transcript = "\n".join(
            f"[{float(item['start_seconds']):.2f}-{float(item['end_seconds']):.2f}s] "
            f"{item.get('speaker', 'S1')}: {item['content']}"
            for item in speech_layers
        )
        tts_request = {
            "requirement_id": "authored_speech_tts",
            "media_type": "audio",
            "usage": "h3_reference",
            "reuse_policy": "whole_design",
            "start_seconds": 0.0,
            "end_seconds": float(plan["duration_seconds"]),
            "track": "A1",
            "subject_keywords": ["exact authored Mandarin speech", "lip sync"],
            "prompt": (
                "AUTHORED SPEECH TTS CLEAN DIALOGUE STEM. Preserve this exact timed transcript, "
                "speaker identity and phoneme rhythm for lip sync. This is not the complete "
                "soundtrack: spatialize it as live on-location production dialogue and generate "
                "audible diegetic ambience, exact contact Foley/SFX and dialogue-ducked background "
                "music around it. Never duplicate the voice:\n" + transcript
            ),
        }
        first_audio = next(
            (
                index for index, item in enumerate(requests)
                if item.get("media_type") == "audio"
            ),
            len(requests),
        )
        requests.insert(first_audio, tts_request)
        plan["media_requests"] = requests
        return True

    def start_design_cleanup(self, job: dict) -> None:
        """Unload Design-only ComfyUI and LM Studio models after Apply."""
        if self.design_cleanup_runner and self.design_cleanup_runner.is_running():
            self.design_cleanup_runner.stop()
        CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        job_path = CACHE_ROOT / f"design_cleanup_{time.time_ns()}.json"
        job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        runner = JsonLineProcess(self, "design-model-cleanup")
        runner.message.connect(self._design_cleanup_message)
        runner.finished.connect(self._design_cleanup_finished)
        self.design_cleanup_runner = runner
        self.design_cleanup_result = {}
        self.statusBar().showMessage("AI Design applied · releasing ComfyUI and LM Studio models…")
        if not runner.start(
            str(self.runtime.python),
            [str(PROJECT_ROOT / "design_cleanup_service.py"), str(job_path)],
        ):
            self.statusBar().showMessage("AI Design applied · model cleanup worker unavailable")

    def _design_cleanup_message(self, payload: dict) -> None:
        if payload.get("completed") or payload.get("error"):
            self.design_cleanup_result = payload

    def _design_cleanup_finished(self, exit_code: int, log: str) -> None:
        result = self.design_cleanup_result
        warnings = list(result.get("warnings") or [])
        if exit_code or result.get("error"):
            warnings.append(str(result.get("error") or log[-400:] or f"worker exit {exit_code}"))
        if warnings:
            self.statusBar().showMessage(
                "AI Design applied · model cleanup warning: " + " | ".join(warnings),
                15000,
            )
        else:
            lm_count = len(result.get("lm_unloaded") or [])
            self.statusBar().showMessage(
                f"AI Design applied · ComfyUI image model released · "
                f"LM Studio model released ({lm_count} instance(s))",
                12000,
            )
        if self.design_cleanup_runner:
            self.design_cleanup_runner.deleteLater()
        self.design_cleanup_runner = None
        self.design_cleanup_result = {}

    def choose_workflow(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Open ComfyUI API workflow", str(PROJECT_ROOT), "JSON (*.json)")
        if filename:
            self.load_workflow_path(Path(filename))

    def new_project(self, _checked: bool = False, *, confirm: bool = True) -> None:
        if confirm and self.project_dirty:
            answer = QMessageBox.question(
                self,
                "New project",
                "Discard the current unsaved project and start a new one?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self._clear_generated_output()
        self.prompt_panel.clear_fields()
        self.special_combo.setCurrentIndex(0)
        if LATEST_WORKFLOW.exists():
            self.load_workflow_path(LATEST_WORKFLOW)
        else:
            self.scan = None
        self.project_path = None
        self.example_work_dir = None
        self.project_workspace_id = ""
        self.legacy_project_source = None
        self.shot_take_states = {}
        self.segment_take_states = {}
        self.quality_profile = "approved_final"
        self.storyboard_target_duration_seconds = 45.0
        self.storyboard_view_mode = "large_icons"
        self.smart_cut_last_plan = {}
        self.smart_cut_job_id = ""
        self.smart_cut_unload_job_id = ""
        self.smart_cut_dialog = None
        self.smart_cut_runner.stop()
        self.storyboard_trim_active = False
        self.production_strategy = "full_range"
        self.production_batch_seconds = 30.0
        self.incremental_approved_horizon = 0.0
        self.incremental_pending_start = 0.0
        self.incremental_pending_end = 0.0
        self.incremental_batch_phase = ""
        self.preview_seed = None
        self.preview_ready = False
        if hasattr(self, "production_strategy_combo"):
            index = self.production_strategy_combo.findData("full_range")
            self.production_strategy_combo.blockSignals(True)
            self.production_strategy_combo.setCurrentIndex(max(0, index))
            self.production_strategy_combo.blockSignals(False)
            self.production_batch_spin.blockSignals(True)
            self.production_batch_spin.setValue(self.production_batch_seconds)
            self.production_batch_spin.blockSignals(False)
            self._refresh_incremental_controls()
        if hasattr(self, "storyboard_target_spin"):
            self.storyboard_target_spin.blockSignals(True)
            self.storyboard_target_spin.setValue(
                self.storyboard_target_duration_seconds
            )
            self.storyboard_target_spin.blockSignals(False)
        if hasattr(self, "storyboard_trim_button"):
            if hasattr(self, "manual_ripple_action"):
                self.manual_ripple_action.setChecked(False)
            self._refresh_storyboard_trim_controls()
        if hasattr(self, "quality_profile_combo"):
            index = self.quality_profile_combo.findData(self.quality_profile)
            self.quality_profile_combo.blockSignals(True)
            self.quality_profile_combo.setCurrentIndex(max(0, index))
            self.quality_profile_combo.blockSignals(False)
        self.project_dirty = False
        self.undo_stack.clear()
        self.undo_stack.setClean()
        self._update_window_title()
        self.statusBar().showMessage("New Director project ready")

    def _clear_generated_output(self, *, preserve_segment_cache: bool = False) -> None:
        """Detach the displayed Master, optionally retaining reusable Segment Takes.

        Structural Timeline editors invalidate the assembled Master immediately,
        but their unchanged Segment checkpoints remain valuable.  Callers that
        remap and explicitly dirty old/new ranges use ``preserve_segment_cache``;
        full project/design resets keep the original destructive behavior.
        """
        self.generated_output_locked = False
        self.storyboard_preview_active = False
        self.generated_output_path = None
        self.generated_playback_path = None
        self.generated_output_timeline_start = 0.0
        self.generated_pending_position_ms = 0
        self.generated_proxy_autoplay_pending = False
        proxy_runner = self.generated_proxy_runner
        self.generated_proxy_runner = None
        self.generated_proxy_source = None
        self.generated_proxy_target = None
        proxy_working = self.generated_proxy_working
        self.generated_proxy_working = None
        if proxy_runner:
            proxy_runner.stop()
            proxy_runner.deleteLater()
        if proxy_working:
            try:
                proxy_working.unlink(missing_ok=True)
            except OSError:
                pass
        if not preserve_segment_cache:
            self.smart_render_manifest = {}
            self.smart_render_manifests = {}
            self.render_dirty_segment_ids.clear()
        self.render_runtime_status.clear()
        self.submit_request_kind = "final"
        self._refresh_render_status_bar()
        self.generated_player.stop()
        self.generated_player.setSource(QUrl())
        if hasattr(self, "generated_frame_pixmap"):
            self.generated_frame_pixmap = QPixmap()
            self.generated_video_widget.clear()
        self.player.stop()
        self.player.setSource(QUrl())
        self.audio_output.setMuted(False)
        if hasattr(self, "generation_overlay"):
            self.generation_overlay.stop()
        if hasattr(self, "generated_output_label"):
            self.generated_output_label.setText("No generated output")
            self.generated_output_label.setStyleSheet("color:#7f8992; padding:2px 4px;")
            self.export_generated_button.setEnabled(False)
        if hasattr(self, "monitor_image"):
            self.monitor_image.clear()
            self.monitor_image.setText("Load a media slot to preview")
            self.monitor_stack.setCurrentWidget(self.monitor_image)
        if hasattr(self, "generated_monitor_image"):
            self.generated_monitor_image.clear()
            self.generated_monitor_image.setText(
                "Generate or open a project with an output video"
            )
            self.generated_monitor_stack.setCurrentWidget(self.generated_monitor_image)
            self.monitor_display_stack.setCurrentWidget(self.monitor_compare_splitter)

    def export_generated_output(self) -> None:
        source = self.generated_output_path
        if not source or not source.is_file():
            QMessageBox.information(self, "No generated video", "Generate a preview or final video first.")
            return
        suffix = source.suffix or ".mp4"
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Export generated video",
            str(PROJECT_ROOT / f"h3_generated{suffix}"),
            f"Generated media (*{suffix});;All files (*)",
        )
        if not destination:
            return
        target = Path(destination)
        if not target.suffix:
            target = target.with_suffix(suffix)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.resolve() != source.resolve():
                shutil.copy2(source, target)
            self.statusBar().showMessage(f"Generated video exported: {target}")
            QMessageBox.information(self, "Export complete", f"Saved to:\n{target}")
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _first_loaded_picture(self) -> MediaAsset | None:
        if not self.scan:
            return None
        pictures = [
            asset for asset in self.scan.assets
            if asset.media_type == "image" and str(asset.local_path).strip()
        ]

        def order(asset: MediaAsset) -> tuple[int, str]:
            match = re.search(r"(\d+)$", stable_reference_id(asset))
            return (int(match.group(1)) if match else 10_000, stable_reference_id(asset))

        return min(pictures, key=order) if pictures else None

    def _preferred_workspace_display_name(
        self,
        plan: dict | None = None,
        authored_requirement: str = "",
    ) -> str:
        """Name projects from P1 visual evidence, then from authored story text."""
        first_picture = self._first_loaded_picture()
        if first_picture is not None:
            overview = picture_overview_project_name(first_picture.recognition)
            if overview:
                return overview
            media_id = stable_reference_id(first_picture)
            for row in (plan or {}).get("existing_media_uses") or []:
                if not isinstance(row, dict) or str(row.get("media_id", "")) != media_id:
                    continue
                keywords = [
                    workspace_folder_name(str(value), "")
                    for value in row.get("subject_keywords") or []
                ]
                keywords = [value for value in keywords if value]
                if keywords:
                    return "_".join(keywords)[:80].strip(" ._")
            # Never fall back to an opaque imported filename: the user asked
            # for visual meaning, not a camera/download filename. Design will
            # supply subject keywords if BLIP has not completed yet.
        if plan:
            planned_name = project_display_name_for_plan(plan)
            if planned_name and not planned_name.startswith("h3_project"):
                return planned_name
        if str(authored_requirement).strip():
            return design_requirement_project_name(authored_requirement)
        if plan:
            return project_display_name_for_plan(plan)
        return "h3_project"

    @staticmethod
    def _storyboard_target_from_workspace(
        workspace_root: Path,
        fallback_duration: float,
    ) -> float:
        """Recover the original requested duration from the latest Design revision."""
        revision_root = workspace_root / "design" / "revisions"
        candidates = sorted(
            revision_root.glob("R*/design_plan.json"),
            key=lambda path: path.parent.name,
            reverse=True,
        )
        for candidate in candidates:
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8-sig"))
                target = float(
                    payload.get("_speech_timing_base_duration", 0.0) or 0.0
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            if target >= 0.5:
                return min(max(0.5, target), max(0.5, fallback_duration))
        return max(0.5, float(fallback_duration))

    def _rebase_runtime_workspace_paths(self, old_root: Path, new_root: Path) -> None:
        if not self.scan or old_root == new_root:
            return
        for asset in self.scan.timeline_assets():
            if not str(asset.local_path).strip():
                continue
            try:
                relative = Path(asset.local_path).resolve().relative_to(old_root)
            except (OSError, ValueError):
                continue
            asset.local_path = str((new_root / relative).resolve())

    def _ensure_project_workspace(self, display_name: str = "") -> Path:
        """Return the single durable Workspace for the current project.

        Legacy projects adopt the folder containing the opened project but the
        old JSON is never rewritten: subsequent saves go to ``project/``.
        """
        if self.example_work_dir:
            root = Path(self.example_work_dir).resolve()
            if str(display_name).strip() and not self.project_path:
                old_root = root
                root = refine_provisional_workspace_root(
                    root,
                    DESIGN_EXAMPLE_ROOT,
                    str(display_name).strip(),
                )
                self._rebase_runtime_workspace_paths(old_root, root)
        elif self.project_path:
            root = locate_workspace_for_project(self.project_path, {})
        else:
            title = str(display_name).strip() or "h3_project"
            root = allocate_workspace_root(DESIGN_EXAMPLE_ROOT, title)
        manifest = ensure_workspace_layout(
            root,
            display_name=str(display_name).strip() or root.name,
            workspace_id=self.project_workspace_id,
            legacy_project_path=self.legacy_project_source,
        )
        self.example_work_dir = root.resolve()
        self.project_workspace_id = str(manifest.get("workspace_id") or "")
        return self.example_work_dir

    def _ensure_example_work_dir(self) -> Path:
        """Compatibility alias retained for older Studio call sites/tests."""
        return self._ensure_project_workspace()

    def _shot_ids(self) -> list[str]:
        return [
            str(cue.cue_id)
            for cue in self.director_cues
            if cue.cue_type == "shot" and str(cue.cue_id).strip()
        ]

    def _sync_shot_take_states(self) -> None:
        self.shot_take_states = normalize_shot_take_states(
            self.shot_take_states,
            self._shot_ids(),
        )
        self.segment_take_states = normalize_segment_take_states(
            self.segment_take_states
        )

    def _write_shot_state_manifests(self) -> None:
        if not self.example_work_dir:
            return
        shot_ranges = {
            str(cue.cue_id): (float(cue.start_seconds), float(cue.end_seconds))
            for cue in self.director_cues
            if cue.cue_type == "shot"
        }
        write_shot_manifests(
            self.example_work_dir,
            self.shot_take_states,
            shot_ranges,
        )

    def _quality_profile_changed(self, *_args) -> None:
        selected = str(self.quality_profile_combo.currentData() or "approved_final")
        self.quality_profile = (
            selected if selected in QUALITY_PROFILES else "approved_final"
        )
        if self.quality_profile == "storyboard":
            self.statusBar().showMessage(
                "Storyboard quality selected - Timeline preview only; ComfyUI is not run."
            )
        self._mark_dirty()

    def _resource_estimate(self, profile: str | None = None):
        root = self._ensure_project_workspace()
        selected = profile or self.quality_profile
        duration = max(0.0, self.clip_end.value() - self.clip_start.value())
        shots = [
            cue for cue in self.director_cues
            if cue.cue_type == "shot"
            and cue.end_seconds > self.clip_start.value()
            and cue.start_seconds < self.clip_end.value()
        ]
        try:
            planned = self._planned_render_segments()
            segment_count = len(planned)
        except Exception:
            planned = []
            segment_count = max(1, int((duration + MAX_NATIVE_SECONDS - 1e-6) // MAX_NATIVE_SECONDS))
        cache_key = "preview" if selected == "motion_preview" else "production"
        cached_manifest = self.smart_render_manifests.get(cache_key, {})
        cached_by_id = {
            str(row.get("segment_id", "")): row
            for row in cached_manifest.get("segments", [])
            if isinstance(row, dict)
            and Path(str(row.get("output_path", ""))).is_file()
            and str(row.get("status", "")).lower()
            in {"cached", "complete", "completed", "reusable"}
        }
        reusable_duration = sum(
            max(
                0.0,
                float(
                    segment.core_end_seconds
                    if segment.core_end_seconds is not None
                    else segment.end_seconds
                )
                - float(
                    segment.core_start_seconds
                    if segment.core_start_seconds is not None
                    else segment.start_seconds
                ),
            )
            for segment in planned
            if segment.segment_id in cached_by_id
            and segment.segment_id not in self.render_dirty_segment_ids
        )
        return estimate_resources(
            root,
            profile=selected,
            total_duration_seconds=duration,
            reusable_duration_seconds=reusable_duration,
            shot_count=len(shots),
            segment_count=segment_count,
            reserve_disk_gb=self.render_settings.workspace_free_disk_reserve_gb,
        )

    def show_resource_estimate(self) -> None:
        self._read_settings_ui()
        estimate = self._resource_estimate()
        calibration = "calibrated from this Workspace" if estimate.calibrated else "first-run estimate"
        QMessageBox.information(
            self,
            "Generation resource estimate",
            f"Quality: {QUALITY_PROFILES[estimate.profile].label}\n"
            f"Timeline: {estimate.total_duration_seconds:.2f}s, "
            f"{estimate.shot_count} Shot(s), {estimate.segment_count} Segment(s)\n"
            f"New / reusable duration: {estimate.render_duration_seconds:.2f}s / "
            f"{estimate.reusable_duration_seconds:.2f}s\n"
            f"Estimated processing: {estimate.gpu_minutes:.1f} minutes ({calibration})\n"
            f"Estimated additional disk: {estimate.additional_disk_bytes / 1024**3:.2f} GB\n"
            f"Free / protected reserve: {estimate.free_disk_bytes / 1024**3:.1f} / "
            f"{estimate.reserve_disk_bytes / 1024**3:.1f} GB\n"
            f"Ready: {'YES' if estimate.fits_disk_budget else 'NO - insufficient reserve'}",
        )

    def _activate_storyboard_mode(self) -> None:
        # Storyboard is a direct source-Timeline preview. Keep the generated
        # Final visible on the right, but play source media and authored audio
        # from the work-area head when the saved playhead is on its end frame.
        self.timeline_playing = False
        self.timeline_timer.stop()
        self.generated_player.pause()
        self.player.pause()
        for player in self.composite_video_players.values():
            player.pause()
        for player in self.timeline_audio_players.values():
            player.pause()
        self.play_button.setText("▶")
        self.storyboard_preview_active = True
        start = float(self.clip_start.value())
        end = float(self.clip_end.value())
        target = float(self.playhead_seconds)
        if target < start - 1e-6 or target >= end - 1e-6:
            target = start
        self.seek_timeline(target)
        self.monitor_display_stack.setCurrentWidget(self.monitor_compare_splitter)
        if self.scan:
            self.toggle_playback()
        self.statusBar().showMessage(
            "Storyboard playing - Timeline source and authored audio; no H3 generation was queued."
        )

    def _storyboard_target_changed(self, value: float) -> None:
        self.storyboard_target_duration_seconds = max(0.5, float(value))
        self._refresh_storyboard_trim_controls()
        self._mark_dirty()

    def _refresh_storyboard_trim_controls(self) -> None:
        if not hasattr(self, "storyboard_trim_button"):
            return
        duration = self.scan.duration_seconds if self.scan else 0.0
        target = max(0.5, float(self.storyboard_target_duration_seconds))
        remaining = max(0.0, duration - target)
        # Keep the feature entry point stable. Replacing its label with
        # "CUT DONE" made Auto Cut look as if it had disappeared, while
        # disabling it prevented the user from opening the explanatory state.
        self.storyboard_trim_button.setText("AUTO CUT")
        self.storyboard_trim_button.setEnabled(True)
        target_state = (
            f"Current {duration:.1f}s → target {target:.1f}s; planned reduction {remaining:.1f}s."
            if duration > 0.0
            else "Load or create a Timeline, then set the Storyboard target duration."
        )
        self.storyboard_trim_button.setToolTip(
            "<b>Auto Cut · Smart Cut Story Compression</b><br>"
            f"{target_state}<br>"
            "Main button uses Balanced mode; the arrow offers Safe, Aggressive and Manual Ripple Cut."
        )
        if remaining <= 0.01 and self.storyboard_trim_active:
            self.storyboard_trim_active = False
            if hasattr(self, "manual_ripple_action"):
                self.manual_ripple_action.blockSignals(True)
                self.manual_ripple_action.setChecked(False)
                self.manual_ripple_action.blockSignals(False)
        self.storyboard_trim_button.setStyleSheet(
            "background:#8f3340; color:white; font-weight:700;"
            if self.storyboard_trim_active else ""
        )

    def _toggle_storyboard_trim_mode(self, enabled: bool) -> None:
        self.storyboard_trim_active = bool(enabled)
        if hasattr(self, "manual_ripple_action") and self.manual_ripple_action.isChecked() != bool(enabled):
            self.manual_ripple_action.blockSignals(True)
            self.manual_ripple_action.setChecked(bool(enabled))
            self.manual_ripple_action.blockSignals(False)
        if not enabled:
            self._refresh_storyboard_trim_controls()
            self.statusBar().showMessage("Storyboard Ripple Cut mode disabled")
            return
        if not self.scan or (
            self.scan.duration_seconds
            <= self.storyboard_target_duration_seconds + 0.01
        ):
            self.storyboard_trim_active = False
            if hasattr(self, "manual_ripple_action"):
                self.manual_ripple_action.blockSignals(True)
                self.manual_ripple_action.setChecked(False)
                self.manual_ripple_action.blockSignals(False)
            self._refresh_storyboard_trim_controls()
            return
        self.quality_profile = "storyboard"
        self.storyboard_preview_active = True
        self.timeline_playing = False
        self.timeline_timer.stop()
        self._stop_all_timeline_media()
        self.play_button.setText("▶")
        self.monitor_display_stack.setCurrentWidget(self.monitor_compare_splitter)
        self.seek_timeline(min(self.playhead_seconds, self.scan.duration_seconds))
        self._refresh_storyboard_trim_controls()
        self.statusBar().showMessage(
            "STORY CUT active · select an unwanted purple Shot Block and press Delete. "
            f"Current {self.scan.duration_seconds:.1f}s → target "
            f"{self.storyboard_target_duration_seconds:.1f}s · Undo/Redo supported."
        )

    def _smart_cut_shot_inputs(self) -> list[dict]:
        """Compile current Timeline truth into the deterministic planner schema."""
        if not self.scan:
            return []
        shots = sorted(
            (cue for cue in self.director_cues if cue.cue_type == "shot"),
            key=lambda cue: (cue.start_seconds, cue.end_seconds),
        )

        def layer_belongs(layer: TextLayer, cue: DirectorCue) -> bool:
            if layer.shot_id:
                return layer.shot_id == cue.cue_id
            midpoint = (layer.start_seconds + layer.end_seconds) / 2
            return cue.start_seconds - 1e-6 <= midpoint <= cue.end_seconds + 1e-6

        rows: list[dict] = []
        timeline_media = [
            asset for asset in self.scan.timeline_assets()
            if asset.timeline_placed and asset.activation_mode != "bypass"
        ]
        for cue in shots:
            speech_layers = [
                layer for layer in self.text_layers
                if layer.content_role in {"dialogue", "voice_over", "lyrics"}
                and layer_belongs(layer, cue)
            ]
            intervals = sorted(
                (
                    max(cue.start_seconds, float(layer.start_seconds)),
                    min(cue.end_seconds, float(layer.end_seconds)),
                )
                for layer in speech_layers
                if min(cue.end_seconds, float(layer.end_seconds))
                > max(cue.start_seconds, float(layer.start_seconds))
            )
            speech_duration = 0.0
            if intervals:
                active_start, active_end = intervals[0]
                for start, end in intervals[1:]:
                    if start <= active_end + 1e-6:
                        active_end = max(active_end, end)
                    else:
                        speech_duration += active_end - active_start
                        active_start, active_end = start, end
                speech_duration += active_end - active_start
            media_ids = sorted({
                media_shortcut(asset)
                for asset in timeline_media
                if ranges_intersect(
                    cue.start_seconds,
                    cue.end_seconds,
                    asset.start_seconds,
                    asset.end_seconds,
                )
            })
            row = asdict(cue)
            row.update({
                "speech_duration": snap_timeline_seconds(speech_duration),
                "speech_count": len(speech_layers),
                "explicit_speech": bool(speech_layers),
                "media_ids": media_ids,
                "locked": False,
            })
            rows.append(row)
        return rows

    def open_smart_cut(self, mode: str = "balanced") -> None:
        """Analyze current Shots and open a non-destructive Smart Cut review."""
        if not self.scan:
            QMessageBox.information(self, "Smart Cut", "Load an API workflow first.")
            return
        rows = self._smart_cut_shot_inputs()
        if not rows:
            QMessageBox.information(
                self,
                "Smart Cut",
                "Create Shot Blocks with Design or the Shot Tool before Smart Cut.",
            )
            return
        if self.scan.duration_seconds <= self.storyboard_target_duration_seconds + 0.01:
            QMessageBox.information(
                self,
                "Smart Cut",
                "The Timeline is already at or below the Storyboard target.",
            )
            return
        self.timeline_playing = False
        self.timeline_timer.stop()
        self._stop_all_timeline_media()
        dialog = SmartCutDialog(
            rows,
            self.storyboard_target_duration_seconds,
            mode if mode in SMART_CUT_MODES else "balanced",
            self,
        )
        self.smart_cut_dialog = dialog
        dialog.ai_refine_requested.connect(self._start_smart_cut_lm)
        result = dialog.exec()
        plan = dialog.result_plan()
        self.smart_cut_dialog = None
        dialog.deleteLater()
        if result != QDialog.Accepted:
            self.statusBar().showMessage("Smart Cut review cancelled · Timeline unchanged")
            return
        self._apply_smart_cut_plan(plan)

    def _start_smart_cut_lm(self, dialog: SmartCutDialog) -> None:
        """Request bounded semantic hints; LM output never contains edit timings."""
        if self.smart_cut_job_id:
            return
        settings = load_design_settings(DESIGN_SETTINGS_ENV)
        provider = settings.provider
        if provider == "lm_studio":
            base_url = settings.lm_studio_base_url
            model = settings.lm_studio_model
            api_key = ""
        else:
            base_url = settings.openai_base_url
            model = settings.openai_model
            api_key = self.semantic_openai_api_key or os.getenv("OPENAI_API_KEY", "")
        if not base_url or not model:
            dialog.set_ai_running(False, "AI semantic refine unavailable · configure Design provider/model")
            return
        if provider == "openai" and not api_key:
            dialog.set_ai_running(False, "Online GPT requires an API key entered in Design")
            return
        system_prompt, user_prompt = smart_cut_lm_prompts(
            dialog.shot_inputs,
            float(dialog.plan["target_duration"]),
        )
        if not self.smart_cut_runner.is_running():
            if not self.smart_cut_runner.start(
                str(self.runtime.python), [str(PROJECT_ROOT / "design_ai_service.py")]
            ):
                dialog.set_ai_running(False, "Could not start Smart Cut semantic service")
                return
        self.smart_cut_job_id = f"smart-cut-{secrets.token_hex(8)}"
        self.smart_cut_active_request = {
            "provider": provider,
            "base_url": base_url,
            "model": model,
            "timeout": settings.timeout,
        }
        dialog.set_ai_running(
            True,
            f"{provider.replace('_', ' ').title()} is classifying story roles · Timeline remains unchanged…",
        )
        self.smart_cut_runner.write_json({
            "action": "generate",
            "job": self.smart_cut_job_id,
            "provider": provider,
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "timeout": settings.timeout,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "schema": smart_cut_lm_schema(),
            "schema_name": "h3_smart_cut_semantic_hints",
            "max_output_tokens": 5000,
        })

    @staticmethod
    def _json_object_from_model_text(value: object) -> dict:
        text = str(value or "").strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("AI semantic response did not contain a JSON object")
            payload = json.loads(text[start:end + 1])
        if not isinstance(payload, dict):
            raise ValueError("AI semantic response must be a JSON object")
        return payload

    def _handle_smart_cut_payload(self, payload: dict) -> None:
        if payload.get("ready"):
            return
        job_id = str(payload.get("job", ""))
        if job_id and job_id == self.smart_cut_unload_job_id:
            self.smart_cut_unload_job_id = ""
            return
        if not job_id or job_id != self.smart_cut_job_id:
            return
        self.smart_cut_job_id = ""
        dialog = self.smart_cut_dialog
        if payload.get("error"):
            if dialog:
                dialog.set_ai_running(False, "AI semantic refine failed · " + str(payload["error"]))
            self._request_smart_cut_lm_unload()
            return
        try:
            response = self._json_object_from_model_text(payload.get("text", ""))
            valid_ids = [str(row.get("cue_id", "")) for row in (dialog.shot_inputs if dialog else [])]
            hints = normalize_lm_hints(response, valid_ids)
            resolved_model = str(
                payload.get("resolved_model")
                or self.smart_cut_active_request.get("model", "")
            )
            if resolved_model:
                # The service may repair a deleted/stale LM Studio model ID.
                # Unload the instance that actually answered, not the authored
                # stale identifier, or LM Studio will report model_not_found.
                self.smart_cut_active_request["model"] = resolved_model
            if dialog:
                dialog.apply_ai_hints(hints, resolved_model)
                dialog.set_ai_running(
                    False,
                    f"AI classified {len(hints)} Shot(s) · deterministic planner retained timing authority",
                )
        except Exception as exc:
            if dialog:
                dialog.set_ai_running(False, "AI semantic response rejected · " + str(exc))
        self._request_smart_cut_lm_unload()

    def _request_smart_cut_lm_unload(self) -> None:
        request = getattr(self, "smart_cut_active_request", {}) or {}
        if (
            request.get("provider") != "lm_studio"
            or not self.smart_cut_runner.is_running()
            or self.smart_cut_unload_job_id
        ):
            return
        self.smart_cut_unload_job_id = f"smart-cut-unload-{secrets.token_hex(6)}"
        self.smart_cut_runner.write_json({
            "action": "unload_lm",
            "job": self.smart_cut_unload_job_id,
            "base_url": request.get("base_url", ""),
            "model": request.get("model", ""),
            "timeout": min(60, int(request.get("timeout", 60))),
        })

    def _smart_cut_service_finished(self, exit_code: int, log: str) -> None:
        self.smart_cut_job_id = ""
        self.smart_cut_unload_job_id = ""
        if self.smart_cut_dialog:
            detail = log.strip().splitlines()[-1] if log.strip() else f"exit {exit_code}"
            self.smart_cut_dialog.set_ai_running(False, "Smart Cut semantic service stopped · " + detail)

    def _apply_smart_cut_plan(self, plan: dict) -> None:
        """Validate reviewed decisions and commit through Storyboard remapping."""
        if not self.scan or plan.get("format") != "h3-smart-cut-plan":
            return
        current_shots = {
            cue.cue_id: cue for cue in self.director_cues if cue.cue_type == "shot"
        }
        speech_ids = {
            layer.shot_id
            for layer in self.text_layers
            if layer.content_role in {"dialogue", "voice_over", "lyrics"}
            and layer.shot_id
        }
        entries: list[dict] = []
        for decision in plan.get("decisions", []):
            shot_id = str(decision.get("shot_id", ""))
            cue = current_shots.get(shot_id)
            if cue is None:
                QMessageBox.warning(self, "Smart Cut stale plan", f"Shot {shot_id} no longer exists.")
                return
            action = str(decision.get("action", "keep"))
            proposed = snap_timeline_seconds(float(decision.get("proposed_duration", 0.0)))
            if action in {"remove", "merge"} and shot_id in speech_ids:
                QMessageBox.warning(
                    self,
                    "Smart Cut speech protection",
                    f"{shot_id} contains authored speech and cannot be silently removed.",
                )
                return
            if action in {"remove", "merge"} or proposed < TIMELINE_SNAP_SECONDS:
                continue
            entries.append({
                "cue_id": cue.cue_id,
                "duration": proposed,
                "preset": cue.preset,
                "framing": cue.framing,
                "subject_action": cue.authored_subject_action or cue.subject_action,
            })
        if not entries:
            QMessageBox.warning(self, "Smart Cut", "The reviewed plan cannot remove every Shot.")
            return
        self.smart_cut_last_plan = deepcopy(plan)
        self._apply_storyboard_entries(
            entries,
            float(plan.get("target_duration", self.storyboard_target_duration_seconds)),
            undo_label="Apply Smart Cut Plan",
            dirty_ranges=[tuple(row) for row in plan.get("affected_ranges", [])],
        )
        if self.example_work_dir:
            try:
                destination = self.example_work_dir / "smart_cut_plan.json"
                destination.write_text(
                    json.dumps(self.smart_cut_last_plan, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except OSError:
                pass
        self.statusBar().showMessage(
            f"Smart Cut applied · {plan.get('mode', 'balanced')} · "
            f"saved {float(plan.get('saved_seconds', 0.0)):.1f}s · "
            "affected Segments marked for local rerender · Undo available"
        )

    def open_storyboard_editor(self) -> None:
        """Open a draft Shot-card board; Timeline changes only after explicit Apply."""
        if not self.scan:
            QMessageBox.information(self, "Storyboard", "Load an API workflow first.")
            return
        shots = sorted(
            (cue for cue in self.director_cues if cue.cue_type == "shot"),
            key=lambda cue: (cue.start_seconds, cue.end_seconds),
        )
        if not shots:
            QMessageBox.information(
                self,
                "Storyboard",
                "Create Shot Blocks with the Shot Tool or apply a Director Design first.",
            )
            return
        self.timeline_playing = False
        self.timeline_timer.stop()
        self._stop_all_timeline_media()
        dialog = StoryboardEditorDialog(
            shots,
            self.text_layers,
            self.scan.timeline_assets(),
            self.scan.duration_seconds,
            self.storyboard_target_duration_seconds,
            self,
            preview_paths=self.preview_paths,
            view_mode=self.storyboard_view_mode,
        )
        result = dialog.exec()
        self.storyboard_view_mode = dialog.view_mode
        if result != QDialog.Accepted:
            dialog.deleteLater()
            self._mark_dirty()
            self.statusBar().showMessage("Storyboard draft cancelled · Timeline unchanged")
            return
        entries = dialog.entries()
        target = float(dialog.target_spin.value())
        dialog.deleteLater()
        self._apply_storyboard_entries(entries, target)

    @staticmethod
    def _storyboard_map_range(
        start: float,
        end: float,
        old_start: float,
        old_end: float,
        new_start: float,
        new_end: float,
        minimum: float,
    ) -> tuple[float, float]:
        old_duration = max(0.05, old_end - old_start)
        new_duration = max(minimum, new_end - new_start)
        scale = new_duration / old_duration
        mapped_start = new_start + (max(old_start, start) - old_start) * scale
        mapped_end = new_start + (min(old_end, end) - old_start) * scale
        mapped_start = max(new_start, min(new_end, mapped_start))
        mapped_end = max(mapped_start + minimum, min(new_end, mapped_end))
        if mapped_end > new_end:
            mapped_end = new_end
            mapped_start = max(new_start, mapped_end - minimum)
        return snap_timeline_seconds(mapped_start), snap_timeline_seconds(mapped_end)

    def _apply_storyboard_entries(
        self,
        entries: list[dict],
        target_duration: float,
        *,
        undo_label: str = "Apply Storyboard Editor",
        dirty_ranges: list[tuple[float, float]] | None = None,
    ) -> None:
        """Atomically remap Shot order/durations and every Timeline dependency."""
        if not self.scan or not entries:
            return
        old_duration = float(self.scan.duration_seconds)
        old_shots = sorted(
            (cue for cue in self.director_cues if cue.cue_type == "shot"),
            key=lambda cue: (cue.start_seconds, cue.end_seconds),
        )
        old_by_id = {cue.cue_id: cue for cue in old_shots}
        before = self._design_workspace_state()
        dirty_before = set(self.render_dirty_segment_ids)
        cursor = 0.0
        normalized: list[dict] = []
        next_number = max(
            [
                int(cue.cue_id[1:])
                for cue in old_shots
                if cue.cue_id.startswith("S") and cue.cue_id[1:].isdigit()
            ]
            or [0]
        )
        for source in entries:
            entry = deepcopy(source)
            duration = max(
                TIMELINE_SNAP_SECONDS,
                snap_timeline_seconds(float(entry.get("duration", 5.0))),
            )
            source_id = str(entry.get("cue_id") or "")
            if source_id not in old_by_id:
                next_number += 1
                source_id = f"S{next_number}"
                entry["is_new"] = True
            entry["cue_id"] = source_id
            entry["new_start"] = cursor
            entry["new_end"] = cursor + duration
            entry["duration"] = duration
            cursor += duration
            normalized.append(entry)
        new_duration = max(0.5, snap_timeline_seconds(cursor))
        mapping = {
            entry["cue_id"]: entry
            for entry in normalized
            if entry["cue_id"] in old_by_id
        }

        automatic_dirty_ranges: list[tuple[float, float]] = []
        for old in old_shots:
            entry = mapping.get(old.cue_id)
            if entry is None:
                automatic_dirty_ranges.append((old.start_seconds, old.end_seconds))
                continue
            changed = any(
                (
                    abs(float(entry["new_start"]) - float(old.start_seconds)) > 1e-6,
                    abs(float(entry["new_end"]) - float(old.end_seconds)) > 1e-6,
                    str(entry.get("preset") or old.preset) != old.preset,
                    str(entry.get("framing") or old.framing) != old.framing,
                    str(entry.get("subject_action") or "")
                    != str(old.authored_subject_action or old.subject_action or ""),
                )
            )
            if changed:
                automatic_dirty_ranges.extend(
                    [
                        (old.start_seconds, old.end_seconds),
                        (float(entry["new_start"]), float(entry["new_end"])),
                    ]
                )
        for entry in normalized:
            if entry["cue_id"] not in old_by_id:
                automatic_dirty_ranges.append(
                    (float(entry["new_start"]), float(entry["new_end"]))
                )

        new_shots: list[DirectorCue] = []
        for entry in normalized:
            old = old_by_id.get(entry["cue_id"])
            if old is None:
                cue = DirectorCue(
                    entry["cue_id"],
                    "shot",
                    entry["new_start"],
                    entry["new_end"],
                    str(entry.get("preset") or "New Story Beat"),
                    track_id="V1",
                    framing=str(entry.get("framing") or "Medium-wide"),
                    subject_action=str(entry.get("subject_action") or ""),
                    authored_subject_action=str(entry.get("subject_action") or ""),
                )
            else:
                values = asdict(old)
                values.update({
                    "start_seconds": entry["new_start"],
                    "end_seconds": entry["new_end"],
                    "preset": str(entry.get("preset") or old.preset),
                    "subject_action": str(entry.get("subject_action") or ""),
                    "authored_subject_action": str(entry.get("subject_action") or ""),
                    "h3_executable_action": "",
                    "h3_optional_flourish": "",
                })
                cue = DirectorCue(**values)
            new_shots.append(cue)

        def owner_entry(start: float, end: float, shot_id: str = "") -> tuple[DirectorCue, dict] | None:
            if shot_id and shot_id in old_by_id and shot_id in mapping:
                return old_by_id[shot_id], mapping[shot_id]
            midpoint = (float(start) + float(end)) / 2
            owner = next(
                (
                    cue for cue in old_shots
                    if cue.start_seconds - 1e-6 <= midpoint <= cue.end_seconds + 1e-6
                ),
                None,
            )
            if owner is None or owner.cue_id not in mapping:
                return None
            return owner, mapping[owner.cue_id]

        retained_cues: list[DirectorCue] = []
        for cue in self.director_cues:
            if cue.cue_type == "shot":
                continue
            owned = owner_entry(cue.start_seconds, cue.end_seconds)
            if owned is None:
                continue
            old, entry = owned
            start, end = self._storyboard_map_range(
                cue.start_seconds,
                cue.end_seconds,
                old.start_seconds,
                old.end_seconds,
                entry["new_start"],
                entry["new_end"],
                0.05,
            )
            values = asdict(cue)
            values.update({"start_seconds": start, "end_seconds": end})
            retained_cues.append(DirectorCue(**values))
        self.director_cues = new_shots + retained_cues

        retained_text: list[TextLayer] = []
        for layer in self.text_layers:
            owned = owner_entry(layer.start_seconds, layer.end_seconds, layer.shot_id)
            if owned is None:
                continue
            old, entry = owned
            start, end = self._storyboard_map_range(
                layer.start_seconds,
                layer.end_seconds,
                old.start_seconds,
                old.end_seconds,
                entry["new_start"],
                entry["new_end"],
                0.1,
            )
            values = asdict(layer)
            values.update({
                "start_seconds": start,
                "end_seconds": end,
                "shot_id": entry["cue_id"],
            })
            retained_text.append(text_layer_from_mapping(values))
        self.text_layers = retained_text

        added_clips: list[MediaAsset] = []

        def mapped_media_pieces(asset: MediaAsset) -> list[MediaAsset]:
            if not asset.timeline_placed:
                return []
            pieces: list[MediaAsset] = []
            original_start = float(asset.start_seconds)
            original_end = float(asset.end_seconds)
            original_speed = max(0.01, float(asset.playback_speed))
            for old in old_shots:
                entry = mapping.get(old.cue_id)
                if entry is None:
                    continue
                overlap_start = max(original_start, old.start_seconds)
                overlap_end = min(original_end, old.end_seconds)
                if overlap_end - overlap_start < 0.05:
                    continue
                start, end = self._storyboard_map_range(
                    overlap_start,
                    overlap_end,
                    old.start_seconds,
                    old.end_seconds,
                    entry["new_start"],
                    entry["new_end"],
                    0.05,
                )
                piece = deepcopy(asset)
                piece.timeline_placed = True
                piece.start_seconds = start
                piece.end_seconds = end
                if piece.media_type in {"audio", "video"}:
                    source_start = float(asset.source_in_seconds) + (
                        overlap_start - original_start
                    ) * original_speed
                    source_span = (overlap_end - overlap_start) * original_speed
                    piece.source_in_seconds = max(0.0, source_start)
                    piece.source_out_seconds = piece.source_in_seconds + source_span
                    if piece.source_duration_seconds > 0:
                        piece.source_out_seconds = min(
                            piece.source_duration_seconds, piece.source_out_seconds
                        )
                    piece.playback_speed = max(0.01, source_span / max(0.05, end - start))
                pieces.append(piece)
            return sorted(pieces, key=lambda item: (item.start_seconds, item.end_seconds))

        for asset in self.scan.assets:
            if not asset.timeline_placed:
                continue
            pieces = mapped_media_pieces(asset)
            if not pieces:
                asset.timeline_placed = False
                continue
            first = pieces.pop(0)
            for field_name in TIMELINE_STATE_FIELDS:
                setattr(asset, field_name, getattr(first, field_name))
            for piece in pieces:
                piece.clip_id = f"clip-{secrets.token_hex(8)}"
                piece.source_node_id = asset.node_id
                added_clips.append(piece)

        new_timeline_clips: list[MediaAsset] = []
        for clip in self.scan.timeline_clips:
            pieces = mapped_media_pieces(clip)
            for index, piece in enumerate(pieces):
                if index:
                    piece.clip_id = f"clip-{secrets.token_hex(8)}"
                piece.source_node_id = clip.source_node_id or clip.node_id
                new_timeline_clips.append(piece)
        self.scan.timeline_clips = new_timeline_clips + added_clips
        self._sync_timeline_clip_sources()

        self.storyboard_target_duration_seconds = max(0.5, float(target_duration))
        self._set_design_duration(new_duration)
        self.timeline_tts_stale = True
        self._refresh_director_cues()
        self._refresh_text_layers()
        self.seek_timeline(0.0)
        ranges_to_dirty = list(automatic_dirty_ranges)
        if dirty_ranges is not None:
            ranges_to_dirty.extend(dirty_ranges)
        self.render_dirty_segment_ids = dirty_before
        for range_start, range_end in ranges_to_dirty:
            self._mark_render_range_dirty(range_start, range_end)
        after = self._design_workspace_state()
        self._restore_design_workspace_state(before)
        self.undo_stack.push(
            WorkspaceDesignCommand(
                before,
                after,
                self._restore_design_workspace_state,
                undo_label,
            )
        )
        self._clear_generated_output(preserve_segment_cache=True)
        self._mark_dirty()
        self.quality_profile = "storyboard"
        self.storyboard_preview_active = True
        self.monitor_display_stack.setCurrentWidget(self.monitor_compare_splitter)
        self.render_timeline_at(0.0, force_seek=True)
        delta = self.scan.duration_seconds - self.storyboard_target_duration_seconds
        self.statusBar().showMessage(
            f"Storyboard applied · {old_duration:.1f}s → {self.scan.duration_seconds:.1f}s · "
            f"target {self.storyboard_target_duration_seconds:.1f}s · "
            f"{'over' if delta > 0.01 else 'under' if delta < -0.01 else 'on target'} "
            f"{abs(delta):.1f}s · Undo available"
        )

    def activate_storyboard_preview(self) -> None:
        if hasattr(self, "manual_ripple_action"):
            self.manual_ripple_action.setChecked(False)
        self.quality_profile = "storyboard"
        index = self.quality_profile_combo.findData(self.quality_profile)
        self.quality_profile_combo.blockSignals(True)
        self.quality_profile_combo.setCurrentIndex(max(0, index))
        self.quality_profile_combo.blockSignals(False)
        self._mark_dirty()
        self._activate_storyboard_mode()

    def _mark_latest_preview_rejected(self) -> None:
        self._sync_shot_take_states()
        for state in self.shot_take_states.values():
            if state.get("status") == "preview" and state.get("latest_take"):
                state["status"] = "rejected"
                state["updated_at"] = utc_now_text()

    def _record_generation_takes(
        self,
        request_kind: str,
        seed: int | None,
        outputs: list[dict],
        manifest: dict | None = None,
    ) -> None:
        """Archive one Preview/Final movie per rendered Segment.

        Shot state contains only time-ranged references to those canonical
        Segment movies. This preserves partial rerender while avoiding one
        15-second file name for every Shot that happens to share that Segment.
        """
        root = self._ensure_project_workspace()
        self._sync_shot_take_states()
        master = next(
            (
                Path(str(item.get("local_path", "")))
                for item in outputs
                if Path(str(item.get("local_path", ""))).is_file()
                and media_type_for_path(Path(str(item.get("local_path", "")))) == "video"
            ),
            None,
        )
        rows = [
            row for row in (manifest or {}).get("segments") or []
            if isinstance(row, dict)
        ]
        if not rows:
            rows = [segment.to_dict() for segment in self._planned_render_segments()]
        profile = "motion_preview" if request_kind == "preview" else "approved_final"
        window_start = float(self.clip_start.value())
        window_end = float(self.clip_end.value())
        clear_shot_segment_refs_for_window(
            self.shot_take_states,
            profile=profile,
            start_seconds=window_start,
            end_seconds=window_end,
        )
        shot_ranges = {
            str(cue.cue_id): (float(cue.start_seconds), float(cue.end_seconds))
            for cue in self.director_cues
            if cue.cue_type == "shot"
        }
        affected_shots: set[str] = set()
        for row in rows:
            core_start = float(
                row.get("core_start_seconds", row.get("start_seconds", window_start))
                or row.get("start_seconds", window_start)
            )
            core_end = float(
                row.get("core_end_seconds", row.get("end_seconds", window_end))
                or row.get("end_seconds", window_end)
            )
            shot_ids = [str(value) for value in row.get("shot_ids") or []]
            if not shot_ids:
                shot_ids = [
                    shot_id for shot_id, (shot_start, shot_end) in shot_ranges.items()
                    if shot_end > core_start + 1e-9 and shot_start < core_end - 1e-9
                ]
                row["shot_ids"] = shot_ids
            affected_shots.update(shot_ids)
            candidate = Path(str(row.get("output_path") or ""))
            source = candidate if candidate.is_file() else master
            if source is None or not source.is_file():
                continue
            destination = record_segment_take(
                root,
                segment=row,
                source=source,
                request_kind=request_kind,
                seed=(
                    int(row["seed"])
                    if row.get("seed") is not None
                    else seed
                ),
                segment_states=self.segment_take_states,
                shot_states=self.shot_take_states,
                shot_ranges=shot_ranges,
            )
            # Future Smart Render reuse must point to the durable Workspace,
            # not to a disposable .director_cache path.
            row["output_path"] = str(destination)
            row["download_dir"] = ""
            row["outputs"] = [
                {"kind": "videos", "local_path": str(destination)}
            ]
        now = utc_now_text()
        for shot_id in affected_shots:
            state = self.shot_take_states.get(shot_id)
            if not state:
                continue
            state["take_count"] = max(0, int(state.get("take_count", 0))) + 1
            state["updated_at"] = now
        self._write_shot_state_manifests()

    def _render_cache_root_from_manifest(self, manifest: dict | None) -> Path | None:
        """Return only an exact generated-output run folder safe to reclaim."""
        if not isinstance(manifest, dict):
            return None
        raw_master = str(manifest.get("master_output") or "").strip()
        if not raw_master:
            return None
        candidate = Path(raw_master).expanduser().resolve().parent
        allowed_roots = [(CACHE_ROOT / "generated_outputs").resolve()]
        if self.example_work_dir:
            allowed_roots.append(
                (self.example_work_dir / "cache" / "generated_outputs").resolve()
            )
        for allowed in allowed_roots:
            try:
                relative = candidate.relative_to(allowed)
            except (OSError, ValueError):
                continue
            # Expected shape: generated_outputs/<preview|accepted|final>/<seed>/
            if len(relative.parts) == 2 and relative.parts[0] in {
                "preview", "accepted", "final"
            }:
                return candidate
        return None

    def _make_render_manifest_portable(
        self,
        manifest: dict | None,
        outputs: list[dict],
    ) -> None:
        if not isinstance(manifest, dict):
            return
        stable_master = next(
            (
                Path(str(item.get("local_path") or "")).resolve()
                for item in outputs
                if Path(str(item.get("local_path") or "")).is_file()
                and media_type_for_path(Path(str(item.get("local_path") or "")))
                == "video"
            ),
            None,
        )
        if stable_master is not None:
            manifest["master_output"] = str(stable_master)
            request_kind = str(manifest.get("request_kind") or "").lower()
            cache_key = "preview" if request_kind == "preview" else "production"
            if self.smart_render_manifest:
                self.smart_render_manifest["master_output"] = str(stable_master)
            if cache_key in self.smart_render_manifests:
                self.smart_render_manifests[cache_key]["master_output"] = str(
                    stable_master
                )

    @staticmethod
    def _recover_workspace_render_manifest(workspace_root: Path) -> dict:
        """Recover durable Smart Render state when the Project snapshot is stale.

        A completed master and its Segment Takes are more authoritative than an
        empty ``generated_output`` field. This also rebases a copied Workspace
        whose manifest still names the source computer or the pre-copy folder.
        """
        candidates = [
            workspace_root / "project" / "render_manifest.json",
            workspace_root / "render_manifest.json",
        ]
        render_jobs = workspace_root / "project" / "render_jobs"
        if render_jobs.is_dir():
            candidates.extend(render_jobs.glob("*.manifest.json"))
        candidates = [candidate for candidate in candidates if candidate.is_file()]
        recovered: list[tuple[tuple[int, str, int], dict]] = []
        for candidate in candidates:
            try:
                loaded = json.loads(candidate.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError, TypeError):
                continue
            if not isinstance(loaded, dict):
                continue

            request_kind = str(loaded.get("request_kind") or "final").lower()
            is_preview = request_kind == "preview"
            stable_master = workspace_root / (
                "generated_preview.mp4" if is_preview else "generated_output.mp4"
            )
            if stable_master.is_file():
                loaded["master_output"] = str(stable_master.resolve())

            take_name = "motion_preview.mp4" if is_preview else "approved_final.mp4"
            for row in loaded.get("segments") or []:
                if not isinstance(row, dict):
                    continue
                segment_id = str(row.get("segment_id") or "").strip()
                if not segment_id:
                    continue
                durable_take = (
                    workspace_root / "segments" / segment_id / "takes" / take_name
                )
                if durable_take.is_file():
                    resolved_take = str(durable_take.resolve())
                    row["output_path"] = resolved_take
                    row["download_dir"] = ""
                    row["outputs"] = [
                        {"kind": "videos", "local_path": resolved_take}
                    ]

            completed = sum(
                1
                for row in loaded.get("segments") or []
                if isinstance(row, dict)
                and str(row.get("status") or "").lower()
                in {"cached", "complete", "completed", "reusable"}
                and Path(str(row.get("output_path") or "")).is_file()
            )
            recovered.append(
                (
                    (
                        completed,
                        str(loaded.get("updated_at") or ""),
                        int(candidate.stat().st_mtime_ns),
                    ),
                    loaded,
                )
            )
        if not recovered:
            return {}
        # A newer failed checkpoint must never hide an older checkpoint that
        # contains more durable completed Segment Takes.
        return max(recovered, key=lambda item: item[0])[1]

    @staticmethod
    def _render_manifest_recovery_score(manifest: dict | None) -> tuple[int, str]:
        if not isinstance(manifest, dict):
            return (0, "")
        completed = sum(
            1
            for row in manifest.get("segments") or []
            if isinstance(row, dict)
            and str(row.get("status") or "").lower()
            in {"cached", "complete", "completed", "reusable"}
            and Path(str(row.get("output_path") or "")).is_file()
        )
        return completed, str(manifest.get("updated_at") or "")

    def _cleanup_completed_render_cache(
        self,
        cache_root: Path | None,
        manifest: dict | None,
    ) -> bool:
        """Reclaim a completed run only after every durable asset is verified."""
        if cache_root is None or not cache_root.is_dir() or not isinstance(manifest, dict):
            return False
        workspace = self._ensure_project_workspace().resolve()
        master = Path(str(manifest.get("master_output") or ""))
        if not master.is_file():
            return False
        try:
            master.resolve().relative_to(workspace)
        except (OSError, ValueError):
            return False
        for row in manifest.get("segments") or []:
            if not isinstance(row, dict):
                return False
            output = Path(str(row.get("output_path") or ""))
            if not output.is_file():
                return False
            try:
                output.resolve().relative_to((workspace / "segments").resolve())
            except (OSError, ValueError):
                return False
        shutil.rmtree(cache_root)
        return True

    def _archive_generated_outputs(
        self,
        outputs: list[dict],
        request_kind: str,
    ) -> list[dict]:
        """Publish one stable user-facing preview/final master in the Workspace.

        Per-Shot Takes remain under ``shots`` for editable Smart Render. Full assembled
        masters are intentionally not duplicated again under renders/takes.
        """
        folder = self._ensure_project_workspace()
        archived = [dict(item) for item in outputs]
        preferred_index: int | None = None
        # ComfyUI can return SaveImage previews before the actual movie. Always
        # archive the first valid video; use an image only when no video exists.
        for wanted_kind in ("video", "image"):
            for index, item in enumerate(outputs):
                source = Path(str(item.get("local_path", "")))
                if source.is_file() and media_type_for_path(source) == wanted_kind:
                    preferred_index = index
                    break
            if preferred_index is not None:
                break
        if preferred_index is None:
            return archived

        source = Path(str(outputs[preferred_index].get("local_path", "")))
        kind = media_type_for_path(source)
        suffix = source.suffix or (".mp4" if kind == "video" else ".png")
        render_kind = "preview" if request_kind == "preview" else "final"
        destination = folder / (
            ("generated_preview" if render_kind == "preview" else "generated_output")
            + suffix
        )
        if self.generated_player.source().toLocalFile():
            try:
                playing = Path(self.generated_player.source().toLocalFile()).resolve()
                if playing == destination.resolve():
                    self.generated_player.stop()
                    self.generated_player.setSource(QUrl())
            except OSError:
                pass
        if source.resolve() != destination.resolve():
            link_or_copy(source, destination)
        archived[preferred_index]["local_path"] = str(destination.resolve())
        archived[preferred_index]["workspace_take"] = str(destination.resolve())
        return archived

    def _auto_save_example_project(self) -> Path | None:
        if not self.scan or not self.generated_output_path:
            return None
        folder = self._ensure_project_workspace()
        destination = workspace_project_path(folder)
        destination.write_text(
            json.dumps(self._project_payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if self.smart_render_manifest:
            manifest_text = json.dumps(
                self.smart_render_manifest, ensure_ascii=False, indent=2
            )
            (folder / "project" / "render_manifest.json").write_text(
                manifest_text, encoding="utf-8"
            )
            (folder / "render_manifest.json").write_text(
                manifest_text, encoding="utf-8"
            )
        self.project_path = destination.resolve()
        self.project_dirty = False
        self.undo_stack.setClean()
        self._update_window_title()
        return destination.resolve()

    def _checkpoint_smart_render_state(self) -> Path | None:
        """Persist a partial long render without pretending the edit is done.

        The worker reports a manifest after every completed or failed hidden
        Segment. Saving it here lets Open Project reconstruct the reusable
        front of a 120-second job and continue from the first unfinished unit.
        """
        if not self.scan or not self.smart_render_manifest:
            return None
        folder = self._ensure_project_workspace()
        destination = workspace_project_path(folder)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self._project_payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(destination)

        manifest_path = folder / "project" / "render_manifest.json"
        manifest_temp = manifest_path.with_suffix(".json.tmp")
        manifest_temp.write_text(
            json.dumps(
                self.smart_render_manifest, ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
        manifest_temp.replace(manifest_path)
        self.project_path = destination.resolve()
        self._update_window_title()
        return destination.resolve()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if (
            hasattr(self, "media_scroll")
            and watched is self.media_scroll.viewport()
            and event.type() == QEvent.Resize
        ):
            QTimer.singleShot(0, self._reflow_media_pool)
        if watched is getattr(self, "generation_toolbar", None):
            if event.type() == QEvent.Resize:
                QTimer.singleShot(0, self._reflow_generation_toolbar)
        if (
            isinstance(watched, QWidget)
            and bool(watched.property("generation_hover_help"))
        ):
            if event.type() == QEvent.Enter and watched.toolTip():
                QToolTip.showText(
                    watched.mapToGlobal(QPoint(0, watched.height() + 3)),
                    watched.toolTip(),
                    watched,
                )
            elif event.type() == QEvent.Leave:
                QToolTip.hideText()
        return super().eventFilter(watched, event)

    def _reflow_media_pool(self) -> None:
        if not self.media_card_order:
            return
        viewport_width = max(1, self.media_scroll.viewport().width() - 10)
        spacing = self.media_grid.horizontalSpacing()
        margins = self.media_grid.contentsMargins()
        available = max(1, viewport_width - margins.left() - margins.right())
        columns = max(1, min(len(self.media_card_order), MEDIA_POOL_COLUMNS))
        card_width = max(
            MEDIA_CARD_MIN_WIDTH,
            (available - max(0, columns - 1) * spacing) // columns,
        )
        previous_columns = getattr(self, "_media_grid_columns", 0)
        for column in range(previous_columns):
            self.media_grid.setColumnStretch(column, 0)
        while self.media_grid.count():
            self.media_grid.takeAt(0)
        for index, card in enumerate(self.media_card_order):
            card.setMinimumWidth(card_width)
            card.setMaximumWidth(card_width)
            self.media_grid.addWidget(card, index // columns, index % columns)
        for column in range(columns):
            self.media_grid.setColumnStretch(column, 1)
        self._media_grid_columns = columns

    def _append_media_card(self, asset: MediaAsset) -> MediaCard:
        card = MediaCard(asset)
        card.selected.connect(self.select_asset)
        card.file_dropped.connect(self.load_asset_file)
        card.z_image_regeneration_requested.connect(
            self.regenerate_media_asset_with_z_image
        )
        self.cards[asset.node_id] = card
        self.media_card_order.append(card)
        QTimer.singleShot(0, self._reflow_media_pool)
        return card

    def _show_immediate_image_preview(self, asset: MediaAsset) -> bool:
        """Bind a valid local Picture directly to its card and in-memory cache.

        Media Preparation may later replace this with a transparent derivative
        or another optimized preview. Failure or delay in that background job
        can no longer leave a real Picture card showing DROP MEDIA.
        """
        if asset.media_type != "image":
            return False
        source = Path(str(asset.local_path or ""))
        if not source.is_file():
            return False
        card = self.cards.get(asset.node_id)
        if card is None or not card.set_local_image_fallback():
            return False
        self.preview_paths[asset.node_id] = source.resolve()
        return True

    def _rebuild_media_cards(self) -> None:
        self.cards.clear()
        self.media_card_order.clear()
        while self.media_grid.count():
            item = self.media_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if self.scan:
            for asset in self.scan.assets:
                self._append_media_card(asset)
        self._refresh_virtual_media_header()

    def _refresh_virtual_media_header(self) -> None:
        if not self.scan:
            self.media_header.setText("VIRTUAL MEDIA POOL · waiting for API")
            return
        logical = self.scan.logical_counts
        capacity = self.scan.counts
        self.media_header.setText(
            "VIRTUAL MEDIA POOL · "
            f"{logical['image']}I · {logical['video']}V · {logical['audio']}A "
            f"· SEG {capacity['image']}/{capacity['video']}/{capacity['audio']}"
        )

    def add_virtual_media(self, media_type: str) -> None:
        if not self.scan:
            QMessageBox.information(self, "Virtual Media Pool", "Load the H3 API workflow first.")
            return
        filters = {
            "image": "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
            "video": "Videos (*.mp4 *.mov *.mkv *.webm *.avi)",
            "audio": "Audio (*.wav *.mp3 *.flac *.m4a *.aac *.ogg)",
        }
        filename, _ = QFileDialog.getOpenFileName(
            self,
            f"Add virtual {media_type}",
            str(self.example_work_dir or PROJECT_ROOT),
            filters.get(media_type, "All media (*.*)"),
        )
        if not filename:
            return
        asset = create_virtual_media_asset(self.scan, media_type)
        self._append_media_card(asset)
        self._refresh_virtual_media_header()
        self.load_asset_file(asset, filename)
        self._mark_dirty()

    def _connect_dirty_signals(self) -> None:
        for name in (
            "brief", "style", "shots", "dialogue", "transition", "ending",
            "constraints", "soundscape", "music",
        ):
            getattr(self.prompt_panel, name).textChanged.connect(self._mark_dirty)
            getattr(self.prompt_panel, name).textChanged.connect(self._mark_prompt_render_dirty)
        self.special_combo.currentIndexChanged.connect(self._mark_dirty)
        self.special_combo.currentIndexChanged.connect(self._mark_all_render_segments_dirty)
        self.special_combo.currentIndexChanged.connect(self._refresh_skill_binding_display)
        self.special_combo.currentIndexChanged.connect(
            self._special_skill_production_strategy_changed
        )
        self.special_combo.currentIndexChanged.connect(
            lambda _value: self.schedule_prompt_generation()
        )
        self.clip_start.valueChanged.connect(self._mark_dirty)
        self.clip_end.valueChanged.connect(self._mark_dirty)
        self.clip_start.valueChanged.connect(lambda _value: self._refresh_render_status_bar())
        self.clip_end.valueChanged.connect(lambda _value: self._refresh_render_status_bar())
        self.clip_start.valueChanged.connect(lambda _value: self.schedule_prompt_generation())
        self.clip_end.valueChanged.connect(lambda _value: self.schedule_prompt_generation())
        self.server_url.textChanged.connect(self._mark_dirty)
        self.prompt_panel.auto_sync.toggled.connect(self._mark_dirty)

    def _refresh_skill_binding_display(self, *_args) -> None:
        special_key = self.special_combo.currentData()
        special = None if special_key == NONE_SPECIAL else self.profiles.get(special_key)
        standalone = bool(special and special.standalone)
        self.default_skill_label.setText("Default Skill (not bound)" if standalone else "Default Skill")
        self.default_skill_combo.setItemText(
            0,
            "Not bound · standalone Special"
            if standalone
            else self.profiles[DEFAULT_SKILL].display_name,
        )
        self.special_skill_label.setText("Standalone Special" if standalone else "+ Special")

    def open_special_skill_creator(self) -> None:
        dialog = SpecialSkillCreatorDialog(PROJECT_ROOT / "skill special", self)
        current_key = str(self.special_combo.currentData() or "")
        if current_key and current_key != NONE_SPECIAL:
            index = dialog.skill_selector.findData(current_key)
            if index >= 0:
                dialog.skill_selector.setCurrentIndex(index)
        if dialog.exec() != QDialog.Accepted or not dialog.saved_key:
            return
        self._reload_skill_profiles(dialog.saved_key)

    def _reload_skill_profiles(self, selected_special: str = NONE_SPECIAL) -> None:
        self.profiles = load_skill_profiles(PROJECT_ROOT)
        self.default_skill_combo.setItemText(
            0, self.profiles[DEFAULT_SKILL].display_name
        )
        self.special_combo.blockSignals(True)
        self.special_combo.clear()
        self.special_combo.addItem("None", NONE_SPECIAL)
        for key, profile in sorted(self.profiles.items()):
            if profile.special:
                self.special_combo.addItem(profile.display_name, key)
        selected_index = self.special_combo.findData(selected_special)
        self.special_combo.setCurrentIndex(max(0, selected_index))
        self.special_combo.blockSignals(False)
        self._refresh_skill_binding_display()
        self._special_skill_production_strategy_changed()
        self._mark_dirty()
        self._mark_all_render_segments_dirty()
        self.schedule_prompt_generation()

    def _mark_dirty(self, *_args) -> None:
        if self.restoring_project:
            return
        self.project_dirty = True
        self._update_window_title()

    def _mark_prompt_render_dirty(self) -> None:
        # Auto-synced Shot/Dialogue/Ending text is already represented by the
        # exact local cue/layer range that caused it.
        if not self.prompt_sync_in_progress:
            self._mark_all_render_segments_dirty()

    def _continuity_mode_at_boundary(
        self,
        seconds: float,
        explicit: str = "Auto",
    ) -> str:
        """Resolve a Shot boundary to one safe hidden-render continuity policy."""
        normalized = explicit.strip().lower().replace(" ", "_").replace("-", "_")
        if normalized in {"hard_cut", "match_action", "motion_reference", "transition"}:
            return normalized
        tolerance = TIMELINE_SNAP_SECONDS / 2 + 1e-6
        nearby = [
            cue for cue in self.director_cues
            if cue.cue_type in {"cut", "transition"}
            and abs(cue.start_seconds - seconds) <= tolerance
        ]
        if any(cue.cue_type == "cut" for cue in nearby):
            return "hard_cut"
        transition = next((cue for cue in nearby if cue.cue_type == "transition"), None)
        if transition:
            preset = transition.preset.strip().lower()
            if "hard cut" in preset:
                return "hard_cut"
            if "match" in preset:
                return "match_action"
            return "transition"
        # Auto continuity now carries one second of motion history (exactly
        # 24 frames at 24 fps) into the next native H3 window.  An authored
        # Hard Cut remains a deliberate context reset, while an explicit
        # Match Action can still request the lighter text-only state contract.
        return "motion_reference"

    def _planned_render_segments(self):
        """Return the hidden render windows represented by the current work area."""
        if not self.scan:
            return []
        start = float(self.clip_start.value())
        end = float(self.clip_end.value())
        if end <= start:
            return []
        keyframe_boundaries = {start, end}
        if is_drone_special_skill(self.special_combo.currentData()):
            for asset in self.scan.timeline_assets():
                if asset.media_type != "image" or not asset.timeline_placed:
                    continue
                direction = str(asset.clip_prompt or "")
                if not (
                    "SCENE KEYFRAME CHAIN ANCHOR" in direction
                    or "AUTO TERMINAL KEYFRAME" in direction
                ):
                    continue
                clipped_start = max(start, float(asset.start_seconds))
                clipped_end = min(end, float(asset.end_seconds))
                if clipped_end > clipped_start + 1e-6:
                    keyframe_boundaries.update((clipped_start, clipped_end))
        keyframe_chain_active = len(keyframe_boundaries) > 2
        if keyframe_chain_active:
            # A later Picture must never be present in the same native H3
            # request as an earlier scene anchor. Render each ownership range
            # independently and carry only the previous final 24 video frames
            # forward as motion context.
            planned = []
            ordered = sorted(keyframe_boundaries)
            for range_start, range_end in zip(ordered, ordered[1:]):
                if range_end <= range_start + 1e-6:
                    continue
                planned.extend(plan_render_segments(
                    range_start,
                    range_end,
                    max_segment_seconds=MAX_NATIVE_SECONDS,
                    overlap_seconds=0.0,
                ))
        elif end - start > MAX_NATIVE_SECONDS + 1e-6:
            shots = [
                asdict(cue) for cue in self.director_cues
                if cue.cue_type == "shot"
                and ranges_intersect(cue.start_seconds, cue.end_seconds, start, end)
            ]
            for row in shots:
                row["continuity_mode"] = self._continuity_mode_at_boundary(
                    float(row["start_seconds"]),
                    str(row.get("continuity_mode", "Auto")),
                )
            coverage = 0.0
            coverage_end = start
            for row in sorted(shots, key=lambda item: float(item["start_seconds"])):
                row_start = max(start, float(row["start_seconds"]))
                row_end = min(end, float(row["end_seconds"]))
                if row_end <= row_start:
                    continue
                if row_start > coverage_end:
                    coverage += row_end - row_start
                elif row_end > coverage_end:
                    coverage += row_end - max(row_start, coverage_end)
                coverage_end = max(coverage_end, row_end)
            # Sparse cue collections are annotations, not a complete edit
            # decision list. Use Shot units only when they describe most of the
            # work area; otherwise retain the proven 15-second planner.
            if shots and coverage >= (end - start) * 0.8:
                planned = plan_shot_render_segments(
                    start,
                    end,
                    shots,
                    # Independent 3-5 second H3 jobs repeatedly re-establish
                    # the same reference scene. Pack micro-Shots into the
                    # longest native window; a 45-second design becomes three
                    # coherent 15-second generation jobs.
                    min_segment_seconds=MAX_NATIVE_SECONDS,
                    max_segment_seconds=MAX_NATIVE_SECONDS,
                    overlap_seconds=0.0,
                )
            else:
                planned = plan_render_segments(
                    start,
                    end,
                    max_segment_seconds=MAX_NATIVE_SECONDS,
                    overlap_seconds=0.0,
                )
        else:
            planned = plan_render_segments(
                start,
                end,
                max_segment_seconds=MAX_NATIVE_SECONDS,
                overlap_seconds=0.0,
            )
        for index, segment in enumerate(planned):
            if index == 0:
                segment.continuity_mode = "none"
            elif keyframe_chain_active:
                # Scene-anchor isolation is a deliberate visual handoff: no
                # Picture or soundtrack crosses the boundary, only the prior
                # segment's final 24 silent frames.
                segment.continuity_mode = "motion_reference"
            elif segment.continuity_mode in {"", "auto", "match_action"}:
                segment.continuity_mode = self._continuity_mode_at_boundary(
                    segment.start_seconds
                )
        if not keyframe_chain_active:
            planned = protect_segment_boundaries_from_speech(
                planned,
                [asdict(layer) for layer in self.text_layers],
                max_segment_seconds=MAX_NATIVE_SECONDS,
                tail_seconds=1.0,
                grid_seconds=TIMELINE_SNAP_SECONDS,
            )
            planned = align_segments_to_dialogue_turns(
                planned,
                [asdict(layer) for layer in self.text_layers],
                max_segment_seconds=MAX_NATIVE_SECONDS,
                grid_seconds=TIMELINE_SNAP_SECONDS,
            )
        shots_in_area = [
            cue for cue in self.director_cues
            if cue.cue_type == "shot"
            and ranges_intersect(cue.start_seconds, cue.end_seconds, start, end)
        ]
        for index, segment in enumerate(planned):
            unit_start = float(
                segment.core_start_seconds
                if segment.core_start_seconds is not None
                else segment.start_seconds
            )
            unit_end = float(
                segment.core_end_seconds
                if segment.core_end_seconds is not None
                else segment.end_seconds
            )
            segment.index = index
            segment.shot_ids = [
                cue.cue_id for cue in shots_in_area
                if ranges_intersect(
                    cue.start_seconds, cue.end_seconds, unit_start, unit_end
                )
            ] or segment.shot_ids
        return planned

    def _render_status_rows(self) -> list[dict]:
        """Merge planned windows, cached outputs, edits, and live worker state."""
        planned = self._planned_render_segments()
        cached_manifest = self.smart_render_manifests.get("production", {})
        cached_by_id = {
            str(row.get("segment_id", "")): row
            for row in (
                cached_manifest.get("segments", [])
                if int(cached_manifest.get("render_policy_version", 0))
                == SMART_RENDER_POLICY_VERSION
                else []
            )
            if isinstance(row, dict)
        }
        rows: list[dict] = []
        for segment in planned:
            segment_id = segment.segment_id
            cached = cached_by_id.get(segment_id, {})
            cached_status = str(cached.get("status", "")).lower()
            cached_output = Path(str(cached.get("output_path", "")))
            runtime = self.render_runtime_status.get(segment_id, "")
            if runtime in {"running", "failed"}:
                status = runtime
            elif segment_id in self.render_dirty_segment_ids:
                status = "dirty"
            elif cached_status == "failed":
                status = "failed"
            elif cached_output.is_file() and cached_status in {
                "cached", "complete", "completed", "reusable",
            }:
                status = "reusable"
            elif (
                len(planned) == 1
                and self.generated_output_path
                and self.generated_output_path.is_file()
                and self.submit_request_kind != "preview"
                and abs(self.generated_output_timeline_start - segment.start_seconds) < 1e-6
            ):
                status = "reusable"
            else:
                status = "pending"
            row = segment.to_dict()
            row["display_status"] = status
            rows.append(row)
        return rows

    def _refresh_render_status_bar(self) -> None:
        if hasattr(self, "timeline"):
            self.timeline.set_render_segments(self._render_status_rows())

    def _mark_render_range_dirty(self, start_seconds: float, end_seconds: float) -> None:
        if self.restoring_project:
            return
        start = min(float(start_seconds), float(end_seconds))
        end = max(float(start_seconds), float(end_seconds))
        for segment in self._planned_render_segments():
            unit_start = (
                segment.core_start_seconds
                if segment.core_start_seconds is not None
                else segment.start_seconds
            )
            unit_end = (
                segment.core_end_seconds
                if segment.core_end_seconds is not None
                else segment.end_seconds
            )
            if ranges_intersect(start, end, unit_start, unit_end):
                self.render_dirty_segment_ids.add(segment.segment_id)
                self.render_runtime_status.pop(segment.segment_id, None)
        self._refresh_render_status_bar()

    def _mark_render_states_dirty(self, *states: dict) -> None:
        for state in states:
            if "timeline_placed" in state and not bool(state.get("timeline_placed")):
                continue
            self._mark_render_range_dirty(
                float(state.get("start_seconds", 0.0)),
                float(state.get("end_seconds", state.get("start_seconds", 0.0))),
            )

    def _mark_all_render_segments_dirty(self) -> None:
        if self.restoring_project:
            return
        for segment in self._planned_render_segments():
            self.render_dirty_segment_ids.add(segment.segment_id)
            self.render_runtime_status.pop(segment.segment_id, None)
        self._refresh_render_status_bar()

    def _update_window_title(self) -> None:
        name = self.project_path.name if self.project_path else "Untitled Director Project"
        marker = " *" if self.project_dirty else ""
        self.setWindowTitle(
            f"MiniMax H3 Director Cut Studio v{APP_VERSION} — {name}{marker}"
        )

    def _project_payload(self) -> dict:
        if not self.scan:
            raise RuntimeError("No workflow is loaded.")
        self._read_settings_ui()
        self._sync_shot_take_states()
        prompt = {
            name: getattr(self.prompt_panel, name).toPlainText()
            for name in (
                "brief", "style", "shots", "dialogue", "transition", "ending",
                "constraints", "soundscape", "music", "output",
            )
        }
        assets = {}
        for asset in self.scan.assets:
            assets[asset.node_id] = {
                "node_id": asset.node_id,
                "class_type": asset.class_type,
                "media_type": asset.media_type,
                "tag": asset.tag,
                "binding": asset.binding,
                "paired_audio_binding": asset.paired_audio_binding,
                "reference_id": stable_reference_id(asset),
                "is_virtual": asset.is_virtual,
                "filename": asset.filename,
                "local_path": asset.local_path,
                "recognition": asset.recognition,
                "semantic_enrichment": asset.semantic_enrichment,
                "semantic_enrichment_source_hash": asset.semantic_enrichment_source_hash,
                "semantic_enrichment_model": asset.semantic_enrichment_model,
                "semantic_enrichment_updated_at": asset.semantic_enrichment_updated_at,
                "activation_mode": asset.activation_mode,
                "timeline_placed": asset.timeline_placed,
                "timeline_lane": asset.timeline_lane,
                "timeline_track_id": asset.timeline_track_id,
                "start_seconds": asset.start_seconds,
                "end_seconds": asset.end_seconds,
                "source_duration_seconds": asset.source_duration_seconds,
                "playback_speed": asset.playback_speed,
                "source_in_seconds": asset.source_in_seconds,
                "source_out_seconds": asset.source_out_seconds,
                "fade_in_seconds": asset.fade_in_seconds,
                "fade_out_seconds": asset.fade_out_seconds,
                "transition_in": asset.transition_in,
                "transition_out": asset.transition_out,
                "clip_prompt": asset.clip_prompt,
                "monitor_visible": asset.monitor_visible,
            }
        return {
            "format": "h3-director-project",
            "version": PROJECT_FORMAT_VERSION,
            "application_version": APP_VERSION,
            "workflow_path": str(self.scan.path),
            "timeline_duration_seconds": self.scan.duration_seconds,
            "storyboard_target_duration_seconds": self.storyboard_target_duration_seconds,
            "storyboard_view_mode": self.storyboard_view_mode,
            "smart_cut_last_plan": deepcopy(self.smart_cut_last_plan),
            "production_strategy": self.production_strategy,
            "production_batch_seconds": self.production_batch_seconds,
            "incremental_production": {
                "approved_horizon_seconds": self.incremental_approved_horizon,
                "pending_start_seconds": self.incremental_pending_start,
                "pending_end_seconds": self.incremental_pending_end,
                "phase": self.incremental_batch_phase,
                "preview_seed": self.preview_seed,
                "preview_ready": self.preview_ready,
            },
            "work_area": [self.clip_start.value(), self.clip_end.value()],
            "playhead_seconds": self.playhead_seconds,
            "special_skill": self.special_combo.currentData(),
            "prompt_auto_sync": self.prompt_panel.auto_sync.isChecked(),
            "server_url": self.server_url.text().strip(),
            "render_settings": asdict(self.render_settings),
            "prompt": prompt,
            "assets": assets,
            "timeline_clips": [asdict(clip) for clip in self.scan.timeline_clips],
            "tracks": [asdict(track) for track in self.tracks],
            "text_layers": [asdict(layer) for layer in self.text_layers],
            "authored_text_requirements": deepcopy(
                self.authored_text_requirements
            ),
            "director_cues": [asdict(cue) for cue in self.director_cues],
            "smart_render": self.smart_render_manifest,
            "smart_render_manifests": self.smart_render_manifests,
            "render_dirty_segment_ids": sorted(self.render_dirty_segment_ids),
            "workspace_layout_version": WORKSPACE_LAYOUT_VERSION,
            "workspace_id": self.project_workspace_id,
            "workspace_root": str(self.example_work_dir) if self.example_work_dir else "",
            "legacy_project_source": (
                str(self.legacy_project_source) if self.legacy_project_source else ""
            ),
            "quality_profile": self.quality_profile,
            "shot_take_states": deepcopy(self.shot_take_states),
            "segment_take_states": deepcopy(self.segment_take_states),
            "example_work_dir": str(self.example_work_dir) if self.example_work_dir else "",
            "monitor_compare_sizes": self.monitor_compare_splitter.sizes(),
            "generated_output_timeline_start": self.generated_output_timeline_start,
            "generated_output_request_kind": self.submit_request_kind,
            "generated_output": (
                str(self.generated_output_path)
                if self.generated_output_path and self.generated_output_path.is_file()
                else ""
            ),
        }

    def save_project(self) -> bool:
        if not self.scan:
            return False
        destination = self.project_path
        if destination is None:
            destination = workspace_project_path(self._ensure_project_workspace())
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._write_shot_state_manifests()
        destination.write_text(json.dumps(self._project_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        self.project_path = destination.resolve()
        self.project_dirty = False
        self.undo_stack.setClean()
        self._update_window_title()
        self.statusBar().showMessage(f"Project saved: {destination.name}")
        return True

    def open_project_storage(self) -> None:
        """Open the auditable storage tool only for a durable saved Workspace."""
        if not self.scan:
            QMessageBox.information(
                self,
                "Project Storage",
                "Load an API workflow or open a Project first.",
            )
            return
        if self.project_dirty or self.project_path is None:
            if not self.save_project():
                QMessageBox.warning(
                    self,
                    "Project Storage",
                    "Save the Project before inspecting or archiving its Workspace.",
                )
                return
        workspace = self._ensure_project_workspace()
        dialog = ProjectStorageDialog(workspace, self)
        dialog.exec()
        dialog.deleteLater()

    def open_project(self) -> None:
        start_folder = (
            self.project_path.parent
            if self.project_path and self.project_path.parent.is_dir()
            else self.example_work_dir
            if self.example_work_dir and self.example_work_dir.is_dir()
            else DESIGN_EXAMPLE_ROOT
        )
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Director Project",
            str(start_folder),
            "H3 Director Project (*.h3director.json);;JSON (*.json)",
        )
        if filename:
            self.load_project_path(Path(filename))

    def load_project_path(self, path: Path) -> None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if payload.get("format") != "h3-director-project":
                raise ValueError("This is not an H3 Director Project file.")
            payload, integrity_repairs = repair_project_payload(payload)
            recovered_workspace_state = False
            opened_project_path = path.resolve()
            is_legacy_project = (
                int(payload.get("version", 0)) < PROJECT_FORMAT_VERSION
                or int(payload.get("workspace_layout_version", 0))
                < WORKSPACE_LAYOUT_VERSION
            )
            workspace_root = locate_workspace_for_project(opened_project_path, payload)
            manifest = ensure_workspace_layout(
                workspace_root,
                display_name=opened_project_path.stem,
                workspace_id=str(payload.get("workspace_id") or ""),
                legacy_project_path=opened_project_path if is_legacy_project else None,
            )
            workflow_path = Path(payload["workflow_path"])
            if not workflow_path.is_file():
                for portable_workflow in (
                    workspace_root / workflow_path.name,
                    workspace_root / "workflow" / workflow_path.name,
                    PROJECT_ROOT / workflow_path.name,
                ):
                    if portable_workflow.is_file():
                        workflow_path = portable_workflow
                        break
            if not workflow_path.is_file():
                raise FileNotFoundError(f"Workflow not found: {workflow_path}")
            self._clear_generated_output()
            self.restoring_project = True
            self.load_workflow_path(workflow_path)
            saved_duration = payload.get("timeline_duration_seconds")
            if saved_duration is not None:
                self._set_design_duration(max(0.5, float(saved_duration)))
            saved_story_target = payload.get("storyboard_target_duration_seconds")
            if saved_story_target is None:
                saved_story_target = self._storyboard_target_from_workspace(
                    workspace_root,
                    float(saved_duration)
                    if saved_duration is not None
                    else self.scan.duration_seconds,
                )
            self.storyboard_target_duration_seconds = max(
                0.5, float(saved_story_target)
            )
            saved_view_mode = str(
                payload.get("storyboard_view_mode", "large_icons")
            )
            self.storyboard_view_mode = (
                saved_view_mode
                if saved_view_mode in StoryboardBlockList.DISPLAY_MODES
                else "large_icons"
            )
            self.smart_cut_last_plan = deepcopy(
                payload.get("smart_cut_last_plan") or {}
            )
            self.storyboard_target_spin.blockSignals(True)
            self.storyboard_target_spin.setValue(
                self.storyboard_target_duration_seconds
            )
            self.storyboard_target_spin.blockSignals(False)
            if hasattr(self, "manual_ripple_action"):
                self.manual_ripple_action.setChecked(False)
            self.storyboard_trim_active = False
            self._refresh_storyboard_trim_controls()
            track_rows = payload.get("tracks") or []
            if track_rows:
                self.tracks = [TimelineTrack(**row) for row in track_rows]
                self.timeline.set_tracks(self.tracks)
                self._rebuild_track_headers()
            self.text_layers = [
                text_layer_from_mapping(row)
                for row in payload.get("text_layers", [])
                if isinstance(row, dict)
            ]
            if self._normalize_text_layer_tracks():
                self.timeline.set_tracks(self.tracks)
                self._rebuild_track_headers()
            self.authored_text_requirements = deepcopy(
                payload.get("authored_text_requirements") or []
            )
            self.timeline.set_text_layers(self.text_layers)
            self.director_cues = [
                DirectorCue(**row) for row in payload.get("director_cues", [])
            ]
            self.timeline.set_director_cues(self.director_cues)
            asset_map = {asset.node_id: asset for asset in self.scan.assets}  # type: ignore[union-attr]
            # Project v18+ persists logical P10/A4/V4 sources.  Recreate those
            # cards before resolving files or Timeline clip instances.
            for node_id, saved in payload.get("assets", {}).items():
                if node_id in asset_map or not isinstance(saved, dict):
                    continue
                if not bool(saved.get("is_virtual")):
                    continue
                media_type = str(saved.get("media_type", "")).lower()
                reference_id = str(saved.get("reference_id", "")).upper()
                virtual = create_virtual_media_asset(
                    self.scan,  # type: ignore[arg-type]
                    media_type,
                    reference_id=reference_id,
                    node_id=str(node_id),
                )
                asset_map[virtual.node_id] = virtual
                self._append_media_card(virtual)
            self._refresh_virtual_media_header()
            raw_saved_work_dir = str(payload.get("example_work_dir") or "").strip()
            saved_media_root = Path(raw_saved_work_dir) if raw_saved_work_dir else None
            for node_id, saved in payload.get("assets", {}).items():
                asset = asset_map.get(node_id)
                if not asset:
                    continue
                resolved_media = resolve_project_media_path(
                    path, saved, saved_media_root
                )
                if resolved_media is not None:
                    assign_local_media(self.scan, asset, resolved_media)  # type: ignore[arg-type]
                    self._show_immediate_image_preview(asset)
                for name in (
                    "reference_id",
                    "is_virtual",
                    "recognition",
                    "semantic_enrichment",
                    "semantic_enrichment_source_hash",
                    "semantic_enrichment_model",
                    "semantic_enrichment_updated_at",
                    "activation_mode",
                    "timeline_placed",
                    "timeline_lane",
                    "timeline_track_id",
                    "start_seconds",
                    "end_seconds",
                    "source_duration_seconds",
                    "playback_speed",
                    "source_in_seconds",
                    "source_out_seconds",
                    "fade_in_seconds",
                    "fade_out_seconds",
                    "transition_in",
                    "transition_out",
                    "clip_prompt",
                    "monitor_visible",
                ):
                    if name in saved:
                        setattr(asset, name, saved[name])
                if resolved_media is None:
                    asset.filename = str(saved.get("filename") or asset.filename)
                    asset.local_path = ""
                if resolved_media is not None:
                    self.queue_media_preparation(
                        asset,
                        auto_analyze=False,
                        preserve_recognition=True,
                    )
            self.scan.timeline_clips = []  # type: ignore[union-attr]
            for saved_clip in payload.get("timeline_clips", []):
                if not isinstance(saved_clip, dict):
                    continue
                source_node_id = str(
                    saved_clip.get("source_node_id") or saved_clip.get("node_id") or ""
                )
                source = asset_map.get(source_node_id)
                if source is None:
                    continue
                values = asdict(source)
                values.update(saved_clip)
                values["node_id"] = source.node_id
                values["source_node_id"] = source.node_id
                values["clip_id"] = str(values.get("clip_id") or f"clip-{secrets.token_hex(8)}")
                self.scan.timeline_clips.append(MediaAsset(**values))  # type: ignore[union-attr]
            self._sync_timeline_clip_sources()
            prompt = payload.get("prompt", {})
            for name, value in prompt.items():
                field = getattr(self.prompt_panel, name, None)
                if isinstance(field, QPlainTextEdit):
                    field.setPlainText(str(value))
            self.prompt_panel.auto_sync.setChecked(bool(payload.get("prompt_auto_sync", True)))
            special = _canonical_special_skill_key(
                payload.get("special_skill", NONE_SPECIAL)
            )
            index = self.special_combo.findData(special)
            self.special_combo.setCurrentIndex(max(0, index))
            self.production_strategy = str(
                payload.get("production_strategy")
                or (
                    "incremental"
                    if str(special) == "long-form-h3-director"
                    else "full_range"
                )
            )
            if self.production_strategy not in {"full_range", "incremental"}:
                self.production_strategy = "full_range"
            self.production_batch_seconds = max(
                16.0, float(payload.get("production_batch_seconds", 30.0))
            )
            incremental = payload.get("incremental_production") or {}
            duration_limit = self._timeline_duration_seconds()
            self.incremental_approved_horizon = min(
                duration_limit,
                max(0.0, float(incremental.get("approved_horizon_seconds", 0.0))),
            )
            self.incremental_pending_start = min(
                duration_limit,
                max(0.0, float(incremental.get("pending_start_seconds", 0.0))),
            )
            self.incremental_pending_end = min(
                duration_limit,
                max(
                    self.incremental_pending_start,
                    float(incremental.get("pending_end_seconds", 0.0)),
                ),
            )
            self.incremental_batch_phase = str(incremental.get("phase") or "")
            raw_preview_seed = incremental.get("preview_seed")
            self.preview_seed = (
                int(raw_preview_seed) if raw_preview_seed is not None else None
            )
            self.preview_ready = bool(incremental.get("preview_ready", False))
            strategy_index = self.production_strategy_combo.findData(
                self.production_strategy
            )
            self.production_strategy_combo.blockSignals(True)
            self.production_strategy_combo.setCurrentIndex(max(0, strategy_index))
            self.production_strategy_combo.blockSignals(False)
            self.production_batch_spin.blockSignals(True)
            self.production_batch_spin.setValue(self.production_batch_seconds)
            self.production_batch_spin.blockSignals(False)
            saved_settings = payload.get("render_settings") or {}
            if saved_settings:
                self.render_settings = RenderSettings.from_mapping(saved_settings)
            self.render_settings.server_url = str(
                payload.get("server_url", self.render_settings.server_url)
            )
            self.server_url.setText(self.render_settings.server_url)
            ratio_index = self.aspect_ratio_combo.findData(self.render_settings.aspect_ratio)
            self.aspect_ratio_combo.setCurrentIndex(max(0, ratio_index))
            self._sync_settings_ui()
            work_area = payload.get("work_area", [0.0, self.scan.duration_seconds])  # type: ignore[union-attr]
            self.clip_start.setValue(float(work_area[0]))
            self.clip_end.setValue(float(work_area[1]))
            self.playhead_seconds = min(
                self.scan.duration_seconds,  # type: ignore[union-attr]
                max(0.0, float(payload.get("playhead_seconds", 0.0))),
            )
            self.timeline.rebuild()
            self.timeline.set_playhead(self.playhead_seconds)
            self.render_timeline_at(self.playhead_seconds, force_seek=True)
            self.refresh_activation()
            self.smart_render_manifest = dict(payload.get("smart_render") or {})
            self.smart_render_manifests = {
                str(key): dict(value)
                for key, value in (payload.get("smart_render_manifests") or {}).items()
                if isinstance(value, dict)
            }
            recovered_manifest = self._recover_workspace_render_manifest(
                workspace_root
            )
            if recovered_manifest:
                recovered_kind = str(
                    recovered_manifest.get("request_kind") or "final"
                ).lower()
                recovered_key = (
                    "preview" if recovered_kind == "preview" else "production"
                )
                existing_manifest = self.smart_render_manifests.get(recovered_key)
                if not existing_manifest or self._render_manifest_recovery_score(
                    recovered_manifest
                ) > self._render_manifest_recovery_score(existing_manifest):
                    self.smart_render_manifests[recovered_key] = recovered_manifest
                    self.smart_render_manifest = recovered_manifest
                    recovered_workspace_state = True
            if self.smart_render_manifest and not self.smart_render_manifests:
                legacy_kind = str(self.smart_render_manifest.get("request_kind", "final"))
                cache_key = "preview" if legacy_kind == "preview" else "production"
                self.smart_render_manifests[cache_key] = self.smart_render_manifest
            preferred_manifest_key = (
                "preview"
                if str(payload.get("generated_output_request_kind", "final"))
                == "preview"
                else "production"
            )
            if preferred_manifest_key in self.smart_render_manifests:
                self.smart_render_manifest = self.smart_render_manifests[
                    preferred_manifest_key
                ]
            self.render_dirty_segment_ids = {
                str(value) for value in payload.get("render_dirty_segment_ids", [])
            }
            self.render_runtime_status.clear()
            self._refresh_render_status_bar()
            # A copied legacy project adopts its containing folder. Its source
            # JSON remains read-only; new snapshots go to project/director_project.
            self.example_work_dir = workspace_root.resolve()
            self.project_workspace_id = str(manifest.get("workspace_id") or "")
            self.legacy_project_source = (
                opened_project_path if is_legacy_project else None
            )
            self.quality_profile = str(
                payload.get("quality_profile") or "approved_final"
            )
            if self.quality_profile not in QUALITY_PROFILES:
                self.quality_profile = "approved_final"
            quality_index = self.quality_profile_combo.findData(self.quality_profile)
            self.quality_profile_combo.blockSignals(True)
            self.quality_profile_combo.setCurrentIndex(max(0, quality_index))
            self.quality_profile_combo.blockSignals(False)
            self.shot_take_states = normalize_shot_take_states(
                payload.get("shot_take_states"), self._shot_ids()
            )
            self.segment_take_states = normalize_segment_take_states(
                payload.get("segment_take_states")
            )
            self.segment_take_states, rebased_shots = rebase_workspace_take_states(
                workspace_root,
                self.segment_take_states,
                self.shot_take_states,
            )
            self.shot_take_states = normalize_shot_take_states(
                rebased_shots, self._shot_ids()
            )
            if int(payload.get("workspace_layout_version", 0)) < 2:
                shot_ranges = {
                    str(cue.cue_id): (
                        float(cue.start_seconds), float(cue.end_seconds)
                    )
                    for cue in self.director_cues
                    if cue.cue_type == "shot"
                }
                migrated_segments, migrated_shots, migration_report = (
                    migrate_legacy_shot_takes(
                        workspace_root,
                        manifests=self.smart_render_manifests,
                        shot_states=self.shot_take_states,
                        shot_ranges=shot_ranges,
                        segment_states=self.segment_take_states,
                    )
                )
                self.segment_take_states = migrated_segments
                self.shot_take_states = normalize_shot_take_states(
                    migrated_shots, self._shot_ids()
                )
                if int(migration_report.get("migrated_segments", 0)):
                    self.statusBar().showMessage(
                        "Workspace upgraded to compact Segment storage: "
                        f"{migration_report['migrated_segments']} Segment assets, "
                        f"{migration_report['removed_legacy_files']} legacy aliases removed."
                    )
            self._write_shot_state_manifests()
            compare_sizes = payload.get("monitor_compare_sizes") or []
            if len(compare_sizes) == 2 and any(int(value) > 0 for value in compare_sizes):
                self.monitor_compare_splitter.setSizes(
                    [max(1, int(value)) for value in compare_sizes]
                )
            saved_output_text = str(payload.get("generated_output", "")).strip()
            generated_output = Path(saved_output_text)
            self.submit_request_kind = str(
                payload.get("generated_output_request_kind", "final")
            )
            root_workspace_output = (
                workspace_root / (
                    "generated_preview.mp4"
                    if self.submit_request_kind == "preview"
                    else "generated_output.mp4"
                )
            )
            workspace_output = (
                workspace_root / "renders" / "final" / "generated_output.mp4"
            )
            legacy_workspace_output = workspace_root / "generated_output.mp4"
            sibling_output = opened_project_path.parent / "generated_output.mp4"
            manifest_master = Path(
                str(self.smart_render_manifest.get("master_output") or "")
            )
            # Durable Workspace masters are authoritative even when an older
            # or interrupted Project snapshot left generated_output empty.
            # Prefer the requested Preview/Final kind, then use portable and
            # legacy fallbacks without ever requiring a stale JSON path first.
            candidates = [
                root_workspace_output,
                generated_output,
                manifest_master,
                workspace_output,
                legacy_workspace_output,
                sibling_output,
            ]
            if self.submit_request_kind == "preview":
                candidates.append(workspace_root / "generated_output.mp4")
            else:
                candidates.append(workspace_root / "generated_preview.mp4")
            generated_output = next(
                (candidate for candidate in candidates if candidate.is_file()),
                generated_output,
            )
            if generated_output.is_file() and (
                not saved_output_text
                or Path(saved_output_text).resolve() != generated_output.resolve()
            ):
                recovered_workspace_state = True
            if generated_output.is_file():
                self._show_generated_output(
                    [{"kind": "videos", "local_path": str(generated_output)}],
                    timeline_start=float(payload.get("generated_output_timeline_start", 0.0)),
                    autoplay=False,
                )
            self.accept_preview_button.setEnabled(
                self.preview_ready and self.preview_seed is not None
            )
            self.reject_preview_button.setEnabled(
                self.preview_ready and self.preview_seed is not None
            )
            self._refresh_incremental_controls()
            # Restore every visible time control from the same saved playhead.
            # Previously the Timeline scene restored correctly while the slider
            # and labels incorrectly remained at 0.00 seconds.
            self.seek_timeline(self.playhead_seconds)
            self.project_path = (
                workspace_project_path(workspace_root).resolve()
                if is_legacy_project
                else opened_project_path
            )
            # Automatic integrity repairs are deliberately kept in memory
            # until the user saves.  The original JSON remains recoverable,
            # while Save Project persists the clean, rerender-ready form.
            if integrity_repairs:
                # Project integrity may have rippled speech and Shot timing.
                # Rebuild the editable prompt fields from that repaired
                # Timeline so a subsequent Run cannot reuse stale timecodes.
                self._sync_prompt_panel_from_timeline(force=True)
            self.project_dirty = bool(integrity_repairs or recovered_workspace_state)
            self.undo_stack.clear()
            if not integrity_repairs and not recovered_workspace_state:
                self.undo_stack.setClean()
            self._update_window_title()
            migration_note = " 路 legacy source preserved" if is_legacy_project else ""
            repair_note = (
                f" · auto-repaired {len(integrity_repairs)} integrity item(s); save to persist"
                if integrity_repairs else ""
            )
            recovery_note = (
                " · recovered generated output/manifest from Workspace; save to persist"
                if recovered_workspace_state else ""
            )
            self.statusBar().showMessage(
                f"Project restored: {path.name}{migration_note}{repair_note}{recovery_note}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Project load error", str(exc))
        finally:
            self.restoring_project = False

    def load_workflow_path(self, path: Path) -> None:
        try:
            scan = load_workflow(path)
        except Exception as exc:
            QMessageBox.critical(self, "Workflow error", str(exc))
            return
        self.media_jobs.clear()
        self.blip_jobs.clear()
        self.blip_results.clear()
        self.audio_jobs.clear()
        previous_lm_request = next(
            (
                dict(job) for job in reversed(list(self.semantic_jobs.values()))
                if job.get("provider") == "lm_studio"
            ),
            {},
        )
        self.semantic_jobs.clear()
        self.semantic_errors.clear()
        self.semantic_waiting_assets.clear()
        self.semantic_unload_job_id = ""
        self.semantic_last_lm_request = previous_lm_request
        self.media_runner.discard_pending()
        self.blip_runner.discard_pending()
        self.audio_runner.discard_pending()
        self.semantic_runner.discard_pending()
        self.preview_paths.clear()
        self.monitor_source_pixmaps.clear()
        self.analysis_paths.clear()
        self.audio_pan_proxies.clear()
        self.audio_pan_pending.clear()
        self.render_dirty_segment_ids.clear()
        self.render_runtime_status.clear()
        self.tracks = default_timeline_tracks()
        self.text_layers = []
        self.authored_text_requirements = []
        self.director_cues = []
        self.selected_asset = None
        self.selected_timeline_asset = None
        self.selected_track = None
        self.timeline.set_tracks(self.tracks)
        self.timeline.set_text_layers(self.text_layers)
        self.timeline.set_director_cues(self.director_cues)
        self._rebuild_track_headers()
        self.scan = scan
        if not self.restoring_project:
            self.storyboard_target_duration_seconds = scan.duration_seconds
            self.storyboard_trim_active = False
            self.production_strategy = "full_range"
            self.production_batch_seconds = 30.0
            self.incremental_approved_horizon = 0.0
            self.incremental_pending_start = 0.0
            self.incremental_pending_end = 0.0
            self.incremental_batch_phase = ""
            if hasattr(self, "production_strategy_combo"):
                strategy_index = self.production_strategy_combo.findData("full_range")
                self.production_strategy_combo.blockSignals(True)
                self.production_strategy_combo.setCurrentIndex(max(0, strategy_index))
                self.production_strategy_combo.blockSignals(False)
                self.production_batch_spin.blockSignals(True)
                self.production_batch_spin.setValue(self.production_batch_seconds)
                self.production_batch_spin.blockSignals(False)
            if hasattr(self, "storyboard_target_spin"):
                self.storyboard_target_spin.blockSignals(True)
                self.storyboard_target_spin.setValue(scan.duration_seconds)
                self.storyboard_target_spin.blockSignals(False)
            if hasattr(self, "storyboard_trim_button"):
                if hasattr(self, "manual_ripple_action"):
                    self.manual_ripple_action.setChecked(False)
                self._refresh_storyboard_trim_controls()
        mapped_classes = (
            "ResolutionSelector",
            "BasicScheduler",
            "RandomNoise",
            "RTXVideoSuperResolution",
        )
        mapped = [
            f"{node_id} · {node.get('class_type')}"
            for node_id, node in scan.nodes.items()
            if node.get("class_type") in mapped_classes
        ]
        self.settings_node_map.setText("\n".join(mapped) or "No compatible generation nodes found.")
        self.preview_seed = None
        self.preview_ready = False
        self.accept_preview_button.setEnabled(False)
        self.reject_preview_button.setEnabled(False)
        self.cards.clear()
        self.media_card_order.clear()
        while self.media_grid.count():
            item = self.media_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for asset in scan.assets:
            self._append_media_card(asset)
        counts = scan.counts
        self._refresh_virtual_media_header()
        self.clip_start.setRange(0, scan.duration_seconds)
        self.clip_end.setRange(0.01, MAX_MANUAL_TIMELINE_SECONDS)
        self.clip_start.setValue(0)
        self.clip_end.setValue(scan.duration_seconds)
        self.asset_start.setRange(0, scan.duration_seconds)
        self.asset_end.setRange(0, scan.duration_seconds)
        self.timeline.set_workflow(scan)
        self.playhead_seconds = 0.0
        self.position_slider.setRange(0, max(1, round(scan.duration_seconds * 1000)))
        self._stop_all_timeline_media()
        self.render_timeline_at(0.0, force_seek=True)
        self.workflow_info.setPlainText(
            f"API: {scan.path}\nH3 node(s): {', '.join(scan.h3_node_ids)}\n"
            f"Duration: {scan.duration_seconds:.2f}s\n"
            f"LoadImage: {counts['image']} / 9\nLoadVideo + GetVideoComponents: {counts['video']} / 3\n"
            f"LoadAudio: {counts['audio']} / 3\n\n" + "\n".join(scan.warnings)
        )
        self.statusBar().showMessage(
            f"Loaded {path.name}: virtual pool ready; per-Segment H3 capacity "
            f"{counts['image']} image / {counts['video']} video / {counts['audio']} audio"
        )
        QTimer.singleShot(0, self._reflow_media_pool)
        self.undo_stack.clear()
        self.project_path = None
        self.project_dirty = False
        self._update_window_title()
        self.refresh_activation()
        self._sync_prompt_panel_from_timeline()
        self._refresh_render_status_bar()
        self._refresh_recognition_inspector()
        self._maybe_request_semantic_lm_unload()
        self._refresh_incremental_controls()

    def load_asset_file(self, asset: MediaAsset, filename: str) -> None:
        if media_type_for_path(filename) != asset.media_type:
            QMessageBox.warning(self, "Wrong media type", f"{asset.tag} expects {asset.media_type} media.")
            return
        try:
            source_path = Path(filename).expanduser().resolve()
            workspace = self._ensure_project_workspace()
            try:
                source_path.relative_to(workspace)
                imported_path = source_path
            except ValueError:
                stat = source_path.stat()
                signature = hashlib.sha256(
                    f"{source_path}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
                ).hexdigest()[:12]
                logical_id = slugify_project_name(
                    stable_reference_id(asset), "media"
                )
                safe_name = slugify_project_name(source_path.stem, "source")
                imported_path = (
                    workspace
                    / "media"
                    / "imported"
                    / f"{logical_id}_{signature}_{safe_name}{source_path.suffix.lower()}"
                )
                if not imported_path.is_file():
                    link_or_copy(source_path, imported_path)
            incoming_path = str(imported_path.resolve())
            replacing_timeline_media = bool(
                any(
                    item.timeline_placed
                    for item in self._timeline_assets()
                    if self._source_asset_for(item) is asset
                )
                and asset.local_path
                and asset.local_path != incoming_path
            )
            assign_local_media(self.scan, asset, imported_path)  # type: ignore[arg-type]
            self._show_immediate_image_preview(asset)
            self.semantic_errors.pop(asset.node_id, None)
            self.semantic_waiting_assets.discard(asset.node_id)
            if replacing_timeline_media:
                # A prompt authored for the previous file must never be applied
                # to its replacement. Force the complete visual-analysis → LM
                # Shot-adaptation chain even when AUTO AI ENRICH is disabled.
                asset.clip_prompt = ""
                for clip in self.scan.timeline_clips:  # type: ignore[union-attr]
                    if clip.source_node_id == asset.node_id:
                        clip.clip_prompt = ""
                self.semantic_waiting_assets.add(asset.node_id)
            self._sync_timeline_clip_sources(asset)
            self.select_asset(asset)
            self.queue_media_preparation(asset, auto_analyze=True, preserve_recognition=False)
            for clip in self._timeline_assets():
                if self._source_asset_for(clip) is asset and clip.timeline_placed:
                    self._mark_render_range_dirty(clip.start_seconds, clip.end_seconds)
            self._mark_dirty()
            self.schedule_prompt_generation()
            if replacing_timeline_media:
                self.statusBar().showMessage(
                    f"Replacing {asset.tag} · analysing new media and adapting existing Shots"
                )
        except Exception as exc:
            QMessageBox.critical(self, "Media load error", str(exc))

    @staticmethod
    def _z_image_sidecar_for_asset(asset: MediaAsset) -> Path | None:
        source = Path(str(asset.local_path or ""))
        if not source.is_file():
            return None
        candidates = [source.with_suffix(source.suffix + ".request.json")]
        if source.stem.endswith("_nobg"):
            original = source.with_name(source.stem[:-5] + source.suffix)
            candidates.append(original.with_suffix(original.suffix + ".request.json"))
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    def _z_image_regeneration_request(self, asset: MediaAsset) -> dict:
        """Rebuild one Z-Image request without changing its stable P mapping."""
        if asset.media_type != "image":
            raise ValueError("Z-Image regeneration is available only for Picture media.")
        metadata: dict = {}
        sidecar = self._z_image_sidecar_for_asset(asset)
        if sidecar is not None:
            try:
                loaded = json.loads(sidecar.read_text(encoding="utf-8-sig"))
                if isinstance(loaded, dict):
                    metadata = loaded
            except (OSError, ValueError):
                metadata = {}
        prompt = str(metadata.get("prompt") or asset.clip_prompt or "").strip()
        if not prompt:
            match = re.search(
                r"(?:^|\n)Requirement:\s*(.*?)(?=\n(?:BLIP|Overview|Inference)|\Z)",
                str(asset.recognition or ""),
                flags=re.I | re.S,
            )
            prompt = match.group(1).strip() if match else ""
        if not prompt:
            raise ValueError(
                f"{media_shortcut(asset)} has no reusable Z-Image prompt. "
                "Add a Clip Prompt or reload its Design-generated request metadata first."
            )
        stable_id = media_shortcut(asset)
        contract = (
            f"REGENERATION CONTRACT FOR {stable_id}: preserve the same story role, exact subject "
            "count, character and prop ownership, identity relationship, environment, composition, "
            "time of day and continuity state stated above. Correct only visual defects. Never add, "
            "merge, replace or duplicate a person beyond the stated subject-count contract."
        )
        if f"REGENERATION CONTRACT FOR {stable_id}:" not in prompt:
            prompt = prompt.rstrip(" .") + ". " + contract
        request = {
            "requirement_id": str(
                metadata.get("requirement_id") or f"regenerate_{stable_id.lower()}"
            ),
            "media_type": "image",
            "usage": str(metadata.get("usage") or "h3_reference"),
            "reuse_policy": str(metadata.get("reuse_policy") or "time_scoped"),
            "start_seconds": float(
                asset.start_seconds
                if asset.timeline_placed
                else metadata.get("start_seconds", asset.start_seconds)
            ),
            "end_seconds": float(
                asset.end_seconds
                if asset.timeline_placed
                else metadata.get("end_seconds", asset.end_seconds)
            ),
            "track": str(
                asset.timeline_track_id
                if asset.timeline_placed and asset.timeline_track_id
                else metadata.get("track") or "V1"
            ),
            "subject_keywords": list(metadata.get("subject_keywords") or []),
            "prompt": prompt,
            "negative_prompt": str(metadata.get("negative_prompt") or ""),
            "identity_anchor_requirement_id": str(
                metadata.get("identity_anchor_requirement_id") or ""
            ),
            "preferred_media_id": stable_id,
            "regeneration_source": {
                "node_id": asset.node_id,
                "reference_id": stable_id,
                "previous_local_path": str(asset.local_path or ""),
                "previous_sidecar": str(sidecar or ""),
            },
        }
        special_key = str(self.special_combo.currentData() or "")
        if is_drone_special_skill(special_key):
            request = sanitize_drone_still_image_request(
                request,
                fireworks=special_key == "drone-fly-on-city-fireworks",
            )
        return request

    def regenerate_media_asset_with_z_image(self, asset: MediaAsset) -> None:
        """Generate a corrected take and replace the same logical Picture source."""
        if not self.scan or asset not in self.scan.assets:
            return
        if asset.media_type != "image":
            self.statusBar().showMessage("Z-Image regeneration supports Picture media only")
            return
        runners = (
            self.submit_runner,
            self.design_media_runner,
            self.design_tts_runner,
            self.media_regeneration_runner,
        )
        if any(runner and runner.is_running() for runner in runners):
            QMessageBox.information(
                self,
                "Generation is busy",
                "Wait for the current video, TTS or reference-image task to finish, then retry.",
            )
            return
        try:
            settings = load_design_settings(DESIGN_SETTINGS_ENV)
            if not settings.image_checkpoint:
                raise RuntimeError(
                    "No Z-Image checkpoint is selected. Choose one in Design settings first."
                )
            request = self._z_image_regeneration_request(asset)
            workspace = self._ensure_project_workspace()
            output_dir = (
                workspace
                / "media"
                / "regenerated_references"
                / media_shortcut(asset)
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            source_stem = slugify_project_name(
                Path(str(asset.filename or "reference")).stem,
                "reference",
            )
            destination = output_dir / (
                f"{media_shortcut(asset)}_{stamp}_{source_stem}.png"
            )
            request["local_path"] = str(destination.resolve())
            request["request_index"] = 0
            destination.with_suffix(destination.suffix + ".request.json").write_text(
                json.dumps(request, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            job_path = CACHE_ROOT / f"z_image_regenerate_{asset.node_id}_{time.time_ns()}.json"
            job_path.parent.mkdir(parents=True, exist_ok=True)
            job_path.write_text(
                json.dumps(
                    {
                        "server": self.server_url.text().strip(),
                        "workflow_path": str(Z_IMAGE_WORKFLOW),
                        "materials": [request],
                        "settings": {
                            "checkpoint": settings.image_checkpoint,
                            "width": settings.image_width,
                            "height": settings.image_height,
                            "steps": settings.image_steps,
                            "cfg": settings.image_cfg,
                            "negative_prompt": settings.image_negative_prompt,
                        },
                        "attempts_per_image": 2,
                        "poll_interval": self.render_settings.history_poll_interval,
                        "generation_timeout": self.render_settings.generation_timeout,
                        "http_timeout": self.render_settings.http_request_timeout,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            runner = JsonLineProcess(self, f"z-image-regenerate-{asset.node_id}")
            runner.message.connect(self._media_regeneration_message)
            runner.finished.connect(self._media_regeneration_finished)
            self.media_regeneration_runner = runner
            self.media_regeneration_result = {}
            self.pending_media_regeneration = {
                "asset": asset,
                "request": request,
                "previous_local_path": str(asset.local_path or ""),
            }
            card = self.cards.get(asset.node_id)
            if card:
                card.set_processing(True, "Z-IMAGE")
            self.statusBar().showMessage(
                f"{media_shortcut(asset)} · regenerating with preserved mapping and relationships"
            )
            if not runner.start(
                str(self.runtime.python),
                [str(PROJECT_ROOT / "design_media_service.py"), str(job_path)],
            ):
                raise RuntimeError("Z-Image regeneration worker is still stopping")
        except Exception as exc:
            card = self.cards.get(asset.node_id)
            if card:
                card.set_processing(False)
            if self.media_regeneration_runner:
                self.media_regeneration_runner.deleteLater()
            self.media_regeneration_runner = None
            self.pending_media_regeneration = None
            QMessageBox.warning(self, "Z-Image regeneration", str(exc))

    def _media_regeneration_message(self, payload: dict) -> None:
        if payload.get("progress"):
            message = str(payload["progress"])
            self.statusBar().showMessage(message)
            pending = self.pending_media_regeneration or {}
            asset = pending.get("asset")
            card = self.cards.get(asset.node_id) if asset else None
            if card:
                card.set_processing(True, "Z-IMAGE")
        if payload.get("completed") or payload.get("error"):
            self.media_regeneration_result = dict(payload)

    def _media_regeneration_finished(self, exit_code: int, log: str) -> None:
        pending = self.pending_media_regeneration or {}
        asset: MediaAsset | None = pending.get("asset")
        result = self.media_regeneration_result
        try:
            if asset is None:
                return
            card = self.cards.get(asset.node_id)
            if card:
                card.set_processing(False)
            outputs = [
                item for item in (result.get("outputs") or [])
                if isinstance(item, dict) and item.get("generated")
            ]
            generated = Path(str(outputs[0].get("local_path", ""))) if outputs else None
            if exit_code or result.get("error") or generated is None or not generated.is_file():
                detail = str(result.get("error") or "").strip()
                if not detail:
                    warnings = result.get("warnings") or []
                    detail = str(warnings[-1]) if warnings else log[-500:]
                raise RuntimeError(detail or f"worker exit {exit_code}")
            preserved_prompt = asset.clip_prompt
            preserved_recognition = asset.recognition
            assign_local_media(self.scan, asset, generated)
            self._show_immediate_image_preview(asset)
            asset.clip_prompt = preserved_prompt
            asset.recognition = (
                remove_previous_blip_output(preserved_recognition).rstrip()
                + "\n\nZ-IMAGE REGENERATION: new visual take; original relationship and mapping contract preserved."
            ).strip()
            self.semantic_errors.pop(asset.node_id, None)
            self.semantic_waiting_assets.discard(asset.node_id)
            self._sync_timeline_clip_sources(asset)
            if card:
                card.set_preview(QPixmap(str(generated)))
            self.select_asset(asset)
            self.queue_media_preparation(
                asset,
                auto_analyze=True,
                preserve_recognition=True,
            )
            for clip in self._timeline_assets():
                if self._source_asset_for(clip) is asset and clip.timeline_placed:
                    self._mark_render_range_dirty(clip.start_seconds, clip.end_seconds)
            self._mark_dirty()
            self.schedule_prompt_generation()
            self.timeline.schedule_rebuild()
            self.render_timeline_at(self.playhead_seconds, force_seek=True)
            self.statusBar().showMessage(
                f"{media_shortcut(asset)} regenerated and replaced in place · Timeline mapping unchanged"
            )
        except Exception as exc:
            if asset is not None:
                card = self.cards.get(asset.node_id)
                if card:
                    card.set_processing(False)
            QMessageBox.warning(self, "Z-Image regeneration failed", str(exc))
        finally:
            self.pending_media_regeneration = None
            self.media_regeneration_result = {}
            if self.media_regeneration_runner:
                self.media_regeneration_runner.deleteLater()
            self.media_regeneration_runner = None

    def queue_media_preparation(
        self,
        asset: MediaAsset,
        *,
        auto_analyze: bool,
        preserve_recognition: bool,
    ) -> None:
        """Queue all FFprobe/FFmpeg work outside the Qt UI process."""
        if not asset.local_path or not self.scan:
            return
        for job_id, job in list(self.media_jobs.items()):
            if job["asset"] is asset:
                self.media_jobs.pop(job_id, None)
        job_id = f"prepare:{asset.node_id}:{time.time_ns()}"
        self.media_jobs[job_id] = {
            "asset": asset,
            "path": asset.local_path,
            "auto_analyze": auto_analyze,
            "preserve_recognition": preserve_recognition,
        }
        if not preserve_recognition:
            asset.recognition = "MEDIA PREPARATION\nQueued for FFprobe and preview generation."
        card = self.cards.get(asset.node_id)
        if card:
            card.set_analysis_status("准备 …")
        self._refresh_semantic_card(asset)
        if asset is self.selected_asset:
            self._refresh_recognition_inspector(asset)
        try:
            if not self.media_runner.is_running():
                if not self.media_runner.start(
                    str(self.runtime.python),
                    [
                        str(PROJECT_ROOT / "media_prepare_service.py"),
                        "--ffmpeg",
                        str(self.runtime.ffmpeg),
                    ],
                ):
                    raise RuntimeError("Media preparation service is still stopping")
            self.media_runner.write_json(
                {
                    "job": job_id,
                    "node_id": asset.node_id,
                    "media_type": asset.media_type,
                    "media": asset.local_path,
                    "timeline_seconds": self.scan.duration_seconds,
                    "cache_root": str(CACHE_ROOT),
                }
            )
            self.statusBar().showMessage(
                f"Preparing {asset.tag} in background — the interface remains available"
            )
        except Exception as exc:
            self.media_jobs.pop(job_id, None)
            self._mark_analysis_failure(asset, f"Media preparation could not start: {exc}")

    def _handle_media_prepare_payload(self, payload: dict) -> None:
        if payload.get("ready"):
            self.statusBar().showMessage("Background media preparation service ready")
            return
        job = self.media_jobs.get(payload.get("job", ""))
        if not job:
            return
        asset: MediaAsset = job["asset"]
        if job["path"] != asset.local_path:
            self.media_jobs.pop(payload.get("job", ""), None)
            return
        if job.get("operation") == "audio-pan":
            if "progress" in payload and "result" not in payload:
                self.statusBar().showMessage(
                    f"Rendering pan proxy for {asset.tag} · {round(float(payload['progress']) * 100)}%"
                )
                return
            self.media_jobs.pop(payload.get("job", ""), None)
            self.audio_pan_pending.discard(job["proxy_key"])
            if payload.get("error"):
                self.statusBar().showMessage(f"Pan proxy failed for {asset.tag}: {payload['error']}")
                return
            proxy = Path((payload.get("result") or {}).get("pan_proxy_path", ""))
            if proxy.is_file():
                self.audio_pan_proxies[job["proxy_key"]] = proxy
                self.render_timeline_at(self.playhead_seconds, force_seek=True)
            return
        if "progress" in payload and "result" not in payload:
            percent = max(0, min(99, round(float(payload["progress"]) * 100)))
            card = self.cards.get(asset.node_id)
            if card:
                card.set_analysis_status(f"准备 {percent}%")
            self.statusBar().showMessage(
                f"{asset.tag} · {payload.get('stage', 'preparing')} · {percent}%"
            )
            return
        self.media_jobs.pop(payload.get("job", ""), None)
        if payload.get("error"):
            self._mark_analysis_failure(asset, f"Media preparation error: {payload['error']}")
            return
        result = payload.get("result") or {}
        info = result.get("info") or {}
        background_removal = result.get("background_removal") or {}
        transparent_path = Path(str(background_removal.get("path", "")))
        if transparent_path.is_file() and self.scan:
            assign_local_media(self.scan, asset, transparent_path)
            self._show_immediate_image_preview(asset)
        if not job["preserve_recognition"] or not asset.recognition.strip():
            asset.recognition = result.get("metadata", "")
        if transparent_path.is_file():
            summary = (
                "AUTO BACKGROUND REMOVAL: uniform edge-connected background removed "
                f"({round(float(background_removal.get('removed_ratio', 0.0)) * 100)}% transparent)."
            )
            if summary not in asset.recognition:
                asset.recognition = (asset.recognition.rstrip() + "\n" + summary).strip()
        preview_path = Path(result.get("preview_path", ""))
        if preview_path.is_file():
            self.preview_paths[asset.node_id] = preview_path
            self.cards[asset.node_id].set_preview(QPixmap(str(preview_path)))
        self.analysis_paths[asset.node_id] = [
            (str(label), Path(path))
            for label, path in result.get("analysis_sources", [])
            if Path(path).is_file()
        ]
        if info.get("duration", 0) and asset.media_type in ("video", "audio"):
            asset.source_duration_seconds = float(info["duration"])
            if asset.timeline_placed and self.scan:
                asset.end_seconds = min(
                    self.scan.duration_seconds,
                    asset.start_seconds + float(info["duration"]),
                )
        self._sync_timeline_clip_sources(asset)
        self.timeline.schedule_rebuild()
        self._refresh_semantic_card(asset)
        if asset is self.selected_asset:
            self._show_asset_inspector(
                asset, self.selected_timeline_asset or asset
            )
        self.statusBar().showMessage(f"Prepared {asset.tag}; recognition queued")
        if job["auto_analyze"]:
            if asset.media_type in ("image", "video"):
                self.start_blip(asset)
            if asset.media_type in ("video", "audio"):
                self.start_audio_analysis(asset)
            self._maybe_auto_enrich(asset)
        else:
            if asset.node_id in self.semantic_waiting_assets:
                if asset.media_type in ("image", "video"):
                    self.start_blip(asset)
                else:
                    self._maybe_auto_enrich(asset)
            self._refresh_recognition_inspector(asset if asset is self.selected_asset else None)

    def _audio_pan_key(self, asset: MediaAsset, track: TimelineTrack) -> str:
        return f"{asset.node_id}:{track.track_id}:{track.pan:.4f}"

    def queue_audio_pan_proxy(self, asset: MediaAsset, track: TimelineTrack) -> None:
        if not self.scan or not asset.local_path or abs(track.pan) < 0.001:
            return
        proxy_key = self._audio_pan_key(asset, track)
        if proxy_key in self.audio_pan_proxies or proxy_key in self.audio_pan_pending:
            return
        self.audio_pan_pending.add(proxy_key)
        digest = hashlib.sha1(
            (asset.local_path + proxy_key + str(self.scan.duration_seconds)).encode()
        ).hexdigest()[:16]
        destination = CACHE_ROOT / f"pan_{asset.node_id}_{digest}.wav"
        if destination.is_file():
            self.audio_pan_proxies[proxy_key] = destination
            self.audio_pan_pending.discard(proxy_key)
            return
        job_id = f"audio-pan:{asset.node_id}:{time.time_ns()}"
        self.media_jobs[job_id] = {
            "asset": asset,
            "path": asset.local_path,
            "operation": "audio-pan",
            "proxy_key": proxy_key,
        }
        try:
            if not self.media_runner.is_running():
                if not self.media_runner.start(
                    str(self.runtime.python),
                    [str(PROJECT_ROOT / "media_prepare_service.py"), "--ffmpeg", str(self.runtime.ffmpeg)],
                ):
                    raise RuntimeError("Media preparation service is still stopping")
            self.media_runner.write_json(
                {
                    "job": job_id,
                    "operation": "audio-pan",
                    "media": asset.local_path,
                    "pan": track.pan,
                    "timeline_seconds": self.scan.duration_seconds,
                    "destination": str(destination),
                }
            )
        except Exception as exc:
            self.media_jobs.pop(job_id, None)
            self.audio_pan_pending.discard(proxy_key)
            self.statusBar().showMessage(f"Pan proxy could not start: {exc}")

    def _media_prepare_service_finished(self, exit_code: int, log: str) -> None:
        self.media_runner.discard_pending()
        if self._closing:
            self.media_jobs.clear()
            return
        affected_assets: list[MediaAsset] = []
        for job in self.media_jobs.values():
            detail = log[-300:] if log else f"exit {exit_code}"
            if job.get("operation") == "audio-pan":
                self.audio_pan_pending.discard(job["proxy_key"])
                self.statusBar().showMessage(f"Pan proxy service stopped: {detail}")
            else:
                affected_assets.append(job["asset"])
                self._mark_analysis_failure(job["asset"], f"Media preparation service stopped: {detail}")
        self.media_jobs.clear()
        for asset in affected_assets:
            self._maybe_auto_enrich(asset)
        self._maybe_request_semantic_lm_unload()

    def _asset_has_base_analysis_jobs(self, asset: MediaAsset) -> bool:
        preparing = any(
            job.get("asset") is asset and job.get("operation") != "audio-pan"
            for job in self.media_jobs.values()
            if isinstance(job, dict)
        )
        blip = any(job[0] is asset for job in self.blip_jobs.values())
        audio = any(job_asset is asset for job_asset in self.audio_jobs.values())
        return preparing or blip or audio

    def _asset_has_semantic_job(self, asset: MediaAsset) -> bool:
        return any(job.get("asset") is asset for job in self.semantic_jobs.values())

    @staticmethod
    def _asset_has_semantic_evidence(asset: MediaAsset) -> bool:
        raw = str(asset.recognition or "").strip()
        if not raw or raw == "Not analyzed yet.":
            return False
        if raw.startswith("MEDIA PREPARATION") and "Queued for FFprobe" in raw and len(raw.splitlines()) <= 3:
            return False
        return bool(
            re.search(
                r"(?:^|\n)(?:Type|Format|Frame|Duration|Video|Audio|BLIP|WHISPER|BEAT|VAD)\b",
                raw,
                flags=re.I,
            )
        )

    @staticmethod
    def _semantic_source_fingerprint(asset: MediaAsset) -> str:
        return enrichment_fingerprint(
            media_id=media_shortcut(asset),
            media_type=asset.media_type,
            filename=Path(asset.local_path or asset.filename).name,
            recognition=asset.recognition,
            clip_prompt=asset.clip_prompt,
            duration_seconds=asset.source_duration_seconds,
            timeline_start_seconds=asset.start_seconds if asset.timeline_placed else 0.0,
            timeline_end_seconds=asset.end_seconds if asset.timeline_placed else 0.0,
        )

    def _semantic_job_context(self, asset: MediaAsset) -> dict:
        existing_shots = []
        if asset.timeline_placed:
            existing_shots = [
                asdict(cue)
                for cue in self.director_cues
                if cue.cue_type == "shot"
                and ranges_intersect(
                    cue.start_seconds,
                    cue.end_seconds,
                    asset.start_seconds,
                    asset.end_seconds,
                )
            ]
        return build_enrichment_job_context(
            media_id=media_shortcut(asset),
            media_type=asset.media_type,
            filename=Path(asset.local_path or asset.filename).name,
            recognition=asset.recognition,
            duration_seconds=asset.source_duration_seconds,
            timeline_start_seconds=asset.start_seconds if asset.timeline_placed else 0.0,
            timeline_end_seconds=asset.end_seconds if asset.timeline_placed else 0.0,
            clip_prompt=asset.clip_prompt,
            existing_shots=existing_shots,
        )

    def _semantic_asset_status_key(self, asset: MediaAsset) -> str:
        if self._asset_has_semantic_job(asset):
            return "running"
        if (
            self._asset_has_base_analysis_jobs(asset)
            or asset.node_id in self.semantic_waiting_assets
        ):
            return "waiting"
        if asset.semantic_enrichment:
            if (
                asset.semantic_enrichment_source_hash
                and asset.semantic_enrichment_source_hash == self._semantic_source_fingerprint(asset)
            ):
                return "ready"
            return "stale"
        if asset.node_id in self.semantic_errors:
            return "failed"
        return "not_generated"

    def _refresh_semantic_card(self, asset: MediaAsset) -> None:
        card = self.cards.get(asset.node_id)
        if not card:
            return
        base_running = self._asset_has_base_analysis_jobs(asset)
        semantic_running = self._asset_has_semantic_job(asset)
        semantic_waiting = asset.node_id in self.semantic_waiting_assets
        card.set_processing(
            base_running or semantic_running or semantic_waiting,
            "AI ENRICH" if semantic_running or semantic_waiting else "ANALYZING",
        )
        if base_running:
            return
        status = self._semantic_asset_status_key(asset)
        badge = {
            "running": "AI …",
            "waiting": "AI WAIT",
            "ready": "AI ✓",
            "stale": "AI STALE",
            "failed": "AI !",
            "not_generated": "识别 ✓" if self._asset_has_semantic_evidence(asset) else "识别 --",
        }.get(status, "识别 …")
        card.set_analysis_status(badge)

    def _refresh_recognition_inspector(self, asset: MediaAsset | None = None) -> None:
        if not hasattr(self, "semantic_enrich_button"):
            return
        if asset is not None and asset is not self.selected_asset:
            self._refresh_semantic_card(asset)
            return
        asset = self.selected_asset
        if asset is None:
            self.recognition_text.clear()
            self.semantic_text.clear()
            self.semantic_status_label.setText("AI semantic enrichment: no media selected")
            self.semantic_enrich_button.setEnabled(False)
            self.run_recognition.setEnabled(False)
            self.cancel_recognition_button.setEnabled(False)
            return

        self.recognition_text.setPlainText(asset.recognition or "Not analyzed yet.")
        self.semantic_text.setPlainText(asset.semantic_enrichment or "")
        status = self._semantic_asset_status_key(asset)
        settings = load_design_settings(DESIGN_SETTINGS_ENV)
        provider_name = "LM Studio" if settings.provider == "lm_studio" else "Online GPT"
        model = settings.lm_studio_model if settings.provider == "lm_studio" else settings.openai_model
        detail = {
            "running": f"AI enriching in background via {provider_name} · {model}",
            "waiting": "Waiting for FFprobe / BLIP / audio analysis to finish",
            "ready": (
                f"Ready · {asset.semantic_enrichment_model or model}"
                + (f" · {asset.semantic_enrichment_updated_at}" if asset.semantic_enrichment_updated_at else "")
            ),
            "stale": "Stale · raw recognition, clip prompt, or source media changed; rerun enrichment",
            "failed": f"Failed · {self.semantic_errors.get(asset.node_id, 'semantic service error')}",
            "not_generated": f"Not generated · optional · uses {provider_name} / {model}",
        }[status]
        if asset.node_id in self.semantic_waiting_assets and status == "waiting":
            detail += " · manual request queued"
        self.semantic_status_label.setText("AI semantic enrichment: " + detail)
        self.recognition_tabs.setTabText(0, "RAW ANALYSIS")
        semantic_tab = {
            "running": "AI SEMANTIC …",
            "ready": "AI SEMANTIC ✓",
            "stale": "AI SEMANTIC · STALE",
            "failed": "AI SEMANTIC !",
        }.get(status, "AI SEMANTIC")
        self.recognition_tabs.setTabText(1, semantic_tab)
        loaded = bool(asset.local_path and Path(asset.local_path).is_file())
        self.run_recognition.setEnabled(loaded)
        self.semantic_enrich_button.setEnabled(loaded and not self._asset_has_semantic_job(asset))
        has_any_job = (
            self._asset_has_base_analysis_jobs(asset)
            or self._asset_has_semantic_job(asset)
            or asset.node_id in self.semantic_waiting_assets
        )
        self.cancel_recognition_button.setEnabled(has_any_job)
        self._refresh_semantic_card(asset)

    def _semantic_auto_changed(self, enabled: bool) -> None:
        settings = load_design_settings(DESIGN_SETTINGS_ENV)
        settings.auto_semantic_enrichment = bool(enabled)
        save_design_settings(DESIGN_SETTINGS_ENV, settings)
        self.design_ai_settings = settings
        if enabled and self.scan:
            for asset in self.scan.assets:
                self._maybe_auto_enrich(asset)
        self._refresh_recognition_inspector()

    def enrich_selected_media(self) -> None:
        asset = self.selected_asset
        if not asset:
            return
        image_sources = self.analysis_paths.get(asset.node_id, [])
        needs_regions = (
            asset.media_type == "image"
            and len(image_sources) > 1
            and "BLIP visual region" not in asset.recognition
        )
        if needs_regions and not self._asset_has_base_analysis_jobs(asset):
            self.semantic_waiting_assets.add(asset.node_id)
            self.start_blip(asset)
            self.statusBar().showMessage(
                f"{asset.tag} · collecting multi-region visual evidence before AI ENRICH"
            )
            self._refresh_recognition_inspector(asset)
            return
        self.start_semantic_enrichment(asset, force=True, interactive=True)

    def start_semantic_enrichment(
        self,
        asset: MediaAsset,
        *,
        force: bool = False,
        interactive: bool = False,
    ) -> bool:
        if not asset.local_path or not Path(asset.local_path).is_file():
            if interactive:
                QMessageBox.information(self, "AI Semantic Enrichment", "Load the selected media first.")
            return False
        if self._asset_has_semantic_job(asset):
            return False
        if self._asset_has_base_analysis_jobs(asset):
            if force:
                self.semantic_waiting_assets.add(asset.node_id)
                self.statusBar().showMessage(
                    f"{asset.tag} semantic enrichment queued after base analysis"
                )
                self._refresh_recognition_inspector(asset)
            return False
        if not self._asset_has_semantic_evidence(asset):
            message = "Run Analyze Selected Media before semantic enrichment."
            self.semantic_waiting_assets.discard(asset.node_id)
            self.semantic_errors[asset.node_id] = message
            self._refresh_recognition_inspector(asset)
            if interactive:
                QMessageBox.information(self, "AI Semantic Enrichment", message)
            return False

        context = self._semantic_job_context(asset)
        fingerprint = str(context.get("evidence_fingerprint", ""))
        if (
            not force
            and asset.semantic_enrichment
            and asset.semantic_enrichment_source_hash == fingerprint
        ):
            return False
        settings = load_design_settings(DESIGN_SETTINGS_ENV)
        provider = settings.provider
        if provider == "lm_studio":
            base_url = settings.lm_studio_base_url
            model = settings.lm_studio_model
            api_key = ""
        else:
            base_url = settings.openai_base_url
            model = settings.openai_model
            hostname = (urlparse(base_url).hostname or "").lower()
            api_key = self.semantic_openai_api_key or (
                os.getenv("OPENAI_API_KEY", "") if hostname == "api.openai.com" else ""
            )
        if not base_url.strip() or not model.strip():
            message = "Configure the provider URL and model on the Design page first."
            self.semantic_waiting_assets.discard(asset.node_id)
            self.semantic_errors[asset.node_id] = message
            self._refresh_recognition_inspector(asset)
            if interactive:
                QMessageBox.warning(self, "AI Semantic Enrichment", message)
            return False
        if provider == "openai" and (urlparse(base_url).hostname or "").lower() == "api.openai.com" and not api_key:
            message = "OPENAI_API_KEY is not available in this process."
            self.semantic_waiting_assets.discard(asset.node_id)
            self.semantic_errors[asset.node_id] = message
            self._refresh_recognition_inspector(asset)
            if interactive:
                QMessageBox.warning(self, "AI Semantic Enrichment", message)
            return False

        system_prompt, user_prompt = build_media_enrichment_prompts(context)
        job_id = f"media-enrich:{asset.node_id}:{time.time_ns()}"
        job = {
            "asset": asset,
            "path": asset.local_path,
            "fingerprint": fingerprint,
            "provider": provider,
            "base_url": base_url,
            "model": model,
            "timeout": settings.timeout,
            "unload_lm": settings.unload_lm_after_semantic_enrichment,
            "existing_shots": list(context.get("existing_shots") or []),
        }
        try:
            if not self.semantic_runner.is_running():
                if not self.semantic_runner.start(
                    str(self.runtime.python), [str(PROJECT_ROOT / "design_ai_service.py")]
                ):
                    raise RuntimeError("semantic service is still stopping")
            self.semantic_jobs[job_id] = job
            self.semantic_errors.pop(asset.node_id, None)
            self.semantic_waiting_assets.discard(asset.node_id)
            self.semantic_runner.write_json({
                "job": job_id,
                "action": "generate",
                "provider": provider,
                "base_url": base_url,
                "model": model,
                "api_key": api_key,
                "timeout": settings.timeout,
                "schema_name": "h3_media_semantic_enrichment",
                "max_output_tokens": 6500,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "schema": MEDIA_SEMANTIC_ENRICHMENT_SCHEMA,
            })
            if provider == "lm_studio":
                self.semantic_last_lm_request = dict(job)
            card = self.cards.get(asset.node_id)
            if card:
                card.set_analysis_status("AI …")
            self._refresh_recognition_inspector(asset)
            self.statusBar().showMessage(
                f"AI semantic enrichment running for {asset.tag} · interface remains responsive"
            )
            return True
        except Exception as exc:
            self.semantic_jobs.pop(job_id, None)
            self.semantic_waiting_assets.discard(asset.node_id)
            self.semantic_errors[asset.node_id] = str(exc)
            self._refresh_recognition_inspector(asset)
            if interactive:
                QMessageBox.warning(self, "AI Semantic Enrichment", str(exc))
            return False

    def _maybe_auto_enrich(self, asset: MediaAsset) -> None:
        if self._closing or self._asset_has_base_analysis_jobs(asset):
            return
        manual_waiting = asset.node_id in self.semantic_waiting_assets
        enabled = bool(
            hasattr(self, "semantic_auto_check") and self.semantic_auto_check.isChecked()
        )
        if not enabled and not manual_waiting:
            self._refresh_semantic_card(asset)
            self._refresh_recognition_inspector(asset if asset is self.selected_asset else None)
            return
        self.start_semantic_enrichment(
            asset,
            force=manual_waiting,
            interactive=False,
        )

    @staticmethod
    def _bounded_semantic_direction_value(value: object, limit: int) -> str:
        text = " ".join(str(value or "").split())
        if len(text) <= limit:
            return text
        return text[: max(1, limit - 1)].rstrip(" ,;:-") + "…"

    def _semantic_shot_reference_direction(
        self,
        asset: MediaAsset,
        semantic: dict,
    ) -> str:
        """Build bounded Shot guidance from accepted, evidence-grounded AI fields."""

        media_id = media_shortcut(asset)
        parts = [
            f"Use the overlapping @{media_id} AI-enriched media as a concrete reference",
        ]
        field_specs = (
            ("Summary", "summary", 320),
            ("Observed", "observed_facts", 380),
            ("Environment", "environment", 260),
            ("Composition/camera", "composition_and_camera", 340),
            ("Lighting/color", "lighting_and_color", 260),
            ("Motion/temporal", "motion_and_temporal_changes", 260),
            ("Audio/speech", "audio_and_speech", 260),
            ("H3 usage", "suggested_h3_usage", 320),
            ("Keywords", "h3_prompt_keywords", 220),
        )
        for label, field_name, limit in field_specs:
            value = semantic.get(field_name)
            if isinstance(value, list):
                value = "; ".join(str(item) for item in value[:10] if str(item).strip())
            text = self._bounded_semantic_direction_value(value, limit)
            if text:
                parts.append(f"{label}: {text}")
        parts.append(
            "Preserve this supplied reference evidence instead of replacing it with a newly invented substitute"
        )
        if asset.media_type == "image":
            parts.append(
                "Reconstruct its people, objects and environment inside the moving video scene; "
                "do not show the source as a flat photo, poster, slideshow card, framed insert or pasted overlay"
            )
        return ". ".join(parts)[:2300].rstrip(" .") + "."

    def _sync_semantic_enrichment_to_existing_shots(
        self,
        asset: MediaAsset,
        semantic: dict,
    ) -> list[str]:
        """Update only authored Shots that overlap an enriched Timeline asset.

        AI ENRICH must never create a Shot. Its evidence is held separately,
        while model-provided adaptations rewrite only existing overlapping
        Shots so replacement media becomes part of the moving scene. The whole
        automatic update remains undoable.
        """

        occurrences = [
            item for item in self._timeline_assets()
            if item.timeline_placed and self._source_asset_for(item) is asset
        ]
        if not occurrences:
            return []
        matching = [
            cue
            for cue in self.director_cues
            if cue.cue_type == "shot"
            and any(
                ranges_intersect(
                    cue.start_seconds,
                    cue.end_seconds,
                    occurrence.start_seconds,
                    occurrence.end_seconds,
                )
                for occurrence in occurrences
            )
        ]
        if not matching:
            return []
        media_id = media_shortcut(asset)
        direction = self._semantic_shot_reference_direction(asset, semantic)
        adaptations = {
            str(row.get("cue_id", "")): row
            for row in (semantic.get("shot_adaptations") or [])
            if isinstance(row, dict) and str(row.get("cue_id", ""))
        }
        changes: list[tuple[DirectorCue, dict, dict]] = []
        for cue in matching:
            before = asdict(cue)
            references = dict(cue.semantic_reference_directions)
            references[media_id] = direction
            after = dict(before)
            after["semantic_reference_directions"] = references
            adaptation = adaptations.get(cue.cue_id)
            if adaptation:
                cue_fields = (
                    "framing", "camera_angle", "camera_movement",
                    "movement_speed", "movement_amplitude", "subject_action",
                    "environment_response", "continuity_state", "optional_flourish",
                )
                for field_name in cue_fields:
                    value = str(adaptation.get(field_name, "")).strip()
                    if value:
                        after[field_name] = value
                        if field_name == "subject_action":
                            after["authored_subject_action"] = value
                        elif field_name == "environment_response":
                            after["authored_environment_response"] = value
                adapted_direction = str(
                    adaptation.get("additional_direction", "")
                ).strip()
                integration = str(
                    adaptation.get("integration_strategy", "")
                ).strip()
                after["detail"] = " ".join(
                    part
                    for part in (
                        adapted_direction,
                        f"Integration strategy: {integration}" if integration else "",
                        (
                            "Reconstruct the replacement reference as a coherent moving scene; "
                            "never display it as a flat photo, poster, slideshow card or pasted overlay."
                            if asset.media_type == "image" else ""
                        ),
                    )
                    if part
                ).strip()
            reference_number = "".join(character for character in media_id if character.isdigit())
            reference_pattern = re.compile(
                rf"(?i)(?:\b{re.escape(media_id)}\b|"
                rf"<\s*(?:Picture|Video|Audio)\s+{re.escape(reference_number)}\s*>)"
            )
            authored_reference_text = " ".join(
                (cue.detail, cue.environment_response)
            )
            if not adaptation and reference_pattern.search(authored_reference_text):
                # A Design-authored field that explicitly names this media is
                # reference guidance, not unrelated story action. Replace that
                # stale interpretation while preserving Subject Action and all
                # other manually authored Shot properties.
                after["detail"] = direction
                environment = self._bounded_semantic_direction_value(
                    semantic.get("environment"), 620
                )
                lighting = self._bounded_semantic_direction_value(
                    semantic.get("lighting_and_color"), 480
                )
                if environment or lighting:
                    after["environment_response"] = ". ".join(
                        part
                        for part in (
                            environment,
                            f"Lighting/color: {lighting}" if lighting else "",
                        )
                        if part
                    ).rstrip(" .") + "."
                    after["authored_environment_response"] = after["environment_response"]
            budgeted = normalize_shot_action_budget({
                "start_seconds": after["start_seconds"],
                "end_seconds": after["end_seconds"],
                "subject_action": after.get("authored_subject_action") or after.get("subject_action", ""),
                "environment_response": (
                    after.get("authored_environment_response")
                    or after.get("environment_response", "")
                ),
                "continuity_state": after.get("continuity_state", ""),
                "optional_flourish": after.get("optional_flourish", ""),
            })
            after.update(
                subject_action=budgeted["subject_action"],
                environment_response=budgeted["environment_response"],
                continuity_state=budgeted["continuity_state"],
                optional_flourish=budgeted["optional_flourish"],
                h3_executable_action=budgeted["h3_executable_action"],
                h3_optional_flourish=budgeted["h3_optional_flourish"],
                action_budget_status=budgeted["action_budget"]["status"],
                action_budget_notes=budgeted["action_budget"]["notes"],
            )
            if after == before:
                continue
            changes.append((cue, before, after))
        if not changes:
            return []

        self.undo_stack.beginMacro(f"Sync {media_id} AI enrichment to Shots")
        try:
            for cue, before, after in changes:
                self.undo_stack.push(
                    DirectorCueEditCommand(
                        cue,
                        before,
                        after,
                        self._refresh_director_cues,
                        f"Update {cue.cue_id} from {media_id} AI enrichment",
                    )
                )
        finally:
            self.undo_stack.endMacro()
        for cue, _before, _after in changes:
            self._mark_render_range_dirty(cue.start_seconds, cue.end_seconds)
        self._mark_dirty()
        self.schedule_prompt_generation()
        return [cue.cue_id for cue, _before, _after in changes]

    def _reconcile_asset_shot_reference_ranges(self, asset: MediaAsset) -> list[str]:
        """Keep an existing AI reference attached only to overlapping Shots.

        Timeline edits may move, trim, duplicate or remove a Media Pool source
        after AI Design/AI Enrich has attached its evidence to one or more
        Shots.  The reference direction is source-owned, so retain the same
        grounded direction while moving its association to the Shots that now
        overlap any occurrence of that source.  This method intentionally does
        not invent a Shot or rewrite authored action.
        """

        if not self.scan:
            return []
        source = self._source_asset_for(asset)
        media_id = media_shortcut(source)
        direction = next(
            (
                cue.semantic_reference_directions.get(media_id, "")
                for cue in self.director_cues
                if cue.semantic_reference_directions.get(media_id, "").strip()
            ),
            "",
        )
        if not direction:
            return []
        occurrences = [
            item
            for item in self._timeline_assets()
            if item.timeline_placed and self._source_asset_for(item) is source
        ]
        changed: list[str] = []
        for cue in self.director_cues:
            if cue.cue_type != "shot":
                continue
            overlaps = any(
                ranges_intersect(
                    cue.start_seconds,
                    cue.end_seconds,
                    occurrence.start_seconds,
                    occurrence.end_seconds,
                )
                for occurrence in occurrences
            )
            references = dict(cue.semantic_reference_directions)
            before = references.get(media_id, "")
            if overlaps:
                references[media_id] = direction
            else:
                references.pop(media_id, None)
            if references != cue.semantic_reference_directions:
                cue.semantic_reference_directions = references
                changed.append(cue.cue_id)
            elif overlaps and not before:
                changed.append(cue.cue_id)
        return changed

    def _handle_semantic_payload(self, payload: dict) -> None:
        if payload.get("ready"):
            self.statusBar().showMessage("AI semantic enrichment service ready")
            return
        job_id = str(payload.get("job", ""))
        if job_id and job_id == self.semantic_unload_job_id:
            self.semantic_unload_job_id = ""
            if payload.get("error"):
                self.statusBar().showMessage(f"LM Studio unload warning: {payload['error']}")
            else:
                self.statusBar().showMessage("LM Studio semantic model unloaded")
            return
        job = self.semantic_jobs.pop(job_id, None)
        if not job:
            if job_id.startswith("media-enrich:"):
                self._maybe_request_semantic_lm_unload()
            return
        asset: MediaAsset = job["asset"]
        try:
            if payload.get("error"):
                raise RuntimeError(str(payload["error"]))
            resolved_model = str(payload.get("resolved_model", "")).strip()
            if job.get("provider") == "lm_studio" and resolved_model:
                job["model"] = resolved_model
                self.semantic_last_lm_request["model"] = resolved_model
                settings = load_design_settings(DESIGN_SETTINGS_ENV)
                if settings.lm_studio_model != resolved_model:
                    settings.lm_studio_model = resolved_model
                    save_design_settings(DESIGN_SETTINGS_ENV, settings)
                    self.design_ai_settings = settings
            current_fingerprint = self._semantic_source_fingerprint(asset)
            if job["path"] != asset.local_path or current_fingerprint != job["fingerprint"]:
                self.semantic_errors[asset.node_id] = (
                    "Stale AI response discarded because the source evidence changed."
                )
                self.statusBar().showMessage(
                    f"Discarded stale semantic result for {asset.tag}"
                )
                self._maybe_auto_enrich(asset)
                return
            normalized = normalize_semantic_enrichment(
                payload.get("text") or payload.get("response") or payload,
                expected_media_id=media_shortcut(asset),
                expected_media_type=asset.media_type,
                expected_fingerprint=job["fingerprint"],
            )
            asset.semantic_enrichment = render_semantic_enrichment(
                normalized,
                provider=job["provider"],
                model=job["model"],
            )
            asset.semantic_enrichment_source_hash = job["fingerprint"]
            asset.semantic_enrichment_model = f"{job['provider']} · {job['model']}"
            asset.semantic_enrichment_updated_at = time.strftime(
                "%Y-%m-%d %H:%M:%S UTC", time.gmtime()
            )
            self._sync_timeline_clip_sources(asset)
            self.semantic_errors.pop(asset.node_id, None)
            synced_shots = self._sync_semantic_enrichment_to_existing_shots(
                asset,
                normalized,
            )
            self._mark_dirty()
            self.schedule_prompt_generation()
            if synced_shots:
                self.statusBar().showMessage(
                    f"AI semantic enrichment ready for {asset.tag} · updated "
                    + ", ".join(synced_shots)
                )
            elif any(
                item.timeline_placed and self._source_asset_for(item) is asset
                for item in self._timeline_assets()
            ):
                self.statusBar().showMessage(
                    f"AI semantic enrichment ready for {asset.tag} · no existing overlapping Shot"
                )
            else:
                self.statusBar().showMessage(
                    f"AI semantic enrichment ready for {asset.tag} · asset is not on Timeline"
                )
        except Exception as exc:
            self.semantic_errors[asset.node_id] = str(exc)
            self.statusBar().showMessage(
                f"AI semantic enrichment failed for {asset.tag}: {exc}"
            )
        finally:
            self._refresh_semantic_card(asset)
            self._refresh_recognition_inspector(asset if asset is self.selected_asset else None)
            self._maybe_request_semantic_lm_unload(job)

    def _maybe_request_semantic_lm_unload(self, completed_job: dict | None = None) -> None:
        if completed_job and completed_job.get("provider") == "lm_studio":
            self.semantic_last_lm_request = dict(completed_job)
        if (
            self.semantic_jobs
            or self.semantic_unload_job_id
            or any(
                job.get("operation") != "audio-pan"
                for job in self.media_jobs.values()
                if isinstance(job, dict)
            )
            or self.blip_jobs
            or self.audio_jobs
        ):
            return
        request = self.semantic_last_lm_request
        if not request:
            return
        self.semantic_last_lm_request = {}
        if request.get("provider") != "lm_studio" or not request.get("unload_lm", True):
            return
        if not self.semantic_runner.is_running():
            return
        job_id = f"media-enrich-unload:{time.time_ns()}"
        self.semantic_unload_job_id = job_id
        try:
            self.semantic_runner.write_json({
                "job": job_id,
                "action": "unload_lm",
                "base_url": request.get("base_url", ""),
                "model": request.get("model", ""),
                "timeout": min(120, max(10, int(request.get("timeout", 60)))),
            })
        except Exception as exc:
            self.semantic_unload_job_id = ""
            self.statusBar().showMessage(f"LM Studio unload warning: {exc}")

    def _semantic_service_finished(self, exit_code: int, log: str) -> None:
        self.semantic_runner.discard_pending()
        if self._closing:
            self.semantic_jobs.clear()
            return
        detail = log[-300:] if log else f"exit {exit_code}"
        affected_assets: list[MediaAsset] = []
        for job in self.semantic_jobs.values():
            asset = job["asset"]
            affected_assets.append(asset)
            self.semantic_errors[asset.node_id] = f"Semantic service stopped: {detail}"
        self.semantic_jobs.clear()
        self.semantic_unload_job_id = ""
        self.semantic_last_lm_request = {}
        for asset in affected_assets:
            self._refresh_semantic_card(asset)
        self._refresh_recognition_inspector()

    def _mark_analysis_failure(self, asset: MediaAsset, detail: str) -> None:
        asset.recognition += f"\n\n{detail}"
        card = self.cards.get(asset.node_id)
        if card:
            card.set_analysis_status("识别 !")
        if asset is self.selected_asset:
            self._refresh_recognition_inspector(asset)
        self.statusBar().showMessage(f"{asset.tag} analysis failed — use Analyze to retry")

        QTimer.singleShot(0, lambda current=asset: self._maybe_auto_enrich(current))

    def _timeline_assets(self) -> list[MediaAsset]:
        return self.scan.timeline_assets() if self.scan else []

    def _source_asset_for(self, asset: MediaAsset) -> MediaAsset:
        if not self.scan or not asset.source_node_id:
            return asset
        return next(
            (item for item in self.scan.assets if item.node_id == asset.source_node_id),
            asset,
        )

    def _selected_clip(self) -> MediaAsset | None:
        return self.selected_timeline_asset or self.selected_asset

    def _sync_timeline_clip_sources(self, source: MediaAsset | None = None) -> None:
        """Refresh source-owned media and analysis on every repeated use."""
        if not self.scan:
            return
        shared = (
            "filename", "local_path", "recognition", "semantic_enrichment",
            "semantic_enrichment_source_hash", "semantic_enrichment_model",
            "semantic_enrichment_updated_at", "source_duration_seconds", "state",
            "binding", "paired_audio_binding", "tag", "class_type", "media_type",
            "reference_id", "is_virtual",
        )
        sources = {item.node_id: item for item in self.scan.assets}
        for clip in self.scan.timeline_clips:
            source_asset = sources.get(clip.source_node_id or clip.node_id)
            if source_asset is None or (source is not None and source_asset is not source):
                continue
            for name in shared:
                setattr(clip, name, getattr(source_asset, name))

    def _show_asset_inspector(self, source: MediaAsset, clip: MediaAsset) -> None:
        self.inspect_tag.setText(f"{source.tag} · {source.media_type.upper()}")
        instance = f" · {clip.clip_id}" if clip.clip_id else ""
        self.inspect_node.setText(f"{source.node_id} · {source.class_type}{instance}")
        self.inspect_file.setText(source.local_path or source.filename or "Not loaded")
        self.asset_start.setValue(clip.start_seconds)
        self.asset_end.setValue(clip.end_seconds)
        self.asset_speed.setValue(clip.playback_speed)
        self.asset_source_in.setValue(clip.source_in_seconds)
        self.asset_source_out.setValue(clip.source_out_seconds)
        self.asset_fade_in.setValue(clip.fade_in_seconds)
        self.asset_fade_out.setValue(clip.fade_out_seconds)
        self.asset_transition_in.setCurrentText(clip.transition_in)
        self.asset_transition_out.setCurrentText(clip.transition_out)
        self._refresh_recognition_inspector(source)
        self.remove_clip_button.setEnabled(clip.timeline_placed)
        for mode, button in self.mode_buttons.items():
            button.setChecked(mode == clip.activation_mode)
        self.render_timeline_at(self.playhead_seconds, force_seek=False)

    def select_asset(self, asset: MediaAsset) -> None:
        """Select a Media Pool source rather than a particular occurrence."""
        self.selected_asset = self._source_asset_for(asset)
        self.selected_timeline_asset = None
        self._show_asset_inspector(self.selected_asset, self.selected_asset)

    def select_timeline_asset(self, clip: MediaAsset) -> None:
        """Select one independently editable Timeline occurrence."""
        source = self._source_asset_for(clip)
        self.selected_asset = source
        self.selected_timeline_asset = clip
        self._show_asset_inspector(source, clip)

    def set_timeline_tool(self, mode: str) -> None:
        if mode not in self.timeline_tool_buttons:
            mode = "selection"
        for name, button in self.timeline_tool_buttons.items():
            button.setChecked(name == mode)
            button.setIcon(
                editor_icon(name, "#2fb7ff" if name == mode else "#d8dde3")
            )
        self.timeline.set_tool_mode(mode)
        for label in self.monitor_text_labels.values():
            label.set_selection_enabled(mode == "selection")
        messages = {
            "selection": "Selection Tool · move clips or drag text directly in Program Monitor",
            "type": "Type Tool · Content Role automatically selects a V track or a dedicated Dialogue/Voice-over/Lyrics A track",
            "prompt": "Prompt Tool · click a clip to add or edit its director instruction",
            "hand": "Hand Tool · drag the Timeline horizontally or vertically to navigate",
            "razor": "Razor Tool · click media for a CUT boundary or split text/director blocks",
            "shot": "Shot Tool · drag horizontally on a visual track to define the Shot Block time range",
            "transition": "Transition Tool · click a cut point to add a transition preset",
            "marker": "Marker Tool · click to add SFX, music, beat, camera, or ending cues",
        }
        self.statusBar().showMessage(messages[mode])

    def _refresh_timeline_tool_labels(self) -> None:
        if not hasattr(self, "timeline_tool_palette"):
            return
        minimum_width = getattr(self, "timeline_tools_minimum_width", 118)
        self.timeline_tool_scroll.setMinimumWidth(minimum_width)
        for button in self.timeline_tool_buttons.values():
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

    def _visual_track_is_empty_for_range(
        self,
        track: TimelineTrack,
        start_seconds: float,
        end_seconds: float,
    ) -> bool:
        """Return whether a visual track has no media or text in a time range."""
        if track.kind != "visual" or track.locked or not self.scan:
            return False
        for item in self.scan.timeline_assets():
            if (
                item.timeline_placed
                and item.media_type in {"image", "video"}
                and item.timeline_track_id == track.track_id
                and ranges_intersect(
                    item.start_seconds,
                    item.end_seconds,
                    start_seconds,
                    end_seconds,
                )
            ):
                return False
        return not any(
            layer.track_id == track.track_id
            and ranges_intersect(
                layer.start_seconds,
                layer.end_seconds,
                start_seconds,
                end_seconds,
            )
            for layer in self.text_layers
        )

    def _nearest_empty_visual_track(
        self,
        source_track: TimelineTrack | None,
        start_seconds: float,
        end_seconds: float,
    ) -> TimelineTrack | None:
        source_index = self.tracks.index(source_track) if source_track in self.tracks else 0
        candidates = [
            (index, track)
            for index, track in enumerate(self.tracks)
            if track is not source_track
            and self._visual_track_is_empty_for_range(track, start_seconds, end_seconds)
        ]
        if not candidates:
            return None
        # Prefer the nearest layer above the source when distances are equal.
        _index, track = min(
            candidates,
            key=lambda row: (
                abs(row[0] - source_index),
                0 if row[0] < source_index else 1,
                row[0],
            ),
        )
        return track

    def _type_tool_targeted(self, asset: MediaAsset) -> None:
        source_track = self._track_for_asset(asset)
        track = self._nearest_empty_visual_track(
            source_track,
            asset.start_seconds,
            asset.end_seconds,
        )
        if track is None:
            self.statusBar().showMessage(
                "Type Tool · no empty V track for this range; add a V track or click an empty range"
            )
            return
        self.create_text_layer(asset.start_seconds, track.track_id, asset.end_seconds)

    def _next_text_layer_id(self) -> str:
        numbers = [
            int(layer.layer_id[1:])
            for layer in self.text_layers
            if layer.layer_id.startswith("T") and layer.layer_id[1:].isdigit()
        ]
        return f"T{max(numbers, default=0) + 1}"

    def create_text_layer(
        self,
        start_seconds: float,
        track_id: str,
        end_seconds: float | None = None,
    ) -> None:
        if not self.scan:
            return
        requested_end = float(end_seconds) if end_seconds is not None else float(start_seconds) + 3.0
        start, end = snap_timeline_range(
            start_seconds,
            requested_end,
            self.scan.duration_seconds,
        )
        layer = TextLayer(self._next_text_layer_id(), "", start, end, track_id)
        dialog = ContentLayerDialog(layer, self.scan.duration_seconds, self.director_cues, self)
        if dialog.exec() != QDialog.Accepted:
            dialog.deleteLater()
            return
        state = dialog.state()
        dialog.deleteLater()
        for name, value in state.items():
            setattr(layer, name, value)
        self.undo_stack.push(AddTextLayerCommand(self.text_layers, layer, self._refresh_text_layers))
        self._mark_render_range_dirty(layer.start_seconds, layer.end_seconds)
        self._mark_dirty()
        self.statusBar().showMessage(f"Created {layer.layer_id} text layer")

    def select_text_layer(self, layer: TextLayer) -> None:
        self.statusBar().showMessage(
            f"Selected {layer.layer_id} · {layer.start_seconds:.2f}s–{layer.end_seconds:.2f}s · use Type Tool to edit"
        )

    def edit_text_layer(self, layer: TextLayer) -> None:
        if not self.scan or layer not in self.text_layers:
            return
        dialog = ContentLayerDialog(layer, self.scan.duration_seconds, self.director_cues, self)
        if dialog.exec() != QDialog.Accepted:
            dialog.deleteLater()
            return
        before = asdict(layer)
        after = dict(before)
        after.update(dialog.state())
        dialog.deleteLater()
        if before == after:
            return
        self.undo_stack.push(
            TextLayerEditCommand(layer, before, after, self._refresh_text_layers, "Edit text layer")
        )
        self._mark_render_states_dirty(before, after)
        self._mark_dirty()

    def commit_text_layer_edit(self, layer: TextLayer, before: dict, after: dict) -> None:
        if before == after:
            return
        self.undo_stack.push(
            TextLayerEditCommand(layer, before, after, self._refresh_text_layers, "Move text layer")
        )
        self._mark_render_states_dirty(before, after)
        self._mark_dirty()

    def remove_text_layer(self, layer: TextLayer) -> None:
        if layer not in self.text_layers:
            return
        state = asdict(layer)
        self.undo_stack.push(RemoveTextLayerCommand(self.text_layers, layer, self._refresh_text_layers))
        self._mark_render_states_dirty(state)
        self._mark_dirty()

    def _normalize_text_layer_tracks(self) -> bool:
        """Repair old projects and role edits without hiding speech on V tracks."""
        track_model_changed = False
        for layer in self.text_layers:
            wanted_kind = text_layer_track_kind(layer.content_role)
            current_track = next(
                (
                    track
                    for track in self.tracks
                    if track.track_id == layer.track_id
                    and track.kind == wanted_kind
                ),
                None,
            )
            if current_track is None:
                current_track = self._design_track(
                    default_text_layer_track(layer.content_role), wanted_kind
                )
                layer.track_id = current_track.track_id
                track_model_changed = True
            wanted_name = text_layer_track_name(
                current_track.track_id, layer.content_role
            )
            if current_track.name in {current_track.track_id, wanted_name}:
                if current_track.name != wanted_name:
                    current_track.name = wanted_name
                    track_model_changed = True
        return track_model_changed

    def _refresh_text_layers(self, _layer: TextLayer | None = None) -> None:
        track_model_changed = self._normalize_text_layer_tracks()
        if not self.restoring_project:
            # Once the user edits a Timeline text layer, the Timeline becomes
            # the authored contract.  This keeps validation, Shot prompts and
            # the synthesized WAV on the same exact words and timing.
            self.authored_text_requirements = [
                {
                    "start_seconds": layer.start_seconds,
                    "end_seconds": layer.end_seconds,
                    "track": layer.track_id,
                    "content": layer.text,
                    "role": layer.content_role,
                    "speaker": layer.speaker,
                    "language": layer.language,
                    "delivery": layer.delivery,
                    "lip_sync": layer.lip_sync,
                    "explicit_user_requested": True,
                }
                for layer in self.text_layers
                if layer.text.strip()
            ]
            if (
                _layer is not None
                and _layer.content_role in {"dialogue", "voice_over", "lyrics"}
            ):
                self.timeline_tts_stale = True
                if (
                    self.render_settings.dialogue_tts_engine != "h3_native"
                    and self._authored_tts_asset() is not None
                ):
                    self.timeline_tts_refresh_timer.start()
        if track_model_changed:
            self.timeline.set_tracks(self.tracks)
            self._rebuild_track_headers()
        self.timeline.set_text_layers(self.text_layers)
        self._sync_prompt_panel_from_timeline(reconcile_brief=True)
        self.render_timeline_at(self.playhead_seconds, force_seek=True)

    def _next_director_cue_id(self, prefix: str = "C") -> str:
        numbers = [
            int(cue.cue_id[1:])
            for cue in self.director_cues
            if cue.cue_id.startswith(prefix) and cue.cue_id[1:].isdigit()
        ]
        return f"{prefix}{max(numbers, default=0) + 1}"

    def add_director_cue(
        self,
        cue_type: str,
        start_seconds: float,
        preset: str,
        detail: str = "",
        end_seconds: float | None = None,
    ) -> DirectorCue | None:
        """Add a cue without opening a dialog; used by tools and testable integrations."""
        if not self.scan or cue_type not in (*DIRECTOR_LANE_TYPES, "cut"):
            return None
        start = snap_timeline_seconds(start_seconds, self.scan.duration_seconds)
        default_length = 3.0 if cue_type == "shot" else 0.12
        start, end = snap_timeline_range(
            start,
            float(end_seconds) if end_seconds is not None else start + default_length,
            self.scan.duration_seconds,
        )
        prefix = {"shot": "S", "transition": "X", "marker": "M", "cut": "C"}[cue_type]
        cue = DirectorCue(
            self._next_director_cue_id(prefix), cue_type, start, end, preset.strip(), detail.strip()
        )
        self._seed_native_audio_for_new_cue(cue)
        self.undo_stack.push(AddDirectorCueCommand(self.director_cues, cue, self._refresh_director_cues))
        self._mark_render_range_dirty(cue.start_seconds, cue.end_seconds)
        self._mark_dirty()
        return cue

    def create_director_cue(self, cue_type: str, start_seconds: float) -> None:
        if not self.scan or cue_type not in DIRECTOR_LANE_TYPES:
            return
        start = snap_timeline_seconds(start_seconds, self.scan.duration_seconds)
        length = 3.0 if cue_type == "shot" else 0.12
        start, end = snap_timeline_range(start, start + length, self.scan.duration_seconds)
        prefix = {"shot": "S", "transition": "X", "marker": "M"}[cue_type]
        default_preset = DirectorCueDialog.PRESETS[cue_type][0]
        cue = DirectorCue(self._next_director_cue_id(prefix), cue_type, start, end, default_preset)
        self._seed_native_audio_for_new_cue(cue)
        dialog = DirectorCueDialog(cue, self.scan.duration_seconds, self)
        if dialog.exec() != QDialog.Accepted:
            dialog.deleteLater()
            return
        state = dialog.state()
        dialog.deleteLater()
        for name, value in state.items():
            setattr(cue, name, value)
        self.undo_stack.push(AddDirectorCueCommand(self.director_cues, cue, self._refresh_director_cues))
        self._mark_render_range_dirty(cue.start_seconds, cue.end_seconds)
        self._mark_dirty()
        self.statusBar().showMessage(f"Created {cue.cue_id} · {cue.preset}")

    def create_shot_range(self, start_seconds: float, end_seconds: float, track_id: str) -> None:
        """Create the structured Shot Block produced by dragging on a visual track."""
        if not self.scan or not any(
            track.track_id == track_id and track.kind == "visual" for track in self.tracks
        ):
            return
        start, end = snap_timeline_range(
            start_seconds, end_seconds, self.scan.duration_seconds
        )
        cue = DirectorCue(
            self._next_director_cue_id("S"),
            "shot",
            start,
            end,
            DirectorCueDialog.PRESETS["shot"][0],
            track_id=track_id,
        )
        self._seed_native_audio_for_new_cue(cue)
        dialog = DirectorCueDialog(cue, self.scan.duration_seconds, self)
        if dialog.exec() != QDialog.Accepted:
            dialog.deleteLater()
            return
        state = dialog.state()
        dialog.deleteLater()
        for name, value in state.items():
            setattr(cue, name, value)
        # A second queued boundary is intentional: the first one opened this
        # modal dialog from mouseReleaseEvent; this one lets QDialog::exec and
        # its native controls fully unwind before QUndoStack triggers UI work.
        QTimer.singleShot(0, lambda item=cue, target=track_id: self._commit_new_shot(item, target))

    def _commit_new_shot(self, cue: DirectorCue, track_id: str) -> None:
        if self._closing or not self.scan or cue in self.director_cues:
            return
        if self.timeline.interaction_active:
            QTimer.singleShot(10, lambda item=cue, target=track_id: self._commit_new_shot(item, target))
            return
        self.undo_stack.push(AddDirectorCueCommand(self.director_cues, cue, self._refresh_director_cues))
        self._mark_render_range_dirty(cue.start_seconds, cue.end_seconds)
        self._mark_dirty()
        number = cue.cue_id[1:] if cue.cue_id.startswith("S") else cue.cue_id
        self.statusBar().showMessage(
            f"Created SHOT {number} · {cue.start_seconds:.2f}–{cue.end_seconds:.2f}s on {track_id}"
        )

    def edit_director_cue(self, cue: DirectorCue) -> None:
        if not self.scan or cue not in self.director_cues:
            return
        self._refresh_native_audio_directions()
        dialog = DirectorCueDialog(cue, self.scan.duration_seconds, self)
        if dialog.exec() != QDialog.Accepted:
            dialog.deleteLater()
            return
        before = asdict(cue)
        after = dict(before)
        after.update(dialog.state())
        dialog.deleteLater()
        if before == after:
            return
        self.undo_stack.push(
            DirectorCueEditCommand(cue, before, after, self._refresh_director_cues, "Edit director cue")
        )
        self._mark_render_states_dirty(before, after)
        self._mark_dirty()

    def remove_director_cue(self, cue: DirectorCue) -> None:
        if cue not in self.director_cues:
            return
        if (
            cue.cue_type == "shot"
            and self.storyboard_trim_active
        ):
            self._ripple_delete_storyboard_shot(cue)
            return
        state = asdict(cue)
        self.undo_stack.push(
            RemoveDirectorCueCommand(
                self.director_cues, cue, self._refresh_director_cues, self.text_layers
            )
        )
        self._mark_render_states_dirty(state)
        self._mark_dirty()

    @staticmethod
    def _ripple_interval(
        item_start: float,
        item_end: float,
        cut_start: float,
        cut_end: float,
    ) -> tuple[float, float] | None:
        """Remove one Timeline interval and return the surviving rippled range."""
        start = float(item_start)
        end = float(item_end)
        delta = cut_end - cut_start
        if end <= cut_start + 1e-6:
            return start, end
        if start >= cut_end - 1e-6:
            return start - delta, end - delta
        if start >= cut_start - 1e-6 and end <= cut_end + 1e-6:
            return None
        if start < cut_start and end > cut_end:
            return start, end - delta
        if start < cut_start < end <= cut_end + 1e-6:
            return (start, cut_start) if cut_start - start >= 0.1 else None
        if cut_start - 1e-6 <= start < cut_end < end:
            shifted_end = end - delta
            return (cut_start, shifted_end) if shifted_end - cut_start >= 0.1 else None
        return start, end

    def _ripple_delete_storyboard_shot(self, shot: DirectorCue) -> None:
        """Delete a Storyboard Shot and ripple all dependent Timeline layers left."""
        if not self.scan or shot not in self.director_cues:
            return
        cut_start = max(0.0, float(shot.start_seconds))
        cut_end = min(self.scan.duration_seconds, float(shot.end_seconds))
        delta = cut_end - cut_start
        if delta < 0.1:
            self.statusBar().showMessage("Storyboard Shot is too short to ripple delete")
            return
        old_duration = float(self.scan.duration_seconds)
        before = self._design_workspace_state()

        retained_cues: list[DirectorCue] = []
        for cue in self.director_cues:
            if cue is shot:
                continue
            adjusted = self._ripple_interval(
                cue.start_seconds, cue.end_seconds, cut_start, cut_end
            )
            if adjusted is None:
                continue
            cue.start_seconds, cue.end_seconds = adjusted
            retained_cues.append(cue)
        self.director_cues = retained_cues

        retained_text: list[TextLayer] = []
        for layer in self.text_layers:
            adjusted = self._ripple_interval(
                layer.start_seconds, layer.end_seconds, cut_start, cut_end
            )
            if adjusted is None:
                continue
            layer.start_seconds, layer.end_seconds = adjusted
            retained_text.append(layer)
        self.text_layers = retained_text

        added_clips: list[MediaAsset] = []

        def adjust_media(asset: MediaAsset) -> bool:
            if not asset.timeline_placed:
                return True
            original_start = float(asset.start_seconds)
            original_end = float(asset.end_seconds)
            adjusted = self._ripple_interval(
                original_start, original_end, cut_start, cut_end
            )
            if adjusted is None:
                asset.timeline_placed = False
                return False
            # A moving Audio/Video clip spanning the removed interval needs a
            # real source discontinuity. Split it into head and tail; still
            # images can simply remain visible across the joined boundary.
            if (
                asset.media_type in {"audio", "video"}
                and original_start < cut_start - 1e-6
                and original_end > cut_end + 1e-6
            ):
                tail = deepcopy(asset)
                tail.clip_id = f"clip-{secrets.token_hex(8)}"
                tail.source_node_id = asset.source_node_id or asset.node_id
                tail.start_seconds = cut_start
                tail.end_seconds = original_end - delta
                tail.source_in_seconds = (
                    float(asset.source_in_seconds)
                    + (cut_end - original_start) * float(asset.playback_speed)
                )
                asset.end_seconds = cut_start
                if asset.source_duration_seconds > 0:
                    asset.source_out_seconds = min(
                        float(asset.source_duration_seconds),
                        float(asset.source_in_seconds)
                        + (cut_start - original_start) * float(asset.playback_speed),
                    )
                added_clips.append(tail)
                return True
            new_start, new_end = adjusted
            if (
                asset.media_type in {"audio", "video"}
                and original_start >= cut_start - 1e-6
                and original_start < cut_end - 1e-6
                and original_end > cut_end + 1e-6
            ):
                asset.source_in_seconds = (
                    float(asset.source_in_seconds)
                    + (cut_end - original_start) * float(asset.playback_speed)
                )
            asset.start_seconds, asset.end_seconds = new_start, new_end
            return True

        for asset in self.scan.assets:
            adjust_media(asset)
        retained_clips: list[MediaAsset] = []
        for clip in self.scan.timeline_clips:
            if adjust_media(clip):
                retained_clips.append(clip)
        self.scan.timeline_clips = retained_clips + added_clips
        self._sync_timeline_clip_sources()

        new_duration = max(0.5, old_duration - delta)
        self._set_design_duration(new_duration)
        ordered_shots = sorted(
            (cue for cue in self.director_cues if cue.cue_type == "shot"),
            key=lambda cue: (cue.start_seconds, cue.end_seconds),
        )
        for layer in self.text_layers:
            midpoint = (layer.start_seconds + layer.end_seconds) / 2
            layer.shot_id = next(
                (
                    cue.cue_id for cue in ordered_shots
                    if cue.start_seconds <= midpoint <= cue.end_seconds
                ),
                "",
            )
        self.timeline_tts_stale = True
        self._refresh_director_cues()
        self._refresh_text_layers()
        self.seek_timeline(min(cut_start, new_duration))
        after = self._design_workspace_state()
        self._restore_design_workspace_state(before)
        self.undo_stack.push(
            WorkspaceDesignCommand(
                before,
                after,
                self._restore_design_workspace_state,
                "Ripple delete Storyboard Shot",
            )
        )
        self._clear_generated_output()
        self._mark_all_render_segments_dirty()
        self._mark_dirty()
        self._refresh_storyboard_trim_controls()
        remaining = max(
            0.0,
            self.scan.duration_seconds - self.storyboard_target_duration_seconds,
        )
        self.statusBar().showMessage(
            f"Deleted {shot.cue_id} and rippled {delta:.1f}s · Timeline "
            f"{old_duration:.1f}s → {self.scan.duration_seconds:.1f}s · "
            f"{remaining:.1f}s still above Story target · Undo available."
        )

    def _refresh_director_cues(self, _cue: DirectorCue | None = None) -> None:
        self.director_cues.sort(key=lambda cue: (cue.start_seconds, cue.end_seconds, cue.cue_id))
        for cue in self.director_cues:
            if cue.cue_type != "shot":
                continue
            budgeted = normalize_shot_action_budget({
                "start_seconds": cue.start_seconds,
                "end_seconds": cue.end_seconds,
                "subject_action": cue.authored_subject_action or cue.subject_action,
                "environment_response": (
                    cue.authored_environment_response or cue.environment_response
                ),
                "continuity_state": cue.continuity_state,
                "optional_flourish": cue.optional_flourish,
            })
            cue.subject_action = budgeted["subject_action"]
            cue.environment_response = budgeted["environment_response"]
            cue.continuity_state = budgeted["continuity_state"]
            cue.optional_flourish = budgeted["optional_flourish"]
            cue.h3_executable_action = budgeted["h3_executable_action"]
            cue.h3_optional_flourish = budgeted["h3_optional_flourish"]
            cue.action_budget_status = budgeted["action_budget"]["status"]
            cue.action_budget_notes = budgeted["action_budget"]["notes"]
        self.timeline.set_director_cues(self.director_cues)
        self._sync_prompt_panel_from_timeline(reconcile_brief=True)

    def razor_asset(self, asset: MediaAsset, seconds: float) -> None:
        if not asset.timeline_placed or not (asset.start_seconds < seconds < asset.end_seconds):
            self.statusBar().showMessage("Razor must be inside the media clip")
            return
        cue = self.add_director_cue(
            "cut", seconds, "CUT", f"Cut boundary inside {asset.tag}", seconds + 0.08
        )
        if cue:
            self.statusBar().showMessage(f"Added {cue.cue_id} CUT at {seconds:.2f}s")

    def razor_text_layer(self, layer: TextLayer, seconds: float) -> None:
        if layer not in self.text_layers or not (layer.start_seconds + 0.05 < seconds < layer.end_seconds - 0.05):
            self.statusBar().showMessage("Razor must be inside the text block")
            return
        clone_state = asdict(layer)
        clone_state.update(
            layer_id=self._next_text_layer_id(),
            start_seconds=seconds,
        )
        clone = text_layer_from_mapping(clone_state)
        self.undo_stack.push(
            SplitTextLayerCommand(self.text_layers, layer, clone, seconds, self._refresh_text_layers)
        )
        self._mark_render_range_dirty(layer.start_seconds, layer.end_seconds)
        self._mark_dirty()
        self.statusBar().showMessage(f"Split {layer.layer_id} at {seconds:.2f}s")

    def razor_director_cue(self, cue: DirectorCue, seconds: float) -> None:
        if cue not in self.director_cues or not (
            cue.start_seconds + 0.05 < seconds < cue.end_seconds - 0.05
        ):
            self.statusBar().showMessage("This cue is too short to split at that point")
            return
        prefix = cue.cue_id[:1] if cue.cue_id else "C"
        clone_state = asdict(cue)
        clone_state.update(
            cue_id=self._next_director_cue_id(prefix),
            start_seconds=seconds,
        )
        clone = DirectorCue(**clone_state)
        self.undo_stack.push(
            SplitDirectorCueCommand(self.director_cues, cue, clone, seconds, self._refresh_director_cues)
        )
        self._mark_render_range_dirty(cue.start_seconds, cue.end_seconds)
        self._mark_dirty()
        self.statusBar().showMessage(f"Split {cue.cue_id} at {seconds:.2f}s")

    def edit_clip_prompt(self, asset: MediaAsset) -> None:
        self.select_timeline_asset(asset)
        initial_prompt = asset.clip_prompt
        if not initial_prompt.strip() and asset.media_type == "image":
            initial_prompt = self._blip_caption_for_asset(asset)
        prompt, accepted = QInputDialog.getMultiLineText(
            self,
            f"Prompt Tool · {asset.tag}",
            "Director instruction for this clip:",
            initial_prompt,
        )
        if accepted:
            self.set_clip_prompt(asset, prompt)

    @staticmethod
    def _blip_caption_for_asset(asset: MediaAsset) -> str:
        captions: list[str] = []
        for line in asset.recognition.splitlines():
            compact = re.match(
                r"\s*BLIP\s*·\s*[^:]+:\s*(.+?)\s*$",
                line,
                flags=re.I,
            )
            if compact:
                caption = compact.group(1).strip()
                if caption and caption not in captions:
                    captions.append(caption)
                continue
            match = re.match(
                r"\s*BLIP visual (?:caption|region)(?:\s*·\s*[^:]+)?\s*:\s*(.+?)\s*$",
                line,
                flags=re.I,
            )
            if match:
                caption = match.group(1).strip()
                if caption and caption not in captions:
                    captions.append(caption)
        return "\n".join(captions)

    def set_clip_prompt(self, asset: MediaAsset, prompt: str) -> None:
        normalized = prompt.strip()
        if asset.clip_prompt == normalized:
            return
        before = timeline_state(asset)
        after = dict(before)
        after["clip_prompt"] = normalized
        self.undo_stack.push(
            AssetEditCommand(
                asset,
                before,
                after,
                self._refresh_after_asset_command,
                "Edit clip prompt",
            )
        )
        self._mark_render_states_dirty(before, after)
        self._mark_dirty()
        self._sync_prompt_panel_from_timeline()
        state = "saved" if normalized else "cleared"
        self.statusBar().showMessage(f"{asset.tag} clip prompt {state}")
        source = self._source_asset_for(asset)
        self._refresh_recognition_inspector(source if source is self.selected_asset else None)
        self._maybe_auto_enrich(source)

    def select_track(self, track: TimelineTrack) -> None:
        self.selected_track = track
        self.statusBar().showMessage(f"Selected {track.kind} track {track.name}")

    def change_track_property(self, track: TimelineTrack, property_name: str, value) -> None:
        if track not in self.tracks or not hasattr(track, property_name):
            return
        normalized = value
        if property_name == "name":
            normalized = str(value).strip() or track.track_id
        elif property_name == "height":
            normalized = max(20, min(140, int(value)))
        elif property_name in {"opacity", "volume"}:
            normalized = max(0.0, min(1.0, float(value)))
        elif property_name == "pan":
            normalized = max(-1.0, min(1.0, float(value)))
        elif property_name == "blend_mode" and normalized not in TrackHeaderWidget.BLEND_MODES:
            normalized = "Normal"
        if getattr(track, property_name) == normalized:
            return
        before = asdict(track)
        after = dict(before)
        after[property_name] = normalized
        label = property_name.replace("_", " ").title()
        self.undo_stack.push(
            TrackEditCommand(
                track,
                before,
                after,
                self._refresh_track_after_command,
                f"Change track {label}",
            )
        )
        self.select_track(track)
        if property_name not in {"name", "color", "height"}:
            self._mark_all_render_segments_dirty()
        self._mark_dirty()

    def _sync_timeline_zoom(self, pixels_per_second: float) -> None:
        value = round(pixels_per_second)
        self.timeline_zoom.blockSignals(True)
        self.timeline_zoom.setValue(value)
        self.timeline_zoom.blockSignals(False)
        self.timeline_zoom_label.setText(f"{round(pixels_per_second / 70.0 * 100)}%")

    def add_video_track(self) -> None:
        number = self._next_track_number("V")
        track = TimelineTrack(f"V{number}", f"V{number}", "visual", "#3978ba")
        index = next((i for i, item in enumerate(self.tracks) if item.kind == "visual"), 0)
        self.undo_stack.push(AddTrackCommand(self.tracks, track, index, self._refresh_tracks))
        self.select_track(track)
        self._mark_dirty()

    def add_audio_track(self) -> None:
        number = self._next_track_number("A")
        track = TimelineTrack(f"A{number}", f"A{number}", "audio", "#258a70")
        self.undo_stack.push(AddTrackCommand(self.tracks, track, len(self.tracks), self._refresh_tracks))
        self.select_track(track)
        self._mark_dirty()

    def _next_track_number(self, prefix: str) -> int:
        numbers = [
            int(track.track_id[1:])
            for track in self.tracks
            if track.track_id.startswith(prefix) and track.track_id[1:].isdigit()
        ]
        return max(numbers, default=0) + 1

    def add_track_beside(self, source: TimelineTrack) -> None:
        if source not in self.tracks:
            return
        prefix = "V" if source.kind == "visual" else "A"
        number = self._next_track_number(prefix)
        color = "#3978ba" if source.kind == "visual" else "#258a70"
        track = TimelineTrack(f"{prefix}{number}", f"{prefix}{number}", source.kind, color)
        index = self.tracks.index(source) + 1
        self.undo_stack.push(AddTrackCommand(self.tracks, track, index, self._refresh_tracks))
        self.select_track(track)
        self._mark_dirty()
        self.statusBar().showMessage(f"Added {track.track_id} beside {source.track_id}")

    def delete_track(self, track: TimelineTrack) -> None:
        if track not in self.tracks:
            return
        compatible = [item for item in self.tracks if item.kind == track.kind and item is not track]
        if not compatible:
            self.statusBar().showMessage(f"Keep at least one {track.kind} track")
            return
        source_index = self.tracks.index(track)
        fallback = min(compatible, key=lambda item: abs(self.tracks.index(item) - source_index))
        assets = self.scan.timeline_assets() if self.scan else []
        self.undo_stack.push(
            RemoveTrackCommand(
                self.tracks,
                track,
                fallback,
                assets,
                self.text_layers,
                self.director_cues,
                self._refresh_tracks,
            )
        )
        self.select_track(fallback)
        self._mark_dirty()
        self.statusBar().showMessage(
            f"Deleted {track.track_id} · its clips moved to {fallback.track_id} · Undo available"
        )

    def _refresh_tracks(self, _track: TimelineTrack | None = None) -> None:
        self.timeline.set_tracks(self.tracks)
        self._rebuild_track_headers()
        self.render_timeline_at(self.playhead_seconds, force_seek=True)

    def _rebuild_track_headers(self) -> None:
        if not hasattr(self, "track_header_layout"):
            return
        while self.track_header_layout.count():
            item = self.track_header_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.track_header_widgets.clear()
        ruler_spacer = QWidget()
        ruler_spacer.setFixedHeight(TIMELINE_RULER_HEIGHT)
        ruler_spacer.setStyleSheet("background:#181b1f; border-bottom:1px solid #34383d;")
        self.track_header_layout.addWidget(ruler_spacer)
        render_status_label = QLabel("RENDER")
        render_status_label.setFixedHeight(RENDER_STATUS_BAR_HEIGHT)
        render_status_label.setToolTip(
            "Render Status · green reusable · yellow dirty · blue rendering · red failed · gray pending"
        )
        render_status_label.setStyleSheet(
            "background:#30343a; color:#a5adb5; padding-left:6px; font-size:7px;"
        )
        self.track_header_layout.addWidget(render_status_label)
        for lane_name in ("SHOT", "TRANSITION", "MARKER"):
            label = QLabel(lane_name)
            label.setFixedHeight(DIRECTOR_LANE_HEIGHT)
            label.setStyleSheet(
                "background:#20242a; color:#98a1ab; border-bottom:1px solid #34383d; "
                "padding-left:6px; font-size:9px; font-weight:600;"
            )
            self.track_header_layout.addWidget(label)
        for track in self.tracks:
            header = TrackHeaderWidget(
                track,
                218,
                self.select_track,
                self.change_track_property,
                self.add_track_beside,
                self.delete_track,
            )
            self.track_header_widgets[track.track_id] = header
            self.track_header_layout.addWidget(header)
        bottom_spacer = QWidget()
        bottom_spacer.setFixedHeight(18)
        self.track_header_layout.addWidget(bottom_spacer)
        self.track_header_layout.addStretch()
        self.track_header_container.setMinimumHeight(
            TIMELINE_TRACKS_TOP + sum(track.height for track in self.tracks) + 18
        )
        # Rebuilding the header container can preserve its old scrollbar value
        # while QGraphicsView has already returned to the top.  Defer until Qt
        # recalculates both ranges, then make the Timeline the source of truth.
        QTimer.singleShot(0, self._sync_timeline_track_scrolls)

    def _sync_timeline_track_scrolls(self) -> None:
        """Keep Track Header rows aligned with their Timeline scene rows."""
        if not hasattr(self, "timeline") or not hasattr(self, "track_header_scroll"):
            return
        timeline_bar = self.timeline.verticalScrollBar()
        header_bar = self.track_header_scroll.verticalScrollBar()
        target = max(
            header_bar.minimum(),
            min(header_bar.maximum(), timeline_bar.value()),
        )
        blocked = header_bar.blockSignals(True)
        try:
            header_bar.setValue(target)
        finally:
            header_bar.blockSignals(blocked)

    def _refresh_track_after_command(self, track: TimelineTrack) -> None:
        header = self.track_header_widgets.get(track.track_id)
        if header is None or header.height() != track.height:
            self._rebuild_track_headers()
        else:
            header.sync_from_track()
        self.timeline.refresh_track(track)
        self.render_timeline_at(self.playhead_seconds, force_seek=True)
        if self.selected_track is track:
            self.select_track(track)

    def _show_monitor_pixmap(self, pixmap: QPixmap) -> None:
        target = self.monitor_image.size() - QSize(20, 20)
        self.monitor_image.setPixmap(pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _generated_video_frame_changed(self, frame) -> None:
        try:
            image = frame.toImage()
        except RuntimeError:
            return
        if image.isNull():
            return
        self.generated_frame_pixmap = QPixmap.fromImage(image)
        self._scale_generated_video_frame()

    def _scale_generated_video_frame(self) -> None:
        if not hasattr(self, "generated_video_widget") or self.generated_frame_pixmap.isNull():
            return
        target = self.generated_video_widget.size() - QSize(4, 4)
        if target.width() <= 0 or target.height() <= 0:
            return
        self.generated_video_widget.setPixmap(
            self.generated_frame_pixmap.scaled(
                target,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.monitor_stack.currentWidget() == self.monitor_image:
            self.render_timeline_at(self.playhead_seconds, force_seek=True)
        self._scale_generated_video_frame()

    def set_activation_mode(self, mode: str) -> None:
        asset = self._selected_clip()
        if not asset:
            return
        before = timeline_state(asset)
        after = dict(before)
        after["activation_mode"] = mode
        self.undo_stack.push(
            AssetEditCommand(asset, before, after, self._refresh_after_asset_command, "Change activation")
        )
        self._mark_render_states_dirty(before, after)
        self._mark_dirty()

    def apply_asset_range(self) -> None:
        asset = self._selected_clip()
        if not asset:
            return
        duration = self.scan.duration_seconds if self.scan else self.asset_end.maximum()
        start, end = snap_timeline_range(
            self.asset_start.value(), self.asset_end.value(), duration
        )
        if end <= start:
            QMessageBox.warning(self, "Invalid range", "Asset end must be later than its start.")
            return
        before = timeline_state(asset)
        after = dict(before)
        after.update(start_seconds=start, end_seconds=end)
        self.undo_stack.push(
            AssetEditCommand(asset, before, after, self._refresh_after_asset_command, "Trim clip")
        )
        self._mark_render_states_dirty(before, after)
        self._mark_dirty()

    def apply_clip_properties(self) -> None:
        asset = self._selected_clip()
        if not asset:
            return
        source_in = self.asset_source_in.value()
        source_out = self.asset_source_out.value()
        if source_out > 0 and source_out <= source_in:
            QMessageBox.warning(self, "Invalid source range", "Source Out must be later than Source In, or zero for the media end.")
            return
        clip_duration = max(0.01, asset.end_seconds - asset.start_seconds)
        before = timeline_state(asset)
        after = dict(before)
        after.update(
            playback_speed=self.asset_speed.value(),
            source_in_seconds=source_in,
            source_out_seconds=source_out,
            fade_in_seconds=min(self.asset_fade_in.value(), clip_duration),
            fade_out_seconds=min(self.asset_fade_out.value(), clip_duration),
            transition_in=self.asset_transition_in.currentText(),
            transition_out=self.asset_transition_out.currentText(),
        )
        self.undo_stack.push(
            AssetEditCommand(asset, before, after, self._refresh_after_asset_command, "Edit clip properties")
        )
        self._mark_render_states_dirty(before, after)
        self._mark_dirty()

    def asset_timing_changed(self, asset: MediaAsset) -> None:
        if asset is self._selected_clip():
            self.asset_start.setValue(asset.start_seconds)
            self.asset_end.setValue(asset.end_seconds)
        self.refresh_activation()
        self.render_timeline_at(self.playhead_seconds, force_seek=False)

    def commit_asset_edit(self, asset: MediaAsset, before: dict, after: dict) -> None:
        if before == after:
            return
        self.undo_stack.push(
            AssetEditCommand(asset, before, after, self._refresh_after_asset_command, "Edit timeline clip")
        )
        self._mark_render_states_dirty(before, after)
        self._mark_dirty()

    def remove_timeline_asset(self, asset: MediaAsset) -> None:
        if not self.scan:
            return
        if asset in self.scan.timeline_clips:
            self.undo_stack.push(
                RemoveTimelineClipCommand(
                    self.scan.timeline_clips, asset, self._refresh_after_timeline_clip_list
                )
            )
            self._mark_render_states_dirty(timeline_state(asset))
            self._mark_dirty()
            return
        before = timeline_state(asset)
        after = dict(before)
        after["timeline_placed"] = False
        self.undo_stack.push(
            AssetEditCommand(asset, before, after, self._refresh_after_asset_command, "Remove clip from timeline")
        )
        self._mark_render_states_dirty(before)
        self._mark_dirty()

    def reject_empty_timeline_slot(self, asset: MediaAsset) -> None:
        self.select_asset(asset)
        self.statusBar().showMessage(
            f"{asset.tag} is empty — double-click the Media Pool card to load media before placing it on Timeline.",
            7000,
        )

    def _refresh_after_asset_command(self, asset: MediaAsset) -> None:
        self.timeline.schedule_rebuild()
        self.asset_timing_changed(asset)
        self._reconcile_asset_shot_reference_ranges(asset)
        self._sync_prompt_panel_from_timeline(reconcile_brief=True)
        card = self.cards.get(asset.node_id)
        if card:
            card.refresh_mode(asset.overlaps(self.clip_start.value(), self.clip_end.value()))
        if asset is self._selected_clip():
            self.select_timeline_asset(asset)
        else:
            self._refresh_recognition_inspector()
        self._maybe_auto_enrich(self._source_asset_for(asset))
        self.render_timeline_at(self.playhead_seconds, force_seek=True)

    def add_timeline_clip_instance(self, clip: MediaAsset) -> None:
        if not self.scan:
            return
        self.undo_stack.push(
            AddTimelineClipCommand(
                self.scan.timeline_clips, clip, self._refresh_after_timeline_clip_list
            )
        )
        self._mark_render_states_dirty(timeline_state(clip))
        self._mark_dirty()

    def _refresh_after_timeline_clip_list(self, clip: MediaAsset) -> None:
        if not self.scan:
            return
        if clip not in self.scan.timeline_clips and self.selected_timeline_asset is clip:
            self.selected_timeline_asset = None
            if self.selected_asset:
                self._show_asset_inspector(self.selected_asset, self.selected_asset)
        self.timeline.schedule_rebuild()
        self.refresh_activation()
        self._reconcile_asset_shot_reference_ranges(clip)
        self._sync_prompt_panel_from_timeline(reconcile_brief=True)
        self.render_timeline_at(self.playhead_seconds, force_seek=True)

    def refresh_activation(self) -> None:
        if not self.scan:
            return
        start, end = self.clip_start.value(), self.clip_end.value()
        if end <= start:
            return
        audio_solo = any(track.enabled and track.solo for track in self.tracks if track.kind == "audio")
        active_source_ids: set[str] = set()
        for asset in self.scan.timeline_assets():
            track = self._track_for_asset(asset)
            track_active = bool(track and track.enabled)
            if track and track.kind == "visual":
                track_active = track_active and track.visible
            if track and track.kind == "audio":
                track_active = track_active and not track.muted and (not audio_solo or track.solo)
            active = asset.overlaps(start, end) and track_active
            if active:
                active_source_ids.add(asset.source_node_id or asset.node_id)
        for source in self.scan.assets:
            card = self.cards.get(source.node_id)
            if card:
                card.refresh_mode(source.node_id in active_source_ids)

    def playhead_changed(self, seconds: float) -> None:
        self.seek_timeline(seconds)

    def _begin_timeline_slider_scrub(self) -> None:
        self.timeline_slider_scrubbing = True
        self.timeline_slider_was_playing = self.timeline_playing
        if self.timeline_playing:
            self.timeline_playing = False
            self.timeline_timer.stop()
            self.generated_player.pause()
            self.player.pause()
            for player in self.composite_video_players.values():
                player.pause()
            for player in self.timeline_audio_players.values():
                player.pause()
            self.play_button.setText("▶")

    def _preview_timeline_slider_scrub(self, milliseconds: int) -> None:
        if not self.scan:
            return
        seconds = min(
            self.scan.duration_seconds,
            max(0.0, int(milliseconds) / 1000.0),
        )
        self.timeline_slider_pending_seconds = seconds
        self.playhead_seconds = seconds
        self.timeline.set_playhead(seconds, snap_to_grid=False)
        exact_ms = round(seconds * 1000)
        self.time_label.setText(self._timecode(exact_ms))
        self.playhead_label.setText(f"PLAYHEAD {self._timecode(exact_ms)}")
        self.render_timeline_at(seconds, force_seek=False)
        # Video decoding is intentionally debounced; the slider and playhead
        # remain pixel-smooth while the monitor catches up after a short pause.
        self.timeline_slider_seek_timer.start()

    def _apply_timeline_slider_seek(self) -> None:
        if not self.timeline_slider_scrubbing or not self.scan:
            return
        seconds = self.timeline_slider_pending_seconds
        self.render_timeline_at(seconds, force_seek=True)
        self._sync_generated_player(seconds, force=True)

    def _end_timeline_slider_scrub(self) -> None:
        if not self.timeline_slider_scrubbing:
            return
        self.timeline_slider_seek_timer.stop()
        resume = self.timeline_slider_was_playing
        self.timeline_slider_scrubbing = False
        self.timeline_slider_was_playing = False
        self.seek_timeline(self.position_slider.value() / 1000.0)
        if resume:
            self.toggle_playback()

    @staticmethod
    def _timecode(milliseconds: float) -> str:
        total = int(milliseconds)
        minutes, remainder = divmod(total, 60000)
        seconds, ms = divmod(remainder, 1000)
        return f"{minutes:02d}:{seconds:02d}.{ms:03d}"

    def toggle_playback(self) -> None:
        generated_video = bool(
            self.generated_output_locked
            and not self.storyboard_preview_active
            and self.generated_output_path
            and media_type_for_path(self.generated_output_path) == "video"
        )
        if generated_video:
            if self.generated_proxy_runner and self.generated_proxy_runner.is_running():
                self.generated_proxy_autoplay_pending = (
                    not self.generated_proxy_autoplay_pending
                )
                self.play_button.setText(
                    "Ⅱ" if self.generated_proxy_autoplay_pending else "▶"
                )
                self.statusBar().showMessage(
                    "Monitor Proxy is being prepared · playback will start automatically"
                    if self.generated_proxy_autoplay_pending
                    else "Monitor Proxy is being prepared · autoplay cancelled"
                )
                return
            if self.timeline_playing or self.generated_player.playbackState() == QMediaPlayer.PlayingState:
                self.timeline_playing = False
                self.generated_player.pause()
                self.player.pause()
                for player in self.composite_video_players.values():
                    player.pause()
                for player in self.timeline_audio_players.values():
                    player.pause()
                self.play_button.setText("▶")
            else:
                if (
                    self.generated_player.duration() > 0
                    and self.generated_player.position() >= self.generated_player.duration() - 100
                ):
                    self.seek_timeline(self.generated_output_timeline_start)
                self.timeline_playing = True
                self.render_timeline_at(self.playhead_seconds, force_seek=True)
                self._sync_generated_player(self.playhead_seconds, force=True)
                self.generated_player.play()
                self.play_button.setText("Ⅱ")
            return
        if self.timeline_playing:
            self.timeline_playing = False
            self.timeline_timer.stop()
            self.player.pause()
            self.generated_player.pause()
            for player in self.composite_video_players.values():
                player.pause()
            for player in self.timeline_audio_players.values():
                player.pause()
            self.play_button.setText("▶")
            self.render_timeline_at(self.playhead_seconds, force_seek=True)
            return
        if not self.scan:
            return
        if self.playhead_seconds >= self.scan.duration_seconds - 0.01:
            self.seek_timeline(0.0)
        self.timeline_playing = True
        self.playback_anchor_seconds = self.playhead_seconds
        self.playback_anchor_time = time.monotonic()
        self.play_button.setText("Ⅱ")
        self.render_timeline_at(self.playhead_seconds, force_seek=True)
        self._sync_generated_player(self.playhead_seconds, force=True)
        self.timeline_timer.start()

    def seek_timeline(self, seconds: float) -> None:
        if not self.scan:
            return
        self.playhead_seconds = min(self.scan.duration_seconds, max(0.0, float(seconds)))
        self.timeline.set_playhead(self.playhead_seconds)
        milliseconds = round(self.playhead_seconds * 1000)
        self.position_slider.setValue(milliseconds)
        self.time_label.setText(self._timecode(milliseconds))
        self.playhead_label.setText(f"PLAYHEAD {self._timecode(milliseconds)}")
        if self.timeline_playing:
            self.playback_anchor_seconds = self.playhead_seconds
            self.playback_anchor_time = time.monotonic()
        self.render_timeline_at(self.playhead_seconds, force_seek=True)
        self._sync_generated_player(self.playhead_seconds, force=True)

    def _timeline_tick(self) -> None:
        if not self.timeline_playing or not self.scan:
            return
        seconds = self.playback_anchor_seconds + (time.monotonic() - self.playback_anchor_time)
        if seconds >= self.scan.duration_seconds:
            self.timeline_playing = False
            self.timeline_timer.stop()
            self.seek_timeline(self.scan.duration_seconds)
            self.player.pause()
            self.generated_player.pause()
            for player in self.composite_video_players.values():
                player.pause()
            for player in self.timeline_audio_players.values():
                player.pause()
            self.play_button.setText("▶")
            return
        self.playhead_seconds = seconds
        self.timeline.set_playhead(seconds)
        milliseconds = round(seconds * 1000)
        self.position_slider.setValue(milliseconds)
        self.time_label.setText(self._timecode(milliseconds))
        self.playhead_label.setText(f"PLAYHEAD {self._timecode(milliseconds)}")
        self.render_timeline_at(seconds, force_seek=False)

    def _sync_generated_player(self, seconds: float, *, force: bool) -> None:
        if (
            not self.generated_output_locked
            or not self.generated_output_path
            or media_type_for_path(self.generated_output_path) != "video"
        ):
            return
        desired_ms = max(
            0,
            round((float(seconds) - self.generated_output_timeline_start) * 1000),
        )
        duration = self.generated_player.duration()
        if duration > 0:
            desired_ms = min(duration, desired_ms)
        self.generated_pending_position_ms = desired_ms
        if force or abs(self.generated_player.position() - desired_ms) > 180:
            self._syncing_generated_position = True
            self.generated_player.setPosition(desired_ms)
            self._syncing_generated_position = False

    def _generated_position_changed(self, position_ms: int) -> None:
        if (
            self._syncing_generated_position
            or not self.generated_output_locked
            or not self.scan
            or self.timeline_slider_scrubbing
            or self.position_slider.isSliderDown()
        ):
            return
        seconds = self.generated_output_timeline_start + max(0, position_ms) / 1000.0
        seconds = min(self.scan.duration_seconds, max(0.0, seconds))
        self.generated_pending_position_ms = max(0, int(position_ms))
        self.playhead_seconds = seconds
        self.timeline.set_playhead(seconds)
        timeline_ms = round(seconds * 1000)
        self.position_slider.setValue(timeline_ms)
        self.time_label.setText(self._timecode(timeline_ms))
        self.playhead_label.setText(f"PLAYHEAD {self._timecode(timeline_ms)}")
        self.render_timeline_at(seconds, force_seek=False)

    def _track_for_asset(self, asset: MediaAsset) -> TimelineTrack | None:
        wanted = "audio" if asset.media_type == "audio" else "visual"
        for track in self.tracks:
            if track.track_id == asset.timeline_track_id and track.kind == wanted:
                return track
        if 0 <= asset.timeline_lane < len(self.tracks):
            candidate = self.tracks[asset.timeline_lane]
            if candidate.kind == wanted:
                return candidate
        return next((track for track in self.tracks if track.kind == wanted), None)

    def _source_position_ms(self, asset: MediaAsset, seconds: float) -> int:
        elapsed = max(0.0, seconds - asset.start_seconds)
        source_seconds = asset.source_in_seconds + elapsed * max(0.1, asset.playback_speed)
        if asset.source_out_seconds > asset.source_in_seconds:
            source_seconds = min(source_seconds, asset.source_out_seconds)
        return max(0, round(source_seconds * 1000))

    @staticmethod
    def _clip_runtime_key(asset: MediaAsset) -> str:
        return asset.clip_id or asset.node_id

    @staticmethod
    def _clip_envelope(asset: MediaAsset, seconds: float) -> float:
        elapsed = max(0.0, seconds - asset.start_seconds)
        remaining = max(0.0, asset.end_seconds - seconds)
        opacity = 1.0
        if asset.fade_in_seconds > 0:
            opacity = min(opacity, elapsed / asset.fade_in_seconds)
        if asset.fade_out_seconds > 0:
            opacity = min(opacity, remaining / asset.fade_out_seconds)
        transition_seconds = min(0.5, max(0.1, (asset.end_seconds - asset.start_seconds) / 2))
        if asset.transition_in != "None":
            opacity = min(opacity, elapsed / transition_seconds)
        if asset.transition_out != "None":
            opacity = min(opacity, remaining / transition_seconds)
        return max(0.0, min(1.0, opacity))

    def _assets_at_playhead(self, seconds: float) -> tuple[list[MediaAsset], list[MediaAsset]]:
        if not self.scan:
            return [], []
        lookup_seconds = min(
            max(0.0, float(seconds)),
            max(0.0, self.scan.duration_seconds - 0.001),
        )
        present = [
            asset
            for asset in self.scan.timeline_assets()
            if asset.timeline_placed
            and asset.activation_mode != "bypass"
            and asset.start_seconds <= lookup_seconds < asset.end_seconds
        ]
        indexed_tracks = {track.track_id: index for index, track in enumerate(self.tracks)}
        visuals = sorted(
            (
                asset
                for asset in present
                if asset.media_type in ("image", "video")
                and asset.monitor_visible
                and (track := self._track_for_asset(asset)) is not None
                and track.enabled
                and track.visible
            ),
            key=lambda asset: (indexed_tracks.get(asset.timeline_track_id, asset.timeline_lane), -asset.start_seconds),
        )
        audio_candidates = [
            asset
            for asset in present
            if asset.media_type == "audio"
            and (track := self._track_for_asset(asset)) is not None
            and track.enabled
            and not track.muted
        ]
        solo_active = any(
            track.enabled and track.solo for track in self.tracks if track.kind == "audio"
        )
        audios = [
            asset
            for asset in audio_candidates
            if not solo_active or bool(self._track_for_asset(asset) and self._track_for_asset(asset).solo)
        ]
        return visuals, audios

    def _reference_visual_at_playhead(self, seconds: float) -> MediaAsset | None:
        """Provide a Source Monitor fallback without activating H3 references."""
        if not self.scan:
            return None
        lookup_seconds = min(
            max(0.0, float(seconds)),
            max(0.0, self.scan.duration_seconds - 0.001),
        )

        def eligible(asset: MediaAsset | None) -> bool:
            if asset is None:
                return False
            track = self._track_for_asset(asset)
            return bool(
                asset.timeline_placed
                and asset.activation_mode != "bypass"
                and asset.media_type in {"image", "video"}
                and asset.local_path
                and Path(asset.local_path).is_file()
                and asset.start_seconds <= lookup_seconds < asset.end_seconds
                and track is not None
                and track.enabled
                and track.visible
            )

        if eligible(self.selected_timeline_asset):
            return self.selected_timeline_asset
        if eligible(self.selected_asset):
            return self.selected_asset
        return next((asset for asset in self.scan.timeline_assets() if eligible(asset)), None)

    def _compositor_required(self, visuals: list[MediaAsset]) -> bool:
        if len(visuals) > 1:
            return True
        for asset in visuals:
            track = self._track_for_asset(asset)
            if (
                track
                and (track.opacity < 0.999 or track.blend_mode != "Normal")
                or asset.fade_in_seconds > 0
                or asset.fade_out_seconds > 0
                or asset.transition_in != "None"
                or asset.transition_out != "None"
            ):
                return True
        return False

    @staticmethod
    def _composition_mode(name: str):
        return {
            "Multiply": QPainter.CompositionMode_Multiply,
            "Screen": QPainter.CompositionMode_Screen,
            "Overlay": QPainter.CompositionMode_Overlay,
            "Additive": QPainter.CompositionMode_Plus,
            "Difference": QPainter.CompositionMode_Difference,
        }.get(name, QPainter.CompositionMode_SourceOver)

    def _composite_frame_changed(self, clip_key: str, frame) -> None:
        image = frame.toImage()
        if not image.isNull():
            self.composite_video_frames[clip_key] = image.copy()
            if any(self._clip_runtime_key(asset) == clip_key for asset in self.composite_visuals):
                self._render_visual_composite(self.composite_visuals, self.playhead_seconds)

    def _sync_composite_video_players(
        self,
        visuals: list[MediaAsset],
        seconds: float,
        force_seek: bool,
    ) -> None:
        active_ids = {
            self._clip_runtime_key(asset)
            for asset in visuals
            if asset.media_type == "video" and asset.local_path
        }
        for node_id, player in self.composite_video_players.items():
            if node_id not in active_ids:
                player.stop()
        for asset in visuals:
            if asset.media_type != "video" or not asset.local_path:
                continue
            clip_key = self._clip_runtime_key(asset)
            player = self.composite_video_players.get(clip_key)
            if player is None:
                sink = QVideoSink(self)
                sink.videoFrameChanged.connect(
                    lambda frame, key=clip_key: self._composite_frame_changed(key, frame)
                )
                player = QMediaPlayer(self)
                player.setVideoOutput(sink)
                self.composite_video_sinks[clip_key] = sink
                self.composite_video_players[clip_key] = player
            desired_ms = self._source_position_ms(asset, seconds)
            player.setPlaybackRate(asset.playback_speed)
            if player.source().toLocalFile() != asset.local_path:
                player.setSource(QUrl.fromLocalFile(asset.local_path))
                player.setPosition(desired_ms)
            elif force_seek or abs(player.position() - desired_ms) > 450:
                player.setPosition(desired_ms)
            source_has_time = player.duration() <= 0 or desired_ms < player.duration() - 20
            if self.timeline_playing and source_has_time:
                player.play()
            else:
                player.pause()

    def _layer_image(self, asset: MediaAsset) -> QImage:
        if asset.media_type == "video":
            frame = self.composite_video_frames.get(self._clip_runtime_key(asset))
            if frame is not None and not frame.isNull():
                return frame
        preview = self.preview_paths.get(asset.node_id)
        if preview and preview.is_file():
            return QImage(str(preview))
        if asset.local_path and Path(asset.local_path).is_file():
            return QImage(asset.local_path)
        return QImage()

    def _render_visual_composite(self, visuals: list[MediaAsset], seconds: float) -> None:
        width = max(640, self.monitor_image.width())
        height = max(360, self.monitor_image.height())
        canvas = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        canvas.fill(QColor("black"))
        painter = QPainter(canvas)
        for asset in reversed(visuals):
            track = self._track_for_asset(asset)
            if not track:
                continue
            image = self._layer_image(asset)
            if image.isNull():
                continue
            scaled = image.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (width - scaled.width()) // 2
            y = (height - scaled.height()) // 2
            envelope = self._clip_envelope(asset, seconds)
            painter.setOpacity(max(0.0, min(1.0, track.opacity * envelope)))
            painter.setCompositionMode(self._composition_mode(track.blend_mode))
            if asset.transition_in == "Wipe" or asset.transition_out == "Wipe":
                painter.save()
                painter.setClipRect(x, y, round(scaled.width() * envelope), scaled.height())
                painter.drawImage(x, y, scaled)
                painter.restore()
            else:
                painter.drawImage(x, y, scaled)
        painter.end()
        self.monitor_stack.setCurrentWidget(self.monitor_image)
        self._show_monitor_pixmap(QPixmap.fromImage(canvas))

    def render_timeline_at(self, seconds: float, force_seek: bool = False) -> None:
        if not hasattr(self, "monitor_stack"):
            return
        visuals, audios = self._assets_at_playhead(seconds)
        if not visuals:
            reference_visual = self._reference_visual_at_playhead(seconds)
            if reference_visual is not None:
                visuals = [reference_visual]
        visual = visuals[0] if visuals else None
        using_compositor = bool(visuals) and self._compositor_required(visuals)
        if using_compositor:
            if self.player.playbackState() != QMediaPlayer.StoppedState:
                self.player.stop()
            self.current_visual_node = ""
            self.composite_visuals = list(visuals)
            self._sync_composite_video_players(visuals, seconds, force_seek)
            self._render_visual_composite(visuals, seconds)
        elif visual and visual.media_type == "video" and visual.local_path:
            self.composite_visuals = []
            for player in self.composite_video_players.values():
                player.stop()
            desired_ms = self._source_position_ms(visual, seconds)
            source_changed = (
                self.current_visual_node != self._clip_runtime_key(visual)
                or self.player.source().toLocalFile() != visual.local_path
            )
            self.pending_video_position_ms = desired_ms
            self.player.setPlaybackRate(visual.playback_speed)
            if source_changed:
                self.current_visual_node = self._clip_runtime_key(visual)
                self.player.stop()
                self.player.setSource(QUrl.fromLocalFile(visual.local_path))
                self.player.setPosition(desired_ms)
            elif force_seek or abs(self.player.position() - desired_ms) > 450:
                self.player.setPosition(desired_ms)
            self.monitor_stack.setCurrentWidget(self.video_widget)
            source_has_time = self.player.duration() <= 0 or desired_ms < self.player.duration() - 20
            if self.timeline_playing and source_has_time:
                self.player.play()
            else:
                self.player.pause()
        else:
            self.composite_visuals = []
            for player in self.composite_video_players.values():
                player.stop()
            if self.current_visual_node and self.player.playbackState() != QMediaPlayer.StoppedState:
                self.player.stop()
            visual_key = self._clip_runtime_key(visual) if visual else ""
            source_changed = self.current_visual_node != visual_key
            self.current_visual_node = visual_key
            self.monitor_stack.setCurrentWidget(self.monitor_image)
            if visual:
                if source_changed or force_seek or self.monitor_image.pixmap().isNull():
                    preview = self.preview_paths.get(visual.node_id)
                    display_path = (
                        preview
                        if preview and preview.exists()
                        else Path(visual.local_path)
                        if visual.local_path and Path(visual.local_path).is_file()
                        else None
                    )
                    if display_path:
                        cache_key = f"{visual.node_id}|{display_path}"
                        pixmap = self.monitor_source_pixmaps.get(cache_key)
                        if pixmap is None:
                            pixmap = QPixmap(str(display_path))
                            self.monitor_source_pixmaps[cache_key] = pixmap
                        self._show_monitor_pixmap(pixmap)
                    else:
                        self.monitor_image.clear()
                        self.monitor_image.setText(f"{visual.tag}\nMedia is referenced by the API but is not available locally for live preview.")
            else:
                self.monitor_image.clear()
                self.monitor_image.setText("No visual clip at the Timeline playhead")
        self._update_text_overlay(seconds)
        supplemental_audio = list(audios)
        supplemental_audio.extend(
            asset
            for asset in visuals
            if asset.media_type == "video"
            and asset.paired_audio_binding
            and (using_compositor or visual is None or asset.node_id != visual.node_id)
        )
        if (
            self.generated_output_locked
            and not self.storyboard_preview_active
            and self.generated_output_path
            and media_type_for_path(self.generated_output_path) == "video"
        ):
            for player in self.timeline_audio_players.values():
                player.pause()
        else:
            self._sync_timeline_audio(supplemental_audio, seconds, force_seek)

    def _update_text_overlay(self, seconds: float) -> None:
        active: list[TextLayer] = []
        for layer in self.text_layers:
            track = next((item for item in self.tracks if item.track_id == layer.track_id), None)
            if (
                layer.start_seconds <= seconds < layer.end_seconds
                and layer.content_role == "on_screen_text"
                and track is not None
                and track.kind == "visual"
                and track.enabled
                and track.visible
            ):
                active.append(layer)
        active_ids = {layer.layer_id for layer in active}
        for layer_id, label in self.monitor_text_labels.items():
            if layer_id not in active_ids:
                label.hide()
        track_order = {track.track_id: index for index, track in enumerate(self.tracks)}
        active.sort(key=lambda layer: track_order.get(layer.track_id, 999), reverse=True)
        monitor_width = max(1, self.monitor_stack.width())
        monitor_height = max(1, self.monitor_stack.height())
        for layer in active:
            label = self.monitor_text_labels.get(layer.layer_id)
            if label is None:
                label = MonitorTextLabel(layer, self.commit_monitor_text_position, self.monitor_stack)
                self.monitor_text_labels[layer.layer_id] = label
            label.layer = layer
            label.setText(layer.text)
            label.setStyleSheet(
                f"background:transparent; color:{layer.color}; font-size:{layer.font_size}px; "
                "font-weight:600; padding:5px; border:1px solid transparent; "
                "selection-background-color:#1688a2;"
            )
            label.setMaximumWidth(max(80, monitor_width - 20))
            label.adjustSize()
            width = min(max(80, label.width()), max(80, monitor_width - 20))
            height = min(max(36, label.height()), max(36, monitor_height - 20))
            x = round(layer.position_x * monitor_width - width / 2)
            y = round(layer.position_y * monitor_height - height / 2)
            x = max(0, min(monitor_width - width, x))
            y = max(0, min(monitor_height - height, y))
            label.setGeometry(x, y, width, height)
            label.set_selection_enabled(self.timeline.tool_mode == "selection")
            label.show()
            label.raise_()

    def commit_monitor_text_position(self, layer: TextLayer, before: dict, after: dict) -> None:
        if before == after:
            return
        self.undo_stack.push(
            TextLayerEditCommand(
                layer,
                before,
                after,
                self._refresh_text_layers,
                "Move Program Monitor text",
            )
        )
        self._mark_render_states_dirty(before, after)
        self._mark_dirty()
        self.statusBar().showMessage(
            f"Moved {layer.layer_id} to {layer.position_x:.0%}, {layer.position_y:.0%}"
        )

    def _audio_playback_source(self, asset: MediaAsset, track: TimelineTrack | None) -> str:
        if not track or track.kind != "audio" or abs(track.pan) < 0.001:
            return asset.local_path
        key = self._audio_pan_key(asset, track)
        proxy = self.audio_pan_proxies.get(key)
        if proxy and proxy.is_file():
            return str(proxy)
        QTimer.singleShot(0, lambda item=asset, lane=track: self.queue_audio_pan_proxy(item, lane))
        return asset.local_path

    def _sync_timeline_audio(self, audios: list[MediaAsset], seconds: float, force_seek: bool) -> None:
        active_ids = {self._clip_runtime_key(asset) for asset in audios if asset.local_path}
        for clip_key, player in self.timeline_audio_players.items():
            if clip_key not in active_ids:
                player.stop()
        for asset in audios:
            if not asset.local_path:
                continue
            clip_key = self._clip_runtime_key(asset)
            player = self.timeline_audio_players.get(clip_key)
            if player is None:
                output = QAudioOutput(self)
                player = QMediaPlayer(self)
                player.setAudioOutput(output)
                player.mediaStatusChanged.connect(
                    lambda status, key=clip_key: self._audio_media_status_changed(key, status)
                )
                self.timeline_audio_outputs[clip_key] = output
                self.timeline_audio_players[clip_key] = player
            output = self.timeline_audio_outputs[clip_key]
            track = self._track_for_asset(asset)
            track_volume = track.volume if track and track.kind == "audio" else 1.0
            output.setVolume(max(0.0, min(1.0, track_volume * self._clip_envelope(asset, seconds))))
            desired_ms = self._source_position_ms(asset, seconds)
            self.pending_audio_positions[clip_key] = desired_ms
            player.setPlaybackRate(asset.playback_speed)
            playback_source = self._audio_playback_source(asset, track)
            if player.source().toLocalFile() != playback_source:
                player.setSource(QUrl.fromLocalFile(playback_source))
                player.setPosition(desired_ms)
            elif force_seek or abs(player.position() - desired_ms) > 450:
                player.setPosition(desired_ms)
            source_has_time = player.duration() <= 0 or desired_ms < player.duration() - 20
            if self.timeline_playing and source_has_time:
                player.play()
            else:
                player.pause()

    def _video_media_status_changed(self, status) -> None:
        if status in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia):
            self.player.setPosition(self.pending_video_position_ms)
            if self.timeline_playing and self.pending_video_position_ms < self.player.duration() - 20:
                self.player.play()

    def _generated_media_status_changed(self, status) -> None:
        if status == QMediaPlayer.EndOfMedia:
            self.timeline_playing = False
            self.generated_player.pause()
            self.player.pause()
            for player in self.composite_video_players.values():
                player.pause()
            for player in self.timeline_audio_players.values():
                player.pause()
            if self.generated_player.duration() > 0:
                self._generated_position_changed(self.generated_player.duration())
            self.play_button.setText("▶")
            return
        if status in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia):
            # Setting the same position on every Loaded/Buffered transition
            # creates an endless Media Foundation buffer/seek loop. Only apply
            # the pending seek when the backend is materially out of sync.
            if (
                abs(
                    self.generated_player.position()
                    - self.generated_pending_position_ms
                )
                > 120
            ):
                self._syncing_generated_position = True
                self.generated_player.setPosition(self.generated_pending_position_ms)
                self._syncing_generated_position = False
            if self.timeline_playing:
                self.generated_player.play()

    def _audio_media_status_changed(self, clip_key: str, status) -> None:
        if status not in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia):
            return
        player = self.timeline_audio_players.get(clip_key)
        if not player:
            return
        player.setPosition(self.pending_audio_positions.get(clip_key, 0))
        if self.timeline_playing and self.pending_audio_positions.get(clip_key, 0) < player.duration() - 20:
            player.play()

    def _stop_all_timeline_media(self) -> None:
        self.timeline_playing = False
        self.timeline_timer.stop()
        self.player.stop()
        self.generated_player.pause()
        for player in self.composite_video_players.values():
            player.stop()
        for player in self.timeline_audio_players.values():
            player.stop()
        self.current_visual_node = ""
        self.composite_visuals = []
        if hasattr(self, "play_button"):
            self.play_button.setText("▶")

    def recognize_selected(self) -> None:
        if not self.selected_asset:
            return
        asset = self.selected_asset
        # A new base-analysis pass invalidates any response currently being
        # generated from the previous evidence. Late payloads are ignored.
        removed_semantic = False
        for job_id, job in list(self.semantic_jobs.items()):
            if job.get("asset") is asset:
                self.semantic_jobs.pop(job_id, None)
                removed_semantic = True
        if removed_semantic and not self.semantic_jobs:
            # Let an already accepted request finish in the crash-isolated
            # worker; its missing job id makes the late result harmless.
            self.semantic_runner.discard_pending()
        self.semantic_errors.pop(asset.node_id, None)
        if asset.media_type in ("image", "video"):
            self.start_blip(asset)
        if asset.media_type in ("video", "audio"):
            self.start_audio_analysis(asset)
        self._refresh_recognition_inspector(asset)

    def _watch_worker_health(self) -> None:
        """Terminate a worker that never becomes ready or stops reporting progress."""
        if self._closing:
            return
        now = time.monotonic()
        timeline_seconds = self.scan.duration_seconds if self.scan else 60.0
        workers = [
            ("media", self.media_runner, bool(self.media_jobs), 180.0),
            ("blip", self.blip_runner, bool(self.blip_jobs), 300.0),
            ("audio", self.audio_runner, bool(self.audio_jobs), max(300.0, timeline_seconds * 20.0)),
            (
                "semantic",
                self.semantic_runner,
                bool(self.semantic_jobs) or bool(self.semantic_unload_job_id),
                max(120.0, float(load_design_settings(DESIGN_SETTINGS_ENV).timeout) + 60.0),
            ),
        ]
        if self.media_regeneration_runner is not None:
            workers.append(
                (
                    "z-image-regeneration",
                    self.media_regeneration_runner,
                    bool(self.pending_media_regeneration),
                    max(300.0, float(self.render_settings.generation_timeout) + 60.0),
                )
            )
        for name, runner, has_jobs, running_timeout in workers:
            if not has_jobs or not runner.is_running():
                continue
            elapsed = now - runner.started_monotonic
            silent = now - runner.last_output_monotonic
            startup_timed_out = not runner.is_ready() and elapsed > 90.0
            job_timed_out = runner.is_ready() and silent > running_timeout
            key = (name, runner.generation)
            if (startup_timed_out or job_timed_out) and key not in self._timed_out_generations:
                self._timed_out_generations.add(key)
                reason = "startup timeout" if startup_timed_out else "job timeout"
                self.statusBar().showMessage(f"{name} worker {reason}; terminating safely")
                runner.terminate_now()

    def cancel_selected_analysis(self) -> None:
        asset = self.selected_asset
        if not asset:
            return
        removed = False
        base_removed = False
        for runner, jobs in (
            (self.media_runner, self.media_jobs),
            (self.blip_runner, self.blip_jobs),
            (self.audio_runner, self.audio_jobs),
        ):
            removed_here = False
            for job_id, job in list(jobs.items()):
                job_asset = job.get("asset") if isinstance(job, dict) else job[0] if isinstance(job, tuple) else job
                if job_asset is asset:
                    jobs.pop(job_id, None)
                    removed = True
                    base_removed = True
                    removed_here = True
            if removed_here and not jobs:
                runner.discard_pending()
                runner.terminate_now()
        semantic_removed = False
        for job_id, job in list(self.semantic_jobs.items()):
            if job.get("asset") is asset:
                self.semantic_last_lm_request = dict(job)
                self.semantic_jobs.pop(job_id, None)
                removed = True
                semantic_removed = True
        if semantic_removed and not self.semantic_jobs:
            # Remove requests that have not reached the worker. An accepted
            # request may finish later, but its result has no matching job id.
            self.semantic_runner.discard_pending()
        if asset.node_id in self.semantic_waiting_assets:
            self.semantic_waiting_assets.discard(asset.node_id)
            removed = True
        if removed:
            if base_removed:
                self.blip_results.pop(asset.node_id, None)
                asset.recognition += "\n\nAnalysis cancelled. Any late worker response will be ignored."
            card = self.cards.get(asset.node_id)
            if card:
                card.set_analysis_status("已取消")
            self._refresh_recognition_inspector(asset)
            self.statusBar().showMessage(f"Cancelled analysis for {asset.tag}")

        if semantic_removed:
            QTimer.singleShot(0, self._maybe_request_semantic_lm_unload)

    def start_blip(self, asset: MediaAsset) -> None:
        sources = self.analysis_paths.get(asset.node_id, [])
        if not sources:
            self._mark_analysis_failure(asset, "BLIP cannot start until media preparation finishes.")
            return
        for job_id, job in list(self.blip_jobs.items()):
            if job[0] is asset:
                self.blip_jobs.pop(job_id, None)
        self.blip_results[asset.node_id] = []
        try:
            if not self.blip_runner.is_running():
                arguments = [
                    str(PROJECT_ROOT / "blip_service.py"),
                    "--model",
                    str(self.runtime.blip_snapshot),
                ]
                configured_device = self.render_settings.blip_device
                if self.blip_cpu_mode or configured_device == "cpu":
                    arguments.append("--cpu")
                elif configured_device == "auto":
                    arguments.append("--auto")
                if not self.blip_runner.start(str(self.runtime.python), arguments):
                    raise RuntimeError("BLIP service is still stopping")
            card = self.cards.get(asset.node_id)
            if card:
                card.set_analysis_status("识别 0%")
            requests: list[tuple[str, Path, str]] = []
            for label, source in sources:
                if asset.media_type == "image" and label != "full frame":
                    lowered = label.casefold()
                    if "subject detail" in lowered:
                        prompt = "the central subject is"
                    elif "upper scene" in lowered:
                        prompt = "the scene shows"
                    else:
                        prompt = "the lighting and environment show"
                    requests.append((label, source, prompt))
                else:
                    requests.append((label, source, ""))
            for label, source, prompt in requests:
                digest = hashlib.sha1(
                    (str(source) + label + prompt + str(time.time_ns())).encode()
                ).hexdigest()[:12]
                job_id = f"blip:{asset.node_id}:{digest}"
                self.blip_jobs[job_id] = (asset, label, source, prompt)
                request = {"job": job_id, "image": str(source)}
                if prompt:
                    request["prompt"] = prompt
                self.blip_runner.write_json(request)
        except Exception as exc:
            for job_id, job in list(self.blip_jobs.items()):
                if job[0] is asset:
                    self.blip_jobs.pop(job_id, None)
            self._mark_analysis_failure(asset, f"BLIP could not start: {exc}")

    def _handle_blip_payload(self, payload: dict) -> None:
        if payload.get("ready"):
            if payload.get("fallback_from") == "cuda":
                self.blip_cpu_mode = True
                self.blip_cpu_fallback_attempted = True
                self.statusBar().showMessage(
                    "BLIP CUDA is incompatible with this GPU/Torch build; "
                    "the same analysis is continuing on CPU"
                )
            else:
                self.statusBar().showMessage(
                    f"BLIP recognition ready on {payload.get('device', '-')}"
                )
            return
        if payload.get("fatal"):
            self.statusBar().showMessage(f"BLIP startup failed: {payload.get('error', 'unknown error')}")
            return
        job = self.blip_jobs.pop(payload.get("job", ""), None)
        if job:
            self._apply_blip_result(job[0], job[1], job[3], payload)

    @staticmethod
    def _blip_display_label(frame_label: str, media_type: str) -> str:
        lowered = frame_label.casefold()
        if frame_label == "full frame":
            return "Overview"
        if media_type == "video":
            return f"Frame {frame_label}"
        if "subject detail" in lowered:
            return "Subject detail"
        if "upper scene" in lowered:
            return "Upper scene"
        if "central scene" in lowered:
            return "Scene context"
        return frame_label

    def _apply_blip_result(
        self,
        asset: MediaAsset,
        frame_label: str,
        prompt: str,
        payload: dict,
    ) -> None:
        if not asset:
            return
        results = self.blip_results.setdefault(asset.node_id, [])
        if payload.get("caption"):
            results.append({
                "label": self._blip_display_label(frame_label, asset.media_type),
                "caption": clean_blip_caption(payload["caption"], prompt),
                "device": str(payload.get("device", "")),
                "error": "",
            })
        else:
            error = payload.get("error") or "BLIP returned no caption"
            results.append({
                "label": self._blip_display_label(frame_label, asset.media_type),
                "caption": "",
                "device": str(payload.get("device", "")),
                "error": str(error),
            })
        pending = any(item[0] is asset for item in self.blip_jobs.values())
        card = self.cards.get(asset.node_id)
        if pending:
            if card:
                card.set_analysis_status("识别 …")
            return
        summary = render_blip_summary(
            (
                (item["label"], item["caption"])
                for item in results
                if item["caption"]
            ),
            (item["device"] for item in results if item["device"]),
            (item["error"] for item in results if item["error"]),
        )
        base = remove_previous_blip_output(asset.recognition)
        asset.recognition = f"{base}\n\n{summary}".strip()
        self.blip_results.pop(asset.node_id, None)
        if self.blip_restart_after_jobs and not self.blip_jobs:
            self.blip_restart_after_jobs = False
            self.blip_runner.stop()
        self._sync_timeline_clip_sources(asset)
        if not self.project_path and not self.media_jobs and not self.blip_jobs:
            first_picture = self._first_loaded_picture()
            overview_name = picture_overview_project_name(
                first_picture.recognition if first_picture is not None else ""
            )
            if overview_name:
                self._ensure_project_workspace(overview_name)
        self._mark_dirty()
        self.schedule_prompt_generation()
        if card:
            card.set_analysis_status("识别 ✓" if "BLIP VISUAL SUMMARY" in summary else "识别 !")
        if asset is self.selected_asset:
            self._refresh_recognition_inspector(asset)
        self._maybe_auto_enrich(asset)
        self._maybe_request_semantic_lm_unload()

    def _blip_service_finished(self, exit_code: int, log: str) -> None:
        if self._closing:
            self.blip_jobs.clear()
            self.blip_results.clear()
            return
        pending_jobs = list(self.blip_jobs.items())
        if pending_jobs and exit_code != 0 and not self.blip_cpu_fallback_attempted:
            self.blip_cpu_fallback_attempted = True
            self.blip_cpu_mode = True
            self.blip_runner.discard_pending()
            try:
                self.blip_runner.start(
                    str(self.runtime.python),
                    [
                        str(PROJECT_ROOT / "blip_service.py"),
                        "--model",
                        str(self.runtime.blip_snapshot),
                        "--cpu",
                    ],
                )
                for job_id, (_asset, _label, source, prompt) in pending_jobs:
                    request = {"job": job_id, "image": str(source)}
                    if prompt:
                        request["prompt"] = prompt
                    self.blip_runner.write_json(request)
                self.statusBar().showMessage("BLIP GPU failed; retrying pending frames on CPU")
                return
            except Exception as exc:
                log = f"{log}\nCPU fallback failed: {exc}".strip()
        seen: set[int] = set()
        affected_assets: list[MediaAsset] = []
        for asset, _label, _source, _prompt in self.blip_jobs.values():
            if id(asset) in seen:
                continue
            seen.add(id(asset))
            affected_assets.append(asset)
            card = self.cards.get(asset.node_id)
            if card:
                card.set_analysis_status("识别 !")
        self.blip_jobs.clear()
        for asset in affected_assets:
            results = self.blip_results.pop(asset.node_id, [])
            results.append({
                "label": "Analysis",
                "caption": "",
                "device": "",
                "error": (
                    f"BLIP service stopped unexpectedly (exit {exit_code})"
                    + (f": {log[-300:]}" if log else "")
                ),
            })
            base = remove_previous_blip_output(asset.recognition)
            summary = render_blip_summary(
                ((item["label"], item["caption"]) for item in results if item["caption"]),
                (item["device"] for item in results if item["device"]),
                (item["error"] for item in results if item["error"]),
            )
            asset.recognition = f"{base}\n\n{summary}".strip()
        self.blip_runner.discard_pending()
        for asset in affected_assets:
            self._maybe_auto_enrich(asset)
        self._maybe_request_semantic_lm_unload()

    def start_audio_analysis(self, asset: MediaAsset) -> None:
        if not asset.local_path:
            return
        for job_id, job_asset in list(self.audio_jobs.items()):
            if job_asset is asset:
                self.audio_jobs.pop(job_id, None)
        try:
            if not self.audio_runner.is_running():
                if not self.audio_runner.start(
                    str(self.runtime.python),
                    [
                        str(PROJECT_ROOT / "audio_service.py"),
                        "--model",
                        str(self.runtime.speech_model),
                        "--ffmpeg",
                        str(self.runtime.ffmpeg),
                    ],
                ):
                    raise RuntimeError("Audio service is still stopping")
            job_id = f"audio:{asset.node_id}:{time.time_ns()}"
            self.audio_jobs[job_id] = asset
            timeline_seconds = self.scan.duration_seconds if self.scan else 60.0
            self.audio_runner.write_json(
                {
                    "job": job_id,
                    "media": asset.local_path,
                    "chunk_seconds": 8.0,
                    "max_seconds": timeline_seconds,
                }
            )
            card = self.cards.get(asset.node_id)
            if card:
                card.set_analysis_status("音频 0%")
        except Exception as exc:
            for job_id, job_asset in list(self.audio_jobs.items()):
                if job_asset is asset:
                    self.audio_jobs.pop(job_id, None)
            self._mark_analysis_failure(asset, f"Audio analysis could not start: {exc}")

    def _handle_audio_payload(self, payload: dict) -> None:
        if payload.get("ready"):
            self.statusBar().showMessage("Beat and VAD engine ready")
            return
        if payload.get("speech_ready"):
            self.statusBar().showMessage(f"Whisper speech recognition ready on {payload.get('device', '-')}")
            return
        if payload.get("fatal"):
            self.statusBar().showMessage(f"Audio service startup failed: {payload.get('error', 'unknown error')}")
            return
        qc_context = self.native_audio_qc_jobs.get(payload.get("job", ""))
        if qc_context is not None:
            if "progress" in payload and not payload.get("error"):
                percent = max(0, min(99, round(float(payload["progress"]) * 100)))
                self.statusBar().showMessage(f"Native Audio QC · {percent}%")
                return
            self.native_audio_qc_jobs.pop(payload.get("job", ""), None)
            if payload.get("error"):
                message = f"Native Audio QC ERROR · {payload['error']}"
            else:
                result = evaluate_native_audio_qc(
                    list(qc_context.get("expected_dialogue", [])),
                    str(payload.get("transcript", "")),
                    dict(payload.get("vad") or {}),
                    dict(payload.get("ambient") or {}),
                )
                message = str(result["message"])
            range_start = float(qc_context.get("timeline_start", 0.0))
            range_end = range_start + float(qc_context.get("duration", 0.0))
            for cue in self.director_cues:
                if (
                    cue.cue_type == "shot"
                    and ranges_intersect(
                        cue.start_seconds,
                        cue.end_seconds,
                        range_start,
                        range_end,
                    )
                    and not cue.native_audio_qc_user_edited
                ):
                    cue.native_audio_qc_status = message
            self._refresh_director_cues()
            self.statusBar().showMessage(message)
            return
        asset = self.audio_jobs.get(payload.get("job", ""))
        if not asset:
            return
        if "progress" in payload and not payload.get("error"):
            percent = max(0, min(99, round(float(payload["progress"]) * 100)))
            card = self.cards.get(asset.node_id)
            if card:
                card.set_analysis_status(f"音频 {percent}%")
            self.statusBar().showMessage(
                f"{asset.tag} audio · {payload.get('decoded_seconds', 0):.1f}/"
                f"{payload.get('max_seconds', 0):.1f}s"
            )
            return
        self.audio_jobs.pop(payload.get("job", ""), None)
        if payload.get("error"):
            asset.recognition += f"\n\nAudio analysis error: {payload['error']}"
        else:
            asset.recognition += payload.get("summary", "")
            transcript = payload.get("transcript", "")
            if transcript:
                asset.recognition += f"\n\nWHISPER TRANSCRIPT · {payload.get('speech_device', '-')}\n{transcript}"
            else:
                asset.recognition += "\n\nWHISPER TRANSCRIPT\nNo confident speech was transcribed."
        self._sync_timeline_clip_sources(asset)
        self._mark_dirty()
        self._sync_prompt_panel_from_timeline(reconcile_brief=True)
        card = self.cards.get(asset.node_id)
        if card:
            card.set_analysis_status("识别 ✓" if not payload.get("error") else "识别 !")
        if asset is self.selected_asset:
            self._refresh_recognition_inspector(asset)
        self._maybe_auto_enrich(asset)
        self._maybe_request_semantic_lm_unload()

    def _audio_service_finished(self, exit_code: int, log: str) -> None:
        self.audio_runner.discard_pending()
        if self._closing:
            self.audio_jobs.clear()
            self.native_audio_qc_jobs.clear()
            return
        seen: set[int] = set()
        affected_assets: list[MediaAsset] = []
        for asset in self.audio_jobs.values():
            if id(asset) in seen:
                continue
            seen.add(id(asset))
            affected_assets.append(asset)
            self._mark_analysis_failure(
                asset,
                f"Audio service stopped unexpectedly (exit {exit_code}): {log[-300:]}",
            )
        self.audio_jobs.clear()
        if self.native_audio_qc_jobs:
            message = f"Native Audio QC ERROR · analysis service stopped (exit {exit_code})"
            for cue in self.director_cues:
                if cue.cue_type == "shot" and not cue.native_audio_qc_user_edited:
                    cue.native_audio_qc_status = message
            self.native_audio_qc_jobs.clear()
        for asset in affected_assets:
            self._maybe_auto_enrich(asset)
        self._maybe_request_semantic_lm_unload()

    def _start_native_audio_qc(self, path: Path, timeline_start: float) -> None:
        """Analyze H3's untouched output through existing VAD/Whisper tooling."""
        try:
            info = probe_media(path, self.runtime)
            duration = max(0.05, float(info.get("duration") or 0.0))
            if not self.audio_runner.is_running():
                if not self.audio_runner.start(
                    str(self.runtime.python),
                    [
                        str(PROJECT_ROOT / "audio_service.py"),
                        "--model",
                        str(self.runtime.speech_model),
                        "--ffmpeg",
                        str(self.runtime.ffmpeg),
                    ],
                ):
                    raise RuntimeError("Audio service is still stopping")
            expected = [
                layer.text
                for layer in self.text_layers
                if layer.text.strip()
                and layer.content_role in {"dialogue", "voice_over", "lyrics"}
                and ranges_intersect(
                    layer.start_seconds,
                    layer.end_seconds,
                    timeline_start,
                    timeline_start + duration,
                )
            ]
            job_id = f"native-audio-qc:{path.stem}:{time.time_ns()}"
            self.native_audio_qc_jobs[job_id] = {
                "path": str(path),
                "timeline_start": timeline_start,
                "duration": duration,
                "expected_dialogue": expected,
            }
            self.audio_runner.write_json(
                {
                    "job": job_id,
                    "media": str(path),
                    "chunk_seconds": 8.0,
                    "max_seconds": duration,
                }
            )
            self.statusBar().showMessage("Native Audio QC · queued (analysis only, soundtrack unchanged)")
        except Exception as exc:
            message = f"Native Audio QC ERROR · {exc}"
            for cue in self.director_cues:
                if cue.cue_type == "shot" and not cue.native_audio_qc_user_edited:
                    cue.native_audio_qc_status = message
            self.statusBar().showMessage(message)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.project_dirty and self.isVisible():
            choice = QMessageBox.question(
                self,
                "Unsaved Director Project",
                "Save the current Director Project before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if choice == QMessageBox.Cancel or (choice == QMessageBox.Save and not self.save_project()):
                event.ignore()
                return
        self._stop_all_timeline_media()
        self._closing = True
        self.media_runner.stop()
        self.blip_runner.stop()
        self.audio_runner.stop()
        self.semantic_runner.stop()
        self.smart_cut_runner.stop()
        if self.submit_runner:
            self.submit_runner.stop()
        if self.design_media_runner:
            self.design_media_runner.stop()
        if self.media_regeneration_runner:
            self.media_regeneration_runner.stop()
        if self.design_tts_runner:
            self.design_tts_runner.stop()
        if self.design_cleanup_runner:
            self.design_cleanup_runner.stop()
        if self.generated_proxy_runner:
            self.generated_proxy_runner.stop()
        if self.generated_proxy_working:
            try:
                self.generated_proxy_working.unlink(missing_ok=True)
            except OSError:
                pass
            self.generated_proxy_working = None
        super().closeEvent(event)

    def _sync_prompt_panel_from_timeline(
        self,
        *,
        force: bool = False,
        reconcile_brief: bool = False,
    ) -> None:
        if (
            not hasattr(self, "prompt_panel")
            or (self.restoring_project and not force)
            or (not force and not self.prompt_panel.auto_sync.isChecked())
        ):
            return
        self.prompt_sync_in_progress = True
        duration = self.scan.duration_seconds if self.scan else 0.0
        ordered_shots = sorted(
            (cue for cue in self.director_cues if cue.cue_type == "shot"),
            key=lambda cue: (cue.start_seconds, cue.end_seconds),
        )
        shot_lines: list[str] = []
        for index, cue in enumerate(ordered_shots, 1):
            parts = [
                f"SHOT {index} · {cue.start_seconds:.2f}–{cue.end_seconds:.2f}s",
                cue.preset,
                f"{cue.framing} · {cue.camera_angle}",
                f"{cue.camera_movement} · {cue.movement_speed} · {cue.movement_amplitude} amplitude",
            ]
            executable_action = cue.h3_executable_action or cue.subject_action
            if executable_action:
                parts.append(
                    "Core action (must complete): "
                    + canonicalize_cue_reference_ids(
                        executable_action, cue.semantic_reference_directions
                    )
                )
            if cue.continuity_state:
                parts.append(
                    "State to preserve: "
                    + canonicalize_cue_reference_ids(
                        cue.continuity_state, cue.semantic_reference_directions
                    )
                )
            if cue.environment_response:
                parts.append(
                    "Environment: "
                    + canonicalize_cue_reference_ids(
                        cue.environment_response,
                        cue.semantic_reference_directions,
                    )
                )
            if cue.h3_optional_flourish:
                parts.append(
                    "Optional (omit before delaying core): "
                    + canonicalize_cue_reference_ids(
                        cue.h3_optional_flourish, cue.semantic_reference_directions
                    )
                )
            if cue.detail:
                parts.append(
                    "Direction: "
                    + canonicalize_cue_reference_ids(
                        cue.detail, cue.semantic_reference_directions
                    )
                )
            for media_id, direction in cue.semantic_reference_directions.items():
                if direction:
                    stable_token = (
                        media_id
                        if str(media_id).startswith("@")
                        else f"@{media_id}"
                        if re.fullmatch(r"[PVA]\d+", str(media_id), flags=re.I)
                        else str(media_id)
                    )
                    parts.append(
                        f"AI reference {stable_token}: "
                        + canonicalize_cue_reference_ids(
                            direction, cue.semantic_reference_directions
                        )
                    )
            shot_lines.append(" | ".join(parts))
        self.prompt_panel.shots.setPlainText("\n".join(shot_lines))

        def layer_shot_number(layer: TextLayer) -> int:
            if layer.shot_id:
                for index, cue in enumerate(ordered_shots, 1):
                    if cue.cue_id == layer.shot_id:
                        return index
            midpoint = (layer.start_seconds + layer.end_seconds) / 2
            for index, cue in enumerate(ordered_shots, 1):
                if cue.start_seconds <= midpoint <= cue.end_seconds:
                    return index
            return 1

        dialogue_lines: list[str] = []
        for layer in sorted(self.text_layers, key=lambda item: (item.start_seconds, item.end_seconds)):
            shot_number = layer_shot_number(layer)
            if layer.content_role == "dialogue":
                sync = "lip sync" if layer.lip_sync else "no required lip sync"
                direction = (
                    f'{layer.speaker} [{layer.language}, {layer.delivery}, {sync}]: "{layer.text}"'
                )
            elif layer.content_role == "voice_over":
                direction = f'Voice-over: "{layer.text}"'
            elif layer.content_role == "lyrics":
                direction = f'Lyrics: "{layer.text}"'
            else:
                direction = f'On-screen text: "{layer.text}"'
            dialogue_lines.append(f"{shot_number}|{direction}")
        self.prompt_panel.dialogue.setPlainText("\n".join(dialogue_lines))

        ending_cues = [
            cue for cue in self.director_cues
            if cue.cue_type == "marker"
            and ("ending" in cue.preset.lower() or "final" in cue.preset.lower())
        ]
        if ending_cues:
            ending = sorted(ending_cues, key=lambda cue: cue.start_seconds)[-1]
            text = ending.detail or MARKER_RECOMMENDATIONS.get(ending.preset, ending.preset)
            self.prompt_panel.ending.setPlainText(
                f"From {ending.start_seconds:.2f}s through the final frame: {text}"
            )
        else:
            self.prompt_panel.ending.clear()

        def compact(value: object, limit: int) -> str:
            text = " ".join(str(value or "").split())
            if len(text) <= limit:
                return text
            return text[: max(1, limit - 1)].rstrip() + "…"

        reference_roles: list[str] = []
        active_visual_ids: list[str] = []
        active_audio_ids: list[str] = []
        transcript_rows: list[str] = []
        if self.scan:
            for asset in self.scan.timeline_assets():
                if not asset.timeline_placed or asset.activation_mode == "bypass":
                    continue
                media_id = media_shortcut(asset)
                stable_token = f"@{media_id}"
                if asset.media_type in {"image", "video"}:
                    if stable_token not in active_visual_ids:
                        active_visual_ids.append(stable_token)
                elif asset.media_type == "audio":
                    if stable_token not in active_audio_ids:
                        active_audio_ids.append(stable_token)
                if asset.clip_prompt.strip():
                    instruction = " ".join(asset.clip_prompt.split())
                    reference_roles.append(
                        f"{stable_token} at {asset.start_seconds:.2f}-{asset.end_seconds:.2f}s: "
                        f"{instruction[:260]}"
                    )
                if asset.media_type == "audio" and "WHISPER TRANSCRIPT" in asset.recognition:
                    capture = False
                    for raw in asset.recognition.splitlines():
                        line = raw.strip()
                        if line.startswith("WHISPER TRANSCRIPT"):
                            capture = True
                            continue
                        if capture and line and not line.startswith("No confident speech"):
                            transcript_rows.append(line)

        brief_parts = [f"Create a {duration:.2f}-second full-reference video."] if duration else []
        brief_parts.append(
            "Treat the current Timeline, its active reference media, structured Shots and authored speech "
            "as the source of truth; ignore superseded AI Design placeholder descriptions."
        )
        if active_visual_ids:
            brief_parts.append(
                "Integrate the latest active visual references "
                + ", ".join(active_visual_ids)
                + " into coherent moving scenes rather than showing them as flat inserted pictures."
            )
        if reference_roles:
            brief_parts.append("Reference roles: " + "; ".join(reference_roles) + ".")
        if ordered_shots:
            brief_parts.append(
                "Follow the timeline's " + str(len(ordered_shots)) + " structured shot block(s): "
                + ", ".join(cue.preset for cue in ordered_shots) + "."
            )
            story_beats: list[str] = []
            for index, cue in enumerate(ordered_shots, 1):
                beat_parts = [
                    cue.h3_executable_action or cue.subject_action,
                    cue.environment_response,
                    cue.continuity_state,
                ]
                if not any(str(part).strip() for part in beat_parts):
                    beat_parts.extend((cue.detail, cue.preset))
                beat = compact(
                    " ".join(str(part).strip().rstrip(".") for part in beat_parts if str(part).strip()),
                    360,
                )
                if beat:
                    story_beats.append(f"Shot {index}: {beat}.")
            if story_beats:
                brief_parts.append("Current narrative progression: " + " ".join(story_beats))

        voice_over_rows = [
            compact(layer.text, 900)
            for layer in sorted(self.text_layers, key=lambda item: (item.start_seconds, item.end_seconds))
            if layer.content_role == "voice_over" and layer.text.strip()
        ]
        if voice_over_rows:
            brief_parts.append(
                "The exact Timeline voice-over is the spoken narrative source of truth: "
                + " ".join(f'"{text}"' for text in voice_over_rows)
                + "."
            )
        elif transcript_rows:
            brief_parts.append(
                "Use the active audio transcript as spoken narrative guidance: "
                + compact(" ".join(transcript_rows), 1100)
                + "."
            )
        if active_audio_ids:
            brief_parts.append(
                "Reuse and synchronize the active Timeline audio reference(s) "
                + ", ".join(active_audio_ids)
                + "."
            )
        if dialogue_lines:
            brief_parts.append("Preserve the timeline-authored dialogue and visible text exactly.")
        if ending_cues:
            brief_parts.append("Finish on the timeline Ending Hold marker.")
        synthesized_brief = " ".join(brief_parts)
        current_brief = self.prompt_panel.brief.toPlainText().strip()
        if (
            force
            or reconcile_brief
            or not current_brief
            or current_brief == self.prompt_panel.last_timeline_brief
        ):
            self.prompt_panel.brief.setPlainText(synthesized_brief)
        self.prompt_panel.last_timeline_brief = synthesized_brief

        self.prompt_sync_in_progress = False
        self.schedule_prompt_generation()

    def schedule_prompt_generation(self) -> None:
        if (
            not self.scan
            or self.restoring_project
            or self.prompt_sync_in_progress
            or self._closing
        ):
            return
        self.prompt_generation_timer.start()

    def _track_allows_reference(
        self,
        asset: MediaAsset,
        *,
        audio_solo: bool,
    ) -> bool:
        """Return whether an editorial track may feed this H3 request."""
        track = self._track_for_asset(asset)
        if not track or not track.enabled:
            return False
        if track.kind == "visual":
            return bool(track.visible)
        if track.kind == "audio":
            return not track.muted and (not audio_solo or track.solo)
        return False

    def generate_prompt(self, interactive: bool = True) -> None:
        if not self.scan:
            return
        self._sync_timeline_clip_sources()
        if interactive:
            self._sync_prompt_panel_from_timeline()
        soundscape = automatic_background_soundscape({
            "overall_soundscape": self.prompt_panel.soundscape.toPlainText(),
            "creative_brief": self.prompt_panel.brief.toPlainText(),
            "shots": [
                {
                    "subject_action": cue.subject_action,
                    "environment_response": cue.environment_response,
                }
                for cue in self.director_cues if cue.cue_type == "shot"
            ],
        })
        if soundscape != self.prompt_panel.soundscape.toPlainText().strip():
            self.prompt_panel.soundscape.setPlainText(soundscape)
        music_mode = normalize_design_music_mode(self.render_settings.music_mode)
        music = self.prompt_panel.music.toPlainText().strip()
        if music_mode == "off":
            music = "N/A"
        elif music_mode == "auto":
            music = automatic_background_music({
                "non_diegetic_music": music,
                "creative_brief": self.prompt_panel.brief.toPlainText(),
                "shots": [
                    {
                        "subject_action": cue.subject_action,
                        "environment_response": cue.environment_response,
                        "additional_direction": cue.detail,
                    }
                    for cue in self.director_cues if cue.cue_type == "shot"
                ],
            })
        if music != self.prompt_panel.music.toPlainText().strip():
            self.prompt_panel.music.setPlainText(music)
        base_spec = self.prompt_panel.spec()
        if not base_spec.brief:
            self.prompt_panel.output.clear()
            if interactive:
                QMessageBox.information(self, "Brief required", "Add a creative brief before generating the H3 prompt.")
            return
        timeline_assets = self.scan.timeline_assets()
        original_enabled = [(asset, asset.enabled) for asset in timeline_assets]
        audio_solo = any(
            track.enabled and track.solo for track in self.tracks if track.kind == "audio"
        )
        try:
            for asset, was_enabled in original_enabled:
                asset.enabled = was_enabled and self._track_allows_reference(
                    asset, audio_solo=audio_solo
                )
            start, end = self.clip_start.value(), self.clip_end.value()
            _, assets = compile_active_workflow(self.scan, start, end)
            spec = self._prompt_spec_with_director_cues(
                base_spec,
                supplied_dialogue_audio_tag=self._supplied_speech_audio_tag(assets),
            )
            if start > 1e-6 or end < self.scan.duration_seconds - 1e-6:
                output = self._prompt_for_window(
                    start,
                    end,
                    assets,
                    is_final_window=end >= self.scan.duration_seconds - 1e-6,
                )
            else:
                prompt_assets, _ = effective_reference_assets(assets)
                special_key = self.special_combo.currentData()
                special = None if special_key == NONE_SPECIAL else self.profiles[special_key]
                output = build_ref2va_prompt(
                    spec,
                    prompt_assets,
                    end - start,
                    self.profiles[DEFAULT_SKILL],
                    special,
                    source_assets=self.scan.assets,
                )
            self.prompt_panel.output.setPlainText(output)
            self.statusBar().showMessage(
                f"H3 prompt auto-generated with {len(assets)} active references"
            )
        except Exception as exc:
            if interactive:
                QMessageBox.critical(self, "Prompt error", str(exc))
            else:
                self.statusBar().showMessage(f"Automatic prompt generation paused: {exc}")
        finally:
            for asset, was_enabled in original_enabled:
                asset.enabled = was_enabled

    @staticmethod
    def _music_cue_stops_score(cue: DirectorCue) -> bool:
        evidence = f"{cue.preset} {cue.detail}".lower()
        return bool(re.search(
            r"\b(?:stop|end|remove|mute|silence|fade[- ]?out)\b|"
            r"停止配乐|停止配樂|结束配乐|結束配樂|音乐停止|音樂停止|静音|靜音|淡出",
            evidence,
        ))

    def _timeline_music_requested_for_range(
        self, start_seconds: float, end_seconds: float
    ) -> bool:
        """Return whether any part of a range is covered by authored Music Cues."""
        cues = sorted(
            (
                cue for cue in self.director_cues
                if cue.cue_type == "marker" and "music" in cue.preset.lower()
            ),
            key=lambda cue: (cue.start_seconds, cue.end_seconds, cue.cue_id),
        )
        active = False
        for cue in cues:
            if cue.start_seconds >= end_seconds - 1e-6:
                break
            if cue.start_seconds <= start_seconds + 1e-6:
                active = not self._music_cue_stops_score(cue)
                continue
            if active:
                return True
            if not self._music_cue_stops_score(cue):
                return True
        return active

    def _refresh_native_audio_directions(
        self,
        reference_assets: list[MediaAsset] | None = None,
    ) -> None:
        """Refresh prompt-only H3 native audio fields without touching overrides."""
        shots = sorted(
            (cue for cue in self.director_cues if cue.cue_type == "shot"),
            key=lambda cue: (cue.start_seconds, cue.end_seconds, cue.cue_id),
        )
        assets = reference_assets
        if assets is None and self.scan is not None:
            assets = [
                asset for asset in self.scan.assets
                if asset.enabled and asset.timeline_placed
            ]
        assets = assets or []
        previous_profile: NativeAudioProfile | None = None
        inherited_space: tuple[str, str] | None = None
        for cue in shots:
            dialogue_rows = [
                {
                    "content_role": layer.content_role,
                    "speaker": layer.speaker,
                    "delivery": layer.delivery,
                    "text": layer.text,
                }
                for layer in self.text_layers
                if layer.text.strip()
                and layer.content_role in {"dialogue", "voice_over", "lyrics"}
                and ranges_intersect(
                    layer.start_seconds,
                    layer.end_seconds,
                    cue.start_seconds,
                    cue.end_seconds,
                )
            ]
            shot_state = {
                "preset": cue.preset,
                "framing": cue.framing,
                "camera_angle": cue.camera_angle,
                "camera_movement": cue.camera_movement,
                "subject_action": cue.subject_action,
                "environment_response": cue.environment_response,
                "continuity_state": cue.continuity_state,
                "optional_flourish": cue.optional_flourish,
                "detail": cue.detail,
            }
            profile = build_native_audio_profile(
                shot_state,
                dialogue_rows,
                inherited_space=inherited_space,
            )
            inherited_space = (profile.acoustic_space, profile.ambience)
            music_mode = normalize_design_music_mode(self.render_settings.music_mode)
            timeline_music_cue = self._timeline_music_requested_for_range(
                cue.start_seconds, cue.end_seconds
            )
            has_music = (
                music_mode == "auto"
                or (music_mode == "timeline" and timeline_music_cue)
            )
            has_voice_over = any(
                row["content_role"] == "voice_over" for row in dialogue_rows
            )
            acoustic_references: list[str] = []
            for asset in assets:
                if not ranges_intersect(
                    asset.start_seconds,
                    asset.end_seconds,
                    cue.start_seconds,
                    cue.end_seconds,
                ):
                    continue
                evidence = " ".join(
                    (asset.filename, asset.clip_prompt, asset.recognition)
                ).lower()
                is_authored_speech = "ai design authored speech tts" in evidence
                is_music_or_dialogue = bool(re.search(
                    r"\b(?:music|song|score|dialogue|speech|voiceover|voice-over|lyrics)\b|"
                    r"音乐|音樂|歌曲|配乐|配樂|对白|對白|旁白|歌词|歌詞",
                    evidence,
                ))
                acoustic_keywords = bool(re.search(
                    r"\b(?:ambience|ambient|room tone|location sound|on-location|environmental sound|"
                    r"spatial acoustics|field recording)\b|环境声|環境聲|现场声|現場聲|空间声学|空間聲學|底噪",
                    evidence,
                ))
                is_acoustic_reference = (
                    asset.media_type == "audio"
                    and not is_authored_speech
                    and not is_music_or_dialogue
                ) or (
                    asset.media_type == "video" and acoustic_keywords
                )
                if is_acoustic_reference:
                    acoustic_references.append(asset.tag)
            if not cue.native_audio_direction_user_edited:
                cue.native_audio_direction = native_audio_direction_text(
                    profile,
                    has_authored_voice_over=has_voice_over,
                    music_requested=has_music,
                )
            if not cue.environment_continuity_user_edited:
                cue.environment_continuity = environment_continuity_text(
                    previous_profile,
                    profile,
                )
            if not cue.audio_reference_intent_user_edited:
                cue.audio_reference_intent = audio_reference_intent_text(
                    acoustic_references
                )
            previous_profile = profile

    def _seed_native_audio_for_new_cue(self, cue: DirectorCue) -> None:
        if cue.cue_type != "shot" or cue in self.director_cues:
            return
        self.director_cues.append(cue)
        try:
            self._refresh_native_audio_directions()
        finally:
            self.director_cues.remove(cue)

    def _prompt_spec_with_director_cues(
        self,
        spec: PromptSpec,
        *,
        window_start: float | None = None,
        window_end: float | None = None,
        is_final_window: bool = True,
        supplied_dialogue_audio_tag: str = "",
        reference_assets: list[MediaAsset] | None = None,
    ) -> PromptSpec:
        """Merge timeline-authored direction into the six-section H3 prompt input."""
        self._refresh_native_audio_directions(reference_assets)
        state = asdict(spec)
        state["has_supplied_dialogue_audio"] = bool(
            supplied_dialogue_audio_tag
        )
        if window_start is not None and window_end is not None:
            # Every hidden H3 request owns a local 0..duration clock. Design
            # presets may contain project-global schedules in prose, so scope
            # every non-Shot production field before it reaches the segment.
            # This prevents an earlier visual/audio phase from being
            # reinterpreted as the opening seconds of a later hidden job.
            for field_name, label in (
                ("style", "visual style"),
                ("references", "reference rule"),
                ("audio", "soundscape"),
                ("music", "music"),
                ("must_keep", "constraint"),
                ("technical", "technical rule"),
                ("ending", "ending"),
            ):
                state[field_name] = scope_timed_prompt_text(
                    str(state.get(field_name, "")),
                    window_start,
                    window_end,
                    field_name=label,
                )
            # Do not let the visible all-timeline Shot/Dialogue fields leak into
            # an internal segment that has no matching cue of its own.
            state["shots"] = []
            state["shot_ranges"] = []
            state["native_audio_ranges"] = []
            state["dialogue"] = ""
            # The visible transition field may summarize the entire project.
            # Hidden generation jobs receive only cues inside their own local
            # interval or H3 tries to replay the full edit in every job.
            state["transition"] = ""
            state["transition_ranges"] = []
        ordered = sorted(self.director_cues, key=lambda cue: (cue.start_seconds, cue.end_seconds))
        if window_start is not None and window_end is not None:
            ordered = [
                cue
                for cue in ordered
                if ranges_intersect(
                    cue.start_seconds,
                    cue.end_seconds,
                    window_start,
                    window_end,
                )
            ]

        # Native mode describes location sound to H3 itself. Legacy generated
        # mix-contract prose is stripped, while the selected OFF/AUTO/TIMELINE
        # policy controls whether the underlying score direction reaches H3.
        state["audio"] = str(state.get("audio", "")).split(
            "Production mix contract:", 1
        )[0].strip(" .")
        raw_music_direction = str(state.get("music", "")).strip()
        if window_start is not None and window_end is not None:
            timeline_music_requested = self._timeline_music_requested_for_range(
                window_start, window_end
            )
        else:
            timeline_music_requested = any(
                cue.cue_type == "marker"
                and "music" in cue.preset.lower()
                and not self._music_cue_stops_score(cue)
                for cue in self.director_cues
            )
        music_mode = normalize_design_music_mode(self.render_settings.music_mode)
        authored_music = raw_music_direction.split(
            "Music mix contract:", 1
        )[0].strip(" .")
        if music_mode == "off":
            state["music"] = "N/A"
        elif music_mode == "auto":
            generated_music = automatic_background_music({
                "non_diegetic_music": raw_music_direction,
                "creative_brief": state.get("brief", ""),
                "shots": [
                    {
                        "subject_action": cue.subject_action,
                        "environment_response": cue.environment_response,
                        "additional_direction": cue.detail,
                    }
                    for cue in ordered if cue.cue_type == "shot"
                ],
            })
            authored_music = generated_music.split(
                "Music mix contract:", 1
            )[0].strip(" .")
            state["music"] = (
                authored_music
                if authored_music and authored_music.lower() != "n/a"
                else "Subtle scene-appropriate cinematic underscore shaped to the active Shot's emotion and pacing."
            )
        elif timeline_music_requested:
            state["music"] = (
                authored_music
                if authored_music and authored_music.lower() != "n/a"
                else "Use only the music explicitly authored by the active Timeline Music Cue."
            )
        else:
            state["music"] = "N/A"

        def local_time(seconds: float) -> float:
            if window_start is None:
                return seconds
            return max(0.0, seconds - window_start)

        shot_cues = [cue for cue in ordered if cue.cue_type == "shot"]
        cut_cues = [cue for cue in ordered if cue.cue_type == "cut"]
        transition_cues = [cue for cue in ordered if cue.cue_type == "transition"]
        marker_cues = [cue for cue in ordered if cue.cue_type == "marker"]

        if shot_cues:
            shots: list[str] = []
            shot_ranges: list[dict] = []
            native_audio_ranges: list[dict] = []
            for cue in shot_cues:
                movement = (
                    f"Camera movement: {cue.camera_movement}, {cue.movement_speed.lower()} speed, "
                    f"{cue.movement_amplitude.lower()} amplitude"
                )
                parts = [
                    cue.preset,
                    f"{cue.framing} framing",
                    f"{cue.camera_angle} camera angle",
                    movement,
                ]
                executable_action = cue.h3_executable_action or cue.subject_action
                if executable_action:
                    parts.append(
                        "MANDATORY CORE ACTION - complete before any flourish: "
                        + canonicalize_cue_reference_ids(
                            executable_action, cue.semantic_reference_directions
                        )
                    )
                if cue.continuity_state:
                    parts.append(
                        "CONTINUITY STATE - preserve exactly: "
                        + canonicalize_cue_reference_ids(
                            cue.continuity_state, cue.semantic_reference_directions
                        )
                    )
                if cue.environment_response:
                    parts.append(
                        "Environment response: "
                        + canonicalize_cue_reference_ids(
                            cue.environment_response,
                            cue.semantic_reference_directions,
                    )
                )
                if cue.h3_optional_flourish:
                    parts.append(
                        "OPTIONAL FLOURISH - omit before delaying, replaying or weakening the core action: "
                        + canonicalize_cue_reference_ids(
                            cue.h3_optional_flourish, cue.semantic_reference_directions
                        )
                    )
                parts.append("NATIVE AUDIO DIRECTION - " + cue.native_audio_direction)
                parts.append("ENVIRONMENT CONTINUITY - " + cue.environment_continuity)
                parts.append("AUDIO REFERENCE INTENT - " + cue.audio_reference_intent)
                if cue.detail:
                    parts.append(
                        canonicalize_cue_reference_ids(
                            cue.detail, cue.semantic_reference_directions
                        )
                    )
                for media_id, direction in cue.semantic_reference_directions.items():
                    if direction:
                        stable_token = (
                            media_id
                            if str(media_id).startswith("@")
                            else f"@{media_id}"
                            if re.fullmatch(r"[PVA]\d+", str(media_id), flags=re.I)
                            else str(media_id)
                        )
                        parts.append(
                            f"AI-enriched media reference {stable_token}: "
                            + canonicalize_cue_reference_ids(
                                direction, cue.semantic_reference_directions
                            )
                        )
                layers = [
                    layer
                    for layer in self.text_layers
                    if (
                        (layer.shot_id == cue.cue_id and (
                            window_start is None
                            or ranges_intersect(
                                layer.start_seconds,
                                layer.end_seconds,
                                window_start,
                                window_end,
                            )
                        ))
                        or (
                            not layer.shot_id
                            and layer.start_seconds < cue.end_seconds
                            and layer.end_seconds > cue.start_seconds
                            and (
                                window_start is None
                                or ranges_intersect(
                                    layer.start_seconds,
                                    layer.end_seconds,
                                    window_start,
                                    window_end,
                                )
                            )
                        )
                    )
                ]
                description = ". ".join(part.strip().rstrip(".") for part in parts if part.strip())
                shots.append(description)
                shot_ranges.append(
                    {
                        "cue_id": cue.cue_id,
                        "track_id": cue.track_id,
                        "start_seconds": local_time(
                            max(cue.start_seconds, window_start)
                            if window_start is not None else cue.start_seconds
                        ),
                        "end_seconds": local_time(
                            min(cue.end_seconds, window_end)
                            if window_end is not None else cue.end_seconds
                        ),
                        "description": description,
                    }
                )
                native_audio_ranges.append(
                    {
                        "cue_id": cue.cue_id,
                        "start_seconds": local_time(
                            max(cue.start_seconds, window_start)
                            if window_start is not None else cue.start_seconds
                        ),
                        "end_seconds": local_time(
                            min(cue.end_seconds, window_end)
                            if window_end is not None else cue.end_seconds
                        ),
                        "native_audio_direction": cue.native_audio_direction,
                        "environment_continuity": cue.environment_continuity,
                        "audio_reference_intent": cue.audio_reference_intent,
                    }
                )
            state["shots"] = shots
            state["shot_ranges"] = shot_ranges
            state["native_audio_ranges"] = native_audio_ranges

        # Type Tool content is a first-class Timeline track, never part of a
        # visual Director Shot's prompt payload.  Keep exact wording in one
        # place so editing a DIA/VO/LYR clip updates Ori without opening Shot.
        state["text_ranges"] = [
            {
                "layer_id": layer.layer_id,
                "track_id": layer.track_id,
                "start_seconds": local_time(
                    max(layer.start_seconds, window_start)
                    if window_start is not None else layer.start_seconds
                ),
                "end_seconds": local_time(
                    min(layer.end_seconds, window_end)
                    if window_end is not None else layer.end_seconds
                ),
                "content_role": layer.content_role,
                "text": layer.text,
                "speaker": layer.speaker,
                "language": layer.language,
                "delivery": layer.delivery,
                "lip_sync": layer.lip_sync,
                "shot_id": layer.shot_id,
                "supplied_audio_tag": supplied_dialogue_audio_tag,
            }
            for layer in sorted(
                self.text_layers,
                key=lambda item: (item.start_seconds, item.end_seconds, item.layer_id),
            )
            if layer.text.strip()
            and (
                window_start is None
                or (
                    layer.start_seconds >= window_start - 1e-6
                    and layer.start_seconds < window_end - 1e-6
                )
            )
        ]
        if self.prompt_panel.auto_sync.isChecked() and self.text_layers:
            # The visible Dialogue panel mirrors Type clips. The compiler emits
            # only text_ranges, preventing duplicate or competing speech.
            state["dialogue"] = ""

        visible_text_rows = [
            row for row in state["text_ranges"]
            if str(row.get("content_role", "")) == "on_screen_text"
        ]
        # Visible words have one authoritative source: editable Timeline
        # on_screen_text layers. Old Design constraints and Shot prose may
        # still contain requests such as "show this text on screen". Remove
        # those phrases from every compiled window so a screen instruction
        # owned by an earlier Shot cannot leak into a later phone/final Shot.
        for field_name in ("brief", "must_keep", "technical"):
            state[field_name] = strip_untracked_visible_text_directions(
                state.get(field_name, "")
            )
        state["shots"] = [
            strip_untracked_visible_text_directions(row)
            for row in state.get("shots", [])
        ]
        for row in state.get("shot_ranges", []):
            if isinstance(row, dict):
                row["description"] = strip_untracked_visible_text_directions(
                    row.get("description", "")
                )
        if visible_text_rows:
            exact_words = " / ".join(
                f'"{str(row.get("text", "")).strip()}"'
                for row in visible_text_rows
                if str(row.get("text", "")).strip()
            )
            visible_text_contract = (
                "VISIBLE TEXT WHITELIST: the only visible words permitted in this generated "
                f"window are the Timeline on_screen_text events {exact_words}. Render them only "
                "at their authored times. Do not invent, repeat or burn in any other subtitle, "
                "caption, lower-third, dialogue or voice-over text."
            )
        else:
            visible_text_contract = (
                "VISIBLE TEXT LOCK: this generated window has no Timeline on_screen_text event. "
                "Render no subtitles, captions, lower-thirds or burned-in spoken words. Dialogue "
                "and voice-over are audio only; never convert them into pixels. Never draw large "
                "centered typography or quotation text. Any monitor, phone, sign or interface must "
                "remain blank, defocused, cropped or unreadable."
            )
        for field_name in ("must_keep", "technical"):
            current = re.sub(
                r"(?:VISIBLE TEXT WHITELIST|VISIBLE TEXT LOCK):.*?(?=(?:CHARACTER CONTINUITY CONTRACT|$))",
                "",
                str(state.get(field_name, "")),
                flags=re.I | re.S,
            ).strip(" .")
            state[field_name] = (
                current + (". " if current else "") + visible_text_contract
            )

        transition_notes = [
            f"At {local_time(cue.start_seconds):.2f}s use {cue.preset}"
            + (f": {cue.detail}" if cue.detail else "")
            for cue in transition_cues
        ]
        transition_notes.extend(f"CUT at {local_time(cue.start_seconds):.2f}s" for cue in cut_cues)
        if transition_notes:
            state["transition"] = "; ".join(
                part for part in (state.get("transition", "").strip(), *transition_notes) if part
            )

        structured_transitions: list[dict] = []
        for cue in (*transition_cues, *cut_cues):
            boundary = cue.start_seconds
            from_shot = max(
                (
                    shot for shot in shot_cues
                    if shot.end_seconds <= boundary + 0.5
                    and shot.start_seconds < boundary - 1e-6
                ),
                key=lambda shot: (shot.end_seconds, shot.start_seconds),
                default=None,
            )
            to_shot = min(
                (
                    shot for shot in shot_cues
                    if shot.start_seconds >= boundary - 0.5
                    and shot.end_seconds > boundary + 1e-6
                ),
                key=lambda shot: (shot.start_seconds, shot.end_seconds),
                default=None,
            )
            description = (
                "CUT"
                if cue.cue_type == "cut"
                else cue.preset + (f": {cue.detail}" if cue.detail else "")
            )
            row = {
                "cue_id": cue.cue_id,
                "start_seconds": local_time(cue.start_seconds),
                "end_seconds": local_time(cue.end_seconds),
                "description": description,
            }
            if from_shot is not None:
                row["from_shot_id"] = from_shot.cue_id
            if to_shot is not None:
                row["to_shot_id"] = to_shot.cue_id
            structured_transitions.append(row)
        if structured_transitions:
            state["transition_ranges"] = structured_transitions

        ending_notes = [
            cue for cue in marker_cues if "ending" in cue.preset.lower() or "final" in cue.preset.lower()
        ]
        if ending_notes and is_final_window:
            cue = ending_notes[-1]
            state["ending"] = cue.detail or cue.preset
        elif not is_final_window:
            state["ending"] = (
                "Continue the action through the end of this segment. Preserve motion direction, "
                "subject pose, camera trajectory, lighting, environment state, and audio rhythm in "
                "the final second as a clean continuity handoff; do not conclude the story."
            )

        technical_notes = [
            f"{cue.preset} at {local_time(cue.start_seconds):.2f}s" + (f": {cue.detail}" if cue.detail else "")
            for cue in marker_cues
            if cue not in ending_notes
            and not cue.preset.startswith(SPEECH_TIMELINE_MARKER_PREFIX)
        ]
        if technical_notes:
            state["technical"] = "; ".join(
                part for part in (state.get("technical", "").strip(), *technical_notes) if part
            )
        return PromptSpec(**state)

    @staticmethod
    def _supplied_speech_audio_tag(assets: list[MediaAsset]) -> str:
        """Return the exact active Audio tag, preferring generated authored TTS."""
        valid: list[MediaAsset] = []
        for asset in assets:
            if asset.media_type != "audio" or not asset.enabled:
                continue
            path = Path(str(asset.local_path or ""))
            if path.is_file() and path.stat().st_size > 44:
                valid.append(asset)
        preferred = next(
            (
                asset for asset in valid
                if "AI DESIGN AUTHORED SPEECH TTS" in asset.recognition
            ),
            valid[0] if valid else None,
        )
        return preferred.tag if preferred else ""

    def _prompt_for_window(
        self,
        start: float,
        end: float,
        assets: list[MediaAsset],
        *,
        is_final_window: bool,
        continuity: dict | None = None,
    ) -> str:
        """Build an H3 prompt whose timeline timestamps are local to one hidden segment."""
        spec = self._prompt_spec_with_director_cues(
            self.prompt_panel.spec(),
            window_start=start,
            window_end=end,
            is_final_window=is_final_window,
            supplied_dialogue_audio_tag=self._supplied_speech_audio_tag(assets),
            reference_assets=assets,
        )
        if start is not None and end is not None:
            # A global creative brief describes the complete movie. Feeding it
            # to every hidden H3 job makes each job attempt the whole story and
            # visually restart from the reference images. Always replace its
            # action summary with a strictly local generation brief.
            local_shots = [
                cue for cue in self.director_cues
                if cue.cue_type == "shot"
                and ranges_intersect(cue.start_seconds, cue.end_seconds, start, end)
            ]
            local_layers = [
                layer for layer in self.text_layers
                if ranges_intersect(layer.start_seconds, layer.end_seconds, start, end)
            ]
            local_speech_layers = [
                layer for layer in local_layers
                if layer.content_role in {"dialogue", "voice_over", "lyrics"}
            ]
            brief_parts = [
                f"Generate only the timeline interval from {start:.2f}s to {end:.2f}s "
                f"as one {end - start:.2f}-second continuation.",
                "Execute only the current Shot blocks listed below. Do not summarize, preview, "
                "restart, recap, or perform any action scheduled outside this interval.",
                "Begin in medias res on the first listed action and use the final frames only "
                "to hand momentum into the next interval.",
            ]
            all_shots = sorted(
                (cue for cue in self.director_cues if cue.cue_type == "shot"),
                key=lambda cue: (cue.start_seconds, cue.end_seconds, cue.cue_id),
            )
            completed_ids = [
                cue.cue_id for cue in all_shots
                if cue.end_seconds <= start + 1e-6
            ]
            if completed_ids:
                brief_parts.append(
                    "Timeline checkpoint: Shot blocks " + ", ".join(completed_ids)
                    + " are already completed off-screen. Treat those IDs only as elapsed edit "
                      "history; never stage their opening pose, setup, attack, camera introduction "
                      "or environmental impact again."
                )
                previous_shot = max(
                    (
                        cue for cue in all_shots
                        if cue.end_seconds <= start + 1e-6
                    ),
                    key=lambda cue: (cue.end_seconds, cue.start_seconds, cue.cue_id),
                )
                terminal_state = self._terminal_state_from_shot(previous_shot)
                if terminal_state:
                    brief_parts.append(
                        "Boundary state contract: "
                        f"{previous_shot.cue_id} has already finished with {terminal_state} "
                        "Use that only as the inherited physical state immediately before frame "
                        "one. Begin with the next action; do not show, reconstruct, hold or replay "
                        "the completed terminal pose."
                    )
            if local_shots:
                first_shot = min(
                    local_shots,
                    key=lambda cue: (cue.start_seconds, cue.end_seconds, cue.cue_id),
                )
                brief_parts.append(
                    f"The first visible event belongs to {first_shot.cue_id}, "
                    f"{first_shot.preset.strip() or first_shot.cue_id}. "
                    "Enter its already-in-progress physical state in the "
                    "first second; do not insert an establishing view, neutral ready pose, or "
                    "reference-image tableau before it."
                )
            brief_parts.append(
                "Reference images define identity, props, geography and explicitly assigned visual "
                "states. They are not instructions to replay a depicted pose or restart the story."
            )
            brief_parts.append(
                "The visible scene may contain only subjects, locations, props, lighting states and "
                "actions explicitly present in this segment's Shot blocks or active references. "
                "A name or place that survives only inside a project-global modifier is inactive "
                "continuity metadata; never introduce it into this segment."
            )
            local_roles = [
                f"{asset.tag}: {' '.join(asset.clip_prompt.split())[:260]}"
                for asset in assets if asset.clip_prompt.strip()
            ]
            if local_roles:
                brief_parts.append("Reference roles: " + "; ".join(local_roles) + ".")
            image_assets = [asset for asset in assets if asset.media_type == "image"]
            female_identity = next(
                (
                    asset for asset in image_assets
                    if re.search(
                        r"\b(?:woman|female|girl|heroine)\b|女人|女性|女孩",
                        f"{asset.filename} {asset.clip_prompt}", re.I,
                    )
                    and not re.search(
                        r"\b(?:man|male|boy|hero)\b|男人|男性|男孩",
                        f"{asset.filename} {asset.clip_prompt}", re.I,
                    )
                ),
                None,
            )
            male_identity = next(
                (
                    asset for asset in image_assets
                    if re.search(
                        r"\b(?:man|male|boy|hero)\b|男人|男性|男孩",
                        f"{asset.filename} {asset.clip_prompt}", re.I,
                    )
                    and not re.search(
                        r"\b(?:woman|female|girl|heroine)\b|女人|女性|女孩",
                        f"{asset.filename} {asset.clip_prompt}", re.I,
                    )
                ),
                None,
            )
            speaker_references = {
                "S1": female_identity.tag if female_identity is not None else "the female character",
                "S2": male_identity.tag if male_identity is not None else "the male character",
            }
            local_dialogue_layers = [
                layer for layer in local_speech_layers
                if layer.content_role == "dialogue"
            ]
            if local_dialogue_layers:
                brief_parts.append(
                    "SPEAKER-TO-FACE IDENTITY LOCK: S1 always means the female voice/character "
                    f"defined by {speaker_references['S1']}; S2 always means the male "
                    f"voice/character defined by {speaker_references['S2']}. These assignments "
                    "never swap with screen position, shot order or camera angle. During each "
                    "Dialogue Text Range, only the assigned speaker moves lips and jaw; every "
                    "listener keeps a fully closed, still mouth and only reacts silently. "
                    "Voice-over never causes any visible character to lip-sync."
                )
                brief_parts.append(
                    "Dialogue face schedule: "
                    + "; ".join(
                        f"{max(start, layer.start_seconds) - start:.2f}-"
                        f"{min(end, layer.end_seconds) - start:.2f}s {layer.layer_id} "
                        f"uses {layer.speaker} -> {speaker_references.get(layer.speaker, layer.speaker)}"
                        for layer in sorted(
                            local_dialogue_layers,
                            key=lambda item: (item.start_seconds, item.end_seconds, item.layer_id),
                        )
                    )
                    + "."
                )
            if local_shots:
                brief_parts.append(
                    "Follow this segment's " + str(len(local_shots))
                    + " structured shot block(s): "
                    + ", ".join(
                        cue.preset.strip() or cue.cue_id for cue in local_shots
                    ) + "."
                )
            if local_speech_layers:
                brief_parts.append(
                    "Preserve this segment's authored dialogue, voice-over and lyrics exactly. "
                    "Only Timeline Dialogue, Voice-over or Lyrics Text Ranges may produce a "
                    "human voice; never improvise, repeat, paraphrase or start an unlisted word."
                )
            else:
                brief_parts.append(
                    "This segment has no authored speech event. Generate no spoken word, vocal "
                    "fragment, whisper, narration or intelligible background voice."
                )
            if local_speech_layers:
                speech_windows = []
                for layer in sorted(
                    local_speech_layers,
                    key=lambda item: (item.start_seconds, item.end_seconds, item.layer_id),
                ):
                    local_start = max(start, layer.start_seconds) - start
                    local_end = min(end, layer.end_seconds) - start
                    speech_windows.append(
                        f"{local_start:.2f}-{local_end:.2f}s {layer.layer_id} "
                        f"({layer.speaker or 'speaker'})"
                    )
                brief_parts.append(
                    "SPEECH WHITELIST WITH VOCAL-SILENCE GAPS: human speech is permitted only "
                    "inside these segment-local windows: "
                    + "; ".join(speech_windows)
                    + ". Start and finish each exact line inside its own window. Every interval "
                      "outside those windows is strict vocal silence: no filler syllable, false "
                      "start, repeated word, translation, commentary, whisper, crowd voice or "
                      "telephone voice. Room tone, music and non-vocal Foley may continue."
                )
            brief_parts.append(
                "AUDIO SEGMENT BOUNDARY CONTRACT: establish the location's continuous room tone "
                "or outdoor ambience from the first frame and keep it stable through the final "
                "frame. Complete every authored utterance by its exact Text Range end. Before an "
                "internal edit boundary leave at least one second for natural breath, reverberation "
                "decay and ambience only; at the final project endpoint use all available authored "
                "tail without extending the Timeline. "
                "Never begin a fresh sound, word, music cue or Foley transient in the final second; "
                "never end the audio bed with an abrupt digital stop."
            )
            if is_final_window and any(
                cue.cue_type == "marker"
                and ("ending" in cue.preset.lower() or "final" in cue.preset.lower())
                and ranges_intersect(cue.start_seconds, cue.end_seconds, start, end)
                for cue in self.director_cues
            ):
                brief_parts.append("Finish on this segment's Timeline Ending Hold marker.")
            state = asdict(spec)
            state["brief"] = " ".join(brief_parts)
            spec = PromptSpec(**state)
        prompt_assets: list[MediaAsset] = []
        for asset in assets:
            clone = MediaAsset(**asdict(asset))
            clone.start_seconds = round(max(start, asset.start_seconds) - start, 6)
            clone.end_seconds = round(min(end, asset.end_seconds) - start, 6)
            prompt_assets.append(clone)
        continuity = continuity or {}
        prompt_assets, continuity_tag = effective_reference_assets(
            prompt_assets,
            extra_kind=str(continuity.get("kind", "")),
            extra_binding=str(continuity.get("binding", "")),
            extra_has_paired_audio=bool(continuity.get("paired_audio_binding")),
        )
        if continuity_tag:
            continuity["tag"] = continuity_tag
        special_key = self.special_combo.currentData()
        special = None if special_key == NONE_SPECIAL else self.profiles[special_key]
        return build_ref2va_prompt(
            spec,
            prompt_assets,
            end - start,
            self.profiles[DEFAULT_SKILL],
            special,
            source_assets=self.scan.assets if self.scan else None,
        )

    def export_active_api(self) -> None:
        if not self.scan:
            return
        start, end = self.clip_start.value(), self.clip_end.value()
        if end <= start:
            QMessageBox.warning(self, "Invalid work area", "Work-area end must be later than its start.")
            return
        # Rebuild from stable Timeline IDs so a previous work area's dynamic
        # Picture/Video/Audio ordinals can never leak into this export.
        self.generate_prompt(interactive=False)
        self._read_settings_ui()
        seed = self._new_seed()
        try:
            compiled, assets = self._compiled_job(
                megapixels=self.render_settings.megapixels,
                seed=seed,
                enable_rtx_vsr=self.render_settings.rtx_video_super_resolution,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Compile error", str(exc))
            return
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Export active ComfyUI API",
            str(PROJECT_ROOT / f"h3_active_{start:.2f}-{end:.2f}.json"),
            "JSON (*.json)",
        )
        if not destination:
            return
        Path(destination).write_text(json.dumps(compiled, ensure_ascii=False, indent=2), encoding="utf-8")
        QMessageBox.information(
            self,
            "Active API exported",
            f"Saved {Path(destination).name}\nSeed: {seed}\n"
            f"Active references: {', '.join(asset.tag for asset in assets) or 'none'}",
        )

    @staticmethod
    def _new_seed(previous: int | None = None) -> int:
        seed = secrets.randbelow(2**63 - 1)
        while previous is not None and seed == previous:
            seed = secrets.randbelow(2**63 - 1)
        return seed

    def _generation_parameters(
        self,
        *,
        megapixels: float,
        seed: int,
        enable_rtx_vsr: bool,
    ) -> dict:
        return {
            "aspect_ratio": self.render_settings.aspect_ratio,
            "megapixels": megapixels,
            "sampling_steps": self.render_settings.sampling_steps,
            "denoise": self.render_settings.denoise,
            "seed": seed,
            "enable_rtx_vsr": enable_rtx_vsr,
        }

    def _progress_shot_rows(self, start: float, end: float) -> list[dict]:
        """Return unique Shot weights clipped to the current work area."""
        rows: list[dict] = []
        seen: set[str] = set()
        for cue in sorted(
            (item for item in self.director_cues if item.cue_type == "shot"),
            key=lambda item: (item.start_seconds, item.end_seconds, item.cue_id),
        ):
            shot_start = max(float(start), float(cue.start_seconds))
            shot_end = min(float(end), float(cue.end_seconds))
            if shot_end <= shot_start + 1e-9 or cue.cue_id in seen:
                continue
            seen.add(cue.cue_id)
            rows.append(
                {
                    "shot_id": cue.cue_id,
                    "start_seconds": shot_start,
                    "end_seconds": shot_end,
                    "duration_seconds": shot_end - shot_start,
                }
            )
        return rows

    def _continuity_slot(
        self,
        active_assets: list[MediaAsset],
        mode: str,
    ) -> dict:
        """Describe one unused reference slot for the selected boundary policy.

        Match-action boundaries retain the text-only state contract.  Motion
        and authored transition boundaries use a motion-only clip containing
        exactly the preceding 24 frames.  One physical H3 video input is
        reserved for that hidden context when possible.
        """
        if not self.scan or not self.scan.h3_node_ids:
            return {}
        if mode == "match_action":
            return {}
        media_type = "video"
        if mode not in {"motion_reference", "transition"}:
            return {}
        active_ids = {
            str(asset.request_loader_node_id or asset.source_node_id or asset.node_id)
            for asset in active_assets
        }
        h3_id = self.scan.h3_node_ids[0]
        h3_inputs = (self.scan.nodes.get(h3_id, {}).get("inputs") or {})
        candidates = [
            asset
            for asset in self.scan.physical_assets("video")
            if (
                asset.media_type == media_type
                and asset.node_id not in active_ids
                and asset.binding != "unassigned"
                and isinstance(h3_inputs.get(asset.binding), list)
            )
        ]
        if not candidates:
            return {}

        def binding_index(asset: MediaAsset) -> int:
            match = re.search(r"_(\d+)$", asset.binding)
            return int(match.group(1)) if match else -1

        # Any free pool loader can carry continuity. The worker canonicalizes
        # Autogrow input order after injection, while the prompt compiler uses
        # this exact binding index to calculate H3's effective ordinal.
        asset = min(candidates, key=binding_index)
        active_video_sources = {
            stable_reference_id(item)
            for item in active_assets
            if item.media_type == "video"
        }
        request_binding = (
            "ref_videos.ref_video_" + str(len(active_video_sources))
        )
        result = {
            "kind": media_type,
            "mode": mode,
            "tag": "",
            "loader_node_id": asset.node_id,
            "loader_input": "file" if media_type == "video" else "image",
            "h3_node_id": h3_id,
            # The free loader remains a permanent Media Pool source, but the
            # hidden continuity clip is appended after the request's compacted
            # user-video references.  Never reuse the loader's sparse physical
            # suffix here or it can collide with a compiled user reference.
            "binding": request_binding,
            "source_binding": asset.binding,
            "connection": list(h3_inputs[asset.binding]),
            "frame_count": 24,
            "fps": 24,
            "tail_seconds": 1.0,
            "visual_only": True,
        }
        # Deliberately do not attach the loader's paired audio output.  The
        # preceding 24 frames are visual motion context, not prior sound to
        # repeat at the next segment boundary.
        return result

    def _reserve_continuity_video_slot(
        self,
        active_assets: list[MediaAsset],
        mode: str,
    ) -> MediaAsset | None:
        """Free one auto video reference slot for hidden 24-frame context.

        The workflow has three physical H3 video inputs even when the editor
        owns V4+ tracks.  If all three are occupied, prefer preserving
        force-active references and release the least temporally specific
        automatic video reference for this render window only.
        """
        if mode not in {"motion_reference", "transition"}:
            return None
        if self._continuity_slot(active_assets, mode):
            return None
        candidates = [
            asset
            for asset in active_assets
            if asset.media_type == "video" and asset.activation_mode != "active"
        ]
        if not candidates:
            return None

        def release_score(asset: MediaAsset) -> tuple[int, float, int]:
            duration = max(0.0, asset.end_seconds - asset.start_seconds)
            # Global/long automatic references are less specific to this
            # boundary than a tightly timed action clip.
            timed_specificity = 1 if duration < MAX_NATIVE_SECONDS - 1e-6 else 0
            prompted = 1 if asset.clip_prompt.strip() else 0
            match = re.search(r"_(\d+)$", asset.request_binding or asset.binding)
            binding_index = int(match.group(1)) if match else 10_000
            return timed_specificity + prompted, -duration, -binding_index

        released = min(candidates, key=release_score)
        released_source = stable_reference_id(released)
        for asset in self.scan.timeline_assets() if self.scan else []:
            if stable_reference_id(asset) == released_source:
                asset.enabled = False
        return released

    def _reference_belongs_to_window(
        self,
        asset: MediaAsset,
        start: float,
        end: float,
    ) -> bool:
        """Keep a short AI-designed action reference in its owning segment.

        Design-generated identity/environment references normally cover the
        whole work area and remain global.  A shorter action-state reference
        is owned by the hidden segment containing its start time; merely
        crossing a later segment boundary must not make H3 perform the same
        pose again.  Manually placed media and force-active references retain
        their established overlap behaviour.
        """
        if (
            asset.media_type != "image"
            or asset.activation_mode == "active"
            or "AI DESIGN GENERATED REFERENCE" not in asset.recognition
        ):
            return True
        work_start = float(self.clip_start.value())
        work_end = float(self.clip_end.value())
        if (
            asset.start_seconds <= work_start + 1e-6
            and asset.end_seconds >= work_end - 1e-6
        ):
            return True
        if asset.start_seconds < start - 1e-6 < asset.end_seconds:
            return False
        return True

    @staticmethod
    def _terminal_state_from_shot(cue: DirectorCue) -> str:
        """Extract a concrete terminal pose instead of a generic boundary note."""

        def split_sentences(value: str) -> list[str]:
            return [
                part.strip()
                for part in re.split(
                    r"(?<=[.!?\u3002\uff01\uff1f])\s+", value.strip()
                )
                if part.strip()
            ]

        action_rows = split_sentences(cue.h3_executable_action or cue.subject_action)
        continuity_rows = split_sentences(cue.continuity_state)
        environment_rows = split_sentences(cue.environment_response)
        direction_rows = split_sentences(cue.detail)
        selected: list[str] = []
        if continuity_rows:
            selected.append(continuity_rows[-1])
        if action_rows:
            selected.append(action_rows[-1])
        elif environment_rows:
            selected.append(environment_rows[-1])

        anchors = (
            "final frame", "continuity anchor", "end with", "ends with",
            "ending state", "at the end", "at ",
            "\u6700\u540e\u4e00\u5e27", "\u7ed3\u5c3e", "\u7ed3\u675f\u65f6",
            "\u8fb9\u754c",
        )
        first_anchor = next(
            (
                index for index, sentence in enumerate(direction_rows)
                if any(word in sentence.lower() for word in anchors)
            ),
            None,
        )
        if first_anchor is not None:
            for sentence in direction_rows[first_anchor:first_anchor + 3]:
                normalized = sentence.lower().strip(" .")
                if normalized in {
                    "this is the boundary for part 2",
                    "this is the boundary for part 3",
                    "this serves as the transition to part 2",
                    "this serves as the transition to part 3",
                }:
                    continue
                selected.append(sentence)

        if not selected and direction_rows:
            selected.append(direction_rows[-1])
        return " ".join(dict.fromkeys(selected))[:900]

    @staticmethod
    def _media_fingerprint_rows(assets: list[MediaAsset]) -> list[dict]:
        rows: list[dict] = []
        for asset in assets:
            path = Path(asset.local_path) if asset.local_path else None
            stat = path.stat() if path and path.is_file() else None
            rows.append(
                {
                    "node_id": asset.node_id,
                    "clip_id": asset.clip_id or f"source-{asset.node_id}",
                    "path": str(path.resolve()) if path and path.is_file() else asset.filename,
                    "size": stat.st_size if stat else None,
                    "mtime_ns": stat.st_mtime_ns if stat else None,
                    "start": asset.start_seconds,
                    "end": asset.end_seconds,
                    "clip_prompt": asset.clip_prompt,
                }
            )
        return rows

    def _compiled_window_job(
        self,
        start: float,
        end: float,
        *,
        megapixels: float,
        seed: int,
        enable_rtx_vsr: bool,
        is_final_window: bool,
        continuity_mode: str,
        fingerprint_start: float | None = None,
    ) -> tuple[dict, list[MediaAsset], dict, str]:
        """Compile one hidden segment without changing the visible work area."""
        if not self.scan:
            raise RuntimeError("No API workflow is loaded.")
        self._sync_timeline_clip_sources()
        timeline_assets = self.scan.timeline_assets()
        original_enabled = [(asset, asset.enabled) for asset in timeline_assets]
        audio_solo = any(
            track.enabled and track.solo for track in self.tracks if track.kind == "audio"
        )
        try:
            for asset, was_enabled in original_enabled:
                asset.enabled = was_enabled and self._track_allows_reference(
                    asset, audio_solo=audio_solo
                )
                if asset.enabled and not self._reference_belongs_to_window(
                    asset, start, end
                ):
                    asset.enabled = False

            _, assets = compile_active_workflow(self.scan, start, end)
            released_for_continuity = self._reserve_continuity_video_slot(
                assets, continuity_mode
            )
            if released_for_continuity is not None:
                _, assets = compile_active_workflow(self.scan, start, end)
            continuity = self._continuity_slot(assets, continuity_mode)
            if continuity and released_for_continuity is not None:
                continuity["reserved_from_media"] = media_shortcut(
                    released_for_continuity
                )
            prompt = self._prompt_for_window(
                start,
                end,
                assets,
                is_final_window=is_final_window,
                continuity=continuity,
            )
            if continuity:
                tag = continuity.get("tag", "<reference>")
                if continuity.get("kind") == "video":
                    continuity_rule = (
                        f"{tag} contains exactly the preceding segment's final 24 motion-only frames "
                        "at 24 fps. It is one second of temporal context, not footage to reproduce. "
                        "Do not replay, recap, restart, loop, or imitate its events. Begin with the "
                        "next physical moment after its final frame and execute only the current "
                        "timeline action."
                    )
                else:
                    continuity_rule = (
                        f"{tag} is the final-state continuity still from immediately before this "
                        "segment. It is a temporal checkpoint, not an opening tableau and not an action "
                        "to perform. Preserve its pose, weapon positions, screen direction, camera "
                        "trajectory, lighting and environment as the inherited state before frame one. "
                        "Advance immediately into the current Shot action; never recreate, hold, replay "
                        "or explain the preceding action."
                    )
                prompt = prompt.replace(
                    "subject_definitions:\n",
                    "subject_definitions:\n" + continuity_rule + "\n",
                    1,
                )
            compiled, assets = compile_active_workflow(
                self.scan,
                start,
                end,
                prompt,
                generation=self._generation_parameters(
                    megapixels=megapixels,
                    seed=seed,
                    enable_rtx_vsr=enable_rtx_vsr,
                ),
                preserve_loader_node_ids=(
                    {str(continuity.get("loader_node_id"))}
                    if continuity and continuity.get("loader_node_id")
                    else None
                ),
            )
            fingerprint_workflow = compiled
            fingerprint_assets = assets
            core_start = max(start, float(fingerprint_start or start))
            if core_start > start + 1e-6:
                _, fingerprint_assets = compile_active_workflow(self.scan, core_start, end)
                core_prompt = self._prompt_for_window(
                    core_start,
                    end,
                    fingerprint_assets,
                    is_final_window=is_final_window,
                    continuity=continuity,
                )
                fingerprint_workflow, fingerprint_assets = compile_active_workflow(
                    self.scan,
                    core_start,
                    end,
                    core_prompt,
                    generation=self._generation_parameters(
                        megapixels=megapixels,
                        seed=seed,
                        enable_rtx_vsr=enable_rtx_vsr,
                    ),
                    preserve_loader_node_ids=(
                        {str(continuity.get("loader_node_id"))}
                        if continuity and continuity.get("loader_node_id")
                        else None
                    ),
                )
            fingerprint = content_fingerprint(
                {
                    "workflow": fingerprint_workflow,
                    "continuity": continuity,
                    "continuity_mode": continuity_mode,
                    "render_policy_version": SMART_RENDER_POLICY_VERSION,
                    "media": self._media_fingerprint_rows(fingerprint_assets),
                    "window": [core_start, end],
                }
            )
            return compiled, assets, continuity, fingerprint
        finally:
            for asset, was_enabled in original_enabled:
                asset.enabled = was_enabled

    def _build_smart_render_job(
        self,
        *,
        request_kind: str,
        megapixels: float,
        seed: int,
        enable_rtx_vsr: bool,
    ) -> tuple[Path, int]:
        """Create a resumable sequential job for a work area beyond 15 seconds."""
        start, end = self.clip_start.value(), self.clip_end.value()
        planned = self._planned_render_segments()
        all_media: list[dict[str, str]] = []
        segment_rows: list[dict] = []
        workspace = self._ensure_project_workspace()
        render_root = workspace / "cache" / "generated_outputs" / request_kind / str(seed)
        for index, segment in enumerate(planned):
            segment.seed = derive_named_segment_seed(seed, segment.segment_id)
            core_start = (
                segment.core_start_seconds
                if segment.core_start_seconds is not None
                else segment.start_seconds
            )
            core_end = (
                segment.core_end_seconds
                if segment.core_end_seconds is not None
                else segment.end_seconds
            )
            compiled, assets, continuity, fingerprint = self._compiled_window_job(
                core_start,
                core_end,
                megapixels=megapixels,
                seed=segment.seed,
                enable_rtx_vsr=enable_rtx_vsr,
                is_final_window=index == len(planned) - 1,
                continuity_mode=segment.continuity_mode,
                fingerprint_start=core_start,
            )
            assets = self._prepare_windowed_tts_audio(
                assets, core_start, core_end
            )
            uploads = media_upload_manifest(assets)
            patch_media_upload_names(compiled, uploads)
            segment.fingerprint = fingerprint
            all_media.extend(uploads)
            row = segment.to_dict()
            row.update(
                {
                    "workflow": compiled,
                    "continuity": continuity,
                    "download_dir": str(render_root / segment.segment_id),
                }
            )
            segment_rows.append(row)

        # Every Segment was already patched from its own active asset set.
        # ``unique_media`` is only the union uploaded once by Smart Render.
        # Never patch a Segment again from this union: different Segments may
        # reuse the same physical Loader node for different virtual assets,
        # and a global rewrite would make the final asset win in every window.
        unique_media = list({
            (row["loader_node_id"], row["upload_name"]): row
            for row in all_media
        }.values())

        cache_key = "preview" if request_kind == "preview" else "production"
        cached_manifest = self.smart_render_manifests.get(cache_key, {})
        cached_rows = (
            list(cached_manifest.get("segments") or [])
            if int(cached_manifest.get("render_policy_version", 0))
            == SMART_RENDER_POLICY_VERSION
            else []
        )
        cached_by_id = {
            str(row.get("segment_id", "")): row
            for row in cached_rows
            if Path(str(row.get("output_path", ""))).is_file()
        }
        approved_horizon = float(
            cached_manifest.get("target_duration_seconds", 0.0) or 0.0
        )
        for row in segment_rows:
            cached = cached_by_id.get(str(row["segment_id"]))
            core_end = float(
                row.get("core_end_seconds", row.get("end_seconds", 0.0))
                or row.get("end_seconds", 0.0)
            )
            dirty = str(row["segment_id"]) in self.render_dirty_segment_ids
            fingerprint_match = bool(
                cached and cached.get("fingerprint") == row.get("fingerprint")
            )
            approved_locked_range = bool(
                cached
                and request_kind != "preview"
                and not dirty
                and approved_horizon > 0.0
                and core_end <= approved_horizon + 1e-6
                and str(cached.get("status", "")).lower()
                in {"cached", "complete", "completed", "reusable"}
            )
            if cached and not dirty and (fingerprint_match or approved_locked_range):
                row["status"] = "cached"
                row["output_path"] = str(Path(cached["output_path"]).resolve())
                row["reuse_reason"] = (
                    "approved_locked_range"
                    if approved_locked_range and not fingerprint_match
                    else "fingerprint_match"
                )
                if request_kind != "preview":
                    self.render_dirty_segment_ids.discard(str(row["segment_id"]))

        self._refresh_render_status_bar()

        render_jobs = workspace / "project" / "render_jobs"
        render_jobs.mkdir(parents=True, exist_ok=True)
        job_token = f"{request_kind}_{seed}_{time.time_ns()}"
        manifest_path = render_jobs / f"{job_token}.manifest.json"
        job_path = render_jobs / f"{job_token}.job.json"
        job = {
            "action": "smart_render",
            "render_policy_version": SMART_RENDER_POLICY_VERSION,
            "server": self.server_url.text().strip(),
            "media": unique_media,
            "segments": segment_rows,
            "segment_count": len(segment_rows),
            "progress_shots": self._progress_shot_rows(start, end),
            "segment_attempts": 3,
            "history_poll_interval": self.render_settings.history_poll_interval,
            "generation_timeout": self.render_settings.generation_timeout,
            "http_timeout": self.render_settings.http_request_timeout,
            "request_kind": request_kind,
            "seed": seed,
            "megapixels": megapixels,
            "target_duration_seconds": end - start,
            "timeline_start_seconds": start,
            "timeline_end_seconds": end,
            "ffmpeg": str(self.runtime.ffmpeg),
            "ffprobe": str(self.runtime.ffprobe),
            "master_output": str(render_root / "master.mp4"),
            "manifest_path": str(manifest_path),
        }
        job_path.parent.mkdir(parents=True, exist_ok=True)
        job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        return job_path, len(segment_rows)

    def _prepare_windowed_tts_audio(
        self,
        assets: list[MediaAsset],
        start: float,
        end: float,
    ) -> list[MediaAsset]:
        """Trim full-Timeline authored TTS to the exact hidden H3 window."""
        clones = [deepcopy(asset) for asset in assets]
        duration = max(0.01, end - start)
        cache = CACHE_ROOT / "tts_windows"
        cache.mkdir(parents=True, exist_ok=True)
        for asset in clones:
            if (
                asset.media_type != "audio"
                or "AI DESIGN AUTHORED SPEECH TTS" not in asset.recognition
            ):
                continue
            source = Path(str(asset.local_path or ""))
            if not source.is_file():
                continue
            source_key = (
                f"{source.resolve()}|{source.stat().st_mtime_ns}|"
                f"{start:.6f}|{end:.6f}|{asset.start_seconds:.6f}"
            )
            digest = hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:20]
            destination = cache / f"tts_{digest}_{start:.3f}-{end:.3f}.wav"
            if not destination.is_file() or destination.stat().st_size <= 44:
                source_offset = max(0.0, start - float(asset.start_seconds))
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                completed = subprocess.run(
                    [
                        str(self.runtime.ffmpeg), "-y", "-ss", f"{source_offset:.6f}",
                        "-i", str(source), "-t", f"{duration:.6f}",
                        "-af", f"apad=whole_dur={duration:.6f}",
                        "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le",
                        str(destination),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    creationflags=creation_flags,
                    timeout=max(60, int(duration * 4)),
                )
                if completed.returncode or not destination.is_file():
                    detail = completed.stderr.decode("utf-8", errors="replace")[-1000:]
                    raise RuntimeError(f"Could not prepare segment TTS audio: {detail}")
            asset.local_path = str(destination.resolve())
            asset.filename = destination.name
        return clones

    def _compiled_job(
        self,
        *,
        megapixels: float | None = None,
        seed: int | None = None,
        enable_rtx_vsr: bool | None = None,
    ) -> tuple[dict, list[MediaAsset]]:
        if not self.scan:
            raise RuntimeError("No API workflow is loaded.")
        self._sync_timeline_clip_sources()
        self._read_settings_ui()
        megapixels = self.render_settings.megapixels if megapixels is None else megapixels
        seed = self._new_seed() if seed is None else seed
        enable_rtx_vsr = (
            self.render_settings.rtx_video_super_resolution
            if enable_rtx_vsr is None
            else enable_rtx_vsr
        )
        start, end = self.clip_start.value(), self.clip_end.value()
        if end <= start:
            raise ValueError("Work-area end must be later than its start.")
        timeline_assets = self.scan.timeline_assets()
        original_enabled = [(asset, asset.enabled) for asset in timeline_assets]
        audio_solo = any(track.enabled and track.solo for track in self.tracks if track.kind == "audio")
        try:
            for asset, was_enabled in original_enabled:
                asset.enabled = was_enabled and self._track_allows_reference(
                    asset, audio_solo=audio_solo
                )
            _, prompt_sources = compile_active_workflow(self.scan, start, end)
            is_partial_window = (
                start > 1e-6 or end < self.scan.duration_seconds - 1e-6
            )
            if is_partial_window:
                prompt = self._prompt_for_window(
                    start,
                    end,
                    prompt_sources,
                    is_final_window=end >= self.scan.duration_seconds - 1e-6,
                )
            else:
                prompt_assets, _ = effective_reference_assets(prompt_sources)
                special_key = self.special_combo.currentData()
                special = None if special_key == NONE_SPECIAL else self.profiles[special_key]
                prompt = build_ref2va_prompt(
                    self._prompt_spec_with_director_cues(
                        self.prompt_panel.spec(),
                        supplied_dialogue_audio_tag=self._supplied_speech_audio_tag(
                            prompt_sources
                        ),
                    ),
                    prompt_assets,
                    end - start,
                    self.profiles[DEFAULT_SKILL],
                    special,
                    source_assets=self.scan.assets,
                )
            self.prompt_panel.output.setPlainText(prompt)
            compiled, compiled_assets = compile_active_workflow(
                self.scan,
                start,
                end,
                prompt,
                generation=self._generation_parameters(
                    megapixels=megapixels,
                    seed=seed,
                    enable_rtx_vsr=enable_rtx_vsr,
                ),
            )
            return compiled, self._prepare_windowed_tts_audio(
                compiled_assets, start, end
            )
        finally:
            for asset, was_enabled in original_enabled:
                asset.enabled = was_enabled

    def generate_pre_run_preview(self) -> None:
        self.quality_profile = "motion_preview"
        quality_index = self.quality_profile_combo.findData(self.quality_profile)
        self.quality_profile_combo.blockSignals(True)
        self.quality_profile_combo.setCurrentIndex(max(0, quality_index))
        self.quality_profile_combo.blockSignals(False)
        self.preview_seed = self._new_seed(self.preview_seed)
        self.preview_ready = False
        self.accept_preview_button.setEnabled(False)
        self.reject_preview_button.setEnabled(False)
        self._start_generation("preview", 0.2, self.preview_seed, False)

    def _reconcile_speech_timing_before_run(self) -> list[str]:
        """Apply speech budget and final-tail repair to the live Timeline."""
        if not self.scan or not any(
            layer.text.strip()
            and layer.content_role in {"dialogue", "voice_over", "lyrics"}
            for layer in self.text_layers
        ):
            return []
        payload = {
            "timeline_duration_seconds": float(self.scan.duration_seconds),
            "work_area": [float(self.clip_start.value()), float(self.clip_end.value())],
            "director_cues": [asdict(cue) for cue in self.director_cues],
            "text_layers": [asdict(layer) for layer in self.text_layers],
            "authored_text_requirements": deepcopy(self.authored_text_requirements),
            "assets": {
                asset.node_id: asdict(asset) for asset in self.scan.assets
            },
            "timeline_clips": [
                asdict(asset) for asset in self.scan.timeline_clips
            ],
        }
        repaired, report = repair_speech_timing_payload(payload)
        if not report:
            return []

        cue_rows = {
            str(row.get("cue_id", "")): row
            for row in repaired.get("director_cues") or []
            if isinstance(row, dict)
        }
        for cue in self.director_cues:
            row = cue_rows.get(cue.cue_id)
            if row:
                cue.start_seconds = float(row.get("start_seconds", cue.start_seconds))
                cue.end_seconds = float(row.get("end_seconds", cue.end_seconds))

        layer_rows = {
            str(row.get("layer_id", "")): row
            for row in repaired.get("text_layers") or []
            if isinstance(row, dict)
        }
        for layer in self.text_layers:
            row = layer_rows.get(layer.layer_id)
            if not row:
                continue
            layer.start_seconds = float(row.get("start_seconds", layer.start_seconds))
            layer.end_seconds = float(row.get("end_seconds", layer.end_seconds))
            layer.language = str(row.get("language", layer.language))
            layer.shot_id = str(row.get("shot_id", layer.shot_id))
            layer.speech_timing_auto_adjusted = bool(
                row.get("speech_timing_auto_adjusted", layer.speech_timing_auto_adjusted)
            )

        asset_rows = repaired.get("assets") or {}
        for asset in self.scan.assets:
            row = asset_rows.get(asset.node_id) if isinstance(asset_rows, dict) else None
            if isinstance(row, dict):
                asset.start_seconds = float(row.get("start_seconds", asset.start_seconds))
                asset.end_seconds = float(row.get("end_seconds", asset.end_seconds))
        clip_rows = {
            str(row.get("clip_id", "")): row
            for row in repaired.get("timeline_clips") or []
            if isinstance(row, dict)
        }
        for asset in self.scan.timeline_clips:
            row = clip_rows.get(str(asset.clip_id or ""))
            if row:
                asset.start_seconds = float(row.get("start_seconds", asset.start_seconds))
                asset.end_seconds = float(row.get("end_seconds", asset.end_seconds))

        duration = float(repaired.get("timeline_duration_seconds", self.scan.duration_seconds))
        work_area = repaired.get("work_area") or [0.0, duration]
        self._set_design_duration(duration)
        self.clip_start.setValue(max(0.0, min(duration, float(work_area[0]))))
        self.clip_end.setValue(max(self.clip_start.value() + 0.01, min(duration, float(work_area[1]))))
        self.authored_text_requirements = deepcopy(
            repaired.get("authored_text_requirements") or []
        )
        self._sync_timeline_clip_sources()
        self._refresh_director_cues()
        self._refresh_text_layers()
        self._mark_all_render_segments_dirty()
        self._mark_dirty()
        self.statusBar().showMessage(
            f"Speech timing reconciled before Run · Timeline {duration:.1f}s · "
            f"{len(report)} repair(s)"
        )
        return report

    def _validate_authored_text_before_run(self) -> bool:
        """Block silent generation when Design-authored exact text was lost."""
        if not self.authored_text_requirements:
            return True
        missing: list[dict] = []
        for required in self.authored_text_requirements:
            content = str(required.get("content", "")).strip()
            role = str(required.get("role", ""))
            start = float(required.get("start_seconds", -1.0))
            end = float(required.get("end_seconds", -1.0))
            if not any(
                layer.content_role == role
                and layer.text.strip() == content
                and abs(layer.start_seconds - start) <= 0.01
                and abs(layer.end_seconds - end) <= 0.01
                for layer in self.text_layers
            ):
                missing.append(required)
        if not missing:
            return True
        preview = "\n".join(
            f"{item.get('start_seconds', 0):.2f}-{item.get('end_seconds', 0):.2f}s "
            f"{item.get('role', 'text')}: {str(item.get('content', ''))[:90]}"
            for item in missing[:4]
        )
        QMessageBox.critical(
            self,
            "Authored dialogue/text is missing",
            "The original Design requirement contained exact timed Dialogue, Voice-over, "
            "Lyrics or On-screen Text, but the matching Timeline layer is missing or changed.\n\n"
            "Generation has been blocked so the Studio cannot silently produce a video without "
            "the user's words. Restore the layer or Apply the Design again.\n\n" + preview,
        )
        return False

    def reject_pre_run_preview(self) -> None:
        self._mark_latest_preview_rejected()
        if (
            self.production_strategy == "incremental"
            and self.incremental_pending_end > self.incremental_pending_start
        ):
            self.incremental_batch_phase = "previewing"
        self.quality_profile = "motion_preview"
        self.preview_seed = self._new_seed(self.preview_seed)
        self.preview_ready = False
        self.accept_preview_button.setEnabled(False)
        self.reject_preview_button.setEnabled(False)
        self._start_generation("preview", 0.2, self.preview_seed, False)

    def accept_pre_run_preview(self) -> None:
        if not self.preview_ready or self.preview_seed is None:
            QMessageBox.information(self, "Preview required", "Complete a 0.2MP preview first.")
            return
        if (
            self.production_strategy == "incremental"
            and self.incremental_pending_end > self.incremental_pending_start
        ):
            # Preview contains only the new range.  Accepted output is always
            # cumulative so Program Monitor and the root master remain one
            # continuous movie; approved prior Segments are cache-reused.
            self.incremental_batch_phase = "accepting"
            self.clip_start.setValue(0.0)
            self.clip_end.setValue(self.incremental_pending_end)
            self._refresh_incremental_controls()
        self.quality_profile = "approved_final"
        quality_index = self.quality_profile_combo.findData(self.quality_profile)
        self.quality_profile_combo.blockSignals(True)
        self.quality_profile_combo.setCurrentIndex(max(0, quality_index))
        self.quality_profile_combo.blockSignals(False)
        self._start_generation(
            "accepted",
            1.0,
            self.preview_seed,
            self.settings_rtx_vsr.isChecked(),
        )

    def _start_generation(
        self,
        request_kind: str,
        megapixels: float,
        seed: int,
        enable_rtx_vsr: bool,
    ) -> None:
        # A real ComfyUI request always leaves source-only Storyboard playback.
        self.storyboard_preview_active = False
        self._reconcile_speech_timing_before_run()
        if not self._validate_authored_text_before_run():
            return
        self._read_settings_ui()
        estimate_profile = (
            "motion_preview" if request_kind == "preview" else "approved_final"
        )
        self.quality_profile = estimate_profile
        estimate = self._resource_estimate(estimate_profile)
        if not estimate.fits_disk_budget:
            QMessageBox.critical(
                self,
                "Workspace disk reserve would be exceeded",
                f"Estimated additional files: {estimate.additional_disk_bytes / 1024**3:.2f} GB\n"
                f"Free space: {estimate.free_disk_bytes / 1024**3:.1f} GB\n"
                f"Protected reserve: {estimate.reserve_disk_bytes / 1024**3:.1f} GB\n\n"
                "Free disk space or lower the reserve in Settings. Existing approved "
                "Shot Takes have not been changed.",
            )
            return
        speech_layers = self._speech_layers_for_tts()
        if (
            speech_layers
            and self.render_settings.dialogue_tts_engine == "voxcpm2_local"
            and not self._require_voxcpm_model(notify=True)
        ):
            return
        if (
            speech_layers
            and self.render_settings.dialogue_tts_engine == "qwen3_tts_local"
            and not self._require_qwen3_tts_model(notify=True)
        ):
            return
        if self.render_settings.dialogue_tts_engine == "h3_native":
            self._use_h3_native_dialogue()
        authored_asset = (
            self._ensure_timeline_tts_asset()
            if speech_layers and self.render_settings.dialogue_tts_engine != "h3_native"
            else None
        )
        if (
            speech_layers
            and self.render_settings.dialogue_tts_engine != "h3_native"
            and authored_asset is None
        ):
            QMessageBox.critical(
                self,
                "No Audio reference slot for authored TTS",
                "Qwen3-TTS/VoxCPM2/Edge TTS needs one free physical Audio slot. Clear one Media Pool "
                "Audio slot, or select MiniMax H3 Native Dialogue (Ori).",
            )
            return
        if authored_asset is not None:
            self._activate_authored_speech_reference(authored_asset)
            expected_signature = self._timeline_tts_signature()
            if (
                self.timeline_tts_stale
                or self._stored_tts_signature(authored_asset) != expected_signature
            ):
                resume = {
                    "request_kind": request_kind,
                    "megapixels": megapixels,
                    "seed": seed,
                    "enable_rtx_vsr": enable_rtx_vsr,
                }
                if self._start_timeline_tts_regeneration(resume):
                    return
        if self.design_media_runner and self.design_media_runner.is_running():
            QMessageBox.information(
                self,
                "Design media running",
                "Wait for the AI Design reference images to finish first.",
            )
            return
        if (
            self.media_regeneration_runner
            and self.media_regeneration_runner.is_running()
        ):
            QMessageBox.information(
                self,
                "Reference regeneration running",
                "Wait for the Media Pool Z-Image regeneration to finish first.",
            )
            return
        if self.design_tts_runner and self.design_tts_runner.is_running():
            QMessageBox.information(
                self,
                "Mandarin TTS running",
                "Wait for the exact authored speech WAV to finish first.",
            )
            return
        if self.submit_runner and self.submit_runner.is_running():
            QMessageBox.information(self, "Generation running", "The current ComfyUI job is still running.")
            return
        is_smart_render = False
        segment_count = 1
        try:
            self._read_settings_ui()
            self.generate_prompt(interactive=False)
            duration = self.clip_end.value() - self.clip_start.value()
            is_smart_render = duration > MAX_NATIVE_SECONDS + 1e-6
            if is_smart_render:
                job_path, segment_count = self._build_smart_render_job(
                    request_kind=request_kind,
                    megapixels=megapixels,
                    seed=seed,
                    enable_rtx_vsr=enable_rtx_vsr,
                )
                smart_job = json.loads(job_path.read_text(encoding="utf-8"))
                smart_media = [
                    item for item in (smart_job.get("media") or [])
                    if isinstance(item, dict)
                ]
                for segment in smart_job.get("segments") or []:
                    continuity = segment.get("continuity") or {}
                    runtime_ids = (
                        {str(continuity.get("loader_node_id"))}
                        if continuity.get("loader_node_id")
                        else set()
                    )
                    validate_portable_media_manifest(
                        segment.get("workflow") or {},
                        smart_media,
                        runtime_loader_node_ids=runtime_ids,
                    )
            else:
                compiled, assets = self._compiled_job(
                    megapixels=megapixels,
                    seed=seed,
                    enable_rtx_vsr=enable_rtx_vsr,
                )
                media = media_upload_manifest(assets)
                patch_media_upload_names(compiled, media)
                validate_portable_media_manifest(compiled, media)
                workspace = self._ensure_project_workspace()
                render_jobs = workspace / "project" / "render_jobs"
                render_jobs.mkdir(parents=True, exist_ok=True)
                job_path = render_jobs / (
                    f"native_{request_kind}_{seed}_{time.time_ns()}.job.json"
                )
                job = {
                    "action": "queue",
                    "server": self.server_url.text().strip(),
                    "workflow": compiled,
                    "media": media,
                    "wait_for_completion": True,
                    "history_poll_interval": self.render_settings.history_poll_interval,
                    "generation_timeout": self.render_settings.generation_timeout,
                    "http_timeout": self.render_settings.http_request_timeout,
                    "download_dir": str(
                        workspace / "cache" / "generated_outputs" / request_kind / str(seed)
                    ),
                    "request_kind": request_kind,
                    "seed": seed,
                    "megapixels": megapixels,
                    "target_duration_seconds": duration,
                    "progress_shots": self._progress_shot_rows(
                        self.clip_start.value(), self.clip_end.value()
                    ),
                }
                job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "Queue error", str(exc))
            return
        runner = JsonLineProcess(self, "comfy-submit")
        runner.message.connect(self._generation_message)
        runner.finished.connect(self._generation_finished)
        self.submit_runner = runner
        self.submit_result = {}
        self.submit_request_kind = request_kind
        self.active_generation_started_at = time.monotonic()
        self.active_generation_profile = estimate_profile
        self.active_generation_duration_seconds = duration
        self.active_generation_job_path = job_path.resolve()
        if not is_smart_render:
            for segment in self._planned_render_segments():
                self.render_runtime_status[segment.segment_id] = "running"
            self._refresh_render_status_bar()
        self.queue_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.accept_preview_button.setEnabled(False)
        self.reject_preview_button.setEnabled(False)
        self.project_storage_button.setEnabled(False)
        self._refresh_incremental_controls()
        self.queue_button.setText("GENERATING…")
        label = {
            "preview": "0.2MP preview without upscaling",
            "accepted": "accepted 1.0MP render",
        }.get(request_kind, f"{megapixels:g}MP final render")
        if is_smart_render:
            label += f" · Smart Long Render · {segment_count} hidden segments"
        self.statusBar().showMessage(f"Submitting {label} · seed {seed}")
        example_folder = self._ensure_example_work_dir()
        self.statusBar().showMessage(
            f"Submitting {label} · seed {seed} · output → {example_folder}"
        )
        self.generation_previous_monitor = self.monitor_display_stack.currentWidget()
        self.generation_overlay.start(f"ComfyUI running · {label}")
        try:
            try:
                progress_job = json.loads(job_path.read_text(encoding="utf-8"))
            except Exception:
                progress_job = {}
            progress_rows = list(progress_job.get("progress_shots") or [])
            total_shots = len(progress_rows) or max(1, segment_count)
            total_weight = sum(
                max(0.0, float(row.get("duration_seconds", 0.0)))
                for row in progress_rows if isinstance(row, dict)
            ) or max(0.0, duration)
            self.generation_overlay.set_progress(
                completed_shots=0,
                total_shots=total_shots,
                completed_weight_seconds=0.0,
                total_weight_seconds=total_weight,
                active_shots=(
                    [str(row.get("shot_id", "")) for row in progress_rows]
                    if not is_smart_render else []
                ),
            )
            started = runner.start(
                str(self.runtime.python),
                [
                    str(
                        PROJECT_ROOT
                        / ("smart_render_worker.py" if is_smart_render else "comfy_submit_worker.py")
                    ),
                    str(job_path),
                ],
            )
            if not started:
                raise RuntimeError("ComfyUI worker is still stopping")
        except Exception as exc:
            self.generation_overlay.stop()
            self._restore_monitor_after_generation()
            self.queue_button.setEnabled(True)
            self.queue_button.setText("RUN+QUEUE")
            self.preview_button.setEnabled(True)
            self.project_storage_button.setEnabled(True)
            self.submit_runner = None
            for segment_id, status in list(self.render_runtime_status.items()):
                if status == "running":
                    self.render_runtime_status.pop(segment_id, None)
            self._refresh_render_status_bar()
            self._refresh_incremental_controls()
            runner.deleteLater()
            QMessageBox.critical(self, "ComfyUI worker failed", str(exc))

    def _generation_message(self, payload: dict) -> None:
        if payload.get("progress"):
            progress = str(payload["progress"])
            self.statusBar().showMessage(progress)
            self.generation_overlay.set_message(progress)
        render_progress = payload.get("render_progress")
        if isinstance(render_progress, dict):
            active_shots = (
                list(render_progress.get("current_shot_ids") or [])
                if str(render_progress.get("stage", "")).lower() == "running"
                else []
            )
            self.generation_overlay.set_progress(
                completed_shots=int(render_progress.get("completed_shots", 0)),
                total_shots=int(render_progress.get("total_shots", 0)),
                completed_weight_seconds=float(
                    render_progress.get("completed_weight_seconds", 0.0)
                ),
                total_weight_seconds=float(
                    render_progress.get("total_weight_seconds", 0.0)
                ),
                active_shots=active_shots,
            )
        segment_status = payload.get("segment_status")
        if isinstance(segment_status, dict):
            segment_id = str(segment_status.get("segment_id", ""))
            status = str(segment_status.get("status", "")).lower()
            if segment_id:
                if status in {"running", "failed"}:
                    self.render_runtime_status[segment_id] = status
                elif status in {"reusable", "cached", "complete", "completed"}:
                    self.render_runtime_status.pop(segment_id, None)
                    if self.submit_request_kind != "preview":
                        self.render_dirty_segment_ids.discard(segment_id)
                self._refresh_render_status_bar()
        if isinstance(payload.get("segment_completed"), dict):
            self._show_render_segment_preview(dict(payload["segment_completed"]))
        if isinstance(payload.get("partial_manifest"), dict):
            self.smart_render_manifest = dict(payload["partial_manifest"])
            cache_key = "preview" if self.submit_request_kind == "preview" else "production"
            self.smart_render_manifests[cache_key] = self.smart_render_manifest
            if cache_key == "production":
                for row in self.smart_render_manifest.get("segments", []):
                    if not isinstance(row, dict):
                        continue
                    segment_id = str(row.get("segment_id", ""))
                    status = str(row.get("status", "")).lower()
                    if status in {"cached", "complete", "completed", "reusable"}:
                        self.render_dirty_segment_ids.discard(segment_id)
                        self.render_runtime_status.pop(segment_id, None)
                    elif status == "failed":
                        self.render_runtime_status[segment_id] = "failed"
            self._refresh_render_status_bar()
            self._mark_dirty()
            try:
                self._checkpoint_smart_render_state()
            except OSError as exc:
                # Keep ComfyUI running, but expose that this particular
                # checkpoint could not be made resumable.
                self.statusBar().showMessage(
                    f"Smart Render checkpoint could not be saved: {exc}"
                )
        if payload.get("queued") or payload.get("error") or payload.get("completed"):
            self.submit_result = payload

    def _show_render_segment_preview(self, segment: dict) -> None:
        """Play each completed Shot unit immediately while the next one renders."""
        path = Path(str(segment.get("output_path", "")))
        if not path.is_file() or media_type_for_path(path) != "video":
            return
        render_start = float(segment.get("start_seconds", 0.0))
        start = float(segment.get("core_start_seconds", render_start) or render_start)
        end = float(segment.get("core_end_seconds", segment.get("end_seconds", start)) or start)
        hidden_handle = max(0.0, float(segment.get("overlap_before_seconds", 0.0)))
        shot_ids = ", ".join(str(value) for value in (segment.get("shot_ids") or []))
        title = f"Completed Shot preview · {start:.2f}–{end:.2f}s"
        if shot_ids:
            title += f" · {shot_ids}"
        self.generated_output_label.setText(title)
        self.generated_output_label.setStyleSheet(
            "color:#65d3df; padding:2px 4px; font-weight:600;"
        )
        self.generated_playback_path = path.resolve()
        self.generated_output_timeline_start = start
        self.generated_player.stop()
        self.generated_player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self.generated_player.setPosition(round(hidden_handle * 1000.0))
        self.generated_monitor_stack.setCurrentWidget(self.generated_video_widget)
        self.monitor_display_stack.setCurrentWidget(self.monitor_compare_splitter)
        self.generated_player.play()
        self.generation_overlay.set_message(
            f"{title}\nContinuing Smart Render…"
        )
        self.generation_overlay.raise_()

    def _apply_incremental_generation_success(
        self,
        kind: str,
        seed: int | None,
        shown: bool,
    ) -> None:
        """Advance a batch only after its durable output is visible."""
        if not shown:
            return
        if kind == "preview":
            if seed is not None:
                self.preview_seed = int(seed)
            self.preview_ready = True
            if (
                self.production_strategy == "incremental"
                and self.incremental_pending_end > self.incremental_pending_start
            ):
                self.incremental_batch_phase = "preview_ready"
            return
        if (
            self.production_strategy == "incremental"
            and self.incremental_batch_phase == "accepting"
            and self.incremental_pending_end > self.incremental_pending_start
        ):
            self.incremental_approved_horizon = min(
                self._timeline_duration_seconds(),
                self.incremental_pending_end,
            )
            self.incremental_pending_start = 0.0
            self.incremental_pending_end = 0.0
            self.incremental_batch_phase = ""
        self.preview_ready = False

    def _generation_finished(self, exit_code: int, log: str) -> None:
        self.generation_overlay.stop()
        self.queue_button.setEnabled(True)
        self.queue_button.setText("RUN+QUEUE")
        self.preview_button.setEnabled(True)
        self.project_storage_button.setEnabled(True)
        result = self.submit_result
        if exit_code == 0 and result.get("queued") and result.get("completed"):
            prompt_id = result["queued"].get("prompt_id", "unknown")
            kind = result.get("request_kind", self.submit_request_kind)
            seed = result.get("seed")
            render_cache_root = self._render_cache_root_from_manifest(
                result.get("manifest")
                if isinstance(result.get("manifest"), dict)
                else None
            )
            if result.get("smart_render") and isinstance(result.get("manifest"), dict):
                self.smart_render_manifest = dict(result["manifest"])
                cache_key = "preview" if kind == "preview" else "production"
                self.smart_render_manifests[cache_key] = self.smart_render_manifest
                if cache_key == "production":
                    for row in self.smart_render_manifest.get("segments", []):
                        segment_id = str(row.get("segment_id", ""))
                        if segment_id and str(row.get("status", "")).lower() in {
                            "cached", "complete", "completed", "reusable",
                        }:
                            self.render_dirty_segment_ids.discard(segment_id)
                            self.render_runtime_status.pop(segment_id, None)
                self._mark_dirty()
            outputs = list(result.get("outputs") or [])
            archive_warning = ""
            try:
                outputs = self._archive_generated_outputs(outputs, kind)
            except OSError as exc:
                archive_warning = str(exc)
            result["outputs"] = outputs
            try:
                self._record_generation_takes(
                    kind,
                    int(seed) if seed is not None else None,
                    outputs,
                    result.get("manifest") if isinstance(result.get("manifest"), dict) else None,
                )
            except OSError as exc:
                archive_warning = " | ".join(
                    item for item in (archive_warning, f"Shot Take: {exc}") if item
                )
            self._make_render_manifest_portable(
                result.get("manifest")
                if isinstance(result.get("manifest"), dict)
                else None,
                outputs,
            )
            shown = self._show_generated_output(
                outputs,
                timeline_start=self.clip_start.value(),
            )
            # Persist the approval state before the automatic project snapshot
            # is written.  A reload therefore resumes the exact batch instead
            # of silently returning to an all-at-once render.
            self._apply_incremental_generation_success(
                str(kind), int(seed) if seed is not None else None, shown
            )
            if kind != "preview":
                for segment in self._planned_render_segments():
                    self.render_dirty_segment_ids.discard(segment.segment_id)
                    self.render_runtime_status.pop(segment.segment_id, None)
            else:
                for segment_id, status in list(self.render_runtime_status.items()):
                    if status == "running":
                        self.render_runtime_status.pop(segment_id, None)
            self._refresh_render_status_bar()
            project_copy = None
            if shown:
                try:
                    elapsed = max(
                        0.0,
                        time.monotonic() - self.active_generation_started_at,
                    ) if self.active_generation_started_at else 0.0
                    output_bytes = sum(
                        Path(str(item.get("local_path", ""))).stat().st_size
                        for item in outputs
                        if Path(str(item.get("local_path", ""))).is_file()
                        and media_type_for_path(Path(str(item.get("local_path", "")))) == "video"
                    )
                    if self.active_generation_profile and elapsed > 0:
                        update_resource_calibration(
                            self._ensure_project_workspace(),
                            self.active_generation_profile,
                            output_duration_seconds=max(
                                0.01, self.active_generation_duration_seconds
                            ),
                            wall_seconds=elapsed,
                            output_bytes=output_bytes,
                        )
                    project_copy = self._auto_save_example_project()
                    self._cleanup_completed_render_cache(
                        render_cache_root,
                        result.get("manifest")
                        if isinstance(result.get("manifest"), dict)
                        else None,
                    )
                    if self.active_generation_job_path:
                        self.active_generation_job_path.unlink(missing_ok=True)
                except OSError as exc:
                    archive_warning = " | ".join(
                        item for item in (archive_warning, str(exc)) if item
                    )
            else:
                self._restore_monitor_after_generation()
            if kind == "preview":
                self.preview_seed = int(seed)
                self.preview_ready = True
                self.accept_preview_button.setEnabled(True)
                self.reject_preview_button.setEnabled(True)
                if result.get("smart_render"):
                    count = len((result.get("manifest") or {}).get("segments") or [])
                    self.statusBar().showMessage(
                        f"Long preview ready · {count} segments · seed {seed}"
                    )
                else:
                    self.statusBar().showMessage(
                        f"Preview ready · seed {seed} · prompt_id {prompt_id}"
                    )
                if project_copy:
                    self.statusBar().showMessage(
                        f"Preview ready · output and project saved to {project_copy.parent}"
                    )
            else:
                self.preview_ready = False
                self.accept_preview_button.setEnabled(False)
                self.reject_preview_button.setEnabled(False)
                if result.get("smart_render"):
                    count = len((result.get("manifest") or {}).get("segments") or [])
                    self.statusBar().showMessage(
                        f"Smart Long Render completed · {count} segments · master ready"
                    )
                else:
                    self.statusBar().showMessage(f"Generation completed · prompt_id {prompt_id}")
                QMessageBox.information(
                    self,
                    "ComfyUI generation completed",
                    (
                        "Master video assembled from "
                        f"{len((result.get('manifest') or {}).get('segments') or [])} hidden segments.\n"
                        if result.get("smart_render")
                        else f"Prompt ID: {prompt_id}\n"
                    )
                    + f"Seed: {seed}\nMegapixels: {result.get('megapixels')}"
                    + (f"\nSaved project: {project_copy}" if project_copy else "")
                    + (f"\nArchive warning: {archive_warning}" if archive_warning else ""),
                )
        else:
            self._restore_monitor_after_generation()
            for segment_id, status in list(self.render_runtime_status.items()):
                if status == "running":
                    self.render_runtime_status[segment_id] = "failed"
            self._refresh_render_status_bar()
            if self.submit_request_kind == "preview" and self.preview_seed is not None:
                self.reject_preview_button.setEnabled(True)
                if self.incremental_batch_phase == "previewing":
                    self.incremental_batch_phase = "preview_failed"
            error = result.get("error") or log[-1200:] or "Unknown ComfyUI error"
            QMessageBox.critical(self, "ComfyUI generation failed", str(error))
        if self.submit_runner:
            self.submit_runner.deleteLater()
        self.submit_runner = None
        self.active_generation_started_at = 0.0
        self.active_generation_profile = ""
        self.active_generation_duration_seconds = 0.0
        self.active_generation_job_path = None
        self._refresh_incremental_controls()

    def _restore_monitor_after_generation(self) -> None:
        previous = self.generation_previous_monitor
        self.generation_previous_monitor = None
        if previous is not None and self.monitor_display_stack.indexOf(previous) >= 0:
            previous.show()
            self.monitor_display_stack.setCurrentWidget(previous)
        else:
            self.monitor_image.show()
            self.monitor_display_stack.setCurrentWidget(self.monitor_compare_splitter)

    def _generated_monitor_proxy_path(self, source: Path) -> Path | None:
        """Return a cached proxy path when Qt may stall on the production master."""
        needs_proxy = source.stat().st_size >= 100 * 1024 * 1024
        try:
            info = probe_media(source, self.runtime)
            video_stream = next(
                (
                    stream
                    for stream in info.get("streams", [])
                    if stream.get("codec_type") == "video"
                ),
                {},
            )
            width = int(video_stream.get("width") or 0)
            height = int(video_stream.get("height") or 0)
            bit_rate = int(info.get("bit_rate") or 0)
            needs_proxy = needs_proxy or width > 1920 or height > 1080 or bit_rate > 18_000_000
        except (OSError, RuntimeError, ValueError, TypeError):
            pass
        if not needs_proxy:
            return None
        stat = source.stat()
        token = hashlib.sha256(
            f"{source.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
        ).hexdigest()[:20]
        folder = CACHE_ROOT / "monitor_proxies"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{source.stem}_{token}.mp4"

    def _generated_monitor_proxy_is_valid(self, source: Path, proxy: Path) -> bool:
        """Reject interrupted proxy files before Qt tries to open them.

        MP4 writes place the ``moov`` index near the end.  If Studio closes
        while FFmpeg is still encoding, a non-empty file may remain but it is
        not playable.  Existence alone therefore cannot be used as the cache
        validity contract.
        """
        try:
            if not proxy.is_file() or proxy.stat().st_size < 1024:
                return False
            proxy_info = probe_media(proxy, self.runtime)
            proxy_streams = proxy_info.get("streams", [])
            if not any(stream.get("codec_type") == "video" for stream in proxy_streams):
                return False
            proxy_duration = float(proxy_info.get("duration") or 0.0)
            if proxy_duration <= 0.0:
                return False
            source_info = probe_media(source, self.runtime)
            source_duration = float(source_info.get("duration") or 0.0)
            if source_duration > 0.0:
                tolerance = max(1.0, min(3.0, source_duration * 0.02))
                if proxy_duration < source_duration - tolerance:
                    return False
                if proxy_duration > source_duration + tolerance:
                    return False
            return True
        except (OSError, RuntimeError, ValueError, TypeError):
            return False

    def _load_generated_player_source(self, source: Path, *, autoplay: bool) -> None:
        self.generated_playback_path = source.resolve()
        self.generated_pending_position_ms = max(
            0,
            round((self.playhead_seconds - self.generated_output_timeline_start) * 1000),
        )
        self.generated_player.stop()
        self.generated_player.setSource(QUrl.fromLocalFile(str(source)))
        self.generated_player.setPosition(self.generated_pending_position_ms)
        self.generated_monitor_stack.setCurrentWidget(self.generated_video_widget)
        self.audio_output.setMuted(True)
        self.render_timeline_at(self.playhead_seconds, force_seek=True)
        if autoplay:
            self.toggle_playback()

    def _prepare_generated_monitor_video(self, source: Path, *, autoplay: bool) -> None:
        proxy = self._generated_monitor_proxy_path(source)
        proxy_ready = bool(
            proxy is not None
            and self._generated_monitor_proxy_is_valid(source, proxy)
        )
        if proxy is None or proxy_ready:
            playback_source = proxy if proxy_ready and proxy is not None else source
            self.generated_output_label.setText(
                f"Generated output · {source.name}"
                + (" · Monitor Proxy" if playback_source != source else "")
            )
            self._load_generated_player_source(playback_source, autoplay=autoplay)
            return

        # A prior interrupted encode can leave a non-empty MP4 without its
        # moov atom.  Remove only that disposable cache entry and rebuild it.
        try:
            proxy.unlink(missing_ok=True)
        except OSError:
            pass
        working = proxy.with_name(
            f"{proxy.stem}.{os.getpid()}.building.mp4"
        )
        try:
            working.unlink(missing_ok=True)
        except OSError:
            pass

        # Keep the original master as a paused poster while FFmpeg builds a
        # lightweight editing proxy in the background. Export always continues
        # to reference generated_output_path, never this cache file.
        self.generated_pending_position_ms = max(
            0,
            round((self.playhead_seconds - self.generated_output_timeline_start) * 1000),
        )
        self.generated_player.setSource(QUrl.fromLocalFile(str(source)))
        self.generated_player.setPosition(self.generated_pending_position_ms)
        self.generated_monitor_stack.setCurrentWidget(self.generated_video_widget)
        self.audio_output.setMuted(True)
        self.render_timeline_at(self.playhead_seconds, force_seek=True)
        self.generated_proxy_source = source.resolve()
        self.generated_proxy_target = proxy.resolve()
        self.generated_proxy_working = working.resolve()
        self.generated_proxy_autoplay_pending = bool(autoplay)
        self.generated_output_label.setText(
            f"Generated output · {source.name} · Preparing Monitor Proxy…"
        )
        self.statusBar().showMessage(
            "Preparing 720p Monitor Proxy in background · original master is unchanged"
        )
        runner = JsonLineProcess(self, "generated-monitor-proxy")
        self.generated_proxy_runner = runner
        runner.finished.connect(
            lambda exit_code, log, instance=runner, expected_source=source.resolve(),
            expected_target=proxy.resolve(), expected_working=working.resolve(): self._generated_proxy_finished(
                instance,
                expected_source,
                expected_target,
                expected_working,
                exit_code,
                log,
            )
        )
        try:
            runner.start(
                str(self.runtime.ffmpeg),
                [
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(source),
                    "-vf",
                    "scale=1280:720:force_original_aspect_ratio=decrease",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-movflags",
                    "+faststart",
                    str(working),
                ],
            )
        except Exception as exc:
            self.generated_proxy_runner = None
            self.generated_proxy_working = None
            runner.deleteLater()
            try:
                working.unlink(missing_ok=True)
            except OSError:
                pass
            self.generated_proxy_autoplay_pending = False
            self.generated_output_label.setText(
                f"Generated output · {source.name} · Proxy failed"
            )
            self.statusBar().showMessage(f"Monitor Proxy could not start: {exc}")
            self._load_generated_player_source(source, autoplay=autoplay)

    def _generated_proxy_finished(
        self,
        runner: JsonLineProcess,
        expected_source: Path,
        expected_target: Path,
        expected_working: Path,
        exit_code: int,
        log: str,
    ) -> None:
        if self.generated_proxy_runner is not runner:
            try:
                expected_working.unlink(missing_ok=True)
            except OSError:
                pass
            runner.deleteLater()
            return
        self.generated_proxy_runner = None
        self.generated_proxy_working = None
        autoplay = self.generated_proxy_autoplay_pending
        self.generated_proxy_autoplay_pending = False
        runner.deleteLater()
        proxy_published = False
        if exit_code == 0 and self._generated_monitor_proxy_is_valid(
            expected_source,
            expected_working,
        ):
            try:
                os.replace(expected_working, expected_target)
                proxy_published = True
            except OSError as exc:
                log = f"{log}\nCould not publish Monitor Proxy atomically: {exc}".strip()
        if proxy_published and self.generated_output_path == expected_source:
            self.generated_output_label.setText(
                f"Generated output · {expected_source.name} · Monitor Proxy"
            )
            self.statusBar().showMessage(
                f"Monitor Proxy ready · {expected_target.name}"
            )
            self._load_generated_player_source(expected_target, autoplay=autoplay)
            return
        try:
            expected_working.unlink(missing_ok=True)
        except OSError:
            pass
        if self.generated_output_path == expected_source:
            self.generated_output_label.setText(
                f"Generated output · {expected_source.name} · Proxy failed"
            )
            self.statusBar().showMessage(
                f"Monitor Proxy failed; using original master · {log[-240:]}"
            )
            self._load_generated_player_source(expected_source, autoplay=autoplay)

    def _show_generated_output(
        self,
        outputs: list[dict],
        *,
        timeline_start: float | None = None,
        autoplay: bool = True,
    ) -> bool:
        candidates = [
            item
            for item in outputs
            if item.get("local_path") and Path(str(item["local_path"])).is_file()
        ]
        candidates.sort(
            key=lambda item: 0 if media_type_for_path(item["local_path"]) == "video" else 1
        )
        if not candidates:
            return False
        path = Path(candidates[0]["local_path"])
        kind = media_type_for_path(path)
        image_pixmap = QPixmap(str(path)) if kind == "image" else QPixmap()
        if kind not in {"video", "image"} or (kind == "image" and image_pixmap.isNull()):
            return False
        self._stop_all_timeline_media()
        self.storyboard_preview_active = False
        self.generated_output_path = path.resolve()
        self.generated_output_locked = True
        if timeline_start is not None:
            self.generated_output_timeline_start = max(0.0, float(timeline_start))
        self.generated_output_label.setText(f"Generated output · {path.name}")
        self.generated_output_label.setStyleSheet("color:#55cfdf; padding:2px 4px; font-weight:600;")
        self.export_generated_button.setEnabled(True)
        self.monitor_display_stack.setCurrentWidget(self.monitor_compare_splitter)
        if kind == "video":
            self._prepare_generated_monitor_video(path, autoplay=autoplay)
            if self.render_settings.dialogue_tts_engine == "h3_native":
                self._start_native_audio_qc(
                    path,
                    self.generated_output_timeline_start,
                )
        elif kind == "image":
            self.generated_monitor_image.setPixmap(
                image_pixmap.scaled(
                    self.generated_monitor_image.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            self.generated_monitor_stack.setCurrentWidget(self.generated_monitor_image)
        self.generation_previous_monitor = None
        self._refresh_render_status_bar()
        return True

    def test_comfyui_connection(self) -> None:
        if self.connection_runner and self.connection_runner.is_running():
            return
        self._read_settings_ui()
        job_path = CACHE_ROOT / "comfy_connection_test.json"
        job_path.write_text(
            json.dumps(
                {
                    "action": "test_connection",
                    "server": self.server_url.text().strip(),
                    "http_timeout": self.render_settings.http_request_timeout,
                }
            ),
            encoding="utf-8",
        )
        runner = JsonLineProcess(self, "comfy-connection")
        runner.message.connect(self._connection_message)
        runner.finished.connect(self._connection_finished)
        self.connection_runner = runner
        self.connection_result = {}
        self.test_connection_button.setEnabled(False)
        self.test_connection_button.setText("TESTING…")
        self.statusBar().showMessage("Testing ComfyUI connection…")
        runner.start(
            str(self.runtime.python),
            [str(PROJECT_ROOT / "comfy_submit_worker.py"), str(job_path)],
        )

    def _connection_message(self, payload: dict) -> None:
        if payload.get("connected") or payload.get("error"):
            self.connection_result = payload

    def _connection_finished(self, exit_code: int, log: str) -> None:
        self.test_connection_button.setEnabled(True)
        self.test_connection_button.setText("TEST")
        if exit_code == 0 and self.connection_result.get("connected"):
            devices = self.connection_result.get("devices") or []
            device_name = devices[0].get("name", "ComfyUI device") if devices else "ComfyUI"
            self.statusBar().showMessage(f"Connected to {device_name}")
            QMessageBox.information(self, "ComfyUI connection", f"Connection successful\n{device_name}")
        else:
            error = self.connection_result.get("error") or log[-1200:] or "Connection failed"
            self.statusBar().showMessage("ComfyUI connection failed")
            QMessageBox.critical(self, "ComfyUI connection", str(error))
        if self.connection_runner:
            self.connection_runner.deleteLater()
        self.connection_runner = None

    def queue_to_comfyui(self) -> None:
        """Queue a settings-quality render independently of preview mode.

        PREVIEW and ACCEPT retain their seed-reuse workflow through their own
        toolbar buttons. RUN+QUEUE must not be redirected by a previously
        selected Storyboard or Motion Preview state.
        """
        self.storyboard_preview_active = False
        seed = self._new_seed()
        if self.clip_end.value() - self.clip_start.value() > MAX_NATIVE_SECONDS + 1e-6:
            previous = self.smart_render_manifests.get("production", {})
            previous_seed = previous.get("master_seed")
            if isinstance(previous_seed, int):
                seed = previous_seed
        self._start_generation(
            "final",
            self.settings_megapixels.value(),
            seed,
            self.settings_rtx_vsr.isChecked(),
        )

    def _submit_message(self, payload: dict) -> None:
        if payload.get("progress"):
            self.statusBar().showMessage(payload["progress"])
        if payload.get("queued") or payload.get("error"):
            self.submit_result = payload

    def _submit_finished(self, exit_code: int, log: str) -> None:
        self.queue_button.setEnabled(True)
        self.queue_button.setText("RUN+QUEUE")
        result = self.submit_result
        if exit_code == 0 and result.get("queued"):
            prompt_id = result["queued"].get("prompt_id", "unknown")
            self.statusBar().showMessage(f"Queued in ComfyUI · prompt_id {prompt_id}")
            QMessageBox.information(self, "ComfyUI queued", f"Prompt ID: {prompt_id}")
        else:
            error = result.get("error") or log[-1200:] or "Unknown upload error"
            QMessageBox.critical(self, "ComfyUI queue failed", error)
        if self.submit_runner:
            self.submit_runner.deleteLater()
        self.submit_runner = None


_CRASH_LOG_STREAM = None


def _install_crash_logging() -> None:
    """Keep Python/native crash evidence instead of silently losing the window."""
    global _CRASH_LOG_STREAM
    try:
        CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        _CRASH_LOG_STREAM = (CACHE_ROOT / "director_crash.log").open(
            "a", encoding="utf-8", buffering=1
        )
        _CRASH_LOG_STREAM.write(
            f"\n=== session {time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"· Studio v{APP_VERSION} · project format {PROJECT_FORMAT_VERSION} ===\n"
        )
        faulthandler.enable(_CRASH_LOG_STREAM, all_threads=True)

        def report_exception(exc_type, exc_value, exc_traceback) -> None:
            traceback.print_exception(
                exc_type,
                exc_value,
                exc_traceback,
                file=_CRASH_LOG_STREAM,
            )
            sys.__excepthook__(exc_type, exc_value, exc_traceback)

        sys.excepthook = report_exception
    except OSError:
        _CRASH_LOG_STREAM = None


def main() -> int:
    _install_crash_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("MiniMax H3 Director Cut Studio")
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    window = DirectorCutStudio()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

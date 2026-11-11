"""Identity Sheet review page for Director Cut Studio.

Character Swap fails in this project for one measurable reason: the P Picture's
own head is far too small for Relay to bind the face once it is contain-fit into
the V1 frame, so H3 keeps the palette and invents a new age, face and wardrobe.
``character_identity_sheet`` measures that coverage and composes a multi-panel
sheet locally; this page is the operator's window on the same numbers the render
path uses, so a Shot can be inspected before any GPU time is spent.

The page never calls ComfyUI, LM Studio or any model.  It reads pictures from
the Media Pool, writes sheets into ``<workspace>/cache/identity_sheets`` and
leaves every Media Pool asset untouched.  ``ComfyUI-H3-Character-Sheets``
generates its sheets with an H3 still workflow; that generator is not installed
here, so the page composes from the existing artwork instead and says so.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from character_identity_sheet import (
    DEFAULT_SHEET_PRESET,
    IDENTITY_SHEET_SIDECAR_SUFFIX,
    measure_head_coverage,
    resolve_identity_sheet,
    sheet_preset_labels,
    sheet_preset_panel_roles,
)
from character_swap_engine import IDENTITY_SHEET_MIN_HEAD_COVERAGE

UPSTREAM_SHEET_NOTE = (
    "Composed locally with PIL from the Media Pool picture - no GPU, no re-painting. "
    "The upstream ComfyUI-H3-Character-Sheets workflow generates its sheets with an H3 "
    "still model; that node pack is not installed here, so 'generate' is unavailable and "
    "the same panel grammar is built from the artwork you already approved."
)


def coverage_verdict(
    coverage: float | None,
    threshold: float = IDENTITY_SHEET_MIN_HEAD_COVERAGE,
) -> str:
    """One-line operator verdict for one head-coverage measurement."""

    if coverage is None:
        return "UNMEASURABLE - the original picture will be sent as-is"
    try:
        value = float(coverage)
    except (TypeError, ValueError):
        return "UNMEASURABLE - the original picture will be sent as-is"
    percent = value * 100.0
    if value >= float(threshold):
        return (
            f"HEAD COVERS {percent:.1f}% OF THE V1 FRAME - enough for Relay; "
            "no sheet needed"
        )
    return (
        f"HEAD COVERS {percent:.1f}% OF THE V1 FRAME - below "
        f"{float(threshold) * 100.0:.0f}%; an Identity Sheet is required or the face, "
        "age and wardrobe will be invented"
    )


def _thumbnail(path: Path, side: int = 96) -> QPixmap | None:
    try:
        pixmap = QPixmap(str(path))
    except Exception:
        return None
    if pixmap.isNull():
        return None
    return pixmap.scaled(
        side,
        side,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )


class IdentitySheetPage(QWidget):
    """Measure, compose and export the identity references Character Swap sends."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        cast_rows: Iterable[dict] | None = None,
        cast_provider: Callable[[], Iterable[dict]] | None = None,
        frame_size: tuple[int, int] = (0, 0),
        output_dir: Path | str | None = None,
        enabled: bool = True,
        preset: int = DEFAULT_SHEET_PRESET,
        min_head_coverage: float = IDENTITY_SHEET_MIN_HEAD_COVERAGE,
        on_settings_changed: Callable[[bool, int], None] | None = None,
        view_sources_provider: Callable[[Path, int], dict] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("identitySheetPage")
        self.setWindowTitle("IDENTITY SHEET - MEASURE & REVIEW THE FACE RELAY CAN READ")
        self.resize(1180, 720)
        self.cast_provider = cast_provider
        self.frame_size = (int(frame_size[0] or 0), int(frame_size[1] or 0))
        self.output_dir = Path(str(output_dir)) if output_dir else None
        self.min_head_coverage = float(min_head_coverage)
        self.on_settings_changed = on_settings_changed
        # The App - not this page - owns the rule for "which sibling picture is a
        # real rear / side drawing of this character", because the render path has
        # to agree with it.  Injecting it keeps the sheet the director previews here
        # the same bytes the Job will send, instead of a preview that quietly
        # mirrors the front while the take uses the real drawing (or the reverse).
        self.view_sources_provider = view_sources_provider
        self._results: dict[str, object] = {}
        self._suppress_callbacks = False

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        header = QHBoxLayout()
        self.enabled_check = QCheckBox(
            "AUTO-COMPOSE WHEN PICTURE 1'S FACE IS TOO SMALL"
        )
        self.enabled_check.setObjectName("identitySheetEnabled")
        self.enabled_check.setChecked(bool(enabled))
        self.enabled_check.toggled.connect(self._settings_changed)
        header.addWidget(self.enabled_check)
        header.addWidget(QLabel("Layout"))
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("identitySheetPreset")
        for preset_value, preset_label in sheet_preset_labels():
            self.preset_combo.addItem(preset_label, int(preset_value))
        wanted = int(preset)
        index = self.preset_combo.findData(
            wanted if wanted in dict(sheet_preset_labels()) else int(DEFAULT_SHEET_PRESET)
        )
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
        self.preset_combo.currentIndexChanged.connect(self._settings_changed)
        header.addWidget(self.preset_combo)
        self.panel_roles_label = QLabel("")
        self.panel_roles_label.setObjectName("identitySheetPanelRoles")
        self.panel_roles_label.setWordWrap(True)
        header.addWidget(self.panel_roles_label, 1)
        root.addLayout(header)

        geometry = self.frame_size
        self.summary_label = QLabel(
            (
                f"V1 FRAME {geometry[0]}x{geometry[1]} - the reference is contain-fit "
                f"into that frame, so a head below {self.min_head_coverage * 100.0:.0f}% "
                "of it is the 'became an old man' regime."
            )
            if geometry[0] > 0 and geometry[1] > 0
            else (
                "No readable V1 plate is selected, so coverage cannot be measured - "
                "the render path sends the original picture."
            )
        )
        self.summary_label.setObjectName("identitySheetSummary")
        self.summary_label.setWordWrap(True)
        root.addWidget(self.summary_label)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        self.cast_list = QListWidget()
        self.cast_list.setObjectName("identitySheetCastList")
        self.cast_list.setIconSize(QSize(96, 96))
        self.cast_list.setSpacing(6)
        self.cast_list.currentItemChanged.connect(self._show_selected)
        left.addWidget(self.cast_list, 1)
        left_host = QWidget()
        left_host.setLayout(left)
        splitter.addWidget(left_host)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        self.preview = QLabel("Select a cast picture.")
        self.preview.setObjectName("identitySheetPreview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(420, 340)
        self.preview.setStyleSheet("QLabel{background:#14171c;border:1px solid #3a414b;}")
        right.addWidget(self.preview, 1)
        self.readout = QPlainTextEdit()
        self.readout.setObjectName("identitySheetReadout")
        self.readout.setReadOnly(True)
        self.readout.setMaximumBlockCount(400)
        right.addWidget(self.readout, 1)
        right_host = QWidget()
        right_host.setLayout(right)
        splitter.addWidget(right_host)
        splitter.setSizes([360, 820])

        actions = QHBoxLayout()
        self.measure_button = QPushButton("Measure selected")
        self.measure_button.setObjectName("identitySheetMeasure")
        self.measure_button.clicked.connect(self._measure_selected)
        actions.addWidget(self.measure_button)
        self.compose_button = QPushButton("Compose sheet")
        self.compose_button.setObjectName("identitySheetCompose")
        self.compose_button.clicked.connect(self._compose_selected)
        actions.addWidget(self.compose_button)
        self.compose_all_button = QPushButton("Compose all that need it")
        self.compose_all_button.setObjectName("identitySheetComposeAll")
        self.compose_all_button.clicked.connect(self._compose_all)
        actions.addWidget(self.compose_all_button)
        self.export_button = QPushButton("Export sheet…")
        self.export_button.setObjectName("identitySheetExport")
        self.export_button.clicked.connect(self._export_sheet)
        actions.addWidget(self.export_button)
        self.folder_button = QPushButton("Open sheet folder")
        self.folder_button.setObjectName("identitySheetFolder")
        self.folder_button.clicked.connect(self._open_folder)
        actions.addWidget(self.folder_button)
        actions.addStretch(1)
        self.status_label = QLabel(UPSTREAM_SHEET_NOTE)
        self.status_label.setObjectName("identitySheetStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setMaximumWidth(520)
        actions.addWidget(self.status_label)
        root.addLayout(actions)

        self._rebuild_roles()
        self._rebuild_rows(list(cast_rows or []))

    # ---------------------------------------------------------------- plumbing

    def set_settings(self, enabled: bool, preset: int) -> None:
        """Mirror a change made on the Design page without echoing it back."""

        wanted_preset = int(preset)
        if self.preset_combo.findData(wanted_preset) < 0:
            wanted_preset = int(DEFAULT_SHEET_PRESET)
        self._suppress_callbacks = True
        try:
            self.enabled_check.setChecked(bool(enabled))
            index = self.preset_combo.findData(wanted_preset)
            if index >= 0 and self.preset_combo.currentIndex() != index:
                self.preset_combo.setCurrentIndex(index)
        finally:
            self._suppress_callbacks = False
        self._rebuild_roles()

    def refresh(self) -> None:
        """Re-read the Media Pool so new cast pictures appear immediately."""

        if self.cast_provider is not None:
            try:
                self._rebuild_rows(list(self.cast_provider()))
            except Exception as error:
                self._status(f"Could not re-read the Media Pool: {error}")

    def selected_row(self) -> dict | None:
        item = self.cast_list.currentItem()
        if item is None:
            return None
        row = item.data(Qt.UserRole)
        return row if isinstance(row, dict) else None

    def _rebuild_rows(self, rows: list[dict]) -> None:
        previous = str(
            (self.selected_row() or {}).get("media_id", "")
        )
        self.cast_list.blockSignals(True)
        self.cast_list.clear()
        for row in rows:
            if not isinstance(row, dict):
                continue
            path = Path(str(row.get("path", "") or ""))
            if not path.is_file():
                continue
            media_id = str(row.get("media_id", "") or path.stem)
            item = QListWidgetItem(
                f"{media_id} · {Path(str(row.get('filename', '') or path.name)).name}"
            )
            item.setData(Qt.UserRole, {"media_id": media_id, "path": path})
            item.setToolTip(str(path))
            thumb = _thumbnail(path)
            if thumb is not None:
                item.setIcon(QIcon(thumb))
            self.cast_list.addItem(item)
            if media_id == previous:
                self.cast_list.setCurrentItem(item)
        self.cast_list.blockSignals(False)
        if self.cast_list.count() and self.cast_list.currentRow() < 0:
            self.cast_list.setCurrentRow(0)
        self._show_selected(None, None)

    def _rebuild_roles(self) -> None:
        preset = self.preset_combo.currentData()
        try:
            roles = sheet_preset_panel_roles(int(preset))
        except Exception:
            roles = []
        rows = [" · ".join(roles)]
        if any("[rear view]" in row or "[side view]" in row for row in roles):
            # The layout asked for an angle the source picture may not have, so the
            # page says how to give it one rather than leaving the director to guess
            # why the rear panel is still a mirror.
            rows.append(
                "Real angles: put a rear / side drawing of the same character in the "
                "same Media Pool folder, same asset id, view in the file name "
                "(rear / back / behind, side / profile) - Compose sheet then cuts that "
                "panel from the real drawing. Without it the panel stays invented and "
                "the readout says so."
            )
        self.panel_roles_label.setText("\n".join(rows))

    def _settings_changed(self, _value: int = 0) -> None:
        self._rebuild_roles()
        if self._suppress_callbacks or self.on_settings_changed is None:
            return
        raw_preset = self.preset_combo.currentData()
        try:
            preset = int(raw_preset)
        except (TypeError, ValueError):
            preset = int(DEFAULT_SHEET_PRESET)
        try:
            self.on_settings_changed(bool(self.enabled_check.isChecked()), preset)
        except Exception as error:
            self._status(f"Setting not stored: {error}")

    def _target_aspect(self) -> tuple[int, int] | None:
        width, height = self.frame_size
        return (width, height) if width > 0 and height > 0 else None

    def _status(self, message: str) -> None:
        self.status_label.setText(str(message))

    # ------------------------------------------------------------ measurements

    def _coverage_for(self, row: dict) -> float | None:
        width, height = self.frame_size
        try:
            return measure_head_coverage(Path(str(row["path"])), width, height)
        except Exception:
            return None

    def _compose_for(self, row: dict, *, force: bool = False):
        if self.output_dir is None:
            return None
        try:
            preset = int(self.preset_combo.currentData() or DEFAULT_SHEET_PRESET)
        except (TypeError, ValueError):
            preset = int(DEFAULT_SHEET_PRESET)
        path = Path(str(row["path"]))
        try:
            view_sources = None
            if self.view_sources_provider is not None:
                # An empty mapping is the honest answer for "this Project only has
                # front artwork", and it composes the pre-round-69 sheet.
                view_sources = (
                    self.view_sources_provider(path, preset) or None
                )
        except Exception as error:
            self._status(f"View artwork not read for {row.get('media_id', '?')}: {error}")
            view_sources = None
        try:
            return resolve_identity_sheet(
                path,
                self.output_dir,
                preset=preset,
                force=force,
                target_aspect=self._target_aspect(),
                view_sources=view_sources,
            )
        except Exception as error:
            self._status(f"Composition failed for {row.get('media_id', '?')}: {error}")
            return None

    def _show_selected(self, _current=None, _previous=None) -> None:
        row = self.selected_row()
        if row is None:
            self.preview.setText("Select a cast picture.")
            self.readout.setPlainText("")
            return
        path = Path(str(row["path"]))
        coverage = self._coverage_for(row)
        self._results[str(row["media_id"])] = {"coverage": coverage}
        thumb = _thumbnail(path, side=max(self.preview.width(), 420))
        if thumb is not None:
            self.preview.setPixmap(thumb)
        else:
            self.preview.setText(path.name)
        lines = [
            f"{row['media_id']} · {path.name}",
            f"source picture {path.stat().st_size / 1024:.0f} KB"
            if path.exists()
            else "source picture missing",
            coverage_verdict(coverage, self.min_head_coverage),
        ]
        sidecar = Path(str(path) + IDENTITY_SHEET_SIDECAR_SUFFIX)
        lines.append(
            f"a sheet already sits beside this picture: {sidecar.name}"
            if sidecar.is_file()
            else "no sheet beside this picture yet (the render path composes into cache)"
        )
        lines.append("")
        lines.append(UPSTREAM_SHEET_NOTE)
        self.readout.setPlainText("\n".join(lines))

    def _measure_selected(self) -> None:
        row = self.selected_row()
        if row is None:
            self._status("Select a cast picture first.")
            return
        coverage = self._coverage_for(row)
        self._show_selected()
        self._status(f"{row['media_id']} · {coverage_verdict(coverage, self.min_head_coverage)}")

    def _compose_selected(self) -> None:
        row = self.selected_row()
        if row is None:
            self._status("Select a cast picture first.")
            return
        result = self._compose_for(row, force=True)
        self._present_result(row, result)

    def _compose_all(self) -> None:
        width, height = self.frame_size
        if width <= 0 or height <= 0:
            self._status("No readable V1 frame, so nothing can be measured.")
            return
        done: list[str] = []
        for index in range(self.cast_list.count()):
            item = self.cast_list.item(index)
            row = item.data(Qt.UserRole) if item is not None else None
            if not isinstance(row, dict):
                continue
            coverage = self._coverage_for(row)
            if coverage is None or coverage >= self.min_head_coverage:
                continue
            result = self._compose_for(row, force=True)
            if result is not None and getattr(result, "ok", False):
                done.append(str(row["media_id"]))
                item.setText(
                    f"{row['media_id']} · sheet head "
                    f"{float(getattr(result, 'head_coverage', 0.0) or 0.0) * 100.0:.0f}%"
                )
        self._status(
            ("composed sheets for " + ", ".join(done)) if done
            else "no cast picture needed a sheet at this layout"
        )

    def _present_result(self, row: dict, result) -> None:
        if result is None:
            self._status(f"{row['media_id']}: nothing composed.")
            return
        sheet = Path(str(getattr(result, "sheet_path", "") or ""))
        if not bool(getattr(result, "ok", False)) or not sheet.is_file():
            self._status(
                f"{row['media_id']}: {getattr(result, 'reason', 'not composed')}"
            )
            return
        pixmap = _thumbnail(sheet, side=max(self.preview.width(), 420))
        if pixmap is not None:
            self.preview.setPixmap(pixmap)
        item = self.cast_list.currentItem()
        if item is not None:
            item.setText(
                f"{row['media_id']} · sheet head "
                f"{float(getattr(result, 'head_coverage', 0.0) or 0.0) * 100.0:.0f}%"
            )
        lines = [
            f"{row['media_id']} → {sheet.name}",
            f"canvas {getattr(result, 'width', 0)}x{getattr(result, 'height', 0)} "
            f"· layout {getattr(result, 'preset_label', '')}",
            coverage_verdict(
                float(getattr(result, "head_coverage", 0.0) or 0.0),
                self.min_head_coverage,
            ),
            "",
        ]
        for panel in list(getattr(result, "panels", None) or []):
            # A parenthesised conditional cannot sit next to a string literal, so
            # the row is assembled from named parts.  ``view`` says which angle
            # the panel holds and ``view_source`` says whether the pixels are the
            # director's own rear/side drawing or artwork the sheet had to
            # invent; both are empty on every layout that predates round 69.
            panel_row = (
                f"panel {getattr(panel, 'slot', '')} = {getattr(panel, 'role', '')}"
                f"{' (mirrored)' if getattr(panel, 'mirrored', False) else ''}"
            )
            if getattr(panel, "view", ""):
                panel_row += f" [{getattr(panel, 'view', '')} view]"
            if getattr(panel, "view_source", ""):
                panel_row += f" from {getattr(panel, 'view_source', '')}"
            panel_row += f" · rect {getattr(panel, 'rect', [])}"
            lines.append(panel_row)
        dropped = list(getattr(result, "dropped_slots", None) or [])
        if dropped:
            lines.append(f"dropped panels (too small to condition anything): {', '.join(dropped)}")
        for note in list(getattr(result, "notes", None) or []):
            lines.append(f"note: {note}")
        self.readout.setPlainText("\n".join(lines))
        self._status(f"{row['media_id']} sheet composed · {sheet}")

    # ---------------------------------------------------------------- exports

    def _export_sheet(self) -> None:
        row = self.selected_row()
        if row is None:
            self._status("Select a cast picture first.")
            return
        result = self._compose_for(row, force=True)
        sheet = Path(str(getattr(result, "sheet_path", "") or "")) if result else Path("")
        if not sheet.is_file():
            self._status(f"{row['media_id']}: nothing to export.")
            return
        try:
            destination, _ = QFileDialog.getSaveFileName(
                self,
                "EXPORT IDENTITY SHEET",
                f"{row['media_id']}_identity_sheet.png",
                "PNG image (*.png)",
            )
        except Exception:
            destination = ""
        if not destination:
            return
        try:
            Path(destination).write_bytes(sheet.read_bytes())
        except OSError as error:
            QMessageBox.warning(self, "EXPORT", f"Could not write the sheet:\n{error}")
            return
        self._status(f"exported {row['media_id']} sheet → {destination}")

    def _open_folder(self) -> None:
        if self.output_dir is None:
            return
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            os.startfile(str(self.output_dir))  # Windows only
        except Exception as error:
            self._status(f"Could not open {self.output_dir}: {error}")

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        parent = self.parent()
        reset = getattr(parent, "note_identity_sheet_page_closed", None)
        if callable(reset):
            try:
                reset(self)
            except Exception:
                pass
        super().closeEvent(event)

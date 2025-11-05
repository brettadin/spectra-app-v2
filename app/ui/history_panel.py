"""History panel: displays knowledge log entries with detail view.

This panel provides a table and detail pane for browsing the knowledge log
history.
"""
from __future__ import annotations

from typing import Optional

from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()


# Get Signal compatible with both PySide6 and PyQt6
Signal = getattr(QtCore, "Signal", None)  # type: ignore[attr-defined]
if Signal is None:
    Signal = getattr(QtCore, "pyqtSignal")  # type: ignore[attr-defined]


class HistoryPanel(QtWidgets.QWidget):
    """Standalone panel for history/knowledge log.

    Exposes public attributes to preserve main window behavior:
      - history_table (QTableWidget)
      - history_detail (QPlainTextEdit)
      - history_filter (QLineEdit)
      - toolbar (QToolBar)

    Signals:
      - filterTextChanged(str): Emitted when the filter text changes
      - refreshRequested(): Emitted when user clicks Refresh
      - copyRequested(list[int]): Emitted with selected row indices
      - exportRequested(list[int]): Emitted with selected row indices
    """

    # Class-level signal definitions
    filterTextChanged = Signal(str)  # type: ignore[misc]
    refreshRequested = Signal()  # type: ignore[misc]
    copyRequested = Signal(list)  # type: ignore[misc]
    exportRequested = Signal(list)  # type: ignore[misc]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.history_table: QtWidgets.QTableWidget
        self.history_detail: QtWidgets.QPlainTextEdit
        self.history_filter: QtWidgets.QLineEdit
        self.toolbar: QtWidgets.QToolBar
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Top: filter + toolbar
        top_row = QtWidgets.QHBoxLayout()
        self.history_filter = QtWidgets.QLineEdit()
        self.history_filter.setPlaceholderText("Filter history…")
        self.history_filter.setClearButtonEnabled(True)
        self.history_filter.textChanged.connect(self.filterTextChanged.emit)
        top_row.addWidget(self.history_filter, 1)

        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.setIconSize(QtCore.QSize(16, 16))

        refresh_action = QtGui.QAction(self)
        refresh_action.setText("Refresh")
        try:
            refresh_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload))
        except Exception:
            pass
        refresh_action.setToolTip("Reload history entries")
        refresh_action.triggered.connect(self.refreshRequested.emit)
        self.toolbar.addAction(refresh_action)

        copy_action = QtGui.QAction(self)
        copy_action.setText("Copy")
        try:
            copy_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton))
        except Exception:
            pass
        copy_action.setToolTip("Copy selected entries to clipboard")
        copy_action.triggered.connect(self._emit_copy_requested)
        self.toolbar.addAction(copy_action)

        export_action = QtGui.QAction(self)
        export_action.setText("Export…")
        try:
            export_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton))
        except Exception:
            pass
        export_action.setToolTip("Export selected entries to a Markdown file")
        export_action.triggered.connect(self._emit_export_requested)
        self.toolbar.addAction(export_action)

        top_row.addWidget(self.toolbar)
        layout.addLayout(top_row)

        self.history_table = QtWidgets.QTableWidget(0, 3)
        self.history_table.setHorizontalHeaderLabels(["When", "Component", "Summary"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.history_table)

        self.history_detail = QtWidgets.QPlainTextEdit(readOnly=True)
        layout.addWidget(self.history_detail, 1)

    def _selected_rows(self) -> list[int]:
        selection = self.history_table.selectionModel()
        if not selection:
            return []
        # Return unique selected row indices
        rows = sorted({index.row() for index in selection.selectedRows()})
        return rows

    def _emit_copy_requested(self) -> None:
        rows = self._selected_rows()
        if not rows and self.history_table.rowCount() > 0:
            # If nothing is selected, default to the first row for convenience
            rows = [0]
        self.copyRequested.emit(rows)

    def _emit_export_requested(self) -> None:
        rows = self._selected_rows()
        if not rows and self.history_table.rowCount() > 0:
            rows = [0]
        self.exportRequested.emit(rows)

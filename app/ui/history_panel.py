"""History panel: displays knowledge log entries with detail view.

This panel provides a table and detail pane for browsing the knowledge log
history.
"""
from __future__ import annotations

from typing import Optional

from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()


class HistoryPanel(QtWidgets.QWidget):
    """Standalone panel for history/knowledge log.

    Exposes public attributes to preserve main window behavior:
      - history_table (QTableWidget)
      - history_detail (QPlainTextEdit)
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.history_table: QtWidgets.QTableWidget
        self.history_detail: QtWidgets.QPlainTextEdit
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.history_table = QtWidgets.QTableWidget(0, 3)
        self.history_table.setHorizontalHeaderLabels(["When", "Component", "Summary"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.history_table)

        self.history_detail = QtWidgets.QPlainTextEdit(readOnly=True)
        layout.addWidget(self.history_detail, 1)

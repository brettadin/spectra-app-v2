"""Dataset panel: provides dataset filter and tree view with model.

Initial extraction focuses on moving UI widgets out of main_window while
preserving existing attribute names via handoff in the main window.
"""
from __future__ import annotations

from typing import Optional

from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()


class DatasetPanel(QtWidgets.QWidget):
    """Standalone panel for the Datasets tab.

    Exposes public attributes to allow the main window to wire handlers
    without refactoring behavior yet:
      - dataset_filter: QLineEdit
      - dataset_view: QTreeView
      - dataset_model: QStandardItemModel
      - _originals_item: QStandardItem (root group)
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.dataset_filter: QtWidgets.QLineEdit
        self.dataset_view: QtWidgets.QTreeView
        self.dataset_model: QtGui.QStandardItemModel
        self._originals_item: QtGui.QStandardItem
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Filter box
        self.dataset_filter = QtWidgets.QLineEdit()
        self.dataset_filter.setPlaceholderText("Filter datasets…")
        self.dataset_filter.setClearButtonEnabled(True)
        layout.addWidget(self.dataset_filter)

        # Tree view + model
        self.dataset_view = QtWidgets.QTreeView()
        self.dataset_view.setRootIsDecorated(True)
        self.dataset_view.setAlternatingRowColors(True)
        self.dataset_view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.dataset_view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)

        self.dataset_model = QtGui.QStandardItemModel(0, 2, self)
        self.dataset_model.setHorizontalHeaderLabels(["Dataset", "Visible"])

        # Root group: Originals
        self._originals_item = QtGui.QStandardItem("Originals")
        self._originals_item.setEditable(False)
        self.dataset_model.appendRow([self._originals_item, QtGui.QStandardItem("")])

        self.dataset_view.setModel(self.dataset_model)

        header = self.dataset_view.header()
        if hasattr(header, "setStretchLastSection"):
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.dataset_view)

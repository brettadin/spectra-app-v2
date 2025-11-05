"""Dataset panel: provides dataset filter and tree view with model.

Emits signals for user interactions that require main window coordination.
"""
from __future__ import annotations

from typing import Optional

from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()

# Get Signal/Slot compatible with both PySide6 and PyQt6
Signal = getattr(QtCore, "Signal", None)  # type: ignore[attr-defined]
if Signal is None:
    Signal = getattr(QtCore, "pyqtSignal")  # type: ignore[attr-defined]


class DatasetPanel(QtWidgets.QWidget):
    """Standalone panel for the Datasets tab.

    Signals:
      - filterTextChanged(str): Emitted when the filter text changes
      - removeRequested(list): Emitted when user requests dataset removal (indexes)
      - selectionChanged(): Emitted when the selection changes
      - clearAllRequested(): Emitted when user confirms clearing all datasets
    
    Public attributes:
      - dataset_filter: QLineEdit
      - dataset_view: QTreeView
      - dataset_model: QStandardItemModel
      - _originals_item: QStandardItem (root group)
    """

    filterTextChanged = Signal(str)
    removeRequested = Signal(list)  # list of QModelIndex
    selectionChanged = Signal()
    clearAllRequested = Signal()  # Request to clear all datasets

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

        # Wire filter to emit signal
        self.dataset_filter.textChanged.connect(self.filterTextChanged.emit)

        # Toolbar with dataset actions
        toolbar = QtWidgets.QToolBar()
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.setIconSize(QtCore.QSize(16, 16))

        # Remove Selected action
        self.remove_action = QtGui.QAction(self)
        self.remove_action.setText("Remove Selected")
        try:
            self.remove_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TrashIcon))
        except Exception:
            pass
        self.remove_action.setShortcut(QtGui.QKeySequence.StandardKey.Delete)
        self.remove_action.setToolTip("Remove selected datasets (Del)")
        self.remove_action.triggered.connect(self._on_remove_selected_clicked)
        toolbar.addAction(self.remove_action)

        # Clear All action
        self.clear_all_action = QtGui.QAction(self)
        self.clear_all_action.setText("Clear All")
        try:
            self.clear_all_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogDiscardButton))
        except Exception:
            pass
        self.clear_all_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+C"))
        self.clear_all_action.setToolTip("Remove all datasets (Ctrl+Shift+C)")
        self.clear_all_action.triggered.connect(self._on_clear_all_clicked)
        toolbar.addAction(self.clear_all_action)

        layout.addWidget(toolbar)

        # Tree view + model
        self.dataset_view = QtWidgets.QTreeView()
        self.dataset_view.setRootIsDecorated(True)
        self.dataset_view.setAlternatingRowColors(True)
        self.dataset_view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.dataset_view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)

        # Wire context menu and selection signals
        self.dataset_view.customContextMenuRequested.connect(self._on_context_menu_requested)

        self.dataset_model = QtGui.QStandardItemModel(0, 2, self)
        self.dataset_model.setHorizontalHeaderLabels(["Dataset", "Visible"])

        # Root group: Originals
        self._originals_item = QtGui.QStandardItem("Originals")
        self._originals_item.setEditable(False)
        self.dataset_model.appendRow([self._originals_item, QtGui.QStandardItem("")])

        self.dataset_view.setModel(self.dataset_model)

        # Wire selection changes
        if self.dataset_view.selectionModel() is not None:
            self.dataset_view.selectionModel().selectionChanged.connect(
                lambda: self.selectionChanged.emit()
            )

        # Add keyboard shortcut for deletion
        delete_shortcut = QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Delete, self.dataset_view)
        delete_shortcut.activated.connect(self._on_delete_shortcut)

        header = self.dataset_view.header()
        if hasattr(header, "setStretchLastSection"):
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.dataset_view)

    def _on_context_menu_requested(self, position: QtCore.QPoint) -> None:
        """Handle context menu request and show removal options."""
        if self.dataset_view is None or self.dataset_model is None:
            return

        # Get the item at the position
        index = self.dataset_view.indexAt(position)
        if not index.isValid():
            return

        # Don't show menu for the root "Originals" item
        if index.parent() == QtCore.QModelIndex():
            return

        # Get selected rows (support multi-selection)
        selected_indexes = self.dataset_view.selectionModel().selectedRows()
        if not selected_indexes:
            return

        # Filter out root items
        valid_indexes = [idx for idx in selected_indexes if idx.parent().isValid()]
        if not valid_indexes:
            return

        # Build context menu
        menu = QtWidgets.QMenu(self.dataset_view)

        if len(valid_indexes) == 1:
            remove_action = menu.addAction("Remove Dataset")
        else:
            remove_action = menu.addAction(f"Remove {len(valid_indexes)} Datasets")

        remove_action.triggered.connect(lambda: self.removeRequested.emit(valid_indexes))

        # Show menu at cursor position
        menu.exec(self.dataset_view.viewport().mapToGlobal(position))

    def _on_delete_shortcut(self) -> None:
        """Handle Delete key press."""
        if self.dataset_view is None:
            return

        selected_indexes = self.dataset_view.selectionModel().selectedRows()
        if not selected_indexes:
            return

        # Filter out the root "Originals" item
        valid_indexes = [idx for idx in selected_indexes if idx.parent().isValid()]
        if valid_indexes:
            self.removeRequested.emit(valid_indexes)

    def _on_remove_selected_clicked(self) -> None:
        """Handle 'Remove Selected' toolbar button click."""
        if self.dataset_view is None:
            return

        selected_indexes = self.dataset_view.selectionModel().selectedRows()
        if not selected_indexes:
            return

        # Filter out the root "Originals" item
        valid_indexes = [idx for idx in selected_indexes if idx.parent().isValid()]
        if valid_indexes:
            self.removeRequested.emit(valid_indexes)

    def _on_clear_all_clicked(self) -> None:
        """Handle 'Clear All' toolbar button click with confirmation."""
        if self.dataset_model is None or self._originals_item is None:
            return

        # Check if there are any datasets to remove
        if self._originals_item.rowCount() == 0:
            return

        # Show confirmation dialog
        reply = QtWidgets.QMessageBox.question(
            self,
            "Clear All Datasets",
            f"Remove all {self._originals_item.rowCount()} dataset(s)?\n\nThis cannot be undone.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.clearAllRequested.emit()

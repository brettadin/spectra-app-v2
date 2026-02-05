"""NIST Lines panel: dedicated dock for managing fetched spectral line collections.

This panel displays NIST line collections in a table with visibility checkboxes,
separate from the main Datasets. Each collection can be toggled on/off or removed
individually, and provides a "Clear All" button to remove all collections at once.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()

# Get Signal compatible with both PySide6 and PyQt6
Signal = getattr(QtCore, "Signal", None)  # type: ignore[attr-defined]
if Signal is None:
    Signal = getattr(QtCore, "pyqtSignal")  # type: ignore[attr-defined]


class NistLinesPanel(QtWidgets.QWidget):
    """Panel for managing NIST spectral line collections.

    Signals:
      - nistFetchRequested(str, float, float): Emitted when user requests NIST fetch (element, lower, upper)
      - visibilityChanged(str, bool): Emitted when a collection's visibility changes (collection_id, visible)
      - removeRequested(List[str]): Emitted when user requests removal of collection IDs
      - clearAllRequested(): Emitted when user clicks Clear All

    Public methods:
      - add_collection(collection_id, name, line_count, color): Add a new collection to the table
      - remove_collection(collection_id): Remove a collection from the table
      - clear(): Remove all collections
      - set_visible(collection_id, visible): Set visibility state for a collection
      - is_visible(collection_id): Get visibility state for a collection
      - get_collections(): Return list of all collection IDs
    """

    nistFetchRequested = Signal(str, float, float)  # element, lower, upper
    visibilityChanged = Signal(str, bool)  # collection_id, visible
    removeRequested = Signal(list)  # list of collection_ids
    clearAllRequested = Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._collection_items: Dict[str, QtGui.QStandardItem] = {}
        self._collection_colors: Dict[str, QtGui.QColor] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # NIST ASD Fetch Controls
        fetch_group = QtWidgets.QGroupBox("Fetch NIST Spectral Lines")
        fetch_layout = QtWidgets.QVBoxLayout(fetch_group)

        # Controls row
        controls_row = QtWidgets.QHBoxLayout()
        controls_row.addWidget(QtWidgets.QLabel("Element:"))

        self.element_edit = QtWidgets.QLineEdit()
        self.element_edit.setPlaceholderText("e.g., H, He, Fe")
        self.element_edit.setMaximumWidth(100)
        controls_row.addWidget(self.element_edit)

        controls_row.addWidget(QtWidgets.QLabel("Range:"))

        self.lower_spin = QtWidgets.QDoubleSpinBox()
        self.lower_spin.setRange(1.0, 1e7)
        self.lower_spin.setDecimals(3)
        self.lower_spin.setValue(400.0)
        self.lower_spin.setSuffix(" nm")
        self.lower_spin.setMaximumWidth(120)
        controls_row.addWidget(self.lower_spin)

        controls_row.addWidget(QtWidgets.QLabel("–"))

        self.upper_spin = QtWidgets.QDoubleSpinBox()
        self.upper_spin.setRange(1.0, 1e7)
        self.upper_spin.setDecimals(3)
        self.upper_spin.setValue(700.0)
        self.upper_spin.setSuffix(" nm")
        self.upper_spin.setMaximumWidth(120)
        controls_row.addWidget(self.upper_spin)

        self.fetch_button = QtWidgets.QPushButton("Fetch")
        self.fetch_button.clicked.connect(self._on_fetch_clicked)
        controls_row.addWidget(self.fetch_button)

        self.cache_button = QtWidgets.QPushButton("Clear Cache")
        self.cache_button.setToolTip("Clear all cached NIST line lists")
        controls_row.addWidget(self.cache_button)

        controls_row.addStretch(1)
        fetch_layout.addLayout(controls_row)

        # Info label
        info = QtWidgets.QLabel("Fetched lines appear in the list below with visibility controls.")
        info.setWordWrap(True)
        info.setStyleSheet("QLabel { color: #888; font-size: 10pt; padding: 4px; }")
        fetch_layout.addWidget(info)

        layout.addWidget(fetch_group)

        # Table view
        self.table_view = QtWidgets.QTreeView()
        self.table_view.setHeaderHidden(False)
        self.table_view.setRootIsDecorated(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_view.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Model with columns: Name, Lines, Visible
        self.model = QtGui.QStandardItemModel(0, 3)
        self.model.setHorizontalHeaderLabels(["Name", "Lines", "Visible"])
        self.table_view.setModel(self.model)
        
        # Wire visibility changes
        self.model.itemChanged.connect(self._on_item_changed)
        
        layout.addWidget(self.table_view, 1)

        # Button row
        button_row = QtWidgets.QHBoxLayout()
        self.remove_button = QtWidgets.QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.clear_all_button = QtWidgets.QPushButton("Clear All")
        self.clear_all_button.clicked.connect(self._on_clear_all_clicked)
        
        button_row.addWidget(self.remove_button)
        button_row.addWidget(self.clear_all_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

    def add_collection(self, collection_id: str, name: str, line_count: int, color: QtGui.QColor) -> None:
        """Add a new NIST line collection to the table."""
        if collection_id in self._collection_items:
            # Update existing
            name_item = self._collection_items[collection_id]
            name_item.setText(name)
            row = name_item.row()
            lines_item = self.model.item(row, 1)
            if lines_item:
                lines_item.setText(str(line_count))
        else:
            # Create new row
            name_item = QtGui.QStandardItem(name)
            name_item.setEditable(False)
            name_item.setData(collection_id, QtCore.Qt.ItemDataRole.UserRole)
            
            # Add color swatch
            try:
                swatch = QtGui.QPixmap(12, 12)
                swatch.fill(QtCore.Qt.GlobalColor.transparent)
                painter = QtGui.QPainter(swatch)
                try:
                    painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 180)))
                    painter.setBrush(QtGui.QBrush(color))
                    painter.drawRect(0, 0, 11, 11)
                finally:
                    painter.end()
                name_item.setData(QtGui.QIcon(swatch), QtCore.Qt.ItemDataRole.DecorationRole)
                name_item.setToolTip(f"Trace colour: {color.name()}")
            except Exception:
                pass
            
            lines_item = QtGui.QStandardItem(str(line_count))
            lines_item.setEditable(False)
            
            visible_item = QtGui.QStandardItem("")
            visible_item.setCheckable(True)
            visible_item.setEditable(False)
            visible_item.setCheckState(QtCore.Qt.CheckState.Checked)
            
            self.model.appendRow([name_item, lines_item, visible_item])
            self._collection_items[collection_id] = name_item
            self._collection_colors[collection_id] = color

    def remove_collection(self, collection_id: str) -> None:
        """Remove a collection from the table."""
        if collection_id not in self._collection_items:
            return
        
        name_item = self._collection_items[collection_id]
        row = name_item.row()
        self.model.removeRow(row)
        
        del self._collection_items[collection_id]
        self._collection_colors.pop(collection_id, None)

    def clear(self) -> None:
        """Remove all collections."""
        self.model.removeRows(0, self.model.rowCount())
        self._collection_items.clear()
        self._collection_colors.clear()

    def set_visible(self, collection_id: str, visible: bool) -> None:
        """Set visibility state for a collection."""
        if collection_id not in self._collection_items:
            return
        
        name_item = self._collection_items[collection_id]
        row = name_item.row()
        visible_item = self.model.item(row, 2)
        if visible_item:
            state = QtCore.Qt.CheckState.Checked if visible else QtCore.Qt.CheckState.Unchecked
            visible_item.setCheckState(state)

    def is_visible(self, collection_id: str) -> bool:
        """Get visibility state for a collection."""
        if collection_id not in self._collection_items:
            return False
        
        name_item = self._collection_items[collection_id]
        row = name_item.row()
        visible_item = self.model.item(row, 2)
        if visible_item:
            return visible_item.checkState() == QtCore.Qt.CheckState.Checked
        return False

    def get_collections(self) -> List[str]:
        """Return list of all collection IDs."""
        return list(self._collection_items.keys())

    def get_color(self, collection_id: str) -> Optional[QtGui.QColor]:
        """Get the assigned color for a collection."""
        return self._collection_colors.get(collection_id)

    def set_color(self, collection_id: str, color: QtGui.QColor) -> None:
        """Update the color swatch for a collection."""
        item = self._collection_items.get(collection_id)
        if item is None:
            return
        try:
            swatch = QtGui.QPixmap(12, 12)
            swatch.fill(QtCore.Qt.GlobalColor.transparent)
            painter = QtGui.QPainter(swatch)
            try:
                painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 180)))
                painter.setBrush(QtGui.QBrush(color))
                painter.drawRect(0, 0, 11, 11)
            finally:
                painter.end()
            item.setData(QtGui.QIcon(swatch), QtCore.Qt.ItemDataRole.DecorationRole)
            item.setToolTip(f"Trace colour: {color.name()}")
            self._collection_colors[collection_id] = color
        except Exception:
            pass

    def _on_fetch_clicked(self) -> None:
        """Handle Fetch button click."""
        element = self.element_edit.text().strip()
        lower = self.lower_spin.value()
        upper = self.upper_spin.value()
        if element:
            self.nistFetchRequested.emit(element, lower, upper)

    def _on_item_changed(self, item: QtGui.QStandardItem) -> None:
        """Handle item changes (visibility checkbox toggles)."""
        if item.column() != 2:  # Only care about visibility column
            return
        
        row = item.row()
        name_item = self.model.item(row, 0)
        if not name_item:
            return
        
        collection_id = name_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not collection_id:
            return
        
        visible = item.checkState() == QtCore.Qt.CheckState.Checked
        self.visibilityChanged.emit(collection_id, visible)

    def _on_remove_clicked(self) -> None:
        """Handle Remove Selected button click."""
        selected = self.table_view.selectionModel().selectedRows()
        if not selected:
            return
        
        collection_ids = []
        for index in selected:
            name_item = self.model.item(index.row(), 0)
            if name_item:
                cid = name_item.data(QtCore.Qt.ItemDataRole.UserRole)
                if cid:
                    collection_ids.append(cid)
        
        if collection_ids:
            self.removeRequested.emit(collection_ids)

    def _on_clear_all_clicked(self) -> None:
        """Handle Clear All button click."""
        if self.model.rowCount() == 0:
            return
        
        # Confirm with user
        reply = QtWidgets.QMessageBox.question(
            self,
            "Clear All NIST Lines",
            f"Remove all {self.model.rowCount()} NIST line collection(s)?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.clearAllRequested.emit()

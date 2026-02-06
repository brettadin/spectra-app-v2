"""Dataset panel: provides dataset filter and tree view with groups.

Emits signals for user interactions that require main window coordination.
"""
from __future__ import annotations

from typing import Optional, Dict, List

from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()

# Get Signal/Slot compatible with both PySide6 and PyQt6
Signal = getattr(QtCore, "Signal", None)  # type: ignore[attr-defined]
if Signal is None:
    Signal = getattr(QtCore, "pyqtSignal")  # type: ignore[attr-defined]


class DatasetPanel(QtWidgets.QWidget):
    """Standalone panel for the Datasets tab with grouped datasets.

    Signals:
      - filterTextChanged(str): Emitted when the filter text changes
      - removeRequested(list): Emitted when user requests dataset removal (indexes)
      - selectionChanged(): Emitted when the selection changes
      - clearAllRequested(): Emitted when user confirms clearing all datasets
      - groupVisibilityChanged(group_id, is_visible): Emitted when group visibility changes
      - createGroupRequested(name, parent_id): Emitted when user requests new group
      - moveToGroupRequested(indexes, group_id): Emitted when user wants to move datasets
      - renameGroupRequested(group_id, new_name): Emitted when user renames a group
      - deleteGroupRequested(group_id): Emitted when user deletes a group
      - normalizationLockChanged(indexes, is_locked): Emitted when user locks/unlocks normalization

    Public attributes:
      - dataset_filter: QLineEdit
      - dataset_view: QTreeView
      - dataset_model: QStandardItemModel
      - _group_items: Dict[group_id, QStandardItem] (organized by group)
    """

    filterTextChanged = Signal(str)
    removeRequested = Signal(list)  # list of QModelIndex
    selectionChanged = Signal()
    clearAllRequested = Signal()  # Request to clear all datasets
    groupVisibilityChanged = Signal(str, bool)  # group_id, is_visible
    createGroupRequested = Signal(str, str)  # name, parent_group_id (empty for root)
    moveToGroupRequested = Signal(list, str)  # list of QModelIndex, target group_id
    renameGroupRequested = Signal(str, str)  # group_id, new_name
    deleteGroupRequested = Signal(str)  # group_id
    normalizationLockChanged = Signal(list, bool)  # list of QModelIndex, is_locked

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.dataset_filter: QtWidgets.QLineEdit
        self.dataset_view: QtWidgets.QTreeView
        self.dataset_model: QtGui.QStandardItemModel
        self._group_items: Dict[str, QtGui.QStandardItem] = {}  # group_id -> QStandardItem
        self._originals_item: Optional[QtGui.QStandardItem] = None  # Compatibility - first group
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
        self.addAction(self.remove_action)  # For global shortcut

    def add_group(self, group_id: str, group_name: str, color_hint: Optional[str] = None, parent_group_id: Optional[str] = None) -> None:
        """Add a dataset group to the tree view.

        Args:
            group_id: Unique group identifier
            group_name: Display name for group
            color_hint: Optional color name (for future styling)
            parent_group_id: Optional parent group ID for hierarchical groups
        """
        # Block signals during group creation to prevent premature itemChanged emissions
        self.dataset_model.blockSignals(True)
        try:
            group_item = QtGui.QStandardItem(group_name)
            group_item.setEditable(False)
            group_item.setData(group_id, role=QtCore.Qt.ItemDataRole.UserRole)  # Store group_id

            # Add checkbox for group visibility in second column
            checkbox_item = QtGui.QStandardItem("")
            checkbox_item.setCheckable(True)
            checkbox_item.setCheckState(QtCore.Qt.CheckState.Checked)
            checkbox_item.setData(group_id, role=QtCore.Qt.ItemDataRole.UserRole)  # Store group_id

            # Connect itemChanged only once (on first group added)
            if not self._group_items:
                self.dataset_model.itemChanged.connect(self._on_item_changed)

            # Add as child of parent group if specified, otherwise add as top-level
            if parent_group_id and parent_group_id in self._group_items:
                parent_item = self._group_items[parent_group_id]
                parent_item.appendRow([group_item, checkbox_item])
            else:
                self.dataset_model.appendRow([group_item, checkbox_item])

            self._group_items[group_id] = group_item

            # Set first group as _originals_item for backward compatibility
            if self._originals_item is None:
                self._originals_item = group_item
        finally:
            self.dataset_model.blockSignals(False)

    def get_group_item(self, group_id: str) -> Optional[QtGui.QStandardItem]:
        """Get the QStandardItem for a group by ID."""
        return self._group_items.get(group_id)

    def _on_item_changed(self, item: QtGui.QStandardItem) -> None:
        """Handle checkbox state changes for group visibility."""
        # Only process checkbox items in the second column (visibility column)
        if item.column() != 1:
            return

        # Check if this is a top-level item (group checkbox) by checking if parent is None
        # QStandardItem.parent() returns None for top-level items, another QStandardItem otherwise
        if item.parent() is None:
            # This is a top-level item (group checkbox), find its group_id
            for row in range(self.dataset_model.rowCount()):
                model_item = self.dataset_model.item(row, 1)
                if model_item is item:
                    group_item = self.dataset_model.item(row, 0)
                    group_id = group_item.data(QtCore.Qt.ItemDataRole.UserRole)
                    is_visible = item.checkState() == QtCore.Qt.CheckState.Checked
                    self.groupVisibilityChanged.emit(group_id, is_visible)
                    return

    def _on_context_menu_requested(self, position: QtCore.QPoint) -> None:
        """Handle context menu request with group and dataset options."""
        if self.dataset_view is None or self.dataset_model is None:
            return

        index = self.dataset_view.indexAt(position)
        menu = QtWidgets.QMenu(self.dataset_view)
        
        # Check if clicked on empty space, a group, or a dataset
        is_group = index.isValid() and not index.parent().isValid()
        is_dataset = index.isValid() and index.parent().isValid()
        
        # Always show "New Group" option
        new_group_action = menu.addAction("New Group…")
        new_group_action.triggered.connect(lambda: self._show_new_group_dialog())
        
        if is_group:
            # Clicked on a group - show group options
            group_item = self.dataset_model.itemFromIndex(index)
            group_id = group_item.data(QtCore.Qt.ItemDataRole.UserRole)
            group_name = group_item.text()
            
            menu.addSeparator()
            
            # Rename group
            rename_action = menu.addAction(f"Rename '{group_name}'…")
            rename_action.triggered.connect(lambda: self._show_rename_group_dialog(group_id, group_name))
            
            # Create subgroup
            subgroup_action = menu.addAction("New Subgroup…")
            subgroup_action.triggered.connect(lambda: self._show_new_group_dialog(parent_group_id=group_id))
            
            # Only allow deleting custom groups (not defaults)
            if group_item.rowCount() == 0:  # Empty groups can be deleted
                delete_action = menu.addAction(f"Delete '{group_name}'")
                delete_action.triggered.connect(lambda: self.deleteGroupRequested.emit(group_id))
        
        elif is_dataset:
            # Clicked on a dataset - show dataset options
            selected_indexes = self.dataset_view.selectionModel().selectedRows()
            valid_indexes = [idx for idx in selected_indexes if idx.parent().isValid()]
            
            if valid_indexes:
                menu.addSeparator()
                
                # Remove option
                if len(valid_indexes) == 1:
                    remove_action = menu.addAction("Remove Dataset")
                else:
                    remove_action = menu.addAction(f"Remove {len(valid_indexes)} Datasets")
                remove_action.triggered.connect(lambda: self.removeRequested.emit(valid_indexes))
                
                # Move to group submenu
                move_menu = menu.addMenu("Move to Group")
                for group_id, group_item in self._group_items.items():
                    group_name = group_item.text()
                    move_action = move_menu.addAction(group_name)
                    # Capture group_id in lambda
                    move_action.triggered.connect(
                        lambda checked=False, gid=group_id: self.moveToGroupRequested.emit(valid_indexes, gid)
                    )

                # Lock/Unlock normalization
                menu.addSeparator()
                if len(valid_indexes) == 1:
                    lock_action = menu.addAction("Lock Normalization")
                    unlock_action = menu.addAction("Unlock Normalization")
                else:
                    lock_action = menu.addAction(f"Lock Normalization ({len(valid_indexes)} datasets)")
                    unlock_action = menu.addAction(f"Unlock Normalization ({len(valid_indexes)} datasets)")
                lock_action.triggered.connect(lambda: self.normalizationLockChanged.emit(valid_indexes, True))
                unlock_action.triggered.connect(lambda: self.normalizationLockChanged.emit(valid_indexes, False))

        menu.exec(self.dataset_view.viewport().mapToGlobal(position))
    
    def _show_new_group_dialog(self, parent_group_id: str = "") -> None:
        """Show dialog to create a new group."""
        name, ok = QtWidgets.QInputDialog.getText(
            self, "New Group", "Enter group name:",
            QtWidgets.QLineEdit.EchoMode.Normal, ""
        )
        if ok and name.strip():
            self.createGroupRequested.emit(name.strip(), parent_group_id)
    
    def _show_rename_group_dialog(self, group_id: str, current_name: str) -> None:
        """Show dialog to rename a group."""
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename Group", "Enter new name:",
            QtWidgets.QLineEdit.EchoMode.Normal, current_name
        )
        if ok and name.strip() and name.strip() != current_name:
            self.renameGroupRequested.emit(group_id, name.strip())

    def _on_delete_shortcut(self) -> None:
        """Handle Delete key press."""
        if self.dataset_view is None:
            return

        selected_indexes = self.dataset_view.selectionModel().selectedRows()
        if not selected_indexes:
            return

        # Filter out group items
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

        # Filter out group items
        valid_indexes = [idx for idx in selected_indexes if idx.parent().isValid()]
        if valid_indexes:
            self.removeRequested.emit(valid_indexes)

    def _on_clear_all_clicked(self) -> None:
        """Handle 'Clear All' toolbar button click with confirmation."""
        if self.dataset_model is None:
            return

        # Count total datasets across all groups
        total_count = 0
        for group_id in self._group_items:
            group_item = self._group_items[group_id]
            total_count += group_item.rowCount()

        if total_count == 0:
            return

        # Show confirmation dialog
        reply = QtWidgets.QMessageBox.question(
            self,
            "Clear All Datasets",
            f"Remove all {total_count} dataset(s) from all groups?\n\nThis cannot be undone.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.clearAllRequested.emit()

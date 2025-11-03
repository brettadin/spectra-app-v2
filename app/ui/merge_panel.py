"""Merge/Average panel: select and combine multiple datasets.

This panel provides controls for merging/averaging selected datasets from
the dataset panel.
"""
from __future__ import annotations

from typing import Optional

from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()


class MergePanel(QtWidgets.QWidget):
    """Standalone panel for merging/averaging datasets.

    Exposes public attributes to preserve main window behavior:
      - merge_only_visible (QCheckBox)
      - merge_name_edit (QLineEdit)
      - merge_preview_label (QLabel)
      - merge_average_button (QPushButton)
      - merge_status_label (QLabel)
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.merge_only_visible: QtWidgets.QCheckBox
        self.merge_name_edit: QtWidgets.QLineEdit
        self.merge_preview_label: QtWidgets.QLabel
        self.merge_average_button: QtWidgets.QPushButton
        self.merge_status_label: QtWidgets.QLabel
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Instructions
        merge_info = QtWidgets.QLabel(
            "Select multiple datasets from the Datasets panel, then merge or average them into a single spectrum."
        )
        merge_info.setWordWrap(True)
        layout.addWidget(merge_info)

        # Options
        merge_options_group = QtWidgets.QGroupBox("Options")
        merge_options_layout = QtWidgets.QVBoxLayout(merge_options_group)

        self.merge_only_visible = QtWidgets.QCheckBox("Only include visible (checked) datasets")
        self.merge_only_visible.setChecked(True)
        merge_options_layout.addWidget(self.merge_only_visible)

        layout.addWidget(merge_options_group)

        # Name for result
        merge_name_layout = QtWidgets.QHBoxLayout()
        merge_name_layout.addWidget(QtWidgets.QLabel("Result name:"))
        self.merge_name_edit = QtWidgets.QLineEdit()
        self.merge_name_edit.setPlaceholderText("(auto-generated)")
        merge_name_layout.addWidget(self.merge_name_edit, 1)
        layout.addLayout(merge_name_layout)

        # Preview info
        self.merge_preview_label = QtWidgets.QLabel("No datasets selected")
        self.merge_preview_label.setWordWrap(True)
        self.merge_preview_label.setStyleSheet("QLabel { padding: 8px; background: #2b2b2b; border-radius: 4px; }")
        layout.addWidget(self.merge_preview_label)

        # Action buttons
        merge_buttons_layout = QtWidgets.QHBoxLayout()
        self.merge_average_button = QtWidgets.QPushButton("Average Selected")
        self.merge_average_button.setEnabled(False)
        merge_buttons_layout.addWidget(self.merge_average_button)
        layout.addLayout(merge_buttons_layout)

        # Status
        self.merge_status_label = QtWidgets.QLabel("")
        self.merge_status_label.setWordWrap(True)
        layout.addWidget(self.merge_status_label)

        layout.addStretch()

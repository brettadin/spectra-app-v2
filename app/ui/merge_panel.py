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
      - merge_subtract_button (QPushButton)
    - merge_ratio_button (QPushButton)
    - merge_normalized_diff_button (QPushButton)
      - merge_status_label (QLabel)
    """

    # Attribute type annotations (class-level per PEP 526)
    merge_only_visible: QtWidgets.QCheckBox
    merge_name_edit: QtWidgets.QLineEdit
    merge_preview_label: QtWidgets.QLabel
    merge_average_button: QtWidgets.QPushButton
    merge_subtract_button: QtWidgets.QPushButton
    merge_ratio_button: QtWidgets.QPushButton
    merge_normalized_diff_button: QtWidgets.QPushButton
    merge_smooth_button: QtWidgets.QPushButton
    merge_derivative_button: QtWidgets.QPushButton
    merge_integral_button: QtWidgets.QPushButton
    merge_status_label: QtWidgets.QLabel

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Instructions
        merge_info = QtWidgets.QLabel(
            "Select datasets from the Datasets panel, then perform mathematical operations."
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
        merge_buttons_layout = QtWidgets.QGridLayout()
        
        # Row 0: Two-operand operations
        self.merge_average_button = QtWidgets.QPushButton("Average")
        self.merge_average_button.setEnabled(False)
        self.merge_average_button.setToolTip("Average multiple selected spectra")
        merge_buttons_layout.addWidget(self.merge_average_button, 0, 0)
        
        self.merge_subtract_button = QtWidgets.QPushButton("A − B")
        self.merge_subtract_button.setEnabled(False)
        self.merge_subtract_button.setToolTip("Subtract second spectrum from first (select exactly 2)")
        merge_buttons_layout.addWidget(self.merge_subtract_button, 0, 1)
        
        self.merge_ratio_button = QtWidgets.QPushButton("A / B")
        self.merge_ratio_button.setEnabled(False)
        self.merge_ratio_button.setToolTip("Divide first spectrum by second (select exactly 2)")
        merge_buttons_layout.addWidget(self.merge_ratio_button, 0, 2)
        
        self.merge_normalized_diff_button = QtWidgets.QPushButton("ND(A,B)")
        self.merge_normalized_diff_button.setEnabled(False)
        self.merge_normalized_diff_button.setToolTip("Normalized difference: (A − B) / (A + B) (select exactly 2)")
        merge_buttons_layout.addWidget(self.merge_normalized_diff_button, 0, 3)
        
        # Row 1: Single-operand operations
        self.merge_smooth_button = QtWidgets.QPushButton("Smooth")
        self.merge_smooth_button.setEnabled(False)
        self.merge_smooth_button.setToolTip("Apply smoothing filter (moving average or Savitzky-Golay)")
        merge_buttons_layout.addWidget(self.merge_smooth_button, 1, 0)
        
        self.merge_derivative_button = QtWidgets.QPushButton("d/dx")
        self.merge_derivative_button.setEnabled(False)
        self.merge_derivative_button.setToolTip("Compute first or second derivative")
        merge_buttons_layout.addWidget(self.merge_derivative_button, 1, 1)
        
        self.merge_integral_button = QtWidgets.QPushButton("∫")
        self.merge_integral_button.setEnabled(False)
        self.merge_integral_button.setToolTip("Compute cumulative integral or total area")
        merge_buttons_layout.addWidget(self.merge_integral_button, 1, 2)
        
        layout.addLayout(merge_buttons_layout)

        # Status
        self.merge_status_label = QtWidgets.QLabel("")
        self.merge_status_label.setWordWrap(True)
        layout.addWidget(self.merge_status_label)

        layout.addStretch()

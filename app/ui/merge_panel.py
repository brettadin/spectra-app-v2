"""Merge/Average panel: select and combine multiple datasets.

This panel provides controls for merging/averaging selected datasets from
the dataset panel, with optional wavelength range selection for operations.
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
      
    Range selection controls:
      - range_enabled (QCheckBox)
      - range_min_spin (QDoubleSpinBox)
      - range_max_spin (QDoubleSpinBox)
      - range_set_overlap_button (QPushButton)
      - range_set_view_button (QPushButton)
    
    Signals:
      - rangeToggled(bool): Emitted when range selection is enabled/disabled
      - rangeChanged(float, float): Emitted when range values change
      - setOverlapRequested(): Request to set range to data overlap
      - setViewRequested(): Request to set range to current view
    """

    # Signals for range selection
    rangeToggled = QtCore.Signal(bool)
    rangeChanged = QtCore.Signal(float, float)
    setOverlapRequested = QtCore.Signal()
    setViewRequested = QtCore.Signal()
    exportRangeRequested = QtCore.Signal()  # Request to export selected spectra within range

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
    # Range selection widgets
    range_enabled: QtWidgets.QCheckBox
    range_min_spin: QtWidgets.QDoubleSpinBox
    range_max_spin: QtWidgets.QDoubleSpinBox
    range_set_overlap_button: QtWidgets.QPushButton
    range_set_view_button: QtWidgets.QPushButton
    range_unit_label: QtWidgets.QLabel
    range_export_button: QtWidgets.QPushButton

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

        # Wavelength Range Selection
        range_group = QtWidgets.QGroupBox("Wavelength Range")
        range_layout = QtWidgets.QVBoxLayout(range_group)
        
        # Enable checkbox
        self.range_enabled = QtWidgets.QCheckBox("Limit to selected range")
        self.range_enabled.setToolTip(
            "When enabled, math operations only use data within the specified range.\n"
            "This is useful for comparing overlapping regions of different datasets."
        )
        range_layout.addWidget(self.range_enabled)
        
        # Range inputs
        range_inputs_layout = QtWidgets.QHBoxLayout()
        
        self.range_min_spin = QtWidgets.QDoubleSpinBox()
        self.range_min_spin.setRange(0, 100000)
        self.range_min_spin.setDecimals(2)
        self.range_min_spin.setValue(200)
        self.range_min_spin.setSuffix("")
        self.range_min_spin.setToolTip("Minimum wavelength (nm)")
        self.range_min_spin.setEnabled(False)
        
        range_inputs_layout.addWidget(QtWidgets.QLabel("Min:"))
        range_inputs_layout.addWidget(self.range_min_spin)
        
        self.range_max_spin = QtWidgets.QDoubleSpinBox()
        self.range_max_spin.setRange(0, 100000)
        self.range_max_spin.setDecimals(2)
        self.range_max_spin.setValue(800)
        self.range_max_spin.setSuffix("")
        self.range_max_spin.setToolTip("Maximum wavelength (nm)")
        self.range_max_spin.setEnabled(False)
        
        range_inputs_layout.addWidget(QtWidgets.QLabel("Max:"))
        range_inputs_layout.addWidget(self.range_max_spin)
        
        self.range_unit_label = QtWidgets.QLabel("nm")
        range_inputs_layout.addWidget(self.range_unit_label)
        
        range_layout.addLayout(range_inputs_layout)
        
        # Quick-set buttons
        range_buttons_layout = QtWidgets.QHBoxLayout()
        
        self.range_set_overlap_button = QtWidgets.QPushButton("Set to Overlap")
        self.range_set_overlap_button.setToolTip(
            "Set range to the overlapping region of all visible datasets"
        )
        self.range_set_overlap_button.setEnabled(False)
        range_buttons_layout.addWidget(self.range_set_overlap_button)
        
        self.range_set_view_button = QtWidgets.QPushButton("Set to View")
        self.range_set_view_button.setToolTip("Set range to match current plot view")
        self.range_set_view_button.setEnabled(False)
        range_buttons_layout.addWidget(self.range_set_view_button)
        
        range_layout.addLayout(range_buttons_layout)
        
        # Export range button
        self.range_export_button = QtWidgets.QPushButton("Export Range...")
        self.range_export_button.setToolTip(
            "Export selected spectra clipped to the current range"
        )
        self.range_export_button.setEnabled(False)
        range_layout.addWidget(self.range_export_button)
        
        layout.addWidget(range_group)
        
        # Wire range signals
        self.range_enabled.toggled.connect(self._on_range_toggled)
        self.range_min_spin.valueChanged.connect(self._on_range_values_changed)
        self.range_max_spin.valueChanged.connect(self._on_range_values_changed)
        self.range_set_overlap_button.clicked.connect(self.setOverlapRequested.emit)
        self.range_set_view_button.clicked.connect(self.setViewRequested.emit)
        self.range_export_button.clicked.connect(self.exportRangeRequested.emit)

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

    def _on_range_toggled(self, checked: bool) -> None:
        """Handle range enabled/disabled toggle."""
        self.range_min_spin.setEnabled(checked)
        self.range_max_spin.setEnabled(checked)
        self.range_set_overlap_button.setEnabled(checked)
        self.range_set_view_button.setEnabled(checked)
        self.range_export_button.setEnabled(checked)
        self.rangeToggled.emit(checked)

    def _on_range_values_changed(self) -> None:
        """Handle range value changes."""
        if self.range_enabled.isChecked():
            self.rangeChanged.emit(
                self.range_min_spin.value(),
                self.range_max_spin.value()
            )

    def set_range_values(self, min_nm: float, max_nm: float) -> None:
        """Set the range spinbox values programmatically (in nm)."""
        # Block signals to avoid feedback loops
        self.range_min_spin.blockSignals(True)
        self.range_max_spin.blockSignals(True)
        self.range_min_spin.setValue(min_nm)
        self.range_max_spin.setValue(max_nm)
        self.range_min_spin.blockSignals(False)
        self.range_max_spin.blockSignals(False)

    def get_range_nm(self) -> tuple[float, float] | None:
        """Get the current range in nm, or None if range selection is disabled."""
        if not self.range_enabled.isChecked():
            return None
        return (self.range_min_spin.value(), self.range_max_spin.value())

    def is_range_enabled(self) -> bool:
        """Return True if range selection is enabled."""
        return self.range_enabled.isChecked()

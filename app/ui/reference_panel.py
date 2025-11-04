"""Reference panel: NIST ASD, IR Functional Groups, and Line Shapes tabs.

This panel provides three reference data sources with a shared preview plot
and overlay toggle. Emits signals for user interactions.
"""
from __future__ import annotations

from typing import Optional

import pyqtgraph as pg
from app.qt_compat import get_qt
from app.ui.plot_pane import PlotPane

QtCore, QtGui, QtWidgets, _ = get_qt()

# Get Signal compatible with both PySide6 and PyQt6
Signal = getattr(QtCore, "Signal", None)  # type: ignore[attr-defined]
if Signal is None:
    Signal = getattr(QtCore, "pyqtSignal")  # type: ignore[attr-defined]


class ReferencePanel(QtWidgets.QWidget):
    """Standalone panel for reference data (NIST, IR, Line Shapes).

    Signals:
      - overlayToggled(bool): Emitted when overlay checkbox is toggled
      - nistFetchRequested(str, float, float): Emitted when NIST fetch is clicked
      - tabChanged(int): Emitted when reference tab changes
      - irFilterChanged(str): Emitted when IR filter text changes
    
    Public attributes:
      - reference_overlay_checkbox
      - reference_status_label
      - reference_plot (PlotWidget)
      - reference_tabs (QTabWidget)
      - nist_element_edit, nist_lower_spin, nist_upper_spin, nist_fetch_button
      - nist_collections_list
      - reference_table (for NIST lines)
      - reference_filter (for IR filter)
      - ir_table
      - ls_table (Line Shapes)
    """

    overlayToggled = Signal(bool)
    nistFetchRequested = Signal(str, float, float)  # element, lower, upper
    tabChanged = Signal(int)
    irFilterChanged = Signal(str)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.reference_overlay_checkbox: QtWidgets.QCheckBox
        self.reference_status_label: QtWidgets.QLabel
        self.reference_plot: pg.PlotWidget
        self.reference_tabs: QtWidgets.QTabWidget
        # NIST controls
        self.nist_element_edit: QtWidgets.QLineEdit
        self.nist_lower_spin: QtWidgets.QDoubleSpinBox
        self.nist_upper_spin: QtWidgets.QDoubleSpinBox
        self.nist_fetch_button: QtWidgets.QPushButton
        self.nist_collections_list: QtWidgets.QListWidget
        self.reference_table: QtWidgets.QTableWidget
        # IR controls
        self.reference_filter: QtWidgets.QLineEdit
        self.ir_table: QtWidgets.QTableWidget
        # Line Shapes
        self.ls_table: QtWidgets.QTableWidget
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Top row: overlay toggle + status
        top_row = QtWidgets.QHBoxLayout()
        self.reference_overlay_checkbox = QtWidgets.QCheckBox("Show on plot")
        self.reference_overlay_checkbox.setEnabled(False)
        # Wire overlay toggle signal
        self.reference_overlay_checkbox.toggled.connect(self.overlayToggled.emit)
        
        self.reference_status_label = QtWidgets.QLabel("")
        top_row.addWidget(self.reference_overlay_checkbox)
        top_row.addStretch(1)
        top_row.addWidget(self.reference_status_label)
        layout.addLayout(top_row)

        # Shared preview plot
        self.reference_plot: pg.PlotWidget = pg.PlotWidget()
        self.reference_plot.setLabel("bottom", "Wavelength (nm)")
        PlotPane.strip_export_from_plot_widget(self.reference_plot)
        layout.addWidget(self.reference_plot, 2)

        # Tabs within Reference
        self.reference_tabs = QtWidgets.QTabWidget()
        # Wire tab change signal
        self.reference_tabs.currentChanged.connect(self.tabChanged.emit)
        layout.addWidget(self.reference_tabs, 3)

        # --- NIST tab
        nist_tab = QtWidgets.QWidget()
        nist_layout = QtWidgets.QVBoxLayout(nist_tab)
        nist_controls = QtWidgets.QHBoxLayout()
        self.nist_element_edit = QtWidgets.QLineEdit()
        self.nist_element_edit.setPlaceholderText("Element symbol (e.g., H, He, Fe)")
        self.nist_lower_spin = QtWidgets.QDoubleSpinBox()
        self.nist_lower_spin.setRange(1.0, 1e7)
        self.nist_lower_spin.setDecimals(3)
        self.nist_lower_spin.setValue(400.0)
        self.nist_upper_spin = QtWidgets.QDoubleSpinBox()
        self.nist_upper_spin.setRange(1.0, 1e7)
        self.nist_upper_spin.setDecimals(3)
        self.nist_upper_spin.setValue(700.0)
        self.nist_fetch_button = QtWidgets.QPushButton("Fetch")
        # Wire fetch button
        self.nist_fetch_button.clicked.connect(self._on_nist_fetch_clicked)
        # Extra controls: show selected only, clear pins, cache management
        self.nist_show_selected_only = QtWidgets.QCheckBox("Show selected only")
        self.nist_clear_button = QtWidgets.QPushButton("Clear Pins")
        self.nist_cache_button = QtWidgets.QPushButton("Clear Cache")
        self.nist_cache_button.setToolTip("Clear all cached NIST line lists")
        
        for w in (
            QtWidgets.QLabel("Element:"),
            self.nist_element_edit,
            QtWidgets.QLabel("Range:"),
            self.nist_lower_spin,
            QtWidgets.QLabel("–"),
            self.nist_upper_spin,
            self.nist_fetch_button,
            self.nist_show_selected_only,
            self.nist_clear_button,
            self.nist_cache_button,
        ):
            nist_controls.addWidget(w)
        nist_controls.addStretch(1)
        nist_layout.addLayout(nist_controls)
        self.nist_collections_list = QtWidgets.QListWidget()
        nist_layout.addWidget(self.nist_collections_list, 1)
        self.reference_table = QtWidgets.QTableWidget(0, 5)
        self.reference_table.setHorizontalHeaderLabels(
            ["λ (nm)", "Ritz λ (nm)", "Intensity", "Lower", "Upper"]
        )
        self.reference_table.horizontalHeader().setStretchLastSection(True)
        nist_layout.addWidget(self.reference_table, 3)
        self.reference_tabs.addTab(nist_tab, "NIST ASD")

        # --- IR functional groups tab
        ir_tab = QtWidgets.QWidget()
        ir_layout = QtWidgets.QVBoxLayout(ir_tab)
        self.reference_filter = QtWidgets.QLineEdit()
        self.reference_filter.setPlaceholderText("Filter IR groups…")
        # Wire IR filter signal
        self.reference_filter.textChanged.connect(self.irFilterChanged.emit)
        ir_layout.addWidget(self.reference_filter)
        self.ir_table = QtWidgets.QTableWidget(0, 3)
        self.ir_table.setHorizontalHeaderLabels(["Group", "min (cm⁻¹)", "max (cm⁻¹)"])
        self.ir_table.horizontalHeader().setStretchLastSection(True)
        ir_layout.addWidget(self.ir_table, 1)
        self.reference_tabs.addTab(ir_tab, "IR Functional Groups")

        # --- Line shapes tab
        ls_tab = QtWidgets.QWidget()
        ls_layout = QtWidgets.QVBoxLayout(ls_tab)
        self.ls_table = QtWidgets.QTableWidget(0, 2)
        self.ls_table.setHorizontalHeaderLabels(["Model", "Notes"])
        self.ls_table.horizontalHeader().setStretchLastSection(True)
        ls_layout.addWidget(self.ls_table, 1)
        self.reference_tabs.addTab(ls_tab, "Line Shapes")

    def _on_nist_fetch_clicked(self) -> None:
        """Emit signal when NIST fetch is requested."""
        element = self.nist_element_edit.text().strip()
        lower = self.nist_lower_spin.value()
        upper = self.nist_upper_spin.value()
        self.nistFetchRequested.emit(element, lower, upper)

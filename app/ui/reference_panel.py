"""Reference panel: NIST ASD, IR Functional Groups, and Reference Lines tabs.

This panel provides reference data sources with a shared preview plot
and overlay toggle. Emits signals for user interactions.
"""
from __future__ import annotations

from typing import Optional

import pyqtgraph as pg
from app.qt_compat import get_qt
from app.ui.plot_pane import PlotPane
from app.ui.nist_lines_panel import NistLinesPanel

QtCore, QtGui, QtWidgets, _ = get_qt()

# Get Signal compatible with both PySide6 and PyQt6
Signal = getattr(QtCore, "Signal", None)  # type: ignore[attr-defined]
if Signal is None:
    Signal = getattr(QtCore, "pyqtSignal")  # type: ignore[attr-defined]


class ReferencePanel(QtWidgets.QWidget):
    """Standalone panel for reference data (NIST, IR, Line Shapes).

    Signals:
      - overlayToggled(bool): Emitted when overlay checkbox is toggled
      - tabChanged(int): Emitted when reference tab changes
      - irFilterChanged(str): Emitted when IR filter text changes
      - referenceLinesToggled(str, bool): Emitted when reference line element is toggled
      - referenceLinesRefreshRequested(): Emitted when refresh is requested
      - nistFetchRequested(str, float, float): Emitted when NIST fetch is requested (element, lower, upper)
      - nistVisibilityChanged(str, bool): Emitted when NIST collection visibility changes (collection_id, visible)
      - nistRemoveRequested(list): Emitted when NIST collection removal is requested
      - nistClearAllRequested(): Emitted when NIST clear all is requested

    Public attributes:
      - reference_overlay_checkbox
      - reference_status_label
      - reference_plot (PlotWidget)
      - reference_tabs (QTabWidget)
      - reference_filter (for IR filter)
      - ir_table
      - nist_lines_panel (NistLinesPanel)
    """

    overlayToggled = Signal(bool)
    tabChanged = Signal(int)
    irFilterChanged = Signal(str)
    referenceLinesToggled = Signal(str, bool)  # element, visible
    referenceLinesRefreshRequested = Signal()
    # NIST panel signals (forwarded from NistLinesPanel)
    nistFetchRequested = Signal(str, float, float)  # element, lower, upper
    nistVisibilityChanged = Signal(str, bool)  # collection_id, visible
    nistRemoveRequested = Signal(list)  # list of collection_ids
    nistClearAllRequested = Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.reference_overlay_checkbox: QtWidgets.QCheckBox
        self.reference_status_label: QtWidgets.QLabel
        self.reference_plot: pg.PlotWidget
        self.reference_tabs: QtWidgets.QTabWidget
        # IR controls
        self.reference_filter: QtWidgets.QLineEdit
        self.ir_table: QtWidgets.QTableWidget
        # Reference Lines
        self.reflines_table: QtWidgets.QTableWidget
        self.reflines_checkboxes: dict[str, QtWidgets.QCheckBox]  # element -> checkbox
        # NIST Lines
        self.nist_lines_panel: NistLinesPanel
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

        # --- Reference Lines tab (curated spectral lines with element filtering)
        reflines_tab = QtWidgets.QWidget()
        reflines_layout = QtWidgets.QVBoxLayout(reflines_tab)
        
        # Element filter checkboxes (common elements)
        filter_label = QtWidgets.QLabel("Show elements:")
        filter_label.setStyleSheet("font-weight: bold;")
        reflines_layout.addWidget(filter_label)
        
        filter_grid = QtWidgets.QGridLayout()
        filter_grid.setContentsMargins(4, 4, 4, 4)
        self.reflines_checkboxes = {}
        
        # Common elements organized in grid (4 columns)
        elements = [
            ("H", "Hydrogen"), ("He", "Helium"), ("Ca", "Calcium"), ("Fe", "Iron"),
            ("Mg", "Magnesium"), ("Na", "Sodium"), ("O2", "Oxygen"), ("Ba", "Barium"),
            ("Sr", "Strontium"), ("Cr", "Chromium"), ("Hg", "Mercury"), ("Ni", "Nickel"),
        ]
        
        for idx, (elem_key, elem_label) in enumerate(elements):
            cb = QtWidgets.QCheckBox(f"{elem_key} ({elem_label})")
            cb.setChecked(False)  # Default: all off
            cb.toggled.connect(lambda checked, e=elem_key: self.referenceLinesToggled.emit(e, checked))
            self.reflines_checkboxes[elem_key] = cb
            row, col = divmod(idx, 4)
            filter_grid.addWidget(cb, row, col)
        
        reflines_layout.addLayout(filter_grid)
        
        # Quick actions
        actions_row = QtWidgets.QHBoxLayout()
        select_all_btn = QtWidgets.QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._set_all_reflines_checkboxes(True))
        clear_all_btn = QtWidgets.QPushButton("Clear All")
        clear_all_btn.clicked.connect(lambda: self._set_all_reflines_checkboxes(False))
        refresh_btn = QtWidgets.QPushButton("Refresh Lines")
        refresh_btn.clicked.connect(lambda: self.referenceLinesRefreshRequested.emit())
        actions_row.addWidget(select_all_btn)
        actions_row.addWidget(clear_all_btn)
        actions_row.addWidget(refresh_btn)
        actions_row.addStretch(1)
        reflines_layout.addLayout(actions_row)
        
        # Table showing filtered lines
        self.reflines_table = QtWidgets.QTableWidget(0, 4)
        self.reflines_table.setHorizontalHeaderLabels(["Wavelength (nm)", "Label", "Element", "Note"])
        self.reflines_table.horizontalHeader().setStretchLastSection(True)
        self.reflines_table.setAlternatingRowColors(True)
        self.reflines_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        reflines_layout.addWidget(self.reflines_table, 1)
        
        info = QtWidgets.QLabel("Check elements above to display their spectral lines on the main plot.")
        info.setWordWrap(True)
        info.setStyleSheet("QLabel { color: #888; font-size: 10pt; padding: 4px; }")
        reflines_layout.addWidget(info)
        
        self.reference_tabs.addTab(reflines_tab, "Reference Lines")

        # --- NIST Spectral Lines tab (fetch from NIST ASD)
        self.nist_lines_panel = NistLinesPanel(self)
        self.reference_tabs.addTab(self.nist_lines_panel, "NIST Spectral Lines")

        # Forward NIST panel signals
        self.nist_lines_panel.nistFetchRequested.connect(self.nistFetchRequested.emit)
        self.nist_lines_panel.visibilityChanged.connect(self.nistVisibilityChanged.emit)
        self.nist_lines_panel.removeRequested.connect(self.nistRemoveRequested.emit)
        self.nist_lines_panel.clearAllRequested.connect(self.nistClearAllRequested.emit)

    def _set_all_reflines_checkboxes(self, checked: bool) -> None:
        """Helper to check/uncheck all element filters at once."""
        for cb in self.reflines_checkboxes.values():
            cb.setChecked(checked)

"""Application entry point for the Spectra desktop shell."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, cast

import numpy as np
import pyqtgraph as pg

from app.qt_compat import get_qt
from .services import (
    UnitsService,
    ProvenanceService,
    DataIngestService,
    OverlayService,
    MathService,
    ReferenceLibrary,
    Spectrum,
)
from .ui.plot_pane import PlotPane, TraceStyle

QtCore: Any
QtGui: Any
QtWidgets: Any
QT_BINDING: str
QtCore, QtGui, QtWidgets, QT_BINDING = get_qt()

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


class SpectraMainWindow(QtWidgets.QMainWindow):
    """Preview shell that wires UI actions to services with docked layout."""

    def __init__(self, container: object | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Spectra Desktop Preview")
        self.resize(1320, 840)

        self.units_service = UnitsService()
        self.provenance_service = ProvenanceService()
        self.ingest_service = DataIngestService(self.units_service)
        self.overlay_service = OverlayService(self.units_service)
        self.math_service = MathService()
        self.reference_library = ReferenceLibrary()

        self._dataset_items: Dict[str, QtGui.QStandardItem] = {}
        self._spectrum_colors: Dict[str, QtGui.QColor] = {}
        self._visibility: Dict[str, bool] = {}
        self._normalization_mode: str = "None"
        self._doc_entries: List[tuple[str, Path]] = []
        self._palette: List[QtGui.QColor] = [
            QtGui.QColor("#4F6D7A"),
            QtGui.QColor("#C0D6DF"),
            QtGui.QColor("#C72C41"),
            QtGui.QColor("#2F4858"),
            QtGui.QColor("#33658A"),
            QtGui.QColor("#758E4F"),
            QtGui.QColor("#6D597A"),
            QtGui.QColor("#EE964B"),
        ]
        self._palette_index = 0

        self.log_view: QtWidgets.QPlainTextEdit | None = None
        self._log_buffer: list[tuple[str, str]] = []
        self._log_ready = False

        self._reference_items: list[pg.GraphicsObject] = []
        self._reference_overlay_payload: Optional[Dict[str, Any]] = None
        self._reference_overlay_key: Optional[str] = None

        self._setup_ui()
        self._setup_menu()
        self._wire_shortcuts()
        self._load_default_samples()

    # ------------------------------------------------------------------
    def _setup_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")

        open_action = QtGui.QAction("&Open…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        sample_action = QtGui.QAction("Load &Sample", self)
        sample_action.triggered.connect(self.load_sample_via_menu)
        file_menu.addAction(sample_action)

        export_action = QtGui.QAction("Export &Manifest", self)
        export_action.triggered.connect(self.export_manifest)
        file_menu.addAction(export_action)

        file_menu.addSeparator()
        exit_action = QtGui.QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menu.addMenu("&View")
        view_menu.addAction(self.dataset_dock.toggleViewAction())
        view_menu.addAction(self.inspector_dock.toggleViewAction())
        view_menu.addAction(self.log_dock.toggleViewAction())
        view_menu.addSeparator()
        self.reset_plot_action = QtGui.QAction("Reset Plot", self)
        self.reset_plot_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+A"))
        self.reset_plot_action.triggered.connect(self.plot.autoscale)
        view_menu.addAction(self.reset_plot_action)
        view_menu.addSeparator()
        self.data_table_action = QtGui.QAction("Show Data Table", self, checkable=True)
        self.data_table_action.triggered.connect(self._toggle_data_table)
        view_menu.addAction(self.data_table_action)

        help_menu = menu.addMenu("&Help")
        docs_action = QtGui.QAction("View &Documentation", self)
        docs_action.setShortcut("F1")
        docs_action.triggered.connect(self.show_documentation)
        help_menu.addAction(docs_action)

    def _setup_ui(self) -> None:
        self.central_split = QtWidgets.QSplitter(self)
        self.central_split.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.setCentralWidget(self.central_split)

        self.plot = PlotPane(self)
        self.plot.setObjectName("plot-area")
        self.central_split.addWidget(self.plot)
        self.plot.autoscale()

        self.data_table = QtWidgets.QTableWidget()
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(["Spectrum", "Point", "X", "Y"])
        self.data_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.data_table.hide()
        self.central_split.addWidget(self.data_table)
        self.central_split.setStretchFactor(0, 4)
        self.central_split.setStretchFactor(1, 3)

        self.dataset_dock = QtWidgets.QDockWidget("Datasets", self)
        self.dataset_dock.setObjectName("dock-datasets")
        self.dataset_dock.setAllowedAreas(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea | QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.dataset_tree = QtWidgets.QTreeView()
        self.dataset_tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.dataset_tree.setRootIsDecorated(True)
        self.dataset_tree.setUniformRowHeights(True)
        self.dataset_model = QtGui.QStandardItemModel()
        self.dataset_model.setHorizontalHeaderLabels(["Alias", "Visible", "Color"])
        self._originals_item = self._create_group_row("Originals")
        self._derived_item = self._create_group_row("Derived")
        self.dataset_tree.setModel(self.dataset_model)
        self.dataset_tree.expandAll()
        self.dataset_tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.dataset_tree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.dataset_tree.header().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.dataset_tree.selectionModel().selectionChanged.connect(self._on_dataset_selection_changed)
        self.dataset_model.dataChanged.connect(self._on_dataset_data_changed)
        self.dataset_dock.setWidget(self.dataset_tree)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.dataset_dock)

        self.inspector_dock = QtWidgets.QDockWidget("Inspector", self)
        self.inspector_dock.setObjectName("dock-inspector")
        self.inspector_tabs = QtWidgets.QTabWidget()
        self._build_inspector_tabs()
        self.inspector_dock.setWidget(self.inspector_tabs)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.inspector_dock)

        self.log_dock = QtWidgets.QDockWidget("Log", self)
        self.log_dock.setObjectName("dock-log")
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_dock.setWidget(self.log_view)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)

        self._log_ready = True
        if self._log_buffer:
            for channel, message in self._log_buffer:
                self.log_view.appendPlainText(f"[{channel}] {message}")
            self._log_buffer.clear()

        self._build_plot_toolbar()

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        self.plot.pointHovered.connect(
            lambda x, y: self.status_bar.showMessage(
                f"x={x:.4g} {self.plot_unit()} | y={y:.4g}"
            )
        )

        # Load documentation entries after all dock widgets (including the log view)
        # have been initialised so that the initial selection can log status safely.
        self._load_documentation_index()

    def _build_inspector_tabs(self) -> None:
        # Info tab -----------------------------------------------------
        self.tab_info = QtWidgets.QWidget()
        info_layout = QtWidgets.QVBoxLayout(self.tab_info)
        self.info_placeholder = QtWidgets.QLabel("Select a trace to see its details.")
        self.info_placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.info_placeholder.setStyleSheet("color: #666; font-size: 14px;")
        info_layout.addWidget(self.info_placeholder)

        self.info_panel = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(self.info_panel)
        self.info_name = QtWidgets.QLabel("–")
        self.info_alias = QtWidgets.QLineEdit()
        self.info_alias.setPlaceholderText("Alias…")
        self.info_alias.editingFinished.connect(self._rename_selected_spectrum)
        self.info_source = QtWidgets.QLabel("–")
        self.info_units = QtWidgets.QLabel("–")
        self.info_range_x = QtWidgets.QLabel("–")
        self.info_range_y = QtWidgets.QLabel("–")
        self.info_points = QtWidgets.QLabel("–")
        form.addRow("Name:", self.info_name)
        form.addRow("Alias:", self.info_alias)
        form.addRow("Source:", self.info_source)
        form.addRow("Units:", self.info_units)
        form.addRow("X Range:", self.info_range_x)
        form.addRow("Y Range:", self.info_range_y)
        form.addRow("Samples:", self.info_points)
        info_layout.addWidget(self.info_panel)
        self.info_panel.hide()

        # Math tab -----------------------------------------------------
        self.tab_math = QtWidgets.QWidget()
        math_layout = QtWidgets.QVBoxLayout(self.tab_math)
        selector_layout = QtWidgets.QHBoxLayout()
        math_layout.addLayout(selector_layout)
        self.math_a = QtWidgets.QComboBox()
        self.math_b = QtWidgets.QComboBox()
        selector_layout.addWidget(QtWidgets.QLabel("Trace A:"))
        selector_layout.addWidget(self.math_a)
        selector_layout.addWidget(QtWidgets.QLabel("Trace B:"))
        selector_layout.addWidget(self.math_b)
        swap_btn = QtWidgets.QPushButton("Swap")
        swap_btn.clicked.connect(self._swap_math_selection)
        selector_layout.addWidget(swap_btn)
        selector_layout.addStretch(1)

        btn_layout = QtWidgets.QHBoxLayout()
        math_layout.addLayout(btn_layout)
        subtract_btn = QtWidgets.QPushButton("A − B")
        subtract_btn.clicked.connect(self.compute_subtract)
        btn_layout.addWidget(subtract_btn)
        ratio_btn = QtWidgets.QPushButton("A ÷ B")
        ratio_btn.clicked.connect(self.compute_ratio)
        btn_layout.addWidget(ratio_btn)
        btn_layout.addStretch(1)

        self.math_log = QtWidgets.QPlainTextEdit()
        self.math_log.setReadOnly(True)
        self.math_log.setPlaceholderText("Math operations will appear here.")
        math_layout.addWidget(self.math_log)

        # Style tab placeholder ---------------------------------------
        self.tab_style = QtWidgets.QWidget()
        style_layout = QtWidgets.QVBoxLayout(self.tab_style)
        style_placeholder = QtWidgets.QLabel("Style controls coming soon.")
        style_placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        style_layout.addWidget(style_placeholder)

        # Provenance tab -----------------------------------------------
        self.tab_prov = QtWidgets.QWidget()
        prov_layout = QtWidgets.QVBoxLayout(self.tab_prov)
        self.prov_placeholder = QtWidgets.QLabel("Select a trace to inspect provenance.")
        self.prov_placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.prov_placeholder.setStyleSheet("color: #666; font-size: 14px;")
        prov_layout.addWidget(self.prov_placeholder)

        self.prov_tree = QtWidgets.QTreeWidget()
        self.prov_tree.setHeaderLabels(["Step", "Details"])
        self.prov_tree.hide()
        prov_layout.addWidget(self.prov_tree)

        self.provenance_view = QtWidgets.QTextEdit(readOnly=True)
        self.provenance_view.setPlaceholderText("Provenance JSON will appear here.")
        self.provenance_view.hide()
        prov_layout.addWidget(self.provenance_view)

        self._build_reference_tab()
        self._build_documentation_tab()

        for name, tab in [
            ("Info", self.tab_info),
            ("Math", self.tab_math),
            ("Style", self.tab_style),
            ("Provenance", self.tab_prov),
            ("Reference", self.tab_reference),
            ("Docs", self.tab_docs),
        ]:
            self.inspector_tabs.addTab(tab, name)

    def _build_plot_toolbar(self) -> None:
        toolbar = QtWidgets.QToolBar("Plot")
        toolbar.setMovable(False)
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, toolbar)

        self.action_cursor = QtGui.QAction("Cursor", self)
        self.action_cursor.setCheckable(True)
        self.action_cursor.setChecked(True)
        self.action_cursor.toggled.connect(self.plot.set_crosshair_visible)
        toolbar.addAction(self.action_cursor)

        self.action_peak = QtGui.QAction("Peak", self)
        toolbar.addAction(self.action_peak)

        toolbar.addSeparator()
        toolbar.addWidget(QtWidgets.QLabel("Units:"))
        self.unit_combo = QtWidgets.QComboBox()
        self.unit_combo.addItems(["nm", "Å", "µm", "cm⁻¹"])
        self.unit_combo.currentTextChanged.connect(self._on_display_unit_changed)
        toolbar.addWidget(self.unit_combo)

        toolbar.addWidget(QtWidgets.QLabel("Normalize:"))
        self.norm_combo = QtWidgets.QComboBox()
        self.norm_combo.addItems(["None", "Max", "Area"])
        self.norm_combo.currentTextChanged.connect(self._on_normalize_changed)
        self._normalization_mode = self.norm_combo.currentText()
        toolbar.addWidget(self.norm_combo)

        toolbar.addWidget(QtWidgets.QLabel("Smoothing:"))
        self.smooth_combo = QtWidgets.QComboBox()
        self.smooth_combo.addItems(["Off", "Savitzky–Golay"])
        self.smooth_combo.currentTextChanged.connect(self._on_smoothing_changed)
        toolbar.addWidget(self.smooth_combo)

        toolbar.addSeparator()
        self.action_export = QtGui.QAction("Export", self)
        self.action_export.triggered.connect(self.export_manifest)
        toolbar.addAction(self.action_export)

    def plot_unit(self) -> str:
        return self.unit_combo.currentText()

    def _on_display_unit_changed(self, unit: str) -> None:
        self.plot.set_display_unit(unit)
        self.refresh_overlay()
        # Reference previews share the same display axis so update them as well.
        if hasattr(self, "reference_dataset_combo"):
            self._refresh_reference_dataset()

    def _create_group_row(self, title: str) -> QtGui.QStandardItem:
        alias_item = QtGui.QStandardItem(title)
        alias_item.setEditable(False)
        alias_item.setSelectable(False)
        alias_item.setData("group", QtCore.Qt.ItemDataRole.UserRole)
        visible_item = QtGui.QStandardItem()
        visible_item.setEditable(False)
        color_item = QtGui.QStandardItem()
        color_item.setEditable(False)
        self.dataset_model.appendRow([alias_item, visible_item, color_item])
        return alias_item

    def _wire_shortcuts(self) -> None:
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), self, activated=self.open_file)
        QtGui.QShortcut(QtGui.QKeySequence("U"), self, activated=self._cycle_units)

    def _cycle_units(self) -> None:
        idx = (self.unit_combo.currentIndex() + 1) % self.unit_combo.count()
        self.unit_combo.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    def _load_default_samples(self) -> None:
        self.plot.begin_bulk_update()
        try:
            for sample_file in sorted(SAMPLES_DIR.glob('sample_*.csv')):
                if sample_file.exists():
                    self._ingest_path(sample_file)
        finally:
            self.plot.end_bulk_update()

    # Actions -----------------------------------------------------------
    def open_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Spectrum",
            str(Path.home()),
            "Spectra (*.csv *.txt)",
        )
        if path:
            self._ingest_path(Path(path))

    def load_sample_via_menu(self) -> None:
        files = list(SAMPLES_DIR.glob('*.csv'))
        if not files:
            self.status_bar.showMessage("No samples found", 5000)
            return
        self._ingest_path(files[0])

    def export_manifest(self) -> None:
        if not self.overlay_service.list():
            QtWidgets.QMessageBox.information(self, "No Data", "Load spectra before exporting provenance.")
            return
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Manifest",
            str(Path.home() / 'manifest.json'),
            "JSON (*.json)",
        )
        if save_path:
            manifest_path = Path(save_path)
            try:
                export = self.provenance_service.export_bundle(
                    self.overlay_service.list(),
                    manifest_path,
                    png_writer=self.plot.export_png,
                )
            except Exception as exc:  # pragma: no cover - UI feedback
                QtWidgets.QMessageBox.warning(self, "Export Failed", str(exc))
                self._log("Export", f"Bundle export failed: {exc}")
                return
            self.status_bar.showMessage(f"Manifest saved to {export['manifest_path']}", 5000)
            self._log("Manifest", f"Saved to {export['manifest_path']}")
            self._log("Export", f"CSV saved to {export['csv_path']}")
            self._log("Export", f"Plot snapshot saved to {export['png_path']}")
            self.provenance_view.setPlainText(json_pretty(export['manifest']))
            self.provenance_view.show()
            self.prov_tree.show()
            self.prov_placeholder.hide()

    def refresh_overlay(self) -> None:
        selected_ids = self._selected_dataset_ids()
        if not selected_ids:
            selected_ids = [sid for sid, visible in self._visibility.items() if visible]
        if not selected_ids:
            self.data_table.clearContents()
            self.data_table.setRowCount(0)
            if self.data_table.isVisible():
                self.data_table.hide()
                self.data_table_action.setChecked(False)
            return
        selected_ids = [sid for sid in selected_ids if self._visibility.get(sid, True)]
        if not selected_ids:
            return
        views = self.overlay_service.overlay(
            selected_ids,
            self.unit_combo.currentText(),
            self._normalise_y("absorbance"),
            normalization=self._normalization_mode,
        )
        self._populate_data_table(views)
        if not self.data_table.isVisible():
            self.data_table.show()
            self.data_table_action.setChecked(True)

        all_ids = [spec.id for spec in self.overlay_service.list()]
        if not all_ids:
            return
        canonical_views = self.overlay_service.overlay(
            all_ids,
            "nm",
            "absorbance",
            normalization=self._normalization_mode,
        )
        for view in canonical_views:
            spec_id = cast(str, view["id"])
            alias_item = self._dataset_items.get(spec_id)
            alias = alias_item.text() if alias_item else cast(str, view["name"])
            color = self._spectrum_colors.get(spec_id)
            if color is None:
                color = QtGui.QColor("#4F6D7A")
            style = TraceStyle(
                color=QtGui.QColor(color),
                width=1.6,
                antialias=False,
                show_in_legend=True,
            )
            self.plot.add_trace(
                key=spec_id,
                alias=alias,
                x_nm=cast(np.ndarray, view["x_canonical"]),
                y=cast(np.ndarray, view["y_canonical"]),
                style=style,
            )
            self.plot.set_visible(spec_id, self._visibility.get(spec_id, True))

    def compute_subtract(self) -> None:
        ids = self._selected_math_ids()
        if not ids:
            return
        spec_a = self.overlay_service.get(ids[0])
        spec_b = self.overlay_service.get(ids[1])
        result, info = self.math_service.subtract(spec_a, spec_b)
        self._log_math(info)
        if result:
            self.overlay_service.add(result)
            self._add_spectrum(result)
            self._update_math_selectors()

    def compute_ratio(self) -> None:
        ids = self._selected_math_ids()
        if not ids:
            return
        spec_a = self.overlay_service.get(ids[0])
        spec_b = self.overlay_service.get(ids[1])
        result, info = self.math_service.ratio(spec_a, spec_b)
        self._log_math(info)
        self.overlay_service.add(result)
        self._add_spectrum(result)
        self._update_math_selectors()

    # Internal helpers --------------------------------------------------
    def _ingest_path(self, path: Path) -> None:
        try:
            spectrum = self.ingest_service.ingest(path)
        except Exception as exc:  # pragma: no cover - UI feedback
            QtWidgets.QMessageBox.critical(self, "Import failed", str(exc))
            return
        self.overlay_service.add(spectrum)
        self._add_spectrum(spectrum)
        self.status_bar.showMessage(f"Loaded {path.name}", 5000)
        self._update_math_selectors()
        self.refresh_overlay()
        self._show_metadata(spectrum)
        self._show_provenance(spectrum)

    def _add_spectrum(self, spectrum: Spectrum) -> None:
        color = self._assign_color(spectrum)
        group_item = self._derived_item if self._is_derived(spectrum) else self._originals_item
        visible_item = QtGui.QStandardItem()
        visible_item.setCheckable(True)
        visible_item.setCheckState(QtCore.Qt.CheckState.Checked)
        visible_item.setEditable(False)
        visible_item.setData(spectrum.id, QtCore.Qt.ItemDataRole.UserRole)

        color_item = QtGui.QStandardItem()
        color_item.setEditable(False)
        icon_pix = QtGui.QPixmap(16, 16)
        icon_pix.fill(color)
        color_item.setIcon(QtGui.QIcon(icon_pix))
        color_item.setData(spectrum.id, QtCore.Qt.ItemDataRole.UserRole)

        alias_item = QtGui.QStandardItem(spectrum.name)
        alias_item.setEditable(False)
        alias_item.setData(spectrum.id, QtCore.Qt.ItemDataRole.UserRole)
        group_item.appendRow([alias_item, visible_item, color_item])
        self.dataset_tree.expandAll()
        self._dataset_items[spectrum.id] = alias_item
        self._visibility[spectrum.id] = True
        self._add_plot_trace(spectrum, color)

    def _add_plot_trace(self, spectrum: Spectrum, color: QtGui.QColor) -> None:
        alias_item = self._dataset_items.get(spectrum.id)
        alias = alias_item.text() if alias_item else spectrum.name
        x_nm = self._to_nm(spectrum.x, spectrum.x_unit)
        style = TraceStyle(
            color=QtGui.QColor(color),
            width=1.6,
            antialias=False,
            show_in_legend=True,
        )
        self.plot.add_trace(
            key=spectrum.id,
            alias=alias,
            x_nm=x_nm,
            y=spectrum.y,
            style=style,
        )
        self.plot.autoscale()

    def _show_metadata(self, spectrum: Spectrum | None) -> None:
        if spectrum is None:
            self.info_panel.hide()
            self.info_placeholder.show()
            return

        alias_item = self._dataset_items.get(spectrum.id)
        alias_text = alias_item.text() if alias_item else spectrum.name
        self.info_name.setText(spectrum.name)
        self.info_alias.setText(alias_text)
        source = spectrum.source_path.name if spectrum.source_path else "N/A"
        self.info_source.setText(source)
        self.info_units.setText(f"x: {spectrum.x_unit} | y: {spectrum.y_unit}")
        if spectrum.x.size:
            self.info_range_x.setText(f"{float(spectrum.x.min()):.4g} – {float(spectrum.x.max()):.4g} {spectrum.x_unit}")
            self.info_points.setText(str(int(spectrum.x.size)))
        else:
            self.info_range_x.setText("–")
            self.info_points.setText("0")
        if spectrum.y.size:
            self.info_range_y.setText(f"{float(spectrum.y.min()):.4g} – {float(spectrum.y.max()):.4g} {spectrum.y_unit}")
        else:
            self.info_range_y.setText("–")
        self.info_panel.show()
        self.info_placeholder.hide()

    def _show_provenance(self, spectrum: Spectrum | None) -> None:
        if spectrum is None:
            self.prov_tree.clear()
            self.provenance_view.clear()
            self.prov_tree.hide()
            self.provenance_view.hide()
            self.prov_placeholder.show()
            return

        self.prov_tree.clear()
        root = QtWidgets.QTreeWidgetItem([spectrum.name, spectrum.id])
        self.prov_tree.addTopLevelItem(root)

        parents = getattr(spectrum, 'parents', ())
        if parents:
            parents_node = QtWidgets.QTreeWidgetItem(["Parents", ", ".join(parents)])
            root.addChild(parents_node)

        transforms = getattr(spectrum, 'transforms', ())
        for transform in transforms:
            node = QtWidgets.QTreeWidgetItem([
                transform.get('name', transform.get('operation', 'Transform')),
                json_pretty(transform),
            ])
            root.addChild(node)

        metadata_node = QtWidgets.QTreeWidgetItem([
            "Metadata keys",
            ", ".join(sorted(map(str, spectrum.metadata.keys()))),
        ])
        root.addChild(metadata_node)

        self.prov_tree.expandAll()
        self.prov_tree.show()
        self.prov_placeholder.hide()

        self.provenance_view.setPlainText(json_pretty({
            'id': spectrum.id,
            'metadata': spectrum.metadata,
            'parents': list(parents),
            'transforms': list(transforms),
        }))
        self.provenance_view.show()

    def _populate_data_table(self, views: Iterable[dict]) -> None:
        rows = sum(min(100, len(view['x'])) for view in views)
        self.data_table.setRowCount(rows)
        row_index = 0
        for view in views:
            x_arr = view['x']
            y_arr = view['y']
            for idx, (x, y) in enumerate(zip(x_arr[:100], y_arr[:100])):
                self.data_table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(view['name']))
                self.data_table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(str(idx)))
                self.data_table.setItem(row_index, 2, QtWidgets.QTableWidgetItem(f"{x:.6g}"))
                self.data_table.setItem(row_index, 3, QtWidgets.QTableWidgetItem(f"{y:.6g}"))
                row_index += 1
        if rows == 0:
            self.data_table.clearContents()
            self.data_table.setRowCount(0)

    def _update_math_selectors(self) -> None:
        spectra = self.overlay_service.list()
        self.math_a.clear()
        self.math_b.clear()
        for spec in spectra:
            alias_item = self._dataset_items.get(spec.id)
            display_name = alias_item.text() if alias_item else spec.name
            self.math_a.addItem(display_name, spec.id)
            self.math_b.addItem(display_name, spec.id)

    def _selected_math_ids(self) -> list[str]:
        if self.math_a.count() < 2 or self.math_b.count() < 2:
            QtWidgets.QMessageBox.information(self, "Need more spectra", "Load at least two spectra for math operations.")
            return []
        return [self.math_a.currentData(), self.math_b.currentData()]

    def _log_math(self, info: dict) -> None:
        new_line = json_pretty(info)
        self.math_log.appendPlainText(new_line)
        self._log("Math", new_line)

    def _normalise_y(self, label: str) -> str:
        mapping = {"%T": "percent_transmittance"}
        return mapping.get(label, label)

    def _assign_color(self, spectrum: Spectrum) -> QtGui.QColor:
        if spectrum.id in self._spectrum_colors:
            return self._spectrum_colors[spectrum.id]

        color: QtGui.QColor | None = None
        metadata = spectrum.metadata if isinstance(spectrum.metadata, dict) else {}
        operation = metadata.get('operation') if isinstance(metadata, dict) else None
        parents: List[str] = []
        if isinstance(operation, dict):
            parents = list(operation.get('parents') or [])
        if parents:
            base_id = parents[0]
            base_color = self._spectrum_colors.get(base_id)
            if base_color:
                color = QtGui.QColor(base_color)
                color = color.lighter(130)
        if color is None:
            color = self._palette[self._palette_index % len(self._palette)]
            self._palette_index += 1
        self._spectrum_colors[spectrum.id] = color
        return color

    def _is_derived(self, spectrum: Spectrum) -> bool:
        metadata = spectrum.metadata
        if isinstance(metadata, dict) and 'operation' in metadata:
            return True
        return bool(getattr(spectrum, 'parents', ()))

    def _to_nm(self, x: np.ndarray, unit: str) -> np.ndarray:
        data = np.asarray(x, dtype=np.float64)
        if unit == "nm":
            return data
        if unit in ("Angstrom", "Å"):
            return data / 10.0
        if unit in ("um", "µm"):
            return data * 1000.0
        if unit in ("cm^-1", "cm⁻¹"):
            with np.errstate(divide='ignore'):
                return 1e7 / data
        return data

    def _selected_dataset_ids(self) -> list[str]:
        selection = self.dataset_tree.selectionModel()
        if not selection:
            return []
        ids: list[str] = []
        for index in selection.selectedRows():
            item = self.dataset_model.itemFromIndex(index)
            if not item:
                continue
            value = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if value and value != "group":
                ids.append(value)
        return ids

    def _on_dataset_selection_changed(self, selected, deselected) -> None:
        ids = self._selected_dataset_ids()
        spectrum = self.overlay_service.get(ids[-1]) if ids else None
        self._show_metadata(spectrum)
        self._show_provenance(spectrum)
        self.refresh_overlay()

    def _on_dataset_data_changed(
        self,
        top_left: QtCore.QModelIndex,
        bottom_right: QtCore.QModelIndex,
        roles: List[int],
    ) -> None:
        if top_left.column() != 1:
            return
        for row in range(top_left.row(), bottom_right.row() + 1):
            index = top_left.sibling(row, 1)
            item = self.dataset_model.itemFromIndex(index)
            if not item:
                continue
            spec_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if not spec_id or spec_id == "group":
                continue
            self._visibility[spec_id] = item.checkState() == QtCore.Qt.CheckState.Checked
            self.plot.set_visible(spec_id, self._visibility[spec_id])
        self.refresh_overlay()

    def _toggle_data_table(self, checked: bool) -> None:
        self.data_table.setVisible(checked)

    def _swap_math_selection(self) -> None:
        idx_a = self.math_a.currentIndex()
        idx_b = self.math_b.currentIndex()
        if idx_a == -1 or idx_b == -1:
            return
        self.math_a.setCurrentIndex(idx_b)
        self.math_b.setCurrentIndex(idx_a)

    # Reference ---------------------------------------------------------
    def _build_reference_tab(self) -> None:
        self.tab_reference = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.tab_reference)
        layout.setContentsMargins(6, 6, 6, 6)

        intro = QtWidgets.QLabel(
            "Curated line lists, infrared heuristics, and JWST quick-look spectra are bundled for offline use."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #555;")
        layout.addWidget(intro)

        controls = QtWidgets.QHBoxLayout()
        layout.addLayout(controls)

        controls.addWidget(QtWidgets.QLabel("Dataset:"))
        self.reference_dataset_combo = QtWidgets.QComboBox()
        self.reference_dataset_combo.currentIndexChanged.connect(self._refresh_reference_dataset)
        controls.addWidget(self.reference_dataset_combo, 1)

        self.reference_filter = QtWidgets.QLineEdit()
        self.reference_filter.setPlaceholderText("Filter rows…")
        self.reference_filter.textChanged.connect(self._filter_reference_rows)
        controls.addWidget(self.reference_filter, 1)

        self.reference_overlay_toggle = QtWidgets.QCheckBox("Overlay on main plot")
        self.reference_overlay_toggle.toggled.connect(self._on_reference_overlay_toggled)
        controls.addWidget(self.reference_overlay_toggle)
        controls.addStretch(1)

        self.reference_table = QtWidgets.QTableWidget()
        self.reference_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.reference_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.reference_table.setAlternatingRowColors(True)
        header = self.reference_table.horizontalHeader()
        header.setStretchLastSection(True)
        layout.addWidget(self.reference_table, 1)

        self.reference_plot = pg.PlotWidget()
        self.reference_plot.setObjectName("reference-preview")
        self.reference_plot.setMinimumHeight(220)
        self.reference_plot.showGrid(x=True, y=False, alpha=0.15)
        self.reference_plot.setLabel("bottom", "Wavelength", units=self.plot_unit())
        self.reference_plot.setLabel("left", "Normalised amplitude")
        layout.addWidget(self.reference_plot, 1)

        self.reference_meta = QtWidgets.QTextBrowser()
        self.reference_meta.setOpenExternalLinks(True)
        self.reference_meta.setPlaceholderText("Select a dataset to view its citation and context.")
        self.reference_meta.setMinimumHeight(160)
        layout.addWidget(self.reference_meta)

        self._populate_reference_combo()

    def _populate_reference_combo(self) -> None:
        combo = self.reference_dataset_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("NIST Hydrogen Lines (Balmer & Lyman)", ("spectral_lines", None))
        combo.addItem("IR Functional Groups", ("ir_groups", None))
        combo.addItem("Line-shape Placeholders", ("line_shapes", None))
        for target in self.reference_library.jwst_targets():
            name = target.get("name", "Unknown")
            instrument = target.get("instrument") or "—"
            combo.addItem(f"JWST: {name} ({instrument})", ("jwst", target.get("id")))
        combo.blockSignals(False)
        if combo.count():
            combo.setCurrentIndex(0)
        self._refresh_reference_dataset()

    def _filter_reference_rows(self, _: str) -> None:
        self._refresh_reference_dataset()

    def _refresh_reference_dataset(self) -> None:
        data = self.reference_dataset_combo.currentData()
        if not data:
            self.reference_table.setRowCount(0)
            self.reference_table.setColumnCount(0)
            self.reference_meta.clear()
            self._clear_reference_plot()
            self._reference_overlay_payload = None
            self._remove_reference_overlay()
            return

        kind, key = data
        query = self.reference_filter.text().strip().lower()

        self._clear_reference_plot()
        overlay_payload: Optional[Dict[str, Any]] = None

        if kind == "spectral_lines":
            entries = self.reference_library.spectral_lines()
            filtered = self._filter_reference_entries(entries, query)
            self.reference_table.setColumnCount(6)
            self.reference_table.setHorizontalHeaderLabels(
                ["Series", "Transition", "λ₀ (nm)", "ṽ (cm⁻¹)", "Aₖᵢ (s⁻¹)", "Relative Intensity"]
            )
            self.reference_table.setRowCount(len(filtered))
            for row, entry in enumerate(filtered):
                self._set_table_item(row, 0, entry.get("series", ""))
                self._set_table_item(row, 1, entry.get("transition", ""))
                self._set_table_item(row, 2, self._format_float(entry.get("vacuum_wavelength_nm")))
                self._set_table_item(row, 3, self._format_float(entry.get("wavenumber_cm_1")))
                self._set_table_item(row, 4, self._format_scientific(entry.get("einstein_a_s_1")))
                self._set_table_item(row, 5, self._format_float(entry.get("relative_intensity"), precision=2))
            meta = self.reference_library.hydrogen_metadata()
            notes = self._merge_provenance(meta)
            self._set_reference_meta(meta.get("citation"), meta.get("url"), notes)
            overlay_payload = self._render_reference_spectral_lines(filtered)

        elif kind == "ir_groups":
            entries = self.reference_library.ir_functional_groups()
            filtered = self._filter_reference_entries(entries, query)
            self.reference_table.setColumnCount(5)
            self.reference_table.setHorizontalHeaderLabels(
                ["Group", "Range (cm⁻¹)", "Intensity", "Modes", "Notes"]
            )
            self.reference_table.setRowCount(len(filtered))
            for row, entry in enumerate(filtered):
                self._set_table_item(row, 0, entry.get("group", ""))
                span = f"{self._format_float(entry.get('wavenumber_cm_1_min'), precision=0)} – {self._format_float(entry.get('wavenumber_cm_1_max'), precision=0)}"
                self._set_table_item(row, 1, span)
                self._set_table_item(row, 2, entry.get("intensity", ""))
                modes = ", ".join(entry.get("associated_modes", []))
                self._set_table_item(row, 3, modes)
                self._set_table_item(row, 4, entry.get("notes", ""))
            meta = self.reference_library.ir_metadata()
            notes = self._merge_provenance(meta)
            self._set_reference_meta(meta.get("citation"), meta.get("url"), notes)
            overlay_payload = self._render_reference_ir_groups(filtered)

        elif kind == "line_shapes":
            entries = self.reference_library.line_shape_placeholders()
            filtered = self._filter_reference_entries(entries, query)
            self.reference_table.setColumnCount(4)
            self.reference_table.setHorizontalHeaderLabels(
                ["Model", "Status", "Parameters", "Notes"]
            )
            self.reference_table.setRowCount(len(filtered))
            for row, entry in enumerate(filtered):
                self._set_table_item(row, 0, entry.get("label", entry.get("id", "")))
                self._set_table_item(row, 1, entry.get("status", ""))
                params = ", ".join(entry.get("parameters", []))
                self._set_table_item(row, 2, params)
                self._set_table_item(row, 3, entry.get("description", ""))
            meta = self.reference_library.line_shape_metadata()
            notes = meta.get("notes", "")
            references = meta.get("references", [])
            ref_lines = "".join(
                f"<li><a href='{ref.get('url')}'>{ref.get('citation')}</a></li>"
                for ref in references
                if isinstance(ref, Mapping)
            )
            self.reference_meta.setHtml(
                f"<p><b>{meta.get('notes', 'Line-shape placeholders')}</b></p><ul>{ref_lines}</ul>"
                if ref_lines
                else f"<p>{notes}</p>"
            )
            overlay_payload = None

        elif kind == "jwst":
            target = self.reference_library.jwst_target(key)
            if not target:
                self.reference_table.setRowCount(0)
                self.reference_table.setColumnCount(0)
                self.reference_meta.setHtml("<p>Target metadata unavailable.</p>")
                self._reference_overlay_payload = None
                self._remove_reference_overlay()
                return
            data_rows = target.get("data", [])
            status = target.get("status")
            if not data_rows:
                self.reference_table.setRowCount(0)
                self.reference_table.setColumnCount(0)
                notes = target.get("source", {}).get("notes", "No public JWST spectrum available.")
                self._set_reference_meta(target.get("name"), target.get("source", {}).get("url"), notes)
                self._reference_overlay_payload = None
                self._remove_reference_overlay()
                return
            filtered = self._filter_reference_entries(data_rows, query)
            wavelength_key = next((k for k in data_rows[0].keys() if "wavelength" in k), "wavelength")
            value_key = "value" if "value" in data_rows[0] else next(iter(set(data_rows[0].keys()) - {wavelength_key}), "value")
            uncertainty_key = next((k for k in data_rows[0].keys() if k.startswith("uncertainty")), None)
            columns = ["λ (µm)", f"Measurement ({target.get('data_units', 'value')})"]
            if uncertainty_key:
                units = uncertainty_key.split("_", 1)[-1].replace("_", " ")
                columns.append(f"Uncertainty ({units})")
            self.reference_table.setColumnCount(len(columns))
            self.reference_table.setHorizontalHeaderLabels(columns)
            self.reference_table.setRowCount(len(filtered))
            for row, entry in enumerate(filtered):
                self._set_table_item(row, 0, self._format_float(entry.get(wavelength_key)))
                self._set_table_item(row, 1, self._format_float(entry.get(value_key)))
                if uncertainty_key and len(columns) > 2:
                    self._set_table_item(row, 2, self._format_float(entry.get(uncertainty_key)))
            source = target.get("source", {})
            notes = source.get("notes", "")
            range_min, range_max = target.get("spectral_range_um", [None, None])
            range_text = ""
            if range_min is not None and range_max is not None:
                range_text = f"Range: {self._format_float(range_min)} – {self._format_float(range_max)} µm"
            resolution = target.get("spectral_resolution")
            resolution_text = f"Resolving power ≈ {resolution}" if resolution else "Resolving power pending"
            meta_html = (
                f"<p><b>{target.get('name')}</b><br/>"
                f"Instrument: {target.get('instrument', '—')} | Program: {target.get('program', '—')}<br/>"
                f"{range_text}<br/>{resolution_text}<br/>"
                f"Data units: {target.get('data_units', '—')}</p>"
            )
            if source.get("url"):
                meta_html += f"<p><a href='{source['url']}'>Source documentation</a></p>"
            if notes:
                meta_html += f"<p>{notes}</p>"
            provenance_html = self._format_target_provenance(target.get("provenance"))
            if provenance_html:
                meta_html += provenance_html
            if status:
                meta_html += f"<p>Status: {status}</p>"
            self.reference_meta.setHtml(meta_html)
            overlay_payload = self._render_reference_jwst(
                target,
                filtered,
                wavelength_key,
                value_key,
                uncertainty_key,
            )

        else:
            self.reference_table.setRowCount(0)
            self.reference_table.setColumnCount(0)
            self.reference_meta.clear()
            overlay_payload = None

        self.reference_table.resizeColumnsToContents()

        self._reference_overlay_payload = overlay_payload
        has_overlay = overlay_payload is not None and bool(overlay_payload.get("x_nm"))
        self.reference_overlay_toggle.setEnabled(has_overlay)
        if not has_overlay:
            if self.reference_overlay_toggle.isChecked():
                self.reference_overlay_toggle.blockSignals(True)
                self.reference_overlay_toggle.setChecked(False)
                self.reference_overlay_toggle.blockSignals(False)
            self._remove_reference_overlay()
        self._update_reference_overlay()

    def _filter_reference_entries(
        self, entries: List[Mapping[str, Any]], query: str
    ) -> List[Mapping[str, Any]]:
        if not query:
            return entries
        needle = query.lower()
        filtered: List[Mapping[str, Any]] = []
        for entry in entries:
            tokens = " ".join(token.lower() for token in ReferenceLibrary.flatten_entry(entry))
            if needle in tokens:
                filtered.append(entry)
        return filtered

    def _on_reference_overlay_toggled(self, _: bool) -> None:
        self._update_reference_overlay()

    def _clear_reference_plot(self) -> None:
        if not hasattr(self, "reference_plot"):
            return
        plot_item = self.reference_plot.getPlotItem()
        plot_item.clear()
        plot_item.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
        for item in list(self._reference_items):
            try:
                self.reference_plot.removeItem(item)
            except ValueError:
                pass
        self._reference_items.clear()
        self.reference_plot.setLabel("bottom", "Wavelength", units=self.plot_unit())
        self.reference_plot.setLabel("left", "Normalised amplitude")

    def _reference_trace_key(self, kind: str, key: Optional[str]) -> str:
        token = (key or kind or "reference").strip().lower().replace(" ", "_")
        return f"reference::{token}"

    def _render_reference_spectral_lines(
        self, entries: List[Mapping[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        overlay_x: List[float] = []
        overlay_y: List[float] = []
        x_nm_values: List[float] = []
        for entry in entries:
            lam = entry.get("vacuum_wavelength_nm")
            if lam is None:
                continue
            try:
                lam_nm = float(lam)
            except (TypeError, ValueError):
                continue
            x_nm_values.append(lam_nm)
            x_disp = self.plot._x_nm_to_disp(np.array([lam_nm], dtype=float))
            line = pg.InfiniteLine(pos=float(x_disp[0]), angle=90, pen=pg.mkPen("#8E44AD", width=1.4))
            line.setZValue(5)
            self.reference_plot.addItem(line)
            self._reference_items.append(line)
            intensity = entry.get("relative_intensity")
            try:
                rel = float(intensity) if intensity is not None else 1.0
            except (TypeError, ValueError):
                rel = 1.0
            overlay_x.extend([lam_nm, lam_nm, np.nan])
            overlay_y.extend([0.0, rel, np.nan])
        if not x_nm_values:
            return None
        disp_values = self.plot._x_nm_to_disp(np.array(x_nm_values, dtype=float))
        self.reference_plot.setXRange(float(np.min(disp_values)), float(np.max(disp_values)), padding=0.05)
        self.reference_plot.setYRange(0.0, 1.05)
        self.reference_plot.setLabel("left", "Relative intensity (normalised)")
        y_array = np.array(overlay_y, dtype=float)
        finite = np.isfinite(y_array)
        if finite.any():
            max_val = np.max(y_array[finite])
            if max_val <= 0:
                max_val = 1.0
            y_array[finite] = y_array[finite] / max_val
        x_array = np.array(overlay_x, dtype=float)
        return {
            "key": self._reference_trace_key("spectral_lines", None),
            "alias": "Reference: Hydrogen lines",
            "x_nm": x_array,
            "y": y_array,
            "style": TraceStyle(color=QtGui.QColor("#8E44AD"), width=2.0, show_in_legend=True),
        }

    def _render_reference_ir_groups(
        self, entries: List[Mapping[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        overlay_x: List[float] = []
        overlay_y: List[float] = []
        disp_bounds: List[float] = []
        brush = pg.mkBrush(22, 160, 133, 60)
        pen = pg.mkPen(22, 160, 133, 120)
        for entry in entries:
            wmin = entry.get("wavenumber_cm_1_min")
            wmax = entry.get("wavenumber_cm_1_max")
            if wmin in (None, 0) or wmax in (None, 0):
                continue
            try:
                wmin_val = float(wmin)
                wmax_val = float(wmax)
            except (TypeError, ValueError):
                continue
            nm_a = 1e7 / wmin_val
            nm_b = 1e7 / wmax_val
            start_nm, end_nm = sorted([nm_a, nm_b])
            disp_range = self.plot._x_nm_to_disp(np.array([start_nm, end_nm], dtype=float))
            region = pg.LinearRegionItem(values=sorted(disp_range.tolist()), brush=brush, pen=pen, movable=False)
            region.setZValue(-1)
            self.reference_plot.addItem(region)
            self._reference_items.append(region)
            overlay_x.extend([start_nm, start_nm, end_nm, end_nm, np.nan])
            overlay_y.extend([0.0, 1.0, 1.0, 0.0, np.nan])
            disp_bounds.extend(disp_range.tolist())
        if not overlay_x:
            return None
        if disp_bounds:
            self.reference_plot.setXRange(float(np.min(disp_bounds)), float(np.max(disp_bounds)), padding=0.05)
        self.reference_plot.setYRange(0.0, 1.05)
        self.reference_plot.setLabel("left", "Band occupancy (normalised)")
        x_array = np.array(overlay_x, dtype=float)
        y_array = np.array(overlay_y, dtype=float)
        return {
            "key": self._reference_trace_key("ir_groups", None),
            "alias": "Reference: IR functional groups",
            "x_nm": x_array,
            "y": y_array,
            "style": TraceStyle(color=QtGui.QColor("#16A085"), width=1.8, show_in_legend=True),
        }

    def _render_reference_jwst(
        self,
        target: Mapping[str, Any],
        entries: List[Mapping[str, Any]],
        wavelength_key: str,
        value_key: str,
        uncertainty_key: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        wavelengths_nm: List[float] = []
        values: List[float] = []
        errors: List[float] = []
        for entry in entries:
            lam = entry.get(wavelength_key)
            val = entry.get(value_key)
            if lam is None or val is None:
                continue
            try:
                lam_val = float(lam)
                val_val = float(val)
            except (TypeError, ValueError):
                continue
            key_lower = wavelength_key.lower()
            if "um" in key_lower or "µm" in key_lower:
                lam_nm = lam_val * 1e3
            elif "nm" in key_lower:
                lam_nm = lam_val
            elif "cm" in key_lower:
                if lam_val == 0:
                    continue
                lam_nm = 1e7 / lam_val
            else:
                lam_nm = lam_val
            wavelengths_nm.append(lam_nm)
            values.append(val_val)
            if uncertainty_key:
                unc = entry.get(uncertainty_key)
                try:
                    errors.append(abs(float(unc)))
                except (TypeError, ValueError):
                    errors.append(0.0)
        if not wavelengths_nm:
            return None
        x_disp = self.plot._x_nm_to_disp(np.array(wavelengths_nm, dtype=float))
        curve = pg.PlotDataItem(x_disp, np.array(values, dtype=float), pen=pg.mkPen("#2980B9", width=2.0))
        self.reference_plot.addItem(curve)
        self._reference_items.append(curve)
        if uncertainty_key and any(err > 0 for err in errors):
            error_item = pg.ErrorBarItem(
                x=x_disp,
                y=np.array(values, dtype=float),
                height=np.array(errors, dtype=float),
                pen=pg.mkPen("#2980B9", width=1.2),
            )
            self.reference_plot.addItem(error_item)
            self._reference_items.append(error_item)
        self.reference_plot.setXRange(float(np.min(x_disp)), float(np.max(x_disp)), padding=0.05)
        self.reference_plot.setLabel("left", str(target.get("data_units", "Measurement")))
        alias_bits = [f"Reference: {target.get('name', 'JWST target')}" ]
        instrument = target.get("instrument")
        if instrument:
            alias_bits.append(str(instrument))
        units = target.get("data_units")
        if units:
            alias_bits.append(str(units))
        resolution = target.get("spectral_resolution")
        if resolution:
            alias_bits.append(f"R≈{resolution}")
        alias = " | ".join(alias_bits)
        overlay_x = np.array(wavelengths_nm, dtype=float)
        overlay_y = np.array(values, dtype=float)
        finite = np.isfinite(overlay_y)
        if finite.any():
            max_abs = np.max(np.abs(overlay_y[finite]))
            if max_abs <= 0:
                max_abs = 1.0
            overlay_y = overlay_y / max_abs
        else:
            overlay_y = np.zeros_like(overlay_y)
        return {
            "key": self._reference_trace_key("jwst", str(target.get("id", "jwst"))),
            "alias": alias,
            "x_nm": overlay_x,
            "y": overlay_y,
            "style": TraceStyle(color=QtGui.QColor("#2980B9"), width=2.0, show_in_legend=True),
        }

    def _update_reference_overlay(self) -> None:
        payload = self._reference_overlay_payload if self.reference_overlay_toggle.isChecked() else None
        current_key = self._reference_overlay_key
        if payload is None:
            if current_key:
                self.plot.remove_trace(current_key)
                self._reference_overlay_key = None
            return
        key = cast(str, payload.get("key", "reference"))
        if current_key and current_key != key:
            self.plot.remove_trace(current_key)
        x_nm = np.asarray(payload.get("x_nm", []), dtype=float)
        y = np.asarray(payload.get("y", []), dtype=float)
        style = cast(TraceStyle, payload.get("style", TraceStyle(color=QtGui.QColor("#8E44AD"))))
        alias = cast(str, payload.get("alias", key))
        if not x_nm.size:
            if current_key:
                self.plot.remove_trace(current_key)
                self._reference_overlay_key = None
            return
        self.plot.add_trace(key=key, alias=alias, x_nm=x_nm, y=y, style=style)
        self.plot.set_visible(key, True)
        self._reference_overlay_key = key

    def _remove_reference_overlay(self) -> None:
        if self._reference_overlay_key:
            self.plot.remove_trace(self._reference_overlay_key)
            self._reference_overlay_key = None

    def _set_reference_meta(self, title: Optional[str], url: Optional[str], notes: Optional[str]) -> None:
        pieces: List[str] = []
        if title:
            pieces.append(f"<b>{title}</b>")
        if url:
            pieces.append(f"<a href='{url}'>{url}</a>")
        if notes:
            pieces.append(notes)
        if pieces:
            self.reference_meta.setHtml("<p>" + "<br/>".join(pieces) + "</p>")
        else:
            self.reference_meta.clear()

    @staticmethod
    def _merge_provenance(meta: Mapping[str, Any]) -> Optional[str]:
        notes = str(meta.get("notes", "")) if meta.get("notes") else ""
        retrieved = meta.get("retrieved_utc")
        provenance = meta.get("provenance") if isinstance(meta.get("provenance"), Mapping) else None
        details: List[str] = []
        if retrieved:
            details.append(f"Retrieved: {retrieved}")
        if provenance:
            status = provenance.get("curation_status")
            if status:
                details.append(f"Curation status: {status}")
            generator = provenance.get("generator")
            if generator:
                details.append(f"Generator: {generator}")
            replacement = provenance.get("replacement_plan") or provenance.get("planned_regeneration_uri")
            if replacement:
                details.append(f"Next steps: {replacement}")
        segments: List[str] = []
        if notes:
            segments.append(notes)
        if details:
            segments.append("; ".join(details))
        if not segments:
            return None
        return "<br/>".join(segments)

    @staticmethod
    def _format_target_provenance(provenance: Optional[Mapping[str, Any]]) -> str:
        if not isinstance(provenance, Mapping):
            return ""
        bits: List[str] = []
        status = provenance.get("curation_status")
        if status:
            bits.append(f"Status: {status}")
        if provenance.get("pipeline_version"):
            bits.append(f"Pipeline: {provenance['pipeline_version']}")
        if provenance.get("mast_product_uri"):
            bits.append(f"MAST URI: {provenance['mast_product_uri']}")
        if provenance.get("planned_regeneration_uri"):
            bits.append(f"Planned URI: {provenance['planned_regeneration_uri']}")
        if provenance.get("retrieved_utc"):
            bits.append(f"Retrieved: {provenance['retrieved_utc']}")
        if provenance.get("notes"):
            bits.append(provenance["notes"])
        if provenance.get("reference"):
            bits.append(f"Reference: {provenance['reference']}")
        if not bits:
            return ""
        return "<p><i>" + " | ".join(bits) + "</i></p>"

    @staticmethod
    def _format_float(value: Any, *, precision: int = 3) -> str:
        if value is None:
            return "–"
        try:
            return f"{float(value):.{precision}f}"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_scientific(value: Any) -> str:
        if value is None:
            return "–"
        try:
            return f"{float(value):.3e}"
        except (TypeError, ValueError):
            return str(value)

    def _set_table_item(self, row: int, column: int, value: Any) -> None:
        text = str(value) if value not in (None, "") else "–"
        item = QtWidgets.QTableWidgetItem(text)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        try:
            float(value)
        except (TypeError, ValueError):
            pass
        else:
            item.setTextAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        self.reference_table.setItem(row, column, item)

    # Documentation -----------------------------------------------------
    def _build_documentation_tab(self) -> None:
        self.tab_docs = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.tab_docs)
        layout.setContentsMargins(6, 6, 6, 6)

        self.docs_filter = QtWidgets.QLineEdit()
        self.docs_filter.setPlaceholderText("Filter topics…")
        self.docs_filter.textChanged.connect(self._filter_docs)
        layout.addWidget(self.docs_filter)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        self.docs_list = QtWidgets.QListWidget()
        self.docs_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.docs_list.itemSelectionChanged.connect(self._on_doc_selection_changed)
        splitter.addWidget(self.docs_list)

        self.doc_viewer = QtWidgets.QTextBrowser()
        self.doc_viewer.setOpenExternalLinks(False)
        self.doc_viewer.setPlaceholderText("Select a document to view its contents.")
        splitter.addWidget(self.doc_viewer)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        self.doc_placeholder = QtWidgets.QLabel("No documentation topics found in docs/user.")
        self.doc_placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.doc_placeholder)

    def _load_documentation_index(self) -> None:
        docs_root = Path(__file__).resolve().parent.parent / "docs" / "user"
        entries: list[tuple[str, Path]] = []
        if docs_root.exists():
            for path in sorted(docs_root.glob("*.md")):
                entries.append((self._extract_doc_title(path), path))

        self._doc_entries = entries
        self.docs_list.clear()
        for title, path in entries:
            item = QtWidgets.QListWidgetItem(title)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, path)
            item.setData(QtCore.Qt.ItemDataRole.UserRole + 1, title.lower())
            self.docs_list.addItem(item)

        has_docs = bool(entries)
        self.doc_placeholder.setVisible(not has_docs)
        self.doc_viewer.setVisible(has_docs)
        if has_docs:
            self.docs_list.setCurrentRow(0)
        else:
            self.doc_viewer.clear()

    def _extract_doc_title(self, path: Path) -> str:
        try:
            with path.open("r", encoding="utf-8") as handle:
                for _ in range(40):
                    line = handle.readline()
                    if not line:
                        break
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        return stripped.lstrip("# ")
        except OSError:
            return path.stem
        return path.stem.replace("_", " ").title()

    def _filter_docs(self, text: str) -> None:
        query = text.strip().lower()
        for idx in range(self.docs_list.count()):
            item = self.docs_list.item(idx)
            if not query:
                item.setHidden(False)
                continue
            haystack = item.data(QtCore.Qt.ItemDataRole.UserRole + 1) or ""
            item.setHidden(query not in haystack)
        if query:
            for idx in range(self.docs_list.count()):
                item = self.docs_list.item(idx)
                if not item.isHidden():
                    self.docs_list.setCurrentItem(item)
                    break

    def _on_doc_selection_changed(self) -> None:
        items = self.docs_list.selectedItems()
        if not items:
            self.doc_viewer.clear()
            return
        item = items[0]
        path = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not isinstance(path, Path):
            self.doc_viewer.clear()
            return
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - filesystem failure feedback
            self.doc_viewer.setPlainText(f"Failed to load {path.name}: {exc}")
            self._log("Docs", f"Failed to open {path.name}: {exc}")
            return
        if hasattr(self.doc_viewer, "setMarkdown"):
            self.doc_viewer.setMarkdown(text)
        else:  # pragma: no cover - Qt fallback
            self.doc_viewer.setPlainText(text)
        self._log("Docs", f"Loaded {path.name}")

    def show_documentation(self) -> None:
        self._load_documentation_index()
        self.inspector_dock.show()
        idx = self.inspector_tabs.indexOf(self.tab_docs)
        if idx != -1:
            self.inspector_tabs.setCurrentIndex(idx)
        self.raise_()

    def _rename_selected_spectrum(self) -> None:
        ids = self._selected_dataset_ids()
        if not ids:
            return
        spectrum_id = ids[-1]
        alias = self.info_alias.text().strip()
        if not alias:
            return
        item = self._dataset_items.get(spectrum_id)
        if item:
            item.setText(alias)
        self._update_math_selectors()
        spectrum = self.overlay_service.get(spectrum_id)
        self.info_name.setText(spectrum.name)
        self.plot.update_alias(spectrum_id, alias)
        self._log("Alias", f"{spectrum.name} → {alias}")

    def _on_normalize_changed(self, value: str) -> None:
        self._normalization_mode = value or "None"
        self.refresh_overlay()
        self._log("Normalize", f"Mode set to {self._normalization_mode}")

    def _on_smoothing_changed(self, value: str) -> None:
        self._log("Smoothing", f"Mode set to {value}")

    def _log(self, channel: str, message: str) -> None:
        if not self._log_ready or self.log_view is None:
            self._log_buffer.append((channel, message))
            return
        self.log_view.appendPlainText(f"[{channel}] {message}")


def json_pretty(data: dict) -> str:
    import json

    return json.dumps(data, indent=2, ensure_ascii=False)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = SpectraMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

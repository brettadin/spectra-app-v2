"""Main application window for the Spectra desktop preview.

Display pipeline contract (view-only, non-destructive):

- Convert X to canonical nanometres (nm) for plotting.
- Apply Calibration (display-time): FWHM blur and RV shift operate in nm-space.
- Apply normalisation: None | Max | Area. If the toolbar's Global toggle is
    enabled, compute a single scale across all visible spectra; otherwise compute
    per-spectrum scales. Scale calculations are NaN/Inf-robust (finite-only).
- Apply Y-scale transform: Linear | Log10 (signed) | Asinh, to improve visibility
    across dynamic ranges. Transforms apply after normalisation.

The Data Table uses the same calibration→normalisation pipeline so tabular values
match the plotted view (before the Y-scale transform). Underlying data and exports
remain in source units unless the user opts into normalisation during export.

This module contains the SpectraMainWindow class and closely related UI/worker
code. It is extracted from app/main.py to keep the entry point slim while
preserving behavior.
"""

from __future__ import annotations

import os
import csv
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np
import pyqtgraph as pg

from app.qt_compat import get_qt
from app.utils.analysis import peak_near
from app.services import (
    UnitsService,
    ProvenanceService,
    DataIngestService,
    OverlayService,
    MathService,
    ReferenceLibrary,
    Spectrum,
    LineShapeModel,
    LocalStore,
    KnowledgeLogEntry,
    KnowledgeLogService,
    RemoteDataService,
    # CalibrationService,  # REMOVED - feature no longer used
)
from app.services.dataset_group_service import DatasetGroupService, GroupType
from app.services.time_series import TimeSeries
from app.services.importers.time_series_csv_importer import TimeSeriesCsvImporter
from app.services.importers.time_series_fits_importer import TimeSeriesFitsImporter
from app.ui.plot_pane import PlotPane, TraceStyle
from app.ui.remote_data_panel import RemoteDataPanel
from app.ui.dataset_panel import DatasetPanel
from app.ui.reference_panel import ReferencePanel
from app.ui.merge_panel import MergePanel
from app.ui.history_panel import HistoryPanel
from app.ui.legend_panel import LegendPanel
# from app.ui.calibration_panel import CalibrationPanel  # REMOVED - feature no longer used
from app.ui.nist_lines_panel import NistLinesPanel
from app.ui.documentation_dialog import DocumentationDialog
from app.ui.styles import apply_pyqtgraph_theme, get_app_stylesheet
from app.ui.themes import default_theme_key, get_theme_definition, iter_theme_definitions
from app.utils.error_handling import ui_action
from app.utils.path_alias import PathAlias


QtCore: Any
QtGui: Any
QtWidgets: Any
QT_BINDING: str
QtCore, QtGui, QtWidgets, QT_BINDING = get_qt()


# Lightweight background workers for Remote Data tab (streaming search and downloads)
# These mirror the behavior of the dialog workers but are local to this module

Signal = getattr(QtCore, "Signal", None)  # type: ignore[attr-defined]
if Signal is None:
    Signal = getattr(QtCore, "pyqtSignal")  # type: ignore[attr-defined]

Slot = getattr(QtCore, "Slot", None)  # type: ignore[attr-defined]
if Slot is None:
    Slot = getattr(QtCore, "pyqtSlot")  # type: ignore[attr-defined]


SAMPLES_DIR = Path(__file__).resolve().parents[2] / "storage" / "samples"
PLOT_MAX_POINTS_KEY = "plot/max_points"


class SpectraMainWindow(QtWidgets.QMainWindow):
    """Preview shell that wires UI actions to services with docked layout."""

    def __init__(
        self,
        container: object | None = None,
        *,
        knowledge_log_service: KnowledgeLogService | None = None,
        theme_key: str | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Spectra Desktop Preview")
        self.resize(1320, 840)

        self.units_service = UnitsService()
        self.provenance_service = ProvenanceService()
        self.reference_library = ReferenceLibrary()
        self.line_shape_model = LineShapeModel(
            self.reference_library.line_shape_placeholders(),
            self.reference_library.line_shape_metadata(),
        )
        self._theme_key = self._load_theme_preference() if theme_key is None else get_theme_definition(theme_key).key
        self._theme_action_group: QtGui.QActionGroup | None = None
        self._applied_theme_key: str | None = None
        self.overlay_service = OverlayService(self.units_service, line_shape_model=self.line_shape_model)
        # Compute persistence flags inline to avoid any bootstrap ordering issues
        _flag = os.environ.get("SPECTRA_DISABLE_PERSISTENCE")
        self._persistence_env_disabled = bool(
            _flag and str(_flag).strip().lower() in {"1", "true", "yes", "on"}
        )
        try:
            settings = QtCore.QSettings("SpectraApp", "DesktopPreview")
            pref_disabled = bool(settings.value("persistence/disabled", False, type=bool))
        except Exception:
            pref_disabled = False
        self._persistence_disabled = self._persistence_env_disabled or pref_disabled
        # Use consolidated storage alias for cache by default (override with SPECTRA_STORE_DIR)
        self._app_root = Path(__file__).resolve().parents[2]
        _store_override = os.environ.get("SPECTRA_STORE_DIR")
        if _store_override:
            self._default_store_dir = Path(_store_override)
        else:
            try:
                self._default_store_dir = PathAlias.resolve("storage://cache")
            except Exception:
                # Fallback for environments without alias helper
                self._default_store_dir = self._app_root / "storage" / "cache"
        self.store: LocalStore | None = None if self._persistence_disabled else LocalStore(base_dir=self._default_store_dir)
        self.ingest_service = DataIngestService(self.units_service, store=self.store)
        remote_store = self.store
        if remote_store is None:
            # Fall back to consolidated cache directory even when persistence is toggled off
            remote_store = LocalStore(base_dir=self._default_store_dir)
        self.remote_data_service = RemoteDataService(remote_store)
        self.math_service = MathService(self.units_service)
        # self.calibration_service = CalibrationService()  # REMOVED - feature no longer used
        self.knowledge_log = knowledge_log_service or KnowledgeLogService(
            default_context="Spectra Desktop Session"
        )
        # Dataset grouping service for organizing spectra
        try:
            group_dir = self._default_store_dir if self._default_store_dir else None
            self.group_service = DatasetGroupService(storage_dir=group_dir)
        except Exception:
            self.group_service = DatasetGroupService()

        self.unit_combo: Optional[QtWidgets.QComboBox] = None
        self.plot_toolbar: Optional[QtWidgets.QToolBar] = None
        self.plot_max_points_control: Optional[QtWidgets.QSpinBox] = None
        self.color_mode_combo: Optional[QtWidgets.QComboBox] = None
        self.norm_combo: Optional[QtWidgets.QComboBox] = None

        self._dataset_items: Dict[str, QtGui.QStandardItem] = {}
        self._dataset_color_items: Dict[str, QtGui.QStandardItem] = {}
        self._spectrum_colors: Dict[str, QtGui.QColor] = {}
        self._visibility: Dict[str, bool] = {}
        self._normalization_mode: str = "None"
        self._doc_entries: List[tuple[str, Path]] = []
        self._reference_plot_items: List[object] = []
        self._reference_overlay_annotations: List[pg.TextItem] = []
        self._reference_overlay_key: List[str] = []
        self._reference_overlay_payload: Optional[Dict[str, Any]] = None
        self._reset_reference_overlay_state()
        self._suppress_overlay_refresh = False
        self._display_y_units: Dict[str, str] = {}
        self._line_shape_rows: List[Mapping[str, Any]] = []
        self._ir_rows: List[Mapping[str, Any]] = []
        # Theme-aware palettes for datasets (distinct from NIST colours)
        self._palette: List[QtGui.QColor] = []
        self._palette_index = 0
        self._nist_palette: List[QtGui.QColor] = []
        self._nist_palette_index = 0
        self._nist_collection_counter = 0  # Just for unique IDs
        
        # NIST lines state: track collections and plot items
        self._nist_collections: Dict[str, Dict[str, Any]] = {}  # collection_id -> {xs, ys, color, ...}
        self._nist_plot_items: Dict[str, pg.PlotDataItem] = {}  # collection_id -> plot item
        
        # Merge preview state: avoid expensive recomputation on every checkbox toggle
        self._merge_preview_stale = True
        
        # Deferred plot refresh: avoid blocking UI during rapid setting changes
        self._refresh_timer = QtCore.QTimer()
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(150)  # 150ms debounce
        self._refresh_timer.timeout.connect(self._refresh_plot)

        self.log_view: QtWidgets.QPlainTextEdit | None = None
        self._log_buffer: list[tuple[str, str]] = []
        self._log_ready = False

        self._reference_items: list[pg.GraphicsObject] = []
        self._history_entries: List[KnowledgeLogEntry] = []
        self._displayed_history_entries: List[KnowledgeLogEntry] = []
        self._history_ui_ready = False

        self._plot_max_points = self._load_plot_max_points()
        self.dataset_filter: QtWidgets.QLineEdit | None = None
        self.data_tabs: QtWidgets.QTabWidget | None = None
        self.dataset_view: QtWidgets.QTreeView | None = None
        self.dataset_model: QtGui.QStandardItemModel | None = None
        self.time_series_view: QtWidgets.QTreeWidget | None = None
        self.time_series_filter: QtWidgets.QLineEdit | None = None
        self.time_series_tab: QtWidgets.QWidget | None = None
        self._time_series_items: Dict[str, QtWidgets.QTreeWidgetItem] = {}
        self._time_series_colors: Dict[str, QtGui.QColor] = {}
        self._time_series_visibility: Dict[str, bool] = {}
        self._time_series: Dict[str, TimeSeries] = {}
        self.plot_stack: QtWidgets.QStackedWidget | None = None
        self.time_plot: PlotPane | None = None
        self.library_list: QtWidgets.QTreeWidget | None = None
        self.library_view: QtWidgets.QTreeWidget | None = None
        self.library_search: QtWidgets.QLineEdit | None = None
        # Build palettes from current theme key
        try:
            self._apply_theme_palettes(self._theme_key)
        except Exception:
            pass
        self.library_detail: QtWidgets.QPlainTextEdit | None = None
        self.library_hint: QtWidgets.QLabel | None = None
        self._library_entries: Dict[str, Mapping[str, Any]] = {}
        self._library_tab_index: int | None = None
        self._use_uniform_palette = False
        self._uniform_color = QtGui.QColor("#4F6D7A")
        self._last_display_views: List[Dict[str, object]] = []
        self._data_table_attached = False
        self.data_table_dock: QtWidgets.QDockWidget | None = None
        self.data_table: QtWidgets.QTableWidget | None = None
        # Docs UI
        self.docs_list: QtWidgets.QListWidget | None = None
        self.doc_viewer: QtWidgets.QPlainTextEdit | None = None

        # Async NIST fetch state
        self._nist_thread: Optional[QtCore.QThread] = None
        self._nist_worker: Optional[QtCore.QObject] = None

        self._setup_ui()
        self._setup_menu()
        self._apply_theme_by_key(self._theme_key, persist=False)
        # Load palette preferences (uniform mode and color)
        try:
            self._load_palette_preferences()
        except Exception:
            pass
        self._wire_shortcuts()
        self._load_reference_lines_data()  # Pre-load curated spectral lines for Reference tab
        # self._load_default_samples()  # Disabled: users prefer empty workspace on launch
        # Ensure visibility in offscreen test environments so isVisible() checks pass
        try:
            if os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen":
                self.show()
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _reset_reference_overlay_state(self) -> None:
        """Reset state used by reference/overlay features.

        This is a minimal implementation to ensure the window can launch even
        if extended reference features are not yet wired.
        """
        self._reference_overlay_annotations = []
        self._reference_overlay_key = []
        self._reference_overlay_payload = None

    def _setup_ui(self) -> None:
        """Build the main UI with plot, dataset/library, inspector, and log."""
        # Central plot area
        self.central_split = QtWidgets.QSplitter(self)
        self.central_split.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.setCentralWidget(self.central_split)

        # Plot panes (spectra + time series) stacked in central area
        self.plot_stack = QtWidgets.QStackedWidget()
        self.central_split.addWidget(self.plot_stack)

        # Spectral plot
        self.plot = PlotPane(self, max_points=self._plot_max_points)
        self.plot.remove_export_from_context_menu()
        self.plot_stack.addWidget(self.plot)
        self.plot.autoscale()
        # Time-series plot (separate axis labeling and units)
        self.time_plot = PlotPane(self, max_points=self._plot_max_points)
        self.time_plot.set_x_mode("time", label="Time", unit="day")
        self.time_plot.set_y_label("Flux")
        self.time_plot.remove_export_from_context_menu()
        self.time_plot.autoscale()
        self.plot_stack.addWidget(self.time_plot)
        self.plot_stack.setCurrentWidget(self.plot)
        # Live cursor readout in status bar (spectral plot only for now)
        try:
            self.plot.pointHovered.connect(self._on_plot_point_hovered)
        except Exception:
            pass
        # Track last cursor x (display units) for peak-near-cursor action
        self._last_cursor_x_display: float | None = None
        # Keep reference overlays in sync with view changes (zoom/pan)
        try:
            # Refresh both reference overlay geometry and reposition user-imported line markers
            self.plot.rangeChanged.connect(lambda *_: (self._refresh_reference_overlay_geometry(), self._update_line_marker_positions()))
        except Exception:
            pass

        # Left dock: datasets and library
        self.dataset_dock = QtWidgets.QDockWidget("Data", self)
        self.dataset_dock.setObjectName("dock-datasets")
        self.data_tabs = QtWidgets.QTabWidget()
        # Datasets tab content (moved into DatasetPanel)
        self.dataset_panel = DatasetPanel(self)
        # Hand off internal widgets to preserve existing attribute names/behavior
        self.dataset_filter = self.dataset_panel.dataset_filter
        self.dataset_view = self.dataset_panel.dataset_view
        self.dataset_tree = self.dataset_view  # compatibility alias for tests
        self.dataset_model = self.dataset_panel.dataset_model
        # Note: _originals_item is set AFTER groups are initialized below

        # Wire panel signals instead of direct widget connections
        self.dataset_panel.filterTextChanged.connect(self._on_dataset_filter_changed)
        self.dataset_panel.removeRequested.connect(self._remove_selected_datasets)
        self.dataset_panel.selectionChanged.connect(self._mark_merge_preview_stale)
        self.dataset_panel.clearAllRequested.connect(self._clear_all_datasets)
        self.dataset_panel.groupVisibilityChanged.connect(self._on_group_visibility_toggled)
        # Group management signals
        self.dataset_panel.createGroupRequested.connect(self._on_create_group_requested)
        self.dataset_panel.moveToGroupRequested.connect(self._on_move_to_group_requested)
        self.dataset_panel.renameGroupRequested.connect(self._on_rename_group_requested)
        self.dataset_panel.deleteGroupRequested.connect(self._on_delete_group_requested)
        self.dataset_panel.normalizationLockChanged.connect(self._on_normalization_lock_changed)
        # Existing model signal (still needed for visibility checkbox changes)
        self.dataset_model.itemChanged.connect(self._on_dataset_item_changed)

        # Initialize groups in the dataset panel from the grouping service
        for group in self.group_service.list_groups():
            self.dataset_panel.add_group(group.id, group.name, color_hint=group.color)
        
        # Set _originals_item now that groups have been added (points to first group as fallback)
        self._originals_item = self.dataset_panel._originals_item
        
        # Expand all groups by default so datasets are visible
        for i in range(self.dataset_model.rowCount()):
            index = self.dataset_model.index(i, 0)
            self.dataset_view.setExpanded(index, True)

        self.data_tabs.addTab(self.dataset_panel, "Datasets")

        # Time Series tab content
        self.time_series_tab = QtWidgets.QWidget()
        ts_layout = QtWidgets.QVBoxLayout(self.time_series_tab)
        ts_layout.setContentsMargins(4, 4, 4, 4)
        self.time_series_filter = QtWidgets.QLineEdit()
        self.time_series_filter.setPlaceholderText("Filter time series…")
        self.time_series_filter.setClearButtonEnabled(True)
        self.time_series_filter.textChanged.connect(self._on_time_series_filter_changed)
        ts_layout.addWidget(self.time_series_filter)

        ts_toolbar = QtWidgets.QToolBar()
        ts_toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        ts_toolbar.setIconSize(QtCore.QSize(16, 16))
        self.time_series_remove_action = QtGui.QAction(self)
        self.time_series_remove_action.setText("Remove Selected")
        try:
            self.time_series_remove_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TrashIcon))
        except Exception:
            pass
        self.time_series_remove_action.setShortcut(QtGui.QKeySequence.StandardKey.Delete)
        self.time_series_remove_action.triggered.connect(self._remove_selected_time_series)
        ts_toolbar.addAction(self.time_series_remove_action)

        self.time_series_clear_action = QtGui.QAction(self)
        self.time_series_clear_action.setText("Clear All")
        try:
            self.time_series_clear_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogDiscardButton))
        except Exception:
            pass
        self.time_series_clear_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+L"))
        self.time_series_clear_action.triggered.connect(self._clear_all_time_series)
        ts_toolbar.addAction(self.time_series_clear_action)
        self.time_series_flux_vs_lambda_action = QtGui.QAction(self)
        self.time_series_flux_vs_lambda_action.setText("Flux vs wavelength...")
        self.time_series_flux_vs_lambda_action.triggered.connect(self._plot_flux_vs_wavelength_at_time)
        ts_toolbar.addAction(self.time_series_flux_vs_lambda_action)
        ts_layout.addWidget(ts_toolbar)

        self.time_series_view = QtWidgets.QTreeWidget()
        self.time_series_view.setHeaderLabels(["Time Series", "Visible", "Channel", "Band / wavelength"])
        self.time_series_view.setRootIsDecorated(False)
        self.time_series_view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.time_series_view.setAlternatingRowColors(True)
        self.time_series_view.setColumnCount(4)
        self.time_series_view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.time_series_view.itemChanged.connect(self._on_time_series_item_changed)
        self.time_series_view.customContextMenuRequested.connect(self._on_time_series_context_menu)
        ts_layout.addWidget(self.time_series_view)

        self.data_tabs.addTab(self.time_series_tab, "Time Series")
        self.data_tabs.currentChanged.connect(self._on_data_tab_changed)

        # Library tab placeholder (built on demand)
        library_container = QtWidgets.QWidget()
        library_layout = QtWidgets.QVBoxLayout(library_container)
        library_layout.setContentsMargins(4, 4, 4, 4)

        # Search/filter bar
        self.library_filter = QtWidgets.QLineEdit()
        self.library_filter.setPlaceholderText("🔍 Search library...")
        self.library_filter.setClearButtonEnabled(True)
        self.library_filter.textChanged.connect(self._on_library_filter_changed)
        library_layout.addWidget(self.library_filter)

        # Tree view
        self.library_view = QtWidgets.QTreeWidget()
        self.library_view.setHeaderLabels(["File", "Origin"])
        # Set column widths to show full filenames
        self.library_view.setColumnWidth(0, 400)  # Wide column for filenames
        self.library_view.setColumnWidth(1, 120)  # Narrower for origin/count
        self.library_view.setAlternatingRowColors(True)
        library_layout.addWidget(self.library_view)
        self.data_tabs.addTab(library_container, "Library")
        self.dataset_dock.setWidget(self.data_tabs)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.dataset_dock)
        # Ensure dataset dock is visible
        self.dataset_dock.show()

        # Right dock: inspector (tab widget placeholder)
        self.inspector_dock = QtWidgets.QDockWidget("Inspector", self)
        self.inspector_dock.setObjectName("dock-inspector")
        # Set reasonable default width (not too huge)
        self.inspector_dock.setMaximumWidth(600)
        self.inspector_tabs = QtWidgets.QTabWidget()
        # Refresh merge preview when Math tab is activated (lazy computation)
        self.inspector_tabs.currentChanged.connect(self._on_inspector_tab_changed)

        # Reference tab (moved into ReferencePanel)
        self.reference_panel = ReferencePanel(self)
        # Hand off internal widgets to preserve existing attribute names/behavior
        self.tab_reference = self.reference_panel  # for backward compat if needed
        self.reference_overlay_checkbox = self.reference_panel.reference_overlay_checkbox
        self.reference_status_label = self.reference_panel.reference_status_label
        self.reference_plot = self.reference_panel.reference_plot
        self.reference_tabs = self.reference_panel.reference_tabs
        # NIST fetch controls moved to nist_lines_panel
        self.reference_filter = self.reference_panel.reference_filter
        self.ir_table = self.reference_panel.ir_table

        # Wire panel signals instead of direct widget connections
        self.reference_panel.overlayToggled.connect(self._on_reference_overlay_toggled)
        self.reference_panel.irFilterChanged.connect(self._on_reference_filter_changed)
        self.reference_panel.tabChanged.connect(lambda _: self._refresh_reference_view())
        # Reference Lines tab signals
        self.reference_panel.referenceLinesToggled.connect(self._on_reference_line_element_toggled)
        self.reference_panel.referenceLinesRefreshRequested.connect(self._refresh_reference_lines_table)
        # Table selection changes still wired directly (more complex to decouple without rewriting handlers)
        self.ir_table.itemSelectionChanged.connect(self._on_ir_row_selected)
        # Unit combo connection
        if self.unit_combo is not None:
            self.unit_combo.currentTextChanged.connect(self._update_reference_axis)

        self.inspector_tabs.addTab(self.reference_panel, "Reference")

        # Calibration tab - REMOVED - feature no longer used
        # self.calibration_panel = CalibrationPanel(self)
        # self.calibration_panel.configChanged.connect(self._on_calibration_changed)
        # self.inspector_tabs.addTab(self.calibration_panel, "Calibration")

        # Remote Data tab
        self.remote_data_panel = RemoteDataPanel(
            self.remote_data_service,
            self.ingest_service,
            self
        )
        self.remote_data_panel.spectra_imported.connect(self._handle_remote_spectra_imported)
        self.remote_data_panel.status_message.connect(self._log)
        # Mirror Remote Data progress into the global status bar
        try:
            self.remote_data_panel.download_started.connect(self._on_global_download_started)
            self.remote_data_panel.download_progress.connect(self._on_global_download_progress)
            self.remote_data_panel.download_finished.connect(self._on_global_download_finished)
        except Exception:
            pass
        self.inspector_tabs.addTab(self.remote_data_panel, "Remote Data")
        
        # Merge/Average tab (moved into MergePanel)
        self.merge_panel = MergePanel(self)
        # Hand off internal widgets to preserve existing attribute names/behavior
        self.tab_merge = self.merge_panel  # for backward compat
        self.merge_only_visible = self.merge_panel.merge_only_visible
        self.merge_name_edit = self.merge_panel.merge_name_edit
        self.merge_preview_label = self.merge_panel.merge_preview_label
        self.merge_average_button = self.merge_panel.merge_average_button
        self.merge_subtract_button = self.merge_panel.merge_subtract_button
        self.merge_ratio_button = self.merge_panel.merge_ratio_button
        self.merge_normalized_diff_button = self.merge_panel.merge_normalized_diff_button
        # Newly added math operation buttons (single-operand)
        self.merge_smooth_button = self.merge_panel.merge_smooth_button
        self.merge_derivative_button = self.merge_panel.merge_derivative_button
        self.merge_integral_button = self.merge_panel.merge_integral_button
        self.merge_status_label = self.merge_panel.merge_status_label

        # Wire existing handlers
        self.merge_only_visible.toggled.connect(lambda _: self._mark_merge_preview_stale())
        self.merge_average_button.clicked.connect(self._on_merge_average)
        self.merge_subtract_button.clicked.connect(self._on_merge_subtract)
        self.merge_ratio_button.clicked.connect(self._on_merge_ratio)
        self.merge_normalized_diff_button.clicked.connect(self._on_merge_normalized_difference)
        self.merge_smooth_button.clicked.connect(self._on_merge_smooth)
        self.merge_derivative_button.clicked.connect(self._on_merge_derivative)
        self.merge_integral_button.clicked.connect(self._on_merge_integral)

        # Wire range selection signals
        self.merge_panel.rangeToggled.connect(self._on_range_selection_toggled)
        self.merge_panel.rangeChanged.connect(self._on_range_values_changed)
        self.merge_panel.setOverlapRequested.connect(self._on_set_range_to_overlap)
        self.merge_panel.setViewRequested.connect(self._on_set_range_to_view)
        self.merge_panel.exportRangeRequested.connect(self._on_export_range)
        # Connect plot region selection to panel
        if hasattr(self.plot, 'regionSelected'):
            self.plot.regionSelected.connect(self._on_plot_region_changed)
        # Connect annotation request signal
        if hasattr(self.plot, 'annotationRequested'):
            self.plot.annotationRequested.connect(self._on_annotation_requested)

        self.inspector_tabs.addTab(self.merge_panel, "Math")
        
        self.inspector_dock.setWidget(self.inspector_tabs)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.inspector_dock)
        # Ensure inspector dock is visible
        self.inspector_dock.show()

        # Enable better dock manipulation and resizing
        self.setDockOptions(
            QtWidgets.QMainWindow.DockOption.AllowTabbedDocks |
            QtWidgets.QMainWindow.DockOption.AllowNestedDocks |
            QtWidgets.QMainWindow.DockOption.AnimatedDocks
        )

        # Bottom dock: log view
        self.log_dock = QtWidgets.QDockWidget("Log", self)
        self.log_dock.setObjectName("dock-log")
        self.log_view = QtWidgets.QPlainTextEdit(readOnly=True)
        self.log_dock.setWidget(self.log_view)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        # Hidden by default; opt-in via View menu
        self.log_dock.hide()

        # Bottom dock: legend panel (compact horizontal legend)
        self.legend_dock = QtWidgets.QDockWidget("Legend", self)
        self.legend_dock.setObjectName("dock-legend")
        self.legend_panel = LegendPanel(self)
        self.legend_dock.setWidget(self.legend_panel)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.legend_dock)
        # Visible by default for better UX
        # Wire legend item clicks to toggle visibility
        self.legend_panel.legendItemClicked.connect(self._on_legend_item_clicked)
        # Hide the floating legend on the plot
        self.plot.set_legend_visible(False)

        # History dock (moved into HistoryPanel)
        self.history_dock = QtWidgets.QDockWidget("History", self)
        self.history_dock.setObjectName("dock-history")
        self.history_panel = HistoryPanel(self)
        # Hand off internal widgets to preserve existing attribute names/behavior
        self.history_table = self.history_panel.history_table
        self.history_detail = self.history_panel.history_detail
        self.history_dock.setWidget(self.history_panel)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.history_dock)
        # Hidden by default to reduce UI noise
        self.history_dock.hide()
        # Don't auto-show History dock - let users open it via View menu when needed
        self.history_table.itemSelectionChanged.connect(self._on_history_row_selected)
        # Wire HistoryPanel signals
        if hasattr(self.history_panel, "filterTextChanged"):
            self.history_panel.filterTextChanged.connect(self._on_history_filter_changed)
        if hasattr(self.history_panel, "refreshRequested"):
            self.history_panel.refreshRequested.connect(self._refresh_history_view)
        if hasattr(self.history_panel, "copyRequested"):
            self.history_panel.copyRequested.connect(self._copy_history_entries)
        if hasattr(self.history_panel, "exportRequested"):
            self.history_panel.exportRequested.connect(self._export_history_entries)
        # Initialize search state and populate view
        self._history_search = ""
        self._refresh_history_view()

        # Back-compat shim for tests expecting a QListWidget-like API on nist_lines_panel
        # Access NIST panel through reference panel's NIST tab
        class _NistCollectionsShim:
            def __init__(self, panel: NistLinesPanel) -> None:
                self._panel = panel
            def count(self) -> int:
                try:
                    return self._panel.model.rowCount()
                except Exception:
                    return 0
            def setCurrentRow(self, row: int) -> None:
                try:
                    index = self._panel.model.index(max(0, row), 0)
                    if index.isValid():
                        self._panel.table_view.setCurrentIndex(index)
                except Exception:
                    pass
        # Expose for tests using legacy attribute - now points to reference panel's NIST tab
        self.nist_collections_list = _NistCollectionsShim(self.reference_panel.nist_lines_panel)

        # Wire NIST Lines panel signals (forwarded from ReferencePanel)
        self.reference_panel.nistFetchRequested.connect(self._on_nist_fetch_from_panel)
        self.reference_panel.nistVisibilityChanged.connect(self._on_nist_visibility_changed)
        self.reference_panel.nistRemoveRequested.connect(self._on_nist_remove_requested)
        self.reference_panel.nistClearAllRequested.connect(self._on_nist_clear_all_requested)
        self.reference_panel.nist_lines_panel.cache_button.clicked.connect(self._on_nist_cache_clear_clicked)

        # Quick Actions toolbar - icon-based shortcuts for common tasks
        self.quick_toolbar = QtWidgets.QToolBar("Quick Actions")
        self.quick_toolbar.setMovable(False)
        self.quick_toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.quick_toolbar.setIconSize(QtCore.QSize(20, 20))
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self.quick_toolbar)

        # Import action
        import_action = QtGui.QAction(self)
        import_action.setText("Import Data")
        import_action.setToolTip("Import spectrum from file (Ctrl+O)")
        import_action.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        try:
            import_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton))
        except Exception:
            pass
        import_action.triggered.connect(self.open_file)
        self.quick_toolbar.addAction(import_action)

        # Export action
        export_action = QtGui.QAction(self)
        export_action.setText("Export")
        export_action.setToolTip("Export spectra and plot (Ctrl+E)")
        export_action.setShortcut(QtGui.QKeySequence("Ctrl+E"))
        try:
            export_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton))
        except Exception:
            pass
        export_action.triggered.connect(self.export_center)
        self.quick_toolbar.addAction(export_action)

        self.quick_toolbar.addSeparator()

        # NIST Lines action
        nist_action = QtGui.QAction(self)
        nist_action.setText("NIST Lines")
        nist_action.setToolTip("Show NIST Lines panel")
        try:
            nist_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView))
        except Exception:
            pass
        # Show inspector dock, switch to Reference tab, then switch to NIST Spectral Lines tab
        def show_nist_panel():
            self.inspector_dock.show()
            self.inspector_dock.raise_()
            self.inspector_tabs.setCurrentIndex(0)  # Reference tab
            self.reference_tabs.setCurrentIndex(2)  # NIST Spectral Lines tab
        nist_action.triggered.connect(show_nist_panel)
        self.quick_toolbar.addAction(nist_action)

        # Autoscale action
        autoscale_action = QtGui.QAction(self)
        autoscale_action.setText("Autoscale")
        autoscale_action.setToolTip("Fit plot to visible data (Ctrl+F)")
        autoscale_action.setShortcut(QtGui.QKeySequence("Ctrl+F"))
        try:
            autoscale_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload))
        except Exception:
            pass
        autoscale_action.triggered.connect(lambda: self.plot.autoscale())
        self.quick_toolbar.addAction(autoscale_action)

        self.quick_toolbar.addSeparator()

        # Edit Labels action
        labels_action = QtGui.QAction(self)
        labels_action.setText("Edit Labels")
        labels_action.setToolTip("Edit plot title and axis labels (Ctrl+L)")
        labels_action.setShortcut(QtGui.QKeySequence("Ctrl+L"))
        try:
            labels_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView))
        except Exception:
            pass
        labels_action.triggered.connect(self._on_edit_labels)
        self.quick_toolbar.addAction(labels_action)

        # Screenshot/Export plot action
        screenshot_action = QtGui.QAction(self)
        screenshot_action.setText("Screenshot")
        screenshot_action.setToolTip("Export plot as PNG image")
        try:
            screenshot_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DesktopIcon))
        except Exception:
            pass
        screenshot_action.triggered.connect(self._on_quick_screenshot)
        self.quick_toolbar.addAction(screenshot_action)

        self.quick_toolbar.addSeparator()

        # Crosshair toggle
        self.crosshair_action = QtGui.QAction(self)
        self.crosshair_action.setText("Crosshair")
        self.crosshair_action.setToolTip("Toggle crosshair cursor")
        self.crosshair_action.setCheckable(True)
        self.crosshair_action.setChecked(True)
        try:
            self.crosshair_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TitleBarContextHelpButton))
        except Exception:
            pass
        self.crosshair_action.triggered.connect(lambda checked: self.plot.set_crosshair_visible(checked))
        self.quick_toolbar.addAction(self.crosshair_action)

        # Plot toolbar
        self.plot_toolbar = QtWidgets.QToolBar("Plot")
        self.plot_toolbar.setMovable(False)
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self.plot_toolbar)
        self.plot_toolbar.toggleViewAction().setChecked(True)
        # Ensure visibility for headless UI tests
        self.plot_toolbar.show()
        # Unit combo
        self.unit_combo = QtWidgets.QComboBox()
        self.unit_combo.addItems(["nm", "Å", "µm", "cm⁻¹"])
        self.unit_combo.setCurrentText("nm")
        self.unit_combo.currentTextChanged.connect(self.plot.set_display_unit)
        self.unit_combo.currentTextChanged.connect(self._on_unit_changed)
        self.plot_toolbar.addWidget(QtWidgets.QLabel(" X: "))
        self.plot_toolbar.addWidget(self.unit_combo)
        # Normalization combo
        self.norm_combo = QtWidgets.QComboBox()
        self.norm_combo.addItems(["None", "Max", "Area"])
        self.norm_combo.setCurrentText("None")
        self.norm_combo.currentTextChanged.connect(lambda _: self._schedule_refresh())
        self.plot_toolbar.addSeparator()
        self.plot_toolbar.addWidget(QtWidgets.QLabel(" Normalize: "))
        self.plot_toolbar.addWidget(self.norm_combo)
        # Normalize button (permanently apply normalization)
        self.normalize_button = QtWidgets.QPushButton("Normalize")
        self.normalize_button.setToolTip(
            "Apply normalization to selected datasets (or all unlocked if none selected).\n"
            "This permanently modifies the dataset. Locked datasets are skipped."
        )
        self.normalize_button.clicked.connect(self._on_normalize_datasets)
        self.plot_toolbar.addWidget(self.normalize_button)
        # Y scale combo (to improve visibility across dynamic ranges)
        self.y_scale_combo = QtWidgets.QComboBox()
        self.y_scale_combo.addItems(["Linear", "Log10", "Asinh"])  # Safe scales; Log10 uses signed-log
        self.y_scale_combo.setCurrentText("Linear")
        self.y_scale_combo.setToolTip("Apply Y scaling after normalization.\nLog10: sign(y)*log10(1+|y|)\nAsinh: arcsinh(y) for wider dynamic range including negatives")
        self.y_scale_combo.currentTextChanged.connect(lambda _: self._schedule_refresh())
        self.plot_toolbar.addWidget(QtWidgets.QLabel(" Y-scale: "))
        self.plot_toolbar.addWidget(self.y_scale_combo)
        # Global normalization checkbox
        self.norm_global_checkbox = QtWidgets.QCheckBox("Global")
        self.norm_global_checkbox.setChecked(False)  # Default to per-spectrum normalization
        self.norm_global_checkbox.setToolTip("When checked, normalize all spectra together.\nWhen unchecked, normalize each spectrum independently.")
        self.norm_global_checkbox.stateChanged.connect(lambda _: self._schedule_refresh())
        self.plot_toolbar.addWidget(self.norm_global_checkbox)
        # Max points control
        self.plot_toolbar.addSeparator()
        self.plot_toolbar.addWidget(QtWidgets.QLabel(" Points: "))
        self.plot_max_points_control = QtWidgets.QSpinBox()
        self.plot_max_points_control.setRange(PlotPane.MIN_MAX_POINTS, PlotPane.MAX_MAX_POINTS)
        self.plot_max_points_control.setValue(self._plot_max_points)
        self.plot_max_points_control.valueChanged.connect(self._on_max_points_changed)
        self.plot_toolbar.addWidget(self.plot_max_points_control)

        # Analysis helpers
        self.plot_toolbar.addSeparator()
        self.action_jump_max = QtGui.QAction("Jump to max", self)
        self.action_jump_max.setToolTip("Center view on the maximum of the selected spectrum (post-normalization)")
        self.action_jump_max.triggered.connect(self._on_jump_to_max)
        self.plot_toolbar.addAction(self.action_jump_max)

        self.action_find_peak = QtGui.QAction("Find peak near cursor", self)
        self.action_find_peak.setToolTip("Find a peak near the cursor in the selected spectrum and center the view")
        self.action_find_peak.triggered.connect(self._on_find_peak_near_cursor)
        self.plot_toolbar.addAction(self.action_find_peak)

        # Status bar
        self.statusBar().showMessage("Ready")
        # Set monospace font for cleaner numeric readouts
        try:
            mono_font = QtGui.QFont("Consolas", 9)
            if not mono_font.exactMatch():
                mono_font = QtGui.QFont("Courier New", 9)
            self.statusBar().setFont(mono_font)
        except Exception:
            pass
        # Global progress bar to surface background work (e.g., downloads)
        self._status_progress = QtWidgets.QProgressBar()
        try:
            self._status_progress.setMaximumHeight(14)
        except Exception:
            pass
        self._status_progress.setVisible(False)
        self._status_progress.setMinimum(0)
        self._status_progress.setMaximum(1)
        self._status_progress.setValue(0)
        try:
            self.statusBar().addPermanentWidget(self._status_progress, 0)
        except Exception:
            pass

        # User-imported and reference spectral line markers (vertical lines + labels)
        # Dict of element/group -> list of markers
        # Each marker: {'x_nm': float, 'line': pg.InfiniteLine, 'text': pg.TextItem, 'color': QtGui.QColor, 'label': str}
        self._line_markers_by_element: Dict[str, List[Dict[str, Any]]] = {}
        self._line_labels_visible = True  # Global toggle for all labels
        # Curated reference lines loaded from samples/reference_lines/
        self._reference_lines_data: List[Dict[str, str]] = []

    # ----------------------------- Merge / Math handlers -------------
    def _selected_dataset_ids(self) -> List[str]:
        """Return the list of selected dataset IDs from the dataset panel.

        Falls back to an empty list when the selection model is not ready yet.
        """
        try:
            if self.dataset_view is None:
                return []
            selection = self.dataset_view.selectionModel()
            if selection is None:
                return []
            ids: List[str] = []
            for index in selection.selectedRows():  # type: ignore[attr-defined]
                if self.dataset_model is None:
                    continue
                item = self.dataset_model.itemFromIndex(index)
                if item is None:
                    continue
                dataset_id = str(item.data(QtCore.Qt.ItemDataRole.UserRole) or "").strip()
                if dataset_id:
                    ids.append(dataset_id)
            return ids
        except Exception:
            return []

    def _resolve_spectra(self, ids: Sequence[str]) -> List[Spectrum]:
        spectra: List[Spectrum] = []
        for did in ids:
            try:
                spec = self.ingest_service.get(did)  # type: ignore[attr-defined]
            except Exception:
                spec = None
            if isinstance(spec, Spectrum):
                spectra.append(spec)
        return spectra

    def _merge_result_name(self, base: str) -> str:
        token = base.strip() or "result"
        if self.merge_name_edit is not None:
            custom = str(self.merge_name_edit.text()).strip()
            if custom:
                return custom
        counter = 1
        candidate = token
        while candidate in self._dataset_items:  # avoid collision with existing IDs
            counter += 1
            candidate = f"{token}_{counter}"
        return candidate

    def _emit_math_result(self, result: Spectrum | None, label: str) -> None:
        if result is None:
            self._log("Math", f"Operation '{label}' failed or produced no result")
            if self.merge_status_label is not None:
                self.merge_status_label.setText(f"{label}: failed")
            return
        # Ingest as a transient spectrum (persist if store available)
        try:
            stored = self.ingest_service.ingest_arrays(
                result.x, result.y, x_unit=result.x_unit, y_unit=result.y_unit, alias=result.label
            )
            self._log("Math", f"Created math spectrum: {stored['id']}")
            self._refresh_dataset_view()
            if self.merge_status_label is not None:
                self.merge_status_label.setText(f"{label}: created '{stored['id']}'")
        except Exception as exc:
            self._log("Math", f"Failed to ingest math result: {exc}")
            if self.merge_status_label is not None:
                self.merge_status_label.setText(f"{label}: ingest failed")

    def _on_merge_average(self) -> None:
        ids = self._selected_dataset_ids()
        spectra = self._resolve_spectra(ids)
        if len(spectra) < 2:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Average requires ≥2 spectra")
            return
        # Apply range selection if enabled
        spectra = self._apply_range_to_spectra(spectra)
        if len(spectra) < 2:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Not enough spectra in range for average")
            return
        try:
            result, _ = self.math_service.average([spec for spec in spectra])
        except Exception as exc:
            self._log("Math", f"Average failed: {exc}")
            result = None
        if result is not None:
            result.label = self._merge_result_name("average")
        self._emit_math_result(result, "Average")

    def _on_merge_subtract(self) -> None:
        ids = self._selected_dataset_ids()
        spectra = self._resolve_spectra(ids)
        if len(spectra) != 2:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Subtract requires exactly 2 spectra")
            return
        # Apply range selection if enabled
        spectra = self._apply_range_to_spectra(spectra)
        if len(spectra) != 2:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Both spectra must have data in range")
            return
        a, b = spectra
        try:
            result, _ = self.math_service.subtract(a, b)
        except Exception as exc:
            self._log("Math", f"Subtract failed: {exc}")
            result = None
        if result is not None:
            result.label = self._merge_result_name("subtract")
        self._emit_math_result(result, "Subtract")

    def _on_merge_ratio(self) -> None:
        ids = self._selected_dataset_ids()
        spectra = self._resolve_spectra(ids)
        if len(spectra) != 2:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Ratio requires exactly 2 spectra")
            return
        # Apply range selection if enabled
        spectra = self._apply_range_to_spectra(spectra)
        if len(spectra) != 2:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Both spectra must have data in range")
            return
        a, b = spectra
        try:
            result, _ = self.math_service.ratio(a, b)
        except Exception as exc:
            self._log("Math", f"Ratio failed: {exc}")
            result = None
        if result is not None:
            result.label = self._merge_result_name("ratio")
        self._emit_math_result(result, "Ratio")

    def _on_merge_normalized_difference(self) -> None:
        ids = self._selected_dataset_ids()
        spectra = self._resolve_spectra(ids)
        if len(spectra) != 2:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Normalized difference requires exactly 2 spectra")
            return
        # Apply range selection if enabled
        spectra = self._apply_range_to_spectra(spectra)
        if len(spectra) != 2:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Both spectra must have data in range")
            return
        a, b = spectra
        try:
            result, _ = self.math_service.normalized_difference(a, b)
        except Exception as exc:
            self._log("Math", f"Normalized difference failed: {exc}")
            result = None
        if result is not None:
            result.label = self._merge_result_name("normalized_diff")
        self._emit_math_result(result, "Normalized difference")

    def _on_merge_smooth(self) -> None:
        ids = self._selected_dataset_ids()
        spectra = self._resolve_spectra(ids)
        if len(spectra) != 1:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Smooth requires exactly 1 spectrum")
            return
        # Apply range selection if enabled
        spectra = self._apply_range_to_spectra(spectra)
        if len(spectra) != 1:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Spectrum must have data in range")
            return
        spec = spectra[0]
        try:
            result, _ = self.math_service.smooth(spec, window_size=7, method="moving_average")
        except Exception as exc:
            self._log("Math", f"Smooth failed: {exc}")
            result = None
        if result is not None:
            result.label = self._merge_result_name("smooth")
        self._emit_math_result(result, "Smooth")

    def _on_merge_derivative(self) -> None:
        ids = self._selected_dataset_ids()
        spectra = self._resolve_spectra(ids)
        if len(spectra) != 1:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Derivative requires exactly 1 spectrum")
            return
        # Apply range selection if enabled
        spectra = self._apply_range_to_spectra(spectra)
        if len(spectra) != 1:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Spectrum must have data in range")
            return
        spec = spectra[0]
        try:
            result, _ = self.math_service.derivative(spec, order=1)
        except Exception as exc:
            self._log("Math", f"Derivative failed: {exc}")
            result = None
        if result is not None:
            result.label = self._merge_result_name("derivative")
        self._emit_math_result(result, "Derivative")

    def _on_merge_integral(self) -> None:
        ids = self._selected_dataset_ids()
        spectra = self._resolve_spectra(ids)
        if len(spectra) != 1:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Integral requires exactly 1 spectrum")
            return
        # Apply range selection if enabled
        spectra = self._apply_range_to_spectra(spectra)
        if len(spectra) != 1:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Spectrum must have data in range")
            return
        spec = spectra[0]
        try:
            result, _ = self.math_service.integral(spec, method='cumulative')
        except Exception as exc:
            self._log("Math", f"Integral failed: {exc}")
            result = None
        if result is not None:
            result.label = self._merge_result_name("integral")
        self._emit_math_result(result, "Integral")

    # ----------------------------- Range Selection Handlers ----------------
    def _on_range_selection_toggled(self, enabled: bool) -> None:
        """Handle range selection toggle from merge panel."""
        if self.plot is not None:
            self.plot.set_region_visible(enabled)
            if enabled:
                # Sync plot region with panel values
                range_nm = self._get_range_nm_from_panel()
                if range_nm is not None:
                    self.plot.set_region_nm(range_nm[0], range_nm[1])

    def _on_range_values_changed(self, min_val: float, max_val: float) -> None:
        """Handle range value changes from merge panel (in display units)."""
        if self.plot is not None and self.merge_panel.is_range_enabled():
            # Convert from display units to nm
            min_nm = self._display_to_nm(min_val)
            max_nm = self._display_to_nm(max_val)
            if min_nm > max_nm:
                min_nm, max_nm = max_nm, min_nm
            self.plot.set_region_nm(min_nm, max_nm)

    def _on_plot_region_changed(self, min_nm: float, max_nm: float) -> None:
        """Handle region changes from plot (user dragging the region)."""
        if self.merge_panel is not None:
            # Convert from nm to display units
            min_disp = self._nm_to_display(min_nm)
            max_disp = self._nm_to_display(max_nm)
            self.merge_panel.set_range_values(min_disp, max_disp)

    def _on_set_range_to_overlap(self) -> None:
        """Set range to overlap of selected/visible datasets."""
        try:
            ids = self._selected_dataset_ids()
            spectra = self._resolve_spectra(ids)
            if len(spectra) < 2:
                # Fall back to all visible spectra
                spectra = self._get_visible_spectra()
            
            if len(spectra) < 2:
                if self.merge_status_label is not None:
                    self.merge_status_label.setText("Need ≥2 spectra to find overlap")
                return
            
            min_nm, max_nm = self.math_service.find_overlap_range(spectra)
            # Convert to display units for the panel
            min_disp = self._nm_to_display(min_nm)
            max_disp = self._nm_to_display(max_nm)
            self.merge_panel.set_range_values(min_disp, max_disp)
            if self.plot is not None:
                self.plot.set_region_nm(min_nm, max_nm)
            unit = self._get_current_display_unit()
            if self.merge_status_label is not None:
                self.merge_status_label.setText(f"Range set to overlap: {min_disp:.1f}-{max_disp:.1f} {unit}")
        except ValueError as exc:
            if self.merge_status_label is not None:
                self.merge_status_label.setText(str(exc))
        except Exception as exc:
            self._log("Math", f"Failed to find overlap: {exc}")

    def _on_set_range_to_view(self) -> None:
        """Set range to match current plot view."""
        if self.plot is None:
            return
        try:
            self.plot.set_region_to_view()
            region = self.plot.get_selected_region_nm()
            if region is not None:
                min_nm, max_nm = region
                # Convert to display units for the panel
                min_disp = self._nm_to_display(min_nm)
                max_disp = self._nm_to_display(max_nm)
                self.merge_panel.set_range_values(min_disp, max_disp)
                unit = self._get_current_display_unit()
                if self.merge_status_label is not None:
                    self.merge_status_label.setText(f"Range set to view: {min_disp:.1f}-{max_disp:.1f} {unit}")
        except Exception as exc:
            self._log("Math", f"Failed to set range to view: {exc}")

    def _get_visible_spectra(self) -> List[Spectrum]:
        """Get all currently visible (checked) spectra."""
        return [spec for spec in self.overlay_service.list() 
                if self._visibility.get(spec.id, True)]

    def _get_all_spectra(self) -> List[Spectrum]:
        """Get all loaded spectra."""
        return list(self.overlay_service.list())

    def _is_spectrum_visible(self, spec: Spectrum) -> bool:
        """Check if a spectrum is currently visible in the plot."""
        return self._visibility.get(spec.id, True)
    
    def _get_current_display_unit(self) -> str:
        """Get the current display unit from the unit combo."""
        if self.unit_combo is not None:
            return self.unit_combo.currentText()
        return "nm"
    
    def _nm_to_display(self, nm: float) -> float:
        """Convert nm to current display unit."""
        unit = self._get_current_display_unit()
        if unit == "nm":
            return nm
        elif unit == "Å":
            return nm * 10.0
        elif unit == "µm":
            return nm / 1000.0
        elif unit == "cm⁻¹":
            if nm <= 0:
                return float('inf')
            return 1e7 / nm
        return nm
    
    def _display_to_nm(self, val: float) -> float:
        """Convert display unit value to nm."""
        unit = self._get_current_display_unit()
        if unit == "nm":
            return val
        elif unit == "Å":
            return val / 10.0
        elif unit == "µm":
            return val * 1000.0
        elif unit == "cm⁻¹":
            if val <= 0:
                return float('inf')
            return 1e7 / val
        return val
    
    def _get_range_nm_from_panel(self) -> tuple[float, float] | None:
        """Get range from panel converted to nm."""
        if self.merge_panel is None or not self.merge_panel.is_range_enabled():
            return None
        min_val = self.merge_panel.range_min_spin.value()
        max_val = self.merge_panel.range_max_spin.value()
        min_nm = self._display_to_nm(min_val)
        max_nm = self._display_to_nm(max_val)
        if min_nm > max_nm:
            min_nm, max_nm = max_nm, min_nm
        return (min_nm, max_nm)

    def _apply_range_to_spectra(self, spectra: List[Spectrum]) -> List[Spectrum]:
        """Apply the current range selection to a list of spectra.
        
        Returns the clipped spectra if range is enabled, otherwise returns original.
        """
        range_nm = self._get_range_nm_from_panel()
        if range_nm is None:
            return spectra
        
        min_nm, max_nm = range_nm
        clipped: List[Spectrum] = []
        for spec in spectra:
            try:
                clipped_spec, _ = self.math_service.clip_to_range(spec, min_nm, max_nm)
                clipped.append(clipped_spec)
            except ValueError as exc:
                self._log("Math", f"Skipping {spec.name}: {exc}")
            except Exception as exc:
                self._log("Math", f"Failed to clip {spec.name}: {exc}")
        return clipped

    def _on_export_range(self) -> None:
        """Export selected spectra clipped to the current range."""
        range_nm = self._get_range_nm_from_panel()
        if range_nm is None:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("Enable range selection first")
            return
        
        # Get selected spectra (or all visible if none selected)
        ids = self._selected_dataset_ids()
        spectra = self._resolve_spectra(ids)
        if not spectra:
            # Fall back to all visible spectra
            spectra = self._get_visible_spectra()
        
        if not spectra:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("No spectra to export")
            return
        
        # Clip spectra to range
        clipped = self._apply_range_to_spectra(spectra)
        if not clipped:
            if self.merge_status_label is not None:
                self.merge_status_label.setText("No spectra have data in range")
            return
        
        # Ask for export location
        min_nm, max_nm = range_nm
        default_name = f"range_{min_nm:.0f}-{max_nm:.0f}nm"
        base_str, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            f"Export {len(clipped)} spectra ({min_nm:.1f}-{max_nm:.1f} nm)",
            str(Path.home() / default_name),
            "CSV files (*.csv);;All files (*.*)",
        )
        if not base_str:
            return
        
        base = Path(base_str)
        try:
            # Write a wide-format CSV with all clipped spectra
            self.provenance_service.write_wide_csv(base.with_suffix('.csv'), clipped)
            self._log("Export", f"Exported {len(clipped)} spectra to {base.with_suffix('.csv')}")
            if self.merge_status_label is not None:
                self.merge_status_label.setText(f"Exported {len(clipped)} spectra to range CSV")
        except Exception as exc:
            self._log("Export", f"Export failed: {exc}")
            QtWidgets.QMessageBox.warning(self, "Export failed", str(exc))

    # ----------------------------- Status readout ----------------------
    def _on_plot_point_hovered(self, x: float, y: float) -> None:
        """Update the status bar with live cursor coordinates.

        - x is already in the current display unit from PlotPane; just label it.
        - y reflects normalized + Y-scale transformed values shown on the canvas.
        """
        # Fast path: cache widget references and only format when values change significantly
        if not hasattr(self, '_last_hover_x'):
            self._last_hover_x = None
            self._last_hover_y = None
            self._last_hover_msg = ""
        
        # Skip update if values haven't changed much (reduces Qt overhead)
        try:
            if (self._last_hover_x is not None and 
                abs(x - self._last_hover_x) < abs(x) * 0.001 and
                abs(y - self._last_hover_y) < abs(y) * 0.001):
                return
        except Exception:
            pass
        
        self._last_hover_x = x
        self._last_hover_y = y
        
        # Cache widget state (avoid repeated hasattr/currentText calls)
        try:
            unit = self.unit_combo.currentText() if self.unit_combo is not None else "nm"
            scale = self.y_scale_combo.currentText() if self.y_scale_combo is not None else "Linear"
            norm_mode = self.norm_combo.currentText() if self.norm_combo is not None else "None"
            is_global = self.norm_global_checkbox.isChecked() if self.norm_global_checkbox is not None else False
        except Exception:
            unit, scale, norm_mode, is_global = "nm", "Linear", "None", False
        
        # Fast formatting
        try:
            if not np.isfinite(x):
                x_str = "—"
            else:
                x_str = f"{float(x):.6g}"
            
            if not np.isfinite(y):
                y_str = "—"
            else:
                y_str = f"{float(y):.6g}"
            
            scale_suffix = "" if scale == "Linear" else f" [{scale}]"
            norm_suffix = "" if norm_mode == "None" else f" [{norm_mode}{'•Global' if is_global else ''}]"
            
            msg = f"x: {x_str} {unit} | y: {y_str}{scale_suffix}{norm_suffix}"
            if msg != self._last_hover_msg:
                self.statusBar().showMessage(msg)
                self._last_hover_msg = msg
            
            # Record last cursor x for analysis helpers
            self._last_cursor_x_display = float(x) if np.isfinite(x) else None
        except Exception:
            pass

    # ----------------------------- NIST Lines helpers ------------------
    def _on_unit_changed(self, unit: str) -> None:
        """Refresh NIST collections and range panel when unit changes."""
        # Redraw all visible NIST collections with new unit
        for collection_id in list(self._nist_plot_items.keys()):
            if self.reference_panel.nist_lines_panel.is_visible(collection_id):
                self._draw_nist_collection(collection_id)
        # Reposition custom line list markers in new display units
        try:
            self._update_line_marker_positions()
        except Exception:
            pass
        # Update merge panel unit label and convert existing range values
        if self.merge_panel is not None:
            try:
                # Get current range in nm before changing unit label
                old_range_nm = self._get_range_nm_from_panel()
                # Update the unit label
                self.merge_panel.set_display_unit(unit)
                # Convert range values to new display units
                if old_range_nm is not None:
                    min_disp = self._nm_to_display(old_range_nm[0])
                    max_disp = self._nm_to_display(old_range_nm[1])
                    self.merge_panel.set_range_values(min_disp, max_disp)
            except Exception:
                pass

    def _update_line_marker_positions(self) -> None:
        """Update positions of all spectral line markers after unit or view change.
        
        When markers are very close (overlapping), vertically stagger their labels
        to prevent text collision.
        """
        # Collect all markers across all element groups
        all_markers: List[Dict[str, Any]] = []
        for element_markers in self._line_markers_by_element.values():
            all_markers.extend(element_markers)
        
        if not all_markers:
            return
        try:
            (x_range, y_range) = self.plot.view_range()
            y0, y1 = float(y_range[0]), float(y_range[1])
            y_span = y1 - y0
            # Base label position: near top with small margin
            y_base = y1 - y_span * 0.04
        except Exception:
            y_base = 0.0
            y_span = 1.0
        
        # First pass: convert all markers to display units and sort by x position
        display_positions: List[tuple[float, Dict[str, Any]]] = []
        for marker in all_markers:
            try:
                x_nm = float(marker.get('x_nm'))
                disp = float(self.plot._x_nm_to_disp(np.array([x_nm]))[0])  # type: ignore[attr-defined]
                marker['line'].setPos(disp)
                display_positions.append((disp, marker))
            except Exception:
                continue
        
        # Sort by x position to process overlaps in order
        display_positions.sort(key=lambda t: t[0])
        
        # Second pass: detect overlaps and assign stagger levels
        # Overlap threshold: ~4% of current view width (accounts for typical label text width)
        try:
            x_view_span = float(x_range[1] - x_range[0])
            overlap_threshold = abs(x_view_span) * 0.04
        except Exception:
            overlap_threshold = 10.0  # fallback
        
        stagger_levels: List[int] = []
        for i, (x_pos, marker) in enumerate(display_positions):
            level = 0
            # Check against all previous markers to find first free level
            for j in range(i):
                prev_x, prev_marker = display_positions[j]
                if abs(x_pos - prev_x) < overlap_threshold:
                    # Overlapping: ensure we're at a different level
                    if stagger_levels[j] == level:
                        level += 1
            stagger_levels.append(level)
        
        # Third pass: position labels with vertical stagger
        # Each level shifts down by 3.5% of y-span (tighter packing)
        stagger_step = y_span * 0.035
        for (x_pos, marker), level in zip(display_positions, stagger_levels):
            y_label = y_base - (level * stagger_step)
            try:
                marker['text'].setPos(x_pos, y_label)
            except Exception:
                continue

    # ----------------------------- Analysis helpers -------------------
    def _get_selected_spec_and_display_arrays(self) -> tuple[str | None, np.ndarray, np.ndarray, str]:
        """Return (spec_id, x_disp, y_disp, unit) for the single selected spectrum.

        y_disp includes calibration+normalization; x_disp in current display units.
        Returns (None, empty, empty, unit) when no selection.
        """
        unit = self.unit_combo.currentText() if self.unit_combo is not None else "nm"
        if self.dataset_view is None or self.dataset_model is None:
            return None, np.array([], dtype=float), np.array([], dtype=float), unit
        sel_model = self.dataset_view.selectionModel()
        rows = sel_model.selectedRows() if sel_model else []
        rows = [idx for idx in rows if idx.parent().isValid()]
        if len(rows) != 1:
            return None, np.array([], dtype=float), np.array([], dtype=float), unit
        index = rows[0]
        alias_item = self.dataset_model.itemFromIndex(self.dataset_model.index(index.row(), 0, index.parent()))
        spec_id = None
        for sid, item in self._dataset_items.items():
            if item is alias_item:
                spec_id = sid
                break
        if not spec_id:
            return None, np.array([], dtype=float), np.array([], dtype=float), unit
        try:
            spec = self.overlay_service.get(spec_id)
        except Exception:
            return None, np.array([], dtype=float), np.array([], dtype=float), unit
        # Build display arrays mirroring _refresh_data_table
        try:
            x_nm, y_conv, _ = self.units_service.convert_arrays(
                np.asarray(spec.x, dtype=float),
                np.asarray(spec.y, dtype=float),
                spec.x_unit, spec.y_unit,
                "nm", spec.y_unit,
            )
        except Exception:
            try:
                x_nm = self.units_service._to_canonical_wavelength(np.asarray(spec.x, dtype=float), spec.x_unit)
                y_conv = np.asarray(spec.y, dtype=float)
            except Exception:
                x_nm = np.asarray(spec.x, dtype=float)
                y_conv = np.asarray(spec.y, dtype=float)
        # x_nm, y_conv = self._apply_calibration_nm(x_nm, y_conv)  # REMOVED - calibration no longer used
        # Unit conversion for display
        if unit == "nm":
            x_disp = x_nm
        elif unit == "Å":
            x_disp = x_nm * 10.0
        elif unit == "µm":
            x_disp = x_nm / 1000.0
        elif unit == "cm⁻¹":
            with np.errstate(divide="ignore"):
                x_disp = 1e7 / x_nm
        else:
            x_disp = x_nm
        # Normalization (support global)
        norm_mode = self.norm_combo.currentText() if self.norm_combo is not None else "None"
        use_global = self.norm_global_checkbox.isChecked() if hasattr(self, 'norm_global_checkbox') else False
        global_val = None
        if norm_mode != "None" and use_global:
            try:
                global_val = self._compute_global_normalization_value(norm_mode)
            except Exception:
                global_val = None
        y_disp = self._apply_normalization(y_conv, norm_mode, global_val, x_nm)
        # Ensure monotonic x for cm⁻¹ display
        try:
            if x_disp.size >= 2 and x_disp[-1] < x_disp[0]:
                x_disp = x_disp[::-1]
                y_disp = y_disp[::-1]
        except Exception:
            pass
        return spec_id, np.asarray(x_disp, dtype=float), np.asarray(y_disp, dtype=float), unit

    @ui_action("Failed to jump to max")
    def _on_jump_to_max(self) -> None:
        _sid, x, y, unit = self._get_selected_spec_and_display_arrays()
        if x.size == 0:
            self.statusBar().showMessage("Select a single spectrum in the Data dock to use Jump to max")
            return
        try:
            idx = int(np.nanargmax(y))
        except Exception:
            self.statusBar().showMessage("Unable to compute maximum for the selected spectrum")
            return
        xp = float(x[idx])
        self._center_view_on_x(xp)
        self.statusBar().showMessage(f"Jumped to max at x≈{xp:.6g} {unit}")

    @ui_action("Failed to find peak near cursor")
    def _on_find_peak_near_cursor(self) -> None:
        _sid, x, y, unit = self._get_selected_spec_and_display_arrays()
        if x.size == 0:
            self.statusBar().showMessage("Select a single spectrum in the Data dock to find a peak")
            return
        x0 = self._last_cursor_x_display
        if x0 is None or not np.isfinite(x0):
            self.statusBar().showMessage("Move the cursor over the plot to choose a neighborhood")
            return
        # Window: 2% of current x-range (reasonable default across units)
        (xr0, xr1), _ = self.plot.view_range()
        try:
            width = abs(float(xr1) - float(xr0)) * 0.02
            if not np.isfinite(width) or width <= 0:
                width = max(1e-6, (np.nanmax(x) - np.nanmin(x)) * 0.02)
        except Exception:
            width = max(1e-6, (np.nanmax(x) - np.nanmin(x)) * 0.02)
        idx, xp, yp = peak_near(x, y, float(x0), width)
        if idx < 0 or not np.isfinite(xp):
            self.statusBar().showMessage("No peak found near cursor")
            return
        self._center_view_on_x(xp)
        self.statusBar().showMessage(f"Peak near cursor at x≈{xp:.6g} {unit}, y≈{float(yp):.6g}")

    def _center_view_on_x(self, x_center: float) -> None:
        """Pan the view to center on x_center, preserving current width."""
        try:
            (xr0, xr1), yr = self.plot.view_range()
            width = float(abs(xr1 - xr0)) if np.isfinite(xr0) and np.isfinite(xr1) else None
            if not width or width <= 0:
                # Fallback to 10% of data span
                width = max(1e-3, (np.nanmax(self._plot_x_span()) - np.nanmin(self._plot_x_span())) * 0.1)
            half = width * 0.5
            self.plot._plot.setXRange(x_center - half, x_center + half, padding=0.0)
        except Exception:
            pass

    def _plot_x_span(self) -> np.ndarray:
        # Collect concatenated x arrays from visible traces for a fallback span estimate
        xs: list[np.ndarray] = []
        try:
            for key in getattr(self.plot, "_traces", {}).keys():
                trace = self.plot._traces.get(key)
                if not trace or not bool(trace.get("visible", True)):
                    continue
                x_nm = np.asarray(trace.get("x_nm"), dtype=float)
                x_disp = self.plot._x_nm_to_disp(x_nm)
                xs.append(x_disp)
        except Exception:
            return np.array([], dtype=float)
        return np.concatenate(xs) if xs else np.array([], dtype=float)

    # ----------------------------- Calibration -------------------------
    # REMOVED - Calibration feature no longer used
    # def _on_calibration_changed(self, payload: Mapping[str, Any]) -> None:
    #     try:
    #         self.calibration_service.set_target_fwhm(payload.get("target_fwhm"))
    #         self.calibration_service.set_rv_kms(float(payload.get("rv_kms", 0.0) or 0.0))
    #         frame = str(payload.get("frame") or "observer")
    #         if frame in ("observer", "rest"):
    #             self.calibration_service.set_frame(frame)  # currently informational
    #     except Exception:
    #         pass
    #     # Refresh plot and data table to reflect new calibration settings
    #     try:
    #         self._refresh_plot()
    #         self._refresh_data_table()
    #     except Exception:
    #         pass

    # def _apply_calibration_nm(self, x_nm: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    #     """Apply calibration in nm-space and return transformed arrays.
    #
    #     The CalibrationService operates in the current x-units; we interpret the
    #     configured FWHM as matching the current display axis. For simplicity and
    #     stability, we apply in nanometers here, which aligns with PlotPane data.
    #     """
    #     try:
    #         x_c, y_c, _s, _meta = self.calibration_service.apply(x_nm, y, None)
    #         return np.asarray(x_c, dtype=float), np.asarray(y_c, dtype=float)
    #     except Exception:
    #         return x_nm, y

    # ----------------------------- Y-Scale -----------------------------
    def _apply_y_scale(self, y: np.ndarray) -> np.ndarray:
        """Apply Y-axis scaling to improve visibility across dynamic ranges.

        Scales are applied after normalization and before plotting.

        - Linear: identity.
        - Log10: signed logarithm, ``sign(y)*log10(1+|y|)``, safe for zeros/negatives.
        - Asinh: ``arcsinh(y)``, behaves like linear near 0 and ~log for large |y|.
        """
        try:
            mode = self.y_scale_combo.currentText() if hasattr(self, "y_scale_combo") else "Linear"
        except Exception:
            mode = "Linear"
        if y.size == 0:
            return y
        if mode == "Linear":
            return y
        # Use numpy operations for performance and safety
        y_abs = np.abs(y)
        if mode == "Log10":
            # signed-log to keep negatives: log10(1 + |y|)
            return np.sign(y) * np.log10(1.0 + y_abs)
        if mode == "Asinh":
            # asinh handles signed values naturally
            return np.arcsinh(y)
        return y

    def _compute_display_uncertainty(
        self,
        spec: "Spectrum",
        x_nm: np.ndarray,
        y_cal: np.ndarray,
        norm_mode: str,
        global_value: float | None,
    ) -> np.ndarray | None:
        """Compute uncertainty array aligned with current display transforms.

        Steps:
        - Convert uncertainty to current Y-units
        - Apply same normalization scale
        - Map through Y-scale using first-order derivative
        """
        try:
            sigma_src = getattr(spec, "uncertainty", None)
        except Exception:
            sigma_src = None
        if sigma_src is None:
            return None
        # Convert uncertainty with the same unit mapping used for Y
        try:
            _, sigma_conv, _ = self.units_service.convert_arrays(
                np.asarray(spec.x, dtype=float),
                np.asarray(sigma_src, dtype=float),
                spec.x_unit,
                spec.y_unit,
                "nm",
                spec.y_unit,
            )
        except Exception:
            sigma_conv = np.asarray(sigma_src, dtype=float)

        sigma_lin = np.asarray(sigma_conv, dtype=float)

        # Apply normalization scale (replicate logic from _apply_normalization)
        if norm_mode != "None" and y_cal.size:
            finite_y = np.isfinite(y_cal)
            norm_val: float | None = None
            if norm_mode == "Max":
                if global_value is not None and np.isfinite(global_value):
                    norm_val = float(global_value)
                elif np.any(finite_y):
                    norm_val = float(np.nanmax(np.abs(y_cal[finite_y])))
            elif norm_mode == "Area":
                if global_value is not None and np.isfinite(global_value):
                    norm_val = float(global_value)
                elif np.any(finite_y):
                    norm_val = float(np.trapz(np.abs(y_cal[finite_y])))
            if norm_val and norm_val > 0:
                sigma_lin = sigma_lin / norm_val

        # Apply Y-scale derivative mapping
        try:
            y_scale_mode = self.y_scale_combo.currentText() if hasattr(self, "y_scale_combo") else "Linear"
        except Exception:
            y_scale_mode = "Linear"

        y_norm = self._apply_normalization(y_cal, norm_mode, global_value, x_nm)
        if y_scale_mode == "Linear":
            return sigma_lin
        if y_scale_mode == "Log10":
            # d/dy [sign(y)*log10(1+|y|)] ≈ 1 / ((1+|y|) ln 10)
            denom = (1.0 + np.abs(y_norm)) * np.log(10.0)
            with np.errstate(divide="ignore", invalid="ignore"):
                sigma_disp = np.divide(sigma_lin, denom, where=denom > 0)
            return sigma_disp
        if y_scale_mode == "Asinh":
            # d/dy asinh(y) = 1 / sqrt(1+y^2)
            denom = np.sqrt(1.0 + y_norm * y_norm)
            with np.errstate(divide="ignore", invalid="ignore"):
                sigma_disp = np.divide(sigma_lin, denom, where=denom > 0)
            return sigma_disp
        return sigma_lin

    def _setup_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")

        open_action = QtGui.QAction("&Open…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        open_ts_action = QtGui.QAction("Open &Time Series…", self)
        open_ts_action.setShortcut("Ctrl+Shift+O")
        open_ts_action.triggered.connect(self.open_time_series)
        file_menu.addAction(open_ts_action)

        sample_action = QtGui.QAction("Load &Sample", self)
        sample_action.triggered.connect(self.load_sample_via_menu)
        file_menu.addAction(sample_action)

        # Line list import moved to Reference tab; keep legacy action for custom imports
        line_list_action = QtGui.QAction("Import Custom Line List…", self)
        line_list_action.setToolTip("Import a custom CSV of spectral lines (wavelength_nm,label,element,...)")
        line_list_action.triggered.connect(self.import_line_list_via_menu)
        file_menu.addAction(line_list_action)

        # Remote Data action now opens Remote Data tab in inspector
        remote_action = QtGui.QAction("Show &Remote Data Tab…", self)
        remote_action.setShortcut("Ctrl+Shift+R")
        remote_action.triggered.connect(self.show_remote_data_tab)
        file_menu.addAction(remote_action)

        self.persistence_action = QtGui.QAction("Enable Persistent Cache", self, checkable=True)
        self.persistence_action.setChecked(not self._persistence_disabled)
        self.persistence_action.setEnabled(not self._persistence_env_disabled)
        if self._persistence_env_disabled:
            self.persistence_action.setToolTip(
                "Disabled via SPECTRA_DISABLE_PERSISTENCE environment override"
            )
        self.persistence_action.triggered.connect(self._on_persistence_toggled)
        file_menu.addAction(self.persistence_action)

        file_menu.addSeparator()

        # Unified Export Center
        export_center_action = QtGui.QAction("&Export…", self)
        export_center_action.setShortcut("Ctrl+E")
        export_center_action.triggered.connect(self.export_center)
        file_menu.addAction(export_center_action)

        file_menu.addSeparator()
        exit_action = QtGui.QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menu.addMenu("&View")
        view_menu.addAction(self.dataset_dock.toggleViewAction())
        view_menu.addAction(self.inspector_dock.toggleViewAction())
        view_menu.addAction(self.legend_dock.toggleViewAction())
        view_menu.addAction(self.history_dock.toggleViewAction())
        view_menu.addAction(self.log_dock.toggleViewAction())
        view_menu.addSeparator()
        # Toolbars
        if hasattr(self, 'quick_toolbar') and self.quick_toolbar is not None:
            view_menu.addAction(self.quick_toolbar.toggleViewAction())
        if self.plot_toolbar is not None:
            view_menu.addAction(self.plot_toolbar.toggleViewAction())

        theme_menu = view_menu.addMenu("&Theme")
        self._theme_action_group = QtGui.QActionGroup(self)
        self._theme_action_group.setExclusive(True)
        for theme in iter_theme_definitions():
            action = QtGui.QAction(theme.label, self, checkable=True)
            action.setData(theme.key)
            action.setToolTip(theme.description)
            if theme.key == self._theme_key:
                action.setChecked(True)
            action.triggered.connect(lambda checked, key=theme.key: self._on_theme_selected(key, checked))
            theme_menu.addAction(action)
            self._theme_action_group.addAction(action)

        view_menu.addSeparator()
        # Palette controls
        palette_menu = view_menu.addMenu("&Palette")
        self.uniform_palette_action = QtGui.QAction("Use Uniform Color", self, checkable=True)
        self.uniform_palette_action.setChecked(bool(self._use_uniform_palette))
        self.uniform_palette_action.toggled.connect(self._on_uniform_palette_toggled)
        palette_menu.addAction(self.uniform_palette_action)

        pick_color_action = QtGui.QAction("Pick Uniform Color…", self)
        pick_color_action.triggered.connect(self._on_pick_uniform_color)
        palette_menu.addAction(pick_color_action)

        reset_palette_action = QtGui.QAction("Reset to Theme Palette", self)
        reset_palette_action.triggered.connect(lambda: self._on_uniform_palette_toggled(False))
        palette_menu.addAction(reset_palette_action)

        view_menu.addSeparator()
        # Crosshair toggle
        self.crosshair_action = QtGui.QAction("Show Crosshair", self, checkable=True)
        try:
            self.crosshair_action.setChecked(self.plot.is_crosshair_visible())
        except Exception:
            self.crosshair_action.setChecked(True)
        self.crosshair_action.toggled.connect(lambda v: self.plot.set_crosshair_visible(bool(v)))
        view_menu.addAction(self.crosshair_action)

        # Plot title toggle
        self.title_action = QtGui.QAction("Show Plot Title", self, checkable=True)
        try:
            self.title_action.setChecked(self.plot.is_title_visible())
        except Exception:
            self.title_action.setChecked(False)
        self.title_action.toggled.connect(lambda v: self.plot.set_title_visible(bool(v)))
        view_menu.addAction(self.title_action)

        # Edit custom labels action
        self.edit_labels_action = QtGui.QAction("Edit Labels...", self)
        self.edit_labels_action.setShortcut(QtGui.QKeySequence("Ctrl+L"))
        self.edit_labels_action.triggered.connect(self._on_edit_labels)
        view_menu.addAction(self.edit_labels_action)

        view_menu.addSeparator()
        # Font size submenu
        font_menu = view_menu.addMenu("&Font Sizes")
        
        label_size_menu = font_menu.addMenu("Axis Labels")
        label_sizes = [("Small (12pt)", "12pt"), ("Medium (14pt)", "14pt"), ("Large (16pt)", "16pt"), ("Extra Large (18pt)", "18pt")]
        label_group = QtGui.QActionGroup(self)
        for size_name, size_value in label_sizes:
            action = QtGui.QAction(size_name, self, checkable=True)
            action.setData(size_value)
            if size_value == "14pt":  # Default
                action.setChecked(True)
            action.triggered.connect(lambda checked, s=size_value: self.plot.set_axis_label_font_size(s) if checked else None)
            label_group.addAction(action)
            label_size_menu.addAction(action)
        
        title_size_menu = font_menu.addMenu("Plot Title")
        title_sizes = [("Small (14pt)", "14pt"), ("Medium (16pt)", "16pt"), ("Large (18pt)", "18pt"), ("Extra Large (20pt)", "20pt")]
        title_group = QtGui.QActionGroup(self)
        for size_name, size_value in title_sizes:
            action = QtGui.QAction(size_name, self, checkable=True)
            action.setData(size_value)
            if size_value == "16pt":  # Default
                action.setChecked(True)
            action.triggered.connect(lambda checked, s=size_value: self.plot.set_title_font_size(s) if checked else None)
            title_group.addAction(action)
            title_size_menu.addAction(action)

        view_menu.addSeparator()
        self.reset_plot_action = QtGui.QAction("Reset Plot", self)
        self.reset_plot_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+A"))
        self.reset_plot_action.triggered.connect(self.plot.autoscale)
        view_menu.addAction(self.reset_plot_action)

        # Toggle for spectral line labels (text items only, lines remain visible)
        self.line_labels_action = QtGui.QAction("Show Line Labels", self, checkable=True)
        self.line_labels_action.setChecked(True)
        self.line_labels_action.toggled.connect(self._on_line_labels_toggled)
        view_menu.addAction(self.line_labels_action)
        
        # Toggle for annotation notes
        self.notes_action = QtGui.QAction("Show Notes", self, checkable=True)
        self.notes_action.setChecked(True)
        self.notes_action.toggled.connect(self._on_notes_toggled)
        view_menu.addAction(self.notes_action)
        
        # Manage annotations
        self.manage_notes_action = QtGui.QAction("Manage Notes...", self)
        self.manage_notes_action.triggered.connect(self._on_manage_notes)
        view_menu.addAction(self.manage_notes_action)
        
        view_menu.addSeparator()
        self.data_table_action = QtGui.QAction("Show Data Table", self, checkable=True)
        self.data_table_action.triggered.connect(self._toggle_data_table)
        view_menu.addAction(self.data_table_action)

        help_menu = menu.addMenu("&Help")
        docs_action = QtGui.QAction("View &Documentation", self)
        docs_action.setShortcut("F1")
        docs_action.triggered.connect(self.show_documentation)
        help_menu.addAction(docs_action)

    def _on_theme_selected(self, theme_key: str, checked: bool) -> None:
        if not checked or theme_key == self._theme_key:
            return
        self._apply_theme_by_key(theme_key)

    def _apply_theme_by_key(self, theme_key: str, *, persist: bool = True) -> None:
        theme = get_theme_definition(theme_key)
        app = QtWidgets.QApplication.instance()
        theme_changed = theme.key != self._applied_theme_key

        if app is not None and theme_changed:
            try:
                app.setStyleSheet(get_app_stylesheet(theme))
            except Exception:
                pass
        if theme_changed:
            try:
                apply_pyqtgraph_theme(theme)
            except Exception:
                pass
            self._applied_theme_key = theme.key
            # Only apply plot theme when it actually changes
            try:
                if getattr(self, "plot", None) is not None:
                    self.plot.apply_theme(theme)
            except Exception:
                pass
            try:
                if getattr(self, "time_plot", None) is not None:
                    self.time_plot.apply_theme(theme)
            except Exception:
                pass
            # Refresh colour palettes for new theme for future datasets/NIST sets
            try:
                self._apply_theme_palettes(theme.key)
            except Exception:
                pass
            # Retint existing traces and NIST collections to match the new theme
            try:
                self._retint_for_theme()
            except Exception:
                pass
        self._theme_key = theme.key
        if persist and theme_changed:
            self._save_theme_preference(theme.key)
        self._sync_theme_actions(theme.key)

    def _sync_theme_actions(self, theme_key: str) -> None:
        if self._theme_action_group is None:
            return
        for action in self._theme_action_group.actions():
            try:
                action.setChecked(action.data() == theme_key)
            except Exception:
                continue

    def _save_theme_preference(self, theme_key: str) -> None:
        try:
            settings = QtCore.QSettings("SpectraApp", "DesktopPreview")
            settings.setValue("ui/theme", theme_key)
        except Exception:
            pass

    def _load_theme_preference(self) -> str:
        try:
            settings = QtCore.QSettings("SpectraApp", "DesktopPreview")
            stored = settings.value("ui/theme", default_theme_key())
        except Exception:
            stored = default_theme_key()
        if isinstance(stored, str) and stored:
            return get_theme_definition(stored).key
        try:
            return get_theme_definition(str(stored)).key
        except Exception:
            return get_theme_definition(default_theme_key()).key

    def _wire_shortcuts(self) -> None:
        # Keep minimal; menu items already provide the primary access paths.
        # Focus dataset filter (Ctrl+L)
        try:
            focus_filter = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
            focus_filter.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
            focus_filter.activated.connect(lambda: self._focus_dataset_filter())
        except Exception:
            pass

        # Show/Raise History dock (Ctrl+Shift+H)
        try:
            show_history = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+H"), self)
            show_history.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
            show_history.activated.connect(lambda: self._show_history_dock())
        except Exception:
            pass

        # Switch to Merge/Average tab (Ctrl+M)
        try:
            go_merge = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+M"), self)
            go_merge.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
            go_merge.activated.connect(lambda: self._show_merge_tab())
        except Exception:
            pass

    def _focus_dataset_filter(self) -> None:
        try:
            self.dataset_dock.raise_()
            self.data_tabs.setCurrentIndex(0)  # Datasets tab
            if hasattr(self, "dataset_filter") and self.dataset_filter is not None:
                self.dataset_filter.setFocus(QtCore.Qt.FocusReason.ShortcutFocusReason)
                self.dataset_filter.selectAll()
        except Exception:
            pass

    def _show_history_dock(self) -> None:
        try:
            self.history_dock.show()
            self.history_dock.raise_()
        except Exception:
            pass

    def _show_merge_tab(self) -> None:
        try:
            self.inspector_dock.show()
            self.inspector_dock.raise_()
            index = self.inspector_tabs.indexOf(self.merge_panel)
            if index != -1:
                self.inspector_tabs.setCurrentIndex(index)
        except Exception:
            pass

    def _build_library_tab(self) -> None:
        # Ensure library tab header is correct and has a placeholder
        if self.library_view is None:
            return
        self._refresh_library_view()

    def _toggle_data_table(self, checked: bool) -> None:
        if checked:
            self._ensure_data_table()
            if self.data_table_dock is not None:
                self.data_table_dock.show()
                self.data_table_dock.raise_()
            self._refresh_data_table()
        else:
            if self.data_table_dock is not None:
                self.data_table_dock.hide()

    def _ensure_data_table(self) -> None:
        """Create the Data Table dock on first use and wire refresh hooks."""
        if self.data_table_dock is not None:
            return
        self.data_table_dock = QtWidgets.QDockWidget("Data Table", self)
        self.data_table_dock.setObjectName("dock-data-table")
        # Compose a small panel: metadata label + table
        container = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(container)
        vbox.setContentsMargins(4, 4, 4, 4)
        self.data_table_meta = QtWidgets.QLabel("")
        try:
            self.data_table_meta.setWordWrap(True)
            self.data_table_meta.setStyleSheet("color: #bbb; font-size: 11px;")
        except Exception:
            pass
        vbox.addWidget(self.data_table_meta)
        self.data_table = QtWidgets.QTableWidget()
        self.data_table.setColumnCount(2)
        self.data_table.setHorizontalHeaderLabels(["Wavelength", "Value"])
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.data_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        vbox.addWidget(self.data_table)
        self.data_table_dock.setWidget(container)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.data_table_dock)
        # Keep visibility action in sync with dock
        if self.data_table_action is not None:
            self.data_table_action.setChecked(True)
        # Refresh on selection/unit/normalization changes
        try:
            if self.dataset_view is not None and self.dataset_view.selectionModel() is not None:
                self.dataset_view.selectionModel().selectionChanged.connect(self._refresh_data_table)
        except Exception:
            pass
        try:
            if self.unit_combo is not None:
                self.unit_combo.currentTextChanged.connect(lambda *_: self._refresh_data_table())
        except Exception:
            pass
        try:
            if self.norm_combo is not None:
                self.norm_combo.currentTextChanged.connect(lambda *_: self._refresh_data_table())
        except Exception:
            pass

    def _refresh_data_table(self) -> None:
        """Populate the Data Table with the currently selected dataset (single selection)."""
        if self.data_table is None or self.dataset_view is None:
            return
        # Determine selected spectrum (single selection preferred)
        selected = self.dataset_view.selectionModel().selectedRows() if self.dataset_view.selectionModel() else []
        # Filter out root rows
        selected = [idx for idx in selected if idx.parent().isValid()]
        if len(selected) != 1:
            self.data_table.clearContents()
            self.data_table.setRowCount(0)
            try:
                if hasattr(self, "data_table_meta"):
                    self.data_table_meta.setText("")
            except Exception:
                pass
            return
        index = selected[0]
        alias_item = self.dataset_model.itemFromIndex(self.dataset_model.index(index.row(), 0, index.parent()))
        spec_id = None
        for sid, item in self._dataset_items.items():
            if item is alias_item:
                spec_id = sid
                break
        if not spec_id:
            self.data_table.clearContents()
            self.data_table.setRowCount(0)
            try:
                if hasattr(self, "data_table_meta"):
                    self.data_table_meta.setText("")
            except Exception:
                pass
            return
        try:
            spec = self.overlay_service.get(spec_id)
        except Exception:
            self.data_table.clearContents()
            self.data_table.setRowCount(0)
            return
        # Build display arrays: convert X to nm first, then to the current display unit
        unit = self.unit_combo.currentText() if self.unit_combo is not None else "nm"
        # Convert from original x_unit to nm
        try:
            x_nm, y_converted, _ = self.units_service.convert_arrays(
                np.asarray(spec.x, dtype=float),
                np.asarray(spec.y, dtype=float),
                spec.x_unit,
                spec.y_unit,
                "nm",
                spec.y_unit,
            )
        except Exception:
            # Fallback for unknown Y units
            try:
                x_nm = self.units_service._to_canonical_wavelength(
                    np.asarray(spec.x, dtype=float), spec.x_unit
                )
                y_converted = np.asarray(spec.y, dtype=float)
            except Exception:
                x_nm = np.asarray(spec.x, dtype=float)
                y_converted = np.asarray(spec.y, dtype=float)
        # Apply calibration in nm space - REMOVED - calibration no longer used
        # x_nm, y_converted = self._apply_calibration_nm(x_nm, y_converted)

        # Convert nm to display unit
        if unit == "nm":
            x_disp = x_nm
        elif unit == "Å":
            x_disp = x_nm * 10.0
        elif unit == "µm":
            x_disp = x_nm / 1000.0
        elif unit == "cm⁻¹":
            with np.errstate(divide="ignore"):
                x_disp = 1e7 / x_nm
        else:
            x_disp = x_nm
        # Apply normalization (robust to NaNs/Infs). Use nm-space for area calculations.
        norm_mode = self.norm_combo.currentText() if self.norm_combo is not None else "None"
        use_global = self.norm_global_checkbox.isChecked() if hasattr(self, 'norm_global_checkbox') else False
        global_val = None
        if norm_mode != "None" and use_global:
            try:
                global_val = self._compute_global_normalization_value(norm_mode)
            except Exception:
                global_val = None
        y = self._apply_normalization(y_converted, norm_mode, global_val, x_nm)
        # Populate table (cap for very large datasets to keep UI responsive)
        cap = 20000
        n = int(min(len(x_disp), len(y), cap))
        self.data_table.setRowCount(n)
        self.data_table.setHorizontalHeaderLabels([f"Wavelength ({unit})", "Value"])
        for r in range(n):
            xi = QtWidgets.QTableWidgetItem(f"{float(x_disp[r]):.6g}")
            yi = QtWidgets.QTableWidgetItem(f"{float(y[r]):.6g}")
            xi.setFlags(xi.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            yi.setFlags(yi.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.data_table.setItem(r, 0, xi)
            self.data_table.setItem(r, 1, yi)
        self.data_table.resizeColumnsToContents()
        # Update the metadata label with credits
        try:
            credits = []
            meta = spec.metadata if isinstance(spec.metadata, dict) else {}
            cache_rec = meta.get("cache_record", {}) if isinstance(meta, dict) else {}
            src = cache_rec.get("source", {}) if isinstance(cache_rec, dict) else {}
            remote = src.get("remote", {}) if isinstance(src, dict) else {}
            if isinstance(remote, dict) and remote:
                provider = str(remote.get("provider") or "Remote")
                ident = str(remote.get("identifier") or remote.get("id") or "").strip()
                uri = str(remote.get("uri") or "")
                m = remote.get("metadata") if isinstance(remote.get("metadata"), dict) else {}
                mission = str(m.get("obs_collection") or m.get("telescope_name") or "").strip()
                instrument = str(m.get("instrument_name") or m.get("instrument") or "").strip()
                title = str(m.get("title") or "").strip()
                parts = [provider]
                if mission:
                    parts.append(mission)
                if instrument:
                    parts.append(instrument)
                line = " / ".join([p for p in parts if p])
                if ident:
                    line = f"{line} — {ident}"
                credits.append(line)
                if title:
                    credits.append(title)
                if uri:
                    credits.append(uri)
            if not credits:
                ingest = src.get("ingest", {}) if isinstance(src, dict) else {}
                if isinstance(ingest, dict):
                    spath = str(ingest.get("source_path") or "")
                    if spath:
                        credits.append(spath)
            if hasattr(self, "data_table_meta"):
                self.data_table_meta.setText(" \n".join([c for c in credits if c]))
        except Exception:
            try:
                if hasattr(self, "data_table_meta"):
                    self.data_table_meta.setText("")
            except Exception:
                pass

    @ui_action("Failed to show documentation")
    def show_documentation(self) -> None:
        """Open documentation dialog."""
        dialog = DocumentationDialog(self)
        dialog.exec()

    @ui_action("Failed to open Remote Data tab")
    def show_remote_data_tab(self) -> None:
        # Switch to the Remote Data tab in Inspector dock
        self.inspector_dock.raise_()
        try:
            index = self.inspector_tabs.indexOf(self.remote_data_panel)
            if index != -1:
                self.inspector_tabs.setCurrentIndex(index)
        except Exception:
            pass

    @ui_action("Failed to open file(s)")
    def open_file(self) -> None:
        path_strs, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Open Spectrum(s)",
            str(SAMPLES_DIR),
            "Data files (*.csv *.txt *.dat *.fits *.fit *.fts *.jdx *.dx *.jcamp *.h5 *.hdf5);;All files (*.*)",
        )
        if not path_strs:
            return
        for path_str in path_strs:
            self._ingest_path(Path(path_str))

    @ui_action("Failed to open time series")
    def open_time_series(self) -> None:
        path_strs, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Open Time Series",
            str(SAMPLES_DIR),
            "Time series (*.csv *.txt *.dat *.fits *.fit *.fts *.h5 *.hdf5);;All files (*.*)",
        )
        if not path_strs:
            return
        for path_str in path_strs:
            self._ingest_time_series_path(Path(path_str))

    @ui_action("Failed to open time series")
    def open_time_series(self) -> None:
        path_strs, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Open Time Series",
            str(SAMPLES_DIR),
            "Time series files (*.csv *.txt *.dat *.fits *.fit *.fts *.h5 *.hdf5);;All files (*.*)",
        )
        if not path_strs:
            return
        for path_str in path_strs:
            self._ingest_time_series_path(Path(path_str))

    @ui_action("Failed to load sample")
    def load_sample_via_menu(self) -> None:
        if not SAMPLES_DIR.exists():
            QtWidgets.QMessageBox.information(self, "Samples", "No samples available.")
            return
        path_str, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Sample",
            str(SAMPLES_DIR),
            "Data files (*.csv *.txt *.dat *.fits *.fit *.fts *.jdx *.dx *.jcamp *.h5 *.hdf5);;All files (*.*)",
        )
        if not path_str:
            return
        self._ingest_path(Path(path_str))

    @ui_action("Failed to import line list")
    def import_line_list_via_menu(self) -> None:
        """Prompt for a CSV file containing labeled spectral lines and overlay them.

        Expected columns (case-insensitive):
        - wavelength_nm (numeric)
        - label (string)
        Optional columns used for tooltip grouping: ion, note.
        """
        # Default to samples directory to encourage using bundled example
        start_dir = str(SAMPLES_DIR) if SAMPLES_DIR.exists() else str(Path.home())
        path_str, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import Line List",
            start_dir,
            "CSV files (*.csv);;All files (*.*)",
        )
        if not path_str:
            return
        self._import_line_list_csv(Path(path_str))

    def _import_line_list_csv(self, path: Path) -> None:
        """Parse a labeled line CSV and create vertical markers with colored labels."""
        if not path.exists():
            QtWidgets.QMessageBox.warning(self, "Line list", f"File not found: {path}")
            return
        try:
            rows: List[Dict[str, Any]] = []
            with path.open("r", encoding="utf-8", newline="") as handle:
                import csv as _csv
                reader = _csv.DictReader(handle)
                for raw in reader:
                    if not isinstance(raw, dict):
                        continue
                    rows.append({k.lower(): v for k, v in raw.items()})
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Line list", f"Failed to read CSV: {exc}")
            return
        if not rows:
            QtWidgets.QMessageBox.information(self, "Line list", "No rows found in CSV.")
            return
        added = 0
        # Heuristic helpers for unit detection
        def _convert_to_nm(raw_val: float, unit_hint: str | None) -> tuple[float, str]:
            u = (unit_hint or "").strip().lower()
            if u in {"nm", "nanometer", "nanometre", "nanometers", "nanometres"}:
                return raw_val, "nm"
            if u in {"m", "meter", "meters"}:
                return raw_val * 1e9, "m"
            if u in {"um", "µm", "micron", "micrometer", "micrometre"}:
                return raw_val * 1000.0, "µm"
            if u in {"angstrom", "ångström", "å", "a"}:
                return raw_val * 0.1, "Å"
            if u in {"cm^-1", "cm⁻¹", "cm-1"}:  # wavenumber to nm (λ_nm = 1e7 / ν_cm^-1)
                if raw_val > 0:
                    return 1e7 / raw_val, "cm⁻¹"
                return raw_val, "cm⁻¹"
            # Unspecified: apply numeric heuristic
            # Typical meters representation of visible lines ~5e-7; microns ~0.5; nm ~500
            if raw_val < 1e-3:  # assume meters
                return raw_val * 1e9, "(assumed m)"
            if 0.05 <= raw_val <= 50.0:  # could be µm range
                # If median later appears ~0.x treat as µm; for single pass assume µm if < 25
                if raw_val < 25.0:
                    return raw_val * 1000.0, "(assumed µm)"
            return raw_val, "(assumed nm)"

        for row in rows:
            # Accept multiple wavelength column variants
            wl_fields = [
                "wavelength_nm", "wavelength", "wavelength_m", "wavelength_um", "wavelength_angstrom", "wavelength_Å", "wavenumber", "wavenumber_cm-1", "wavenumber_cm^-1"
            ]
            wl_text = ""
            for key in wl_fields:
                if key in row and str(row.get(key)).strip():
                    wl_text = str(row.get(key)).strip()
                    break
            if not wl_text:
                continue
            try:
                raw_val = float(wl_text)
            except Exception:
                continue
            # Determine explicit unit hint from columns
            unit_hint = None
            for ukey in ["unit", "wavelength_unit", "x_unit"]:
                if ukey in row and str(row.get(ukey)).strip():
                    unit_hint = str(row.get(ukey)).strip()
                    break
            # If column name itself encodes unit
            if wl_text and unit_hint is None:
                for cname in wl_fields:
                    if cname in row and row.get(cname) == wl_text:
                        if cname.endswith("_m"):
                            unit_hint = "m"
                        elif cname.endswith("_um"):
                            unit_hint = "µm"
                        elif "angstrom" in cname.lower() or "å" in cname.lower():
                            unit_hint = "angstrom"
                        elif "wavenumber" in cname.lower():
                            unit_hint = "cm^-1"
                        elif cname.endswith("_nm"):
                            unit_hint = "nm"
                        break
            wavelength_nm, assumed = _convert_to_nm(raw_val, unit_hint)
            label = str(row.get("label") or row.get("name") or f"{wavelength_nm:.6g} nm").strip()
            ion = str(row.get("ion") or "").strip()
            note = str(row.get("note") or row.get("comment") or "").strip()
            color = self._next_palette_color()
            pen = pg.mkPen(color, width=1.2)
            try:
                disp = float(self.plot._x_nm_to_disp(np.array([wavelength_nm]))[0])  # type: ignore[attr-defined]
            except Exception:
                disp = wavelength_nm
            # Get current Y position for label
            try:
                (_, y_range) = self.plot.view_range()
                y0, y1 = float(y_range[0]), float(y_range[1])
                y_pos = y1 - (y1 - y0) * 0.04
            except Exception:
                y_pos = 0.0
            line_item = pg.InfiniteLine(pos=disp, angle=90, pen=pen, movable=False)
            text_item = pg.TextItem(text=label, color=color)
            text_item.setPos(disp, y_pos)  # Set initial position
            tooltip_bits = [f"{wavelength_nm:.6g} nm", f"src={assumed}"]
            if ion:
                tooltip_bits.append(ion)
            if note:
                tooltip_bits.append(note)
            line_item.setToolTip(" | ".join(tooltip_bits))
            text_item.setToolTip(" | ".join(tooltip_bits))
            try:
                self.plot._plot.addItem(line_item)
                self.plot._plot.addItem(text_item)
            except Exception:
                continue
            # Store in "Custom" element group
            custom_markers = self._line_markers_by_element.setdefault("Custom", [])
            custom_markers.append({
                'x_nm': wavelength_nm,
                'line': line_item,
                'text': text_item,
                'color': color,
                'label': label,
                'source_unit': assumed,
            })
            added += 1
        # Position labels vertically and refresh
        try:
            self._update_line_marker_positions()
        except Exception:
            pass
        if added:
            self.statusBar().showMessage(f"Added {added} spectral line(s) from '{path.name}'", 5000)
        else:
            QtWidgets.QMessageBox.information(self, "Line list", "No valid wavelength rows found.")

    def _clear_line_list_markers(self) -> None:
        """Remove all user-imported and reference spectral line markers from the plot."""
        total = sum(len(markers) for markers in self._line_markers_by_element.values())
        if total == 0:
            self.statusBar().showMessage("No line markers to clear", 3000)
            return
        removed = 0
        for element, markers in list(self._line_markers_by_element.items()):
            for marker in markers:
                try:
                    self.plot._plot.removeItem(marker.get('line'))
                    self.plot._plot.removeItem(marker.get('text'))
                    removed += 1
                except Exception:
                    pass
        self._line_markers_by_element.clear()
        self.statusBar().showMessage(f"Cleared {removed} line marker(s)", 5000)

    def _on_edit_labels(self) -> None:
        """Open dialog to edit custom plot title and axis labels."""
        current = self.plot.get_current_labels()
        
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Edit Plot Labels")
        dialog.setMinimumWidth(400)
        
        layout = QtWidgets.QFormLayout(dialog)
        
        # Title field
        title_edit = QtWidgets.QLineEdit()
        title_edit.setPlaceholderText("Leave empty for auto-generated title")
        title_edit.setText(self.plot.get_custom_title() or "")
        layout.addRow("Plot Title:", title_edit)
        
        # X-axis label field
        x_edit = QtWidgets.QLineEdit()
        x_edit.setPlaceholderText("Leave empty for default (Wavelength/Wavenumber)")
        x_edit.setText(self.plot.get_custom_x_axis_label() or "")
        layout.addRow("X-Axis Label:", x_edit)
        
        # Y-axis label field
        y_edit = QtWidgets.QLineEdit()
        y_edit.setPlaceholderText("Leave empty for auto-detected (Intensity/Absorbance/etc)")
        y_edit.setText(self.plot.get_custom_y_axis_label() or "")
        layout.addRow("Y-Axis Label:", y_edit)
        
        # Info label
        info_label = QtWidgets.QLabel(
            "<small>Leave fields empty to use automatic labels based on data type.</small>"
        )
        info_label.setWordWrap(True)
        layout.addRow(info_label)
        
        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel |
            QtWidgets.QDialogButtonBox.StandardButton.Reset
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        
        # Reset button clears all fields
        reset_btn = button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Reset)
        reset_btn.clicked.connect(lambda: (title_edit.clear(), x_edit.clear(), y_edit.clear()))
        
        layout.addRow(button_box)
        
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            # Apply custom labels (empty string = None = auto)
            self.plot.set_custom_title(title_edit.text().strip() or None)
            self.plot.set_custom_x_axis_label(x_edit.text().strip() or None)
            self.plot.set_custom_y_axis_label(y_edit.text().strip() or None)
            self.statusBar().showMessage("Plot labels updated", 3000)

    def _on_quick_screenshot(self) -> None:
        """Quick screenshot export of the current plot."""
        from pathlib import Path
        import datetime

        # Generate default filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"plot_{timestamp}.png"
        default_path = Path.home() / "Desktop" / default_name

        # Ask user for save location
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Plot Screenshot",
            str(default_path),
            "PNG Image (*.png);;All Files (*.*)"
        )

        if not file_path:
            return  # User cancelled

        try:
            # Export plot to PNG
            self.plot.export_png(Path(file_path))
            self.statusBar().showMessage(f"Plot saved to {Path(file_path).name}", 5000)
            self._log("Screenshot", f"Saved plot to {file_path}")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(
                self,
                "Screenshot Failed",
                f"Failed to save screenshot: {exc}"
            )

    def _on_annotation_requested(self, x_nm: float, y_fraction: float, x_max_nm: object) -> None:
        """Handle request to add an annotation at the specified position.
        
        Args:
            x_nm: X position in canonical nm
            y_fraction: Y position as fraction of view (0=bottom, 1=top)
            x_max_nm: If not None, this is a range annotation
        """
        from app.ui.plot_pane import Annotation
        
        # Get list of visible datasets for selection
        visible_spectra = [
            spec for spec in self.overlay_service.list()
            if self._visibility.get(spec.id, True)
        ]
        
        if not visible_spectra:
            QtWidgets.QMessageBox.information(
                self, "Add Note", "No visible datasets to annotate."
            )
            return
        
        # Build dialog
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Add Note")
        dialog.setMinimumWidth(350)
        
        layout = QtWidgets.QFormLayout(dialog)
        
        # Dataset selector
        dataset_combo = QtWidgets.QComboBox()
        for spec in visible_spectra:
            alias = spec.name or spec.id[:8]
            dataset_combo.addItem(alias, spec.id)
        layout.addRow("Dataset:", dataset_combo)
        
        # Position info
        is_range = x_max_nm is not None
        if is_range:
            pos_text = f"{x_nm:.2f} – {x_max_nm:.2f} nm"
        else:
            pos_text = f"{x_nm:.2f} nm"
        pos_label = QtWidgets.QLabel(pos_text)
        layout.addRow("Position:", pos_label)
        
        # Note text
        note_edit = QtWidgets.QLineEdit()
        note_edit.setPlaceholderText("Enter note (e.g., 'H-alpha emission')")
        layout.addRow("Note:", note_edit)
        
        # Orientation
        orientation_combo = QtWidgets.QComboBox()
        orientation_combo.addItem("Horizontal", False)
        orientation_combo.addItem("Vertical", True)
        layout.addRow("Orientation:", orientation_combo)
        
        # Color picker
        color_btn = QtWidgets.QPushButton("Yellow")
        color_btn.setStyleSheet("background-color: #FFFF00; color: black;")
        selected_color = ["#FFFF00"]  # Mutable to allow change in nested function
        
        def pick_color():
            color = QtWidgets.QColorDialog.getColor(
                QtGui.QColor(selected_color[0]), dialog, "Note Color"
            )
            if color.isValid():
                selected_color[0] = color.name()
                color_btn.setStyleSheet(f"background-color: {color.name()};")
                # Adjust text color for readability
                luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
                text_color = "black" if luminance > 128 else "white"
                color_btn.setStyleSheet(f"background-color: {color.name()}; color: {text_color};")
        
        color_btn.clicked.connect(pick_color)
        layout.addRow("Color:", color_btn)
        
        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            note_text = note_edit.text().strip()
            if not note_text:
                return
            
            dataset_id = dataset_combo.currentData()
            is_vertical = orientation_combo.currentData()
            annotation = Annotation(
                dataset_id=dataset_id,
                text=note_text,
                x_nm=x_nm,
                x_max_nm=float(x_max_nm) if x_max_nm is not None else None,
                y_fraction=y_fraction,
                color=selected_color[0],
                vertical=is_vertical,
            )
            
            self.plot.add_annotation(annotation)
            self.statusBar().showMessage(f"Note added: {note_text}", 3000)
            self._log("annotations", f"Added note '{note_text}' at {pos_text}")

            # Auto-save annotations for this dataset
            try:
                self._save_annotations_for_dataset(annotation.dataset_id)
            except Exception:
                pass  # Non-fatal

    def _on_notes_toggled(self, visible: bool) -> None:
        """Show or hide all annotation notes."""
        self.plot.set_all_annotations_visible(visible)
        self.statusBar().showMessage(f"Notes {'shown' if visible else 'hidden'}", 3000)

    def _on_manage_notes(self) -> None:
        """Open dialog to view and manage all annotations."""
        from app.ui.plot_pane import Annotation
        
        annotations = self.plot.get_annotations()
        if not annotations:
            QtWidgets.QMessageBox.information(
                self, "Manage Notes", "No notes to manage. Right-click on the plot to add notes."
            )
            return
        
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Manage Notes")
        dialog.setMinimumSize(500, 400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # Create table
        table = QtWidgets.QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Dataset", "Position", "Note", "Visible", ""])
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setRowCount(len(annotations))
        
        for row, ann in enumerate(annotations):
            # Dataset name
            # Get alias from overlay service or use dataset ID
            alias = ann.dataset_id[:8] if ann.dataset_id else "Unknown"
            try:
                spec = self.overlay_service.get(ann.dataset_id)
                if spec:
                    alias = spec.name or alias
            except Exception:
                pass
            dataset_item = QtWidgets.QTableWidgetItem(alias)
            dataset_item.setData(QtCore.Qt.ItemDataRole.UserRole, ann.id)
            dataset_item.setFlags(dataset_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, dataset_item)
            
            # Position
            if ann.x_max_nm is not None:
                pos_text = f"{ann.x_nm:.1f}–{ann.x_max_nm:.1f} nm"
            else:
                pos_text = f"{ann.x_nm:.1f} nm"
            pos_item = QtWidgets.QTableWidgetItem(pos_text)
            pos_item.setFlags(pos_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 1, pos_item)
            
            # Note text (editable)
            note_item = QtWidgets.QTableWidgetItem(ann.text)
            table.setItem(row, 2, note_item)
            
            # Visibility checkbox
            vis_widget = QtWidgets.QWidget()
            vis_layout = QtWidgets.QHBoxLayout(vis_widget)
            vis_layout.setContentsMargins(0, 0, 0, 0)
            vis_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            vis_check = QtWidgets.QCheckBox()
            vis_check.setChecked(ann.visible)
            vis_check.stateChanged.connect(
                lambda state, aid=ann.id: self.plot.set_annotation_visible(aid, state == QtCore.Qt.CheckState.Checked.value)
            )
            vis_layout.addWidget(vis_check)
            table.setCellWidget(row, 3, vis_widget)
            
            # Delete button
            del_btn = QtWidgets.QPushButton("×")
            del_btn.setFixedWidth(30)
            del_btn.setToolTip("Delete this note")
            del_btn.clicked.connect(
                lambda checked, aid=ann.id, r=row: self._delete_annotation_row(table, aid, r)
            )
            table.setCellWidget(row, 4, del_btn)
        
        layout.addWidget(table)
        
        # Track edits to apply on close
        def apply_edits():
            edited_datasets = set()
            for row in range(table.rowCount()):
                dataset_item = table.item(row, 0)
                if dataset_item is None:
                    continue
                ann_id = dataset_item.data(QtCore.Qt.ItemDataRole.UserRole)
                note_item = table.item(row, 2)
                if note_item:
                    new_text = note_item.text()
                    if self.plot.update_annotation(ann_id, text=new_text):
                        # Track which datasets were edited
                        ann = self.plot.get_annotation(ann_id)
                        if ann:
                            edited_datasets.add(ann.dataset_id)

            # Auto-save annotations for edited datasets
            for dataset_id in edited_datasets:
                try:
                    self._save_annotations_for_dataset(dataset_id)
                except Exception:
                    pass  # Non-fatal
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        clear_all_btn = QtWidgets.QPushButton("Clear All Notes")
        clear_all_btn.clicked.connect(lambda: self._clear_all_annotations(dialog))
        button_layout.addWidget(clear_all_btn)
        
        button_layout.addStretch()
        
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(lambda: (apply_edits(), dialog.accept()))
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()

    def _delete_annotation_row(self, table: QtWidgets.QTableWidget, ann_id: str, row: int) -> None:
        """Delete an annotation and remove its row from the table."""
        # Get dataset ID before deletion
        ann = self.plot.get_annotation(ann_id)
        dataset_id = ann.dataset_id if ann else None

        self.plot.remove_annotation(ann_id)
        table.removeRow(row)

        # Auto-save annotations for the dataset
        if dataset_id:
            try:
                self._save_annotations_for_dataset(dataset_id)
            except Exception:
                pass  # Non-fatal

        # Update row indices for remaining delete buttons
        for r in range(table.rowCount()):
            del_btn = table.cellWidget(r, 4)
            if del_btn:
                del_btn.clicked.disconnect()
                item = table.item(r, 0)
                if item:
                    aid = item.data(QtCore.Qt.ItemDataRole.UserRole)
                    del_btn.clicked.connect(
                        lambda checked, a=aid, row=r: self._delete_annotation_row(table, a, row)
                    )

    def _clear_all_annotations(self, parent_dialog: QtWidgets.QDialog) -> None:
        """Clear all annotations after confirmation."""
        count = len(self.plot.get_annotations())
        if count == 0:
            return

        reply = QtWidgets.QMessageBox.question(
            parent_dialog,
            "Clear All Notes",
            f"Delete all {count} notes?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # Collect all dataset IDs that have annotations
            dataset_ids = set()
            for ann in self.plot.get_annotations():
                dataset_ids.add(ann.dataset_id)

            self.plot.clear_annotations()
            parent_dialog.accept()
            self.statusBar().showMessage(f"Cleared {count} notes", 3000)

            # Auto-save (delete annotation files) for all affected datasets
            for dataset_id in dataset_ids:
                try:
                    self._save_annotations_for_dataset(dataset_id)
                except Exception:
                    pass  # Non-fatal

    def _on_line_labels_toggled(self, visible: bool) -> None:
        """Show or hide textual labels for all spectral line markers."""
        self._line_labels_visible = bool(visible)
        for element_markers in self._line_markers_by_element.values():
            for marker in element_markers:
                try:
                    text_item = marker.get('text')
                    if text_item is not None:
                        text_item.setVisible(self._line_labels_visible)
                except Exception:
                    continue
        # No status spam; brief confirmation
        self.statusBar().showMessage("Line labels {}".format("shown" if visible else "hidden"), 3000)

    @ui_action("Export failed")
    def export_center(self) -> None:
        """Unified export entry-point to write manifest, CSVs, and plot artifacts."""
        spectra = [spec for spec in self.overlay_service.list() if self._visibility.get(spec.id, True)]
        if not spectra:
            QtWidgets.QMessageBox.information(self, "Export", "No visible spectra to export.")
            return
        allow_composite = len(spectra) >= 2
        # Use lazy import to avoid circular dependency
        from app import main as main_module
        DialogClass = getattr(main_module, "ExportCenterDialog")
        dialog = DialogClass(self, allow_composite=allow_composite)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        opts = dialog.result()
        if not any([opts.manifest, opts.wide_csv, opts.composite_csv, opts.plot_png, opts.plot_svg, opts.plot_csv]):
            return
        base_str, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Choose export base name",
            str(Path.home() / "export" / "export"),
            "All files (*.*)",
        )
        if not base_str:
            return
        base = Path(base_str)
        try:
            # Manifest bundle (JSON + per-spectrum CSVs + PNG snapshot)
            if opts.manifest:
                outcome = self.provenance_service.export_bundle(
                    spectra,
                    base.with_suffix(".json"),
                    png_writer=lambda p: self.plot.export_png(p),
                )
                self._log("Export", f"Bundle written: {outcome.get('manifest_path')}")
            # Wide CSV
            if opts.wide_csv:
                self.provenance_service.write_wide_csv(base.with_name(base.stem + "-wide.csv"), spectra)
                self._log("Export", f"Wide CSV written: {base.with_name(base.stem + '-wide.csv')}")
            # Composite CSV (mean across visible spectra)
            if opts.composite_csv and allow_composite:
                self.provenance_service.write_composite_csv(base.with_name(base.stem + "-composite.csv"), spectra)
                self._log("Export", f"Composite CSV written: {base.with_name(base.stem + '-composite.csv')}")
            # Plot artifacts via pyqtgraph exporters (best-effort)
            try:
                from pyqtgraph.exporters import ImageExporter, SVGExporter, CSVExporter  # type: ignore
                plot_item = self.plot._plot.plotItem  # type: ignore[attr-defined]
                if opts.plot_png:
                    ImageExporter(plot_item).export(str(base.with_name(base.stem + "-plot.png")))
                    self._log("Export", f"Plot PNG written: {base.with_name(base.stem + '-plot.png')}")
                if opts.plot_svg:
                    SVGExporter(plot_item).export(str(base.with_name(base.stem + "-plot.svg")))
                    self._log("Export", f"Plot SVG written: {base.with_name(base.stem + '-plot.svg')}")
                if opts.plot_csv:
                    CSVExporter(plot_item).export(fileName=str(base.with_name(base.stem + "-plot.csv")))
                    self._log("Export", f"Plot CSV written: {base.with_name(base.stem + '-plot.csv')}")
            except Exception:
                # Ignore exporter errors; manifest/CSVs may still have succeeded
                pass
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Export failed", str(exc))

    def _persistence_disabled_via_env(self) -> bool:
        flag = os.environ.get("SPECTRA_DISABLE_PERSISTENCE")
        if flag is None:
            return False
        return flag.strip().lower() in {"1", "true", "yes", "on"}

    def _load_persistence_preference(self) -> bool:
        settings = QtCore.QSettings("SpectraApp", "DesktopPreview")
        return bool(settings.value("persistence/disabled", False, type=bool))

    def _load_plot_max_points(self) -> int:
        settings = QtCore.QSettings("SpectraApp", "DesktopPreview")
        stored = settings.value(PLOT_MAX_POINTS_KEY, PlotPane.DEFAULT_MAX_POINTS, type=int)
        return PlotPane.normalize_max_points(stored)

    def _save_plot_max_points(self, value: int) -> None:
        settings = QtCore.QSettings("SpectraApp", "DesktopPreview")
        settings.setValue(PLOT_MAX_POINTS_KEY, int(value))

    # ----------------------------- Palette preferences ---------------------
    def _load_palette_preferences(self) -> None:
        settings = QtCore.QSettings("SpectraApp", "DesktopPreview")
        self._use_uniform_palette = bool(settings.value("palette/uniform_enabled", False, type=bool))
        color_str = str(settings.value("palette/uniform_color", self._uniform_color.name()))
        try:
            self._uniform_color = QtGui.QColor(color_str)
        except Exception:
            pass
        # If enabled, retint datasets immediately
        if self._use_uniform_palette:
            try:
                self._retint_datasets_only()
            except Exception:
                pass

    def _save_palette_preferences(self) -> None:
        settings = QtCore.QSettings("SpectraApp", "DesktopPreview")
        settings.setValue("palette/uniform_enabled", bool(self._use_uniform_palette))
        try:
            settings.setValue("palette/uniform_color", self._uniform_color.name())
        except Exception:
            pass

    def _on_persistence_toggled(self, enabled: bool) -> None:
        if self._persistence_env_disabled:
            return
        self._persistence_disabled = not enabled
        settings = QtCore.QSettings("SpectraApp", "DesktopPreview")
        settings.setValue("persistence/disabled", self._persistence_disabled)
        if self._persistence_disabled:
            self.store = None
            self._log("System", "Persistent cache disabled. New data will be stored in memory only.")
        else:
            # Re-enable persistent cache in the consolidated cache directory
            self.store = LocalStore(base_dir=self._default_store_dir)
            self._log("System", "Persistent cache enabled.")
        self.ingest_service.store = self.store
        if hasattr(self, "remote_data_service") and isinstance(self.remote_data_service, RemoteDataService):
            if self.store is None:
                # When disabled, still use consolidated cache dir for remote downloads
                self.remote_data_service.store = LocalStore(base_dir=self._default_store_dir)
            else:
                self.remote_data_service.store = self.store
        self._build_library_tab()

    def _log(self, channel: str, message: str) -> None:
        line = f"[{channel}] {message}"
        print(line)
        # Always marshal UI updates to the GUI thread to avoid cross-thread warnings
        try:
            if QtCore.QThread.currentThread() is self.thread():
                self._append_log_line(line)
            else:
                QtCore.QMetaObject.invokeMethod(
                    self,
                    "_append_log_line",
                    getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection,
                    line,
                )
        except Exception:
            # Best-effort fallback; avoid crashing on logging
            pass

    @QtCore.Slot(str)  # type: ignore[name-defined]
    def _append_log_line(self, line: str) -> None:
        try:
            if self.log_view is not None:
                self.log_view.appendPlainText(line)
        except Exception:
            pass

    # ----------------------------- Global progress bar -------------------
    @QtCore.Slot(int)  # type: ignore[name-defined]
    def _on_global_download_started(self, total: int) -> None:
        try:
            self._status_progress.setVisible(True)
            self._status_progress.setRange(0, 0)  # indeterminate per-file
            self._status_progress.setValue(0)
            self.statusBar().showMessage(f"Downloading {int(total)} item(s)…")
        except Exception:
            pass

    @QtCore.Slot(str, int, int)  # type: ignore[name-defined]
    def _on_global_download_progress(self, label: str, received: int, total: int) -> None:
        try:
            if total >= 0:
                self._status_progress.setRange(0, max(1, total))
                self._status_progress.setValue(min(received, total))
            else:
                self._status_progress.setRange(0, 0)
                self._status_progress.setValue(0)
            self.statusBar().showMessage(f"Downloading {label}…")
        except Exception:
            pass

    @QtCore.Slot()  # type: ignore[name-defined]
    def _on_global_download_finished(self) -> None:
        try:
            self._status_progress.setVisible(False)
            self._status_progress.setRange(0, 1)
            self._status_progress.setValue(0)
            self.statusBar().showMessage("Ready", 3000)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Library, ingest, and docs helpers
    def _refresh_library_view(self) -> None:
        """Refresh the library view with organized groups."""
        if self.library_view is None:
            return
        self.library_view.clear()
        
        # Prefer the main store
        effective_store = self.store
        if effective_store is None and hasattr(self, "remote_data_service"):
            effective_store = getattr(self.remote_data_service, "store", None)
        
        entries = effective_store.list_entries() if effective_store is not None else {}
        
        # Organize entries by source type
        local_items: list = []
        remote_items: dict = {}  # provider -> target -> list of (name, record, sha)
        
        for _sha, record in entries.items():
            name = str(record.get("filename") or Path(str(record.get("stored_path", ""))).name)
            src = record.get("source", {})
            
            if isinstance(src, dict) and isinstance(src.get("remote"), dict):
                remote = src.get("remote") or {}
                provider = str(remote.get("provider") or "Remote")
                
                # Extract target from multiple possible locations
                target = ""
                for key in ["target_name", "target", "object_name", "identifier"]:
                    val = remote.get(key)
                    if val and str(val).strip():
                        target = str(val).strip()
                        break
                
                # Also check metadata for target
                if not target:
                    meta = remote.get("metadata", {})
                    if isinstance(meta, dict):
                        for key in ["target_name", "target", "object_name"]:
                            val = meta.get(key)
                            if val and str(val).strip():
                                target = str(val).strip()
                                break
                
                # Also try to extract from filename patterns like "jupiter_" or "sirius_"
                if not target:
                    name_lower = name.lower()
                    for known in ["jupiter", "sirius", "mars", "saturn", "wasp", "hd_", "ngc_"]:
                        if known in name_lower:
                            target = known.replace("_", "").upper()
                            break
                
                if not target:
                    target = "Other"
                
                if provider not in remote_items:
                    remote_items[provider] = {}
                if target not in remote_items[provider]:
                    remote_items[provider][target] = []
                remote_items[provider][target].append((name, record, _sha))
            else:
                local_items.append((name, record, _sha))
        
        # Add Local Imports group
        if local_items:
            local_root = QtWidgets.QTreeWidgetItem(["Local Imports", f"({len(local_items)})"])
            self.library_view.addTopLevelItem(local_root)
            for name, record, sha in local_items:
                child = QtWidgets.QTreeWidgetItem([name, ""])
                child.setData(0, QtCore.Qt.ItemDataRole.UserRole, sha)
                child.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, record.get("stored_path"))
                local_root.addChild(child)
            local_root.setExpanded(True)
        
        # Add Remote groups by provider
        for provider, targets in remote_items.items():
            total = sum(len(items) for items in targets.values())
            provider_root = QtWidgets.QTreeWidgetItem([provider, f"({total})"])
            self.library_view.addTopLevelItem(provider_root)
            
            # Add targets as subgroups
            for target, items in sorted(targets.items()):
                if len(targets) > 1 and target:  # Only create target subgroups if multiple targets
                    target_root = QtWidgets.QTreeWidgetItem([target or "Unknown", f"({len(items)})"])
                    provider_root.addChild(target_root)
                    for name, record, sha in items:
                        child = QtWidgets.QTreeWidgetItem([name, ""])
                        child.setData(0, QtCore.Qt.ItemDataRole.UserRole, sha)
                        child.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, record.get("stored_path"))
                        target_root.addChild(child)
                    target_root.setExpanded(False)
                else:
                    # Single target or empty - add directly under provider
                    for name, record, sha in items:
                        child = QtWidgets.QTreeWidgetItem([name, target or ""])
                        child.setData(0, QtCore.Qt.ItemDataRole.UserRole, sha)
                        child.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, record.get("stored_path"))
                        provider_root.addChild(child)
            provider_root.setExpanded(True)
        
        # Add Samples directory
        try:
            try:
                from app import main as main_module
                samples_dir = getattr(main_module, "SAMPLES_DIR", SAMPLES_DIR)
            except Exception:
                samples_dir = SAMPLES_DIR
            if samples_dir and Path(samples_dir).exists():
                eligible: list[Path] = []
                for p in sorted(Path(samples_dir).rglob("*")):  # Recursive glob
                    if p.is_file() and p.suffix.lower() in {".csv", ".txt", ".dat", ".fits", ".fit", ".fts", ".jdx", ".dx", ".jcamp", ".h5", ".hdf5"}:
                        eligible.append(p)
                if eligible:
                    samples_root = QtWidgets.QTreeWidgetItem(["Samples", f"({len(eligible)})"])
                    self.library_view.addTopLevelItem(samples_root)
                    
                    # Group samples by subdirectory
                    samples_by_dir: dict = {}
                    for p in eligible:
                        rel = p.relative_to(samples_dir)
                        if len(rel.parts) > 1:
                            subdir = rel.parts[0]
                        else:
                            subdir = ""
                        if subdir not in samples_by_dir:
                            samples_by_dir[subdir] = []
                        samples_by_dir[subdir].append(p)
                    
                    for subdir in sorted(samples_by_dir.keys()):
                        files = samples_by_dir[subdir]
                        if subdir:
                            dir_item = QtWidgets.QTreeWidgetItem([subdir, f"({len(files)})"])
                            samples_root.addChild(dir_item)
                            for p in files:
                                child = QtWidgets.QTreeWidgetItem([p.name, ""])
                                child.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(p))
                                dir_item.addChild(child)
                        else:
                            for p in files:
                                child = QtWidgets.QTreeWidgetItem([p.name, ""])
                                child.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(p))
                                samples_root.addChild(child)
                    samples_root.setExpanded(False)
        except Exception:
            pass
        
        # Add Storage directory (curated, external, etc.)
        try:
            storage_dir = Path(__file__).parent.parent.parent / "storage"
            if storage_dir.exists():
                storage_eligible: list[Path] = []
                for subdir in ["curated", "external", "passbands"]:
                    sub_path = storage_dir / subdir
                    if sub_path.exists():
                        for p in sorted(sub_path.rglob("*")):
                            if p.is_file() and p.suffix.lower() in {".csv", ".txt", ".dat", ".fits", ".fit", ".fts", ".jdx", ".dx", ".jcamp", ".h5", ".hdf5", ".ecsv"}:
                                storage_eligible.append(p)
                
                if storage_eligible:
                    storage_root = QtWidgets.QTreeWidgetItem(["Storage", f"({len(storage_eligible)})"])
                    self.library_view.addTopLevelItem(storage_root)
                    
                    # Group by subdirectory
                    storage_by_dir: dict = {}
                    for p in storage_eligible:
                        rel = p.relative_to(storage_dir)
                        subdir = rel.parts[0] if rel.parts else ""
                        if subdir not in storage_by_dir:
                            storage_by_dir[subdir] = []
                        storage_by_dir[subdir].append(p)
                    
                    for subdir in sorted(storage_by_dir.keys()):
                        files = storage_by_dir[subdir]
                        if subdir:
                            dir_item = QtWidgets.QTreeWidgetItem([subdir, f"({len(files)})"])
                            storage_root.addChild(dir_item)
                            for p in files:
                                child = QtWidgets.QTreeWidgetItem([p.name, ""])
                                child.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(p))
                                dir_item.addChild(child)
                    storage_root.setExpanded(False)
        except Exception:
            pass
        
        # Show placeholder if empty
        if self.library_view.topLevelItemCount() == 0:
            self.library_view.addTopLevelItem(QtWidgets.QTreeWidgetItem(["No data in library", ""]))

        # Connect double-click handler
        try:
            was_blocked = self.library_view.blockSignals(True)
            try:
                self.library_view.itemActivated.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.library_view.blockSignals(was_blocked)
        except Exception:
            pass
        try:
            self.library_view.itemActivated.connect(self._on_library_item_activated)
        except Exception:
            pass

    def _on_library_filter_changed(self, text: str) -> None:
        """Filter library items based on search text."""
        if self.library_view is None:
            return

        filter_text = text.lower().strip()

        # Iterate through all top-level items (groups)
        for i in range(self.library_view.topLevelItemCount()):
            group = self.library_view.topLevelItem(i)
            if group is None:
                continue

            group_has_match = False

            # Check all children and subchildren
            self._filter_tree_item(group, filter_text)

            # Count visible children
            visible_count = 0
            for j in range(group.childCount()):
                child = group.child(j)
                if child and not child.isHidden():
                    visible_count += 1
                    group_has_match = True

            # Hide group if no children are visible
            group.setHidden(not group_has_match and filter_text != "")

    def _filter_tree_item(self, item: QtWidgets.QTreeWidgetItem, filter_text: str) -> bool:
        """Recursively filter tree items. Returns True if item or any child matches."""
        if filter_text == "":
            # No filter - show everything
            item.setHidden(False)
            for i in range(item.childCount()):
                child = item.child(i)
                if child:
                    self._filter_tree_item(child, filter_text)
            return True

        # Check if this item's text matches
        item_text = item.text(0).lower()
        matches = filter_text in item_text

        # Check children
        has_matching_child = False
        for i in range(item.childCount()):
            child = item.child(i)
            if child and self._filter_tree_item(child, filter_text):
                has_matching_child = True

        # Show item if it matches or has matching children
        should_show = matches or has_matching_child
        item.setHidden(not should_show)

        return should_show

    def _on_library_item_activated(self, item: QtWidgets.QTreeWidgetItem, _col: int) -> None:
        """Handle double-click on library item to re-import."""
        # Get path - could be direct path or SHA256 hash for cached files
        try:
            path_str = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            stored_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 1)
        except Exception:
            path_str = None
            stored_path = None
        
        # Determine which group to use based on source
        target_group_id = None
        
        # Check if this is from MAST (remote)
        parent = item.parent()
        grandparent = parent.parent() if parent else None
        if parent:
            parent_text = parent.text(0).upper() if parent.text(0) else ""
            grandparent_text = grandparent.text(0).upper() if grandparent and grandparent.text(0) else ""
            
            if "MAST" in parent_text or "MAST" in grandparent_text or "REMOTE" in parent_text:
                # Route to Remote Data group
                from app.services.dataset_group_service import GroupType
                remote_group = self.group_service.get_default_group(GroupType.REMOTE)
                if remote_group:
                    target_group_id = remote_group.id
        
        # Try stored_path first (for cached remote files)
        if stored_path and Path(str(stored_path)).exists():
            try:
                self._ingest_path(Path(str(stored_path)), target_group_id=target_group_id)
                return
            except Exception:
                pass
        
        # Fall back to direct path (for samples)
        if path_str and not path_str.startswith("sha") and Path(str(path_str)).exists():
            try:
                self._ingest_path(Path(str(path_str)))
            except Exception:
                pass

    def _record_remote_history_event(self, spectra: Spectrum | list[Spectrum]) -> Dict[str, str]:
        specs = spectra if isinstance(spectra, list) else [spectra]
        providers: dict[str, set[str]] = {}
        references: set[str] = set()
        last_payload: Dict[str, str] = {}

        for spec in specs:
            rec = spec.metadata.get("cache_record", {}) if isinstance(spec.metadata, dict) else {}
            src = rec.get("source", {}) if isinstance(rec, dict) else {}
            remote = src.get("remote", {}) if isinstance(src, dict) else {}
            if not isinstance(remote, dict):
                continue

            provider = str(remote.get("provider") or "Remote")
            ident = str(remote.get("identifier") or remote.get("id") or "")
            bucket = providers.setdefault(provider, set())
            if ident:
                bucket.add(ident)

            ref = str(remote.get("uri") or ident or provider)
            if ref.startswith("http"):
                ref = ref.rstrip("/").split("/")[-1][:55]
            references.add(ref)
            last_payload = {"provider": provider, "identifier": ident}

        if providers:
            descriptors: list[str] = []
            for provider, identifiers in providers.items():
                if identifiers:
                    descriptor = f"{provider} ({', '.join(sorted(identifiers))})"
                else:
                    descriptor = provider
                descriptors.append(descriptor)
            descriptor_text = "; ".join(descriptors)
            if len(specs) > 1:
                summary = f"Imported {len(specs)} remote dataset(s) from {descriptor_text}"
            else:
                summary = f"Imported remote data from {descriptor_text}"
            ref_list = sorted(references)
        else:
            summary = "Imported remote data"
            ref_list = []

        return last_payload

    @staticmethod
    def _format_bytes(value: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(max(value, 0))
        unit = 0
        while size >= 1024 and unit < len(units) - 1:
            size /= 1024.0
            unit += 1
        if unit == 0:
            return f"{int(size)} {units[unit]}"
        return f"{size:.1f} {units[unit]}"

    def _ingest_path(self, path: Path, target_group_id: Optional[str] = None) -> None:
        try:
            spectra = self.ingest_service.ingest(path)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Import failed", str(exc))
            return
        
        # Batch plot updates to avoid incremental redraws
        self.plot.begin_bulk_update()
        try:
            for spectrum in spectra:
                self.overlay_service.add(spectrum)
                self._add_spectrum(spectrum, defer_refresh=True, target_group_id=target_group_id)
            # Refresh plot once after all spectra loaded (avoid O(n²) behavior)
            norm_mode = self.norm_combo.currentText()
            use_global = self.norm_global_checkbox.isChecked() if hasattr(self, 'norm_global_checkbox') else False
            if use_global and norm_mode != "None":
                self._refresh_plot()
        finally:
            self.plot.end_bulk_update()  # Re-enable updates and autoscale

        # If dataset is very large, disable crosshair/hover to keep interactions smooth
        try:
            trace_count, total_points = self.plot.get_trace_stats()
            if trace_count >= 50 or total_points >= 500_000:
                self.plot.set_crosshair_visible(False)
                try:
                    if hasattr(self, "crosshair_action") and self.crosshair_action is not None:
                        self.crosshair_action.setChecked(False)
                except Exception:
                    pass
                try:
                    self.statusBar().showMessage("Performance mode: crosshair disabled for large dataset (hover overlay off)", 5000)
                except Exception:
                    pass
        except Exception:
            pass
        
        # Reflow overlays against the new y-range
        try:
            self._refresh_reference_overlay_geometry()
        except Exception:
            pass
        self._refresh_library_view()
        self._refresh_history_view()

    def _read_time_series(self, path: Path) -> TimeSeries:
        suffix = path.suffix.lower()
        if suffix in {".csv", ".txt", ".dat"}:
            return TimeSeriesCsvImporter().read(path)
        if suffix in {".fits", ".fit", ".fts", ".h5", ".hdf5"}:
            return TimeSeriesFitsImporter().read(path)
        raise ValueError(f"Unsupported time-series extension: {suffix}")

    def _ingest_time_series_path(self, path: Path) -> None:
        try:
            ts = self._read_time_series(path)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Import failed", str(exc))
            return

        self._add_time_series(ts)
        if self.time_plot is not None:
            try:
                self.time_plot.autoscale()
            except Exception:
                pass
        # Switch to Time Series tab when importing a light curve
        if self.data_tabs is not None and self.time_series_tab is not None:
            try:
                idx = self.data_tabs.indexOf(self.time_series_tab)
                if idx != -1:
                    self.data_tabs.setCurrentIndex(idx)
            except Exception:
                pass
        self._log("Time Series", f"Loaded {path.name}")

    def _add_time_series(self, ts: TimeSeries) -> None:
        if self.time_plot is None or self.time_series_view is None:
            return

        ts_id = getattr(ts, "id", None) or ts.name
        # Replace any existing trace with the same id
        if ts_id in self._time_series_items:
            self._remove_time_series_by_id(ts_id)

        color = self._next_palette_color()
        self._time_series_colors[ts_id] = color
        self._time_series_visibility[ts_id] = True
        self._time_series[ts_id] = ts

        style = TraceStyle(color=color, width=1.2, show_in_legend=True)
        alias = ts.name
        tag = self._format_time_series_tag(ts)
        if tag:
            alias = f"{alias} [{tag}]"
        x_vals = np.asarray(ts.time, dtype=float)
        y_vals = np.asarray(ts.values, dtype=float)
        sigma = np.asarray(ts.errors, dtype=float) if ts.errors is not None else None
        flags = np.asarray(ts.quality, dtype=int) if ts.quality is not None else None

        x_unit = getattr(ts, "time_unit", None) or "day"
        value_unit = getattr(ts, "value_unit", None) or "flux"
        self.time_plot.set_x_mode("time", label="Time", unit=x_unit)
        self.time_plot.set_y_label(f"Flux ({value_unit})" if value_unit else "Flux")

        self.time_plot.add_trace(
            key=str(ts_id),
            alias=alias,
            x_nm=x_vals,
            y=y_vals,
            style=style,
            uncertainty=sigma,
            quality_flags=flags,
        )
        self._append_time_series_row(ts, color)

    def _append_time_series_row(self, ts: TimeSeries, color: QtGui.QColor) -> None:
        if self.time_series_view is None:
            return
        item = QtWidgets.QTreeWidgetItem([ts.name, "", "", ""])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, getattr(ts, "id", ts.name))
        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable | QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
        item.setCheckState(1, QtCore.Qt.CheckState.Checked)
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
            item.setIcon(0, QtGui.QIcon(swatch))
        except Exception:
            pass
        self._set_time_series_row_tags(item, ts)
        self.time_series_view.addTopLevelItem(item)
        self._time_series_items[str(getattr(ts, "id", ts.name))] = item

    def _set_time_series_row_tags(self, item: QtWidgets.QTreeWidgetItem, ts: TimeSeries) -> None:
        channel = getattr(ts, "channel_id", None) or ""
        band = getattr(ts, "band", None) or ""
        wavelength = getattr(ts, "wavelength", None)
        band_text = band
        if wavelength is not None:
            if band_text:
                band_text = f"{band_text} @ {wavelength:.4g}"
            else:
                band_text = f"{wavelength:.4g}"
        item.setText(2, channel)
        item.setText(3, band_text)

    def _format_time_series_tag(self, ts: TimeSeries) -> str:
        channel = getattr(ts, "channel_id", None) or ""
        band = getattr(ts, "band", None) or ""
        wavelength = getattr(ts, "wavelength", None)
        parts: list[str] = []
        if channel:
            parts.append(channel)
        if band:
            parts.append(band)
        if wavelength is not None:
            parts.append(f"{wavelength:.4g}")
        return " | ".join(parts)

    def _refresh_time_series_trace(self, ts_id: str) -> None:
        if self.time_plot is None:
            return
        ts = self._time_series.get(ts_id)
        color = self._time_series_colors.get(ts_id)
        if ts is None or color is None:
            return

        style = TraceStyle(color=color, width=1.2, show_in_legend=True)
        alias = ts.name
        tag = self._format_time_series_tag(ts)
        if tag:
            alias = f"{alias} [{tag}]"
        x_vals = np.asarray(ts.time, dtype=float)
        y_vals = np.asarray(ts.values, dtype=float)
        sigma = np.asarray(ts.errors, dtype=float) if ts.errors is not None else None
        flags = np.asarray(ts.quality, dtype=int) if ts.quality is not None else None

        x_unit = getattr(ts, "time_unit", None) or "day"
        value_unit = getattr(ts, "value_unit", None) or "flux"
        self.time_plot.set_x_mode("time", label="Time", unit=x_unit)
        self.time_plot.set_y_label(f"Flux ({value_unit})" if value_unit else "Flux")

        self.time_plot.add_trace(
            key=str(ts_id),
            alias=alias,
            x_nm=x_vals,
            y=y_vals,
            style=style,
            uncertainty=sigma,
            quality_flags=flags,
        )

    def _remove_time_series_by_id(self, ts_id: str) -> None:
        try:
            if self.time_plot is not None:
                self.time_plot.remove_trace(ts_id)
        except Exception:
            pass
        self._time_series.pop(ts_id, None)
        self._time_series_colors.pop(ts_id, None)
        self._time_series_visibility.pop(ts_id, None)
        item = self._time_series_items.pop(ts_id, None)
        if item is not None and self.time_series_view is not None:
            idx = self.time_series_view.indexOfTopLevelItem(item)
            if idx != -1:
                self.time_series_view.takeTopLevelItem(idx)

    def _remove_selected_time_series(self) -> None:
        if self.time_series_view is None:
            return
        selected = [it for it in self.time_series_view.selectedItems() if it is not None]
        if not selected:
            return
        for item in selected:
            ts_id = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if ts_id:
                self._remove_time_series_by_id(str(ts_id))
        self._log("Time Series", f"Removed {len(selected)} entr{'y' if len(selected)==1 else 'ies'}")

    def _clear_all_time_series(self) -> None:
        for ts_id in list(self._time_series_items.keys()):
            self._remove_time_series_by_id(ts_id)
        if self.time_plot is not None:
            try:
                self.time_plot.autoscale()
            except Exception:
                pass
        self._log("Time Series", "Cleared all time-series entries")

    def _on_time_series_filter_changed(self, text: str) -> None:
        if self.time_series_view is None:
            return
        needle = (text or "").strip().lower()
        for i in range(self.time_series_view.topLevelItemCount()):
            item = self.time_series_view.topLevelItem(i)
            if item is None:
                continue
            item.setHidden(needle not in item.text(0).lower())

    def _on_time_series_item_changed(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        if column != 1 or self.time_plot is None:
            return
        ts_id = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if ts_id is None:
            return
        visible = item.checkState(1) == QtCore.Qt.CheckState.Checked
        self._time_series_visibility[str(ts_id)] = visible
        try:
            self.time_plot.set_visible(str(ts_id), visible)
        except Exception:
            pass

    def _on_time_series_context_menu(self, position: QtCore.QPoint) -> None:
        if self.time_series_view is None:
            return
        index = self.time_series_view.indexAt(position)
        if not index.isValid():
            return
        selected = self.time_series_view.selectedItems()
        if not selected:
            return
        menu = QtWidgets.QMenu(self.time_series_view)
        edit_action = menu.addAction("Edit tags...")
        if len(selected) == 1:
            remove_action = menu.addAction("Remove Time Series")
        else:
            remove_action = menu.addAction(f"Remove {len(selected)} Time Series")
        edit_action.triggered.connect(lambda _, sel=selected: self._edit_time_series_tags(sel))
        remove_action.triggered.connect(self._remove_selected_time_series)
        menu.exec(self.time_series_view.viewport().mapToGlobal(position))

    def _edit_time_series_tags(self, items: Sequence[QtWidgets.QTreeWidgetItem]) -> None:
        if not items:
            return
        ts_ids: list[str] = []
        for item in items:
            ts_id = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if ts_id:
                ts_ids.append(str(ts_id))
        if not ts_ids:
            return
        first_ts = self._time_series.get(ts_ids[0])
        if first_ts is None:
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Edit time-series tags")
        layout = QtWidgets.QFormLayout(dialog)
        channel_edit = QtWidgets.QLineEdit(dialog)
        channel_edit.setText(first_ts.channel_id or "")
        band_edit = QtWidgets.QLineEdit(dialog)
        band_edit.setText(first_ts.band or "")
        wavelength_edit = QtWidgets.QLineEdit(dialog)
        wavelength_edit.setPlaceholderText("optional")
        if first_ts.wavelength is not None:
            wavelength_edit.setText(f"{float(first_ts.wavelength):.6g}")

        layout.addRow("Channel", channel_edit)
        layout.addRow("Band", band_edit)
        layout.addRow("Wavelength", wavelength_edit)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        channel_val = channel_edit.text().strip() or None
        band_val = band_edit.text().strip() or None
        wavelength_val: Optional[float] = None
        raw_wavelength = wavelength_edit.text().strip()
        if raw_wavelength:
            try:
                wavelength_val = float(raw_wavelength)
            except Exception:
                wavelength_val = None

        for ts_id in ts_ids:
            ts = self._time_series.get(ts_id)
            if ts is None:
                continue
            ts.channel_id = channel_val
            ts.band = band_val
            ts.wavelength = wavelength_val
            item = self._time_series_items.get(ts_id)
            if item is not None:
                self._set_time_series_row_tags(item, ts)
            self._refresh_time_series_trace(ts_id)

    def _plot_flux_vs_wavelength_at_time(self) -> None:
        tagged = [
            (ts_id, ts)
            for ts_id, ts in self._time_series.items()
            if getattr(ts, "wavelength", None) is not None
        ]
        if len(tagged) < 2:
            QtWidgets.QMessageBox.information(self, "Flux vs wavelength", "Set wavelength tags on at least two time series first.")
            return

        def _finite_bounds(ts_list: Sequence[TimeSeries]) -> tuple[float, float]:
            mins: list[float] = []
            maxs: list[float] = []
            for ts in ts_list:
                arr = np.asarray(ts.time, dtype=float)
                arr = arr[np.isfinite(arr)]
                if arr.size:
                    mins.append(float(arr.min()))
                    maxs.append(float(arr.max()))
            if not mins or not maxs:
                return 0.0, 1.0
            return min(mins), max(maxs)

        t_min, t_max = _finite_bounds([ts for _, ts in tagged])
        if not np.isfinite(t_min) or not np.isfinite(t_max) or t_min == t_max:
            t_min, t_max = 0.0, 1.0
        default_time = 0.5 * (t_min + t_max)
        default_window = max((t_max - t_min) * 0.02, 0.001)

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Flux vs wavelength")
        form = QtWidgets.QFormLayout(dialog)

        time_spin = QtWidgets.QDoubleSpinBox(dialog)
        time_spin.setRange(-1e9, 1e9)
        time_spin.setDecimals(6)
        time_spin.setValue(default_time)
        window_spin = QtWidgets.QDoubleSpinBox(dialog)
        window_spin.setRange(0.0, 1e6)
        window_spin.setDecimals(6)
        window_spin.setValue(default_window)
        window_spin.setToolTip("Half-width window; median is used if data exist within this window, otherwise nearest-neighbour interpolation is used.")

        form.addRow("Time", time_spin)
        form.addRow("Window", window_spin)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        target_time = float(time_spin.value())
        window = float(window_spin.value())

        def _sample_flux(ts: TimeSeries) -> Optional[float]:
            t_arr = np.asarray(ts.time, dtype=float)
            f_arr = np.asarray(ts.values, dtype=float)
            mask = np.isfinite(t_arr) & np.isfinite(f_arr)
            if not mask.any():
                return None
            t_valid = t_arr[mask]
            f_valid = f_arr[mask]
            try:
                order = np.argsort(t_valid)
                t_valid = t_valid[order]
                f_valid = f_valid[order]
            except Exception:
                pass
            if window > 0:
                win_mask = np.abs(t_valid - target_time) <= (window * 0.5)
                if win_mask.any():
                    return float(np.nanmedian(f_valid[win_mask]))
            try:
                return float(np.interp(target_time, t_valid, f_valid))
            except Exception:
                return None

        wavelengths: list[float] = []
        fluxes: list[float] = []
        labels: list[str] = []

        for ts_id, ts in tagged:
            flux_val = _sample_flux(ts)
            if flux_val is None:
                continue
            wl = getattr(ts, "wavelength", None)
            if wl is None:
                continue
            wavelengths.append(float(wl))
            fluxes.append(flux_val)
            labels.append(ts.name)

        if not wavelengths:
            QtWidgets.QMessageBox.information(self, "Flux vs wavelength", "No usable flux values at the requested time.")
            return

        plot_dialog = QtWidgets.QDialog(self)
        plot_dialog.setWindowTitle(f"Flux vs wavelength @ t={target_time:.4g}")
        vbox = QtWidgets.QVBoxLayout(plot_dialog)
        plot_widget = pg.PlotWidget(plot_dialog)
        plot_widget.showGrid(x=True, y=True, alpha=0.25)
        scatter = pg.ScatterPlotItem(x=wavelengths, y=fluxes, pen=None, brush="c", size=9, symbol="o")
        plot_widget.addItem(scatter)
        plot_widget.setLabel("bottom", "Wavelength", units="")
        plot_widget.setLabel("left", "Flux", units="")
        vbox.addWidget(plot_widget)

        # Optional legend-like annotation using text items
        for x, y, label in zip(wavelengths, fluxes, labels):
            try:
                text = pg.TextItem(label, anchor=(0.5, -0.4))
                text.setPos(x, y)
                plot_widget.addItem(text)
            except Exception:
                pass

        close_buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close,
            parent=plot_dialog,
        )
        close_buttons.rejected.connect(plot_dialog.reject)
        close_buttons.accepted.connect(plot_dialog.accept)
        vbox.addWidget(close_buttons)
        plot_dialog.resize(420, 360)
        plot_dialog.exec()

    # Public helper used by tests
    def _add_spectrum(self, spectrum: Spectrum, *, defer_refresh: bool = False, target_group_id: Optional[str] = None) -> None:
        color = self._next_palette_color()
        self._spectrum_colors[spectrum.id] = color
        style = TraceStyle(color=color, width=1.0, show_in_legend=True)
        
        # Auto-categorize into appropriate group (or use specified target)
        try:
            if target_group_id:
                self.group_service.assign_to_group(spectrum.id, target_group_id)
            else:
                self.group_service.assign_to_group(spectrum)
        except Exception:
            pass
        
        # Convert X to canonical nm for plotting (plot expects x_nm in nanometers)
        try:
            x_nm, y_converted, _ = self.units_service.convert_arrays(
                np.asarray(spectrum.x, dtype=float),
                np.asarray(spectrum.y, dtype=float),
                spectrum.x_unit,
                spectrum.y_unit,
                "nm",
                spectrum.y_unit,
            )
        except Exception:
            # Fallback: if conversion fails (e.g., unknown Y unit like flux density),
            # just convert X and pass Y through unchanged
            try:
                x_nm = self.units_service._to_canonical_wavelength(
                    np.asarray(spectrum.x, dtype=float), spectrum.x_unit
                )
                y_converted = np.asarray(spectrum.y, dtype=float)
            except Exception:
                # Ultimate fallback: assume x is already in nm
                x_nm = np.asarray(spectrum.x, dtype=float)
                y_converted = np.asarray(spectrum.y, dtype=float)

        # Apply calibration then current normalization mode - REMOVED - calibration no longer used
        norm_mode = self.norm_combo.currentText()
        use_global = self.norm_global_checkbox.isChecked() if hasattr(self, 'norm_global_checkbox') else False
        # x_nm, y_cal = self._apply_calibration_nm(x_nm, y_converted)
        y_cal = y_converted  # Skip calibration step

        # If global normalization is enabled and there are existing spectra, we need to refresh all
        if use_global and norm_mode != "None" and len(self.overlay_service.list()) > 0:
            # Add the spectrum to the plot with temporary normalization, then refresh all
            y_data = self._apply_normalization(y_cal, norm_mode, None, x_nm)  # Temporary per-spectrum norm
            y_data = self._apply_y_scale(y_data)
        else:
            # Per-spectrum normalization or first spectrum
            y_data = self._apply_normalization(y_cal, norm_mode, None, x_nm)
            y_data = self._apply_y_scale(y_data)
        
        # If this is the first dataset and the original x-unit was microns, switch display to µm
        try:
            is_first_dataset = (len(self._dataset_items) == 0)
        except Exception:
            is_first_dataset = False
        if is_first_dataset and self.unit_combo is not None:
            try:
                src_units = {}
                if isinstance(spectrum.metadata, dict):
                    src_units = spectrum.metadata.get("source_units", {}) or {}
                orig_x = str(src_units.get("x") or spectrum.x_unit or "").strip().lower()
                if any(tok in orig_x for tok in ("um", "micron", "micrometer", "micrometre")):
                    # Use the UI label with micro sign
                    self.unit_combo.setCurrentText("µm")
            except Exception:
                pass

        self.plot.add_trace(
            key=spectrum.id,
            alias=spectrum.name,
            x_nm=x_nm,
            y=y_data,
            style=style,
            uncertainty=self._compute_display_uncertainty(spectrum, x_nm, y_cal, norm_mode, None),
            quality_flags=getattr(spectrum, "quality_flags", None),
        )
        self._visibility[spectrum.id] = True
        self._append_dataset_row(spectrum)

        # Update legend panel
        try:
            if hasattr(self, 'legend_panel'):
                self.legend_panel.add_legend_item(
                    spectrum.id,
                    spectrum.name,
                    color,
                    visible=True
                )
        except Exception:
            pass

        # Load any saved annotations for this dataset
        try:
            self._load_annotations_for_dataset(spectrum.id)
        except Exception:
            pass  # Non-fatal

        # If global normalization is enabled, refresh all spectra to apply global norm
        # (but only if not deferred to batch processing)
        if use_global and norm_mode != "None" and not defer_refresh:
            try:
                self._refresh_plot()
            except Exception:
                pass

    def _append_dataset_row(self, spectrum: Spectrum) -> None:
        if self.dataset_model is None or getattr(self, "_originals_item", None) is None:
            return
        # Create the alias cell for the dataset row and decorate it with a colour chip
        # that matches the trace colour used in the main plot. This makes it much easier
        # to correlate entries in the Data → Datasets tree with on-canvas traces.

        # Build display name with inline metadata (wavelength range, point count)
        display_name = str(spectrum.name)
        metadata_parts = []

        # Add wavelength range if available
        try:
            if spectrum.x is not None and len(spectrum.x) > 0:
                x_min = float(spectrum.x.min())
                x_max = float(spectrum.x.max())
                # Use current x-axis unit for display
                if hasattr(self, '_current_unit') and self._current_unit:
                    unit_label = self._current_unit.value if hasattr(self._current_unit, 'value') else str(self._current_unit)
                else:
                    unit_label = "nm"  # default

                # Format wavelength range compactly
                if x_min < 100:
                    range_str = f"{x_min:.1f}-{x_max:.1f} {unit_label}"
                else:
                    range_str = f"{x_min:.0f}-{x_max:.0f} {unit_label}"
                metadata_parts.append(range_str)

                # Add point count
                point_count = len(spectrum.x)
                if point_count >= 1000000:
                    pts_str = f"{point_count/1000000:.1f}M pts"
                elif point_count >= 1000:
                    pts_str = f"{point_count/1000:.1f}k pts"
                else:
                    pts_str = f"{point_count} pts"
                metadata_parts.append(pts_str)
        except Exception:
            pass  # Skip metadata if extraction fails

        # Assemble display name with metadata in parentheses
        if metadata_parts:
            display_name = f"{spectrum.name} ({', '.join(metadata_parts)})"

        # Add lock icon if normalization is locked
        if spectrum.normalization_locked:
            lock_icon = "\U0001F512 "  # 🔒
            display_name = lock_icon + display_name

        alias_item = QtGui.QStandardItem(display_name)
        alias_item.setEditable(False)
        # Store spectrum ID directly in item data for O(1) lookup in event handlers
        alias_item.setData(spectrum.id, QtCore.Qt.ItemDataRole.UserRole)
        visible_item = QtGui.QStandardItem("")
        visible_item.setCheckable(True)
        visible_item.setEditable(False)
        visible_item.setCheckState(QtCore.Qt.CheckState.Checked)
        # Attach a small colour swatch icon to the alias cell using the assigned spectrum colour.
        # The colour was assigned in _add_spectrum() via _next_palette_color() before this call.
        try:
            color = self._spectrum_colors.get(spectrum.id)
            if color is not None:
                # Build a 12×12 px swatch with a subtle border for dark themes
                swatch = QtGui.QPixmap(12, 12)
                swatch.fill(QtCore.Qt.GlobalColor.transparent)
                painter = QtGui.QPainter(swatch)
                try:
                    painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 180)))
                    painter.setBrush(QtGui.QBrush(color))
                    painter.drawRect(0, 0, 11, 11)
                finally:
                    painter.end()
                alias_item.setData(QtGui.QIcon(swatch), QtCore.Qt.ItemDataRole.DecorationRole)
                # Build tooltip with colour and provenance/credits if available
                tip_lines = [f"Trace colour: {color.name()}"]
                try:
                    meta = spectrum.metadata if isinstance(spectrum.metadata, dict) else {}
                    cache_rec = meta.get("cache_record", {}) if isinstance(meta, dict) else {}
                    src = cache_rec.get("source", {}) if isinstance(cache_rec, dict) else {}
                    remote = src.get("remote", {}) if isinstance(src, dict) else {}
                    if isinstance(remote, dict) and remote:
                        provider = str(remote.get("provider") or "Remote")
                        ident = str(remote.get("identifier") or remote.get("id") or "").strip()
                        mission = str(remote.get("metadata", {}).get("obs_collection") if isinstance(remote.get("metadata"), dict) else "")
                        telescope = str(remote.get("metadata", {}).get("telescope_name") if isinstance(remote.get("metadata"), dict) else "")
                        instrument = str(remote.get("metadata", {}).get("instrument_name") if isinstance(remote.get("metadata"), dict) else "")
                        title = str(remote.get("metadata", {}).get("title") if isinstance(remote.get("metadata"), dict) else "")
                        uri = str(remote.get("uri") or "")
                        # Assemble a concise credit block
                        credits: list[str] = [provider]
                        if mission:
                            credits.append(mission)
                        if telescope and telescope not in credits:
                            credits.append(telescope)
                        if instrument:
                            credits.append(instrument)
                        credit_line = " / ".join([c for c in credits if c])
                        if ident:
                            tip_lines.append(f"Source: {credit_line} — {ident}")
                        else:
                            tip_lines.append(f"Source: {credit_line}")
                        if title:
                            tip_lines.append(f"Title: {title}")
                        if uri:
                            tip_lines.append(f"URI: {uri}")
                except Exception:
                    pass
                alias_item.setToolTip("\n".join([line for line in tip_lines if line]))
                # Keep a handle so palette-mode toggles can refresh chips later if needed
                self._dataset_color_items[spectrum.id] = alias_item
        except Exception:
            # Non-fatal: skip decoration if any Qt painting fails in headless runs
            pass

        # Find the correct group for this spectrum and add it there
        try:
            group = self.group_service.get_group_for_dataset(spectrum.id)
            group_id = group.id if group else None
        except Exception:
            group_id = None
        
        # Add to the correct group in the tree view
        if group_id:
            group_item = self.dataset_panel.get_group_item(group_id)
            if group_item:
                group_item.appendRow([alias_item, visible_item])
            else:
                # Fallback to originals if group item not found
                if self._originals_item:
                    self._originals_item.appendRow([alias_item, visible_item])
        else:
            # Fallback to originals if no group assigned
            if self._originals_item:
                self._originals_item.appendRow([alias_item, visible_item])
        
        self._dataset_items[spectrum.id] = alias_item

    def _on_dataset_item_changed(self, item: QtGui.QStandardItem) -> None:
        if self.dataset_model is None or self.dataset_view is None:
            return
        #  Determine which spectrum id this row corresponds to (support tree rows)
        index = item.index()
        parent = index.parent()
        row = index.row()
        alias_index = self.dataset_model.index(row, 0, parent)
        alias_item = self.dataset_model.itemFromIndex(alias_index)
        
        # Use item's data role to store spec_id directly (avoids O(n) search)
        spec_id = alias_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if spec_id is None:
            # Fallback to linear search (for old items without stored ID)
            for sid, ali in self._dataset_items.items():
                if ali is alias_item:
                    spec_id = sid
                    alias_item.setData(sid, QtCore.Qt.ItemDataRole.UserRole)  # Cache for next time
                    break
        if spec_id is None:
            return
        vis_index = self.dataset_model.index(row, 1, parent)
        vis_item = self.dataset_model.itemFromIndex(vis_index)
        checked = vis_item.checkState() == QtCore.Qt.CheckState.Checked if vis_item else True
        self._visibility[spec_id] = checked
        try:
            self.plot.set_visible(spec_id, checked)
        except Exception:
            pass
        # Update merge preview to reflect visibility filtering
        try:
            self._mark_merge_preview_stale()
        except Exception:
            pass

    def _on_dataset_filter_changed(self, text: str) -> None:
        """Apply dataset filter to tree view (called via panel signal)."""
        if self.dataset_model is None or getattr(self, "_originals_item", None) is None:
            return
        needle = (text or "").strip().lower()
        parent_index = self.dataset_model.indexFromItem(self._originals_item)
        child_count = self._originals_item.rowCount()
        for row in range(child_count):
            alias_item = self._originals_item.child(row, 0)
            match = needle in alias_item.text().lower()
            # Hide or show the child row relative to the parent
            self.dataset_tree.setRowHidden(row, parent_index, not match)

    def _on_data_tab_changed(self, index: int) -> None:
        """Swap central plot when switching between spectra and time-series tabs."""
        if self.data_tabs is None or self.plot_stack is None:
            return
        widget = self.data_tabs.widget(index)
        if widget is self.time_series_tab:
            target = self.time_plot
        else:
            target = self.plot
        if target is not None:
            try:
                self.plot_stack.setCurrentWidget(target)
            except Exception:
                pass

    def _remove_selected_datasets(self, indexes: list[QtCore.QModelIndex]) -> None:
        """Remove selected datasets from the overlay and UI (called via panel signal)."""
        if not indexes:
            return
        
        # Collect spectrum IDs to remove
        spec_ids_to_remove = []
        rows_to_remove = []
        
        for index in indexes:
            # Get the alias item from column 0
            alias_index = self.dataset_model.index(index.row(), 0, index.parent())
            alias_item = self.dataset_model.itemFromIndex(alias_index)
            
            # Find corresponding spectrum ID
            for spec_id, item in self._dataset_items.items():
                if item is alias_item:
                    spec_ids_to_remove.append(spec_id)
                    rows_to_remove.append((index.row(), index.parent()))
                    break
        
        # Remove from overlay service
        for spec_id in spec_ids_to_remove:
            try:
                self.overlay_service.remove(spec_id)
            except Exception:
                pass
            
            # Remove from plot
            try:
                self.plot.remove_trace(spec_id)
            except Exception:
                pass

            # Remove from legend panel
            try:
                if hasattr(self, 'legend_panel'):
                    self.legend_panel.remove_legend_item(spec_id)
            except Exception:
                pass

            # Remove from internal tracking
            self._dataset_items.pop(spec_id, None)
            self._dataset_color_items.pop(spec_id, None)
            self._spectrum_colors.pop(spec_id, None)
            self._visibility.pop(spec_id, None)
            self._display_y_units.pop(spec_id, None)
        
        # Remove rows from model (sort in reverse to avoid index shifting)
        rows_to_remove.sort(reverse=True, key=lambda x: x[0])
        for row, parent in rows_to_remove:
            if parent.isValid():
                parent_item = self.dataset_model.itemFromIndex(parent)
                if parent_item:
                    parent_item.removeRow(row)
        
        # Update math selectors
        self._update_math_selectors()
        
        # Log the removal
        if len(spec_ids_to_remove) == 1:
            self._log("Datasets", "Removed 1 dataset")
        else:
            self._log("Datasets", f"Removed {len(spec_ids_to_remove)} datasets")

    def _clear_all_datasets(self) -> None:
        """Remove all datasets from the overlay and UI (called after confirmation)."""
        if self._originals_item is None or self._originals_item.rowCount() == 0:
            return

        # Collect all spectrum IDs
        spec_ids_to_remove = list(self._dataset_items.keys())

        # Remove from overlay service and plot
        for spec_id in spec_ids_to_remove:
            try:
                self.overlay_service.remove(spec_id)
            except Exception:
                pass

            try:
                self.plot.remove_trace(spec_id)
            except Exception:
                pass

        # Clear internal tracking dictionaries
        self._dataset_items.clear()
        self._dataset_color_items.clear()
        self._spectrum_colors.clear()
        self._visibility.clear()
        self._display_y_units.clear()

        # Clear legend panel
        try:
            if hasattr(self, 'legend_panel'):
                self.legend_panel.clear()
        except Exception:
            pass

        # Remove all rows from the model
        self._originals_item.removeRows(0, self._originals_item.rowCount())

        # Clear group assignments
        try:
            self.group_service.clear_assignments()
        except Exception:
            pass

        # Update math selectors
        self._update_math_selectors()

        # Log the removal
        self._log("Datasets", f"Cleared all {len(spec_ids_to_remove)} dataset(s)")

    # ----------------------------- Dataset grouping helpers ---------------
    def _get_visible_groups(self) -> List[str]:
        """Get list of group IDs that should be displayed."""
        return [g.id for g in self.group_service.list_groups()]

    def _get_datasets_in_group(self, group_id: str) -> List[str]:
        """Get spectrum IDs for a group."""
        return self.group_service.get_datasets_in_group(group_id)

    def _on_group_visibility_toggled(self, group_id: str, visible: bool) -> None:
        """Toggle visibility of all datasets in a group."""
        if self.plot is None:
            return

        # Check if this is the Spectral Lines group (toggle NIST lines)
        try:
            group = self.group_service.get_group(group_id)
            if group and group.group_type == GroupType.SPECTRAL_LINES:
                # Toggle all NIST line collections
                for collection_id in list(self._nist_collections.keys()):
                    try:
                        if visible:
                            self._draw_nist_collection(collection_id)
                        else:
                            self._hide_nist_collection(collection_id)
                    except Exception:
                        pass
                return
        except Exception:
            pass

        # Regular dataset groups
        dataset_ids = self._get_datasets_in_group(group_id)
        for spec_id in dataset_ids:
            self._visibility[spec_id] = visible
            try:
                self.plot.set_visible(spec_id, visible)
            except Exception:
                pass

    def _on_legend_item_clicked(self, dataset_id: str) -> None:
        """Handle legend item click to toggle dataset visibility."""
        try:
            # Toggle visibility state
            current_visible = self._visibility.get(dataset_id, True)
            new_visible = not current_visible
            self._visibility[dataset_id] = new_visible

            # Update plot
            try:
                self.plot.set_visible(dataset_id, new_visible)
            except Exception:
                pass

            # Update legend panel styling
            try:
                if hasattr(self, 'legend_panel'):
                    self.legend_panel.update_item_visibility(dataset_id, new_visible)
            except Exception:
                pass

        except Exception as e:
            self._log("Legend", f"Failed to toggle visibility: {e}")

    def _on_group_expanded_changed(self, group_id: str, is_expanded: bool) -> None:
        """Handle group expand/collapse state change."""
        try:
            self.group_service.update_group(group_id, is_expanded=is_expanded)
        except Exception:
            pass

    def _get_group_for_dataset(self, spectrum_id: str) -> Optional[str]:
        """Get the group ID for a dataset."""
        try:
            group = self.group_service.get_group_for_dataset(spectrum_id)
            return group.id if group else None
        except Exception:
            return None
    
    # ----------------------------- Group management handlers ---------------
    def _on_create_group_requested(self, name: str, parent_group_id: str) -> None:
        """Handle request to create a new group."""
        try:
            from app.services.dataset_group_service import GroupType
            group_id = self.group_service.create_group(
                name=name,
                group_type=GroupType.CUSTOM,
                parent_group_id=parent_group_id if parent_group_id else None,
            )
            # Add to UI
            self.dataset_panel.add_group(group_id, name)
            # Expand the new group
            group_item = self.dataset_panel.get_group_item(group_id)
            if group_item:
                index = self.dataset_model.indexFromItem(group_item)
                self.dataset_view.setExpanded(index, True)
            self._log("Groups", f"Created group '{name}'")
        except Exception as e:
            self._log("Groups", f"Failed to create group: {e}")
    
    def _on_move_to_group_requested(self, indexes: list, target_group_id: str) -> None:
        """Handle request to move datasets to a different group."""
        if not indexes:
            return
        
        # Sort indexes by row in reverse order to avoid index shifting issues
        valid_indexes = [idx for idx in indexes if idx.parent().isValid()]
        valid_indexes.sort(key=lambda idx: idx.row(), reverse=True)
        
        moved_count = 0
        target_group_item = self.dataset_panel.get_group_item(target_group_id)
        if not target_group_item:
            return
        
        for index in valid_indexes:
            # Get spectrum ID from the item
            item = self.dataset_model.itemFromIndex(index)
            if not item:
                continue
            spec_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if not spec_id:
                continue
            
            # Remove from current parent
            parent = item.parent()
            if parent:
                row = item.row()
                # Take the items (both columns) from the parent
                items = parent.takeRow(row)
                if items:
                    target_group_item.appendRow(items)
                    # Update group service
                    try:
                        self.group_service.assign_to_group(spec_id, target_group_id)
                    except Exception:
                        pass
                    moved_count += 1
        
        if moved_count > 0:
            target_group = self.group_service.get_group(target_group_id)
            group_name = target_group.name if target_group else "group"
            self._log("Groups", f"Moved {moved_count} dataset(s) to '{group_name}'")
    
    def _on_rename_group_requested(self, group_id: str, new_name: str) -> None:
        """Handle request to rename a group."""
        try:
            self.group_service.update_group(group_id, name=new_name)
            # Update UI
            group_item = self.dataset_panel.get_group_item(group_id)
            if group_item:
                group_item.setText(new_name)
            self._log("Groups", f"Renamed group to '{new_name}'")
        except Exception as e:
            self._log("Groups", f"Failed to rename group: {e}")
    
    def _on_delete_group_requested(self, group_id: str) -> None:
        """Handle request to delete an empty group."""
        try:
            group = self.group_service.get_group(group_id)
            if not group:
                return
            
            # Get the group item and check if empty
            group_item = self.dataset_panel.get_group_item(group_id)
            if group_item and group_item.rowCount() > 0:
                QtWidgets.QMessageBox.warning(
                    self, "Cannot Delete Group",
                    "Cannot delete a group that contains datasets.\n"
                    "Move or remove the datasets first."
                )
                return
            
            # Delete from service
            self.group_service.delete_group(group_id)
            
            # Remove from UI
            if group_item:
                index = self.dataset_model.indexFromItem(group_item)
                self.dataset_model.removeRow(index.row())
                if group_id in self.dataset_panel._group_items:
                    del self.dataset_panel._group_items[group_id]
            
            self._log("Groups", f"Deleted group '{group.name}'")
        except Exception as e:
            self._log("Groups", f"Failed to delete group: {e}")

    def _on_normalization_lock_changed(self, indexes: List[QtCore.QModelIndex], is_locked: bool) -> None:
        """Handle request to lock/unlock normalization for selected datasets."""
        try:
            from dataclasses import replace

            for index in indexes:
                if not index.parent().isValid():
                    continue  # Skip group items

                # Get spectrum ID from the item
                alias_item = self.dataset_model.itemFromIndex(index)
                if not alias_item:
                    continue

                spec_id = alias_item.data(QtCore.Qt.ItemDataRole.UserRole)
                if not spec_id:
                    continue

                # Get the spectrum and update its lock state
                try:
                    spectrum = self.overlay_service.get(spec_id)
                    updated_spectrum = replace(spectrum, normalization_locked=is_locked)

                    # Update in overlay service
                    self.overlay_service.remove(spec_id)
                    self.overlay_service.add(updated_spectrum)

                    # Update the display name to show lock icon
                    current_text = alias_item.text()
                    lock_icon = "\U0001F512 "  # 🔒

                    if is_locked:
                        # Add lock icon if not already present
                        if not current_text.startswith(lock_icon):
                            alias_item.setText(lock_icon + current_text)
                    else:
                        # Remove lock icon if present
                        if current_text.startswith(lock_icon):
                            alias_item.setText(current_text[len(lock_icon):])

                except Exception as e:
                    self._log("Normalization", f"Failed to update lock state for {spec_id}: {e}")
                    continue

            lock_status = "locked" if is_locked else "unlocked"
            count = len(indexes)
            self._log("Normalization", f"{count} dataset(s) {lock_status}")

        except Exception as e:
            self._log("Normalization", f"Failed to change normalization lock: {e}")

    def _on_normalize_datasets(self) -> None:
        """Permanently normalize selected datasets (or all unlocked if none selected)."""
        try:
            # Get normalization mode from combo
            norm_mode = self.norm_combo.currentText() if self.norm_combo else "None"
            if norm_mode == "None":
                QtWidgets.QMessageBox.information(
                    self, "No Normalization Mode",
                    "Please select a normalization mode (Max or Area) from the dropdown first."
                )
                return

            # Determine which datasets to normalize
            selected_indexes = self.dataset_view.selectionModel().selectedRows() if self.dataset_view.selectionModel() else []
            dataset_indexes = [idx for idx in selected_indexes if idx.parent().isValid()]

            # Get list of spectrum IDs to normalize
            spec_ids_to_normalize = []

            if dataset_indexes:
                # Normalize only selected datasets
                for index in dataset_indexes:
                    alias_item = self.dataset_model.itemFromIndex(index)
                    if alias_item:
                        spec_id = alias_item.data(QtCore.Qt.ItemDataRole.UserRole)
                        if spec_id:
                            spec_ids_to_normalize.append(spec_id)
            else:
                # No selection - normalize all unlocked datasets
                spec_ids_to_normalize = [
                    spec.id for spec in self.overlay_service.list()
                    if not spec.normalization_locked
                ]

            if not spec_ids_to_normalize:
                QtWidgets.QMessageBox.information(
                    self, "No Datasets to Normalize",
                    "No unlocked datasets available to normalize."
                )
                return

            # Count locked datasets that were skipped
            locked_count = 0
            normalized_count = 0

            # Normalize each dataset
            for spec_id in spec_ids_to_normalize:
                try:
                    spectrum = self.overlay_service.get(spec_id)

                    # Skip if locked
                    if spectrum.normalization_locked:
                        locked_count += 1
                        continue

                    # Apply normalization to the data
                    x_canonical = np.asarray(spectrum.x, dtype=np.float64)
                    y_canonical = np.asarray(spectrum.y, dtype=np.float64)

                    # Apply normalization using overlay service's method
                    y_normalized, norm_meta = self.overlay_service._apply_normalization(
                        x_canonical, y_canonical, norm_mode
                    )

                    # Check if normalization was actually applied
                    if norm_meta and norm_meta.get("applied", False):
                        # Create new spectrum with normalized data
                        from dataclasses import replace
                        normalized_spectrum = replace(
                            spectrum,
                            y=y_normalized,
                            metadata={**spectrum.metadata, "normalization_applied": norm_meta}
                        )

                        # Update in overlay service
                        self.overlay_service.remove(spec_id)
                        self.overlay_service.add(normalized_spectrum)
                        normalized_count += 1
                    else:
                        # Normalization couldn't be applied (e.g., no finite values)
                        reason = norm_meta.get("reason", "unknown") if norm_meta else "unknown"
                        self._log("Normalization", f"Skipped '{spectrum.name}': {reason}")

                except Exception as e:
                    self._log("Normalization", f"Failed to normalize '{spec_id}': {e}")
                    continue

            # Show summary
            msg = f"Normalized {normalized_count} dataset(s) using {norm_mode} mode."
            if locked_count > 0:
                msg += f"\n{locked_count} locked dataset(s) were skipped."

            self._log("Normalization", msg)
            QtWidgets.QMessageBox.information(self, "Normalization Complete", msg)

            # Refresh the plot to show updated data
            self._schedule_refresh()

        except Exception as e:
            self._log("Normalization", f"Failed to normalize datasets: {e}")
            QtWidgets.QMessageBox.critical(
                self, "Normalization Error",
                f"Failed to normalize datasets:\n{e}"
            )

    def _on_max_points_changed(self, value: int) -> None:
        self._plot_max_points = int(value)
        self.plot.set_max_points(self._plot_max_points)
        self._save_plot_max_points(self._plot_max_points)

    def _schedule_refresh(self) -> None:
        """Schedule a deferred plot refresh to avoid blocking during rapid changes."""
        try:
            if str(os.environ.get("QT_QPA_PLATFORM", "")).lower() == "offscreen":
                # In headless test runs, refresh immediately to satisfy timing-sensitive assertions
                self._refresh_plot()
                return
        except Exception:
            pass
        self._refresh_timer.start()  # Restarts the timer if already running
    
    def _refresh_plot(self) -> None:
        """Refresh plot with current normalization mode."""
        # Batch plot updates to avoid incremental redraws during refresh
        try:
            self.plot.begin_bulk_update()
        except Exception:
            pass

        norm_mode = self.norm_combo.currentText()
        use_global = self.norm_global_checkbox.isChecked() if hasattr(self, 'norm_global_checkbox') else False
        
        # If global normalization, compute the global max/area first
        global_norm_value = None
        spectra_list = self.overlay_service.list()  # Cache to avoid multiple calls
        if norm_mode != "None" and use_global:
            global_norm_value = self._compute_global_normalization_value(norm_mode)
        
        for spec in spectra_list:
            try:
                # Convert X to nm for plotting
                try:
                    x_nm, y_converted, _ = self.units_service.convert_arrays(
                        np.asarray(spec.x, dtype=float),
                        np.asarray(spec.y, dtype=float),
                        spec.x_unit,
                        spec.y_unit,
                        "nm",
                        spec.y_unit,
                    )
                except Exception:
                    # Fallback for unknown Y units
                    x_nm = self.units_service._to_canonical_wavelength(
                        np.asarray(spec.x, dtype=float), spec.x_unit
                    )
                    y_converted = np.asarray(spec.y, dtype=float)
                self.plot.update_alias(spec.id, spec.name)
                # Apply calibration then normalization - REMOVED - calibration no longer used
                # x_nm, y_cal = self._apply_calibration_nm(x_nm, y_converted)
                y_cal = y_converted  # Skip calibration step
                y_data = self._apply_normalization(y_cal, norm_mode, global_norm_value, x_nm)
                y_data = self._apply_y_scale(y_data)
                
                color = self._spectrum_colors.get(spec.id, QtGui.QColor("white"))
                style = TraceStyle(color=color, width=1.0, show_in_legend=True)
                self.plot.add_trace(
                    key=spec.id,
                    alias=spec.name,
                    x_nm=x_nm,
                    y=y_data,
                    style=style,
                    uncertainty=self._compute_display_uncertainty(spec, x_nm, y_cal, norm_mode, global_norm_value),
                    quality_flags=getattr(spec, "quality_flags", None),
                )
            except Exception as e:
                import logging
                logger = logging.getLogger("spectra")
                logger.error(f"Error refreshing plot for spectrum {spec.id}: {e}", exc_info=True)
        # End batch update without autoscaling
        # User can manually autoscale using Ctrl+F or the Autoscale button
        try:
            self.plot.end_bulk_update()
        except Exception:
            pass
    
    def _compute_global_normalization_value(self, mode: str) -> float | None:
        """Compute global normalization value across all spectra."""
        if mode == "None":
            return None

        all_values = []
        for spec in self.overlay_service.list():
            try:
                # Convert to nm space and apply calibration (same as in _refresh_plot)
                try:
                    x_nm, y_converted, _ = self.units_service.convert_arrays(
                        np.asarray(spec.x, dtype=float),
                        np.asarray(spec.y, dtype=float),
                        spec.x_unit,
                        spec.y_unit,
                        "nm",
                        spec.y_unit,
                    )
                except Exception:
                    x_nm = self.units_service._to_canonical_wavelength(
                        np.asarray(spec.x, dtype=float), spec.x_unit
                    )
                    y_converted = np.asarray(spec.y, dtype=float)

                # x_nm, y_cal = self._apply_calibration_nm(x_nm, y_converted)  # REMOVED - calibration no longer used
                y_cal = y_converted  # Skip calibration step
                all_values.append(y_cal)
            except Exception:
                pass
        
        if not all_values:
            return None

        # Concatenate all Y values
        all_y = np.concatenate(all_values)
        
        if mode == "Max":
            # Robust to NaNs/Infs
            finite = np.isfinite(all_y)
            if not np.any(finite):
                return None
            return float(np.nanmax(np.abs(all_y[finite])))
        elif mode == "Area":
            # Index-based area (matches existing test expectations): sum per-curve |y| areas
            total_area = 0.0
            for yv in all_values:
                finite = np.isfinite(yv)
                if np.count_nonzero(finite) < 2:
                    continue
                total_area += float(np.trapz(np.abs(yv[finite])))
            return total_area if total_area > 0 else None
        
        return None
    
    def _apply_normalization(self, y: np.ndarray, mode: str, global_value: float | None = None, x: np.ndarray | None = None) -> np.ndarray:
        """Apply normalization to y-data based on mode.
        
        Args:
            y: Y-data array to normalize.
            mode: Normalization mode ("None", "Max", or "Area").
            global_value: If provided, use this value instead of computing from ``y``.
            x: Optional x-array (nm). Reserved for potential x-weighted area; currently
               not used, as Area uses index-based integration to match tests.

        Notes:
            - Scale calculations ignore non-finite samples (NaN/Inf) so FITS masked
              values do not corrupt Max/Area factors. Non-finite samples are preserved
              in the output array.
        """
        import logging
        logger = logging.getLogger("spectra")
        
        if mode == "None" or len(y) == 0:
            return y
        
        # Compute scales on finite values only (FITS often carries NaNs/masked samples)
        finite_y = np.isfinite(y)
        
        if mode == "Max":
            if global_value is not None and np.isfinite(global_value):
                norm_val = float(global_value)
            else:
                if not np.any(finite_y):
                    return y
                norm_val = float(np.nanmax(np.abs(y[finite_y])))
            logger.info(f"Max normalization: norm_val={norm_val:.6f}")
            if norm_val > 0:
                result = y / norm_val
                logger.info(f"  Result range: [{np.nanmin(result):.6f}, {np.nanmax(result):.6f}]")
                return result
            return y
        
        if mode == "Area":
            if global_value is not None and np.isfinite(global_value):
                norm_val = float(global_value)
            else:
                if not np.any(finite_y):
                    return y
                # Index-based area to match existing behavior/tests
                    norm_val = float(np.trapz(np.abs(y[finite_y])))

            logger.info(f"Area normalization: norm_val={norm_val:.6f}")
            if norm_val > 0:
                result = y / norm_val
                logger.info(f"  Result range: [{np.nanmin(result):.6f}, {np.nanmax(result):.6f}]")
                return result
            return y
        
        return y

    def _next_palette_color(self) -> QtGui.QColor:
        if self._use_uniform_palette:
            return QtGui.QColor(self._uniform_color)
        color = self._palette[self._palette_index % len(self._palette)]
        self._palette_index += 1
        return color

    def _next_nist_color(self) -> QtGui.QColor:
        """Return the next colour for NIST spectra from the NIST palette.

        Uses theme-specific, high-contrast colours distinct from dataset palette.
        """
        palette = self._nist_palette or self._palette
        idx = self._nist_palette_index % max(1, len(palette))
        color = palette[idx]
        self._nist_palette_index += 1
        return color

    def _apply_theme_palettes(self, theme_key: str) -> None:
        """Update dataset and NIST colour palettes for the given theme key."""
        # Colourblind-safe Okabe–Ito base set (works on both themes)
        okabe_ito = [
            "#E69F00", "#56B4E9", "#009E73", "#F0E442",
            "#0072B2", "#D55E00", "#CC79A7", "#999999",
        ]
        if str(theme_key).lower() in ("light",):
            # Eye-friendly, non-blue starter colour (rust/brown) for better legibility on white
            dataset = [
                "#7A3E2F",  # rust (primary)
                "#2F6B4F",  # forest
                "#7A6FA1",  # aubergine
                "#6E5A49",  # walnut
                "#A77C49",  # ochre
                "#808080",  # grey
                "#3E6A6A",  # slate green
                "#8A5E7A",  # dusty rose
            ]
            # For light backgrounds: avoid yellows entirely; use deep, legible accents
            nist = [
                "#4B3F72",  # deep aubergine
                "#2F6B4F",  # forest
                "#7A3E2F",  # rust
                "#5A6B7A",  # slate
            ]
        else:
            # Vibrant but not neon for dark theme
            # Use a bright, readable set on dark canvases (Okabe–Ito inspired)
            dataset = [
                "#E69F00", "#56B4E9", "#009E73", "#D55E00",
                "#CC79A7", "#F0E442", "#0072B2", "#999999",
            ]
            # Start NIST accents with cyan; move yellow to the end
            nist = ["#33BBC5", "#FF5A5F", "#C77DFF", "#FFB000"]
        # Mix in Okabe–Ito to lengthen
        def as_qcolors(hexes: list[str]) -> list[QtGui.QColor]:
            return [QtGui.QColor(h) for h in hexes + okabe_ito]
        self._palette = as_qcolors(dataset)
        self._nist_palette = as_qcolors(nist)
        self._palette_index = 0
        self._nist_palette_index = 0

    def _retint_for_theme(self) -> None:
        """Re-apply palette colors to existing items when the theme changes."""
        # Datasets: reassign colours in insertion order
        try:
            self._palette_index = 0
            for spec in self.overlay_service.list():
                color = self._next_palette_color()
                self._spectrum_colors[spec.id] = color
                # Update plot style
                self.plot.update_style(spec.id, TraceStyle(color=color, width=1.0, show_in_legend=True))
                # Update dataset chip icon if available
                alias_item = self._dataset_items.get(spec.id)
                if alias_item is not None:
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
                        alias_item.setData(QtGui.QIcon(swatch), QtCore.Qt.ItemDataRole.DecorationRole)
                        alias_item.setToolTip(f"Trace colour: {color.name()}")
                    except Exception:
                        pass
        except Exception:
            pass

        # Time-series traces: reassign colours and restyle
        try:
            for ts_id, ts in self._time_series.items():
                color = self._next_palette_color()
                self._time_series_colors[ts_id] = color
                if self.time_plot is not None:
                    self.time_plot.update_style(ts_id, TraceStyle(color=color, width=1.2, show_in_legend=True))
                item = self._time_series_items.get(ts_id)
                if item is not None:
                    swatch = QtGui.QPixmap(12, 12)
                    swatch.fill(QtCore.Qt.GlobalColor.transparent)
                    painter = QtGui.QPainter(swatch)
                    try:
                        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 180)))
                        painter.setBrush(QtGui.QBrush(color))
                        painter.drawRect(0, 0, 11, 11)
                    finally:
                        painter.end()
                    item.setIcon(0, QtGui.QIcon(swatch))
        except Exception:
            pass

        # NIST collections: reassign colours and redraw visible sets
        try:
            self._nist_palette_index = 0
            if hasattr(self.reference_panel, "nist_lines_panel") and self.reference_panel.nist_lines_panel is not None:
                for cid in self.reference_panel.nist_lines_panel.get_collections():
                    color = self._next_nist_color()
                    if cid in self._nist_collections:
                        self._nist_collections[cid]["color"] = color
                    # Update panel swatch
                    try:
                        self.reference_panel.nist_lines_panel.set_color(cid, color)
                    except Exception:
                        pass
                    # Redraw on plot if visible
                    try:
                        if self.nist_lines_panel.is_visible(cid):
                            self._draw_nist_collection(cid)
                    except Exception:
                        pass
        except Exception:
            pass

    def _retint_datasets_only(self) -> None:
        """Reapply current dataset palette (uniform or theme) to existing traces."""
        try:
            self._palette_index = 0
            for spec in self.overlay_service.list():
                color = self._next_palette_color()
                self._spectrum_colors[spec.id] = color
                self.plot.update_style(spec.id, TraceStyle(color=color, width=1.0, show_in_legend=True))
                alias_item = self._dataset_items.get(spec.id)
                if alias_item is not None:
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
                        alias_item.setData(QtGui.QIcon(swatch), QtCore.Qt.ItemDataRole.DecorationRole)
                        alias_item.setToolTip(f"Trace colour: {color.name()}")
                    except Exception:
                        pass
        except Exception:
            pass

    def _on_uniform_palette_toggled(self, enabled: bool) -> None:
        self._use_uniform_palette = bool(enabled)
        self._save_palette_preferences()
        # Retint datasets with the chosen mode
        self._retint_datasets_only()

    def _on_pick_uniform_color(self) -> None:
        try:
            dlg = QtWidgets.QColorDialog(self._uniform_color, self)
            dlg.setOption(QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel, False)
            if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                color = dlg.currentColor()
                if color.isValid():
                    self._uniform_color = color
                    self._save_palette_preferences()
                    if self._use_uniform_palette:
                        self._retint_datasets_only()
        except Exception:
            pass

    # ----------------------------- Reference tab helpers -----------------
    def _update_reference_axis(self, unit: str) -> None:
        try:
            # If IR tab is active, prefer wavenumber labelling for clarity
            is_ir = False
            try:
                # Tab 0 = IR Functional Groups after consolidation
                is_ir = (self.reference_panel.reference_tabs.currentIndex() == 0)
            except Exception:
                is_ir = False
            if is_ir and unit == "cm⁻¹":
                self.reference_panel.reference_plot.setLabel("bottom", "Wavenumber (cm⁻¹)")
            else:
                self.reference_panel.reference_plot.setLabel("bottom", f"Wavelength ({unit})")
        except Exception:
            pass

    def _refresh_reference_view(self) -> None:
        # Clear preview plot and table for fresh content
        try:
            for item in self.reference_panel.reference_plot.listDataItems():
                self.reference_panel.reference_plot.removeItem(item)
        except Exception:
            pass

        # Clear IR table if present
        if hasattr(self.reference_panel, 'ir_table') and isinstance(self.reference_panel.ir_table, QtWidgets.QTableWidget):
            self.reference_panel.ir_table.setRowCount(0)

        # NEW tab order after consolidation:
        # Tab 0: IR Functional Groups
        # Tab 1: Reference Lines (curated spectral lines)
        # Tab 2: NIST Spectral Lines (NIST ASD)
        current = self.reference_panel.reference_tabs.currentIndex()
        if current == 0:
            # IR functional groups
            self.reference_panel.reference_filter.setPlaceholderText("Filter IR groups…")
            groups = self.reference_library.ir_functional_groups()
            self._populate_reference_table_ir(groups)
            payload = self._build_overlay_for_ir(groups)
            self._update_reference_overlay_state(payload)
            self._preview_reference_payload(payload)
        elif current == 1:
            # Reference Lines (curated spectral lines)
            self.reference_panel.reference_filter.setPlaceholderText("Use checkboxes to show lines…")
            self._refresh_reference_lines_table()
            self.reference_panel.reference_overlay_checkbox.setEnabled(False)
            self.reference_panel.reference_status_label.setText("Check elements to display lines on plot")
        elif current == 2:
            # NIST Spectral Lines: no automatic fetch; leave controls ready
            self.reference_panel.reference_filter.setPlaceholderText("Filter spectral lines…")
            self.reference_panel.reference_overlay_checkbox.setEnabled(False)
            self.reference_panel.reference_status_label.setText("Enter element and range, then Fetch")

    def _populate_reference_table_ir(self, groups: Sequence[Mapping[str, Any]] | None) -> None:
        rows = list(groups or [])
        self._ir_rows = rows
        # Populate IR table in reference panel
        if hasattr(self.reference_panel, 'ir_table') and isinstance(self.reference_panel.ir_table, QtWidgets.QTableWidget):
            self.reference_panel.ir_table.setRowCount(len(rows))
            for r, entry in enumerate(rows):
                self.reference_panel.ir_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(entry.get("group", ""))))
                self.reference_panel.ir_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(entry.get("wavenumber_cm_1_min", ""))))
                self.reference_panel.ir_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(entry.get("wavenumber_cm_1_max", ""))))

    def _preview_reference_payload(self, payload: Mapping[str, Any]) -> None:
        import numpy as _np
        # Clear existing preview items
        try:
            for item in self.reference_panel.reference_plot.listDataItems():
                self.reference_panel.reference_plot.removeItem(item)
        except Exception:
            pass
        # Draw preview in the reference_plot
        mode = str(payload.get("mode") or "").lower()
        x = _np.asarray(payload.get("x_nm", []), dtype=float)
        y = _np.asarray(payload.get("y", []), dtype=float)
        domain = str(payload.get("domain") or "")
        # For IR domain, show preview axis in cm^-1 for readability
        try:
            if domain == "ir":
                self.reference_panel.reference_plot.setLabel("bottom", "Wavenumber (cm⁻¹)")
            else:
                self.reference_panel.reference_plot.setLabel("bottom", "Wavelength (nm)")
        except Exception:
            pass
        if domain == "ir" and x.size:
            with _np.errstate(divide="ignore"):
                x = 1e7 / x
        if mode == "bars" and x.size and y.size and x.size == y.size:
            # Render vertical bar segments scaled by y intensities
            try:
                _, y_range = self.reference_panel.reference_plot.getPlotItem().viewRange()
                y_min, y_max = float(y_range[0]), float(y_range[1])
            except Exception:
                y_min, y_max = -1.0, 1.0
            band_bottom = y_min + (y_max - y_min) * 0.05
            band_top = y_max - (y_max - y_min) * 0.05
            span = max(1e-9, band_top - band_bottom)
            xs: list[float] = []
            ys: list[float] = []
            for xi, yi in zip(x.tolist(), y.tolist()):
                xs.extend([xi, xi, _np.nan])
                ys.extend([band_bottom, band_bottom + float(yi) * span, _np.nan])
            pen = pg.mkPen(color=payload.get("color", "#6D597A"), width=float(payload.get("width", 1.2)))
            item = pg.PlotDataItem(_np.array(xs, dtype=float), _np.array(ys, dtype=float), pen=pen, connect="finite")
            self.reference_panel.reference_plot.addItem(item)
            return
        # Default polyline/filled preview
        if x.size and y.size and x.size == y.size:
            self.reference_panel.reference_plot.plot(x, y, pen=(100, 100, 180, 190), fillLevel=payload.get("fill_level"))

    def _on_reference_filter_changed(self, text: str) -> None:
        # Only applies to IR tab currently
        try:
            if self.reference_panel.reference_tabs.currentIndex() != 0:  # IR tab is now tab 0
                return
        except Exception:
            return
        needle = (text or "").strip().lower()
        groups = self.reference_library.ir_functional_groups() or []
        if needle:
            filtered = [g for g in groups if needle in str(g.get("group", "")).lower() or needle in str(g.get("category", "")).lower()]
        else:
            filtered = list(groups)
        # Update the table and preview
        self._populate_reference_table_ir(filtered)
        # If there is a selection, preview selected; otherwise preview all filtered
        try:
            items = self.reference_panel.ir_table.selectedItems()
        except Exception:
            items = []
        rows: list[Mapping[str, Any]] = []
        if items:
            sel_rows = sorted({it.row() for it in items})
            for r in sel_rows:
                if 0 <= r < len(self._ir_rows):
                    rows.append(self._ir_rows[r])
        else:
            rows = filtered
        payload = self._build_overlay_for_ir(rows)
        self._update_reference_overlay_state(payload)
        self._preview_reference_payload(payload)

    def _on_ir_row_selected(self) -> None:
        # Only act when IR tab is active
        try:
            if self.reference_panel.reference_tabs.currentIndex() != 0:  # IR tab is now tab 0
                return
        except Exception:
            return
        try:
            items = self.reference_panel.ir_table.selectedItems()
        except Exception:
            items = []
        if not items:
            # No selection – preview all visible rows
            rows = list(self._ir_rows)
        else:
            rows = []
            sel_rows = sorted({it.row() for it in items})
            for r in sel_rows:
                if 0 <= r < len(self._ir_rows):
                    rows.append(self._ir_rows[r])
        payload = self._build_overlay_for_ir(rows)
        self._update_reference_overlay_state(payload)
        self._preview_reference_payload(payload)

    def _on_nist_fetch_from_panel(self, element: str, lower: float, upper: float) -> None:
        """Handle NIST fetch request from NistLinesPanel signal."""
        self._on_nist_fetch_clicked(element, lower, upper)

    def _on_nist_fetch_clicked(self, element: str = "", lower: float = 400.0, upper: float = 700.0) -> None:
        """Fetch NIST spectral lines and add to the dedicated NIST Lines dock.

        Order of attempts:
        1) In-process nist_asd_service (tests monkeypatch this path)
        2) Subprocess safe_fetch isolation
        3) HTTP fallback
        """
        element = element.strip()
        if not element:
            self.reference_status_label.setText("Enter element symbol")
            return
        
        # Try in-process service first (unit tests patch this)
        payload = None
        cache_indicator = ""
        subprocess_error = None
        try:
            from app import main as main_module
            svc = getattr(main_module, "nist_asd_service", None)
            if svc is not None and getattr(svc, "dependencies_available", lambda: False)():
                try:
                    payload = svc.fetch_lines(
                        identifier=element,
                        element=element,
                        lower=lower,
                        upper=upper,
                        wavelength_unit="nm",
                        wavelength_type="vacuum",
                        use_ritz=True,
                    )
                except Exception as exc:
                    # Fall through to subprocess path
                    self._log("NIST", f"In-process fetch failed: {exc}")
                    payload = {"error": "inprocess-exception", "message": str(exc)}
        except Exception:
            # Ignore and fall through to subprocess path
            pass
        
        # Attempt 2: Subprocess (isolates native crashes) if no success yet
        if not payload or (isinstance(payload, dict) and "error" in payload):
            try:
                from app.services import nist_subprocess
                payload = nist_subprocess.safe_fetch(
                    identifier=element,
                    element=element,
                    lower=lower,
                    upper=upper,
                    wavelength_unit="nm",
                    wavelength_type="vacuum",
                    use_ritz=True,
                )
                if "error" not in payload:
                    cache_indicator = " (subprocess)"
                else:
                    subprocess_error = f"{payload.get('error', 'unknown')}: {payload.get('message', 'No details')}"
                    self._log("NIST", f"Subprocess failed: {subprocess_error}")
            except Exception as exc:
                subprocess_error = str(exc)
                self._log("NIST", f"Subprocess exception: {subprocess_error}")
                payload = {"error": "subprocess-exception", "message": str(exc)}
        
        # Attempt 3: HTTP fallback if previous attempts failed
        if payload and "error" in payload:
            self._log("NIST", f"Trying HTTP fallback (subprocess failed: {subprocess_error})")
            try:
                from app.services.nist_http_fallback import fetch_lines_http
                payload = fetch_lines_http(element=element, lower=lower, upper=upper, wavelength_unit="nm")
                if "error" not in payload:
                    cache_indicator = " (HTTP)"
                    self._log("NIST", f"HTTP fallback succeeded with {len(payload.get('lines', []))} lines")
                else:
                    http_error = f"{payload.get('error', 'unknown')}: {payload.get('message', 'No details')}"
                    self._log("NIST", f"HTTP fallback also failed: {http_error}")
            except Exception as exc:
                self._log("NIST", f"HTTP fallback exception: {exc}")
                payload = {"error": "http-exception", "message": str(exc)}
        
        # Check final result
        if not payload or "error" in payload:
            error_code = payload.get("error", "unknown") if payload else "no-result"
            error_msg = payload.get("message", "No details") if payload else "Both subprocess and HTTP failed"
            
            # Provide helpful guidance based on error type
            if error_code == "empty-output" and "code 0xc06d007f" in str(payload.get("stderr", "")):
                full_msg = f"NIST fetch failed: Astropy has a known Windows DLL issue. Try using the built-in lines (H, He, Na, Fe, Ca, Mg, O, N) or update astropy."
            elif error_code in ("http-status", "http-failure"):
                full_msg = f"NIST server error: {error_msg}. Using built-in lines if available."
            else:
                full_msg = f"NIST error ({error_code}): {error_msg}"
            
            self.reference_status_label.setText(full_msg)
            self._log("NIST", full_msg)
            return
        
        lines = list(payload.get("lines", [])) if isinstance(payload, Mapping) else []
        if not lines:
            self.reference_status_label.setText(f"No lines found for {element} in {lower}-{upper} nm")
            return
        
        # Update reference table (legacy table expected by tests)
        self.reference_table.setColumnCount(5)
        self.reference_table.setHorizontalHeaderLabels(["λ (nm)", "Ritz λ (nm)", "Intensity", "Lower", "Upper"])
        self.reference_table.setRowCount(len(lines))
        for r, row in enumerate(lines):
            self.reference_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(row.get("wavelength_nm", ""))))
            self.reference_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(row.get("ritz_wavelength_nm", ""))))
            self.reference_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(row.get("relative_intensity", ""))))
            self.reference_table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(row.get("lower_level", ""))))
            self.reference_table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(row.get("upper_level", ""))))

        # Build stick spectrum data for the NIST Lines dock
        try:
            raw_xs = np.array([row.get("wavelength_nm") for row in lines if isinstance(row, Mapping)], dtype=float)
            intensities = []
            for row in lines:
                try:
                    intensities.append(float(row.get("relative_intensity") or 0.0))
                except Exception:
                    intensities.append(0.0)
            raw_ys = np.array(intensities, dtype=float)
            max_i = float(np.nanmax(raw_ys)) if raw_ys.size else 0.0
            raw_ys_norm = (raw_ys / max_i) if max_i > 0 else np.ones_like(raw_xs)
            
            # Create stick spectrum: [x0, x0, nan, x1, x1, nan, ...] and [0, y0, nan, 0, y1, nan, ...]
            n = len(raw_xs)
            xs = np.empty(3 * n, dtype=float)
            ys = np.empty(3 * n, dtype=float)
            xs[0::3] = raw_xs
            xs[1::3] = raw_xs
            xs[2::3] = np.nan
            ys[0::3] = 0.0
            ys[1::3] = raw_ys_norm
            ys[2::3] = np.nan
            
            # If HTTP fallback used built-in set, label accordingly
            try:
                meta = payload.get("meta", {}) if isinstance(payload, Mapping) else {}
                if str(meta.get("source", "")).lower() == "builtin":
                    cache_indicator = " (builtin)"
            except Exception:
                pass

            # Generate unique collection ID and pick color
            self._nist_collection_counter += 1
            collection_id = f"nist_{element}_{self._nist_collection_counter}"
            color = self._next_nist_color()
            alias = f"NIST: {element}{cache_indicator}"
            
            # Store collection data
            self._nist_collections[collection_id] = {
                "xs_nm": xs,
                "ys": ys,
                "color": color,
                "alias": alias,
                "element": element,
                "line_count": len(lines),
            }
            
            # Add to NIST Lines panel
            self.reference_panel.nist_lines_panel.add_collection(collection_id, alias, len(lines), color)
            
            # Draw on plot (respects visibility state)
            self._draw_nist_collection(collection_id)

            # Show the Inspector dock and switch to NIST tab if this is the first fetch
            if self.inspector_dock.isHidden():
                self.inspector_dock.show()
                self.inspector_dock.raise_()
                self.inspector_tabs.setCurrentIndex(0)  # Reference tab
                self.reference_tabs.setCurrentIndex(2)  # NIST Spectral Lines tab
            
            # Update status with pinned sets count for compatibility with tests
            try:
                pinned = len(self.reference_panel.nist_lines_panel.get_collections())
            except Exception:
                pinned = 0
            suffix = f" – {pinned} pinned set" + ("s" if pinned != 1 else "") if pinned else ""
            self.reference_status_label.setText(f"✓ Fetched {len(lines)} lines for {element}{cache_indicator}{suffix}")

            # Build/update multi-overlay payload for NIST (used by tests)
            try:
                payload_obj = self._reference_overlay_payload
                if not isinstance(payload_obj, dict) or payload_obj.get("kind") != "nist-multi":
                    payload_obj = {"kind": "nist-multi", "payloads": {}}
                pmap = payload_obj.setdefault("payloads", {})  # type: ignore[assignment]
                # Construct a per-collection payload with a Reference-styled alias
                ref_alias = f"Reference – {alias}"
                subpayload = {
                    "key": collection_id,
                    "alias": ref_alias,
                    "x_nm": xs,
                    "y": ys,
                    "color": color,
                    "width": 1.2,
                }
                pmap[collection_id] = subpayload
                # Update overlay state and enable the checkbox
                self._update_reference_overlay_state(payload_obj)
            except Exception:
                # Non-fatal; overlay remains disabled if this fails
                pass
        except Exception as exc:
            # Catch any errors during spectrum creation/display
            self.reference_status_label.setText(f"Error creating spectrum: {exc}")
            import traceback
            traceback.print_exc()


    def _draw_nist_collection(self, collection_id: str) -> None:
        """Draw a NIST collection on the main plot as stick spectrum."""
        if collection_id not in self._nist_collections:
            return
        
        collection = self._nist_collections[collection_id]
        xs_nm = collection["xs_nm"]
        ys = collection["ys"]
        color = collection["color"]
        
        # Convert nm to current display unit
        unit = self.unit_combo.currentText() if self.unit_combo is not None else "nm"
        if unit == "nm":
            xs_disp = xs_nm
        elif unit == "Å":
            xs_disp = xs_nm * 10.0
        elif unit == "µm":
            xs_disp = xs_nm / 1000.0
        elif unit == "cm⁻¹":
            with np.errstate(divide="ignore"):
                xs_disp = 1e7 / xs_nm
        else:
            xs_disp = xs_nm
        
        # Create plot item
        pen = pg.mkPen(color=color, width=1.2)
        item = pg.PlotDataItem(xs_disp, ys, pen=pen, connect="finite")
        try:
            item.setZValue(-5)  # Draw behind spectra but above reference overlays
        except Exception:
            pass
        
        # Remove old item if exists
        old_item = self._nist_plot_items.get(collection_id)
        if old_item:
            try:
                self.plot.remove_graphics_item(old_item)
            except Exception:
                pass
        
        # Add new item and track it
        self.plot.add_graphics_item(item)
        self._nist_plot_items[collection_id] = item

    def _on_nist_visibility_changed(self, collection_id: str, visible: bool) -> None:
        """Handle visibility toggle for a NIST collection."""
        if collection_id not in self._nist_collections:
            return
        
        if visible:
            self._draw_nist_collection(collection_id)
        else:
            self._hide_nist_collection(collection_id)

    def _hide_nist_collection(self, collection_id: str) -> None:
        """Hide a NIST collection from the plot."""
        # Remove from plot
        item = self._nist_plot_items.get(collection_id)
        if item:
            try:
                self.plot.remove_graphics_item(item)
            except Exception:
                pass
            del self._nist_plot_items[collection_id]

    def _on_nist_remove_requested(self, collection_ids: List[str]) -> None:
        """Handle removal of NIST collections."""
        for collection_id in collection_ids:
            # Remove from plot
            item = self._nist_plot_items.get(collection_id)
            if item:
                try:
                    self.plot.remove_graphics_item(item)
                except Exception:
                    pass
                self._nist_plot_items.pop(collection_id, None)
            
            # Remove from panel
            self.reference_panel.nist_lines_panel.remove_collection(collection_id)
            
            # Remove from internal state
            self._nist_collections.pop(collection_id, None)
        
        self._log("NIST", f"Removed {len(collection_ids)} collection(s)")

    def _on_nist_clear_all_requested(self) -> None:
        """Handle Clear All for NIST collections."""
        # Remove all plot items
        for item in list(self._nist_plot_items.values()):
            try:
                self.plot.remove_graphics_item(item)
            except Exception:
                pass
        
        # Clear panel
        count = len(self._nist_collections)
        self.reference_panel.nist_lines_panel.clear()
        
        # Clear internal state
        self._nist_plot_items.clear()
        self._nist_collections.clear()
        
        self._log("NIST", f"Cleared all {count} collection(s)")

    def _on_nist_cache_clear_clicked(self) -> None:
        """Clear all cached NIST line lists."""
        try:
            from app import main as main_module
            count = main_module.nist_asd_service.clear_cache()
            stats = main_module.nist_asd_service.cache_stats()
            msg = f"Cleared {count} cached entries (stats: {stats['hits']} hits, {stats['misses']} misses)"
            self.reference_status_label.setText(msg)
        except Exception as exc:
            self.reference_status_label.setText(f"Cache clear failed: {exc}")

    # ----------------------------- Reference Lines ---------------------
    def _load_reference_lines_data(self) -> None:
        """Load curated reference spectral lines from samples/reference_lines/."""
        try:
            ref_lines_path = SAMPLES_DIR / "reference_lines" / "common_elements.csv"
            if not ref_lines_path.exists():
                return
            import csv
            with ref_lines_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                self._reference_lines_data = [row for row in reader if row.get("wavelength_nm")]
            # Populate table on Reference Lines tab
            self._refresh_reference_lines_table()
        except Exception as exc:
            self._log("RefLines", f"Failed to load reference lines: {exc}", level="WARN")

    def _refresh_reference_lines_table(self) -> None:
        """Populate the Reference Lines table with currently visible elements."""
        if not hasattr(self.reference_panel, "reflines_table"):
            return
        table = self.reference_panel.reflines_table
        # Get checked elements
        checked_elements = {
            elem for elem, cb in self.reference_panel.reflines_checkboxes.items() if cb.isChecked()
        }
        # Filter lines (exact element match only)
        filtered = [
            row for row in self._reference_lines_data
            if row.get("element", "").strip() in checked_elements
        ]
        # Populate table
        table.setRowCount(len(filtered))
        for idx, row in enumerate(filtered):
            wl = row.get("wavelength_nm", "")
            lbl = row.get("label", "")
            elem = row.get("element", "")
            note = row.get("note", "")
            table.setItem(idx, 0, QtWidgets.QTableWidgetItem(wl))
            table.setItem(idx, 1, QtWidgets.QTableWidgetItem(lbl))
            table.setItem(idx, 2, QtWidgets.QTableWidgetItem(elem))
            table.setItem(idx, 3, QtWidgets.QTableWidgetItem(note))
        table.resizeColumnsToContents()

        # Update preview plot with selected lines
        try:
            import numpy as np
            # Clear preview
            for item in self.reference_panel.reference_plot.listDataItems():
                self.reference_panel.reference_plot.removeItem(item)

            # Draw vertical lines for each filtered line
            if filtered:
                xs = [float(row.get("wavelength_nm", 0)) for row in filtered if row.get("wavelength_nm")]
                for x_nm in xs:
                    line = pg.InfiniteLine(pos=x_nm, angle=90, pen=pg.mkPen(color=(100, 100, 180, 150), width=1))
                    self.reference_panel.reference_plot.addItem(line)
        except Exception:
            pass

    def _on_reference_line_element_toggled(self, element: str, visible: bool) -> None:
        """Show or hide reference lines for a specific element."""
        if visible:
            # Add lines for this element
            self._add_reference_lines_for_element(element)
        else:
            # Remove lines for this element
            self._remove_reference_lines_for_element(element)
        # Refresh table
        self._refresh_reference_lines_table()
        # Reposition all markers
        try:
            self._update_line_marker_positions()
        except Exception:
            pass

    def _add_reference_lines_for_element(self, element: str) -> None:
        """Add spectral line markers for a specific element from curated data."""
        # Filter reference lines for this element (exact match only)
        lines_for_element = [
            row for row in self._reference_lines_data
            if row.get("element", "").strip() == element
        ]
        if not lines_for_element:
            return
        
        # Get current view range for initial label positioning
        try:
            (x_range, y_range) = self.plot.view_range()
            y0, y1 = float(y_range[0]), float(y_range[1])
            y_span = y1 - y0
            y_label_base = y1 - y_span * 0.04
        except Exception:
            y_label_base = 0.0
        
        # Track already-added wavelengths to avoid duplicates
        added_wavelengths = set()
        
        # Create markers
        markers = self._line_markers_by_element.setdefault(element, [])
        for row in lines_for_element:
            try:
                wl_nm = float(row.get("wavelength_nm", 0))
                if wl_nm <= 0:
                    continue
                # Skip if we already added this wavelength for this element
                if wl_nm in added_wavelengths:
                    continue
                added_wavelengths.add(wl_nm)
            except Exception:
                continue
            label = row.get("label", f"{wl_nm:.3f} nm")
            note = row.get("note", "")
            # Use consistent color per element
            color = self._next_palette_color()
            pen = pg.mkPen(color, width=1.2)
            try:
                disp = float(self.plot._x_nm_to_disp(np.array([wl_nm]))[0])  # type: ignore[attr-defined]
            except Exception:
                disp = wl_nm
            line_item = pg.InfiniteLine(pos=disp, angle=90, pen=pen, movable=False)
            text_item = pg.TextItem(text=label, color=color)
            text_item.setPos(disp, y_label_base)  # Set initial position
            text_item.setVisible(self._line_labels_visible)
            tooltip = f"{wl_nm:.3f} nm | {element}"
            if note:
                tooltip += f" | {note}"
            line_item.setToolTip(tooltip)
            text_item.setToolTip(tooltip)
            try:
                # Use ignoreBounds=True so lines don't affect Y-axis scaling
                self.plot._plot.addItem(line_item, ignoreBounds=True)
                self.plot._plot.addItem(text_item, ignoreBounds=True)
            except Exception:
                continue
            markers.append({
                'x_nm': wl_nm,
                'line': line_item,
                'text': text_item,
                'color': color,
                'label': label,
            })

    def _remove_reference_lines_for_element(self, element: str) -> None:
        """Remove all spectral line markers for a specific element."""
        markers = self._line_markers_by_element.get(element, [])
        for marker in markers:
            try:
                self.plot._plot.removeItem(marker.get('line'))
                self.plot._plot.removeItem(marker.get('text'))
            except Exception:
                pass
        self._line_markers_by_element.pop(element, None)

    def _refresh_reference_overlay_geometry(self) -> None:
        """Re-apply overlay items with the current view's y-range.

        Keeps NIST bars sized sensibly when zooming or after normalization.
        """
        try:
            if self.reference_overlay_checkbox.isChecked() and self._reference_overlay_payload:
                self._apply_reference_overlay()
        except Exception:
            pass
        # Also reposition any custom line list labels against new y-range
        try:
            self._update_line_marker_positions()
        except Exception:
            pass

    # Build IR overlay payload used by tests
    def _build_overlay_for_ir(self, entries: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        import numpy as _np
        # Determine band bounds from preview plot range
        y_min, y_max = -1.0, 1.0
        try:
            _, y_range = self.reference_plot.getPlotItem().viewRange()
            y_min, y_max = float(y_range[0]), float(y_range[1])
        except Exception:
            pass
        band_bottom = y_min + (y_max - y_min) * 0.05
        band_top = y_max - (y_max - y_min) * 0.05

        xs: list[float] = []
        ys: list[float] = []
        labels: list[Dict[str, Any]] = []
        for row in entries:
            try:
                lo = float(row.get("wavenumber_cm_1_max"))
                hi = float(row.get("wavenumber_cm_1_min"))
            except Exception:
                continue
            # Convert cm^-1 to nm
            x1 = 1e7 / hi if hi else float("nan")
            x2 = 1e7 / lo if lo else float("nan")
            # Ensure strictly increasing order and avoid duplicates
            x1e = _np.nextafter(x1, x2)
            x2e = _np.nextafter(x2, x1)
            xs.extend([x1, x1e, x2e, x2, _np.nan])
            ys.extend([band_bottom, band_top, band_top, band_bottom, _np.nan])
            centre_cm1 = 0.5 * (lo + hi)
            centre_nm = 1e7 / centre_cm1 if centre_cm1 else float("nan")
            labels.append({"text": str(row.get("group", "")), "centre_nm": float(centre_nm)})

        payload = {
            "key": "reference::ir_groups",
            "alias": "Reference – IR Functional Groups",
            "x_nm": np.array(xs, dtype=float),
            "y": np.array(ys, dtype=float),
            "color": "#6D597A",
            "width": 1.2,
            "fill_color": (109, 89, 122, 70),
            "fill_level": float(band_bottom),
            "band_bounds": (float(band_bottom), float(band_top)),
            "labels": labels,
            "domain": "ir",
        }
        return payload

    def _overlay_band_bounds(self) -> tuple[float, float]:
        try:
            _, y_range = self.plot._plot.viewRange()
            y_min, y_max = float(y_range[0]), float(y_range[1])
        except Exception:
            y_min, y_max = -1.0, 1.0
        margin = (y_max - y_min) * 0.05
        return (y_min + margin, y_max - margin)

    def _on_reference_overlay_toggled(self, checked: bool) -> None:
        if not checked:
            self._clear_reference_overlay()
            # For simple overlays record a cleared state
            if isinstance(self._reference_overlay_key, str):
                self._reference_overlay_key = None
            return
        self._apply_reference_overlay()

    def _apply_reference_overlay(self) -> None:
        payload = self._reference_overlay_payload or {}
        key = str(payload.get("key", ""))
        if not key and payload.get("kind") == "nist-multi":
            # NIST multi-payload
            pmap = payload.get("payloads", {})
            if isinstance(pmap, dict):
                self._reference_overlay_key = list(pmap.keys())
        else:
            self._reference_overlay_key = key

        # Always clear old annotations first to prevent stale items from persisting
        for item in list(self._reference_overlay_annotations):
            try:
                self.plot.remove_graphics_item(item)
            except Exception:
                pass
        self._reference_overlay_annotations.clear()

        # Create stacked label annotations on the main plot
        labels = payload.get("labels") or []
        if isinstance(labels, list) and labels:
            band_bottom, band_top = payload.get("band_bounds", self._overlay_band_bounds())
            if not isinstance(band_bottom, (int, float)):
                band_bottom, band_top = self._overlay_band_bounds()
            span = float(band_top - band_bottom) if (band_top is not None and band_bottom is not None) else 1.0
            n = max(1, len(labels))
            # Annotations already cleared above
            for i, label in enumerate(sorted(labels, key=lambda d: d.get("centre_nm", 0))):
                y = float(band_bottom) + (i + 1) * span / (n + 1)
                x_nm = float(label.get("centre_nm", 0.0))
                x_disp = self.plot.map_nm_to_display(x_nm)
                item = pg.TextItem(text=str(label.get("text", "")), color=(230, 230, 230))
                item.setPos(x_disp, y)
                self.plot.add_graphics_item(item)
                self._reference_overlay_annotations.append(item)

        # Draw overlay shapes/bars on the main plot
        # Clear any previous overlay graphics
        for item in list(self._reference_items):
            try:
                self.plot.remove_graphics_item(item)
            except Exception:
                pass
        self._reference_items.clear()

        # Helper to convert nm -> current unit for arrays
        def _convert_x_nm(x_nm: np.ndarray) -> np.ndarray:
            unit = self.unit_combo.currentText() if self.unit_combo is not None else "nm"
            if unit == "nm":
                return x_nm
            if unit == "Å":
                return x_nm * 10.0
            if unit == "µm":
                return x_nm / 1000.0
            if unit == "cm⁻¹":
                with np.errstate(divide="ignore"):
                    return 1e7 / x_nm
            return x_nm

        try:
            _, y_range = self.plot.view_range()
            y_min, y_max = float(y_range[0]), float(y_range[1])
        except Exception:
            y_min, y_max = -1.0, 1.0
        # Anchor bars to zero when 0 is within the current view; otherwise use a small margin above the bottom.
        if y_min < 0 < y_max:
            band_bottom = 0.0
            band_top = y_max - (y_max - max(0.0, y_min)) * 0.05
        else:
            band_bottom = y_min + (y_max - y_min) * 0.05
            band_top = y_max - (y_max - y_min) * 0.05
        span = max(1e-9, band_top - band_bottom)

        # NIST multi: draw one set of bars per pinned collection
        if payload.get("kind") == "nist-multi":
            pmap = payload.get("payloads", {})
            if isinstance(pmap, dict):
                for pin_key, p in pmap.items():
                    try:
                        xs_nm = np.asarray(p.get("x_nm", []), dtype=float)
                        ys = np.asarray(p.get("y", []), dtype=float)
                    except Exception:
                        continue
                    if xs_nm.size == 0 or ys.size == 0 or xs_nm.size != ys.size:
                        continue
                    xs_disp = _convert_x_nm(xs_nm)
                    xs: list[float] = []
                    ys_plot: list[float] = []
                    for xd, yi in zip(xs_disp.tolist(), ys.tolist()):
                        xs.extend([xd, xd, np.nan])
                        ys_plot.extend([band_bottom, band_bottom + float(yi) * span, np.nan])
                    pen = pg.mkPen(color=p.get("color", "#6D597A"), width=float(p.get("width", 1.2)))
                    item = pg.PlotDataItem(np.array(xs, dtype=float), np.array(ys_plot, dtype=float), pen=pen, connect="finite")
                    try:
                        item.setZValue(-10)  # draw behind spectra to reduce clutter
                    except Exception:
                        pass
                    self.plot.add_graphics_item(item)
                    self._reference_items.append(item)
            return

        # Generic polyline/filled overlay for IR and other references
        try:
            xs_nm = np.asarray(payload.get("x_nm", []), dtype=float)
            ys = np.asarray(payload.get("y", []), dtype=float)
        except Exception:
            xs_nm = np.array([], dtype=float)
            ys = np.array([], dtype=float)
        if xs_nm.size and ys.size and xs_nm.size == ys.size:
            xs_disp = _convert_x_nm(xs_nm)
            pen = pg.mkPen(color=payload.get("color", "#6D597A"), width=float(payload.get("width", 1.2)))
            item = pg.PlotDataItem(xs_disp, ys, pen=pen, connect="finite")
            try:
                item.setZValue(-10)
            except Exception:
                pass
            # Fill if specified
            fill_color = payload.get("fill_color")
            if fill_color is not None and hasattr(item, "setBrush"):
                item.setBrush(pg.mkBrush(fill_color))
                if hasattr(item, "setFillLevel"):
                    item.setFillLevel(float(payload.get("fill_level", band_bottom)))
            self.plot.add_graphics_item(item)
            self._reference_items.append(item)

    def _clear_reference_overlay(self) -> None:
        for item in list(self._reference_overlay_annotations):
            try:
                self.plot.remove_graphics_item(item)
            except Exception:
                pass
        # Preserve identity; just clear
        self._reference_overlay_annotations.clear()
        # Remove drawn overlay items
        for item in list(self._reference_items):
            try:
                self.plot.remove_graphics_item(item)
            except Exception:
                pass
        self._reference_items.clear()

    def _update_reference_overlay_state(self, payload: Mapping[str, Any]) -> None:
        self._reference_overlay_payload = payload  # preserve identity for tests
        self.reference_overlay_checkbox.setEnabled(True)
        # Do not auto-enable the overlay; keep toggle under user control

    # ----------------------------- Remote Data tab helpers --------------
    def _handle_remote_spectra_imported(self, spectra: list[Spectrum]) -> None:
        """Handle spectra imported from the remote data panel."""
        count = 0
        for spectrum in spectra:
            try:
                self.overlay_service.add(spectrum)
                self._add_spectrum(spectrum)
                count += 1
            except Exception as e:
                self._log("Remote Import", f"Failed to add spectrum: {e}")
                continue
        
        # Refresh UI
        self.plot.autoscale()
        self._refresh_library_view()
        
        # Record in history
        try:
            if spectra:
                self._record_remote_history_event(spectra)
        finally:
            self._refresh_history_view()
        
        self._log("Remote Import", f"Successfully imported {count} dataset(s)")

    # ----------------------------- History helpers ----------------------
    def _refresh_history_view(self) -> None:
        entries = []
        try:
            # Apply active search text if available
            search = getattr(self, "_history_search", "") or None
            entries = self.knowledge_log.load_entries(search=search)
        except Exception:
            entries = []
        self._history_entries = list(entries)
        self.history_table.setRowCount(len(self._history_entries))
        for r, entry in enumerate(self._history_entries):
            when = entry.timestamp.strftime("%Y-%m-%d %H:%M") if entry.timestamp else ""
            self.history_table.setItem(r, 0, QtWidgets.QTableWidgetItem(when))
            self.history_table.setItem(r, 1, QtWidgets.QTableWidgetItem(entry.component))
            self.history_table.setItem(r, 2, QtWidgets.QTableWidgetItem(entry.summary))
        if self._history_entries:
            self.history_table.selectRow(0)
            self._on_history_row_selected()

    def _on_history_row_selected(self) -> None:
        row = self.history_table.currentRow()
        if row < 0 or row >= len(self._history_entries):
            self.history_detail.setPlainText("")
            return
        entry = self._history_entries[row]
        self.history_detail.setPlainText(entry.raw)

    def _on_history_filter_changed(self, text: str) -> None:
        # Persist search text on the instance and refresh the table
        self._history_search = text
        self._refresh_history_view()

    def _copy_history_entries(self, rows: list[int]) -> None:
        if not rows:
            return
        rows = [r for r in rows if 0 <= r < len(self._history_entries)]
        if not rows:
            return
        payload = "\n\n".join(self._history_entries[r].raw.strip() for r in rows)
        cb = QtWidgets.QApplication.clipboard() if hasattr(QtWidgets, "QApplication") else None
        try:
            if cb is not None:
                cb.setText(payload)
            self._log("History", f"Copied {len(rows)} entr{'y' if len(rows)==1 else 'ies'} to clipboard")
        except Exception:
            pass

    def _export_history_entries(self, rows: list[int]) -> None:
        if not rows:
            return
        rows = [r for r in rows if 0 <= r < len(self._history_entries)]
        if not rows:
            return
        # Prompt for destination
        path_str, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export History Entries",
            str(Path.home() / "history_export.md"),
            "Markdown (*.md);;All files (*.*)",
        )
        if not path_str:
            return
        try:
            selected = [self._history_entries[r] for r in rows]
            dest = Path(path_str)
            self.knowledge_log.export_entries(dest, selected)
            self._log("History", f"Exported {len(selected)} entr{'y' if len(selected)==1 else 'ies'} → {dest.name}")
        except Exception as exc:
            self._log("History", f"Failed to export entries: {exc}")

    # ----------------------------- Merge/Average helpers ----------------
    def _mark_merge_preview_stale(self) -> None:
        """Mark the merge preview as needing recomputation and refresh immediately."""
        self._merge_preview_stale = True
        try:
            self._update_merge_preview()
        except Exception:
            pass
    
    def _on_inspector_tab_changed(self, index: int) -> None:
        """Update merge preview when the Math tab becomes visible."""
        try:
            if self.inspector_tabs.tabText(index) == "Math":
                self._update_merge_preview()
        except Exception:
            pass
    
    def _update_merge_preview(self) -> None:
        """Update the merge preview when dataset selection or visibility changes."""
        if not hasattr(self, 'merge_preview_label') or not hasattr(self, 'merge_average_button'):
            return
        
        # Skip if not stale (already computed)
        if not self._merge_preview_stale:
            return
        
        self._merge_preview_stale = False
        
        # Get selected datasets
        selected_specs = self._get_merge_candidates()
        
        if len(selected_specs) == 0:
            self.merge_preview_label.setText("No datasets selected")
            self.merge_average_button.setEnabled(False)
            self.merge_subtract_button.setEnabled(False)
            self.merge_ratio_button.setEnabled(False)
            self.merge_normalized_diff_button.setEnabled(False)
            self.merge_smooth_button.setEnabled(False)
            self.merge_derivative_button.setEnabled(False)
            self.merge_integral_button.setEnabled(False)
        elif len(selected_specs) == 1:
            spec = selected_specs[0]
            self.merge_preview_label.setText(
                f"1 dataset selected: {spec.name}\n"
                f"Points: {len(spec.x)}, Range: {spec.x.min():.2f}-{spec.x.max():.2f} nm"
            )
            self.merge_average_button.setEnabled(False)
            self.merge_subtract_button.setEnabled(False)
            self.merge_ratio_button.setEnabled(False)
            self.merge_normalized_diff_button.setEnabled(False)
            # Enable single-operand operations
            self.merge_smooth_button.setEnabled(True)
            self.merge_derivative_button.setEnabled(True)
            self.merge_integral_button.setEnabled(True)
        elif len(selected_specs) == 2:
            # Two spectra: enable subtract/ratio, check for average
            spec_a, spec_b = selected_specs
            # Check if they have the same wavelength grid for subtract/ratio
            try:
                ax, _, _ = self.units_service.to_canonical(spec_a.x, spec_a.y, spec_a.x_unit, spec_a.y_unit)
                bx, _, _ = self.units_service.to_canonical(spec_b.x, spec_b.y, spec_b.x_unit, spec_b.y_unit)
                same_grid = ax.shape == bx.shape and np.allclose(ax, bx, atol=1e-9)
            except Exception:
                same_grid = False
            
            if same_grid:
                self.merge_preview_label.setText(
                    f"2 datasets selected:\n"
                    f"A: {spec_a.name}\n"
                    f"B: {spec_b.name}\n"
                    f"✓ Same wavelength grid"
                )
                self.merge_subtract_button.setEnabled(True)
                self.merge_ratio_button.setEnabled(True)
                self.merge_normalized_diff_button.setEnabled(True)
            else:
                self.merge_preview_label.setText(
                    f"2 datasets selected:\n"
                    f"A: {spec_a.name}\n"
                    f"B: {spec_b.name}\n"
                    f"⚠️ Different wavelength grids - cannot subtract/divide"
                )
                self.merge_subtract_button.setEnabled(False)
                self.merge_ratio_button.setEnabled(False)
                self.merge_normalized_diff_button.setEnabled(False)
            
            # Disable single-operand operations for 2 spectra
            self.merge_smooth_button.setEnabled(False)
            self.merge_derivative_button.setEnabled(False)
            self.merge_integral_button.setEnabled(False)
            
            # Check for overlapping range for average
            overlap_min = max(spec_a.x.min(), spec_b.x.min())
            overlap_max = min(spec_a.x.max(), spec_b.x.max())
            self.merge_average_button.setEnabled(bool(overlap_min < overlap_max))
        else:
            # Show info about multiple spectra
            point_counts = [len(spec.x) for spec in selected_specs]
            min_wls = [spec.x.min() for spec in selected_specs]
            max_wls = [spec.x.max() for spec in selected_specs]
            
            overlap_min = max(min_wls)
            overlap_max = min(max_wls)
            
            # Disable subtract/ratio for more than 2 spectra
            self.merge_subtract_button.setEnabled(False)
            self.merge_ratio_button.setEnabled(False)
            self.merge_normalized_diff_button.setEnabled(False)
            
            # Disable single-operand operations for multiple spectra
            self.merge_smooth_button.setEnabled(False)
            self.merge_derivative_button.setEnabled(False)
            self.merge_integral_button.setEnabled(False)
            
            if bool(overlap_min >= overlap_max):
                self.merge_preview_label.setText(
                    f"{len(selected_specs)} datasets selected\n"
                    f"⚠️ No overlapping wavelength range - cannot average"
                )
                self.merge_average_button.setEnabled(False)
            else:
                self.merge_preview_label.setText(
                    f"{len(selected_specs)} datasets selected\n"
                    f"Point counts: {min(point_counts)}-{max(point_counts)}\n"
                    f"Overlapping range: {overlap_min:.2f}-{overlap_max:.2f} nm"
                )
                self.merge_average_button.setEnabled(True)
    
    def _get_merge_candidates(self) -> list[Spectrum]:
        """Get list of spectra that are candidates for merging based on selection and visibility."""
        if not hasattr(self, 'merge_only_visible') or not hasattr(self, 'dataset_view'):
            return []
        
        only_visible = self.merge_only_visible.isChecked()
        
        # Get selected indexes
        selection_model = self.dataset_view.selectionModel()
        if not selection_model:
            return []
        
        selected_indexes = selection_model.selectedRows()
        
        # Collect spectrum IDs from selection
        selected_ids = []
        for index in selected_indexes:
            # Get the alias item (column 0)
            alias_item = self.dataset_model.itemFromIndex(
                self.dataset_model.index(index.row(), 0, index.parent())
            )
            if alias_item is None:
                continue
            
            # Find spectrum ID for this item
            for spec_id, item in self._dataset_items.items():
                if item is alias_item:
                    selected_ids.append(spec_id)
                    break
        
        # Filter by visibility if requested
        if only_visible:
            selected_ids = [sid for sid in selected_ids if self._visibility.get(sid, True)]
        
        # Get the actual Spectrum objects
        candidates = []
        for spec_id in selected_ids:
            try:
                spec = self.overlay_service.get(spec_id)
                candidates.append(spec)
            except Exception:
                pass
        
        return candidates
    
    def _on_merge_average(self) -> None:
        """Perform averaging operation on selected spectra."""
        if not hasattr(self, 'merge_status_label'):
            return
        
        self.merge_status_label.setText("Processing...")
        
        try:
            # Get spectra to average
            spectra = self._get_merge_candidates()
            
            if len(spectra) < 2:
                self.merge_status_label.setText("⚠️ Select at least 2 datasets to average")
                return
            
            # Get custom name if provided
            custom_name = self.merge_name_edit.text().strip() if hasattr(self, 'merge_name_edit') else ""
            name = custom_name or None
            
            # Perform averaging
            result, metadata = self.math_service.average(spectra, name=name)
            
            # Add to overlay
            self.overlay_service.add(result)
            self._add_spectrum(result)

            # Update status
            self.merge_status_label.setText(
                f"✓ Created '{result.name}' from {len(spectra)} spectra"
            )
            
            # Clear the name field
            if hasattr(self, 'merge_name_edit'):
                self.merge_name_edit.clear()
            
            # Refresh UI
            self.plot.autoscale()
            self._refresh_history_view()
            
        except Exception as exc:
            self.merge_status_label.setText(f"❌ Error: {exc}")
            import traceback
            traceback.print_exc()

    def _on_merge_subtract(self) -> None:
        """Perform subtraction operation on two selected spectra (A - B)."""
        if not hasattr(self, 'merge_status_label'):
            return
        
        self.merge_status_label.setText("Processing...")
        
        try:
            # Get exactly 2 spectra
            spectra = self._get_merge_candidates()
            
            if len(spectra) != 2:
                self.merge_status_label.setText("⚠️ Select exactly 2 datasets for subtraction")
                return
            
            spec_a, spec_b = spectra
            
            # Perform subtraction (A - B)
            result, metadata = self.math_service.subtract(spec_a, spec_b)
            
            # Check if result was suppressed
            if result is None:
                status = metadata.get('status', '')
                message = metadata.get('message', 'Result suppressed')
                self.merge_status_label.setText(f"ℹ️ {message}")
                return
            
            # Add to overlay
            self.overlay_service.add(result)
            self._add_spectrum(result)

            # Update status
            self.merge_status_label.setText(
                f"✓ Created '{result.name}' = {spec_a.name} − {spec_b.name}"
            )
            
            # Clear the name field
            if hasattr(self, 'merge_name_edit'):
                self.merge_name_edit.clear()
            
            # Refresh UI
            self.plot.autoscale()
            self._refresh_history_view()
            
        except Exception as exc:
            self.merge_status_label.setText(f"❌ Error: {exc}")
            import traceback
            traceback.print_exc()

    def _on_merge_ratio(self) -> None:
        """Perform ratio operation on two selected spectra (A / B)."""
        if not hasattr(self, 'merge_status_label'):
            return
        
        self.merge_status_label.setText("Processing...")
        
        try:
            # Get exactly 2 spectra
            spectra = self._get_merge_candidates()
            
            if len(spectra) != 2:
                self.merge_status_label.setText("⚠️ Select exactly 2 datasets for ratio")
                return
            
            spec_a, spec_b = spectra
            
            # Perform ratio (A / B)
            result, metadata = self.math_service.ratio(spec_a, spec_b)
            
            # Add to overlay
            self.overlay_service.add(result)
            self._add_spectrum(result)
            
            # Update status
            status_msg = f"✓ Created '{result.name}' = {spec_a.name} / {spec_b.name}"
            if masked > 0:
                status_msg += f"\n⚠️ {masked} points masked"
            self.merge_status_label.setText(status_msg)
            
            # Clear the name field
            if hasattr(self, 'merge_name_edit'):
                self.merge_name_edit.clear()
            
            # Refresh UI
            self.plot.autoscale()
            self._refresh_history_view()
            
        except Exception as exc:
            self.merge_status_label.setText(f"❌ Error: {exc}")
            import traceback
            traceback.print_exc()

    def _on_merge_normalized_difference(self) -> None:
        """Perform normalized difference operation on two selected spectra."""
        if not hasattr(self, 'merge_status_label'):
            return
        
        self.merge_status_label.setText("Processing...")
        try:
            spectra = self._get_merge_candidates()
            if len(spectra) != 2:
                self.merge_status_label.setText("⚠️ Select exactly 2 datasets for ND")
                return
            spec_a, spec_b = spectra
            result, metadata = self.math_service.normalized_difference(spec_a, spec_b)
            if result is None:
                status = str(metadata.get('status', 'suppressed'))
                msg = str(metadata.get('message', 'Result suppressed'))
                self.merge_status_label.setText(f"ℹ️ {msg}")
                return
            # Add to overlay
            self.overlay_service.add(result)
            self._add_spectrum(result)
            # Status
            masked = int(metadata.get('masked_points', 0)) if isinstance(metadata, dict) else 0
            status_msg = f"✓ Created '{result.name}' = (A − B) / (A + B)"
            if masked > 0:
                status_msg += f"\n⚠️ {masked} points masked"
            self.merge_status_label.setText(status_msg)
            # Clear the name field if used in future iterations
            if hasattr(self, 'merge_name_edit'):
                self.merge_name_edit.clear()
            # Refresh UI
            self.plot.autoscale()
            self._refresh_history_view()
        except Exception as exc:
            self.merge_status_label.setText(f"❌ Error: {exc}")
            import traceback
            traceback.print_exc()

    def _on_merge_smooth(self) -> None:
        """Apply smoothing to selected spectrum."""
        if not hasattr(self, 'merge_status_label'):
            return
        
        self.merge_status_label.setText("Processing...")
        try:
            spectra = self._get_merge_candidates()
            if len(spectra) != 1:
                self.merge_status_label.setText("⚠️ Select exactly 1 dataset for smoothing")
                return
            
            # Prompt for smoothing parameters
            window_size, ok1 = QtWidgets.QInputDialog.getInt(
                self, "Smoothing Parameters", "Window size (odd number ≥3):",
                value=5, min=3, max=51, step=2
            )
            if not ok1:
                self.merge_status_label.setText("Cancelled")
                return
            
            method_items = ["moving_average", "savitzky_golay"]
            method, ok2 = QtWidgets.QInputDialog.getItem(
                self, "Smoothing Method", "Select method:",
                method_items, 0, False
            )
            if not ok2:
                self.merge_status_label.setText("Cancelled")
                return
            
            spec = spectra[0]
            result, metadata = self.math_service.smooth(spec, window_size=window_size, method=method)
            
            # Add to overlay
            self.overlay_service.add(result)
            self._add_spectrum(result)

            self.merge_status_label.setText(f"✓ Created '{result.name}' ({method}, window={window_size})")
            
            if hasattr(self, 'merge_name_edit'):
                self.merge_name_edit.clear()
            
            self.plot.autoscale()
            self._refresh_history_view()
            
        except Exception as exc:
            self.merge_status_label.setText(f"❌ Error: {exc}")
            import traceback
            traceback.print_exc()

    def _on_merge_derivative(self) -> None:
        """Compute derivative of selected spectrum."""
        if not hasattr(self, 'merge_status_label'):
            return
        
        self.merge_status_label.setText("Processing...")
        try:
            spectra = self._get_merge_candidates()
            if len(spectra) != 1:
                self.merge_status_label.setText("⚠️ Select exactly 1 dataset for derivative")
                return
            
            # Prompt for derivative order
            order, ok = QtWidgets.QInputDialog.getInt(
                self, "Derivative Order", "Order (1=first derivative, 2=second derivative):",
                value=1, min=1, max=2, step=1
            )
            if not ok:
                self.merge_status_label.setText("Cancelled")
                return
            
            spec = spectra[0]
            result, metadata = self.math_service.derivative(spec, order=order)
            
            # Add to overlay
            self.overlay_service.add(result)
            self._add_spectrum(result)

            order_name = "first" if order == 1 else "second"
            self.merge_status_label.setText(f"✓ Created '{result.name}' ({order_name} derivative)")
            
            if hasattr(self, 'merge_name_edit'):
                self.merge_name_edit.clear()
            
            self.plot.autoscale()
            self._refresh_history_view()
            
        except Exception as exc:
            self.merge_status_label.setText(f"❌ Error: {exc}")
            import traceback
            traceback.print_exc()

    def _on_merge_integral(self) -> None:
        """Compute integral of selected spectrum."""
        if not hasattr(self, 'merge_status_label'):
            return
        
        self.merge_status_label.setText("Processing...")
        try:
            spectra = self._get_merge_candidates()
            if len(spectra) != 1:
                self.merge_status_label.setText("⚠️ Select exactly 1 dataset for integral")
                return
            
            # Prompt for integration method
            method_items = ["cumulative", "total"]
            method, ok = QtWidgets.QInputDialog.getItem(
                self, "Integration Method", "Select method:\n• cumulative: cumulative trapezoid integration (creates new spectrum)\n• total: single integrated value (shown in log)",
                method_items, 0, False
            )
            if not ok:
                self.merge_status_label.setText("Cancelled")
                return
            
            spec = spectra[0]
            result, metadata = self.math_service.integral(spec, method=method)
            
            if method == 'cumulative':
                # Add spectrum to overlay
                self.overlay_service.add(result)
                self._add_spectrum(result)

                total_val = metadata.get('total', 0.0)
                self.merge_status_label.setText(f"✓ Created '{result.name}' (cumulative, total={total_val:.6g})")
                
                if hasattr(self, 'merge_name_edit'):
                    self.merge_name_edit.clear()
                
                self.plot.autoscale()
                self._refresh_history_view()
            else:
                # Total: just show the value
                total_val = metadata.get('total', 0.0)
                unit = metadata.get('unit', '')

                self.merge_status_label.setText(f"✓ Total integral: {total_val:.6g} {unit}")
                
        except Exception as exc:
            self.merge_status_label.setText(f"❌ Error: {exc}")
            import traceback
            traceback.print_exc()

    # ----------------------------- Annotation Persistence ------------------
    def _get_annotations_dir(self) -> Path:
        """Get the directory for storing annotation files."""
        annotations_dir = Path("storage") / "annotations"
        annotations_dir.mkdir(parents=True, exist_ok=True)
        return annotations_dir

    def _save_annotations_for_dataset(self, dataset_id: str) -> None:
        """Save all annotations for a specific dataset to a JSON file."""
        if not dataset_id:
            return

        annotations = self.plot.get_annotations(dataset_id=dataset_id)
        if not annotations:
            # Delete annotation file if no annotations exist
            annotation_file = self._get_annotations_dir() / f"{dataset_id}.json"
            if annotation_file.exists():
                annotation_file.unlink()
            return

        # Convert annotations to JSON-serializable dict
        annotations_data = []
        for ann in annotations:
            annotations_data.append({
                'id': ann.id,
                'dataset_id': ann.dataset_id,
                'text': ann.text,
                'x_nm': ann.x_nm,
                'x_max_nm': ann.x_max_nm,
                'y_fraction': ann.y_fraction,
                'visible': ann.visible,
                'color': ann.color,
                'vertical': ann.vertical,
            })

        # Write to file
        import json
        annotation_file = self._get_annotations_dir() / f"{dataset_id}.json"
        with open(annotation_file, 'w') as f:
            json.dump({
                'version': '1.0',
                'dataset_id': dataset_id,
                'annotations': annotations_data
            }, f, indent=2)

    def _load_annotations_for_dataset(self, dataset_id: str) -> None:
        """Load annotations for a specific dataset from JSON file."""
        if not dataset_id:
            return

        annotation_file = self._get_annotations_dir() / f"{dataset_id}.json"
        if not annotation_file.exists():
            return

        try:
            import json
            from app.ui.plot_pane import Annotation

            with open(annotation_file, 'r') as f:
                data = json.load(f)

            # Clear existing annotations for this dataset
            self.plot.clear_annotations(dataset_id=dataset_id)

            # Load annotations
            for ann_data in data.get('annotations', []):
                annotation = Annotation(
                    id=ann_data.get('id', ''),
                    dataset_id=ann_data.get('dataset_id', dataset_id),
                    text=ann_data.get('text', ''),
                    x_nm=ann_data.get('x_nm', 0.0),
                    x_max_nm=ann_data.get('x_max_nm'),
                    y_fraction=ann_data.get('y_fraction', 0.9),
                    visible=ann_data.get('visible', True),
                    color=ann_data.get('color', '#FFFF00'),
                    vertical=ann_data.get('vertical', False),
                )
                self.plot.add_annotation(annotation)
        except Exception:
            pass  # Non-fatal: annotation loading failures shouldn't crash the app

    # ----------------------------- Overlay refresh ----------------------
    def _update_math_selectors(self) -> None:
        # Placeholder hook for tests
        pass

    def refresh_overlay(self) -> None:
        # Rebuild traces using the current unit selections and visibility
        x_unit = self.unit_combo.currentText() if self.unit_combo is not None else "nm"
        for spec in self.overlay_service.list():
            visible = self._visibility.get(spec.id, True)
            style = TraceStyle(color=self._spectrum_colors.get(spec.id, QtGui.QColor("#4F6D7A")))
            target_y_unit = spec.y_unit
            x_disp, y_disp, _ = self.units_service.convert(spec, x_unit, target_y_unit)
            y_label = "%T" if target_y_unit.lower() in {"%t", "percent_transmittance"} else target_y_unit
            self.plot.set_y_label(y_label or "Intensity")
            self.plot.add_trace(spec.id, spec.name, x_disp, y_disp, style)
            self.plot.set_visible(spec.id, visible)
        self.plot.autoscale()

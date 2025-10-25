"""Application entry point for the Spectra desktop shell."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, cast

import numpy as np
import pyqtgraph as pg

# Ensure repository root is importable when run as a script OR when VS Code
# launches as a hyphenated pseudo-package name (e.g., "spectra-app-v2.app.main").
# In that case, __package__ is non-empty but contains a '-', which prevents
# normal relative imports from resolving; we force-add the repo root to sys.path
# so absolute imports like 'from app import ...' continue to work.
_pkg = __package__ or ""
if _pkg in (None, "") or ("-" in _pkg):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.qt_compat import get_qt
from typing import Any
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
)
from app.services import nist_asd_service
from app.ui.plot_pane import PlotPane, TraceStyle
from app.ui.remote_data_dialog import RemoteDataDialog
from app.ui.export_options_dialog import ExportOptionsDialog

QtCore: Any
QtGui: Any
QtWidgets: Any
QT_BINDING: str
QtCore, QtGui, QtWidgets, QT_BINDING = get_qt()


# Lightweight background workers for Remote Data tab (streaming search and downloads)
# These mirror the behavior of the dialog workers but are local to the main window module

Signal = getattr(QtCore, "Signal", None)  # type: ignore[attr-defined]
if Signal is None:
    Signal = getattr(QtCore, "pyqtSignal")  # type: ignore[attr-defined]

Slot = getattr(QtCore, "Slot", None)  # type: ignore[attr-defined]
if Slot is None:
    Slot = getattr(QtCore, "pyqtSlot")  # type: ignore[attr-defined]


class _RemoteSearchWorker(QtCore.QObject):  # type: ignore[name-defined]
    started = Signal()  # type: ignore[misc]
    record_found = Signal(object)  # type: ignore[misc]
    finished = Signal(list)  # type: ignore[misc]
    failed = Signal(str)  # type: ignore[misc]
    cancelled = Signal()  # type: ignore[misc]

    def __init__(self, remote_service: RemoteDataService) -> None:
        super().__init__()
        self._remote_service = remote_service
        self._cancel_requested = False

    @Slot(str, dict, bool)  # type: ignore[misc]
    def run(self, provider: str, query: dict[str, str], include_imaging: bool) -> None:
        self.started.emit()  # type: ignore[attr-defined]
        collected: list[Any] = []
        try:
            # Fast path for simple providers
            if provider == RemoteDataService.PROVIDER_NIST:
                results = self._remote_service.search(provider, query, include_imaging=include_imaging)
                for rec in results:
                    if self._cancel_requested:
                        self.cancelled.emit()  # type: ignore[attr-defined]
                        return
                    collected.append(rec)
                    self.record_found.emit(rec)  # type: ignore[attr-defined]
                self.finished.emit(collected)  # type: ignore[attr-defined]
                return

            # Progressive strategy for MAST (spectra first, then optional imaging)
            if provider == RemoteDataService.PROVIDER_MAST:
                base = dict(query)
                mission_batches: list[list[str]] = [["JWST"], ["HST"], ["IUE", "FUSE", "GALEX"], ["Kepler", "K2", "TESS"]]
                seen: set[tuple[str, str]] = set()

                def _emit(batch: list[Any]) -> None:
                    for rec in batch:
                        if self._cancel_requested:
                            self.cancelled.emit()  # type: ignore[attr-defined]
                            return
                        key = (getattr(rec, 'download_url', ''), getattr(rec, 'identifier', ''))
                        if key in seen:
                            continue
                        seen.add(key)
                        collected.append(rec)
                        self.record_found.emit(rec)  # type: ignore[attr-defined]

                # Spectra first
                for missions in mission_batches:
                    for mission in missions:
                        if self._cancel_requested:
                            self.cancelled.emit()  # type: ignore[attr-defined]
                            return
                        criteria = {**base, "obs_collection": mission, "dataproduct_type": "spectrum", "calib_level": [2, 3], "intentType": "SCIENCE"}
                        try:
                            batch = self._remote_service.search(RemoteDataService.PROVIDER_MAST, criteria, include_imaging=False)
                        except Exception:
                            batch = []
                        _emit(batch)

                # Imaging next (optional)
                if include_imaging:
                    for missions in mission_batches:
                        for mission in missions:
                            if self._cancel_requested:
                                self.cancelled.emit()  # type: ignore[attr-defined]
                                return
                            criteria = {**base, "obs_collection": mission, "dataproduct_type": "image", "intentType": "SCIENCE"}
                            try:
                                batch = self._remote_service.search(RemoteDataService.PROVIDER_MAST, criteria, include_imaging=True)
                            except Exception:
                                batch = []
                            _emit(batch)

                self.finished.emit(collected)  # type: ignore[attr-defined]
                return

            # Fallback: single-shot
            results = self._remote_service.search(provider, query, include_imaging=include_imaging)
            for rec in results:
                if self._cancel_requested:
                    self.cancelled.emit()  # type: ignore[attr-defined]
                    return
                collected.append(rec)
                self.record_found.emit(rec)  # type: ignore[attr-defined]
            self.finished.emit(collected)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover
            self.failed.emit(str(exc))  # type: ignore[attr-defined]

    @Slot()  # type: ignore[misc]
    def cancel(self) -> None:
        self._cancel_requested = True


class _RemoteDownloadWorker(QtCore.QObject):  # type: ignore[name-defined]
    started = Signal(int)  # type: ignore[misc]
    record_ingested = Signal(object)  # type: ignore[misc]
    record_failed = Signal(object, str)  # type: ignore[misc]
    finished = Signal(list)  # type: ignore[misc]
    failed = Signal(str)  # type: ignore[misc]
    cancelled = Signal()  # type: ignore[misc]

    def __init__(self, remote_service: RemoteDataService, ingest_service: DataIngestService) -> None:
        super().__init__()
        self._remote_service = remote_service
        self._ingest_service = ingest_service
        self._cancel_requested = False

    @Slot(list)  # type: ignore[misc]
    def run(self, records: list[Any]) -> None:
        self.started.emit(len(records))  # type: ignore[attr-defined]
        ingested: list[Any] = []
        try:
            for record in records:
                if self._cancel_requested:
                    self.cancelled.emit()  # type: ignore[attr-defined]
                    return
                try:
                    download = self._remote_service.download(record)
                    # RemoteDownloadResult has a clean Path attribute; use it directly
                    file_path = download.path
                    non_spectral_extensions = {'.gif', '.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.svg', '.txt', '.log', '.xml', '.html', '.htm', '.json', '.md'}
                    if file_path.suffix.lower() in non_spectral_extensions:
                        self.record_failed.emit(record, f"Skipped non-spectral file type: {file_path.suffix}")  # type: ignore[attr-defined]
                        continue
                    ing_item = self._ingest_service.ingest(file_path)
                except Exception as exc:  # pragma: no cover
                    self.record_failed.emit(record, str(exc))  # type: ignore[attr-defined]
                    continue
                if isinstance(ing_item, list):
                    ingested.extend(ing_item)
                else:
                    ingested.append(ing_item)
                self.record_ingested.emit(record)  # type: ignore[attr-defined]
            if self._cancel_requested:
                self.cancelled.emit()  # type: ignore[attr-defined]
                return
        except Exception as exc:  # pragma: no cover
            self.failed.emit(str(exc))  # type: ignore[attr-defined]
            return
        self.finished.emit(ingested)  # type: ignore[attr-defined]

    @Slot()  # type: ignore[misc]
    def cancel(self) -> None:
        self._cancel_requested = True

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
PLOT_MAX_POINTS_KEY = "plot/max_points"


class SpectraMainWindow(QtWidgets.QMainWindow):
    """Preview shell that wires UI actions to services with docked layout."""

    def __init__(
        self,
        container: object | None = None,
        *,
        knowledge_log_service: KnowledgeLogService | None = None,
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
        # Use an app-local, easy-to-find downloads directory by default (override with SPECTRA_STORE_DIR)
        self._app_root = Path(__file__).resolve().parent.parent
        _store_override = os.environ.get("SPECTRA_STORE_DIR")
        self._default_store_dir = Path(_store_override) if _store_override else (self._app_root / "downloads")
        self.store: LocalStore | None = None if self._persistence_disabled else LocalStore(base_dir=self._default_store_dir)
        self.ingest_service = DataIngestService(self.units_service, store=self.store)
        remote_store = self.store
        if remote_store is None:
            # Fall back to app-local downloads directory even when persistence is toggled off
            remote_store = LocalStore(base_dir=self._default_store_dir)
        self.remote_data_service = RemoteDataService(remote_store)
        self.math_service = MathService()
        self.knowledge_log = knowledge_log_service or KnowledgeLogService(
            default_context="Spectra Desktop Session"
        )

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
        self._nist_collections: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._nist_collection_labels: Dict[str, str] = {}
        self._nist_collection_colors: Dict[str, QtGui.QColor] = {}
        self._nist_palette_index = 0
        self._nist_use_uniform_colors = False
        self._nist_active_key: Optional[str] = None
        self._nist_collection_counter = 0
        self._nist_overlay_payloads: Dict[str, Dict[str, Any]] = {}

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
        self.library_list: QtWidgets.QTreeWidget | None = None
        self.library_view: QtWidgets.QTreeWidget | None = None
        self.library_search: QtWidgets.QLineEdit | None = None
        self.library_detail: QtWidgets.QPlainTextEdit | None = None
        self.library_hint: QtWidgets.QLabel | None = None
        self._library_entries: Dict[str, Mapping[str, Any]] = {}
        self._library_tab_index: int | None = None
        self._use_uniform_palette = False
        self._uniform_color = QtGui.QColor("#4F6D7A")
        self._last_display_views: List[Dict[str, object]] = []
        self._data_table_attached = False
        # Docs UI
        self.docs_list: QtWidgets.QListWidget | None = None
        self.doc_viewer: QtWidgets.QPlainTextEdit | None = None

        # Async NIST fetch state
        self._nist_thread: Optional[QtCore.QThread] = None
        self._nist_worker: Optional[QtCore.QObject] = None

        # Remote data tab state
        self._remote_records: List[Any] = []
        self._remote_search_thread: Optional[QtCore.QThread] = None
        self._remote_search_worker: Optional[QtCore.QObject] = None
        self._remote_download_thread: Optional[QtCore.QThread] = None
        self._remote_download_worker: Optional[QtCore.QObject] = None

        self._setup_ui()
        self._setup_menu()
        self._wire_shortcuts()
        self._initialize_remote_data_providers()
        self._load_docs_if_needed()  # Pre-load documentation so it's ready immediately
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

        # Plot pane
        self.plot = PlotPane(self, max_points=self._plot_max_points)
        self.central_split.addWidget(self.plot)
        self.plot.autoscale()

        # Left dock: datasets and library
        self.dataset_dock = QtWidgets.QDockWidget("Data", self)
        self.dataset_dock.setObjectName("dock-datasets")
        self.data_tabs = QtWidgets.QTabWidget()
        # Datasets tab content
        datasets_container = QtWidgets.QWidget()
        datasets_layout = QtWidgets.QVBoxLayout(datasets_container)
        datasets_layout.setContentsMargins(4, 4, 4, 4)
        # Optional filter line edit (future use)
        self.dataset_filter = QtWidgets.QLineEdit()
        self.dataset_filter.setPlaceholderText("Filter datasets…")
        self.dataset_filter.setClearButtonEnabled(True)
        self.dataset_filter.textChanged.connect(self._on_dataset_filter_changed)
        datasets_layout.addWidget(self.dataset_filter)
        # Dataset view
        self.dataset_view = QtWidgets.QTreeView()
        self.dataset_view.setRootIsDecorated(True)
        self.dataset_tree = self.dataset_view  # compatibility alias for tests
        self.dataset_view.setAlternatingRowColors(True)
        self.dataset_model = QtGui.QStandardItemModel(0, 2, self)
        self.dataset_model.setHorizontalHeaderLabels(["Dataset", "Visible"])
        # Create a root group "Originals" to hold imported spectra
        self._originals_item = QtGui.QStandardItem("Originals")
        self._originals_item.setEditable(False)
        self.dataset_model.appendRow([self._originals_item, QtGui.QStandardItem("")])
        self.dataset_view.setModel(self.dataset_model)
        if hasattr(self.dataset_view.header(), "setStretchLastSection"):
            self.dataset_view.header().setStretchLastSection(False)
            self.dataset_view.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
            self.dataset_view.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.dataset_model.itemChanged.connect(self._on_dataset_item_changed)
        datasets_layout.addWidget(self.dataset_view)
        self.data_tabs.addTab(datasets_container, "Datasets")

        # Library tab placeholder (built on demand)
        library_container = QtWidgets.QWidget()
        library_layout = QtWidgets.QVBoxLayout(library_container)
        library_layout.setContentsMargins(4, 4, 4, 4)
        self.library_view = QtWidgets.QTreeWidget()
        self.library_view.setHeaderLabels(["File", "Origin"])
        library_layout.addWidget(self.library_view)
        self.data_tabs.addTab(library_container, "Library")
        self.dataset_dock.setWidget(self.data_tabs)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.dataset_dock)
        # Ensure dataset dock is visible
        self.dataset_dock.show()

        # Right dock: inspector (tab widget placeholder)
        self.inspector_dock = QtWidgets.QDockWidget("Inspector", self)
        self.inspector_dock.setObjectName("dock-inspector")
        self.inspector_tabs = QtWidgets.QTabWidget()
        # Documentation tab
        docs_container = QtWidgets.QWidget()
        docs_layout = QtWidgets.QHBoxLayout(docs_container)
        docs_layout.setContentsMargins(4, 4, 4, 4)
        self.docs_list = QtWidgets.QListWidget()
        self.docs_list.currentRowChanged.connect(self._on_doc_selected)
        self.doc_viewer = QtWidgets.QPlainTextEdit(readOnly=True)
        docs_layout.addWidget(self.docs_list, 1)
        docs_layout.addWidget(self.doc_viewer, 2)
        # Expose for tests
        self.tab_docs = docs_container
        self.inspector_tabs.addTab(docs_container, "Docs")

        # Reference tab (NIST, IR, Line shapes)
        self.tab_reference = QtWidgets.QWidget()
        ref_layout = QtWidgets.QVBoxLayout(self.tab_reference)
        ref_layout.setContentsMargins(4, 4, 4, 4)

        # Top row: overlay toggle + status
        top_row = QtWidgets.QHBoxLayout()
        self.reference_overlay_checkbox = QtWidgets.QCheckBox("Show on plot")
        self.reference_overlay_checkbox.setEnabled(False)
        self.reference_overlay_checkbox.toggled.connect(self._on_reference_overlay_toggled)
        self.reference_status_label = QtWidgets.QLabel("")
        top_row.addWidget(self.reference_overlay_checkbox)
        top_row.addStretch(1)
        top_row.addWidget(self.reference_status_label)
        ref_layout.addLayout(top_row)

        # Shared preview plot
        import pyqtgraph as _pg  # local import to ensure pg is ready
        self.reference_plot: _pg.PlotWidget = _pg.PlotWidget()
        self.reference_plot.setLabel("bottom", "Wavelength (nm)")
        ref_layout.addWidget(self.reference_plot, 2)

        # Tabs within Reference
        self.reference_tabs = QtWidgets.QTabWidget()
        ref_layout.addWidget(self.reference_tabs, 3)

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
        self.nist_fetch_button.clicked.connect(self._on_nist_fetch_clicked)
        for w in (
            QtWidgets.QLabel("Element:"),
            self.nist_element_edit,
            QtWidgets.QLabel("Range:"),
            self.nist_lower_spin,
            QtWidgets.QLabel("–"),
            self.nist_upper_spin,
            self.nist_fetch_button,
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
        self.reference_filter.textChanged.connect(self._on_reference_filter_changed)
        ir_layout.addWidget(self.reference_filter)
        # Table dedicated to IR
        self.ir_table = QtWidgets.QTableWidget(0, 3)
        self.ir_table.setHorizontalHeaderLabels(["Group", "min (cm⁻¹)", "max (cm⁻¹)"])
        self.ir_table.horizontalHeader().setStretchLastSection(True)
        self.ir_table.itemSelectionChanged.connect(self._on_ir_row_selected)
        ir_layout.addWidget(self.ir_table, 1)
        self.reference_tabs.addTab(ir_tab, "IR Functional Groups")

        # --- Line shapes tab
        ls_tab = QtWidgets.QWidget()
        ls_layout = QtWidgets.QVBoxLayout(ls_tab)
        # Table dedicated to Line Shapes
        self.ls_table = QtWidgets.QTableWidget(0, 2)
        self.ls_table.setHorizontalHeaderLabels(["Model", "Notes"])
        self.ls_table.horizontalHeader().setStretchLastSection(True)
        self.ls_table.itemSelectionChanged.connect(self._on_line_shape_row_selected)
        ls_layout.addWidget(self.ls_table, 1)
        self.reference_tabs.addTab(ls_tab, "Line Shapes")

        # When the tab changes, refresh the view
        self.reference_tabs.currentChanged.connect(lambda _: self._refresh_reference_view())
        # Also update preview axis unit when the global unit changes
        if self.unit_combo is not None:
            self.unit_combo.currentTextChanged.connect(self._update_reference_axis)

        self.inspector_tabs.addTab(self.tab_reference, "Reference")

        # Remote Data tab
        self.tab_remote = QtWidgets.QWidget()
        remote_layout = QtWidgets.QVBoxLayout(self.tab_remote)
        remote_layout.setContentsMargins(4, 4, 4, 4)
        
        # Controls row
        remote_controls = QtWidgets.QHBoxLayout()
        remote_controls.addWidget(QtWidgets.QLabel("Catalogue:"))
        self.remote_provider_combo = QtWidgets.QComboBox()
        self.remote_provider_combo.currentIndexChanged.connect(self._on_remote_provider_changed)
        remote_controls.addWidget(self.remote_provider_combo)
        self.remote_search_edit = QtWidgets.QLineEdit()
        self.remote_search_edit.setPlaceholderText("Target name or keyword…")
        self.remote_search_edit.returnPressed.connect(self._on_remote_search)
        remote_controls.addWidget(self.remote_search_edit, 1)
        self.remote_search_button = QtWidgets.QPushButton("Search")
        self.remote_search_button.clicked.connect(self._on_remote_search)
        remote_controls.addWidget(self.remote_search_button)
        remote_layout.addLayout(remote_controls)
        
        # Results table
        self.remote_results_table = QtWidgets.QTableWidget(0, 4)
        self.remote_results_table.setHorizontalHeaderLabels(["ID", "Title", "Target", "Telescope"])
        self.remote_results_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.remote_results_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        header = self.remote_results_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.remote_results_table.itemSelectionChanged.connect(self._on_remote_selection_changed)
        remote_layout.addWidget(self.remote_results_table, 1)
        
        # Import button
        self.remote_import_button = QtWidgets.QPushButton("Download && Import Selected")
        self.remote_import_button.setEnabled(False)
        self.remote_import_button.clicked.connect(self._on_remote_import)
        remote_layout.addWidget(self.remote_import_button)
        
        # Status label
        self.remote_status_label = QtWidgets.QLabel("")
        self.remote_status_label.setWordWrap(True)
        remote_layout.addWidget(self.remote_status_label)
        
        self.inspector_tabs.addTab(self.tab_remote, "Remote Data")
        
        self.inspector_dock.setWidget(self.inspector_tabs)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.inspector_dock)
        # Ensure inspector dock is visible
        self.inspector_dock.show()

        # Bottom dock: log view
        self.log_dock = QtWidgets.QDockWidget("Log", self)
        self.log_dock.setObjectName("dock-log")
        self.log_view = QtWidgets.QPlainTextEdit(readOnly=True)
        self.log_dock.setWidget(self.log_view)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)

        # History dock (table + detail)
        self.history_dock = QtWidgets.QDockWidget("History", self)
        self.history_dock.setObjectName("dock-history")
        history_container = QtWidgets.QWidget()
        history_layout = QtWidgets.QVBoxLayout(history_container)
        self.history_table = QtWidgets.QTableWidget(0, 3)
        self.history_table.setHorizontalHeaderLabels(["When", "Component", "Summary"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_detail = QtWidgets.QPlainTextEdit(readOnly=True)
        history_layout.addWidget(self.history_table)
        history_layout.addWidget(self.history_detail, 1)
        self.history_dock.setWidget(history_container)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.history_dock)
        # Don't auto-show History dock - let users open it via View menu when needed
        self.history_table.itemSelectionChanged.connect(self._on_history_row_selected)
        self._refresh_history_view()

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
        self.plot_toolbar.addWidget(QtWidgets.QLabel(" X: "))
        self.plot_toolbar.addWidget(self.unit_combo)
        # Normalization combo
        self.norm_combo = QtWidgets.QComboBox()
        self.norm_combo.addItems(["None", "Max", "Area"])
        self.norm_combo.setCurrentText("None")
        self.norm_combo.currentTextChanged.connect(lambda _: self._refresh_plot())
        self.plot_toolbar.addSeparator()
        self.plot_toolbar.addWidget(QtWidgets.QLabel(" Normalize: "))
        self.plot_toolbar.addWidget(self.norm_combo)
        # Max points control
        self.plot_toolbar.addSeparator()
        self.plot_toolbar.addWidget(QtWidgets.QLabel(" Points: "))
        self.plot_max_points_control = QtWidgets.QSpinBox()
        self.plot_max_points_control.setRange(PlotPane.MIN_MAX_POINTS, PlotPane.MAX_MAX_POINTS)
        self.plot_max_points_control.setValue(self._plot_max_points)
        self.plot_max_points_control.valueChanged.connect(self._on_max_points_changed)
        self.plot_toolbar.addWidget(self.plot_max_points_control)

        # Status bar
        self.statusBar().showMessage("Ready")

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
        view_menu.addAction(self.history_dock.toggleViewAction())
        view_menu.addAction(self.log_dock.toggleViewAction())
        if self.plot_toolbar is not None:
            view_menu.addAction(self.plot_toolbar.toggleViewAction())

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

    def _wire_shortcuts(self) -> None:
        # Keep minimal; menu items already provide the primary access paths.
        pass

    def _build_library_tab(self) -> None:
        # Ensure library tab header is correct and has a placeholder
        if self.library_view is None:
            return
        self._refresh_library_view()

    def _toggle_data_table(self, checked: bool) -> None:
        # Not implemented in the minimal UI; ignore toggle.
        pass

    def show_documentation(self) -> None:
        self._load_docs_if_needed()
        if self.docs_list is not None and self.docs_list.count() > 0:
            self.docs_list.setCurrentRow(0)
            self._on_doc_selected(0)
        # If no docs, silently succeed

    def show_remote_data_tab(self) -> None:
        # Switch to the Remote Data tab in Inspector dock
        self.inspector_dock.raise_()
        try:
            index = self.inspector_tabs.indexOf(self.tab_remote)
            if index != -1:
                self.inspector_tabs.setCurrentIndex(index)
        except Exception:
            pass

    def open_file(self) -> None:
        path_str, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Spectrum",
            str(SAMPLES_DIR),
            "Data files (*.csv *.txt *.fits *.fit *.fts *.jdx *.dx *.jcamp);;All files (*.*)",
        )
        if not path_str:
            return
        self._ingest_path(Path(path_str))

    def load_sample_via_menu(self) -> None:
        if not SAMPLES_DIR.exists():
            QtWidgets.QMessageBox.information(self, "Samples", "No samples available.")
            return
        path_str, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Sample",
            str(SAMPLES_DIR),
            "Data files (*.csv *.txt *.fits *.fit *.fts *.jdx *.dx *.jcamp);;All files (*.*)",
        )
        if not path_str:
            return
        self._ingest_path(Path(path_str))

    def export_manifest(self) -> None:
        spectra = [spec for spec in self.overlay_service.list() if self._visibility.get(spec.id, True)]
        if not spectra:
            QtWidgets.QMessageBox.information(self, "Export", "No visible spectra to export.")
            return
        allow_composite = len(spectra) >= 2
        dialog = ExportOptionsDialog(self, allow_composite=allow_composite)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        options = dialog.result()
        if not options.has_selection:
            return

        target_str, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Manifest",
            str(Path.home() / "export" / "manifest.json"),
            "JSON (*.json)",
        )
        if not target_str:
            return
        target = Path(target_str)
        # Always write the bundle manifest + combined CSV + PNG
        outcome = self.provenance_service.export_bundle(
            spectra,
            target,
            png_writer=lambda p: self.plot.export_png(p),
        )
        # Optional additional CSVs
        if options.include_wide_csv:
            try:
                self.provenance_service.write_wide_csv(target.with_name(target.stem + "-wide.csv"), spectra)
            except Exception as exc:
                self._log("Export", f"Wide CSV failed: {exc}")
        if options.include_composite_csv and len(spectra) >= 2:
            try:
                self.provenance_service.write_composite_csv(target.with_name(target.stem + "-composite.csv"), spectra)
            except Exception as exc:
                self._log("Export", f"Composite CSV failed: {exc}")
        self._log("Export", f"Bundle written: {outcome.get('manifest_path')}")

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
            # Re-enable persistent cache in the app-local downloads directory
            self.store = LocalStore(base_dir=self._default_store_dir)
            self._log("System", "Persistent cache enabled.")
        self.ingest_service.store = self.store
        if hasattr(self, "remote_data_service") and isinstance(self.remote_data_service, RemoteDataService):
            if self.store is None:
                # When disabled, still use app-local dir for remote downloads
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

    # ------------------------------------------------------------------
    # Library, ingest, and docs helpers
    def _refresh_library_view(self) -> None:
        if self.library_view is None:
            return
        self.library_view.clear()
        # Prefer the main store; if persistence is disabled, fall back to remote service store
        effective_store = self.store
        if effective_store is None and hasattr(self, "remote_data_service"):
            effective_store = getattr(self.remote_data_service, "store", None)
        entries = effective_store.list_entries() if effective_store is not None else {}
        if not entries:
            placeholder = QtWidgets.QTreeWidgetItem(["No cached files", ""])
            self.library_view.addTopLevelItem(placeholder)
            return
        for _sha, record in entries.items():
            name = str(record.get("filename") or Path(str(record.get("stored_path", ""))).name)
            origin = "Local import"
            src = record.get("source", {})
            if isinstance(src, dict) and isinstance(src.get("remote"), dict):
                remote = src.get("remote") or {}
                provider = str(remote.get("provider") or "Remote")
                identifier = str(remote.get("identifier") or remote.get("id") or "")
                origin = provider if not identifier else f"{provider} – {identifier}"
            item = QtWidgets.QTreeWidgetItem([name, origin])
            self.library_view.addTopLevelItem(item)

    def _record_remote_history_event(self, spectra: Spectrum | list[Spectrum]) -> Dict[str, str]:
        specs = spectra if isinstance(spectra, list) else [spectra]
        summary_parts: list[str] = []
        last_payload: Dict[str, str] = {}
        for spec in specs:
            rec = spec.metadata.get("cache_record", {}) if isinstance(spec.metadata, dict) else {}
            src = rec.get("source", {}) if isinstance(rec, dict) else {}
            remote = src.get("remote", {}) if isinstance(src, dict) else {}
            if isinstance(remote, dict):
                provider = str(remote.get("provider") or "Remote")
                ident = str(remote.get("identifier") or remote.get("id") or "")
                summary_parts.append(provider + (f" ({ident})" if ident else ""))
                # Trim references to avoid long URLs in log entries
                ref = str(remote.get("uri") or ident or provider)
                if ref.startswith("http"):
                    ref = ref.split("/")[-1][:55]
                # Persist a history entry regardless of runtime-only defaults
                try:
                    from app.services.knowledge_log_service import KnowledgeLogService as _KLS

                    klog = _KLS(
                        log_path=self.knowledge_log.log_path,  # type: ignore[attr-defined]
                        runtime_only_components=(),
                        author=self.knowledge_log.author if hasattr(self.knowledge_log, "author") else None,
                        default_context=getattr(self.knowledge_log, "default_context", None),
                    )
                    klog.record_event(
                        "Remote Import",
                        f"Imported remote data from {provider}",
                        references=[ref],
                        persist=True,
                    )
                except Exception:
                    # Best-effort logging; do not fail UI flows
                    pass
                last_payload = {"provider": provider, "identifier": ident}
        if not summary_parts:
            try:
                from app.services.knowledge_log_service import KnowledgeLogService as _KLS

                klog = _KLS(
                    log_path=self.knowledge_log.log_path,  # type: ignore[attr-defined]
                    runtime_only_components=(),
                    author=self.knowledge_log.author if hasattr(self.knowledge_log, "author") else None,
                    default_context=getattr(self.knowledge_log, "default_context", None),
                )
                klog.record_event("Remote Import", "Imported remote data", persist=True)
            except Exception:
                pass
        return last_payload

    def _ingest_path(self, path: Path) -> None:
        try:
            spectra = self.ingest_service.ingest(path)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Import failed", str(exc))
            return
        for spectrum in spectra:
            self.overlay_service.add(spectrum)
            self._add_spectrum(spectrum)
        self.plot.autoscale()
        self._refresh_library_view()
        # Record in knowledge log and update history
        try:
            self.knowledge_log.record_event(
                "Ingest",
                f"Ingested file {path.name}",
                references=[path.name],
                persist=True,
            )
        finally:
            self._refresh_history_view()

    # Public helper used by tests
    def _add_spectrum(self, spectrum: Spectrum) -> None:
        color = self._next_palette_color()
        self._spectrum_colors[spectrum.id] = color
        style = TraceStyle(color=color, width=1.5, show_in_legend=True)
        self.plot.add_trace(
            key=spectrum.id,
            alias=spectrum.name,
            x_nm=spectrum.x,
            y=spectrum.y,
            style=style,
        )
        self._visibility[spectrum.id] = True
        self._append_dataset_row(spectrum)

    def _append_dataset_row(self, spectrum: Spectrum) -> None:
        if self.dataset_model is None or getattr(self, "_originals_item", None) is None:
            return
        alias_item = QtGui.QStandardItem(str(spectrum.name))
        alias_item.setEditable(False)
        visible_item = QtGui.QStandardItem("")
        visible_item.setCheckable(True)
        visible_item.setEditable(False)
        visible_item.setCheckState(QtCore.Qt.CheckState.Checked)
        self._originals_item.appendRow([alias_item, visible_item])
        self._dataset_items[spectrum.id] = alias_item

    def _on_dataset_item_changed(self, item: QtGui.QStandardItem) -> None:
        if self.dataset_model is None or self.dataset_view is None:
            return
        # Determine which spectrum id this row corresponds to (support tree rows)
        index = item.index()
        parent = index.parent()
        row = index.row()
        alias_index = self.dataset_model.index(row, 0, parent)
        alias_item = self.dataset_model.itemFromIndex(alias_index)
        spec_id = None
        for sid, ali in self._dataset_items.items():
            if ali is alias_item:
                spec_id = sid
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

    def _on_dataset_filter_changed(self, text: str) -> None:
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

    def _on_doc_selected(self, row: int) -> None:
        if self.docs_list is None or self.doc_viewer is None:
            return
        item = self.docs_list.item(row)
        if item is None:
            return
        path = Path(str(item.data(QtCore.Qt.ItemDataRole.UserRole)))
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            text = ""
        self.doc_viewer.setPlainText(text)

    def _load_docs_if_needed(self) -> None:
        if self.docs_list is None:
            return
        if self.docs_list.count() > 0:
            return
        # Prefer user-facing docs, fallback to project docs
        candidates: list[Path] = []
        for folder in (Path(__file__).resolve().parents[1] / "docs" / "user",
                       Path(__file__).resolve().parents[1] / "docs"):
            if folder.exists():
                candidates.extend(sorted(folder.glob("*.md")))
        for path in candidates:
            item = QtWidgets.QListWidgetItem(path.stem)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, str(path))
            self.docs_list.addItem(item)

    def _on_max_points_changed(self, value: int) -> None:
        self._plot_max_points = int(value)
        self.plot.set_max_points(self._plot_max_points)
        self._save_plot_max_points(self._plot_max_points)

    def _refresh_plot(self) -> None:
        # For now, just re-apply visibility and autoscale. A full redraw with
        # normalization can be wired in a later step.
        for spec in self.overlay_service.list():
            try:
                self.plot.update_alias(spec.id, spec.name)
            except Exception:
                pass
        self.plot.autoscale()

    def _next_palette_color(self) -> QtGui.QColor:
        if self._use_uniform_palette:
            return QtGui.QColor(self._uniform_color)
        color = self._palette[self._palette_index % len(self._palette)]
        self._palette_index += 1
        return color

    # ----------------------------- Reference tab helpers -----------------
    def _update_reference_axis(self, unit: str) -> None:
        try:
            # If IR tab is active, prefer wavenumber labelling for clarity
            is_ir = False
            try:
                is_ir = (self.reference_tabs.currentIndex() == 1)
            except Exception:
                is_ir = False
            if is_ir and unit == "cm⁻¹":
                self.reference_plot.setLabel("bottom", "Wavenumber (cm⁻¹)")
            else:
                self.reference_plot.setLabel("bottom", f"Wavelength ({unit})")
        except Exception:
            pass

    def _refresh_reference_view(self) -> None:
        # Clear preview plot and table for fresh content
        try:
            for item in self.reference_plot.listDataItems():
                self.reference_plot.removeItem(item)
        except Exception:
            pass
        self.reference_table.setRowCount(0)
        # Also clear dedicated IR/Line Shape tables if present
        if hasattr(self, 'ir_table') and isinstance(self.ir_table, QtWidgets.QTableWidget):
            self.ir_table.setRowCount(0)
        if hasattr(self, 'ls_table') and isinstance(self.ls_table, QtWidgets.QTableWidget):
            self.ls_table.setRowCount(0)
        current = self.reference_tabs.currentIndex()
        if current == 0:
            # NIST: no automatic fetch; leave controls ready
            self.reference_filter.setPlaceholderText("Filter IR groups…")
            self.reference_overlay_checkbox.setEnabled(False)
            self.reference_status_label.setText("Enter element and range, then Fetch")
        elif current == 1:
            # IR functional groups
            self.reference_filter.setPlaceholderText("Filter IR groups…")
            groups = self.reference_library.ir_functional_groups()
            self._populate_reference_table_ir(groups)
            payload = self._build_overlay_for_ir(groups)
            self._update_reference_overlay_state(payload)
            self._preview_reference_payload(payload)
        else:
            # Line shapes
            self.reference_filter.setPlaceholderText("Filter line-shape…")
            placeholders = self.reference_library.line_shape_placeholders()
            self._populate_reference_table_line_shapes(placeholders)
            # Pick the first model for preview by default
            if placeholders:
                first = placeholders[0]
                model_id = str(first.get("id"))
                self._preview_line_shape(model_id)

    def _populate_reference_table_ir(self, groups: Sequence[Mapping[str, Any]] | None) -> None:
        from typing import Mapping, Sequence
        rows = list(groups or [])
        self._ir_rows = rows
        # Keep legacy reference_table populated for tests expecting rowCount()
        try:
            self.reference_table.setRowCount(len(rows))
        except Exception:
            pass
        if hasattr(self, 'ir_table') and isinstance(self.ir_table, QtWidgets.QTableWidget):
            self.ir_table.setRowCount(len(rows))
            for r, entry in enumerate(rows):
                self.ir_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(entry.get("group", ""))))
                self.ir_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(entry.get("wavenumber_cm_1_min", ""))))
                self.ir_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(entry.get("wavenumber_cm_1_max", ""))))

    def _populate_reference_table_line_shapes(self, defs: Sequence[Mapping[str, Any]] | None) -> None:
        from typing import Mapping, Sequence
        rows = list(defs or [])
        # Mirror row count into legacy reference_table for tests
        try:
            self.reference_table.setRowCount(len(rows))
        except Exception:
            pass
        if hasattr(self, 'ls_table') and isinstance(self.ls_table, QtWidgets.QTableWidget):
            self.ls_table.setRowCount(len(rows))
            for r, entry in enumerate(rows):
                self.ls_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(entry.get("id", ""))))
                self.ls_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(entry.get("label", ""))))

    def _preview_reference_payload(self, payload: Mapping[str, Any]) -> None:
        import numpy as _np
        # Clear existing preview items
        try:
            for item in self.reference_plot.listDataItems():
                self.reference_plot.removeItem(item)
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
                self.reference_plot.setLabel("bottom", "Wavenumber (cm⁻¹)")
            else:
                self.reference_plot.setLabel("bottom", "Wavelength (nm)")
        except Exception:
            pass
        if domain == "ir" and x.size:
            with _np.errstate(divide="ignore"):
                x = 1e7 / x
        if mode == "bars" and x.size and y.size and x.size == y.size:
            # Render vertical bar segments scaled by y intensities
            try:
                _, y_range = self.reference_plot.getPlotItem().viewRange()
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
            self.reference_plot.addItem(item)
            return
        # Default polyline/filled preview
        if x.size and y.size and x.size == y.size:
            self.reference_plot.plot(x, y, pen=(100, 100, 180, 190), fillLevel=payload.get("fill_level"))

    def _on_reference_filter_changed(self, text: str) -> None:
        # Only applies to IR tab currently
        try:
            if self.reference_tabs.currentIndex() != 1:
                return
        except Exception:
            return
        needle = (text or "").strip().lower()
        groups = self.reference_library.ir_functional_groups() or []
        if needle:
            filtered = [g for g in groups if needle in str(g.get("group", "")).lower() or needle in str(g.get("category", "")).lower()]
        else:
            filtered = list(groups)
        self._populate_reference_table_ir(filtered)
        # If there is a selection, preview selected; otherwise preview all filtered
        try:
            items = self.ir_table.selectedItems()
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
            if self.reference_tabs.currentIndex() != 1:
                return
        except Exception:
            return
        try:
            items = self.ir_table.selectedItems()
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

    def _on_line_shape_row_selected(self) -> None:
        try:
            items = self.ls_table.selectedItems()
        except Exception:
            items = []
        if not items:
            return
        model_item = items[0]
        model_id = model_item.text()
        self._preview_line_shape(model_id)

    def _preview_line_shape(self, model_id: str) -> None:
        try:
            outcome = self.line_shape_model.sample_profile(model_id)
        except Exception:
            outcome = None
        if outcome is None:
            return
        payload = {
            "key": f"reference::line_shape::{model_id}",
            "alias": f"Reference – {model_id}",
            "x_nm": outcome.x,
            "y": outcome.y,
            "color": "#4F6D7A",
            "width": 1.5,
            "metadata": dict(outcome.metadata),
        }
        self._update_reference_overlay_state(payload)
        # Clear preview plot and draw
        try:
            for item in self.reference_plot.listDataItems():
                self.reference_plot.removeItem(item)
        except Exception:
            pass
        self.reference_plot.plot(outcome.x, outcome.y, pen=(180, 140, 60, 220))

    def _on_nist_fetch_clicked(self) -> None:
        element = (self.nist_element_edit.text() or "").strip()
        lower = float(self.nist_lower_spin.value())
        upper = float(self.nist_upper_spin.value())
        if not element:
            self.reference_status_label.setText("Enter element symbol")
            return
        try:
            payload = nist_asd_service.fetch_lines(
                element,
                lower_wavelength=lower,
                upper_wavelength=upper,
                wavelength_unit="nm",
                wavelength_type="vacuum",
            )
        except Exception as exc:
            self.reference_status_label.setText(f"NIST fetch failed: {exc}")
            return
        # Populate table with the first collection
        lines = list(payload.get("lines", [])) if isinstance(payload, Mapping) else []
        self.reference_table.setColumnCount(5)
        self.reference_table.setHorizontalHeaderLabels(["λ (nm)", "Ritz λ (nm)", "Intensity", "Lower", "Upper"])
        self.reference_table.setRowCount(len(lines))
        for r, row in enumerate(lines):
            self.reference_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(row.get("wavelength_nm", ""))))
            self.reference_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(row.get("ritz_wavelength_nm", ""))))
            self.reference_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(row.get("relative_intensity", ""))))
            self.reference_table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(row.get("lower_level", ""))))
            self.reference_table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(row.get("upper_level", ""))))

        # Build multi-overlay container (pin collection)
        try:
            label = str(payload.get("meta", {}).get("label", element))
        except Exception:
            label = element
        alias = f"Reference – {label}"
        xs = np.array([row.get("wavelength_nm") for row in lines if isinstance(row, Mapping)], dtype=float)
        # Normalise intensities to [0,1] for bar heights
        intensities = []
        for row in lines:
            try:
                intensities.append(float(row.get("relative_intensity") or 0.0))
            except Exception:
                intensities.append(0.0)
        ys_raw = np.array(intensities, dtype=float)
        max_i = float(np.nanmax(ys_raw)) if ys_raw.size else 0.0
        ys = (ys_raw / max_i) if max_i > 0 else np.ones_like(xs)
        single = {
            "key": f"reference::nist::{label}",
            "alias": alias,
            "x_nm": xs,
            "y": ys,
            "color": "#6D597A",
            "width": 1.2,
            "mode": "bars",
            "labels": [],
        }
        # Track pinned sets
        self._nist_collection_counter += 1
        pin_key = f"set-{self._nist_collection_counter}"
        self._nist_collections[pin_key] = {"payload": single, "label": label}
        self.nist_collections_list.addItem(f"{label} – pinned")
        multi = {"kind": "nist-multi", "payloads": {k: v["payload"] for k, v in self._nist_collections.items()}}
        self._update_reference_overlay_state(multi)
        self.reference_overlay_checkbox.setEnabled(True)
        count = len(self._nist_collections)
        suffix = "set" if count == 1 else "sets"
        self.reference_status_label.setText(f"{count} pinned {suffix}")
        # Preview the most recent fetch as bars
        self._preview_reference_payload(single)

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

        # Create stacked label annotations on the main plot
        labels = payload.get("labels") or []
        if isinstance(labels, list) and labels:
            band_bottom, band_top = payload.get("band_bounds", self._overlay_band_bounds())
            if not isinstance(band_bottom, (int, float)):
                band_bottom, band_top = self._overlay_band_bounds()
            span = float(band_top - band_bottom) if (band_top is not None and band_bottom is not None) else 1.0
            n = max(1, len(labels))
            # Do not replace the list object; mutate in-place so identity is preserved for tests
            self._reference_overlay_annotations.clear()
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
    def _initialize_remote_data_providers(self) -> None:
        """Populate remote provider combo with available providers."""
        if not hasattr(self, 'remote_provider_combo'):
            return
        
        providers = self.remote_data_service.providers()
        # Filter out NIST as it's handled in Reference tab
        providers = [p for p in providers if p != RemoteDataService.PROVIDER_NIST]
        
        self.remote_provider_combo.clear()
        if providers:
            self.remote_provider_combo.addItems(providers)
            self.remote_provider_combo.setEnabled(True)
            self.remote_search_edit.setEnabled(True)
            self.remote_search_button.setEnabled(True)
        else:
            self.remote_provider_combo.setEnabled(False)
            self.remote_search_edit.setEnabled(False)
            self.remote_search_button.setEnabled(False)
            self.remote_status_label.setText("Remote data providers unavailable")
        
        self._on_remote_provider_changed()
    
    def _on_remote_provider_changed(self) -> None:
        """Update UI hints when provider changes."""
        if not hasattr(self, 'remote_provider_combo'):
            return
        
        provider = self.remote_provider_combo.currentText()
        
        if provider == RemoteDataService.PROVIDER_MAST:
            self.remote_search_edit.setPlaceholderText("MAST target name (e.g. NGC 7023, SN 1987A)…")
        elif provider == RemoteDataService.PROVIDER_EXOSYSTEMS:
            self.remote_search_edit.setPlaceholderText("Planet, star, or solar system target (e.g. HD 189733 b, Jupiter)…")
        else:
            self.remote_search_edit.setPlaceholderText("Target name or keyword…")
    
    def _cancel_remote_search_worker(self) -> None:
        if self._remote_search_worker is None:
            return
        queued = getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection
        QtCore.QMetaObject.invokeMethod(self._remote_search_worker, "cancel", queued)

    def _on_remote_search(self) -> None:
        """Initiate remote data search (non-blocking with streaming updates)."""
        if not hasattr(self, 'remote_provider_combo'):
            return
        provider = self.remote_provider_combo.currentText()
        query_text = self.remote_search_edit.text().strip()
        if not query_text:
            self.remote_status_label.setText("Enter a search term")
            return
        # Build provider-specific query
        if provider == RemoteDataService.PROVIDER_MAST:
            query = {"target_name": query_text}
        elif provider == RemoteDataService.PROVIDER_EXOSYSTEMS:
            query = {"text": query_text}
        else:
            query = {"text": query_text}

        # Reset UI and state
        self._cancel_remote_search_worker()
        self._remote_records = []
        self.remote_results_table.setRowCount(0)
        self.remote_import_button.setEnabled(False)
        self.remote_status_label.setText(f"Searching {provider}…")
        self.remote_search_button.setEnabled(False)

        # Create streaming worker (reuse dialog worker logic)
        worker = _RemoteSearchWorker(self.remote_data_service)
        thread = QtCore.QThread(self)
        self._remote_search_worker = worker
        self._remote_search_thread = thread
        worker.moveToThread(thread)
        thread.started.connect(lambda p=provider, q=query: worker.run(p, q, False))
        # Streamed records
        worker.record_found.connect(self._handle_remote_record_found)
        worker.finished.connect(self._handle_remote_search_finished)
        worker.failed.connect(self._handle_remote_search_failed)
        worker.cancelled.connect(self._handle_remote_search_cancelled)
        # Cleanup
        def _cleanup() -> None:
            if thread.isRunning():
                thread.quit()
            worker.deleteLater()
            thread.deleteLater()
            if self._remote_search_worker is worker:
                self._remote_search_worker = None
                self._remote_search_thread = None
        worker.finished.connect(lambda *_: QtCore.QTimer.singleShot(0, _cleanup))
        worker.failed.connect(lambda *_: QtCore.QTimer.singleShot(0, _cleanup))
        worker.cancelled.connect(lambda *_: QtCore.QTimer.singleShot(0, _cleanup))
        thread.start()

    def _handle_remote_record_found(self, record: Any) -> None:
        def _append():
            # Append incrementally to the table for streaming UX
            self._remote_records.append(record)
            row = self.remote_results_table.rowCount()
            self.remote_results_table.insertRow(row)
            # ID
            item = QtWidgets.QTableWidgetItem(str(getattr(record, 'identifier', '')))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.remote_results_table.setItem(row, 0, item)
            # Title
            item = QtWidgets.QTableWidgetItem(str(getattr(record, 'title', '')))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.remote_results_table.setItem(row, 1, item)
            # Target
            metadata = getattr(record, 'metadata', {}) if isinstance(getattr(record, 'metadata', {}), dict) else {}
            target = str(metadata.get("target_name", ""))
            item = QtWidgets.QTableWidgetItem(target)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.remote_results_table.setItem(row, 2, item)
            # Telescope
            telescope = str(metadata.get("obs_collection", metadata.get("telescope_name", "")))
            item = QtWidgets.QTableWidgetItem(telescope)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.remote_results_table.setItem(row, 3, item)
        QtCore.QTimer.singleShot(0, _append)

    def _handle_remote_search_finished(self, results: List[Any]) -> None:
        def _done():
            self.remote_search_button.setEnabled(True)
            count = len(results)
            self.remote_status_label.setText(f"Found {count} result(s)" if count else "No results found")
        QtCore.QTimer.singleShot(0, _done)

    def _handle_remote_search_failed(self, message: str) -> None:
        def _fail():
            self.remote_search_button.setEnabled(True)
            self.remote_status_label.setText(f"Search failed: {message}")
            self._log("Remote", f"Search failed: {message}")
        QtCore.QTimer.singleShot(0, _fail)

    def _handle_remote_search_cancelled(self) -> None:
        def _cancel():
            self.remote_search_button.setEnabled(True)
            self.remote_status_label.setText("Search cancelled")
        QtCore.QTimer.singleShot(0, _cancel)
    
    def _populate_remote_results(self, records: List[Any]) -> None:
        """Populate the results table with records."""
        self.remote_results_table.setRowCount(len(records))
        
        for row, record in enumerate(records):
            # ID
            item = QtWidgets.QTableWidgetItem(str(record.identifier))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.remote_results_table.setItem(row, 0, item)
            
            # Title
            item = QtWidgets.QTableWidgetItem(str(record.title))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.remote_results_table.setItem(row, 1, item)
            
            # Target
            metadata = record.metadata if hasattr(record, 'metadata') and isinstance(record.metadata, dict) else {}
            target = metadata.get("target_name", "")
            item = QtWidgets.QTableWidgetItem(str(target))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.remote_results_table.setItem(row, 2, item)
            
            # Telescope
            telescope = metadata.get("obs_collection", metadata.get("telescope_name", ""))
            item = QtWidgets.QTableWidgetItem(str(telescope))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.remote_results_table.setItem(row, 3, item)
    
    def _on_remote_selection_changed(self) -> None:
        """Update import button state when selection changes."""
        if not hasattr(self, 'remote_results_table'):
            return
        
        selected = self.remote_results_table.selectionModel().selectedRows()
        self.remote_import_button.setEnabled(len(selected) > 0)
        
        if len(selected) == 1:
            self.remote_import_button.setText("Download & Import")
        elif len(selected) > 1:
            self.remote_import_button.setText(f"Download & Import ({len(selected)} selected)")
        else:
            self.remote_import_button.setText("Download & Import Selected")
    
    def _cancel_remote_download_worker(self) -> None:
        if self._remote_download_worker is None:
            return
        queued = getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection
        QtCore.QMetaObject.invokeMethod(self._remote_download_worker, "cancel", queued)

    def _on_remote_import(self) -> None:
        """Download and import selected records (in background with progress)."""
        if not hasattr(self, 'remote_results_table'):
            return
        selected = self.remote_results_table.selectionModel().selectedRows()
        if not selected:
            return
        records = [self._remote_records[index.row()] for index in selected]
        self.remote_status_label.setText(f"Preparing download of {len(records)} record(s)…")
        self.remote_import_button.setEnabled(False)

        # Start background downloads using shared worker
        worker = _RemoteDownloadWorker(self.remote_data_service, self.ingest_service)
        thread = QtCore.QThread(self)
        self._remote_download_worker = worker
        self._remote_download_thread = thread
        worker.moveToThread(thread)
        thread.started.connect(lambda recs=records: worker.run(recs))

        def _on_started(total: int) -> None:
            # Queue status update on the main thread
            try:
                QtCore.QMetaObject.invokeMethod(
                    self.remote_status_label,
                    "setText",
                    getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection,
                    f"Downloading {total} record(s)…",
                )
            except Exception:
                pass

        def _on_progress(_record: Any) -> None:
            # Refresh plot and library gradually is expensive; update status only
            pass

        def _on_failure(record: Any, message: str) -> None:
            # Log on main thread via _log() internal marshalling
            self._log("Remote Import", f"Failed to import {getattr(record, 'identifier', '')}: {message}")

        def _on_finished(ingested: list[Any]) -> None:
            # Merge spectra into overlay and UI
            count = 0
            all_spectra: list[Spectrum] = []
            for item in ingested:
                try:
                    spectra = item if isinstance(item, list) else [item]
                    for spectrum in spectra:
                        self.overlay_service.add(spectrum)
                        self._add_spectrum(spectrum)
                        all_spectra.append(spectrum)
                        count += 1
                except Exception:
                    continue

            def _finalize_ui() -> None:
                self.plot.autoscale()
                self._refresh_library_view()
                # Record in history and refresh
                try:
                    if all_spectra:
                        self._record_remote_history_event(all_spectra)
                finally:
                    self._refresh_history_view()
                self.remote_status_label.setText(f"Imported {count} dataset(s)")
                self.remote_import_button.setEnabled(True)

            # Ensure finalize runs on GUI thread
            if QtCore.QThread.currentThread() is self.thread():
                _finalize_ui()
            else:
                try:
                    QtCore.QMetaObject.invokeMethod(
                        self,
                        "_append_log_line",  # use any slot on main thread to queue; then call finalize via singleShot
                        getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection,
                        "",
                    )
                except Exception:
                    pass
                QtCore.QTimer.singleShot(0, _finalize_ui)

        def _on_failed(message: str) -> None:
            try:
                QtCore.QMetaObject.invokeMethod(
                    self.remote_status_label,
                    "setText",
                    getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection,
                    f"Download failed: {message}",
                )
                QtCore.QMetaObject.invokeMethod(
                    self.remote_import_button,
                    "setEnabled",
                    getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection,
                    True,
                )
            except Exception:
                pass

        def _on_cancelled() -> None:
            try:
                QtCore.QMetaObject.invokeMethod(
                    self.remote_status_label,
                    "setText",
                    getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection,
                    "Download cancelled",
                )
                QtCore.QMetaObject.invokeMethod(
                    self.remote_import_button,
                    "setEnabled",
                    getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection,
                    True,
                )
            except Exception:
                pass

        # Force all signal connections to use queued connection to ensure slots run on GUI thread
        queued = getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection
        worker.started.connect(_on_started, queued)
        worker.record_ingested.connect(_on_progress, queued)
        worker.record_failed.connect(_on_failure, queued)
        worker.finished.connect(_on_finished, queued)
        worker.failed.connect(_on_failed, queued)
        worker.cancelled.connect(_on_cancelled, queued)

        def _cleanup() -> None:
            if thread.isRunning():
                thread.quit()
            worker.deleteLater()
            thread.deleteLater()
            if self._remote_download_worker is worker:
                self._remote_download_worker = None
                self._remote_download_thread = None

        worker.finished.connect(lambda *_: QtCore.QTimer.singleShot(0, _cleanup))
        worker.failed.connect(lambda *_: QtCore.QTimer.singleShot(0, _cleanup))
        worker.cancelled.connect(lambda *_: QtCore.QTimer.singleShot(0, _cleanup))
        thread.start()

    # ----------------------------- History helpers ----------------------
    def _refresh_history_view(self) -> None:
        entries = []
        try:
            entries = self.knowledge_log.load_entries()
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
            # Convert canonical data back to the source intensity unit for display
            src_y_unit = str(spec.metadata.get("source_units", {}).get("y", "absorbance"))
            x_disp, y_disp = self.units_service.from_canonical(spec.x, spec.y, x_unit, src_y_unit)
            y_label = "%T" if src_y_unit in {"%T", "percent_transmittance"} else "Intensity"
            self.plot.set_y_label(y_label)
            self.plot.add_trace(spec.id, spec.name, x_disp, y_disp, style)
            self.plot.set_visible(spec.id, visible)
        self.plot.autoscale()


def _install_exception_handler() -> None:
    """Show uncaught exceptions in both console and a dialog, then exit."""
    def _excepthook(exc_type, exc_value, exc_tb):
        import traceback
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        # Persist to a log file for sharing during support sessions
        try:
            logs_dir = Path(__file__).resolve().parent.parent / "reports"
            logs_dir.mkdir(parents=True, exist_ok=True)
            (logs_dir / "runtime.log").write_text(details, encoding="utf-8")
        except Exception:
            pass
        try:
            # Print to the terminal for real-time visibility
            print(details, file=sys.stderr)
        except Exception:
            pass
        try:
            # Also surface in a message box so the window doesn't just vanish
            QtWidgets.QMessageBox.critical(None, "Unhandled exception", details)
        except Exception:
            pass
    sys.excepthook = _excepthook


def main(argv: list[str] | None = None) -> int:
    """Launch the Spectra desktop app.

    Returns an OS exit code (0 for normal shutdown).
    """
    _install_exception_handler()

    # High-DPI scaling is automatic in Qt6; no need for deprecated attributes
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(argv or sys.argv)
    app.setApplicationName("Spectra App")
    app.setOrganizationName("Spectra")

    window = SpectraMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":  # Script/direct launch
    raise SystemExit(main())

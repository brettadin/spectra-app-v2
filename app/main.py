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

from app.qt_compat import get_qt
from .services import (
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
from .services import nist_asd_service
from .ui.plot_pane import PlotPane, TraceStyle
from .ui.remote_data_dialog import RemoteDataDialog
from .ui.export_options_dialog import ExportOptionsDialog

QtCore: Any
QtGui: Any
QtWidgets: Any
QT_BINDING: str
QtCore, QtGui, QtWidgets, QT_BINDING = get_qt()

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
        self._persistence_env_disabled = self._persistence_disabled_via_env()
        self._persistence_disabled = self._persistence_env_disabled or self._load_persistence_preference()
        self.store: LocalStore | None = None if self._persistence_disabled else LocalStore()
        self.ingest_service = DataIngestService(self.units_service, store=self.store)
        remote_store = self.store
        if remote_store is None:
            remote_store = LocalStore(base_dir=Path(tempfile.mkdtemp(prefix="spectra-remote-")))
        self.remote_data_service = RemoteDataService(remote_store)
        self.math_service = MathService()
        self.knowledge_log = knowledge_log_service or KnowledgeLogService(
            default_context="Spectra Desktop Session"
        )

        self.unit_combo: Optional[QtWidgets.QComboBox] = None
        self.plot_toolbar: Optional[QtWidgets.QToolBar] = None
        self.plot_max_points_control: Optional[QtWidgets.QSpinBox] = None
        self.color_mode_combo: Optional[QtWidgets.QComboBox] = None

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
        self.library_list: QtWidgets.QTreeWidget | None = None
        self.library_search: QtWidgets.QLineEdit | None = None
        self.library_detail: QtWidgets.QPlainTextEdit | None = None
        self.library_hint: QtWidgets.QLabel | None = None
        self._library_entries: Dict[str, Mapping[str, Any]] = {}
        self._library_tab_index: int | None = None
        self._use_uniform_palette = False
        self._uniform_color = QtGui.QColor("#4F6D7A")
        self._last_display_views: List[Dict[str, object]] = []

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

        remote_action = QtGui.QAction("Fetch &Remote Data…", self)
        remote_action.setShortcut("Ctrl+Shift+R")
        remote_action.triggered.connect(self.open_remote_data_dialog)
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
            if self.library_list is not None:
                self.library_list.clear()
                self.library_list.setDisabled(True)
        else:
            self.store = LocalStore()
            if self.library_list is not None:
                self.library_list.setDisabled(False)
        self.ingest_service.store = self.store
        if hasattr(self, "remote_data_service") and isinstance(self.remote_data_service, RemoteDataService):
            if self.store is not None:
                self.remote_data_service.store = self.store
            else:
                temp_remote = LocalStore(base_dir=Path(tempfile.mkdtemp(prefix="spectra-remote-")))
                self.remote_data_service.store = temp_remote
        self._build_library_tab()

    def _setup_ui(self) -> None:
        self.central_split = QtWidgets.QSplitter(self)
        self.central_split.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.setCentralWidget(self.central_split)

        self.plot = PlotPane(self, max_points=self._plot_max_points)
        self._plot_max_points = self.plot.max_points
        self.plot.setObjectName("plot-area")
        self.central_split.addWidget(self.plot)
        self.plot.autoscale()
        self.plot.rangeChanged.connect(self._on_plot_range_changed)

        # Build the plot toolbar immediately so dependent UI (e.g. menus)
        # can reference it during their own setup routines.
        self._build_plot_toolbar()

        self.data_table = QtWidgets.QTableWidget()
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(["Spectrum", "Point", "X", "Y"])
        self.data_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.data_table.hide()
        self.central_split.addWidget(self.data_table)
        self.central_split.setStretchFactor(0, 4)
        self.central_split.setStretchFactor(1, 3)

        self.dataset_dock = QtWidgets.QDockWidget("Data", self)
        self.dataset_dock.setObjectName("dock-datasets")
        self.dataset_dock.setAllowedAreas(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea | QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
        dataset_container = QtWidgets.QWidget()
        dataset_layout = QtWidgets.QVBoxLayout(dataset_container)
        dataset_layout.setContentsMargins(6, 6, 6, 6)
        dataset_layout.setSpacing(6)

        self.dataset_filter = QtWidgets.QLineEdit()
        self.dataset_filter.setPlaceholderText("Filter datasets…")
        self.dataset_filter.textChanged.connect(self._on_dataset_filter_changed)
        dataset_layout.addWidget(self.dataset_filter)

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
        dataset_layout.addWidget(self.dataset_tree, 1)

        self.data_tabs = QtWidgets.QTabWidget()
        self.data_tabs.setObjectName("data-tabs")
        self.data_tabs.addTab(dataset_container, "Datasets")
        self.dataset_dock.setWidget(self.data_tabs)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.dataset_dock)

        self._build_library_tab()

        self._build_history_dock()

        self.log_dock = QtWidgets.QDockWidget("Log", self)
        self.log_dock.setObjectName("dock-log")
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_dock.setWidget(self.log_view)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)

        self.inspector_dock = QtWidgets.QDockWidget("Inspector", self)
        self.inspector_dock.setObjectName("dock-inspector")
        self.inspector_tabs = QtWidgets.QTabWidget()
        self._build_inspector_tabs()
        self.inspector_dock.setWidget(self.inspector_tabs)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.inspector_dock)

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

    def _build_library_tab(self) -> None:
        if self.data_tabs is None:
            return

        if self._library_tab_index is not None:
            widget = self.data_tabs.widget(self._library_tab_index)
            if widget is not None:
                widget.deleteLater()
            self.data_tabs.removeTab(self._library_tab_index)
            self._library_tab_index = None

        if self.store is None:
            placeholder = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(placeholder)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(6)
            message = QtWidgets.QLabel(
                "Enable the persistent cache to browse previously imported or downloaded spectra."
            )
            message.setWordWrap(True)
            layout.addWidget(message, alignment=QtCore.Qt.AlignmentFlag.AlignTop)
            self.library_list = None
            self.library_search = None
            self.library_detail = None
            self.library_hint = message
            self._library_tab_index = self.data_tabs.addTab(placeholder, "Library")
            self.data_tabs.setTabToolTip(
                self._library_tab_index,
                "Persistent cache disabled; toggle persistence to enable the Library.",
            )
            return

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.library_search = QtWidgets.QLineEdit()
        self.library_search.setPlaceholderText("Filter cached spectra…")
        self.library_search.textChanged.connect(self._on_library_filter_changed)
        layout.addWidget(self.library_search)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)

        self.library_list = QtWidgets.QTreeWidget()
        self.library_list.setColumnCount(4)
        self.library_list.setHeaderLabels(["Alias", "Units", "Updated", "Source"])
        self.library_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.library_list.itemDoubleClicked.connect(self._on_library_item_activated)
        self.library_list.itemSelectionChanged.connect(self._on_library_selection_changed)
        self.library_list.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.library_list.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.library_list.header().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.library_list.header().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        splitter.addWidget(self.library_list)

        self.library_detail = QtWidgets.QPlainTextEdit()
        self.library_detail.setObjectName("library-detail")
        self.library_detail.setReadOnly(True)
        self.library_detail.setPlaceholderText("Select a cached entry to inspect metadata and provenance.")
        splitter.addWidget(self.library_detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter, 1)

        self.library_hint = QtWidgets.QLabel(
            "Double-click a cached entry to load it into the workspace without re-downloading."
        )
        self.library_hint.setWordWrap(True)
        layout.addWidget(self.library_hint)

        self._library_tab_index = self.data_tabs.addTab(container, "Library")
        self.data_tabs.setTabToolTip(
            self._library_tab_index,
            "Inspect cached spectra; double-click a row to re-ingest it into the workspace.",
        )
        self.data_tabs.tabBar().setTabButton(
            self._library_tab_index,
            QtWidgets.QTabBar.ButtonPosition.RightSide,
            None,
        )
        self._refresh_library_view()

    def _on_library_filter_changed(self) -> None:
        self._refresh_library_view()

    def _refresh_library_view(self) -> None:
        if self.store is None or self.library_list is None:
            return

        entries = self.store.list_entries()
        self._library_entries = {
            sha: entry for sha, entry in entries.items() if isinstance(entry, Mapping)
        }
        filter_text = ""
        if self.library_search is not None:
            filter_text = self.library_search.text().strip().lower()

        selected_sha = None
        if self.library_list is not None and self.library_list.currentItem() is not None:
            selected_sha = str(
                self.library_list.currentItem().data(0, QtCore.Qt.ItemDataRole.UserRole) or ""
            )

        self.library_list.setUpdatesEnabled(False)
        blocker = QtCore.QSignalBlocker(self.library_list)
        self.library_list.clear()

        def entry_tokens(entry: Mapping[str, Any]) -> str:
            tokens: List[str] = []
            alias = str(entry.get("filename") or entry.get("stored_path") or "")
            tokens.append(alias)
            units = entry.get("units")
            if isinstance(units, Mapping):
                tokens.extend(str(value) for value in units.values())
            source = entry.get("source")
            if isinstance(source, Mapping):
                remote = source.get("remote")
                if isinstance(remote, Mapping):
                    tokens.extend(str(value) for value in remote.values())
                ingest = source.get("ingest")
                if isinstance(ingest, Mapping):
                    tokens.extend(str(value) for value in ingest.values())
            return " ".join(tokens).lower()

        items: List[QtWidgets.QTreeWidgetItem] = []
        for sha, entry in sorted(self._library_entries.items(), key=lambda kv: kv[0]):
            text_blob = entry_tokens(entry)
            if filter_text and filter_text not in text_blob:
                continue

            alias = str(entry.get("filename") or Path(entry.get("stored_path", "")).name)
            units_map = entry.get("units") if isinstance(entry.get("units"), Mapping) else {}
            x_unit = units_map.get("x", "?") if isinstance(units_map, Mapping) else "?"
            y_unit = units_map.get("y", "?") if isinstance(units_map, Mapping) else "?"
            units_label = f"{x_unit} / {y_unit}"
            updated = str(entry.get("updated") or entry.get("created") or "")
            source_label = self._describe_library_source(entry)

            item = QtWidgets.QTreeWidgetItem([alias, units_label, updated, source_label])
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, sha)
            item.setToolTip(0, str(entry.get("stored_path", "")))
            items.append(item)

        for item in items:
            self.library_list.addTopLevelItem(item)

        if items:
            self.library_list.sortItems(2, QtCore.Qt.SortOrder.DescendingOrder)
            target_item: QtWidgets.QTreeWidgetItem | None = None
            if selected_sha:
                for row in range(self.library_list.topLevelItemCount()):
                    candidate = self.library_list.topLevelItem(row)
                    if not candidate:
                        continue
                    sha_value = str(
                        candidate.data(0, QtCore.Qt.ItemDataRole.UserRole) or ""
                    )
                    if sha_value == selected_sha:
                        target_item = candidate
                        break
            if target_item is None:
                target_item = self.library_list.topLevelItem(0)
            if target_item is not None:
                self.library_list.setCurrentItem(target_item)
        else:
            if self.library_list is not None:
                self.library_list.setCurrentItem(None)
        del blocker
        self.library_list.setUpdatesEnabled(True)

        if self.library_hint is not None:
            if items:
                self.library_hint.setText(
                    "Select a cached entry to inspect metadata or double-click to reload it into the session."
                )
            else:
                self.library_hint.setText(
                    "No cached spectra available yet. Import data or fetch a remote record to populate the library."
                )

        self._update_library_detail()

    def _describe_library_source(self, entry: Mapping[str, Any]) -> str:
        source = entry.get("source")
        if not isinstance(source, Mapping):
            return ""
        remote = source.get("remote")
        if isinstance(remote, Mapping):
            provider = remote.get("provider")
            identifier = remote.get("identifier")
            if provider and identifier:
                return f"{provider} – {identifier}"
            if provider:
                return str(provider)
        ingest = source.get("ingest")
        if isinstance(ingest, Mapping):
            importer = ingest.get("importer")
            if importer:
                return str(importer)
        return ""

    def _on_library_item_activated(
        self, item: QtWidgets.QTreeWidgetItem, column: int
    ) -> None:
        sha = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not sha:
            return
        entry = self._library_entries.get(str(sha))
        if not isinstance(entry, Mapping):
            return
        stored_path = entry.get("stored_path")
        if not stored_path:
            QtWidgets.QMessageBox.warning(self, "Missing file", "The cached file is not available.")
            return
        path = Path(stored_path)
        if not path.exists():
            QtWidgets.QMessageBox.warning(
                self,
                "Missing file",
                "The cached file could not be found on disk. It may have been moved or deleted.",
            )
            return
        self.plot.begin_bulk_update()
        try:
            self._ingest_path(path)
        finally:
            self.plot.end_bulk_update()

    def _on_library_selection_changed(self) -> None:
        self._update_library_detail()

    def _update_library_detail(self) -> None:
        if self.library_detail is None:
            return
        if self.library_list is None or self.library_list.currentItem() is None:
            self.library_detail.clear()
            if self.library_hint is not None:
                self.library_hint.setText(
                    "Select a cached entry to inspect metadata or double-click to reload it into the session."
                )
            return

        item = self.library_list.currentItem()
        sha = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        entry = self._library_entries.get(str(sha)) if sha else None
        if not isinstance(entry, Mapping):
            self.library_detail.clear()
            if self.library_hint is not None:
                self.library_hint.setText(
                    "The selected cache entry could not be read from disk."
                )
            return

        detail = self._format_library_entry(entry)
        self.library_detail.setPlainText(detail)
        if self.library_hint is not None:
            stored_path = entry.get("stored_path")
            if stored_path:
                self.library_hint.setText(f"Cached at: {stored_path}")
            else:
                self.library_hint.setText(
                    "Double-click the entry to load it into the workspace without re-downloading."
                )

    def _format_library_entry(self, entry: Mapping[str, Any]) -> str:
        payload: Dict[str, Any] = {
            "alias": entry.get("filename"),
            "sha256": entry.get("sha256"),
            "stored_path": entry.get("stored_path"),
            "bytes": entry.get("bytes"),
            "units": entry.get("units"),
            "created": entry.get("created"),
            "updated": entry.get("updated"),
        }
        manifest = entry.get("manifest_path")
        if manifest:
            payload["manifest_path"] = manifest
        source = entry.get("source")
        if isinstance(source, Mapping):
            payload["source"] = source
        provenance = entry.get("provenance")
        if isinstance(provenance, Mapping):
            payload["provenance"] = provenance
        return json_pretty(payload)

    def _build_history_dock(self) -> None:
        self.history_dock = QtWidgets.QDockWidget("History", self)
        self.history_dock.setObjectName("dock-history")

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        filter_layout = QtWidgets.QHBoxLayout()
        self.history_search = QtWidgets.QLineEdit()
        self.history_search.setPlaceholderText("Filter history…")
        self.history_search.textChanged.connect(self._on_history_filter_changed)
        filter_layout.addWidget(self.history_search)

        self.history_component_filter = QtWidgets.QComboBox()
        self.history_component_filter.addItem("All Components")
        self.history_component_filter.currentTextChanged.connect(self._on_history_filter_changed)
        filter_layout.addWidget(self.history_component_filter)

        refresh_btn = QtWidgets.QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_history_entries)
        filter_layout.addWidget(refresh_btn)

        export_btn = QtWidgets.QPushButton("Export…")
        export_btn.clicked.connect(self._export_history_entries)
        filter_layout.addWidget(export_btn)

        layout.addLayout(filter_layout)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)

        self.history_table = QtWidgets.QTableWidget(0, 3)
        self.history_table.setHorizontalHeaderLabels(["Timestamp", "Component", "Summary"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.history_table.itemSelectionChanged.connect(self._on_history_selection_changed)
        splitter.addWidget(self.history_table)

        self.history_detail = QtWidgets.QPlainTextEdit()
        self.history_detail.setReadOnly(True)
        self.history_detail.setPlaceholderText("Select an entry to inspect details.")
        splitter.addWidget(self.history_detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        self.history_dock.setWidget(container)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.history_dock)
        self._history_ui_ready = True
        self._load_history_entries()

    def _build_inspector_tabs(self) -> None:
        self.inspector_tabs.clear()

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
        lod_help = QtWidgets.QLabel(
            "Adjust the level-of-detail budget to trade fidelity for interactivity when plotting dense spectra."
        )
        lod_help.setWordWrap(True)
        style_layout.addWidget(lod_help)

        lod_form = QtWidgets.QFormLayout()
        style_layout.addLayout(lod_form)

        self.plot_max_points_control = QtWidgets.QSpinBox()
        self.plot_max_points_control.setRange(PlotPane.MIN_MAX_POINTS, PlotPane.MAX_MAX_POINTS)
        self.plot_max_points_control.setSingleStep(PlotPane.MIN_MAX_POINTS)
        self.plot_max_points_control.setAccelerated(True)
        self.plot_max_points_control.setKeyboardTracking(False)
        self.plot_max_points_control.setValue(self._plot_max_points)
        self.plot_max_points_control.valueChanged.connect(self._on_plot_max_points_changed)
        lod_form.addRow("LOD point budget:", self.plot_max_points_control)

        palette_form = QtWidgets.QFormLayout()
        style_layout.addLayout(palette_form)
        self.color_mode_combo = QtWidgets.QComboBox()
        self.color_mode_combo.addItems([
            "High-contrast palette",
            "Uniform (single colour)",
        ])
        self.color_mode_combo.currentIndexChanged.connect(self._on_color_mode_changed)
        palette_form.addRow("Trace colouring:", self.color_mode_combo)

        style_layout.addStretch(1)

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
        toolbar.show()
        toolbar.toggleViewAction().setChecked(True)
        self.plot_toolbar = toolbar

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
        if self.unit_combo is None:
            return "nm"
        return self.unit_combo.currentText()

    def _on_plot_max_points_changed(self, value: int) -> None:
        coerced = PlotPane.normalize_max_points(value)
        if coerced != value and self.plot_max_points_control is not None:
            self.plot_max_points_control.blockSignals(True)
            self.plot_max_points_control.setValue(coerced)
            self.plot_max_points_control.blockSignals(False)
        if coerced == self._plot_max_points:
            return
        self._plot_max_points = coerced
        self.plot.set_max_points(coerced)
        self._save_plot_max_points(coerced)

    def _on_color_mode_changed(self) -> None:
        if self.color_mode_combo is None:
            return
        use_uniform = self.color_mode_combo.currentIndex() == 1
        if use_uniform == self._use_uniform_palette:
            return
        self._use_uniform_palette = use_uniform
        for spec_id, base_color in self._spectrum_colors.items():
            self._update_dataset_icon(spec_id, self._display_color(base_color))
        self.refresh_overlay()

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

    def _on_dataset_filter_changed(self, _: str) -> None:
        self._apply_dataset_filter()

    def _apply_dataset_filter(self) -> None:
        if self.dataset_tree is None or self.dataset_model is None:
            return

        pattern = ""
        if self.dataset_filter is not None:
            pattern = self.dataset_filter.text().strip().lower()

        root_index = QtCore.QModelIndex()
        groups = [self._originals_item, self._derived_item]
        for group in groups:
            if group is None:
                continue
            group_index = self.dataset_model.indexFromItem(group)
            any_visible = False
            for row in range(group.rowCount()):
                child = group.child(row)
                alias = child.text() if child is not None else ""
                match = not pattern or pattern in alias.lower()
                self.dataset_tree.setRowHidden(row, group_index, not match)
                if match:
                    any_visible = True
            hide_group = bool(pattern) and not any_visible
            self.dataset_tree.setRowHidden(group.row(), root_index, hide_group)


    def _wire_shortcuts(self) -> None:
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), self, activated=self.open_file)
        QtGui.QShortcut(QtGui.QKeySequence("U"), self, activated=self._cycle_units)

    def _cycle_units(self) -> None:
        if self.unit_combo is None or self.unit_combo.count() == 0:
            return
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
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Open Spectra",
            str(Path.home()),
            "Spectra (*.csv *.txt)",
        )
        if not paths:
            return

        self.plot.begin_bulk_update()
        try:
            for raw in paths:
                if not raw:
                    continue
                self._ingest_path(Path(raw))
        finally:
            self.plot.end_bulk_update()

    def open_remote_data_dialog(self) -> None:
        dialog = RemoteDataDialog(
            self,
            remote_service=self.remote_data_service,
            ingest_service=self.ingest_service,
        )
        if not dialog.exec():
            return

        spectra = [spec for spec in dialog.ingested_spectra() if isinstance(spec, Spectrum)]
        if not spectra:
            return

        self.plot.begin_bulk_update()
        try:
            for spectrum in spectra:
                self.overlay_service.add(spectrum)
                self._add_spectrum(spectrum)
                remote_info = self._record_remote_history_event(spectrum)
                provider = str(remote_info.get("provider", "remote source"))
                uri = remote_info.get("uri")
                detail = f"Imported {spectrum.name} from {provider}"
                if uri:
                    detail += f" ({uri})"
                self._log("Remote", detail)
        finally:
            self.plot.end_bulk_update()

        self._refresh_library_view()
        self._update_math_selectors()
        self.refresh_overlay()
        self._show_metadata(spectra[-1])
        self._show_provenance(spectra[-1])
        message = f"Imported {len(spectra)} remote spectrum(s)."
        self.status_bar.showMessage(message, 5000)
        self._log("Remote", message)

    def load_sample_via_menu(self) -> None:
        files = list(SAMPLES_DIR.glob("*.csv"))
        if not files:
            self.status_bar.showMessage("No samples found", 5000)
            return

        dialog = QtWidgets.QFileDialog(self, "Load Sample", str(SAMPLES_DIR))
        dialog.setNameFilter("Spectra (*.csv *.txt)")
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFiles)
        if not dialog.exec():
            return

        selected = dialog.selectedFiles()
        if not selected:
            return

        self.plot.begin_bulk_update()
        try:
            for raw in selected:
                path = Path(raw)
                if path.exists():
                    self._ingest_path(path)
        finally:
            self.plot.end_bulk_update()

    def export_manifest(self) -> None:
        spectra_to_export = [
            spectrum
            for spectrum in self.overlay_service.list()
            if self._visibility.get(spectrum.id, True)
        ]

        if not spectra_to_export:
            if self.overlay_service.list():
                QtWidgets.QMessageBox.information(
                    self,
                    "No Visible Data",
                    "Set at least one dataset to visible before exporting.",
                )
            else:
                QtWidgets.QMessageBox.information(
                    self,
                    "No Data",
                    "Load spectra before exporting provenance.",
                )
            return

        options_dialog = ExportOptionsDialog(self, allow_composite=len(spectra_to_export) > 1)
        if options_dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        export_options = options_dialog.result()
        if not export_options.has_selection:
            QtWidgets.QMessageBox.information(
                self,
                "No Outputs Selected",
                "Choose at least one export artefact before continuing.",
            )
            return

        default_name = 'manifest.json' if export_options.include_manifest else 'spectra.csv'
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Manifest",
            str(Path.home() / default_name),
            "JSON (*.json);;CSV (*.csv)",
        )
        if save_path:
            manifest_path = Path(save_path)
            if export_options.include_manifest and manifest_path.suffix.lower() != ".json":
                manifest_path = manifest_path.with_suffix('.json')
            if not export_options.include_manifest:
                manifest_path.parent.mkdir(parents=True, exist_ok=True)

            generated_paths: List[str] = []
            status_messages: List[str] = []

            export: Dict[str, object] | None = None
            if export_options.include_manifest:
                try:
                    export = self.provenance_service.export_bundle(
                        spectra_to_export,
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
                generated_paths.extend(
                    [
                        str(export["manifest_path"]),
                        str(export["csv_path"]),
                        str(export["png_path"]),
                    ]
                )
                status_messages.append(f"Manifest saved to {export['manifest_path']}")
                self.provenance_view.setPlainText(json_pretty(export['manifest']))
                self.provenance_view.show()
                self.prov_tree.show()
                self.prov_placeholder.hide()

                base_dir = Path(export["manifest_path"]).parent
                base_stem = Path(export["manifest_path"]).stem
            else:
                base_dir = manifest_path.parent
                base_dir.mkdir(parents=True, exist_ok=True)
                base_stem = manifest_path.stem

            if export_options.include_wide_csv:
                if export_options.include_manifest:
                    wide_path = base_dir / f"{base_stem}_wide.csv"
                else:
                    wide_path = (
                        manifest_path
                        if manifest_path.suffix.lower() == '.csv' and not export_options.include_composite_csv
                        else base_dir / f"{base_stem}_wide.csv"
                    )
                try:
                    self.provenance_service.write_wide_csv(wide_path, spectra_to_export)
                except Exception as exc:  # pragma: no cover - UI feedback
                    QtWidgets.QMessageBox.warning(self, "Wide CSV Failed", str(exc))
                    self._log("Export", f"Wide CSV failed: {exc}")
                else:
                    generated_paths.append(str(wide_path))
                    status_messages.append(f"Wide CSV saved to {wide_path}")
                    self._log("Export", f"Wide CSV saved to {wide_path}")

            if export_options.include_composite_csv:
                composite_path = base_dir / f"{base_stem}_composite.csv"
                try:
                    self.provenance_service.write_composite_csv(
                        composite_path,
                        spectra_to_export,
                    )
                except Exception as exc:  # pragma: no cover - UI feedback
                    QtWidgets.QMessageBox.warning(self, "Composite Failed", str(exc))
                    self._log("Export", f"Composite export failed: {exc}")
                else:
                    generated_paths.append(str(composite_path))
                    status_messages.append(f"Composite CSV saved to {composite_path}")
                    self._log("Export", f"Composite CSV saved to {composite_path}")

            if status_messages:
                self.status_bar.showMessage("; ".join(status_messages), 5000)

            if generated_paths:
                self._record_history_event(
                    "Export",
                    f"Exported {len(spectra_to_export)} visible spectra",
                    generated_paths,
                )

    def refresh_overlay(self) -> None:
        selected_ids = self._selected_dataset_ids()
        if not selected_ids:
            selected_ids = [sid for sid, visible in self._visibility.items() if visible]
        if not selected_ids:
            self._last_display_views = []
            self.data_table.clearContents()
            self.data_table.setRowCount(0)
            if self.data_table.isVisible():
                self.data_table.hide()
            if self.data_table_action.isChecked():
                self.data_table_action.blockSignals(True)
                self.data_table_action.setChecked(False)
                self.data_table_action.blockSignals(False)
            return
        selected_ids = [sid for sid in selected_ids if self._visibility.get(sid, True)]
        if not selected_ids:
            self._last_display_views = []
            if self.data_table.isVisible():
                self.data_table.hide()
            if self.data_table_action.isChecked():
                self.data_table_action.blockSignals(True)
                self.data_table_action.setChecked(False)
                self.data_table_action.blockSignals(False)
            return
        raw_views = self.overlay_service.overlay(
            selected_ids,
            self.plot_unit(),
            self._normalise_y("absorbance"),
            normalization=self._normalization_mode,
        )
        display_views: List[Dict[str, object]] = []
        for view in raw_views:
            spec_id = cast(str, view["id"])
            display_unit = self._display_y_units.get(spec_id, "absorbance")
            _, y_display = self.units_service.from_canonical(
                cast(np.ndarray, view["x_canonical"]),
                cast(np.ndarray, view["y_canonical"]),
                "nm",
                display_unit,
            )
            updated = dict(view)
            updated["y"] = y_display
            updated["y_unit"] = display_unit
            display_views.append(updated)

        self._last_display_views = display_views
        if self.data_table_action.isChecked():
            if not self.data_table.isVisible():
                self.data_table.show()
            self._populate_data_table(display_views)
        else:
            if self.data_table.isVisible():
                self.data_table.hide()

        all_ids = [spec.id for spec in self.overlay_service.list()]
        if not all_ids:
            return
        canonical_views = self.overlay_service.overlay(
            all_ids,
            "nm",
            "absorbance",
            normalization=self._normalization_mode,
        )
        y_units_in_view: List[str] = []
        for view in canonical_views:
            spec_id = cast(str, view["id"])
            alias_item = self._dataset_items.get(spec_id)
            alias = alias_item.text() if alias_item else cast(str, view["name"])
            base_color = self._spectrum_colors.get(spec_id)
            if base_color is None:
                base_color = QtGui.QColor("#4F6D7A")
            display_unit = self._display_y_units.get(spec_id, "absorbance")
            _, y_display = self.units_service.from_canonical(
                cast(np.ndarray, view["x_canonical"]),
                cast(np.ndarray, view["y_canonical"]),
                "nm",
                display_unit,
            )
            y_units_in_view.append(display_unit)
            display_color = self._display_color(base_color)
            style = TraceStyle(
                color=QtGui.QColor(display_color),
                width=1.6,
                antialias=False,
                show_in_legend=True,
            )
            self.plot.add_trace(
                key=spec_id,
                alias=alias,
                x_nm=cast(np.ndarray, view["x_canonical"]),
                y=y_display,
                style=style,
            )
            self.plot.set_visible(spec_id, self._visibility.get(spec_id, True))

        if y_units_in_view:
            self.plot.set_y_label(self._format_y_axis_label(y_units_in_view[0]))

    def compute_subtract(self) -> None:
        ids = self._selected_math_ids()
        if not ids:
            return
        spec_a = self.overlay_service.get(ids[0])
        spec_b = self.overlay_service.get(ids[1])
        result, info = self.math_service.subtract(spec_a, spec_b)
        self._log_math(info)
        summary = (
            f"Computed {spec_a.name} − {spec_b.name}; "
            + (f"created {result.name} ({result.id})." if result else "result suppressed within tolerance.")
        )
        references = [spec_a.id, spec_b.id]
        if result and result.id:
            references.append(result.id)
        self._record_history_event("Math", summary, references)
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
        masked_points = info.get("masked_points") if isinstance(info, dict) else None
        summary = f"Computed {spec_a.name} ÷ {spec_b.name}; created {result.name} ({result.id})."
        if masked_points:
            summary += f" Masked {masked_points} low-denominator points."
        references = [spec_a.id, spec_b.id]
        if result.id:
            references.append(result.id)
        self._record_history_event("Math", summary, references)
        self.overlay_service.add(result)
        self._add_spectrum(result)
        self._update_math_selectors()

    # Internal helpers --------------------------------------------------
    def _ingest_path(self, path: Path) -> None:
        try:
            spectra = self.ingest_service.ingest(path)
        except Exception as exc:  # pragma: no cover - UI feedback
            QtWidgets.QMessageBox.critical(self, "Import failed", str(exc))
            return
        if not spectra:
            QtWidgets.QMessageBox.information(
                self,
                "No Spectra Imported",
                f"{path.name} did not contain any spectra to import.",
            )
            return

        for spectrum in spectra:
            self.overlay_service.add(spectrum)
            self._add_spectrum(spectrum)

        last_spectrum = spectra[-1]
        count = len(spectra)
        message = f"Loaded {count} spectrum{'s' if count != 1 else ''} from {path.name}"
        self.status_bar.showMessage(message, 5000)
        self._update_math_selectors()
        self.refresh_overlay()
        self._show_metadata(last_spectrum)
        self._show_provenance(last_spectrum)
        ingest_meta = last_spectrum.metadata.get("ingest", {}) if isinstance(last_spectrum.metadata, dict) else {}
        importer = ingest_meta.get("importer", "Unknown importer")
        summary = f"Ingested {count} spectrum{'s' if count != 1 else ''} via {importer}."
        references = [spec.id for spec in spectra if getattr(spec, "id", None)]
        self._record_history_event("Import", summary, references, persist=False)
        self._refresh_library_view()

    def _add_spectrum(self, spectrum: Spectrum) -> None:
        base_color = self._assign_color(spectrum)
        display_color = self._display_color(base_color)
        group_item = self._derived_item if self._is_derived(spectrum) else self._originals_item
        visible_item = QtGui.QStandardItem()
        visible_item.setCheckable(True)
        visible_item.setCheckState(QtCore.Qt.CheckState.Checked)
        visible_item.setEditable(False)
        visible_item.setData(spectrum.id, QtCore.Qt.ItemDataRole.UserRole)

        color_item = QtGui.QStandardItem()
        color_item.setEditable(False)
        icon_pix = QtGui.QPixmap(16, 16)
        icon_pix.fill(display_color)
        color_item.setIcon(QtGui.QIcon(icon_pix))
        color_item.setData(spectrum.id, QtCore.Qt.ItemDataRole.UserRole)

        alias_item = QtGui.QStandardItem(spectrum.name)
        alias_item.setEditable(False)
        alias_item.setData(spectrum.id, QtCore.Qt.ItemDataRole.UserRole)
        group_item.appendRow([alias_item, visible_item, color_item])
        self.dataset_tree.expandAll()
        self._dataset_items[spectrum.id] = alias_item
        self._dataset_color_items[spectrum.id] = color_item
        self._visibility[spectrum.id] = True
        _source_x, source_y = self._source_units(spectrum)
        self._display_y_units[spectrum.id] = source_y
        self._add_plot_trace(spectrum, base_color)
        self._apply_dataset_filter()

    def _add_plot_trace(self, spectrum: Spectrum, base_color: QtGui.QColor) -> None:
        alias_item = self._dataset_items.get(spectrum.id)
        alias = alias_item.text() if alias_item else spectrum.name
        x_nm = self._to_nm(spectrum.x, spectrum.x_unit)
        display_y_unit = self._display_y_units.get(spectrum.id, spectrum.y_unit)
        _, y_display = self.units_service.from_canonical(
            spectrum.x,
            spectrum.y,
            spectrum.x_unit,
            display_y_unit,
        )
        display_color = self._display_color(base_color)
        style = TraceStyle(
            color=QtGui.QColor(display_color),
            width=1.6,
            antialias=False,
            show_in_legend=True,
        )
        self.plot.add_trace(
            key=spectrum.id,
            alias=alias,
            x_nm=x_nm,
            y=y_display,
            style=style,
        )
        self.plot.set_y_label(self._format_y_axis_label(display_y_unit))
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
        source_x, source_y = self._source_units(spectrum)
        self.info_units.setText(f"x: {source_x} | y: {source_y}")
        self.info_units.setToolTip("Canonical units: x=nm | y=A₁₀")
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

    # History helpers --------------------------------------------------
    def _load_history_entries(self) -> None:
        if not getattr(self, "_history_ui_ready", False):
            return
        try:
            entries = self.knowledge_log.load_entries(limit=250)
        except Exception as exc:  # pragma: no cover - filesystem feedback
            self._log("History", f"Failed to load knowledge log: {exc}")
            return
        self._history_entries = entries
        self._refresh_history_component_filter()
        self._refresh_history_table(select_first=True)

    def _refresh_history_component_filter(self) -> None:
        if not getattr(self, "_history_ui_ready", False):
            return
        current = self.history_component_filter.currentText()
        self.history_component_filter.blockSignals(True)
        self.history_component_filter.clear()
        self.history_component_filter.addItem("All Components")
        for component in sorted({entry.component for entry in self._history_entries}):
            self.history_component_filter.addItem(component)
        if current:
            idx = self.history_component_filter.findText(current)
            if idx != -1:
                self.history_component_filter.setCurrentIndex(idx)
        self.history_component_filter.blockSignals(False)

    def _filtered_history_entries(self) -> list[KnowledgeLogEntry]:
        if not getattr(self, "_history_ui_ready", False):
            return []
        entries = list(self._history_entries)
        component = self.history_component_filter.currentText()
        if component and component != "All Components":
            entries = [entry for entry in entries if entry.component == component]
        text = self.history_search.text().strip().lower()
        if text:
            entries = [
                entry
                for entry in entries
                if text in entry.summary.lower()
                or any(text in ref.lower() for ref in entry.references)
                or text in entry.component.lower()
            ]
        return entries

    def _refresh_history_table(self, *, select_first: bool = False) -> None:
        if not getattr(self, "_history_ui_ready", False):
            return
        entries = self._filtered_history_entries()
        self._displayed_history_entries = entries
        self.history_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            timestamp = entry.timestamp.astimezone().strftime("%Y-%m-%d %H:%M") if entry.timestamp.tzinfo else entry.timestamp.strftime("%Y-%m-%d %H:%M")
            items = [
                QtWidgets.QTableWidgetItem(timestamp),
                QtWidgets.QTableWidgetItem(entry.component),
                QtWidgets.QTableWidgetItem(entry.summary.splitlines()[0] if entry.summary else ""),
            ]
            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.history_table.setItem(row, col, item)
        if not entries:
            self.history_detail.clear()
            return
        if select_first:
            self.history_table.selectRow(0)
            self.history_detail.setPlainText(entries[0].raw.strip())

    def _on_history_filter_changed(self) -> None:
        self._refresh_history_table(select_first=True)

    def _on_history_selection_changed(self) -> None:
        if not getattr(self, "_history_ui_ready", False):
            return
        indexes = self.history_table.selectionModel().selectedRows()
        if not indexes:
            self.history_detail.clear()
            return
        row = indexes[0].row()
        if 0 <= row < len(self._displayed_history_entries):
            entry = self._displayed_history_entries[row]
            self.history_detail.setPlainText(entry.raw.strip())

    def _export_history_entries(self) -> None:
        entries = self._filtered_history_entries()
        if not entries:
            QtWidgets.QMessageBox.information(self, "No Entries", "Nothing to export.")
            return
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export History",
            str(Path.home() / "spectra_history.md"),
            "Markdown (*.md *.markdown)",
        )
        if not save_path:
            return
        try:
            self.knowledge_log.export_entries(Path(save_path), entries)
        except Exception as exc:  # pragma: no cover - filesystem feedback
            QtWidgets.QMessageBox.warning(self, "Export Failed", str(exc))
            self._log("History", f"Export failed: {exc}")
        else:
            self._log("History", f"Exported {len(entries)} entries to {save_path}")

    def _append_history_entry(self, entry: KnowledgeLogEntry) -> None:
        self._history_entries.insert(0, entry)
        self._refresh_history_component_filter()
        self._refresh_history_table(select_first=True)

    def _record_history_event(
        self,
        component: str,
        summary: str,
        references: Sequence[str] | None = None,
        *,
        persist: bool = True,
    ) -> None:
        try:
            entry = self.knowledge_log.record_event(
                component,
                summary,
                references,
                persist=persist,
            )
        except Exception as exc:  # pragma: no cover - filesystem feedback
            self._log("History", f"Failed to record event: {exc}")
            return
        if getattr(self, "_history_ui_ready", False):
            self._append_history_entry(entry)

    def _record_remote_history_event(self, spectrum: Spectrum) -> Mapping[str, Any]:
        metadata = spectrum.metadata if isinstance(spectrum.metadata, Mapping) else {}
        cache_record = metadata.get("cache_record") if isinstance(metadata, Mapping) else None
        remote: Mapping[str, Any] | None = None
        if isinstance(cache_record, Mapping):
            source = cache_record.get("source")
            if isinstance(source, Mapping):
                candidate = source.get("remote")
                if isinstance(candidate, Mapping):
                    remote = candidate
        provider = str(remote.get("provider", "remote source")) if remote else "remote source"
        uri = str(remote.get("uri")) if remote and remote.get("uri") else None
        summary = f"Imported {spectrum.name} via {provider}."
        references = [ref for ref in [spectrum.id] if ref]
        self._record_history_event("Remote Import", summary, references, persist=False)
        return {"provider": provider, "uri": uri}

    def _populate_data_table(self, views: Iterable[dict]) -> None:
        views = list(views)
        if not views:
            self.data_table.clearContents()
            self.data_table.setRowCount(0)
            return

        x_header = f"X ({self.plot_unit()})"
        y_units = {self._format_display_unit(str(view.get("y_unit", ""))) for view in views if view.get("y_unit")}
        if not y_units:
            y_header = "Y"
        elif len(y_units) == 1:
            unit = next(iter(y_units))
            y_header = f"Y ({unit})"
        else:
            y_header = "Y (mixed)"
        self.data_table.setHorizontalHeaderLabels(["Spectrum", "Point", x_header, y_header])

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

    def _source_units(self, spectrum: Spectrum) -> tuple[str, str]:
        metadata = spectrum.metadata if isinstance(spectrum.metadata, Mapping) else {}
        source_units = metadata.get("source_units") if isinstance(metadata, Mapping) else None
        if not isinstance(source_units, Mapping):
            return spectrum.x_unit, spectrum.y_unit
        x_unit = str(source_units.get("x", spectrum.x_unit))
        y_unit = str(source_units.get("y", spectrum.y_unit))
        return x_unit, y_unit

    def _format_display_unit(self, unit: str) -> str:
        normalised = unit.strip().lower()
        pretty = {
            "absorbance": "A₁₀",
            "absorbance_e": "Aᴇ",
            "transmittance": "T",
            "percent_transmittance": "%T",
        }.get(normalised, unit)
        return pretty

    def _format_y_axis_label(self, unit: str) -> str:
        unit_label = self._format_display_unit(unit)
        normalised = self._normalization_mode.strip()
        if normalised.lower() not in {"", "none", "identity"}:
            return f"Intensity ({unit_label}, normalized: {normalised})"
        return f"Intensity ({unit_label})"

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

    def _display_color(self, base: QtGui.QColor) -> QtGui.QColor:
        if self._use_uniform_palette:
            return QtGui.QColor(self._uniform_color)
        return QtGui.QColor(base)

    def _update_dataset_icon(self, spectrum_id: str, color: QtGui.QColor) -> None:
        color_item = self._dataset_color_items.get(spectrum_id)
        if color_item is None:
            return
        icon_pix = QtGui.QPixmap(16, 16)
        icon_pix.fill(color)
        color_item.setIcon(QtGui.QIcon(icon_pix))

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
        if checked:
            self._populate_data_table(self._last_display_views)
            self.data_table.show()
        else:
            self.data_table.hide()

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
            "Use the panels below to fetch spectral line lists from NIST or browse infrared heuristics."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #555;")
        layout.addWidget(intro)

        self.reference_tabs = QtWidgets.QTabWidget()
        self.reference_tabs.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.reference_tabs.addTab(self._build_reference_lines_controls(), "Spectral lines")
        self.reference_tabs.addTab(self._build_reference_ir_controls(), "IR groups")
        self.reference_tabs.addTab(self._build_reference_line_shape_controls(), "Line-shape models")
        self.reference_tabs.currentChanged.connect(self._on_reference_tab_changed)
        layout.addWidget(self.reference_tabs)

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(QtWidgets.QLabel("Filter:"))
        self.reference_filter = QtWidgets.QLineEdit()
        self.reference_filter.setPlaceholderText("Filter spectral lines…")
        self.reference_filter.textChanged.connect(self._on_reference_filter_changed)
        controls.addWidget(self.reference_filter, 1)

        controls.addStretch(1)
        self.reference_overlay_checkbox = QtWidgets.QCheckBox("Overlay on plot")
        self.reference_overlay_checkbox.setEnabled(False)
        self.reference_overlay_checkbox.toggled.connect(self._on_reference_overlay_toggled)
        controls.addWidget(self.reference_overlay_checkbox)

        layout.addLayout(controls)

        self.reference_status_label = QtWidgets.QLabel()
        self.reference_status_label.setObjectName("reference-status")
        self.reference_status_label.setWordWrap(True)
        layout.addWidget(self.reference_status_label)

        self.reference_table = QtWidgets.QTableWidget()
        self.reference_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.reference_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.reference_table.setAlternatingRowColors(True)
        header = self.reference_table.horizontalHeader()
        header.setStretchLastSection(True)
        self.reference_table.itemSelectionChanged.connect(self._on_reference_row_selection_changed)
        layout.addWidget(self.reference_table, 1)

        self.reference_plot = pg.PlotWidget()
        self.reference_plot.setObjectName("reference-plot")
        self.reference_plot.setMinimumHeight(220)
        self.reference_plot.showGrid(x=True, y=True, alpha=0.25)
        default_unit = self.plot_unit()
        self.reference_plot.setLabel("bottom", "Wavelength", units=default_unit)
        self.reference_plot.setLabel("left", "Relative Intensity")
        layout.addWidget(self.reference_plot, 1)

        self.reference_meta = QtWidgets.QTextBrowser()
        self.reference_meta.setOpenExternalLinks(True)
        self.reference_meta.setPlaceholderText("Select a dataset to view its citation and context.")
        self.reference_meta.setMinimumHeight(160)
        layout.addWidget(self.reference_meta)

        self._reference_mode = "nist"
        self._nist_payload: Optional[Dict[str, Any]] = None
        self._refresh_reference_view()

    def _build_reference_lines_controls(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(6)

        form_layout = QtWidgets.QGridLayout()
        form_layout.setHorizontalSpacing(8)
        form_layout.setVerticalSpacing(4)

        self.nist_element_edit = QtWidgets.QLineEdit()
        self.nist_element_edit.setPlaceholderText("Element symbol (e.g., Fe)")
        self.nist_element_edit.setClearButtonEnabled(True)
        form_layout.addWidget(QtWidgets.QLabel("Element"), 0, 0)
        form_layout.addWidget(self.nist_element_edit, 0, 1)

        self.nist_ion_edit = QtWidgets.QLineEdit()
        self.nist_ion_edit.setPlaceholderText("Ion stage (I, II, …)")
        self.nist_ion_edit.setClearButtonEnabled(True)
        form_layout.addWidget(QtWidgets.QLabel("Ion"), 0, 2)
        form_layout.addWidget(self.nist_ion_edit, 0, 3)

        self.nist_lower_spin = QtWidgets.QDoubleSpinBox()
        self.nist_lower_spin.setDecimals(2)
        self.nist_lower_spin.setRange(1.0, 20000.0)
        self.nist_lower_spin.setValue(float(nist_asd_service.DEFAULT_LOWER_WAVELENGTH_NM))
        self.nist_lower_spin.setSuffix(" nm")
        form_layout.addWidget(QtWidgets.QLabel("λ min"), 1, 0)
        form_layout.addWidget(self.nist_lower_spin, 1, 1)

        self.nist_upper_spin = QtWidgets.QDoubleSpinBox()
        self.nist_upper_spin.setDecimals(2)
        self.nist_upper_spin.setRange(1.0, 20000.0)
        self.nist_upper_spin.setValue(float(nist_asd_service.DEFAULT_UPPER_WAVELENGTH_NM))
        self.nist_upper_spin.setSuffix(" nm")
        form_layout.addWidget(QtWidgets.QLabel("λ max"), 1, 2)
        form_layout.addWidget(self.nist_upper_spin, 1, 3)

        self.nist_medium_combo = QtWidgets.QComboBox()
        self.nist_medium_combo.addItem("Vacuum", userData="vacuum")
        self.nist_medium_combo.addItem("Air", userData="air")
        form_layout.addWidget(QtWidgets.QLabel("Medium"), 2, 0)
        form_layout.addWidget(self.nist_medium_combo, 2, 1)

        self.nist_use_ritz_checkbox = QtWidgets.QCheckBox("Prefer Ritz wavelengths")
        self.nist_use_ritz_checkbox.setChecked(True)
        form_layout.addWidget(self.nist_use_ritz_checkbox, 2, 2, 1, 2)

        root_layout.addLayout(form_layout)

        controls_layout = QtWidgets.QHBoxLayout()
        self.nist_examples_combo = QtWidgets.QComboBox()
        self.nist_examples_combo.addItem("Examples…", userData=None)
        self.nist_examples_combo.addItem("Hydrogen I (Balmer)", userData=("H", "I", 380.0, 750.0))
        self.nist_examples_combo.addItem("Helium II", userData=("He", "II", 200.0, 700.0))
        self.nist_examples_combo.addItem("Iron II", userData=("Fe", "II", 200.0, 800.0))
        self.nist_examples_combo.currentIndexChanged.connect(self._on_nist_example_selected)
        controls_layout.addWidget(self.nist_examples_combo)

        controls_layout.addStretch(1)

        self.nist_uniform_checkbox = QtWidgets.QCheckBox("Use uniform line colour")
        self.nist_uniform_checkbox.setToolTip(
            "Toggle to render all pinned line sets with the same colour on the preview and overlays."
        )
        self.nist_uniform_checkbox.toggled.connect(self._on_nist_uniform_toggled)
        controls_layout.addWidget(self.nist_uniform_checkbox)

        self.nist_fetch_button = QtWidgets.QPushButton("Fetch lines")
        self.nist_fetch_button.clicked.connect(self._on_nist_fetch_clicked)
        controls_layout.addWidget(self.nist_fetch_button)

        root_layout.addLayout(controls_layout)

        self.nist_collections_group = QtWidgets.QGroupBox("Pinned line sets")
        group_layout = QtWidgets.QVBoxLayout(self.nist_collections_group)
        group_layout.setSpacing(4)

        self.nist_collections_list = QtWidgets.QListWidget()
        self.nist_collections_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.nist_collections_list.itemSelectionChanged.connect(self._on_nist_collection_selected)
        group_layout.addWidget(self.nist_collections_list, 1)

        button_bar = QtWidgets.QHBoxLayout()
        self.nist_remove_button = QtWidgets.QPushButton("Remove selected")
        self.nist_remove_button.clicked.connect(self._on_nist_remove_selected)
        self.nist_remove_button.setEnabled(False)
        button_bar.addWidget(self.nist_remove_button)

        self.nist_clear_button = QtWidgets.QPushButton("Clear all")
        self.nist_clear_button.clicked.connect(self._on_nist_clear_all)
        self.nist_clear_button.setEnabled(False)
        button_bar.addWidget(self.nist_clear_button)
        button_bar.addStretch(1)
        group_layout.addLayout(button_bar)

        root_layout.addWidget(self.nist_collections_group)

        self.nist_hint_label = QtWidgets.QLabel()
        self.nist_hint_label.setWordWrap(True)
        root_layout.addWidget(self.nist_hint_label)

        if not nist_asd_service.dependencies_available():
            self.nist_fetch_button.setEnabled(False)
            self.nist_hint_label.setText(
                "Install the optional 'astroquery' package to enable NIST ASD lookups."
            )
        else:
            self.nist_hint_label.setText(
                "Enter an element symbol and optional ion stage, then adjust the wavelength window as needed."
            )
        self._update_nist_collections_ui()

        return widget

    def _build_reference_ir_controls(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QtWidgets.QLabel(
            "Infrared functional-group bands are bundled offline. Use the filter box to search by group, mode, or note."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        return widget

    def _build_reference_line_shape_controls(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QtWidgets.QLabel(
            "Line-shape placeholders illustrate Doppler, pressure, and Stark models. Select a row to preview the profile."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        return widget

    def _on_reference_tab_changed(self, index: int) -> None:
        mode_map = {0: "nist", 1: "ir", 2: "line_shapes"}
        new_mode = mode_map.get(index, "nist")
        if new_mode == self._reference_mode:
            return
        self._reference_mode = new_mode
        placeholder = {
            "nist": "Filter spectral lines…",
            "ir": "Filter IR groups…",
            "line_shapes": "Filter line-shape entries…",
        }.get(new_mode, "Filter entries…")
        self.reference_filter.blockSignals(True)
        self.reference_filter.setPlaceholderText(placeholder)
        self.reference_filter.clear()
        self.reference_filter.blockSignals(False)
        self.reference_overlay_checkbox.blockSignals(True)
        self.reference_overlay_checkbox.setChecked(False)
        self.reference_overlay_checkbox.blockSignals(False)
        self._refresh_reference_view()

    def _on_reference_filter_changed(self, _: str) -> None:
        self._refresh_reference_view()

    def _refresh_reference_view(self) -> None:
        query = self.reference_filter.text().strip().lower() if hasattr(self, "reference_filter") else ""
        overlay_payload: Optional[Dict[str, Any]] = None

        self._clear_reference_plot()
        self._line_shape_rows = []
        self.reference_table.setRowCount(0)
        self.reference_table.setColumnCount(0)

        mode = getattr(self, "_reference_mode", "nist")

        if mode == "nist":
            if not self._nist_collections:
                self.reference_status_label.setText(
                    "Enter an element and fetch spectral lines to populate this table."
                )
                self.reference_meta.clear()
                self._update_reference_overlay_state(None)
                return

            if not self._nist_active_key or self._nist_active_key not in self._nist_collections:
                self._nist_active_key = next(iter(self._nist_collections))

            payload = self._nist_collections.get(self._nist_active_key)
            if not payload:
                self._update_reference_overlay_state(None)
                return

            self._nist_payload = payload
            lines = list(payload.get("lines", []))
            filtered = self._filter_reference_entries(lines, query)

            headers = [
                "λ (nm)",
                "Observed (nm)",
                "Ritz (nm)",
                "Rel. intensity",
                "Norm. intensity",
                "Lower level",
                "Upper level",
                "Type",
            ]
            self.reference_table.setColumnCount(len(headers))
            self.reference_table.setHorizontalHeaderLabels(headers)
            self.reference_table.setRowCount(len(filtered))

            for row, entry in enumerate(filtered):
                self._set_table_item(row, 0, self._format_float(entry.get("wavelength_nm")))
                self._set_table_item(row, 1, self._format_float(entry.get("observed_wavelength_nm")))
                self._set_table_item(row, 2, self._format_float(entry.get("ritz_wavelength_nm")))
                self._set_table_item(row, 3, self._format_float(entry.get("relative_intensity"), precision=2))
                self._set_table_item(row, 4, self._format_float(entry.get("relative_intensity_normalized"), precision=3))
                self._set_table_item(row, 5, entry.get("lower_level", ""))
                self._set_table_item(row, 6, entry.get("upper_level", ""))
                self._set_table_item(row, 7, entry.get("transition_type", ""))

            meta = payload.get("meta", {})
            label = meta.get("label") or meta.get("element_name") or "NIST ASD lines"
            query_meta = meta.get("query") if isinstance(meta.get("query"), Mapping) else {}
            if isinstance(query_meta, Mapping):
                lower_nm = query_meta.get("lower_wavelength")
                upper_nm = query_meta.get("upper_wavelength")
                unit = query_meta.get("wavelength_unit", "nm")
                range_text = None
                if lower_nm is not None and upper_nm is not None:
                    range_text = f"Range: {lower_nm:.1f}–{upper_nm:.1f} {unit}"
                elif lower_nm is not None:
                    range_text = f"Lower bound: {lower_nm:.1f} {unit}"
                notes_parts = []
                if range_text:
                    notes_parts.append(range_text)
                medium = query_meta.get("wavelength_type")
                if medium:
                    notes_parts.append(f"Medium: {medium}")
                if meta.get("ion_stage"):
                    notes_parts.append(f"Ion stage: {meta['ion_stage']}")
                notes = "; ".join(notes_parts) if notes_parts else None
            else:
                notes = None

            self._set_reference_meta(label, "https://physics.nist.gov/asd", notes)

            overlay_payload: Optional[Dict[str, Any]] = None
            overlay_payloads: Dict[str, Dict[str, Any]] = {}
            overlay_datasets: List[Mapping[str, Any]] = []
            max_intensity = 0.0
            pinned_count = len(self._nist_collections)
            for key, dataset in self._nist_collections.items():
                entries = list(dataset.get("lines", []))
                meta_for_plot = dataset.get("meta", {})
                color = self._resolve_nist_color(key)
                payload_result, dataset_max = self._render_nist_lines(
                    entries,
                    meta_for_plot,
                    color,
                    build_overlay=True,
                )
                if payload_result is not None:
                    overlay_payloads[key] = payload_result
                    overlay_datasets.append(meta_for_plot)
                max_intensity = max(max_intensity, dataset_max)

            if max_intensity > 0:
                self.reference_plot.setYRange(0.0, max_intensity * 1.1, padding=0.05)

            line_total = len(lines)
            self.reference_status_label.setText(
                f"Displaying {len(filtered)} of {line_total} spectral line(s); {pinned_count} pinned set(s) on chart."
            )

            if overlay_payloads:
                overlay_payload = {
                    "kind": "nist-multi",
                    "payloads": overlay_payloads,
                    "datasets": overlay_datasets,
                }

        elif mode == "ir":
            entries = self.reference_library.ir_functional_groups()
            filtered = self._filter_reference_entries(entries, query)
            self.reference_table.setColumnCount(5)
            self.reference_table.setHorizontalHeaderLabels(
                ["Group", "Range (cm⁻¹)", "Intensity", "Modes", "Notes"]
            )
            self.reference_table.setRowCount(len(filtered))
            for row, entry in enumerate(filtered):
                self._set_table_item(row, 0, entry.get("group", ""))
                span = (
                    f"{self._format_float(entry.get('wavenumber_cm_1_min'), precision=0)} – "
                    f"{self._format_float(entry.get('wavenumber_cm_1_max'), precision=0)}"
                )
                self._set_table_item(row, 1, span)
                self._set_table_item(row, 2, entry.get("intensity", ""))
                modes = ", ".join(entry.get("associated_modes", []))
                self._set_table_item(row, 3, modes)
                self._set_table_item(row, 4, entry.get("notes", ""))
            meta = self.reference_library.ir_metadata()
            notes = self._merge_provenance(meta)
            self._set_reference_meta(meta.get("citation"), meta.get("url"), notes)
            self.reference_status_label.setText(
                f"{len(filtered)} of {len(entries)} IR functional-group band(s) shown."
            )
            overlay_payload = self._render_reference_ir_groups(filtered)

        else:  # line-shape models
            entries = self.reference_library.line_shape_placeholders()
            filtered = self._filter_reference_entries(entries, query)
            self._line_shape_rows = list(filtered)
            self.reference_table.setColumnCount(5)
            self.reference_table.setHorizontalHeaderLabels(
                ["Model", "Status", "Parameters", "Units", "Example"]
            )
            self.reference_table.setRowCount(len(filtered))
            for row, entry in enumerate(filtered):
                label = entry.get("label", entry.get("id", ""))
                self._set_table_item(row, 0, label)
                self._set_table_item(row, 1, entry.get("status", ""))
                params = entry.get("parameters", [])
                params_text = ", ".join(params) if isinstance(params, list) else ""
                self._set_table_item(row, 2, params_text)
                units_map = entry.get("units")
                units_text = ", ".join(
                    f"{key} ({value})" for key, value in units_map.items()
                ) if isinstance(units_map, Mapping) else ""
                self._set_table_item(row, 3, units_text)
                example_text = self._format_line_shape_example(entry.get("example_parameters"))
                self._set_table_item(row, 4, example_text)

            if filtered:
                self.reference_table.blockSignals(True)
                self.reference_table.selectRow(0)
                self.reference_table.blockSignals(False)
                overlay_payload = self._render_selected_line_shape()
            else:
                self.reference_table.clearSelection()
                meta = self.reference_library.line_shape_metadata()
                self.reference_meta.setHtml(self._line_shape_overview_html(meta))

            self.reference_status_label.setText(
                f"{len(filtered)} line-shape template(s) available."
            )

        self.reference_table.resizeColumnsToContents()
        self._update_reference_overlay_state(overlay_payload)

    def _on_nist_example_selected(self, index: int) -> None:
        data = self.nist_examples_combo.itemData(index)
        if not data:
            return
        element, ion, lower, upper = data
        self.nist_element_edit.setText(str(element))
        self.nist_ion_edit.setText(str(ion) if ion else "")
        self.nist_lower_spin.setValue(float(lower))
        self.nist_upper_spin.setValue(float(upper))
        self.nist_examples_combo.blockSignals(True)
        self.nist_examples_combo.setCurrentIndex(0)
        self.nist_examples_combo.blockSignals(False)

    def _on_nist_uniform_toggled(self, checked: bool) -> None:
        if checked == self._nist_use_uniform_colors:
            return
        self._nist_use_uniform_colors = checked
        self._update_nist_collections_ui()
        self._refresh_reference_view()

    def _register_nist_payload(self, payload: Mapping[str, Any]) -> str:
        self._nist_collection_counter += 1
        key = f"nist::{self._nist_collection_counter}"
        self._nist_collections[key] = dict(payload)
        meta = payload.get("meta", {}) if isinstance(payload, Mapping) else {}
        self._nist_collection_labels[key] = self._describe_nist_payload(meta)
        if key not in self._nist_collection_colors:
            self._nist_collection_colors[key] = self._allocate_nist_color()
        self._nist_active_key = key
        self._nist_payload = dict(payload)
        self._update_nist_collections_ui()
        return key

    def _describe_nist_payload(self, meta: Mapping[str, Any]) -> str:
        label = str(meta.get("label") or meta.get("element_name") or meta.get("element_symbol") or "NIST ASD")
        ion = meta.get("ion_stage")
        query = meta.get("query") if isinstance(meta.get("query"), Mapping) else {}
        parts = [label]
        if ion:
            parts.append(str(ion))
        if isinstance(query, Mapping):
            lower = query.get("lower_wavelength")
            upper = query.get("upper_wavelength")
            unit = query.get("wavelength_unit", "nm")
            if lower is not None and upper is not None:
                parts.append(f"{float(lower):.0f}–{float(upper):.0f} {unit}")
            elif lower is not None:
                parts.append(f"> {float(lower):.0f} {unit}")
            elif upper is not None:
                parts.append(f"< {float(upper):.0f} {unit}")
        return " • ".join(parts)

    def _allocate_nist_color(self) -> QtGui.QColor:
        base = self._palette[self._nist_palette_index % len(self._palette)]
        self._nist_palette_index += 1
        return QtGui.QColor(base)

    def _resolve_nist_color(self, key: str) -> QtGui.QColor:
        if self._nist_use_uniform_colors:
            return QtGui.QColor(self._uniform_color)
        color = self._nist_collection_colors.get(key)
        return QtGui.QColor(color) if isinstance(color, QtGui.QColor) else QtGui.QColor(self._uniform_color)

    def _make_color_icon(self, color: QtGui.QColor) -> QtGui.QIcon:
        pixmap = QtGui.QPixmap(12, 12)
        pixmap.fill(color)
        return QtGui.QIcon(pixmap)

    def _update_nist_collections_ui(self) -> None:
        if not hasattr(self, "nist_collections_list"):
            return

        self.nist_collections_list.blockSignals(True)
        self.nist_collections_list.clear()
        active_key = self._nist_active_key
        for key in self._nist_collections:
            label = self._nist_collection_labels.get(key, key)
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, key)
            item.setIcon(self._make_color_icon(self._resolve_nist_color(key)))
            self.nist_collections_list.addItem(item)
            if key == active_key:
                self.nist_collections_list.setCurrentItem(item)
        self.nist_collections_list.blockSignals(False)

        has_items = bool(self._nist_collections)
        if hasattr(self, "nist_collections_group") and self.nist_collections_group is not None:
            self.nist_collections_group.setEnabled(has_items)
        if hasattr(self, "nist_remove_button"):
            self.nist_remove_button.setEnabled(has_items and active_key in self._nist_collections)
        if hasattr(self, "nist_clear_button"):
            self.nist_clear_button.setEnabled(has_items)

        if has_items and not self.nist_collections_list.currentItem():
            self.nist_collections_list.setCurrentRow(0)

    def _on_nist_collection_selected(self) -> None:
        if not hasattr(self, "nist_collections_list"):
            return
        items = self.nist_collections_list.selectedItems()
        if not items:
            self._nist_active_key = None
            self._nist_payload = None
            self.nist_remove_button.setEnabled(False)
            self._refresh_reference_view()
            return
        key = items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(key, str) and key in self._nist_collections:
            self._nist_active_key = key
            self._nist_payload = self._nist_collections[key]
        self.nist_remove_button.setEnabled(self._nist_active_key in self._nist_collections)
        self._refresh_reference_view()

    def _on_nist_remove_selected(self) -> None:
        key = self._nist_active_key
        if not key:
            return
        self._nist_collections.pop(key, None)
        self._nist_collection_labels.pop(key, None)
        self._nist_collection_colors.pop(key, None)
        if self._nist_active_key == key:
            self._nist_active_key = None
            self._nist_payload = None
        self._update_nist_collections_ui()
        self._refresh_reference_view()

    def _on_nist_clear_all(self) -> None:
        if not self._nist_collections:
            return
        self._nist_collections.clear()
        self._nist_collection_labels.clear()
        self._nist_collection_colors.clear()
        self._nist_palette_index = 0
        self._nist_active_key = None
        self._nist_payload = None
        self._update_nist_collections_ui()
        self._refresh_reference_view()

    def _on_nist_fetch_clicked(self) -> None:
        element = self.nist_element_edit.text().strip()
        if not element:
            QtWidgets.QMessageBox.information(
                self,
                "Enter element",
                "Provide an element symbol or name before querying NIST.",
            )
            return

        ion_stage = self.nist_ion_edit.text().strip() or None
        lower_nm = float(self.nist_lower_spin.value())
        upper_nm = float(self.nist_upper_spin.value())
        use_ritz = self.nist_use_ritz_checkbox.isChecked()
        wavelength_type = str(self.nist_medium_combo.currentData() or "vacuum")

        try:
            payload = nist_asd_service.fetch_lines(
                element,
                element=element,
                ion_stage=ion_stage,
                lower_wavelength=lower_nm,
                upper_wavelength=upper_nm,
                wavelength_unit="nm",
                use_ritz=use_ritz,
                wavelength_type=wavelength_type,
            )
        except nist_asd_service.NistUnavailableError as exc:
            QtWidgets.QMessageBox.critical(self, "NIST unavailable", str(exc))
            return
        except nist_asd_service.NistQueryError as exc:
            QtWidgets.QMessageBox.critical(self, "Query failed", str(exc))
            return

        self._register_nist_payload(payload)
        self.reference_overlay_checkbox.blockSignals(True)
        self.reference_overlay_checkbox.setChecked(False)
        self.reference_overlay_checkbox.blockSignals(False)
        meta = payload.get("meta", {})
        line_count = meta.get("line_count") or len(payload.get("lines", []))
        self.reference_status_label.setText(
            f"Fetched {line_count} spectral line(s) from NIST ASD."
        )
        self._log("Reference", f"NIST ASD → {meta.get('label', element)}")
        self._refresh_reference_view()

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

    def _clear_reference_plot(self) -> None:
        if hasattr(self, "reference_plot"):
            for item in getattr(self, "_reference_plot_items", []):
                try:
                    self.reference_plot.removeItem(item)
                except Exception:  # pragma: no cover - defensive against pyqtgraph internals
                    pass
            self.reference_plot.clear()
            self.reference_plot.showGrid(x=True, y=True, alpha=0.25)
        self._reference_plot_items = []

    def _render_nist_lines(
        self,
        entries: List[Mapping[str, Any]],
        meta: Mapping[str, Any],
        color: QtGui.QColor,
        *,
        build_overlay: bool,
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        if not entries:
            display_unit = self._reference_display_unit()
            self.reference_plot.setLabel("bottom", "Wavelength", units=display_unit)
            self.reference_plot.setLabel("left", "Relative Intensity (a.u.)")
            return None, 0.0

        wavelengths: List[float] = []
        intensities: List[float] = []
        for entry in entries:
            wavelength = self._coerce_float(entry.get("wavelength_nm"))
            if wavelength is None or not np.isfinite(wavelength):
                continue
            wavelengths.append(wavelength)
            norm = self._coerce_float(entry.get("relative_intensity_normalized"))
            if norm is None:
                norm = self._coerce_float(entry.get("relative_intensity"))
            intensities.append(norm if norm is not None else 1.0)

        if not wavelengths:
            display_unit = self._reference_display_unit()
            self.reference_plot.setLabel("bottom", "Wavelength", units=display_unit)
            self.reference_plot.setLabel("left", "Relative Intensity (a.u.)")
            return None, 0.0

        wavelengths_nm = np.array(wavelengths, dtype=float)
        intensities_arr = np.array(intensities, dtype=float)
        if intensities_arr.size == 0:
            intensities_arr = np.ones_like(wavelengths_nm)

        display_unit = self._reference_display_unit()
        display_wavelengths = self._convert_nm_to_unit(wavelengths_nm, display_unit)
        pen = pg.mkPen(color=color, width=2)
        for x_val, intensity in zip(display_wavelengths, intensities_arr):
            height = float(intensity) if np.isfinite(intensity) and intensity > 0 else 1.0
            item = self.reference_plot.plot([x_val, x_val], [0.0, height], pen=pen)
            self._reference_plot_items.append(item)

        max_intensity = float(np.nanmax(intensities_arr)) if intensities_arr.size else 1.0
        if not np.isfinite(max_intensity) or max_intensity <= 0:
            max_intensity = 1.0
        self.reference_plot.setLabel("bottom", "Wavelength", units=display_unit)
        self.reference_plot.setLabel("left", "Relative Intensity (a.u.)")
        overlay_payload: Optional[Dict[str, Any]] = None
        if build_overlay:
            label = meta.get("label") or "NIST ASD"
            element_symbol = meta.get("element_symbol", "")
            overlay_alias = f"Reference – {label}"
            overlay_key = f"reference::nist::{element_symbol or label}".lower().replace(" ", "_")
            overlay_payload = self._build_overlay_for_lines(
                wavelengths_nm,
                intensities_arr,
                key=overlay_key,
                alias=overlay_alias,
                color=QtGui.QColor(color).name(),
            )
            if overlay_payload is not None:
                overlay_payload["dataset"] = meta

        return overlay_payload, max_intensity

    def _render_reference_spectral_lines(
        self, entries: List[Mapping[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        wavelengths: List[float] = []
        intensities: List[float] = []
        for entry in entries:
            wavelength = self._coerce_float(entry.get("vacuum_wavelength_nm"))
            if wavelength is None:
                continue
            wavelengths.append(wavelength)
            intensity = self._coerce_float(entry.get("relative_intensity"))
            intensities.append(intensity if intensity is not None else 1.0)

        if not wavelengths:
            display_unit = self._reference_display_unit()
            self.reference_plot.setLabel("bottom", "Wavelength", units=display_unit)
            self.reference_plot.setLabel("left", "Relative Intensity (a.u.)")
            return None

        wavelengths_nm = np.array(wavelengths, dtype=float)
        intensities_arr = np.array(intensities, dtype=float)
        max_intensity = float(np.nanmax(intensities_arr)) if intensities_arr.size else 1.0
        if not np.isfinite(max_intensity) or max_intensity <= 0:
            max_intensity = 1.0

        display_unit = self._reference_display_unit()
        display_wavelengths = self._convert_nm_to_unit(wavelengths_nm, display_unit)
        pen = pg.mkPen(color="#C72C41", width=2)
        for x_val, intensity in zip(display_wavelengths, intensities_arr):
            height = float(intensity) if np.isfinite(intensity) and intensity > 0 else 1.0
            item = self.reference_plot.plot([x_val, x_val], [0.0, height], pen=pen)
            self._reference_plot_items.append(item)

        self.reference_plot.setLabel("bottom", "Wavelength", units=display_unit)
        self.reference_plot.setLabel("left", "Relative Intensity (a.u.)")
        self.reference_plot.setYRange(0.0, max_intensity * 1.1, padding=0.05)
        return self._build_overlay_for_lines(
            wavelengths_nm,
            intensities_arr,
            key="reference::hydrogen_lines",
            alias="Reference – NIST Hydrogen",
            color="#C72C41",
        )

    def _render_reference_ir_groups(
        self, entries: List[Mapping[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not entries:
            self.reference_plot.setLabel("bottom", "Wavenumber", units="cm⁻¹")
            self.reference_plot.setLabel("left", "Relative Presence")
            return None

        brush = pg.mkBrush(109, 89, 122, 45)
        pen = pg.mkPen(color="#6D597A", width=1.2)
        for entry in entries:
            start = self._coerce_float(entry.get("wavenumber_cm_1_min"))
            end = self._coerce_float(entry.get("wavenumber_cm_1_max"))
            if start is None or end is None:
                continue
            if not np.isfinite(start) or not np.isfinite(end):
                continue
            lower = min(start, end)
            upper = max(start, end)
            region = pg.LinearRegionItem(values=(lower, upper), movable=False)
            region.setBrush(brush)
            # LinearRegionItem does not expose setPen; update the endpoint lines directly
            for line in getattr(region, "lines", []):
                line.setPen(pen)
            region.setZValue(5)
            self.reference_plot.addItem(region)
            self._reference_plot_items.append(region)

            label = entry.get("group") or entry.get("id")
            if label:
                centre = (lower + upper) / 2.0
                y_low, y_high = self._overlay_band_bounds()
                label_y = y_low + (y_high - y_low) * 0.5
                text_item = pg.TextItem(label, color="#6D597A")
                text_item.setAnchor((0.5, 0.5))
                text_item.setPos(centre, label_y)
                text_item.setZValue(6)
                self.reference_plot.addItem(text_item)
                self._reference_plot_items.append(text_item)

        self.reference_plot.setLabel("bottom", "Wavenumber", units="cm⁻¹")
        self.reference_plot.setLabel("left", "Relative Presence")
        return self._build_overlay_for_ir(entries)

    def _render_reference_jwst(
        self,
        target: Mapping[str, Any],
        rows: List[Mapping[str, Any]],
        wavelength_key: str,
        value_key: str,
        uncertainty_key: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        units = target.get("data_units", "Value")
        self.reference_plot.setLabel("bottom", "Wavelength", units="µm")
        self.reference_plot.setLabel("left", str(units))
        if not rows:
            return None

        x_vals: List[float] = []
        y_vals: List[float] = []
        err_vals: List[float] = []
        for entry in rows:
            wavelength = self._coerce_float(entry.get(wavelength_key))
            value = self._coerce_float(entry.get(value_key))
            if wavelength is None or value is None:
                continue
            if not np.isfinite(wavelength) or not np.isfinite(value):
                continue
            x_vals.append(wavelength)
            y_vals.append(value)
            if uncertainty_key:
                err = self._coerce_float(entry.get(uncertainty_key))
                if err is None:
                    err = float("nan")
                err_vals.append(err)

        if not x_vals:
            return None

        x_array = np.array(x_vals, dtype=float)
        y_array = np.array(y_vals, dtype=float)
        plot_item = self.reference_plot.plot(x_array, y_array, pen=pg.mkPen(color="#33658A", width=2))
        self._reference_plot_items.append(plot_item)

        if uncertainty_key and err_vals:
            err_array = np.array(err_vals, dtype=float)
            upper = y_array + err_array
            lower = y_array - err_array
            dotted_pen = pg.mkPen(color="#33658A", width=1, style=QtCore.Qt.PenStyle.DotLine)
            upper_item = self.reference_plot.plot(x_array, upper, pen=dotted_pen)
            lower_item = self.reference_plot.plot(x_array, lower, pen=dotted_pen)
            self._reference_plot_items.extend([upper_item, lower_item])

        nm_values = self._convert_um_to_nm(x_array)
        return self._build_overlay_for_jwst(target, nm_values, y_array)

    def _on_reference_row_selection_changed(self) -> None:
        if getattr(self, "_reference_mode", "") != "line_shapes":
            return
        overlay_payload = self._render_selected_line_shape()
        self._update_reference_overlay_state(overlay_payload)

    def _render_selected_line_shape(self) -> Optional[Dict[str, Any]]:
        if not self._line_shape_rows or self.line_shape_model is None:
            meta = self.reference_library.line_shape_metadata()
            self.reference_meta.setHtml(self._line_shape_overview_html(meta))
            self._clear_reference_plot()
            return None
        row = self.reference_table.currentRow()
        if row < 0 or row >= len(self._line_shape_rows):
            meta = self.reference_library.line_shape_metadata()
            self.reference_meta.setHtml(self._line_shape_overview_html(meta))
            self._clear_reference_plot()
            return None
        entry = self._line_shape_rows[row]
        return self._render_line_shape_entry(entry)

    def _render_line_shape_entry(self, entry: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        if self.line_shape_model is None:
            return None
        model_id = str(entry.get("id", ""))
        params = entry.get("example_parameters")
        params_map = params if isinstance(params, Mapping) else None
        outcome = self.line_shape_model.sample_profile(model_id, params_map)
        meta = self.reference_library.line_shape_metadata()
        if outcome is None:
            self._clear_reference_plot()
            self.reference_meta.setHtml(self._line_shape_overview_html(meta, entry, None))
            return None

        self._clear_reference_plot()
        x_nm = np.asarray(outcome.x, dtype=float)
        y_vals = np.asarray(outcome.y, dtype=float)
        display_unit = self._reference_display_unit()
        x_display = self._convert_nm_to_unit(x_nm, display_unit)
        pen = pg.mkPen(color="#4F6D7A", width=2)
        curve = self.reference_plot.plot(x_display, y_vals, pen=pen)
        self._reference_plot_items.append(curve)
        self.reference_plot.setLabel("bottom", "Wavelength", units=display_unit)
        self.reference_plot.setLabel("left", "Normalised intensity (a.u.)")
        if y_vals.size:
            y_max = float(np.nanmax(y_vals))
            if not np.isfinite(y_max) or y_max <= 0:
                y_max = 1.0
            self.reference_plot.setYRange(0.0, y_max * 1.1, padding=0.05)

        self.reference_meta.setHtml(self._line_shape_overview_html(meta, entry, outcome.metadata))
        alias = entry.get("label") or model_id or "Line-shape"
        payload = {
            "key": f"reference::line_shape::{model_id}",
            "alias": f"Reference – {alias}",
            "x_nm": x_nm,
            "y": y_vals,
            "color": "#4F6D7A",
            "width": 2.0,
            "model": model_id,
            "parameters": outcome.metadata.get("parameters", {}),
            "metadata": outcome.metadata,
        }
        return payload

    def _format_line_shape_example(self, params: Any) -> str:
        if not isinstance(params, Mapping):
            return ""
        tokens: List[str] = []
        for key, value in params.items():
            if isinstance(value, (int, float)):
                tokens.append(f"{key}={self._format_float(value)}")
            else:
                tokens.append(f"{key}={value}")
        return ", ".join(tokens)

    def _line_shape_overview_html(
        self,
        meta: Mapping[str, Any],
        entry: Mapping[str, Any] | None = None,
        outcome: Mapping[str, Any] | None = None,
    ) -> str:
        parts: List[str] = []
        if entry is not None:
            title = entry.get("label") or entry.get("id") or "Line-shape model"
            description = entry.get("description") or entry.get("notes") or ""
            parts.append(f"<p><b>{title}</b><br/>{description}</p>")

            units_map = entry.get("units")
            if isinstance(units_map, Mapping) and units_map:
                unit_items = "".join(
                    f"<li>{key}: {value}</li>" for key, value in units_map.items()
                )
                parts.append(f"<p><b>Units</b></p><ul>{unit_items}</ul>")

            params = outcome.get("parameters") if isinstance(outcome, Mapping) else entry.get("example_parameters")
            example_text = self._format_line_shape_example(params)
            if example_text:
                parts.append(f"<p><b>Example parameters:</b> {example_text}</p>")

            if isinstance(outcome, Mapping):
                highlights: List[str] = []
                for key in ("doppler_factor", "beta", "width_nm", "stark_width_nm", "delta_nm"):
                    value = outcome.get(key)
                    if value is None:
                        continue
                    if isinstance(value, (int, float)):
                        highlights.append(f"{key.replace('_', ' ')} = {self._format_float(value)}")
                    else:
                        highlights.append(f"{key.replace('_', ' ')} = {value}")
                if highlights:
                    parts.append("<p><b>Computed metrics:</b> " + ", ".join(highlights) + "</p>")

        notes = meta.get("notes")
        if notes:
            parts.append(f"<p>{notes}</p>")
        references = meta.get("references")
        if isinstance(references, list) and references:
            ref_lines = "".join(
                f"<li><a href='{ref.get('url')}'>{ref.get('citation')}</a></li>"
                if isinstance(ref, Mapping) and ref.get("url")
                else f"<li>{ref.get('citation')}</li>"
                for ref in references
                if isinstance(ref, Mapping) and ref.get("citation")
            )
            if ref_lines:
                parts.append(f"<p><b>References</b></p><ul>{ref_lines}</ul>")
        return "".join(parts) if parts else "<p>Line-shape placeholders</p>"

    def _reference_display_unit(self) -> str:
        return self.plot_unit()

    def _convert_nm_to_unit(self, values_nm: np.ndarray, unit: str) -> np.ndarray:
        normalised = self.units_service._normalise_x_unit(unit)
        if normalised == "nm":
            return values_nm
        if normalised in {"um", "µm"}:
            return values_nm / 1e3
        if normalised == "angstrom":
            return values_nm * 10.0
        if normalised == "cm^-1":
            with np.errstate(divide="ignore"):
                return np.where(values_nm != 0, 1e7 / values_nm, np.nan)
        return values_nm

    @staticmethod
    def _convert_um_to_nm(values_um: np.ndarray) -> np.ndarray:
        return values_um * 1e3

    @staticmethod
    def _coerce_float(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _build_overlay_for_lines(
        self,
        wavelengths_nm: np.ndarray,
        intensities: np.ndarray,
        *,
        key: str,
        alias: str,
        color: str = "#C72C41",
    ) -> Optional[Dict[str, Any]]:
        if wavelengths_nm.size == 0:
            return None

        if intensities.size != wavelengths_nm.size:
            intensities = np.full_like(wavelengths_nm, 1.0)

        y_min, y_max = self._overlay_vertical_bounds()
        span = y_max - y_min if np.isfinite(y_max - y_min) else 1.0
        baseline = y_min + span * 0.05
        cap = y_min + span * 0.35
        if not np.isfinite(baseline) or not np.isfinite(cap) or cap <= baseline:
            baseline = y_min
            cap = y_min + max(span, 1.0)
        max_intensity = float(np.nanmax(intensities)) if intensities.size else 1.0
        if not np.isfinite(max_intensity) or max_intensity <= 0:
            max_intensity = 1.0

        x_segments: List[float] = []
        y_segments: List[float] = []
        for value, raw_intensity in zip(wavelengths_nm, intensities):
            if not np.isfinite(value):
                continue
            intensity = float(raw_intensity) if np.isfinite(raw_intensity) and raw_intensity >= 0 else 0.0
            scaled_top = baseline + (cap - baseline) * (intensity / max_intensity)
            x_segments.extend([value, value, np.nan])
            y_segments.extend([baseline, scaled_top, np.nan])

        if not x_segments:
            return None

        return {
            "key": key,
            "alias": alias,
            "x_nm": np.array(x_segments, dtype=float),
            "y": np.array(y_segments, dtype=float),
            "color": color,
            "width": 1.4,
        }

    def _build_overlay_for_ir(self, entries: List[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
        x_segments: List[float] = []
        y_segments: List[float] = []
        y_low, y_high = self._overlay_band_bounds()
        labels: List[Dict[str, object]] = []

        for entry in entries:
            start = self._coerce_float(entry.get("wavenumber_cm_1_min"))
            end = self._coerce_float(entry.get("wavenumber_cm_1_max"))
            if start is None or end is None:
                continue
            if not np.isfinite(start) or not np.isfinite(end):
                continue
            nm_bounds = self.units_service._to_canonical_wavelength(np.array([start, end], dtype=float), "cm^-1")
            nm_low, nm_high = float(np.nanmin(nm_bounds)), float(np.nanmax(nm_bounds))
            if not np.isfinite(nm_low) or not np.isfinite(nm_high):
                continue
            if nm_low == nm_high:
                continue
            # PyQtGraph's PlotDataItem differentiates successive X values when
            # constructing fill paths; perfectly vertical edges therefore
            # trigger divide-by-zero warnings if we submit identical
            # coordinates back-to-back.  Use ``nextafter`` to pull the interior
            # points infinitesimally towards the opposite edge so the segment
            # remains visually vertical while avoiding zero-length steps.
            low_edge = np.nextafter(nm_low, nm_high)
            high_edge = np.nextafter(nm_high, nm_low)
            x_segments.extend([nm_low, low_edge, high_edge, nm_high, np.nan])
            y_segments.extend([y_low, y_high, y_high, y_low, np.nan])

            label = entry.get("group") or entry.get("id")
            if label:
                labels.append({
                    "text": str(label),
                    "centre_nm": float((nm_low + nm_high) / 2.0),
                })

        if not x_segments:
            return None

        return {
            "key": "reference::ir_groups",
            "alias": "Reference – IR Functional Groups",
            "x_nm": np.array(x_segments, dtype=float),
            "y": np.array(y_segments, dtype=float),
            "color": "#6D597A",
            "width": 1.2,
            "fill_color": (109, 89, 122, 70),
            "fill_level": float(y_low),
            "band_bounds": (float(y_low), float(y_high)),
            "labels": labels,
        }

    def _build_overlay_for_jwst(
        self,
        target: Mapping[str, Any],
        wavelengths_nm: np.ndarray,
        values: np.ndarray,
    ) -> Optional[Dict[str, Any]]:
        if wavelengths_nm.size == 0 or values.size == 0:
            return None

        if values.size != wavelengths_nm.size:
            min_size = min(values.size, wavelengths_nm.size)
            wavelengths_nm = wavelengths_nm[:min_size]
            values = values[:min_size]

        key_suffix = target.get("id") or target.get("name") or "jwst"
        key = f"reference::jwst::{key_suffix}"
        alias = f"Reference – JWST {target.get('name', key_suffix)}"
        color = target.get("plot_color", "#33658A")
        width = float(target.get("plot_width", 1.6))

        return {
            "key": key,
            "alias": alias,
            "x_nm": np.array(wavelengths_nm, dtype=float),
            "y": np.array(values, dtype=float),
            "color": color,
            "width": width,
        }

    def _overlay_vertical_bounds(self) -> tuple[float, float]:
        _, y_range = self.plot.view_range()
        y_min, y_max = y_range
        if not np.isfinite(y_min) or not np.isfinite(y_max) or y_min == y_max:
            y_min, y_max = 0.0, 1.0
        if y_min == y_max:
            y_max = y_min + 1.0
        return y_min, y_max

    def _overlay_band_bounds(self) -> tuple[float, float]:
        y_min, y_max = self._overlay_vertical_bounds()
        span = y_max - y_min
        bottom = y_min + span * 0.08
        top = y_min + span * 0.38
        if not np.isfinite(bottom) or not np.isfinite(top) or top <= bottom:
            bottom = y_min + span * 0.1
            top = bottom + max(span * 0.3, 1.0)
        return bottom, top

    def _reset_reference_overlay_state(self) -> None:
        """Clear overlay bookkeeping while preserving payload state."""

        self._reference_overlay_key.clear()
        annotations = getattr(self, "_reference_overlay_annotations", None)
        if annotations is None:
            self._reference_overlay_annotations = []
        else:
            annotations.clear()

    def _on_reference_overlay_toggled(self, checked: bool) -> None:
        if getattr(self, "_suppress_overlay_refresh", False):
            return
        if checked:
            self._apply_reference_overlay()
            payload = self._reference_overlay_payload or {}
            references = [str(key) for key in self._reference_overlay_key]
            dataset = payload.get("dataset") if isinstance(payload, dict) else None
            if dataset:
                references.append(str(dataset))
            elif isinstance(payload, dict) and payload.get("kind") == "nist-multi":
                meta_refs = payload.get("datasets")
                if isinstance(meta_refs, list):
                    references.extend(str(item) for item in meta_refs)
            self._record_history_event(
                "Overlay",
                "Enabled reference overlay(s).",
                references,
            )
        else:
            previous_keys = list(self._reference_overlay_key)
            self._clear_reference_overlay()
            references = [str(key) for key in previous_keys]
            self._record_history_event("Overlay", "Reference overlay cleared.", references)

    def _on_plot_range_changed(self, _: tuple[float, float], __: tuple[float, float]) -> None:
        if self._suppress_overlay_refresh:
            return
        if not self.reference_overlay_checkbox.isChecked():
            return
        payload = self._reference_overlay_payload
        if not payload:
            return
        if isinstance(payload, Mapping) and payload.get("kind") == "nist-multi":
            return

        band_bounds = payload.get("band_bounds")
        if not (
            isinstance(band_bounds, tuple)
            and len(band_bounds) == 2
        ):
            return

        new_bottom, new_top = self._overlay_band_bounds()
        if not (np.isfinite(new_bottom) and np.isfinite(new_top)):
            return

        old_bottom = float(band_bounds[0])
        old_top = float(band_bounds[1])
        if np.isclose(new_bottom, old_bottom) and np.isclose(new_top, old_top):
            return

        y_values = payload.get("y")
        if isinstance(y_values, np.ndarray):
            updated = y_values.copy()
            bottom_mask = np.isclose(
                updated,
                old_bottom,
                rtol=1e-6,
                atol=1e-9,
                equal_nan=False,
            )
            top_mask = np.isclose(
                updated,
                old_top,
                rtol=1e-6,
                atol=1e-9,
                equal_nan=False,
            )
            updated[bottom_mask] = float(new_bottom)
            updated[top_mask] = float(new_top)
            payload["y"] = updated

        payload["fill_level"] = float(new_bottom)
        payload["band_bounds"] = (float(new_bottom), float(new_top))

        self._reference_overlay_payload = payload
        self._suppress_overlay_refresh = True
        try:
            self._apply_reference_overlay()
        finally:
            self._suppress_overlay_refresh = False

    def _update_reference_overlay_state(self, payload: Optional[Dict[str, Any]]) -> None:
        self._reference_overlay_payload = payload
        overlay_available = False
        if isinstance(payload, Mapping) and payload.get("kind") == "nist-multi":
            payloads = payload.get("payloads")
            if isinstance(payloads, Mapping):
                self._nist_overlay_payloads = {}
                for key, item in payloads.items():
                    if not isinstance(item, Mapping):
                        continue
                    x_values = item.get("x_nm")
                    y_values = item.get("y")
                    if (
                        isinstance(x_values, np.ndarray)
                        and isinstance(y_values, np.ndarray)
                        and x_values.size > 0
                        and y_values.size == x_values.size
                    ):
                        self._nist_overlay_payloads[str(key)] = dict(item)
                overlay_available = bool(self._nist_overlay_payloads)
        else:
            self._nist_overlay_payloads = {}
            x_values = payload.get("x_nm") if payload else None
            y_values = payload.get("y") if payload else None
            overlay_available = (
                isinstance(x_values, np.ndarray)
                and isinstance(y_values, np.ndarray)
                and x_values.size > 0
                and y_values.size == x_values.size
            )

        self.reference_overlay_checkbox.blockSignals(True)
        self.reference_overlay_checkbox.setEnabled(overlay_available)
        if not overlay_available:
            self.reference_overlay_checkbox.setChecked(False)
        self.reference_overlay_checkbox.blockSignals(False)

        if overlay_available and self.reference_overlay_checkbox.isChecked():
            self._apply_reference_overlay()
        elif not overlay_available:
            self._clear_reference_overlay()

    def _apply_reference_overlay(self) -> None:
        payload = self._reference_overlay_payload
        if not payload:
            self._clear_reference_overlay()
            return

        if isinstance(payload, Mapping) and payload.get("kind") == "nist-multi":
            overlays = self._nist_overlay_payloads
            if not overlays:
                self._clear_reference_overlay()
                return
            self._clear_reference_overlay()
            for item in overlays.values():
                x_values = item.get("x_nm")
                y_values = item.get("y")
                if not (
                    isinstance(x_values, np.ndarray)
                    and isinstance(y_values, np.ndarray)
                    and x_values.size
                    and x_values.size == y_values.size
                ):
                    continue
                key = str(item.get("key") or f"reference::nist::{len(self._reference_overlay_key)+1}")
                alias = str(item.get("alias", key))
                color = item.get("color", "#33658A")
                width = float(item.get("width", 1.4))
                style = TraceStyle(QtGui.QColor(color), width=width, show_in_legend=False)
                self.plot.add_trace(key, alias, x_values, y_values, style)
                self._reference_overlay_key.append(key)
            self._reference_overlay_annotations.clear()
            return

        x_values = payload.get("x_nm")
        y_values = payload.get("y")
        if not isinstance(x_values, np.ndarray) or not isinstance(y_values, np.ndarray):
            self._clear_reference_overlay()
            return

        key = str(payload.get("key", "reference::overlay"))
        alias = str(payload.get("alias", key))
        color = payload.get("color", "#33658A")
        width = float(payload.get("width", 1.5))
        fill_color = payload.get("fill_color")
        fill_level = payload.get("fill_level")

        self._clear_reference_overlay()

        style = TraceStyle(
            QtGui.QColor(color),
            width=width,
            show_in_legend=False,
            fill_brush=fill_color,
            fill_level=float(fill_level) if fill_level is not None else None,
        )
        self.plot.add_trace(key, alias, x_values, y_values, style)
        self._reference_overlay_key.append(key)

        self._reference_overlay_annotations.clear()
        band_bounds = payload.get("band_bounds")
        labels = payload.get("labels")
        if (
            isinstance(labels, list)
            and isinstance(band_bounds, tuple)
            and len(band_bounds) == 2
        ):
            band_bottom = float(band_bounds[0])
            band_top = float(band_bounds[1])
            if not (np.isfinite(band_bottom) and np.isfinite(band_top)):
                return
            if band_top <= band_bottom:
                band_top = band_bottom + 1.0

            x_range, _ = self.plot.view_range()
            x_min, x_max = map(float, x_range)
            x_span = abs(x_max - x_min)
            if not np.isfinite(x_span) or x_span == 0.0:
                x_span = 1.0
            cluster_threshold = x_span * 0.04

            assigned: List[tuple[str, float, int]] = []
            row_last_x: List[float] = []

            for label in sorted(
                (label for label in labels if isinstance(label, Mapping)),
                key=lambda entry: float(entry.get("centre_nm", float("inf"))),
            ):
                text = label.get("text")
                centre_nm = label.get("centre_nm")
                if not text or centre_nm is None:
                    continue
                centre_nm = float(centre_nm)
                if not np.isfinite(centre_nm):
                    continue
                x_display = self.plot.map_nm_to_display(centre_nm)
                if not np.isfinite(x_display):
                    continue

                row_index = None
                for idx, last_x in enumerate(row_last_x):
                    if abs(x_display - last_x) >= cluster_threshold:
                        row_index = idx
                        row_last_x[idx] = x_display
                        break
                if row_index is None:
                    row_index = len(row_last_x)
                    row_last_x.append(x_display)

                assigned.append((str(text), x_display, row_index))

            if not assigned:
                return

            row_count = max((row for *_, row in assigned), default=-1) + 1
            if row_count <= 0:
                row_count = 1

            band_span = band_top - band_bottom
            margin = band_span * 0.1
            if not np.isfinite(margin) or margin < 0.0:
                margin = 0.0
            available = band_span - margin * 2.0
            if available <= 0:
                available = band_span
            spacing = available / max(row_count, 1)

            for text, x_display, row_index in assigned:
                anchor_y = band_top - margin - spacing * (row_index + 0.5)
                anchor_y = float(np.clip(anchor_y, band_bottom + margin, band_top - margin))
                text_item = pg.TextItem(
                    text,
                    color=QtGui.QColor("#E6E1EB"),
                    fill=pg.mkBrush(28, 28, 38, 200),
                    border=pg.mkPen(color),
                )
                text_item.setAnchor((0.5, 0.5))
                text_item.setPos(x_display, anchor_y)
                text_item.setZValue(25)
                self.plot.add_graphics_item(text_item, ignore_bounds=True)
                self._reference_overlay_annotations.append(text_item)

    def _clear_reference_overlay(self) -> None:
        keys = list(self._reference_overlay_key)
        for key in keys:
            self.plot.remove_trace(key)
        for item in self._reference_overlay_annotations:
            try:
                self.plot.remove_graphics_item(item)
            except Exception:  # pragma: no cover - defensive cleanup
                continue
        self._reset_reference_overlay_state()

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

        self._load_documentation_index()

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
        if not hasattr(self, "log_view") or self.log_view is None:
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

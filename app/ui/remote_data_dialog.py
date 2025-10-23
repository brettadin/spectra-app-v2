"""Remote data discovery dialog."""

from __future__ import annotations

import html
import math
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, List

from app.qt_compat import get_qt
from app.services import DataIngestService, RemoteDataService, RemoteRecord

QtCore, QtGui, QtWidgets, _ = get_qt()  # type: ignore[misc]

# Dynamic Signal/Slot resolution for PySide6/PyQt6 compatibility
Signal = getattr(QtCore, "Signal", None)  # type: ignore[attr-defined]
if Signal is None:
    Signal = getattr(QtCore, "pyqtSignal")  # type: ignore[attr-defined]

Slot = getattr(QtCore, "Slot", None)  # type: ignore[attr-defined]
if Slot is None:
    Slot = getattr(QtCore, "pyqtSlot")  # type: ignore[attr-defined]


class _SearchWorker(QtCore.QObject):  # type: ignore[name-defined]
    """Background worker that streams search results from a remote provider."""

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
        """Execute a progressive/batched search and stream results.

        For MAST-based providers we split the search into smaller segments to
        reduce time-to-first-result and avoid issuing a single heavyweight
        query that returns everything at once. Segments are grouped by mission
        and product type (spectra first, then imaging if requested).
        """
        self.started.emit()  # type: ignore[attr-defined]
        collected: list[RemoteRecord] = []

        try:
            # Fast path for NIST or providers without a batching strategy
            if provider == RemoteDataService.PROVIDER_NIST:
                results = self._remote_service.search(provider, query, include_imaging=include_imaging)
                for record in results:
                    if self._cancel_requested:
                        self.cancelled.emit()  # type: ignore[attr-defined]
                        return
                    collected.append(record)
                    self.record_found.emit(record)  # type: ignore[attr-defined]
                self.finished.emit(collected)  # type: ignore[attr-defined]
                return

            # Progressive strategy for MAST and ExoSystems
            seen: set[tuple[str, str]] = set()

            def _emit_batch(batch: list[RemoteRecord]) -> None:
                for rec in batch:
                    if self._cancel_requested:
                        self.cancelled.emit()  # type: ignore[attr-defined]
                        return
                    key = (rec.download_url, rec.identifier)
                    if key in seen:
                        continue
                    seen.add(key)
                    collected.append(rec)
                    self.record_found.emit(rec)  # type: ignore[attr-defined]

            if provider == RemoteDataService.PROVIDER_MAST:
                # Prioritise calibrated spectra from common missions first.
                base = dict(query)
                # Always search spectra first (fast, most relevant)
                mission_batches: list[list[str]] = [
                    ["JWST"],
                    ["HST"],
                    ["IUE", "FUSE", "GALEX"],
                    ["Kepler", "K2", "TESS"],
                ]

                # Spectra (calib 2/3), by mission group
                for missions in mission_batches:
                    for mission in missions:
                        if self._cancel_requested:
                            self.cancelled.emit()  # type: ignore[attr-defined]
                            return
                        criteria = {**base, "obs_collection": mission, "dataproduct_type": "spectrum", "calib_level": [2, 3], "intentType": "SCIENCE"}
                        try:
                            batch = self._remote_service.search(
                                RemoteDataService.PROVIDER_MAST, criteria, include_imaging=False
                            )
                        except Exception:
                            batch = []
                        _emit_batch(batch)

                # Imaging next (optional)
                if include_imaging:
                    for missions in mission_batches:
                        for mission in missions:
                            if self._cancel_requested:
                                self.cancelled.emit()  # type: ignore[attr-defined]
                                return
                            criteria = {**base, "obs_collection": mission, "dataproduct_type": "image", "intentType": "SCIENCE"}
                            try:
                                batch = self._remote_service.search(
                                    RemoteDataService.PROVIDER_MAST, criteria, include_imaging=True
                                )
                            except Exception:
                                batch = []
                            _emit_batch(batch)

                self.finished.emit(collected)  # type: ignore[attr-defined]
                return

            if provider == RemoteDataService.PROVIDER_EXOSYSTEMS:
                # Fetch spectra first to get relevant results quickly
                try:
                    spectral = self._remote_service.search(
                        RemoteDataService.PROVIDER_EXOSYSTEMS, query, include_imaging=False
                    )
                except Exception:
                    spectral = []
                _emit_batch(spectral)

                if include_imaging:
                    try:
                        mixed = self._remote_service.search(
                            RemoteDataService.PROVIDER_EXOSYSTEMS, query, include_imaging=True
                        )
                    except Exception:
                        mixed = []
                    # From the mixed set, emit only imaging records to avoid duplicates
                    imaging_only: list[RemoteRecord] = []
                    for rec in mixed:
                        meta = rec.metadata if isinstance(rec.metadata, dict) else {}
                        dtype = str(meta.get("dataproduct_type") or meta.get("productType") or "").lower()
                        desc = str(meta.get("description") or meta.get("display_name") or "").lower()
                        if ("image" in dtype) or ("image" in desc):
                            imaging_only.append(rec)
                    _emit_batch(imaging_only)

                self.finished.emit(collected)  # type: ignore[attr-defined]
                return

            # Fallback: non-batched search
            results = self._remote_service.search(provider, query, include_imaging=include_imaging)
            _emit_batch(results)
            self.finished.emit(collected)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - defensive: surfaced via signal
            self.failed.emit(str(exc))  # type: ignore[attr-defined]
            return

    @Slot()  # type: ignore[misc]
    def cancel(self) -> None:
        self._cancel_requested = True


class _DownloadWorker(QtCore.QObject):  # type: ignore[name-defined]
    """Background worker that downloads and ingests selected remote records."""

    started = Signal(int)  # type: ignore[misc]
    record_ingested = Signal(object)  # type: ignore[misc]
    record_failed = Signal(object, str)  # type: ignore[misc]
    finished = Signal(list)  # type: ignore[misc]
    failed = Signal(str)  # type: ignore[misc]
    cancelled = Signal()  # type: ignore[misc]

    def __init__(
        self,
        remote_service: RemoteDataService,
        ingest_service: DataIngestService,
    ) -> None:
        super().__init__()
        self._remote_service = remote_service
        self._ingest_service = ingest_service
        self._cancel_requested = False

    @Slot(list)  # type: ignore[misc]
    def run(self, records: list[RemoteRecord]) -> None:
        self.started.emit(len(records))  # type: ignore[attr-defined]
        ingested: list[object] = []
        try:
            for record in records:
                if self._cancel_requested:
                    self.cancelled.emit()  # type: ignore[attr-defined]
                    return
                try:
                    download = self._remote_service.download(record)
                    file_path = Path(download.cache_entry["stored_path"])
                    
                    # Skip non-spectral file types (images, logs, etc.)
                    non_spectral_extensions = {
                        '.gif', '.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.svg',
                        '.txt', '.log', '.xml', '.html', '.htm', '.json', '.md'
                    }
                    if file_path.suffix.lower() in non_spectral_extensions:
                        # Emit as failed with a clear message
                        self.record_failed.emit(
                            record,
                            f"Skipped non-spectral file type: {file_path.suffix}"
                        )  # type: ignore[attr-defined]
                        continue
                    
                    ingested_item = self._ingest_service.ingest(file_path)
                except Exception as exc:  # pragma: no cover - defensive: surfaced via signal
                    self.record_failed.emit(record, str(exc))  # type: ignore[attr-defined]
                    continue
                if isinstance(ingested_item, list):
                    ingested.extend(ingested_item)
                else:
                    ingested.append(ingested_item)
                self.record_ingested.emit(record)  # type: ignore[attr-defined]
            if self._cancel_requested:
                self.cancelled.emit()  # type: ignore[attr-defined]
                return
        except Exception as exc:  # pragma: no cover - defensive: surfaced via signal
            self.failed.emit(str(exc))  # type: ignore[attr-defined]
            return
        self.finished.emit(ingested)  # type: ignore[attr-defined]

    @Slot()  # type: ignore[misc]
    def cancel(self) -> None:
        self._cancel_requested = True


class RemoteDataDialog(QtWidgets.QDialog):  # type: ignore[name-defined]
    """Interactive browser for remote catalogue search and download."""

    search_started = Signal(str)  # type: ignore[misc]
    search_completed = Signal(list)  # type: ignore[misc]
    search_failed = Signal(str)  # type: ignore[misc]
    download_started = Signal(int)  # type: ignore[misc]
    download_completed = Signal(list)  # type: ignore[misc]
    download_failed = Signal(str)  # type: ignore[misc]

    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        *,
        remote_service: RemoteDataService,
        ingest_service: DataIngestService,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Remote Data")
        self.resize(720, 520)

        self.remote_service = remote_service
        self.ingest_service = ingest_service
        self._records: List[RemoteRecord] = []
        self._filtered_records: List[RemoteRecord] = []  # Store filtered records for table mapping
        self._ingested: List[object] = []
        self._provider_hints: dict[str, str] = {}
        self._provider_placeholders: dict[str, str] = {}
        self._provider_examples: dict[str, list[tuple[str, str]]] = {}
        self._dependency_hint: str = ""
        self._search_thread: QtCore.QThread | None = None
        self._search_worker: _SearchWorker | None = None
        self._download_thread: QtCore.QThread | None = None
        self._download_worker: _DownloadWorker | None = None
        self._search_in_progress = False
        self._download_in_progress = False
        self._download_warnings: list[str] = []
        self._busy: bool = False
        # Tracks enabled state of controls while in busy mode; must exist before
        # any calls to _set_busy(False) during initial UI refresh.
        self._control_enabled_state: dict[object, bool] = {}
        self._quick_pick_targets: list[Mapping[str, Any]] = []
        self._current_filter: str = "all"  # all, spectra, images, other

        # Build the UI once
        self._build_ui()

    # ------------------------------------------------------------------
    def ingested_spectra(self) -> List[object]:
        return list(self._ingested)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        controls = QtWidgets.QHBoxLayout()
        self.provider_combo = QtWidgets.QComboBox(self)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        controls.addWidget(QtWidgets.QLabel("Catalogue:"))
        controls.addWidget(self.provider_combo)

        self.search_edit = QtWidgets.QLineEdit(self)
        self.search_edit.setPlaceholderText("Element, target name, or keyword…")
        controls.addWidget(self.search_edit, 1)

        self.example_combo = QtWidgets.QComboBox(self)
        self.example_combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self.example_combo.addItem("Examples…")
        self.example_combo.setEnabled(False)
        self.example_combo.activated.connect(self._on_example_selected)
        controls.addWidget(self.example_combo)

        self.quick_pick_button = QtWidgets.QToolButton(self)
        self.quick_pick_button.setText("Solar System")
        self.quick_pick_button.setPopupMode(
            QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.quick_pick_button.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly
        )
        self.quick_pick_button.setEnabled(False)
        self.quick_pick_button.setToolTip(
            "Quick-pick Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto."
        )
        self.quick_pick_menu = QtWidgets.QMenu(self.quick_pick_button)
        self.quick_pick_button.setMenu(self.quick_pick_menu)
        controls.addWidget(self.quick_pick_button)

        self.search_button = QtWidgets.QPushButton("Search", self)
        self.search_button.clicked.connect(self._on_search)
        controls.addWidget(self.search_button)

        self.include_imaging_checkbox = QtWidgets.QCheckBox("Include imaging", self)
        self.include_imaging_checkbox.setToolTip(
            "When enabled, MAST results may include calibrated imaging alongside spectroscopic products."
        )
        self.include_imaging_checkbox.setVisible(False)
        controls.addWidget(self.include_imaging_checkbox)

        layout.addLayout(controls)

        # Data type filter buttons
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Show:"))
        
        self.filter_all_radio = QtWidgets.QRadioButton("All")
        self.filter_all_radio.setChecked(True)
        self.filter_all_radio.toggled.connect(self._on_filter_changed)
        filter_layout.addWidget(self.filter_all_radio)
        
        self.filter_spectra_radio = QtWidgets.QRadioButton("Spectra")
        self.filter_spectra_radio.toggled.connect(self._on_filter_changed)
        filter_layout.addWidget(self.filter_spectra_radio)
        
        self.filter_images_radio = QtWidgets.QRadioButton("Images")
        self.filter_images_radio.toggled.connect(self._on_filter_changed)
        filter_layout.addWidget(self.filter_images_radio)
        
        self.filter_other_radio = QtWidgets.QRadioButton("Other")
        self.filter_other_radio.toggled.connect(self._on_filter_changed)
        filter_layout.addWidget(self.filter_other_radio)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self)
        layout.addWidget(splitter, 1)

        self.results = QtWidgets.QTableWidget(self)
        self._results_headers = [
            "ID",
            "Title",
            "Target / Host",
            "Telescope / Mission",
            "Instrument / Mode",
            "Product Type",
            "Download",
            "Preview / Citation",
        ]
        self.results.setColumnCount(len(self._results_headers))
        self.results.setHorizontalHeaderLabels(self._results_headers)
        self.results.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.results.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        header = self.results.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        for column in (0, 6, 7):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.results.verticalHeader().setVisible(False)
        self.results.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.results)

        self.preview = QtWidgets.QPlainTextEdit(self)
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Select a result to preview metadata")
        splitter.addWidget(self.preview)

        buttons = QtWidgets.QDialogButtonBox(self)
        self.download_button = buttons.addButton(
            "Download & Import", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.download_button.clicked.connect(self._on_queue_downloads)
        cancel = buttons.addButton(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        cancel.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self.hint_label = QtWidgets.QLabel(self)
        self.hint_label.setObjectName("remote-hint")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        progress_container = QtWidgets.QHBoxLayout()
        self.progress_label = QtWidgets.QLabel(self)
        self.progress_label.setObjectName("remote-progress")
        self.progress_label.setVisible(False)
        self.progress_movie = QtGui.QMovie(
            ":/qt-project.org/styles/commonstyle/images/working-32.gif"
        )
        if self.progress_movie.isValid():
            self.progress_label.setMovie(self.progress_movie)
        else:  # pragma: no cover - fallback when Qt resource missing
            self.progress_label.setText("Working…")
        progress_container.addWidget(self.progress_label)

        self.status_label = QtWidgets.QLabel(self)
        self.status_label.setObjectName("remote-status")
        self.status_label.setWordWrap(True)
        progress_container.addWidget(self.status_label, 1)
        layout.addLayout(progress_container)

        self._refresh_provider_state()
        self._update_download_button_state()

    # ------------------------------------------------------------------
    def _on_filter_changed(self) -> None:
        """Update visible records based on selected filter."""
        if self.filter_all_radio.isChecked():
            self._current_filter = "all"
        elif self.filter_spectra_radio.isChecked():
            self._current_filter = "spectra"
        elif self.filter_images_radio.isChecked():
            self._current_filter = "images"
        else:
            self._current_filter = "other"
        
        # Re-populate table with filtered records
        if self._records:
            self._populate_results_table(self._records)
    
    def _should_show_record(self, record: RemoteRecord) -> bool:
        """Check if record matches current filter."""
        if self._current_filter == "all":
            return True
        
        metadata = record.metadata if isinstance(record.metadata, Mapping) else {}
        product_type = str(metadata.get("dataproduct_type") or metadata.get("productType") or "").lower()
        
        if self._current_filter == "spectra":
            return "spectrum" in product_type or "spectral" in product_type
        elif self._current_filter == "images":
            return "image" in product_type or "imaging" in product_type
        else:  # other
            return "spectrum" not in product_type and "image" not in product_type

    def _on_search(self) -> None:
        provider = self.provider_combo.currentText()
        query = self._build_provider_query(provider, self.search_edit.text())
        if not query:
            self.status_label.setText(
                "Provide provider-specific search text before querying the remote catalogue."
            )
            return

        include_imaging = bool(
            self.include_imaging_checkbox.isVisible()
            and self.include_imaging_checkbox.isEnabled()
            and self.include_imaging_checkbox.isChecked()
        )
        self._start_search(provider, query, include_imaging)

    def _start_search(
        self, provider: str, query: dict[str, str], include_imaging: bool
    ) -> None:
        # Prepare UI
        self._cancel_search_worker()
        self._records = []
        self._reset_results_table()
        self.preview.clear()
        self._search_in_progress = True
        self._update_enabled_state()
        self._set_busy(True, message=f"Searching {provider}…")

        # Create worker and thread, wire signals, and start
        worker = _SearchWorker(self.remote_service)
        thread = QtCore.QThread(self)
        self._search_worker = worker
        self._search_thread = thread
        worker.moveToThread(thread)
        thread.started.connect(lambda p=provider, q=query, inc=include_imaging: worker.run(p, q, inc))
        worker.started.connect(lambda: self.search_started.emit(provider))  # type: ignore[misc]
        # Streamed results are optional; we primarily update on completion
        worker.record_found.connect(self._handle_record_found)
        worker.finished.connect(self._handle_search_results)
        worker.failed.connect(self._handle_search_error)
        worker.cancelled.connect(self._handle_search_cancelled)
        # Ensure proper cleanup and UI reset
        worker.finished.connect(self._search_finished)
        worker.failed.connect(lambda _msg: self._search_finished())
        worker.cancelled.connect(self._search_finished)
        self._connect_worker_cleanup(worker, thread)
        thread.start()

    def _handle_search_failed(self, message: str) -> None:
        self._set_busy(False)
        self.status_label.setText(f"Search failed: {message}")
        self._records = []
        self._reset_results_table()
        self.preview.clear()

    def _handle_search_cancelled(self) -> None:
        self._set_busy(False)
        self.status_label.setText("Search cancelled.")
        self._records = []
        self._reset_results_table()
        self.preview.clear()

    def _start_download(self, records: list[RemoteRecord]) -> None:
        self._cancel_download_worker()
        if not records:
            return
        self._download_errors: list[str] = []
        self._download_total = len(records)
        self._download_completed = 0
        message = f"Preparing download of {self._download_total} record(s)…"
        self._set_busy(True, message=message)

        worker = self._download_worker_factory()
        thread = QtCore.QThread(self)
        self._download_worker = worker
        self._download_thread = thread
        worker.moveToThread(thread)
        thread.started.connect(lambda records=records: worker.run(records))
        worker.started.connect(self._handle_download_started)
        worker.record_ingested.connect(self._handle_download_progress)
        worker.record_failed.connect(self._handle_download_failure)
        worker.finished.connect(self._handle_download_finished)
        worker.failed.connect(self._handle_download_failed)
        worker.cancelled.connect(self._handle_download_cancelled)
        self._connect_worker_cleanup(worker, thread)
        thread.start()

    def _download_worker_factory(self) -> _DownloadWorker:
        """Construct a download worker bound to this dialog's services."""
        return _DownloadWorker(self.remote_service, self.ingest_service)

    def _handle_download_started(self, total: int) -> None:
        self._download_total = total
        self._download_completed = 0
        self._set_busy(True, message=f"Downloading {total} record(s)…")

    def _handle_download_progress(self, record: RemoteRecord) -> None:
        self._download_completed += 1
        status = f"Imported {self._download_completed}/{self._download_total} record(s)…"
        self.status_label.setText(status)

    def _handle_download_failure(self, record: RemoteRecord, message: str) -> None:
        self._download_errors.append(f"{record.identifier}: {message}")
        self.status_label.setText(
            f"{len(self._download_errors)} failure(s) while importing. Continuing…"
        )

    def _handle_download_finished(self, ingested: list[object]) -> None:
        self._set_busy(False)
        if not ingested:
            if self._download_errors:
                self.status_label.setText(
                    "Downloads completed with errors; no datasets were imported."
                )
            else:
                self.status_label.setText("No datasets were imported.")
            return

        self._ingested = ingested
        if self._download_errors:
            failures = len(self._download_errors)
            self.status_label.setText(
                f"Imported {len(ingested)} dataset(s) with {failures} failure(s)."
            )
        else:
            self.status_label.setText(f"Imported {len(ingested)} dataset(s).")
        self.accept()

    def _handle_download_failed(self, message: str) -> None:
        self._set_busy(False)
        self.status_label.setText(f"Download failed: {message}")

    def _handle_download_cancelled(self) -> None:
        self._set_busy(False)
        self.status_label.setText("Download cancelled.")

    def _set_busy(self, busy: bool, *, message: str | None = None) -> None:
        self._busy = busy
        controls = [
            self.provider_combo,
            self.search_edit,
            self.search_button,
            self.example_combo,
            self.include_imaging_checkbox,
        ]
        if busy:
            self._control_enabled_state = {control: control.isEnabled() for control in controls}
            for control in controls:
                control.setEnabled(False)
        else:
            for control in controls:
                enabled = self._control_enabled_state.get(control, True)
                if control is self.include_imaging_checkbox and not control.isVisible():
                    control.setEnabled(False)
                else:
                    control.setEnabled(enabled)
            self._control_enabled_state = {}
        if busy:
            self.download_button.setEnabled(False)
            if self.progress_movie and self.progress_movie.isValid():
                self.progress_movie.start()
            self.progress_label.setVisible(True)
        else:
            if self.progress_movie and self.progress_movie.isValid():
                self.progress_movie.stop()
            self.progress_label.setVisible(False)
            self._update_download_button_state()
        if message is not None:
            self.status_label.setText(message)

    def _update_download_button_state(self) -> None:
        if self._busy:
            self.download_button.setEnabled(False)
            return
        selected = self.results.selectionModel().selectedRows()
        enable = bool(selected)
        self.download_button.setEnabled(enable)
        if enable:
            count = len(selected)
            if count == 1:
                self.download_button.setText("Download & Import")
            else:
                self.download_button.setText(f"Download & Import ({count} selected)")
        else:
            self.download_button.setText("Download & Import")

    def _connect_worker_cleanup(
        self,
        worker: QtCore.QObject,
        thread: QtCore.QThread,
    ) -> None:
        def _do_cleanup() -> None:
            if thread.isRunning():
                thread.quit()
                # Non-blocking: let event loop finish thread shutdown
                # Calling wait() here causes "QThread::wait: Thread tried to wait on itself"
            worker.deleteLater()
            thread.deleteLater()
            if worker is self._search_worker:
                self._search_worker = None
                self._search_thread = None
            if worker is self._download_worker:
                self._download_worker = None
                self._download_thread = None

        def _schedule_cleanup(*_args: object) -> None:
            # Ensure cleanup runs on the dialog's (GUI) thread to avoid
            # waiting on the current worker thread and triggering
            # "QThread::wait: Thread tried to wait on itself".
            QtCore.QTimer.singleShot(0, _do_cleanup)

        worker.finished.connect(_schedule_cleanup)
        worker.failed.connect(_schedule_cleanup)
        worker.cancelled.connect(_schedule_cleanup)

    def _cancel_search_worker(self) -> None:
        if self._search_worker is None:
            return
        queued = getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection
        QtCore.QMetaObject.invokeMethod(
            self._search_worker,
            "cancel",
            queued,
        )

    def _cancel_download_worker(self) -> None:
        if self._download_worker is None:
            return
        queued = getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection
        QtCore.QMetaObject.invokeMethod(
            self._download_worker,
            "cancel",
            queued,
        )

    def _await_thread_shutdown(
        self,
        *,
        thread_attr: str,
        worker_attr: str,
        timeout_ms: int | None = None,
    ) -> bool:
        """Request shutdown and check if the worker thread has stopped.

        Returns ``True`` when the thread has stopped. When ``timeout_ms`` is
        ``None``, waits indefinitely (only used during app shutdown). A finite
        timeout checks without blocking, allowing the caller to poll using
        ``QtCore.QTimer``.
        """

        thread = getattr(self, thread_attr)
        worker = getattr(self, worker_attr)
        if thread is None:
            return True
        
        # Only quit if still running
        if thread.isRunning():
            thread.quit()
        
        # Check if finished without blocking (except during app shutdown)
        if timeout_ms is not None:
            # Non-blocking check: don't wait, just see if it's done
            if thread.isRunning():
                return False
        else:
            # App is shutting down, event loop gone, must block
            if thread.isRunning():
                thread.wait()
        
        # Clean up
        if worker is not None:
            worker.deleteLater()
        thread.deleteLater()
        setattr(self, worker_attr, None)
        setattr(self, thread_attr, None)
        return True

    def _schedule_thread_shutdown(
        self,
        pending: list[tuple[str, str]],
        *,
        interval_ms: int = 100,
    ) -> None:
        """Retry thread shutdown without blocking the UI."""

        # ``QtCore.QTimer.singleShot`` copies basic Python values, so we keep the
        # payload small and rebuild the remaining list on each poll.

        def _poll() -> None:
            remaining: list[tuple[str, str]] = []
            for thread_attr, worker_attr in pending:
                if not self._await_thread_shutdown(
                    thread_attr=thread_attr,
                    worker_attr=worker_attr,
                    timeout_ms=0,
                ):
                    remaining.append((thread_attr, worker_attr))
            if remaining:
                next_interval = min(interval_ms * 2, 1000)
                QtCore.QTimer.singleShot(
                    next_interval,
                    lambda rem=remaining, iv=next_interval: self._schedule_thread_shutdown(
                        rem,
                        interval_ms=iv,
                    ),
                )

        QtCore.QTimer.singleShot(interval_ms, _poll)

    def reject(self) -> None:
        self._cancel_search_worker()
        self._cancel_download_worker()
        pending: list[tuple[str, str]] = []
        if not self._await_thread_shutdown(
            thread_attr="_search_thread",
            worker_attr="_search_worker",
            timeout_ms=25,
        ):
            pending.append(("_search_thread", "_search_worker"))
        if not self._await_thread_shutdown(
            thread_attr="_download_thread",
            worker_attr="_download_worker",
            timeout_ms=25,
        ):
            pending.append(("_download_thread", "_download_worker"))
        if pending:
            self._schedule_thread_shutdown(pending)
        super().reject()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # pragma: no cover - Qt event hook
        """Ensure worker threads stop when the application is shutting down."""

        if QtCore.QCoreApplication.closingDown():
            # ``reject`` keeps the dialog responsive by polling the worker threads
            # with short timeouts. When the whole application is quitting we no
            # longer have an event loop to service the timers, so block until the
            # threads have stopped to avoid crashing Qt's parent–child teardown.
            self._cancel_search_worker()
            self._cancel_download_worker()
            self._await_thread_shutdown(
                thread_attr="_search_thread",
                worker_attr="_search_worker",
            )
            self._await_thread_shutdown(
                thread_attr="_download_thread",
                worker_attr="_download_worker",
            )
        super().closeEvent(event)

    def _on_provider_changed(self, index: int | None = None) -> None:
        # Accept the index argument emitted by Qt while keeping the logic driven
        # by the current provider string so external callers can trigger the
        # refresh without supplying an index explicitly.
        if index is not None:
            # Qt passes the numeric index; the logic below derives values from
            # the provider string so the argument is intentionally ignored.
            pass
        provider = self.provider_combo.currentText()
        is_mast = provider in {
            RemoteDataService.PROVIDER_MAST,
            RemoteDataService.PROVIDER_EXOSYSTEMS,
        }
        placeholder = self._provider_placeholders.get(provider)
        if placeholder:
            self.search_edit.setPlaceholderText(placeholder)
        else:
            self.search_edit.setPlaceholderText("Element, target name, or keyword…")
        hint = self._provider_hints.get(provider, "")
        if self._dependency_hint:
            parts = [part for part in (hint, self._dependency_hint) if part]
            hint = "\n".join(parts)
        self.hint_label.setText(hint)

        examples = self._provider_examples.get(provider, [])
        self.example_combo.blockSignals(True)
        self.example_combo.clear()
        self.example_combo.addItem("Examples…")
        for label, query in examples:
            self.example_combo.addItem(label, userData=query)
        self.example_combo.setCurrentIndex(0)
        self.example_combo.setEnabled(bool(examples))
        self.example_combo.blockSignals(False)

        self.include_imaging_checkbox.blockSignals(True)
        self.include_imaging_checkbox.setVisible(is_mast)
        self.include_imaging_checkbox.setEnabled(is_mast)
        if not is_mast:
            self.include_imaging_checkbox.setChecked(False)
        self.include_imaging_checkbox.blockSignals(False)

    def _build_provider_query(self, provider: str, text: str) -> dict[str, str]:
        stripped = text.strip()
        if provider == RemoteDataService.PROVIDER_NIST:
            if not stripped:
                return {}
            # Support simple "key=value; key2=value2" parsing for convenience
            query: dict[str, str] = {}
            parts = [part.strip() for part in stripped.split(";") if part.strip()]
            for part in parts:
                if "=" not in part:
                    continue
                key, value = part.split("=", 1)
                key = key.strip().lower()
                value = value.strip()
                if not value:
                    continue
                if key in {"element", "spectrum", "linename"}:
                    query["element"] = value
                elif key in {"ion", "ion_stage"}:
                    query["ion_stage"] = value
                elif key in {"keyword", "text"}:
                    query["text"] = value
            if not query:
                query = {"text": stripped}
            return query
        if provider == RemoteDataService.PROVIDER_MAST:
            return {"target_name": stripped} if stripped else {}
        if provider == RemoteDataService.PROVIDER_EXOSYSTEMS:
            return {"text": stripped} if stripped else {}
        return {"text": stripped} if stripped else {}

    def _on_quick_pick_selected(self, target: Mapping[str, Any]) -> None:
        canonical = str(
            target.get("object_name")
            or target.get("display_name")
            or (target.get("names") or [""])[0]
        ).strip()
        if not canonical:
            return

        provider_index = self.provider_combo.findText(RemoteDataService.PROVIDER_EXOSYSTEMS)
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)
        self.search_edit.setText(canonical)
        self._on_search()

    def _on_example_selected(self, index: int) -> None:
        if index <= 0:
            return
        query_text = self.example_combo.itemData(index)
        if isinstance(query_text, str):
            self.search_edit.setText(query_text)
            self._on_search()
    def _update_preview(self) -> None:
        indexes = self.results.selectionModel().selectedRows()
        if not indexes:
            self.preview.clear()
            return
        # Use filtered records for correct mapping
        row_index = indexes[0].row()
        if row_index < 0 or row_index >= len(self._filtered_records):
            self.preview.clear()
            return
        record = self._filtered_records[row_index]
        metadata = record.metadata if isinstance(record.metadata, Mapping) else {}
        narrative_lines: list[str] = []
        summary = self._format_exoplanet_summary(metadata)
        if summary:
            narrative_lines.append(summary)
        instrument = self._format_instrument(record.metadata)
        mission = self._format_mission(record.metadata)
        mission_parts = [part for part in (mission, instrument) if part]
        if mission_parts:
            narrative_lines.append(" | ".join(mission_parts))
        citation = self._extract_citation(record.metadata)
        if citation:
            narrative_lines.append(f"Citation: {citation}")
        if narrative_lines:
            narrative_lines.append("")
        narrative_lines.append(json.dumps(metadata, indent=2, ensure_ascii=False))
        self.preview.setPlainText("\n".join(narrative_lines))

    def _on_selection_changed(self) -> None:
        self._update_preview()
    def _populate_results_table(self, records: Sequence[RemoteRecord]) -> None:
        self._clear_result_widgets()
        
        # Filter records based on current filter
        filtered = [r for r in records if self._should_show_record(r)]
        self._filtered_records = filtered  # Store filtered records for row mapping
        
        self.results.setRowCount(len(filtered))
        for row, record in enumerate(filtered):
            self._set_table_text(row, 0, record.identifier)
            self._set_table_text(row, 1, record.title)
            self._set_table_text(row, 2, self._format_target(record))
            self._set_table_text(row, 3, self._format_mission(record.metadata))
            self._set_table_text(row, 4, self._format_instrument(record.metadata))
            self._set_table_text(row, 5, self._format_product(record.metadata))
            self._set_table_text(row, 6, "")
            self._set_download_widget(row, 6, record.download_url)
            self._set_table_text(row, 7, "")
            self._set_preview_widget(row, 7, record.metadata)

    def _set_table_text(self, row: int, column: int, value: str | None) -> None:
        item = QtWidgets.QTableWidgetItem(value or "")
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        self.results.setItem(row, column, item)
        
    def _set_download_widget(self, row: int, column: int, url: str) -> None:
        label = QtWidgets.QLabel(self.results)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        label.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        if not url:
            label.setText("N/A")
            label.setEnabled(False)
            label.setToolTip("No download available")
            label.setOpenExternalLinks(False)
            label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        else:
            hyperlink = self._link_for_download(url)
            escaped = html.escape(hyperlink)
            label.setText(f'<a href="{escaped}">Open</a>')
            label.setOpenExternalLinks(True)
            label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
            tooltip = url
            if hyperlink != url:
                tooltip = f"{url}\n{hyperlink}"
            label.setToolTip(tooltip)
        self.results.setCellWidget(row, column, label)

    def _link_for_download(self, url: str) -> str:
        """Return a user-friendly hyperlink for a given download URL.

        - For MAST dataURIs (mast:...), use the MAST Download API endpoint so a browser
          can open the file directly.
        - For NIST pseudo-URIs, link to the NIST ASD site since the CSV is generated locally.
        - For regular http(s) links, return as-is.
        - Otherwise, fall back to the original string.
        """
        try:
            from urllib.parse import quote
        except Exception:  # pragma: no cover - extremely defensive
            quote = None  # type: ignore[assignment]

        if isinstance(url, str) and url.startswith("mast:"):
            if quote is not None:
                return f"https://mast.stsci.edu/api/v0.1/Download/file?uri={quote(url, safe='')}"
            return f"https://mast.stsci.edu/api/v0.1/Download/file?uri={url}"
        if isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
            return url
        if isinstance(url, str) and (url.startswith("nist-asd:") or url.startswith("nist-asd://")):
            return "https://physics.nist.gov/PhysRefData/ASD/lines_form.html"
        return url

    def _set_preview_widget(self, row: int, column: int, metadata: Mapping[str, Any] | Any) -> None:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        preview_url = self._first_text(mapping, [
            "preview_url",
            "previewURL",
            "preview_uri",
            "QuicklookURL",
            "quicklook_url",
            "productPreviewURL",
            "thumbnailURL",
            "thumbnail_uri",
        ])
        citation = self._extract_citation(mapping)
        if not preview_url and not citation:
            self.results.setCellWidget(row, column, None)
            self._set_table_text(row, column, "")
            return

        label = QtWidgets.QLabel(self.results)
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        label.setWordWrap(True)
        label.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        fragments: list[str] = []
        if preview_url:
            escaped_url = html.escape(preview_url)
            fragments.append(f'<a href="{escaped_url}">Preview</a>')
            label.setToolTip(preview_url)
        if citation:
            fragments.append(html.escape(citation))
        label.setText("<br/>".join(fragments))
        self.results.setCellWidget(row, column, label)

    def _clear_result_widgets(self) -> None:
        for row in range(self.results.rowCount()):
            for column in range(self.results.columnCount()):
                widget = self.results.cellWidget(row, column)
                if widget is not None:
                    widget.deleteLater()
                    self.results.setCellWidget(row, column, None)
        self.results.clearContents()
        self.results.setRowCount(0)

    def _reset_results_table(self) -> None:
        self._clear_result_widgets()
        self._all_records = []
        self._filtered_records = []
        self.status_label.setText("")

    def _on_queue_downloads(self) -> None:
        if self._busy:
            return
        selected = self.results.selectionModel().selectedRows()
        if not selected:
            self.status_label.setText("Select at least one record to import.")
            return

        # Use filtered records for correct mapping
        records = [self._filtered_records[index.row()] for index in selected]
        self._start_download(records)

    def _refresh_provider_state(self) -> None:
        providers = [
            provider
            for provider in self.remote_service.providers()
            if provider != RemoteDataService.PROVIDER_NIST
        ]
        self.provider_combo.clear()
        if providers:
            self.provider_combo.addItems(providers)
            self.provider_combo.setEnabled(True)
            self.search_edit.setEnabled(True)
            self.search_button.setEnabled(True)
            self._provider_placeholders = {
                RemoteDataService.PROVIDER_EXOSYSTEMS: (
                    "Planet, host star, or solar system target (e.g. Mercury, HD 189733 b, Tau Ceti)…"
                ),
                RemoteDataService.PROVIDER_MAST: "MAST target name or observation keyword (e.g. NIRSpec, NGC 7023)…",
            }
            self._provider_hints = {
                RemoteDataService.PROVIDER_EXOSYSTEMS: (
                    "Chains NASA Exoplanet Archive coordinates with MAST product listings and Exo.MAST file lists."
                    " Quick-picks cover Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune, and Pluto while"
                    " examples highlight host stars (Vega, Tau Ceti, HD 189733) and transiting exoplanets."
                ),
                RemoteDataService.PROVIDER_MAST: (
                    "MAST requests favour calibrated spectra (IFS cubes, slits, prisms). Enable "
                    "\"Include imaging\" to broaden results with calibrated image products."
                ),
            }
            self._provider_examples = {
                RemoteDataService.PROVIDER_EXOSYSTEMS: [
                    ("HD 189733 b – JWST/NIRISS", "HD 189733 b"),
                    ("HD 189733 – host star", "HD 189733"),
                    ("TRAPPIST-1 system", "TRAPPIST-1"),
                    ("Vega – CALSPEC standard", "Vega"),
                    ("Tau Ceti – nearby solar analog", "Tau Ceti"),
                ],
                RemoteDataService.PROVIDER_MAST: [
                    ("NGC 7023 – JWST/NIRSpec", "NGC 7023"),
                    ("SN 1987A – HST/STIS", "SN 1987A"),
                    ("HD 189733 – JWST/NIRISS", "HD 189733"),
                ],
            }
        else:
            self.provider_combo.setEnabled(False)
            self.search_edit.setEnabled(False)
            self.search_button.setEnabled(False)
            self.example_combo.setEnabled(False)
            self.include_imaging_checkbox.setVisible(False)
            self.include_imaging_checkbox.setEnabled(False)
            self.include_imaging_checkbox.setChecked(False)
            self._provider_placeholders = {}
            self._provider_hints = {}
            self._provider_examples = {}

        self._refresh_quick_pick_state(providers)

        unavailable = self.remote_service.unavailable_providers()
        if unavailable:
            messages = []
            for provider, reason in unavailable.items():
                messages.append(f"{provider}: {reason}")
            self._dependency_hint = "\n".join(messages)
        else:
            self._dependency_hint = ""

        if not providers:
            if not unavailable:
                self.status_label.setText("Remote catalogues are temporarily unavailable.")
            else:
                self.status_label.setText(
                    "Remote catalogues are unavailable until the required optional dependencies are installed."
                )
        else:
            self.status_label.clear()

        self._on_provider_changed()
        self._set_busy(False)

    def _refresh_quick_pick_state(self, providers: Sequence[str]) -> None:
        menu = getattr(self, "quick_pick_menu", None)
        if menu is None:
            return

        menu.clear()
        self._quick_pick_targets = []

        available = RemoteDataService.PROVIDER_EXOSYSTEMS in providers
        self.quick_pick_button.setEnabled(available)

        if not available:
            self.quick_pick_button.setToolTip(
                "Solar System quick picks require the MAST ExoSystems provider."
            )
            return

        targets = self.remote_service.curated_targets(category="solar_system")
        if not targets:
            self.quick_pick_button.setToolTip(
                "Solar System quick picks become available once curated targets are configured."
            )
            return

        tooltip = (
            "Quick-pick Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto."
        )
        self.quick_pick_button.setToolTip(tooltip)
        for target in targets:
            label = str(target.get("display_name") or target.get("object_name") or "").strip()
            canonical = str(target.get("object_name") or label).strip()
            if not label or not canonical:
                continue
            action = menu.addAction(label)
            action.setData(canonical)
            action.triggered.connect(
                lambda _checked=False, entry=target: self._on_quick_pick_selected(entry)
            )
            self._quick_pick_targets.append(target)

    # (removed unused worker bootstrap helpers; we wire workers inline where started)

    def _handle_search_results(self, records: list[RemoteRecord]) -> None:
        # Finalise with the complete set (deduped) from the worker
        self._records = list(records)
        self._populate_results_table(self._records)
        
        # Count how many match the current filter
        filtered = [r for r in records if self._should_show_record(r)]
        total_count = len(records)
        visible_count = len(filtered)
        
        provider_name = self.provider_combo.currentText()
        if visible_count == total_count:
            self.status_label.setText(
                f"{total_count} result(s) fetched from {provider_name}."
            )
        else:
            self.status_label.setText(
                f"Showing {visible_count} of {total_count} result(s) from {provider_name}."
            )
        
        if filtered:
            self.results.selectRow(0)
        else:
            self.preview.clear()
        self.search_completed.emit(records)

    def _handle_record_found(self, record: RemoteRecord) -> None:
        """Incrementally add a found record to the table to reduce TTFB."""
        # Track full set regardless of visibility
        self._records.append(record)
        # Respect current filter when adding to the table
        if not self._should_show_record(record):
            # Still update the count/status using totals
            self.status_label.setText(f"Fetched {len(self._records)} record(s)…")
            return

        # Append to filtered list and insert a new row
        self._filtered_records.append(record)
        row = self.results.rowCount()
        self.results.insertRow(row)
        self._set_table_text(row, 0, record.identifier)
        self._set_table_text(row, 1, record.title)
        self._set_table_text(row, 2, self._format_target(record))
        self._set_table_text(row, 3, self._format_mission(record.metadata))
        self._set_table_text(row, 4, self._format_instrument(record.metadata))
        self._set_table_text(row, 5, self._format_product(record.metadata))
        self._set_table_text(row, 6, "")
        self._set_download_widget(row, 6, record.download_url)
        self._set_table_text(row, 7, "")
        self._set_preview_widget(row, 7, record.metadata)
        # Update status with visible/total counts
        visible = len(self._filtered_records)
        total = len(self._records)
        provider_name = self.provider_combo.currentText()
        if visible == total:
            self.status_label.setText(f"{visible} result(s) fetched from {provider_name}…")
        else:
            self.status_label.setText(f"Showing {visible} of {total} result(s) from {provider_name}…")

    def _handle_search_error(self, message: str) -> None:
        QtWidgets.QMessageBox.critical(self, "Search failed", message)
        self.status_label.setText(message)
        self.search_failed.emit(message)

    def _search_finished(self) -> None:
        self._search_in_progress = False
        self._update_enabled_state()
        self._set_busy(False)

    # (removed duplicate download handlers; earlier ones handle progress/finish/failure)

    def _update_enabled_state(self) -> None:
        searching = self._search_in_progress
        downloading = self._download_in_progress
        providers_available = self.provider_combo.count() > 0

        self.provider_combo.setEnabled(providers_available and not searching)
        self.search_edit.setEnabled(not searching)
        self.search_button.setEnabled(not searching)
        self.example_combo.setEnabled(not searching and self.example_combo.count() > 1)
        self.include_imaging_checkbox.setEnabled(
            self.include_imaging_checkbox.isVisible() and not searching
        )
        self.download_button.setEnabled(bool(self._records) and not downloading and not searching)

    # (removed duplicate lifecycle/shutdown helpers; a single reject/closeEvent earlier handles cleanup safely)

    # ------------------------------------------------------------------
    def _format_target(self, record: RemoteRecord) -> str:
        metadata = record.metadata if isinstance(record.metadata, Mapping) else {}
        exosystem = metadata.get("exosystem") if isinstance(metadata.get("exosystem"), Mapping) else None
        if exosystem:
            planet = self._first_text(exosystem, ["planet_name", "display_name"])
            host = self._first_text(exosystem, ["host_name", "object_name"])
            if planet and host:
                return f"{planet} (host: {host})"
            if planet:
                return planet
            if host:
                return host
        return self._first_text(metadata, ["target_display", "target_name", "object_name", "obs_id"]) or record.title

    # Small utility used by formatting helpers to fetch the first non-empty text value
    def _first_text(self, mapping: Mapping[str, Any] | Any, keys: list[str]) -> str:
        source = mapping if isinstance(mapping, Mapping) else {}
        for key in keys:
            if key not in source:
                continue
            value = source.get(key)
            if value is None:
                continue
            if isinstance(value, str):
                text = value.strip()
                if text:
                    return text
            else:
                # Gracefully coerce non-string simple values
                try:
                    text = str(value).strip()
                except Exception:
                    text = ""
                if text and text.lower() != "nan":
                    return text
        return ""

    def _format_mission(self, metadata: Mapping[str, Any] | Any) -> str:
        mission = self._first_text(metadata, ["obs_collection", "telescope_name", "project"])
        proposal = self._first_text(metadata, ["proposal_pi", "proposal_id"])
        if mission and proposal:
            return f"{mission} (PI: {proposal})"
        return mission

    def _format_instrument(self, metadata: Mapping[str, Any] | Any) -> str:
        instrument = self._first_text(metadata, ["instrument_name", "instrument", "filters"])
        aperture = self._first_text(metadata, ["aperture", "optical_element"])
        if instrument and aperture:
            return f"{instrument} ({aperture})"
        return instrument

    def _format_product(self, metadata: Mapping[str, Any] | Any) -> str:
        product = self._first_text(metadata, ["productType", "dataproduct_type", "product_type"])
        calib = metadata.get("calib_level") if isinstance(metadata, Mapping) else None
        if product and calib is not None:
            return f"{product} (calib {calib})"
        return product

    def _format_exoplanet_summary(self, metadata: Mapping[str, Any] | Any) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        summary = mapping.get("exoplanet_summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()

        def _normalise_year(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, int):
                return str(value)
            if isinstance(value, float):
                if math.isnan(value):
                    return ""
                return str(int(value))
            if isinstance(value, str):
                text = value.strip()
                if not text or text.lower() == "nan":
                    return ""
                try:
                    numeric = float(text)
                except ValueError:
                    return text
                if math.isnan(numeric):
                    return ""
                return str(int(numeric))
            return ""

        exoplanet = mapping.get("exoplanet")
        if isinstance(exoplanet, Mapping):
            name = self._first_text(exoplanet, ["display_name", "name"])
            classification = self._first_text(exoplanet, ["classification", "type"])
            host = self._first_text(exoplanet, ["host_star", "host"])
            discovery_method = self._first_text(exoplanet, ["discovery_method", "discovered_via"])
            discovery_facility = self._first_text(exoplanet, ["discovery_facility", "facility"])
            discovery_year = _normalise_year(exoplanet.get("discovery_year"))

            details: list[str] = []
            if classification:
                details.append(classification)
            if host:
                details.append(f"Host: {host}")

            discovery_bits = [
                part
                for part in (discovery_method, discovery_facility, discovery_year)
                if part
            ]
            if discovery_bits:
                details.append(f"Discovery: {', '.join(discovery_bits)}")

            if name or details:
                body = ", ".join(details) if details else ""
                return " – ".join(filter(None, [name, body]))
        return ""

    def _extract_citation(self, metadata: Mapping[str, Any] | Any) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        citations: list[str] = []

        def _collect(source: Any) -> None:
            if not isinstance(source, list):
                return
            for entry in source:
                if not isinstance(entry, Mapping):
                    continue
                title = entry.get("title") or entry.get("name")
                note = entry.get("notes")
                doi = entry.get("doi")
                url = entry.get("url")
                fragment = title or url or doi
                if not fragment:
                    continue
                detail_parts = [fragment]
                if doi:
                    detail_parts.append(f"DOI: {doi}")
                if url:
                    detail_parts.append(url)
                if note:
                    detail_parts.append(note)
                citations.append(" — ".join(detail_parts))

        _collect(mapping.get("citations"))
        exosystem = mapping.get("exosystem") if isinstance(mapping.get("exosystem"), Mapping) else None
        if exosystem:
            _collect(exosystem.get("citations"))

        return "; ".join(dict.fromkeys(citations))

    @staticmethod
    def _format_number(value: Any, *, suffix: str = "") -> str:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if math.isnan(number):
            return "?"
        if abs(number) >= 1000:
            formatted = f"{number:,.0f}"
        elif abs(number) >= 1:
            formatted = f"{number:,.1f}"
        else:
            formatted = f"{number:.3g}"
        return f"{formatted}{suffix}"


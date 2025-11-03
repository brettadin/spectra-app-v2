"""Remote data search and download panel for the Spectra main window.

This panel provides:
- Provider selection (MAST, ExoSystems, etc.)
- Search UI with streaming results
- Download & import with progress tracking
- Quick-load for bundled solar system samples
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, List

from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()

from app.services import RemoteDataService, DataIngestService, Spectrum
from app.workers.remote import SearchWorker, DownloadWorker


Signal = getattr(QtCore, "Signal", None)
if Signal is None:  # pragma: no cover
    Signal = getattr(QtCore, "pyqtSignal")


class RemoteDataPanel(QtWidgets.QWidget):
    """Standalone panel for remote data search and import.
    
    Signals
    -------
    spectra_imported : Signal(list)
        Emitted when spectra are successfully imported with list of Spectrum objects.
    status_message : Signal(str)
        Emitted when status text should be logged (channel, message).
    """
    
    spectra_imported = Signal(list)  # type: ignore[misc]
    status_message = Signal(str, str)  # type: ignore[misc]  # (channel, message)
    
    def __init__(
        self,
        remote_service: RemoteDataService,
        ingest_service: DataIngestService,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.remote_service = remote_service
        self.ingest_service = ingest_service
        
        # State
        self._records: List[Any] = []
        self._search_worker: SearchWorker | None = None
        self._search_thread: QtCore.QThread | None = None
        self._download_worker: DownloadWorker | None = None
        self._download_thread: QtCore.QThread | None = None
        self._download_total = 0
        self._download_completed = 0
        self._download_errors: list[str] = []
        
        self._setup_ui()
        self._initialize_providers()
    
    def _setup_ui(self) -> None:
        """Build the panel UI."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Controls row
        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(QtWidgets.QLabel("Catalogue:"))
        
        self.provider_combo = QtWidgets.QComboBox()
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        controls.addWidget(self.provider_combo)
        
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Target name or keyword…")
        self.search_edit.returnPressed.connect(self._on_search)
        controls.addWidget(self.search_edit, 1)
        
        self.search_button = QtWidgets.QPushButton("Search")
        self.search_button.clicked.connect(self._on_search)
        controls.addWidget(self.search_button)
        
        # Quick load of curated local samples
        self.load_samples_button = QtWidgets.QPushButton("Load Solar System Samples")
        self.load_samples_button.setToolTip("Import all CSV spectra under samples/solar_system")
        self.load_samples_button.clicked.connect(self._on_load_solar_system_samples)
        controls.addWidget(self.load_samples_button)
        
        layout.addLayout(controls)
        
        # Results table
        self.results_table = QtWidgets.QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(["ID", "Title", "Target", "Telescope"])
        self.results_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.results_table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.results_table, 1)
        
        # Import button
        self.import_button = QtWidgets.QPushButton("Download && Import Selected")
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self._on_import)
        layout.addWidget(self.import_button)
        
        # Status label
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Progress bar for downloads
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
    
    def _initialize_providers(self) -> None:
        """Populate provider combo with available catalogues."""
        providers = self.remote_service.providers()
        # Filter out NIST (handled in Reference tab)
        providers = [p for p in providers if p != RemoteDataService.PROVIDER_NIST]
        
        self.provider_combo.clear()
        if providers:
            self.provider_combo.addItems(providers)
            self.provider_combo.setEnabled(True)
            self.search_edit.setEnabled(True)
            self.search_button.setEnabled(True)
        else:
            self.provider_combo.setEnabled(False)
            self.search_edit.setEnabled(False)
            self.search_button.setEnabled(False)
            self.status_label.setText("Remote data providers unavailable")
        
        self._on_provider_changed()
    
    def _on_provider_changed(self) -> None:
        """Update placeholder text based on selected provider."""
        provider = self.provider_combo.currentText()
        
        if provider == RemoteDataService.PROVIDER_MAST:
            self.search_edit.setPlaceholderText("MAST target name (e.g. NGC 7023, SN 1987A)…")
        elif provider == RemoteDataService.PROVIDER_EXOSYSTEMS:
            self.search_edit.setPlaceholderText("Planet, star, or solar system target (e.g. HD 189733 b, Jupiter)…")
        else:
            self.search_edit.setPlaceholderText("Target name or keyword…")
    
    def _on_search(self) -> None:
        """Initiate remote search with streaming results."""
        provider = self.provider_combo.currentText()
        query_text = self.search_edit.text().strip()
        
        if not query_text:
            self.status_label.setText("Enter a search term")
            return
        
        # Build provider-specific query
        if provider == RemoteDataService.PROVIDER_MAST:
            query = {"target_name": query_text}
        elif provider == RemoteDataService.PROVIDER_EXOSYSTEMS:
            query = {"text": query_text}
        else:
            query = {"text": query_text}
        
        # Reset UI and state
        self._cancel_search_worker()
        self._records = []
        self.results_table.setRowCount(0)
        self.import_button.setEnabled(False)
        self.status_label.setText(f"Searching {provider}…")
        self.search_button.setEnabled(False)
        
        # Create streaming worker
        worker = SearchWorker(self.remote_service)
        thread = QtCore.QThread(self)
        self._search_worker = worker
        self._search_thread = thread
        worker.moveToThread(thread)
        
        thread.started.connect(lambda p=provider, q=query: worker.run(p, q, False))
        worker.record_found.connect(self._handle_record_found)
        worker.finished.connect(self._handle_search_finished)
        worker.failed.connect(self._handle_search_failed)
        worker.cancelled.connect(self._handle_search_cancelled)
        
        # Cleanup
        def _cleanup() -> None:
            if thread.isRunning():
                thread.quit()
            worker.deleteLater()
            thread.deleteLater()
            if self._search_worker is worker:
                self._search_worker = None
                self._search_thread = None
        
        worker.finished.connect(lambda *_: QtCore.QTimer.singleShot(0, _cleanup))
        worker.failed.connect(lambda *_: QtCore.QTimer.singleShot(0, _cleanup))
        worker.cancelled.connect(lambda *_: QtCore.QTimer.singleShot(0, _cleanup))
        thread.start()
    
    def _cancel_search_worker(self) -> None:
        """Cancel any running search."""
        if self._search_worker is None:
            return
        queued = getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection
        QtCore.QMetaObject.invokeMethod(self._search_worker, "cancel", queued)
    
    def _handle_record_found(self, record: Any) -> None:
        """Handle streamed search result (runs on GUI thread)."""
        def _append():
            self._records.append(record)
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            # ID
            item = QtWidgets.QTableWidgetItem(str(getattr(record, 'identifier', '')))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 0, item)
            
            # Title
            item = QtWidgets.QTableWidgetItem(str(getattr(record, 'title', '')))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 1, item)
            
            # Target
            metadata = getattr(record, 'metadata', {}) if isinstance(getattr(record, 'metadata', {}), dict) else {}
            target = str(metadata.get("target_name", ""))
            item = QtWidgets.QTableWidgetItem(target)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 2, item)
            
            # Telescope
            telescope = str(metadata.get("obs_collection", metadata.get("telescope_name", "")))
            item = QtWidgets.QTableWidgetItem(telescope)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 3, item)
        
        QtCore.QTimer.singleShot(0, _append)
    
    def _handle_search_finished(self, results: List[Any]) -> None:
        """Handle search completion."""
        def _done():
            self.search_button.setEnabled(True)
            count = len(results)
            self.status_label.setText(f"Found {count} result(s)" if count else "No results found")
        QtCore.QTimer.singleShot(0, _done)
    
    def _handle_search_failed(self, message: str) -> None:
        """Handle search failure."""
        def _fail():
            self.search_button.setEnabled(True)
            self.status_label.setText(f"Search failed: {message}")
            self.status_message.emit("Remote", f"Search failed: {message}")  # type: ignore[attr-defined]
        QtCore.QTimer.singleShot(0, _fail)
    
    def _handle_search_cancelled(self) -> None:
        """Handle search cancellation."""
        def _cancel():
            self.search_button.setEnabled(True)
            self.status_label.setText("Search cancelled")
        QtCore.QTimer.singleShot(0, _cancel)
    
    def _on_selection_changed(self) -> None:
        """Update import button state when selection changes."""
        selected = self.results_table.selectionModel().selectedRows()
        self.import_button.setEnabled(len(selected) > 0)
        
        if len(selected) == 1:
            self.import_button.setText("Download & Import")
        elif len(selected) > 1:
            self.import_button.setText(f"Download & Import ({len(selected)} selected)")
        else:
            self.import_button.setText("Download & Import Selected")
    
    def _on_import(self) -> None:
        """Download and import selected records with progress tracking."""
        selected = self.results_table.selectionModel().selectedRows()
        if not selected:
            return
        
        records = [self._records[index.row()] for index in selected]
        self.status_label.setText(f"Preparing download of {len(records)} record(s)…")
        self.import_button.setEnabled(False)
        
        # Start background download worker
        worker = DownloadWorker(self.remote_service, self.ingest_service)
        thread = QtCore.QThread(self)
        self._download_worker = worker
        self._download_thread = thread
        worker.moveToThread(thread)
        
        thread.started.connect(lambda recs=records: worker.run(recs))
        
        # Connect signals with queued connection for thread safety
        queued = getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection
        worker.started.connect(self._on_download_started, queued)
        worker.record_progress.connect(self._on_download_progress, queued)
        worker.record_ingested.connect(self._on_record_ingested, queued)
        worker.record_failed.connect(self._on_download_failed, queued)
        worker.finished.connect(self._on_download_finished, queued)
        worker.failed.connect(self._on_download_error, queued)
        worker.cancelled.connect(self._on_download_cancelled, queued)
        
        # Cleanup
        def _cleanup() -> None:
            if thread.isRunning():
                thread.quit()
            worker.deleteLater()
            thread.deleteLater()
            if self._download_worker is worker:
                self._download_worker = None
                self._download_thread = None
        
        worker.finished.connect(lambda *_: QtCore.QTimer.singleShot(0, _cleanup))
        worker.failed.connect(lambda *_: QtCore.QTimer.singleShot(0, _cleanup))
        worker.cancelled.connect(lambda *_: QtCore.QTimer.singleShot(0, _cleanup))
        thread.start()
    
    def _cancel_download_worker(self) -> None:
        """Cancel any running download."""
        if self._download_worker is None:
            return
        queued = getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection
        QtCore.QMetaObject.invokeMethod(self._download_worker, "cancel", queued)
    
    def _on_download_started(self, total: int) -> None:
        """Handle download start."""
        self._download_total = total
        self._download_completed = 0
        self._download_errors = []
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Downloading {total} record(s)…")
    
    def _on_download_progress(self, record: Any, received: int, total: int) -> None:
        """Handle download progress update."""
        label = getattr(record, "title", getattr(record, "identifier", "Remote item"))
        show_total = total >= 0
        
        if show_total:
            span = total or 1
            self.progress_bar.setRange(0, span)
            self.progress_bar.setValue(min(received, span))
            message = f"Downloading {label}: {self._format_bytes(received)} / {self._format_bytes(total)}"
        else:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setValue(0)
            message = f"Downloading {label}: {self._format_bytes(received)} received"
        
        self.status_label.setText(message)
    
    def _on_record_ingested(self, record: Any) -> None:
        """Handle successful record ingest."""
        self._download_completed += 1
        self.status_label.setText(
            f"Imported {self._download_completed}/{self._download_total} record(s)…"
        )
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
    
    def _on_download_failed(self, record: Any, message: str) -> None:
        """Handle individual record download failure."""
        identifier = getattr(record, "identifier", "")
        self._download_errors.append(f"{identifier}: {message}")
        self.status_label.setText(
            f"{len(self._download_errors)} failure(s) while importing. Continuing…"
        )
        self.status_message.emit("Remote Import", f"Failed to import {identifier}: {message}")  # type: ignore[attr-defined]
    
    def _on_download_finished(self, ingested: list[Any]) -> None:
        """Handle download completion and emit imported spectra."""
        # Flatten list of spectra (some items may be lists themselves)
        all_spectra: list[Spectrum] = []
        for item in ingested:
            if isinstance(item, list):
                all_spectra.extend(item)
            else:
                all_spectra.append(item)
        
        # Update UI
        if self._download_errors:
            failures = len(self._download_errors)
            self.status_label.setText(
                f"Imported {len(all_spectra)} dataset(s) with {failures} failure(s)"
            )
        else:
            self.status_label.setText(f"Imported {len(all_spectra)} dataset(s)")
        
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.import_button.setEnabled(True)
        
        # Emit signal for main window to handle
        if all_spectra:
            self.spectra_imported.emit(all_spectra)  # type: ignore[attr-defined]
    
    def _on_download_error(self, message: str) -> None:
        """Handle catastrophic download failure."""
        self.status_label.setText(f"Download failed: {message}")
        self.import_button.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def _on_download_cancelled(self) -> None:
        """Handle download cancellation."""
        self.status_label.setText("Download cancelled")
        self.import_button.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def _on_load_solar_system_samples(self) -> None:
        """Import all bundled solar system CSV samples."""
        try:
            samples_root = Path(__file__).resolve().parents[2] / "samples" / "solar_system"
        except Exception:
            samples_root = Path.cwd() / "samples" / "solar_system"
        
        if not samples_root.exists():
            self.status_label.setText("No local Solar System samples found")
            return
        
        # Find CSV files
        csv_paths = sorted(samples_root.glob("**/*.csv"))
        if not csv_paths:
            self.status_label.setText("No CSV files found in samples/solar_system")
            return
        
        # Filter duplicates
        original_count = len(csv_paths)
        csv_paths = [
            p for p in csv_paths
            if not (p.name.endswith("_infrared.csv") or p.name.endswith("_uvvis.csv"))
        ]
        skipped = original_count - len(csv_paths)
        
        # Ingest files
        imported_spectra: list[Spectrum] = []
        errors: list[str] = []
        
        if skipped:
            self.status_label.setText(
                f"Importing {len(csv_paths)} local sample(s)… (skipped {skipped} duplicate(s))"
            )
        else:
            self.status_label.setText(f"Importing {len(csv_paths)} local sample(s)…")
        
        for path in csv_paths:
            try:
                result = self.ingest_service.ingest(path)
                if isinstance(result, list):
                    imported_spectra.extend(result)
                else:
                    imported_spectra.append(result)
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
                continue
        
        # Report results
        if errors:
            self.status_label.setText(
                f"Imported {len(imported_spectra)} sample(s) with {len(errors)} error(s)."
            )
        else:
            self.status_label.setText(f"Imported {len(imported_spectra)} local sample(s).")
        
        # Emit signal
        if imported_spectra:
            self.spectra_imported.emit(imported_spectra)  # type: ignore[attr-defined]
    
    @staticmethod
    def _format_bytes(value: int) -> str:
        """Format byte count as human-readable string."""
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(max(value, 0))
        unit = 0
        while size >= 1024 and unit < len(units) - 1:
            size /= 1024.0
            unit += 1
        if unit == 0:
            return f"{int(size)} {units[unit]}"
        return f"{size:.1f} {units[unit]}"

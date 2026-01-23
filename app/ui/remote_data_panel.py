"""Remote data search and download panel for the Spectra main window.

This panel provides:
- Provider selection (MAST, ExoSystems, etc.)
- Search UI with non-blocking subprocess-based MAST queries
- Download & import with progress tracking
- Quick-load for bundled solar system samples
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import numpy as np
from typing import Any, List

from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()

from app.services import RemoteDataService, DataIngestService, Spectrum, RemoteRecord
from app.workers.remote import DownloadWorker


Signal = getattr(QtCore, "Signal", None)
if Signal is None:  # pragma: no cover
    Signal = getattr(QtCore, "pyqtSignal")


class RemoteDataPanel(QtWidgets.QWidget):
    """Standalone panel for remote data search and import.
    
    Uses QProcess for MAST searches to guarantee the UI never freezes.
    
    Signals
    -------
    spectra_imported : Signal(list)
        Emitted when spectra are successfully imported with list of Spectrum objects.
    status_message : Signal(str)
        Emitted when status text should be logged (channel, message).
    """
    
    spectra_imported = Signal(list)  # type: ignore[misc]
    status_message = Signal(str, str)  # type: ignore[misc]  # (channel, message)
    download_started = Signal(int)  # type: ignore[misc]
    download_progress = Signal(str, int, int)  # type: ignore[misc]
    download_finished = Signal()  # type: ignore[misc]
    
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
        self._search_process: QtCore.QProcess | None = None
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
        
        # Results table - 6 columns of useful metadata
        self.results_table = QtWidgets.QTableWidget(0, 6)
        self.results_table.setHorizontalHeaderLabels([
            "ID",
            "Title",
            "Target",
            "Telescope",
            "Instrument",
            "Product",
        ])
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
        """Initiate search using subprocess (never freezes UI)."""
        # Handle cancel if search is in progress
        if self._search_process is not None:
            self._search_process.kill()
            self._search_process = None
            self.status_label.setText("Search cancelled")
            self.search_button.setText("Search")
            return
        
        query_text = self.search_edit.text().strip()
        if not query_text:
            self.status_label.setText("Enter a search term")
            return
        
        # Reset UI
        self._records = []
        self.results_table.setRowCount(0)
        self.import_button.setEnabled(False)
        self.status_label.setText(f"Searching MAST for '{query_text}'…")
        self.search_button.setText("Cancel")
        
        # Find Python executable and search script
        python_exe = sys.executable
        script_path = Path(__file__).parent.parent / "workers" / "search_subprocess.py"
        
        # Start subprocess
        self._search_process = QtCore.QProcess(self)
        self._search_process.finished.connect(self._on_search_process_finished)
        self._search_process.setProgram(python_exe)
        self._search_process.setArguments([str(script_path), query_text])
        self._search_process.start()
    
    def _on_search_process_finished(self, exit_code: int, exit_status: int) -> None:
        """Handle search subprocess completion."""
        process = self._search_process
        self._search_process = None
        self.search_button.setText("Search")
        
        if process is None:
            return
        
        # Read output
        try:
            output = bytes(process.readAllStandardOutput()).decode('utf-8', errors='replace')
            results = json.loads(output) if output.strip() else []
        except Exception as e:
            self.status_label.setText(f"Search failed: {e}")
            return
        
        # Check for error
        if results and isinstance(results, list) and len(results) == 1 and 'error' in results[0]:
            self.status_label.setText(f"Search error: {results[0]['error']}")
            return
        
        # Populate table
        self._populate_results(results)
        self.status_label.setText(f"Found {len(results)} result(s)")
    
    def _populate_results(self, results: list[dict]) -> None:
        """Populate the results table from search results."""
        self.results_table.setUpdatesEnabled(False)
        try:
            for r in results:
                # Create a RemoteRecord-like object
                record = RemoteRecord(
                    provider=RemoteDataService.PROVIDER_MAST,
                    identifier=r.get('identifier', ''),
                    title=r.get('title', ''),
                    download_url=r.get('download_url', ''),
                    metadata={
                        'target_name': r.get('target', ''),
                        'obs_collection': r.get('telescope', ''),
                        'instrument_name': r.get('instrument', ''),
                    },
                    units=None,
                )
                self._records.append(record)
                
                row = self.results_table.rowCount()
                self.results_table.insertRow(row)
                
                # ID
                item = QtWidgets.QTableWidgetItem(r.get('identifier', ''))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.results_table.setItem(row, 0, item)
                
                # Title  
                item = QtWidgets.QTableWidgetItem(r.get('title', ''))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.results_table.setItem(row, 1, item)
                
                # Target
                item = QtWidgets.QTableWidgetItem(r.get('target', ''))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.results_table.setItem(row, 2, item)
                
                # Telescope
                item = QtWidgets.QTableWidgetItem(r.get('telescope', ''))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.results_table.setItem(row, 3, item)
                
                # Instrument
                item = QtWidgets.QTableWidgetItem(r.get('instrument', ''))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.results_table.setItem(row, 4, item)
                
                # Product type
                item = QtWidgets.QTableWidgetItem('spectrum')
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.results_table.setItem(row, 5, item)
        finally:
            self.results_table.setUpdatesEnabled(True)
    
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
        # Bubble up for main window status bar integration
        self.download_started.emit(int(total))  # type: ignore[attr-defined]
    
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
        self.download_progress.emit(str(label), int(received), int(total))  # type: ignore[attr-defined]
    
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
        self.download_finished.emit()  # type: ignore[attr-defined]
        
        # Emit signal for main window to handle
        if all_spectra:
            self.spectra_imported.emit(all_spectra)  # type: ignore[attr-defined]
    
    def _on_download_error(self, message: str) -> None:
        """Handle catastrophic download failure."""
        self.status_label.setText(f"Download failed: {message}")
        self.import_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.download_finished.emit()  # type: ignore[attr-defined]
    
    def _on_download_cancelled(self) -> None:
        """Handle download cancellation."""
        self.status_label.setText("Download cancelled")
        self.import_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.download_finished.emit()  # type: ignore[attr-defined]
    
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

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
        self._current_page = 1
        self._total_pages = 0
        self._total_results = 0
        self._last_query = ""
        self._last_filters = {}  # Store filter state

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

        # Filter controls (MAST only)
        filter_group = QtWidgets.QGroupBox("Filters (optional)")
        filter_layout = QtWidgets.QHBoxLayout(filter_group)

        # Wavelength range filters
        filter_layout.addWidget(QtWidgets.QLabel("Wavelength:"))
        self.wavelength_min_edit = QtWidgets.QLineEdit()
        self.wavelength_min_edit.setPlaceholderText("Min (nm)")
        self.wavelength_min_edit.setMaximumWidth(80)
        self.wavelength_min_edit.setToolTip("Minimum wavelength in nanometers (e.g., 115 for UV)")
        filter_layout.addWidget(self.wavelength_min_edit)

        filter_layout.addWidget(QtWidgets.QLabel("–"))

        self.wavelength_max_edit = QtWidgets.QLineEdit()
        self.wavelength_max_edit.setPlaceholderText("Max (nm)")
        self.wavelength_max_edit.setMaximumWidth(80)
        self.wavelength_max_edit.setToolTip("Maximum wavelength in nanometers (e.g., 5000 for mid-IR)")
        filter_layout.addWidget(self.wavelength_max_edit)

        # Instrument filter
        filter_layout.addWidget(QtWidgets.QLabel("Instrument:"))
        self.instrument_combo = QtWidgets.QComboBox()
        self.instrument_combo.addItem("All", None)
        self.instrument_combo.addItem("HST/COS", "COS")
        self.instrument_combo.addItem("HST/STIS", "STIS")
        self.instrument_combo.addItem("HST/FOS", "FOS")
        self.instrument_combo.addItem("IUE", "IUE")
        self.instrument_combo.addItem("FUSE", "FUSE")
        self.instrument_combo.addItem("JWST/NIRSpec", "NIRSPEC")
        self.instrument_combo.addItem("JWST/MIRI", "MIRI")
        self.instrument_combo.addItem("JWST/NIRISS", "NIRISS")
        self.instrument_combo.addItem("JWST/NIRCam", "NIRCAM")
        self.instrument_combo.addItem("Spitzer/IRS", "IRS")
        self.instrument_combo.setMinimumWidth(150)
        filter_layout.addWidget(self.instrument_combo)

        filter_layout.addStretch()

        # Clear filters button
        self.clear_filters_button = QtWidgets.QPushButton("Clear Filters")
        self.clear_filters_button.clicked.connect(self._on_clear_filters)
        filter_layout.addWidget(self.clear_filters_button)

        self.filter_group = filter_group
        layout.addWidget(filter_group)

        # Results table - 7 columns of useful metadata
        self.results_table = QtWidgets.QTableWidget(0, 7)
        self.results_table.setHorizontalHeaderLabels([
            "ID",
            "Title",
            "Target",
            "Wavelength Range",
            "Telescope",
            "Instrument",
            "Product",
        ])
        self.results_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.results_table.setSortingEnabled(True)  # Enable column sorting

        # Configure column widths and resizing
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)  # Target
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)  # Wavelength Range
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)  # Telescope
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)  # Instrument
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)  # Product

        # Enable user column resizing by dragging
        header.setSectionsMovable(False)
        header.setStretchLastSection(False)

        # Word wrap and text eliding
        self.results_table.setWordWrap(False)
        self.results_table.setTextElideMode(QtCore.Qt.TextElideMode.ElideMiddle)

        self.results_table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.results_table, 1)

        # Pagination controls
        pagination_layout = QtWidgets.QHBoxLayout()
        self.prev_button = QtWidgets.QPushButton("← Previous")
        self.prev_button.setEnabled(False)
        self.prev_button.clicked.connect(self._on_prev_page)
        pagination_layout.addWidget(self.prev_button)

        self.page_label = QtWidgets.QLabel("Page 1 of 1")
        self.page_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        pagination_layout.addWidget(self.page_label, 1)

        self.next_button = QtWidgets.QPushButton("Next →")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self._on_next_page)
        pagination_layout.addWidget(self.next_button)

        layout.addLayout(pagination_layout)

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
        """Update placeholder text and filter visibility based on selected provider."""
        provider = self.provider_combo.currentText()

        # Show filters only for MAST
        is_mast = provider == RemoteDataService.PROVIDER_MAST
        self.filter_group.setVisible(is_mast)

        if provider == RemoteDataService.PROVIDER_MAST:
            self.search_edit.setPlaceholderText("MAST target name (e.g. NGC 7023, SN 1987A)…")
        elif provider == RemoteDataService.PROVIDER_EXOMAST:
            self.search_edit.setPlaceholderText("Exoplanet name (e.g. WASP-39 b, HAT-P-11 b)…")
        elif provider == RemoteDataService.PROVIDER_EXOPLANET_ARCHIVE:
            self.search_edit.setPlaceholderText("Exoplanet or host star name (e.g. WASP-39 b, HD 189733 b)…")
        elif provider == RemoteDataService.PROVIDER_EXOSYSTEMS:
            self.search_edit.setPlaceholderText("Planet, star, or solar system target (e.g. HD 189733 b, Jupiter)…")
        else:
            self.search_edit.setPlaceholderText("Target name or keyword…")

    def _on_clear_filters(self) -> None:
        """Clear all filter inputs."""
        self.wavelength_min_edit.clear()
        self.wavelength_max_edit.clear()
        self.instrument_combo.setCurrentIndex(0)
    
    def _on_search(self) -> None:
        """Initiate search - uses subprocess for MAST, direct call for other providers."""
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

        provider = self.provider_combo.currentText()

        # Reset UI for new search
        self._records = []
        self.results_table.setRowCount(0)
        self.import_button.setEnabled(False)
        self._current_page = 1
        self._last_query = query_text

        # Route to appropriate search method based on provider
        if provider == RemoteDataService.PROVIDER_MAST:
            self._search_mast_subprocess(query_text)
        elif provider == RemoteDataService.PROVIDER_EXOMAST:
            self._search_exomast_direct(query_text)
        elif provider == RemoteDataService.PROVIDER_EXOPLANET_ARCHIVE:
            self._search_exoplanet_archive_direct(query_text)
        else:
            self.status_label.setText(f"Provider '{provider}' not yet supported")

    def _search_mast_subprocess(self, query_text: str) -> None:
        """Search MAST using subprocess (non-blocking)."""
        # Build filter dict
        filters = self._get_current_filters()
        self._last_filters = filters

        filter_desc = self._format_filter_description(filters)
        status_text = f"Searching MAST for '{query_text}'{filter_desc}…"
        self.status_label.setText(status_text)
        self.search_button.setText("Cancel")

        # Find Python executable and search script
        python_exe = sys.executable
        script_path = Path(__file__).parent.parent / "workers" / "search_subprocess.py"

        # Start subprocess with page number and filters
        self._search_process = QtCore.QProcess(self)
        self._search_process.finished.connect(self._on_search_process_finished)
        self._search_process.setProgram(python_exe)

        args = [str(script_path), query_text, str(self._current_page)]
        if filters:
            args.append(json.dumps(filters))

        self._search_process.setArguments(args)
        self._search_process.start()

    def _search_exoplanet_archive_direct(self, query_text: str) -> None:
        """Search NASA Exoplanet Archive directly (synchronous but fast)."""
        self.status_label.setText(f"Searching NASA Exoplanet Archive for '{query_text}'…")
        self.search_button.setText("Searching...")
        self.search_button.setEnabled(False)

        try:
            # Direct service call (exoplanet archive is fast, no subprocess needed)
            query = {"text": query_text}
            results = self.remote_service.search(
                RemoteDataService.PROVIDER_EXOPLANET_ARCHIVE,
                query
            )

            # Convert RemoteRecord to dict format for populate_results
            result_dicts = []
            for record in results:
                result_dicts.append({
                    'identifier': record.identifier,
                    'title': record.title,
                    'download_url': record.download_url,
                    'target': record.metadata.get('planet_name', query_text),
                    'telescope': 'NASA Exoplanet Archive',
                    'instrument': record.metadata.get('spectrum_type', 'transmission'),
                    'wavelength_range': f"{record.metadata.get('wav_units', 'um')} spectra",
                })

            self._populate_results(result_dicts)
            self.status_label.setText(f"Found {len(results)} spectrum/spectra")

        except Exception as e:
            self.status_label.setText(f"Search error: {e}")

        finally:
            self.search_button.setText("Search")
            self.search_button.setEnabled(True)

    def _search_exomast_direct(self, query_text: str) -> None:
        """Search Exo.MAST directly (synchronous, fast, curated spectra)."""
        self.status_label.setText(f"Searching Exo.MAST for '{query_text}'…")
        self.search_button.setText("Searching...")
        self.search_button.setEnabled(False)

        try:
            # Direct service call (Exo.MAST is fast, no subprocess needed)
            query = {"text": query_text}
            results = self.remote_service.search(
                RemoteDataService.PROVIDER_EXOMAST,
                query
            )

            # Convert RemoteRecord to dict format for populate_results
            result_dicts = []
            for record in results:
                result_dicts.append({
                    'identifier': record.identifier,
                    'title': record.title,
                    'download_url': record.download_url,
                    'target': record.metadata.get('target', query_text),
                    'telescope': 'Exo.MAST',
                    'instrument': record.metadata.get('reference', 'Publication'),
                    'wavelength_range': f"{record.metadata.get('spectrum_type', 'spectrum')}",
                })

            self._populate_results(result_dicts)
            self.status_label.setText(f"Found {len(results)} spectrum/spectra")

        except Exception as e:
            self.status_label.setText(f"Search error: {e}")

        finally:
            self.search_button.setText("Search")
            self.search_button.setEnabled(True)

    def _get_current_filters(self) -> dict:
        """Get current filter values as a dict."""
        filters = {}

        # Wavelength filters
        wl_min_text = self.wavelength_min_edit.text().strip()
        wl_max_text = self.wavelength_max_edit.text().strip()

        if wl_min_text:
            try:
                filters['wavelength_min'] = float(wl_min_text)
            except ValueError:
                pass

        if wl_max_text:
            try:
                filters['wavelength_max'] = float(wl_max_text)
            except ValueError:
                pass

        # Instrument filter
        inst_data = self.instrument_combo.currentData()
        if inst_data:
            filters['instruments'] = [inst_data]

        return filters

    def _format_filter_description(self, filters: dict) -> str:
        """Format filter dict into human-readable description."""
        if not filters:
            return ""

        parts = []
        if 'wavelength_min' in filters or 'wavelength_max' in filters:
            wl_min = filters.get('wavelength_min', '?')
            wl_max = filters.get('wavelength_max', '?')
            parts.append(f"{wl_min}–{wl_max} nm")

        if 'instruments' in filters and filters['instruments']:
            parts.append(f"{filters['instruments'][0]}")

        return f" ({', '.join(parts)})" if parts else ""
    
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
            data = json.loads(output) if output.strip() else {'results': [], 'total': 0, 'page': 1, 'total_pages': 0}
        except Exception as e:
            self.status_label.setText(f"Search failed: {e}")
            return

        # Handle old format (list) for backwards compatibility
        if isinstance(data, list):
            data = {'results': data, 'total': len(data), 'page': 1, 'total_pages': 1}

        results = data.get('results', [])

        # Check for error
        if results and isinstance(results, list) and len(results) == 1 and 'error' in results[0]:
            self.status_label.setText(f"Search error: {results[0]['error']}")
            return

        # Update pagination info
        self._total_results = data.get('total', len(results))
        self._total_pages = data.get('total_pages', 1)
        self._current_page = data.get('page', 1)

        # Populate table
        self._populate_results(results)

        # Update pagination UI
        self._update_pagination_ui()

        # Update status
        if self._total_results > len(results):
            self.status_label.setText(
                f"Showing {len(results)} of {self._total_results} result(s) "
                f"(Page {self._current_page} of {self._total_pages})"
            )
        else:
            self.status_label.setText(f"Found {self._total_results} result(s)")
    
    def _populate_results(self, results: list[dict]) -> None:
        """Populate the results table from search results."""
        self.results_table.setUpdatesEnabled(False)
        try:
            # Clear existing results first (important for pagination)
            self._records = []
            self.results_table.setRowCount(0)

            # Get current provider to set correctly on RemoteRecords
            current_provider = self.provider_combo.currentText()

            for r in results:
                # Create a RemoteRecord-like object
                record = RemoteRecord(
                    provider=current_provider,  # Use actual provider, not hardcoded MAST
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

                # Wavelength Range
                wavelength_range = r.get('wavelength_range', '')
                item = QtWidgets.QTableWidgetItem(wavelength_range)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.results_table.setItem(row, 3, item)

                # Telescope
                item = QtWidgets.QTableWidgetItem(r.get('telescope', ''))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.results_table.setItem(row, 4, item)

                # Instrument
                item = QtWidgets.QTableWidgetItem(r.get('instrument', ''))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.results_table.setItem(row, 5, item)

                # Product type
                item = QtWidgets.QTableWidgetItem('spectrum')
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.results_table.setItem(row, 6, item)
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

    def _update_pagination_ui(self) -> None:
        """Update pagination button states and label."""
        self.prev_button.setEnabled(self._current_page > 1)
        self.next_button.setEnabled(self._current_page < self._total_pages)

        if self._total_pages > 0:
            self.page_label.setText(f"Page {self._current_page} of {self._total_pages} ({self._total_results} total)")
        else:
            self.page_label.setText("No results")

    def _on_prev_page(self) -> None:
        """Go to previous page of results."""
        if self._current_page > 1:
            self._current_page -= 1
            self._load_page()

    def _on_next_page(self) -> None:
        """Go to next page of results."""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._load_page()

    def _load_page(self) -> None:
        """Load the current page of results using the last query and filters."""
        if not self._last_query:
            return

        # Reset UI
        self._records = []
        self.results_table.setRowCount(0)
        self.import_button.setEnabled(False)
        self.status_label.setText(f"Loading page {self._current_page}…")

        # Find Python executable and search script
        python_exe = sys.executable
        script_path = Path(__file__).parent.parent / "workers" / "search_subprocess.py"

        # Start subprocess with current page and last filters
        self._search_process = QtCore.QProcess(self)
        self._search_process.finished.connect(self._on_search_process_finished)
        self._search_process.setProgram(python_exe)

        args = [str(script_path), self._last_query, str(self._current_page)]
        if self._last_filters:
            args.append(json.dumps(self._last_filters))

        self._search_process.setArguments(args)
        self._search_process.start()

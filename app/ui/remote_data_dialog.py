"""Remote data discovery dialog."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, List
from urllib.parse import quote

from app.qt_compat import get_qt
from app.services import DataIngestService, RemoteDataService, RemoteRecord

QtCore, QtGui, QtWidgets, _ = get_qt()

if hasattr(QtCore, "Signal"):
    Signal = QtCore.Signal  # type: ignore[attr-defined]
elif hasattr(QtCore, "pyqtSignal"):  # pragma: no cover - PyQt fallback for developers
    Signal = QtCore.pyqtSignal  # type: ignore[attr-defined]
else:  # pragma: no cover - fail fast with a clearer error
    raise ImportError("Qt binding does not expose Signal/pyqtSignal")


class _SearchWorker(QtCore.QObject):
    """Background worker that queries a remote catalogue."""

    finished = Signal()
    results_ready = Signal(list)
    error = Signal(str)

    def __init__(
        self,
        remote_service: RemoteDataService,
        provider: str,
        query: dict[str, str],
        *,
        include_imaging: bool,
    ) -> None:
        super().__init__()
        self._remote_service = remote_service
        self._provider = provider
        self._query = query
        self._include_imaging = include_imaging

    @QtCore.Slot()
    def run(self) -> None:
        try:
            results = self._remote_service.search(
                self._provider,
                dict(self._query),
                include_imaging=self._include_imaging,
            )
        except Exception as exc:  # pragma: no cover - surfaced via error signal
            self.error.emit(str(exc))
        else:
            self.results_ready.emit(results)
        finally:
            self.finished.emit()


class _DownloadWorker(QtCore.QObject):
    """Background worker that downloads and ingests remote catalogue entries."""

    finished = Signal()
    completed = Signal(list)
    warning = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        remote_service: RemoteDataService,
        ingest_service: DataIngestService,
        records: list[RemoteRecord],
    ) -> None:
        super().__init__()
        self._remote_service = remote_service
        self._ingest_service = ingest_service
        self._records = list(records)

    @QtCore.Slot()
    def run(self) -> None:
        spectra: list[object] = []
        try:
            for record in self._records:
                try:
                    download = self._remote_service.download(record)
                    ingested = self._ingest_service.ingest(
                        Path(download.cache_entry["stored_path"])
                    )
                except Exception as exc:  # pragma: no cover - surfaced via warning
                    self.warning.emit(f"{record.identifier}: {exc}")
                    continue
                if isinstance(ingested, list):
                    spectra.extend(ingested)
                else:
                    spectra.append(ingested)
        except Exception as exc:  # pragma: no cover - surfaced via error signal
            self.error.emit(str(exc))
        else:
            self.completed.emit(spectra)
        finally:
            self.finished.emit()


class RemoteDataDialog(QtWidgets.QDialog):
    """Interactive browser for remote catalogue search and download."""

    search_started = Signal(str)
    search_completed = Signal(list)
    search_failed = Signal(str)
    download_started = Signal(int)
    download_completed = Signal(list)
    download_failed = Signal(str)

    _RESULT_HEADERS: tuple[str, ...] = (
        "ID",
        "Title",
        "Target",
        "Mission",
        "Instrument",
        "Product",
        "Download",
        "Preview / Citation",
    )

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
        self._ingested: List[object] = []
        self._provider_hints: dict[str, str] = {}
        self._provider_placeholders: dict[str, str] = {}
        self._provider_examples: dict[str, list[tuple[str, str]]] = {}
        self._dependency_hint: str = ""
        self._search_thread: QtCore.QThread | None = None
        self._download_thread: QtCore.QThread | None = None
        self._search_worker: _SearchWorker | None = None
        self._download_worker: _DownloadWorker | None = None
        self._search_in_progress = False
        self._download_in_progress = False
        self._download_warnings: list[str] = []
        self._busy: bool = False

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

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self)
        layout.addWidget(splitter, 1)

        self.results = QtWidgets.QTableWidget(self)
        self.results.setColumnCount(len(self._RESULT_HEADERS))
        self.results.setHorizontalHeaderLabels(list(self._RESULT_HEADERS))
        self.results.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.results.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        header = self.results.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        for column in (0, 6, 7):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.results.verticalHeader().setVisible(False)
        self.results.setAlternatingRowColors(True)
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
        progress_container.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(progress_container)

        self.progress_indicator = QtWidgets.QProgressBar(self)
        self.progress_indicator.setRange(0, 1)
        self.progress_indicator.setTextVisible(False)
        self.progress_indicator.setFixedWidth(140)
        self.progress_indicator.setVisible(False)
        progress_container.addWidget(self.progress_indicator)

        self.status_label = QtWidgets.QLabel(self)
        self.status_label.setObjectName("remote-status")
        self.status_label.setWordWrap(True)
        progress_container.addWidget(self.status_label, 1)

        self._refresh_provider_state()
        self._update_enabled_state()
        self._set_busy(False)

    # ------------------------------------------------------------------
    def _on_search(self) -> None:
        provider = self.provider_combo.currentText()
        query = self._build_provider_query(provider, self.search_edit.text())
        if not query:
            QtWidgets.QMessageBox.information(
                self,
                "Enter search criteria",
                "Provide provider-specific search text before querying the remote catalogue.",
            )
            return

        include_imaging = bool(
            self.include_imaging_checkbox.isVisible()
            and self.include_imaging_checkbox.isEnabled()
            and self.include_imaging_checkbox.isChecked()
        )

        self._records = []
        self.results.setRowCount(0)
        self.preview.clear()
        self._update_download_button_state()

        self._search_in_progress = True
        self._update_enabled_state()
        self._set_busy(True)
        self.status_label.setText(f"Searching {provider}…")
        self.search_started.emit(provider)

        worker = _SearchWorker(
            self.remote_service,
            provider,
            query,
            include_imaging=include_imaging,
        )
        worker.results_ready.connect(self._handle_search_results)
        worker.error.connect(self._handle_search_error)
        worker.finished.connect(self._search_finished)
        self._start_search_worker(worker)

    def _on_provider_changed(self, index: int | None = None) -> None:
        # Accept the index argument emitted by Qt while keeping the logic driven
        # by the current provider string so external callers can trigger the
        # refresh without supplying an index explicitly.
        if index is not None:
            # Qt passes the numeric index; the logic below derives values from
            # the provider string so the argument is intentionally ignored.
            pass
        provider = self.provider_combo.currentText()
        is_mast = provider == RemoteDataService.PROVIDER_MAST
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
        if provider == RemoteDataService.PROVIDER_MAST:
            return {"target_name": stripped} if stripped else {}
        if provider == RemoteDataService.PROVIDER_NIST:
            return self._build_nist_query(stripped)
        if provider == RemoteDataService.PROVIDER_SOLAR_SYSTEM:
            if stripped:
                return {"text": stripped}
            return {"text": "", "include_all": "true"}
        return {"text": stripped} if stripped else {}

    def _build_nist_query(self, stripped: str) -> dict[str, str]:
        if not stripped:
            return {}

        element: str | None = None
        ion_stage: str | None = None
        keywords: list[str] = []

        def assign_keyword(value: str) -> None:
            normalized = value.strip()
            if normalized:
                keywords.append(normalized)

        parts = [part.strip() for part in re.split(r"[;,\n]+", stripped) if part.strip()]
        element_prefix = re.compile(
            r"^(?P<element>[A-Za-z]{1,2}(?:\s*(?:[IVXLCDM]+|\d+\+?))?)(?P<rest>.*)$",
            re.IGNORECASE,
        )
        element_only = re.compile(
            r"^[A-Za-z]{1,2}(?:\s*(?:[IVXLCDM]+|\d+\+?))?$",
            re.IGNORECASE,
        )

        for part in parts:
            key_match = re.split(r"[:=]", part, maxsplit=1)
            if len(key_match) == 2 and key_match[0].strip():
                key = key_match[0].strip().lower()
                value = key_match[1].strip()
                if not value:
                    continue
                if key in {"element", "species"}:
                    element = value
                    continue
                if key in {"ion", "ion_stage"}:
                    ion_stage = value
                    continue
                if key in {"keyword", "keywords"}:
                    assign_keyword(value)
                    continue
            if element is None:
                prefix_match = element_prefix.match(part)
                if prefix_match:
                    candidate = prefix_match.group("element").strip()
                    rest = prefix_match.group("rest").strip()
                    if candidate and element_only.match(candidate):
                        element = candidate
                        if rest:
                            assign_keyword(rest)
                        continue
            assign_keyword(part)

        query: dict[str, str] = {}
        if element:
            query["element"] = element
        if ion_stage:
            query["ion_stage"] = ion_stage
        if keywords:
            query["text"] = " ".join(keywords)
        elif element:
            query["text"] = element
        else:
            query["text"] = stripped
        return query

    def _on_example_selected(self, index: int) -> None:
        if index <= 0:
            return
        query_text = self.example_combo.itemData(index)
        if isinstance(query_text, str):
            self.search_edit.setText(query_text)
            self._on_search()

    def _on_selection_changed(self) -> None:
        self._update_preview()
        self._update_download_button_state()

    def _update_preview(self) -> None:
        indexes = self.results.selectionModel().selectedRows()
        if not indexes:
            self.preview.clear()
            return
        record = self._records[indexes[0].row()]
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
        citations = self._formatted_citations(record.metadata)
        if citations:
            narrative_lines.append("Citations:")
            for citation in citations:
                narrative_lines.append(f"  - {citation}")
        if narrative_lines:
            narrative_lines.append("")
        narrative_lines.append(json.dumps(metadata, indent=2, ensure_ascii=False))
        self.preview.setPlainText("\n".join(narrative_lines))

    def _populate_results_table(self, records: Sequence[RemoteRecord]) -> None:
        self._clear_result_widgets()
        self.results.setColumnCount(len(self._RESULT_HEADERS))
        self.results.setHorizontalHeaderLabels(list(self._RESULT_HEADERS))
        self.results.setRowCount(len(records))
        for row, record in enumerate(records):
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

    def _formatted_citations(self, metadata: Mapping[str, Any] | Any) -> list[str]:
        formatted: list[str] = []
        for entry in self._citation_entries(metadata):
            text = self._format_citation_entry(entry)
            if text:
                formatted.append(text)
        return formatted

    def _citation_entries(self, metadata: Mapping[str, Any] | Any) -> list[Mapping[str, Any]]:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        entries: list[Mapping[str, Any]] = []
        raw = mapping.get("citations")
        if isinstance(raw, Sequence):
            for item in raw:
                if isinstance(item, Mapping):
                    entries.append(item)
                elif isinstance(item, str) and item.strip():
                    entries.append({"title": item.strip()})
        single = mapping.get("citation")
        if isinstance(single, str) and single.strip():
            entries.append({"title": single.strip()})
        return entries

    def _format_citation_entry(self, entry: Mapping[str, Any]) -> str:
        title = str(entry.get("title") or entry.get("label") or "").strip()
        doi = str(entry.get("doi") or "").strip()
        url = str(entry.get("url") or entry.get("link") or "").strip()
        notes = str(entry.get("notes") or "").strip()

        parts: list[str] = []
        if title:
            parts.append(title)

        detail_parts: list[str] = []
        if doi:
            detail_parts.append(f"DOI {doi}")
        if url:
            detail_parts.append(url)
        if detail_parts:
            parts.append(", ".join(detail_parts))

        if notes:
            parts.append(notes)

        return " — ".join(parts) if parts else ""

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

    def _on_queue_downloads(self) -> None:
        if self._busy:
            return
        selected = self.results.selectionModel().selectedRows()
        if not selected:
            self.status_label.setText("Select at least one record to import.")
            return

        records = [self._records[index.row()] for index in selected]

        self._download_in_progress = True
        self._download_warnings = []
        self._update_enabled_state()
        self._set_busy(True)
        self.status_label.setText(f"Downloading {len(records)} selection(s)…")
        self.download_started.emit(len(records))

        worker = _DownloadWorker(self.remote_service, self.ingest_service, records)
        worker.completed.connect(self._handle_download_completed)
        worker.warning.connect(self._handle_download_warning)
        worker.error.connect(self._handle_download_error)
        worker.finished.connect(self._download_finished)
        self._start_download_worker(worker)

    def _refresh_provider_state(self) -> None:
        providers = list(self.remote_service.providers(include_reference=False))
        self.provider_combo.clear()
        if providers:
            self.provider_combo.addItems(providers)
            self.provider_combo.setEnabled(True)
            self.search_edit.setEnabled(True)
            self.search_button.setEnabled(True)
            placeholders: dict[str, str] = {}
            hints: dict[str, str] = {}
            examples: dict[str, list[tuple[str, str]]] = {}
            if RemoteDataService.PROVIDER_MAST in providers:
                placeholders[RemoteDataService.PROVIDER_MAST] = (
                    "JWST spectroscopic target (e.g. WASP-96 b, NIRSpec)…"
                )
                hints[RemoteDataService.PROVIDER_MAST] = (
                    "MAST requests favour calibrated spectra (IFS cubes, slits, prisms). Enable "
                    '"Include imaging" to broaden results with calibrated image products.'
                )
                examples[RemoteDataService.PROVIDER_MAST] = [
                    ("WASP-96 b – JWST/NIRSpec", "WASP-96 b"),
                    ("WASP-39 b – JWST/NIRSpec", "WASP-39 b"),
                    ("HD 189733 – JWST/NIRISS", "HD 189733"),
                ]
            if RemoteDataService.PROVIDER_SOLAR_SYSTEM in providers:
                placeholders[RemoteDataService.PROVIDER_SOLAR_SYSTEM] = (
                    "Curated solar system or stellar target (e.g. Jupiter, Vega)…"
                )
                hints[RemoteDataService.PROVIDER_SOLAR_SYSTEM] = (
                    "Solar System Archive samples are bundled manifests mapped to local spectra. Leave the field blank "
                    "to list every curated target, or search by planet/moon/star name to filter the table."
                )
                examples[RemoteDataService.PROVIDER_SOLAR_SYSTEM] = [
                    ("Mercury – MESSENGER MASCS", "Mercury"),
                    ("Jupiter – JWST ERS composite", "Jupiter"),
                    ("Vega – HST CALSPEC standard", "Vega"),
                ]
            self._provider_placeholders = placeholders
            self._provider_hints = hints
            self._provider_examples = examples
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

    # ------------------------------------------------------------------
    def _start_search_worker(self, worker: _SearchWorker) -> None:
        self._cleanup_search_thread()
        thread = QtCore.QThread(self)
        thread.setObjectName("remote-search-worker")
        self._search_thread = thread
        self._search_worker = worker
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_search_thread_finished)
        thread.start()

    def _start_download_worker(self, worker: _DownloadWorker) -> None:
        self._cleanup_download_thread()
        thread = QtCore.QThread(self)
        thread.setObjectName("remote-download-worker")
        self._download_thread = thread
        self._download_worker = worker
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_download_thread_finished)
        thread.start()

    def _handle_search_results(self, records: list[RemoteRecord]) -> None:
        self._records = list(records)
        self._populate_results_table(self._records)
        self.status_label.setText(f"{len(records)} result(s) fetched from {self.provider_combo.currentText()}.")
        if records:
            self.results.selectRow(0)
        else:
            self.preview.clear()
        self._update_download_button_state()
        self.search_completed.emit(records)

    def _handle_search_error(self, message: str) -> None:
        QtWidgets.QMessageBox.critical(self, "Search failed", message)
        self.status_label.setText(message)
        self.search_failed.emit(message)

    def _search_finished(self) -> None:
        self._search_in_progress = False
        self._update_enabled_state()
        self._set_busy(False)

    def _handle_download_completed(self, spectra: list[object]) -> None:
        self._ingested = list(spectra)
        if self._download_warnings and spectra:
            QtWidgets.QMessageBox.warning(
                self,
                "Partial download",
                "\n".join(self._download_warnings),
            )
            self._download_warnings.clear()
        if spectra:
            self.status_label.setText(f"Imported {len(spectra)} spectrum/s.")
            self.download_completed.emit(spectra)
            self.accept()
        elif self._download_warnings:
            QtWidgets.QMessageBox.warning(
                self,
                "Download failed",
                "\n".join(self._download_warnings),
            )
            self._download_warnings.clear()
        else:
            self.status_label.setText("No spectra were imported.")

    def _handle_download_warning(self, message: str) -> None:
        self._download_warnings.append(message)

    def _handle_download_error(self, message: str) -> None:
        QtWidgets.QMessageBox.critical(self, "Download failed", message)
        self.status_label.setText(message)
        self.download_failed.emit(message)

    def _download_finished(self) -> None:
        self._download_in_progress = False
        self._update_enabled_state()
        self._download_warnings.clear()
        self._set_busy(False)

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
        self._update_download_button_state()

    def accept(self) -> None:  # pragma: no cover - Qt dialog lifecycle glue
        self._cleanup_search_thread()
        self._cleanup_download_thread()
        super().accept()

    def reject(self) -> None:  # pragma: no cover - Qt dialog lifecycle glue
        self._cleanup_search_thread()
        self._cleanup_download_thread()
        super().reject()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # pragma: no cover
        self._cleanup_search_thread()
        self._cleanup_download_thread()
        super().closeEvent(event)

    def _on_search_thread_finished(self) -> None:
        self._search_thread = None
        self._search_worker = None

    def _on_download_thread_finished(self) -> None:
        self._download_thread = None
        self._download_worker = None

    def _cleanup_search_thread(self) -> None:
        if self._search_thread is not None:
            self._search_thread.quit()
            self._search_thread.wait()
            self._search_thread = None
        self._search_worker = None

    def _cleanup_download_thread(self) -> None:
        if self._download_thread is not None:
            self._download_thread.quit()
            self._download_thread.wait()
            self._download_thread = None
        self._download_worker = None

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            self.progress_indicator.setRange(0, 0)
            self.progress_indicator.setVisible(True)
        else:
            self.progress_indicator.setVisible(False)
            self.progress_indicator.setRange(0, 1)

    def _update_download_button_state(self) -> None:
        has_selection = bool(
            self.results.selectionModel()
            and self.results.selectionModel().selectedRows()
        )
        enabled = (
            has_selection
            and bool(self._records)
            and not self._search_in_progress
            and not self._download_in_progress
        )
        self.download_button.setEnabled(enabled)

    # ------------------------------------------------------------------
    def _format_target(self, record: RemoteRecord) -> str:
        metadata = record.metadata if isinstance(record.metadata, Mapping) else {}
        target = self._first_text(
            metadata,
            [
                "target_name",
                "target",
                "Target Name",
                "display_name",
                "obs_target",
                "intentTargetName",
            ],
        )
        if target:
            return target
        return record.title

    def _format_mission(self, metadata: Mapping[str, Any] | Any) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        mission = self._first_text(
            mapping,
            [
                "obs_collection",
                "mission",
                "obs_collection_name",
                "project",
                "facility_name",
                "telescope_name",
            ],
        )
        program = self._first_text(mapping, ["program", "program_name", "proposal_pi", "proposal_id"])
        if mission and program:
            return f"{mission} ({program})"
        return mission or program

    def _format_instrument(self, metadata: Mapping[str, Any] | Any) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        instrument = self._first_text(
            mapping,
            [
                "instrument_name",
                "instrument",
                "instrument_id",
                "instr_band",
                "detector",
            ],
        )
        channel = self._first_text(mapping, ["channel", "camera", "module"])
        grating = self._first_text(mapping, ["grating", "grating_config", "spectral_element"])
        filters = self._first_text(mapping, ["filters", "filter"])
        details = [part for part in (instrument, channel, grating, filters) if part]
        return " / ".join(dict.fromkeys(details)) if details else ""

    def _format_product(self, metadata: Mapping[str, Any] | Any) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        product = self._first_text(
            mapping,
            [
                "productType",
                "dataproduct_type",
                "product_type",
                "Product Type",
            ],
        )
        intent = self._first_text(mapping, ["intentType", "intent_type"])
        calibration = mapping.get("calib_level")
        calibration_text = ""
        if calibration not in (None, ""):
            calibration_text = f"Level {calibration}"
        descriptors = [part for part in (product, intent, calibration_text) if part]
        return "; ".join(dict.fromkeys(descriptors))

    def _format_exoplanet_summary(self, metadata: Mapping[str, Any] | Any) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        summary = mapping.get("exoplanet_summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
        exoplanet = mapping.get("exoplanet")
        if isinstance(exoplanet, Mapping):
            name = self._first_text(exoplanet, ["display_name", "name"])
            classification = self._first_text(exoplanet, ["classification", "type"])
            host = self._first_text(exoplanet, ["host_star", "host"])
            details = [part for part in (classification, host and f"Host: {host}") if part]
            if name or details:
                return " – ".join(filter(None, [name, ", ".join(details) if details else ""]))
        return ""

    def _extract_citation(self, metadata: Mapping[str, Any] | Any) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        citation = self._first_text(
            mapping,
            ["citation", "citation_text", "Citation", "reference", "reference_text"],
        )
        if citation:
            return citation
        doi = self._first_text(mapping, ["doi", "DOI", "citation_doi"])
        url = self._first_text(
            mapping,
            ["citation_url", "bibliographic_url", "referenceURL", "url", "link"],
        )
        if doi and url:
            return f"DOI {doi} – {url}"
        if doi:
            return f"DOI {doi}"
        if url:
            return url
        citations = mapping.get("citations")
        if isinstance(citations, Mapping):
            return self._extract_citation(citations)
        if isinstance(citations, Sequence) and not isinstance(citations, (str, bytes)):
            for entry in citations:
                if not isinstance(entry, Mapping):
                    continue
                title = self._first_text(entry, ["title", "citation", "reference"])
                entry_doi = self._first_text(entry, ["doi", "DOI"])
                pieces = [part for part in (title, entry_doi and f"DOI {entry_doi}") if part]
                if pieces:
                    return " – ".join(pieces)
        return ""

    def _set_download_widget(self, row: int, column: int, url: str) -> None:
        hyperlink = self._link_for_download(url)
        if not hyperlink:
            self.results.setCellWidget(row, column, None)
            self._set_table_text(row, column, "")
            return

        label = QtWidgets.QLabel(self.results)
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        label.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        escaped = html.escape(hyperlink)
        label.setText(f'<a href="{escaped}">Open</a>')
        tooltip = url
        if hyperlink != url:
            tooltip = f"{url}\n{hyperlink}"
        label.setToolTip(tooltip)
        self.results.setCellWidget(row, column, label)

    def _set_preview_widget(self, row: int, column: int, metadata: Mapping[str, Any] | Any) -> None:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        preview_url = self._first_text(
            mapping,
            [
                "preview_url",
                "previewURL",
                "preview_uri",
                "QuicklookURL",
                "quicklook_url",
                "productPreviewURL",
                "thumbnailURL",
                "thumbnail_uri",
                "preview_download",
            ],
        )
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

    @staticmethod
    def _link_for_download(url: str) -> str:
        if not url:
            return ""
        if url.startswith("mast:"):
            encoded = quote(url, safe=":/")
            return f"https://mast.stsci.edu/api/v0.1/Download/file?uri={encoded}"
        if url.startswith("nist-asd"):
            encoded = quote(url, safe=":/?=&,+-_.")
            return f"https://physics.nist.gov/PhysRefData/ASD/lines_form.html?uri={encoded}"
        return url

    @staticmethod
    def _first_text(metadata: Mapping[str, Any] | Any, keys: Sequence[str]) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        for key in keys:
            value = mapping.get(key)
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                for item in value:
                    if item is None:
                        continue
                    text = str(item).strip()
                    if text:
                        return text
                continue
            text = str(value).strip()
            if text:
                return text
        return ""


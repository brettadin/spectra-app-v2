"""Remote data discovery dialog."""

from __future__ import annotations

import html
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, List
from urllib.parse import quote

from app.qt_compat import get_qt
from app.services import DataIngestService, RemoteDataService, RemoteRecord

QtCore, QtGui, QtWidgets, _ = get_qt()

Signal = getattr(QtCore, "Signal", getattr(QtCore, "pyqtSignal"))
Slot = getattr(QtCore, "Slot", getattr(QtCore, "pyqtSlot"))


class _SearchWorker(QtCore.QObject):
    """Background worker that streams search results from a remote provider."""

    started = Signal()
    record_found = Signal(object)
    finished = Signal(list)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, remote_service: RemoteDataService) -> None:
        super().__init__()
        self._remote_service = remote_service
        self._cancel_requested = False

    @Slot(str, dict, bool)
    def run(self, provider: str, query: dict[str, str], include_imaging: bool) -> None:
        self.started.emit()
        collected: list[RemoteRecord] = []
        try:
            results = self._remote_service.search(
                provider,
                query,
                include_imaging=include_imaging,
            )
            for record in results:
                if self._cancel_requested:
                    self.cancelled.emit()
                    return
                collected.append(record)
                self.record_found.emit(record)
            if self._cancel_requested:
                self.cancelled.emit()
                return
        except Exception as exc:  # pragma: no cover - defensive: surfaced via signal
            self.failed.emit(str(exc))
            return
        self.finished.emit(collected)

    @Slot()
    def cancel(self) -> None:
        self._cancel_requested = True


class _DownloadWorker(QtCore.QObject):
    """Background worker that downloads and ingests selected remote records."""

    started = Signal(int)
    record_ingested = Signal(object)
    record_failed = Signal(object, str)
    finished = Signal(list)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        remote_service: RemoteDataService,
        ingest_service: DataIngestService,
    ) -> None:
        super().__init__()
        self._remote_service = remote_service
        self._ingest_service = ingest_service
        self._cancel_requested = False

    @Slot(list)
    def run(self, records: list[RemoteRecord]) -> None:
        self.started.emit(len(records))
        ingested: list[object] = []
        try:
            for record in records:
                if self._cancel_requested:
                    self.cancelled.emit()
                    return
                try:
                    download = self._remote_service.download(record)
                    ingested_item = self._ingest_service.ingest(
                        Path(download.cache_entry["stored_path"])
                    )
                except Exception as exc:  # pragma: no cover - defensive: surfaced via signal
                    self.record_failed.emit(record, str(exc))
                    continue
                if isinstance(ingested_item, list):
                    ingested.extend(ingested_item)
                else:
                    ingested.append(ingested_item)
                self.record_ingested.emit(record)
            if self._cancel_requested:
                self.cancelled.emit()
                return
        except Exception as exc:  # pragma: no cover - defensive: surfaced via signal
            self.failed.emit(str(exc))
            return
        self.finished.emit(ingested)

    @Slot()
    def cancel(self) -> None:
        self._cancel_requested = True


class RemoteDataDialog(QtWidgets.QDialog):
    """Interactive browser for remote catalogue search and download."""

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
        self._search_worker: _SearchWorker | None = None
        self._download_thread: QtCore.QThread | None = None
        self._download_worker: _DownloadWorker | None = None
        self._busy = False
        self._download_total = 0
        self._download_completed = 0
        self._download_errors: list[str] = []
        self._control_enabled_state: dict[QtWidgets.QWidget, bool] = {}

        self._search_worker_factory = lambda: _SearchWorker(self.remote_service)
        self._download_worker_factory = lambda: _DownloadWorker(
            self.remote_service, self.ingest_service
        )

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
        self._cancel_search_worker()
        self._records = []
        self._reset_results_table()
        self.preview.clear()
        message = f"Searching {provider}…"
        self._set_busy(True, message=message)

        worker = self._search_worker_factory()
        thread = QtCore.QThread(self)
        self._search_worker = worker
        self._search_thread = thread
        worker.moveToThread(thread)
        thread.started.connect(
            lambda provider=provider, query=query, include_imaging=include_imaging: worker.run(
                provider, query, include_imaging
            )
        )
        worker.started.connect(lambda: self._set_busy(True, message=message))
        worker.record_found.connect(self._handle_search_record)
        worker.finished.connect(self._handle_search_finished)
        worker.failed.connect(self._handle_search_failed)
        worker.cancelled.connect(self._handle_search_cancelled)
        self._connect_worker_cleanup(worker, thread)
        thread.start()

    def _handle_search_record(self, record: RemoteRecord) -> None:
        self._records.append(record)
        row = len(self._records) - 1
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

        if row == 0:
            self.results.selectRow(0)
        status = f"{len(self._records)} result(s) received from {self.provider_combo.currentText()}…"
        self.status_label.setText(status)

    def _handle_search_finished(self, records: list[RemoteRecord]) -> None:
        self._set_busy(False)
        provider = self.provider_combo.currentText()
        total = len(records)
        if not total:
            self.status_label.setText(f"No results found for {provider}.")
            self.preview.clear()
            return
        summary = self._format_status_summary(records)
        status = f"{total} result(s) fetched from {provider}."
        if summary:
            status = f"{status} {summary}"
        self.status_label.setText(status)
        self._update_download_button_state()

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
        enable = bool(self.results.selectionModel().selectedRows())
        self.download_button.setEnabled(enable)

    def _connect_worker_cleanup(
        self,
        worker: QtCore.QObject,
        thread: QtCore.QThread,
    ) -> None:
        def cleanup(*_args: object) -> None:
            if thread.isRunning():
                thread.quit()
                thread.wait()
            worker.deleteLater()
            thread.deleteLater()
            if worker is self._search_worker:
                self._search_worker = None
                self._search_thread = None
            if worker is self._download_worker:
                self._download_worker = None
                self._download_thread = None

        worker.finished.connect(cleanup)
        worker.failed.connect(cleanup)
        worker.cancelled.connect(cleanup)

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
        """Request shutdown and optionally wait for the worker thread.

        Returns ``True`` when the thread has stopped and been cleaned up. When
        ``timeout_ms`` is ``None`` the call blocks until the thread exits. A
        finite timeout keeps the UI responsive by allowing the caller to poll
        for completion using ``QtCore.QTimer``.
        """

        thread = getattr(self, thread_attr)
        worker = getattr(self, worker_attr)
        if thread is None:
            return True
        if thread.isRunning():
            thread.quit()
            if timeout_ms is not None:
                if not thread.wait(timeout_ms):
                    return False
            else:
                thread.wait()
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
        return {"text": stripped} if stripped else {}

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
        citation = self._extract_citation(record.metadata)
        if citation:
            narrative_lines.append(f"Citation: {citation}")
        if narrative_lines:
            narrative_lines.append("")
        narrative_lines.append(json.dumps(metadata, indent=2, ensure_ascii=False))
        self.preview.setPlainText("\n".join(narrative_lines))

    def _on_selection_changed(self) -> None:
        self._update_preview()
        self._update_download_button_state()

    def _populate_results_table(self, records: Sequence[RemoteRecord]) -> None:
        self._clear_result_widgets()
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

    def _set_download_widget(self, row: int, column: int, url: str) -> None:
        label = QtWidgets.QLabel(self.results)
        hyperlink = self._link_for_download(url)
        escaped = html.escape(hyperlink)
        label.setText(f'<a href="{escaped}">Open</a>')
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        tooltip = url
        if hyperlink != url:
            tooltip = f"{url}\n{hyperlink}"
        label.setToolTip(tooltip)
        label.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.results.setCellWidget(row, column, label)

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

    def _on_queue_downloads(self) -> None:
        if self._busy:
            return
        selected = self.results.selectionModel().selectedRows()
        if not selected:
            self.status_label.setText("Select at least one record to import.")
            return

        records = [self._records[index.row()] for index in selected]
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
                RemoteDataService.PROVIDER_MAST: (
                    "Solar system body, host star, or exoplanet target (e.g. Jupiter, TRAPPIST-1, WASP-96 b)…"
                ),
            }
            self._provider_hints = {
                RemoteDataService.PROVIDER_MAST: (
                    "MAST requests favour calibrated spectra (IFS cubes, slits, prisms) and Exo.MAST cross-matching with the "
                    "NASA Exoplanet Archive. Enable \"Include imaging\" to add calibrated previews alongside spectra."
                ),
            }
            self._provider_examples = {
                RemoteDataService.PROVIDER_MAST: [
                    ("Jupiter – JWST/NIRCam (solar system)", "Jupiter"),
                    ("TRAPPIST-1e – JWST/NIRSpec (exoplanet host)", "TRAPPIST-1"),
                    ("HD 189733 – HST/STIS (stellar benchmark)", "HD 189733"),
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
        self._update_download_button_state()

    # ------------------------------------------------------------------
    def _format_status_summary(self, records: Sequence[RemoteRecord]) -> str:
        if not records:
            return ""
        metadata = records[0].metadata if isinstance(records[0].metadata, Mapping) else {}
        focus = [self._format_exoplanet_summary(metadata)]
        mission = self._format_mission(metadata)
        instrument = self._format_instrument(metadata)
        focus.extend([mission, instrument])
        cleaned = [part for part in focus if part]
        return " | ".join(cleaned)

    def _format_target(self, record: RemoteRecord) -> str:
        metadata = record.metadata if isinstance(record.metadata, Mapping) else {}
        target = self._first_text(metadata, ["target_name", "target", "title"]) or record.title
        host = self._first_text(metadata, ["host_name", "hostname", "star_name", "st_name"])
        planet = self._first_text(metadata, ["planet_name", "pl_name", "exoplanet", "object"])
        label_parts: list[str] = []
        if planet and host:
            label_parts.append(f"{planet} ({host})")
        elif planet:
            label_parts.append(str(planet))
        elif host and target and host != target:
            label_parts.append(f"{target} ({host})")
        if target and target not in label_parts:
            label_parts.append(str(target))
        return " • ".join(dict.fromkeys([part for part in label_parts if part]))

    def _format_mission(self, metadata: Mapping[str, Any] | Any) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        mission_candidates = [
            self._first_text(mapping, ["telescope", "mission", "facility", "obs_collection", "project"]),
            self._first_text(mapping, ["proposal_id", "proposal_title"]),
        ]
        mission_parts = [part for part in mission_candidates if part]
        return " • ".join(dict.fromkeys(mission_parts))

    def _format_instrument(self, metadata: Mapping[str, Any] | Any) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        instrument = self._first_text(mapping, ["instrument_name", "instrument", "detector", "channel"])
        mode = self._first_text(mapping, ["observation_mode", "mode", "obsmode", "configuration", "aperture"])
        parts = [part for part in (instrument, mode) if part]
        return " • ".join(parts)

    def _format_product(self, metadata: Mapping[str, Any] | Any) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        product = self._first_text(mapping, ["dataproduct_type", "productType", "intentType"])
        calibration = self._first_text(mapping, ["calib_level", "dataRights"])
        parts = [part for part in (product, calibration) if part]
        return " • ".join(parts)

    def _extract_citation(self, metadata: Mapping[str, Any] | Any) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        citation = self._first_text(
            mapping,
            [
                "citation",
                "short_citation",
                "reference",
                "bib_reference",
                "bibcode",
                "proposal_pi",
            ],
        )
        if citation:
            return str(citation)
        pi = self._first_text(mapping, ["proposal_pi"])
        cycle = self._first_text(mapping, ["proposal_cycle", "cycle"])
        if pi or cycle:
            descriptor = ", ".join(part for part in (pi, cycle) if part)
            return descriptor
        return ""

    def _format_exoplanet_summary(self, metadata: Mapping[str, Any]) -> str:
        planet = self._first_text(metadata, ["planet_name", "pl_name", "target_name", "object"])
        host = self._first_text(metadata, ["host_name", "hostname", "star_name", "st_name"])
        discovery = self._first_text(metadata, ["discoverymethod", "disc_method", "discovery_method"])
        period = self._first_number(metadata, ["pl_orbper", "orbital_period", "period_days"])
        teff = self._first_number(metadata, ["st_teff", "teff", "stellar_temperature"])
        summary_parts: list[str] = []
        if planet and host:
            summary_parts.append(f"{planet} around {host}")
        elif planet:
            summary_parts.append(str(planet))
        elif host:
            summary_parts.append(str(host))
        if discovery:
            summary_parts.append(f"Discovery: {discovery}")
        if period is not None:
            formatted_period = self._format_numeric(period, " d", decimals=2)
            if formatted_period:
                summary_parts.append(f"Period: {formatted_period}")
        if teff is not None:
            formatted_teff = self._format_numeric(teff, " K", decimals=0)
            if formatted_teff:
                summary_parts.append(f"T_eff: {formatted_teff}")
        return " • ".join(summary_parts)

    def _first_text(self, metadata: Mapping[str, Any], keys: Sequence[str]) -> str:
        for key in keys:
            value = self._lookup_metadata(metadata, key)
            if value is None:
                continue
            if isinstance(value, (list, tuple, set)):
                text = ", ".join(str(part).strip() for part in value if str(part).strip())
            else:
                text = str(value).strip()
            if text:
                return text
        return ""

    def _first_number(self, metadata: Mapping[str, Any], keys: Sequence[str]) -> float | None:
        for key in keys:
            value = self._lookup_metadata(metadata, key)
            if value is None:
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(number):
                return number
        return None

    def _lookup_metadata(self, metadata: Mapping[str, Any], key: str) -> Any:
        candidates = [metadata]
        nested_keys = ("exomast", "exo_mast", "exoplanet_archive", "exoplanet", "planet", "host")
        for nested in nested_keys:
            value = metadata.get(nested)
            if isinstance(value, Mapping):
                candidates.append(value)
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            if key in candidate and candidate[key] not in (None, ""):
                return candidate[key]
        return None

    def _format_numeric(self, value: float, suffix: str, *, decimals: int) -> str:
        if not math.isfinite(value):
            return ""
        if abs(value - round(value)) < 10 ** -(decimals + 1):
            return f"{int(round(value))}{suffix}"
        return f"{value:.{decimals}f}{suffix}"

    def _link_for_download(self, url: str) -> str:
        if url.startswith("mast:"):
            encoded = quote(url, safe="")
            return f"https://mast.stsci.edu/portal/Download/file?uri={encoded}"
        return url


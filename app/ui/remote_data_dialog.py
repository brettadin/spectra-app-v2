"""Remote data discovery dialog."""

from __future__ import annotations

import html
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
        self.started.emit()  # type: ignore[attr-defined]
        collected: list[RemoteRecord] = []
        try:
            results = self._remote_service.search(
                provider,
                query,
                include_imaging=include_imaging,
            )
            for record in results:
                if self._cancel_requested:
                    self.cancelled.emit()  # type: ignore[attr-defined]
                    return
                collected.append(record)
                self.record_found.emit(record)  # type: ignore[attr-defined]
            if self._cancel_requested:
                self.cancelled.emit()  # type: ignore[attr-defined]
                return
        except Exception as exc:  # pragma: no cover - defensive: surfaced via signal
            self.failed.emit(str(exc))  # type: ignore[attr-defined]
            return
        self.finished.emit(collected)  # type: ignore[attr-defined]

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
                    ingested_item = self._ingest_service.ingest(
                        Path(download.cache_entry["stored_path"])
                    )
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
        self._shutdown_timer: QtCore.QTimer | None = None
        self._shutdown_requested = False
        self._quick_pick_targets: list[Mapping[str, Any]] = []

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
        self._populate_results_table(records)
        self.status_label.setText(
            f"{len(records)} result(s) fetched from {self.provider_combo.currentText()}."
        )
        if records:
            self.results.selectRow(0)
        else:
            self.preview.clear()
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
        self.download_button.setEnabled(bool(self._records) and not downloading and not searching)

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

    def _set_busy(self, busy: bool, *, message: str | None = None) -> None:
        """Toggle busy state using the animated progress label.

        This mirrors the earlier implementation defined for search/download
        flows and avoids referencing a non-existent ``progress_indicator``.
        """
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
            if getattr(self, "progress_movie", None) and self.progress_movie.isValid():
                self.progress_movie.start()
            self.progress_label.setVisible(True)
        else:
            if getattr(self, "progress_movie", None) and self.progress_movie.isValid():
                self.progress_movie.stop()
            self.progress_label.setVisible(False)
            self._update_download_button_state()

        if message is not None:
            self.status_label.setText(message)

    # ------------------------------------------------------------------
    def reject(self) -> None:  # type: ignore[override]
        if self._shutdown_requested:
            return

        threads = [
            thread
            for thread in (self._search_thread, self._download_thread)
            if thread is not None and thread.isRunning()
        ]
        if not threads:
            self._finish_reject()
            return

        self._shutdown_requested = True
        self._set_busy(True)
        self.status_label.setText(
            "Closing Remote Data… waiting for background tasks to finish."
        )
        timer = self._ensure_shutdown_timer()
        self._poll_shutdown_threads()
        if self._shutdown_requested:
            timer.start()

    def _ensure_shutdown_timer(self) -> QtCore.QTimer:
        if self._shutdown_timer is None:
            timer = QtCore.QTimer(self)
            timer.setInterval(150)
            timer.setSingleShot(False)
            timer.timeout.connect(self._poll_shutdown_threads)
            self._shutdown_timer = timer
        return self._shutdown_timer

    def _poll_shutdown_threads(self) -> None:
        if not self._shutdown_requested:
            return

        active = False
        for thread in (self._search_thread, self._download_thread):
            if thread is None:
                continue
            if thread.isRunning():
                if not thread.wait(0):
                    active = True
                    continue
            thread.wait(0)

        if active:
            return

        self._finish_reject()

    def _finish_reject(self) -> None:
        timer = self._shutdown_timer
        if timer is not None:
            timer.stop()
            timer.deleteLater()
            self._shutdown_timer = None
        self._shutdown_requested = False
        self._set_busy(False)
        super().reject()

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


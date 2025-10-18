"""Remote data discovery dialog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from app.qt_compat import get_qt
from app.services import DataIngestService, RemoteDataService, RemoteRecord

QtCore, QtGui, QtWidgets, _ = get_qt()


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
        self._provider_validation_messages: dict[str, str] = {}
        self._dependency_hint: str = ""

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

        self.search_button = QtWidgets.QPushButton("Search", self)
        self.search_button.clicked.connect(self._on_search)
        controls.addWidget(self.search_button)

        layout.addLayout(controls)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self)
        layout.addWidget(splitter, 1)

        self.results = QtWidgets.QTableWidget(self)
        self.results.setColumnCount(3)
        self.results.setHorizontalHeaderLabels(["ID", "Title", "Source"])
        self.results.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.results.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.results.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.results.verticalHeader().setVisible(False)
        self.results.itemSelectionChanged.connect(self._update_preview)
        splitter.addWidget(self.results)

        self.preview = QtWidgets.QPlainTextEdit(self)
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Select a result to preview metadata")
        splitter.addWidget(self.preview)

        buttons = QtWidgets.QDialogButtonBox(self)
        self.download_button = buttons.addButton("Download & Import", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        self.download_button.clicked.connect(self._on_queue_downloads)
        cancel = buttons.addButton(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        cancel.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self.hint_label = QtWidgets.QLabel(self)
        self.hint_label.setObjectName("remote-hint")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        self.status_label = QtWidgets.QLabel(self)
        self.status_label.setObjectName("remote-status")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self._refresh_provider_state()

    # ------------------------------------------------------------------
    def _on_search(self) -> None:
        provider = self._current_provider_key()
        query = self._build_provider_query(provider, self.search_edit.text())
        if not query:
            message = self._provider_validation_messages.get(
                provider,
                "Enter search criteria before querying remote catalogues.",
            )
            QtWidgets.QMessageBox.information(self, "Search criteria required", message)
            self.status_label.setText(message)
            self.results.setRowCount(0)
            self.preview.clear()
            return
        try:
            records = self.remote_service.search(provider, query)
        except Exception as exc:  # pragma: no cover - UI feedback
            QtWidgets.QMessageBox.critical(self, "Search failed", str(exc))
            return

        self._records = records
        self.results.setRowCount(len(records))
        for row, record in enumerate(records):
            self.results.setItem(row, 0, QtWidgets.QTableWidgetItem(record.identifier))
            self.results.setItem(row, 1, QtWidgets.QTableWidgetItem(record.title))
            self.results.setItem(row, 2, QtWidgets.QTableWidgetItem(record.download_url))
        self.status_label.setText(f"{len(records)} result(s) fetched from {provider}.")
        if records:
            self.results.selectRow(0)
        else:
            self.preview.clear()

    def _on_provider_changed(self, index: int | None = None) -> None:
        # Accept the index argument emitted by Qt while keeping the logic driven
        # by the current provider string so external callers can trigger the
        # refresh without supplying an index explicitly.
        if index is not None:
            # Qt passes the numeric index; the logic below derives values from
            # the provider string so the argument is intentionally ignored.
            pass
        provider = self._current_provider_key()
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

    def _current_provider_key(self) -> str:
        """Return canonical provider key (userData) for current selection."""
        data = self.provider_combo.currentData()
        if isinstance(data, str) and data:
            return data
        return str(self.provider_combo.currentText() or "")

    def _build_provider_query(self, provider: str, text: str) -> dict[str, str]:
        stripped = text.strip()
        if provider == RemoteDataService.PROVIDER_MAST:
            return {"target_name": stripped} if stripped else {}
        if provider == RemoteDataService.PROVIDER_NIST:
            return {"element": stripped} if stripped else {}
        return {"text": stripped} if stripped else {}

    def _update_preview(self) -> None:
        indexes = self.results.selectionModel().selectedRows()
        if not indexes:
            self.preview.clear()
            return
        payload = self._records[indexes[0].row()].metadata
        self.preview.setPlainText(json.dumps(payload, indent=2, ensure_ascii=False))

    def _on_queue_downloads(self) -> None:
        selected = self.results.selectionModel().selectedRows()
        if not selected:
            QtWidgets.QMessageBox.information(self, "No selection", "Select at least one record to import.")
            return

        spectra: List[object] = []
        for index in selected:
            record = self._records[index.row()]
            try:
                download = self.remote_service.download(record)
                spectrum = self.ingest_service.ingest(Path(download.cache_entry["stored_path"]))
            except Exception as exc:  # pragma: no cover - UI feedback
                QtWidgets.QMessageBox.warning(self, "Download failed", str(exc))
                continue
            spectra.append(spectrum)

        if not spectra:
            return

        self._ingested = spectra
        self.accept()

    def _refresh_provider_state(self) -> None:
        available = set(self.remote_service.providers())
        unavailable = self.remote_service.unavailable_providers()

        # Populate the combo with both available and unavailable providers so
        # the user can still select and inspect catalogue descriptions. The
        # availability state controls whether searches are permitted.
        self.provider_combo.clear()
        # Add available providers first (store canonical key as userData)
        for p in sorted(available):
            self.provider_combo.addItem(p, p)
        # Add unavailable providers (annotated display text), keep key in userData
        for p in sorted(unavailable.keys()):
            if p not in available:
                self.provider_combo.addItem(f"{p} (dependencies missing)", p)

        # The combo and search box should remain enabled so users can choose a
        # provider and type queries. The search button is enabled only when the
        # currently selected provider has its dependencies satisfied.
        self.provider_combo.setEnabled(True)
        self.search_edit.setEnabled(True)
        # placeholders and hints for known providers (without annotations)
        self._provider_placeholders = {
            RemoteDataService.PROVIDER_NIST: "Fe II, H-alpha, or ion symbol…",
            RemoteDataService.PROVIDER_MAST: "JWST spectroscopic target (e.g. WASP-96 b, NIRSpec)…",
        }
        self._provider_hints = {
            RemoteDataService.PROVIDER_NIST: (
                "Searches target laboratory-grade spectral line lists from the NIST ASD."
            ),
            RemoteDataService.PROVIDER_MAST: (
                "MAST requests favour calibrated spectra (IFS cubes, slits, prisms) using the "
                "`dataproduct_type=spectrum` filter so results align with lab references."
            ),
        }
        self._provider_validation_messages = {
            RemoteDataService.PROVIDER_NIST: (
                "Enter an element, ion, or transition label before searching the NIST ASD."
            ),
            RemoteDataService.PROVIDER_MAST: (
                "MAST searches require a target name or instrument keyword (e.g. WASP-96 b, NIRSpec)."
            ),
        }

        # Compose dependency hint text (if any)
        if unavailable:
            messages = []
            for provider, reason in unavailable.items():
                messages.append(f"{provider}: {reason}")
            self._dependency_hint = "\n".join(messages)
        else:
            self._dependency_hint = ""

        # Update status depending on whether any providers are available.
        if not available:
            if not unavailable:
                self.status_label.setText("Remote catalogues are temporarily unavailable.")
            else:
                self.status_label.setText(
                    "Remote catalogues are unavailable until the required optional dependencies are installed."
                )
        else:
            self.status_label.clear()

        # Adjust the Search button enablement based on the currently selected
        # provider's availability. If provider name includes our annotation,
        # treat it as unavailable.
        self._on_provider_changed()
        key = self._current_provider_key()
        self.search_button.setEnabled(bool(key) and key in available)


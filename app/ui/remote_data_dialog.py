"""Remote data discovery dialog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

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

        self._provider_hints: Dict[str, Dict[str, str]] = {
            RemoteDataService.PROVIDER_NIST: {
                "placeholder": "Element symbol (e.g. Fe II) or wavelength range",
                "hint": (
                    "NIST ASD accepts element symbols, ionisation stages, or keyword"
                    " filters. Use tokens like 'element:Fe II' or 'wavelength_min:250'"
                    " to refine queries."
                ),
            },
            RemoteDataService.PROVIDER_MAST: {
                "placeholder": "Target name (e.g. WASP-96 b) or obsid:12345",
                "hint": (
                    "MAST searches map free text to 'target_name'. Provide additional"
                    " filters like 'obsid:12345' or 'instrument:NIRSpec' for precise"
                    " lookups."
                ),
            },
        }

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

        self.provider_hint_label = QtWidgets.QLabel(self)
        self.provider_hint_label.setObjectName("remote-provider-hint")
        self.provider_hint_label.setWordWrap(True)
        layout.addWidget(self.provider_hint_label)

        self._refresh_provider_state()

    # ------------------------------------------------------------------
    def _on_search(self) -> None:
        provider = self.provider_combo.currentText()
        query = self._build_query(provider, self.search_edit.text().strip())
        if provider == RemoteDataService.PROVIDER_MAST and not query:
            QtWidgets.QMessageBox.information(
                self,
                "Search criteria required",
                "Enter a target name or key:value filter before querying MAST.",
            )
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

    def _on_provider_changed(self, index: int) -> None:
        if index < 0:
            return
        provider = self.provider_combo.itemText(index)
        hints = self._provider_hints.get(provider)
        if hints:
            self.search_edit.setPlaceholderText(hints.get("placeholder", self.search_edit.placeholderText()))
            self.provider_hint_label.setText(hints.get("hint", ""))
        else:
            self.search_edit.setPlaceholderText("Element, target name, or keyword…")
            self.provider_hint_label.clear()
        self.status_label.clear()

    def _build_query(self, provider: str, text: str) -> Dict[str, Any]:
        text = text.strip()
        if not text:
            return {}
        tokens = [token.strip() for token in text.split() if token.strip()]
        explicit: Dict[str, Any] = {}
        for token in tokens:
            if ":" in token:
                key, value = token.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    try:
                        numeric = float(value)
                    except ValueError:
                        explicit[key] = value
                    else:
                        explicit[key] = numeric
        if provider == RemoteDataService.PROVIDER_NIST:
            if "element" not in explicit and "spectra" not in explicit and text:
                explicit["element"] = text
            return explicit
        if provider == RemoteDataService.PROVIDER_MAST:
            aliases = {
                "target": "target_name",
                "name": "target_name",
            }
            normalised: Dict[str, Any] = {}
            for key, value in explicit.items():
                normalised[aliases.get(key, key)] = value
            if "target_name" not in normalised and text:
                normalised["target_name"] = text
            return normalised
        return {"text": text}

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
        providers = self.remote_service.providers()
        self.provider_combo.blockSignals(True)
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
        self.provider_combo.blockSignals(False)

        unavailable = self.remote_service.unavailable_providers()
        if unavailable:
            messages = []
            for provider, reason in unavailable.items():
                messages.append(f"{provider}: {reason}")
            self.hint_label.setText("\n".join(messages))
        else:
            self.hint_label.clear()

        if not providers:
            if not unavailable:
                self.status_label.setText("Remote catalogues are temporarily unavailable.")
            else:
                self.status_label.setText(
                    "Remote catalogues are unavailable until the required optional dependencies are installed."
                )
            self.provider_hint_label.clear()
        else:
            self._on_provider_changed(self.provider_combo.currentIndex())


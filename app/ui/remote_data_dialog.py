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
        self._provider_examples: dict[str, list[tuple[str, str]]] = {}
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

        try:
            records = self.remote_service.search(
                provider,
                query,
                include_imaging=include_imaging,
            )
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
                ingested = self.ingest_service.ingest(Path(download.cache_entry["stored_path"]))
            except Exception as exc:  # pragma: no cover - UI feedback
                QtWidgets.QMessageBox.warning(self, "Download failed", str(exc))
                continue
            if isinstance(ingested, list):
                spectra.extend(ingested)
            else:
                spectra.append(ingested)

        if not spectra:
            return

        self._ingested = spectra
        self.accept()

    def _refresh_provider_state(self) -> None:
        providers = list(self.remote_service.providers())
        self.provider_combo.clear()
        if providers:
            self.provider_combo.addItems(providers)
            self.provider_combo.setEnabled(True)
            self.search_edit.setEnabled(True)
            self.search_button.setEnabled(True)
            self._provider_placeholders = {}
            self._provider_hints = {}
            self._provider_examples = {}

            if RemoteDataService.PROVIDER_MAST in providers:
                self._provider_placeholders[RemoteDataService.PROVIDER_MAST] = (
                    "JWST spectroscopic target (e.g. WASP-96 b, NIRSpec)…"
                )
                self._provider_hints[RemoteDataService.PROVIDER_MAST] = (
                    "MAST requests favour calibrated spectra (IFS cubes, slits, prisms). Enable "
                    "\"Include imaging\" to broaden results with calibrated image products."
                )
                self._provider_examples[RemoteDataService.PROVIDER_MAST] = [
                    ("WASP-96 b – JWST/NIRSpec", "WASP-96 b"),
                    ("WASP-39 b – JWST/NIRSpec", "WASP-39 b"),
                    ("HD 189733 – JWST/NIRISS", "HD 189733"),
                ]

            if RemoteDataService.PROVIDER_NIST in providers:
                self._provider_placeholders[RemoteDataService.PROVIDER_NIST] = (
                    "Element or ion (e.g. Fe II, H I)…"
                )
                self._provider_hints[RemoteDataService.PROVIDER_NIST] = (
                    "The NIST Atomic Spectra Database searches spectral line lists. Supply an element "
                    "or specific ion to retrieve transition data."
                )
                self._provider_examples[RemoteDataService.PROVIDER_NIST] = [
                    ("Fe II ultraviolet lines", "Fe II"),
                    ("Neutral hydrogen Balmer series", "H I"),
                ]
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


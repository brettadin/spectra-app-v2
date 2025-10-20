"""UI smoke tests for the Remote Data dialog."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, List

import pytest

from app.qt_compat import get_qt
from app.services import LocalStore, RemoteDataService, RemoteRecord

try:  # pragma: no cover - skip when Qt bindings unavailable
    QtCore, QtGui, QtWidgets, _ = get_qt()
except ImportError:  # pragma: no cover - test skipped in headless envs
    pytest.skip("Qt bindings not available for RemoteDataDialog smoke test", allow_module_level=True)

from app.ui.remote_data_dialog import RemoteDataDialog


class StubRemoteService(RemoteDataService):
    def __init__(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="spectra-remote-test-"))
        super().__init__(store=LocalStore(base_dir=base))
        self._providers: List[str] = [
            RemoteDataService.PROVIDER_NIST,
            RemoteDataService.PROVIDER_MAST,
        ]

    def providers(self) -> List[str]:
        return list(self._providers)

    def unavailable_providers(self) -> dict[str, str]:
        return {}


class TrackingRemoteService(StubRemoteService):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, dict[str, Any], bool]] = []
        self.stub_records: list[RemoteRecord] = []

    def queue_record(self, record: RemoteRecord) -> None:
        self.stub_records.append(record)

    def search(
        self,
        provider: str,
        query: dict[str, Any],
        *,
        include_imaging: bool = False,
    ) -> List[RemoteRecord]:
        self.calls.append((provider, dict(query), include_imaging))
        if self.stub_records:
            return [self.stub_records.pop(0)]
        return []


def _ensure_app() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def test_dialog_initialises_without_missing_slots(monkeypatch: Any) -> None:
    app = _ensure_app()
    ingest = IngestServiceStub()
    dialog = RemoteDataDialog(
        None,
        remote_service=StubRemoteService(),
        ingest_service=ingest,
    )

    assert dialog.provider_combo.count() == 1
    assert dialog.provider_combo.itemText(0) == RemoteDataService.PROVIDER_MAST
    assert "Catalogue" in dialog.windowTitle() or dialog.windowTitle() == "Remote Data"

    # Trigger provider refresh to ensure the slot updates hints/placeholder.
    dialog._on_provider_changed()
    assert "Solar system" in dialog.search_edit.placeholderText()

    # Clean up the dialog explicitly for Qt stability in headless tests.
    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_empty_search_does_not_hit_service(monkeypatch: Any) -> None:
    app = _ensure_app()
    service = TrackingRemoteService()
    ingest = IngestServiceStub()

    dialog = RemoteDataDialog(
        None,
        remote_service=service,
        ingest_service=ingest,
    )

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "information",
        lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.Ok,
    )

    dialog.search_edit.setText("   ")
    dialog._on_search()

    assert service.calls == []

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_example_selection_runs_search(monkeypatch: Any) -> None:
    app = _ensure_app()
    service = TrackingRemoteService()
    ingest = IngestServiceStub()

    record = RemoteRecord(
        provider=RemoteDataService.PROVIDER_MAST,
        identifier="obsid-1",
        title="WASP-96 b",
        download_url="mast:JWST/product.fits",
        metadata={"units": {"x": "um", "y": "flux"}},
        units={"x": "um", "y": "flux"},
    )
    service.queue_record(record)

    dialog = RemoteDataDialog(
        None,
        remote_service=service,
        ingest_service=ingest,
    )

    provider_index = dialog.provider_combo.findText(RemoteDataService.PROVIDER_MAST)
    dialog.provider_combo.setCurrentIndex(provider_index)

    assert dialog.example_combo.isEnabled()
    assert dialog.example_combo.count() > 1

    dialog._on_example_selected(1)

    assert service.calls, "Example selection should trigger a search"
    provider, query, include_imaging = service.calls[0]
    assert provider == RemoteDataService.PROVIDER_MAST
    assert query.get("target_name")
    assert dialog.search_edit.text() == query["target_name"]
    assert include_imaging is False

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_include_imaging_toggle_passes_flag(monkeypatch: Any) -> None:
    app = _ensure_app()
    service = TrackingRemoteService()
    ingest = IngestServiceStub()

    dialog = RemoteDataDialog(
        None,
        remote_service=service,
        ingest_service=ingest,
    )

    provider_index = dialog.provider_combo.findText(RemoteDataService.PROVIDER_MAST)
    dialog.provider_combo.setCurrentIndex(provider_index)

    assert dialog.include_imaging_checkbox.isVisible()
    dialog.include_imaging_checkbox.setChecked(True)

    dialog.search_edit.setText("WASP-39 b")
    dialog._on_search()

    assert service.calls, "Search should record include_imaging flag"
    _, _, include_imaging = service.calls[-1]
    assert include_imaging is True

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_results_table_displays_extended_columns_and_preview(monkeypatch: Any) -> None:
    app = _ensure_app()
    service = TrackingRemoteService()
    ingest = IngestServiceStub()

    metadata = {
        "target_name": "WASP-96 b",
        "host_name": "WASP-96",
        "planet_name": "WASP-96 b",
        "mission": "JWST",
        "telescope": "JWST",
        "instrument_name": "NIRSpec",
        "observation_mode": "Bright Object Time Series",
        "dataproduct_type": "spectrum",
        "productType": "SCIENCE",
        "previewURL": "https://example.test/preview.png",
        "citation": "Ahrer et al. 2022, JWST ERS",
        "calib_level": 3,
        "exomast": {
            "pl_name": "WASP-96 b",
            "hostname": "WASP-96",
            "discoverymethod": "Transit",
            "pl_orbper": 3.425,
            "st_teff": 5600,
        },
    }

    record = RemoteRecord(
        provider=RemoteDataService.PROVIDER_MAST,
        identifier="obsid-1",
        title="WASP-96 b",
        download_url="mast:JWST/product.fits",
        metadata=metadata,
        units={"x": "um", "y": "flux"},
    )
    service.queue_record(record)

    dialog = RemoteDataDialog(
        None,
        remote_service=service,
        ingest_service=ingest,
    )

    provider_index = dialog.provider_combo.findText(RemoteDataService.PROVIDER_MAST)
    dialog.provider_combo.setCurrentIndex(provider_index)
    dialog.search_edit.setText("WASP-96 b")
    dialog._on_search()

    headers = [dialog.results.horizontalHeaderItem(i).text() for i in range(dialog.results.columnCount())]
    assert headers == [
        "ID",
        "Title",
        "Target / Host",
        "Telescope / Mission",
        "Instrument / Mode",
        "Product Type",
        "Download",
        "Preview / Citation",
    ]

    download_column = headers.index("Download")
    download_widget = dialog.results.cellWidget(0, download_column)
    assert isinstance(download_widget, QtWidgets.QLabel)
    assert "href" in download_widget.text()
    assert "https://mast.stsci.edu/portal/Download/file?uri=" in download_widget.text()

    preview_column = headers.index("Preview / Citation")
    preview_widget = dialog.results.cellWidget(0, preview_column)
    assert isinstance(preview_widget, QtWidgets.QLabel)
    assert "Preview" in preview_widget.text()
    assert "Ahrer et al. 2022" in preview_widget.text()

    status_text = dialog.status_label.text()
    assert "WASP-96 b around WASP-96" in status_text
    assert "JWST" in status_text

    dialog.results.selectRow(0)
    QtWidgets.QApplication.processEvents()
    preview_text = dialog.preview.toPlainText()
    assert "WASP-96 b around WASP-96" in preview_text
    assert "Citation: Ahrer et al. 2022" in preview_text

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


class IngestServiceStub:
    """Minimal stub mimicking the ingest service used by the dialog."""

    def ingest(self, path: Path) -> Any:  # pragma: no cover - not exercised in this smoke test
        raise RuntimeError(f"ingest not expected in dialog smoke test for {path}")

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
            RemoteDataService.PROVIDER_EXOSYSTEMS,
        ]

    def providers(self, *, include_reference: bool = True) -> List[str]:
        providers = list(self._providers)
        if include_reference:
            return providers
        return [
            provider
            for provider in providers
            if provider != RemoteDataService.PROVIDER_NIST
        ]

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


def _spin_until(predicate, app: QtWidgets.QApplication, timeout_ms: int = 2000) -> None:
    timer = QtCore.QElapsedTimer()
    timer.start()
    while not predicate():
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
        if timer.hasExpired(timeout_ms):
            pytest.fail("Timed out waiting for RemoteDataDialog background work")


def test_dialog_initialises_without_missing_slots(monkeypatch: Any) -> None:
    app = _ensure_app()
    ingest = IngestServiceStub()
    dialog = RemoteDataDialog(
        None,
        remote_service=StubRemoteService(),
        ingest_service=ingest,
    )

    assert dialog.provider_combo.count() == 2
    assert dialog.provider_combo.itemText(0) == RemoteDataService.PROVIDER_MAST
    assert dialog.provider_combo.itemText(1) == RemoteDataService.PROVIDER_EXOSYSTEMS
    assert dialog.provider_combo.findText(RemoteDataService.PROVIDER_NIST) == -1
    assert "Catalogue" in dialog.windowTitle() or dialog.windowTitle() == "Remote Data"

    # Trigger provider refresh to ensure the slot updates hints/placeholder.
    dialog._on_provider_changed()
    placeholder = dialog.search_edit.placeholderText()
    assert "JWST" in placeholder
    assert "MAST" in dialog.hint_label.text()

    # Clean up the dialog explicitly for Qt stability in headless tests.
    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_reference_only_service_disables_combo(monkeypatch: Any) -> None:
    app = _ensure_app()

    class NistOnlyService(StubRemoteService):
        def __init__(self) -> None:
            super().__init__()
            self._providers = [RemoteDataService.PROVIDER_NIST]

    ingest = IngestServiceStub()
    dialog = RemoteDataDialog(
        None,
        remote_service=NistOnlyService(),
        ingest_service=ingest,
    )

    assert dialog.provider_combo.count() == 0
    assert dialog.provider_combo.isEnabled() is False
    assert dialog.search_edit.isEnabled() is False
    assert "Remote catalogues" in dialog.status_label.text()

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

    _spin_until(lambda: bool(service.calls), app)
    _spin_until(lambda: dialog._search_thread is None, app)

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

    _spin_until(lambda: bool(service.calls), app)
    _spin_until(lambda: dialog._search_thread is None, app)

    assert service.calls, "Search should record include_imaging flag"
    _, _, include_imaging = service.calls[-1]
    assert include_imaging is True

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_build_provider_query_parses_nist_fields(monkeypatch: Any) -> None:
    app = _ensure_app()
    ingest = IngestServiceStub()
    dialog = RemoteDataDialog(
        None,
        remote_service=StubRemoteService(),
        ingest_service=ingest,
    )

    query = dialog._build_provider_query(
        RemoteDataService.PROVIDER_NIST,
        "element=Fe II; keyword=aurora; ion=III",
    )

    assert query["element"] == "Fe II"
    assert query["text"] == "aurora"
    assert query["ion_stage"] == "III"

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_populate_results_table_builds_links_and_preview(monkeypatch: Any) -> None:
    app = _ensure_app()
    ingest = IngestServiceStub()
    dialog = RemoteDataDialog(
        None,
        remote_service=StubRemoteService(),
        ingest_service=ingest,
    )

    metadata = {
        "target_name": "WASP-96 b",
        "obs_collection": "JWST",
        "instrument_name": "NIRSpec",
        "grating": "G395H",
        "filters": ["F290LP"],
        "dataproduct_type": "spectrum",
        "intentType": "SCIENCE",
        "calib_level": 3,
        "preview_url": "https://example.invalid/preview.jpg",
        "citations": [
            {
                "title": "JWST early release observations",
                "doi": "10.1234/example",
            }
        ],
        "exoplanet": {
            "display_name": "WASP-96 b",
            "classification": "Hot Jupiter",
            "host_star": "WASP-96",
        },
    }

    record = RemoteRecord(
        provider=RemoteDataService.PROVIDER_MAST,
        identifier="obsid-0001",
        title="WASP-96 b transit",
        download_url="mast:JWST/product.fits",
        metadata=metadata,
        units={"x": "um", "y": "flux"},
    )

    dialog._handle_search_results([record])

    assert dialog.results.rowCount() == 1
    assert dialog.results.columnCount() == 8
    assert dialog.results.horizontalHeaderItem(7).text() == "Preview / Citation"

    target_item = dialog.results.item(0, 2)
    assert target_item is not None
    assert target_item.text() == "WASP-96 b"

    product_item = dialog.results.item(0, 5)
    assert product_item is not None
    assert "Level 3" in product_item.text()

    download_widget = dialog.results.cellWidget(0, 6)
    assert isinstance(download_widget, QtWidgets.QLabel)
    href = "https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:JWST/product.fits"
    assert href in download_widget.text()
    assert "Open" in download_widget.text()

    preview_widget = dialog.results.cellWidget(0, 7)
    assert isinstance(preview_widget, QtWidgets.QLabel)
    preview_text = preview_widget.text()
    assert "Preview" in preview_text
    assert "DOI 10.1234/example" in preview_text

    dialog.results.selectRow(0)
    dialog._update_preview()
    assert "Citation: DOI 10.1234/example" in dialog.preview.toPlainText()

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


class IngestServiceStub:
    """Minimal stub mimicking the ingest service used by the dialog."""

    def ingest(self, path: Path) -> Any:  # pragma: no cover - not exercised in this smoke test
        raise RuntimeError(f"ingest not expected in dialog smoke test for {path}")

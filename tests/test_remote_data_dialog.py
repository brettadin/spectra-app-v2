"""UI smoke tests for the Remote Data dialog."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any, Callable, List

import pytest

from app.qt_compat import get_qt
from app.services import LocalStore, RemoteDataService, RemoteRecord

try:  # pragma: no cover - skip when Qt bindings unavailable
    QtCore, QtGui, QtWidgets, _ = get_qt()
except ImportError:  # pragma: no cover - test skipped in headless envs
    pytest.skip("Qt bindings not available for RemoteDataDialog smoke test", allow_module_level=True)

from app.ui.remote_data_dialog import RemoteDataDialog

Signal = getattr(QtCore, "Signal", getattr(QtCore, "pyqtSignal"))
Slot = getattr(QtCore, "Slot", getattr(QtCore, "pyqtSlot"))


class StreamingSearchWorker(QtCore.QObject):
    """Test double that mimics the threaded worker with incremental updates."""

    started = Signal()
    record_found = Signal(object)
    finished = Signal(list)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, service: TrackingRemoteService) -> None:
        super().__init__()
        self._service = service
        self._cancelled = False

    @Slot(str, dict, bool)
    def run(self, provider: str, query: dict[str, Any], include_imaging: bool) -> None:
        self.started.emit()
        try:
            results = self._service.search(
                provider,
                query,
                include_imaging=include_imaging,
            )
        except Exception as exc:  # pragma: no cover - defensive path
            self.failed.emit(str(exc))
            return
        collected: list[RemoteRecord] = []
        for record in results:
            if self._cancelled:
                self.cancelled.emit()
                return
            collected.append(record)
            self.record_found.emit(record)
            QtCore.QThread.msleep(25)
        self.finished.emit(collected)

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True


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
        if not self.stub_records:
            return []
        results = list(self.stub_records)
        self.stub_records.clear()
        return results


def _ensure_app() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def _wait_for(condition: Callable[[], bool], timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QtWidgets.QApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    QtWidgets.QApplication.processEvents()
    return bool(condition())


def test_dialog_initialises_without_missing_slots() -> None:
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
    assert not dialog.progress_label.isVisible()
    assert not dialog.download_button.isEnabled()

    # Trigger provider refresh to ensure the slot updates hints/placeholder.
    dialog._on_provider_changed()
    assert "Solar system" in dialog.search_edit.placeholderText()

    # Clean up the dialog explicitly for Qt stability in headless tests.
    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_empty_search_does_not_hit_service() -> None:
    app = _ensure_app()
    service = TrackingRemoteService()
    ingest = IngestServiceStub()

    dialog = RemoteDataDialog(
        None,
        remote_service=service,
        ingest_service=ingest,
    )

    dialog.search_edit.setText("   ")
    dialog._on_search()

    assert service.calls == []
    assert "Provide provider-specific" in dialog.status_label.text()
    assert not dialog.progress_label.isVisible()

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_example_selection_runs_search() -> None:
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

    dialog._search_worker_factory = lambda: StreamingSearchWorker(service)

    provider_index = dialog.provider_combo.findText(RemoteDataService.PROVIDER_MAST)
    dialog.provider_combo.setCurrentIndex(provider_index)

    assert dialog.example_combo.isEnabled()
    assert dialog.example_combo.count() > 1

    dialog._on_example_selected(1)

    assert _wait_for(lambda: bool(service.calls)), "Search should be scheduled"
    assert _wait_for(lambda: dialog.progress_label.isVisible())
    assert _wait_for(lambda: dialog.results.rowCount() >= 1)
    provider, query, include_imaging = service.calls[0]
    assert provider == RemoteDataService.PROVIDER_MAST
    assert query.get("target_name")
    assert dialog.search_edit.text() == query["target_name"]
    assert include_imaging is False
    assert _wait_for(lambda: not dialog.progress_label.isVisible())
    assert dialog.search_button.isEnabled()

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_include_imaging_toggle_passes_flag() -> None:
    app = _ensure_app()
    service = TrackingRemoteService()
    ingest = IngestServiceStub()

    dialog = RemoteDataDialog(
        None,
        remote_service=service,
        ingest_service=ingest,
    )

    dialog._search_worker_factory = lambda: StreamingSearchWorker(service)

    provider_index = dialog.provider_combo.findText(RemoteDataService.PROVIDER_MAST)
    dialog.provider_combo.setCurrentIndex(provider_index)

    assert dialog.include_imaging_checkbox.isVisible()
    dialog.include_imaging_checkbox.setChecked(True)

    dialog.search_edit.setText("WASP-39 b")
    dialog._on_search()

    assert _wait_for(lambda: bool(service.calls)), "Search should record include_imaging flag"
    _, _, include_imaging = service.calls[-1]
    assert include_imaging is True
    assert _wait_for(lambda: not dialog.progress_label.isVisible())

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_search_streams_results_without_blocking_ui() -> None:
    app = _ensure_app()
    service = TrackingRemoteService()
    ingest = IngestServiceStub()

    record1 = RemoteRecord(
        provider=RemoteDataService.PROVIDER_MAST,
        identifier="obsid-1",
        title="First",
        download_url="mast:first.fits",
        metadata={},
        units={},
    )
    record2 = RemoteRecord(
        provider=RemoteDataService.PROVIDER_MAST,
        identifier="obsid-2",
        title="Second",
        download_url="mast:second.fits",
        metadata={},
        units={},
    )
    service.queue_record(record1)
    service.queue_record(record2)

    dialog = RemoteDataDialog(
        None,
        remote_service=service,
        ingest_service=ingest,
    )
    dialog._search_worker_factory = lambda: StreamingSearchWorker(service)

    provider_index = dialog.provider_combo.findText(RemoteDataService.PROVIDER_MAST)
    dialog.provider_combo.setCurrentIndex(provider_index)
    dialog.search_edit.setText("stream test")
    dialog._on_search()

    assert _wait_for(lambda: dialog.results.rowCount() >= 1)
    assert dialog.progress_label.isVisible()
    assert not dialog.search_button.isEnabled()
    assert _wait_for(lambda: dialog.results.rowCount() == 2)
    assert _wait_for(lambda: not dialog.progress_label.isVisible())
    assert dialog.search_button.isEnabled()

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_results_table_displays_extended_columns_and_preview() -> None:
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

    dialog._search_worker_factory = lambda: StreamingSearchWorker(service)

    provider_index = dialog.provider_combo.findText(RemoteDataService.PROVIDER_MAST)
    dialog.provider_combo.setCurrentIndex(provider_index)
    dialog.search_edit.setText("WASP-96 b")
    dialog._on_search()

    assert _wait_for(lambda: dialog.results.rowCount() == 1)
    assert _wait_for(lambda: not dialog.progress_label.isVisible())

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

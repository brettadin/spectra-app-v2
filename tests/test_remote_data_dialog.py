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

    assert dialog.provider_combo.count() == 2
    assert "Catalogue" in dialog.windowTitle() or dialog.windowTitle() == "Remote Data"

    # Switch providers to ensure the slot exists and updates hints/placeholder.
    dialog.provider_combo.setCurrentIndex(1)
    assert "JWST" in dialog.search_edit.placeholderText()

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


class IngestServiceStub:
    """Minimal stub mimicking the ingest service used by the dialog."""

    def ingest(self, path: Path) -> Any:  # pragma: no cover - not exercised in this smoke test
        raise RuntimeError(f"ingest not expected in dialog smoke test for {path}")

"""UI smoke tests for the Remote Data dialog."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, List

import pytest

from app.qt_compat import get_qt
from app.services import LocalStore, RemoteDataService

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
        self.search_calls: int = 0
        self.last_provider: str | None = None
        self.last_query: dict[str, object] | None = None

    def providers(self) -> List[str]:
        return list(self._providers)

    def unavailable_providers(self) -> dict[str, str]:
        return {}

    def search(self, provider: str, query: dict[str, object]):
        self.search_calls += 1
        self.last_provider = provider
        self.last_query = dict(query)
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


def test_mast_blank_query_surfaces_validation(monkeypatch: Any) -> None:
    app = _ensure_app()
    ingest = IngestServiceStub()
    remote = StubRemoteService()
    dialog = RemoteDataDialog(
        None,
        remote_service=remote,
        ingest_service=ingest,
    )

    index = dialog.provider_combo.findText(RemoteDataService.PROVIDER_MAST)
    dialog.provider_combo.setCurrentIndex(index)
    dialog.search_edit.setText("   ")
    dialog.search_button.click()
    app.processEvents()

    assert remote.search_calls == 0
    assert "MAST searches require" in dialog.status_label.text()

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_nist_blank_query_surfaces_validation(monkeypatch: Any) -> None:
    app = _ensure_app()
    ingest = IngestServiceStub()
    remote = StubRemoteService()
    dialog = RemoteDataDialog(
        None,
        remote_service=remote,
        ingest_service=ingest,
    )

    index = dialog.provider_combo.findText(RemoteDataService.PROVIDER_NIST)
    dialog.provider_combo.setCurrentIndex(index)
    dialog.search_edit.clear()
    dialog.search_button.click()
    app.processEvents()

    assert remote.search_calls == 0
    assert "NIST ASD searches require" in dialog.status_label.text()

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_mast_supported_filters_route_to_service(monkeypatch: Any) -> None:
    app = _ensure_app()
    ingest = IngestServiceStub()
    remote = StubRemoteService()
    dialog = RemoteDataDialog(
        None,
        remote_service=remote,
        ingest_service=ingest,
    )

    index = dialog.provider_combo.findText(RemoteDataService.PROVIDER_MAST)
    dialog.provider_combo.setCurrentIndex(index)
    dialog.search_edit.setText("instrument_name=NIRSpec, s_ra=123.4, s_dec=-45.6, radius=0.2")
    dialog._on_search()

    assert remote.search_calls == 1
    assert remote.last_provider == RemoteDataService.PROVIDER_MAST
    assert remote.last_query is not None
    assert remote.last_query.get("instrument_name") == "NIRSpec"
    assert remote.last_query.get("s_ra") == pytest.approx(123.4)
    assert remote.last_query.get("s_dec") == pytest.approx(-45.6)
    assert remote.last_query.get("radius") == pytest.approx(0.2)
    assert dialog.status_label.text().startswith("0 result(s) fetched from MAST")

    dialog.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


class IngestServiceStub:
    """Minimal stub mimicking the ingest service used by the dialog."""

    def ingest(self, path: Path) -> Any:  # pragma: no cover - not exercised in this smoke test
        raise RuntimeError(f"ingest not expected in dialog smoke test for {path}")

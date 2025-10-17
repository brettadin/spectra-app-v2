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

    def providers(self) -> List[str]:
        return list(self._providers)

    def unavailable_providers(self) -> dict[str, str]:
        return {}


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


class IngestServiceStub:
    """Minimal stub mimicking the ingest service used by the dialog."""

    def ingest(self, path: Path) -> Any:  # pragma: no cover - not exercised in this smoke test
        raise RuntimeError(f"ingest not expected in dialog smoke test for {path}")

"""Regression coverage for the remote data discovery dialog."""

from __future__ import annotations

import os
from typing import Any

import pytest

try:  # pragma: no cover - optional dependency guard
    from app.services import RemoteDataService
    from app.ui.remote_data_dialog import RemoteDataDialog
    from app.qt_compat import get_qt
except ImportError as exc:  # pragma: no cover - exercised via skip path
    RemoteDataDialog = None  # type: ignore[assignment]
    RemoteDataService = None  # type: ignore[assignment]
    _qt_import_error = exc
    QtWidgets = None  # type: ignore[assignment]
else:  # pragma: no cover - covered when Qt stack is present
    _qt_import_error = None
    QtCore, QtGui, QtWidgets, _ = get_qt()


def _ensure_app() -> "QtWidgets.QApplication":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.mark.skipif(RemoteDataDialog is None or QtWidgets is None, reason="Qt stack unavailable")
def test_remote_dialog_translates_mast_search() -> None:
    app = _ensure_app()

    class DummyRemoteService:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, Any]]] = []

        def providers(self) -> list[str]:
            return [RemoteDataService.PROVIDER_NIST, RemoteDataService.PROVIDER_MAST]

        def unavailable_providers(self) -> dict[str, str]:
            return {}

        def search(self, provider: str, query: dict[str, Any]):
            self.calls.append((provider, query))
            return []

        def download(self, record):  # pragma: no cover - dialog test does not download
            raise AssertionError("download should not be invoked during search")

    class DummyIngestService:
        def ingest(self, path):  # pragma: no cover - dialog test does not ingest
            raise AssertionError("ingest should not be invoked during search")

    remote = DummyRemoteService()
    dialog = RemoteDataDialog(None, remote_service=remote, ingest_service=DummyIngestService())

    try:
        index = dialog.provider_combo.findText(RemoteDataService.PROVIDER_MAST)
        assert index != -1
        dialog.provider_combo.setCurrentIndex(index)
        dialog.search_edit.setText("WASP-96 b")

        dialog._on_search()
        app.processEvents()

        assert remote.calls, "search should invoke the remote service"
        provider, query = remote.calls[-1]
        assert provider == RemoteDataService.PROVIDER_MAST
        assert query == {"target_name": "WASP-96 b"}
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()

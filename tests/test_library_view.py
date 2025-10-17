from __future__ import annotations

import os
from pathlib import Path

import pytest

try:
    from app import main as main_mod
    from app.main import SpectraMainWindow
    from app.qt_compat import get_qt
    from app.services import KnowledgeLogService, LocalStore
except ImportError as exc:  # pragma: no cover - optional on headless CI
    SpectraMainWindow = None  # type: ignore[assignment]
    main_mod = None  # type: ignore[assignment]
    _qt_import_error = exc
    QtCore = QtGui = QtWidgets = None  # type: ignore[assignment]
    KnowledgeLogService = LocalStore = None  # type: ignore[assignment]
else:  # pragma: no cover - exercised via regression test
    _qt_import_error = None
    QtCore, QtGui, QtWidgets, _ = get_qt()


def _ensure_app() -> QtWidgets.QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def test_library_view_populates_and_summarises_remote_history(tmp_path, monkeypatch):
    if (
        SpectraMainWindow is None
        or QtWidgets is None
        or KnowledgeLogService is None
        or LocalStore is None
        or main_mod is None
    ):
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    app = _ensure_app()

    empty_samples = tmp_path / "samples"
    empty_samples.mkdir()
    monkeypatch.setattr(main_mod, "SAMPLES_DIR", empty_samples)

    log_path = tmp_path / "log.md"
    knowledge_log = KnowledgeLogService(log_path=log_path)

    window = SpectraMainWindow(knowledge_log_service=knowledge_log)
    try:
        window.store = LocalStore(base_dir=tmp_path / "store")
        window.ingest_service.store = window.store
        window._refresh_library_view()
        app.processEvents()

        assert window.library_view is not None
        assert window.library_view.headerItem().text(1) == "Origin"
        assert window.library_view.topLevelItemCount() == 1
        placeholder = window.library_view.topLevelItem(0)
        assert "No cached files" in placeholder.text(0)

        sample = Path(__file__).resolve().parent / "data" / "mini.csv"
        window._ingest_path(sample)
        app.processEvents()
        window._refresh_library_view()

        items = [
            [window.library_view.topLevelItem(index).text(col) for col in range(window.library_view.columnCount())]
            for index in range(window.library_view.topLevelItemCount())
        ]
        assert any("mini.csv" in row[0] for row in items)
        assert any(row[1] == "Local import" for row in items)

        import_entries = knowledge_log.load_entries(component="Import")
        assert import_entries == []

        remote_payload = {
            "provider": "Test Provider",
            "uri": "https://example.test/data",  # nosec - test fixture
            "identifier": "ABC123",
        }
        remote_record = window.store.record(
            sample,
            x_unit="nm",
            y_unit="absorbance",
            source={"remote": remote_payload},
            alias="remote.csv",
        )
        remote_spectrum = window.ingest_service.ingest(Path(remote_record["stored_path"]))
        assert remote_spectrum.metadata.get("cache_record", {}).get("source", {}).get("remote")

        summary_info = window._record_remote_history_event(remote_spectrum)
        assert summary_info["provider"] == "Test Provider"

        window._refresh_library_view()
        app.processEvents()

        entries = knowledge_log.load_entries(component="Remote Import")
        assert entries
        for entry in entries:
            assert not any(ref.startswith("http") for ref in entry.references)
            assert all(len(ref) < 60 for ref in entry.references)
            assert "Test Provider" in entry.summary

        library_entries = window.store.list_entries()
        assert library_entries[remote_record["sha256"]]["source"]["remote"]["provider"] == "Test Provider"

        has_remote_origin = False
        for index in range(window.library_view.topLevelItemCount()):
            item = window.library_view.topLevelItem(index)
            if item.text(0) == "remote.csv":
                has_remote_origin = item.text(1).startswith("Test Provider")
                break
        assert has_remote_origin
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

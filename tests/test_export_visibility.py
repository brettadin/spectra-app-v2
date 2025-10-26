"""Tests for export behaviour tied to dataset visibility."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

try:
    from app.main import SpectraMainWindow
    from app.qt_compat import get_qt
except ImportError as exc:  # pragma: no cover - optional on headless CI
    SpectraMainWindow = None  # type: ignore[assignment]
    _qt_import_error = exc
    QtCore = QtWidgets = None  # type: ignore[assignment]
else:  # pragma: no cover - exercised when Qt bindings are available
    _qt_import_error = None
    QtCore, QtGui, QtWidgets, _ = get_qt()

from app.services import KnowledgeLogService


def _ensure_app() -> "QtWidgets.QApplication":  # type: ignore[name-defined]
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance()  # type: ignore[attr-defined]
    if app is None:
        app = QtWidgets.QApplication([])  # type: ignore[call-arg]
    return app


@pytest.mark.skipif(SpectraMainWindow is None, reason="Qt stack unavailable")
def test_export_skips_hidden_spectra(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = _ensure_app()

    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    try:
        app.processEvents()

        first_csv = tmp_path / "first.csv"
        first_csv.write_text("wavelength_nm,absorbance\n500,0.1\n510,0.2\n", encoding="utf-8")
        second_csv = tmp_path / "second.csv"
        second_csv.write_text("wavelength_nm,absorbance\n520,0.3\n530,0.4\n", encoding="utf-8")

        window._ingest_path(first_csv)
        window._ingest_path(second_csv)
        app.processEvents()

        spectra = window.overlay_service.list()
        assert len(spectra) == 2

        hidden_spec = spectra[0]
        alias_item = window._dataset_items[hidden_spec.id]
        visible_index = alias_item.index().siblingAtColumn(1)
        visible_item = window.dataset_model.itemFromIndex(visible_index)
        assert visible_item is not None
        visible_item.setCheckState(QtCore.Qt.CheckState.Unchecked)
        app.processEvents()

        target_manifest = tmp_path / "bundle" / "manifest.json"
        monkeypatch.setattr(
            QtWidgets.QFileDialog,
            "getSaveFileName",
            lambda *args, **kwargs: (str(target_manifest), "JSON (*.json)"),
        )

        captured: dict[str, object] = {}

        import app.main as main_module

        class _AcceptDialog:
            def __init__(self, *args, **kwargs) -> None:
                pass

            def exec(self) -> int:
                return QtWidgets.QDialog.DialogCode.Accepted

            def result(self):  # type: ignore[override]
                from app.ui.export_center_dialog import ExportCenterOptions

                return ExportCenterOptions(
                    manifest=True,
                    wide_csv=False,
                    composite_csv=False,
                    plot_png=False,
                    plot_svg=False,
                    plot_csv=False,
                )

        monkeypatch.setattr(main_module, "ExportCenterDialog", _AcceptDialog)

        def _fake_export_bundle(spectra_arg, manifest_path, **kwargs):
            ids = [spec.id for spec in spectra_arg]
            captured["ids"] = ids
            manifest = {"sources": [{"id": sid} for sid in ids]}
            manifest_path = Path(manifest_path)
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            csv_path = manifest_path.with_suffix(".csv")
            csv_path.write_text("id\n", encoding="utf-8")
            png_path = manifest_path.with_suffix(".png")
            png_path.write_bytes(b"PNG")
            log_path = manifest_path.with_suffix(".log")
            log_path.write_text("log\n", encoding="utf-8")
            return {
                "manifest": manifest,
                "manifest_path": manifest_path,
                "csv_path": csv_path,
                "png_path": png_path,
                "log_path": log_path,
                "spectra_dir": None,
                "sources_dir": None,
            }

        monkeypatch.setattr(window.provenance_service, "export_bundle", _fake_export_bundle)

        window.export_center()
        app.processEvents()

        expected_ids = [spec.id for spec in window.overlay_service.list() if window._visibility.get(spec.id, True)]
        assert captured["ids"] == expected_ids

        manifest_text = target_manifest.read_text(encoding="utf-8")
        manifest_data = json.loads(manifest_text)
        assert len(manifest_data["sources"]) == len(expected_ids) == 1
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

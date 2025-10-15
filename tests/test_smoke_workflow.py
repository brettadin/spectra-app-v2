from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

try:
    from app.main import SpectraMainWindow
    from app.qt_compat import get_qt
except ImportError as exc:  # pragma: no cover - optional on headless CI
    SpectraMainWindow = None  # type: ignore[assignment]
    _qt_import_error = exc
    QtCore = QtGui = QtWidgets = None  # type: ignore[assignment]
else:  # pragma: no cover - exercised via smoke test
    _qt_import_error = None
    QtCore, QtGui, QtWidgets, _ = get_qt()

from app.services import DataIngestService, ProvenanceService, UnitsService

def _ensure_app() -> QtWidgets.QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def test_smoke_ingest_toggle_and_export(tmp_path: Path, mini_fits: Path) -> None:
    """Exercise the core happy path: launch shell, ingest, convert units, export manifest."""

    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    pg = pytest.importorskip("pyqtgraph")

    app = _ensure_app()
    window = SpectraMainWindow()
    try:
        assert window.windowTitle().startswith("Spectra")
        docs_tab_index = window.inspector_tabs.indexOf(window.tab_docs)
        assert docs_tab_index != -1
        window.inspector_tabs.setCurrentIndex(docs_tab_index)
        app.processEvents()
        if window.docs_list.count():
            assert window.docs_list.currentRow() == 0
            assert window.doc_viewer.toPlainText().strip()

        reference_index = window.inspector_tabs.indexOf(window.tab_reference)
        assert reference_index != -1
        window.inspector_tabs.setCurrentIndex(reference_index)
        app.processEvents()
        assert window.reference_dataset_combo.count() >= 3
        assert isinstance(window.reference_plot, pg.PlotWidget)
        window.reference_dataset_combo.setCurrentIndex(0)
        app.processEvents()
        assert window.reference_table.rowCount() > 0
        hydrogen_markers = [
            item
            for item in window.reference_plot.getPlotItem().items
            if isinstance(item, pg.InfiniteLine)
        ]
        assert hydrogen_markers, "Expected vertical markers for hydrogen lines"

        window.reference_overlay_toggle.setChecked(True)
        app.processEvents()
        assert window._reference_overlay_key is not None
        assert window._reference_overlay_key.startswith("reference::")
        assert window._reference_overlay_key in window.plot._traces

        window.reference_dataset_combo.setCurrentIndex(1)
        app.processEvents()
        ir_regions = [
            item
            for item in window.reference_plot.getPlotItem().items
            if isinstance(item, pg.LinearRegionItem)
        ]
        assert ir_regions, "Expected shaded regions for IR functional groups"
        assert window._reference_overlay_key in window.plot._traces

        placeholder_index = next(
            idx
            for idx in range(window.reference_dataset_combo.count())
            if window.reference_dataset_combo.itemData(idx)[0] == "line_shapes"
        )
        window.reference_dataset_combo.setCurrentIndex(placeholder_index)
        app.processEvents()
        assert window.reference_overlay_toggle.isEnabled() is False
        assert window._reference_overlay_key is None

        jwst_index = next(
            idx
            for idx in range(window.reference_dataset_combo.count())
            if window.reference_dataset_combo.itemData(idx)[0] == "jwst"
        )
        window.reference_dataset_combo.setCurrentIndex(jwst_index)
        app.processEvents()
        data_items = window.reference_plot.listDataItems()
        assert any(isinstance(item, pg.PlotDataItem) for item in data_items)
        error_items = [
            item
            for item in window.reference_plot.getPlotItem().items
            if isinstance(item, pg.ErrorBarItem)
        ]
        assert error_items, "Expected error bars for JWST spectra"
        assert window._reference_overlay_key in window.plot._traces

        window.reference_overlay_toggle.setChecked(False)
        app.processEvents()
        assert window._reference_overlay_key is None
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

    units = UnitsService()
    ingest = DataIngestService(units)
    provenance = ProvenanceService(app_version="0.2-smoke")

    csv_spec = ingest.ingest(Path("samples/sample_spectrum.csv"))
    fits_spec = ingest.ingest(mini_fits)

    supported = ingest.supported_extensions()
    assert supported.get(".csv") == "CsvImporter"
    assert supported.get(".fits") == "FitsImporter"

    angstrom_view = csv_spec.view(units, "angstrom", "transmittance")
    assert np.allclose(angstrom_view["x"], csv_spec.x * 10.0)
    assert np.allclose(angstrom_view["y"], np.power(10.0, -csv_spec.y))

    roundtrip_x, roundtrip_y, meta = units.to_canonical(
        angstrom_view["x"], angstrom_view["y"], "angstrom", "transmittance"
    )
    assert np.allclose(roundtrip_x, csv_spec.x)
    assert np.allclose(roundtrip_y, csv_spec.y)
    assert meta["source_units"] == {"x": "angstrom", "y": "transmittance"}

    bundle_dir = tmp_path / "export"
    manifest_path = bundle_dir / "manifest.json"
    png_bytes = b"\x89PNG\r\n"

    bundle = provenance.export_bundle(
        [csv_spec, fits_spec], manifest_path, png_writer=lambda path: path.write_bytes(png_bytes)
    )

    assert bundle["manifest_path"].exists()
    manifest = bundle["manifest"]
    importer_ids = {entry["metadata"]["ingest"]["importer"] for entry in manifest["sources"]}
    assert {"CsvImporter", "FitsImporter"}.issubset(importer_ids)

    csv_contents = bundle["csv_path"].read_text(encoding="utf-8")
    assert "wavelength_nm" in csv_contents
    assert str(csv_spec.x[0]) in csv_contents

    assert bundle["png_path"].read_bytes() == png_bytes


def test_show_documentation_no_attribute_error() -> None:
    """Opening the documentation view should not raise AttributeError during startup."""

    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    app = _ensure_app()
    window = SpectraMainWindow()
    try:
        window.show_documentation()
        app.processEvents()
        docs_index = window.inspector_tabs.indexOf(window.tab_docs)
        assert docs_index != -1
        assert window.inspector_tabs.currentIndex() == docs_index
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_docs_tab_auto_loads_first_entry_without_error() -> None:
    """Switching to the Docs tab should auto-load the first entry without exploding."""

    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    app = _ensure_app()
    window = SpectraMainWindow()
    try:
        docs_index = window.inspector_tabs.indexOf(window.tab_docs)
        assert docs_index != -1
        window.inspector_tabs.setCurrentIndex(docs_index)
        app.processEvents()

        if window.docs_list.count():
            # The first entry should be selected automatically and rendered without error.
            assert window.docs_list.currentRow() == 0
            assert window.doc_viewer.toPlainText().strip()
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

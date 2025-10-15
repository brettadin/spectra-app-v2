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

    app = _ensure_app()
    window = SpectraMainWindow()
    try:
        assert window.windowTitle().startswith("Spectra")
        docs_tab_index = window.inspector_tabs.indexOf(window.tab_docs)
        assert docs_tab_index != -1
        if window.docs_list.count():
            window.docs_list.setCurrentRow(0)
            app.processEvents()
            assert window.doc_viewer.toPlainText().strip()

        reference_index = window.inspector_tabs.indexOf(window.tab_reference)
        assert reference_index != -1
        window.inspector_tabs.setCurrentIndex(reference_index)
        app.processEvents()
        assert window.reference_dataset_combo.count() >= 3
        window.reference_dataset_combo.setCurrentIndex(0)
        app.processEvents()
        assert window.reference_table.rowCount() > 0
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

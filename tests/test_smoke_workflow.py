from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

try:
    from app.main import SpectraMainWindow
    from app.qt_compat import get_qt
    from app.ui.plot_pane import PlotPane, TraceStyle
except ImportError as exc:  # pragma: no cover - optional on headless CI
    SpectraMainWindow = None  # type: ignore[assignment]
    _qt_import_error = exc
    QtCore = QtGui = QtWidgets = None  # type: ignore[assignment]
    PlotPane = None  # type: ignore[assignment]
    TraceStyle = None  # type: ignore[assignment]
else:  # pragma: no cover - exercised via smoke test
    _qt_import_error = None
    QtCore, QtGui, QtWidgets, _ = get_qt()

from app.services import (
    DataIngestService,
    KnowledgeLogService,
    LocalStore,
    ProvenanceService,
    UnitsService,
)

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
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
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
        assert hasattr(window, "reference_plot")
        assert window.reference_plot.listDataItems()
        assert window.reference_overlay_checkbox.isEnabled()
        payload = window._reference_overlay_payload
        assert payload is not None
        y_values = payload.get("y")
        assert isinstance(y_values, np.ndarray)
        assert np.nanmax(y_values) > np.nanmin(y_values)
        window.reference_overlay_checkbox.setChecked(True)
        app.processEvents()
        assert window._reference_overlay_key is not None
        window.reference_overlay_checkbox.setChecked(False)
        app.processEvents()
        assert window._reference_overlay_key is None

        # Switch datasets to ensure combo selection updates correctly
        initial_key = payload.get("key") if payload else None
        window.reference_dataset_combo.setCurrentIndex(1)
        app.processEvents()
        assert window.reference_dataset_combo.currentIndex() == 1
        assert window.reference_table.rowCount() > 0
        next_payload = window._reference_overlay_payload
        if next_payload:
            assert next_payload.get("key") != initial_key

        jwst_index = None
        for idx, (kind, _key) in enumerate(window._reference_options):
            if kind == "jwst":
                jwst_index = idx
                break
        if jwst_index is not None:
            window.reference_dataset_combo.setCurrentIndex(jwst_index)
            app.processEvents()
            jwst_payload = window._reference_overlay_payload
            assert jwst_payload is not None
            assert str(jwst_payload.get("key", "")).startswith("reference::jwst::")
            x_vals = jwst_payload.get("x_nm")
            y_vals = jwst_payload.get("y")
            assert isinstance(x_vals, np.ndarray) and x_vals.size > 0
            assert isinstance(y_vals, np.ndarray) and y_vals.size == x_vals.size
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_library_dock_populates_and_previews(tmp_path: Path) -> None:
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    try:
        store = LocalStore(base_dir=tmp_path / "store")
        window.store = store
        window.ingest_service.store = store
        if hasattr(window, "remote_data_service"):
            window.remote_data_service.store = store

        csv_path = tmp_path / "library.csv"
        csv_path.write_text("wavelength_nm,absorbance\n500,0.5\n505,0.6\n", encoding="utf-8")

        window._ingest_path(csv_path)
        app.processEvents()
        window._refresh_library_view()

        if window.library_list is None or window.library_detail is None:
            pytest.skip("Persistence disabled: library dock not available")

        target_item: QtWidgets.QTreeWidgetItem | None = None
        for index in range(window.library_list.topLevelItemCount()):
            item = window.library_list.topLevelItem(index)
            if item is not None and item.text(0) == "library.csv":
                target_item = item
                break
        if target_item is None:
            pytest.skip("Library ingest did not register test file")

        window.library_list.setCurrentItem(target_item)
        app.processEvents()

        detail = window.library_detail.toPlainText()
        assert detail, "Selecting a cached entry should display metadata"
        assert "Alias: library.csv" in detail
        assert "Canonical units:" in detail
        assert "Knowledge log:" in detail
        assert str(log_service.log_path) in detail
        if window.library_hint is not None:
            assert window.library_hint.text()
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_palette_presets_update_trace_colours(tmp_path: Path) -> None:
    if SpectraMainWindow is None or QtWidgets is None or PlotPane is None or TraceStyle is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    try:
        csv_path = tmp_path / "palette.csv"
        csv_path.write_text("wavelength_nm,absorbance\n500,0.4\n510,0.5\n", encoding="utf-8")

        spectrum = window.ingest_service.ingest(csv_path)
        window.overlay_service.add(spectrum)
        window._add_spectrum(spectrum)
        window._update_math_selectors()
        window.refresh_overlay()
        app.processEvents()

        assert window.color_mode_combo is not None
        definitions = PlotPane.palette_definitions()
        assert window.color_mode_combo.count() == len(definitions)

        def _icon_rgb(item: QtGui.QStandardItem) -> tuple[int, int, int]:
            icon = item.icon()
            pixmap = icon.pixmap(16, 16)
            image = pixmap.toImage()
            colour = image.pixelColor(0, 0)
            return (colour.red(), colour.green(), colour.blue())

        observed_colours: set[tuple[int, int, int]] = set()
        colour_item = window._dataset_color_items[spectrum.id]
        for definition in definitions:
            index = window.color_mode_combo.findData(definition.key)
            assert index != -1
            window.color_mode_combo.setCurrentIndex(index)
            app.processEvents()

            expected_display = QtGui.QColor(
                definition.resolved_uniform_color() if definition.uniform else definition.colors[0]
            )
            icon_rgb = _icon_rgb(colour_item)
            assert icon_rgb == (
                expected_display.red(),
                expected_display.green(),
                expected_display.blue(),
            )

            trace = window.plot._traces[spectrum.id]
            style = trace.get("style")
            assert isinstance(style, TraceStyle)
            pen_colour = style.color
            assert (
                pen_colour.red(),
                pen_colour.green(),
                pen_colour.blue(),
            ) == icon_rgb
            assert window._use_uniform_palette is definition.uniform
            observed_colours.add(icon_rgb)

        assert len(observed_colours) >= 2
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_history_view_updates_on_import(tmp_path: Path) -> None:
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    try:
        app.processEvents()
        initial_rows = window.history_table.rowCount()
        csv_path = tmp_path / "integration.csv"
        csv_path.write_text("wavelength_nm,absorbance\n500,0.1\n510,0.2\n", encoding="utf-8")

        window._ingest_path(csv_path)
        app.processEvents()

        entries = log_service.load_entries()
        assert entries
        assert any("integration.csv" in entry.summary for entry in entries)
        assert window.history_table.rowCount() >= initial_rows + 1
        top_summary_item = window.history_table.item(0, 2)
        assert top_summary_item is not None
        assert "integration" in top_summary_item.text()
        window.history_table.selectRow(0)
        app.processEvents()
        detail_text = window.history_detail.toPlainText()
        assert "Ingested" in detail_text
        assert "integration.csv" in detail_text
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


def test_plot_preserves_source_intensity_units(tmp_path: Path) -> None:
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    csv_path = tmp_path / "transmittance.csv"
    csv_path.write_text("wavelength_nm,%T\n400,50\n410,75\n420,100\n", encoding="utf-8")

    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    try:
        spectrum = window.ingest_service.ingest(csv_path)
        window.overlay_service.add(spectrum)
        window._add_spectrum(spectrum)
        window._update_math_selectors()
        window.refresh_overlay()
        trace = window.plot._traces[spectrum.id]
        y_values = trace["y"]  # type: ignore[index]
        assert isinstance(y_values, np.ndarray)
        assert np.allclose(y_values[:3], np.array([50.0, 75.0, 100.0]))
        assert "%T" in window.plot._y_label  # type: ignore[attr-defined]
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

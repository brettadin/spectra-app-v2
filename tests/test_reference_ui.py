from __future__ import annotations

import os

import numpy as np
import pytest

try:
    from app.main import SpectraMainWindow
    from app.qt_compat import get_qt
except ImportError as exc:  # pragma: no cover - optional on headless CI
    SpectraMainWindow = None  # type: ignore[assignment]
    _qt_import_error = exc
    QtCore = QtGui = QtWidgets = None  # type: ignore[assignment]
else:  # pragma: no cover - exercised via regression test
    _qt_import_error = None
    QtCore, QtGui, QtWidgets, _ = get_qt()


def _ensure_app() -> QtWidgets.QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def test_reference_tab_builds_without_error() -> None:
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    pytest.importorskip("pyqtgraph")

    app = _ensure_app()
    window = SpectraMainWindow()
    try:
        reference_index = window.inspector_tabs.indexOf(window.tab_reference)
        assert reference_index != -1

        assert window.reference_tabs.count() >= 2
        assert window.nist_element_edit.placeholderText()

        axis = window.reference_plot.getPlotItem().getAxis("bottom")
        assert axis is not None

        label_text = ""
        if hasattr(axis, "labelText"):
            label_text = axis.labelText
        elif hasattr(axis, "label"):
            label = axis.label
            if hasattr(label, "text"):
                label_text = label.text
            elif hasattr(label, "toPlainText"):
                label_text = label.toPlainText()

        assert label_text
        assert "Wavelength" in label_text
        assert window.unit_combo.currentText() in label_text
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_reference_nist_fetch_populates_table(monkeypatch) -> None:
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    pytest.importorskip("pyqtgraph")

    app = _ensure_app()

    from app import main as main_module

    monkeypatch.setattr(main_module.nist_asd_service, "dependencies_available", lambda: True)

    sample_payload = {
        "lines": [
            {
                "wavelength_nm": 486.13,
                "observed_wavelength_nm": 486.13,
                "ritz_wavelength_nm": 486.128,
                "relative_intensity": 100.0,
                "relative_intensity_normalized": 1.0,
                "lower_level": "2s² 2p⁵",
                "upper_level": "2s² 2p⁴ 3s",
                "transition_type": "E1",
            }
        ],
        "meta": {
            "label": "Hydrogen I",
            "element_symbol": "H",
            "line_count": 1,
            "query": {
                "lower_wavelength": 400.0,
                "upper_wavelength": 700.0,
                "wavelength_unit": "nm",
                "wavelength_type": "vacuum",
            },
        },
    }

    sample_payload_two = {
        "lines": [
            {
                "wavelength_nm": 656.28,
                "observed_wavelength_nm": 656.28,
                "ritz_wavelength_nm": 656.281,
                "relative_intensity": 120.0,
                "relative_intensity_normalized": 1.0,
                "lower_level": "2p⁶",
                "upper_level": "2p⁵ 3s",
                "transition_type": "E1",
            }
        ],
        "meta": {
            "label": "Hydrogen I",
            "element_symbol": "H",
            "ion_stage": "I",
            "line_count": 1,
            "query": {
                "lower_wavelength": 600.0,
                "upper_wavelength": 700.0,
                "wavelength_unit": "nm",
                "wavelength_type": "vacuum",
            },
        },
    }

    payloads = iter([sample_payload, sample_payload_two])

    monkeypatch.setattr(
        main_module.nist_asd_service,
        "fetch_lines",
        lambda *_, **__: next(payloads),
    )

    window = SpectraMainWindow()
    try:
        window.nist_element_edit.setText("H")
        window.nist_lower_spin.setValue(400.0)
        window.nist_upper_spin.setValue(700.0)

        window._on_nist_fetch_clicked()
        app.processEvents()

        assert window.reference_table.rowCount() == 1
        assert window.reference_overlay_checkbox.isEnabled()

        payload = window._reference_overlay_payload
        assert isinstance(payload, dict)
        assert payload.get("kind") == "nist-multi"
        payload_map = payload.get("payloads")
        assert isinstance(payload_map, dict)
        assert len(payload_map) == 1
        first_payload = next(iter(payload_map.values()))
        assert first_payload["alias"].startswith("Reference –")
        assert first_payload["x_nm"].size > 0

        assert window.nist_collections_list.count() == 1
        assert "1 pinned set" in window.reference_status_label.text()

        window.nist_element_edit.setText("H")
        window.nist_lower_spin.setValue(600.0)
        window.nist_upper_spin.setValue(700.0)
        window._on_nist_fetch_clicked()
        app.processEvents()

        assert window.nist_collections_list.count() == 2
        assert "2 pinned set" in window.reference_status_label.text()

        window.nist_collections_list.setCurrentRow(0)
        app.processEvents()
        assert window.reference_table.rowCount() >= 1

        window.reference_overlay_checkbox.setChecked(True)
        app.processEvents()
        assert len(window._reference_overlay_key) == 2
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_ir_overlay_payload_includes_fill_and_labels() -> None:
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    pytest.importorskip("pyqtgraph")

    app = _ensure_app()
    window = SpectraMainWindow()
    try:
        sample = [{
            "wavenumber_cm_1_min": 1600.0,
            "wavenumber_cm_1_max": 1500.0,
            "group": "Carbonyl",
        }]
        payload = window._build_overlay_for_ir(sample)
        assert payload is not None
        assert payload["fill_color"]
        assert payload["fill_level"] == pytest.approx(payload["band_bounds"][0])
        labels = payload.get("labels")
        assert isinstance(labels, list)
        assert labels and labels[0]["text"] == "Carbonyl"
        assert labels[0]["centre_nm"] > 0

        x_values = payload["x_nm"]
        finite = x_values[np.isfinite(x_values)]
        assert finite.size >= 2
        diffs = np.diff(finite)
        assert np.all(diffs != 0.0)
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_ir_overlay_labels_stack_inside_band() -> None:
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    pytest.importorskip("pyqtgraph")

    app = _ensure_app()
    window = SpectraMainWindow()
    try:
        plot_item = window.plot._plot.getPlotItem()
        plot_item.setXRange(800, 1800)
        plot_item.setYRange(-1, 1)

        band_bottom, band_top = window._overlay_band_bounds()

        x_segments = np.array(
            [
                900.0,
                np.nextafter(900.0, 950.0),
                np.nextafter(950.0, 900.0),
                950.0,
                np.nan,
            ],
            dtype=float,
        )
        y_segments = np.array([band_bottom, band_top, band_top, band_bottom, np.nan], dtype=float)

        payload = {
            "key": "reference::ir_groups",
            "alias": "Reference – IR Functional Groups",
            "x_nm": x_segments,
            "y": y_segments,
            "color": "#6D597A",
            "width": 1.2,
            "fill_color": (109, 89, 122, 70),
            "fill_level": float(band_bottom),
            "band_bounds": (float(band_bottom), float(band_top)),
            "labels": [
                {"text": "A", "centre_nm": 910.0},
                {"text": "B", "centre_nm": 912.0},
                {"text": "C", "centre_nm": 950.0},
            ],
        }

        window._reference_overlay_payload = payload
        window.reference_overlay_checkbox.setChecked(True)
        window._apply_reference_overlay()
        app.processEvents()

        annotations = window._reference_overlay_annotations
        assert len(annotations) == 3

        ys = [item.pos().y() for item in annotations]
        assert all(band_bottom <= y <= band_top for y in ys)

        # Ensure stacked labels occupy distinct vertical slots to avoid overlap.
        unique_y = {round(y, 6) for y in ys}
        assert len(unique_y) == len(ys)
    finally:
        window._clear_reference_overlay()
        window.close()
        window.deleteLater()
        app.processEvents()


def test_line_shape_preview_populates_overlay_payload() -> None:
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    pytest.importorskip("pyqtgraph")

    app = _ensure_app()
    window = SpectraMainWindow()
    try:
        window.reference_tabs.setCurrentIndex(2)
        window._refresh_reference_view()
        app.processEvents()

        assert window.reference_table.rowCount() > 0
        window.reference_table.selectRow(0)
        app.processEvents()

        plot_items = window.reference_plot.getPlotItem().listDataItems()
        assert plot_items, "line-shape preview curve should be drawn"

        payload = window._reference_overlay_payload
        assert payload is not None
        assert str(payload.get("key", "")).startswith("reference::line_shape::")
        x_values = payload.get("x_nm")
        y_values = payload.get("y")
        assert isinstance(x_values, np.ndarray)
        assert isinstance(y_values, np.ndarray)
        assert x_values.size == y_values.size

        metadata = payload.get("metadata")
        assert isinstance(metadata, dict)
        assert metadata.get("model") in {"doppler_shift", "pressure_broadening", "stark_broadening"}

        assert window.reference_overlay_checkbox.isEnabled()
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_reference_overlay_toggle_preserves_payload_object() -> None:
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    pytest.importorskip("pyqtgraph")

    app = _ensure_app()
    window = SpectraMainWindow()
    try:
        band_bottom, band_top = window._overlay_band_bounds()
        payload = {
            "key": "reference::regression::toggle",
            "alias": "Reference – Toggle Regression",
            "x_nm": np.array([410.0, 410.0, 520.0, 520.0, np.nan], dtype=float),
            "y": np.array([band_bottom, band_top, band_top, band_bottom, np.nan], dtype=float),
            "color": "#4F6D7A",
            "width": 1.2,
            "fill_color": (79, 109, 122, 90),
            "fill_level": float(band_bottom),
            "band_bounds": (float(band_bottom), float(band_top)),
            "labels": [
                {"text": "Feature", "centre_nm": 465.0},
            ],
        }

        window._update_reference_overlay_state(payload)
        assert window._reference_overlay_payload is payload

        annotations_list = window._reference_overlay_annotations
        window.reference_overlay_checkbox.setChecked(True)
        app.processEvents()

        assert window._reference_overlay_payload is payload
        assert window._reference_overlay_annotations is annotations_list
        assert window._reference_overlay_annotations

        window.reference_overlay_checkbox.setChecked(False)
        app.processEvents()

        assert window._reference_overlay_payload is payload
        assert window._reference_overlay_annotations is annotations_list
        assert not window._reference_overlay_annotations
    finally:
        window._clear_reference_overlay()
        window.close()
        window.deleteLater()
        app.processEvents()

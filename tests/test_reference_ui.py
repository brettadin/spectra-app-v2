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
        index = window.reference_dataset_combo.findText("Line-shape Placeholders")
        assert index != -1
        window.reference_dataset_combo.setCurrentIndex(index)
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

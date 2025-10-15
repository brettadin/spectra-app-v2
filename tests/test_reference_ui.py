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

        x_segments = np.array([900, 900, 950, 950, np.nan], dtype=float)
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


def test_ir_overlay_realigns_with_view_range() -> None:
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
        payload = {
            "key": "reference::ir_groups",
            "alias": "Reference – IR Functional Groups",
            "x_nm": np.array([900, 900, 950, 950, np.nan], dtype=float),
            "y": np.array([band_bottom, band_top, band_top, band_bottom, np.nan], dtype=float),
            "color": "#6D597A",
            "width": 1.2,
            "fill_color": (109, 89, 122, 70),
            "fill_level": float(band_bottom),
            "band_bounds": (float(band_bottom), float(band_top)),
            "labels": [
                {"text": "A", "centre_nm": 905.0},
                {"text": "B", "centre_nm": 912.0},
                {"text": "C", "centre_nm": 950.0},
            ],
        }

        window._reference_overlay_payload = payload
        window.reference_overlay_checkbox.setChecked(True)
        window._apply_reference_overlay()
        app.processEvents()

        plot_item.setYRange(0, 5)
        app.processEvents()

        refreshed = window._reference_overlay_payload
        assert refreshed is not None

        new_bottom, new_top = window._overlay_band_bounds()
        assert refreshed["band_bounds"] == pytest.approx((new_bottom, new_top))

        y_values = refreshed.get("y")
        assert isinstance(y_values, np.ndarray)
        finite = y_values[np.isfinite(y_values)]
        assert finite.size
        assert np.isclose(np.nanmin(finite), new_bottom)
        assert np.isclose(np.nanmax(finite), new_top)

        for item in window._reference_overlay_annotations:
            y_pos = item.pos().y()
            assert new_bottom <= y_pos <= new_top
    finally:
        window._clear_reference_overlay()
        window.close()
        window.deleteLater()
        app.processEvents()

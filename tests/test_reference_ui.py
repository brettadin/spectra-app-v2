from __future__ import annotations

import os

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

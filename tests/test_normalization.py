"""Test normalization functionality."""
from pathlib import Path
import os

import pytest
import numpy as np

try:
    from app.main import SpectraMainWindow
    from app.qt_compat import get_qt
except ImportError as exc:
    SpectraMainWindow = None
    _qt_import_error = exc
    QtCore = QtGui = QtWidgets = None
else:
    _qt_import_error = None
    QtCore, QtGui, QtWidgets, _ = get_qt()

from app.services import KnowledgeLogService


def _ensure_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def test_normalization_max(tmp_path: Path) -> None:
    """Test Max normalization scales data to [0, 1] range."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Create test data with known max value using absorbance (no conversion)
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(
            "wavelength_nm,absorbance\n"
            "400,1.0\n"
            "450,5.0\n"  # Max value
            "500,2.0\n",
            encoding="utf-8"
        )
        
        # Set to Max normalization before ingesting
        window.norm_combo.setCurrentText("Max")
        app.processEvents()
        
        # Ingest the data
        window._ingest_path(csv_path)
        app.processEvents()
        
        # Get the spectrum from overlay
        specs = window.overlay_service.list()
        assert len(specs) == 1
        spec = specs[0]
        
        # Get the plotted y-data from the plot trace
        trace = window.plot._traces.get(spec.id)
        assert trace is not None
        y_plotted = trace["y"]
        
        # With Max normalization, max absolute value should be 1.0
        assert np.max(np.abs(y_plotted)) == pytest.approx(1.0, abs=1e-6)
        # Original max was 5.0, so values should be scaled by 1/5
        assert y_plotted[1] == pytest.approx(1.0, abs=1e-6)  # 5.0 / 5.0 = 1.0
        assert y_plotted[0] == pytest.approx(0.2, abs=1e-6)  # 1.0 / 5.0 = 0.2
        assert y_plotted[2] == pytest.approx(0.4, abs=1e-6)  # 2.0 / 5.0 = 0.4
        
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_normalization_area(tmp_path: Path) -> None:
    """Test Area normalization scales by integral."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Create test data
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(
            "wavelength_nm,absorbance\n"
            "400,2.0\n"
            "450,4.0\n"
            "500,2.0\n",
            encoding="utf-8"
        )
        
        # Set to Area normalization before ingesting
        window.norm_combo.setCurrentText("Area")
        app.processEvents()
        
        # Ingest the data
        window._ingest_path(csv_path)
        app.processEvents()
        
        # Get the spectrum
        specs = window.overlay_service.list()
        assert len(specs) == 1
        spec = specs[0]
        
        # Get the plotted y-data
        trace = window.plot._traces.get(spec.id)
        assert trace is not None
        y_plotted = trace["y"]
        
        # With Area normalization, the integral should be 1.0
        area = np.trapz(np.abs(y_plotted))
        assert area == pytest.approx(1.0, abs=1e-6)
        
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_normalization_none(tmp_path: Path) -> None:
    """Test None normalization keeps original data."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Create test data
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(
            "wavelength_nm,absorbance\n"
            "400,100.0\n"
            "450,200.0\n"
            "500,150.0\n",
            encoding="utf-8"
        )
        
        # Keep default "None" normalization
        assert window.norm_combo.currentText() == "None"
        
        # Ingest the data
        window._ingest_path(csv_path)
        app.processEvents()
        
        # Get the spectrum
        specs = window.overlay_service.list()
        assert len(specs) == 1
        spec = specs[0]
        
        # Get the plotted y-data
        trace = window.plot._traces.get(spec.id)
        assert trace is not None
        y_plotted = trace["y"]
        
        # With None normalization, values should be unchanged
        assert y_plotted[0] == pytest.approx(100.0, abs=1e-6)
        assert y_plotted[1] == pytest.approx(200.0, abs=1e-6)
        assert y_plotted[2] == pytest.approx(150.0, abs=1e-6)
        
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_normalization_change_updates_plot(tmp_path: Path) -> None:
    """Test changing normalization mode updates existing plots."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Create test data with simple evenly-spaced points
        csv_path = tmp_path / "test.csv"
        # Use simple data that won't get downsampled
        csv_path.write_text(
            "wavelength_nm,absorbance\n"
            "400,10.0\n"
            "500,20.0\n"
            "600,15.0\n",
            encoding="utf-8"
        )
        
        # Ingest with no normalization
        window._ingest_path(csv_path)
        app.processEvents()
        
        specs = window.overlay_service.list()
        spec = specs[0]
        
        # Check original spectrum data (stored in overlay service)
        assert spec.y[1] == pytest.approx(20.0, abs=1e-6)
        
        # Change to Max normalization
        window.norm_combo.setCurrentText("Max")
        app.processEvents()
        
        # Get updated trace - should be normalized
        trace = window.plot._traces.get(spec.id)
        y_normalized = trace["y"]
        
        # The trace data should now be normalized
        # Since original max was 20.0, all values divided by 20.0
        max_val = np.max(np.abs(y_normalized))
        assert max_val == pytest.approx(1.0, abs=1e-2)  # Allow for downsampling effects
        
        # But the original spectrum should still have original values
        specs = window.overlay_service.list()
        spec = specs[0]
        assert spec.y[1] == pytest.approx(20.0, abs=1e-6)  # Original data unchanged
        
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_normalization_multiple_spectra(tmp_path: Path) -> None:
    """Test normalization works correctly with multiple spectra."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Create two spectra with different scales
        csv1 = tmp_path / "test1.csv"
        csv1.write_text(
            "wavelength_nm,absorbance\n"
            "400,1.0\n"
            "450,2.0\n"
            "500,1.5\n",
            encoding="utf-8"
        )
        
        csv2 = tmp_path / "test2.csv"
        csv2.write_text(
            "wavelength_nm,absorbance\n"
            "400,100.0\n"
            "450,200.0\n"
            "500,150.0\n",
            encoding="utf-8"
        )
        
        # Set Max normalization
        window.norm_combo.setCurrentText("Max")
        app.processEvents()
        
        # Ingest both
        window._ingest_path(csv1)
        window._ingest_path(csv2)
        app.processEvents()
        
        specs = window.overlay_service.list()
        assert len(specs) == 2
        
        # Both should be normalized to max=1.0 independently
        for spec in specs:
            trace = window.plot._traces.get(spec.id)
            assert trace is not None
            y_data = trace["y"]
            assert np.max(np.abs(y_data)) == pytest.approx(1.0, abs=1e-6)
        
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

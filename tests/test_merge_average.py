"""Test multi-file upload and averaging functionality."""
from pathlib import Path
import os
from typing import Any, Dict, cast

import pytest
import numpy as np

try:
    from app.main import SpectraMainWindow
    from app.qt_compat import get_qt
except ImportError as exc:
    SpectraMainWindow = None
    _qt_import_error = exc
    QtCore = cast(Any, None)
    QtGui = cast(Any, None)
    QtWidgets = cast(Any, None)
else:
    _qt_import_error = None
    QtCore, QtGui, QtWidgets, _ = get_qt()

QtCore = cast(Any, QtCore)
QtGui = cast(Any, QtGui)
QtWidgets = cast(Any, QtWidgets)

from app.services import KnowledgeLogService, MathService, Spectrum, UnitsService


def _make_spectrum(name: str, x: np.ndarray, y: np.ndarray, *, metadata: dict | None = None) -> Spectrum:
    return Spectrum.create(name=name, x=x, y=y, x_unit="nm", y_unit="absorbance", metadata=metadata or {})


def _ensure_app() -> Any:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return cast(Any, app)


def test_math_service_average_two_spectra(tmp_path: Path) -> None:
    """Test averaging two spectra with same wavelength grid."""
    # Create two spectra with same x values
    x = np.array([400.0, 450.0, 500.0])
    y1 = np.array([1.0, 2.0, 3.0])
    y2 = np.array([3.0, 4.0, 5.0])
    
    spec1 = _make_spectrum(name="test1", x=x, y=y1)
    spec2 = _make_spectrum(name="test2", x=x, y=y2)
    
    math_service = MathService(UnitsService())
    result, metadata = math_service.average([spec1, spec2])
    
    # Average should be (y1 + y2) / 2
    expected_y = np.array([2.0, 3.0, 4.0])
    
    assert result.name == "Average of 2 spectra"
    assert len(result.x) == 3
    assert len(result.y) == 3
    assert np.allclose(result.y, expected_y)
    assert metadata['status'] == 'ok'
    assert metadata['count'] == 2


def test_math_service_average_different_grids(tmp_path: Path) -> None:
    """Test averaging spectra with different wavelength grids via interpolation."""
    # Spec1: coarse grid
    x1 = np.array([400.0, 500.0, 600.0])
    y1 = np.array([1.0, 2.0, 3.0])
    
    # Spec2: fine grid overlapping
    x2 = np.array([400.0, 425.0, 450.0, 475.0, 500.0, 525.0, 550.0, 575.0, 600.0])
    y2 = np.array([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0])
    
    spec1 = _make_spectrum(name="coarse", x=x1, y=y1)
    spec2 = _make_spectrum(name="fine", x=x2, y=y2)
    
    math_service = MathService(UnitsService())
    result, metadata = math_service.average([spec1, spec2])
    
    # Result should use the finer grid
    assert len(result.x) == len(x2)
    assert metadata['status'] == 'ok'
    assert metadata['count'] == 2


def test_math_service_average_partial_overlap(tmp_path: Path) -> None:
    """Test averaging spectra with only partial wavelength overlap."""
    # Spec1: 400-600 nm
    x1 = np.array([400.0, 450.0, 500.0, 550.0, 600.0])
    y1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    
    # Spec2: 500-700 nm (overlaps 500-600)
    x2 = np.array([500.0, 550.0, 600.0, 650.0, 700.0])
    y2 = np.array([3.0, 4.0, 5.0, 6.0, 7.0])
    
    spec1 = _make_spectrum(name="spec1", x=x1, y=y1)
    spec2 = _make_spectrum(name="spec2", x=x2, y=y2)
    
    math_service = MathService(UnitsService())
    result, metadata = math_service.average([spec1, spec2])
    
    # Result should only cover overlapping range (500-600)
    assert result.x.min() >= 500.0
    assert result.x.max() <= 600.0
    assert metadata['wavelength_range'][0] == 500.0
    assert metadata['wavelength_range'][1] == 600.0


def test_math_service_average_no_overlap_error(tmp_path: Path) -> None:
    """Test that averaging fails when spectra have no overlapping range."""
    # Spec1: 400-500 nm
    x1 = np.array([400.0, 450.0, 500.0])
    y1 = np.array([1.0, 2.0, 3.0])
    
    # Spec2: 600-700 nm (no overlap!)
    x2 = np.array([600.0, 650.0, 700.0])
    y2 = np.array([1.0, 2.0, 3.0])
    
    spec1 = _make_spectrum(name="spec1", x=x1, y=y1)
    spec2 = _make_spectrum(name="spec2", x=x2, y=y2)
    
    math_service = MathService(UnitsService())
    
    with pytest.raises(ValueError, match="no overlapping wavelength range"):
        math_service.average([spec1, spec2])


def test_math_service_average_custom_name(tmp_path: Path) -> None:
    """Test averaging with custom result name."""
    x = np.array([400.0, 450.0, 500.0])
    y1 = np.array([1.0, 2.0, 3.0])
    y2 = np.array([3.0, 4.0, 5.0])
    
    spec1 = _make_spectrum(name="test1", x=x, y=y1)
    spec2 = _make_spectrum(name="test2", x=x, y=y2)
    
    math_service = MathService(UnitsService())
    result, _ = math_service.average([spec1, spec2], name="My Custom Average")
    
    assert result.name == "My Custom Average"


def test_merge_ui_preview_updates(tmp_path: Path) -> None:
    """Test that merge preview updates when datasets are selected."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Ingest multiple spectra
        for i in range(3):
            csv_path = tmp_path / f"test{i}.csv"
            csv_path.write_text(
                f"wavelength_nm,absorbance\n"
                f"400,{i+1}.0\n"
                f"450,{i+2}.0\n"
                f"500,{i+3}.0\n",
                encoding="utf-8"
            )
            window._ingest_path(csv_path)
            app.processEvents()
        
        # Initially no selection
        assert "No datasets selected" in window.merge_preview_label.text()
        assert not window.merge_average_button.isEnabled()
        
        # Select first dataset
        first_item = window._originals_item.child(0, 0)
        index = window.dataset_model.indexFromItem(first_item)
        window.dataset_view.selectionModel().select(
            index,
            QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows
        )
        app.processEvents()
        
        # Should show 1 dataset but button disabled (need at least 2)
        assert "1 dataset selected" in window.merge_preview_label.text()
        assert not window.merge_average_button.isEnabled()
        
        # Select second dataset too
        second_item = window._originals_item.child(1, 0)
        index2 = window.dataset_model.indexFromItem(second_item)
        window.dataset_view.selectionModel().select(
            index2,
            QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows
        )
        app.processEvents()
        
        # Should show 2 datasets and enable button
        assert "2 datasets selected" in window.merge_preview_label.text()
        assert window.merge_average_button.isEnabled()
        
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_merge_respects_visibility_checkbox(tmp_path: Path) -> None:
    """Test that 'only visible' checkbox filters datasets correctly."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Ingest 3 spectra
        for i in range(3):
            csv_path = tmp_path / f"test{i}.csv"
            csv_path.write_text(
                f"wavelength_nm,absorbance\n"
                f"400,{i+1}.0\n"
                f"450,{i+2}.0\n"
                f"500,{i+3}.0\n",
                encoding="utf-8"
            )
            window._ingest_path(csv_path)
            app.processEvents()
        
        # Select all 3 datasets
        for i in range(3):
            item = window._originals_item.child(i, 0)
            index = window.dataset_model.indexFromItem(item)
            window.dataset_view.selectionModel().select(
                index,
                QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows
            )
        app.processEvents()
        
        # Should show 3 datasets
        assert "3 datasets selected" in window.merge_preview_label.text()
        
        # Uncheck visibility on second dataset
        vis_item = window._originals_item.child(1, 1)
        vis_item.setCheckState(QtCore.Qt.CheckState.Unchecked)
        app.processEvents()
        
        # With "only visible" checked, should now show 2 datasets
        assert window.merge_only_visible.isChecked()
        assert "2 datasets selected" in window.merge_preview_label.text()
        
        # Uncheck "only visible" - should show all 3 again
        window.merge_only_visible.setChecked(False)
        app.processEvents()
        assert "3 datasets selected" in window.merge_preview_label.text()
        
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_merge_average_creates_new_spectrum(tmp_path: Path) -> None:
    """Test that averaging creates a new spectrum in the overlay."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Ingest 2 spectra
        csv1 = tmp_path / "test1.csv"
        csv1.write_text(
            "wavelength_nm,absorbance\n"
            "400,1.0\n"
            "500,2.0\n"
            "600,3.0\n",
            encoding="utf-8"
        )
        csv2 = tmp_path / "test2.csv"
        csv2.write_text(
            "wavelength_nm,absorbance\n"
            "400,3.0\n"
            "500,4.0\n"
            "600,5.0\n",
            encoding="utf-8"
        )
        window._ingest_path(csv1)
        window._ingest_path(csv2)
        app.processEvents()
        
        # Select both
        for i in range(2):
            item = window._originals_item.child(i, 0)
            index = window.dataset_model.indexFromItem(item)
            window.dataset_view.selectionModel().select(
                index,
                QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows
            )
        app.processEvents()
        
        # Initially 2 spectra
        assert len(window.overlay_service.list()) == 2
        
        # Perform average
        window._on_merge_average()
        app.processEvents()
        
        # Should now have 3 spectra (original 2 + averaged)
        assert len(window.overlay_service.list()) == 3
        
        # Find the averaged spectrum
        specs = window.overlay_service.list()
        averaged = [s for s in specs if "Average" in s.name][0]
        
        # Check averaged values (should be mean of 1.0,3.0 = 2.0 etc)
        assert averaged.y[0] == pytest.approx(2.0, abs=0.1)  # (1+3)/2
        assert averaged.y[1] == pytest.approx(3.0, abs=0.1)  # (2+4)/2
        assert averaged.y[2] == pytest.approx(4.0, abs=0.1)  # (3+5)/2
        
        # Check status message
        assert "Created" in window.merge_status_label.text()
        
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_merge_subtract_creates_difference_spectrum(tmp_path: Path) -> None:
    """Test that subtraction creates A - B spectrum."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Ingest 2 spectra with same wavelength grid
        csv1 = tmp_path / "test1.csv"
        csv1.write_text(
            "wavelength_nm,absorbance\n"
            "400,5.0\n"
            "500,6.0\n"
            "600,7.0\n",
            encoding="utf-8"
        )
        csv2 = tmp_path / "test2.csv"
        csv2.write_text(
            "wavelength_nm,absorbance\n"
            "400,2.0\n"
            "500,3.0\n"
            "600,4.0\n",
            encoding="utf-8"
        )
        window._ingest_path(csv1)
        window._ingest_path(csv2)
        app.processEvents()
        
        # Select both (first selected will be A, second will be B)
        for i in range(2):
            item = window._originals_item.child(i, 0)
            index = window.dataset_model.indexFromItem(item)
            window.dataset_view.selectionModel().select(
                index,
                QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows
            )
        app.processEvents()
        
        # Check button is enabled
        assert window.merge_subtract_button.isEnabled()
        
        # Initially 2 spectra
        assert len(window.overlay_service.list()) == 2
        
        # Perform subtraction
        window._on_merge_subtract()
        app.processEvents()
        
        # Should now have 3 spectra (original 2 + difference)
        assert len(window.overlay_service.list()) == 3
        
        # Find the difference spectrum
        specs = window.overlay_service.list()
        diff = [s for s in specs if " - " in s.name][0]
        
        # Check difference values (should be A - B = 5-2=3, 6-3=3, 7-4=3)
        assert diff.y[0] == pytest.approx(3.0, abs=0.1)
        assert diff.y[1] == pytest.approx(3.0, abs=0.1)
        assert diff.y[2] == pytest.approx(3.0, abs=0.1)
        
        # Check status message
        assert "Created" in window.merge_status_label.text()
        assert "−" in window.merge_status_label.text() or "-" in window.merge_status_label.text()
        
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_merge_ratio_creates_quotient_spectrum(tmp_path: Path) -> None:
    """Test that ratio creates A / B spectrum."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Ingest 2 spectra with same wavelength grid
        csv1 = tmp_path / "test1.csv"
        csv1.write_text(
            "wavelength_nm,absorbance\n"
            "400,6.0\n"
            "500,9.0\n"
            "600,12.0\n",
            encoding="utf-8"
        )
        csv2 = tmp_path / "test2.csv"
        csv2.write_text(
            "wavelength_nm,absorbance\n"
            "400,2.0\n"
            "500,3.0\n"
            "600,4.0\n",
            encoding="utf-8"
        )
        window._ingest_path(csv1)
        window._ingest_path(csv2)
        app.processEvents()
        
        # Select both
        for i in range(2):
            item = window._originals_item.child(i, 0)
            index = window.dataset_model.indexFromItem(item)
            window.dataset_view.selectionModel().select(
                index,
                QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows
            )
        app.processEvents()
        
        # Check button is enabled
        assert window.merge_ratio_button.isEnabled()
        
        # Initially 2 spectra
        assert len(window.overlay_service.list()) == 2
        
        # Perform ratio
        window._on_merge_ratio()
        app.processEvents()
        
        # Should now have 3 spectra (original 2 + ratio)
        assert len(window.overlay_service.list()) == 3
        
        # Find the ratio spectrum
        specs = window.overlay_service.list()
        ratio = [s for s in specs if " / " in s.name][0]
        
        # Check ratio values (should be A / B = 6/2=3, 9/3=3, 12/4=3)
        assert ratio.y[0] == pytest.approx(3.0, abs=0.1)
        assert ratio.y[1] == pytest.approx(3.0, abs=0.1)
        assert ratio.y[2] == pytest.approx(3.0, abs=0.1)
        
        # Check status message
        assert "Created" in window.merge_status_label.text()
        assert "/" in window.merge_status_label.text()
        
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_merge_math_buttons_disabled_for_different_grids(tmp_path: Path) -> None:
    """Test that subtract/ratio buttons are disabled for different wavelength grids."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Ingest 2 spectra with DIFFERENT wavelength grids
        csv1 = tmp_path / "test1.csv"
        csv1.write_text(
            "wavelength_nm,absorbance\n"
            "400,1.0\n"
            "500,2.0\n"
            "600,3.0\n",
            encoding="utf-8"
        )
        csv2 = tmp_path / "test2.csv"
        csv2.write_text(
            "wavelength_nm,absorbance\n"
            "410,2.0\n"  # Different grid!
            "510,3.0\n"
            "610,4.0\n",
            encoding="utf-8"
        )
        window._ingest_path(csv1)
        window._ingest_path(csv2)
        app.processEvents()
        
        # Select both
        for i in range(2):
            item = window._originals_item.child(i, 0)
            index = window.dataset_model.indexFromItem(item)
            window.dataset_view.selectionModel().select(
                index,
                QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows
            )
        app.processEvents()
        
        # Math buttons should be disabled (different grids)
        assert not window.merge_subtract_button.isEnabled()
        assert not window.merge_ratio_button.isEnabled()
        
        # But average should still be enabled (uses interpolation)
        assert window.merge_average_button.isEnabled()
        
        # Check preview message warns about different grids
        assert "Different wavelength grids" in window.merge_preview_label.text() or "different" in window.merge_preview_label.text().lower()
        
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


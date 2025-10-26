"""Test dataset removal functionality."""
from pathlib import Path
import os

import pytest

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


def test_remove_single_dataset(tmp_path: Path) -> None:
    """Test removing a single dataset via context menu."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Ingest a test CSV
        csv_path = tmp_path / "test1.csv"
        csv_path.write_text("wavelength_nm,absorbance\n400,0.1\n410,0.2\n", encoding="utf-8")
        window._ingest_path(csv_path)
        app.processEvents()
        
        # Verify spectrum added
        assert len(window.overlay_service.list()) == 1
        assert window._originals_item.rowCount() == 1
        
        # Get the spectrum ID
        spec_id = list(window._dataset_items.keys())[0]
        
        # Simulate removal
        alias_item = window._dataset_items[spec_id]
        index = window.dataset_model.indexFromItem(alias_item)
        window._remove_selected_datasets([index])
        
        # Verify removal
        assert len(window.overlay_service.list()) == 0
        assert window._originals_item.rowCount() == 0
        assert spec_id not in window._dataset_items
        assert spec_id not in window._spectrum_colors
        assert spec_id not in window._visibility
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_remove_multiple_datasets(tmp_path: Path) -> None:
    """Test removing multiple datasets at once."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Ingest multiple test CSVs
        for i in range(3):
            csv_path = tmp_path / f"test{i}.csv"
            csv_path.write_text(f"wavelength_nm,absorbance\n400,{i*0.1}\n410,{i*0.2}\n", encoding="utf-8")
            window._ingest_path(csv_path)
            app.processEvents()
        
        # Verify spectra added
        assert len(window.overlay_service.list()) == 3
        assert window._originals_item.rowCount() == 3
        
        # Get spectrum IDs (remove first two)
        spec_ids = list(window._dataset_items.keys())[:2]
        indexes = [window.dataset_model.indexFromItem(window._dataset_items[sid]) for sid in spec_ids]
        
        # Simulate removal
        window._remove_selected_datasets(indexes)
        
        # Verify removal
        assert len(window.overlay_service.list()) == 1
        assert window._originals_item.rowCount() == 1
        for spec_id in spec_ids:
            assert spec_id not in window._dataset_items
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_delete_key_shortcut(tmp_path: Path) -> None:
    """Test Delete key removes selected datasets."""
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")
    
    app = _ensure_app()
    log_service = KnowledgeLogService(log_path=tmp_path / "history.md", author="pytest")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    try:
        # Ingest a test CSV
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("wavelength_nm,absorbance\n400,0.1\n410,0.2\n", encoding="utf-8")
        window._ingest_path(csv_path)
        app.processEvents()
        
        # Select the dataset
        spec_id = list(window._dataset_items.keys())[0]
        alias_item = window._dataset_items[spec_id]
        index = window.dataset_model.indexFromItem(alias_item)
        window.dataset_view.selectionModel().select(index, QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows)
        
        # Trigger shortcut handler
        window._remove_selected_datasets_shortcut()
        
        # Verify removal
        assert len(window.overlay_service.list()) == 0
        assert window._originals_item.rowCount() == 0
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

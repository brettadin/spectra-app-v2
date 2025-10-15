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


def test_show_documentation_selects_first_entry_without_error() -> None:
    if SpectraMainWindow is None or QtWidgets is None:
        pytest.skip(f"Qt stack unavailable: {_qt_import_error}")

    app = _ensure_app()
    window = SpectraMainWindow()
    try:
        window.show_documentation()
        app.processEvents()

        count = window.docs_list.count()
        if count == 0:
            pytest.skip("No documentation topics available")

        assert window.docs_list.currentRow() == 0
        current = window.docs_list.currentItem()
        assert current is not None
        assert not current.isHidden()
        # Ensure the viewer has displayed content for the selection.
        assert window.doc_viewer.toPlainText() or window.doc_viewer.toHtml()
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

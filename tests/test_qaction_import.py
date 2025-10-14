import pytest


def test_qaction_import_and_create():
    from app.qt_compat import get_qt

    try:
        QtCore, QtGui, QtWidgets, _ = get_qt()
    except ImportError:
        pytest.skip("No Qt binding available for test")
    action = QtGui.QAction("Test", None)
    assert action.text() == "Test"

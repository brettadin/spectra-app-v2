# app/qt_compat.py
"""
Qt compatibility layer to smooth over Qt5/Qt6 differences for QAction & enums.
"""


def get_qt():
    try:
        # Prefer PySide6
        from PySide6 import QtCore, QtGui, QtWidgets
        return QtCore, QtGui, QtWidgets, "PySide6"
    except Exception:
        pass
    try:
        # Fallback to PySide2
        from PySide2 import QtCore, QtGui, QtWidgets
        return QtCore, QtGui, QtWidgets, "PySide2"
    except Exception:
        pass
    try:
        # PyQt6
        from PyQt6 import QtCore, QtGui, QtWidgets
        return QtCore, QtGui, QtWidgets, "PyQt6"
    except Exception:
        pass
    try:
        # PyQt5
        from PyQt5 import QtCore, QtGui, QtWidgets
        return QtCore, QtGui, QtWidgets, "PyQt5"
    except Exception:
        pass
    raise ImportError("No supported Qt binding found (PySide6/PySide2/PyQt6/PyQt5).")

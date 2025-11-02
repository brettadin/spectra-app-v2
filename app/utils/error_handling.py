"""UI error handling helpers.

Provides a lightweight decorator for UI action handlers that logs exceptions
and shows a user-friendly message box without crashing the app.

This module has no Qt imports at import time to avoid binding-order issues;
it imports Qt lazily on exception to display the dialog.
"""
from __future__ import annotations

import functools
import logging
import traceback

logger = logging.getLogger("spectra.ui")


def ui_action(message: str = "An unexpected error occurred."):
    """Decorator for Qt slot functions to catch and report exceptions.

    Usage:
        @ui_action("Failed to export")
        def on_export(self):
            ...
    """

    def _decorator(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - defensive UI wrapper
                details = traceback.format_exc()
                try:
                    logger.error("%s: %s", message, exc)
                    logger.debug("Traceback for UI error:\n%s", details)
                except Exception:
                    pass
                # Lazy import Qt to avoid hard dependency at import time
                try:
                    from app.qt_compat import get_qt  # type: ignore
                    QtCore, QtGui, QtWidgets, _ = get_qt()
                    QtWidgets.QMessageBox.warning(None, "Error", f"{message}\n\n{exc}")
                except Exception:
                    # Last resort: print to stderr
                    try:
                        import sys
                        print(details, file=sys.stderr)
                    except Exception:
                        pass
                return None

        return _wrapper

    return _decorator

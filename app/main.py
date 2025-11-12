"""Application entry point for the Spectra desktop shell."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, cast
import types

try:
    from app.qt_compat import get_qt
except ModuleNotFoundError as exc:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        from app.qt_compat import get_qt
    except ModuleNotFoundError as second_exc:  # pragma: no cover - defensive fallback
        raise exc from second_exc

from app.logging_config import setup_logging
from app.ui.main_window import SpectraMainWindow
from app.services import nist_asd_service as nist_asd_service_module

QtCore: Any
QtGui: Any
QtWidgets: Any
qt_tuple: tuple[Any, Any, Any, str] = get_qt()
QtCore = cast(Any, qt_tuple[0])
QtGui = cast(Any, qt_tuple[1])
QtWidgets = cast(Any, qt_tuple[2])
QT_BINDING = qt_tuple[3]

# Re-exported constants used by tests to monkeypatch paths
SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

# Global NIST ASD service instance re-exported for UI modules that lazily access
# main_module.nist_asd_service. The heavy astroquery import cost is incurred only
# if the user triggers a NIST fetch. If astroquery is unavailable, fetch calls
# will raise a clear NistUnavailableError handled in the UI.
nist_asd_service = nist_asd_service_module  # provides fetch_lines(), clear_cache(), cache_stats()


def _install_exception_handler() -> None:
    """Show uncaught exceptions in both console and a dialog, then exit."""
    def _excepthook(exc_type: type[BaseException], exc_value: BaseException, exc_tb: types.TracebackType | None):
        import traceback
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        # Persist to a log file for sharing during support sessions
        try:
            logs_dir = Path(__file__).resolve().parent.parent / "reports"
            logs_dir.mkdir(parents=True, exist_ok=True)
            (logs_dir / "runtime.log").write_text(details, encoding="utf-8")
        except Exception:
            pass
        try:
            # Print to the terminal for real-time visibility
            print(details, file=sys.stderr)
        except Exception:
            pass
        try:
            # Also surface in a message box so the window doesn't just vanish
            QtWidgets.QMessageBox.critical(None, "Unhandled exception", details)
        except Exception:
            pass
    sys.excepthook = _excepthook


def main(argv: list[str] | None = None) -> int:
    """Launch the Spectra desktop app.

    Returns an OS exit code (0 for normal shutdown).
    """
    # Initialize baseline logging early so startup issues are captured
    logger = setup_logging()
    try:
        logger.info("Starting Spectra App desktop session")
    except Exception:
        pass
    _install_exception_handler()

    # High-DPI scaling is automatic in Qt6; no need for deprecated attributes
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(argv or sys.argv)
    app.setApplicationName("Spectra App")
    app.setOrganizationName("Spectra")
    try:
        window: SpectraMainWindow = SpectraMainWindow(theme_key=theme.key)
        window.show()
        logger.info("Main window constructed and shown successfully")
    except Exception as exc:
        logger.exception("Failed to construct main window: %s", exc)
        return 1
    code = app.exec()
    try:
        logger.info("Qt event loop exited with code %s", code)
    except Exception:
        pass
    return code


if __name__ == "__main__":  # Script/direct launch
    raise SystemExit(main())

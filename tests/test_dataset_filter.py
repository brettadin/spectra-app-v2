import os

import numpy as np
import pytest

try:
    from app.main import SpectraMainWindow
    from app.qt_compat import get_qt
    from app.services.spectrum import Spectrum
except ImportError as exc:  # pragma: no cover - optional on headless CI
    SpectraMainWindow = None  # type: ignore[assignment]
    Spectrum = None  # type: ignore[assignment]
    _qt_import_error = exc
    QtCore = QtGui = QtWidgets = None  # type: ignore[assignment]
else:  # pragma: no cover - exercised via regression test
    _qt_import_error = None
    QtCore, QtGui, QtWidgets, _ = get_qt()


def _ensure_app() -> "QtWidgets.QApplication":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.mark.skipif(SpectraMainWindow is None or QtWidgets is None, reason="Qt stack unavailable")
def test_dataset_filter_hides_non_matching_entries() -> None:
    pytest.importorskip("pyqtgraph")

    app = _ensure_app()
    window = SpectraMainWindow()
    try:
        assert window.dataset_filter is not None

        # Create two synthetic spectra so their aliases are easy to filter.
        spec_alpha = Spectrum.create(
            name="Alpha Lamp",
            x=np.linspace(400.0, 500.0, 3),
            y=np.array([0.1, 0.2, 0.3]),
        )
        spec_beta = Spectrum.create(
            name="Beta Lamp",
            x=np.linspace(500.0, 600.0, 3),
            y=np.array([0.3, 0.2, 0.1]),
        )

        window.overlay_service.add(spec_alpha)
        window._add_spectrum(spec_alpha)
        window.overlay_service.add(spec_beta)
        window._add_spectrum(spec_beta)

        app.processEvents()

        window.dataset_filter.setText("beta")
        app.processEvents()

        originals = window._originals_item
        assert originals is not None
        index = window.dataset_model.indexFromItem(originals)

        visibility = {
            originals.child(row).text(): not window.dataset_tree.isRowHidden(row, index)
            for row in range(originals.rowCount())
        }

        assert visibility.get("Beta Lamp") is True
        assert visibility.get("Alpha Lamp") is False

        # Clearing the filter restores both entries.
        window.dataset_filter.clear()
        app.processEvents()
        visibility_after_clear = {
            originals.child(row).text(): not window.dataset_tree.isRowHidden(row, index)
            for row in range(originals.rowCount())
        }
        assert all(visibility_after_clear.values())
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

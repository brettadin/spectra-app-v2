"""Performance guard tests for the plot pane."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pyqtgraph", exc_type=ImportError)

from app.qt_compat import get_qt
from app.ui.plot_pane import PlotPane


def test_plotpane_downsamples_to_point_cap():
    try:
        _, _, QtWidgets, _ = get_qt()
    except ImportError:  # pragma: no cover - environment specific
        pytest.skip("Qt bindings not available")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    pane = PlotPane()
    assert pane._max_points <= 120_000  # Guard rail to prevent regressions

    x = np.linspace(0, 1, pane._max_points * 5)
    y = np.sin(x)
    xs, ys = pane._downsample_peak(x, y, pane._max_points)

    assert len(xs) <= pane._max_points * 2
    assert len(xs) < len(x)
    assert len(xs) == len(ys)

    pane.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_plotpane_crosshair_toggle():
    try:
        _, _, QtWidgets, _ = get_qt()
    except ImportError:  # pragma: no cover - environment specific
        pytest.skip("Qt bindings not available")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    pane = PlotPane()

    assert pane.is_crosshair_visible()

    pane.set_crosshair_visible(False)
    assert not pane.is_crosshair_visible()

    pane.set_crosshair_visible(True)
    assert pane.is_crosshair_visible()

    pane.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()

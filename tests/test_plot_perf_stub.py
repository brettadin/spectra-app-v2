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
    assert pane.max_points <= PlotPane.DEFAULT_MAX_POINTS  # Guard rail to prevent regressions

    x = np.linspace(0, 1, pane.max_points * 5)
    y = np.sin(x)
    xs, ys = pane._downsample_peak(x, y, pane.max_points)

    assert len(xs) <= pane.max_points * 2
    assert len(xs) < len(x)
    assert len(xs) == len(ys)

    pane.deleteLater()
    if QtWidgets.QApplication.instance() is app and not app.topLevelWidgets():
        app.quit()


def test_plotpane_max_points_override_and_clamping():
    try:
        _, _, QtWidgets, _ = get_qt()
    except ImportError:  # pragma: no cover - environment specific
        pytest.skip("Qt bindings not available")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    pane = PlotPane(max_points=10_000)
    assert pane.max_points == 10_000

    # Setting too-low values clamps to the supported minimum.
    pane.set_max_points(10)
    assert pane.max_points == PlotPane.MIN_MAX_POINTS

    # Setting too-high values clamps to the supported maximum.
    pane.set_max_points(5_000_000)
    assert pane.max_points == PlotPane.MAX_MAX_POINTS

    # Downsampling honours the configured budget.
    x = np.linspace(0, 1, pane.max_points * 4)
    y = np.cos(x)
    xs, _ = pane._downsample_peak(x, y, pane.max_points)
    assert len(xs) <= pane.max_points * 2

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

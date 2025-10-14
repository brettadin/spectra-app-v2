"""Reusable plotting pane for spectral traces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters

from app.qt_compat import get_qt

QtCore: Any
QtGui: Any
QtWidgets: Any
_: Any
QtCore, QtGui, QtWidgets, _ = get_qt()


@dataclass
class TraceStyle:
    """Styling parameters for plot traces."""

    color: QtGui.QColor
    width: float = 1.5
    # Accepted for backwards compatibility but ignored by pyqtgraph 0.13.x.
    antialias: bool = False
    show_in_legend: bool = True


class PlotPane(QtWidgets.QWidget):
    """Central plotting widget with legend, crosshair, and multi-trace support."""

    unitChanged = QtCore.Signal(str)
    pointHovered = QtCore.Signal(float, float)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._display_unit = "nm"
        self._traces: Dict[str, Dict[str, object]] = {}
        self._order: list[str] = []
        self._max_points = 120_000
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    def set_display_unit(self, unit: str) -> None:
        if unit == self._display_unit:
            return
        self._display_unit = unit
        self._redraw_units()
        self.unitChanged.emit(unit)

    def add_trace(
        self,
        key: str,
        alias: str,
        x_nm: np.ndarray,
        y: np.ndarray,
        style: TraceStyle,
    ) -> None:
        """Add or update a trace in the plot."""

        if key in self._traces:
            trace = self._traces[key]
            trace["alias"] = alias
            trace["x_nm"] = np.array(x_nm, copy=True)
            trace["y"] = np.array(y, copy=True)
            trace["style"] = style
            self._apply_style(key)
            self._update_curve(key)
            self._rebuild_legend()
            return

        curve = pg.PlotDataItem()
        self._plot.addItem(curve)
        self._traces[key] = {
            "alias": alias,
            "x_nm": np.array(x_nm, copy=True),
            "y": np.array(y, copy=True),
            "item": curve,
            "style": style,
            "visible": True,
        }
        self._order.append(key)
        self._apply_style(key)
        self._update_curve(key)
        self._rebuild_legend()

    def remove_trace(self, key: str) -> None:
        trace = self._traces.pop(key, None)
        if not trace:
            return
        item: pg.PlotDataItem = trace["item"]  # type: ignore[assignment]
        self._plot.removeItem(item)
        self._order = [k for k in self._order if k != key]
        self._rebuild_legend()

    def set_visible(self, key: str, visible: bool) -> None:
        trace = self._traces.get(key)
        if not trace:
            return
        trace["visible"] = visible
        item: pg.PlotDataItem = trace["item"]  # type: ignore[assignment]
        item.setVisible(visible)
        self._rebuild_legend()

    def update_style(self, key: str, style: TraceStyle) -> None:
        trace = self._traces.get(key)
        if not trace:
            return
        trace["style"] = style
        self._apply_style(key)
        self._rebuild_legend()

    def update_alias(self, key: str, alias: str) -> None:
        trace = self._traces.get(key)
        if not trace:
            return
        trace["alias"] = alias
        self._rebuild_legend()

    def autoscale(self) -> None:
        self._plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

    def export_png(self, path: str | Path, width: int = 1600) -> None:
        """Export the current plot view as a PNG image."""

        exporter = pg.exporters.ImageExporter(self._plot.plotItem)
        exporter.parameters()["width"] = width
        exporter.export(str(path))

    # ------------------------------------------------------------------
    # Internal helpers
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # Use pyqtgraph defaults for foreground/background colours to avoid
        # invalid colour values being passed to mkColor.
        pg.setConfigOptions(antialias=False)

        self._plot = pg.PlotWidget()
        self._plot.setObjectName("plot-pane")
        self._plot.setClipToView(True)
        self._plot.setDownsampling(mode="peak")
        self._plot.showGrid(x=False, y=False, alpha=0.2)
        self._vb: pg.ViewBox = self._plot.getPlotItem().getViewBox()

        self._legend = pg.LegendItem(offset=(10, 10))
        self._legend.setParentItem(self._plot.getPlotItem())
        self._legend.anchor(itemPos=(0, 0), parentPos=(0, 0), offset=(10, 10))

        pen = pg.mkPen(100, 100, 100, 120)
        self._vline = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self._hline = pg.InfiniteLine(angle=0, movable=False, pen=pen)
        self._plot.addItem(self._vline, ignoreBounds=True)
        self._plot.addItem(self._hline, ignoreBounds=True)
        self._proxy = pg.SignalProxy(
            self._plot.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_move,
        )

        layout.addWidget(self._plot)

        self._plot.setLabel("bottom", "Wavelength", units=self._display_unit)
        self._plot.setLabel("left", "Intensity")

    def _apply_style(self, key: str) -> None:
        trace = self._traces[key]
        style: TraceStyle = trace["style"]  # type: ignore[assignment]
        pen = pg.mkPen(color=style.color, width=style.width)
        item: pg.PlotDataItem = trace["item"]  # type: ignore[assignment]
        item.setPen(pen)
        if hasattr(item, "setFillLevel"):
            item.setFillLevel(None)
        if hasattr(item, "setBrush"):
            item.setBrush(None)

    def _x_nm_to_disp(self, x_nm: np.ndarray) -> np.ndarray:
        unit = self._display_unit
        if unit == "nm":
            return x_nm
        if unit == "Å":
            return x_nm * 10.0
        if unit == "µm":
            return x_nm / 1000.0
        if unit == "cm⁻¹":
            with np.errstate(divide="ignore"):
                return 1e7 / x_nm
        return x_nm

    def _update_curve(self, key: str) -> None:
        trace = self._traces[key]
        item: pg.PlotDataItem = trace["item"]  # type: ignore[assignment]
        x_nm: np.ndarray = trace["x_nm"]  # type: ignore[assignment]
        y: np.ndarray = trace["y"]  # type: ignore[assignment]
        x_disp = self._x_nm_to_disp(x_nm)
        x_disp, y = self._downsample_peak(x_disp, y, self._max_points)
        item.setData(x_disp, y, connect="finite")
        item.setVisible(bool(trace.get("visible", True)))

    def _downsample_peak(
        self, x: np.ndarray, y: np.ndarray, max_points: int
    ) -> tuple[np.ndarray, np.ndarray]:
        n = len(x)
        if n <= max_points:
            return x, y
        step = int(np.ceil(n / max_points))
        if step <= 1:
            return x, y
        trim = n - (n % step)
        if trim <= 0:
            return x[::step], y[::step]
        xr = x[:trim].reshape(-1, step)
        yr = y[:trim].reshape(-1, step)
        x_bin = xr[:, 0]
        y_min = yr.min(axis=1)
        y_max = yr.max(axis=1)
        out_n = x_bin.size * 2
        xo = np.empty(out_n, dtype=x.dtype)
        yo = np.empty(out_n, dtype=y.dtype)
        xo[0::2] = x_bin
        xo[1::2] = x_bin
        yo[0::2] = y_min
        yo[1::2] = y_max
        if trim < n:
            tail_x = x[trim:]
            tail_y = y[trim:]
            xo = np.concatenate([xo, tail_x])
            yo = np.concatenate([yo, tail_y])
        return xo, yo

    def _redraw_units(self) -> None:
        for key in self._traces:
            self._update_curve(key)
        self._plot.setLabel("bottom", "Wavelength", units=self._display_unit)

    def _rebuild_legend(self) -> None:
        self._legend.clear()
        for key in self._order:
            trace = self._traces.get(key)
            if not trace:
                continue
            style: TraceStyle = trace["style"]  # type: ignore[assignment]
            if not bool(trace.get("visible", True)) or not style.show_in_legend:
                continue
            item: pg.PlotDataItem = trace["item"]  # type: ignore[assignment]
            alias = trace.get("alias", key)
            self._legend.addItem(item, str(alias))

    def _on_mouse_move(self, event) -> None:
        pos = event[0]
        if not self._plot.sceneBoundingRect().contains(pos):
            return
        mapped = self._plot.getPlotItem().vb.mapSceneToView(pos)
        self._vline.setPos(mapped.x())
        self._hline.setPos(mapped.y())
        self.pointHovered.emit(mapped.x(), mapped.y())

    def begin_bulk_update(self) -> None:
        self._plot.setUpdatesEnabled(False)

    def end_bulk_update(self) -> None:
        self._plot.setUpdatesEnabled(True)
        self.autoscale()

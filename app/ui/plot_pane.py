"""Reusable plotting pane for spectral traces."""

# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Sequence, cast

import numpy as np

try:
    import pyqtgraph as pg  # type: ignore[import-not-found]
    import pyqtgraph.exporters  # noqa: F401
except Exception:  # pragma: no cover
    pg = None  # type: ignore[assignment]

from app.qt_compat import get_qt
from .palettes import DEFAULT_PALETTE_KEY, PaletteDefinition, load_palette_definitions

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
    fill_brush: QtGui.QBrush | QtGui.QColor | str | None = None
    fill_level: float | None = None


class PlotPane(QtWidgets.QWidget):
    """Central plotting widget with legend, crosshair, and multi-trace support."""

    DEFAULT_MAX_POINTS = 120_000
    MIN_MAX_POINTS = 1_000
    MAX_MAX_POINTS = 1_000_000

    unitChanged = QtCore.Signal(str)
    pointHovered = QtCore.Signal(float, float)
    rangeChanged = QtCore.Signal(tuple, tuple)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        *,
        max_points: int | None = None,
    ) -> None:
        super().__init__(parent)
        if pg is None:
            raise RuntimeError("pyqtgraph is required for PlotPane")
        self._display_unit = "nm"
        self._y_label = "Intensity"
        self._traces: Dict[str, Dict[str, object]] = {}
        self._order: list[str] = []
        self._max_points = self.normalize_max_points(max_points)
        self._crosshair_visible = True
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
        *,
        uncertainty: np.ndarray | None = None,
        quality_flags: np.ndarray | None = None,
    ) -> None:
        """Add or update a trace in the plot."""

        if key in self._traces:
            trace = self._traces[key]
            trace["alias"] = alias
            trace["x_nm"] = np.array(x_nm, copy=True)
            trace["y"] = np.array(y, copy=True)
            trace["style"] = style
            trace["sigma"] = np.array(uncertainty, copy=True) if uncertainty is not None else None
            trace["flags"] = np.array(quality_flags, copy=True) if quality_flags is not None else None
            self._apply_style(key)
            self._update_curve(key)
            return

        curve = pg.PlotDataItem()
        x_copy = np.array(x_nm, copy=True)
        y_copy = np.array(y, copy=True)
        self._traces[key] = {
            "alias": alias,
            "x_nm": x_copy,
            "y": y_copy,
            "item": curve,
            "style": style,
            "visible": True,
            "sigma": (np.array(uncertainty, copy=True) if uncertainty is not None else None),
            "flags": (np.array(quality_flags, copy=True) if quality_flags is not None else None),
            "err_item": None,
            "flag_items": [],
        }
        self._order.append(key)
        self._apply_style(key)
        self._update_curve(key)  # Populate data before the curve is added to the plot
        self._plot.addItem(curve)
        self._rebuild_legend()

    def remove_export_from_context_menu(self) -> None:
        """Keep pyqtgraph's context menu but strip the built-in Export entry."""
        if pg is None:
            return
        self.strip_export_from_plot_widget(self._plot)

    @staticmethod
    def strip_export_from_plot_widget(plot_widget: Any) -> None:
        """Remove pyqtgraph's default export action from ``plot_widget`` if present."""

        if pg is None or plot_widget is None:
            return
        try:
            plot_item = plot_widget.getPlotItem()
        except Exception:
            return
        try:
            view_box = plot_item.getViewBox()
        except Exception:
            return

        menu: QtWidgets.QMenu | None = getattr(view_box, "menu", None)
        if menu is None and hasattr(view_box, "getMenu"):
            try:
                menu = cast(QtWidgets.QMenu, view_box.getMenu())
            except Exception:
                menu = None
        if menu is None:
            return

        sentinel_owner = cast(Any, menu)
        if getattr(sentinel_owner, "_spectra_export_stripped", False):
            return

        setattr(sentinel_owner, "_spectra_export_stripped", True)

        def _prune_export() -> None:
            try:
                for action in list(menu.actions()):
                    text = (action.text() or "").strip().lower()
                    if text.startswith("export"):
                        menu.removeAction(action)
            except Exception:
                pass

        try:
            menu.aboutToShow.connect(_prune_export)  # type: ignore[arg-type]
        except Exception:
            setattr(sentinel_owner, "_spectra_export_stripped", False)

    def view_range(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Return the current (x, y) view ranges."""

        x_range, y_range = self._plot.viewRange()
        return (tuple(x_range), tuple(y_range))

    def set_y_label(self, label: str) -> None:
        """Update the left-axis label text."""

        if label == self._y_label:
            return
        self._y_label = label
        self._plot.setLabel("left", label)

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
        """Autoscale the plot to fit all visible data."""
        try:
            self._plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
            self._plot.autoRange()  # Force immediate autoscale
        except Exception:
            pass

    def export_png(self, path: str | Path, width: int = 1600) -> None:
        """Export the current plot view as a PNG image."""

        exporter = pg.exporters.ImageExporter(self._plot.plotItem)
        exporter.parameters()["width"] = width
        exporter.export(str(path))

    def set_crosshair_visible(self, visible: bool) -> None:
        """Show or hide the crosshair guide."""

        self._crosshair_visible = bool(visible)
        self._vline.setVisible(self._crosshair_visible)
        self._hline.setVisible(self._crosshair_visible)

    def is_crosshair_visible(self) -> bool:
        """Return True when the crosshair guide is visible."""

        return self._crosshair_visible

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
        self._plot.sigRangeChanged.connect(self._on_plot_range_changed)

        self._legend = pg.LegendItem(offset=(10, 10))
        self._legend.setParentItem(self._plot.getPlotItem())
        self._legend.anchor(itemPos=(0, 0), parentPos=(0, 0), offset=(10, 10))

        pen = pg.mkPen(100, 100, 100, 120)
        self._vline = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self._hline = pg.InfiniteLine(angle=0, movable=False, pen=pen)
        self._plot.addItem(self._vline, ignoreBounds=True)
        self._plot.addItem(self._hline, ignoreBounds=True)
        self.set_crosshair_visible(self._crosshair_visible)
        self._proxy = pg.SignalProxy(
            self._plot.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_move,
        )

        layout.addWidget(self._plot)

        self._plot.setLabel("bottom", "Wavelength", units=self._display_unit)
        self._plot.setLabel("left", self._y_label)
        for axis in ("bottom", "left"):
            axis_item = self._plot.getPlotItem().getAxis(axis)
            if hasattr(axis_item, "enableAutoSIPrefix"):
                axis_item.enableAutoSIPrefix(False)

    # ------------------------------------------------------------------
    def _on_plot_range_changed(self, _: pg.PlotItem, ranges: object) -> None:
        """Emit a simplified range tuple when the view bounds change."""

        try:
            x_range, y_range = ranges  # type: ignore[misc]
        except Exception:
            x_range, y_range = self._plot.viewRange()

        def _coerce_pair(pair: object) -> tuple[float, float]:
            values: list[float] = []
            if isinstance(pair, (list, tuple)):
                for value in pair[:2]:
                    try:
                        values.append(float(value))
                    except (TypeError, ValueError):
                        values.append(float("nan"))
            if len(values) != 2:
                return (float("nan"), float("nan"))
            return (values[0], values[1])

        self.rangeChanged.emit(_coerce_pair(x_range), _coerce_pair(y_range))

    def _apply_style(self, key: str) -> None:
        trace = self._traces[key]
        style: TraceStyle = trace["style"]  # type: ignore[assignment]
        pen = pg.mkPen(color=style.color, width=style.width)
        item: pg.PlotDataItem = trace["item"]  # type: ignore[assignment]
        item.setPen(pen)
        if hasattr(item, "setAntialiasing"):
            item.setAntialiasing(style.antialias)
        if style.fill_brush is not None and hasattr(item, "setBrush"):
            item.setBrush(pg.mkBrush(style.fill_brush))
            if hasattr(item, "setFillLevel"):
                item.setFillLevel(style.fill_level)
        else:
            if hasattr(item, "setBrush"):
                item.setBrush(None)
            if hasattr(item, "setFillLevel"):
                item.setFillLevel(None)

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
        sigma: np.ndarray | None = trace.get("sigma")  # type: ignore[assignment]
        flags: np.ndarray | None = trace.get("flags")  # type: ignore[assignment]
        x_disp = self._x_nm_to_disp(x_nm)
        # Ensure display x is monotonically increasing for robust clipping/downsampling.
        # Conversions like cm⁻¹ = 1e7 / nm invert the order; reverse both arrays
        # so pyqtgraph's clipToView/downsampling never drops entire segments.
        try:
            if x_disp.size >= 2 and x_disp[-1] < x_disp[0]:
                x_disp = x_disp[::-1]
                y = y[::-1]
                if sigma is not None:
                    sigma = sigma[::-1]
                if flags is not None:
                    flags = flags[::-1]
        except Exception:
            pass
        x_disp, y = self._downsample_peak(x_disp, y, self._max_points)
        item.setData(x_disp, y, connect="finite")
        item.setVisible(bool(trace.get("visible", True)))

        # Remove any prior error/flag items before re-adding
        try:
            if trace.get("err_item") is not None:
                self._plot.removeItem(trace["err_item"])  # type: ignore[index]
                trace["err_item"] = None
        except Exception:
            pass
        try:
            for gi in list(trace.get("flag_items") or []):
                self._plot.removeItem(gi)
            trace["flag_items"] = []
        except Exception:
            pass

        # Error bars (only for moderate point counts for performance)
        try:
            if sigma is not None and x_disp.size <= 5000 and sigma.size == len(x_nm):
                # When downsampled, take matching head of sigma if sizes differ
                if sigma.size != x_disp.size:
                    # Basic resampling: interpolate sigma to x_disp domain
                    with np.errstate(all="ignore"):
                        sigma_disp = np.interp(x_disp, self._x_nm_to_disp(x_nm), sigma)
                else:
                    sigma_disp = sigma
                err = pg.ErrorBarItem(x=x_disp, y=y, top=sigma_disp, bottom=sigma_disp, beam=0.0)
                self._plot.addItem(err)
                trace["err_item"] = err
        except Exception:
            # Non-fatal if ErrorBarItem is unavailable
            pass

        # Quality flag markers (limited density)
        try:
            if flags is not None and flags.size == len(x_nm):
                # Map primary flags to colours
                flag_defs: list[tuple[int, QtGui.QColor, str]] = [
                    (0x01, QtGui.QColor(220, 20, 60), "Bad pixel"),        # red
                    (0x02, QtGui.QColor(255, 0, 255), "Cosmic ray"),       # magenta
                    (0x04, QtGui.QColor(255, 140, 0), "Saturated"),        # orange
                    (0x08, QtGui.QColor(255, 215, 0), "Low SNR"),          # gold
                ]
                x_src_disp = self._x_nm_to_disp(x_nm)
                for bit, color, _label in flag_defs:
                    mask = (flags & bit) != 0
                    if not np.any(mask):
                        continue
                    x_f = x_src_disp[mask]
                    # Place markers along bottom of current view for visibility
                    try:
                        _, y_range = self._plot.viewRange()
                        y_base = float(y_range[0])
                    except Exception:
                        y_base = 0.0
                    y_f = np.full_like(x_f, y_base, dtype=float)
                    # Limit number of points per flag type for performance
                    if x_f.size > 3000:
                        step = int(np.ceil(x_f.size / 3000))
                        x_f = x_f[::step]
                    spots = [{'pos': (xf, np.nan), 'data': 1} for xf in x_f]
                    sp = pg.ScatterPlotItem(size=6, pen=pg.mkPen(color), brush=pg.mkBrush(color), pxMode=True)
                    # Position markers at current y=NaN so they don't connect; use infinite line instead?
                    # Scatter without y can be weird; place at bottom of view bounds later if needed.
                    sp.setData(x=x_f, y=y_f)
                    self._plot.addItem(sp)
                    (trace.get("flag_items") or []).append(sp)
        except Exception:
            pass

    def set_max_points(self, value: int | None) -> None:
        """Adjust the point budget used when downsampling traces."""

        validated = self.normalize_max_points(value)
        if validated == self._max_points:
            return
        self._max_points = validated
        for key in self._traces:
            self._update_curve(key)

    @property
    def max_points(self) -> int:
        return self._max_points

    @classmethod
    def normalize_max_points(cls, value: int | None) -> int:
        if value is None:
            return cls.DEFAULT_MAX_POINTS
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return cls.DEFAULT_MAX_POINTS
        if numeric < cls.MIN_MAX_POINTS:
            return cls.MIN_MAX_POINTS
        if numeric > cls.MAX_MAX_POINTS:
            return cls.MAX_MAX_POINTS
        return numeric

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
        label = "Wavenumber" if self._display_unit == "cm⁻¹" else "Wavelength"
        self._plot.setLabel("bottom", label, units=self._display_unit)

    def map_nm_to_display(self, value_nm: float) -> float:
        """Convert a canonical wavelength (nm) to the current display unit."""

        array = np.array([value_nm], dtype=float)
        display = self._x_nm_to_disp(array)
        return float(display[0]) if display.size else float("nan")

    def add_graphics_item(self, item: pg.GraphicsObject, *, ignore_bounds: bool = False) -> None:
        """Attach an arbitrary graphics item to the underlying plot."""

        self._plot.addItem(item, ignoreBounds=ignore_bounds)

    def remove_graphics_item(self, item: pg.GraphicsObject) -> None:
        """Detach a previously added graphics item."""

        self._plot.removeItem(item)

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
    @staticmethod
    def palette_definitions() -> Sequence[PaletteDefinition]:
        """Expose the shared palette registry to callers."""

        return list(load_palette_definitions())

    @staticmethod
    def default_palette_key() -> str:
        """Return the key of the palette used for new sessions."""

        return DEFAULT_PALETTE_KEY


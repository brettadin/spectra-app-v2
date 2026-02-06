"""Reusable plotting pane for spectral traces."""

# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Sequence, cast

import numpy as np

try:
    import pyqtgraph as pg  # type: ignore[import-not-found]
    import pyqtgraph.exporters  # noqa: F401
except Exception:  # pragma: no cover
    pg = None  # type: ignore[assignment]

from app.qt_compat import get_qt
from app.ui.themes import ThemeDefinition, get_theme_definition
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


@dataclass
class Annotation:
    """A user annotation on the plot, associated with a dataset."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    dataset_id: str = ""  # Which spectrum this belongs to
    text: str = ""
    x_nm: float = 0.0  # Position in canonical nm
    x_max_nm: float | None = None  # If set, this is a range annotation
    y_fraction: float = 0.9  # Y position as fraction of view (0=bottom, 1=top)
    visible: bool = True
    color: str = "#FFFF00"  # Yellow default
    vertical: bool = False  # If True, display text vertically


class PlotPane(QtWidgets.QWidget):
    """Central plotting widget with legend, crosshair, and multi-trace support."""

    DEFAULT_MAX_POINTS = 50_000  # Reduced for better performance; PyQtGraph auto-downsamples beyond this
    MIN_MAX_POINTS = 1_000
    MAX_MAX_POINTS = 1_000_000

    unitChanged = QtCore.Signal(str)
    pointHovered = QtCore.Signal(float, float)
    rangeChanged = QtCore.Signal(tuple, tuple)
    # Emitted when the user changes the selection region: (min_nm, max_nm)
    regionSelected = QtCore.Signal(float, float)
    # Emitted when user requests to add annotation: (x_nm, y_fraction, x_max_nm or None for point)
    annotationRequested = QtCore.Signal(float, float, object)

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
        self._x_mode = "wavelength"  # wavelength|time|custom
        self._custom_x_label: str | None = None
        self._custom_x_unit: str | None = None
        self._y_label = "Intensity"
        # Custom labels (override auto-generated when set)
        self._custom_title: str | None = None
        self._custom_y_label: str | None = None
        self._traces: Dict[str, Dict[str, object]] = {}
        self._order: list[str] = []
        self._max_points = self.normalize_max_points(max_points)
        self._crosshair_visible = True
        self._title_visible = False
        self._axis_label_font_size = "14pt"
        self._title_font_size = "16pt"
        # Range selection region (for math/export operations)
        self._region_item: pg.LinearRegionItem | None = None
        self._region_visible = False
        # Annotations storage: {annotation_id: {'annotation': Annotation, 'text': pg.TextItem, 'region': pg.LinearRegionItem|None}}
        self._annotations: Dict[str, Dict[str, Any]] = {}
        self._annotations_visible = True  # Global toggle
        self._build_ui()
        # Don't apply theme during initialization - causes performance issues

    # ------------------------------------------------------------------
    # Public API
    def set_display_unit(self, unit: str) -> None:
        if unit == self._display_unit:
            return
        self._display_unit = unit
        self._redraw_units()
        self.unitChanged.emit(unit)

    def set_x_mode(self, mode: str, *, label: str | None = None, unit: str | None = None) -> None:
        """Switch the x-axis interpretation.

        ``mode`` accepts "wavelength" (default spectral view) or any other
        value to treat the x-axis as a generic/time axis (no unit conversion).
        ``label`` and ``unit`` override the bottom axis text for non-spectral
        modes.
        """

        normalized = mode.lower()
        self._x_mode = "wavelength" if normalized == "wavelength" else normalized
        if unit is not None:
            self._display_unit = unit
            self._custom_x_unit = unit
        if label is not None:
            self._custom_x_label = label
        self._redraw_units()

    def apply_theme(self, theme: ThemeDefinition | str | None) -> None:
        """Apply widget-level styling for the provided theme."""

        theme_def = theme if isinstance(theme, ThemeDefinition) else get_theme_definition(theme)
        palette = theme_def.palette
        plot_item = self._plot.getPlotItem()
        # Remember legend/text colours for later legend rebuilds
        try:
            self._legend_text_color = QtGui.QColor(palette.plot_foreground)
            self._legend_panel_color = QtGui.QColor(palette.panel_alt)
            self._legend_border_color = QtGui.QColor(palette.border)
        except Exception:
            pass

        # Plot background and axis colours
        try:
            self._plot.setBackground(palette.plot_background)
        except Exception:
            pass

        try:
            axis_pen = pg.mkPen(palette.plot_foreground)
            for axis in ("bottom", "left"):
                axis_item = plot_item.getAxis(axis)
                if hasattr(axis_item, "setPen"):
                    axis_item.setPen(axis_pen)
                if hasattr(axis_item, "setTextPen"):
                    axis_item.setTextPen(axis_pen)
            label_style = {"color": palette.plot_foreground, "font-size": self._axis_label_font_size}
            bottom_label, bottom_unit = self._bottom_axis_text()
            self._plot.setLabel("bottom", bottom_label, units=bottom_unit, **label_style)
            self._plot.setLabel("left", self._y_label, **label_style)
            # Update title with current theme color
            self._update_title()
        except Exception:
            pass

        # Light grid and crosshair pens tuned to the theme
        try:
            crosshair_color = QtGui.QColor(palette.plot_foreground)
            if crosshair_color.isValid():
                crosshair_color.setAlphaF(0.35)
                crosshair_pen = pg.mkPen(crosshair_color, width=1)
                self._vline.setPen(crosshair_pen)
                self._hline.setPen(crosshair_pen)
        except Exception:
            pass

        # Legend styling: subtle panel background and readable text
        self._apply_legend_theme_style()

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

        # Create PlotDataItem without performance options that trigger bugs in pyqtgraph 0.13.7
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

    def get_trace_stats(self) -> tuple[int, int]:
        """Return (trace_count, total_points) using stored x_nm lengths.

        Used by callers to make performance-mode decisions.
        """
        try:
            count = len(self._traces)
            total = 0
            for t in self._traces.values():
                arr = t.get("x_nm")
                total += int(arr.size) if hasattr(arr, "size") else 0
            return count, total
        except Exception:
            return 0, 0

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
        self._update_axis_labels()
        self._update_title()

    # ------------------------------------------------------------------
    # Custom Label API
    def set_custom_title(self, title: str | None) -> None:
        """Set a custom plot title (pass None to restore auto-generated)."""
        self._custom_title = title if title else None
        self._update_title()

    def get_custom_title(self) -> str | None:
        """Return the current custom title, or None if using auto-generated."""
        return self._custom_title

    def set_custom_x_axis_label(self, label: str | None) -> None:
        """Set a custom x-axis label (pass None to restore default)."""
        self._custom_x_label = label if label else None
        self._update_axis_labels()

    def get_custom_x_axis_label(self) -> str | None:
        """Return the current custom x-axis label, or None if using default."""
        return self._custom_x_label

    def set_custom_y_axis_label(self, label: str | None) -> None:
        """Set a custom y-axis label (pass None to restore auto-generated)."""
        self._custom_y_label = label if label else None
        self._update_axis_labels()

    def get_custom_y_axis_label(self) -> str | None:
        """Return the current custom y-axis label, or None if using default."""
        return self._custom_y_label

    def get_current_labels(self) -> dict[str, str]:
        """Return the currently displayed title and axis labels."""
        # Get what's actually shown
        bottom_label, bottom_unit = self._bottom_axis_text()
        x_text = f"{bottom_label} ({bottom_unit})" if bottom_unit else bottom_label
        y_text = self._custom_y_label or self._y_label
        
        # Get title (match _update_title logic)
        if self._custom_title:
            title = self._custom_title
        elif not self._title_visible:
            title = ""
        else:
            y_lower = self._y_label.lower()
            if "intensity" in y_lower:
                title = "Spectral Intensity"
            elif "absorbance" in y_lower:
                title = "Absorbance Spectrum"
            elif "transmittance" in y_lower:
                title = "Transmittance Spectrum"
            elif "reflectance" in y_lower:
                title = "Reflectance Spectrum"
            elif "flux" in y_lower:
                title = "Spectral Flux"
            elif "radiance" in y_lower:
                title = "Spectral Radiance"
            else:
                title = "Spectral Data"
        
        return {"title": title, "x_axis": x_text, "y_axis": y_text}

    # ------------------------------------------------------------------
    # Annotation API
    def add_annotation(self, annotation: Annotation) -> str:
        """Add an annotation to the plot. Returns the annotation ID."""
        # Create visual elements
        color = QtGui.QColor(annotation.color)
        
        # Text item for the label
        # Anchor: (0, 0.5) = left edge, vertically centered at click point
        # This makes text appear to the right of where you click
        if annotation.vertical:
            anchor = (0.5, 0.0)  # Center at bottom for vertical
        else:
            anchor = (0, 0.5)  # Left edge, vertically centered on click point
        
        text_item = pg.TextItem(
            text=annotation.text,
            color=color,
            anchor=anchor,
            border=pg.mkPen(color, width=0.5),  # Subtle border for visibility
            fill=pg.mkBrush(0, 0, 0, 150),  # Semi-transparent background
        )
        text_item.setFont(QtGui.QFont("Arial", 9))
        
        # Ensure text draws on top of everything (z-value)
        text_item.setZValue(1000)
        
        # Apply rotation for vertical text
        if annotation.vertical:
            text_item.setAngle(-90)  # Rotate 90 degrees counter-clockwise
        
        # Position in display units
        x_disp = self._x_nm_to_disp(np.array([annotation.x_nm]))[0]
        
        # Convert stored Y fraction to actual position in current view
        try:
            (_, y_range) = self.view_range()
            y0, y1 = float(y_range[0]), float(y_range[1])
            y_pos = y0 + (y1 - y0) * annotation.y_fraction
        except Exception:
            y_pos = 0.0
        
        text_item.setPos(x_disp, y_pos)
        
        # Range highlight if this is a range annotation
        region_item = None
        if annotation.x_max_nm is not None:
            x_max_disp = self._x_nm_to_disp(np.array([annotation.x_max_nm]))[0]
            # Ensure correct order for wavenumber (inverted)
            x_min_disp, x_max_disp = min(x_disp, x_max_disp), max(x_disp, x_max_disp)
            region_item = pg.LinearRegionItem(
                values=(x_min_disp, x_max_disp),
                movable=False,
                brush=pg.mkBrush(color.red(), color.green(), color.blue(), 30),
                pen=pg.mkPen(color, width=1, style=QtCore.Qt.PenStyle.DashLine),
            )
            # Region should be behind text
            region_item.setZValue(100)
            # Position text in center of range (for range annotations, center it)
            text_item.setAnchor((0.5, 0.5))  # Center for range annotations
            text_item.setPos((x_min_disp + x_max_disp) / 2, y_pos)
        
        # Add to plot (region first so it's behind text)
        if region_item:
            self._plot.addItem(region_item, ignoreBounds=True)
        self._plot.addItem(text_item, ignoreBounds=True)
        
        # Store
        self._annotations[annotation.id] = {
            'annotation': annotation,
            'text': text_item,
            'region': region_item,
        }
        
        # Apply visibility
        visible = self._annotations_visible and annotation.visible
        text_item.setVisible(visible)
        if region_item:
            region_item.setVisible(visible)
        
        return annotation.id

    def remove_annotation(self, annotation_id: str) -> bool:
        """Remove an annotation by ID. Returns True if found and removed."""
        entry = self._annotations.pop(annotation_id, None)
        if not entry:
            return False
        try:
            self._plot.removeItem(entry['text'])
            if entry['region']:
                self._plot.removeItem(entry['region'])
        except Exception:
            pass
        return True

    def update_annotation(self, annotation_id: str, text: str | None = None, 
                         color: str | None = None) -> bool:
        """Update an existing annotation's text or color."""
        entry = self._annotations.get(annotation_id)
        if not entry:
            return False
        ann: Annotation = entry['annotation']
        
        if text is not None:
            ann.text = text
            entry['text'].setText(text)
        
        if color is not None:
            ann.color = color
            qcolor = QtGui.QColor(color)
            entry['text'].setColor(qcolor)
            if entry['region']:
                entry['region'].setBrush(pg.mkBrush(qcolor.red(), qcolor.green(), qcolor.blue(), 30))
                entry['region'].setPen(pg.mkPen(qcolor, width=1, style=QtCore.Qt.PenStyle.DashLine))
        
        return True

    def set_annotation_visible(self, annotation_id: str, visible: bool) -> bool:
        """Set visibility of a single annotation."""
        entry = self._annotations.get(annotation_id)
        if not entry:
            return False
        ann: Annotation = entry['annotation']
        ann.visible = visible
        
        # Respect both individual and global visibility
        actual_visible = self._annotations_visible and visible
        entry['text'].setVisible(actual_visible)
        if entry['region']:
            entry['region'].setVisible(actual_visible)
        return True

    def set_all_annotations_visible(self, visible: bool) -> None:
        """Toggle global visibility of all annotations."""
        self._annotations_visible = visible
        for entry in self._annotations.values():
            ann: Annotation = entry['annotation']
            actual_visible = visible and ann.visible
            entry['text'].setVisible(actual_visible)
            if entry['region']:
                entry['region'].setVisible(actual_visible)

    def set_dataset_annotations_visible(self, dataset_id: str, visible: bool) -> None:
        """Toggle visibility of all annotations for a specific dataset."""
        for entry in self._annotations.values():
            ann: Annotation = entry['annotation']
            if ann.dataset_id == dataset_id:
                ann.visible = visible
                actual_visible = self._annotations_visible and visible
                entry['text'].setVisible(actual_visible)
                if entry['region']:
                    entry['region'].setVisible(actual_visible)

    def get_annotations(self, dataset_id: str | None = None) -> list[Annotation]:
        """Get all annotations, optionally filtered by dataset."""
        result = []
        for entry in self._annotations.values():
            ann: Annotation = entry['annotation']
            if dataset_id is None or ann.dataset_id == dataset_id:
                result.append(ann)
        return result

    def get_annotation(self, annotation_id: str) -> Annotation | None:
        """Get a specific annotation by ID."""
        entry = self._annotations.get(annotation_id)
        return entry['annotation'] if entry else None

    def clear_annotations(self, dataset_id: str | None = None) -> int:
        """Clear annotations, optionally only for a specific dataset. Returns count removed."""
        to_remove = []
        for ann_id, entry in self._annotations.items():
            ann: Annotation = entry['annotation']
            if dataset_id is None or ann.dataset_id == dataset_id:
                to_remove.append(ann_id)
        
        for ann_id in to_remove:
            self.remove_annotation(ann_id)
        return len(to_remove)

    def _refresh_annotation_positions(self) -> None:
        """Update annotation positions when units or view change."""
        try:
            (_, y_range) = self.view_range()
            y0, y1 = float(y_range[0]), float(y_range[1])
        except Exception:
            y0, y1 = 0.0, 1.0
        
        for entry in self._annotations.values():
            ann: Annotation = entry['annotation']
            x_disp = self._x_nm_to_disp(np.array([ann.x_nm]))[0]
            
            # Convert stored fraction to actual Y position
            y_pos = y0 + (y1 - y0) * ann.y_fraction
            
            if ann.x_max_nm is not None:
                x_max_disp = self._x_nm_to_disp(np.array([ann.x_max_nm]))[0]
                x_min_disp, x_max_disp = min(x_disp, x_max_disp), max(x_disp, x_max_disp)
                entry['text'].setPos((x_min_disp + x_max_disp) / 2, y_pos)
                if entry['region']:
                    entry['region'].setRegion((x_min_disp, x_max_disp))
            else:
                entry['text'].setPos(x_disp, y_pos)

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
        # Only update legend for this specific item instead of rebuilding everything
        self._update_legend_item(key)

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

    # ------------------------------------------------------------------
    # Range selection support
    # ------------------------------------------------------------------
    def set_region_visible(self, visible: bool) -> None:
        """Show or hide the interactive range selection region."""
        self._region_visible = bool(visible)
        if self._region_visible:
            self._ensure_region_item()
            if self._region_item is not None:
                self._region_item.setVisible(True)
        elif self._region_item is not None:
            self._region_item.setVisible(False)

    def is_region_visible(self) -> bool:
        """Return True when the range selection region is visible."""
        return self._region_visible

    def get_selected_region_nm(self) -> tuple[float, float] | None:
        """Return the currently selected region in nm, or None if not active.
        
        Returns:
            Tuple of (min_nm, max_nm) in canonical wavelength units, or None
        """
        if not self._region_visible or self._region_item is None:
            return None
        region = self._region_item.getRegion()
        # Convert display units back to nm
        min_disp, max_disp = region
        min_nm = self._disp_to_x_nm(min_disp)
        max_nm = self._disp_to_x_nm(max_disp)
        # Ensure min < max (in case of inverted units like cm⁻¹)
        if min_nm > max_nm:
            min_nm, max_nm = max_nm, min_nm
        return (min_nm, max_nm)

    def set_region_nm(self, min_nm: float, max_nm: float) -> None:
        """Set the selection region in canonical wavelength units (nm)."""
        self._ensure_region_item()
        if self._region_item is None:
            return
        min_disp = self.map_nm_to_display(min_nm)
        max_disp = self.map_nm_to_display(max_nm)
        # Handle inverted units (cm⁻¹)
        if min_disp > max_disp:
            min_disp, max_disp = max_disp, min_disp
        self._region_item.setRegion((min_disp, max_disp))

    def set_region_to_data_overlap(self) -> None:
        """Set the region to the overlapping range of all visible traces."""
        min_nm = float('-inf')
        max_nm = float('inf')
        has_data = False
        for trace in self._traces.values():
            if not trace.get("visible", True):
                continue
            x_nm = trace.get("x_nm")
            if x_nm is None or len(x_nm) == 0:
                continue
            has_data = True
            trace_min = float(np.nanmin(x_nm))
            trace_max = float(np.nanmax(x_nm))
            min_nm = max(min_nm, trace_min)
            max_nm = min(max_nm, trace_max)
        
        if has_data and min_nm < max_nm:
            self.set_region_nm(min_nm, max_nm)
            self.set_region_visible(True)

    def set_region_to_view(self) -> None:
        """Set the region to match the current view bounds."""
        try:
            x_range, _ = self._plot.viewRange()
            min_disp, max_disp = x_range
            self._ensure_region_item()
            if self._region_item is not None:
                self._region_item.setRegion((min_disp, max_disp))
        except Exception:
            pass

    def _ensure_region_item(self) -> None:
        """Create the region item if it doesn't exist."""
        if self._region_item is not None:
            return
        # Default region: center 50% of current view
        try:
            x_range, _ = self._plot.viewRange()
            x_min, x_max = x_range
            span = x_max - x_min
            center = (x_min + x_max) / 2
            region_min = center - span * 0.25
            region_max = center + span * 0.25
        except Exception:
            region_min, region_max = 400, 700  # Default nm range
            region_min = self.map_nm_to_display(region_min)
            region_max = self.map_nm_to_display(region_max)
        
        self._region_item = pg.LinearRegionItem(
            values=(region_min, region_max),
            brush=pg.mkBrush(100, 100, 255, 50),
            pen=pg.mkPen(100, 100, 255, 200),
            hoverBrush=pg.mkBrush(100, 100, 255, 80),
            hoverPen=pg.mkPen(100, 100, 255, 255),
        )
        self._region_item.sigRegionChangeFinished.connect(self._on_region_changed)
        self._plot.addItem(self._region_item)
        self._region_item.setVisible(self._region_visible)

    def _on_region_changed(self) -> None:
        """Handle region selection changes."""
        if self._region_item is None:
            return
        region = self.get_selected_region_nm()
        if region is not None:
            self.regionSelected.emit(region[0], region[1])

    def _disp_to_x_nm(self, x_disp: float) -> float:
        """Convert display coordinate back to canonical nm."""
        if self._x_mode != "wavelength":
            return x_disp
        unit = self._display_unit
        if unit == "nm":
            return x_disp
        if unit == "Å":
            return x_disp / 10.0
        if unit == "µm":
            return x_disp * 1000.0
        if unit == "cm⁻¹":
            if x_disp <= 0:
                return float('inf')
            return 1e7 / x_disp
        return x_disp

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

    def set_title_visible(self, visible: bool) -> None:
        """Show or hide the plot title."""

        self._title_visible = bool(visible)
        self._update_title()

    def is_title_visible(self) -> bool:
        """Return True when the plot title is visible."""

        return self._title_visible

    def set_axis_label_font_size(self, size: str) -> None:
        """Set the font size for axis labels (e.g., '12pt', '14pt', '16pt')."""

        self._axis_label_font_size = size
        self._update_axis_labels()

    def set_title_font_size(self, size: str) -> None:
        """Set the font size for the plot title (e.g., '14pt', '16pt', '18pt')."""

        self._title_font_size = size
        self._update_title()

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
        # NOTE: Performance options like setClipToView and setDownsampling cause crashes 
        # in pyqtgraph 0.13.7 with autoRangeEnabled errors - using manual downsampling only
        self._plot.showGrid(x=False, y=False, alpha=0.2)
        self._vb: pg.ViewBox = self._plot.getPlotItem().getViewBox()
        self._plot.sigRangeChanged.connect(self._on_plot_range_changed)
        
        # Add annotation items to the ViewBox's context menu (keep pyqtgraph's menu)
        self._add_annotation_menu_items()
        self._last_click_pos: tuple[float, float] | None = None  # Store last click position in nm

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
            rateLimit=60,  # Back to 60Hz for smooth hover feedback
            slot=self._on_mouse_move,
        )

        layout.addWidget(self._plot)

        # Set initial axis labels with font sizing
        self._update_axis_labels()
        for axis in ("bottom", "left"):
            axis_item = self._plot.getPlotItem().getAxis(axis)
            if hasattr(axis_item, "enableAutoSIPrefix"):
                axis_item.enableAutoSIPrefix(False)

    def _add_annotation_menu_items(self) -> None:
        """Add annotation actions to the ViewBox's context menu."""
        menu = self._vb.menu
        if menu is None:
            return
        
        # Add separator before our items
        menu.addSeparator()
        
        # Create a submenu for notes
        notes_menu = menu.addMenu("Notes")
        
        # Add note action - will emit signal with current mouse position
        add_note_action = notes_menu.addAction("Add Note Here...")
        add_note_action.triggered.connect(self._on_add_note_here)
        
        # Add range note action
        self._add_range_note_action = notes_menu.addAction("Add Note for Selected Range...")
        self._add_range_note_action.triggered.connect(self._on_add_range_note)
        self._add_range_note_action.setEnabled(False)  # Enabled when region is visible
        
        # Delete nearest note action
        self._delete_note_action = notes_menu.addAction("Delete Nearest Note")
        self._delete_note_action.triggered.connect(self._on_delete_nearest_note)
        self._delete_note_action.setEnabled(False)  # Enabled when notes exist
        
        notes_menu.addSeparator()
        
        # Toggle range selection
        self._toggle_range_action = notes_menu.addAction("Enable Range Selection")
        self._toggle_range_action.triggered.connect(self._on_toggle_range_selection)
        
        notes_menu.addSeparator()
        
        # Rescale notes to fit current view (for after normalization)
        self._rescale_notes_action = notes_menu.addAction("Fit Notes to View")
        self._rescale_notes_action.triggered.connect(self._on_rescale_notes_to_view)
        self._rescale_notes_action.setEnabled(False)
        
        # Toggle visibility
        self._toggle_notes_action = notes_menu.addAction("Hide All Notes")
        self._toggle_notes_action.triggered.connect(self._on_toggle_notes)
        
        # Store the menu to update items dynamically
        self._notes_menu = notes_menu
        
        # Connect to aboutToShow to update menu state
        menu.aboutToShow.connect(self._update_notes_menu_state)

    def _update_notes_menu_state(self) -> None:
        """Update notes menu items based on current state."""
        # Update delete/rescale based on whether notes exist
        has_notes = len(self._annotations) > 0
        if hasattr(self, '_delete_note_action'):
            self._delete_note_action.setEnabled(has_notes)
        if hasattr(self, '_rescale_notes_action'):
            self._rescale_notes_action.setEnabled(has_notes)
        
        # Update range note action
        if hasattr(self, '_add_range_note_action'):
            self._add_range_note_action.setEnabled(self._region_visible)
        
        # Update range selection toggle text
        if hasattr(self, '_toggle_range_action'):
            if self._region_visible:
                self._toggle_range_action.setText("Disable Range Selection")
            else:
                self._toggle_range_action.setText("Enable Range Selection")
        
        # Update toggle text
        if hasattr(self, '_toggle_notes_action'):
            if self._annotations_visible:
                self._toggle_notes_action.setText("Hide All Notes")
            else:
                self._toggle_notes_action.setText("Show All Notes")
        
        # Store current mouse position for "Add Note Here"
        try:
            cursor_pos = QtGui.QCursor.pos()
            # Map global -> widget viewport coordinates
            widget_pos = self._plot.mapFromGlobal(cursor_pos)
            # Map widget viewport -> scene coordinates (PlotWidget is a QGraphicsView)
            scene_pos = self._plot.mapToScene(widget_pos)
            # Map scene -> view/data coordinates
            view_pos = self._vb.mapSceneToView(scene_pos)
            x_disp = view_pos.x()
            x_nm = self._disp_to_x_nm(x_disp)
            # Convert Y to fraction of view range (0=bottom, 1=top)
            try:
                (_, y_range) = self.view_range()
                y0, y1 = float(y_range[0]), float(y_range[1])
                if y1 != y0:
                    y_fraction = (view_pos.y() - y0) / (y1 - y0)
                else:
                    y_fraction = 0.9  # Default near top
            except Exception:
                y_fraction = 0.9
            self._last_click_pos = (x_nm, y_fraction)
        except Exception:
            self._last_click_pos = None

    def _on_add_note_here(self) -> None:
        """Handle 'Add Note Here' action."""
        if self._last_click_pos:
            x_nm, y_fraction = self._last_click_pos
            self.annotationRequested.emit(x_nm, y_fraction, None)

    def _on_add_range_note(self) -> None:
        """Handle 'Add Note for Selected Range' action."""
        if self._region_visible and self._last_click_pos:
            region_nm = self.get_selected_region_nm()
            if region_nm:
                _, y_fraction = self._last_click_pos
                self.annotationRequested.emit(region_nm[0], y_fraction, region_nm[1])

    def _on_toggle_notes(self) -> None:
        """Toggle all notes visibility."""
        self.set_all_annotations_visible(not self._annotations_visible)

    def _on_delete_nearest_note(self) -> None:
        """Delete the note nearest to the click position."""
        if not self._last_click_pos or not self._annotations:
            return
        
        click_x_nm, click_y = self._last_click_pos
        
        # Find nearest annotation by X position (in nm)
        nearest_id = None
        nearest_dist = float('inf')
        
        for ann_id, entry in self._annotations.items():
            ann: Annotation = entry['annotation']
            # Calculate distance (primarily by X, with some Y consideration)
            x_dist = abs(ann.x_nm - click_x_nm)
            if x_dist < nearest_dist:
                nearest_dist = x_dist
                nearest_id = ann_id
        
        if nearest_id:
            ann = self._annotations[nearest_id]['annotation']
            self.remove_annotation(nearest_id)

    def _on_rescale_notes_to_view(self) -> None:
        """Rescale all note Y positions to fit within current view."""
        if not self._annotations:
            return
        
        try:
            (_, y_range) = self.view_range()
            y0, y1 = float(y_range[0]), float(y_range[1])
            y_span = y1 - y0
            
            # Position notes in the upper portion of the view
            # Spread them out if there are multiple
            visible_notes = [
                (ann_id, entry) for ann_id, entry in self._annotations.items()
                if entry['annotation'].visible
            ]
            
            if not visible_notes:
                return
            
            # Sort by X position
            visible_notes.sort(key=lambda x: x[1]['annotation'].x_nm)
            
            # Assign Y positions in upper 20% of view, staggered
            for i, (ann_id, entry) in enumerate(visible_notes):
                ann: Annotation = entry['annotation']
                # Stagger between 85% and 95% of view height
                y_frac = 0.85 + (i % 3) * 0.05
                ann.y_fraction = y_frac
                
                # Update visual position
                new_y = y0 + y_span * y_frac
                x_disp = self._x_nm_to_disp(np.array([ann.x_nm]))[0]
                if ann.x_max_nm is not None:
                    x_max_disp = self._x_nm_to_disp(np.array([ann.x_max_nm]))[0]
                    x_disp = (min(x_disp, x_max_disp) + max(x_disp, x_max_disp)) / 2
                entry['text'].setPos(x_disp, new_y)
        except Exception:
            pass

    def _on_toggle_range_selection(self) -> None:
        """Toggle range selection visibility from context menu."""
        new_visible = not self._region_visible
        self.set_region_visible(new_visible)
        # If enabling, set initial region to center of current view
        if new_visible:
            try:
                (x_range, _) = self.view_range()
                x0, x1 = float(x_range[0]), float(x_range[1])
                # Convert display range to nm
                x0_nm = self._disp_to_x_nm(x0)
                x1_nm = self._disp_to_x_nm(x1)
                # Set region to middle 50% of view
                margin = (x1_nm - x0_nm) * 0.25
                self.set_region_nm(x0_nm + margin, x1_nm - margin)
            except Exception:
                pass

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
        
        # Update annotation Y positions to stay near top of view
        self._refresh_annotation_positions()

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
        if self._x_mode != "wavelength":
            return np.array(x_nm, copy=True)
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
        # Store region in nm before redraw (units may be changing)
        region_nm = self.get_selected_region_nm() if self._region_visible else None
        
        for key in self._traces:
            self._update_curve(key)
        self._update_axis_labels()
        self._update_title()
        
        # Restore region in new display units
        if region_nm is not None:
            self.set_region_nm(region_nm[0], region_nm[1])
        
        # Refresh annotation positions for new display units
        self._refresh_annotation_positions()

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

    def _update_axis_labels(self) -> None:
        """Update axis labels with current units and font size."""

        bottom_label, bottom_unit = self._bottom_axis_text()
        label_style = {"font-size": self._axis_label_font_size}
        self._plot.setLabel("bottom", bottom_label, units=bottom_unit, **label_style)
        # Use custom y-axis label if set, otherwise default
        y_label = self._custom_y_label or self._y_label
        self._plot.setLabel("left", y_label, **label_style)

    def _bottom_axis_text(self) -> tuple[str, str | None]:
        if self._x_mode == "wavelength":
            return ("Wavenumber" if self._display_unit == "cm⁻¹" else "Wavelength", self._display_unit)
        label = self._custom_x_label or "Time"
        unit = self._custom_x_unit if self._custom_x_unit is not None else self._display_unit
        return (label, unit)

    def _update_title(self) -> None:
        """Update plot title based on current y_label and visibility."""

        if not self._title_visible:
            self._plot.setTitle("", size=self._title_font_size)
            return

        # Use custom title if set
        if self._custom_title:
            self._plot.setTitle(self._custom_title, size=self._title_font_size)
            return

        # Generate intelligent title based on y_label
        y_lower = self._y_label.lower()
        if "intensity" in y_lower:
            title = "Spectral Intensity"
        elif "absorbance" in y_lower:
            title = "Absorbance Spectrum"
        elif "transmittance" in y_lower:
            title = "Transmittance Spectrum"
        elif "reflectance" in y_lower:
            title = "Reflectance Spectrum"
        elif "flux" in y_lower:
            title = "Spectral Flux"
        elif "radiance" in y_lower:
            title = "Spectral Radiance"
        else:
            # Generic fallback
            title = "Spectral Data"

        self._plot.setTitle(title, size=self._title_font_size)

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
        # Ensure colours are correct immediately after building
        self._apply_legend_theme_style()
    
    def _update_legend_item(self, key: str) -> None:
        """Update a single legend item without rebuilding the entire legend."""
        trace = self._traces.get(key)
        if not trace:
            return
        
        item: pg.PlotDataItem = trace["item"]  # type: ignore[assignment]
        style: TraceStyle = trace["style"]  # type: ignore[assignment]
        visible = bool(trace.get("visible", True))
        
        # Remove item from legend if it exists
        try:
            self._legend.removeItem(item)
        except Exception:
            pass
        
        # Add back if it should be visible
        if visible and style.show_in_legend:
            alias = trace.get("alias", key)
            self._legend.addItem(item, str(alias))
        # Restyle labels so colours are correct without further interaction
        self._apply_legend_theme_style()

    def _on_mouse_move(self, event) -> None:
        """Handle mouse movement (rate-limited by SignalProxy to 60 Hz)."""
        # If crosshair is hidden, skip work entirely (also suppress hover emits)
        if not self._crosshair_visible:
            return

        pos = event[0]
        if not self._plot.sceneBoundingRect().contains(pos):
            return

        # Skip tiny movements (<5px) to reduce redraw churn on large scenes
        try:
            last = getattr(self, "_last_mouse_scene_pos", None)
            if last is not None and (pos - last).manhattanLength() < 5:
                return
            self._last_mouse_scene_pos = pos
        except Exception:
            pass

        mapped = self._plot.getPlotItem().vb.mapSceneToView(pos)
        # Update crosshair and emit hover signal (both already rate-limited by SignalProxy)
        self._vline.setPos(mapped.x())
        self._hline.setPos(mapped.y())
        self.pointHovered.emit(mapped.x(), mapped.y())

    def begin_bulk_update(self) -> None:
        self._plot.setUpdatesEnabled(False)

    def end_bulk_update(self) -> None:
        """End bulk update mode and re-enable plot updates.

        Note: Does not autoscale automatically. User can manually autoscale
        using Ctrl+F or the Autoscale button.
        """
        self._plot.setUpdatesEnabled(True)

    # ---- Legend theming -------------------------------------------------
    def _apply_legend_theme_style(self) -> None:
        """Apply panel, border, and text colours to the legend.

        This is called from apply_theme and after legend rebuilds so that
        startup and first-add both look correct without requiring user input.
        """
        if pg is None or self._legend is None:
            return
        try:
            # Panel brush with a slightly opaque fill to stand off from canvas
            panel = getattr(self, "_legend_panel_color", None)
            border = getattr(self, "_legend_border_color", None)
            text = getattr(self, "_legend_text_color", None)
            if isinstance(panel, QtGui.QColor):
                c = QtGui.QColor(panel)
                if c.alpha() == 255:
                    # Make it slightly translucent to contrast on white canvases
                    c.setAlpha(230)
                self._legend.setBrush(pg.mkBrush(c))
            if isinstance(border, QtGui.QColor):
                self._legend.setPen(pg.mkPen(border))
            if isinstance(text, QtGui.QColor):
                if hasattr(self._legend, "setLabelTextColor"):
                    self._legend.setLabelTextColor(text)
                for _sample, label in getattr(self._legend, "items", []) or []:
                    try:
                        if hasattr(label, "setDefaultTextColor"):
                            label.setDefaultTextColor(text)
                    except Exception:
                        pass
        except Exception:
            pass
    @staticmethod
    def palette_definitions() -> Sequence[PaletteDefinition]:
        """Expose the shared palette registry to callers."""

        return list(load_palette_definitions())

    @staticmethod
    def default_palette_key() -> str:
        """Return the key of the palette used for new sessions."""

        return DEFAULT_PALETTE_KEY


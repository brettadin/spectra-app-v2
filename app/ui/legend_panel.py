"""Legend panel: displays dataset legend in a compact horizontal layout."""
from __future__ import annotations

from typing import Optional

from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()

# Get Signal/Slot compatible with both PySide6 and PyQt6
Signal = getattr(QtCore, "Signal", None)  # type: ignore[attr-defined]
if Signal is None:
    Signal = getattr(QtCore, "pyqtSignal")  # type: ignore[attr-defined]


class LegendPanel(QtWidgets.QWidget):
    """Compact legend panel for bottom dock showing dataset colors and names.

    Displays datasets in a horizontal flow layout with color swatches.
    Clicking a legend item can toggle dataset visibility.

    Signals:
        legendItemClicked(str): Emitted when a legend item is clicked (dataset_id)
    """

    legendItemClicked = Signal(str)  # dataset_id

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._legend_items: dict[str, QtWidgets.QLabel] = {}  # dataset_id -> QLabel
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the legend panel UI."""
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # Scroll area for horizontal scrolling when many datasets
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll_area.setMaximumHeight(40)

        # Container widget for legend items
        self.legend_container = QtWidgets.QWidget()
        self.legend_layout = QtWidgets.QHBoxLayout(self.legend_container)
        self.legend_layout.setContentsMargins(0, 0, 0, 0)
        self.legend_layout.setSpacing(12)
        self.legend_layout.addStretch(1)  # Push items to the left

        scroll_area.setWidget(self.legend_container)
        layout.addWidget(scroll_area)

    def add_legend_item(self, dataset_id: str, name: str, color: QtGui.QColor, visible: bool = True) -> None:
        """Add or update a legend item.

        Args:
            dataset_id: Unique dataset identifier
            name: Display name
            color: Dataset color
            visible: Whether dataset is currently visible
        """
        # Remove existing item if present
        if dataset_id in self._legend_items:
            self.remove_legend_item(dataset_id)

        # Create color swatch (16x16 square)
        swatch = QtGui.QPixmap(16, 16)
        swatch.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(swatch)
        try:
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 180), 1))
            painter.setBrush(QtGui.QBrush(color))
            painter.drawRect(0, 0, 15, 15)
        finally:
            painter.end()

        # Create label with icon and text
        label = QtWidgets.QLabel()
        label.setPixmap(swatch)
        label.setText(f" {name}")
        label.setToolTip(f"{name}\nClick to toggle visibility")
        label.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        label.setStyleSheet(f"""
            QLabel {{
                color: {color.name()};
                font-weight: 500;
                padding: 2px 6px;
                border-radius: 3px;
            }}
            QLabel:hover {{
                background: rgba(255, 255, 255, 0.1);
            }}
        """)

        # Make clickable
        label.mousePressEvent = lambda event, did=dataset_id: self._on_item_clicked(did)

        # Add to layout (before the stretch)
        insert_pos = self.legend_layout.count() - 1  # Before stretch
        self.legend_layout.insertWidget(insert_pos, label)
        self._legend_items[dataset_id] = label

        # Apply visibility styling
        self._update_item_visibility_style(dataset_id, visible)

    def remove_legend_item(self, dataset_id: str) -> None:
        """Remove a legend item by dataset ID."""
        if dataset_id in self._legend_items:
            label = self._legend_items.pop(dataset_id)
            self.legend_layout.removeWidget(label)
            label.deleteLater()

    def update_item_visibility(self, dataset_id: str, visible: bool) -> None:
        """Update the visual styling of a legend item based on visibility."""
        self._update_item_visibility_style(dataset_id, visible)

    def _update_item_visibility_style(self, dataset_id: str, visible: bool) -> None:
        """Apply opacity styling based on visibility state."""
        if dataset_id in self._legend_items:
            label = self._legend_items[dataset_id]
            opacity = 1.0 if visible else 0.4
            effect = QtWidgets.QGraphicsOpacityEffect()
            effect.setOpacity(opacity)
            label.setGraphicsEffect(effect)

    def clear(self) -> None:
        """Remove all legend items."""
        for dataset_id in list(self._legend_items.keys()):
            self.remove_legend_item(dataset_id)

    def _on_item_clicked(self, dataset_id: str) -> None:
        """Handle legend item click."""
        self.legendItemClicked.emit(dataset_id)

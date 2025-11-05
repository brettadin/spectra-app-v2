"""Application-wide stylesheet helpers.

Provides a modern dark theme with subtle accents that works across Qt bindings.
"""
from __future__ import annotations

from typing import Optional


def get_app_stylesheet(accent: str = "#4FC3F7") -> str:
    """Return the QSS stylesheet string for the application.

    Parameters
    ----------
    accent: Hex color for highlights (default a soft cyan)
    """
    # Base palette
    bg0 = "#1e1e1e"
    bg1 = "#252526"
    bg2 = "#2d2d30"
    fg0 = "#e0e0e0"
    fg_dim = "#bdbdbd"
    border = "#3c3c3c"

    return f"""
    QWidget {{
        background: {bg0};
        color: {fg0};
        selection-background-color: {accent};
    }}

    QDockWidget::title {{
        background: {bg1};
        padding: 6px 8px;
        border-bottom: 1px solid {border};
        font-weight: 600;
    }}

    QToolBar {{
        background: {bg1};
        border: 0px;
        padding: 4px;
        spacing: 6px;
    }}
    QToolButton {{
        padding: 4px 6px;
        border-radius: 4px;
    }}
    QToolButton:hover {{
        background: {bg2};
    }}
    QToolButton:pressed {{
        background: {accent};
        color: #000;
    }}
    QToolButton:checked {
        background: {accent};
        color: #000;
        border: 1px solid #000;
    }

    QLineEdit {{
        background: {bg2};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 4px 6px;
        color: {fg0};
    }}
    QLineEdit:focus {{
        border: 1px solid {accent};
    }}

    QComboBox, QSpinBox {{
        background: {bg2};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 2px 6px;
        color: {fg0};
    }}

    /* High-contrast checkboxes */
    QCheckBox::indicator {
        width: 14px; height: 14px;
        border: 1px solid {border};
        background: {bg2};
    }
    QCheckBox::indicator:checked {
        background: {accent};
        border: 1px solid #000;
    }
    QCheckBox::indicator:unchecked:hover {
        border: 1px solid {accent};
    }

    QTreeView, QTableWidget, QTableView {{
        background: {bg1};
        alternate-background-color: {bg2};
        gridline-color: {border};
        selection-background-color: {accent};
        selection-color: #000;
    }}
    QHeaderView::section {{
        background: {bg2};
        padding: 6px;
        border: 0px;
        border-bottom: 1px solid {border};
        color: {fg_dim};
    }}

    QLabel#status {{ color: {fg_dim}; }}
    """.strip()


def apply_pyqtgraph_theme() -> None:
    """Set a matching theme for pyqtgraph plots."""
    try:
        import pyqtgraph as pg  # type: ignore
        pg.setConfigOption("background", "#1e1e1e")
        pg.setConfigOption("foreground", "#e0e0e0")
        pg.setConfigOption("antialias", True)
    except Exception:
        pass

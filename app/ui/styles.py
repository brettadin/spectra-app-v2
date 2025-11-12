"""Application-wide stylesheet helpers and pyqtgraph configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import overload

from app.ui.themes import ThemeDefinition, get_theme_definition


@overload
def get_app_stylesheet(theme: ThemeDefinition) -> str:
    ...


@overload
def get_app_stylesheet(theme: str | None = None) -> str:
    ...


@lru_cache(maxsize=None)
def get_app_stylesheet(theme: ThemeDefinition | str | None = None) -> str:
    """Return the QSS stylesheet string for ``theme``."""

    theme_def = theme if isinstance(theme, ThemeDefinition) else get_theme_definition(theme)
    palette = theme_def.palette
    accent = palette.accent
    accent_text = palette.accent_text

    return f"""
    QWidget {{
        background: {palette.window};
        color: {palette.text};
        selection-background-color: {accent};
        selection-color: {accent_text};
    }}

    QDockWidget::title {{
        background: {palette.panel};
        padding: 6px 8px;
        border-bottom: 1px solid {palette.border};
        font-weight: 600;
    }}

    QToolBar {{
        background: {palette.panel};
        border: 0px;
        padding: 4px;
        spacing: 6px;
    }}
    QToolButton {{
        padding: 4px 6px;
        border-radius: 4px;
    }}
    QToolButton:hover {{
        background: {palette.panel_alt};
    }}
    QToolButton:pressed {{
        background: {accent};
        color: {accent_text};
    }}
    QToolButton:checked {{
        background: {accent};
        color: {accent_text};
        border: 1px solid {accent_text};
    }}

    QLineEdit {{
        background: {palette.raised};
        border: 1px solid {palette.border};
        border-radius: 4px;
        padding: 4px 6px;
        color: {palette.text};
    }}
    QLineEdit:focus {{
        border: 1px solid {accent};
    }}

    QComboBox, QSpinBox {{
        background: {palette.raised};
        border: 1px solid {palette.border};
        border-radius: 4px;
        padding: 2px 6px;
        color: {palette.text};
    }}

    /* High-contrast checkboxes */
    QCheckBox::indicator {
        width: 14px; height: 14px;
        border: 1px solid {palette.border};
        background: {palette.raised};
    }
    QCheckBox::indicator:checked {
        background: {accent};
        border: 1px solid {accent_text};
    }
    QCheckBox::indicator:unchecked:hover {
        border: 1px solid {accent};
    }

    QTreeView, QTableWidget, QTableView {{
        background: {palette.panel};
        alternate-background-color: {palette.panel_alt};
        gridline-color: {palette.border};
        selection-background-color: {accent};
        selection-color: {accent_text};
    }}
    QHeaderView::section {{
        background: {palette.panel_alt};
        padding: 6px;
        border: 0px;
        border-bottom: 1px solid {palette.border};
        color: {palette.text_dim};
    }}

    QLabel#status {{ color: {palette.text_dim}; }}
    """.strip()


def apply_pyqtgraph_theme(theme: ThemeDefinition | str | None = None) -> None:
    """Set pyqtgraph globals for ``theme``."""

    theme_def = theme if isinstance(theme, ThemeDefinition) else get_theme_definition(theme)
    palette = theme_def.palette
    try:
        import pyqtgraph as pg  # type: ignore

        pg.setConfigOption("background", palette.plot_background)
        pg.setConfigOption("foreground", palette.plot_foreground)
        # Disable global antialiasing for performance with large datasets
        pg.setConfigOption("antialias", False)
        # Enable OpenGL for hardware-accelerated rendering if available
        pg.setConfigOption("useOpenGL", True)
        pg.setConfigOption("enableExperimental", False)
    except Exception:
        pass

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
    /* Base widget styling with improved depth */
    QWidget {{
        background: {palette.window};
        color: {palette.text};
        selection-background-color: {accent};
        selection-color: {accent_text};
        font-size: 9pt;
    }}

    /* Dock widget titles - professional header style */
    QDockWidget::title {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {palette.panel_alt}, stop:1 {palette.panel});
        padding: 8px 12px;
        border-bottom: 2px solid {palette.border};
        font-weight: 600;
        font-size: 10pt;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* Toolbar - clean and organized */
    QToolBar {{
        background: {palette.panel};
        border: none;
        border-bottom: 1px solid {palette.border};
        padding: 6px 8px;
        spacing: 8px;
    }}

    QToolButton {{
        background: {palette.raised};
        border: 1px solid {palette.border};
        border-radius: 4px;
        padding: 6px 10px;
        font-weight: 500;
    }}
    QToolButton:hover {{
        background: {palette.panel_alt};
        border: 1px solid {accent};
    }}
    QToolButton:pressed {{
        background: {accent};
        color: {accent_text};
        border: 1px solid {accent};
    }}
    QToolButton:checked {{
        background: {accent};
        color: {accent_text};
        border: 1px solid {accent};
        font-weight: 600;
    }}

    /* Push buttons - modern, clean style */
    QPushButton {{
        background: {palette.raised};
        border: 1px solid {palette.border};
        border-radius: 4px;
        padding: 6px 16px;
        font-weight: 500;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background: {palette.panel_alt};
        border: 1px solid {accent};
    }}
    QPushButton:pressed {{
        background: {accent};
        color: {accent_text};
        border: 1px solid {accent};
    }}
    QPushButton:disabled {{
        background: {palette.panel};
        color: {palette.text_dim};
        border: 1px solid {palette.border};
    }}

    /* Text inputs - clean and focused */
    QLineEdit {{
        background: {palette.raised};
        border: 1px solid {palette.border};
        border-radius: 4px;
        padding: 6px 10px;
        color: {palette.text};
        selection-background-color: {accent};
    }}
    QLineEdit:focus {{
        border: 2px solid {accent};
        padding: 5px 9px;  /* Compensate for thicker border */
    }}
    QLineEdit:disabled {{
        background: {palette.panel};
        color: {palette.text_dim};
    }}

    /* Combo boxes and spin boxes */
    QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {palette.raised};
        border: 1px solid {palette.border};
        border-radius: 4px;
        padding: 4px 8px;
        color: {palette.text};
    }}
    QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
        border: 1px solid {accent};
    }}
    QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 2px solid {accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    /* High-contrast checkboxes with better visuals */
    QCheckBox {{
        spacing: 6px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {palette.border};
        border-radius: 3px;
        background: {palette.raised};
    }}
    QCheckBox::indicator:checked {{
        background: {accent};
        border: 2px solid {accent};
        image: none;  /* Use solid fill instead of checkmark */
    }}
    QCheckBox::indicator:unchecked:hover {{
        border: 2px solid {accent};
    }}
    QCheckBox::indicator:disabled {{
        background: {palette.panel};
        border: 2px solid {palette.border};
    }}

    /* Tree and table views - improved spacing */
    QTreeView, QTableWidget, QTableView, QListWidget {{
        background: {palette.panel};
        alternate-background-color: {palette.panel_alt};
        gridline-color: {palette.border};
        border: 1px solid {palette.border};
        border-radius: 4px;
        selection-background-color: {accent};
        selection-color: {accent_text};
        padding: 4px;
    }}
    QTreeView::item, QTableWidget::item, QListWidget::item {{
        padding: 4px 8px;
        border: none;
    }}
    QTreeView::item:hover, QTableWidget::item:hover, QListWidget::item:hover {{
        background: {palette.panel_alt};
    }}
    QTreeView::item:selected, QTableWidget::item:selected, QListWidget::item:selected {{
        background: {accent};
        color: {accent_text};
    }}

    /* Header views - cleaner look */
    QHeaderView::section {{
        background: {palette.panel_alt};
        padding: 8px 12px;
        border: none;
        border-right: 1px solid {palette.border};
        border-bottom: 2px solid {palette.border};
        color: {palette.text};
        font-weight: 600;
        font-size: 9pt;
    }}
    QHeaderView::section:hover {{
        background: {palette.raised};
    }}

    /* Tab widgets - modern tab style */
    QTabWidget::pane {{
        border: 1px solid {palette.border};
        border-radius: 4px;
        background: {palette.panel};
        padding: 4px;
    }}
    QTabBar::tab {{
        background: {palette.panel_alt};
        border: 1px solid {palette.border};
        border-bottom: none;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        font-weight: 500;
    }}
    QTabBar::tab:selected {{
        background: {palette.panel};
        border-bottom: 2px solid {accent};
        font-weight: 600;
    }}
    QTabBar::tab:hover {{
        background: {palette.raised};
    }}

    /* Group boxes - subtle containers */
    QGroupBox {{
        border: 1px solid {palette.border};
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 8px;
        background: {palette.panel};
        color: {palette.text};
    }}

    /* Scroll bars - clean and minimal */
    QScrollBar:vertical {{
        background: {palette.panel};
        width: 12px;
        border: none;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {palette.raised};
        min-height: 30px;
        border-radius: 4px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {accent};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: {palette.panel};
        height: 12px;
        border: none;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {palette.raised};
        min-width: 30px;
        border-radius: 4px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {accent};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* Splitters - better visibility */
    QSplitter::handle {{
        background: {palette.border};
        width: 3px;
        height: 3px;
    }}
    QSplitter::handle:hover {{
        background: {accent};
    }}

    /* Menu styling */
    QMenuBar {{
        background: {palette.panel};
        border-bottom: 1px solid {palette.border};
        padding: 2px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 6px 12px;
        border-radius: 4px;
    }}
    QMenuBar::item:selected {{
        background: {palette.panel_alt};
    }}

    QMenu {{
        background: {palette.panel};
        border: 1px solid {palette.border};
        border-radius: 6px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 6px 24px 6px 12px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background: {accent};
        color: {accent_text};
    }}
    QMenu::separator {{
        height: 1px;
        background: {palette.border};
        margin: 4px 8px;
    }}

    /* Status bar - sleek bottom bar */
    QStatusBar {{
        background: {palette.panel};
        border-top: 1px solid {palette.border};
        color: {palette.text_dim};
        padding: 4px 8px;
    }}

    /* Progress bars - modern style */
    QProgressBar {{
        background: {palette.raised};
        border: 1px solid {palette.border};
        border-radius: 4px;
        text-align: center;
        height: 16px;
    }}
    QProgressBar::chunk {{
        background: {accent};
        border-radius: 3px;
    }}

    /* Tool tips - clean popups */
    QToolTip {{
        background: {palette.raised};
        border: 1px solid {accent};
        border-radius: 4px;
        padding: 6px 10px;
        color: {palette.text};
        opacity: 240;
    }}

    /* Special label styling */
    QLabel#status {{
        color: {palette.text_dim};
        font-style: italic;
    }}
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

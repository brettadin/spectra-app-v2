"""Enhanced application stylesheet with vibrant crypto terminal aesthetic."""

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
    """Return the QSS stylesheet string for ``theme`` with vibrant crypto aesthetic."""

    theme_def = theme if isinstance(theme, ThemeDefinition) else get_theme_definition(theme)
    palette = theme_def.palette
    accent = palette.accent
    accent_text = palette.accent_text

    # Create a dimmer version of accent for subtle glows
    accent_glow = f"{accent}40"  # 40 = 25% opacity in hex

    return f"""
    /* Base widget styling with depth and glow */
    QWidget {{
        background: {palette.window};
        color: {palette.text};
        selection-background-color: {accent};
        selection-color: {accent_text};
        font-size: 9pt;
        font-family: "Segoe UI", "Inter", "SF Pro", sans-serif;
    }}

    /* Dock widget titles - premium header with accent underline */
    QDockWidget::title {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {palette.panel_alt}, stop:1 {palette.panel});
        padding: 10px 14px;
        border-bottom: 2px solid {accent};
        font-weight: 600;
        font-size: 10pt;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* Toolbar - sleek command bar */
    QToolBar {{
        background: {palette.panel};
        border: none;
        border-bottom: 1px solid {accent_glow};
        padding: 8px;
        spacing: 10px;
    }}

    QToolButton {{
        background: {palette.raised};
        border: 1px solid {palette.border};
        border-radius: 6px;
        padding: 8px 12px;
        font-weight: 500;
        min-width: 32px;
        min-height: 32px;
    }}
    QToolButton:hover {{
        background: {palette.panel_alt};
        border: 2px solid {accent};
        padding: 7px 11px;  /* Compensate for thicker border */
    }}
    QToolButton:pressed {{
        background: {accent};
        color: {accent_text};
        border: 2px solid {accent};
        font-weight: 600;
    }}
    QToolButton:checked {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {accent}, stop:1 {palette.raised});
        color: {accent_text};
        border: 2px solid {accent};
        font-weight: 600;
    }}

    /* Push buttons - high-tech style with glow on hover */
    QPushButton {{
        background: {palette.raised};
        border: 1px solid {palette.border};
        border-radius: 6px;
        padding: 8px 20px;
        font-weight: 500;
        min-height: 24px;
    }}
    QPushButton:hover {{
        background: {palette.panel_alt};
        border: 2px solid {accent};
        padding: 7px 19px;  /* Compensate for thicker border */
    }}
    QPushButton:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {accent}, stop:1 {palette.raised});
        color: {accent_text};
        border: 2px solid {accent};
        font-weight: 600;
    }}
    QPushButton:disabled {{
        background: {palette.panel};
        color: {palette.text_dim};
        border: 1px solid {palette.border};
    }}

    /* Text inputs - glowing focus states */
    QLineEdit {{
        background: {palette.raised};
        border: 1px solid {palette.border};
        border-radius: 5px;
        padding: 7px 11px;
        color: {palette.text};
        selection-background-color: {accent};
    }}
    QLineEdit:focus {{
        border: 2px solid {accent};
        padding: 6px 10px;  /* Compensate for thicker border */
        background: {palette.panel};
    }}
    QLineEdit:disabled {{
        background: {palette.panel};
        color: {palette.text_dim};
    }}

    /* Combo boxes and spin boxes - sleek dropdowns */
    QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {palette.raised};
        border: 1px solid {palette.border};
        border-radius: 5px;
        padding: 5px 10px;
        color: {palette.text};
        min-height: 22px;
    }}
    QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
        border: 2px solid {accent};
        padding: 4px 9px;  /* Compensate for thicker border */
    }}
    QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 2px solid {accent};
        background: {palette.panel};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {palette.text};
        width: 0;
        height: 0;
        margin-right: 8px;
    }}

    /* High-contrast checkboxes with pulsing accent */
    QCheckBox {{
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {palette.border};
        border-radius: 4px;
        background: {palette.raised};
    }}
    QCheckBox::indicator:checked {{
        background: {accent};
        border: 2px solid {accent};
        image: none;
    }}
    QCheckBox::indicator:unchecked:hover {{
        border: 2px solid {accent};
        background: {palette.panel_alt};
    }}
    QCheckBox::indicator:disabled {{
        background: {palette.panel};
        border: 2px solid {palette.border};
    }}

    /* Tree and table views - data grid with accent highlights */
    QTreeView, QTableWidget, QTableView, QListWidget {{
        background: {palette.panel};
        alternate-background-color: {palette.panel_alt};
        gridline-color: {palette.border};
        border: 1px solid {palette.border};
        border-radius: 5px;
        selection-background-color: {accent};
        selection-color: {accent_text};
        padding: 4px;
        outline: none;
    }}
    QTreeView::item, QTableWidget::item, QListWidget::item {{
        padding: 6px 10px;
        border: none;
        border-radius: 3px;
    }}
    QTreeView::item:hover, QTableWidget::item:hover, QListWidget::item:hover {{
        background: {palette.panel_alt};
        border-left: 3px solid {accent};
        padding-left: 7px;
    }}
    QTreeView::item:selected, QTableWidget::item:selected, QListWidget::item:selected {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 {accent}, stop:1 {palette.raised});
        color: {accent_text};
        font-weight: 600;
    }}

    /* Header views - premium table headers */
    QHeaderView::section {{
        background: {palette.panel_alt};
        padding: 10px 14px;
        border: none;
        border-right: 1px solid {palette.border};
        border-bottom: 2px solid {accent_glow};
        color: {palette.text};
        font-weight: 700;
        font-size: 9pt;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    QHeaderView::section:hover {{
        background: {palette.raised};
        border-bottom: 2px solid {accent};
    }}

    /* Tab widgets - modern navigation */
    QTabWidget::pane {{
        border: 1px solid {palette.border};
        border-radius: 6px;
        background: {palette.panel};
        padding: 6px;
    }}
    QTabBar::tab {{
        background: {palette.panel_alt};
        border: 1px solid {palette.border};
        border-bottom: none;
        padding: 10px 18px;
        margin-right: 3px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-weight: 500;
    }}
    QTabBar::tab:selected {{
        background: {palette.panel};
        border-bottom: 3px solid {accent};
        font-weight: 700;
        color{palette.text};
    }}
    QTabBar::tab:hover {{
        background: {palette.raised};
        border-bottom: 3px solid {accent_glow};
    }}

    /* Group boxes - elegant containers */
    QGroupBox {{
        border: 1px solid {palette.border};
        border-radius: 8px;
        margin-top: 14px;
        padding-top: 14px;
        font-weight: 600;
        background: {palette.panel};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 16px;
        padding: 0 10px;
        background: {palette.panel};
        color: {accent};
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* Scroll bars - minimal accent-highlighted */
    QScrollBar:vertical {{
        background: {palette.panel};
        width: 14px;
        border: none;
        border-radius: 7px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {palette.raised};
        min-height: 40px;
        border-radius: 6px;
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
        height: 14px;
        border: none;
        border-radius: 7px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {palette.raised};
        min-width: 40px;
        border-radius: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {accent};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* Splitters - accent on hover */
    QSplitter::handle {{
        background: {palette.border};
        width: 4px;
        height: 4px;
    }}
    QSplitter::handle:hover {{
        background: {accent};
    }}

    /* Menu styling - sleek dropdown */
    QMenuBar {{
        background: {palette.panel};
        border-bottom: 1px solid {accent_glow};
        padding: 4px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 8px 14px;
        border-radius: 5px;
    }}
    QMenuBar::item:selected {{
        background: {palette.panel_alt};
        border-bottom: 2px solid {accent};
    }}

    QMenu {{
        background: {palette.panel};
        border: 2px solid {accent};
        border-radius: 8px;
        padding: 8px;
    }}
    QMenu::item {{
        padding: 8px 28px 8px 14px;
        border-radius: 5px;
    }}
    QMenu::item:selected {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 {accent}, stop:1 {palette.raised});
        color: {accent_text};
    }}
    QMenu::separator {{
        height: 1px;
        background: {accent_glow};
        margin: 6px 10px;
    }}

    /* Status bar - info strip with accent */
    QStatusBar {{
        background: {palette.panel};
        border-top: 2px solid {accent_glow};
        color: {palette.text_dim};
        padding: 6px 10px;
        font-family: "Consolas", "Monaco", "Courier New", monospace;
    }}

    /* Progress bars - vibrant loading */
    QProgressBar {{
        background: {palette.raised};
        border: 1px solid {palette.border};
        border-radius: 8px;
        text-align: center;
        height: 20px;
        font-weight: 600;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 {accent}, stop:0.5 {palette.raised}, stop:1 {accent});
        border-radius: 7px;
    }}

    /* Tool tips - accent-bordered hints */
    QToolTip {{
        background: {palette.raised};
        border: 2px solid {accent};
        border-radius: 6px;
        padding: 8px 12px;
        color: {palette.text};
        opacity: 240;
        font-size: 9pt;
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

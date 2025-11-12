"""Theme definitions for the Spectra desktop shell."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ThemePalette:
    """Colour slots used by both Qt widgets and pyqtgraph plots."""

    window: str
    panel: str
    panel_alt: str
    raised: str
    text: str
    text_dim: str
    border: str
    accent: str
    accent_text: str
    plot_background: str
    plot_foreground: str


@dataclass(frozen=True)
class ThemeDefinition:
    """Describes a selectable application theme."""

    key: str
    label: str
    description: str
    palette: ThemePalette


@lru_cache(maxsize=1)
def load_theme_definitions() -> Sequence[ThemeDefinition]:
    """Return all theme definitions exposed to the UI."""

    return (
        ThemeDefinition(
            key="dark",
            label="Dark",
            description="High-contrast dark theme tuned for long sessions.",
            palette=ThemePalette(
                window="#1e1e1e",
                panel="#252526",
                panel_alt="#2d2d30",
                raised="#303033",
                text="#e0e0e0",
                text_dim="#bdbdbd",
                border="#3c3c3c",
                accent="#4FC3F7",
                accent_text="#000000",
                plot_background="#1e1e1e",
                plot_foreground="#f0f0f0",
            ),
        ),
        ThemeDefinition(
            key="light",
            label="Light",
            description="Bright theme for daylight or print review sessions.",
            palette=ThemePalette(
                window="#f5f5f5",
                panel="#ffffff",
                panel_alt="#f0f0f0",
                raised="#e8e8e8",
                text="#1b1b1b",
                text_dim="#4a4a4a",
                border="#d0d0d0",
                accent="#1f7a8c",
                accent_text="#ffffff",
                plot_background="#ffffff",
                plot_foreground="#1b1b1b",
            ),
        ),
        ThemeDefinition(
            key="midnight",
            label="Midnight",
            description="Ultra-dark theme with teal accents for lab environments.",
            palette=ThemePalette(
                window="#111827",
                panel="#16213c",
                panel_alt="#1f2a44",
                raised="#233055",
                text="#dbeafe",
                text_dim="#93c5fd",
                border="#1f2937",
                accent="#38bdf8",
                accent_text="#04111f",
                plot_background="#0b1220",
                plot_foreground="#dbeafe",
            ),
        ),
    )


def default_theme_key() -> str:
    """Return the key of the theme used for new installations."""

    return "dark"


def iter_theme_definitions() -> Iterable[ThemeDefinition]:
    """Yield all available theme definitions."""

    yield from load_theme_definitions()


def get_theme_definition(key: str | None) -> ThemeDefinition:
    """Resolve ``key`` to a known theme definition."""

    if key:
        for theme in load_theme_definitions():
            if theme.key == key:
                return theme
    # Fall back to the default theme
    for theme in load_theme_definitions():
        if theme.key == default_theme_key():
            return theme
    # Defensive fallback: return the first entry if the default is missing
    return load_theme_definitions()[0]

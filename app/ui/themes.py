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
            key="terminal",
            label="Terminal",
            description="Vibrant data terminal aesthetic with neon green accents.",
            palette=ThemePalette(
                window="#0a0e1a",
                panel="#0f1419",
                panel_alt="#151b28",
                raised="#1a2332",
                text="#e2e8f0",
                text_dim="#94a3b8",
                border="#1e293b",
                accent="#00ff88",  # Neon green
                accent_text="#000000",
                plot_background="#0a0e1a",
                plot_foreground="#e2e8f0",
            ),
        ),
        ThemeDefinition(
            key="magenta",
            label="Magenta Pulse",
            description="Deep purple theme with vibrant magenta highlights.",
            palette=ThemePalette(
                window="#0d0a14",
                panel="#15101f",
                panel_alt="#1d1429",
                raised="#251b35",
                text="#f0e6ff",
                text_dim="#b794f6",
                border="#2d1b4e",
                accent="#ff10f0",  # Bright magenta
                accent_text="#000000",
                plot_background="#0d0a14",
                plot_foreground="#f0e6ff",
            ),
        ),
        ThemeDefinition(
            key="amber",
            label="Amber Alert",
            description="Warm terminal theme with amber and orange accents.",
            palette=ThemePalette(
                window="#1a1108",
                panel="#211709",
                panel_alt="#2a1e0f",
                raised="#352616",
                text="#fff4e6",
                text_dim="#fbbf24",
                border="#4a3218",
                accent="#ff9500",  # Bright amber
                accent_text="#000000",
                plot_background="#1a1108",
                plot_foreground="#fff4e6",
            ),
        ),
        ThemeDefinition(
            key="cyan",
            label="Cyan Electric",
            description="Electric blue theme with bright cyan highlights.",
            palette=ThemePalette(
                window="#050f1a",
                panel="#0a1420",
                panel_alt="#0f1c2e",
                raised="#14233a",
                text="#e0f7ff",
                text_dim="#7dd3fc",
                border="#1e3a5f",
                accent="#00d9ff",  # Electric cyan
                accent_text="#000000",
                plot_background="#050f1a",
                plot_foreground="#e0f7ff",
            ),
        ),
        ThemeDefinition(
            key="hotpink",
            label="Pink Neon",
            description="Dark theme with hot pink neon accents.",
            palette=ThemePalette(
                window="#14050f",
                panel="#1f0a18",
                panel_alt="#2a0f20",
                raised="#35142a",
                text="#ffe6f7",
                text_dim="#f472b6",
                border="#4f1f3e",
                accent="#ff0080",  # Hot pink
                accent_text="#ffffff",
                plot_background="#14050f",
                plot_foreground="#ffe6f7",
            ),
        ),
        ThemeDefinition(
            key="emerald",
            label="Emerald Matrix",
            description="Matrix-inspired theme with emerald green accents.",
            palette=ThemePalette(
                window="#030f0a",
                panel="#081610",
                panel_alt="#0d1f17",
                raised="#12271e",
                text="#d1fae5",
                text_dim="#6ee7b7",
                border="#1e4d3a",
                accent="#10b981",  # Emerald green
                accent_text="#000000",
                plot_background="#030f0a",
                plot_foreground="#d1fae5",
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

    return "terminal"


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

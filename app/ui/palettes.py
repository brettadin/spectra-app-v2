"""Central palette registry shared by the plot pane and inspector."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class PaletteDefinition:
    """Describes a selectable colour palette for traces and dataset icons."""

    key: str
    label: str
    colors: tuple[str, ...]
    description: str
    uniform: bool = False
    uniform_color: str | None = None

    def sequence(self) -> tuple[str, ...]:
        """Return the canonical sequence of colours for this palette."""

        return self.colors

    def resolved_uniform_color(self) -> str:
        """Return the display colour used when the palette enforces uniform output."""

        if self.uniform_color:
            return self.uniform_color
        if self.colors:
            return self.colors[0]
        return "#4F6D7A"


DEFAULT_PALETTE_KEY = "high_contrast"


def load_palette_definitions() -> Sequence[PaletteDefinition]:
    """Return the ordered palette definitions exposed in the UI."""

    return (
        PaletteDefinition(
            key="high_contrast",
            label="High-contrast palette",
            colors=(
                "#4F6D7A",
                "#C0D6DF",
                "#C72C41",
                "#2F4858",
                "#33658A",
                "#758E4F",
                "#6D597A",
                "#EE964B",
            ),
            description="Default balanced palette for mixed overlays.",
        ),
        PaletteDefinition(
            key="colour_blind_friendly",
            label="Colour-blind friendly",
            colors=(
                "#0072B2",
                "#E69F00",
                "#009E73",
                "#D55E00",
                "#CC79A7",
                "#F0E442",
                "#56B4E9",
                "#999999",
            ),
            description="Okabe–Ito palette tuned for common colour-vision deficiencies.",
        ),
        PaletteDefinition(
            key="light_on_dark",
            label="Light-on-dark",
            colors=(
                "#F07167",
                "#FED9B7",
                "#00AFB9",
                "#FFD166",
                "#06D6A0",
                "#C77DFF",
                "#70A9A1",
                "#FAFF7F",
            ),
            description="Bright accents that remain legible on dark backgrounds.",
        ),
        PaletteDefinition(
            key="uniform",
            label="Uniform (single colour)",
            colors=("#4F6D7A",),
            description="Single-colour mode for alignment and registration checks.",
            uniform=True,
            uniform_color="#346751",
        ),
    )

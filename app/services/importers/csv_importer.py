"""CSV importer implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np

from .base import ImporterResult


class CsvImporter:
    """Read spectral data from comma-separated value files."""

    def read(self, path: Path) -> ImporterResult:
        """Parse ``path`` and return raw spectral arrays.

        The importer expects the first non-comment line to contain column
        headers. Units can be provided in parentheses, e.g. ``wavelength(nm)``.
        Subsequent rows must provide numeric data with at least two columns.
        """

        comments: list[str] = []
        data_lines: list[str] = []
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    comments.append(line[1:].strip())
                else:
                    data_lines.append(line)

        if len(data_lines) < 2:
            raise ValueError(f"No data rows found in {path}")

        header = data_lines[0].split(",")
        if len(header) < 2:
            raise ValueError("CSV must have at least two columns")

        def parse_header(token: str) -> Tuple[str, str]:
            token = token.strip()
            if "(" in token and token.endswith(")"):
                base, unit = token[:-1].split("(", 1)
                return base.strip(), unit.strip()
            return token, ""

        x_label, x_unit = parse_header(header[0])
        y_label, y_unit = parse_header(header[1])

        if not x_unit:
            normalised_label = x_label.strip().lower()
            if normalised_label in {"wavelength_nm", "wavelength (nm)", "wavelength"}:
                x_unit = "nm"

        if not y_unit:
            label_lower = y_label.strip().lower()
            if label_lower in {"percent_transmittance", "%t", "percent transmittance"}:
                y_unit = "percent_transmittance"
            elif label_lower in {"transmittance", "t"}:
                y_unit = "transmittance"

        body = np.genfromtxt(data_lines[1:], delimiter=",", dtype=float)
        if body.ndim == 1:
            body = body.reshape(1, -1)

        x = body[:, 0]
        y = body[:, 1]

        metadata = {
            "comments": comments,
            "x_label": x_label,
            "y_label": y_label,
        }

        return ImporterResult(
            name=path.stem,
            x=x,
            y=y,
            x_unit=x_unit or "nm",
            y_unit=y_unit or "absorbance",
            metadata=metadata,
            source_path=path,
        )

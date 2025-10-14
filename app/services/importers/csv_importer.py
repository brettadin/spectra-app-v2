"""Import spectra from CSV files."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np

from .base import ImporterResult


class CsvImporter:
    """Read spectral data from CSV files."""

    def read(self, path: Path) -> ImporterResult:
        """Parse the given CSV file and return raw spectral data."""
        comments = []
        with path.open('r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]

        data_lines = []
        for ln in lines:
            if ln.startswith('#'):
                comments.append(ln[1:].strip())
            else:
                data_lines.append(ln)

        if not data_lines:
            raise ValueError(f"No data found in {path}")

        header = data_lines[0].split(',')
        if len(header) < 2:
            raise ValueError("CSV must have at least two columns")

        def parse_name(name: str) -> Tuple[str, str]:
            if '(' in name and name.endswith(')'):
                base, unit = name[:-1].split('(', 1)
                return base.strip(), unit.strip()
            return name.strip(), ''

        x_label, x_unit = parse_name(header[0])
        y_label, y_unit = parse_name(header[1])

        data = np.genfromtxt(data_lines[1:], delimiter=',', dtype=float)
        if data.ndim == 1:
            data = data.reshape(1, -1)

        x = data[:, 0]
        y = data[:, 1]

        metadata = {
            "comments": comments,
            "x_label": x_label,
            "y_label": y_label,
        }

        return ImporterResult(
            name=path.stem,
            x=x,
            y=y,
            x_unit=x_unit or 'nm',
            y_unit=y_unit or 'absorbance',
            metadata=metadata,
            source_path=path,
        )

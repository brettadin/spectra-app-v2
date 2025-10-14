"""Import spectra from CSV or delimited text files."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
import numpy as np

from .base import ImporterResult, Importer


class CsvImporter(Importer):
    """Read spectral data from delimited text files."""

    supported_extensions: Tuple[str, ...] = (".csv", ".txt", ".dat")

    def description(self) -> str:
        return "Comma- or tab-delimited spectra"

    def read(self, path: Path) -> ImporterResult:
        comments: List[str] = []
        with path.open("r", encoding="utf-8") as handle:
            lines = [line.rstrip("\n") for line in handle if line.strip()]

        data_lines: List[str] = []
        for line in lines:
            if line.lstrip().startswith("#"):
                comments.append(line.lstrip()[1:].strip())
            else:
                data_lines.append(line)

        if not data_lines:
            raise ValueError(f"No data rows found in {path}")

        header_parts = [part.strip() for part in data_lines[0].split(',')]
        if len(header_parts) < 2:
            raise ValueError("CSV requires at least two columns")

        x_label, x_unit = self._parse_header(header_parts[0])
        y_label, y_unit = self._parse_header(header_parts[1])

        if not x_unit:
            lower = x_label.lower()
            if any(token in lower for token in ("µm", "micron", "micrometre", "micrometer")):
                x_unit = "µm"
            elif any(token in lower for token in ("cm^-1", "wavenumber", "1/cm", "cm-1")):
                x_unit = "cm^-1"
            elif "ang" in lower:
                x_unit = "Å"
            else:
                x_unit = "nm"

        if not y_unit:
            lower_y = y_label.lower()
            if "percent_trans" in lower_y or "%t" in lower_y:
                y_unit = "percent_transmittance"
            elif "transmittance" in lower_y:
                y_unit = "transmittance"
            elif "absorption_coefficient" in lower_y or "alpha" in lower_y:
                y_unit = "absorption_coefficient"
            else:
                y_unit = "absorbance"

        raw_data = np.genfromtxt(data_lines[1:], delimiter=',', dtype=float)
        if raw_data.ndim == 1:
            raw_data = raw_data.reshape(1, -1)

        wavelengths = raw_data[:, 0]
        flux = raw_data[:, 1]

        metadata = {
            "comments": comments,
            "x_label": x_label,
            "y_label": y_label,
            "original_header": data_lines[0],
            "flux_context": {},
        }

        return ImporterResult(
            wavelengths=wavelengths,
            flux=flux,
            wavelength_unit=x_unit,
            flux_unit=y_unit,
            metadata=metadata,
            source_path=path,
        )

    @staticmethod
    def _parse_header(value: str) -> Tuple[str, str]:
        if "(" in value and value.endswith(")"):
            base, unit = value[:-1].split("(", 1)
            return base.strip(), unit.strip()
        return value, ""

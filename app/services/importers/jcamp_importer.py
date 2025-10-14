"""JCAMP-DX importer for infrared/UV spectra."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

from .base import ImporterResult


class JcampImporter:
    """Parse a minimal subset of the JCAMP-DX specification.

    The parser focuses on the structures commonly encountered in laboratory
    spectra: ``##XUNITS``, ``##YUNITS``, and ``##XYDATA`` blocks. Multi-value
    rows inside ``##XYDATA`` are expanded using ``##DELTAX`` if present; when no
    spacing is provided, the importer falls back to emitting a single sample per
    row. The goal is to provide predictable behaviour for regression tests
    without attempting to implement the entire JCAMP dialect.
    """

    _DEFAULT_X_UNIT = "cm^-1"
    _DEFAULT_Y_UNIT = "absorbance"

    def read(self, path: Path) -> ImporterResult:
        path = Path(path)
        text = path.read_text(encoding="utf-8", errors="ignore")
        header, samples = self._parse(text)

        x_unit = header.get("XUNITS", self._DEFAULT_X_UNIT)
        y_unit = header.get("YUNITS", self._DEFAULT_Y_UNIT)
        name = header.get("TITLE", path.stem)

        x_values, y_values = samples
        if not x_values or not y_values:
            raise ValueError(f"No spectral samples found in JCAMP file {path}")

        metadata: Dict[str, object] = {
            "jcamp_header": header,
            "source_format": "JCAMP-DX",
        }

        return ImporterResult(
            name=name,
            x=np.asarray(x_values, dtype=np.float64),
            y=np.asarray(y_values, dtype=np.float64),
            x_unit=x_unit.lower(),
            y_unit=y_unit.lower(),
            metadata=metadata,
            source_path=path,
        )

    # ------------------------------------------------------------------
    def _parse(self, text: str) -> Tuple[Dict[str, str], Tuple[List[float], List[float]]]:
        header: Dict[str, str] = {}
        x_samples: List[float] = []
        y_samples: List[float] = []

        in_xydata = False
        delta_x: float | None = None

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("##"):
                key, _, value = line[2:].partition("=")
                key_upper = key.strip().upper()
                value = value.strip()

                if key_upper == "XYDATA":
                    in_xydata = True
                    continue
                if key_upper in {"END", "END="}:
                    break
                if key_upper == "DELTAX":
                    try:
                        delta_x = float(value)
                    except ValueError:
                        delta_x = None
                    continue

                header[key_upper] = value
                continue

            if not in_xydata:
                continue

            tokens = self._split_tokens(line)
            if len(tokens) < 2:
                continue

            try:
                start_x = float(tokens[0])
            except ValueError:
                continue

            y_values: List[float] = []
            for token in tokens[1:]:
                try:
                    y_values.append(float(token))
                except ValueError:
                    continue

            if not y_values:
                continue

            if len(y_values) == 1 or delta_x is None:
                x_samples.append(start_x)
                y_samples.append(y_values[0])
            else:
                current_x = start_x
                for y in y_values:
                    x_samples.append(current_x)
                    y_samples.append(y)
                    current_x += delta_x

        return header, (x_samples, y_samples)

    def _split_tokens(self, line: str) -> List[str]:
        separators: Iterable[str] = {",", " ", "\t"}
        for sep in separators:
            line = line.replace(sep, " ")
        return [token for token in line.split(" ") if token]


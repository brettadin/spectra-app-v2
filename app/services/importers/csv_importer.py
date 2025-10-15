"""CSV importer implementation with heuristic parsing for loose tabular data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Iterable, List, Sequence, Tuple, cast

import numpy as np

from .base import ImporterResult

_NUMERIC_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


@dataclass
class _HeaderToken:
    label: str
    unit: str = ""

    @property
    def normalised_label(self) -> str:
        return self.label.strip().lower()


_WAVELENGTH_LABEL_HINTS = {"wavelength", "wavenumber", "lambda", "λ", "ν̅", "nu", "wn", "kmax"}
_INTENSITY_LABEL_HINTS = {
    "intensity",
    "absorbance",
    "transmittance",
    "reflectance",
    "signal",
    "counts",
    "flux",
    "radiance",
    "emission",
    "brightness",
    "optical density",
    "density",
    "power",
    "y",
}
_WAVELENGTH_UNIT_HINTS = {
    "nm",
    "nanometer",
    "nanometre",
    "nanometers",
    "nanometres",
    "µm",
    "um",
    "micrometer",
    "micrometre",
    "angstrom",
    "ångström",
    "å",
    "cm^-1",
    "cm⁻¹",
    "cm-1",
    "1/cm",
    "1cm^-1",
}
_INTENSITY_UNIT_HINTS = {
    "%",
    "percent",
    "percentt",
    "percenttransmittance",
    "a.u.",
    "a.u",
    "au",
    "arb",
    "arb.units",
    "arbunits",
    "counts",
    "cts",
    "flux",
    "w/m2",
    "w/m^2",
    "absorbance",
    "transmittance",
    "reflectance",
    "radiance",
    "od",
    "opticaldensity",
    "emission",
    "power",
}

_WAVELENGTH_UNIT_HINTS_NORMALISED = {unit.strip().lower().replace(" ", "") for unit in _WAVELENGTH_UNIT_HINTS}
_INTENSITY_UNIT_HINTS_NORMALISED = {unit.strip().lower().replace(" ", "") for unit in _INTENSITY_UNIT_HINTS}


_LAYOUT_CACHE: Dict[Tuple[str, ...], Tuple[int, int]] = {}


def _reset_layout_cache() -> None:
    """Testing helper to clear the in-process layout cache."""

    _LAYOUT_CACHE.clear()


class CsvImporter:
    """Read spectral data from loosely formatted delimited text files."""

    def read(self, path: Path) -> ImporterResult:
        """Parse ``path`` and return raw spectral arrays.

        The importer accepts traditional CSV files as well as scientific data
        exports that interleave prose, comments, or additional descriptor
        columns. Numeric detection is performed row-by-row so the importer can
        recover the dominant two-column trace even when the original file
        contains extra values.
        """

        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            raise ValueError(f"File {path} is empty")

        comments: list[str] = []
        preface: list[str] = []
        block_rows: list[Tuple[str, List[float]]] = []
        block_start_index = -1
        best_block: list[Tuple[str, List[float]]] = []
        best_start = -1

        def commit_block() -> None:
            nonlocal best_block, best_start, block_rows, block_start_index
            if block_rows and len(block_rows) > len(best_block):
                best_block = block_rows
                best_start = block_start_index
            block_rows = []
            block_start_index = -1

        for idx, raw_line in enumerate(lines):
            line = raw_line.strip()
            if not line:
                commit_block()
                continue
            if line.startswith("#"):
                comments.append(line[1:].strip())
                commit_block()
                continue

            numbers = self._extract_numbers(line)
            if len(numbers) >= 2:
                if not block_rows:
                    block_start_index = idx
                block_rows.append((raw_line, numbers))
            else:
                preface.append(raw_line.strip())
                commit_block()

        commit_block()

        if not best_block:
            raise ValueError(f"No tabular data found in {path}")

        delimiter = self._detect_delimiter(best_block[0][0])
        header_tokens = self._extract_header_tokens(lines, best_start, delimiter)

        data = self._rows_to_array(best_block)
        layout_signature = self._layout_signature(header_tokens)
        cached = self._lookup_cached_layout(layout_signature, data.shape[1])
        cache_hit = False
        if cached:
            x_candidate, y_candidate = cached
            if self._layout_is_valid(data, x_candidate, y_candidate, header_tokens):
                cache_hit = True
                x_index_raw, y_index_raw = x_candidate, y_candidate
                x_reason_raw = y_reason_raw = "layout-cache"
            else:
                x_index_raw = y_index_raw = -1
        if not cache_hit:
            x_index_raw, x_reason_raw = self._select_x_column(data, header_tokens)
            y_index_raw, y_reason_raw = self._select_y_column(data, x_index_raw, header_tokens)
        swap_reason = None
        if not cache_hit:
            swap_reason = self._axis_conflict_resolution(x_index_raw, y_index_raw, header_tokens)
        if swap_reason:
            x_index, y_index = y_index_raw, x_index_raw
            x_select_reason = f"{y_reason_raw}|{swap_reason}"
            y_select_reason = f"{x_reason_raw}|{swap_reason}"
        else:
            x_index, y_index = x_index_raw, y_index_raw
            x_select_reason, y_select_reason = x_reason_raw, y_reason_raw

        x_raw = data[:, x_index]
        y_raw = data[:, y_index]
        mask = np.isfinite(x_raw) & np.isfinite(y_raw)
        x = x_raw[mask]
        y = y_raw[mask]

        profile_swap_reason: str | None = None
        if not cache_hit and swap_reason is None and self._should_swap_by_profile(x, y):
            profile_swap_reason = "profile-swap"
            x_index, y_index = y_index, x_index
            x_raw, y_raw = y_raw, x_raw
            x_select_reason, y_select_reason = y_select_reason, x_select_reason
            x_select_reason = f"{x_select_reason}|{profile_swap_reason}"
            y_select_reason = f"{y_select_reason}|{profile_swap_reason}"
            mask = np.isfinite(x_raw) & np.isfinite(y_raw)
            x = x_raw[mask]
            y = y_raw[mask]

        if profile_swap_reason:
            swap_reason = profile_swap_reason

        metadata_context = "\n".join(preface + comments + [tok.label for tok in header_tokens])

        x_label = header_tokens[x_index].label if x_index < len(header_tokens) else f"Column {x_index + 1}"
        y_label = header_tokens[y_index].label if y_index < len(header_tokens) else f"Column {y_index + 1}"

        x_unit, x_unit_reason = self._infer_x_unit(x, header_tokens, metadata_context, x_index)
        y_unit, y_unit_reason = self._infer_y_unit(y, header_tokens, metadata_context, y_index)

        if x.size == 0 or y.size == 0:
            raise ValueError(f"Unable to extract numeric data from {path}")

        metadata: dict[str, object] = {
            "comments": comments,
            "preface": preface,
            "x_label": x_label,
            "y_label": y_label,
            "header_tokens": [token.label for token in header_tokens],
            "detected_units": {
                "x": {"unit": x_unit, "reason": x_unit_reason},
                "y": {"unit": y_unit, "reason": y_unit_reason},
            },
            "column_selection": {
                "x_index": int(x_index),
                "y_index": int(y_index),
                "x_reason": x_select_reason,
                "y_reason": y_select_reason,
            },
        }

        if swap_reason:
            column_meta = cast(dict[str, object], metadata["column_selection"])
            column_meta["swap"] = swap_reason
            column_meta["original"] = {
                "x_index": int(x_index_raw),
                "y_index": int(y_index_raw),
            }
        column_meta = cast(dict[str, object], metadata["column_selection"])
        if layout_signature:
            column_meta["layout_signature"] = list(layout_signature)
            column_meta["layout_cache"] = "hit" if cache_hit else "miss"

        if layout_signature and self._layout_is_valid(data, int(x_index), int(y_index), header_tokens):
            self._store_layout(layout_signature, int(x_index), int(y_index))

        if x[0] > x[-1]:
            # Preserve monotonic increase expected by downstream consumers.
            x = x[::-1]
            y = y[::-1]
            detected_units = cast(dict[str, dict[str, str]], metadata["detected_units"])
            x_meta = detected_units.setdefault("x", {})
            x_meta["sorted"] = "descending→ascending"

        return ImporterResult(
            name=path.stem,
            x=x,
            y=y,
            x_unit=x_unit,
            y_unit=y_unit,
            metadata=metadata,
            source_path=path,
        )

    # ------------------------------------------------------------------
    def _extract_numbers(self, line: str) -> List[float]:
        return [float(match.group()) for match in _NUMERIC_RE.finditer(line)]

    def _detect_delimiter(self, sample: str) -> str | None:
        for candidate in (",", "\t", ";", "|", " "):
            if candidate in sample:
                return candidate
        return None

    def _extract_header_tokens(
        self, lines: Sequence[str], start_index: int, delimiter: str | None
    ) -> List[_HeaderToken]:
        if start_index <= 0:
            return []
        header_line = lines[start_index - 1].strip()
        if not header_line or header_line.lstrip().startswith("#"):
            return []
        tokens = self._tokenise(header_line, delimiter)
        return [self._parse_header_token(token) for token in tokens]

    def _rows_to_array(self, rows: Sequence[Tuple[str, Sequence[float]]]) -> np.ndarray:
        max_columns = max(len(row[1]) for row in rows)
        data = np.full((len(rows), max_columns), np.nan, dtype=float)
        for idx, (_raw, numbers) in enumerate(rows):
            length = min(len(numbers), max_columns)
            data[idx, :length] = numbers[:length]
        return data

    def _layout_signature(self, headers: Sequence[_HeaderToken]) -> Tuple[str, ...]:
        if not headers:
            return tuple()
        signature: List[str] = []
        for token in headers:
            label = token.normalised_label
            unit = self._normalise_unit_string(token.unit)
            signature.append(f"{label}|{unit}")
        return tuple(signature)

    def _lookup_cached_layout(
        self, signature: Tuple[str, ...], column_count: int
    ) -> Tuple[int, int] | None:
        if not signature or signature not in _LAYOUT_CACHE:
            return None
        cached_x, cached_y = _LAYOUT_CACHE[signature]
        if cached_x >= column_count or cached_y >= column_count:
            return None
        return cached_x, cached_y

    def _store_layout(self, signature: Tuple[str, ...], x_index: int, y_index: int) -> None:
        if not signature:
            return
        _LAYOUT_CACHE[signature] = (x_index, y_index)

    def _layout_is_valid(
        self,
        data: np.ndarray,
        x_index: int,
        y_index: int,
        headers: Sequence[_HeaderToken],
    ) -> bool:
        if x_index < 0 or y_index < 0:
            return False
        _, cols = data.shape
        if x_index >= cols or y_index >= cols or x_index == y_index:
            return False
        x_column = data[:, x_index]
        y_column = data[:, y_index]
        x_valid = self._column_looks_like_wavelength(x_column, headers, x_index)
        y_valid = self._column_looks_like_intensity(y_column, headers, y_index)
        return x_valid and y_valid

    def _column_looks_like_wavelength(
        self, column: np.ndarray, headers: Sequence[_HeaderToken], index: int
    ) -> bool:
        mask = np.isfinite(column)
        values = column[mask]
        if values.size < 3:
            return False
        diffs = np.diff(values)
        monotonic = bool(diffs.size) and (
            np.all(diffs >= 0) or np.all(diffs <= 0)
        )
        negative_fraction = float(np.mean(values < 0)) if values.size else 0.0
        predominantly_negative = negative_fraction > 0.6
        looks_wavelength = self._looks_like_wavelength(values)
        looks_intensity = self._looks_like_intensity(values)
        header_wavelength = (
            index < len(headers) and self._token_is_wavelength(headers[index])
        )
        if looks_wavelength and not looks_intensity:
            return monotonic and not predominantly_negative
        if looks_wavelength and looks_intensity:
            return header_wavelength and monotonic and not predominantly_negative
        return (
            header_wavelength
            and monotonic
            and not looks_intensity
            and not predominantly_negative
        )

    def _column_looks_like_intensity(
        self, column: np.ndarray, headers: Sequence[_HeaderToken], index: int
    ) -> bool:
        mask = np.isfinite(column)
        values = column[mask]
        if values.size < 3:
            return False
        looks_intensity = self._looks_like_intensity(values)
        looks_wavelength = self._looks_like_wavelength(values)
        header_intensity = (
            index < len(headers) and self._token_is_intensity(headers[index])
        )
        if looks_wavelength and not looks_intensity:
            return False
        if looks_intensity:
            return True
        return header_intensity and not looks_wavelength

    def _select_x_column(self, data: np.ndarray, headers: Sequence[_HeaderToken]) -> Tuple[int, str]:
        header_unit = self._header_index_by_unit(headers, _WAVELENGTH_UNIT_HINTS)
        if header_unit is not None:
            return header_unit, "header-unit"
        header_index = self._header_index(headers, _WAVELENGTH_LABEL_HINTS)
        if header_index is not None:
            return header_index, "header-label"
        scored = self._score_columns_for_axis(data, prefer_monotonic=True)
        return scored, "score"

    def _select_y_column(
        self, data: np.ndarray, x_index: int, headers: Sequence[_HeaderToken]
    ) -> Tuple[int, str]:
        header_unit = self._header_index_by_unit(headers, _INTENSITY_UNIT_HINTS, exclude={x_index})
        if header_unit is not None:
            return header_unit, "header-unit"
        header_index = self._header_index(
            headers,
            _INTENSITY_LABEL_HINTS,
            exclude={x_index},
        )
        if header_index is not None:
            return header_index, "header-label"
        scored = self._score_columns_for_axis(data, prefer_monotonic=False, exclude={x_index})
        return scored, "score"

    def _header_index(
        self,
        headers: Sequence[_HeaderToken],
        keywords: Iterable[str],
        *,
        exclude: set[int] | None = None,
    ) -> int | None:
        if not headers:
            return None
        exclude = exclude or set()
        keywords_lower = {kw.lower() for kw in keywords}
        for idx, token in enumerate(headers):
            if idx in exclude:
                continue
            if any(keyword in token.normalised_label for keyword in keywords_lower):
                return idx
        return None

    def _header_index_by_unit(
        self,
        headers: Sequence[_HeaderToken],
        units: Iterable[str],
        *,
        exclude: set[int] | None = None,
    ) -> int | None:
        if not headers:
            return None
        exclude = exclude or set()
        unit_set = {self._normalise_unit_string(unit) for unit in units}
        for idx, token in enumerate(headers):
            if idx in exclude:
                continue
            unit = self._normalise_unit_string(token.unit)
            if unit and unit in unit_set:
                return idx
        return None

    def _axis_conflict_resolution(
        self,
        x_index: int,
        y_index: int,
        headers: Sequence[_HeaderToken],
    ) -> str | None:
        if not headers:
            return None
        if x_index >= len(headers) or y_index >= len(headers):
            return None
        x_token = headers[x_index]
        y_token = headers[y_index]
        if self._token_is_intensity(x_token) and self._token_is_wavelength(y_token):
            if not self._token_is_intensity(y_token):
                return "header-swap"
        return None

    def _should_swap_by_profile(self, x_values: np.ndarray, y_values: np.ndarray) -> bool:
        if x_values.size < 3 or y_values.size < 3:
            return False
        x_is_intensity = self._looks_like_intensity(x_values)
        y_is_intensity = self._looks_like_intensity(y_values)
        y_is_wavelength = self._looks_like_wavelength(y_values)
        x_is_wavelength = self._looks_like_wavelength(x_values)

        if x_is_intensity and not y_is_intensity and y_is_wavelength:
            return True
        if x_is_wavelength and y_is_intensity:
            return False
        return False

    def _token_is_wavelength(self, token: _HeaderToken) -> bool:
        label = token.normalised_label
        if any(keyword in label for keyword in _WAVELENGTH_LABEL_HINTS):
            return True
        unit = self._normalise_unit_string(token.unit)
        return bool(unit) and unit in _WAVELENGTH_UNIT_HINTS_NORMALISED

    def _token_is_intensity(self, token: _HeaderToken) -> bool:
        label = token.normalised_label
        if any(keyword in label for keyword in _INTENSITY_LABEL_HINTS):
            return True
        unit = self._normalise_unit_string(token.unit)
        return bool(unit) and unit in _INTENSITY_UNIT_HINTS_NORMALISED

    def _normalise_unit_string(self, unit: str) -> str:
        return unit.strip().lower().replace(" ", "")

    def _score_columns_for_axis(
        self,
        data: np.ndarray,
        *,
        prefer_monotonic: bool,
        exclude: set[int] | None = None,
    ) -> int:
        exclude = exclude or set()
        best_index = 0
        best_score = float("-inf")
        rows, cols = data.shape
        for col in range(cols):
            if col in exclude:
                continue
            column = data[:, col]
            mask = np.isfinite(column)
            valid = column[mask]
            if valid.size < 3:
                continue
            diffs = np.diff(valid)
            monotonic = bool(diffs.size) and (
                np.all(diffs >= 0) or np.all(diffs <= 0)
            )
            variance = float(np.nanvar(valid))
            span = float(np.nanmax(valid) - np.nanmin(valid))
            score = valid.size
            if prefer_monotonic:
                if monotonic:
                    score += 10
                else:
                    score -= 8
            elif not prefer_monotonic and not monotonic:
                score += 2
            score += np.log1p(abs(span))
            score += np.log1p(abs(variance))
            if prefer_monotonic and monotonic and self._looks_like_wavelength(valid):
                score += 12
            if not prefer_monotonic and self._looks_like_intensity(valid):
                score += 6
            if prefer_monotonic and span < 1.0 and np.nanmedian(np.abs(valid)) < 2.0:
                score -= 5
            if score > best_score:
                best_score = score
                best_index = col
        return best_index

    def _looks_like_wavelength(self, data: np.ndarray) -> bool:
        median = float(np.nanmedian(np.abs(data)))
        if not np.isfinite(median):
            return False
        if 1e3 <= median <= 2.5e4:  # typical wavenumber export
            return True
        if 80.0 <= median <= 2500.0:  # typical nanometre range
            return True
        if 0.2 <= median <= 25.0:  # micrometre export
            return True
        return False

    def _looks_like_intensity(self, data: np.ndarray) -> bool:
        median = float(np.nanmedian(np.abs(data)))
        if not np.isfinite(median):
            return False
        span = float(np.nanmax(data) - np.nanmin(data))
        if median <= 10.0 and span <= 200.0:
            return True
        return False

    def _infer_x_unit(
        self,
        data: np.ndarray,
        headers: Sequence[_HeaderToken],
        context: str,
        index: int,
    ) -> Tuple[str, str]:
        explicit = self._unit_from_header(headers, index)
        if explicit:
            return explicit, "header"

        ctx_lower = context.lower()
        if any(keyword in ctx_lower for keyword in {"wavenumber", "cm-1", "cm^-1", "wavenumbers"}):
            return "cm^-1", "preface"
        if any(keyword in ctx_lower for keyword in {"angstrom", "ångström", "å"}):
            return "angstrom", "preface"
        if any(keyword in ctx_lower for keyword in {"micron", "micrometre", "micrometer", "µm"}):
            return "µm", "preface"

        median = float(np.nanmedian(data))
        if 1e3 <= median <= 2.5e4:
            return "cm^-1", "value-range"
        if 80 <= median <= 2500:
            return "nm", "value-range"
        if 0.2 <= median <= 25:
            return "µm", "value-range"
        return "nm", "default"

    def _infer_y_unit(
        self,
        data: np.ndarray,
        headers: Sequence[_HeaderToken],
        context: str,
        index: int,
    ) -> Tuple[str, str]:
        explicit = self._unit_from_header(headers, index)
        if explicit:
            normalised = self._normalise_intensity_unit(explicit)
            if normalised:
                return normalised, "header"

        ctx_lower = context.lower()
        if any(keyword in ctx_lower for keyword in {"percent trans", "%t", "transmittance (%)", "transmission"}):
            return "percent_transmittance", "preface"
        if "transmittance" in ctx_lower:
            return "transmittance", "preface"
        if any(keyword in ctx_lower for keyword in {"absorbance", "optical density"}):
            return "absorbance", "preface"

        median = float(np.nanmedian(np.abs(data)))
        if 20.0 <= np.nanmax(data) <= 120.0:
            return "percent_transmittance", "value-range"
        if 0.0 <= median <= 5.0:
            return "absorbance", "value-range"
        return "absorbance", "default"

    def _unit_from_header(self, headers: Sequence[_HeaderToken], index: int) -> str | None:
        if not headers or index >= len(headers):
            return None
        token = headers[index]
        if token.unit:
            return token.unit
        for keyword, unit in {
            "wavenumber": "cm^-1",
            "cm^-1": "cm^-1",
            "cm⁻¹": "cm^-1",
            "angstrom": "angstrom",
            "ångström": "angstrom",
            "å": "angstrom",
            "micron": "µm",
            "µm": "µm",
            "nanometre": "nm",
            "nanometer": "nm",
            "nm": "nm",
            "percent": "percent_transmittance",
            "%": "percent_transmittance",
            "transmittance": "transmittance",
            "absorbance": "absorbance",
            "optical density": "absorbance",
            "density": "absorbance",
            "a.u.": "absorbance",
            "a.u": "absorbance",
            "au": "absorbance",
            "arb": "absorbance",
            "arb.units": "absorbance",
            "arbunits": "absorbance",
            "counts": "absorbance",
            "cts": "absorbance",
            "flux": "absorbance",
            "reflectance": "transmittance",
            "radiance": "absorbance",
            "od": "absorbance",
        }.items():
            if keyword in token.normalised_label:
                return unit
        return None

    def _normalise_intensity_unit(self, unit: str) -> str | None:
        u = unit.strip().lower()
        mapping = {
            "percent": "percent_transmittance",
            "%": "percent_transmittance",
            "%t": "percent_transmittance",
            "percent_transmittance": "percent_transmittance",
            "transmittance": "transmittance",
            "t": "transmittance",
            "reflectance": "transmittance",
            "absorbance": "absorbance",
            "a10": "absorbance",
            "absorbance_e": "absorbance",
            "opticaldensity": "absorbance",
            "od": "absorbance",
            "a.u.": "absorbance",
            "a.u": "absorbance",
            "au": "absorbance",
            "arb": "absorbance",
            "arb.units": "absorbance",
            "arbunits": "absorbance",
            "counts": "absorbance",
            "cts": "absorbance",
            "flux": "absorbance",
            "radiance": "absorbance",
        }
        return mapping.get(u)

    def _tokenise(self, line: str, delimiter: str | None) -> List[str]:
        if delimiter in {None, " "}:
            return [token for token in line.replace("\t", " ").split() if token]
        return [token.strip() for token in line.split(delimiter) if token.strip()]

    def _parse_header_token(self, token: str) -> _HeaderToken:
        token = token.strip().strip("#")
        if not token:
            return _HeaderToken(label="")
        if "(" in token and token.endswith(")"):
            base, unit = token[:-1].split("(", 1)
            return _HeaderToken(label=base.strip(), unit=unit.strip())
        if "[" in token and token.endswith("]"):
            base, unit = token[:-1].split("[", 1)
            return _HeaderToken(label=base.strip(), unit=unit.strip())
        if ":" in token:
            base, unit = token.split(":", 1)
            unit = unit.strip()
            return _HeaderToken(label=base.strip(), unit=unit)
        return _HeaderToken(label=token)

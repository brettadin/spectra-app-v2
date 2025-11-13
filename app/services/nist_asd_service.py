"""Fetch spectral line lists from the NIST Atomic Spectra Database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import math
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from app.services.line_list_cache import LineListCache

# Exposed flags/sentinels for tests to patch
try:
    import importlib.util as _importlib_util  # type: ignore
except Exception:  # pragma: no cover
    _importlib_util = None  # type: ignore

# Whether heavy deps appear available (can be patched by tests)
ASTROQUERY_AVAILABLE: bool = False
try:
    if _importlib_util is not None:
        _has_nist = _importlib_util.find_spec("astroquery.nist") is not None
        _has_astropy = _importlib_util.find_spec("astropy.units") is not None
        ASTROQUERY_AVAILABLE = bool(_has_nist and _has_astropy)
except Exception:
    ASTROQUERY_AVAILABLE = False

# Placeholder symbol so tests can patch `Nist` without importing astroquery
Nist = None  # type: ignore

# Global cache instance shared across all NIST queries
_CACHE: Optional[LineListCache] = None


class NistUnavailableError(RuntimeError):
    """Raised when astroquery is not available to service NIST requests."""


class NistQueryError(RuntimeError):
    """Raised when the NIST service cannot satisfy the requested query."""


@dataclass(frozen=True)
class ElementRecord:
    number: int
    symbol: str
    name: str
    aliases: Tuple[str, ...] = ()


# Adapted from the upstream Spectra project (`spectra-app`) so element lookups and
# alias handling match the curated Streamlit build. The dataset is static and
# maps symbols/names onto atomic numbers.
_ELEMENT_TABLE: Tuple[ElementRecord, ...] = (
    ElementRecord(1, "H", "Hydrogen"),
    ElementRecord(2, "He", "Helium"),
    ElementRecord(3, "Li", "Lithium"),
    ElementRecord(4, "Be", "Beryllium"),
    ElementRecord(5, "B", "Boron"),
    ElementRecord(6, "C", "Carbon"),
    ElementRecord(7, "N", "Nitrogen"),
    ElementRecord(8, "O", "Oxygen"),
    ElementRecord(9, "F", "Fluorine"),
    ElementRecord(10, "Ne", "Neon"),
    ElementRecord(11, "Na", "Sodium"),
    ElementRecord(12, "Mg", "Magnesium"),
    ElementRecord(13, "Al", "Aluminium", ("Aluminum",)),
    ElementRecord(14, "Si", "Silicon"),
    ElementRecord(15, "P", "Phosphorus"),
    ElementRecord(16, "S", "Sulfur", ("Sulphur",)),
    ElementRecord(17, "Cl", "Chlorine"),
    ElementRecord(18, "Ar", "Argon"),
    ElementRecord(19, "K", "Potassium"),
    ElementRecord(20, "Ca", "Calcium"),
    ElementRecord(21, "Sc", "Scandium"),
    ElementRecord(22, "Ti", "Titanium"),
    ElementRecord(23, "V", "Vanadium"),
    ElementRecord(24, "Cr", "Chromium"),
    ElementRecord(25, "Mn", "Manganese"),
    ElementRecord(26, "Fe", "Iron"),
    ElementRecord(27, "Co", "Cobalt"),
    ElementRecord(28, "Ni", "Nickel"),
    ElementRecord(29, "Cu", "Copper"),
    ElementRecord(30, "Zn", "Zinc"),
    ElementRecord(31, "Ga", "Gallium"),
    ElementRecord(32, "Ge", "Germanium"),
    ElementRecord(33, "As", "Arsenic"),
    ElementRecord(34, "Se", "Selenium"),
    ElementRecord(35, "Br", "Bromine"),
    ElementRecord(36, "Kr", "Krypton"),
    ElementRecord(37, "Rb", "Rubidium"),
    ElementRecord(38, "Sr", "Strontium"),
    ElementRecord(39, "Y", "Yttrium"),
    ElementRecord(40, "Zr", "Zirconium"),
    ElementRecord(41, "Nb", "Niobium"),
    ElementRecord(42, "Mo", "Molybdenum"),
    ElementRecord(43, "Tc", "Technetium"),
    ElementRecord(44, "Ru", "Ruthenium"),
    ElementRecord(45, "Rh", "Rhodium"),
    ElementRecord(46, "Pd", "Palladium"),
    ElementRecord(47, "Ag", "Silver"),
    ElementRecord(48, "Cd", "Cadmium"),
    ElementRecord(49, "In", "Indium"),
    ElementRecord(50, "Sn", "Tin"),
    ElementRecord(51, "Sb", "Antimony"),
    ElementRecord(52, "Te", "Tellurium"),
    ElementRecord(53, "I", "Iodine"),
    ElementRecord(54, "Xe", "Xenon"),
    ElementRecord(55, "Cs", "Caesium", ("Cesium",)),
    ElementRecord(56, "Ba", "Barium"),
    ElementRecord(57, "La", "Lanthanum"),
    ElementRecord(58, "Ce", "Cerium"),
    ElementRecord(59, "Pr", "Praseodymium"),
    ElementRecord(60, "Nd", "Neodymium"),
    ElementRecord(61, "Pm", "Promethium"),
    ElementRecord(62, "Sm", "Samarium"),
    ElementRecord(63, "Eu", "Europium"),
    ElementRecord(64, "Gd", "Gadolinium"),
    ElementRecord(65, "Tb", "Terbium"),
    ElementRecord(66, "Dy", "Dysprosium"),
    ElementRecord(67, "Ho", "Holmium"),
    ElementRecord(68, "Er", "Erbium"),
    ElementRecord(69, "Tm", "Thulium"),
    ElementRecord(70, "Yb", "Ytterbium"),
    ElementRecord(71, "Lu", "Lutetium"),
    ElementRecord(72, "Hf", "Hafnium"),
    ElementRecord(73, "Ta", "Tantalum"),
    ElementRecord(74, "W", "Tungsten"),
    ElementRecord(75, "Re", "Rhenium"),
    ElementRecord(76, "Os", "Osmium"),
    ElementRecord(77, "Ir", "Iridium"),
    ElementRecord(78, "Pt", "Platinum"),
    ElementRecord(79, "Au", "Gold"),
    ElementRecord(80, "Hg", "Mercury"),
    ElementRecord(81, "Tl", "Thallium"),
    ElementRecord(82, "Pb", "Lead"),
    ElementRecord(83, "Bi", "Bismuth"),
    ElementRecord(84, "Po", "Polonium"),
    ElementRecord(85, "At", "Astatine"),
    ElementRecord(86, "Rn", "Radon"),
    ElementRecord(87, "Fr", "Francium"),
    ElementRecord(88, "Ra", "Radium"),
    ElementRecord(89, "Ac", "Actinium"),
    ElementRecord(90, "Th", "Thorium"),
    ElementRecord(91, "Pa", "Protactinium"),
    ElementRecord(92, "U", "Uranium"),
    ElementRecord(93, "Np", "Neptunium"),
    ElementRecord(94, "Pu", "Plutonium"),
    ElementRecord(95, "Am", "Americium"),
    ElementRecord(96, "Cm", "Curium"),
    ElementRecord(97, "Bk", "Berkelium"),
    ElementRecord(98, "Cf", "Californium"),
    ElementRecord(99, "Es", "Einsteinium"),
    ElementRecord(100, "Fm", "Fermium"),
    ElementRecord(101, "Md", "Mendelevium"),
    ElementRecord(102, "No", "Nobelium"),
    ElementRecord(103, "Lr", "Lawrencium"),
    ElementRecord(104, "Rf", "Rutherfordium"),
    ElementRecord(105, "Db", "Dubnium"),
    ElementRecord(106, "Sg", "Seaborgium"),
    ElementRecord(107, "Bh", "Bohrium"),
    ElementRecord(108, "Hs", "Hassium"),
    ElementRecord(109, "Mt", "Meitnerium"),
    ElementRecord(110, "Ds", "Darmstadtium"),
    ElementRecord(111, "Rg", "Roentgenium"),
    ElementRecord(112, "Cn", "Copernicium"),
    ElementRecord(113, "Nh", "Nihonium"),
    ElementRecord(114, "Fl", "Flerovium"),
    ElementRecord(115, "Mc", "Moscovium"),
    ElementRecord(116, "Lv", "Livermorium"),
    ElementRecord(117, "Ts", "Tennessine"),
    ElementRecord(118, "Og", "Oganesson"),
)

_SYMBOL_TO_ELEMENT = {record.symbol.lower(): record for record in _ELEMENT_TABLE}
_NAME_TO_ELEMENT: Dict[str, ElementRecord] = {record.name.lower(): record for record in _ELEMENT_TABLE}
for record in _ELEMENT_TABLE:
    for alias in record.aliases:
        _NAME_TO_ELEMENT[alias.lower()] = record


_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
_FLOAT_PATTERN = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")

DEFAULT_LOWER_WAVELENGTH_NM = 380.0
DEFAULT_UPPER_WAVELENGTH_NM = 750.0


def dependencies_available() -> bool:
    """Return True if astroquery.nist and astropy.units are present without importing them."""
    try:
        return (
            importlib.util.find_spec("astroquery.nist") is not None
            and importlib.util.find_spec("astropy.units") is not None
        )
    except Exception:
        return False


def get_cache() -> LineListCache:
    """
    Return the global line list cache instance.
    
    Lazily initializes the cache on first access. Cache can be disabled
    via the SPECTRA_DISABLE_LINE_CACHE environment variable.
    """
    global _CACHE
    if _CACHE is None:
        import os
        enabled = os.environ.get("SPECTRA_DISABLE_LINE_CACHE", "").lower() not in {"1", "true", "yes"}
        _CACHE = LineListCache(enabled=enabled)
    return _CACHE


def clear_cache() -> int:
    """Clear all cached line lists. Returns the number of entries removed."""
    return get_cache().clear()


def cache_stats() -> Dict[str, int]:
    """Return cache statistics (hits, misses, stores, evictions)."""
    return get_cache().stats


def _lookup_element(token: str) -> ElementRecord:
    key = token.strip().lower()
    if not key:
        raise ValueError("Element token is empty")
    if key in _SYMBOL_TO_ELEMENT:
        return _SYMBOL_TO_ELEMENT[key]
    if key in _NAME_TO_ELEMENT:
        return _NAME_TO_ELEMENT[key]
    raise ValueError(f"Unknown element identifier: {token!r}")


def _roman_to_int(token: str) -> Optional[int]:
    stripped = token.strip().upper()
    if not stripped or any(ch not in _ROMAN_VALUES for ch in stripped):
        return None
    total = 0
    prev = 0
    for ch in reversed(stripped):
        value = _ROMAN_VALUES[ch]
        if value < prev:
            total -= value
        else:
            total += value
            prev = value
    return total or None


def _int_to_roman(value: int) -> str:
    if value <= 0:
        raise ValueError("Ion stage must be positive")
    numerals = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    remaining = value
    result = []
    for magnitude, numeral in numerals:
        while remaining >= magnitude:
            result.append(numeral)
            remaining -= magnitude
    return "".join(result)


def _parse_ion_token(token: str | int | None) -> Optional[int]:
    if token is None:
        return None
    if isinstance(token, int):
        return token if token > 0 else None
    if isinstance(token, str):
        stripped = token.strip()
        if not stripped:
            return None
        if stripped.isdigit():
            value = int(stripped)
            return value if value > 0 else None
        plus_count = stripped.count("+")
        if plus_count:
            return plus_count + 1
        roman = _roman_to_int(stripped)
        if roman:
            return roman
    return None


def _resolve_spectrum(
    *,
    element: str | None = None,
    linename: str | None = None,
    ion_stage: str | int | None = None,
) -> Tuple[ElementRecord, int, str, str, str]:
    """Return the element metadata and formatted spectrum identifier."""

    chosen_element: Optional[ElementRecord] = None
    stage_value: Optional[int] = _parse_ion_token(ion_stage)

    def inspect_tokens(tokens: Iterable[str]) -> None:
        nonlocal chosen_element, stage_value
        for token in tokens:
            candidate = token.strip()
            if not candidate:
                continue
            if chosen_element is None:
                try:
                    chosen_element = _lookup_element(candidate)
                    continue
                except ValueError:
                    pass
            parsed = _parse_ion_token(candidate)
            if parsed:
                stage_value = stage_value or parsed

    if linename:
        inspect_tokens(re.split(r"[\s,/;]+", linename))
    if element and chosen_element is None:
        inspect_tokens(re.split(r"[\s,/;]+", element))

    if chosen_element is None:
        if linename:
            raise ValueError(f"Could not resolve element from identifier {linename!r}")
        raise ValueError("Element identifier is required for NIST queries")

    stage_value = stage_value or 1
    stage_roman = _int_to_roman(stage_value)
    spectrum = f"{chosen_element.symbol} {stage_roman}"
    label = f"{chosen_element.symbol} {stage_roman} (NIST ASD)"
    return chosen_element, stage_value, stage_roman, spectrum, label


def _extract_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isnan(value):  # type: ignore[arg-type]
            return None
        return float(value)
    text = str(value).strip()
    if not text or text in {"-", "--"}:
        return None
    match = _FLOAT_PATTERN.search(text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _scaled_float(value: Optional[float], scale: float) -> Optional[float]:
    if value is None:
        return None
    scaled = value * scale
    try:
        as_float = float(scaled)
    except Exception:
        return None
    if not math.isfinite(as_float):
        return None
    return as_float


def _column_scale_to_nm(table: Any, column: str, default: float = 1.0) -> float:
    # Import astropy.units lazily to avoid triggering heavy imports at module import time
    try:
        import astropy.units as u  # type: ignore
    except Exception:
        return default

    if table is None or column not in getattr(table, "colnames", []):
        return default
    col = table[column]
    unit = getattr(col, "unit", None)
    if unit is not None:
        try:
            return u.Unit(unit).to(u.nm)
        except Exception:
            try:
                return 1.0 / u.Unit(unit).to(1 / u.nm)
            except Exception:
                return default
    metadata_unit = getattr(getattr(col, "info", None), "unit", None)
    if metadata_unit is not None:
        try:
            return u.Unit(metadata_unit).to(u.nm)
        except Exception:
            try:
                return 1.0 / u.Unit(metadata_unit).to(1 / u.nm)
            except Exception:
                return default
    return default


def _resolve_wavelength_unit(label: str) -> Tuple[Any, str]:
    # Import astropy.units lazily
    try:
        import astropy.units as u  # type: ignore
    except Exception:
        # Fallback: pretend everything is nm
        return ("nm", "nm")

    normalized = (label or "nm").strip().lower()
    aliases = {
        "nm": (u.nm, "nm"),
        "nanometer": (u.nm, "nm"),
        "nanometre": (u.nm, "nm"),
        "angstrom": (u.AA, "angstrom"),
        "ångström": (u.AA, "angstrom"),
        "å": (u.AA, "angstrom"),
        "aa": (u.AA, "angstrom"),
        "um": (u.um, "um"),
        "µm": (u.um, "um"),
        "micron": (u.um, "um"),
        "micrometer": (u.um, "um"),
        "micrometre": (u.um, "um"),
    }
    if normalized in aliases:
        return aliases[normalized]
    try:
        unit = u.Unit(label)
        return unit, unit.to_string()
    except Exception:
        return u.nm, "nm"


def fetch_lines(
    identifier: str,
    *,
    element: str | None = None,
    ion_stage: str | int | None = None,
    lower_wavelength: float | None = None,
    upper_wavelength: float | None = None,
    wavelength_unit: str = "nm",
    use_ritz: bool = True,
    wavelength_type: str = "vacuum",
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Return spectral line data for the requested element/ion combination.
    
    Args:
        identifier: Element identifier (symbol, name, or combined with ion stage)
        element: Optional separate element identifier
        ion_stage: Ion stage (I, II, III, 1, 2, 3, or +, ++, etc.)
        lower_wavelength: Lower wavelength bound for query
        upper_wavelength: Upper wavelength bound for query
        wavelength_unit: Unit for wavelength bounds (nm, angstrom, um, etc.)
        use_ritz: Prefer Ritz wavelengths over observed when available
        wavelength_type: Wavelength type ('vacuum' or 'air')
        use_cache: Whether to use cached results (default: True)
    
    Returns:
        Dictionary with wavelength_nm, intensity, intensity_normalized, lines, and meta keys.
        Meta includes cache_hit boolean indicating whether data came from cache.
    """

    # Resolve identifiers first (no heavy imports)
    element_record, stage_value, stage_roman, spectrum, label = _resolve_spectrum(
        element=element,
        linename=identifier,
        ion_stage=ion_stage,
    )
    lower = lower_wavelength if lower_wavelength is not None else DEFAULT_LOWER_WAVELENGTH_NM
    upper = upper_wavelength if upper_wavelength is not None else DEFAULT_UPPER_WAVELENGTH_NM
    if lower > upper:
        lower, upper = upper, lower

    # Try cache first if enabled
    cache_hit = False
    if use_cache:
        cache = get_cache()
        if cache.enabled:
            cached_data = cache.get(
                element_record.symbol,
                stage_value,
                lower,
                upper,
            )
            if cached_data is not None:
                cached_data["meta"]["cache_hit"] = True
                return cached_data

    # Import heavy deps lazily only when needed (post cache-miss)
    # Prefer a patched Nist (from tests) if provided; otherwise import.
    _Nist = globals().get("Nist", None)
    try:
        if _Nist is None:
            if not ASTROQUERY_AVAILABLE:
                # Attempt import anyway; ASTROQUERY_AVAILABLE may be a hint only
                raise ImportError("astroquery not pre-validated")
            # If available, still import to obtain class
            from astroquery.nist import Nist as _RealNist  # type: ignore
            _Nist = _RealNist
    except Exception as exc:
        # Last attempt to import without relying on ASTROQUERY_AVAILABLE
        try:
            from astroquery.nist import Nist as _RealNist  # type: ignore
            _Nist = _RealNist
        except Exception as inner_exc:
            raise NistUnavailableError(
                "astroquery.nist (and astropy.units) are required to query the NIST ASD"
            ) from inner_exc

    # Units import (used for query bounds and column scaling)
    try:
        import astropy.units as u  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise NistUnavailableError(
            "astropy.units is required to query the NIST ASD"
        ) from exc

    unit, canonical_unit = _resolve_wavelength_unit(wavelength_unit)

    # Cache miss or disabled - fetch from NIST
    min_wavelength = u.Quantity(lower, unit)
    max_wavelength = u.Quantity(upper, unit)

    try:
        table = _Nist.query(
            min_wavelength,
            max_wavelength,
            linename=spectrum,
            wavelength_type=wavelength_type,
        )
    except Exception as exc:
        raise NistQueryError(f"Failed to query NIST ASD: {exc}") from exc

    lines: List[Dict[str, Any]] = []
    max_relative_intensity = 0.0

    observed_scale = _column_scale_to_nm(table, "Observed", default=1.0)
    ritz_scale = _column_scale_to_nm(table, "Ritz", default=1.0)

    if table is not None:
        for row in table:
            if not isinstance(row, Mapping):
                row = {name: row[name] for name in table.colnames}
            observed_value = _extract_float(row.get("Observed"))
            ritz_value = _extract_float(row.get("Ritz"))

            observed_nm = _scaled_float(observed_value, observed_scale)
            ritz_nm = _scaled_float(ritz_value, ritz_scale)

            if use_ritz and ritz_nm is not None:
                chosen_nm = ritz_nm
            elif observed_nm is not None:
                chosen_nm = observed_nm
            else:
                chosen_nm = ritz_nm

            if chosen_nm is None:
                continue

            relative_intensity = _extract_float(row.get("Rel."))
            if relative_intensity is not None:
                max_relative_intensity = max(max_relative_intensity, relative_intensity)

            aki = _extract_float(row.get("Aki"))
            fik = _extract_float(row.get("fik"))
            energy_lower, energy_upper = _split_energy(row.get("Ei           Ek"))

            lines.append(
                {
                    "wavelength_nm": chosen_nm,
                    "observed_wavelength_nm": observed_nm,
                    "ritz_wavelength_nm": ritz_nm,
                    "relative_intensity": relative_intensity,
                    "transition_probability_s": aki,
                    "oscillator_strength": fik,
                    "accuracy": _clean_text(row.get("Acc.")),
                    "lower_level": _clean_text(row.get("Lower level")),
                    "upper_level": _clean_text(row.get("Upper level")),
                    "transition_type": _clean_text(row.get("Type")),
                    "transition_probability_reference": _clean_text(row.get("TP")),
                    "line_reference": _clean_text(row.get("Line")),
                    "lower_level_energy_ev": energy_lower,
                    "upper_level_energy_ev": energy_upper,
                }
            )

    intensities = [line.get("relative_intensity") for line in lines]
    if max_relative_intensity <= 0:
        max_relative_intensity = 0.0
    for line in lines:
        rel = line.get("relative_intensity")
        if rel is None or max_relative_intensity <= 0:
            line["relative_intensity_normalized"] = None
        else:
            line["relative_intensity_normalized"] = rel / max_relative_intensity

    wavelength_series = [line["wavelength_nm"] for line in lines]
    normalized_series = [line.get("relative_intensity_normalized") for line in lines]

    meta = {
        "source_type": "reference",
        "archive": "NIST ASD",
        "label": label,
        "element_symbol": element_record.symbol,
        "element_name": element_record.name,
        "atomic_number": element_record.number,
        "ion_stage": stage_roman,
        "ion_stage_number": stage_value,
        "query": {
            "linename": spectrum,
            "identifier": identifier,
            "lower_wavelength": float(lower),
            "upper_wavelength": float(upper),
            "wavelength_unit": canonical_unit,
            "wavelength_type": wavelength_type,
            "use_ritz": use_ritz,
        },
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "citation": "Kramida, A. et al. (NIST ASD), https://physics.nist.gov/asd",
        "retrieved_via": "astroquery.nist",
        "cache_hit": cache_hit,
    }

    if not lines:
        meta["note"] = "No spectral lines returned for requested range."

    result = {
        "wavelength_nm": wavelength_series,
        "intensity": intensities,
        "intensity_normalized": normalized_series,
        "lines": lines,
        "meta": meta,
    }

    # Store in cache for future use
    if use_cache:
        cache = get_cache()
        if cache.enabled:
            cache.set(
                element_record.symbol,
                stage_value,
                lower,
                upper,
                result,
            )

    return result


def _split_energy(value: Any) -> Tuple[Optional[float], Optional[float]]:
    text = str(value).strip()
    if not text or text in {"-", "--"}:
        return (None, None)
    matches = _FLOAT_PATTERN.findall(text.replace(",", ""))
    if not matches:
        return (None, None)
    lower = float(matches[0]) if matches else None
    upper = float(matches[1]) if len(matches) > 1 else None
    return (lower, upper)


def _clean_text(value: Any) -> Optional[str]:
    text = str(value).strip()
    if not text or text in {"-", "--"}:
        return None
    return re.sub(r"\s+", " ", text)

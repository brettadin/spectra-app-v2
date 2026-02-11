"""Abstractions for retrieving remote spectral catalogues and downloads."""

# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportGeneralTypeIssues=false

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence
from urllib.parse import quote, urlencode, urlparse

from . import nist_asd_service
from .store import LocalStore

try:  # Optional dependency – requests may be absent in minimal installs
    import requests
except Exception:  # pragma: no cover - handled by dependency guards
    requests = None  # type: ignore[assignment]

# Lazy import sentinels for heavy optional dependencies; avoid importing at module load
astroquery_mast = None  # type: ignore[assignment]
astroquery_nexsci = None  # type: ignore[assignment]

# Default timeout for individual MAST queries (seconds)
_MAST_QUERY_TIMEOUT = 30

# Probe availability without importing the modules eagerly
import importlib.util as _importlib_util

def _spec_exists(module_name: str) -> bool:
    try:
        return _importlib_util.find_spec(module_name) is not None
    except Exception:
        return False


def _has_module(module_name: str) -> bool:
    return _spec_exists(module_name)


def _import_mast():
    global astroquery_mast
    if astroquery_mast is None:
        from astroquery import mast as _mast  # type: ignore
        astroquery_mast = _mast
    return astroquery_mast


def _import_exoplanet_archive():
    global astroquery_nexsci
    if astroquery_nexsci is None:
        from astroquery.ipac.nexsci.nasa_exoplanet_archive import (
            NasaExoplanetArchive as _archive,  # type: ignore
        )
        astroquery_nexsci = _archive
    return astroquery_nexsci


def prewarm_astroquery() -> None:
    """Pre-import astropy and astroquery on the main thread.
    
    This MUST be called from the main thread before any background searches.
    Astropy's ERFA library has thread-safety issues on Windows when first
    imported from a background thread, causing fatal crashes.
    """
    try:
        # Import astropy coordinates - this triggers ERFA initialization
        import astropy.coordinates  # noqa: F401
        # Also import the archives we use
        _import_mast()
        _import_exoplanet_archive()
    except Exception:
        pass  # Fail silently - will be tried again later if needed


# Module-level probe flags (tests monkeypatch these)
_HAS_PANDAS = False

def _initialise_dependency_flags() -> None:
    global _HAS_PANDAS
    try:
        _HAS_PANDAS = _has_module("pandas")
    except Exception:
        _HAS_PANDAS = False


_initialise_dependency_flags()


def _has_pandas() -> bool:
    return bool(_HAS_PANDAS)


@dataclass
class RemoteRecord:
    """Normalised representation of a remote catalogue entry."""

    provider: str
    identifier: str
    title: str
    download_url: str
    metadata: Dict[str, Any]
    units: Mapping[str, str] | None = None

    def suggested_filename(self) -> str:
        """Derive a filename from the download URL or identifier."""

        parsed = urlparse(self.download_url)
        candidate = Path(parsed.path).name
        if candidate:
            return candidate
        return f"{self.identifier}.dat"

    def resolved_units(self) -> tuple[str, str]:
        units = dict(self.units or {})
        x_unit = units.get("x", "unknown") or "unknown"
        y_unit = units.get("y", "unknown") or "unknown"
        return x_unit, y_unit


@dataclass
class RemoteDownloadResult:
    """Summary of a persisted remote download."""

    record: RemoteRecord
    cache_entry: Dict[str, Any]
    path: Path
    cached: bool = False


@dataclass(frozen=True)
class LocalSample:
    """Descriptor for a curated on-disk sample spectrum."""

    sample_id: str
    label: str
    path: Path
    description: str = ""
    range_hint: str = ""
    instrument: str = ""
    credit: str = ""


@dataclass
class RemoteDataService:
    """Facade over remote catalogue searches and download persistence."""

    store: LocalStore
    session: Any | None = None
    clock: Any = datetime.now
    mast_product_fields: Iterable[str] = field(
        default_factory=lambda: ("obsid", "target_name", "productFilename", "dataURI")
    )
    nist_page_size: int = 100

    PROVIDER_NIST = "NIST ASD"
    PROVIDER_MAST = "MAST"
    PROVIDER_EXOSYSTEMS = "MAST ExoSystems"  # Deprecated
    PROVIDER_EXOPLANET_ARCHIVE = "NASA Exoplanet Archive"
    PROVIDER_EXOMAST = "Exo.MAST"  # Curated exoplanet spectra

    _DEFAULT_REGION_RADIUS = "0.02 deg"
    _SAMPLES_ROOT = Path(__file__).resolve().parents[2] / "samples"
    _SOLAR_SYSTEM_ROOT = _SAMPLES_ROOT / "solar_system"

    _CURATED_TARGETS: tuple[Dict[str, Any], ...] = (
        {
            "names": {"mercury"},
            "display_name": "Mercury",
            "object_name": "Mercury",
            "classification": "Solar System planet",
            "category": "solar_system",
            "local_samples": [
                {
                    "id": "mercury-visible",
                    "label": "Visible reflectance (350-700 nm)",
                    "path": "solar_system/mercury/mercury_visible.csv",
                    "description": "Simulated MASCS reflectance trace across the visible band.",
                    "instrument": "MESSENGER MASCS",
                    "range": "350-700 nm",
                },
                {
                    "id": "mercury-infrared",
                    "label": "Thermal emission (1000-2400 nm)",
                    "path": "solar_system/mercury/mercury_infrared.csv",
                    "description": "Thermal continuum sample representative of Mercury's dayside.",
                    "instrument": "MESSENGER MASCS",
                    "range": "1000-2400 nm",
                },
            ],
            "citations": [
                {
                    "title": "MESSENGER MASCS reflectance spectra",
                    "url": "https://pds.nasa.gov/ds-view/pds/viewDataset.jsp?dsid=MESS-H-MASCS-3-RDR-V1.0",
                    "notes": "Planetary Data System calibrated spectra for Mercury's dayside.",
                }
            ],
        },
        {
            "names": {"venus"},
            "display_name": "Venus",
            "object_name": "Venus",
            "classification": "Solar System planet",
            "category": "solar_system",
            "local_samples": [
                {
                    "id": "venus-visible",
                    "label": "Cloud reflectance (350-700 nm)",
                    "path": "solar_system/venus/venus_visible.csv",
                    "description": "VIRTIS-style reflectance averaged across the visible band.",
                    "instrument": "Venus Express VIRTIS",
                    "range": "350-700 nm",
                },
                {
                    "id": "venus-infrared",
                    "label": "Thermal emission (1000-2400 nm)",
                    "path": "solar_system/venus/venus_infrared.csv",
                    "description": "Thermal signature of Venusian cloud tops in the near/mid infrared.",
                    "instrument": "Venus Express VIRTIS",
                    "range": "1000-2400 nm",
                },
            ],
            "citations": [
                {
                    "title": "Venus Express VIRTIS spectral survey",
                    "url": "https://archives.esac.esa.int/psa/ftp/VENUS-EXPRESS/VIRTIS/",
                    "notes": "VIRTIS calibrated cubes spanning UV through thermal infrared.",
                }
            ],
        },
        {
            "names": {"earth", "earth-moon", "terra"},
            "display_name": "Earth",
            "object_name": "Earth",
            "classification": "Solar System planet",
            "category": "solar_system",
            "local_samples": [
                {
                    "id": "earth-visible",
                    "label": "Visible disc reflectance (350-700 nm)",
                    "path": "solar_system/earth/earth_visible.csv",
                    "description": "EPOXI-inspired whole-Earth reflectance across the visible band.",
                    "instrument": "EPOXI MRI",
                    "range": "350-700 nm",
                },
                {
                    "id": "earth-infrared",
                    "label": "Thermal emission (1000-2400 nm)",
                    "path": "solar_system/earth/earth_infrared.csv",
                    "description": "Disc-averaged thermal emission sample used for benchmarking.",
                    "instrument": "EPOXI HRI-IR",
                    "range": "1000-2400 nm",
                },
            ],
            "citations": [
                {
                    "title": "EPOXI Earth Observations",
                    "url": "https://pds.nasa.gov/ds-view/pds/viewDataset.jsp?dsid=EPOXI-C/EARTH-MRI/HRII-5-EPOXI-EARTH-V1.0",
                    "notes": "Disc-integrated Earth spectra captured during the EPOXI flyby.",
                }
            ],
        },
        {
            "names": {"mars"},
            "display_name": "Mars",
            "object_name": "Mars",
            "classification": "Solar System planet",
            "category": "solar_system",
            "local_samples": [
                {
                    "id": "mars-visible",
                    "label": "Dust reflectance (350-700 nm)",
                    "path": "solar_system/mars/mars_visible.csv",
                    "description": "Representative visible reflectance of dusty equatorial regions.",
                    "instrument": "JWST NIRSpec quick-look",
                    "range": "350-700 nm",
                },
                {
                    "id": "mars-infrared",
                    "label": "Thermal emission (1000-2400 nm)",
                    "path": "solar_system/mars/mars_infrared.csv",
                    "description": "Thermal continuum sample highlighting CO2 absorption structure.",
                    "instrument": "JWST NIRSpec",
                    "range": "1000-2400 nm",
                },
            ],
            "citations": [
                {
                    "title": "JWST/NIRSpec Mars observations",
                    "doi": "10.3847/1538-4365/abf3cb",
                    "notes": "Quick-look spectra distributed via Exo.MAST science highlights.",
                }
            ],
        },
        {
            "names": {"jupiter", "io", "europa", "ganymede", "callisto"},
            "display_name": "Jupiter",
            "object_name": "Jupiter",
            "classification": "Solar System planet",
            "category": "solar_system",
            "local_samples": [
                {
                    "id": "jupiter-visible",
                    "label": "Cloud reflectance (350-700 nm)",
                    "path": "solar_system/jupiter/jupiter_visible.csv",
                    "description": "Visible-band reflectance capturing ammonia cloud structure.",
                    "instrument": "JWST ERS",
                    "range": "350-700 nm",
                },
                {
                    "id": "jupiter-infrared",
                    "label": "Thermal emission (1000-2400 nm)",
                    "path": "solar_system/jupiter/jupiter_infrared.csv",
                    "description": "Thermal emission continuum with methane absorption features.",
                    "instrument": "JWST ERS",
                    "range": "1000-2400 nm",
                },
            ],
            "citations": [
                {
                    "title": "JWST Early Release Observations",
                    "doi": "10.3847/1538-4365/acbd9a",
                    "notes": "JWST ERS quick-look spectra curated for Jovian system.",
                }
            ],
        },
        {
            "names": {"saturn", "enceladus", "titan"},
            "display_name": "Saturn",
            "object_name": "Saturn",
            "classification": "Solar System planet",
            "category": "solar_system",
            "local_samples": [
                {
                    "id": "saturn-visible",
                    "label": "Ring and cloud reflectance (350-700 nm)",
                    "path": "solar_system/saturn/saturn_visible.csv",
                    "description": "Composite reflectance for Saturn's disc and main rings.",
                    "instrument": "Cassini VIMS",
                    "range": "350-700 nm",
                },
                {
                    "id": "saturn-infrared",
                    "label": "Thermal emission (1000-2400 nm)",
                    "path": "solar_system/saturn/saturn_infrared.csv",
                    "description": "Thermal spectrum combining Cassini and JWST highlights.",
                    "instrument": "Cassini VIMS",
                    "range": "1000-2400 nm",
                },
            ],
            "citations": [
                {
                    "title": "Cassini & JWST comparative spectra",
                    "url": "https://pds-rings.seti.org/",
                    "notes": "Composite set used in Spectra examples for Saturnian system.",
                }
            ],
        },
        {
            "names": {"uranus"},
            "display_name": "Uranus",
            "object_name": "Uranus",
            "classification": "Solar System planet",
            "category": "solar_system",
            "local_samples": [
                {
                    "id": "uranus-visible",
                    "label": "Methane-band reflectance (350-700 nm)",
                    "path": "solar_system/uranus/uranus_visible.csv",
                    "description": "HST-inspired reflectance capturing methane absorption in the visible.",
                    "instrument": "HST/STIS",
                    "range": "350-700 nm",
                },
                {
                    "id": "uranus-infrared",
                    "label": "Thermal emission (1000-2400 nm)",
                    "path": "solar_system/uranus/uranus_infrared.csv",
                    "description": "NICMOS-style thermal emission template for Uranus.",
                    "instrument": "HST/NICMOS",
                    "range": "1000-2400 nm",
                },
            ],
            "citations": [
                {
                    "title": "HST/STIS Uranus atlas",
                    "url": "https://archive.stsci.edu/hst/",
                    "notes": "Calibrated ultraviolet-through-infrared spectra from STIS and NICMOS.",
                }
            ],
        },
        {
            "names": {"neptune"},
            "display_name": "Neptune",
            "object_name": "Neptune",
            "classification": "Solar System planet",
            "category": "solar_system",
            "local_samples": [
                {
                    "id": "neptune-visible",
                    "label": "Methane-band reflectance (350-700 nm)",
                    "path": "solar_system/neptune/neptune_visible.csv",
                    "description": "NICMOS-inspired reflectance tracing methane absorption.",
                    "instrument": "HST/NICMOS",
                    "range": "350-700 nm",
                },
                {
                    "id": "neptune-infrared",
                    "label": "Thermal emission (1000-2400 nm)",
                    "path": "solar_system/neptune/neptune_infrared.csv",
                    "description": "Thermal continuum sample of Neptune's upper atmosphere.",
                    "instrument": "HST/NICMOS",
                    "range": "1000-2400 nm",
                },
            ],
            "citations": [
                {
                    "title": "HST/NICMOS Neptune program",
                    "url": "https://archive.stsci.edu/missions-and-data/hst",
                    "notes": "NICMOS calibrations spanning methane absorption bands.",
                }
            ],
        },
        {
            "names": {"pluto", "pluto-charon"},
            "display_name": "Pluto",
            "object_name": "Pluto",
            "classification": "Solar System planet",
            "category": "solar_system",
            "local_samples": [
                {
                    "id": "pluto-visible",
                    "label": "Disc reflectance (350-700 nm)",
                    "path": "solar_system/pluto/pluto_visible.csv",
                    "description": "New Horizons LEISA-derived reflectance across visible wavelengths.",
                    "instrument": "New Horizons LEISA",
                    "range": "350-700 nm",
                },
                {
                    "id": "pluto-infrared",
                    "label": "Thermal emission (1000-2400 nm)",
                    "path": "solar_system/pluto/pluto_infrared.csv",
                    "description": "Thermal sample illustrating methane and nitrogen absorption bands.",
                    "instrument": "New Horizons LEISA",
                    "range": "1000-2400 nm",
                },
            ],
            "citations": [
                {
                    "title": "New Horizons LEISA spectral maps",
                    "url": "https://pds.nasa.gov/ds-view/pds/viewDataset.jsp?dsid=NH-P-LEISA-3-PLUTO-V3.0",
                    "notes": "LEISA calibrated cubes covering methane and nitrogen bands.",
                }
            ],
        },
        {
            "names": {"g2v", "solar analog", "sun-like", "hd 10700", "tau ceti"},
            "display_name": "Tau Ceti (G8V)",
            "object_name": "HD 10700",
            "classification": "Nearby solar-type star",
            "category": "stellar_standard",
            "citations": [
                {
                    "title": "Pickles stellar spectral library",
                    "doi": "10.1086/316293",
                    "notes": "Representative solar-type spectrum maintained in Spectra samples.",
                }
            ],
        },
        {
            "names": {"a0v", "vega"},
            "display_name": "Vega (A0V)",
            "object_name": "Vega",
            "classification": "Spectral standard",
            "category": "stellar_standard",
            "citations": [
                {
                    "title": "HST CALSPEC standards",
                    "doi": "10.1086/383228",
                    "notes": "CALSPEC flux standards distributed via MAST.",
                }
            ],
        },
        {
            "names": {"hd 189733"},
            "display_name": "HD 189733",
            "object_name": "HD 189733",
            "classification": "Active K dwarf host star",
            "category": "host_star",
            "citations": [
                {
                    "title": "HD 189733 stellar monitoring",
                    "url": "https://archive.stsci.edu/hlsp/hd189733/",
                    "notes": "HST and JWST monitoring programs capturing the host star spectrum.",
                }
            ],
        },
        {
            "names": {"hd 189733 b"},
            "display_name": "HD 189733 b",
            "object_name": "HD 189733 b",
            "planet_name": "HD 189733 b",
            "host_name": "HD 189733",
            "classification": "Transiting exoplanet",
            "category": "exoplanet",
            "ra": 300.1821,
            "dec": 22.7099,
            "search_radius": "0.05 deg",
            "citations": [
                {
                    "title": "JWST Early Release Science: HD 189733 b",
                    "url": "https://jwst-docs.stsci.edu/",
                    "notes": "Transit spectroscopy spanning 0.8–5 μm.",
                }
            ],
        },
        {
            "names": {"wasp-39", "wasp-39 b"},
            "display_name": "WASP-39 b",
            "object_name": "WASP-39",
            "planet_name": "WASP-39 b",
            "host_name": "WASP-39",
            "classification": "Transiting exoplanet",
            "category": "exoplanet",
            "ra": 210.1234,
            "dec": -39.1234,
            "search_radius": "0.05 deg",
            "citations": [
                {
                    "title": "JWST ERS Transmission Spectra",
                    "doi": "10.1038/s41586-022-05439-6",
                    "notes": "WASP-39 b transmission spectra released through Exo.MAST.",
                }
            ],
        },
        {
            "names": {"trappist-1", "trappist-1e", "trappist-1 system"},
            "display_name": "TRAPPIST-1 system",
            "object_name": "TRAPPIST-1",
            "classification": "Ultracool dwarf planetary system",
            "category": "exoplanet_system",
            "citations": [
                {
                    "title": "Spitzer and JWST phase curve campaigns",
                    "url": "https://exo.mast.stsci.edu/exomast_planet.html?planet=TRAPPIST-1%20e",
                    "notes": "Combined photometry and spectroscopic programs for TRAPPIST-1 planets.",
                }
            ],
        },
    )

    def curated_targets(
        self,
        *,
        category: str | None = None,
        classification: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Return curated targets filtered by category or classification."""

        targets: List[Dict[str, Any]] = []
        for entry in self._CURATED_TARGETS:
            if category and entry.get("category") != category:
                continue
            if classification and entry.get("classification") != classification:
                continue

            names = entry.get("names", set())
            if not isinstance(names, set):
                names = set(names)
            canonical_names = {str(name).strip() for name in names if str(name).strip()}
            canonical_names.add(str(entry.get("display_name", "")).lower())
            canonical_names.add(str(entry.get("object_name", "")).lower())

            payload = dict(entry)
            payload["names"] = sorted(canonical_names)
            if entry.get("local_samples"):
                payload["local_samples"] = list(entry.get("local_samples") or [])
            targets.append(payload)
        return targets

    def local_samples(self, target: Mapping[str, Any]) -> List[LocalSample]:
        """Resolve curated local samples for the provided target entry."""

        entries = target.get("local_samples")
        if not isinstance(entries, Sequence):
            return []

        samples: List[LocalSample] = []
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            path_str = str(entry.get("path") or "").strip()
            label = str(entry.get("label") or "").strip()
            if not path_str or not label:
                continue
            resolved = self._resolve_sample_path(path_str)
            if resolved is None or not resolved.exists():
                continue
            sample_id = str(entry.get("id") or resolved.stem)
            description = str(entry.get("description") or "").strip()
            range_hint = str(
                entry.get("range")
                or entry.get("wavelength_range")
                or entry.get("range_hint")
                or ""
            ).strip()
            instrument = str(entry.get("instrument") or "").strip()
            credit = str(entry.get("credit") or entry.get("citation") or "").strip()
            samples.append(
                LocalSample(
                    sample_id=sample_id,
                    label=label,
                    path=resolved,
                    description=description,
                    range_hint=range_hint,
                    instrument=instrument,
                    credit=credit,
                )
            )
        return samples

    @classmethod
    def _resolve_sample_path(cls, raw_path: str) -> Path | None:
        if not raw_path:
            return None
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = cls._SAMPLES_ROOT / candidate
        try:
            candidate.relative_to(cls._SAMPLES_ROOT)
        except ValueError:
            return None
        return candidate

    def providers(self) -> List[str]:
        """Return the list of remote providers whose dependencies are satisfied."""

        providers: List[str] = []
        if self._has_nist_support():
            providers.append(self.PROVIDER_NIST)
        if self._has_exosystem_support():
            # Exo.MAST - Curated exoplanet spectra (BEST for exoplanets!)
            providers.append(self.PROVIDER_EXOMAST)
            # NASA Exoplanet Archive - transmission/emission spectra
            providers.append(self.PROVIDER_EXOPLANET_ARCHIVE)
        if self._has_mast_support():
            # Removed PROVIDER_EXOSYSTEMS - redundant with MAST
            providers.append(self.PROVIDER_MAST)
        return providers

    def unavailable_providers(self) -> Dict[str, str]:
        """Describe catalogues that cannot be used because dependencies are missing."""

        reasons: Dict[str, str] = {}
        if not self._has_nist_support():
            reasons[self.PROVIDER_NIST] = (
                "Install the 'astroquery' package to enable NIST ASD line searches."
            )
        if not self._has_mast_support():
            reasons[self.PROVIDER_MAST] = (
                "Install the 'astroquery' and 'pandas' packages to enable MAST searches."
            )
        if not self._has_exosystem_support():
            reasons[self.PROVIDER_EXOMAST] = (
                "Install 'requests' package to enable Exo.MAST curated exoplanet spectra."
            )
            reasons[self.PROVIDER_EXOPLANET_ARCHIVE] = (
                "Install 'requests' package to enable NASA Exoplanet Archive atmospheric spectra."
            )
        return reasons

    # ------------------------------------------------------------------
    def search(
        self,
        provider: str,
        query: Mapping[str, Any],
        *,
        include_imaging: bool = False,
        cancel_check: Callable[[], bool] | None = None,
    ) -> List[RemoteRecord]:
        if provider == self.PROVIDER_NIST:
            return self._search_nist(query)
        if provider == self.PROVIDER_EXOMAST:
            return self._search_exomast(query)
        if provider == self.PROVIDER_EXOPLANET_ARCHIVE:
            return self._search_exoplanet_archive_spectra(query)
        if provider == self.PROVIDER_MAST:
            return self._search_mast(query, include_imaging=include_imaging)
        # Removed EXOSYSTEMS routing - now use MAST directly
        raise ValueError(f"Unsupported provider: {provider}")

    # ------------------------------------------------------------------
    def download(
        self,
        record: RemoteRecord,
        *,
        force: bool = False,
        progress: Callable[[RemoteRecord, int, int | None], None] | None = None,
    ) -> RemoteDownloadResult:
        cached = None if force else self._find_cached(record.download_url)
        if cached is not None:
            return RemoteDownloadResult(
                record=record,
                cache_entry=cached,
                path=Path(cached["stored_path"]),
                cached=True,
            )

        print(f"[Download] record.provider = '{record.provider}'")
        print(f"[Download] PROVIDER_EXOMAST = '{self.PROVIDER_EXOMAST}'")
        print(f"[Download] Match? {record.provider == self.PROVIDER_EXOMAST}")

        # Handle NASA Exoplanet Archive TAP queries (return CSV directly)
        if record.provider == self.PROVIDER_EXOPLANET_ARCHIVE and 'TAP/sync' in record.download_url:
            return self._download_tap_csv(record, progress=progress)

        # Handle Exo.MAST TSV files (tab-separated with comments)
        if record.provider == self.PROVIDER_EXOMAST:
            return self._download_exomast_tsv(record, progress=progress)

        fetch_path = self._fetch_remote(record, progress=progress)

        x_unit, y_unit = record.resolved_units()
        remote_metadata = {
            "provider": record.provider,
            "uri": record.download_url,
            "identifier": record.identifier,
            "fetched_at": self._timestamp(),
            "metadata": self._json_safe(record.metadata),
        }
        store_entry = self.store.record(
            fetch_path,
            x_unit=x_unit,
            y_unit=y_unit,
            source={"remote": remote_metadata},
            alias=record.suggested_filename(),
        )

        return RemoteDownloadResult(
            record=record,
            cache_entry=store_entry,
            path=Path(store_entry["stored_path"]),
            cached=False,
        )

    # ------------------------------------------------------------------
    def _search_nist(self, query: Mapping[str, Any]) -> List[RemoteRecord]:
        identifier = str(query.get("element") or query.get("text") or "").strip()
        if not identifier:
            raise ValueError("NIST searches require an element or spectrum identifier.")

        lower = query.get("wavelength_min")
        upper = query.get("wavelength_max")
        try:
            payload = nist_asd_service.fetch_lines(
                identifier,
                element=query.get("element"),
                ion_stage=query.get("ion_stage"),
                lower_wavelength=float(lower) if lower is not None else None,
                upper_wavelength=float(upper) if upper is not None else None,
                wavelength_unit=str(query.get("wavelength_unit") or "nm"),
                use_ritz=bool(query.get("use_ritz", True)),
                wavelength_type=str(query.get("wavelength_type") or "vacuum"),
            )
        except (nist_asd_service.NistUnavailableError, nist_asd_service.NistQueryError) as exc:
            raise RuntimeError(str(exc)) from exc

        lines = payload.get("lines", [])
        meta = dict(payload.get("meta", {}))
        meta["query_text"] = identifier
        meta["line_count"] = len(lines)
        meta.setdefault("series", {})
        meta["series"]["wavelength_nm"] = payload.get("wavelength_nm", [])
        meta["series"]["relative_intensity"] = payload.get("intensity", [])
        meta["series"]["relative_intensity_normalized"] = payload.get(
            "intensity_normalized", []
        )
        meta["lines"] = lines

        label = meta.get("label") or identifier
        line_count = len(lines)
        title = f"{label} — {line_count} line{'s' if line_count != 1 else ''}"
        download_token = label.replace(" ", "_")
        record = RemoteRecord(
            provider=self.PROVIDER_NIST,
            identifier=label,
            title=title,
            download_url=f"nist-asd:{download_token}",
            metadata=meta,
            units={"x": "nm", "y": "relative_intensity"},
        )
        return [record]

    def _search_mast(
        self,
        query: Mapping[str, Any],
        *,
        include_imaging: bool = False,
    ) -> List[RemoteRecord]:
        text_raw = str(query.get("text") or query.get("target_name") or "").strip()
        if not text_raw:
            raise ValueError("MAST ExoSystems searches require a planet, star, or system name.")

        # Try a few normalizations to improve hit rate (e.g., WASP-39 b vs wasp39b)
        variants = {
            text_raw,
            text_raw.replace(" ", ""),
            text_raw.replace("-", " "),
            text_raw.replace("-", ""),
            text_raw.upper(),
            text_raw.lower(),
        }
        systems: List[Dict[str, Any]] = []
        for variant in variants:
            try:
                systems = self._resolve_exosystem_targets(variant)
            except Exception:
                systems = []
            if systems:
                break

        records: List[RemoteRecord] = []
        for system in systems:
            records.extend(self._collect_exosystem_products(system, include_imaging=include_imaging))

        if not records:
            try:
                records = self._search_mast({"target_name": text_raw}, include_imaging=include_imaging)
            except Exception:
                records = []
        criteria.setdefault("intentType", "SCIENCE")
        if "calib_level" not in criteria:
            criteria["calib_level"] = [2, 3]

        mast = self._ensure_mast()
        observation_table = mast.Observations.query_criteria(**criteria)
        return self._records_from_mast_products(
            observation_table,
            include_imaging=include_imaging,
            provider=self.PROVIDER_MAST,
        )

    def _search_exosystems(
        self,
        query: Mapping[str, Any],
        *,
        include_imaging: bool = False,
        cancel_check: Callable[[], bool] | None = None,
    ) -> List[RemoteRecord]:
        """Search ExoSystems (exoplanets and host stars) via MAST.
        
        Args:
            query: Search parameters with 'text' or 'target_name'
            include_imaging: Whether to include imaging products
            cancel_check: Optional callback that returns True if search should be cancelled
        """
        text = str(query.get("text") or query.get("target_name") or "").strip()
        if not text:
            raise ValueError("MAST ExoSystems searches require a planet, star, or system name.")

        # Check for cancellation
        if cancel_check and cancel_check():
            return []

        # First try curated targets only (fast, no network)
        systems = self._match_curated_targets(text)
        
        # Only query exoplanet archive if no curated match found
        if not systems:
            if cancel_check and cancel_check():
                return []
            try:
                systems = self._query_exoplanet_archive(text)
            except Exception:
                systems = []
        
        # Limit to just 1 system to prevent slow searches
        if len(systems) > 1:
            systems = systems[:1]
        
        if cancel_check and cancel_check():
            return []
        
        records: List[RemoteRecord] = []
        for system in systems:
            if cancel_check and cancel_check():
                return records
            try:
                system_records = self._collect_exosystem_products(
                    system, include_imaging=include_imaging, cancel_check=cancel_check
                )
                records.extend(system_records)
                # Stop early if we have enough results
                if len(records) >= self._MAX_MAST_RESULTS:
                    break
            except Exception:
                continue

        # If no results from systems, try direct MAST search
        if not records:
            if cancel_check and cancel_check():
                return []
            try:
                records = self._search_mast({"target_name": text}, include_imaging=include_imaging)
            except Exception:
                records = []

        deduped: List[RemoteRecord] = []
        seen: set[tuple[str, str]] = set()
        for record in records:
            key = (record.download_url, record.identifier)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(record)
        return deduped

    def _is_spectroscopic(self, metadata: Mapping[str, Any]) -> bool:
        """Return True when the MAST row represents spectroscopic data."""

        product = str(metadata.get("dataproduct_type") or "").lower()
        if product in {"spectrum", "spectral_energy_distribution"}:
            return True
        if "spect" in product:
            return True

        product_type = str(metadata.get("productType") or "").lower()
        spectro_tokens = ("spectrum", "spectroscopy", "grism", "ifu", "slit", "prism")
        if any(token in product_type for token in spectro_tokens):
            return True

        description = str(metadata.get("description") or metadata.get("display_name") or "").lower()
        if any(token in description for token in spectro_tokens):
            return True

        return False

    def _is_timeseries(self, metadata: Mapping[str, Any]) -> bool:
        product = str(metadata.get("dataproduct_type") or "").lower()
        if product in {"timeseries", "time_series", "lightcurve", "light_curve"}:
            return True
        product_type = str(metadata.get("productType") or "").lower()
        if "timeseries" in product_type or "time series" in product_type or "lightcurve" in product_type:
            return True
        description = str(metadata.get("description") or metadata.get("display_name") or "").lower()
        if "time series" in description or "timeseries" in description or "lightcurve" in description:
            return True
        return False

    def _normalise_calib_levels(self, value: Any) -> list[int]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            values = value
        else:
            values = [value]

        normalised: list[int] = []
        for item in values:
            try:
                if isinstance(item, str) and not item.strip():
                    continue
                normalised.append(int(float(item)))
            except (TypeError, ValueError):
                continue
        return normalised

    def _is_science_ready(self, metadata: Mapping[str, Any]) -> bool:
        calib_candidates = metadata.get("calib_level")
        if calib_candidates is None:
            calib_candidates = metadata.get("calibLevel")
        levels = self._normalise_calib_levels(calib_candidates)
        if levels and not any(level in {2, 3} for level in levels):
            return False

        intent = metadata.get("intentType") or metadata.get("intent_type")
        if intent:
            if str(intent).strip().upper() != "SCIENCE":
                return False

        dataproduct = str(metadata.get("dataproduct_type") or "").lower()
        if dataproduct and dataproduct not in {"spectrum", "spectral_energy_distribution", "timeseries", "time_series"}:
            # Allow imaging products only when the caller explicitly widens the
            # search. The imaging flag is handled separately in
            # ``_records_from_mast_products``.
            return False

        return True

    def _is_imaging(self, metadata: Mapping[str, Any]) -> bool:
        product = str(metadata.get("dataproduct_type") or "").lower()
        if product in {"image", "image_cube", "preview"}:
            return True
        product_type = str(metadata.get("productType") or "").lower()
        if "image" in product_type or "imaging" in product_type:
            return True
        description = str(metadata.get("description") or metadata.get("display_name") or "").lower()
        if "image" in description:
            return True
        return False

    # Maximum number of records to return from a single MAST search to prevent
    # memory issues and UI freezes with popular targets like "Jupiter"
    _MAX_MAST_RESULTS = 100

    def _records_from_mast_products(
        self,
        observation_table: Any,
        *,
        include_imaging: bool,
        provider: str,
        system_metadata: Mapping[str, Any] | None = None,
    ) -> List[RemoteRecord]:
        mast = self._ensure_mast()
        observation_rows = self._table_to_records(observation_table)
        if not observation_rows:
            return []
        
        # Limit observations to prevent massive queries
        MAX_OBSERVATIONS = 50
        if len(observation_rows) > MAX_OBSERVATIONS:
            observation_rows = observation_rows[:MAX_OBSERVATIONS]
            # Rebuild observation_table with limited rows for get_product_list
            try:
                observation_table = observation_table[:MAX_OBSERVATIONS]
            except Exception:
                pass  # If slicing fails, continue with full table

        observation_index = self._index_observations(observation_rows)
        try:
            product_table = mast.Observations.get_product_list(observation_table)
        except Exception:
            return []  # If product list fails, return empty
        product_rows = self._table_to_records(product_table)
        if not product_rows:
            return []

        # Limit products to prevent memory issues (each obs can have 100+ products)
        MAX_PRODUCTS = 500
        if len(product_rows) > MAX_PRODUCTS:
            product_rows = product_rows[:MAX_PRODUCTS]

        records: List[RemoteRecord] = []
        for product in product_rows:
            # Stop early if we've collected enough results
            if len(records) >= self._MAX_MAST_RESULTS:
                break
            
            # Skip non-science products (AUXILIARY, PREVIEW, INFO files)
            product_type = str(product.get("productType", "")).upper()
            if product_type in ("AUXILIARY", "PREVIEW", "INFO", "THUMBNAIL"):
                continue
                
            metadata = dict(product)
            obs_id = self._normalise_observation_id(metadata)
            observation_meta = observation_index.get(obs_id, {})
            merged: Dict[str, Any] = {**observation_meta, **metadata}

            if include_imaging:
                if not (self._is_spectroscopic(merged) or self._is_timeseries(merged) or self._is_imaging(merged)):
                    continue
            elif not (self._is_spectroscopic(merged) or self._is_timeseries(merged)):
                continue

            if not self._is_science_ready(merged) and not (
                include_imaging and self._is_imaging(merged)
            ):
                continue

            # Only list products we can ingest/display directly (speeds up search and UI)
            if not self._is_supported_product(merged, include_imaging=include_imaging):
                continue

            data_uri = self._first_text(merged, ["dataURI", "data_uri", "ProductURI"])
            if not data_uri:
                continue

            identifier = self._first_text(
                merged,
                [
                    "productFilename",
                    "productFilenameSource",
                    "obs_id",
                    "obsid",
                    "observationID",
                    "dataURI",
                ],
            )
            if not identifier:
                continue

            if system_metadata:
                merged.setdefault("exosystem", dict(system_metadata))
                if "citations" in system_metadata and "citations" not in merged:
                    citations = system_metadata.get("citations")
                    if isinstance(citations, list):
                        merged["citations"] = list(citations)

            title = self._build_mast_title(merged)
            units_map = merged.get("units") if isinstance(merged.get("units"), Mapping) else None
            merged["observation"] = observation_meta

            clean_metadata = self._json_safe(merged)

            records.append(
                RemoteRecord(
                    provider=provider,
                    identifier=str(identifier),
                    title=title,
                    download_url=str(data_uri),
                    metadata=clean_metadata,
                    units=units_map,
                )
            )

        return records

    def _is_supported_product(self, metadata: Mapping[str, Any], *, include_imaging: bool = False) -> bool:
        """Return True when the product's filename/URI matches supported importers.

        We currently support FITS/CSV/JCAMP-DX spectra; skip JPEG/PNG previews and other
        auxiliary files to keep result lists focused and imports reliable.
        
        For FITS files, we prioritize known 1D spectral formats that can actually be plotted:
        - _x1d.fits: 1D extracted spectrum (HST STIS/COS)
        - _sx1.fits: Summed 1D spectrum (HST)
        - _sx2.fits: Summed 2D spectrum 
        - _vo.fits: Virtual Observatory format
        - _spec.fits: Generic spectrum
        - _s1d.fits: JWST 1D spectrum
        - _x1dsum.fits: Combined 1D spectrum
        """
        # Accepted extensions (lowercase with leading dot)
        supported_ext = {".fits", ".fit", ".fts", ".csv", ".txt", ".dat", ".jdx", ".dx", ".jcamp"}
        
        # Known 1D spectral file patterns (preferred - these actually contain plottable 1D spectra)
        spectral_1d_patterns = (
            "_x1d.fits", "_sx1.fits", "_sx2.fits", "_vo.fits", "_spec.fits",
            "_s1d.fits", "_x1dsum.fits", "_mxs.fits", "_mos.fits",
            "_cal.fits",  # JWST calibrated
        )
        
        # Known 2D/image FITS variants that we cannot parse as 1D spectra
        excluded_name_suffixes = (
            "_evt.fits",  # event lists
            "_img.fits",  # images
            "_lws.fits",  # long/medium/short wave segments (image tables)
            "_mws.fits",
            "_sws.fits",
            "_flt.fits",  # flat-fielded 2D images
            "_crj.fits",  # cosmic-ray rejected 2D
            "_drz.fits",  # drizzled 2D images
            "_raw.fits",  # raw data
            "_uncal.fits",  # uncalibrated
            "_d0f.fits",  # raw WFPC/FOS
            "_c0f.fits",  # calibrated 2D (not 1D spectrum)
            "_c1f.fits",  # calibrated 2D (not 1D spectrum)
            "_c2f.fits",  # calibrated 2D
            "_c3f.fits",  # calibrated GHRS 2D
            "_c4f.fits",
            "_c5f.fits",
            "_rate.fits",  # JWST rate images
            "_rateints.fits",
            "_i2d.fits",  # JWST 2D images
        )
        excluded_keywords = (
            "_evt", "_event", "_img", "_image", "preview", "quicklook",
        )
        name_candidates = [
            self._first_text(metadata, ["productFilename", "productFilenameSource"]),
            self._first_text(metadata, ["dataURI", "data_uri", "ProductURI"]),
            self._first_text(metadata, ["description", "display_name"]),
        ]
        for raw in name_candidates:
            if not raw:
                continue
            # Extract extension from URL or filename
            try:
                from urllib.parse import urlparse as _urlparse
                parsed = _urlparse(raw)
                path = parsed.path or raw
            except Exception:
                path = raw
            lower_path = str(path).lower()
            
            # First check: if it matches a known 1D spectral pattern, accept it immediately
            if any(lower_path.endswith(pat) for pat in spectral_1d_patterns):
                return True
            
            # Exclude by explicit filename suffix patterns (2D images, raw data, etc.)
            if any(lower_path.endswith(suf) for suf in excluded_name_suffixes):
                # Still allow explicit VO spectra
                if lower_path.endswith("_vo.fits"):
                    pass
                else:
                    # If it's clearly an image and imaging is requested, allow
                    if include_imaging and (lower_path.endswith("_img.fits") or "_img" in lower_path or "_image" in lower_path):
                        pass
                    else:
                        return False
            # Exclude by keyword tokens in name unless imaging requested
            if any(tok in lower_path for tok in excluded_keywords):
                if lower_path.endswith("_vo.fits"):
                    pass
                elif include_imaging and ("_img" in lower_path or "_image" in lower_path or "image" in lower_path):
                    pass
                else:
                    return False
            ext = Path(lower_path).suffix
            if ext in supported_ext:
                return True
        return False

    def _collect_exosystem_products(
        self,
        system: Mapping[str, Any],
        *,
        include_imaging: bool,
        cancel_check: Callable[[], bool] | None = None,
    ) -> List[RemoteRecord]:
        """Collect products for a system using MAST query_criteria for efficiency.
        
        Instead of query_object() which returns ALL observations, we use
        query_criteria() with filters to get only relevant spectroscopic data.
        """
        if cancel_check and cancel_check():
            return []
            
        mast = self._ensure_mast()
        target_name = self._first_text(system, ["object_name", "host_name", "display_name"])
        if not target_name:
            return []

        # Build efficient query using query_criteria with target_name filter
        base_criteria = {
            "target_name": target_name,
            "intentType": "science",
            "calib_level": [2, 3],
        }
        
        if not include_imaging:
            base_criteria["dataproduct_type"] = "spectrum"
        
        # Do a single query instead of per-mission queries to be faster
        all_records: List[RemoteRecord] = []
        
        if cancel_check and cancel_check():
            return []
            
        try:
            observation_table = mast.Observations.query_criteria(**base_criteria)
            
            # Limit rows immediately
            if observation_table is not None and len(observation_table) > 50:
                observation_table = observation_table[:50]
            
            if cancel_check and cancel_check():
                return []
            
            if observation_table is not None and len(observation_table) > 0:
                enriched_system = dict(system)
                system_metadata = self._build_system_metadata(enriched_system)
                all_records = self._records_from_mast_products(
                    observation_table,
                    include_imaging=include_imaging,
                    provider=self.PROVIDER_EXOSYSTEMS,
                    system_metadata=system_metadata,
                )
        except Exception:
            pass
        
        # Add target display to records
        for record in all_records:
            if isinstance(record.metadata, Mapping):
                system_metadata = self._build_system_metadata(dict(system))
                record.metadata.setdefault("target_display", system_metadata.get("display_name"))
        
        return all_records[:self._MAX_MAST_RESULTS]

    def _resolve_exosystem_targets(self, text: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        matches.extend(self._match_curated_targets(text))
        matches.extend(self._query_exoplanet_archive(text))

        deduped: List[Dict[str, Any]] = []
        seen: set[tuple[str | None, str | None]] = set()
        for entry in matches:
            host = entry.get("host_name") or entry.get("object_name")
            planet = entry.get("planet_name")
            key = (str(host).lower() if host else None, str(planet).lower() if planet else None)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(entry)

        if deduped:
            return deduped

        return [
            {
                "display_name": text,
                "object_name": text,
                "aliases": {text.lower()},
                "citations": [],
            }
        ]

    def _match_curated_targets(self, text: str) -> List[Dict[str, Any]]:
        query = text.strip().lower()
        matches: List[Dict[str, Any]] = []
        for entry in self._CURATED_TARGETS:
            names = entry.get("names", set())
            if not isinstance(names, set):
                names = set(names)
            if query in {name.lower() for name in names} or query == entry.get("display_name", "").lower():
                metadata = {
                    "display_name": entry.get("display_name"),
                    "object_name": entry.get("object_name"),
                    "host_name": entry.get("host_name") or entry.get("object_name"),
                    "planet_name": entry.get("planet_name"),
                    "classification": entry.get("classification"),
                    "citations": entry.get("citations", []),
                    "aliases": {name.lower() for name in names},
                    "source": "curated",
                }
                for key in ("category", "ra", "dec", "search_radius"):
                    value = entry.get(key)
                    if value is not None:
                        metadata[key] = value
                matches.append(metadata)
        return matches

    def _query_exoplanet_archive(self, text: str) -> List[Dict[str, Any]]:
        if not self._has_exoplanet_archive():
            return []

        archive = self._ensure_exoplanet_archive()
        token = text.replace("'", "''")
        if "%" not in token and "_" not in token:
            like_token = f"%{token}%"
        else:
            like_token = token

        select_fields = (
            "TOP 10 pl_name,hostname,disc_year,discoverymethod,ra,dec,st_teff,st_logg,st_rad,st_spectype,"
            "sy_dist,pl_rade,pl_bmasse,pl_orbper"
        )
        try:
            table = archive.query_criteria(
                table="pscomppars",
                select=select_fields,
                where=f"(pl_name like '{like_token}' OR hostname like '{like_token}')",
            )
        except Exception:
            return []

        rows = self._table_to_records(table)
        systems: List[Dict[str, Any]] = []
        for row in rows:
            planet = self._first_text(row, ["pl_name"])
            host = self._first_text(row, ["hostname"])
            system = {
                "display_name": planet or host or text,
                "planet_name": planet or None,
                "host_name": host or None,
                "object_name": host or planet or text,
                "classification": "Exoplanet host system",
                "ra": row.get("ra"),
                "dec": row.get("dec"),
                "search_radius": self._DEFAULT_REGION_RADIUS,
                "citations": [
                    {
                        "title": "NASA Exoplanet Archive PSCompPars",
                        "url": "https://exoplanetarchive.ipac.caltech.edu/",
                        "notes": "Planetary and stellar parameters retrieved via astroquery.",
                    }
                ],
                "parameters": {
                    "stellar_teff": row.get("st_teff"),
                    "stellar_logg": row.get("st_logg"),
                    "stellar_radius": row.get("st_rad"),
                    "stellar_type": row.get("st_spectype"),
                    "system_distance_pc": row.get("sy_dist"),
                    "planet_radius_re": row.get("pl_rade"),
                    "planet_mass_me": row.get("pl_bmasse"),
                    "planet_orbital_period_days": row.get("pl_orbper"),
                    "discovery_method": row.get("discoverymethod"),
                    "discovery_year": row.get("disc_year"),
                },
            }

            exomast_payload = self._fetch_exomast_filelist(planet) if planet else None
            if exomast_payload:
                system["exomast"] = exomast_payload
                citation = exomast_payload.get("citation")
                if citation:
                    system.setdefault("citations", []).append({
                        "title": citation,
                        "url": "https://exo.mast.stsci.edu/",
                        "notes": "Curated spectra and file list from Exo.MAST.",
                    })

            systems.append(system)

        return systems

    def _download_tap_csv(self, record: RemoteRecord, progress: Callable[[RemoteRecord, int, int | None], None] | None = None) -> RemoteDownloadResult:
        """Download CSV data from TAP query and store it."""
        import requests
        import tempfile

        # Fetch CSV data
        response = requests.get(record.download_url, timeout=30, stream=True)
        response.raise_for_status()

        # Get total size if available
        total_size = int(response.headers.get('content-length', 0))

        # Create temp CSV file
        temp_dir = Path(tempfile.gettempdir()) / "spectra_cache"
        temp_dir.mkdir(exist_ok=True, parents=True)

        identifier = record.identifier.replace("/", "_").replace(":", "_")
        csv_path = temp_dir / f"{identifier}.csv"

        # Download with progress
        downloaded = 0
        with open(csv_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress and total_size > 0:
                        progress(record, downloaded, total_size)

        # Store in local store
        x_unit, y_unit = record.resolved_units()
        remote_metadata = {
            "provider": record.provider,
            "uri": record.download_url,
            "identifier": record.identifier,
            "fetched_at": self._timestamp(),
            "metadata": self._json_safe(record.metadata),
        }

        store_entry = self.store.record(
            csv_path,
            x_unit=x_unit,
            y_unit=y_unit,
            source={"remote": remote_metadata},
            alias=record.suggested_filename() or f"{identifier}.csv",
        )

        return RemoteDownloadResult(
            record=record,
            cache_entry=store_entry,
            path=Path(store_entry["stored_path"]),
            cached=False,
        )

    def _download_exomast_tsv(self, record: RemoteRecord, progress: Callable[[RemoteRecord, int, int | None], None] | None = None) -> RemoteDownloadResult:
        """Download TSV data from Exo.MAST and convert to CSV for easier import."""
        import requests
        import tempfile
        import csv

        print(f"[Exo.MAST Download] Starting download: {record.download_url}")

        # Fetch TSV data
        response = requests.get(record.download_url, timeout=30, stream=True)
        print(f"[Exo.MAST Download] Response status: {response.status_code}")
        response.raise_for_status()

        # Get total size if available
        total_size = int(response.headers.get('content-length', 0))

        # Download to temp file
        downloaded = 0
        lines = []
        for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
            if chunk:
                lines.append(chunk)
                downloaded += len(chunk.encode('utf-8'))
                if progress and total_size > 0:
                    progress(record, downloaded, total_size)

        # Parse TSV and convert to CSV
        content = ''.join(lines)
        tsv_lines = content.split('\n')

        # Find header line (first non-comment line)
        data_lines = []
        header_line = None
        for line in tsv_lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if header_line is None:
                header_line = line
            else:
                data_lines.append(line)

        if not header_line:
            raise ValueError("No data found in Exo.MAST file")

        # Parse header and data (whitespace-separated)
        header_parts = header_line.split()

        # Create CSV file
        temp_dir = Path(tempfile.gettempdir()) / "spectra_cache"
        temp_dir.mkdir(exist_ok=True, parents=True)

        identifier = record.identifier.replace("/", "_").replace(":", "_")
        csv_path = temp_dir / f"{identifier}.csv"

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write simplified header (remove units for CSV compatibility)
            # Map Exo.MAST columns to standard names
            simple_header = []
            for i, part in enumerate(header_parts):
                # Remove parenthetical units like "(microns)"
                clean_name = part.split('(')[0].strip()

                # Standardize column names for importer
                if 'wavelength' in clean_name.lower() and 'delta' not in clean_name.lower():
                    simple_header.append('Wavelength')
                elif 'rp/rs' in part.lower() and '+/-' not in part.lower():
                    simple_header.append('Rp_Rs_squared')
                elif '+/-' in part.lower() or 'uncertainty' in clean_name.lower():
                    simple_header.append('Uncertainty')
                elif 'delta' in clean_name.lower() and 'wavelength' in clean_name.lower():
                    simple_header.append('Delta_Wavelength')
                elif 'fp/fs' in part.lower():
                    simple_header.append('Fp_Fs')
                else:
                    simple_header.append(clean_name)
            writer.writerow(simple_header)

            # Write data rows
            for line in data_lines:
                if not line.strip():
                    continue
                values = line.split()
                if len(values) == len(simple_header):
                    writer.writerow(values)

        # Store in local store
        x_unit, y_unit = record.resolved_units()
        print(f"[Exo.MAST Download] CSV created at: {csv_path}")
        print(f"[Exo.MAST Download] Units: x={x_unit}, y={y_unit}")

        remote_metadata = {
            "provider": record.provider,
            "uri": record.download_url,
            "identifier": record.identifier,
            "fetched_at": self._timestamp(),
            "metadata": self._json_safe(record.metadata),
        }

        store_entry = self.store.record(
            csv_path,
            x_unit=x_unit,
            y_unit=y_unit,
            source={"remote": remote_metadata},
            alias=f"{identifier}.csv",  # Force .csv extension for import compatibility
        )
        print(f"[Exo.MAST Download] Stored at: {store_entry['stored_path']}")

        return RemoteDownloadResult(
            record=record,
            cache_entry=store_entry,
            path=Path(store_entry["stored_path"]),
            cached=False,
        )

    def _download_exoplanet_archive_embedded(self, record: RemoteRecord) -> RemoteDownloadResult:
        """Handle exoplanet archive records with embedded array data.

        Converts array data to CSV format and stores it.
        """
        import csv
        import tempfile

        metadata = record.metadata
        wavelength = metadata.get("wavelength", [])
        spectra = metadata.get("spectra", [])

        if not wavelength or not spectra:
            raise ValueError("No wavelength or spectra data in record")

        # Create temp CSV file
        temp_dir = Path(tempfile.gettempdir()) / "spectra_cache"
        temp_dir.mkdir(exist_ok=True, parents=True)

        identifier = record.identifier.replace("/", "_").replace(":", "_")
        csv_path = temp_dir / f"{identifier}.csv"

        # Get units
        x_unit, y_unit = record.resolved_units()
        wav_units = metadata.get("wav_units", "um")
        spectra_units = metadata.get("spectra_units", y_unit)

        # Write CSV
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header with metadata
            writer.writerow([f"# {record.title}"])
            writer.writerow([f"# Planet: {metadata.get('planet_name', '')}"])
            writer.writerow([f"# Host: {metadata.get('host_name', '')}"])
            writer.writerow([f"# Type: {metadata.get('spectrum_type', 'transmission')}"])
            writer.writerow([f"# Reference: {metadata.get('reference', '')}"])
            writer.writerow([f"# X-axis: Wavelength ({wav_units})"])
            writer.writerow([f"# Y-axis: {spectra_units}"])
            writer.writerow([])

            # Column headers
            headers = [f"wavelength_{wav_units}", spectra_units]
            error_max = metadata.get("spectra_error_max")
            error_min = metadata.get("spectra_error_min")

            if error_max is not None:
                headers.append("error_max")
            if error_min is not None:
                headers.append("error_min")

            writer.writerow(headers)

            # Data rows
            for i, (w, s) in enumerate(zip(wavelength, spectra)):
                row = [w, s]
                if error_max is not None and i < len(error_max):
                    row.append(error_max[i])
                if error_min is not None and i < len(error_min):
                    row.append(error_min[i])
                writer.writerow(row)

        # Store in local store
        remote_metadata = {
            "provider": record.provider,
            "uri": record.download_url,
            "identifier": record.identifier,
            "fetched_at": self._timestamp(),
            "metadata": self._json_safe(record.metadata),
        }

        store_entry = self.store.record(
            csv_path,
            x_unit=x_unit,
            y_unit=y_unit,
            source={"remote": remote_metadata},
            alias=record.suggested_filename() or f"{identifier}.csv",
        )

        return RemoteDownloadResult(
            record=record,
            cache_entry=store_entry,
            path=Path(store_entry["stored_path"]),
            cached=False,
        )

    def _search_exoplanet_archive_spectra(self, query: Mapping[str, Any]) -> List[RemoteRecord]:
        """Search NASA Exoplanet Archive for atmospheric spectra (transmission/emission).

        Uses TAP (Table Access Protocol) endpoint with ADQL queries.
        """
        import requests

        text = str(query.get("text") or query.get("target_name") or "").strip()
        if not text:
            raise ValueError("NASA Exoplanet Archive searches require a planet or star name.")

        records: List[RemoteRecord] = []
        search_term = text.strip().upper().replace("'", "''")

        # TAP sync endpoint
        tap_url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

        # Try transmission spectra (transitspec table)
        # Columns: centralwavelng, plnratror (Rp/Rs), plnratrorerr1/2, plntname
        try:
            trans_query = f"SELECT centralwavelng,plnratror,plnratrorerr1,plnratrorerr2,plntname FROM transitspec WHERE UPPER(plntname) LIKE '%{search_term}%'"
            trans_params = {
                'query': trans_query,
                'format': 'csv'
            }
            response = requests.get(tap_url, params=trans_params, timeout=10)

            if response.ok and len(response.text) > 100:  # Has data
                # Create a download record using this query URL
                identifier = f"{text.replace(' ', '_')}_transmission"
                title = f"{text} Transmission Spectrum"

                download_url = f"{tap_url}?query={requests.utils.quote(trans_query)}&format=csv"

                record = RemoteRecord(
                    provider=self.PROVIDER_EXOPLANET_ARCHIVE,
                    identifier=identifier,
                    title=title,
                    download_url=download_url,
                    metadata={
                        "target": text,
                        "spectrum_type": "transmission",
                        "data_format": "csv",
                        "source_table": "transitspec",
                        "x_column": "centralwavelng",
                        "y_column": "plnratror",
                    },
                    units={"x": "um", "y": "Rp/Rs"},
                )
                records.append(record)

        except Exception as e:
            pass  # Continue to emission

        # Try emission spectra (emissionspec table)
        try:
            emis_query = f"SELECT centralwavelng,plnecldep,plnecldeperr1,plnecldeperr2,plntname FROM emissionspec WHERE UPPER(plntname) LIKE '%{search_term}%'"
            emis_params = {
                'query': emis_query,
                'format': 'csv'
            }
            response = requests.get(tap_url, params=emis_params, timeout=10)

            if response.ok and len(response.text) > 100:
                identifier = f"{text.replace(' ', '_')}_emission"
                title = f"{text} Emission Spectrum"

                download_url = f"{tap_url}?query={requests.utils.quote(emis_query)}&format=csv"

                record = RemoteRecord(
                    provider=self.PROVIDER_EXOPLANET_ARCHIVE,
                    identifier=identifier,
                    title=title,
                    download_url=download_url,
                    metadata={
                        "target": text,
                        "spectrum_type": "emission",
                        "data_format": "csv",
                        "source_table": "emissionspec",
                        "x_column": "centralwavelng",
                        "y_column": "plnecldep",
                    },
                    units={"x": "um", "y": "Fp/Fs"},
                )
                records.append(record)

        except Exception as e:
            pass

        return records

    def _search_exomast(self, query: Mapping[str, Any]) -> List[RemoteRecord]:
        """Search Exo.MAST for curated exoplanet spectra.

        Uses the Exo.MAST API to find publication-quality transmission and emission spectra.
        Much more reliable than general MAST searches.
        """
        import requests
        import re

        text = str(query.get("text") or query.get("target_name") or "").strip()
        if not text:
            raise ValueError("Exo.MAST searches require a planet name.")

        # Normalize planet name: Exo.MAST expects "WASP-39 b" not "WASP-39b"
        # Add space before lowercase letter if missing (handles WASP-39b -> WASP-39 b)
        text = re.sub(r'(\d)([a-z])', r'\1 \2', text)

        base_url = "https://exo.mast.stsci.edu/api/v0.1"

        # Get file list for this planet
        try:
            filelist_url = f"{base_url}/spectra/{text}/filelist/"
            print(f"[Exo.MAST] Searching for: '{text}'")
            print(f"[Exo.MAST] URL: {filelist_url}")

            response = requests.get(filelist_url, timeout=10)
            print(f"[Exo.MAST] Response status: {response.status_code}")

            response.raise_for_status()

            data = response.json()
            filenames = data.get("filenames", [])
            print(f"[Exo.MAST] Found {len(filenames)} file(s)")

            if not filenames:
                return []

            # Create RemoteRecord for each file
            records = []
            for filename in filenames:
                # Parse filename to extract info
                # Format: "PLANET_type_Author2023.txt"
                parts = filename.replace(".txt", "").split("_")
                if len(parts) >= 3:
                    spectrum_type = parts[1]  # "transmission" or "emission"
                    reference = parts[2] if len(parts) > 2 else "Unknown"
                else:
                    spectrum_type = "transmission"
                    reference = "Unknown"

                identifier = filename.replace(".txt", "")
                title = f"{text} {spectrum_type.capitalize()} ({reference})"

                # Direct download URL
                download_url = f"{base_url}/spectra/{text}/file/{filename}"

                # Determine units based on spectrum type
                if "transmission" in spectrum_type.lower():
                    y_unit = "(Rp/Rs)^2"
                elif "emission" in spectrum_type.lower():
                    y_unit = "Fp/Fs"
                else:
                    y_unit = "ratio"

                record = RemoteRecord(
                    provider=self.PROVIDER_EXOMAST,
                    identifier=identifier,
                    title=title,
                    download_url=download_url,
                    metadata={
                        "target": text,
                        "spectrum_type": spectrum_type,
                        "reference": reference,
                        "data_format": "tsv",
                        "filename": filename,
                    },
                    units={"x": "um", "y": y_unit},
                )
                records.append(record)

            return records

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                # Planet not found in Exo.MAST
                return []
            raise RuntimeError(f"Exo.MAST query failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Exo.MAST error: {e}")

        for row in rows:
            pl_name = self._first_text(row, ["pl_name"])
            hostname = self._first_text(row, ["hostname"])
            spect_type = self._first_text(row, ["spect_type"]) or "transmission"
            refname = self._first_text(row, ["refname"]) or "NASA Exoplanet Archive"

            # Get wavelength and spectra data
            wav = row.get("wav")
            wav_units = self._first_text(row, ["wav_units"]) or "um"
            spectra = row.get("spectra")
            spectra_units = self._first_text(row, ["spectra_units"]) or "Rp/Rs"
            spectra_error_max = row.get("spectra_error_max")
            spectra_error_min = row.get("spectra_error_min")

            if wav is None or spectra is None:
                continue

            # Create identifier and title
            identifier = f"{pl_name}_{spect_type}"
            title = f"{pl_name} {spect_type.capitalize()} Spectrum"

            # Build metadata
            metadata = {
                "planet_name": pl_name,
                "host_name": hostname,
                "spectrum_type": spect_type,
                "reference": refname,
                "wav_units": wav_units,
                "spectra_units": spectra_units,
                "data_format": "arrays",
                "wavelength": wav if isinstance(wav, list) else [wav],
                "spectra": spectra if isinstance(spectra, list) else [spectra],
            }

            if spectra_error_max is not None:
                metadata["spectra_error_max"] = spectra_error_max if isinstance(spectra_error_max, list) else [spectra_error_max]
            if spectra_error_min is not None:
                metadata["spectra_error_min"] = spectra_error_min if isinstance(spectra_error_min, list) else [spectra_error_min]

            # Convert units for display
            x_unit = "um" if wav_units.lower() in ["um", "micron", "microns"] else "nm"

            # Determine y-unit based on spectrum type and units
            if "rp/rs" in spectra_units.lower() or "radius" in spectra_units.lower():
                y_unit = "Rp/Rs"
            elif "fp/fs" in spectra_units.lower() or "flux" in spectra_units.lower():
                y_unit = "Fp/Fs"
            elif "ppm" in spectra_units.lower():
                y_unit = "ppm"
            else:
                y_unit = spectra_units

            # Create download URL (synthetic - data is embedded)
            download_url = f"exoplanet-archive://{identifier}"

            record = RemoteRecord(
                provider=self.PROVIDER_EXOPLANET_ARCHIVE,
                identifier=identifier,
                title=title,
                download_url=download_url,
                metadata=metadata,
                units={"x": x_unit, "y": y_unit},
            )
            records.append(record)

        return records

    def _build_system_metadata(self, system: Mapping[str, Any]) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        for key in (
            "display_name",
            "object_name",
            "host_name",
            "planet_name",
            "classification",
            "parameters",
            "citations",
            "aliases",
        ):
            value = system.get(key)
            if value is not None:
                metadata[key] = self._json_safe(value)

        coordinates: Dict[str, Any] = {}
        ra = system.get("ra")
        dec = system.get("dec")
        if isinstance(ra, (int, float)) and not math.isnan(float(ra)):
            coordinates["ra"] = float(ra)
        if isinstance(dec, (int, float)) and not math.isnan(float(dec)):
            coordinates["dec"] = float(dec)
        if coordinates:
            metadata["coordinates"] = coordinates

        if system.get("exomast") is not None:
            metadata["exomast"] = self._json_safe(system.get("exomast"))

        return metadata

    def _download_staging_dir(self) -> Path:
        base: Path | None = None
        if self.store is not None:
            try:
                base = Path(self.store.data_dir)
            except Exception:
                base = None
        if base is None:
            base = Path(tempfile.gettempdir()) / "spectra-downloads"
        staging = base / "_incoming"
        try:
            staging.mkdir(parents=True, exist_ok=True)
            return staging
        except Exception:
            fallback = Path(tempfile.gettempdir()) / "spectra-downloads"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    def _prepare_staging_file(self, filename: str | None, *, suffix: str = "") -> Path:
        staging = self._download_staging_dir()
        safe_name = self._sanitized_filename(filename, suffix=suffix)
        candidate = staging / safe_name
        if candidate.exists():
            stem = Path(safe_name).stem or "download"
            ext = Path(safe_name).suffix or (suffix if suffix.startswith(".") else suffix)
            counter = 1
            while True:
                numbered = staging / f"{stem}_{counter}{ext}"
                if not numbered.exists():
                    candidate = numbered
                    break
                counter += 1
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    @staticmethod
    def _sanitized_filename(name: str | None, *, suffix: str = "") -> str:
        normalized_suffix = suffix if suffix.startswith(".") or not suffix else f".{suffix.lstrip('.')}"
        if name:
            parsed = Path(name)
            stem = parsed.stem or "download"
            file_suffix = parsed.suffix or normalized_suffix or ""
        else:
            stem = "download"
            file_suffix = normalized_suffix or ""
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "download"
        return f"{safe_stem}{file_suffix}"

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        if hasattr(value, "tolist"):
            try:
                return RemoteDataService._json_safe(value.tolist())
            except Exception:
                pass
        if hasattr(value, "item") and not isinstance(value, (str, bytes)):
            try:
                return RemoteDataService._json_safe(value.item())
            except Exception:
                pass
        if isinstance(value, Mapping):
            return {str(key): RemoteDataService._json_safe(subvalue) for key, subvalue in value.items()}
        if isinstance(value, set):
            try:
                ordered = sorted(value)
            except Exception:
                ordered = list(value)
            return [RemoteDataService._json_safe(item) for item in ordered]
        if isinstance(value, (list, tuple)):
            return [RemoteDataService._json_safe(item) for item in value]
        return str(value)

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            result = float(value)
        except (TypeError, ValueError):
            return None
        if math.isnan(result):
            return None
        return result

    def _fetch_exomast_filelist(self, planet_name: str | None) -> Dict[str, Any] | None:
        if not planet_name or not self._has_requests():
            return None
        session = self._ensure_session()
        url = "https://exo.mast.stsci.edu/api/v0.1/spectra/{}/filelist".format(
            quote(str(planet_name).strip(), safe="")
        )
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return None
        if isinstance(payload, Mapping):
            return dict(payload)
        return None

    def _fetch_remote(
        self,
        record: RemoteRecord,
        *,
        progress: Callable[[RemoteRecord, int, int | None], None] | None = None,
    ) -> Path:
        if record.provider == self.PROVIDER_NIST:
            return self._generate_nist_csv(record, progress=progress)
        if self._should_use_mast(record):
            return self._fetch_via_mast(record, progress=progress)
        return self._fetch_via_http(record, progress=progress)

    def _generate_nist_csv(
        self,
        record: RemoteRecord,
        *,
        progress: Callable[[RemoteRecord, int, int | None], None] | None = None,
    ) -> Path:
        lines = record.metadata.get("lines") if isinstance(record.metadata, Mapping) else None
        if not isinstance(lines, list) or not lines:
            query_meta = (
                record.metadata.get("query")
                if isinstance(record.metadata, Mapping)
                else {}
            )
            identifier = str(
                (query_meta.get("identifier") if isinstance(query_meta, Mapping) else None)
                or record.metadata.get("query_text")
                if isinstance(record.metadata, Mapping)
                else None
                or record.identifier
            )
            element_symbol = (
                record.metadata.get("element_symbol")
                if isinstance(record.metadata, Mapping)
                else None
            )
            ion_stage_number = (
                record.metadata.get("ion_stage_number")
                if isinstance(record.metadata, Mapping)
                else None
            )
            try:
                payload = nist_asd_service.fetch_lines(
                    identifier,
                    element=element_symbol,
                    ion_stage=ion_stage_number,
                    lower_wavelength=(
                        float(query_meta.get("lower_wavelength"))
                        if isinstance(query_meta, Mapping)
                        and query_meta.get("lower_wavelength") is not None
                        else None
                    ),
                    upper_wavelength=(
                        float(query_meta.get("upper_wavelength"))
                        if isinstance(query_meta, Mapping)
                        and query_meta.get("upper_wavelength") is not None
                        else None
                    ),
                    wavelength_unit=str(
                        query_meta.get("wavelength_unit", "nm") if isinstance(query_meta, Mapping) else "nm"
                    ),
                    use_ritz=bool(query_meta.get("use_ritz", True))
                    if isinstance(query_meta, Mapping)
                    else True,
                    wavelength_type=str(
                        query_meta.get("wavelength_type", "vacuum")
                        if isinstance(query_meta, Mapping)
                        else "vacuum"
                    ),
                )
            except (nist_asd_service.NistUnavailableError, nist_asd_service.NistQueryError) as exc:
                raise RuntimeError(str(exc)) from exc

            lines = payload.get("lines", [])
            if isinstance(record.metadata, Mapping):
                record.metadata["lines"] = lines
                series = record.metadata.setdefault("series", {})
                if isinstance(series, Mapping):
                    series["wavelength_nm"] = payload.get("wavelength_nm", [])
                    series["relative_intensity"] = payload.get("intensity", [])
                    series["relative_intensity_normalized"] = payload.get(
                        "intensity_normalized", []
                    )

        alias = record.suggested_filename()
        if not alias.lower().endswith(".csv"):
            alias_stem = Path(alias).stem if alias else record.identifier
            alias = f"{alias_stem or 'nist_lines'}.csv"
        target_path = self._prepare_staging_file(alias, suffix=".csv")
        with target_path.open("w", newline="", encoding="utf-8") as handle:
            handle.write("# Source: NIST Atomic Spectra Database\n")
            handle.write(f"# Provider: {record.provider}\n")
            handle.write(f"# Identifier: {record.identifier}\n")
            query_meta = (
                record.metadata.get("query")
                if isinstance(record.metadata, Mapping)
                else {}
            )
            if isinstance(query_meta, Mapping):
                handle.write(f"# Query: {json.dumps(query_meta, ensure_ascii=False)}\n")

            writer = csv.writer(handle)
            writer.writerow(
                [
                    "Wavelength (nm)",
                    "Relative Intensity (arb.)",
                    "Normalized Intensity",
                    "Observed Wavelength (nm)",
                    "Ritz Wavelength (nm)",
                    "Lower Level",
                    "Upper Level",
                    "Transition Type",
                    "Transition Probability (s^-1)",
                    "Oscillator Strength",
                    "Lower Level Energy (eV)",
                    "Upper Level Energy (eV)",
                    "Line Reference",
                    "Transition Probability Reference",
                    "Accuracy",
                ]
            )

            def _format(value: Any) -> str:
                if value is None:
                    return ""
                if isinstance(value, float):
                    return f"{value:.9g}"
                return str(value)

            for line in lines or []:
                writer.writerow(
                    [
                        _format(line.get("wavelength_nm")),
                        _format(line.get("relative_intensity")),
                        _format(line.get("relative_intensity_normalized")),
                        _format(line.get("observed_wavelength_nm")),
                        _format(line.get("ritz_wavelength_nm")),
                        _format(line.get("lower_level")),
                        _format(line.get("upper_level")),
                        _format(line.get("transition_type")),
                        _format(line.get("transition_probability_s")),
                        _format(line.get("oscillator_strength")),
                        _format(line.get("lower_level_energy_ev")),
                        _format(line.get("upper_level_energy_ev")),
                        _format(line.get("line_reference")),
                        _format(line.get("transition_probability_reference")),
                        _format(line.get("accuracy")),
                    ]
                )

        try:
            size = target_path.stat().st_size
        except Exception:
            size = 0
        if progress is not None:
            progress(record, size, size if size > 0 else None)
        return target_path

    def _fetch_via_http(
        self,
        record: RemoteRecord,
        *,
        progress: Callable[[RemoteRecord, int, int | None], None] | None = None,
    ) -> Path:
        session = self._ensure_session()
        response = session.get(record.download_url, timeout=60, stream=True)
        response.raise_for_status()

        parsed = urlparse(record.download_url)
        alias = Path(parsed.path).name or record.suggested_filename()
        suffix = Path(alias).suffix or Path(parsed.path).suffix or ""
        target_path = self._prepare_staging_file(alias, suffix=suffix)
        total_header = response.headers.get("Content-Length")
        total = int(total_header) if total_header and total_header.isdigit() else None
        received = 0
        with target_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 512):
                if not chunk:
                    continue
                handle.write(chunk)
                received += len(chunk)
                if progress is not None:
                    progress(record, received, total)
        if progress is not None and (total is None or received != total):
            progress(record, received, total)
        return target_path

    def _fetch_via_mast(
        self,
        record: RemoteRecord,
        *,
        progress: Callable[[RemoteRecord, int, int | None], None] | None = None,
    ) -> Path:
        # Prefer astroquery's Observations.download_file when available; fall back to direct HTTP
        try:
            mast = self._ensure_mast()
            # Resolve a local target path; Observations will create/overwrite this path
            parsed = urlparse(record.download_url)
            suffix = Path(parsed.path).suffix or ".fits"
            alias = record.suggested_filename() or Path(parsed.path).name or "mast_product"
            target = self._prepare_staging_file(alias, suffix=suffix)
            # The astroquery API writes to the provided local_path and returns the written path
            result = mast.Observations.download_file(record.download_url, cache=False, local_path=str(target))
            try:
                return Path(result)
            except Exception:
                return target
        except Exception:
            return self._fetch_via_mast_direct(record.download_url, record=record, progress=progress)

    def _fetch_via_mast_direct(
        self,
        mast_uri: str,
        *,
        record: RemoteRecord | None = None,
        progress: Callable[[RemoteRecord, int, int | None], None] | None = None,
    ) -> Path:
        """Fallback path: fetch a MAST 'mast:' URI via the public Download API.

        Example: https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:...
        """
        session = self._ensure_session()
        from urllib.parse import quote
        url = f"https://mast.stsci.edu/api/v0.1/Download/file?uri={quote(mast_uri, safe='')}"

        response = session.get(url, timeout=90, stream=True)
        response.raise_for_status()
        # Try to infer a suffix from headers or URI
        suffix = ".fits"
        cdisp = response.headers.get("Content-Disposition", "")
        if ".csv" in cdisp.lower() or url.lower().endswith(".csv"):
            suffix = ".csv"
        elif ".jdx" in cdisp.lower() or url.lower().endswith(".jdx") or url.lower().endswith(".dx"):
            suffix = ".jdx"

        parsed = urlparse(mast_uri)
        base_name = Path(parsed.path).name
        alias = base_name or (record.suggested_filename() if record else None)
        target_path = self._prepare_staging_file(alias, suffix=suffix)
        total_header = response.headers.get("Content-Length")
        total = int(total_header) if total_header and total_header.isdigit() else None
        received = 0
        with target_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 512):
                if not chunk:
                    continue
                handle.write(chunk)
                received += len(chunk)
                if progress is not None and record is not None:
                    progress(record, received, total)
        if progress is not None and record is not None and (total is None or received != total):
            progress(record, received, total)
        return target_path

    def _fetch_exomast_filelist(self, target_name: str) -> Dict[str, Any] | None:
        """Return the Exo.MAST file list for *target_name* without double encoding."""

        cleaned = str(target_name).strip()
        if not cleaned:
            return None

        session = self._ensure_session()
        slug = quote(cleaned, safe="")
        url = f"https://exo.mast.stsci.edu/api/v0.1/exoplanets/{slug}/filelist"

        response = session.get(url, timeout=30)
        if response.status_code == 404:
            return None
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise RuntimeError("Exo.MAST file list response was not valid JSON") from exc

        if not isinstance(payload, Mapping):
            raise RuntimeError("Exo.MAST file list response must be a mapping")

        return dict(payload)

    def _should_use_mast(self, record: RemoteRecord) -> bool:
        if record.provider == self.PROVIDER_MAST:
            return True
        return record.download_url.startswith("mast:")

    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_nist_query(identifier: str, meta: Mapping[str, Any]) -> Dict[str, Any]:
        """Return a stable mapping that captures the effective NIST query."""

        query_meta: Dict[str, Any] = {}
        raw_query = meta.get("query") if isinstance(meta, Mapping) else None
        if isinstance(raw_query, Mapping):
            query_meta.update(raw_query)

        query_meta.setdefault("identifier", identifier)
        if "linename" not in query_meta and "spectrum" in query_meta:
            query_meta["linename"] = query_meta["spectrum"]
        if meta.get("element_symbol"):
            query_meta.setdefault("element_symbol", meta.get("element_symbol"))
        if meta.get("ion_stage_number") is not None:
            query_meta.setdefault("ion_stage_number", meta.get("ion_stage_number"))
        if meta.get("ion_stage"):
            query_meta.setdefault("ion_stage", meta.get("ion_stage"))
        if meta.get("label"):
            query_meta.setdefault("label", meta.get("label"))

        # Ensure wavelength bounds are represented explicitly for caching.
        lower = query_meta.get("lower_wavelength")
        upper = query_meta.get("upper_wavelength")
        if lower is not None:
            query_meta["lower_wavelength"] = float(lower)
        if upper is not None:
            query_meta["upper_wavelength"] = float(upper)

        unit = query_meta.get("wavelength_unit")
        if unit is not None:
            query_meta["wavelength_unit"] = str(unit)
        wtype = query_meta.get("wavelength_type")
        if wtype is not None:
            query_meta["wavelength_type"] = str(wtype)
        if "use_ritz" in query_meta:
            query_meta["use_ritz"] = bool(query_meta["use_ritz"])

        return query_meta

    @staticmethod
    def _build_nist_download_url(label: str, query_meta: Mapping[str, Any]) -> str:
        """Create a cache-safe pseudo URI for a NIST line query."""

        safe_label = quote(str(label).strip().replace(" ", "_"), safe="+-_.") or "lines"

        def _stringify(value: Any) -> str:
            if isinstance(value, bool):
                return "true" if value else "false"
            if isinstance(value, float):
                return f"{value:.9g}"
            return str(value)

        params: List[tuple[str, str]] = []
        for key in sorted(query_meta):
            value = query_meta[key]
            if value is None:
                continue
            params.append((key, _stringify(value)))

        query_string = urlencode(params, doseq=True, safe="+-_.:")
        base = f"nist-asd://lines/{safe_label}"
        return f"{base}?{query_string}" if query_string else base

    def _find_cached(self, uri: str) -> Dict[str, Any] | None:
        entries = self.store.list_entries()
        for entry in entries.values():
            source = entry.get("source")
            if not isinstance(source, Mapping):
                continue
            remote = source.get("remote")
            if isinstance(remote, Mapping) and remote.get("uri") == uri:
                return dict(entry)
        return None

    def _build_nist_cache_uri(self, token: str, query_signature: Mapping[str, Any]) -> str:
        payload = json.dumps(
            query_signature,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        return f"nist-asd:{token}:{digest}"

    def _ensure_session(self):
        if self.session is not None:
            return self.session
        if requests is None:
            raise RuntimeError(
                "The 'requests' package is required for remote downloads. "
                "Install it via `pip install -r requirements.txt` or `poetry install --with remote`."
            )
        self.session = requests.Session()
        return self.session

    def _ensure_mast(self):
        if not self._has_astroquery():
            raise RuntimeError(
                "The 'astroquery' and 'pandas' packages are required for MAST searches"
            )
        return _import_mast()

    def _has_nist_support(self) -> bool:
        return nist_asd_service.dependencies_available()

    def _has_mast_support(self) -> bool:
        return self._has_astroquery()

    def _has_exoplanet_archive(self) -> bool:
        return _has_module("astroquery.ipac.nexsci.nasa_exoplanet_archive") and _has_pandas()

    def _has_exosystem_support(self) -> bool:
        return self._has_mast_support() and self._has_exoplanet_archive() and self._has_requests()

    def _has_requests(self) -> bool:
        return requests is not None or self.session is not None

    def _has_astroquery(self) -> bool:
        return _has_module("astroquery.mast") and _has_pandas()

    def _ensure_exoplanet_archive(self):
        if not self._has_exoplanet_archive():
            raise RuntimeError(
                "The 'astroquery' and 'pandas' packages are required for Exoplanet Archive queries"
            )
        return _import_exoplanet_archive()

    def _table_to_records(self, table: Any) -> List[Mapping[str, Any]]:
        if table is None:
            return []
        if isinstance(table, list):
            return [row for row in table if isinstance(row, Mapping)]
        if hasattr(table, "to_pandas"):
            return [
                dict(row)
                for row in table.to_pandas().to_dict(orient="records")  # type: ignore[call-arg]
            ]
        if hasattr(table, "as_array"):
            raw = table.as_array()
            try:
                return [dict(zip(raw.dtype.names or (), values)) for values in raw.tolist()]
            except Exception:  # pragma: no cover - defensive fallback
                pass
        if hasattr(table, "__iter__"):
            rows: List[Mapping[str, Any]] = []
            for row in table:
                if isinstance(row, Mapping):
                    rows.append(row)
            return rows
        return []

    def _timestamp(self) -> str:
        try:
            moment = self.clock(timezone.utc)  # type: ignore[misc]
        except TypeError:
            moment = self.clock()  # type: ignore[misc]
        if not isinstance(moment, datetime):
            moment = datetime.now(timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.isoformat()

    @staticmethod
    def _normalise_observation_id(metadata: Mapping[str, Any]) -> str:
        for key in (
            "obsid",
            "obs_id",
            "parent_obsid",
            "parent_obsID",
            "ObservationID",
            "observation_id",
        ):
            value = metadata.get(key) if isinstance(metadata, Mapping) else None
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""

    @staticmethod
    def _first_text(metadata: Mapping[str, Any] | Any, keys: Sequence[str]) -> str:
        mapping = metadata if isinstance(metadata, Mapping) else {}
        for key in keys:
            value = mapping.get(key)
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                for item in value:
                    if item is None:
                        continue
                    text = str(item).strip()
                    if text:
                        return text
                continue
            text = str(value).strip()
            if text:
                return text
        return ""

    def _index_observations(self, rows: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
        index: Dict[str, Mapping[str, Any]] = {}
        for row in rows:
            key = self._normalise_observation_id(row)
            if key and key not in index:
                index[key] = dict(row)
        return index

    def _build_mast_title(self, metadata: Mapping[str, Any]) -> str:
        target = self._first_text(metadata, ["target_name", "obs_title", "intentDescription"])
        mission = self._first_text(metadata, ["obs_collection", "telescope_name", "proposal_pi"])
        instrument = self._first_text(metadata, ["instrument_name", "instrument", "filters"])
        product = self._first_text(
            metadata,
            ["productType", "dataproduct_type", "product_type"],
        )

        details: list[str] = []
        mission_parts = [part for part in (mission, instrument) if part]
        if mission_parts:
            details.append(" / ".join(mission_parts))
        if product:
            details.append(product)

        if target and details:
            return f"{target} — {'; '.join(details)}"
        if target:
            return target
        if details:
            return "; ".join(details)
        return str(metadata.get("productFilename") or metadata.get("obs_id") or "MAST product")


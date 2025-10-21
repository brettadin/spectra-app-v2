"""Abstractions for retrieving remote spectral catalogues and downloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import csv
import json
import logging
import math
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence
from urllib.parse import quote, urlencode, urlparse

from . import nist_asd_service
from .store import LocalStore

try:  # Optional dependency – requests may be absent in minimal installs
    import requests
except Exception:  # pragma: no cover - handled by dependency guards
    requests = None  # type: ignore[assignment]

try:  # Optional dependency – astroquery is heavy and not always bundled
    from astroquery import mast as astroquery_mast
except Exception:  # pragma: no cover - handled by dependency guards
    astroquery_mast = None  # type: ignore[assignment]

try:  # Optional dependency – astroquery depends on pandas at runtime
    import pandas  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover - handled by dependency guards
    _HAS_PANDAS = False
else:  # pragma: no branch - simple flag wiring
    _HAS_PANDAS = True


logger = logging.getLogger(__name__)


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
    _curated_manifest_cache: Dict[str, Dict[str, Any]] = field(
        default_factory=dict, init=False, repr=False
    )

    PROVIDER_NIST = "NIST ASD"
    PROVIDER_MAST = "MAST"
    PROVIDER_SOLAR_SYSTEM = "Solar System Archive"

    _DEFAULT_REGION_RADIUS = "0.02 deg"
    _CURATED_BASE_DIR = Path(__file__).resolve().parents[2]

    _CURATED_TARGETS: tuple[Dict[str, Any], ...] = (
        {
            "names": {"mercury"},
            "display_name": "Mercury",
            "manifest": "samples/solar_system/mercury_messenger_mascs.json",
        },
        {
            "names": {"venus"},
            "display_name": "Venus",
            "manifest": "samples/solar_system/venus_akatsuki_ir2.json",
        },
        {
            "names": {"earth", "moon"},
            "display_name": "Earth/Moon",
            "manifest": "samples/solar_system/earth_astronomy_earthshine.json",
        },
        {
            "names": {"mars"},
            "display_name": "Mars",
            "manifest": "samples/solar_system/mars_jwst_nirspec.json",
        },
        {
            "names": {"jupiter", "io", "europa", "ganymede", "callisto"},
            "display_name": "Jupiter",
            "manifest": "samples/solar_system/jupiter_jwst_ers.json",
        },
        {
            "names": {"saturn", "enceladus", "titan"},
            "display_name": "Saturn",
            "manifest": "samples/solar_system/saturn_cassini_composite.json",
        },
        {
            "names": {"uranus"},
            "display_name": "Uranus",
            "manifest": "samples/solar_system/uranus_near_ir.json",
        },
        {
            "names": {"neptune", "triton"},
            "display_name": "Neptune",
            "manifest": "samples/solar_system/neptune_ir.json",
        },
        {
            "names": {"g2v", "solar analog", "sun-like", "hd 10700", "tau cet"},
            "display_name": "Tau Ceti (G8V)",
            "manifest": "samples/solar_system/tau_ceti_pickles.json",
        },
        {
            "names": {"a0v", "vega"},
            "display_name": "Vega (A0V)",
            "manifest": "samples/solar_system/vega_calspec.json",
        },
    )

    def providers(self, *, include_reference: bool = True) -> List[str]:
        """Return the list of remote providers whose dependencies are satisfied."""

        providers: List[str] = []
        if include_reference and self._has_nist_support():
            providers.append(self.PROVIDER_NIST)
        if self._has_mast_support():
            providers.append(self.PROVIDER_MAST)
        if self._has_curated_support():
            providers.append(self.PROVIDER_SOLAR_SYSTEM)
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
        if not self._has_curated_support():
            reasons[self.PROVIDER_SOLAR_SYSTEM] = (
                "Curated Solar System manifests are missing from the application bundle."
            )
        return reasons

    # ------------------------------------------------------------------
    def search(
        self,
        provider: str,
        query: Mapping[str, Any],
        *,
        include_imaging: bool = False,
    ) -> List[RemoteRecord]:
        if provider == self.PROVIDER_NIST:
            return self._search_nist(query)
        if provider == self.PROVIDER_MAST:
            return self._search_mast(query, include_imaging=include_imaging)
        if provider == self.PROVIDER_SOLAR_SYSTEM:
            return self._search_curated(query)
        raise ValueError(f"Unsupported provider: {provider}")

    # ------------------------------------------------------------------
    def download(self, record: RemoteRecord, *, force: bool = False) -> RemoteDownloadResult:
        cached = None if force else self._find_cached(record.download_url)
        if cached is not None:
            return RemoteDownloadResult(
                record=record,
                cache_entry=cached,
                path=Path(cached["stored_path"]),
                cached=True,
            )

        fetch_path, cleanup, manifest_path = self._fetch_remote(record)

        x_unit, y_unit = record.resolved_units()
        remote_metadata = {
            "provider": record.provider,
            "uri": record.download_url,
            "identifier": record.identifier,
            "fetched_at": self._timestamp(),
            "metadata": json.loads(json.dumps(record.metadata)),
        }
        store_entry = self.store.record(
            fetch_path,
            x_unit=x_unit,
            y_unit=y_unit,
            source={"remote": remote_metadata},
            alias=record.suggested_filename(),
            manifest_path=manifest_path,
        )
        if cleanup:
            fetch_path.unlink(missing_ok=True)

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
        criteria = dict(query)
        legacy_text = criteria.pop("text", None)
        if legacy_text and "target_name" not in criteria:
            if isinstance(legacy_text, str) and legacy_text.strip():
                criteria["target_name"] = legacy_text.strip()

        if not criteria or not any(criteria.values()):
            raise ValueError("MAST searches require a target name or explicit filtering criteria.")

        observations = self._ensure_mast()

        # Default to calibrated spectroscopic products so search results focus on
        # slit/grism/cube observations that pair with laboratory references.
        if include_imaging:
            criteria.setdefault("dataproduct_type", ["spectrum", "image"])
        else:
            criteria.setdefault("dataproduct_type", "spectrum")
        criteria.setdefault("intentType", "SCIENCE")
        if "calib_level" not in criteria:
            criteria["calib_level"] = [2, 3]

        table = observations.Observations.query_criteria(**criteria)
        rows = self._table_to_records(table)
        records: List[RemoteRecord] = []
        for row in rows:
            metadata = dict(row)
            if include_imaging:
                if not (self._is_spectroscopic(metadata) or self._is_imaging(metadata)):
                    continue
            else:
                if not self._is_spectroscopic(metadata):
                    continue
            identifier = str(metadata.get("obsid") or metadata.get("ObservationID") or metadata.get("id"))
            if not identifier:
                continue
            title = str(metadata.get("target_name") or metadata.get("target") or identifier)
            download_uri = metadata.get("dataURI") or metadata.get("ProductURI") or metadata.get("download_uri")
            if not download_uri:
                continue
            units_map = metadata.get("units") if isinstance(metadata.get("units"), Mapping) else None
            records.append(
                RemoteRecord(
                    provider=self.PROVIDER_MAST,
                    identifier=identifier,
                    title=title,
                    download_url=str(download_uri),
                    metadata=metadata,
                    units=units_map,
                )
                )
        return records

    def _search_curated(self, query: Mapping[str, Any]) -> List[RemoteRecord]:
        text = str(query.get("text") or query.get("target_name") or "").strip().lower()
        include_all_flag = str(query.get("include_all") or "").strip().lower()
        include_all = include_all_flag in {"1", "true", "yes"}

        records: List[RemoteRecord] = []
        for entry in self._CURATED_TARGETS:
            manifest_ref = entry.get("manifest")
            if not manifest_ref:
                continue
            manifest_path = self._resolve_curated_path(manifest_ref)
            try:
                manifest = self._load_curated_manifest(manifest_path)
            except (FileNotFoundError, RuntimeError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Skipping curated target due to manifest issue: %s", manifest_path, exc_info=exc
                )
                continue
            terms = self._curated_terms(entry, manifest)
            if text:
                if not self._curated_term_matches(text, terms):
                    continue
            elif not include_all:
                continue
            try:
                record = self._build_curated_record(entry, manifest, manifest_path)
            except (FileNotFoundError, RuntimeError) as exc:
                logger.warning(
                    "Skipping curated target due to asset issue: %s", manifest_path, exc_info=exc
                )
                continue
            records.append(record)
        return records

    def _curated_terms(self, entry: Mapping[str, Any], manifest: Mapping[str, Any]) -> set[str]:
        terms: set[str] = set()
        for name in entry.get("names", set()):
            if name:
                terms.add(str(name).lower())
        display = entry.get("display_name")
        if display:
            terms.add(str(display).lower())

        target = manifest.get("target") if isinstance(manifest.get("target"), Mapping) else {}
        if isinstance(target, Mapping):
            target_name = target.get("name")
            if target_name:
                terms.add(str(target_name).lower())
            aliases = target.get("aliases")
            if isinstance(aliases, (list, tuple, set)):
                for alias in aliases:
                    if alias:
                        terms.add(str(alias).lower())

        identifier = manifest.get("id")
        if identifier:
            terms.add(str(identifier).lower())
        summary = manifest.get("summary")
        if isinstance(summary, str) and summary.strip():
            terms.add(summary.strip().lower())
        return terms

    @staticmethod
    def _curated_term_matches(text: str, terms: set[str]) -> bool:
        if not text:
            return True
        for term in terms:
            if not term:
                continue
            if text in term or term in text:
                return True
        return False

    def _build_curated_record(
        self,
        entry: Mapping[str, Any],
        manifest: Mapping[str, Any],
        manifest_path: Path,
    ) -> RemoteRecord:
        asset = manifest.get("asset") if isinstance(manifest.get("asset"), Mapping) else None
        if not isinstance(asset, Mapping):
            raise RuntimeError("Curated manifest is missing an 'asset' mapping.")

        asset_path_value = asset.get("path")
        if not asset_path_value:
            raise RuntimeError("Curated asset is missing a 'path' entry.")
        asset_path = self._resolve_curated_path(asset_path_value)
        if not asset_path.exists():
            raise FileNotFoundError(f"Curated asset missing: {asset_path}")

        identifier = str(manifest.get("id") or Path(asset_path).stem)
        title = str(manifest.get("title") or entry.get("display_name") or identifier)

        target = manifest.get("target") if isinstance(manifest.get("target"), Mapping) else {}
        aliases = []
        if isinstance(target, Mapping):
            alias_values = target.get("aliases")
            if isinstance(alias_values, (list, tuple, set)):
                aliases = [str(alias) for alias in alias_values if alias]

        units_raw = asset.get("units") if isinstance(asset.get("units"), Mapping) else {}
        units: Dict[str, str] = {}
        if isinstance(units_raw, Mapping):
            for axis in ("x", "y"):
                value = units_raw.get(axis)
                if value is not None:
                    units[axis] = str(value)

        metadata: Dict[str, Any] = {
            "target_name": (target.get("name") if isinstance(target, Mapping) else None)
            or entry.get("display_name")
            or identifier,
            "target_aliases": aliases,
            "classification": target.get("classification") if isinstance(target, Mapping) else None,
            "display_name": entry.get("display_name"),
            "mission": manifest.get("mission"),
            "obs_collection": manifest.get("mission"),
            "instrument_name": manifest.get("instrument"),
            "productType": manifest.get("product_type"),
            "dataproduct_type": manifest.get("product_type"),
            "asset_description": asset.get("description"),
            "asset_columns": asset.get("columns") if isinstance(asset.get("columns"), list) else None,
            "asset_path": str(asset_path),
            "manifest_path": str(manifest_path),
            "summary": manifest.get("summary"),
            "citations": manifest.get("citations", []),
            "units": units,
            "provider": self.PROVIDER_SOLAR_SYSTEM,
        }

        # Remove empty optional fields while keeping explicit falsy values like [] for citations.
        cleaned_metadata = {
            key: value
            for key, value in metadata.items()
            if value not in (None, "")
        }
        if "citations" not in cleaned_metadata:
            cleaned_metadata["citations"] = []
        if not cleaned_metadata.get("citations") and manifest.get("citations"):
            cleaned_metadata["citations"] = manifest.get("citations")

        download_url = f"curated:{asset_path.name}"
        return RemoteRecord(
            provider=self.PROVIDER_SOLAR_SYSTEM,
            identifier=identifier,
            title=title,
            download_url=download_url,
            metadata=cleaned_metadata,
            units=units if units else None,
        )

    def _resolve_curated_path(self, path_value: str | Path) -> Path:
        candidate = Path(path_value)
        if candidate.is_absolute():
            return candidate
        return (self._CURATED_BASE_DIR / candidate).resolve()

    def _load_curated_manifest(self, manifest_path: Path) -> Dict[str, Any]:
        key = str(manifest_path)
        if key in self._curated_manifest_cache:
            return json.loads(json.dumps(self._curated_manifest_cache[key]))
        if not manifest_path.exists():
            raise FileNotFoundError(f"Curated manifest missing: {manifest_path}")
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        if not isinstance(manifest, dict):
            raise RuntimeError("Curated manifest must decode to a mapping.")
        self._curated_manifest_cache[key] = manifest
        return json.loads(json.dumps(manifest))

    def _fetch_curated(self, record: RemoteRecord) -> tuple[Path, bool, Path | None]:
        metadata = record.metadata if isinstance(record.metadata, Mapping) else {}
        manifest_ref = metadata.get("manifest_path") or metadata.get("manifest")
        if not manifest_ref:
            raise RuntimeError("Curated record is missing manifest metadata.")
        manifest_path = self._resolve_curated_path(manifest_ref)
        manifest = self._load_curated_manifest(manifest_path)
        asset = manifest.get("asset") if isinstance(manifest.get("asset"), Mapping) else None
        if not isinstance(asset, Mapping):
            raise RuntimeError("Curated manifest is missing an asset definition.")
        asset_path_value = asset.get("path")
        if not asset_path_value:
            raise RuntimeError("Curated asset is missing a 'path' entry.")
        asset_path = self._resolve_curated_path(asset_path_value)
        if not asset_path.exists():
            raise FileNotFoundError(f"Curated asset missing: {asset_path}")
        return asset_path, False, manifest_path

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

    def _fetch_remote(self, record: RemoteRecord) -> tuple[Path, bool, Path | None]:
        if record.provider == self.PROVIDER_SOLAR_SYSTEM:
            return self._fetch_curated(record)
        if record.provider == self.PROVIDER_NIST:
            return self._generate_nist_csv(record), True, None
        if self._should_use_mast(record):
            return self._fetch_via_mast(record), True, None
        return self._fetch_via_http(record), True, None

    def _generate_nist_csv(self, record: RemoteRecord) -> Path:
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

        with tempfile.NamedTemporaryFile("w", delete=False, newline="", encoding="utf-8", suffix=".csv") as handle:
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

        return Path(handle.name)

    def _fetch_via_http(self, record: RemoteRecord) -> Path:
        session = self._ensure_session()
        response = session.get(record.download_url, timeout=60)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(response.content)
            return Path(handle.name)

    def _fetch_via_mast(self, record: RemoteRecord) -> Path:
        mast = self._ensure_mast()
        result = mast.Observations.download_file(record.download_url, cache=False)
        if not result:
            raise RuntimeError("MAST download did not return a file path")
        path = Path(result)
        if not path.exists():
            raise FileNotFoundError(f"MAST download missing: {path}")
        return path

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
        return astroquery_mast

    def _has_nist_support(self) -> bool:
        return nist_asd_service.dependencies_available()

    def _has_mast_support(self) -> bool:
        return self._has_astroquery()

    def _has_requests(self) -> bool:
        return requests is not None or self.session is not None

    def _has_astroquery(self) -> bool:
        return astroquery_mast is not None and _HAS_PANDAS

    def _has_curated_support(self) -> bool:
        for entry in self._CURATED_TARGETS:
            manifest_ref = entry.get("manifest")
            if not manifest_ref:
                continue
            manifest_path = self._resolve_curated_path(manifest_ref)
            if not manifest_path.exists():
                continue
            try:
                manifest = self._load_curated_manifest(manifest_path)
            except Exception:  # pragma: no cover - defensive guard
                continue
            asset = manifest.get("asset") if isinstance(manifest.get("asset"), Mapping) else None
            if not isinstance(asset, Mapping):
                continue
            asset_path_value = asset.get("path")
            if not asset_path_value:
                continue
            asset_path = self._resolve_curated_path(asset_path_value)
            if asset_path.exists():
                return True
        return False

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


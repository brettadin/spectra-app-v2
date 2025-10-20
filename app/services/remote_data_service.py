"""Abstractions for retrieving remote spectral catalogues and downloads."""

from __future__ import annotations

import csv
import io
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
import csv
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping
from urllib.parse import quote, urlencode, urlparse

from . import nist_asd_service
from .store import LocalStore

try:  # Optional dependency – requests may be absent in minimal installs
    import requests
except Exception:  # pragma: no cover - handled by dependency guards
    requests = None  # type: ignore[assignment]

try:  # Optional dependency – astroquery is heavy and not always bundled
    from astroquery import mast as astroquery_mast
    from astroquery.ipac import nexsci as astroquery_nexsci
except Exception:  # pragma: no cover - handled by dependency guards
    astroquery_mast = None  # type: ignore[assignment]
    astroquery_nexsci = None  # type: ignore[assignment]
else:  # pragma: no branch
    try:
        from astroquery.ipac.nexsci import NasaExoplanetArchive as _ExoplanetArchive
    except Exception:  # pragma: no cover - some astroquery builds omit NExScI
        _ExoplanetArchive = None  # type: ignore[assignment]
    else:  # pragma: no branch
        astroquery_nexsci = _ExoplanetArchive

try:  # Optional dependency – astroquery depends on pandas at runtime
    import pandas  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover - handled by dependency guards
    _HAS_PANDAS = False
else:  # pragma: no branch - simple flag wiring
    _HAS_PANDAS = True


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

    PROVIDER_NIST = "NIST ASD"
    PROVIDER_MAST = "MAST"
    PROVIDER_EXOSYSTEMS = "MAST ExoSystems"

    _DEFAULT_REGION_RADIUS = "0.02 deg"

    _CURATED_TARGETS: tuple[Dict[str, Any], ...] = (
        {
            "names": {"jupiter", "io", "europa", "ganymede", "callisto"},
            "display_name": "Jupiter",
            "object_name": "Jupiter",
            "classification": "Solar System planet",
            "citations": [
                {
                    "title": "JWST Early Release Observations",
                    "doi": "10.3847/1538-4365/acbd9a",
                    "notes": "JWST ERS quick-look spectra curated for Jovian system.",
                }
            ],
        },
        {
            "names": {"mars"},
            "display_name": "Mars",
            "object_name": "Mars",
            "classification": "Solar System planet",
            "citations": [
                {
                    "title": "JWST/NIRSpec Mars observations",
                    "doi": "10.3847/1538-4365/abf3cb",
                    "notes": "Quick-look spectra distributed via Exo.MAST science highlights.",
                }
            ],
        },
        {
            "names": {"saturn", "enceladus", "titan"},
            "display_name": "Saturn",
            "object_name": "Saturn",
            "classification": "Solar System planet",
            "citations": [
                {
                    "title": "Cassini / JWST comparative spectra",
                    "notes": "Curated composite assembled for Spectra examples",
                }
            ],
        },
        {
            "names": {"g2v", "solar analog", "sun-like", "hd 10700", "tau cet"},
            "display_name": "Tau Ceti (G8V)",
            "object_name": "HD 10700",
            "classification": "Nearby solar-type star",
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
            "citations": [
                {
                    "title": "HST CALSPEC standards",
                    "doi": "10.1086/383228",
                    "notes": "CALSPEC flux standards distributed via MAST.",
                }
            ],
        },
    )

    def providers(self) -> List[str]:
        """Return the list of remote providers whose dependencies are satisfied."""

        providers: List[str] = []
        if self._has_nist_support():
            providers.append(self.PROVIDER_NIST)
        if self._has_mast_support():
            providers.append(self.PROVIDER_MAST)
        if self._has_exosystems_support():
            providers.append(self.PROVIDER_EXOSYSTEMS)
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
        if not self._has_exosystems_support():
            reasons[self.PROVIDER_EXOSYSTEMS] = (
                "Install the 'astroquery', 'pandas', and 'requests' packages to enable ExoSystems searches."
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
        if provider == self.PROVIDER_EXOSYSTEMS:
            return self._search_exosystems(query, include_imaging=include_imaging)
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

        fetch_path, cleanup = self._fetch_remote(record)

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

        observation_table = observations.Observations.query_criteria(**criteria)
        observation_rows = self._table_to_records(observation_table)

        if not observation_rows:
            return []

        product_table = observations.Observations.get_product_list(observation_table)
        product_rows = self._table_to_records(product_table)

        observation_lookup: Dict[str, Mapping[str, Any]] = {}
        for row in observation_rows:
            identifier = str(
                row.get("obsid")
                or row.get("ObservationID")
                or row.get("id")
                or row.get("parent_obsid")
                or ""
            ).strip()
            if identifier:
                observation_lookup[identifier] = row

        records: List[RemoteRecord] = []
        for product in product_rows:
            product_obsid = str(
                product.get("obsid")
                or product.get("parent_obsid")
                or product.get("ObservationID")
                or ""
            ).strip()
            if not product_obsid:
                continue

            observation_meta = observation_lookup.get(product_obsid, {})
            combined_meta: Dict[str, Any] = {}
            if isinstance(observation_meta, Mapping):
                combined_meta.update(dict(observation_meta))
            if isinstance(product, Mapping):
                combined_meta.update(dict(product))

            data_uri = (
                combined_meta.get("dataURI")
                or combined_meta.get("ProductURI")
                or combined_meta.get("download_uri")
            )
            if not data_uri:
                continue

            product_type = str(combined_meta.get("productType") or "").lower()
            dataproduct_type = str(combined_meta.get("dataproduct_type") or "").lower()
            is_preview = "preview" in product_type or "preview" in dataproduct_type

            if not is_preview:
                if combined_meta.get("calib_level") is not None:
                    try:
                        if int(float(combined_meta.get("calib_level"))) < 2:
                            continue
                    except (TypeError, ValueError):
                        pass
                if not self._is_spectroscopic(combined_meta):
                    if not include_imaging or not self._is_imaging(combined_meta):
                        continue
            else:
                if not include_imaging:
                    continue

            product_filename = str(combined_meta.get("productFilename") or "").strip()
            target_name = str(
                combined_meta.get("target_name")
                or combined_meta.get("target")
                or combined_meta.get("obs_title")
                or product_obsid
            )

            identifier = product_filename or str(data_uri)
            obs_collection = combined_meta.get("obs_collection")
            instrument_name = combined_meta.get("instrument_name")
            preview_url = combined_meta.get("previewURL") or combined_meta.get("preview_url")

            metadata: Dict[str, Any] = {
                "obsid": product_obsid,
                "obs_collection": obs_collection,
                "instrument_name": instrument_name,
                "target_name": target_name,
                "productFilename": product_filename,
                "dataURI": data_uri,
            }
            if preview_url:
                metadata["previewURL"] = preview_url

            metadata["observation"] = dict(observation_meta)
            metadata["product"] = dict(product)

            units_value = combined_meta.get("units")
            units_map = dict(units_value) if isinstance(units_value, Mapping) else None

            records.append(
                RemoteRecord(
                    provider=self.PROVIDER_MAST,
                    identifier=identifier,
                    title=f"{target_name} — {product_filename}" if product_filename else target_name,
                    download_url=str(data_uri),
                    metadata=metadata,
                    units=units_map,
                )
            )

        return records

    def _search_exosystems(
        self,
        query: Mapping[str, Any],
        *,
        include_imaging: bool = False,
    ) -> List[RemoteRecord]:
        target = str(
            query.get("target_name")
            or query.get("target")
            or query.get("text")
            or query.get("object")
            or ""
        ).strip()
        if not target:
            raise ValueError("ExoSystems searches require a planet, host star, or alias.")

        archive = self._ensure_exoplanet_archive()
        resolved = self._resolve_exoplanet_target(archive, target)
        curated = None
        if not resolved:
            curated = self._resolve_curated_target(target)
            if curated:
                resolved = curated
        if not resolved:
            raise RuntimeError(
                "ExoSystems search could not resolve the requested target via the Exoplanet Archive"
            )

        observations = self._ensure_mast()
        obs_rows = self._query_observations_for_target(observations, resolved, include_imaging)
        if not obs_rows and not curated:
            # If the archive resolved the target but yielded no observations,
            # attempt curated fallbacks before returning an empty list.
            curated = self._resolve_curated_target(target)
            if curated:
                resolved = curated
                obs_rows = self._query_observations_for_target(
                    observations, resolved, include_imaging
                )

        exomast_payload: Dict[str, Any] | None = None
        if resolved.get("transiting"):
            exomast_payload = self._fetch_exomast_filelist(resolved.get("canonical_name"))
            if not exomast_payload and resolved.get("aliases"):
                for alias in resolved["aliases"]:
                    exomast_payload = self._fetch_exomast_filelist(alias)
                    if exomast_payload:
                        break

        records: List[RemoteRecord] = []
        for obs_row in obs_rows:
            try:
                product_table = observations.Observations.get_product_list(obs_row)
            except TypeError:
                product_table = observations.Observations.get_product_list(
                    obs_row.get("obsid") if isinstance(obs_row, Mapping) else obs_row
                )
            for product in self._table_to_records(product_table):
                download_uri = product.get("dataURI") or product.get("ProductURI")
                if not download_uri:
                    continue
                identifier = str(
                    product.get("obsid")
                    or product.get("ObservationID")
                    or product.get("productFilename")
                    or download_uri
                )
                title = self._build_exosystems_title(resolved, obs_row, product)
                metadata = self._build_exosystems_metadata(
                    resolved,
                    obs_row,
                    product,
                    curated=curated is not None,
                    exomast=exomast_payload,
                )
                records.append(
                    RemoteRecord(
                        provider=self.PROVIDER_EXOSYSTEMS,
                        identifier=identifier,
                        title=title,
                        download_url=str(download_uri),
                        metadata=metadata,
                        units=None,
                    )
                )
        return records

    # ------------------------------------------------------------------
    def _query_observations_for_target(
        self,
        observations: Any,
        resolved: Mapping[str, Any],
        include_imaging: bool,
    ) -> List[Mapping[str, Any]]:
        target_name = resolved.get("canonical_name") or resolved.get("display_name")
        aliases = list(resolved.get("aliases", []))
        if resolved.get("object_name") and resolved.get("object_name") not in aliases:
            aliases.append(resolved.get("object_name"))
        coordinates = resolved.get("coordinates") if isinstance(resolved.get("coordinates"), Mapping) else {}
        radius = resolved.get("search_radius") or self._DEFAULT_REGION_RADIUS

        obs_rows: List[Mapping[str, Any]] = []
        if coordinates and coordinates.get("ra") is not None and coordinates.get("dec") is not None:
            try:
                table = observations.Observations.query_region(
                    f"{coordinates['ra']} {coordinates['dec']}",
                    radius=radius,
                )
                obs_rows = self._table_to_records(table)
            except Exception:  # pragma: no cover - fallback to object queries
                obs_rows = []

        if not obs_rows:
            object_names = [name for name in [target_name, *aliases] if name]
            for object_name in object_names:
                try:
                    table = observations.Observations.query_object(object_name)
                except Exception:  # pragma: no cover - ignore astroquery failures
                    continue
                obs_rows = self._table_to_records(table)
                if obs_rows:
                    break

        if not include_imaging:
            filtered: List[Mapping[str, Any]] = []
            for row in obs_rows:
                if self._is_spectroscopic(row):
                    filtered.append(row)
            obs_rows = filtered
        else:
            filtered = []
            for row in obs_rows:
                if self._is_spectroscopic(row) or self._is_imaging(row):
                    filtered.append(row)
            obs_rows = filtered
        return obs_rows

    def _build_exosystems_title(
        self,
        resolved: Mapping[str, Any],
        observation: Mapping[str, Any],
        product: Mapping[str, Any],
    ) -> str:
        parts = [str(resolved.get("display_name") or resolved.get("canonical_name") or "")]
        instrument = observation.get("instrument_name") or observation.get("Instrument")
        if instrument:
            parts.append(str(instrument))
        filters = product.get("filters") or observation.get("filters")
        if filters:
            parts.append(str(filters))
        product_name = product.get("productFilename") or product.get("description")
        if product_name:
            parts.append(str(product_name))
        title = " – ".join(part for part in parts if part)
        return title or str(product.get("productFilename") or product.get("obsid") or "MAST product")

    def _build_exosystems_metadata(
        self,
        resolved: Mapping[str, Any],
        observation: Mapping[str, Any],
        product: Mapping[str, Any],
        *,
        curated: bool,
        exomast: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "target": dict(resolved),
            "observation": dict(observation),
            "product": dict(product),
            "provenance": {
                "exoplanet_archive": not curated,
                "curated_fallback": curated,
            },
        }

        if exomast:
            metadata["exomast"] = dict(exomast)

        mast_fields = (
            "obs_collection",
            "instrument_name",
            "filters",
            "previewURL",
            "dataRights",
            "target_name",
            "obsid",
            "proposal_pi",
            "proposal_id",
        )
        product_fields = (
            "productFilename",
            "productType",
            "dataURI",
            "description",
            "size",
            "calib_level",
            "obs_collection",
            "instrument_name",
            "filters",
            "previewURL",
            "productGroupDescription",
            "productSubGroupDescription",
            "proposal_pi",
            "proposal_id",
            "proposal_name",
            "productDocumentationURL",
            "dataRights",
            "dataID",
            "distance",
            "t_exptime",
            "s_region",
            "em_min",
            "em_max",
        )

        mast_metadata: Dict[str, Any] = {}
        for field in mast_fields:
            if field in observation:
                mast_metadata[field] = observation[field]
        for field in product_fields:
            if field in product and field not in mast_metadata:
                mast_metadata[field] = product[field]
        if mast_metadata:
            metadata.setdefault("mast", mast_metadata)

        citations: List[Mapping[str, Any]] = []
        base_citations = resolved.get("citations")
        if isinstance(base_citations, list):
            for citation in base_citations:
                if isinstance(citation, Mapping):
                    citations.append(dict(citation))
        product_citation_keys = ("dataID", "dataURL", "dataURI", "productDocumentationURL", "doi")
        for key in product_citation_keys:
            if key in product:
                citations.append({"field": key, "value": product[key]})
        if citations:
            metadata.setdefault("citations", citations)

        return metadata

    def _resolve_exoplanet_target(
        self,
        archive: Any,
        target: str,
    ) -> Dict[str, Any] | None:
        tables = ("pscomppars", "ps")
        cleaned_target = target.strip()
        aliases: List[str] = []
        base_row: Dict[str, Any] | None = None
        resolved_table = None
        for table_name in tables:
            try:
                result = archive.query_object(cleaned_target, table=table_name)
            except Exception:
                continue
            rows = self._table_to_records(result)
            if not rows:
                continue
            base_row = dict(rows[0])
            resolved_table = table_name
            break

        if not base_row:
            return None

        ra = base_row.get("ra") or base_row.get("rastr") or base_row.get("ra_str")
        dec = base_row.get("dec") or base_row.get("decstr") or base_row.get("dec_str")
        try:
            ra_value = float(ra) if ra is not None else None
        except (TypeError, ValueError):  # pragma: no cover - depends on astroquery payload
            ra_value = None
        try:
            dec_value = float(dec) if dec is not None else None
        except (TypeError, ValueError):  # pragma: no cover - depends on astroquery payload
            dec_value = None

        canonical_name = str(
            base_row.get("pl_name")
            or base_row.get("hostname")
            or base_row.get("star_name")
            or cleaned_target
        )
        host_name = base_row.get("hostname") or base_row.get("star_name")

        for key in ("pl_name", "pl_letter", "hostname", "star_name", "sy_sname"):
            value = base_row.get(key)
            if isinstance(value, str):
                aliases.append(value)

        citation_keys = (
            "pl_refname",
            "disc_pubdate",
            "discoverymethod",
            "disc_facility",
            "disc_year",
        )
        citations: List[Dict[str, Any]] = []
        for key in citation_keys:
            if base_row.get(key) is not None:
                citations.append({"field": key, "value": base_row.get(key)})

        transiting = False
        for key in ("pl_tranflag", "tran_flag", "transit_flag"):
            if base_row.get(key) in (1, True, "1", "true", "True"):
                transiting = True
                break

        coordinates: Dict[str, Any] | None = None
        if ra_value is not None and dec_value is not None:
            coordinates = {
                "ra": ra_value,
                "dec": dec_value,
                "epoch": base_row.get("epoch") or base_row.get("ra_epoch"),
            }

        metadata: Dict[str, Any] = {
            "canonical_name": canonical_name,
            "display_name": base_row.get("pl_name") or canonical_name,
            "host_star": host_name,
            "aliases": sorted({alias for alias in aliases if alias}),
            "coordinates": coordinates,
            "search_radius": self._DEFAULT_REGION_RADIUS,
            "transiting": transiting,
            "citations": citations,
            "exoplanet_archive": {
                "table": resolved_table,
                "row": base_row,
            },
        }
        return metadata

    def _resolve_curated_target(self, target: str) -> Dict[str, Any] | None:
        lower = target.strip().lower()
        for entry in self._CURATED_TARGETS:
            if lower in entry["names"]:
                aliases = sorted(entry["names"] - {lower})
                metadata = {
                    "canonical_name": entry["display_name"],
                    "display_name": entry["display_name"],
                    "aliases": aliases,
                    "coordinates": None,
                    "object_name": entry.get("object_name"),
                    "search_radius": entry.get("search_radius", self._DEFAULT_REGION_RADIUS),
                    "classification": entry.get("classification"),
                    "citations": entry.get("citations", []),
                    "transiting": entry.get("transiting", False),
                    "curated": True,
                }
                return metadata
        return None

    def _fetch_exomast_filelist(self, planet_name: Any) -> Dict[str, Any] | None:
        if not planet_name or not isinstance(planet_name, str):
            return None
        if not self._has_requests():
            return None
        session = self._ensure_session()
        url = (
            "https://exo.mast.stsci.edu/api/v0.1/spectra/"
            f"{quote(planet_name.strip())}/filelist"
        )
        try:
            response = session.get(url, timeout=60)
            response.raise_for_status()
        except Exception:  # pragma: no cover - network failures handled gracefully
            return None
        try:
            payload = response.json()
        except Exception:  # pragma: no cover - JSON decoding fallback
            return None
        if isinstance(payload, Mapping):
            return dict(payload)
        return None

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

    def _fetch_remote(self, record: RemoteRecord) -> tuple[Path, bool]:
        if record.provider == self.PROVIDER_NIST:
            return self._generate_nist_csv(record), True
        if self._should_use_mast(record):
            return self._fetch_via_mast(record), True
        return self._fetch_via_http(record), True

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
        if record.provider in {self.PROVIDER_MAST, self.PROVIDER_EXOSYSTEMS}:
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

    def _ensure_exoplanet_archive(self):
        if not self._has_exosystems_support():
            raise RuntimeError(
                "The 'astroquery', 'pandas', and 'requests' packages are required for ExoSystems searches"
            )
        if astroquery_nexsci is None:
            raise RuntimeError("astroquery.ipac.nexsci is unavailable in this environment")
        return astroquery_nexsci

    def _has_nist_support(self) -> bool:
        return nist_asd_service.dependencies_available()

    def _has_mast_support(self) -> bool:
        return self._has_astroquery()

    def _has_exosystems_support(self) -> bool:
        return (
            self._has_astroquery()
            and self._has_requests()
            and astroquery_nexsci is not None
            and hasattr(astroquery_nexsci, "query_object")
        )

    def _has_requests(self) -> bool:
        return requests is not None or self.session is not None

    def _has_astroquery(self) -> bool:
        return astroquery_mast is not None and _HAS_PANDAS

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


"""Abstractions for retrieving remote spectral catalogues and downloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping
from urllib.parse import urlparse

from .store import LocalStore

try:  # Optional dependency – requests may be absent in minimal installs
    import requests
except Exception:  # pragma: no cover - handled by dependency guards
    requests = None  # type: ignore[assignment]

try:  # Optional dependency – astroquery is heavy and not always bundled
    from astroquery import mast as astroquery_mast
except Exception:  # pragma: no cover - handled by dependency guards
    astroquery_mast = None  # type: ignore[assignment]


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
    nist_search_url: str = "https://physics.nist.gov/cgi-bin/ASD/lines/linesearch.pl"
    mast_product_fields: Iterable[str] = field(
        default_factory=lambda: ("obsid", "target_name", "productFilename", "dataURI")
    )

    PROVIDER_NIST = "NIST ASD"
    PROVIDER_MAST = "MAST"

    def providers(self) -> List[str]:
        """Return the list of remote providers whose dependencies are satisfied."""

        providers: List[str] = []
        if self._has_requests():
            providers.append(self.PROVIDER_NIST)
            if self._has_astroquery():
                providers.append(self.PROVIDER_MAST)
        return providers

    def unavailable_providers(self) -> Dict[str, str]:
        """Describe catalogues that cannot be used because dependencies are missing."""

        reasons: Dict[str, str] = {}
        if not self._has_requests():
            reasons[self.PROVIDER_NIST] = "Install the 'requests' package to enable remote downloads."
            reasons[self.PROVIDER_MAST] = (
                "Install the 'requests' and 'astroquery' packages to enable MAST searches."
            )
            return reasons
        if not self._has_astroquery():
            reasons[self.PROVIDER_MAST] = "Install the 'astroquery' package to enable MAST searches."
        return reasons

    # ------------------------------------------------------------------
    def search(self, provider: str, query: Mapping[str, Any]) -> List[RemoteRecord]:
        if provider == self.PROVIDER_NIST:
            return self._search_nist(query)
        if provider == self.PROVIDER_MAST:
            return self._search_mast(query)
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

        mast_provenance: Dict[str, Any] | None = None
        cleanup_tmp = False
        if record.provider == self.PROVIDER_MAST:
            tmp_path = self._download_via_mast(record)
            mast_provenance = {
                "mast": {
                    "downloaded_via": "astroquery.mast.Observations.download_file",
                }
            }
        else:
            session = self._ensure_session()
            response = session.get(record.download_url, timeout=60)
            response.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False) as handle:
                handle.write(response.content)
                tmp_path = Path(handle.name)
            cleanup_tmp = True

        tmp_path = Path(tmp_path)

        x_unit, y_unit = record.resolved_units()
        remote_metadata = {
            "provider": record.provider,
            "uri": record.download_url,
            "identifier": record.identifier,
            "fetched_at": self._timestamp(),
            "metadata": json.loads(json.dumps(record.metadata)),
        }
        if mast_provenance is not None:
            remote_metadata.update(mast_provenance)
        store_entry = self.store.record(
            tmp_path,
            x_unit=x_unit,
            y_unit=y_unit,
            source={"remote": remote_metadata},
            alias=record.suggested_filename(),
        )
        if cleanup_tmp:
            tmp_path.unlink(missing_ok=True)

        return RemoteDownloadResult(
            record=record,
            cache_entry=store_entry,
            path=Path(store_entry["stored_path"]),
            cached=False,
        )

    # ------------------------------------------------------------------
    def _search_nist(self, query: Mapping[str, Any]) -> List[RemoteRecord]:
        session = self._ensure_session()
        params: Dict[str, Any] = {
            "format": "json",
            "spectra": query.get("element") or query.get("spectra") or query.get("text") or "",
        }
        if query.get("wavelength_min") is not None:
            params["wavemin"] = query["wavelength_min"]
        if query.get("wavelength_max") is not None:
            params["wavemax"] = query["wavelength_max"]
        response = session.get(self.nist_search_url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or payload.get("lines") or []
        records: List[RemoteRecord] = []
        for idx, entry in enumerate(results):
            if not isinstance(entry, Mapping):
                continue
            metadata = dict(entry)
            identifier = str(
                metadata.get("id")
                or metadata.get("identifier")
                or metadata.get("transition")
                or idx
            )
            title = str(
                metadata.get("species")
                or metadata.get("title")
                or metadata.get("transition")
                or identifier
            )
            download_uri = (
                metadata.get("download_uri")
                or metadata.get("data_uri")
                or metadata.get("url")
                or metadata.get("uri")
            )
            if not download_uri:
                download_uri = f"{self.nist_search_url}?download={identifier}"
            units = metadata.get("units")
            records.append(
                RemoteRecord(
                    provider=self.PROVIDER_NIST,
                    identifier=identifier,
                    title=title,
                    download_url=str(download_uri),
                    metadata=metadata,
                    units=units if isinstance(units, Mapping) else None,
                )
            )
        return records

    def _search_mast(self, query: Mapping[str, Any]) -> List[RemoteRecord]:
        observations = self._ensure_mast()
        criteria = dict(query)
        if "text" in criteria:
            text_value = criteria.pop("text")
            if "target_name" not in criteria:
                normalized = self._normalize_mast_text(text_value)
                if normalized is not None:
                    criteria["target_name"] = normalized
        table = observations.Observations.query_criteria(**criteria)
        rows = self._table_to_records(table)
        records: List[RemoteRecord] = []
        for row in rows:
            metadata = dict(row)
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

    @staticmethod
    def _normalize_mast_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        try:
            text = str(value)
        except Exception:
            return None
        stripped = text.strip()
        return stripped or None

    # ------------------------------------------------------------------
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

    def _ensure_session(self):
        if self.session is not None:
            return self.session
        if requests is None:
            raise RuntimeError("The 'requests' package is required for remote downloads")
        self.session = requests.Session()
        return self.session

    def _ensure_mast(self):
        if astroquery_mast is None:
            raise RuntimeError("The 'astroquery' package is required for MAST searches")
        return astroquery_mast

    def _download_via_mast(self, record: RemoteRecord) -> Path:
        observations = self._ensure_mast()
        path = observations.Observations.download_file(record.download_url, cache=False)
        return Path(path)

    def _has_requests(self) -> bool:
        return requests is not None or self.session is not None

    def _has_astroquery(self) -> bool:
        return astroquery_mast is not None

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


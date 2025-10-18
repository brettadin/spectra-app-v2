"""Abstractions for retrieving remote spectral catalogues and downloads."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping
from urllib.parse import urlencode, urlparse

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
    nist_search_url: str = "https://physics.nist.gov/cgi-bin/ASD/lines1.pl"
    mast_product_fields: Iterable[str] = field(
        default_factory=lambda: ("obsid", "target_name", "productFilename", "dataURI")
    )
    nist_page_size: int = 100

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
        session = self._ensure_session()

        search_term = str(query.get("element") or query.get("text") or "").strip()
        if not search_term:
            raise ValueError("NIST searches require an element or ion query.")

        params = self._build_nist_params(search_term, query)
        response = session.get(self.nist_search_url, params=params, timeout=60)
        response.raise_for_status()

        text = response.text
        if self._nist_response_is_error(text):
            message = self._extract_nist_error_message(text)
            raise RuntimeError(message or "NIST ASD returned an error for the query.")

        rows = self._parse_nist_csv(text)
        records: List[RemoteRecord] = []
        if not rows:
            return records

        base_metadata = {
            "search_term": search_term,
            "wavelength_min_nm": self._as_float(query.get("wavelength_min")),
            "wavelength_max_nm": self._as_float(query.get("wavelength_max")),
            "page_no": int(params.get("page_no", 1)),
            "page_size": int(params.get("page_size", self.nist_page_size)),
        }
        offset = (base_metadata["page_no"] - 1) * base_metadata["page_size"]

        for index, row in enumerate(rows):
            record = self._build_nist_record(
                search_term=search_term,
                row=row,
                base_params=params,
                base_metadata=base_metadata,
                row_index=index,
                absolute_index=offset + index,
            )
            records.append(record)
        return records

    def _search_mast(self, query: Mapping[str, Any]) -> List[RemoteRecord]:
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
        criteria.setdefault("dataproduct_type", "spectrum")
        criteria.setdefault("intentType", "SCIENCE")
        if "calib_level" not in criteria:
            criteria["calib_level"] = [2, 3]

        table = observations.Observations.query_criteria(**criteria)
        rows = self._table_to_records(table)
        records: List[RemoteRecord] = []
        for row in rows:
            metadata = dict(row)
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

    # ------------------------------------------------------------------
    def _build_nist_params(self, search_term: str, query: Mapping[str, Any]) -> Dict[str, str]:
        page_size = int(query.get("page_size") or self.nist_page_size)
        page_size = max(1, min(page_size, 500))
        page_no = int(query.get("page_no") or 1)
        page_no = max(page_no, 1)

        low = self._as_float(query.get("wavelength_min"))
        high = self._as_float(query.get("wavelength_max"))

        params: Dict[str, str] = {
            "spectra": search_term,
            "format": "2",
            "output": "1",
            "page_size": str(page_size),
            "page_no": str(page_no),
            "A_out": "0",
            "allowed_out": "1",
            "forbid_out": "1",
            "show_obs_wl": "1",
            "show_calc_wl": "1",
            "show_diff_obs_calc": "1",
            "show_wn": "1",
            "unc_out": "1",
            "conf_out": "1",
            "term_out": "1",
            "enrg_out": "1",
            "J_out": "1",
            "intens_out": "1",
            "ids_out": "1",
            "show_av": "2",
            "output_type": "0",
            "unit": "0",
            "line_out": "0",
            "order_out": "0",
        }
        params["low_w"] = f"{low:g}" if low is not None else "1"
        params["upp_w"] = f"{high:g}" if high is not None else "100000"
        return params

    def _nist_response_is_error(self, text: str) -> bool:
        snippet = text.lstrip()
        if snippet.startswith("<!DOCTYPE html") and "Error Message:" in text:
            return True
        return "Software error" in text

    def _extract_nist_error_message(self, text: str) -> str | None:
        marker = "<FONT COLOR=red>"
        if marker in text:
            start = text.index(marker) + len(marker)
            end = text.find("</FONT>", start)
            message = text[start:end] if end != -1 else text[start:]
            return self._clean_nist_value(message)
        if "Software error" in text:
            return "NIST ASD reported a server-side error. Please retry later."
        return None

    def _parse_nist_csv(self, text: str) -> List[Dict[str, str]]:
        reader = csv.reader(io.StringIO(text))
        header: List[str] = []
        rows: List[Dict[str, str]] = []
        for raw in reader:
            if not raw:
                continue
            first = raw[0].strip()
            if first.lower().startswith("<form"):
                break
            cleaned = [self._clean_nist_value(value) for value in raw]
            if not header:
                header = cleaned
                continue
            if all(not value for value in cleaned):
                continue
            entry: Dict[str, str] = {}
            for idx, key in enumerate(header):
                if not key:
                    continue
                if idx >= len(cleaned):
                    break
                entry[key] = cleaned[idx]
            if entry:
                rows.append(entry)
        return rows

    def _clean_nist_value(self, value: str | None) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if text.startswith("\"") and text.endswith("\""):
            text = text[1:-1]
        text = text.strip()
        if text.startswith("="):
            text = text[1:]
        text = text.replace("\"\"", "\"")
        while text.startswith("\"") and text.endswith("\"") and len(text) >= 2:
            text = text[1:-1].strip()
        text = text.strip("\"")
        text = text.replace("&nbsp;", " ")
        return text.strip()

    def _build_nist_record(
        self,
        *,
        search_term: str,
        row: Mapping[str, str],
        base_params: Mapping[str, str],
        base_metadata: Mapping[str, Any],
        row_index: int,
        absolute_index: int,
    ) -> RemoteRecord:
        download_params = dict(base_params)
        download_url = f"{self.nist_search_url}?{urlencode(download_params)}"

        obs_wl = self._as_float(row.get("obs_wl_vac(A)"))
        ritz_wl = self._as_float(row.get("ritz_wl_vac(A)"))
        representative_wl = ritz_wl or obs_wl

        intensity = self._as_float(row.get("intens"))
        einstein_a = self._as_float(row.get("Aki(s^-1)"))
        wavenumber = self._as_float(row.get("wn(cm-1)"))

        lower_level = {
            "energy_cm-1": self._as_float(row.get("Ei(cm-1)")),
            "configuration": row.get("conf_i") or None,
            "term": row.get("term_i") or None,
            "J": row.get("J_i") or None,
            "id": row.get("ID_i") or None,
        }
        upper_level = {
            "energy_cm-1": self._as_float(row.get("Ek(cm-1)")),
            "configuration": row.get("conf_k") or None,
            "term": row.get("term_k") or None,
            "J": row.get("J_k") or None,
            "id": row.get("ID_k") or None,
        }

        metadata: Dict[str, Any] = {
            "provider": self.PROVIDER_NIST,
            "search": dict(base_metadata),
            "row_index": row_index,
            "absolute_index": absolute_index,
            "wavelength_vacuum_A": representative_wl,
            "wavelength_observed_A": obs_wl,
            "wavelength_ritz_A": ritz_wl,
            "observed_minus_ritz_A": self._as_float(row.get("obs-ritz")),
            "uncertainty_obs_A": self._as_float(row.get("unc_obs_wl")),
            "uncertainty_ritz_A": self._as_float(row.get("unc_ritz_wl")),
            "wavenumber_cm-1": wavenumber,
            "intensity_relative": intensity,
            "einstein_A_s-1": einstein_a,
            "accuracy": row.get("Acc") or None,
            "transition_type": row.get("Type") or None,
            "lower_level": lower_level,
            "upper_level": upper_level,
            "nist_level_ids": {
                "lower": row.get("ID_i") or None,
                "upper": row.get("ID_k") or None,
            },
            "download": {
                "url": download_url,
                "parameters": dict(download_params),
            },
        }

        identifier = self._derive_nist_identifier(search_term, row, absolute_index, representative_wl)
        title = self._derive_nist_title(search_term, row, representative_wl)

        units = {"x": "Angstrom (vacuum)", "y": "relative intensity (arbitrary)"}

        return RemoteRecord(
            provider=self.PROVIDER_NIST,
            identifier=identifier,
            title=title,
            download_url=download_url,
            metadata=metadata,
            units=units,
        )

    def _derive_nist_identifier(
        self,
        search_term: str,
        row: Mapping[str, str],
        absolute_index: int,
        wavelength: float | None,
    ) -> str:
        lower_id = row.get("ID_i")
        upper_id = row.get("ID_k")
        if lower_id or upper_id:
            parts = [search_term]
            if lower_id:
                parts.append(lower_id)
            if upper_id:
                parts.append(f"→{upper_id}")
            return " ".join(parts)
        if wavelength is not None:
            return f"{search_term} λ {wavelength:.3f} Å"
        return f"{search_term} line {absolute_index + 1}"

    def _derive_nist_title(
        self,
        search_term: str,
        row: Mapping[str, str],
        wavelength: float | None,
    ) -> str:
        parts = [search_term]
        if wavelength is not None:
            parts.append(f"λ {wavelength:.3f} Å")
        transition = self._format_nist_transition(row)
        if transition:
            parts.append(transition)
        return " – ".join(parts)

    def _format_nist_transition(self, row: Mapping[str, str]) -> str | None:
        lower = row.get("term_i") or ""
        lower_j = row.get("J_i") or ""
        upper = row.get("term_k") or ""
        upper_j = row.get("J_k") or ""

        lower_label = lower.strip()
        if lower_j:
            suffix = lower_j.strip()
            lower_label = f"{lower_label} ({suffix})" if lower_label else suffix

        upper_label = upper.strip()
        if upper_j:
            suffix = upper_j.strip()
            upper_label = f"{upper_label} ({suffix})" if upper_label else suffix

        if lower_label and upper_label:
            return f"{lower_label} → {upper_label}"
        return lower_label or upper_label or None

    def _as_float(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return None
        text = text.replace("\xa0", " ")
        try:
            return float(text)
        except ValueError:
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

    def _fetch_remote(self, record: RemoteRecord) -> tuple[Path, bool]:
        if self._should_use_mast(record):
            return self._fetch_via_mast(record), True
        return self._fetch_via_http(record), True

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
            raise RuntimeError(
                "The 'requests' package is required for remote downloads. "
                "Install it via `pip install -r requirements.txt` or `poetry install --with remote`."
            )
        self.session = requests.Session()
        return self.session

    def _ensure_mast(self):
        if astroquery_mast is None:
            raise RuntimeError(
                "The 'astroquery' package is required for MAST searches. "
                "Install it via `pip install -r requirements.txt` or `poetry install --with remote`."
            )
        return astroquery_mast

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


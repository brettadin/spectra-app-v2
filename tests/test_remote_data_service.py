"""Regression coverage for the remote data service."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from app.services import LocalStore, RemoteDataService, RemoteRecord

from app.services import remote_data_service as remote_module


class DummyResponse:
    def __init__(self, *, json_payload: Any | None = None, content: bytes = b"", status: int = 200):
        self._json = json_payload or {}
        self.content = content
        self.status_code = status

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP error {self.status_code}")


class DummySession:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses: list[DummyResponse] = []

    def queue(self, response: DummyResponse) -> None:
        self.responses.append(response)

    def get(self, url: str, params: dict[str, Any] | None = None, timeout: int | None = None) -> DummyResponse:
        self.calls.append({"url": url, "params": params or {}, "timeout": timeout})
        if not self.responses:
            raise AssertionError("No queued response for request")
        return self.responses.pop(0)


@pytest.fixture()
def store(tmp_path: Path) -> LocalStore:
    return LocalStore(base_dir=tmp_path)


def test_search_nist_constructs_url_and_params(store: LocalStore) -> None:
    session = DummySession()
    session.queue(
        DummyResponse(
            json_payload={
                "results": [
                    {
                        "id": "FeII-1",
                        "species": "Fe II",
                        "download_uri": "https://example.test/FeII-1.csv",
                        "units": {"x": "nm", "y": "absorbance"},
                    }
                ]
            }
        )
    )
    service = RemoteDataService(store, session=session)

    records = service.search(
        RemoteDataService.PROVIDER_NIST,
        {"element": "Fe II", "wavelength_min": 250.0, "wavelength_max": 260.0},
    )

    assert session.calls, "The HTTP session should have been invoked"
    call = session.calls[0]
    assert call["url"] == service.nist_search_url
    assert call["params"]["spectra"] == "Fe II"
    assert call["params"]["wavemin"] == 250.0
    assert call["params"]["wavemax"] == 260.0
    assert len(records) == 1
    assert records[0].download_url == "https://example.test/FeII-1.csv"


def test_download_uses_cache_and_records_provenance(store: LocalStore) -> None:
    session = DummySession()
    content = b"wavelength,flux\n100,0.1\n"
    session.queue(DummyResponse(content=content))
    service = RemoteDataService(store, session=session)
    record = RemoteRecord(
        provider=RemoteDataService.PROVIDER_NIST,
        identifier="FeII-1",
        title="Fe II",
        download_url="https://example.test/FeII-1.csv",
        metadata={"note": "synthetic", "units": {"x": "nm", "y": "absorbance"}},
        units={"x": "nm", "y": "absorbance"},
    )

    first = service.download(record)
    assert first.cached is False
    stored_path = Path(first.cache_entry["stored_path"])
    assert stored_path.exists()
    expected_sha = hashlib.sha256(content).hexdigest()
    assert first.cache_entry["sha256"] == expected_sha
    remote_meta = first.cache_entry.get("source", {}).get("remote", {})
    assert remote_meta.get("uri") == record.download_url
    assert remote_meta.get("provider") == RemoteDataService.PROVIDER_NIST
    assert "fetched_at" in remote_meta

    # Second download should use the cache and avoid another HTTP request
    before_calls = len(session.calls)
    cached = service.download(record)
    assert cached.cached is True
    assert len(session.calls) == before_calls
    assert Path(cached.cache_entry["stored_path"]) == stored_path


def test_search_mast_table_conversion(store: LocalStore, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyObservations:
        criteria: dict[str, Any] | None = None

        @classmethod
        def query_criteria(cls, **criteria: Any) -> list[dict[str, Any]]:
            cls.criteria = dict(criteria)
            return [
                {
                    "obsid": "12345",
                    "target_name": "WASP-96 b",
                    "dataURI": "mast:JWST/product.fits",
                    "units": {"x": "um", "y": "flux"},
                    "dataproduct_type": "spectrum",
                },
                {
                    "obsid": "12346",
                    "target_name": "WASP-96 b",
                    "dataURI": "mast:JWST/image.fits",
                    "dataproduct_type": "image",
                },
            ]

    class DummyMast:
        Observations = DummyObservations

    service = RemoteDataService(store, session=None)
    monkeypatch.setattr(service, "_ensure_mast", lambda: DummyMast)

    records = service.search(RemoteDataService.PROVIDER_MAST, {"text": "WASP-96 b"})

    assert DummyObservations.criteria is not None
    assert DummyObservations.criteria.get("target_name") == "WASP-96 b"
    assert DummyObservations.criteria.get("dataproduct_type") == "spectrum"
    assert DummyObservations.criteria.get("intentType") == "SCIENCE"
    assert DummyObservations.criteria.get("calib_level") == [2, 3]
    assert "text" not in DummyObservations.criteria
    assert len(records) == 1
    assert records[0].identifier == "12345"
    assert records[0].download_url == "mast:JWST/product.fits"
    assert records[0].units == {"x": "um", "y": "flux"}


def test_search_mast_can_include_imaging(store: LocalStore, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyObservations:
        criteria: dict[str, Any] | None = None

        @classmethod
        def query_criteria(cls, **criteria: Any) -> list[dict[str, Any]]:
            cls.criteria = dict(criteria)
            return [
                {
                    "obsid": "12345",
                    "target_name": "WASP-96 b",
                    "dataURI": "mast:JWST/product.fits",
                    "units": {"x": "um", "y": "flux"},
                    "dataproduct_type": "spectrum",
                },
                {
                    "obsid": "12346",
                    "target_name": "WASP-96 b",
                    "dataURI": "mast:JWST/image.fits",
                    "dataproduct_type": "image",
                },
            ]

    class DummyMast:
        Observations = DummyObservations

    service = RemoteDataService(store, session=None)
    monkeypatch.setattr(service, "_ensure_mast", lambda: DummyMast)

    records = service.search(
        RemoteDataService.PROVIDER_MAST,
        {"target_name": "WASP-96 b"},
        include_imaging=True,
    )

    assert DummyObservations.criteria is not None
    assert DummyObservations.criteria.get("dataproduct_type") == ["spectrum", "image"]
    identifiers = {record.identifier for record in records}
    assert identifiers == {"12345", "12346"}


def test_search_mast_requires_non_empty_criteria(store: LocalStore) -> None:
    service = RemoteDataService(store, session=None)

    with pytest.raises(ValueError):
        service.search(RemoteDataService.PROVIDER_MAST, {})


def test_download_mast_uses_astroquery(
    store: LocalStore, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    download_calls: dict[str, Any] = {}

    class DummyObservations:
        @staticmethod
        def query_criteria(**criteria: Any) -> list[dict[str, Any]]:
            return []

        @staticmethod
        def download_file(data_uri: str, cache: bool = False) -> Path:
            download_calls["uri"] = data_uri
            download_calls["cache"] = cache
            target = tmp_path / "mast_product.fits"
            target.write_bytes(b"mast-bytes")
            return target

    class DummyMast:
        Observations = DummyObservations

    service = RemoteDataService(store, session=None)
    monkeypatch.setattr(service, "_ensure_mast", lambda: DummyMast)

    record = RemoteRecord(
        provider=RemoteDataService.PROVIDER_MAST,
        identifier="obs123",
        title="WASP-96 b",
        download_url="mast:JWST/product.fits",
        metadata={"units": {"x": "um", "y": "flux"}},
        units={"x": "um", "y": "flux"},
    )

    result = service.download(record, force=True)

    assert download_calls["uri"] == "mast:JWST/product.fits"
    assert download_calls["cache"] is False
    assert result.cached is False
    remote_meta = result.cache_entry.get("source", {}).get("remote", {})
    assert remote_meta.get("provider") == RemoteDataService.PROVIDER_MAST
    assert remote_meta.get("uri") == record.download_url
    stored_path = Path(result.cache_entry["stored_path"])
    assert stored_path.exists()


def test_providers_hide_missing_dependencies(monkeypatch: pytest.MonkeyPatch, store: LocalStore) -> None:
    monkeypatch.setattr(remote_module, "requests", None)
    monkeypatch.setattr(remote_module, "astroquery_mast", None)
    monkeypatch.setattr(remote_module, "_HAS_PANDAS", False)
    service = RemoteDataService(store, session=None)

    assert service.providers() == []
    unavailable = service.unavailable_providers()
    assert remote_module.RemoteDataService.PROVIDER_NIST in unavailable
    assert remote_module.RemoteDataService.PROVIDER_MAST in unavailable

    # Restoring requests but not astroquery keeps NIST available while flagging MAST.
    class DummyRequests:
        class Session:
            def __call__(self) -> None:  # pragma: no cover - defensive
                return None

    monkeypatch.setattr(remote_module, "requests", DummyRequests)
    service = RemoteDataService(store, session=None)

    assert service.providers() == [remote_module.RemoteDataService.PROVIDER_NIST]
    unavailable = service.unavailable_providers()
    assert remote_module.RemoteDataService.PROVIDER_MAST in unavailable

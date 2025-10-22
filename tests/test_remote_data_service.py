"""Regression coverage for the remote data service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.services import LocalStore, RemoteDataService, RemoteRecord

from app.services import remote_data_service as remote_module


class DummyResponse:
    def __init__(
        self,
        *,
        json_payload: Any | None = None,
        content: bytes = b"",
        text: str | None = None,
        status: int = 200,
    ):
        self._json = json_payload or {}
        self.content = content
        self.status_code = status
        if text is not None:
            self.text = text
        elif content:
            try:
                self.text = content.decode("utf-8")
            except UnicodeDecodeError:
                self.text = ""
        else:
            self.text = ""

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


def test_fetch_exomast_filelist_does_not_double_encode_spaces(
    store: LocalStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = RemoteDataService(store, session=None)

    session = DummySession()
    session.queue(DummyResponse(json_payload={"products": []}))

    monkeypatch.setattr(RemoteDataService, "_ensure_session", lambda self: session)

    payload = service._fetch_exomast_filelist("WASP-39 b")

    assert session.calls, "Expected Exo.MAST request to be issued"
    assert session.calls[0]["url"].endswith("/WASP-39%20b/filelist")
    assert payload == {"products": []}


def test_search_nist_uses_nist_service(store: LocalStore, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_dependencies() -> bool:
        return True

    def fake_fetch(
        identifier: str,
        *,
        element: str | None = None,
        ion_stage: str | int | None = None,
        lower_wavelength: float | None = None,
        upper_wavelength: float | None = None,
        wavelength_unit: str = "nm",
        use_ritz: bool = True,
        wavelength_type: str = "vacuum",
    ) -> dict[str, Any]:
        captured.update(
            {
                "identifier": identifier,
                "element": element,
                "ion_stage": ion_stage,
                "lower": lower_wavelength,
                "upper": upper_wavelength,
                "unit": wavelength_unit,
                "use_ritz": use_ritz,
                "wavelength_type": wavelength_type,
            }
        )
        return {
            "wavelength_nm": [510.0],
            "intensity": [120.0],
            "intensity_normalized": [1.0],
            "lines": [
                {
                    "wavelength_nm": 510.0,
                    "relative_intensity": 120.0,
                    "relative_intensity_normalized": 1.0,
                }
            ],
            "meta": {
                "label": "Fe II (NIST ASD)",
                "element_symbol": "Fe",
                "element_name": "Iron",
                "atomic_number": 26,
                "ion_stage": "II",
                "ion_stage_number": 2,
                "query": {
                    "identifier": identifier,
                    "linename": "Fe II",
                    "lower_wavelength": lower_wavelength,
                    "upper_wavelength": upper_wavelength,
                    "wavelength_unit": wavelength_unit,
                    "wavelength_type": wavelength_type,
                    "use_ritz": use_ritz,
                },
                "fetched_at_utc": "2025-10-18T00:00:00Z",
                "citation": "citation",
                "retrieved_via": "astroquery.nist",
            },
        }

    monkeypatch.setattr(remote_module.nist_asd_service, "dependencies_available", fake_dependencies)
    monkeypatch.setattr(remote_module.nist_asd_service, "fetch_lines", fake_fetch)

    service = RemoteDataService(store, session=None)

    records = service.search(
        RemoteDataService.PROVIDER_NIST,
        {"element": "Fe II", "wavelength_min": 250.0, "wavelength_max": 260.0},
    )

    assert captured["identifier"] == "Fe II"
    assert captured["lower"] == 250.0
    assert captured["upper"] == 260.0
    assert captured["unit"] == "nm"
    assert len(records) == 1
    record = records[0]
    assert record.provider == RemoteDataService.PROVIDER_NIST
    assert record.download_url.startswith("nist-asd:")
    assert record.metadata.get("line_count") == 1
    assert record.metadata["series"]["wavelength_nm"] == [510.0]


def test_download_nist_generates_csv_and_records_provenance(store: LocalStore) -> None:
    service = RemoteDataService(store, session=None)
    metadata = {
        "lines": [
            {
                "wavelength_nm": 510.0,
                "relative_intensity": 120.0,
                "relative_intensity_normalized": 1.0,
                "observed_wavelength_nm": 509.9,
                "ritz_wavelength_nm": 510.02,
                "lower_level": "a 6D",
                "upper_level": "z 6F",
            }
        ],
        "query": {
            "identifier": "Fe II",
            "linename": "Fe II",
            "lower_wavelength": 250.0,
            "upper_wavelength": 260.0,
            "wavelength_unit": "nm",
            "wavelength_type": "vacuum",
            "use_ritz": True,
        },
        "element_symbol": "Fe",
        "element_name": "Iron",
        "ion_stage_number": 2,
    }
    record = RemoteRecord(
        provider=RemoteDataService.PROVIDER_NIST,
        identifier="Fe II (NIST ASD)",
        title="Fe II — 1 line",
        download_url="nist-asd:Fe_II",
        metadata=metadata,
        units={"x": "nm", "y": "relative_intensity"},
    )

    first = service.download(record, force=True)
    assert first.cached is False
    stored_path = Path(first.cache_entry["stored_path"])
    assert stored_path.exists()
    text = stored_path.read_text(encoding="utf-8")
    assert "Wavelength (nm)" in text
    assert "510" in text
    remote_meta = first.cache_entry.get("source", {}).get("remote", {})
    assert remote_meta.get("uri") == record.download_url
    assert remote_meta.get("provider") == RemoteDataService.PROVIDER_NIST
    assert "fetched_at" in remote_meta

    cached = service.download(record)
    assert cached.cached is True
    assert Path(cached.cache_entry["stored_path"]) == stored_path


def test_search_mast_filters_products_and_records_metadata(
    store: LocalStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    class DummyObservations:
        criteria: dict[str, Any] | None = None
        products_requested: Any = None

        @classmethod
        def query_criteria(cls, **criteria: Any) -> list[dict[str, Any]]:
            cls.criteria = dict(criteria)
            return [
                {
                    "obsid": "12345",
                    "target_name": "WASP-96 b",
                    "obs_collection": "JWST",
                    "instrument_name": "NIRSpec",
                }
            ]

        @classmethod
        def get_product_list(cls, table: Any) -> list[dict[str, Any]]:
            cls.products_requested = table
            return [
                {
                    "obsid": "12345",
                    "productFilename": "jwst_spec.fits",
                    "dataURI": "mast:JWST/spec.fits",
                    "dataproduct_type": "spectrum",
                    "productType": "SCIENCE",
                    "intentType": "SCIENCE",
                    "calib_level": 3,
                    "units": {"x": "um", "y": "flux"},
                },
                {
                    "obsid": "12345",
                    "productFilename": "jwst_image.fits",
                    "dataURI": "mast:JWST/image.fits",
                    "dataproduct_type": "image",
                    "productType": "SCIENCE",
                    "intentType": "SCIENCE",
                    "calib_level": 3,
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
    assert records[0].identifier == "jwst_spec.fits"
    assert records[0].download_url == "mast:JWST/spec.fits"
    assert records[0].units == {"x": "um", "y": "flux"}
    assert records[0].metadata.get("observation", {}).get("obs_collection") == "JWST"


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
                    "obs_collection": "JWST",
                    "instrument_name": "NIRSpec",
                },
            ]

        @classmethod
        def get_product_list(cls, table: Any) -> list[dict[str, Any]]:
            return [
                {
                    "obsid": "12345",
                    "productFilename": "jwst_spec.fits",
                    "dataURI": "mast:JWST/spec.fits",
                    "dataproduct_type": "spectrum",
                    "productType": "SCIENCE",
                    "intentType": "SCIENCE",
                    "calib_level": 3,
                },
                {
                    "obsid": "12345",
                    "productFilename": "jwst_image.fits",
                    "dataURI": "mast:JWST/image.fits",
                    "dataproduct_type": "image",
                    "productType": "SCIENCE",
                    "intentType": "SCIENCE",
                    "calib_level": 3,
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
    assert identifiers == {"jwst_spec.fits", "jwst_image.fits"}


def test_search_mast_filters_non_science_products(
    store: LocalStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    class DummyObservations:
        @staticmethod
        def query_criteria(**criteria: Any) -> list[dict[str, Any]]:
            return [
                {
                    "obsid": "999",
                    "target_name": "HD 189733",
                    "obs_collection": "JWST",
                    "instrument_name": "NIRISS",
                }
            ]

        @staticmethod
        def get_product_list(table: Any) -> list[dict[str, Any]]:
            return [
                {
                    "obsid": "999",
                    "productFilename": "hd189733_science.fits",
                    "dataURI": "mast:JWST/hd189733_science.fits",
                    "dataproduct_type": "spectrum",
                    "productType": "SCIENCE",
                    "intentType": "SCIENCE",
                    "calib_level": 3,
                },
                {
                    "obsid": "999",
                    "productFilename": "hd189733_calibration.fits",
                    "dataURI": "mast:JWST/hd189733_calibration.fits",
                    "dataproduct_type": "spectrum",
                    "productType": "SCIENCE",
                    "intentType": "CALIBRATION",
                    "calib_level": 3,
                },
                {
                    "obsid": "999",
                    "productFilename": "hd189733_uncal.fits",
                    "dataURI": "mast:JWST/hd189733_uncal.fits",
                    "dataproduct_type": "spectrum",
                    "productType": "SCIENCE",
                    "intentType": "SCIENCE",
                    "calib_level": 1,
                },
            ]

    class DummyMast:
        Observations = DummyObservations

    service = RemoteDataService(store, session=None)
    monkeypatch.setattr(service, "_ensure_mast", lambda: DummyMast)

    records = service.search(
        RemoteDataService.PROVIDER_MAST,
        {"target_name": "HD 189733"},
    )

    assert [record.identifier for record in records] == ["hd189733_science.fits"]


def test_search_exosystems_queries_archive_and_mast(
    store: LocalStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_calls: dict[str, Any] = {}

    class DummyArchive:
        @staticmethod
        def query_criteria(**criteria: Any) -> list[dict[str, Any]]:
            archive_calls.update(criteria)
            return [
                {
                    "pl_name": "WASP-39 b",
                    "hostname": "WASP-39",
                    "ra": 210.1234,
                    "dec": -39.1234,
                    "st_teff": 5400.0,
                    "sy_dist": 217.0,
                    "discoverymethod": "Transit",
                    "disc_year": 2011,
                }
            ]

    class DummyObservations:
        region_calls: list[tuple[Any, dict[str, Any]]] = []
        object_calls: list[tuple[Any, dict[str, Any]]] = []

        @classmethod
        def query_region(cls, coordinates: Any, radius: str) -> list[dict[str, Any]]:
            cls.region_calls.append((coordinates, {"radius": radius}))
            return [
                {
                    "obsid": "444",
                    "target_name": "WASP-39",
                    "obs_collection": "JWST",
                    "instrument_name": "NIRSpec",
                }
            ]

        @classmethod
        def query_object(cls, target_name: str, radius: str) -> list[dict[str, Any]]:
            cls.object_calls.append((target_name, {"radius": radius}))
            return [
                {
                    "obsid": "444",
                    "target_name": target_name,
                    "obs_collection": "JWST",
                    "instrument_name": "NIRSpec",
                }
            ]

        @classmethod
        def get_product_list(cls, table: Any) -> list[dict[str, Any]]:
            return [
                {
                    "obsid": "444",
                    "productFilename": "wasp39b_nirspec.fits",
                    "dataURI": "mast:JWST/wasp39b.fits",
                    "dataproduct_type": "spectrum",
                    "productType": "SCIENCE",
                    "intentType": "SCIENCE",
                    "calib_level": 3,
                }
            ]

    class DummyMast:
        Observations = DummyObservations

    service = RemoteDataService(store, session=None)
    monkeypatch.setattr(service, "_ensure_exoplanet_archive", lambda: DummyArchive)
    monkeypatch.setattr(service, "_has_exoplanet_archive", lambda: True)
    monkeypatch.setattr(service, "_ensure_mast", lambda: DummyMast)
    monkeypatch.setattr(service, "_fetch_exomast_filelist", lambda name: {"files": [name], "citation": "Exo.MAST"})

    records = service.search(RemoteDataService.PROVIDER_EXOSYSTEMS, {"text": "WASP-39 b"})

    assert archive_calls["table"] == "pscomppars"
    assert "WASP-39" in archive_calls["where"]
    assert DummyObservations.region_calls, "Exosystem search should query by coordinates"
    assert not DummyObservations.object_calls, "Coordinate-based search should not fall back to query_object"
    assert len(records) == 1
    record = records[0]
    assert record.provider == RemoteDataService.PROVIDER_EXOSYSTEMS
    assert record.metadata.get("exosystem", {}).get("planet_name") == "WASP-39 b"
    assert any(
        isinstance(citation, dict) and "Exo.MAST" in str(citation.get("title"))
        for citation in record.metadata.get("citations", [])
    )


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
    monkeypatch.setattr(remote_module.nist_asd_service, "dependencies_available", lambda: False)
    monkeypatch.setattr(remote_module, "astroquery_mast", None)
    monkeypatch.setattr(remote_module, "_HAS_PANDAS", False)
    service = RemoteDataService(store, session=None)

    assert service.providers() == []
    unavailable = service.unavailable_providers()
    assert remote_module.RemoteDataService.PROVIDER_NIST in unavailable
    assert remote_module.RemoteDataService.PROVIDER_MAST in unavailable

    # Restoring NIST while keeping MAST dependencies missing yields only NIST.
    monkeypatch.setattr(remote_module.nist_asd_service, "dependencies_available", lambda: True)
    service = RemoteDataService(store, session=None)

    assert service.providers() == [remote_module.RemoteDataService.PROVIDER_NIST]
    unavailable = service.unavailable_providers()
    assert remote_module.RemoteDataService.PROVIDER_MAST in unavailable

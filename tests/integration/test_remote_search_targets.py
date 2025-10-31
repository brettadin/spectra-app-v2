from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.services import LocalStore, RemoteDataService


@pytest.fixture()
def store(tmp_path: Path) -> LocalStore:
    return LocalStore(base_dir=tmp_path)


def test_curated_planets_cover_major_targets(store: LocalStore) -> None:
    service = RemoteDataService(store, session=None)

    planets = service.curated_targets(category="solar_system")
    names = [entry.get("display_name") for entry in planets]

    assert names[:9] == [
        "Mercury",
        "Venus",
        "Earth",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Pluto",
    ]


def test_curated_planets_expose_local_samples(store: LocalStore) -> None:
    service = RemoteDataService(store, session=None)

    planets = service.curated_targets(category="solar_system")
    earth = next(entry for entry in planets if entry.get("display_name") == "Earth")
    samples = service.local_samples(earth)

    assert samples, "Expected curated local samples for Earth"
    assert all(sample.path.exists() for sample in samples)


def test_solar_system_search_filters_science_products(
    store: LocalStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    class DummyObservations:
        object_calls: list[tuple[str, dict[str, Any]]] = []

        @classmethod
        def query_object(cls, target_name: str, radius: str) -> list[dict[str, Any]]:
            cls.object_calls.append((target_name, {"radius": radius}))
            return [
                {
                    "obsid": "321",
                    "target_name": target_name,
                    "obs_collection": "JWST",
                    "instrument_name": "NIRSpec",
                }
            ]

        @staticmethod
        def get_product_list(table: Any) -> list[dict[str, Any]]:
            return [
                {
                    "obsid": "321",
                    "productFilename": "jupiter_science.fits",
                    "dataURI": "mast:JWST/jupiter_science.fits",
                    "dataproduct_type": "spectrum",
                    "productType": "SCIENCE",
                    "intentType": "SCIENCE",
                    "calib_level": 3,
                },
                {
                    "obsid": "321",
                    "productFilename": "jupiter_preview.fits",
                    "dataURI": "mast:JWST/jupiter_preview.fits",
                    "dataproduct_type": "image",
                    "productType": "PREVIEW",
                    "intentType": "ENGINEERING",
                    "calib_level": 1,
                },
            ]

    class DummyMast:
        Observations = DummyObservations

    service = RemoteDataService(store, session=None)
    monkeypatch.setattr(service, "_ensure_mast", lambda: DummyMast)
    monkeypatch.setattr(service, "_has_exoplanet_archive", lambda: False)
    monkeypatch.setattr(service, "_fetch_exomast_filelist", lambda name: None)

    records = service.search(RemoteDataService.PROVIDER_EXOSYSTEMS, {"text": "Jupiter"})

    assert [record.identifier for record in records] == ["jupiter_science.fits"]
    assert DummyObservations.object_calls


def test_host_star_query_uses_archive_metadata(
    store: LocalStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_calls: dict[str, Any] = {}

    class DummyArchive:
        @staticmethod
        def query_criteria(**criteria: Any) -> list[dict[str, Any]]:
            archive_calls.update(criteria)
            return [
                {
                    "pl_name": "HD 189733 b",
                    "hostname": "HD 189733",
                    "ra": 300.1821,
                    "dec": 22.7099,
                    "st_teff": 4980.0,
                    "sy_dist": 19.8,
                    "discoverymethod": "Transit",
                    "disc_year": 2005,
                }
            ]

    class DummyObservations:
        region_calls: list[tuple[str, dict[str, Any]]] = []
        object_calls: list[tuple[str, dict[str, Any]]] = []

        @classmethod
        def query_region(cls, coordinates: str, radius: str) -> list[dict[str, Any]]:
            cls.region_calls.append((coordinates, {"radius": radius}))
            return [
                {
                    "obsid": "654",
                    "target_name": "HD 189733",
                    "obs_collection": "JWST",
                    "instrument_name": "NIRISS",
                }
            ]

        @classmethod
        def query_object(cls, target_name: str, radius: str) -> list[dict[str, Any]]:
            cls.object_calls.append((target_name, {"radius": radius}))
            return [
                {
                    "obsid": "654",
                    "target_name": target_name,
                    "obs_collection": "JWST",
                    "instrument_name": "NIRISS",
                }
            ]

        @staticmethod
        def get_product_list(table: Any) -> list[dict[str, Any]]:
            return [
                {
                    "obsid": "654",
                    "productFilename": "hd189733b_science.fits",
                    "dataURI": "mast:JWST/hd189733b_science.fits",
                    "dataproduct_type": "spectrum",
                    "productType": "SCIENCE",
                    "intentType": "SCIENCE",
                    "calib_level": 3,
                },
                {
                    "obsid": "654",
                    "productFilename": "hd189733b_calibration.fits",
                    "dataURI": "mast:JWST/hd189733b_calibration.fits",
                    "dataproduct_type": "spectrum",
                    "productType": "SCIENCE",
                    "intentType": "CALIBRATION",
                    "calib_level": 3,
                },
            ]

    class DummyMast:
        Observations = DummyObservations

    service = RemoteDataService(store, session=None)
    monkeypatch.setattr(service, "_ensure_exoplanet_archive", lambda: DummyArchive)
    monkeypatch.setattr(service, "_has_exoplanet_archive", lambda: True)
    monkeypatch.setattr(service, "_ensure_mast", lambda: DummyMast)
    monkeypatch.setattr(service, "_fetch_exomast_filelist", lambda name: {"citation": "Exo.MAST"})

    records = service.search(RemoteDataService.PROVIDER_EXOSYSTEMS, {"text": "HD 189733 b"})

    assert [record.identifier for record in records] == ["hd189733b_science.fits"]
    record = records[0]
    assert record.metadata.get("exosystem", {}).get("planet_name") == "HD 189733 b"
    assert any(
        isinstance(citation, dict) and "Exo.MAST" in str(citation.get("notes", ""))
        for citation in record.metadata.get("citations", [])
    )
    assert DummyObservations.region_calls
    assert not DummyObservations.object_calls
    assert "pscomppars" in archive_calls.get("table", "")

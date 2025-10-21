from pathlib import Path

import importlib.util

import numpy as np
import pytest

from app.services import DataIngestService, UnitsService
from app.services.importers import FitsImporter
from app.services.store import LocalStore


def build_ingest_service() -> DataIngestService:
    units = UnitsService()
    return DataIngestService(units)


def test_csv_ingest_samples():
    service = build_ingest_service()
    sample_path = Path("samples/sample_spectrum.csv")
    spectra = service.ingest(sample_path)
    assert len(spectra) == 1
    spectrum = spectra[0]
    ingest_meta = spectrum.metadata["ingest"]
    assert ingest_meta["importer"] == "CsvImporter"
    assert ingest_meta["source_path"].endswith("sample_spectrum.csv")
    assert np.isclose(spectrum.x[0], 400.0)


def test_percent_transmittance_conversion():
    service = build_ingest_service()
    sample_path = Path("samples/sample_transmittance.csv")
    spectra = service.ingest(sample_path)
    spectrum = spectra[0]
    expected = -np.log10(np.array([0.9, 0.8, 0.7, 0.6, 0.5]))
    assert np.allclose(spectrum.y, expected)


def test_fits_ingest_fixture(mini_fits: Path):
    service = build_ingest_service()
    spectra = service.ingest(mini_fits)
    spectrum = spectra[0]
    ingest_meta = spectrum.metadata["ingest"]
    assert ingest_meta["importer"] == "FitsImporter"
    assert ingest_meta["source_path"].endswith("mini.fits")
    assert np.isclose(spectrum.x[0], 500.0)
    assert spectrum.metadata.get("original_flux_unit") == "erg/s/cm2/angstrom"


def test_fits_importer_requires_astropy_when_missing(tmp_path: Path):
    try:
        fits_spec = importlib.util.find_spec("astropy.io.fits")
    except ModuleNotFoundError:  # pragma: no cover - interpreter behaviour
        fits_spec = None

    if fits_spec is not None:
        pytest.skip("astropy installed; runtime guard not triggered")

    importer = FitsImporter()
    with pytest.raises(RuntimeError):
        importer.read(tmp_path / "dummy.fits")


def test_export_bundle_csv_roundtrip(tmp_path: Path):
    service = build_ingest_service()
    bundle_path = tmp_path / "bundle.csv"
    bundle_path.write_text(
        """wavelength_nm,intensity,spectrum_id,spectrum_name,point_index,x_unit,y_unit
400,0.1,first,First lamp,0,nm,absorbance
410,0.2,first,First lamp,1,nm,absorbance
420,0.3,second,Second lamp,0,nm,absorbance
430,0.4,second,Second lamp,1,nm,absorbance
""",
        encoding="utf-8",
    )

    spectra = service.ingest(bundle_path)
    assert len(spectra) == 2
    names = [s.name for s in spectra]
    assert "First lamp" in names
    assert "Second lamp" in names
    for spectrum in spectra:
        assert spectrum.x_unit == "nm"
        assert spectrum.y_unit == "absorbance"
        assert spectrum.metadata.get("ingest", {}).get("bundle_member")


def test_ingest_preserves_remote_metadata(tmp_path: Path):
    class OverwritingStore(LocalStore):
        def record(self, source_path, *, x_unit, y_unit, source=None, manifest_path=None, alias=None):  # type: ignore[override]
            entry = super().record(
                source_path,
                x_unit=x_unit,
                y_unit=y_unit,
                source=source,
                manifest_path=manifest_path,
                alias=alias,
            )
            if source is None or "remote" in source:
                return entry

            index = self.load_index()
            items = index.get("items", {})
            stored = items.get(entry["sha256"], {})
            stored_source = stored.get("source")
            if isinstance(stored_source, dict):
                stored_source.pop("remote", None)
                stored["source"] = stored_source
                items[entry["sha256"]] = stored
                self.save_index(index)
                entry["source"] = stored_source
            return entry

    store = OverwritingStore(base_dir=tmp_path)
    service = DataIngestService(UnitsService(), store=store)

    remote_meta = {
        "uri": "https://example.test/catalogue/file", 
        "provider": "Test Provider",
        "identifier": "sample-entry",
    }
    initial_entry = store.record(
        Path("samples/sample_spectrum.csv"),
        x_unit="nm",
        y_unit="absorbance",
        source={"remote": remote_meta},
        alias="remote_sample.csv",
    )

    spectra = service.ingest(Path(initial_entry["stored_path"]))
    assert spectra, "Ingest should return at least one spectrum"

    entries = store.list_entries()
    updated = entries.get(initial_entry["sha256"])
    assert isinstance(updated, dict)
    source = updated.get("source", {})
    remote = source.get("remote")
    assert isinstance(remote, dict)
    assert remote.get("uri") == remote_meta["uri"]
    assert remote.get("provider") == remote_meta["provider"]
    ingest_meta = source.get("ingest", {})
    assert ingest_meta.get("importer") == "CsvImporter"

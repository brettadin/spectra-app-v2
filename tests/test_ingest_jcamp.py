from pathlib import Path

import numpy as np

from app.services import DataIngestService, UnitsService


def test_jcamp_ingest_fixture():
    service = DataIngestService(UnitsService())
    spectrum = service.ingest(Path("tests/data/mini.dx.jcamp"))

    ingest_meta = spectrum.metadata["ingest"]
    assert ingest_meta["importer"] == "JcampImporter"
    assert ingest_meta["source_path"].endswith("mini.dx.jcamp")

    expected_nm = np.array([1e7 / 4000.0, 1e7 / 3500.0, 1e7 / 3000.0])
    assert np.allclose(spectrum.x, expected_nm)
    assert spectrum.metadata["source_units"] == {"x": "cm^-1", "y": "absorbance"}


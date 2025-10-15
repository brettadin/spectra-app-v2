from __future__ import annotations

from pathlib import Path

import numpy as np

from app.services.importers import CsvImporter


def test_csv_importer_detects_wavenumber_from_preface(tmp_path: Path) -> None:
    raw = """
    Spectrometer Export — Run 18
    Axis description: Wavenumber (cm^-1)
    Signal: Percent Transmittance

    Wavenumber, Sample (%), Notes
    3500, 78.5, baseline
    3400, 79.1, baseline
    3200, 80.2, sample
    3000, 82.0, sample
    """.strip()

    path = tmp_path / "run18.txt"
    path.write_text(raw, encoding="utf-8")

    importer = CsvImporter()
    result = importer.read(path)

    assert result.x_unit == "cm^-1"
    assert result.y_unit == "percent_transmittance"
    assert np.all(np.diff(result.x) > 0)
    assert result.metadata["detected_units"]["x"]["reason"] in {"header", "preface", "value-range"}
    assert result.metadata["detected_units"]["y"]["unit"] == "percent_transmittance"


def test_csv_importer_handles_extra_columns_and_selects_intensity(tmp_path: Path) -> None:
    raw = """
    Sample collected at dawn
    Columns: wavelength (nm)  intensity  noise  temp[K]

    wavelength (nm),Intensity,Noise,Temp [K]
    410,0.12,0.01,298
    420,0.18,0.00,298
    430,0.19,0.02,298
    440,0.22,0.02,298
    450,0.28,0.03,298
    """.strip()

    path = tmp_path / "dawn.csv"
    path.write_text(raw, encoding="utf-8")

    importer = CsvImporter()
    result = importer.read(path)

    assert result.x_unit == "nm"
    assert result.y_unit == "absorbance"
    assert result.x.shape == result.y.shape
    assert result.x[0] == 410
    assert np.isclose(result.y.max(), 0.28)
    units_meta = result.metadata["detected_units"]
    assert units_meta["x"]["unit"] == "nm"
    assert units_meta["y"]["reason"] in {"header", "value-range", "default"}

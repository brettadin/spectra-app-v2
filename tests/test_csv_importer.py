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


def test_csv_importer_prefers_wavelength_column_when_intensity_first(tmp_path: Path) -> None:
    raw = """
    # Free-form report with intensity before wavelength
    0.010, 2100
    0.020, 2085
    0.030, 2050
    0.040, 2000
    0.050, 1900
    0.060, 1800
    """.strip()

    path = tmp_path / "reverse_columns.txt"
    path.write_text(raw, encoding="utf-8")

    importer = CsvImporter()
    result = importer.read(path)

    assert result.x_unit == "cm^-1"
    assert result.y_unit == "absorbance"
    assert result.x[0] == 1800  # descending table flipped to ascending
    assert np.isclose(result.y[0], 0.060)
    assert result.metadata["detected_units"]["x"]["reason"] in {"value-range", "default"}
    column_meta = result.metadata["column_selection"]
    assert column_meta["x_reason"].startswith("score")
    assert column_meta["y_reason"].startswith("score")


def test_csv_importer_honours_unit_only_headers(tmp_path: Path) -> None:
    raw = """
    Value [cm^-1],Absorbance (a.u.)
    1800,0.10
    1700,0.15
    1600,0.21
    1500,0.26
    1400,0.33
    """.strip()

    path = tmp_path / "unit_only_headers.csv"
    path.write_text(raw, encoding="utf-8")

    importer = CsvImporter()
    result = importer.read(path)

    assert result.x_unit == "cm^-1"
    assert result.y_unit == "absorbance"
    column_meta = result.metadata["column_selection"]
    assert column_meta["x_reason"].startswith("header-unit")
    assert column_meta["y_reason"].startswith("header-unit")


def test_csv_importer_swaps_axes_when_headers_conflict(tmp_path: Path) -> None:
    class ForcedSwapImporter(CsvImporter):
        def _select_x_column(self, data, headers):  # type: ignore[override]
            # Simulate a misclassification so the conflict resolver can swap.
            return 0, "forced"

    raw = """
    Intensity (a.u.),Axis [nm]
    0.52,400
    0.48,410
    0.44,420
    0.40,430
    0.36,440
    """.strip()

    path = tmp_path / "header_swap.csv"
    path.write_text(raw, encoding="utf-8")

    importer = ForcedSwapImporter()
    result = importer.read(path)

    assert np.allclose(result.x, np.array([400, 410, 420, 430, 440]))
    assert np.allclose(result.y, np.array([0.52, 0.48, 0.44, 0.40, 0.36]))
    column_meta = result.metadata["column_selection"]
    assert column_meta["swap"] == "header-swap"
    assert column_meta["original"] == {"x_index": 0, "y_index": 1}
    assert column_meta["x_reason"].endswith("header-swap")
    assert column_meta["y_reason"].endswith("header-swap")


def test_csv_importer_profile_swap_for_monotonic_intensity(tmp_path: Path) -> None:
    class ProfileSwapImporter(CsvImporter):
        def _select_x_column(self, data, headers):  # type: ignore[override]
            return 0, "score"

        def _select_y_column(self, data, x_index, headers):  # type: ignore[override]
            return 1, "score"

    raw = """
    # Intensity column is monotonic; wavelength column jitters and would be mis-scored without profile swap
    0.05, 5000
    0.07, 4992
    0.09, 5001
    0.12, 4988
    0.15, 4995
    0.18, 4989
    """.strip()

    path = tmp_path / "profile_swap.txt"
    path.write_text(raw, encoding="utf-8")

    importer = ProfileSwapImporter()
    result = importer.read(path)

    expected_wavenumbers = np.array([5000, 4992, 5001, 4988, 4995, 4989], dtype=float)
    assert result.x_unit in {"cm^-1", "cm⁻¹"}
    assert np.allclose(np.sort(result.x), np.sort(expected_wavenumbers))
    column_meta = result.metadata["column_selection"]
    assert column_meta["swap"] == "profile-swap"
    assert column_meta["x_reason"].endswith("profile-swap")
    assert column_meta["y_reason"].endswith("profile-swap")
    assert np.isclose(result.y.max(), 0.18)

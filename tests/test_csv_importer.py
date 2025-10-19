from __future__ import annotations

from pathlib import Path

import numpy as np

from app.services.importers import CsvImporter
from app.services.importers.csv_importer import _LAYOUT_CACHE, _reset_layout_cache


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


def test_csv_importer_scores_monotonic_wavelength_over_noisy_intensity(
    tmp_path: Path,
) -> None:
    _reset_layout_cache()
    raw = """
    250.0, 400
    -300.0, 405
    275.0, 410
    -320.0, 415
    290.0, 420
    -280.0, 425
    """.strip()

    path = tmp_path / "noisy_trace.csv"
    path.write_text(raw, encoding="utf-8")

    importer = CsvImporter()
    result = importer.read(path)

    column_meta = result.metadata["column_selection"]
    assert column_meta["x_index"] == 1
    assert column_meta["x_reason"].startswith("score")
    assert np.all(np.diff(result.x) > 0)
    assert not _LAYOUT_CACHE


def test_csv_importer_ignores_invalid_cached_layout(tmp_path: Path) -> None:
    _reset_layout_cache()
    header = "Value,Value2"
    first = "\n".join(
        [
            header,
            "100,0.1",
            "200,0.5",
            "300,0.9",
            "400,0.4",
        ]
    )
    second = "\n".join(
        [
            header,
            "0.5,120",
            "0.2,140",
            "0.8,160",
            "0.1,180",
        ]
    )

    first_path = tmp_path / "first.csv"
    second_path = tmp_path / "second.csv"
    first_path.write_text(first, encoding="utf-8")
    second_path.write_text(second, encoding="utf-8")

    importer = CsvImporter()
    first_result = importer.read(first_path)

    assert first_result.metadata["column_selection"]["layout_cache"] == "miss"
    signature = tuple(first_result.metadata["column_selection"]["layout_signature"])
    assert _LAYOUT_CACHE[signature] == (0, 1)

    second_result = importer.read(second_path)
    column_meta = second_result.metadata["column_selection"]

    assert column_meta["layout_cache"] == "miss"
    assert column_meta["x_index"] == 1
    assert column_meta["y_index"] == 0
    assert not column_meta["x_reason"].startswith("layout-cache")
    assert _LAYOUT_CACHE[signature] == (1, 0)


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


def test_csv_importer_reuses_layout_cache_for_repeat_headers(tmp_path: Path) -> None:
    _reset_layout_cache()

    header = "Channel A, Channel B\n"
    file_one = header + "400,0.10\n410,0.12\n420,0.11\n430,0.15\n"
    file_two = header + "450,0.08\n460,0.09\n470,0.11\n480,0.14\n"

    path_one = tmp_path / "instrument_a.csv"
    path_two = tmp_path / "instrument_b.csv"
    path_one.write_text(file_one, encoding="utf-8")
    path_two.write_text(file_two, encoding="utf-8")

    importer = CsvImporter()
    first = importer.read(path_one)
    assert first.metadata["column_selection"]["layout_cache"] == "miss"

    class CacheProbeImporter(CsvImporter):
        def _select_x_column(self, data, headers):  # type: ignore[override]
            raise AssertionError("layout cache not applied")

        def _select_y_column(self, data, x_index, headers):  # type: ignore[override]
            raise AssertionError("layout cache not applied")

    probe = CacheProbeImporter()
    second = probe.read(path_two)

    column_meta = second.metadata["column_selection"]
    assert column_meta["layout_cache"] == "hit"
    assert column_meta["x_index"] == first.metadata["column_selection"]["x_index"]
    assert column_meta["y_index"] == first.metadata["column_selection"]["y_index"]


def test_csv_importer_validates_layout_cache_against_data(tmp_path: Path) -> None:
    _reset_layout_cache()

    header = "Wavelength (nm),Intensity (a.u.)\n"
    file_one = header + "400,0.10\n410,0.12\n420,0.11\n430,0.15\n"
    file_two = header + "0.02,400\n0.03,410\n0.05,420\n0.04,430\n"

    path_one = tmp_path / "aligned.csv"
    path_two = tmp_path / "swapped.csv"
    path_one.write_text(file_one, encoding="utf-8")
    path_two.write_text(file_two, encoding="utf-8")

    importer = CsvImporter()
    first = importer.read(path_one)
    assert first.metadata["column_selection"]["layout_cache"] == "miss"

    second = importer.read(path_two)

    column_meta = second.metadata["column_selection"]
    assert column_meta["layout_cache"] == "miss"
    assert np.allclose(second.x, np.array([400.0, 410.0, 420.0, 430.0]))


def test_export_bundle_detection(tmp_path: Path) -> None:
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

    importer = CsvImporter()
    result = importer.read(bundle_path)

    bundle = result.metadata.get("bundle")
    assert isinstance(bundle, dict)
    assert bundle.get("format") == "spectra-export-v1"
    members = bundle.get("members") if isinstance(bundle, dict) else None
    assert isinstance(members, list)
    assert len(members) == 2
    assert np.isclose(result.x[0], 400.0)


def test_wide_bundle_detection(tmp_path: Path) -> None:
    wide_path = tmp_path / "wide.csv"
    wide_path.write_text(
        """# spectra-wide-v1
# member {"id": "first", "name": "First lamp", "x_unit": "nm", "y_unit": "absorbance"}
# member {"id": "second", "name": "Second lamp", "x_unit": "nm", "y_unit": "absorbance"}
wavelength_nm::first,intensity::first,wavelength_nm::second,intensity::second
400,0.1,420,0.3
410,0.2,430,0.4
""",
        encoding="utf-8",
    )

    importer = CsvImporter()
    result = importer.read(wide_path)

    bundle = result.metadata.get("bundle")
    assert isinstance(bundle, dict)
    members = bundle.get("members") if isinstance(bundle, dict) else None
    assert isinstance(members, list)
    assert len(members) == 2
    assert {member["id"] for member in members} == {"first", "second"}

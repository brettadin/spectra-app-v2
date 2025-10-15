"""Regression tests for provenance export bundles."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app.services.provenance_service import ProvenanceService
from app.services.spectrum import Spectrum


def build_spectrum(tmp_path: Path | None = None) -> Spectrum:
    wavelengths = np.array([500.0, 600.0, 700.0])
    flux = np.array([0.1, 0.2, 0.3])
    source_path = None
    if tmp_path is not None:
        source_path = tmp_path / "mini_source.csv"
        source_path.write_text("raw_flux\n", encoding="utf-8")
    return Spectrum.create("mini", wavelengths, flux, source_path=source_path)


def test_export_bundle_writes_manifest_csv_and_png(tmp_path: Path):
    service = ProvenanceService(app_version="0.2-test")
    spectrum = build_spectrum(tmp_path)
    manifest_path = tmp_path / "bundle" / "manifest.json"

    png_bytes = b"\x89PNG\r\n"
    export = service.export_bundle(
        [spectrum],
        manifest_path,
        png_writer=lambda path: path.write_bytes(png_bytes),
    )

    assert export["manifest_path"] == manifest_path
    manifest_data = export["manifest"]
    assert manifest_data["app"]["version"] == "0.2-test"
    assert manifest_data["sources"][0]["name"] == "mini"

    csv_text = export["csv_path"].read_text(encoding="utf-8")
    assert "wavelength_nm" in csv_text
    assert "0.1" in csv_text

    png_path = export["png_path"]
    assert png_path.read_bytes() == png_bytes

    log_path = export["log_path"]
    log_text = log_path.read_text(encoding="utf-8")
    assert "Export started" in log_text
    assert "Manifest saved" in log_text

    spectra_dir = export["spectra_dir"]
    assert spectra_dir and spectra_dir.is_dir()
    per_csv_files = list(spectra_dir.glob("*.csv"))
    assert len(per_csv_files) == 1
    per_csv_text = per_csv_files[0].read_text(encoding="utf-8")
    assert "wavelength_nm" in per_csv_text
    assert "0.2" in per_csv_text

    manifest_entry = manifest_data["sources"][0]
    canonical_csv_rel = Path(manifest_entry["canonical_csv"])
    assert (manifest_path.parent / canonical_csv_rel).read_text(encoding="utf-8") == per_csv_text

    sources_dir = export["sources_dir"]
    assert sources_dir and sources_dir.is_dir()
    copied_sources = list(sources_dir.iterdir())
    assert len(copied_sources) == 1
    assert copied_sources[0].read_text(encoding="utf-8") == "raw_flux\n"
    exported_copy_rel = Path(manifest_entry["exported_copy"])
    assert (manifest_path.parent / exported_copy_rel).read_text(encoding="utf-8") == "raw_flux\n"

    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded["sources"][0]["id"] == manifest_data["sources"][0]["id"]

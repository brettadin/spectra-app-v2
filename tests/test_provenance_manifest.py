"""Regression tests for provenance export bundles."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app.services.provenance_service import ProvenanceService
from app.services.spectrum import Spectrum


def build_spectrum() -> Spectrum:
    wavelengths = np.array([500.0, 600.0, 700.0])
    flux = np.array([0.1, 0.2, 0.3])
    return Spectrum.create("mini", wavelengths, flux)


def test_export_bundle_writes_manifest_csv_and_png(tmp_path: Path):
    service = ProvenanceService(app_version="0.2-test")
    spectrum = build_spectrum()
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

    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded["sources"][0]["id"] == manifest_data["sources"][0]["id"]

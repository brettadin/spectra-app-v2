from __future__ import annotations
import math

import re

from app.services.reference_library import ReferenceLibrary


def test_reference_library_hydrogen_and_ir_catalogues() -> None:
    library = ReferenceLibrary()

    balmer_lines = library.spectral_lines(series="Balmer")
    identifiers = {entry["id"] for entry in balmer_lines}
    assert {"H_Balmer_alpha", "H_Balmer_beta", "H_Balmer_gamma"}.issubset(identifiers)

    meta = library.hydrogen_metadata()
    source_id = meta["source_id"]
    assert source_id.startswith("nist_asd_2024")
    assert "Rydberg" in meta.get("notes", "")
    provenance = meta.get("provenance", {})
    assert provenance.get("generator") == "tools/reference_build/build_hydrogen_asd.py"

    all_lines = library.spectral_lines()
    assert all_lines, "expected bundled hydrogen lines"

    def version_tag(identifier: str) -> str:
        match = re.search(r"(\d{4}.*)$", identifier)
        if match:
            return match.group(1)
        if "_" in identifier:
            return identifier.split("_", 1)[-1]
        return identifier

    meta_tag = version_tag(source_id)
    line_tags = {version_tag(line.get("source_id", "")) for line in all_lines}
    assert line_tags == {meta_tag}, "hydrogen lines must share the ASD version tag"

    ir_groups = library.ir_functional_groups()
    group_names = {entry["group"] for entry in ir_groups}
    assert "C=O (ketone/aldehyde)" in group_names
    ir_meta = library.ir_metadata()
    assert ir_meta.get("provenance", {}).get("generator") == "tools/reference_build/build_ir_bands.py"

    placeholders = library.line_shape_placeholders()
    placeholder_ids = {entry["id"] for entry in placeholders}
    assert "doppler_shift" in placeholder_ids


def test_reference_library_jwst_target_metadata() -> None:
    library = ReferenceLibrary()

    targets = library.jwst_targets()
    ids = {target["id"] for target in targets}
    assert "jwst_jupiter_nirspec_ifu_g140h_f100lp" in ids

    for target in targets:
        data = target["data"]
        assert data, "expected resampled data rows"
        wavelengths = [row["wavelength_um"] for row in data]
        values = [row["value"] for row in data]
        assert wavelengths == sorted(wavelengths), "wavelength grid should be monotonic"
        assert all(math.isfinite(w) for w in wavelengths)
        assert all(math.isfinite(v) for v in values)
        prov = target.get("provenance", {})
        assert "mast_product_uri" in prov
        assert "retrieved_utc" in prov
        assert prov.get("pipeline_version")
        assert "digitized_release_graphic" not in prov

    bibliography = library.bibliography()
    citations = {entry["citation"] for entry in bibliography}
    assert any("NIST" in citation for citation in citations)

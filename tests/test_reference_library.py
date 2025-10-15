from __future__ import annotations
from app.services.reference_library import ReferenceLibrary


def test_reference_library_hydrogen_and_ir_catalogues() -> None:
    library = ReferenceLibrary()

    balmer_lines = library.spectral_lines(series="Balmer")
    identifiers = {entry["id"] for entry in balmer_lines}
    assert {"H_Balmer_alpha", "H_Balmer_beta", "H_Balmer_gamma"}.issubset(identifiers)

    meta = library.hydrogen_metadata()
    assert meta["source_id"] == "nist_asd_2024"
    assert "Rydberg" in meta.get("notes", "")

    ir_groups = library.ir_functional_groups()
    group_names = {entry["group"] for entry in ir_groups}
    assert "C=O (ketone/aldehyde)" in group_names

    placeholders = library.line_shape_placeholders()
    placeholder_ids = {entry["id"] for entry in placeholders}
    assert "doppler_shift" in placeholder_ids


def test_reference_library_jwst_target_metadata() -> None:
    library = ReferenceLibrary()

    targets = library.jwst_targets()
    ids = {target["id"] for target in targets}
    assert "jwst_wasp96b_nirspec_prism" in ids

    wasp96 = library.jwst_target("jwst_wasp96b_nirspec_prism")
    assert wasp96 is not None
    assert wasp96["spectral_range_um"][0] < wasp96["spectral_range_um"][1]
    assert len(wasp96["data"]) >= 3
    assert wasp96["data"][0]["value"] > 0

    bibliography = library.bibliography()
    citations = {entry["citation"] for entry in bibliography}
    assert any("NIST" in citation for citation in citations)

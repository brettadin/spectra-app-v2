import numpy as np

from app.services import OverlayService, Spectrum


def make_spectrum(name: str, base: float) -> Spectrum:
    return Spectrum.create(
        name=name,
        wavelength_nm=np.array([base, base + 1]),
        flux=np.array([0.1, 0.2]),
    )


def test_add_and_prevent_duplicates():
    service = OverlayService()
    spec = make_spectrum("A", 500.0)
    service.add(spec)
    service.add(spec)
    assert len(service.spectra()) == 1


def test_reorder():
    service = OverlayService()
    spec_a = make_spectrum("A", 500)
    spec_b = make_spectrum("B", 600)
    service.add(spec_a)
    service.add(spec_b)
    service.order([spec_b.id, spec_a.id])
    names = [s.name for s in service.spectra()]
    assert names == ["B", "A"]

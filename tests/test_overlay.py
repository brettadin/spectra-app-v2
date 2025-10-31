import numpy as np

from app.services import OverlayService, Spectrum, UnitsService


def make_spectrum(name: str, base: float) -> Spectrum:
    return Spectrum.create(
        name,
        np.array([base, base + 1]),
        np.array([0.1, 0.2]),
        x_unit="nm",
        y_unit="absorbance",
    )


def test_add_and_prevent_duplicates():
    service = OverlayService(UnitsService())
    spec = make_spectrum("A", 500.0)
    service.add(spec)
    service.add(spec)
    assert len(service.list()) == 1


def test_remove_and_clear():
    service = OverlayService(UnitsService())
    spec_a = make_spectrum("A", 500)
    spec_b = make_spectrum("B", 600)
    service.add(spec_a)
    service.add(spec_b)
    service.remove(spec_a.id)
    names = [s.name for s in service.list()]
    assert names == ["B"]
    service.clear()
    assert service.list() == []

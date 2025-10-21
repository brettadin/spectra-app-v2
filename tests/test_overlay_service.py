import numpy as np

from app.services import OverlayService, UnitsService, Spectrum


def test_overlay_applies_max_normalization() -> None:
    units = UnitsService()
    overlay = OverlayService(units)
    spectrum = Spectrum.create(
        name="demo",
        x=np.linspace(100.0, 200.0, 5),
        y=np.array([0.2, 0.4, 0.8, 0.6, 0.1], dtype=float),
    )
    overlay.add(spectrum)

    views = overlay.overlay([spectrum.id], "nm", "absorbance", normalization="Max")
    view = views[0]

    assert np.isclose(view["y_canonical"].max(), 1.0)
    norm_meta = view["metadata"]["normalization"]
    assert norm_meta["mode"] == "max"
    assert norm_meta["applied"] is True
    assert np.isclose(norm_meta["scale"], 0.8)


def test_overlay_area_normalization_targets_unit_area() -> None:
    units = UnitsService()
    overlay = OverlayService(units)
    x = np.linspace(400.0, 420.0, 5)
    y = np.array([0.0, 1.0, 2.0, 1.0, 0.0], dtype=float)
    spectrum = Spectrum.create(name="area", x=x, y=y)
    overlay.add(spectrum)

    view = overlay.overlay([spectrum.id], "nm", "absorbance", normalization="Area")[0]
    area = np.trapezoid(np.abs(view["y_canonical"]), view["x_canonical"])

    assert np.isclose(area, 1.0)
    norm_meta = view["metadata"]["normalization"]
    assert norm_meta["mode"] == "area"
    assert norm_meta["applied"] is True
    assert norm_meta["scale"] > 0
    assert norm_meta["basis"] == "abs-trapezoid"

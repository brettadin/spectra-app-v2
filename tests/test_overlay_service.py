from typing import Any, Dict, cast

import numpy as np

from app.services import OverlayService, UnitsService, Spectrum


def test_overlay_applies_max_normalization() -> None:
    units = UnitsService()
    overlay = OverlayService(units)
    spectrum = Spectrum.create(
        name="demo",
        x=np.linspace(100.0, 200.0, 5),
        y=np.array([0.2, 0.4, 0.8, 0.6, 0.1], dtype=float),
        x_unit="nm",
        y_unit="absorbance",
    )
    overlay.add(spectrum)

    views = overlay.overlay([spectrum.id], "nm", "absorbance", normalization="Max")
    view = views[0]

    y_canonical = np.asarray(view["y_canonical"], dtype=float)
    metadata = cast(Dict[str, Any], view["metadata"])
    norm_meta = cast(Dict[str, Any], metadata["normalization"])
    assert np.isclose(y_canonical.max(), 1.0)
    assert norm_meta["mode"] == "max"
    assert norm_meta["applied"] is True
    assert np.isclose(float(norm_meta["scale"]), 0.8)


def test_overlay_area_normalization_targets_unit_area() -> None:
    units = UnitsService()
    overlay = OverlayService(units)
    x = np.linspace(400.0, 420.0, 5)
    y = np.array([0.0, 1.0, 2.0, 1.0, 0.0], dtype=float)
    spectrum = Spectrum.create(name="area", x=x, y=y, x_unit="nm", y_unit="absorbance")
    overlay.add(spectrum)

    view = overlay.overlay([spectrum.id], "nm", "absorbance", normalization="Area")[0]
    metadata = cast(Dict[str, Any], view["metadata"])
    norm_meta = cast(Dict[str, Any], metadata["normalization"])
    y_canonical = np.asarray(view["y_canonical"], dtype=float)
    x_canonical = np.asarray(view["x_canonical"], dtype=float)
    area = np.trapezoid(np.abs(y_canonical), x_canonical)

    assert np.isclose(area, 1.0)
    assert norm_meta["mode"] == "area"
    assert norm_meta["applied"] is True
    assert norm_meta["scale"] > 0
    assert norm_meta["basis"] == "abs-trapz"

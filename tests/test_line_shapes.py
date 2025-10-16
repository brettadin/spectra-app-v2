from __future__ import annotations

import numpy as np
import pytest

from app.services.line_shapes import LineShapeModel
from app.services.reference_library import ReferenceLibrary


@pytest.fixture(scope="module")
def line_shape_model() -> LineShapeModel:
    library = ReferenceLibrary()
    return LineShapeModel(library.line_shape_placeholders(), library.line_shape_metadata())


def test_doppler_shift_relativistic_factor(line_shape_model: LineShapeModel) -> None:
    params = line_shape_model.example_parameters("doppler_shift")
    rest = float(params.get("rest_wavelength_nm", 656.281))
    beta = float(params.get("radial_velocity_kms", 0.0)) / 299_792.458
    x = np.linspace(rest - 1.0, rest + 1.0, 51)
    y = np.ones_like(x)

    outcome = line_shape_model.apply("doppler_shift", x, y, params)
    factor = np.sqrt((1.0 + beta) / (1.0 - beta))

    assert np.allclose(outcome.x, x * factor)
    assert outcome.metadata["doppler_factor"] == pytest.approx(factor)
    assert outcome.metadata["beta"] == pytest.approx(beta)
    assert outcome.metadata["observed_wavelength_nm"] == pytest.approx(rest * factor)


def test_pressure_broadening_kernel_normalisation(line_shape_model: LineShapeModel) -> None:
    params = line_shape_model.example_parameters("pressure_broadening")
    centre = float(params.get("line_centre_nm", 486.133))
    x = np.linspace(centre - 1.0, centre + 1.0, 801)
    y = np.exp(-0.5 * ((x - centre) / 0.04) ** 2)

    outcome = line_shape_model.apply("pressure_broadening", x, y, params)

    assert outcome.metadata["kernel_sum"] == pytest.approx(1.0, rel=1e-6)
    assert outcome.metadata["width_nm"] > 0
    assert outcome.y.max() < y.max()


def test_stark_broadening_wings_gain_weight(line_shape_model: LineShapeModel) -> None:
    params = line_shape_model.example_parameters("stark_broadening")
    centre = float(params.get("line_centre_nm", 486.133))
    x = np.linspace(centre - 2.0, centre + 2.0, 1201)
    y = np.exp(-0.5 * ((x - centre) / 0.05) ** 2)

    outcome = line_shape_model.apply("stark_broadening", x, y, params)
    wings = np.abs(x - centre) > 0.4

    assert outcome.metadata["stark_width_nm"] > 0
    assert outcome.metadata["kernel_sum"] == pytest.approx(1.0, rel=1e-6)
    assert outcome.y[wings].sum() > y[wings].sum()

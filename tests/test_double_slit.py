# Copyright 2026 Capstone MCP contributors.
"""Independent aperture quadrature validates double-slit geometry inference."""

import cmath
import math
import random
from unittest.mock import Mock

import pytest

from capstone_mcp.numerics import diffraction
from capstone_mcp.numerics.diffraction import fit_double_slit
from capstone_mcp.recipes.slit_diffraction import SlitDiffractionRecipe


def aperture_scan(  # noqa: PLR0913, PLR0917
    width: float,
    separation: float,
    wavelength: float,
    distance: float,
    center: float = 0.000137,
    sample_shift: float = 0.0,
) -> tuple[list[float], list[float]]:
    # Integrate the two physical rectangular apertures. This does not use the
    # production sinc/cos model or its optimizer to generate expected values.
    extent = 1.35 * wavelength * distance / width
    positions = [center + sample_shift + extent * i / 240 for i in range(-240, 241)]
    aperture = [
        sign * separation / 2 + width * ((j + 0.5) / 64 - 0.5)
        for sign in (-1, 1)
        for j in range(64)
    ]
    intensities = []
    for position in positions:
        sine = (position - center) / math.hypot(distance, position - center)
        field = sum(
            cmath.exp(2j * math.pi * coordinate * sine / wavelength)
            for coordinate in aperture
        ) / len(aperture)
        intensities.append(0.2 + 3.0 * abs(field) ** 2)
    return positions, intensities


@pytest.mark.parametrize(
    ("width", "separation", "wavelength", "distance"),
    [
        (4e-5, 2.5e-4, 650e-9, 1.0),
        (8e-5, 2e-4, 532e-9, 0.75),
        (3e-5, 3e-4, 450e-9, 1.4),
    ],
)
def test_geometry_matches_independent_aperture_integral(
    width: float,
    separation: float,
    wavelength: float,
    distance: float,
) -> None:
    x, y = aperture_scan(width, separation, wavelength, distance)
    fit = fit_double_slit(x, y, wavelength, distance)
    assert fit.width_m == pytest.approx(width, rel=0.003)
    assert fit.separation_m == pytest.approx(separation, rel=0.001)
    assert fit.center_m == pytest.approx(0.000137, abs=1e-6)
    assert fit.background == pytest.approx(0.2, abs=0.002)
    assert fit.amplitude == pytest.approx(3, rel=0.002)


def test_recipe_returns_both_geometry_values_with_metre_and_mm_inputs() -> None:
    x, y = aperture_scan(4e-5, 2.5e-4, 650e-9, 1)
    recipe = SlitDiffractionRecipe()
    for positions in (
        {"positions_m": x},
        {"positions_mm": [value * 1000 for value in x]},
    ):
        result = recipe.analyze(
            {**positions, "intensities": y, "slit_type": "double_slit"},
        )
        assert result.status == "completed", result.message
        assert result.details["derived_slit_width_mm"] == pytest.approx(0.04, rel=0.003)
        assert result.details["derived_slit_separation_mm"] == pytest.approx(
            0.25, rel=0.001,
        )


def test_small_detector_noise_is_tolerated() -> None:
    x, y = aperture_scan(4e-5, 2.5e-4, 650e-9, 1)
    rng = random.Random(12)  # noqa: S311 - deterministic measurement noise
    noisy = [value + rng.uniform(-0.001, 0.001) for value in y]
    fit = fit_double_slit(x, noisy, 650e-9, 1)
    assert fit.width_m == pytest.approx(4e-5, rel=0.01)
    assert fit.separation_m == pytest.approx(2.5e-4, rel=0.01)


def test_unobserved_envelope_is_not_assigned_a_width() -> None:
    x = [i * 1e-5 for i in range(-200, 201)]
    y = [math.cos(math.pi * value / 0.001) ** 2 for value in x]
    with pytest.raises(ValueError, match="envelope"):
        fit_double_slit(x, y, 650e-9, 1)


def test_undersampled_fringes_and_flat_signal_are_rejected() -> None:
    x, y = aperture_scan(4e-5, 2.5e-4, 650e-9, 1)
    with pytest.raises(ValueError, match="undersampled"):
        fit_double_slit(x[::10], y[::10], 650e-9, 1)
    with pytest.raises(ValueError, match="fringes"):
        fit_double_slit(x, [1.0] * len(x), 650e-9, 1)


def test_invalid_geometry_parameters_fail_before_fitting() -> None:
    x, y = aperture_scan(4e-5, 2.5e-4, 650e-9, 1)
    with pytest.raises(ValueError, match="positive"):
        fit_double_slit(x, y, 0, 1)
    with pytest.raises(ValueError, match="finite"):
        fit_double_slit(x, y, 650e-9, math.inf)


def test_non_double_slit_structure_is_rejected_by_residual() -> None:
    x, y = aperture_scan(4e-5, 2.5e-4, 650e-9, 1)
    distorted = [value + 0.8 * math.sin(990 * position)**2 for position, value in zip(x, y, strict=True)]
    with pytest.raises(ValueError, match=r"model|envelope"):
        fit_double_slit(x, distorted, 650e-9, 1)


def test_recipe_does_not_replace_zero_wavelength_with_default() -> None:
    x, y = aperture_scan(4e-5, 2.5e-4, 650e-9, 1)
    result = SlitDiffractionRecipe().analyze({
        "positions_m": x, "intensities": y, "slit_type": "double_slit",
        "wavelength_m": 0,
    })
    assert result.status == "failed"
    assert "positive" in result.message


def test_peak_between_samples_is_fitted_without_assuming_sample_center() -> None:
    x, y = aperture_scan(4e-5, 2.5e-4, 650e-9, 1, sample_shift=0.00003)
    fit = fit_double_slit(x, y, 650e-9, 1)
    assert fit.center_m == pytest.approx(0.000137, abs=1e-6)
    assert fit.width_m == pytest.approx(4e-5, rel=0.003)
    assert fit.separation_m == pytest.approx(2.5e-4, rel=0.001)


@pytest.mark.parametrize(("wavelength", "distance"), [(1e308, 1e308), (5e-324, 5e-324)])
def test_unrepresentable_geometry_fails_as_domain_value_error(wavelength: float, distance: float) -> None:
    x, y = aperture_scan(4e-5, 2.5e-4, 650e-9, 1)
    with pytest.raises(ValueError):  # noqa: PT011 - verify no arithmetic exception escapes
        fit_double_slit(x, y, wavelength, distance)


def test_maximum_input_uses_bounded_search_with_full_resolution_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    x = [-0.022 + 0.044 * index / 19999 for index in range(20000)]
    y = []
    for position in x:
        sine = position / math.hypot(1, position)
        beta = math.pi * 4e-5 * sine / 650e-9
        y.append((math.sin(beta) / beta if beta else 1)**2 * math.cos(math.pi * 2.5e-4 * sine / 650e-9)**2)
    tracked = Mock(wraps=diffraction._refine)
    monkeypatch.setattr(diffraction, "_refine", tracked)
    fit = fit_double_slit(x, y, 650e-9, 1)
    assert fit.width_m == pytest.approx(4e-5, rel=0.003)
    assert max(len(call.args[0]) for call in tracked.call_args_list) <= 2048

# Copyright 2026 Capstone MCP contributors.
"""Regression scaling and chart validity without GUI dependencies."""

import math

import pytest
from defusedxml.ElementTree import fromstring

from capstone_mcp.numerics import (
    fit_polynomial_series,
    render_ascii_sparkline,
    render_svg_sparkline,
)


def test_svg_title_is_xml_text_not_markup() -> None:
    title = "x < y & </text><script>alert(1)</script>"
    root = fromstring(render_svg_sparkline([0, 1], [0, 1], title=title))
    assert root.find("{http://www.w3.org/2000/svg}script") is None
    assert root.find("{http://www.w3.org/2000/svg}text").text == title


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf")])
def test_plot_coordinates_reject_nonfinite_values(invalid: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        render_ascii_sparkline([0, 1], [0, invalid])
    with pytest.raises(ValueError, match="finite"):
        render_svg_sparkline([0, 1], [0, invalid])
    with pytest.raises(ValueError, match="finite"):
        render_svg_sparkline([0, 1], [0, 1], fit_x=[0, 1], fit_y=[invalid, 1])


@pytest.mark.parametrize("scale", [1e-100, 1e-9, 1.0, 1e100])
def test_polynomial_normalization_preserves_original_units(scale: float) -> None:
    x = [value * scale for value in (-2, -1, 0, 1, 2)]
    y = [4, 1, 0, 1, 4]
    result = fit_polynomial_series(x, y, degree=2)
    assert result.coefficients[2] == pytest.approx(1 / scale**2)
    assert result.r_squared == pytest.approx(1)
    predicted = [sum(c * value**i for i, c in enumerate(result.coefficients)) for value in x]
    assert predicted == pytest.approx(y, abs=1e-12)


def test_polynomial_translation_and_y_scaling_backtransform() -> None:
    x = [1000.0 + index for index in range(7)]
    y = [1e200 * (2 + 3 * (value - 1000) + 4 * (value - 1000)**2) for value in x]
    fit = fit_polynomial_series(x, y, degree=2)
    assert [value / 1e200 for value in fit.coefficients] == pytest.approx([3997002, -7997, 4])
    assert fit.r_squared == pytest.approx(1)


def test_polynomial_singular_design_fails_explicitly() -> None:
    with pytest.raises(ValueError, match="Singular"):
        fit_polynomial_series([0, 0, 1, 1], [0, 0, 1, 1], degree=2)


def test_unrepresentable_original_polynomial_coefficients_fail() -> None:
    with pytest.raises(ValueError, match="floating-point range"):
        fit_polynomial_series([0, 1e-200, 2e-200], [0, 1, 4], degree=2)


def test_extreme_plot_span_fails_before_rendering_invalid_coordinates() -> None:
    with pytest.raises(ValueError, match="span"):
        render_svg_sparkline([-1e308, 1e308], [0, 1])
    with pytest.raises(ValueError, match="span"):
        render_ascii_sparkline([-1e308, 1e308], [0, 1])


def test_constant_polynomial_y_is_representable() -> None:
    result = fit_polynomial_series([0, 1, 2], [0, 0, 0])
    assert result.coefficients == [0, 0, 0]
    assert all(math.isfinite(value) for value in result.coefficients)


def test_polynomial_rejects_unstable_original_basis_despite_perfect_normalized_fit() -> None:
    x = [1e12 + index for index in range(7)]
    y = [float(index**2) for index in range(7)]
    with pytest.raises(ValueError, match=r"Original-basis.*unstable"):
        fit_polynomial_series(x, y, degree=2)

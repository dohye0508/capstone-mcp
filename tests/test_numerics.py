# Copyright 2026 Capstone MCP contributors.
"""Tests for the Deep Numerics Engine (statistics, regressions, and sparklines)."""

import math

import pytest

from capstone_mcp.numerics import (
    compute_series_summary,
    fit_linear_series,
    fit_polynomial_series,
    render_ascii_sparkline,
    render_svg_sparkline,
)
from capstone_mcp.numerics.sparklines import (
    MAX_SVG_POINTS,
    plot_bounds,
    sampled_svg_points,
)


def test_compute_series_summary_valid() -> None:
    """Ensure accurate statistics for standard numeric series."""
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    summary = compute_series_summary(values)

    assert summary.count == 5
    assert math.isclose(summary.mean, 3.0)
    assert math.isclose(summary.min_val, 1.0)
    assert math.isclose(summary.max_val, 5.0)
    assert math.isclose(summary.peak_val, 5.0)
    assert summary.std_dev > 0.0


def test_compute_series_summary_empty_raises() -> None:
    """Ensure empty series raises ValueError."""
    with pytest.raises(ValueError, match="empty"):
        compute_series_summary([])


def test_summary_keeps_finite_values_and_small_variation() -> None:
    summary = compute_series_summary([
        float("nan"), 1e12 + 1, float("inf"), 1e12 + 2, 1e12 + 3, float("-inf"),
    ])

    assert summary.count == 3
    assert summary.mean == 1e12 + 2
    assert summary.std_dev == pytest.approx(1.0)
    assert summary.min_val == 1e12 + 1
    assert summary.max_val == 1e12 + 3


def test_fit_linear_series_exact() -> None:
    """Verify exact linear fit for y = 2x + 1."""
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [1.0, 3.0, 5.0, 7.0, 9.0]
    result = fit_linear_series(x, y)

    assert math.isclose(result.slope, 2.0, abs_tol=1e-7)
    assert math.isclose(result.intercept, 1.0, abs_tol=1e-7)
    assert math.isclose(result.r_squared, 1.0, abs_tol=1e-7)
    assert len(result.residuals) == 5
    for r in result.residuals:
        assert math.isclose(r, 0.0, abs_tol=1e-7)


def test_fit_linear_series_insufficient_points() -> None:
    """Ensure series with fewer than 2 points raises ValueError."""
    with pytest.raises(ValueError, match="at least 2 points"):
        fit_linear_series([1.0], [2.0])


def test_fit_linear_series_length_mismatch() -> None:
    """Ensure mismatched x and y lengths raise ValueError."""
    with pytest.raises(ValueError, match="Mismatched lengths"):
        fit_linear_series([1.0, 2.0], [3.0])


def test_fit_linear_series_zero_variance_x() -> None:
    """Ensure vertical data (zero x variance) raises ValueError."""
    with pytest.raises(ValueError, match="zero variance"):
        fit_linear_series([2.0, 2.0, 2.0], [1.0, 2.0, 3.0])


def test_fit_polynomial_series_quadratic() -> None:
    """Verify polynomial fit for y = x^2."""
    x = [-2.0, -1.0, 0.0, 1.0, 2.0]
    y = [4.0, 1.0, 0.0, 1.0, 4.0]
    result = fit_polynomial_series(x, y, degree=2)

    assert result.degree == 2
    assert math.isclose(result.r_squared, 1.0, abs_tol=1e-5)
    assert math.isclose(result.coefficients[2], 1.0, abs_tol=1e-4)


def test_render_ascii_sparkline() -> None:
    """Verify ASCII chart rendering outputs non-empty grid with title."""
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [10.0, 20.0, 35.0, 25.0, 50.0]
    chart = render_ascii_sparkline(x, y, width=30, height=8, title="Test Plot")

    assert "Test Plot" in chart
    assert len(chart.splitlines()) >= 8


def test_render_svg_sparkline() -> None:
    """Verify SVG rendering outputs valid SVG markup with viewBox and paths."""
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [1.0, 3.0, 5.0, 7.0, 9.0]
    svg = render_svg_sparkline(x, y, fit_x=x, fit_y=y, title="Linear SVG")

    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "Linear SVG" in svg
    assert "circle" in svg
    assert "path" in svg


@pytest.mark.parametrize("scale", [1.0, 1e-9, 1e-20, 1e20, 1e-200, 1e200])
def test_linear_regression_respects_input_units(scale: float) -> None:
    result = fit_linear_series([400 * scale, 500 * scale, 600 * scale], [3.0, 5.0, 7.0])
    assert result.slope * scale == pytest.approx(0.02)
    assert result.intercept == pytest.approx(-5.0)
    assert result.r_squared == pytest.approx(1.0)

@pytest.mark.parametrize("infinite", [float("inf"), -float("inf")])
def test_linear_regression_does_not_silently_drop_infinity(infinite: float) -> None:
    with pytest.raises(ValueError, match="finite measurements"):
        fit_linear_series([1.0, 2.0, 3.0], [2.0, infinite, 6.0])

@pytest.mark.parametrize("scale", [1e-200, 1e200])
def test_linear_regression_scales_both_axes_without_overflow(scale: float) -> None:
    result = fit_linear_series([scale, 2 * scale, 3 * scale], [2 * scale, 4 * scale, 6 * scale])
    assert result.slope == pytest.approx(2.0)
    assert result.intercept / scale == pytest.approx(0.0, abs=1e-14)
    assert result.r_squared == pytest.approx(1.0)


def test_linear_regression_unrepresentable_result_fails() -> None:
    with pytest.raises(ValueError, match="floating-point range"):
        fit_linear_series([1e-300, 2e-300], [1e300, 2e300])
def test_svg_sparkline_bounds_scatter_and_fit_and_preserves_title() -> None:
    values = list(range(3_000))
    svg = render_svg_sparkline(
        values, values, fit_x=values, fit_y=values, title="Force & <Motion>",
    )

    assert 0 < svg.count("<circle ") <= 1_000
    assert 0 < svg.count(" L ") < 1_000
    assert 'cx="nan"' not in svg
    assert "Force &amp; &lt;Motion&gt;" in svg
    assert ">2999.00<" in svg


@pytest.mark.parametrize("count", [MAX_SVG_POINTS + 1, 5_000])
def test_svg_sampling_preserves_a_narrow_peak_and_endpoints(count: int) -> None:
    x = list(range(count))
    y = [0.0] * count
    y[503] = 100.0
    bounds = plot_bounds(x, y)
    assert bounds is not None

    sampled = list(sampled_svg_points(x, y, bounds))

    assert len(sampled) == MAX_SVG_POINTS
    assert sampled[0] == (0, 0)
    assert sampled[-1] == (count - 1, 0)
    assert (503, 100) in sampled
    assert [px for px, _ in sampled] == sorted({px for px, _ in sampled})

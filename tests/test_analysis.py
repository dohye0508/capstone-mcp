# Copyright 2026 Capstone MCP contributors.
"""Deterministic numerical checks for analysis of measured samples."""

import math

import pytest
from pydantic import ValidationError

from capstone_mcp.analysis import (
    AnalysisError,
    FitInput,
    RunSamples,
    compare_runs,
    linear_fit,
)


def test_fit_recovers_exact_line() -> None:
    # Given
    samples = FitInput(x=[0, 1, 2, 3], y=[3, 5, 7, 9])
    # When
    result = linear_fit(samples)
    # Then
    assert result.slope == 2
    assert result.intercept == 3
    assert result.slope_standard_error == 0
    assert result.r_squared == 1


def test_fit_reports_residual_based_standard_error() -> None:
    # Given: centered x, and a residual orthogonal to x and the constant vector.
    samples = FitInput(x=[-1, 0, 1], y=[0, -2, 2])
    # When
    result = linear_fit(samples)
    # Then
    assert result.slope == 1
    assert result.intercept == 0
    assert result.slope_standard_error == pytest.approx(math.sqrt(3))
    assert result.intercept_standard_error == pytest.approx(math.sqrt(2))
    assert result.r_squared == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("x", "y"),
    [([1, 1, 1], [1, 2, 3]), ([1, 2, 3], [1, 2, 3, 4])],
)
def test_fit_rejects_unusable_pairing(x: list[float], y: list[float]) -> None:
    # Given
    samples = FitInput(x=x, y=y)
    # When / Then
    with pytest.raises(AnalysisError):
        _ = linear_fit(samples)


def test_input_rejects_nonfinite_samples() -> None:
    # Given / When / Then
    with pytest.raises(ValidationError):
        _ = FitInput(x=[0, 1, 2], y=[1, float("nan"), 3])


def test_constant_y_has_no_defined_r_squared() -> None:
    # Given
    samples = FitInput(x=[0, 1, 2], y=[4, 4, 4])
    # When
    result = linear_fit(samples)
    # Then
    assert result.slope == 0
    assert result.intercept == 4
    assert result.r_squared is None


def test_run_comparison_keeps_unequal_sample_counts() -> None:
    # Given
    runs = [
        RunSamples(name="first", values=[1, 2, 3]),
        RunSamples(name="second", values=[5]),
    ]
    # When
    results = compare_runs(runs)
    # Then
    assert results[0].sample_standard_deviation == 1
    assert results[1].sample_standard_deviation is None
    assert results[1].mean_difference_from_first == 3
    assert [result.count for result in results] == [3, 1]

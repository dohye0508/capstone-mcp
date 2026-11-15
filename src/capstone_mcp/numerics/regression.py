# Copyright 2026 Capstone MCP contributors.
"""Linear and polynomial regression analysis with residual diagnostics."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

MIN_LINEAR_POINTS: Final[int] = 2


@dataclass(frozen=True)
class LinearRegressionResult:
    """Results from an Ordinary Least Squares (OLS) linear fit: y = m*x + b."""

    slope: float
    intercept: float
    r_squared: float
    std_err_slope: float
    std_err_intercept: float
    residuals: list[float]


@dataclass(frozen=True)
class PolynomialRegressionResult:
    """Results from a polynomial fit: y = c0 + c1*x + c2*x^2 + ..."""

    coefficients: list[float]
    r_squared: float
    degree: int


def _rescale_ratio(value: float, numerator: float, denominator: float) -> float:
    """Apply a scale ratio without overflowing an intermediate quotient."""
    value_m, value_e = math.frexp(value)
    num_m, num_e = math.frexp(numerator)
    den_m, den_e = math.frexp(denominator)
    try:
        return math.ldexp(value_m * num_m / den_m, value_e + num_e - den_e)
    except OverflowError as exc:
        msg = "Regression result exceeds the finite floating-point range."
        raise ValueError(msg) from exc


def fit_linear_series(
    x: Sequence[float],
    y: Sequence[float],
) -> LinearRegressionResult:
    """Perform OLS linear regression on two series: y = m*x + b.

    Args:
        x: Independent variable series.
        y: Dependent variable series.

    Returns:
        LinearRegressionResult with slope, intercept, R^2, errors, and residuals.

    Raises:
        ValueError: If series have mismatched lengths or fewer than 2 points.
    """
    if len(x) != len(y):
        msg = f"Mismatched lengths: len(x)={len(x)} vs len(y)={len(y)}"
        raise ValueError(msg)

    if any(math.isinf(v) for v in (*x, *y)):
        msg = "Regression requires finite measurements; infinity is not supported."
        raise ValueError(msg)

    pairs = [
        (float(xi), float(yi))
        for xi, yi in zip(x, y, strict=True)
        if not (math.isnan(xi) or math.isnan(yi))
    ]
    n = len(pairs)
    if n < MIN_LINEAR_POINTS:
        msg = f"Need at least {MIN_LINEAR_POINTS} points for linear regression, got {n}"
        raise ValueError(msg)

    clean_x = [p[0] for p in pairs]
    clean_y = [p[1] for p in pairs]

    # Normalize before centering and squaring: units must not decide whether
    # nonconstant data has variance, or overflow otherwise finite input.
    x_scale = max(abs(v) for v in clean_x) or 1.0
    y_scale = max(abs(v) for v in clean_y) or 1.0
    scaled_x = [v / x_scale for v in clean_x]
    scaled_y = [v / y_scale for v in clean_y]
    mean_x = math.fsum(scaled_x) / n
    mean_y = math.fsum(scaled_y) / n
    dx = [v - mean_x for v in scaled_x]
    dy = [v - mean_y for v in scaled_y]
    ss_xx = math.fsum(v * v for v in dx)
    if ss_xx == 0.0:
        msg = "Independent variable x has zero variance (cannot fit vertical line)"
        raise ValueError(msg)
    ss_yy = math.fsum(v * v for v in dy)
    ss_xy = math.fsum(a * b for a, b in zip(dx, dy, strict=True))
    scaled_slope = ss_xy / ss_xx
    slope = _rescale_ratio(scaled_slope, y_scale, x_scale)
    intercept = (mean_y - scaled_slope * mean_x) * y_scale
    scaled_residuals = [
        b - scaled_slope * a for a, b in zip(dx, dy, strict=True)
    ]
    residuals = [r * y_scale for r in scaled_residuals]
    ss_res = math.fsum(r * r for r in scaled_residuals)
    r_squared = max(0.0, min(1.0, 1.0 - ss_res / ss_yy)) if ss_yy else 1.0
    mse = ss_res / max(n - 2, 1)
    std_err_slope = _rescale_ratio(math.sqrt(mse / ss_xx), y_scale, x_scale)
    std_err_intercept = math.sqrt(mse * (1.0 / n + mean_x**2 / ss_xx)) * y_scale
    if not all(
        math.isfinite(v)
        for v in (slope, intercept, std_err_slope, std_err_intercept, *residuals)
    ):
        msg = "Regression result exceeds the finite floating-point range."
        raise ValueError(msg)

    return LinearRegressionResult(
        slope=slope,
        intercept=intercept,
        r_squared=r_squared,
        std_err_slope=std_err_slope,
        std_err_intercept=std_err_intercept,
        residuals=residuals,
    )


def fit_polynomial_series(  # noqa: C901
    x: Sequence[float],
    y: Sequence[float],
    degree: int = 2,
) -> PolynomialRegressionResult:
    """Fit a polynomial of given degree using Gaussian elimination on normal equations.

    Args:
        x: Independent variable series.
        y: Dependent variable series.
        degree: Degree of polynomial (e.g. 2 for quadratic).

    Returns:
        PolynomialRegressionResult with ascending coefficients [c0, c1, c2, ...].

    Raises:
        ValueError: If invalid degree or insufficient points.
    """
    if degree < 1:
        msg = f"Polynomial degree must be >= 1, got {degree}"
        raise ValueError(msg)

    pairs = [
        (float(xi), float(yi))
        for xi, yi in zip(x, y, strict=True)
        if not (math.isnan(xi) or math.isnan(yi))
    ]
    n = len(pairs)
    if n <= degree:
        msg = f"Need at least {degree + 1} points for degree {degree} fit, got {n}"
        raise ValueError(msg)

    # Build Normal equations: (X^T * X) * C = X^T * Y
    m = degree + 1
    matrix = [[0.0] * m for _ in range(m)]
    rhs = [0.0] * m

    for xi, yi in pairs:
        powers = [xi**p for p in range(2 * degree + 1)]
        for i in range(m):
            rhs[i] += yi * powers[i]
            for j in range(m):
                matrix[i][j] += powers[i + j]

    # Gaussian elimination with partial pivoting
    for i in range(m):
        max_row = max(range(i, m), key=lambda r: abs(matrix[r][i]))
        matrix[i], matrix[max_row] = matrix[max_row], matrix[i]
        rhs[i], rhs[max_row] = rhs[max_row], rhs[i]

        pivot = matrix[i][i]
        if math.isclose(pivot, 0.0, abs_tol=1e-12):
            msg = "Singular matrix in polynomial normal equations"
            raise ValueError(msg)

        for r in range(i + 1, m):
            factor = matrix[r][i] / pivot
            for c in range(i, m):
                matrix[r][c] -= factor * matrix[i][c]
            rhs[r] -= factor * rhs[i]

    # Back substitution
    coeffs = [0.0] * m
    for i in range(m - 1, -1, -1):
        s = sum(matrix[i][j] * coeffs[j] for j in range(i + 1, m))
        coeffs[i] = (rhs[i] - s) / matrix[i][i]

    clean_y = [p[1] for p in pairs]
    mean_y = sum(clean_y) / n
    ss_yy = sum((yi - mean_y) ** 2 for yi in clean_y)
    ss_res = sum(
        (yi - sum(coeffs[p] * (xi**p) for p in range(m))) ** 2 for xi, yi in pairs
    )
    r_squared = max(0.0, min(1.0, 1.0 - (ss_res / ss_yy))) if ss_yy > 0.0 else 1.0

    return PolynomialRegressionResult(
        coefficients=coeffs,
        r_squared=r_squared,
        degree=degree,
    )

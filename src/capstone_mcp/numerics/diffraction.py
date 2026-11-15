# Copyright 2026 Capstone MCP contributors.
"""Resolved equal-width double-slit Fraunhofer profile inference.

Fit I = background + amplitude*sinc(pi*a*sin(theta)/lambda)^2
                            *cos(pi*d*sin(theta)/lambda)^2.
The detector coordinate uses sin(theta)=dx/hypot(L, dx). Slit width a
and center separation d are separate parameters; interference zeros are
never interpreted as diffraction-envelope zeros.
"""

import math
from dataclasses import dataclass
from itertools import pairwise

MIN_SAMPLES = 41
MAX_SAMPLES = 20_000
MAX_FIT_SAMPLES = 2048
MIN_SAMPLES_PER_FRINGE = 8
MAX_NORMALIZED_RMS = 0.03
MIN_ENVELOPE_EXTENT = 1.05
PARAMETER_TOLERANCE = 1e-7


@dataclass(frozen=True)
class DoubleSlitFit:
    """Measured geometry and fit diagnostics, with all lengths in metres."""

    width_m: float
    separation_m: float
    center_m: float
    amplitude: float
    background: float
    normalized_rms: float


def _profile(
    positions: list[float],
    geometry: tuple[float, float, float],
    distance: float,
) -> list[float]:
    ratio, period, center = geometry
    values = []
    for position in positions:
        delta = position - center
        fringe = (delta / period) * (distance / math.hypot(distance, delta))
        if not math.isfinite(fringe) or abs(fringe) > 1 / math.ulp(1.0):
            msg = "Double-slit phase exceeds reliable floating-point resolution."
            raise ValueError(msg)
        beta = math.pi * ratio * fringe
        envelope = math.sin(beta) / beta if beta else 1.0
        values.append((envelope * math.cos(math.pi * fringe)) ** 2)
    return values


def _linear_intensity(
    shape: list[float], values: list[float],
) -> tuple[float, float, float]:
    mean_shape = math.fsum(shape) / len(shape)
    mean_value = math.fsum(values) / len(values)
    variance = math.fsum((value - mean_shape) ** 2 for value in shape)
    if variance == 0:
        return math.inf, 0.0, 0.0
    amplitude = (
        math.fsum(
            (a - mean_shape) * (b - mean_value)
            for a, b in zip(shape, values, strict=True)
        )
        / variance
    )
    background = mean_value - amplitude * mean_shape
    error = math.fsum(
        (amplitude * a + background - b) ** 2
        for a, b in zip(shape, values, strict=True)
    ) / len(shape)
    return error if amplitude > 0 else math.inf, amplitude, background


def _refine(
    positions: list[float],
    values: list[float],
    distance: float,
    initial: tuple[float, float, float],
    resolution: float,
) -> tuple[float, tuple[float, float, float]]:
    """Bounded multiscale coordinate search; amplitude/offset are solved exactly."""
    ratio, period, center = initial
    point = [ratio, period, center]
    steps = [0.12, period * 0.08, resolution]
    bounds = [
        (0.02, 0.98),
        (period * 0.65, period * 1.35),
        (center - 2 * resolution, center + 2 * resolution),
    ]
    best = _linear_intensity(_profile(positions, initial, distance), values)[0]
    for _ in range(160):
        improved = False
        for axis in range(3):
            for direction in (-1, 1):
                candidate = point.copy()
                candidate[axis] += direction * steps[axis]
                if not bounds[axis][0] < candidate[axis] < bounds[axis][1]:
                    continue
                geometry = (candidate[0], candidate[1], candidate[2])
                error = _linear_intensity(
                    _profile(positions, geometry, distance), values,
                )[0]
                if error < best:
                    point, best, improved = candidate, error, True
        if not improved:
            steps = [step / 2 for step in steps]
            if steps[0] < PARAMETER_TOLERANCE:
                break
    return best, (point[0], point[1], point[2])


def fit_double_slit(  # noqa: C901, PLR0915, PLR0912
    positions_m: list[float],
    intensities: list[float],
    wavelength_m: float,
    screen_distance_m: float,
) -> DoubleSlitFit:
    """Infer equal-width slit geometry only from resolved, bilateral envelope data.

    Supports width/separation ratios strictly between 0.02 and 0.98.
    Requires at least eight samples per fringe and both first envelope zeros
    within the scan. Accepts a constant detector background. Fits with RMS
    residual above 3% of modulation amplitude fail rather than report geometry.
    """
    if not MIN_SAMPLES <= len(positions_m) <= MAX_SAMPLES or len(positions_m) != len(
        intensities,
    ):
        msg = "Double-slit envelope fitting needs 41 to 20000 matching samples."
        raise ValueError(msg)
    if not all(
        math.isfinite(v)
        for v in (*positions_m, *intensities, wavelength_m, screen_distance_m)
    ):
        msg = "Double-slit inputs must be finite."
        raise ValueError(msg)
    if wavelength_m <= 0 or screen_distance_m <= 0:
        msg = "Wavelength and screen distance must be positive."
        raise ValueError(msg)
    spacings = [b - a for a, b in pairwise(positions_m)]
    if (min(spacings) <= 0 or not all(math.isfinite(v) for v in spacings)
            or not math.isfinite(positions_m[-1] - positions_m[0])):
        msg = "Double-slit positions must be strictly increasing."
        raise ValueError(msg)
    scale = max(abs(value) for value in intensities)
    if scale == 0:
        msg = "Double-slit intensity has no observable modulation."
        raise ValueError(msg)
    values = [value / scale for value in intensities]
    peak = max(range(len(values)), key=values.__getitem__)
    center = positions_m[peak]
    minima = [
        i
        for i in range(1, len(values) - 1)
        if values[i] < values[i - 1] and values[i] <= values[i + 1]
    ]
    left, right = [i for i in minima if i < peak], [i for i in minima if i > peak]
    if not left or not right:
        msg = "Double-slit envelope requires resolved fringes on both sides."
        raise ValueError(msg)
    period = positions_m[right[0]] - positions_m[left[-1]]
    resolution = max(spacings)
    if period < MIN_SAMPLES_PER_FRINGE * resolution:
        msg = "Interference fringes are undersampled; need eight samples per fringe."
        raise ValueError(msg)
    indices = [
        round(index * (len(values) - 1) / (MAX_FIT_SAMPLES - 1))
        for index in range(MAX_FIT_SAMPLES)
    ] if len(values) > MAX_FIT_SAMPLES else list(range(len(values)))
    fit_positions = [positions_m[index] for index in indices]
    fit_values = [values[index] for index in indices]
    if max(b - a for a, b in pairwise(fit_positions)) * MIN_SAMPLES_PER_FRINGE > period:
        msg = (
            "Scan is too wide for bounded fringe fitting; "
            "supply a resolved central region."
        )
        raise ValueError(msg)
    fits = [
        _refine(
            fit_positions, fit_values, screen_distance_m,
            (ratio, period, center), resolution,
        )
        for ratio in (0.06, 0.15, 0.3, 0.5, 0.75, 0.9)
    ]
    _, geometry = min(fits, key=lambda item: item[0])
    ratio, period, center = geometry
    if period < MIN_SAMPLES_PER_FRINGE * resolution:
        msg = "Fitted interference fringes are undersampled."
        raise ValueError(msg)
    error, amplitude, background = _linear_intensity(
        _profile(positions_m, geometry, screen_distance_m),
        values,
    )
    if not math.isfinite(error) or amplitude <= 0:
        msg = "No identifiable double-slit fit."
        raise ValueError(msg)
    rms = math.sqrt(error) / amplitude
    extent = min(center - positions_m[0], positions_m[-1] - center)
    envelope_order = (
        ratio
        * (extent / period)
        * (screen_distance_m / math.hypot(screen_distance_m, extent))
    )
    if envelope_order < MIN_ENVELOPE_EXTENT:
        msg = (
            "Scan must include both first diffraction-envelope zeros "
            "to identify slit width."
        )
        raise ValueError(msg)
    if rms > MAX_NORMALIZED_RMS or background < -MAX_NORMALIZED_RMS * amplitude:
        msg = "Data do not resolve the equal-width double-slit model within 3% RMS."
        raise ValueError(msg)
    separation = wavelength_m * (screen_distance_m / period)
    result = DoubleSlitFit(
        ratio * separation,
        separation,
        center,
        amplitude * scale,
        background * scale,
        rms,
    )
    if (
        not all(
            math.isfinite(v)
            for v in (
                result.width_m,
                result.separation_m,
                result.amplitude,
                result.background,
            )
        )
        or result.width_m <= 0
    ):
        msg = "Double-slit geometry exceeds numeric range."
        raise ValueError(msg)
    return result

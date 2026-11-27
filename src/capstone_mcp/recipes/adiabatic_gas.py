# Copyright 2026 Capstone MCP contributors.
"""Adiabatic Gas Law and Heat Engine Cycle experiment automation recipe."""

import math
from itertools import pairwise
from typing import Any, Final

from capstone_mcp.desktop import Capstone
from capstone_mcp.recipes.base import ExperimentRecipe, RecipePhaseResult

DEFAULT_SAMPLING_RATE_HZ: Final[float] = 1000.0  # 1000 Hz high-speed sampling
GAMMA_AIR_THEORY: Final[float] = 1.400  # Theoretical diatomic gas gamma (7/5)
MIN_CYCLE_POINTS: Final[int] = 3
MIN_ANALYSIS_POINTS: Final[int] = 4


def _pressure_volume_work(
    pressure_kpa: list[float],
    volume_cm3: list[float],
    *, closed: object,
) -> dict[str, float]:
    """Integrate P dV along consecutive observations in acquisition order."""
    if not isinstance(closed, bool):
        msg = "closed_cycle must be a boolean."
        raise TypeError(msg)
    work = math.fsum(
        (p0 * 0.5 + p1 * 0.5) * (v1 - v0)
        for (p0, v0), (p1, v1) in pairwise(zip(pressure_kpa, volume_cm3, strict=True))
    )
    result = {"path_work_mj": work, "path_work_joules": work * 1e-3}
    if closed:
        mean_pressure = pressure_kpa[-1] * 0.5 + pressure_kpa[0] * 0.5
        cycle = work + mean_pressure * (volume_cm3[0] - volume_cm3[-1])
        result.update(cyclic_work_mj=cycle, cyclic_work_joules=cycle * 1e-3)
    if not all(math.isfinite(value) for value in result.values()):
        msg = "Pressure-volume work exceeds finite numerical range."
        raise ValueError(msg)
    return result


def _fit_adiabatic_index(
    pressures: list[float],
    volumes: list[float],
) -> tuple[float, float, float]:
    """Fit ln(P) = -gamma * ln(V) + ln(C) over compression points.

    Returns:
        tuple of (gamma_exp, r_squared, gamma_error_pct).
    """
    if not all(math.isfinite(v) and v > 0 for v in (*pressures, *volumes)):
        msg = "Adiabatic fitting requires finite positive pressure and volume."
        raise ValueError(msg)
    valid_pairs = list(zip(pressures, volumes, strict=True))
    if len(valid_pairs) < MIN_CYCLE_POINTS:
        msg = "Adiabatic fitting requires at least three measured pairs."
        raise ValueError(msg)
    compression_pairs = [
        valid_pairs[i]
        for i in range(len(valid_pairs) - 1)
        if valid_pairs[i + 1][1] < valid_pairs[i][1]
        and valid_pairs[i + 1][0] > valid_pairs[i][0]
    ]

    if len(compression_pairs) < MIN_CYCLE_POINTS:
        compression_pairs = valid_pairs

    ln_v = [math.log(v) for _, v in compression_pairs]
    ln_p = [math.log(p) for p, _ in compression_pairs]

    if len(set(ln_v)) < 2:  # noqa: PLR2004
        msg = "Adiabatic fitting requires positive data at distinct volumes."
        raise ValueError(msg)

    n = len(ln_v)
    mean_x = math.fsum(ln_v) / n
    mean_y = math.fsum(ln_p) / n

    dx = [x - mean_x for x in ln_v]
    dy = [y - mean_y for y in ln_p]

    sxx = math.fsum(x * x for x in dx)
    sxy = math.fsum(x * y for x, y in zip(dx, dy, strict=True))
    syy = math.fsum(y * y for y in dy)

    if sxx > 0:
        slope = sxy / sxx
        gamma_exp = -slope
        r_squared = (sxy * sxy) / (sxx * syy) if syy > 0 else 0.0
    else:
        msg = "Adiabatic fitting requires nonconstant volume measurements."
        raise ValueError(msg)

    err_diff = abs(gamma_exp - GAMMA_AIR_THEORY)
    gamma_error_pct = (err_diff / GAMMA_AIR_THEORY) * 100.0
    return gamma_exp, r_squared, gamma_error_pct


class AdiabaticGasRecipe(ExperimentRecipe):
    """Macro recipe executing 1000Hz sampling & cyclic work area integration."""

    experiment_id = "adiabatic_gas"
    title = "Adiabatic Gas Law & Heat Engine Cycle (단열 기체 및 열기관)"
    description = (
        "1000Hz sampling, P-V cycle area integration (oint P dV), and "
        "adiabatic index gamma (PV^gamma = const) curve fitting."
    )

    def setup(
        self,
        parameters: dict[str, Any] | None = None,
        app: Capstone | None = None,
    ) -> RecipePhaseResult:
        """Report that automatic hardware configuration is not implemented."""
        del parameters, app
        return RecipePhaseResult(
            phase="setup",
            status="failed",
            message="Automatic hardware setup is not implemented. Configure the "
            "experiment manually and provide recorded data for analysis.",
        )

    def acquire(
        self,
        parameters: dict[str, Any] | None = None,
        app: Capstone | None = None,
    ) -> RecipePhaseResult:
        """Acquire 1000Hz pressure and volume datasets during thermodynamic cycle."""
        del app
        params = parameters or {}

        if "pressure_kpa" in params and "volume_cm3" in params:
            p_data = [float(p) for p in params["pressure_kpa"]]
            v_data = [float(v) for v in params["volume_cm3"]]
        else:
            return RecipePhaseResult(
                phase="acquire",
                status="failed",
                message="Live acquisition is not implemented. Provide recorded "
                "measurement arrays; synthetic data is not generated.",
            )

        if (
            not p_data
            or len(p_data) != len(v_data)
            or not all(math.isfinite(v) for v in (*p_data, *v_data))
        ):
            return RecipePhaseResult(
                phase="acquire",
                status="failed",
                message="Provide nonempty, matching, finite measurement arrays.",
            )

        details: dict[str, Any] = {
            "data": {
                "pressure_kpa": p_data,
                "volume_cm3": v_data,
            },
            "sample_count": len(p_data),
            "p_max_kpa": max(p_data) if p_data else 0.0,
            "p_min_kpa": min(p_data) if p_data else 0.0,
            "v_max_cm3": max(v_data) if v_data else 0.0,
            "v_min_cm3": min(v_data) if v_data else 0.0,
        }

        return RecipePhaseResult(
            phase="acquire",
            status="completed",
            message=f"Accepted caller-provided {len(p_data)} P-V samples.",
            details=details,
        )

    def analyze(
        self,
        parameters: dict[str, Any] | None = None,
    ) -> RecipePhaseResult:
        """Calculate cyclic work oint P dV and fit adiabatic index gamma."""
        params = parameters or {}
        data = params.get("data", {})

        p_raw = params.get("pressure_kpa") or data.get("pressure_kpa")
        v_raw = params.get("volume_cm3") or data.get("volume_cm3")

        if not p_raw or not v_raw:
            return RecipePhaseResult(
                phase="analyze",
                status="failed",
                message="Missing pressure or volume data for adiabatic gas analysis.",
                details={},
            )

        pressures = [float(p) for p in p_raw]
        volumes = [float(v) for v in v_raw]

        if len(pressures) != len(volumes):
            return RecipePhaseResult(
                phase="analyze",
                status="failed",
                message="Pressure and volume array lengths do not match.",
                details={"p_count": len(pressures), "v_count": len(volumes)},
            )

        if len(pressures) < MIN_ANALYSIS_POINTS:
            return RecipePhaseResult(
                phase="analyze",
                status="failed",
                message="At least 4 data points required for cycle area integration.",
                details={"points_count": len(pressures)},
            )

        same_endpoint = (pressures[0], volumes[0]) == (pressures[-1], volumes[-1])
        closed = params.get("closed_cycle", same_endpoint)
        # 2. Adiabatic Index Gamma Fit: ln(P) = -gamma * ln(V) + ln(C)
        try:
            gamma_exp, r_squared, gamma_error_pct = _fit_adiabatic_index(
                pressures,
                volumes,
            )
            work = _pressure_volume_work(pressures, volumes, closed=closed)
        except (OverflowError, TypeError, ValueError) as exc:
            return RecipePhaseResult(
                phase="analyze",
                status="failed",
                message=str(exc),
            )

        p_max = max(pressures)
        p_min = min(pressures)
        v_max = max(volumes)
        v_min = min(volumes)
        compression_ratio = v_max / v_min if v_min > 0 else 1.0

        details: dict[str, Any] = {
            **work,
            "adiabatic_index_gamma_exp": round(gamma_exp, 4),
            "adiabatic_index_gamma_theory": GAMMA_AIR_THEORY,
            "gamma_error_pct": round(gamma_error_pct, 2),
            "r_squared": round(r_squared, 4),
            "p_max_kpa": round(p_max, 2),
            "p_min_kpa": round(p_min, 2),
            "v_max_cm3": round(v_max, 2),
            "v_min_cm3": round(v_min, 2),
            "compression_ratio": round(compression_ratio, 2),
            "cycle_points_count": len(pressures),
        }

        msg = (
            f"Measured path work P dV = {work['path_work_joules']:.4f} J, "
            f"gamma = {gamma_exp:.3f} (Theory: {GAMMA_AIR_THEORY:.3f}, "
            f"Error: {gamma_error_pct:.2f}%, R^2 = {r_squared:.4f}), "
            f"Compression ratio = {compression_ratio:.1f}:1"
        )

        return RecipePhaseResult(
            phase="analyze",
            status="completed",
            message=msg,
            details=details,
        )

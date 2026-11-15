# Copyright 2026 Capstone MCP contributors.
"""Photoelectric Effect experiment automation recipe."""

import math
from typing import Any, Final

from capstone_mcp.desktop import Capstone
from capstone_mcp.recipes.base import ExperimentRecipe, RecipePhaseResult

SPEED_OF_LIGHT: Final[float] = 299792458.0  # m/s
ELEMENTARY_CHARGE: Final[float] = 1.602176634e-19  # C
PLANCK_CONSTANT_ACCEPTED: Final[float] = 6.62607015e-34  # J*s
HE_ACCEPTED: Final[float] = (
    PLANCK_CONSTANT_ACCEPTED / ELEMENTARY_CHARGE  # V*s (~4.1357e-15)
)

MIN_REGRESSION_POINTS: Final[int] = 3

CANONICAL_WAVELENGTHS_NM: Final[list[float]] = [
    365.0,  # Mercury ultraviolet line
    405.0,  # Mercury violet line
    436.0,  # Mercury blue line
    546.0,  # Mercury green line
    577.0,  # Mercury yellow-orange line
]

DEFAULT_STOPPING_VOLTAGES_V: Final[list[float]] = [
    1.448,  # 365 nm
    1.112,  # 405 nm
    0.895,  # 436 nm
    0.325,  # 546 nm
    0.203,  # 577 nm
]


class PhotoelectricEffectRecipe(ExperimentRecipe):
    """Macro recipe orchestrating Photoelectric Effect measurement and h/e fit."""

    experiment_id = "photoelectric_effect"
    title = "Photoelectric Effect (광전 효과)"
    description = (
        "Wavelength sweep (365, 405, 436, 546, 577 nm), DC amplifier Ch A / "
        "DC power supply Ch B, Keep Sample stopping potential acquisition, "
        "and h/e linear regression fit."
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
        """Sample stopping potential at each mercury emission line."""
        del app
        params = parameters or {}
        wavelengths: list[float] = [
            float(w) for w in params.get("wavelengths_nm", CANONICAL_WAVELENGTHS_NM)
        ]

        # Use caller-provided stopping voltages if available
        if "stopping_voltages_v" in params:
            voltages = [float(v) for v in params["stopping_voltages_v"]]
        elif "stopping_voltages" in params:
            voltages = [float(v) for v in params["stopping_voltages"]]
        else:
            return RecipePhaseResult(
                phase="acquire",
                status="failed",
                message="Live acquisition is not implemented. Provide recorded "
                "measurement arrays; synthetic data is not generated.",
            )

        if len(voltages) != len(wavelengths):
            return RecipePhaseResult(
                phase="acquire",
                status="failed",
                message=(
                    f"Mismatched data lengths: {len(wavelengths)} wavelengths vs "
                    f"{len(voltages)} stopping voltages."
                ),
                details={
                    "wavelengths_nm": wavelengths,
                    "stopping_voltages_v": voltages,
                },
            )

        if (
            not wavelengths
            or len(wavelengths) != len(voltages)
            or not all(math.isfinite(v) for v in (*wavelengths, *voltages))
        ):
            return RecipePhaseResult(
                phase="acquire",
                status="failed",
                message="Provide nonempty, matching, finite measurement arrays.",
            )

        if not all(math.isfinite(w) and w > 0 for w in wavelengths):
            return RecipePhaseResult(
                phase="acquire",
                status="failed",
                message="Wavelengths must be finite and positive.",
            )
        frequencies = [SPEED_OF_LIGHT / (w * 1e-9) for w in wavelengths]

        records: list[dict[str, float]] = [
            {
                "wavelength_nm": round(w, 2),
                "frequency_hz": round(f, 4),
                "stopping_voltage_v": round(v, 4),
            }
            for w, f, v in zip(wavelengths, frequencies, voltages, strict=True)
        ]

        acq_mode = "user_provided"
        details: dict[str, Any] = {
            "records": records,
            "data": {
                "wavelengths_nm": wavelengths,
                "frequencies_hz": frequencies,
                "stopping_voltages_v": voltages,
            },
            "sample_count": len(records),
            "acquisition_mode": acq_mode,
        }

        return RecipePhaseResult(
            phase="acquire",
            status="completed",
            message=f"Accepted {len(records)} caller-provided stopping voltages.",
            details=details,
        )

    def analyze(
        self,
        parameters: dict[str, Any] | None = None,
    ) -> RecipePhaseResult:
        """Perform linear regression on V vs f to calculate Planck's constant h."""
        params = parameters or {}
        data = params.get("data", {})

        wavelengths_raw = params.get("wavelengths_nm") or data.get("wavelengths_nm")
        voltages_raw = (
            params.get("stopping_voltages_v")
            or params.get("stopping_voltages")
            or data.get("stopping_voltages_v")
        )

        if not wavelengths_raw or not voltages_raw:
            return RecipePhaseResult(
                phase="analyze",
                status="failed",
                message="Provide wavelength and stopping voltage measurements.",
            )

        wavelengths = [float(w) for w in wavelengths_raw]
        voltages = [float(v) for v in voltages_raw]

        if (
            len(wavelengths) < MIN_REGRESSION_POINTS
            or len(voltages) < MIN_REGRESSION_POINTS
        ):
            return RecipePhaseResult(
                phase="analyze",
                status="failed",
                message="At least 3 data points required for linear regression.",
                details={"count": min(len(wavelengths), len(voltages))},
            )

        if len(wavelengths) != len(voltages):
            return RecipePhaseResult(
                phase="analyze",
                status="failed",
                message="Wavelength and voltage array lengths do not match.",
                details={
                    "wavelengths_count": len(wavelengths),
                    "voltages_count": len(voltages),
                },
            )

        if not all(math.isfinite(w) and w > 0 for w in wavelengths) or not all(
            math.isfinite(v) for v in voltages
        ):
            return RecipePhaseResult(
                phase="analyze",
                status="failed",
                message="Provide positive finite wavelengths and finite voltages.",
            )
        frequencies = [SPEED_OF_LIGHT / (w * 1e-9) for w in wavelengths]

        # OLS regression: V = (h/e)*f - (phi/e)
        n = len(frequencies)
        mean_f = math.fsum(frequencies) / n
        mean_v = math.fsum(voltages) / n

        df = [f - mean_f for f in frequencies]
        dv = [v - mean_v for v in voltages]

        sff = math.fsum(x * x for x in df)
        sfv = math.fsum(x * y for x, y in zip(df, dv, strict=True))
        svv = math.fsum(y * y for y in dv)

        if sff == 0.0 or svv == 0.0:
            return RecipePhaseResult(
                phase="analyze",
                status="failed",
                message="Zero variance in frequency or voltage values.",
                details={},
            )

        slope = sfv / sff  # Experimental h/e (V*s)
        intercept = mean_v - slope * mean_f  # -phi/e (V)

        r_squared = (sfv * sfv) / (sff * svv) if (sff * svv) > 0 else 0.0

        # Physical constants derivation
        h_exp = slope * ELEMENTARY_CHARGE  # J*s
        h_diff = abs(h_exp - PLANCK_CONSTANT_ACCEPTED)
        h_error_pct = (h_diff / PLANCK_CONSTANT_ACCEPTED) * 100.0

        work_function_j = -intercept * ELEMENTARY_CHARGE
        work_function_ev = -intercept

        cutoff_freq_hz = -intercept / slope if slope != 0 else 0.0
        cutoff_wavelength_nm = (
            (SPEED_OF_LIGHT / cutoff_freq_hz * 1e9) if cutoff_freq_hz > 0 else 0.0
        )

        details: dict[str, Any] = {
            "slope_h_over_e": slope,
            "slope_h_over_e_theoretical": HE_ACCEPTED,
            "intercept_v": intercept,
            "planck_constant_exp_js": h_exp,
            "planck_constant_accepted_js": PLANCK_CONSTANT_ACCEPTED,
            "planck_constant_error_pct": round(h_error_pct, 4),
            "work_function_ev": round(work_function_ev, 4),
            "work_function_j": work_function_j,
            "cutoff_frequency_hz": cutoff_freq_hz,
            "cutoff_wavelength_nm": round(cutoff_wavelength_nm, 2),
            "r_squared": round(r_squared, 6),
            "data_points": [
                {
                    "wavelength_nm": round(w, 2),
                    "frequency_hz": f,
                    "stopping_voltage_v": v,
                    "fitted_voltage_v": slope * f + intercept,
                }
                for w, f, v in zip(wavelengths, frequencies, voltages, strict=True)
            ],
        }

        msg = (
            f"Planck's constant h = {h_exp:.4e} J*s (error: {h_error_pct:.2f}%), "
            f"work function phi = {work_function_ev:.2f} eV, "
            f"cutoff wavelength = {cutoff_wavelength_nm:.1f} nm, R^2 = {r_squared:.4f}"
        )

        return RecipePhaseResult(
            phase="analyze",
            status="completed",
            message=msg,
            details=details,
        )

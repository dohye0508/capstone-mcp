# Copyright 2026 Capstone MCP contributors.
"""Descriptive statistics and summary calculations for numeric data series."""

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class SeriesSummary:
    """Summary metrics of a 1D numerical data series."""

    count: int
    mean: float
    std_dev: float
    min_val: float
    max_val: float
    peak_val: float


def compute_series_summary(values: Sequence[float]) -> SeriesSummary:
    """Compute descriptive statistics for a sequence of floating point values.

    Args:
        values: Sequence of numeric values.

    Returns:
        SeriesSummary containing count, mean, std_dev, min, max, and peak.

    Raises:
        ValueError: If there are no finite values or the statistics overflow.
    """
    n = 0
    mean_val = m2 = 0.0
    min_val, max_val = math.inf, -math.inf
    for value in values:
        if not math.isfinite(value):
            continue
        n += 1
        delta = value - mean_val
        mean_val += delta / n
        m2 += delta * (value - mean_val)
        min_val, max_val = min(value, min_val), max(value, max_val)

    if n == 0:
        msg = "Cannot compute summary on an empty series or without finite values"
        raise ValueError(msg)
    if not math.isfinite(mean_val) or not math.isfinite(m2):
        msg = "Series summary exceeds finite floating-point range"
        raise ValueError(msg)

    return SeriesSummary(
        count=n,
        mean=mean_val,
        std_dev=math.sqrt(m2 / max(n - 1, 1)),
        min_val=min_val,
        max_val=max_val,
        peak_val=max(abs(min_val), abs(max_val)),
    )

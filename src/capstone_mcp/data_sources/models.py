# Copyright 2026 Capstone MCP contributors.
"""Domain models for unified experiment data series and sources."""

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DataSeries:
    """A 1D numerical data series with associated units and metadata."""

    name: str
    units: str
    values: list[float | None]

    def clean_floats(self) -> list[float]:
        """Return finite values for single-series summaries."""
        return [v for v in self.values if v is not None and math.isfinite(v)]


@dataclass(frozen=True)
class ExperimentSeries:
    """Paired independent (x) and dependent (y) series for analysis and reporting."""

    x: DataSeries
    y: DataSeries
    run_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def paired_floats(self) -> tuple[list[float], list[float]]:
        """Keep the samples where both variables are finite and present."""
        x_samples: list[float] = []
        y_samples: list[float] = []
        for x, y in zip(self.x.values, self.y.values, strict=True):
            if x is None or y is None or not (math.isfinite(x) and math.isfinite(y)):
                continue
            x_samples.append(x)
            y_samples.append(y)
        return x_samples, y_samples


@dataclass(frozen=True)
class DatasetMetadata:
    """Metadata describing an available dataset within an experiment source."""

    name: str
    units: str
    run_id: str | None
    sample_count: int

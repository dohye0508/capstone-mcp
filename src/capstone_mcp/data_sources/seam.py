# Copyright 2026 Capstone MCP contributors.
"""Unified experiment data source seam for file archives, tables, and sessions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from capstone_mcp.data_sources.adapters.capfile import (
    read_capfile_datasets,
    read_capfile_series,
)
from capstone_mcp.data_sources.adapters.csv_file import (
    read_csv_datasets,
    read_csv_series,
)
from capstone_mcp.data_sources.adapters.live_session import LiveSessionAdapter
from capstone_mcp.data_sources.adapters.live_telemetry import LiveMeasurementAdapter

if TYPE_CHECKING:
    from capstone_mcp.data_sources.models import DatasetMetadata, ExperimentSeries
    from capstone_mcp.displays import ReadTableResult
    from capstone_mcp.session import UnifiedSessionManager


def list_source_datasets(
    source: str | Path,
    *,
    table_result: ReadTableResult | None = None,
    live_session: UnifiedSessionManager | None = None,
) -> list[DatasetMetadata]:
    """List all available datasets and their metadata from any experiment source.

    Args:
        source: Path to experiment archive (.cap), table (.csv), or live URI.
        table_result: A captured table page when source is live://table.
        live_session: Optional measurement session for retained sample counts.

    Returns:
        List of DatasetMetadata objects.

    Raises:
        FileNotFoundError: If source file does not exist.
        ValueError: If file format or live URI is unsupported.
    """
    if isinstance(source, str) and source.startswith("live://"):
        if source == "live://measurements":
            return LiveMeasurementAdapter(live_session).list_datasets()
        if source == "live://table":
            return LiveSessionAdapter(table_result).list_datasets()
        msg = f"Unsupported live source URI: {source}"
        raise ValueError(msg)

    path = Path(source)
    if not path.exists():
        msg = f"Data source file does not exist: {path}"
        raise FileNotFoundError(msg)

    suffix = path.suffix.lower()
    if suffix == ".cap":
        return read_capfile_datasets(path)
    if suffix in [".csv", ".tsv", ".txt"]:
        return read_csv_datasets(path)

    msg = f"Unsupported data source format: {suffix} for {path}"
    raise ValueError(msg)


def get_experiment_series(  # noqa: PLR0913
    source: str | Path,
    x_name: str,
    y_name: str,
    run_id: str | None = None,
    *,
    table_result: ReadTableResult | None = None,
    live_session: UnifiedSessionManager | None = None,
) -> ExperimentSeries:
    """Retrieve paired X and Y series from any supported experiment source.

    Args:
        source: Path to experiment source file (.cap or .csv) or live URI.
        x_name: Target independent variable column/signal name.
        y_name: Target dependent variable column/signal name.
        run_id: Optional specific Run ID filter (e.g. 'Run #1').
        table_result: A captured table page when source is live://table.
        live_session: Session that collected samples when source is live://measurements.

    Returns:
        ExperimentSeries containing paired x and y DataSeries.

    Raises:
        FileNotFoundError: If source does not exist.
        ValueError: If format is unsupported or series cannot be extracted.
    """
    if isinstance(source, str) and source.startswith("live://"):
        if source == "live://measurements":
            return LiveMeasurementAdapter(live_session).get_series(
                x_name, y_name, run_id=run_id,
            )
        if source == "live://table":
            return LiveSessionAdapter(table_result).get_series(
                x_name, y_name, run_id=run_id,
            )
        msg = f"Unsupported live source URI: {source}"
        raise ValueError(msg)

    path = Path(source)
    if not path.exists():
        msg = f"Data source file does not exist: {path}"
        raise FileNotFoundError(msg)

    suffix = path.suffix.lower()
    if suffix == ".cap":
        return read_capfile_series(path, x_name, y_name, run_id=run_id)
    if suffix in [".csv", ".tsv", ".txt"]:
        return read_csv_series(path, x_name, y_name)

    msg = f"Unsupported data source format '{suffix}' for {path}"
    raise ValueError(msg)

# Copyright 2026 Capstone MCP contributors.
"""Adapter for reading data series from PASCO Capstone .cap archives."""

from __future__ import annotations

from typing import TYPE_CHECKING

from capstone_mcp.capfiles import read_cap_file
from capstone_mcp.data_sources.models import (
    DataSeries,
    DatasetMetadata,
    ExperimentSeries,
)

if TYPE_CHECKING:
    from pathlib import Path

    from capstone_mcp.capfile_models import CapDataSet


def _resolve_dataset(datasets: list[CapDataSet], name: str) -> CapDataSet:
    target = name.strip().casefold()
    if not target:
        msg = "Dataset name must not be empty."
        raise ValueError(msg)
    exact: list[CapDataSet] = []
    partial: list[CapDataSet] = []
    for dataset in datasets:
        names = [
            value.casefold() for value in (dataset.name, dataset.source_name) if value
        ]
        if target in names:
            exact.append(dataset)
        elif any(target in value for value in names):
            partial.append(dataset)
    matches = exact or partial
    if not matches:
        msg = f"Dataset '{name}' not found in the selected run."
        raise ValueError(msg)
    if len(matches) > 1:
        msg = f"Dataset '{name}' is ambiguous; specify a unique name and run_id."
        raise ValueError(msg)
    return matches[0]


def read_capfile_datasets(path: Path) -> list[DatasetMetadata]:
    """Extract dataset metadata from a .cap archive."""
    archive = read_cap_file(path)
    metadata: list[DatasetMetadata] = []

    for d in archive.datasets:
        unit_str = str(d.unit_id) if d.unit_id is not None else ""
        run_id = d.run_name or (
            f"Run #{d.run_number}" if d.run_number is not None else None
        )
        count = (
            len(d.numeric_values)
            if d.numeric_values is not None
            else len(d.raw_values)
        )
        ds_name = (
            d.name
            or d.source_name
            or (f"Dataset_{d.data_set_id}" if d.data_set_id else "Unnamed")
        )
        metadata.append(
            DatasetMetadata(
                name=ds_name,
                units=unit_str,
                run_id=run_id,
                sample_count=count,
            ),
        )
    return metadata


def read_capfile_series(
    path: Path, x_name: str, y_name: str, run_id: str | None = None,
) -> ExperimentSeries:
    """Extract paired x and y series from a .cap archive."""
    archive = read_cap_file(path)

    # An unspecified run must not silently select among repeated measurements.
    datasets = archive.datasets
    if run_id:
        datasets = [
            d
            for d in datasets
            if (
                d.run_name == run_id
                or (
                    d.run_number is not None
                    and f"Run #{d.run_number}" == run_id
                )
            )
        ]

    x_ds = _resolve_dataset(datasets, x_name)
    y_ds = _resolve_dataset(datasets, y_name)
    if x_ds.numeric_values is None or y_ds.numeric_values is None:
        msg = "Selected datasets must contain numeric values."
        raise ValueError(msg)

    # Extract numeric values (which can contain None for sparse cells)
    x_raw = x_ds.numeric_values or []
    y_raw = y_ds.numeric_values or []
    x_vals = [float(v) if v is not None else None for v in x_raw]
    y_vals = [float(v) if v is not None else None for v in y_raw]

    x_run_id = x_ds.run_name or (
        f"Run #{x_ds.run_number}" if x_ds.run_number is not None else None
    )
    y_run_id = y_ds.run_name or (
        f"Run #{y_ds.run_number}" if y_ds.run_number is not None else None
    )
    if x_run_id != y_run_id or (
        x_run_id is not None
        and x_ds.data_set_id != y_ds.data_set_id
    ):
        msg = "Selected datasets belong to different runs."
        raise ValueError(msg)
    if len(x_vals) != len(y_vals):
        msg = "Selected datasets have different sample counts."
        raise ValueError(msg)

    return ExperimentSeries(
        x=DataSeries(
            name=x_ds.name or x_ds.source_name or "x",
            units=str(x_ds.unit_id) if x_ds.unit_id is not None else "",
            values=x_vals,
        ),
        y=DataSeries(
            name=y_ds.name or y_ds.source_name or "y",
            units=str(y_ds.unit_id) if y_ds.unit_id is not None else "",
            values=y_vals,
        ),
        run_id=x_run_id or y_run_id,
        metadata={"source": str(path), "format": "cap"},
    )


def read_capfile_all_series(
    path: Path,
) -> tuple[dict[str, list[float]], dict[str, str]]:
    """Extract all numeric series and interface channels from a .cap archive."""
    from capstone_mcp.capfiles import (  # noqa: PLC0415
        extract_cap_datasets,
        read_cap_configuration,
    )

    series: dict[str, list[float]] = {}
    channels: dict[str, str] = {}

    datasets = extract_cap_datasets(path)
    for ds in datasets:
        name = ds.name or ds.source_name or f"Series_{ds.data_set_id}"
        if ds.numeric_values:
            if any(value is None for value in ds.numeric_values):
                msg = (
                    f"Series '{name}' contains missing samples; "
                    "explicit alignment is required."
                )
                raise ValueError(msg)
            if name in series:
                msg = f"Series '{name}' occurs more than once; select an explicit run."
                raise ValueError(msg)
            series[name] = [float(v) for v in ds.numeric_values if v is not None]

    cfg = read_cap_configuration(path)
    for iface in cfg.hardware_interfaces:
        channels[f"Interface_{iface.euid}"] = (
            iface.interface_type or iface.subtype or "PASCO Interface"
        )

    return series, channels


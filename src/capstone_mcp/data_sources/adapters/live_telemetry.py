# Copyright 2026 Capstone MCP contributors.
"""Adapter for reading live telemetry series via CDP WebSocket fast-path."""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING, Final

import httpx2

from capstone_mcp.bridge import DEFAULT_PORT
from capstone_mcp.data_sources.models import (
    DataSeries,
    DatasetMetadata,
    ExperimentSeries,
)
from capstone_mcp.session import UnifiedSessionManager

if TYPE_CHECKING:
    from collections.abc import Iterator

    from capstone_mcp.bridge import NativeInventory

MIN_SERIES_SAMPLES: Final = 2


class LiveMeasurementAdapter:
    """Adapter for querying live telemetry and inventory over CDP WebSocket."""

    def __init__(
        self,
        session: UnifiedSessionManager | None = None,
        debug_port: int | None = None,
    ) -> None:
        """Initialize adapter with optional session manager and port."""
        if session is not None and debug_port not in (None, session.debug_port):
            msg = "Use the supplied session's debug port for its telemetry history."
            raise ValueError(msg)
        self.session = session or UnifiedSessionManager(
            debug_port=DEFAULT_PORT if debug_port is None else debug_port,
        )
        self.debug_port = self.session.debug_port

    def _inventory(self) -> NativeInventory:
        try:
            return self.session.read_live_inventory(port=self.debug_port)
        except (httpx2.HTTPError, RuntimeError, OSError, ValueError) as exc:
            msg = (
                "Capstone is not running for live source: "
                f"live://measurements ({exc})"
            )
            raise ValueError(msg) from exc

    def list_datasets(self) -> list[DatasetMetadata]:
        """Return inventory metadata and counts of retained samples."""
        return [
            DatasetMetadata(
                name=name,
                units=units,
                run_id=None,
                sample_count=self.session.telemetry.sample_count(euid),
            )
            for euid, name, units in _measurements(self._inventory())
        ]

    def get_series(
        self,
        x_name: str,
        y_name: str,
        run_id: str | None = None,
    ) -> ExperimentSeries:
        """Read one measurement against host elapsed time or sample index."""
        axis = _normalized(x_name)
        by_time = axis in {"time", "t", "시간"}
        if run_id is not None or not (by_time or axis in {"index", "sample", "인덱스"}):
            msg = "Use recorded data for paired measurements or a specific run."
            raise ValueError(msg)
        target = _normalized(y_name)
        matches = [
            (euid, units)
            for euid, name, units in _measurements(self._inventory())
            if target in {_normalized(name), _normalized(euid)}
        ]
        if len(matches) != 1:
            msg = f"Expected one live measurement matching '{y_name}'; use its EUID."
            raise ValueError(msg)
        y_euid, y_units = matches[0]
        samples = self.session.telemetry.get_samples(y_euid)
        if len(samples) < MIN_SERIES_SAMPLES:
            msg = "Collect at least two samples in the same Capstone session first."
            raise ValueError(msg)

        start = samples[0][0]
        return ExperimentSeries(
            x=DataSeries(
                name=x_name,
                units="s" if by_time else "",
                values=(
                    [timestamp - start for timestamp, _ in samples]
                    if by_time else [float(i) for i in range(len(samples))]
                ),
            ),
            y=DataSeries(name=y_name, units=y_units, values=[v for _, v in samples]),
            run_id=None,
            metadata={
                "source": "live_telemetry",
                "uri": "live://measurements",
                "x_basis": "host_monotonic_elapsed" if by_time else "sample_index",
                "y_euid": y_euid,
            },
        )


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip()).casefold()


def _measurements(inventory: NativeInventory) -> Iterator[tuple[str, str, str]]:
    for item in inventory.measurements:
        if not isinstance(item, dict):
            continue
        euid = str(
            item.get("MeasurementEUID") or item.get("euid") or item.get("EUID") or "",
        )
        if euid:
            name = str(
                item.get("MeasurementName")
                or item.get("name")
                or item.get("Name")
                or euid,
            )
            units = str(
                item.get("Unit") or item.get("units") or item.get("Units") or "",
            )
            yield euid, name, units

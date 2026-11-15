# Copyright 2026 Capstone MCP contributors.
"""Adapter for reading live telemetry series via CDP WebSocket fast-path."""

from __future__ import annotations

import logging
import unicodedata
from typing import TYPE_CHECKING, Final

import httpx2

from capstone_mcp.bridge import BridgeError
from capstone_mcp.data_sources.models import (
    DataSeries,
    DatasetMetadata,
    ExperimentSeries,
)
from capstone_mcp.session import UnifiedSessionManager

if TYPE_CHECKING:
    from capstone_mcp.bridge import NativeInventory

LOGGER: Final = logging.getLogger(__name__)


class LiveMeasurementAdapter:
    """Adapter for querying live telemetry and inventory over CDP WebSocket."""

    def __init__(
        self,
        session: UnifiedSessionManager | None = None,
        debug_port: int = 9222,
    ) -> None:
        """Initialize adapter with optional session manager and port."""
        self.session = session or UnifiedSessionManager(debug_port=debug_port)
        self.debug_port = debug_port

    def list_datasets(self) -> list[DatasetMetadata]:
        """Query live hardware inventory and return available measurement datasets."""
        try:
            inventory = self.session.read_live_inventory(port=self.debug_port)
        except (
            BridgeError,
            httpx2.HTTPError,
            RuntimeError,
            OSError,
            ValueError,
            TimeoutError,
        ) as exc:
            msg = (
                f"Capstone is not running for live source: live://measurements ({exc})"
            )
            raise ValueError(msg) from exc

        datasets: list[DatasetMetadata] = []
        for m in inventory.measurements:
            if isinstance(m, dict):
                name = str(
                    m.get("MeasurementName")
                    or m.get("name")
                    or m.get("Name")
                    or m.get("euid")
                    or "Measurement",
                )
                units = str(m.get("Unit") or m.get("units") or m.get("Units") or "")
                euid = str(
                    m.get("MeasurementEUID") or m.get("euid") or m.get("EUID") or "",
                ).strip()
                datasets.append(
                    DatasetMetadata(
                        name=name,
                        units=units,
                        run_id=None,
                        sample_count=self.session.telemetry.sample_count(euid),
                    ),
                )
        return datasets

    def get_series(
        self,
        x_name: str,
        y_name: str,
        run_id: str | None = None,
    ) -> ExperimentSeries:
        """Extract paired x and y DataSeries from live telemetry stream."""
        if run_id is not None:
            msg = "Live instantaneous measurements do not support run_id selection."
            raise ValueError(msg)
        try:
            inventory = self.session.read_live_inventory(port=self.debug_port)
        except (
            BridgeError,
            httpx2.HTTPError,
            RuntimeError,
            OSError,
            ValueError,
            TimeoutError,
        ) as exc:
            msg = (
                f"Capstone is not running for live source: live://measurements ({exc})"
            )
            raise ValueError(msg) from exc

        x_euid, x_units = self._resolve_measurement(inventory, x_name)
        y_euid, y_units = self._resolve_measurement(inventory, y_name)

        index_name = unicodedata.normalize("NFC", x_name.strip()).casefold()
        if x_euid is None and index_name in {"index", "sample", "인덱스", "샘플"}:
            x_val = 0.0
            x_units = ""
        elif x_euid is not None:
            try:
                x_val = self.session.read_live_measurement(x_euid, port=self.debug_port)
            except Exception as exc:
                msg = f"Failed to read live measurement for '{x_name}': {exc}"
                raise ValueError(msg) from exc
        else:
            msg = f"Measurement '{x_name}' not found in live inventory."
            raise ValueError(msg)

        if y_euid is not None:
            try:
                y_val = self.session.read_live_measurement(y_euid, port=self.debug_port)
            except Exception as exc:
                msg = f"Failed to read live measurement for '{y_name}': {exc}"
                raise ValueError(msg) from exc
        else:
            msg = f"Measurement '{y_name}' not found in live inventory."
            raise ValueError(msg)

        return ExperimentSeries(
            x=DataSeries(name=x_name, units=x_units, values=[x_val]),
            y=DataSeries(name=y_name, units=y_units, values=[y_val]),
            run_id=run_id,
            metadata={
                "source": "live_telemetry",
                "uri": "live://measurements",
                "x_euid": x_euid or "sample_index",
                "y_euid": y_euid,
            },
        )

    def _resolve_measurement(
        self,
        inventory: NativeInventory,
        target_name: str,
    ) -> tuple[str | None, str]:
        """Search inventory measurements for a matching name or euid."""
        target_lower = unicodedata.normalize("NFC", target_name.strip()).casefold()
        if not target_lower:
            msg = "Measurement name must not be empty."
            raise ValueError(msg)
        exact: list[tuple[str, str]] = []
        partial: list[tuple[str, str]] = []
        for m in inventory.measurements:
            if isinstance(m, dict):
                name = unicodedata.normalize(
                    "NFC",
                    str(
                        m.get("MeasurementName")
                        or m.get("name") or m.get("Name") or "",
                    ).strip(),
                )
                euid = str(
                    m.get("MeasurementEUID") or m.get("euid") or m.get("EUID") or "",
                ).strip()
                units = str(
                    m.get("Unit") or m.get("units") or m.get("Units") or "",
                ).strip()
                if not euid:
                    continue
                if target_lower in {name.casefold(), euid.casefold()}:
                    exact.append((euid, units))
                elif target_lower in name.casefold():
                    partial.append((euid, units))
        if target_lower in {"time", "t", "index", "sample"} and not exact:
            return None, ""
        matches = exact or partial
        if len(matches) > 1:
            msg = f"Measurement '{target_name}' is ambiguous; specify its EUID."
            raise ValueError(msg)
        return matches[0] if matches else (None, "")

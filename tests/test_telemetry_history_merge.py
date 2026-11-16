# Copyright 2026 Capstone MCP contributors.
"""Merge regression: history retains clock identity, ordering and LRU lifecycle."""
from unittest.mock import Mock

import pytest

from capstone_mcp.bridge import NativeInventory
from capstone_mcp.data_sources.adapters.live_telemetry import LiveMeasurementAdapter
from capstone_mcp.session.telemetry import (
    MAX_MEASUREMENTS,
    TelemetryBuffer,
    TelemetryClock,
)

CLOCK = TelemetryClock(clock_id="device-clock", unit="milliseconds", origin="device-boot")


def test_elapsed_timestamp_overflow_does_not_silently_drop_samples() -> None:
    buffer = TelemetryBuffer()
    session = Mock(debug_port=9222, telemetry=buffer)
    session.read_live_inventory.return_value = NativeInventory(
        sensors=[], measurements=[{"MeasurementEUID": "x", "MeasurementName": "X"}],
    )
    buffer.push_sample("x", 1, -1e308, clock=CLOCK)
    buffer.push_sample("x", 2, 1e308, clock=CLOCK)
    with pytest.raises(ValueError, match="elapsed time"):
        LiveMeasurementAdapter(session=session).get_series("time", "X")


def test_channel_lru_evicts_clock_origin_and_count_together() -> None:
    buffer = TelemetryBuffer()
    for i in range(MAX_MEASUREMENTS):
        buffer.push_sample(str(i), i, 10, clock=CLOCK)
    buffer.push_sample("0", 0, 11, clock=CLOCK)
    buffer.push_sample("new", 1, 12, clock=CLOCK)
    removed = buffer.get_snapshot("1")
    assert removed.clock is None
    assert removed.first_timestamp is None
    assert removed.first_sample_index == 0
    assert removed.samples == []
    buffer.push_sample("1", 2)
    assert buffer.get_clock("1") != CLOCK
    assert buffer.get_snapshot("1").first_sample_index == 0


def test_history_preserves_equal_time_order_and_stable_elapsed_origin() -> None:
    buffer = TelemetryBuffer(capacity=2)
    session = Mock(debug_port=9222, telemetry=buffer)
    session.read_live_inventory.return_value = NativeInventory(sensors=[], measurements=[{"MeasurementEUID": "x", "MeasurementName": "Position", "Unit": "m"}])
    adapter = LiveMeasurementAdapter(session=session)
    buffer.push_sample("x", 9, 100, clock=CLOCK)
    buffer.push_sample("x", 1, 100, clock=CLOCK)
    first = adapter.get_series("time", "Position")
    assert first.y.values == [9, 1]
    assert first.x.values == [0, 0]
    buffer.push_sample("x", 3, 150, clock=CLOCK)
    timed = adapter.get_series("time", "Position")
    assert timed.x.values == [0, 50]
    assert timed.x.units == "ms"
    assert timed.metadata["clock_id"] == CLOCK.clock_id
    assert timed.metadata["clock_origin"] == CLOCK.origin
    buffer.push_sample("x", 4, 200, clock=CLOCK)
    assert adapter.get_series("time", "Position").x.values == [50, 100]
    assert adapter.get_series("index", "Position").x.values == [2, 3]
    session.read_live_measurement.assert_not_called()

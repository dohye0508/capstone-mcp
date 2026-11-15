# Copyright 2026 Capstone MCP contributors.
"""Deterministic monitoring failure, cancellation, and cadence regressions."""

from threading import Event
from unittest.mock import Mock

import pytest

from capstone_mcp.session import watcher
from capstone_mcp.session.watcher import ConditionWatcher, StopCondition


def test_sampler_failure_requests_halt_once_and_preserves_failure() -> None:
    halt = Mock()
    condition = StopCondition(measurement_euid="test", operator=">", threshold=1)
    with pytest.raises(OSError, match="disconnected"):
        ConditionWatcher().monitor(
            condition, Mock(side_effect=OSError("disconnected")), halt_callback=halt,
        )
    halt.assert_called_once_with()


def test_cancellation_before_sampling_does_not_invent_a_value() -> None:
    cancel = Event()
    cancel.set()
    sampler = Mock()
    halt = Mock()
    result = ConditionWatcher().monitor(
        StopCondition(measurement_euid="test", operator=">", threshold=1),
        sampler, halt_callback=halt, cancel=cancel,
    )
    assert not result.triggered
    assert result.current_value is None
    assert "cancelled" in result.detail
    sampler.assert_not_called()
    halt.assert_called_once_with()


def test_sampler_duration_is_subtracted_from_poll_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [0.0]
    delays: list[float] = []

    class ClockCancellation:
        def is_set(self) -> bool:
            return False

        def wait(self, timeout: float) -> bool:
            delays.append(timeout)
            clock[0] += timeout
            return False

    def sample() -> float:
        clock[0] += 0.02
        return 1.0

    monkeypatch.setattr(watcher.time, "monotonic", lambda: clock[0])
    halt = Mock()
    result = ConditionWatcher().monitor(
        StopCondition(
            measurement_euid="test", operator=">", threshold=2,
            poll_interval=0.05, timeout=0.1,
        ),
        sample, halt_callback=halt, cancel=ClockCancellation(),
    )
    assert delays == pytest.approx([0.03, 0.03])
    assert not result.triggered
    assert result.elapsed_seconds == pytest.approx(0.1)
    halt.assert_called_once_with()


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_invalid_monitor_timing_is_rejected(value: float) -> None:
    with pytest.raises(ValueError, match="poll_interval"):
        StopCondition(measurement_euid="test", operator=">", threshold=1, poll_interval=value)

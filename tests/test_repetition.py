# Copyright 2026 Capstone MCP contributors.
"""Test deterministic repeated acquisition sequencing."""

from collections import deque
from collections.abc import Callable

import pytest

from capstone_mcp.acquisition import RecordingStatus
from capstone_mcp.desktop import AutomationError
from capstone_mcp.repetition import RepeatPlan, run_sequence


class StartError(RuntimeError):
    """Represent a failed recording start request."""


class RecordingBackendFake:
    """Expose scripted observations while tracking requested transitions."""

    def __init__(
        self,
        observations: tuple[RecordingStatus, ...],
        start_error: StartError | None = None,
    ) -> None:
        self.observations: deque[RecordingStatus] = deque(observations)
        self.current: RecordingStatus = observations[0]
        self.start_error: StartError | None = start_error
        self.changes: list[bool] = []

    def observe(self) -> RecordingStatus:
        self.current = self.observations.popleft()
        return self.current

    def change(self, *, recording: bool) -> RecordingStatus:
        self.changes.append(recording)
        if recording and self.start_error is not None:
            raise self.start_error
        self.current = self.current.model_copy(update={"recording": recording})
        return self.current


class CancellationFake:
    """Return scripted wait outcomes without sleeping or polling."""

    def __init__(
        self, wait_results: tuple[bool, ...], *, cancelled: bool = False,
    ) -> None:
        self.wait_results: deque[bool] = deque(wait_results)
        self.cancelled: bool = cancelled
        self.waits: list[float] = []

    def is_set(self) -> bool:
        return self.cancelled

    def wait(self, timeout: float) -> bool:
        self.waits.append(timeout)
        return self.wait_results.popleft()


def recording_status(
    *, recording: bool = False, enabled: bool = True, rate: str = "20 Hz",
) -> RecordingStatus:
    return RecordingStatus(
        window_handle=1,
        process_id=1,
        recording=recording,
        control_enabled=enabled,
        time_display="00:00.00",
        sampling_rate_display=rate,
    )


def repeat_plan(*, repetitions: int = 1) -> RepeatPlan:
    return RepeatPlan(
        process_id=1,
        window_handle=1,
        repetitions=repetitions,
        duration_seconds=2,
        pause_seconds=0.5,
    )


def clock_from(*values: float) -> Callable[[], float]:
    return iter(values).__next__


def test_run_sequence_completes_two_cycles() -> None:
    # Given
    backend = RecordingBackendFake((
        recording_status(),
        recording_status(),
        recording_status(),
    ))
    cancellation = CancellationFake((False, False, False))
    # When
    outcome = run_sequence(
        backend,
        repeat_plan(repetitions=2),
        cancellation,
        clock=clock_from(10, 12, 20, 23),
    )
    # Then
    assert outcome.state == "completed"
    assert outcome.runs is not None
    assert [run.ordinal for run in outcome.runs] == [1, 2]
    assert [run.elapsed_seconds for run in outcome.runs] == [2, 3]
    assert backend.changes == [True, False, True, False]
    assert cancellation.waits == [2, 0.5, 2]


def test_run_sequence_stops_when_cancelled_during_measurement() -> None:
    # Given
    backend = RecordingBackendFake((recording_status(), recording_status()))
    cancellation = CancellationFake((True,))
    # When
    outcome = run_sequence(
        backend,
        repeat_plan(),
        cancellation,
        clock=clock_from(5, 6.5),
    )
    # Then
    assert outcome.state == "cancelled"
    assert outcome.runs is not None
    assert [run.elapsed_seconds for run in outcome.runs] == [1.5]
    assert backend.changes == [True, False]
    assert cancellation.waits == [2]


def test_run_sequence_requests_stop_when_start_raises() -> None:
    # Given
    error = StartError("start failed")
    backend = RecordingBackendFake(
        (recording_status(), recording_status()),
        start_error=error,
    )
    # When / Then
    with pytest.raises(StartError) as raised:
        _ = run_sequence(backend, repeat_plan(), CancellationFake(()))
    assert raised.value is error
    assert backend.changes == [True, False]


@pytest.mark.parametrize(
    ("recording", "enabled"),
    [(True, True), (False, False)],
    ids=["already-recording", "disabled"],
)
def test_run_sequence_rejects_unavailable_initial_state(
    *, recording: bool, enabled: bool,
) -> None:
    # Given
    backend = RecordingBackendFake((
        recording_status(recording=recording, enabled=enabled),
    ))
    # When / Then
    with pytest.raises(AutomationError):
        _ = run_sequence(backend, repeat_plan(), CancellationFake(()))
    assert backend.changes == []


def test_run_sequence_rejects_sample_rate_change_between_runs() -> None:
    # Given
    backend = RecordingBackendFake((
        recording_status(),
        recording_status(),
        recording_status(rate="100 Hz"),
    ))
    cancellation = CancellationFake((False, False))
    # When / Then
    with pytest.raises(AutomationError):
        _ = run_sequence(
            backend,
            repeat_plan(repetitions=2),
            cancellation,
            clock=clock_from(10, 11),
        )
    assert backend.changes == [True, False]

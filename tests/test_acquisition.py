# Copyright 2026 Capstone MCP contributors.
"""Test recording request semantics at the native adapter boundary."""

from typing import override

import pytest

from capstone_mcp import acquisition
from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.models import Action, Bounds, Control, Result, Snapshot, Window


class RecordingAdapter(Capstone):
    """Mutable native-adapter fake: an accepted input changes its recording state."""

    def __init__(self, *, enabled: bool = True, accepts_input: bool = True) -> None:
        super().__init__()
        self.recording: bool = False
        self.enabled: bool = enabled
        self.accepts_input: bool = accepts_input
        self.calls: int = 0

    @override
    def act(
        self, ref: str, action: Action, *, allow_foreground: bool = False,
    ) -> Result:
        assert ref == "record"
        assert action == Action.INVOKE
        assert allow_foreground
        self.calls += 1
        if self.accepts_input:
            self.recording = not self.recording
        return Result(detail="input delivered")

    def observation(self) -> acquisition.RecordingStatus:
        return acquisition.RecordingStatus(
            window_handle=1, process_id=1, recording=self.recording,
            control_enabled=self.enabled, time_display="00:00.00",
            sampling_rate_display="20 Hz",
        )


def install_observer(
    monkeypatch: pytest.MonkeyPatch, adapter: RecordingAdapter,
) -> None:
    def observed(
        _app: Capstone, _handle: int,
    ) -> tuple[acquisition.RecordingStatus, str]:
        return adapter.observation(), "record"

    monkeypatch.setattr(acquisition, "observe_recording", observed)


def test_stop_does_not_toggle_an_already_stopped_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    app = RecordingAdapter()
    install_observer(monkeypatch, app)
    # When
    result = acquisition.request_recording(
        app, 1, recording=False, allow_foreground=False,
    )
    # Then
    assert app.calls == 0
    assert not result.observed.recording
    assert not result.transition_pending


def test_disabled_record_control_cannot_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    app = RecordingAdapter(enabled=False)
    install_observer(monkeypatch, app)
    # When / Then
    with pytest.raises(AutomationError):
        _ = acquisition.request_recording(
            app, 1, recording=True, allow_foreground=True,
        )
    assert app.calls == 0


@pytest.mark.parametrize("accepts_input", [True, False])
def test_start_reports_observed_state_not_just_input_delivery(
    monkeypatch: pytest.MonkeyPatch, *, accepts_input: bool,
) -> None:
    # Given
    app = RecordingAdapter(accepts_input=accepts_input)
    install_observer(monkeypatch, app)
    # When
    result = acquisition.request_recording(
        app, 1, recording=True,
    )
    # Then
    assert app.calls == 1
    assert result.observed.recording == accepts_input
    assert result.transition_pending != accepts_input


class RateAdapter(RecordingAdapter):
    """One selected sensor with a real state change at the input boundary."""

    def __init__(self) -> None:
        super().__init__()
        self.rate: str = "50 Hz"
        self.calls: int = 0

    @override
    def observation(self) -> acquisition.RecordingStatus:
        return super().observation().model_copy(update={
            "sampling_rate_display": self.rate,
        })

    @override
    def snapshot(self, handle: int, depth: int, limit: int) -> Snapshot:
        bounds = Bounds(left=0, top=0, right=100, bottom=100)
        return Snapshot(
            window=Window(handle=handle, title="test", process_id=1, bounds=bounds),
            controls=[
                Control(
                    ref=ref, parent=None, name=name, control_type="Button",
                    automation_id="control." + suffix, enabled=True, visible=True,
                    bounds=bounds,
                )
                for ref, name, suffix in [
                    ("sensor", "Blue", "SamplingRateTargetSelector"),
                    ("increase", "", "IncreaseSampleRateButton"),
                    ("decrease", "", "DecreaseSampleRateButton"),
                ]
            ], truncated=False,
        )

    @override
    def act(
        self, ref: str, action: Action, *, allow_foreground: bool = False,
    ) -> Result:
        assert allow_foreground
        assert action == Action.INVOKE
        self.calls += 1
        self.rate = "100 Hz" if ref == "increase" else "25 Hz"
        return Result(detail="rate changed")


def test_rate_step_reports_native_change(monkeypatch: pytest.MonkeyPatch) -> None:
    app = RateAdapter()
    install_observer(monkeypatch, app)
    result = acquisition.step_sampling_rate(
        app, 1, "increase", expected_sensor="Blue",
    )
    assert (result.before, result.after, result.changed) == ("50 Hz", "100 Hz", True)
    assert app.calls == 1


@pytest.mark.parametrize("recording", [True, False])
def test_rate_step_rejects_wrong_sensor_or_active_run(
    monkeypatch: pytest.MonkeyPatch, *, recording: bool,
) -> None:
    app = RateAdapter()
    app.recording = recording
    install_observer(monkeypatch, app)
    with pytest.raises(AutomationError):
        _ = acquisition.step_sampling_rate(
            app, 1, "increase", expected_sensor="Red", allow_foreground=True,
        )
    assert app.calls == 0

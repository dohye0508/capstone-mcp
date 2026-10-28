# Copyright 2026 Capstone MCP contributors.
"""Explicit start/stop requests based on the observed Capstone recording state."""

from typing import Final, Literal

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.models import Action, Model

TOGGLE_OFF: Final = 0
TOGGLE_ON: Final = 1
RECORD_SUFFIX: Final = ".RecordContainer.RecordStartStopButton"
RATE_SUFFIX: Final = ".SamplingRateControl.SamplingRateLabel"
TIME_SUFFIX: Final = ".ExperimentTimeControl.TimeLabel"


class RecordingStatus(Model):
    """Observed UI state; displayed time/rate strings are not converted or guessed."""

    window_handle: int
    process_id: int
    recording: bool
    control_enabled: bool
    time_display: str | None
    sampling_rate_display: str | None


class RecordingRequest(Model):
    """A request and its immediate observation, without claiming an async transition."""

    requested_recording: bool
    observed: RecordingStatus
    transition_pending: bool


class SamplingRateChange(Model):
    """Observed discrete setting change for the currently selected sensor."""

    sensor: str
    before: str
    after: str
    changed: bool


def step_sampling_rate(
    app: Capstone, handle: int, direction: Literal["increase", "decrease"],
    *, expected_sensor: str, allow_foreground: bool = True,
) -> SamplingRateChange:
    """Click one native rate step, checking the selected sensor and stopped state."""
    state, _ = observe_recording(app, handle)
    if state.recording:
        msg = "Stop recording before changing the sample rate."
        raise AutomationError(msg)
    snapshot = app.snapshot(handle, 16, 10_000)
    sensors = [
        c for c in snapshot.controls if c.visible
        and c.automation_id.endswith(".SamplingRateTargetSelector")
    ]
    if len(sensors) != 1 or sensors[0].name != expected_sensor:
        msg = "Selected sampling sensor does not match expected_sensor."
        raise AutomationError(msg)
    suffix = (
        ".IncreaseSampleRateButton" if direction == "increase"
        else ".DecreaseSampleRateButton"
    )
    buttons = [
        c for c in snapshot.controls
        if c.visible and c.automation_id.endswith(suffix)
    ]
    if len(buttons) != 1 or not buttons[0].enabled:
        msg = "The requested sampling-rate step is unavailable."
        raise AutomationError(msg)
    if state.sampling_rate_display is None:
        msg = "The current sampling rate is not visible."
        raise AutomationError(msg)
    _ = app.act(buttons[0].ref, Action.INVOKE, allow_foreground=allow_foreground)
    after, _ = observe_recording(app, handle)
    if after.sampling_rate_display is None:
        msg = "Sampling rate disappeared after the request; inspect Capstone."
        raise AutomationError(msg)
    return SamplingRateChange(
        sensor=expected_sensor, before=state.sampling_rate_display,
        after=after.sampling_rate_display,
        changed=state.sampling_rate_display != after.sampling_rate_display,
    )


def observe_recording(app: Capstone, handle: int) -> tuple[RecordingStatus, str]:
    """Read the visible recording checkbox and nearby displays from a fresh tree."""
    snapshot = app.snapshot(handle, 16, 10_000)
    controls = [
        control for control in snapshot.controls
        if control.visible and control.automation_id.endswith(RECORD_SUFFIX)
    ]
    if len(controls) != 1:
        msg = "No unique visible recording control; inspect the active experiment page."
        raise AutomationError(msg)
    control = controls[0]
    toggle = app.refs[control.ref].iface_toggle.CurrentToggleState
    if toggle not in (TOGGLE_OFF, TOGGLE_ON):
        msg = "Capstone recording state is indeterminate."
        raise AutomationError(msg)
    rate = next(
        (c.name for c in snapshot.controls if c.automation_id.endswith(RATE_SUFFIX)),
        None,
    )
    time_text = next(
        (c.name for c in snapshot.controls if c.automation_id.endswith(TIME_SUFFIX)),
        None,
    )
    return RecordingStatus(
        window_handle=handle, process_id=snapshot.window.process_id,
        recording=toggle == TOGGLE_ON, control_enabled=control.enabled,
        time_display=time_text, sampling_rate_display=rate,
    ), control.ref


def request_recording(
    app: Capstone, handle: int, *, recording: bool, allow_foreground: bool = True,
) -> RecordingRequest:
    """Request one idempotent start or stop; never toggle an already-correct state."""
    observed, ref = observe_recording(app, handle)
    if observed.recording == recording:
        return RecordingRequest(
            requested_recording=recording, observed=observed,
            transition_pending=False,
        )
    if not observed.control_enabled:
        msg = "Capstone recording control is disabled; connect/configure a data source."
        raise AutomationError(msg)
    _ = app.act(ref, Action.INVOKE, allow_foreground=allow_foreground)
    observed, _ = observe_recording(app, handle)
    return RecordingRequest(
        requested_recording=recording, observed=observed,
        transition_pending=observed.recording != recording,
    )

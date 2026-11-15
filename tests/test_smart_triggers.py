# Copyright 2026 Capstone MCP contributors.
"""Tests for smart triggers, recording conditions, and keep sample tools."""

from unittest.mock import MagicMock

import pytest

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.instruments import (
    ConditionSpec,
    InstrumentAction,
    InstrumentRequest,
    InstrumentResult,
    KeepSampleRequest,
    KeepSampleResult,
    SetRecordingConditionRequest,
    SetSamplingModeRequest,
    SetSamplingModeResult,
    manage_instrument,
)
from capstone_mcp.models import Bounds, Control, Snapshot, Window


def _make_window() -> Window:
    return Window(
        handle=100,
        title="Capstone",
        process_id=1,
        bounds=Bounds(left=0, top=0, right=1200, bottom=900),
    )


# --- Tests for set_recording_condition ---


def test_set_recording_condition_rejects_missing_foreground() -> None:
    app = Capstone()
    req = SetRecordingConditionRequest(
        handle=100,
        start_condition=ConditionSpec(condition_type="time", threshold=5.0),
        allow_foreground=False,
    )
    with pytest.raises(AutomationError, match="allow_foreground"):
        _ = manage_instrument(
            app,
            InstrumentRequest(
                action=InstrumentAction.SET_RECORDING_CONDITION,
                set_recording_condition=req,
            ),
        )


def test_set_recording_condition_rejects_empty_conditions() -> None:
    app = Capstone()
    req = SetRecordingConditionRequest(handle=100)
    with pytest.raises(AutomationError, match="At least one"):
        _ = manage_instrument(
            app,
            InstrumentRequest(
                action=InstrumentAction.SET_RECORDING_CONDITION,
                set_recording_condition=req,
            ),
        )


def test_set_recording_condition_raises_when_toggle_not_found() -> None:
    app = Capstone()
    mock_win = _make_window()
    app.snapshot = MagicMock(
        return_value=Snapshot(
            window=mock_win,
            controls=[
                Control(
                    ref="ref:btn",
                    parent=None,
                    name="Calculator",
                    control_type="CheckBox",
                    automation_id="ObjNameCalculator",
                    enabled=True,
                    visible=True,
                    bounds=Bounds(left=0, top=0, right=50, bottom=50),
                ),
            ],
            truncated=False,
        ),
    )

    req = SetRecordingConditionRequest(
        handle=100,
        start_condition=ConditionSpec(condition_type="time", threshold=3.0),
    )
    with pytest.raises(AutomationError, match="Recording Conditions toggle button"):
        _ = manage_instrument(
            app,
            InstrumentRequest(
                action=InstrumentAction.SET_RECORDING_CONDITION,
                set_recording_condition=req,
            ),
        )


def test_sensor_trigger_rejects_unimplemented_measurement_before_input() -> None:
    app = MagicMock(spec=Capstone)
    req = SetRecordingConditionRequest(
        start_condition=ConditionSpec(
            condition_type="sensor_threshold",
            measurement="Force",
            threshold=5.0,
        ),
    )
    with pytest.raises(
        AutomationError, match="Sensor-trigger selection is unsupported",
    ):
        manage_instrument(
            app,
            InstrumentRequest(
                action=InstrumentAction.SET_RECORDING_CONDITION,
                set_recording_condition=req,
            ),
        )
    app.snapshot.assert_not_called()


# --- Tests for set_sampling_mode ---


def test_set_sampling_mode_requires_foreground() -> None:
    app = Capstone()
    req = SetSamplingModeRequest(handle=100, mode="keep_sample", allow_foreground=False)
    with pytest.raises(AutomationError, match="allow_foreground"):
        _ = manage_instrument(
            app,
            InstrumentRequest(
                action=InstrumentAction.SET_SAMPLING_MODE,
                set_sampling_mode=req,
            ),
        )


def test_set_sampling_mode_raises_when_control_not_found() -> None:
    app = Capstone()
    mock_win = _make_window()
    app.snapshot = MagicMock(
        return_value=Snapshot(
            window=mock_win,
            controls=[],
            truncated=False,
        ),
    )

    req = SetSamplingModeRequest(handle=100, mode="keep_sample")
    with pytest.raises(AutomationError, match="Sampling mode control"):
        _ = manage_instrument(
            app,
            InstrumentRequest(
                action=InstrumentAction.SET_SAMPLING_MODE,
                set_sampling_mode=req,
            ),
        )


def test_set_sampling_mode_success() -> None:
    app = Capstone()
    mock_win = _make_window()

    mode_btn = Control(
        ref="ref:keep_radio",
        parent=None,
        name="Keep Sample",
        control_type="RadioButton",
        automation_id="mode_keep_sample",
        enabled=True,
        visible=True,
        bounds=Bounds(left=100, top=800, right=200, bottom=830),
    )
    app.snapshot = MagicMock(
        return_value=Snapshot(
            window=mock_win,
            controls=[mode_btn],
            truncated=False,
        ),
    )

    btn_node = MagicMock()
    app.control = MagicMock(return_value=btn_node)

    req = SetSamplingModeRequest(handle=100, mode="keep_sample")
    inst_res = manage_instrument(
        app,
        InstrumentRequest(
            action=InstrumentAction.SET_SAMPLING_MODE,
            set_sampling_mode=req,
        ),
    )

    assert isinstance(inst_res, InstrumentResult)
    assert isinstance(inst_res.set_sampling_mode, SetSamplingModeResult)
    result = inst_res.set_sampling_mode
    assert result.mode == "keep_sample"
    assert result.verified is False
    btn_node.iface_selection_item.Select.assert_called_once()


# --- Tests for keep_sample ---


def test_keep_sample_requires_foreground() -> None:
    app = Capstone()
    req = KeepSampleRequest(handle=100, allow_foreground=False)
    with pytest.raises(AutomationError, match="allow_foreground"):
        _ = manage_instrument(
            app,
            InstrumentRequest(
                action=InstrumentAction.KEEP_SAMPLE,
                keep_sample=req,
            ),
        )


def test_keep_sample_raises_when_button_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "capstone_mcp.instruments.triggers.observe_recording",
        MagicMock(return_value=(MagicMock(recording=True), "record")),
    )
    app = Capstone()
    mock_win = _make_window()
    app.snapshot = MagicMock(
        return_value=Snapshot(
            window=mock_win,
            controls=[],
            truncated=False,
        ),
    )

    req = KeepSampleRequest(handle=100)
    with pytest.raises(AutomationError, match="Keep Sample button not found"):
        _ = manage_instrument(
            app,
            InstrumentRequest(
                action=InstrumentAction.KEEP_SAMPLE,
                keep_sample=req,
            ),
        )


def test_keep_sample_success_with_value_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "capstone_mcp.instruments.triggers.observe_recording",
        MagicMock(return_value=(MagicMock(recording=True), "record")),
    )
    app = Capstone()
    mock_win = _make_window()

    keep_btn = Control(
        ref="ref:keep_btn",
        parent=None,
        name="Keep Sample",
        control_type="Button",
        automation_id="ControlBar.KeepSampleButton",
        enabled=True,
        visible=True,
        bounds=Bounds(left=50, top=800, right=150, bottom=830),
    )
    val_edit = Control(
        ref="ref:val_edit",
        parent=None,
        name="Position Value",
        control_type="Edit",
        automation_id="SampleValueEdit",
        enabled=True,
        visible=True,
        bounds=Bounds(left=300, top=400, right=400, bottom=430),
    )

    app.snapshot = MagicMock(
        return_value=Snapshot(
            window=mock_win,
            controls=[keep_btn, val_edit],
            truncated=False,
        ),
    )
    app.click = MagicMock()
    app.keys = MagicMock()

    val_node = MagicMock()
    app.control = MagicMock(return_value=val_node)

    req = KeepSampleRequest(handle=100, value=0.25, variable_name="Position")
    inst_res = manage_instrument(
        app,
        InstrumentRequest(
            action=InstrumentAction.KEEP_SAMPLE,
            keep_sample=req,
        ),
    )

    assert isinstance(inst_res, InstrumentResult)
    assert isinstance(inst_res.keep_sample, KeepSampleResult)
    result = inst_res.keep_sample
    assert result.sample_retained is False
    assert result.recorded_value == 0.25
    assert result.variable_name == "Position"
    assert result.verified is False
    app.click.assert_called_once_with(100, "ref:keep_btn", allow_foreground=True)
    val_node.iface_value.SetValue.assert_called_once_with("0.25")
    app.keys.assert_called_once_with(100, "{ENTER}", allow_foreground=True)

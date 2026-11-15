# Copyright 2026 Capstone MCP contributors.
"""Adversarial offline contracts; these tests do not validate real hardware."""

from _ctypes import COMError
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock

import pytest

from capstone_mcp.acquisition import observe_recording
from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.instruments import generator, sensors, triggers, wireless
from capstone_mcp.instruments._controls import select_observed_option
from capstone_mcp.instruments.models import (
    ConnectWirelessSensorRequest,
    InstrumentRequest,
    KeepSampleRequest,
    SamplingRateRequest,
    ScanWirelessSensorsRequest,
    ZeroSensorRequest,
    _RateControls,
)
from capstone_mcp.models import Bounds, Control, Snapshot, Window


def control(name: str, kind: str = "Button", aid: str = "", ref: str = "ref") -> Control:
    return Control(ref=ref, parent=None, name=name, control_type=kind,
                   automation_id=aid, enabled=True, visible=True,
                   bounds=Bounds(left=0, top=0, right=10, bottom=10))


def snapshot(*controls: Control) -> Snapshot:
    return Snapshot(window=Window(handle=1, title="test", process_id=1,
                    bounds=Bounds(left=0, top=0, right=100, bottom=100)),
                    controls=list(controls), truncated=False)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, duration: float) -> None:
        self.now += duration


@pytest.mark.parametrize(("display", "hz"), [
    ("1 kHz", "1000"), ("2 MHz", "2000000"), ("0.5 ms", "2000"),
    ("10 us", "100000"), ("1 s", "1"),
])
def test_sampling_units_normalize(display: str, hz: str) -> None:
    assert sensors._rate_parts(display) == (Decimal(hz), "Hz")


def test_rate_transition_waits_without_replaying_input(monkeypatch: pytest.MonkeyPatch) -> None:
    before = _RateControls(display="500 Hz", increase_ref="inc", decrease_ref="dec", increase_enabled=True, decrease_enabled=True)
    after = before.model_copy(update={"display": "1 kHz"})
    read = MagicMock(side_effect=[before, before, after])
    monkeypatch.setattr(sensors, "_rate_controls", read)
    clock = Clock()
    monkeypatch.setattr(sensors, "time", clock)
    app = MagicMock(spec=Capstone)
    result = sensors._step_rate(app, 1, SamplingRateRequest(sensor="Force"), "increase", before)
    assert result.display == "1 kHz"
    assert clock.now > 0
    app.act.assert_called_once()


def test_rate_transition_timeout_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    before = _RateControls(display="500 Hz", increase_ref="inc", decrease_ref="dec", increase_enabled=True, decrease_enabled=True)
    monkeypatch.setattr(sensors, "_rate_controls", MagicMock(return_value=before))
    clock = Clock()
    monkeypatch.setattr(sensors, "time", clock)
    app = MagicMock(spec=Capstone)
    with pytest.raises(AutomationError, match="did not change"):
        sensors._step_rate(app, 1, SamplingRateRequest(sensor="Force"), "increase", before)
    assert clock.now == pytest.approx(2.0)
    app.act.assert_called_once()


def test_target_rate_crosses_khz_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    displays = ["500 Hz", "1 kHz", "2 kHz"]
    index = 0
    app = MagicMock(spec=Capstone)

    def read(*_args: object) -> _RateControls:
        return _RateControls(display=displays[index], increase_ref="inc", decrease_ref="dec", increase_enabled=True, decrease_enabled=True)

    def act(*_args: object, **_kwargs: object) -> None:
        nonlocal index
        index += 1

    app.act.side_effect = act
    monkeypatch.setattr(sensors, "_rate_controls", read)
    result = sensors.target_sampling_rate(app, 1, SamplingRateRequest(sensor="Force", target="0.5 ms"))
    assert result.after == "2 kHz"
    assert result.inputs_delivered == 2


def test_zero_during_recording_never_delivers_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sensors, "observe_recording", MagicMock(return_value=(SimpleNamespace(recording=True), "r")))
    app = MagicMock(spec=Capstone)
    with pytest.raises(AutomationError, match="Stop recording"):
        sensors.zero_sensor(app, ZeroSensorRequest())
    app.act.assert_not_called()
    app.snapshot.assert_not_called()


def test_keep_sample_while_stopped_never_delivers_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(triggers, "observe_recording", MagicMock(return_value=(SimpleNamespace(recording=False), "r")))
    app = MagicMock(spec=Capstone)
    with pytest.raises(AutomationError, match="Start recording"):
        triggers.keep_sample(app, KeepSampleRequest())
    app.click.assert_not_called()


def test_power_id_does_not_determine_power_state() -> None:
    app = MagicMock(spec=Capstone)
    app.control.return_value = SimpleNamespace()
    ctrl = control("Power", aid="Output_On_Off")
    with pytest.raises(AutomationError, match="unobservable"):
        generator._is_power_on(app, ctrl)
    assert not generator._is_power_button(control("Output Configuration"))


def test_combo_selects_only_observed_label() -> None:
    app = MagicMock(spec=Capstone)
    node = app.control.return_value
    node.item_texts.return_value = ["Continuous", "Keep Sample"]
    select_observed_option(app, control("Sampling Mode", "ComboBox"), "keep_sample")
    node.select.assert_called_once_with("Keep Sample")
    node.iface_value.SetValue.assert_not_called()
    with pytest.raises(AutomationError, match="No unique observed option"):
        select_observed_option(app, control("Sampling Mode", "ComboBox"), "fast_monitor")


def test_recording_disconnection_becomes_domain_error() -> None:
    app = MagicMock(spec=Capstone)
    app.snapshot.return_value = snapshot(control("Record", "CheckBox", ".RecordContainer.RecordStartStopButton"))
    toggle = MagicMock()
    type(toggle).CurrentToggleState = PropertyMock(side_effect=COMError(-2147220991, "gone", None))
    app.refs = {"ref": SimpleNamespace(iface_toggle=toggle)}
    with pytest.raises(AutomationError, match="sensor connection") as exc:
        observe_recording(app, 1)
    assert isinstance(exc.value.__cause__, COMError)


def wireless_app(*controls: Control) -> MagicMock:
    app = MagicMock(spec=Capstone)
    toggle = control("Hardware Setup", "CheckBox", ".ObjNameHardware", "toggle")
    app.snapshot.return_value = snapshot(toggle, *controls)
    app.control.return_value.iface_toggle.CurrentToggleState = 1
    app.control.return_value.iface_toggle.ToggleState = 1
    return app


def test_wireless_discovery_observes_delayed_advertisement(monkeypatch: pytest.MonkeyPatch) -> None:
    app = wireless_app()
    initial = app.snapshot.return_value
    found = snapshot(*initial.controls, control("Wireless 123-456", "ListItem"))
    app.snapshot.side_effect = [initial, initial, found, found]
    clock = Clock()
    monkeypatch.setattr(wireless, "time", clock)
    result = wireless.scan_wireless_sensors(app, ScanWirelessSensorsRequest(timeout_seconds=0.2))
    assert result.count == 1
    assert result.sensors[0].sensor_id == "123-456"
    assert clock.now == pytest.approx(0.2)


def test_wireless_already_connected_is_not_toggled() -> None:
    app = wireless_app(control("Wireless 123-456 Connected", "ListItem"))
    result = wireless.connect_wireless_sensor(app, ConnectWirelessSensorRequest(sensor_id="123-456"))
    assert result.connected
    app.click.assert_not_called()


def test_wireless_timeout_never_claims_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    app = wireless_app(control("Wireless 123-456 Disconnected", "ListItem"), control("Connect"))
    clock = Clock()
    monkeypatch.setattr(wireless, "time", clock)
    with pytest.raises(AutomationError, match="not confirmed"):
        wireless.connect_wireless_sensor(app, ConnectWirelessSensorRequest(sensor_id="123-456", timeout_seconds=0.2))
    assert clock.now == pytest.approx(0.2)
    app.click.assert_called_once()


def test_null_nested_payload_still_normalizes_flat_request() -> None:
    payload = {"action": "zero_sensor", "zero_sensor": None, "sensor_name": "Force", "handle": 1}
    result = InstrumentRequest.model_validate(payload)
    assert result.zero_sensor is not None
    assert result.zero_sensor.sensor_name == "Force"
    assert payload["zero_sensor"] is None


@pytest.mark.parametrize("flat", [
    {"sensor_name": "Force", "sampling_rate": "1 kHz"},
    {"sensor": "Force", "target": "1 kHz"},
    {"sensor_name": "Force", "rate_value": 1, "rate_unit": "kHz"},
])
def test_flat_sampling_rate_aliases_match_nested_contract(flat: dict[str, object]) -> None:
    request = InstrumentRequest.model_validate({"action": "set_sampling_rate", "set_sampling_rate": None, **flat})
    assert request.set_sampling_rate is not None
    assert request.set_sampling_rate.sensor == "Force"
    assert request.set_sampling_rate.target == "1 kHz"


def test_unknown_drawer_state_does_not_toggle() -> None:
    app = MagicMock(spec=Capstone)
    app.control.return_value = SimpleNamespace()
    with pytest.raises(AutomationError, match="unobservable"):
        generator._is_drawer_open(app, control("Signal Generator", "CheckBox"))
    app.click.assert_not_called()


def test_ambiguous_wireless_connect_buttons_are_not_guessed() -> None:
    app = wireless_app(
        control("Wireless 123-456 Disconnected", "ListItem"),
        control("Connect", ref="first"), control("Connect", ref="second"),
    )
    with pytest.raises(AutomationError):
        wireless.connect_wireless_sensor(app, ConnectWirelessSensorRequest(sensor_id="123-456"))
    app.click.assert_not_called()

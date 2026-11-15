# Copyright 2026 Capstone MCP contributors.
"""Wireless sensor discovery, pairing, and multi-point calibration tools."""

from __future__ import annotations

import contextlib
import re
import time
from typing import TYPE_CHECKING

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.instruments.models import (
    CALIBRATION_NAME,
    CALIBRATION_TOGGLE_SUFFIX,
    HARDWARE_SETUP_NAME,
    HARDWARE_SETUP_TOGGLE_SUFFIX,
    VALID_CALIBRATIONS,
    CalibrateSensorRequest,
    CalibrateSensorResult,
    ConnectWirelessSensorRequest,
    ConnectWirelessSensorResult,
    ScanWirelessSensorsRequest,
    ScanWirelessSensorsResult,
    WirelessSensorInfo,
)
from capstone_mcp.models import Action

if TYPE_CHECKING:
    from capstone_mcp.models import Control, Snapshot

# ---------------------------------------------------------------------------
# 1. Internal Helpers
# ---------------------------------------------------------------------------


def _find_palette_toggle(
    controls: list[Control],
    name: str,
    suffix: str,
) -> Control:
    n_lower = name.lower()
    for ctrl in controls:
        if (
            ctrl.visible
            and ctrl.control_type == "CheckBox"
            and (
                ctrl.automation_id.endswith(suffix)
                or ctrl.name.strip().lower() == n_lower
                or n_lower in ctrl.name.strip().lower()
            )
        ):
            return ctrl
    msg = f"{name} palette toggle button not found in window snapshot."
    raise AutomationError(msg)


def _is_drawer_open(app: Capstone, toggle_ctrl: Control) -> bool:
    node = app.control(toggle_ctrl.ref)
    with contextlib.suppress(Exception):
        if hasattr(node, "iface_toggle") and node.iface_toggle:
            toggle = node.iface_toggle
            v = getattr(toggle, "ToggleState", None)
            if isinstance(v, int) and v in (0, 1):
                return bool(v == 1)
            v_curr = getattr(toggle, "CurrentToggleState", None)
            if isinstance(v_curr, int) and v_curr in (0, 1):
                return bool(v_curr == 1)
    msg = "Instrument drawer state is unobservable; no toggle was sent."
    raise AutomationError(msg)


def _set_ctrl_value(app: Capstone, handle: int, ctrl: Control, text: str) -> None:
    node = app.control(ctrl.ref)
    try:
        if hasattr(node, "iface_value") and node.iface_value:
            node.iface_value.SetValue(text)
            return
    except (AttributeError, RuntimeError):
        pass

    app.click(handle, ctrl.ref, allow_foreground=True)
    app.keys(handle, "^a{BACKSPACE}")
    app.type_text(text)
    app.keys(handle, "{ENTER}")


def _parse_sensor_id(text: str) -> str:
    match = re.search(r"\b\d{3}-\d{3}\b", text)
    if match:
        return match.group(0)
    match_code = re.search(r"\b(?:PS|EM)-\d+\b", text, re.IGNORECASE)
    if match_code:
        return match_code.group(0)
    return text.strip()


def _parse_battery(text: str) -> int | None:
    match = re.search(r"(\d{1,3})\s*%", text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _is_wireless_item(ctrl: Control) -> bool:
    if not ctrl.visible:
        return False
    combined = f"{ctrl.name} {ctrl.automation_id}".lower()
    return (
        "wireless" in combined
        or "smart cart" in combined
        or "bluetooth" in combined
        or bool(re.search(r"\b\d{3}-\d{3}\b", ctrl.name))
    )


def _extract_sensor_info(ctrl: Control) -> WirelessSensorInfo:
    sensor_id = _parse_sensor_id(ctrl.name)
    battery = _parse_battery(ctrl.name)
    name = ctrl.name.strip()
    lower_name = name.lower()
    lower_auto = ctrl.automation_id.lower()
    is_disconn = "disconnected" in lower_name or "disconnected" in lower_auto
    is_conn = not is_disconn and (
        bool(re.search(r"\bconnected\b", lower_name))
        or bool(re.search(r"\bconnected\b", lower_auto))
    )
    return WirelessSensorInfo(
        sensor_id=sensor_id,
        name=name,
        connected=is_conn,
        battery_percent=battery,
    )


# ---------------------------------------------------------------------------
# 2. Public Operations: Scan & Connect Wireless Sensors
# ---------------------------------------------------------------------------


def scan_wireless_sensors(
    app: Capstone,
    request: ScanWirelessSensorsRequest,
) -> ScanWirelessSensorsResult:
    """Scan and list available Bluetooth wireless sensors in Hardware Setup."""
    if not request.allow_foreground:
        msg = "Wireless sensor scanning requires allow_foreground=true."
        raise AutomationError(msg)

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    toggle = _find_palette_toggle(
        snapshot.controls,
        HARDWARE_SETUP_NAME,
        HARDWARE_SETUP_TOGGLE_SUFFIX,
    )
    was_open = _is_drawer_open(app, toggle)

    opened_by_tool = False
    if not was_open:
        app.click(request.handle, toggle.ref, allow_foreground=True)
        opened_by_tool = True
        snapshot = app.snapshot(request.handle, depth=16, limit=10_000)

    try:
        by_id: dict[str, WirelessSensorInfo] = {}
        deadline = time.monotonic() + request.timeout_seconds
        while True:
            snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
            for ctrl in snapshot.controls:
                if _is_wireless_item(ctrl):
                    info = _extract_sensor_info(ctrl)
                    by_id[info.sensor_id] = info
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.1, remaining))
        sensors = list(by_id.values())

        detail = f"Found {len(sensors)} wireless sensor(s)."
        return ScanWirelessSensorsResult(
            sensors=sensors,
            count=len(sensors),
            verified=True,
            detail=detail,
        )

    finally:
        if opened_by_tool and not request.keep_open:
            fresh = app.snapshot(request.handle, depth=16, limit=10_000)
            current_toggle = _find_palette_toggle(
                fresh.controls,
                HARDWARE_SETUP_NAME,
                HARDWARE_SETUP_TOGGLE_SUFFIX,
            )
            app.click(request.handle, current_toggle.ref, allow_foreground=True)


def _find_target_sensor(controls: list[Control], target_id: str) -> Control | None:
    t_lower = target_id.strip().casefold()
    matches = [
        c
        for c in controls
        if c.visible
        and (
            _parse_sensor_id(c.name).casefold() == t_lower
            or c.name.strip().casefold() == t_lower
            or c.automation_id.casefold() == t_lower
        )
    ]
    return matches[0] if len(matches) == 1 else None


def _find_connect_button(controls: list[Control]) -> Control | None:
    candidates = [
        ctrl for ctrl in controls
        if ctrl.visible and ctrl.control_type == "Button" and ctrl.enabled
        and ctrl.name.strip().lower() in ("connect", "pair")
    ]
    return candidates[0] if len(candidates) == 1 else None


def _await_connected(
    app: Capstone, request: ConnectWirelessSensorRequest, target_id: str,
) -> WirelessSensorInfo:
    """Wait for observed connected state without replaying the pairing input."""
    deadline = time.monotonic() + request.timeout_seconds
    while True:
        snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
        current = _find_target_sensor(snapshot.controls, target_id)
        if current is not None:
            info = _extract_sensor_info(current)
            if info.connected:
                return info
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            msg = "Wireless connection was not confirmed before timeout."
            raise AutomationError(msg)
        time.sleep(min(0.1, remaining))


def connect_wireless_sensor(
    app: Capstone,
    request: ConnectWirelessSensorRequest,
) -> ConnectWirelessSensorResult:
    """Connect/pair a specific wireless sensor by ID or name in Hardware Setup."""
    if not request.allow_foreground:
        msg = "Connecting wireless sensor requires allow_foreground=true."
        raise AutomationError(msg)

    target_id = request.sensor_id.strip()
    if not target_id:
        msg = "sensor_id must not be empty."
        raise AutomationError(msg)

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    toggle = _find_palette_toggle(
        snapshot.controls,
        HARDWARE_SETUP_NAME,
        HARDWARE_SETUP_TOGGLE_SUFFIX,
    )
    was_open = _is_drawer_open(app, toggle)

    opened_by_tool = False
    if not was_open:
        app.click(request.handle, toggle.ref, allow_foreground=True)
        opened_by_tool = True
        snapshot = app.snapshot(request.handle, depth=16, limit=10_000)

    try:
        target_ctrl = _find_target_sensor(snapshot.controls, target_id)
        if not target_ctrl:
            msg = f"Wireless sensor '{request.sensor_id}' not found in Hardware Setup."
            raise AutomationError(msg)

        info = _extract_sensor_info(target_ctrl)
        if not info.connected:
            connect_btn = _find_connect_button(snapshot.controls)
            if connect_btn is None:
                msg = "No explicit Connect/Pair button; sensor toggle is ambiguous."
                raise AutomationError(msg)
            candidates = [c for c in snapshot.controls if _is_wireless_item(c)]
            if len(candidates) > 1:
                _ = app.act(target_ctrl.ref, Action.SELECT, allow_foreground=True)
                snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
                connect_btn = _find_connect_button(snapshot.controls)
                if connect_btn is None:
                    msg = "Connect button disappeared after sensor selection."
                    raise AutomationError(msg)
            opened_by_tool_before_pairing = opened_by_tool
            opened_by_tool = False
            app.click(request.handle, connect_btn.ref, allow_foreground=True)
            info = _await_connected(app, request, target_id)
            opened_by_tool = opened_by_tool_before_pairing
        return ConnectWirelessSensorResult(
            sensor_id=target_id,
            name=info.name,
            connected=True,
            verified=True,
            detail="Connected state observed in Hardware Setup.",
        )

    finally:
        if opened_by_tool and not request.keep_open:
            fresh = app.snapshot(request.handle, depth=16, limit=10_000)
            current_toggle = _find_palette_toggle(
                fresh.controls,
                HARDWARE_SETUP_NAME,
                HARDWARE_SETUP_TOGGLE_SUFFIX,
            )
            app.click(request.handle, current_toggle.ref, allow_foreground=True)


# ---------------------------------------------------------------------------
# 3. Public Operations: Multi-Point Sensor Calibration Wizard
# ---------------------------------------------------------------------------


def _find_wizard_button(controls: list[Control], label: str) -> Control | None:
    l_lower = label.lower()
    for ctrl in controls:
        if (
            ctrl.visible
            and ctrl.control_type == "Button"
            and (l_lower == ctrl.name.strip().lower() or l_lower in ctrl.name.lower())
        ):
            return ctrl
    return None


def _find_wizard_edit(controls: list[Control], index: int = 0) -> Control | None:
    edits = [c for c in controls if c.visible and c.control_type == "Edit"]
    if 0 <= index < len(edits):
        return edits[index]
    return None


def _wizard_select_measurement(
    app: Capstone,
    handle: int,
    label: str,
    snapshot: Snapshot,
) -> Snapshot:
    matches = [ctrl for ctrl in snapshot.controls
               if ctrl.visible and label.casefold() in ctrl.name.casefold()]
    if len(matches) != 1:
        msg = "Calibration measurement was not uniquely identified."
        raise AutomationError(msg)
    app.click(handle, matches[0].ref, allow_foreground=True)
    snapshot = app.snapshot(handle, depth=16, limit=10_000)

    next_btn = _find_wizard_button(snapshot.controls, "Next")
    if next_btn:
        app.click(handle, next_btn.ref, allow_foreground=True)
        return app.snapshot(handle, depth=16, limit=10_000)
    return snapshot


def _wizard_set_standard(
    app: Capstone,
    handle: int,
    value: float,
    snapshot: Snapshot,
) -> Snapshot:
    std_edit = _find_wizard_edit(snapshot.controls, 0)
    if std_edit is None:
        msg = "Calibration standard input was not found."
        raise AutomationError(msg)
    _set_ctrl_value(app, handle, std_edit, str(value))
    snapshot = app.snapshot(handle, depth=16, limit=10_000)

    set_btn = _find_wizard_button(snapshot.controls, "Set")
    if set_btn is None:
        msg = "Calibration Set button was not found."
        raise AutomationError(msg)
    app.click(handle, set_btn.ref, allow_foreground=True)
    snapshot = app.snapshot(handle, depth=16, limit=10_000)

    next_btn = _find_wizard_button(snapshot.controls, "Next")
    if next_btn:
        app.click(handle, next_btn.ref, allow_foreground=True)
        return app.snapshot(handle, depth=16, limit=10_000)
    return snapshot


def _wizard_finish(app: Capstone, handle: int, snapshot: Snapshot) -> None:
    finish_btn = _find_wizard_button(
        snapshot.controls, "Finish",
    ) or _find_wizard_button(snapshot.controls, "Done")
    if finish_btn is None:
        msg = "Calibration Finish button was not found."
        raise AutomationError(msg)
    app.click(handle, finish_btn.ref, allow_foreground=True)


def calibrate_sensor(
    app: Capstone,
    request: CalibrateSensorRequest,
) -> CalibrateSensorResult:
    """Automate multi-point sensor calibration wizard using standard references."""
    if not request.allow_foreground:
        msg = "Sensor calibration requires allow_foreground=true."
        raise AutomationError(msg)

    cal_key = request.calibration_type.strip().lower()
    if cal_key not in VALID_CALIBRATIONS:
        msg = (
            f"Unsupported calibration type '{request.calibration_type}'. "
            f"Supported: two_point, one_point."
        )
        raise AutomationError(msg)
    normalized_cal = VALID_CALIBRATIONS[cal_key]

    if normalized_cal == "two_point" and request.standard_2 is None:
        msg = "standard_2 is required for two_point calibration."
        raise AutomationError(msg)

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    toggle = _find_palette_toggle(
        snapshot.controls,
        CALIBRATION_NAME,
        CALIBRATION_TOGGLE_SUFFIX,
    )
    was_open = _is_drawer_open(app, toggle)

    opened_by_tool = False
    if not was_open:
        app.click(request.handle, toggle.ref, allow_foreground=True)
        opened_by_tool = True
        snapshot = app.snapshot(request.handle, depth=16, limit=10_000)

    try:
        meas_label = request.measurement_type or request.sensor_name
        snapshot = _wizard_select_measurement(
            app,
            request.handle,
            meas_label,
            snapshot,
        )

        snapshot = _wizard_set_standard(
            app,
            request.handle,
            request.standard_1,
            snapshot,
        )

        if normalized_cal == "two_point" and request.standard_2 is not None:
            snapshot = _wizard_set_standard(
                app,
                request.handle,
                request.standard_2,
                snapshot,
            )

        _wizard_finish(app, request.handle, snapshot)

        detail = (
            f"Calibration inputs sent for '{request.sensor_name}' ({normalized_cal}): "
            f"Std1={request.standard_1}"
            + (
                f", Std2={request.standard_2}."
                if request.standard_2 is not None
                else "."
            )
        )

        return CalibrateSensorResult(
            sensor_name=request.sensor_name,
            measurement_type=meas_label,
            calibration_type=normalized_cal,
            standard_1=request.standard_1,
            standard_2=request.standard_2,
            verified=False,
            detail=detail,
        )

    finally:
        if opened_by_tool and not request.keep_open:
            fresh = app.snapshot(request.handle, depth=16, limit=10_000)
            current_toggle = _find_palette_toggle(
                fresh.controls, CALIBRATION_NAME, CALIBRATION_TOGGLE_SUFFIX,
            )
            app.click(request.handle, current_toggle.ref, allow_foreground=True)

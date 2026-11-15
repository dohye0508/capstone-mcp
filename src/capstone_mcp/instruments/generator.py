# Copyright 2026 Capstone MCP contributors.
"""Control waveform and output parameters of Capstone Signal Generator."""

from __future__ import annotations

import contextlib
import math
import re
from typing import TYPE_CHECKING

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.instruments._controls import select_observed_option, selected_text
from capstone_mcp.instruments.models import (
    DEFAULT_GENERATOR_NAME,
    SIGNAL_GENERATOR_NAME,
    SIGNAL_GENERATOR_TOGGLE_SUFFIX,
    VALID_WAVEFORMS,
    ReadSignalGeneratorStatusRequest,
    SetSignalGeneratorRequest,
    SetSignalGeneratorResult,
    SignalGeneratorStatusResult,
)

if TYPE_CHECKING:
    from capstone_mcp.models import Control

# ---------------------------------------------------------------------------
# 1. Internal Helpers
# ---------------------------------------------------------------------------


def _normalize_waveform(raw_waveform: str) -> str:
    """Normalize input waveform string to canonical title case."""
    key = raw_waveform.strip().lower()
    if key in VALID_WAVEFORMS:
        return VALID_WAVEFORMS[key]
    msg = (
        f"Unsupported waveform '{raw_waveform}'. "
        f"Supported waveforms: {', '.join(VALID_WAVEFORMS.values())}."
    )
    raise AutomationError(msg)


def _find_signal_generator_toggle(controls: list[Control]) -> Control:
    """Find the Signal Generator palette toggle button in the active window."""
    for ctrl in controls:
        if (
            ctrl.visible
            and ctrl.control_type == "CheckBox"
            and (
                ctrl.automation_id.endswith(SIGNAL_GENERATOR_TOGGLE_SUFFIX)
                or ctrl.name.strip() == SIGNAL_GENERATOR_NAME
                or "signal generator" in ctrl.name.strip().lower()
            )
        ):
            return ctrl
    msg = "Signal Generator palette toggle button not found in window snapshot."
    raise AutomationError(msg)


def _is_drawer_open(app: Capstone, toggle_ctrl: Control) -> bool:
    """Check if the Signal Generator drawer is currently open."""
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


def _is_power_button(ctrl: Control) -> bool:
    aid_lower = ctrl.automation_id.lower()
    name_lower = ctrl.name.lower()
    return ctrl.control_type in ("Button", "CheckBox") and (
        "power" in aid_lower
        or "onoff" in aid_lower
        or "output_on" in aid_lower
        or name_lower in ("on", "off", "power", "auto")
        or bool(re.search(r"\boutput\s+(?:on|off)\b", name_lower))
    )


def _is_waveform_input(ctrl: Control) -> bool:
    aid_lower = ctrl.automation_id.lower()
    name_lower = ctrl.name.lower()
    return ctrl.control_type in ("ComboBox", "Edit", "List") and (
        "waveform" in aid_lower
        or "wave" in aid_lower
        or "shape" in aid_lower
        or "waveform" in name_lower
    )


def _is_frequency_input(ctrl: Control) -> bool:
    aid_lower = ctrl.automation_id.lower()
    name_lower = ctrl.name.lower()
    return ctrl.control_type == "Edit" and (
        "frequency" in aid_lower
        or "freq" in aid_lower
        or "frequency" in name_lower
        or "freq" in name_lower
    )


def _is_amplitude_input(ctrl: Control) -> bool:
    aid_lower = ctrl.automation_id.lower()
    name_lower = ctrl.name.lower()
    return ctrl.control_type == "Edit" and (
        "amplitude" in aid_lower
        or "voltage" in aid_lower
        or "amp" in aid_lower
        or "amplitude" in name_lower
        or "voltage" in name_lower
        or "amp" in name_lower
    )


def _find_generator_controls(
    controls: list[Control],
) -> tuple[Control | None, Control | None, Control | None, Control | None]:
    """Find power toggle, waveform selector, frequency edit, and amplitude edit."""
    groups = [[c for c in controls if c.visible and predicate(c)]
              for predicate in (_is_power_button, _is_waveform_input,
                                _is_frequency_input, _is_amplitude_input)]
    if any(len(group) > 1 for group in groups):
        msg = "Signal generator controls are ambiguous; select one output manually."
        raise AutomationError(msg)
    found = [group[0] if group else None for group in groups]
    return found[0], found[1], found[2], found[3]


def _set_ctrl_value(app: Capstone, handle: int, ctrl: Control, text: str) -> None:
    """Set text or value in a target control with keyboard fallback."""
    if ctrl.control_type == "ComboBox":
        select_observed_option(app, ctrl, text)
        return
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


def _read_ctrl_value(app: Capstone, ctrl: Control | None) -> str:
    """Read text or value string from a control."""
    if not ctrl:
        return ""
    if ctrl.control_type == "ComboBox":
        return selected_text(app, ctrl)
    node = app.control(ctrl.ref)
    with contextlib.suppress(Exception):
        if hasattr(node, "iface_value") and node.iface_value:
            val = node.iface_value.CurrentValue
            if val is not None:
                return str(val).strip()
    msg = "Control does not expose a readable value; accessible name is not its value."
    raise AutomationError(msg)


def _is_power_on(app: Capstone, power_ctrl: Control | None) -> bool:
    """Determine whether the signal generator output power is currently ON."""
    if not power_ctrl:
        msg = "Signal generator power control was not found."
        raise AutomationError(msg)
    node = app.control(power_ctrl.ref)
    with contextlib.suppress(Exception):
        if hasattr(node, "iface_toggle") and node.iface_toggle:
            toggle = node.iface_toggle
            v = getattr(toggle, "ToggleState", None)
            if isinstance(v, int) and v in (0, 1):
                return bool(v == 1)
            v_curr = getattr(toggle, "CurrentToggleState", None)
            if isinstance(v_curr, int) and v_curr in (0, 1):
                return bool(v_curr == 1)
    name_lower = power_ctrl.name.strip().lower()
    if name_lower in ("on", "running", "active"):
        return True
    if name_lower in ("off", "stopped", "inactive"):
        return False
    msg = "Signal generator power state is unobservable; no toggle was sent."
    raise AutomationError(msg)


def _parse_numeric(text: str) -> float | None:
    """Extract float value from formatted string like '1000 Hz' or '5.0 V'."""
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# 2. Public Operations
# ---------------------------------------------------------------------------


def _configure_values(
    app: Capstone, request: SetSignalGeneratorRequest, waveform: str,
) -> None:
    """Reacquire controls between mutations and require every requested input."""
    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    power_ctrl, wave_ctrl, freq_ctrl, amp_ctrl = _find_generator_controls(
        snapshot.controls,
    )
    if (
        wave_ctrl is None
        or power_ctrl is None
        or (request.frequency is not None and freq_ctrl is None)
        or (request.amplitude is not None and amp_ctrl is None)
    ):
        msg = "Required signal generator controls are unavailable."
        raise AutomationError(msg)
    _set_ctrl_value(app, request.handle, wave_ctrl, waveform)

    for index, value in ((2, request.frequency), (3, request.amplitude)):
        if value is None:
            continue
        fresh = app.snapshot(request.handle, depth=16, limit=10_000)
        ctrl = _find_generator_controls(fresh.controls)[index]
        if ctrl is None:
            msg = "Signal generator input disappeared after configuration."
            raise AutomationError(msg)
        _set_ctrl_value(app, request.handle, ctrl, str(value))


def set_signal_generator(
    app: Capstone,
    request: SetSignalGeneratorRequest,
) -> SetSignalGeneratorResult:
    """Configure signal generator waveform, frequency, amplitude, and output power."""
    if not request.allow_foreground:
        msg = "Signal Generator operation requires allow_foreground=true."
        raise AutomationError(msg)

    waveform = _normalize_waveform(request.waveform)
    if request.frequency is not None and request.frequency < 0:
        msg = "Frequency must be non-negative."
        raise AutomationError(msg)

    if any(
        v is not None and not math.isfinite(v)
        for v in (request.frequency, request.amplitude)
    ):
        msg = "Frequency and amplitude must be finite."
        raise AutomationError(msg)
    generator_name = request.generator_name or DEFAULT_GENERATOR_NAME

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    toggle_ctrl = _find_signal_generator_toggle(snapshot.controls)
    was_open = _is_drawer_open(app, toggle_ctrl)

    opened_by_tool = False
    if not was_open:
        app.click(request.handle, toggle_ctrl.ref, allow_foreground=True)
        opened_by_tool = True
        snapshot = app.snapshot(request.handle, depth=16, limit=10_000)

    try:
        power_ctrl, wave_ctrl, freq_ctrl, amp_ctrl = _find_generator_controls(
            snapshot.controls,
        )

        _configure_values(app, request, waveform)

        fresh = app.snapshot(request.handle, depth=16, limit=10_000)
        power_ctrl = _find_generator_controls(fresh.controls)[0]
        if power_ctrl:
            current_on = _is_power_on(app, power_ctrl)
            if current_on != request.enabled:
                app.click(request.handle, power_ctrl.ref, allow_foreground=True)

        fresh = app.snapshot(request.handle, depth=16, limit=10_000)
        power_ctrl, wave_ctrl, freq_ctrl, amp_ctrl = _find_generator_controls(
            fresh.controls,
        )
        verified = (
            _is_power_on(app, power_ctrl) == request.enabled
            and _read_ctrl_value(app, wave_ctrl).casefold() == waveform.casefold()
            and (
                request.frequency is None
                or _parse_numeric(_read_ctrl_value(app, freq_ctrl)) == request.frequency
            )
            and (
                request.amplitude is None
                or _parse_numeric(_read_ctrl_value(app, amp_ctrl)) == request.amplitude
            )
        )
        detail = (
            f"Signal Generator '{generator_name}' input delivered: "
            f"Waveform={waveform}, Freq={request.frequency}Hz, "
            f"Amp={request.amplitude}V, Power={'On' if request.enabled else 'Off'}."
        )

        return SetSignalGeneratorResult(
            generator_name=generator_name,
            waveform=waveform,
            frequency=request.frequency,
            amplitude=request.amplitude,
            enabled=request.enabled,
            verified=verified,
            detail=detail,
        )

    finally:
        if opened_by_tool and not request.keep_open:
            fresh = app.snapshot(request.handle, depth=16, limit=10_000)
            current_toggle = _find_signal_generator_toggle(fresh.controls)
            app.click(request.handle, current_toggle.ref, allow_foreground=True)


def read_signal_generator_status(
    app: Capstone,
    request: ReadSignalGeneratorStatusRequest,
) -> SignalGeneratorStatusResult:
    """Read waveform, frequency, amplitude, and power state of Signal Generator."""
    if not request.allow_foreground:
        msg = "Signal Generator operation requires allow_foreground=true."
        raise AutomationError(msg)

    generator_name = request.generator_name or DEFAULT_GENERATOR_NAME

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    toggle_ctrl = _find_signal_generator_toggle(snapshot.controls)
    was_open = _is_drawer_open(app, toggle_ctrl)

    opened_by_tool = False
    if not was_open:
        app.click(request.handle, toggle_ctrl.ref, allow_foreground=True)
        opened_by_tool = True
        snapshot = app.snapshot(request.handle, depth=16, limit=10_000)

    try:
        power_ctrl, wave_ctrl, freq_ctrl, amp_ctrl = _find_generator_controls(
            snapshot.controls,
        )

        enabled = _is_power_on(app, power_ctrl)
        raw_wave = _read_ctrl_value(app, wave_ctrl)
        raw_freq = _read_ctrl_value(app, freq_ctrl)
        raw_amp = _read_ctrl_value(app, amp_ctrl)

        waveform = raw_wave or "Sine"
        freq_val = _parse_numeric(raw_freq)
        amp_val = _parse_numeric(raw_amp)

        detail = (
            f"Signal Generator '{generator_name}' status: "
            f"Power={'On' if enabled else 'Off'}, Waveform={waveform}, "
            f"Freq={freq_val}Hz, Amp={amp_val}V."
        )

        return SignalGeneratorStatusResult(
            generator_name=generator_name,
            enabled=enabled,
            waveform=waveform,
            frequency=freq_val,
            amplitude=amp_val,
            verified=True,
            detail=detail,
        )

    finally:
        if opened_by_tool and not request.keep_open:
            fresh = app.snapshot(request.handle, depth=16, limit=10_000)
            current_toggle = _find_signal_generator_toggle(fresh.controls)
            app.click(request.handle, current_toggle.ref, allow_foreground=True)

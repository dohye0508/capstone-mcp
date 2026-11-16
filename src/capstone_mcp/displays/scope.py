# Copyright 2026 Capstone MCP contributors.
"""Oscilloscope and FFT frequency spectrum display tools in Capstone."""

from __future__ import annotations

import math
import re
from _ctypes import COMError
from typing import TYPE_CHECKING, Final

from pywinauto.uia_defines import NoPatternInterfaceError

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.displays.harness import (
    double_click_control,
    find_palette_item,
)
from capstone_mcp.displays.models import (
    FFT_PALETTE_SUFFIX,
    SCOPE_PALETTE_SUFFIX,
    VALID_MODES,
    VALID_SLOPES,
    CreateFftRequest,
    CreateFftResult,
    CreateScopeRequest,
    CreateScopeResult,
    FftPeak,
    ReadFftPeaksRequest,
    ReadFftPeaksResult,
    ScopeTriggerResult,
    SetScopeTriggerRequest,
)

if TYPE_CHECKING:
    from capstone_mcp.models import Control, Snapshot

_PEAK_NUMBER: Final = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?"
_PEAK_FREQUENCY: Final = rf"({_PEAK_NUMBER})\s*(kHz|Hz)?"
_PEAK_AMPLITUDE: Final = rf"({_PEAK_NUMBER})\s*(mV|V|dB)?"
_WIDGET_TITLES: Final = {
    "Scope": re.compile(r"(?:scope|oscilloscope)(?:\s*#?\d+)?", re.IGNORECASE),
    "FFT": re.compile(r"(?:fft|spectrum analyzer)(?:\s*#?\d+)?", re.IGNORECASE),
}
_VALUE_ERRORS = (AttributeError, COMError, NoPatternInterfaceError, RuntimeError)
type Settings = tuple[tuple[tuple[str, ...], str | None], ...]


def _widgets(snapshot: Snapshot, kind: str) -> list[Control]:
    if snapshot.truncated:
        return []
    page_refs = {
        c.ref for c in snapshot.controls
        if c.visible and c.automation_id.endswith(".PageView")
    }
    return [
        c for c in _descendants(snapshot, page_refs)
        if c.control_type in {"Custom", "Group", "Pane"}
        and _WIDGET_TITLES[kind].fullmatch(c.name.strip())
    ]


def _descendants(snapshot: Snapshot, refs: set[str]) -> list[Control]:
    # Full snapshots are in depth-first order, so parents precede children.
    result: list[Control] = []
    for c in snapshot.controls:
        if c.visible and c.parent in refs:
            refs.add(c.ref)
            result.append(c)
    return result


def _widget_id(widget: Control) -> str:
    return widget.automation_id or widget.name.strip()


def _widget(snapshot: Snapshot, kind: str, identifier: str | None) -> Control:
    widgets = [
        c for c in _widgets(snapshot, kind)
        if identifier is None or identifier in {_widget_id(c), c.name.strip()}
    ]
    if len(widgets) != 1:
        msg = f"Expected one identifiable {kind} widget on the visible workbook page."
        raise AutomationError(msg)
    return widgets[0]


def _matches_setting(ctrl: Control, aliases: tuple[str, ...]) -> bool:
    if not ctrl.enabled:
        return False
    names = (ctrl.name, ctrl.automation_id.rsplit(".", 1)[-1])
    return any(re.sub(r"[\W_]+", "", name.casefold()) in aliases for name in names)


def _write_settings(
    app: Capstone, snapshot: Snapshot, widget: Control, settings: Settings,
) -> bool:
    controls = _descendants(snapshot, {widget.ref})
    writes = []
    for aliases, value in settings:
        if value is None:
            continue
        candidates = [c for c in controls if _matches_setting(c, aliases)]
        msg = f"{widget.name} does not expose one writable {aliases[0]} control."
        if len(candidates) != 1:
            raise AutomationError(msg)
        try:
            pattern = app.control(candidates[0].ref).iface_value
            if pattern.CurrentIsReadOnly:
                raise AutomationError(msg)
        except _VALUE_ERRORS as exc:
            raise AutomationError(msg) from exc
        writes.append((pattern, value))

    if not writes:
        return True
    app.require_input_ready(snapshot.window.handle)
    try:
        for pattern, value in writes:
            pattern.SetValue(value)
        return all(
            pattern.CurrentValue.strip().casefold() == value.strip().casefold()
            for pattern, value in writes
        )
    except _VALUE_ERRORS as exc:
        msg = "A display setting may have changed; inspect the widget before retrying."
        raise AutomationError(msg) from exc
    finally:
        app.refs.clear()


def _insert_widget(
    app: Capstone, handle: int, kind: str, palette_suffix: str, settings: Settings,
) -> tuple[str | None, bool, str]:
    before = app.snapshot(handle, depth=20, limit=10_000)
    existing = {_widget_id(widget) for widget in _widgets(before, kind)}
    palette = find_palette_item(before.controls, kind, palette_suffix)
    double_click_control(app, before.window.handle, palette)
    after = app.snapshot(before.window.handle, depth=20, limit=10_000)
    widgets = _widgets(after, kind)
    new = [widget for widget in widgets if _widget_id(widget) not in existing]
    if before.truncated or len(new) != 1:
        return None, False, (
            f"{kind} palette input sent. Inspect the page before retrying; "
            "the new widget could not be identified and no settings were applied."
        )
    identifier = _widget_id(new[0])
    try:
        verified = _write_settings(app, after, new[0], settings)
    except AutomationError as exc:
        return identifier, False, f"{kind} '{identifier}' is visible. {exc}"
    if verified:
        return identifier, True, f"{kind} '{identifier}' is visible."
    return identifier, False, f"{kind} '{identifier}' settings could not be verified."


def create_scope(
    app: Capstone,
    request: CreateScopeRequest | None = None,
) -> CreateScopeResult:
    """Insert an oscilloscope display onto the page and optionally configure it."""
    if request is None:
        request = CreateScopeRequest()

    if not request.allow_foreground:
        msg = "Scope creation requires allow_foreground=true."
        raise AutomationError(msg)

    timebase_str = str(request.timebase) if request.timebase is not None else None
    display_id, verified, detail = _insert_widget(
        app, request.handle, "Scope", SCOPE_PALETTE_SUFFIX,
        (
            (("timebase", "timebaseedit", "secdiv"), timebase_str),
            (("channel", "channelselector", "measurementselector"), request.channel),
        ),
    )
    return CreateScopeResult(
        display_id=display_id,
        display_type="Scope",
        timebase=timebase_str if verified else None,
        channel=request.channel if verified else None,
        verified=verified,
        detail=detail,
    )


def set_scope_trigger(
    app: Capstone,
    request: SetScopeTriggerRequest,
) -> ScopeTriggerResult:
    """Configure oscilloscope trigger level, slope, and mode."""
    if not request.allow_foreground:
        msg = "Oscilloscope trigger configuration requires allow_foreground=true."
        raise AutomationError(msg)

    normalized_slope = VALID_SLOPES.get(request.trigger_slope.lower())
    if not normalized_slope:
        valid = list(VALID_SLOPES.keys())
        msg = (
            f"Unsupported trigger slope "
            f"'{request.trigger_slope}'. Valid: {valid}"
        )
        raise AutomationError(msg)

    normalized_mode = VALID_MODES.get(request.trigger_mode.lower())
    if not normalized_mode:
        valid = list(VALID_MODES.keys())
        msg = (
            f"Unsupported trigger mode "
            f"'{request.trigger_mode}'. Valid: {valid}"
        )
        raise AutomationError(msg)

    snapshot = app.snapshot(request.handle, depth=20, limit=10_000)
    widget = _widget(snapshot, "Scope", request.scope_id)
    scope_id = _widget_id(widget)
    verified = _write_settings(
        app, snapshot, widget,
        (
            (("triggerlevel",), str(request.trigger_level)),
            (("triggerslope",), normalized_slope),
            (("triggermode",), normalized_mode),
            (("triggersource",), request.trigger_source),
        ),
    )

    detail = (
        f"Scope '{scope_id}' trigger settings verified." if verified
        else f"Scope '{scope_id}' trigger values could not be verified."
    )
    return ScopeTriggerResult(
        scope_id=scope_id,
        trigger_level=request.trigger_level,
        trigger_slope=normalized_slope,
        trigger_mode=normalized_mode,
        trigger_source=request.trigger_source,
        verified=verified,
        detail=detail,
    )


def create_fft(
    app: Capstone,
    request: CreateFftRequest | None = None,
) -> CreateFftResult:
    """Insert an FFT frequency spectrum display onto the active page."""
    if request is None:
        request = CreateFftRequest()

    if not request.allow_foreground:
        msg = "FFT creation requires allow_foreground=true."
        raise AutomationError(msg)

    display_id, verified, detail = _insert_widget(
        app, request.handle, "FFT", FFT_PALETTE_SUFFIX,
        (
            (("measurement", "measurementselector", "channel"), request.measurement),
            (("frequencyrange", "freqrangeedit", "span"), request.frequency_range),
        ),
    )
    return CreateFftResult(
        display_id=display_id,
        display_type="FFT",
        measurement=request.measurement if verified else None,
        frequency_range=request.frequency_range if verified else None,
        verified=verified,
        detail=detail,
    )


def _parse_peak_text(text: str) -> FftPeak | None:
    """Parse FFT coordinates or named frequency and amplitude labels."""
    text = text.replace("\u2212", "-")
    match = re.search(
        rf"\(\s*{_PEAK_FREQUENCY}\s*,\s*{_PEAK_AMPLITUDE}\s*\)",
        text,
        re.IGNORECASE,
    )
    if match is None:
        match = re.search(
            rf"\b(?:freq(?:uency)?|f)\s*[:=]\s*{_PEAK_FREQUENCY}(?![\w.]).*?"
            rf"\bamp(?:litude)?\s*[:=]\s*{_PEAK_AMPLITUDE}(?![\w.])",
            text,
            re.IGNORECASE,
        )
    if match is None:
        return None
    frequency, frequency_unit, amplitude, amplitude_unit = match.groups(default="")
    frequency_hz = float(frequency) * (1000 if frequency_unit.lower() == "khz" else 1)
    magnitude = float(amplitude)
    if (
        frequency_hz < 0
        or not math.isfinite(frequency_hz)
        or not math.isfinite(magnitude)
    ):
        return None
    unit = amplitude_unit.lower()
    if unit == "mv":
        magnitude /= 1000
    return FftPeak(
        frequency_hz=frequency_hz,
        amplitude=magnitude,
        amplitude_unit="dB" if unit == "db" else "V" if unit else None,
    )


def read_fft_peaks(
    app: Capstone,
    request: ReadFftPeaksRequest | None = None,
) -> ReadFftPeaksResult:
    """Extract top peak frequencies and amplitudes from the FFT display."""
    if request is None:
        request = ReadFftPeaksRequest()

    if not request.allow_foreground:
        msg = "FFT peak reading requires allow_foreground=true."
        raise AutomationError(msg)

    if request.top_k < 1:
        msg = "FFT top_k must be positive."
        raise AutomationError(msg)
    snapshot = app.snapshot(request.handle, depth=20, limit=10_000)
    widget = _widget(snapshot, "FFT", request.fft_id)
    fft_id = _widget_id(widget)

    peaks: list[FftPeak] = []
    seen: set[float] = set()

    for ctrl in _descendants(snapshot, {widget.ref}):
        text = ctrl.name.strip()
        peak = _parse_peak_text(text)
        if peak is not None and peak.frequency_hz not in seen:
            seen.add(peak.frequency_hz)
            peaks.append(peak)

    if len({p.amplitude_unit for p in peaks}) > 1:
        msg = "FFT peak amplitudes have different or unknown units."
        raise AutomationError(msg)
    if request.min_amplitude is not None:
        peaks = [p for p in peaks if p.amplitude >= request.min_amplitude]
    peaks.sort(key=lambda p: p.amplitude, reverse=True)
    top_peaks = peaks[: request.top_k]

    detail = (
        f"Extracted {len(top_peaks)} FFT peak(s) from '{fft_id}'."
        if top_peaks
        else f"No peak coordinates detected in '{fft_id}'."
    )

    return ReadFftPeaksResult(
        fft_id=fft_id,
        peaks=top_peaks,
        peak_count=len(top_peaks),
        verified=True,
        detail=detail,
    )

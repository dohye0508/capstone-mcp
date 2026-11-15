# Copyright 2026 Capstone MCP contributors.
"""Digits display creation and live numerical monitoring."""

from __future__ import annotations

import contextlib
import re
from typing import TYPE_CHECKING

from pywinauto.uia_defines import NoPatternInterfaceError

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.displays.harness import (
    click_control,
    find_display_container,
    find_palette_item,
    is_within_bounds,
)
from capstone_mcp.displays.models import (
    DIGITS_PALETTE_NAME,
    FLOAT_PATTERN,
    CreateDigitsRequest,
    CreateDigitsResult,
)

if TYPE_CHECKING:
    from capstone_mcp.models import Control

MAX_UNIT_STR_LEN = 10


def _find_digits_palette_item(controls: list[Control]) -> Control:
    """Find Digits display item in the Displays palette."""
    return find_palette_item(controls, DIGITS_PALETTE_NAME, ".ObjNameDigits")


def _find_digits_control(
    controls: list[Control],
    digits_name: str | None = None,
) -> Control:
    """Locate the target Digits widget container in the active window."""
    return find_display_container(controls, "digits", digits_name)


def _find_measurement_selector(
    controls: list[Control],
    digits_ctrl: Control,
) -> Control | None:
    """Find the measurement selector button inside the Digits widget."""
    for c in controls:
        if not c.visible or c.ref == digits_ctrl.ref:
            continue
        if not is_within_bounds(c, digits_ctrl):
            continue
        name_lower = c.name.strip().lower()
        aid_lower = c.automation_id.lower()
        if (
            "select measurement" in name_lower
            or "measurement" in aid_lower
            or "datasource" in aid_lower
        ):
            return c
    return None


def _extract_digits_value_and_unit(
    controls: list[Control],
    digits_ctrl: Control,
) -> tuple[float | None, str | None]:
    """Read the current numeric readout and engineering unit from Digits display."""
    b = digits_ctrl.bounds
    found_value: float | None = None
    found_unit: str | None = None

    for c in controls:
        if not c.visible or c.ref == digits_ctrl.ref:
            continue
        if not (
            c.bounds.top >= b.top
            and c.bounds.bottom <= b.bottom
            and c.bounds.left >= b.left
            and c.bounds.right <= b.right
        ):
            continue

        text = c.name.strip().replace("\u2212", "-")
        if not text:
            continue

        # Check if text is a purely numeric readout
        if FLOAT_PATTERN.match(text):
            with contextlib.suppress(ValueError):
                found_value = float(text)
                continue

        # Check combined text like "12.34 m/s"
        combined_match = re.match(
            r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([A-Za-z°%µΩ/·^-]+)?$",
            text,
        )
        if combined_match:
            with contextlib.suppress(ValueError):
                found_value = float(combined_match.group(1))
            if combined_match.group(2):
                found_unit = combined_match.group(2).strip()
            continue

        # Unit candidate (short text like 'm/s', 'N', 'V', 'Hz')
        if (
            c.control_type in ("Text", "Custom")
            and len(text) <= MAX_UNIT_STR_LEN
            and "select" not in text.lower()
            and not found_unit
        ):
            found_unit = text

    return found_value, found_unit


def create_digits(
    app: Capstone,
    request: CreateDigitsRequest | None = None,
) -> CreateDigitsResult:
    """Insert a Digits display into the active page and bind target measurement."""
    if request is None:
        request = CreateDigitsRequest()

    if not request.allow_foreground:
        msg = "Digits display creation requires allow_foreground=true."
        raise AutomationError(msg)

    # 1. Locate and activate Digits palette item
    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    palette_item = _find_digits_palette_item(snapshot.controls)
    before = snapshot

    click_control(
        app,
        request.handle,
        palette_item,
        double=True,
        allow_foreground=True,
    )

    # 2. Take fresh snapshot to locate the inserted Digits display
    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    try:
        digits_ctrl = _find_digits_control(snapshot.controls, request.digits_name)
    except AutomationError as exc:
        return CreateDigitsResult(
            created=False,
            verified=False,
            detail=f"Digits insertion requested. Inspect before retrying. {exc}",
        )
    if before.truncated or snapshot.truncated or any(
        (c.automation_id, c.name, c.control_type)
        == (digits_ctrl.automation_id, digits_ctrl.name, digits_ctrl.control_type)
        for c in before.controls
    ):
        return CreateDigitsResult(
            created=False,
            verified=False,
            detail="Could not identify a new Digits widget. Inspect before retrying.",
        )

    # 3. Bind measurement if requested
    measurement = None
    if request.measurement:
        selector = _find_measurement_selector(snapshot.controls, digits_ctrl)
        if selector and selector.enabled:
            with contextlib.suppress(NoPatternInterfaceError):
                _ = app.set_value(selector.ref, request.measurement)
            snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
            digits_ctrl = _find_digits_control(snapshot.controls, request.digits_name)
            selected = _find_measurement_selector(snapshot.controls, digits_ctrl)
            if selected and selected.name.strip() == request.measurement.strip():
                measurement = selected.name.strip()

    # 4. Read bound numerical value and unit
    val, unit = _extract_digits_value_and_unit(snapshot.controls, digits_ctrl)

    d_name = request.digits_name or digits_ctrl.name or "Digits"
    verified = request.measurement is None or measurement is not None
    meas_info = f" bound to '{measurement}'" if measurement else ""
    val_info = f" with value {val} {unit or ''}".rstrip() if val is not None else ""
    detail = f"Digits display '{d_name}' created{meas_info}{val_info}."
    if not verified:
        detail += f" Could not verify measurement {request.measurement!r}."

    return CreateDigitsResult(
        created=True,
        digits_name=d_name,
        measurement=measurement,
        current_value=val if verified else None,
        unit=unit if verified else None,
        verified=verified,
        detail=detail,
    )

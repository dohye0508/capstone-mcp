# Copyright 2026 Capstone MCP contributors.
"""Tests for high-level Digits display creation and monitoring tool."""

from unittest.mock import MagicMock

import pytest

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.displays import (
    CreateDigitsRequest,
    CreateDigitsResult,
    DisplayAction,
    DisplayRequest,
    DisplayResult,
    manage_display,
)
from capstone_mcp.models import Bounds, Control, Snapshot, Window


def _mock_window(handle: int = 100) -> Window:
    return Window(
        handle=handle,
        title="Capstone",
        process_id=1,
        bounds=Bounds(left=0, top=0, right=1200, bottom=900),
    )


def test_create_digits_refuses_disabled_foreground() -> None:
    app = Capstone()
    req = DisplayRequest(
        action=DisplayAction.CREATE_DIGITS,
        create_digits=CreateDigitsRequest(handle=100, allow_foreground=False),
    )
    with pytest.raises(AutomationError, match="allow_foreground=true"):
        manage_display(app, req)


def test_create_digits_raises_when_palette_missing() -> None:
    app = Capstone()
    mock_win = _mock_window()
    app.snapshot = MagicMock(
        return_value=Snapshot(
            window=mock_win,
            controls=[
                Control(
                    ref="ref:other",
                    parent=None,
                    name="Graph",
                    control_type="Text",
                    automation_id="Palette.Graph",
                    enabled=True,
                    visible=True,
                    bounds=Bounds(left=10, top=10, right=50, bottom=50),
                ),
            ],
            truncated=False,
        ),
    )
    with pytest.raises(AutomationError, match="Digits display palette item not found"):
        manage_display(
            app,
            DisplayRequest(
                action=DisplayAction.CREATE_DIGITS,
                create_digits=CreateDigitsRequest(handle=100),
            ),
        )


def test_create_digits_success_without_binding() -> None:
    app = Capstone()
    mock_win = _mock_window()

    palette_item = Control(
        ref="ref:digits_palette",
        parent=None,
        name="Digits",
        control_type="Text",
        automation_id="Palette.ObjNameDigits",
        enabled=True,
        visible=True,
        bounds=Bounds(left=10, top=200, right=60, bottom=230),
    )
    digits_ctrl = Control(
        ref="ref:digits_widget",
        parent=None,
        name="Digits 1",
        control_type="Custom",
        automation_id="DigitsDisplay",
        enabled=True,
        visible=True,
        bounds=Bounds(left=100, top=100, right=400, bottom=300),
    )
    value_text = Control(
        ref="ref:val",
        parent="ref:digits_widget",
        name="0.00",
        control_type="Text",
        automation_id="DisplayValue",
        enabled=True,
        visible=True,
        bounds=Bounds(left=120, top=140, right=300, bottom=220),
    )

    call_count = 0

    def mock_snapshot(*_args: object, **_kwargs: object) -> Snapshot:
        nonlocal call_count
        call_count += 1
        ctrls = [palette_item]
        if call_count > 1:
            ctrls.extend([digits_ctrl, value_text])
        return Snapshot(window=mock_win, controls=ctrls, truncated=False)

    app.snapshot = mock_snapshot
    app.click = MagicMock()

    display_res = manage_display(
        app,
        DisplayRequest(
            action=DisplayAction.CREATE_DIGITS,
            create_digits=CreateDigitsRequest(handle=100),
        ),
    )

    assert isinstance(display_res, DisplayResult)
    assert isinstance(display_res.create_digits, CreateDigitsResult)
    res = display_res.create_digits
    assert res.created is True
    assert res.digits_name == "Digits 1"
    assert res.current_value == 0.0
    assert res.verified is True
    app.click.assert_called_once_with(
        100, "ref:digits_palette", double=True, allow_foreground=True,
    )


def test_create_digits_does_not_verify_palette_as_a_new_widget() -> None:
    app = Capstone()
    bounds = Bounds(left=0, top=0, right=20, bottom=20)
    controls = [
        Control(
            ref="page", parent=None, name="", control_type="Group",
            automation_id="Workbook.PageView", enabled=True, visible=True, bounds=bounds,
        ),
        Control(
            ref="page-child", parent="page", name="", control_type="Group",
            automation_id="", enabled=True, visible=True, bounds=bounds,
        ),
        Control(
            ref="palette-group", parent=None, name="", control_type="Group",
            automation_id="CSDataDigits", enabled=True, visible=True, bounds=bounds,
        ),
        Control(
            ref="palette-text", parent="palette-group", name="Digits", control_type="Text",
            automation_id="", enabled=True, visible=True, bounds=bounds,
        ),
    ]
    app.snapshot = MagicMock(return_value=Snapshot(
        window=_mock_window(), controls=controls, truncated=False,
    ))
    app.click = MagicMock()

    result = manage_display(app, DisplayRequest(
        action=DisplayAction.CREATE_DIGITS,
        create_digits=CreateDigitsRequest(handle=100, measurement="Acceleration"),
    )).create_digits

    assert result is not None
    assert result.verified is False
    assert result.measurement is None
    app.click.assert_called_once_with(100, "palette-text", double=True, allow_foreground=True)


@pytest.mark.parametrize("binding_applied", [True, False])
def test_create_digits_confirms_measurement_and_unit(*, binding_applied: bool) -> None:
    app = Capstone()
    mock_win = _mock_window()

    palette_item = Control(
        ref="ref:digits_palette",
        parent=None,
        name="Digits",
        control_type="Text",
        automation_id="Palette.ObjNameDigits",
        enabled=True,
        visible=True,
        bounds=Bounds(left=10, top=200, right=60, bottom=230),
    )
    digits_ctrl = Control(
        ref="ref:digits_widget",
        parent=None,
        name="Digits",
        control_type="Custom",
        automation_id="DigitsDisplay",
        enabled=True,
        visible=True,
        bounds=Bounds(left=100, top=100, right=500, bottom=350),
    )
    selector = Control(
        ref="ref:selector",
        parent="ref:digits_widget",
        name="<Select Measurement>",
        control_type="Button",
        automation_id="MeasurementSelector",
        enabled=True,
        visible=True,
        bounds=Bounds(left=110, top=110, right=280, bottom=135),
    )
    value_text = Control(
        ref="ref:val",
        parent="ref:digits_widget",
        name="9.81",
        control_type="Text",
        automation_id="DisplayValue",
        enabled=True,
        visible=True,
        bounds=Bounds(left=150, top=150, right=350, bottom=260),
    )
    unit_text = Control(
        ref="ref:unit",
        parent="ref:digits_widget",
        name="m/s^2",
        control_type="Text",
        automation_id="DisplayUnit",
        enabled=True,
        visible=True,
        bounds=Bounds(left=360, top=200, right=450, bottom=240),
    )

    call_count = 0

    def mock_snapshot(*_args: object, **_kwargs: object) -> Snapshot:
        nonlocal call_count
        call_count += 1
        ctrls = [palette_item]
        if call_count > 1:
            ctrls.extend([digits_ctrl, selector, value_text, unit_text])
        return Snapshot(window=mock_win, controls=ctrls, truncated=False)

    app.snapshot = mock_snapshot
    app.click = MagicMock()
    app.keys = MagicMock()

    mock_node = MagicMock()

    def bind_measurement(name: str) -> None:
        nonlocal selector
        if binding_applied:
            selector = selector.model_copy(update={"name": name})

    mock_node.iface_value.SetValue.side_effect = bind_measurement
    app.control = MagicMock(return_value=mock_node)

    display_res = manage_display(
        app,
        DisplayRequest(
            action=DisplayAction.CREATE_DIGITS,
            create_digits=CreateDigitsRequest(
                handle=100,
                measurement="Acceleration (m/s^2)",
            ),
        ),
    )

    assert isinstance(display_res, DisplayResult)
    assert isinstance(display_res.create_digits, CreateDigitsResult)
    res = display_res.create_digits
    assert res.created is True
    assert res.digits_name == "Digits"
    assert res.measurement == ("Acceleration (m/s^2)" if binding_applied else None)
    assert res.current_value == (9.81 if binding_applied else None)
    assert res.unit == ("m/s^2" if binding_applied else None)
    assert res.verified is binding_applied
    assert app.click.call_count == 1

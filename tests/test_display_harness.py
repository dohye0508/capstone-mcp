# Copyright 2026 Capstone MCP contributors.
"""Unit tests for the consolidated DisplayHarness module."""

from unittest.mock import MagicMock, patch

import pytest

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.displays import (
    DisplayHarness,
    click_control,
    double_click_control,
    drag_control,
    find_display_container,
    find_display_containers,
    find_palette_item,
    is_within_bounds,
    set_control_value,
)
from capstone_mcp.models import Bounds, Control


def _make_control(
    ref: str,
    name: str,
    control_type: str = "Custom",
    automation_id: str = "",
    bounds: Bounds | None = None,
) -> Control:
    return Control(
        ref=ref,
        parent=None,
        name=name,
        control_type=control_type,
        automation_id=automation_id or f"id:{ref}",
        enabled=True,
        visible=True,
        bounds=bounds or Bounds(left=10, top=10, right=100, bottom=100),
    )


# ---------------------------------------------------------------------------
# Click and Double-Click Fallback Tests
# ---------------------------------------------------------------------------


def test_click_via_app_click() -> None:
    app = Capstone()
    app.click = MagicMock()
    ctrl = _make_control("ref:1", "Button 1")

    click_control(app, 100, ctrl, allow_foreground=True)

    app.click.assert_called_once_with(100, "ref:1", allow_foreground=True)


def test_double_click_reaches_guarded_desktop_input() -> None:
    app = Capstone()
    mock_node = MagicMock()
    mock_node.rectangle.return_value = Bounds(left=0, top=0, right=100, bottom=100)
    app.control = MagicMock(return_value=mock_node)
    app.require_foreground = MagicMock()
    ctrl = _make_control(
        "ref:1",
        "Palette Item",
        bounds=Bounds(left=0, top=0, right=100, bottom=100),
    )

    with (
        patch("capstone_mcp.desktop.win32gui.IsWindowEnabled", return_value=True),
        patch("capstone_mcp.desktop.HwndWrapper") as hwnd,
    ):
        double_click_control(app, 100, ctrl)

    hwnd.return_value.set_focus.assert_called_once()
    app.require_foreground.assert_called_once()
    mock_node.click_input.assert_called_once_with(
        button="left",
        double=True,
        coords=(50, 50),
        absolute=True,
    )


def test_click_failure_does_not_retry() -> None:
    app = Capstone()
    app.click = MagicMock(side_effect=AutomationError("input failed"))
    ctrl = _make_control("ref:1", "Button 1")

    with pytest.raises(AutomationError, match="input failed"):
        click_control(app, 100, ctrl)

    app.click.assert_called_once_with(100, "ref:1", allow_foreground=True)


# ---------------------------------------------------------------------------
# Drag and Value Setting Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fails", [False, True])
def test_drag_uses_current_geometry_without_click_fallback(*, fails: bool) -> None:
    app = Capstone()
    source = _make_control("ref:src", "Palette Item")
    target = _make_control("ref:dst", "Layout Area")
    source_node, target_node, window = MagicMock(), MagicMock(), MagicMock()
    source_node.rectangle.return_value = Bounds(left=100, top=10, right=200, bottom=40)
    target_node.rectangle.return_value = Bounds(left=200, top=200, right=400, bottom=400)
    window.rectangle.return_value = Bounds(left=0, top=0, right=500, bottom=500)
    app.refs.update({source.ref: source_node, target.ref: target_node})
    app.control = MagicMock(side_effect=app.refs.__getitem__)
    app.owning_window = MagicMock(return_value=100)
    app.focus_window = MagicMock(return_value=window)
    app.require_uncovered = MagicMock()
    app.click = MagicMock()

    if fails:
        window.drag_mouse_input.side_effect = AutomationError("drag failed")
        with pytest.raises(AutomationError, match="drag failed"):
            drag_control(app, 100, source, target)
        window.release_mouse_input.assert_called_once_with(
            coords=(300, 300), absolute=True,
        )
    else:
        drag_control(app, 100, source, target)
        window.release_mouse_input.assert_not_called()

    window.drag_mouse_input.assert_called_once_with(
        src=(150, 25), dst=(300, 300), absolute=True,
    )
    assert app.refs == {}
    app.click.assert_not_called()


def test_drag_with_foreground_disabled_stops_before_input() -> None:
    app = Capstone()
    app.focus_window = MagicMock()
    app.click = MagicMock()
    source = _make_control("ref:src", "Palette Item")
    target = _make_control("ref:dst", "Layout Area")

    with pytest.raises(AutomationError, match="allow_foreground"):
        drag_control(app, 100, source, target, allow_foreground=False)

    app.focus_window.assert_not_called()
    app.click.assert_not_called()


def test_set_control_value_via_iface_value() -> None:
    app = Capstone()
    mock_node = MagicMock()
    mock_node.iface_value.SetValue = MagicMock()
    app.control = MagicMock(return_value=mock_node)
    ctrl = _make_control("ref:input", "TextBox", control_type="Edit")

    set_control_value(app, 100, ctrl, "50.0")

    mock_node.iface_value.SetValue.assert_called_once_with("50.0")


def test_set_control_value_fallback_keyboard() -> None:
    app = Capstone()
    app.click = MagicMock()
    app.keys = MagicMock()
    app.type_text = MagicMock()
    mock_node = MagicMock()
    mock_node.iface_value = None
    app.control = MagicMock(return_value=mock_node)
    ctrl = _make_control("ref:input", "TextBox", control_type="Edit")

    set_control_value(app, 100, ctrl, "100 ms")

    app.click.assert_called_once_with(100, "ref:input", allow_foreground=True)
    app.type_text.assert_called_once_with("100 ms")


# ---------------------------------------------------------------------------
# Bounds and Finding Containers / Palette Tests
# ---------------------------------------------------------------------------


def test_is_within_bounds() -> None:
    outer = _make_control(
        "ref:outer", "Outer",
        bounds=Bounds(left=10, top=10, right=200, bottom=200),
    )
    inner = _make_control(
        "ref:inner", "Inner",
        bounds=Bounds(left=20, top=20, right=100, bottom=100),
    )
    outside = _make_control(
        "ref:outside", "Outside",
        bounds=Bounds(left=0, top=0, right=50, bottom=50),
    )

    assert is_within_bounds(inner, outer) is True
    assert is_within_bounds(outside, outer) is False


def test_find_palette_item_matches_name_or_suffix() -> None:
    item = _make_control(
        "ref:p1", "Scope", control_type="Button",
        automation_id="Displays.ObjNameScope",
    )
    controls = [item]

    found = find_palette_item(controls, "Scope", ".ObjNameScope")
    assert found.ref == "ref:p1"


def test_find_palette_item_missing_raises() -> None:
    controls = [_make_control("ref:p1", "Other", control_type="Button")]

    with pytest.raises(AutomationError, match="not found in window snapshot"):
        _ = find_palette_item(controls, "FFT")


def test_find_display_container_by_type_and_keywords() -> None:
    table = _make_control(
        "ref:tbl", "Data Table", control_type="Table",
        automation_id="TableDisplay",
    )
    graph = _make_control(
        "ref:grp", "Graph 1", control_type="Custom",
        automation_id="GraphDisplay",
    )
    controls = [table, graph]

    found_tbl = find_display_container(controls, "table")
    assert found_tbl.ref == "ref:tbl"

    found_grp = find_display_container(controls, "graph")
    assert found_grp.ref == "ref:grp"


def test_find_display_containers_multiple() -> None:
    c1 = _make_control("ref:1", "Graph 1", control_type="Custom")
    c2 = _make_control("ref:2", "Table 1", control_type="Table")
    c3 = _make_control("ref:3", "Button", control_type="Button")
    controls = [c1, c2, c3]

    found = find_display_containers(controls, ("graph", "table"))
    assert len(found) == 2
    assert {c.ref for c in found} == {"ref:1", "ref:2"}


def test_display_harness_class_interface() -> None:
    app = Capstone()
    app.click = MagicMock()
    harness = DisplayHarness(app)
    ctrl = _make_control("ref:c", "Container")

    harness.click(100, ctrl)
    app.click.assert_called_once_with(100, "ref:c", allow_foreground=True)
    assert harness.is_within_bounds(ctrl, ctrl) is True

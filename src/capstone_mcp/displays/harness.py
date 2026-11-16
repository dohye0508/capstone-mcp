# Copyright 2026 Capstone MCP contributors.
"""Unified Display Harness for Capstone UI automation and display containers."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Final

from capstone_mcp.desktop import AutomationError, Capstone, bounds

if TYPE_CHECKING:
    from capstone_mcp.models import Bounds, Control

DEFAULT_DISPLAY_KEYWORDS: Final[tuple[str, ...]] = (
    "graph",
    "table",
    "digits",
    "scope",
    "oscilloscope",
    "fft",
)
CONTAINER_CONTROL_TYPES: Final[tuple[str, ...]] = (
    "Table",
    "DataGrid",
    "Custom",
    "Pane",
    "Group",
)
PALETTE_ITEM_CONTROL_TYPES: Final[tuple[str, ...]] = (
    "Text",
    "Button",
    "ListItem",
    "TreeItem",
    "Custom",
)


def center_coords(bounds: Bounds) -> tuple[int, int]:
    """Calculate the integer center coordinate (x, y) of a bounding rectangle."""
    return ((bounds.left + bounds.right) // 2, (bounds.top + bounds.bottom) // 2)


def click_control(
    app: Capstone,
    handle: int,
    ctrl: Control,
    *,
    double: bool = False,
    allow_foreground: bool = True,
) -> None:
    """Deliver one click request through the guarded desktop path."""
    if double:
        _ = app.click(handle, ctrl.ref, double=True, allow_foreground=allow_foreground)
    else:
        _ = app.click(handle, ctrl.ref, allow_foreground=allow_foreground)


def double_click_control(
    app: Capstone,
    handle: int,
    ctrl: Control,
    *,
    allow_foreground: bool = True,
) -> None:
    """Deliver an explicit double-click to insert palette items onto the page."""
    click_control(app, handle, ctrl, double=True, allow_foreground=allow_foreground)


def drag_control(
    app: Capstone,
    handle: int,
    source: Control,
    target: Control,
    *,
    allow_foreground: bool = True,
) -> None:
    """Drag a palette item to a target layout container or page region."""
    if not allow_foreground:
        msg = "Dragging requires allow_foreground=true."
        raise AutomationError(msg)
    source_node, target_node = app.control(source.ref), app.control(target.ref)
    if {app.owning_window(source_node), app.owning_window(target_node)} != {handle}:
        msg = "Both drag controls must belong to the selected Capstone window."
        raise AutomationError(msg)
    window = app.focus_window(handle)
    rect = bounds(window)
    src, dst = center_coords(bounds(source_node)), center_coords(bounds(target_node))
    for x, y in (src, dst):
        if not (rect.left <= x < rect.right and rect.top <= y < rect.bottom):
            msg = "Both drag endpoints must be inside the selected Capstone window."
            raise AutomationError(msg)
        app.require_uncovered(handle, (x, y))
    app.drag_mouse(window, src, dst)


def set_control_value(
    app: Capstone,
    handle: int,
    ctrl: Control,
    text: str,
) -> None:
    """Set text or value in a target control via ValuePattern or keystrokes."""
    node = app.control(ctrl.ref)
    with contextlib.suppress(AttributeError, RuntimeError):
        if hasattr(node, "iface_value") and node.iface_value:
            node.iface_value.SetValue(text)
            return

    if ctrl.control_type != "Edit" or any(c in text for c in "\r\n"):
        msg = (
            "Control has no writable Value pattern; refusing unverified keyboard input."
        )
        raise AutomationError(msg)
    click_control(app, handle, ctrl, allow_foreground=True)
    app.keys(handle, "^a{BACKSPACE}", allow_foreground=True)
    app.type_text(text)
    app.keys(handle, "{ENTER}", allow_foreground=True)


def is_within_bounds(inner: Control, outer: Control) -> bool:
    """Check if inner control rectangle is strictly contained within outer bounds."""
    return (
        inner.bounds.left >= outer.bounds.left
        and inner.bounds.top >= outer.bounds.top
        and inner.bounds.right <= outer.bounds.right
        and inner.bounds.bottom <= outer.bounds.bottom
    )


def find_palette_item(
    controls: list[Control],
    target_name: str,
    suffix: str | None = None,
) -> Control:
    """Find a display item in the Displays palette panel."""
    target_lower = target_name.strip().lower()
    for ctrl in controls:
        if not (ctrl.visible and ctrl.enabled):
            continue
        if ctrl.control_type not in PALETTE_ITEM_CONTROL_TYPES:
            continue

        cname_lower = ctrl.name.strip().lower()
        aid_lower = ctrl.automation_id.lower()

        if suffix and ctrl.automation_id.endswith(suffix):
            return ctrl
        if cname_lower == target_lower or target_lower in cname_lower:
            return ctrl
        if target_lower in aid_lower:
            return ctrl

    msg = f"Expected {target_name} display palette item not found in window snapshot."
    raise AutomationError(msg)


def _match_custom_name(controls: list[Control], custom_name: str) -> Control | None:
    c_lower = custom_name.strip().casefold()
    matches = [
        c
        for c in controls
        if c.visible
        and c.control_type in CONTAINER_CONTROL_TYPES
        and c_lower in (c.name.strip().casefold(), c.automation_id.casefold())
    ]
    if len(matches) > 1:
        msg = f"Display name '{custom_name}' is ambiguous."
        raise AutomationError(msg)
    return matches[0] if matches else None


def _workbook_controls(controls: list[Control]) -> list[Control]:
    page_refs = {
        c.ref for c in controls if c.visible and c.automation_id.endswith(".PageView")
    }
    if not page_refs:
        return controls
    page_controls = []
    for ctrl in controls:
        if ctrl.visible and ctrl.parent in page_refs:
            page_controls.append(ctrl)
            page_refs.add(ctrl.ref)
    return page_controls


def find_display_container(
    controls: list[Control],
    widget_type: str,
    custom_name: str | None = None,
) -> Control:
    """Locate one explicitly identified display; never choose an unrelated pane."""
    controls = _workbook_controls(controls)
    if custom_name:
        matched = _match_custom_name(controls, custom_name)
        if matched is not None:
            return matched
    else:
        keyword = widget_type.casefold()
        matches = [
            c
            for c in controls
            if c.visible
            and c.control_type in CONTAINER_CONTROL_TYPES
            and (
                keyword in c.name.casefold()
                or keyword in c.automation_id.casefold()
                or (keyword == "table" and c.control_type in ("Table", "DataGrid"))
            )
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            msg = f"Multiple {widget_type} displays found; specify an exact name."
            raise AutomationError(msg)
    msg = f"No uniquely identified {widget_type} display found: {custom_name!r}."
    raise AutomationError(msg)


def find_display_containers(
    controls: list[Control],
    keywords: tuple[str, ...] = DEFAULT_DISPLAY_KEYWORDS,
) -> list[Control]:
    """Find all graph, table, or display containers in the window snapshot."""
    displays: list[Control] = []
    for ctrl in controls:
        if not ctrl.visible:
            continue
        name_lower = ctrl.name.lower()
        aid_lower = ctrl.automation_id.lower()
        if ctrl.control_type in ("Custom", "Pane", "Group", "Table", "DataGrid") and (
            any(k in name_lower for k in keywords)
            or any(k in aid_lower for k in keywords)
        ):
            displays.append(ctrl)
    return displays


class DisplayHarness:
    """Unified automation harness for display creation and container interaction."""

    def __init__(self, app: Capstone) -> None:
        """Initialize display harness bound to Capstone automation client."""
        self.app = app

    def click(
        self,
        handle: int,
        ctrl: Control,
        *,
        double: bool = False,
        allow_foreground: bool = True,
    ) -> None:
        """Click or double-click a control."""
        click_control(
            self.app,
            handle,
            ctrl,
            double=double,
            allow_foreground=allow_foreground,
        )

    def double_click(self, handle: int, ctrl: Control) -> None:
        """Double-click a control."""
        double_click_control(self.app, handle, ctrl)

    def drag(
        self,
        handle: int,
        source: Control,
        target: Control,
        *,
        allow_foreground: bool = True,
    ) -> None:
        """Drag a control from source to target."""
        drag_control(
            self.app,
            handle,
            source,
            target,
            allow_foreground=allow_foreground,
        )

    def set_value(self, handle: int, ctrl: Control, text: str) -> None:
        """Set value in a target control."""
        set_control_value(self.app, handle, ctrl, text)

    def find_palette_item(
        self,
        controls: list[Control],
        target_name: str,
        suffix: str | None = None,
    ) -> Control:
        """Find a palette item in snapshot controls."""
        return find_palette_item(controls, target_name, suffix)

    def find_container(
        self,
        controls: list[Control],
        widget_type: str,
        custom_name: str | None = None,
    ) -> Control:
        """Locate target display container."""
        return find_display_container(controls, widget_type, custom_name)

    def find_containers(
        self,
        controls: list[Control],
        keywords: tuple[str, ...] = DEFAULT_DISPLAY_KEYWORDS,
    ) -> list[Control]:
        """Find all matching display containers."""
        return find_display_containers(controls, keywords)

    @staticmethod
    def is_within_bounds(inner: Control, outer: Control) -> bool:
        """Check if inner control rectangle is inside outer bounds."""
        return is_within_bounds(inner, outer)

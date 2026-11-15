# Copyright 2026 Capstone MCP contributors.
"""Observed selection contracts for native instrument controls."""

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.models import Control


def select_observed_option(app: Capstone, ctrl: Control, requested: str) -> None:
    """Select an existing displayed option instead of typing protocol enum names."""
    node = app.control(ctrl.ref)
    try:
        labels = getattr(node, "item_texts")()  # noqa: B009
    except (AttributeError, RuntimeError) as exc:
        msg = "Control does not expose selectable options; selection is unsupported."
        raise AutomationError(msg) from exc
    key = requested.replace("_", " ").strip().casefold()
    matches = [
        label
        for label in labels
        if isinstance(label, str) and label.replace("_", " ").strip().casefold() == key
    ]
    if len(matches) != 1:
        msg = f"No unique observed option matches {requested!r}; no text was injected."
        raise AutomationError(msg)
    getattr(node, "select")(matches[0])  # noqa: B009


def selected_text(app: Capstone, ctrl: Control) -> str:
    """Read an actual selected option, never the selector's accessible label."""
    node = app.control(ctrl.ref)
    try:
        value = getattr(node, "selected_text")()  # noqa: B009
    except (AttributeError, RuntimeError) as exc:
        msg = "Selected option is not observable."
        raise AutomationError(msg) from exc
    if not isinstance(value, str):
        msg = "Selected option is not observable."
        raise AutomationError(msg)
    return value.strip()

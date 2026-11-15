# Copyright 2026 Capstone MCP contributors.
"""Graph tools must belong to the selected graph, independent of screen layout."""

import pytest

from capstone_mcp.desktop import AutomationError
from capstone_mcp.graphs.toolbox import _find_toolbar_button
from capstone_mcp.models import Bounds, Control


def _control(ref: str, parent: str | None, *, top: int = 0) -> Control:
    return Control(
        ref=ref, parent=parent, name="Statistics", control_type="Button",
        automation_id=ref, enabled=True, visible=True,
        bounds=Bounds(left=110, top=top, right=140, bottom=top + 30),
    )


def test_overlapping_neighbor_graph_button_is_not_selected() -> None:
    graph = _control("graph", None)
    neighbor = _control("neighbor", None)
    wrong = _control("wrong", "neighbor")
    with pytest.raises(AutomationError, match="not found"):
        _find_toolbar_button([graph, neighbor, wrong], graph, ("statistics",))


def test_only_selected_graph_button_is_returned_when_layouts_overlap() -> None:
    graph = _control("graph", None)
    neighbor = _control("neighbor", None)
    wrong = _control("wrong", "neighbor")
    wanted = _control("wanted", "graph")
    assert _find_toolbar_button(
        [graph, neighbor, wrong, wanted], graph, ("statistics",),
    ) == wanted


def test_nested_bottom_toolbar_is_not_limited_to_top_120_pixels() -> None:
    graph = _control("graph", None)
    toolbar = _control("toolbar", "graph").model_copy(update={"name": "Toolbar"})
    wanted = _control("wanted", "toolbar", top=700)
    assert _find_toolbar_button(
        [graph, toolbar, wanted], graph, ("statistics",),
    ) == wanted


@pytest.mark.parametrize("parent", [None, "missing", "self"])
def test_unknown_or_cyclic_ancestry_never_falls_back_to_geometry(
    parent: str | None,
) -> None:
    graph = _control("graph", None)
    button = _control("self", parent)
    with pytest.raises(AutomationError, match="not found"):
        _find_toolbar_button([graph, button], graph, ("statistics",))

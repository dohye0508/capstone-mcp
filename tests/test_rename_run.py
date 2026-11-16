# Copyright 2026 Capstone MCP contributors.
"""Tests for dedicated run renaming in Data Summary."""

from unittest.mock import MagicMock

import pytest

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.models import Bounds, Control, Snapshot, Window
from capstone_mcp.runs import RenameRunRequest, rename_run


def test_rename_run_rejects_empty_name() -> None:
    app = Capstone()
    req = RenameRunRequest(handle=100, old_name="Run #1", new_name="")
    with pytest.raises(AutomationError, match="new_name"):
        _ = rename_run(app, req)


def test_rename_run_raises_when_run_not_found() -> None:
    app = Capstone()
    mock_window = Window(
        handle=100, title="Capstone", process_id=1,
        bounds=Bounds(left=0, top=0, right=800, bottom=600),
    )
    app.windows = MagicMock(return_value=[mock_window])
    app.snapshot = MagicMock(return_value=Snapshot(
        window=mock_window,
        controls=[
            Control(
                ref="ref:1", parent=None, name="Some Other Control",
                control_type="Button", automation_id="btn", enabled=True,
                visible=True, bounds=Bounds(left=0, top=0, right=10, bottom=10),
            ),
        ],
        truncated=False,
    ))

    req = RenameRunRequest(handle=100, old_name="Run #99", new_name="Final Run")
    with pytest.raises(AutomationError, match="not found"):
        _ = rename_run(app, req)


@pytest.mark.parametrize("space", [" ", "\u00a0"])
def test_rename_run_direct_value_pattern_success(space: str) -> None:
    app = Capstone()
    mock_window = Window(
        handle=100, title="Capstone", process_id=1,
        bounds=Bounds(left=0, top=0, right=800, bottom=600),
    )
    app.windows = MagicMock(return_value=[mock_window])

    initial_treeitem = Control(
        ref="ref:run1", parent="sensor-tree", name=f"Run{space}#1",
        control_type="TreeItem", automation_id="run_1", enabled=True,
        visible=True, bounds=Bounds(left=10, top=10, right=100, bottom=30),
    )
    renamed_treeitem = Control(
        ref="ref:run1", parent="sensor-tree", name="1k Ohm Trial",
        control_type="TreeItem", automation_id="run_1", enabled=True,
        visible=True, bounds=Bounds(left=10, top=10, right=100, bottom=30),
    )

    call_count = 0
    tree = initial_treeitem.model_copy(update={
        "ref": "sensor-tree", "parent": None, "control_type": "Tree", "name": "",
        "automation_id": "experimentDataSensors",
    })

    def mock_snapshot(*_args: object, **_kwargs: object) -> Snapshot:
        nonlocal call_count
        call_count += 1
        return Snapshot(
            window=mock_window,
            controls=[tree, renamed_treeitem if call_count > 1 else initial_treeitem],
            truncated=False,
        )

    app.snapshot = mock_snapshot

    mock_node = MagicMock()
    mock_node.iface_value.SetValue = MagicMock()
    app.control = MagicMock(return_value=mock_node)

    req = RenameRunRequest(handle=100, old_name="Run #1", new_name="1k Ohm Trial")
    res = rename_run(app, req)

    assert res.old_name == "Run #1"
    assert res.new_name == "1k Ohm Trial"
    assert res.verified is True
    mock_node.iface_value.SetValue.assert_called_once_with("1k Ohm Trial")


def test_rename_routes_literal_name_to_confirmed_inline_editor() -> None:
    app = Capstone()
    bounds = Bounds(left=0, top=0, right=200, bottom=100)
    window = Window(handle=100, title="Capstone", process_id=1, bounds=bounds)
    tree = Control(
        ref="tree", parent=None, name="", control_type="Tree",
        automation_id="experimentDataSensors", enabled=True, visible=True, bounds=bounds,
    )
    row = tree.model_copy(update={
        "ref": "run", "parent": tree.ref, "name": "Run #1", "control_type": "TreeItem",
    })
    field = row.model_copy(update={"ref": "edit", "control_type": "Edit"})
    new_name = "실험 ^a + {ENTER}"
    renamed = row.model_copy(update={"name": new_name})
    app.snapshot = MagicMock(side_effect=[
        Snapshot(window=window, controls=[tree, *items], truncated=False)
        for items in ([row], [row, field], [renamed])
    ])
    run_node = MagicMock()
    del run_node.iface_value
    editor = MagicMock()
    editor.iface_value.CurrentValue = "Run #1"
    editor.iface_value.SetValue.side_effect = lambda name: setattr(
        editor.iface_value, "CurrentValue", name,
    )
    app.control = MagicMock(side_effect={"run": run_node, "edit": editor}.__getitem__)
    app.focus_window = MagicMock()
    app.keys = MagicMock()
    app.require_input_ready = MagicMock()
    app.require_foreground = MagicMock()

    result = rename_run(app, RenameRunRequest(old_name="Run #1", new_name=new_name))

    assert result.verified
    app.keys.assert_called_once_with(100, "{F2}", allow_foreground=True)
    editor.iface_value.SetValue.assert_called_once_with(new_name)
    assert editor.type_keys.call_args.args == ("{ENTER}",)


@pytest.mark.parametrize("other_name", ["Run #1", "Run\u00a0#1"])
def test_rename_refuses_repeated_summary_rows_before_writing(other_name: str) -> None:
    app = Capstone()
    bounds = Bounds(left=0, top=0, right=200, bottom=100)
    window = Window(handle=100, title="Capstone", process_id=1, bounds=bounds)
    tree = Control(
        ref="tree", parent=None, name="", control_type="Tree",
        automation_id="experimentDataSensors", enabled=True, visible=True, bounds=bounds,
    )
    row = tree.model_copy(update={
        "ref": "run", "parent": tree.ref, "name": "Run #1", "control_type": "TreeItem",
    })
    other = row.model_copy(update={"ref": "run-other", "name": other_name})
    app.snapshot = MagicMock(return_value=Snapshot(
        window=window, controls=[tree, row, other],
        truncated=False,
    ))
    app.control = MagicMock()

    with pytest.raises(AutomationError, match="Multiple rows"):
        _ = rename_run(app, RenameRunRequest(old_name="Run #1", new_name="Trial A"))

    app.control.assert_not_called()

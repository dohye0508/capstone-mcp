# Copyright 2026 Capstone MCP contributors.
"""Test the observed native last-run deletion path and its verification."""

from unittest.mock import MagicMock

import pytest

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.models import Bounds, Control, Snapshot, Window
from capstone_mcp.runs import DeleteRunRequest, delete_run


@pytest.fixture
def app() -> Capstone:
    window = Window(
        handle=100, title="Experiment.cap", process_id=1,
        bounds=Bounds(left=0, top=0, right=1000, bottom=800),
    )

    def control(ref: str, name: str, kind: str, aid: str) -> Control:
        return Control(
            ref=ref, parent="tree" if kind == "TreeItem" else None,
            name=name, control_type=kind, automation_id=aid,
            enabled=True, visible=True, bounds=window.bounds,
        )

    tree = control("tree", "", "Tree", "experimentDataSensors")
    button = control("last", "Delete Last Run", "Button", "Workbook.DeleteRunButton")
    first = control("row1", "Run #1", "TreeItem", "")
    last = control("row2", "Trial A", "TreeItem", "")
    before = Snapshot(window=window, controls=[tree, button, first, last], truncated=False)
    after = Snapshot(window=window, controls=[tree, button, first], truncated=False)
    result = Capstone()
    result.snapshot = MagicMock(side_effect=[before, after])
    result.windows = MagicMock(return_value=[window])
    result.click = MagicMock()
    result.keys = MagicMock()
    return result


def test_last_run_deletion_confirms_actual_name_even_if_renamed(app: Capstone) -> None:
    result = delete_run(app, DeleteRunRequest(handle=100))

    assert result.deleted_run == "Trial A"
    assert result.verified
    app.click.assert_called_once_with(100, "last", allow_foreground=True)
    app.keys.assert_not_called()


def test_named_delete_does_not_guess_a_run_or_press_delete(app: Capstone) -> None:
    with pytest.raises(AutomationError, match="by name"):
        delete_run(app, DeleteRunRequest(handle=100, run_name="Trial A"))
    app.click.assert_not_called()
    app.keys.assert_not_called()


def test_last_run_deletion_reports_unconfirmed_state(
    app: Capstone, monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = app.snapshot(100, 16, 10_000)
    app.snapshot.side_effect = None
    app.snapshot.return_value = before
    monkeypatch.setattr("capstone_mcp.runs.manager.RUN_DELETE_TIMEOUT_SECONDS", 0)

    with pytest.raises(AutomationError, match="Could not verify"):
        delete_run(app, DeleteRunRequest(handle=100))
    app.click.assert_called_once()
    app.keys.assert_not_called()


@pytest.mark.parametrize("when", ["immediate", "delayed"])
def test_last_run_deletion_never_confirms_unexpected_dialog(
    app: Capstone, when: str,
) -> None:
    window = app.windows.return_value[0]
    dialog = window.model_copy(update={"handle": 200, "title": "Unexpected dialog"})
    observed = [[window, dialog]] * 2
    if when == "delayed":
        observed.insert(0, [window])
    app.windows.side_effect = [[window], *observed]

    with pytest.raises(AutomationError, match="unexpected window"):
        delete_run(app, DeleteRunRequest(handle=100))
    app.click.assert_called_once()
    app.keys.assert_not_called()

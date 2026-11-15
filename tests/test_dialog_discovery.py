# Copyright 2026 Capstone MCP contributors.
"""Dialog discovery rejects ambiguity and returns current snapshot references."""
from unittest.mock import Mock

import pytest

from capstone_mcp.desktop import AutomationError
from capstone_mcp.file_workflows import _new_snapshot
from tests.test_file_workflow_labels import _control, _snapshot


def test_two_matching_dialogs_fail_before_selecting_target() -> None:
    first = _snapshot([_control("wanted")], 2)
    second = _snapshot([_control("wanted")], 3)
    app = Mock(windows=Mock(return_value=[first.window, second.window]), snapshot=Mock(side_effect=[first, second]))
    with pytest.raises(AutomationError, match="Multiple new native dialogs"):
        _new_snapshot(app, {1}, lambda s: s.controls[0].name == "wanted")
    app.act.assert_not_called()


def test_unique_dialog_refreshed_after_other_window_invalidates_refs() -> None:
    old = _snapshot([_control("wanted", ref="old")], 2)
    other = _snapshot([_control("unrelated")], 3)
    fresh = _snapshot([_control("wanted", ref="fresh")], 2)
    app = Mock(windows=Mock(return_value=[old.window, other.window]), snapshot=Mock(side_effect=[old, other, fresh]))
    result = _new_snapshot(app, {1}, lambda s: s.controls[0].name == "wanted")
    assert result is fresh
    assert result.controls[0].ref == "fresh"
    assert [c.args[0] for c in app.snapshot.call_args_list] == [2, 3, 2]


@pytest.mark.parametrize("changed", ["truncated", "predicate", "disappeared"])
def test_refreshed_dialog_must_still_match(changed: str) -> None:
    old = _snapshot([_control("wanted")], 2)
    fresh = old.model_copy(update={"truncated": True}) if changed == "truncated" else _snapshot([_control("other")], 2)
    outcome = AutomationError("window gone") if changed == "disappeared" else fresh
    app = Mock(windows=Mock(return_value=[old.window]), snapshot=Mock(side_effect=[old, outcome]))
    assert _new_snapshot(app, {1}, lambda s: s.controls[0].name == "wanted") is None

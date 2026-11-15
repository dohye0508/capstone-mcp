# Copyright 2026 Capstone MCP contributors.
"""Default action handles select one observed window, never an arbitrary window."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from capstone_mcp.automation_models import NativeRequest
from capstone_mcp.desktop import AutomationError
from capstone_mcp.native.runtime import NativeDesktop


@pytest.mark.parametrize(("action", "field", "arguments"), [
    ("rename", "rename", {"old_name": "old", "new_name": "new"}),
    ("delete", "delete", {}),
    ("set_visibility", "visibility", {"runs": ["Run #1"]}),
])
def test_default_run_action_handle_resolved_before_dispatch(
    action: str, field: str, arguments: dict[str, object],
) -> None:
    runtime = NativeDesktop.__new__(NativeDesktop)
    runtime.app = Mock(windows=Mock(return_value=[SimpleNamespace(handle=123)]))
    handler = Mock(return_value={})
    runtime.handlers = {"manage_run": handler}
    runtime.dispatch(NativeRequest(operation="manage_run", run_request={"action": action, field: arguments}))
    assert handler.call_args.args[0].run_request[field]["handle"] == 123


@pytest.mark.parametrize("handles", [[], [12, 34]])
def test_default_handle_requires_unique_window(handles: list[int]) -> None:
    runtime = NativeDesktop.__new__(NativeDesktop)
    runtime.app = Mock(windows=Mock(return_value=[SimpleNamespace(handle=h) for h in handles]))
    handler = Mock()
    runtime.handlers = {"manage_run": handler}
    with pytest.raises(AutomationError, match="explicit window handle"):
        runtime.dispatch(NativeRequest(operation="manage_run", run_request={"action": "delete", "delete": {}}))
    handler.assert_not_called()


@pytest.mark.parametrize(("operation", "payload_field", "action", "args"), [
    ("manage_display", "display_request", "create_table", {}),
    ("manage_instrument", "instrument_request", "keep_sample", {}),
    ("manage_graph", "graph_request", "read", {}),
])
def test_other_unified_action_defaults_resolve_without_changing_explicit_handles(
    operation: str, payload_field: str, action: str, args: dict[str, object],
) -> None:
    runtime = NativeDesktop.__new__(NativeDesktop)
    runtime.app = Mock(windows=Mock(return_value=[SimpleNamespace(handle=123)]))
    request = NativeRequest.model_validate({"operation": operation, payload_field: {"action": action, action: args}})
    resolved = runtime._resolve_default_window(request)
    assert getattr(resolved, payload_field)[action]["handle"] == 123
    explicit = request.model_copy(update={payload_field: {"action": action, action: {**args, "handle": 789}}})
    assert runtime._resolve_default_window(explicit) is explicit


def test_calculation_default_resolves_but_observation_handle_policy_is_unchanged() -> None:
    runtime = NativeDesktop.__new__(NativeDesktop)
    runtime.app = Mock(windows=Mock(return_value=[SimpleNamespace(handle=123)]))
    calculation = NativeRequest(operation="create_calculation", handle=0)
    assert runtime._resolve_default_window(calculation).handle == 123
    observation = NativeRequest(operation="observe_graph", handle=0)
    assert runtime._resolve_default_window(observation) is observation

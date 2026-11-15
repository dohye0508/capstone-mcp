# Copyright 2026 Capstone MCP contributors.
"""Coordinate requests require one fresh receipt and preserve uncertain outcomes."""
import base64
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from capstone_mcp.automation_models import NativeRequest
from capstone_mcp.automation_worker import AutomationWorker
from capstone_mcp.graphs import GraphOperationError
from capstone_mcp.native.runtime import NativeDesktop


def _runtime() -> NativeDesktop:
    runtime = NativeDesktop.__new__(NativeDesktop)
    runtime.last_frame = SimpleNamespace(frame=SimpleNamespace(frame_id="fresh", handle=12, bounds="bounds"), png_base64=base64.b64encode(b"screen").decode())
    runtime.app = Mock(windows=Mock(return_value=[SimpleNamespace(handle=12, bounds="bounds")]), graph_screenshot=Mock(return_value=b"screen"))
    runtime.handlers = {"manage_graph": Mock(return_value={}), "fit_graph": Mock(return_value={})}
    return runtime


@pytest.mark.parametrize("action", ["fit", "select_measurement"])
@pytest.mark.parametrize("receipt", [None, "old", "fresh"])
def test_unified_coordinate_action_requires_fresh_receipt(action: str, receipt: str | None) -> None:
    runtime = _runtime()
    request = NativeRequest(operation="manage_graph", graph_request={"action": action, action: {"handle": 12, "frame_id": receipt}})
    if receipt == "fresh":
        runtime.dispatch(request)
        runtime.handlers["manage_graph"].assert_called_once()
    else:
        with pytest.raises(GraphOperationError, match="fresh graph frame"):
            runtime.dispatch(request)
        runtime.handlers["manage_graph"].assert_not_called()
    assert runtime.last_frame is None


def test_legacy_fit_rejects_changed_pixels_before_input() -> None:
    runtime = _runtime()
    runtime.app.graph_screenshot.return_value = b"changed"
    with pytest.raises(GraphOperationError, match="visible graph image changed"):
        runtime.dispatch(NativeRequest(operation="fit_graph", handle=12, frame_id="fresh"))
    runtime.handlers["fit_graph"].assert_not_called()


@pytest.mark.parametrize("operation", ["fit_graph", "graph_delta", "measure_graph_area", "toggle_graph_statistics", "manage_graph"])
def test_all_graph_mutations_preserve_transport_uncertainty(operation: str) -> None:
    worker = AutomationWorker()
    request = NativeRequest.model_validate({"operation": operation, "graph_request": {"action": "fit"}})
    failure = worker._graph_transport_failure(request, "id", "WORKER_TIMEOUT", "timeout")
    assert failure is not None
    assert failure.graph_input_may_have_been_sent


def test_unified_read_transport_failure_does_not_claim_mutation() -> None:
    worker = AutomationWorker()
    failure = worker._graph_transport_failure(NativeRequest(operation="manage_graph", graph_request={"action": "read"}), "id", "WORKER_TIMEOUT", "timeout")
    assert failure is not None
    assert not failure.graph_input_may_have_been_sent

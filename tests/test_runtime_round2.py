# Copyright 2026 Capstone MCP contributors.
"""Offline runtime contracts for resources, error content, and Win32 dispatch."""

import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from mcp.types import (
    CallToolRequest,
    CallToolRequestParams,
    CallToolResult,
    ImageContent,
    ServerResult,
    TextContent,
)
from pydantic import BaseModel

from capstone_mcp import bridge, desktop, resources, server, ui_events
from capstone_mcp.automation_models import NativeRequest
from capstone_mcp.graphs import GraphOperationError
from capstone_mcp.models import Point
from capstone_mcp.native.errors import classify_native_error
from capstone_mcp.native.runtime import NativeDesktop, _json


def test_unified_analysis_requires_existing_frame_before_handler() -> None:
    runtime = NativeDesktop.__new__(NativeDesktop)
    runtime.last_frame = None
    handler = Mock()
    runtime.handlers = {"manage_graph": handler}
    request = NativeRequest(operation="manage_graph", graph_request={
        "action": "analyze", "analyze": {
            "handle": 123,
            "fitting": {"frame_id": "old", "menu_point": {"x": 1, "y": 2}, "models": []},
        },
    })
    with pytest.raises(GraphOperationError, match="fresh graph frame"):
        runtime.dispatch(request)
    handler.assert_not_called()


def test_focus_failure_has_recovery_instead_of_coordinate_rewrite() -> None:
    code, remediation = classify_native_error(RuntimeError("Foreground check failed"))
    assert code == "AUTOMATION_ERROR"
    assert "do not change input coordinates" in remediation


def test_native_drag_translates_coordinates_and_releases_once() -> None:
    runtime = NativeDesktop()
    window = Mock()
    window.rectangle.return_value = SimpleNamespace(
        left=-250, top=100, right=150, bottom=500,
    )
    runtime.app.focus_window = Mock(return_value=window)

    _ = runtime.dispatch(NativeRequest(
        operation="drag", handle=42,
        point=Point(x=20, y=30), end=Point(x=100, y=200),
    ))

    window.drag_mouse_input.assert_called_once_with(
        src=(-230, 130), dst=(-150, 300), absolute=True,
    )
    window.release_mouse_input.assert_not_called()


@pytest.mark.parametrize("message", ["Graph timed out", "Page load timed out", "File read timed out"])
def test_timeout_precedes_domain_keywords(message: str) -> None:
    assert server.format_tool_error(message).error_code == "TIMEOUT_ERROR"
    assert classify_native_error(RuntimeError(message))[0] == "TIMEOUT_ERROR"


def test_file_errors_do_not_all_claim_missing_file() -> None:
    assert server.format_tool_error("Archive corrupted in file").error_code == "AUTOMATION_ERROR"
    assert server.format_tool_error("Access denied to path").error_code == "AUTOMATION_ERROR"
    assert server.format_tool_error("Input validation error for graph").error_code == "INVALID_ARGUMENT"
    assert server.format_tool_error(TimeoutError("graph unavailable")).error_code == "TIMEOUT_ERROR"


def test_native_json_preserves_json_mode_without_string_roundtrip() -> None:
    class Payload(BaseModel):
        value: Decimal
        values: tuple[int, ...]

    payload = Payload(value=Decimal("1.234"), values=(1, 2))
    assert _json(payload) == json.loads(payload.model_dump_json())


@pytest.mark.anyio
async def test_display_resource_selects_observed_handle() -> None:
    worker = Mock(retired=False, process_id=123)
    native = AsyncMock(side_effect=[
        [{"handle": 456}],
        {"controls": [{"name": "Graph", "automation_id": "graph"}]},
    ])
    result = json.loads(await resources._read_active_displays_doc(worker, native))
    assert result["graph_count"] == 1
    assert native.await_args_list[1].args[0].handle == 456


@pytest.mark.anyio
async def test_display_resource_reports_ambiguity_without_guessing() -> None:
    worker = Mock(retired=False, process_id=123)
    native = AsyncMock(return_value=[{"handle": 456}, {"handle": 789}])
    result = json.loads(await resources._read_active_displays_doc(worker, native))
    assert "unambiguous" in result["error"]
    assert native.await_count == 1


@pytest.mark.anyio
async def test_protocol_error_rewrite_preserves_other_content_and_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    picture = ImageContent(type="image", data="AA==", mimeType="image/png")
    detail = TextContent(type="text", text="second detail")
    original = CallToolResult(
        content=[picture, TextContent(type="text", text="Timed out"), detail],
        isError=True, structuredContent={"request_id": "original"},
    )
    monkeypatch.setattr(server, "_orig_call_tool_handler", AsyncMock(return_value=ServerResult(original)))
    result = await server._structured_call_tool_handler(CallToolRequest(
        method="tools/call", params=CallToolRequestParams(name="unused", arguments={}),
    ))
    assert result.root.structuredContent == {"request_id": "original"}
    assert result.root.content[0] == picture
    assert result.root.content[2] == detail
    assert json.loads(result.root.content[1].text)["error_code"] == "TIMEOUT_ERROR"


def test_window_message_dispatches_to_window_procedure() -> None:
    user32 = Mock()
    user32.GetMessageW.side_effect = [1, 0]
    events = ui_events.WindowEvents(1)
    events._dispatch_messages(user32)
    user32.TranslateMessage.assert_called_once()
    user32.DispatchMessageW.assert_called_once()


def test_getmessage_failure_is_reported() -> None:
    user32 = Mock()
    user32.GetMessageW.return_value = -1
    events = ui_events.WindowEvents(1)
    events._dispatch_messages(user32)
    assert events.error
    user32.DispatchMessageW.assert_not_called()


def test_wrong_debug_process_rejected_before_network(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = SimpleNamespace(
        status=bridge.psutil.CONN_LISTEN, pid=123,
        laddr=SimpleNamespace(port=54321, ip="127.0.0.1"),
    )
    monkeypatch.setattr(bridge.psutil, "net_connections", Mock(return_value=[connection]))
    monkeypatch.setattr(bridge.psutil, "Process", Mock(return_value=Mock(exe=lambda: "C:/other.exe")))
    client = Mock()
    monkeypatch.setattr(bridge.httpx2, "Client", client)
    with pytest.raises(bridge.BridgeError, match="configured Capstone"):
        bridge.discover_target(54321)
    client.assert_not_called()


def test_exact_configured_debug_process_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = SimpleNamespace(
        status=bridge.psutil.CONN_LISTEN, pid=123,
        laddr=SimpleNamespace(port=54321, ip="127.0.0.1"),
    )
    monkeypatch.setattr(bridge.psutil, "net_connections", Mock(return_value=[connection]))
    monkeypatch.setattr(bridge.psutil, "Process", Mock(return_value=Mock(exe=lambda: str(desktop.EXECUTABLE))))
    bridge._verify_debug_owner(54321)


@pytest.mark.anyio
async def test_server_lifespan_closes_pool_even_after_worker_cleanup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server, "JOBS", Mock())
    monkeypatch.setattr(server, "WORKER", Mock(close=Mock(side_effect=RuntimeError("cleanup"))))
    close = Mock()
    monkeypatch.setattr(bridge, "close_connections", close)
    with pytest.raises(RuntimeError, match="cleanup"):
        async with server._lifespan(server.MCP):
            pass
    close.assert_called_once_with()


def test_pending_run_resource_does_not_poll_native_backend() -> None:
    from threading import RLock  # noqa: PLC0415

    backend = Mock()
    job = Mock(result=Mock(done=Mock(return_value=False)), backend=backend)
    jobs = Mock(lock=RLock(), jobs={"running": job})
    doc = json.loads(resources._read_active_runs_doc(Mock(process_id=1), jobs))
    assert doc["active_jobs"][0]["state"] == "running"
    backend.observe.assert_not_called()

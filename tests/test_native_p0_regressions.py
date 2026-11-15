# Copyright 2026 Capstone MCP contributors.
"""Offline failure-path regressions using only mocked worker and Win32 boundaries."""

import json
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from capstone_mcp import server, ui_events
from capstone_mcp.automation_models import NativeRequest
from capstone_mcp.automation_worker import NativeSessionError
from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.native.errors import classify_native_error


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Runtime calculation failed", "AUTOMATION_ERROR"),
        ("Sometimes data is unavailable", "AUTOMATION_ERROR"),
        ("Timestamp conversion failed", "AUTOMATION_ERROR"),
        ("Recording failed: disk full", "AUTOMATION_ERROR"),
        ("Recording sensor disconnected", "INSTRUMENT_ERROR"),
        ("Session result is corrupt", "AUTOMATION_ERROR"),
        ("Operation timed out", "TIMEOUT_ERROR"),
    ],
)
def test_native_error_does_not_infer_state_from_substrings(
    message: str, expected: str,
) -> None:
    assert classify_native_error(RuntimeError(message))[0] == expected


def test_real_unattached_precondition_preserves_session_error_code() -> None:
    # windows() rejects an unset PID before querying any OS window or process.
    with pytest.raises(AutomationError, match="Call capstone_attach first") as caught:
        Capstone().windows()
    code, remediation = classify_native_error(caught.value)
    assert code == "SESSION_NOT_ATTACHED"
    assert "capstone_attach" in remediation


@pytest.mark.anyio
@pytest.mark.parametrize("during_reset", [False, True])
async def test_uncoded_worker_failure_is_structured_without_stderr(
    monkeypatch: pytest.MonkeyPatch, *, during_reset: bool,
) -> None:
    worker = MagicMock()
    worker.retired = during_reset
    failure = NativeSessionError(
        "Native transport failed; outcome is unknown.",
        stderr_tail=["Traceback: private worker diagnostic"],
    )
    if during_reset:
        worker.reset.side_effect = failure
    else:
        worker.call.side_effect = failure
    monkeypatch.setattr(server, "WORKER", worker)

    with pytest.raises(ToolError) as caught:
        await server._native(NativeRequest(operation="attach"))

    payload = json.loads(str(caught.value))
    assert payload["error_code"] == "AUTOMATION_ERROR"
    assert payload["message"] == failure.message
    assert payload["remediation"]
    assert "private worker diagnostic" not in str(caught.value)
    if during_reset:
        worker.call.assert_not_called()


@pytest.mark.parametrize("failure_stage", ["create", "subscribe", "destroy"])
def test_hook_is_released_after_clipboard_initialization_failure(
    monkeypatch: pytest.MonkeyPatch, failure_stage: str,
) -> None:
    user32 = MagicMock()
    user32.SetWinEventHook.return_value = 123
    user32.AddClipboardFormatListener.return_value = failure_stage != "subscribe"
    user32.GetMessageW.return_value = 0
    kernel32 = MagicMock()
    kernel32.GetCurrentThreadId.return_value = 99
    create = MagicMock(return_value=456)
    destroy = MagicMock()
    if failure_stage == "create":
        create.side_effect = OSError("window creation failed")
    elif failure_stage == "destroy":
        destroy.side_effect = OSError("window destruction failed")
    monkeypatch.setattr(ui_events, "_User32", lambda: user32)
    monkeypatch.setattr(ui_events.ctypes, "WinDLL", lambda *_a, **_kw: kernel32)
    monkeypatch.setattr(ui_events.win32gui, "CreateWindowEx", create)
    monkeypatch.setattr(ui_events.win32gui, "DestroyWindow", destroy)
    events = ui_events.WindowEvents(1, clipboard=True)

    if failure_stage == "destroy":
        with pytest.raises(OSError, match="window destruction failed"):
            events._pump()
    else:
        events._pump()
        assert events.error
    user32.UnhookWinEvent.assert_called_once_with(123)
    assert events.ready.is_set()

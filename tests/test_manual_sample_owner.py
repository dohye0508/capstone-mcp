# Copyright 2026 Capstone MCP contributors.
"""Manual samples use the recording owner without racing its stop/save commands."""
from concurrent.futures import Future
from threading import Event, Lock, Thread
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from capstone_mcp import server
from capstone_mcp.automation_models import NativeRequest
from capstone_mcp.desktop import AutomationError
from capstone_mcp.repetition import AcquisitionJobs, RemoteRecordingBackend


def _backend(call: Mock) -> RemoteRecordingBackend:
    backend = RemoteRecordingBackend.__new__(RemoteRecordingBackend)
    backend.worker = Mock(call=call)
    backend.handle = 321
    backend.command_lock = Lock()
    backend.closed = False
    return backend


@pytest.mark.anyio
async def test_sample_routes_to_active_owner_and_resolves_only_its_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    call = Mock(return_value={"action": "keep_sample"})
    backend = _backend(call)
    jobs = AcquisitionJobs()
    jobs.jobs["active"] = SimpleNamespace(result=Future(), backend=backend)
    global_worker = Mock()
    monkeypatch.setattr(server, "JOBS", jobs)
    monkeypatch.setattr(server, "WORKER", global_worker)
    request = NativeRequest(operation="manage_instrument", instrument_request={"action": "keep_sample", "keep_sample": {"handle": 0}})
    await server._native(request, mutates=True)
    assert call.call_args.args[0].instrument_request["keep_sample"]["handle"] == 321
    global_worker.call.assert_not_called()
    with pytest.raises(AutomationError, match="active recording window"):
        await server._native(request.model_copy(update={"instrument_request": {"action": "keep_sample", "keep_sample": {"handle": 999}}}), mutates=True)
    with pytest.raises(AutomationError, match="acquisition or another input"):
        await server._native(NativeRequest(operation="keys"), mutates=True)
    assert call.call_count == 1
    assert not jobs.input_reserved


@pytest.mark.parametrize("operation", ["recording_change", "save_experiment"])
def test_sample_and_stop_or_save_never_overlap(operation: str) -> None:
    entered, release, second_entered = Event(), Event(), Event()
    errors = []

    def call(request: NativeRequest) -> dict[str, object]:
        if request.operation == "manage_instrument":
            entered.set()
            assert release.wait(5)
        else:
            second_entered.set()
        return {}

    backend = _backend(Mock(side_effect=call))
    sample = Thread(target=lambda: backend.keep_sample(NativeRequest(operation="manage_instrument")))

    def next_command() -> None:
        try:
            backend._call(NativeRequest(operation=operation))
        except (AutomationError, AssertionError) as error:
            errors.append(error)

    transition = Thread(target=next_command)
    try:
        sample.start()
        assert entered.wait(5)
        transition.start()
        assert not second_entered.wait(0.1)
        release.set()
        sample.join(5)
        transition.join(5)
        assert second_entered.is_set()
        assert not errors
        assert not sample.is_alive()
        assert not transition.is_alive()
    finally:
        release.set()
        sample.join(5)
        if transition.ident is not None:
            transition.join(5)
    backend.close()
    with pytest.raises(AutomationError, match="closed; no input"):
        backend.keep_sample(NativeRequest(operation="manage_instrument"))

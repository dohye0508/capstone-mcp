# Copyright 2026 Capstone MCP contributors.
"""Real thread cancellation and admission semantics without native app calls."""

from threading import Event
from unittest.mock import Mock

import anyio
import pytest

from capstone_mcp import server
from capstone_mcp.automation_models import NativeRequest
from capstone_mcp.automation_worker import AutomationWorker, NativeSessionError
from capstone_mcp.desktop import AutomationError
from capstone_mcp.repetition import AcquisitionJobs


@pytest.mark.anyio
async def test_cancellation_keeps_mutation_reserved_until_worker_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = Event()
    release = Event()

    def call(_request: NativeRequest) -> list[object]:
        entered.set()
        assert release.wait(5)
        return []

    worker = Mock(call=call, retired=False)
    jobs = AcquisitionJobs()
    monkeypatch.setattr(server, "WORKER", worker)
    monkeypatch.setattr(server, "JOBS", jobs)
    scope = anyio.CancelScope()

    async def mutate() -> None:
        with scope:
            await server._native(NativeRequest(operation="windows"), mutates=True)

    try:
        async with anyio.create_task_group() as group:
            group.start_soon(mutate)
            assert await anyio.to_thread.run_sync(entered.wait, 5)
            scope.cancel()
            await anyio.lowlevel.checkpoint()
            assert jobs.input_reserved
            with pytest.raises(AutomationError, match="another input is active"):
                await server._native(NativeRequest(operation="windows"), mutates=True)
            release.set()
    finally:
        release.set()
    assert not jobs.input_reserved


def test_concurrent_worker_rejection_does_not_retire_active_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = AutomationWorker()
    retire = Mock()
    monkeypatch.setattr(worker, "_retire", retire)
    with worker.lock, pytest.raises(NativeSessionError, match="already active"):
        worker.call(NativeRequest(operation="windows"))
    assert not worker.retired
    retire.assert_not_called()

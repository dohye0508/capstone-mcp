# Copyright 2026 Capstone MCP contributors.
"""Prove blocking resource I/O is isolated without contacting Capstone."""

from threading import get_ident
from unittest.mock import AsyncMock

import pytest
from mcp.server.fastmcp import FastMCP

from capstone_mcp import resources
from capstone_mcp.automation_worker import AutomationWorker
from capstone_mcp.repetition import AcquisitionJobs


@pytest.mark.anyio
async def test_live_measurement_io_runs_outside_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loop_thread = get_ident()
    worker = AutomationWorker()
    calls: list[int] = []

    def read_doc(received_worker: AutomationWorker) -> str:
        assert received_worker is worker
        calls.append(get_ident())
        return '{"status":"disconnected"}'

    monkeypatch.setattr(resources, "_read_live_measurements_doc", read_doc)
    registered = resources.register_resources(
        FastMCP("offline-resource-test"), worker, AcquisitionJobs(), AsyncMock(),
    )
    result = await registered["capstone_live_measurements_resource"]()

    assert result == '{"status":"disconnected"}'
    assert len(calls) == 1
    assert calls[0] != loop_thread
    assert worker.process is None

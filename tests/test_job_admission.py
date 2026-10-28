# Copyright 2026 Capstone MCP contributors.
"""Input admission and status/cancellation remain independent of blocked native I/O."""

from threading import Event
from typing import override

import anyio
import pytest
from pydantic import JsonValue, TypeAdapter

from capstone_mcp import server
from capstone_mcp.acquisition import RecordingStatus
from capstone_mcp.automation_models import NativeRequest
from capstone_mcp.automation_worker import AutomationWorker
from capstone_mcp.desktop import AutomationError
from capstone_mcp.file_workflows import FileArtifact
from capstone_mcp.models import Window
from capstone_mcp.repetition import (
    AcquisitionJob,
    AcquisitionJobs,
    JobStatus,
    RepeatPlan,
)


class HeldWorker(AutomationWorker):
    """Simulate one blocked native call with an exact entry/release handshake."""

    def __init__(self) -> None:
        super().__init__()
        self.entered: Event = Event()
        self.release: Event = Event()

    @override
    def call(self, request: NativeRequest) -> JsonValue:
        del request
        self.entered.set()
        if not self.release.wait(10):
            msg = "The MCP event loop did not release the blocked request."
            raise RuntimeError(msg)
        return []


class IdleBackend:
    """A pending job must not query native state merely to report or cancel."""

    def __init__(self) -> None:
        self.uncertain: bool = False

    def observe(self) -> RecordingStatus:
        msg = "Status must not call the native backend"
        raise AssertionError(msg)

    def change(self, *, recording: bool) -> RecordingStatus:
        del recording
        msg = "Cancellation must not synchronously call native input"
        raise AssertionError(msg)

    def save(self, path: str) -> FileArtifact:
        del path
        msg = "Status must not save a file"
        raise AssertionError(msg)

    def close(self) -> None:
        pass


def test_input_reservation_rejects_acquisition_preflight() -> None:
    # Given
    jobs = AcquisitionJobs()
    plan = RepeatPlan(process_id=1, window_handle=1, duration_seconds=1)
    # When / Then
    with jobs.interaction(), pytest.raises(AutomationError):
        _ = jobs.start(plan)
    jobs.require_idle()
    assert not jobs.jobs


def test_job_status_and_cancel_work_while_native_request_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    worker = HeldWorker()
    jobs = AcquisitionJobs()
    plan = RepeatPlan(process_id=1, window_handle=1, duration_seconds=1)
    job = AcquisitionJob(plan, IdleBackend())
    jobs.jobs["pending"] = job
    monkeypatch.setattr(server, "WORKER", worker)
    monkeypatch.setattr(server, "JOBS", jobs)

    async def exercise() -> None:
        async def query_windows() -> None:
            _ = TypeAdapter(list[Window]).validate_python(
                await server.capstone_windows(),
            )

        with anyio.fail_after(10):
            async with anyio.create_task_group() as group:
                _ = group.start_soon(query_windows)
                assert await anyio.to_thread.run_sync(worker.entered.wait, 5)
                try:
                    # When
                    status = JobStatus.model_validate(
                        server.capstone_acquisition_job("pending"),
                    )
                    cancelled = JobStatus.model_validate(
                        server.capstone_cancel_acquisition("pending"),
                    )
                    # Then
                    assert status.state == "running"
                    assert cancelled.state == "running"
                    assert job.cancel.is_set()
                    assert not job.result.done()
                finally:
                    worker.release.set()

    anyio.run(exercise)

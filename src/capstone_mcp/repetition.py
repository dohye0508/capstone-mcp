# Copyright 2026 Capstone MCP contributors.
"""Cancellable repeated acquisition using native start/stop event confirmation."""

import logging
import time
from collections.abc import Callable
from concurrent.futures import Future
from threading import Event, Thread
from typing import Annotated, Final, Literal, Protocol
from uuid import uuid4

import pythoncom
from pydantic import Field, FiniteFloat

from capstone_mcp.acquisition import (
    RecordingStatus,
    observe_recording,
    request_recording,
)
from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.models import Model
from capstone_mcp.record_events import (
    arm_transition,
    await_transition,
    dispose_transition,
    verify_debug_process,
)

LOGGER: Final = logging.getLogger(__name__)
MAX_JOB_HISTORY: Final = 16


class RepeatPlan(Model):
    """Explicit acquisition timing; no samplerate or sensor settings are changed."""

    process_id: Annotated[int, Field(gt=0)]
    window_handle: Annotated[int, Field(gt=0)]
    debug_port: Annotated[int, Field(ge=1024, le=65535)] = 9223
    repetitions: Annotated[int, Field(ge=1, le=100)] = 1
    duration_seconds: Annotated[FiniteFloat, Field(gt=0, le=3600)]
    pause_seconds: Annotated[FiniteFloat, Field(ge=0, le=3600)] = 0
    allow_foreground: bool = True


class RunReceipt(Model):
    """Host-observed cycle timing; not a hardware sampling timestamp."""

    ordinal: int
    elapsed_seconds: float


class RepeatOutcome(Model):
    """Recorded cycles are retained in Capstone, not deleted or overwritten."""

    state: Literal["completed", "cancelled", "failed"]
    runs: list[RunReceipt] | None
    error: str | None = None


class JobStatus(Model):
    """Background job receipt; callers use its ID to inspect or cancel."""

    job_id: str
    state: Literal["running", "completed", "cancelled", "failed"]
    result: RepeatOutcome | None


class RecordingBackend(Protocol):
    """Native boundary used by the deterministic acquisition sequencer."""

    def observe(self) -> RecordingStatus:
        """Read current recording state."""
        ...

    def change(self, *, recording: bool) -> RecordingStatus:
        """Request and confirm a native recording transition."""
        ...


class Cancellation(Protocol):
    """Interruptible acquisition timer; duration itself is intended behavior."""

    def is_set(self) -> bool:
        """Report whether cancellation was requested."""
        ...

    def wait(self, timeout: float) -> bool:
        """Wait the specified acquisition time, interrupting on cancellation."""
        ...


class NativeRecordingBackend:
    """Own UIA objects on the worker's COM apartment rather than sharing APP refs."""

    def __init__(self, plan: RepeatPlan) -> None:
        """Bind independently to the validated process and native event endpoint."""
        verify_debug_process(plan.debug_port, plan.process_id)
        self.app: Capstone = Capstone()
        _ = self.app.attach(process_id=plan.process_id)
        self.plan: RepeatPlan = plan

    def observe(self) -> RecordingStatus:
        """Read the current native control state."""
        state, _ = observe_recording(self.app, self.plan.window_handle)
        return state

    def change(self, *, recording: bool) -> RecordingStatus:
        """Arm the event before input, and require the actual native transition."""
        state = self.observe()
        if state.recording == recording:
            return state
        token = arm_transition(self.plan.debug_port, recording=recording)
        try:
            _ = request_recording(
                self.app, self.plan.window_handle, recording=recording,
                allow_foreground=self.plan.allow_foreground,
            )
            await_transition(self.plan.debug_port, token, recording=recording)
        finally:
            dispose_transition(self.plan.debug_port, token)
        observed = self.observe()
        if observed.recording != recording:
            msg = "Native event and observed recording control state disagree."
            raise AutomationError(msg)
        return observed


def run_sequence(
    backend: RecordingBackend, plan: RepeatPlan, cancellation: Cancellation,
    *, clock: Callable[[], float] = time.monotonic,
) -> RepeatOutcome:
    """Run confirmed cycles, always requesting stop if a start attempt was made."""
    initial = backend.observe()
    if initial.recording or not initial.control_enabled:
        msg = "Begin from a stopped experiment with an enabled recording source."
        raise AutomationError(msg)
    receipts: list[RunReceipt] = []
    for ordinal in range(1, plan.repetitions + 1):
        if cancellation.is_set():
            return RepeatOutcome(state="cancelled", runs=receipts)
        state = backend.observe()
        if (
            state.recording
            or not state.control_enabled
            or state.sampling_rate_display != initial.sampling_rate_display
        ):
            msg = "Recording availability or sample-rate display changed between runs."
            raise AutomationError(msg)
        try:
            started = backend.change(recording=True)
            if not started.recording:
                msg = "Start was not confirmed."
                raise AutomationError(msg)
            start_time = clock()
            interrupted = cancellation.wait(plan.duration_seconds)
        finally:
            stopped = backend.change(recording=False)
            if stopped.recording:
                msg = "Stop was not confirmed; inspect Capstone immediately."
                raise AutomationError(msg)
        receipts.append(RunReceipt(
            ordinal=ordinal, elapsed_seconds=clock() - start_time,
        ))
        if interrupted:
            return RepeatOutcome(state="cancelled", runs=receipts)
        if ordinal < plan.repetitions and cancellation.wait(plan.pause_seconds):
            return RepeatOutcome(state="cancelled", runs=receipts)
    return RepeatOutcome(state="completed", runs=receipts)


class AcquisitionJob:
    """Mutable cancellation and completion state for one background acquisition."""

    def __init__(self, plan: RepeatPlan) -> None:
        """Allocate one cancellation signal and one completion future."""
        self.plan: RepeatPlan = plan
        self.cancel: Event = Event()
        self.result: Future[RepeatOutcome] = Future()

    def run(self) -> None:
        """Worker boundary records all failures and preserves their traceback."""
        try:
            pythoncom.CoInitializeEx(0)
            try:
                result = run_sequence(
                    NativeRecordingBackend(self.plan), self.plan, self.cancel,
                )
            finally:
                pythoncom.CoUninitialize()
        except Exception as error:
            LOGGER.exception("Repeated Capstone acquisition failed")
            result = RepeatOutcome(state="failed", runs=None, error=str(error))
        self.result.set_result(result)


class AcquisitionJobs:
    """Own one active acquisition and bounded completion history."""

    def __init__(self) -> None:
        """Start with no jobs; completed history remains bounded."""
        self.jobs: dict[str, AcquisitionJob] = {}

    def require_idle(self) -> None:
        """Prevent other MCP input from racing an active acquisition."""
        if any(not job.result.done() for job in self.jobs.values()):
            msg = "An acquisition job is active; cancel it before other input."
            raise AutomationError(msg)

    def start(self, plan: RepeatPlan) -> JobStatus:
        """Validate the target and readiness before starting the asynchronous worker."""
        self.require_idle()
        if not plan.allow_foreground:
            msg = "Repeated acquisition requires explicit allow_foreground=true."
            raise AutomationError(msg)
        state = NativeRecordingBackend(plan).observe()
        if state.recording or not state.control_enabled:
            msg = "A stopped experiment with connected/configured data is required."
            raise AutomationError(msg)
        if len(self.jobs) >= MAX_JOB_HISTORY:
            del self.jobs[next(iter(self.jobs))]
        identifier = uuid4().hex
        job = AcquisitionJob(plan)
        self.jobs[identifier] = job
        Thread(target=job.run, daemon=True).start()
        return self.status(identifier)

    def status(self, identifier: str) -> JobStatus:
        """Return only observed completion; no polling or implicit retry."""
        job = self.jobs[identifier]
        result = job.result.result() if job.result.done() else None
        return JobStatus(
            job_id=identifier, state="running" if result is None else result.state,
            result=result,
        )

    def cancel(self, identifier: str) -> JobStatus:
        """Interrupt the timer; the worker then requests a confirmed stop."""
        self.jobs[identifier].cancel.set()
        return self.status(identifier)

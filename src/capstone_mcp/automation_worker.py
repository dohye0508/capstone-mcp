# Copyright 2026 Capstone MCP contributors.
"""Persistent native sessions with bounded IPC and no replay after uncertainty."""

from __future__ import annotations

import ctypes
import logging
import subprocess
import sys
import time
from collections import deque
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from contextlib import suppress
from ctypes import wintypes
from threading import Lock, Thread
from typing import IO, Final
from uuid import uuid4

import win32api
import win32job
from pydantic import JsonValue, TypeAdapter

from capstone_mcp.automation_models import NativeReply, NativeRequest, RequestPacket
from capstone_mcp.graphs import GRAPH_INPUT_OPERATIONS, GraphFailure

TEXT_VALUE: Final = TypeAdapter(str)
LOGGER: Final = logging.getLogger(__name__)
MAX_MESSAGE_BYTES: Final = 64 * 1024 * 1024
MAX_STDERR_LINE_BYTES: Final = 4096
MAX_STDERR_LINES: Final = 200
CLEANUP_SECONDS: Final = 2
PROCESS_ATTACH_TO_JOB: Final = 0x0101
THREAD_TERMINATE: Final = 0x0001
ERROR_INVALID_PARAMETER: Final = 87
ERROR_NOT_FOUND: Final = 1168


def _cancel_thread_io(thread: Thread | None) -> None:
    """Cancel only a worker-owned thread's outstanding synchronous pipe I/O."""
    if thread is None or not thread.is_alive() or thread.native_id is None:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenThread.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenThread.restype = wintypes.HANDLE
    kernel32.CancelSynchronousIo.argtypes = (wintypes.HANDLE,)
    kernel32.CancelSynchronousIo.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenThread(THREAD_TERMINATE, 0, thread.native_id)
    if not handle:
        error = ctypes.get_last_error()
        if error == ERROR_INVALID_PARAMETER:  # The thread already exited.
            return
        raise ctypes.WinError(error)
    try:
        if not kernel32.CancelSynchronousIo(handle):
            error = ctypes.get_last_error()
            if error != ERROR_NOT_FOUND:  # No outstanding I/O is also success.
                raise ctypes.WinError(error)
    finally:
        kernel32.CloseHandle(handle)

class NativeSessionError(RuntimeError):
    """The native session failed; an input may already have reached Capstone."""

    def __init__(
        self,
        message: str,
        failure: GraphFailure | None = None,
        *,
        stderr_tail: list[str] | None = None,
        error_code: str | None = None,
        remediation: str | None = None,
    ) -> None:
        """Keep graph recovery metadata without changing ordinary worker errors."""
        self.message: str = message
        self.failure: GraphFailure | None = failure
        self.stderr_tail: list[str] = list(stderr_tail or [])
        self.error_code: str | None = error_code
        self.remediation: str | None = remediation
        correlation = "" if failure is None else f" [request_id={failure.request_id}]"
        stderr_info = ""
        if self.stderr_tail:
            tail_joined = "".join(self.stderr_tail)
            stderr_info = f"\n[Worker stderr tail]:\n{tail_joined}"
        super().__init__(message + correlation + stderr_info)


class AutomationWorker:
    """Serialize one session's requests; retire its process on uncertain results."""

    def __init__(self, *, timeout: float = 60) -> None:
        """Start lazily so importing the MCP does not launch a worker."""
        self.timeout: float = timeout
        self.lock: Lock = Lock()
        self.cleanup_lock: Lock = Lock()
        self.process: subprocess.Popen[str] | None = None
        self.job: win32job.Handle | None = None
        self.transport: Thread | None = None
        self.retired: bool = False
        self.uncertain: bool = False
        self.last_graph_failure: GraphFailure | None = None
        self.stderr_buffer: deque[str] = deque(maxlen=MAX_STDERR_LINES)
        self._stderr_thread: Thread | None = None

    @property
    def process_id(self) -> int | None:
        """Return the native worker process ID if currently running."""
        return self.process.pid if self.process is not None else None

    def _spawn(self) -> subprocess.Popen[str]:
        """Launch the fixed native bootstrap; test backends replace this boundary."""
        return subprocess.Popen(
            [sys.executable, "-X", "utf8", "-u", "-m", "capstone_mcp.native_main"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8",
        )

    def _start_stderr_reader(self, stream: IO[str] | None) -> None:
        if stream is None:
            return

        def reader() -> None:
            with suppress(OSError, ValueError):
                while True:
                    line = stream.readline(MAX_STDERR_LINE_BYTES)
                    if not line:
                        break
                    self.stderr_buffer.append(line)

        thread = Thread(target=reader, daemon=True)
        thread.start()
        self._stderr_thread = thread

    def _start(self) -> subprocess.Popen[str]:
        if self.retired:
            msg = "Native session was retired; attach a new session before more input."
            raise NativeSessionError(msg)
        if self.process is not None:
            return self.process
        self.job = win32job.CreateJobObject(None, "capstone-mcp-" + uuid4().hex)
        limits = win32job.QueryInformationJobObject(
            self.job, win32job.JobObjectExtendedLimitInformation,
        )
        limits["BasicLimitInformation"]["LimitFlags"] |= (
            win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            | win32job.JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK
        )
        win32job.SetInformationJobObject(
            self.job, win32job.JobObjectExtendedLimitInformation, limits,
        )
        process = self._spawn()
        self.process = process
        self._start_stderr_reader(process.stderr)
        if self.retired:
            process.kill()
            msg = "Worker startup finished after its session was retired."
            raise NativeSessionError(msg, stderr_tail=list(self.stderr_buffer))
        process_handle = win32api.OpenProcess(
            PROCESS_ATTACH_TO_JOB, 0, process.pid,
        )
        try:
            win32job.AssignProcessToJobObject(self.job, process_handle)
        finally:
            process_handle.Close()
        if process.stdin is None:
            msg = "Native worker input stream is unavailable."
            raise NativeSessionError(msg, stderr_tail=list(self.stderr_buffer))
        _ = process.stdin.write("INITIALIZE\n")
        process.stdin.flush()
        return process

    def _exchange(self, request: NativeRequest, identifier: str) -> NativeReply:
        process = self._start()
        if self.retired:
            msg = "Native session was retired before input delivery."
            raise NativeSessionError(msg, stderr_tail=list(self.stderr_buffer))
        if process.stdin is None or process.stdout is None:
            msg = "Native worker IPC streams are unavailable."
            raise NativeSessionError(msg, stderr_tail=list(self.stderr_buffer))
        packet = RequestPacket(identifier=identifier, command=request)
        _ = process.stdin.write(packet.model_dump_json() + "\n")
        process.stdin.flush()
        line = TEXT_VALUE.validate_python(
            process.stdout.readline(MAX_MESSAGE_BYTES + 1),
        )
        if not line.endswith("\n") or len(line) > MAX_MESSAGE_BYTES:
            exit_code = process.poll()
            time.sleep(0.05)
            stderr_tail = list(self.stderr_buffer)
            msg = "Native worker returned an incomplete or oversized reply."
            if exit_code is not None:
                msg = f"Native worker terminated unexpectedly with code {exit_code}."
            raise NativeSessionError(msg, stderr_tail=stderr_tail)
        reply = NativeReply.model_validate_json(line)
        if reply.identifier != identifier:
            msg = "Native worker returned a reply for a different request."
            raise NativeSessionError(msg, stderr_tail=list(self.stderr_buffer))
        return reply

    def _handle_call_timeout(
        self, request: NativeRequest, identifier: str, _error: FutureTimeout,
    ) -> NativeSessionError:
        self.uncertain = True
        stderr_tail = list(self.stderr_buffer)
        self._retire()
        msg = (
            "Native operation timed out; its outcome is unknown. The worker was "
            "retired without replay. Capstone was not terminated. Reattach and "
            "inspect the application before further input."
        )
        failure = self._graph_transport_failure(
            request, identifier, "WORKER_TIMEOUT", msg,
        )
        return NativeSessionError(
            msg,
            failure,
            stderr_tail=stderr_tail,
            error_code="TIMEOUT_ERROR",
            remediation=(
                "Call capstone_attach and inspect Capstone before issuing more input. "
                "The previous operation may have partially completed."
            ),
        )

    def _handle_call_failure(
        self, request: NativeRequest, identifier: str, error: Exception,
    ) -> NativeSessionError:
        self.uncertain = True
        stderr_tail = list(self.stderr_buffer)
        self._retire()
        if isinstance(error, NativeSessionError):
            if not error.stderr_tail:
                error.stderr_tail = stderr_tail
            return error
        msg = f"Native transport failed; outcome is unknown: {error}"
        failure = self._graph_transport_failure(
            request, identifier, "TRANSPORT_FAILURE", msg,
        )
        return NativeSessionError(msg, failure, stderr_tail=stderr_tail)

    def call(self, request: NativeRequest) -> JsonValue:
        """Serialize reattachment and requests; never retry an uncertain operation."""
        if not self.lock.acquire(blocking=False):
            msg = "A native request is already active; it was not queued or replayed."
            raise NativeSessionError(msg)
        try:
            if self.retired:
                if request.operation != "attach":
                    msg = "Native session retired. Call capstone_attach before input."
                    raise NativeSessionError(msg)
                self._reset_locked()
            return self._call_locked(request)
        finally:
            self.lock.release()

    def _call_locked(self, request: NativeRequest) -> JsonValue:
        deadline = time.monotonic() + self.timeout
        identifier = uuid4().hex
        future: Future[NativeReply] = Future()

        def exchange() -> None:
            try:
                reply = self._exchange(request, identifier)
            except Exception as error:
                LOGGER.exception("Native worker transport failed")
                future.set_exception(error)
            else:
                future.set_result(reply)

        self.transport = Thread(target=exchange, daemon=True)
        self.transport.start()
        try:
            reply = future.result(timeout=max(0, deadline - time.monotonic()))
        except FutureTimeout as error:
            raise self._handle_call_timeout(request, identifier, error) from error
        except Exception as error:
            raise self._handle_call_failure(request, identifier, error) from error
        if reply.error is not None:
            if reply.graph_failure is not None:
                self.last_graph_failure = reply.graph_failure
            raise NativeSessionError(
                reply.error,
                reply.graph_failure,
                error_code=reply.error_code,
                remediation=reply.remediation,
            )
        return reply.result

    def _graph_transport_failure(
        self, request: NativeRequest, identifier: str, code: str, detail: str,
    ) -> GraphFailure | None:
        if request.operation not in GRAPH_INPUT_OPERATIONS | {
            "read_graph", "observe_graph", "create_graph",
        }:
            return None
        failure = GraphFailure(
            code=code, request_id=identifier, operation=request.operation,
            stage="transport",
            graph_input_may_have_been_sent=request.operation in
            GRAPH_INPUT_OPERATIONS | {"create_graph"},
            next_action="reattach_and_inspect", detail=detail,
        )
        self.last_graph_failure = failure
        return failure

    def _retire(self) -> None:
        """Terminate only the automation worker, with bounded reaping."""
        self.retired = True
        if not self.cleanup_lock.acquire(timeout=CLEANUP_SECONDS):
            msg = "Worker retirement is already in progress; replacement is prohibited."
            raise NativeSessionError(msg)
        try:
            self._dispose_resources()
        finally:
            self.cleanup_lock.release()

    def _terminate_process(self) -> None:
        process = self.process
        if process is None:
            return
        if process.poll() is None:
            process.kill()
        try:
            _ = process.wait(timeout=CLEANUP_SECONDS)
        except subprocess.TimeoutExpired as error:
            msg = "Worker termination is unconfirmed; replacement is prohibited."
            raise NativeSessionError(msg) from error

    def _close_streams(self) -> None:
        process = self.process
        if process is None:
            return
        if process.stdin is not None:
            process.stdin.close()
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()

    def _dispose_resources(self) -> None:
        try:
            self._terminate_process()
            _cancel_thread_io(self.transport)
            _cancel_thread_io(self._stderr_thread)
            for thread in (self.transport, self._stderr_thread):
                if thread is not None:
                    thread.join(CLEANUP_SECONDS)
                    if thread.is_alive():
                        msg = (
                            "Worker I/O did not retire; no replacement may be started."
                        )
                        raise NativeSessionError(msg)
            self._stderr_thread = None
            self._close_streams()
        finally:
            if self.job is not None:
                self.job.Close()
                self.job = None

    def reset(self) -> None:
        """Prepare a fresh session only for an explicit attach after worker loss."""
        if not self.lock.acquire(blocking=False):
            msg = "A native request is still active; reattachment was not queued."
            raise NativeSessionError(msg)
        try:
            self._reset_locked()
        finally:
            self.lock.release()

    def _reset_locked(self) -> None:
        self._retire()
        self.process = None
        self.transport = None
        self.retired = False
        self.uncertain = False
        self.stderr_buffer.clear()

    def close(self) -> None:
        """Retire without attempting to repeat or undo an uncertain native action."""
        self._retire()

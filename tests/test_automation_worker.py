# Copyright 2026 Capstone MCP contributors.
"""Exercise real process transport and retirement using exact native-entry signals."""

import socket
import subprocess
import sys
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from typing import override

import psutil
import pytest
from pydantic import TypeAdapter

from capstone_mcp import automation_worker
from capstone_mcp.automation_models import NativeReply, NativeRequest
from capstone_mcp.automation_worker import AutomationWorker, NativeSessionError


class FixtureWorker(AutomationWorker):
    """Keep the real transport and lifecycle, replacing only the native executable."""

    @override
    def _spawn(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-X", "utf8", "-u", "-m", "tests.worker_fixture"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8",
        )


def test_worker_preserves_state_and_unicode_between_calls() -> None:
    # Given
    worker = FixtureWorker()
    try:
        # When
        first = worker.call(NativeRequest(operation="windows"))
        second = worker.call(NativeRequest(operation="windows"))
        # Then
        assert first == "한글 1"
        assert second == "한글 2"
    finally:
        worker.close()
    assert worker.process is not None
    assert worker.process.poll() is not None


def test_request_and_reply_larger_than_pipe_capacity_complete_without_deadlock() -> None:
    worker = FixtureWorker(timeout=10)
    payload = "한글 data " * 100000
    try:
        assert worker.call(NativeRequest(operation="keys", value=payload)) == payload
    finally:
        worker.close()


@pytest.mark.parametrize("response", ["none", "partial", "inherited"])
def test_timeout_retires_worker_without_replaying_delivered_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, response: str,
) -> None:
    # Given: subscribe before delivering the operation; no timer decides readiness.
    delivered = tmp_path / "delivered.txt"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(10)
        port = TypeAdapter(int).validate_python(listener.getsockname()[1])

        class DeadlineAfterEntry(Future[NativeReply]):
            @override
            def result(self, timeout: float | None = None) -> NativeReply:
                assert timeout is not None
                connection = listener.accept()[0]
                with connection:
                    connection.settimeout(10)
                    assert connection.recv(7) == b"entered"
                    # Time itself is the seam: expire only after native entry.
                    raise FutureTimeout

        monkeypatch.setattr(automation_worker, "Future", DeadlineAfterEntry)
        worker = FixtureWorker()
        try:
            # When
            with pytest.raises(NativeSessionError) as failure:
                _ = worker.call(NativeRequest(
                    operation="snapshot", ref=str(delivered),
                    value=response, limit=port,
                ))
            # Then: one input, dead worker, and no implicit restart on another call.
            assert failure.value.error_code == "TIMEOUT_ERROR"
            assert failure.value.remediation is not None
            assert "capstone_attach" in failure.value.remediation
            assert delivered.read_text(encoding="utf-8") == "delivered\n"
            assert worker.process is not None
            process = worker.process
            assert process.poll() is not None
            assert worker.retired
            assert worker.transport is not None
            assert not worker.transport.is_alive()
            with pytest.raises(NativeSessionError):
                _ = worker.call(NativeRequest(operation="windows"))
            assert worker.process is process
            monkeypatch.setattr(automation_worker, "Future", Future)
            assert worker.call(NativeRequest(operation="attach")) == "한글 1"
            assert worker.process is not process
            assert not worker.retired
            assert not worker.uncertain
            assert delivered.read_text(encoding="utf-8") == "delivered\n"
        finally:
            try:
                worker.close()
            finally:
                child_path = Path(str(delivered) + ".child")
                if child_path.exists():
                    child = psutil.Process(int(child_path.read_text(encoding="utf-8")))
                    assert child.cmdline()[-2:] == ["-c", "import time; time.sleep(60)"]
                    child.kill()
                    child.wait(timeout=5)

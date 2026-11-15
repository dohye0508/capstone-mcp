# Copyright 2026 Capstone MCP contributors.
"""Telemetry ring buffer and streaming sample aggregator for Capstone sessions."""

from __future__ import annotations

import math
import time
from collections import OrderedDict, deque
from threading import Lock
from typing import Final

DEFAULT_BUFFER_CAPACITY: Final = 1000
MAX_MEASUREMENTS: Final = 256


class TelemetryBuffer:
    """Thread-safe, bounded ring buffer for streaming sensor samples."""

    def __init__(self, capacity: int = DEFAULT_BUFFER_CAPACITY) -> None:
        """Initialize telemetry buffer with bounded capacity per measurement."""
        self._capacity = max(1, capacity)
        self._buffers: OrderedDict[str, deque[tuple[float, float]]] = OrderedDict()
        self._lock = Lock()

    def push_sample(
        self,
        euid: str,
        value: float,
        timestamp: float | None = None,
    ) -> None:
        """Record a sample, evicting the least recently sampled series at capacity."""
        with self._lock:
            ts = timestamp if timestamp is not None else time.monotonic()
            if not math.isfinite(ts):
                msg = "Telemetry timestamp must be finite."
                raise ValueError(msg)
            buf = self._buffers.get(euid)
            if buf and ts < buf[-1][0]:
                msg = "Telemetry timestamps must not decrease within a measurement."
                raise ValueError(msg)
            if euid not in self._buffers:
                if len(self._buffers) == MAX_MEASUREMENTS:
                    _ = self._buffers.popitem(last=False)
                self._buffers[euid] = deque(maxlen=self._capacity)
            self._buffers[euid].append((ts, value))
            self._buffers.move_to_end(euid)

    def get_samples(
        self,
        euid: str,
        limit: int | None = None,
    ) -> list[tuple[float, float]]:
        """Retrieve recent samples as (timestamp, value) pairs."""
        if limit is not None and limit < 0:
            msg = "Sample limit must be nonnegative."
            raise ValueError(msg)
        if limit == 0:
            return []
        with self._lock:
            buf = self._buffers.get(euid)
            samples = list(buf) if buf else []
        if limit is not None and limit > 0:
            return samples[-limit:]
        return samples

    def sample_count(self, euid: str) -> int:
        """Count retained samples without copying them."""
        with self._lock:
            return len(self._buffers.get(euid, ()))

    def get_latest(self, euid: str) -> float | None:
        """Get the most recent value for a given measurement EUID."""
        with self._lock:
            buf = self._buffers.get(euid)
            return buf[-1][1] if buf else None

    def clear(self, euid: str | None = None) -> None:
        """Clear recorded samples for a specific EUID or all buffers."""
        with self._lock:
            if euid is not None:
                _ = self._buffers.pop(euid, None)
            else:
                self._buffers.clear()

    def compute_stats(self, euid: str) -> dict[str, float]:
        """Compute basic summary statistics for buffered samples."""
        vals = [value for _, value in self.get_samples(euid)]
        if not vals:
            return {"count": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}
        count = len(vals)
        mean_val = sum(vals) / count
        return {
            "count": float(count),
            "mean": mean_val,
            "min": min(vals),
            "max": max(vals),
        }

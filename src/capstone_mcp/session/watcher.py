# Copyright 2026 Capstone MCP contributors.
"""Threshold condition monitoring and trigger evaluation for Capstone sessions."""

from __future__ import annotations

import logging
import operator
import time
from threading import Event
from typing import TYPE_CHECKING, Annotated, Any, Final

from pydantic import Field, FiniteFloat

from capstone_mcp.models import Model

if TYPE_CHECKING:
    from collections.abc import Callable

LOGGER: Final = logging.getLogger(__name__)

COMPARATORS: Final[dict[str, Callable[[float, float], bool]]] = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    "=": operator.eq,
    "above": operator.gt,
    "below": operator.lt,
    "reaches": operator.ge,
}


class StopCondition(Model):
    """Threshold specification for monitoring and halting recording."""

    measurement_euid: str
    operator: str
    threshold: FiniteFloat
    unit_type: int = 0
    timeout: Annotated[FiniteFloat, Field(gt=0)] = 10.0
    poll_interval: Annotated[FiniteFloat, Field(gt=0)] = 0.05


class StopConditionTrigger(Model):
    """Evaluation result for threshold stop conditions."""

    triggered: bool
    current_value: float | None
    threshold: float
    operator: str
    elapsed_seconds: float
    detail: str


class ConditionWatcher:
    """Monitors live sensor streams against user-defined threshold conditions."""

    @staticmethod
    def evaluate(
        current_value: float,
        operator_str: str,
        threshold: float,
    ) -> bool:
        """Check if current value satisfies the stop condition threshold."""
        op_fn = COMPARATORS.get(operator_str.strip().lower())
        if op_fn is None:
            msg = f"Unsupported threshold operator: {operator_str!r}"
            raise ValueError(msg)
        return op_fn(current_value, threshold)

    def monitor(
        self,
        condition: StopCondition,
        sampler: Callable[[], float],
        *,
        halt_callback: Callable[[], Any] | None = None,
        cancel: Event | None = None,
    ) -> StopConditionTrigger:
        """Poll until threshold, cancellation, or deadline; always request halt."""
        # Reject invalid configuration before starting the monitoring lifecycle.
        _ = self.evaluate(0.0, condition.operator, condition.threshold)
        try:
            return self._monitor(condition, sampler, cancel or Event())
        finally:
            if halt_callback is not None:
                halt_callback()

    def _monitor(
        self, condition: StopCondition, sampler: Callable[[], float], cancel: Event,
    ) -> StopConditionTrigger:
        start_time = time.monotonic()
        deadline = start_time + condition.timeout
        next_sample = start_time
        last_val = None

        while True:
            elapsed = time.monotonic() - start_time
            if cancel.is_set() or time.monotonic() >= deadline:
                return StopConditionTrigger(
                    triggered=False,
                    current_value=last_val,
                    threshold=condition.threshold,
                    operator=condition.operator,
                    elapsed_seconds=elapsed,
                    detail="Monitoring cancelled." if cancel.is_set() else (
                        f"Timeout of {condition.timeout:.1f}s exceeded "
                        "before threshold was met."
                    ),
                )

            val = sampler()
            last_val = val

            if cancel.is_set() or time.monotonic() >= deadline:
                continue

            if self.evaluate(val, condition.operator, condition.threshold):
                return StopConditionTrigger(
                    triggered=True,
                    current_value=val,
                    threshold=condition.threshold,
                    operator=condition.operator,
                    elapsed_seconds=time.monotonic() - start_time,
                    detail=(
                        f"Stop condition triggered: {val} {condition.operator} "
                        f"{condition.threshold}"
                    ),
                )

            next_sample += condition.poll_interval
            now = time.monotonic()
            # Skip missed slots instead of issuing a burst of stale polls.
            next_sample = max(next_sample, now)
            _ = cancel.wait(max(0.0, min(next_sample, deadline) - now))

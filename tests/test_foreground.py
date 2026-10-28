# Copyright 2026 Capstone MCP contributors.
"""Explicit opt-out remains effective without touching the desktop."""

import pytest

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.repetition import AcquisitionJobs, RepeatPlan


def test_keyboard_opt_out_rejects_input_before_window_lookup() -> None:
    # Given
    app = Capstone()
    # When / Then
    with pytest.raises(AutomationError):
        _ = app.keys(0, "{ESC}", allow_foreground=False)


def test_repeat_opt_out_rejects_job_before_native_connection() -> None:
    # Given
    jobs = AcquisitionJobs()
    plan = RepeatPlan(
        process_id=1, window_handle=1, duration_seconds=1,
        allow_foreground=False,
    )
    # When / Then
    with pytest.raises(AutomationError):
        _ = jobs.start(plan)
    assert not jobs.jobs

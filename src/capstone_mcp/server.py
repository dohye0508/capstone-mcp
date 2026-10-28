# Copyright 2026 Capstone MCP contributors.
"""Stdio MCP entry point for Capstone UI inspection and operation."""

from typing import Annotated, Final, Literal
from uuid import UUID

from mcp.server.fastmcp import FastMCP, Image
from pydantic import Field

from capstone_mcp.acquisition import (
    RecordingRequest,
    RecordingStatus,
    SamplingRateChange,
    observe_recording,
    request_recording,
    step_sampling_rate,
)
from capstone_mcp.analysis import (
    FitInput,
    LinearFit,
    RunComparison,
    RunSamples,
    compare_runs,
    linear_fit,
)
from capstone_mcp.bridge import NativeInventory, read_inventory, read_measurement
from capstone_mcp.capfile_models import (
    CapConfiguration,
    CapDatasetPage,
    CapDatasetSummary,
)
from capstone_mcp.capfiles import extract_cap_datasets, read_cap_configuration
from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.models import Action, Button, Point, Result, Snapshot, Window
from capstone_mcp.plotting import PlotInput, render_plot
from capstone_mcp.repetition import AcquisitionJobs, JobStatus, RepeatPlan

APP: Final = Capstone()
JOBS: Final = AcquisitionJobs()
MCP: Final = FastMCP(
    "capstone",
    host="127.0.0.1",
    port=8766,
    instructions=(
        "Attach, list windows, then snapshot before acting. References expire after "
        "a new snapshot or action. Inspect again to verify outcomes. Window handles "
        "are restricted to Capstone. Screenshots target the window HWND. "
        "Ask the user before overwriting files or operating hardware."
    ),
)


@MCP.tool()
def capstone_recording_status(handle: int) -> RecordingStatus:
    """Read actual recording toggle, enabled state, and displayed time/rate."""
    state, _ = observe_recording(APP, handle)
    return state


@MCP.tool()
def capstone_set_recording(
    handle: int, *, recording: bool, allow_foreground: bool = False,
) -> RecordingRequest:
    """Request start/stop only when the observed state differs from the request.

    Requires configured hardware/data sources and explicit foreground input.
    transition_pending=true means the requested state has not yet been observed;
    it is not a claim that acquisition succeeded.
    """
    JOBS.require_idle()
    return request_recording(
        APP, handle, recording=recording, allow_foreground=allow_foreground,
    )


@MCP.tool()
def capstone_step_sampling_rate(
    handle: int, direction: Literal["increase", "decrease"], expected_sensor: str,
    *, allow_foreground: bool = False,
) -> SamplingRateChange:
    """Move one supported rate step for the explicitly named selected sensor.

    Read the sensor name from a fresh snapshot. Uses Capstone's native discrete
    rate buttons, not a guessed frequency setter; recording must be stopped.
    """
    JOBS.require_idle()
    return step_sampling_rate(
        APP, handle, direction, expected_sensor=expected_sensor,
        allow_foreground=allow_foreground,
    )


@MCP.tool()
def capstone_repeat_acquisition(plan: RepeatPlan) -> JobStatus:
    """Start bounded repeated runs, confirming native start/stop events each cycle.

    Requires the debug endpoint and UI to belong to the same Capstone process,
    an enabled recording source, and explicit foreground opt-in. Runs remain in
    Capstone; save the experiment separately before extracting their arrays.
    """
    return JOBS.start(plan)


@MCP.tool()
def capstone_acquisition_job(job_id: str) -> JobStatus:
    """Read a repeat job's completion and confirmed-cycle receipts."""
    return JOBS.status(job_id)


@MCP.tool()
def capstone_cancel_acquisition(job_id: str) -> JobStatus:
    """Request cancellation; completion requires the worker to stop recording."""
    return JOBS.cancel(job_id)


@MCP.tool()
def capstone_plot(samples: PlotInput) -> Image:
    """Render paired numeric data as a PNG, optionally showing an OLS fit.

    Produces a standalone graph for the AI/user; does not modify Capstone pages.
    Supply explicit axis labels including units from the source metadata.
    """
    return Image(data=render_plot(samples), format="png")


@MCP.tool()
def capstone_inspect_file(path: str) -> CapConfiguration:
    """Read saved .cap hardware/settings, source metadata, pages and calculations.

    Does not open the file in Capstone or infer live hardware connectivity.
    Array decoding is independent, so unknown recorded storage types do not
    prevent configuration inspection.
    """
    return read_cap_configuration(path)


@MCP.tool()
def capstone_file_datasets(path: str) -> list[CapDatasetSummary]:
    """List decodable saved datasets with source IDs, unit IDs and sample counts.

    Supports type-7 strings and type-0 tagged doubles, with stored, interval,
    or implicit-index independent coordinates.
    Unsupported array encodings raise an error instead of reporting empty data.
    """
    return [
        CapDatasetSummary(
            index=index, dataset_id=dataset.data_set_id,
            source_euid=dataset.source_euid, name=dataset.source_name,
            unit_id=dataset.unit_id, value_kind=dataset.value_kind,
            count=len(dataset.raw_values),
        )
        for index, dataset in enumerate(extract_cap_datasets(path))
    ]


@MCP.tool()
def capstone_extract_dataset(
    path: str, dataset_index: Annotated[int, Field(ge=0)],
    offset: Annotated[int, Field(ge=0)] = 0,
    limit: Annotated[int, Field(ge=1, le=10_000)] = 1000,
) -> CapDatasetPage:
    """Extract one sample page from a saved dataset, preserving original text.

    Numeric decimals are serialized losslessly as decimal strings. Implicit
    sample_indices are indices, not seconds. Use list tools to select the dataset.
    """
    datasets = extract_cap_datasets(path)
    if dataset_index >= len(datasets):
        msg = "Dataset index is outside this file's dataset list."
        raise AutomationError(msg)
    dataset = datasets[dataset_index]
    end = offset + limit
    return CapDatasetPage(
        dataset=CapDatasetSummary(
            index=dataset_index, dataset_id=dataset.data_set_id,
            source_euid=dataset.source_euid, name=dataset.source_name,
            unit_id=dataset.unit_id, value_kind=dataset.value_kind,
            count=len(dataset.raw_values),
        ),
        offset=offset,
        sample_indices=dataset.sample_indices[offset:end],
        raw_values=dataset.raw_values[offset:end],
        numeric_values=(
            None if dataset.numeric_values is None
            else dataset.numeric_values[offset:end]
        ),
        independent_values=dataset.independent_values[offset:end],
        independent_kind=dataset.independent_kind,
    )


@MCP.tool()
def capstone_linear_fit(samples: FitInput) -> LinearFit:
    """Fit supplied paired numeric samples with an intercept and standard errors.

    Performs local ordinary least squares, not a click on Capstone's fit menu.
    Standard errors assume independent residuals with common variance.
    Keep samples in their original units; no automatic unit conversion is applied.
    """
    return linear_fit(samples)


@MCP.tool()
def capstone_compare_runs(
    runs: Annotated[list[RunSamples], Field(min_length=2, max_length=50)],
) -> list[RunComparison]:
    """Compare run means, sample deviations and ranges in a common supplied unit.

    Does not start measurements or assume time alignment between runs.
    """
    return compare_runs(runs)


@MCP.tool()
def capstone_live_configuration(
    debug_port: Annotated[int, Field(ge=1024, le=65535)] = 9223,
) -> NativeInventory:
    """Read native sensor/measurement metadata without screen scraping.

    Requires Capstone started with QTWEBENGINE_REMOTE_DEBUGGING=127.0.0.1:PORT.
    This returns the application's configured metadata, not proof that every
    listed sensor is physically connected.
    """
    return read_inventory(debug_port)


@MCP.tool()
def capstone_current_value(
    measurement_euid: UUID,
    unit_type: Annotated[int, Field(ge=0)],
    debug_port: Annotated[int, Field(ge=1024, le=65535)] = 9223,
) -> float:
    """Read one native current value using IDs returned by live configuration.

    Unavailable values raise an error rather than returning a fabricated zero.
    This is not an extraction of an entire recorded run.
    """
    return read_measurement(debug_port, "{" + str(measurement_euid) + "}", unit_type)


@MCP.tool()
def capstone_attach(
    *, launch: bool = False,
    process_id: Annotated[int, Field(gt=0)] | None = None,
) -> list[Window]:
    """Attach to installed Capstone, optionally selecting an exact process ID."""
    JOBS.require_idle()
    return APP.attach(launch=launch, process_id=process_id)


@MCP.tool()
def capstone_windows() -> list[Window]:
    """List Capstone windows, including file dialogs and modal dialogs."""
    return APP.windows()


@MCP.tool()
def capstone_snapshot(
    handle: int,
    depth: Annotated[int, Field(ge=1, le=30)] = 12,
    limit: Annotated[int, Field(ge=1, le=3000)] = 800,
) -> Snapshot:
    """Read control names, roles, bounds, and fresh action references."""
    return APP.snapshot(handle, depth, limit)


@MCP.tool()
def capstone_action(
    ref: str, action: Action, *, allow_foreground: bool = False,
) -> Result:
    """Activate by click (invoke), or use UIA toggle/select/expand/collapse/focus.

    Invoke requires allow_foreground=true. Avoids Capstone's blocking modal
    InvokePattern provider; this is physical input, not background UIA Invoke.
    """
    JOBS.require_idle()
    return APP.act(ref, action, allow_foreground=allow_foreground)


@MCP.tool()
def capstone_read_value(ref: str) -> str:
    """Read literal current text from a control's UIA Value pattern."""
    return APP.control(ref).iface_value.CurrentValue


@MCP.tool()
def capstone_set_value(ref: str, value: str) -> Result:
    """Set literal text in a control supporting the UIA Value pattern."""
    JOBS.require_idle()
    return APP.set_value(ref, value)


@MCP.tool()
def capstone_screenshot(handle: int) -> Image:
    """Capture PNG pixels at native resolution; does not raise the window."""
    return Image(data=APP.screenshot(handle), format="png")


@MCP.tool()
def capstone_click(
    handle: int, point: Point, button: Button = Button.LEFT,
    *, double: bool = False, allow_foreground: bool = False,
) -> Result:
    """Click window-relative pixels. Requires explicit foreground input opt-in."""
    JOBS.require_idle()
    if not allow_foreground:
        msg = "Physical input changes focus. Set allow_foreground=true explicitly."
        raise AutomationError(msg)
    window = APP.focus_window(handle)
    rect = window.rectangle()
    x, y = point.x, point.y
    if not (0 <= x < rect.right - rect.left and 0 <= y < rect.bottom - rect.top):
        msg = "Coordinates must be inside the current window rectangle."
        raise AutomationError(msg)
    window.click_input(
        button=button.value, coords=(rect.left + x, rect.top + y),
        double=double, absolute=True,
    )
    APP.refs.clear()
    return Result(detail="Click delivered; inspect the window to verify.")


@MCP.tool()
def capstone_drag(
    handle: int, start: Point, end: Point, *, allow_foreground: bool = False,
) -> Result:
    """Drag between window-relative pixels, releasing the button even on failure."""
    JOBS.require_idle()
    if not allow_foreground:
        msg = "Dragging changes focus. Set allow_foreground=true explicitly."
        raise AutomationError(msg)
    window = APP.focus_window(handle)
    rect = window.rectangle()
    for point in (start, end):
        if not (
            0 <= point.x < rect.right - rect.left
            and 0 <= point.y < rect.bottom - rect.top
        ):
            msg = "Both drag endpoints must be inside the window."
            raise AutomationError(msg)
    try:
        _ = window.drag_mouse_input(
            src=(rect.left + start.x, rect.top + start.y),
            dst=(rect.left + end.x, rect.top + end.y), absolute=True,
        )
    finally:
        _ = window.release_mouse_input(
            coords=(rect.left + end.x, rect.top + end.y), absolute=True,
        )
        APP.refs.clear()
    return Result(detail="Drag delivered; inspect to verify.")


@MCP.tool()
def capstone_scroll(
    handle: int, point: Point,
    notches: Annotated[int, Field(ge=-100, le=100)],
    *, allow_foreground: bool = False,
) -> Result:
    """Scroll at window-relative pixels; positive notches scroll upward."""
    JOBS.require_idle()
    if not allow_foreground:
        msg = "Scrolling changes focus. Set allow_foreground=true explicitly."
        raise AutomationError(msg)
    window = APP.focus_window(handle)
    rect = window.rectangle()
    if not (
        0 <= point.x < rect.right - rect.left
        and 0 <= point.y < rect.bottom - rect.top
    ):
        msg = "Scroll position must be inside the window."
        raise AutomationError(msg)
    _ = window.wheel_mouse_input(coords=(point.x, point.y), wheel_dist=notches)
    APP.refs.clear()
    return Result(detail="Scroll delivered; inspect to verify.")


@MCP.tool()
def capstone_keys(
    handle: int, keys: str, *, allow_foreground: bool = False,
) -> Result:
    """Send pywinauto key syntax: ^o, {ESC}, {ENTER}, %{F4}. Changes focus."""
    JOBS.require_idle()
    return APP.keys(handle, keys, allow_foreground=allow_foreground)


@MCP.tool()
def capstone_type_text(
    handle: int, text: str, *, allow_foreground: bool = False,
) -> Result:
    """Type literal Unicode text in the focused field, escaping shortcut syntax."""
    JOBS.require_idle()
    escaped = "".join(
        "{" + char + "}" if char in "+^%~(){}" else char for char in text
    )
    return APP.keys(
        handle, escaped, allow_foreground=allow_foreground, unicode_input=True,
    )


def main() -> None:
    """Serve MCP over stdio; diagnostics must never go to stdout."""
    MCP.run(transport="stdio")


def http_main() -> None:
    """Serve only on loopback for local MCP clients supporting HTTP."""
    MCP.run(transport="streamable-http")


if __name__ == "__main__":
    main()

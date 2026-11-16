# Copyright 2026 Capstone MCP contributors.
"""Tool router for graphs, tables, digits displays, and workbook pages."""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Final

from anyio import to_thread
from mcp.server.fastmcp import FastMCP
from mcp.types import (
    CallToolResult,
    ImageContent,
    TextContent,
    ToolAnnotations,
)
from pydantic import JsonValue, TypeAdapter

from capstone_mcp.automation_models import NativeRequest
from capstone_mcp.displays import (
    DisplayAction,
    DisplayRequest,
    DisplayResult,
)
from capstone_mcp.graphs import (
    GraphAction,
    GraphCapture,
    GraphFailure,
    GraphRequest,
    GraphResult,
    read_saved_graph,
)

type NativeCaller = Callable[..., Awaitable[Any]]
JSON_VALUE: Final = TypeAdapter(JsonValue)


def register_display_tools(
    mcp: FastMCP,
    native: NativeCaller,
    get_last_failure: Callable[[], GraphFailure | None] | None = None,
) -> dict[str, Any]:
    """Register all graph, table, digits, and display layout tools."""
    del get_last_failure

    async def manage_graph(request: GraphRequest) -> GraphResult | CallToolResult:
        if request.action == GraphAction.OBSERVE:
            observe = request.observe
            if observe is None or not observe.allow_foreground:
                msg = "Graph observation requires a handle and allow_foreground=true."
                raise ValueError(msg)
            capture = GraphCapture.model_validate(await native(
                NativeRequest(operation="observe_graph", handle=observe.handle),
                mutates=True,
            ))
            result = GraphResult(action=request.action, observe=capture.frame)
            return CallToolResult(
                content=[
                    ImageContent(type="image", data=capture.png_base64, mimeType="image/png"),
                    TextContent(type="text", text=result.model_dump_json()),
                ],
                structuredContent=result.model_dump(mode="json"),
            )
        if (
            request.action == GraphAction.READ
            and request.read is not None
            and request.read.cap_file is not None
        ):
            saved = await to_thread.run_sync(
                read_saved_graph, request.read.cap_file, request.read.graph_index,
            )
            return GraphResult(action=request.action, read=saved)
        return GraphResult.model_validate(
            await native(
                NativeRequest(
                    operation="manage_graph",
                    graph_request=JSON_VALUE.validate_json(request.model_dump_json()),
                ),
                mutates=request.action != GraphAction.READ,
            ),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Unified graph management seam",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def capstone_manage_graph(
        request: GraphRequest,
    ) -> Annotated[CallToolResult, GraphResult]:
        """Unified entry point for all Capstone graph display operations.

        Supported actions (request.action):
        - create: Insert a new graph onto active page (request.create)
        - read: Read graph curves, fits, and data signatures (request.read)
          Set request.read.cap_file to read a saved archive without the desktop.
          Set request.read.graph_index (zero-based workbook order) for multiple graphs.
        - observe: Capture a fresh screenshot and one-use frame_id
          (request.observe, requires allow_foreground=true)
        - fit: Scale graph axes using an observed offset and frame_id (request.fit)
        - select_measurement: Select axis measurement via popup menu path
          (request.select_measurement, requires a fresh frame_id)
        - toolbox_delta: Measure coordinates difference with delta crosshair
          (request.toolbox_delta)
        - toolbox_area: Integrate area under curve with area tool
          (request.toolbox_area)
        - toolbox_statistics: Toggle statistics box and read summary stats
          (request.toolbox_statistics)
        - analyze: Set axes, fit curves, and compile analytical report
          (request.analyze)
        """
        result = await manage_graph(request)
        if isinstance(result, CallToolResult):
            return result
        return CallToolResult(
            content=[TextContent(type="text", text=result.model_dump_json())],
            structuredContent=result.model_dump(mode="json"),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Unified display and workbook management seam",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def capstone_manage_display(
        request: DisplayRequest,
    ) -> DisplayResult:
        """Unified entry point for all Capstone display and workbook operations.

        Supported actions (request.action):
        - create_digits: Insert Digits display and monitor numeric readout
        - create_table: Insert Table display widget on active page
        - set_table_columns: Configure measurement columns for Table display
        - read_table: Extract tabular rows, pagination, and statistics
        - create_scope: Insert Oscilloscope display widget
        - set_scope_trigger: Configure scope hardware trigger level/slope/mode
        - create_fft: Insert FFT frequency spectrum display
        - read_fft_peaks: Read detected spectral peak frequencies and amplitudes
        - add_page: Add a new workbook page tab
        - set_page_layout: Apply multi-display split grid layout template
        """
        return DisplayResult.model_validate(
            await native(
                NativeRequest(
                    operation="manage_display",
                    display_request=JSON_VALUE.validate_json(
                        request.model_dump_json(),
                    ),
                ),
                mutates=request.action not in (
                    DisplayAction.READ_TABLE,
                    DisplayAction.READ_FFT_PEAKS,
                ),
            ),
        )

    return {
        "capstone_manage_display": capstone_manage_display,
        "capstone_manage_graph": manage_graph,
    }


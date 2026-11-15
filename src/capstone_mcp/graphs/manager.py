# Copyright 2026 Capstone MCP contributors.
"""Unified Graph Manager engine and functional manage_graph seam."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.displays import click_control
from capstone_mcp.graphs.inspection import (
    MENU_RELEASE_ATTEMPTS,
    close_menus,
    menu_item_disabled,
    read_graph,
    release_menu_bar,
    summarize_graph,
    verify_graph_binding,
)
from capstone_mcp.graphs.models import (
    FIT_ROWS,
    FIT_SUCCESS_STATUSES,
    FIT_TYPES,
    SUPPORTED_FIT_MODES,
    AnalyzeGraphRequest,
    AnalyzeGraphResult,
    CreateGraphRequest,
    CreateGraphResult,
    FitGraphRequest,
    FitGraphResult,
    GraphAction,
    GraphDeltaRequest,
    GraphDeltaResult,
    GraphFitOutcome,
    GraphProgress,
    GraphRequest,
    GraphResult,
    GraphState,
    MeasureGraphAreaRequest,
    MeasureGraphAreaResult,
    ReadGraphRequest,
    ReadGraphResult,
    SelectMeasurementRequest,
    SelectMeasurementResult,
    SetGraphFitsRequest,
    ToggleGraphStatisticsRequest,
    ToggleGraphStatisticsResult,
)
from capstone_mcp.graphs.toolbox import (
    _find_graph_control,
    graph_delta,
    measure_graph_area,
    toggle_graph_statistics,
)
from capstone_mcp.models import Bounds, Point, Result, Snapshot

if TYPE_CHECKING:
    from collections.abc import Callable

try:
    import win32api
    import win32gui
    import win32process

    from capstone_mcp.ui_events import WindowEvents
except ImportError:
    win32api = None  # type: ignore[assignment]
    win32gui = None  # type: ignore[assignment]
    win32process = None  # type: ignore[assignment]
    WindowEvents = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)

TRANSITION_SECONDS: Final = 15


# ---------------------------------------------------------------------------
# 1. Menu Interaction Helpers
# ---------------------------------------------------------------------------


def invoke_graph_menu(
    app: Capstone,
    ref: str,
    *,
    screen_point: Point | None = None,
) -> None:
    """Click an open menu item without activating its transient Qt window."""
    if win32gui is not None and win32process is not None:
        foreground = win32gui.GetForegroundWindow()
        if win32process.GetWindowThreadProcessId(foreground)[1] != app.pid:
            msg = "Capstone lost foreground focus; no menu input was sent."
            raise AutomationError(msg)
    control = app.control(ref)
    bounds = control.rectangle()
    point = screen_point or Point(
        x=(bounds.left + bounds.right) // 2,
        y=(bounds.top + bounds.bottom) // 2,
    )
    control.click_input(button="left", coords=(point.x, point.y), absolute=True)
    app.refs.clear()


def ready_graph_menu(app: Capstone, before: set[int], name: str) -> Snapshot | None:
    """Observe a newly opened menu only after its requested item is usable."""
    for window in app.windows():
        if window.handle in before:
            continue
        try:
            snapshot = app.snapshot(window.handle, 5, 500)
        except Exception as e:  # noqa: BLE001
            logger.debug(
                "Failed to snapshot window %s: %s",
                window.handle,
                e,
            )
            continue
        if any(
            c.name == name and c.control_type == "MenuItem" and c.enabled and c.visible
            for c in snapshot.controls
        ):
            return snapshot
    return None


def _matches_fit_popup(snapshot: Snapshot, label: str | None) -> bool:
    if snapshot.truncated:
        return False
    items = [c for c in snapshot.controls
             if c.control_type == "MenuItem" and c.visible and c.enabled]
    if label is not None:
        named = [c for c in items if c.name == label]
        if len(named) > 1:
            msg = "Observed fit label matches multiple menu items."
            raise AutomationError(msg)
        return len(named) == 1
    return (len(items) == 1 and not items[0].name
            and not snapshot.controls[0].automation_id)


def _fit_menu(
    app: Capstone, before: set[int], label: str | None = None,
) -> Snapshot | None:
    candidates: list[int] = []
    for window in app.windows():
        if window.handle in before or (
            label is None and window.title != "PASCO Capstone"
        ):
            continue
        try:
            snapshot = app.snapshot(window.handle, 3, 100)
        except Exception as error:  # noqa: BLE001
            logger.debug("Failed to snapshot fit window %s: %s", window.handle, error)
            continue
        if _matches_fit_popup(snapshot, label):
            candidates.append(window.handle)
    if len(candidates) > 1:
        msg = "Multiple native fit popups appeared; no fit menu was selected."
        raise AutomationError(msg)
    if not candidates:
        return None
    # snapshot() replaces app.refs globally: scanning a later window invalidates
    # earlier refs. Reacquire and validate the unique target after the scan.
    current = app.snapshot(candidates[0], 3, 100)
    return current if _matches_fit_popup(current, label) else None


def _fit_popup_bounds(app: Capstone, popup: Snapshot) -> Bounds:
    """Validate fresh owned popup geometry against a physical monitor, not its owner."""
    if win32api is None:
        msg = "Fit popup visibility requires Windows monitor geometry."
        raise AutomationError(msg)
    # window() verifies process ownership and visibility on every call.
    rect = app.window(popup.window.handle).rectangle()
    current = Bounds(left=rect.left, top=rect.top, right=rect.right, bottom=rect.bottom)
    if current != popup.window.bounds:
        msg = (
            "Fit popup moved since inspection; inspect it again before choosing a fit."
        )
        raise AutomationError(msg)
    if current.right <= current.left or current.bottom <= current.top:
        msg = "Fit popup has empty bounds; no fit was selected."
        raise AutomationError(msg)
    # Pywin32 exposes this API at runtime; its bundled stub omits it.
    monitors = [entry[2] for entry in win32api.EnumDisplayMonitors()]  # pyright: ignore[reportAttributeAccessIssue]
    if not any(
        left <= current.left
        and top <= current.top
        and current.right <= right
        and current.bottom <= bottom
        for left, top, right, bottom in monitors
    ):
        msg = "Fit popup is not wholly on a monitor; reposition it before choosing."
        raise AutomationError(msg)
    return current


def _require_popup_point(bounds: Bounds, point: Point) -> None:
    if not (bounds.left <= point.x < bounds.right
            and bounds.top <= point.y < bounds.bottom):
        msg = "Fit item lies outside its popup; no selection was sent."
        raise AutomationError(msg)


def _toggle_fit(  # noqa: PLR0913
    app: Capstone,
    handle: int,
    point: Point,
    native_type: int,
    *,
    allow_foreground: bool = True,
    menu_label: str | None = None,
) -> Result:
    """Toggle one known native model; callers must verify the copied state."""
    if not allow_foreground:
        msg = "Graph fitting requires foreground input."
        raise AutomationError(msg)
    if native_type not in FIT_ROWS:
        msg = "Unknown native fit type; no fit menu was opened."
        raise AutomationError(msg)
    window = app.window(handle)
    rect = window.rectangle()
    if not (
        0 <= point.x < rect.right - rect.left and 0 <= point.y < rect.bottom - rect.top
    ):
        msg = "Fit-menu anchor must be inside the current window."
        raise AutomationError(msg)
    before = {w.handle for w in app.windows()}
    app.require_input_ready(handle)
    if WindowEvents is None:
        msg = "WindowEvents requires Windows environment."
        raise AutomationError(msg)
    with WindowEvents(window.process_id()) as events:
        _ = app.focus_window(handle)
        window.click_input(button="left", coords=(point.x, point.y))
        try:
            popup = events.changes.until(
                lambda: _fit_menu(app, before, menu_label),
                TRANSITION_SECONDS,
                description=f"Native fit menu at {point}",
            )
            bounds = _fit_popup_bounds(app, popup)
            if menu_label is not None:
                item = next(c for c in popup.controls
                            if c.control_type == "MenuItem" and c.name == menu_label
                            and c.visible and c.enabled)
                click_point = Point(
                    x=(item.bounds.left + item.bounds.right) // 2,
                    y=(item.bounds.top + item.bounds.bottom) // 2,
                )
            else:
                item = next(c for c in popup.controls if c.control_type == "MenuItem")
                click_point = Point(
                    x=(bounds.left + bounds.right) // 2,
                    y=bounds.top + (bounds.bottom - bounds.top)
                    * (2 * FIT_ROWS[native_type] + 1) // 48,
                )
            _require_popup_point(bounds, click_point)
            app.require_uncovered(popup.window.handle, (click_point.x, click_point.y))
            invoke_graph_menu(app, item.ref, screen_point=click_point)
            _ = app.keys(handle, "{ESC}")
            _ = events.changes.until(
                lambda: True if {w.handle for w in app.windows()} == before else None,
                TRANSITION_SECONDS,
            )
        except Exception:
            try:
                close_menus(app, handle)
            except Exception:
                logger.exception("Fit cleanup failed; preserving the original error.")
            raise
    return Result(
        detail=f"Native fit type {native_type} toggled; verify copied graph state.",
    )


def _read_fitting_graph(
    app: Capstone, handle: int, request: SetGraphFitsRequest,
) -> GraphState:
    if (request.display_menu_label == "Display"
            and request.copy_display_label == "Copy Display"):
        return read_graph(app, handle, allow_foreground=request.allow_foreground)
    return read_graph(
        app, handle, allow_foreground=request.allow_foreground,
        display_menu_label=request.display_menu_label,
        copy_display_label=request.copy_display_label,
    )


def _enable_fitting(
    app: Capstone,
    handle: int,
    point: Point | None,
    request: SetGraphFitsRequest | None = None,
) -> GraphState:
    if point is None:
        msg = "Native fitting remained disabled; inspect the fit toolbar."
        raise AutomationError(msg)
    window = app.window(handle)
    rect = window.rectangle()
    if not (
        0 <= point.x < rect.right - rect.left and 0 <= point.y < rect.bottom - rect.top
    ):
        msg = "Fit icon anchor must be inside the current window."
        raise AutomationError(msg)
    _ = app.focus_window(handle)
    window.click_input(button="left", coords=(point.x, point.y))
    if request is not None:
        return _read_fitting_graph(app, handle, request)
    return read_graph(app, handle)


# ---------------------------------------------------------------------------
# 2. Individual Operational Functions
# ---------------------------------------------------------------------------


def create_graph(
    app: Capstone,
    handle_or_request: int | CreateGraphRequest | None = None,
    *,
    allow_foreground: bool = True,
) -> CreateGraphResult:
    """Insert a graph into the active page through its display palette item."""
    if isinstance(handle_or_request, CreateGraphRequest):
        request = handle_or_request
    elif isinstance(handle_or_request, int):
        request = CreateGraphRequest(
            handle=handle_or_request,
            allow_foreground=allow_foreground,
        )
    elif handle_or_request is None:
        request = CreateGraphRequest(allow_foreground=allow_foreground)
    else:
        request = CreateGraphRequest(
            handle=int(handle_or_request),
            allow_foreground=allow_foreground,
        )

    if not request.allow_foreground:
        msg = "Graph creation requires foreground input."
        raise AutomationError(msg)

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    if snapshot.truncated:
        msg = "Graph palette selection requires a complete snapshot."
        raise AutomationError(msg)
    matches = [
        c
        for c in snapshot.controls
        if c.name == request.palette_label
        and c.control_type in ("Text", "Button", "ListItem", "Custom")
        and c.visible
        and c.enabled
    ]
    if len(matches) != 1:
        msg = "Expected one Graph display palette item; inspect the current page."
        raise AutomationError(msg)

    palette_item = matches[0]
    click_control(
        app,
        request.handle,
        palette_item,
        double=True,
        allow_foreground=True,
    )
    return CreateGraphResult(
        detail="Graph inserted; inspect a fresh screenshot before selecting axes.",
        verified=False,
    )


def fit_graph(
    app: Capstone,
    request: FitGraphRequest | None = None,
) -> FitGraphResult:
    """Dispatch an explicitly observed graph action offset without claiming readback."""
    if request is None:
        request = FitGraphRequest()
    if request.mode not in SUPPORTED_FIT_MODES:
        msg = (
            f"Unsupported mode '{request.mode}'. Supported modes: {SUPPORTED_FIT_MODES}"
        )
        raise AutomationError(msg)
    if not request.allow_foreground:
        msg = "Graph scaling requires allow_foreground=true."
        raise AutomationError(msg)
    if request.offset is None:
        msg = "Provide an observed toolbar offset; no default graph click is safe."
        raise AutomationError(msg)

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    if snapshot.truncated:
        msg = "Graph scaling requires a complete snapshot."
        raise AutomationError(msg)
    target_ctrl = _find_graph_control(snapshot.controls, request.graph_name)
    if not (
        0 <= request.offset.x < target_ctrl.bounds.right - target_ctrl.bounds.left
        and 0 <= request.offset.y < target_ctrl.bounds.bottom - target_ctrl.bounds.top
    ):
        msg = "Observed toolbar offset must be inside the selected graph."
        raise AutomationError(msg)

    target_x = target_ctrl.bounds.left + request.offset.x
    target_y = target_ctrl.bounds.top + request.offset.y

    app.click_point(
        request.handle,
        target_x,
        target_y,
        button="left",
        allow_foreground=request.allow_foreground,
    )

    detail = (
        f"Dispatched {request.mode} click at ({target_x}, {target_y}) "
        f"on graph '{target_ctrl.name or target_ctrl.ref}'; "
        "axis bounds have not been verified."
    )
    return FitGraphResult(
        mode=request.mode,
        target_ref=target_ctrl.ref,
        clicked_point=(target_x, target_y),
        verified=False,
        detail=detail,
    )


def select_graph_measurement(
    app: Capstone,
    handle: int,
    point: Point,
    path: list[str],
    *,
    allow_foreground: bool = True,
) -> Result:
    """Open an observed axis label and choose an exact native measurement path."""
    if not allow_foreground:
        msg = "Graph axis selection requires foreground input."
        raise AutomationError(msg)
    if not path or any(not part for part in path):
        msg = "Provide a nonempty exact measurement menu path."
        raise AutomationError(msg)

    window = app.window(handle)
    rect = window.rectangle()
    if not (
        0 <= point.x < rect.right - rect.left and 0 <= point.y < rect.bottom - rect.top
    ):
        msg = "Axis anchor must be inside the current window."
        raise AutomationError(msg)

    before = {w.handle for w in app.windows()}
    app.require_input_ready(handle)

    if WindowEvents is None:
        msg = "WindowEvents requires Windows pywin32 environment."
        raise AutomationError(msg)

    with WindowEvents(window.process_id()) as events:
        _ = app.focus_window(handle)
        window.click_input(button="left", coords=(point.x, point.y))
        for name in path:
            menu = events.changes.until(
                lambda selected=name: ready_graph_menu(app, before, selected),
                TRANSITION_SECONDS,
            )
            matches = [
                c
                for c in menu.controls
                if c.control_type == "MenuItem"
                and c.name == name
                and c.visible
                and c.enabled
            ]
            if len(matches) != 1:
                msg = f"Measurement menu entry is ambiguous or disabled: {name!r}."
                raise AutomationError(msg)
            invoke_graph_menu(app, matches[0].ref)
        _ = events.changes.until(
            lambda: True if {w.handle for w in app.windows()} == before else None,
            TRANSITION_SECONDS,
        )
    return Result(
        detail=f"Selected {path!r}; inspect a fresh screenshot to confirm the axis.",
    )


def set_graph_fits(
    app: Capstone,
    handle: int,
    request: SetGraphFitsRequest,
    *,
    progress: GraphProgress | None = None,
) -> GraphFitOutcome:
    """Apply an exact model set and verify it against Capstone's own graph XML."""
    progress = progress or GraphProgress()
    progress.stage = "inspect_graph_for_fitting"
    before = _read_fitting_graph(app, handle, request)
    verify_graph_binding(before, request.expected_data_signature)

    desired = {FIT_TYPES[model] for model in request.models}
    current = set(before.selected_types)
    unknown = current.difference(FIT_ROWS)
    if unknown:
        msg = f"Graph contains unsupported native fit types: {sorted(unknown)}."
        raise AutomationError(msg)
    if desired and not before.series:
        msg = "Assign both axes and select data before applying native fits."
        raise AutomationError(msg)
    if desired and not before.fit_enabled and request.master_point is None:
        msg = "Fitting is disabled; supply the observed fit icon as master_point."
        raise AutomationError(msg)

    state = before
    changed = False
    for native_type in sorted(current.symmetric_difference(desired)):
        progress.begin_input(f"select_fit_{native_type}")
        labels_by_type = {FIT_TYPES[model]: label
                          for model, label in request.menu_labels.items()}
        label = labels_by_type.get(native_type)
        if label is None:
            _ = _toggle_fit(app, handle, request.menu_point, native_type)
        else:
            _ = _toggle_fit(app, handle, request.menu_point, native_type,
                            menu_label=label)
        progress.stage = f"verify_fit_{native_type}"
        expected = set(state.selected_types).symmetric_difference({native_type})
        observed = _read_fitting_graph(app, handle, request)
        if set(observed.selected_types) != expected:
            msg = (
                f"Native fit selection was not confirmed for type {native_type}; "
                f"observed {observed.selected_types}. Inspect before retrying."
            )
            raise AutomationError(msg)
        if [(s.renderer_id, s.inputs) for s in observed.series] != [
            (s.renderer_id, s.inputs) for s in before.series
        ]:
            msg = "Graph data changed during fitting; inspect before retrying."
            raise AutomationError(msg)
        state = observed
        changed = True
        progress.confirmed(f"fit_{native_type}_verified")

    if desired and not state.fit_enabled:
        progress.begin_input("enable_fitting")
        state = _enable_fitting(app, handle, request.master_point, request)
        changed = True

    if set(state.selected_types) != desired or (desired and not state.fit_enabled):
        msg = "Requested native fit configuration was not confirmed."
        raise AutomationError(msg)

    progress.confirmed("fit_configuration_verified")
    successful = not desired or (
        bool(state.series)
        and all(
            any(
                fit.native_type == model and fit.error_status in FIT_SUCCESS_STATUSES
                for fit in series.fits
            )
            for series in state.series
            for model in desired
        )
    )
    return GraphFitOutcome(
        changed=changed,
        requested_models=request.models,
        fits_successful=successful,
        before=before,
        after=state,
    )


def analyze_graph(
    app: Capstone,
    handle: int,
    request: AnalyzeGraphRequest,
    *,
    progress: GraphProgress | None = None,
) -> GraphFitOutcome:
    """Assign requested native axes, then set and read verified native fits."""
    progress = progress or GraphProgress()
    fitting = request.fitting
    if request.x is not None or request.y is not None:
        before = _read_fitting_graph(app, handle, fitting)
        verify_graph_binding(before, fitting.expected_data_signature)

    for name, axis in (("x", request.x), ("y", request.y)):
        if axis is not None:
            progress.begin_input(f"select_{name}_axis")
            _ = select_graph_measurement(
                app,
                handle,
                axis.point,
                axis.menu_path,
                allow_foreground=request.fitting.allow_foreground,
            )
            progress.confirmed(f"{name}_menu_selection_delivered")

    if request.x is not None or request.y is not None:
        current = _read_fitting_graph(app, handle, fitting)
        fitting = fitting.model_copy(
            update={"expected_data_signature": current.data_signature},
        )
    return set_graph_fits(app, handle, fitting, progress=progress)


# ---------------------------------------------------------------------------
# 3. GraphManager Class & manage_graph Seam
# ---------------------------------------------------------------------------


class GraphManager:
    """Consolidated engine for all Capstone graph interactions and analysis."""

    def __init__(self, app: Capstone) -> None:
        """Initialize GraphManager with Capstone desktop app instance."""
        self.app = app

    def create(self, request: CreateGraphRequest) -> CreateGraphResult:
        """Insert a graph onto active page."""
        return create_graph(self.app, request)

    def read(self, request: ReadGraphRequest) -> ReadGraphResult:
        """Read graph state via native clipboard."""
        state = read_graph(
            self.app,
            request.handle,
            allow_foreground=request.allow_foreground,
            display_menu_label=request.display_menu_label,
            copy_display_label=request.copy_display_label,
        )
        return ReadGraphResult(state=state, verified=True)

    def fit(self, request: FitGraphRequest) -> FitGraphResult:
        """Auto-scale axes using Scale to Fit."""
        return fit_graph(self.app, request)

    def select_measurement(
        self,
        request: SelectMeasurementRequest,
    ) -> SelectMeasurementResult:
        """Select an axis measurement via popup menu."""
        res = select_graph_measurement(
            self.app,
            request.handle,
            request.point,
            request.path,
            allow_foreground=request.allow_foreground,
        )
        return SelectMeasurementResult(detail=res.detail, verified=False)

    def toolbox_delta(self, request: GraphDeltaRequest) -> GraphDeltaResult:
        """Toggle delta tool and read coordinate offsets."""
        return graph_delta(self.app, request)

    def toolbox_area(self, request: MeasureGraphAreaRequest) -> MeasureGraphAreaResult:
        """Toggle area tool and read curve integration."""
        return measure_graph_area(self.app, request)

    def toolbox_statistics(
        self,
        request: ToggleGraphStatisticsRequest,
    ) -> ToggleGraphStatisticsResult:
        """Toggle statistics box and extract summary metrics."""
        return toggle_graph_statistics(self.app, request)

    def analyze(self, request: AnalyzeGraphRequest) -> AnalyzeGraphResult:
        """Assign axes, fit curves, and compile summary report."""
        outcome = analyze_graph(self.app, request.handle, request)
        report = summarize_graph(outcome.after) if outcome.after else None
        return AnalyzeGraphResult(outcome=outcome, report=report)

    def _manage_create(self, request: GraphRequest) -> GraphResult:
        if request.create is None:
            msg = "create request must be provided for CREATE action."
            raise AutomationError(msg)
        return GraphResult(
            action=request.action,
            create=self.create(request.create),
        )

    def _manage_read(self, request: GraphRequest) -> GraphResult:
        if request.read is None:
            msg = "read request must be provided for READ action."
            raise AutomationError(msg)
        return GraphResult(action=request.action, read=self.read(request.read))

    def _manage_fit(self, request: GraphRequest) -> GraphResult:
        if request.fit is None:
            msg = "fit request must be provided for FIT action."
            raise AutomationError(msg)
        return GraphResult(action=request.action, fit=self.fit(request.fit))

    def _manage_select_measurement(self, request: GraphRequest) -> GraphResult:
        if request.select_measurement is None:
            msg = (
                "select_measurement request must be provided for "
                "SELECT_MEASUREMENT action."
            )
            raise AutomationError(msg)
        return GraphResult(
            action=request.action,
            select_measurement=self.select_measurement(request.select_measurement),
        )

    def _manage_delta(self, request: GraphRequest) -> GraphResult:
        if request.toolbox_delta is None:
            msg = "toolbox_delta request must be provided for TOOLBOX_DELTA action."
            raise AutomationError(msg)
        return GraphResult(
            action=request.action,
            toolbox_delta=self.toolbox_delta(request.toolbox_delta),
        )

    def _manage_area(self, request: GraphRequest) -> GraphResult:
        if request.toolbox_area is None:
            msg = "toolbox_area request must be provided for TOOLBOX_AREA action."
            raise AutomationError(msg)
        return GraphResult(
            action=request.action,
            toolbox_area=self.toolbox_area(request.toolbox_area),
        )

    def _manage_statistics(self, request: GraphRequest) -> GraphResult:
        if request.toolbox_statistics is None:
            msg = (
                "toolbox_statistics request must be provided for "
                "TOOLBOX_STATISTICS action."
            )
            raise AutomationError(msg)
        return GraphResult(
            action=request.action,
            toolbox_statistics=self.toolbox_statistics(
                request.toolbox_statistics,
            ),
        )

    def _manage_analyze(self, request: GraphRequest) -> GraphResult:
        if request.analyze is None:
            msg = "analyze request must be provided for ANALYZE action."
            raise AutomationError(msg)
        return GraphResult(
            action=request.action,
            analyze=self.analyze(request.analyze),
        )

    def manage(self, request: GraphRequest) -> GraphResult:
        """Unified dispatch method for all graph actions."""
        dispatchers: dict[GraphAction, Callable[[GraphRequest], GraphResult]] = {
            GraphAction.CREATE: self._manage_create,
            GraphAction.READ: self._manage_read,
            GraphAction.FIT: self._manage_fit,
            GraphAction.SELECT_MEASUREMENT: self._manage_select_measurement,
            GraphAction.TOOLBOX_DELTA: self._manage_delta,
            GraphAction.TOOLBOX_AREA: self._manage_area,
            GraphAction.TOOLBOX_STATISTICS: self._manage_statistics,
            GraphAction.ANALYZE: self._manage_analyze,
        }
        handler = dispatchers.get(request.action)
        if handler is None:
            msg = f"Unsupported GraphAction: {request.action}"
            raise AutomationError(msg)
        return handler(request)


def manage_graph(app: Capstone, request: GraphRequest) -> GraphResult:
    """Functional convenience wrapper for the unified graph management seam."""
    return GraphManager(app).manage(request)


__all__ = [
    "MENU_RELEASE_ATTEMPTS",
    "GraphManager",
    "_toggle_fit",
    "analyze_graph",
    "close_menus",
    "create_graph",
    "fit_graph",
    "invoke_graph_menu",
    "manage_graph",
    "menu_item_disabled",
    "read_graph",
    "ready_graph_menu",
    "release_menu_bar",
    "select_graph_measurement",
    "set_graph_fits",
]

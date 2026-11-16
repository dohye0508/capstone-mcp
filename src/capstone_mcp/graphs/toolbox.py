# Copyright 2026 Capstone MCP contributors.
"""Graph toolbar analysis tools: statistics (Σ), area under curve (∫ydx), delta (Δ)."""

from __future__ import annotations

import contextlib
import re
from _ctypes import COMError
from typing import TYPE_CHECKING, Final

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.displays import click_control
from capstone_mcp.graphs.models import (
    GraphDeltaRequest,
    GraphDeltaResult,
    GraphStatistics,
    MeasureGraphAreaRequest,
    MeasureGraphAreaResult,
    ToggleGraphStatisticsRequest,
    ToggleGraphStatisticsResult,
)

if TYPE_CHECKING:
    from capstone_mcp.models import Control

MIN_COORDINATE_PAIRS: Final = 2

STATS_KEYWORDS: Final = (
    "statistics",
    "stats",
    "sigma",
    "\u03c3",
    "\u03a3",
)
AREA_KEYWORDS: Final = (
    "area",
    "integral",
    "\u222b",
    "\u222bydx",
)
DELTA_KEYWORDS: Final = (
    "delta",
    "coordinate",
    "coord",
    "crosshair",
    "\u0394",
)

MEAN_RE: Final = re.compile(
    r"(?:\bmean|\bavg|\baverage)\s*[:=]\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
    re.IGNORECASE,
)
STDDEV_RE: Final = re.compile(
    r"(?:\bstd\.?\s*dev(?:\.|iation)?|\bstandard\s*deviation|\u03c3)\s*[:=]\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
    re.IGNORECASE,
)
MIN_RE: Final = re.compile(
    r"(?:\bminimum|\bmin)\s*[:=]\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
    re.IGNORECASE,
)
MAX_RE: Final = re.compile(
    r"(?:\bmaximum|\bmax)\s*[:=]\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
    re.IGNORECASE,
)
COUNT_RE: Final = re.compile(
    r"(?:\bcount|\bsamples|\bn)\s*[:=]\s*(\d+)",
    re.IGNORECASE,
)
AREA_RE: Final = re.compile(
    r"(?:area|∫\s*y\s*d\s*x|integral)\s*[:=]?\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([A-Za-z°%µΩ/·^-]+)?",
    re.IGNORECASE,
)
DX_RE: Final = re.compile(
    r"(?:Δ\s*x|dx|delta\s*x)\s*[:=]?\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([A-Za-z°%µΩ/·^-]+)?",
    re.IGNORECASE,
)
DY_RE: Final = re.compile(
    r"(?:Δ\s*y|dy|delta\s*y)\s*[:=]?\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([A-Za-z°%µΩ/·^-]+)?",
    re.IGNORECASE,
)
COORD_PAIR_RE: Final = re.compile(
    r"\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*\)",
)


def _find_graph_control(
    controls: list[Control],
    graph_name: str | None = None,
) -> Control:
    """Find target graph display widget."""
    target = graph_name.strip().casefold() if graph_name else "graph"
    matches = [
        ctrl
        for ctrl in controls
        if ctrl.visible
        and ctrl.control_type in ("Custom", "Pane", "Group")
        and (
            (
                target == ctrl.name.strip().casefold()
                if graph_name
                else target in ctrl.name.casefold()
            )
            or (
                target == ctrl.automation_id.casefold()
                if graph_name
                else target in ctrl.automation_id.casefold()
            )
        )
    ]
    if not matches:
        msg = "No Graph display found in the active window."
        raise AutomationError(msg)
    if len(matches) != 1:
        msg = "Graph selection is ambiguous; specify a unique graph_name."
        raise AutomationError(msg)
    return matches[0]


def _find_toolbar_button(
    controls: list[Control],
    graph_ctrl: Control,
    keywords: tuple[str, ...],
    *,
    label: str | None = None,
) -> Control:
    """Locate a specific tool button on the graph toolbar."""
    by_ref = {control.ref: control for control in controls}
    matches: list[Control] = []
    for c in controls:
        if not c.visible or not c.enabled:
            continue
        # Screen rectangles can overlap or touch across displays. Only the
        # snapshot's explicit ancestry establishes which graph owns a button.
        parent = c.parent
        visited: set[str] = set()
        while parent is not None and parent != graph_ctrl.ref:
            if parent in visited or parent not in by_ref:
                parent = None
                break
            visited.add(parent)
            parent = by_ref[parent].parent
        if parent != graph_ctrl.ref:
            continue

        if c.control_type not in ("Button", "CheckBox", "MenuItem", "Custom"):
            continue

        name_lower = c.name.strip().lower()
        aid_lower = c.automation_id.lower()

        if (
            c.name == label
            if label is not None
            else any(
                kw.lower() in name_lower or kw.lower() in aid_lower for kw in keywords
            )
        ):
            matches.append(c)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        msg = f"Graph toolbar button matching {keywords} is ambiguous."
        raise AutomationError(msg)

    msg = f"Graph toolbar button matching {keywords} not found."
    raise AutomationError(msg)


def _observed_toggle(app: Capstone, button: Control, *, visible: bool) -> bool | None:
    with contextlib.suppress(AutomationError, COMError, AttributeError, RuntimeError):
        state = app.control(button.ref).iface_toggle.CurrentToggleState
        if isinstance(state, int) and state in (0, 1):
            return state == 1
    return True if visible else None


def _set_tool_state(
    app: Capstone,
    handle: int,
    button: Control,
    *,
    enable: bool | None,
    visible: bool,
) -> None:
    if enable is not None:
        state = _observed_toggle(app, button, visible=visible)
        if state is None:
            msg = "Cannot verify the graph tool's toggle state; no input was sent."
            raise AutomationError(msg)
        if state == enable:
            return
    click_control(app, handle, button, allow_foreground=True)


def _extract_graph_controls(
    controls: list[Control],
    graph_ctrl: Control,
) -> list[Control]:
    """Return visible controls inside or directly overlaying the graph area."""
    gb = graph_ctrl.bounds
    return [
        c
        for c in controls
        if c.visible
        and c.ref != graph_ctrl.ref
        and c.bounds.top >= gb.top
        and c.bounds.bottom <= gb.bottom
        and c.bounds.left >= gb.left
        and c.bounds.right <= gb.right
    ]


def _parse_statistics(graph_controls: list[Control]) -> GraphStatistics:
    """Parse statistical metrics from text labels overlaying the graph."""
    mean_val: float | None = None
    std_dev_val: float | None = None
    min_val: float | None = None
    max_val: float | None = None
    count_val: int | None = None
    raw: dict[str, str] = {}

    for c in graph_controls:
        text = c.name.strip()
        if not text:
            continue

        m_mean = MEAN_RE.search(text)
        if m_mean and mean_val is None:
            with contextlib.suppress(ValueError):
                mean_val = float(m_mean.group(1))
                raw["mean"] = m_mean.group(1)

        m_std = STDDEV_RE.search(text)
        if m_std and std_dev_val is None:
            with contextlib.suppress(ValueError):
                std_dev_val = float(m_std.group(1))
                raw["std_dev"] = m_std.group(1)

        m_min = MIN_RE.search(text)
        if m_min and min_val is None:
            with contextlib.suppress(ValueError):
                min_val = float(m_min.group(1))
                raw["min"] = m_min.group(1)

        m_max = MAX_RE.search(text)
        if m_max and max_val is None:
            with contextlib.suppress(ValueError):
                max_val = float(m_max.group(1))
                raw["max"] = m_max.group(1)

        m_cnt = COUNT_RE.search(text)
        if m_cnt and count_val is None:
            with contextlib.suppress(ValueError):
                count_val = int(m_cnt.group(1))
                raw["count"] = m_cnt.group(1)

    return GraphStatistics(
        mean=mean_val,
        std_dev=std_dev_val,
        min=min_val,
        max=max_val,
        count=count_val,
        raw_values=raw,
    )


def toggle_graph_statistics(
    app: Capstone,
    request: ToggleGraphStatisticsRequest | None = None,
) -> ToggleGraphStatisticsResult:
    """Toggle graph statistics box (Σ) and extract summary metrics."""
    if request is None:
        request = ToggleGraphStatisticsRequest()

    if not request.allow_foreground:
        msg = "Graph statistics toggle requires allow_foreground=true."
        raise AutomationError(msg)

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    graph_ctrl = _find_graph_control(snapshot.controls, request.graph_name)
    stats_btn = _find_toolbar_button(
        snapshot.controls, graph_ctrl, STATS_KEYWORDS, label=request.tool_label,
    )

    previous_stats = _parse_statistics(
        _extract_graph_controls(snapshot.controls, graph_ctrl),
    )
    _set_tool_state(
        app,
        request.handle,
        stats_btn,
        enable=request.enable,
        visible=bool(previous_stats.raw_values),
    )

    # Inspect graph overlay for statistics box
    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    graph_ctrl = _find_graph_control(snapshot.controls, request.graph_name)
    overlay_ctrls = _extract_graph_controls(snapshot.controls, graph_ctrl)

    stats = _parse_statistics(overlay_ctrls)
    has_stats = any(
        v is not None
        for v in (stats.mean, stats.std_dev, stats.min, stats.max, stats.count)
    )

    g_name = request.graph_name or graph_ctrl.name or "Graph"
    observed_button = _find_toolbar_button(
        snapshot.controls,
        graph_ctrl,
        STATS_KEYWORDS,
        label=request.tool_label,
    )
    observed = _observed_toggle(app, observed_button, visible=has_stats)
    detail = (
        f"Statistics on '{g_name}': mean={stats.mean}, std_dev={stats.std_dev}, "
        f"min={stats.min}, max={stats.max}, count={stats.count}."
    )

    return ToggleGraphStatisticsResult(
        visible=has_stats,
        statistics=stats if has_stats else None,
        graph_name=g_name,
        verified=observed is not None
        and (request.enable is None or observed == request.enable),
        detail=detail,
    )


def _parse_area(
    graph_controls: list[Control],
) -> tuple[float | None, str | None, str | None]:
    """Parse area integral value and unit from graph overlay labels."""
    for c in graph_controls:
        text = c.name.strip()
        if not text:
            continue
        m = AREA_RE.search(text)
        if m:
            val = float(m.group(1))
            unit = m.group(2).strip() if m.group(2) else None
            return val, unit, text
    return None, None, None


def measure_graph_area(
    app: Capstone,
    request: MeasureGraphAreaRequest | None = None,
) -> MeasureGraphAreaResult:
    """Toggle curve area integration tool (∫ydx) and extract integral value."""
    if request is None:
        request = MeasureGraphAreaRequest()

    if not request.allow_foreground:
        msg = "Graph area measurement requires allow_foreground=true."
        raise AutomationError(msg)

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    graph_ctrl = _find_graph_control(snapshot.controls, request.graph_name)
    area_btn = _find_toolbar_button(
        snapshot.controls, graph_ctrl, AREA_KEYWORDS, label=request.tool_label,
    )

    previous_area, _, _ = _parse_area(
        _extract_graph_controls(snapshot.controls, graph_ctrl),
    )
    _set_tool_state(
        app,
        request.handle,
        area_btn,
        enable=request.enable,
        visible=previous_area is not None,
    )

    # Read area from graph overlay
    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    graph_ctrl = _find_graph_control(snapshot.controls, request.graph_name)
    overlay_ctrls = _extract_graph_controls(snapshot.controls, graph_ctrl)

    area_val, unit, raw_text = _parse_area(overlay_ctrls)

    g_name = request.graph_name or graph_ctrl.name or "Graph"
    observed_button = _find_toolbar_button(
        snapshot.controls, graph_ctrl, AREA_KEYWORDS, label=request.tool_label,
    )
    observed = _observed_toggle(app, observed_button, visible=area_val is not None)
    unit_str = f" {unit}" if unit else ""
    detail = (
        f"Curve area on '{g_name}': {area_val}{unit_str}."
        if area_val is not None
        else f"Area tool toggled on '{g_name}'."
    )

    return MeasureGraphAreaResult(
        visible=area_val is not None,
        area=area_val,
        unit=unit,
        raw_text=raw_text,
        graph_name=g_name,
        verified=observed is not None
        and (request.enable is None or observed == request.enable),
        detail=detail,
    )


def _parse_delta(
    graph_controls: list[Control],
) -> tuple[
    float | None,
    float | None,
    float | None,
    float | None,
    float | None,
    float | None,
    str | None,
    str | None,
    str | None,
]:
    """Parse dx, dy, and endpoints from delta crosshair labels."""
    dx: float | None = None
    dy: float | None = None
    x1: float | None = None
    y1: float | None = None
    x2: float | None = None
    y2: float | None = None
    unit_x: str | None = None
    unit_y: str | None = None
    raw_texts: list[str] = []
    all_coordinates: list[tuple[str, str]] = []

    for c in graph_controls:
        text = c.name.strip()
        if not text:
            continue

        m_dx = DX_RE.search(text)
        if m_dx and dx is None:
            with contextlib.suppress(ValueError):
                dx = float(m_dx.group(1))
                if m_dx.group(2):
                    unit_x = m_dx.group(2).strip()
            raw_texts.append(text)

        m_dy = DY_RE.search(text)
        if m_dy and dy is None:
            with contextlib.suppress(ValueError):
                dy = float(m_dy.group(1))
                if m_dy.group(2):
                    unit_y = m_dy.group(2).strip()
            raw_texts.append(text)

        coord_pairs = COORD_PAIR_RE.findall(text)
        if coord_pairs:
            all_coordinates.extend(coord_pairs)
            raw_texts.append(text)

    if len(all_coordinates) == MIN_COORDINATE_PAIRS:
        x1, y1 = map(float, all_coordinates[0])
        x2, y2 = map(float, all_coordinates[1])
        dx = x2 - x1 if dx is None else dx
        dy = y2 - y1 if dy is None else dy

    raw_combined = " | ".join(raw_texts) if raw_texts else None
    return dx, dy, x1, y1, x2, y2, unit_x, unit_y, raw_combined


def graph_delta(
    app: Capstone,
    request: GraphDeltaRequest | None = None,
) -> GraphDeltaResult:
    """Activate delta tool (Δ) and extract delta coordinates / differences."""
    if request is None:
        request = GraphDeltaRequest()

    if not request.allow_foreground:
        msg = "Graph delta measurement requires allow_foreground=true."
        raise AutomationError(msg)

    if any(
        point is not None for point in (request.point, request.point1, request.point2)
    ):
        msg = (
            "Delta endpoint positioning is unverified; "
            "position crosshairs in Capstone first."
        )
        raise AutomationError(msg)

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    graph_ctrl = _find_graph_control(snapshot.controls, request.graph_name)
    delta_btn = _find_toolbar_button(
        snapshot.controls, graph_ctrl, DELTA_KEYWORDS, label=request.tool_label,
    )

    # Click delta button to activate tool using display harness primitive
    click_control(app, request.handle, delta_btn, allow_foreground=True)

    # Read delta readout
    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    graph_ctrl = _find_graph_control(snapshot.controls, request.graph_name)
    overlay_ctrls = _extract_graph_controls(snapshot.controls, graph_ctrl)

    dx, dy, x1, y1, x2, y2, unit_x, unit_y, raw_text = _parse_delta(overlay_ctrls)

    g_name = request.graph_name or graph_ctrl.name or "Graph"
    detail = (
        f"Delta on '{g_name}': Δx={dx} {unit_x or ''}, Δy={dy} {unit_y or ''}."
        if (dx is not None or dy is not None)
        else f"Delta tool activated on '{g_name}'."
    ).strip()

    return GraphDeltaResult(
        active=dx is not None or dy is not None,
        visible=dx is not None or dy is not None,
        delta_x=dx,
        delta_y=dy,
        dx=dx,
        dy=dy,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        unit_x=unit_x,
        unit_y=unit_y,
        raw_text=raw_text,
        graph_name=g_name,
        verified=dx is not None or dy is not None,
        detail=detail,
    )

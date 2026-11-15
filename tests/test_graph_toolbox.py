# Copyright 2026 Capstone MCP contributors.
"""Tests for graph toolbox: statistics, area under curve, delta measurements."""

from unittest.mock import MagicMock

import pytest

from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.graphs import (
    GraphDeltaRequest,
    GraphDeltaResult,
    MeasureGraphAreaRequest,
    MeasureGraphAreaResult,
    ToggleGraphStatisticsRequest,
    ToggleGraphStatisticsResult,
    graph_delta,
    measure_graph_area,
    toggle_graph_statistics,
)
from capstone_mcp.models import Bounds, Control, Point, Snapshot, Window


def _mock_window(handle: int = 100) -> Window:
    return Window(
        handle=handle,
        title="Capstone",
        process_id=1,
        bounds=Bounds(left=0, top=0, right=1200, bottom=900),
    )


def test_toggle_graph_statistics_refuses_disabled_foreground() -> None:
    app = Capstone()
    req = ToggleGraphStatisticsRequest(handle=100, allow_foreground=False)
    with pytest.raises(AutomationError, match="allow_foreground=true"):
        toggle_graph_statistics(app, req)


def test_toggle_graph_statistics_raises_when_no_graph() -> None:
    app = Capstone()
    mock_win = _mock_window()
    app.snapshot = MagicMock(
        return_value=Snapshot(
            window=mock_win,
            controls=[],
            truncated=False,
        ),
    )
    with pytest.raises(AutomationError, match="No Graph display found"):
        toggle_graph_statistics(app, ToggleGraphStatisticsRequest(handle=100))


def test_toggle_graph_statistics_success() -> None:
    app = Capstone()
    mock_win = _mock_window()

    graph_ctrl = Control(
        ref="ref:graph",
        parent=None,
        name="Graph 1",
        control_type="Custom",
        automation_id="GraphDisplay",
        enabled=True,
        visible=True,
        bounds=Bounds(left=100, top=100, right=800, bottom=600),
    )
    stats_btn = Control(
        ref="ref:stats_btn",
        parent="ref:graph",
        name="Statistics (Σ)",
        control_type="Button",
        automation_id="Graph.StatisticsButton",
        enabled=True,
        visible=True,
        bounds=Bounds(left=110, top=105, right=140, bottom=135),
    )

    stat_mean = Control(
        ref="ref:mean",
        parent="ref:graph",
        name="Mean: 5.42",
        control_type="Text",
        automation_id="StatMean",
        enabled=True,
        visible=True,
        bounds=Bounds(left=600, top=150, right=750, bottom=170),
    )
    stat_std = Control(
        ref="ref:std",
        parent="ref:graph",
        name="Std. Dev.: 0.83",
        control_type="Text",
        automation_id="StatStdDev",
        enabled=True,
        visible=True,
        bounds=Bounds(left=600, top=175, right=750, bottom=195),
    )
    stat_min = Control(
        ref="ref:min",
        parent="ref:graph",
        name="Min: 3.10",
        control_type="Text",
        automation_id="StatMin",
        enabled=True,
        visible=True,
        bounds=Bounds(left=600, top=200, right=750, bottom=220),
    )
    stat_max = Control(
        ref="ref:max",
        parent="ref:graph",
        name="Max: 7.95",
        control_type="Text",
        automation_id="StatMax",
        enabled=True,
        visible=True,
        bounds=Bounds(left=600, top=225, right=750, bottom=245),
    )
    stat_cnt = Control(
        ref="ref:cnt",
        parent="ref:graph",
        name="Count: 250",
        control_type="Text",
        automation_id="StatCount",
        enabled=True,
        visible=True,
        bounds=Bounds(left=600, top=250, right=750, bottom=270),
    )

    call_count = 0

    def mock_snapshot(*_args: object, **_kwargs: object) -> Snapshot:
        nonlocal call_count
        call_count += 1
        ctrls = [graph_ctrl, stats_btn]
        if call_count > 1:
            ctrls.extend([stat_mean, stat_std, stat_min, stat_max, stat_cnt])
        return Snapshot(window=mock_win, controls=ctrls, truncated=False)

    app.snapshot = mock_snapshot
    app.click = MagicMock()

    res = toggle_graph_statistics(
        app,
        ToggleGraphStatisticsRequest(handle=100, graph_name="Graph 1"),
    )

    assert isinstance(res, ToggleGraphStatisticsResult)
    assert res.visible is True
    assert res.verified is True
    assert res.statistics is not None
    assert res.statistics.mean == 5.42
    assert res.statistics.std_dev == 0.83
    assert res.statistics.min == 3.10
    assert res.statistics.max == 7.95
    assert res.statistics.count == 250
    app.click.assert_called_once_with(100, "ref:stats_btn", allow_foreground=True)


def test_measure_graph_area_success() -> None:
    app = Capstone()
    mock_win = _mock_window()

    graph_ctrl = Control(
        ref="ref:graph",
        parent=None,
        name="Graph",
        control_type="Custom",
        automation_id="GraphDisplay",
        enabled=True,
        visible=True,
        bounds=Bounds(left=100, top=100, right=800, bottom=600),
    )
    area_btn = Control(
        ref="ref:area_btn",
        parent="ref:graph",
        name="Area under Curve (∫ydx)",
        control_type="Button",
        automation_id="Graph.AreaToolButton",
        enabled=True,
        visible=True,
        bounds=Bounds(left=150, top=105, right=180, bottom=135),
    )
    area_label = Control(
        ref="ref:area_label",
        parent="ref:graph",
        name="Area = 42.50 N·s",
        control_type="Text",
        automation_id="Graph.AreaReadout",
        enabled=True,
        visible=True,
        bounds=Bounds(left=300, top=300, right=450, bottom=330),
    )

    call_count = 0

    def mock_snapshot(*_args: object, **_kwargs: object) -> Snapshot:
        nonlocal call_count
        call_count += 1
        ctrls = [graph_ctrl, area_btn]
        if call_count > 1:
            ctrls.append(area_label)
        return Snapshot(window=mock_win, controls=ctrls, truncated=False)

    app.snapshot = mock_snapshot
    app.click = MagicMock()

    res = measure_graph_area(app, MeasureGraphAreaRequest(handle=100))

    assert isinstance(res, MeasureGraphAreaResult)
    assert res.visible is True
    assert res.area == 42.50
    assert res.unit == "N·s"
    assert res.verified is True
    app.click.assert_called_once_with(100, "ref:area_btn", allow_foreground=True)


def test_graph_delta_reads_observed_values() -> None:
    app = Capstone()
    mock_win = _mock_window()

    graph_ctrl = Control(
        ref="ref:graph",
        parent=None,
        name="Graph",
        control_type="Custom",
        automation_id="GraphDisplay",
        enabled=True,
        visible=True,
        bounds=Bounds(left=100, top=100, right=800, bottom=600),
    )
    delta_btn = Control(
        ref="ref:delta_btn",
        parent="ref:graph",
        name="Coordinates / Delta Tool (Δ)",
        control_type="Button",
        automation_id="Graph.DeltaToolButton",
        enabled=True,
        visible=True,
        bounds=Bounds(left=190, top=105, right=220, bottom=135),
    )
    delta_label_dx = Control(
        ref="ref:delta_dx",
        parent="ref:graph",
        name="Δx = 1.20 s",
        control_type="Text",
        automation_id="DeltaXLabel",
        enabled=True,
        visible=True,
        bounds=Bounds(left=300, top=200, right=400, bottom=220),
    )
    delta_label_dy = Control(
        ref="ref:delta_dy",
        parent="ref:graph",
        name="Δy = 3.60 m/s",
        control_type="Text",
        automation_id="DeltaYLabel",
        enabled=True,
        visible=True,
        bounds=Bounds(left=300, top=225, right=400, bottom=245),
    )

    call_count = 0

    def mock_snapshot(*_args: object, **_kwargs: object) -> Snapshot:
        nonlocal call_count
        call_count += 1
        ctrls = [graph_ctrl, delta_btn]
        if call_count > 1:
            ctrls.extend([delta_label_dx, delta_label_dy])
        return Snapshot(window=mock_win, controls=ctrls, truncated=False)

    app.snapshot = mock_snapshot
    app.click = MagicMock()
    app.click_point = MagicMock()

    res = graph_delta(
        app,
        GraphDeltaRequest(
            handle=100,
        ),
    )

    assert isinstance(res, GraphDeltaResult)
    assert res.active is True
    assert res.delta_x == 1.20
    assert res.unit_x == "s"
    assert res.delta_y == 3.60
    assert res.unit_y == "m/s"
    assert res.verified is True
    app.click.assert_called_once_with(100, "ref:delta_btn", allow_foreground=True)
    app.click_point.assert_not_called()


def test_graph_delta_rejects_unverified_endpoint_positioning_before_input() -> None:
    app = MagicMock(spec=Capstone)
    with pytest.raises(AutomationError, match="positioning is unverified"):
        _ = graph_delta(app, GraphDeltaRequest(point1=Point(x=20, y=30)))
    app.snapshot.assert_not_called()
    app.click.assert_not_called()


@pytest.mark.parametrize("enable", [True, False])
@pytest.mark.parametrize("tool", ["statistics", "area"])
def test_explicit_tool_state_is_idempotent(tool: str, *, enable: bool) -> None:
    app = MagicMock(spec=Capstone)
    graph = Control(ref="graph", parent=None, name="Graph", control_type="Custom", automation_id="GraphDisplay", enabled=True, visible=True, bounds=Bounds(left=0, top=0, right=500, bottom=500))
    button = Control(ref="button", parent="graph", name=tool, control_type="CheckBox", automation_id=tool, enabled=True, visible=True, bounds=Bounds(left=10, top=10, right=30, bottom=30))
    app.snapshot.return_value = Snapshot(window=_mock_window(), controls=[graph, button], truncated=False)
    app.control.return_value.iface_toggle.CurrentToggleState = int(enable)
    result = (
        toggle_graph_statistics(app, ToggleGraphStatisticsRequest(enable=enable))
        if tool == "statistics" else measure_graph_area(app, MeasureGraphAreaRequest(enable=enable))
    )
    app.click.assert_not_called()
    assert result.verified


def test_explicit_unknown_tool_state_never_sends_input() -> None:
    app = MagicMock(spec=Capstone)
    graph = Control(ref="graph", parent=None, name="Graph", control_type="Custom", automation_id="GraphDisplay", enabled=True, visible=True, bounds=Bounds(left=0, top=0, right=500, bottom=500))
    button = Control(ref="button", parent="graph", name="Statistics", control_type="Button", automation_id="Stats", enabled=True, visible=True, bounds=Bounds(left=10, top=10, right=30, bottom=30))
    app.snapshot.return_value = Snapshot(window=_mock_window(), controls=[graph, button], truncated=False)
    app.control.side_effect = AutomationError("no toggle pattern")
    with pytest.raises(AutomationError, match="toggle state"):
        _ = toggle_graph_statistics(app, ToggleGraphStatisticsRequest(enable=True))
    app.click.assert_not_called()

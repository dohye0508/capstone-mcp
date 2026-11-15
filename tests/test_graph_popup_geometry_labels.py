# Copyright 2026 Capstone MCP contributors.
"""Offline popup geometry and explicit observed-label contracts."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from capstone_mcp.desktop import AutomationError
from capstone_mcp.graphs import inspection, manager
from capstone_mcp.graphs.models import (
    CreateGraphRequest,
    FitModel,
    GraphAction,
    GraphFitRequest,
    GraphRequest,
    GraphSeries,
    GraphState,
    ReadGraphRequest,
    ToggleGraphStatisticsRequest,
)
from capstone_mcp.graphs.toolbox import _find_toolbar_button, toggle_graph_statistics
from capstone_mcp.models import Bounds, Control, Point, Snapshot, Window


def _snapshot(handle: int = 2, *, label: str = "", top: int = 400) -> Snapshot:
    rect = Bounds(left=300, top=top, right=550, bottom=top + 480)
    window = Window(handle=handle, title="PASCO Capstone", process_id=7, bounds=rect)
    item = Control(ref=f"item-{handle}", parent=None, name=label,
                   control_type="MenuItem", automation_id="", enabled=True,
                   visible=True, bounds=rect)
    return Snapshot(window=window, controls=[item], truncated=False)


def test_owned_popup_outside_main_window_is_allowed_on_monitor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = MagicMock()
    popup = _snapshot(top=400)
    app.window.return_value.rectangle.return_value = popup.window.bounds
    api = MagicMock()
    api.EnumDisplayMonitors.return_value = [(1, 0, (0, 0, 1920, 1080))]
    monkeypatch.setattr(manager, "win32api", api)
    assert manager._fit_popup_bounds(app, popup) == popup.window.bounds
    app.window.assert_called_once_with(2)


@pytest.mark.parametrize("top", [-10, 700])
def test_offscreen_popup_is_not_allowed(
    monkeypatch: pytest.MonkeyPatch, top: int,
) -> None:
    app = MagicMock()
    popup = _snapshot(top=top)
    app.window.return_value.rectangle.return_value = popup.window.bounds
    api = MagicMock()
    api.EnumDisplayMonitors.return_value = [(1, 0, (0, 0, 1920, 1080))]
    monkeypatch.setattr(manager, "win32api", api)
    with pytest.raises(AutomationError, match="monitor"):
        manager._fit_popup_bounds(app, popup)


def test_popup_on_negative_origin_monitor_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    app = MagicMock()
    popup = _snapshot(top=-900)
    app.window.return_value.rectangle.return_value = popup.window.bounds
    api = MagicMock()
    api.EnumDisplayMonitors.return_value = [(1, 0, (0, -1080, 1920, 0))]
    monkeypatch.setattr(manager, "win32api", api)
    assert manager._fit_popup_bounds(app, popup) == popup.window.bounds


def test_moved_popup_is_rejected_before_monitor_query(monkeypatch: pytest.MonkeyPatch) -> None:
    app, api = MagicMock(), MagicMock()
    popup = _snapshot()
    app.window.return_value.rectangle.return_value = _snapshot(top=500).window.bounds
    monkeypatch.setattr(manager, "win32api", api)
    with pytest.raises(AutomationError, match="moved"):
        manager._fit_popup_bounds(app, popup)
    api.EnumDisplayMonitors.assert_not_called()


def test_named_fit_menu_supports_multiple_accessible_items() -> None:
    app = MagicMock()
    popup = _snapshot(label="선형 피팅")
    other = popup.controls[0].model_copy(update={"ref": "other", "name": "이차 피팅"})
    popup = popup.model_copy(update={"controls": [other, *popup.controls]})
    app.windows.return_value = [popup.window]
    app.snapshot.return_value = popup
    assert manager._fit_menu(app, {1}, "선형 피팅") == popup


def test_named_fit_menu_refuses_duplicate_labels() -> None:
    app = MagicMock()
    popup = _snapshot(label="선형 피팅")
    popup = popup.model_copy(update={"controls": popup.controls * 2})
    app.windows.return_value = [popup.window]
    app.snapshot.return_value = popup
    with pytest.raises(AutomationError, match="multiple menu items"):
        manager._fit_menu(app, {1}, "선형 피팅")


def test_fit_popup_ambiguity_never_selects_first_window() -> None:
    app = MagicMock()
    one, two = _snapshot(), _snapshot(3)
    app.windows.return_value = [one.window, two.window]
    app.snapshot.side_effect = [one, two]
    with pytest.raises(AutomationError, match="Multiple native fit popups"):
        manager._fit_menu(app, {1})


def test_graph_create_uses_exact_observed_nonenglish_palette_label() -> None:
    app = MagicMock()
    item = _snapshot(label="그래프").controls[0].model_copy(update={"control_type": "Button"})
    app.snapshot.return_value = _snapshot().model_copy(update={"controls": [item]})
    request = GraphRequest(action=GraphAction.CREATE,
                           create=CreateGraphRequest(handle=1, palette_label="그래프"))
    manager.manage_graph(app, GraphRequest.model_validate_json(request.model_dump_json()))
    app.click.assert_called_once_with(1, item.ref, allow_foreground=True)


def test_graph_create_refuses_ambiguous_observed_palette_label() -> None:
    app = MagicMock()
    item = _snapshot(label="그래프").controls[0].model_copy(update={"control_type": "Button"})
    app.snapshot.return_value = _snapshot().model_copy(update={"controls": [item, item]})
    with pytest.raises(AutomationError, match="Expected one Graph"):
        manager.create_graph(app, CreateGraphRequest(handle=1, palette_label="그래프"))
    app.click.assert_not_called()


def test_graph_read_routes_observed_labels_through_unified_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = MagicMock(return_value=GraphState(fit_enabled=False, selected_types=[], series=[]))
    monkeypatch.setattr(manager, "read_graph", reader)
    app = MagicMock()
    request = GraphRequest(action=GraphAction.READ, read=ReadGraphRequest(
        handle=1, display_menu_label="화면", copy_display_label="화면 복사",
    ))
    manager.manage_graph(app, GraphRequest.model_validate_json(request.model_dump_json()))
    reader.assert_called_once_with(app, 1, allow_foreground=True,
                                   display_menu_label="화면", copy_display_label="화면 복사")


def test_display_popup_exact_label_and_new_window_are_required() -> None:
    app = MagicMock()
    popup = _snapshot(label="화면 복사")
    app.windows.return_value = [popup.window]
    app.snapshot.return_value = popup
    assert inspection._display_popup(app, 1, "화면 복사", before={1}) == popup
    assert inspection._display_popup(app, 1, "복사", before={1}) is None
    assert inspection._display_popup(app, 1, "화면 복사", before={1, 2}) is None


def test_toolbar_observed_label_uses_owned_exact_match() -> None:
    graph = _snapshot().controls[0].model_copy(update={"ref": "graph", "name": "Graph", "control_type": "Pane"})
    button = graph.model_copy(update={"ref": "button", "parent": "graph", "name": "통계", "control_type": "Button"})
    app = MagicMock()
    app.snapshot.return_value = _snapshot().model_copy(update={"controls": [graph, button]})
    app.control.return_value.iface_toggle.CurrentToggleState = 1
    result = toggle_graph_statistics(app, ToggleGraphStatisticsRequest(handle=1, tool_label="통계", enable=True))
    assert result.verified
    app.click.assert_not_called()
    with pytest.raises(AutomationError, match="not found"):
        _find_toolbar_button([graph, button], graph, ("statistics",), label="통")


def test_fit_menu_label_map_roundtrips_and_rejects_blank_values() -> None:
    request = GraphFitRequest(frame_id="frame", menu_point=Point(x=1, y=1),
                              models=[FitModel.LINEAR], menu_labels={FitModel.LINEAR: "선형 피팅"})
    assert GraphFitRequest.model_validate_json(request.model_dump_json()).menu_labels == request.menu_labels
    with pytest.raises(ValidationError, match="must not be blank"):
        GraphFitRequest(frame_id="frame", menu_point=Point(x=1, y=1), models=[],
                        menu_labels={FitModel.LINEAR: " "})


def test_fit_selection_accepts_visible_popup_beyond_main_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, events, api = MagicMock(), MagicMock(), MagicMock()
    popup = _snapshot(top=400)
    main = MagicMock()
    main.rectangle.return_value = Bounds(left=0, top=0, right=600, bottom=500)
    transient = MagicMock()
    transient.rectangle.return_value = popup.window.bounds
    app.window.side_effect = lambda handle: main if handle == 1 else transient
    app.windows.return_value = [popup.window.model_copy(update={"handle": 1})]
    events.__enter__.return_value = events
    events.changes.until.side_effect = [popup, True]
    api.EnumDisplayMonitors.return_value = [(1, 0, (0, 0, 1920, 1080))]
    click = MagicMock()
    monkeypatch.setattr(manager, "win32api", api)
    monkeypatch.setattr(manager, "WindowEvents", MagicMock(return_value=events))
    monkeypatch.setattr(manager, "invoke_graph_menu", click)
    manager._toggle_fit(app, 1, Point(x=10, y=20), 1)
    click.assert_called_once()
    assert click.call_args.kwargs["screen_point"].y > 400
    app.require_uncovered.assert_called_once()


def test_rejected_popup_cleans_up_without_selecting_fit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, events = MagicMock(), MagicMock()
    main = MagicMock()
    main.rectangle.return_value = Bounds(left=0, top=0, right=600, bottom=500)
    app.window.return_value = main
    events.__enter__.return_value = events
    events.changes.until.return_value = _snapshot()
    cleanup, click = MagicMock(), MagicMock()
    monkeypatch.setattr(manager, "WindowEvents", MagicMock(return_value=events))
    monkeypatch.setattr(manager, "_fit_popup_bounds", MagicMock(side_effect=AutomationError("clipped")))
    monkeypatch.setattr(manager, "close_menus", cleanup)
    monkeypatch.setattr(manager, "invoke_graph_menu", click)
    with pytest.raises(AutomationError, match="clipped"):
        manager._toggle_fit(app, 1, Point(x=10, y=20), 1)
    click.assert_not_called()
    cleanup.assert_called_once_with(app, 1)


def test_named_fit_contract_routes_labels_through_native_readback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = MagicMock()
    initial = GraphState(fit_enabled=True, selected_types=[],
                         series=[GraphSeries(renderer_id="run1", inputs=[], fits=[])])
    after = initial.model_copy(update={"selected_types": [1]})
    reader = MagicMock(side_effect=[initial, after])
    toggle = MagicMock()
    monkeypatch.setattr(manager, "read_graph", reader)
    monkeypatch.setattr(manager, "_toggle_fit", toggle)
    request = GraphFitRequest(
        frame_id="frame", menu_point=Point(x=1, y=1), models=[FitModel.LINEAR],
        menu_labels={FitModel.LINEAR: "선형"}, display_menu_label="화면",
        copy_display_label="화면 복사",
    )
    outcome = manager.set_graph_fits(app, 1, request)
    assert outcome.after.selected_types == [1]
    toggle.assert_called_once_with(app, 1, request.menu_point, 1, menu_label="선형")
    assert reader.call_count == 2
    for call in reader.call_args_list:
        assert call.kwargs["display_menu_label"] == "화면"
        assert call.kwargs["copy_display_label"] == "화면 복사"


def test_analysis_keeps_observed_labels_after_axis_binding_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = MagicMock()
    reader = MagicMock(return_value=GraphState(fit_enabled=True, selected_types=[], series=[]))
    monkeypatch.setattr(manager, "read_graph", reader)
    monkeypatch.setattr(manager, "select_graph_measurement", MagicMock())
    request = manager.AnalyzeGraphRequest.model_validate({
        "handle": 1, "fitting": {
            "frame_id": "frame", "menu_point": {"x": 1, "y": 1}, "models": [],
            "display_menu_label": "화면", "copy_display_label": "화면 복사",
        }, "x": {"point": {"x": 1, "y": 1}, "menu_path": ["시간"]},
    })
    manager.analyze_graph(app, 1, request)
    assert reader.call_count == 3
    assert all(call.kwargs["copy_display_label"] == "화면 복사"
               for call in reader.call_args_list)


@pytest.mark.parametrize("kind", ["fit", "copy"])
def test_popup_scan_refreshes_target_after_unrelated_snapshot(kind: str) -> None:
    app = MagicMock()
    wanted = _snapshot(label="선형" if kind == "fit" else "화면 복사")
    unrelated = _snapshot(3, label="other")
    fresh = wanted.model_copy(update={"controls": [wanted.controls[0].model_copy(
        update={"ref": "fresh-target"},
    )]})
    app.windows.return_value = [wanted.window, unrelated.window]
    app.snapshot.side_effect = [wanted, unrelated, fresh]
    result = (manager._fit_menu(app, {1}, "선형") if kind == "fit" else
              inspection._display_popup(app, 1, "화면 복사", before={1}))
    assert result is not None
    assert result.controls[0].ref == "fresh-target"
    assert app.snapshot.call_args.args[0] == wanted.window.handle


@pytest.mark.parametrize("kind", ["fit", "copy"])
def test_popup_refresh_revalidates_label_before_returning_refs(kind: str) -> None:
    app = MagicMock()
    wanted = _snapshot(label="선형" if kind == "fit" else "화면 복사")
    app.windows.return_value = [wanted.window]
    app.snapshot.side_effect = [wanted, _snapshot(label="changed")]
    result = (manager._fit_menu(app, {1}, "선형") if kind == "fit" else
              inspection._display_popup(app, 1, "화면 복사", before={1}))
    assert result is None

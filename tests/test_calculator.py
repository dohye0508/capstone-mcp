# Copyright 2026 Capstone MCP contributors.
"""Tests for high-level calculator formula creation tool."""

from unittest.mock import MagicMock

import pytest

from capstone_mcp.calculator import (
    CreateCalculationRequest,
    CreateCalculationResult,
    _find_editor_controls,
    _parse_calculation_name,
    create_calculation,
)
from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.models import Bounds, Control, Snapshot, Window


def _editor(ref: str, name: str, *, enabled: bool = True) -> Control:
    return Control(ref=ref, parent=None, name=name, control_type="Edit",
                   automation_id="", enabled=enabled, visible=True,
                   bounds=Bounds(left=0, top=0, right=100, bottom=30))


def test_unrelated_edit_is_never_used_as_formula_or_unit() -> None:
    assert _find_editor_controls([_editor("search", "Search")]) == (None, None)


def test_ambiguous_formula_editors_are_not_selected_by_order() -> None:
    with pytest.raises(AutomationError, match="ambiguous"):
        _find_editor_controls([_editor("a", "Formula"), _editor("b", "Formula")])


def test_disabled_formula_editor_is_not_mutated() -> None:
    assert _find_editor_controls([_editor("a", "Formula", enabled=False)]) == (None, None)


def test_truncated_calculator_snapshot_is_rejected_before_input() -> None:
    app = MagicMock(spec=Capstone)
    app.snapshot.return_value = Snapshot(
        window=Window(handle=1, title="Capstone", process_id=1,
                      bounds=Bounds(left=0, top=0, right=800, bottom=600)),
        controls=[], truncated=True,
    )
    with pytest.raises(AutomationError, match="truncated"):
        create_calculation(app, CreateCalculationRequest(handle=1, expression="a = 1"))
    app.click.assert_not_called()
    app.keys.assert_not_called()


def test_create_calculation_rejects_empty_expression() -> None:
    app = Capstone()
    req = CreateCalculationRequest(handle=100, expression="")
    with pytest.raises(AutomationError, match="expression"):
        _ = create_calculation(app, req)


@pytest.mark.parametrize("name", ["θ", "λ", "ω", "v₀", "速度"])
def test_calculation_name_preserves_unicode_identifiers(name: str) -> None:
    assert _parse_calculation_name(f"{name} = 2 * [Time]") == name


@pytest.mark.parametrize("expression", ["a = (1 + 2", "a = 1 + 2)", "a = [Force", 'a = "open'])
def test_unbalanced_formula_is_rejected_before_ui_input(expression: str) -> None:
    app = MagicMock(spec=Capstone)
    with pytest.raises(AutomationError, match="unbalanced"):
        _ = create_calculation(app, CreateCalculationRequest(expression=expression))
    app.snapshot.assert_not_called()


def test_unimplemented_variable_bindings_are_rejected_before_ui_input() -> None:
    app = MagicMock(spec=Capstone)
    with pytest.raises(AutomationError, match="variable bindings"):
        _ = create_calculation(app, CreateCalculationRequest(expression="p = m*v", variables={"m": "Mass"}))
    app.snapshot.assert_not_called()


def test_create_calculation_raises_when_calculator_toggle_not_found() -> None:
    app = Capstone()
    mock_window = Window(
        handle=100, title="Capstone", process_id=1,
        bounds=Bounds(left=0, top=0, right=1000, bottom=800),
    )
    app.windows = MagicMock(return_value=[mock_window])
    app.snapshot = MagicMock(return_value=Snapshot(
        window=mock_window,
        controls=[
            Control(
                ref="ref:other", parent=None, name="Hardware Setup",
                control_type="CheckBox",
                automation_id="Palette.ObjNameHardware",
                enabled=True, visible=True,
                bounds=Bounds(left=0, top=0, right=50, bottom=50),
            ),
        ],
        truncated=False,
    ))

    req = CreateCalculationRequest(handle=100, expression="p = [m] * [v]")
    with pytest.raises(AutomationError, match="Calculator"):
        _ = create_calculation(app, req)


def test_create_calculation_submission_is_not_verified_success() -> None:
    app = Capstone()
    mock_window = Window(
        handle=100, title="Capstone", process_id=1,
        bounds=Bounds(left=0, top=0, right=1000, bottom=800),
    )
    app.windows = MagicMock(return_value=[mock_window])

    calc_toggle = Control(
        ref="ref:calc_btn", parent=None, name="Calculator",
        control_type="CheckBox", automation_id="Palette.ObjNameCalculator",
        enabled=True, visible=True,
        bounds=Bounds(left=10, top=100, right=50, bottom=140),
    )
    formula_edit = Control(
        ref="ref:edit_formula", parent=None, name="Calculation Formula",
        control_type="Edit", automation_id="Calculator.FormulaEditor",
        enabled=True, visible=True,
        bounds=Bounds(left=100, top=100, right=300, bottom=130),
    )
    unit_edit = Control(
        ref="ref:edit_unit", parent=None, name="Units",
        control_type="Edit", automation_id="Calculator.UnitEditor",
        enabled=True, visible=True,
        bounds=Bounds(left=310, top=100, right=360, bottom=130),
    )

    step = 0

    def mock_snapshot(*_args: object, **_kwargs: object) -> Snapshot:
        nonlocal step
        step += 1
        controls = [calc_toggle.model_copy(update={"ref": f"ref:calc_btn:{step}"})]
        if step > 1:
            controls.extend([formula_edit, unit_edit])
        return Snapshot(window=mock_window, controls=controls, truncated=False)

    app.snapshot = mock_snapshot
    app.focus_window = MagicMock()
    app.click = MagicMock()
    app.keys = MagicMock()

    mock_toggle_node = MagicMock()
    mock_toggle_node.iface_toggle.ToggleState = 0

    mock_formula_node = MagicMock()
    mock_formula_node.iface_value.SetValue = MagicMock()

    mock_unit_node = MagicMock()
    mock_unit_node.iface_value.SetValue = MagicMock()

    def mock_control(ref: str) -> MagicMock:
        if ref.startswith("ref:calc_btn:"):
            return mock_toggle_node
        if ref == "ref:edit_formula":
            return mock_formula_node
        if ref == "ref:edit_unit":
            return mock_unit_node
        return MagicMock()

    app.control = mock_control

    req = CreateCalculationRequest(
        handle=100,
        expression="KE = 0.5 * [m] * [v]^2",
        unit="J",
    )
    result = create_calculation(app, req)

    assert isinstance(result, CreateCalculationResult)
    assert result.calculation_name == "KE"
    assert result.expression == "KE = 0.5 * [m] * [v]^2"
    assert result.unit == "J"
    assert result.status == "failed"
    assert result.verified is False
    assert "could not be verified" in result.detail

    # Check that calculator toggle was clicked to open and close/restore
    assert app.click.call_count == 2
    app.click.assert_called_with(100, "ref:calc_btn:4", allow_foreground=True)
    mock_formula_node.iface_value.SetValue.assert_called_once_with(
        "KE = 0.5 * [m] * [v]^2",
    )
    mock_unit_node.iface_value.SetValue.assert_called_once_with("J")

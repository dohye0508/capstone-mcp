# Copyright 2026 Capstone MCP contributors.
"""Preserve native success semantics at the bridge response boundary."""

import pytest
from pydantic import JsonValue

from capstone_mcp import bridge


def test_unavailable_value_is_not_reported_as_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the real provider's unavailable-value response shape.
    def unavailable(_port: int, _expression: str) -> JsonValue:
        return {"ReturnValue": 0, "cmdResult": False}

    monkeypatch.setattr(bridge, "evaluate", unavailable)
    # When / Then
    with pytest.raises(bridge.BridgeError):
        _ = bridge.read_measurement(9223, "{measurement}", 0)


def test_successful_zero_remains_a_valid_measurement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    def measured_zero(_port: int, _expression: str) -> JsonValue:
        return {"ReturnValue": 0, "cmdResult": True}

    monkeypatch.setattr(bridge, "evaluate", measured_zero)
    # When
    value = bridge.read_measurement(9223, "{measurement}", 0)
    # Then
    assert value == 0

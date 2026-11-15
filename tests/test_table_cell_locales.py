# Copyright 2026 Capstone MCP contributors.
"""Table cell parsing preserves localized decimals and missing numeric values."""

from capstone_mcp.displays.table import _parse_cell_value


def test_live_cell_decimal_comma_and_text() -> None:
    assert _parse_cell_value("0,750") == 0.75
    assert _parse_cell_value("1.25") == 1.25
    assert _parse_cell_value("NaN") is None
    assert _parse_cell_value("Label") == "Label"
    assert _parse_cell_value("1e999") == "1e999"
    assert _parse_cell_value("1e-999") == "1e-999"

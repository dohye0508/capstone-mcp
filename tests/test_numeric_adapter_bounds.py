# Copyright 2026 Capstone MCP contributors.
"""Adapter boundaries reject representational data loss without desktop access."""

from pathlib import Path

import pytest

from capstone_mcp.capfiles import read_cap_file
from capstone_mcp.csv_data import CsvDataError
from capstone_mcp.data_sources.adapters.capfile import (
    read_capfile_all_series,
    read_capfile_series,
)
from capstone_mcp.data_sources.adapters.csv_file import (
    read_csv_all_columns,
    read_csv_series,
)
from tests.test_capfiles import _payload, _write_cap, _xml


def test_explicit_saved_independent_coordinates_do_not_invent_units(tmp_path: Path) -> None:
    path = tmp_path / "independent.cap"
    _write_cap(path, xml=_xml(3), payload=_payload(["1", "2", "3"]))
    full = read_cap_file(path).datasets[0]
    series = read_capfile_series(path, "@independent", "Observed Value")
    assert series.x.values == [float(value) for value in full.independent_values]
    assert series.x.units == ""
    assert series.metadata["independent_kind"] == full.independent_kind


@pytest.mark.parametrize("value", ["1e999", "-1e999", "1e-999", "-1e-999"])
def test_csv_numeric_range_failure_is_not_a_text_column(tmp_path: Path, value: str) -> None:
    path = tmp_path / "bounds.csv"
    path.write_text(f"Time,Force\n0,{value}\n", encoding="utf-8")
    with pytest.raises(CsvDataError, match="floating-point range"):
        read_csv_all_columns(path)
    with pytest.raises(CsvDataError, match="floating-point range"):
        read_csv_series(path, "Time", "Force")


@pytest.mark.parametrize("value", ["1e999", "-1e999", "1e-999", "-1e-999"])
def test_cap_numeric_range_failure_in_all_adapter_paths(tmp_path: Path, value: str) -> None:
    path = tmp_path / "bounds.cap"
    _write_cap(path, xml=_xml(1), payload=_payload([value]))
    with pytest.raises(ValueError, match="floating-point range"):
        read_capfile_all_series(path)
    for x_name in ("@independent", "Observed Value"):
        with pytest.raises(ValueError, match="floating-point range"):
            read_capfile_series(path, x_name, "Observed Value")


def test_representable_subnormal_zero_and_text_remain_supported(tmp_path: Path) -> None:
    csv_path = tmp_path / "finite.csv"
    csv_path.write_text("Force,Label\n5e-324,a\n-0,b\n", encoding="utf-8")
    assert read_csv_all_columns(csv_path) == {"Force": [5e-324, -0.0]}
    cap_path = tmp_path / "finite.cap"
    _write_cap(cap_path, xml=_xml(2), payload=_payload(["5e-324", "-0"]))
    assert read_capfile_all_series(cap_path)[0] == {"Set": [5e-324, -0.0]}

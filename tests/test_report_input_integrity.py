# Copyright 2026 Capstone MCP contributors.
"""Report input errors remain visible and cannot become fabricated fits."""

from pathlib import Path

import pytest

from capstone_mcp.csv_data import CsvDataError
from capstone_mcp.reports import generator
from capstone_mcp.reports.generator import (
    compute_data_summary,
    compute_linear_regression,
    generate_ascii_plot,
    generate_report,
)


def test_json_with_path_characters_is_parsed_before_filesystem() -> None:
    report = generate_report('  {"x/y": [1,2,3], "z": [2,4,6]}')
    assert report.regression is not None
    assert report.regression.slope == pytest.approx(2)
    assert report.raw_data_points["x/y"] == [1, 2, 3]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_report_input_rejected_at_public_helpers(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        compute_data_summary([1, value], "x")
    with pytest.raises(ValueError, match="finite"):
        compute_linear_regression([1, 2], [value, 3])
    with pytest.raises(ValueError, match="finite"):
        generate_ascii_plot([1, 2], [value, 3])
    with pytest.raises(ValueError, match="finite"):
        generate_report(data_series={"x": [1, 2], "y": [value, 3]})


@pytest.mark.parametrize("text", ['{"x": [NaN]}', '{"x": [1e999]}', '{"x": [true]}'])
def test_invalid_json_numeric_series_is_not_silently_ignored(text: str) -> None:
    with pytest.raises(ValueError, match=r"finite|numeric samples"):
        generate_report(text)


def test_zero_variance_does_not_fabricate_regression() -> None:
    with pytest.raises(ValueError, match="zero variance"):
        generate_report(data_series={"x": [1, 1, 1], "y": [1, 2, 3]})


@pytest.mark.parametrize(("suffix", "content", "message"), [
    (".json", "{broken", "property name"),
    (".cap", "not a zip file", "archive"),
])
def test_file_parse_error_retains_underlying_diagnostic(
    tmp_path: Path, suffix: str, content: str, message: str,
) -> None:
    path = tmp_path / f"invalid{suffix}"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        generate_report(str(path))


def test_csv_adapter_error_is_not_suppressed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "invalid.csv"
    path.write_text("x,y\n", encoding="utf-8")
    failure = CsvDataError("CSV row layout is invalid")

    def failed_read(_path: Path) -> dict[str, list[float]]:
        raise failure

    monkeypatch.setattr(generator, "read_csv_all_columns", failed_read)
    with pytest.raises(CsvDataError, match="row layout") as caught:
        generate_report(str(path))
    assert caught.value is failure


def test_plot_overflow_has_explicit_error() -> None:
    with pytest.raises(ValueError, match="finite"):
        generate_ascii_plot([-1e308, 1e308], [1, 2])

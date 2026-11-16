# Copyright 2026 Capstone MCP contributors.
"""Validate exported values, pagination, and malformed CSV rejection."""

import tracemalloc
from decimal import Decimal
from pathlib import Path

import pytest

from capstone_mcp.csv_data import CsvDataError, read_csv_page


def test_csv_page_preserves_labels_precision_and_missing_values(tmp_path: Path) -> None:
    # Given
    path = tmp_path / "export.csv"
    _ = path.write_text(
        """\
"Force (N) Run 1","Label","Force (N) Run 1"
0.750,"첫 측정",1
,"둘째 측정",2
1.250,"셋째 측정",3
""",
        encoding="utf-8-sig",
    )
    # When
    page = read_csv_page(str(path), 0, 2)
    # Then
    assert page.row_count == 3
    assert page.returned_rows == 2
    assert page.next_offset == 2
    assert page.columns[0].values == ["0.750", ""]
    assert page.columns[0].numeric_values == [Decimal("0.750"), None]
    assert page.columns[1].values == ["첫 측정", "둘째 측정"]
    assert page.columns[1].numeric_values is None
    assert page.columns[0].label == page.columns[2].label
    assert page.columns[0].index != page.columns[2].index


def test_csv_page_does_not_retain_rows_outside_page(tmp_path: Path) -> None:
    path = tmp_path / "large.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        _ = stream.write("index,label\n")
        for index in range(30_000):
            _ = stream.write(f"{index},{'x' * 64}\n")

    tracemalloc.start()
    try:
        page = read_csv_page(str(path), offset=29_998, limit=2)
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert page.row_count == 30_000
    assert page.columns[0].values == ["29998", "29999"]
    assert page.next_offset is None
    assert peak_bytes < 1_000_000


def test_csv_page_reads_semicolon_and_decimal_comma(tmp_path: Path) -> None:
    path = tmp_path / "export.csv"
    _ = path.write_text(
        'Time (s);Force (N);Label\n0,750;1,25e-2;"notes; 1,2"\n;2,50;next\n',
        encoding="utf-8-sig",
    )

    page = read_csv_page(str(path))

    assert [c.label for c in page.columns] == ["Time (s)", "Force (N)", "Label"]
    assert page.columns[0].values == ["0,750", ""]
    assert page.columns[0].numeric_values == [Decimal("0.750"), None]
    assert page.columns[1].numeric_values == [Decimal("0.0125"), Decimal("2.50")]
    assert page.columns[2].values == ["notes; 1,2", "next"]


@pytest.mark.parametrize("text", ["", "a,b\n1\n", 'a,b\n"unclosed,2'])
def test_malformed_exports_are_not_silently_padded(
    tmp_path: Path, text: str,
) -> None:
    # Given
    path = tmp_path / "export.csv"
    _ = path.write_text(text, encoding="utf-8")
    # When / Then
    with pytest.raises(CsvDataError):
        _ = read_csv_page(str(path))

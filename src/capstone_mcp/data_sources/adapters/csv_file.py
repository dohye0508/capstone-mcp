# Copyright 2026 Capstone MCP contributors.
"""Read validated CSV data without inventing channels or shifting missing rows."""

import math
import re
import unicodedata
from pathlib import Path

from capstone_mcp.csv_data import CsvDataError, parse_csv_number, read_csv_table
from capstone_mcp.data_sources.models import (
    DataSeries,
    DatasetMetadata,
    ExperimentSeries,
)


def _parse_col_header(header: str) -> tuple[str, str]:
    match = re.search(r"^(.+?)\s*\((.*?)\)$", header.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return header.strip(), ""


def _normalized(name: str) -> str:
    return unicodedata.normalize("NFC", name.strip()).casefold()


def _column_index(columns: list[tuple[str, str]], query: str) -> int:
    target = _normalized(query)
    exact = [i for i, (name, _) in enumerate(columns) if _normalized(name) == target]
    partial = [i for i, (name, _) in enumerate(columns) if target in _normalized(name)]
    matches = exact or partial
    if not target or not matches:
        msg = f"CSV column {query!r} was not found."
        raise CsvDataError(msg)
    if len(matches) != 1:
        msg = f"CSV column {query!r} is ambiguous; use a unique header."
        raise CsvDataError(msg)
    return matches[0]


class CsvNumberRangeError(CsvDataError):
    """A numeric cell cannot be represented without overflow or zero underflow."""


def _numeric_cell(value: str) -> float | None:
    number = parse_csv_number(value)
    if number is None:
        if value.strip():
            msg = "CSV number must be finite."
            raise CsvNumberRangeError(msg)
        return None
    result = float(number)
    if not math.isfinite(result) or (result == 0.0 and number != 0):
        msg = "CSV number is outside the nonzero finite floating-point range."
        raise CsvNumberRangeError(msg)
    return result


def read_csv_datasets(path: Path) -> list[DatasetMetadata]:
    """Inspect bounded CSV metadata without claiming text cells are numeric."""
    table = read_csv_table(path)
    return [
        DatasetMetadata(
            name=_parse_col_header(header)[0],
            units=_parse_col_header(header)[1],
            run_id=None,
            sample_count=sum(bool(row[index].strip()) for row in table.rows),
        )
        for index, header in enumerate(table.header)
    ]


def read_csv_series(path: Path, x_name: str, y_name: str) -> ExperimentSeries:
    """Select unique columns and retain blanks in their original sample positions."""
    table = read_csv_table(path)
    columns = [_parse_col_header(header) for header in table.header]
    x_index = _column_index(columns, x_name)
    y_index = _column_index(columns, y_name)
    x_label, x_unit = columns[x_index]
    y_label, y_unit = columns[y_index]
    return ExperimentSeries(
        x=DataSeries(
            name=x_label,
            units=x_unit,
            values=[_numeric_cell(row[x_index]) for row in table.rows],
        ),
        y=DataSeries(
            name=y_label,
            units=y_unit,
            values=[_numeric_cell(row[y_index]) for row in table.rows],
        ),
        metadata={"source": str(path), "format": "csv"},
    )


def read_csv_all_columns(path: Path) -> dict[str, list[float]]:
    """Read numeric columns with NaN placeholders for blank cells."""
    table = read_csv_table(path)
    series: dict[str, list[float]] = {}
    names: set[str] = set()
    for index, header in enumerate(table.header):
        values: list[float | None] = []
        invalid = False
        for row in table.rows:
            try:
                values.append(_numeric_cell(row[index]))
            except CsvNumberRangeError:
                raise
            except CsvDataError:
                invalid = True
        if not any(value is not None for value in values):
            continue
        if invalid:
            msg = f"CSV column {header!r} contains invalid samples."
            raise CsvDataError(msg)
        name = header.strip()
        if _normalized(name) in names:
            msg = f"Duplicate numeric CSV column: {name!r}."
            raise CsvDataError(msg)
        names.add(_normalized(name))
        series[name] = [math.nan if value is None else value for value in values]
    return series

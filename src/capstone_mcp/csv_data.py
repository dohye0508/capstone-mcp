# Copyright 2026 Capstone MCP contributors.
"""Bounded pages of native CSV export text, without invented dataset identities."""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final

from capstone_mcp.models import Model

MAX_CSV_BYTES: Final = 64 * 1024 * 1024
MAX_ROWS: Final = 1_000_000
MAX_COLUMNS: Final = 1024
MAX_PAGE_CELLS: Final = 100_000


class CsvDataError(ValueError):
    """The exported text is malformed or exceeds extraction bounds."""


class CsvColumn(Model):
    """Raw header and cells; parsed numbers are not a native source-type claim."""

    index: int
    label: str
    values: list[str]
    numeric_values: list[Decimal | None] | None


class CsvPage(Model):
    """One page of an immutable export; column indices disambiguate repeated labels."""

    path: str
    row_count: int
    offset: int
    returned_rows: int
    next_offset: int | None
    columns: list[CsvColumn]


def _numbers(values: list[str]) -> list[Decimal | None] | None:
    parsed: list[Decimal | None] = []
    has_value = False
    for value in values:
        if not value.strip():
            parsed.append(None)
            continue
        try:
            numeric = Decimal(value)
        except InvalidOperation:
            return None
        has_value = True
        parsed.append(numeric if numeric.is_finite() else None)
    return parsed if has_value else None


def read_csv_page(path: str, offset: int = 0, limit: int = 1000) -> CsvPage:
    """Read UTF-8 CSV without assuming unit symbols, run IDs, or time alignment."""
    source = Path(path).resolve()
    if source.stat().st_size > MAX_CSV_BYTES:
        msg = "CSV exceeds the 64 MiB extraction limit."
        raise CsvDataError(msg)
    rows: list[list[str]] = []
    with source.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        try:
            header = next(reader, None)
            if not header or len(header) > MAX_COLUMNS:
                msg = "CSV needs a header with at most 1024 columns."
                raise CsvDataError(msg)
            for row in reader:
                if len(row) != len(header) or len(rows) >= MAX_ROWS:
                    msg = "CSV is ragged or exceeds the one-million-row limit."
                    raise CsvDataError(msg)
                rows.append(row)
        except csv.Error as error:
            raise CsvDataError(str(error)) from error
    page_limit = min(limit, MAX_PAGE_CELLS // len(header))
    page = rows[offset:offset + page_limit]
    columns: list[CsvColumn] = []
    for index, label in enumerate(header):
        values = [row[index] for row in page]
        columns.append(CsvColumn(
            index=index, label=label, values=values, numeric_values=_numbers(values),
        ))
    next_offset = offset + len(page)
    return CsvPage(
        path=str(source), row_count=len(rows), offset=offset, returned_rows=len(page),
        next_offset=next_offset if next_offset < len(rows) else None,
        columns=columns,
    )

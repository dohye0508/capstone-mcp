# Copyright 2026 Capstone MCP contributors.
"""Bounded pages of native CSV export text, without invented dataset identities."""

import csv
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final

from capstone_mcp.models import Model

MAX_CSV_BYTES: Final = 64 * 1024 * 1024
MAX_ROWS: Final = 1_000_000
MAX_COLUMNS: Final = 1024
MAX_PAGE_CELLS: Final = 100_000
DELIMITER_SAMPLE_ROWS: Final = 20


class CsvDataError(ValueError):
    """The exported text is malformed or exceeds extraction bounds."""


@dataclass
class CsvTable:
    """Validated CSV cells shared by paging and analysis adapters."""

    header: list[str]
    rows: list[list[str]]


def parse_csv_number(value: str) -> Decimal | None:
    """Parse decimal-point or decimal-comma values, without thousands grouping."""
    value = value.strip()
    if not value:
        return None
    if "," in value and "." not in value and value.count(",") == 1:
        value = value.replace(",", ".")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        msg = f"Invalid numeric CSV value: {value!r}."
        raise CsvDataError(msg) from exc
    return number if number.is_finite() else None


def _decode_csv(payload: bytes) -> str:
    if payload.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings = ("utf-16",)
    else:
        encodings = ("utf-8-sig", "cp949")
    for encoding in encodings:
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    msg = "CSV must be UTF-8, BOM-marked UTF-16, or CP949 text."
    raise CsvDataError(msg)


def _csv_delimiter(text: str) -> str:
    candidates: list[str] = []
    header_candidates: list[str] = []
    for delimiter in (",", ";", "\t"):
        reader = csv.reader(io.StringIO(text), delimiter=delimiter, strict=True)
        try:
            header = next(reader, [])
            if len(header) <= 1:
                continue
            header_candidates.append(delimiter)
            consistent = True
            for index, row in enumerate(reader):
                if len(row) != len(header):
                    consistent = False
                    break
                if index + 1 >= DELIMITER_SAMPLE_ROWS:
                    break
            if consistent:
                candidates.append(delimiter)
        except csv.Error:
            continue
    candidates = candidates or header_candidates
    if len(candidates) > 1:
        msg = "CSV delimiter is ambiguous; export with quoted fields."
        raise CsvDataError(msg)
    return candidates[0] if candidates else ","


def read_csv_table(path: str | Path) -> CsvTable:
    """Read a bounded, rectangular UTF-8/UTF-16/CP949 comma/semicolon/tab table."""
    source = Path(path)
    with source.open("rb") as stream:
        payload = stream.read(MAX_CSV_BYTES + 1)
    if len(payload) > MAX_CSV_BYTES:
        msg = "CSV exceeds the 64 MiB extraction limit."
        raise CsvDataError(msg)
    text = _decode_csv(payload)
    reader = csv.reader(
        io.StringIO(text, newline=""), delimiter=_csv_delimiter(text), strict=True,
    )
    try:
        header = next(reader, None)
        if not header or len(header) > MAX_COLUMNS:
            msg = "CSV needs a header with at most 1024 columns."
            raise CsvDataError(msg)
        rows: list[list[str]] = []
        for row in reader:
            if len(row) != len(header) or len(rows) >= MAX_ROWS:
                msg = "CSV is ragged or exceeds the one-million-row limit."
                raise CsvDataError(msg)
            rows.append(row)
    except csv.Error as exc:
        raise CsvDataError(str(exc)) from exc
    return CsvTable(header, rows)


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
            numeric = parse_csv_number(value)
        except CsvDataError:
            return None
        has_value = True
        parsed.append(numeric)
    return parsed if has_value else None


def read_csv_page(path: str, offset: int = 0, limit: int = 1000) -> CsvPage:
    """Read CSV without assuming unit symbols, run IDs, or time alignment."""
    if offset < 0 or limit < 1:
        msg = "CSV offset must be nonnegative and limit must be positive."
        raise CsvDataError(msg)
    source = Path(path).resolve()
    table = read_csv_table(source)
    header, rows = table.header, table.rows
    page_limit = min(limit, MAX_PAGE_CELLS // len(header))
    page = rows[offset : offset + page_limit]
    columns: list[CsvColumn] = []
    for index, label in enumerate(header):
        values = [row[index] for row in page]
        columns.append(
            CsvColumn(
                index=index,
                label=label,
                values=values,
                numeric_values=_numbers(values),
            ),
        )
    next_offset = offset + len(page)
    return CsvPage(
        path=str(source),
        row_count=len(rows),
        offset=offset,
        returned_rows=len(page),
        next_offset=next_offset if next_offset < len(rows) else None,
        columns=columns,
    )

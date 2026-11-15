# Copyright 2026 Capstone MCP contributors.
"""Table display creation, column mapping, and data extraction."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any

from pywinauto.uia_defines import NoPatternInterfaceError

from capstone_mcp.csv_data import CsvDataError, parse_csv_number
from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.displays.harness import (
    center_coords,
    click_control,
    find_display_container,
    find_palette_item,
    is_within_bounds,
)
from capstone_mcp.displays.models import (
    MAX_HEADER_HEIGHT_PX,
    ROW_Y_TOLERANCE_PX,
    STATISTICS_KEYWORDS,
    TABLE_PALETTE_NAME,
    CreateTableRequest,
    CreateTableResult,
    ReadTableRequest,
    ReadTableResult,
    SetTableColumnsRequest,
    SetTableColumnsResult,
)

if TYPE_CHECKING:
    from capstone_mcp.models import Control


def _find_table_palette_item(controls: list[Control]) -> Control:
    """Find Table display item in the Displays palette."""
    return find_palette_item(controls, TABLE_PALETTE_NAME, ".ObjNameTable")


def _find_table_control(
    controls: list[Control],
    table_name: str | None = None,
) -> Control:
    """Locate the target Table widget container."""
    return find_display_container(controls, "table", table_name)


def _find_column_headers(controls: list[Control], table_ctrl: Control) -> list[Control]:
    """Find column header buttons or header items belonging to the table."""
    headers = [
        c
        for c in controls
        if c.visible
        and (
            c.parent == table_ctrl.ref
            or (
                c.bounds.top >= table_ctrl.bounds.top
                and c.bounds.bottom <= table_ctrl.bounds.top + MAX_HEADER_HEIGHT_PX
                and c.bounds.left >= table_ctrl.bounds.left
                and c.bounds.right <= table_ctrl.bounds.right
            )
        )
        and (
            c.control_type in ("HeaderItem", "Header")
            or "header" in c.automation_id.lower()
            or "select measurement" in c.name.lower()
        )
    ]
    headers.sort(key=lambda h: h.bounds.left)
    return headers


def _find_add_column_button(
    controls: list[Control],
    table_ctrl: Control,
) -> Control | None:
    """Find '+' or 'Add Column' button in the table."""
    matches = [
        c
        for c in controls
        if c.visible
        and c.enabled
        and c.control_type == "Button"
        and (
            c.name.strip().lower() == "add column"
            or "addcolumn" in c.automation_id.lower()
            or "add_column" in c.automation_id.lower()
        )
        and is_within_bounds(c, table_ctrl)
    ]
    if len(matches) > 1:
        msg = "Ambiguous Add Column controls in the selected table."
        raise AutomationError(msg)
    return matches[0] if matches else None


def create_table(
    app: Capstone,
    request: CreateTableRequest | None = None,
) -> CreateTableResult:
    """Insert a Table display into the active page via the Displays palette."""
    if request is None:
        request = CreateTableRequest()

    if not request.allow_foreground:
        msg = "Table creation requires allow_foreground=true."
        raise AutomationError(msg)

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    palette_item = _find_table_palette_item(snapshot.controls)

    click_control(
        app,
        request.handle,
        palette_item,
        double=True,
        allow_foreground=True,
    )

    t_name = request.table_name or "Table"
    return CreateTableResult(
        created=True,
        table_name=t_name,
        verified=True,
        detail=f"Table display '{t_name}' created.",
    )


def set_table_columns(
    app: Capstone,
    request: SetTableColumnsRequest,
) -> SetTableColumnsResult:
    """Map measurements to Table columns, auto-expanding as needed."""
    if not request.columns:
        msg = "columns must not be empty."
        raise AutomationError(msg)

    if not request.allow_foreground:
        msg = "Setting table columns requires allow_foreground=true."
        raise AutomationError(msg)

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    table_ctrl = _find_table_control(snapshot.controls, request.table_name)
    headers = _find_column_headers(snapshot.controls, table_ctrl)
    for i, col_name in enumerate(request.columns):
        if i >= len(headers):
            add_btn = _find_add_column_button(snapshot.controls, table_ctrl)
            if add_btn is None:
                break
            click_control(app, request.handle, add_btn, allow_foreground=True)
            snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
            table_ctrl = _find_table_control(snapshot.controls, request.table_name)
            headers = _find_column_headers(snapshot.controls, table_ctrl)

        if i >= len(headers) or not headers[i].enabled:
            break
        if headers[i].name.strip() == col_name.strip():
            continue
        try:
            _ = app.set_value(headers[i].ref, col_name)
        except NoPatternInterfaceError:
            break
        snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
        table_ctrl = _find_table_control(snapshot.controls, request.table_name)
        headers = _find_column_headers(snapshot.controls, table_ctrl)
        if i >= len(headers) or headers[i].name.strip() != col_name.strip():
            break

    t_name = request.table_name or table_ctrl.name or "Table"
    observed = [header.name.strip() for header in headers[:len(request.columns)]]
    verified = observed == [name.strip() for name in request.columns]
    detail = f"Observed {len(observed)} column headers in Table '{t_name}'."
    return SetTableColumnsResult(
        table_name=t_name,
        columns=observed,
        column_count=len(observed),
        verified=verified,
        detail=detail,
    )


def _parse_cell_value(text: str) -> float | str | None:
    """Parse string into float if numeric, or preserve raw string."""
    val = text.strip()
    if not val or val == "-":
        return None
    try:
        number = parse_csv_number(val)
    except CsvDataError:
        return val
    if number is None:
        return None
    converted = float(number)
    if not math.isfinite(converted) or (converted == 0 and number != 0):
        return val
    return converted


def _extract_cells_and_statistics(
    controls: list[Control],
    table_ctrl: Control,
    headers: list[Control],
) -> tuple[list[tuple[int, str, str]], dict[str, dict[str, Any]]]:
    """Separate raw data cell coordinates and statistical summary values."""
    cells_by_pos: list[tuple[int, str, str]] = []
    stat_rows: dict[str, dict[str, Any]] = {}
    table_b = table_ctrl.bounds
    header_refs = {h.ref for h in headers}

    for c in controls:
        if not c.visible or c.ref == table_ctrl.ref or c.ref in header_refs:
            continue
        if not (
            c.bounds.top >= table_b.top
            and c.bounds.bottom <= table_b.bottom
            and c.bounds.left >= table_b.left
            and c.bounds.right <= table_b.right
        ):
            continue

        if c.control_type in ("DataItem", "Text", "Edit", "Custom"):
            text = c.name.strip()
            if not text:
                continue

            x, _y = center_coords(c.bounds)
            column = next(
                (h.name.strip() for h in headers
                 if h.bounds.left <= x < h.bounds.right),
                "",
            )
            if not column or "select measurement" in column.lower():
                continue

            lower = text.lower()
            matched_stat = next(
                (
                    k
                    for k in STATISTICS_KEYWORDS
                    if lower.startswith(k) or f"{k}:" in lower
                ),
                None,
            )
            if matched_stat:
                stat_key = matched_stat.title()
                m = re.search(r"[:=]\s*([+-]?\d+(?:\.\d+)?)", text)
                parsed_val = float(m.group(1)) if m else _parse_cell_value(text)
                stat_rows.setdefault(stat_key, {})[column] = parsed_val
            else:
                cells_by_pos.append((c.bounds.top, column, text))

    return cells_by_pos, stat_rows


def _group_cells_into_rows(
    cells_by_pos: list[tuple[int, str, str]],
    column_names: list[str],
) -> list[dict[str, Any]]:
    """Group spatial cell coordinates into structured rows."""
    cells_by_pos.sort(key=lambda cell: cell[0])
    rows: list[dict[str, Any]] = []
    current_top: int | None = None

    for top, column, text in cells_by_pos:
        if current_top is None or top - current_top > ROW_Y_TOLERANCE_PX:
            rows.append(dict.fromkeys(column_names))
            current_top = top
        rows[-1][column] = _parse_cell_value(text)

    return rows


def read_table(
    app: Capstone,
    request: ReadTableRequest | None = None,
) -> ReadTableResult:
    """Read rendered cell data and statistical summary rows with pagination."""
    if request is None:
        request = ReadTableRequest()

    if request.page < 1:
        msg = "page must be >= 1."
        raise AutomationError(msg)

    if request.page_size <= 0:
        msg = "page_size must be > 0."
        raise AutomationError(msg)

    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    table_ctrl = _find_table_control(snapshot.controls, request.table_name)

    headers = _find_column_headers(snapshot.controls, table_ctrl)
    column_names = [
        h.name.strip()
        for h in headers
        if h.name.strip() and "select measurement" not in h.name.lower()
    ]
    if not column_names:
        column_names = ["Column 1", "Column 2"]

    cells_by_pos, stat_rows = _extract_cells_and_statistics(
        snapshot.controls,
        table_ctrl,
        headers,
    )
    formatted_rows = _group_cells_into_rows(cells_by_pos, column_names)

    total_rows = len(formatted_rows)
    total_pages = max(1, math.ceil(total_rows / request.page_size))

    start_idx = (request.page - 1) * request.page_size
    end_idx = start_idx + request.page_size
    paged_rows = formatted_rows[start_idx:end_idx]

    detail = (
        f"Read {len(paged_rows)} row(s) (page {request.page}/{total_pages}, "
        f"total {total_rows}) across {len(column_names)} column(s)."
    )

    t_name = request.table_name or table_ctrl.name or "Table"

    return ReadTableResult(
        table_name=t_name,
        columns=column_names,
        rows=paged_rows,
        row_count=len(paged_rows),
        total_rows=total_rows,
        page=request.page,
        page_size=request.page_size,
        total_pages=total_pages,
        statistics=stat_rows if request.include_statistics else None,
        has_more=end_idx < total_rows,
        verified=True,
        detail=detail,
    )

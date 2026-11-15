# Copyright 2026 Capstone MCP contributors.
"""Explicit labels and IDs observed in native file workflow controls."""
from typing import Annotated

from pydantic import Field

from capstone_mcp.models import Model

ObservedLabel = Annotated[str, Field(min_length=1, max_length=256)]


class FileWorkflowLabels(Model):
    """Exact observed mapping; this does not translate or certify a native locale."""

    file_menu: ObservedLabel = "File"
    filename_id: ObservedLabel = "1001"
    open_filename_id: ObservedLabel = "1148"
    discard: ObservedLabel = "Discard"
    export_format: ObservedLabel = "Export Format"
    csv_format: ObservedLabel = "Comma separated values"
    alignment_options: ObservedLabel = "Alignment Options"
    align_by_index: ObservedLabel = "Align by Index"
    select_all: ObservedLabel = "Select All"
    export_to_file: ObservedLabel = "Export to file..."
    close: ObservedLabel = "Close"

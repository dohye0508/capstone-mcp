# Copyright 2026 Capstone MCP contributors.
"""The reported document title reflects the completed Save As."""

import time
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import pytest

from capstone_mcp import file_workflows
from capstone_mcp.models import Bounds, Window

if TYPE_CHECKING:
    from capstone_mcp.desktop import Capstone

HANDLE = 5
BOUNDS = Bounds(left=0, top=0, right=5, bottom=5)


def _app(titles: list[str]) -> tuple["Capstone", Mock]:
    windows = Mock(side_effect=[
        [Window(handle=HANDLE, title=title, process_id=7, bounds=BOUNDS)]
        for title in titles
    ])
    return cast("Capstone", cast("object", Mock(windows=windows))), windows


def test_saved_title_waits_for_capstone_to_rename_the_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the window still shows the previous name right after the save.
    monkeypatch.setattr(time, "sleep", Mock())
    app, windows = _app(["old.cap*", "old.cap*", "new.cap"])
    # When
    title = file_workflows.settled_title(
        app, HANDLE, Path("C:/out/new.cap"), "cap",
    )
    # Then
    assert title == "new.cap"
    assert windows.call_count == 3


def test_unrenamed_title_is_reported_as_observed_after_the_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the title never changes and the bound has already elapsed.
    monkeypatch.setattr(file_workflows, "TITLE_SECONDS", 0.0)
    app, _windows = _app(["old.cap*"])
    # When
    title = file_workflows.settled_title(
        app, HANDLE, Path("C:/out/new.cap"), "cap",
    )
    # Then: nothing is invented.
    assert title == "old.cap*"


def test_export_reads_the_title_once_because_it_never_renames() -> None:
    app, windows = _app(["experiment.cap*"])
    title = file_workflows.settled_title(
        app, HANDLE, Path("C:/out/data.csv"), "csv",
    )
    assert title == "experiment.cap*"
    windows.assert_called_once()

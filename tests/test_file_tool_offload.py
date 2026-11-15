# Copyright 2026 Capstone MCP contributors.
"""Verify registered file tools offload actual parsing work."""

import threading
from pathlib import Path

import pytest

from capstone_mcp import server
from capstone_mcp.tools import files
from tests.test_capfiles import _payload, _write_cap, _xml


@pytest.mark.anyio
async def test_archive_extraction_runs_outside_event_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "thread.cap"
    _write_cap(path, xml=_xml(1), payload=_payload(["4.0"]))
    main_thread = threading.get_ident()
    original = files.read_cap_dataset_page
    threads: list[int] = []

    def observed(*args: object) -> object:
        threads.append(threading.get_ident())
        return original(*args)

    monkeypatch.setattr(files, "read_cap_dataset_page", observed)
    tool = server.MCP._tool_manager.get_tool("capstone_extract_dataset")
    assert tool is not None
    result = await tool.fn(str(path), 0)
    assert result.raw_values == ["4.0"]
    assert threads
    assert threads[0] != main_thread

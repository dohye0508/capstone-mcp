# Copyright 2026 Capstone MCP contributors.
"""Actual stdio MCP tests using only local synthetic archives and pure tools."""

import json
import sys
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from tests.test_capfiles import _payload, _write_cap, _xml

_REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.anyio
async def test_real_stdio_guide_and_archive_page_without_capstone(tmp_path: Path) -> None:
    path = tmp_path / "측정.cap"
    _write_cap(path, xml=_xml(3), payload=_payload(["1.25", "2.50", "3.75"]))
    bad = tmp_path / "bad.cap"
    bad.write_bytes(b"not a zip")
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "capstone_mcp.server"],
        cwd=str(_REPO_ROOT),
    )
    with anyio.fail_after(45):
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            assert "capstone_guide" in {tool.name for tool in tools.tools}
            assert len(tools.tools) <= 22
            guide = await session.call_tool("capstone_guide", {"topic": "files"})
            assert not guide.isError
            result = await session.call_tool("capstone_extract_dataset", {
                "path": str(path), "dataset_index": 0, "offset": 1, "limit": 1,
            })
            assert not result.isError
            assert result.structuredContent is not None
            assert result.structuredContent["raw_values"] == ["2.50"]
            assert result.structuredContent["sample_indices"] == [1]
            error = await session.call_tool("capstone_file_datasets", {"path": str(bad)})
            assert error.isError
            payload = json.loads(next(c.text for c in error.content if isinstance(c, TextContent)))
            assert {"error_code", "message", "remediation"} <= payload.keys()
            assert "Traceback" not in payload["message"]
            regression = await session.call_tool("capstone_linear_fit", {
                "samples": {"x": [1, 1, 1], "y": [1, 2, 3]},
            })
            assert regression.isError
            failure = json.loads(next(c.text for c in regression.content if isinstance(c, TextContent)))
            assert {"error_code", "message", "remediation"} <= failure.keys()
            assert any(word in failure["message"].lower() for word in ("variance", "variation"))

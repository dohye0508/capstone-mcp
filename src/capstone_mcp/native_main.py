# Copyright 2026 Capstone MCP contributors.
"""Native-free bootstrap waiting for the parent's process-job assignment."""

import runpy
import sys


def main() -> None:
    """Import the COM runtime only after an explicit parent initialization signal."""
    if sys.stdin.readline() != "INITIALIZE\n":
        return
    sys.__dict__["coinit_flags"] = 0
    _ = runpy.run_module("capstone_mcp.native_loop", run_name="__main__")


if __name__ == "__main__":
    main()

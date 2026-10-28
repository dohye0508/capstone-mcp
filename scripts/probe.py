# Copyright 2026 Capstone MCP contributors.
"""Read-only probe of the real Capstone adapter."""

import sys

from capstone_mcp.desktop import Capstone

app = Capstone()
windows = app.attach()
for window in windows:
    _ = sys.stdout.write(window.model_dump_json() + "\n")
    snapshot = app.snapshot(window.handle, 12, 800)
    _ = sys.stdout.write(snapshot.model_dump_json() + "\n")

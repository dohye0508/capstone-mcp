# Copyright 2026 Capstone MCP contributors.
"""Locate optional real Capstone archives for local regression tests."""

import os
from pathlib import Path
from typing import Final

GOLDEN_MASTER_DIR: Final = Path(
    os.environ.get("CAPSTONE_GOLDEN_MASTER_DIR")
    or Path.home() / "Downloads" / "(2026)캡스톤 실험별 파일",
)

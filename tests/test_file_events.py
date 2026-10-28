# Copyright 2026 Capstone MCP contributors.
"""Check native output-file readiness without delay-based polling."""

from pathlib import Path

from capstone_mcp.file_events import FileEvents, file_is_closed
from capstone_mcp.ui_events import StateChanges


def test_directory_event_confirms_closed_file(tmp_path: Path) -> None:
    # Given
    target = tmp_path / "output.csv"
    changes = StateChanges()
    with FileEvents(tmp_path, changes) as events:
        generation = changes.generation
        # When
        _ = target.write_text("x,y\n1,2\n", encoding="utf-8")
        ready = changes.until(
            lambda: True if (
                changes.generation > generation and events.ready(target)
            ) else None, 5,
        )
        # Then
        assert ready
    assert not events.thread.is_alive()


def test_open_writer_is_not_a_completed_export(tmp_path: Path) -> None:
    # Given
    target = tmp_path / "output.csv"
    with target.open("w", encoding="utf-8") as writer:
        _ = writer.write("x,y\n1,2\n")
        writer.flush()
        # When / Then
        assert not file_is_closed(target)
    assert file_is_closed(target)


def test_other_readers_do_not_block_completed_export(tmp_path: Path) -> None:
    # Given
    target = tmp_path / "output.csv"
    _ = target.write_text("x,y\n1,2\n", encoding="utf-8")
    # When / Then
    with target.open("rb"):
        assert file_is_closed(target)

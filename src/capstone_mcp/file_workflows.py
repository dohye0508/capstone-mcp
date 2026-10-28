# Copyright 2026 Capstone MCP contributors.
"""Observed native save/export dialogs with event-confirmed output completion."""

from __future__ import annotations

import hashlib
from _ctypes import COMError
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

from capstone_mcp.capfiles import read_cap_configuration
from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.file_events import FileEvents
from capstone_mcp.models import Action, Control, Model, Snapshot
from capstone_mcp.ui_events import WindowEvents

if TYPE_CHECKING:
    from collections.abc import Callable

MAX_OUTPUT_BYTES: Final = 64 * 1024 * 1024
TRANSITION_SECONDS: Final = 15


class FileArtifact(Model):
    """A closed, confirmed native output; the document itself may remain unsaved."""

    path: str
    format: Literal["cap", "csv"]
    size_bytes: int
    sha256: str
    document_title_before: str
    document_title_after: str
    precision: Literal["native-cache", "capstone-export"]


def _one(snapshot: Snapshot, predicate: Callable[[Control], bool]) -> Control:
    matches = [c for c in snapshot.controls if c.visible and predicate(c)]
    if len(matches) != 1 or not matches[0].enabled:
        msg = "Expected one enabled native control; inspect the current dialog."
        raise AutomationError(msg)
    return matches[0]


def _new_snapshot(
    app: Capstone, before: set[int], predicate: Callable[[Snapshot], bool],
    *, depth: int = 2,
) -> Snapshot | None:
    for window in app.windows():
        if window.handle in before:
            continue
        try:
            snapshot = app.snapshot(window.handle, depth, 1500)
        except (COMError, AutomationError):
            continue
        if predicate(snapshot):
            return snapshot
    return None


def _named_button(app: Capstone, handle: int, name: str) -> Control:
    return _one(
        app.snapshot(handle, 1, 200),
        lambda c: c.control_type == "Button" and c.name == name,
    )


def _open_command(
    app: Capstone, events: WindowEvents, handle: int, command_id: str,
) -> set[int]:
    before = {w.handle for w in app.windows()}
    file_menu = _one(
        app.snapshot(handle, 2, 300),
        lambda c: c.control_type == "MenuItem" and c.name == "File",
    )
    _ = app.act(file_menu.ref, Action.INVOKE)
    menu = events.changes.until(
        lambda: _new_snapshot(
            app, before,
            lambda s: any(c.automation_id == command_id for c in s.controls),
        ),
        TRANSITION_SECONDS,
    )
    command = _one(menu, lambda c: c.automation_id == command_id)
    _ = app.act(command.ref, Action.INVOKE)
    return before


def _choose_export_option(
    app: Capstone, events: WindowEvents, handle: int, button: str, option: str,
) -> None:
    before = {w.handle for w in app.windows()}
    control = _named_button(app, handle, button)
    _ = app.act(control.ref, Action.INVOKE)
    menu = events.changes.until(
        lambda: _new_snapshot(
            app, before,
            lambda s: any(
                c.control_type == "MenuItem" and c.name == option for c in s.controls
            ),
        ),
        TRANSITION_SECONDS,
    )
    control = _one(
        menu, lambda c: c.control_type == "MenuItem" and c.name == option,
    )
    menu_handle = menu.window.handle
    _ = app.act(control.ref, Action.INVOKE)
    _ = events.changes.until(
        lambda: True if all(
            w.handle != menu_handle for w in app.windows()
        ) else None,
        TRANSITION_SECONDS,
    )


def _file_dialog(
    app: Capstone, events: WindowEvents, before: set[int],
) -> Snapshot:
    return events.changes.until(
        lambda: _new_snapshot(
            app, before,
            lambda s: any(
                c.control_type == "Edit" and c.automation_id == "1001"
                for c in s.controls
            ),
            depth=12,
        ),
        TRANSITION_SECONDS,
    )


def _save_dialog(
    app: Capstone, files: FileEvents,
    dialog: Snapshot, path: Path, allowed_windows: set[int],
) -> None:
    field = _one(
        dialog, lambda c: c.control_type == "Edit" and c.automation_id == "1001",
    )
    _ = app.set_value(field.ref, str(path))
    snapshot = app.snapshot(dialog.window.handle, 12, 1500)
    save = _one(
        snapshot, lambda c: c.control_type == "Button" and c.automation_id == "1",
    )
    if path.exists():
        msg = "Output appeared before Save; overwrite was not authorized."
        raise AutomationError(msg)
    _ = app.act(save.ref, Action.INVOKE)
    _ = files.changes.until(
        lambda: True if files.ready(path) and {
            w.handle for w in app.windows()
        }.issubset(allowed_windows) else None,
        TRANSITION_SECONDS,
    )


def _prepare(
    app: Capstone, handle: int, destination: str, suffix: str,
    *, allow_foreground: bool,
) -> tuple[Path, str, int]:
    if not allow_foreground:
        msg = "Saving/exporting uses native dialog input; foreground input is disabled."
        raise AutomationError(msg)
    path = Path(destination).resolve()
    if path.suffix.lower() != suffix or path.exists():
        msg = f"Choose a new {suffix} path; existing files are never overwritten."
        raise AutomationError(msg)
    if not path.parent.is_dir():
        msg = "Output directory must already exist."
        raise AutomationError(msg)
    windows = app.windows()
    if len(windows) != 1 or windows[0].handle != handle:
        msg = (
            "Close existing Capstone dialogs/menus before this workflow: "
            + ", ".join(f"{w.handle}: {w.title}" for w in windows)
        )
        raise AutomationError(msg)
    return path, windows[0].title, windows[0].process_id


def _artifact(
    app: Capstone, handle: int, path: Path, before: str,
    kind: Literal["cap", "csv"],
) -> FileArtifact:
    size = path.stat().st_size
    if size > MAX_OUTPUT_BYTES:
        msg = "Output was created but exceeds the 64 MiB extraction limit."
        raise AutomationError(msg)
    after = next(w.title for w in app.windows() if w.handle == handle)
    return FileArtifact(
        path=str(path), format=kind, size_bytes=size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        document_title_before=before, document_title_after=after,
        precision="native-cache" if kind == "cap" else "capstone-export",
    )


def save_experiment(
    app: Capstone, handle: int, destination: str, *, allow_foreground: bool = True,
) -> FileArtifact:
    """Save As to a new explicit path and verify the resulting Capstone archive."""
    path, before, pid = _prepare(
        app, handle, destination, ".cap", allow_foreground=allow_foreground,
    )
    with WindowEvents(pid) as events, FileEvents(path.parent, events.changes) as files:
        previous = _open_command(app, events, handle, "mActionSaveAs")
        dialog = _file_dialog(app, events, previous)
        _save_dialog(app, files, dialog, path, {handle})
    _ = read_cap_configuration(path)
    return _artifact(app, handle, path, before, "cap")


def export_data(
    app: Capstone, handle: int, destination: str, *, allow_foreground: bool = True,
) -> FileArtifact:
    """Select all data and export by index as CSV without saving the .cap document."""
    path, before, pid = _prepare(
        app, handle, destination, ".csv", allow_foreground=allow_foreground,
    )
    with WindowEvents(pid) as events, FileEvents(path.parent, events.changes) as files:
        previous = _open_command(app, events, handle, "mActionExportData")
        dialog = events.changes.until(
            lambda: _new_snapshot(
                app, previous,
                lambda s: s.controls[0].automation_id == "DataExportDialog",
                depth=1,
            ),
            TRANSITION_SECONDS,
        )
        export_handle = dialog.window.handle
        _choose_export_option(
            app, events, export_handle, "Export Format", "Comma separated values",
        )
        _choose_export_option(
            app, events, export_handle, "Alignment Options", "Align by Index",
        )
        select = _named_button(app, export_handle, "Select All")
        _ = app.act(select.ref, Action.INVOKE)
        export = _named_button(app, export_handle, "Export to file...")
        previous = {w.handle for w in app.windows()}
        _ = app.act(export.ref, Action.INVOKE)
        file_dialog = _file_dialog(app, events, previous)
        _save_dialog(
            app, files, file_dialog, path, {handle, export_handle},
        )
        close = _named_button(app, export_handle, "Close")
        _ = app.act(close.ref, Action.INVOKE)
        _ = events.changes.until(
            lambda: True if all(
                w.handle != export_handle for w in app.windows()
            ) else None,
            TRANSITION_SECONDS,
        )
    return _artifact(app, handle, path, before, "csv")

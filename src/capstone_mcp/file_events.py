# Copyright 2026 Capstone MCP contributors.
"""Native file-change signals and exclusive-read completion checks."""

from __future__ import annotations

from threading import Thread
from typing import TYPE_CHECKING, Final, Self

import win32event
import win32file

from capstone_mcp.desktop import AutomationError

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType

    from win32job import Handle

    from capstone_mcp.ui_events import StateChanges

FILE_CHANGE_FLAGS: Final = 0x00000001 | 0x00000008 | 0x00000010
GENERIC_READ: Final = 0x80000000
OPEN_EXISTING: Final = 3
FILE_ATTRIBUTE_NORMAL: Final = 0x80
FILE_SHARE_READ: Final = 1
NOT_READY_ERRORS: Final = {2, 3, 32, 33}


def file_is_closed(path: Path) -> bool:
    """Require a nonempty file with no active writer; other readers may remain."""
    try:
        handle = win32file.CreateFile(
            str(path), GENERIC_READ, FILE_SHARE_READ, None, OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL, None,
        )
    except win32file.error as error:
        if error.winerror in NOT_READY_ERRORS:
            return False
        raise
    try:
        return path.stat().st_size > 0
    finally:
        handle.Close()


class FileEvents:
    """Wake state predicates when the target directory changes, without polling."""

    def __init__(self, directory: Path, changes: StateChanges) -> None:
        """Register before the native save/export input is delivered."""
        self.changes: StateChanges = changes
        self.change_handle: Handle = win32file.FindFirstChangeNotification(
            str(directory), 0, FILE_CHANGE_FLAGS,
        )
        self.stop_handle: Handle = win32event.CreateEvent(None, 1, 0, None)
        self.thread: Thread = Thread(target=self._watch, daemon=True)
        self.error: str | None = None

    def __enter__(self) -> Self:
        """Start the receiver; the OS subscription already exists."""
        self.thread.start()
        return self

    def __exit__(
        self, _kind: type[BaseException] | None,
        _error: BaseException | None, _traceback: TracebackType | None,
    ) -> None:
        """Wake and close the receiver without an unbounded join."""
        win32event.SetEvent(self.stop_handle)
        self.thread.join(2)
        if self.thread.is_alive():
            msg = "File notification receiver did not stop."
            raise AutomationError(msg)
        win32file.FindCloseChangeNotification(self.change_handle)
        self.stop_handle.Close()

    def _watch(self) -> None:
        try:
            while True:
                event = win32event.WaitForMultipleObjects(
                    [self.stop_handle, self.change_handle], 0, win32event.INFINITE,
                )
                if event == win32event.WAIT_OBJECT_0:
                    return
                win32file.FindNextChangeNotification(self.change_handle)
                self.changes.notify()
        except (win32event.error, win32file.error) as error:
            self.error = str(error)
            self.changes.notify()

    def ready(self, path: Path) -> bool:
        """Surface watcher failures instead of silently waiting on a dead receiver."""
        if self.error is not None:
            raise AutomationError(self.error)
        return file_is_closed(path)

from collections.abc import Sequence

from win32job import Handle

class error(Exception):
    winerror: int

INFINITE: int
WAIT_OBJECT_0: int

def CreateEvent(
    security: None, manual_reset: int, initial_state: int, name: None,
) -> Handle: ...
def SetEvent(handle: Handle) -> None: ...
def WaitForMultipleObjects(
    handles: Sequence[Handle], wait_all: int, timeout: int,
) -> int: ...

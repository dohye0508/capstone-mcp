from typing import TypedDict

class Handle:
    def Close(self) -> None: ...

class BasicLimits(TypedDict):
    LimitFlags: int

class ExtendedLimits(TypedDict):
    BasicLimitInformation: BasicLimits

JobObjectExtendedLimitInformation: int
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: int
JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK: int

def CreateJobObject(attributes: None, name: str) -> Handle: ...
def QueryInformationJobObject(handle: Handle, info_class: int) -> ExtendedLimits: ...
def SetInformationJobObject(
    handle: Handle, info_class: int, information: ExtendedLimits,
) -> None: ...
def AssignProcessToJobObject(job: Handle, process: Handle) -> None: ...

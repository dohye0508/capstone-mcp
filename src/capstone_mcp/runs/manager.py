# Copyright 2026 Capstone MCP contributors.
"""Consolidated, deep Run Management engine for Capstone Data Summary."""

import contextlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import ValidationError

from capstone_mcp.analysis import (
    MIN_COMPARISON_RUNS,
    AnalysisError,
    FitInput,
    RunComparison,
    RunSamples,
    compare_runs,
    linear_fit,
)
from capstone_mcp.capfile_models import CapDataSet, CapFile
from capstone_mcp.capfiles import CapFileError, read_cap_file
from capstone_mcp.desktop import AutomationError, Capstone
from capstone_mcp.displays import (
    click_control,
    find_display_containers,
    is_within_bounds,
)
from capstone_mcp.file_workflows import FileArtifact
from capstone_mcp.models import Control
from capstone_mcp.runs.models import (
    CapturedFit,
    CapturedRun,
    CaptureError,
    CapturePlan,
    CaptureResult,
    DatasetChange,
    DatasetIdentity,
    DeleteRunRequest,
    DeleteRunResult,
    RenameRunRequest,
    RenameRunResult,
    RunAction,
    RunRequest,
    RunResult,
    SetRunVisibilityRequest,
    SetRunVisibilityResult,
    SourceFit,
)

RUN_NAME_PATTERN: Final = re.compile(r"run\s*#?\s*\d+", re.IGNORECASE)


# ---------------------------------------------------------------------------
# 1. Run Renaming
# ---------------------------------------------------------------------------


def _rename_via_inline_editor(
    app: Capstone,
    handle: int,
    node: Any,  # noqa: ANN401
    new_name: str,
) -> None:
    """Fallback inline renaming via F2 keystrokes."""
    node.set_focus()
    app.keys(handle, "{F2}", allow_foreground=True)
    app.keys(handle, "^a", allow_foreground=True)
    app.type_text(new_name)
    app.keys(handle, "{ENTER}", allow_foreground=True)


def rename_run(app: Capstone, request: RenameRunRequest) -> RenameRunResult:
    """Find the target run in Data Summary and rename it reliably."""
    if not request.new_name.strip() or any(c in request.new_name for c in "\r\n"):
        msg = "new_name must not be empty."
        raise AutomationError(msg)

    # 1. Take snapshot to locate the target run item
    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    if snapshot.truncated:
        msg = "Run mutation requires a complete snapshot."
        raise AutomationError(msg)
    matches = [
        control
        for control in snapshot.controls
        if control.visible
        and control.control_type == "TreeItem"
        and control.name.strip() == request.old_name.strip()
    ]
    if not matches:
        msg = f"Run item with name '{request.old_name}' not found in Data Summary."
        raise AutomationError(msg)
    if len(matches) != 1:
        msg = "Run name is ambiguous; refusing to rename multiple matching items."
        raise AutomationError(msg)
    target_control = matches[0]
    if request.new_name != request.old_name and any(
        c.visible
        and c.control_type == "TreeItem"
        and c.name.strip() == request.new_name.strip()
        for c in snapshot.controls
    ):
        msg = "The requested new run name already exists."
        raise AutomationError(msg)

    node = app.control(target_control.ref)

    # 2. Try ValuePattern direct set
    value_set = False
    with contextlib.suppress(AttributeError, RuntimeError):
        if hasattr(node, "iface_value") and node.iface_value:
            node.iface_value.SetValue(request.new_name)
            value_set = True

    if not value_set:
        if not request.allow_foreground:
            msg = "Renaming via inline editor requires allow_foreground=true."
            raise AutomationError(msg)
        _rename_via_inline_editor(app, request.handle, node, request.new_name)

    # 3. Verify via fresh snapshot
    verification_snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    renamed = any(
        c.visible
        and c.control_type == "TreeItem"
        and c.name.strip() == request.new_name.strip()
        for c in verification_snapshot.controls
    )

    detail = (
        f"Run successfully renamed from '{request.old_name}' to '{request.new_name}'."
        if renamed
        else f"Rename issued, but '{request.new_name}' was not confirmed in tree."
    )

    return RenameRunResult(
        old_name=request.old_name,
        new_name=request.new_name,
        verified=renamed,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# 2. Run Deletion & Modal Auto-Dismissal
# ---------------------------------------------------------------------------


def _find_run_items(controls: list[Control]) -> list[Control]:
    """Find all Run items in Data Summary tree."""
    return [
        ctrl
        for ctrl in controls
        if (
            ctrl.visible
            and ctrl.control_type == "TreeItem"
            and RUN_NAME_PATTERN.search(ctrl.name)
        )
    ]


def delete_run(app: Capstone, request: DeleteRunRequest) -> DeleteRunResult:
    """Delete a unique named run and report only observed removal."""
    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    if snapshot.truncated:
        msg = "Run mutation requires a complete snapshot."
        raise AutomationError(msg)
    name = request.run_name.strip()
    if name.casefold() in ("last_run", "last", "latest"):
        run_items = _find_run_items(snapshot.controls)
        if not run_items:
            msg = "No runs found to delete in Data Summary."
            raise AutomationError(msg)
        msg = "Latest run identity is unverified; provide an explicit run name."
        raise AutomationError(msg)
    matches = [
        c
        for c in snapshot.controls
        if c.visible
        and c.control_type == "TreeItem"
        and c.name.strip().casefold() == name.casefold()
    ]
    if len(matches) != 1:
        msg = f"Run '{name}' not found uniquely in Data Summary."
        raise AutomationError(msg)
    target = matches[0]
    click_control(
        app, request.handle, target, allow_foreground=request.allow_foreground,
    )
    app.keys(request.handle, "{DELETE}", allow_foreground=request.allow_foreground)
    fresh = app.snapshot(request.handle, depth=16, limit=10_000)
    removed = not fresh.truncated and not any(
        c.control_type == "TreeItem" and c.name.strip().casefold() == name.casefold()
        for c in fresh.controls
    )
    if removed:
        try:
            app.require_input_ready(request.handle)
        except AutomationError:
            removed = False
    return DeleteRunResult(
        deleted_run=target.name,
        verified=removed,
        detail=(
            f"Run '{target.name}' removal observed."
            if removed
            else "Deletion requested but not verified; inspect any confirmation dialog."
        ),
    )


# ---------------------------------------------------------------------------
# 3. Run Visibility Toggling
# ---------------------------------------------------------------------------


def _match_display_control(controls: list[Control], display_name: str) -> Control:
    """Resolve an exact container name; never choose an overlapping label."""
    matches = [c for c in controls if c.visible
               and c.control_type in ("Custom", "Pane", "Group", "Table", "DataGrid")
               and c.name.strip().casefold() == display_name.strip().casefold()]
    if len(matches) == 1:
        return matches[0]
    msg = f"Target display '{display_name}' not found uniquely in active window."
    raise AutomationError(msg)


def _find_display_containers(controls: list[Control]) -> list[Control]:
    """Find all graph or table display containers in the window snapshot."""
    return find_display_containers(controls, ("graph", "table"))


def _is_within_bounds(inner: Control, outer: Control) -> bool:
    """Check if inner control rectangle is contained within outer control bounds."""
    return is_within_bounds(inner, outer)


def _find_run_controls(
    controls: list[Control],
    target_containers: list[Control] | None = None,
    requested_runs: list[str] | None = None,
) -> list[Control]:
    """Find controls representing runs (checkboxes, tree items, list items)."""
    candidates: list[Control] = []
    for ctrl in controls:
        if not ctrl.visible:
            continue
        if ctrl.control_type not in (
            "CheckBox",
            "TreeItem",
            "ListItem",
            "MenuItem",
            "Button",
            "RadioButton",
        ):
            continue
        if not (
            RUN_NAME_PATTERN.fullmatch(ctrl.name.strip())
            or any(
                ctrl.name.strip().casefold() == name.strip().casefold()
                for name in (requested_runs or [])
            )
        ):
            continue

        if target_containers is None or any(
            _is_within_bounds(ctrl, c) for c in target_containers
        ):
            candidates.append(ctrl)
    return candidates


def _matches_run_name(ctrl: Control, target_run: str) -> bool:
    """Match a control against a target run identifier."""
    cname = ctrl.name.strip().lower()
    tname = target_run.strip().lower()
    if cname == tname:
        return True
    if not RUN_NAME_PATTERN.fullmatch(cname):
        return False
    if not (RUN_NAME_PATTERN.fullmatch(tname) or tname.isdecimal()):
        return False
    return re.findall(r"\d+", cname) == re.findall(r"\d+", tname)


def _get_control_visibility_state(app: Capstone, ctrl: Control) -> bool | None:
    """Read an explicit binary Toggle state; absence is unknown."""
    with contextlib.suppress(AttributeError, RuntimeError):
        node = app.control(ctrl.ref)
        toggle = node.iface_toggle
        for attribute in ("CurrentToggleState", "ToggleState"):
            value = getattr(toggle, attribute, None)
            if type(value) is int and value in (0, 1):
                return value == 1
    return None


def _set_control_visibility_state(
    app: Capstone,
    handle: int,
    ctrl: Control,
    visible: bool,  # noqa: FBT001
) -> None:
    """Change only controls with an observed binary toggle state."""
    del handle
    current = _get_control_visibility_state(app, ctrl)
    if current is None:
        msg = f"Run visibility state is unknown for '{ctrl.name}'."
        raise AutomationError(msg)
    if current != visible:
        app.control(ctrl.ref).iface_toggle.Toggle()


def _resolve_targets(
    controls: list[Control],
    target_displays: list[str] | None,
) -> tuple[list[Control] | None, list[str]]:
    """Determine target display controls and display name labels."""
    if target_displays:
        matched: list[Control] = []
        labels: list[str] = []
        for name in target_displays:
            ctrl = _match_display_control(controls, name)
            matched.append(ctrl)
            labels.append(ctrl.name.strip())
        return matched, labels

    found = _find_display_containers(controls)
    if found:
        return None, [d.name.strip() for d in found]
    return None, ["All Displays"]


def _visibility_controls(
    app: Capstone,
    request: SetRunVisibilityRequest,
) -> tuple[list[Control], list[str]]:
    snapshot = app.snapshot(request.handle, depth=16, limit=10_000)
    if snapshot.truncated:
        msg = "Run visibility requires a complete snapshot."
        raise AutomationError(msg)
    containers, names = _resolve_targets(snapshot.controls, request.target_displays)
    return _find_run_controls(snapshot.controls, containers, request.runs), names


def set_run_visibility(
    app: Capstone,
    request: SetRunVisibilityRequest,
) -> SetRunVisibilityResult:
    """Set run toggles using fresh references and observed postconditions."""
    if not request.runs:
        msg = "runs must not be empty."
        raise AutomationError(msg)
    if not request.allow_foreground:
        msg = "Run visibility operation requires allow_foreground=true."
        raise AutomationError(msg)
    controls, display_names = _visibility_controls(app, request)
    for name in request.runs:
        matches = [c for c in controls if _matches_run_name(c, name)]
        if len(matches) != 1:
            msg = f"Unique run visibility control for '{name}' not found."
            raise AutomationError(msg)
        # Check every requested state before mutating any of them.
        if any(_get_control_visibility_state(app, c) is None for c in matches):
            msg = f"Run visibility state is unknown for '{name}'."
            raise AutomationError(msg)
    for name in request.runs:
        current, _ = _visibility_controls(app, request)
        matches = [c for c in current if _matches_run_name(c, name)]
        if len(matches) != 1:
            msg = f"Run '{name}' is ambiguous; target one display explicitly."
            raise AutomationError(msg)
        _set_control_visibility_state(app, request.handle, matches[0], request.visible)
    current, display_names = _visibility_controls(app, request)
    verified = all(
        bool(matches := [c for c in current if _matches_run_name(c, name)])
        and all(
            _get_control_visibility_state(app, c) == request.visible for c in matches
        )
        for name in request.runs
    )
    visible_names = sorted(
        {
            c.name.strip()
            for c in current
            if _get_control_visibility_state(app, c) is True
        },
    )
    return SetRunVisibilityResult(
        visible_runs=visible_names,
        target_displays=display_names,
        verified=verified,
        detail=(
            "Requested run visibility observed."
            if verified
            else "Run visibility request was not confirmed by the current controls."
        ),
    )


# ---------------------------------------------------------------------------
# 4. Run Capture Session
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Delta:
    provenance: DatasetChange
    dataset: CapDataSet


def _indexed(parsed: CapFile) -> dict[tuple[str, str], CapDataSet]:
    result: dict[tuple[str, str], CapDataSet] = {}
    for dataset in parsed.datasets:
        identifier = dataset.data_set_id
        source = dataset.source_euid
        if identifier is None or source is None or (source, identifier) in result:
            msg = "Snapshot dataset IDs are missing or ambiguous."
            raise CaptureError(msg)
        result[source, identifier] = dataset
    return result


def _deltas(
    before: CapFile,
    after: CapFile,
) -> tuple[list[_Delta], list[DatasetIdentity]]:
    old = _indexed(before)
    current = _indexed(after)
    changes: list[_Delta] = []
    for index, dataset in enumerate(after.datasets):
        identifier = dataset.data_set_id
        source = dataset.source_euid
        if identifier is None or source is None:
            msg = "Dataset has no identity."
            raise CaptureError(msg)
        previous = old.get((source, identifier))
        count = len(dataset.raw_values)
        start: int | None = 0
        kind: Literal["created", "appended", "replaced"] = "created"
        if previous is not None:
            same_metadata = (
                dataset.source_euid == previous.source_euid
                and dataset.unit_id == previous.unit_id
                and dataset.independent_kind == previous.independent_kind
            )
            old_values = (
                previous.numeric_values
                if previous.numeric_values is not None
                else previous.raw_values
            )
            values = (
                dataset.numeric_values
                if dataset.numeric_values is not None
                else dataset.raw_values
            )
            if (
                same_metadata
                and values == old_values
                and dataset.independent_values == previous.independent_values
            ):
                continue
            old_count = len(previous.raw_values)
            appended = (
                same_metadata
                and count > old_count
                and values[:old_count] == old_values
                and dataset.independent_values[:old_count]
                == previous.independent_values
            )
            start = old_count if appended else None
            kind = "appended" if appended else "replaced"
        provenance = DatasetChange(
            dataset_index=index,
            dataset_id=identifier,
            source_euid=dataset.source_euid,
            source_name=dataset.source_name,
            unit_id=dataset.unit_id,
            kind=kind,
            sample_start=start,
            sample_count=count,
            new_sample_count=None if start is None else count - start,
        )
        changes.append(_Delta(provenance=provenance, dataset=dataset))
    removed = [
        DatasetIdentity(euid=source, name=str(identifier))
        for source, identifier in sorted(old.keys() - current.keys())
    ]
    return changes, removed


def _select(changes: list[_Delta], source: str) -> _Delta:
    matches = [
        change
        for change in changes
        if change.provenance.source_euid == source
        and change.provenance.new_sample_count
    ]
    if len(matches) != 1:
        msg = f"Source {source!r} has no unique newly captured dataset."
        raise CaptureError(msg)
    return matches[0]


def _values(change: _Delta) -> list[float]:
    start = change.provenance.sample_start
    values = change.dataset.numeric_values
    if start is None or values is None or any(v is None for v in values[start:]):
        msg = "Captured samples are replaced, nonnumeric, or missing."
        raise CaptureError(msg)
    return [float(value) for value in values[start:] if value is not None]


def _fit(
    changes: list[_Delta],
    sources: SourceFit,
    ordinal: int,
) -> tuple[CapturedFit, RunSamples]:
    x = _select(changes, sources.x_source_euid)
    y = _select(changes, sources.y_source_euid)
    start_x = 0 if x.provenance.sample_start is None else x.provenance.sample_start
    start_y = 0 if y.provenance.sample_start is None else y.provenance.sample_start
    x_coords = (
        []
        if x.dataset.independent_values is None
        else x.dataset.independent_values[start_x:]
    )
    y_coords = (
        []
        if y.dataset.independent_values is None
        else y.dataset.independent_values[start_y:]
    )
    if (
        x.dataset.independent_kind != y.dataset.independent_kind
        or x_coords != y_coords
        or any(value is None or not value.is_finite() for value in x_coords)
    ):
        msg = "Captured x/y samples are not paired at identical valid coordinates."
        raise CaptureError(msg)
    samples = FitInput(x=_values(x), y=_values(y))
    fit = CapturedFit(
        x=x.provenance,
        y=y.provenance,
        result=linear_fit(samples),
    )
    return fit, RunSamples(name=f"run {ordinal}", values=samples.y)


class CaptureSession:
    """Save snapshots and analyze each cycle after its confirmed stop."""

    def __init__(
        self,
        plan: CapturePlan,
        save: Callable[[str], FileArtifact],
    ) -> None:
        """Initialize capture session with output directory plan and saver."""
        self.plan: CapturePlan = plan
        self.directory: Path = Path(plan.directory).resolve()
        self.save: Callable[[str], FileArtifact] = save
        self.baseline: FileArtifact | None = None
        self.previous: CapFile | None = None
        self.runs: list[CapturedRun] = []
        self.comparisons: list[RunSamples] = []
        self.comparison_unit: int | None = None

    def begin(self) -> None:
        """Save the baseline before measuring; never reuse a nonempty directory."""
        if self.directory.exists() and (
            not self.directory.is_dir() or any(self.directory.iterdir())
        ):
            msg = "Capture needs a new or empty output directory."
            raise CaptureError(msg)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.baseline = self.save(str(self.directory / "baseline.cap"))
        self.previous = read_cap_file(self.baseline.path)
        _ = _indexed(self.previous)
        if self.plan.fit is not None:
            required = {self.plan.fit.x_source_euid, self.plan.fit.y_source_euid}
            known = {ds.source_euid for ds in self.previous.datasets}
            if not required.issubset(known):
                missing = sorted(required - known)
                msg = f"Fit sources {missing} are missing from baseline."
                raise CaptureError(msg)

    def record(self, ordinal: int, *, interrupted: bool = False) -> None:
        """Save one cycle, identify changed datasets, and optionally fit them."""
        if self.previous is None:
            msg = "Record requires a captured baseline."
            raise CaptureError(msg)
        artifact = self.save(str(self.directory / f"run-{ordinal:03d}.cap"))
        parsed: CapFile | None = None
        changes: list[_Delta] = []
        removed: list[DatasetIdentity] = []
        fit: CapturedFit | None = None
        error: str | None = None
        validated_snapshot = False
        try:
            parsed = read_cap_file(artifact.path)
            changes, removed = _deltas(self.previous, parsed)
            validated_snapshot = True
            if self.plan.fit is not None and not interrupted:
                fit, samples = _fit(changes, self.plan.fit, ordinal)
                unit = fit.y.unit_id
                if unit is None or (
                    self.comparison_unit is not None and unit != self.comparison_unit
                ):
                    msg = "Captured comparison requires one consistent declared y unit."
                    raise CaptureError(msg)
                self.comparison_unit = unit
                self.comparisons.append(samples)
        except (AnalysisError, ValidationError, CapFileError) as failure:
            error = str(failure)
            raise
        finally:
            self.runs.append(
                CapturedRun(
                    ordinal=ordinal,
                    interrupted=interrupted,
                    artifact=artifact,
                    datasets=[change.provenance for change in changes],
                    removed_datasets=removed,
                    fit=fit,
                    analysis_error=error,
                ),
            )
            if validated_snapshot:
                self.previous = parsed

    record_cycle = record

    def result(self) -> CaptureResult:
        """Collate the saved artifacts and comparative slope/intercept trends."""
        comparison: list[RunComparison] = []
        comparison_error: str | None = None
        if (
            len(self.comparisons) >= MIN_COMPARISON_RUNS
            and self.comparison_unit is not None
        ):
            try:
                comparison = compare_runs(self.comparisons)
            except AnalysisError as error:
                comparison_error = str(error)
        return CaptureResult(
            baseline=self.baseline,
            runs=self.runs,
            comparison=comparison,
            comparison_error=comparison_error,
        )


# ---------------------------------------------------------------------------
# 5. Unified RunManager & Seam
# ---------------------------------------------------------------------------


class RunManager:
    """Deep module managing all run lifecycles and interactions."""

    def __init__(self, app: Capstone) -> None:
        """Initialize run manager bound to a Capstone automation client."""
        self.app = app

    def rename(self, request: RenameRunRequest) -> RenameRunResult:
        """Rename an experimental run in Data Summary."""
        return rename_run(self.app, request)

    def delete(self, request: DeleteRunRequest) -> DeleteRunResult:
        """Delete a named run and verify its observed removal."""
        return delete_run(self.app, request)

    def set_visibility(
        self,
        request: SetRunVisibilityRequest,
    ) -> SetRunVisibilityResult:
        """Toggle or assign visibility for runs across displays."""
        return set_run_visibility(self.app, request)

    def manage(self, request: RunRequest) -> RunResult:
        """Single unified entry point for all run operations."""
        if request.action == RunAction.RENAME:
            if request.rename is None:
                msg = "rename request must be provided for RENAME action."
                raise AutomationError(msg)
            return RunResult(action=request.action, rename=self.rename(request.rename))

        if request.action == RunAction.DELETE:
            if request.delete is None:
                msg = "delete request must be provided for DELETE action."
                raise AutomationError(msg)
            return RunResult(action=request.action, delete=self.delete(request.delete))

        if request.action == RunAction.SET_VISIBILITY:
            if request.visibility is None:
                msg = "visibility request must be provided for SET_VISIBILITY action."
                raise AutomationError(msg)
            return RunResult(
                action=request.action,
                visibility=self.set_visibility(request.visibility),
            )

        msg = f"Unsupported RunAction: {request.action}"
        raise AutomationError(msg)


def manage_run(app: Capstone, request: RunRequest) -> RunResult:
    """Functional convenience wrapper for the unified run management seam."""
    return RunManager(app).manage(request)

# Copyright 2026 Capstone MCP contributors.
"""Saved snapshots and explicit dataset deltas for individual acquisition cycles."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, ValidationError, model_validator

from capstone_mcp.analysis import (
    MIN_COMPARISON_RUNS,
    AnalysisError,
    FitInput,
    LinearFit,
    RunComparison,
    RunSamples,
    compare_runs,
    linear_fit,
)
from capstone_mcp.capfile_models import CapDataSet, CapFile
from capstone_mcp.capfiles import CapFileError, read_cap_file
from capstone_mcp.file_workflows import FileArtifact
from capstone_mcp.models import Model


class CaptureError(AnalysisError):
    """A saved cycle cannot be attributed or analyzed without guessing."""


class SourceFit(Model):
    """Explicit measurement source IDs remain stable while run dataset IDs change."""

    x_source_euid: str = Field(min_length=1)
    y_source_euid: str = Field(min_length=1)

    @model_validator(mode="after")
    def distinct_sources(self) -> Self:
        """Reject a self-fit before starting acquisition."""
        if self.x_source_euid == self.y_source_euid:
            msg = "Select different x and y measurement sources."
            raise ValueError(msg)
        return self


class CapturePlan(Model):
    """Use an empty output directory; optionally fit every captured cycle."""

    directory: str = Field(min_length=1)
    fit: SourceFit | None = None


class DatasetChange(Model):
    """A saved dataset change; replacements have no claimed new-sample slice."""

    dataset_index: int
    dataset_id: str
    source_euid: str | None
    source_name: str | None
    unit_id: int | None
    kind: Literal["created", "appended", "replaced"]
    sample_start: int | None
    sample_count: int
    new_sample_count: int | None


class CapturedFit(Model):
    """A fit of only the newly attributed samples, not a previous run's data."""

    x: DatasetChange
    y: DatasetChange
    result: LinearFit


class DatasetIdentity(Model):
    """Dataset identity is scoped to its measurement source."""

    source_euid: str
    dataset_id: str


class CapturedRun(Model):
    """One stopped cycle's saved artifact, changes, and optional analysis."""

    ordinal: int
    interrupted: bool
    artifact: FileArtifact
    datasets: list[DatasetChange]
    removed_datasets: list[DatasetIdentity]
    fit: CapturedFit | None
    analysis_error: str | None


class CaptureResult(Model):
    """Preserve completed artifacts even if a later measurement or analysis fails."""

    baseline: FileArtifact | None
    runs: list[CapturedRun]
    comparison: list[RunComparison]
    comparison_error: str | None


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
    before: CapFile, after: CapFile,
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
                if previous.numeric_values is not None else previous.raw_values
            )
            values = (
                dataset.numeric_values
                if dataset.numeric_values is not None else dataset.raw_values
            )
            if (
                same_metadata and values == old_values
                and dataset.independent_values == previous.independent_values
            ):
                continue
            old_count = len(previous.raw_values)
            appended = (
                same_metadata and count > old_count
                and values[:old_count] == old_values
                and dataset.independent_values[:old_count]
                == previous.independent_values
            )
            start = old_count if appended else None
            kind = "appended" if appended else "replaced"
        provenance = DatasetChange(
            dataset_index=index, dataset_id=identifier,
            source_euid=dataset.source_euid, source_name=dataset.source_name,
            unit_id=dataset.unit_id, kind=kind, sample_start=start,
            sample_count=count,
            new_sample_count=None if start is None else count - start,
        )
        changes.append(_Delta(provenance=provenance, dataset=dataset))
    removed = [
        DatasetIdentity(source_euid=source, dataset_id=identifier)
        for source, identifier in sorted(old.keys() - current.keys())
    ]
    return changes, removed


def _select(changes: list[_Delta], source: str) -> _Delta:
    matches = [
        change for change in changes
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
    changes: list[_Delta], sources: SourceFit, ordinal: int,
) -> tuple[CapturedFit, RunSamples]:
    x = _select(changes, sources.x_source_euid)
    y = _select(changes, sources.y_source_euid)
    x_coordinates = x.dataset.independent_values[x.provenance.sample_start:]
    y_coordinates = y.dataset.independent_values[y.provenance.sample_start:]
    if (
        x.dataset.independent_kind != y.dataset.independent_kind
        or x_coordinates != y_coordinates
        or any(value is None or not value.is_finite() for value in x_coordinates)
    ):
        msg = "Captured x/y samples are not paired at identical valid coordinates."
        raise CaptureError(msg)
    samples = FitInput(x=_values(x), y=_values(y))
    fit = CapturedFit(
        x=x.provenance, y=y.provenance, result=linear_fit(samples),
    )
    return fit, RunSamples(name=f"run {ordinal}", values=samples.y)


class CaptureSession:
    """Save snapshots and analyze each cycle after its confirmed stop."""

    def __init__(
        self, plan: CapturePlan, save: Callable[[str], FileArtifact],
    ) -> None:
        """Bind to one output directory and one verified native save operation."""
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
            required = {
                self.plan.fit.x_source_euid, self.plan.fit.y_source_euid,
            }
            if not required.issubset({s.euid for s in self.previous.data_sources}):
                msg = "Requested fit sources are absent from the baseline experiment."
                raise CaptureError(msg)

    def record(self, ordinal: int, *, interrupted: bool = False) -> None:
        """Save the stopped run and analyze only changes since the prior snapshot."""
        if self.previous is None:
            msg = "Capture baseline has not been saved."
            raise CaptureError(msg)
        artifact = self.save(str(self.directory / f"run-{ordinal:03d}.cap"))
        parsed: CapFile | None = None
        changes: list[_Delta] = []
        removed: list[DatasetIdentity] = []
        fit: CapturedFit | None = None
        error: str | None = None
        try:
            parsed = read_cap_file(artifact.path)
            changes, removed = _deltas(self.previous, parsed)
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
            self.runs.append(CapturedRun(
                ordinal=ordinal, interrupted=interrupted, artifact=artifact,
                datasets=[change.provenance for change in changes],
                removed_datasets=removed, fit=fit, analysis_error=error,
            ))
            if parsed is not None:
                self.previous = parsed

    def result(self) -> CaptureResult:
        """Return existing files and cross-run statistics without re-reading the app."""
        comparison: list[RunComparison] = []
        error: str | None = None
        try:
            if len(self.comparisons) >= MIN_COMPARISON_RUNS:
                comparison = compare_runs(self.comparisons)
        except AnalysisError as failure:
            error = str(failure)
        return CaptureResult(
            baseline=self.baseline, runs=list(self.runs), comparison=comparison,
            comparison_error=error,
        )

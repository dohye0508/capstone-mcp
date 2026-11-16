# Copyright 2026 Capstone MCP contributors.
"""Saved-experiment selection, provenance, and analysis coverage."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from pydantic import ValidationError

from capstone_mcp.data_sources import get_experiment_series
from capstone_mcp.experiment_analysis import (
    CapDatasetSelection,
    CapLinearFitRequest,
    CapRunComparisonRequest,
    ExperimentAnalysisError,
    compare_cap_datasets,
    fit_cap_datasets,
)
from capstone_mcp.reports import generate_report
from capstone_mcp.server import capstone_generate_lab_report

EXAMPLE: Final = (
    Path("C:/Program Files/PASCO scientific/Capstone")
    / "Resources"
    / "Templates"
    / "QuickStart"
    / "Conservation of Momentum.cap"
)


@dataclass(frozen=True)
class _DatasetSpec:
    dataset_id: str
    source_euid: str
    source_name: str
    values: list[float | str | None]
    unit_id: int | None = 2048
    value_kind: Literal["numeric", "text"] = "numeric"
    numeric_cache: bool = False
    independent_kind: Literal["index", "interval"] = "index"
    interval_start: float = 0
    interval_step: float = 1


def _text_payload(values: list[float | str | None]) -> bytes:
    payload = bytearray()
    for value in values:
        assert value is not None
        encoded = str(value).encode("utf-16-le")
        payload.extend(struct.pack("<II", 2, len(encoded)))
        payload.extend(encoded)
    return bytes(payload)


def _numeric_payload(values: list[float | str | None]) -> bytes:
    payload = bytearray()
    for value in values:
        if value is None:
            payload.extend(struct.pack("<Id", 0, 0))
        else:
            payload.extend(struct.pack("<Id", 1, float(value)))
    return bytes(payload)


def _write_cap(
    path: Path, specs: list[_DatasetSpec], *, runs: dict[str, int] | None = None,
) -> None:
    sources: list[str] = []
    payloads: list[tuple[str, bytes]] = []
    for index, spec in enumerate(specs):
        count = len(spec.values)
        payload_name = f"data/values-{index}.tmp"
        storage_type = 0 if spec.numeric_cache else 7
        evaluated_type = "2" if spec.value_kind == "text" else "1"
        unit_attribute = (
            "" if spec.unit_id is None else f' DefaultUnit="{spec.unit_id}"'
        )
        offset_attribute = ' DataOffsetValue="0"' if spec.numeric_cache else ""
        if spec.independent_kind == "interval":
            independent = (
                f'<IndependentStorageElement StorageType="1" '
                f'CacheDataCount="{count}" '
                f'IntervalCacheStartValue="{spec.interval_start}" '
                f'IntervalCacheInterval="{spec.interval_step}" />'
            )
        else:
            independent = (
                f'<IndependentStorageElement StorageType="4" '
                f'CacheDataCount="{count}" />'
            )
        sources.append(
            f"""
    <DataSource EUID="{spec.source_euid}" LongName="{spec.source_name}"
                UserDataEvaluatedType="{evaluated_type}"{unit_attribute}>
      <DataSet DataSetID="{spec.dataset_id}" Name="Set {index}">
        <DataSegmentElement>
          <DependentStorageElement StorageType="{storage_type}"
              DataCacheDataSize="{count}" FileName="{payload_name}"
              {offset_attribute} />
          {independent}
        </DataSegmentElement>
      </DataSet>
    </DataSource>
""",
        )
        payload = (
            _numeric_payload(spec.values)
            if spec.numeric_cache
            else _text_payload(spec.values)
        )
        payloads.append((payload_name, payload))

    run_labels = "".join(
        f'<RunParameterSet RunParameterID="{run_id}">'
        f'<ParameterValue RunNumber="{number}" /></RunParameterSet>'
        for run_id, number in (runs or {}).items()
    )
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<DSProExperiment>\n"
        "  <DataRepository>\n"
        f"{''.join(sources)}"
        f"{run_labels}"
        "  </DataRepository>\n"
        "</DSProExperiment>\n"
    ).encode()
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("main.xml", xml)
        for payload_name, payload in payloads:
            archive.writestr(payload_name, payload)


@pytest.mark.parametrize("storage", [
    (True, "index"), (True, "interval"), (False, "index"), (False, "interval"),
], ids=["binary-index", "binary-interval", "text-index", "text-interval"])
@pytest.mark.parametrize(("x", "y", "slope"), [
    (("Voltage", 1024, [1, 2, 3, 4]), ("Current", 3584, [2, 4, 6, 8]), 2),
    (("Time", 3330, [0, 1, 2, 3]), ("Velocity", 2304, [3, 2, 1, 0]), -1),
    (("Pressure", 770, [100, 110, 120, 130]), ("Volume", 1280, [8, 7, 6, 5]), -0.1),
    (
        ("Frequency", 7936, [400, 500, 600, 700]),
        ("Stopping Voltage", 1024, [0.5, 1.0, 1.5, 2.0]), 0.005,
    ),
    (("Angle", 2560, [0, 1, 2, 3]), ("Light Intensity", 5122, [1, 4, 7, 10]), 3),
], ids=["circuit", "motion", "gas", "photoelectric", "optics"])
def test_portable_archive_analysis(
    tmp_path: Path,
    storage: tuple[bool, Literal["index", "interval"]],
    x: tuple[str, int, list[int | float]],
    y: tuple[str, int, list[int | float]],
    slope: float,
) -> None:
    """Use deterministic samples to exercise the full .cap-to-report path in CI."""
    numeric_cache, axis_kind = storage
    path = tmp_path / "experiment.cap"
    _write_cap(path, [
        _DatasetSpec(
            "{run}", f"{{axis-{index}}}", name, list(values), unit_id=unit,
            numeric_cache=numeric_cache, independent_kind=axis_kind,
            interval_start=0.25, interval_step=0.5,
        )
        for index, (name, unit, values) in enumerate((x, y))
    ], runs={"{run}": 2})

    report = generate_report(str(path), run_id="Run #2", axes=(x[0], y[0]))

    assert report.metadata.run_name == "Run #2"
    assert report.raw_data_points == {x[0]: x[2], y[0]: y[2]}
    assert [summary.unit for summary in report.data_summaries] == [
        f"Capstone unit ID {x[1]}", f"Capstone unit ID {y[1]}",
    ]
    assert report.regression is not None
    assert report.regression.slope == pytest.approx(slope)
    assert report.regression.r_squared == pytest.approx(1.0)


def test_saved_series_requires_named_axes_and_exposes_independent_coordinates(
    tmp_path: Path,
) -> None:
    path = tmp_path / "series.cap"
    _write_cap(path, [_DatasetSpec(
        dataset_id="{force}", source_euid="{sensor}", source_name="Force",
        values=[3, None, 8], numeric_cache=True, independent_kind="interval",
        interval_start=0.25, interval_step=0.5,
    )])

    with pytest.raises(ValueError, match="Unknown"):
        get_experiment_series(path, "Unknown", "Force")
    series = get_experiment_series(path, "independent_coordinate", "Force")
    assert series.x.values == [0.25, 0.75, 1.25]
    assert series.x.units == ""
    assert series.y.values == [3.0, None, 8.0]
    assert series.paired_floats() == ([0.25, 1.25], [3.0, 8.0])


def test_saved_series_rejects_matching_counts_with_shifted_coordinates(
    tmp_path: Path,
) -> None:
    path = tmp_path / "shifted.cap"
    _write_cap(path, [
        _DatasetSpec("{x}", "{source-x}", "Position", [1, 2], independent_kind="interval"),
        _DatasetSpec("{y}", "{source-y}", "Force", [3, 4], independent_kind="interval", interval_start=1),
    ])

    with pytest.raises(ValueError, match="different independent coordinates"):
        get_experiment_series(path, "Position", "Force")


def test_saved_series_pairs_only_exact_shared_coordinates_of_same_run(
    tmp_path: Path,
) -> None:
    path = tmp_path / "overlap.cap"
    _write_cap(path, [
        _DatasetSpec("{run}", "{source-x}", "Angle", [1, 2, 3], independent_kind="interval"),
        _DatasetSpec("{run}", "{source-y}", "Light", [8, 9, 10], independent_kind="interval", interval_start=1),
    ], runs={"{run}": 1})

    series = get_experiment_series(path, "Angle", "Light", run_id="Run #1")

    assert series.paired_floats() == ([2.0, 3.0], [8.0, 9.0])
    assert series.run_id == "Run #1"


@pytest.mark.anyio
async def test_saved_report_preserves_requested_run_and_raw_row_positions(
    tmp_path: Path,
) -> None:
    path = tmp_path / "report.cap"
    _write_cap(path, [
        _DatasetSpec("{r1}", "{x}", "Angle", [1, None, 3], numeric_cache=True),
        _DatasetSpec("{r1}", "{y}", "Light", [2, 100, 6], numeric_cache=True),
        _DatasetSpec("{r2}", "{x}", "Angle", [4, 5], numeric_cache=True),
        _DatasetSpec("{r2}", "{y}", "Light", [40, 50], numeric_cache=True),
    ], runs={"{r1}": 1, "{r2}": 2})

    with pytest.raises(ValueError, match="multiple saved runs"):
        generate_report(str(path))
    summary = generate_report(str(path), run_id="Run #2")
    assert summary.regression is None
    assert summary.plotted_data_points == {}
    assert summary.raw_data_points["Light"] == [40.0, 50.0]

    result = await capstone_generate_lab_report(
        str(path), "photoelectric_effect", run_id="Run #1", axes=("Angle", "Light"),
        format="both",
    )
    report = result.lab_report
    assert report.metadata.run_name == "Run #1"
    assert report.raw_data_points["Angle"] == [1.0, None, 3.0]
    assert report.raw_data_points["Light"] == [2.0, 100.0, 6.0]
    assert report.regression is not None
    assert report.regression.slope == pytest.approx(2.0)
    assert report.error_analysis == []
    assert result.report_html is not None
    assert result.report_html.count("<circle ") == 2


def test_fit_saved_datasets_by_exact_id_with_provenance(
    tmp_path: Path,
) -> None:
    cap_path = tmp_path / "fit.cap"
    _write_cap(
        cap_path,
        [
            _DatasetSpec(
                dataset_id="{x}",
                source_euid="{source-x}",
                source_name="Position",
                values=[0, 1, 2, 3],
                unit_id=100,
            ),
            _DatasetSpec(
                dataset_id="{y}",
                source_euid="{source-y}",
                source_name="Force",
                values=[3, 5, 7, 9],
                unit_id=200,
            ),
        ],
    )

    result = fit_cap_datasets(
        cap_path,
        CapLinearFitRequest(
            x=CapDatasetSelection(dataset_id="{x}"),
            y=CapDatasetSelection(dataset_id="{y}"),
        ),
    )

    assert result.fit.slope == 2
    assert result.fit.intercept == 3
    assert result.x.file_path == str(cap_path.resolve())
    assert result.x.file_name == "fit.cap"
    assert result.x.dataset_index == 0
    assert result.x.dataset_id == "{x}"
    assert result.x.source_euid == "{source-x}"
    assert result.x.source_name == "Position"
    assert result.x.unit_id == 100
    assert result.y.dataset_index == 1
    assert result.y.unit_id == 200


def test_fit_rejects_different_sample_counts(tmp_path: Path) -> None:
    cap_path = tmp_path / "lengths.cap"
    _write_cap(
        cap_path,
        [
            _DatasetSpec("{x}", "{sx}", "x", [0, 1, 2]),
            _DatasetSpec("{y}", "{sy}", "y", [1, 2, 3, 4]),
        ],
    )

    with pytest.raises(ExperimentAnalysisError, match="numbers of samples"):
        _ = fit_cap_datasets(
            cap_path,
            CapLinearFitRequest(
                x=CapDatasetSelection(index=0),
                y=CapDatasetSelection(index=1),
            ),
        )


def test_fit_rejects_different_independent_coordinates(
    tmp_path: Path,
) -> None:
    cap_path = tmp_path / "coordinates.cap"
    _write_cap(
        cap_path,
        [
            _DatasetSpec("{x}", "{sx}", "x", [0, 1, 2]),
            _DatasetSpec(
                "{y}",
                "{sy}",
                "y",
                [1, 2, 3],
                independent_kind="interval",
                interval_step=2,
            ),
        ],
    )

    with pytest.raises(ExperimentAnalysisError, match="coordinate kinds"):
        _ = fit_cap_datasets(
            cap_path,
            CapLinearFitRequest(
                x=CapDatasetSelection(index=0),
                y=CapDatasetSelection(index=1),
            ),
        )


@pytest.mark.parametrize(
    "unavailable",
    [
        _DatasetSpec(
            "{text}",
            "{st}",
            "Label",
            ["first", "second", "third"],
            value_kind="text",
        ),
        _DatasetSpec(
            "{missing}",
            "{sm}",
            "Missing",
            [1, None, 3],
            numeric_cache=True,
        ),
    ],
)
def test_fit_rejects_unavailable_numeric_samples(
    tmp_path: Path,
    unavailable: _DatasetSpec,
) -> None:
    cap_path = tmp_path / "unavailable.cap"
    _write_cap(
        cap_path,
        [
            _DatasetSpec("{x}", "{sx}", "x", [0, 1, 2]),
            unavailable,
        ],
    )

    with pytest.raises(ExperimentAnalysisError):
        _ = fit_cap_datasets(
            cap_path,
            CapLinearFitRequest(
                x=CapDatasetSelection(index=0),
                y=CapDatasetSelection(index=1),
            ),
        )


@pytest.mark.parametrize("second_unit", [4096, None])
def test_comparison_requires_matching_declared_units(
    tmp_path: Path,
    second_unit: int | None,
) -> None:
    cap_path = tmp_path / "units.cap"
    _write_cap(
        cap_path,
        [
            _DatasetSpec("{first}", "{s1}", "first", [1, 2], unit_id=2048),
            _DatasetSpec(
                "{second}",
                "{s2}",
                "second",
                [3, 4],
                unit_id=second_unit,
            ),
        ],
    )

    with pytest.raises(ExperimentAnalysisError, match="unit"):
        _ = compare_cap_datasets(
            cap_path,
            CapRunComparisonRequest(
                datasets=[
                    CapDatasetSelection(index=0),
                    CapDatasetSelection(index=1),
                ],
            ),
        )


def test_comparison_returns_explicit_provenance(tmp_path: Path) -> None:
    cap_path = tmp_path / "compare.cap"
    _write_cap(
        cap_path,
        [
            _DatasetSpec("{first}", "{s1}", "First", [1, 2, 3]),
            _DatasetSpec("{second}", "{s2}", "Second", [4, 5]),
        ],
    )

    result = compare_cap_datasets(
        cap_path,
        CapRunComparisonRequest(
            datasets=[
                CapDatasetSelection(index=0),
                CapDatasetSelection(dataset_id="{second}"),
            ],
        ),
    )

    assert [item.dataset_id for item in result.datasets] == [
        "{first}",
        "{second}",
    ]
    assert [item.unit_id for item in result.datasets] == [2048, 2048]
    assert [item.name for item in result.comparison] == [
        "dataset[0]",
        "dataset[1]",
    ]
    assert result.comparison[1].mean_difference_from_first == 2.5


def test_selection_rejects_ambiguous_id_and_invalid_index(
    tmp_path: Path,
) -> None:
    cap_path = tmp_path / "selection.cap"
    _write_cap(
        cap_path,
        [
            _DatasetSpec("{duplicate}", "{s1}", "first", [0, 1, 2]),
            _DatasetSpec("{duplicate}", "{s2}", "second", [1, 2, 3]),
        ],
    )

    with pytest.raises(ExperimentAnalysisError, match="ambiguous"):
        _ = fit_cap_datasets(
            cap_path,
            CapLinearFitRequest(
                x=CapDatasetSelection(dataset_id="{duplicate}"),
                y=CapDatasetSelection(index=1),
            ),
        )
    with pytest.raises(ExperimentAnalysisError, match="outside"):
        _ = fit_cap_datasets(
            cap_path,
            CapLinearFitRequest(
                x=CapDatasetSelection(index=0),
                y=CapDatasetSelection(index=99),
            ),
        )


def test_selection_requires_one_explicit_selector() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        _ = CapDatasetSelection()
    with pytest.raises(ValidationError, match="exactly one"):
        _ = CapDatasetSelection(index=0, dataset_id="{dataset}")


def test_comparison_rejects_same_dataset_selected_twice(
    tmp_path: Path,
) -> None:
    cap_path = tmp_path / "duplicate-selection.cap"
    _write_cap(
        cap_path,
        [
            _DatasetSpec("{first}", "{s1}", "first", [1, 2]),
            _DatasetSpec("{second}", "{s2}", "second", [3, 4]),
        ],
    )

    with pytest.raises(ExperimentAnalysisError, match="distinct"):
        _ = compare_cap_datasets(
            cap_path,
            CapRunComparisonRequest(
                datasets=[
                    CapDatasetSelection(index=0),
                    CapDatasetSelection(dataset_id="{first}"),
                ],
            ),
        )


@pytest.mark.skipif(not EXAMPLE.exists(), reason="Capstone example is not installed")
def test_reads_installed_example_without_modifying_it() -> None:
    result = compare_cap_datasets(
        EXAMPLE,
        CapRunComparisonRequest(
            datasets=[
                CapDatasetSelection(
                    dataset_id="{6c0c3c58-4e82-4c61-a84b-d1784e7340ed}",
                ),
                CapDatasetSelection(
                    dataset_id="{ef8cfd90-2cbb-4021-ba2e-c39cb05837cb}",
                ),
            ],
        ),
    )

    assert [item.source_name for item in result.datasets] == [
        "Init. Red v",
        "Init. Blue v",
    ]
    assert [item.unit_id for item in result.datasets] == [2304, 2304]
    assert [item.sample_count for item in result.datasets] == [6, 6]

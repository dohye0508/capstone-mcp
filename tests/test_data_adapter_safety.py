# Copyright 2026 Capstone MCP contributors.
"""Offline regression tests for channel selection and sample provenance."""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING
from unittest.mock import MagicMock
from xml.etree.ElementTree import Element, SubElement, tostring
from zipfile import ZipFile

import pytest

from capstone_mcp.bridge import NativeInventory
from capstone_mcp.data_sources.adapters.capfile import (
    read_capfile_series,
    read_saved_run_data,
)
from capstone_mcp.data_sources.adapters.live_telemetry import LiveMeasurementAdapter
from capstone_mcp.session import UnifiedSessionManager
from capstone_mcp.session.telemetry import TelemetryBuffer

if TYPE_CHECKING:
    from pathlib import Path


def _write_channels(
    path: Path,
    channels: list[tuple[str, str, list[float]]],
    *,
    run_ids: list[str] | None = None,
) -> None:
    root = Element("DSProExperiment")
    repository = SubElement(root, "DataRepository")
    with ZipFile(path, "w") as archive:
        for index, (name, run, values) in enumerate(channels):
            identifier = run_ids[index] if run_ids else f"run-{run}"
            member = f"data/{index}.tmp"
            source = SubElement(repository, "DataSource", LongName=name)
            dataset = SubElement(source, "DataSet", Name=name, DataSetID=identifier)
            segment = SubElement(dataset, "DataSegmentElement")
            _ = SubElement(
                segment, "DependentStorageElement", StorageType="0",
                DataCacheDataSize=str(len(values)), FileName=member,
            )
            _ = SubElement(
                segment, "IndependentStorageElement", StorageType="4",
                CacheDataCount=str(len(values)),
            )
            parameters = SubElement(repository, "RunParameterSet", RunParameterID=identifier)
            _ = SubElement(parameters, "ParameterValue", RunName=run)
            archive.writestr(member, b"".join(struct.pack("<Id", 1, v) for v in values))
        archive.writestr("main.xml", tostring(root))


@pytest.mark.parametrize(("x_name", "y_name"), [("missing", "Force"), ("Time", "missing"), ("", "Force")])
def test_archive_unknown_channel_never_uses_other_dataset(
    tmp_path: Path, x_name: str, y_name: str,
) -> None:
    path = tmp_path / "channels.cap"
    _write_channels(path, [("Time", "Run #1", [0, 1]), ("Force", "Run #1", [3, 4])])
    with pytest.raises(ValueError, match=r"not found|must not be empty"):
        _ = read_capfile_series(path, x_name, y_name)


def test_archive_exact_match_precedes_partial_and_rejects_ambiguity(tmp_path: Path) -> None:
    path = tmp_path / "channels.cap"
    _write_channels(path, [
        ("Time", "Run #1", [0, 1]),
        ("Force sensor 2", "Run #1", [30, 40]),
        ("Force", "Run #1", [3, 4]),
    ])
    assert read_capfile_series(path, "Time", "Force").y.values == [3, 4]
    with pytest.raises(ValueError, match="ambiguous"):
        _ = read_capfile_series(path, "Time", "For")


def test_archive_multiple_runs_require_explicit_selection(tmp_path: Path) -> None:
    path = tmp_path / "runs.cap"
    _write_channels(path, [
        ("Time", "Run #1", [0, 1]), ("Force", "Run #1", [3, 4]),
        ("Time", "Run #2", [0, 1]), ("Force", "Run #2", [5, 6]),
    ])
    with pytest.raises(ValueError, match="ambiguous"):
        _ = read_capfile_series(path, "Time", "Force")
    series = read_capfile_series(path, "Time", "Force", run_id="Run #2")
    assert series.y.values == [5, 6]
    assert series.run_id == "Run #2"


@pytest.mark.parametrize(
    ("channels", "message"),
    [
        ([("Time", "Run #1", [0, 1]), ("Force", "Run #2", [3, 4])], "different runs"),
        ([("Time", "Run #1", [0]), ("Force", "Run #1", [3, 4])], "different sample counts"),
    ],
)
def test_archive_rejects_unpaired_arrays(
    tmp_path: Path, channels: list[tuple[str, str, list[float]]], message: str,
) -> None:
    path = tmp_path / "unpaired.cap"
    _write_channels(path, channels)
    with pytest.raises(ValueError, match=message):
        _ = read_capfile_series(path, "Time", "Force")


def test_archive_different_run_identifiers_with_same_label_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "same-label.cap"
    _write_channels(
        path,
        [("Time", "Renamed run", [0, 1]), ("Force", "Renamed run", [3, 4])],
        run_ids=["run-a", "run-b"],
    )
    with pytest.raises(ValueError, match="different runs"):
        _ = read_capfile_series(path, "Time", "Force")


def test_all_series_rejects_duplicate_run_names(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.cap"
    _write_channels(path, [("Force", "Run #1", [1, 2]), ("Force", "Run #2", [3, 4])])
    with pytest.raises(ValueError, match="multiple saved runs"):
        _ = read_saved_run_data(path, run_id=None, axes=None)


def test_all_series_preserves_sparse_values_without_shifting_samples(tmp_path: Path) -> None:
    path = tmp_path / "sparse.cap"
    _write_channels(path, [("Time", "Run #1", [0, 1]), ("Force", "Run #1", [float("nan"), 4])])
    saved = read_saved_run_data(path, run_id=None, axes=None)
    assert saved.series["Force"].values == [None, 4]


def test_all_series_preserves_complete_arrays(tmp_path: Path) -> None:
    path = tmp_path / "complete.cap"
    _write_channels(path, [("Time", "Run #1", [0, 1]), ("Force", "Run #1", [3, 4])])
    saved = read_saved_run_data(path, run_id=None, axes=None)
    assert {name: channel.values for name, channel in saved.series.items()} == {"Time": [0, 1], "Force": [3, 4]}


def _live_adapter() -> tuple[LiveMeasurementAdapter, MagicMock]:
    session = MagicMock(spec=UnifiedSessionManager)
    session.debug_port = 9222
    session.telemetry = TelemetryBuffer()
    session.read_live_inventory.return_value = NativeInventory(sensors=[], measurements=[
        {"name": "Voltage 2", "euid": "v2", "units": "V"},
        {"name": "Voltage", "euid": "v1", "units": "V"},
    ])
    session.read_live_measurement.return_value = 3.3
    return LiveMeasurementAdapter(session=session), session


def test_live_exact_channel_and_retained_sample_count() -> None:
    adapter, session = _live_adapter()
    assert [d.sample_count for d in adapter.list_datasets()] == [0, 0]
    session.telemetry.push_sample("v1", 2.0, timestamp=0.0)
    assert [d.sample_count for d in adapter.list_datasets()] == [0, 1]
    session.telemetry.push_sample("v1", 3.0, timestamp=1.0)
    series = adapter.get_series("index", "Voltage")
    session.read_live_measurement.assert_not_called()
    assert series.x.values == [0, 1]
    assert series.y.values == [2.0, 3.0]
    assert series.metadata["x_basis"] == "sample_index"


@pytest.mark.parametrize("x_name", ["time", "t"])
def test_live_does_not_invent_time_axis(x_name: str) -> None:
    adapter, session = _live_adapter()
    with pytest.raises(ValueError, match="at least two"):
        _ = adapter.get_series(x_name, "Voltage")
    session.read_live_measurement.assert_not_called()


@pytest.mark.parametrize("name", ["Volt", ""])
def test_live_ambiguous_or_empty_measurement_is_rejected(name: str) -> None:
    adapter, session = _live_adapter()
    with pytest.raises(ValueError, match="Expected one"):
        _ = adapter.get_series("index", name)
    session.read_live_measurement.assert_not_called()


def test_live_run_selection_is_not_fabricated() -> None:
    adapter, session = _live_adapter()
    with pytest.raises(ValueError, match="specific run"):
        _ = adapter.get_series("index", "Voltage", run_id="Run #1")
    session.read_live_inventory.assert_not_called()

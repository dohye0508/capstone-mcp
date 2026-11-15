# Copyright 2026 Capstone MCP contributors.
"""Offline regressions for literal inputs and non-destructive report output."""

import json
import threading
from pathlib import Path
from typing import cast
from unittest.mock import Mock

import pytest
from pywinauto.keyboard import parse_keys

from capstone_mcp import bridge, desktop, server
from capstone_mcp.tools import physics
from capstone_mcp.tools.physics import _write_report_file


@pytest.mark.parametrize("unit", ["0);evil();//", "1", True, None, 1.5])
def test_measurement_rejects_non_integer_before_evaluation(
    unit: object, monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluate = Mock()
    monkeypatch.setattr(bridge, "evaluate", evaluate)
    with pytest.raises(bridge.BridgeError, match="must be an integer"):
        bridge.read_measurement(9222, "sensor", cast("int", unit))
    evaluate.assert_not_called()


def test_measurement_identifier_is_json_encoded(monkeypatch: pytest.MonkeyPatch) -> None:
    evaluate = Mock(return_value={"ReturnValue": 1, "cmdResult": True})
    monkeypatch.setattr(bridge, "evaluate", evaluate)
    identifier = 'sensor\\");evil();//'
    assert bridge.read_measurement(9222, identifier, 3) == 1
    assert evaluate.call_args.args[1].endswith(json.dumps(identifier) + ",3)")


@pytest.mark.parametrize("text", ["F = (m+a)^2 + 50%", "%{F4}", "{ENTER}~{}", "한글 λ + β"])
def test_literal_text_roundtrips_keyboard_parser_without_shortcuts(
    text: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    send = Mock()
    monkeypatch.setattr(desktop, "keyboard_send_keys", send)
    desktop.Capstone().type_text(text)
    actions = parse_keys(send.call_args.args[0], with_spaces=True)
    assert "".join(action.key for action in actions) == text
    assert all(action.down and action.up for action in actions)


@pytest.mark.parametrize("format_type", ["markdown", "html", "both"])
def test_report_never_overwrites_existing_file(tmp_path: Path, format_type: str) -> None:
    destination = tmp_path / "report.md"
    destination.write_text("original", encoding="utf-8")
    with pytest.raises(FileExistsError):
        _write_report_file(str(destination), format_type, "new", "<p>new</p>")
    assert destination.read_text(encoding="utf-8") == "original"
    assert not destination.with_suffix(".html").exists()


def test_report_second_destination_conflict_rolls_back_first(tmp_path: Path) -> None:
    destination = tmp_path / "report.md"
    html = destination.with_suffix(".html")
    html.write_text("original", encoding="utf-8")
    with pytest.raises(FileExistsError):
        _write_report_file(str(destination), "both", "new", "<p>new</p>")
    assert not destination.exists()
    assert html.read_text(encoding="utf-8") == "original"


def test_report_rejects_colliding_output_paths(tmp_path: Path) -> None:
    destination = tmp_path / "report.html"
    with pytest.raises(ValueError, match="must be different"):
        _write_report_file(str(destination), "both", "new", "<p>new</p>")
    assert not destination.exists()


def test_report_writes_both_new_outputs(tmp_path: Path) -> None:
    destination = tmp_path / "nested" / "report.md"
    _write_report_file(str(destination), "both", "new", "<p>new</p>")
    assert destination.read_text(encoding="utf-8") == "new"
    assert destination.with_suffix(".html").read_text(encoding="utf-8") == "<p>new</p>"


@pytest.mark.anyio
async def test_report_generation_and_rendering_leave_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loop_thread = threading.get_ident()
    generate = physics.generate_report
    render = physics.render_report
    threads: list[int] = []

    def generate_checked(*args: object, **kwargs: object) -> object:
        threads.append(threading.get_ident())
        return generate(*args, **kwargs)

    def render_checked(*args: object, **kwargs: object) -> object:
        threads.append(threading.get_ident())
        return render(*args, **kwargs)

    monkeypatch.setattr(physics, "generate_report", generate_checked)
    monkeypatch.setattr(physics, "render_report", render_checked)
    result = await server.capstone_generate_lab_report(
        "sample", experiment_id="photoelectric_effect",
    )
    assert result.report_markdown
    assert len(threads) == 2
    assert all(worker_thread != loop_thread for worker_thread in threads)

# Copyright 2026 Capstone MCP contributors.
"""Observed non-English mappings travel through tools, IPC and native workflows."""
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from capstone_mcp import file_workflows as workflow
from capstone_mcp.automation_models import NativeRequest
from capstone_mcp.desktop import AutomationError
from capstone_mcp.file_workflow_models import FileWorkflowLabels
from capstone_mcp.models import Action, Bounds, Control, Snapshot, Window
from capstone_mcp.native import runtime
from capstone_mcp.tools.files import register_file_tools

LABELS = FileWorkflowLabels(file_menu="파일", filename_id="저장경로", open_filename_id="열기경로", discard="버리기", export_format="출력 형식", csv_format="쉼표 데이터", alignment_options="정렬 방식", align_by_index="번호 순서", select_all="전체 선택", export_to_file="파일 출력", close="닫기")
BOUNDS = Bounds(left=0, top=0, right=100, bottom=100)


def _control(name: str, kind: str = "Button", identifier: str = "", ref: str | None = None) -> Control:
    return Control(ref=ref or name, parent=None, name=name, control_type=kind, automation_id=identifier, enabled=True, visible=True, bounds=BOUNDS)


def _snapshot(controls: list[Control], handle: int = 2) -> Snapshot:
    return Snapshot(window=Window(handle=handle, title="dialog", process_id=7, bounds=BOUNDS), controls=controls, truncated=False)


def test_exact_file_menu_mapping_and_duplicate_rejection() -> None:
    menu = _control("파일", "MenuItem")
    command = _control("저장", "MenuItem", "mActionSaveAs")
    app = Mock(windows=Mock(return_value=[]), snapshot=Mock(return_value=_snapshot([menu, _control("File", "MenuItem")])))
    events = Mock()
    events.changes.until.return_value = _snapshot([command])
    workflow._open_command(app, events, 1, "mActionSaveAs", file_menu_label=LABELS.file_menu)
    assert app.act.call_args_list[0].args == (menu.ref, Action.INVOKE)
    app.act.reset_mock()
    app.snapshot.return_value = _snapshot([menu, menu.model_copy(update={"ref": "duplicate"})])
    with pytest.raises(AutomationError, match="one enabled"):
        workflow._open_command(app, events, 1, "mActionSaveAs", file_menu_label=LABELS.file_menu)
    app.act.assert_not_called()


def test_custom_filename_id_used_before_save(tmp_path: Path) -> None:
    field = _control("경로", "Edit", LABELS.filename_id)
    save = _control("저장", "Button", "1")
    app = Mock(snapshot=Mock(return_value=_snapshot([save])))
    files = Mock()
    workflow._save_dialog(app, files, _snapshot([field]), tmp_path / "new.cap", {1}, filename_id=LABELS.filename_id)
    assert app.set_value.call_args.args[0] == field.ref
    with pytest.raises(AutomationError, match="one enabled"):
        workflow._save_dialog(app, files, _snapshot([field]), tmp_path / "new.cap", {1})


def _events(monkeypatch: pytest.MonkeyPatch) -> Mock:
    events = Mock()
    monkeypatch.setattr(workflow, "WindowEvents", lambda _pid: nullcontext(events))
    monkeypatch.setattr(workflow, "FileEvents", lambda *_args: nullcontext(Mock()))
    return events


def test_export_uses_every_observed_export_label(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = _events(monkeypatch)
    events.changes.until.side_effect = [_snapshot([], 2), True]
    buttons = [_control(name) for name in (LABELS.select_all, LABELS.export_to_file, LABELS.close)]
    app = Mock(snapshot=Mock(return_value=_snapshot(buttons)), windows=Mock(return_value=[_snapshot([], 2).window]))
    monkeypatch.setattr(workflow, "_prepare", Mock(return_value=(tmp_path / "a.csv", "old", 7)))
    command, option, dialog, save, artifact = Mock(return_value={1}), Mock(), Mock(), Mock(), Mock()
    monkeypatch.setattr(workflow, "_open_command", command)
    monkeypatch.setattr(workflow, "_choose_export_option", option)
    monkeypatch.setattr(workflow, "_file_dialog", dialog)
    monkeypatch.setattr(workflow, "_save_dialog", save)
    monkeypatch.setattr(workflow, "_artifact", artifact)
    workflow.export_data(app, 1, "ignored.csv", workflow_labels=LABELS)
    assert command.call_args.kwargs["file_menu_label"] == LABELS.file_menu
    assert [call.args[-2:] for call in option.call_args_list] == [(LABELS.export_format, LABELS.csv_format), (LABELS.alignment_options, LABELS.align_by_index)]
    assert dialog.call_args.kwargs["filename_id"] == LABELS.filename_id
    assert save.call_args.kwargs["filename_id"] == LABELS.filename_id
    assert [call.args[0] for call in app.act.call_args_list] == [LABELS.select_all, LABELS.export_to_file, LABELS.close]


def test_open_uses_observed_discard_and_filename_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = _events(monkeypatch)
    discard, field = _control(LABELS.discard), _control("경로", "Edit", LABELS.open_filename_id)
    events.changes.until.side_effect = [_snapshot([discard]), _snapshot([field])]
    app = Mock(snapshot=Mock(return_value=_snapshot([_control("열기", "Button", "1")])))
    monkeypatch.setattr(workflow, "_open_preconditions", Mock(return_value=(tmp_path / "a.cap", "old*", 7)))
    command = Mock(return_value={1})
    monkeypatch.setattr(workflow, "_open_command", command)
    monkeypatch.setattr(workflow, "await_opened", Mock(return_value="a.cap"))
    result = workflow.open_experiment(app, 1, "a.cap", discard_unsaved=True, workflow_labels=LABELS)
    assert result.discarded_unsaved_changes
    assert app.act.call_args_list[0].args[0] == LABELS.discard
    assert app.set_value.call_args.args[0] == field.ref
    assert command.call_args.kwargs["file_menu_label"] == LABELS.file_menu


@pytest.mark.parametrize("operation", ["save_experiment", "export_data", "open_experiment"])
def test_native_roundtrip_forwards_workflow_labels(monkeypatch: pytest.MonkeyPatch, operation: str) -> None:
    class Payload(BaseModel):
        """Minimal native reply for forwarding-only assertions."""

    target = Mock(return_value=Payload())
    monkeypatch.setattr(runtime, operation, target)
    desktop = runtime.NativeDesktop()
    request = NativeRequest.model_validate({"operation": operation, "handle": 1, "value": "path", "workflow_labels": LABELS.model_dump()})
    request = NativeRequest.model_validate_json(request.model_dump_json())
    desktop.dispatch(request)
    assert target.call_args.kwargs["workflow_labels"] == LABELS


@pytest.mark.anyio
@pytest.mark.parametrize("operation", ["save_experiment", "export_data", "open_experiment"])
async def test_public_router_forwards_observed_mapping(operation: str, tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n1,2\n", encoding="utf-8")
    result = {"path": str(path), "document_title_before": "before", "document_title_after": "after", "discarded_unsaved_changes": False} if operation == "open_experiment" else {"path": str(path), "format": "csv", "size_bytes": 8, "sha256": "hash", "document_title_before": "before", "document_title_after": "after", "precision": "capstone-export"}
    native = AsyncMock(return_value=result)
    tools = register_file_tools(FastMCP("label-test"), native)
    await tools[f"capstone_{operation}"](1, str(path), workflow_labels=LABELS)
    assert native.call_args.args[0].workflow_labels == LABELS
    assert native.call_args.kwargs["mutates"]

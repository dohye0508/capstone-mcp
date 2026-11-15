# Round 3 explicit file workflow mappings

WF06/WF15: file menus, filename fields and export dialog controls no longer require hardcoded English labels/field IDs. `FileWorkflowLabels` is an optional public `workflow_labels` parameter on save/open/export. The typed model survives NativeRequest JSON encoding and each native runtime handler forwards it to the workflow implementation.

All fields are consumed: file_menu, filename_id, open_filename_id, discard, export_format, csv_format, alignment_options, align_by_index, select_all, export_to_file, close. Defaults retain the earlier observed English labels and filename IDs 1001/1148. Stable existing command and confirmation Automation IDs remain unchanged.

This is an explicit **observed mapping**, not automatic translation or certification of Korean/other native locales. Supply labels/IDs copied from the actual current native snapshot. Exact equality and `_one` retain uniqueness, visibility, enabled-state and truncated-snapshot checks. Missing/ambiguous controls fail rather than falling back to fuzzy text or another language. Existing no-overwrite, unsaved-discard consent, title-confirmation and export cleanup behavior remains intact.

Example: `workflow_labels={"file_menu":"<observed label>","filename_id":"<observed field ID>"}` overrides only those fields; every other default is still used. For another locale, supply every differing observed field rather than assuming translations.

Tests in `test_file_workflow_labels.py` use synthetic non-English controls with English distractors and duplicate targets; exercise mapped filename/discard controls, export format/alignment/options/close, all three public routers, and all three native IPC handlers. These tests do not open native dialogs. 49 scoped workflow/router/native/capture tests pass; basedpyright and Ruff pass for changed production files.

Contract limits: each label/ID is 1–256 characters; unknown fields are forbidden by the shared Model. Matching is exact and case-sensitive with no whitespace trimming or translation. Overrides do not change stable command IDs (`mActionSaveAs`, `mActionOpenExperiment`, `mActionExportData`), confirmation button ID `1`, or the export dialog ID `DataExportDialog`. An installation with different command/dialog structure remains unsupported until observed evidence establishes a compatible workflow.

Illustrative tool invocation (the Korean labels are synthetic examples; replace them with actual snapshot values):

```json
{
  "handle": 123,
  "path": "C:/experiments/new-output.csv",
  "allow_foreground": true,
  "workflow_labels": {
    "file_menu": "파일",
    "filename_id": "1001",
    "open_filename_id": "1148",
    "discard": "버리기",
    "export_format": "출력 형식",
    "csv_format": "쉼표 데이터",
    "alignment_options": "정렬 방식",
    "align_by_index": "번호 순서",
    "select_all": "전체 선택",
    "export_to_file": "파일 출력",
    "close": "닫기"
  }
}
```

Call `capstone_export_data` with this structure only after independently observing the target controls. Save/open accept the same mapping; discard remains separately gated by `discard_unsaved=true`.

Dialog/menu snapshots now use bounded depth 16 and 10,000 controls, including candidate refresh. This avoids deliberately shallow trees being rejected by the completeness guard. A tree that still exceeds either bound remains explicitly rejected; no claim of unrestricted traversal or native locale coverage is made.

# Round 3 graph residuals: supported observed-label contracts

All verification below is internal. UIA, clipboard, monitor and window APIs are
mocked in regression tests; no live GUI, sensor or clipboard operation was run.

## Implemented

| Original IDs | Change | Remaining native verification |
|---|---|---|
| GR06 | Fit popup visibility uses a freshly validated owned HWND and physical monitor bounds, not the main window rectangle. A popup extending beyond its owner is allowed when fully visible on a monitor. Moved, empty, offscreen, occluded-at-click-point or out-of-popup targets fail before selection. Errors after opening attempt menu cleanup while preserving the original error. | Validate physical monitor rectangles and popup placement at mixed DPI; a popup spanning monitor boundaries is conservatively refused. |
| GR07 | `GraphFitRequest.menu_labels` maps known fit-model enums to exact caller-observed accessible native labels. Named menus can contain multiple items; no anonymous single-item assumption is applied to this explicit path. The existing anonymous 24-row schema remains the compatibility fallback when no label is supplied. Both paths require a unique popup, complete snapshot, fresh final refs and native fit-state readback. | Confirm the installed Capstone exposes accessible named entries, or use the already supported anonymous schema; no alternate row order/ID was invented. |
| GR02 / WF07 | `ReadGraphRequest.display_menu_label` and `copy_display_label` allow exact observed labels through the unified graph request. The same fields on `GraphFitRequest` route through fitting and analysis initial/readback/enable/axis-change reads. Copy popup lookup excludes baseline windows, rejects ambiguity and refreshes selected refs after the scan. | Confirm the actual labels/native Copy Display payload for each installed locale. Automatic translation/discovery is not claimed. |
| GR08 | `CreateGraphRequest.palette_label` selects one exact observed visible/enabled palette item. Defaults retain `Graph`; duplicate labels or incomplete snapshots fail before insertion. | Confirm actual palette label and native insertion in the installed locale. |
| GR14 | `tool_label` on statistics, area and delta requests selects one exact observed owned toolbar label; known English keywords remain defaults. The supplied label is used on both pre-state and post-state snapshots. | Native translated numeric readouts may still require locale-specific parsing; a toolbar match alone does not establish a measured value. |

The new label fields are transported by the existing serialized `GraphRequest`
router. Legacy direct `read_graph`/`create_graph` native operations retain English
defaults; use `capstone_manage_graph` with the corresponding explicit subrequest
for the new observed-label contract. `set_graph_fits` already validates its nested
`GraphFitRequest`, so named model labels and readback labels survive that route.

Example fields (values must come from an actual current snapshot; these strings
are examples, not an asserted PASCO translation table):

```json
{
  "action": "read",
  "read": {
    "handle": 123,
    "display_menu_label": "observed display menu text",
    "copy_display_label": "observed copy item text"
  }
}
```

For fitting, pass `menu_labels: {"linear": "observed linear fit item text"}` and
both display/copy labels in the nested fitting request. Model enum/native type
mapping and authoritative graph-XML verification are unchanged.

## Still unsupported without native evidence

| Original ID | Concrete blocker | Required evidence / acceptance |
|---|---|---|
| GR11 | Request coordinates do not identify native draggable crosshair handles or specify whether they are screen/data coordinates; no captured drag schema exists in the repository. Positioning remains rejected before input, while observed delta reading works. | Capture native crosshair identities, coordinate convention and post-drag readback. Move only identified handles and verify both native endpoints before reporting positioned=true. |
| DISP-02 | Native measurement popup binding has no captured selector/menu/acceptance schema. Existing safe ValuePattern path does not prove native binding; unsafe click-then-stale-write was removed. | Capture the selector's owned popup and measurement identity/readback; implement exact observed traversal and verify the bound source ID. |
| RUN-01 | No captured owned deletion-confirmation schema identifies the requested run. Automatically clicking an arbitrary new Yes/OK dialog would recreate the removed destructive defect. Explicit-name deletion reports only observed removal; unresolved confirmation remains unverified. | On a disposable run, capture dialog owner, exact run identity and button behavior; confirm only that owned request and verify the run is absent afterward. |

These capability gaps are not reported as fixed by the observed-label additions.
No production code was changed in displays or runs in this round.

## Regression evidence

`tests/test_graph_popup_geometry_labels.py` covers popup beyond owner bounds,
negative-origin monitors, offscreen/moved rejection, cleanup, ambiguous/named fit
menus, non-English explicit-label routing, analysis readback, and fresh-reference
reacquisition after unrelated popup snapshots. Existing graph and UI workflow
suites also pass: **114 tests passed in 5.95 seconds**. Scoped Ruff is clean;
scoped basedpyright reports **0 errors, 0 warnings, 0 notes**.

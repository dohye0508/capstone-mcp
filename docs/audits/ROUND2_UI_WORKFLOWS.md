# Round 2: UI workflow offline audit

This ledger distinguishes internally reproduced defects from native behavior that
cannot be certified without a Capstone session. `fixed` below means the stated
Python failure or unsafe success path has a regression test; it does not certify
Windows/Qt menus, DPI behavior, a native calculation, or hardware acquisition.
No application-control tools were used. Existing clipboard unit coverage was
found to call the real API and has been converted to an explicit mock; all new
clipboard regressions use a mock. The local CAP corpus remains read-only.

## Graphs

| ID | Disposition and evidence |
|---|---|
| GR01 | Fixed exact target window selection/input-readiness guard and baseline handle set; pre-existing palettes no longer inherently block inspection. Modal ownership relies on the existing Win32 guard. |
| GR02 | Requires live locale evidence. Display/Copy Display labels remain English; inventing translated native IDs would be unsafe. |
| GR03 | Fixed: failed fits may omit numeric result/goodness attributes; successful fits still require them. `test_graph_state` covers both. |
| GR04 | Partial: menu refs now go through validated `app.control`, with fresh snapshots and bounded spacing between ESC attempts. Persistent menu state raises instead of pretending completion. Native event timing still requires live validation. |
| GR05 | Fixed singleton-window precondition in fit/axis workflows: target input readiness plus baseline window set replaces blanket refusal of palettes. |
| GR06 | Requires live evidence of popup geometry/ownership at screen edges. No guessed desktop/menu coordinate conversion introduced. |
| GR07 | Requires native snapshot evidence for alternate unnamed menu structures. Existing fail-closed uniqueness rule retained. |
| GR08 | Requires live locale palette evidence. |
| GR09 | Requires live mixed-DPI validation; bootstrap DPI ownership is in the runtime agent's ledger. |
| GR10 | Fixed: explicit enable compares observed Toggle state/visible readout, no-ops if already correct, rejects unknown state before clicking. |
| GR11 | Mitigated: requested crosshair repositioning is rejected before input because two clicks do not establish requested coordinates. Read-only observed delta labels remain supported; drag placement requires live evidence. |
| GR12 | Fixed: coordinate pairs may be on separate labels; exactly two pairs required, three cannot be arbitrarily paired. |
| GR13 | Partial: removed cross-window global button fallback and unrelated graph fallback; ambiguous graphs/buttons fail. Toolbar geometry/ancestry at unusual layouts still needs live validation. |
| GR14 | Requires native locale toolbar evidence. |

## File workflows and Windows/localization

| ID | Disposition and evidence |
|---|---|
| WF01 | Partial safety fix: unsupported clipboard handles fail before Copy Display; restore only occurs if the sequence still matches this operation's captured copy, including restoring an originally empty clipboard. Newer external clipboard contents are not overwritten. The native clipboard mechanism and OS failure modes still require live validation. |
| WF02 | Architectural/native requirement remains: graph inspection uses Capstone's exported native clipboard schema. No unsupported replacement parser/API was invented. |
| WF03 | Root/tools runtime ownership; foreground defaults and receipt guards tracked there. |
| WF04 | Root report-path ownership; previous exclusive-create fix retained. |
| WF05 | Not reproduced as a traversal exploit: caller-specified local input/output paths are an explicit API capability; no extraction destination is derived from untrusted archive paths here. Existing save refusal of pre-existing output remains. |
| WF06 | Requires native locale evidence for File/export dialog labels. |
| WF07 | Duplicate GR02; requires live locale evidence. |
| WF08 | Root tools/physics ownership. |
| WF09 | Root tools/physics error-boundary ownership. |
| WF10 | Root tools/files and tools/ui error-boundary ownership. |
| WF11 | Runtime error-boundary ownership; prior structured-error fixes retained. |
| WF12 | Fixed: selects requested handle rather than windows[0]; uses existing input-readiness/modal guard and preserves baseline palette windows. |
| WF13 | Intentional safety contract: existing destinations are rejected to prevent overwrites. A new overwrite capability is not required to repair a P0. |
| WF14 | Partial fix: failure after opening File menu attempts ESC, preserving the original failure if cleanup also fails. Native menu timing requires live coverage. |
| WF15 | Requires supported native dialog snapshot evidence before replacing Edit ID1001. No guessed fallback clicks. |
| WF16 | Partial fix: known export dialog is closed in finally using a fresh Close ref; original failure is preserved. Unknown child confirmation dialogs are not automatically clicked. |
| WF17 | Fixed missing-window StopIteration: bounded retry then AutomationError. Observed old title after the existing time bound remains explicitly observed, never renamed synthetically. Large-file timing remains live-dependent. |
| WF18 | Fixed: opening waits for target title/input-readiness rather than requiring a singleton process window. NFC normalization shared with save title verification. |
| WF19 | Root file export/flush ownership. |
| WF20 | Root tools/files offload ownership. |
| WF21 | Root tools/physics offload ownership. |
| WF22 | Previously fixed HWND-scoped capture retained; screenshot unit tests mock capture backend. |
| WF23 | Runtime/instrument interaction ownership. |
| WF24 | Claim of unnecessary graph-analysis mutation lock is not generally valid: analyze can assign axes and toggle native fits. Runtime owns lock behavior. |
| P0-WIN01 | Native popup HWND selection requires live evidence; the claimed missing ClientToScreen is not universally valid because click_point's public coordinates are absolute screen coordinates. Popup module/runtime ownership handed to root. |
| P0-WIN02 | Fixed exception contract: matching_snapshot catches COMError, clears partial refs and raises actionable AutomationError instead of leaking partial snapshot. Does not bypass UIPI permissions. |
| P0-WIN03 | Runtime DPI bootstrap owns setup; actual high-DPI click correctness requires live evidence. |
| P0-L10N01 | Prior literal type_text escaping retained; new run/workbook/value fallbacks separate shortcut commands from literal text. |
| P0-L10N02 | Fixed NFC-normalized save/open title comparison; NFD/NFC fixture tests. |
| P0-L10N03 | Fixed requested run-name matching supports exact custom/Korean labels; no fabricated translations or generic number-only localized aliases. Automatic locale discovery remains native-dependent. |
| NAT09 | Fixed: no indefinite HWND-to-UIA-wrapper cache; fresh wrapper acquired after ownership/visibility check, regression reuses same handle. |
| NAT18 | Native frame-receipt validation belongs to runtime agent. |
| SEC09 | Fixed malformed override validation: explicit executable must be absolute, existing regular .exe file; legitimate custom filename is allowed. Explicit executable configuration is still a caller trust decision, not a signature-verification feature. |

## Calculator and run lifecycle

| ID | Disposition and evidence |
|---|---|
| CALC01 | Partial: reject unbalanced delimiters before UI, respecting quoted literals and bracketed measurement names; reject unsupported variable-binding map and unavailable unit control. Full Capstone expression grammar/engine validity requires native evidence. Cleanup refreshes refs and preserves original failure. |
| CALC02 | Prior fix retained: unverified submission returns failed/verified=false; no native registration is invented. |
| CALC03 | Fixed Unicode calculation names (Greek, subscript, CJK) through Unicode word matching. |
| CALC04 | False positive at audited baseline: Capstone.click and type_text exist. Correct current type_text(text) signature is used. |
| RUN-01 | Partial: removed indiscriminate Yes/OK clicks across windows and unconditional verified=true. Only unique explicit run names may be deleted; reports observed removal and input-readiness. Unresolved confirmation remains unverified; native confirmation workflow needs live evidence. |
| RUN-02 | Fixed exact named deletion supports renamed/localized runs. Latest aliases cannot establish identity and fail before input. |
| RUN-03 | Partial: removed suppressed delete/input/focus failures; selection does not stand in for visibility. Native ValuePattern backend behavior still requires live proof. |
| RUN-04 | Fixed fabricated visible_names injection removed; post-state is read, unknown state is not false or success. |
| RUN-05 | Fixed numeric aliases only apply to canonical English Run-number names; arbitrary unrelated digit strings cannot match. |
| RUN-06 | Partial: literal name typing separated from F2/selection/Enter; inline editor activation timing remains native-dependent. |
| RUN-07 | Tests now include stale-generation refs, no-op toggles and incomplete deletion. Mocks intentionally do not certify Qt/real sensor behavior. |
| RUN-P2-01 | Fixed fresh snapshots between run mutations; multiple matching controls fail before input unless one display is explicitly resolved. |
| RUN-P2-02 | Fixed shortcut/literal separation. |
| RUN-P2-03 | Fixed exact user-requested custom/localized names in visibility controls. |
| RUN-P2-06 | Exact coordinate pairing is intentional; fuzzy pairing could invent scientific alignment. No tolerance invented. |
| RUN-P2-07 | Fixed destructiveHint=true because the unified router exposes deletion; docstring no longer promises arbitrary automatic confirmation. |
| RUN-P3-01 | Runtime owns handle=0 resolution/validation; no arbitrary topmost window chosen by this domain layer. |
| RUN-P3-02 | Fixed brace/modifier literal typing; multiline run names rejected before snapshot/input. |
| CAP18 | False positive: prior equality compares deterministic numeric/independent value lists. Regression confirms repeated sparse nonfinite-to-None data produces no false delta. |
| CAP19 | Fixed: invalid/duplicate dataset identities do not replace prior baseline. A structurally valid snapshot whose later fit fails still advances baseline intentionally to prevent double-counting already captured samples. |

## Displays

| ID | Disposition and evidence |
|---|---|
| DISP-01 | Fixed generic Button/ComboBox selector fallback removed; Close is never chosen as measurement selector. |
| DISP-02 | Mitigated: no click-popup then write stale source control. Supported ValuePattern may be used; otherwise only an explicit Edit allows literal typing. Measurement binding does not claim native verification. Native popup selection needs live evidence. |
| DISP-04 | Fixed arbitrary Button excluded from column headers; semantic header or measurement-selector evidence is required. Delete Column regression. |
| DISP-05 | Fixed cross-table expansion bounds removed; only uniquely identified Add Column inside selected table qualifies. |
| DISP-06 | Fixed each column operation refreshes table/header/add refs, including after expansion; missing newly added column fails instead of reusing old refs. |
| DISP-07 | Fixed statistics attributed only to exactly one containing header's horizontal bounds; ambiguous or duplicate column statistics fail rather than overwrite first column. |
| DISP-08 | Fixed global time/range scans removed: unique scope/FFT container plus unique field of an editable type is required; timestamp outside a known field cannot be mutated. |
| DISP-09 | Mitigated: missing/collapsed trigger controls fail before mutation; unsupported trigger-source binding rejects. Settings submission stays verified=false; drawer expansion needs native evidence. |
| DISP-10 | Fixed plain '+' excluded from Add Page matching. |
| DISP-11 | Fixed only exactly one newly observed tab may be renamed; no new tab or ambiguous difference fails without renaming old page. Fresh snapshot verifies requested title. Async wait/real page identity requires live evidence. |
| DISP-12 | Fixed exact layout names/terminal automation IDs, no substring match; generic grid/template3 aliases rejected. Native layout postcondition remains unverified. |
| DISP-13 | Fixed unrelated largest/first Custom/Pane fallback removed; multiple matching displays require explicit exact target. |
| DISP-15 | Fixed Unicode minus normalization for digits and FFT coordinate parsing; table numeric parsing delegated to root locale parser. |
| DISP-16 | Fixed literal typing for run/workbook/value inputs; unsafe popup keyboard fallback removed. |
| DISP-17 | Partial: scope/FFT palette snapshots use depth16 and reject truncated snapshots. An arbitrary depth cannot prove complete native hierarchy; native-tree coverage remains live-dependent. |
| DISP-18 | Fixed unsolicited Voltage suffix removed: numeric level uses the existing control's unit context, never fabricates V. Trigger native validity remains unverified. |
| DISP-21 | Fixed explicit names/automation IDs match exactly with required container type; digit substring no longer selects arbitrary controls. |
| TST14 | Added mock-only file menu failure/known-export cleanup regressions. Real native dialog composition/timing remains live-dependent. |

## Internal verification

- Final owned suite: **268 passed in 22.24 seconds**, including graph/desktop,
  calculator, file, run and display tests plus the new safety regressions.
- Owned basedpyright: **0 errors, 0 warnings, 0 notes**.
- `git diff --check`: clean. Whole-repository Ruff/CI and integration tests are
  recorded by the integrating agent.

Main regression file: `tests/test_ui_workflow_safety.py`; existing calculator,
file, snapshot, graph, run, display and executable tests provide focused cases.

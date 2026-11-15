# Runtime remaining findings and live acceptance plan (2026-11-16)

These are original audit IDs, counted once each. They are not a count of confirmed unfixed P0 bugs. Cross-owner entries in ROUND2_RUNTIME are excluded and must be counted by their actual owner. No live steps below have been executed.

## Exact residual inventory

- Unresolved physical/interface evidence, 4 IDs: DEFECT-NAT02, DEFECT-HW01, DEFECT-HW02, P0-STRM01.
- Partial internal implementation, 0 IDs after this patch: DEFECT-NAT18 is now internally fixed for the actual coordinate-input paths and transport uncertainty. Physical native-control correctness is still not certified.
- Source-contract decision, 1 ID: DEFECT-TEL05. Finite/monotonic values and limits are validated; origin/unit/domain metadata for arbitrary externally supplied timestamps is not inferable.
- Explicit live test gaps, 15 IDs: DEFECT-TST01, DEFECT-TST02, DEFECT-TST03, DEFECT-TST11, DEFECT-TST12, DEFECT-TST13, DEFECT-TST14, DEFECT-TST15, DEFECT-TST17, DEFECT-TST18, DEFECT-TST20, DEFECT-MOCK01, DEFECT-MOCK02, DEFECT-MOCK03, DEFECT-SKIP02. TST12/MOCK01 describe overlapping calculator evidence but are two original IDs. TST15/TST20 have improved real process/thread tests; only their physical COM/stop portion remains.

Total residual evidence/contract IDs in this runtime-owned view: 20 (4 + 1 + 15). **This does not mean 20 confirmed unfixed production defects.** Cross-owner hardware tests may overlap this test-gap list: deduplicate original IDs in the master ledger. SDK private interception (FASTMCP-04) is a maintenance risk with a regression contract, not an additional proven unfixed P0. Deliberate nonblocking mutation admission and borrowed-worker ownership are policies, not unresolved bugs.

## Reproducible live acceptance procedures

Run only in an explicitly authorized disposable Capstone experiment, record application/version, Windows build, sensor model/firmware, locale/DPI, and before/after screenshots or raw responses. Preserve originals and disable hazardous outputs. These are proposed procedures, not instructions to autonomously operate equipment.

| Original ID | Procedure | Pass criterion |
| --- | --- | --- |
| DEFECT-NAT02 | On a disposable experiment, exercise a documented slow/unresponsive provider condition; issue one bounded read then inspect worker and application independently. | Request terminates within configured worker deadline plus cleanup budget; structured error; no automatic replay or unrelated process termination; physical state is explicitly unknown until independently observed. |
| DEFECT-HW01 | Compare the supported native acquisition export's timestamps with a captured read-measurement response for the same sensor; retain raw provider schema. | Hardware timestamps are identified with units/clock domain, or API explicitly reports instantaneous host polling and refuses high-rate historical claims. Do not equate host monotonic time to hardware time. |
| DEFECT-HW02 | Feed two channels the same documented reference event and export both native series; compare sample identities and timestamp domains. | Alignment follows an explicit validated contract, with missing/unequal channels rejected. No implicit interpolation or cross-run matching. Accuracy tolerance must come from equipment specifications before measurement. |
| P0-STRM01 | Identify an actually supported bulk acquisition interface using vendor documentation/captured native response; compare count and timing with native export at supported rates. | Exact retained sample count and timestamp semantics match native output; otherwise report unsupported high-rate streaming. A single instantaneous polling value cannot pass as 100 kHz streaming. |
| DEFECT-TEL05 | Supply two explicitly labeled clock domains and units plus same-domain monotonic samples. | Cross-domain combination rejected unless a documented transformation is provided; valid same-domain samples preserve origin. If no metadata API exists, keep this contract gap open. |
| DEFECT-TST01 | Execute each publicly supported native operation against a saved disposable fixture and retain independent observed postconditions. | A per-operation matrix separates verified state, delivered-but-unverified input, unsupported cases, and failures; fake backend coverage is never counted as native parity. |
| DEFECT-TST02 | Inspect target edit controls and actual UIA ValuePattern availability; exercise valid edit and denied/read-only control. | Supported edits are read back; unsupported patterns fail or use verified literal input, never invented COM methods or success. |
| DEFECT-TST03 | Repeat target input at documented 100/150/200 percent DPI, across monitor moves and authorized integrity-level combinations. | Target bounds/coordinates agree with observed controls; denied foreground/UIPI yields error without alternate guessed clicks. |
| DEFECT-TST11 | Explicitly opt into live smoke with a disposable experiment and a real supported sensor. | Smoke executes rather than skips; native state and sample availability verified independently; stopping is confirmed. |
| DEFECT-TST12 | Submit valid and invalid calculation expressions in the actual Qt editor and inspect native error/status controls. | Only observed native acceptance is verified; invalid/unknown results remain error/unverified. |
| DEFECT-TST13 | Open axis menus repeatedly under normal and delayed rendering; choose unique exact paths, then repeat ambiguous and missing labels. | No click before observed menu item, ambiguity fails, selection is checked from native binding evidence. |
| DEFECT-TST14 | Exercise open/save/export dialogs on copies, including cancel and an existing output filename. | Correct target and literal path; existing file untouched; cancel returns failure/cancel status; no focus-loss click elsewhere. |
| DEFECT-TST15 | Run the real native worker's attach/read/error/shutdown sequence, including a safely reproducible provider failure. | Same wire/error/cleanup contracts as subprocess tests, plus no unrelated application termination or leaked worker. |
| DEFECT-TST17 | Change a supported sampling rate and wait for native observed value; include delayed negotiation and rejection. | Receipt reflects observed rate with correct unit; no zero-delay guessed success or unsupported rollback. |
| DEFECT-TST18 | Subscribe to target-process WinEvents, trigger an authorized target control change, also generate an unrelated process event. | Target event reaches callback, unrelated event is excluded, shutdown releases hook/window/thread; no same-process-only evidence substituted. |
| DEFECT-TST20 | Start a short authorized acquisition, request concurrent mutation and cancellation, and independently observe final recording state. | Mutations remain serialized/rejected; cancellation does not release ownership early; stop observed before completion. Unknown stop must be explicit, not success. |
| DEFECT-MOCK01 | Use the TST12 procedure and capture native controls used as acceptance evidence. | Native expression acceptance replaces mock expectation; invalid expression cannot report verified success. |
| DEFECT-MOCK02 | Inspect actual digits display descendant Automation IDs/ancestry in supported locales. | Selector identifies exactly intended display or explicitly reports unsupported; no cross-display or fabricated ID fallback. |
| DEFECT-MOCK03 | Inspect actual trigger controls and measurement binding, then read back a harmless configured condition. | Actual IDs/ancestry and selected sensor/threshold match; missing control or binding is unsupported/unverified. |
| DEFECT-SKIP02 | Run installed-example extraction and live-dependent tests with explicitly configured fixture locations; retain executed/skipped report. | Tests actually execute on the documented environment; absent private/installed fixtures remain explicit skips and are not counted as a pass. |

## NAT18 internal closure and separate live check

Current coordinate-consuming paths are legacy fit_graph/select_graph_measurement/set_graph_fits/analyze_graph and unified fit/select_measurement/analyze. Fit and select schema now accept optional frame_id for compatibility, but runtime rejects coordinate requests without a matching one-use receipt using FRAME_REQUIRED; changed pixels/bounds use STALE_FRAME. This is an intentional tightening: old callers without frame_id must observe_graph first and pass the receipt. No automatic fresh screenshot is substituted for client intent.

The reported toolbox paths use freshly observed semantic controls; graph_delta rejects explicit endpoint positioning rather than silently pretending to apply it. They do not need a caller screenshot for nonexistent coordinate positioning. All reported legacy graph operations and unified manage_graph now preserve potentially-sent-input metadata on transport failure. Unified read is marked nonmutating. Errors after entering a mutating handler conservatively report possible input.

Live NAT18 acceptance: observe a graph, move the window/change its pixels, submit the old receipt, and confirm no click plus STALE_FRAME; capture a new receipt and submit once, then replay and confirm FRAME_REQUIRED. Repeat fit and axis selection with explicit handle. This checks frame admission, not whether an explicit scale-to-fit offset denotes the actual native toolbar action. FitGraphRequest now defaults offset to None; callers must provide an observed offset, and native effect remains unverified without independent state evidence.


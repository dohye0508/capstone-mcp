# Round 2: instrumentation and optical analysis

Scope: offline tests only; no GUI, sensors, Bluetooth pairing, generator output, or calibration was exercised. `fixed-now` means the reproducible Python defect is corrected, not that hardware compatibility is certified. Unsupported findings identify an absent implementation or an audit claim contradicted by current code, not successful hardware operation.

## Instrument and sensor findings

| ID | Disposition | Evidence and remaining boundary |
|---|---|---|
| P0-HW01 | Runtime ledger | Native telemetry ownership belongs to runtime agent; no invented channel RPC. |
| P0-HW02 | Runtime ledger | Native measurement discovery belongs to runtime agent. |
| P0-HW03 | fixed-now | `_step_rate` polls observed rate after one input, bounded by two seconds; delayed and timeout regressions. Actual USB negotiation needs live verification. |
| P0-HW04 | fixed-now | Decimal normalization compares Hz/kHz/MHz and s/ms/us periods in Hz; cross-unit target regression. |
| P0-HW05 | fixed-now | Wireless scan honors finite bounded timeout and accumulates delayed advertisements; deterministic clock regression. |
| P0-HW06 | fixed-now | Pairing requires an explicit unique Connect/Pair button and observed connected state; already-connected devices are not toggled; timeout leaves unresolved drawer open. |
| P0-HW07 | fixed-now | Zero/tare rejects recording before input and checks again before each mutation. |
| P0-HW08 | needs-live | Tare input returns `verified=False`. Hardware completion and clearing the correct telemetry buffer need known sensor-to-measurement identity and actual client ownership; no arbitrary delay or global buffer clear is substituted. |
| P0-HW09 | unsupported | Sensor/measurement trigger selection is not implemented. It now raises before opening or mutating the panel, instead of silently ignoring the measurement. |
| P0-HW10 | fixed-now | Generator state no longer derives from an automation ID containing `On`; missing/ambiguous controls fail. Numeric edit payloads omit forced unit suffixes. Actual device scaling needs live verification. |
| P0-HW11 | Runtime ledger | Native argument and error semantics belong to runtime agent. |
| P0-INST01 | fixed-now | Generator sequential edits, calibration wizard steps, trigger edits, and zero actions reacquire controls after mutations. Native dynamic layout remains unverified. |
| P0-INST02 | fixed-now | Finally cleanup locates current drawer/panel toggle from a new snapshot, avoiding old refs. |
| P0-INST03 | fixed-now | Rate normalization supports equivalent frequency units. |
| P0-INST04 | fixed-now | Reciprocal period units normalize to frequency; unknown units retain strict same-unit comparisons. |
| P0-INST05 | fixed-now | Power observation rejects unknown state and does not search `On` within automation IDs. |
| P0-INST06 | fixed-now | Generator submits unitless numeric edit values; observed readback determines verification. Separate native unit selection is not implemented. |
| P0-INST07 | fixed-now | ComboBox selection resolves actual observed labels; missing choices raise, rather than typing internal enum tokens. |
| P0-INST08 | fixed-now | Keep Sample requires recording and an enabled button, rejects missing manual-value field, and reports unverified receipt (`sample_retained=False`). |
| P0-INST09 | unsupported-as-stated | Exact sensor name selection is an explicit API contract. Guessing a shortened name could select another sensor; use the observed complete name. |
| P0-INST10 | fixed-now | Already-connected sensor short-circuits; ambiguous connection buttons fail before input. |
| P0-INST11 | fixed-now | Null nested requests normalize from flat fields without mutating caller dictionaries; sampling aliases are covered by regression tests. |
| P0-INST12 | fixed-now / unsupported | Actual observed mode/operator labels are used; sensor-threshold configuration explicitly unsupported before mutation. |
| P0-INST13 | unsupported | Measurement selection for sensor triggers remains unavailable; explicit preflight failure replaces silently ignored parameters. |
| P0-INST14 | fixed-now | ComboBox readback uses selected text, never accessible control caption as selected waveform. |
| P0-INST15 | unsupported-as-stated | Battery percentage is optional and remains unknown when no numeric observation exists. No fabricated icon-to-percentage mapping. |
| P0-INST16 | previously-fixed | Sampling-rate failure paths explicitly report restoration unverified; existing post-click and failed-restore regressions prevent false rollback claims. |
| P0-STRM01 | Runtime ledger | Live telemetry buffering owned by runtime agent. |
| P0-STRM02 | fixed-now | Recording TogglePattern COMError becomes a domain AutomationError with original cause and no replay; adversarial COM disconnection regression. Generic native exception envelope already prevented uncaught worker death. |
| P0-STRM03 | unsupported-as-stated | Audited `list_sensors`/`tools/sensors.py` API does not exist. Real disconnection still needs live verification; native exception envelope applies. |
| P0-STRM04 | unsupported-as-stated | Audited `record_interval` API does not exist. Actual run sequence uses bounded `cancellation.wait(duration_seconds)` (validated maximum 3600 seconds), not an unbounded spin. Mid-run physical disconnection remains unverified. |

## Optical findings

| ID | Disposition | Evidence and remaining boundary |
|---|---|---|
| P0-DIFF05 | fixed-now | Contiguous central plateau uses the midpoint of endpoint positions. Noncontiguous maxima, edge peaks, nonpositive peaks and non-increasing coordinates fail. Plateau regression verifies width in mm. This is not detector saturation recovery. |
| P0-DIFF06 | fixed-now | Isolated spike (adjacent samples at most 10% of peak) and asymmetric nearest minima beyond sample resolution fail explicitly. Regression rejects isolated cosmic-ray-like spike. Conservative validation does not recover arbitrary noisy curves. |
| P0-DIFF09 | previously-fixed | Missing minima no longer produce a theoretical slit width; analysis fails. |
| P0-DIFF10 | unsupported | Double-slit analysis explicitly fails; it no longer mislabels the single-slit formula. A genuine double-slit fitter is not implemented. |

## Test-claim findings

Mocks certify the tested contract only, never real UI or hardware compatibility. New adversarial tests cover delayed observations, missing and ambiguous controls, COM disconnection, stopped recording, null aliases, unknown state, and failed wireless confirmation.

| ID | Disposition | Evidence and remaining boundary |
|---|---|---|
| P0-TST01 | unsupported-as-stated | FakeBackend is an explicit testing implementation; no production automatic fallback to it was found. Missing hardware RPC remains unsupported, not implemented by mocks. |
| P0-TST02 | fixed-now / needs-live | ComboBox tests expose actual item labels and selected values; unsupported choices fail. Native IUIAutomationValuePattern exists, but availability on each Capstone widget needs live validation. |
| P0-TST03 | needs-live | Unit tests cannot establish DPI/UIPI or actual desktop rendering behavior. |
| P0-TST04 | fixed-now | Added negative and delayed-state tests beyond dispatcher return-shape assertions; seam contract tests remain valid limited tests. |
| P0-TST05 | fixed-now | Generator verification compares fresh actual readback; fake fixture models separate setting and observed state. Display claims belong to UI ledger. |
| P0-TST06 | previously-fixed | Recipes no longer auto-generate input data or fake setup/acquisition; explicit caller arrays required. |
| P0-TST07 | fixed-now | Generator cannot use accessible captions/IDs as state, unknown drawers fail, mandatory controls required. Display exception handling belongs to UI ledger. |
| P0-TST08 | unsupported-as-stated | Repetition start-error test asserts exact original exception identity, so unrelated exceptions cannot satisfy it. Broader assertions elsewhere are test-quality work, not evidence of a production P0. |
| P0-TST09 | unsupported-as-stated | `test_domain_protocol.py` contains unconditional real stdio subprocess MCP tests, including linear fit. Actual desktop E2E remains intentionally live-only. |
| P0-TST10 | previously-fixed | Golden-master directory can be configured via CAPSTONE_GOLDEN_MASTER_DIR; root validates local real capfile corpus separately. Private fixtures are not published. |
| P0-TST11 | needs-live | Installed-app smoke tests require explicit opt-in and are intentionally skipped for this offline-only request. |
| P0-TST12 | UI ledger | Calculator verification limits are addressed by UI agent. |
| P0-TST13 | UI ledger | Popup observation timing owned by UI agent. |
| P0-TST14 | Root ledger | File workflow atomicity and result validation owned by root. |
| P0-TST15 | Runtime ledger | Actual worker lifecycle and protocol checks owned by runtime agent. |
| P0-TST16 | Runtime ledger | Wire-level bridge tests owned by runtime agent. |
| P0-TST17 | fixed-now | Sampling rate tests model delayed UI observation and bounded failure, not immediate echo-only success. |
| P0-TST18 | needs-live | Same-process WinEvent fixtures do not prove external Capstone event delivery. |
| P0-TST19 | Runtime ledger | Existing stderr tests already bound joins and close worker in finally; runtime agent adds lifecycle coverage. |
| P0-TST20 | Runtime ledger | Deterministic sequencing tests are not hardware certification; runtime cancellation/concurrency tests handled separately. |
| P0-TST21 | UI ledger | Graph control discovery owned by UI agent. |
| P0-MOCK01 | UI ledger | Calculator observation owned by UI agent. |
| P0-MOCK02 | needs-live | Fake digit-display IDs do not establish native identity. No invented native IDs added. |
| P0-MOCK03 | fixed-now / needs-live | Trigger option selection requires observed labels, sensor trigger unsupported explicitly, and mutation returns unverified; actual native identities still need live evidence. |
| P0-FIX02 | Runtime ledger | Intentionally hanging worker fixture supports bounded timeout/cleanup tests; runtime agent audits teardown. |
| P0-SKIP01 | previously-fixed | Golden-master path configurable; absent private corpus produces intentional skip. |
| P0-SKIP02 | Root ledger | Installed sample/corpus discovery handled with offline file validation. |

Validation: targeted instrumentation/recipe tests, ruff, and basedpyright; exact final count is reported in the parent completion record. No live hardware claim is made.

## Report input follow-up

- DEFECT-REP03 (Critical): fixed-now. Plot entry validates finite source and fit values, bounds and derived spans; overflowing bounds raise clear ValueError before rendering. Summary/regression/error-analysis also reject nonfinite values.
- DEFECT-REP07 (Critical): fixed-now. Inline JSON is detected before path heuristics, including leading whitespace and slash-bearing channel names. JSON/CSV/capfile loaders no longer suppress arbitrary exceptions into empty data; malformed source diagnostics remain visible.
- DEFECT-REP08 (Critical): previously-fixed / regression-protected. Zero-variance fit explicitly raises ValueError; no theoretical or dummy fit substitutes for it. Transport error envelope belongs to runtime verification.
- DEFECT-REP09 (Major): fixed-now. NaN/Infinity in report source series is rejected before statistics or preview calculation, including all-NaN input. No fabricated zero summary replaces invalid measured input.
- DEFECT-WF23: fixed-now by runtime owner. Exact mutating Keep Sample routes through the active recording backend under its command lock; conflicting handles fail. Hardware sample retention remains unverified. See runtime ledger and its 11 focused regressions.

## Distinct numerical audit IDs

These DEFECT-NUM IDs are distinct from P0-NUM01 (linear SI-scale regression) and P0-NUM02 (adiabatic input validation); do not merge their statuses by suffix.

- DEFECT-NUM01: fixed-now. SVG title is escaped as XML text. Adversarial title containing tags, `<`, and `&` round-trips with no script element.
- DEFECT-NUM02: fixed-now. Both fitted coordinate arrays must be supplied with matching lengths and finite values before SVG bounds/rendering.
- DEFECT-NUM03: fixed-now. ASCII source coordinates and derived spans must be finite; unsupported dimensions fail explicitly.
- DEFECT-NUM04 / DEFECT-NUM05: fixed-now. Polynomial fitting centers/scales x and scales y, uses reorthogonalized QR rather than raw normal equations, and rejects singular/unresolved design. Decimal basis composition avoids intermediate overflow when restoring original coefficients; unrepresentable output coefficients fail explicitly. Tests cover x scales 1e-100 through 1e100, translated x, y scale 1e200, repeated-coordinate singularity and true coefficient overflow. Original-basis evaluation may still be ill-conditioned for extreme translations; no universal high-degree accuracy guarantee.
- DEFECT-REP10: fixed-now by report finite source/fit/span validation; explicit ValueError rather than integer-conversion crash.
- DEFECT-REP01: previously-fixed synthesis opt-in; loader error suppression removed now.
- DEFECT-REP04: previously-fixed report computation/file I/O offloaded to thread; root verifies actual MCP wire handling.

Final numerical review: original-basis coefficients are additionally evaluated with Horner at input samples and compared with the normalized fit in y-scaled units. Error tolerance is sqrt(machine epsilon) times polynomial size/normalized signal magnitude plus residual RMS; this reserves roughly half binary precision for conversion. The x=1e12+i, y=i² case now raises explicit numerical-instability ValueError instead of returning coefficients whose float predictions disagree despite normalized R²=1. Moderate translation and extreme representable scaling continue to pass. This is a fail-closed restriction, not a promise of stable extrapolation outside observed coordinates.

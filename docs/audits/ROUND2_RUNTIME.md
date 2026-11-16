# Round 2 runtime P0 evidence ledger

Scope: offline internal verification only. No Capstone GUI, sensor, or real debug-port operations were performed. `fixed-now` means the stated internal defect has a regression; it does not certify hardware behavior. Paths below are repository-relative. Cross-owner findings remain explicit rather than being counted twice.

| Finding | Disposition | Evidence / remaining boundary |
|---|---|---|
| NAT01 | unsupported/false | native bootstrap sets `sys.coinit_flags=0` (MTA) before pywinauto; report assumes STA. Do not add an unproven COM pump. |
| NAT02 | requires-live | automation_worker bounds requests and retires its own worker; actual stuck COM call and physical operation outcome cannot be established offline. No automatic action replay. |
| NAT05, NAT06, WF11 | previously-fixed; extended now | native errors use narrow matching; missing error_code is normalized. New timeout/domain precedence tests preserve public error codes. |
| NAT09 | cross-owner | desktop cached-window identity validation belongs to UI ledger. |
| NAT10 | unsupported/false | initialize_recording production caller is RemoteRecordingBackend using a dedicated worker, not the shared desktop session. |
| NAT13 | fixed-now | native `_json` validates JSON-mode model_dump directly instead of serializing and parsing; Decimal/tuple regression preserves wire values. P0 memory exhaustion claim not measured. |
| NAT18 | fixed-now internal admission/uncertainty | Unified fit/select now expose optional frame_id and require fresh receipt before coordinate input; analyze existing receipt remains enforced, legacy fit now guarded. Reported legacy and unified graph transport errors preserve possible-input metadata. Semantic-control toolbox operations are distinguished from caller coordinates; unsupported delta endpoints already fail closed. See RUNTIME_REMAINING_LIVE_PLAN.md for tightened caller contract and live acceptance. |
| NAT19 | fixed-now | foreground/focus failures give AUTOMATION_ERROR with reacquisition guidance, not invalid-coordinate guidance. |
| NAT25 | unsupported/false as global-hook claim | SetWinEventHook supplies target process_id. Broad events within that process need live profiling before narrowing event coverage. |
| NAT26 | fixed-now | pump now TranslateMessage/DispatchMessage for retrieved messages; GetMessage -1 terminates with error. Fake Win32 queue test verifies dispatch. Real external event delivery remains untested. |
| CONC01 | unsupported/false | request is drained before response; stderr has independent reader. Real worker subprocess transfers approximately 1 MB Unicode request/reply. This does not prove unlimited payload capacity. |
| CONC02 | fixed-now | cancel synchronous I/O only on owned reader/transport thread handles, bounded joins, then stream close; handle cleanup in finally. Real fixture child inheriting pipe exercises formerly stuck close path. |
| CONC04 | unsupported/false | nonblocking admission is intentional; AnyIO shielded thread execution retains mutation reservation after cancellation. Actual held Python thread test verifies a second mutation is rejected until first exits. |
| CONC08 | previously-fixed; extended now | resources offload blocking reads; active runs snapshots registry under lock without calling observe on pending jobs. |
| SEC01, BR03 | previously-fixed | unit_type requires exact int and EUID uses JSON encoding; no public arbitrary JavaScript parameter. |
| SEC02 | previously-fixed; extended now | wildcard debug origin removed earlier. Bridge now verifies exact configured executable owning loopback listener before discovery and again after connection; validates endpoint host/port and credentials. Ownership tests mock psutil explicitly. |
| SEC04 | unsupported/false | callback local remains rooted by active pump frame until finally unhooks; report's premature GC premise does not match lifetime. |
| SEC05 | previously-fixed | hook setup and message-only window cleanup guarded by finally. |
| SEC09 | cross-owner | desktop executable environment override validation is UI owner's patch; not claimed hardcoded-safe. |
| SEC13, SEC14, SEC16 | cross-owner | archive traversal/ADS/decompression limits covered by root parser changes. |
| TEL01 | unsupported/false | current telemetry store has no MAX_MEASUREMENTS=256 channel eviction. |
| TEL02 | unsupported/false eviction premise; cross-owner actual metadata defect | current live adapter metadata normalization is root's patch; no fabricated historical sensor stream. |
| TEL03 | unsupported/false | current instantaneous live adapter does not sort tuple samples as alleged. |
| TEL04 | unsupported/false | current adapter does not recompute rolling relative-time origin as alleged. |
| TEL05 | previously-fixed; contract limitation | finite/monotonic timestamp and positive limit validation exist. Arbitrary float timestamps cannot reveal their physical clock origin without an explicit source contract. |
| TEL06, BR01, HW11 | fixed-now | bounded per-port connection pool, serialized request correlation, close integration at app lifespan, disconnect invalidation and no replay after uncertain failure. Real local WS tests verify reuse/reconnect. Report's port-exhaustion arithmetic alone was not proof. |
| TEL07 | unsupported buffer-drain premise; improved now | recv consumes events; irrelevant events/reply IDs skipped before response-schema validation. No invented push subscription. Fragmented/event-interleaved wire test exercises drain. |
| TEL08 | unsupported P0 claim | locked copies bounded by store capacity, sample_count O(1); no starvation reproduction supplied. Per-channel locking requires measurement, not speculation. |
| TEL09 | fixed-now | watcher subtracts sampler time from cadence, bounds waiting to deadline and supports cancellation. Offloaded resource paths prevent event-loop network blockage. Slow sensor cannot be promised 20 Hz. |
| BR02 | unsupported overflow premise; regression added | websocket library reassembles frames and enforces explicit size limit; >64 KB fragmented Korean reply passes real wire test. Protocol/disconnect errors normalized without replay. |
| BR04 | fixed-now | halt callback finally executes once on success/cancel/error/timeout; finite timing validation, no fabricated pre-cancel value. Arbitrary sampler cannot be force-interrupted; bridge transport is bounded. |
| BR05 | unsupported unsafe ownership inference | lifecycle manager borrows a worker and has no production terminate callers. Clarified docstrings; it must not kill the user's Capstone process. |
| PROTO01 | fixed-now | discovery accepts only validated loopback same-port ws URL and normalizes hostname to 127.0.0.1; local wire server advertises localhost to test this. |
| PROTO02 | unsupported worker-kill premise | worker lock rejection occurs before retirement exception handling; test asserts contention does not retire. HTTP session lifetime defect is separately fixed below. |
| FASTMCP-01 | fixed-now | timeout precedence, input-validation precedence, narrower missing-file matching; explicit TimeoutError handling. |
| FASTMCP-02 | fixed-now | streamable HTTP application owns shared resources; per-session lifespans borrow through ContextVar. Actual ASGI initialize/delete/ping two-client test verifies deleting one leaves other alive; shielded cleanup runs on outer exit. |
| FASTMCP-03 | previously-fixed / root extension | tools.physics macro runs blocking work in anyio.to_thread.run_sync. |
| FASTMCP-04 | fixed-now content loss | error wrapper replaces first text only, retains images/other text/metadata and structuredContent. Internal SDK interception remains version-sensitive and covered by contract tests; not falsely declared public API. |
| FASTMCP-05 | fixed-now | active display resource obtains exactly one actual visible window handle or returns explicit ambiguity/error; no handle=0 and no silent empty-success fallback. |
| HW01, HW02, STRM01 | requires-live/interface evidence | RequestReadMeasurement is instantaneous polling; no observed hardware timestamp or bulk-stream endpoint contract. Cannot promise 100 kHz, synchronized channels, or invent interpolation/USB RPC. Root adapter rejects unsupported timestamp semantics. |
| STRM02, STRM03 | cross-owner | acquisition COM normalization/sensor read errors in instruments ledger; worker error envelope also prevents unhandled errors from escaping protocol. |
| STRM04 | unsupported/false | alleged record_interval function absent; run_sequence uses bounded Event.wait(duration). See instruments ledger. |
| WF23 | fixed-now | Exact mutating keep_sample borrows active job worker; target handle is validated/resolved to that job. Backend command lock serializes sample with observe/stop/save/close; closed owner rejects input. Other mutation guards remain. Real thread regressions verify stop/save cannot overlap sample; hardware retention remains unverified. |
| WF24 | unsupported/false | analyze_graph changes axes and fit selections, so mutation reservation is necessary; report calls it read-only incorrectly. |
| RUN-P3-01 | fixed-now | Native dispatcher resolves default handle=0 for the selected nested unified run/graph/display/instrument action, plus legacy run operations, only when exactly one visible window exists. Explicit handles remain unchanged; zero/multiple windows fail before dispatch. Graph frame receipt checks remain mandatory. tests/test_default_window.py covers all run actions and other unified defaults. |

## Test and fixture findings

| Finding | Disposition | Evidence / limitation |
|---|---|---|
| TST01 | requires-live | fake backend validates state-machine logic, not claimed 96% native parity; actual RPC/COM parity needs real observed application. |
| TST02, TST03 | requires-live; cross-owner unit improvements | real ValuePattern/DPI/UIPI existence cannot be established by mocks; UI tests cover explicit denied/fallback behavior only. |
| TST04 | unsupported universal claim | seam assertions test dispatch routing, not all native functionality; new wire/lifetime/failure tests complement them instead of treating them as physical evidence. |
| TST05 | cross-owner | unverified success reporting corrected in UI/instruments ledger. |
| TST06 | previously-fixed / instruments | fake synthetic recipe success removed; optical/internal math regressions do not certify equipment. |
| TST07 | fixed-now resource failure; cross-owner rest | display resource errors no longer silent; UI/instruments suppressed failures audited separately. |
| TST08 | unsupported universal claim | broad exception tests do not demonstrate every unrelated failure passes; new tests assert exact codes/side effects/messages. No claim all historic tests are exhaustive. |
| TST09 | unsupported only-protocol premise; improved now | offline domain protocol tests existed; actual HTTP ASGI two-session and real WS wire tests added. Live protocol remains explicit opt-in. |
| TST10, SKIP01 | cross-owner | corpus path configurable in root work; private experimental artifacts not published as CI fixtures. Portable parser fixtures provided separately. |
| TST11, SKIP02 | requires-live for installed app; cross-owner parsers | no GUI/sensors means live smoke remains opt-in, not falsely passed. Offline extraction fixtures/root protocol tests cover their actual contract. |
| TST12, MOCK01 | previously-fixed; requires-live acceptance | calculator reports unverified unless observed; actual Qt acceptance requires application evidence. |
| TST13, TST14 | requires-live; cross-owner internal fixes | menu rendering and file dialog automation cannot be certified by fake controls; UI ledger covers local race/preflight contracts. |
| TST15 | fixed-now coverage gap; live boundary retained | real spawned fixture worker now exercises large bidirectional pipe transfer, inherited pipe ownership and timeout cleanup; does not emulate COM. |
| TST16 | fixed-now | real ephemeral localhost HTTP+WS server with fragmented replies, events, request IDs, disconnect/no replay, pooling, concurrency. Only ownership verification is mocked explicitly. |
| TST17 | requires-live | actual hardware negotiation latency cannot be proven by settings FSM; instruments ledger has conservative verification behavior. |
| TST18 | requires-live | same-process Win32 tests validate wrapper mechanics, not external Capstone delivery; no new external GUI created. |
| TST19 | fixed-now | stderr tests join reader at EOF with deadline instead of timing sleeps; guaranteed worker cleanup in finally. |
| TST20 | fixed-now internal concurrency | real Python worker thread held across cancellation; reservation lifetime and contention verified. Physical stop outcome still requires hardware. |
| TST21 | cross-owner | graph semantic-control/coordinate safety in UI ledger. |
| FIX02 | fixed-now | fixture Event waits bounded to 30 seconds; inherited helper is killed only after verified fixture command identity in finally. |
| FIX01, FIX03 | P1, not silently counted P0 | directory layout alone no correctness defect; FIX03 finally cleanup corrected alongside TST19. |
| MOCK02, MOCK03 | requires-live; cross-owner guards | actual Automation IDs require observed UI evidence; no guessed production IDs introduced. |

Validation: 97 scoped tests passed before final NAT18 addition; runtime_round2 subsequently 16 passed including NAT18. Includes real fixture subprocesses and ephemeral local mock sockets only. Final root aggregate checks and CI remain necessary before merge.


Historical baseline note: the table above records the pre-b11dd2a code. Upstream later added MAX_MEASUREMENTS=256 and a history adapter, so the earlier TEL01/TEL03/TEL04 statements about absent code no longer describe the merged implementation. The merged LRU/clock/ordering/origin contract and regressions are recorded in ROUND3_TELEMETRY.md; TEL05 is now explicitly enforced rather than an open timestamp-origin policy gap.

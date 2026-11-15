# Round 2: archives, text data, and offline MCP tools

Baseline: upstream `5c1c84d`, with the first offline remediation series applied. Tests never open Capstone or operate sensors. `fixed-now` identifies a reproduced defect and regression test, not native format or hardware certification.

| Finding | Disposition and evidence |
| --- | --- |
| CAP01 / SEC16 | Unsupported as stated: Python ZIP reading enforces declared member length; existing member, total, ratio, and decoded-record limits remain. No universal memory-safety claim. |
| CAP02 / SEC13 / SEC14 | Hardened: reject colons in every archive path component. No archive members are extracted to disk, so the reported ADS/ZipSlip write exploit was not reproduced. |
| CAP03 | Needs native format evidence: retain verified boolean representations; no corpus evidence establishes mixed-case `True` as a supported native representation. |
| CAP04 | Unsupported multi-segment format: explicit rejection remains. Concatenating segments without verified alignment semantics would corrupt data. |
| CAP05 | Fixed-now: a zero-sample dataset may omit its dependent payload filename. Nonempty datasets still require payload identity. |
| CAP06 | Unsupported as stated: read-only corpus tests compare saved run names and numbers directly with native RunParameterSet attributes. |
| CAP07 | Needs native format evidence: do not strip counted NUL characters without evidence that they are terminators rather than stored values. |
| CAP08 | Fixed-now: nonfinite numeric text remains exact in raw_values and maps to missing numeric values. Invalid finite-number syntax still fails. |
| CAP09 / CAP10 / STRS01 | Fixed for the public page/list path: list metadata without decoding payloads; select one dataset before sample decoding; allocate only the requested numeric/text/coordinate page. ZIP payload decompression and text-record traversal remain bounded but are not random access. Full-archive reads remain eager under aggregate budgets. |
| CAP11 | Previously fixed: absent or ambiguous channels fail, and run/sample identity is checked. NFC matching added without arbitrary language aliases. |
| CAP12 | Fixed-now with explicit semantics: adapter x_name=`@independent` selects saved coordinates. Units remain unknown; interval coordinates are never silently called seconds or substituted for a missing named Time channel. |
| CAP13 | Unsupported as a correctness defect: counting declared directory sizes conservatively is a deliberate archive budget policy. |
| CAP14 | Unsupported as stated: building the parent lookup visits each tree edge once, not O(N squared). |
| CAP15 | Previously guarded: orphan datasets raise CapFileError before source lookup. |
| CAP16 | Unsupported as stated: metadata traversal has an explicit maximum depth of 128. Sibling count does not multiply recursion depth. Archive XML size remains bounded. |
| CAP17 | Needs native schema evidence: dependent and independent storage fields are separate; no real corpus failure demonstrates the alleged filename confusion. |
| CAP18 / CAP19 | See UI/workflow ledger for capture-baseline validation. |
| CAP20 | Unsupported as stated: local imports do not establish a circular-import defect; adapter and actual stdio import tests execute successfully. |
| CAP21 | Previously fixed and extended: negative/huge counts, bounds and page offsets are tested; stored interval arithmetic matches full decode. |
| CAP22 | Wire behavior verified: a corrupt archive returns isError with error_code/message/remediation in an actual stdio MCP session. No raw traceback is returned. |
| ENC01 / ENC02 / ENC03 / ENC04 | Fixed-now: page, series, metadata and report CSV readers share strict UTF-8/BOM-UTF-16/CP949 decoding. Invalid bytes produce a domain error. |
| ENC07 / ENC08 | Fixed underlying behavior: CSV-aware comma/semicolon/tab detection and quoted decimal-comma parsing. Ambiguous/ragged tables fail; thousands separators are not guessed. Some function names quoted in the audit do not exist in the baseline. |
| ENC13 | Fixed-now: table numeric cells share decimal-comma parsing; text stays text and nonfinite values stay missing. |
| ENC15 | NFC/NFD matching fixed. Exact Korean headers already worked; no unsupported promise of translating arbitrary synonyms. |
| ENC16 | Fixed-now: Korean index aliases are explicit; actual named Korean time channels resolve through normalized inventory names. Missing physical time is never fabricated. Actual native MeasurementName/MeasurementEUID/Unit inventory keys are accepted. |
| WF03 | Explicit product behavior: allow_foreground is an exposed opt-in/default policy, not an accidental parser defect. Changing its default needs a user-facing API decision. |
| WF04 / WF21 | Previously fixed: exclusive report creation and off-thread report work. |
| WF05 | Product boundary: this local workstation server intentionally reads user-selected paths. No invented workspace allowlist is imposed. Native save/export paths remain no-overwrite. A remote multi-user authorization policy is outside this offline compatibility fix. |
| WF08 | Fixed-now: capstone_guide is registered and callable over stdio; public tool count remains at most 22. |
| WF09 / WF10 | Error envelopes verified. Plot/fit/comparison tools are now async with numerical work off the event-loop thread. |
| WF11 | Runtime ledger: native errors have stable structured envelopes. |
| WF20 | Fixed-now: archive configuration, metadata and page tools offload file/parse work. A thread-identity regression verifies the actual registered tool. |
| WF19 | Unsupported immediate-read premise: native export waits for FileEvents.ready, which opens the file with read-only sharing and rejects an active writer before returning the artifact. Existing real temporary-file tests cover an open writer and other readers. External processes reopening the completed output and physical flush timing are not certified. |
| WF23 / WF24 | Runtime/UI ledgers: mutation ownership and recording guards require explicit semantics; no bypass by pretending a mutating action is read-only. |
| TST09 / SKIP02 | New unconditional actual stdio tests use synthetic archives; private installed examples remain optional. Synthetic protocol tests do not certify the desktop. |
| TST10 / SKIP01 / SKIP03 | Configurable read-only real corpus; a former hardcoded Downloads test that silently passed without a file now uses an unconditional synthetic adapter fixture. |
| TST14 | UI/workflow ledger; offline fixtures do not prove native dialogs. |
| P0-WIN03 | Unsupported missing-bootstrap premise: native_main.main calls init_dpi_awareness before importing the native runtime. Actual mixed-DPI interaction still requires a real desktop session. |
| P0-NUM01 / P0-NUM02 | Previously fixed normalized linear regression and explicit rejection of invalid adiabatic data. Distinct DEFECT-NUM01 through DEFECT-NUM05 findings are covered in the instruments/analysis ledger. |

## Validation scope

- Synthetic page/full comparisons cover numeric and text storage, exact raw decimals, interval coordinates, out-of-range pages, malformed members and nonfinite values.
- A 50,000-sample allocation regression verifies that a two-sample page retains substantially less memory than full decode.
- With CAPSTONE_GOLDEN_MASTER_DIR configured, all 34 supplied archives are checked read-only. Metadata counts and last-page raw/numeric/independent/sample-index arrays match full parsing, and SHA-256 is unchanged afterward. No private archive is committed.
- CSV cases cross three encodings and three delimiters, including Korean decomposed Unicode headers, quoted delimiters, missing cells and ambiguous names.
- Adapter float overflow and zero-underflow fail explicitly instead of creating infinity, silently zeroing values or dropping entire columns.

The corpus does not establish support for unobserved multi-segment encodings, alternate native boolean syntax, physical sensor timing, UI localization, or high-rate acquisition.

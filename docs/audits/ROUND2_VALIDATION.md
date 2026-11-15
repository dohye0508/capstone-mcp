# Round 2 integration validation

The combined offline remediation branch `codex/p0-offline-round2`, commit `72f6686`, passed **910 tests with 7 skipped** on Windows Python 3.12. Full Ruff and Basedpyright checks also passed. The corpus directory was supplied through `CAPSTONE_GOLDEN_MASTER_DIR`; `CAPSTONE_RUN_LIVE_TESTS=0`.

The seven skips are the explicitly disabled live tests and measurement-only cases for settings-only gyroscope files. All 34 supplied private `.cap` files were read without modification; metadata and paged samples were compared to full decoding. No original experiment file is part of these commits.

This is an integration result, not the test count for any single PR. The patches are distributed across runtime #131, parser #132, analysis #133, UI/tools #134, data #135, and the separate instrument-observation PR. Each PR also requires independent GitHub Actions CI success. The common CSV decoder is shared identically by #134 and #135.

The final full run follows correction of two outdated test contracts and a fixture-only process-start race. The crashing stderr fixture now waits for its request before exiting, so it tests crash diagnostics instead of racing Windows Job Object attachment. Existing clipboard unit coverage that reached the real API was changed to an explicit mock; new clipboard tests do not access the user's clipboard.

Refer to the ROUND2_RUNTIME, ROUND2_FILES_PROTOCOL, ROUND2_INSTRUMENTS_ANALYSIS and ROUND2_UI_WORKFLOWS ledgers for per-finding evidence. Some files live in their corresponding PR until the series is integrated. Findings requiring native UI snapshots, mixed-DPI/locale validation, sensor timing or new hardware RPC contracts remain explicitly unresolved. Unsupported capabilities fail or return unverified receipts; they are not counted as successfully implemented hardware features. The broad epic issues are not automatically closed.

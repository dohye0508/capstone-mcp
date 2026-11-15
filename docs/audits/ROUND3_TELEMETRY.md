# Round 3 telemetry clock contract and native evidence

## TEL05: internally fixed

`TelemetryClock` now declares `clock_id`, `unit`, and `origin`. Explicit `push_sample(..., timestamp=...)` must also supply this immutable clock. Automatic host timestamps use a buffer-owned monotonic clock identity in seconds and explicitly do not claim hardware timing. Domain, unit, or origin changes within a retained channel fail before mutation, even if the new numeric timestamp increases. Eviction preserves the original clock; clearing a channel clears its provenance. No guessed clock conversion or zero rebasing occurs.

Migration: callers that previously supplied bare timestamps must construct `TelemetryClock(clock_id="device-or-import:run-identity", unit="seconds", origin="documented acquisition origin")` from their actual source contract and pass `clock=...`. Calling code must not use that example identity for unrelated devices or runs. The only production writer currently supplies no timestamp and therefore retains host observation behavior. Explicit fixture timestamps were updated accordingly.

`get_snapshot(euid)` exports an atomic copy of both timestamped samples and their clock under one lock. `get_clock(euid)` exposes immutable provenance for diagnostics; `get_samples` remains a compatibility value-only accessor and must not be used to infer shared time domains. The live data adapter exports instantaneous values rather than buffer timestamps: metadata now states `sampling=sequential_instantaneous`, `synchronized=false`, and `timestamps_exported=false`. It does not claim paired synchronous acquisition.

Tests: `test_telemetry_clock.py` covers missing metadata, changed domain/unit/origin, automatic/external clock mixing, eviction, clearing and snapshot independence. Existing finite/monotonic/limit and adapter safety tests continue to execute.

## Read-only installed native evidence (no process access)

Inspected installed `C:/Program Files/PASCO scientific/Capstone/Resources/www/javascripts/capstonelibrary.js`, SHA-256 `512A4E7F6379D0EDAFD195A5CA330BA7EBD0697BF486DE03190788E51610A0F7`, plus repository `docs/reverse_engineering_dump.json`. No native service was called. The installed JavaScript is evidence of this particular installation, not a universal vendor API specification.

- `RequestReadMeasurement` constructs one request with ViewModelID, ReadMeasurement function, measurementEUID and unitType. No timebase, sample count, bulk offset or timestamp argument exists in that wrapper.
- `RequestSensorsAndMeasurements` calls the inventory function. The repository dump's captured test result contains empty sensor/measurement arrays, so it establishes no real sensor-to-measurement mapping.
- The generated code includes a ZeroSensor command using sensorEUID, and the local enum assigns ZeroSensor 44. This establishes a dispatch vocabulary, **not** a completion acknowledgement, settled-value criterion, timestamp epoch reset, or safe sensor mapping. No new command was added from the enum alone.
- StartCondition/StopCondition and related threshold/behavior names occur as vocabulary constants. No matching selector request implementation, read-back contract or sensor binding was found in the searched client wrapper. Constants alone are insufficient to implement trigger mutation safely.
- The searched wrapper has no GetSamples/GetData bulk acquisition method and no measurement timestamp field. This is a bounded search result, not proof that no native binary API exists.

## Per-ID disposition

| Original ID | Disposition after this work | Exact remaining evidence requirement |
| --- | --- | --- |
| DEFECT-TEL05 | Fixed internal source contract | None for internal mixing prevention. External producers remain responsible for truthful clock metadata. |
| DEFECT-HW01 | Unsupported hardware timestamp capability | Actual native acquisition response or documented export provides hardware clock identity, origin and units. Current read-measurement wrapper cannot establish them. |
| DEFECT-HW02 | Unsupported synchronized channel capability | Native sample identifiers/timestamps and an explicit alignment contract. Sequential instantaneous measurements are now labeled unsynchronized. |
| P0-STRM01 | Unsupported bulk streaming capability | Documented or captured bulk request/response and rate/count semantics. No invented endpoint or claim of 100 kHz support. |
| DEFECT-HW08 | Partial: safe admission/unverified result already implemented; completion unsupported | ZeroSensor vocabulary exists, but sensor-to-measurement mapping and settled/finished acknowledgement are absent. Current zero tool rejects recording and reports completion unverified. UI request has sensor_name rather than authoritative EUID; private per-adapter buffers have no global ownership registry. Clearing every client's buffer would silently destroy unrelated data. |
| DEFECT-HW09 | Unsupported trigger binding, fails before mutation | Native sensor-selection/control evidence and independent selected-measurement readback. Inventory dump is empty, property names alone do not establish selection semantics. |
| DEFECT-INST12 | Partial supported mode/operator behavior; sensor-threshold portion unsupported | Existing tests verify exact observed mode/operator labels; no sensor-binding contract for threshold configuration. |
| DEFECT-INST13 | Unsupported trigger measurement selection, fails before mutation | Same missing selector/read-back contract as HW09; no guessed Automation IDs or RPC fields added. |
| DEFECT-NAT02 | Claim verification, not reproduced unbounded worker | Existing real subprocess tests verify bounded request timeout and owned cleanup. Actual blocked COM operation and physical outcome require authorized controlled live evidence; host timeout cannot prove cancellation of equipment state. |

No GUI, sensor, trigger, output, or actual debug endpoint operations were performed. No additional speculative native implementation was introduced.

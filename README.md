<img src="assets/icon.svg" width="64" height="64" alt="">

# Capstone MCP

Local Windows MCP server for PASCO Capstone UI control, experiment-file
inspection, numeric extraction, and analysis. IDA is an investigation tool,
not a dependency of this server.

## Run

Requires Windows with an unlocked interactive desktop, Python 3.12+, and `uv`.
The configured executable is
`C:/Program Files/PASCO scientific/Capstone/Capstone.exe`.

```powershell
uv sync --python 3.12
uv run capstone-mcp
```

For local HTTP clients, run `uv run capstone-mcp-http` and connect to
`http://127.0.0.1:8766/mcp`. It binds only to loopback. Do not expose this
desktop-control server to a network or use concurrent controlling clients.

The server speaks MCP over stdin/stdout. Add this entry to your MCP client's
configuration (adjust the directory on other machines):

```json
{
  "mcpServers": {
    "capstone": {
      "command": "uv",
      "args": [
        "--directory", "C:/Projects/capstone-mcp",
        "run", "capstone-mcp"
      ]
    }
  }
}
```

## Operation

1. `capstone_attach(launch=true)` starts or attaches to the installed executable.
   The returned window list can be empty during application startup; the process
   is already attached. Call `capstone_windows` after startup to obtain handles.
2. `capstone_windows` lists the process's visible windows, including dialogs.
3. `capstone_snapshot(handle)` returns control references, names, roles, bounds,
   and visibility. `truncated=true` means the depth or node budget omitted data.
4. Use `capstone_action(ref, action)` for toggle, select, expand, collapse,
   or focus. `action="invoke"` activates the named control by a physical click
   and requires `allow_foreground=true`. `capstone_set_value(ref, value)` sets
   literal text through UIA; `capstone_read_value(ref)` reads it back.
5. Inspect again after each action. References expire on actions and snapshots.

Capstone's UIA InvokePattern can block all accessibility queries while a modal
dialog remains open. Named-control activation therefore uses a physical click,
not InvokePattern. It reports input delivery, not application success.

`capstone_screenshot(handle)` returns a PNG at native pixel resolution.
`capstone_click(handle, point={"x":100,"y":100}, allow_foreground=true)` uses
window-relative pixels. It supports `button` and `double`.
`capstone_keys` uses pywinauto key syntax, such as `^o`, `{ENTER}`, and `{ESC}`.
`capstone_type_text` escapes shortcut characters for literal Unicode input.
Physical mouse and keyboard tools require `allow_foreground=true` because
they change focus and share the user's desktop.

When multiple Capstone instances exist, pass `process_id` to `capstone_attach`.
The process image is checked against the installed executable. Windows may refuse
foreground activation; in that case activate the intended Capstone window
manually before retrying input.

## Experiment data and analysis

| Tool | Output |
| --- | --- |
| `capstone_inspect_file(path)` | Saved hardware, sensor sampling configuration, recording conditions, source metadata, workbook structure, and calculations |
| `capstone_file_datasets(path)` | Dataset indices, IDs, source names, numeric unit IDs, and sample counts |
| `capstone_extract_dataset(path, dataset_index, offset, limit)` | A bounded page of actual stored values and sample indices |
| `capstone_live_configuration(debug_port)` | Native runtime sensor and measurement metadata from the selected Capstone debug instance |
| `capstone_current_value(measurement_euid, unit_type, debug_port)` | One native current numeric value, or an explicit unavailable-value error |
| `capstone_linear_fit(samples)` | OLS slope, intercept, standard errors, residual error, and R-squared |
| `capstone_compare_runs(runs)` | Means, sample standard deviations, ranges, and mean differences for supplied runs |
| `capstone_plot(samples)` | Standalone PNG scatter plot with optional OLS line; does not modify workbook pages |
| `capstone_recording_status(handle)` | Actual recording toggle, enabled state, and displayed time/rate |
| `capstone_set_recording(handle, recording, allow_foreground)` | Idempotent start/stop request with observed state and an explicit pending-transition flag |
| `capstone_step_sampling_rate(handle, direction, expected_sensor, allow_foreground)` | One native increase/decrease step for the named selected sensor, with before/after values |
| `capstone_repeat_acquisition(plan)` | Background repeated acquisition job with native event confirmation |
| `capstone_acquisition_job(job_id)` | Completion state, confirmed-cycle timing receipts, or failure |
| `capstone_cancel_acquisition(job_id)` | Interrupt acquisition timing and request a confirmed stop |

File inspection does not open or modify the document in Capstone. Numeric
extraction supports dependent type 7 strings and type 0 tagged doubles, with
independent type 0 stored doubles, type 1 intervals, or type 4 implicit indices.
Offsets and missing/invalid numeric tags are preserved as values or nulls.
Nonempty interval attribute exceptions, legacy string aliases, and other
encodings fail explicitly. Configuration inspection does not require a supported
array encoding.

Exact decimal values are serialized as decimal strings alongside original text.
Independent coordinates are returned separately with their storage kind.
Implicit sample indices are **not timestamps**. Numeric unit IDs are retained
without guessing unit symbols. Select matching runs and units before fitting or
comparing arrays; unequal x/y lengths and nonfinite inputs are rejected.

```json
{
  "samples": {
    "x": [0, 1, 2, 3],
    "y": [1, 3, 5, 7],
    "title": "Measurement",
    "x_label": "Time (s)",
    "y_label": "Position (m)",
    "show_fit": true
  }
}
```

The example is input for `capstone_plot`. `capstone_linear_fit` takes only the
`x` and `y` arrays inside `samples`. OLS standard errors assume independent,
equal-variance residuals; they are not sensor calibration uncertainties.

### Native runtime bridge

File tools and local analysis do not need this setup. Live bridge tools require
Capstone started with a loopback Qt debugging endpoint. Save and close the
existing application before starting the intended instance:

```powershell
$env:QTWEBENGINE_REMOTE_DEBUGGING = "127.0.0.1:9223"
Start-Process "C:/Program Files/PASCO scientific/Capstone/Capstone.exe"
Remove-Item Env:QTWEBENGINE_REMOTE_DEBUGGING
```

The bridge matches the local Sense and Control resource page. It is an
undocumented interface observed in this installation, not a supported PASCO API.
A listed measurement is not proof that hardware is physically connected.
The provider's `cmdResult=false` is an error, never a fabricated zero.

### Acquisition and repeated runs

Start/stop requests are implemented but successful physical acquisition has not
been verified: the available application currently has no enabled recording
source. A disabled control raises an error. An already-stopped application is
not toggled by a stop request. `transition_pending=true` is not acquisition
success; inspect status again or await the application's recording event.

The rate tool uses the actual discrete rate buttons rather than assuming an
arbitrary frequency is supported. It requires the exact selected sensor name and
a stopped experiment. Other sensor settings remain accessible through the
snapshot/action tools; there is no universal calibration API.

Repeat jobs require the native debug endpoint to belong to the selected UI
process. For example, replace the process and window IDs with attached values:

```json
{
  "plan": {
    "process_id": 1234,
    "window_handle": 5678,
    "debug_port": 9223,
    "repetitions": 3,
    "duration_seconds": 5,
    "pause_seconds": 2,
    "allow_foreground": true
  }
}
```

The worker subscribes to each native recording event before sending input.
Cancellation interrupts the duration timer and requests stop; inspect the job
until it is terminal before considering cancellation complete. Other MCP input
is rejected while a job is active. Do not change the experiment manually during
the job. It checks the displayed rate between runs, but cannot guarantee that
every experiment setting or physical condition remains unchanged.

Run receipts contain host elapsed time, not sensor timestamps. Runs stay in
Capstone. Save the experiment separately, extract matching datasets, and pass
their values and common units to `capstone_compare_runs`. The repeat tool does
not silently save files or associate UI cycles with guessed dataset IDs.
Successful physical-sensor acquisition and repeated native event delivery still
need a connected sensor. Event subscription itself was verified in the live app.

## Boundaries

- This is a generic UI control surface, not a guarantee that every Capstone
  feature is accessible or that an AI can perform every experiment correctly.
- A successful input result means delivery, not completion of the intended task.
- UIA patterns vary between controls. Unsupported patterns produce tool errors;
  the server does not silently substitute a click.
- Screen captures target the Capstone HWND, rather than cropping the desktop.
- Hardware measurements still require connected hardware and appropriate setup.
- File overwrites, hardware output, and other consequential actions need an
  explicit user decision in the controlling agent.
- `capstone_drag` and `capstone_scroll` operate in window-relative pixels with
  explicit foreground opt-in. Positive scroll notches move upward.
- Use the current snapshot's bounds when translating control coordinates.
  Native window-list bounds can include non-client borders not exposed by Qt.
- A blocked or hung application's accessibility provider can still block a
  synchronous UIA query. There is no process-isolated timeout for every provider
  operation. Restart this MCP server if the application stops responding.

## Validation

With Capstone running:

```powershell
uv run basedpyright src tests scripts
uv run ruff check src tests scripts
uv run pytest -q
```

The integration test talks to a real MCP subprocess and observes the running
application. It checks control data, PNG delivery, and stale-reference errors;
it does not claim to validate all application operations.

Manual verification on the installed application (2026-10-27):

- Activated Open Experiment by the observed control name using physical input.
- Entered Korean text and shortcut characters literally; read-back matched.
- Set text through UIA and read it back, without opening or saving a file.
- Moved the file dialog exactly 100 screen pixels using drag.
- Scrolled its navigation tree and observed changed visible item positions.
- Cancelled the dialog and verified it disappeared.
- Closed the empty application normally, launched a new process through
  `launch=true`, and enumerated the new process's windows and controls.
- Visually checked HWND screenshots while another window covered Capstone.

Additional domain verification:

- Automated checks passed: the full 35-test baseline, then the expanded
  seven-test acquisition module and six new repetition tests (44 distinct
  cases total). Ruff and BasedPyright passed for production code and test changes.
  Repetition tests use injected clocks/signals, not hardware or timing sleeps.
- Parsed the installed QuickStart experiment archives and their populated arrays.
- Rendered a scatter plot and OLS fit from the installed Newton experiment data.
- Traced the native JSON dispatcher and storage readers in IDA. The advertised
  JSON dataset reader (method 57) returns false unconditionally; it is not used.
- Generated a separate numeric-cache fixture, opened it in Capstone, and compared
  six offset-adjusted values with the native Export Data preview. Values agreed
  within the preview's display precision. Installed templates were not modified.
- Changed the selected Blue Smart Cart rate from 50 to 100 Hz in that scratch
  experiment, then restored 50 Hz through the new rate function.
- Verified disabled-source rejection, idempotent stop, and native event
  subscription registration/removal. These are not successful hardware captures.

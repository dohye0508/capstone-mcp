# Copyright 2026 Capstone MCP contributors.
"""Subscribe to the observed native recording events before sending UI input."""

import json
from uuid import uuid4

import psutil

from capstone_mcp.bridge import BridgeError, evaluate
from capstone_mcp.models import Model


class Transition(Model):
    """A native event and the state observed after its callbacks ran."""

    matched: bool
    recording: bool


def verify_debug_process(port: int, process_id: int) -> None:
    """Require the UI process and the native-event endpoint to be the same process."""
    owners = {
        connection.pid
        for connection in psutil.net_connections(kind="tcp")
        if connection.status == psutil.CONN_LISTEN
        and connection.laddr
        and connection.laddr.port == port
        and connection.laddr.ip == "127.0.0.1"
    }
    if owners != {process_id}:
        msg = "Debug port ownership does not match the selected Capstone process."
        raise BridgeError(msg)


def arm_transition(port: int, *, recording: bool) -> str:
    """Install a bounded event subscription before an acquisition input is sent."""
    token = uuid4().hex
    key = json.dumps(token)
    desired = "true" if recording else "false"
    event_name = "RecordingStarted" if recording else "RecordingStopped"
    script = f"""(() => {{
      const control = window.app.constructor.experimentControl;
      if (control.IsRecordingData === {desired})
        throw new Error("Recording state already matches the target");
      const event = control.Events.{event_name};
      const waits = window.__capstoneMcpWaits || (window.__capstoneMcpWaits = {{}});
      const host = {{Subscriptions: []}};
      let resolve, timer, finished = false;
      const promise = new Promise(r => {{ resolve = r; }});
      const finish = matched => {{
        if (finished) return;
        finished = true;
        clearTimeout(timer);
        event.RemoveListener(listener);
        resolve({{matched, recording: control.IsRecordingData}});
      }};
      const listener = () => finish(true);
      event.AddListener(listener, host);
      timer = setTimeout(() => finish(false), 10000);
      const expiry = setTimeout(() => {{
        finish(false);
        delete waits[{key}];
      }}, 120000);
      waits[{key}] = {{promise, expiry, dispose: () => finish(false)}};
      return true;
    }})()"""
    if evaluate(port, script) is not True:
        msg = "The recording event subscription was not acknowledged."
        raise BridgeError(msg)
    return token


def await_transition(port: int, token: str, *, recording: bool) -> None:
    """Consume the exact event signal; a timeout is not a successful transition."""
    key = json.dumps(token)
    script = (
        "(async () => { const waits=window.__capstoneMcpWaits;"
        f"try {{ return await waits[{key}].promise; }}"
        f"finally {{ clearTimeout(waits[{key}]?.expiry); delete waits[{key}]; }} }})()"
    )
    transition = Transition.model_validate(evaluate(port, script))
    if not transition.matched or transition.recording != recording:
        msg = "The expected native recording transition was not observed."
        raise BridgeError(msg)


def dispose_transition(port: int, token: str) -> None:
    """Remove an armed listener when its associated input failed."""
    key = json.dumps(token)
    _ = evaluate(port, (
        "(() => {const waits=window.__capstoneMcpWaits;"
        f"if(waits && waits[{key}]){{ clearTimeout(waits[{key}].expiry);"
        f" waits[{key}].dispose(); delete waits[{key}]; }}"
        "return true;})()"
    ))

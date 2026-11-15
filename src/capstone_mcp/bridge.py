# Copyright 2026 Capstone MCP contributors.
"""Read Capstone's observed native data bridge through its local Qt debug port."""

import json
import logging
import socket
import time
from contextlib import ExitStack
from pathlib import Path
from threading import Lock
from typing import Final
from urllib.parse import urlsplit, urlunsplit

import httpx2
import psutil
from pydantic import Field, FiniteFloat, JsonValue, TypeAdapter
from websockets.exceptions import WebSocketException
from websockets.sync.client import ClientConnection, connect

from capstone_mcp.models import Model

LOGGER: Final = logging.getLogger(__name__)
DEFAULT_PORT: Final = 9222
REQUEST_TIMEOUT: Final = 15.0
TARGET_SUFFIX: Final = "/Capstone/Resources/www/index.html"
MAX_CONNECTIONS: Final = 16
MAX_PORT: Final = 65535


class BridgeError(RuntimeError):
    """The configured local Capstone bridge could not produce a valid result."""


class DebugTarget(Model):
    """A target from Qt's local Chrome DevTools discovery endpoint."""

    id: str
    type: str
    url: str
    websocket_url: str = Field(alias="webSocketDebuggerUrl")


class RemoteValue(Model):
    """A CDP Runtime remote value returned by value."""

    type: str
    value: JsonValue = None
    description: str | None = None


class Evaluation(Model):
    """Runtime.evaluate result, including JavaScript exceptions."""

    result: RemoteValue
    exception_details: JsonValue = Field(default=None, alias="exceptionDetails")


class ProtocolError(Model):
    """CDP protocol failure."""

    code: int
    message: str


class Reply(Model):
    """CDP response or event; only matching response IDs are consumed."""

    id: int | None = None
    result: Evaluation | None = None
    error: ProtocolError | None = None


class NativeInventory(Model):
    """Native metadata retained without inventing units or sensor fields.

    Only sensors and measurements are common to every observed Capstone build.
    A category the running build does not report stays null, not an empty list.
    """

    accessories: list[JsonValue] | None = None
    codable_interfaces: list[JsonValue] | None = Field(
        default=None, alias="codableInterfaces",
    )
    code_nodes: list[JsonValue] | None = Field(default=None, alias="codeNodes")
    control_nodes: list[JsonValue] | None = Field(default=None, alias="controlNodes")
    measurements: list[JsonValue]
    outputs: list[JsonValue] | None = None
    sensors: list[JsonValue]


class MeasurementReply(Model):
    """Native success flag is independent from the numeric return value."""

    value: FiniteFloat = Field(alias="ReturnValue")
    succeeded: bool = Field(alias="cmdResult")


def log_request(request: httpx2.Request) -> None:
    """Log discovery requests to stderr through the configured logger."""
    LOGGER.debug("Capstone discovery %s %s", request.method, request.url)


def discover_target(port: int = DEFAULT_PORT) -> DebugTarget:
    """Resolve exactly one Capstone page on the explicit loopback debug port."""
    _verify_debug_owner(port)
    transport = httpx2.HTTPTransport(
        http2=True,
        retries=3,
        limits=httpx2.Limits(
            max_connections=50, max_keepalive_connections=20,
            keepalive_expiry=60,
        ),
        socket_options=[(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)],
    )
    with httpx2.Client(
        transport=transport,
        timeout=httpx2.Timeout(connect=2.0, read=4.0, write=4.0, pool=4.0),
        trust_env=False,
        follow_redirects=False,
        event_hooks={"request": [log_request]},
    ) as client:
        response = client.get(f"http://127.0.0.1:{port}/json/list")
        _ = response.raise_for_status()
        targets = TypeAdapter(list[DebugTarget]).validate_json(response.content)
    matches = [
        target for target in targets
        if target.type == "page" and target.url.lower().endswith(TARGET_SUFFIX.lower())
    ]
    if len(matches) != 1:
        msg = "Expected one Capstone Sense and Control page on the debug port."
        raise BridgeError(msg)
    target = matches[0]
    endpoint = urlsplit(target.websocket_url)
    if (
        endpoint.scheme != "ws"
        or endpoint.hostname not in {"127.0.0.1", "localhost", "::1"}
        or endpoint.username is not None
        or endpoint.password is not None
    ):
        msg = "The Capstone debug WebSocket must remain on loopback."
        raise BridgeError(msg)
    if endpoint.port != port:
        msg = "The discovered WebSocket does not match the selected port."
        raise BridgeError(msg)
    return target.model_copy(update={
        "websocket_url": urlunsplit((
            "ws", f"127.0.0.1:{port}", endpoint.path,
            endpoint.query, endpoint.fragment,
        )),
    })


def _verify_debug_owner(port: int) -> None:
    """Reject another program impersonating the local Capstone debug endpoint."""
    # Import only on connection: desktop itself imports bridge consumers.
    from capstone_mcp.desktop import EXECUTABLE  # noqa: PLC0415

    try:
        owners = {
            connection.pid
            for connection in psutil.net_connections(kind="tcp")
            if connection.status == psutil.CONN_LISTEN
            and connection.laddr
            and connection.laddr.port == port
            and connection.laddr.ip in {"127.0.0.1", "::1"}
        }
        if len(owners) != 1 or None in owners:
            msg = "Debug port must have one identifiable loopback process owner."
            raise BridgeError(msg)
        owner = next(iter(owners))
        actual = Path(psutil.Process(owner).exe()).resolve()
        if actual != EXECUTABLE.resolve():
            msg = "Debug port is not owned by the configured Capstone executable."
            raise BridgeError(msg)
    except (psutil.Error, OSError) as error:
        msg = "Could not verify Capstone debug port ownership: " + str(error)
        raise BridgeError(msg) from error


class BridgeConnection:
    """Serialize one port's requests without replaying uncertain evaluations."""

    def __init__(self, port: int) -> None:
        """Allocate a lazy connection; no discovery or network I/O occurs here."""
        self.port = port
        self._lock = Lock()
        self._websocket: ClientConnection | None = None
        self._stack = ExitStack()
        self._next_id = 0
        self._closed = False

    def close(self) -> None:
        """Invalidate the connection and release its socket after active I/O."""
        with self._lock:
            self._closed = True
            self._disconnect()

    def _disconnect(self) -> None:
        self._websocket = None
        self._stack.close()

    def _get_websocket(self) -> ClientConnection:
        if self._closed:
            msg = "Capstone bridge connection has been closed."
            raise BridgeError(msg)
        if self._websocket is None:
            target = discover_target(self.port)
            self._websocket = self._stack.enter_context(connect(
                target.websocket_url, proxy=None, open_timeout=5,
                close_timeout=2, max_size=8 * 1024 * 1024,
                ping_interval=20, ping_timeout=20,
            ))
            _verify_debug_owner(self.port)
        return self._websocket

    def evaluate(self, expression: str) -> JsonValue:
        """Reuse the socket; a failed request is never retried automatically."""
        if not self._lock.acquire(timeout=REQUEST_TIMEOUT):
            msg = "Another Capstone bridge request is still active."
            raise BridgeError(msg)
        try:
            self._next_id += 1
            return self._exchange(expression, self._next_id, self._get_websocket())
        except (
            OSError, TimeoutError, WebSocketException, ValueError, BridgeError,
        ) as error:
            self._disconnect()
            msg = "Capstone bridge request failed; it was not replayed: " + str(error)
            raise BridgeError(msg) from error
        finally:
            self._lock.release()

    @staticmethod
    def _exchange(
        expression: str, identifier: int, websocket: ClientConnection,
    ) -> JsonValue:
        request = {
            "id": identifier,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
            },
        }
        deadline = time.monotonic() + REQUEST_TIMEOUT
        websocket.send(json.dumps(request))
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                msg = "Capstone bridge response deadline exceeded."
                raise TimeoutError(msg)
            packet = json.loads(websocket.recv(timeout=remaining))
            if not isinstance(packet, dict):
                msg = "Capstone bridge returned a non-object protocol message."
                raise BridgeError(msg)
            if type(packet.get("id")) is not int or packet["id"] != identifier:
                continue
            reply = Reply.model_validate(packet)
            if reply.error is not None:
                raise BridgeError(reply.error.message)
            if reply.result is None:
                msg = "Capstone returned no evaluation result."
                raise BridgeError(msg)
            result = reply.result
            if result.exception_details is not None:
                msg = "Capstone JavaScript bridge raised: " + json.dumps(
                    result.exception_details, ensure_ascii=False,
                )
                raise BridgeError(msg)
            return result.result.value


_CONNECTIONS: Final[dict[int, BridgeConnection]] = {}
_POOL_LOCK: Final = Lock()


def close_connections() -> None:
    """Release every cached connection at server shutdown or explicit teardown."""
    with _POOL_LOCK:
        connections = list(_CONNECTIONS.values())
        _CONNECTIONS.clear()
    for connection in connections:
        connection.close()


def evaluate(port: int, expression: str) -> JsonValue:
    """Evaluate using a bounded pool with one serialized connection per port."""
    if type(port) is not int or not 1 <= port <= MAX_PORT:
        msg = "Capstone debug port must be an integer between 1 and 65535."
        raise BridgeError(msg)
    with _POOL_LOCK:
        connection = _CONNECTIONS.get(port)
        if connection is None:
            if len(_CONNECTIONS) >= MAX_CONNECTIONS:
                msg = "Capstone bridge connection limit reached; close unused sessions."
                raise BridgeError(msg)
            connection = _CONNECTIONS[port] = BridgeConnection(port)
    return connection.evaluate(expression)


def read_inventory(port: int = DEFAULT_PORT) -> NativeInventory:
    """Read actual sensor and measurement metadata from the running application."""
    result = evaluate(
        port,
        "window.app.mSenseAndControlView.mServices.RequestSensorsAndMeasurements()",
    )
    return NativeInventory.model_validate(result)


def read_measurement(port: int, measurement_euid: str, unit_type: int) -> float:
    """Read a current value, refusing the provider's unavailable-value sentinel."""
    expression = (
        "window.app.mSenseAndControlView.mServices.RequestReadMeasurement("
        + json.dumps(measurement_euid) + "," + str(unit_type) + ")"
    )
    reply = MeasurementReply.model_validate(evaluate(port, expression))
    if not reply.succeeded:
        msg = "Capstone reports no current value for this measurement and unit."
        raise BridgeError(msg)
    return reply.value

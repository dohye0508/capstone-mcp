# Copyright 2026 Capstone MCP contributors.
"""Real HTTP/WebSocket contracts on an ephemeral test server, never Capstone."""

import json
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from threading import Thread

import pytest
from websockets.http11 import Request, Response
from websockets.sync.server import ServerConnection, serve

from capstone_mcp import bridge


@pytest.fixture
def wire_server(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[int, list[str], list[int]]]:
    # This fixture deliberately substitutes the process owner, not the wire I/O.
    monkeypatch.setattr(bridge, "_verify_debug_owner", lambda _port: None)
    requests: list[str] = []
    connections: list[int] = []

    def handler(connection: ServerConnection) -> None:
        connections.append(1)
        for raw in connection:
            request = json.loads(raw)
            expression = request["params"]["expression"]
            requests.append(expression)
            if expression == "disconnect":
                connection.close()
                return
            connection.send(json.dumps({"method": "Runtime.consoleAPICalled"}))
            # Another method's result need not share Runtime.evaluate's schema.
            connection.send(json.dumps({"id": -1, "result": {"unrelated": True}}))
            reply = json.dumps({
                "id": request["id"],
                "result": {"result": {"type": "string", "value": expression}},
            })
            connection.send([reply[:17], reply[17:]])

    def process_request(connection: ServerConnection, request: Request) -> Response | None:
        if request.path == "/json/list":
            payload = json.dumps([{
                "id": "fixture", "type": "page",
                "url": "file:///Capstone/Resources/www/index.html",
                # Exercise Qt's localhost spelling without DNS/IPv6 dependence.
                "webSocketDebuggerUrl": f"ws://localhost:{port}/devtools/page/fixture",
            }])
            return connection.respond(HTTPStatus.OK, payload)
        return None

    with serve(handler, "127.0.0.1", 0, process_request=process_request) as listener:
        port = listener.socket.getsockname()[1]
        thread = Thread(target=listener.serve_forever, daemon=True)
        thread.start()
        try:
            yield port, requests, connections
        finally:
            bridge.close_connections()
            listener.shutdown()
            thread.join(timeout=5)
            assert not thread.is_alive()


def test_socket_reused_and_fragmented_events_do_not_corrupt_replies(
    wire_server: tuple[int, list[str], list[int]],
) -> None:
    port, requests, connections = wire_server
    assert bridge.evaluate(port, "first") == "first"
    payload = "한글" * 40000
    assert bridge.evaluate(port, payload) == payload
    assert requests == ["first", payload]
    assert len(connections) == 1


def test_failed_request_not_replayed_and_next_call_reconnects(
    wire_server: tuple[int, list[str], list[int]],
) -> None:
    port, requests, connections = wire_server
    with pytest.raises(bridge.BridgeError, match="not replayed"):
        bridge.evaluate(port, "disconnect")
    assert requests == ["disconnect"]
    assert bridge.evaluate(port, "next") == "next"
    assert requests == ["disconnect", "next"]
    assert len(connections) == 2


def test_concurrent_requests_remain_correlated_on_one_socket(
    wire_server: tuple[int, list[str], list[int]],
) -> None:
    port, requests, connections = wire_server
    values = [f"request-{index}" for index in range(12)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda value: bridge.evaluate(port, value), values))
    assert results == values
    assert sorted(requests) == sorted(values)
    assert len(connections) == 1


def test_pool_shutdown_closes_and_next_lifecycle_can_connect(
    wire_server: tuple[int, list[str], list[int]],
) -> None:
    port, _, connections = wire_server
    assert bridge.evaluate(port, "before") == "before"
    bridge.close_connections()
    assert not bridge._CONNECTIONS
    assert bridge.evaluate(port, "after") == "after"
    assert len(connections) == 2

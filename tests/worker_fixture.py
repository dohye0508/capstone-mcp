# Copyright 2026 Capstone MCP contributors.
"""Real subprocess fixture simulating native success and an unreturning operation."""

import socket
import subprocess
import sys
from pathlib import Path
from threading import Event

from capstone_mcp.automation_models import NativeReply, RequestPacket


def main() -> None:
    if sys.stdin.readline() != "INITIALIZE\n":
        return
    for counter, line in enumerate(sys.stdin, 1):
        packet = RequestPacket.model_validate_json(line)
        if packet.command.operation == "snapshot":
            with Path(packet.command.ref).open("a", encoding="utf-8") as delivered:
                _ = delivered.write("delivered\n")
            if packet.command.value == "inherited":
                child = subprocess.Popen(
                    [sys.executable, "-c", "import time; time.sleep(60)"],
                    stdin=subprocess.DEVNULL, stdout=sys.stdout, stderr=sys.stderr,
                )
                _ = Path(packet.command.ref + ".child").write_text(
                    str(child.pid), encoding="utf-8",
                )
            if packet.command.value == "partial":
                _ = sys.stdout.write("{")
                _ = sys.stdout.flush()
            with socket.create_connection(
                ("127.0.0.1", packet.command.limit), timeout=5,
            ) as signal:
                signal.sendall(b"entered")
                # The parent deliberately retires this worker; bound the fallback
                # even if the test runner itself disappears before cleanup.
                _ = Event().wait(30)
        reply = NativeReply(
            identifier=packet.identifier,
            result=(
                packet.command.value
                if packet.command.operation == "keys" else f"한글 {counter}"
            ),
        )
        _ = sys.stdout.write(reply.model_dump_json() + "\n")
        _ = sys.stdout.flush()


if __name__ == "__main__":
    main()

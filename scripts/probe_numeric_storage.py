# Copyright 2026 Capstone MCP contributors.
"""Generate a private native-reader validation copy; never overwrite the source."""

import json
import struct
import sys
from io import BytesIO
from pathlib import Path
from typing import Final
from xml.etree.ElementTree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile

from defusedxml.ElementTree import fromstring

SOURCE: Final = Path(
    "C:/Program Files/PASCO scientific/Capstone/Resources/Templates/QuickStart",
) / "Conservation of Momentum.cap"
OUTPUT: Final = (
    Path(__file__).resolve().parents[1] / ".analysis/native-numeric-probe.cap"
)
VALUES: Final = (-1.25, 0.0, 2.5, 12.0, 3.1415, 100.0)
OFFSET: Final = 0.5
PAYLOAD: Final = "data/mcp-native-numeric-probe.tmp"


def main() -> None:
    """Create a known-value type-0 array for verification in real Capstone."""
    with ZipFile(SOURCE) as source:
        root = fromstring(source.read("main.xml"))
        data_source = next(
            element for element in root.iter("DataSource")
            if element.get("LongName") == "Init. Red v"
        )
        dependent = next(data_source.iter("DependentStorageElement"))
        dependent.set("StorageType", "0")
        dependent.set("DataCacheDataSize", str(len(VALUES)))
        dependent.set("DataOffsetValue", str(OFFSET))
        dependent.set("FileName", PAYLOAD)
        numeric_payload = b"".join(struct.pack("<Id", 1, value) for value in VALUES)
        with ZipFile(OUTPUT, "x", compression=ZIP_DEFLATED) as output:
            for member in source.infolist():
                if member.filename == "main.xml":
                    with BytesIO() as buffer:
                        ElementTree(root).write(buffer, encoding="utf-8")
                        output.writestr(member.filename, buffer.getvalue())
                else:
                    output.writestr(member, source.read(member))
            output.writestr(PAYLOAD, numeric_payload)
    _ = sys.stdout.write(json.dumps({
        "path": str(OUTPUT),
        "source_euid": data_source.get("EUID"),
        "expected_values": [value + OFFSET for value in VALUES],
    }) + "\n")


if __name__ == "__main__":
    main()

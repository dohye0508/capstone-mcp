# Copyright 2026 Capstone MCP contributors.
"""ZDataCache scalar decoding established from the native Capstone reader."""

import math
import struct
from decimal import Decimal
from typing import Final

from capstone_mcp.models import Model

SCALAR_BYTES: Final = 12
NUMERIC_TAG: Final = 1
EMPTY_TAG: Final = 0
INVALID_TAG: Final = 3


class NumericStorageError(ValueError):
    """The numeric payload does not match a verified native encoding."""


class DecodedScalars(Model):
    """Retain attribute words and missing samples rather than inventing zero values."""

    values: list[Decimal | None]
    text: list[str]
    attributes: list[int]


def decode_numeric_records(
    payload: bytes,
    count: int,
    offset: Decimal,
    *,
    start_index: int = 0,
    limit: int | None = None,
) -> DecodedScalars:
    """Read little-endian attribute/double pairs and apply native double addition."""
    if count < 0 or start_index < 0 or (limit is not None and limit < 0):
        msg = "Invalid numeric cache record range."
        raise NumericStorageError(msg)
    if len(payload) < count * SCALAR_BYTES:
        msg = "Truncated numeric cache payload or invalid record count."
        raise NumericStorageError(msg)
    values: list[Decimal | None] = []
    text: list[str] = []
    attributes: list[int] = []
    adjustment = float(offset)
    if not math.isfinite(adjustment):
        msg = "Numeric cache offset is outside the finite double range."
        raise NumericStorageError(msg)
    end_index = count if limit is None else min(count, start_index + limit)
    for index in range(start_index, end_index):
        attribute, stored = struct.unpack_from("<Id", payload, index * SCALAR_BYTES)
        attribute = int(attribute)
        stored = float(stored)
        tag = attribute & 0xFF
        attributes.append(attribute)
        if tag == EMPTY_TAG:
            values.append(None)
            text.append("")
        elif tag == INVALID_TAG:
            values.append(None)
            text.append("NaN")
        elif tag == NUMERIC_TAG:
            value = stored + adjustment
            rendered = repr(value)
            values.append(Decimal(rendered) if math.isfinite(value) else None)
            text.append(rendered)
        else:
            msg = f"Unsupported numeric scalar tag: {tag}."
            raise NumericStorageError(msg)
    return DecodedScalars(values=values, text=text, attributes=attributes)


def interval_values(
    start: Decimal,
    interval: Decimal,
    count: int,
    *,
    start_index: int = 0,
    limit: int | None = None,
) -> list[Decimal]:
    """Reproduce ZIntervalCache's start + index * interval double arithmetic."""
    first, step = float(start), float(interval)
    if count < 0 or start_index < 0 or (limit is not None and limit < 0):
        msg = "Invalid interval cache record range."
        raise NumericStorageError(msg)
    values: list[Decimal] = []
    end_index = count if limit is None else min(count, start_index + limit)
    for index in range(start_index, end_index):
        value = first + index * step
        if not math.isfinite(value):
            msg = "Interval cache produces a nonfinite coordinate."
            raise NumericStorageError(msg)
        values.append(Decimal(repr(value)))
    return values

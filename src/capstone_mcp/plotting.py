# Copyright 2026 Capstone MCP contributors.
"""Render measurement scatter plots without altering the Capstone workbook."""

import math
from io import BytesIO
from typing import Annotated, Final

from PIL import Image, ImageDraw, ImageFont
from pydantic import Field, FiniteFloat

from capstone_mcp.analysis import AnalysisError, FitInput, LinearFit, linear_fit
from capstone_mcp.models import Model

SIZE: Final = (1000, 640)
PLOT_BOX: Final = (110, 100, 940, 510)
FONT_PATH: Final = "C:/Windows/Fonts/malgun.ttf"
TICK_COUNT: Final = 5
DOT_RADIUS: Final = 3
MIN_FONT_SIZE: Final = 8
LINE_ENDPOINTS: Final = 2


class PlotInput(Model):
    """Paired coordinates with explicit labels; units are never inferred."""

    x: Annotated[list[FiniteFloat], Field(min_length=1, max_length=100_000)]
    y: Annotated[list[FiniteFloat], Field(min_length=1, max_length=100_000)]
    title: Annotated[str, Field(max_length=80)] = "Measurement data"
    x_label: Annotated[str, Field(max_length=60)] = "x"
    y_label: Annotated[str, Field(max_length=60)] = "y"
    show_fit: bool = False


def _extent(values: list[float]) -> tuple[float, float]:
    low, high = min(values), max(values)
    span = high - low
    if not math.isfinite(span):
        msg = "Plot range exceeds finite floating-point precision."
        raise AnalysisError(msg)
    padding = span * 0.05 if span else max(abs(low) * 0.05, 1)
    low, high = low - padding, high + padding
    if not math.isfinite(low) or not math.isfinite(high):
        msg = "Padded plot range exceeds finite floating-point precision."
        raise AnalysisError(msg)
    return low, high


def _font(text: str, width: float, preferred_size: int) -> ImageFont.FreeTypeFont:
    for size in range(preferred_size, MIN_FONT_SIZE - 1, -1):
        font = ImageFont.truetype(FONT_PATH, size)
        if font.getlength(text) <= width:
            return font
    msg = "Plot label cannot fit at a readable size."
    raise AnalysisError(msg)


def clip_fit_line(
    fit: LinearFit, x_range: tuple[float, float], y_range: tuple[float, float],
) -> list[tuple[float, float]]:
    """Clip a fitted line to the plot rectangle without duplicate corner points."""
    x_min, x_max = x_range
    y_min, y_max = y_range
    endpoints: set[tuple[float, float]] = set()
    for x in x_range:
        y = fit.slope * x + fit.intercept
        if y_min <= y <= y_max:
            endpoints.add((x, y))
    if fit.slope:
        for y in y_range:
            x = (y - fit.intercept) / fit.slope
            if x_min <= x <= x_max:
                endpoints.add((x, y))
    ordered = sorted(endpoints)
    return [ordered[0], ordered[-1]] if len(ordered) >= LINE_ENDPOINTS else []


def render_plot(samples: PlotInput) -> bytes:
    """Draw axes, samples and an optional OLS fit as a standalone PNG."""
    if len(samples.x) != len(samples.y):
        msg = "Plot x and y must contain the same number of samples."
        raise AnalysisError(msg)
    x_min, x_max = _extent(samples.x)
    y_min, y_max = _extent(samples.y)
    fit = (
        linear_fit(FitInput(x=samples.x, y=samples.y))
        if samples.show_fit else None
    )
    left, top, right, bottom = PLOT_BOX

    def position(x: float, y: float) -> tuple[float, float]:
        return (
            left + (x - x_min) / (x_max - x_min) * (right - left),
            bottom - (y - y_min) / (y_max - y_min) * (bottom - top),
        )

    with Image.new("RGB", SIZE, "white") as image, BytesIO() as output:
        draw = ImageDraw.Draw(image)
        normal = ImageFont.truetype(FONT_PATH, 18)
        title = _font(samples.title, right - left, 28)
        draw.text((left, 24), samples.title, fill="#16202a", font=title)
        draw.text(
            (left, 65), samples.y_label, fill="#334155",
            font=_font(samples.y_label, right - left, 22),
        )
        for tick in range(TICK_COUNT + 1):
            fraction = tick / TICK_COUNT
            x_value = x_min + fraction * (x_max - x_min)
            y_value = y_min + fraction * (y_max - y_min)
            x_pixel, _ = position(x_value, y_min)
            _, y_pixel = position(x_min, y_value)
            draw.line((x_pixel, top, x_pixel, bottom), fill="#e2e8f0")
            draw.line((left, y_pixel, right, y_pixel), fill="#e2e8f0")
            draw.text(
                (x_pixel, bottom + 12), f"{x_value:.4g}",
                anchor="mt", fill="#334155", font=normal,
            )
            draw.text(
                (left - 12, y_pixel), f"{y_value:.4g}",
                anchor="rm", fill="#334155",
                font=_font(f"{y_value:.4g}", left - 20, 18),
            )
        draw.rectangle(PLOT_BOX, outline="#64748b", width=1)
        if fit is not None:
            endpoints = clip_fit_line(fit, (x_min, x_max), (y_min, y_max))
            if endpoints:
                draw.line(
                    [position(x, y) for x, y in endpoints],
                    fill="#d14b28", width=2,
                )
        for x, y in zip(samples.x, samples.y, strict=True):
            px, py = position(x, y)
            draw.ellipse(
                (px - DOT_RADIUS, py - DOT_RADIUS,
                 px + DOT_RADIUS, py + DOT_RADIUS),
                fill="#1769aa",
            )
        draw.text(
            ((left + right) / 2, 560), samples.x_label,
            anchor="mt", fill="#334155",
            font=_font(samples.x_label, right - left, 22),
        )
        footer = f"n = {len(samples.x)}"
        if fit is not None:
            r_squared = "undefined" if fit.r_squared is None else f"{fit.r_squared:.5g}"
            footer += (
                f"   OLS: y = {fit.slope:.5g} x + {fit.intercept:.5g}"
                f"   R^2 = {r_squared}"
            )
        draw.text(
            (left, 607), footer, fill="#334155",
            font=_font(footer, right - left, 18),
        )
        image.save(output, format="PNG")
        return output.getvalue()

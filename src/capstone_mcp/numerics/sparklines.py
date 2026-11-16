# Copyright 2026 Capstone MCP contributors.
"""Clean ASCII sparklines and standalone SVG chart generation."""

from __future__ import annotations

import html
import math
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

MIN_FIT_POINTS: Final[int] = 2
MAX_SVG_POINTS: Final[int] = 1000


def finite_plot_points(
    x: Sequence[float], y: Sequence[float],
) -> Iterator[tuple[float, float]]:
    """Yield finite pairs without shifting one series across missing rows."""
    return (
        (px, py)
        for px, py in zip(x, y, strict=False)
        if math.isfinite(px) and math.isfinite(py)
    )


def plot_bounds(
    x: Sequence[float], y: Sequence[float],
) -> tuple[int, float, float, float, float] | None:
    """Count finite points and determine axis bounds without retaining points."""
    min_x = min_y = math.inf
    max_x = max_y = -math.inf
    count = 0
    for px, py in finite_plot_points(x, y):
        count += 1
        min_x, max_x = min(px, min_x), max(px, max_x)
        min_y, max_y = min(py, min_y), max(py, max_y)
    if not count:
        return None
    return count, min_x, max_x, min_y, max_y


def sampled_svg_points(
    x: Sequence[float], y: Sequence[float], count: int,
) -> Iterator[tuple[float, float]]:
    """Sample finite points in order, preserving endpoints and bounding SVG size."""
    step = max(1, math.ceil((count - 1) / (MAX_SVG_POINTS - 1)))
    for index, point in enumerate(finite_plot_points(x, y)):
        if index % step == 0 or index == count - 1:
            yield point


def _validate_plot_values(x: Sequence[float], y: Sequence[float]) -> None:
    if len(x) != len(y):
        msg = "Plot coordinates must have matching lengths."
        raise ValueError(msg)
    if not all(math.isfinite(value) for values in (x, y) for value in values):
        msg = "Plot coordinates must be finite."
        raise ValueError(msg)


def _validate_plot_spans(span_x: float, span_y: float) -> None:
    if not math.isfinite(span_x) or not math.isfinite(span_y):
        msg = "Plot coordinate span exceeds the finite floating-point range."
        raise ValueError(msg)


def render_ascii_sparkline(
    x: Sequence[float],
    y: Sequence[float],
    width: int = 40,
    height: int = 10,
    title: str = "",
) -> str:
    """Render a clean 2D ASCII scatter/line plot for terminal and markdown display.

    Args:
        x: Independent variable series.
        y: Dependent variable series.
        width: Character width of plot area.
        height: Character height of plot area.
        title: Optional plot title header.

    Returns:
        Formatted ASCII plot string.
    """
    _validate_plot_values(x, y)
    if width < 1 or height < 1:
        msg = "ASCII plot dimensions must be positive."
        raise ValueError(msg)
    bounds = plot_bounds(x, y)
    if bounds is None:
        return "[Empty data series for ASCII plot]"

    _, min_x, max_x, min_y, max_y = bounds

    span_x = max_x - min_x if max_x > min_x else 1.0
    span_y = max_y - min_y if max_y > min_y else 1.0

    _validate_plot_spans(span_x, span_y)

    # Grid init
    grid = [[" " for _ in range(width)] for _ in range(height)]

    for xi, yi in finite_plot_points(x, y):
        col = int(((xi - min_x) / span_x) * (width - 1))
        row = int(((max_y - yi) / span_y) * (height - 1))
        col = max(0, min(width - 1, col))
        row = max(0, min(height - 1, row))
        grid[row][col] = "*"

    lines: list[str] = []
    if title:
        lines.append(f"  {title}")
    lines.append(f"  +{'-' * width}+")
    for r in range(height):
        y_val = max_y - (r / max(height - 1, 1)) * span_y
        row_str = "".join(grid[r])
        lines.append(f"{y_val:6.2f} |{row_str}|")
    lines.append(f"  +{'-' * width}+")
    lines.append(f"       {min_x:<10.2f}{' ' * max(0, width - 20)}{max_x:>10.2f}")

    return "\n".join(lines)


def render_svg_sparkline(
    x: Sequence[float],
    y: Sequence[float],
    fit_x: Sequence[float] | None = None,
    fit_y: Sequence[float] | None = None,
    width: int = 500,
    height: int = 250,
    title: str = "",
) -> str:
    """Render a clean, responsive standalone vector SVG chart.

    Args:
        x: Independent variable series.
        y: Dependent variable series.
        fit_x: Optional fitted line X coordinates.
        fit_y: Optional fitted line Y coordinates.
        width: ViewBox pixel width.
        height: ViewBox pixel height.
        title: Chart title.

    Returns:
        Valid SVG XML markup string.
    """
    _validate_plot_values(x, y)
    fit_x = fit_x if fit_x is not None else ()
    fit_y = fit_y if fit_y is not None else ()
    _validate_plot_values(fit_x, fit_y)
    no_data = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"><text x="20" y="30">No data</text></svg>'
    bounds = plot_bounds(x, y)
    if bounds is None:
        return no_data

    pad_left = 60
    pad_right = 30
    pad_top = 40
    pad_bottom = 40

    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    count, min_x, max_x, min_y, max_y = bounds
    fit_bounds = plot_bounds(fit_x, fit_y)
    fit_count = 0
    if fit_bounds and fit_bounds[0] >= MIN_FIT_POINTS:
        fit_count, fit_min_x, fit_max_x, fit_min_y, fit_max_y = fit_bounds
        min_x, max_x = min(min_x, fit_min_x), max(max_x, fit_max_x)
        min_y, max_y = min(min_y, fit_min_y), max(max_y, fit_max_y)

    span_x = max_x - min_x if max_x > min_x else 1.0
    span_y = max_y - min_y if max_y > min_y else 1.0
    _validate_plot_spans(span_x, span_y)

    def to_svg(px: float, py: float) -> tuple[float, float]:
        sx = pad_left + ((px - min_x) / span_x) * plot_w
        sy = pad_top + ((max_y - py) / span_y) * plot_h
        return sx, sy

    elements: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" style="background:#ffffff; border-radius:6px;">',
    ]

    if title:
        elements.append(
            f'<text x="{pad_left}" y="25" font-family="sans-serif" font-size="14" font-weight="bold" fill="#1e293b">{html.escape(title)}</text>',
        )

    # Axes
    elements.append(
        f'<line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{pad_top + plot_h}" stroke="#94a3b8" stroke-width="1.5"/>',
    )
    elements.append(
        f'<line x1="{pad_left}" y1="{pad_top + plot_h}" x2="{pad_left + plot_w}" y2="{pad_top + plot_h}" stroke="#94a3b8" stroke-width="1.5"/>',
    )

    # Fitted line if present
    if fit_count:
        path_data: list[str] = []
        for i, (fx, fy) in enumerate(sampled_svg_points(fit_x, fit_y, fit_count)):
            sx, sy = to_svg(fx, fy)
            cmd = "M" if i == 0 else "L"
            path_data.append(f"{cmd} {sx:.1f} {sy:.1f}")
        elements.append(
            f'<path d="{" ".join(path_data)}" fill="none" stroke="#dc2626" stroke-width="2" stroke-dasharray="4 2"/>',
        )

    # Scatter points
    for xi, yi in sampled_svg_points(x, y, count):
        sx, sy = to_svg(xi, yi)
        elements.append(
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="3.5" fill="#2563eb" opacity="0.85"/>',
        )

    # Axis tick labels
    elements.append(
        f'<text x="{pad_left}" y="{pad_top + plot_h + 20}" font-family="sans-serif" font-size="10" fill="#64748b" text-anchor="middle">{min_x:.2f}</text>',
    )
    elements.append(
        f'<text x="{pad_left + plot_w}" y="{pad_top + plot_h + 20}" font-family="sans-serif" font-size="10" fill="#64748b" text-anchor="middle">{max_x:.2f}</text>',
    )
    elements.append(
        f'<text x="{pad_left - 8}" y="{pad_top + plot_h}" font-family="sans-serif" font-size="10" fill="#64748b" text-anchor="end">{min_y:.2f}</text>',
    )
    elements.append(
        f'<text x="{pad_left - 8}" y="{pad_top + 10}" font-family="sans-serif" font-size="10" fill="#64748b" text-anchor="end">{max_y:.2f}</text>',
    )

    elements.append("</svg>")
    return "\n".join(elements)

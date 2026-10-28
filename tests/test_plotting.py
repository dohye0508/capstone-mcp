# Copyright 2026 Capstone MCP contributors.
"""Geometry and real-image verification for numeric plotting."""

from io import BytesIO

from PIL import Image

from capstone_mcp.analysis import FitInput, linear_fit
from capstone_mcp.plotting import PlotInput, clip_fit_line, render_plot


def test_negative_fit_keeps_both_rectangle_corners() -> None:
    # Given
    fit = linear_fit(FitInput(x=[0, 0.5, 1], y=[1, 0.5, 0]))
    # When
    endpoints = clip_fit_line(fit, (0, 1), (0, 1))
    # Then
    assert endpoints == [(0, 1), (1, 0)]


def test_plot_returns_decodable_nonblank_image() -> None:
    # Given
    samples = PlotInput(x=[0, 1, 2], y=[3, 2, 1], show_fit=True)
    # When
    png = render_plot(samples)
    # Then
    with Image.open(BytesIO(png)) as image:
        assert image.size == (1000, 640)
        assert image.getextrema() != ((255, 255), (255, 255), (255, 255))

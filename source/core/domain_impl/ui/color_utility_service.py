"""Shared color conversion/blending helpers for UI modules."""

from __future__ import annotations

from typing import Any


def hex_to_colorref(hex_color: Any) -> int | None:
    """Convert #RRGGBB color text to Win32 COLORREF integer."""
    value = str(hex_color).strip().lstrip("#")
    if len(value) != 6:
        return None
    try:
        red = int(value[0:2], 16)
        green = int(value[2:4], 16)
        blue = int(value[4:6], 16)
    except ValueError:
        return None
    return (blue << 16) | (green << 8) | red


def hex_to_rgb_tuple(
    hex_color: Any,
    default_rgb: tuple[int, int, int] = (220, 235, 245),
    *,
    expected_errors: tuple[type[BaseException], ...],
) -> tuple[int, int, int]:
    """Parse #RRGGBB into (r, g, b) with fallback defaults."""
    try:
        raw = str(hex_color).strip().lstrip("#")
        if len(raw) != 6:
            return default_rgb
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
    except expected_errors:
        return default_rgb


def blend_hex_color(
    color_a: Any,
    color_b: Any,
    ratio: Any,
    *,
    expected_errors: tuple[type[BaseException], ...],
) -> str:
    """Blend two hex colors by ratio and return #RRGGBB."""
    try:
        normalized_ratio = max(0.0, min(1.0, float(ratio)))
    except expected_errors:
        normalized_ratio = 0.0
    ra, ga, ba = hex_to_rgb_tuple(
        color_a,
        default_rgb=(0, 0, 0),
        expected_errors=expected_errors,
    )
    rb, gb, bb = hex_to_rgb_tuple(
        color_b,
        default_rgb=(0, 0, 0),
        expected_errors=expected_errors,
    )
    red = int(round(ra + ((rb - ra) * normalized_ratio)))
    green = int(round(ga + ((gb - ga) * normalized_ratio)))
    blue = int(round(ba + ((bb - ba) * normalized_ratio)))
    return f"#{red:02x}{green:02x}{blue:02x}"


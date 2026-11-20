"""
Color system
Central color schemes for grades and rarities across the game
"""
from __future__ import annotations

import re
from typing import Protocol


class ColorGradable(Protocol):
    """Protocol for objects with a graded color"""

    @property
    def color_rgb(self) -> tuple[int, int, int]:
        """Return the RGB color"""
        ...


# ==================== Common colors ====================


class Color:
    """Predefined color constants"""

    # Basic colors
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

    # Quality colors - low to high
    COMMON_WHITE = (255, 255, 255)  # common / white
    UNCOMMON_GREEN = (50, 205, 50)  # uncommon / green
    RARE_BLUE = (74, 144, 226)  # rare / blue
    EPIC_PURPLE = (147, 112, 219)  # epic / purple
    LEGENDARY_GOLD = (255, 215, 0)  # legendary / gold


# ==================== Helpers ====================


COLOR_TAG_PATTERN = re.compile(
    r"<color:(\d{1,3}),(\d{1,3}),(\d{1,3})>(.*?)</color>", re.DOTALL
)


def get_color_from_mapping(
    grade_value: object,
    color_mapping: dict,
    default_color: tuple[int, int, int] = Color.COMMON_WHITE,
) -> tuple[int, int, int]:
    """
    Look up a color in a mapping dict

    Args:
        grade_value: grade object
        color_mapping: dict mapping grades to colors
        default_color: default color

    Returns:
        RGB color tuple
    """
    return color_mapping.get(grade_value, default_color)


def format_colored_text(text: str, color_rgb: tuple[int, int, int]) -> str:
    """
    Wrap text in a color tag for the frontend to render
    Format: <color:R,G,B>text</color>

    Args:
        text: text to color
        color_rgb: RGB color tuple

    Returns:
        text wrapped in a color tag
    """
    r, g, b = color_rgb
    return f"<color:{r},{g},{b}>{text}</color>"


def rgb_to_hex(color_rgb: tuple[int, int, int]) -> str:
    """Convert an RGB int tuple to a hex string (#rrggbb)"""
    r, g, b = color_rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def split_colored_segments(text: str) -> list[dict[str, str]]:
    """
    Split text containing <color> tags into segments;
    each segment is {"text": "...", "color": "#rrggbb"} (color is optional).
    """
    segments: list[dict[str, str]] = []
    last_index = 0

    for match in COLOR_TAG_PATTERN.finditer(text):
        start, end = match.span()
        if start > last_index:
            plain = text[last_index:start]
            if plain:
                segments.append({"text": plain})

        r, g, b, content = match.groups()
        color_hex = rgb_to_hex((int(r), int(g), int(b)))
        segments.append({"text": content, "color": color_hex})
        last_index = end

    if last_index < len(text):
        trailing = text[last_index:]
        if trailing:
            segments.append({"text": trailing})

    if not segments:
        segments.append({"text": text})

    return segments


# ==================== Color scheme mappings ====================

# Equipment grade colors (common - treasure - artifact)
EQUIPMENT_GRADE_COLORS = {
    "COMMON": Color.COMMON_WHITE,
    "TREASURE": Color.EPIC_PURPLE,
    "ARTIFACT": Color.LEGENDARY_GOLD,
}

# Rarity colors (N-R-SR-SSR)
RARITY_COLORS = {
    "N": Color.COMMON_WHITE,
    "R": Color.RARE_BLUE,
    "SR": Color.EPIC_PURPLE,
    "SSR": Color.LEGENDARY_GOLD,
}

# Technique grade colors (lower - middle - upper)
TECHNIQUE_GRADE_COLORS = {
    "LOWER": Color.COMMON_WHITE,
    "MIDDLE": Color.UNCOMMON_GREEN,
    "UPPER": Color.EPIC_PURPLE,
}


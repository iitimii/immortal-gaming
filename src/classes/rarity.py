"""
Rarity system
Defines rarity levels for traits, items, etc.
"""
from enum import Enum
from dataclasses import dataclass
from src.classes.color import Color, RARITY_COLORS


class RarityLevel(Enum):
    """Rarity level"""
    N = "N"      # Normal
    R = "R"      # Rare
    SR = "SR"    # Super Rare
    SSR = "SSR"  # Super Super Rare (Legendary)


@dataclass
class Rarity:
    """
    Rarity configuration
    Holds the level, weight, colors, etc.
    """
    level: RarityLevel
    weight: float
    color_rgb: tuple[int, int, int]  # RGB color
    color_hex: str  # hex color
    display_name: str
    
    def __str__(self) -> str:
        return self.display_name


# Rarity config table
RARITY_CONFIGS = {
    RarityLevel.N: Rarity(
        level=RarityLevel.N,
        weight=10.0,
        color_rgb=RARITY_COLORS["N"],
        color_hex="#FFFFFF",
        display_name="Common"
    ),
    RarityLevel.R: Rarity(
        level=RarityLevel.R,
        weight=5.0,
        color_rgb=RARITY_COLORS["R"],
        color_hex="#4A90E2",
        display_name="Rare"
    ),
    RarityLevel.SR: Rarity(
        level=RarityLevel.SR,
        weight=3.0,
        color_rgb=RARITY_COLORS["SR"],
        color_hex="#9370DB",
        display_name="Super Rare"
    ),
    RarityLevel.SSR: Rarity(
        level=RarityLevel.SSR,
        weight=1.0,
        color_rgb=RARITY_COLORS["SSR"],
        color_hex="#FFD700",
        display_name="Legendary"
    ),
}


def get_rarity_from_str(rarity_str: str) -> Rarity:
    """
    Get a rarity config from a string
    
    Args:
        rarity_str: rarity string such as "N", "R", "SR", "SSR"
    
    Returns:
        Rarity: the rarity config; N if unrecognized
    """
    rarity_str = str(rarity_str).strip().upper()
    try:
        level = RarityLevel(rarity_str)
        return RARITY_CONFIGS[level]
    except (ValueError, KeyError):
        # Default to Common rarity
        return RARITY_CONFIGS[RarityLevel.N]


def get_weight_from_rarity(rarity_str: str) -> float:
    """
    Get the weight for a rarity string
    
    Args:
        rarity_str: rarity string
    
    Returns:
        float: the corresponding weight
    """
    rarity = get_rarity_from_str(rarity_str)
    return rarity.weight

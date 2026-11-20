from enum import Enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.environment.region import Region
    from src.classes.core.avatar import Avatar

class TileType(Enum):
    PLAIN = "plain" # Plain
    WATER = "water" # Water
    SEA = "sea" # Sea
    MOUNTAIN = "mountain" # Mountain
    FOREST = "forest" # Forest
    CITY = "city" # City
    DESERT = "desert" # Desert
    RAINFOREST = "rainforest" # Rainforest
    GLACIER = "glacier" # Glacier/ice field
    SNOW_MOUNTAIN = "snow_mountain" # Snow mountain
    VOLCANO = "volcano" # Volcano
    GRASSLAND = "grassland" # Grassland
    SWAMP = "swamp" # Swamp
    CAVE = "cave" # Cave
    RUIN = "ruin" # Ruin
    FARM = "farm" # Farmland
    SECT = "sect" # Sect
    ISLAND = "island" # Island
    BAMBOO = "bamboo" # Bamboo forest
    GOBI = "gobi" # Gobi
    TUNDRA = "tundra" # Tundra
    MARSH = "marsh" # Marsh


# ============================================================
# 2x2 large tile config
# ============================================================

# Fixed large tile types (based on TileType)
LARGE_TILE_TYPES: set[TileType] = {
    TileType.CAVE,
    TileType.RUIN,
    TileType.SECT,
    TileType.CITY,
}

# Dynamic large tile prefixes (for sect names, city names, etc.)
# If a tile name stored in the map starts with one of these category subfolders, it is treated as a large tile
LARGE_TILE_CATEGORIES: set[str] = {"sect", "city"}


def is_large_tile(tile_name: str) -> bool:
    """
    Determine whether a tile name is a 2x2 large tile.
    
    Args:
        tile_name: the tile's name (e.g. "cave", or a sect/city tile name)
    
    Returns:
        Whether it is a large tile
    """
    # 1. Check whether it's a standard large TileType
    try:
        t = TileType(tile_name.lower())
        return t in LARGE_TILE_TYPES
    except ValueError:
        pass
    
    # 2. Non-standard types: sect names, city names, etc.
    # These tile names are sect/city identifiers whose slices live in the sects/ or cities/ directories
    # Since this can't be determined statically, assume every non-standard TileType name is a large tile
    # (because all normal tiles are in the TileType enum)
    return True


def get_large_tile_slices(tile_name: str) -> list[str]:
    """
    Get the 4 slice names of a large tile.
    
    Args:
        tile_name: the large tile's name
    
    Returns:
        List of 4 slice names [TL, TR, BL, BR]
    """
    return [f"{tile_name}_{i}" for i in range(4)]


@dataclass
class Tile():
    # The actual tile
    type: TileType
    x: int
    y: int
    region: 'Region' = None # Can be part of a region, or belong to no region

    @property
    def coordinate(self) -> tuple[int, int]:
        return (self.x, self.y)

    @property
    def location_name(self) -> str:
        """
        Get the current location's name.
        If it belongs to a region, return the region name; otherwise return 'Wilderness'.
        """
        from src.i18n import t
        return self.region.name if self.region else t("Wilderness")


from src.utils.distance import manhattan_distance

def get_avatar_distance(avatar1: 'Avatar', avatar2: 'Avatar') -> int:
    """
    Compute the Manhattan distance between two Avatars
    
    Args:
        avatar1: the first avatar
        avatar2: the second avatar
    
    Returns:
        The distance between the two avatars
    """
    return manhattan_distance((avatar1.pos_x, avatar1.pos_y), (avatar2.pos_x, avatar2.pos_y))

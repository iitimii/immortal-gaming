from enum import Enum
from collections import defaultdict


class EssenceType(Enum):
    """
    Essence (spiritual qi) type
    """
    GOLD = "GOLD"
    WOOD = "WOOD"
    WATER = "WATER"
    FIRE = "FIRE"
    EARTH = "EARTH"

    def __str__(self) -> str:
        """Return the translated name of the essence type"""
        from src.i18n import t
        return t(essence_msg_ids.get(self, self.value))
    
    @classmethod
    def from_str(cls, essence_str: str) -> 'EssenceType':
        """
        Create an EssenceType from a string
        
        Args:
            essence_str: string representation of the essence
            
        Returns:
            the matching EssenceType value
        """
        s = str(essence_str).strip().upper()
        
        mapping = {
            "GOLD": "GOLD",
            "WOOD": "WOOD",
            "WATER": "WATER",
            "FIRE": "FIRE",
            "EARTH": "EARTH"
        }
        
        etype_id = mapping.get(s)
        if etype_id:
            return cls(etype_id)
                
        raise ValueError(f"Unknown essence type: {essence_str}")

essence_msg_ids = {
    EssenceType.GOLD: "gold_essence",
    EssenceType.WOOD: "wood_essence",
    EssenceType.WATER: "water_essence",
    EssenceType.FIRE: "fire_essence",
    EssenceType.EARTH: "earth_essence"
}

class Essence():
    """
    Essence: describes the spiritual qi of a region.
    There are five kinds: gold, wood, water, fire, earth (more may be added later).
    Each region has all five kinds, each with its own density.
    Density ranges from 0 to 10.
    """
    def __init__(self, density: dict[EssenceType, int]):
        self.density = defaultdict(int)
        for essence_type, density in density.items():
            self.density[essence_type] = density

    def get_density(self, essence_type: EssenceType) -> int:
        return self.density[essence_type]

    def set_density(self, essence_type: EssenceType, density: int):
        self.density[essence_type] = density

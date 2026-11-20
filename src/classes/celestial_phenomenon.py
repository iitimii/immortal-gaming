"""
Heaven and earth phenomenon system
==================================

A heaven and earth phenomenon is a celestial anomaly affecting the whole cultivation world, providing global buffs/debuffs.

Characteristics:
- Not bound to any avatar; it is a world event
- Changes periodically (every 5 years by default)
- Supports conditions (e.g. targeting specific spirit roots, weapon types, etc.)
- Uses the effect system and merges with avatars' own effects

Extensibility:
- Multiple concurrent phenomena may be supported in the future (primary + secondary)
- Special events may trigger phenomenon changes in the future (e.g. ascension, great wars)
- Regional phenomena may be supported in the future (affecting only specific regions/sects)
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from src.utils.df import game_configs, get_str, get_int
from src.classes.effect import load_effect_from_str
from src.classes.rarity import Rarity, get_rarity_from_str


@dataclass
class CelestialPhenomenon:
    """
    Heaven and earth phenomenon (celestial anomaly)
    
    Fields correspond to static/game_configs/celestial_phenomenon.csv:
    - id: unique identifier
    - name: phenomenon name (xianxia style)
    - rarity: rarity (N/R/SR/SSR), determines display color and occurrence probability
    - effects: JSON effect config, supports conditions
    - desc: phenomenon description (used for UI display and event generation)
    - duration_years: duration in years (5 by default)
    """
    id: int
    name: str
    rarity: Rarity
    effects: dict[str, object]
    effect_desc: str
    desc: str
    duration_years: int
    
    @property
    def weight(self) -> float:
        """Occurrence weight derived from rarity"""
        return self.rarity.weight
    
    def get_info(self) -> str:
        """Get brief info"""
        return self.name
    
    def get_detailed_info(self) -> str:
        """Get detailed info"""
        from src.i18n import t
        effect_part = t(" Effect: {effect_desc}", effect_desc=self.effect_desc) if self.effect_desc else ""
        return t("{name} ({desc}{effect})", name=self.name, desc=self.desc, effect=effect_part)


def _load_celestial_phenomena() -> dict[int, CelestialPhenomenon]:
    """Load phenomenon data from the config table"""
    phenomena_by_id: dict[int, CelestialPhenomenon] = {}
    
    if "celestial_phenomenon" not in game_configs:
        return phenomena_by_id
    
    phenomenon_df = game_configs["celestial_phenomenon"]
    for row in phenomenon_df:
        # Parse rarity
        rarity_str = get_str(row, "rarity", "N").upper()
        rarity = get_rarity_from_str(rarity_str) if rarity_str and rarity_str != "NAN" else get_rarity_from_str("N")
        
        # Parse effects
        effects = load_effect_from_str(get_str(row, "effects"))
        from src.classes.effect import format_effects_to_text
        effect_desc = format_effects_to_text(effects)
        
        phenomenon = CelestialPhenomenon(
            id=get_int(row, "id"),
            name=get_str(row, "name"),
            rarity=rarity,
            effects=effects,
            effect_desc=effect_desc,
            desc=get_str(row, "desc"),
            duration_years=get_int(row, "duration_years", 5),
        )
        phenomena_by_id[phenomenon.id] = phenomenon
    
    return phenomena_by_id


# Global container
celestial_phenomena_by_id: dict[int, CelestialPhenomenon] = {}

def reload():
    """Reload data while keeping the global dict reference"""
    new_data = _load_celestial_phenomena()
    celestial_phenomena_by_id.clear()
    celestial_phenomena_by_id.update(new_data)

# Run once on module import
reload()


def get_random_celestial_phenomenon() -> Optional[CelestialPhenomenon]:
    """
    Pick a random phenomenon by weight
    
    Returns:
        CelestialPhenomenon, or None if none are available
    """
    if not celestial_phenomena_by_id:
        return None
    
    phenomena = list(celestial_phenomena_by_id.values())
    weights = [p.weight for p in phenomena]
    
    return random.choices(phenomena, weights=weights, k=1)[0]

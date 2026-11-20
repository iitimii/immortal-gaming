from __future__ import annotations

import random
import copy
from dataclasses import dataclass, field
from typing import Optional, Dict

from src.utils.df import game_configs, get_str, get_int
from src.classes.effect import load_effect_from_str
from src.systems.cultivation import Realm
from src.classes.weapon_type import WeaponType
from src.classes.items.item import Item


@dataclass
class Weapon(Item):
    """
    Weapon: equipment used in battle
    Fields correspond to static/game_configs/weapon.csv:
    - weapon_type: weapon type (sword, saber, spear, etc.)
    - realm: equipment grade (Qi Refinement/Foundation Establishment/Core Formation/Nascent Soul)
    - effects: parsed into a dict, merged with Avatar.effects
    """
    id: int
    name: str
    weapon_type: WeaponType
    realm: Realm
    desc: str
    effects: dict[str, object] = field(default_factory=dict)
    effect_desc: str = ""
    # Special attributes (e.g. the devoured soul count of the Ten Thousand Souls Banner)
    special_data: dict = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def instantiate(self) -> "Weapon":
        instance = copy.copy(self)
        instance.special_data = copy.deepcopy(self.special_data)
        return instance

    def get_info(self, detailed: bool = False) -> str:
        """Get info."""
        if detailed:
            return self.get_detailed_info()
        return f"{self.name}"

    def get_detailed_info(self) -> str:
        """Get detailed info."""
        from src.i18n import t
        effect_part = t(" Effect: {effect_desc}", effect_desc=self.effect_desc) if self.effect_desc else ""
        return f"[{self.id}] " + t("{name} ({type}·{realm}, {desc}){effect}",
                 name=self.name, type=str(self.weapon_type), realm=str(self.realm), 
                 desc=self.desc, effect=effect_part)
    
    def get_colored_info(self) -> str:
        """Get info with color markup for frontend rendering."""
        r, g, b = self.realm.color_rgb
        return f"<color:{r},{g},{b}>{self.get_info()}</color>"

    def get_structured_info(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "desc": self.desc,
            "grade": str(self.realm),
            "realm": str(self.realm),
            "color": self.realm.color_rgb,
            "type": self.weapon_type.value,
            "effect_desc": self.effect_desc,
        }


def _load_weapons_data() -> tuple[Dict[int, Weapon], Dict[str, Weapon]]:
    """Load weapon data from the config table.
    Returns: new (by ID, by name) mappings.
    """
    new_by_id: Dict[int, Weapon] = {}
    new_by_name: Dict[str, Weapon] = {}

    df = game_configs.get("weapon")
    if df is None:
        return new_by_id, new_by_name

    for row in df:
        effects = load_effect_from_str(get_str(row, "effects"))
        from src.classes.effect import format_effects_to_text
        effect_desc = format_effects_to_text(effects)

        # Parse weapon_type
        weapon_type_str = get_str(row, "weapon_type")
        weapon_type = WeaponType.from_str(weapon_type_str)
        
        # Parse grade
        grade_str = get_str(row, "grade", "QI_REFINEMENT")
        realm = Realm.from_str(grade_str)

        w = Weapon(
            id=get_int(row, "item_id"),
            name=get_str(row, "name"),
            weapon_type=weapon_type,
            realm=realm,
            desc=get_str(row, "desc"),
            effects=effects,
            effect_desc=effect_desc,
        )

        new_by_id[w.id] = w
        new_by_name[w.name] = w
        
        # Register in the global registry (note: after ItemRegistry is reset externally, items are re-registered here)
        from src.classes.items.registry import ItemRegistry
        ItemRegistry.register(w.id, w)

    return new_by_id, new_by_name

# Global containers
weapons_by_id: Dict[int, Weapon] = {}
weapons_by_name: Dict[str, Weapon] = {}

def reload():
    """Reload data while preserving the global dict references."""
    new_id, new_name = _load_weapons_data()
    
    weapons_by_id.clear()
    weapons_by_id.update(new_id)
    
    weapons_by_name.clear()
    weapons_by_name.update(new_name)

# Run once at module import
reload()


def get_random_weapon_by_realm(realm: Realm, weapon_type: Optional[WeaponType] = None) -> Optional[Weapon]:
    """Get a random weapon of the given realm (and optional type)."""
    candidates = [w for w in weapons_by_id.values() if w.realm == realm]
    if weapon_type is not None:
        candidates = [w for w in candidates if w.weapon_type == weapon_type]
        
    if not candidates:
        return None
    return random.choice(candidates).instantiate()

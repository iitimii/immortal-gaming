from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional, Dict

from src.utils.df import game_configs, get_str, get_int
from src.classes.effect import load_effect_from_str
from src.systems.cultivation import Realm
from src.classes.items.item import Item


TEN_THOUSAND_SOULS_BANNER_MAX_SOULS = 100_000


def get_ten_thousand_souls_banner_bonus(souls: int) -> int:
    thresholds = [
        (90_000, 8),
        (70_000, 7),
        (50_000, 6),
        (30_000, 5),
        (15_000, 4),
        (7_000, 3),
        (3_000, 2),
        (1_000, 1),
    ]
    for minimum_souls, bonus in thresholds:
        if souls >= minimum_souls:
            return bonus
    return 0


@dataclass
class Auxiliary(Item):
    """
    Auxiliary equipment: equipment providing various support functions
    Fields correspond to static/game_configs/auxiliary.csv:
    - realm: equipment grade (Qi Refinement/Foundation Establishment/Core Formation/Nascent Soul)
    - effects: parsed into a dict, merged with Avatar.effects
    """
    id: int
    name: str
    realm: Realm
    desc: str
    name_id: str = ""
    effects: dict[str, object] = field(default_factory=dict)
    effect_desc: str = ""
    # Special attributes (stores instance-specific data)
    special_data: dict = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def instantiate(self) -> "Auxiliary":
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
        souls = ""
        if is_ten_thousand_souls_banner(self) and self.special_data.get("devoured_souls", 0) > 0:
            soul_count = int(self.special_data["devoured_souls"])
            battle_bonus = get_ten_thousand_souls_banner_bonus(soul_count)
            souls = t(" Devoured Souls: {count}, Battle Bonus: +{bonus}", count=soul_count, bonus=battle_bonus)
        
        effect_part = t(" Effect: {effect_desc}", effect_desc=self.effect_desc) if self.effect_desc else ""
        return f"[{self.id}] {self.name} ({str(self.realm)}, {self.desc}{souls}){effect_part}"
    
    def get_colored_info(self) -> str:
        """Get info with color markup for frontend rendering."""
        r, g, b = self.realm.color_rgb
        return f"<color:{r},{g},{b}>{self.get_info()}</color>"

    def get_structured_info(self) -> dict:
        full_desc = self.desc
        # Special data handling
        souls = 0
        if is_ten_thousand_souls_banner(self):
            souls = self.special_data.get("devoured_souls", 0)
            if souls > 0:
                from src.i18n import t
                battle_bonus = get_ten_thousand_souls_banner_bonus(int(souls))
                full_desc = t(
                    "{desc} (Devoured Souls: {souls}, Battle Bonus: +{bonus})",
                    desc=full_desc,
                    souls=souls,
                    bonus=battle_bonus,
                )

        grade_display = str(self.realm)

        return {
            "id": str(self.id),
            "name": self.name,
            "desc": full_desc,
            "type": "auxiliary",
            "grade": grade_display,
            "realm": grade_display,
            "color": self.realm.color_rgb,
            "effect_desc": self.effect_desc,
        }


def _load_auxiliaries_data() -> tuple[Dict[int, Auxiliary], Dict[str, Auxiliary]]:
    """Load auxiliary data from the config table.
    Returns: new (by ID, by name) mappings.
    """
    new_by_id: Dict[int, Auxiliary] = {}
    new_by_name: Dict[str, Auxiliary] = {}

    df = game_configs.get("auxiliary")
    if df is None:
        return new_by_id, new_by_name

    for row in df:
        effects = load_effect_from_str(get_str(row, "effects"))
        from src.classes.effect import format_effects_to_text
        effect_desc = format_effects_to_text(effects)
        
        # Parse grade
        grade_str = get_str(row, "grade", "QI_REFINEMENT")
        realm = Realm.from_str(grade_str)

        a = Auxiliary(
            id=get_int(row, "item_id"),
            name_id=get_str(row, "name_id"),
            name=get_str(row, "name"),
            realm=realm,
            desc=get_str(row, "desc"),
            effects=effects,
            effect_desc=effect_desc,
        )

        new_by_id[a.id] = a
        new_by_name[a.name] = a
        
        # Register in the global registry
        from src.classes.items.registry import ItemRegistry
        ItemRegistry.register(a.id, a)

    return new_by_id, new_by_name

# Global containers
auxiliaries_by_id: Dict[int, Auxiliary] = {}
auxiliaries_by_name: Dict[str, Auxiliary] = {}

def reload():
    """Reload data while preserving the global dict references."""
    new_id, new_name = _load_auxiliaries_data()
    
    auxiliaries_by_id.clear()
    auxiliaries_by_id.update(new_id)
    
    auxiliaries_by_name.clear()
    auxiliaries_by_name.update(new_name)

# Run once at module import
reload()


TEN_THOUSAND_SOULS_BANNER_ID = 2064
TEN_THOUSAND_SOULS_BANNER_NAME_ID = "AUXILIARY_2064_NAME"


def is_ten_thousand_souls_banner(auxiliary: Auxiliary | None) -> bool:
    if auxiliary is None:
        return False
    if int(getattr(auxiliary, "id", 0) or 0) == TEN_THOUSAND_SOULS_BANNER_ID:
        return True
    if str(getattr(auxiliary, "name_id", "") or "") == TEN_THOUSAND_SOULS_BANNER_NAME_ID:
        return True
    # Legacy save-data fallback.
    return str(getattr(auxiliary, "name", "") or "") == "Ten Thousand Souls Banner"


def get_random_auxiliary_by_realm(realm: Realm) -> Optional[Auxiliary]:
    """Get a random auxiliary of the given realm."""
    import random
    candidates = [a for a in auxiliaries_by_id.values() if a.realm == realm]
    if not candidates:
        return None
    return random.choice(candidates).instantiate()

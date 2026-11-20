from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List
import json
from src.classes.effect import load_effect_from_str
from src.classes.color import Color, TECHNIQUE_GRADE_COLORS
from src.systems.cultivation import Realm

from src.utils.df import game_configs, get_str, get_float, get_int
from src.classes.alignment import Alignment
from src.classes.root import Root, RootElement


class TechniqueAttribute(Enum):
    GOLD = "GOLD"  # Metal
    WOOD = "WOOD"  # Wood
    WATER = "WATER"# Water
    FIRE = "FIRE"  # Fire
    EARTH = "EARTH"# Earth
    ICE = "ICE"    # Ice
    WIND = "WIND"  # Wind
    DARK = "DARK"  # Dark
    THUNDER = "THUNDER"  # Thunder
    EVIL = "EVIL"  # Evil

    def __str__(self) -> str:
        from src.i18n import t
        return t(technique_attribute_msg_ids.get(self, self.value))


technique_attribute_msg_ids = {
    TechniqueAttribute.GOLD: "gold_attribute",
    TechniqueAttribute.WOOD: "wood_attribute",
    TechniqueAttribute.WATER: "water_attribute",
    TechniqueAttribute.FIRE: "fire_attribute",
    TechniqueAttribute.EARTH: "earth_attribute",
    TechniqueAttribute.ICE: "ice_attribute",
    TechniqueAttribute.WIND: "wind_attribute",
    TechniqueAttribute.DARK: "dark_attribute",
    TechniqueAttribute.THUNDER: "thunder_attribute",
    TechniqueAttribute.EVIL: "evil_attribute",
}


class TechniqueGrade(Enum):
    LOWER = "LOWER"    # Lower grade
    MIDDLE = "MIDDLE"  # Middle grade
    UPPER = "UPPER"    # Upper grade

    def __str__(self) -> str:
        from src.i18n import t
        return t(technique_grade_msg_ids.get(self, self.value))

    @staticmethod
    def from_str(s: str) -> "TechniqueGrade":
        s = str(s).strip().upper()
        # Accept the enum names used in technique.csv
        mapping = {
            "UPPER": "UPPER",
            "MIDDLE": "MIDDLE",
            "LOWER": "LOWER"
        }
        grade_id = mapping.get(s, "LOWER")
        return TechniqueGrade(grade_id)
    
    @property
    def color_rgb(self) -> tuple[int, int, int]:
        """Return the RGB color for the technique grade."""
        color_map = {
            TechniqueGrade.LOWER: TECHNIQUE_GRADE_COLORS["LOWER"],
            TechniqueGrade.MIDDLE: TECHNIQUE_GRADE_COLORS["MIDDLE"],
            TechniqueGrade.UPPER: TECHNIQUE_GRADE_COLORS["UPPER"],
        }
        return color_map.get(self, Color.COMMON_WHITE)


technique_grade_msg_ids = {
    TechniqueGrade.LOWER: "lower_grade",
    TechniqueGrade.MIDDLE: "middle_grade",
    TechniqueGrade.UPPER: "upper_grade",
}


@dataclass
class Technique:
    id: int
    name: str
    attribute: TechniqueAttribute
    grade: TechniqueGrade
    desc: str
    weight: float
    condition: str
    realm: Realm | None = None
    # Owning sect ID; None means no sect requirement (rogue cultivators can learn it)
    sect_id: Optional[int] = None
    # Effects applied to avatars or systems
    effects: dict[str, object] = field(default_factory=dict)
    effect_desc: str = ""

    def is_allowed_for(self, avatar) -> bool:
        if not self.condition:
            return True
        return bool(eval(self.condition, {"__builtins__": {}}, {"avatar": avatar, "Alignment": Alignment}))

    def get_info(self, detailed: bool = False) -> str:
        if detailed:
            return self.get_detailed_info()
        from src.i18n import t
        return t("{name} ({attribute}) {grade}", name=self.name, attribute=str(self.attribute), grade=str(self.grade))

    def get_detailed_info(self) -> str:
        from src.i18n import t
        effect_part = t(" Effect: {effect_desc}", effect_desc=self.effect_desc) if self.effect_desc else ""
        return t("{name} ({attribute}) {grade} {desc}{effect}", 
                 name=self.name, attribute=str(self.attribute), grade=str(self.grade), 
                 desc=self.desc, effect=effect_part)
    
    def get_colored_info(self) -> str:
        """Get info with color markup for frontend rendering."""
        from src.i18n import t
        r, g, b = self.grade.color_rgb
        # Same format as get_info, but with color tags
        info = t("{name} ({attribute}·{grade})", name=self.name, attribute=str(self.attribute), grade=str(self.grade))
        return f"<color:{r},{g},{b}>{info}</color>"

    def get_structured_info(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "type": "technique",
            "desc": self.desc,
            "grade": str(self.grade),
            "realm": str(self.realm) if self.realm is not None else "",
            "color": self.grade.color_rgb,
            "attribute": str(self.attribute),
            "effect_desc": self.effect_desc,
        }

# Counter relationships among the five elements and extended attributes
# - Five elements: Metal counters Wood, Wood counters Earth, Earth counters Water, Water counters Fire, Fire counters Metal
# - Thunder counters Evil; Evil, Ice, Wind and Dark counter nothing
SUPPRESSION: dict[TechniqueAttribute, set[TechniqueAttribute]] = {
    TechniqueAttribute.GOLD: {TechniqueAttribute.WOOD},
    TechniqueAttribute.WOOD: {TechniqueAttribute.EARTH},
    TechniqueAttribute.EARTH: {TechniqueAttribute.WATER},
    TechniqueAttribute.WATER: {TechniqueAttribute.FIRE},
    TechniqueAttribute.FIRE: {TechniqueAttribute.GOLD},
    TechniqueAttribute.THUNDER: {TechniqueAttribute.EVIL},
    TechniqueAttribute.ICE: set(),
    TechniqueAttribute.WIND: set(),
    TechniqueAttribute.DARK: set(),
    TechniqueAttribute.EVIL: set(),
}


def _load_techniques_data() -> tuple[dict[int, Technique], dict[str, Technique]]:
    """Load technique data from the config table.
    Returns: new (techniques_by_id, techniques_by_name)
    """
    new_by_id: dict[int, Technique] = {}
    new_by_name: dict[str, Technique] = {}
    df = game_configs["technique"]
    for row in df:
        attr = TechniqueAttribute(get_str(row, "technique_root"))
        name = get_str(row, "name")
        grade = TechniqueGrade.from_str(get_str(row, "grade", "LOWER"))
        condition = get_str(row, "condition")
        weight = get_float(row, "weight", 1.0)
        
        sect_id_raw = get_int(row, "sect_id", -1)
        sect_id = sect_id_raw if sect_id_raw > 0 else None
            
        effects = load_effect_from_str(get_str(row, "effects"))
        from src.classes.effect import format_effects_to_text
        effect_desc = format_effects_to_text(effects)

        t = Technique(
            id=get_int(row, "id"),
            name=name,
            attribute=attr,
            grade=grade,
            realm=Realm.from_str(get_str(row, "realm")) if get_str(row, "realm") else None,
            desc=get_str(row, "desc"),
            weight=weight,
            condition=condition,
            sect_id=sect_id,
            effects=effects,
            effect_desc=effect_desc,
        )
        new_by_id[t.id] = t
        new_by_name[t.name] = t
    return new_by_id, new_by_name


# Global containers (keep references stable)
techniques_by_id: dict[int, Technique] = {}
techniques_by_name: dict[str, Technique] = {}

def reload():
    """Reload data while preserving the global dict references."""
    new_id, new_name = _load_techniques_data()
    
    techniques_by_id.clear()
    techniques_by_id.update(new_id)
    
    techniques_by_name.clear()
    techniques_by_name.update(new_name)

# Run once at module import
reload()


def is_attribute_compatible_with_root(attr: TechniqueAttribute, root: Root) -> bool:
    if attr == TechniqueAttribute.EVIL:
        # Evil techniques are constrained only by alignment; treated as unrelated to spiritual roots here
        return True

    # Heavenly spiritual root: can cultivate all types except Evil
    if root == Root.HEAVEN:
        return attr != TechniqueAttribute.EVIL

    # Single-attribute spiritual root: can only cultivate the matching attribute
    single_map = {
        Root.GOLD: TechniqueAttribute.GOLD,
        Root.WOOD: TechniqueAttribute.WOOD,
        Root.WATER: TechniqueAttribute.WATER,
        Root.FIRE: TechniqueAttribute.FIRE,
        Root.EARTH: TechniqueAttribute.EARTH,
    }
    if root in single_map:
        return attr == single_map[root]

    # Compound/extended spiritual roots: the root's own attribute + the attributes in its element list
    complex_map: dict[Root, set[TechniqueAttribute]] = {
        Root.ICE: {TechniqueAttribute.ICE, TechniqueAttribute.GOLD, TechniqueAttribute.WATER},
        Root.WIND: {TechniqueAttribute.WIND, TechniqueAttribute.WOOD, TechniqueAttribute.WATER},
        Root.DARK: {TechniqueAttribute.DARK, TechniqueAttribute.FIRE, TechniqueAttribute.EARTH},
        Root.THUNDER: {TechniqueAttribute.THUNDER, TechniqueAttribute.WATER, TechniqueAttribute.EARTH},
    }
    if root in complex_map:
        return attr in complex_map[root]

    return False

def get_random_technique_for_avatar(avatar) -> Technique:
    import random
    candidates: List[Technique] = []
    for t in techniques_by_id.values():
        if not t.is_allowed_for(avatar):
            continue
        if t.attribute == TechniqueAttribute.EVIL and avatar.alignment != Alignment.EVIL:
            continue
        if not is_attribute_compatible_with_root(t.attribute, avatar.root):
            continue
        candidates.append(t)
    if not candidates:
        # Fallback: ignore conditions, pick only by spiritual root compatibility (if still empty, use all)
        fallback = [
            t for t in techniques_by_id.values()
            if (t.attribute != TechniqueAttribute.EVIL) and is_attribute_compatible_with_root(t.attribute, avatar.root)
        ]
        candidates = fallback or list(techniques_by_id.values())
    weights = [max(0.0, t.weight) for t in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]


def get_random_upper_technique_for_avatar(avatar) -> Technique | None:
    """
    Return an upper-grade technique compatible with the avatar's spiritual root/alignment/conditions; None if none.
    Only used to prefer upper-grade techniques for fortune rewards.
    """
    import random
    candidates: List[Technique] = []
    for t in techniques_by_id.values():
        if t.grade is not TechniqueGrade.UPPER:
            continue
        if not t.is_allowed_for(avatar):
            continue
        if t.attribute == TechniqueAttribute.EVIL and avatar.alignment != Alignment.EVIL:
            continue
        if not is_attribute_compatible_with_root(t.attribute, avatar.root):
            continue
        candidates.append(t)
    if not candidates:
        return None
    weights = [max(0.0, t.weight) for t in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]

def get_technique_by_sect(sect) -> Technique:
    """
    Simplified: filter only by sect and sample by weight, ignoring spiritual roots and conditions.
    - Rogue cultivators (sect is None): sample only from techniques without a sect requirement (sect_id is None);
    - With a sect: sample from techniques with "no sect + this sect";
    If the set is empty, fall back to all techniques.
    """
    import random

    target_sect_id: Optional[int] = None
    if sect is not None:
        target_sect_id = getattr(sect, "id", None)

    allowed_sect_ids: set[Optional[int]] = {None}
    if target_sect_id is not None:
        allowed_sect_ids.add(target_sect_id)

    def _in_allowed_sect(t: Technique) -> bool:
        return t.sect_id in allowed_sect_ids

    candidates: List[Technique] = [t for t in techniques_by_id.values() if _in_allowed_sect(t)]
    if not candidates:
        candidates = list(techniques_by_id.values())
    weights = [max(0.0, t.weight) for t in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]


def get_suppression_bonus(att_attr: TechniqueAttribute, def_attr: TechniqueAttribute) -> float:
    return 0.10 if def_attr in SUPPRESSION.get(att_attr, set()) else 0.0



# Map technique attributes to default spiritual roots (Evil techniques return nothing)
def attribute_to_root(attr: TechniqueAttribute) -> Optional[Root]:
    mapping: dict[TechniqueAttribute, Root] = {
        TechniqueAttribute.GOLD: Root.GOLD,
        TechniqueAttribute.WOOD: Root.WOOD,
        TechniqueAttribute.WATER: Root.WATER,
        TechniqueAttribute.FIRE: Root.FIRE,
        TechniqueAttribute.EARTH: Root.EARTH,
        TechniqueAttribute.THUNDER: Root.THUNDER,
        TechniqueAttribute.ICE: Root.ICE,
        TechniqueAttribute.WIND: Root.WIND,
        TechniqueAttribute.DARK: Root.DARK,
    }
    return mapping.get(attr)

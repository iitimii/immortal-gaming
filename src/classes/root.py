"""
Spiritual roots
Five elements and spiritual root combinations:
- RootElement: Metal, Wood, Water, Fire, Earth (constant)
- Root: hard-coded definitions (single/dual/heavenly roots etc.); each member holds (name msgid, element list)
"""
from enum import Enum
from typing import List, Tuple, Dict
from collections import defaultdict
from src.utils.df import game_configs
from src.classes.effect import build_effects_map_from_df

from src.classes.essence import EssenceType


class RootElement(Enum):
    GOLD = "GOLD"  # Metal
    WOOD = "WOOD"  # Wood
    WATER = "WATER"  # Water
    FIRE = "FIRE"  # Fire
    EARTH = "EARTH"  # Earth

    def __str__(self) -> str:
        from src.i18n import t
        return t(root_element_msg_ids.get(self, self.value))


root_element_msg_ids = {
    RootElement.GOLD: "gold_element",
    RootElement.WOOD: "wood_element",
    RootElement.WATER: "water_element",
    RootElement.FIRE: "fire_element",
    RootElement.EARTH: "earth_element",
}


class _RootMixin:
    """
    Base implementation of Root: member values are (name msgid, element tuple).
    The real Root enum is created dynamically via the functional API.
    """

    def __new__(cls, cn_name: str, elements: Tuple[RootElement, ...]):
        obj = object.__new__(cls)
        obj._value_ = cn_name
        obj._elements = elements
        return obj

    @property
    def elements(self) -> Tuple[RootElement, ...]:
        return self._elements

    def __str__(self) -> str:
        return f"{self.value}({', '.join(str(e) for e in self.elements)})"


class Root(_RootMixin, Enum):
    """
    Spiritual roots (hard-coded): member values are (name msgid, element tuple).
    The data originally came from CSV and is now built in:
    - GOLD: Metal Root -> Metal
    - WOOD: Wood Root -> Wood
    - WATER: Water Root -> Water
    - FIRE: Fire Root -> Fire
    - EARTH: Earth Root -> Earth
    - THUNDER: Thunder Root -> Water;Earth
    - ICE: Ice Root -> Metal;Water
    - WIND: Wind Root -> Wood;Water
    - DARK: Dark Root -> Fire;Earth
    - HEAVEN: Heavenly Root -> Metal;Wood;Water;Fire;Earth (extra breakthrough +0.1)
    """

    GOLD = ("root_gold", (RootElement.GOLD,))
    WOOD = ("root_wood", (RootElement.WOOD,))
    WATER = ("root_water", (RootElement.WATER,))
    FIRE = ("root_fire", (RootElement.FIRE,))
    EARTH = ("root_earth", (RootElement.EARTH,))
    THUNDER = ("root_thunder", (RootElement.WATER, RootElement.EARTH))
    ICE = ("root_ice", (RootElement.GOLD, RootElement.WATER))
    WIND = ("root_wind", (RootElement.WOOD, RootElement.WATER))
    DARK = ("root_dark", (RootElement.FIRE, RootElement.EARTH))
    HEAVEN = (
        "root_heaven",
        (
            RootElement.GOLD,
            RootElement.WOOD,
            RootElement.WATER,
            RootElement.FIRE,
            RootElement.EARTH,
        ),
    )

    def get_info(self) -> str:
        return format_root_cn(self)

    def get_detailed_info(self) -> str:
        return self.get_info()

    @property
    def effects(self) -> dict[str, object]:
        """
        This root's effects as read from CSV.
        """
        return dict(_root_effects_by_root.get(self, {}))

    @property
    def effect_desc(self) -> str:
        """
        Get the text description of the root's effects.
        """
        return _root_effect_desc_by_root.get(self, "")


# One-to-one mapping from elements to qi types
_essence_by_element = {
    RootElement.GOLD: EssenceType.GOLD,
    RootElement.WOOD: EssenceType.WOOD,
    RootElement.WATER: EssenceType.WATER,
    RootElement.FIRE: EssenceType.FIRE,
    RootElement.EARTH: EssenceType.EARTH,
}


def get_essence_types_for_root(root: "Root") -> List[EssenceType]:
    """
    Get the list of qi types matching this root (a match on any element counts as usable).
    """
    return [_essence_by_element[e] for e in root.elements]


def _parse_root_key(raw: str) -> "Root":
    return Root[raw]


_root_effects_by_root = build_effects_map_from_df(
    game_configs.get("root"),
    key_column="key",
    parse_key=_parse_root_key,
    effects_column="effects",
)

from src.classes.effect import format_effects_to_text
_root_effect_desc_by_root = {
    root: format_effects_to_text(effects)
    for root, effects in _root_effects_by_root.items()
}

def format_root_cn(root: "Root") -> str:
    """
    Display a Root as a short name + composition, e.g.:
    - Heavenly (Metal, Wood, Water, Fire, Earth)
    - Wind (Wood, Water)
    - Metal
    Fallback: show only the short name if the composition can't be obtained.
    """
    from src.i18n import t
    # The value of a Root member is a msgid (e.g. "root_wind")
    name_key = getattr(root, "value", str(root))
    translated_name = t(name_key)
    
    # Try to get the short name (without the "Root" suffix)
    # Short-name keys could be defined separately in the translation files, or the string handled here
    # For simplicity, strip the "Root" suffix from the translated name
    # Alternative: define root_short_wind -> "Wind"
    # To stay compatible with the existing structure, the translated string is handled simply for now.
    
    short_name = translated_name.replace(" Root", "")
    
    elements = getattr(root, "elements", None)
    if not elements:
        return short_name
    if len(elements) <= 1:
        return short_name
    # RootElement.__str__ returns the translated value
    elements_cn = t("element_separator").join(str(e) for e in elements)
    return t("{root_name} ({elements})", root_name=short_name, elements=elements_cn)

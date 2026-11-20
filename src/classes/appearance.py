from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, List, Tuple


@dataclass
class Appearance:
    """
    Appearance / looks
    """
    level: int  # 1~10
    name: str
    desc_male: str
    desc_female: str

    def get_info(self) -> str:
        from src.i18n import t
        return f"{t(self.name)}({self.level})"

    def get_detailed_info(self, gender: object | None = None) -> str:
        """
        Return a more fitting description by gender; if gender isn't given or can't be recognized, the male description is used by default.
        Doesn't depend on a concrete Gender type, to avoid circular imports.
        """
        from src.i18n import t
        g = str(gender) if gender is not None else ""
        s = g.lower()
        use_female = s == "female"
        desc = self.desc_female if use_female else self.desc_male
        return f"{t(self.name)}({self.level}) - {t(desc)}"


_LEVEL_DATA: Tuple[Tuple[int, str, str, str], ...] = (
    # level, name, desc_male, desc_female
    (1, "appearance_1_name", "appearance_1_desc_male", "appearance_1_desc_female"),
    (2, "appearance_2_name", "appearance_2_desc_male", "appearance_2_desc_female"),
    (3, "appearance_3_name", "appearance_3_desc_male", "appearance_3_desc_female"),
    (4, "appearance_4_name", "appearance_4_desc_male", "appearance_4_desc_female"),
    (5, "appearance_5_name", "appearance_5_desc_male", "appearance_5_desc_female"),
    (6, "appearance_6_name", "appearance_6_desc_male", "appearance_6_desc_female"),
    (7, "appearance_7_name", "appearance_7_desc_male", "appearance_7_desc_female"),
    (8, "appearance_8_name", "appearance_8_desc_male", "appearance_8_desc_female"), 
    (9, "appearance_9_name", "appearance_9_desc_male", "appearance_9_desc_female"),
    (10, "appearance_10_name", "appearance_10_desc_male", "appearance_10_desc_female"),
)


def _build_pool(data: Iterable[Tuple[int, str, str, str]]) -> List[Appearance]:
    pool: List[Appearance] = []
    for level, name, dm, df in data:
        pool.append(Appearance(level=level, name=name, desc_male=dm, desc_female=df))
    return pool


_APPEARANCE_POOL: List[Appearance] = _build_pool(_LEVEL_DATA)


def get_random_appearance() -> Appearance:
    """Return a random appearance instance."""
    # Construct a new instance to avoid sharing the same object reference
    base = random.choice(_APPEARANCE_POOL)
    return Appearance(level=base.level, name=base.name, desc_male=base.desc_male, desc_female=base.desc_female)


def get_appearance_by_level(level: int) -> Appearance:
    """
    Return an appearance instance by level (1-10); out-of-range values are clamped.
    Returns a new instance so callers don't hold references into the pool.
    """
    lv = int(level)
    if lv < 1:
        lv = 1
    if lv > 10:
        lv = 10
    base = next((a for a in _APPEARANCE_POOL if a.level == lv), _APPEARANCE_POOL[-1])
    return Appearance(level=base.level, name=base.name, desc_male=base.desc_male, desc_female=base.desc_female)


__all__ = [
    "Appearance",
    "get_random_appearance",
    "get_appearance_by_level",
]



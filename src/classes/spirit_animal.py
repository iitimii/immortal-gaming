from __future__ import annotations

from dataclasses import dataclass

from src.systems.cultivation import Realm


@dataclass
class SpiritAnimal:
    """
    Spirit animal: the single "guardian spirit animal" attached to an Avatar.
    Only records the name and realm, and grants fixed battle strength points by realm.
    
    Rules:
    - Qi Refinement/Foundation Establishment/Core Formation/Nascent Soul give +2/+4/+6/+8 battle strength points
    - An Avatar can have at most one spirit_animal; a new one replaces the old.
    """

    name: str
    realm: Realm

    def get_extra_strength_points(self) -> int:
        mapping = {
            Realm.Qi_Refinement: 2,
            Realm.Foundation_Establishment: 4,
            Realm.Core_Formation: 6,
            Realm.Nascent_Soul: 8,
        }
        return mapping.get(self.realm, 0)

    def get_info(self) -> str:
        return f"{self.name} ({str(self.realm)})"

    @property
    def effects(self) -> dict[str, object]:
        """
        The spirit animal's effects. Currently only battle strength points; other keys may be added later.
        """
        pts = self.get_extra_strength_points()
        return {"extra_battle_strength_points": pts} if pts else {}

    def get_structured_info(self) -> dict:
        from src.classes.effect import format_effects_to_text
        return {
            "name": self.name,
            "desc": f"Realm: {str(self.realm)}",
            "grade": str(self.realm),
            "effect_desc": format_effects_to_text(self.effects),
        }



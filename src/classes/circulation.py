from __future__ import annotations
from typing import Dict, List, TYPE_CHECKING, Any
import copy

if TYPE_CHECKING:
    from src.classes.items.weapon import Weapon
    from src.classes.items.auxiliary import Auxiliary
    from src.classes.items.elixir import Elixir


class CirculationManager:
    """
    Manager for circulation of items released into the world
    Records all valuable items that leave avatars (sold, dropped on death and not seized, etc.)
    Used as the item pool for later features such as auctions
    """
    
    def __init__(self):
        # Stores sold weapons
        self.sold_weapons: List[Weapon] = []
        # Stores sold auxiliaries
        self.sold_auxiliaries: List[Auxiliary] = []
        # Stores sold elixirs
        self.sold_elixirs: List[Elixir] = []
        
    @property
    def sold_item_count(self) -> int:
        """Track the total number of sold items."""
        return len(self.sold_weapons) + len(self.sold_auxiliaries) + len(self.sold_elixirs)

    def add_weapon(self, weapon: "Weapon") -> None:
        """Record an outgoing weapon."""
        if weapon is None:
            return
        # Store a deep copy so external changes don't affect the record
        # Note: this assumes the weapon object can be copied
        self.sold_weapons.append(weapon.instantiate())
        
    def add_auxiliary(self, auxiliary: "Auxiliary") -> None:
        """Record an outgoing auxiliary."""
        if auxiliary is None:
            return
        self.sold_auxiliaries.append(auxiliary.instantiate())

    def add_elixir(self, elixir: "Elixir") -> None:
        """Record an outgoing elixir."""
        if elixir is None:
            return
        # Try to instantiate; if that fails (e.g. not implemented), copy, or store directly
        if hasattr(elixir, "instantiate"):
            self.sold_elixirs.append(elixir.instantiate())
        else:
            self.sold_elixirs.append(copy.copy(elixir))

    def add_item(self, item: Any) -> None:
        """
        Generic entry point: record an outgoing item.
        Dispatches automatically to the matching storage list by item type.
        This method unifies all item outflow logic so business modules don't have to check types manually.
        """
        if item is None:
            return
            
        from src.classes.items.weapon import Weapon
        from src.classes.items.auxiliary import Auxiliary
        from src.classes.items.elixir import Elixir
        
        if isinstance(item, Weapon):
            self.add_weapon(item)
        elif isinstance(item, Auxiliary):
            self.add_auxiliary(item)
        elif isinstance(item, Elixir):
            self.add_elixir(item)
        # Other types may be added in the future...

    def remove_item(self, item: Any) -> None:
        """
        Remove an item from the circulation pool
        """
        from src.classes.items.weapon import Weapon
        from src.classes.items.auxiliary import Auxiliary
        from src.classes.items.elixir import Elixir
        
        if isinstance(item, Weapon):
            if item in self.sold_weapons:
                self.sold_weapons.remove(item)
        elif isinstance(item, Auxiliary):
            if item in self.sold_auxiliaries:
                self.sold_auxiliaries.remove(item)
        elif isinstance(item, Elixir):
            if item in self.sold_elixirs:
                self.sold_elixirs.remove(item)
    
    def to_save_dict(self) -> dict:
        """Serialize to a dict for saving."""
        return {
            "weapons": [self._item_to_dict(w) for w in self.sold_weapons],
            "auxiliaries": [self._item_to_dict(a) for a in self.sold_auxiliaries],
            "elixirs": [self._item_to_dict(e) for e in self.sold_elixirs]
        }
    
    def load_from_dict(self, data: dict) -> None:
        """Restore data from a dict."""
        from src.classes.items.weapon import weapons_by_id
        from src.classes.items.auxiliary import auxiliaries_by_id
        from src.classes.items.elixir import elixirs_by_id
        
        self.sold_weapons = []
        for w_data in data.get("weapons", []):
            w_id = w_data.get("id")
            if w_id in weapons_by_id:
                weapon = copy.copy(weapons_by_id[w_id])
                weapon.special_data = w_data.get("special_data", {})
                self.sold_weapons.append(weapon)
                
        self.sold_auxiliaries = []
        for a_data in data.get("auxiliaries", []):
            a_id = a_data.get("id")
            if a_id in auxiliaries_by_id:
                auxiliary = copy.copy(auxiliaries_by_id[a_id])
                auxiliary.special_data = a_data.get("special_data", {})
                self.sold_auxiliaries.append(auxiliary)

        self.sold_elixirs = []
        for e_data in data.get("elixirs", []):
            e_id = e_data.get("id")
            if e_id in elixirs_by_id:
                elixir = copy.copy(elixirs_by_id[e_id])
                elixir.special_data = e_data.get("special_data", {})
                self.sold_elixirs.append(elixir)

    def _item_to_dict(self, item) -> dict:
        """Convert an item object into a compact storage format."""
        return {
            "id": item.id,
            "special_data": getattr(item, "special_data", {})
        }


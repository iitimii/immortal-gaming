"""
Unified price system
============

All item/equipment prices are obtained through this module.
Prices are bound only to the corresponding realm and are globally uniform.

Price design reference (based on a Qi Refinement annual income of about 20-30 spirit stones):
- Material: gathered goods and other consumables
- Weapon: rare equipment, relatively high value
- Auxiliary: treasures etc., valued below weapons
"""
from __future__ import annotations

from typing import Union, TYPE_CHECKING

from src.systems.cultivation import Realm

if TYPE_CHECKING:
    from src.classes.material import Material
    from src.classes.items.weapon import Weapon
    from src.classes.items.auxiliary import Auxiliary
    from src.classes.core.avatar import Avatar

# Type alias
Sellable = Union["Material", "Weapon", "Auxiliary"]


class Prices:
    """
    Price system.
    Prices of all items/equipment tradable in towns are managed here.
    """
    
    # Global buy multiplier (premium when the player buys from the system)
    GLOBAL_BUY_MULTIPLIER = 1.5
    
    # Material price table (gathered goods etc.)
    MATERIAL_PRICES = {
        Realm.Qi_Refinement: 10,
        Realm.Foundation_Establishment: 30,
        Realm.Core_Formation: 50,
        Realm.Nascent_Soul: 70,
    }
    
    # Weapon price table (rare, high value)
    WEAPON_PRICES = {
        Realm.Qi_Refinement: 150,
        Realm.Foundation_Establishment: 300,
        Realm.Core_Formation: 1000,
        Realm.Nascent_Soul: 2000,
    }
    
    # Auxiliary price table
    AUXILIARY_PRICES = {
        Realm.Qi_Refinement: 150,
        Realm.Foundation_Establishment: 250,
        Realm.Core_Formation: 800,
        Realm.Nascent_Soul: 1600,
    }
    
    def get_material_price(self, material: "Material") -> int:
        """Get the base price of a material."""
        return self.MATERIAL_PRICES.get(material.realm, 10)
    
    def get_weapon_price(self, weapon: "Weapon") -> int:
        """Get the base price of a weapon."""
        return self.WEAPON_PRICES.get(weapon.realm, 100)
    
    def get_auxiliary_price(self, auxiliary: "Auxiliary") -> int:
        """Get the base price of an auxiliary."""
        return self.AUXILIARY_PRICES.get(auxiliary.realm, 80)
    
    def get_price(self, obj: Sellable) -> int:
        """
        Unified base price lookup.
        Dispatches automatically to the matching price method by object type.
        Note: this is the item's [base value], usually equal to the base price when the player [sells to the system].
        """
        from src.classes.material import Material
        from src.classes.items.weapon import Weapon
        from src.classes.items.auxiliary import Auxiliary
        from src.classes.items.elixir import Elixir
        
        if isinstance(obj, Material):
            return self.get_material_price(obj)
        elif isinstance(obj, Weapon):
            return self.get_weapon_price(obj)
        elif isinstance(obj, Auxiliary):
            return self.get_auxiliary_price(obj)
        elif isinstance(obj, Elixir):
            return obj.price
        return 0

    def get_buying_price(self, obj: Sellable, buyer: "Avatar" = None) -> int:
        """
        Get the player's buying price (buying from the system store).
        
        Formula:
            base price * max(1.0, GLOBAL_BUY_MULTIPLIER - discount)
            
        Args:
            obj: the traded item
            buyer: the buyer (used to compute the discount)
        """
        base_price = self.get_price(obj)
        
        # Default multiplier 1.5
        multiplier = self.GLOBAL_BUY_MULTIPLIER
        
        if buyer is not None:
            # Get the discount (multiplier reduction)
            # e.g. 0.1 means multiplier -0.1
            reduction = float(buyer.effects.get("shop_buy_price_reduction", 0.0))
            multiplier -= reduction
            
        # Ensure the multiplier is not below 1.0 (original price)
        final_multiplier = max(1.0, multiplier)
        
        return int(base_price * final_multiplier)

    def get_selling_price(self, obj: Sellable, seller: "Avatar" = None) -> int:
        """
        Get the player's selling price (selling to the system store).
        
        Formula:
            base price * (1.0 + sell bonus)
            
        Args:
            obj: the traded item
            seller: the seller (used to compute the bonus)
        """
        base_price = self.get_price(obj)
        
        multiplier = 1.0
        
        if seller is not None:
            # Get the sell bonus
            # e.g. 0.2 means price +20%
            bonus = float(seller.effects.get("extra_item_sell_price_multiplier", 0.0))
            multiplier += bonus
            
        return int(base_price * multiplier)


# Global singleton
prices = Prices()

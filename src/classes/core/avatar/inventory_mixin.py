"""
Avatar item and equipment management mixin
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Any, Union

if TYPE_CHECKING:
    from src.classes.core.avatar.core import Avatar
    from src.classes.material import Material
    from src.classes.items.weapon import Weapon
    from src.classes.items.auxiliary import Auxiliary
    from src.classes.items.elixir import Elixir


class InventoryMixin:
    """Item and equipment management methods."""
    
    def add_material(self: "Avatar", material: "Material", quantity: int = 1) -> None:
        """
        Add an item to the inventory.
        
        Args:
            material: the item to add
            quantity: quantity to add, default 1
        """
        if quantity <= 0:
            return
            
        if material in self.materials:
            self.materials[material] += quantity
        else:
            self.materials[material] = quantity
    
    def remove_material(self: "Avatar", material: "Material", quantity: int = 1) -> bool:
        """
        Remove a material from the inventory.
        
        Args:
            material: the material to remove
            quantity: quantity to remove, default 1
            
        Returns:
            bool: whether removal succeeded (False if there isn't enough)
        """
        if quantity <= 0:
            return True
            
        if material not in self.materials:
            return False
            
        if self.materials[material] < quantity:
            return False
            
        self.materials[material] -= quantity
        
        # If the quantity drops to 0, remove the item from the dict
        if self.materials[material] == 0:
            del self.materials[material]
            
        return True
    
    def get_material_quantity(self: "Avatar", material: "Material") -> int:
        """
        Get the quantity of a given material.
        
        Args:
            material: the material to query
            
        Returns:
            int: material quantity, 0 if none
        """
        return self.materials.get(material, 0)

    def change_weapon(self: "Avatar", new_weapon: Optional["Weapon"]) -> None:
        """
        Change weapon: proficiency resets to zero and long-term effects are recalculated.
        
        Args:
            new_weapon: the new weapon
        """
        self.weapon = new_weapon
        self.weapon_proficiency = 0.0
        self.recalc_effects()
    
    def change_auxiliary(self: "Avatar", new_auxiliary: Optional["Auxiliary"]) -> None:
        """
        Change auxiliary equipment and recalculate long-term effects.
        
        Args:
            new_auxiliary: the new auxiliary (None means unequip)
        """
        self.auxiliary = new_auxiliary
        self.recalc_effects()
    
    def increase_weapon_proficiency(self: "Avatar", amount: float) -> None:
        """
        Increase weapon proficiency, capped at 100.
        
        Args:
            amount: proficiency to add
        """
        # Apply the extra_weapon_proficiency_gain effect (multiplier bonus)
        gain_multiplier = 1.0 + self.effects.get("extra_weapon_proficiency_gain", 0.0)
        actual_amount = amount * gain_multiplier
        self.weapon_proficiency = min(100.0, self.weapon_proficiency + actual_amount)

    # ==================== Selling ====================
    
    def sell_material(self: "Avatar", material: "Material", quantity: int = 1) -> int:
        """
        Sell materials and return the spirit stones earned.
        Applies the extra_item_sell_price_multiplier effect.
        """
        from src.classes.prices import prices
        
        if quantity <= 0 or self.get_material_quantity(material) < quantity:
            return 0
        
        self.remove_material(material, quantity)
        
        # Use the unified sell price interface (includes all bonus logic)
        unit_price = prices.get_selling_price(material, self)
        total = unit_price * quantity
        
        self.magic_stone = self.magic_stone + total
        return total

    def sell_weapon(self: "Avatar", weapon: "Weapon") -> int:
        """
        Sell a weapon and return the spirit stones earned.
        Note: this is a helper; it does not automatically unequip the current equipment.
        """
        from src.classes.prices import prices
        
        # Record circulation
        self.world.circulation.add_weapon(weapon)

        # Use the unified sell price interface
        total = prices.get_selling_price(weapon, self)
        self.magic_stone = self.magic_stone + total
        return total

    def sell_auxiliary(self: "Avatar", auxiliary: "Auxiliary") -> int:
        """
        Sell an auxiliary and return the spirit stones earned.
        Note: this is a helper; it does not automatically unequip the current equipment.
        """
        from src.classes.prices import prices
        
        # Record circulation
        self.world.circulation.add_auxiliary(auxiliary)

        # Use the unified sell price interface
        total = prices.get_selling_price(auxiliary, self)
        self.magic_stone = self.magic_stone + total
        return total

    def sell_elixir(self: "Avatar", elixir: "Elixir") -> int:
        """
        Sell an elixir and return the spirit stones earned.
        """
        from src.classes.prices import prices
        
        # Record circulation
        self.world.circulation.add_elixir(elixir)
        
        # Use the unified sell price interface
        total = prices.get_selling_price(elixir, self)
        self.magic_stone = self.magic_stone + total
        return total

    # ==================== Buying ====================

    def can_buy_item(self: "Avatar", obj: Any) -> tuple[bool, str]:
        """
        Check whether the given item can be bought.
        Covers price checks, realm limits, drug tolerance, etc.
        """
        from src.classes.items.elixir import Elixir
        from src.classes.prices import prices
        from src.systems.cultivation import Realm
        
        # 1. Check the price
        price = prices.get_buying_price(obj, self)
        if self.magic_stone < price:
            return False, f"Not enough spirit stones (need {price})"

        # 2. Elixir-specific checks
        if isinstance(obj, Elixir):
            # Realm limit
            if obj.realm > self.cultivation_progress.realm:
                # Use str() to trigger Realm.__str__ for i18n translation.
                return False, f"Realm too low to withstand the elixir's potency ({str(obj.realm)})"

            # Tolerance / already-active check
            for consumed in self.elixirs:
                if consumed.elixir.id == obj.id:
                    if not consumed.is_completely_expired(int(self.world.month_stamp)):
                        return False, "The elixir's effect is still active; it cannot be taken again"
                
        return True, ""

    def buy_item(self: "Avatar", obj: Any) -> dict:
        """
        Execute the purchase.
        Includes payment, receiving the item (consume / add to inventory / equip), and trade-in.
        Returns a transaction report dict.
        """
        from src.classes.items.elixir import Elixir
        from src.classes.items.weapon import Weapon
        from src.classes.items.auxiliary import Auxiliary
        from src.classes.material import Material
        from src.classes.prices import prices
        
        report = {
            "success": True,
            "cost": 0,
            "action_type": "store", # store, consume, equip
            "sold_item_name": None,
            "sold_item_refund": 0
        }
        
        # 1. Pay
        price = prices.get_buying_price(obj, self)
        self.magic_stone -= price
        report["cost"] = price
        
        # 2. Deliver
        if isinstance(obj, Elixir):
            # Consumed on purchase
            self.consume_elixir(obj)
            report["action_type"] = "consume"
            
        elif isinstance(obj, Material):
            # Add to inventory
            self.add_material(obj)
            report["action_type"] = "store"
            
        elif isinstance(obj, (Weapon, Auxiliary)):
            # Equipment needs a deep copy
            new_equip = obj.instantiate()
            
            # Try to sell the old equipment and equip the new one
            sold_name, refund = self._equip_and_trade_in(new_equip)
            
            report["action_type"] = "equip"
            if sold_name:
                report["sold_item_name"] = sold_name
                report["sold_item_refund"] = refund
            
        return report

    def _equip_and_trade_in(self: "Avatar", new_equip: Union["Weapon", "Auxiliary"]) -> tuple[str | None, int]:
        """
        Internal: equip a new item and try to sell the old one (if any).
        Returns: (old item name, sale amount)
        """
        from src.classes.items.weapon import Weapon
        from src.classes.items.auxiliary import Auxiliary
        
        sold_name = None
        refund = 0
        
        if isinstance(new_equip, Weapon):
            # Check for an old weapon
            if self.weapon:
                sold_name = self.weapon.name
                # sell_weapon adds the old weapon to circulation and pays the avatar
                # Note: sell_weapon doesn't clear self.weapon or deepcopy (it hands the reference to circulation)
                # This is correct: the old object goes to the system, the new one is equipped
                refund = self.sell_weapon(self.weapon)
                
            # Equip the new weapon (overwrites self.weapon)
            self.change_weapon(new_equip)
            
        elif isinstance(new_equip, Auxiliary):
            # Check for an old auxiliary
            if self.auxiliary:
                sold_name = self.auxiliary.name
                refund = self.sell_auxiliary(self.auxiliary)
                
            # Equip the new auxiliary
            self.change_auxiliary(new_equip)
            
        return sold_name, refund

from __future__ import annotations

from typing import Tuple, Any

from src.i18n import t
from src.classes.action import InstantAction
from src.classes.action.param_options import ParamOptionSource
from src.classes.event import Event
from src.classes.environment.region import CityRegion
from src.utils.normalize import normalize_goods_name
from src.utils.resolution import resolve_query
from src.classes.material import Material
from src.classes.items.weapon import Weapon
from src.classes.items.auxiliary import Auxiliary


class Sell(InstantAction):
    """
    Sell an item/equipment by name in a town.
    Materials: sell the entire held quantity at once.
    Equipment: sell the currently equipped item (if it is equipped).
    Proceeds are settled via avatar.sell_material() / sell_weapon() / sell_auxiliary().
    """
    
    # i18n IDs
    ACTION_NAME_ID = "sell_action_name"
    DESC_ID = "sell_description"
    REQUIREMENTS_ID = "sell_requirements"
    
    # Constants that need no translation
    EMOJI = "💰"
    PARAMS = {"target_name": "str"}
    PARAM_OPTION_SOURCES = {"target_name": ParamOptionSource.SELLABLE_ITEM_NAME}

    def can_start(self, target_name: str) -> tuple[bool, str]:
        region = self.avatar.tile.region
        if not isinstance(region, CityRegion):
            return False, t("Can only execute in city areas")
        
        # Use the generic resolution logic to get the item prototype and type
        res = resolve_query(target_name, expected_types=[Material, Weapon, Auxiliary])
        if not res.is_valid:
            return False, t("Do not possess item/equipment: {name}", name=target_name)
        
        obj = res.obj
        normalized_name = normalize_goods_name(target_name)
        
        # 1. If it's a material, check the inventory
        if isinstance(obj, Material):
            if self.avatar.get_material_quantity(obj) > 0:
                pass # Check passed
            else:
                return False, t("Do not possess material: {name}", name=target_name)

        # 2. If it's a weapon, check the current equipment
        elif isinstance(obj, Weapon):
            if self.avatar.weapon and normalize_goods_name(self.avatar.weapon.name) == normalized_name:
                pass # Check passed
            else:
                return False, t("Do not possess equipment: {name}", name=target_name)

        # 3. If it's an auxiliary, check the current equipment
        elif isinstance(obj, Auxiliary):
            if self.avatar.auxiliary and normalize_goods_name(self.avatar.auxiliary.name) == normalized_name:
                pass # Check passed
            else:
                return False, t("Do not possess equipment: {name}", name=target_name)
        
        else:
            return False, t("Cannot sell this type: {name}", name=target_name)
            
        return True, ""

    def _execute(self, target_name: str) -> None:
        region = self.avatar.tile.region
        if not isinstance(region, CityRegion):
            return

        res = resolve_query(target_name, expected_types=[Material, Weapon, Auxiliary])
        if not res.is_valid:
            return
            
        obj = res.obj
        normalized_name = normalize_goods_name(target_name)
        
        if isinstance(obj, Material):
            quantity = self.avatar.get_material_quantity(obj)
            self.avatar.sell_material(obj, quantity)
        elif isinstance(obj, Weapon):
            # Confirm again that it is the current equipment
             if self.avatar.weapon and normalize_goods_name(self.avatar.weapon.name) == normalized_name:
                self.avatar.sell_weapon(obj)
                self.avatar.change_weapon(None) # Unequip after selling
        elif isinstance(obj, Auxiliary):
            # Confirm again that it is the current equipment
             if self.avatar.auxiliary and normalize_goods_name(self.avatar.auxiliary.name) == normalized_name:
                self.avatar.sell_auxiliary(obj)
                self.avatar.change_auxiliary(None) # Unequip after selling

    def start(self, target_name: str) -> Event:
        res = resolve_query(target_name)
        display_name = res.name if res.is_valid else target_name
        content = t("{avatar} sold {item} in town",
                   avatar=self.avatar.name, item=display_name)
        return Event(
            self.world.month_stamp, 
            content, 
            related_avatars=[self.avatar.id]
        )

    async def finish(self, target_name: str) -> list[Event]:
        return []

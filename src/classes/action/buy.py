from __future__ import annotations

from typing import TYPE_CHECKING, Tuple, Any

from src.i18n import t
from src.classes.action import InstantAction
from src.classes.action.param_options import ParamOptionSource
from src.classes.event import Event
from src.classes.environment.region import CityRegion
from src.classes.items.elixir import Elixir
from src.classes.prices import prices
from src.classes.items.weapon import Weapon
from src.classes.items.auxiliary import Auxiliary
from src.classes.material import Material
from src.utils.resolution import resolve_query

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


class Buy(InstantAction):
    """
    Buy items in a town.
    
    Elixirs: consumed immediately after purchase.
    Other items: added to the inventory after purchase.
    Equipment (weapons/treasures): equipped directly after purchase (replacing the current one; the old one is sold at a discount).
    """
    
    # i18n IDs
    ACTION_NAME_ID = "buy_action_name"
    DESC_ID = "buy_description"
    REQUIREMENTS_ID = "buy_requirements"
    
    # Constants that need no translation
    EMOJI = "💸"
    PARAMS = {"target_name": "str"}
    PARAM_OPTION_SOURCES = {"target_name": ParamOptionSource.CURRENT_CITY_STORE_ITEM_NAME}

    def can_start(self, target_name: str) -> tuple[bool, str]:
        region = self.avatar.tile.region
        if not isinstance(region, CityRegion):
            return False, t("Can only execute in city areas")
            
        res = resolve_query(target_name, expected_types=[Elixir, Weapon, Auxiliary, Material])
        if not res.is_valid:
            return False, t("Unknown item: {name}", name=target_name)

        # Check whether the store sells it
        # Must be a StoreMixin (CityRegion mixes in StoreMixin)
        if hasattr(region, "is_selling"):
            if not region.is_selling(res.obj.name):
                return False, t("{region} does not sell {item}", region=region.name, item=res.obj.name)
        else:
            # Not a store region (CityRegion was already checked above, but for safety)
            return False, t("This area has no shop")

        # Core logic is delegated to Avatar
        return self.avatar.can_buy_item(res.obj)

    def _execute(self, target_name: str) -> None:
        res = resolve_query(target_name, expected_types=[Elixir, Weapon, Auxiliary, Material])
        if not res.is_valid:
            return
            
        # Actually execute the purchase (payment, consume/equip/sell old)
        self.avatar.buy_item(res.obj)

    def start(self, target_name: str) -> Event:
        res = resolve_query(target_name, expected_types=[Elixir, Weapon, Auxiliary, Material])
        obj = res.obj
        display_name = res.name
        
        # Pre-fetch some info for generating text (without changing state)
        price = prices.get_buying_price(obj, self.avatar)
        
        # Build the description
        action_desc = t("bought")
        suffix = ""
        
        if isinstance(obj, Elixir):
            action_desc = t("bought and consumed")
        elif isinstance(obj, (Weapon, Auxiliary)):
            action_desc = t("bought and equipped")
            # Predict whether an old item will be sold and generate the matching description
            if isinstance(obj, Weapon) and self.avatar.weapon:
                suffix = t(" (and sold old {item} at reduced price)", item=self.avatar.weapon.name)
            elif isinstance(obj, Auxiliary) and self.avatar.auxiliary:
                suffix = t(" (and sold old {item} at reduced price)", item=self.avatar.auxiliary.name)

        content = t("{avatar} spent {price} spirit stones in town, {action} {item}{suffix}",
                   avatar=self.avatar.name, price=price, action=action_desc, 
                   item=display_name, suffix=suffix)
        return Event(
            self.world.month_stamp, 
            content, 
            related_avatars=[self.avatar.id]
        )

    async def finish(self, target_name: str) -> list[Event]:
        return []

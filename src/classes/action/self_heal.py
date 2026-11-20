from __future__ import annotations

from src.i18n import t
from src.classes.action import TimedAction
from src.classes.event import Event
from src.classes.sect_metadata import is_in_sect_headquarter
from src.systems.formation import get_region_formation_effect_value


class SelfHeal(TimedAction):
    """
    Rest and heal.
    Single-month action. Outside sect headquarters it recovers a portion of HP; at sect headquarters it fully restores HP.
    """
    
    # i18n IDs
    ACTION_NAME_ID = "self_heal_action_name"
    DESC_ID = "self_heal_description"
    REQUIREMENTS_ID = "self_heal_requirements"
    
    # Constants that need no translation
    EMOJI = "💚"
    PARAMS = {}

    # Single-month action
    duration_months = 1

    def _execute(self) -> None:
        hp_obj = self.avatar.hp
        
        # Base recovery ratio (10%)
        base_ratio = 0.1
        
        # Persona/effect bonuses
        # extra_self_heal_efficiency is a decimal, e.g. 0.5 means +50% efficiency
        effect_bonus = float(self.avatar.effects.get("extra_self_heal_efficiency", 0.0))
        effect_bonus += float(self.avatar.effects.get("extra_hp_recovery_rate", 0.0) or 0.0)
        effect_bonus += float(get_region_formation_effect_value(self.avatar, "extra_hp_recovery_rate", 0.0) or 0.0)
        
        # Location bonus
        # Sect headquarters: fully restore (overrides the base value, treated as a huge bonus)
        is_hq = self._is_in_own_sect_headquarter()
        
        if is_hq:
            # Sect headquarters: fully restore
            heal_amount = max(0, hp_obj.max - hp_obj.cur)
        else:
            # Normal region: base + bonus
            # Compute the total ratio: base * (1 + efficiency bonus)
            total_ratio = base_ratio * (1.0 + effect_bonus)
            heal_amount = int(hp_obj.max * total_ratio)
            
        # Ensure no overflow and at least 1 (if HP isn't full)
        heal_amount = min(heal_amount, hp_obj.max - hp_obj.cur)
        if hp_obj.cur < hp_obj.max:
            heal_amount = max(1, heal_amount)
        else:
            heal_amount = 0
        
        if heal_amount > 0:
            hp_obj.recover(heal_amount)
            
        self._healed_total = heal_amount

    def _is_in_own_sect_headquarter(self) -> bool:
        sect = getattr(self.avatar, "sect", None)
        tile = getattr(self.avatar, "tile", None)
        region = getattr(tile, "region", None)
        return is_in_sect_headquarter(self.world, sect, region)

    def can_start(self) -> tuple[bool, str]:
        # Anyone can heal anywhere, as long as HP isn't full
        
        hp_obj = getattr(self.avatar, "hp", None)
        if hp_obj is None:
            return False, t("Missing HP information")
        if not (hp_obj.cur < hp_obj.max):
            return False, t("Current HP is full")
        return True, ""

    def start(self) -> Event:
        region = getattr(getattr(self.avatar, "tile", None), "region", None)
        region_name = getattr(region, "name", t("wilderness"))
        # Reset the accumulated amount
        self._healed_total = 0
        content = t("{avatar} begins resting and healing at {location}",
                   avatar=self.avatar.name, location=region_name)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])

    # TimedAction already unifies the step logic

    async def finish(self) -> list[Event]:
        healed_total = int(getattr(self, "_healed_total", 0))
        # Give brief feedback with a single event
        content = t("{avatar} healing completed (recovered {amount} HP, current HP {hp})",
                   avatar=self.avatar.name, amount=healed_total, hp=self.avatar.hp)
        return [Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])]

from __future__ import annotations

from src.i18n import t
from src.classes.action import TimedAction
from src.classes.event import Event
import random


class NurtureWeapon(TimedAction):
    """
    Nurture weapon: spend time nurturing the weapon to significantly increase proficiency
    """
    
    # i18n IDs
    ACTION_NAME_ID = "nurture_weapon_action_name"
    DESC_ID = "nurture_weapon_description"
    REQUIREMENTS_ID = "nurture_weapon_requirements"
    
    # Constants that need no translation
    EMOJI = "✨"
    PARAMS = {}

    duration_months = 3

    def _execute(self) -> None:
        from src.systems.cultivation import Realm
        from src.classes.items.weapon import get_random_weapon_by_realm
        
        # Nurturing increases proficiency substantially (5-10)
        proficiency_gain = random.uniform(5.0, 10.0)
        self.avatar.increase_weapon_proficiency(proficiency_gain)
        
        # A Qi Refinement weapon has a chance to upgrade to a Foundation Establishment weapon
        if self.avatar.weapon and self.avatar.weapon.realm == Realm.Qi_Refinement:
            # Base 5% chance + extra chance from effects
            base_upgrade_chance = 0.05
            extra_chance_raw = self.avatar.effects.get("extra_weapon_upgrade_chance", 0.0)
            extra_chance = max(0.0, min(1.0, float(extra_chance_raw or 0.0)))
            total_chance = min(1.0, base_upgrade_chance + extra_chance)
            
            if random.random() < total_chance:
                treasure_weapon = get_random_weapon_by_realm(Realm.Foundation_Establishment, self.avatar.weapon.weapon_type)
                if treasure_weapon:
                    old_weapon_name = self.avatar.weapon.name
                    old_proficiency = self.avatar.weapon_proficiency
                    # Deep-copy the treasure weapon and swap it in (long-term effects are recalculated)
                    # get_random_weapon_by_realm already returns a copy, but copying again doesn't hurt
                    new_weapon = treasure_weapon.instantiate()
                    self.avatar.change_weapon(new_weapon)
                    # Restore proficiency (change_weapon resets it to zero, so restore manually)
                    self.avatar.weapon_proficiency = old_proficiency
                    # Record the upgrade event
                    from src.classes.event import Event
                    content = t("{avatar} nurturing {old_weapon}, the weapon's spirituality greatly increased, evolved into {new_weapon}!",
                               avatar=self.avatar.name, old_weapon=old_weapon_name, new_weapon=treasure_weapon.name)
                    self.avatar.add_event(Event(
                        self.world.month_stamp,
                        content,
                        related_avatars=[self.avatar.id]
                    ))

    def can_start(self) -> tuple[bool, str]:
        # A weapon can be nurtured at any time
        return (True, "")

    def start(self) -> Event:
        weapon_name = self.avatar.weapon.name if self.avatar.weapon else t("weapon")
        content = t("{avatar} begins nurturing {weapon}",
                   avatar=self.avatar.name, weapon=weapon_name)
        return Event(
            self.world.month_stamp,
            content,
            related_avatars=[self.avatar.id]
        )

    async def finish(self) -> list[Event]:
        weapon_name = self.avatar.weapon.name if self.avatar.weapon else t("weapon")
        proficiency = self.avatar.weapon_proficiency
        # Note: the upgrade event is already added in _execute; only the completion event is added here
        content = t("{avatar} finished nurturing {weapon}, proficiency increased to {proficiency}%",
                   avatar=self.avatar.name, weapon=weapon_name, proficiency=f"{proficiency:.1f}")
        return [
            Event(
                self.world.month_stamp,
                content,
                related_avatars=[self.avatar.id]
            )
        ]


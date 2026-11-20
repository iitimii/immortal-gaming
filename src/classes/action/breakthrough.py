from __future__ import annotations

import random
from src.i18n import t
from src.classes.action import TimedAction
from src.classes.action.cooldown import cooldown_action
from src.classes.death import handle_death
from src.classes.death_reason import DeathReason, DeathType
from src.classes.event import Event
from src.classes.story_event_service import StoryEventKind, StoryEventService
from src.systems.cultivation import Realm
from src.systems.tribulation import TribulationSelector
from src.classes.hp import HP_MAX_BY_REALM
from src.classes.effect import _merge_effects
from src.systems.formation import get_region_formation_effect_value

# -- Config: which "starting realms" generate a breakthrough story (global var) --
ALLOW_STORY_FROM_REALMS: list[Realm] = [
    Realm.Foundation_Establishment,  # Foundation Establishment
    Realm.Core_Formation,            # Core Formation
]


@cooldown_action
class Breakthrough(TimedAction):
    """
    Break through to the next realm.
    The success rate is determined by `CultivationProgress.get_breakthrough_success_rate()`;
    on failure, lifespan (years) is reduced per `CultivationProgress.get_breakthrough_fail_reduce_lifespan()`.
    """
    
    # i18n IDs
    ACTION_NAME_ID = "breakthrough_action_name"
    DESC_ID = "breakthrough_description"
    REQUIREMENTS_ID = "breakthrough_requirements"
    
    # Constants that need no translation
    EMOJI = "⚡"
    PARAMS = {}
    # Cooldown: breakthroughs should have a CD to prevent spamming
    ACTION_CD_MONTHS: int = 3
    # Breakthrough is a major event (long-term memory)
    IS_MAJOR: bool = True
    # Class-level constant declaration kept; the module-level config is what's actually read

    def can_possibly_start(self) -> bool:
        return self.avatar.cultivation_progress.can_break_through()

    def calc_success_rate(self) -> float:
        """
        Compute the breakthrough success rate (given by cultivation progress)
        """
        base = self.avatar.cultivation_progress.get_breakthrough_success_rate()
        # Read extra bonuses uniformly from avatar.effects (root/technique/sect etc. already merged)
        bonus = float(self.avatar.effects.get("extra_breakthrough_success_rate", 0.0))
        bonus += float(get_region_formation_effect_value(self.avatar, "extra_breakthrough_success_rate", 0.0) or 0.0)
        # Clamp to [0, 1]
        return max(0.0, min(1.0, base + bonus))

    duration_months = 1

    def _execute(self) -> None:
        """
        Break through to the next realm
        """
        assert self.avatar.cultivation_progress.can_break_through()
        success_rate = self.calc_success_rate()
        # Record the basic info of this attempt
        self._success_rate_cached = success_rate
        if random.random() < success_rate:
            old_realm = self.avatar.cultivation_progress.realm
            self.avatar.cultivation_progress.break_through()
            new_realm = self.avatar.cultivation_progress.realm

            # Update max HP on a successful breakthrough
            if new_realm != old_realm:
                self._update_hp_on_breakthrough(new_realm)
                self.avatar.recalc_effects()
            # Record the result for the finish event
            self._last_result = (
                "success",
                old_realm.value,
                new_realm.value,
            )
        else:
            # Breakthrough failed: add a permanent lifespan-loss effect so the frontend can show the source
            reduce_years = self.avatar.cultivation_progress.get_breakthrough_fail_reduce_lifespan()
            self.avatar.add_persistent_effect(
                "effect_source_breakthrough_failure",
                {"extra_max_lifespan": -int(reduce_years)},
            )
            if self.avatar.age.age >= self.avatar.age.max_lifespan and not self.avatar.is_dead:
                handle_death(
                    self.world,
                    self.avatar,
                    DeathReason(DeathType.OLD_AGE),
                )
            # Record the result for the finish event
            self._last_result = ("fail", int(reduce_years))

    def _update_hp_on_breakthrough(self, new_realm):
        """
        Update max HP and fully recover on breakthrough

        Args:
            new_realm: the new realm
        """
        new_max_hp = HP_MAX_BY_REALM.get(new_realm, 100)

        # Compute the max HP increase
        hp_increase = new_max_hp - self.avatar.hp.max

        # Update the max and recover the current value accordingly
        self.avatar.hp.add_max(hp_increase)
        self.avatar.hp.recover(hp_increase)  # Fully recover HP on breakthrough

    def can_start(self) -> tuple[bool, str]:
        ok = self.avatar.cultivation_progress.can_break_through()
        return (ok, "" if ok else t("Not at bottleneck, cannot breakthrough"))

    def start(self) -> Event:
        # Initialize state
        self._last_result = None
        self._success_rate_cached = None
        # Decide in advance whether to generate a story and pick a tribulation
        old_realm = self.avatar.cultivation_progress.realm
        self._gen_story = old_realm in ALLOW_STORY_FROM_REALMS
        if self._gen_story:
            self._calamity = TribulationSelector.choose_tribulation(self.avatar)
            self._calamity_other = TribulationSelector.choose_related_avatar(self.avatar, self._calamity)
        else:
            self._calamity = None
            self._calamity_other = None
        content = t("{avatar} begins attempting breakthrough", avatar=self.avatar.name)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id], is_major=True)

    # TimedAction already unifies the step logic

    async def finish(self) -> list[Event]:
        if not self._last_result:
            return []
        result_ok = self._last_result[0] == "success"
        if not self._gen_story:
            # No story: no tribulation, just a simple result
            result_text = t("Breakthrough succeeded") if result_ok else t("Breakthrough failed")
            core_text = t("{avatar} breakthrough result: {result}", 
                         avatar=self.avatar.name, result=result_text)
            return [Event(self.world.month_stamp, core_text, related_avatars=[self.avatar.id], is_major=True)]

        calamity = self._calamity
        calamity_display = TribulationSelector.get_display_name(str(calamity))
        result_text = t("succeeded") if result_ok else t("failed")
        core_text = t("{avatar} encountered {calamity} tribulation, breakthrough {result}",
                     avatar=self.avatar.name, calamity=calamity_display, result=result_text)
        rel_ids = [self.avatar.id]
        if self._calamity_other is not None:
            try:
                rel_ids.append(self._calamity_other.id)
            except Exception:
                pass
        events: list[Event] = [Event(self.world.month_stamp, core_text, related_avatars=rel_ids, is_major=True)]

        # Story participants: self + (optional) related avatars
        prompt = TribulationSelector.get_story_prompt(str(calamity))
        # Breakthrough is forced into solo mode and doesn't change relations (no interaction like dual cultivation/battle)
        story_result = t("Breakthrough succeeded") if result_ok else t("Breakthrough failed")
        story_event = await StoryEventService.maybe_create_story(
            kind=StoryEventKind.CULTIVATION_MAJOR,
            month_stamp=self.world.month_stamp,
            start_text=core_text,
            result_text=story_result,
            actors=[self.avatar, self._calamity_other],
            related_avatar_ids=rel_ids,
            prompt=prompt,
            allow_relation_changes=False,
        )
        if story_event is not None:
            events.append(story_event)
        return events

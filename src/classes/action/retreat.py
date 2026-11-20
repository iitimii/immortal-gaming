from __future__ import annotations

import random
from src.i18n import t
from src.classes.action import TimedAction
from src.classes.action.cooldown import cooldown_action
from src.classes.death import handle_death
from src.classes.death_reason import DeathReason, DeathType
from src.classes.event import Event
from src.classes.story_event_service import StoryEventKind, StoryEventService
from src.systems.cultivation import REALM_RANK
from src.classes.action_runtime import ActionResult, ActionStatus
from src.systems.formation import get_region_formation_effect_value

@cooldown_action
class Retreat(TimedAction):
    """
    Retreat: a gamble.
    Lasts a random 1-5 years.
    Success: gain a breakthrough probability bonus lasting 10 years.
    Failure: lose lifespan.
    """
    
    ACTION_NAME_ID = "retreat_action_name"
    DESC_ID = "retreat_desc"
    REQUIREMENTS_ID = "retreat_requirements"
    
    EMOJI = "🛖"
    PARAMS = {}
    
    # Cannot retreat again within 1 year after a retreat ends
    ACTION_CD_MONTHS = 12
    IS_MAJOR = True
    
    # During retreat, ignore worldly affairs and stay free of karma
    ALLOW_GATHERING = False
    ALLOW_WORLD_EVENTS = False

    def __init__(self, avatar, world):
        super().__init__(avatar, world)
        # Random duration: 12 - 60 months (1-5 years)
        self.duration_months = random.randint(12, 60)
    
    def get_save_data(self) -> dict:
        data = super().get_save_data()
        data['duration_months'] = self.duration_months
        return data

    def load_save_data(self, data: dict) -> None:
        super().load_save_data(data)
        if 'duration_months' in data:
            self.duration_months = data['duration_months']

    def calc_success_rate(self) -> float:
        """
        Compute the retreat success rate
        Qi Refinement (0): 50%, Foundation Establishment (1): 40%, Core Formation (2): 30%, Nascent Soul (3): 20%
        """
        realm_idx = REALM_RANK.get(self.avatar.cultivation_progress.realm, 0)
        base = 0.5 - (realm_idx * 0.1)
        base = max(0.1, base)
        
        # Apply effect bonuses
        extra_rate = self.avatar.effects.get("extra_retreat_success_rate", 0.0)
        extra_rate = float(extra_rate) + float(get_region_formation_effect_value(self.avatar, "extra_retreat_success_rate", 0.0) or 0.0)
        return min(1.0, base + float(extra_rate))

    def _execute(self) -> None:
        # TimedAction's _execute is called monthly; here it mainly handles settlement at the end
        # But TimedAction.step sets the status to COMPLETED when time is up
        # We need to handle settlement in finish, or in the last step
        # Per TimedAction's design, _execute is the in-progress logic.
        # We can leave _execute empty, or add some descriptive events here (optional)
        pass

    async def finish(self) -> list[Event]:
        # 1. Determine the result
        success_rate = self.calc_success_rate()
        is_success = random.random() < success_rate
        
        events = []
        current_month = int(self.world.month_stamp)
        
        if is_success:
            # Success: add a temporary effect (10 years = 120 months)
            buff_duration = 120
            # Add 20% breakthrough success rate
            bonus = {
                "extra_breakthrough_success_rate": 0.3
            }
            
            self.avatar.temporary_effects.append({
                "source": "Retreat Bonus",
                "effects": bonus,
                "start_month": current_month,
                "duration": buff_duration
            })
            self.avatar.recalc_effects()
            
            result_text = t("retreat_success", duration=self.duration_months)
            core_text = t("{avatar} finished retreat successfully.", avatar=self.avatar.name)
            
            prompt = t("retreat_story_prompt_success")
            events.append(Event(self.world.month_stamp, core_text, related_avatars=[self.avatar.id], is_major=True))
            story_event = await StoryEventService.maybe_create_story(
                kind=StoryEventKind.CULTIVATION_MAJOR,
                month_stamp=self.world.month_stamp,
                start_text=core_text,
                result_text=result_text,
                actors=[self.avatar],
                related_avatar_ids=[self.avatar.id],
                prompt=prompt,
                allow_relation_changes=False,
            )
            if story_event is not None:
                events.append(story_event)
            
        else:
            # Failure: deduct lifespan
            # Randomly deduct 5-20 years
            reduce_years = random.randint(5, 20)
            self.avatar.add_persistent_effect(
                "effect_source_retreat_failure",
                {"extra_max_lifespan": -int(reduce_years)},
            )
            is_dead = self.avatar.age.age >= self.avatar.age.max_lifespan
            if is_dead and not self.avatar.is_dead:
                handle_death(
                    self.world,
                    self.avatar,
                    DeathReason(DeathType.OLD_AGE),
                )
            
            result_text = t("retreat_fail", reduce_years=reduce_years)
            if is_dead:
                result_text += t("retreat_death_append")
                
            core_text = t("{avatar} failed retreat and lost {years} years of lifespan.", avatar=self.avatar.name, years=reduce_years)
            
            prompt = t("retreat_story_prompt_fail")
            events.append(Event(self.world.month_stamp, core_text, related_avatars=[self.avatar.id], is_major=True))
            story_event = await StoryEventService.maybe_create_story(
                kind=StoryEventKind.CULTIVATION_MAJOR,
                month_stamp=self.world.month_stamp,
                start_text=core_text,
                result_text=result_text,
                actors=[self.avatar],
                related_avatar_ids=[self.avatar.id],
                prompt=prompt,
                allow_relation_changes=False,
            )
            if story_event is not None:
                events.append(story_event)

        return events

    def can_start(self) -> tuple[bool, str]:
        # Retreat is possible any time, as long as the avatar is alive
        # Could add a limit: discourage retreat when lifespan is low? No, that's the user's own choice (or the AI's foolish choice)
        return True, ""

    def start(self) -> Event:
        # Record the start
        content = t("retreat_start", avatar=self.avatar.name)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id], is_major=False)

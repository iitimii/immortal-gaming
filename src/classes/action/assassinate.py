from __future__ import annotations
from typing import TYPE_CHECKING
import random

from src.i18n import t
from src.classes.action import InstantAction
from src.classes.action.cooldown import cooldown_action
from src.classes.action.param_options import ParamOptionSource
from src.classes.action.targeting_mixin import TargetingMixin
from src.classes.event import Event
from src.classes.story_event_service import StoryEventKind, StoryEventService
from src.systems.battle import decide_battle, get_assassination_success_rate
from src.classes.death import handle_death
from src.classes.death_reason import DeathReason, DeathType
from src.classes.kill_and_grab import kill_and_grab

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


@cooldown_action
class Assassinate(InstantAction, TargetingMixin):
    # i18n IDs
    ACTION_NAME_ID = "assassinate_action_name"
    DESC_ID = "assassinate_description"
    REQUIREMENTS_ID = "assassinate_requirements"
    
    # Constants that need no translation
    EMOJI = "🗡️"
    PARAMS = {"avatar_name": "AvatarName"}
    PARAM_OPTION_SOURCES = {"avatar_name": ParamOptionSource.OBSERVABLE_AVATAR_NAME}
    ACTION_CD_MONTHS = 12
    
    # LLM prompt IDs
    STORY_PROMPT_SUCCESS_ID = "assassinate_story_prompt_success"
    STORY_PROMPT_FAIL_ID = "assassinate_story_prompt_fail"
    
    # Assassination is a major event (long-term memory)
    IS_MAJOR: bool = True
    
    @classmethod
    def get_story_prompt_success(cls) -> str:
        """Get the translated success prompt."""
        return t(cls.STORY_PROMPT_SUCCESS_ID)
    
    @classmethod
    def get_story_prompt_fail(cls) -> str:
        """Get the translated failure prompt."""
        return t(cls.STORY_PROMPT_FAIL_ID)

    def _execute(self, avatar_name: str) -> None:
        target = self.find_avatar_by_name(avatar_name)
        if target is None:
            return
            
        # Determine whether the assassination succeeds
        success_rate = get_assassination_success_rate(self.avatar, target)
        is_success = random.random() < success_rate
        
        self._is_assassinate_success = is_success
        
        if is_success:
            # Assassination succeeded; the target dies outright
            target.hp.current = 0
            self._last_result = None # No battle result needed
        else:
            # Assassination failed; switch to a normal battle
            winner, loser, loser_damage, winner_damage = decide_battle(self.avatar, target)
            # Apply damage to both sides
            loser.hp.reduce(loser_damage)
            winner.hp.reduce(winner_damage)
            
            # Increase proficiency (since they fought anyway)
            proficiency_gain = random.uniform(1.0, 3.0)
            self.avatar.increase_weapon_proficiency(proficiency_gain)
            target.increase_weapon_proficiency(proficiency_gain)
            
            self._last_result = (winner, loser, loser_damage, winner_damage)

    def can_start(self, avatar_name: str) -> tuple[bool, str]:
        # Note: the cooldown_action decorator wraps this method and checks the CD before calling it
        _, ok, reason = self.validate_target_avatar(avatar_name)
        return ok, reason

    def start(self, avatar_name: str) -> Event:
        target = self.find_avatar_by_name(avatar_name)
        target_name = target.name if target is not None else avatar_name
        
        content = t("{avatar} lurks in the shadows, attempting to assassinate {target}...", 
                   avatar=self.avatar.name, target=target_name)
        event = Event(self.world.month_stamp, content, related_avatars=[self.avatar.id, target.id] if target else [self.avatar.id], is_major=False)
        self._start_event_content = event.content
        return event

    async def finish(self, avatar_name: str) -> list[Event]:
        target = self.find_avatar_by_name(avatar_name)
        if target is None:
            return []
            
        rel_ids = [self.avatar.id, target.id]
        
        if getattr(self, '_is_assassinate_success', False):
            # --- Assassination succeeded ---
            result_text = t("{avatar} assassinated successfully! {target} fell without any defense.",
                           avatar=self.avatar.name, target=target.name)
            
            # Kill and grab
            loot_text = await kill_and_grab(self.avatar, target)
            result_text += loot_text
            
            result_event = Event(self.world.month_stamp, result_text, related_avatars=rel_ids, is_major=True)
            
            story_event = await StoryEventService.maybe_create_story(
                kind=StoryEventKind.COMBAT,
                month_stamp=self.world.month_stamp,
                start_text=self._start_event_content,
                result_text=result_event.content,
                actors=[self.avatar, target],
                related_avatar_ids=rel_ids,
                prompt=self.get_story_prompt_success(),
                allow_relation_changes=True,
            )
            
            # Death cleanup
            handle_death(self.world, target, DeathReason(DeathType.BATTLE, killer_name=self.avatar.name))
            
            events = [result_event]
            if story_event is not None:
                events.append(story_event)
            return events
            
        else:
            # --- Assassination failed, switch to battle ---
            res = getattr(self, '_last_result', None)
            if not (isinstance(res, tuple) and len(res) == 4):
                return [] 
                
            start_text = getattr(self, '_start_event_content', "")
            
            from src.systems.battle import handle_battle_finish
            return await handle_battle_finish(
                self.world,
                self.avatar,
                target,
                res,
                start_text,
                self.get_story_prompt_fail(),
                prefix=t("Assassination failed! Both sides engaged in fierce battle."),
                check_loot=True
            )


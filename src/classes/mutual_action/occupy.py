from __future__ import annotations

from typing import TYPE_CHECKING

from src.i18n import t
from src.classes.mutual_action.mutual_action import PressureAction
from src.classes.action.param_options import ParamOptionSource
from src.classes.event import Event
from src.classes.action.registry import register_action
from src.classes.action.cooldown import cooldown_action
from src.classes.environment.region import CultivateRegion
from src.classes.action_runtime import ActionResult, ActionStatus
from src.systems.battle import decide_battle
from src.classes.action.event_helper import EventHelper
from src.utils.resolution import resolve_query

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


@cooldown_action
@register_action(actual=True)
class Occupy(PressureAction):
    """
    Occupy action (mutual version):
    Occupy the specified cave dwelling. An unowned one is occupied directly; an owned one triggers a seizure attempt.
    If the owner refuses, a battle starts; if the attacker wins, the cave dwelling changes hands.
    """
    
    # i18n IDs
    ACTION_NAME_ID = "occupy_action_name"
    DESC_ID = "occupy_description"
    REQUIREMENTS_ID = "occupy_requirements"
    STORY_PROMPT_ID = "occupy_story_prompt"
    
    # Constants that need no translation
    EMOJI = "🚩"
    PARAMS = {"region_name": "str"}
    PARAM_OPTION_SOURCES = {"region_name": ParamOptionSource.KNOWN_CULTIVATE_REGION_NAME}
    RESPONSE_ACTIONS = ["Yield", "Reject"]
    
    # Custom feedback labels
    RESPONSE_LABEL_IDS = {"Yield": "feedback_yield", "Reject": "feedback_reject"}
    
    IS_MAJOR = True
    ACTION_CD_MONTHS = 6

    def _get_region_and_host(self, region_name: str) -> tuple[CultivateRegion | None, "Avatar | None", str]:
        """Resolve the region and get its owner."""
        res = resolve_query(region_name, self.world, expected_types=[CultivateRegion])
        
        # resolve_query may return a plain Region; strictly check for CultivateRegion here
        region = res.obj
        
        if not res.is_valid or region is None:
            return None, None, t("Cannot find region: {region}", region=region_name)
            
        if not isinstance(region, CultivateRegion):
            return None, None, t("{region} is not a cultivation area, cannot occupy",
                                region=region.name if region else t("wilderness"))
            
        return region, region.host_avatar, ""

    def can_start(self, region_name: str) -> tuple[bool, str]:
        region, host, err = self._get_region_and_host(region_name)
        if err:
            return False, err
        if region.host_avatar == self.avatar:
            return False, t("Already the owner of this cave dwelling")
        if host is None:
            return True, ""
        return super().can_start(target_avatar=host)

    def start(self, region_name: str) -> Event:
        region, host, _ = self._get_region_and_host(region_name)

        self._start_month_stamp = self.world.month_stamp
        self.target_region_name = region_name

        region_display_name = region.name if region else self.avatar.tile.location_name
        if host is None:
            content = t("{initiator} begins occupying unclaimed cave dwelling {region}",
                       initiator=self.avatar.name, region=region_display_name)
        else:
            content = t("{initiator} attempts to seize {region} from {host}",
                       initiator=self.avatar.name, region=region_display_name, host=host.name)

        rel_ids = [self.avatar.id]
        if host:
            rel_ids.append(host.id)

        event = Event(
            self._start_month_stamp,
            content,
            related_avatars=rel_ids,
            is_major=False
        )

        return event

    def step(self, region_name: str) -> ActionResult:
        region, host, _ = self._get_region_and_host(region_name)
        if region is None:
            return ActionResult(status=ActionStatus.FAILED, events=[])
        if host is None:
            self.avatar.occupy_region(region)
            self._last_result = None
            content = t("{avatar} occupied cave dwelling {region}",
                        avatar=self.avatar.name, region=region.name)
            event = Event(
                self.world.month_stamp,
                content,
                related_avatars=[self.avatar.id],
                is_major=True,
            )
            return ActionResult(status=ActionStatus.COMPLETED, events=[event])
        return super().step(target_avatar=host)

    def _settle_response(self, target_avatar: "Avatar", response_name: str) -> None:
        """Handle the feedback result."""
        region_name = getattr(self, "target_region_name", self.avatar.tile.location_name)
        region, _, _ = self._get_region_and_host(region_name)
        
        if response_name == "Yield":
            # The owner yields: transfer ownership directly
            if region:
                self.avatar.occupy_region(region)
            
            # Share one event
            event_text = t("{initiator} forced {target} to yield {region}",
                          initiator=self.avatar.name, target=target_avatar.name, region=region_name)
            event = Event(
                self.world.month_stamp, 
                event_text, 
                related_avatars=[self.avatar.id, target_avatar.id],
                is_major=True
            )
            # Push once, avoiding duplicates
            EventHelper.push_pair(event, initiator=self.avatar, target=target_avatar, to_sidebar_once=True)
            
            self._last_result = None
            
        elif response_name == "Reject":
            # The owner refuses: start a battle
            winner, loser, loser_dmg, winner_dmg = decide_battle(self.avatar, target_avatar)
            loser.hp.reduce(loser_dmg)
            winner.hp.reduce(winner_dmg)
            
            # If the attacker wins, the cave dwelling changes hands
            attacker_won = winner == self.avatar
            if attacker_won and region:
                self.avatar.occupy_region(region)
            
            self._last_result = (winner, loser, loser_dmg, winner_dmg, region_name, attacker_won)

    async def finish(self, region_name: str) -> list[Event]:
        """Finish the action: generate the battle story and handle deaths."""
        res = self._last_result if hasattr(self, '_last_result') else None
        if res is None:
            return []
        
        # res format from occupy: (winner, loser, l_dmg, w_dmg, r_name, attacker_won)
        winner, loser, l_dmg, w_dmg, r_name, attacker_won = res
        battle_res = (winner, loser, l_dmg, w_dmg)
        
        target = loser if winner == self.avatar else winner
        
        start_text = t("{initiator} attempted to seize {target}'s cave dwelling {region}, {target} rejected and engaged in battle",
                      initiator=self.avatar.name, target=target.name, region=r_name)
        
        postfix = t(", successfully seized {region}", region=r_name) if attacker_won else t(", defended {region}", region=r_name)

        from src.systems.battle import handle_battle_finish
        return await handle_battle_finish(
            self.world,
            self.avatar,
            target,
            battle_res,
            start_text,
            self.get_story_prompt(),  # Use classmethod
            action_desc=t("defeated"),
            postfix=postfix
        )

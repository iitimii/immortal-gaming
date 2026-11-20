from __future__ import annotations

import random
from pathlib import Path
from typing import TYPE_CHECKING

from src.i18n import t
from .mutual_action import InvitationAction
from src.classes.action.cooldown import cooldown_action
from src.classes.event import Event
from src.classes.story_event_service import StoryEventKind, StoryEventService
from src.classes.relation.relation_delta_service import RelationDeltaService
from src.utils.config import CONFIG

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


@cooldown_action
class DualCultivation(InvitationAction):
    """Dual cultivation: a cultivator may attempt dual cultivation with a cultivator within interaction range.

    - Only when the target is within interaction range
    - The target can choose to accept or refuse
    - If accepted: the initiator gains a lot of cultivation exp (about 3-5x normal cultivation, varying with the other's level); the target gains none
    - On success, a short "romance/dual cultivation" story is generated
    """
    
    # i18n IDs
    ACTION_NAME_ID = "dual_cultivation_action_name"
    DESC_ID = "dual_cultivation_description"
    REQUIREMENTS_ID = "dual_cultivation_requirements"
    STORY_PROMPT_ID = "dual_cultivation_story_prompt"
    
    # Constants that need no translation
    EMOJI = "💕"
    PARAMS = {"target_avatar": "AvatarName"}
    RESPONSE_ACTIONS = ["Accept", "Reject"]
    # Social cooldown for dual cultivation: avoid frequent requests
    ACTION_CD_MONTHS: int = 3
    # Dual cultivation is a major event (long-term memory)
    IS_MAJOR: bool = True

    def _can_start(self, target: "Avatar") -> tuple[bool, str]:
        """Check the dual-cultivation-specific start conditions."""
        return True, ""

    def start(self, target_avatar: "Avatar|str") -> Event:
        target = self._get_target_avatar(target_avatar)
        target_name = target.name if target is not None else str(target_avatar)
        rel_ids = [self.avatar.id]
        if target is not None:
            rel_ids.append(target.id)
        
        # Dual cultivation has special invitation semantics
        content = t("{initiator} invites {target} for dual cultivation",
                   initiator=self.avatar.name, target=target_name)
        event = Event(self.world.month_stamp, content, related_avatars=rel_ids, is_major=False)
        
        # Record the start text for story generation
        self._start_event_content = event.content
        # Initialize internal flags to avoid later getattr
        self._dual_cultivation_success = False
        self._dual_exp_gain = 0
        return event

    def _settle_response(self, target_avatar: "Avatar", response_name: str) -> None:
        fb = str(response_name).strip()
        if fb == "Accept":
            # If accepted, settle the cultivation gain on the spot (initiator gains, target doesn't) and set a flag for finish to generate the story
            self._apply_dual_cultivation_gain(self.avatar, target_avatar)
            self._dual_cultivation_success = True
        else:
            # Refused
            self._dual_cultivation_success = False

    def _apply_dual_cultivation_gain(self, initiator: "Avatar", target: "Avatar") -> None:
        # Use the base exp of "cultivate" as reference: base=100 * essence_density
        # Since this doesn't depend on a specific cultivation region's qi, use a stable baseline: essence_density=1;
        # then pick a multiplier between 3 and 5 based on the other's level.
        base = 100
        # The higher the other's level, the higher the multiplier (3.0 ~ 5.0), via a clamped linear mapping
        other_level = target.cultivation_progress.level
        factor = 3.0 + min(2.0, max(0.0, other_level / 60.0 * 2.0))  # level 0-120 -> +0~4, but capped at 5
        # Add a little jitter to avoid being too stable
        jitter = random.uniform(-0.2, 0.2)
        factor = max(3.0, min(5.0, factor + jitter))
        exp_gain = int(base * factor)
        # Apply "dual cultivation exp boost" effects (e.g. from treasures)
        extra_raw = initiator.effects.get("extra_dual_cultivation_exp", 0)
        extra = int(extra_raw or 0)
        exp_gain += extra
        initiator.cultivation_progress.add_exp(exp_gain)
        self._dual_exp_gain = exp_gain

    async def finish(self, target_avatar: "Avatar|str") -> list[Event]:
        target = self._get_target_avatar(target_avatar)
        events: list[Event] = []
        success = self._dual_cultivation_success
        if target is None:
            return events

        if success:
            gain = int(self._dual_exp_gain)
            result_text = t("{avatar} gained cultivation experience +{exp} points",
                          avatar=self.avatar.name, exp=gain)
            a_to_b, b_to_a = RelationDeltaService.get_fixed_delta("dual_cultivation", "accepted")
            result_event = Event(self.world.month_stamp, result_text, 
                               related_avatars=[self.avatar.id, target.id], is_major=True)
            
            events.append(result_event)
            RelationDeltaService.apply_bidirectional_delta(self.avatar, target, a_to_b, b_to_a)

            start_text = self._start_event_content or result_event.content
            story_event = await StoryEventService.maybe_create_story(
                kind=StoryEventKind.RELATIONSHIP_MAJOR,
                month_stamp=self.world.month_stamp,
                start_text=start_text,
                result_text=result_event.content,
                actors=[self.avatar, target],
                related_avatar_ids=[self.avatar.id, target.id],
                prompt=self.get_story_prompt(),
                allow_relation_changes=True,
            )
            if story_event is not None:
                events.append(story_event)
        else:
            a_to_b, b_to_a = RelationDeltaService.get_fixed_delta("dual_cultivation", "rejected")
            RelationDeltaService.apply_bidirectional_delta(self.avatar, target, a_to_b, b_to_a)

        return events

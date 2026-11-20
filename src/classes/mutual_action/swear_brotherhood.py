from __future__ import annotations

from typing import TYPE_CHECKING

from src.i18n import t
from .mutual_action import InvitationAction
from src.classes.action.cooldown import cooldown_action
from src.classes.event import Event
from src.classes.story_event_service import StoryEventKind, StoryEventService
from src.classes.close_relation_event_service import (
    apply_positive_bond_warmth,
    configure_positive_bond_event,
)
from src.classes.relation.relation_delta_service import RelationDeltaService
from src.classes.relation.relation import Relation

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


@cooldown_action
class SwearBrotherhood(InvitationAction):
    """Swear brotherhood: propose sworn kinship to a cultivator within interaction range; if accepted, they become sworn siblings.
    """
    
    # i18n IDs
    ACTION_NAME_ID = "swear_brotherhood_action_name"
    DESC_ID = "swear_brotherhood_description"
    REQUIREMENTS_ID = "swear_brotherhood_requirements"
    STORY_PROMPT_ID = "swear_brotherhood_story_prompt"
    
    # Constants that need no translation
    EMOJI = "🤝"
    PARAMS = {"target_avatar": "AvatarName"}
    RESPONSE_ACTIONS = ["Accept", "Reject"]
    
    # Social cooldown for sworn brotherhood: avoid frequent requests
    ACTION_CD_MONTHS: int = 6
    # Sworn brotherhood is a major event (long-term memory)
    IS_MAJOR: bool = True

    def _can_start(self, target: "Avatar") -> tuple[bool, str]:
        """Check the sworn-brotherhood-specific start conditions."""
        from src.classes.observe import is_within_observation
        if not is_within_observation(self.avatar, target):
            return False, t("Target not within interaction range")
            
        if self.avatar.has_identity_relation(target, Relation.IS_SWORN_SIBLING_OF) or self.avatar.get_relation(target) == Relation.IS_SWORN_SIBLING_OF:
            return False, t("Already sworn siblings")
            
        return True, ""

    def start(self, target_avatar: "Avatar|str") -> Event:
        target = self._get_target_avatar(target_avatar)
        target_name = target.name if target is not None else str(target_avatar)
        rel_ids = [self.avatar.id]
        if target is not None:
            rel_ids.append(target.id)
        
        content = t("{initiator} proposes to become sworn siblings with {target}",
                   initiator=self.avatar.name, target=target_name)
        event = Event(self.world.month_stamp, content, related_avatars=rel_ids, is_major=False)
        
        # Record the start text for story generation
        self._start_event_content = event.content
        # Initialize internal flags
        self._swear_success = False
        return event

    def _settle_response(self, target_avatar: "Avatar", response_name: str) -> None:
        fb = str(response_name).strip()
        if fb == "Accept":
            # If accepted, become sworn siblings
            self.avatar.become_sworn_sibling_with(target_avatar)
            self._swear_success = True
        else:
            # Refused
            self._swear_success = False

    async def finish(self, target_avatar: "Avatar|str", **kwargs) -> list[Event]:
        target = self._get_target_avatar(target_avatar)
        events: list[Event] = []
        if target is None:
            return events

        if self._swear_success:
            result_text = t("{target} accepted {initiator}'s proposal, they became sworn siblings",
                          target=target.name, initiator=self.avatar.name)
            a_to_b, b_to_a = RelationDeltaService.get_fixed_delta("swear_brotherhood", "accepted")
        else:
            result_text = t("{target} rejected {initiator}'s proposal to become sworn siblings",
                          target=target.name, initiator=self.avatar.name)
            a_to_b, b_to_a = RelationDeltaService.get_fixed_delta("swear_brotherhood", "rejected")

        RelationDeltaService.apply_bidirectional_delta(self.avatar, target, a_to_b, b_to_a)
            
        event_type = "bond_sworn_sibling_formed" if self._swear_success else "bond_sworn_sibling_rejected"
        result_event = Event(
            self.world.month_stamp,
            result_text,
            related_avatars=[self.avatar.id, target.id],
            is_major=True,
            event_type=event_type,
        )
        if self._swear_success:
            configure_positive_bond_event(result_event, avatar_a=self.avatar, avatar_b=target)
            apply_positive_bond_warmth(subject=self.avatar, other_party=target, event_type=event_type)
            apply_positive_bond_warmth(subject=target, other_party=self.avatar, event_type=event_type)
        
        events.append(result_event)

        # Generate the sworn brotherhood story
        start_text = getattr(self, "_start_event_content", "") or result_event.content
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

        return events

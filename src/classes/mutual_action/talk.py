from __future__ import annotations

from typing import TYPE_CHECKING

from src.i18n import t
from src.classes.action_runtime import ActionResult, ActionStatus
from src.classes.event import Event

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

from .mutual_action import InvitationAction


class Talk(InvitationAction):
    """
    Talk: strike up a conversation with an NPC within interaction range.
    - Automatically enters Conversation once accepted
    """
    
    # i18n IDs
    ACTION_NAME_ID = "talk_action_name"
    DESC_ID = "talk_description"
    REQUIREMENTS_ID = "talk_requirements"
    
    # Constants that need no translation
    EMOJI = "👋"
    PARAMS = {"target_avatar": "AvatarName"}
    RESPONSE_ACTIONS: list[str] = ["Talk", "Reject"]
    
    # Custom feedback labels
    RESPONSE_LABEL_IDS: dict[str, str] = {
        "Talk": "feedback_talk",
        "Reject": "feedback_reject",
    }
    
    def _can_start(self, target: "Avatar") -> tuple[bool, str]:
        """Talk has no extra start conditions."""
        from src.classes.observe import is_within_observation
        if not is_within_observation(self.avatar, target):
            return False, t("Target not within interaction range")
        return True, ""
    
    def _handle_response_result(self, target: "Avatar", result: dict) -> ActionResult:
        """
        Handle the response returned by the LLM.
        """
        response = str(result.get("response", result.get("feedback", ""))).strip()
        
        events_to_return = []
        
        # Handle the response
        if response == "Talk":
            # After accepting, enter Conversation directly, avoiding duplication between "accepted the talk" and the conversation body
            # Add Conversation to the plan queue and commit it immediately
            self.avatar.load_decide_result_chain(
                [("Conversation", {"target_avatar": target.name})],
                self.avatar.thinking,
                self.avatar.short_term_objective,
                prepend=True
            )
            # Commit immediately as the current action
            start_event = self.avatar.commit_next_plan()
            if start_event is not None:
                pass

        else:
            # Talk refused
            content = t("{target} rejected {initiator}'s talk invitation",
                       target=target.name, initiator=self.avatar.name)
            reject_event = Event(
                self.world.month_stamp, 
                content, 
                related_avatars=[self.avatar.id, target.id]
            )
            events_to_return.append(reject_event)
        
        return ActionResult(status=ActionStatus.COMPLETED, events=events_to_return)
    
    def step(self, target_avatar: "Avatar|str", **kwargs) -> ActionResult:
        """Call the parent's generic async step logic."""
        return super().step(target_avatar=target_avatar)

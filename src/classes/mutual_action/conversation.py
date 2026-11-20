from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.i18n import t
from .mutual_action import MutualAction
from src.classes.event import Event, NULL_EVENT
from src.utils.config import CONFIG
from src.classes.action_runtime import ActionResult, ActionStatus
from src.classes.relation.relation_delta_service import RelationDeltaService
from src.classes.story_event_service import StoryEventKind, StoryEventService

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


class Conversation(MutualAction):
    """Conversation: two avatars talk with each other in the same region.

    - Can be triggered by "Talk" or initiated directly
    - Can only start when both are in the same Region
    - The LLM generates the conversation content
    - The conversation content and follow-up story are written to the event system
    """
    
    # i18n IDs
    ACTION_NAME_ID = "conversation_action_name"
    DESC_ID = "conversation_description"
    REQUIREMENTS_ID = "conversation_requirements"
    
    # Constants that need no translation
    EMOJI = "🗣️"
    PARAMS = {"target_avatar": "AvatarName"}
    RESPONSE_ACTIONS: list[str] = []  # Conversation triggers automatically; no decision needed from the other side
    RESPONSE_EVENT_STYLE = "none"

    def _get_template_path(self) -> Path:
        # Use the dedicated conversation.txt template
        return CONFIG.paths.templates / "conversation.txt"

    def _build_prompt_infos(self, target_avatar: "Avatar") -> dict:
        avatar_name_1 = self.avatar.name
        avatar_name_2 = target_avatar.name
        
        # avatar1 uses expanded_info (detailed info plus shared events) to avoid duplication
        expanded_info = self.avatar.get_expanded_info(other_avatar=target_avatar, detailed=True)
        
        avatar_infos = {
            avatar_name_1: expanded_info,
            avatar_name_2: target_avatar.get_info(detailed=True),
        }
        
        # Get follow-up plans
        p1 = self.avatar.get_planned_actions_str()
        p2 = target_avatar.get_planned_actions_str()
        planned_actions_str = {
            avatar_name_1: p1,
            avatar_name_2: p2,
        }
        return {
            "avatar_infos": avatar_infos,
            "avatar_name_1": avatar_name_1,
            "avatar_name_2": avatar_name_2,
            "planned_actions": planned_actions_str,
        }

    def _can_start(self, target: "Avatar") -> tuple[bool, str]:
        """Conversation has no extra start conditions."""
        return True, ""

    # Override start: custom event message
    def start(self, target_avatar: "Avatar|str", **kwargs) -> Event:
        # Record the start time
        self._start_month_stamp = self.world.month_stamp
        
        # The Conversation action returns NULL_EVENT to avoid a redundant "starts a conversation" event (which would confuse the display order with the conversation event),
        # and there's no need to add_event manually, since both the sidebar and history should only show the final conversation content.
        
        return NULL_EVENT

    def _handle_response_result(self, target: "Avatar", result: dict) -> ActionResult:
        """
        Handle the conversation result returned by the LLM, including content and relation changes.
        Conversation needs no response events (RESPONSE_ACTIONS is empty); it generates content directly.
        """
        thinking = str(result.get("thinking", "")).strip()
        conversation_content = str(result.get("conversation_content", "")).strip()
        target.thinking = thinking

        # Use the start timestamp
        month_stamp = self._start_month_stamp if self._start_month_stamp is not None else self.world.month_stamp

        events_to_return = []

        # Record the conversation content
        if conversation_content:
            content = t("{avatar1} conversation with {avatar2}: {content}",
                       avatar1=self.avatar.name, avatar2=target.name, content=conversation_content)
            content_event = Event(
                month_stamp, 
                content, 
                related_avatars=[self.avatar.id, target.id]
            )
            self._conversation_result_text = content
            self._conversation_target = target
            events_to_return.append(content_event)
        return ActionResult(status=ActionStatus.COMPLETED, events=events_to_return)

    def step(self, target_avatar: "Avatar|str", **kwargs) -> ActionResult:
        """When the player is roleplaying, switch to a runtime conversation session; otherwise reuse the existing async LLM conversation logic."""
        target = self._get_target_avatar(target_avatar)
        if target is None or self._is_dead_avatar(target):
            return ActionResult(status=ActionStatus.FAILED, events=[])

        from src.sim.runtime_capabilities import get_decision_boundary_gateway

        gateway = get_decision_boundary_gateway(self.world)
        if gateway is None:
            return super().step(target_avatar=target_avatar)
        if not gateway.controls_avatar(str(self.avatar.id)):
            return super().step(target_avatar=target_avatar)

        session = gateway.get_session()
        conversation_session = session.get("conversation_session") or {}
        is_matching_session = (
            str(conversation_session.get("avatar_id") or "") == str(self.avatar.id)
            and str(conversation_session.get("target_avatar_id") or "") == str(target.id)
        )

        if is_matching_session and str(conversation_session.get("status") or "") == "completed":
            summary_payload = conversation_session.get("last_summary") or {}
            summary_text = str(summary_payload.get("summary", "") or "").strip()
            relation_hint = str(summary_payload.get("relation_hint", "") or "").strip()
            story_hint = str(summary_payload.get("story_hint", "") or "").strip()
            target.thinking = str(conversation_session.get("last_ai_thinking", "") or "")
            events_to_return = []
            if summary_text:
                event = Event(
                    self._start_month_stamp if self._start_month_stamp is not None else self.world.month_stamp,
                    summary_text,
                    related_avatars=[self.avatar.id, target.id],
                )
                self._conversation_result_text = summary_text
                self._conversation_relation_hint = relation_hint
                self._conversation_story_hint = story_hint
                self._conversation_target = target
                events_to_return.append(event)
            session["conversation_session"] = None
            session["pending_request"] = None
            if str(session.get("status") or "") != "inactive":
                session["status"] = "observing"
            return ActionResult(status=ActionStatus.COMPLETED, events=events_to_return)

        if not is_matching_session:
            gateway.begin_conversation(avatar=self.avatar, target_avatar=target)

        return ActionResult(status=ActionStatus.RUNNING, events=[])

    async def finish(self, target_avatar: "Avatar|str") -> list[Event]:
        target = getattr(self, "_conversation_target", None) or self._get_target_avatar(target_avatar)
        result_text = getattr(self, "_conversation_result_text", "")
        relation_hint = str(getattr(self, "_conversation_relation_hint", "") or "").strip()
        story_hint = str(getattr(self, "_conversation_story_hint", "") or "").strip()
        if target is None or not result_text:
            return []

        relation_resolution_text = result_text
        if relation_hint:
            relation_resolution_text = f"{result_text}\n[relation_hint={relation_hint}]"

        a_to_b, b_to_a = await RelationDeltaService.resolve_event_text_delta(
            action_key="conversation",
            avatar_a=self.avatar,
            avatar_b=target,
            event_text=relation_resolution_text,
        )
        RelationDeltaService.apply_bidirectional_delta(self.avatar, target, a_to_b, b_to_a)

        story_event = await StoryEventService.maybe_create_story(
            kind=StoryEventKind.DAILY_SOCIAL,
            month_stamp=self.world.month_stamp,
            start_text=result_text,
            result_text=result_text,
            actors=[self.avatar, target],
            related_avatar_ids=[self.avatar.id, target.id],
            prompt=story_hint,
            allow_relation_changes=False,
        )
        return [story_event] if story_event is not None else []

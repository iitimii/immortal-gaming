from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
import asyncio

from src.i18n import t
from src.classes.action.action import DefineAction, ActualActionMixin, LLMAction
from src.classes.action.param_options import ParamOptionSource
from src.classes.event import Event, NULL_EVENT
from src.utils.llm import call_llm_with_task_name
from src.utils.config import CONFIG
from src.classes.action_runtime import ActionResult, ActionStatus
from src.classes.action.event_helper import EventHelper
from src.classes.action.targeting_mixin import TargetingMixin

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar
    from src.classes.core.world import World


@dataclass(slots=True)
class _MutualActionResponseScenario:
    action: "MutualAction"
    target_avatar: "Avatar"
    request: object

    def build_request(self):
        return self.request

    async def apply_decision(self, decision):
        return {
            self.target_avatar.name: {
                "thinking": decision.thinking,
                "response": decision.selected_key,
                "feedback": decision.selected_key,
            }
        }


class MutualAction(DefineAction, LLMAction, ActualActionMixin, TargetingMixin):
    """
    Mutual action: A initiates an action toward B, and B can respond (decided by the LLM).
    Subclasses must define:
      - ACTION_NAME_ID: msgid of the action name
      - DESC_ID: msgid of the action's semantic description
      - REQUIREMENTS_ID: msgid of the executable conditions
      - RESPONSE_ACTIONS: list of action names available as responses (directly executable)
      - PARAMS: params, must include target_avatar
    """
    
    # i18n IDs (overridden by subclasses)
    ACTION_NAME_ID: str = "mutual_action_name"
    DESC_ID: str = ""
    REQUIREMENTS_ID: str = "mutual_action_requirements"
    STORY_PROMPT_ID: str = ""
    
    # Constants that need no translation
    EMOJI: str = "💬"
    PARAMS: dict = {"target_avatar": "Avatar"}
    PARAM_OPTION_SOURCES: dict[str, ParamOptionSource] = {
        "target_avatar": ParamOptionSource.OBSERVABLE_AVATAR_NAME,
    }
    RESPONSE_ACTIONS: list[str] = []
    RESPONSE_EVENT_STYLE: str = "reply"
    SHOW_RESPONSE_EVENT: bool = False
    
    # Response action -> msgid mapping (subclasses may override)
    RESPONSE_LABEL_IDS: dict[str, str] = {
        "Accept": "feedback_accept",
        "Reject": "feedback_reject",
        "MoveAwayFromAvatar": "feedback_move_away_from_avatar",
        "MoveAwayFromRegion": "feedback_move_away_from_region",
        "Escape": "feedback_escape",
        "Attack": "feedback_attack",
    }
    
    @classmethod
    def get_action_name(cls) -> str:
        """Get the translated action name."""
        if cls.ACTION_NAME_ID:
            return t(cls.ACTION_NAME_ID)
        return cls.__name__
    
    @classmethod
    def get_desc(cls) -> str:
        """Get the translated action description."""
        if cls.DESC_ID:
            return t(cls.DESC_ID)
        return ""
    
    @classmethod
    def get_requirements(cls) -> str:
        """Get the translated executable conditions."""
        if cls.REQUIREMENTS_ID:
            return t(cls.REQUIREMENTS_ID)
        return ""
    
    @classmethod
    def get_response_label(cls, response_name: str) -> str:
        """Get the translated response label."""
        msgid = cls.RESPONSE_LABEL_IDS.get(response_name, "")
        if msgid:
            return t(msgid)
        return response_name
    
    @classmethod
    def get_story_prompt(cls) -> str:
        """Get the translated story prompt."""
        if cls.STORY_PROMPT_ID:
            return t(cls.STORY_PROMPT_ID)
        return ""

    def __init__(self, avatar: "Avatar", world: "World"):
        super().__init__(avatar, world)
        # Async response task handle and cached result
        self._response_task: asyncio.Task | None = None
        self._response_cached: dict | None = None
        # Record the action start time, used as the timestamp of generated events
        self._start_month_stamp: int | None = None

    def _get_template_path(self) -> Path:
        return CONFIG.paths.templates / "mutual_action.txt"

    @staticmethod
    def _is_dead_avatar(target_avatar: "Avatar | None") -> bool:
        if target_avatar is None:
            return False
        return getattr(target_avatar, "is_dead", False) is True

    def _build_prompt_infos(self, target_avatar: "Avatar") -> dict:
        avatar_name_1 = self.avatar.name
        avatar_name_2 = target_avatar.name
        
        # avatar1 uses expanded_info (non-detailed info plus shared events) to avoid duplication
        expanded_info = self.avatar.get_expanded_info(other_avatar=target_avatar, detailed=False)
        
        avatar_infos = {
            avatar_name_1: expanded_info,
            avatar_name_2: target_avatar.get_info(detailed=False),
        }
        
        world_info = self.world.static_info

        response_actions = self.RESPONSE_ACTIONS
        desc = self.get_desc()  # Get the translation via classmethod
        action_name = self.get_action_name()  # Get the translation via classmethod
        return {
            "world_info": world_info,
            "avatar_infos": avatar_infos,
            "avatar_name_1": avatar_name_1,
            "avatar_name_2": avatar_name_2,
            "action_name": action_name,
            "action_info": desc,
            "response_actions": response_actions,
            # Keep the template compatibility field to avoid inconsistencies when changing the prompt rendering chain
            "feedback_actions": response_actions,
        }

    async def _call_llm_response(self, infos: dict) -> dict:
        """Asynchronously call the LLM for a response."""
        template_path = self._get_template_path()
        return await call_llm_with_task_name("interaction_feedback", template_path, infos)

    def _build_response_choice_request(self, target_avatar: "Avatar"):
        from src.systems.single_choice import (
            FallbackMode,
            FallbackPolicy,
            SingleChoiceOption,
            SingleChoiceRequest,
        )

        action_name = self.get_action_name()
        situation = getattr(self, "_start_event_content", "") or self.get_desc() or action_name
        response_options = [
            SingleChoiceOption(
                key=response_name,
                title=self.get_response_label(response_name),
                description=f"{target_avatar.name}: {self.get_response_label(response_name)}",
                metadata={"display_variant": "reject" if response_name == "Reject" else "accept"},
            )
            for response_name in self.RESPONSE_ACTIONS
        ]

        avatar_infos = {
            target_avatar.name: target_avatar.get_info(detailed=True),
            self.avatar.name: self.avatar.get_expanded_info(other_avatar=target_avatar, detailed=True),
        }

        return SingleChoiceRequest(
            task_name="single_choice",
            template_path=CONFIG.paths.templates / "single_choice.txt",
            avatar=target_avatar,
            request_id=f"mutual-action-{type(self).__name__}-{self.avatar.id}-{target_avatar.id}",
            title=f"{target_avatar.name}: {action_name}",
            description=situation,
            situation=situation,
            options=response_options,
            fallback_policy=FallbackPolicy(mode=FallbackMode.FIRST_OPTION),
            context={
                "avatar_infos": avatar_infos,
                "initiator_name": self.avatar.name,
                "target_name": target_avatar.name,
                "action_name": action_name,
                "action_info": self.get_desc(),
            },
        )

    async def _call_response_resolution(self, target_avatar: "Avatar") -> dict:
        if not self.RESPONSE_ACTIONS:
            infos = self._build_prompt_infos(target_avatar)
            return await self._call_llm_response(infos)

        from src.systems.single_choice import resolve_single_choice

        scenario = _MutualActionResponseScenario(
            action=self,
            target_avatar=target_avatar,
            request=self._build_response_choice_request(target_avatar),
        )
        return await resolve_single_choice(scenario)

    def _set_target_immediate_action(
        self,
        target_avatar: "Avatar",
        action_name: str,
        action_params: dict,
        *,
        push_start_event: bool = True,
    ) -> None:
        """
        Apply the response decision as the target's immediate action (clear, then load a single-step action chain).
        """
        # If the current action is already the same class with the same params, skip it, to avoid spamming events like "starts a battle"
        try:
            cur = target_avatar.current_action
            if cur is not None:
                cur_name = getattr(cur.action, "__class__", type(cur.action)).__name__
                if cur_name == action_name:
                    if getattr(cur, "params", {}) == dict(action_params):
                        return
        except Exception:
            pass
        # Preempt: clear subsequent plans and interrupt the current action
        self.preempt_avatar(target_avatar)
        # Load it as a plan first
        target_avatar.load_decide_result_chain([(action_name, action_params)], target_avatar.thinking, "")
        # Commit immediately as the current action, triggering the start event
        start_event = target_avatar.commit_next_plan()
        if push_start_event and start_event is not None and start_event != NULL_EVENT:
            # The sidebar is pushed only once (by the initiator); the other side only writes history
            EventHelper.push_pair(start_event, initiator=self.avatar, target=target_avatar, to_sidebar_once=True)

    def _settle_response(self, target_avatar: "Avatar", response_name: str) -> None:
        """
        Implemented by subclasses: map the response to a concrete action
        """
        pass

    def _apply_response(self, target_avatar: "Avatar", response_name: str) -> None:
        # No extra recording by default; handled by the event system
        return

    def _handle_response_result(self, target_avatar: "Avatar", result: dict) -> ActionResult:
        thinking = result.get("thinking", "")
        response = result.get("response", result.get("feedback", ""))

        target_avatar.thinking = thinking
        self._settle_response(target_avatar, response)

        response_event = self._build_response_event(target_avatar, response)
        self._apply_response(target_avatar, response)

        events = [response_event] if response_event is not None else []
        return ActionResult(status=ActionStatus.COMPLETED, events=events)

    def _build_response_event_content(self, target_avatar: "Avatar", response_name: str) -> str:
        response_label = self.get_response_label(str(response_name).strip())
        return t(
            "{target} feedback to {initiator}: {feedback}",
            target=target_avatar.name,
            initiator=self.avatar.name,
            feedback=response_label,
        )

    def _build_response_event(self, target_avatar: "Avatar", response_name: str) -> Event | None:
        if self.RESPONSE_EVENT_STYLE == "none" or not self.SHOW_RESPONSE_EVENT:
            return None

        month_stamp = self._start_month_stamp if self._start_month_stamp is not None else self.world.month_stamp
        content = self._build_response_event_content(target_avatar, response_name)
        event = Event(month_stamp, content, related_avatars=[self.avatar.id, target_avatar.id])
        self._last_response_event_content = content
        return event

    def _get_target_avatar(self, target_avatar: "Avatar|str") -> "Avatar|None":
        if isinstance(target_avatar, str):
            return self.find_avatar_by_name(target_avatar)
        return target_avatar
    
    async def _execute(self, target_avatar: "Avatar|str") -> None:
        """Run the mutual action asynchronously (deprecated, use step instead)."""
        # Only for compatibility with the DefineAction interface; the actual logic is in step
        pass

    # Implement the ActualActionMixin interface
    def can_start(self, target_avatar: "Avatar|str") -> tuple[bool, str]:
        """
        Check whether the mutual action can start: the target must be within the initiator's interaction range.
        Subclasses add extra checks by implementing _can_start.

        Note: this method doesn't use TargetingMixin.validate_target_avatar(),
        because it additionally checks target == self.avatar and calls the subclass's _can_start().
        """
        target = self._get_target_avatar(target_avatar)
        if target is None:
            return False, t("Target does not exist")
        if target == self.avatar:
            return False, t("Cannot initiate interaction with self")
        if self._is_dead_avatar(target):
            return False, t("Target is already dead")
        # Call the subclass's extra checks
        return self._can_start(target)

    def _can_start(self, target: "Avatar") -> tuple[bool, str]:
        """
        Implemented by subclasses to add specific start condition checks.
        The target param has already been validated by the base class (exists and within interaction range).
        Returns True by default.
        """
        return True, ""

    def start(self, target_avatar: "Avatar|str") -> Event:
        """
        Start the mutual action and return the start event
        """
        target = self._get_target_avatar(target_avatar)
        if self._is_dead_avatar(target):
            return NULL_EVENT

        # Record the start time
        self._start_month_stamp = self.world.month_stamp
        target_name = target.name if target is not None else str(target_avatar)
        action_name = self.get_action_name()
        rel_ids = [self.avatar.id]
        if target is not None:
            rel_ids.append(target.id)
        # Set the event type from the IS_MAJOR class variable
        is_major = self.__class__.IS_MAJOR if hasattr(self.__class__, 'IS_MAJOR') else False
        
        content = t("{initiator} initiates {action} with {target}",
                   initiator=self.avatar.name, action=action_name, target=target_name)
        event = Event(self._start_month_stamp, content, related_avatars=rel_ids, is_major=is_major)
        self._start_event_content = event.content
        return event

    def step(self, target_avatar: "Avatar|str") -> ActionResult:
        """
        Async: the first frame launches the LLM task and returns RUNNING; once the task completes, later frames apply the response and finish.
        """
        target = self._get_target_avatar(target_avatar)
        if target is None or self._is_dead_avatar(target):
            return ActionResult(status=ActionStatus.FAILED, events=[])

        # If there is no task, create an async task
        if self._response_task is None and self._response_cached is None:
            loop = asyncio.get_running_loop()
            # Some unit tests patch get_running_loop() with a bare MagicMock just to
            # bypass async scheduling. In that case, creating the coroutine here would
            # leak an un-awaited coroutine object and emit RuntimeWarning.
            if isinstance(loop, asyncio.AbstractEventLoop):
                self._response_task = loop.create_task(self._call_response_resolution(target))
            else:
                return ActionResult(status=ActionStatus.RUNNING, events=[])

        # If the task is done, consume the result
        if self._response_task is not None and self._response_task.done():
            self._response_cached = self._response_task.result()
            self._response_task = None

        if self._response_cached is not None:
            res = self._response_cached
            self._response_cached = None
            r = res.get(target.name, {})
            return self._handle_response_result(target, r)

        return ActionResult(status=ActionStatus.RUNNING, events=[])

    async def finish(self, target_avatar: "Avatar|str") -> list[Event]:
        """
        Finish the mutual action; events were handled in step, so no extra event is needed
        """
        return []


class InvitationAction(MutualAction):
    """Invitation/request-type interaction; the target mainly accepts or refuses."""

    RESPONSE_EVENT_STYLE = "reply"
    SHOW_RESPONSE_EVENT = False


class PressureAction(MutualAction):
    """Pressure/hostile-type interaction; the target mainly flees, fights back, etc."""

    RESPONSE_EVENT_STYLE = "reply"
    SHOW_RESPONSE_EVENT = False

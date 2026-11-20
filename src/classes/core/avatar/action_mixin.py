"""
Avatar action management mixin
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from src.classes.core.avatar.core import Avatar

from src.classes.action import Action
from src.classes.action_runtime import ActionStatus, ActionResult, ActionPlan, ActionInstance
from src.classes.action.registry import ActionRegistry
from src.classes.event import Event
from src.classes.typings import ACTION_NAME, ACTION_NAME_PARAMS_PAIRS
from src.utils.params import filter_kwargs_for_callable
from src.run.log import get_logger


from src.utils.config import CONFIG

class ActionMixin:
    """Action management methods."""
    
    def create_action(self: "Avatar", action_name: ACTION_NAME) -> Action:
        """
        Create a new action instance from an action name.
        
        Args:
            action_name: name of the action class (e.g. 'Respire', 'Breakthrough')
        
        Returns:
            The newly created Action instance
        
        Raises:
            ValueError: if no matching action class is found
        """
        action_cls = ActionRegistry.get(action_name)
        return action_cls(self, self.world)

    def load_decide_result_chain(
        self: "Avatar",
        action_name_params_pairs: ACTION_NAME_PARAMS_PAIRS,
        avatar_thinking: str,
        short_term_objective: str,
        prepend: bool = False
    ):
        """
        Load the AI's decision (action chain): set the first as the current action immediately and queue the rest.
        
        Args:
            action_name_params_pairs: list of (action name, params) pairs
            avatar_thinking: thinking content
            short_term_objective: short-term objective
            prepend: whether to jump to the front of the queue (default False, i.e. append to the end)
        """
        if not action_name_params_pairs:
            return
        self.thinking = avatar_thinking
        self.short_term_objective = short_term_objective
        # Convert to plans and enqueue (not committed immediately; the commit phase triggers start events uniformly)
        plans: List[ActionPlan] = [ActionPlan(name, params) for name, params in action_name_params_pairs]
        if prepend:
            self.planned_actions[0:0] = plans
        else:
            self.planned_actions.extend(plans)

    def clear_plans(self: "Avatar") -> None:
        self.planned_actions.clear()

    def has_plans(self: "Avatar") -> bool:
        return len(self.planned_actions) > 0

    def commit_next_plan(self: "Avatar") -> Optional[Event]:
        """
        Commit the next startable plan as the current action; return the start event (if any).
        """
        if self.current_action is not None:
            return None
        while self.planned_actions:
            plan = self.planned_actions.pop(0)
            try:
                action = self.create_action(plan.action_name)
            except Exception as e:
                logger = get_logger().logger
                logger.warning(
                    "Illegal action: Avatar(name=%s,id=%s) action %s params=%s cannot start, reason=%s",
                    self.name, self.id, plan.action_name, plan.params, e
                )
                continue
            # Validate again
            if not isinstance(plan.params, dict):
                get_logger().logger.warning(
                    "Illegal params: Avatar(name=%s) action %s has wrong param types: %s",
                    self.name, plan.action_name, type(plan.params)
                )
                continue

            params_for_can_start = filter_kwargs_for_callable(action.can_start, plan.params)
            try:
                can_start, reason = action.can_start(**params_for_can_start)
            except TypeError as e:
                get_logger().logger.warning(
                    "Action start failed: Avatar(name=%s) action %s param validation error: %s",
                    self.name, plan.action_name, e
                )
                continue

            if not can_start:
                # Record the illegal action
                logger = get_logger().logger
                logger.warning(
                    "Illegal action: Avatar(name=%s,id=%s) action %s params=%s cannot start, reason=%s",
                    self.name, self.id, plan.action_name, plan.params, reason
                )
                continue
            # Start
            params_for_start = filter_kwargs_for_callable(action.start, plan.params)
            start_event = action.start(**params_for_start)
            self.current_action = ActionInstance(action=action, params=plan.params, status="running")
            # Mark as "action newly set this round", used for supplementary execution this month
            self._new_action_set_this_step = True
            return start_event
        return None

    async def tick_action(self: "Avatar") -> List[Event]:
        """
        Advance the current action by one step; return events produced inside the action along the way (collected via add_event).
        """
        if self.current_action is None:
            return []
        # Keep a reference to the current action instance to detect "preemption/switching" during execution
        action_instance_before = self.current_action
        action = action_instance_before.action
        params = action_instance_before.params
        params_for_step = filter_kwargs_for_callable(action.step, params)
        result: ActionResult = action.step(**params_for_step)
        if result.status == ActionStatus.COMPLETED:
            params_for_finish = filter_kwargs_for_callable(action.finish, params)
            finish_events = await action.finish(**params_for_finish)
            if finish_events:
                # Allow finish to return events directly (rare); merge them into pending
                for e in finish_events:
                    self._pending_events.append(e)
            try:
                from src.systems.background_npc import try_trigger_background_npc_action_echo

                action_echo_events = try_trigger_background_npc_action_echo(
                    self.world,
                    self,
                    action.__class__.__name__,
                )
                for event in action_echo_events:
                    self._pending_events.append(event)
            except Exception as exc:
                get_logger().logger.warning(
                    "Background NPC action echo generation failed: Avatar(name=%s,id=%s) action=%s reason=%s",
                    self.name,
                    self.id,
                    action.__class__.__name__,
                    exc,
                )
                    
        # Merge events returned by the action (usually empty)
        if result.events:
            for e in result.events:
                self.add_event(e)
                
        # Only clear if the current action is still the instance just executed
        # If step() switched actions via "preemption" (e.g. failed Escape immediately switches to Attack), don't clear the new action
        # All non-RUNNING states (COMPLETED, FAILED, CANCELLED, INTERRUPTED) mean the action has ended and the slot must be cleared
        if result.status != ActionStatus.RUNNING:
            if self.current_action is action_instance_before:
                self.current_action = None

        events, self._pending_events = self._pending_events, []
        # Already executed this round; clear the "newly set action" flag when
        # 1. the action ended (None)
        # 2. the action continues without being switched (is action_instance_before)
        # Note: if the action switched (e.g. Escape -> Attack), treat it as a new action and keep the flag so the Simulator schedules another round
        if self.current_action is None or self.current_action is action_instance_before:
            self._new_action_set_this_step = False
            
        return events

    def add_event(self: "Avatar", event: Event, *, to_sidebar: bool = True) -> None:
        """
        Add an event:
        - to_sidebar: whether it goes to the global sidebar (buffered in Avatar._pending_events)
        
        Note: events are first stored in _pending_events and written to event_manager by the Simulator, to avoid duplicates
        """
        if to_sidebar:
            self._pending_events.append(event)
        
    def process_interaction_from_event(self: "Avatar", event: "Event") -> None:
        """
        The old logic of counting interactions per event is deprecated.
        The new relation system has actions/gatherings write friendliness changes directly at settlement.
        """
        return

    def get_planned_actions_str(self: "Avatar") -> str:
        """
        Get a readable string of the planned action list.
        """
        from src.i18n import t
        if not self.planned_actions:
            return t("None")
        
        lines = []
        for i, plan in enumerate(self.planned_actions, 1):
            try:
                action_cls = ActionRegistry.get(plan.action_name)
                # Prefer ACTION_NAME, otherwise use the class name
                display_name = getattr(action_cls, "ACTION_NAME", plan.action_name)
            except Exception:
                display_name = plan.action_name
            
            # Simplify param display; keep only basic types
            simple_params = {k: v for k, v in plan.params.items() if isinstance(v, (str, int, float, bool))}
            info = f"{i}. {display_name}"
            if simple_params:
                info += f" {simple_params}"
            
            lines.append(info)
            
        return "\n".join(lines)

    @property
    def can_join_gathering(self: "Avatar") -> bool:
        """Whether the avatar can join a gathering."""
        can_interrupt = getattr(CONFIG.world, 'can_interrupt_major_events', False)
        
        if self.current_action and self.current_action.action:
            action_cls = self.current_action.action.__class__
            if action_cls.can_gather():
                return True
            # The action itself disallows gatherings, but config allows interrupting major actions and this major action doesn't explicitly refuse
            if can_interrupt and getattr(action_cls, 'IS_MAJOR', False) and action_cls.ALLOW_GATHERING is None:
                return True
            return False
            
        return True # Idle avatars can join by default

    @property
    def can_trigger_world_event(self: "Avatar") -> bool:
        """Whether fortune/misfortune can be triggered."""
        can_interrupt = getattr(CONFIG.world, 'can_interrupt_major_events', False)
        
        if self.current_action and self.current_action.action:
            action_cls = self.current_action.action.__class__
            if action_cls.can_trigger_events():
                return True
            # Same as above: handle the global interruption config
            if can_interrupt and getattr(action_cls, 'IS_MAJOR', False) and action_cls.ALLOW_WORLD_EVENTS is None:
                return True
            return False
            
        return True

    @property
    def is_in_major_action(self: "Avatar") -> bool:
        """Whether a major action is in progress."""
        if self.current_action and self.current_action.action:
            return getattr(self.current_action.action, 'IS_MAJOR', False)
        return False



from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from src.i18n import t
from src.classes.event import Event
from src.classes.action_runtime import ActionResult, ActionStatus
from src.utils.params import filter_kwargs_for_callable

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar
    from src.classes.core.world import World


def long_action(step_month: int):
    """
    Long-running action decorator that automatically adds time management to action classes

    Args:
        step_month: number of months the action takes
    """
    def decorator(cls):
        # Set class attributes for the base class to use
        cls._step_month = step_month

        def is_finished(self, *args, **kwargs) -> bool:
            """
            Determine whether the action is finished from the elapsed time
            Accepts but ignores extra params for compatibility with other action types
            """
            if self.start_monthstamp is None:
                return False
            # Corrected logic: use >= step_month - 1 instead of >= step_month
            # So a 1-month action completes in month 1 (diff 0 >= 0), a 10-month action completes in month 10 (diff 9 >= 9)
            # This avoids the old bug of running one extra month
            return (self.world.month_stamp - self.start_monthstamp) >= self.step_month - 1

        # Only add the is_finished method
        cls.is_finished = is_finished

        return cls

    return decorator


class Action(ABC):
    """
    Actions an avatar can perform.
    For example: move, attack, gather, build, etc.
    """
    
    # i18n class variables (overridden by subclasses)
    ACTION_NAME_ID: str = ""
    DESC_ID: str = ""
    REQUIREMENTS_ID: str = ""

    # Whether joining gatherings is allowed (e.g. auctions, tournaments)
    ALLOW_GATHERING: bool | None = None
    
    # Whether world random events may trigger (e.g. fortune, misfortune)
    ALLOW_WORLD_EVENTS: bool | None = None

    @classmethod
    def can_gather(cls) -> bool:
        """Whether joining gatherings is allowed: use the explicit config if set; otherwise major actions disallow by default and non-major actions allow."""
        if cls.ALLOW_GATHERING is not None:
            return cls.ALLOW_GATHERING
        return not getattr(cls, 'IS_MAJOR', False)

    @classmethod
    def can_trigger_events(cls) -> bool:
        """Whether fortune/misfortune is allowed: use the explicit config if set; otherwise major actions disallow by default and non-major actions allow."""
        if cls.ALLOW_WORLD_EVENTS is not None:
            return cls.ALLOW_WORLD_EVENTS
        return not getattr(cls, 'IS_MAJOR', False)

    def __init__(self, avatar: Avatar, world: World):
        """
        Pass in a ref to the avatar
        so that at execution time the avatar's abilities and state are known.
        A world can optionally be passed; otherwise it is taken from avatar.world.
        """
        self.avatar = avatar
        self.world = world

    @abstractmethod
    def execute(self) -> None:
        pass

    @property
    def name(self) -> str:
        """
        Get the action name
        """
        return str(self.__class__.__name__)

    EMOJI: str = ""
    
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

    def get_save_data(self) -> dict:
        """Get runtime data that needs to be saved."""
        return {}

    def load_save_data(self, data: dict) -> None:
        """Load runtime data."""
        pass

    def can_possibly_start(self) -> bool:
        """
        Determine whether the action could possibly start.
        Used during AI decisions to filter out actions that absolutely can't be executed, reducing prompt length.
        """
        return True


class DefineAction(Action):
    def __init__(self, avatar: Avatar, world: World):
        """
        Initialize the action, handling long-running action attributes
        """
        super().__init__(avatar, world)

        # If it's a long-running action, initialize related attributes
        if hasattr(self.__class__, '_step_month'):
            self.step_month = self.__class__._step_month
            self.start_monthstamp = None

    def execute(self, *args, **kwargs) -> None:
        """
        Execute the action, handling time management, then call the concrete _execute implementation
        """
        # If it's a long-running action executing for the first time, record the start time
        if hasattr(self, 'step_month') and self.start_monthstamp is None:
            self.start_monthstamp = self.world.month_stamp

        self._execute(*args, **kwargs)

    @abstractmethod
    def _execute(self, *args, **kwargs) -> None:
        """
        Concrete action execution logic, implemented by subclasses
        """
        pass

    def get_save_data(self) -> dict:
        data = super().get_save_data()
        # Many long-running actions (including MoveToDirection) set this attribute
        if hasattr(self, 'start_monthstamp'):
            val = self.start_monthstamp
            data['start_monthstamp'] = int(val) if val is not None else None
        return data

    def load_save_data(self, data: dict) -> None:
        super().load_save_data(data)
        if 'start_monthstamp' in data:
            val = data['start_monthstamp']
            if val is not None:
                from src.systems.time import MonthStamp
                self.start_monthstamp = MonthStamp(val)
            else:
                self.start_monthstamp = None


class LLMAction(Action):
    """
    LLM-based actions; these generally don't need concrete rule definitions.
    They're abstract definitions with only social consequences,
    such as "humiliate", "glare viciously", "break off an engagement", etc.
    Such actions are generated and executed via the LLM, so NPCs remember them and they have consequences,
    but the rule side doesn't need to react.
    """

    pass


class ChunkActionMixin():
    """
    Action segment: think of it as a sliced-out piece of an action.
    It can't be executed directly by an avatar; it becomes a step of some action the avatar performs.
    """

    pass


class ActualActionMixin():
    """
    An actual action that rules/LLM can call to have an avatar execute.
    Not necessarily multi-step; it may be a single step.

    New interface: subclasses must implement can_start/start/step/finish.
    
    Class variables:
    - IS_MAJOR: whether it's a major event (long-term memory), default False (minor / short-term memory)
    """
    
    # Minor event (short-term memory) by default
    IS_MAJOR: bool = False

    def create_event(self, content: str, related_avatars=None) -> Event:
        """
        Helper to create an event, automatically carrying the is_major attribute
        
        Args:
            content: event content
            related_avatars: list of related avatar IDs
            
        Returns:
            An Event object, with is_major set from the current Action's IS_MAJOR class variable
        """
        from src.classes.action.action import Action
        # Get the current class's IS_MAJOR attribute
        is_major = self.__class__.IS_MAJOR if hasattr(self.__class__, 'IS_MAJOR') else False
        return Event(
            month_stamp=self.world.month_stamp,
            content=content,
            related_avatars=related_avatars,
            is_major=is_major
        )

    @abstractmethod
    def can_start(self, **params) -> tuple[bool, str]:
        return True, ""

    @abstractmethod
    def start(self, **params) -> Event | None:
        return None

    @abstractmethod
    def step(self, **params) -> ActionResult:
        ...

    @abstractmethod
    async def finish(self, **params) -> list[Event]:
        return []


class InstantAction(DefineAction, ActualActionMixin):
    """
    One-shot action: completes within one step. Subclasses only need to implement _execute.
    """

    def step(self, **params) -> ActionResult:
        params_for_execute = filter_kwargs_for_callable(self._execute, params)
        self._execute(**params_for_execute)
        return ActionResult(status=ActionStatus.COMPLETED, events=[])


class TimedAction(DefineAction, ActualActionMixin):
    """
    Long-running action: duration is controlled by the duration_months class attribute.
    Subclasses implement _execute as the monthly execution logic.
    """

    duration_months: int = 1

    def step(self, **params) -> ActionResult:
        if not hasattr(self, 'start_monthstamp') or self.start_monthstamp is None:
            self.start_monthstamp = self.world.month_stamp
        params_for_execute = filter_kwargs_for_callable(self._execute, params)
        self._execute(**params_for_execute)
        done = (self.world.month_stamp - self.start_monthstamp) >= (self.duration_months - 1)
        return ActionResult(status=(ActionStatus.COMPLETED if done else ActionStatus.RUNNING), events=[])

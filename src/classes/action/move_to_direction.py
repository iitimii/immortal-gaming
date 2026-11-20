from __future__ import annotations

import random
from src.i18n import t
from src.classes.action import DefineAction, ActualActionMixin, Move
from src.classes.action.param_options import ParamOptionSource
from src.classes.event import Event
from src.classes.action_runtime import ActionResult, ActionStatus
from src.utils.distance import manhattan_distance
from src.classes.environment.region import Region

class Direction:
    """
    Direction helper: centralizes direction vector definitions and name conversion
    """
    # Vector mapping (assuming (0,0) is the top-left corner)
    # North: y decreases
    # South: y increases
    # West: x decreases
    # East: x increases
    _VECTORS = {
        "North": (0, -1),
        "South": (0, 1),
        "West": (-1, 0),
        "East": (1, 0),
        "north": (0, -1),
        "south": (0, 1),
        "west": (-1, 0),
        "east": (1, 0),
    }

    _MSGIDS = {
        "North": "north",
        "South": "south",
        "West": "west",
        "East": "east",
        "north": "north",
        "south": "south",
        "west": "west",
        "east": "east",
    }

    @classmethod
    def is_valid(cls, direction: str) -> bool:
        return direction in cls._VECTORS

    @classmethod
    def get_vector(cls, direction: str) -> tuple[int, int]:
        return cls._VECTORS.get(direction, (0, 0))

    @classmethod
    def get_msgid(cls, direction: str) -> str:
        return cls._MSGIDS.get(direction, direction)


class MoveToDirection(DefineAction, ActualActionMixin):
    """
    Move and explore in a direction (fixed duration of 6 months)
    """
    
    # i18n IDs
    ACTION_NAME_ID = "move_to_direction_action_name"
    DESC_ID = "move_to_direction_description"
    REQUIREMENTS_ID = "move_to_direction_requirements"
    
    # Constants that need no translation
    EMOJI = "🧭"
    PARAMS = {"direction": "direction (north/south/east/west)"}
    PARAM_OPTION_SOURCES = {"direction": ParamOptionSource.CARDINAL_DIRECTION}
    IS_MAJOR = False
    
    # Fixed duration
    DURATION = 6

    def __init__(self, avatar, world):
        super().__init__(avatar, world)
        # Record the start state of this action
        self.start_monthstamp = None
        self.direction = None

    def can_start(self, direction: str) -> tuple[bool, str]:
        if not Direction.is_valid(direction):
            return False, t("Invalid direction: {direction}", direction=direction)
        return True, ""

    def start(self, direction: str) -> Event:
        self.start_monthstamp = self.world.month_stamp
        self.direction = direction
        direction_translated = t(Direction.get_msgid(direction))
        content = t("{avatar} begins moving toward {direction}",
                   avatar=self.avatar.name, direction=direction_translated)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])

    def step(self, direction: str) -> ActionResult:
        # Make sure the direction is set
        self.direction = direction
        dx_dir, dy_dir = Direction.get_vector(direction)
        
        # Compute this move's step length
        step_len = getattr(self.avatar, "move_step_length", 1)
        
        # Compute the actual displacement
        dx = dx_dir * step_len
        dy = dy_dir * step_len
        
        # Perform the move
        Move(self.avatar, self.world).execute(dx, dy)
        
        # Check for completion (fixed duration)
        # Fix: (current - start) >= duration - 1, i.e. after the 1st month the diff is 0, so duration=1 completes
        elapsed = self.world.month_stamp - self.start_monthstamp
        is_done = elapsed >= (self.DURATION - 1)
        
        return ActionResult(status=(ActionStatus.COMPLETED if is_done else ActionStatus.RUNNING), events=[])

    async def finish(self, direction: str) -> list[Event]:
        direction_translated = t(Direction.get_msgid(direction))
        content = t("{avatar} finished moving toward {direction}",
                   avatar=self.avatar.name, direction=direction_translated)
        return [Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])]

    def _execute(self, *args, **kwargs):
        pass

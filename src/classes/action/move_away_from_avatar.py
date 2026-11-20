from __future__ import annotations

from src.i18n import t
from src.classes.action import TimedAction, Move
from src.classes.action.param_options import ParamOptionSource
from src.classes.event import Event
from src.classes.action.move_helper import clamp_manhattan_with_diagonal_priority
from src.utils.resolution import resolve_query
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


class MoveAwayFromAvatar(TimedAction):
    """
    Keep moving away from the given avatar, for 6 months.
    - Rule: each month try to increase the Manhattan distance to the target by one step
    - Can start at any time
    """
    
    # i18n IDs
    ACTION_NAME_ID = "move_away_from_avatar_action_name"
    DESC_ID = "move_away_from_avatar_description"
    REQUIREMENTS_ID = "move_away_from_avatar_requirements"
    
    # Constants that need no translation
    EMOJI = "🏃"
    PARAMS = {"avatar_name": "AvatarName"}
    PARAM_OPTION_SOURCES = {"avatar_name": ParamOptionSource.OBSERVABLE_AVATAR_NAME}

    def _find_avatar_by_name(self, name: str) -> "Avatar | None":
        """
        Find an avatar by name or ID; return None if not found.
        """
        from src.classes.core.avatar import Avatar

        return resolve_query(name, self.world, expected_types=[Avatar]).obj

    duration_months = 6

    def _execute(self, avatar_name: str) -> None:
        target = self._find_avatar_by_name(avatar_name)
        if target is None:
            return
        # Direction away: negate the vector from the target to self
        raw_dx = -(target.pos_x - self.avatar.pos_x)
        raw_dy = -(target.pos_y - self.avatar.pos_y)
        step = getattr(self.avatar, "move_step_length", 1)
        dx, dy = clamp_manhattan_with_diagonal_priority(raw_dx, raw_dy, step)
        Move(self.avatar, self.world).execute(dx, dy)

    def can_start(self, avatar_name: str) -> tuple[bool, str]:
        return True, ""

    def start(self, avatar_name: str) -> Event:
        target_name = avatar_name
        try:
            target = self._find_avatar_by_name(avatar_name)
            if target is not None:
                target_name = target.name
        except Exception:
            pass
        rel_ids = [self.avatar.id]
        try:
            target = self._find_avatar_by_name(avatar_name)
            if target is not None:
                rel_ids.append(target.id)
        except Exception:
            pass
        content = t("{avatar} begins moving away from {target}",
                   avatar=self.avatar.name, target=target_name)
        return Event(self.world.month_stamp, content, related_avatars=rel_ids)

    # TimedAction already unifies the step logic

    async def finish(self, avatar_name: str) -> list[Event]:
        return []



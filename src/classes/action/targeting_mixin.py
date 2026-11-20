from __future__ import annotations

from typing import Optional, Iterable, TYPE_CHECKING

from src.i18n import t
from src.classes.environment.tile import get_avatar_distance
from src.classes.observe import get_observable_avatars
from src.utils.normalize import normalize_avatar_name
from src.utils.resolution import resolve_query
# Note: avoid importing Avatar directly here to prevent circular imports; use TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


class TargetingMixin:
    """
    Targeting and distance utilities: give action classes unified lookup and preemption abilities.

    Note: exceptions are not swallowed; failure paths return None or False and the caller decides.
    """
    def find_avatar_by_name(self, name: str) -> "Avatar|None":
        """
        Find an avatar by name.
        Normalizes the name automatically (removing parentheses and other extra info) for better tolerance.
        """
            
        # Dynamically import the Avatar class for type checking, or rely directly on resolve_query's internal logic
        # resolve_query needs the world context here
        from src.classes.core.avatar import Avatar
        res = resolve_query(name, self.world, expected_types=[Avatar])
        return res.obj

    def avatars_in_same_region(self, avatar: "Avatar") -> list["Avatar"]:
        return self.world.avatar_manager.get_avatars_in_same_region(avatar)

    def avatars_on_same_tile(self, avatar: "Avatar") -> list["Avatar"]:
        result: list["Avatar"] = []
        my_tile = avatar.tile
        if my_tile is None:
            return []
        for v in self.world.avatar_manager.avatars.values():
            if v is avatar or v.tile is None:
                continue
            if v.tile == my_tile:
                result.append(v)
        return result

    def distance_between(self, a: "Avatar", b: "Avatar") -> int:
        return get_avatar_distance(a, b)

    def avatars_in_observation_range(self, avatar: "Avatar") -> list["Avatar"]:
        return self.world.avatar_manager.get_observable_avatars(avatar)

    def preempt_avatar(self, avatar: "Avatar") -> None:
        """Preempt the target: clear its plans and interrupt its current action."""
        avatar.clear_plans()
        avatar.current_action = None

    def set_immediate_action(self, avatar: "Avatar", action_name: str, params: dict) -> None:
        """Load the action immediately and commit it as the current action, triggering the start event."""
        avatar.load_decide_result_chain([(action_name, params)], avatar.thinking, "")
        avatar.commit_next_plan()

    def validate_target_avatar(self, name: str | None) -> tuple["Avatar | None", bool, str]:
        """
        Validate that the target avatar is valid (exists and is alive).

        Args:
            name: target avatar name.

        Returns:
            (target, can_proceed, reason)
            - target: the found avatar object, None if invalid.
            - can_proceed: whether to proceed.
            - reason: failure reason (empty string on success).
        """
        if not name:
            return None, False, t("Missing target parameter")
        target = self.find_avatar_by_name(name)
        if target is None:
            return None, False, t("Target does not exist")
        if target.is_dead:
            return None, False, t("Target is already dead")
        return target, True, ""

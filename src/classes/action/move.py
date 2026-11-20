from __future__ import annotations

from src.classes.action import DefineAction, ChunkActionMixin
from src.classes.action.move_helper import clamp_manhattan_with_diagonal_priority


class Move(DefineAction, ChunkActionMixin):
    """
    The most basic move action, switching between tiles.
    """
    
    # i18n IDs
    ACTION_NAME_ID = "move_action_name"
    DESC_ID = "move_description"
    
    # Constants that need no translation
    EMOJI = "🏃"
    PARAMS = {"delta_x": "int", "delta_y": "int"}

    def _execute(self, delta_x: int, delta_y: int) -> None:
        """
        Move to a tile
        """
        world = self.world
        # Realm-based move step: Manhattan-limited, diagonal preferred
        step = getattr(self.avatar, "move_step_length", 1)
        # Add the extra move step bonus
        extra_raw = self.avatar.effects.get("extra_move_step", 0)
        step += int(extra_raw or 0)
        clamped_dx, clamped_dy = clamp_manhattan_with_diagonal_priority(delta_x, delta_y, step)

        new_x = self.avatar.pos_x + clamped_dx
        new_y = self.avatar.pos_y + clamped_dy

        # Bounds check: don't move if out of bounds
        if world.map.is_in_bounds(new_x, new_y):
            self.avatar.pos_x = new_x
            self.avatar.pos_y = new_y
            target_tile = world.map.get_tile(new_x, new_y)
            self.avatar.tile = target_tile
        else:
            # Out of bounds: position and tile unchanged
            pass



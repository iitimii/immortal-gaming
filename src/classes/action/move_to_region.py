from __future__ import annotations

import random
from src.i18n import t
from src.classes.action import DefineAction, ActualActionMixin
from src.classes.action.param_options import ParamOptionSource
from src.classes.event import Event
from src.classes.environment.region import Region
from src.classes.environment.sect_region import SectRegion
from src.classes.action import Move
from src.classes.action_runtime import ActionResult, ActionStatus
from src.classes.action.move_helper import clamp_manhattan_with_diagonal_priority
from src.utils.resolution import resolve_query


class MoveToRegion(DefineAction, ActualActionMixin):
    """
    Move to a region
    """
    
    # i18n IDs
    ACTION_NAME_ID = "move_to_region_action_name"
    DESC_ID = "move_to_region_description"
    REQUIREMENTS_ID = "move_to_region_requirements"
    
    # Constants that need no translation
    EMOJI = "🏃"
    PARAMS = {"region": "region_name"}
    PARAM_OPTION_SOURCES = {"region": ParamOptionSource.KNOWN_REGION_NAME}

    def __init__(self, avatar, world):
        super().__init__(avatar, world)
        self.target_loc = None

    def _get_target_loc(self, region: Region) -> tuple[int, int]:
        """
        Get or generate the target coordinate of this move.
        If not yet generated, pick one at random from the region's coordinate set.
        """
        if self.target_loc is not None:
            # Simple check: make sure the target point belongs to the region (guards against edge cases like region changes; optional)
            return self.target_loc

        if hasattr(region, "cors") and region.cors:
            self.target_loc = random.choice(region.cors)
        else:
            # Fallback: if the region has no coordinate set, use the center point
            self.target_loc = region.center_loc
        
        return self.target_loc

    def _execute(self, region: Region | str) -> None:
        """
        Move to a region
        """
        target_region = resolve_query(region, self.world, expected_types=[Region]).obj
        if not target_region:
            return

        target_loc = self._get_target_loc(target_region)
        
        cur_loc = (self.avatar.pos_x, self.avatar.pos_y)
        raw_dx = target_loc[0] - cur_loc[0]
        raw_dy = target_loc[1] - cur_loc[1]
        
        step = getattr(self.avatar, "move_step_length", 1)
        dx, dy = clamp_manhattan_with_diagonal_priority(raw_dx, raw_dy, step)
        Move(self.avatar, self.world).execute(dx, dy)

    def can_start(self, region: Region | str) -> tuple[bool, str]:
        r = resolve_query(region, self.world, expected_types=[Region]).obj
        if not r:
            return False, t("Cannot resolve region: {region}", region=region)
            
        # Sect headquarters restriction: non-members may not enter
        if isinstance(r, SectRegion):
            if self.avatar.sect is None or self.avatar.sect.id != r.sect_id:
                return False, t("[{region}] is another sect's territory, you are not a disciple of that sect", region=r.name)
        
        return True, ""

    def start(self, region: Region | str) -> Event:
        r = resolve_query(region, self.world, expected_types=[Region]).obj
        # In theory can_start already validated this, but check again for safety; do nothing if None (shouldn't happen)
        if r:
            region_name = r.name
            # Fix the target point at the start
            self._get_target_loc(r)
            content = t("{avatar} begins moving toward {region}",
                       avatar=self.avatar.name, region=region_name)
            return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])
        content = t("{avatar} attempted to move but target is invalid", avatar=self.avatar.name)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])

    def step(self, region: Region | str) -> ActionResult:
        self.execute(region=region)
        
        r = resolve_query(region, self.world, expected_types=[Region]).obj
        if not r:
             return ActionResult(status=ActionStatus.FAILED, events=[])

        target_loc = self._get_target_loc(r)
        
        # Completion condition: reach the specific random target point
        cur_loc = (self.avatar.pos_x, self.avatar.pos_y)
        done = (cur_loc == target_loc)
        
        return ActionResult(status=(ActionStatus.COMPLETED if done else ActionStatus.RUNNING), events=[])

    async def finish(self, region: Region | str) -> list[Event]:
        return []

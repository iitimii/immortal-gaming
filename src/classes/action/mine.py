from __future__ import annotations

from src.i18n import t
from src.classes.action import TimedAction
from src.classes.event import Event
from src.utils.gather import execute_gather, check_can_start_gather


class Mine(TimedAction):
    """
    Mining action: mine in a region with ore veins, lasting 6 months
    Yields the ores of the vein
    """
    
    # i18n IDs
    ACTION_NAME_ID = "mine_action_name"
    DESC_ID = "mine_description"
    REQUIREMENTS_ID = "mine_requirements"
    
    # Constants that need no translation
    EMOJI = "⛏️"
    PARAMS = {}

    duration_months = 6

    def __init__(self, avatar, world):
        super().__init__(avatar, world)
        self.gained_materials: dict[str, int] = {}

    def _execute(self) -> None:
        """
        Perform the mining action
        """
        gained = execute_gather(self.avatar, "lodes", "extra_mine_materials")
        for name, count in gained.items():
            self.gained_materials[name] = self.gained_materials.get(name, 0) + count

    def can_start(self) -> tuple[bool, str]:
        return check_can_start_gather(self.avatar, "lodes", "ore veins")

    def start(self) -> Event:
        content = t("{avatar} begins mining at {location}",
                   avatar=self.avatar.name, location=self.avatar.tile.location_name)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])

    # TimedAction already unifies the step logic

    async def finish(self) -> list[Event]:
        materials_desc = ", ".join([f"{k}x{v}" for k, v in self.gained_materials.items()])
        content = t("{avatar} finished mining, obtained: {materials}",
                   avatar=self.avatar.name, materials=materials_desc)
        return [Event(
            self.world.month_stamp,
            content,
            related_avatars=[self.avatar.id]
        )]

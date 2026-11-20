from __future__ import annotations

from src.i18n import t
from src.classes.action import TimedAction
from src.classes.event import Event
from src.utils.gather import execute_gather, check_can_start_gather
from src.classes.race import is_yao_avatar


class Harvest(TimedAction):
    """
    Harvest action: gather in a region with plants, lasting 6 months
    Yields the plants' materials
    """
    
    # i18n IDs
    ACTION_NAME_ID = "harvest_action_name"
    DESC_ID = "harvest_description"
    REQUIREMENTS_ID = "harvest_requirements"
    
    # Constants that need no translation
    EMOJI = "🌾"
    PARAMS = {}

    duration_months = 6

    def __init__(self, avatar, world):
        super().__init__(avatar, world)
        self.gained_materials: dict[str, int] = {}

    def _execute(self) -> None:
        """
        Perform the harvest action
        """
        gained = execute_gather(self.avatar, "plants", "extra_harvest_materials")
        for name, count in gained.items():
            self.gained_materials[name] = self.gained_materials.get(name, 0) + count

    def can_start(self) -> tuple[bool, str]:
        return check_can_start_gather(self.avatar, "plants", "plants")

    def start(self) -> Event:
        if is_yao_avatar(self.avatar):
            content = t("{avatar} follows wild instincts to seek spiritual herbs at {location}",
                       avatar=self.avatar.name, location=self.avatar.tile.location_name)
        else:
            content = t("{avatar} begins harvesting at {location}",
                       avatar=self.avatar.name, location=self.avatar.tile.location_name)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])

    # TimedAction already unifies the step logic

    async def finish(self) -> list[Event]:
        # Always yields something
        materials_desc = ", ".join([f"{k}x{v}" for k, v in self.gained_materials.items()])
        if is_yao_avatar(self.avatar):
            content = t("{avatar} finished foraging through the wilds, obtained: {materials}",
                       avatar=self.avatar.name, materials=materials_desc)
        else:
            content = t("{avatar} finished harvesting, obtained: {materials}",
                       avatar=self.avatar.name, materials=materials_desc)
        return [Event(
            self.world.month_stamp,
            content,
            related_avatars=[self.avatar.id]
        )]

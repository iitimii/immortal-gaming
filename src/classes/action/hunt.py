from __future__ import annotations

from src.i18n import t
from src.classes.action import TimedAction
from src.classes.event import Event
from src.utils.gather import execute_gather, check_can_start_gather
from src.classes.race import is_yao_avatar


class Hunt(TimedAction):
    """
    Hunt action: hunt in a region with animals, lasting 6 months
    Yields the animals' materials
    """
    
    # i18n IDs
    ACTION_NAME_ID = "hunt_action_name"
    DESC_ID = "hunt_description"
    REQUIREMENTS_ID = "hunt_requirements"
    
    # Constants that need no translation
    EMOJI = "🏹"
    PARAMS = {}

    duration_months = 6

    def __init__(self, avatar, world):
        super().__init__(avatar, world)
        self.gained_materials: dict[str, int] = {}

    def _execute(self) -> None:
        """
        Perform the hunt action
        """
        gained = execute_gather(self.avatar, "animals", "extra_hunt_materials")
        for name, count in gained.items():
            self.gained_materials[name] = self.gained_materials.get(name, 0) + count

    def can_start(self) -> tuple[bool, str]:
        return check_can_start_gather(self.avatar, "animals", "animals")

    def start(self) -> Event:
        if is_yao_avatar(self.avatar):
            content = t("{avatar} begins tracking prey by scent and instinct at {location}",
                       avatar=self.avatar.name, location=self.avatar.tile.location_name)
        else:
            content = t("{avatar} begins hunting at {location}",
                       avatar=self.avatar.name, location=self.avatar.tile.location_name)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])

    # TimedAction already unifies the step logic

    async def finish(self) -> list[Event]:
        # Always yields something
        materials_desc = ", ".join([f"{k}x{v}" for k, v in self.gained_materials.items()])
        if is_yao_avatar(self.avatar):
            content = t("{avatar} finished a primal hunt, obtained: {materials}",
                       avatar=self.avatar.name, materials=materials_desc)
        else:
            content = t("{avatar} finished hunting, obtained: {materials}",
                       avatar=self.avatar.name, materials=materials_desc)
        return [Event(
            self.world.month_stamp,
            content,
            related_avatars=[self.avatar.id]
        )]

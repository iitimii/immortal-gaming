from __future__ import annotations
import random
from typing import TYPE_CHECKING

from src.i18n import t
from src.classes.action.action import TimedAction
from src.classes.action_runtime import ActionStatus
from src.classes.event import Event
from src.utils.config import CONFIG

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar
    from src.classes.core.world import World

class BasePlayAction(TimedAction):
    """Base class for leisure actions."""
    duration_months = 1
    REQUIREMENTS_ID = "play_requirements"

    def __init__(self, avatar: Avatar, world: World):
        super().__init__(avatar, world)

    def _try_trigger_benefit(self) -> str:
        """Try to trigger extra benefits (breakthrough probability)."""
        prob = CONFIG.play.base_benefit_probability if hasattr(CONFIG, 'play') else 0.05
        
        if random.random() < prob:
            rate = 0.2
            self.avatar.add_breakthrough_rate(rate)
            return t("breakthrough probability increased by {val:.1%}", val=rate)
        return ""

    def _execute(self) -> None:
        pass # Concrete logic is implemented by subclasses, or only an event is recorded

    def start(self) -> Event:
        # Generic start event
        return Event(self.world.month_stamp, t("{avatar} starts {action}", avatar=self.avatar.name, action=self.get_action_name()), related_avatars=[self.avatar.id])

    async def finish(self) -> list[Event]:
        # Try to trigger benefits on settlement
        benefit_msg = self._try_trigger_benefit()
        content = t("{avatar} finished {action}.", avatar=self.avatar.name, action=self.get_action_name())
        if benefit_msg:
            content += f" {benefit_msg}"
        
        return [Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])]

# Concrete action implementations
class Reading(BasePlayAction):
    ACTION_NAME_ID = "action_reading"
    DESC_ID = "action_reading_desc"
    EMOJI = "📖"

class TeaTasting(BasePlayAction):
    ACTION_NAME_ID = "action_tea_tasting"
    DESC_ID = "action_tea_tasting_desc"
    EMOJI = "🍵"

class Traveling(BasePlayAction):
    ACTION_NAME_ID = "action_traveling"
    DESC_ID = "action_traveling_desc"
    EMOJI = "🧳"

class ZitherPlaying(BasePlayAction):
    ACTION_NAME_ID = "action_zither_playing"
    DESC_ID = "action_zither_playing_desc"
    EMOJI = "🎵"

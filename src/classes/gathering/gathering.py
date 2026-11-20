from abc import ABC, abstractmethod
from typing import List, Type, TYPE_CHECKING

from src.classes.event import Event

if TYPE_CHECKING:
    from src.classes.core.world import World
    from src.classes.core.avatar import Avatar

class Gathering(ABC):
    """
    Abstract base class for multi-avatar gathering events/scenes.
    Handles complex multi-avatar events such as "auctions", "sect competitions", "hidden domain openings".
    """
    
    # Whether major actions may be interrupted
    CAN_INTERRUPT_MAJOR: bool = False
    
    def _can_avatar_join(self, avatar: "Avatar") -> bool:
        """
        Determine whether the avatar can join this gathering.
        Combines avatar.can_join_gathering with whether the avatar is in an uninterruptible major action.
        """
        if not avatar.can_join_gathering:
            return False
            
        if not self.CAN_INTERRUPT_MAJOR and avatar.is_in_major_action:
            return False
            
        return True
    
    @abstractmethod
    def is_start(self, world: "World") -> bool:
        """
        Check whether this Gathering should start.
        Usually based on time, location or specific trigger conditions.
        """
        pass

    @abstractmethod
    def get_related_avatars(self, world: "World") -> List[int]:
        """
        Get the list of avatar IDs participating in this Gathering.
        """
        pass

    @abstractmethod
    def get_info(self, world: "World") -> str:
        """
        Get the Gathering's description.
        """
        pass

    @abstractmethod
    async def execute(self, world: "World") -> List[Event]:
        """
        Execute the Gathering's concrete logic.
        
        Notes:
        Because a Gathering is designed to settle instantly (within one step),
        no finish function is needed. All interactions and results are handled at once in execute.
        """
        pass

# Global registry for Gathering classes
GATHERING_REGISTRY: List[Type[Gathering]] = []

def register_gathering(cls: Type[Gathering]):
    """
        Decorator: register a Gathering class
    """
    GATHERING_REGISTRY.append(cls)
    return cls

class GatheringManager:
    def __init__(self):
        # Instantiate all registered Gatherings
        self.gatherings: List[Gathering] = [cls() for cls in GATHERING_REGISTRY]

    async def check_and_run_all(self, world: "World") -> List[Event]:
        """
        Check all Gatherings and execute those whose conditions are met
        """
        events = []
        for gathering in self.gatherings:
            if gathering.is_start(world):
                # Execute the Gathering logic
                gathering_events = await gathering.execute(world)
                if gathering_events:
                    events.extend(gathering_events)
        return events
from __future__ import annotations
from typing import TYPE_CHECKING, Union
from src.classes.death_reason import DeathReason

if TYPE_CHECKING:
    from src.classes.core.world import World
    from src.classes.core.avatar import Avatar

def handle_death(world: World, avatar: Avatar, reason: Union[str, DeathReason]) -> None:
    """
    Unified entry point for handling avatar death.
    Marks the avatar as dead and clears the action queue, but keeps the avatar data.
    
    Args:
        world: the world object
        avatar: the dead avatar
        reason: cause of death (DeathReason object or string)
    """
    reason_str = str(reason)
    
    # Mark as dead (soft delete)
    avatar.set_dead(reason_str, world.month_stamp)

    # Create a grave at the death coordinates. Kill-and-grab happens before handle_death, so only the remaining equipment is kept here.
    poi_manager = getattr(world, "poi_manager", None)
    if poi_manager is not None and hasattr(poi_manager, "create_grave_from_avatar"):
        poi_manager.create_grave_from_avatar(avatar, current_month=int(world.month_stamp))
    
    # Archive from the manager (hard move) and record the change
    world.avatar_manager.handle_death(avatar.id)

    # Record the deceased archive (independent of AvatarManager, unaffected by cleanup)
    world.deceased_manager.record_death(avatar)
    
    # Other logic can be triggered here, e.g. checking for heirs

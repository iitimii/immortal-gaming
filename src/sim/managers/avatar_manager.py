from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, TYPE_CHECKING, Iterable
import itertools

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

from src.classes.observe import get_observable_avatars

@dataclass
class AvatarManager:
    # Stores only living avatars, iterated by the main loop
    avatars: Dict[str, "Avatar"] = field(default_factory=dict)
    # Stores dead avatars (archive)
    dead_avatars: Dict[str, "Avatar"] = field(default_factory=dict)
    
    # --- Change buffers (not serialized) ---
    _newly_dead_buffer: List[str] = field(default_factory=list, init=False)
    _newly_born_buffer: List[str] = field(default_factory=list, init=False)
    _removed_buffer: List[str] = field(default_factory=list, init=False)

    def register_avatar(self, avatar: "Avatar", is_newly_born: bool = False) -> None:
        """
        Register an avatar with the manager.
        Args:
            avatar: the avatar object
            is_newly_born: whether the avatar is newly born (if so, it is added to the change buffer for frontend sync)
        """
        aid = str(avatar.id)
        if getattr(avatar, "is_dead", False):
            if aid in self.dead_avatars:
                return

            # Factories may detect an exhausted lifespan before registration.
            # Put the avatar under manager ownership first, then use the sole
            # death entry point so it receives a grave, archive record, and
            # client death delta just like every other death.
            self.avatars[aid] = avatar
            from src.classes.death import handle_death
            from src.classes.death_reason import DeathReason, DeathType

            death_info = getattr(avatar, "death_info", None) or {}
            reason = death_info.get("reason") or DeathReason(DeathType.OLD_AGE)
            handle_death(avatar.world, avatar, reason)
            return

        self.avatars[aid] = avatar
        if is_newly_born:
            self._newly_born_buffer.append(aid)

    def pop_newly_dead(self) -> List[str]:
        """Get and clear the IDs of avatars that died this frame"""
        res = list(self._newly_dead_buffer)
        self._newly_dead_buffer.clear()
        return res

    def pop_newly_born(self) -> List[str]:
        """Get and clear the IDs of avatars born this frame"""
        res = list(self._newly_born_buffer)
        self._newly_born_buffer.clear()
        return res

    def pop_removed(self) -> List[str]:
        """Return manually removed avatar IDs since the last client delta."""
        res = list(self._removed_buffer)
        self._removed_buffer.clear()
        return res

    def get_avatar(self, avatar_id: str) -> "Avatar | None":
        """
        Get an avatar by ID, checking the living first, then the dead
        """
        aid = str(avatar_id)
        return self.avatars.get(aid) or self.dead_avatars.get(aid)

    def handle_death(self, avatar_id: str) -> None:
        """
        Handle avatar death: move the avatar from the active list to the graveyard
        """
        aid = str(avatar_id)
        if aid in self.avatars:
            avatar = self.avatars.pop(aid)
            self.dead_avatars[aid] = avatar
            # Detach from the map so it no longer appears on the map grid
            if hasattr(avatar, "tile"):
                avatar.tile = None
            
            # Record the change
            self._newly_dead_buffer.append(aid)

    def get_avatars_in_same_region(self, avatar: "Avatar") -> List["Avatar"]:
        """
        Return other [living] avatars in the same region as the given avatar (excluding itself).
        """
        if avatar is None or getattr(avatar, "tile", None) is None or avatar.tile.region is None:
            return []
        region = avatar.tile.region
        same_region: list["Avatar"] = []
        # Iterate only the living
        for other in self.avatars.values():
            if other is avatar or getattr(other, "tile", None) is None:
                continue
            if other.tile.region == region:
                same_region.append(other)
        return same_region

    def get_living_avatars(self) -> List["Avatar"]:
        """
        Return all living avatars.
        Since avatars now only holds the living, simply return its values.
        """
        return list(self.avatars.values())

    def get_observable_avatars(self, avatar: "Avatar") -> List["Avatar"]:
        """
        Return other [living] avatars within the given avatar's interaction range (excluding itself).
        """
        return get_observable_avatars(avatar, self.avatars.values())
    
    def _iter_all_avatars(self) -> Iterable["Avatar"]:
        """Helper: iterate all avatars (living + dead)"""
        return itertools.chain(self.avatars.values(), self.dead_avatars.values())

    def cleanup_long_dead_avatars(self, current_time: "MonthStamp", threshold_years: int = 50) -> int:
        """
        Clean up avatars that have been dead for a long time.
        
        Args:
            current_time: current timestamp
            threshold_years: clean up avatars dead for more than this many years (default 50)
            
        Returns:
            Number of avatars cleaned up
        """
        if not self.dead_avatars:
            return 0
            
        to_remove = []
        for aid, avatar in self.dead_avatars.items():
            if avatar.death_info:
                death_time = avatar.death_info.get("time") # int timestamp
                if death_time is not None:
                    # Compute the time difference (MonthStamp is essentially an int: total months)
                    elapsed_months = int(current_time) - death_time
                    elapsed_years = elapsed_months // 12
                    
                    if elapsed_years >= threshold_years:
                        to_remove.append(aid)
        
        # Batch delete
        if to_remove:
            self.remove_avatars(to_remove)
            
        return len(to_remove)

    def remove_avatar(self, avatar_id: str) -> None:
        """
        Completely remove an avatar from the manager (dead or alive) and clean up all bidirectional relations involving it.
        This operation is irreversible.
        """
        aid = str(avatar_id)
        avatar = self.get_avatar(aid)
        
        if avatar is None:
            return
            
        # 1. Clean up relations it records directly
        related = list(getattr(avatar, "relations", {}).keys())
        for other in related:
            avatar.clear_relation(other)
        archived_related = list(getattr(avatar, "archived_relations", {}).keys())
        for other in archived_related:
            getattr(avatar, "archived_relations", {}).pop(other, None)
            if getattr(other, "archived_relations", None) is not None:
                other.archived_relations.pop(avatar, None)
            avatar.relation_start_dates.pop(other.id, None)
            other.relation_start_dates.pop(avatar.id, None)

        # 2. Release occupied cave dwellings
        if hasattr(avatar, "owned_regions") and avatar.owned_regions:
            for region in list(avatar.owned_regions):
                # Only remove the relationship; do not trigger any other logic
                if region.host_avatar == avatar:
                    region.host_avatar = None
            avatar.owned_regions.clear()
            
        # 3. Sweep all avatars (including the dead) to clear back-references
        for other in self._iter_all_avatars():
            if other is avatar:
                continue
            if getattr(other, "relations", None) is not None and avatar in other.relations:
                other.clear_relation(avatar)
            if getattr(other, "archived_relations", None) is not None:
                other.archived_relations.pop(avatar, None)
        
        # 4. Clean up sect relations
        if getattr(avatar, "sect", None) is not None:
            # Must call sect.remove_member to remove it from the sect's member dict
            # Note: do not call avatar.leave_sect(), since it may set avatar.sect to None,
            # while here we mainly care about clearing external (Sect object) references to the avatar.
            avatar.sect.remove_member(avatar)

        # 5. Remove itself
        self.avatars.pop(aid, None)
        self.dead_avatars.pop(aid, None)
        self._newly_born_buffer = [item for item in self._newly_born_buffer if item != aid]
        self._newly_dead_buffer = [item for item in self._newly_dead_buffer if item != aid]
        self._removed_buffer.append(aid)

    def remove_avatars(self, avatar_ids: List[str]) -> None:
        """
        Batch-delete avatars and clean up all their relations.
        """
        for aid in list(avatar_ids):
            self.remove_avatar(aid)

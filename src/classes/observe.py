from __future__ import annotations

from typing import Iterable, List, TYPE_CHECKING

from src.systems.cultivation import Realm
from src.classes.environment.tile import get_avatar_distance

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


_OBSERVATION_RADIUS_BY_REALM: dict[Realm, int] = {
    Realm.Qi_Refinement: 3,            # Qi Refinement
    Realm.Foundation_Establishment: 5, # Foundation Establishment
    Realm.Core_Formation: 7,           # Core Formation
    Realm.Nascent_Soul: 9,             # Nascent Soul
}


def get_observation_radius_by_realm(realm: Realm) -> int:
    """
    Return the perception radius by realm (based on Manhattan distance).
    """
    return _OBSERVATION_RADIUS_BY_REALM.get(realm, 2)


def get_avatar_observation_radius(avatar: "Avatar") -> int:
    """
    Get the avatar's perception radius.
    """
    base = get_observation_radius_by_realm(avatar.cultivation_progress.realm)
    extra_raw = avatar.effects.get("extra_observation_radius", 0)
    extra = int(extra_raw or 0)
    return max(1, base + extra)


def is_within_observation(initiator: "Avatar", other: "Avatar") -> bool:
    """
    Determine whether other is within the initiator's interaction range:
    Manhattan distance <= the initiator's perception radius.
    """
    return get_avatar_distance(initiator, other) <= get_avatar_observation_radius(initiator)


def get_observable_avatars(initiator: "Avatar", avatars: Iterable["Avatar"]) -> List["Avatar"]:
    """
    Filter the avatars within the initiator's interaction range from the given collection (excluding the initiator).
    Algorithm: linear scan O(N), consistent with existing manager iteration complexity.
    """
    result: list["Avatar"] = []
    for v in avatars:
        if v is initiator:
            continue
        if is_within_observation(initiator, v):
            result.append(v)
    return result



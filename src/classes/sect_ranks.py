"""
Sect rank system
Defines sect ranks and their mapping to cultivation realms
"""
from enum import Enum
from functools import total_ordering
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.systems.cultivation import Realm
    from src.classes.core.sect import Sect


@total_ordering
class SectRank(Enum):
    """
    Sect rank
    From high to low: Patriarch > Elder > Inner Disciple > Outer Disciple
    """
    Patriarch = "patriarch"      # Patriarch
    Elder = "elder"              # Elder
    InnerDisciple = "inner"      # Inner Disciple
    OuterDisciple = "outer"      # Outer Disciple
    
    def __str__(self) -> str:
        from src.i18n import t
        return t(sect_rank_msg_ids.get(self, self.value))
    
    def __lt__(self, other):
        if not isinstance(other, SectRank):
            return NotImplemented
        # A smaller number means a higher rank, so the comparison is reversed
        return RANK_ORDER[self] > RANK_ORDER[other]
    
    def __le__(self, other):
        if not isinstance(other, SectRank):
            return NotImplemented
        return RANK_ORDER[self] >= RANK_ORDER[other]
    
    def __gt__(self, other):
        if not isinstance(other, SectRank):
            return NotImplemented
        # A smaller number means a higher rank, so the comparison is reversed
        return RANK_ORDER[self] < RANK_ORDER[other]
    
    def __ge__(self, other):
        if not isinstance(other, SectRank):
            return NotImplemented
        return RANK_ORDER[self] <= RANK_ORDER[other]


# Sect rank order (smaller number = higher rank)
RANK_ORDER = {
    SectRank.Patriarch: 0,
    SectRank.Elder: 1,
    SectRank.InnerDisciple: 2,
    SectRank.OuterDisciple: 3,
}

# msgid mapping
sect_rank_msg_ids = {
    SectRank.Patriarch: "patriarch",
    SectRank.Elder: "elder",
    SectRank.InnerDisciple: "inner_disciple",
    SectRank.OuterDisciple: "outer_disciple",
}

# Default rank names (sects can override with custom names)
DEFAULT_RANK_NAMES = {
    SectRank.Patriarch: "patriarch",
    SectRank.Elder: "elder",
    SectRank.InnerDisciple: "inner_disciple",
    SectRank.OuterDisciple: "outer_disciple",
}


def get_rank_from_realm(realm: "Realm") -> SectRank:
    """
    Map a cultivation realm to a sect rank
    
    Mapping rules:
    - Qi Refinement -> Outer Disciple
    - Foundation Establishment -> Inner Disciple
    - Core Formation -> Elder
    - Nascent Soul -> Patriarch (requires an extra uniqueness check)
    
    Args:
        realm: cultivation realm
        
    Returns:
        The corresponding sect rank
    """
    from src.systems.cultivation import Realm
    
    mapping = {
        Realm.Qi_Refinement: SectRank.OuterDisciple,
        Realm.Foundation_Establishment: SectRank.InnerDisciple,
        Realm.Core_Formation: SectRank.Elder,
        Realm.Nascent_Soul: SectRank.Patriarch,
    }
    return mapping.get(realm, SectRank.OuterDisciple)


def get_rank_display_name(rank: SectRank, sect: Optional["Sect"] = None) -> str:
    """
    Get the rank's display name (sect custom names supported)
    
    Args:
        rank: sect rank
        sect: sect object (optional; if given, its custom names are used)
        
    Returns:
        The rank's display name
    """
    from src.i18n import t
    if sect is not None:
        custom_name = sect.get_rank_name(rank)
        if custom_name:
            return custom_name
    val = DEFAULT_RANK_NAMES.get(rank, "Disciple")
    return t(val)


def should_auto_promote(old_realm: "Realm", new_realm: "Realm") -> bool:
    """
    Determine whether the sect rank should be auto-promoted after a realm breakthrough
    
    Args:
        old_realm: old realm
        new_realm: new realm
        
    Returns:
        Whether to promote
    """
    if old_realm == new_realm:
        return False
    
    from src.systems.cultivation import Realm
    
    # Check whether the realm increased
    old_rank = get_rank_from_realm(old_realm)
    new_rank = get_rank_from_realm(new_realm)
    
    # Only promote if the new realm's rank is higher (in the rank enum, > means higher)
    return new_rank > old_rank


def check_and_promote_sect_rank(avatar: "Avatar", old_realm: "Realm", new_realm: "Realm") -> None:
    """
    Check whether the sect rank needs promotion after a realm breakthrough.

    In the current version, sect ranks are mainly decided by the yearly reshuffle based on "contribution + battle strength",
    so ranks no longer change at the moment of breakthrough; the interface is kept for compatibility with old call sites.
    
    Args:
        avatar: the avatar to check
        old_realm: old realm
        new_realm: new realm
    """
    return


def sect_has_patriarch(avatar: "Avatar") -> bool:
    """
    Check whether the current sect already has a patriarch (excluding oneself)
    
    Args:
        avatar: the avatar to check
        
    Returns:
        Whether there is another patriarch
    """
    if avatar.sect is None:
        return False
    
    # Look for other avatars of the same sect in the world
    for other in avatar.world.avatar_manager.avatars.values():
        if other is avatar:
            continue
        if other.sect == avatar.sect and other.sect_rank == SectRank.Patriarch:
            return True
    
    return False


"""
Tests for the sect rank system
"""
import pytest
from src.systems.cultivation import CultivationProgress, Realm
from src.classes.sect_ranks import (
    SectRank,
    get_rank_from_realm,
    get_rank_display_name,
    should_auto_promote,
)
from src.classes.core.sect import sects_by_name
from src.classes.core.world import World
from src.classes.environment.map import Map
from src.systems.time import MonthStamp
from src.sim.avatar_init import make_avatars


def test_rank_from_realm():
    """Mapping from realm to sect rank."""
    assert get_rank_from_realm(Realm.Qi_Refinement) == SectRank.OuterDisciple
    assert get_rank_from_realm(Realm.Foundation_Establishment) == SectRank.InnerDisciple
    assert get_rank_from_realm(Realm.Core_Formation) == SectRank.Elder
    assert get_rank_from_realm(Realm.Nascent_Soul) == SectRank.Patriarch


def test_rank_display_name():
    """Rank display names."""
    assert get_rank_display_name(SectRank.Patriarch) == "Patriarch"
    assert get_rank_display_name(SectRank.Elder) == "Elder"
    assert get_rank_display_name(SectRank.InnerDisciple) == "Inner Disciple"
    assert get_rank_display_name(SectRank.OuterDisciple) == "Outer Disciple"


def test_rank_comparison():
    """Rank comparison."""
    assert SectRank.Patriarch > SectRank.Elder
    assert SectRank.Elder > SectRank.InnerDisciple
    assert SectRank.InnerDisciple > SectRank.OuterDisciple
    assert SectRank.OuterDisciple < SectRank.Patriarch


def test_auto_promote():
    """Auto-promotion logic."""
    assert should_auto_promote(Realm.Qi_Refinement, Realm.Foundation_Establishment) == True
    assert should_auto_promote(Realm.Foundation_Establishment, Realm.Core_Formation) == True
    assert should_auto_promote(Realm.Core_Formation, Realm.Nascent_Soul) == True
    assert should_auto_promote(Realm.Qi_Refinement, Realm.Qi_Refinement) == False



def test_avatar_sect_rank_assignment(base_world):
    """Sect rank assignment when avatars are created."""
    # Uses the base_world fixture; load_cultivation_world_map is not needed
    
    # Create several avatars
    avatars_dict = make_avatars(base_world, count=20, current_month_stamp=MonthStamp(100 * 12))
    avatars = list(avatars_dict.values())
    
    # Every avatar with a sect must have a rank
    for avatar in avatars:
        if avatar.sect is not None:
            assert avatar.sect_rank is not None, f"{avatar.name} has a sect but no rank"
            # The rank should match the realm
            expected_rank = get_rank_from_realm(avatar.cultivation_progress.realm)
            # The only allowed mismatch is a Nascent Soul cultivator demoted to Elder (patriarch uniqueness)
            if avatar.sect_rank != expected_rank:
                assert avatar.cultivation_progress.realm == Realm.Nascent_Soul
                assert avatar.sect_rank == SectRank.Elder
        else:
            assert avatar.sect_rank is None, f"{avatar.name} is a rogue cultivator and should have no rank"


def test_patriarch_uniqueness(base_world):
    """Each sect has at most one patriarch."""
    
    # Create enough avatars
    avatars_dict = make_avatars(base_world, count=50, current_month_stamp=MonthStamp(100 * 12))
    avatars = list(avatars_dict.values())
    
    # Count patriarchs per sect
    sect_patriarchs = {}
    for avatar in avatars:
        if avatar.sect is not None and avatar.sect_rank == SectRank.Patriarch:
            sect_id = avatar.sect.id
            if sect_id not in sect_patriarchs:
                sect_patriarchs[sect_id] = []
            sect_patriarchs[sect_id].append(avatar.name)
    
    # Ensure each sect has at most one patriarch
    for sect_id, patriarchs in sect_patriarchs.items():
        assert len(patriarchs) <= 1, f"Sect {sect_id} has multiple patriarchs: {patriarchs}"


def test_sect_str_display(base_world):
    """Sect info display."""
    
    avatars_dict = make_avatars(base_world, count=20, current_month_stamp=MonthStamp(100 * 12))
    avatars = list(avatars_dict.values())
    
    for avatar in avatars:
        sect_str = avatar.get_sect_str()
        if avatar.sect is None:
            assert sect_str == "Rogue Cultivator"
        else:
            # Should contain the sect name
            assert avatar.sect.name in sect_str
            # Should contain the rank name
            if avatar.sect_rank is not None:
                rank_name = get_rank_display_name(avatar.sect_rank, avatar.sect)
                assert rank_name in sect_str


def test_cultivation_breakthrough_promotion(base_world):
    """Automatic promotion after a realm breakthrough."""
    
    avatars_dict = make_avatars(base_world, count=10, current_month_stamp=MonthStamp(100 * 12))
    avatars = list(avatars_dict.values())
    
    # Find a Qi Refinement sect disciple
    target_avatar = None
    for avatar in avatars:
        if avatar.sect is not None and avatar.cultivation_progress.realm == Realm.Qi_Refinement:
            target_avatar = avatar
            break
    
    if target_avatar is not None:
        # Record the original rank
        old_rank = target_avatar.sect_rank
        assert old_rank == SectRank.OuterDisciple
        
        # Break through to Foundation Establishment
        target_avatar.cultivation_progress.level = 31  # Foundation Establishment early stage
        target_avatar.update_cultivation(31)
        
        # Check that the rank was promoted
        assert target_avatar.sect_rank == SectRank.InnerDisciple
        assert target_avatar.sect_rank > old_rank



if __name__ == "__main__":
    pytest.main([__file__, "-v"])


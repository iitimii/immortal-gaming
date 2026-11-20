import pytest
from src.systems.cultivation import CultivationProgress, Realm, Stage, REALM_ORDER, LEVELS_PER_REALM

def test_breakthrough_normal(dummy_avatar):
    """
    Normal breakthrough: from peak Qi Refinement to early Foundation Establishment.
    """
    # Peak Qi Refinement is level 30 (LEVELS_PER_REALM * 1)
    qi_max_level = 30
    
    # Set the avatar state
    cp = CultivationProgress(level=qi_max_level, exp=0)
    dummy_avatar.cultivation_progress = cp
    
    # Verify the current state
    assert cp.realm == Realm.Qi_Refinement
    assert cp.is_in_bottleneck() is True
    assert cp.can_break_through() is True
    
    # Break through
    cp.break_through()
    
    # Verify the post-breakthrough state
    # Should advance to level 31
    assert cp.level == 31
    # Realm should be Foundation Establishment
    assert cp.realm == Realm.Foundation_Establishment
    # Stage should be Early Stage
    assert cp.stage == Stage.Early_Stage
    # No longer in a bottleneck
    assert cp.is_in_bottleneck() is False

def test_breakthrough_max_realm_limit(dummy_avatar):
    """
    Max realm limit: peak Nascent Soul (currently the highest level) cannot break through.
    """
    # Compute the maximum level
    # There are currently 4 realms of 30 levels each, so the max is 120
    max_level = len(REALM_ORDER) * LEVELS_PER_REALM
    
    # Put the avatar at the maximum level
    cp = CultivationProgress(level=max_level, exp=0)
    dummy_avatar.cultivation_progress = cp
    
    # Verify the current state
    assert cp.realm == Realm.Nascent_Soul
    # 30/60/90/120 are all 0 mod 30, so is_in_bottleneck returns True
    assert cp.is_in_bottleneck() is True
    
    # Key check: can_break_through must return False because the cap is reached
    assert cp.can_break_through() is False

def test_not_in_bottleneck(dummy_avatar):
    """
    Cannot break through outside a bottleneck.
    """
    # Pick an intermediate level, e.g. 15 (middle Qi Refinement)
    cp = CultivationProgress(level=15, exp=0)
    dummy_avatar.cultivation_progress = cp
    
    assert cp.is_in_bottleneck() is False
    assert cp.can_break_through() is False

def test_breakthrough_intermediate_bottleneck(dummy_avatar):
    """
    Intermediate breakthrough: peak Foundation Establishment -> Core Formation.
    """
    # Peak Foundation Establishment is level 60
    foundation_max_level = 60
    
    cp = CultivationProgress(level=foundation_max_level, exp=0)
    dummy_avatar.cultivation_progress = cp
    
    assert cp.realm == Realm.Foundation_Establishment
    assert cp.can_break_through() is True
    
    cp.break_through()
    
    assert cp.level == 61
    assert cp.realm == Realm.Core_Formation
    assert cp.stage == Stage.Early_Stage

import pytest
import random
from unittest.mock import MagicMock, patch
from src.classes.action.meditate import Meditate
from src.classes.action.educate import Educate
from src.classes.environment.region import CityRegion, CultivateRegion, Region
from src.classes.environment.tile import TileType, Tile
from src.classes.core.avatar import Avatar
from src.systems.cultivation import Realm, CultivationProgress

# --- Meditate tests ---

def test_meditate_can_start(dummy_avatar):
    # 1. By default (rogue cultivator) meditation is unavailable (legal_actions is empty and lacks Meditate)
    # Note: per meditate.py, the "Meditate" permission must be granted explicitly
    can, reason = Meditate(dummy_avatar, dummy_avatar.world).can_start()
    assert can is False
    assert "does not support Zen Meditation" in reason

    # 2. Grant the Buddhist permission
    # dummy_avatar.effects is read-only, so add a temporary effect
    dummy_avatar.temporary_effects.append({
        "source": "test_buff",
        "effects": {
            "legal_actions": ["Meditate"]
        },
        "start_month": int(dummy_avatar.world.month_stamp),
        "duration": 10
    })
    
    can, reason = Meditate(dummy_avatar, dummy_avatar.world).can_start()
    assert can is True

    # 3. Bottleneck state
    dummy_avatar.cultivation_progress.level = 30 # Qi Refinement peak bottleneck
    can, reason = Meditate(dummy_avatar, dummy_avatar.world).can_start()
    assert can is False
    assert "bottleneck" in reason

def test_meditate_execution_normal(dummy_avatar):
    """Test a normal meditation (no epiphany)."""
    dummy_avatar.temporary_effects.append({
        "source": "test_buff",
        "effects": {
            "legal_actions": ["Meditate"]
        },
        "start_month": int(dummy_avatar.world.month_stamp),
        "duration": 10
    })
    
    action = Meditate(dummy_avatar, dummy_avatar.world)
    
    # Mock the random number so no epiphany triggers (prob < 0.1, random > 0.1)
    # BASE_PROB = 0.1
    random.seed(42) 
    # random.random() -> 0.639... > 0.1 -> normal meditation
    
    initial_exp = dummy_avatar.cultivation_progress.exp
    action._execute()
    
    # Qi Refinement multiplier = 1
    # Normal EXP BASE_EXP = 10
    expected_gain = 10 * 1 
    assert dummy_avatar.cultivation_progress.exp == initial_exp + expected_gain
    assert action._last_is_epiphany is False

def test_meditate_execution_epiphany(dummy_avatar):
    """Test a meditation epiphany."""
    # dummy_avatar.effects is read-only, so add a temporary effect
    dummy_avatar.temporary_effects.append({
        "source": "test_buff",
        "effects": {
            "legal_actions": ["Meditate"],
            "extra_meditate_prob": 1.0 # Force an epiphany with a huge probability
        },
        "start_month": int(dummy_avatar.world.month_stamp),
        "duration": 10
    })
    
    action = Meditate(dummy_avatar, dummy_avatar.world)
    
    # Mock add_exp so level-up consumption does not skew the numbers
    dummy_avatar.cultivation_progress.add_exp = MagicMock()
    
    action._execute()
    
    # Qi Refinement multiplier = 1 (REALM_RANK.get(Qi_Refinement, 0) + 1 = 1)
    # Epiphany EXP EPIPHANY_EXP = 1500
    # Extra bonus multiplier = 0
    # exp = 1500 * 1 * (1 + 0) = 1500
    expected_gain = 1500 * 1
    
    dummy_avatar.cultivation_progress.add_exp.assert_called_with(expected_gain)
    assert action._last_is_epiphany is True

def test_meditate_realm_bonus(dummy_avatar):
    """Test the realm bonus."""
    # Raise to Foundation Establishment
    # Note: changing realm alone may not be enough since REALM_RANK may depend on other state
    # also make sure REALM_RANK.get(realm) is correct
    dummy_avatar.cultivation_progress.realm = Realm.Foundation_Establishment
    # Foundation Establishment rank index = 1 -> multiplier = 2
    
    dummy_avatar.temporary_effects.append({
        "source": "test_buff",
        "effects": {
            "legal_actions": ["Meditate"],
            "extra_meditate_prob": -1.0 # Cancel the probability to force a normal meditation
        },
        "start_month": int(dummy_avatar.world.month_stamp),
        "duration": 10
    })
    
    action = Meditate(dummy_avatar, dummy_avatar.world)
    
    # Mock add_exp
    dummy_avatar.cultivation_progress.add_exp = MagicMock()
    
    action._execute()
    
    # 10 * 2 = 20
    dummy_avatar.cultivation_progress.add_exp.assert_called_with(20)

# --- Educate tests ---

def test_educate_can_start(avatar_in_city):
    # avatar_in_city is already in a CityRegion
    
    # 1. No permission
    can, reason = Educate(avatar_in_city, avatar_in_city.world).can_start()
    assert can is False
    assert "does not support Confucian Education" in reason
    
    # 2. Grant the Confucian permission (via temporary_effects)
    avatar_in_city.temporary_effects.append({
        "source": "test_buff",
        "effects": {
            "legal_actions": ["Educate"]
        },
        "start_month": int(avatar_in_city.world.month_stamp),
        "duration": 10
    })
    # Force attribute recalculation
    avatar_in_city.recalc_effects()
    
    can, reason = Educate(avatar_in_city, avatar_in_city.world).can_start()
    assert can is True
    
    # 3. Move to the wilderness (NormalRegion)
    avatar_in_city.tile.region = CultivateRegion(id=99, name="Cave", desc="Cave")
    can, reason = Educate(avatar_in_city, avatar_in_city.world).can_start()
    assert can is False
    assert "Must be in a City" in reason

def test_educate_execution(avatar_in_city):
    """Test Educate EXP calculation (a half-full city gives the standard multiplier)."""
    # Same as above, using temporary_effects
    avatar_in_city.temporary_effects.append({
        "source": "test_buff",
        "effects": {
            "legal_actions": ["Educate"]
        },
        "start_month": int(avatar_in_city.world.month_stamp),
        "duration": 10
    })
    # Force attribute recalculation
    avatar_in_city.recalc_effects()
    
    region = avatar_in_city.tile.region
    region.population = 50.0
    region.population_capacity = 100.0
    
    action = Educate(avatar_in_city, avatar_in_city.world)
    
    # Mock add_exp
    avatar_in_city.cultivation_progress.add_exp = MagicMock()
    
    # Fix the random number so population changes do not interfere (this mainly tests EXP)
    random.seed(1)
    
    action._execute()
    
    # Qi Refinement multiplier = 1
    # Population multiplier = 0.5 + 50/100 = 1.0
    # Base EXP BASE_EXP_TOTAL = 150
    # 150 * 1 * 1 = 150
    # avatar_in_city.cultivation_progress.add_exp.assert_called_with(150)
    
    dummy_avatar = avatar_in_city
    dummy_avatar.cultivation_progress.add_exp.assert_called()
    args, _ = dummy_avatar.cultivation_progress.add_exp.call_args
    # Allow some tolerance, or first assert the call happened
    assert args[0] == 150

def test_educate_population_effect(avatar_in_city):
    """Test the effect of Educate on population."""
    avatar_in_city.temporary_effects.append({
        "source": "test_buff",
        "effects": {
            "legal_actions": ["Educate"]
        },
        "start_month": int(avatar_in_city.world.month_stamp),
        "duration": 10
    })
    # Force attribute recalculation
    avatar_in_city.recalc_effects()
    
    region = avatar_in_city.tile.region
    region.population = 50.0
    region.population_capacity = 100.0
    
    action = Educate(avatar_in_city, avatar_in_city.world)
    
    # Force a trigger
    # Use patch to override random.random inside action._execute
    # Note: since the action module imports random itself, usually patch 'src.classes.action.educate.random.random'
    # or patch 'random.random' directly when it does a plain import random
    with patch('src.classes.action.educate.random.random', return_value=0.1):
        action._execute()
        
    assert region.population == pytest.approx(50.2)

def test_educate_high_population_bonus(avatar_in_city):
    """Test the Educate bonus in a high-population city."""
    avatar_in_city.temporary_effects.append({
        "source": "test_buff",
        "effects": {
            "legal_actions": ["Educate"]
        },
        "start_month": int(avatar_in_city.world.month_stamp),
        "duration": 10
    })
    # Force attribute recalculation
    avatar_in_city.recalc_effects()
    
    region = avatar_in_city.tile.region
    region.population = 100.0
    region.population_capacity = 100.0
    
    action = Educate(avatar_in_city, avatar_in_city.world)
    
    # Mock add_exp
    avatar_in_city.cultivation_progress.add_exp = MagicMock()
    
    action._execute()
    
    # Full city multiplier = 0.5 + 100/100 = 1.5
    expected = 150 * 1 * 1.5
    # avatar_in_city.cultivation_progress.add_exp.assert_called_with(int(expected))
    
    dummy_avatar = avatar_in_city
    dummy_avatar.cultivation_progress.add_exp.assert_called()
    args, _ = dummy_avatar.cultivation_progress.add_exp.call_args
    assert args[0] == int(expected)

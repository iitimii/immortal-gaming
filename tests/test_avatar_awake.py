import pytest
import random
from unittest.mock import MagicMock, patch
from src.classes.core.world import World
from src.classes.mortal import Mortal
from src.classes.core.avatar import Avatar, Gender
from src.systems.time import MonthStamp
from src.classes.relation.relation import Relation
from src.sim.avatar_awake import (
    _process_bloodline_awakening,
    _process_wild_awakening,
    _register_avatar_and_resolve_lifespan,
    process_awakening,
)
from src.utils.config import CONFIG
from src.classes.race import get_race

@pytest.fixture
def mock_world(base_world):
    return base_world

def test_process_bloodline_awakening(mock_world):
    """Test bloodline awakening logic."""
    # 1. Prepare a mortal
    mortal = Mortal(
        id="m1", 
        name="Test Mortal", 
        gender=Gender.MALE, 
        race=get_race("fox"),
        birth_month_stamp=MonthStamp(0), # old enough
        parents=[]
    )
    mock_world.mortal_manager.register_mortal(mortal)
    
    # 2. Set the time so the age requirement (>= 16) is met
    mock_world.month_stamp = MonthStamp(20 * 12) # age 20
    
    # 3. Force the awakening roll to hit
    with patch("random.random", return_value=0.0): # < 0.05
        events = _process_bloodline_awakening(mock_world)
        
    # 4. Verify
    assert len(events) == 1
    assert "awakened" in events[0].content
    
    # The mortal should be removed
    assert mock_world.mortal_manager.get_mortal("m1") is None
    
    # The avatar should be registered (ID reused)
    avatar = mock_world.avatar_manager.get_avatar("m1")
    assert avatar is not None
    assert avatar.name == "Test Mortal"
    assert avatar.race.id == "fox"
    assert avatar.cultivation_progress.level == 1 # Qi Refinement level 1

def test_process_bloodline_awakening_age_limit(mock_world):
    """A mortal past the awakening age limit cannot awaken."""
    mortal = Mortal(
        id="m1", name="Old Mortal", gender=Gender.MALE, 
        birth_month_stamp=MonthStamp(0), parents=[]
    )
    mock_world.mortal_manager.register_mortal(mortal)
    
    # Set age to 80 (> 60)
    mock_world.month_stamp = MonthStamp(80 * 12)
    
    with patch("random.random", return_value=0.0):
        events = _process_bloodline_awakening(mock_world)
        
    assert len(events) == 0
    assert mock_world.mortal_manager.get_mortal("m1") is not None # still present, waiting to die of old age
    assert mock_world.avatar_manager.get_avatar("m1") is None

def test_process_wild_awakening(mock_world):
    """Test wild awakening logic."""
    # Note: process_awakening in simulator.py calls this;
    # here we test _process_wild_awakening directly
    
    with patch("src.sim.avatar_awake.roll_avatar_race", return_value=get_race("snake")):
        event = _process_wild_awakening(mock_world)
    
    assert event is not None
    assert "rogue cultivator" in event.content
    
    # Verify an avatar was created
    # The ID is random, so look it up via pop_newly_born
    new_ids = mock_world.avatar_manager.pop_newly_born()
    assert len(new_ids) == 1
    
    avatar = mock_world.avatar_manager.get_avatar(new_ids[0])
    assert avatar is not None
    assert avatar.sect is None # rogue cultivator
    assert avatar.race.id == "snake"


def test_lifespan_exhausted_awakening_creates_grave(mock_world, dummy_avatar):
    dummy_avatar.age.max_lifespan = dummy_avatar.age.age

    _register_avatar_and_resolve_lifespan(mock_world, dummy_avatar)

    assert dummy_avatar.id not in mock_world.avatar_manager.avatars
    assert dummy_avatar.id in mock_world.avatar_manager.dead_avatars
    assert mock_world.deceased_manager.get_record(dummy_avatar.id) is not None
    graves = mock_world.poi_manager.get_all_active(int(mock_world.month_stamp))
    assert len(graves) == 1
    assert graves[0].deceased_avatar_id == dummy_avatar.id

def test_awakening_integration(mock_world):
    """Test the process_awakening integration call."""
    # Trigger both bloodline and wild awakening
    mortal = Mortal(id="m1", name="M", gender=Gender.MALE, birth_month_stamp=MonthStamp(0), parents=[])
    mock_world.mortal_manager.register_mortal(mortal)
    mock_world.month_stamp = MonthStamp(20 * 12)
    
    # Patch random to always return 0 (hit both probabilities)
    with patch("random.random", return_value=0.0):
        events = process_awakening(mock_world)
        
    # There should be 2 events (1 bloodline + 1 wild)
    assert len(events) == 2
    
    # Verify results
    assert mock_world.avatar_manager.get_avatar("m1") is not None
    assert len(mock_world.avatar_manager.pop_newly_born()) == 2 # m1 + wild

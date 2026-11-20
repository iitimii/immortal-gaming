import pytest
from src.classes.core.avatar import Avatar, Gender
from src.classes.age import Age
from src.systems.cultivation import Realm, CultivationProgress
from src.utils.id_generator import get_avatar_id
from src.classes.root import Root
from src.sim.simulator_engine.phases.lifecycle import phase_update_age_and_birth
from src.systems.time import create_month_stamp, Year, Month

def test_register_avatar_buffer(base_world):
    """Test the buffer logic when registering new avatars."""
    manager = base_world.avatar_manager
    
    # 1. Register a regular avatar (not newborn, e.g. from a loaded save)
    a1 = Avatar(
        world=base_world,
        name="OldGuy",
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(100), Month.JANUARY),
        age=Age(20, Realm.Qi_Refinement),
        gender=Gender.MALE
    )
    manager.register_avatar(a1, is_newly_born=False)
    
    assert a1.id in manager.avatars
    assert len(manager.pop_newly_born()) == 0
    
    # 2. Register a newborn avatar
    a2 = Avatar(
        world=base_world,
        name="Baby",
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(200), Month.JANUARY),
        age=Age(1, Realm.Qi_Refinement),
        gender=Gender.FEMALE
    )
    manager.register_avatar(a2, is_newly_born=True)
    
    assert a2.id in manager.avatars
    newly_born = manager.pop_newly_born()
    assert len(newly_born) == 1
    assert str(a2.id) in newly_born
    
    # 3. Fetching again should return nothing
    assert len(manager.pop_newly_born()) == 0

@pytest.mark.asyncio
async def test_simulator_birth_logic(base_world):
    """Test the childbirth logic integration in the simulator."""
    from src.sim.simulator import Simulator
    from unittest.mock import patch
    from src.classes.core.avatar import Avatar
    from src.classes.age import Age
    from src.systems.cultivation import Realm, CultivationProgress
    from src.classes.event import Event
    
    # Build a simple mocked return value
    mock_avatar = Avatar(
        world=base_world,
        name="MockBaby",
        id="mock_id_123",
        birth_month_stamp=base_world.month_stamp,
        age=Age(1, Realm.Qi_Refinement),
        gender=Gender.MALE
    )
    
    sim = Simulator(base_world)
    # sim.awakening_rate no longer controls this directly; process_awakening reads the config internally
    # Patch process_awakening directly to simulate a hit
    
    def mock_process_awakening(world):
        # Simulate the internal behaviour: register the avatar and return an event
        world.avatar_manager.register_avatar(mock_avatar, is_newly_born=True)
        return [Event(world.month_stamp, f"{mock_avatar.name} awakened", related_avatars=[mock_avatar.id])]

    # Patch process_awakening
    with patch('src.sim.simulator_engine.phases.lifecycle.process_awakening', side_effect=mock_process_awakening):
        # Run one update
        living_avatars = base_world.avatar_manager.get_living_avatars()
        events = phase_update_age_and_birth(base_world, living_avatars)
    
    # Verify a new avatar was produced
    newly_born = base_world.avatar_manager.pop_newly_born()
    assert len(newly_born) == 1
    assert newly_born[0] == mock_avatar.id
    
    # Verify the new avatar is in the manager
    avatar = base_world.avatar_manager.get_avatar(mock_avatar.id)
    assert avatar is mock_avatar
    assert mock_avatar.name in events[0].content # make sure the event was generated too

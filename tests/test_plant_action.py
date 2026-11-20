import pytest
from src.classes.action.registry import ActionRegistry
from src.classes.action.plant import Plant
from src.systems.cultivation import Realm
from src.classes.environment.region import NormalRegion

def test_plant_action_registered():
    """Verify the Plant action is registered."""
    assert "Plant" in [cls.__name__ for cls in ActionRegistry.all()]

@pytest.mark.asyncio
async def test_plant_action_execution(dummy_avatar, base_world):
    """Verify the Plant action execution logic."""
    # Simulate being in a normal region
    from unittest.mock import MagicMock
    dummy_avatar.tile.region = MagicMock(spec=NormalRegion)
    dummy_avatar.cultivation_progress.realm = Realm.Qi_Refinement
    dummy_avatar.magic_stone = 0
    
    # Base yield without personas
    action = Plant(dummy_avatar, base_world)
    can_start, msg = action.can_start()
    assert can_start is True
    
    action._execute()
    assert dummy_avatar.magic_stone == 100
    assert action.gained_stones == 100

@pytest.mark.asyncio
async def test_plant_action_with_effect(dummy_avatar, base_world):
    """Verify the Plant action with a bonus-yield persona."""
    from unittest.mock import MagicMock
    dummy_avatar.tile.region = MagicMock(spec=NormalRegion)
    dummy_avatar.cultivation_progress.realm = Realm.Foundation_Establishment
    dummy_avatar.magic_stone = 0
    
    # Simulate the FARMER persona effect
    dummy_avatar.temporary_effects.append({
        "source": "test",
        "start_month": 0,
        "duration": 100,
        "effects": {"extra_plant_income": 50}
    })
    
    action = Plant(dummy_avatar, base_world)
    action._execute()
    # Foundation Establishment 200 + persona 50 = 250
    assert dummy_avatar.magic_stone == 250


import pytest
from unittest.mock import MagicMock, patch
from src.classes.action.refine import Refine
from src.classes.action.cast import Cast
from src.systems.cultivation import Realm
from src.classes.material import Material

# -----------------------------------------------------------------------------
# Refine (alchemy) Tests
# -----------------------------------------------------------------------------

def test_refine_can_start_params(dummy_avatar):
    """Parameter parsing for the Refine action."""
    action = Refine(dummy_avatar, dummy_avatar.world)
    
    # 1. Missing parameter
    can, reason = action.can_start("")
    assert not can
    assert "not specified" in reason

    # 2. Invalid parameter
    can, reason = action.can_start("INVALID_REALM_XYZ")
    assert not can
    assert "Invalid realm" in reason

    # 3. Valid parameter - enum value string (the format the prompt asks for)
    # Give the avatar some materials first, otherwise it reports insufficient materials
    mat = Material(id=1, name="TestMat", realm=Realm.Qi_Refinement, desc="desc")
    dummy_avatar.materials[mat] = 100
    
    can, reason = action.can_start("QI_REFINEMENT")
    assert can, f"Should accept enum value string. Reason: {reason}"

    # 4. Valid parameter - enum name string
    can, reason = action.can_start("Qi_Refinement")
    assert can, f"Should accept enum name string. Reason: {reason}"

    # 5. Valid parameter - Realm object
    can, reason = action.can_start(Realm.Qi_Refinement)
    assert can, f"Should accept Realm object. Reason: {reason}"

    # 6. Display-name parameter (expected to fail: resolution only accepts enum names/values)
    # Note: update this test if resolution.py changes
    can, reason = action.can_start("Qi Refinement Realm")
    assert not can
    assert "Invalid realm" in reason

def test_refine_materials_check(dummy_avatar):
    """Material check logic for Refine."""
    action = Refine(dummy_avatar, dummy_avatar.world)
    target_realm = Realm.Qi_Refinement
    cost = action.COST # 3

    # Clear materials
    dummy_avatar.materials = {}
    
    # 1. Insufficient materials
    can, reason = action.can_start(target_realm)
    assert not can
    assert "Insufficient materials" in reason

    # 2. Enough materials (same realm)
    mat = Material(id=1, name="TestMat", realm=target_realm, desc="desc")
    dummy_avatar.materials[mat] = cost
    can, reason = action.can_start(target_realm)
    assert can

    # 3. Enough materials (mixed materials, total is enough)
    dummy_avatar.materials = {}
    mat1 = Material(id=1, name="Mat1", realm=target_realm, desc="desc")
    mat2 = Material(id=2, name="Mat2", realm=target_realm, desc="desc")
    dummy_avatar.materials[mat1] = 1
    dummy_avatar.materials[mat2] = cost # Total > cost
    can, reason = action.can_start(target_realm)
    assert can

    # 4. Only higher-tier materials (must not count toward lower-tier refining)
    dummy_avatar.materials = {}
    high_mat = Material(id=3, name="HighMat", realm=Realm.Foundation_Establishment, desc="desc")
    dummy_avatar.materials[high_mat] = 10
    can, reason = action.can_start(target_realm)
    assert not can

@pytest.mark.asyncio
async def test_refine_execution_flow(dummy_avatar):
    """Refine execution flow: consume materials -> success/failure -> output."""
    action = Refine(dummy_avatar, dummy_avatar.world)
    target_realm = Realm.Qi_Refinement
    cost = action.COST

    # Prepare materials
    mat = Material(id=1, name="TestMat", realm=target_realm, desc="desc")
    dummy_avatar.materials[mat] = cost + 2 # a little extra

    # Start
    event = action.start(target_realm)
    assert event is not None
    assert action.target_realm == target_realm
    
    # Verify materials were consumed
    assert dummy_avatar.materials[mat] == 2

    # Mock the success rate (100% success)
    # Refine.SUCCESS_RATES[Realm.Qi_Refinement] = 0.6
    # We mock random.random to control the outcome
    
    # Case A: Success
    with patch("random.random", return_value=0.0): # 0.0 < success_rate
        with patch("src.classes.action.refine.get_random_elixir_by_realm") as mock_get_elixir:
            with patch("src.classes.action.refine.resolve_item_exchange", new_callable=MagicMock) as mock_exchange:
                with patch("src.classes.story_event_service.StoryEventService.should_trigger", return_value=False):
                # Setup mock return
                    mock_elixir = MagicMock()
                    mock_elixir.name = "Godly Pill"
                    mock_get_elixir.return_value = mock_elixir
                
                    async def async_return(*args, **kwargs):
                        return MagicMock(result_text="Exchange Result")
                    mock_exchange.side_effect = async_return
                
                    events = await action.finish()
                
                    assert len(events) == 2 # 1 success event + 1 exchange event
                    assert "successfully" in events[0].content
                    mock_get_elixir.assert_called_once_with(target_realm)
                    mock_exchange.assert_called_once()

    # Case B: Fail
    action.target_realm = target_realm # Reset
    with patch("random.random", return_value=0.99): # 0.99 > success_rate
         events = await action.finish()
         assert len(events) == 1
         assert "failed" in events[0].content


# -----------------------------------------------------------------------------
# Cast (forging) Tests
# -----------------------------------------------------------------------------

def test_cast_can_start_params(dummy_avatar):
    """Parameter parsing for the Cast action."""
    action = Cast(dummy_avatar, dummy_avatar.world)
    
    # Basic parameter test
    can, reason = action.can_start("QI_REFINEMENT")
    # Need materials
    mat = Material(id=1, name="TestMat", realm=Realm.Qi_Refinement, desc="desc")
    dummy_avatar.materials[mat] = 100
    
    can, reason = action.can_start("QI_REFINEMENT")
    assert can
    
    can, reason = action.can_start("INVALID")
    assert not can

def test_cast_materials_check(dummy_avatar):
    """Material cost for Cast (COST=5)."""
    action = Cast(dummy_avatar, dummy_avatar.world)
    target_realm = Realm.Qi_Refinement
    cost = action.COST # 5

    dummy_avatar.materials = {}
    
    # 1. Not enough
    mat = Material(id=1, name="TestMat", realm=target_realm, desc="desc")
    dummy_avatar.materials[mat] = cost - 1
    can, reason = action.can_start(target_realm)
    assert not can
    
    # 2. Enough
    dummy_avatar.materials[mat] = cost
    can, reason = action.can_start(target_realm)
    assert can

@pytest.mark.asyncio
async def test_cast_execution_flow(dummy_avatar):
    """Cast execution flow."""
    action = Cast(dummy_avatar, dummy_avatar.world)
    target_realm = Realm.Qi_Refinement
    cost = action.COST

    mat = Material(id=1, name="TestMat", realm=target_realm, desc="desc")
    dummy_avatar.materials[mat] = cost
    
    action.start(target_realm)
    assert dummy_avatar.materials.get(mat, 0) == 0

    # Test Success (Weapon)
    with patch("random.random", side_effect=[0.0, 0.0]): # First: check success, Second: check is_weapon (<0.5)
        with patch("src.classes.action.cast.get_random_weapon_by_realm") as mock_get_weapon:
            with patch("src.classes.action.cast.resolve_item_exchange") as mock_exchange:
                with patch("src.classes.story_event_service.StoryEventService.should_trigger", return_value=False):
                    mock_weapon = MagicMock()
                    mock_weapon.name = "Godly Sword"
                    mock_get_weapon.return_value = mock_weapon
                
                    async def async_return(*args, **kwargs):
                        return MagicMock(result_text="Exchange Result")
                    mock_exchange.side_effect = async_return
                
                    events = await action.finish()
                
                    assert len(events) == 2
                    assert "successfully" in events[0].content
                    # Should be a weapon
                    assert "weapon" in events[0].content


import pytest
from unittest.mock import patch, MagicMock
from src.classes.mutual_action.gift import Gift
from src.classes.action_runtime import ActionResult, ActionStatus
from src.classes.core.avatar import Avatar, Gender
from src.classes.age import Age
from src.systems.cultivation import Realm
from src.classes.relation.relation import Relation
from src.utils.id_generator import get_avatar_id
from src.systems.time import create_month_stamp, Year, Month

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def target_avatar(base_world):
    """Create a second avatar to receive gifts."""
    av = Avatar(
        world=base_world,
        name="TargetNPC",
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
        age=Age(20, Realm.Qi_Refinement),
        gender=Gender.FEMALE,
        pos_x=0,
        pos_y=0,
        personas=[],  # Explicitly clear personas so random ones do not affect price tests
    )
    # Force an effect recalculation so attributes are clean
    av.recalc_effects()
    return av

@pytest.fixture
def gift_action(dummy_avatar, base_world):
    """Initialize the Gift action."""
    # Mock _call_llm_response so step() does not call asyncio.get_running_loop()
    with patch.object(Gift, '_call_llm_response', new_callable=MagicMock) as mock_llm:
         # Return a mock task so task.done() is initially False,
         # but here the main goal is just to keep step() from failing
         mock_llm.return_value = {} 
         
         action = Gift(dummy_avatar, base_world)
         
         # We mock out the async task creation inside step(),
         # because what we mainly test is:
         # 1. Parameters are parsed correctly (step -> _resolve_gift)
         # 2. _can_start logic
         # 3. Response settlement logic _settle_response / _apply_gift
         
         # But step() itself does:
         # 1. Parse parameters
         # 2. Check the target
         # 3. Create a task (this would fail here)
         
         # Patching asyncio.get_running_loop is the simpler approach
         yield action

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

class TestGiftAction:

    # --- 1. Gifting spirit stones ---

    def test_gift_spirit_stone_success(self, gift_action, dummy_avatar, target_avatar):
        """Gifting spirit stones succeeds."""
        dummy_avatar.magic_stone = 1000
        target_avatar.magic_stone = 0
        
        # Mock asyncio loop just to pass the step() check
        with patch("asyncio.get_running_loop", return_value=MagicMock()):
            gift_action.step(target_avatar, item_id="SPIRIT_STONE", amount=100)
            
        can_start, reason = gift_action._can_start(target_avatar)
        assert can_start is True, f"Should be able to start: {reason}"
        
        # Simulate acceptance
        gift_action._settle_response(target_avatar, "Accept")
        
        assert dummy_avatar.magic_stone == 900
        assert target_avatar.magic_stone == 100
        assert gift_action._gift_success is True

    def test_gift_spirit_stone_insufficient(self, gift_action, dummy_avatar, target_avatar):
        """Not enough spirit stones."""
        dummy_avatar.magic_stone = 50
        
        with patch("asyncio.get_running_loop", return_value=MagicMock()):
             gift_action.step(target_avatar, item_id="SPIRIT_STONE", amount=100)
             
        can_start, reason = gift_action._can_start(target_avatar)
        
        assert can_start is False
        assert "Insufficient spirit stones" in reason

    # --- 2. Gifting materials ---

    def test_gift_material_success(self, gift_action, dummy_avatar, target_avatar, mock_item_data):
        """Gifting a material succeeds."""
        test_material = mock_item_data["obj_material"]
        dummy_avatar.add_material(test_material, quantity=5)
        
        with patch("asyncio.get_running_loop", return_value=MagicMock()):
            # Non-stone gifts are forced to quantity 1
            gift_action.step(target_avatar, item_id=str(test_material.id), amount=999) 
        
        can_start, reason = gift_action._can_start(target_avatar)
        assert can_start is True
        
        gift_action._settle_response(target_avatar, "Accept")
        
        assert dummy_avatar.get_material_quantity(test_material) == 4
        assert target_avatar.get_material_quantity(test_material) == 1
        assert gift_action._current_gift_context["amount"] == 1

    def test_gift_material_not_owned(self, gift_action, dummy_avatar, target_avatar, mock_item_data):
        """Gifting a material that is not owned."""
        test_material = mock_item_data["obj_material"]
        
        with patch("asyncio.get_running_loop", return_value=MagicMock()):
            gift_action.step(target_avatar, item_id=str(test_material.id), amount=1)
            
        can_start, reason = gift_action._can_start(target_avatar)
        assert can_start is False

    # --- 3. Gifting equipment ---

    def test_gift_weapon_success_and_auto_equip(self, gift_action, dummy_avatar, target_avatar, mock_item_data):
        """Gifting equipment succeeds and the target auto-equips it."""
        test_weapon = mock_item_data["obj_weapon"]
        dummy_avatar.weapon = test_weapon
        assert target_avatar.weapon is None
        
        with patch("asyncio.get_running_loop", return_value=MagicMock()):
            gift_action.step(target_avatar, item_id=str(test_weapon.id), amount=1)
        
        can_start, reason = gift_action._can_start(target_avatar)
        assert can_start is True
        
        gift_action._settle_response(target_avatar, "Accept")
        
        assert dummy_avatar.weapon is None
        assert target_avatar.weapon == test_weapon

    def test_gift_weapon_fail_not_equipped(self, gift_action, dummy_avatar, target_avatar, mock_item_data):
        """Gifting equipment that is not equipped."""
        test_weapon = mock_item_data["obj_weapon"]
        
        with patch("asyncio.get_running_loop", return_value=MagicMock()):
            gift_action.step(target_avatar, item_id=str(test_weapon.id), amount=1)
            
        can_start, reason = gift_action._can_start(target_avatar)
        assert can_start is False

    def test_gift_weapon_target_trade_in(self, gift_action, dummy_avatar, target_avatar, mock_item_data):
        """When the target already has equipment, the old one is sold at a discount."""
        from tests.conftest import create_test_weapon
        from src.systems.cultivation import Realm
        
        new_weapon = mock_item_data["obj_weapon"]
        dummy_avatar.weapon = new_weapon
        
        old_weapon = create_test_weapon("Old Iron Sword", Realm.Qi_Refinement, weapon_id=999)     
        # old_weapon.price = 100 # Prices are now set by realm (Qi Refinement = 150), not manually
        target_avatar.weapon = old_weapon
        target_avatar.magic_stone = 0
        
        with patch("asyncio.get_running_loop", return_value=MagicMock()):
            gift_action.step(target_avatar, item_id=str(new_weapon.id), amount=1)
            
        gift_action._settle_response(target_avatar, "Accept")
        
        assert target_avatar.weapon == new_weapon
        # Qi Refinement weapon base price 150, sell multiplier 1.0 (no persona bonus) -> 150
        assert target_avatar.magic_stone == 150

    # --- 4. Context and description ---

    def test_prompt_info_description(self, gift_action, dummy_avatar, target_avatar, mock_item_data):
        """The prompt sent to the LLM includes the specific item description."""
        test_weapon = mock_item_data["obj_weapon"]
        dummy_avatar.weapon = test_weapon
        
        with patch("asyncio.get_running_loop", return_value=MagicMock()):
            gift_action.step(target_avatar, item_id=str(test_weapon.id))
            
        infos = gift_action._build_prompt_infos(target_avatar)
        
        assert f"[{test_weapon.name}]" in infos["action_info"]
        assert "Gift you" in infos["action_info"]

    def test_prompt_info_description_stones(self, gift_action, dummy_avatar, target_avatar):
        dummy_avatar.magic_stone = 1000
        
        with patch("asyncio.get_running_loop", return_value=MagicMock()):
            gift_action.step(target_avatar, item_id="SPIRIT_STONE", amount=500)
            
        infos = gift_action._build_prompt_infos(target_avatar)
        assert "500 spirit stones" in infos["action_info"]
    
    def test_gift_invalid_id(self, gift_action, dummy_avatar, target_avatar):
        """Passing an invalid ID."""
        with patch("asyncio.get_running_loop", return_value=MagicMock()):
            gift_action.step(target_avatar, item_id="invalid_id_999", amount=1)
            
        can_start, reason = gift_action._can_start(target_avatar)
        assert can_start is False
        assert "Item not found" in reason

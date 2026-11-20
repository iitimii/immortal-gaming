import pytest
from unittest.mock import patch
from src.classes.action.buy import Buy
from src.classes.environment.region import CityRegion
from src.classes.items.elixir import ElixirType, ConsumedElixir
from src.systems.cultivation import Realm
from tests.conftest import create_test_weapon # Explicitly import if needed, or rely on conftest being auto-loaded (it is)

def test_buy_item_success(avatar_in_city, mock_item_data):
    """Buying an ordinary material succeeds."""
    elixirs_mock = mock_item_data["elixirs"]
    materials_mock = mock_item_data["materials"]
    test_material = mock_item_data["obj_material"]
    
    # Mock CityRegion.is_selling directly on avatar_in_city.tile.region
    # (avatar_in_city's region is a real CityRegion, so patch the method dynamically)
    with patch.object(avatar_in_city.tile.region, 'is_selling', return_value=True) as mock_is_selling:
        with patch("src.utils.resolution.elixirs_by_name", elixirs_mock), \
             patch("src.utils.resolution.materials_by_name", materials_mock):
            
            action = Buy(avatar_in_city, avatar_in_city.world)
            
            # 1. Check whether it can be bought
            can_start, reason = action.can_start("Iron Ore")
            assert can_start is True
            mock_is_selling.assert_called_with("Iron Ore")
            
            # 2. Perform the purchase
            initial_money = avatar_in_city.magic_stone
            # Qi Refinement material base price 10, multiplier 1.5 -> 15
            expected_price = int(10 * 1.5)
            
            action._execute("Iron Ore")
            
            # 3. Verify the result
            assert avatar_in_city.magic_stone == initial_money - expected_price
            assert avatar_in_city.get_material_quantity(test_material) == 1

def test_buy_elixir_success(avatar_in_city, mock_item_data):
    """Buying and consuming an elixir succeeds."""
    elixirs_mock = mock_item_data["elixirs"]
    materials_mock = mock_item_data["materials"]
    test_elixir = mock_item_data["obj_elixir"]
    
    with patch.object(avatar_in_city.tile.region, 'is_selling', return_value=True):
        with patch("src.utils.resolution.elixirs_by_name", elixirs_mock), \
             patch("src.utils.resolution.materials_by_name", materials_mock):
            
            action = Buy(avatar_in_city, avatar_in_city.world)
            
            can_start, reason = action.can_start("Qi Gathering Pill")
            assert can_start is True
            
            initial_money = avatar_in_city.magic_stone
            expected_price = int(test_elixir.price * 1.5)
            
            # Simulate consuming the elixir
            action._execute("Qi Gathering Pill")
            
            assert avatar_in_city.magic_stone == initial_money - expected_price
            # The elixir must not end up in the inventory
            assert len(avatar_in_city.materials) == 0 
            # It should be in the consumed list
            assert len(avatar_in_city.elixirs) == 1
            assert avatar_in_city.elixirs[0].elixir.name == "Qi Gathering Pill"

def test_buy_fail_item_not_sold(avatar_in_city, mock_item_data):
    """The item is not in the shop's selling list."""
    elixirs_mock = mock_item_data["elixirs"]
    materials_mock = mock_item_data["materials"]
    
    # Mock is_selling to return False
    with patch.object(avatar_in_city.tile.region, 'is_selling', return_value=False):
        with patch("src.utils.resolution.elixirs_by_name", elixirs_mock), \
             patch("src.utils.resolution.materials_by_name", materials_mock):
             
            action = Buy(avatar_in_city, avatar_in_city.world)
            can_start, reason = action.can_start("Iron Ore")
            
            assert can_start is False
            assert "does not sell" in reason

def test_buy_fail_not_in_city(dummy_avatar, mock_item_data):
    """Cannot buy outside a city."""
    elixirs_mock = mock_item_data["elixirs"]
    materials_mock = mock_item_data["materials"]
    
    # Make sure we are not in a city (dummy_avatar defaults to (0,0) PLAIN)
    assert not isinstance(dummy_avatar.tile.region, CityRegion)
    
    with patch("src.utils.resolution.elixirs_by_name", elixirs_mock), \
         patch("src.utils.resolution.materials_by_name", materials_mock):
        
        action = Buy(dummy_avatar, dummy_avatar.world)
        can_start, reason = action.can_start("Iron Ore")
        
        assert can_start is False
        assert "Can only execute in city areas" in reason

def test_buy_fail_no_money(avatar_in_city, mock_item_data):
    """Cannot buy without money."""
    elixirs_mock = mock_item_data["elixirs"]
    materials_mock = mock_item_data["materials"]
    
    avatar_in_city.magic_stone = 0 # no money
    
    with patch.object(avatar_in_city.tile.region, 'is_selling', return_value=True):
        with patch("src.utils.resolution.elixirs_by_name", elixirs_mock), \
             patch("src.utils.resolution.materials_by_name", materials_mock):
            
            action = Buy(avatar_in_city, avatar_in_city.world)
            can_start, reason = action.can_start("Iron Ore")
            
            assert can_start is False
            assert "Not enough spirit stones" in reason

def test_buy_fail_unknown_item(avatar_in_city, mock_item_data):
    """Unknown item."""
    elixirs_mock = mock_item_data["elixirs"]
    materials_mock = mock_item_data["materials"]
    
    with patch("src.utils.resolution.elixirs_by_name", elixirs_mock), \
         patch("src.utils.resolution.materials_by_name", materials_mock):
        
        action = Buy(avatar_in_city, avatar_in_city.world)
        can_start, reason = action.can_start("Nonexistent Thing")
        
        assert can_start is False
        assert "Unknown item" in reason

def test_buy_elixir_fail_high_level_restricted(avatar_in_city, mock_item_data):
    """Buying a higher-tier elixir is restricted."""
    elixirs_mock = mock_item_data["elixirs"]
    materials_mock = mock_item_data["materials"]
    high_level_elixir = mock_item_data["obj_high_elixir"]
    
    # Give enough money
    avatar_in_city.magic_stone = 10000
    
    # Avatar is Qi Refinement, trying to buy a Foundation Establishment elixir
    assert avatar_in_city.cultivation_progress.realm == Realm.Qi_Refinement
    assert high_level_elixir.realm == Realm.Foundation_Establishment
    
    with patch.object(avatar_in_city.tile.region, 'is_selling', return_value=True):
        with patch("src.utils.resolution.elixirs_by_name", elixirs_mock), \
             patch("src.utils.resolution.materials_by_name", materials_mock):
            
            action = Buy(avatar_in_city, avatar_in_city.world)
            can_start, reason = action.can_start("Foundation Pill")
            
            assert can_start is False
            # Generic realm restriction message
            assert "Realm too low" in reason

def test_buy_elixir_fail_duplicate_active(avatar_in_city, mock_item_data):
    """Cannot buy again while the elixir effect is still active."""
    elixirs_mock = mock_item_data["elixirs"]
    materials_mock = mock_item_data["materials"]
    test_elixir = mock_item_data["obj_elixir"]
    
    # Consume one first
    consumed = ConsumedElixir(test_elixir, int(avatar_in_city.world.month_stamp))
    
    avatar_in_city.elixirs.append(consumed)
    
    with patch.object(avatar_in_city.tile.region, 'is_selling', return_value=True):
        with patch("src.utils.resolution.elixirs_by_name", elixirs_mock), \
             patch("src.utils.resolution.materials_by_name", materials_mock):
            
            action = Buy(avatar_in_city, avatar_in_city.world)
            can_start, reason = action.can_start("Qi Gathering Pill")
            
            assert can_start is False
            assert "still active" in reason

def test_buy_weapon_trade_in(avatar_in_city, mock_item_data):
    """Buying a new weapon automatically sells the old one."""
    # Build an old weapon here; mock_item_data only has the new one
    from tests.conftest import create_test_weapon
    from src.classes.items.weapon import Weapon, WeaponType
    
    elixirs_mock = mock_item_data["elixirs"]
    materials_mock = mock_item_data["materials"]
    new_weapon = mock_item_data["obj_weapon"]
    
    materials_mock["Azure Cloud Sword"] = new_weapon
    
    # Build the old weapon
    old_weapon = create_test_weapon("Iron Sword", Realm.Qi_Refinement, weapon_id=199)
    old_weapon.effects = {'atk': 1}
    
    # Equip the old weapon
    avatar_in_city.change_weapon(old_weapon)
    assert avatar_in_city.weapon == old_weapon
    
    initial_money = avatar_in_city.magic_stone
    
    # Price calculation
    # Qi Refinement Weapon Base Price = 150 (refer to src/classes/prices.py)
    # Buy: 150 * 1.5 = 225
    buy_cost = 225
    # Sell: 150 * 1.0 = 150
    sell_refund = 150
    
    expected_money = initial_money - buy_cost + sell_refund
    
    with patch.object(avatar_in_city.tile.region, 'is_selling', return_value=True):
        with patch("src.utils.resolution.elixirs_by_name", elixirs_mock), \
             patch("src.utils.resolution.materials_by_name", materials_mock):
             
            action = Buy(avatar_in_city, avatar_in_city.world)
            
            # Verify the event description
            event = action.start("Azure Cloud Sword")
            assert "Azure Cloud Sword" in event.content
            assert "Iron Sword" in event.content
            assert "sold old" in event.content
            
            # Perform the purchase
            action._execute("Azure Cloud Sword")
            
            assert avatar_in_city.weapon.name == "Azure Cloud Sword"
            assert avatar_in_city.weapon != old_weapon
            assert avatar_in_city.magic_stone == expected_money

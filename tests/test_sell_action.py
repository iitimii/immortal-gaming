import pytest
from unittest.mock import patch
from src.classes.action.sell import Sell
from src.classes.environment.region import CityRegion
from tests.conftest import create_test_material # Explicit import if needed

def test_sell_material_success(avatar_in_city, mock_item_data):
    """Selling an ordinary material succeeds."""
    materials_mock = mock_item_data["materials"]
    weapons_mock = mock_item_data["weapons"]
    auxiliaries_mock = mock_item_data["auxiliaries"]
    test_material = mock_item_data["obj_material"]
    
    # Give the avatar materials
    avatar_in_city.add_material(test_material, quantity=5)
    
    with patch("src.utils.resolution.materials_by_name", materials_mock), \
         patch("src.utils.resolution.weapons_by_name", weapons_mock), \
         patch("src.utils.resolution.auxiliaries_by_name", auxiliaries_mock):
        
        action = Sell(avatar_in_city, avatar_in_city.world)
        
        # 1. Check that it can be sold
        can_start, reason = action.can_start("Iron Ore")
        assert can_start is True
        
        # 2. Sell
        # Qi Refinement material base price is 10, default sell multiplier 1.0 -> unit price 10
        # Selling all 5 -> total 50
        initial_money = avatar_in_city.magic_stone
        expected_income = 50
        
        action._execute("Iron Ore")
        
        # 3. Verify the result
        assert avatar_in_city.magic_stone == initial_money + expected_income
        assert avatar_in_city.get_material_quantity(test_material) == 0

def test_sell_weapon_success(avatar_in_city, mock_item_data):
    """Selling the equipped weapon succeeds."""
    materials_mock = mock_item_data["materials"]
    weapons_mock = mock_item_data["weapons"]
    auxiliaries_mock = mock_item_data["auxiliaries"]
    test_weapon = mock_item_data["obj_weapon"]
    
    # Equip the weapon
    avatar_in_city.weapon = test_weapon
    
    with patch("src.utils.resolution.materials_by_name", materials_mock), \
         patch("src.utils.resolution.weapons_by_name", weapons_mock), \
         patch("src.utils.resolution.auxiliaries_by_name", auxiliaries_mock):
        
        action = Sell(avatar_in_city, avatar_in_city.world)
        
        # 1. Check that it can be sold
        can_start, reason = action.can_start("Azure Cloud Sword")
        assert can_start is True
        
        # 2. Sell
        # Qi Refinement weapon base price is 150 (see src/classes/prices.py)
        # Default sell bonus 0.0 -> unit price 150
        expected_income = 150 
        
        initial_money = avatar_in_city.magic_stone
        action._execute("Azure Cloud Sword")
        
        # 3. Verify the result
        assert avatar_in_city.magic_stone == initial_money + expected_income
        assert avatar_in_city.weapon is None

def test_sell_auxiliary_success(avatar_in_city, mock_item_data):
    """Selling the equipped auxiliary succeeds."""
    materials_mock = mock_item_data["materials"]
    weapons_mock = mock_item_data["weapons"]
    auxiliaries_mock = mock_item_data["auxiliaries"]
    test_auxiliary = mock_item_data["obj_auxiliary"]
    
    # Equip the auxiliary
    avatar_in_city.auxiliary = test_auxiliary
    
    with patch("src.utils.resolution.materials_by_name", materials_mock), \
         patch("src.utils.resolution.weapons_by_name", weapons_mock), \
         patch("src.utils.resolution.auxiliaries_by_name", auxiliaries_mock):
        
        action = Sell(avatar_in_city, avatar_in_city.world)
        
        can_start, reason = action.can_start("Spirit Gathering Orb")
        assert can_start is True
        
        # Qi Refinement auxiliary base price is 150
        expected_income = 150
        
        action._execute("Spirit Gathering Orb")
        
        assert avatar_in_city.magic_stone == 1000 + expected_income
        assert avatar_in_city.auxiliary is None

def test_sell_fail_not_in_city(dummy_avatar, mock_item_data):
    """Selling is impossible outside a city."""
    materials_mock = mock_item_data["materials"]
    weapons_mock = mock_item_data["weapons"]
    auxiliaries_mock = mock_item_data["auxiliaries"]
    test_material = mock_item_data["obj_material"]
    
    # Make sure we are not in a city
    assert not isinstance(dummy_avatar.tile.region, CityRegion)
    dummy_avatar.add_material(test_material, 1)
    
    with patch("src.utils.resolution.materials_by_name", materials_mock), \
         patch("src.utils.resolution.weapons_by_name", weapons_mock), \
         patch("src.utils.resolution.auxiliaries_by_name", auxiliaries_mock):
        
        action = Sell(dummy_avatar, dummy_avatar.world)
        can_start, reason = action.can_start("Iron Ore")
        
        assert can_start is False
        assert "Can only execute in city" in reason

def test_sell_fail_no_item(avatar_in_city, mock_item_data):
    """The avatar does not hold the material."""
    materials_mock = mock_item_data["materials"]
    weapons_mock = mock_item_data["weapons"]
    auxiliaries_mock = mock_item_data["auxiliaries"]
    
    # Empty inventory, no equipment (fixture default)
    
    with patch("src.utils.resolution.materials_by_name", materials_mock), \
         patch("src.utils.resolution.weapons_by_name", weapons_mock), \
         patch("src.utils.resolution.auxiliaries_by_name", auxiliaries_mock):
        
        action = Sell(avatar_in_city, avatar_in_city.world)
        can_start, reason = action.can_start("Iron Ore")
        
        assert can_start is False
        assert "Do not possess material" in reason

def test_sell_fail_unknown_name(avatar_in_city, mock_item_data):
    """Unknown item name."""
    materials_mock = mock_item_data["materials"]
    weapons_mock = mock_item_data["weapons"]
    auxiliaries_mock = mock_item_data["auxiliaries"]
    
    with patch("src.utils.resolution.materials_by_name", materials_mock), \
         patch("src.utils.resolution.weapons_by_name", weapons_mock), \
         patch("src.utils.resolution.auxiliaries_by_name", auxiliaries_mock):
        
        action = Sell(avatar_in_city, avatar_in_city.world)
        can_start, reason = action.can_start("Nonexistent Divine Artifact")
        
        assert can_start is False
        assert "Do not possess item/equipment" in reason

def test_sell_priority(avatar_in_city, mock_item_data):
    """Priority: with duplicate names, equipped gear is sold first (resolution priority)."""
    materials_mock = mock_item_data["materials"]
    weapons_mock = mock_item_data["weapons"]
    auxiliaries_mock = mock_item_data["auxiliaries"]
    test_weapon = mock_item_data["obj_weapon"]
    
    # Build a material with the same name
    # Imported from conftest
    from src.systems.cultivation import Realm
    fake_sword_material = create_test_material("Azure Cloud Sword", Realm.Qi_Refinement)
    
    # Update the mock so "Azure Cloud Sword" also resolves among materials
    materials_mock["Azure Cloud Sword"] = fake_sword_material
    
    # The avatar holds both the material and the weapon
    avatar_in_city.add_material(fake_sword_material, 1)
    avatar_in_city.weapon = test_weapon # name is also "Azure Cloud Sword"
    
    with patch("src.utils.resolution.materials_by_name", materials_mock), \
         patch("src.utils.resolution.weapons_by_name", weapons_mock), \
         patch("src.utils.resolution.auxiliaries_by_name", auxiliaries_mock):
        
        action = Sell(avatar_in_city, avatar_in_city.world)
        
        # Sell
        action._execute("Azure Cloud Sword")
        
        # Assert: the weapon is gone and the material remains.
        assert avatar_in_city.weapon is None
        assert avatar_in_city.get_material_quantity(fake_sword_material) == 1

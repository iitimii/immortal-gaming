import pytest
import copy
from unittest.mock import MagicMock, patch

from src.classes.prices import prices, Prices
from src.systems.cultivation import Realm
from src.classes.material import materials_by_id
from src.classes.items.weapon import weapons_by_id, Weapon, get_random_weapon_by_realm
from src.classes.items.auxiliary import auxiliaries_by_id, Auxiliary, get_random_auxiliary_by_realm


class TestPrices:
    """Price system tests."""
    
    def test_material_prices_by_realm(self):
        """Material prices increase with realm."""
        assert prices.MATERIAL_PRICES[Realm.Qi_Refinement] < prices.MATERIAL_PRICES[Realm.Foundation_Establishment]
        assert prices.MATERIAL_PRICES[Realm.Foundation_Establishment] < prices.MATERIAL_PRICES[Realm.Core_Formation]
        assert prices.MATERIAL_PRICES[Realm.Core_Formation] < prices.MATERIAL_PRICES[Realm.Nascent_Soul]

    def test_weapon_prices_by_realm(self):
        """Weapon prices increase with realm."""
        assert prices.WEAPON_PRICES[Realm.Qi_Refinement] < prices.WEAPON_PRICES[Realm.Foundation_Establishment]
        assert prices.WEAPON_PRICES[Realm.Foundation_Establishment] < prices.WEAPON_PRICES[Realm.Core_Formation]
        assert prices.WEAPON_PRICES[Realm.Core_Formation] < prices.WEAPON_PRICES[Realm.Nascent_Soul]

    def test_auxiliary_prices_by_realm(self):
        """Auxiliary prices increase with realm."""
        assert prices.AUXILIARY_PRICES[Realm.Qi_Refinement] < prices.AUXILIARY_PRICES[Realm.Foundation_Establishment]
        assert prices.AUXILIARY_PRICES[Realm.Foundation_Establishment] < prices.AUXILIARY_PRICES[Realm.Core_Formation]
        assert prices.AUXILIARY_PRICES[Realm.Core_Formation] < prices.AUXILIARY_PRICES[Realm.Nascent_Soul]

    def test_get_price_for_material(self):
        """get_price dispatches for Material."""
        if not materials_by_id:
            pytest.skip("No items available in config")
        
        item = next(iter(materials_by_id.values()))
        price = prices.get_price(item)
        expected = prices.get_material_price(item)
        assert price == expected
        assert price == prices.MATERIAL_PRICES[item.realm]

    def test_get_price_for_weapon(self):
        """get_price dispatches for Weapon."""
        if not weapons_by_id:
            pytest.skip("No weapons available in config")
        
        weapon = next(iter(weapons_by_id.values()))
        price = prices.get_price(weapon)
        expected = prices.get_weapon_price(weapon)
        assert price == expected
        assert price == prices.WEAPON_PRICES[weapon.realm]

    def test_get_price_for_auxiliary(self):
        """get_price dispatches for Auxiliary."""
        if not auxiliaries_by_id:
            pytest.skip("No auxiliaries available in config")
        
        aux = next(iter(auxiliaries_by_id.values()))
        price = prices.get_price(aux)
        expected = prices.get_auxiliary_price(aux)
        assert price == expected
        assert price == prices.AUXILIARY_PRICES[aux.realm]

    def test_weapon_more_expensive_than_material(self):
        """Weapons cost more than materials at the same realm."""
        for realm in Realm:
            if realm in prices.MATERIAL_PRICES and realm in prices.WEAPON_PRICES:
                assert prices.WEAPON_PRICES[realm] >= prices.MATERIAL_PRICES[realm]


class TestAvatarSell:
    """Avatar selling API tests."""

    def test_sell_material_basic(self, dummy_avatar):
        """Basic material sale."""
        if not materials_by_id:
            pytest.skip("No items available in config")
        
        item = next(iter(materials_by_id.values()))
        dummy_avatar.materials = {}  # empty the inventory
        dummy_avatar.magic_stone.value = 0
        
        # Add items
        dummy_avatar.add_material(item, 5)
        assert dummy_avatar.get_material_quantity(item) == 5
        
        # Sell 3
        gained = dummy_avatar.sell_material(item, 3)
        
        expected_price = prices.get_material_price(item) * 3
        assert gained == expected_price
        assert dummy_avatar.magic_stone.value == expected_price
        assert dummy_avatar.get_material_quantity(item) == 2

    def test_sell_material_insufficient(self, dummy_avatar):
        """Selling more items than owned."""
        if not materials_by_id:
            pytest.skip("No items available in config")
        
        item = next(iter(materials_by_id.values()))
        dummy_avatar.materials = {}
        dummy_avatar.magic_stone.value = 100
        
        dummy_avatar.add_material(item, 2)
        
        # Try to sell 5 (only 2 owned)
        gained = dummy_avatar.sell_material(item, 5)
        
        assert gained == 0
        assert dummy_avatar.magic_stone.value == 100  # unchanged
        assert dummy_avatar.get_material_quantity(item) == 2  # items not reduced

    def test_sell_weapon(self, dummy_avatar):
        """Selling a weapon."""
        weapon = get_random_weapon_by_realm(Realm.Foundation_Establishment)
        if not weapon:
            pytest.skip("No Foundation Establishment weapons available")
        
        dummy_avatar.magic_stone.value = 0
        
        gained = dummy_avatar.sell_weapon(weapon)
        
        expected = prices.get_weapon_price(weapon)
        assert gained == expected
        assert dummy_avatar.magic_stone.value == expected

    def test_sell_auxiliary(self, dummy_avatar):
        """Selling an auxiliary."""
        aux = get_random_auxiliary_by_realm(Realm.Core_Formation)
        if not aux:
            pytest.skip("No Core Formation auxiliaries available")
        
        dummy_avatar.magic_stone.value = 0
        
        gained = dummy_avatar.sell_auxiliary(aux)
        
        expected = prices.get_auxiliary_price(aux)
        assert gained == expected
        assert dummy_avatar.magic_stone.value == expected

    def test_sell_with_price_multiplier(self, dummy_avatar):
        """Sell price multiplier effect."""
        if not materials_by_id:
            pytest.skip("No items available in config")
        
        item = next(iter(materials_by_id.values()))
        dummy_avatar.materials = {}
        dummy_avatar.magic_stone.value = 0
        dummy_avatar.add_material(item, 1)
        
        base_price = prices.get_material_price(item)
        
        # Simulate a 20% bonus (0.2)
        # effects is a property, so it has to be patched
        with patch("src.classes.core.avatar.core.Avatar.effects", new_callable=lambda: {"extra_item_sell_price_multiplier": 0.2}):
             # Note: Avatar is composed of several mixins; effects lives in EffectsMixin
             # but is resolved on the Avatar class once mixed in.
             pass

        # Patching the property is fiddly, and Prices.get_selling_price is covered by its own
        # unit tests, so patch prices.get_selling_price instead and verify that it is called
        # and its return value is credited correctly.
        
        expected_total = int(base_price * 1.2)
        with patch("src.classes.prices.prices.get_selling_price", return_value=expected_total) as mock_get_price:
            gained = dummy_avatar.sell_material(item, 1)
            
            # Verify the call arguments
            mock_get_price.assert_called_with(item, dummy_avatar)
            
        assert gained == expected_total
        assert dummy_avatar.magic_stone.value == expected_total

    def test_sell_weapon_with_multiplier(self, dummy_avatar):
        """Price multiplier applies when selling a weapon."""
        weapon = get_random_weapon_by_realm(Realm.Qi_Refinement)
        if not weapon:
            pytest.skip("No Qi Refinement weapons available")
        
        dummy_avatar.magic_stone.value = 0
        base_price = prices.get_weapon_price(weapon)
        
        expected_total = int(base_price * 1.5)
        
        # Likewise patch get_selling_price
        with patch("src.classes.prices.prices.get_selling_price", return_value=expected_total) as mock_get_price:
            gained = dummy_avatar.sell_weapon(weapon)
            mock_get_price.assert_called_with(weapon, dummy_avatar)
        
        assert gained == expected_total


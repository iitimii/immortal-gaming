import pytest
from unittest.mock import MagicMock, patch

from src.classes.action.self_heal import SelfHeal
from src.classes.environment.sect_region import SectRegion
from src.classes.environment.region import NormalRegion
from src.classes.environment.tile import Tile, TileType
from src.classes.core.sect import Sect
from src.classes.hp import HP

class TestSelfHealAction:
    
    @pytest.fixture
    def healing_avatar(self, dummy_avatar):
        """
        Extends dummy_avatar with half HP so healing is possible.
        """
        dummy_avatar.hp = HP(100, 50) # 50/100 HP
        # effects is a property and cannot be assigned directly; mock it or override via the effects mixin
        # dummy_avatar is a real Avatar, so the effects property reads self._effects or computes it
        return dummy_avatar

    @pytest.fixture
    def sect_region(self):
        return SectRegion(id=999, name="Azure Cloud Sect Headquarters", desc="Test sect headquarters", sect_id=42, sect_name="Azure Cloud Sect")
    
    @pytest.fixture
    def normal_region(self):
        return NormalRegion(id=101, name="Wilderness", desc="Test wilderness")

    @pytest.fixture
    def mock_sect(self, sect_region):
        sect = MagicMock(spec=Sect)
        sect.id = sect_region.sect_id
        sect.name = "Azure Cloud Sect"
        sect.headquarter = MagicMock()
        sect.headquarter.name = "An outdated old name"
        return sect

    def test_can_start_basic(self, healing_avatar):
        """Basic start condition: HP is not full."""
        # Action classes usually take (avatar, world)
        action = SelfHeal(healing_avatar, healing_avatar.world)
        can, reason = action.can_start()
        assert can is True
        assert reason == ""

    def test_cannot_start_full_hp(self, healing_avatar):
        """Cannot start at full HP."""
        healing_avatar.hp.cur = 100
        action = SelfHeal(healing_avatar, healing_avatar.world)
        can, reason = action.can_start()
        assert can is False
        assert "HP is full" in reason

    def test_execute_in_wild_no_bonus(self, healing_avatar, normal_region):
        """Base recovery (10%) in the wild (not a sect)."""
        # Set location
        healing_avatar.tile = Tile(0, 0, TileType.PLAIN)
        healing_avatar.tile.region = normal_region
        healing_avatar.sect = None # rogue cultivator
        
        # Mock empty effects
        with patch.object(type(healing_avatar), 'effects', new_callable=lambda: {}) as mock_effects:
             action = SelfHeal(healing_avatar, healing_avatar.world)
             action._execute()

        # Expected: base recovery 10% * 100 = 10
        # starting 50 -> 60
        assert healing_avatar.hp.cur == 60
        assert action._healed_total == 10

    def test_execute_in_wild_with_persona_bonus(self, healing_avatar, normal_region):
        """Recovery in the wild with a cautious-persona bonus (+50% efficiency)."""
        # Set location
        healing_avatar.tile = Tile(0, 0, TileType.PLAIN)
        healing_avatar.tile.region = normal_region
        
        # Mock effects with a bonus
        with patch.object(type(healing_avatar), 'effects', new_callable=lambda: {"extra_self_heal_efficiency": 0.5}):
            action = SelfHeal(healing_avatar, healing_avatar.world)
            action._execute()

        # Expected: base 0.1 * (1 + 0.5) = 0.15
        # recovers 15 -> 50 + 15 = 65
        assert healing_avatar.hp.cur == 65
        assert action._healed_total == 15

    def test_execute_in_sect_hq_as_member(self, healing_avatar, sect_region, mock_sect):
        """A sect member at their HQ recovers fully."""
        # Set location
        # TileType.SECT may not exist; the source usually uses CITY or PLAIN, what matters is the region
        # If TileType matters, check src/classes/tile.py; here we use PLAIN and make the region a SectRegion
        # To be safe, the TileType definition can be checked.
        # Use PLAIN for now; the region type is what matters.
        healing_avatar.tile = Tile(0, 0, TileType.PLAIN)
        healing_avatar.tile.region = sect_region
        
        # Set sect membership
        healing_avatar.sect = mock_sect

        with patch.object(type(healing_avatar), 'effects', new_callable=lambda: {}):
            action = SelfHeal(healing_avatar, healing_avatar.world)
            action._execute()

        # Expected: fully healed -> 100
        assert healing_avatar.hp.cur == 100
        assert action._healed_total == 50

    def test_execute_in_sect_hq_not_member(self, healing_avatar, sect_region):
        """A non-member at a sect HQ (treated as normal-region recovery)."""
        # Set location
        healing_avatar.tile = Tile(0, 0, TileType.PLAIN)
        healing_avatar.tile.region = sect_region
        
        # rogue cultivator (or no matching sect)
        healing_avatar.sect = None 

        with patch.object(type(healing_avatar), 'effects', new_callable=lambda: {}):
            action = SelfHeal(healing_avatar, healing_avatar.world)
            action._execute()

        # Expected: base recovery 10% = 10
        assert healing_avatar.hp.cur == 60
        assert action._healed_total == 10

    def test_heal_overflow_clamp(self, healing_avatar, normal_region):
        """Recovery overflow handling (never exceeds max HP)."""
        healing_avatar.hp.cur = 95 # only 5 missing
        healing_avatar.tile = Tile(0, 0, TileType.PLAIN)
        healing_avatar.tile.region = normal_region

        with patch.object(type(healing_avatar), 'effects', new_callable=lambda: {}):
            action = SelfHeal(healing_avatar, healing_avatar.world)
            action._execute()

        # Expected: base recovery 10 but only 5 missing -> recovers 5, now 100
        assert healing_avatar.hp.cur == 100
        assert action._healed_total == 5

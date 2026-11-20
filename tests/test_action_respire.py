import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from src.classes.action.respire import Respire
from src.classes.environment.tile import TileType
from src.classes.environment.region import CultivateRegion, NormalRegion
from src.classes.environment.sect_region import SectRegion
from src.classes.event import Event
from src.classes.root import Root
from src.classes.essence import EssenceType

class TestActionRespire:
    
    @pytest.fixture
    def cultivation_avatar(self, dummy_avatar):
        """Set up an avatar environment suitable for cultivation."""
        # Set spirit root
        dummy_avatar.root = Root.FIRE
        
        # Patch out the effects property
        # Note: this affects the Avatar class but is restored when the fixture scope ends
        with patch('src.classes.core.avatar.Avatar.effects', new_callable=PropertyMock) as mock_effects:
            mock_effects.return_value = {}
            
            # Reset cultivation progress
            dummy_avatar.cultivation_progress.exp = 0
            # Set to level 29
            dummy_avatar.cultivation_progress.level = 29
            dummy_avatar.cultivation_progress.max_exp = 1000 
            
            yield dummy_avatar

    def test_respire_in_wild(self, cultivation_avatar):
        """Respiring in the wild (non-cultivation region): minimum experience."""
        # Make sure the current region is not a CultivateRegion
        tile = cultivation_avatar.tile
        tile.region = NormalRegion(id=999, name="Wild", desc="Just Wild") # normal region
        
        action = Respire(cultivation_avatar, cultivation_avatar.world)
        
        # Check
        can_start, reason = action.can_start()
        assert can_start is True
        
        # Execute
        action._execute()
        
        # Assert: minimum experience gained
        expected_exp = Respire.BASE_EXP_LOW_EFFICIENCY
        assert cultivation_avatar.cultivation_progress.exp == expected_exp

    def test_respire_in_matching_region(self, cultivation_avatar):
        """Respiring in a cave with matching essence: high experience."""
        # Set the current tile to a CultivateRegion
        region = CultivateRegion(id=1, name="Fire Cave", desc="Hot", essence_type=EssenceType.FIRE, essence_density=5)
        
        cultivation_avatar.tile.region = region
        
        action = Respire(cultivation_avatar, cultivation_avatar.world)
        action._execute()
        
        # Assert: density(5) * base(100) = 500
        expected_exp = 5 * Respire.BASE_EXP_PER_DENSITY
        
        assert cultivation_avatar.cultivation_progress.exp == expected_exp

    def test_respire_in_mismatching_region(self, cultivation_avatar):
        """Respiring in a cave with mismatched essence: minimum experience."""
        # Water essence, while the avatar has a fire root
        region = CultivateRegion(id=2, name="Water Cave", desc="Wet", essence_type=EssenceType.WATER, essence_density=5)
        cultivation_avatar.tile.region = region
        
        action = Respire(cultivation_avatar, cultivation_avatar.world)
        action._execute()
        
        # Assert: 0 * 100 -> fallback to LOW_EFFICIENCY
        expected_exp = Respire.BASE_EXP_LOW_EFFICIENCY
        assert cultivation_avatar.cultivation_progress.exp == expected_exp

    def test_respire_bottleneck(self, cultivation_avatar):
        """Respiring at a bottleneck: no experience gained."""
        # Set to a bottleneck level
        cultivation_avatar.cultivation_progress.level = 30 
        initial_exp = cultivation_avatar.cultivation_progress.exp
        
        action = Respire(cultivation_avatar, cultivation_avatar.world)
        
        # Check can_start
        can_start, reason = action.can_start()
        assert can_start is False
        assert "bottleneck" in reason.lower()
        
        # Force execute (should return early)
        action._execute()
        assert cultivation_avatar.cultivation_progress.exp == initial_exp

    def test_respire_occupied_region(self, cultivation_avatar):
        """Cultivation region occupied by someone else."""
        region = CultivateRegion(id=3, name="Occupied", desc="Full", essence_type=EssenceType.FIRE, essence_density=5)
        other_avatar = MagicMock()
        other_avatar.name = "Stranger"
        region.host_avatar = other_avatar # occupied by someone else
        cultivation_avatar.tile.region = region
        
        action = Respire(cultivation_avatar, cultivation_avatar.world)
        
        can_start, reason = action.can_start()
        assert can_start is False
        assert "Stranger" in reason

    def test_respire_in_sect_headquarter_as_member(self, cultivation_avatar):
        """A sect member respiring at their sect HQ: experience computed as if all five elements were 5."""
        region = SectRegion(
            id=401,
            name="Sect Headquarters",
            desc="Test sect headquarters",
            sect_name="Test Sect",
            sect_id=1,
        )
        cultivation_avatar.tile.region = region

        sect = MagicMock()
        sect.id = 1
        sect.name = "Test Sect"
        cultivation_avatar.sect = sect

        action = Respire(cultivation_avatar, cultivation_avatar.world)
        can_start, reason = action.can_start()
        assert can_start is True
        assert reason == ""

        action._execute()

        expected_exp = 5 * Respire.BASE_EXP_PER_DENSITY
        assert cultivation_avatar.cultivation_progress.exp == expected_exp

    def test_respire_in_sect_headquarter_not_member_forbidden(self, cultivation_avatar):
        """A non-member at another sect's HQ: respiring is forbidden."""
        region = SectRegion(
            id=402,
            name="Other Sect Headquarters",
            desc="Test other sect headquarters",
            sect_name="Other Sect",
            sect_id=2,
        )
        cultivation_avatar.tile.region = region

        sect = MagicMock()
        sect.id = 1
        sect.name = "Own Sect"
        cultivation_avatar.sect = sect

        action = Respire(cultivation_avatar, cultivation_avatar.world)
        can_start, reason = action.can_start()

        assert can_start is False
        # The reason should mention the sect
        assert "sect" in reason.lower()

    def test_respire_with_multiplier(self, cultivation_avatar):
        """Effect of the extra respire experience multiplier."""
        # Base cultivation environment (matching essence)
        region = CultivateRegion(id=4, name="Multiplier Cave", desc="Multiplier", essence_type=EssenceType.FIRE, essence_density=5)
        cultivation_avatar.tile.region = region
        
        # Base experience: 5 * 100 = 500
        base_exp = 5 * Respire.BASE_EXP_PER_DENSITY
        
        # Mock effects to include multiplier
        # Note: the cultivation_avatar fixture already patches effects; we either change that mock's
        # return value or patch it again
        
        with patch.object(cultivation_avatar.__class__, 'effects', new_callable=PropertyMock) as mock_effects:
             # Case 1: 0.5 multiplier (+50%)
            mock_effects.return_value = {"extra_respire_exp_multiplier": 0.5}
            
            action = Respire(cultivation_avatar, cultivation_avatar.world)
            action._execute()
            
            expected_exp_1 = base_exp * (1 + 0.5)
            assert cultivation_avatar.cultivation_progress.exp == expected_exp_1
            
            # Reset exp
            cultivation_avatar.cultivation_progress.exp = 0
            
            # Case 2: 1.0 multiplier (+100%)
            mock_effects.return_value = {"extra_respire_exp_multiplier": 1.0}
            action._execute()
            
            expected_exp_2 = base_exp * (1 + 1.0)
            assert cultivation_avatar.cultivation_progress.exp == expected_exp_2

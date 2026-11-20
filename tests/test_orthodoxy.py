import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from src.classes.core.orthodoxy import get_orthodoxy, orthodoxy_by_id, Orthodoxy
from src.classes.core.sect import Sect, sects_by_id
from src.classes.core.avatar.core import Avatar
from src.classes.action.respire import Respire
from src.systems.cultivation import Realm
EXTRA_RESPIRE_EXP_MULTIPLIER = "extra_respire_exp_multiplier"

class TestOrthodoxyData:
    """Test loading and basic structure of orthodoxy data."""

    def test_orthodoxy_loaded(self):
        """Ensure orthodoxy data is loaded and contains the expected IDs."""
        assert "dao" in orthodoxy_by_id
        assert "buddhism" in orthodoxy_by_id
        assert "confucianism" in orthodoxy_by_id

    def test_orthodoxy_attributes(self):
        """Test orthodoxy object attributes."""
        dao = get_orthodoxy("dao")
        assert dao.id == "dao"
        assert dao.name # Should not be empty
        assert dao.desc # Should not be empty
        assert isinstance(dao.effects, dict)
        
    def test_orthodoxy_info(self):
        """Test the get_info method."""
        buddhism = get_orthodoxy("buddhism")
        info = buddhism.get_info(detailed=False)
        assert "id" in info
        assert "name" in info
        assert "desc" not in info
        
        detailed_info = buddhism.get_info(detailed=True)
        assert "desc" in detailed_info
        assert "effect_desc" in detailed_info

class TestSectIntegration:
    """Test integration between sects and orthodoxies."""

    def test_sect_default_orthodoxy(self):
        """A sect without an explicit orthodoxy defaults to Dao."""
        # Sect ID 1 (High Heaven Sword Sect) has no explicit orthodoxy and should default to dao
        sect_1 = sects_by_id.get(1)
        if sect_1:
            assert sect_1.orthodoxy_id == "dao"

    def test_sect_explicit_orthodoxy(self):
        """Test sects with an explicit orthodoxy."""
        # Sumeru Zen Temple (ID 7) is set to buddhism
        sect_7 = sects_by_id.get(7)
        if sect_7:
            assert sect_7.orthodoxy_id == "buddhism"
            # Check that the buddhism effect exists (legal_actions: ['Meditate'])
            assert "legal_actions" in sect_7.effects
            assert "Meditate" in sect_7.effects["legal_actions"]

        # Haoran Academy (ID 13) is set to confucianism
        sect_13 = sects_by_id.get(13)
        if sect_13:
            assert sect_13.orthodoxy_id == "confucianism"
            assert "legal_actions" in sect_13.effects
            assert "Educate" in sect_13.effects["legal_actions"]

    def test_sect_info_contains_orthodoxy(self):
        """Sect info includes the orthodoxy."""
        sect_7 = sects_by_id.get(7)
        if sect_7:
            info = sect_7.get_info()
            assert "Buddhism" in info
            
            detailed = sect_7.get_detailed_info()
            assert "Buddhism" in detailed

class TestOrthodoxyEffects:
    """Test that orthodoxy effects apply in game logic."""

    def test_respire_exp_multiplier(self, dummy_avatar):
        """Test the cultivation EXP multiplier bonus."""
        # 1. Make the avatar a Dao sect member (or modify effects directly)
        # Mock the effects dict directly since we are testing how Cultivate responds to effects
        
        # Base EXP
        dummy_avatar.cultivation_progress.is_in_bottleneck = MagicMock(return_value=False)
        dummy_avatar.cultivation_progress.add_exp = MagicMock()
        
        action = Respire(dummy_avatar, dummy_avatar.world)
        
        # Mock _get_matched_essence_density to return specific density for predictable base exp
        # BASE_EXP_PER_DENSITY = 100. Let's say density 1. Base exp = 100.
        action._get_matched_essence_density = MagicMock(return_value=1)
        
        with patch.object(Avatar, 'effects', new_callable=PropertyMock) as mock_effects:
            # Case 1: No multiplier
            mock_effects.return_value = {}
            action._execute()
            # Expect 100 exp
            dummy_avatar.cultivation_progress.add_exp.assert_called_with(100)
            
            # Case 2: 0.5 multiplier (Dao)
            mock_effects.return_value = {EXTRA_RESPIRE_EXP_MULTIPLIER: 0.5}
            action._execute()
            # Expect 100 * (1 + 0.5) = 150
            dummy_avatar.cultivation_progress.add_exp.assert_called_with(150)
            
            # Case 3: 1.0 multiplier + extra fixed exp
            mock_effects.return_value = {
                EXTRA_RESPIRE_EXP_MULTIPLIER: 1.0,
                "extra_respire_exp": 50
            }
            action._execute()
            # Base 100 + Extra 50 = 150.
            # Multiplier applies to total exp (base + extra)
            # exp = 150 * (1 + 1.0) = 300
            dummy_avatar.cultivation_progress.add_exp.assert_called_with(300)

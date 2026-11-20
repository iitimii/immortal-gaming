import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from src.classes.core.orthodoxy import get_orthodoxy
from src.classes.action.respire import Respire

class TestRogueCultivatorOrthodoxy:
    """Orthodoxy logic for rogue cultivators (avatars without a sect)."""

    def test_rogue_has_sanxiu_orthodoxy(self, dummy_avatar):
        """Rogue cultivators default to the 'sanxiu' orthodoxy."""
        # Make sure the avatar has no sect
        dummy_avatar.sect = None
        
        # Check the orthodoxy attribute
        orthodoxy = dummy_avatar.orthodoxy
        assert orthodoxy is not None
        assert orthodoxy.id == "sanxiu"
        assert orthodoxy.name == "ORTHODOXY_SANXIU_NAME"

    def test_rogue_effects_include_sanxiu(self, dummy_avatar):
        """Rogue cultivator effects include the sanxiu orthodoxy effects."""
        dummy_avatar.sect = None
        
        # Recompute effects (effects is a dynamic property, but read it explicitly to be safe)
        effects = dummy_avatar.effects
        
        # Check legal_actions
        assert "legal_actions" in effects
        legal_actions = effects["legal_actions"]
        assert "Respire" in legal_actions
        
    def test_rogue_can_cultivate(self, dummy_avatar):
        """Rogue cultivators can perform the cultivation action."""
        dummy_avatar.sect = None
        
        # Create the cultivation action
        action = Respire(dummy_avatar, dummy_avatar.world)
        
        # Simulate passing the bottleneck check
        dummy_avatar.cultivation_progress.can_cultivate = MagicMock(return_value=True)
        
        # Check can_start
        can_start, reason = action.can_start()
        assert can_start is True
        assert reason == ""

    def test_rogue_cannot_meditate_by_default(self, dummy_avatar):
        """Rogue cultivators cannot meditate by default (meditation is Buddhist-only)."""
        dummy_avatar.sect = None
        
        # The Meditate action checks the 'Meditate' permission;
        # inspect effects manually to mirror that logic
        effects = dummy_avatar.effects
        legal_actions = effects.get("legal_actions", [])
        
        # Rogue cultivators should have Respire but not Meditate
        assert "Respire" in legal_actions
        assert "Meditate" not in legal_actions

    def test_join_sect_overrides_sanxiu(self, dummy_avatar):
        """Joining a sect replaces the sanxiu orthodoxy with the sect orthodoxy."""
        # Mock a Buddhist sect
        mock_sect = MagicMock()
        mock_sect.name = "Test Buddhism Sect"
        mock_sect.orthodoxy_id = "buddhism"
        mock_sect.effects = {"legal_actions": ["Meditate"]} # effects provided by the sect
        
        # Join the sect
        dummy_avatar.sect = mock_sect
        
        # Check the orthodoxy attribute
        assert dummy_avatar.orthodoxy.id == "buddhism"
        
        # Check effects.
        # This relies on the effects mixin: when self.sect exists it reads
        # self.sect.effects instead of the sanxiu orthodoxy effects.
        # dummy_avatar is a real Avatar (with some mocked parts), so the
        # get_effect_breakdown logic runs for real as long as mock_sect
        # behaves like a real sect.

        # Re-assign the sect to ensure a clean state
        dummy_avatar.sect = mock_sect
        
        # Check effects
        effects = dummy_avatar.effects
        legal_actions = effects.get("legal_actions", [])
        
        # Should carry the Buddhist effects
        assert "Meditate" in legal_actions
        # The sanxiu Respire permission should be gone (Buddhism is configured with Meditate)
        assert "Respire" not in legal_actions

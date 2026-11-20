import pytest
from unittest.mock import MagicMock
from src.classes.nickname import can_get_nickname
from src.classes.nickname_data import Nickname
from src.utils.config import CONFIG

class TestNicknameRenewal:
    """Test nickname renewal: one new nickname per decade."""

    def test_nickname_renewal_logic(self, dummy_avatar):
        """Test nickname eligibility over time for an avatar that already has one."""
        
        # 0. Mock config: lower the thresholds to simplify the test
        CONFIG.nickname.major_event_threshold = 1
        CONFIG.nickname.minor_event_threshold = 1
        
        # Mock the event manager so it always returns enough events
        dummy_avatar.world.event_manager.get_major_events_by_avatar = MagicMock(return_value=[1])
        dummy_avatar.world.event_manager.get_minor_events_by_avatar = MagicMock(return_value=[1])

        # 1. Initial state: no nickname -> eligible (True)
        assert dummy_avatar.nickname is None
        assert can_get_nickname(dummy_avatar) is True

        # 2. Grant an initial nickname created in the current year (Year 1)
        current_year = dummy_avatar.world.month_stamp.get_year()  # Year 1
        dummy_avatar.nickname = Nickname(value="Fledgling", reason="test", created_year=current_year)
        
        # 3. Same year the nickname was granted -> not eligible (False)
        assert can_get_nickname(dummy_avatar) is False

        # 4. Five years later (Year 6) -> 5-year gap -> not eligible (False)
        dummy_avatar.world.month_stamp += 12 * 5
        assert dummy_avatar.world.month_stamp.get_year() - current_year == 5
        assert can_get_nickname(dummy_avatar) is False

        # 5. Nine years later (Year 10) -> 9-year gap -> not eligible (False)
        dummy_avatar.world.month_stamp += 12 * 4
        assert dummy_avatar.world.month_stamp.get_year() - current_year == 9
        assert can_get_nickname(dummy_avatar) is False

        # 6. Ten years later (Year 11) -> 10-year gap -> eligible (True)
        dummy_avatar.world.month_stamp += 12 * 1
        assert dummy_avatar.world.month_stamp.get_year() - current_year == 10
        assert can_get_nickname(dummy_avatar) is True

        # 7. Eleven years later (Year 12) -> 11-year gap -> eligible (True)
        dummy_avatar.world.month_stamp += 12 * 1
        assert dummy_avatar.world.month_stamp.get_year() - current_year == 11
        assert can_get_nickname(dummy_avatar) is True

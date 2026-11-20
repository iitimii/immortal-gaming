import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from src.classes.action.play import Reading, TeaTasting, Traveling, ZitherPlaying
from src.classes.mutual_action.play import TeaParty, Chess
from src.classes.event import Event
from src.utils.config import CONFIG

class TestActionPlay:
    
    @pytest.fixture
    def play_avatar(self, dummy_avatar):
        """Configure an avatar suitable for leisure actions."""
        # Make sure there are no initial temporary effects
        dummy_avatar.temporary_effects = []
        return dummy_avatar

    def test_single_play_action_instantiation(self, play_avatar):
        """Solo leisure actions can be instantiated."""
        world = play_avatar.world
        actions = [Reading, TeaTasting, Traveling, ZitherPlaying]
        
        for action_cls in actions:
            action = action_cls(play_avatar, world)
            assert action.duration_months == 1
            assert action.can_start()[0] is True

    @patch('src.classes.action.play.random.random')
    def test_single_play_benefit_trigger(self, mock_random, play_avatar):
        """Solo leisure action triggers its benefit."""
        # mock random < 0.05 to trigger benefit
        # CONFIG.play.base_benefit_probability is 0.05
        mock_random.return_value = 0.01 
        
        action = Reading(play_avatar, play_avatar.world)
        
        # Execute finish (async)
        events = asyncio.run(action.finish())
        
        # Check event content
        assert len(events) == 1
        # The event should mention the breakthrough-rate boost.
        # conftest.py force_default_language fixture sets language to the default locale (en-US).
        assert "20.0%" in events[0].content
        
        # Check effect applied
        # Need to check if temporary_effects has the entry
        assert len(play_avatar.temporary_effects) == 1
        effect = play_avatar.temporary_effects[0]
        assert effect["source"] == "play_benefit"
        assert effect["effects"]["extra_breakthrough_success_rate"] == 0.2
        assert effect["duration"] == 1

    @patch('src.classes.action.play.random.random')
    def test_single_play_no_benefit(self, mock_random, play_avatar):
        """Solo leisure action does not trigger its benefit."""
        # mock random >= 0.05
        mock_random.return_value = 0.1 
        
        action = Reading(play_avatar, play_avatar.world)
        
        events = asyncio.run(action.finish())
        
        assert len(events) == 1
        assert "20.0%" not in events[0].content
        assert len(play_avatar.temporary_effects) == 0

    @patch('src.classes.mutual_action.play.random.random')
    def test_mutual_play_benefit(self, mock_random, play_avatar):
        """Mutual leisure action triggers its benefit."""
        # Setup target avatar
        target_avatar = MagicMock()
        target_avatar.name = "Friend"
        # MagicMock doesn't have temporary_effects list by default, but add_breakthrough_rate is called on it
        
        # mock random < 0.05
        mock_random.return_value = 0.01
        
        action = TeaParty(play_avatar, play_avatar.world)
        
        # Simulate response "Accept"
        action._settle_response(target_avatar, "Accept")
        
        # Check initiator benefit
        assert len(play_avatar.temporary_effects) == 1
        assert play_avatar.temporary_effects[0]["effects"]["extra_breakthrough_success_rate"] == 0.2
        
        # Check target benefit
        target_avatar.add_breakthrough_rate.assert_called_with(0.2)

    @patch('src.classes.mutual_action.play.StoryEventService.maybe_create_story', new_callable=AsyncMock)
    def test_tea_party_finish_returns_result_event(self, mock_story, play_avatar):
        """Tea party produces a result event on finish."""
        mock_story.return_value = None

        target_avatar = MagicMock()
        target_avatar.name = "Friend"
        target_avatar.id = "target-id"

        action = TeaParty(play_avatar, play_avatar.world)
        action._settle_response(target_avatar, "Accept")

        events = asyncio.run(action.finish(target_avatar))

        assert len(events) == 1
        assert isinstance(events[0], Event)
        assert play_avatar.name in events[0].content
        assert target_avatar.name in events[0].content
        assert events[0].related_avatars == [play_avatar.id, target_avatar.id]

    @patch('src.classes.mutual_action.play.StoryEventService.maybe_create_story', new_callable=AsyncMock)
    def test_chess_finish_returns_result_event(self, mock_story, play_avatar):
        """Chess produces a result event on finish."""
        mock_story.return_value = None

        target_avatar = MagicMock()
        target_avatar.name = "Friend"
        target_avatar.id = "target-id"

        action = Chess(play_avatar, play_avatar.world)
        action._settle_response(target_avatar, "Accept")

        events = asyncio.run(action.finish(target_avatar))

        assert len(events) == 1
        assert isinstance(events[0], Event)
        assert play_avatar.name in events[0].content
        assert target_avatar.name in events[0].content
        assert events[0].related_avatars == [play_avatar.id, target_avatar.id]

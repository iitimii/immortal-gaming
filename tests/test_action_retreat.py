
import pytest
from unittest.mock import MagicMock, patch, ANY, AsyncMock
from src.classes.action.retreat import Retreat
from src.classes.action_runtime import ActionStatus
from src.systems.cultivation import Realm
from src.i18n import t

class TestActionRetreat:
    
    @pytest.fixture
    def retreat_avatar(self, dummy_avatar):
        """Set up an avatar environment suitable for retreat."""
        # Qi Refinement, base breakthrough probability 0.5
        dummy_avatar.cultivation_progress.realm = Realm.Qi_Refinement
        
        # Make sure the temporary_effects list exists (init should already create it)
        if not hasattr(dummy_avatar, "temporary_effects"):
            dummy_avatar.temporary_effects = []
            
        return dummy_avatar

    def test_retreat_init(self, retreat_avatar):
        """Retreat action initialization."""
        action = Retreat(retreat_avatar, retreat_avatar.world)
        
        # Duration should be within 12-60 months
        assert 12 <= action.duration_months <= 60
        # It should be a major event
        assert action.IS_MAJOR is True
        
        # It should be startable
        can_start, reason = action.can_start()
        assert can_start is True

    @pytest.mark.asyncio
    async def test_retreat_success(self, retreat_avatar):
        """Retreat succeeds."""
        action = Retreat(retreat_avatar, retreat_avatar.world)
        action.duration_months = 24
        
        # Mock randomness so that random.random() < success_rate (0.5)
        # calc_success_rate for Qi_Refinement is 0.5 (0.5 - 0*0.1)
        # So we need random < 0.5
        with patch('random.random', return_value=0.1), \
             patch('src.classes.story_event_service.StoryEventService.should_trigger', return_value=True), \
             patch('src.classes.story_event_service.StoryTeller.tell_story', new_callable=AsyncMock, return_value="Great story"):
            
            # Start
            start_event = action.start()
            assert start_event is not None
            
            # Finish
            events = await action.finish()
            
            # Verify the event is generated
            assert len(events) >= 2
            assert any("successfully" in str(e) for e in events)
            
            # Verify a temporary effect was granted
            assert len(retreat_avatar.temporary_effects) == 1
            effect = retreat_avatar.temporary_effects[0]
            assert effect["source"] == "Retreat Bonus"
            assert effect["effects"]["extra_breakthrough_success_rate"] > 0
            assert effect["duration"] == 120 # 10 years
            
            # Verify attribute recomputation (effects should include the bonus).
            # effects are computed dynamically; as long as temporary_effects holds it and
            # EffectsMixin works, avatar.effects will expose it.
            
            # Only verify the temporary_effects structure here; EffectsMixin is covered by its own tests
            pass

    @pytest.mark.asyncio
    async def test_retreat_fail(self, retreat_avatar):
        """Retreat fails."""
        action = Retreat(retreat_avatar, retreat_avatar.world)
        action.duration_months = 36
        
        original_lifespan = retreat_avatar.age.max_lifespan
        
        # Mock randomness so that random.random() >= success_rate (0.5)
        # random.randint used for reduce_years (5, 20)
        with patch('random.random', return_value=0.9), \
             patch('random.randint', side_effect=[10]), \
             patch('src.classes.story_event_service.StoryEventService.should_trigger', return_value=True), \
             patch('src.classes.story_event_service.StoryTeller.tell_story', new_callable=AsyncMock, return_value="Sad story"):
            
            # Finish
            events = await action.finish()
            
            # Verify the event
            assert len(events) >= 2
            assert any("failed" in str(e) for e in events)
            
            # Verify there is no temporary effect
            assert len(retreat_avatar.temporary_effects) == 0
            assert len(retreat_avatar.persistent_effects) == 1
            persistent = retreat_avatar.persistent_effects[0]
            assert persistent["source"] == "effect_source_retreat_failure"
            assert persistent["effects"]["extra_max_lifespan"] == -10

            # Verify lifespan is reduced (mocked to reduce 10)
            assert retreat_avatar.age.max_lifespan == original_lifespan - 10

    def test_calc_success_rate(self, retreat_avatar):
        """Success rate calculation."""
        action = Retreat(retreat_avatar, retreat_avatar.world)
        
        # Qi Refinement: 0.5 - 0 = 0.5
        retreat_avatar.cultivation_progress.realm = Realm.Qi_Refinement
        assert action.calc_success_rate() == 0.5
        
        # Foundation: 0.5 - 0.1 = 0.4
        retreat_avatar.cultivation_progress.realm = Realm.Foundation_Establishment
        assert action.calc_success_rate() == 0.4
        
        # Core Formation: 0.5 - 0.2 = 0.3
        retreat_avatar.cultivation_progress.realm = Realm.Core_Formation
        assert action.calc_success_rate() == 0.3
        
        # Nascent Soul: 0.5 - 0.3 = 0.2
        retreat_avatar.cultivation_progress.realm = Realm.Nascent_Soul
        assert action.calc_success_rate() == pytest.approx(0.2)

    def test_retreat_isolation(self, retreat_avatar):
        """Retreat isolation (no gatherings, no fortune events)."""
        action = Retreat(retreat_avatar, retreat_avatar.world)
        
        # 1. Verify the Action class attributes
        assert action.ALLOW_GATHERING is False
        assert action.ALLOW_WORLD_EVENTS is False
        
        # 2. Verify the Avatar state check
        # Simulate the avatar currently in retreat
        from src.classes.action_runtime import ActionInstance
        retreat_avatar.current_action = ActionInstance(action=action, params={}, status="running")
        
        assert retreat_avatar.can_join_gathering is False
        assert retreat_avatar.can_trigger_world_event is False
        
        # 3. Verify normal state after the action is cleared
        retreat_avatar.current_action = None
        assert retreat_avatar.can_join_gathering is True
        assert retreat_avatar.can_trigger_world_event is True


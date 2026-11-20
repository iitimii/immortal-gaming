import pytest
from unittest.mock import patch, MagicMock
from src.classes.action.attack import Attack
from src.classes.event import Event
from src.systems.cultivation import Realm
from src.classes.core.avatar import Avatar

# A simple resolution-result mock
class MockResolutionResult:
    def __init__(self, obj):
        self.obj = obj

def test_attack_can_start_success(dummy_avatar):
    """Attack precondition check passes."""
    target = MagicMock(spec=Avatar)
    target.name = "TargetAvatar"
    target.is_dead = False
    
    with patch("src.classes.action.attack.resolve_query") as mock_resolve:
        mock_resolve.return_value = MockResolutionResult(target)
        
        action = Attack(dummy_avatar, dummy_avatar.world)
        can_start, reason = action.can_start("TargetAvatar")
        
        assert can_start is True
        assert reason == ""

def test_attack_can_start_fail_no_target(dummy_avatar):
    """Target does not exist."""
    with patch("src.classes.action.attack.resolve_query") as mock_resolve:
        mock_resolve.return_value = MockResolutionResult(None)
        
        action = Attack(dummy_avatar, dummy_avatar.world)
        can_start, reason = action.can_start("Ghost")
        
        assert can_start is False
        assert "Target does not exist" in reason

def test_attack_can_start_fail_dead_target(dummy_avatar):
    """Target is already dead."""
    target = MagicMock(spec=Avatar)
    target.is_dead = True
    
    with patch("src.classes.action.attack.resolve_query") as mock_resolve:
        mock_resolve.return_value = MockResolutionResult(target)
        
        action = Attack(dummy_avatar, dummy_avatar.world)
        can_start, reason = action.can_start("Zombie")
        
        assert can_start is False
        assert "Target is already dead" in reason

def test_attack_start_event(dummy_avatar):
    """Event generated when an attack starts."""
    target = MagicMock(spec=Avatar)
    target.name = "Enemy"
    target.id = "enemy-id"
    
    # Mock combat strength calculation
    with patch("src.classes.action.attack.resolve_query") as mock_resolve, \
         patch("src.classes.action.attack.get_effective_strength_pair") as mock_strength:
        
        mock_resolve.return_value = MockResolutionResult(target)
        mock_strength.return_value = (100, 80)
        
        action = Attack(dummy_avatar, dummy_avatar.world)
        event = action.start("Enemy")
        
        assert isinstance(event, Event)
        assert "TestDummy" in event.content
        assert "Enemy" in event.content
        assert "100" in event.content # combat strength shown
        assert event.is_major is False

def test_attack_execute_logic(dummy_avatar):
    """Combat execution logic."""
    target = MagicMock(spec=Avatar)
    target.name = "Enemy"
    
    # Setup HP mocks
    dummy_avatar.hp = MagicMock()
    target.hp = MagicMock()
    
    # Setup proficiency mocks (methods on MagicMock)
    dummy_avatar.increase_weapon_proficiency = MagicMock()
    target.increase_weapon_proficiency = MagicMock()

    with patch("src.classes.action.attack.resolve_query") as mock_resolve, \
         patch("src.classes.action.attack.decide_battle") as mock_decide:
        
        mock_resolve.return_value = MockResolutionResult(target)
        
        # winner, loser, loser_damage, winner_damage
        # Assume dummy_avatar wins
        mock_decide.return_value = (dummy_avatar, target, 50, 10)
        
        action = Attack(dummy_avatar, dummy_avatar.world)
        action._execute("Enemy")
        
        # Verify damage is applied
        # loser (target) takes 50 dmg
        target.hp.reduce.assert_called_with(50)
        # winner (dummy) takes 10 dmg
        dummy_avatar.hp.reduce.assert_called_with(10)
        
        # Verify proficiency increases
        assert dummy_avatar.increase_weapon_proficiency.called
        assert target.increase_weapon_proficiency.called
        
        # Verify the result is stored
        assert action._last_result == (dummy_avatar, target, 50, 10)

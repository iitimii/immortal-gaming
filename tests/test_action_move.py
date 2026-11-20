
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from src.classes.action.move import Move
from src.classes.environment.tile import TileType
from src.classes.action_runtime import ActionStatus

class TestActionMove:
    
    def test_move_basic(self, dummy_avatar):
        """Basic movement: move one tile to the right."""
        # Starting position (0, 0)
        assert dummy_avatar.pos_x == 0
        assert dummy_avatar.pos_y == 0
        
        # Default step length is 1; (1, 0) is always within the Manhattan limit
        # enforced by clamp_manhattan_with_diagonal_priority.
        
        action = Move(dummy_avatar, dummy_avatar.world)
        action.execute(delta_x=1, delta_y=0)
        
        assert dummy_avatar.pos_x == 1
        assert dummy_avatar.pos_y == 0
        assert dummy_avatar.tile.x == 1
        assert dummy_avatar.tile.y == 0

    def test_move_out_of_bounds(self, dummy_avatar):
        """Boundary movement: try to move off the map (to the left)."""
        # Start at (0, 0)
        action = Move(dummy_avatar, dummy_avatar.world)
        action.execute(delta_x=-1, delta_y=0)
        
        # Should still be at (0, 0)
        assert dummy_avatar.pos_x == 0
        assert dummy_avatar.pos_y == 0

    def test_move_with_increased_step(self, dummy_avatar):
        """Movement with an increased step length."""
        # Increase the step length
        with patch.object(type(dummy_avatar), 'move_step_length', new_callable=PropertyMock) as mock_step:
            mock_step.return_value = 3
            
            action = Move(dummy_avatar, dummy_avatar.world)
            # Try to move (0, 3)
            action.execute(delta_x=0, delta_y=3)
            
            assert dummy_avatar.pos_x == 0
            assert dummy_avatar.pos_y == 3

    def test_move_clamped_by_step(self, dummy_avatar):
        """Step limit: try to move farther than the step length."""
        with patch.object(type(dummy_avatar), 'move_step_length', new_callable=PropertyMock) as mock_step:
            mock_step.return_value = 1
            
            action = Move(dummy_avatar, dummy_avatar.world)
            # Try to move (5, 0)
            action.execute(delta_x=5, delta_y=0)
            
            # Should only have moved 1 tile to (1, 0)
            assert dummy_avatar.pos_x == 1
            assert dummy_avatar.pos_y == 0


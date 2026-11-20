import pytest
import copy
from unittest.mock import patch, MagicMock
from src.classes.relation.relation import Relation
from src.classes.core.avatar import Gender
from src.utils.config import CONFIG
from src.sim.simulator import Simulator
from src.sim.simulator_engine.phases.lifecycle import phase_update_age_and_birth
from src.systems.time import MonthStamp

def test_couple_birth_logic(base_world, dummy_avatar):
    """
    Test the Dao-companion childbirth logic:
    1. Establish the relation
    2. Check the time restriction
    3. Check that a child is generated
    4. Check the child count limit
    """
    # 1. Prepare the parents
    father = dummy_avatar
    father.gender = Gender.MALE
    father.name = "Zhang San"
    
    # Register father with avatar_manager
    base_world.avatar_manager.register_avatar(father)
    
    # Create mother
    mother = copy.deepcopy(dummy_avatar)
    mother.id = "mother_id"
    mother.gender = Gender.FEMALE
    mother.name = "Li Si"
    # Clear data that may have been copied over
    mother.children = []
    mother.relation_start_dates = {}
    mother.relations = {}
    
    base_world.avatar_manager.register_avatar(mother)
    
    # 2. Establish the relation and backdate it
    father.become_lovers_with(mother)
    
    # The relation start time is recorded
    current_time = int(base_world.month_stamp)
    assert father.relation_start_dates[mother.id] == current_time
    assert mother.relation_start_dates[father.id] == current_time
    
    # Move the start time back 13 months to satisfy the > 12 month condition
    start_time = current_time - 13
    father.relation_start_dates[mother.id] = start_time
    mother.relation_start_dates[father.id] = start_time
    
    # 3. Mock config and probability so birth is guaranteed
    CONFIG.world.birth_rate_per_month = 1.0
    CONFIG.world.max_children_per_couple = 1
    
    # 4. Run the simulator phase
    sim = Simulator(base_world)
    
    # The first run should produce one child
    # Keep awakening_rate at 0 to avoid interference
    sim.awakening_rate = 0
    
    with patch("random.random", return_value=0.0): # make the probability roll pass
        living_avatars = base_world.avatar_manager.get_living_avatars()
        events = phase_update_age_and_birth(base_world, living_avatars)
        
    # 5. Verify the result
    assert len(father.children) == 1
    child = father.children[0]
    
    # Name: takes the father's surname (Zhang)
    assert child.name.startswith("Zhang ")
    
    # Bidirectional binding
    assert child in mother.children
    assert str(father.id) in child.parents
    assert str(mother.id) in child.parents
    
    # Birth event
    birth_events = [e for e in events if "gave birth to a" in str(e)]
    assert len(birth_events) > 0
    
    # 6. Limit: a second run adds nothing because max_children_per_couple = 1
    with patch("random.random", return_value=0.0):
        living_avatars = base_world.avatar_manager.get_living_avatars()
        phase_update_age_and_birth(base_world, living_avatars)
        
    assert len(father.children) == 1
    
def test_birth_time_restriction(base_world, dummy_avatar):
    """
    Time restriction: no child before the relation is one year old
    """
    father = dummy_avatar
    base_world.avatar_manager.register_avatar(father)
    
    mother = copy.deepcopy(dummy_avatar)
    mother.id = "mother_id_2"
    base_world.avatar_manager.register_avatar(mother)
    
    father.become_lovers_with(mother)
    
    # The relation was just established, less than a year ago
    CONFIG.world.birth_rate_per_month = 1.0
    sim = Simulator(base_world)
    sim.awakening_rate = 0
    
    with patch("random.random", return_value=0.0):
        living_avatars = base_world.avatar_manager.get_living_avatars()
        phase_update_age_and_birth(base_world, living_avatars)
        
    assert len(father.children) == 0


import pytest
from unittest.mock import MagicMock

from src.classes.death_reason import DeathReason, DeathType
from src.classes.death import handle_death
from src.classes.relation.relation import Relation, get_relations_strs
from src.classes.event import Event

def test_death_reason_str():
    """Test string formatting of death reasons."""
    # Killed in battle
    reason_battle = DeathReason(DeathType.BATTLE, killer_name="Zhang San")
    assert str(reason_battle) == "Killed by Zhang San"
    
    # Killed in battle (unknown killer)
    reason_battle_unknown = DeathReason(DeathType.BATTLE)
    assert str(reason_battle_unknown) == "Killed by Unknown character"
    
    # Serious injury
    reason_injury = DeathReason(DeathType.SERIOUS_INJURY)
    assert str(reason_injury) == "Died from severe injuries"
    
    # Old age
    reason_old = DeathReason(DeathType.OLD_AGE)
    assert str(reason_old) == "Died of old age"

def test_handle_death(base_world, dummy_avatar):
    """Test the death handler (integration: archiving and buffering)."""
    reason = DeathReason(DeathType.BATTLE, killer_name="Li Si")
    
    # Make sure the avatar is in the manager
    base_world.avatar_manager.register_avatar(dummy_avatar)
    assert dummy_avatar.id in base_world.avatar_manager.avatars
    
    # Handle the death
    handle_death(base_world, dummy_avatar, reason)
    
    # 1. Object state
    assert dummy_avatar.is_dead is True
    assert dummy_avatar.death_info is not None
    assert dummy_avatar.death_info["reason"] == "Killed by Li Si"
    assert dummy_avatar.death_info["time"] == int(base_world.month_stamp)
    
    # 2. Manager state (archived)
    assert dummy_avatar.id not in base_world.avatar_manager.avatars
    assert dummy_avatar.id in base_world.avatar_manager.dead_avatars
    
    # 3. Buffer (for frontend push)
    newly_dead = base_world.avatar_manager.pop_newly_dead()
    assert str(dummy_avatar.id) in newly_dead
    
    # 4. Buffer is cleared
    assert len(base_world.avatar_manager.pop_newly_dead()) == 0

def test_relation_display_with_death(base_world, dummy_avatar):
    """Test how deaths are displayed in the relation list."""
    # Create another avatar as a friend
    from src.classes.core.avatar import Avatar, Gender
    from src.classes.age import Age
    from src.systems.cultivation import Realm
    from src.utils.id_generator import get_avatar_id
    from src.classes.root import Root
    from src.classes.alignment import Alignment
    from src.systems.time import create_month_stamp, Year, Month
    
    friend = Avatar(
        world=base_world,
        name="Friend",
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
        age=Age(20, Realm.Qi_Refinement),
        gender=Gender.MALE,
        pos_x=0, pos_y=0,
        root=Root.WOOD,
        alignment=Alignment.RIGHTEOUS
    )
    # Register the friend
    base_world.avatar_manager.register_avatar(friend)
    
    # Establish the relation
    dummy_avatar.make_friend_with(friend)
    
    # Initially: the plain name is shown
    strs_before = get_relations_strs(dummy_avatar)
    assert "Friendly: Friend" in strs_before
    
    # The friend dies (serious injury)
    reason = DeathReason(DeathType.SERIOUS_INJURY)
    handle_death(base_world, friend, reason)
    
    # After death: the name is shown with the cause of death
    strs_after = get_relations_strs(dummy_avatar)
    assert "Friendly: Friend (Deceased: Died from severe injuries)" in strs_after
    assert friend not in dummy_avatar.relations
    assert friend in dummy_avatar.archived_relations
    assert dummy_avatar not in friend.relations
    assert dummy_avatar in friend.archived_relations


def test_death_archives_master_relation_and_clears_active_graph(base_world, dummy_avatar):
    from src.classes.core.avatar import Avatar, Gender
    from src.classes.age import Age
    from src.systems.cultivation import Realm
    from src.utils.id_generator import get_avatar_id
    from src.classes.root import Root
    from src.classes.alignment import Alignment
    from src.systems.time import create_month_stamp, Year, Month

    master = Avatar(
        world=base_world,
        name="Master",
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(1990), Month.JANUARY),
        age=Age(50, Realm.Foundation_Establishment),
        gender=Gender.MALE,
        pos_x=1, pos_y=1,
        root=Root.WOOD,
        alignment=Alignment.RIGHTEOUS,
    )
    base_world.avatar_manager.register_avatar(master)
    dummy_avatar.acknowledge_master(master)

    assert master in dummy_avatar.relations
    handle_death(base_world, master, DeathReason(DeathType.OLD_AGE))

    assert master not in dummy_avatar.relations
    assert master in dummy_avatar.archived_relations
    assert dummy_avatar not in master.relations
    assert dummy_avatar in master.archived_relations
    assert master.sect is None
    assert master.death_info["sect_name_at_death"] == ""


def test_structured_relations_mark_archived_scope_after_death(base_world, dummy_avatar):
    from src.classes.core.avatar import Avatar, Gender
    from src.classes.age import Age
    from src.systems.cultivation import Realm
    from src.utils.id_generator import get_avatar_id
    from src.classes.root import Root
    from src.classes.alignment import Alignment
    from src.systems.time import create_month_stamp, Year, Month

    friend = Avatar(
        world=base_world,
        name="Friend",
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
        age=Age(20, Realm.Qi_Refinement),
        gender=Gender.MALE,
        pos_x=0,
        pos_y=0,
        root=Root.WOOD,
        alignment=Alignment.RIGHTEOUS,
    )
    base_world.avatar_manager.register_avatar(friend)
    dummy_avatar.make_friend_with(friend)

    handle_death(base_world, friend, DeathReason(DeathType.SERIOUS_INJURY))

    relations = dummy_avatar.get_structured_info()["relations"]
    archived_entry = next(item for item in relations if item["target_id"] == friend.id)
    assert archived_entry["relation_scope"] == "archived"
    assert archived_entry["numeric_relation"] == "friend"
    assert archived_entry["is_dead"] is True


def test_avatar_manager_archive_death(base_world, dummy_avatar):
    """Test AvatarManager's death archiving logic."""
    manager = base_world.avatar_manager
    manager.register_avatar(dummy_avatar)
    
    # Initially in the living table
    assert dummy_avatar.id in manager.avatars
    assert dummy_avatar.id not in manager.dead_avatars
    
    # Archive
    manager.handle_death(dummy_avatar.id)
    
    # Moved to the dead table
    assert dummy_avatar.id not in manager.avatars
    assert dummy_avatar.id in manager.dead_avatars
    
    # get_avatar still finds it
    assert manager.get_avatar(dummy_avatar.id) == dummy_avatar
    
    # Buffer
    assert str(dummy_avatar.id) in manager.pop_newly_dead()


def test_registering_an_already_dead_avatar_creates_a_grave(base_world, dummy_avatar):
    manager = base_world.avatar_manager
    dummy_avatar.set_dead("Died of old age", base_world.month_stamp)

    manager.register_avatar(dummy_avatar, is_newly_born=True)

    assert dummy_avatar.id not in manager.avatars
    assert dummy_avatar.id in manager.dead_avatars
    assert base_world.deceased_manager.get_record(dummy_avatar.id) is not None
    graves = base_world.poi_manager.get_all_active(int(base_world.month_stamp))
    assert len(graves) == 1
    assert graves[0].deceased_avatar_id == dummy_avatar.id
    assert graves[0].get_summary_payload()["deceased_avatar_id"] == dummy_avatar.id
    assert str(dummy_avatar.id) in manager.pop_newly_dead()

@pytest.mark.asyncio
async def test_simulator_resolve_death(base_world, dummy_avatar):
    """Test the simulator's death resolution phase."""
    from src.sim.simulator_engine.phases.lifecycle import phase_resolve_death
    base_world.avatar_manager.register_avatar(dummy_avatar)
    
    # Case 1: death from serious injury
    dummy_avatar.hp.cur = -10
    
    # Resolve deaths
    events = phase_resolve_death(base_world, [dummy_avatar])
    
    # Verify
    assert dummy_avatar.is_dead is True
    assert dummy_avatar.death_info["reason"] == "Died from severe injuries"
    assert len(events) > 0
    assert "Died from severe injuries" in str(events[0])
    
    # Archived automatically (handle_death now calls manager.handle_death)
    assert dummy_avatar.id in base_world.avatar_manager.dead_avatars
    assert str(dummy_avatar.id) in base_world.avatar_manager.pop_newly_dead()


def test_death_phase_repairs_previously_marked_dead_avatar(base_world, dummy_avatar):
    from src.sim.simulator_engine.phases.lifecycle import phase_resolve_death

    dummy_avatar.set_dead("Legacy save death state", base_world.month_stamp)
    base_world.avatar_manager.avatars[dummy_avatar.id] = dummy_avatar

    events = phase_resolve_death(base_world, [dummy_avatar])

    assert events == []
    assert dummy_avatar.id not in base_world.avatar_manager.avatars
    assert dummy_avatar.id in base_world.avatar_manager.dead_avatars
    graves = base_world.poi_manager.get_all_active(int(base_world.month_stamp))
    assert len(graves) == 1
    assert graves[0].deceased_avatar_id == dummy_avatar.id

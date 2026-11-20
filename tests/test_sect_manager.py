import math
import pytest
from pathlib import Path
from unittest.mock import patch
from src.classes.core.world import World
from src.classes.core.sect import Sect, SectHeadQuarter
from src.classes.core.avatar.core import Avatar
from src.classes.alignment import Alignment
from src.classes.age import Age
from src.systems.time import MonthStamp
from src.sim.managers.sect_manager import SectManager
from src.classes.event import Event
from src.classes.gender import Gender
from src.systems.battle import get_base_strength
from src.systems.cultivation import CultivationProgress
from src.classes.sect_ranks import SectRank

@pytest.fixture
def mock_world(base_world):
    """Build a world with two sects on top of the standard base_world."""

    world: World = base_world
    game_map = world.map

    # Register a SectRegion only for sect1 so it has an influence center and income; sect2 has no HQ so its income is 0
    from src.classes.environment.sect_region import SectRegion
    r1_id = 1001
    cors1 = [(0, 0)]
    r1 = SectRegion(id=r1_id, name="R1", desc="", sect_id=1, sect_name="Test Sect 1", cors=cors1)
    game_map.regions[r1_id] = r1
    game_map.region_cors[r1_id] = cors1
    game_map.update_sect_regions()

    hq = SectHeadQuarter(name="Test HQ", desc="", image=Path(""))
    sect1 = Sect(
        id=1,
        name="Test Sect 1",
        desc="",
        member_act_style="",
        alignment=Alignment.NEUTRAL,
        headquarter=hq,
        technique_names=[],
    )
    sect2 = Sect(
        id=2,
        name="Test Sect 2",
        desc="",
        member_act_style="",
        alignment=Alignment.NEUTRAL,
        headquarter=hq,
        technique_names=[],
    )

    world.existed_sects = [sect1, sect2]
    # Also record the enabled sects in SectContext so SectManager can read them
    world.sect_context.from_existed_sects(world.existed_sects)
    return world

def create_mock_avatar(world, name, sect, battle_strength=None):
    # Build a simplified Avatar by hand; battle_strength is only used when patched for assertions, real strength comes from get_base_strength
    avatar = Avatar(
        world=world,
        name=name,
        id=f"avatar_{name}",
        birth_month_stamp=MonthStamp(1),
        age=Age(18, realm=0),
        gender=Gender.MALE
    )
    if battle_strength is not None:
        avatar.base_battle_strength = battle_strength  # only used as the patched return value in test_sect_manager_update
    if sect:
        avatar.join_sect(sect, SectRank.OuterDisciple)
    return avatar

def test_sect_manager_update(mock_world):
    """Sect total strength, influence radius, and per-tile spirit stone income (matches the old logic when there is no conflict)."""
    sect1 = mock_world.existed_sects[0]
    sect2 = mock_world.existed_sects[1]
    manager = SectManager(mock_world)

    a1 = create_mock_avatar(mock_world, "Zhang San", sect1, 100)
    a2 = create_mock_avatar(mock_world, "Li Si", sect1, 120)
    a1.is_dead = False
    a2.is_dead = False
    mock_world.avatar_manager.avatars[a1.id] = a1
    mock_world.avatar_manager.avatars[a2.id] = a2

    # SectManager uses get_base_strength(avatar); patch it to fixed values to assert the formula
    with patch("src.sim.managers.sect_manager.get_base_strength", side_effect=[100.0, 120.0]):
        events = manager.update_sects()
    
    # sect1 data
    # Formula: max_str + log(sum(exp(s - max_str)))
    # max_str = 120
    # s1 = 100 -> exp(-20) ≈ 0
    # s2 = 120 -> exp(0) = 1
    # total ≈ 120 + log(1) = 120
    assert sect1.total_battle_strength >= 120
    assert sect1.total_battle_strength < 121
    
    # Radius follows the current config: int(120) // 8 + 1 = 16
    assert sect1.influence_radius == 16

    # Income is computed per map tile; only check > 0 here, exact values are asserted in dedicated tests
    assert sect1.magic_stone > 0

    # sect2 data (empty sect)
    assert sect2.total_battle_strength == 0.0
    assert sect2.influence_radius == 1
    # An empty sect keeps 0 income
    assert sect2.magic_stone == 0
    
    # Events are generated
    assert len(events) == 2
    assert all(isinstance(e, Event) for e in events)
    assert events[0].related_sects == [1]
    assert events[1].related_sects == [2]


def test_sect_total_strength_uses_avatar_battle_strength(mock_world):
    """Sect total strength must use get_base_strength(member), i.e. strength derived from realm + effects."""
    from src.systems.cultivation import CultivationProgress

    sect = mock_world.existed_sects[0]
    manager = SectManager(mock_world)

    # Foundation Establishment early stage: Foundation_Establishment=20, Early_Stage=0 -> 20
    avatar = Avatar(
        world=mock_world,
        name="Wang Wu",
        id="avatar_wang",
        birth_month_stamp=MonthStamp(1),
        age=Age(18, realm=0),
        gender=Gender.MALE
    )
    avatar.cultivation_progress = CultivationProgress(31)  # Foundation Establishment early stage
    avatar.join_sect(sect, SectRank.OuterDisciple)
    avatar.is_dead = False
    mock_world.avatar_manager.avatars[avatar.id] = avatar

    expected_strength = get_base_strength(avatar)  # 20.0
    events = manager.update_sects()

    assert sect.total_battle_strength >= 19.0
    assert sect.total_battle_strength <= 21.0
    # Radius follows the current config: int(20) // 8 + 1 = 3
    assert sect.influence_radius == 3
    assert len(events) >= 1


def test_sect_income_conflict_sharing(base_world):
    """When two sects are adjacent, each tile has a single owner and income is no longer split on overlap."""
    world: World = base_world
    game_map = world.map

    # Pick two adjacent coordinates as the sect HQ regions
    r1_id, r2_id = 1001, 1002
    cors1 = [(1, 1)]
    cors2 = [(2, 1)]

    from src.classes.environment.sect_region import SectRegion

    r1 = SectRegion(id=r1_id, name="R1", desc="", sect_id=1, sect_name="S1", cors=cors1)
    r2 = SectRegion(id=r2_id, name="R2", desc="", sect_id=2, sect_name="S2", cors=cors2)

    game_map.regions[r1_id] = r1
    game_map.regions[r2_id] = r2
    game_map.region_cors[r1_id] = cors1
    game_map.region_cors[r2_id] = cors2
    game_map.update_sect_regions()

    hq = SectHeadQuarter(name="Test HQ", desc="", image=Path(""))
    sect1 = Sect(
        id=1,
        name="Sect A",
        desc="",
        member_act_style="",
        alignment=Alignment.NEUTRAL,
        headquarter=hq,
        technique_names=[],
    )
    sect2 = Sect(
        id=2,
        name="Sect B",
        desc="",
        member_act_style="",
        alignment=Alignment.NEUTRAL,
        headquarter=hq,
        technique_names=[],
    )

    world.existed_sects = [sect1, sect2]
    world.sect_context.from_existed_sects(world.existed_sects)

    # Fix strength so both radii are 1
    with patch("src.sim.managers.sect_manager.get_base_strength", return_value=10.0):
        manager = SectManager(world)
        events = manager.update_sects()

    # With no members strength is 0, radius = int(0)//10+1 == 1
    assert sect1.influence_radius == 1
    assert sect2.influence_radius == 1

    snapshot = manager.get_snapshot()
    assert all(len(owners) == 1 for owners in snapshot.tile_owners.values())
    assert snapshot.border_contact_counts

    # Events are produced
    assert len(events) == 2
    assert sect1.magic_stone > 0
    assert sect2.magic_stone > 0


def test_get_tile_owners_only_active(mock_world):
    """get_tile_owners only returns active sects and their territory."""
    sect1 = mock_world.existed_sects[0]
    sect2 = mock_world.existed_sects[1]
    # Mark sect2 inactive
    sect2.is_active = False

    manager = SectManager(mock_world)
    active_sects, tile_owners = manager.get_tile_owners()

    # Only sect1
    assert sect1 in active_sects
    assert sect2 not in active_sects

    # Every tile should contain only sect1's ID
    all_owner_ids = {sid for owners in tile_owners.values() for sid in owners}
    assert sect1.id in all_owner_ids or not all_owner_ids
    assert sect2.id not in all_owner_ids


def test_sect_manager_applies_member_upkeep(base_world):
    """The yearly settlement pays member salaries by rank and deducts the same amount from the sect treasury."""
    world: World = base_world
    game_map = world.map

    from src.classes.environment.sect_region import SectRegion

    region_id = 1001
    cors = [(1, 1)]
    region = SectRegion(id=region_id, name="R1", desc="", sect_id=1, sect_name="Sect A", cors=cors)
    game_map.regions[region_id] = region
    game_map.region_cors[region_id] = cors
    game_map.update_sect_regions()

    hq = SectHeadQuarter(name="Test HQ", desc="", image=Path(""))
    sect = Sect(
        id=1,
        name="Sect A",
        desc="",
        member_act_style="",
        alignment=Alignment.NEUTRAL,
        headquarter=hq,
        technique_names=[],
    )

    member = Avatar(
        world=world,
        name="Disciple A",
        id="member_a",
        birth_month_stamp=MonthStamp(1),
        age=Age(18, realm=0),
        gender=Gender.MALE,
    )
    member.cultivation_progress = CultivationProgress(1)
    member.join_sect(sect, SectRank.OuterDisciple)
    member.is_dead = False

    world.existed_sects = [sect]
    world.sect_context.from_existed_sects(world.existed_sects)
    world.avatar_manager.avatars[member.id] = member

    manager = SectManager(world)
    snapshot = manager.get_snapshot()
    expected_income = int(manager.calculate_income_by_sect(snapshot).get(sect.id, 0.0))
    expected_salary = sect.get_member_upkeep_for_avatar(member)
    events = manager.update_sects()

    assert sect.influence_radius == 2
    assert member.magic_stone == expected_salary
    assert sect.magic_stone == expected_income - expected_salary
    assert len(events) == 1
    assert f"income {expected_income} spirit stones" in events[0].content
    assert f"salaries paid {expected_salary} spirit stones" in events[0].content
    assert f"balance {expected_income - expected_salary} spirit stones" in events[0].content
    assert "War weariness adjusted to 0" in events[0].content


def test_sect_manager_member_salary_uses_sect_rank(base_world):
    """Member salaries are paid by sect rank, not by the current realm field."""
    world: World = base_world
    game_map = world.map

    from src.classes.environment.sect_region import SectRegion

    region_id = 1001
    cors = [(1, 1)]
    region = SectRegion(id=region_id, name="R1", desc="", sect_id=1, sect_name="Sect A", cors=cors)
    game_map.regions[region_id] = region
    game_map.region_cors[region_id] = cors
    game_map.update_sect_regions()

    hq = SectHeadQuarter(name="Test HQ", desc="", image=Path(""))
    sect = Sect(
        id=1,
        name="Sect A",
        desc="",
        member_act_style="",
        alignment=Alignment.NEUTRAL,
        headquarter=hq,
        technique_names=[],
    )

    member = Avatar(
        world=world,
        name="Disciple A",
        id="member_a",
        birth_month_stamp=MonthStamp(1),
        age=Age(18, realm=0),
        gender=Gender.MALE,
    )
    member.cultivation_progress = CultivationProgress(1)
    member.join_sect(sect, SectRank.OuterDisciple)
    member.sect_rank = SectRank.Elder
    member.is_dead = False

    world.existed_sects = [sect]
    world.sect_context.from_existed_sects(world.existed_sects)
    world.avatar_manager.avatars[member.id] = member

    manager = SectManager(world)
    manager.update_sects()

    assert member.magic_stone == 60


def test_sect_manager_updates_war_weariness_annually(base_world):
    world: World = base_world
    game_map = world.map

    from src.classes.environment.sect_region import SectRegion

    region_a = SectRegion(id=1001, name="A", desc="", sect_id=1, sect_name="Sect A", cors=[(1, 1)])
    region_b = SectRegion(id=1002, name="B", desc="", sect_id=2, sect_name="Sect B", cors=[(2, 1)])
    game_map.regions[1001] = region_a
    game_map.region_cors[1001] = [(1, 1)]
    game_map.regions[1002] = region_b
    game_map.region_cors[1002] = [(2, 1)]
    game_map.update_sect_regions()

    hq = SectHeadQuarter(name="Test HQ", desc="", image=Path(""))
    sect_a = Sect(
        id=1,
        name="Sect A",
        desc="",
        member_act_style="",
        alignment=Alignment.NEUTRAL,
        headquarter=hq,
        technique_names=[],
    )
    sect_b = Sect(
        id=2,
        name="Sect B",
        desc="",
        member_act_style="",
        alignment=Alignment.NEUTRAL,
        headquarter=hq,
        technique_names=[],
    )
    sect_a.set_war_weariness(10)
    sect_b.set_war_weariness(2)

    world.existed_sects = [sect_a, sect_b]
    world.sect_context.from_existed_sects(world.existed_sects)
    world.declare_sect_war(sect_a_id=1, sect_b_id=2)

    manager = SectManager(world)
    manager.update_sects()

    assert sect_a.war_weariness == 8
    assert sect_b.war_weariness == 0

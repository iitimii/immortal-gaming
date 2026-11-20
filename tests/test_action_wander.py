from unittest.mock import PropertyMock, patch

import pytest

import src.classes.action as action_pkg
from src.classes.action.registry import ActionRegistry
from src.classes.action.wander import Wander
from src.classes.action_runtime import ActionStatus
from src.classes.actions import ALL_ACTUAL_ACTION_NAMES, get_action_infos
from src.classes.core.avatar import Avatar
from src.classes.environment.plant import Plant
from src.classes.environment.region import CityRegion, NormalRegion
from src.classes.environment.sect_region import SectRegion
from src.server.services.roleplay_action_display import build_roleplay_action_chain_display
from src.systems.cultivation import Realm
from src.systems.time import MonthStamp
from tests.conftest import create_test_material


def _add_region(world, region, cors):
    region.cors = list(cors)
    world.map.regions[region.id] = region
    for x, y in cors:
        world.map.get_tile(x, y).region = region
    return region


def _normal(region_id, name, cors, world):
    return _add_region(world, NormalRegion(id=region_id, name=name, desc=""), cors)


def _advance(world):
    world.month_stamp = MonthStamp(int(world.month_stamp) + 1)


def _run_months(action, world, months):
    statuses = []
    for _ in range(months):
        statuses.append(action.step().status)
        _advance(world)
    return statuses


@pytest.fixture
def wanderer(dummy_avatar):
    # Qi Refinement step is 2; pin it so the paths in these tests are exact.
    with patch.object(Avatar, "move_step_length", new_callable=PropertyMock, return_value=2):
        dummy_avatar.known_regions = set()
        yield dummy_avatar


# ----------------------------------------------------------------------
# Registration, schema and display
# ----------------------------------------------------------------------

def test_wander_is_registered_and_exported(dummy_avatar):
    assert ActionRegistry.get("Wander") is Wander
    assert "Wander" in ALL_ACTUAL_ACTION_NAMES
    assert "Wander" in action_pkg.__all__
    assert action_pkg.Wander is Wander
    assert Wander.ACTION_NAME_ID == "wander_action_name"
    assert Wander.DESC_ID == "wander_description"
    assert Wander.REQUIREMENTS_ID == "wander_requirements"
    assert Wander.EMOJI
    assert Wander.PARAMS == {}
    assert Wander.duration_months == 2


def test_wander_action_info_is_localized_without_params(dummy_avatar):
    infos = get_action_infos(dummy_avatar)
    assert "Wander" in infos
    info = infos["Wander"]
    assert "params" not in info
    assert "param_options" not in info
    assert info["desc"] and info["desc"] != "wander_description"
    assert info["require"] and info["require"] != "wander_requirements"
    assert Wander.get_action_name() == "Wander"


def test_wander_roleplay_display_uses_localized_name():
    display = build_roleplay_action_chain_display([("Wander", {})])
    assert display == [{"action_name": "Wander", "tokens": [{"kind": "verb", "text": "Wander"}]}]


# ----------------------------------------------------------------------
# can_possibly_start / can_start
# ----------------------------------------------------------------------

def test_wander_can_start_branches(dummy_avatar, base_world):
    action = Wander(dummy_avatar, base_world)
    assert action.can_possibly_start() is True
    assert action.can_start() == (True, "")

    dummy_avatar.is_dead = True
    assert action.can_possibly_start() is False
    ok, reason = action.can_start()
    assert ok is False
    assert reason and reason != "wander_cannot_start_dead"


# ----------------------------------------------------------------------
# Movement and discovery
# ----------------------------------------------------------------------

def test_wander_drifts_to_nearest_unknown_region_and_learns_it(wanderer, base_world):
    near = _normal(1, "Misty Vale", [(3, 0), (3, 1)], base_world)
    _normal(2, "Far Marsh", [(9, 9)], base_world)

    action = Wander(wanderer, base_world)
    start_event = action.start()
    assert start_event.related_avatars == [wanderer.id]
    assert wanderer.name in start_event.content

    statuses = _run_months(action, base_world, 2)
    assert statuses == [ActionStatus.RUNNING, ActionStatus.COMPLETED]
    assert (wanderer.pos_x, wanderer.pos_y) == (3, 0)
    assert wanderer.tile is base_world.map.get_tile(3, 0)
    assert near.id in wanderer.known_regions
    assert 2 not in wanderer.known_regions


def test_wander_skips_known_regions_and_foreign_sect_headquarters(wanderer, base_world):
    known = _normal(1, "Home Hills", [(1, 0)], base_world)
    _add_region(base_world, SectRegion(id=2, name="Rival Sect", desc="", sect_id=999), [(0, 2)])
    target = _normal(3, "Quiet Grove", [(4, 0)], base_world)
    wanderer.known_regions = {known.id}

    action = Wander(wanderer, base_world)
    action.start()
    action.step()

    assert action.target_region_id == target.id
    assert (wanderer.pos_x, wanderer.pos_y) == (2, 0)


def test_wander_ignores_unknown_regions_beyond_search_radius(wanderer, base_world):
    _normal(1, "Distant Peak", [(9, 9)], base_world)
    action = Wander(wanderer, base_world)
    action.SEARCH_RADIUS = 5
    action.start()
    action.step()
    assert action.target_region_id is None
    assert action.fallback_direction in {"east", "south"}


def test_wander_fallback_stays_in_bounds_over_many_months(wanderer, base_world):
    # No regions at all: every tile is wilderness (-1) and nothing can be learned.
    action = Wander(wanderer, base_world)
    action.start()
    game_map = base_world.map
    positions = set()
    for _ in range(20):
        action.step()
        _advance(base_world)
        assert game_map.is_in_bounds(wanderer.pos_x, wanderer.pos_y)
        assert wanderer.tile is game_map.get_tile(wanderer.pos_x, wanderer.pos_y)
        positions.add((wanderer.pos_x, wanderer.pos_y))
    assert len(positions) > 1
    assert wanderer.known_regions == set()


def test_wander_fallback_changes_direction_at_map_edge(wanderer, base_world):
    wanderer.pos_x, wanderer.pos_y = 9, 5
    wanderer.tile = base_world.map.get_tile(9, 5)
    action = Wander(wanderer, base_world)
    action.fallback_direction = "east"
    action.start()
    action.step()
    assert action.fallback_direction in {"north", "south", "west"}
    assert (wanderer.pos_x, wanderer.pos_y) != (9, 5)


@pytest.mark.asyncio
async def test_wander_finish_reports_discovered_regions(wanderer, base_world):
    _normal(1, "Misty Vale", [(2, 0)], base_world)
    action = Wander(wanderer, base_world)
    action.start()
    _run_months(action, base_world, 2)

    with patch.object(Wander, "get_find_probability", return_value=0.0):
        events = await action.finish()

    assert len(events) == 1
    assert "Misty Vale" in events[0].content
    assert events[0].related_avatars == [wanderer.id]


@pytest.mark.asyncio
async def test_wander_finish_without_discovery(wanderer, base_world):
    action = Wander(wanderer, base_world)
    action.start()
    _run_months(action, base_world, 2)

    with patch.object(Wander, "get_find_probability", return_value=0.0):
        events = await action.finish()

    assert len(events) == 1
    assert wanderer.name in events[0].content
    assert "{" not in events[0].content


# ----------------------------------------------------------------------
# Serendipitous find
# ----------------------------------------------------------------------

def test_wander_find_probability_scales_with_luck_and_is_clamped(dummy_avatar, base_world):
    action = Wander(dummy_avatar, base_world)
    with patch.object(Avatar, "luck", new_callable=PropertyMock) as mock_luck:
        mock_luck.return_value = 0
        assert action.get_find_probability() == pytest.approx(Wander.BASE_FIND_PROB)
        mock_luck.return_value = 10
        assert action.get_find_probability() == pytest.approx(Wander.BASE_FIND_PROB + 10 * Wander.LUCK_FIND_FACTOR)
        mock_luck.return_value = 1000
        assert action.get_find_probability() == pytest.approx(Wander.MAX_FIND_PROB)
        mock_luck.return_value = -1000
        assert action.get_find_probability() == pytest.approx(Wander.MIN_FIND_PROB)


def test_wander_find_rate_matches_probability_with_seed(dummy_avatar, base_world):
    import random

    action = Wander(dummy_avatar, base_world)
    random.seed(1234)
    with patch.object(Wander, "get_find_probability", return_value=0.25):
        hits = sum(1 for _ in range(2000) if action._try_serendipitous_find())
    assert 0.20 < hits / 2000 < 0.30


def _place_in_region_with_plant(avatar, world):
    region = NormalRegion(id=7, name="Herb Valley", desc="")
    material = create_test_material("Dew Grass", Realm.Qi_Refinement)
    plant = Plant(id=1, name="Dew Bush", desc="", realm=Realm.Qi_Refinement)
    plant.materials = [material]
    high_plant = Plant(id=2, name="Sky Lotus", desc="", realm=Realm.Nascent_Soul)
    high_plant.materials = [create_test_material("Sky Lotus Seed", Realm.Nascent_Soul, material_id=102)]
    region.plants = [plant, high_plant]
    _add_region(world, region, [(0, 0)])
    avatar.tile = world.map.get_tile(0, 0)
    return material


@pytest.mark.asyncio
async def test_wander_find_local_material(dummy_avatar, base_world):
    material = _place_in_region_with_plant(dummy_avatar, base_world)
    dummy_avatar.materials = {}
    action = Wander(dummy_avatar, base_world)
    action.start()

    with patch.object(Wander, "get_find_probability", return_value=1.0), \
            patch.object(Wander, "MATERIAL_FIND_SHARE", 1.0):
        events = await action.finish()

    assert len(events) == 2
    assert dummy_avatar.materials.get(material) == 1
    assert "Dew Grass" in events[1].content
    assert events[1].related_avatars == [dummy_avatar.id]


@pytest.mark.asyncio
async def test_wander_find_spirit_stones_outside_resource_regions(dummy_avatar, base_world):
    _add_region(base_world, CityRegion(id=8, name="Market Town", desc=""), [(0, 0)])
    dummy_avatar.tile = base_world.map.get_tile(0, 0)
    dummy_avatar.magic_stone = 0
    action = Wander(dummy_avatar, base_world)
    action.start()

    with patch.object(Wander, "get_find_probability", return_value=1.0):
        events = await action.finish()

    low, high = Wander.SPIRIT_STONE_RANGES[0]
    assert low <= int(dummy_avatar.magic_stone) <= high
    assert len(events) == 2
    assert str(int(dummy_avatar.magic_stone)) in events[1].content


@pytest.mark.asyncio
async def test_wander_no_find_when_roll_fails(dummy_avatar, base_world):
    dummy_avatar.magic_stone = 0
    action = Wander(dummy_avatar, base_world)
    action.start()
    with patch.object(Wander, "get_find_probability", return_value=0.0):
        events = await action.finish()
    assert len(events) == 1
    assert int(dummy_avatar.magic_stone) == 0


# ----------------------------------------------------------------------
# Save / load of an in-progress wander
# ----------------------------------------------------------------------

def test_wander_save_data_roundtrip(wanderer, base_world):
    _normal(1, "Misty Vale", [(5, 0)], base_world)
    wanderer.known_regions = {42}
    action = Wander(wanderer, base_world)
    action.start()
    action.step()
    data = action.get_save_data()

    restored = Wander(wanderer, base_world)
    restored.load_save_data(data)
    assert restored.target_region_id == 1
    assert restored.target_loc == (5, 0)
    assert restored.initial_known_regions == {42}
    assert int(restored.start_monthstamp) == int(action.start_monthstamp)

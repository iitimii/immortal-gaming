from src.classes.actions import get_action_infos
from src.classes.action.param_options import ParamOptionSource, _get_declared_param_option_sources
from src.classes.action.buy import Buy
from src.classes.action.inflict_gu import InflictGu
from src.classes.mutual_action.gift import Gift
from src.classes.mutual_action.talk import Talk
from src.classes.age import Age
from src.classes.core.avatar import Avatar, Gender
from src.classes.environment.region import CityRegion, CultivateRegion
from src.classes.environment.tile import Tile, TileType
from src.classes.root import Root
from src.systems.cultivation import Realm
from src.systems.time import Month, Year, create_month_stamp
from src.utils.id_generator import get_avatar_id
from tests.conftest import create_test_weapon


def _names(options: list[dict]) -> set[str]:
    return {str(option.get("name", "")) for option in options}


def _ids(options: list[dict]) -> set[str]:
    return {str(option.get("id", "")) for option in options}


def _values(options: list[dict]) -> set[str]:
    return {str(option.get("value", "")) for option in options}


def _register_nearby_avatar(base_world, avatar_in_city) -> Avatar:
    target = Avatar(
        world=base_world,
        name="NearbyNPC",
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
        age=Age(20, Realm.Qi_Refinement),
        gender=Gender.FEMALE,
        pos_x=0,
        pos_y=0,
        root=Root.WOOD,
        personas=[],
    )
    target.tile = avatar_in_city.tile
    base_world.avatar_manager.register_avatar(avatar_in_city)
    base_world.avatar_manager.register_avatar(target)
    return target


def test_action_infos_expose_contextual_param_options(
    avatar_in_city,
    base_world,
    mock_item_data,
):
    city = avatar_in_city.tile.region
    city.store_items = [
        mock_item_data["obj_elixir"],
        mock_item_data["obj_weapon"],
        mock_item_data["obj_material"],
    ]
    base_world.map.regions[city.id] = city
    avatar_in_city.known_regions.add(city.id)

    cave = CultivateRegion(id=2, name="Azure Cloud Cave Abode", desc="Rich spiritual qi", cors=[(1, 1)])
    base_world.map.regions[cave.id] = cave
    avatar_in_city.known_regions.add(cave.id)

    avatar_in_city.add_material(mock_item_data["obj_material"], quantity=5)
    avatar_in_city.weapon = mock_item_data["obj_weapon"]
    avatar_in_city.auxiliary = mock_item_data["obj_auxiliary"]
    _register_nearby_avatar(base_world, avatar_in_city)

    infos = get_action_infos(avatar_in_city)

    buy_options = infos["Buy"]["param_options"]["target_name"]
    assert {"Qi Gathering Pill", "Azure Cloud Sword", "Iron Ore"} <= _names(buy_options)
    assert {"Qi Gathering Pill", "Azure Cloud Sword", "Iron Ore"} <= _values(buy_options)
    assert all("price" in option for option in buy_options)

    sell_options = infos["Sell"]["param_options"]["target_name"]
    assert {"Iron Ore", "Azure Cloud Sword", "Spirit Gathering Orb"} <= _names(sell_options)
    assert {"Iron Ore", "Azure Cloud Sword", "Spirit Gathering Orb"} <= _values(sell_options)

    gift_options = infos["Gift"]["param_options"]["item_id"]
    assert {"SPIRIT_STONE", str(mock_item_data["obj_material"].id), str(mock_item_data["obj_weapon"].id)} <= _ids(gift_options)
    assert {"SPIRIT_STONE", str(mock_item_data["obj_material"].id), str(mock_item_data["obj_weapon"].id)} <= _values(gift_options)
    assert str(mock_item_data["obj_elixir"].id) not in _ids(gift_options)

    target_options = infos["Talk"]["param_options"]["target_avatar"]
    assert "NearbyNPC" in _names(target_options)
    assert "NearbyNPC" in _values(target_options)

    region_options = infos["MoveToRegion"]["param_options"]["region"]
    assert {"TestCity", "Azure Cloud Cave Abode"} <= _names(region_options)
    assert {"TestCity", "Azure Cloud Cave Abode"} <= _values(region_options)

    occupy_options = infos["Occupy"]["param_options"]["region_name"]
    assert "Azure Cloud Cave Abode" in _names(occupy_options)
    assert "Azure Cloud Cave Abode" in _values(occupy_options)
    assert "TestCity" not in _names(occupy_options)

    direction_options = infos["MoveToDirection"]["param_options"]["direction"]
    assert {"north", "south", "east", "west"} <= _ids(direction_options)
    assert {"north", "south", "east", "west"} <= _values(direction_options)

    cast_realms = infos["Cast"]["param_options"]["target_realm"]
    refine_realms = infos["Refine"]["param_options"]["target_realm"]
    assert Realm.Qi_Refinement.value in _ids(cast_realms)
    assert Realm.Qi_Refinement.value in _ids(refine_realms)
    assert Realm.Qi_Refinement.value in _values(cast_realms)
    assert Realm.Qi_Refinement.value in _values(refine_realms)


def test_param_option_sources_are_declared_on_actions_and_inherited():
    assert Buy.PARAM_OPTION_SOURCES["target_name"] == ParamOptionSource.CURRENT_CITY_STORE_ITEM_NAME
    assert Talk.PARAM_OPTION_SOURCES["target_avatar"] == ParamOptionSource.OBSERVABLE_AVATAR_NAME
    gift_sources = _get_declared_param_option_sources(Gift)
    assert gift_sources["target_avatar"] == ParamOptionSource.OBSERVABLE_AVATAR_NAME
    assert gift_sources["item_id"] == ParamOptionSource.GIFTABLE_ITEM_ID
    assert InflictGu.PARAM_OPTION_SOURCES["gu_type"] == ParamOptionSource.AVAILABLE_GU_TYPE


def test_action_param_options_are_derived_from_live_world_state(
    avatar_in_city,
    base_world,
    mock_item_data,
):
    city = avatar_in_city.tile.region
    city.store_items = [mock_item_data["obj_elixir"]]
    base_world.map.regions[city.id] = city
    avatar_in_city.known_regions.add(city.id)

    before = get_action_infos(avatar_in_city)
    assert "Dark Iron Sword" not in _names(before["Buy"]["param_options"]["target_name"])

    city.store_items.append(create_test_weapon("Dark Iron Sword", Realm.Qi_Refinement, weapon_id=90210))

    after = get_action_infos(avatar_in_city)
    assert "Dark Iron Sword" in _names(after["Buy"]["param_options"]["target_name"])


def test_contextual_action_parameters_are_grounded_or_left_numeric(
    avatar_in_city,
    base_world,
    mock_item_data,
):
    city = avatar_in_city.tile.region
    city.store_items = [mock_item_data["obj_elixir"], mock_item_data["obj_material"]]
    base_world.map.regions[city.id] = city
    avatar_in_city.known_regions.add(city.id)
    cave = CultivateRegion(id=2, name="Azure Cloud Cave Abode", desc="Rich spiritual qi", cors=[(1, 1)])
    base_world.map.regions[cave.id] = cave
    avatar_in_city.known_regions.add(cave.id)
    avatar_in_city.add_material(mock_item_data["obj_material"], quantity=5)
    _register_nearby_avatar(base_world, avatar_in_city)

    infos = get_action_infos(avatar_in_city)
    grounded_param_names = {
        "avatar_name",
        "target_avatar",
        "region",
        "region_name",
        "target_name",
        "item_id",
        "target_realm",
        "direction",
        "gu_type",
    }
    grounded_param_types = {
        "avatarname",
        "regionname",
        "region_name",
        "direction",
    }

    for action_name, info in infos.items():
        params = info.get("params", {})
        for param_name, param_type in params.items():
            normalized_type = str(param_type).lower().replace(" ", "")
            needs_grounding = (
                param_name in grounded_param_names
                or any(kind in normalized_type for kind in grounded_param_types)
            )
            if not needs_grounding:
                continue

            options = info.get("param_options", {}).get(param_name)
            assert options, f"{action_name}.{param_name} should expose contextual options"


def test_inflict_gu_param_options_expose_all_gu_types(avatar_in_city):
    avatar_in_city.temporary_effects.append({
        "source": "test_gu_permission",
        "effects": {"legal_actions": ["InflictGu"]},
        "start_month": int(avatar_in_city.world.month_stamp),
        "duration": 1,
    })

    infos = get_action_infos(avatar_in_city)
    options = infos["InflictGu"]["param_options"]["gu_type"]

    assert _values(options) == {"qianxin", "shixue", "shiyuan", "luanxin"}
    assert {"Heartlink Gu", "Bloodgnaw Gu", "Essence-Eroding Gu", "Mind-Disorder Gu"} <= _names(options)


def test_observable_avatar_options_do_not_fallback_to_all_living_when_empty(
    avatar_in_city,
    base_world,
):
    far_target = Avatar(
        world=base_world,
        name="FarAwayNPC",
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
        age=Age(20, Realm.Qi_Refinement),
        gender=Gender.FEMALE,
        pos_x=9,
        pos_y=9,
        root=Root.WOOD,
        personas=[],
    )
    far_target.tile = Tile(9, 9, TileType.PLAIN)
    base_world.avatar_manager.register_avatar(avatar_in_city)
    base_world.avatar_manager.register_avatar(far_target)

    infos = get_action_infos(avatar_in_city)

    assert "param_options" not in infos["Talk"] or "target_avatar" not in infos["Talk"]["param_options"]


def test_known_region_options_require_known_regions_attribute(
    avatar_in_city,
    base_world,
):
    city = avatar_in_city.tile.region
    base_world.map.regions[city.id] = city
    avatar_in_city.known_regions = None

    infos = get_action_infos(avatar_in_city)

    assert "param_options" not in infos["MoveToRegion"] or "region" not in infos["MoveToRegion"]["param_options"]


def test_occupy_options_exclude_owned_regions_and_include_host_context(
    avatar_in_city,
    base_world,
):
    owned_cave = CultivateRegion(id=2, name="Own Cave Abode", desc="Occupied", cors=[(1, 1)])
    contested_cave = CultivateRegion(id=3, name="Contested Cave Abode", desc="Owned", cors=[(2, 2)])
    host = _register_nearby_avatar(base_world, avatar_in_city)
    host.name = "Cave Abode Host"
    contested_cave.host_avatar = host
    avatar_in_city.occupy_region(owned_cave)

    base_world.map.regions[owned_cave.id] = owned_cave
    base_world.map.regions[contested_cave.id] = contested_cave
    avatar_in_city.known_regions.update({owned_cave.id, contested_cave.id})

    infos = get_action_infos(avatar_in_city)
    options = infos["Occupy"]["param_options"]["region_name"]

    assert "Own Cave Abode" not in _names(options)
    assert "Contested Cave Abode" in _names(options)
    contested_option = next(option for option in options if option["name"] == "Contested Cave Abode")
    assert contested_option["value"] == "Contested Cave Abode"
    assert contested_option["host_avatar"] == {"id": str(host.id), "name": "Cave Abode Host"}

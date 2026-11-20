from fastapi.testclient import TestClient

from src.classes.environment.map import Map
from src.classes.environment.region import CityRegion
from src.classes.gender import Gender
from src.classes.mortal import Mortal
from src.server import main
from src.sim.managers.mortal_manager import MortalManager
from src.systems.time import Month, MonthStamp, Year, create_month_stamp


def _build_world_with_mortal_data():
    from src.classes.core.world import World

    game_map = Map(width=5, height=5)
    world = World(
        map=game_map,
        month_stamp=create_month_stamp(Year(100), Month.JANUARY),
    )

    city_a = CityRegion(
        id=1,
        name="Bluestone City",
        desc="",
        population=100.0,
        population_capacity=200.0,
    )
    city_b = CityRegion(
        id=2,
        name="Whiteriver City",
        desc="",
        population=40.0,
        population_capacity=50.0,
    )
    world.map.regions[1] = city_a
    world.map.regions[2] = city_b

    world.mortal_manager = MortalManager()
    world.mortal_manager.register_mortal(
        Mortal(
            id="mortal-young",
            name="Lin Xiaoman",
            gender=Gender.FEMALE,
            birth_month_stamp=MonthStamp(int(world.month_stamp) - 10 * 12),
            parents=["a1", "a2"],
            born_region_id=1,
        )
    )
    world.mortal_manager.register_mortal(
        Mortal(
            id="mortal-awaken",
            name="Zhao Xingzhou",
            gender=Gender.MALE,
            birth_month_stamp=MonthStamp(int(world.month_stamp) - 20 * 12),
            parents=["b1", "b2"],
            born_region_id=2,
        )
    )

    return world


def test_get_mortal_overview_empty_when_world_missing():
    original_instance = main.game_instance.copy()
    try:
        main.game_instance["world"] = None
        client = TestClient(main.app)
        resp = client.get("/api/v1/query/mortals/overview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["summary"]["total_population"] == 0.0
        assert data["summary"]["tracked_mortal_count"] == 0
        assert data["cities"] == []
        assert data["tracked_mortals"] == []
    finally:
        main.game_instance.update(original_instance)


def test_get_mortal_overview_aggregates_cities_and_tracked_mortals():
    original_instance = main.game_instance.copy()
    try:
        world = _build_world_with_mortal_data()
        main.game_instance["world"] = world
        main.game_instance["sim"] = None

        client = TestClient(main.app)
        resp = client.get("/api/v1/query/mortals/overview")

        assert resp.status_code == 200
        data = resp.json()["data"]

        summary = data["summary"]
        assert summary["total_population"] == 140.0
        assert summary["total_population_capacity"] == 250.0
        expected_growth = 0.03 * 100.0 * (1 - 100.0 / 200.0) + 0.03 * 40.0 * (1 - 40.0 / 50.0)
        assert summary["total_natural_growth"] == expected_growth
        assert summary["tracked_mortal_count"] == 2
        assert summary["awakening_candidate_count"] == 1

        cities = data["cities"]
        assert [item["name"] for item in cities] == ["Bluestone City", "Whiteriver City"]
        assert cities[0]["natural_growth"] == 1.5

        tracked = data["tracked_mortals"]
        assert [item["name"] for item in tracked] == ["Zhao Xingzhou", "Lin Xiaoman"]
        assert tracked[0]["age"] == 20
        assert tracked[0]["born_region_name"] == "Whiteriver City"
        assert tracked[0]["is_awakening_candidate"] is True
        assert tracked[1]["is_awakening_candidate"] is False
    finally:
        main.game_instance.update(original_instance)

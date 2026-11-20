from fastapi.testclient import TestClient

from src.classes.age import Age
from src.classes.alignment import Alignment
from src.classes.core.avatar import Avatar, Gender
from src.classes.core.sect import sects_by_id
from src.classes.death_reason import DeathReason, DeathType
from src.classes.items.magic_stone import MagicStone
from src.classes.race import get_race
from src.classes.root import Root
from src.server import main
from src.server.services.world_statistics import build_world_statistics
from src.systems.cultivation import CultivationProgress, Realm
from src.systems.time import Month, Year, create_month_stamp
from src.utils.id_generator import get_avatar_id


def _make_avatar(world, *, name, age, level=1, gender=Gender.MALE, race="human",
                 sect=None, alignment=Alignment.RIGHTEOUS, stones=0) -> Avatar:
    avatar = Avatar(
        world=world,
        name=name,
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
        age=Age(age, Realm.Qi_Refinement, innate_max_lifespan=500),
        gender=gender,
        pos_x=0,
        pos_y=0,
        root=Root.GOLD,
        personas=[],
        alignment=alignment,
    )
    avatar.personas = []
    avatar.technique = None
    avatar.race = get_race(race)
    avatar.sect = sect
    avatar.cultivation_progress = CultivationProgress(level)
    avatar.magic_stone = MagicStone(stones)
    world.avatar_manager.register_avatar(avatar)
    return avatar


def _kill(world, avatar, reason) -> None:
    avatar.set_dead(str(reason), world.month_stamp)
    world.avatar_manager.handle_death(avatar.id)
    world.deceased_manager.record_death(avatar)


def _build_world(world):
    sect = sects_by_id[1]
    elder = _make_avatar(world, name="Elder", age=320, level=95, sect=sect, stones=50,
                         alignment=Alignment.NEUTRAL)
    rich = _make_avatar(world, name="Merchant", age=40, level=5, stones=900,
                        gender=Gender.FEMALE)
    fox = _make_avatar(world, name="Fox", age=60, level=35, race="fox", sect=sect,
                       alignment=Alignment.EVIL, stones=50)

    for index, reason in enumerate([
        DeathReason(DeathType.BATTLE, killer_name="Elder"),
        DeathReason(DeathType.BATTLE, killer_name="Fox"),
        DeathReason(DeathType.OLD_AGE),
        "Swallowed by a heavenly tribulation",
    ]):
        victim = _make_avatar(world, name=f"Victim{index}", age=30)
        _kill(world, victim, reason)
    return sect, elder, rich, fox


def test_world_statistics_counts_living_distributions(base_world):
    sect, elder, rich, fox = _build_world(base_world)

    stats = build_world_statistics(base_world)

    assert stats["living_count"] == 3

    realms = stats["realms"]
    assert [item["id"] for item in realms] == [
        "QI_REFINEMENT", "FOUNDATION_ESTABLISHMENT", "CORE_FORMATION", "NASCENT_SOUL",
    ]
    assert [item["count"] for item in realms] == [1, 1, 0, 1]
    assert realms[0]["label"] == "Qi Refinement"
    assert [stage["id"] for stage in realms[0]["stages"]] == ["EARLY_STAGE", "MIDDLE_STAGE", "LATE_STAGE"]
    assert realms[0]["stages"][0]["count"] == 1
    assert realms[1]["stages"][0]["count"] == 1
    assert realms[3]["stages"][0]["count"] == 1

    distributions = stats["distributions"]
    assert distributions["sect"] == [
        {"id": str(sect.id), "label": sect.name, "count": 2},
        {"id": "rogue", "label": "Rogue Cultivator", "count": 1},
    ]
    assert distributions["race"] == [
        {"id": "human", "label": "Human", "count": 2},
        {"id": "fox", "label": "Fox Yao", "count": 1},
    ]
    assert distributions["gender"] == [
        {"id": "male", "label": "Male", "count": 2},
        {"id": "female", "label": "Female", "count": 1},
    ]
    assert {item["id"]: item["count"] for item in distributions["alignment"]} == {
        "RIGHTEOUS": 1, "NEUTRAL": 1, "EVIL": 1,
    }
    # Buckets with equal counts are ordered by label.
    assert [item["label"] for item in distributions["alignment"]] == ["Evil", "Neutral", "Righteous"]
    orthodoxy = {item["id"]: item for item in distributions["orthodoxy"]}
    assert orthodoxy[sect.orthodoxy_id]["count"] == 2
    assert orthodoxy["sanxiu"]["count"] == 1
    assert orthodoxy["sanxiu"]["label"] == "Nature"


def test_world_statistics_age_wealth_and_deceased(base_world):
    _sect, elder, rich, _fox = _build_world(base_world)

    stats = build_world_statistics(base_world)

    assert stats["age"] == {
        "average": round((320 + 40 + 60) / 3, 1),
        "oldest": {"id": elder.id, "name": "Elder", "value": 320},
    }
    assert stats["wealth"] == {
        "total": 1000,
        "average": round(1000 / 3, 1),
        "richest": {"id": rich.id, "name": "Merchant", "value": 900},
    }

    deceased = stats["deceased"]
    assert deceased["total"] == 4
    assert deceased["top_reasons"] == [
        {"id": "battle", "label": "Killed in battle", "count": 2},
        {"id": "old_age", "label": "Died of old age", "count": 1},
        {"id": "other", "label": "Other causes", "count": 1},
    ]


def test_world_statistics_empty_world(base_world):
    stats = build_world_statistics(base_world)

    assert stats["living_count"] == 0
    assert all(item["count"] == 0 for item in stats["realms"])
    assert stats["distributions"]["sect"] == []
    assert stats["age"] == {"average": 0.0, "oldest": None}
    assert stats["wealth"] == {"total": 0, "average": 0.0, "richest": None}
    assert stats["deceased"] == {"total": 0, "top_reasons": []}


def test_v1_world_statistics_endpoint(base_world):
    original = dict(main.game_instance)
    try:
        _build_world(base_world)
        main.game_instance["world"] = base_world
        client = TestClient(main.app)

        response = client.get("/api/v1/query/world/statistics")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["living_count"] == 3
        assert payload["data"]["deceased"]["total"] == 4
        assert payload["data"]["wealth"]["richest"]["name"] == "Merchant"
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_world_statistics_requires_world():
    original = dict(main.game_instance)
    try:
        main.game_instance["world"] = None
        client = TestClient(main.app)

        response = client.get("/api/v1/query/world/statistics")

        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "WORLD_NOT_READY"
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)

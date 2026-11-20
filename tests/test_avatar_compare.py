import copy
import random

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.classes.age import Age
from src.classes.alignment import Alignment
from src.classes.core.avatar import Avatar, Gender
from src.classes.core.sect import sects_by_id
from src.classes.items.magic_stone import MagicStone
from src.classes.relation.relation import NumericRelation, Relation
from src.classes.relation.relations import set_friendliness, set_relation
from src.classes.root import Root
from src.classes.technique import techniques_by_id
from src.server import main
from src.server.services.avatar_compare import build_avatar_comparison
from src.systems import battle
from src.systems.cultivation import CultivationProgress, Realm
from src.systems.time import Month, Year, create_month_stamp
from src.utils.id_generator import get_avatar_id
from tests.conftest import create_test_auxiliary, create_test_weapon


def _make_avatar(world, *, name, level=1, stones=0, sect=None, weapon=None, auxiliary=None,
                 technique=None, alignment=Alignment.RIGHTEOUS) -> Avatar:
    avatar = Avatar(
        world=world,
        name=name,
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
        age=Age(40, Realm.Qi_Refinement, innate_max_lifespan=300),
        gender=Gender.MALE,
        pos_x=0,
        pos_y=0,
        root=Root.GOLD,
        personas=[],
        alignment=alignment,
    )
    avatar.personas = []
    avatar.technique = technique
    avatar.weapon = weapon
    avatar.auxiliary = auxiliary
    avatar.sect = sect
    avatar.cultivation_progress = CultivationProgress(level)
    avatar.magic_stone = MagicStone(stones)
    avatar.recalc_effects()
    world.avatar_manager.register_avatar(avatar)
    return avatar


def _pair(world):
    technique = next(iter(techniques_by_id.values()))
    strong = _make_avatar(
        world,
        name="Elder Lan",
        level=85,
        stones=300,
        sect=sects_by_id[1],
        weapon=create_test_weapon("Azure Blade", Realm.Core_Formation),
        auxiliary=create_test_auxiliary("Jade Bell", Realm.Foundation_Establishment),
        technique=technique,
    )
    weak = _make_avatar(world, name="Wanderer Qiu", level=5, stones=20, alignment=Alignment.EVIL)
    return strong, weak


def _snapshot(avatar):
    return {
        "hp": (avatar.hp.cur, avatar.hp.max),
        "stones": avatar.magic_stone.value,
        "relations": {other.id: copy.deepcopy(state.__dict__) for other, state in avatar.relations.items()},
        "relation_keys": set(avatar.relations.keys()),
        "level": avatar.cultivation_progress.level,
        "pos": (avatar.pos_x, avatar.pos_y),
    }


def test_compare_builds_both_sides(base_world):
    strong, weak = _pair(base_world)

    result = build_avatar_comparison(base_world, strong.id, weak.id)
    a, b = result["a"], result["b"]

    assert a["id"] == strong.id and a["name"] == "Elder Lan"
    assert b["id"] == weak.id
    assert a["realm"]["id"] == "CORE_FORMATION"
    assert a["stage"]["id"] == "LATE_STAGE"
    assert b["realm"] == {"id": "QI_REFINEMENT", "label": b["realm"]["label"]}
    assert a["cultivation_display"]
    assert a["level"] == 85
    assert a["age"] == 40
    assert a["lifespan"] == strong.age.max_lifespan
    assert a["hp"] == {"cur": strong.hp.cur, "max": strong.hp.max}
    assert a["battle_strength"] == round(battle.get_base_strength(strong), 1)
    assert a["battle_strength"] > b["battle_strength"]
    assert a["root"]["id"] == "GOLD" and a["root"]["label"]
    assert a["sect"]["id"] == str(sects_by_id[1].id)
    assert a["sect"]["name"] == sects_by_id[1].name
    assert a["sect"]["rank"]
    assert b["sect"] is None
    assert a["orthodoxy"]["id"] == sects_by_id[1].orthodoxy_id
    assert b["orthodoxy"] == {"id": "sanxiu", "label": "Nature"}
    assert a["alignment"] == {"id": "RIGHTEOUS", "label": "Righteous"}
    assert b["alignment"] == {"id": "EVIL", "label": "Evil"}
    assert a["technique"]["name"] == strong.technique.name
    assert a["technique"]["grade"] == str(strong.technique.grade)
    assert b["technique"] is None
    assert a["weapon"] == {"id": "201", "name": "Azure Blade", "grade": str(Realm.Core_Formation), "grade_rank": 2}
    assert a["auxiliary"]["grade_rank"] == 1
    assert b["weapon"] is None and b["auxiliary"] is None
    assert a["spirit_stones"] == 300 and b["spirit_stones"] == 20
    assert a["relation_count"] == 0


def test_compare_relations_between_pair(base_world):
    strong, weak = _pair(base_world)
    other = _make_avatar(base_world, name="Bystander")
    set_relation(strong, weak, Relation.IS_SWORN_SIBLING_OF)
    set_friendliness(strong, weak, 60, current_month=int(base_world.month_stamp))
    set_friendliness(weak, other, -70, current_month=int(base_world.month_stamp))

    result = build_avatar_comparison(base_world, strong.id, weak.id)

    a_to_b = result["relation"]["a_to_b"]
    b_to_a = result["relation"]["b_to_a"]
    assert len(a_to_b["labels"]) == 2
    assert a_to_b["friendliness"] == 60
    assert a_to_b["numeric_relation"] == strong.relations[weak].last_numeric_relation.value
    assert len(b_to_a["labels"]) == 2
    assert result["a"]["relation_count"] == 1
    # Sworn sibling of A plus archenemy Bystander.
    assert result["b"]["relation_count"] == 2


def test_compare_strangers_have_stranger_label(base_world):
    strong, weak = _pair(base_world)

    result = build_avatar_comparison(base_world, strong.id, weak.id)

    assert result["relation"]["a_to_b"] == {
        "labels": [str(NumericRelation.STRANGER)],
        "numeric_relation": "stranger",
        "friendliness": 0,
    }
    # Looking at a stranger must not create relation state.
    assert weak not in strong.relations
    assert strong not in weak.relations


def test_compare_win_probability_matches_battle_system(base_world):
    strong, weak = _pair(base_world)

    estimate = build_avatar_comparison(base_world, strong.id, weak.id)["battle"]

    assert estimate["method"] == "closed_form"
    assert estimate["a_win_probability"] == round(battle.calc_win_rate(strong, weak), 4)
    a_strength, b_strength = battle.get_effective_strength_pair(strong, weak)
    assert estimate["a_strength"] == round(a_strength, 1)
    assert estimate["b_strength"] == round(b_strength, 1)
    assert 0.0 < estimate["b_win_probability"] < estimate["a_win_probability"] < 1.0
    assert estimate["a_win_probability"] + estimate["b_win_probability"] == pytest.approx(1.0, abs=1e-3)


def test_compare_is_symmetric_and_deterministic(base_world):
    strong, weak = _pair(base_world)

    forward = build_avatar_comparison(base_world, strong.id, weak.id)
    random.seed(12345)
    again = build_avatar_comparison(base_world, strong.id, weak.id)
    reverse = build_avatar_comparison(base_world, weak.id, strong.id)

    assert forward == again
    assert reverse["a"] == forward["b"]
    assert reverse["b"] == forward["a"]
    assert reverse["battle"]["a_win_probability"] == forward["battle"]["b_win_probability"]
    assert reverse["relation"]["a_to_b"] == forward["relation"]["b_to_a"]


def test_compare_matches_empirical_battle_outcomes(base_world):
    strong, weak = _pair(base_world)
    expected = build_avatar_comparison(base_world, strong.id, weak.id)["battle"]["a_win_probability"]

    rng_state = random.getstate()
    random.seed(7)
    trials = 4000
    wins = sum(1 for _ in range(trials) if battle.decide_battle(strong, weak)[0] is strong)
    random.setstate(rng_state)

    assert wins / trials == pytest.approx(expected, abs=0.03)


def test_compare_does_not_mutate_world(base_world):
    strong, weak = _pair(base_world)
    set_friendliness(strong, weak, 40, current_month=int(base_world.month_stamp))
    before = (_snapshot(strong), _snapshot(weak))
    living_before = set(base_world.avatar_manager.avatars)
    rng_state = random.getstate()

    build_avatar_comparison(base_world, strong.id, weak.id)

    assert (_snapshot(strong), _snapshot(weak)) == before
    assert set(base_world.avatar_manager.avatars) == living_before
    assert random.getstate() == rng_state


def _error_code(excinfo) -> tuple[int, str]:
    return excinfo.value.status_code, excinfo.value.detail["code"]


def test_compare_rejects_invalid_ids(base_world):
    strong, weak = _pair(base_world)

    with pytest.raises(HTTPException) as missing:
        build_avatar_comparison(base_world, strong.id, "")
    assert _error_code(missing) == (400, "AVATAR_ID_REQUIRED")

    with pytest.raises(HTTPException) as same:
        build_avatar_comparison(base_world, strong.id, strong.id)
    assert _error_code(same) == (400, "SAME_AVATAR")

    with pytest.raises(HTTPException) as unknown:
        build_avatar_comparison(base_world, strong.id, "ghost")
    assert _error_code(unknown) == (404, "AVATAR_NOT_FOUND")
    assert unknown.value.detail["details"] == {"avatar_id": "ghost"}


def test_compare_rejects_dead_avatar(base_world):
    strong, weak = _pair(base_world)
    weak.set_dead("Old age", base_world.month_stamp)
    base_world.avatar_manager.handle_death(weak.id)

    with pytest.raises(HTTPException) as dead:
        build_avatar_comparison(base_world, strong.id, weak.id)

    assert _error_code(dead) == (404, "AVATAR_DEAD")


def test_v1_avatar_compare_endpoint(base_world):
    original = dict(main.game_instance)
    try:
        strong, weak = _pair(base_world)
        main.game_instance["world"] = base_world
        client = TestClient(main.app)

        response = client.get(f"/api/v1/query/avatars/compare?a={strong.id}&b={weak.id}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["a"]["name"] == "Elder Lan"
        assert payload["data"]["b"]["name"] == "Wanderer Qiu"
        assert payload["data"]["battle"]["a_win_probability"] > 0.5

        same = client.get(f"/api/v1/query/avatars/compare?a={strong.id}&b={strong.id}")
        assert same.status_code == 400
        assert same.json()["detail"]["code"] == "SAME_AVATAR"

        missing = client.get(f"/api/v1/query/avatars/compare?a={strong.id}")
        assert missing.status_code == 400
        assert missing.json()["detail"]["code"] == "AVATAR_ID_REQUIRED"

        unknown = client.get(f"/api/v1/query/avatars/compare?a={strong.id}&b=nobody")
        assert unknown.status_code == 404
        assert unknown.json()["detail"]["code"] == "AVATAR_NOT_FOUND"
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_avatar_compare_requires_world():
    original = dict(main.game_instance)
    try:
        main.game_instance["world"] = None
        client = TestClient(main.app)

        response = client.get("/api/v1/query/avatars/compare?a=x&b=y")

        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "WORLD_NOT_READY"
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)

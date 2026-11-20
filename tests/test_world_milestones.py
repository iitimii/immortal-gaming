from pathlib import Path

from fastapi.testclient import TestClient

from src.classes.age import Age
from src.classes.alignment import Alignment
from src.classes.core.avatar import Avatar, Gender
from src.classes.core.sect import sects_by_id
from src.classes.root import Root
from src.classes.world_milestone import WorldMilestoneState
from src.sim.load.load_game import load_game
from src.sim.save.save_game import save_game
from src.sim.simulator import Simulator
from src.sim.simulator_engine.phase_registry import get_simulation_phases
from src.sim.simulator_engine.phases import world as world_phases
from src.systems.cultivation import CultivationProgress, Realm
from src.systems.time import Month, Year, create_month_stamp
from src.systems.world_milestones import (
    MILESTONE_DEFINITIONS,
    build_world_milestones_overview,
    detect_world_milestones,
)
from src.utils.id_generator import get_avatar_id


REALM_LEVEL = {
    Realm.Qi_Refinement: 1,
    Realm.Foundation_Establishment: 31,
    Realm.Core_Formation: 61,
    Realm.Nascent_Soul: 91,
}


def _make_avatar(world, name: str, *, age: int = 20, realm: Realm = Realm.Qi_Refinement) -> Avatar:
    avatar = Avatar(
        world=world,
        name=name,
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(1), Month.JANUARY),
        age=Age(age, realm, innate_max_lifespan=900),
        gender=Gender.MALE,
        pos_x=0,
        pos_y=0,
        root=Root.GOLD,
        personas=[],
        alignment=Alignment.RIGHTEOUS,
    )
    avatar.personas = []
    avatar.technique = None
    avatar.cultivation_progress = CultivationProgress(REALM_LEVEL[realm])
    world.avatar_manager.register_avatar(avatar)
    return avatar


def _set_realm(avatar: Avatar, realm: Realm) -> None:
    avatar.cultivation_progress = CultivationProgress(REALM_LEVEL[realm])


def _living(world):
    return world.avatar_manager.get_living_avatars()


def _advance(world, months: int = 1) -> None:
    world.month_stamp = world.month_stamp + months


def _detect(world):
    return detect_world_milestones(world, _living(world))


def _open_chronicle(world):
    assert _detect(world) == []
    _advance(world)


def test_definitions_cover_expected_milestones():
    keys = [definition.key for definition in MILESTONE_DEFINITIONS]
    assert keys == [
        "first_realm_foundation_establishment",
        "first_realm_core_formation",
        "first_realm_nascent_soul",
        "first_age_100",
        "first_age_300",
        "first_sworn_siblings",
        "first_dao_companions",
        "first_master_disciple",
        "first_sect_war",
    ]


def test_opening_pass_seeds_pre_existing_state_silently(base_world):
    sects = list(sects_by_id.values())[:2]
    elder = _make_avatar(base_world, "Elder", age=150, realm=Realm.Nascent_Soul)
    partner = _make_avatar(base_world, "Partner", realm=Realm.Core_Formation)
    elder.become_lovers_with(partner)
    elder.become_sworn_sibling_with(partner)
    base_world.declare_sect_war(sect_a_id=sects[0].id, sect_b_id=sects[1].id)

    assert _detect(base_world) == []

    state = base_world.milestones
    assert state.opened_month == int(base_world.month_stamp)
    assert state.records == []
    assert set(state.avatar_marks) == {elder.id, partner.id}

    # Nothing changed, so a later pass still records nothing.
    _advance(base_world)
    assert _detect(base_world) == []


def test_realm_breakthrough_records_first_once_with_major_event(base_world):
    first = _make_avatar(base_world, "First")
    second = _make_avatar(base_world, "Second")
    _open_chronicle(base_world)

    _set_realm(first, Realm.Foundation_Establishment)
    events = _detect(base_world)

    assert len(events) == 1
    event = events[0]
    assert event.is_major is True
    assert event.related_avatars == [first.id]
    assert "First" in event.content
    assert "Foundation Establishment" in event.content

    record = base_world.milestones.get_record("first_realm_foundation_establishment")
    assert record is not None
    assert record.avatar_ids == [first.id]
    assert record.avatar_names == ["First"]
    assert record.month_stamp == int(base_world.month_stamp)
    assert record.event_id == event.id

    _advance(base_world)
    _set_realm(second, Realm.Foundation_Establishment)
    assert _detect(base_world) == []
    assert len(base_world.milestones.records) == 1


def test_each_higher_realm_is_its_own_milestone(base_world):
    climber = _make_avatar(base_world, "Climber", realm=Realm.Foundation_Establishment)
    _open_chronicle(base_world)

    _set_realm(climber, Realm.Core_Formation)
    events = _detect(base_world)
    assert [e.related_avatars for e in events] == [[climber.id]]
    assert base_world.milestones.is_achieved("first_realm_core_formation")
    # Starting above Qi Refinement does not count as breaking through to Foundation Establishment.
    assert not base_world.milestones.is_achieved("first_realm_foundation_establishment")

    _advance(base_world)
    _set_realm(climber, Realm.Nascent_Soul)
    events = _detect(base_world)
    assert len(events) == 1
    assert base_world.milestones.is_achieved("first_realm_nascent_soul")


def test_newcomer_above_threshold_is_baselined_silently(base_world):
    _open_chronicle(base_world)
    newcomer = _make_avatar(base_world, "Newcomer", age=120, realm=Realm.Core_Formation)

    assert _detect(base_world) == []
    assert newcomer.id in base_world.milestones.avatar_marks


def test_age_thresholds_detected_on_crossing(base_world):
    elder = _make_avatar(base_world, "Elder", age=99, realm=Realm.Foundation_Establishment)
    ancient = _make_avatar(base_world, "Ancient", age=299, realm=Realm.Nascent_Soul)
    _open_chronicle(base_world)

    elder.age.age = 100
    ancient.age.age = 300
    events = _detect(base_world)

    assert len(events) == 2
    assert base_world.milestones.get_record("first_age_100").avatar_ids == [elder.id]
    assert base_world.milestones.get_record("first_age_300").avatar_ids == [ancient.id]
    assert "100" in events[0].content


def test_sworn_siblings_and_dao_companions(base_world):
    a = _make_avatar(base_world, "Alpha")
    b = _make_avatar(base_world, "Beta")
    _open_chronicle(base_world)

    a.become_sworn_sibling_with(b)
    events = _detect(base_world)
    assert len(events) == 1
    assert sorted(events[0].related_avatars) == sorted([a.id, b.id])
    assert base_world.milestones.is_achieved("first_sworn_siblings")

    _advance(base_world)
    a.become_lovers_with(b)
    events = _detect(base_world)
    assert len(events) == 1
    record = base_world.milestones.get_record("first_dao_companions")
    assert sorted(record.avatar_ids) == sorted([a.id, b.id])
    assert "Dao companions" in events[0].content


def test_master_disciple_records_master_first(base_world):
    master = _make_avatar(base_world, "Master", realm=Realm.Core_Formation)
    disciple = _make_avatar(base_world, "Disciple")
    _open_chronicle(base_world)

    disciple.acknowledge_master(master)
    events = _detect(base_world)

    assert len(events) == 1
    record = base_world.milestones.get_record("first_master_disciple")
    assert record.avatar_ids == [master.id, disciple.id]
    assert events[0].content.index("Master") < events[0].content.index("Disciple")


def test_bond_with_newcomer_is_not_a_first(base_world):
    veteran = _make_avatar(base_world, "Veteran")
    _open_chronicle(base_world)

    newcomer = _make_avatar(base_world, "Newcomer")
    veteran.become_lovers_with(newcomer)

    assert _detect(base_world) == []
    assert not base_world.milestones.is_achieved("first_dao_companions")


def test_sect_war_declared_after_opening(base_world):
    sects = list(sects_by_id.values())[:3]
    base_world.declare_sect_war(sect_a_id=sects[0].id, sect_b_id=sects[1].id)
    _open_chronicle(base_world)

    base_world.declare_sect_war(sect_a_id=sects[1].id, sect_b_id=sects[2].id)
    events = _detect(base_world)

    assert len(events) == 1
    assert events[0].is_major is True
    assert sorted(events[0].related_sects) == sorted([sects[1].id, sects[2].id])
    record = base_world.milestones.get_record("first_sect_war")
    assert set(record.sect_names) == {sects[1].name, sects[2].name}

    _advance(base_world)
    base_world.make_sect_peace(sect_a_id=sects[1].id, sect_b_id=sects[2].id)
    base_world.declare_sect_war(sect_a_id=sects[0].id, sect_b_id=sects[2].id)
    assert _detect(base_world) == []


def test_dead_avatars_leave_baseline(base_world):
    victim = _make_avatar(base_world, "Victim")
    _open_chronicle(base_world)
    victim.set_dead("test", base_world.month_stamp)

    # Even if a stale list still contains the dead avatar, it drops out of the baseline.
    detect_world_milestones(base_world, [victim])
    assert victim.id not in base_world.milestones.avatar_marks


def test_overview_lists_achieved_chronologically_and_pending(base_world):
    first = _make_avatar(base_world, "First")
    second = _make_avatar(base_world, "Second", age=99)
    _open_chronicle(base_world)

    second.age.age = 100
    _detect(base_world)
    _advance(base_world, 3)
    _set_realm(first, Realm.Foundation_Establishment)
    _detect(base_world)

    overview = build_world_milestones_overview(base_world)

    assert [item["key"] for item in overview["achieved"]] == [
        "first_age_100",
        "first_realm_foundation_establishment",
    ]
    item = overview["achieved"][1]
    assert item["title"] == "First to Reach Foundation Establishment"
    assert "First became the first cultivator" in item["description"]
    assert item["year"] == base_world.month_stamp.get_year()
    assert item["month"] == base_world.month_stamp.get_month().value
    assert item["date_text"].startswith("Year ")
    assert item["avatars"] == [{"id": first.id, "name": "First", "available": True, "is_dead": False}]
    assert overview["total"] == len(MILESTONE_DEFINITIONS)
    pending_keys = [entry["key"] for entry in overview["pending"]]
    assert "first_age_100" not in pending_keys
    assert "first_sect_war" in pending_keys
    assert all(entry["title"] and entry["description"] for entry in overview["pending"])
    assert overview["opened_month_stamp"] is not None


def test_phase_is_registered_before_finalize(base_world):
    phases = get_simulation_phases()
    names = [phase.name for phase in phases]
    assert names[-2:] == ["detect_world_milestones", "finalize_step"]

    avatar = _make_avatar(base_world, "Phased")
    assert world_phases.phase_detect_world_milestones(base_world, _living(base_world)) == []
    _advance(base_world)
    _set_realm(avatar, Realm.Foundation_Establishment)
    events = world_phases.phase_detect_world_milestones(base_world, _living(base_world))
    assert len(events) == 1


def test_save_load_round_trip_preserves_milestones(base_world, tmp_path):
    sects = list(sects_by_id.values())[:2]
    base_world.existed_sects = sects
    base_world.sect_context.from_existed_sects(sects)
    hero = _make_avatar(base_world, "Hero")
    rival = _make_avatar(base_world, "Rival")
    _open_chronicle(base_world)
    _set_realm(hero, Realm.Foundation_Establishment)
    _detect(base_world)

    save_path = Path(tmp_path) / "milestones_save.json"
    success, _ = save_game(base_world, Simulator(base_world), sects, save_path=save_path)
    assert success

    new_world, _sim, _sects = load_game(save_path)
    state = new_world.milestones
    assert state.opened_month == base_world.milestones.opened_month
    assert [record.to_dict() for record in state.records] == [
        record.to_dict() for record in base_world.milestones.records
    ]
    assert state.avatar_marks == base_world.milestones.avatar_marks

    # Achieved milestones are not re-announced after loading, while open ones keep tracking.
    loaded_hero = new_world.avatar_manager.get_avatar(hero.id)
    loaded_rival = new_world.avatar_manager.get_avatar(rival.id)
    _set_realm(loaded_rival, Realm.Foundation_Establishment)
    loaded_hero.become_sworn_sibling_with(loaded_rival)
    events = detect_world_milestones(new_world, new_world.avatar_manager.get_living_avatars())
    assert len(events) == 1
    assert new_world.milestones.is_achieved("first_sworn_siblings")


def test_missing_milestones_field_loads_as_empty():
    state = WorldMilestoneState()
    state.load_from_dict(None)
    assert state.opened_month is None
    assert state.records == []
    assert state.avatar_marks == {}

    state.load_from_dict({"records": [{"key": ""}, "junk", {"key": "first_sect_war", "month_stamp": 5}]})
    assert [record.key for record in state.records] == ["first_sect_war"]


def test_public_api_returns_milestones(base_world):
    from src.server import main

    hero = _make_avatar(base_world, "Hero")
    _open_chronicle(base_world)
    _set_realm(hero, Realm.Foundation_Establishment)
    _detect(base_world)

    original = dict(main.game_instance)
    try:
        main.game_instance["world"] = base_world
        client = TestClient(main.app)
        response = client.get("/api/v1/query/world/milestones")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        data = payload["data"]
        assert data["achieved"][0]["key"] == "first_realm_foundation_establishment"
        assert data["achieved"][0]["avatars"][0]["id"] == hero.id
        assert len(data["pending"]) == len(MILESTONE_DEFINITIONS) - 1
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_public_api_requires_world():
    from src.server import main

    original = dict(main.game_instance)
    try:
        main.game_instance["world"] = None
        client = TestClient(main.app)
        response = client.get("/api/v1/query/world/milestones")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "WORLD_NOT_READY"
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)

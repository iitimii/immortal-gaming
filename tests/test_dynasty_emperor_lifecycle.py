from src.classes.core.dynasty import Dynasty, Emperor
from src.sim.simulator_engine.phases import world as world_phases
from src.systems.time import MonthStamp


def test_phase_update_dynasty_replaces_dead_emperor(base_world):
    base_world.dynasty = Dynasty(
        id=1,
        name="Jin",
        desc="",
        royal_surname="Sima",
        current_emperor=Emperor(
            surname="Sima",
            given_name="Cheng'an",
            birth_month_stamp=int(base_world.month_stamp) - 80 * 12,
            max_age=80,
        ),
    )

    events = world_phases.phase_update_dynasty(base_world)

    assert len(events) == 2
    assert "has passed away" in events[0].content
    assert "Sima Cheng'an" in events[0].content
    assert "A new emperor ascends" in events[1].content
    assert base_world.dynasty.current_emperor is not None
    assert base_world.dynasty.current_emperor.name != "Sima Cheng'an"
    assert base_world.dynasty.current_emperor.surname == "Sima"
    assert base_world.dynasty.current_emperor.name.startswith("Sima ")
    assert 25 <= base_world.dynasty.current_emperor.max_age <= 90
    assert base_world.dynasty.current_emperor.get_age(int(base_world.month_stamp)) < base_world.dynasty.current_emperor.max_age


def test_phase_update_dynasty_generates_emperor_if_missing(base_world):
    base_world.dynasty = Dynasty(
        id=1,
        name="Qin",
        desc="",
        royal_surname="Shangguan",
    )

    events = world_phases.phase_update_dynasty(base_world)

    assert len(events) == 1
    assert "has enthroned a new ruler" in events[0].content
    assert base_world.dynasty.current_emperor is not None
    assert base_world.dynasty.current_emperor.surname == "Shangguan"

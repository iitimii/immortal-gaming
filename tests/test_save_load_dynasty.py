from pathlib import Path

from src.classes.core.dynasty import Dynasty, Emperor
from src.sim.simulator import Simulator
from src.sim.save.save_game import save_game
from src.sim.load.load_game import load_game


def test_save_and_load_preserves_dynasty(base_world, tmp_path):
    base_world.dynasty = Dynasty(
        id=2,
        name="Song",
        desc="Values letters over arms; its statutes are elaborate and private academies flourish.",
        royal_surname="Shangguan",
        effect_desc="",
        effects={},
        current_emperor=Emperor(
            surname="Shangguan",
            given_name="Jingtian",
            birth_month_stamp=int(base_world.month_stamp) - 28 * 12,
            max_age=80,
        ),
    )

    simulator = Simulator(base_world)
    save_path = Path(tmp_path) / "dynasty_save.json"
    success, _ = save_game(base_world, simulator, existed_sects=[], save_path=save_path)

    assert success

    new_world, _new_sim, _new_sects = load_game(save_path)
    assert new_world.dynasty is not None
    assert new_world.dynasty.name == "Song"
    assert new_world.dynasty.royal_surname == "Shangguan"
    assert new_world.dynasty.title == "Song Dynasty"
    assert new_world.dynasty.current_emperor is not None
    assert new_world.dynasty.current_emperor.name == "Shangguan Jingtian"

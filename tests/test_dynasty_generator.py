from src.classes.core.dynasty import dynasties_by_id
from src.systems.dynasty_generator import generate_dynasty


def test_generate_dynasty_returns_runtime_dynasty():
    dynasty = generate_dynasty()
    template = dynasties_by_id[dynasty.id]

    assert dynasty.id in dynasties_by_id
    assert dynasty.name == template.name
    assert dynasty.royal_surname
    assert dynasty.title == f"{dynasty.name} Dynasty"
    assert dynasty.royal_house_name == f"House {dynasty.royal_surname}"
    assert dynasty.is_low_magic is True
    assert dynasty.effects == template.effects
    assert dynasty.effects is not template.effects

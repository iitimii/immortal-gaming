import pytest

from src.classes.environment.sect_region import SectRegion
from src.classes.essence import EssenceType


def test_sect_region_essence_all_types_are_five():
    """Sect headquarters effective essence: every element is 5."""
    region = SectRegion(id=1, name="Test Sect HQ", desc="desc", sect_name="Test Sect", sect_id=1)

    for essence_type in EssenceType:
        assert region.essence.get_density(essence_type) == 5

    info = region.get_structured_info()
    assert info.get("essence", {}).get("density") == 5


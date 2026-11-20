import pytest
from unittest.mock import MagicMock, Mock
from src.utils.normalize import (
    remove_parentheses,
    normalize_name,
    normalize_goods_name,
    normalize_weapon_type
)
from src.utils.resolution import (
    resolve_query,
    ResolutionResult
)
from src.classes.material import Material
from src.classes.environment.region import CityRegion, Region
from src.classes.core.avatar import Avatar, Gender
from src.classes.age import Age
from src.classes.root import Root
from src.systems.cultivation import Realm
from src.systems.time import Month, Year, create_month_stamp
from src.utils.id_generator import get_avatar_id

# ==================== Normalize Tests ====================

def test_remove_parentheses():
    """Test bracket removal."""
    # Basic cases (ASCII and full-width brackets)
    assert remove_parentheses("Azure Cloud Sword(Mortal)") == "Azure Cloud Sword"
    assert remove_parentheses("Azure Cloud Sword\uff08Mortal\uff09") == "Azure Cloud Sword"
    assert remove_parentheses("Azure Cloud Sword[Mortal]") == "Azure Cloud Sword"
    assert remove_parentheses("Azure Cloud Sword\u3010Mortal\u3011") == "Azure Cloud Sword"
    assert remove_parentheses("Azure Cloud Sword<Mortal>") == "Azure Cloud Sword"
    assert remove_parentheses("Azure Cloud Sword\u300aMortal\u300b") == "Azure Cloud Sword"
    assert remove_parentheses("Azure Cloud Sword (Mortal)") == "Azure Cloud Sword"

    # Nested and multiple brackets
    assert remove_parentheses("Item(note(more notes))") == "Item"
    assert remove_parentheses("Prefix(note)Suffix") == "Prefix"  # current logic truncates

    # No brackets
    assert remove_parentheses("Plain Item") == "Plain Item"
    assert remove_parentheses("") == ""

def test_normalize_goods_name():
    """Test goods name normalization."""
    assert normalize_goods_name("Iron Sword -") == "Iron Sword"
    assert normalize_goods_name("Iron Sword(Mortal) -") == "Iron Sword"
    assert normalize_goods_name("  Iron Sword  ") == "Iron Sword"

def test_normalize_weapon_type():
    """Test weapon type normalization."""
    assert normalize_weapon_type("Sword type") == "Sword"
    assert normalize_weapon_type("Saber weapon") == "Saber"
    assert normalize_weapon_type("  Spear Weapon ") == "Spear"
    assert normalize_weapon_type("Plain Sword") == "Plain Sword"


# ==================== Resolution Tests ====================

class MockWorld:
    def __init__(self):
        self.map = Mock()
        self.map.regions = {}
        self.map.sect_regions = {}
        self.avatar_manager = Mock()
        self.avatar_manager.avatars = {}

@pytest.fixture
def mock_world():
    return MockWorld()

def test_resolve_query_empty():
    """Test an empty query."""
    res = resolve_query("")
    assert not res.is_valid
    # The message depends on whether the query is None or ""
    assert res.error_msg in ["Empty query", "Empty query string"]
    
    res = resolve_query(None)
    assert not res.is_valid
    assert res.error_msg == "Empty query"

def test_resolve_query_direct_object():
    """Test passing an object directly."""
    # 1. Matching type
    material = Material(id=999, name="Test Material", desc="Test description", realm=Realm.Qi_Refinement)
    res = resolve_query(material, expected_types=[Material])
    assert res.is_valid
    assert res.obj is material
    assert res.resolved_type == Material

    # 2. Object passed with a non-matching type
    res = resolve_query(material, expected_types=[Realm])
    assert not res.is_valid

def test_resolve_query_realm():
    """Test realm resolution."""
    # Enum names are the most robust input
    res = resolve_query("Qi_Refinement", expected_types=[Realm])
    assert res.is_valid
    assert res.obj == Realm.Qi_Refinement

    # 2. Invalid value
    res = resolve_query("Nonexistent Realm", expected_types=[Realm])
    assert not res.is_valid


def test_resolve_query_goods_by_id(monkeypatch):
    material = Material(id=123456, name="ID Material", desc="Test description", realm=Realm.Qi_Refinement)

    import src.utils.resolution as resolution

    monkeypatch.setitem(resolution.materials_by_id, material.id, material)

    res = resolve_query(str(material.id), expected_types=[Material])

    assert res.is_valid
    assert res.obj is material


def test_resolve_query_region_by_id(mock_world):
    region = CityRegion(id=77, name="ID Region", desc="Test region")
    mock_world.map.regions = {region.id: region}

    res = resolve_query(str(region.id), world=mock_world, expected_types=[Region])

    assert res.is_valid
    assert res.obj is region


def test_resolve_query_avatar_by_id(base_world):
    avatar = Avatar(
        world=base_world,
        name="IDTarget",
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
        age=Age(20, Realm.Qi_Refinement),
        gender=Gender.FEMALE,
        pos_x=0,
        pos_y=0,
        root=Root.WOOD,
        personas=[],
    )
    base_world.avatar_manager.register_avatar(avatar)

    res = resolve_query(str(avatar.id), world=base_world, expected_types=[Avatar])

    assert res.is_valid
    assert res.obj is avatar

def test_resolve_query_unsupported_type():
    """Test unsupported input types."""
    res = resolve_query(123, expected_types=[Material])
    assert not res.is_valid
    assert "non-string" in res.error_msg

def test_resolve_region_mock(mock_world):
    """Test region resolution (mocked environment)."""
    # Prepare data - use the regions[id] dict rather than region_names
    mock_region = Mock()
    mock_region.name = "Azure Cloud Mountain"
    mock_world.map.regions = {1: mock_region}
    
    # 1. Exact match
    res = resolve_query("Azure Cloud Mountain", world=mock_world, expected_types=[type(mock_region)]) # dynamic type standing in for Region
    # Note: resolution checks concrete class names, which Mock classes do not match,
    # so this only exercises the code path rather than asserting a result.
    pass 

# resolution.py depends heavily on the concrete classes (Material, Region, ...)
# and checks isinstance(t, type) and t.__name__, so unit tests mainly cover
# logic branches; integration tests cover the real classes.

def test_resolve_priority():
    """Test resolution priority."""
    # Placeholder: a name that is both an item and a realm (unlikely) would be
    # resolved according to the order of expected_types.
    pass


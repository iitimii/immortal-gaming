import pytest
from unittest.mock import MagicMock

from src.classes.core.world import World
from src.classes.core.avatar import Avatar, Gender
from src.classes.environment.map import Map
from src.classes.environment.region import CityRegion, Region, NormalRegion
from src.classes.environment.sect_region import SectRegion
from src.classes.core.sect import Sect
from src.classes.environment.tile import Tile, TileType
from src.utils.born_region import get_born_region_id
from src.classes.core.avatar.info_presenter import get_avatar_info, get_avatar_structured_info

@pytest.fixture
def mock_world():
    """Create a world containing cities and a sect headquarters."""
    game_map = Map(width=10, height=10)
    
    # Create a few regions
    city1 = CityRegion(id=1, name="CityA", desc="City A")
    city2 = CityRegion(id=2, name="CityB", desc="City B")
    sect_region = SectRegion(id=3, name="SectBase", desc="Sect HQ", sect_id=1, sect_name="TestSect")
    wild_region = NormalRegion(id=4, name="Wilds", desc="Wild land")
    
    # Inject into the map
    game_map.regions[1] = city1
    game_map.regions[2] = city2
    game_map.regions[3] = sect_region
    game_map.regions[4] = wild_region
    game_map.update_sect_regions() # Refresh the sect_regions dict
    
    # Set the center point
    city1.center_loc = (0, 0)
    city2.center_loc = (9, 9)
    sect_region.center_loc = (5, 5)
    wild_region.center_loc = (2, 7)

    world = MagicMock(spec=World)
    world.map = game_map
    return world

def test_born_region_priority_sect(mock_world):
    """Priority 1: sect headquarters."""
    # Mock a sect
    sect = MagicMock(spec=Sect)
    sect.id = 1
    sect.name = "TestSect"
    
    # Parent belongs to that sect
    parent = MagicMock(spec=Avatar)
    parent.sect = sect
    
    # Expected: returns SectRegion (id=3)
    born_id = get_born_region_id(mock_world, parents=[parent])
    assert born_id == 3

def test_born_region_priority_nearest_city(mock_world):
    """Priority 2: nearest city."""
    # Parent has no sect
    parent = MagicMock(spec=Avatar)
    parent.sect = None
    
    # Parent at (1, 1), near CityA (0,0)
    parent.tile = MagicMock(spec=Tile)
    parent.tile.coordinate = (1, 1)
    
    # Expected: returns CityA (id=1)
    born_id = get_born_region_id(mock_world, parents=[parent])
    assert born_id == 1
    
    # Parent at (8, 8), near CityB (9,9)
    parent.tile.coordinate = (8, 8)
    born_id = get_born_region_id(mock_world, parents=[parent])
    assert born_id == 2

def test_born_region_priority_random_city(mock_world):
    """Priority 3: random city."""
    # No parents, no sect
    born_id = get_born_region_id(mock_world, parents=[], sect=None)
    assert born_id in [1, 2] # must be one of the two cities


def test_yao_born_region_prefers_wild_region(mock_world):
    from src.classes.race import get_race

    born_id = get_born_region_id(mock_world, parents=[], sect=None, race=get_race("fox"))
    assert born_id == 4

def test_info_presenter_integration(mock_world):
    """Presentation-layer integration."""
    # Create an avatar with an origin
    avatar = MagicMock(spec=Avatar)
    avatar.name = "TestAvatar"
    avatar.gender = Gender.MALE
    avatar.age = MagicMock()
    avatar.age.__str__.return_value = "20"
    avatar.age.age = 20
    avatar.cultivation_progress = MagicMock()
    avatar.cultivation_progress.get_info.return_value = "Qi Refinement"
    avatar.world = mock_world
    avatar.world.ranking_manager = MagicMock()
    avatar.world.ranking_manager.get_avatar_rank.return_value = None
    
    # Set the origin to CityA
    avatar.born_region_id = 1
    
    # Mock necessary attributes for get_avatar_info
    avatar.tile = None
    avatar.relations = {}
    avatar.magic_stone = 100
    avatar.weapon = None
    avatar.auxiliary = None
    avatar.sect = None
    avatar.alignment = None
    avatar.root = MagicMock()
    avatar.root.get_info.return_value = "Gold"
    avatar.technique = None
    avatar.personas = []
    avatar.materials = {}
    avatar.appearance = MagicMock()
    avatar.appearance.get_info.return_value = "Handsome"
    avatar.spirit_animal = None
    avatar.emotion = MagicMock()
    avatar.emotion.value = "Calm"
    avatar.long_term_objective = None
    avatar.short_term_objective = ""
    avatar.nickname = None
    avatar.hp = MagicMock()
    avatar.hp.__str__.return_value = "100/100"
    avatar.id = 1
    avatar.orthodoxy = None
    avatar.emotion = MagicMock()
    avatar.emotion.value = "calm"

    # Check info_dict
    from src.classes.core.avatar.info_presenter import get_avatar_info
    info = get_avatar_info(avatar, detailed=False)
    
    # The key is localized (default locale en-US); the mocked Region.name is "CityA"
    assert "Origin" in info
    assert info["Origin"] == "CityA"

"""
Tests for the behavior of Avatar._init_known_regions.

Verifies:
1. Avatar without a sect: known_regions only contains the region at the current position (if any)
2. Avatar with a sect: known_regions contains the sect headquarters
"""
import pytest
from unittest.mock import MagicMock

from src.classes.environment.map import Map
from src.classes.environment.tile import TileType
from src.classes.core.world import World
from src.systems.time import Month, Year, create_month_stamp
from src.classes.core.avatar import Avatar, Gender
from src.classes.age import Age
from src.systems.cultivation import Realm
from src.classes.root import Root
from src.classes.alignment import Alignment
from src.classes.core.sect import sects_by_id
from src.classes.environment.sect_region import SectRegion
from src.classes.environment.region import NormalRegion
from src.utils.id_generator import get_avatar_id


@pytest.fixture
def world_with_sect_region():
    """Create a world with a sect headquarters."""
    width, height = 10, 10
    game_map = Map(width=width, height=height)
    
    # Create tiles
    for x in range(width):
        for y in range(height):
            game_map.create_tile(x, y, TileType.PLAIN)
    
    # Get a real sect (High Heaven Sword Sect, id=1)
    sect = sects_by_id.get(1)
    assert sect is not None, "Sect ID=1 should exist"
    
    # Create the matching SectRegion
    sect_region = SectRegion(
        id=401,
        name="Rosy Cloud Mountain",
        desc="Test sect headquarters",
        cors=[(5, 5)],
        sect_name=sect.name,
        sect_id=sect.id
    )
    
    # Register on the map
    game_map.regions[sect_region.id] = sect_region
    game_map.sect_regions[sect_region.id] = sect_region
    
    # Bind the region to the tile
    tile = game_map.get_tile(5, 5)
    tile.region = sect_region
    
    world = World(map=game_map, month_stamp=create_month_stamp(Year(1), Month.JANUARY))
    return world, sect, sect_region


@pytest.fixture
def world_with_normal_region():
    """Create a world with a normal region."""
    width, height = 10, 10
    game_map = Map(width=width, height=height)
    
    for x in range(width):
        for y in range(height):
            game_map.create_tile(x, y, TileType.PLAIN)
    
    # Create a normal region
    normal_region = NormalRegion(
        id=101,
        name="Test Region",
        desc="An ordinary region",
        cors=[(0, 0)]
    )
    
    game_map.regions[normal_region.id] = normal_region
    
    # Bind to the tile
    tile = game_map.get_tile(0, 0)
    tile.region = normal_region
    
    world = World(map=game_map, month_stamp=create_month_stamp(Year(1), Month.JANUARY))
    return world, normal_region


class TestInitKnownRegions:
    """Tests for Avatar._init_known_regions."""

    def test_avatar_without_sect_knows_current_region(self, world_with_normal_region):
        """An avatar without a sect should know the region at its current position."""
        world, normal_region = world_with_normal_region
        
        avatar = Avatar(
            world=world,
            name="Rogue Test",
            id=get_avatar_id(),
            birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
            age=Age(20, Realm.Qi_Refinement),
            gender=Gender.MALE,
            pos_x=0,
            pos_y=0,
            root=Root.GOLD,
            alignment=Alignment.RIGHTEOUS,
            sect=None  # rogue cultivator
        )
        
        # Set the tile (simulating the normal init flow)
        avatar.tile = world.map.get_tile(0, 0)
        avatar._init_known_regions()
        
        assert normal_region.id in avatar.known_regions, (
            f"A rogue cultivator should know the current region, but known_regions={avatar.known_regions}"
        )

    def test_avatar_with_sect_knows_headquarters(self, world_with_sect_region):
        """An avatar with a sect should know the sect headquarters."""
        world, sect, sect_region = world_with_sect_region
        
        avatar = Avatar(
            world=world,
            name="Sect Disciple Test",
            id=get_avatar_id(),
            birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
            age=Age(20, Realm.Qi_Refinement),
            gender=Gender.MALE,
            pos_x=0,
            pos_y=0,  # not at the sect headquarters
            root=Root.GOLD,
            alignment=Alignment.RIGHTEOUS,
            sect=sect  # has a sect
        )
        
        # _init_known_regions is called automatically in __post_init__
        assert sect_region.id in avatar.known_regions, (
            f"A sect disciple should know the sect headquarters, but known_regions={avatar.known_regions}"
        )

    def test_avatar_without_sect_does_not_know_sect_region(self, world_with_sect_region):
        """An avatar without a sect should not automatically know the sect headquarters."""
        world, sect, sect_region = world_with_sect_region
        
        avatar = Avatar(
            world=world,
            name="Rogue Test",
            id=get_avatar_id(),
            birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
            age=Age(20, Realm.Qi_Refinement),
            gender=Gender.MALE,
            pos_x=0,
            pos_y=0,
            root=Root.GOLD,
            alignment=Alignment.RIGHTEOUS,
            sect=None  # rogue cultivator
        )
        
        # A rogue cultivator should not know the sect HQ (unless standing there)
        assert sect_region.id not in avatar.known_regions, (
            f"A rogue cultivator should not automatically know the sect HQ, but known_regions={avatar.known_regions}"
        )

    def test_avatar_knows_only_their_sect_headquarters(self, world_with_sect_region):
        """An avatar should only know its own sect's headquarters, not other sects'."""
        world, sect, sect_region = world_with_sect_region
        
        # Add another sect's headquarters
        other_sect = sects_by_id.get(2)  # Ten Thousand Beasts Mountain
        assert other_sect is not None
        
        other_sect_region = SectRegion(
            id=402,
            name="Mystic Spirit Cave",
            desc="Another sect headquarters",
            cors=[(7, 7)],
            sect_name=other_sect.name,
            sect_id=other_sect.id
        )
        world.map.regions[other_sect_region.id] = other_sect_region
        world.map.sect_regions[other_sect_region.id] = other_sect_region
        
        # Create a High Heaven Sword Sect disciple
        avatar = Avatar(
            world=world,
            name="High Heaven Sword Disciple",
            id=get_avatar_id(),
            birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
            age=Age(20, Realm.Qi_Refinement),
            gender=Gender.MALE,
            pos_x=0,
            pos_y=0,
            root=Root.GOLD,
            alignment=Alignment.RIGHTEOUS,
            sect=sect  # High Heaven Sword Sect
        )
        
        # Should know its own sect headquarters
        assert sect_region.id in avatar.known_regions, (
            "Should know its own sect headquarters"
        )
        # Should not know other sects' headquarters
        assert other_sect_region.id not in avatar.known_regions, (
            "Should not know other sects' headquarters"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

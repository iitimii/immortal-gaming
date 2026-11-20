
import pytest
from src.classes.death_reason import DeathReason, DeathType
from src.classes.death import handle_death
from src.classes.environment.region import CultivateRegion, EssenceType

def test_death_releases_region(base_world, dummy_avatar):
    """An occupied cave dwelling is released when its owner dies."""
    # 1. Create a cultivation region
    region = CultivateRegion(
        id=1001,
        name="Test Cave",
        desc="A test cave",
        essence_type=EssenceType.GOLD,
        essence_density=10
    )
    # Add the region to the map
    base_world.map.regions[region.id] = region
    
    # 2. Have the avatar occupy the region
    dummy_avatar.occupy_region(region)
    
    # Occupation succeeded
    assert region.host_avatar == dummy_avatar
    assert region in dummy_avatar.owned_regions
    
    # 3. The avatar dies
    reason = DeathReason(DeathType.OLD_AGE)
    handle_death(base_world, dummy_avatar, reason)
    
    # 4. The cave dwelling has been released
    assert region.host_avatar is None
    assert len(dummy_avatar.owned_regions) == 0
    assert dummy_avatar.is_dead is True

def test_occupy_region_logic(base_world, dummy_avatar):
    """Occupation keeps a bidirectional binding and supports seizure."""
    from src.classes.core.avatar import Avatar, Gender
    from src.classes.age import Age
    from src.systems.cultivation import Realm
    from src.utils.id_generator import get_avatar_id
    from src.classes.root import Root
    from src.classes.alignment import Alignment
    from src.systems.time import create_month_stamp, Year, Month

    # Create a second avatar
    other_avatar = Avatar(
        world=base_world,
        name="Other",
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
        age=Age(20, Realm.Qi_Refinement),
        gender=Gender.MALE,
        pos_x=0, pos_y=0,
        root=Root.WOOD,
        alignment=Alignment.RIGHTEOUS
    )
    
    region = CultivateRegion(
        id=1002,
        name="Test Cave 2",
        desc="Another test cave",
        essence_type=EssenceType.WOOD,
        essence_density=10
    )
    
    # 1. dummy_avatar occupies
    dummy_avatar.occupy_region(region)
    assert region.host_avatar == dummy_avatar
    assert region in dummy_avatar.owned_regions
    
    # 2. other_avatar seizes it
    other_avatar.occupy_region(region)
    
    # Ownership transferred
    assert region.host_avatar == other_avatar
    assert region in other_avatar.owned_regions
    
    # The previous owner released it
    assert region not in dummy_avatar.owned_regions

def test_remove_avatar_releases_region(base_world, dummy_avatar):
    """An occupied cave dwelling is released when its owner is fully removed."""
    # 1. Create a cultivation region
    region = CultivateRegion(
        id=1003,
        name="Test Cave 3",
        desc="Yet another test cave",
        essence_type=EssenceType.WATER,
        essence_density=10
    )
    base_world.map.regions[region.id] = region
    
    # 2. Register and occupy
    base_world.avatar_manager.register_avatar(dummy_avatar)
    dummy_avatar.occupy_region(region)
    
    assert region.host_avatar == dummy_avatar
    
    # 3. Fully remove the avatar
    base_world.avatar_manager.remove_avatar(dummy_avatar.id)
    
    # 4. The cave dwelling has been released
    assert region.host_avatar is None
    # Note: the dummy_avatar object may still be in memory, but it is removed from the manager
    # its owned_regions should be cleared
    assert len(dummy_avatar.owned_regions) == 0

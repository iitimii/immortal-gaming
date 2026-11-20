import pytest
from unittest.mock import MagicMock, patch
from src.utils.gather import execute_gather, check_can_start_gather
from src.systems.cultivation import Realm
from src.classes.environment.region import NormalRegion

@pytest.fixture
def mock_region(dummy_avatar):
    """Attach a mock NormalRegion to the avatar's tile."""
    real_region = NormalRegion(id=999, name="TestRegion", desc="Testing")
    # Bypass post_init loading from global dicts by manually setting fields
    real_region.lodes = []
    real_region.animals = []
    real_region.plants = []
    
    dummy_avatar.tile.region = real_region
    return real_region

@pytest.fixture
def mock_resource_material():
    material = MagicMock()
    material.name = "TestMaterial"
    material.realm = Realm.Qi_Refinement
    return material

@pytest.fixture
def mock_resource(mock_resource_material):
    """Create a generic resource object (Lode/Animal/Plant)."""
    res = MagicMock()
    res.realm = Realm.Qi_Refinement
    res.materials = [mock_resource_material]
    return res

def test_check_can_start_gather_success(dummy_avatar, mock_region, mock_resource):
    """Gather check passes."""
    mock_region.lodes = [mock_resource]
    
    can, msg = check_can_start_gather(dummy_avatar, "lodes", "ore veins")
    assert can is True
    assert msg == ""

def test_check_can_start_gather_not_normal_region(dummy_avatar):
    """Avatar is not in a normal region."""
    dummy_avatar.tile.region = "NotARegion" 
    
    can, msg = check_can_start_gather(dummy_avatar, "lodes", "ore veins")
    assert can is False
    assert "Not currently in a normal region" in msg

def test_check_can_start_gather_no_resources(dummy_avatar, mock_region):
    """Region has no resources."""
    mock_region.lodes = []
    
    can, msg = check_can_start_gather(dummy_avatar, "lodes", "ore veins")
    assert can is False
    assert "The current region has no ore veins" in msg

def test_check_can_start_gather_realm_too_low(dummy_avatar, mock_region, mock_resource):
    """Avatar realm is too low."""
    # Raise the resource realm to Foundation Establishment
    mock_resource.realm = Realm.Foundation_Establishment
    mock_region.lodes = [mock_resource]
    # the avatar defaults to Qi Refinement
    
    can, msg = check_can_start_gather(dummy_avatar, "lodes", "ore veins")
    assert can is False
    assert "The ore veins in the current region are of too high a realm" in msg

def test_execute_gather_success(dummy_avatar, mock_region, mock_resource, mock_resource_material):
    """Gather execution succeeds."""
    mock_region.lodes = [mock_resource]
    
    # Mock add_material
    dummy_avatar.add_material = MagicMock()
    
    result = execute_gather(dummy_avatar, "lodes", "extra_mine_materials")
    
    assert "TestMaterial" in result
    assert result["TestMaterial"] >= 1
    dummy_avatar.add_material.assert_called_once()
    
    # Verify the gathered material is correct
    args, _ = dummy_avatar.add_material.call_args
    assert args[0] == mock_resource_material
    assert args[1] >= 1

def test_execute_gather_with_extra_effect(dummy_avatar, mock_region, mock_resource):
    """Gather with a bonus effect."""
    mock_region.lodes = [mock_resource]
    
    # effects is a read-only property computed by merging component effects.
    # Mock the effects property for this test.
    with patch.object(type(dummy_avatar), 'effects', new_callable=lambda: {"extra_mine_materials": 2}):
        dummy_avatar.add_material = MagicMock()
        
        result = execute_gather(dummy_avatar, "lodes", "extra_mine_materials")
        
        # base 1 + bonus 2 = 3
        assert result["TestMaterial"] == 3
    
def test_execute_gather_random_selection(dummy_avatar, mock_region):
    """Randomly pick among multiple resources."""
    res1 = MagicMock()
    res1.realm = Realm.Qi_Refinement
    res1.materials = [MagicMock(name="Material1")]
    res1.materials[0].name = "Material1"
    
    res2 = MagicMock()
    res2.realm = Realm.Qi_Refinement
    res2.materials = [MagicMock(name="Material2")]
    res2.materials[0].name = "Material2"
    
    mock_region.lodes = [res1, res2]
    dummy_avatar.add_material = MagicMock()
    
    execute_gather(dummy_avatar, "lodes", "extra_mine_materials")
    dummy_avatar.add_material.assert_called_once()

from __future__ import annotations
import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

def check_can_start_gather(
    avatar: Avatar,
    resource_attr: str,  # "lodes", "animals", "plants"
    resource_name: str  # e.g. "ore veins", "animals", "plants"
) -> tuple[bool, str]:
    from src.classes.environment.region import NormalRegion
    
    region = avatar.tile.region
    if not isinstance(region, NormalRegion):
        return False, "Not currently in a normal region"
        
    resources = getattr(region, resource_attr, [])
    if not resources:
        return False, f"The current region has no {resource_name}"
        
    # Filter resources by realm
    available = [
        r for r in resources
        if avatar.cultivation_progress.realm >= r.realm
    ]
    if not available:
        return False, f"The {resource_name} in the current region are of too high a realm"
        
    return True, ""

def execute_gather(
    avatar: Avatar,
    resource_attr: str,
    extra_effect_key: str
) -> dict[str, int]:
    """
    Run the gathering logic.
    Returns: {material_name: count}
    """
    from src.classes.environment.region import NormalRegion
    region = avatar.tile.region
    
    # Re-check the type in case the runtime state changed
    if not isinstance(region, NormalRegion):
        return {}

    resources = getattr(region, resource_attr, [])
    
    # Filter
    available = [
        r for r in resources
        if avatar.cultivation_progress.realm >= r.realm
    ]
    
    if not available:
        return {}
        
    # 1. Pick a random resource node (uniform)
    target = random.choice(available)
    
    # 2. Pick a random output material
    if not hasattr(target, "materials") or not target.materials:
        return {}
        
    material = random.choice(target.materials)
    
    base_quantity = 1
    extra_materials = int(avatar.effects.get(extra_effect_key, 0) or 0)
    from src.systems.formation import get_region_formation_effect_value

    extra_materials += int(get_region_formation_effect_value(avatar, extra_effect_key, 0) or 0)
    total_quantity = base_quantity + extra_materials
    
    avatar.add_material(material, total_quantity)
    
    return {material.name: total_quantity}


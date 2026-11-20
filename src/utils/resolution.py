from __future__ import annotations
from typing import Any, Type, Optional, List, Union
from dataclasses import dataclass

from src.utils.normalize import normalize_goods_name, normalize_name, normalize_avatar_name
from src.classes.items.elixir import elixirs_by_name, Elixir
from src.classes.items.elixir import elixirs_by_id
from src.classes.items.weapon import weapons_by_name, Weapon
from src.classes.items.weapon import weapons_by_id
from src.classes.items.auxiliary import auxiliaries_by_name, Auxiliary
from src.classes.items.auxiliary import auxiliaries_by_id
from src.classes.material import materials_by_name, Material
from src.classes.material import materials_by_id
from src.systems.cultivation import Realm

@dataclass
class ResolutionResult:
    """Resolution result wrapper."""
    obj: Any | None              # resolved object instance
    resolved_type: Type | None   # type (class) of the object
    is_valid: bool               # whether resolution succeeded
    error_msg: str = ""          # error message
    
    @property
    def name(self) -> str:
        """Try to get the object's name."""
        if self.obj and hasattr(self.obj, "name"):
            return self.obj.name
        return ""

def resolve_query(
    query: Any, 
    world: Any = None, 
    expected_types: Optional[list[Type]] = None
) -> ResolutionResult:
    """
    Unified resolution entry point.
    
    Args:
        query: object to resolve (a string name or an object instance)
        world: world context (used to look up Avatar, Region)
        expected_types: list of expected types. If given, only these types are tried, in order.
                        Supported types: Material, Weapon, Elixir, Auxiliary, Region, Avatar, Realm and similar classes.
                        Class objects must be passed directly; string names are no longer supported.
    """
    if query is None:
        return ResolutionResult(None, None, False, "Empty query")

    # 0. Fast path: already an instance of an expected type
    if expected_types:
        for t in expected_types:
            if isinstance(query, t):
                return _success(query, t)
    
    # Not a string and missed the fast path above, so the wrong object was probably passed
    # Strict mode: it matched none of expected_types and cannot pass the string lookup below either.
    # Fail right away unless query is a string that can be looked up.
    if not isinstance(query, str):
        return ResolutionResult(None, None, False, f"Unsupported non-string input type: {type(query)}")

    if not query:
        return ResolutionResult(None, None, False, "Empty query string")

    # Prepare the list of checks
    checks = []
    
    # If no expected types are given, check all of them
    if not expected_types:
        checks = ["realm", "goods", "region", "avatar"]
    else:
        # Build the check order from the expected types
        for t in expected_types:
            # must be a class object
            if not isinstance(t, type):
                 # Could raise here or ignore; after the refactor, callers are assumed to be fixed.
                 continue

            t_name = t.__name__
            
            if t_name in ["Material", "Weapon", "Elixir", "Auxiliary"]:
                if "goods" not in checks: checks.append("goods")
            elif t_name == "Region" or t_name == "CityRegion" or t_name == "SectRegion" or t_name == "CultivateRegion":
                if "region" not in checks: checks.append("region")
            elif t_name == "Avatar":
                if "avatar" not in checks: checks.append("avatar")
            elif t_name == "Realm":
                if "realm" not in checks: checks.append("realm")

    # Run the checks
    for check in checks:
        if check == "realm":
            res = _resolve_realm(query) # Realm rarely needs much normalization; handled internally
            if res: return _success(res, Realm)
            
        elif check == "goods":
            # Item resolution
            obj = _resolve_goods(query)
            if obj: return _success(obj, type(obj))
            
        elif check == "region" and world:
            obj = _resolve_region(query, world)
            if obj: return _success(obj, type(obj))
            
        elif check == "avatar" and world:
            obj = _resolve_avatar(query, world)
            if obj: return _success(obj, type(obj))

    return ResolutionResult(None, None, False, f"Unable to resolve: {query}")

def _success(obj: Any, type_cls: Type) -> ResolutionResult:
    return ResolutionResult(obj, type_cls, True)

# --- Internal resolution logic ---

def _resolve_goods(name: str) -> Any | None:
    """Resolve items / equipment / elixirs."""
    item_id = _parse_int_id(name)
    if item_id is not None:
        if item_id in elixirs_by_id:
            return elixirs_by_id[item_id]
        if item_id in weapons_by_id:
            return weapons_by_id[item_id]
        if item_id in auxiliaries_by_id:
            return auxiliaries_by_id[item_id]
        if item_id in materials_by_id:
            return materials_by_id[item_id]

    norm = normalize_goods_name(name)
    
    # 1. Elixirs (return the first in the list)
    if norm in elixirs_by_name:
        return elixirs_by_name[norm][0]
        
    # 2. Weapons
    if norm in weapons_by_name:
        return weapons_by_name[norm]
        
    # 3. Auxiliary equipment
    if norm in auxiliaries_by_name:
        return auxiliaries_by_name[norm]
        
    # 4. Materials
    if norm in materials_by_name:
        return materials_by_name[norm]
        
    return None

def _resolve_realm(name: str) -> Realm | None:
    """Resolve a realm."""
    try:
        # Try matching the value directly
        return Realm(name)
    except ValueError:
        pass
    
    # Try matching the enum name
    for r in Realm:
        if r.name == name or r.value == name:
            return r
    return None

def _resolve_region(name: str, world: Any) -> Any | None:
    """Resolve a region by scanning regions.values(), avoiding an extra name index."""
    if not hasattr(world, 'map'):
        return None
    
    regions = getattr(world.map, "regions", {})
    if not regions:
        return None

    region_id = _parse_int_id(name)
    if region_id is not None:
        region = regions.get(region_id) or regions.get(str(region_id))
        if region is not None:
            return region
    
    norm = normalize_name(name)
    
    # 1. Exact / normalized match
    for region in regions.values():
        if region.name == name or region.name == norm:
            return region
    
    # 2. Substring match (if unique)
    candidates = [r for r in regions.values() if (norm in r.name) or (name in r.name)]
    if len(candidates) == 1:
        return candidates[0]
        
    # 3. Sect name match (resolves to the sect headquarters)
    from src.classes.core.sect import sects_by_name
    from src.classes.sect_metadata import get_sect_region_by_sect_id
    sect = sects_by_name.get(name) or sects_by_name.get(norm)
    if sect:
        return get_sect_region_by_sect_id(world, int(getattr(sect, "id", -1)))
            
    return None

def _resolve_avatar(name: str, world: Any) -> Any | None:
    """Resolve an avatar."""
    if not hasattr(world, 'avatar_manager'):
        return None

    manager = world.avatar_manager
    avatar = None
    if hasattr(manager, "get_avatar"):
        avatar = manager.get_avatar(name)
    else:
        avatar = getattr(manager, "avatars", {}).get(str(name))
    if avatar is not None:
        return avatar
        
    norm = normalize_avatar_name(name)
    
    # Linear scan (performance note: may need a dict lookup if there are very many avatars)
    # Assumes avatar_manager.avatars is dict[id, Avatar]
    for avatar in manager.avatars.values():
        if avatar.name == norm:
            return avatar
            
    return None


def _parse_int_id(value: str) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None

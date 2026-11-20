from __future__ import annotations

import json
from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


def load_effect_from_str(value: object) -> dict[str, Any] | list[dict[str, Any]]:
    """
    Parse an effects field into a dict or list (relaxed JSON is supported).
    
    Supported formats:
    1. Standard JSON: {"extra_battle_strength_points": 3}
    2. Single quotes: {'extra_battle_strength_points': 3}
    3. Unquoted keys: {extra_battle_strength_points: 3}
    4. Mixed: {extra_battle_strength_points: 3, 'legal_actions': ['DevourPeople']}
    5. Conditional array: [{when: 'condition', effect1: value1}, ...]
    
    - Returns {} when value is None / empty string / 'nan'
    - Returns {} when parsing fails
    - May return a dict (single effect) or list[dict] (multiple conditional effects)
    """
    if value is None:
        return {}
    if isinstance(value, (dict, list)):
        return value
    s = str(value).strip()
    if not s or s == "nan":
        return {}
    
    # Try standard JSON parsing first
    try:
        obj = json.loads(s)
        if isinstance(obj, (dict, list)):
            return obj
        return {}
    except Exception:
        pass
    
    # Try relaxed parsing: single quotes to double quotes + quote bare keys
    try:
        import re
        
        # 1. First protect everything inside quotes (both single- and double-quoted strings)
        strings = []
        def save_string(match):
            strings.append(match.group(0))
            return f"__STRING_{len(strings)-1}__"
        
        relaxed = s
        # Protect double-quoted strings
        relaxed = re.sub(r'"(?:[^"\\]|\\.)*"', save_string, relaxed)
        # Protect single-quoted strings
        relaxed = re.sub(r"'(?:[^'\\]|\\.)*'", save_string, relaxed)
        
        # 2. Quote unquoted keys (all strings are protected at this point)
        # Match: identifier after a start position + colon
        relaxed = re.sub(r'([{\[,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*):', r'\1"__KEY_\2__"\3:', relaxed)
        
        # 3. Restore strings and convert single quotes to double quotes
        for i, s_val in enumerate(strings):
            # Single-quoted string: convert to double quotes
            if s_val.startswith("'"):
                # Inner double quotes must be escaped, but restore the __STRING_ placeholders first
                content = s_val[1:-1]  # strip the single quotes
                # Restore inner string placeholders
                for j, inner_str in enumerate(strings):
                    if f"__STRING_{j}__" in content and j != i:
                        content = content.replace(f"__STRING_{j}__", inner_str)
                # Escape
                content = content.replace('\\', '\\\\').replace('"', '\\"')
                s_val = f'"{content}"'
            relaxed = relaxed.replace(f"__STRING_{i}__", s_val)
        
        # 4. Restore keys (drop the __KEY_ markers)
        relaxed = relaxed.replace('"__KEY_', '"').replace('__"', '"')
        
        # 5. Try to parse
        obj = json.loads(relaxed)
        if isinstance(obj, (dict, list)):
            return obj
        return {}
    except Exception:
        return {}


def _evaluate_conditional_effect(effect: dict[str, Any] | list[dict[str, Any]], avatar: "Avatar") -> dict[str, Any]:
    """
    Evaluate conditional effects and return the effect dict that actually applies.
    
    Three formats are supported:
    1. Plain dict (unconditional): {"extra_battle_strength_points": 1}
    2. Conditional dict: {"extra_battle_strength_points": 2, "when": "avatar.weapon.weapon_type == WeaponType.SWORD"}
    3. Conditional array: [{"extra_battle_strength_points": 2, "when": "..."}, {...}]
    
    Args:
        effect: raw effect config (dict or list)
        avatar: the current avatar
    
    Returns:
        the effective effect dict after evaluation (all effects whose conditions hold, merged)
    """
    from src.classes.weapon_type import WeaponType
    from src.systems.cultivation import Realm
    from src.classes.alignment import Alignment
    
    # Build a safe eval context
    safe_context = {
        "__builtins__": {},
        "avatar": avatar,
        "WeaponType": WeaponType,
        "Realm": Realm,
        "Alignment": Alignment,
        # Common builtins
        "any": any,
        "all": all,
        "len": len,
        "set": set,
        "list": list,
        "max": max,
        "min": min,
    }
    
    def _check_condition(when_expr: str) -> bool:
        """Check whether a condition expression is true"""
        if not when_expr:
            return True
        try:
            return bool(eval(when_expr, safe_context, {}))
        except Exception:
            # Treat a failed condition evaluation as False
            return False
    
    def _process_single_effect(eff: dict[str, Any]) -> dict[str, Any]:
        """Process a single effect dict: check its condition and return the part that applies"""
        if not isinstance(eff, dict):
            return {}
        
        when_expr = eff.get("when")
        if when_expr is None:
            # Unconditional effect: return as is
            return eff
        
        # Conditional effect: check the condition
        if not _check_condition(when_expr):
            return {}
        
        # Condition holds: return every field except when
        return {k: v for k, v in eff.items() if k != "when"}
    
    # Handle list format (multiple conditional effects)
    if isinstance(effect, list):
        result = {}
        for item in effect:
            evaluated = _process_single_effect(item)
            result = _merge_effects(result, evaluated)
        return result
    
    # Handle dict format (single effect)
    return _process_single_effect(effect)


def _merge_effects(base: dict[str, object], addition: dict[str, object]) -> dict[str, object]:
    """
    Merge two effects dicts:
    - lists (e.g. legal_actions): deduplicated union
    - numbers: summed
    - others: the latter overrides the former
    Returns a new dict without modifying the inputs.
    """
    if not base and not addition:
        return {}
    merged: dict[str, object] = dict(base) if base else {}
    for key, val in (addition or {}).items():
        if key in merged:
            old = merged[key]
            if isinstance(old, list) and isinstance(val, list):
                # Deduplicated union, preserving relative order
                seen: set[object] = set()
                result: list[object] = []
                for x in old + val:
                    if x in seen:
                        continue
                    seen.add(x)
                    result.append(x)
                merged[key] = result
            elif isinstance(old, (int, float)) and isinstance(val, (int, float)):
                merged[key] = old + val
            else:
                merged[key] = val
        else:
            merged[key] = val
    return merged


def build_effects_map_from_df(
    data: list[dict[str, Any]],
    key_column: str,
    parse_key: Callable[[str], Any],
    effects_column: str = "effects",
) -> dict[Any, dict[str, object]]:
    """
    Build a {key -> effects} mapping from config rows:
    - key_column: column holding the key (string), parsed into the target key (e.g. an Enum) via parse_key
    - effects_column: string column, parsed with load_effect_from_str
    Rows that fail to parse or are empty are ignored.
    """
    effects_map: dict[Any, dict[str, object]] = {}
    if not data:
        return effects_map
    for row in data:
        raw_key = str(row.get(key_column, "")).strip()
        if not raw_key or raw_key == "nan":
            continue
        try:
            key = parse_key(raw_key)
        except Exception:
            continue
        eff = load_effect_from_str(row.get(effects_column, ""))
        if eff:
            effects_map[key] = eff
    return effects_map


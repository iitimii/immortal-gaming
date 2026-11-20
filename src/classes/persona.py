import random
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

from src.utils.df import game_configs, get_str, get_list_str, get_int
from src.utils.config import CONFIG
from src.classes.effect import load_effect_from_str
from src.classes.rarity import Rarity, get_rarity_from_str

if TYPE_CHECKING:
    # Only for type checking, to avoid circular imports at runtime
    from src.classes.core.avatar import Avatar

@dataclass
class Persona:
    """
    Avatar persona
    Includes personality, talents and other avatar traits
    """
    id: int
    key: str
    name: str
    desc: str
    exclusion_keys: List[str]
    rarity: Rarity
    condition: str
    effects: dict[str, object]
    effect_desc: str = ""
    
    @property
    def weight(self) -> float:
        """Get the sampling weight by rarity."""
        return self.rarity.weight

    def get_info(self) -> str:
        return self.name

    def get_detailed_info(self) -> str:
        from src.i18n import t
        desc_part = f" ({self.desc})" if self.desc else ""
        effect_part = t("\nEffect: {effect_desc}", effect_desc=self.effect_desc) if self.effect_desc else ""
        return f"{self.name}{desc_part}{effect_part}"
    
    def get_colored_info(self) -> str:
        """Get info with color markup for frontend rendering."""
        r, g, b = self.rarity.color_rgb
        return f"<color:{r},{g},{b}>{self.name}</color>"

    def get_structured_info(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "desc": self.desc,
            "key": self.key,
            "rarity": self.rarity.level.value,
            "color": self.rarity.color_rgb,
            "effect_desc": self.effect_desc,
        }

def _load_personas() -> tuple[dict[int, Persona], dict[str, Persona]]:
    """Load persona data from the config table."""
    personas_by_id: dict[int, Persona] = {}
    personas_by_name: dict[str, Persona] = {}
    
    persona_df = game_configs["persona"]
    for row in persona_df:
        # Parse the exclusion_keys string into a list of strings
        exclusion_keys = get_list_str(row, "exclusion_keys")
        
        # Parse rarity
        rarity_str = get_str(row, "rarity", "N").upper()
        rarity = get_rarity_from_str(rarity_str)
        
        # Parse effects
        effects = load_effect_from_str(get_str(row, "effects"))
        from src.classes.effect import format_effects_to_text
        effect_desc = format_effects_to_text(effects)
        
        persona = Persona(
            id=get_int(row, "id"),
            key=get_str(row, "key").upper(),
            name=get_str(row, "name"),
            desc=get_str(row, "desc"),
            exclusion_keys=exclusion_keys,
            rarity=rarity,
            condition=get_str(row, "condition"),
            effects=effects,
            effect_desc=effect_desc,
        )
        personas_by_id[persona.id] = persona
        personas_by_name[persona.name] = persona
    
    return personas_by_id, personas_by_name

# Load persona data from the config table
personas_by_id: dict[int, Persona] = {}
personas_by_name: dict[str, Persona] = {}

def reload():
    """Reload data while preserving the global dict references."""
    new_id, new_name = _load_personas()
    
    personas_by_id.clear()
    personas_by_id.update(new_id)
    
    personas_by_name.clear()
    personas_by_name.update(new_name)

# Run once at module import
reload()

def _is_persona_allowed(persona_id: int, already_selected_ids: set[int], avatar: Optional["Avatar"]) -> bool:
    """
    Unified check: whether a persona may be selected (conditions + exclusions).
    """
    persona = personas_by_id[persona_id]
    # Condition check
    if avatar is not None and persona.condition:
        allowed = bool(eval(persona.condition, {"__builtins__": {}}, {"avatar": avatar}))
        if not allowed:
            return False
    # Exclusion check against already selected ones (two-way, via Key)
    for sid in already_selected_ids:
        other = personas_by_id[sid]
        if (persona.key in other.exclusion_keys) or (other.key in persona.exclusion_keys):
            return False
    return True

def get_random_compatible_personas(num_personas: int = 2, avatar: Optional["Avatar"] = None) -> List[Persona]:
    """
    Randomly select the given number of mutually compatible personas
    
    Args:
        num_personas: number of personas to select, default 2
        avatar: optional; if given, filter by persona.condition
    
    Returns:
        List[Persona]: list of mutually compatible personas
        
    Raises:
        ValueError: if not enough compatible personas can be found
    """
    # Initial candidates: filter by condition if an avatar is given; otherwise all
    initial_ids = set(personas_by_id.keys())
    if avatar is not None:
        initial_ids = {pid for pid in initial_ids if _is_persona_allowed(pid, set(), avatar)}

    selected_personas: List[Persona] = []
    selected_ids: set[int] = set()

    for i in range(num_personas):
        # Filter again against the current selection (exclusions + conditions)
        available_ids = [pid for pid in initial_ids if pid not in selected_ids and _is_persona_allowed(pid, selected_ids, avatar)]
        if not available_ids:
            raise ValueError(f"Could only find {i} compatible personas, cannot satisfy the required {num_personas}")

        candidates: List[Persona] = [personas_by_id[pid] for pid in available_ids]
        weights: List[float] = [max(0.0, c.weight) for c in candidates]
        selected_persona = random.choices(candidates, weights=weights, k=1)[0]
        selected_personas.append(selected_persona)
        selected_ids.add(selected_persona.id)

    return selected_personas

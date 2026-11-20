import random
from typing import Optional, Union
from dataclasses import dataclass

from src.utils.df import game_configs, get_str, get_int
from src.classes.core.avatar import Gender
from src.i18n.locale_registry import uses_space_separated_names


@dataclass
class LastName:
    """Surname."""
    name: str
    sect_id: Optional[int]
    
@dataclass
class GivenName:
    """Given name."""
    name: str
    gender: Gender
    sect_id: Optional[int]


class NameManager:
    """Name manager."""
    
    def __init__(self):
        # Common surnames for rogue cultivators
        self.common_last_names: list[str] = []
        # Surnames by sect {sect_id: [surnames]}
        self.sect_last_names: dict[int, list[str]] = {}
        
        # Common given names for rogue cultivators {Gender: [given names]}
        self.common_given_names: dict[Gender, list[str]] = {
            Gender.MALE: [],
            Gender.FEMALE: []
        }
        # Given names by sect and gender {sect_id: {Gender: [given names]}}
        self.sect_given_names: dict[int, dict[Gender, list[str]]] = {}
        
        self._load_names()
    
    def _load_names(self):
        """Load name data from CSV."""
        # Clear existing data
        self.common_last_names.clear()
        self.sect_last_names.clear()
        for g_list in self.common_given_names.values():
            g_list.clear()
        self.sect_given_names.clear()
        
        # Load surnames (no separate _en suffix; config/df already handles loading)
        last_name_df = game_configs.get("last_name", [])
            
        if last_name_df:
            for row in last_name_df:
                name = get_str(row, "last_name")
                sect_id = get_int(row, "sect_id")
                
                if sect_id > 0:
                    if sect_id not in self.sect_last_names:
                        self.sect_last_names[sect_id] = []
                    self.sect_last_names[sect_id].append(name)
                else:
                    self.common_last_names.append(name)
        
        # Load given names
        given_name_df = game_configs.get("given_name", [])
            
        if given_name_df:
            for row in given_name_df:
                name = get_str(row, "given_name")
                gender_val = get_int(row, "gender") # 0 or 1
                # Assumes 1=Male, 0=Female
                gender = Gender.MALE if gender_val == 1 else Gender.FEMALE
                
                sect_id = get_int(row, "sect_id")
                
                if sect_id > 0:
                    if sect_id not in self.sect_given_names:
                        self.sect_given_names[sect_id] = {Gender.MALE: [], Gender.FEMALE: []}
                    self.sect_given_names[sect_id][gender].append(name)
                else:
                    self.common_given_names[gender].append(name)
    
    def get_random_last_name(self, sect_id: Optional[int] = None) -> str:
        """
        Get a random surname.
        """
        if sect_id and sect_id in self.sect_last_names:
            return random.choice(self.sect_last_names[sect_id])
        return random.choice(self.common_last_names)
    
    def get_random_given_name(self, gender: Gender, sect_id: Optional[int] = None) -> str:
        """
        Get a random given name.
        """
        if sect_id and sect_id in self.sect_given_names:
            sect_names = self.sect_given_names[sect_id][gender]
            if sect_names:
                return random.choice(sect_names)
        return random.choice(self.common_given_names[gender])
    
    def get_random_full_name(self, gender: Gender, sect_id: Optional[int] = None) -> str:
        """
        Get a random full name.
        """
        last_name = self.get_random_last_name(sect_id)
        given_name = self.get_random_given_name(gender, sect_id)
        
        # Handle locale-specific name joining
        from src.classes.language import language_manager
        if uses_space_separated_names(language_manager.current):
            return f"{last_name} {given_name}"
        return last_name + given_name
    
    def get_random_full_name_with_surname(
        self, 
        gender: Gender, 
        surname: str, 
        sect_id: Optional[int] = None
    ) -> str:
        """
        Generate a random full name with the given surname.
        """
        if not surname:
            # No surname given: fall back to a random full name
            return self.get_random_full_name(gender, sect_id)
            
        given_name = self.get_random_given_name(gender, sect_id)
        
        # Handle locale-specific name joining
        from src.classes.language import language_manager
        if uses_space_separated_names(language_manager.current):
            return f"{surname} {given_name}"
        return surname + given_name


# Global singleton
_name_manager = NameManager()


def get_random_name(gender: Gender, sect_name: Optional[str] = None, sect_id: Optional[int] = None) -> str:
    """Get a random full name."""
    # Compatibility: if only sect_name is given without sect_id, it cannot be mapped to an ID here (would need a lookup table)
    # but callers should already be updated or pass only the sect object
    return _name_manager.get_random_full_name(gender, sect_id)


def get_random_name_for_sect(gender: Gender, sect) -> str:
    """
    Generate a name based on the sect (legacy interface).
    """
    sect_id = sect.id if sect is not None else None
    return _name_manager.get_random_full_name(gender, sect_id)


def pick_surname_for_sect(sect) -> str:
    """
    Pick a surname from the sect's common surnames or the global pool (legacy interface).
    """
    sect_id = sect.id if sect is not None else None
    return _name_manager.get_random_last_name(sect_id)


def get_random_name_with_surname(
    gender: Gender, 
    surname: str, 
    sect
) -> str:
    """
    Generate a random full name with the given surname (legacy interface).
    """
    sect_id = sect.id if sect is not None else None
    return _name_manager.get_random_full_name_with_surname(gender, surname, sect_id)


def get_random_name_for_race(gender: Gender, race, sect=None) -> str:
    """
    Yao races use the race name as surname; humans keep the existing sect/common surname rules.
    """
    from src.classes.race import get_race, get_race_surname

    race_obj = get_race(getattr(race, "id", race))
    if not race_obj.is_yao:
        return get_random_name_for_sect(gender, sect)
    surname = get_race_surname(race_obj)
    return _name_manager.get_random_full_name_with_surname(gender, surname, None)


def get_name_with_race_surname(gender: Gender, race, given_name: str | None = None) -> str:
    from src.classes.language import language_manager
    from src.classes.race import get_race, get_race_surname

    race_obj = get_race(getattr(race, "id", race))
    surname = get_race_surname(race_obj)
    if not surname:
        return str(given_name or "").strip() or get_random_name(gender)
    final_given_name = str(given_name or "").strip() or _name_manager.get_random_given_name(gender, None)
    if uses_space_separated_names(language_manager.current):
        return f"{surname} {final_given_name}"
    return surname + final_given_name


def reload():
    """Reload the data."""
    _name_manager._load_names()

from dataclasses import dataclass, field
from src.classes.gender import Gender
from src.classes.race import Race, get_race
from src.systems.time import MonthStamp

@dataclass
class Mortal:
    """
    Lightweight mortal/child data structure.
    Only stores info about non-cultivator children; doesn't take part in complex simulation.
    """
    id: str                 # Unique ID
    name: str               # Name
    gender: Gender          # Gender
    birth_month_stamp: MonthStamp  # Birth timestamp
    race: Race = field(default_factory=lambda: get_race("human"))
    parents: list[str] = field(default_factory=list)      # Parents' Avatar IDs
    born_region_id: int = -1  # Birthplace region ID (-1 means unknown)

    def to_dict(self) -> dict:
        """Convert to a dict."""
        return {
            "id": self.id,
            "name": self.name,
            "gender": self.gender.value,
            "birth_month_stamp": int(self.birth_month_stamp),
            "race_id": getattr(getattr(self, "race", None), "id", "human"),
            "parents": self.parents,
            "born_region_id": self.born_region_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Mortal":
        """Restore from a dict."""
        return cls(
            id=data["id"],
            name=data["name"],
            gender=Gender(data["gender"]),
            birth_month_stamp=MonthStamp(data["birth_month_stamp"]),
            race=get_race(data.get("race_id", "human")),
            parents=data.get("parents", []),
            born_region_id=data.get("born_region_id", -1)
        )

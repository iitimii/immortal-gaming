from dataclasses import dataclass, asdict
from typing import List, Optional
from enum import Enum
from src.systems.time import MonthStamp


class MetricTag(Enum):
    """Predefined metric tags."""
    BREAKTHROUGH = "breakthrough"
    INJURED = "injured"
    RECOVERED = "recovered"
    SECT_JOIN = "sect_join"
    SECT_LEAVE = "sect_leave"
    TECHNIQUE_LEARN = "technique_learn"
    DEATH = "death"
    BATTLE = "battle"
    DUNGEON = "dungeon"


@dataclass
class AvatarMetrics:
    """
    Avatar state snapshot, used to track the avatar's growth trajectory.

    Design principles:
    - Lightweight: only key metrics are recorded
    - Immutable: a snapshot is never modified once created
    - Optional: doesn't affect existing features
    """
    timestamp: MonthStamp
    age: int

    # Cultivation
    cultivation_level: int
    cultivation_progress: int

    # Resources
    hp: float
    hp_max: float
    spirit_stones: int

    # Social
    relations_count: int
    known_regions_count: int

    # Tags
    tags: List[str]

    def to_save_dict(self) -> dict:
        """Convert to a serializable dict (for saving)."""
        return asdict(self)

    @classmethod
    def from_save_dict(cls, data: dict) -> "AvatarMetrics":
        """Rebuild from a dict (for loading)."""
        return cls(**data)

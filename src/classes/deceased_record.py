from dataclasses import dataclass
from typing import Optional


@dataclass
class DeceasedRecord:
    """Lightweight archive of a deceased avatar, independent of the Avatar object and unaffected by cleanup_long_dead_avatars."""

    id: str
    name: str
    gender: str
    age_at_death: int
    realm_at_death: str       # cultivation_progress.realm.value
    stage_at_death: str       # cultivation_progress.stage.value
    death_reason: str
    death_time: int            # MonthStamp int, same semantics as death_info["time"]
    sect_name_at_death: str    # avatar.sect.name if avatar.sect else ""
    alignment_at_death: str    # avatar.alignment.value if avatar.alignment else ""
    backstory: Optional[str] = None
    custom_pic_id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "gender": self.gender,
            "age_at_death": self.age_at_death,
            "realm_at_death": self.realm_at_death,
            "stage_at_death": self.stage_at_death,
            "death_reason": self.death_reason,
            "death_time": self.death_time,
            "sect_name_at_death": self.sect_name_at_death,
            "alignment_at_death": self.alignment_at_death,
            "backstory": self.backstory,
            "custom_pic_id": self.custom_pic_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeceasedRecord":
        fields = cls.__dataclass_fields__
        filtered = {k: data[k] for k in fields if k in data}
        return cls(**filtered)

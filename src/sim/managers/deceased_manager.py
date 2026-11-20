from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

from src.classes.deceased_record import DeceasedRecord


@dataclass
class DeceasedManager:
    """Deceased avatar record manager, independent of AvatarManager and unaffected by cleanup_long_dead_avatars."""

    _records: Dict[str, DeceasedRecord] = field(default_factory=dict)

    def record_death(self, avatar: "Avatar") -> None:
        """Create a DeceasedRecord from an Avatar snapshot, overwriting by id (idempotent)."""
        death_info = avatar.death_info or {}
        record = DeceasedRecord(
            id=avatar.id,
            name=avatar.name,
            gender=avatar.gender.value if hasattr(avatar.gender, "value") else str(avatar.gender),
            age_at_death=avatar.age.age,
            realm_at_death=avatar.cultivation_progress.realm.value,
            stage_at_death=avatar.cultivation_progress.stage.value,
            death_reason=death_info.get("reason", ""),
            death_time=death_info.get("time", 0),
            sect_name_at_death=str(death_info.get("sect_name_at_death", "")),
            alignment_at_death=str(death_info.get("alignment_at_death", "")),
            backstory=avatar.backstory,
            custom_pic_id=avatar.custom_pic_id,
        )
        self._records[avatar.id] = record

    def get_all_records(self) -> List[DeceasedRecord]:
        """Return all records ordered by time of death, newest first."""
        return sorted(self._records.values(), key=lambda r: r.death_time, reverse=True)

    def get_record(self, avatar_id: str) -> Optional[DeceasedRecord]:
        return self._records.get(avatar_id)

    def to_save_list(self) -> List[dict]:
        return [r.to_dict() for r in self._records.values()]

    def load_from_list(self, data: List[dict]) -> None:
        self._records.clear()
        for item in data:
            record = DeceasedRecord.from_dict(item)
            self._records[record.id] = record

    def cleanup_expired_records(self, current_time: object, threshold_years: int = 50) -> int:
        """Clean up lightweight deceased records older than the threshold."""
        to_remove: list[str] = []
        current_month = int(current_time)
        threshold_months = int(threshold_years) * 12
        for avatar_id, record in self._records.items():
            if current_month - int(record.death_time) >= threshold_months:
                to_remove.append(avatar_id)
        for avatar_id in to_remove:
            self._records.pop(avatar_id, None)
        return len(to_remove)

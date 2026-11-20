from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result


@dataclass(slots=True)
class WorldMilestoneRecord:
    """An achieved world "first". Names are snapshotted so the chronicle survives avatar cleanup."""

    key: str
    month_stamp: int
    avatar_ids: list[str] = field(default_factory=list)
    avatar_names: list[str] = field(default_factory=list)
    sect_ids: list[int] = field(default_factory=list)
    sect_names: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)
    event_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "month_stamp": int(self.month_stamp),
            "avatar_ids": list(self.avatar_ids),
            "avatar_names": list(self.avatar_names),
            "sect_ids": list(self.sect_ids),
            "sect_names": list(self.sect_names),
            "detail": dict(self.detail),
            "event_id": self.event_id,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "WorldMilestoneRecord | None":
        if not isinstance(data, dict) or not data.get("key"):
            return None
        try:
            month_stamp = int(data.get("month_stamp", 0))
        except (TypeError, ValueError):
            return None
        detail = data.get("detail")
        return cls(
            key=str(data["key"]),
            month_stamp=month_stamp,
            avatar_ids=_str_list(data.get("avatar_ids")),
            avatar_names=_str_list(data.get("avatar_names")),
            sect_ids=_int_list(data.get("sect_ids")),
            sect_names=_str_list(data.get("sect_names")),
            detail=dict(detail) if isinstance(detail, dict) else {},
            event_id=str(data.get("event_id", "") or ""),
        )


@dataclass
class WorldMilestoneState:
    """World-level chronicle of firsts.

    - ``opened_month``: month of the first detection pass. Everything already true at that
      point is treated as pre-history and seeded silently (see ``src/systems/world_milestones.py``).
    - ``records``: achieved milestones in chronological order.
    - ``avatar_marks``: per-avatar baseline (realm rank, age, bond partner ids) used to detect
      transitions between monthly passes. Only JSON primitives, references stored as IDs.
    """

    opened_month: int | None = None
    records: list[WorldMilestoneRecord] = field(default_factory=list)
    avatar_marks: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def is_open(self) -> bool:
        return self.opened_month is not None

    def is_achieved(self, key: str) -> bool:
        return any(record.key == key for record in self.records)

    def get_record(self, key: str) -> WorldMilestoneRecord | None:
        return next((record for record in self.records if record.key == key), None)

    def add_record(self, record: WorldMilestoneRecord) -> bool:
        if self.is_achieved(record.key):
            return False
        self.records.append(record)
        return True

    def get_records_chronological(self) -> list[WorldMilestoneRecord]:
        # sorted() is stable, so milestones achieved in the same month keep their detection order.
        return sorted(self.records, key=lambda record: int(record.month_stamp))

    def to_save_dict(self) -> dict[str, Any]:
        return {
            "opened_month": self.opened_month,
            "records": [record.to_dict() for record in self.records],
            "avatar_marks": {
                str(avatar_id): dict(marks)
                for avatar_id, marks in self.avatar_marks.items()
            },
        }

    def load_from_dict(self, data: Any) -> None:
        self.opened_month = None
        self.records = []
        self.avatar_marks = {}
        if not isinstance(data, dict):
            return
        opened_month = data.get("opened_month")
        if opened_month is not None:
            try:
                self.opened_month = int(opened_month)
            except (TypeError, ValueError):
                self.opened_month = None
        for item in data.get("records", []) or []:
            record = WorldMilestoneRecord.from_dict(item)
            if record is not None:
                self.add_record(record)
        marks = data.get("avatar_marks", {})
        if isinstance(marks, dict):
            self.avatar_marks = {
                str(avatar_id): dict(value)
                for avatar_id, value in marks.items()
                if isinstance(value, dict)
            }

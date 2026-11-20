from __future__ import annotations

from dataclasses import dataclass
from typing import Any


STATUS_WAR = "war"
STATUS_PEACE = "peace"


@dataclass(slots=True)
class SectWar:
    """
    World-level sect diplomacy status record.

    The first version only distinguishes war/peace, keeping key timestamps such as start, latest battle and peace start.
    """

    sect_a_id: int
    sect_b_id: int
    status: str
    start_month: int
    last_battle_month: int | None = None
    peace_start_month: int | None = None
    reason: str = ""

    @classmethod
    def normalize_pair(cls, sect_a_id: int, sect_b_id: int) -> tuple[int, int]:
        a = int(sect_a_id)
        b = int(sect_b_id)
        return (a, b) if a <= b else (b, a)

    @classmethod
    def create(
        cls,
        *,
        sect_a_id: int,
        sect_b_id: int,
        status: str,
        current_month: int,
        reason: str = "",
        last_battle_month: int | None = None,
        peace_start_month: int | None = None,
    ) -> "SectWar":
        a, b = cls.normalize_pair(sect_a_id, sect_b_id)
        return cls(
            sect_a_id=a,
            sect_b_id=b,
            status=str(status or STATUS_PEACE),
            start_month=int(current_month),
            last_battle_month=last_battle_month,
            peace_start_month=peace_start_month,
            reason=str(reason or ""),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SectWar":
        a, b = cls.normalize_pair(
            int(data.get("sect_a_id", 0)),
            int(data.get("sect_b_id", 0)),
        )
        return cls(
            sect_a_id=a,
            sect_b_id=b,
            status=str(data.get("status", STATUS_PEACE) or STATUS_PEACE),
            start_month=int(data.get("start_month", 0) or 0),
            last_battle_month=(
                int(data["last_battle_month"])
                if data.get("last_battle_month") is not None
                else None
            ),
            peace_start_month=(
                int(data["peace_start_month"])
                if data.get("peace_start_month") is not None
                else None
            ),
            reason=str(data.get("reason", "") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sect_a_id": int(self.sect_a_id),
            "sect_b_id": int(self.sect_b_id),
            "status": str(self.status),
            "start_month": int(self.start_month),
            "last_battle_month": int(self.last_battle_month) if self.last_battle_month is not None else None,
            "peace_start_month": int(self.peace_start_month) if self.peace_start_month is not None else None,
            "reason": str(self.reason or ""),
        }

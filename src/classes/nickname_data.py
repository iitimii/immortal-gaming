"""
Nickname data class
"""
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Nickname:
    """
    Nickname data class
    Holds the nickname and the reason behind it
    """
    value: str
    reason: str
    created_year: int
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Nickname":
        if not data:
            return None
        return cls(
            value=data["value"],
            reason=data["reason"],
            created_year=data.get("created_year", 0)
        )
    
    def __str__(self) -> str:
        return self.value


"""
event class
"""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional
import uuid
import time

from src.systems.time import Month, Year, MonthStamp, get_date_str

if TYPE_CHECKING:
    from src.classes.event_observation import EventObservation

@dataclass
class Event:
    month_stamp: MonthStamp
    content: str
    # IDs of related avatars; None if unrelated to any avatar
    related_avatars: Optional[List[str]] = None
    # IDs of related sects; None if unrelated to any sect
    related_sects: Optional[List[int]] = None
    # Whether this is a major event (long-term memory); default False (minor / short-term memory)
    is_major: bool = False
    # Whether this is a story event (not indexed into memory); default False
    is_story: bool = False
    # Fact event type, used for propagation and rendering
    event_type: str = ""
    # Template key the frontend can use for localized rendering
    render_key: Optional[str] = None
    # Frontend template render parameters
    render_params: Optional[dict[str, Any]] = None
    # Display snapshot of the subjects at event time, so the event panel can still show names after an avatar is manually deleted or cleaned up
    subject_snapshots: dict[str, str] = field(default_factory=dict)
    # Unique ID used for deduplication
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Creation timestamp (Unix timestamp float)
    created_at: float = field(default_factory=time.time)
    # Observation attached at runtime; persisted centrally by EventManager
    observations: List["EventObservation"] = field(default_factory=list, repr=False, compare=False)

    def __str__(self) -> str:
        return f"{get_date_str(int(self.month_stamp))}: {self.content}"
    
    def to_dict(self) -> dict:
        """Convert to a serializable dict."""
        return {
            "month_stamp": int(self.month_stamp),
            "content": self.content,
            "related_avatars": self.related_avatars,
            "related_sects": self.related_sects,
            "is_major": self.is_major,
            "is_story": self.is_story,
            "event_type": self.event_type,
            "render_key": self.render_key,
            "render_params": self.render_params,
            "subject_snapshots": self.subject_snapshots,
            "id": self.id,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        """Rebuild an Event from a dict."""
        return cls(
            month_stamp=MonthStamp(data["month_stamp"]),
            content=data["content"],
            related_avatars=data.get("related_avatars"),
            related_sects=data.get("related_sects"),
            is_major=data.get("is_major", False),
            is_story=data.get("is_story", False),
            event_type=data.get("event_type", ""),
            render_key=data.get("render_key"),
            render_params=data.get("render_params"),
            subject_snapshots=dict(data.get("subject_snapshots") or {}),
            id=data.get("id", str(uuid.uuid4())),
            created_at=data.get("created_at", time.time())
        )

class NullEvent:
    """
    Null event singleton class; keeps the same minimal interface as Event so callers don't error when accessing attributes.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize only once
            cls._instance.month_stamp = MonthStamp(0)
            cls._instance.content = ""
            cls._instance.related_avatars = None
            cls._instance.related_sects = None
            cls._instance.is_major = False
            cls._instance.is_story = False
            cls._instance.event_type = ""
            cls._instance.render_key = None
            cls._instance.render_params = None
            cls._instance.id = "NULL_EVENT"
            cls._instance.observations = []
        return cls._instance
    
    def __str__(self) -> str:
        return ""
    
    def __bool__(self) -> bool:
        """Make NullEvent instances falsy in boolean context."""
        return False
    
    def to_dict(self) -> dict:
        """Keep the serialization interface."""
        return {
            "month_stamp": int(self.month_stamp),
            "content": self.content,
            "related_avatars": self.related_avatars,
            "related_sects": self.related_sects,
            "is_major": self.is_major,
            "is_story": self.is_story,
            "event_type": self.event_type,
            "render_key": self.render_key,
            "render_params": self.render_params,
            "subject_snapshots": {},
            "id": self.id,
        }

# Global singleton instance
NULL_EVENT = NullEvent()

def is_null_event(event) -> bool:
    """Convenience function to check whether an event is the null event."""
    return event is NULL_EVENT

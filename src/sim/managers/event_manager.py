"""
Event manager.

Provides a facade for writing and querying events, backed preferably by SQLite storage.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional, TYPE_CHECKING
from src.classes.event_query import EventAudience, EventMemoryScope, EventPage, EventQuery, matches_memory_scope

if TYPE_CHECKING:
    from src.classes.event import Event
    from src.classes.event_storage import EventStorage


class EventManager:
    """
    Event manager: uses SQLite for persistent storage.

    Exposes a unified event interface:
    - add_event: add an event
    - get_recent_events: get recent events
    - get_events_by_avatar: query by avatar
    - get_events_between: query by avatar pair
    - get_major_events_by_avatar: get an avatar's major events
    - get_minor_events_by_avatar: get an avatar's minor events
    - get_major_events_between: get an avatar pair's major events
    - get_minor_events_between: get an avatar pair's minor events
    """

    def __init__(self, storage: Optional["EventStorage"] = None):
        """
        Initialize the event manager.

        Args:
            storage: SQLite storage layer. If None, in-memory mode is used (for tests only).
        """
        self._storage = storage
        self._subject_resolver: Callable[[str], object | None] | None = None
        # In-memory fallback, used only when storage is None, mainly for tests.
        self._memory_events: List["Event"] = []

    @classmethod
    def create_with_db(cls, db_path: Path) -> "EventManager":
        """
        Factory method: create an event manager backed by SQLite.

        Args:
            db_path: database file path.

        Returns:
            A configured EventManager instance.
        """
        from src.classes.event_storage import EventStorage
        storage = EventStorage(db_path)
        return cls(storage)

    @classmethod
    def create_in_memory(cls) -> "EventManager":
        """
        Factory method: create an in-memory event manager (for tests only).

        Returns:
            An in-memory EventManager instance.
        """
        return cls(storage=None)

    def set_subject_resolver(self, resolver: Callable[[str], object | None]) -> None:
        self._subject_resolver = resolver

    def _capture_subject_snapshots(self, event: "Event") -> None:
        if self._subject_resolver is None:
            return
        snapshots = dict(getattr(event, "subject_snapshots", {}) or {})
        for avatar_id in getattr(event, "related_avatars", None) or []:
            avatar_id_str = str(avatar_id)
            if avatar_id_str in snapshots:
                continue
            avatar = self._subject_resolver(avatar_id_str)
            name = getattr(avatar, "name", None) if avatar is not None else None
            if name:
                snapshots[avatar_id_str] = str(name)
        event.subject_snapshots = snapshots

    def add_event(self, event: "Event") -> None:
        """
        Add an event.

        If SQLite storage is available, write to the database immediately.
        Otherwise store it in the in-memory fallback list.
        """
        # Filter out empty events.
        from src.classes.event import is_null_event
        if is_null_event(event):
            return

        self._capture_subject_snapshots(event)

        if self._storage:
            self._storage.add_event(event)
        else:
            # In-memory fallback mode.
            self._memory_events.append(event)

    @staticmethod
    def _is_observed_by(event: "Event", avatar_id: str) -> bool:
        avatar_id = str(avatar_id)
        if event.related_avatars and avatar_id in {str(item) for item in event.related_avatars}:
            return True
        for observation in getattr(event, "observations", []) or []:
            if str(getattr(observation, "observer_avatar_id", "")) == avatar_id:
                return True
        return False

    @staticmethod
    def _render_for_observer(event: "Event", avatar_id: str) -> "Event":
        from src.classes.event import Event
        from src.classes.event_renderer import render_observed_event

        avatar_id = str(avatar_id)
        matched_observation = None
        for observation in getattr(event, "observations", []) or []:
            if str(getattr(observation, "observer_avatar_id", "")) == avatar_id:
                matched_observation = {
                    "propagation_kind": getattr(observation, "propagation_kind", "self_direct"),
                    "subject_avatar_id": getattr(observation, "subject_avatar_id", None),
                }
                break

        if matched_observation is None and event.related_avatars and avatar_id in {str(item) for item in event.related_avatars}:
            matched_observation = {
                "propagation_kind": "self_direct",
                "subject_avatar_id": avatar_id,
            }

        if matched_observation is None:
            return event

        rendered = Event.from_dict(event.to_dict())
        rendered.content = render_observed_event(rendered, matched_observation)
        return rendered

    def get_recent_events(self, limit: int = 100) -> List["Event"]:
        """Get recent events (chronological order)."""
        if self._storage:
            return self._storage.get_recent_events(limit=limit)
        else:
            return self._memory_events[-limit:]

    def get_events_by_avatar(self, avatar_id: str, *, limit: int = 50) -> List["Event"]:
        """Get events related to an avatar (chronological order)."""
        return self.query_events(EventQuery(avatar_ids=(str(avatar_id),), limit=limit, chronological=True))

    def get_events_between(self, avatar_id1: str, avatar_id2: str, *, limit: int = 50) -> List["Event"]:
        """Get events between two avatars (chronological order)."""
        return self.query_events(EventQuery(avatar_ids=(str(avatar_id1), str(avatar_id2)), limit=limit, chronological=True))

    def get_major_events_by_avatar(self, avatar_id: str, *, limit: int = 10) -> List["Event"]:
        """Get an avatar's major events (long-term memory, chronological order)."""
        return self.query_events(EventQuery(avatar_ids=(str(avatar_id),), audience=EventAudience.OBSERVED,
                                            memory_scope=EventMemoryScope.MAJOR, limit=limit, chronological=True))

    def get_minor_events_by_avatar(self, avatar_id: str, *, limit: int = 10) -> List["Event"]:
        """Get an avatar's minor events (short-term memory, chronological order)."""
        return self.query_events(EventQuery(avatar_ids=(str(avatar_id),), audience=EventAudience.OBSERVED,
                                            memory_scope=EventMemoryScope.MINOR, limit=limit, chronological=True))

    def get_major_events_between(self, avatar_id1: str, avatar_id2: str, *, limit: int = 10) -> List["Event"]:
        """Get major events between two avatars (long-term memory, chronological order)."""
        return self.query_events(EventQuery(avatar_ids=(str(avatar_id1), str(avatar_id2)),
                                            memory_scope=EventMemoryScope.MAJOR, limit=limit, chronological=True))

    def get_minor_events_between(self, avatar_id1: str, avatar_id2: str, *, limit: int = 10) -> List["Event"]:
        """Get minor events between two avatars (short-term memory, chronological order)."""
        return self.query_events(EventQuery(avatar_ids=(str(avatar_id1), str(avatar_id2)),
                                            memory_scope=EventMemoryScope.MINOR, limit=limit, chronological=True))

    def query_events(self, query: EventQuery) -> List["Event"]:
        """Execute the same semantic query contract in either storage backend."""
        events = self.query_page(query).events
        return list(reversed(events)) if query.chronological else events

    def query_page(self, query: EventQuery) -> EventPage["Event"]:
        """Return one page using the same EventQuery semantics in both backends."""
        if self._storage:
            return self._storage.query_page(query)

        if query.audience is EventAudience.OBSERVED and len(query.avatar_ids) != 1:
            raise ValueError("Observed event queries require exactly one avatar")
        result: list["Event"] = []
        start_index = int(query.cursor or "0")
        matched_index = 0
        for event in reversed(self._memory_events):
            related = {str(item) for item in (event.related_avatars or [])}
            if query.audience is EventAudience.OBSERVED:
                matched = self._is_observed_by(event, query.avatar_ids[0])
            else:
                matched = all(avatar_id in related for avatar_id in query.avatar_ids)
            if not matched or not matches_memory_scope(event, query.memory_scope):
                continue
            if query.sect_id is not None and query.sect_id not in (getattr(event, "related_sects", None) or []):
                continue
            if matched_index < start_index:
                matched_index += 1
                continue
            result.append(self._render_for_observer(event, query.avatar_ids[0]) if query.audience is EventAudience.OBSERVED else event)
            matched_index += 1
            if len(result) > query.limit:
                break
        has_more = len(result) > query.limit
        result = result[:query.limit]
        return EventPage(result, str(start_index + len(result)) if has_more else None)

    # --- Paginated query interface (new) ---

    def get_events_paginated(
        self,
        avatar_id: Optional[str] = None,
        avatar_id_pair: Optional[tuple[str, str]] = None,
        sect_id: Optional[int] = None,
        major_scope: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> tuple[List["Event"], Optional[str], bool]:
        """
        Query events with pagination.

        Args:
            avatar_id: filter by a single avatar.
            avatar_id_pair: pair query (events between two avatars).
            sect_id: filter by a single sect.
            cursor: pagination cursor; fetch events before this position.
            limit: page size.

        Returns:
            (events, next_cursor, has_more)
            - events: list of events (reverse chronological, newest first).
            - next_cursor: cursor for the next page; None means no more.
            - has_more: whether more data exists.
        """
        avatar_ids = avatar_id_pair or ((avatar_id,) if avatar_id else ())
        page = self.query_page(EventQuery(
            avatar_ids=tuple(str(item) for item in avatar_ids),
            sect_id=sect_id,
            memory_scope=EventMemoryScope(major_scope) if major_scope in {"major", "minor"} else EventMemoryScope.ALL,
            cursor=cursor,
            limit=limit,
        ))
        return page.events, page.next_cursor, page.next_cursor is not None

    # --- Cleanup interface ---

    def cleanup(self, keep_major: bool = True, before_month_stamp: Optional[int] = None) -> int:
        """
        Clean up events.

        Args:
            keep_major: whether to keep major events.
            before_month_stamp: delete events before this time.

        Returns:
            Number of deleted events.
        """
        if self._storage:
            return self._storage.cleanup(keep_major=keep_major, before_month_stamp=before_month_stamp)
        else:
            # In-memory mode: simply clear everything.
            count = len(self._memory_events)
            self._memory_events.clear()
            return count

    def count(self) -> int:
        """Get the total number of events."""
        if self._storage:
            return self._storage.count()
        else:
            return len(self._memory_events)

    def close(self) -> None:
        """Release resources."""
        if self._storage:
            self._storage.close()

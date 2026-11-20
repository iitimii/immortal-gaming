from __future__ import annotations

from typing import Optional

from src.classes.event import Event


class EventHelper:
    """
    Event push helper: unifies the convention "push to the sidebar once, write history for both sides".

    - push_pair: write the event to both initiator and target; by default only the initiator side goes to the sidebar.
    - push_self: write the event only to oneself, optionally to the sidebar.
    """
    @staticmethod
    def push_pair(event: Event, initiator: "Avatar", target: Optional["Avatar"], *, to_sidebar_once: bool = True) -> None:
        """
        Dispatch the event to both sides.
        The initiator side goes to the sidebar (to_sidebar=True), so the Simulator collects it and stores it in the global database.
        Since the Simulator already handles interaction counts for related avatars, there's no need to call target.add_event manually.
        """
        initiator.add_event(event, to_sidebar=True)

    @staticmethod
    def push_self(event: Event, avatar: "Avatar", *, to_sidebar: bool = True) -> None:
        """Dispatch the event only to oneself."""
        avatar.add_event(event, to_sidebar=to_sidebar)



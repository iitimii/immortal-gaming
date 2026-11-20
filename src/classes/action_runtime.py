from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


class ActionStatus(Enum):
    """
    Standard status enum while advancing an action.
    - RUNNING: still in progress; must continue advancing in future ticks
    - COMPLETED: finished normally
    - FAILED: execution failed (due to params/preconditions etc.)
    - CANCELLED: cancelled externally (e.g. preempted by another action)
    - INTERRUPTED: interrupted while running (e.g. by battle/events)
    """

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


@dataclass
class ActionResult:
    """
    Standard action result. Every Action.step() must return this type.

    Attributes:
        status: the status after this advance (see ActionStatus)
        events: events generated during this advance (usually collected and shown by Avatar)
        payload: optional structured data for upper layers (e.g. values, battle results)
        next_action: optional "suggested next action" (name, params) for upper-layer scheduling
    """

    status: ActionStatus
    events: List[Any]
    payload: Optional[Dict[str, Any]] = None
    next_action: Optional[tuple[str, Dict[str, Any]]] = None


@dataclass
class ActionPlan:
    """
    A planned action item: not yet committed for execution.
    Holds only the class name and params, plus optional scheduling fields.
    """
    action_name: str
    params: Dict[str, Any]
    priority: int = 0
    expiry_month: Optional[int] = None  # Expiry month stamp; None means it never expires
    max_retries: int = 0
    attempted: int = 0
    
    def to_dict(self) -> dict:
        """Convert to a serializable dict."""
        return {
            "action_name": self.action_name,
            "params": self.params,
            "priority": self.priority,
            "expiry_month": self.expiry_month,
            "max_retries": self.max_retries,
            "attempted": self.attempted
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ActionPlan":
        """Rebuild an ActionPlan from a dict."""
        return cls(
            action_name=data["action_name"],
            params=data["params"],
            priority=data.get("priority", 0),
            expiry_month=data.get("expiry_month"),
            max_retries=data.get("max_retries", 0),
            attempted=data.get("attempted", 0)
        )


@dataclass
class ActionInstance:
    """
    An action instance that has been committed and started.
    """
    action: Any  # src.classes.action.Action
    params: Dict[str, Any]
    status: str = "running"  # Legacy field: Avatar records the running state as a string


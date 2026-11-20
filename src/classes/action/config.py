from __future__ import annotations

from typing import Any

from src.utils.config import CONFIG


class ActionConfig:
    """
    Lightweight wrapper for reading action-related config.

    Usage:
        ActionConfig.get("actions.duration.play", default=6)
    Supports dot-separated paths resolved via getattr level by level; returns default if not found.
    """
    @staticmethod
    def get(path: str, default: Any = None) -> Any:
        cur = CONFIG
        for part in path.split("."):
            cur = getattr(cur, part, None)
            if cur is None:
                return default
        return cur



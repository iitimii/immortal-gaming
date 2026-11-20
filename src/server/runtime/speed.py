from __future__ import annotations

from typing import Any

# Single source of truth for the simulation speed multipliers exposed to clients.
ALLOWED_SIMULATION_SPEEDS: tuple[float, ...] = (0.5, 1.0, 2.0, 4.0)
DEFAULT_SIMULATION_SPEED: float = 1.0
# Seconds between monthly steps at 1x speed.
BASE_STEP_INTERVAL_SECONDS: float = 1.0


def normalize_simulation_speed(value: Any) -> float | None:
    """Return the matching allowed speed, or None when the value is not allowed."""
    if isinstance(value, bool):
        return None
    try:
        speed = float(value)
    except (TypeError, ValueError):
        return None
    for allowed in ALLOWED_SIMULATION_SPEEDS:
        if abs(speed - allowed) < 1e-9:
            return allowed
    return None


def step_interval_for_speed(speed: float) -> float:
    return BASE_STEP_INTERVAL_SECONDS / speed

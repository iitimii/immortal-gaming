from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from .stepper import SimulationStepper
from src.server.runtime.speed import DEFAULT_SIMULATION_SPEED, step_interval_for_speed


@dataclass(slots=True)
class GameLoopRunner:
    game_instance: dict[str, Any]
    runtime: Any
    stepper: SimulationStepper
    get_logger: Callable[[], Any]
    sleep: Callable[[float], Any] = asyncio.sleep
    # Waits are split into short slices so speed changes take effect quickly.
    sleep_slice_seconds: float = 0.05

    async def wait_for_initialization(self) -> bool:
        print("Background game loop started, waiting for initialization...")
        while self.game_instance.get("init_status") not in ("ready", "error"):
            await self.sleep(0.5)

        if self.game_instance.get("init_status") == "error":
            print("[game_loop] Initialization failed, game loop exiting.")
            return False

        print("[game_loop] Initialization completed, starting game loop.")
        return True

    async def run_forever(self) -> None:
        if not await self.wait_for_initialization():
            return

        while True:
            await self.wait_for_next_step()
            await self.run_once()

    def get_step_interval(self) -> float:
        get_speed = getattr(self.runtime, "get_simulation_speed", None)
        speed = get_speed() if callable(get_speed) else DEFAULT_SIMULATION_SPEED
        return step_interval_for_speed(speed)

    async def wait_for_next_step(self) -> None:
        """Sleep until the interval for the current speed has elapsed.

        The speed is re-read after every slice, so switching from a slow to a
        fast speed shortens the wait that is already in progress.
        """
        elapsed = 0.0
        while True:
            remaining = self.get_step_interval() - elapsed
            if remaining <= 1e-9:
                return
            chunk = min(self.sleep_slice_seconds, remaining)
            await self.sleep(chunk)
            elapsed += chunk

    async def run_once(self) -> None:
        try:
            if self.runtime.is_effectively_paused():
                return
            if self.runtime.get("init_status") != "ready":
                return

            await self.stepper.step_and_broadcast()
        except Exception as exc:
            print(f"Game loop error: {exc}")
            self.get_logger().logger.error(f"Game loop error: {exc}", exc_info=True)

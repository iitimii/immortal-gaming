from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable

from .tick_payload import TickPayloadBuilder
from src.utils.llm.runtime_mode import is_world_test_mode, llm_test_mode_scope


@dataclass(slots=True)
class SimulationStepResult:
    events: list[Any] = field(default_factory=list)
    year: int = 0
    month: int = 0
    auto_saved: bool = False


@dataclass(slots=True)
class SimulationStepper:
    """Run one simulator step and publish its results.

    Shared by the background game loop and the manual "step once" command so
    both go through the same mutation lock, test-mode scope, tick broadcast and
    auto-save check.
    """

    runtime: Any
    manager: Any
    tick_payload_builder: TickPayloadBuilder
    should_trigger_auto_save: Callable[[Any], tuple[bool, int, int]]
    trigger_auto_save: Callable[[Any, Any], None]
    build_auto_save_toast: Callable[[], dict[str, Any]]

    async def step_and_broadcast(
        self,
        *,
        before_step: Callable[[], None] | None = None,
    ) -> SimulationStepResult | None:
        """Step the simulator once.

        ``before_step`` runs inside the mutation lock right before stepping, so
        callers can re-validate preconditions that may have changed while they
        were waiting for the lock; it may raise to abort the step.

        Returns None when there is nothing to step or the game was reset while
        the step was running.
        """
        if not self.runtime.get("sim") or not self.runtime.get("world"):
            return None

        async def _step_in_run_scope():
            if before_step is not None:
                before_step()
            sim = self.runtime.get("sim")
            world = self.runtime.get("world")
            if not sim or not world:
                return None
            with llm_test_mode_scope(is_world_test_mode(world)):
                events = await sim.step()
            return world, sim, events

        stepped = await self.runtime.run_mutation(_step_in_run_scope)
        if stepped is None:
            return None
        if getattr(self.runtime, "is_reset_requested", lambda: False)():
            return None

        world, sim, events = stepped
        await self.manager.broadcast(self.tick_payload_builder.build(events=events, world=world))

        auto_saved = False
        should_auto_save, year, _month = self.should_trigger_auto_save(world)
        if should_auto_save:
            print(f"[Auto-Save] Triggering auto save for year {year}...")
            await asyncio.to_thread(self.trigger_auto_save, world, sim)
            await self.manager.broadcast(self.build_auto_save_toast())
            print("[Auto-Save] Auto save completed.")
            auto_saved = True

        return SimulationStepResult(
            events=list(events or []),
            year=int(world.month_stamp.get_year()),
            month=int(world.month_stamp.get_month().value),
            auto_saved=auto_saved,
        )

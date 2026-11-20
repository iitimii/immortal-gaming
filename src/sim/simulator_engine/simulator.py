from __future__ import annotations

from src.classes.event import Event
from src.classes.core.world import World
from src.config.providers import StaticConfigProvider

from .phase_runner import SimulationPhaseRunner


class Simulator:
    def __init__(self, world: World):
        self.world = world
        run_config = getattr(world, "run_config_snapshot", {}) or {}
        self.awakening_rate = float(run_config.get("npc_awakening_rate_per_month", 0.01))
        self.config_provider = StaticConfigProvider.current()
        self.can_interrupt_major = self.config_provider.can_interrupt_major_events()

        from src.sim.managers.sect_manager import SectManager

        self.sect_manager = SectManager(world)

    async def step(self) -> list[Event]:
        """
        Main flow of a single simulator step (advances one month).

        Phase order:
        1.  Update avatar perception and known regions
        2.  Long-term objective thinking
        3.  Gathering system (gatherings/conventions)
        4.  AI decisions (generate action chains for avatars without plans)
        5.  Commit and start the next planned step
        6.  Execute current actions (multiple tick rounds until stable or the cap is reached)
        7.  Process interactions from events (first round)
        8.  Relation evolution phase
        9.  Death settlement
        10. Age update and birth/awakening handling
        11. Backstory generation
        12. Passive effects and world-level random events
        13. Minor random events + sect random events
        14. Nickname generation
        15. Celestial phenomenon (world climate) update
        16. City population update
        17. Process interactions from events (second round, including newly generated events)
        18. Computed relations update (e.g. second-order relations)
        19. Every January: yearly world maintenance
        20. Finalize events, persist them, write logs, and advance the month
        """
        return await SimulationPhaseRunner(self).run()

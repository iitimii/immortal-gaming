from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.classes.world_lore_snapshot import build_world_lore_snapshot
from src.run.log import get_logger
from src.systems.world_lore_rewrite import (
    WorldLoreRewriteRunner,
    apply_world_lore_rewrite,
    build_world_lore_context,
)

if TYPE_CHECKING:
    from src.classes.core.world import World


@dataclass
class WorldLore:
    text: str = ""


class WorldLoreManager:
    """
    At game start, rewrites this run's location, sect, technique and equipment texts all at once based on the "world lore and history" text.
    """

    def __init__(self, world: "World"):
        self.world = world
        self.logger = get_logger().logger

    async def apply_world_lore(self, lore_text: str) -> None:
        lore_text = str(lore_text or "").strip()
        if not lore_text:
            return

        self.logger.info("[WorldLore] Reshaping the world from the world lore and history...")
        context = build_world_lore_context(self.world, lore_text)
        draft = await WorldLoreRewriteRunner(context).run()
        apply_world_lore_rewrite(self.world, draft)
        self.world.world_lore_snapshot = build_world_lore_snapshot(
            self.world,
            lore_text=lore_text,
            draft=draft,
            rewrite_config=context.config,
        )
        self.logger.info("[WorldLore] World lore and history shaping complete")

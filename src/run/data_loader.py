"""Compatibility facade for the static catalog lifecycle."""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.run.log import get_logger
from src.run.static_catalog import static_catalog

if TYPE_CHECKING:
    from src.classes.core.world import World


def reload_all_static_data():
    logger = get_logger().logger
    logger.info("[DataLoader] Resetting static game data...")
    snapshot = static_catalog.reload()
    logger.info("[DataLoader] Static data reset complete, generation=%s.", snapshot.generation)
    return snapshot


def fix_runtime_references(world: "World"):
    report = static_catalog.rebind_world(world)
    get_logger().logger.info(
        "[DataLoader] Repaired static references for %s avatars, missing=%s.",
        report.avatars_seen,
        list(report.missing_references),
    )
    return report

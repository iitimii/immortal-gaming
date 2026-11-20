"""
Load game module.

Top-level functions only handle path resolution, file IO, section registry orchestration, and error handling. The concrete restore
order is maintained centrally in the save/load section registry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

import src.utils.config as app_config
from src.sim.save.sections.base import LoadContext
from src.sim.save.sections.registry import restore_loaded_game

if TYPE_CHECKING:
    from src.classes.core.sect import Sect
    from src.classes.core.world import World
    from src.sim.simulator import Simulator


def get_events_db_path(save_path: Path) -> Path:
    """
    Compute the events database path from the save path.

    Example: save_20260105_1423.json -> save_20260105_1423_events.db
    """
    return save_path.with_suffix("").with_name(save_path.stem + "_events.db")


def _get_current_saves_dir() -> Path:
    return Path(app_config.CONFIG.paths.saves)


def _resolve_load_path(save_path: Optional[Path]) -> Path:
    if save_path is None:
        return _get_current_saves_dir() / "save.json"
    return Path(save_path)


def load_game(save_path: Optional[Path] = None) -> Tuple["World", "Simulator", List["Sect"]]:
    """Load game state from a file."""
    resolved_save_path = _resolve_load_path(save_path)
    if not resolved_save_path.exists():
        raise FileNotFoundError(f"Save file does not exist: {resolved_save_path}")

    try:
        with open(resolved_save_path, "r", encoding="utf-8") as f:
            save_data = json.load(f)

        meta = save_data.get("meta", {})
        print(
            f"Loading save (Version: {meta.get('version', 'unknown')}, "
            f"Game time: {meta.get('game_time', 'unknown')})"
        )

        context = LoadContext(save_path=resolved_save_path, save_data=save_data)
        world, simulator, existed_sects = restore_loaded_game(context)
        loaded_count = len(context.all_avatars or {})
        print(f"Save loaded successfully! Loaded {loaded_count} avatars")
        return world, simulator, existed_sects
    except Exception as exc:
        print(f"Failed to load game: {exc}")
        import traceback

        traceback.print_exc()
        raise


def check_save_compatibility(save_path: Path) -> Tuple[bool, str]:
    """Check save compatibility. During the current development phase, no strict version blocking is done."""
    try:
        with open(save_path, "r", encoding="utf-8") as f:
            json.load(f)
        return True, ""
    except Exception as exc:
        return False, f"Unable to read save file: {exc}"

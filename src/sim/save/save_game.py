"""
Save game module.

Top-level functions only handle paths, event database copying, section orchestration, and file IO. The concrete payload
is owned by sections in `src.sim.save.sections`, so new systems don't keep bloating this file.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import src.utils.config as app_config
from src.sim.load.load_game import get_events_db_path
from src.sim.save.sections.base import SaveContext
from src.sim.save.sections.registry import dump_save_data

if TYPE_CHECKING:
    from src.classes.core.sect import Sect
    from src.classes.core.world import World
    from src.sim.simulator import Simulator


def sanitize_save_name(name: str) -> str:
    """Sanitize the save name, keeping only safe characters."""
    safe_name = re.sub(r'[\\/:*?"<>|]', "", name)
    safe_name = re.sub(r"[^\w\u4e00-\u9fff]", "_", safe_name)
    return safe_name[:50] if safe_name else "save"


def _get_current_saves_dir() -> Path:
    return Path(app_config.CONFIG.paths.saves)


def _resolve_save_path(
    *,
    world: "World",
    save_path: Optional[Path],
    custom_name: Optional[str],
) -> Path:
    if save_path is not None:
        resolved = Path(save_path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    saves_dir = _get_current_saves_dir()
    saves_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    time_str = now.strftime("%Y%m%d_%H%M%S")
    year = world.month_stamp.get_year()
    month = world.month_stamp.get_month().value
    game_time_str = f"Y{year}M{month}"
    if custom_name:
        filename = f"{sanitize_save_name(custom_name)}_{time_str}.json"
    else:
        filename = f"{time_str}_{game_time_str}.json"
    return saves_dir / filename


def _copy_events_database_if_needed(world: "World", events_db_path: Path) -> None:
    storage = getattr(getattr(world, "event_manager", None), "_storage", None)
    if storage is None:
        return

    current_db_path = storage._db_path
    if current_db_path == events_db_path:
        return

    import shutil

    if current_db_path.exists():
        events_db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(current_db_path, events_db_path)
        print(f"Copied events database: {current_db_path} -> {events_db_path}")
    else:
        print(f"Warning: Current events database not found: {current_db_path}")


def save_game(
    world: "World",
    simulator: "Simulator",
    existed_sects: List["Sect"],
    save_path: Optional[Path] = None,
    custom_name: Optional[str] = None,
    is_auto_save: bool = False,
) -> tuple[bool, Optional[str]]:
    """Save game state to JSON + a SQLite event database."""
    try:
        resolved_save_path = _resolve_save_path(
            world=world,
            save_path=save_path,
            custom_name=custom_name,
        )
        events_db_path = get_events_db_path(resolved_save_path)
        _copy_events_database_if_needed(world, events_db_path)

        context = SaveContext(
            world=world,
            simulator=simulator,
            existed_sects=list(existed_sects),
            save_path=resolved_save_path,
            events_db_path=events_db_path,
            custom_name=custom_name,
            is_auto_save=is_auto_save,
        )
        save_data = dump_save_data(context)

        with open(resolved_save_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        print(f"Game saved to: {resolved_save_path}")
        return True, resolved_save_path.name
    except Exception as exc:
        print(f"Failed to save game: {exc}")
        import traceback

        traceback.print_exc()
        return False, None


def get_save_info(save_path: Path) -> Optional[dict]:
    """Read a save file's metadata."""
    try:
        with open(save_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("meta", {})
    except Exception:
        return None


def list_saves(saves_dir: Optional[Path] = None) -> List[tuple[Path, dict]]:
    """List all save files and their metadata."""
    if saves_dir is None:
        saves_dir = _get_current_saves_dir()

    if not saves_dir.exists():
        return []

    saves = []
    for save_file in saves_dir.glob("*.json"):
        info = get_save_info(save_file)
        if info is not None:
            saves.append((save_file, info))

    saves.sort(key=lambda x: x[1].get("save_time", ""), reverse=True)
    return saves

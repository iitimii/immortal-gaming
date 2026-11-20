from __future__ import annotations

import json
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

from src.classes.action.registry import ActionRegistry
from src.classes.action.param_options import build_param_options
# Make sure all action modules (including mutual actions) are loaded before collecting the registry
import src.classes.action  # noqa: F401
import src.classes.mutual_action  # noqa: F401


ALL_ACTION_CLASSES = list(ActionRegistry.all())
ALL_ACTUAL_ACTION_CLASSES = list(ActionRegistry.all_actual())
ALL_ACTION_NAMES = [cls.__name__ for cls in ALL_ACTION_CLASSES]
ALL_ACTUAL_ACTION_NAMES = [cls.__name__ for cls in ALL_ACTUAL_ACTION_CLASSES]


def _build_action_info(action, avatar: "Avatar" | None = None):
    info = {
        "desc": action.get_desc(),
        "require": action.get_requirements(),
    }
    if hasattr(action, 'PARAMS') and action.PARAMS:
        info["params"] = action.PARAMS
        if avatar is not None:
            param_options = build_param_options(action, avatar)
            if param_options:
                info["param_options"] = param_options

    cd = int(getattr(action, "ACTION_CD_MONTHS", 0) or 0)
    if cd > 0:
        info["cd_months"] = cd
    return info

def get_action_infos(avatar: "Avatar" | None = None) -> Dict[str, Any]:
    """
    Dynamically get action descriptions for the current locale.
    If an avatar is given, actions that avatar can't possibly perform are filtered out.
    """
    infos = {}
    for action_cls in ALL_ACTUAL_ACTION_CLASSES:
        if avatar is not None:
            # Instantiate the action to check whether it could possibly execute
            action_inst = action_cls(avatar, avatar.world)
            if not action_inst.can_possibly_start():
                continue
        infos[action_cls.__name__] = _build_action_info(action_cls, avatar=avatar)
    return infos

def get_action_infos_str(avatar: "Avatar" | None = None) -> str:
    """
    Get the action descriptions as a JSON string
    """
    return json.dumps(get_action_infos(avatar), ensure_ascii=False, indent=2)

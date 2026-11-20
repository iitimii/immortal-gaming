"""
Avatar module

The original avatar.py is split into several submodules, exported via this __init__.py for backward compatibility.
"""
from src.classes.core.avatar.core import (
    Avatar,
)
from src.classes.gender import Gender

from src.classes.core.avatar.info_presenter import (
    get_avatar_info,
    get_avatar_structured_info,
    get_avatar_expanded_info,
    get_other_avatar_info,
)

__all__ = [
    # Core class
    "Avatar",
    "Gender",
    # Info display functions
    "get_avatar_info",
    "get_avatar_structured_info",
    "get_avatar_hover_info",
    "get_avatar_expanded_info",
    "get_other_avatar_info",
]


"""Save game module

Uses lazy imports to avoid circular dependencies
"""

def __getattr__(name):
    """Lazy import to avoid triggering circular dependencies at module level"""
    if name == "save_game":
        from .save_game import save_game
        return save_game
    elif name == "get_save_info":
        from .save_game import get_save_info
        return get_save_info
    elif name == "list_saves":
        from .save_game import list_saves
        return list_saves
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["save_game", "get_save_info", "list_saves"]


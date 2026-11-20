"""Load game module

Uses lazy imports to avoid circular dependencies
"""

def __getattr__(name):
    """Lazy import to avoid triggering circular dependencies at module level"""
    if name == "load_game":
        from .load_game import load_game
        return load_game
    elif name == "check_save_compatibility":
        from .load_game import check_save_compatibility
        return check_save_compatibility
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["load_game", "check_save_compatibility"]


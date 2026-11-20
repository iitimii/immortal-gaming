from typing import Dict, Type, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.classes.items.item import Item

class ItemRegistry:
    """Global item registry."""
    
    _items_by_id: Dict[int, "Item"] = {}

    @classmethod
    def register(cls, item_id: int, item: "Item"):
        if item_id in cls._items_by_id:
            # Allow re-registration (overwrite), though a warning would be good in development
            pass
        cls._items_by_id[item_id] = item

    @classmethod
    def get(cls, item_id: int) -> Optional["Item"]:
        return cls._items_by_id.get(item_id)

    @classmethod
    def unregister(cls, item_id: int):
        cls._items_by_id.pop(item_id, None)

    @classmethod
    def get_all(cls) -> Dict[int, "Item"]:
        return cls._items_by_id
    
    @classmethod
    def reset(cls):
        """Reset the registry, clearing all registered items."""
        cls._items_by_id.clear()

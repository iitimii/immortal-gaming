import copy
from typing import TypeVar, Any

T = TypeVar("T", bound="Item")

class Item:
    """Base class for all items."""
    
    def instantiate(self: T) -> T:
        """
        Create a new instance of this item.
        The default is a deep copy, suitable for items with independent state (e.g. equipment).
        Read-only subclasses (e.g. materials) can override this to return self for performance.
        """
        return copy.deepcopy(self)


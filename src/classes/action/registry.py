from __future__ import annotations

from typing import Callable, Dict, Type, Iterable


class ActionRegistry:
    """
    Action registry: maps action names to classes and marks which are "actually executable" actions.

    - register(action_cls, actual): register an action class
    - get(name): get an action class by name
    - all()/all_actual(): get all / actually executable action classes
    """
    _name_to_cls: Dict[str, type] = {}
    _actual_name_to_cls: Dict[str, type] = {}

    @classmethod
    def register(cls, action_cls: type, *, actual: bool) -> None:
        name = action_cls.__name__
        cls._name_to_cls[name] = action_cls
        if actual:
            cls._actual_name_to_cls[name] = action_cls

    @classmethod
    def get(cls, name: str) -> type:
        return cls._name_to_cls[name]

    @classmethod
    def all(cls) -> Iterable[type]:
        # Deduplicate while keeping a stable order
        seen = set()
        ordered: list[type] = []
        for t in cls._name_to_cls.values():
            if t not in seen:
                seen.add(t)
                ordered.append(t)
        return ordered

    @classmethod
    def all_actual(cls) -> Iterable[type]:
        # Deduplicate while keeping a stable order
        seen = set()
        ordered: list[type] = []
        for t in cls._actual_name_to_cls.values():
            if t not in seen:
                seen.add(t)
                ordered.append(t)
        return ordered


def register_action(*, actual: bool = True) -> Callable[[type], type]:
    def deco(t: type) -> type:
        ActionRegistry.register(t, actual=actual)
        return t
    return deco



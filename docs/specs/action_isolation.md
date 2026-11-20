# Action Isolation Strategy

The strategy described in this document has been implemented; the content below reflects the paths and default rules of the current repository implementation.

## Background

In the cultivation world simulation, avatars perform various long-running actions (such as retreat, battle, movement, etc.). At the same time, the system has various global mechanisms (such as auctions, tournaments, fortunes, misfortunes, etc.) that try to interact with avatars.

The previous problem was that global mechanisms ignored the avatar's current state, leading to logically jarring situations such as "an avatar in closed-door retreat running off to join an auction" or "picking up a divine weapon by the roadside while in retreat".

## Solution: Trait-based Declarative Control

We adopt a "trait-based declarative control" approach, delegating the authority to define "whether interruption is allowed" to the `Action` class itself.

### 1. Action Base Class Definition

In `src/classes/action/action.py`, whether an action may be interrupted by external systems follows these rules:

- If `ALLOW_GATHERING` / `ALLOW_WORLD_EVENTS` is explicitly set, the explicit value takes precedence.
- If not explicitly set, it is determined by `IS_MAJOR`: major actions are not allowed by default, non-major actions are allowed by default.

```python
class Action(ABC):
    ALLOW_GATHERING: bool | None = None
    ALLOW_WORLD_EVENTS: bool | None = None

    @classmethod
    def can_gather(cls) -> bool:
        if cls.ALLOW_GATHERING is not None:
            return cls.ALLOW_GATHERING
        return not getattr(cls, 'IS_MAJOR', False)
```

### 2. Overriding the Strategy in Specific Actions

For example, the `Retreat` action (`src/classes/action/retreat.py`) needs to be cut off from the world:

```python
class Retreat(TimedAction):
    # ...
    # During retreat, ignore worldly affairs and stay free of karmic entanglement
    ALLOW_GATHERING = False
    ALLOW_WORLD_EVENTS = False
```

### 3. Avatar State Check Interface

`Avatar` (`src/classes/core/avatar/action_mixin.py`) encapsulates state check properties:

- `avatar.can_join_gathering`: checks whether the current action allows joining a gathering.
- `avatar.can_trigger_world_event`: checks whether the current action allows triggering fortune/misfortune.

### 4. External Call Conventions

- **Gathering (e.g. Auction)**: when getting the participant list, avatars must be filtered to those with `can_join_gathering` set to True.
- **Passive Effects (Fortune/Misfortune)**: before triggering, `can_trigger_world_event` must be checked to be True.

## Extension Guide

When you create a new Action:
- If the action requires the avatar's full concentration (such as "breakthrough" or "alchemy"), consider setting `ALLOW_GATHERING` to `False`.
- If the action takes place in a special space or a flow state (such as "inner demon tribulation" or "epiphany"), consider setting `ALLOW_WORLD_EVENTS` to `False`.
- By default, no changes are needed.

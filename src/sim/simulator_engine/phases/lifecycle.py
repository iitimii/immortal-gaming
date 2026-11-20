from __future__ import annotations

import asyncio

from src.classes.backstory import process_avatar_backstory
from src.classes.birth import process_births
from src.classes.core.avatar import Avatar
from src.classes.death import handle_death
from src.classes.death_reason import DeathReason, DeathType
from src.classes.event import Event
from src.classes.long_term_objective import process_avatar_long_term_objective
from src.classes.nickname import process_avatar_nickname
from src.sim.avatar_awake import process_awakening


def phase_resolve_death(world, living_avatars: list[Avatar]) -> list[Event]:
    # Besides generating death events, death settlement must also maintain living_avatars.
    # Later phases reuse this list, so the dead must be removed from it in place here.
    events: list[Event] = []
    dead_avatars: list[Avatar] = []

    for avatar in living_avatars:
        # Repair worlds created before all creation paths used handle_death().
        # They may contain an already-dead avatar in the active collection,
        # which otherwise leaves an avatar portrait on the map with no grave.
        if avatar.is_dead:
            handle_death(
                world,
                avatar,
                str((getattr(avatar, "death_info", None) or {}).get("reason") or DeathReason(DeathType.OLD_AGE)),
            )
            dead_avatars.append(avatar)
            continue

        is_dead = False
        death_reason: DeathReason | None = None

        if avatar.hp.cur <= 0:
            is_dead = True
            death_reason = DeathReason(DeathType.SERIOUS_INJURY)
        elif avatar.death_by_old_age():
            is_dead = True
            death_reason = DeathReason(DeathType.OLD_AGE)

        if is_dead and death_reason:
            events.append(
                Event(
                    world.month_stamp,
                    f"{avatar.name}{death_reason}",
                    related_avatars=[avatar.id],
                    is_major=True,
                    event_type="death",
                    render_params={"subject_name": avatar.name},
                )
            )
            handle_death(world, avatar, death_reason)
            dead_avatars.append(avatar)

    # Remove after the loop to avoid mutating the list while iterating.
    for dead in dead_avatars:
        if dead in living_avatars:
            living_avatars.remove(dead)

    return events


def phase_update_age_and_birth(world, living_avatars: list[Avatar]) -> list[Event]:
    events: list[Event] = []
    for avatar in living_avatars:
        avatar.update_age(world.month_stamp)

    # The mortal manager and the cultivator list are separate pipelines; clean up dead mortals here as well.
    world.mortal_manager.cleanup_dead_mortals(world.month_stamp)

    # Handle awakening first, then births, keeping the same ordering as the old simulator.
    awakening_events = process_awakening(world)
    if awakening_events:
        events.extend(awakening_events)

    birth_events = process_births(world)
    if birth_events:
        events.extend(birth_events)

    return events


async def phase_backstory_generation(living_avatars: list[Avatar]) -> None:
    # Backstory is generated only once; avatars that already have one are skipped.
    avatars_to_process = [avatar for avatar in living_avatars if avatar.backstory is None]
    if not avatars_to_process:
        return

    await asyncio.gather(*[process_avatar_backstory(avatar) for avatar in avatars_to_process])


async def phase_nickname_generation(living_avatars: list[Avatar]) -> list[Event]:
    # Nickname generation may run fully concurrently; only avatars that actually produced an event leave a record.
    results = await asyncio.gather(*[process_avatar_nickname(avatar) for avatar in living_avatars])
    return [event for event in results if event]


async def phase_long_term_objective_thinking(living_avatars: list[Avatar]) -> list[Event]:
    # Long-term objective thinking is a routine monthly update and does not require the avatar to be idle.
    results = await asyncio.gather(
        *[process_avatar_long_term_objective(avatar) for avatar in living_avatars]
    )
    return [event for event in results if event]

from __future__ import annotations

from src.classes.ai import llm_ai
from src.classes.core.avatar import Avatar
from src.classes.event import Event, is_null_event
from src.config.providers import StaticConfigProvider
from src.run.log import get_logger
from src.sim.runtime_capabilities import get_decision_boundary_gateway


async def phase_decide_actions(world, living_avatars: list[Avatar]) -> None:
    gateway = get_decision_boundary_gateway(world)
    if gateway is not None:
        gateway.before_ai_decision(world)
    controlled_avatar_id = gateway.get_controlled_avatar_id() if gateway is not None else ""

    # Only make decisions for avatars that are neither executing an action nor have a pending plan,
    # so the LLM does not overwrite an already scheduled action chain.
    avatars_to_decide = [
        avatar
        for avatar in living_avatars
        if avatar.current_action is None and not avatar.has_plans()
        and str(getattr(avatar, "id", "")) != controlled_avatar_id
    ]
    if not avatars_to_decide:
        return

    decide_results = await llm_ai.decide(world, avatars_to_decide)
    for avatar, result in decide_results.items():
        action_name_params_pairs, avatar_thinking, short_term_objective, _event = result
        avatar.load_decide_result_chain(
            action_name_params_pairs,
            avatar_thinking,
            short_term_objective,
        )


def phase_commit_next_plans(living_avatars: list[Avatar]) -> list[Event]:
    events: list[Event] = []
    for avatar in living_avatars:
        if avatar.current_action is None:
            # This only advances an existing plan into current_action;
            # it does not participate in deciding where the plan came from.
            start_event = avatar.commit_next_plan()
            if start_event is not None and not is_null_event(start_event):
                events.append(start_event)
    return events


async def _tick_action_round(avatars: list[Avatar], log_label: str) -> tuple[list[Event], set[Avatar]]:
    # A single round of action execution. Returns this round's events and the avatars that need to keep running this month.
    # It is split out so the "first round" and subsequent "retry rounds" share the same exception handling.
    events: list[Event] = []
    avatars_needing_retry: set[Avatar] = set()

    for avatar in avatars:
        try:
            new_events = await avatar.tick_action()
            if new_events:
                events.extend(new_events)

            if getattr(avatar, "_new_action_set_this_step", False):
                avatars_needing_retry.add(avatar)
        except Exception as exc:
            get_logger().logger.error(
                "Avatar %s(%s) %s failed: %s",
                avatar.name,
                avatar.id,
                log_label,
                exc,
                exc_info=True,
            )
            if hasattr(avatar, "_new_action_set_this_step"):
                avatar._new_action_set_this_step = False

    return events, avatars_needing_retry


async def phase_execute_actions(living_avatars: list[Avatar]) -> list[Event]:
    events: list[Event] = []
    max_local_rounds = StaticConfigProvider.current().max_action_rounds_per_turn()

    # In the first round, every avatar executing an action runs once.
    round_events, avatars_needing_retry = await _tick_action_round(
        living_avatars,
        "tick_action",
    )
    events.extend(round_events)

    round_count = 1
    # Some actions seamlessly chain into a new current_action within a tick.
    # Such avatars keep running within the same month, guarded by a global cap to avoid infinite loops.
    while avatars_needing_retry and round_count < max_local_rounds:
        current_avatars = list(avatars_needing_retry)
        round_events, avatars_needing_retry = await _tick_action_round(
            current_avatars,
            "retry tick_action",
        )
        events.extend(round_events)
        round_count += 1

    return events

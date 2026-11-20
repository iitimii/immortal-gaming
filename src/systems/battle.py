from __future__ import annotations

import math
import random
from typing import Tuple, TYPE_CHECKING, Callable, Awaitable, Optional

from src.classes.story_event_service import StoryEventKind, StoryEventService
from src.classes.close_relation_event_service import (
    append_close_relation_major_observations,
    apply_kill_hatred,
)
from src.classes.technique import TechniqueGrade, get_suppression_bonus
from src.systems.formation import get_current_region_formation_effects

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar
    from src.classes.event import Event


# Battle strength parameters (inspired by Civ6, adapted to this project's numbers)
# Base strength per realm
_REALM_BASE_STRENGTH = {
    "Qi_Refinement": 10.0,
    "Foundation_Establishment": 20.0,
    "Core_Formation": 30.0,
    "Nascent_Soul": 40.0,
}
# Extra bonus per minor realm (stage)
_STAGE_BONUS_STRENGTH = {
    "Early_Stage": 0.0,
    "Middle_Stage": 2.5,
    "Late_Stage": 5.0,
}

_SUPPRESSION_POINTS: float = 3.0             # Flat strength points granted by elemental suppression
_CIV6_K: float = 0.04                        # Damage exponent coefficient: e^(K x diff)
_WIN_BETA: float = 0.15                      # Slope of the win-rate logistic function
_MIN_WIN_RATE: float = 0.01                  # Minimum win rate
_MAX_WIN_RATE: float = 0.99                  # Maximum win rate
_BASE_DAMAGE_LOW: int = 24                   # Base damage lower bound (scaled by defender.maxHP/100)
_BASE_DAMAGE_HIGH: int = 36                  # Base damage upper bound (scaled by defender.maxHP/100)
_MIN_RATIO: float = 1.05                     # Minimum advantage ratio, keeps winner damage strictly lower
_PAIR_BIAS: float = 1.1                     # Pair bias: a bit more for the loser, a bit less for the winner


def get_base_strength(self_avatar: "Avatar") -> float:
    """
    Base battle strength (refactored):
    = realm base value + stage bonus + extra effects
    """
    # 1. Base value of the current realm
    realm_name = self_avatar.cultivation_progress.realm.name
    base_val = _REALM_BASE_STRENGTH.get(realm_name, 10.0)
    
    # 2. Stage bonus
    stage_name = self_avatar.cultivation_progress.stage.name
    stage_bonus = _STAGE_BONUS_STRENGTH.get(stage_name, 0.0)
    
    strength_from_level = base_val + stage_bonus
    
    # Extra strength points from effects (e.g. passive bonuses from techniques or treasures)
    extra_raw = self_avatar.effects.get("extra_battle_strength_points", 0)
    extra_points = float(extra_raw or 0.0)
    return strength_from_level + extra_points


def _formation_battle_strength_bonus(self_avatar: "Avatar", opponent: "Avatar") -> float:
    self_region = getattr(getattr(self_avatar, "tile", None), "region", None)
    opponent_region = getattr(getattr(opponent, "tile", None), "region", None)
    if self_region is None or opponent_region is None:
        return 0.0
    if getattr(self_region, "id", None) != getattr(opponent_region, "id", None):
        return 0.0
    effects = get_current_region_formation_effects(self_avatar)
    try:
        return float(effects.get("extra_battle_strength_points", 0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _combat_strength_vs(opponent: "Avatar", self_avatar: "Avatar") -> float:
    """
    Relative strength = base strength + suppression points (+3 if suppressing)
    """
    base = get_base_strength(self_avatar) + _formation_battle_strength_bonus(self_avatar, opponent)
    
    # Elemental suppression bonus
    suppression_points = 0.0
    if self_avatar.technique is not None and opponent.technique is not None:
        if get_suppression_bonus(self_avatar.technique.attribute, opponent.technique.attribute) > 0.0:
            suppression_points = _SUPPRESSION_POINTS
    
    return base + suppression_points


def _strength_diff(attacker: "Avatar", defender: "Avatar") -> float:
    return _combat_strength_vs(defender, attacker) - _combat_strength_vs(attacker, defender)


def get_effective_strength(self_avatar: "Avatar", opponent: "Avatar") -> float:
    """
    Public: return self_avatar's effective strength against opponent.
    Used for event display and debugging; does not modify state.
    """
    return _combat_strength_vs(opponent, self_avatar)


def get_effective_strength_pair(a: "Avatar", b: "Avatar") -> tuple[float, float]:
    """
    Return both sides' effective strength at once (a vs b, b vs a).
    Order: (a_strength, b_strength)
    """
    return _combat_strength_vs(b, a), _combat_strength_vs(a, b)


def calc_win_rate(attacker: "Avatar", defender: "Avatar") -> float:
    """
    Win rate = sigmoid(beta x strength diff), clamped to [0.1, 0.9]
    - strength diff = effective strength(att) - effective strength(def)
    - beta defaults to 0.15, so a diff of ~10 gives a win rate of ~0.82
    """
    diff = _strength_diff(attacker, defender)
    p = 1.0 / (1.0 + math.exp(-_WIN_BETA * diff))
    if p < _MIN_WIN_RATE:
        return _MIN_WIN_RATE
    if p > _MAX_WIN_RATE:
        return _MAX_WIN_RATE
    return p


def _base_damage_scale(defender: "Avatar") -> float:
    # Using 100 HP as baseline, map Civ6's 24-36 damage to each realm's HP tier
    max_hp = defender.hp.max
    return max(1.0, max_hp / 100.0)

def _damage_pair(winner: "Avatar", loser: "Avatar") -> tuple[int, int]:
    """
    Paired damage: uses one base and a symmetric ratio so winner damage is strictly lower than loser damage.
    - ratio = max(exp(K×|diff|), MIN_RATIO)
    - mid scale = geometric mean sqrt(scale_winner x scale_loser)
    - loser damage = base x mid scale x ratio x (1 - loser damage reduction)
    - winner damage = base x mid scale / ratio x (1 - winner damage reduction)
    """
    abs_diff = abs(_strength_diff(winner, loser))
    ratio = math.exp(_CIV6_K * abs_diff)
    ratio *= _PAIR_BIAS
    if ratio < _MIN_RATIO:
        ratio = _MIN_RATIO

    base = random.randint(_BASE_DAMAGE_LOW, _BASE_DAMAGE_HIGH)
    scale_w = _base_damage_scale(winner)
    scale_l = _base_damage_scale(loser)
    mid_scale = math.sqrt(scale_w * scale_l)

    # Compute raw damage
    loser_damage_raw = base * mid_scale * ratio
    winner_damage_raw = base * mid_scale / ratio
    
    # Apply damage reduction effects
    loser_reduction_raw = loser.effects.get("damage_reduction", 0.0)
    loser_reduction = max(0.0, min(1.0, float(loser_reduction_raw or 0.0)))
    winner_reduction_raw = winner.effects.get("damage_reduction", 0.0)
    winner_reduction = max(0.0, min(1.0, float(winner_reduction_raw or 0.0)))
    
    loser_damage = max(1, int(loser_damage_raw * (1.0 - loser_reduction)))
    winner_damage = max(1, int(winner_damage_raw * (1.0 - winner_reduction)))
    
    return loser_damage, winner_damage


def decide_battle(attacker: "Avatar", defender: "Avatar") -> Tuple["Avatar", "Avatar", int, int]:
    """
    Resolve a battle, returning (winner, loser, loser damage, winner damage).
    - Win rate comes from a logistic function of the strength diff;
    - Both sides' damage is decided by the same diff in Civ6 style (symmetric formula); HP is independent of strength.
    """
    p = calc_win_rate(attacker, defender)
    if random.random() < p:
        winner, loser = attacker, defender
    else:
        winner, loser = defender, attacker

    loser_damage, winner_damage = _damage_pair(winner, loser)
    return winner, loser, loser_damage, winner_damage


def get_escape_success_rate(attacker: "Avatar", defender: "Avatar") -> float:
    """
    Escape success rate: defender tries to flee from attacker.
    Base rate 0.1, can be increased by the defender's effects.
    """
    base_rate = 0.1
    bonus = float(defender.effects.get("extra_escape_success_rate", 0.0))
    return max(0.0, min(1.0, base_rate + bonus))


def get_assassination_success_rate(attacker: "Avatar", defender: "Avatar") -> float:
    """
    Assassination success rate:
    - Base 10%
    - Same realm: 10%
    - +5% per major realm above the target, -5% per major realm below
    - Range [1%, 100%]
    """
    from src.systems.cultivation import Realm
    realm_order = {
        Realm.Qi_Refinement: 1,
        Realm.Foundation_Establishment: 2,
        Realm.Core_Formation: 3,
        Realm.Nascent_Soul: 4,
    }
    
    base_rate = 0.10
    
    attacker_rank = realm_order.get(attacker.cultivation_progress.realm, 1)
    defender_rank = realm_order.get(defender.cultivation_progress.realm, 1)
    
    diff = attacker_rank - defender_rank
    rate = base_rate + diff * 0.05
    
    # Apply extra assassination success bonuses
    extra = float(attacker.effects.get("extra_assassinate_success_rate", 0.0))
    rate += extra
    
    return max(0.01, min(1.0, rate))


async def gen_battle_result_text(
    winner: "Avatar",
    loser: "Avatar",
    l_dmg: int,
    w_dmg: int,
    is_fatal: bool,
    prefix: str = "",
    action_desc: str = "defeated",
    postfix: str = "",
    check_loot: bool = False
) -> str:
    """
    Generate the standard battle result text.
    """
    text_prefix = f"{prefix} " if prefix else ""
    if is_fatal:
        text = f"{text_prefix}{winner.name} {action_desc} {loser.name}{postfix}, dealing {l_dmg} damage. {loser.name} was fatally wounded and perished on the spot."
        if check_loot:
            from src.classes.kill_and_grab import kill_and_grab
            text += await kill_and_grab(winner, loser)
        return text
    else:
        return f"{text_prefix}{winner.name} {action_desc} {loser.name}{postfix}. {loser.name} took {l_dmg} damage, and {winner.name} also took {w_dmg} damage."


async def handle_battle_finish(
    world,
    attacker: "Avatar",
    target: "Avatar",
    res: Tuple["Avatar", "Avatar", int, int],
    start_event_content: str,
    story_prompt: str,
    outcome_text_func: Optional[Callable[["Avatar", "Avatar", int, int, bool], Awaitable[str]]] = None,
    check_loot: bool = False,
    prefix: str = "",
    action_desc: str = "defeated",
    postfix: str = ""
) -> list["Event"]:
    """
    Shared logic for handling battle results (events, story, death).
    
    Args:
        world: World object
        attacker: Initiator
        target: Target
        res: Result of decide_battle (winner, loser, loser_damage, winner_damage)
        start_event_content: Content of the start event (used for story generation)
        story_prompt: Prompt for story generation
        outcome_text_func: (Optional) async callback that generates the result text.
                           If None, the standard generation logic is used.
                           Args: (winner, loser, loser_damage, winner_damage, is_fatal)
                           Returns: result text string
        check_loot: Whether to check kill-and-loot (only when is_fatal is True with default text generation; otherwise outcome_text_func handles it)
        prefix: Prefix for default text generation (only when outcome_text_func is None)
        action_desc: Action description for default text generation (only when outcome_text_func is None)
        postfix: Suffix for default text generation (only when outcome_text_func is None)
    """
    from src.classes.event import Event
    from src.classes.death import handle_death
    from src.classes.death_reason import DeathReason, DeathType

    winner, loser, loser_damage, winner_damage = res
    is_fatal = loser.hp <= 0
    
    # Generate the result text
    if outcome_text_func:
        result_text = await outcome_text_func(winner, loser, loser_damage, winner_damage, is_fatal)
    else:
        result_text = await gen_battle_result_text(
            winner, loser, loser_damage, winner_damage, is_fatal,
            prefix=prefix, action_desc=action_desc, postfix=postfix, check_loot=check_loot
        )
    
    # Build the event
    rel_ids = [attacker.id]
    if target:
        rel_ids.append(target.id)
        
    event_type = "battle_kill" if is_fatal else "battle_result"
    result_event = Event(
        world.month_stamp,
        result_text,
        related_avatars=rel_ids,
        is_major=True,
        event_type=event_type,
        render_params={
            "killer_id": str(winner.id),
            "killer_name": winner.name,
            "victim_id": str(loser.id),
            "victim_name": loser.name,
            "subject_name": loser.name,
        },
    )
    
    # Start text for story generation (fall back to the result text if empty)
    start_content = start_event_content
    if not start_content:
        start_content = result_text

    story_event = await StoryEventService.maybe_create_story(
        kind=StoryEventKind.COMBAT,
        month_stamp=world.month_stamp,
        start_text=start_content,
        result_text=result_event.content,
        actors=[attacker, target],
        related_avatar_ids=rel_ids,
        prompt=story_prompt,
        allow_relation_changes=True,
    )
    
    # Handle death
    if is_fatal:
        append_close_relation_major_observations(
            result_event,
            subject=loser,
            propagation_kind="close_relation_killed",
        )
        apply_kill_hatred(victim=loser, killer=winner)
        handle_death(world, loser, DeathReason(DeathType.BATTLE, killer_name=winner.name))
    events = [result_event]
    if story_event is not None:
        events.append(story_event)
    return events

from __future__ import annotations

import random
from enum import Enum
from typing import Optional, Any
import asyncio

from src.utils.config import CONFIG
from src.classes.core.avatar import Avatar
from src.classes.event import Event
from src.classes.story_event_service import StoryEventKind, StoryEventService
from src.classes.close_relation_event_service import (
    apply_positive_bond_warmth,
    configure_positive_bond_event,
)
from src.classes.technique import (
    TechniqueGrade,
    get_random_upper_technique_for_avatar,
    techniques_by_id,
    Technique,
    is_attribute_compatible_with_root,
    TechniqueAttribute,
)
from src.classes.items.weapon import Weapon, get_random_weapon_by_realm
from src.classes.items.auxiliary import Auxiliary, get_random_auxiliary_by_realm
from src.classes.relation.relation import Relation
from src.classes.relation.relations import get_live_related_avatars
from src.classes.alignment import Alignment
from src.systems.cultivation import Realm
from src.systems.single_choice import (
    ItemExchangeKind,
    ItemExchangeRequest,
    RejectMode,
    resolve_item_exchange,
)


class FortuneKind(Enum):
    """Fortune (lucky encounter) types."""
    WEAPON = "weapon"               # Weapon fortune
    AUXILIARY = "auxiliary"         # Auxiliary equipment fortune
    TECHNIQUE = "technique"
    FIND_MASTER = "find_master"
    SPIRIT_STONE = "spirit_stone"   # Spirit stone fortune
    CULTIVATION = "cultivation"     # Cultivation fortune




def _has_master(avatar: Avatar) -> bool:
    """Check whether the avatar already has a master."""
    return bool(get_live_related_avatars(avatar, identity_relation=Relation.IS_MASTER_OF))


def _is_alignment_compatible(avatar: Avatar, other: Avatar) -> bool:
    """Check whether two avatars' alignments are compatible (not hostile)."""
    from src.classes.alignment import Alignment
    if avatar.alignment is None or other.alignment is None:
        return True
    # Righteous and evil are incompatible
    if avatar.alignment == Alignment.RIGHTEOUS and other.alignment == Alignment.EVIL:
        return False
    if avatar.alignment == Alignment.EVIL and other.alignment == Alignment.RIGHTEOUS:
        return False
    return True


def _find_potential_master(avatar: Avatar) -> Optional[Avatar]:
    """
    Find a potential master in the world.
    Rules:
    1. Level > avatar.level + 20
    2. Prefer experts from the same sect
    3. If none in the same sect, pick someone else with a compatible alignment
    4. Cannot take someone from a hostile alignment as master
    """
    same_sect_candidates: list[Avatar] = []
    other_candidates: list[Avatar] = []
    
    for other in avatar.world.avatar_manager.get_living_avatars():
        if other is avatar:
            continue
        
        # Level gap check
        level_diff = other.cultivation_progress.level - avatar.cultivation_progress.level
        if level_diff < 20:
            continue
        
        # Alignment compatibility check
        if not _is_alignment_compatible(avatar, other):
            continue
        
        # Same sect first
        if avatar.sect is not None and other.sect == avatar.sect:
            same_sect_candidates.append(other)
        else:
            other_candidates.append(other)
    
    # Prefer choosing from the same sect
    if same_sect_candidates:
        return random.choice(same_sect_candidates)
    
    # No same-sect candidates; choose from the others
    if other_candidates:
        return random.choice(other_candidates)
    
    return None


def _can_get_weapon(avatar: Avatar) -> bool:
    """Check whether a weapon fortune is possible: triggers when the current weapon is Qi Refinement grade."""
    if avatar.weapon is None:
        return True
    return avatar.weapon.realm == Realm.Qi_Refinement


def _can_get_auxiliary(avatar: Avatar) -> bool:
    """Check whether an auxiliary fortune is possible: triggers with no auxiliary or a Qi Refinement grade one."""
    if avatar.auxiliary is None:
        return True
    return avatar.auxiliary.realm == Realm.Qi_Refinement


def _can_get_technique(avatar: Avatar) -> bool:
    """
    Check whether a technique fortune is possible.
    - Anyone whose technique is not Upper grade can trigger it
    - Whether a technique is actually obtained is checked again on acquisition (sect disciples are restricted)
    """
    tech_not_upper = (avatar.technique is None) or (avatar.technique.grade is not TechniqueGrade.UPPER)
    return tech_not_upper


def _can_get_master(avatar: Avatar) -> bool:
    """Check whether a find-master fortune is possible."""
    if _has_master(avatar):
        return False
    return _find_potential_master(avatar) is not None


def _can_get_spirit_stone(avatar: Avatar) -> bool:
    """Check whether a spirit stone fortune is possible."""
    # Anyone can obtain spirit stones
    return True


def _can_get_cultivation(avatar: Avatar) -> bool:
    """Check whether a cultivation fortune is possible."""
    # Only those not at a bottleneck can gain cultivation
    return not avatar.cultivation_progress.is_in_bottleneck()


def _choose_fortune_record(avatar: Avatar) -> Optional[dict]:
    """
    Randomly pick one config record from all possible fortunes.
    The possible fortunes depend on the avatar's current state and realm.
    """
    from src.utils.df import game_configs
    
    possible_records = []
    
    records = game_configs.get("fortune", [])
    for record in records:
        kind_str = record.get("kind")
        if not kind_str:
            continue
            
        try:
            kind = FortuneKind(kind_str.lower())
        except ValueError:
            continue
            
        min_realm_str = record.get("min_realm", "QI_REFINEMENT")
        max_realm_str = record.get("max_realm", "NASCENT_SOUL")
        
        min_realm = Realm.from_str(min_realm_str)
        max_realm = Realm.from_str(max_realm_str)
        
        if not (min_realm <= avatar.cultivation_progress.realm <= max_realm):
            continue
            
        # Check prerequisites
        can_trigger = False
        if kind == FortuneKind.WEAPON:
            can_trigger = _can_get_weapon(avatar)
        elif kind == FortuneKind.AUXILIARY:
            can_trigger = _can_get_auxiliary(avatar)
        elif kind == FortuneKind.TECHNIQUE:
            can_trigger = _can_get_technique(avatar)
        elif kind == FortuneKind.FIND_MASTER:
            can_trigger = _can_get_master(avatar)
        elif kind == FortuneKind.SPIRIT_STONE:
            can_trigger = _can_get_spirit_stone(avatar)
        elif kind == FortuneKind.CULTIVATION:
            can_trigger = _can_get_cultivation(avatar)
            
        if can_trigger:
            possible_records.append(record)
            
    if not possible_records:
        return None
        
    weights = [float(r.get("weight", 10)) for r in possible_records]
    return random.choices(possible_records, weights=weights, k=1)[0]




def _get_weapon_for_avatar(avatar: Avatar) -> Optional[Weapon]:
    """
    Get a weapon:
    Fortunes usually offer a weapon better than the current realm.
    In Qi Refinement, offer a Foundation Establishment weapon.
    Other realms get a same-realm weapon (high-realm weapons are already rare and strong).
    """
    target_realm = avatar.cultivation_progress.realm
    if target_realm == Realm.Qi_Refinement:
        target_realm = Realm.Foundation_Establishment
        
    return get_random_weapon_by_realm(target_realm)


def _get_auxiliary_for_avatar(avatar: Avatar) -> Optional[Auxiliary]:
    """
    Get auxiliary equipment:
    Same rules as weapons.
    """
    target_realm = avatar.cultivation_progress.realm
    if target_realm == Realm.Qi_Refinement:
        target_realm = Realm.Foundation_Establishment
        
    return get_random_auxiliary_by_realm(target_realm)


def _get_fortune_technique_for_avatar(avatar: Avatar) -> Optional[Technique]:
    """
    Get a technique for the fortune.
    Rules:
    1. Rogue cultivators: may obtain any Upper grade technique (compatible with spirit root/alignment/condition)
    2. Sect disciples: may only obtain Upper grade techniques of their own sect or with no sect
    """
    candidates: list[Technique] = []
    
    # Determine the allowed sect IDs
    allowed_sect_ids: set[Optional[int]] = {None}
    if avatar.sect is not None:
        allowed_sect_ids.add(avatar.sect.id)
    
    # Filter techniques
    for t in techniques_by_id.values():
        # Must be Upper grade
        if t.grade != TechniqueGrade.UPPER:
            continue
        
        # Sect restriction: disciples may only get techniques of their sect or with no sect
        if t.sect_id not in allowed_sect_ids:
            continue
        
        # condition check
        if not t.is_allowed_for(avatar):
            continue
        
        # Evil techniques can only be practiced by evil cultivators
        if t.attribute == TechniqueAttribute.EVIL and avatar.alignment != Alignment.EVIL:
            continue
        
        # Spirit root compatibility
        if not is_attribute_compatible_with_root(t.attribute, avatar.root):
            continue
        
        candidates.append(t)
    
    if not candidates:
        return None
    
    # Weighted random choice
    weights = [max(0.0, t.weight) for t in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]


def _get_spirit_stone_amount(avatar: Avatar) -> int:
    """Return spirit stones by realm (about one year of hunting and selling income)."""
    from src.systems.cultivation import Realm
    
    realm_ranges = {
        Realm.Qi_Refinement: (20, 30),
        Realm.Foundation_Establishment: (100, 150),
        Realm.Core_Formation: (200, 300),
        Realm.Nascent_Soul: (400, 600),
    }
    range_tuple = realm_ranges.get(
        avatar.cultivation_progress.realm, 
        (20, 30)  # Default
    )
    return random.randint(*range_tuple)


def get_cultivation_exp_reward(avatar: Avatar) -> int:
    """Return cultivation experience by realm (about one year of cultivation gains)."""
    from src.systems.cultivation import Realm
    
    realm_exp = {
        Realm.Qi_Refinement: 600,
        Realm.Foundation_Establishment: 800,
        Realm.Core_Formation: 1000,
        Realm.Nascent_Soul: 1200,
    }
    return realm_exp.get(
        avatar.cultivation_progress.realm,
        600  # Default
    )


async def try_trigger_fortune(avatar: Avatar) -> list[Event]:
    """
    Try to trigger a fortune during the monthly settlement phase.
    Rules:
    - A fortune is not an action; it only triggers with some probability when conditions are met.
    - Trigger conditions:
      * Weapon: the current weapon is common grade
      * Auxiliary: no auxiliary equipment, or it is below treasure grade
      * Technique: technique is not Upper grade (rogue or sect, but disciples only get own-sect or sectless techniques)
      * Find master: no master and a suitable master exists in the world (same sect preferred, never a hostile alignment)
      * Spirit stones: anyone can trigger
      * Cultivation: anyone not at a bottleneck can trigger
    - Results:
      * Weapon: prefer a treasure (unique in the world) > a regular item (repeatable)
      * Auxiliary: prefer a treasure (unique in the world) > a regular item (repeatable)
      * Technique: repeatable, Upper grade preferred, must match spirit root, disciples restricted by sect
      * Find master: establish a master-disciple relation
      * Spirit stones: gain spirit stones by realm (about one year of hunting and selling income)
      * Cultivation: gain cultivation experience by realm (about one year of cultivation gains)
    - Story: only the theme is given; the LLM freely writes a short story.
    """
    base_prob = float(getattr(CONFIG.world, "fortune_probability", 0.0))
    extra_prob = float(avatar.effects.get("extra_fortune_probability", 0.0))
    prob = max(0.0, base_prob + extra_prob)
    if prob <= 0.0:
        return []

    # Check whether the current action state allows world events to trigger
    if not avatar.can_trigger_world_event:
        return []
    
    if random.random() >= prob:
        return []

    # Choose from all possible fortunes
    record = _choose_fortune_record(avatar)
    if not record:
        return []
        
    kind = FortuneKind(record["kind"].lower())
    
    res_text: str = ""
    related_avatars = [avatar.id]
    actors_for_story = [avatar]  # Avatars used for story generation

    
    if kind == FortuneKind.WEAPON:
        weapon = _get_weapon_for_avatar(avatar)
        if weapon is None:
            # Fall back to a technique
            kind = FortuneKind.TECHNIQUE
            record["title_id"] = "fortune_title_technique"
        else:
            from src.i18n import t
            # Use str() so Realm.__str__ performs the i18n translation.
            intro = t("You discovered a {realm} weapon '{weapon_name}' in your fortune.",
                     realm=str(weapon.realm), weapon_name=weapon.name)
            if avatar.weapon:
                intro += t(" But you already have '{weapon_name}'.", weapon_name=avatar.weapon.name)

            outcome = await resolve_item_exchange(
                ItemExchangeRequest(
                    avatar=avatar,
                    new_item=weapon,
                    kind=ItemExchangeKind.WEAPON,
                    scene_intro=intro,
                    reject_mode=RejectMode.ABANDON_NEW,
                    auto_accept_when_empty=True,
                )
            )
            res_text = t(
                "Discovered weapon '{weapon_name}', {exchange_text}",
                weapon_name=weapon.name,
                exchange_text=outcome.result_text,
            )

    elif kind == FortuneKind.AUXILIARY:
        auxiliary = _get_auxiliary_for_avatar(avatar)
        if auxiliary is None:
            # Fall back to a technique
            kind = FortuneKind.TECHNIQUE
            record["title_id"] = "fortune_title_technique"
        else:
            from src.i18n import t
            # Use str() so Realm.__str__ performs the i18n translation.
            intro = t("You discovered a {realm} auxiliary '{auxiliary_name}' in your fortune.",
                     realm=str(auxiliary.realm), auxiliary_name=auxiliary.name)
            if avatar.auxiliary:
                intro += t(" But you already have '{auxiliary_name}'.", auxiliary_name=avatar.auxiliary.name)

            outcome = await resolve_item_exchange(
                ItemExchangeRequest(
                    avatar=avatar,
                    new_item=auxiliary,
                    kind=ItemExchangeKind.AUXILIARY,
                    scene_intro=intro,
                    reject_mode=RejectMode.ABANDON_NEW,
                    auto_accept_when_empty=True,
                )
            )
            res_text = t(
                "Discovered auxiliary '{auxiliary_name}', {exchange_text}",
                auxiliary_name=auxiliary.name,
                exchange_text=outcome.result_text,
            )

    if kind == FortuneKind.TECHNIQUE:
        tech = _get_fortune_technique_for_avatar(avatar)
        if tech is None:
            return []
        
        from src.i18n import t
        intro = t("You comprehended an upper-grade technique '{technique_name}' in your fortune.",
                 technique_name=tech.name)
        if avatar.technique:
            intro += t(" This conflicts with your current technique '{technique_name}'.",
                      technique_name=avatar.technique.name)

        outcome = await resolve_item_exchange(
            ItemExchangeRequest(
                avatar=avatar,
                new_item=tech,
                kind=ItemExchangeKind.TECHNIQUE,
                scene_intro=intro,
                reject_mode=RejectMode.ABANDON_NEW,
                auto_accept_when_empty=True,
            )
        )
        res_text = t(
            "Comprehended technique '{technique_name}', {exchange_text}",
            technique_name=tech.name,
            exchange_text=outcome.result_text,
        )

    elif kind == FortuneKind.FIND_MASTER:
        master = _find_potential_master(avatar)
        if master is None:
            # No suitable master found
            return []
        # Establish master-disciple relation: avatar is the disciple, master is the master
        # avatar sees master as MASTER, master sees avatar as DISCIPLE (the counterpart is set automatically).
        avatar.acknowledge_master(master)
        from src.i18n import t
        res_text = t("{avatar_name} became disciple of {master_name}",
                    avatar_name=avatar.name, master_name=master.name)
        related_avatars.append(master.id)
        actors_for_story = [avatar, master]  # The find-master fortune needs info for both avatars

    elif kind == FortuneKind.SPIRIT_STONE:
        amount = _get_spirit_stone_amount(avatar)
        avatar.magic_stone.value += amount
        from src.i18n import t
        res_text = t("{avatar_name} obtained {amount} spirit stones",
                    avatar_name=avatar.name, amount=amount)

    elif kind == FortuneKind.CULTIVATION:
        exp_gain = get_cultivation_exp_reward(avatar)
        avatar.cultivation_progress.add_exp(exp_gain)
        from src.i18n import t
        res_text = t("{avatar_name} gained {exp_gain} cultivation experience",
                    avatar_name=avatar.name, exp_gain=exp_gain)

    # Extract the action the avatar is currently performing
    action_desc = t("wandering aimlessly")
    if avatar.current_action and avatar.current_action.action:
        action_name = avatar.current_action.action.__class__.__name__
        action_desc = f"{action_name} ({avatar.current_action.params})"
        
    location_name = avatar.tile.region.name if avatar.tile and avatar.tile.region else t("unknown location")

    # Generate the story (async, awaited)
    title_text = t(record.get("title_id", "fortune_title_mystery"))
    event_text = t("fortune_event_base",
                   title=title_text, result=res_text)
                   
    story_prompt = t("fortune_dynamic_story_prompt",
                     realm=str(avatar.cultivation_progress.realm),
                     location=location_name,
                     action_desc=action_desc,
                     result=res_text)

    month_at_finish = avatar.world.month_stamp
    event_type = "bond_master_disciple_formed" if kind == FortuneKind.FIND_MASTER else "world_fortune"
    base_event = Event(
        month_at_finish,
        event_text,
        related_avatars=related_avatars,
        is_major=True,
        event_type=event_type,
    )
    if kind == FortuneKind.FIND_MASTER and len(actors_for_story) >= 2:
        disciple = avatar
        master = actors_for_story[1]
        configure_positive_bond_event(base_event, avatar_a=disciple, avatar_b=master)
        apply_positive_bond_warmth(subject=disciple, other_party=master, event_type=event_type)
        apply_positive_bond_warmth(subject=master, other_party=disciple, event_type=event_type)

    # Generate the story event
    # Fortunes force single-avatar mode and do not change relations (already handled by hard logic)
    story_event = await StoryEventService.maybe_create_story(
        kind=StoryEventKind.WORLD_FORTUNE,
        month_stamp=month_at_finish,
        start_text=event_text,
        result_text=res_text,
        actors=actors_for_story,
        related_avatar_ids=related_avatars,
        prompt=story_prompt,
        allow_relation_changes=False,
    )

    events = [base_event]
    if story_event is not None:
        events.append(story_event)
    return events


class MisfortuneKind(Enum):
    """Misfortune types."""
    LOSS_SPIRIT_STONE = "loss_spirit_stone" # Lose spirit stones
    INJURY = "injury"                       # Injury
    CULTIVATION_BACKLASH = "backlash"       # Cultivation backlash




def _choose_misfortune_record(avatar: Avatar) -> Optional[dict]:
    """Choose a misfortune config record."""
    from src.utils.df import game_configs
    
    possible_records = []
    records = game_configs.get("misfortune", [])
    
    for record in records:
        kind_str = record.get("kind")
        if not kind_str:
            continue
            
        try:
            kind = MisfortuneKind(kind_str.lower())
        except ValueError:
            continue
            
        min_realm_str = record.get("min_realm", "QI_REFINEMENT")
        max_realm_str = record.get("max_realm", "NASCENT_SOUL")
        
        min_realm = Realm.from_str(min_realm_str)
        max_realm = Realm.from_str(max_realm_str)
        
        if not (min_realm <= avatar.cultivation_progress.realm <= max_realm):
            continue
            
        can_trigger = False
        if kind == MisfortuneKind.LOSS_SPIRIT_STONE:
            can_trigger = avatar.magic_stone.value > 0
        elif kind == MisfortuneKind.INJURY:
            can_trigger = True
        elif kind == MisfortuneKind.CULTIVATION_BACKLASH:
            can_trigger = True
            
        if can_trigger:
            possible_records.append(record)
            
    if not possible_records:
        return None
        
    weights = [float(r.get("weight", 10)) for r in possible_records]
    return random.choices(possible_records, weights=weights, k=1)[0]




async def try_trigger_misfortune(avatar: Avatar) -> list[Event]:
    """
    Trigger a misfortune.
    Rules:
    - Probability: config + effects
    - Types: lose spirit stones, injury, cultivation backlash
    - Lose spirit stones: random amount, never more than the total
    - Injury: reduce HP, possibly fatal (resolved by the simulator)
    - Cultivation backlash: reduce experience without dropping a level; here current exp is reduced, minimum 0
    """
    base_prob = float(getattr(CONFIG.world, "misfortune_probability", 0.0))
    extra_prob = float(avatar.effects.get("extra_misfortune_probability", 0.0))
    prob = max(0.0, base_prob + extra_prob)
    if prob <= 0.0:
        return []

    # Check whether the current action state allows world events to trigger
    if not avatar.can_trigger_world_event:
        return []
    
    if random.random() >= prob:
        return []
        
    record = _choose_misfortune_record(avatar)
    if not record:
        return []
        
    kind = MisfortuneKind(record["kind"].lower())
    res_text: str = ""
    
    from src.i18n import t

    if kind == MisfortuneKind.LOSS_SPIRIT_STONE:
        # Lose spirit stones: random amount, never more than the total
        max_loss = avatar.magic_stone.value
        # Pick a random range (e.g. 10-500), capped by max_loss
        # or fully random
        loss = random.randint(50, 300)
        loss = min(loss, max_loss)
        avatar.magic_stone.value -= loss
        res_text = t("misfortune_result_loss_spirit_stone", name=avatar.name, amount=loss)
        
    elif kind == MisfortuneKind.INJURY:
        # Injury: reduce HP
        # Amount: 10%-30% of max HP plus a flat value
        max_hp = avatar.hp.max
        ratio = random.uniform(0.1, 0.3)
        damage = int(max_hp * ratio) + random.randint(10, 50)
        
        avatar.hp.cur -= damage
        # Note: this may go negative; the simulator handles it in _phase_resolve_death
        res_text = t("misfortune_result_injury", name=avatar.name, damage=damage, current=avatar.hp.cur, max=max_hp)
        
    elif kind == MisfortuneKind.CULTIVATION_BACKLASH:
        # Cultivation backlash
        # Amount: 100-500
        loss = random.randint(100, 500)
        
        # Make sure it does not go negative (experience is normally non-negative)
        # Only reduce current experience; never drop a level
        current_exp = avatar.cultivation_progress.exp
        actual_loss = min(current_exp, loss)
        avatar.cultivation_progress.exp -= actual_loss
        
        res_text = t("misfortune_result_backlash", name=avatar.name, amount=actual_loss)
        
    # Extract the action the avatar is currently performing
    action_desc = t("wandering aimlessly")
    if avatar.current_action and avatar.current_action.action:
        action_name = avatar.current_action.action.__class__.__name__
        action_desc = f"{action_name} ({avatar.current_action.params})"
        
    location_name = avatar.tile.region.name if avatar.tile and avatar.tile.region else t("unknown location")

    # Generate the story
    title_text = t(record.get("title_id", "misfortune_title_mystery"))
    event_text = t("misfortune_event_base", title=title_text, result=res_text)
    
    story_prompt = t("misfortune_dynamic_story_prompt",
                     realm=str(avatar.cultivation_progress.realm),
                     location=location_name,
                     action_desc=action_desc,
                     result=res_text)
    
    month_at_finish = avatar.world.month_stamp
    base_event = Event(month_at_finish, event_text, related_avatars=[avatar.id], is_major=True)
    
    story_event = await StoryEventService.maybe_create_story(
        kind=StoryEventKind.WORLD_MISFORTUNE,
        month_stamp=month_at_finish,
        start_text=event_text,
        result_text=res_text,
        actors=[avatar],
        related_avatar_ids=[avatar.id],
        prompt=story_prompt,
        allow_relation_changes=False,
    )

    events = [base_event]
    if story_event is not None:
        events.append(story_event)
    return events


__all__ = [
    "try_trigger_fortune",
    "get_cultivation_exp_reward",
    "try_trigger_misfortune",
]

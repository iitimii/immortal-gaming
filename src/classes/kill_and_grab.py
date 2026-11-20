from __future__ import annotations
from typing import TYPE_CHECKING
import random

from src.systems.single_choice import (
    ItemDisposition,
    ItemExchangeKind,
    ItemExchangeRequest,
    RejectMode,
    resolve_item_exchange,
)

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


async def kill_and_grab(winner: Avatar, loser: Avatar) -> str:
    """
    Handle the kill-and-grab logic
    
    Args:
        winner: the winner
        loser: the loser (already dead)
        
    Returns:
        str: text describing the seized loot (e.g. "seized ..."), or an empty string if nothing was seized
    """
    loot_candidates = []
    
    # Check the weapon
    if loser.weapon:
        loot_candidates.append(("weapon", loser.weapon))
    
    # Check the auxiliary
    if loser.auxiliary:
        loot_candidates.append(("auxiliary", loser.auxiliary))
    
    if not loot_candidates:
        return ""

    # Prefer higher realms
    loot_candidates.sort(key=lambda x: x[1].realm, reverse=True)
    # Keep only the highest-priority candidates
    best_realm = loot_candidates[0][1].realm
    best_candidates = [c for c in loot_candidates if c[1].realm == best_realm]
    loot_type, loot_item = random.choice(best_candidates)
    
    # Decide whether to seize
    item_label = 'weapon' if loot_type == 'weapon' else 'auxiliary'
    # Use str() to trigger Realm.__str__ for i18n translation.
    context = f"Victorious in battle: {loser.name} has perished, leaving behind a {str(loot_item.realm)} {item_label} [{loot_item.name}]."
    
    outcome = await resolve_item_exchange(
        ItemExchangeRequest(
            avatar=winner,
            new_item=loot_item,
            kind=ItemExchangeKind(loot_type),
            scene_intro=context,
            reject_mode=RejectMode.ABANDON_NEW,
            auto_accept_when_empty=True,
        )
    )

    if outcome.accepted and outcome.action in {
        ItemDisposition.AUTO_ACCEPTED,
        ItemDisposition.REPLACED_OLD,
    }:
        if loot_type == "weapon":
            loser.change_weapon(None)
        else:
            loser.change_auxiliary(None)
        
        return f"Seized the {item_label} [{loot_item.name}]. {outcome.result_text}"
    
    return ""

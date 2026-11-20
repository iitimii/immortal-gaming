from __future__ import annotations
from typing import TYPE_CHECKING, List, Tuple, Optional
import asyncio

from src.i18n import t
from src.classes.relation.relation import Relation
from src.classes.relation.relations import (
    set_relation,
    cancel_relation,
)
from src.systems.time import get_date_str
from src.classes.event import Event
from src.classes.close_relation_event_service import (
    apply_positive_bond_warmth,
    configure_positive_bond_event,
)
from src.utils.llm import call_llm_with_task_name
from src.utils.config import CONFIG

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

class RelationResolver:
    TEMPLATE_PATH = CONFIG.paths.templates / "relation_update.txt"
    
    @staticmethod
    def _build_prompt_data(avatar_a: "Avatar", avatar_b: "Avatar") -> dict:
        # 1. Get recent interaction records
        # Prefer the EventManager index
        event_manager = avatar_a.world.event_manager
        
        # Get archived historical events (latest 10)
        # get_events_between returns events in chronological order
        recent_events = event_manager.get_events_between(avatar_a.id, avatar_b.id, limit=10)
        
        event_lines = [str(e) for e in recent_events]
            
        recent_events_text = "\n".join(event_lines) if event_lines else t("No significant recent interactions.")
        
        # 2. Get the current relation description
        current_rel = avatar_a.get_relation(avatar_b)
        rel_desc = t("None")
        if current_rel:
            rel_name = str(current_rel)
            rel_desc = f"{rel_name}"
        
        # Get the current world time
        current_time_str = get_date_str(avatar_a.world.month_stamp)
        
        return {
            "relation_rules_desc": "",
            "avatar_a_name": avatar_a.name,
            "avatar_a_info": str(avatar_a.get_info(detailed=True)),
            "avatar_b_name": avatar_b.name,
            "avatar_b_info": str(avatar_b.get_info(detailed=True)),
            "current_relations": t("Current relations: {rel_desc}", rel_desc=rel_desc),
            "recent_events_text": recent_events_text,
            "current_time": current_time_str
        }

    @staticmethod
    async def resolve_pair(avatar_a: "Avatar", avatar_b: "Avatar") -> Optional[Event]:
        """
        Process relation changes for a pair of avatars and return the resulting events
        """
        infos = RelationResolver._build_prompt_data(avatar_a, avatar_b)
        
        result = await call_llm_with_task_name("relation_resolver", RelationResolver.TEMPLATE_PATH, infos)
            
        changed = result.get("changed", False)
        if not changed:
            return None
            
        month_stamp = avatar_a.world.month_stamp
        
        c_type = result.get("change_type")
        rel_name = result.get("relation")
        reason = result.get("reason", "")
        
        if not rel_name:
            return None

        # Parse the relation enum
        try:
            # Try to get it by the new name
            rel = Relation[rel_name]
        except KeyError:
            return None
            
        display_name = str(rel)
        event = None
            
        if c_type == "ADD":
            # Logic: if the LLM outputs "IS_MASTER_OF" (key) or "master" (value)
            # it means A is B's Master.
            # set_relation(from, to, rel) means: from considers to to be rel.
            # If A is B's Master, then B should consider A as IS_MASTER_OF.
            # So call set_relation(B, A, IS_MASTER_OF).
            
            event_type = "relationship_major"
            # Using the new semantic methods is safer
            target_method = None
            if rel == Relation.IS_MASTER_OF:
                # A is B's Master -> B takes A as master
                avatar_b.acknowledge_master(avatar_a)
                event_type = "bond_master_disciple_formed"
            elif rel == Relation.IS_DISCIPLE_OF:
                # A is B's Disciple -> B takes A as disciple
                avatar_b.accept_disciple(avatar_a)
                event_type = "bond_master_disciple_formed"
            elif rel == Relation.IS_PARENT_OF:
                # A is B's Parent -> B acknowledges A as father/mother
                avatar_b.acknowledge_parent(avatar_a)
            elif rel == Relation.IS_CHILD_OF:
                # A is B's Child -> B acknowledges A as son/daughter
                avatar_b.acknowledge_child(avatar_a)
            elif rel == Relation.IS_LOVER_OF:
                avatar_b.become_lovers_with(avatar_a)
                event_type = "bond_lovers_formed"
            else:
                # Fall back to the low-level method (set_relation(B, A, rel))
                avatar_b.set_relation(avatar_a, rel)
                if rel == Relation.IS_SWORN_SIBLING_OF:
                    event_type = "bond_sworn_sibling_formed"
            
            event_text = t(
                "Because {reason}, {avatar_a} became {avatar_b}'s {relation}.",
                reason=reason,
                avatar_a=avatar_a.name,
                avatar_b=avatar_b.name,
                relation=display_name,
            )
            event = Event(
                month_stamp,
                event_text,
                related_avatars=[avatar_a.id, avatar_b.id],
                is_major=True,
                event_type=event_type,
            )
            if event_type in {
                "bond_master_disciple_formed",
                "bond_lovers_formed",
                "bond_sworn_sibling_formed",
            }:
                configure_positive_bond_event(event, avatar_a=avatar_a, avatar_b=avatar_b)
                apply_positive_bond_warmth(subject=avatar_a, other_party=avatar_b, event_type=event_type)
                apply_positive_bond_warmth(subject=avatar_b, other_party=avatar_a, event_type=event_type)
            
        elif c_type == "REMOVE":
            # Same reversed call
            # Removing a relation can only use the low-level cancel_relation
            success = cancel_relation(avatar_b, avatar_a, rel)
            if success:
                event_text = t(
                    "Because {reason}, {avatar_a} is no longer {avatar_b}'s {relation}.",
                    reason=reason,
                    avatar_a=avatar_a.name,
                    avatar_b=avatar_b.name,
                    relation=display_name,
                )
                event = Event(month_stamp, event_text, related_avatars=[avatar_a.id, avatar_b.id], is_major=True)

        if event:
            return event
            
        return None

    @staticmethod
    async def run_batch(pairs: List[Tuple["Avatar", "Avatar"]]) -> List[Event]:
        """
        Process in concurrent batches and return all resulting events
        """
        if not pairs:
            return []

        # Run all tasks concurrently
        tasks = [RelationResolver.resolve_pair(a, b) for a, b in pairs]
        results = await asyncio.gather(*tasks)
        
        # Filter out None results (resolve_pair returns None on failure or no change)
        return [res for res in results if res]

"""
Long-term objective module
Generates and manages long-term objectives (5-10 years) for avatars
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

from src.classes.event import Event
from src.utils.config import CONFIG
from src.utils.llm import call_llm_with_task_name
from src.run.log import get_logger
from src.classes.actions import get_action_infos_str
from src.i18n import t

logger = get_logger().logger


@dataclass
class LongTermObjective:
    """Long-term objective."""
    content: str  # Objective content
    origin: str  # "llm" or "user"
    set_year: int  # Year it was set


def can_generate_long_term_objective(avatar: "Avatar") -> bool:
    """
    Check whether the avatar needs to generate/update its long-term objective
    
    Rules:
    1. If there's a user-set objective, never auto-generate
    2. With no objective, may generate
    3. Less than 5 years since last set: don't generate
    4. 10 or more years since last set: always generate
    5. 5-10 years since last set: generate with probability (increasing gradually)
    
    Args:
        avatar: the avatar to check
        
    Returns:
        Whether a long-term objective should be generated
    """
    # A user-set objective exists; no more auto-generation
    if avatar.long_term_objective and avatar.long_term_objective.origin == "user":
        return False
    
    current_year = avatar.world.month_stamp.get_year()
    
    # First time setting (no objective)
    if not avatar.long_term_objective:
        return True
    
    years_passed = current_year - avatar.long_term_objective.set_year
    
    if years_passed < 5:
        return False
    elif years_passed >= 10:
        return True
    else:  # Between 5 and 10 years
        # Gradual probability: 10% at 5 years, increasing over time, approaching 100% near 10 years
        probability = (years_passed - 5) / 5 * 0.9 + 0.1
        return random.random() < probability


async def generate_long_term_objective(avatar: "Avatar") -> Optional[LongTermObjective]:
    """
    Generate a long-term objective for the avatar
    
    Call the LLM to generate a suitable long-term objective based on the avatar's info and event history
    
    Args:
        avatar: the avatar to generate a long-term objective for
        
    Returns:
        The generated LongTermObjective, or None on failure
    """
    # Prepare world info (only known regions + distance info)
    world_info = avatar.world.get_info(avatar=avatar)
    
    # Get expanded_info (detailed info and event history)
    expanded_info = avatar.get_expanded_info(detailed=True)
    
    # Prepare template params
    template_path = CONFIG.paths.templates / "long_term_objective.txt"
    infos = {
        "world_info": world_info,
        "world_lore": avatar.world.world_lore.text,
        "avatar_info": expanded_info,
        "general_action_infos": get_action_infos_str(avatar),
    }
    
    # Call the LLM and parse the JSON automatically (using the configured model mode)
    response_data = await call_llm_with_task_name("long_term_objective", template_path, infos)
    
    content = response_data.get("long_term_objective", "").strip()
    
    if not content:
        logger.warning(f"Failed to generate a long-term objective for avatar {avatar.name}: empty content returned")
        return None
    
    current_year = avatar.world.month_stamp.get_year()
    objective = LongTermObjective(
        content=content,
        origin="llm",
        set_year=current_year
    )
    
    logger.info(f"Generated a long-term objective for avatar {avatar.name}: {content}")
    
    return objective
        


async def process_avatar_long_term_objective(avatar: "Avatar") -> Optional[Event]:
    """
    Handle long-term objective generation/update for a single avatar
    
    Check whether the avatar needs an objective; if so, generate it and return the corresponding event
    
    Args:
        avatar: the avatar to process
        
    Returns:
        The generated event, or None if not needed or generation failed
    """
    if not can_generate_long_term_objective(avatar):
        return None
    
    old_objective = avatar.long_term_objective
    new_objective = await generate_long_term_objective(avatar)
    
    if not new_objective:
        return None
    
    avatar.long_term_objective = new_objective
    
    # Generate the event
    if old_objective:
        # Update the objective
        event = Event(
            avatar.world.month_stamp,
            t("{avatar_name} deliberated and redefined their long-term objective: {objective}", avatar_name=avatar.name, objective=new_objective.content),
            related_avatars=[avatar.id],
            is_major=False
        )
    else:
        # First-time objective
        event = Event(
            avatar.world.month_stamp,
            t("{avatar_name} determined their long-term objective: {objective}", avatar_name=avatar.name, objective=new_objective.content),
            related_avatars=[avatar.id],
            is_major=False
        )
    
    return event


def set_user_long_term_objective(avatar: "Avatar", objective_content: str) -> None:
    """
    Set the avatar's long-term objective by the player
    
    After the user sets it, origin is marked "user" and the system no longer calls the LLM to update it automatically
    The player may still call this function again to change it
    
    Args:
        avatar: the avatar to set the objective for
        objective_content: objective content
    """
    current_year = avatar.world.month_stamp.get_year()
    avatar.long_term_objective = LongTermObjective(
        content=objective_content,
        origin="user",
        set_year=current_year
    )
    
    # When the user sets a long-term objective manually, clear the short-term objective and pending plans so the AI replans
    avatar.short_term_objective = ""
    avatar.clear_plans()
    
    logger.info(f"Player set long-term objective for avatar {avatar.name}: {objective_content}; short-term objective and pending plans cleared")


def clear_user_long_term_objective(avatar: "Avatar") -> bool:
    """
    Clear the player-set long-term objective
    If the current objective was generated by system/llm, don't clear it and return False
    If it was user-generated, clear it and return True
    """
    if avatar.long_term_objective and avatar.long_term_objective.origin == "user":
        avatar.long_term_objective = None
        logger.info(f"Player cleared the long-term objective of avatar {avatar.name}")
        return True
    return False

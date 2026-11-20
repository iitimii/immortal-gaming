"""
Nickname generation
Generates cultivation-world nicknames for eligible avatars
"""
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar
    from src.classes.core.world import World

from src.classes.event import Event
from src.utils.config import CONFIG
from src.utils.llm import call_llm_with_task_name
from src.run.log import get_logger
from src.i18n import t

from src.classes.nickname_data import Nickname

logger = get_logger().logger


def can_get_nickname(avatar: "Avatar") -> bool:
    """
    Check whether an avatar qualifies for a nickname
    
    Conditions:
    1. No nickname yet (nickname is None)
    2. Major event count >= major_event_threshold
    3. Minor event count >= minor_event_threshold
    
    Args:
        avatar: the avatar to check
        
    Returns:
        whether the conditions are met
    """
    # Check for an existing nickname and its age
    if avatar.nickname is not None:
        current_year = avatar.world.month_stamp.get_year()
        # Do not regenerate within 10 years
        if current_year - avatar.nickname.created_year < 10:
            return False
    
    # Check event counts
    em = avatar.world.event_manager
    major_threshold = CONFIG.nickname.major_event_threshold
    minor_threshold = CONFIG.nickname.minor_event_threshold
    
    major_events = em.get_major_events_by_avatar(avatar.id, limit=major_threshold)
    minor_events = em.get_minor_events_by_avatar(avatar.id, limit=minor_threshold)
    
    major_count = len(major_events)
    minor_count = len(minor_events)
    
    # AND logic: both conditions must hold
    return major_count >= major_threshold and minor_count >= minor_threshold


async def generate_nickname(avatar: "Avatar") -> Optional[dict]:
    """
    Generate a nickname for an avatar
    
    Calls the LLM to produce a fitting nickname from the avatar's info and event history
    
    Args:
        avatar: the avatar to name
        
    Returns:
        dict with nickname and reason, or None on failure
    """
    try:
        # Get expanded_info (detailed info plus event history)
        expanded_info = avatar.get_expanded_info(detailed=True)
        
        # Prepare template parameters
        template_path = CONFIG.paths.templates / "nickname.txt"
        infos = {
            "world_info": avatar.world.static_info,
            "world_lore": avatar.world.world_lore.text,
            "avatar_info": expanded_info,
        }
        
        # Call the LLM and parse the JSON response
        response_data = await call_llm_with_task_name("nickname", template_path, infos)
        
        nickname = response_data.get("nickname", "").strip()
        thinking = response_data.get("thinking", "")
        reason = response_data.get("reason", "").strip()
        
        if not nickname:
            logger.warning(f"Nickname generation for avatar {avatar.name} failed: empty nickname returned")
            return None
        
        logger.info(f"Generated nickname for avatar {avatar.name}: {nickname} (reason: {reason})")
        logger.debug(f"Nickname generation reasoning: {thinking}")
        
        return {
            "nickname": nickname,
            "reason": reason
        }
        
    except Exception as e:
        logger.error(f"Error while generating nickname: {e}")
        return None


async def process_avatar_nickname(avatar: "Avatar") -> Optional[Event]:
    """
    Handle nickname generation for a single avatar
    
    If the avatar qualifies, generate a nickname and return the corresponding event
    
    Args:
        avatar: the avatar to process
        
    Returns:
        the generated event, or None if not eligible or generation failed
    """
    if not can_get_nickname(avatar):
        return None
    
    result = await generate_nickname(avatar)
    if not result:
        return None
    
    nickname_str = result["nickname"]
    reason = result["reason"]
    
    current_year = avatar.world.month_stamp.get_year()
    avatar.nickname = Nickname(value=nickname_str, reason=reason, created_year=current_year)
    
    # Create the event: the avatar earns a nickname
    event = Event(
        avatar.world.month_stamp,
        t(
            '{avatar_name} made a name in the cultivation world and came to be known as "{nickname}".',
            avatar_name=avatar.name,
            nickname=nickname_str,
        ),
        related_avatars=[avatar.id],
        is_major=True,
        render_key="nickname_awarded",
        render_params={
            "avatar_name": avatar.name,
            "nickname": nickname_str,
        }
    )
    return event


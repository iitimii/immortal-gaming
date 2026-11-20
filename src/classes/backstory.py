import asyncio
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

from src.classes.ai import call_llm_with_task_name
from src.utils.config import CONFIG
from src.run.log import get_logger

logger = get_logger().logger

def can_get_backstory(avatar: "Avatar") -> bool:
    """
    Determine whether the avatar needs a backstory generated.
    """
    if avatar.is_dead:
        return False
    
    # If there's already a backstory, don't generate another
    if avatar.backstory is not None:
        return False
        
    return True

async def generate_backstory(avatar: "Avatar") -> Optional[str]:
    """
    Call the LLM to generate the avatar's backstory.
    """
    try:
        from src.classes.core.world import World
        
        infos = {
            "world_info": str(avatar.world.get_info()),
            "world_lore": avatar.world.world_lore.text,
            "avatar_info": str(avatar.get_expanded_info(detailed=True))
        }
        if getattr(avatar, "is_yao", False):
            from src.i18n import t

            race_name = str(getattr(getattr(avatar, "race", None), "get_info", lambda detailed=False: {"name": "Yao"})(detailed=False).get("name", "Yao"))
            infos["avatar_info"] += "\n" + t("yao_backstory_constraint", race=race_name)
        
        template_path = CONFIG.paths.templates / "backstory.txt"
        
        # Call the LLM using the backstory task from config (fast by default)
        response_data = await call_llm_with_task_name("backstory", template_path, infos)
        
        backstory = response_data.get("backstory", "").strip()
        
        if not backstory:
            return None
            
        logger.info(f"Generated backstory for avatar {avatar.name}: {backstory}")
        return backstory
        
    except Exception as e:
        logger.error(f"Failed to generate backstory for {avatar.name}: {e}")
        return None

async def process_avatar_backstory(avatar: "Avatar") -> None:
    """
    Generate and set the avatar's backstory (skipped if conditions aren't met).
    Returns nothing; modifies the avatar attributes directly.
    """
    if not can_get_backstory(avatar):
        return
        
    backstory = await generate_backstory(avatar)
    
    if backstory:
        avatar.backstory = backstory

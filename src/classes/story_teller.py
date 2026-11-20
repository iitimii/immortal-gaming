from __future__ import annotations

from typing import Dict, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

from src.utils.config import CONFIG
from src.utils.llm import call_llm_with_task_name
from src.i18n.story_styles import get_random_story_style


class StoryTeller:
    """
    Story teller: expands given events into short stories using templates and the LLM.
    """
    
    TEMPLATE_SINGLE_FILE = "story_single.txt"
    TEMPLATE_DUAL_FILE = "story_dual.txt"
    TEMPLATE_GATHERING_FILE = "story_gathering.txt"

    @staticmethod
    def _get_template_path(filename: str) -> Path:
        """Get the template path for the current locale."""
        return CONFIG.paths.templates / filename

    @staticmethod
    def _build_avatar_infos(*actors: "Avatar") -> Dict[str, dict]:
        """
        Build the avatar info dict.
        - Two-person story: the first avatar uses expanded_info (including shared events), the second uses normal info
        - Single-person story: uses expanded_info
        """
        non_null = [a for a in actors if a is not None]
        avatar_infos: Dict[str, dict] = {}
        
        if len(non_null) >= 2:
            avatar_infos[non_null[0].name] = non_null[0].get_expanded_info(other_avatar=non_null[1], detailed=True)
            avatar_infos[non_null[1].name] = non_null[1].get_info(detailed=True)
        elif non_null:
            avatar_infos[non_null[0].name] = non_null[0].get_expanded_info(detailed=True)
        
        return avatar_infos

    @staticmethod
    def _build_template_data(event: str, res: str, avatar_infos: Dict[str, dict], prompt: str, *actors: "Avatar") -> dict:
        """Build the data dict needed for template rendering."""
        
        # Default empty relation list
        avatar_name_1 = ""
        avatar_name_2 = ""
        
        world_info = actors[0].world.static_info
        
        # If there are two valid avatars, compute possible relations
        non_null = [a for a in actors if a is not None]
        if len(non_null) >= 2:
            avatar_name_1 = non_null[0].name
            avatar_name_2 = non_null[1].name

        return {
            "world_info": world_info,
            "world_lore": actors[0].world.world_lore.text if actors else "",
            "avatar_infos": avatar_infos,
            "avatar_name_1": avatar_name_1,
            "avatar_name_2": avatar_name_2,
            "event": event,
            "res": res,
            "style": get_random_story_style(),
            "story_prompt": prompt,
        }

    @staticmethod
    def _make_fallback_story(event: str, res: str, style: str) -> str:
        """Generate fallback text."""
        # Style is no longer shown, to avoid breaking immersion
        return f"{event.rstrip('.')}. {res.rstrip('.')}."

    @staticmethod
    async def tell_story(event: str, res: str, *actors: "Avatar", prompt: str = "", allow_relation_changes: bool = False) -> str:
        """
        Generate a short story (async version).
        The template is chosen by the allow_relation_changes param:
        - True: use story_dual.txt (two-person story template; requires at least 2 avatars)
        - False: use story_single.txt (generic story template)
        
        Args:
            event: event description
            res: result description
            *actors: participating avatars (1-2)
            prompt: optional story prompt
            allow_relation_changes:
                Historical name; currently only switches between the two-person and single-person templates,
                and does not write back avatar relations directly.
        """
        non_null = [a for a in actors if a is not None]
        
        # Historical name kept; the current semantics are only "whether to use the two-person story template".
        is_dual = allow_relation_changes and len(non_null) >= 2
        
        template_file = StoryTeller.TEMPLATE_DUAL_FILE if is_dual else StoryTeller.TEMPLATE_SINGLE_FILE
        template_path = StoryTeller._get_template_path(template_file)
        
        avatar_infos = StoryTeller._build_avatar_infos(*actors)
        infos = StoryTeller._build_template_data(event, res, avatar_infos, prompt, *actors)
        
        # The try-except block was removed so exceptions bubble up (fail fast)
        data = await call_llm_with_task_name("story_teller", template_path, infos)
        story = data.get("story", "").strip()

        if story:
            return story
        
        return StoryTeller._make_fallback_story(event, res, infos["style"])

    @staticmethod
    async def tell_gathering_story(
        gathering_info: str,
        events_text: str,
        details_text: str,
        related_avatars: list["Avatar"],
        prompt: str = ""
    ) -> str:
        """
        Generate stories for multi-avatar events such as gatherings/auctions.
        Generic interface for the story_gathering.txt template.
        
        Args:
            gathering_info: the event's setting info (e.g. location, background, rules)
            events_text: the concrete events/interaction records that happened
            details_text: detailed info (including avatar info, item info, etc.)
            related_avatars: participating avatars (mainly used to get world background info)
            prompt: extra prompt
        """
        if not related_avatars:
            return events_text

        # Use the first avatar's world info
        world_info = related_avatars[0].world.static_info
            
        infos = {
            "world_info": world_info,
            "world_lore": related_avatars[0].world.world_lore.text,
            "gathering_info": gathering_info,
            "events": events_text,
            "details": details_text,
            "style": get_random_story_style(),
            "story_prompt": prompt
        }
        
        # Raise the token limit to support long stories
        template_path = StoryTeller._get_template_path(StoryTeller.TEMPLATE_GATHERING_FILE)
        data = await call_llm_with_task_name("story_teller", template_path, infos)
        story = data.get("story", "").strip()
        
        if story:
            return story
            
        return events_text


__all__ = ["StoryTeller"]

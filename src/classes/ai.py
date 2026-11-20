"""
NPC AI classes.
This refers to the NPC decision-making mechanism.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import asyncio

from src.classes.core.world import World
from src.classes.event import Event, NULL_EVENT
from src.utils.llm import call_llm_with_task_name
from src.classes.typings import ACTION_NAME_PARAMS_PAIRS
from src.classes.actions import get_action_infos_str
from src.utils.config import CONFIG

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

class AI(ABC):
    """
    Abstract AI: uses a batch interface throughout.
    """

    @abstractmethod
    async def _decide(self, world: World, avatars_to_decide: list[Avatar]) -> dict[Avatar, tuple]:
        pass

    async def decide(self, world: World, avatars_to_decide: list[Avatar]) -> dict[Avatar, tuple[ACTION_NAME_PARAMS_PAIRS, str, str, Event]]:
        """
        Decide what to do and generate the corresponding events.
        The underlying LLM calls are already hooked into the global task pool, so all tasks can simply run concurrently here.
        """
        # Call the concrete decision logic
        results = await self._decide(world, avatars_to_decide)

        # Fill in Event fields
        for avatar in list(results.keys()):
            action_name_params_pairs, avatar_thinking, short_term_objective = results[avatar]  # type: ignore
            # Don't generate start events during the decision phase; the commit phase triggers them uniformly
            results[avatar] = (action_name_params_pairs, avatar_thinking, short_term_objective, NULL_EVENT)

        return results

class LLMAI(AI):
    """
    LLM AI
    """

    async def _decide(self, world: World, avatars_to_decide: list[Avatar]) -> dict[Avatar, tuple[ACTION_NAME_PARAMS_PAIRS, str, str]]:
        """
        Async decision logic: use the LLM to decide which action to perform and with what params
        """
        
        async def decide_one(avatar: Avatar):
            general_action_infos = get_action_infos_str(avatar)
            # Get world info based on the avatar's known regions (including distance computation)
            world_info = world.get_info(avatar=avatar, detailed=True)
            
            # Include other avatars within the avatar's observation range in the prompt
            observed = world.get_observable_avatars(avatar)
            avatar_info = avatar.get_expanded_info(co_region_avatars=observed, detailed=True)
            from src.classes.core.avatar.info_presenter import get_avatar_ai_context
            avatar_ai_context = get_avatar_ai_context(avatar, co_region_avatars=observed)
            
            info = {
                "avatar_name": avatar.name,
                "avatar_info": avatar_info,
                "avatar_ai_context": avatar_ai_context,
                "world_info": world_info,
                "world_lore": world.world_lore.text,
                "general_action_infos": general_action_infos,
                "player_command": "",
            }
            template_path = CONFIG.paths.templates / "ai.txt"
            res = await call_llm_with_task_name("action_decision", template_path, info)
            return avatar, res

        # Run all tasks concurrently
        tasks = [decide_one(avatar) for avatar in avatars_to_decide]
        results_list = await asyncio.gather(*tasks)
        
        results: dict[Avatar, tuple[ACTION_NAME_PARAMS_PAIRS, str, str]] = {}
        for avatar, res in results_list:
            if not res or avatar.name not in res:
                continue
                
            r = res[avatar.name]
            # Only action_name_params_pairs is accepted; a single action_name/action_params is no longer supported
            raw_pairs = r.get("action_name_params_pairs", [])
            pairs: ACTION_NAME_PARAMS_PAIRS = []
            
            for p in raw_pairs:
                if isinstance(p, list) and len(p) == 2:
                    # The LLM may return null for params; convert it to an empty dict.
                    pairs.append((p[0], p[1] or {}))
                elif isinstance(p, dict) and "action_name" in p and "action_params" in p:
                    pairs.append((p["action_name"], p["action_params"] or {}))
                else:
                    continue
            
            # At least one
            if not pairs:
                continue # Skip if no valid actions found

            avatar_thinking = r.get("avatar_thinking", r.get("thinking", ""))
            short_term_objective = r.get("short_term_objective", "")
            
            # Update emotion
            from src.classes.emotions import EmotionType
            raw_emotion = r.get("current_emotion", "emotion_calm")
            try:
                # Try to get the enum by value
                avatar.emotion = EmotionType(raw_emotion)
            except ValueError:
                avatar.emotion = EmotionType.CALM
                
            results[avatar] = (pairs, avatar_thinking, short_term_objective)
            
        return results

llm_ai = LLMAI()

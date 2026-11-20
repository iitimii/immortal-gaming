from __future__ import annotations

from src.i18n import t
from src.classes.action import InstantAction
from src.classes.action.param_options import ParamOptionSource
from src.classes.event import Event
from src.systems.battle import get_escape_success_rate
from src.classes.action.event_helper import EventHelper
from src.utils.resolution import resolve_query


class Escape(InstantAction):
    """
    Escape: try to break away from the other (with a success rate).
    Success: preempt and enter MoveAwayFromAvatar (6 months).
    Failure: preempt and enter Attack.
    """
    
    # i18n IDs
    ACTION_NAME_ID = "escape_action_name"
    DESC_ID = "escape_description"
    REQUIREMENTS_ID = "escape_requirements"
    
    # Constants that need no translation
    EMOJI = "💨"
    PARAMS = {"avatar_name": "AvatarName"}
    PARAM_OPTION_SOURCES = {"avatar_name": ParamOptionSource.OBSERVABLE_AVATAR_NAME}

    def _find_avatar_by_name(self, name: str) -> "Avatar|None":
        """
        Find an avatar by name or ID; return None if not found.
        """
        from src.classes.core.avatar import Avatar

        return resolve_query(name, self.world, expected_types=[Avatar]).obj

    def _preempt_avatar(self, avatar: "Avatar") -> None:
        avatar.clear_plans()
        avatar.current_action = None

    def _execute(self, avatar_name: str) -> None:
        target = self._find_avatar_by_name(avatar_name)
        if target is None:
            return
        escape_rate = float(get_escape_success_rate(target, self.avatar))
        import random as _r

        success = _r.random() < escape_rate
        result_text = t("succeeded") if success else t("failed")
        content = t("{avatar} attempted to escape from {target}: {result}",
                   avatar=self.avatar.name, target=target.name, result=result_text)
        result_event = Event(self.world.month_stamp, content, related_avatars=[self.avatar.id, target.id])
        EventHelper.push_pair(result_event, initiator=self.avatar, target=target, to_sidebar_once=True)
        if success:
            self._preempt_avatar(self.avatar)
            self.avatar.load_decide_result_chain([("MoveAwayFromAvatar", {"avatar_name": avatar_name})], self.avatar.thinking, "")
            self.avatar.commit_next_plan()
        else:
            self._preempt_avatar(self.avatar)
            self.avatar.load_decide_result_chain([("Attack", {"avatar_name": avatar_name})], self.avatar.thinking, "")
            self.avatar.commit_next_plan()

    def can_start(self, avatar_name: str) -> tuple[bool, str]:
        return True, ""

    def start(self, avatar_name: str) -> Event:
        target = self._find_avatar_by_name(avatar_name)
        target_name = target.name if target is not None else avatar_name
        rel_ids = [self.avatar.id]
        if target is not None:
            rel_ids.append(target.id)
        content = t("{avatar} attempts to escape from {target}", 
                   avatar=self.avatar.name, target=target_name)
        return Event(self.world.month_stamp, content, related_avatars=rel_ids)

    # InstantAction already completes in step

    async def finish(self, avatar_name: str) -> list[Event]:
        return []



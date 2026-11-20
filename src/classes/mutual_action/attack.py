from __future__ import annotations

from .mutual_action import PressureAction
from src.i18n import t
from src.classes.action.cooldown import cooldown_action
from src.classes.relation.relation_delta_service import RelationDeltaService
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


@cooldown_action
class MutualAttack(PressureAction):
    """Attack another NPC."""
    
    # i18n IDs
    ACTION_NAME_ID = "mutual_attack_action_name"
    DESC_ID = "mutual_attack_description"
    REQUIREMENTS_ID = "mutual_attack_requirements"
    
    # Constants that need no translation
    EMOJI = "⚔️"
    PARAMS = {"target_avatar": "AvatarName"}
    RESPONSE_ACTIONS = ["Escape", "Attack"]
    # Attack cooldown: avoid repeated attacks in the same month
    ACTION_CD_MONTHS: int = 3
    # Attack is a major event (long-term memory)
    IS_MAJOR: bool = True

    def _can_start(self, target: "Avatar") -> tuple[bool, str]:
        """Attack has no extra start conditions."""
        from src.classes.observe import is_within_observation
        if not is_within_observation(self.avatar, target):
            return False, t("Target not within interaction range")
        return True, ""

    def _settle_response(self, target_avatar: "Avatar", response_name: str) -> None:
        fb = str(response_name).strip()
        a_to_b, b_to_a = RelationDeltaService.get_fixed_delta("attack", "started")
        RelationDeltaService.apply_bidirectional_delta(self.avatar, target_avatar, a_to_b, b_to_a)
        
        # No new event is produced here; only the target's behavior changes
        # The target's behavior change produces new events via _set_target_immediate_action -> commit_next_plan
        # and commit_next_plan handles event dispatch internally (in theory)
        # But let's look at the base class's _set_target_immediate_action implementation
        
        if fb == "Escape":
            params = {"avatar_name": self.avatar.name}
            self._set_target_immediate_action(target_avatar, fb, params, push_start_event=False)
        elif fb == "Attack":
            params = {"avatar_name": self.avatar.name}
            self._set_target_immediate_action(target_avatar, fb, params, push_start_event=False)

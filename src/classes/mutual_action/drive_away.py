from __future__ import annotations

from .mutual_action import PressureAction
from src.i18n import t
from src.classes.action.cooldown import cooldown_action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


@cooldown_action
class DriveAway(PressureAction):
    """Drive away: try to make the other leave the current region."""
    
    # i18n IDs
    ACTION_NAME_ID = "drive_away_action_name"
    DESC_ID = "drive_away_description"
    REQUIREMENTS_ID = "drive_away_requirements"
    
    # Constants that need no translation
    EMOJI = "😤"
    PARAMS = {"target_avatar": "AvatarName"}
    RESPONSE_ACTIONS = ["MoveAwayFromRegion", "Attack"]
    # Drive-away cooldown: avoid repeated drive-away spam
    ACTION_CD_MONTHS: int = 3

    def _can_start(self, target: "Avatar") -> tuple[bool, str]:
        """Drive away has no extra start conditions."""
        # Must be in a valid region to drive away (the target region for MoveAwayFromRegion must be specified)
        if self.avatar.tile.region is None:
            return False, t("Cannot drive away in wilderness")
            
        from src.classes.observe import is_within_observation
        if not is_within_observation(self.avatar, target):
            return False, t("Target not within interaction range")
        return True, ""

    def _settle_response(self, target_avatar: "Avatar", response_name: str) -> None:
        fb = str(response_name).strip()
        if fb == "MoveAwayFromRegion":
            # Choosing to leave when driven away: always succeeds, no probability involved
            params = {"region": self.avatar.tile.location_name}
            self._set_target_immediate_action(target_avatar, fb, params, push_start_event=True)
        elif fb == "Attack":
            params = {"avatar_name": self.avatar.name}
            self._set_target_immediate_action(target_avatar, fb, params, push_start_event=False)



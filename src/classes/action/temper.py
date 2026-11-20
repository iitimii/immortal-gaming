from __future__ import annotations

from src.i18n import t
from src.classes.action import TimedAction
from src.classes.event import Event

class Temper(TimedAction):
    """
    Temper action, a cultivation method exclusive to the martial path.
    Doesn't depend on qi; spends time tempering the body.
    """
    
    ACTION_NAME_ID = "temper_action_name"
    DESC_ID = "temper_description"
    REQUIREMENTS_ID = "temper_requirements"
    
    EMOJI = "💪"
    PARAMS = {}

    duration_months = 10
    
    # Base exp
    BASE_EXP = 480

    def can_possibly_start(self) -> bool:
        legal = self.avatar.effects.get("legal_actions", [])
        if legal and "Temper" not in legal:
            return False
        return True

    def _execute(self) -> None:
        if self.avatar.cultivation_progress.is_in_bottleneck():
            return
            
        # Base exp
        exp = self.BASE_EXP
        
        # Apply the extra temper exp multiplier (from techniques/sects etc.)
        # extra_temper_exp_multiplier: 0.1 means +10%
        multiplier = float(self.avatar.effects.get("extra_temper_exp_multiplier", 0.0) or 0.0)
        
        if multiplier != 0:
            exp = int(exp * (1 + multiplier))
            
        # Ensure at least 1 exp
        exp = max(1, exp)
            
        self.avatar.cultivation_progress.add_exp(exp)

    def can_start(self) -> tuple[bool, str]:
        if not self.avatar.cultivation_progress.can_cultivate():
            return False, t("Cultivation has reached bottleneck, cannot continue cultivating")
            
        legal = self.avatar.effects.get("legal_actions", [])
        if legal and "Temper" not in legal:
            return False, t("Your orthodoxy does not support Body Tempering.")
        
        return True, ""

    def start(self) -> Event:
        reduction = float(self.avatar.effects.get("temper_duration_reduction", 0.0))
        reduction = max(0.0, min(0.9, reduction))
        
        base_duration = self.__class__.duration_months
        actual_duration = max(1, round(base_duration * (1.0 - reduction)))
        self.duration_months = actual_duration
        
        content = t("{avatar} begins tempering body strength", avatar=self.avatar.name)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])

    async def finish(self) -> list[Event]:
        return []

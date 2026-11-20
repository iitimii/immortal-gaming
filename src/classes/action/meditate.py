from __future__ import annotations

import random
from src.i18n import t
from src.classes.action import TimedAction
from src.classes.event import Event
from src.systems.cultivation import REALM_RANK

class Meditate(TimedAction):
    """
    Meditate (Buddhist cultivation): independent of qi; calms the mind through seated meditation, with a chance of epiphany granting a lot of cultivation.
    """
    
    # i18n IDs
    ACTION_NAME_ID = "meditate_action_name"
    DESC_ID = "meditate_description"
    REQUIREMENTS_ID = "meditate_requirements"
    
    # Constants that need no translation
    EMOJI = "🧘"
    PARAMS = {}

    duration_months = 3
    
    # Exp constants
    BASE_EXP = 10       # Normal meditation exp (very little)
    EPIPHANY_EXP = 1500 # Epiphany exp (a lot; expected value about 50/month)
    BASE_PROB = 0.1     # Base epiphany probability 10%

    def can_possibly_start(self) -> bool:
        legal = self.avatar.effects.get("legal_actions", [])
        if "Meditate" not in legal:
            return False
        return True

    def _execute(self) -> None:
        """
        Meditation execution logic
        """
        # Bottleneck check
        if self.avatar.cultivation_progress.is_in_bottleneck():
            return

        # Compute the realm bonus (1, 2, 3, 4)
        realm = self.avatar.cultivation_progress.realm
        realm_multiplier = REALM_RANK.get(realm, 0) + 1
        
        # Compute the epiphany probability
        prob = self.BASE_PROB + float(self.avatar.effects.get("extra_meditate_prob", 0.0))
        
        # Determine whether an epiphany occurs
        is_epiphany = random.random() < prob
        
        base_exp = self.EPIPHANY_EXP if is_epiphany else self.BASE_EXP
        
        # Compute the final exp
        exp = int(base_exp * realm_multiplier)
        
        # Extra bonus
        multiplier = float(self.avatar.effects.get("extra_meditate_exp_multiplier", 0.0))
        if multiplier > 0:
            exp = int(exp * (1 + multiplier))
            
        self.avatar.cultivation_progress.add_exp(exp)
        
        # Record this result for the event
        self._last_is_epiphany = is_epiphany
        self._last_exp = exp

    def can_start(self) -> tuple[bool, str]:
        # 1. Bottleneck check
        if not self.avatar.cultivation_progress.can_cultivate():
            return False, t("Cultivation has reached bottleneck, cannot continue cultivating")
        
        # 2. Permission check (must have the Meditate permission)
        legal = self.avatar.effects.get("legal_actions", [])
        if "Meditate" not in legal:
             return False, t("Your orthodoxy does not support Zen Meditation.")
             
        return True, ""

    def start(self) -> Event:
        # Record the start time
        content = t("{avatar} begins Zen Meditation.", avatar=self.avatar.name)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])

    async def finish(self) -> list[Event]:
        # On finish, generate different logs depending on whether an epiphany occurred
        if getattr(self, '_last_is_epiphany', False):
            content = t("{avatar} had an epiphany during meditation! Cultivation increased significantly (+{exp}).", 
                       avatar=self.avatar.name, exp=getattr(self, '_last_exp', 0))
        else:
            content = t("{avatar} completed meditation with a peaceful mind.", 
                       avatar=self.avatar.name)
            
        return [Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])]

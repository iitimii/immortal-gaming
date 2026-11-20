from __future__ import annotations

from src.i18n import t
from src.classes.action import TimedAction
from src.classes.event import Event
from src.classes.root import get_essence_types_for_root
from src.classes.environment.region import CultivateRegion
from src.classes.environment.sect_region import SectRegion
from src.systems.formation import get_region_formation_effect_value


class Respire(TimedAction):
    """
    Respire action; increases cultivation progress.
    """
    
    # i18n IDs
    ACTION_NAME_ID = "respire_action_name"
    DESC_ID = "respire_description"
    REQUIREMENTS_ID = "respire_requirements"
    
    # Constants that need no translation
    EMOJI = "🌀"
    PARAMS = {}

    duration_months = 10
    
    # Exp constants
    BASE_EXP_PER_DENSITY = 100   # Base exp per point of qi density in a cultivation region
    BASE_EXP_LOW_EFFICIENCY = 50 # Base exp with no matching qi or outside a cultivation region

    def can_possibly_start(self) -> bool:
        legal = self.avatar.effects.get("legal_actions", [])
        if legal and "Respire" not in legal:
            return False
        return True

    def _execute(self) -> None:
        """
        Respire
        The exp gained depends on the region type and qi matching:
        - Cultivation region + matching qi: exp = BASE_EXP_PER_DENSITY * density
        - Cultivation region without matching qi, or a non-cultivation region: exp = BASE_EXP_LOW_EFFICIENCY
        """
        if self.avatar.cultivation_progress.is_in_bottleneck():
            return
            
        exp = self._calculate_base_exp()
        
        # Apply extra respire exp (from techniques/sects/spiritual roots etc.)
        extra_exp = int(self.avatar.effects.get("extra_respire_exp", 0) or 0)
        if extra_exp:
            exp += extra_exp

        # Apply the extra respire exp multiplier
        multiplier = float(self.avatar.effects.get("extra_respire_exp_multiplier", 0.0) or 0.0)
        multiplier += float(get_region_formation_effect_value(self.avatar, "extra_respire_exp_multiplier", 0.0) or 0.0)
        if multiplier > 0:
            exp = int(exp * (1 + multiplier))
            
        self.avatar.cultivation_progress.add_exp(exp)

    def _get_matched_essence_density(self) -> int:
        """
        Get the qi density of the current region matching the avatar's spiritual root.
        - Cave dwellings/ruins (CultivateRegion): computed from the single qi type as before;
        - Sect headquarters (SectRegion): a cultivation environment for members only, with an equivalent density of 5 for all elements;
        - Other regions: returns 0.
        """
        region = self.avatar.tile.region
        essence_types = get_essence_types_for_root(self.avatar.root)

        # Cave dwelling / ruin
        if isinstance(region, CultivateRegion):
            return max((region.essence.get_density(et) for et in essence_types), default=0)

        # Sect headquarters: only members enjoy the fallback "all five elements at 5" cultivation environment
        if isinstance(region, SectRegion):
            sect = getattr(self.avatar, "sect", None)
            if sect is None or sect.id != region.sect_id:
                return 0
            return max((region.essence.get_density(et) for et in essence_types), default=0)

        return 0

    def _calculate_base_exp(self) -> int:
        """
        Compute base exp from the region type and qi matching
        """
        density = self._get_matched_essence_density()
        if density > 0:
            return self.BASE_EXP_PER_DENSITY * density
        return self.BASE_EXP_LOW_EFFICIENCY

    def can_start(self) -> tuple[bool, str]:
        # Bottleneck check
        if not self.avatar.cultivation_progress.can_cultivate():
            return False, t("Cultivation has reached bottleneck, cannot continue cultivating")
            
        # Permission check (Dao or rogue cultivator)
        # If legal_actions is non-empty and doesn't include "Respire", it's forbidden (another orthodoxy, e.g. Buddhism/Confucianism)
        legal = self.avatar.effects.get("legal_actions", [])
        if legal and "Respire" not in legal:
            return False, t("Your orthodoxy does not support Qi Respiration.")
        
        region = self.avatar.tile.region

        # If in a cultivation region, check cave dwelling ownership
        if isinstance(region, CultivateRegion):
            if region.host_avatar is not None and region.host_avatar != self.avatar:
                return False, t("This cave dwelling has been occupied by {name}, cannot respire",
                               name=region.host_avatar.name)

        # Sect headquarters: only members may respire here
        if isinstance(region, SectRegion):
            sect = getattr(self.avatar, "sect", None)
            if sect is None or sect.id != region.sect_id:
                return False, t("respire_sect_hq_members_only")
        
        return True, ""

    def start(self) -> Event:
        # Compute the respire duration reduction
        reduction = float(self.avatar.effects.get("respire_duration_reduction", 0.0))
        reduction = max(0.0, min(0.9, reduction))
        
        # Dynamically set the actual duration of this respire
        base_duration = self.__class__.duration_months
        actual_duration = max(1, round(base_duration * (1.0 - reduction)))
        self.duration_months = actual_duration
        
        matched_density = self._get_matched_essence_density()
        region = self.avatar.tile.region

        # Respiring at one's own sect headquarters: use the dedicated efficiency text, conveying "a fallback, but not as good as a secret realm"
        if isinstance(region, SectRegion):
            sect = getattr(self.avatar, "sect", None)
            if sect is not None and sect.id == region.sect_id and matched_density > 0:
                efficiency = t("respire_efficiency_sect_hq")
            elif matched_density > 0:
                # In theory non-members can't start respiring at the headquarters, but fall back to the normal excellent-progress text
                efficiency = t("excellent progress")
            else:
                efficiency = t("slow progress (sparse essence)")
        else:
            if matched_density > 0:
                efficiency = t("excellent progress")
            elif isinstance(region, CultivateRegion) and getattr(region, "essence_density", 0) > 0:
                efficiency = t("slow progress (essence mismatch)")
            else:
                efficiency = t("slow progress (sparse essence)")

        content = t("{avatar} begins respiring at {location}, {efficiency}",
                   avatar=self.avatar.name, location=self.avatar.tile.location_name, efficiency=efficiency)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])

    async def finish(self) -> list[Event]:
        return []

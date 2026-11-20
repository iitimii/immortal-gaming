from enum import Enum
from functools import total_ordering

from src.classes.color import Color

@total_ordering
class Realm(Enum):
    Qi_Refinement = "QI_REFINEMENT"
    Foundation_Establishment = "FOUNDATION_ESTABLISHMENT"
    Core_Formation = "CORE_FORMATION"
    Nascent_Soul = "NASCENT_SOUL"

    def __str__(self) -> str:
        """Return the translated realm name."""
        from src.i18n import t
        return t(realm_msg_ids.get(self, self.value))

    @staticmethod
    def from_str(s: str) -> "Realm":
        s = str(s).strip().replace(" ", "_").upper()
        # Mapping to accept several input formats
        mapping = {
            "QI_REFINEMENT": "QI_REFINEMENT", "QI REFINEMENT": "QI_REFINEMENT",
            "FOUNDATION_ESTABLISHMENT": "FOUNDATION_ESTABLISHMENT", "FOUNDATION ESTABLISHMENT": "FOUNDATION_ESTABLISHMENT",
            "CORE_FORMATION": "CORE_FORMATION", "CORE FORMATION": "CORE_FORMATION",
            "NASCENT_SOUL": "NASCENT_SOUL", "NASCENT SOUL": "NASCENT_SOUL"
        }
        realm_id = mapping.get(s, "QI_REFINEMENT")
        return Realm(realm_id)

    @property
    def color_rgb(self) -> tuple[int, int, int]:
        """Return the RGB color for the realm."""
        color_map = {
            Realm.Qi_Refinement: Color.COMMON_WHITE,
            Realm.Foundation_Establishment: Color.UNCOMMON_GREEN,
            Realm.Core_Formation: Color.EPIC_PURPLE,
            Realm.Nascent_Soul: Color.LEGENDARY_GOLD,
        }
        return color_map.get(self, Color.COMMON_WHITE)

    @classmethod
    def from_id(cls, realm_id: int) -> "Realm":
        index = realm_id - 1
        if index < 0 or index >= len(REALM_ORDER):
            raise ValueError(f"Unknown realm_id: {realm_id}")
        return REALM_ORDER[index]

    def __lt__(self, other):
        if not isinstance(other, Realm):
            return NotImplemented
        return REALM_RANK[self] < REALM_RANK[other]

    def __le__(self, other):
        if not isinstance(other, Realm):
            return NotImplemented
        return REALM_RANK[self] <= REALM_RANK[other]

    def __gt__(self, other):
        if not isinstance(other, Realm):
            return NotImplemented
        return REALM_RANK[self] > REALM_RANK[other]

    def __ge__(self, other):
        if not isinstance(other, Realm):
            return NotImplemented
        return REALM_RANK[self] >= REALM_RANK[other]
        

@total_ordering
class Stage(Enum):
    Early_Stage = "EARLY_STAGE"
    Middle_Stage = "MIDDLE_STAGE"
    Late_Stage = "LATE_STAGE"

    def __str__(self) -> str:
        """Return the translated stage name."""
        from src.i18n import t
        return t(stage_msg_ids.get(self, self.value))

    @staticmethod
    def from_str(s: str) -> "Stage":
        s = str(s).strip().replace(" ", "_").upper()
        mapping = {
            "EARLY_STAGE": "EARLY_STAGE", "EARLY STAGE": "EARLY_STAGE",
            "MIDDLE_STAGE": "MIDDLE_STAGE", "MIDDLE STAGE": "MIDDLE_STAGE",
            "LATE_STAGE": "LATE_STAGE", "LATE STAGE": "LATE_STAGE"
        }
        stage_id = mapping.get(s, "EARLY_STAGE")
        return Stage(stage_id)

    def __lt__(self, other):
        if not isinstance(other, Stage):
            return NotImplemented
        return STAGE_RANK[self] < STAGE_RANK[other]

    def __le__(self, other):
        if not isinstance(other, Stage):
            return NotImplemented
        return STAGE_RANK[self] <= STAGE_RANK[other]

    def __gt__(self, other):
        if not isinstance(other, Stage):
            return NotImplemented
        return STAGE_RANK[self] > STAGE_RANK[other]

    def __ge__(self, other):
        if not isinstance(other, Stage):
            return NotImplemented
        return STAGE_RANK[self] >= STAGE_RANK[other]

# msgid mapping
realm_msg_ids = {
    Realm.Qi_Refinement: "qi_refinement",
    Realm.Foundation_Establishment: "foundation_establishment",
    Realm.Core_Formation: "core_formation",
    Realm.Nascent_Soul: "nascent_soul",
}

stage_msg_ids = {
    Stage.Early_Stage: "early_stage",
    Stage.Middle_Stage: "middle_stage",
    Stage.Late_Stage: "late_stage",
}

# Single definition of realm order and rank
REALM_ORDER: tuple[Realm, ...] = (
    Realm.Qi_Refinement,
    Realm.Foundation_Establishment,
    Realm.Core_Formation,
    Realm.Nascent_Soul,
)
REALM_RANK: dict[Realm, int] = {realm: idx for idx, realm in enumerate(REALM_ORDER)}

# Single definition of stage order and rank
STAGE_ORDER: tuple[Stage, ...] = (
    Stage.Early_Stage,
    Stage.Middle_Stage,
    Stage.Late_Stage,
)
STAGE_RANK: dict[Stage, int] = {stage: idx for idx, stage in enumerate(STAGE_ORDER)}

LEVELS_PER_REALM = 30
LEVELS_PER_STAGE = 10

REALM_TO_MOVE_STEP = {
    Realm.Qi_Refinement: 2,
    Realm.Foundation_Establishment: 3,
    Realm.Core_Formation: 4,
    Realm.Nascent_Soul: 5,
}

class CultivationProgress:
    """
    Cultivation progress (level, realm and experience).
    There are currently four major realms, each split into Early, Middle and Late stages of 10 levels each,
    so each realm spans 30 levels. Once a realm's levels are maxed out, a breakthrough is required to
    enter the next realm and keep leveling:
    Qi Refinement: Early (1-10), Middle (11-20), Late (21-30), breakthrough (31)
    Foundation Establishment: Early (31-40), Middle (41-50), Late (51-60), breakthrough (61)
    Core Formation: Early (61-70), Middle (71-80), Late (81-90), breakthrough (91)
    Nascent Soul: Early (91-100), Middle (101-110), Late (111-120), breakthrough (121)
    """

    def __init__(self, level: int, exp: int = 0):
        self.level = level
        self.exp = exp
        self.realm = self.get_realm(level)
        self.stage = self.get_stage(level)

    def get_realm(self, level: int) -> Realm:
        """Get the realm (derived arithmetically, no lookup table)."""
        if level <= 0:
            return Realm.Qi_Refinement
        realm_index = (level - 1) // LEVELS_PER_REALM  # 0-based index
        return REALM_ORDER[min(realm_index, len(REALM_ORDER) - 1)]

    def get_stage(self, level: int) -> Stage:
        """Get the stage (derived arithmetically: 1-10 Early, 11-20 Middle, 21-30 Late)."""
        if level <= 0:
            return Stage.Early_Stage
        stage_index = ((level - 1) % LEVELS_PER_REALM) // LEVELS_PER_STAGE
        return STAGE_ORDER[min(stage_index, len(STAGE_ORDER) - 1)]

    def get_move_step(self) -> int:
        """
        Distance that can be moved per month:
        Qi Refinement: 2
        Foundation Establishment: 3
        Core Formation: 4
        Nascent Soul: 5
        """
        return REALM_TO_MOVE_STEP[self.realm]

    def get_detailed_info(self) -> str:
        from src.i18n import t
        can_break_through = self.can_break_through()
        can_break_through_str = t("Needs breakthrough") if can_break_through else t("Not at bottleneck, no breakthrough needed")
        return t("{realm} {stage} (Level {level}) {status}", 
                realm=str(self.realm), stage=str(self.stage), 
                level=self.level, status=can_break_through_str)

    def get_info(self) -> str:
        return f"{self.realm} {self.stage}"

    def get_exp_required(self) -> int:
        """
        Compute the experience required to reach the next level.
        Uses simple arithmetic: base_exp + (level - 1) * increment + realm_bonus

        Returns:
            Required experience
        """
        next_level = self.level + 1
        
        base_exp = 100  # Base experience
        increment = 50   # +50 experience per level
        
        # Base experience calculation
        exp_required = base_exp + (next_level - 1) * increment
        
        # Realm bonus: based on the realm next_level falls in (derived arithmetically)
        realm_index = (max(1, next_level) - 1) // LEVELS_PER_REALM
        realm_bonus = realm_index * 1000
        
        return exp_required + realm_bonus

    def get_exp_progress(self) -> tuple[int, int]:
        """
        Get the current experience progress.

        Returns:
            (current experience, experience required to level up)
        """
        required_exp = self.get_exp_required()
        return self.exp, required_exp

    def add_exp(self, exp_amount: int) -> bool:
        """
        Add experience.

        Args:
            exp_amount: Amount of experience to add

        Returns:
            True if the avatar leveled up
        """
        self.exp += exp_amount

        leveled_up = False
        # Supports multiple level-ups, but stops at bottlenecks (30/60/90...) awaiting breakthrough
        while True:
            # Bottleneck: level > 0 and level % LEVELS_PER_REALM == 0
            if self.is_in_bottleneck():
                break
            if not self.is_level_up():
                break
            required_exp = self.get_exp_required()
            self.exp -= required_exp
            self.level += 1
            self.realm = self.get_realm(self.level)
            self.stage = self.get_stage(self.level)
            leveled_up = True
            if self.is_in_bottleneck():
                break

        return leveled_up

    def break_through(self):
        """
        Break through to the next realm.
        """
        self.level += 1
        self.realm = self.get_realm(self.level)
        self.stage = self.get_stage(self.level)

    def is_in_bottleneck(self) -> bool:
        """
        Whether the avatar is at a bottleneck.
        True at level 30, 60, 90... of each major realm (level > 0 and level % LEVELS_PER_REALM == 0).
        """
        return self.level > 0 and (self.level % LEVELS_PER_REALM == 0)

    def can_break_through(self) -> bool:
        """
        Check whether a breakthrough is possible.
        """
        # Dynamically detect the cap: no breakthrough at the highest level of the highest realm
        max_level = len(REALM_ORDER) * LEVELS_PER_REALM
        if self.level >= max_level:
            return False
        return self.is_in_bottleneck()

    def can_cultivate(self) -> bool:
        """
        Check whether cultivation is possible.
        If a breakthrough is due, the level is capped and cultivation is blocked until the breakthrough.
        """
        return not self.is_in_bottleneck()

    def is_level_up(self) -> bool:
        """
        Check whether the next level can be reached.
        """
        exp_required = self.get_exp_required()
        return self.exp >= exp_required

    def __str__(self) -> str:
        from src.i18n import t
        bottleneck_status = t("Yes") if self.is_in_bottleneck() else t("No")
        return t("{realm} {stage} (Level {level}). At bottleneck: {status}",
                realm=str(self.realm), stage=str(self.stage),
                level=self.level, status=bottleneck_status)

    def get_breakthrough_success_rate(self) -> float:
        return breakthrough_success_rate_by_realm[self.realm]
    
    def get_breakthrough_fail_reduce_lifespan(self) -> int:
        return breakthrough_fail_reduce_lifespan_by_realm[self.realm]

    def get_realm_effects(self) -> dict[str, int]:
        return {
            "extra_max_lifespan": realm_max_lifespan_effect_by_realm[self.realm]
        }
    
    def to_dict(self) -> dict:
        """Convert to a serializable dict."""
        return {
            "level": self.level,
            "exp": self.exp,
            "realm": self.realm.name,  # Store the enum name
            "stage": self.stage.name
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CultivationProgress":
        """Rebuild CultivationProgress from a dict."""
        return cls(level=data["level"], exp=data["exp"])



breakthrough_success_rate_by_realm = {
    Realm.Qi_Refinement: 0.8, # Qi Refinement, 80%
    Realm.Foundation_Establishment: 0.6, # Foundation Establishment, 60%
    Realm.Core_Formation: 0.4, # Core Formation, 40%
    Realm.Nascent_Soul: 0.2, # Nascent Soul, 20%
}

breakthrough_fail_reduce_lifespan_by_realm = {
    Realm.Qi_Refinement: 5,
    Realm.Foundation_Establishment: 10,
    Realm.Core_Formation: 15,
    Realm.Nascent_Soul: 20,
}

realm_max_lifespan_effect_by_realm = {
    Realm.Qi_Refinement: 0,
    Realm.Foundation_Establishment: 50,
    Realm.Core_Formation: 100,
    Realm.Nascent_Soul: 400,
}

"""
Avatar core class

Slimmed-down Avatar class; full functionality is composed via mixins.
"""
import random
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.sect_ranks import SectRank
    from src.classes.environment.region import CultivateRegion
    from src.classes.core.orthodoxy import Orthodoxy

from src.systems.time import MonthStamp
from src.classes.core.world import World
from src.sim.save.avatar_save_mixin import AvatarSaveMixin
from src.sim.load.avatar_load_mixin import AvatarLoadMixin
from src.classes.environment.tile import Tile
from src.classes.environment.region import Region
from src.systems.cultivation import CultivationProgress
from src.classes.root import Root
from src.classes.technique import Technique, get_technique_by_sect
from src.classes.age import Age
from src.classes.event import Event
from src.classes.action_runtime import ActionPlan, ActionInstance
from src.classes.alignment import Alignment
from src.classes.persona import Persona, get_random_compatible_personas
from src.classes.goldfinger import Goldfinger
from src.classes.race import Race, get_race
from src.classes.material import Material
from src.classes.items.weapon import Weapon
from src.classes.items.auxiliary import Auxiliary
from src.classes.items.magic_stone import MagicStone
from src.classes.hp import HP, HP_MAX_BY_REALM
from src.classes.relation.relation import NumericRelation, Relation, RelationState
from src.classes.core.sect import Sect
from src.classes.appearance import Appearance, get_appearance_by_level, get_random_appearance
from src.classes.spirit_animal import SpiritAnimal
from src.classes.long_term_objective import LongTermObjective
from src.classes.nickname_data import Nickname
from src.classes.emotions import EmotionType
from src.classes.official_rank import OFFICIAL_NONE
from src.classes.items.elixir import ConsumedElixir, Elixir
from src.classes.avatar_metrics import AvatarMetrics
from src.classes.mortal import Mortal
from src.classes.gender import Gender
from src.classes.world_secret import AvatarWorldSecretKnowledge

# Mixin imports
from src.classes.effect import EffectsMixin
from src.classes.core.avatar.inventory_mixin import InventoryMixin
from src.classes.core.avatar.action_mixin import ActionMixin

def _get_persona_num() -> int:
    from src.utils.config import CONFIG as current_config

    return int(current_config.avatar.persona_num)


@dataclass
class Avatar(
    AvatarSaveMixin,
    AvatarLoadMixin,
    EffectsMixin,
    InventoryMixin,
    ActionMixin,
):
    """
    The NPC class.
    Holds all information about this avatar.
    """
    world: World
    name: str
    id: str
    birth_month_stamp: MonthStamp
    age: Age
    gender: Gender
    race: Race = field(default_factory=lambda: get_race("human"))
    cultivation_progress: CultivationProgress = field(default_factory=lambda: CultivationProgress(0))
    pos_x: int = 0
    pos_y: int = 0
    tile: Optional[Tile] = None

    root: Root = field(default_factory=lambda: random.choice(list(Root)))
    personas: List[Persona] = field(default=None)  # type: ignore
    goldfinger: Goldfinger | None = None
    goldfinger_state: dict = field(default_factory=dict)
    technique: Technique | None = None
    _pending_events: List[Event] = field(default_factory=list)
    current_action: Optional[ActionInstance] = None
    planned_actions: List[ActionPlan] = field(default_factory=list)
    thinking: str = ""
    short_term_objective: str = ""
    long_term_objective: Optional[LongTermObjective] = None
    magic_stone: MagicStone = field(default_factory=lambda: MagicStone(0))
    materials: dict[Material, int] = field(default_factory=dict)
    hp: HP = field(default_factory=lambda: HP(0, 0))
    relations: dict["Avatar", RelationState] = field(default_factory=dict)
    archived_relations: dict["Avatar", RelationState] = field(default_factory=dict)
    # Cached second-degree relations (computed periodically by the Simulator)
    computed_relations: dict["Avatar", Relation] = field(default_factory=dict)
    alignment: Alignment | None = None
    sect: Sect | None = None
    sect_rank: "SectRank | None" = None
    sect_contribution: int = 0
    base_appearance: Appearance = field(default_factory=get_random_appearance)
    weapon: Optional[Weapon] = None
    weapon_proficiency: float = 0.0
    auxiliary: Optional[Auxiliary] = None
    spirit_animal: Optional[SpiritAnimal] = None
    nickname: Optional[Nickname] = None
    backstory: Optional[str] = None
    fate_revelation: Optional[dict] = None
    emotion: EmotionType = EmotionType.CALM
    custom_pic_id: Optional[int] = None
    luck_base: float = 0.0
    official_rank: str = OFFICIAL_NONE
    court_reputation: int = 0
    last_governance_month: Optional[int] = None
    
    elixirs: List[ConsumedElixir] = field(default_factory=list)
    # Temporary effects: [{"source": str, "effects": dict, "start_month": int, "duration": int}]
    temporary_effects: List[dict] = field(default_factory=list)
    # Permanent effects: [{"source": str, "effects": dict}]
    persistent_effects: List[dict] = field(default_factory=list)

    is_dead: bool = False
    death_info: Optional[dict] = None

    _new_action_set_this_step: bool = False
    _action_cd_last_months: dict[str, int] = field(default_factory=dict)
    
    known_regions: set[int] = field(default_factory=set)
    world_secret_knowledge: dict[str, AvatarWorldSecretKnowledge] = field(default_factory=dict)

    # Metrics tracking (optional)
    metrics_history: List[AvatarMetrics] = field(default_factory=list)
    enable_metrics_tracking: bool = False
    max_metrics_history: int = 1200  # At most 100 years

    # The legacy event-count cache is kept as an empty shell so other call sites don't error.
    relation_interaction_states: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"count": 0, "checked_times": 0}))

    # [New] list of children
    children: List["Mortal"] = field(default_factory=list)

    # [New] birthplace region ID
    born_region_id: Optional[int] = None

    # Month stamp of reaching Qi Refinement / starting cultivation
    cultivation_start_month_stamp: Optional[MonthStamp] = None

    # [New] relation start time cache
    # Key: other Avatar ID, Value: MonthStamp (int) when the relation started
    relation_start_dates: dict[str, int] = field(default_factory=dict)

    # Owned cave dwellings (not serialized; rebuilt via load_game)
    owned_regions: List["CultivateRegion"] = field(default_factory=list, init=False)

    def occupy_region(self, region: "CultivateRegion") -> None:
        """
        Occupy a cave dwelling, handling the two-way binding and cleanup of the previous owner.
        """
        # Already mine; nothing to do
        if region.host_avatar == self:
            if region not in self.owned_regions:
                self.owned_regions.append(region)
            return

        # If there is a previous owner, have them release it first
        if region.host_avatar is not None:
            region.host_avatar.release_region(region)

        # Establish the new relation
        region.host_avatar = self
        if region not in self.owned_regions:
            self.owned_regions.append(region)

    def release_region(self, region: "CultivateRegion") -> None:
        """
        Give up ownership of a cave dwelling.
        """
        if region in self.owned_regions:
            self.owned_regions.remove(region)
        
        # Only clear it if the region's owner is really me (avoid hurting a new owner)
        if region.host_avatar == self:
            region.host_avatar = None

    def add_breakthrough_rate(self, rate: float, duration: int = 1) -> None:
        """
        Increase breakthrough success rate (temporary effect).
        """
        self.temporary_effects.append({
            "source": "play_benefit",
            "effects": {"extra_breakthrough_success_rate": rate},
            "start_month": int(self.world.month_stamp),
            "duration": duration
        })
        self.recalc_effects()

    def add_persistent_effect(self, source: str, effects: dict[str, object]) -> None:
        """
        Add a permanent effect source.
        For long-lasting displayed effects such as lifespan loss from a failed breakthrough or fate-altering destinies.
        """
        self.persistent_effects.append({
            "source": source,
            "effects": dict(effects),
        })
        self.recalc_effects()

    @property
    def appearance(self) -> Appearance:
        """
        Current appearance = base appearance + extra_appearance.
        avatar.appearance is kept as the public accessor so upper-layer code doesn't need to change.
        """
        base = self.base_appearance
        if not isinstance(base, Appearance):
            return base

        raw_extra = self.effects.get("extra_appearance", 0)
        try:
            extra_level = int(raw_extra)
        except (TypeError, ValueError):
            extra_level = 0

        return get_appearance_by_level(base.level + extra_level)

    @appearance.setter
    def appearance(self, value: Appearance) -> None:
        self.base_appearance = value

    @property
    def base_appearance_level(self) -> int:
        base = self.base_appearance
        if isinstance(base, Appearance):
            return int(base.level)
        return 5

    @property
    def appearance_level(self) -> int:
        appearance = self.appearance
        if isinstance(appearance, Appearance):
            return int(appearance.level)
        return self.base_appearance_level

    # ========== Sect ==========

    def consume_elixir(self, elixir: Elixir) -> bool:
        """
        Consume an elixir.
        :return: whether it was consumed successfully
        """
        # 1. Realm check: only elixirs of a realm equal to or lower than the current realm can be consumed
        if elixir.realm > self.cultivation_progress.realm:
            return False
            
        # 2. Duplicate check: if the same elixir was taken and is still active, it has no effect
        # Lifespan elixirs last forever, so each one can only be taken once.
        for consumed in self.elixirs:
            if consumed.elixir.id == elixir.id:
                if not consumed.is_completely_expired(int(self.world.month_stamp)):
                    return False

        # 3. Record the consumption
        self.elixirs.append(ConsumedElixir(elixir, int(self.world.month_stamp)))
        
        # 4. Trigger an immediate attribute recalculation (instant stat changes, or MaxHP/Lifespan changes)
        self.recalc_effects()
        
        return True
    
    def process_elixir_expiration(self, current_month: int) -> None:
        """
        Handle elixir expiry:
        1. Remove fully expired elixirs
        2. If anything was removed, trigger an attribute recalculation
        """
        need_recalc = False
        
        # Process elixirs
        if self.elixirs:
            original_count = len(self.elixirs)
            self.elixirs = [
                e for e in self.elixirs 
                if not e.is_completely_expired(current_month)
            ]
            if len(self.elixirs) < original_count:
                need_recalc = True

        # Process temporary effects
        if self.temporary_effects:
            original_temp_count = len(self.temporary_effects)
            self.temporary_effects = [
                eff for eff in self.temporary_effects
                if current_month < (eff.get("start_month", 0) + eff.get("duration", 0))
            ]
            if len(self.temporary_effects) < original_temp_count:
                need_recalc = True
        
        # If anything expired, recalculate attributes
        if need_recalc:
            self.recalc_effects()

    def join_sect(self, sect: Sect, rank: "SectRank") -> None:
        """Join a sect."""
        if self.is_dead:
            return
        if not sect.accepts_avatar_race(self):
            return
        if self.sect:
            self.leave_sect()
        self.sect = sect
        self.sect_rank = rank
        self.sect_contribution = 0
        sect.add_member(self)
        
    def leave_sect(self) -> None:
        """Leave the sect."""
        if self.sect:
            self.sect.remove_member(self)
            self.sect = None
            self.sect_rank = None
            self.sect_contribution = 0

    def add_sect_contribution(self, amount: int) -> int:
        """
        Accumulate contribution points for the current sect.
        Contribution only applies while in a sect, and negative calls never reduce it.
        """
        if self.sect is None:
            return 0
        try:
            delta = int(amount)
        except (TypeError, ValueError):
            return 0
        if delta <= 0:
            return 0
        self.sect_contribution = max(0, int(getattr(self, "sect_contribution", 0) or 0) + delta)
        return delta

    def get_sect_str(self) -> str:
        """Get the sect display name: "sect name + rank" if in a sect, otherwise "Rogue Cultivator"."""
        from src.i18n import t
        if self.sect is None:
            return t("Rogue Cultivator")
        if self.sect_rank is None:
            return self.sect.name
        from src.classes.sect_ranks import get_rank_display_name
        rank_name = get_rank_display_name(self.sect_rank, self.sect)
        return t("{sect} {rank}", sect=self.sect.name, rank=rank_name)

    def get_sect_rank_name(self) -> str:
        """Get the display name of the sect rank."""
        from src.i18n import t
        if self.sect is None or self.sect_rank is None:
            return t("Rogue Cultivator")
        from src.classes.sect_ranks import get_rank_display_name
        return get_rank_display_name(self.sect_rank, self.sect)

    def get_official_rank_name(self) -> str:
        from src.classes.official_rank import get_official_rank_name
        return get_official_rank_name(self.official_rank)

    @property
    def is_yao(self) -> bool:
        return bool(getattr(getattr(self, "race", None), "is_yao", False))

    # ========== Death ==========

    def set_dead(self, reason: str, time: MonthStamp) -> None:
        """Set the avatar's death state."""
        if self.is_dead:
            return
            
        self.is_dead = True
        self.death_info = {
            "time": int(time),
            "reason": reason,
            "location": (self.pos_x, self.pos_y),
            "sect_name_at_death": self.sect.name if self.sect else "",
            "alignment_at_death": str(self.alignment) if self.alignment else "",
        }
        
        self.planned_actions.clear()
        self.current_action = None
        self._pending_events.clear()
        self.thinking = ""
        self.short_term_objective = ""
        
        # Release all owned cave dwellings
        # Iterate over a copy because release_region modifies the list
        for region in list(self.owned_regions):
            self.release_region(region)

        if self.sect:
            self.sect.remove_member(self)
            self.sect = None
            self.sect_rank = None

        # Leave the active relation graph immediately on death; keep display/remembrance semantics only in archived_relations.
        from src.classes.relation.relations import archive_all_relations_for_death

        archive_all_relations_for_death(self)
        self.computed_relations = {}

    def death_by_old_age(self) -> bool:
        """Check whether the avatar died of old age."""
        return self.age.death_by_old_age(self.cultivation_progress.realm)

    # ========== Metrics tracking ==========

    def record_metrics(self, tags: Optional[List[str]] = None) -> Optional[AvatarMetrics]:
        """
        Record a snapshot of the current state.

        Args:
            tags: optional event tags

        Returns:
            The created snapshot, or None if tracking is disabled
        """
        if not self.enable_metrics_tracking:
            return None

        metrics = AvatarMetrics(
            timestamp=self.world.month_stamp,
            age=self.age.value,
            cultivation_level=self.cultivation_progress.level,
            cultivation_progress=self.cultivation_progress.exp,
            hp=self.hp.cur,
            hp_max=self.hp.max,
            spirit_stones=self.magic_stone.value,
            relations_count=len(self.relations),
            known_regions_count=len(self.known_regions),
            tags=tags or [],
        )

        self.metrics_history.append(metrics)

        # Automatically prune old records
        if len(self.metrics_history) > self.max_metrics_history:
            self.metrics_history = self.metrics_history[-self.max_metrics_history:]

        return metrics

    def get_metrics_summary(self) -> dict:
        """Get the metrics tracking summary."""
        if not self.metrics_history:
            return {"enabled": self.enable_metrics_tracking, "count": 0}

        return {
            "enabled": self.enable_metrics_tracking,
            "count": len(self.metrics_history),
            "first_record": self.metrics_history[0].timestamp,
            "latest_record": self.metrics_history[-1].timestamp,
            "cultivation_growth": (
                self.metrics_history[-1].cultivation_level -
                self.metrics_history[0].cultivation_level
            ),
        }

    # ========== Age and cultivation ==========

    def update_age(self, current_month_stamp: MonthStamp):
        """Update age."""
        self.age.update_age(current_month_stamp, self.birth_month_stamp)

    def update_cultivation(self, new_level: int):
        """Update cultivation progress, and update lifespan and sect rank on realm advancement."""
        old_realm = self.cultivation_progress.realm
        self.cultivation_progress.level = new_level
        self.cultivation_progress.realm = self.cultivation_progress.get_realm(new_level)
        self.cultivation_progress.stage = self.cultivation_progress.get_stage(new_level)
        
        if self.cultivation_progress.realm != old_realm:
            self.recalc_effects()
            from src.classes.sect_ranks import check_and_promote_sect_rank
            check_and_promote_sect_rank(self, old_realm, self.cultivation_progress.realm)

    # ========== Regions and position ==========

    def _init_known_regions(self):
        """Initialize known regions: current position + sect headquarters."""
        if self.tile and self.tile.region:
            self.known_regions.add(self.tile.region.id)
        
        if self.sect:
            from src.classes.sect_metadata import get_sect_region_id_by_sect_id

            sect_region_id = get_sect_region_id_by_sect_id(self.world, int(self.sect.id))
            if sect_region_id is not None:
                self.known_regions.add(sect_region_id)

    # ========== Relations ==========

    def set_relation(self, other: "Avatar", relation: Relation) -> None:
        """Set the relation with another avatar."""
        from src.classes.relation.relations import set_relation
        set_relation(self, other, relation)

    # ========== Semantic Relation Operations ==========

    def acknowledge_master(self, teacher: "Avatar") -> None:
        """
        [I] take [teacher] as my master.
        Semantics: the other is my MASTER.
        """
        self.set_relation(teacher, Relation.IS_MASTER_OF)

    def accept_disciple(self, student: "Avatar") -> None:
        """
        [I] take [student] as my disciple.
        Semantics: the other is my DISCIPLE.
        """
        self.set_relation(student, Relation.IS_DISCIPLE_OF)

    def acknowledge_parent(self, parent: "Avatar") -> None:
        """
        [I] acknowledge [parent] as my father/mother.
        Semantics: the other is my PARENT.
        """
        self.set_relation(parent, Relation.IS_PARENT_OF)
        
    def acknowledge_child(self, child: "Avatar") -> None:
        """
        [I] acknowledge [child] as my son/daughter.
        Semantics: the other is my CHILD.
        """
        self.set_relation(child, Relation.IS_CHILD_OF)

    def become_lovers_with(self, other: "Avatar") -> None:
        """
        [I] become Dao companions with [other].
        """
        self.set_relation(other, Relation.IS_LOVER_OF)

    def become_sworn_sibling_with(self, other: "Avatar") -> None:
        """
        [I] become sworn siblings with [other] (sworn brothers/sisters).
        """
        self.set_relation(other, Relation.IS_SWORN_SIBLING_OF)

    def make_friend_with(self, other: "Avatar") -> None:
        from src.classes.relation.relations import set_friendliness

        set_friendliness(self, other, 35, current_month=int(self.world.month_stamp))
        set_friendliness(other, self, 35, current_month=int(self.world.month_stamp))

    def make_enemy_of(self, other: "Avatar") -> None:
        from src.classes.relation.relations import set_friendliness

        set_friendliness(self, other, -70, current_month=int(self.world.month_stamp))
        set_friendliness(other, self, -70, current_month=int(self.world.month_stamp))

    def get_relation(self, other: "Avatar") -> Optional[Relation]:
        """Get the relation with another avatar."""
        from src.classes.relation.relations import get_relation
        return get_relation(self, other)

    def clear_relation(self, other: "Avatar") -> None:
        """Clear the relation with another avatar."""
        from src.classes.relation.relations import clear_relation
        clear_relation(self, other)

    def get_relation_state(self, other: "Avatar") -> RelationState | None:
        from src.classes.relation.relations import get_state

        return get_state(self, other)

    def has_identity_relation(self, other: "Avatar", relation: Relation) -> bool:
        from src.classes.relation.relations import has_identity_relation

        return has_identity_relation(self, other, relation)

    def get_friendliness(self, other: "Avatar") -> int:
        from src.classes.relation.relations import get_friendliness

        return get_friendliness(self, other)

    def get_numeric_relation(self, other: "Avatar") -> NumericRelation:
        from src.classes.relation.relations import get_numeric_relation

        return get_numeric_relation(self, other)

    # ========== Info display (delegated) ==========

    def get_info(self, detailed: bool = False) -> dict:
        from src.classes.core.avatar.info_presenter import get_avatar_info
        return get_avatar_info(self, detailed)

    def get_structured_info(self) -> dict:
        from src.classes.core.avatar.info_presenter import get_avatar_structured_info
        return get_avatar_structured_info(self)

    def get_expanded_info(
        self, 
        co_region_avatars: Optional[List["Avatar"]] = None,
        other_avatar: Optional["Avatar"] = None,
        detailed: bool = False
    ) -> dict:
        from src.classes.core.avatar.info_presenter import get_avatar_expanded_info
        return get_avatar_expanded_info(self, co_region_avatars, other_avatar, detailed)

    def get_other_avatar_info(self, other_avatar: "Avatar") -> str:
        from src.classes.core.avatar.info_presenter import get_other_avatar_info
        return get_other_avatar_info(self, other_avatar)

    def get_desc(self, detailed: bool = False) -> str:
        """Get the avatar's text description (including effect details)."""
        from src.classes.core.avatar.info_presenter import get_avatar_desc
        return get_avatar_desc(self, detailed=detailed)

    # ========== Magic methods ==========

    @property
    def orthodoxy(self) -> "Orthodoxy | None":
        """Get the avatar's orthodoxy (follows the sect if in one; rogue cultivators use the default)."""
        from src.classes.core.orthodoxy import get_orthodoxy
        
        # Prefer the sect's orthodoxy
        if self.sect:
            return get_orthodoxy(self.sect.orthodoxy_id)
            
        # Rogue cultivators return the default orthodoxy
        return get_orthodoxy("sanxiu")

    @property
    def current_action_name(self) -> str:
        """Get the current action name; defaults to 'Thinking'."""
        if self.current_action and self.current_action.action:
            action = self.current_action.action
            # Use get_action_name() to get the translated action name
            return action.get_action_name()
        from src.i18n import t
        return t("action_thinking")

    def __post_init__(self):
        """Automatically initialize tile and HP after Avatar creation."""
        self.tile = self.world.map.get_tile(self.pos_x, self.pos_y)
        
        max_hp = HP_MAX_BY_REALM.get(self.cultivation_progress.realm, 100)
        self.hp = HP(max_hp, max_hp)
        
        if self.personas is None:
            self.personas = get_random_compatible_personas(_get_persona_num(), avatar=self)

        if not isinstance(self.race, Race):
            self.race = get_race(getattr(self.race, "id", self.race))

        if self.technique is None:
            self.technique = get_technique_by_sect(self.sect)

        if self.sect:
            self.sect.add_member(self)

        if self.alignment is None:
            if self.sect is not None:
                self.alignment = self.sect.alignment
            else:
                self.alignment = random.choice(list(Alignment))
        
        self.recalc_effects()
        self._init_known_regions()

    def __hash__(self) -> int:
        if not hasattr(self, 'id'):
            # Defensive: if id is not initialized yet (e.g. during deepcopy), use the object's memory address
            return super().__hash__()
        return hash(self.id)

    def __str__(self) -> str:
        return str(self.get_info(detailed=False))

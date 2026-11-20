from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Any, Iterable
import uuid

from src.classes.environment.map import Map
from src.systems.time import Year, Month, MonthStamp
from src.sim.managers.avatar_manager import AvatarManager
from src.sim.managers.mortal_manager import MortalManager
from src.sim.managers.deceased_manager import DeceasedManager
from src.sim.managers.event_manager import EventManager
from src.classes.circulation import CirculationManager
from src.classes.gathering.gathering import GatheringManager
from src.classes.poi import POIManager
from src.classes.world_lore import WorldLore
from src.classes.world_secret import WorldSecretRuntime
from src.utils.df import game_configs
from src.classes.language import language_manager
from src.i18n import t
from src.classes.ranking import RankingManager
from src.classes.sect_diplomacy_state import SectDiplomacyState
from src.classes.war import STATUS_PEACE, STATUS_WAR
from src.systems.opportunity import OpportunityManager

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar
    from src.classes.celestial_phenomenon import CelestialPhenomenon
    from src.classes.core.dynasty import Dynasty
    from src.classes.core.sect import Sect


@dataclass
class World():
    map: Map
    month_stamp: MonthStamp
    avatar_manager: AvatarManager = field(default_factory=AvatarManager)
    # Mortal manager
    mortal_manager: MortalManager = field(default_factory=MortalManager)
    # Global event manager
    event_manager: EventManager = field(default_factory=EventManager)
    # Deceased avatar archive manager (independent of AvatarManager, unaffected by cleanup)
    deceased_manager: DeceasedManager = field(default_factory=DeceasedManager)
    # Runtime points of interest, such as graves and future ancient steles / formation eyes
    poi_manager: POIManager = field(default_factory=POIManager)
    # Current celestial phenomenon (world-level buff/debuff)
    current_phenomenon: Optional["CelestialPhenomenon"] = None
    # Current dynasty (mortal dynasty)
    dynasty: Optional["Dynasty"] = None
    # Start year of the celestial phenomenon (used to compute duration)
    phenomenon_start_year: int = 0
    # Manager for circulation of items released into the world
    circulation: CirculationManager = field(default_factory=CirculationManager)
    # Gathering manager
    gathering_manager: GatheringManager = field(default_factory=GatheringManager)
    # World lore and history input for this run
    world_lore: "WorldLore" = field(default_factory=WorldLore)
    # Snapshot of static objects after world-lore shaping, used for save/load restoration
    world_lore_snapshot: dict[str, Any] = field(default_factory=dict)
    # Runtime state of this run's world secrets, independent of world_lore
    world_secret: WorldSecretRuntime = field(default_factory=WorldSecretRuntime)
    # World start year
    start_year: int = 0
    # Ranking manager
    ranking_manager: RankingManager = field(default_factory=RankingManager)
    # Play-session ID, used to distinguish saves
    playthrough_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sect_diplomacy: SectDiplomacyState = field(default_factory=SectDiplomacyState)
    # Opportunity manager: tracks per-avatar time-limited opportunity state and cooldowns.
    opportunity_manager: OpportunityManager = field(default_factory=OpportunityManager)
    # Sect context (lazily initialized), unifies the scope of sects enabled in this run
    _sect_context: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if hasattr(self.event_manager, "set_subject_resolver"):
            self.event_manager.set_subject_resolver(
                lambda avatar_id: self.avatar_manager.get_avatar(str(avatar_id))
            )

    def get_info(self, detailed: bool = False, avatar: Optional["Avatar"] = None) -> dict:
        """
        Return world info (dict), including map info (dict).
        If an avatar is given, it is passed to map.get_info to filter regions and compute distances.
        """
        static_info = self.static_info
        map_info = self.map.get_info(detailed=detailed, avatar=avatar)
        world_info = {**map_info, **static_info}

        if self.current_phenomenon:
            # Use translation keys
            key = t("Current World Phenomenon")
            # Format the content; we assume name and desc are already in the current language (object attributes fixed at load time)
            # If the prompt needs a specific format, a key could be introduced for that too
            # For simplicity, the format is also put into the translation
            # "phenomenon_format": "[{name}] {desc}" (ZH) vs "{name}: {desc}" (EN)
            value = t("phenomenon_format", name=self.current_phenomenon.name, desc=self.current_phenomenon.desc)
            world_info[key] = value

        return world_info

    def get_avatars_in_same_region(self, avatar: "Avatar"):
        return self.avatar_manager.get_avatars_in_same_region(avatar)

    def get_observable_avatars(self, avatar: "Avatar"):
        return self.avatar_manager.get_observable_avatars(avatar)

    @property
    def sect_context(self) -> "SectContext":
        """
        Unified access point for the sect scope.
        - active_sects defaults to existed_sects;
        - if missing, falls back to the global sects_by_id.
        """
        if self._sect_context is None:
            self._sect_context = SectContext(self)
            # Initialize the context with the current world's existed_sects (if present)
            existed = getattr(self, "existed_sects", None)
            if existed:
                self._sect_context.from_existed_sects(existed)
        return self._sect_context

    @property
    def sect_relation_modifiers(self) -> list[dict[str, Any]]:
        return self.sect_diplomacy.relation_modifiers

    @sect_relation_modifiers.setter
    def sect_relation_modifiers(self, value: Iterable[dict[str, Any]]) -> None:
        self.sect_diplomacy.set_relation_modifiers(value)

    @property
    def sect_wars(self) -> list[dict[str, Any]]:
        return self.sect_diplomacy.wars

    @sect_wars.setter
    def sect_wars(self, value: Iterable[dict[str, Any]]) -> None:
        self.sect_diplomacy.set_wars(value)

    def add_sect_relation_modifier(
        self,
        *,
        sect_a_id: int,
        sect_b_id: int,
        delta: int,
        duration: int,
        reason: str,
        meta: Optional[dict] = None,
    ) -> None:
        self.sect_diplomacy.add_relation_modifier(sect_a_id=sect_a_id, sect_b_id=sect_b_id, delta=delta, duration=duration, reason=reason, current_month=int(self.month_stamp), meta=meta)

    def get_sect_war(self, sect_a_id: int, sect_b_id: int) -> Optional[dict[str, Any]]:
        return self.sect_diplomacy.get_war(sect_a_id, sect_b_id)

    def are_sects_at_war(self, sect_a_id: int, sect_b_id: int) -> bool:
        war = self.get_sect_war(sect_a_id, sect_b_id)
        return bool(war and str(war.get("status", "")) == STATUS_WAR)

    def declare_sect_war(
        self,
        *,
        sect_a_id: int,
        sect_b_id: int,
        reason: str = "",
        start_month: Optional[int] = None,
    ) -> dict[str, Any]:
        return self.sect_diplomacy.declare_war(sect_a_id=sect_a_id, sect_b_id=sect_b_id, current_month=int(self.month_stamp if start_month is None else start_month), reason=reason)

    def make_sect_peace(
        self,
        *,
        sect_a_id: int,
        sect_b_id: int,
        reason: str = "",
        peace_start_month: Optional[int] = None,
    ) -> dict[str, Any]:
        return self.sect_diplomacy.make_peace(sect_a_id=sect_a_id, sect_b_id=sect_b_id, current_month=int(self.month_stamp if peace_start_month is None else peace_start_month), reason=reason)

    def record_sect_battle(self, sect_a_id: int, sect_b_id: int, *, battle_month: Optional[int] = None) -> None:
        self.sect_diplomacy.record_battle(sect_a_id, sect_b_id, current_month=int(self.month_stamp if battle_month is None else battle_month))

    def get_sect_diplomacy_state(
        self,
        sect_a_id: int,
        sect_b_id: int,
        *,
        current_month: Optional[int] = None,
    ) -> dict[str, Any]:
        return self.sect_diplomacy.get_state(
            sect_a_id,
            sect_b_id,
            current_month=int(self.month_stamp if current_month is None else current_month),
            start_year=self.start_year,
        )

    def prune_expired_sect_relation_modifiers(self, current_month: Optional[int] = None) -> None:
        self.sect_diplomacy.prune_relation_modifiers(
            current_month=int(self.month_stamp if current_month is None else current_month)
        )

    def get_active_sect_relation_breakdown(
        self, current_month: Optional[int] = None
    ) -> dict[tuple[int, int], list[dict[str, Any]]]:
        return self.sect_diplomacy.relation_breakdown(
            current_month=int(self.month_stamp if current_month is None else current_month)
        )

    def get_active_sect_diplomacy_breakdown(
        self,
        current_month: Optional[int] = None,
        sect_ids: Optional[Iterable[int]] = None,
    ) -> dict[tuple[int, int], list[dict[str, Any]]]:
        return self.sect_diplomacy.diplomacy_breakdown(
            current_month=int(self.month_stamp if current_month is None else current_month),
            start_year=self.start_year,
            sect_ids=sect_ids,
        )

    def set_world_lore(self, lore_text: str) -> None:
        """Set this run's world lore and history input text."""
        self.world_lore.text = lore_text

    @property
    def static_info(self) -> dict:
        info_list = game_configs.get("world_info", [])
        desc = {}
        for row in info_list:
            t_val = row.get("title")
            d_val = row.get("desc")
            if t_val and d_val:
                desc[t_val] = d_val
        return desc

    @classmethod
    def create_with_db(
        cls,
        map: "Map",
        month_stamp: MonthStamp,
        events_db_path: Path,
        start_year: int = 0,
    ) -> "World":
        """
        Factory method: create a World instance that persists events with SQLite.

        Args:
            map: the map object.
            month_stamp: timestamp.
            events_db_path: events database file path.
            start_year: world start year.

        Returns:
            A configured World instance.
        """
        event_manager = EventManager.create_with_db(events_db_path)
        world = cls(
            map=map,
            month_stamp=month_stamp,
            event_manager=event_manager,
            start_year=start_year,
        )
        
        # Initialize the World Martial Tournament schedule
        world.ranking_manager.init_tournament_info(
            start_year,
            month_stamp.get_year(),
            month_stamp.get_month().value
        )
        
        return world


class SectContext:
    """
    Sect context for this run.
    Maintains the "set of sect IDs enabled in this run and still existing", and provides a unified accessor for active sects.
    """

    def __init__(self, world: World):
        self._world = world
        self.active_sect_ids: set[int] = set()

    def from_existed_sects(self, existed_sects: Iterable["Sect"]) -> None:
        """Initialize active_sect_ids from this run's enabled sect list."""
        self.active_sect_ids = {
            int(getattr(sect, "id", 0))
            for sect in existed_sects
            if getattr(sect, "is_active", True)
        }

    def mark_sect_inactive(self, sect_id: int) -> None:
        """Mark a sect as inactive in the context."""
        try:
            sid = int(sect_id)
        except (TypeError, ValueError):
            return
        self.active_sect_ids.discard(sid)

    def get_active_sects(self) -> list["Sect"]:
        """
        Return the list of sects still active in this run.
        Prefers world.existed_sects (consistent with the Sect instances actually mounted in this run),
        then filters by active_sect_ids; if missing, falls back to the global sects_by_id.
        """
        from src.classes.core.sect import sects_by_id
        existed = getattr(self._world, "existed_sects", None) or []

        # 1. If the world has explicit existed_sects, use them as the primary source (consistent with this run's instances)
        if existed:
            if self.active_sect_ids:
                return [
                    sect
                    for sect in existed
                    if int(getattr(sect, "id", 0)) in self.active_sect_ids
                    and getattr(sect, "is_active", True)
                ]
            return [sect for sect in existed if getattr(sect, "is_active", True)]

        # 2. Without existed_sects, filter the global sects_by_id by active_sect_ids
        if self.active_sect_ids:
            return [
                sect
                for sid, sect in sects_by_id.items()
                if sid in self.active_sect_ids and getattr(sect, "is_active", True)
            ]

        # 3. Finally fall back to the active sects in the global sects_by_id
        return [sect for sect in sects_by_id.values() if getattr(sect, "is_active", True)]

from dataclasses import dataclass, field
from pathlib import Path
import json
from enum import Enum

from src.classes.alignment import Alignment
from src.utils.df import game_configs, get_str, get_float, get_int, get_bool
from src.classes.effect import load_effect_from_str
from src.classes.sect_effect import SectEffectsMixin
from src.classes.core.orthodoxy import get_orthodoxy
from src.utils.config import CONFIG

from typing import TYPE_CHECKING, Optional

from src.systems.cultivation import Realm
if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar
    from src.classes.technique import Technique
    from src.classes.sect_ranks import SectRank
    from src.classes.weapon_type import WeaponType

"""
Base data for sects and sect headquarters.
Headquarters names and descriptions have moved to sect_region.csv for use by the map region system.
Only the sect's own info and the static fields needed by the avatar editor are kept here.
"""


class SectRuleId(str, Enum):
    RIGHTEOUS_ORTHODOXY = "righteous_orthodoxy"
    EVIL_SECT_LOYALTY = "evil_sect_loyalty"
    NEUTRAL_SECRECY = "neutral_secrecy"

# Sect headquarters (basic display data; the concrete map location is defined in sect_region.csv)
@dataclass
class SectHeadQuarter:
    """
    Sect headquarters
    """
    name: str
    desc: str
    image: Path

@dataclass
class Sect(SectEffectsMixin):
    """
    Sect
    """
    id: int
    name: str
    desc: str
    member_act_style: str
    alignment: Alignment
    headquarter: SectHeadQuarter
    # Names of techniques associated with this sect (from the sect column of technique.csv)
    technique_names: list[str]
    name_id: str = ""
    # Weight used when randomly choosing a sect (default 1)
    weight: float = 1.0
    # The sect's preferred weapon type
    preferred_weapon: Optional["WeaponType"] = None
    # Effects applied to avatars or systems
    effects: dict[str, object] = field(default_factory=dict)
    effect_desc: str = ""
    sect_effects: dict[str, object] = field(default_factory=dict)
    temporary_sect_effects: list[dict] = field(default_factory=list)
    # Custom sect rank names (optional): SectRank -> name
    rank_names: dict[str, str] = field(default_factory=dict)
    # Orthodoxy ID
    orthodoxy_id: str = "dao"
    # Sect rules
    rule_id: str = ""
    rule_desc: str = ""
    # Whether yao disciples are accepted
    accept_yao: bool = True
    
    # Power-related
    magic_stone: int = 0
    war_weariness: int = 0
    is_active: bool = True
    total_battle_strength: float = 0.0
    influence_radius: int = 0
    color: str = "#FFFFFF"
    # Periodic sect thinking (display only, not written to the event stream)
    periodic_thinking: str = ""
    # Summary of the most recent sect decision (runtime)
    last_decision_summary: str = ""

    # Runtime member list: Avatar ID -> Avatar
    members: dict[str, "Avatar"] = field(default_factory=dict, init=False)
    # List of technique objects: Technique
    techniques: list["Technique"] = field(default_factory=list, init=False)

    def __post_init__(self):
        self.members = {}
        self.techniques = []
        self.sect_effects = dict(self.sect_effects or {})
        self.temporary_sect_effects = list(self.temporary_sect_effects or [])
        self.war_weariness = self._clamp_war_weariness(self.war_weariness)

    @staticmethod
    def _clamp_war_weariness(value: int | float) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            normalized = 0
        return max(0, min(100, normalized))

    def set_war_weariness(self, value: int | float) -> None:
        self.war_weariness = self._clamp_war_weariness(value)

    def change_war_weariness(self, delta: int | float) -> None:
        self.set_war_weariness(int(self.war_weariness) + int(delta))

    def add_member(self, avatar: "Avatar") -> None:
        """Add a member to the sect."""
        if avatar.id not in self.members:
            self.members[avatar.id] = avatar
    
    def remove_member(self, avatar: "Avatar") -> None:
        """Remove a member from the sect."""
        if avatar.id in self.members:
            del self.members[avatar.id]

    def accepts_race(self, race: object) -> bool:
        from src.classes.race import is_yao_race

        return self.accept_yao or not is_yao_race(race)

    def accepts_avatar_race(self, avatar: "Avatar") -> bool:
        return self.accepts_race(getattr(avatar, "race", None))

    def get_info(self) -> str:
        from src.i18n import t
        hq = self.headquarter
        orthodoxy = get_orthodoxy(self.orthodoxy_id)
        orthodoxy_name = t(orthodoxy.name) if orthodoxy else self.orthodoxy_id
        return t("{sect_name} (Orthodoxy: {orthodoxy}, Alignment: {alignment}, Headquarters: {hq_name})",
                sect_name=self.name, orthodoxy=orthodoxy_name, alignment=str(self.alignment), hq_name=hq.name)

    def get_detailed_info(self) -> str:
        # Detailed description: style, alignment, headquarters
        from src.i18n import t
        hq = self.headquarter
        effect_part = t(" Effect: {effect_desc}", effect_desc=self.effect_desc) if self.effect_desc else ""
        
        orthodoxy = get_orthodoxy(self.orthodoxy_id)
        orthodoxy_name = t(orthodoxy.name) if orthodoxy else self.orthodoxy_id
        
        return t("{sect_name} (Orthodoxy: {orthodoxy}, Alignment: {alignment}, Style: {style}, Headquarters: {hq_name}){effect}",
                sect_name=self.name, orthodoxy=orthodoxy_name, alignment=str(self.alignment), 
                style=t(self.member_act_style), hq_name=hq.name, effect=effect_part)
    
    def get_rank_name(self, rank: "SectRank") -> str:
        """
        Get the sect's rank name (custom names supported).
        
        Args:
            rank: sect rank enum
            
        Returns:
            The rank name string
        """
        from src.classes.sect_ranks import SectRank, DEFAULT_RANK_NAMES
        from src.i18n import t
        # Prefer the custom name, otherwise use the default name
        val = self.rank_names.get(rank.value, DEFAULT_RANK_NAMES.get(rank, t("Disciple")))
        return t(val)

    def get_structured_info(self) -> dict:
        hq = self.headquarter
        from src.i18n import t
        from src.classes.sect_ranks import RANK_ORDER
        from src.classes.technique import techniques_by_name
        status_snapshot_by_avatar = self._build_member_status_snapshot_map()
        
        # Member list: taken directly from self.members
        members_list = []
        for a in self.members.values():
            rank_enum = getattr(a, "sect_rank", None)
            sort_val = 999
            if rank_enum and rank_enum in RANK_ORDER:
                sort_val = RANK_ORDER[rank_enum]
            member_status = status_snapshot_by_avatar.get(str(getattr(a, "id", "")), {})
                
            members_list.append({
                "id": str(a.id),
                "name": a.name,
                # Only a placeholder avatar ID is provided here; the frontend has its own fallback logic
                "pic_id": getattr(a, "custom_pic_id", 0) or 0,
                "gender": a.gender.value if hasattr(a.gender, "value") else "male",
                "rank": a.get_sect_rank_name(),
                "realm": a.cultivation_progress.get_info() if hasattr(a, 'cultivation_progress') else t("Unknown"),
                "contribution": int(member_status.get("sect_contribution", 0) or 0),
                "base_battle_strength": int(member_status.get("base_battle_strength", 0) or 0),
                "status_score": float(member_status.get("status_score", 0.0) or 0.0),
                "_sort_val": sort_val,
            })
        # Sort by rank
        members_list.sort(key=lambda x: (x["_sort_val"], -x["contribution"], -x["status_score"], x["name"]))
        # Clean up the sort field
        for m in members_list:
            del m["_sort_val"]

        # Fill in techniques
        # Look up the Technique objects in the global dict by technique_names and serialize them
        techniques_data = []
        for t_name in self.technique_names:
            t_obj = techniques_by_name.get(t_name)
            if t_obj:
                techniques_data.append(t_obj.get_structured_info())
            else:
                # Fallback for missing techniques: create a minimal structure
                techniques_data.append({
                    "name": t_name,
                    "desc": t("(Unknown technique)"),
                    "grade": "",
                    "color": (200, 200, 200), # Gray
                    "attribute": "",
                    "effect_desc": ""
                })

        orthodoxy = get_orthodoxy(self.orthodoxy_id)

        return {
            "id": self.id,
            "name": self.name,
            "desc": self.desc,
            "alignment": str(self.alignment), # Return the localized string directly
            "style": t(self.member_act_style),
            "hq_name": hq.name,
            "hq_desc": hq.desc,
            "effect_desc": self.effect_desc,
            "techniques": techniques_data,
            # The domain model still tracks config sources via technique_names; the API also provides structured techniques.
            "technique_names": self.technique_names,
            "preferred_weapon": str(self.preferred_weapon) if self.preferred_weapon else "",
            "members": members_list,
            "orthodoxy": orthodoxy.get_info(detailed=True) if orthodoxy else {"id": self.orthodoxy_id},
            "magic_stone": self.magic_stone,
            "war_weariness": self.war_weariness,
            "is_active": self.is_active,
            "total_battle_strength": self.total_battle_strength,
            "influence_radius": self.influence_radius,
            "color": self.color,
            "rule_id": self.rule_id,
            "rule_desc": self.rule_desc,
            "accept_yao": self.accept_yao,
            "periodic_thinking": self.periodic_thinking,
            # Alias still marked deprecated on the frontend; same semantics as periodic_thinking.
            "yearly_thinking": self.periodic_thinking,
        }

    def is_alignment_recruitable(self, alignment: Alignment | None) -> bool:
        if alignment is None:
            return True
        if self.alignment == Alignment.RIGHTEOUS:
            return alignment != Alignment.EVIL
        if self.alignment == Alignment.EVIL:
            return alignment != Alignment.RIGHTEOUS
        return True

    def is_member_rule_breaker(self, avatar: "Avatar") -> bool:
        """
        The current version only handles obvious rule conflicts that are "extreme enough to warrant expulsion".
        Finer-grained rule behavior checks can be added here later.
        """
        alignment = getattr(avatar, "alignment", None)
        if alignment is None:
            return False

        if self.rule_id == SectRuleId.RIGHTEOUS_ORTHODOXY.value:
            return alignment == Alignment.EVIL
        if self.rule_id == SectRuleId.EVIL_SECT_LOYALTY.value:
            return alignment == Alignment.RIGHTEOUS
        return False

    def get_identity_summary(self) -> dict:
        from src.i18n import t

        orthodoxy = get_orthodoxy(self.orthodoxy_id)
        return {
            "sect_name": self.name,
            "purpose": self.desc,
            "style": t(self.member_act_style),
            "alignment": str(self.alignment),
            "orthodoxy_id": self.orthodoxy_id,
            "orthodoxy_name": t(orthodoxy.name) if orthodoxy else self.orthodoxy_id,
            "rule_id": self.rule_id,
            "rule_desc": self.rule_desc,
        }

    def get_member_upkeep_by_realm(self) -> dict[Realm, int]:
        from src.classes.sect_member_status import get_member_upkeep_by_realm
        return get_member_upkeep_by_realm()

    def get_member_upkeep_by_rank(self) -> dict["SectRank", int]:
        from src.classes.sect_ranks import SectRank

        realm_upkeep = self.get_member_upkeep_by_realm()
        return {
            SectRank.OuterDisciple: realm_upkeep.get(Realm.Qi_Refinement, 0),
            SectRank.InnerDisciple: realm_upkeep.get(Realm.Foundation_Establishment, 0),
            SectRank.Elder: realm_upkeep.get(Realm.Core_Formation, 0),
            SectRank.Patriarch: realm_upkeep.get(Realm.Nascent_Soul, 0),
        }

    def _resolve_member_rank(self, avatar: "Avatar") -> "SectRank":
        from src.classes.sect_ranks import SectRank, get_rank_from_realm

        rank = getattr(avatar, "sect_rank", None)
        if isinstance(rank, SectRank):
            return rank
        if isinstance(rank, str):
            normalized = rank.strip().lower()
            string_mapping = {
                "patriarch": SectRank.Patriarch,
                "elder": SectRank.Elder,
                "inner": SectRank.InnerDisciple,
                "innerdisciple": SectRank.InnerDisciple,
                "outer": SectRank.OuterDisciple,
                "outerdisciple": SectRank.OuterDisciple,
            }
            if normalized in string_mapping:
                return string_mapping[normalized]
        realm = getattr(getattr(avatar, "cultivation_progress", None), "realm", Realm.Qi_Refinement)
        return get_rank_from_realm(realm)

    def get_member_upkeep_for_avatar(self, avatar: "Avatar") -> int:
        rank = self._resolve_member_rank(avatar)
        return self.get_member_upkeep_by_rank().get(rank, 0)

    def estimate_yearly_member_upkeep(self) -> tuple[int, dict[str, dict[str, int]]]:
        total = 0
        breakdown: dict[str, dict[str, int]] = {}
        upkeep_by_rank = self.get_member_upkeep_by_rank()

        for avatar in getattr(self, "members", {}).values():
            if getattr(avatar, "is_dead", False):
                continue
            rank = self._resolve_member_rank(avatar)
            cost = upkeep_by_rank.get(rank, 0)
            key = str(rank.value)
            entry = breakdown.setdefault(
                key,
                {
                    "rank": str(rank),
                    "member_count": 0,
                    "upkeep_per_member": cost,
                    "subtotal": 0,
                },
            )
            entry["member_count"] += 1
            entry["subtotal"] += cost
            total += cost

        return total, breakdown

    def _get_status_normalization_context(self) -> dict[str, float]:
        from src.classes.sect_member_status import SectMemberStatusService
        return SectMemberStatusService.normalization(self)

    def get_member_status_score(
        self,
        avatar: "Avatar",
        *,
        max_contribution: float | None = None,
        max_battle_strength: float | None = None,
    ) -> float:
        from src.classes.sect_member_status import SectMemberStatusService
        normalization = self._get_status_normalization_context()
        return SectMemberStatusService.score(
            avatar,
            max_contribution=float(max_contribution if max_contribution is not None else normalization["max_contribution"]),
            max_battle_strength=float(max_battle_strength if max_battle_strength is not None else normalization["max_battle_strength"]),
        )

    def get_member_status_snapshot(self, avatar: "Avatar") -> dict[str, float | int]:
        from src.classes.sect_member_status import SectMemberStatusService
        return SectMemberStatusService.snapshot(self, avatar)

    def _build_member_status_snapshot_map(self) -> dict[str, dict[str, float | int]]:
        from src.classes.sect_member_status import SectMemberStatusService
        return SectMemberStatusService.snapshot_map(self)

    def get_member_status_snapshot_with_normalization(
        self,
        avatar: "Avatar",
        *,
        max_contribution: float,
        max_battle_strength: float,
    ) -> dict[str, float | int]:
        from src.classes.sect_member_status import SectMemberStatusService
        return SectMemberStatusService.snapshot(self, avatar, normalization={
            "max_contribution": max_contribution, "max_battle_strength": max_battle_strength,
        })

    def get_living_members_sorted_by_status(self) -> list["Avatar"]:
        from src.classes.sect_member_status import SectMemberStatusService
        return SectMemberStatusService.living_members_sorted(self)

    def refresh_member_ranks(self) -> None:
        from src.classes.sect_ranks import SectRank

        members = self.get_living_members_sorted_by_status()
        count = len(members)
        if count <= 0:
            return

        elder_quota = 0
        if count >= 4:
            elder_quota = max(1, count // 6)
        inner_quota = 0
        if count >= 2:
            inner_quota = max(1, count // 3)
        inner_quota = min(inner_quota, max(0, count - 1 - elder_quota))

        for index, avatar in enumerate(members):
            if index == 0:
                avatar.sect_rank = SectRank.Patriarch
            elif index <= elder_quota:
                avatar.sect_rank = SectRank.Elder
            elif index <= elder_quota + inner_quota:
                avatar.sect_rank = SectRank.InnerDisciple
            else:
                avatar.sect_rank = SectRank.OuterDisciple


def _split_names(value: object) -> list[str]:
    raw = "" if value is None or str(value) == "nan" else str(value)
    sep = CONFIG.df.ids_separator
    parts = [x.strip() for x in raw.split(sep) if x.strip()] if raw else []
    return parts

def _merge_effects_dict(base: dict[str, object], addition: dict[str, object]) -> dict[str, object]:
    """Merge two effects dicts (simple merge logic)."""
    if not base and not addition:
        return {}
    merged: dict[str, object] = dict(base) if base else {}
    for key, val in (addition or {}).items():
        if key in merged:
            old = merged[key]
            if isinstance(old, list) and isinstance(val, list):
                # Deduplicated union
                seen = set(old)
                result = list(old)
                for x in val:
                    if x not in seen:
                        seen.add(x)
                        result.append(x)
                merged[key] = result
            elif isinstance(old, (int, float)) and isinstance(val, (int, float)):
                merged[key] = old + val
            else:
                # Overwrite by default
                merged[key] = val
        else:
            merged[key] = val
    return merged

def _load_sects_data() -> tuple[dict[int, Sect], dict[str, Sect]]:
    """Load sect data from the config table.
    Returns: new (sects_by_id, sects_by_name)
    """
    new_by_id: dict[int, Sect] = {}
    new_by_name: dict[str, Sect] = {}

    df = game_configs["sect"]
    # Read the headquarters mapping (prefer headquarters name/description from sect_region.csv)
    sect_region_df = game_configs.get("sect_region")
    hq_by_sect_id: dict[int, tuple[str, str]] = {}
    if sect_region_df is not None:
        for sr in sect_region_df:
            sid = get_int(sr, "sect_id", -1)
            if sid == -1:
                continue
            hq_name = get_str(sr, "name")
            hq_desc = get_str(sr, "desc")
            hq_by_sect_id[sid] = (hq_name, hq_desc)
    
    # The technique table may not exist or may lack the sect column; be tolerant
    tech_df = game_configs.get("technique")
    assets_base = Path("assets/sects")
    
    for row in df:
        name = get_str(row, "name")
        image_path = assets_base / f"{name}.png"
        
        # Read the current sect ID first for later use
        sid = get_int(row, "id")

        # Collect the technique names configured under this sect
        technique_names: list[str] = []
        # Check whether tech_df exists and has data
        if tech_df:
            technique_names = [
                get_str(t, "name")
                for t in tech_df
                if get_int(t, "sect_id") == sid and get_str(t, "name")
            ]

        weight = get_float(row, "weight", 1.0)

        # Read effects
        base_effects = load_effect_from_str(get_str(row, "effects"))
        
        # Orthodoxy handling
        orthodoxy_id = get_str(row, "orthodoxy_id") or "dao"
        orthodoxy = get_orthodoxy(orthodoxy_id)
        
        # Merge orthodoxy effects into sect effects
        final_effects = base_effects
        if orthodoxy and orthodoxy.effects:
             # Use the orthodoxy as the base; sect effects stack on/override it
             final_effects = _merge_effects_dict(orthodoxy.effects, base_effects)
        
        from src.classes.effect import format_effects_to_text
        effect_desc = format_effects_to_text(final_effects)

        # Read the preferred weapon type
        from src.classes.weapon_type import WeaponType
        preferred_weapon_str = get_str(row, "preferred_weapon")
        preferred_weapon = WeaponType.from_str(preferred_weapon_str) if preferred_weapon_str else None

        # Parse custom ranks
        raw_ranks = get_str(row, "rank_names")
        rank_names_map = {}
        if raw_ranks:
            # Format: patriarch;elder;inner;outer
            parts = [x.strip() for x in raw_ranks.split(";") if x.strip()]
            if len(parts) == 4:
                from src.classes.sect_ranks import SectRank
                rank_names_map = {
                    SectRank.Patriarch.value: parts[0],
                    SectRank.Elder.value: parts[1],
                    SectRank.InnerDisciple.value: parts[2],
                    SectRank.OuterDisciple.value: parts[3],
                }

        # Prefer the headquarters name/description from sect_region.csv; otherwise use the inline headquarters column or fall back to the sect name
        csv_hq = hq_by_sect_id.get(sid)
        hq_name_from_csv = (csv_hq[0] if csv_hq else "").strip() if csv_hq else ""
        hq_desc_from_csv = (csv_hq[1] if csv_hq else "").strip() if csv_hq else ""

        hq_name = hq_name_from_csv or get_str(row, "headquarter_name") or name
        hq_desc = hq_desc_from_csv or get_str(row, "headquarter_desc")
        
        color = get_str(row, "color") or "#FFFFFF"
        rule_id = get_str(row, "rule_id")
        rule_desc_id = get_str(row, "rule_desc_id")
        from src.i18n import t
        rule_desc = t(rule_desc_id) if rule_desc_id else ""
        if rule_desc == rule_desc_id:
            rule_desc = ""

        sect = Sect(
            id=sid,
            name_id=get_str(row, "name_id"),
            name=name,
            desc=get_str(row, "desc"),
            member_act_style=get_str(row, "member_act_style"),
            alignment=Alignment.from_str(get_str(row, "alignment")),
            headquarter=SectHeadQuarter(
                name=hq_name,
                desc=hq_desc,
                image=image_path,
            ),
            technique_names=technique_names,
            weight=weight,
            preferred_weapon=preferred_weapon,
            effects=final_effects,
            effect_desc=effect_desc,
            rank_names=rank_names_map,
            orthodoxy_id=orthodoxy_id,
            color=color,
            rule_id=rule_id,
            rule_desc=rule_desc,
            accept_yao=get_bool(row, "accept_yao", True),
        )
        new_by_id[sect.id] = sect
        new_by_name[sect.name] = sect

    return new_by_id, new_by_name

# Global containers (keep references stable)
sects_by_id: dict[int, Sect] = {}
sects_by_name: dict[str, Sect] = {}

def reload():
    """Reload data while preserving the global dict references."""
    new_id, new_name = _load_sects_data()
    
    sects_by_id.clear()
    sects_by_id.update(new_id)
    
    sects_by_name.clear()
    sects_by_name.update(new_name)

# Run once at module import
reload()


def get_sect_info_with_rank(avatar: "Avatar", detailed: bool = False) -> str:
    """
    Get the sect info string including the rank.
    
    Args:
        avatar: the avatar object
        detailed: whether to include detailed sect info (alignment, style, headquarters, etc.)
        
    Returns:
        - Rogue cultivator: returns "Rogue Cultivator"
        - detailed=False: returns e.g. "Mingxin Sword Sect Elder"
        - detailed=True: returns e.g. "Mingxin Sword Sect Elder (Alignment: Righteous, Style: ..., Headquarters: ...)"
    """
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from src.classes.core.avatar import Avatar
    
    # Rogue cultivators return directly
    from src.i18n import t
    if avatar.sect is None:
        return t("Rogue Cultivator")
    
    # Get rank + sect name (e.g. "Mingxin Sword Sect Elder")
    sect_rank_str = avatar.get_sect_str()
    
    # If details are not needed, return the rank string directly
    if not detailed:
        return sect_rank_str
    
    # Details needed: append the sect's detailed description
    # Rebuild it instead of parsing the string
    hq = avatar.sect.headquarter
    effect_part = t(" Effect: {effect_desc}", effect_desc=avatar.sect.effect_desc) if avatar.sect.effect_desc else ""
    
    # Build the details using standard spaces and parentheses
    orthodoxy = get_orthodoxy(avatar.sect.orthodoxy_id)
    orthodoxy_name = t(orthodoxy.name) if orthodoxy else avatar.sect.orthodoxy_id
    
    detail_content = t("(Orthodoxy: {orthodoxy}, Alignment: {alignment}, Style: {style}, Headquarters: {hq_name}){effect}",
                       orthodoxy=orthodoxy_name,
                       alignment=avatar.sect.alignment, 
                       style=t(avatar.sect.member_act_style), 
                       hq_name=hq.name, 
                       effect=effect_part)
    
    return f"{sect_rank_str} {detail_content}"


def get_sect_decision_context(
    sect: "Sect",
    world: "World",
    event_storage: "EventStorage",
    *,
    history_limit: int = 50,
):
    """
    Convenience entry point: get the sect decision context.

    Forwards the call once here so the domain layer does not depend directly on a concrete system implementation.
    """
    from src.systems.sect_decision_context import build_sect_decision_context

    return build_sect_decision_context(
        sect=sect,
        world=world,
        event_storage=event_storage,
        history_limit=history_limit,
    )

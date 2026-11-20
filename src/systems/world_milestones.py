"""World milestones ("Chronicle of Firsts").

Deterministic, LLM-free detection of notable world "firsts", run once per monthly step.

Baseline choice: the chronicle opens on the first detection pass (the first simulated
month of a new world, or the first month after loading a save that predates this
feature). Everything already true at that point -- avatars that start above Qi
Refinement, existing Dao companions, sects already at war -- is pre-history and is
seeded silently. Only transitions observed between two passes are recorded, so each
milestone means "the first to do X since the chronicle began". Avatars (and bond
partners) that are first seen on a pass are also baselined silently, so cultivators
created mid-run at a high realm or with pre-planned bonds never count as a first.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterable

from src.classes.event import Event
from src.classes.relation.relation import Relation
from src.classes.world_milestone import WorldMilestoneRecord, WorldMilestoneState
from src.classes.war import STATUS_WAR
from src.i18n import t
from src.systems.cultivation import REALM_ORDER, REALM_RANK, Realm
from src.systems.time import MonthStamp, get_date_str

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar
    from src.classes.core.world import World


KIND_REALM = "realm"
KIND_AGE = "age"
KIND_SWORN_SIBLINGS = "sworn_siblings"
KIND_DAO_COMPANIONS = "dao_companions"
KIND_MASTER_DISCIPLE = "master_disciple"
KIND_SECT_WAR = "sect_war"

# Lifespans: Qi Refinement 60-90, Foundation +50, Core +100, Nascent Soul +400.
# 100 is reachable from Foundation Establishment; 300 requires Nascent Soul (or rare boons).
AGE_THRESHOLDS: tuple[int, ...] = (100, 300)

# Mark name -> relation that, stored on avatar A toward B, means "B is my <relation>".
BOND_MARKS: dict[str, Relation] = {
    KIND_SWORN_SIBLINGS: Relation.IS_SWORN_SIBLING_OF,
    KIND_DAO_COMPANIONS: Relation.IS_LOVER_OF,
    KIND_MASTER_DISCIPLE: Relation.IS_DISCIPLE_OF,
}


@dataclass(frozen=True, slots=True)
class MilestoneDefinition:
    key: str
    kind: str
    realm: Realm | None = None
    age: int | None = None


def _build_definitions() -> tuple[MilestoneDefinition, ...]:
    definitions: list[MilestoneDefinition] = [
        MilestoneDefinition(key=f"first_realm_{realm.value.lower()}", kind=KIND_REALM, realm=realm)
        for realm in REALM_ORDER[1:]
    ]
    definitions.extend(
        MilestoneDefinition(key=f"first_age_{age}", kind=KIND_AGE, age=age)
        for age in AGE_THRESHOLDS
    )
    definitions.extend(
        [
            MilestoneDefinition(key="first_sworn_siblings", kind=KIND_SWORN_SIBLINGS),
            MilestoneDefinition(key="first_dao_companions", kind=KIND_DAO_COMPANIONS),
            MilestoneDefinition(key="first_master_disciple", kind=KIND_MASTER_DISCIPLE),
            MilestoneDefinition(key="first_sect_war", kind=KIND_SECT_WAR),
        ]
    )
    return tuple(definitions)


MILESTONE_DEFINITIONS: tuple[MilestoneDefinition, ...] = _build_definitions()
MILESTONE_DEFINITIONS_BY_KEY: dict[str, MilestoneDefinition] = {
    definition.key: definition for definition in MILESTONE_DEFINITIONS
}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _realm_name(realm_value: Any) -> str:
    try:
        return str(Realm(str(realm_value)))
    except ValueError:
        return str(realm_value)


def get_milestone_title(definition: MilestoneDefinition) -> str:
    if definition.kind == KIND_REALM:
        return t("First to Reach {realm}", realm=str(definition.realm))
    if definition.kind == KIND_AGE:
        return t("First to Live {age} Years", age=definition.age)
    if definition.kind == KIND_SWORN_SIBLINGS:
        return t("First Sworn Siblings")
    if definition.kind == KIND_DAO_COMPANIONS:
        return t("First Dao Companions")
    if definition.kind == KIND_MASTER_DISCIPLE:
        return t("First Master and Disciple")
    return t("First Sect War")


def get_milestone_description(definition: MilestoneDefinition) -> str:
    if definition.kind == KIND_REALM:
        return t(
            "The first cultivator to break through to {realm} since the chronicle began.",
            realm=str(definition.realm),
        )
    if definition.kind == KIND_AGE:
        return t(
            "The first cultivator to reach the age of {age} since the chronicle began.",
            age=definition.age,
        )
    if definition.kind == KIND_SWORN_SIBLINGS:
        return t("The first pair of cultivators to swear an oath of sworn siblinghood since the chronicle began.")
    if definition.kind == KIND_DAO_COMPANIONS:
        return t("The first pair of cultivators to become Dao companions since the chronicle began.")
    if definition.kind == KIND_MASTER_DISCIPLE:
        return t("The first master to take a disciple since the chronicle began.")
    return t("The first war declared between two sects since the chronicle began.")


def _name_at(names: list[str], index: int) -> str:
    return names[index] if index < len(names) else t("Unknown character")


def render_milestone_summary(record: WorldMilestoneRecord) -> str:
    definition = MILESTONE_DEFINITIONS_BY_KEY.get(record.key)
    if definition is None:
        return ""
    names = record.avatar_names
    if definition.kind == KIND_REALM:
        return t(
            "{avatar} became the first cultivator in recorded history to break through to {realm}.",
            avatar=_name_at(names, 0),
            realm=_realm_name(record.detail.get("realm", "")),
        )
    if definition.kind == KIND_AGE:
        return t(
            "{avatar} became the first cultivator in recorded history to reach the age of {age}.",
            avatar=_name_at(names, 0),
            age=record.detail.get("age", definition.age),
        )
    if definition.kind == KIND_SWORN_SIBLINGS:
        return t(
            "{avatar_a} and {avatar_b} swore the first oath of sworn siblinghood in recorded history.",
            avatar_a=_name_at(names, 0),
            avatar_b=_name_at(names, 1),
        )
    if definition.kind == KIND_DAO_COMPANIONS:
        return t(
            "{avatar_a} and {avatar_b} became the first Dao companions in recorded history.",
            avatar_a=_name_at(names, 0),
            avatar_b=_name_at(names, 1),
        )
    if definition.kind == KIND_MASTER_DISCIPLE:
        return t(
            "{master} took {disciple} as a disciple, forging the first master-disciple bond in recorded history.",
            master=_name_at(names, 0),
            disciple=_name_at(names, 1),
        )
    sect_names = record.sect_names
    return t(
        "{sect_a} and {sect_b} went to war, the first sect war in recorded history.",
        sect_a=sect_names[0] if sect_names else "",
        sect_b=sect_names[1] if len(sect_names) > 1 else "",
    )


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def _bond_partner_ids(avatar: "Avatar", relation: Relation) -> list[str]:
    return sorted(
        str(other.id)
        for other, state in (getattr(avatar, "relations", None) or {}).items()
        if relation in state.identity_relations
    )


def build_avatar_marks(avatar: "Avatar") -> dict[str, Any]:
    marks: dict[str, Any] = {
        KIND_REALM: REALM_RANK[avatar.cultivation_progress.realm],
        KIND_AGE: int(avatar.age.age),
    }
    for mark_name, relation in BOND_MARKS.items():
        marks[mark_name] = _bond_partner_ids(avatar, relation)
    return marks


def _avatar_record(
    key: str,
    month: int,
    avatars: Iterable["Avatar"],
    detail: dict[str, Any] | None = None,
) -> WorldMilestoneRecord:
    avatar_list = list(avatars)
    return WorldMilestoneRecord(
        key=key,
        month_stamp=month,
        avatar_ids=[str(avatar.id) for avatar in avatar_list],
        avatar_names=[str(avatar.name) for avatar in avatar_list],
        detail=dict(detail or {}),
    )


def _detect_realm(definition: MilestoneDefinition, world, state, avatars, current_marks):
    target_rank = REALM_RANK[definition.realm]
    for avatar in avatars:
        previous = state.avatar_marks.get(str(avatar.id))
        if previous is None:
            continue
        before = int(previous.get(KIND_REALM, target_rank))
        after = int(current_marks[str(avatar.id)][KIND_REALM])
        if before < target_rank <= after:
            return _avatar_record(
                definition.key,
                int(world.month_stamp),
                [avatar],
                {"realm": definition.realm.value},
            )
    return None


def _detect_age(definition: MilestoneDefinition, world, state, avatars, current_marks):
    threshold = int(definition.age)
    for avatar in avatars:
        previous = state.avatar_marks.get(str(avatar.id))
        if previous is None:
            continue
        before = int(previous.get(KIND_AGE, threshold))
        after = int(current_marks[str(avatar.id)][KIND_AGE])
        if before < threshold <= after:
            return _avatar_record(definition.key, int(world.month_stamp), [avatar], {"age": threshold})
    return None


def _detect_bond(definition: MilestoneDefinition, world, state, avatars, current_marks):
    mark_name = definition.kind
    for avatar in avatars:
        previous = state.avatar_marks.get(str(avatar.id))
        if previous is None:
            continue
        new_partner_ids = set(current_marks[str(avatar.id)][mark_name]) - set(previous.get(mark_name, []))
        for partner_id in sorted(new_partner_ids):
            # A partner first seen this pass is a newcomer whose bonds are pre-planned, not a first.
            if partner_id not in state.avatar_marks:
                continue
            partner = world.avatar_manager.get_avatar(partner_id)
            if partner is None:
                continue
            # For master-disciple the mark lives on the master, so the order is (master, disciple).
            return _avatar_record(definition.key, int(world.month_stamp), [avatar, partner])
    return None


def _resolve_sect_name(sect_id: int) -> str:
    from src.classes.core.sect import sects_by_id

    sect = sects_by_id.get(int(sect_id))
    return str(sect.name) if sect is not None else str(sect_id)


def _detect_sect_war(definition: MilestoneDefinition, world, state, _avatars, _current_marks):
    opened_month = int(state.opened_month or 0)
    candidates = []
    for war in getattr(world, "sect_wars", None) or []:
        if str(war.get("status", "")) != STATUS_WAR:
            continue
        try:
            start_month = int(war.get("start_month", 0))
            sect_ids = [int(war["sect_a_id"]), int(war["sect_b_id"])]
        except (TypeError, ValueError, KeyError):
            continue
        if start_month <= opened_month:
            continue
        candidates.append((start_month, sect_ids))
    if not candidates:
        return None
    start_month, sect_ids = min(candidates)
    return WorldMilestoneRecord(
        key=definition.key,
        month_stamp=int(world.month_stamp),
        sect_ids=sect_ids,
        sect_names=[_resolve_sect_name(sect_id) for sect_id in sect_ids],
        detail={"start_month": start_month},
    )


_DETECTORS: dict[str, Callable[..., WorldMilestoneRecord | None]] = {
    KIND_REALM: _detect_realm,
    KIND_AGE: _detect_age,
    KIND_SWORN_SIBLINGS: _detect_bond,
    KIND_DAO_COMPANIONS: _detect_bond,
    KIND_MASTER_DISCIPLE: _detect_bond,
    KIND_SECT_WAR: _detect_sect_war,
}


def _build_event(world: "World", record: WorldMilestoneRecord) -> Event:
    return Event(
        month_stamp=world.month_stamp,
        content=t("[Chronicle of Firsts] {summary}", summary=render_milestone_summary(record)),
        related_avatars=list(record.avatar_ids) or None,
        related_sects=list(record.sect_ids) or None,
        is_major=True,
    )


def detect_world_milestones(world: "World", living_avatars: list["Avatar"]) -> list[Event]:
    """Run one detection pass; returns the major events for newly achieved milestones."""
    state: WorldMilestoneState = world.milestones
    avatars = [avatar for avatar in living_avatars if not getattr(avatar, "is_dead", False)]
    current_marks = {str(avatar.id): build_avatar_marks(avatar) for avatar in avatars}

    if not state.is_open:
        state.opened_month = int(world.month_stamp)
        state.avatar_marks = current_marks
        return []

    events: list[Event] = []
    for definition in MILESTONE_DEFINITIONS:
        if state.is_achieved(definition.key):
            continue
        record = _DETECTORS[definition.kind](definition, world, state, avatars, current_marks)
        if record is None:
            continue
        event = _build_event(world, record)
        record.event_id = event.id
        if state.add_record(record):
            events.append(event)

    # Dead or removed avatars drop out of the baseline; newcomers enter it silently.
    state.avatar_marks = current_marks
    return events


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


def _record_to_view(world: "World", record: WorldMilestoneRecord) -> dict[str, Any]:
    definition = MILESTONE_DEFINITIONS_BY_KEY[record.key]
    month_stamp = MonthStamp(int(record.month_stamp))
    avatars = []
    for index, avatar_id in enumerate(record.avatar_ids):
        avatar = world.avatar_manager.get_avatar(avatar_id)
        avatars.append(
            {
                "id": avatar_id,
                "name": _name_at(record.avatar_names, index),
                "available": avatar is not None,
                "is_dead": bool(getattr(avatar, "is_dead", False)) if avatar is not None else True,
            }
        )
    return {
        "key": record.key,
        "kind": definition.kind,
        "title": get_milestone_title(definition),
        "description": render_milestone_summary(record),
        "month_stamp": int(record.month_stamp),
        "year": month_stamp.get_year(),
        "month": month_stamp.get_month().value,
        "date_text": get_date_str(int(record.month_stamp)),
        "avatars": avatars,
        "sects": [
            {"id": sect_id, "name": record.sect_names[index] if index < len(record.sect_names) else str(sect_id)}
            for index, sect_id in enumerate(record.sect_ids)
        ],
    }


def build_world_milestones_overview(world: "World") -> dict[str, Any]:
    state: WorldMilestoneState = world.milestones
    achieved = [
        _record_to_view(world, record)
        for record in state.get_records_chronological()
        if record.key in MILESTONE_DEFINITIONS_BY_KEY
    ]
    achieved_keys = {item["key"] for item in achieved}
    pending = [
        {
            "key": definition.key,
            "kind": definition.kind,
            "title": get_milestone_title(definition),
            "description": get_milestone_description(definition),
        }
        for definition in MILESTONE_DEFINITIONS
        if definition.key not in achieved_keys
    ]
    opened_month = state.opened_month
    return {
        "achieved": achieved,
        "pending": pending,
        "total": len(MILESTONE_DEFINITIONS),
        "opened_month_stamp": opened_month,
        "opened_date_text": get_date_str(int(opened_month)) if opened_month is not None else "",
    }

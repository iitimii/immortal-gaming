"""Read-only side-by-side comparison of two living avatars.

DTO shape (labels are localized server-side, ids are stable):

    {
        "a": AvatarSide,
        "b": AvatarSide,
        "relation": {
            "a_to_b": RelationView,  # how A regards B
            "b_to_a": RelationView,  # how B regards A
        },
        "battle": {
            "a_strength": float,         # A's effective strength against B
            "b_strength": float,         # B's effective strength against A
            "a_win_probability": float,  # chance A wins a fight against B
            "b_win_probability": float,  # chance B wins a fight against A
            "method": "closed_form",
        },
    }

    AvatarSide = {
        "id", "name", "nickname",
        "realm": Label, "stage": Label, "cultivation_display": str, "level": int,
        "age": int, "lifespan": int, "hp": {"cur": int, "max": int},
        "battle_strength": float,  # base strength from the battle system
        "root": Label, "orthodoxy": Label | None, "alignment": Label | None,
        "sect": {"id", "name", "rank"} | None,
        "technique": {"id", "name", "grade", "grade_rank", "attribute"} | None,
        "weapon": {"id", "name", "grade", "grade_rank"} | None,
        "auxiliary": {"id", "name", "grade", "grade_rank"} | None,
        "spirit_stones": int, "relation_count": int,
    }
    Label = {"id": str, "label": str}
    RelationView = {"labels": [str], "numeric_relation": str, "friendliness": int}

The battle section reuses ``src.systems.battle`` directly. Battle resolution in
``decide_battle`` draws against the closed-form ``calc_win_rate``, so the win
probabilities are exact rather than simulated. Nothing here mutates world state.
"""

from __future__ import annotations

from typing import Any

from src.i18n import t
from src.server.services.public_api_contract import raise_public_error

COMPARE_METHOD_CLOSED_FORM = "closed_form"


def _label(item_id: Any, label: Any) -> dict[str, str]:
    return {"id": str(item_id), "label": str(label)}


def _grade_rank(grade: Any, order: tuple) -> int:
    try:
        return order.index(grade)
    except ValueError:
        return 0


def _technique_view(technique: Any) -> dict[str, Any] | None:
    if technique is None:
        return None
    from src.classes.technique import TechniqueGrade

    return {
        "id": str(technique.id),
        "name": str(technique.name),
        "grade": str(technique.grade),
        "grade_rank": _grade_rank(technique.grade, tuple(TechniqueGrade)),
        "attribute": str(technique.attribute),
    }


def _equipment_view(item: Any) -> dict[str, Any] | None:
    if item is None:
        return None
    from src.systems.cultivation import REALM_ORDER

    return {
        "id": str(item.id),
        "name": str(item.name),
        "grade": str(item.realm),
        "grade_rank": _grade_rank(item.realm, REALM_ORDER),
    }


def _sect_view(avatar: Any) -> dict[str, Any] | None:
    sect = getattr(avatar, "sect", None)
    if sect is None:
        return None
    rank = avatar.get_sect_rank_name() if getattr(avatar, "sect_rank", None) is not None else t("Disciple")
    return {"id": str(sect.id), "name": str(sect.name), "rank": str(rank)}


def _relation_states(avatar: Any) -> dict[Any, Any]:
    # Read the dict directly: the relation helpers lazily create missing state.
    relations = getattr(avatar, "relations", None)
    return relations if isinstance(relations, dict) else {}


def _count_relations(avatar: Any) -> int:
    """Count cultivators this avatar has a meaningful (non-stranger) relation with."""
    from src.classes.relation.relation import NumericRelation

    targets = set()
    for other, state in _relation_states(avatar).items():
        if (
            state.blood_relation is not None
            or state.identity_relations
            or state.last_numeric_relation != NumericRelation.STRANGER
        ):
            targets.add(other)
    targets.update((getattr(avatar, "computed_relations", None) or {}).keys())
    return len(targets)


def _relation_view(avatar: Any, other: Any) -> dict[str, Any]:
    from src.classes.relation.relation import RelationState, get_relation_state_labels

    state = _relation_states(avatar).get(other)
    if not isinstance(state, RelationState):
        state = RelationState()
    computed = (getattr(avatar, "computed_relations", None) or {}).get(other)
    return {
        "labels": get_relation_state_labels(avatar, other, state, computed),
        "numeric_relation": state.last_numeric_relation.value,
        "friendliness": int(state.friendliness),
    }


def build_avatar_side(avatar: Any) -> dict[str, Any]:
    from src.classes.root import format_root_cn
    from src.systems.battle import get_base_strength
    from src.systems.cultivation_display import build_avatar_cultivation_display

    progress = avatar.cultivation_progress
    cultivation = build_avatar_cultivation_display(avatar)
    nickname = getattr(avatar, "nickname", None)
    orthodoxy = getattr(avatar, "orthodoxy", None)
    alignment = getattr(avatar, "alignment", None)

    return {
        "id": str(avatar.id),
        "name": str(avatar.name),
        "nickname": nickname.value if nickname else None,
        "realm": _label(progress.realm.value, cultivation["display_realm_name"]),
        "stage": _label(progress.stage.value, cultivation["display_stage_name"]),
        "cultivation_display": cultivation["display_full_name"],
        "level": int(progress.level),
        "age": int(avatar.age.age),
        "lifespan": int(avatar.age.max_lifespan),
        "hp": {"cur": int(avatar.hp.cur), "max": int(avatar.hp.max)},
        "battle_strength": round(float(get_base_strength(avatar)), 1),
        "root": _label(avatar.root.name, format_root_cn(avatar.root)),
        "orthodoxy": _label(orthodoxy.id, t(orthodoxy.name)) if orthodoxy else None,
        "alignment": _label(alignment.value, alignment) if alignment else None,
        "sect": _sect_view(avatar),
        "technique": _technique_view(getattr(avatar, "technique", None)),
        "weapon": _equipment_view(getattr(avatar, "weapon", None)),
        "auxiliary": _equipment_view(getattr(avatar, "auxiliary", None)),
        "spirit_stones": int(avatar.magic_stone.value),
        "relation_count": _count_relations(avatar),
    }


def build_battle_estimate(a: Any, b: Any) -> dict[str, Any]:
    from src.systems.battle import calc_win_rate, get_effective_strength_pair

    a_strength, b_strength = get_effective_strength_pair(a, b)
    return {
        "a_strength": round(float(a_strength), 1),
        "b_strength": round(float(b_strength), 1),
        "a_win_probability": round(float(calc_win_rate(a, b)), 4),
        "b_win_probability": round(float(calc_win_rate(b, a)), 4),
        "method": COMPARE_METHOD_CLOSED_FORM,
    }


def _resolve_living_avatar(world: Any, avatar_id: str) -> Any:
    manager = world.avatar_manager
    avatar = manager.avatars.get(avatar_id)
    if avatar is not None and not getattr(avatar, "is_dead", False):
        return avatar
    if avatar is not None or avatar_id in getattr(manager, "dead_avatars", {}):
        raise_public_error(
            status_code=404,
            code="AVATAR_DEAD",
            message="Avatar is deceased and cannot be compared",
            details={"avatar_id": avatar_id},
        )
    raise_public_error(
        status_code=404,
        code="AVATAR_NOT_FOUND",
        message="Avatar not found",
        details={"avatar_id": avatar_id},
    )


def build_avatar_comparison(world: Any, a_id: str | None, b_id: str | None) -> dict[str, Any]:
    a_key = str(a_id or "").strip()
    b_key = str(b_id or "").strip()
    if not a_key or not b_key:
        raise_public_error(
            status_code=400,
            code="AVATAR_ID_REQUIRED",
            message="Both avatar ids (a and b) are required",
        )
    if a_key == b_key:
        raise_public_error(
            status_code=400,
            code="SAME_AVATAR",
            message="Cannot compare an avatar with itself",
            details={"avatar_id": a_key},
        )

    a = _resolve_living_avatar(world, a_key)
    b = _resolve_living_avatar(world, b_key)

    return {
        "a": build_avatar_side(a),
        "b": build_avatar_side(b),
        "relation": {
            "a_to_b": _relation_view(a, b),
            "b_to_a": _relation_view(b, a),
        },
        "battle": build_battle_estimate(a, b),
    }

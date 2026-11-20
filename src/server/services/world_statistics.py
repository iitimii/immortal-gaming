"""Read-only demographic statistics of the current world.

DTO shape (all labels are localized server-side, ids are stable):

    {
        "living_count": int,
        "realms": [  # every realm in rank order, zero counts included
            {"id": "QI_REFINEMENT", "label": str, "count": int,
             "stages": [{"id": "EARLY_STAGE", "label": str, "count": int}, ...]},
        ],
        "distributions": {  # buckets ordered by count desc, then label
            "race": [Bucket], "sect": [Bucket], "alignment": [Bucket],
            "gender": [Bucket], "orthodoxy": [Bucket],
        },
        "age": {"average": float, "oldest": AvatarRef | None},
        "wealth": {"total": int, "average": float, "richest": AvatarRef | None},
        "deceased": {"total": int, "top_reasons": [Bucket]},
    }

    Bucket = {"id": str, "label": str, "count": int}
    AvatarRef = {"id": str, "name": str, "value": int}
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from src.i18n import t
from src.systems.cultivation import REALM_ORDER, STAGE_ORDER

ROGUE_SECT_ID = "rogue"
UNKNOWN_ID = "unknown"
OTHER_DEATH_REASON_ID = "other"
TOP_DEATH_REASON_LIMIT = 5


def _sorted_buckets(counter: Counter, labels: dict[str, str]) -> list[dict[str, Any]]:
    buckets = [
        {"id": bucket_id, "label": labels.get(bucket_id, bucket_id), "count": count}
        for bucket_id, count in counter.items()
    ]
    buckets.sort(key=lambda item: (-item["count"], item["label"]))
    return buckets


def _count_by(avatars: Iterable[Any], key_fn) -> list[dict[str, Any]]:
    counter: Counter = Counter()
    labels: dict[str, str] = {}
    for avatar in avatars:
        bucket_id, label = key_fn(avatar)
        counter[bucket_id] += 1
        labels.setdefault(bucket_id, label)
    return _sorted_buckets(counter, labels)


def _race_key(avatar: Any) -> tuple[str, str]:
    race = getattr(avatar, "race", None)
    if race is None:
        return UNKNOWN_ID, t("Unknown")
    return str(race.id), str(race)


def _sect_key(avatar: Any) -> tuple[str, str]:
    sect = getattr(avatar, "sect", None)
    if sect is None:
        return ROGUE_SECT_ID, t("Rogue Cultivator")
    return str(sect.id), str(sect.name)


def _alignment_key(avatar: Any) -> tuple[str, str]:
    alignment = getattr(avatar, "alignment", None)
    if alignment is None:
        return UNKNOWN_ID, t("Unknown")
    return str(alignment.value), str(alignment)


def _gender_key(avatar: Any) -> tuple[str, str]:
    gender = getattr(avatar, "gender", None)
    if gender is None:
        return UNKNOWN_ID, t("Unknown")
    return str(gender.value), str(gender)


def _orthodoxy_key(avatar: Any) -> tuple[str, str]:
    orthodoxy = getattr(avatar, "orthodoxy", None)
    if orthodoxy is None:
        return UNKNOWN_ID, t("Unknown")
    return str(orthodoxy.id), t(orthodoxy.name)


def _build_realms(avatars: list[Any]) -> list[dict[str, Any]]:
    counts: Counter = Counter()
    for avatar in avatars:
        progress = getattr(avatar, "cultivation_progress", None)
        if progress is None:
            continue
        counts[(progress.realm, progress.stage)] += 1

    realms: list[dict[str, Any]] = []
    for realm in REALM_ORDER:
        stages = [
            {"id": stage.value, "label": str(stage), "count": counts[(realm, stage)]}
            for stage in STAGE_ORDER
        ]
        realms.append(
            {
                "id": realm.value,
                "label": str(realm),
                "count": sum(stage["count"] for stage in stages),
                "stages": stages,
            }
        )
    return realms


def _avatar_ref(avatar: Any, value: int) -> dict[str, Any]:
    return {"id": str(avatar.id), "name": str(avatar.name), "value": int(value)}


def _build_age_stats(avatars: list[Any]) -> dict[str, Any]:
    if not avatars:
        return {"average": 0.0, "oldest": None}
    ages = [(avatar, int(avatar.age.age)) for avatar in avatars]
    oldest, oldest_age = max(ages, key=lambda item: item[1])
    average = sum(age for _, age in ages) / len(ages)
    return {"average": round(average, 1), "oldest": _avatar_ref(oldest, oldest_age)}


def _build_wealth_stats(avatars: list[Any]) -> dict[str, Any]:
    if not avatars:
        return {"total": 0, "average": 0.0, "richest": None}
    wealth = [(avatar, int(avatar.magic_stone.value)) for avatar in avatars]
    total = sum(amount for _, amount in wealth)
    richest, richest_amount = max(wealth, key=lambda item: item[1])
    return {
        "total": total,
        "average": round(total / len(wealth), 1),
        "richest": _avatar_ref(richest, richest_amount),
    }


def _death_reason_classifier():
    """Map a stored (already localized) death reason string to a stable category."""
    from src.classes.death_reason import DeathReason, DeathType

    exact: dict[str, str] = {}
    for death_type in DeathType:
        if death_type is not DeathType.BATTLE:
            exact[str(DeathReason(death_type))] = death_type.value

    marker = "\x00"
    battle_prefix, _, battle_suffix = str(
        DeathReason(DeathType.BATTLE, killer_name=marker)
    ).partition(marker)

    def classify(reason: str) -> str:
        reason = str(reason or "").strip()
        if not reason:
            return UNKNOWN_ID
        if reason in exact:
            return exact[reason]
        if battle_prefix and reason.startswith(battle_prefix) and reason.endswith(battle_suffix):
            return DeathType.BATTLE.value
        return OTHER_DEATH_REASON_ID

    return classify


def _death_reason_labels() -> dict[str, str]:
    from src.classes.death_reason import DeathType

    return {
        DeathType.OLD_AGE.value: t("Died of old age"),
        DeathType.BATTLE.value: t("Killed in battle"),
        DeathType.SERIOUS_INJURY.value: t("Died from severe injuries"),
        DeathType.HIDDEN_DOMAIN.value: t("Perished in a Hidden Domain"),
        OTHER_DEATH_REASON_ID: t("Other causes"),
        UNKNOWN_ID: t("Unknown reason"),
    }


def _build_deceased_stats(records: list[Any]) -> dict[str, Any]:
    classify = _death_reason_classifier()
    counter: Counter = Counter(classify(getattr(record, "death_reason", "")) for record in records)
    buckets = _sorted_buckets(counter, _death_reason_labels())
    return {"total": len(records), "top_reasons": buckets[:TOP_DEATH_REASON_LIMIT]}


def build_world_statistics(world: Any) -> dict[str, Any]:
    avatars = list(world.avatar_manager.get_living_avatars())
    deceased_manager = getattr(world, "deceased_manager", None)
    records = deceased_manager.get_all_records() if deceased_manager is not None else []

    return {
        "living_count": len(avatars),
        "realms": _build_realms(avatars),
        "distributions": {
            "race": _count_by(avatars, _race_key),
            "sect": _count_by(avatars, _sect_key),
            "alignment": _count_by(avatars, _alignment_key),
            "gender": _count_by(avatars, _gender_key),
            "orthodoxy": _count_by(avatars, _orthodoxy_key),
        },
        "age": _build_age_stats(avatars),
        "wealth": _build_wealth_stats(avatars),
        "deceased": _build_deceased_stats(records),
    }

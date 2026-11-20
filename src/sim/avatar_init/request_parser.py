from __future__ import annotations
from ._shared import *  # noqa: F403
from ._shared import (
    _apply_structural_initial_friendliness,
    _create_manual_innate_lifespan,
    _create_random_innate_lifespan,
)
from .planning import MortalPlanner
from .factory import AvatarFactory
from .relations import RelationApplier

def _parse_gender(value: Union[str, Gender, None]) -> Optional[Gender]:
    if value is None:
        return None
    if isinstance(value, Gender):
        return value
    s = str(value).strip().lower()
    if s in ("male", "m"):
        return Gender.MALE
    if s in ("female", "f"):
        return Gender.FEMALE
    return None


def _parse_sect(value: Union[str, int, Sect, None]) -> Optional[Sect]:
    if value is None:
        return None
    if isinstance(value, Sect):
        return value
    # Pure digits are treated as an id
    if isinstance(value, int):
        return sects_by_id.get(value)
    s = str(value).strip()
    if not s:
        return None
    if s.isdigit():
        return sects_by_id.get(int(s))
    return sects_by_name.get(s)


def _parse_technique(value: Union[str, int, Technique, None]) -> Optional[Technique]:
    if value is None:
        return None
    if isinstance(value, Technique):
        return value
    if isinstance(value, int):
        return techniques_by_id.get(value)
    s = str(value).strip()
    if not s:
        return None
    if s.isdigit():
        return techniques_by_id.get(int(s))
    return techniques_by_name.get(s)


def _parse_weapon(value: Union[str, int, Weapon, None]) -> Optional[Weapon]:
    if value is None:
        return None
    if isinstance(value, Weapon):
        return value
    if isinstance(value, int):
        return weapons_by_id.get(value)
    s = str(value).strip()
    if not s:
        return None
    if s.isdigit():
        return weapons_by_id.get(int(s))
    return weapons_by_name.get(s)


def _parse_auxiliary(value: Union[str, int, Auxiliary, None]) -> Optional[Auxiliary]:
    if value is None:
        return None
    if isinstance(value, Auxiliary):
        return value
    if isinstance(value, int):
        return auxiliaries_by_id.get(value)
    s = str(value).strip()
    if not s:
        return None
    if s.isdigit():
        return auxiliaries_by_id.get(int(s))
    return auxiliaries_by_name.get(s)


def _parse_race(value: Union[str, Race, None]) -> Optional[Race]:
    if value is None:
        return None
    if isinstance(value, Race):
        return value
    s = str(value).strip()
    if not s:
        return None
    return get_race(s)


def _parse_personas(value: Union[str, int, Persona, List[Union[str, int, Persona]], None]) -> Optional[List[Persona]]:
    if value is None:
        return None

    # Normalize into a list; compatible with OmegaConf's ListConfig
    def _as_list(v: object) -> List[object]:
        # A Persona itself is treated as a scalar
        if isinstance(v, Persona):
            return [v]
        # Native sequence
        if isinstance(v, (list, tuple, set)):
            return list(v)
        # Compatible with OmegaConf.ListConfig (if present)
        try:
            from omegaconf import ListConfig  # type: ignore
            if isinstance(v, ListConfig):
                return list(v)
        except Exception:
            pass
        # Other non-string iterables: expand where possible
        if hasattr(v, "__iter__") and not isinstance(v, (str, bytes)):
            try:
                return list(v)  # type: ignore
            except Exception:
                return [v]
        return [v]

    raw_values = _as_list(value)
    values: List[Union[str, int, Persona]] = raw_values  # type: ignore
    result: List[Persona] = []
    for v in values:
        if isinstance(v, Persona):
            result.append(v)
            continue
        if isinstance(v, int):
            p = personas_by_id.get(v)
            if p is not None:
                result.append(p)
            continue
        s = str(v).strip()
        if not s:
            continue
        if s.isdigit():
            p = personas_by_id.get(int(s))
            if p is not None:
                result.append(p)
        else:
            p = personas_by_name.get(s)
            if p is not None:
                result.append(p)
    # Deduplicate while preserving order
    seen: set[int] = set()
    unique: List[Persona] = []
    for p in result:
        if p.id in seen:
            continue
        seen.add(p.id)
        unique.append(p)
    return unique if unique else None


def create_avatar_from_request(
    world: World,
    current_month_stamp: MonthStamp,
    *,
    name: Optional[str] = None,
    age: Union[int, Age, None] = None,
    gender: Union[str, Gender, None] = None,
    sect: Union[str, int, Sect, None] = None,
    level: Optional[int] = None,
    pos: Optional[Tuple[int, int]] = None,
    technique: Union[str, int, Technique, None] = None,
    weapon: Union[str, int, Weapon, None] = None,
    auxiliary: Union[str, int, Auxiliary, None] = None,
    personas: Union[str, int, Persona, List[Union[str, int, Persona]], None] = None,
    appearance: Optional[int] = None,
    race: Union[str, Race, None] = None,
    relations: Optional[List[Dict[str, str]]] = None,
) -> Avatar:
    """
    Avatar creation entry point for the frontend: accepts string/ID params and by default generates no family/friend relations.
    """
    # Age (take an integer age first; planning only uses age.age and does not depend on realm)
    if isinstance(age, Age):
        age_years = age.age
    elif isinstance(age, int):
        age_years = max(AGE_MIN, age)
    else:
        age_years = AGE_MIN

    tmp_age_for_plan = Age(
        age_years,
        CultivationProgress(LEVEL_MIN).realm,
        innate_max_lifespan=_create_random_innate_lifespan(),
    )
    plan = MortalPlanner.plan(world, name=name or "", age=tmp_age_for_plan, allow_relations=False)
    plan.race = get_race("human")

    requested_race = _parse_race(race)
    if requested_race is not None:
        plan.race = requested_race

    # Override: gender
    g = _parse_gender(gender)
    if g is not None:
        plan.gender = g

    # Override: sect
    s = _parse_sect(sect)
    if s is not None:
        plan.sect = s if s.accepts_race(plan.race) else None

    # Override: level
    if isinstance(level, int):
        plan.level = max(LEVEL_MIN, min(LEVEL_MAX, level))

    # Override: coordinates
    if isinstance(pos, tuple) and len(pos) == 2:
        x, y = int(pos[0]), int(pos[1])
        # Clamp to map bounds
        x = max(0, min(world.map.width - 1, x))
        y = max(0, min(world.map.height - 1, y))
        plan.pos_x, plan.pos_y = x, y

    # Derive realm from the final level, then build Age
    final_realm = CultivationProgress(plan.level).realm
    max_age = get_manual_avatar_age_max(final_realm)
    if age_years > max_age:
        raise ManualAvatarAgeLimitError(
            age=age_years,
            max_age=max_age,
            realm=final_realm,
        )
    final_age = Age(
        age_years,
        final_realm,
        innate_max_lifespan=(
            age.innate_max_lifespan
            if isinstance(age, Age)
            else _create_manual_innate_lifespan(age_years, final_realm)
        ),
    )

    # Generate
    overrides: Dict[str, object] = {}
    tech_obj = _parse_technique(technique)
    if tech_obj is not None:
        overrides["technique"] = tech_obj
    weapon_obj = _parse_weapon(weapon)
    if weapon_obj is not None:
        overrides["weapon"] = weapon_obj
    auxiliary_obj = _parse_auxiliary(auxiliary)
    if auxiliary_obj is not None:
        overrides["auxiliary"] = auxiliary_obj
    pers_list = _parse_personas(personas)
    if pers_list:
        overrides["personas"] = pers_list
    if isinstance(appearance, int):
        overrides["appearance"] = appearance

    avatar = AvatarFactory.build_from_plan(
        world,
        current_month_stamp,
        name=name or "",
        age=final_age,
        plan=plan,
        attach_relations=False,
        overrides=overrides if overrides else None,
        allow_random_goldfinger=False,
    )

    if relations:
        for rel_item in relations:
            target_id = rel_item.get('target_id')
            rel_type = rel_item.get('relation')

            if not target_id or not rel_type:
                continue

            # Try converting to a string ID
            t_id_str = str(target_id)
            target = world.avatar_manager.avatars.get(t_id_str)
            if not target:
                continue

            # Parse the relation
            rel_enum = None
            for r in Relation:
                if r.value == rel_type:
                    rel_enum = r
                    break

            if rel_enum:
                avatar.set_relation(target, rel_enum)
                _apply_structural_initial_friendliness(avatar, target, rel_enum)

    return avatar

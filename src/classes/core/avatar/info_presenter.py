"""
Avatar info presentation module

Separates info-formatting logic from the Avatar class into standalone functions.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from src.classes.core.avatar.core import Avatar

from src.systems.battle import get_base_strength
from src.classes.relation.relation import Relation, get_numeric_relation_label, get_relation_label
from src.classes.emotions import EMOTION_EMOJIS, EmotionType
from src.classes.official_rank import OFFICIAL_NONE
from src.utils.config import CONFIG


def _get_goldfinger_structured_payload(avatar: "Avatar") -> dict | None:
    goldfinger = getattr(avatar, "goldfinger", None)
    if goldfinger is None:
        return None

    payload = goldfinger.get_structured_info()
    payload["state"] = dict(getattr(avatar, "goldfinger_state", {}) or {})
    payload["source_of_truth"] = "avatar.goldfinger"
    payload["state_source_of_truth"] = "avatar.goldfinger_state"
    return payload


def _get_race_info(avatar: "Avatar", *, detailed: bool = False) -> dict:
    race = getattr(avatar, "race", None)
    if race is None:
        from src.classes.race import get_race

        race = get_race("human")
    return race.get_info(detailed=detailed)


def _get_race_behavior_desc(avatar: "Avatar") -> str:
    return str(_get_race_info(avatar, detailed=True).get("behavior_desc", "") or "")


def _get_effects_text(avatar: "Avatar") -> str:
    """Get the formatted effects text."""
    from src.i18n import t
    from src.classes.effect import format_effects_to_text
    breakdown = avatar.get_effect_breakdown()
    effect_parts = []
    for source_name, effects in breakdown:
        desc_str = format_effects_to_text(effects)
        if desc_str:
            effect_parts.append(f"[{source_name}] {desc_str}")
    return "\n".join(effect_parts) if effect_parts else t("None")


def _get_goldfinger_detail(avatar: "Avatar", detailed: bool) -> str:
    from src.i18n import t

    goldfinger = getattr(avatar, "goldfinger", None)
    if goldfinger is None:
        return t("None")
    return goldfinger.get_detailed_info() if detailed else goldfinger.get_info()


def _get_fate_revelation(avatar: "Avatar") -> dict | None:
    fate = getattr(avatar, "fate_revelation", None)
    return fate if isinstance(fate, dict) else None


def _get_fate_oracle_text(avatar: "Avatar") -> str:
    fate = _get_fate_revelation(avatar)
    if not fate:
        return ""
    return str(fate.get("oracle_text", "") or "").strip()


def _get_world_secret_knowledge_payload(avatar: "Avatar") -> dict | None:
    from src.systems.world_secret import build_avatar_world_secret_ai_context

    return build_avatar_world_secret_ai_context(avatar)


def get_avatar_info(avatar: "Avatar", detailed: bool = False) -> dict:
    """
    Get avatar info as a dict; detailed controls the granularity.
    """
    from src.i18n import t
    region = avatar.tile.region if avatar.tile is not None else None
    from src.classes.relation.relation import get_relations_strs
    relation_lines = get_relations_strs(avatar, max_lines=8)
    relations_info = t("relation_separator").join(relation_lines) if relation_lines else t("None")
    magic_stone_info = str(avatar.magic_stone)

    born_region_name = t("Unknown")
    if avatar.born_region_id and avatar.born_region_id != -1:
         r = avatar.world.map.regions.get(avatar.born_region_id)
         if r:
             born_region_name = r.name

    from src.classes.core.sect import get_sect_info_with_rank
    
    # [New] Orthodoxy
    orthodoxy_info = t(avatar.orthodoxy.name) if avatar.orthodoxy else t("None")

    if detailed:
        weapon_info = t("{weapon_name}, Proficiency: {proficiency}%", 
                       weapon_name=avatar.weapon.get_detailed_info(), 
                       proficiency=f"{avatar.weapon_proficiency:.1f}") if avatar.weapon else t("None")
        auxiliary_info = avatar.auxiliary.get_detailed_info() if avatar.auxiliary else t("None")
        sect_info = get_sect_info_with_rank(avatar, detailed=True)
        alignment_info = avatar.alignment.get_detailed_info() if avatar.alignment is not None else t("Unknown")
        region_info = region.get_detailed_info() if region is not None else t("None")
        root_info = avatar.root.get_detailed_info()
        technique_info = avatar.technique.get_detailed_info() if avatar.technique is not None else t("None")
        cultivation_info = avatar.cultivation_progress.get_detailed_info()
        personas_info = ", ".join([p.get_detailed_info() for p in avatar.personas]) if avatar.personas else t("None")
        goldfinger_info = _get_goldfinger_detail(avatar, detailed=True)
        materials_info = t("material_separator").join([f"{mat.get_detailed_info()}x{quantity}" for mat, quantity in avatar.materials.items()]) if avatar.materials else t("None")
        appearance_info = avatar.appearance.get_detailed_info(avatar.gender)
        spirit_animal_info = avatar.spirit_animal.get_info() if avatar.spirit_animal is not None else t("None")
    else:
        weapon_info = avatar.weapon.get_info() if avatar.weapon is not None else t("None")
        auxiliary_info = avatar.auxiliary.get_info() if avatar.auxiliary is not None else t("None")
        sect_info = get_sect_info_with_rank(avatar, detailed=False)
        region_info = region.get_info() if region is not None else t("None")
        alignment_info = avatar.alignment.get_info() if avatar.alignment is not None else t("Unknown")
        root_info = avatar.root.get_info()
        technique_info = avatar.technique.get_info() if avatar.technique is not None else t("None")
        cultivation_info = avatar.cultivation_progress.get_info()
        personas_info = ", ".join([p.get_detailed_info() for p in avatar.personas]) if avatar.personas else t("None")
        goldfinger_info = _get_goldfinger_detail(avatar, detailed=False)
        materials_info = t("material_separator").join([f"{mat.get_info()}x{quantity}" for mat, quantity in avatar.materials.items()]) if avatar.materials else t("None")
        appearance_info = avatar.appearance.get_info()
        spirit_animal_info = avatar.spirit_animal.get_info() if avatar.spirit_animal is not None else t("None")

    info_dict = {
        t("Name"): avatar.name,
        t("Origin"): born_region_name,
        t("Race"): _get_race_info(avatar, detailed=detailed).get("name", ""),
        t("Gender"): str(avatar.gender),
        t("Age"): str(avatar.age),
        t("HP"): str(avatar.hp),
        t("Spirit Stones"): magic_stone_info,
        t("Relations"): relations_info,
        t("Sect"): sect_info,
        t("Orthodoxy"): orthodoxy_info,
        t("Alignment"): alignment_info,
        t("Region"): region_info,
        t("Spirit Root"): root_info,
        t("Technique"): technique_info,
        t("Realm"): cultivation_info,
        t("Traits"): personas_info,
        t("Goldfinger"): goldfinger_info,
        t("Fate"): _get_fate_oracle_text(avatar) or t("None"),
        t("Materials"): materials_info,
        t("Appearance"): appearance_info,
        t("Weapon"): weapon_info,
        t("Auxiliary"): auxiliary_info,
        t("Emotion"): t(avatar.emotion.value),
        t("Current Action"): avatar.current_action_name,
        t("Long-term Goal"): avatar.long_term_objective.content if avatar.long_term_objective else t("None"),
        t("Short-term Goal"): avatar.short_term_objective if avatar.short_term_objective else t("None"),
    }
    
    rank_info = avatar.world.ranking_manager.get_avatar_rank(str(avatar.id))
    if rank_info:
        r_type, r_num = rank_info
        
        en_type_map = {"heaven": "Heaven List", "earth": "Earth List", "human": "Human List"}
        list_name = en_type_map.get(r_type, r_type)
        info_dict[t("Ranking")] = f"{list_name} Rank {r_num}"
    
    if detailed:
        info_dict[t("Current Effects")] = _get_effects_text(avatar)
        world_secret_knowledge = _get_world_secret_knowledge_payload(avatar)
        if world_secret_knowledge:
            info_dict["world_secret_knowledge"] = world_secret_knowledge
        race_behavior_desc = _get_race_behavior_desc(avatar)
        if race_behavior_desc:
            info_dict[t("Race Behavior Priority")] = race_behavior_desc
        if avatar.backstory:
            info_dict[t("Backstory")] = avatar.backstory
        fate = _get_fate_revelation(avatar)
        if fate and fate.get("trigger_text"):
            info_dict[t("Fate Revelation")] = str(fate.get("trigger_text", ""))

    # Nickname: shown only when present
    if avatar.nickname is not None:
        info_dict[t("Nickname")] = avatar.nickname.value
    # Spirit animal: shown only when present
    if avatar.spirit_animal is not None:
        info_dict[t("Spirit Animal")] = spirit_animal_info
    return info_dict


def get_avatar_structured_info(avatar: "Avatar") -> dict:
    """
    Get structured avatar info for frontend display and interaction.
    """
    # Basic info
    from src.i18n import t
    from src.classes.observe import get_avatar_observation_radius
    from src.classes.relation.relations import iter_display_relation_entries
    from src.systems.cultivation_display import build_avatar_cultivation_display
    emoji = EMOTION_EMOJIS.get(avatar.emotion, EMOTION_EMOJIS[EmotionType.CALM])
    
    born_region_name = t("Unknown")
    if avatar.born_region_id and avatar.born_region_id != -1:
         r = avatar.world.map.regions.get(avatar.born_region_id)
         if r:
             born_region_name = r.name

    start_age = None
    if avatar.cultivation_start_month_stamp is not None:
        start_age = (int(avatar.cultivation_start_month_stamp) - int(avatar.birth_month_stamp)) // 12

    cultivation_display = build_avatar_cultivation_display(avatar)

    info = {
        "id": avatar.id,
        "name": avatar.name,
        "origin": born_region_name,
        "born_region_id": avatar.born_region_id,
        "race": _get_race_info(avatar, detailed=True),
        "cultivation_start_age": start_age,
        "cultivation_start_month_stamp": int(avatar.cultivation_start_month_stamp) if avatar.cultivation_start_month_stamp else None,
        "gender": str(avatar.gender),
        "age": avatar.age.age,
        "lifespan": avatar.age.max_lifespan,
        "realm": avatar.cultivation_progress.get_info(),
        "realm_id": cultivation_display["realm_id"],
        "stage_id": cultivation_display["stage_id"],
        "cultivation": cultivation_display,
        "level": avatar.cultivation_progress.level,
        "hp": {"cur": avatar.hp.cur, "max": avatar.hp.max},
        "observation_radius": get_avatar_observation_radius(avatar),
        "luck": avatar.luck,
        "alignment": str(avatar.alignment) if avatar.alignment else t("Unknown"),
        "magic_stone": avatar.magic_stone.value,
        "sect_contribution": max(0, int(getattr(avatar, "sect_contribution", 0) or 0)),
        "base_battle_strength": int(get_base_strength(avatar)),
        "official_rank": avatar.get_official_rank_name(),
        "court_reputation": int(getattr(avatar, "court_reputation", 0) or 0),
        "is_official": bool(getattr(avatar, "official_rank", OFFICIAL_NONE) != OFFICIAL_NONE),
        "emotion": {
            "name": t(avatar.emotion.value),
            "emoji": emoji,
            "desc": t(avatar.emotion.value)
        },
        "thinking": avatar.thinking,
        "short_term_objective": avatar.short_term_objective,
        "long_term_objective": avatar.long_term_objective.content if avatar.long_term_objective else "",
        "backstory": avatar.backstory if avatar.backstory else None,
        "fate_revelation": _get_fate_revelation(avatar),
        "nickname": avatar.nickname.value if avatar.nickname else None,
        "nickname_reason": avatar.nickname.reason if avatar.nickname else None,
        "is_dead": avatar.is_dead,
        "death_info": avatar.death_info,
        "action_state": t("Performing {action}", action=avatar.current_action_name)
    }

    rank_info = avatar.world.ranking_manager.get_avatar_rank(str(avatar.id))
    if rank_info:
        info["ranking"] = {"type": rank_info[0], "rank": rank_info[1]}

    # 1. Personas
    info["personas"] = [p.get_structured_info() for p in avatar.personas]

    # 2. Goldfinger
    info["goldfinger"] = _get_goldfinger_structured_payload(avatar)

    # 3. Technique
    if avatar.technique:
        info["technique"] = avatar.technique.get_structured_info()
    else:
        info["technique"] = None

    # 4. Sect
    if avatar.sect:
        sect_info = avatar.sect.get_structured_info()
        if avatar.sect_rank:
            from src.classes.sect_ranks import get_rank_display_name
            sect_info["rank"] = get_rank_display_name(avatar.sect_rank, avatar.sect)
        else:
            sect_info["rank"] = t("Disciple")
        sect_info["contribution"] = max(0, int(getattr(avatar, "sect_contribution", 0) or 0))
        info["sect"] = sect_info
    else:
        info["sect"] = None

    current_month = int(getattr(avatar.world, "month_stamp", 0))
    sect_status_summary = None
    if avatar.sect:
        sect_context = getattr(avatar.world, "sect_context", None)
        active_sects = sect_context.get_active_sects() if sect_context is not None else []
        active_wars = []
        for other in active_sects:
            if other is None or int(getattr(other, "id", 0)) == int(getattr(avatar.sect, "id", 0)):
                continue
            state = avatar.world.get_sect_diplomacy_state(
                int(avatar.sect.id),
                int(other.id),
                current_month=current_month,
            )
            if str(state.get("status", "peace") or "peace") != "war":
                continue
            active_wars.append(
                {
                    "other_sect_id": int(other.id),
                    "other_sect_name": str(getattr(other, "name", "") or ""),
                    "war_months": int(state.get("war_months", 0) or 0),
                    "war_reason": str(state.get("reason", "") or ""),
                    "last_battle_month": state.get("last_battle_month"),
                }
            )
        sect_status_summary = {
            "sect_name": avatar.sect.name,
            "sect_rank": avatar.get_sect_rank_name(),
            "sect_is_at_war": bool(active_wars),
            "active_war_count": len(active_wars),
            "active_wars": active_wars,
            "rule_desc": str(getattr(avatar.sect, "rule_desc", "") or ""),
            "sect_alignment": str(getattr(avatar.sect, "alignment", "") or ""),
            "sect_orthodoxy": str(getattr(getattr(avatar, "orthodoxy", None), "name", "") or ""),
        }
    info["sect_status_summary"] = sect_status_summary
        
    # [New] Orthodoxy
    # Return orthodoxy info whether or not the avatar has a sect (rogue cultivators get the default orthodoxy)
    if avatar.orthodoxy:
        info["orthodoxy"] = avatar.orthodoxy.get_info(detailed=True)
    else:
        info["orthodoxy"] = None
        
    # Extra: alignment details
    from src.classes.alignment import alignment_info_msg_ids
    info["alignment"] = str(avatar.alignment) if avatar.alignment else t("Unknown")
    if avatar.alignment:
        desc_id = alignment_info_msg_ids.get(avatar.alignment, "")
        info["alignment_detail"] = {
            "name": str(avatar.alignment),
            "desc": t(desc_id) if desc_id else "",
        }

    # 5. Equipment (Weapon & Auxiliary)
    if avatar.weapon:
        w_info = avatar.weapon.get_structured_info()
        w_info["proficiency"] = f"{avatar.weapon_proficiency:.1f}%"
        info["weapon"] = w_info
    else:
        info["weapon"] = None
        
    if avatar.auxiliary:
        info["auxiliary"] = avatar.auxiliary.get_structured_info()
    else:
        info["auxiliary"] = None
        
    # 6. Materials
    materials_list = []
    for material, count in avatar.materials.items():
        m_info = material.get_structured_info()
        m_info["count"] = count
        materials_list.append(m_info)
    info["materials"] = materials_list
    
    # 7. Relations
    relations_list = []
    
    # 6.1 Add existing cultivator relations
    existing_ids = set()
    for other, relation_state, relation_scope in iter_display_relation_entries(avatar):
        existing_ids.add(other.id)
        other_death_info = getattr(other, "death_info", None) or {}
        other_sect_name = other.sect.name if other.sect else str(other_death_info.get("sect_name_at_death", "") or t("Rogue Cultivator"))
        blood_label = get_relation_label(relation_state.blood_relation, avatar, other) if relation_state.blood_relation else None
        identity_labels = [
            get_relation_label(rel, avatar, other)
            for rel in sorted(relation_state.identity_relations, key=lambda item: item.value)
        ]
        numeric_relation = relation_state.last_numeric_relation
        relations_list.append({
            "target_id": other.id,
            "name": other.name,
            "relation": " / ".join(filter(None, [blood_label, *identity_labels, get_numeric_relation_label(numeric_relation)])),
            "relation_type": relation_state.blood_relation.value if relation_state.blood_relation else "",
            "blood_relation": relation_state.blood_relation.value if relation_state.blood_relation else None,
            "identity_relations": [rel.value for rel in sorted(relation_state.identity_relations, key=lambda item: item.value)],
            "numeric_relation": numeric_relation.value,
            "friendliness": relation_state.friendliness,
            "realm": other.cultivation_progress.get_info(),
            "cultivation": build_avatar_cultivation_display(other),
            "sect": other_sect_name,
            "is_mortal": False,
            "target_gender": other.gender.value,
            "is_dead": bool(getattr(other, "is_dead", False)),
            "relation_scope": relation_scope,
        })

    for other, relation in avatar.computed_relations.items():
        if other.id in existing_ids:
            continue
        relations_list.append({
            "target_id": other.id,
            "name": other.name,
            "relation": get_relation_label(relation, avatar, other),
            "relation_type": relation.value,
            "blood_relation": relation.value if relation in {
                Relation.IS_PARENT_OF,
                Relation.IS_CHILD_OF,
                Relation.IS_SIBLING_OF,
                Relation.IS_KIN_OF,
                Relation.IS_GRAND_PARENT_OF,
                Relation.IS_GRAND_CHILD_OF,
            } else None,
            "identity_relations": [],
            "numeric_relation": None,
            "friendliness": 0,
            "realm": other.cultivation_progress.get_info(),
            "cultivation": build_avatar_cultivation_display(other),
            "sect": other.sect.name if other.sect else t("Rogue Cultivator"),
            "is_mortal": False,
            "target_gender": other.gender.value,
            "is_dead": bool(getattr(other, "is_dead", False)),
            "relation_scope": "computed",
        })
    
    # 6.2 [New] Add mortal children
    from src.classes.relation.relation import GENDERED_DISPLAY
    for child in avatar.children:
        if child.id not in existing_ids:
            # Mortal children: Owner is Parent -> relation should be Relation.PARENT
            # Label should be Son/Daughter
            gender_val = child.gender.value
            # Find the matching translation key (Relation.PARENT, "male") -> "relation_son"
            label_key = GENDERED_DISPLAY.get((Relation.IS_CHILD_OF, gender_val), "child")
            
            relations_list.append({
                "target_id": child.id,
                "name": child.name,
                "relation": t(label_key), 
                "relation_type": Relation.IS_CHILD_OF.value, # The type here should be CHILD (Target is Child)
                "realm": t("Mortal"),
                "sect": t("None"),
                "is_mortal": True,
                "target_gender": gender_val,
                "is_dead": False,
                "relation_scope": "mortal_child",
            })

    info["relations"] = relations_list
    
    # 8. Appearance
    info["appearance"] = avatar.appearance.get_info()
    
    # 9. Spiritual root
    from src.classes.root import format_root_cn
    root_str = format_root_cn(avatar.root)
    info["root"] = root_str
    info["root_detail"] = {
         "name": root_str,
         "desc": t("Contains elements: {elements}", elements=t("element_separator").join(str(e) for e in avatar.root.elements)),
         "effect_desc": avatar.root.effect_desc
    }
    
    # 10. Spirit animal
    if avatar.spirit_animal:
         info["spirit_animal"] = avatar.spirit_animal.get_structured_info()

    # Current effects
    effects_text = _get_effects_text(avatar)
    info["current_effects"] = effects_text
    info[t("Current Effects")] = effects_text
    info["world_secret_knowledge"] = _get_world_secret_knowledge_payload(avatar)

    return info


def get_avatar_ai_context(
    avatar: "Avatar",
    co_region_avatars: Optional[List["Avatar"]] = None,
) -> dict:
    from src.classes.core.avatar.prompt_context import build_avatar_prompt_context

    return build_avatar_prompt_context(avatar, co_region_avatars=co_region_avatars)


def get_avatar_expanded_info(
    avatar: "Avatar", 
    co_region_avatars: Optional[List["Avatar"]] = None,
    other_avatar: Optional["Avatar"] = None,
    detailed: bool = False
) -> dict:
    """
    Get extended avatar info, including basic info, observed avatars and event history.
    
    Args:
        avatar: target avatar
        co_region_avatars: other avatars in the same region, used for the "observed avatars" field
        other_avatar: another avatar; if given, return events the two shared, otherwise single-avatar events
        detailed: whether to return detailed info
    """
    from src.i18n import t
    from src.systems.cultivation_display import build_avatar_cultivation_display
    info = get_avatar_info(avatar, detailed=detailed)

    observed: list[str] = []
    if co_region_avatars:
        for other in co_region_avatars[:8]:
            cultivation = build_avatar_cultivation_display(other)
            observed.append(t("{name}, Realm: {realm}", name=other.name, realm=cultivation["display_full_name"]))

    # History events are now queried by category from the global event manager
    em = avatar.world.event_manager
    major_limit = CONFIG.social.major_event_context_num
    minor_limit = CONFIG.social.minor_event_context_num
    
    # Decide between single-avatar and shared events depending on other_avatar
    if other_avatar is not None:
        major_events = em.get_major_events_between(avatar.id, other_avatar.id, limit=major_limit)
        minor_events = em.get_minor_events_between(avatar.id, other_avatar.id, limit=minor_limit)
    else:
        major_events = em.get_major_events_by_avatar(avatar.id, limit=major_limit)
        minor_events = em.get_minor_events_by_avatar(avatar.id, limit=minor_limit)
    
    major_list = [str(e) for e in major_events]
    minor_list = [str(e) for e in minor_events]

    info[t("Nearby Avatars")] = observed
    info[t("Major Events")] = major_list
    info[t("Recent Events")] = minor_list
    info["goldfinger_context"] = _get_goldfinger_structured_payload(avatar)
    info["world_secret_knowledge"] = _get_world_secret_knowledge_payload(avatar)
    return info


def get_other_avatar_info(from_avatar: "Avatar", to_avatar: "Avatar") -> str:
    from src.classes.core.avatar.text_presenter import build_other_avatar_text

    return build_other_avatar_text(from_avatar, to_avatar)


def get_avatar_desc(avatar: "Avatar", detailed: bool = False) -> str:
    from src.classes.core.avatar.text_presenter import build_avatar_description_text

    return build_avatar_description_text(avatar, detailed=detailed)

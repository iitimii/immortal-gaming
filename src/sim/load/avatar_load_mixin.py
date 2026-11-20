"""
Avatar load (deserialization) mixin

Separates Avatar deserialization logic from avatar.py.

Load strategy:
- Two-phase load: first load all Avatars (relations left empty), then rebuild the relations network
- Referenced objects: fetched from global dicts by id (e.g. techniques_by_id)
- weapon/auxiliary: shallow-copied, then special_data restored (avoids recursion/crash risks of deepcopy)
- Fault tolerance: missing referenced objects are skipped instead of crashing
"""
from typing import TYPE_CHECKING
import copy

if TYPE_CHECKING:
    from src.classes.core.world import World


class AvatarLoadMixin:
    """Avatar load (deserialization) mixin
    
    Provides the from_save_dict classmethod to rebuild an Avatar object from a dict
    """
    
    @classmethod
    def from_save_dict(cls, data: dict, world: "World") -> "AvatarLoadMixin":
        """Rebuild an Avatar from a dict (used when loading a save)
        
        Note: relations must be rebuilt separately after all Avatars have been loaded
        
        Args:
            data: save data dict
            world: world object reference
            
        Returns:
            The rebuilt Avatar object (relations empty; filled in by an external second phase)
        """
        from src.classes.core.avatar import Gender
        from src.systems.time import MonthStamp
        from src.systems.cultivation import Realm, CultivationProgress
        from src.classes.age import Age
        from src.classes.hp import HP
        from src.classes.technique import techniques_by_id
        from src.classes.material import materials_by_id
        from src.classes.items.weapon import weapons_by_id
        from src.classes.items.auxiliary import auxiliaries_by_id
        from src.classes.core.sect import sects_by_id
        from src.classes.sect_ranks import SectRank
        from src.classes.root import Root
        from src.classes.alignment import Alignment
        from src.classes.persona import personas_by_id
        from src.classes.goldfinger import goldfingers_by_id
        from src.classes.race import get_race
        from src.classes.appearance import get_appearance_by_level
        from src.classes.items.magic_stone import MagicStone
        from src.classes.action_runtime import ActionPlan
        from src.classes.items.elixir import elixirs_by_id, ConsumedElixir
        from src.classes.avatar_metrics import AvatarMetrics
        
        # Rebuild basic objects
        gender = Gender(data["gender"])
        birth_month_stamp = MonthStamp(data["birth_month_stamp"])
        
        # Rebuild cultivation progress
        cultivation_progress = CultivationProgress.from_dict(data["cultivation_progress"])
        realm = cultivation_progress.realm
        
        # Rebuild age
        age = Age.from_dict(data["age"], realm)
        
        # Create the Avatar (incomplete, filled in below)
        avatar = cls(
            world=world,
            name=data["name"],
            id=data["id"],
            birth_month_stamp=birth_month_stamp,
            age=age,
            gender=gender,
            cultivation_progress=cultivation_progress,
            pos_x=data["pos_x"],
            pos_y=data["pos_y"],
        )
        avatar.born_region_id = data.get("born_region_id")
        stamp_val = data.get("cultivation_start_month_stamp")
        avatar.cultivation_start_month_stamp = MonthStamp(stamp_val) if stamp_val is not None else None
        
        # Set spirit root
        avatar.root = Root[data["root"]]
        avatar.race = get_race(data["race_id"])
        
        # Set technique
        technique_id = data.get("technique_id")
        if technique_id is not None:
            avatar.technique = techniques_by_id.get(technique_id)
        
        # Set HP
        avatar.hp = HP.from_dict(data["hp"])
        
        # Set items and resources
        avatar.magic_stone = MagicStone(data.get("magic_stone", 0))
        
        # Rebuild materials (compatible with legacy saves' items)
        materials_dict = data.get("materials") or data.get("items") or {}
        avatar.materials = {}
        for mat_id_str, quantity in materials_dict.items():
            mat_id = int(mat_id_str)
            if mat_id in materials_by_id:
                avatar.materials[materials_by_id[mat_id]] = quantity
        
        # Rebuild weapon
        # Use copy instead of deepcopy to avoid crashes from potential recursive references; it is also faster
        # special_data is instance-specific and must be assigned separately
        weapon_id = data.get("weapon_id")
        if weapon_id is not None and weapon_id in weapons_by_id:
            # Shallow copy: copies references, but weapon.special_data would be shared
            # so special_data must be reassigned manually
            weapon_proto = weapons_by_id[weapon_id]
            avatar.weapon = copy.copy(weapon_proto)
            avatar.weapon.special_data = data.get("weapon_special_data", {})
        
        # Restore weapon proficiency
        avatar.weapon_proficiency = float(data.get("weapon_proficiency", 0.0))
        
        # Rebuild auxiliary
        # Same as above, use copy
        auxiliary_id = data.get("auxiliary_id")
        if auxiliary_id is not None and auxiliary_id in auxiliaries_by_id:
            auxiliary_proto = auxiliaries_by_id[auxiliary_id]
            avatar.auxiliary = copy.copy(auxiliary_proto)
            avatar.auxiliary.special_data = data.get("auxiliary_special_data", {})
        
        # Rebuild spirit_animal
        spirit_animal_data = data.get("spirit_animal")
        if spirit_animal_data is not None:
            from src.classes.spirit_animal import SpiritAnimal
            spirit_realm = Realm[spirit_animal_data["realm"]]
            avatar.spirit_animal = SpiritAnimal(
                name=spirit_animal_data["name"],
                realm=spirit_realm
            )
        
        # Set social info and status
        sect_id = data.get("sect_id")
        if sect_id is not None:
            avatar.sect = sects_by_id.get(sect_id)
        
        sect_rank_value = data.get("sect_rank")
        if sect_rank_value is not None:
            avatar.sect_rank = SectRank(sect_rank_value)
        avatar.sect_contribution = max(0, int(data.get("sect_contribution", 0) or 0))
        
        alignment_name = data.get("alignment")
        if alignment_name is not None:
            avatar.alignment = Alignment[alignment_name]
        
        # Rebuild personas
        persona_ids = data.get("persona_ids", [])
        avatar.personas = [personas_by_id[pid] for pid in persona_ids if pid in personas_by_id]
        goldfinger_id = data.get("goldfinger_id")
        avatar.goldfinger = goldfingers_by_id.get(goldfinger_id) if goldfinger_id is not None else None
        avatar.goldfinger_state = dict(data.get("goldfinger_state", {}) or {})
        avatar.official_rank = str(data.get("official_rank", "NONE") or "NONE")
        avatar.court_reputation = int(data.get("court_reputation", 0) or 0)
        last_governance_month = data.get("last_governance_month")
        avatar.last_governance_month = int(last_governance_month) if last_governance_month is not None else None
        
        # Set appearance (get the full Appearance object from its level)
        avatar.base_appearance = get_appearance_by_level(data.get("appearance", 5))

        # Restore nickname
        from src.classes.nickname_data import Nickname
        avatar.nickname = Nickname.from_dict(data.get("nickname"))

        # Restore backstory
        avatar.backstory = data.get("backstory")
        avatar.fate_revelation = data.get("fate_revelation")

        # Restore emotion
        from src.classes.emotions import EmotionType
        emotion_str = data.get("emotion", "emotion_calm")
        try:
            avatar.emotion = EmotionType(emotion_str)
        except ValueError:
            avatar.emotion = EmotionType.CALM

        # Restore death state
        avatar.is_dead = data.get("is_dead", False)
        avatar.death_info = data.get("death_info")
        
        # Set actions and AI
        avatar.thinking = data.get("thinking", "")
        avatar.short_term_objective = data.get("short_term_objective", "")
        avatar._action_cd_last_months = data.get("_action_cd_last_months", {})
        avatar.known_regions = set(data.get("known_regions", []))
        from src.classes.world_secret import deserialize_avatar_world_secret_knowledge
        avatar.world_secret_knowledge = deserialize_avatar_world_secret_knowledge(data.get("world_secret_knowledge"))
        
        # Load long-term objective
        long_term_objective_data = data.get("long_term_objective")
        if long_term_objective_data:
            from src.classes.long_term_objective import LongTermObjective
            avatar.long_term_objective = LongTermObjective(
                content=long_term_objective_data.get("content", ""),
                origin=long_term_objective_data.get("origin", "llm"),
                set_year=long_term_objective_data.get("set_year", 100)
            )
        else:
            avatar.long_term_objective = None
        
        # Rebuild planned_actions
        planned_actions_data = data.get("planned_actions", [])
        avatar.planned_actions = [ActionPlan.from_dict(plan_data) for plan_data in planned_actions_data]
        
        # Rebuild current_action (if any)
        current_action_dict = data.get("current_action")
        if current_action_dict is not None:
            try:
                action = avatar.create_action(current_action_dict["action_name"])
                
                # Restore the action's internal state
                if "state" in current_action_dict:
                    action.load_save_data(current_action_dict["state"])
                
                from src.classes.action_runtime import ActionInstance
                avatar.current_action = ActionInstance(
                    action=action,
                    params=current_action_dict["params"],
                    status=current_action_dict["status"]
                )
            except Exception:
                # If the action cannot be rebuilt, skip it (fault tolerance)
                avatar.current_action = None
        
        # relations must be rebuilt externally (all avatars need to be loaded first)
        avatar.relations = {}
        avatar.archived_relations = {}
        
        # Restore elixir records
        elixir_list_data = data.get("elixirs", [])
        avatar.elixirs = []
        for elixir_data in elixir_list_data:
            elixir_id = elixir_data["id"]
            if elixir_id in elixirs_by_id:
                elixir_obj = elixirs_by_id[elixir_id]
                consume_time = elixir_data["time"]
                avatar.elixirs.append(ConsumedElixir(elixir_obj, consume_time))

        # Restore temporary effects
        avatar.temporary_effects = data.get("temporary_effects", [])
        avatar.persistent_effects = data.get("persistent_effects", [])

        # Rebuild metrics_history
        metrics_history_data = data.get("metrics_history", [])
        avatar.metrics_history = [
            AvatarMetrics.from_save_dict(metrics_data)
            for metrics_data in metrics_history_data
        ]
        avatar.enable_metrics_tracking = data.get("enable_metrics_tracking", False)

        # Restore children
        children_data = data.get("children", [])
        from src.classes.mortal import Mortal
        avatar.children = [Mortal.from_dict(child_data) for child_data in children_data]
        avatar.relation_start_dates = data.get("relation_start_dates", {})

        # Recalculate effects after loading (ensures correct values)
        avatar.recalc_effects()
        
        return avatar

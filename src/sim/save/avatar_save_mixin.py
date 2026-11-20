"""
Avatar save (serialization) mixin

Separates Avatar serialization logic from avatar.py to keep the core class clean.

Save strategy:
- Referenced objects (Technique, Material, etc.): save the id; fetch from global dicts on load
- relations: converted to dict[str, str] (avatar_id -> relation_value)
- materials: converted to dict[int, int] (material_id -> quantity)
- current_action: save the action class name and params
- weapon/auxiliary: need a deep copy (special_data is instance-specific)
"""


class AvatarSaveMixin:
    """Avatar save (serialization) mixin
    
    Provides the to_save_dict method, converting an Avatar into a JSON-serializable dict
    """
    
    def to_save_dict(self) -> dict:
        """Convert to a serializable dict (used for saving)
        
        Returns:
            A dict containing the Avatar's full state, directly JSON-serializable
        """
        # Serialize relations: dict[Avatar, Relation] -> dict[str, str]
        relations_dict = {
            other.id: relation_state.to_save_dict()
            for other, relation_state in self.relations.items()
        }
        archived_relations_dict = {
            other.id: relation_state.to_save_dict()
            for other, relation_state in getattr(self, "archived_relations", {}).items()
        }
        
        # Serialize materials: dict[Material, int] -> dict[int, int]
        materials_dict = {
            material.id: quantity
            for material, quantity in self.materials.items()
        }
        
        # Serialize current_action
        current_action_dict = None
        if self.current_action is not None:
            current_action_dict = {
                "action_name": self.current_action.action.__class__.__name__,
                "params": self.current_action.params,
                "status": self.current_action.status,
                "state": self.current_action.action.get_save_data()
            }
        
        # Serialize planned_actions
        planned_actions_list = [plan.to_dict() for plan in self.planned_actions]

        from src.classes.world_secret import serialize_avatar_world_secret_knowledge
        
        # Serialize spirit_animal
        spirit_animal_dict = None
        if self.spirit_animal is not None:
            spirit_animal_dict = {
                "name": self.spirit_animal.name,
                "realm": self.spirit_animal.realm.name
            }
        
        return {
            # Basic info
            "id": self.id,
            "name": self.name,
            "birth_month_stamp": int(self.birth_month_stamp),
            "gender": self.gender.value,
            "race_id": getattr(getattr(self, "race", None), "id", "human"),
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
            "born_region_id": self.born_region_id,
            "cultivation_start_month_stamp": int(self.cultivation_start_month_stamp) if self.cultivation_start_month_stamp is not None else None,
            
            # Cultivation
            "age": self.age.to_dict(),
            "cultivation_progress": self.cultivation_progress.to_dict(),
            "root": self.root.name,
            "technique_id": self.technique.id if self.technique else None,
            "hp": self.hp.to_dict(),
            
            # Items and resources
            "magic_stone": self.magic_stone.value,
            "materials": materials_dict,
            "weapon_id": self.weapon.id if self.weapon else None,
            "weapon_special_data": self.weapon.special_data if self.weapon else {},
            "weapon_proficiency": self.weapon_proficiency,
            "auxiliary_id": self.auxiliary.id if self.auxiliary else None,
            "auxiliary_special_data": self.auxiliary.special_data if self.auxiliary else {},
            "spirit_animal": spirit_animal_dict,
            
            # Social info and status
            "relations": relations_dict,
            "archived_relations": archived_relations_dict,
            "sect_id": self.sect.id if self.sect else None,
            "sect_rank": self.sect_rank.value if self.sect_rank else None,
            "sect_contribution": int(getattr(self, "sect_contribution", 0) or 0),
            "alignment": self.alignment.name if self.alignment else None,
            "persona_ids": [p.id for p in self.personas] if self.personas else [],
            "goldfinger_id": self.goldfinger.id if getattr(self, "goldfinger", None) else None,
            "goldfinger_state": dict(getattr(self, "goldfinger_state", {}) or {}),
            "official_rank": self.official_rank,
            "court_reputation": self.court_reputation,
            "last_governance_month": self.last_governance_month,
            "appearance": self.base_appearance.level,
            "nickname": self.nickname.to_dict() if self.nickname else None,
            "backstory": self.backstory,
            "fate_revelation": self.fate_revelation,
            "emotion": self.emotion.value,
            "is_dead": self.is_dead,
            "death_info": self.death_info,
            
            # Actions and AI
            "current_action": current_action_dict,
            "planned_actions": planned_actions_list,
            "thinking": self.thinking,
            "short_term_objective": self.short_term_objective,
            "long_term_objective": {
                "content": self.long_term_objective.content,
                "origin": self.long_term_objective.origin,
                "set_year": self.long_term_objective.set_year
            } if self.long_term_objective else None,
            "_action_cd_last_months": self._action_cd_last_months,
            "known_regions": list(self.known_regions),
            "world_secret_knowledge": serialize_avatar_world_secret_knowledge(self),

            # State tracking
            "metrics_history": [
                metrics.to_save_dict()
                for metrics in self.metrics_history
            ] if self.enable_metrics_tracking else [],
            "enable_metrics_tracking": self.enable_metrics_tracking,

            # Elixirs
            "elixirs": [
                {
                    "id": consumed.elixir.id,
                    "time": consumed.consume_time
                }
                for consumed in self.elixirs
            ],
            "temporary_effects": self.temporary_effects,
            "persistent_effects": self.persistent_effects,
            
            # Reproduction
            "children": [child.to_dict() for child in self.children],
            "relation_start_dates": self.relation_start_dates,
        }

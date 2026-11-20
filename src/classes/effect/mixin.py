"""
Avatar effects mixin

Computes and applies avatar effects.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.classes.core.avatar.core import Avatar

from .process import _merge_effects, _evaluate_conditional_effect
from .luck import build_luck_derived_effects, compute_luck_value
from .consts import EXTRA_LUCK
from src.classes.hp import HP_MAX_BY_REALM


class EffectsMixin:
    """Effect computation methods"""
    
    def get_active_temporary_effects(self: "Avatar") -> list[dict[str, Any]]:
        """Return the list of currently active temporary effects"""
        current_month = int(self.world.month_stamp)
        return [
            eff for eff in getattr(self, "temporary_effects", [])
            if current_month < eff.get("start_month", 0) + eff.get("duration", 0)
        ]

    def _evaluate_values(self, effects: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluate dynamic values (string expressions) in an effects dict.
        Supports explicit 'eval(...)' as well as implicit expressions containing 'avatar.'.
        """
        result = {}
        # Safe eval context
        context = {
            "__builtins__": {},
            "avatar": self,
            "max": max,
            "min": min,
            "int": int,
            "float": float,
            "round": round,
        }
        try:
            from src.classes.items.auxiliary import get_ten_thousand_souls_banner_bonus
            context["get_ten_thousand_souls_banner_bonus"] = get_ten_thousand_souls_banner_bonus
        except Exception:
            pass

        for k, v in effects.items():
            if isinstance(v, str):
                s = v.strip()
                expr = None
                
                # Check whether this is an expression
                if s.startswith("eval(") and s.endswith(")"):
                    expr = s[5:-1]
                elif "avatar." in s: # Heuristic: anything containing avatar. is treated as an expression
                    expr = s
                
                if expr:
                    try:
                        result[k] = eval(expr, context)
                    except Exception:
                        # Evaluation failed: keep the original value (a plain string, or a broken expression)
                        result[k] = v
                else:
                    result[k] = v
            else:
                result[k] = v
        return result

    @property
    def effects(self: "Avatar") -> dict[str, object]:
        """
        Merge effects from every source: sect, technique, spirit root, traits, weapon, auxiliary, spirit animal, heaven-and-earth phenomenon, elixirs.
        Reuses get_effect_breakdown directly so what is displayed matches what applies.
        """
        merged: dict[str, object] = {}

        # We only need to merge the results
        for _, effect_dict in self.get_effect_breakdown():
            merged = _merge_effects(merged, effect_dict)

        return merged

    def _get_raw_effect_breakdown(self: "Avatar") -> list[tuple[str, dict[str, Any]]]:
        """
        Return the raw effect breakdown before luck-derived effects are injected.
        """
        from src.i18n import t
        breakdown = []
        
        def _collect(name: str, source_obj=None, explicit_effects=None):
            """
            Collect effects.
            source_obj: object that has .effects
            explicit_effects: effects passed in directly (dict or list)
            """
            raw_effects = explicit_effects
            if raw_effects is None and source_obj is not None:
                raw_effects = getattr(source_obj, "effects", {})
                
            if not raw_effects:
                return

            # 1. Evaluate conditions (when)
            evaluated = _evaluate_conditional_effect(raw_effects, self)
            # 2. Evaluate dynamic values (expressions)
            evaluated = self._evaluate_values(evaluated)
            
            if evaluated:
                breakdown.append((name, evaluated))

        # Collect in priority / logical order (translated labels)
        if self.sect:
            label = t("Sect [{name}]", name=self.sect.name)
            _collect(label, source_obj=self.sect)
        else:
            # Rogue cultivators get the default orthodoxy effects
            from src.classes.core.orthodoxy import get_orthodoxy
            sanxiu_orthodoxy = get_orthodoxy("sanxiu")
            if sanxiu_orthodoxy:
                label = t("Orthodoxy [{name}]", name=t(sanxiu_orthodoxy.name))
                _collect(label, source_obj=sanxiu_orthodoxy)

        if getattr(self, "race", None):
            label = t("Race [{name}]", name=str(self.race))
            _collect(label, source_obj=self.race)
            
        if self.technique:
            label = t("Technique [{name}]", name=self.technique.name)
            _collect(label, source_obj=self.technique)
            
        if self.root:
            _collect(t("Spirit Root"), source_obj=self.root)

        from src.classes.official_rank import OFFICIAL_NONE, get_official_effects, get_official_rank_name
        if getattr(self, "official_rank", OFFICIAL_NONE) != OFFICIAL_NONE:
            label = t("Official Rank [{name}]", name=get_official_rank_name(self.official_rank))
            _collect(label, explicit_effects=get_official_effects(self.official_rank))
            
        for p in self.personas:
            label = t("Trait [{name}]", name=p.name)
            _collect(label, source_obj=p)

        if getattr(self, "goldfinger", None):
            label = f"Goldfinger [{self.goldfinger.name}]"
            _collect(label, source_obj=self.goldfinger)
            
        if self.weapon:
            label = t("Weapon [{name}]", name=self.weapon.name)
            _collect(label, source_obj=self.weapon)
            
        if self.auxiliary:
            label = t("Auxiliary [{name}]", name=self.auxiliary.name)
            _collect(label, source_obj=self.auxiliary)
            
        if self.spirit_animal:
            label = t("Spirit Animal [{name}]", name=self.spirit_animal.name)
            _collect(label, source_obj=self.spirit_animal)
            
        if self.world.current_phenomenon:
            _collect(t("Heaven and Earth Phenomenon"), source_obj=self.world.current_phenomenon)

        realm_effects = self.cultivation_progress.get_realm_effects()
        if realm_effects:
            _collect(t("effect_source_cultivation_realm"), explicit_effects=realm_effects)

        for consumed in self.elixirs:
            # Use get_active_effects to get the currently active effects
            active = consumed.get_active_effects(int(self.world.month_stamp))
            label = t("Elixir [{name}]", name=consumed.elixir.name)
            _collect(label, explicit_effects=active)

        for persistent_eff in getattr(self, "persistent_effects", []):
            label = t(persistent_eff.get("source", "effect_source_persistent_effect"))
            _collect(label, explicit_effects=persistent_eff.get("effects", {}))

        # Temporary effects (e.g. short-term bonuses from secluded cultivation)
        for temp_eff in self.get_active_temporary_effects():
            # Source label, translatable
            source_key = temp_eff.get("source", "Unknown")
            label = t(source_key)
            _collect(label, explicit_effects=temp_eff.get("effects", {}))

        return breakdown

    @property
    def luck(self: "Avatar") -> float:
        raw_merged: dict[str, object] = {}
        for _, effect_dict in self._get_raw_effect_breakdown():
            raw_merged = _merge_effects(raw_merged, effect_dict)
        return compute_luck_value(getattr(self, "luck_base", 0), raw_merged)

    def get_effect_breakdown(self: "Avatar") -> list[tuple[str, dict[str, Any]]]:
        """
        Return the final effect breakdown as [(source name, effective effects dict), ...].
        In addition to the raw sources, a luck-derived effects source is inserted.
        """
        from src.i18n import t

        breakdown = self._get_raw_effect_breakdown()
        raw_merged: dict[str, object] = {}
        for _, effect_dict in breakdown:
            raw_merged = _merge_effects(raw_merged, effect_dict)

        luck_value = compute_luck_value(getattr(self, "luck_base", 0), raw_merged)
        derived_effects = build_luck_derived_effects(luck_value)
        if derived_effects:
            breakdown.append((t("Luck"), derived_effects))

        return breakdown

    def recalc_effects(self: "Avatar") -> None:
        """
        Recalculate all long-term effects.
        Called on equipment changes, realm breakthroughs, etc.
        
        Currently covers:
        - max HP
        - max lifespan
        """
        # Compute the base maximum (by realm)
        base_max_hp = HP_MAX_BY_REALM.get(self.cultivation_progress.realm, 100)
        
        # Accessing self.effects triggers the @property and re-merges all effects
        effects = self.effects
        extra_max_hp = int(effects.get("extra_max_hp", 0))
        extra_max_lifespan = int(effects.get("extra_max_lifespan", 0))
        
        # Compute the new maximum
        new_max_hp = base_max_hp + extra_max_hp
        
        # Update the maximum
        self.hp.max = new_max_hp
        
        # Update lifespan
        if self.age:
            self.age.recalculate_max_lifespan(extra_max_lifespan)
        
        # Clamp the current value to the new maximum
        if self.hp.cur > new_max_hp:
            self.hp.cur = new_max_hp

    def update_time_effect(self: "Avatar") -> None:
        """
        Passive effects that update over time.
        Current behavior: while HP is not full, recover 1% of max HP (scaled by the HP recovery rate bonus).
        """
        if self.hp.cur < self.hp.max:
            base_recover = self.hp.max * 0.01
            
            # Apply the HP recovery rate bonus
            recovery_rate_raw = self.effects.get("extra_hp_recovery_rate", 0.0)
            recovery_rate = float(recovery_rate_raw or 0.0)
            from src.systems.formation import get_region_formation_effect_value

            recovery_rate += float(get_region_formation_effect_value(self, "extra_hp_recovery_rate", 0.0) or 0.0)
            recovery_rate_multiplier = 1.0 + recovery_rate
            
            recover_amount = int(base_recover * recovery_rate_multiplier)
            self.hp.recover(recover_amount)

    @property
    def move_step_length(self: "Avatar") -> int:
        """Return the avatar's move step length"""
        return self.cultivation_progress.get_move_step()

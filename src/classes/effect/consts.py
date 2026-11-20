"""
Effects system
==============

This file defines every valid effect field in the game.
Effects are merged and applied through the avatar.effects property.

Effect sources:
- Sect (sect)
- Technique (technique)
- Spirit root (root)
- Trait (persona)
- Weapon and auxiliary equipment (weapon, auxiliary)
"""

# =============================================================================
# Effect constant definitions
# =============================================================================

# --- Combat ---
EXTRA_BATTLE_STRENGTH_POINTS = "extra_battle_strength_points"
"""
Extra battle strength points
Type: int
Applied in: src/classes/battle.py
Notes: Directly increases the avatar's battle strength.
Reference values:
  - Minor: 1~2 (about 1-2 minor stages)
  - Moderate: 3~5 (about half a major realm)
  - Major: 8+ (about one major realm)
"""

EXTRA_MAX_HP = "extra_max_hp"
"""
Extra max HP
Type: int
Applied in: src/classes/avatar.py (__post_init__)
Notes: Raises the avatar's maximum HP.
Reference values:
  - Minor: 10~30
  - Moderate: 50~100 (base HP in Qi Refinement is about 100)
  - Major: 150+
"""

EXTRA_OBSERVATION_RADIUS = "extra_observation_radius"
"""
Extra observation radius
Type: int
Applied in: src/classes/observe.py
Notes: Increases the avatar's observation range (in tiles).
Reference values:
  - Minor: 1
  - Moderate: 2
  - Major: 3
"""

EXTRA_APPEARANCE = "extra_appearance"
"""
Extra appearance
Type: int
Applied in: src/classes/core/avatar/core.py (Avatar.appearance)
Notes: Added on top of the avatar's base appearance; the final result is clamped to 1~10.
Reference values:
  - Minor: 1
  - Major: 2
"""

# --- Cultivation (immortal path - respiration) ---
EXTRA_RESPIRE_EXP = "extra_respire_exp"
"""
Extra respiration exp
Type: int
Applied in: src/classes/action/respire.py
Notes: Fixed extra exp gained each time respiration is settled.
Reference values:
  - Minor: 5~10
  - Moderate: 20~50 (base respiration is about 100 exp per settlement)
  - Major: 100+
"""

EXTRA_RESPIRE_EXP_MULTIPLIER = "extra_respire_exp_multiplier"
"""
Extra respiration exp multiplier
Type: float
Applied in: src/classes/action/respire.py
Notes: Extra exp multiplier applied each time respiration is settled.
Reference values:
  - Minor: 0.1 (+10%)
  - Moderate: 0.5 (+50%)
  - Major: 1.0 (+100%)
"""

RESPIRE_DURATION_REDUCTION = "respire_duration_reduction"
"""
Respiration duration reduction
Type: float
Applied in: src/classes/action/respire.py
Notes: Fractional reduction of the respiration action's duration.
Reference values:
  - Minor: 0.05~0.1 (5%-10% shorter)
  - Moderate: 0.15 (15%)
  - Cap: 0.3 (30%)
"""

# --- Cultivation (martial path - body tempering) ---
TEMPER_DURATION_REDUCTION = "temper_duration_reduction"
"""
Body tempering duration reduction
Type: float
Applied in: src/classes/action/temper.py
Notes: Fractional reduction of the body tempering action's duration.
Reference values:
  - Minor: 0.05~0.1
  - Moderate: 0.15
  - Cap: 0.3
"""

EXTRA_BREAKTHROUGH_SUCCESS_RATE = "extra_breakthrough_success_rate"
"""
Extra breakthrough success rate
Type: float
Applied in: src/classes/action/breakthrough.py
Notes: Modifies the success rate when breaking through a bottleneck.
Reference values:
  - Minor: 0.05 (5%)
  - Moderate: 0.1 (10%)
  - Major: 0.3 (30%)
"""

EXTRA_RETREAT_SUCCESS_RATE = "extra_retreat_success_rate"
"""
Extra secluded cultivation success rate
Type: float
Applied in: src/classes/action/retreat.py
Notes: Bonus to the success check of secluded cultivation.
Reference values:
  - Minor: 0.05 (5%)
  - Moderate: 0.1 (10%)
  - Major: 0.2 (20%)
"""

EXTRA_REST_EXP = "extra_rest_exp"
"""
Extra rest cultivation exp
Type: int
Applied in: src/classes/action/rest.py
Notes: Fixed extra cultivation exp gained when the rest action is settled.
"""

# --- Dual cultivation ---
EXTRA_DUAL_CULTIVATION_EXP = "extra_dual_cultivation_exp"
"""
Extra dual cultivation exp
Type: int
Applied in: src/classes/mutual_action/dual_cultivation.py
Notes: Fixed extra exp gained by the initiator during dual cultivation.
Reference values:
  - Minor: 10~30
  - Moderate: 50~100 (base dual cultivation yield is about 300~500)
  - Major: 150+
"""

# --- Gathering ---
EXTRA_HARVEST_MATERIALS = "extra_harvest_materials"
"""
Extra harvested materials
Type: int
Applied in: src/classes/action/harvest.py
Notes: Extra materials gained when harvesting plants.
Reference values:
  - Minor: 1
  - Moderate: 2
  - Major: 3
"""

EXTRA_HUNT_MATERIALS = "extra_hunt_materials"
"""
Extra hunted materials
Type: int
Applied in: src/classes/action/hunt.py
Notes: Extra materials gained when hunting animals.
Reference values:
  - Minor: 1
  - Moderate: 2
  - Major: 3
"""

EXTRA_MINE_MATERIALS = "extra_mine_materials"
"""
Extra mined materials
Type: int
Applied in: src/classes/action/mine.py
Notes: Extra materials gained when mining.
"""

EXTRA_PLANT_INCOME = "extra_plant_income"
"""
Extra planting spirit stone income
Type: int
Applied in: src/classes/action/plant.py
Notes: Extra spirit stones gained when planting.
"""

# --- Movement ---
EXTRA_MOVE_STEP = "extra_move_step"
"""
Extra move steps
Type: int
Applied in: src/classes/action/move.py
Notes: Number of extra tiles that can be moved per move.
Reference values:
  - Moderate: 1
  - Major: 2
"""

# --- Capture ---
EXTRA_CATCH_SUCCESS_RATE = "extra_catch_success_rate"
"""
Extra capture success rate
Type: float
Applied in: src/classes/action/catch.py
Notes: Added success rate when capturing a spirit beast.
Reference values:
  - Minor: 0.05~0.1 (5%-10%)
  - Moderate: 0.2 (20%)
  - Major: 0.3 (30%)
"""

# --- Escape ---
EXTRA_ESCAPE_SUCCESS_RATE = "extra_escape_success_rate"
"""
Extra escape success rate
Type: float
Applied in: src/classes/battle.py
Notes: Bonus to the success rate of fleeing from battle.
Reference values:
  - Minor: 0.1
  - Moderate: 0.2
  - Major: 0.3~0.5 (together with the base chance, escape is nearly guaranteed)
"""

# --- Assassination ---
EXTRA_ASSASSINATE_SUCCESS_RATE = "extra_assassinate_success_rate"
"""
Extra assassination success rate
Type: float
Applied in: src/classes/battle.py (get_assassination_success_rate)
Notes: Bonus to the assassination success check.
Reference values:
  - Minor: 0.05 (5%)
  - Moderate: 0.1 (10%)
  - Major: 0.15 (15%)
"""

# --- Fortune ---
EXTRA_LUCK = "extra_luck"
"""
Extra luck
Type: int
Applied in: src/classes/effect/luck.py
Notes: Affects fate-related outcomes such as fortunes, misfortunes, hidden domains, epiphanies and breakthroughs.
Reference values:
  - Ordinary person: 0
  - Blessed: 5~10
  - Protagonist template: 15~25
  - Jinxed: -5~-10
"""

EXTRA_FORTUNE_PROBABILITY = "extra_fortune_probability"
"""
Extra fortune probability
Type: float
Applied in: src/classes/fortune.py
Notes: Extra (absolute) monthly probability of triggering a fortune.
Reference values:
  - The base probability is usually very low (<0.01)
  - Minor: 0.001 (0.1%, noticeable)
  - Moderate: 0.002~0.005 (high)
  - Very high: 0.01 (1%, quite a lot)
"""

EXTRA_MISFORTUNE_PROBABILITY = "extra_misfortune_probability"
"""
Extra misfortune probability
Type: float
Applied in: src/classes/misfortune.py
Reference values:
  - The base probability is usually very low (<0.01)
  - Minor: 0.001 (0.1%, noticeable)
  - Moderate: 0.002~0.005 (high)
  - Very high: 0.01 (1%, quite a lot)
"""

EXTRA_OPPORTUNITY_PROBABILITY = "extra_opportunity_probability"
"""
Extra opportunity probability
Type: float
Applied in: src/systems/opportunity/
Notes: Extra (absolute) monthly probability of sensing a time-limited opportunity.
Reference values:
  - The base probability is usually very low (<0.01)
  - Minor: 0.001 (0.1%, noticeable)
  - Moderate: 0.002~0.005 (high)
  - Very high: 0.01 (1%, quite a lot)
"""

# --- Crafting ---
EXTRA_CAST_SUCCESS_RATE = "extra_cast_success_rate"
"""
Extra forging success rate
Type: float
Applied in: src/classes/action/cast.py
Notes: Success rate bonus for the forging (Cast) action.
Reference values:
  - Minor: 0.05 (+5%)
  - Moderate: 0.1 (+10%)
  - Major: 0.2+ (+20%)
"""

EXTRA_REFINE_SUCCESS_RATE = "extra_refine_success_rate"
"""
Extra alchemy success rate
Type: float
Applied in: src/classes/action/refine.py
Notes: Success rate bonus for the alchemy (Refine) action.
Reference values:
  - Minor: 0.05 (+5%)
  - Moderate: 0.1 (+10%)
  - Major: 0.2+ (+20%)
"""

EXTRA_SECT_MISSION_SUCCESS_RATE = "extra_sect_mission_success_rate"
"""
Extra sect mission success rate
Type: float
Applied in: src/classes/action/sect_mission.py
Notes: Success rate bonus for the sect mission action.
Reference values:
  - Minor: 0.05 (+5%)
  - Moderate: 0.1 (+10%)
  - Major: 0.2+ (+20%)
"""

# --- Weapons ---
EXTRA_WEAPON_PROFICIENCY_GAIN = "extra_weapon_proficiency_gain"
"""
Extra weapon proficiency growth
Type: float
Applied in: src/classes/action/nurture_weapon.py
Notes: Proficiency growth multiplier (multiplicative bonus).
Reference values:
  - Minor: 0.1~0.2 (+10%-20%)
  - Moderate: 0.5 (+50%)
  - Major: 1.0 (+100%, doubled)
"""

EXTRA_WEAPON_UPGRADE_CHANCE = "extra_weapon_upgrade_chance"
"""
Extra weapon ascension chance
Type: float
Applied in: src/classes/action/nurture_weapon.py
Notes: Bonus to the chance that a nurtured weapon ascends into a treasure.
Reference values:
  - Base chance: 0.05 (5%)
  - Minor: 0.05 (+5%)
  - Moderate: 0.1 (10%)
  - Major: 0.15 (15%)
"""

# --- Survival and recovery ---
EXTRA_MAX_LIFESPAN = "extra_max_lifespan"
"""
Extra max lifespan
Type: int (years)
Applied in: src/classes/age.py
Notes: Raises the avatar's maximum lifespan.
Reference values:
  - Minor: 5~10
  - Moderate: 20~50
  - Major: 100+
"""

EXTRA_HP_RECOVERY_RATE = "extra_hp_recovery_rate"
"""
Extra HP recovery rate. Affects both the SelfHeal action and natural recovery in the Simulator.
Type: float
Applied in: src/classes/action/self_heal.py
Notes: HP recovery efficiency multiplier when healing.
Reference values:
  - Minor: 0.1~0.2
  - Moderate: 0.5 (+50%)
  - Major: 1.0 (doubled)
"""

EXTRA_REST_HP_RECOVERY_RATE = "extra_rest_hp_recovery_rate"
"""
Extra rest recovery multiplier
Type: float
Applied in: src/classes/action/rest.py
Notes: Extra multiplier when the rest action restores HP.
"""

DAMAGE_REDUCTION = "damage_reduction"
"""
Damage reduction
Type: float
Applied in: src/classes/battle.py
Notes: Fraction of incoming damage that is reduced (multiplicative).
Reference values:
  - Minor: 0.05
  - Moderate: 0.1
  - Tank: 0.2~0.3 (not recommended above 0.3)
"""

REALM_SUPPRESSION_BONUS = "realm_suppression_bonus"
"""
Realm suppression bonus
Type: float
Applied in: src/classes/battle.py
Notes: When above the opponent's realm, percentage battle strength bonus per realm of difference. Think of it as "extra pressure".
Reference values:
  - Base: 0.0 (no extra bonus, base stats only)
  - Minor: 0.05 (10% more battle strength per realm of difference)
  - Moderate: 0.1
  - Major: 0.15
"""

# --- Economy ---
EXTRA_ITEM_SELL_PRICE_MULTIPLIER = "extra_item_sell_price_multiplier"
"""
Extra item sell price multiplier
Type: float
Applied in: src/classes/action/sold.py
Notes: Price bonus multiplier when selling items.
Reference values:
  - Minor: 0.1 (+10%)
  - Moderate: 0.2~0.3
  - Profiteer: 0.5
"""

SHOP_BUY_PRICE_REDUCTION = "shop_buy_price_reduction"
"""
Shop purchase price multiplier reduction
Type: float
Applied in: src/classes/prices.py
Notes: Lowers the markup multiplier when buying items from the system.
Reference values:
  - Minor: 0.1 (multiplier -0.1)
  - Moderate: 0.5 (multiplier -0.5)
Limit: the final multiplier is at least 1.0
"""

EXTRA_PLUNDER_MULTIPLIER = "extra_plunder_multiplier"
"""
Extra plunder yield multiplier
Type: float
Applied in: src/classes/action/plunder_people.py
Notes: Yield multiplier when plundering mortals.
Reference values:
  - Minor: 0.5
  - Moderate: 1.0
  - Major: 2
"""

EXTRA_EAT_MORTALS_EXP_MULTIPLIER = "extra_eat_mortals_exp_multiplier"
"""
Extra mortal-devouring cultivation exp multiplier
Type: float
Applied in: src/classes/action/eat_mortals.py
Notes: Bonus multiplier to cultivation exp gained when a yao devours mortals.
"""

EXTRA_CROSS_RACE_FRIENDLINESS = "extra_cross_race_friendliness"
"""
Cross-race initial friendliness modifier
Type: int
Applied in: src/sim/avatar_init/
Notes: Friendliness modifier when generating initial relations between avatars of different races.
"""

# Hidden domains
EXTRA_HIDDEN_DOMAIN_DROP_PROB = "extra_hidden_domain_drop_prob"
"""
Extra hidden domain drop probability
Type: float
Applied in: src/classes/gathering/hidden_domain.py
Notes: Increases the chance of obtaining treasure in a hidden domain.
Reference values:
  - Minor: 0.05
  - Moderate: 0.1
  - Major: 0.2
"""

EXTRA_HIDDEN_DOMAIN_DANGER_PROB = "extra_hidden_domain_danger_prob"
"""
Extra hidden domain danger probability
Type: float
Applied in: src/classes/gathering/hidden_domain.py
Notes: Increases (or, if negative, decreases) the chance of encountering danger in a hidden domain.
Reference values:
  - Less danger: -0.1 (10% lower danger rate)
  - More danger: 0.1
"""

# --- Sect teaching ---
EXTRA_EPIPHANY_PROBABILITY = "extra_epiphany_probability"
"""
Extra epiphany probability
Type: float
Applied in: src/classes/gathering/sect_teaching.py
Notes: Extra chance to directly learn another's technique/experience during events such as the sect teaching assembly.
Reference values:
  - Minor: 0.05
  - Moderate: 0.1
  - Genius: 0.2
"""

# --- Special permissions ---
LEGAL_ACTIONS = "legal_actions"
"""
Legal actions list
Type: list[str]
Applied in: permission checks of each action
Notes: List of special actions the avatar is allowed to perform.
Allowed values:
  - "DevourPeople": Devour living beings (evil treasure: Ten Thousand Souls Banner)
  - "InflictGu": Inflict Gu (Gu tools)
"""

# --- Gu arts ---
EXTRA_GU_SUCCESS_RATE = "extra_gu_success_rate"
"""
Extra Gu infliction success rate
Type: float
Applied in: src/systems/gu.py
Notes: Increases the success rate of the Inflict Gu action.
Reference values:
  - Gu tool (small): 0.03
  - Gu Master: 0.10
  - Gu Immortal: 0.18
"""

EXTRA_GU_DURATION_MONTHS = "extra_gu_duration_months"
"""
Extra Gu duration (months)
Type: int
Applied in: src/systems/gu.py
Notes: Extends the duration after a successful Gu infliction.
Reference values:
  - Small: 3
  - Gu Master: 6
  - Gu Immortal: 12
"""

EXTRA_GU_RESISTANCE_RATE = "extra_gu_resistance_rate"
"""
Extra Gu resistance modifier
Type: float
Applied in: src/systems/gu.py
Notes: Lowers the success rate of Gu inflicted on the avatar.
Reference values:
  - Basic protection: 0.08
  - Noticeable protection: 0.12
  - Strong protection: 0.18
  - Top-tier protection: 0.20
"""

# --- Formations ---
EXTRA_FORMATION_POWER = "extra_formation_power"
"""
Extra formation power
Type: float
Applied in: src/systems/formation.py
Notes: Increases the final regional formation effect when setting up a formation.
Reference values:
  - Formation Master: 0.15
  - Formation Immortal: 0.35
"""

EXTRA_FORMATION_DURATION_MONTHS = "extra_formation_duration_months"
"""
Extra formation duration (months)
Type: int
Applied in: src/systems/formation.py
Notes: Extends the duration when setting up a formation.
Reference values:
  - Formation Master: 6
  - Formation Immortal: 12
"""

FORMATION_COST_REDUCTION = "formation_cost_reduction"
"""
Formation spirit stone cost reduction
Type: float
Applied in: src/systems/formation.py
Notes: Lowers the spirit stone cost of setting up a formation.
Reference values:
  - Formation Master: 0.10
  - Formation Immortal: 0.25
"""

# =============================================================================
# CSV configuration format
# =============================================================================

"""
How to write the effects column in CSV (relaxed JSON is supported):

Basic format (unquoted keys recommended):
  {extra_battle_strength_points: 3}
  {extra_battle_strength_points: 2, extra_max_hp: 50}
  {legal_actions: ['DevourPeople']}

Conditional effects (when field):
  [{when: 'avatar.weapon.weapon_type == WeaponType.SWORD', extra_battle_strength_points: 3}]
  Accessible names: avatar, WeaponType, EquipmentGrade, Alignment

Dynamic values (string expressions are evaluated):
  {extra_battle_strength_points: 'avatar.weapon.special_data.get("souls", 0) * 0.1'}

Note: effects values containing commas must be wrapped in double quotes in CSV so they are not mistaken for column separators
"""

# =============================================================================
# Effect merge rules
# =============================================================================

"""
Effects are merged by _merge_effects() in src/classes/effect/process.py.

Merge rules:
1. List values (e.g. legal_actions): union (deduplicated)
2. Numeric values (e.g. extra_*): summed
3. Other values: the latter overrides the former
4. Dynamic expressions (strings): evaluated in the Avatar.effects property

Merge order (lowest to highest priority):
1. Sect (sect)
2. Technique (technique)
3. Spirit root (root)
4. Trait (persona) - iterates over all personas
5. Weapon and auxiliary equipment (weapon, auxiliary)

The final result is obtained through the Avatar.effects property (computed live).
"""

# =============================================================================
# List of all valid effect fields
# =============================================================================

ALL_EFFECTS = [
    # Combat
    "extra_battle_strength_points",      # int - extra battle strength
    "extra_max_hp",                      # int - extra max HP
    "extra_observation_radius",          # int - extra observation radius
    "extra_appearance",                  # int - extra appearance
    "damage_reduction",                  # float - damage reduction
    "realm_suppression_bonus",           # float - realm suppression bonus

    # Cultivation
    "extra_respire_exp",                 # int - extra respiration exp
    "extra_respire_exp_multiplier",      # float - extra respiration exp multiplier
    "respire_duration_reduction",        # float - respiration duration reduction
    "temper_duration_reduction",         # float - body tempering duration reduction
    "extra_breakthrough_success_rate",   # float - extra breakthrough success rate
    "extra_retreat_success_rate",        # float - extra secluded cultivation success rate
    "extra_rest_exp",                    # int - extra rest cultivation exp

    # Dual cultivation
    "extra_dual_cultivation_exp",        # int - extra dual cultivation exp

    # Gathering
    "extra_harvest_materials",           # int - extra harvested materials
    "extra_hunt_materials",              # int - extra hunted materials
    "extra_mine_materials",               # int - extra mined materials
    "extra_plant_income",                # int - extra planting spirit stone income

    # Movement
    "extra_move_step",                   # int - extra move steps

    # Capture
    "extra_catch_success_rate",          # float - extra capture success rate

    # Escape
    "extra_escape_success_rate",         # float - extra escape success rate

    # Assassination
    "extra_assassinate_success_rate",    # float - extra assassination success rate

    # Fortune
    "extra_luck",                        # int - extra luck
    "extra_fortune_probability",         # float - extra fortune probability
    "extra_misfortune_probability",      # float - extra misfortune probability
    "extra_opportunity_probability",     # float - extra opportunity probability

    # Crafting
    "extra_cast_success_rate",           # float - extra forging success rate
    "extra_refine_success_rate",         # float - extra alchemy success rate
    "extra_sect_mission_success_rate",   # float - extra sect mission success rate

    # Weapons
    "extra_weapon_proficiency_gain",     # float - extra weapon proficiency growth multiplier
    "extra_weapon_upgrade_chance",       # float - extra weapon ascension chance

    # Survival and recovery
    "extra_max_lifespan",                # int - extra max lifespan (years)
    "extra_hp_recovery_rate",            # float - extra HP recovery rate multiplier
    "extra_rest_hp_recovery_rate",       # float - extra rest recovery multiplier

    # Economy
    "extra_item_sell_price_multiplier",  # float - extra item sell price multiplier
    "shop_buy_price_reduction",          # float - shop purchase price multiplier reduction
    "extra_plunder_multiplier",          # float - extra plunder yield multiplier
    "extra_eat_mortals_exp_multiplier",  # float - extra mortal-devouring exp multiplier
    "extra_cross_race_friendliness",     # int - cross-race initial friendliness modifier
    "extra_gu_success_rate",             # float - extra Gu infliction success rate
    "extra_gu_duration_months",          # int - extra Gu duration (months)
    "extra_gu_resistance_rate",          # float - extra Gu resistance modifier
    "extra_formation_power",             # float - extra formation power
    "extra_formation_duration_months",   # int - extra formation duration (months)
    "formation_cost_reduction",          # float - formation spirit stone cost reduction

    # Hidden domains
    "extra_hidden_domain_drop_prob",     # float - extra hidden domain drop probability
    "extra_hidden_domain_danger_prob",   # float - extra hidden domain danger probability

    # Sect teaching
    "extra_epiphany_probability",        # float - extra epiphany probability

    # Special permissions
    "legal_actions",                     # list[str] - legal actions list
]

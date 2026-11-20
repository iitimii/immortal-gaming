# Formation System Spec

This document records the first-version design goals and implementation constraints of the formation system. The formation system should work together with the existing actions, auxiliary equipment, region-first map, effects and save structure, but should not force regional effects into the avatar temporary effect chain.

## Goals

A formation is a time-limited regional effect set up in the current region using a formation disk:

1. A formation disk is a kind of auxiliary equipment.
2. After equipping a formation disk, an avatar can perform the "Set Formation" action.
3. Setting a formation can only affect the region the avatar is currently in; remote formation setting is not supported, and it is not bound to a tile.
4. A formation is bound to a region, not to an avatar.
5. A region can only have one formation at a time.
6. A newly set formation automatically replaces the region's existing formation.
7. A formation consumes spirit stones, not the formation disk.
8. A formation has no failure rate; if the conditions are met, it succeeds.
9. A formation lasts for a period of time and ends automatically on expiry.
10. The first version does not include withdrawal, formation breaking, maintenance fees, contesting formation eyes, stacking multiple formations, or city economy formations.

Formations and Gu are structurally similar but have different targets:

| System | Tool | Action | Target | State carrier | Gameplay role |
|---|---|---|---|---|---|
| Gu | Gu vessel auxiliary | Plant Gu | avatar | avatar temporary effects | Covertly influence a single person |
| Formation | Formation disk auxiliary | Set Formation | current region | map/region formation state | Reshape an area |

## Design Principles

### 1. A formation is a regional aura, not an avatar temporary effect

A formation has no single avatar recipient, so it should not be written into:

```python
avatar.temporary_effects
```

An avatar only temporarily benefits from a formation's effects while located in that region and performing formation-related actions or taking part in battles within that region.

It is recommended that `src/systems/formation.py` provide unified query functions, for example:

```python
get_active_region_formation(world, region_id)
get_active_region_formation_effects(world, region_id)
get_current_region_formation_effects(avatar)
```

Specific actions and systems read the current region's active formation effects at settlement time and combine them with the avatar's own `avatar.effects`.

### 2. Only set formations at the current location

The "Set Formation" action does not need a region parameter. The action reads directly:

```python
region = avatar.tile.region
```

This keeps the action simple, and matches the gameplay semantics of "a formation master personally sets the formation on the earth veins".

### 3. Overwrite the old formation, no withdrawal

Each region has at most one active formation at a time. If the current region already has a formation, the new formation directly overwrites the old one.

Overwriting does not refund spirit stones and does not keep the old formation's remaining time.

### 4. Action descriptions use expository text

Formation action descriptions are used by players and the LLM AI to understand behavioral boundaries, so they should remain plain expository text without literary embellishment.

Recommended description:

```text
Set a formation in the current region. Requires an equipped formation disk and consumes spirit stones. Each region can have only one active formation at a time; a new formation replaces the existing one. The Spirit-Gathering Formation increases breathing cultivation gains and suits cultivation regions and sect headquarters. The Mountain-Guard Formation improves combat capability within the formation and suits sect headquarters and cultivation regions. The Healing Formation improves healing recovery and suits sect headquarters, cultivation regions, and cities. The Clarity Formation improves seclusion and breakthrough stability and suits cultivation regions and sect headquarters. The Vein-Seeking Formation increases mining gains and suits normal regions with mineral lodes. The Wood-Growth Formation increases gathering gains and suits normal regions with plants. The Beast-Driving Formation increases hunting gains and suits normal regions with animals.
```

Story events are left to the story module; the formation action itself is only responsible for the base fact event.

## Data Model

For the first version, it is recommended to maintain a region formation dict on the runtime `Map`:

```python
world.map.region_formations = {
    301: {
        "formation_type": "spirit_gathering",
        "caster_id": "avatar_1",
        "disk_item_id": 2082,
        "start_month": 120,
        "duration": 28,
        "effects": {
            "extra_respire_exp_multiplier": 0.18
        },
        "cost": 220
    }
}
```

Field descriptions:

1. `formation_type`: formation type key.
2. `caster_id`: ID of the avatar who set the formation; only the ID is saved, not an object reference.
3. `disk_item_id`: item ID of the formation disk used.
4. `start_month`: the month the formation was set.
5. `duration`: duration in months.
6. `effects`: regional effects provided by the formation, using JSON primitive types.
7. `cost`: spirit stones consumed by this formation setting, mainly for display and debugging.

Expiry check:

```python
current_month >= start_month + duration
```

After expiry, it is deleted from `region_formations`.

## Formation Disks

Formation disks are configured as `Auxiliary`. The formation disk itself grants the action permission:

```text
{legal_actions: ['SetFormation']}
```

Suggested formation disk grades:

| Formation disk | Corresponding realm | Base duration | Base cost | Notes |
|---|---|---:|---:|---|
| Low-grade formation disk | Qi Refinement | 18 months | 80 | Entry-level disk |
| Mid-grade formation disk | Foundation Establishment | 24 months | 200 | Stable disk |
| High-grade formation disk | Core Formation | 30 months | 600 | Advanced disk |
| Supreme-grade formation disk | Nascent Soul | 36 months | 1800 | Top-tier disk |

Formation disks are not one-time consumables. Setting a formation only consumes spirit stones.

## Persona

The first version adds two formation-related personas:

### Formation Master

Formation Master is a relatively rare formation-setting specialty persona.

Suggested effects:

```python
{
    "extra_formation_power": 0.15,
    "extra_formation_duration_months": 6,
    "formation_cost_reduction": 0.10
}
```

### Formation Immortal

Formation Immortal is a rarer, more powerful formation-setting specialty persona.

Suggested effects:

```python
{
    "extra_formation_power": 0.35,
    "extra_formation_duration_months": 12,
    "formation_cost_reduction": 0.25
}
```

Calculation:

```text
final_effect = base_effect * (1 + extra_formation_power)
duration = base_duration + extra_formation_duration_months + random_delta
cost = base_cost * (1 - formation_cost_reduction)
```

If an avatar has several related personas at the same time, simply accumulate them according to the existing effect merge rules. Since Formation Immortal should be sufficiently rare, the first version does not need extra mutual-exclusion logic.

## Formation Types

The first version includes the following formations. It does not include the Market-Gathering Formation or the Blood Fiend Formation.

| Formation key | Name | Effect | Allowed regions |
|---|---|---|---|
| `spirit_gathering` | Spirit-Gathering Formation | Increases breathing gains | Cultivation regions, sect headquarters |
| `mountain_guard` | Mountain-Guard Formation | Improves combat capability within the formation | Sect headquarters, cultivation regions |
| `healing` | Healing Formation | Improves healing recovery | Sect headquarters, cultivation regions, cities |
| `clarity` | Clarity Formation | Improves seclusion and breakthrough stability | Cultivation regions, sect headquarters |
| `vein_seeking` | Vein-Seeking Formation | Increases mining gains | Normal regions with lodes |
| `wood_growth` | Wood-Growth Formation | Increases gathering gains | Normal regions with plants |
| `beast_driving` | Beast-Driving Formation | Increases hunting gains | Normal regions with animals |

### Suggested effects

Spirit-Gathering Formation:

```python
{"extra_respire_exp_multiplier": 0.10 / 0.18 / 0.28 / 0.40}
```

Mountain-Guard Formation:

```python
{"extra_battle_strength_points": 1 / 2 / 4 / 7}
```

Healing Formation:

```python
{"extra_hp_recovery_rate": 0.20 / 0.35 / 0.55 / 0.80}
```

Clarity Formation:

```python
{
    "extra_breakthrough_success_rate": 0.03 / 0.05 / 0.08 / 0.12,
    "extra_retreat_success_rate": 0.03 / 0.05 / 0.08 / 0.12
}
```

Vein-Seeking Formation:

```python
{"extra_mine_materials": 1 / 1 / 2 / 3}
```

Wood-Growth Formation:

```python
{"extra_harvest_materials": 1 / 1 / 2 / 3}
```

Beast-Driving Formation:

```python
{"extra_hunt_materials": 1 / 1 / 2 / 3}
```

The value order corresponds to low-grade, mid-grade, high-grade and supreme-grade formation disks. The final values are further boosted by `extra_formation_power`.

## Cost and Duration

The base cost is determined by the formation disk grade, then multiplied by the formation type multiplier and the region type multiplier.

Formation type multipliers:

| Formation | Multiplier |
|---|---:|
| Spirit-Gathering Formation | 1.2 |
| Mountain-Guard Formation | 1.4 |
| Healing Formation | 1.0 |
| Clarity Formation | 1.3 |
| Vein-Seeking Formation | 0.8 |
| Wood-Growth Formation | 0.8 |
| Beast-Driving Formation | 0.8 |

Region type multipliers:

| region | Multiplier |
|---|---:|
| Normal region | 1.0 |
| City | 1.1 |
| Cultivation region | 1.3 |
| Sect headquarters | 1.5 |

Final cost:

```text
cost = disk_base_cost * formation_multiplier * region_multiplier * (1 - formation_cost_reduction)
```

Final duration:

```text
duration = disk_base_duration + extra_formation_duration_months + random_delta
```

`random_delta` should be kept within a small range, e.g. `-3` to `+6` months, to keep results predictable.

## Action Design

New action:

```python
SetFormation
```

Display name:

```text
Set Formation
```

Action parameters:

```python
PARAMS = {
    "formation_type": "FormationType",
}
```

Parameter sources:

```python
PARAM_OPTION_SOURCES = {
    "formation_type": ParamOptionSource.AVAILABLE_FORMATION_TYPE,
}
```

`AVAILABLE_FORMATION_TYPE` should only return formations that can be set in the current region, to avoid the LLM AI choosing obviously invalid formations.

`can_possibly_start` should check:

1. The avatar has a formation disk equipped.
2. The avatar is currently in a valid region.
3. The current region has at least one formation that can be set.
4. The avatar has the minimum spirit stones needed to set any available formation.

`can_start(formation_type)` should check:

1. A formation disk is equipped.
2. `formation_type` is valid.
3. The current region allows this formation.
4. The avatar has enough spirit stones.

Suggested `_execute` flow:

1. Calculate the cost.
2. Deduct spirit stones.
3. Build the formation record.
4. Overwrite `world.map.region_formations[region.id]`.

The `finish` base event should use expository text:

```text
{avatar} set {formation} in {region}.
```

If an old formation is overwritten:

```text
{avatar} set {formation} in {region}; the original formation in this region was replaced.
```

## Settlement Integration Points

Formation effects are read at specific settlement points and do not enter the avatar's own main effect chain.

Suggested integration:

1. `src/classes/action/respire.py`
   - Spirit-Gathering Formation: breathing experience multiplier.
2. `src/classes/action/self_heal.py`
   - Healing Formation: healing recovery multiplier.
3. `src/systems/battle.py`
   - Mountain-Guard Formation: combat strength bonus within the formation.
   - The first version may apply it only when both sides are in the same region.
4. `src/classes/action/breakthrough.py`
   - Clarity Formation: breakthrough success rate bonus.
5. `src/classes/action/retreat.py`
   - Clarity Formation: seclusion success rate bonus.
6. `src/classes/action/mine.py`
   - Vein-Seeking Formation: mining gains.
7. `src/classes/action/harvest.py`
   - Wood-Growth Formation: gathering gains.
8. `src/classes/action/hunt.py`
   - Beast-Driving Formation: hunting gains.

If the Beast-Driving Formation later needs to affect capturing, it can be hooked into `src/classes/action/catch.py`, but this is not required in the first version.

## Save Files

Formations are world state and should be saved with the save file.

Recommended to save into map/world-related state:

```json
{
  "region_formations": {
    "301": {
      "formation_type": "spirit_gathering",
      "caster_id": "avatar_1",
      "disk_item_id": 2082,
      "start_month": 120,
      "duration": 28,
      "effects": {
        "extra_respire_exp_multiplier": 0.18
      },
      "cost": 220
    }
  }
}
```

On load, restoring it as `dict[int, dict]` according to the current model is enough; there is no need to restore it into complex objects.

Follow the save constraints:

1. Only save JSON primitive types.
2. Cross-object references only save IDs.
3. Do not save avatar, region or auxiliary object references.

## Display

The first-version display should stay restrained:

1. Region details show the current formation name, remaining time and effect description.
2. The map region tooltip can show a brief summary of the current formation.
3. The "Set Formation" action appears in the avatar action list.
4. No dedicated formation management page is added.

Because the first version has no withdrawal, formation breaking, maintenance or multi-formation stacking, the region detail display is sufficient.

## Testing Suggestions

Backend tests should cover at least:

1. A formation cannot be set without an equipped formation disk.
2. The `SetFormation` permission appears after equipping a formation disk.
3. `param_options` only returns formations that can be set in the current region.
4. `can_possibly_start` is false when the current region has no available formation.
5. A formation cannot be set with insufficient spirit stones.
6. After a successful setting, spirit stones are deducted and `region_formations` is written.
7. A new formation in the same region overwrites the old one.
8. Formations are deleted automatically on expiry.
9. Saving stores and restores `region_formations`.
10. The Spirit-Gathering Formation affects breathing gains.
11. The Mountain-Guard Formation affects combat strength within the formation.
12. The Healing Formation affects healing recovery.
13. The Clarity Formation affects seclusion or breakthrough success rate.
14. The Vein-Seeking, Wood-Growth and Beast-Driving Formations each affect their corresponding gathering action.
15. Formation Master and Formation Immortal affect formation power, duration and cost.

Frontend tests should be added according to the actual display scope:

1. Region detail can display the current formation.
2. Formation info can be loaded when region detail is opened for the first time.
3. Type definitions and mappers do not spread `any`.

## Not Included Yet

The first version explicitly does not include:

1. Market-Gathering Formation.
2. Blood Fiend Formation.
3. Remote formation setting.
4. Formation setting failure rate.
5. Withdrawing formations.
6. Formation-breaking actions.
7. Formation maintenance fees.
8. Stacking multiple formations.
9. Tile-level formations.
10. Formations affecting avatars not in that region.
11. Dedicated formation management UI.


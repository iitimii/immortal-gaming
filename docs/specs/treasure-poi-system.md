# Treasure Emergence POI System Spec

This document defines the implementation plan for the "treasure emergence" system. A treasure is a time-limited Point of Interest (POI) on the map. It is not ordinary event text whose specific location is immediately visible to the whole world, nor is it a new equipment slot, a treasure growth system, or a standalone contest system.

Current status: design confirmed; runtime logic and frontend integration pending implementation.

Related existing systems:

- Grave and general POI: [grave-poi-system.md](grave-poi-system.md)
- Single-choice equipment exchange and roleplay continuation: [single-choice-unified-framework.md](single-choice-unified-framework.md)
- Event semantics: [story-event-system.md](story-event-system.md)
- Official map source of truth and runtime state: [region-first-map-system.md](region-first-map-system.md)

## 1. Goals and Boundaries

### 1.1 Goals

1. Time-limited treasure POIs randomly appear in the world.
2. A treasure exists for twenty years, i.e. `240` game months; if no one takes it by expiry, its treasure light dissipates and it is removed.
3. Emergence can produce a global, vague celestial sign that reveals the treasure's major realm but not its coordinates, specific item, or source.
4. When an avatar enters the POI's existing observation range, it always discovers the treasure.
5. The god's-eye view map always shows valid treasure POIs; but an avatar's action parameters only include treasures it has discovered itself.
6. Avatars that have discovered it can travel there via the existing `MoveToPOI`; after arriving on the same tile they can perform the instant action "Take Treasure".
7. Whether taking the treasure happens, whether to keep staying, leave, or attack avatars on the same tile is still decided by the existing action decision system; the treasure system does not force choices on avatars.
8. After successfully taking a treasure, only the existing weapon and auxiliary equipment replacement flow is reused.
9. All treasure state, discovery relationships, attempt counts, and pending items can be restored with the save file.

### 1.2 Non-goals

The first phase explicitly does not include:

1. New equipment slots, natal treasures, artifact spirits, binding, growth, sealing, or uniqueness.
2. Negotiation, alliances, teams, dedicated contests, or an "occupy treasure" state.
3. Modifying the take-treasure success rate by injury, HP, perception, luck, sect, or any other temporary state.
4. Giving intermediate products such as materials, scraps, or partial rewards after a failed take.
5. Static treasure points in map presets; treasures are runtime world state and are not written into `map.json`.
6. Maintaining complex migrations or dual-track deserialization for old saves. When an old save lacks treasure data, restore it as "no active treasures".

## 2. Confirmed Product Rules

### 2.1 Generation rules

| Item | Confirmed value |
|---|---|
| Check frequency | Once per month |
| Emergence probability | `0.5%` / month |
| Active cap | At most `3` valid treasure POIs in the whole world |
| Duration | `240` months (twenty years) |
| Coordinates | Generated on a random valid map tile |
| Map display | The god's-eye view map shows all valid treasures |
| Avatar awareness | Only avatars that enter the observation range are written into `discovered_by` |
| Generatable items | Existing `weapon` or `auxiliary` |
| Generatable major realms | Foundation Establishment, Core Formation, Nascent Soul; no Qi Refinement |

A "random valid map tile" at least requires: within bounds, readable normally by the map model, and not a tile where a treasure already exists. Implementation should prefer the map's existing valid tile semantics, and must not restore or introduce a parallel `tile_map.csv/region_map.csv` path.

### 2.2 Narrative source

Each treasure determines one narrative source at generation time and saves it with the save file:

```text
ancient_cultivator_relic  # relic weapon of an ancient cultivator
spirit_vein_treasure      # treasure born of a spirit vein
demon_king_relic          # relic of a demon king
demonic_artifact          # demonic-path fell artifact
meteorite_relic           # treasure from beyond the heavens (meteorite)
lost_sect_artifact        # lost artifact of a sect
```

The source only serves event and detail narrative; it does not change equipment stats, take probability, map location, or contest rules.

### 2.3 Discovery and action visibility

Discovery rules strictly reuse the grave POI implementation: `POIManager.discover_nearby()` checks with `get_avatar_observation_radius()` and Manhattan distance; a POI within observation range is always discovered.

The discovery relationship is only stored in `poi.discovered_by`; a second `known_poi_ids` is not maintained on the Avatar, to avoid double-write inconsistency.

The following visibility layers must be distinguished:

| Layer | Is the treasure visible |
|---|---|
| `/api/v1/query/world/map`, map POI layer | All treasures that have not expired are shown |
| `MoveToPOI` parameter options | Only POIs the current avatar has discovered |
| `TakeTreasure` parameter options | Only `treasure` POIs the current avatar has discovered |
| Action `can_start()` | Additionally checks that the POI has not expired and the avatar is on the same tile |

## 3. Domain Model and Save Files

### 3.1 `TreasurePOI`

Add `src/classes/poi/treasure.py`:

```python
@dataclass(kw_only=True)
class TreasurePOI(PointOfInterest):
    kind: str = "treasure"
    treasure_source: str
    treasure_realm: str
    treasure_payload: dict[str, Any] | None
    treasure_icon_id: str
    attempt_count: int = 0
```

`PointOfInterest` already carries the following common fields, which treasures must not maintain again:

```text
id, kind, x, y, name, desc,
created_month, expires_month,
discovered_by, icon_key, is_clickable
```

The ID should be a non-colliding runtime ID, for example:

```text
treasure:<created_month>:<short-random-id>
```

A treasure item has only one `treasure_payload`. It should not hold both a weapon and auxiliary equipment, nor should it save an extra live Python Item object outside the payload.

### 3.2 Common equipment payload

The existing grave in `src/classes/poi/grave.py` contains the item snapshot and restore logic. When implementing treasures, extract it into a POI-scoped shared helper, for example:

```text
src/classes/poi/item_payload.py
  build_equipment_payload(item) -> dict | None
  restore_equipment_item(payload) -> Weapon | Auxiliary | None
```

The payload only stores basic JSON types:

```json
{
  "kind": "weapon",
  "item_id": 1001,
  "name": "Mysterious Meteor Sword",
  "realm": "CORE_FORMATION",
  "special_data": {}
}
```

On restore, find the prototype through the existing `weapons_by_id` or `auxiliaries_by_id`, instantiate it, and then restore `special_data`. This way graves and treasures share the same persistence contract and never share item instances.

### 3.3 Save format

The world save continues to save only through the existing `world_data["pois"]`:

```json
{
  "schema_version": 1,
  "id": "treasure:1296:8f3d2a",
  "kind": "treasure",
  "x": 42,
  "y": 17,
  "name": "Core Formation Treasure",
  "desc": "Spiritual light swirls; an ancient treasure is emerging here.",
  "created_month": 1296,
  "expires_month": 1416,
  "discovered_by": ["avatar-1", "avatar-8"],
  "icon_key": "treasure_04",
  "is_clickable": true,
  "treasure_source": "meteorite_relic",
  "treasure_realm": "CORE_FORMATION",
  "treasure_payload": {
    "kind": "weapon",
    "item_id": 1001,
    "name": "Mysterious Meteor Sword",
    "realm": "CORE_FORMATION",
    "special_data": {}
  },
  "treasure_icon_id": "treasure_04",
  "attempt_count": 4
}
```

Serialization constraints:

1. Only store basic JSON types.
2. Cross-object relationships only store Avatar IDs and do not hold Avatar references.
3. `discovered_by` is stored as a string array and restored to `set[str]` on load.
4. `icon_key`, source, item, realm, and attempt count remain unchanged after loading and are not re-randomized.
5. If the corresponding item ID no longer exists in configuration, the action should produce a controlled failure event and keep the POI; it must not abort the simulation with an exception.

### 3.4 Polymorphic deserialization

The current `POIManager.load_from_list()` mainly only recognizes `grave`. Implementation should use an explicit loader dispatch table:

```python
POI_LOADERS = {
    "grave": GravePOI.from_save_dict,
    "treasure": TreasurePOI.from_save_dict,
}
```

An unknown `kind` can be ignored with a warning logged; there is no need to add a compatibility branch for old saves. `src/classes/poi/__init__.py` must export `TreasurePOI` and the shared helper, to keep the import path complete.

## 4. World Lifecycle

### 4.1 Configuration

Add `static/config.yml -> world.treasure`:

```yaml
world:
  treasure:
    spawn_probability_per_month: 0.005
    max_active_count: 3
    duration_months: 240
    realms:
      - FOUNDATION_ESTABLISHMENT
      - CORE_FORMATION
      - NASCENT_SOUL
    source_weights:
      ancient_cultivator_relic: 20
      spirit_vein_treasure: 20
      demon_king_relic: 15
      demonic_artifact: 15
      meteorite_relic: 15
      lost_sect_artifact: 15
    backlash_probability: 0.10
    backlash_hp_ratio: 0.12
```

The runtime should read the current configuration at call time, to avoid freezing the configuration object at module import.

### 4.2 Service responsibilities

Add `src/systems/treasure.py`, responsible for:

1. Judging the number of active treasures and this month's emergence probability.
2. Randomly drawing a valid tile, an available major realm, an equipment category, the corresponding item, a narrative source, and a treasure chest icon.
3. Creating the POI and handing it to `POIManager.add()`.
4. Generating a global celestial sign event that contains no location.
5. Cleaning up treasures expiring this month and generating treasure light dissipation events.

`TreasurePOI` only stores state, serialization, and the detail payload; it does not read probability configuration, nor does it actively scan the map.

### 4.3 Simulation phase

Add a monthly `treasure_lifecycle` phase, positioned after death resolution and before POI discovery:

```text
11  resolve_death
12  treasure_lifecycle
      a. Remove treasure POIs expiring this month, and produce dissipation events
      b. When active treasures are below the cap, attempt emergence by probability
      c. On successful generation, POIManager.add() produces an upsert increment
13  discover_pois
      a. Avatars within observation range automatically discover new and existing treasures
```

After adding the phase, the subsequent `SimulationPhase.index` values must be reordered; `step()` remains responsible only for orchestration. Treasure expiry cleanup cannot keep relying only on annual maintenance, because annual cleanup cannot guarantee precise dissipation at "the 240th month". Whether graves continue to use annual cleanup is decided by the grave system itself; this change does not alter its 50-year semantics.

### 4.4 Events

All events continue to be collected and stored centrally by the simulator:

| Timing | Content scope | Related | `is_major` |
|---|---|---|---:|
| Treasure emergence | Vague celestial sign, reveals treasure grade, no coordinates | None | `False` |
| Avatar discovery | Coordinates, name, and source visible | Discoverer | `False` |
| Take failure | Failure or restriction backlash | Attempter | `False` |
| Take success and accept | Obtains the specific item | Taker | `True` |
| Twenty-year dissipation | Treasure light dissipates; coordinates need not be revealed | None | `False` |

Events produce the factual result first; this phase does not add an LLM story event for treasures. When expansion is needed in the future, use `StoryEventService` to append `is_story=True` body text after the base event.

## 5. Action and Take-Treasure Resolution

### 5.1 Parameters and start conditions

Add `src/classes/action/take_treasure.py`:

```python
class TakeTreasure(InstantAction):
    ACTION_NAME_ID = "take_treasure_action_name"
    DESC_ID = "take_treasure_description"
    REQUIREMENTS_ID = "take_treasure_requirements"
    EMOJI = "..."
    PARAMS = {"poi_id": "poi_id"}
    PARAM_OPTION_SOURCES = {
        "poi_id": ParamOptionSource.KNOWN_TREASURE_POI_ID,
    }
    IS_MAJOR = True
```

`EMOJI` follows the existing action display convention; the specific value is chosen at implementation time as an existing compatible symbol. The action must be imported in `src/classes/action/__init__.py` to ensure action registration takes effect.

Add `ParamOptionSource.KNOWN_TREASURE_POI_ID`, implemented as:

```python
_known_poi_options(avatar, kind="treasure")
```

The option's `value` must be the POI ID, not the name, and executability tests must be added.

`can_start(poi_id)` must check, in order:

1. The POI exists and `isinstance(poi, TreasurePOI)`.
2. The POI has not expired.
3. The current avatar has discovered the POI.
4. `treasure_payload` still exists.
5. The current avatar's coordinates exactly match the POI's coordinates.

`can_possibly_start()` returns `True` only when the current tile has a discovered, valid treasure that still has a payload.

### 5.2 Success rate

Taking a treasure is determined only by the major realm difference between the taker and the treasure:

```python
success_rate = clamp(
    0.45 + (taker_realm_rank - treasure_realm_rank) * 0.15,
    minimum=0.05,
    maximum=0.95,
)
```

| Major realm difference | Success rate |
|---:|---:|
| Two or more ranks lower | 5% |
| One rank lower | 30% |
| Same | 45% |
| One rank higher | 60% |
| Two ranks higher | 75% |
| Four or more ranks higher | 95% |

During implementation, extract the realm rank mapping inside `DigGrave` into a shared helper, to avoid two hardcoded copies. Treasures have no Qi Refinement grade, but Qi Refinement avatars are allowed to attempt Foundation Establishment treasures.

The following factors must not be added to the take probability: current HP, injuries, perception, luck, personality, sect, equipment quality, the number of avatars on the same tile, or previous failure count.

### 5.3 Failure and backlash

Each `TakeTreasure.step()` increments `attempt_count += 1`.

If the random check fails:

1. The POI and payload are kept.
2. No item or material is given.
3. A restriction backlash is triggered with small probability per `world.treasure.backlash_probability`.
4. Backlash damage is the configured ratio of current max HP, at least `1` point.
5. When the damage is lethal, it must go through normal death resolution and not bypass `handle_death()`.
6. Produce a non-major event related only to the attempter.

This action does not reuse the luck deduction rule from grave digging.

### 5.4 Success and equipment exchange

After success:

1. Restore an independent equipment instance from `treasure_payload`.
2. Construct `ItemExchangeKind.WEAPON` or `ItemExchangeKind.AUXILIARY` according to the payload `kind`.
3. Call the existing `resolve_item_exchange()`, so that the LLM, rule fallback, and roleplay continuation still go through the same decision framework.
4. Only when the avatar actually accepts the new equipment, call `poi_manager.remove(treasure.id)`.
5. POI removal automatically produces the existing `poi_updates` remove increment.
6. Write the take-success major event.

When the equipment slot is empty, keep using `auto_accept_when_empty=True`. When equipment already exists, the avatar can accept the replacement or reject.

### 5.5 "Rejected and left in place" exchange semantics

The existing `RejectMode.ABANDON_NEW` narrative is abandoning the new item, which cannot accurately express the rule that the treasure remains at the POI. Add a general semantic in `src/systems/single_choice/item_exchange.py`:

```python
class RejectMode(Enum):
    ABANDON_NEW = "abandon_new"
    SELL_NEW = "sell_new"
    LEAVE_AT_SOURCE = "leave_at_source"

class ItemDisposition(Enum):
    ...
    LEFT_AT_SOURCE = "left_at_source"
```

`TakeTreasure` uses `LEAVE_AT_SOURCE`. The reject option text should express "not taking it for now; the treasure remains where it is"; the action decides whether to remove the POI based on `outcome.accepted`. This design keeps `single_choice` domain-neutral: it neither lets POI logic intrude into the decision engine nor scatters roleplay branches into business actions.

## 6. API and Frontend

### 6.1 Reusing existing APIs

No treasure-specific HTTP endpoint needs to be added:

| Existing interface or mechanism | How treasures plug in |
|---|---|
| `/api/v1/query/world/map` | Reuse `poi.get_summary_payload()` to return all valid treasures |
| tick WebSocket `poi_updates` | `POIManager.add/remove()` automatically upsert/remove |
| `/api/v1/query/detail?type=poi&id=...` | `TreasurePOI.get_detail_payload(world)` returns the treasure detail |
| `MoveToPOI` | Existing general POI move action; no semantic change needed |

Publicly showing all valid POIs on the map is a confirmed product decision; `get_world_map()` must not filter treasures by discoverer.

### 6.2 DTO

Update `web/src/types/api.ts` first, then `web/src/types/core.ts` and the mapper. `POIDetail` should add optional treasure detail:

```ts
treasure?: {
  source: string
  realm: string
  item: {
    kind: 'weapon' | 'auxiliary'
    item_id: number
    name: string
    realm: string
  } | null
  attempt_count: number
  expires_month: number
}
```

Do not use `any`, and do not hardcode in the frontend the user-visible source or realm labels that the backend provides. If sources need localization, the backend should provide stable keys and a localized structured DTO, or the frontend maps them via i18n keys.

### 6.3 Map icons and detail

Assets already generated and accepted:

```text
web/src/assets/icons/pois/
  treasure_01.png
  treasure_02.png
  treasure_03.png
  treasure_04.png
  treasure_05.png
  treasure_06.png
  treasure_07.png
  treasure_08.png
  treasure_09.png
```

During implementation:

1. Explicitly import and register the 9 keys above in `web/src/utils/poiIcons.ts`.
2. `TreasurePOI.icon_key` is randomly chosen from these 9 keys at creation and saved with the save file.
3. `POILayer.vue` reuses the existing texture loading and click events; no need to rewrite the layer for treasures.
4. Existing grave clicks still jump to the deceased Avatar detail; treasures remain ordinary `type: 'poi'` and open `POIDetail.vue`.
5. `POIDetail.vue` branches on `data.kind`: graves show the deceased/grave goods, treasures show source, realm, item, attempt count, and remaining time.

The icon generation tool is `tools/item_icons/generate_treasure_icons.py`: it reads `FAL_API_KEY` from the untracked `tools/img_gen/image_api.env`, calls `openai/gpt-image-2` to generate a 3x3 atlas on a magenta background, then slices, removes background, removes color spill, pixelates, and writes to the asset directory above. The key must not enter git, logs, test assertions, or the frontend bundle.

### 6.4 i18n

The game is English-only: `en-US` is the sole and source locale. Add new entries to the `en-US` split source PO files (under `modules/` / `game_configs_modules/`, not the merged `LC_MESSAGES/*.po` artifacts); after editing, run `python tools/i18n/build_mo.py`.

Add at least:

```text
take_treasure_action_name
take_treasure_description
take_treasure_requirements
poi.treasure.title_short
poi.treasure.source
poi.treasure.realm
poi.treasure.item
poi.treasure.attempt_count
poi.treasure.expires
poi.treasure.empty
```

`.po` `msgid` uses a stable English key or English source text; the display text goes in `msgstr`. Event text, action text, and source text must not hardcode final display text directly in Python logic.

## 7. Implementation Order

1. Complete the POI shared equipment payload helper, and migrate the grave's calls to it.
2. Add `TreasurePOI`, POI loader dispatch, serialization, and detail payload.
3. Add `TreasureService`, configuration, and the `treasure_lifecycle` monthly phase.
4. Extend discovery event text and the precise 240-month dissipation event.
5. Add `KNOWN_TREASURE_POI_ID` and the `TakeTreasure` action, and import/register it in the action package.
6. Add `LEAVE_AT_SOURCE` to item exchange, so that rejection does not consume the treasure.
7. Extend map/detail DTOs, mapper, icon mapping, and POI detail display.
8. Add backend and frontend tests, and run targeted regression, type checking, and locale compilation.

This order completes the backend facts and save files first, then wires in action decisions and display, avoiding the frontend depending on a temporary DTO or state that is not yet persisted.

## 8. Testing and Acceptance

### 8.1 Backend

1. `TreasurePOI.to_save_dict/from_save_dict` preserves all fields, payload, source, discoverers, icon, and attempt count.
2. `POIManager.load_from_list()` restores both graves and treasures.
3. Old saves without `pois` or without treasures load normally.
4. Generation only selects Foundation Establishment, Core Formation, or Nascent Soul weapons or auxiliary equipment, and never produces Qi Refinement treasures.
5. No more generation when active treasures reach 3.
6. The generation position is always valid and never on the same tile as an existing treasure.
7. The emergence event reveals the grade but contains no coordinates.
8. A POI within observation range is always discovered; outside range it is not.
9. Parameter values of `MoveToPOI` and `TakeTreasure` are both executable POI IDs.
10. `TakeTreasure.can_start()` must reject when the POI is undiscovered, expired, not a treasure, on a different tile, or has an empty payload.
11. Success rate covers lower rank, same rank, higher rank, and the 5%/95% boundaries, and does not read unrelated fields such as HP, injuries, or luck.
12. Failure keeps the POI and payload; backlash only affects HP, and lethal damage goes through the normal death entry point.
13. After successful acceptance, avatar equipment is updated, the entire POI is removed, and a major event and remove increment are produced.
14. After success but rejection, the POI/payload remain, and `LEFT_AT_SOURCE` is returned.
15. The treasure is removed exactly at month 240 and a dissipation event is produced, without waiting for annual maintenance.

### 8.2 Frontend

1. `treasure_01` through `treasure_09` are all registered in `POI_ICON_URLS`.
2. When an icon is missing, `fallback_poi` is still used.
3. Map DTO, mapper, and map store can receive treasure summary/upsert/remove.
4. `POILayer` correctly loads and clicks treasure icons.
5. Clicking a treasure opens POI detail and does not trigger the grave-specific jump to the deceased.
6. Treasure detail shows source, realm, equipment, attempt count, and expiry info; grave detail does not regress.
7. `npm run type-check` passes, with no `any` introduced.

### 8.3 Suggested commands

```powershell
& 'C:\Users\wangx\AppData\Local\Programs\Python\Python312\python.exe' -m pytest tests/test_grave_poi.py tests/test_action_poi.py
cd web
npm run test -- poiIcons
npm run type-check
```

After adding treasure tests during implementation, add the corresponding test paths to the first pytest command. If i18n source files are changed, also run:

```powershell
& 'C:\Users\wangx\AppData\Local\Programs\Python\Python312\python.exe' tools/i18n/build_mo.py
```

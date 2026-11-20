# Grave and POI System Spec

This document describes the design for "generating a grave after a cultivator dies" and the point-level Point of Interest (POI) system that follows from it.

Current status: design pending implementation. This document is not a description of a shipped system. Implementation should follow this spec first, and after landing, the "code map" and test commands should be filled in with the real entry points.

## Background

The existing map system uses region as its primary semantic unit. A region represents an area and occupies multiple tiles; the clickable objects on the map are currently mainly regions and living avatars.

Graves are different from regions:

1. A grave is bound to a specific coordinate point `x/y`, not to a region.
2. Death anywhere should leave a grave, including wilderness, tiles without a region, cities, cave dwellings, sects, and ordinary outdoor areas.
3. A grave has a runtime lifecycle: it expires, gets discovered, gets dug up, and gets emptied.
4. The grave is only the first kind of POI; in the future there may be ancient steles, formation eyes, temporary hidden domain entrances, lost magic artifacts, quest clues, and so on.

Therefore the grave should not be built as:

1. Another map representation of the deceased Avatar.
2. An attached field of some region.
3. A one-off list that only serves graves.

A general POI system should be established, with the grave plugged in as the `grave` type.

## Goals

1. After a cultivator avatar dies, generate a grave POI at the death coordinate.
2. The grave is retained for 50 years; the corresponding deceased information also disappears after 50 years.
3. The grave is clickable; clicking shows the corresponding deceased information and the grave status.
4. A grave can only retain the weapon and auxiliary equipment the deceased still held at the time of death; techniques do not go into the grave.
5. If the deceased was killed and looted in battle, the grave only retains the equipment left after looting.
6. Avatars that know of a POI can perform an action to move to the POI.
7. A grave within an avatar's interaction range is always discovered.
8. Avatars can dig graves; digging may succeed, fail, come back empty-handed, or even cause injury.
9. Digging a grave deducts a small amount of luck; righteous avatars are slightly reluctant to dig graves, evil avatars receive no behavioral-tendency penalty but still lose luck.
10. Phase 1 only completes the grave image assets and does not wire in runtime logic.

## Non-goals

1. The first version does not aggregate multiple graves on the same tile for display.
2. In the first version, graves do not block movement.
3. The first version does not include complex social consequences such as "friends and family discover the grave was dug and develop hatred".
4. The first version does not make graves terrain, a region overlay, or an occupiable object.
5. The first version does not require forward compatibility with old saves; during development, clarity of the new structure comes first.
6. The first version does not implement vision isolation in roleplay mode; the god's-eye view frontend can show all currently valid POIs, while avatar action parameters only show POIs known to that avatar.

## Phase Plan

### Phase 1: Grave image assets

Goal: establish grave icon assets, without wiring into backend or frontend runtime.

Deliverables:

1. Generate a 3x3 grave icon preview image.
2. Manually pick and slice it into 9 independent grave icons.
3. Put them in the frontend asset directory, for example:

```text
web/src/assets/icons/pois/
  grave_01.png
  grave_02.png
  grave_03.png
  grave_04.png
  grave_05.png
  grave_06.png
  grave_07.png
  grave_08.png
  grave_09.png
  fallback_poi.png
```

4. Create a POI icon resolution helper, for example `web/src/utils/poiIcons.ts`, which may initially be unused by the runtime.
5. The grave icon style should match existing item icons: pixelated, low detail, clean outlines, recognizable at 32x32 and 64x64.

When the image API is currently unavailable, save the prompt first, have a human run the image generation tool, and then paste the result back into the repo for processing.

Recommended prompt:

```text
Create a 3x3 sprite sheet of nine different tombstone icons for a pixel-art xianxia cultivation world game.

Style requirements:
- Pixel art game item icon style, matching small inventory icons.
- Each icon should be a separate square tile with a clean transparent or pure white background.
- Low detail, readable at 32x32 and 64x64.
- Ancient Chinese fantasy cultivation atmosphere.
- Weathered stone tombstones, small spirit marks, faint jade cracks, old talisman paper, subtle moss, carved runes, small incense ash, or a tiny spiritual glow.
- Somber but not horror-like.
- No skulls, no gore, no realistic corpse elements.
- Avoid modern cemetery shapes; use ancient stone stele forms, rough carved tablets, worn memorial stones.
- Keep silhouettes distinct across all nine variants.
- Palette: muted stone gray, dark ink lines, small accents of aged jade green, faded cinnabar red, or pale spiritual blue.
- Crisp pixel edges, no blur, no painterly rendering, no 3D, no photorealism.

Composition:
- A single 3 by 3 grid.
- Nine icons, evenly spaced.
- Each icon centered and fully visible.
- No text labels outside the icons.
- No UI frame, no decorative background scene.

Output:
- One square image containing the 3x3 sheet.
```

Negative prompt:

```text
photorealistic, high detail, 3D render, anime character, corpse, skull, blood, horror, modern graveyard, large background scene, blurry, soft gradients, vector logo, text, watermark
```

### Phase 2: POI domain model and save/load

Goal: establish the backend POI abstraction, the grave POI, and POIManager, and include them in saves.

Frontend map rendering need not be wired in, but tests should be able to create, save, load, and clean up expired POIs.

### Phase 3: Grave generation on death and 50-year cleanup

Goal: all death entry points uniformly generate graves, and the lifecycles of the deceased and the grave are unified.

### Phase 4: Discovery, moving to POI, and API

Goal: avatars can discover graves, action parameters can select known POIs, and the map/detail API can return POI data.

### Phase 5: Frontend click and grave detail

Goal: render graves on the map, and clicking a grave opens its detail.

### Phase 6: Dig grave action

Goal: implement grave digging, equipment acquisition, failure/injury, luck deduction, and event recording.

## Domain Model

### PointOfInterest abstraction

Suggested new package:

```text
src/classes/poi/
  __init__.py
  poi.py
  grave.py
  manager.py
  serialization.py
```

Suggested base abstraction:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PointOfInterest(ABC):
    id: str
    kind: str
    x: int
    y: int
    name: str
    desc: str = ""
    created_month: int = 0
    expires_month: int | None = None
    discovered_by: set[str] = field(default_factory=set)
    icon_key: str = ""
    is_clickable: bool = True

    @property
    def loc(self) -> tuple[int, int]:
        return self.x, self.y

    def is_expired(self, current_month: int) -> bool:
        return self.expires_month is not None and current_month >= self.expires_month

    def is_discoverable_by(self, avatar: Any) -> bool:
        return True

    def discover(self, avatar: Any) -> bool:
        avatar_id = str(getattr(avatar, "id", ""))
        if not avatar_id or avatar_id in self.discovered_by:
            return False
        self.discovered_by.add(avatar_id)
        return True

    def is_known_by(self, avatar: Any) -> bool:
        return str(getattr(avatar, "id", "")) in self.discovered_by

    @abstractmethod
    def get_detail_payload(self, world: Any) -> dict[str, Any]:
        ...

    @abstractmethod
    def to_save_dict(self) -> dict[str, Any]:
        ...
```

Notes:

1. `id` is a stable ID; names are not used for resolution.
2. `kind` distinguishes `grave` from future ancient steles, formation eyes, etc.
3. `x/y` are tile coordinates.
4. `discovered_by` stores the IDs of avatars that know of this POI.
5. The first version can store the discovery relationship only on the POI, without also maintaining `avatar.known_poi_ids`, to avoid double-write inconsistency.

### GravePOI

Suggested grave fields:

```python
@dataclass
class GravePOI(PointOfInterest):
    kind: str = "grave"
    deceased_avatar_id: str = ""
    deceased_name: str = ""
    death_reason: str = ""
    death_month: int = 0
    realm_at_death: str = ""
    stage_at_death: str = ""
    sect_name_at_death: str = ""
    alignment_at_death: str = ""
    grave_icon_id: str = "grave_01"
    weapon_payload: dict[str, Any] | None = None
    auxiliary_payload: dict[str, Any] | None = None
    weapon_looted: bool = False
    auxiliary_looted: bool = False
    dig_attempt_count: int = 0
```

The grave should store a lightweight snapshot of the deceased, so that within the 50 years the grave detail can still be displayed even if the Avatar object is cleaned up or indexes change.

Equipment payloads only store basic JSON types:

```json
{
  "kind": "weapon",
  "item_id": 1001,
  "name": "Qi Refinement Sword",
  "realm": "Qi_Refinement",
  "special_data": {}
}
```

Auxiliary equipment likewise:

```json
{
  "kind": "auxiliary",
  "item_id": 2001,
  "name": "Spirit Gathering Pearl",
  "realm": "Qi_Refinement",
  "special_data": {}
}
```

The grave does not store:

1. Techniques.
2. Materials.
3. Spirit stones.
4. Elixirs.
5. Complex Avatar object references.
6. Weapon / Auxiliary object references.

## POIManager

Suggested to be attached to `World`:

```python
@dataclass
class World:
    ...
    poi_manager: POIManager = field(default_factory=POIManager)
```

Reasons:

1. POIs are runtime world state, not static map configuration.
2. POIs depend on world time, death, events, and saves.
3. `Map` should continue to be mainly responsible for map structure such as tiles, regions, landmarks, and formations.

Suggested `POIManager` responsibilities:

```python
@dataclass
class POIManager:
    pois: dict[str, PointOfInterest] = field(default_factory=dict)

    def add(self, poi: PointOfInterest) -> None: ...
    def get(self, poi_id: str) -> PointOfInterest | None: ...
    def remove(self, poi_id: str) -> None: ...
    def get_all_active(self, current_month: int | None = None) -> list[PointOfInterest]: ...
    def get_known_by(self, avatar: Any) -> list[PointOfInterest]: ...
    def get_within_observation(self, avatar: Any) -> list[PointOfInterest]: ...
    def discover_nearby(self, avatar: Any) -> list[PointOfInterest]: ...
    def cleanup_expired(self, current_month: int) -> int: ...
    def create_grave_from_avatar(self, avatar: Any, current_month: int) -> GravePOI: ...
    def to_save_list(self) -> list[dict[str, Any]]: ...
    def load_from_list(self, data: list[dict[str, Any]]) -> None: ...
```

## Grave Generation

The unified entry point should be `src/classes/death.py -> handle_death(...)`.

Recommended order:

```python
def handle_death(world: World, avatar: Avatar, reason: Union[str, DeathReason]) -> None:
    reason_str = str(reason)
    avatar.set_dead(reason_str, world.month_stamp)
    world.poi_manager.create_grave_from_avatar(avatar, current_month=int(world.month_stamp))
    world.avatar_manager.handle_death(avatar.id)
    world.deceased_manager.record_death(avatar)
```

Order notes:

1. `avatar.set_dead(...)` records `death_info`, including death time, cause of death, death coordinates, sect snapshot, and alignment snapshot.
2. Grave generation must use `avatar.pos_x/pos_y` or `death_info.location`, not `avatar.tile`.
3. `avatar_manager.handle_death(...)` moves the deceased into `dead_avatars` and sets `avatar.tile = None`.
4. Killing and looting in battle currently happens before `handle_death(...)`, so when the grave is generated, `avatar.weapon/auxiliary` is already the equipment remaining after looting.

Suggested grave ID:

```text
grave:<avatar_id>:<death_month>
```

Suggested grave name:

```text
Grave of {deceased_name}
```

Grave icon:

1. Randomly pick one from `grave_01` to `grave_09`.
2. Once selected, write it to `grave_icon_id` and save it with the save file.
3. Do not re-randomize after loading, to keep the visuals stable.

## Discovery Mechanism

Avatar interaction range reuses the existing observation range:

1. `src/classes/observe.py -> get_avatar_observation_radius(...)`
2. Manhattan distance: `abs(poi.x - avatar.pos_x) + abs(poi.y - avatar.pos_y)`

Rules:

1. A POI within an avatar's interaction range is always discovered.
2. Discovered POIs are written into `poi.discovered_by`.
3. Expired POIs are no longer discovered.
4. The first version does not include hidden difficulty, trap perception, rumor-based discovery, or intelligence propagation.

Suggested new simulator phase:

```text
src/sim/simulator_engine/phases/poi.py
```

Place it after avatar action progression and before annual maintenance, so that an avatar can discover nearby graves in the same tick after moving.

Discovery events:

1. Ordinary grave discovery is a minor event.
2. If future POIs have higher rarity, `is_major` can be decided by POI type.
3. The event's `related_avatars` includes the discoverer; whether the grave's deceased goes into `related_avatars` can be left out for now, to avoid too much impact from event subjects degrading after 50 years.

## Moving to a POI

Two new actions are suggested:

1. `MoveToPoint`: a low-level action that moves by `x/y`, not necessarily exposed to the AI.
2. `MoveToPOI`: the actually exposed action, with parameter `poi_id`.

`MoveToPOI`:

```python
class MoveToPOI(DefineAction, ActualActionMixin):
    ACTION_NAME_ID = "move_to_poi_action_name"
    DESC_ID = "move_to_poi_description"
    REQUIREMENTS_ID = "move_to_poi_requirements"
    EMOJI = "🏃"
    PARAMS = {"poi_id": "poi_id"}
    PARAM_OPTION_SOURCES = {"poi_id": ParamOptionSource.KNOWN_POI_ID}
```

Parameter design:

1. `value` must be `poi.id`.
2. Names are not used as execution parameters.
3. `param_options` can show `name`, `kind`, `x/y`, and distance.

Example:

```json
{
  "value": "grave:avatar-123:600",
  "id": "grave:avatar-123:600",
  "name": "Grave of Li Qing",
  "type": "grave",
  "x": 12,
  "y": 8,
  "distance": 5
}
```

`can_start(...)` checks:

1. The POI exists.
2. The POI has not expired.
3. The avatar knows the POI.
4. The target coordinate is within map bounds.

Execution logic can reference `MoveToRegion`, but the target point is fixed to `poi.x/poi.y`.

Completion condition:

```python
avatar.pos_x == poi.x and avatar.pos_y == poi.y
```

## Dig Grave Action

Suggested new action:

```text
src/classes/action/dig_grave.py
```

Action definition:

```python
class DigGrave(InstantAction):
    ACTION_NAME_ID = "dig_grave_action_name"
    DESC_ID = "dig_grave_description"
    REQUIREMENTS_ID = "dig_grave_requirements"
    EMOJI = "⛏"
    PARAMS = {"poi_id": "poi_id"}
    PARAM_OPTION_SOURCES = {"poi_id": ParamOptionSource.KNOWN_GRAVE_POI_ID}
```

`can_start(...)`:

1. `poi_id` must point to an existing POI.
2. The POI must be a `grave`.
3. The grave has not expired.
4. The avatar must know of the grave.
5. The avatar must be within the grave's interaction range, or more strictly be on the same tile. The first version suggests requiring the same tile, with the action chain `MoveToPOI -> DigGrave` completing the flow.
6. A grave without equipment can also be started, but the result will never successfully obtain an item.

Suggested success rate:

```text
base_success = 0.45
realm_delta = digger_realm_rank - deceased_realm_rank
success_rate = clamp(base_success + realm_delta * 0.15, 0.05, 0.85)
injury_rate = clamp(0.10 - realm_delta * 0.05, 0.02, 0.50)
```

Notes:

1. The higher the digger's realm, the relatively easier it is to succeed.
2. The higher the deceased's realm, the more dangerous the residual restrictions in the grave.
3. When there is no weapon/auxiliary, no successful drop is performed; only an empty-grave result is generated.
4. A grave can be dug multiple times; each attempt increments `dig_attempt_count`.
5. Each piece of equipment can only be dug out once; after being taken, the corresponding payload is cleared or its looted flag is set to True.

Item selection:

1. If both a weapon and an auxiliary exist, prefer the equipment with the higher realm.
2. Random among the same realm.
3. On success, reuse `resolve_item_exchange(...)` so the avatar decides whether to replace existing equipment.
4. If the player/AI rejects the new equipment, it is treated as not taken this time and the grave equipment remains; if this is complex to implement, the first version can also auto-accept only into an empty equipment slot via `auto_accept_when_empty`, and when old equipment exists, the event states that it "could not be carried away".

Luck:

1. Every grave dig deducts a small amount of luck, e.g. `luck_base -= 0.2`, or configurable as `game.grave.dig_luck_penalty`.
2. Both righteous and evil avatars lose luck.
3. The "slight reluctance" of righteous avatars is expressed in AI behavioral tendency, prompt description, or action scoring, not as a `can_start` prohibition.
4. Evil avatars receive no behavioral-tendency penalty but still lose luck.

Injury:

1. Failure may cause injury.
2. Injury amount is determined by the realm difference between the deceased and the digger.
3. When injury reduces HP below 0, go through the existing death resolution; do not hand-write death archiving inside the dig action.

Events:

1. Successfully digging out equipment: `is_major=True`.
2. Failing to dig but getting injured: `is_major=True`, or decided by injury severity.
3. Empty grave, ordinary failure: `is_major=False`.
4. The event's `related_avatars` includes at least the digger.
5. The first version does not factor the deceased's friend/family relationships into event impact.

## Frontend Interface and Rendering

### Map API

Extend `/api/v1/query/world/map` with `pois`:

```json
{
  "pois": [
    {
      "id": "grave:avatar-123:600",
      "kind": "grave",
      "name": "Grave of Li Qing",
      "x": 12,
      "y": 8,
      "icon_key": "grave_01",
      "clickable": true
    }
  ]
}
```

In the first version, the god's-eye view can return all non-expired POIs. Avatar action parameters are still filtered by POIs known to the avatar.

### Detail API

Extend the existing detail query:

```text
GET /api/v1/query/detail?type=poi&id=<poi_id>
```

When `target_type == "poi"`:

1. Read the POI from `world.poi_manager.get(target_id)`.
2. Return 404 if it does not exist or has expired.
3. Call `poi.get_detail_payload(world)`.

Grave detail payload example:

```json
{
  "id": "grave:avatar-123:600",
  "kind": "grave",
  "name": "Grave of Li Qing",
  "desc": "An old, weathered grave; a faint spiritual glow still lingers on its face.",
  "x": 12,
  "y": 8,
  "icon_key": "grave_01",
  "deceased": {
    "id": "avatar-123",
    "name": "Li Qing",
    "age_at_death": 73,
    "realm_at_death": "Foundation_Establishment",
    "stage_at_death": "Middle_Stage",
    "death_reason": "Killed by Wang Wu",
    "death_time": 600,
    "sect_name_at_death": "Azure Cloud Sect",
    "alignment_at_death": "Righteous"
  },
  "grave_goods": {
    "weapon": null,
    "auxiliary": {
      "id": 2001,
      "name": "Spirit Gathering Pearl",
      "realm": "Qi_Refinement"
    }
  },
  "dig_attempt_count": 1
}
```

### WebSocket increments

To avoid "the grave only appears after refreshing the page following a death", the tick payload should add POI increments:

```json
{
  "poi_updates": [
    {"op": "upsert", "poi": {"id": "...", "kind": "grave", "x": 1, "y": 2}},
    {"op": "remove", "id": "..."}
  ]
}
```

If the first version does not do increments yet, it must still let the frontend trigger a re-fetch of map/pois after a death, to avoid graves being out of sync.

### Frontend types and Store

New type:

```ts
export interface POISummary extends EntityBase, Coordinates {
  kind: string
  icon_key?: string
  clickable?: boolean
}
```

Add to `MapResponseDTO`:

```ts
pois?: Array<{
  id: string
  kind: string
  name: string
  x: number
  y: number
  icon_key?: string
  clickable?: boolean
}>
```

Add `pois = shallowRef<Map<string, POISummary>>(new Map())` to the `map` store.

### POILayer

Suggested new file:

```text
web/src/components/game/POILayer.vue
```

And insert it in `GameCanvas.vue`:

```text
MapLayer
SectInfluenceLayer
POILayer
EntityLayer
PerceptionLayer
CloudLayer
```

Click event:

```ts
(e: 'poiSelected', payload: { type: 'poi'; id: string; kind: string; name?: string }): void
```

For grave detail display, suggested new file:

```text
web/src/components/game/panels/info/POIDetail.vue
```

Dispatched by `InfoPanelContainer` on `type === 'poi'`.

## Save and Load

During development, forward compatibility with old saves is not required; new fields can be added directly and the new code can read them with a clear structure.

### World save fields

Suggested addition to the world section:

```json
{
  "pois": [
    {
      "schema_version": 1,
      "id": "grave:avatar-123:600",
      "kind": "grave",
      "x": 12,
      "y": 8,
      "name": "Grave of Li Qing",
      "desc": "An old, weathered grave; a faint spiritual glow still lingers on its face.",
      "created_month": 600,
      "expires_month": 1200,
      "discovered_by": ["avatar-456"],
      "icon_key": "grave_01",
      "is_clickable": true,
      "deceased_avatar_id": "avatar-123",
      "deceased_name": "Li Qing",
      "death_reason": "Killed by Wang Wu",
      "death_month": 600,
      "realm_at_death": "Foundation_Establishment",
      "stage_at_death": "Middle_Stage",
      "sect_name_at_death": "Azure Cloud Sect",
      "alignment_at_death": "Righteous",
      "grave_icon_id": "grave_01",
      "weapon_payload": null,
      "auxiliary_payload": {
        "kind": "auxiliary",
        "item_id": 2001,
        "name": "Spirit Gathering Pearl",
        "realm": "Qi_Refinement",
        "special_data": {}
      },
      "weapon_looted": true,
      "auxiliary_looted": false,
      "dig_attempt_count": 1
    }
  ]
}
```

### Serialization constraints

1. Only store basic JSON types.
2. Cross-object references only store IDs.
3. Equipment stores `item_id + special_data`; on load, instances are restored from the global registry.
4. `discovered_by` is stored as a list of strings and converted back to a set on load.
5. After loading, `grave_icon_id/icon_key` stay unchanged and are not re-randomized.

### Load restoration

On load:

1. Create `world.poi_manager`.
2. Restore all POIs from `world_data["pois"]`.
3. Dispatch to the concrete class by `kind`, e.g. `GravePOI.from_save_dict(...)`.
4. After restoration, do not depend on the deceased Avatar object existing.
5. After restoration, deceased details can be supplemented via `world.deceased_manager.get_record(...)`; if the record does not exist, use the grave's built-in snapshot.

### Cleanup

Clean up together during annual maintenance:

1. `world.avatar_manager.cleanup_long_dead_avatars(..., threshold_years=50)`
2. `world.deceased_manager.cleanup_expired_records(..., threshold_years=50)`
3. `world.poi_manager.cleanup_expired(current_month)`

Configuration:

```yaml
world:
  long_dead_cleanup_years: 50
```

Optionally add:

```yaml
game:
  grave:
    retention_years: 50
    dig_luck_penalty: 0.2
```

But the first version can also reuse `world.long_dead_cleanup_years` first, ensuring the lifecycles of the deceased and the grave stay consistent.

## i18n

The game is English-only; `en-US` is the sole and source locale.

Where new keys belong:

1. Backend action text: `static/locales/en-US/modules/action.po` or the relevant action module.
2. Backend event text: placed in the existing event/action modules.
3. Frontend UI text: `web/src/locales/en-US/game.json` or a new `poi.json`.

The split source `.po` files under `modules/` and `game_configs_modules/` are the source of truth; `LC_MESSAGES/*.po` are merged artifacts and should not be edited directly. After editing, run `python tools/i18n/build_mo.py`.

In `.po` files, `msgid` uses an English source string or a stable key; the display text goes in `msgstr`.

Short-slot suggestions:

1. `poi.grave.title_short`: `Grave`
2. `poi.grave.goods`: `Grave Goods`
3. `poi.grave.dig`: `Dig Grave`
4. `poi.grave.empty`: `Nothing left to take`

## Test Strategy

### Backend unit and integration

1. POIManager add/remove/query and expiry cleanup.
2. GravePOI `to_save_dict/from_save_dict` keep all fields intact.
3. `handle_death()` generates a grave whose coordinates equal the death coordinates.
4. Death anywhere generates a grave, including tiles without a region.
5. After being killed and looted in battle, the grave only stores the remaining equipment.
6. On non-battle death, the grave stores the weapon and auxiliary equipment, but not techniques.
7. The randomized grave icon is saved with the save file and does not change on load.
8. The deceased, the grave, and the deceased record still exist at 49 years and are cleaned up at 50 years.
9. After the deceased is cleaned up, the grave detail can still be displayed within the 50 years using its own snapshot.
10. `discover_nearby()`: always discovers within range, does not discover outside range.
11. `MoveToPOI`: can only move to known, non-expired POIs.
12. `MoveToPOI` parameter option value is the poi id, not the name.
13. `DigGrave`: cannot start for unknown POIs, non-graves, expired graves, or when the distance requirement is not met.
14. `DigGrave`: an empty grave can be executed but will not successfully obtain equipment.
15. `DigGrave`: after success, the corresponding equipment disappears from the grave detail.
16. `DigGrave`: each execution deducts luck; both righteous and evil avatars lose luck.
17. `DigGrave`: failure may cause injury, and the HP change is correct.
18. `DigGrave`: when injury causes death, go through the existing death resolution.

### Frontend

1. `MapResponseDTO` and the mapper correctly receive `pois`.
2. The map store uses `shallowRef` to hold the POI collection.
3. `POILayer` renders grave icons and emits `poiSelected`.
4. `GameCanvas` forwards `poiSelected`.
5. `InfoPanelContainer` can open `POIDetail`.
6. The grave detail shows deceased information, death time, cause of death, and grave goods.
7. After equipment is dug out, the corresponding information is no longer shown.
8. When a grave icon is missing, the fallback is used.

## Code Areas to Modify

Expected to involve:

```text
src/classes/death.py
src/classes/core/world.py
src/classes/poi/**
src/classes/action/param_options.py
src/classes/action/move_to_poi.py
src/classes/action/dig_grave.py
src/classes/action/__init__.py
src/sim/simulator_engine/phases/**
src/sim/save/sections/**
src/server/services/game_queries.py
src/server/loop_runtime.py
web/src/types/api.ts
web/src/types/core.ts
web/src/api/mappers/world.ts
web/src/stores/map.ts
web/src/components/game/GameCanvas.vue
web/src/components/game/POILayer.vue
web/src/components/game/panels/info/**
web/src/utils/poiIcons.ts
web/src/assets/icons/pois/**
static/config.yml
static/locales/en-US/modules/**
web/src/locales/en-US/**
tests/**
web/src/__tests__/**
```

New actions must:

1. Be imported and registered in `src/classes/action/__init__.py`.
2. Add `can_possibly_start` tests, especially for the branches with no known grave, a grave within range, an empty grave, etc.
3. Add parameter option tests, ensuring `param_options.value` can be parsed by the action execution layer.

## Verification Commands

Backend, run according to the scope of changes:

```powershell
pytest tests/test_death.py tests/test_save_load_death.py tests/test_deceased_manager.py
pytest tests/test_action_param_options.py tests/test_action_can_possibly_start.py
pytest tests/test_public_api_v1.py tests/test_websocket_handlers.py
```

After adding POI tests, they can be run separately:

```powershell
pytest tests/test_poi_system.py tests/test_grave_poi.py tests/test_action_dig_grave.py tests/test_action_move_to_poi.py
```

Frontend, run according to the scope of changes:

```powershell
cd web; npm run type-check
cd web; npm run test -- --run
```

If only doing the Phase 1 image assets, at least manually check:

1. PNG file sizes are consistent.
2. The grave body is not empty.
3. Still recognizable at small sizes.
4. Background is transparent or consistent with the existing icon system.
5. File names match the `poiIcons.ts` mapping.

## Design Trade-off Record

1. Digging a grave still deducts luck; both righteous and evil avatars lose luck.
2. Evil avatars receive no "slight reluctance to dig graves" behavioral-tendency penalty.
3. The first version does not aggregate multiple graves.
4. The first version allows repeated digging, but each piece of equipment can only be dug out once.
5. A successful dig or a severe failure can be a major event.
6. Graves do not block movement.
7. The first version does not include complex consequences such as revenge by friends and family or sect reputation penalties.
8. Death at any map point generates a grave.
9. Deceased information disappears after 50 years; old event subjects may degrade to IDs, which is an acceptable result.

## Future Extensions

Possible future extensions:

1. Aggregated display of multiple POIs on the same tile.
2. Social propagation and hatred after a grave is dug.
3. Special events such as grave feng shui, luck, resentment, and corpse transformation.
4. Restrictions, formations, and grave-guarding spirits in high-realm graves.
5. POI intelligence trading, rumor-based discovery, and map marker sharing.
6. Filtering visible POIs by the controlled avatar in roleplay mode.
7. External control API query and command interfaces, e.g. `query/poi/list`, `command/avatar/move-to-poi`.
8. Other POI types: ancient steles, formation eyes, hidden domain entrances, lost magic artifacts, battlefield ruins.

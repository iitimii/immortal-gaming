# Region-First Map System Spec

This document records the region-first map system that has already landed. The map system has moved from the early `tile_map.csv + region_map.csv` dual-matrix maintenance approach to schema v2, with `static/game_configs/maps/<map_id>/map.json` as the source of truth for official maps.

## Current Conclusions

Maps use region as the primary semantics:

1. A region can occupy multiple cells on the map.
2. A region is currently allowed to bind only one tile image.
3. Different regions can interlock, forming more natural map boundaries.
4. `-1` means no region, i.e. wilderness.
5. Wilderness uses the map's own `wilderness_tile`, which can be `plain` or another valid tile such as `sea`.
6. Only regions are clickable on the map; tiles are not independent interactive objects.
7. The positions of large images such as cities, sects, cave dwellings, and ruins are controlled by `landmarks`; when not configured, they fall back to the region center.
8. Map-specific differences in region names and descriptions are expressed through `region_overrides`.

This system only addresses the consistency of the map source format, map loading, snapshots, and maintenance tools. It does not introduce complex geographic systems such as random map generation, a player editor, road/river networks, height and climate, or war/disaster terrain overlays.

## Code Map

Main entry points of the current map system:

1. `static/game_configs/maps/<map_id>/map.json`: source of truth for official map presets.
2. `static/game_configs/maps/<map_id>/meta.json`: map preset metadata.
3. `static/game_configs/region_tile.csv`: binding of regions to the base tile / landmark asset.
4. `src/run/map_source.py`: reads, validates, and serializes the map source, and derives the tile matrix from the region matrix.
5. `src/run/load_map.py`: loads a `MapSource` into runtime `Map` / `Tile` / `Region` objects.
6. `src/run/map_snapshot.py`: saves and reads the schema v2 map snapshot in save files.
7. `src/classes/environment/map.py`: the runtime map object, holding map-level information such as `landmarks`, `wilderness_tile`, and `region_overrides`.
8. `src/server/services/game_queries.py`: external queries for the map and region detail, reading runtime region information.
9. `tools/map_creator/main.py`: region-first map design tool, reads and writes `map.json`.
10. `tools/map_presets/validate_presets.py`: official map preset validation.
11. `tools/map_presets/render_preview.py`: generates local preview images.
12. `tools/map_presets/export_frontend_previews.py`: exports the preview SVGs used by the frontend.

The historical dual-CSV path is no longer the main path for official maps. Future maintenance should not re-spread `tile_map.csv` / `region_map.csv` as parallel sources of truth.

## Data Format

Each official map preset directory:

```text
static/game_configs/maps/
  classic/
    meta.json
    map.json
  island_seas/
    meta.json
    map.json
  mountain_frontier/
    meta.json
    map.json
```

Current `map.json` format:

```json
{
  "schema_version": 2,
  "id": "island_seas",
  "version": 2,
  "width": 84,
  "height": 60,
  "wilderness_tile": "sea",
  "region_overrides": {
    "102": {
      "name": "North Sea Sand Isle",
      "desc": "An island in the northern seas ringed by white sand and shallow reefs."
    },
    "305": {
      "name": "Lanyue Harbor",
      "desc": "A harbor city with calm tides, where moonlight falls between the long breakwater and the sails at night."
    }
  },
  "region_rows": [
    [-1, -1, 102],
    [-1, 102, 102]
  ],
  "landmarks": {
    "305": {
      "x": 50,
      "y": 18,
      "asset": "city_305"
    }
  }
}
```

Field descriptions:

1. `schema_version`: map source format version, currently `2`.
2. `id`: map ID; must match the directory name and `meta.json.id`.
3. `version`: official map preset version; incremented when map content is adjusted.
4. `width` / `height`: map dimensions.
5. `wilderness_tile`: the tile used by `-1` wilderness cells; must be a valid `TileType`.
6. `region_rows`: the main matrix, storing only region ids; `-1` means wilderness.
7. `landmarks`: positions and assets of large visual markers.
8. `region_overrides`: map-local overrides of region display text; currently supports `name` and `desc`.

Not stored:

1. `tile_rows` is not stored.
2. Per-cell tiles are not stored.
3. Per-cell terrain overrides are not stored.
4. Future runtime overlays are not stored.

`region_overrides` is the exception: it is not a full copy of gameplay static metadata, but the map preset's own display semantics. It solves the problem of "the same region id needing a different geographic name or description in different maps".

## Region Tile Binding

The binding of regions to tiles is maintained centrally in `static/game_configs/region_tile.csv`; the map matrix itself does not express tiles.

Example:

```csv
region_id,tile,landmark_asset
101,plain,
102,desert,
112,farm,
201,mountain,cave
206,mountain,ruin
301,city,city_301
401,mountain,sect_1
```

Resolution rules:

1. When `region_tile.csv` has an explicit entry, use it.
2. When a `city` region has no explicit entry, the tile is `city` and the landmark is `city_<region_id>`.
3. When a `sect` region has no explicit entry, the tile is `mountain` and the landmark is `sect_<sect_id>`.
4. When a `cultivate` region has no explicit entry, the tile is `mountain` and the landmark is its `sub_type`, e.g. `cave` / `ruin`.
5. A `normal` region must have an explicit tile entry; a missing one is an error.
6. Wilderness uses the current map's `wilderness_tile`.

Key constraints:

1. A region can have only one tile image.
2. Manually assigning different tiles to different cells of the same region is not allowed.
3. For richer boundaries, interlock different regions instead of adding per-cell tile overrides to the same region.
4. `tile` is the base terrain image; `landmark_asset` is the 2x2 or special overlay image; the two must not be merged into one field.

## Wilderness Semantics

`-1` means no region, i.e. wilderness.

Wilderness is not a clickable region and does not enter region detail. If the frontend supports clicking cells in the future, it should resolve the cell's region first; when the value is `-1`, it does not open the region panel.

The wilderness tile is decided by the map:

1. The classic map and the mountain frontier can use `plain`.
2. The archipelago map can use `sea`, making large sea areas a non-clickable, no-region sea surface.

Do not restore the dual-matrix main path to express no-region landforms such as sea areas or uninhabited snow mountains. If multiple no-region landforms are truly needed in the future, a base terrain layer should be redesigned, rather than diluting this round's region-first source of truth back into two matrices.

## Landmark

A region's extent represents "which cells this region occupies". The large images of cities, sects, cave dwellings, and ruins represent "where this region's visual marker is placed". The two are separate.

Rules:

1. Landmark coordinates must be within the map bounds.
2. The landmark anchor cell should belong to the corresponding region.
3. A 2x2 landmark must fall entirely within the map bounds.
4. A 2x2 landmark's footprint should in principle fall inside the corresponding region as much as possible; when a small cross-boundary overlap is allowed, the validator should give a warning instead of passing silently.
5. When no landmark is configured, the region center is used as a fallback.

Keep the semantics consistent during maintenance: if a city's name or description implies it is among mountains, a harbor, a sand isle, or a forest sea, the terrain around the landmark and the map's description should match. If they do not match, prefer moving the region / landmark, or add `region_overrides`.

## Region Overrides

`region_overrides` are map-local overrides of region display text, stored by region id in `map.json`.

Currently supported fields:

1. `name`: overrides the region name.
2. `desc`: overrides the region description.

Loading flow:

1. `src/run/map_source.py` reads and validates `region_overrides`.
2. `src/run/load_map.py` applies the overrides when creating a `Region`.
3. The runtime `Map.region_overrides` keeps the override information.
4. `src/run/map_snapshot.py` writes the overrides into the save snapshot and restores them when loading the save.
5. The region detail query naturally returns the overridden name and description.
6. `tools/map_creator/main.py` reads and writes `regionOverrides`, so they are not lost when the editor saves.

Usage principles:

1. When all maps share a region's meaning, change the global region CSV.
2. When only one map needs a different geographic name, direction, or harbor/mountain town/sand isle semantics, use `region_overrides`.
3. Do not pollute the global region configuration for one map's text difference.
4. The description must match the actual position, surrounding terrain, and landmark position in that map.
5. Use direction words carefully. For example, if "South Sea Sand Isle" is actually on the north side of the map, rename it to "North Sea Sand Isle" or to a name without a direction.

i18n note: `en-US` is the sole and source locale, so `region_overrides` text is maintained directly in English.

## Connectivity and Boundaries

Regions are allowed to interlock, and boundaries need not be regular. This lets farmland, forest seas, mountains, and sandy land form a realistic map feel.

But regions should not shatter into an unreadable scatter of fragments:

1. A `city` region must be contiguous.
2. A `sect` region must be contiguous.
3. A `cultivate` region must be contiguous, unless a certain kind of hidden domain is explicitly designed later to have multiple entrances.
4. A `normal` region may have a few separate components, to represent natural forms such as mountain spurs, forest sea edges, and embedded farmland.
5. The number of connected components of a `normal` region is limited by the validator; exceeding the limit should be an error or warning.
6. Every region must have at least one cell.

Boundary maintenance suggestions:

1. Avoid long purely straight edges, especially for mountains, forest seas, deserts, and coasts.
2. Large homogeneous areas can keep their main shape, but edges should have small-scale interlocking, peninsulas, valleys, oases, or foothill transitions.
3. A small patch that appears abruptly must have a geographic reason, such as an oasis, isolated island, mountain pass, or river bend; otherwise merge or delete it.
4. Different maps should express their differences mainly through overall topology, rather than only changing local shapes.

## Semantic Consistency

Map text, geographic position, tile binding, landmarks, and surrounding regions must all explain each other.

Typical issues already fixed:

1. In the archipelago map, "South Sea Sand Isle" was on the north side, so it was renamed "North Sea Sand Isle".
2. In the archipelago map, "Lanyue City" was not among mountains, so it was renamed "Lanyue Harbor", which better fits the island semantics.
3. Cities and special locations in the mountain frontier map use override text that better fits mountain ridges, gorge rivers, and border towns.

When checking maps later, focus on:

1. Whether region names with direction words are really located in the corresponding direction.
2. Whether city/sect/cave dwelling descriptions match the surrounding terrain.
3. Whether the archipelago map avoids large land texts directly inheriting continental semantics.
4. Whether the mountain map avoids city, farmland, and hidden domain text conflicting with the high-mountain frontier topology.
5. Whether strongly semantic landforms such as deserts, snow mountains, and sea areas are correctly expressed in region names and descriptions.

Fixes, in order of priority:

1. Move the region or landmark so the visuals and text agree.
2. Use `region_overrides` to override the name and description for that map.
3. If all maps should change, adjust the global region CSV.

## Save Snapshot

The map snapshot is currently schema v2.

Structure:

```json
{
  "schema_version": 2,
  "preset_id": "island_seas",
  "preset_version": 2,
  "width": 84,
  "height": 60,
  "wilderness_tile": "sea",
  "region_rows": [
    [-1, -1, 102],
    [-1, 102, 102]
  ],
  "landmarks": {
    "305": {
      "x": 50,
      "y": 18,
      "asset": "city_305"
    }
  },
  "region_overrides": {
    "305": {
      "name": "Lanyue Harbor",
      "desc": "A harbor city with calm tides."
    }
  },
  "region_tile_overrides": {}
}
```

Notes:

1. The save stores the actual `region_rows` of the current run.
2. The save stores the actual `wilderness_tile` of the current run.
3. The save stores the actual `landmarks` of the current run.
4. The save stores the actual `region_overrides` of the current run, ensuring that region display semantics after loading are not broken by later changes to preset files.
5. `region_tile_overrides` is reserved for future runtime changes where "an entire region switches images"; it is currently always empty.
6. No per-cell tile overlay is reserved until future gameplay clearly needs it.

During the development phase, long-term compatibility with old v1 snapshots is not required. The current code keeps a low-cost v1 read path, but new designs should not introduce dual-track complexity for the old format.

## Map Design Tool

`tools/map_creator` already reads and writes `map.json` in the region-first way.

Main editing path:

1. Select a region.
2. Paint region ownership on the map.
3. Tile images are automatically derived from `region_tile.csv` and `wilderness_tile`.
4. When wilderness is selected, set the cell's region to `-1`.
5. Write back to `map.json` on save.
6. The editor must preserve and write back `regionOverrides` / `region_overrides`; map-specific text must not be lost after saving.

Frontend fields in the tool's API use camelCase, for example:

1. `regionRows`
2. `wildernessTile`
3. `regionOverrides`
4. `landmarks`

When written to disk they are converted to the snake_case fields of `map.json`.

## Frontend Interaction

The current frontend map interaction object is the region, not the tile.

Constraints:

1. Tiles are not clickable.
2. Clicking a map label selects a region.
3. If clicking map cells is supported later, it should also resolve to "clicking that cell's region".
4. If the cell is `-1` wilderness, region detail is not triggered.
5. The frontend does not show a tile detail panel.
6. The frontend does not hardcode a user-visible region-to-tile label mapping.

The map query API can continue to return the renderable tile matrix and region summaries; summary coordinates for large regions should prefer the landmark, then fall back to the center.

## Current Official Map Strategy

The current official presets are:

1. `classic`: a balanced continent.
2. `island_seas`: an archipelago sea area; `wilderness_tile` is `sea`, and large sea areas are `-1` non-clickable areas.
3. `mountain_frontier`: mountains, woodland, and a cold frontier.

Current tests still require the three official maps to use the same set of region ids. This is a preset convention for the current stage, keeping gameplay configuration, avatar distribution, and verification cost stable; it is not a fundamental limitation of the schema.

If different maps are to have truly different region rosters in the future, the following must be adjusted in sync:

1. The map validator, so it no longer forces all official maps to have the same region set.
2. Logic that depends on the global region set, such as avatar spawning, action parameters, and region option sources.
3. Empty states for the frontend region list and detail.
4. How saves and the external control API describe map differences.
5. The corresponding tests and documentation.

Until then, map differences are mainly achieved through:

1. Topological differences in `region_rows`.
2. Differences in `wilderness_tile`.
3. Differences in `landmarks` positions.
4. Text differences in `region_overrides`.

## Validation and Verification

After modifying an official map, run at least:

```powershell
python tools\map_presets\validate_presets.py
```

When previews are involved, run:

```powershell
python tools\map_presets\render_preview.py --all
python tools\map_presets\export_frontend_previews.py
```

To view all soft hints, run:

```powershell
python tools\map_presets\quality_audit.py
```

When loading, saves, queries, or the editor are involved, run according to the scope of the change:

```powershell
pytest tests/test_map_presets.py tests/test_save_load_map_snapshot.py
pytest tests/test_init_status_api.py tests/test_websocket_handlers.py
pytest tests/test_csv_loading.py
cd web; npm run type-check
cd web; npm run test -- --run
```

The validator should cover:

1. `meta.json.id`, the directory name, and `map.json.id` are consistent.
2. `schema_version == 2`.
3. `width` / `height` match the dimensions of `region_rows`.
4. `wilderness_tile` is a valid `TileType`.
5. All region ids exist in the region metadata configuration.
6. At the current stage, official maps use the same set of region ids.
7. Every region has at least one cell.
8. `normal` regions have a tile binding.
9. The tile in a tile binding is a valid `TileType`.
10. The landmark asset has a corresponding resource, or follows the existing resource naming rules.
11. Landmark coordinates are within the map bounds.
12. The landmark anchor belongs to the corresponding region.
13. A 2x2 landmark does not go out of bounds.
14. city / sect / cultivate regions are contiguous.
15. The number of connected components of a normal region does not exceed the threshold.
16. Region ids in `region_overrides` must exist.
17. Low-false-positive structural quality items in `quality_audit.py`:
    - In `classic` / `mountain_frontier`, the `106` water system is contiguous and connects to `105`.
    - No tiny water / sea component may appear.
    - Normal regions must not have overly small detached fragments.
    - Large normal regions must not be overly blocky.
    - Normal regions must not have overly long internal straight edges.
    - Landmark 2x2 footprints must not be a poor fit.

`landmark_near_boundary` is still a soft hint, shown only in the `quality_audit.py` report and not a `validate_presets.py` hard fail. Archipelagos, small islands, harbors, cave dwellings, and similar semantics often naturally hug edges; whether to move them should be judged by hand with the preview images.

Aesthetic and narrative semantics still need human review. After each major map adjustment, spot-check names, descriptions, direction words, city positions, terrain around sects/cave dwellings, and the preview images. The full background of map quality optimization is in `docs/specs/map-quality-optimization.md`.

## Future Room

If map evolution is to be added in the future, the following should be redesigned:

1. An entire region switching tile images, e.g. a city falling into ruins or a forest burning down.
2. Runtime overlays for local cells.
3. Whether no-region landforms upgrade from a single `wilderness_tile` to a base terrain layer.
4. Independent geographic layers such as roads, rivers, borders, and coastlines.
5. The external control API modifying region ownership or landmarks.
6. A complete contract for different maps having different region rosters.

None of these are within the scope of the currently landed system. The core remains: the official map source format uses `region_rows` as the only semantic matrix, and tiles are derived from region bindings and the wilderness tile.

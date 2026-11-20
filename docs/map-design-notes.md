# Map Design Notes

A short design note for the official map expansion, recording *why* things are done this way and which boundaries current maintenance should respect. For implementation details see:

- `docs/specs/region-first-map-system.md`

## Core Decision

The first version of the map system does no procedural generation and no complex geographic sandbox.

It is currently better served by "official map presets + map snapshots":

1. A small number of quality-controlled official maps are provided.
2. Players choose a map when starting a game.
3. Saves store a snapshot of the run's map.
4. If avatar actions later change the map, the change can be written straight into the snapshot.

This gives worlds distinct spatial character without dragging the system prematurely into procedural generation, geographic simulation, economic networks, and cultural derivation.

## Current Map Goals

The official maps currently vary only map shape and spatial relationships:

1. Expand from one map to three official maps.
2. All three maps share the same dimensions.
3. No new regions.
4. No new tile types.
5. No new local-culture fields.
6. Only region shape, area, and position change.

In other words, the same region id still represents the same region in every official map, but it may appear in a different place with a different size and boundary shape.

## The Three Official Maps

### Central Nine Provinces (`classic`)

The default, balanced continent.

Suited for new players and ordinary starts. Terrain is fairly evenly distributed; cities, sects, cave dwellings, and wilderness don't lean too heavily toward any one style.

### Ten Thousand Mountains (`mountain_frontier`)

More mountains, forests, and perilous terrain.

It should feel more like a frontier with dangerous cultivation grounds: cities cluster in valleys or mountain passes, while sects and cave dwellings sit closer to ranges, dense forests, snowy peaks, and similar places.

### Azure Isles (`island_seas`)

More water, coastline, and islands.

It should make the world feel more scattered: regions are spread across several islands, peninsulas, or coastal belts, and cities mostly sit near coasts, inner bays, or river mouths.

## Map Presets vs. Map Snapshots

`map_id` identifies which official map the run started from.

`map_snapshot` is the run's current, actual map.

The two concepts must stay separate:

1. On a new game, the official map is read via `map_id`.
2. During play, the map may be changed by future systems.
3. On save, the full `map_snapshot` is written.
4. On load, `map_snapshot` is restored first, rather than re-reading the official map.

That way, even if official map files are updated later, old saves keep the map state they had at the time.

## Why Save the Full Map

Maps are currently small, so saving the full region-ownership matrix is cheap.

There is no compression and no diff-only saving for now. This keeps the implementation straightforward, the tests simpler, and future map changes easier to integrate.

## Maintenance

Do not bring back the old `tile_map.csv` / `region_map.csv` dual-matrix main path.

The maintenance workflow is:

1. Edit or generate `static/game_configs/maps/<id>/map.json`, updating `static/game_configs/region_tile.csv` if needed.
2. Run the map validation tool.
3. Generate preview images.
4. Review the previews and fix the spatial structure.
5. Verify in the real frontend: map rendering, labels, the sect layer, and avatar positions.

Maps are visual assets; they must be adjusted by looking at them.

## Future Directions

This round only adds official map presets. Later extensions could include:

1. Regional local culture.
2. Avatar birthplaces and regional character.
3. Sect locations influencing sect style.
4. Event locations influencing story text.
5. Disasters, wars, and sect actions changing the map.
6. The external control API querying or modifying map state.

All of these build on the first version's `map_id + map_snapshot` foundation.

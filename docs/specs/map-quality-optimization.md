# Map Quality Optimization Spec

This document records the design judgments, potential issues, phased plan, and acceptance criteria for optimizing the quality of the official maps. It builds on the existing region-first map system and does not replace `docs/specs/region-first-map-system.md`; instead it adds a quality layer about "whether the map looks reasonable, looks good, and is easy to maintain".

## Background

The official maps have already converged on schema v2:

1. The source of truth for official maps is `static/game_configs/maps/<map_id>/map.json`.
2. `region_rows` is the only semantic matrix and stores only region ids.
3. Tiles are derived from `static/game_configs/region_tile.csv` and `wilderness_tile`.
4. A region is currently allowed to bind only one tile.
5. The positions of large images such as cities, sects, cave dwellings, and ruins are controlled by `landmarks`.
6. Map-local differences in names and descriptions are controlled by `region_overrides`.

This design suits the current stage. We should not restore the `tile_map.csv + region_map.csv` dual matrix to fix how the map looks, nor introduce per-cell terrain overrides as a new main path.

The current problem is mainly not a wrong schema choice, but that the official map content and the toolchain have not yet formed a stable quality gate: maps can be painted into large blocky regions, water systems can be cut off, and the editing tool also risks writing broken official map dimensions.

## Currently Observed Issues

### Map Design Issues

1. Water system topology is unstable.
   - `106` is a region with strong water-system semantics in the global configuration.
   - In `classic`, `106` is currently split into multiple water segments, which visually looks like a river that has been cut off.
   - In `mountain_frontier`, `106` is also split into multiple segments, which does not match the map override text "a gorge river rushing through".
   - In `island_seas`, `106` as a tidal channel may have multiple segments, but should read as straits, channels, and inner bays, rather than random water blobs.

2. Large regions are too blocky.
   - The bodies of desert, rainforest, ice field, mountain, grassland, poison marsh, coast, and similar regions are too solid.
   - Even without very long straight boundaries, they still look as if they were laid down with a rectangle or a big round brush.
   - They lack natural forms such as foothills, bay mouths, headlands, river bends, oases, forest edges, spurs, and peninsulas.

3. Boundaries are not jagged enough, yet fragments lack semantics.
   - Natural boundaries need to interlock, but not as a scatter of fragments everywhere.
   - A few small patches of 1 to 5 cells look like painting mistakes if there is no geographic explanation such as an oasis, outlying island, lagoon, mountain pass, or tributary.

4. Map semantics and visual positions easily drift apart.
   - Global region names carry direction, landform, and purpose semantics.
   - Map override text can correct local semantics, but if the shape and landmark do not match, the text correction also looks forced.
   - Cities, sects, cave dwellings, and ruins should sit near positions that match their descriptions, not merely satisfy the requirement that the landmark anchor belongs to the region.

5. The differences between the three official maps could be stronger.
   - `classic` should be a balanced continent, focusing on the complete geographic relationship among the main river, the Eastern Sea, the Western Regions, the Southern Frontier, and the Northern Border.
   - `island_seas` should be dominated by archipelagos, straits, harbors, inner bays, and outlying islands, rather than continental landforms broken into small pieces scattered on the sea.
   - `mountain_frontier` should be dominated by mountain ranges, valleys, gorge rivers, border towns, and wastelands, rather than simply enlarging the area of the mountain tile.

### Code and Toolchain Issues

1. Save dimensions in `tools/map_creator/main.py` are risky.
   - The constants are still `MAP_WIDTH = 70`, `MAP_HEIGHT = 50`.
   - The official maps are currently `84x60`.
   - Loading reads the real dimensions of the map source, but saving still rebuilds the matrix from the constants, which may crop the map.

2. `tools/map_creator/main.py` currently loads only `classic` by default.
   - `DEFAULT_MAP_ID = "classic"` is fixed.
   - There is no main path for selecting `mapId` from the URL or the API.
   - When maintaining the three official maps it is easy to edit the wrong one or be unable to edit the target preset directly.

3. The map editor's save payload does not sufficiently reuse the existing parser / serializer.
   - `src/run/map_source.py` already has `MapSource`, `map_source_to_dict`, and read and validation logic.
   - The editor currently assembles the JSON itself, which easily drifts from the main path.

4. The validator focuses on format correctness and lacks a quality audit.
   - The existing `tools/map_presets/validate_presets.py` already checks schema, region ids, connectivity, landmark anchors, etc.
   - Visual checks currently cover only a few special cases, such as island/plain noise in the archipelago and an overly straight left edge of the mountains.
   - It does not yet systematically check water continuity, small fragments, isolated water blobs, blockiness, coast/riverbank quality, or semantic anchors.

5. Runtime region creation failures currently only `print`.
   - In `src/run/load_map.py`, `_load_and_assign_regions()` prints an error and continues when region creation fails.
   - For official maps, this can turn a data error into a hidden failure where "the map loads but is missing regions".
   - The validator can catch it first, but the loader should also fail fast for official presets where possible.

6. The frontend map preview component hand-writes preset imports.
   - `web/src/components/game/panels/system/MapPresetPreview.vue` directly imports three SVGs.
   - `tools/map_presets/export_frontend_previews.py` can export all presets, but the frontend display table still needs manual syncing.
   - When adding maps later, it is easy to end up in a state where a preview is exported but not shown in the frontend.

7. The preview system is fragmented.
   - `render_preview.py` outputs PNGs for human review.
   - `export_frontend_previews.py` outputs SVGs for the frontend start page.
   - The two maintain duplicate color tables and marker rules, which may diverge in the future.

8. Map quality issues lack reproducible reports.
   - Currently someone has to look at the image to discover "the river is broken" or "it is too regular".
   - There should be machine-readable audit output, so PRs, tests, and human review share a common language.

## Design Principles

1. Stay region-first.
   - This round does not add a tile layer, river layer, road layer, or height layer.
   - Do not restore the old dual matrix.
   - Do not add per-cell tile overrides for a single region.

2. Improve map quality primarily through `region_rows`.
   - Water systems are expressed by the continuous shape of water regions.
   - Coasts are expressed by the boundaries between sea, island, sea wilderness, and land regions.
   - Mountains, forests, deserts, and grasslands express transitions through interlocking regions.

3. Automation only assists; no fully random generation.
   - Official maps are visual assets and need human review.
   - Scripts can be used to find issues, generate candidate boundary perturbations, and compute quality metrics.
   - The final `map.json` should be a reviewable deterministic result.

4. Do not use fragments to fake naturalness.
   - Natural boundaries need a main body and direction.
   - Small patches must have geographic semantics; otherwise merge or delete them.
   - city / sect / cultivate regions should stay clear and contiguous.

5. Text, landmark, and shape must agree.
   - Names and descriptions containing direction words, river/sea words, mountain/valley words, or harbor words must match the actual position.
   - Prefer moving the region / landmark; otherwise use `region_overrides` to correct the local name.

6. Layered quality gates.
   - Format and runtime contract errors should hard fail.
   - Aesthetic metrics are first output as audit warnings, and gradually turned into hard fails once stable.

## Phased Plan

### Phase 0: Fix Safety Issues in Maintenance Tools

Status: landed.

Goal: ensure later edits to the three official maps will not be broken by the toolchain.

Tasks:

1. Fix save dimensions in `tools/map_creator/main.py`.
   - Use `width` / `height` from the request when saving.
   - If missing from the request, fall back to `width` / `height` read from the current `map.json`.
   - Forbid unconditionally using `MAP_WIDTH` / `MAP_HEIGHT` when saving.

2. Support selecting a map preset.
   - `load_map_data()` accepts a `map_id`.
   - `/api/init` supports `?mapId=<id>`.
   - `/api/save` uses `mapId` from the payload and validates that the directory exists or creation is explicitly allowed.
   - Page initialization can read `mapId` from the URL query.

3. Preserve map source metadata when saving.
   - Keep the existing `schema_version`.
   - The rule for keeping or correctly incrementing `version` needs to be made explicit.
   - Keep `wilderness_tile`, `landmarks`, and `region_overrides`.
   - Output still uses `ensure_ascii=False, indent=2` and ends with a newline.

4. Add a tool-level smoke test.
   - Cover at least: after reading an `84x60` map and saving, it is still `84x60`.
   - Cover: saving a non-classic map does not write to classic.
   - Prefer extracting pure functions for tests, to avoid starting the Flask server.

Acceptance:

1. After reading and writing `classic` with the map editor, `width=84`, `height=60`, and the `region_rows` dimensions are unchanged.
2. Reading and writing `island_seas` and `mountain_frontier` with the map editor does not overwrite `classic`.
3. `python tools\map_presets\validate_presets.py` passes.

Landed:

1. `tools/map_creator/main.py` now saves using the real dimensions from the request or the existing `map.json`.
2. The map editor supports loading and saving a specific preset via `?mapId=<id>`.
3. The save payload carries `mapId`, `width`, `height`, and `regionOverrides`.
4. Unless creation is explicitly allowed, unknown map ids are rejected.
5. Added `tests/test_map_creator.py`, covering dimension preservation, non-classic read/write, unknown map rejection, and rejection of path-like map ids.

### Phase 1: Establish a Map Quality Audit

Status: first version landed.

Goal: turn "the river is broken", "too square", and "too fragmented" into reproducible reports.

Tasks:

1. Add quality audit capability under `tools/map_presets`.
   - It can be integrated into `validate_presets.py`, or first added as `audit_quality.py`.
   - Recommend outputting a warning report first, to avoid too many hard fails early on.

2. Audit metrics:
   - Number of region connected components and the area of small fragments.
   - Number of water / sea connected components.
   - Whether `106` is contiguous in `classic` and `mountain_frontier`.
   - Whether `106` makes reasonable contact with `105` or a coastal outlet.
   - Isolated water / sea / normal region components below a threshold.
   - Blockiness of large regions, e.g. `area / bbox_area`, perimeter, rate of boundary direction change.
   - Long straight lines and long staircases on region boundaries.
   - Whether most of a landmark's 2x2 footprint falls inside its region.
   - Whether a landmark is too close to its region's boundary.

3. Output format:
   - Console-friendly text for human reading.
   - Optional JSON for later CI or PR comments.
   - Each warning includes map id, region id, issue type, key values, and a suggested action.

4. Tests:
   - Add unit tests for the audit's pure functions.
   - Use small matrices to cover scenarios such as broken rivers, isolated water blobs, overly high fill ratios, and small fragments.

Acceptance:

1. The audit script outputs stable reports for the three official maps.
2. Even if the existing maps have warnings, they do not block the basic validation of `validate_presets.py` unless strict is explicitly enabled.
3. Small-matrix tests cover the core metrics.

Landed:

1. Added `tools/map_presets/quality_audit.py`.
2. The audit supports a console report, `--json` machine-readable output, and `--strict` non-zero exit.
3. The current first-version metrics include:
   - Region connected components and small fragments.
   - Small water / sea components.
   - Continuity and sea outlet of `106` in `classic` / `mountain_frontier`.
   - Blockiness of large normal regions.
   - Long straight edges of normal regions.
   - Landmark 2x2 footprint fit and edge-hugging.
4. Added `tests/test_map_quality_audit.py` covering the core audit functions.

### Phase 2: Redraw the Three Official Maps

Status: structural hard issues fixed; overall beautification can continue to iterate.

Goal: fix unreasonable and unattractive issues, and strengthen the differences between the three maps.

General rules:

1. Modify `region_rows` in `static/game_configs/maps/<id>/map.json`.
2. Do not change `region_tile.csv` unless a region binding itself is found to be wrong.
3. Do not add new region ids.
4. Do not delete the region roster shared by the three maps.
5. When moving a landmark, keep its anchor inside the corresponding region.
6. Regenerate previews after modifying a map.

`classic` direction:

1. Turn `106` into a contiguous main river.
2. The river should flow from a north-central or northwestern source, through the center, and finally into the Eastern Sea or an estuary.
3. `110`, `115`, and `112` can form forest belts, bamboo lands, and farmland transitions along the river.
4. The borders of western `102` / `117` with southern `103` should have Gobi, desert-edge, and forest-edge transitions.
5. Add bay mouths and headlands to the Eastern Sea `105` coastline, avoiding a single vertically cut coast.
6. Keep `118` as an overseas island with clear isolated-island semantics.

`island_seas` direction:

1. Keep large areas of `-1` sea wilderness as the sea background.
2. `106` expresses tidal channels, straits, and inner bays; multiple segments are allowed, but random water blobs should be avoided.
3. Delete or merge 1 to 2 cell fragments that lack semantics.
4. Add bays, headlands, and lagoons to the edges of large islands, but avoid checkerboard noise.
5. Cities preferably sit by harbors, inner bays, or estuaries.
6. `105` expresses a sea area with strong semantics and does not need to cover all sea surface.

`mountain_frontier` direction:

1. Turn `106` into a contiguous gorge river.
2. The gorge river should pass through mountains and valleys, giving the positions of cities, sects, and cave dwellings a better explanation.
3. Change `107` from a large gray block into a main mountain range plus spurs.
4. `109` / `101` / `301` / `406` form a central valley or mountain-pass corridor.
5. Reduce the edge-hugging block feel at the edge of the `117` Gobi, adding foothill, wasteland, and oasis-like interlocking.
6. Treat the `105` Eastern Sea boundary as a coast or estuary bay, rather than a cropped blue block.

Acceptance:

1. Human review of the PNG previews shows no obvious broken rivers on the three maps.
2. Edges of large regions are naturally jagged, but without a scatter of fragments.
3. Landmarks match the text semantics.
4. `python tools\map_presets\validate_presets.py` passes.
5. `python tools\map_presets\render_preview.py --all` generates previews.
6. `python tools\map_presets\export_frontend_previews.py` updates the frontend preview SVGs.

First round landed:

1. In `classic`, `106` has been adjusted from multiple water segments into a contiguous water system, keeping special regions such as `202` and `303` contiguous.
2. In `mountain_frontier`, `106` has been adjusted into a contiguous gorge river, with a sea outlet added.
3. In `mountain_frontier`, `406` has been expanded from 1 cell into a station region that can hold a 2x2 landmark.
4. In `island_seas`, some 1 to 2 cell fragments lacking semantics have been cleaned up.
5. The `map.json` and `meta.json` versions of the three maps have been bumped to `2`.
6. The frontend map preview SVGs have been re-exported.
7. `tests/test_map_presets.py` has added core quality regressions, locking water-system continuity for the continent/mountain maps and the mountain `406` landmark fit.

Second round landed:

1. In `classic`, the Eastern Sea `105` coastline has been further carved; the northern woodland, central foothills, and fields form continuous headlands and bay mouths, and the blockiness warning has been eliminated.
2. In `mountain_frontier`, the long straight foothill edge of `107` has been slightly bitten into by adjacent valley regions, and the long straight edge warning has been eliminated.
3. In the current quality audit, structural warnings such as broken river, no sea outlet, blocky large region, long straight edge, small fragment, and tiny water / sea component have been cleared to zero.
4. The three PNG previews and frontend SVG previews have been regenerated, and a human preview check has been completed.

Remaining focus:

1. The remaining automated audit items are all `landmark_near_boundary` soft hints.
2. Because of archipelago and small-island semantics, `island_seas` naturally tends to hug edges; landmarks should not be mechanically moved just to eliminate warnings.
3. `202` and `303` in `classic`, and `301`, `303`, and `406` in `mountain_frontier`, can be judged individually during later in-game review as to whether they need moving or expanding.
4. Later beautification can continue with local boundary carving, but should prioritize keeping geographic semantics, connectivity, and landmark readability.

### Phase 3: Tighten the Quality Gate and Documentation

Status: first version of the quality gate and automatic frontend preview mapping landed.

Goal: prevent official maps from degrading again in the future.

Tasks:

1. Wire stable audit items into the strict mode of `validate_presets.py`.
   - Basic format errors continue to hard fail.
   - Quality items that are stable and have low false-positive rates can hard fail.
   - Aesthetic items remain warnings.

2. Update tests.
   - Add key quality assertions to `tests/test_map_presets.py`.
   - Assert `106` is contiguous in `classic` / `mountain_frontier`.
   - Assert the archipelago map does not have too many isolated 1-cell sea/water components.
   - Assert map creator save dimensions do not revert to `70x50`.

3. Update documentation.
   - Add a map quality maintenance workflow to `docs/map-design-notes.md`.
   - If `.cursor/rules/map-system.mdc` changes later, `AGENTS.md` needs to be synced.

4. Improve frontend preview syncing.
   - Prefer having `MapPresetPreview.vue` use a dynamic mapping or a generated file, to avoid manual imports for every new map.
   - If bundler constraints require static imports, have the export script generate a manifest in sync.

Landed:

1. `tools/map_presets/validate_presets.py` now calls `quality_audit.audit_map_source()`.
2. Quality audit items other than `landmark_near_boundary` are now hard fails for official maps:
   - Broken river / no sea outlet.
   - Small fragment / tiny water / sea component.
   - Overly blocky large normal region.
   - Long straight edge of a normal region.
   - Landmark 2x2 poor fit.
3. `landmark_near_boundary` remains a soft hint, because archipelagos, small islands, harbors, cave dwellings, and similar semantics often need to hug edges, and a mechanical hard fail would easily cause false positives.
4. `web/src/components/game/panels/system/MapPresetPreview.vue` now automatically collects `web/src/assets/map-previews/*.svg` via `import.meta.glob()`, so adding a new map preview SVG no longer requires a hand-written import.
5. `tests/test_map_quality_audit.py` has added regression tests for the soft/hard quality item layering.

Acceptance:

1. The map quality audit has become part of the official map maintenance workflow.
2. When adding or modifying an official map, `python tools\map_presets\validate_presets.py` prevents objective structural issues from entering the official presets.
3. Frontend map previews will not be missing because someone forgot a hand-written import.

## Recommended Commands

After modifying a map or map tool, run at least:

```powershell
python tools\map_presets\validate_presets.py
python tools\map_presets\render_preview.py --all
python tools\map_presets\export_frontend_previews.py
pytest tests/test_map_presets.py
```

If the map editor was modified:

```powershell
pytest tests/test_map_presets.py
```

If the frontend preview component or the map start panel was modified:

```powershell
cd web
npm run type-check
npm run test -- --run
```

## Not Doing for Now

1. No random map generation.
2. No independent river layer.
3. No road layer.
4. No height, climate, or ecology simulation.
5. No per-cell tile overlay.
6. No change to the interim convention that the three official maps share the same region roster.
7. No new compatibility dual track for old map formats.

## Future Room

If stronger map expression is needed in the future, the following capabilities can be redesigned:

1. base terrain layer: allow more than one kind of no-region landform.
2. river / road overlay: decouple rivers and roads from region ownership.
3. coast / border autotile: automatically render edges based on adjacency.
4. runtime overlay: war, disaster, and construction change local landforms.
5. map editor brush: provide deterministic helper tools such as edge perturbation, river connection, and island generation.

These capabilities should be designed in separate specs, with a fresh evaluation of saves, frontend rendering, the external control API, and test contracts.

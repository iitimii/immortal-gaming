# World Lore Rewrite Pipeline Spec

This document records the target design of the "World Lore and History" start-of-run shaping system. It is meant to replace the current implementation in `WorldLoreManager` where "three large LLM tasks for map / sects / items read the global CSVs and return partial modification suggestions".

This plan does not require backward compatibility with the old world lore shaping output structure. Implementation prioritizes clarity of the current code, completeness of results and controllable wait time.

## Goals

World lore input should not just produce suggested renames for a few configuration entries; it should produce a static text snapshot exclusive to the current run.

After the player fills in "World Lore and History" at the start of a run, the system should, based on the currently selected map and that world lore, uniformly rewrite the following:

1. All locations that actually exist on the current map:
   - City regions
   - Normal regions
   - Cultivation regions
   - Sect headquarters
2. All sects themselves:
   - `name`
   - `desc`
3. All techniques:
   - `name`
   - `desc`
4. All weapons:
   - `name`
   - `desc`
5. All auxiliary equipment:
   - `name`
   - `desc`

Item text should be fully rewritten by default. If a product-level switch is really needed later, `world_lore.rewrite_items` can be added, but the main architectural path must support full rewriting and should no longer use "let the LLM pick a few items to modify" as the core flow.

## Non-Goals

This system only rewrites the current run's static display text and does not change gameplay values or structure.

It does not:

1. Add map regions.
2. Add sects, techniques or equipment.
3. Modify technique attributes, grades or conditions.
4. Modify weapon types, realms, prices or effects.
5. Modify auxiliary equipment realms, prices or effects.
6. Let the LLM write directly into save files or runtime objects.
7. Require compatibility with the old `world_lore_snapshot` structure.

## Current Problems

The current implementation lives in `src/classes/world_lore.py` and is called by `src/server/init_flow.py` during the start-of-run initialization phase.

Main problems with the status quo:

1. There are only three large tasks: `world_lore_map`, `world_lore_sect` and `world_lore_item`.
2. Although the three tasks run concurrently, each task's prompt is very large; in particular `world_lore_item` stuffs in the complete `technique.csv`, `weapon.csv` and `auxiliary.csv`.
3. The world lore tasks pass `max_retries=3`, whose underlying semantics are the initial call plus up to 3 retries; the single HTTP timeout is currently 120 seconds, so the worst-case wait is far too long.
4. The prompts require outputting `thinking`, and the map and item templates also require detailed analysis, which increases output tokens and the probability of JSON parse failures.
5. The map task reads the global region CSV instead of the current `world.map`, so it cannot truly understand the current map preset, `wilderness_tile`, `region_overrides`, landmarks or the current region position semantics.
6. The failure granularity is too coarse; one large task getting stuck or failing to parse slows down the whole initialization phase.
7. The initialization status only shows `shaping_world_lore`, making it impossible to tell whether it is stuck on the map, sects, techniques or equipment.

## Overall Design

The new system uses a pipeline of "full chunked rewriting + shared global LLM semaphore + local fallback + one-shot apply".

Flow:

1. Build the rewrite context from the current `world` and the player-entered `world_lore`.
2. Optionally generate a short `style_guide` to unify naming and description style across all chunk tasks.
3. Build rewrite jobs based on the current world:
   - Location jobs
   - Sect group jobs
   - Technique jobs
   - Weapon jobs
   - Auxiliary equipment jobs
4. Each job processes one chunk; the input count is fixed and the output count must be the same.
5. All jobs go through the existing `call_llm_with_task_name` and share the global LLM semaphore.
6. Each job has its own time budget and at most one format retry.
7. Jobs that fail, time out or fail validation are filled in with fallback.
8. All results are aggregated into a `WorldLoreRewriteDraft`.
9. First verify that the draft covers all target entities, then apply it in one shot to the world and global registries.
10. Build the new `world_lore_snapshot` and save it with the save file.

## Module Split

Do not keep piling the complete pipeline into `src/classes/world_lore.py`.

Suggested structure:

```text
src/classes/world_lore.py
  WorldLore
  WorldLoreManager thin facade

src/systems/world_lore_rewrite/
  __init__.py
  models.py
  planner.py
  prompts.py
  runner.py
  validation.py
  fallback.py
  apply.py
```

Responsibilities:

1. `models.py`
   - Defines data models such as context, job, chunk, draft and rewrite payload.
2. `planner.py`
   - Builds jobs from the current world and registries.
   - Does not read the raw global region CSV as map input.
3. `prompts.py`
   - Builds short prompt infos.
   - Uses structured JSON summaries and does not pass irrelevant gameplay fields.
4. `runner.py`
   - Schedules jobs.
   - Handles the global deadline, job deadlines, parse retries, cancellation and progress.
5. `validation.py`
   - Validates LLM output JSON, id sets, field lengths and forbidden content.
6. `fallback.py`
   - Generates baseline rewrite text for failed jobs.
7. `apply.py`
   - Applies the draft in one shot to the world, sects, techniques, weapons, auxiliaries, ItemRegistry and name indexes.

`WorldLoreManager.apply_world_lore()` should be reduced to a facade:

```python
async def apply_world_lore(self, lore_text: str) -> None:
    context = build_world_lore_context(self.world, lore_text)
    draft = await WorldLoreRewriteRunner(context).run()
    apply_world_lore_rewrite(self.world, draft)
```

## Current Map Input

Map rewriting must be based on the current `world.map`, not the global region CSV.

The map context includes at least:

1. `map_id`
2. `map_name`
3. `preset_version`
4. `width`
5. `height`
6. `wilderness_tile`
7. `landmarks`
8. `region_overrides`
9. The `regions` that actually exist on the current map

Each region input is suggested to include:

```json
{
  "id": 305,
  "type": "city",
  "name": "Moon-Embracing Harbor",
  "desc": "A harbor city with calm tides, where at night the moon's reflection falls between the long breakwater and the ship sails.",
  "tile_count": 23,
  "center": [50, 18],
  "landmark": {
    "x": 50,
    "y": 18,
    "asset": "city_305"
  },
  "map_override": true
}
```

It is not recommended to pass the complete `region_rows` to the LLM. Models are not good at understanding large matrices, and it would significantly increase prompt size. If map semantics are needed, code should generate a summary in advance, for example:

1. Whether the large wilderness area of the current map is sea or plain.
2. The type a region belongs to.
3. Whether a region uses a map-local override name.
4. Whether a region landmark is a city, sect, cave dwelling, ruin, etc.
5. An optional summary of adjacent terrain.

## Job Types

### Style Guide Job

An optional preliminary task that compresses the player's world lore into a short style guide.

Example output:

```json
{
  "world_tone": "Dharma-ending age, desolate and cold, collapse of sect order",
  "naming_rules": [
    "Place names lean toward ruined, desolate, ancient-battlefield feel",
    "Technique names avoid traditional auspicious words, leaning toward ash, setting sun, severed meridians"
  ],
  "forbidden_patterns": [
    "Do not frequently use Great Void, Mystic Heaven, Nine Heavens",
    "Do not write numeric bonuses"
  ],
  "description_style": "Concrete and visual, without explaining game mechanics"
}
```

This task must not output long thinking. On timeout or failure, a code-generated default style guide is used.

### Region Rewrite Jobs

Covers all regions that actually exist on the current map, including sect regions.

Input N regions; the output must be N regions.

Unified output structure:

```json
{
  "entities": [
    {
      "id": 305,
      "name": "New location name",
      "desc": "New location description"
    }
  ]
}
```

Location description requirements:

1. Match the current map semantics.
2. Focus on terrain, architecture, environmental phenomena, everyday atmosphere and cultivation atmosphere.
3. Do not write player bonuses, numeric effects or system mechanics.
4. `desc` is around 60 to 120 characters by default.

### Sect Group Rewrite Jobs

A sect itself and its corresponding sect headquarters should be processed in the same sect group job where possible, to avoid the sect description and the headquarters description drifting apart.

Input:

1. N sects.
2. The corresponding N sect regions.

Output:

```json
{
  "sects": [
    {
      "id": 1,
      "name": "New sect name",
      "desc": "New sect description"
    }
  ],
  "sect_regions": [
    {
      "id": 401,
      "name": "New headquarters name",
      "desc": "New headquarters description"
    }
  ]
}
```

Sect description requirements:

1. Focus on the sect's positioning, cultivation style, organizational temperament, internal structure and latent conflicts.
2. Do not repeat the headquarters terrain.
3. Do not restate sect rules, prohibitions or punishment logic.
4. Do not write player bonuses, numeric effects or system mechanics.

Sect headquarters description requirements:

1. Focus on terrain, architecture, spatial layering, environmental phenomena, dynamic scenery and sensory atmosphere.
2. Complement the semantics of the sect itself, without repeating the same information.

### Technique Rewrite Jobs

Fully rewrite the `name/desc` of all techniques.

Necessary fields input for each technique:

```json
{
  "id": 1,
  "name": "Primordial Golden Body",
  "desc": "Old description",
  "attribute": "GOLD",
  "grade": "LOWER"
}
```

Output:

```json
{
  "entities": [
    {
      "id": 1,
      "name": "New technique name",
      "desc": "New technique description"
    }
  ]
}
```

Requirements:

1. Keep the original attribute and grade positioning.
2. Describe the cultivation path, aura, risks and imagery.
3. Do not write specific damage, bonuses or game mechanics.
4. Do not modify fields such as conditions, weights or effects.

### Weapon Rewrite Jobs

Fully rewrite the `name/desc` of all weapons.

Necessary fields input for each weapon:

```json
{
  "id": 1001,
  "name": "Old weapon name",
  "desc": "Old description",
  "weapon_type": "SWORD",
  "realm": "Qi_Refinement"
}
```

Requirements:

1. Keep the original weapon type and realm positioning.
2. Describe material, form, origin and the temperament of its use.
3. Do not write numeric bonuses.
4. Do not change the weapon type semantics.

### Auxiliary Rewrite Jobs

Fully rewrite the `name/desc` of all auxiliary equipment.

Necessary fields input for each auxiliary:

```json
{
  "id": 2001,
  "name": "Old auxiliary equipment name",
  "desc": "Old description",
  "realm": "Qi_Refinement"
}
```

Requirements:

1. Keep the original realm and auxiliary positioning.
2. Describe how it is worn, the nature of the magic tool, and protective or supportive imagery.
3. Do not write numeric bonuses.
4. Do not promise mechanics that do not exist.

## Prompt Constraints

All rewrite prompts should be short, strongly constrained and without thinking.

General requirements:

1. Output JSON only.
2. Do not output markdown.
3. Do not output thinking.
4. Output as many entities as were input.
5. ids must be preserved exactly.
6. No new ids allowed.
7. No missing ids allowed.
8. Return only the allowed fields.
9. Do not write game mechanics, numbers or player bonuses.
10. The world lore style should be evident, but not every name should repeat the same word.

Illustration:

```text
You are a xianxia world-setting editor. Based on the world lore and the style guide, rewrite the name and desc of the input entities.

You must follow:
- Output as many entities as were input.
- ids must be preserved exactly.
- Output JSON only, no explanations, no markdown.
- Do not output thinking.
- Do not write game mechanics, numbers or player bonuses.
- Keep name concise; make desc concrete and visual.
- Preserve each entity's original category and gameplay positioning.
- The world lore style should be evident, but not every name should repeat the same word.

World lore:
{world_lore}

Style guide:
{style_guide}

Current map summary:
{map_summary}

Entities:
{entities_json}

Return:
{
  "entities": [
    {"id": 1, "name": "...", "desc": "..."}
  ]
}
```

## Concurrency Design

World lore rewrite tasks should share the existing global LLM semaphore.

`call_llm()` in the existing `src/utils/llm/client.py` already controls external request concurrency via `_get_semaphore()`. World Lore rewrite jobs must keep going through `call_llm_with_task_name` and must not bypass that entry point.

Principles:

1. `max_concurrent_requests` is the only real upper bound on external LLM request concurrency.
2. Do not add a world-lore-specific HTTP concurrency limit.
3. The World Lore runner may maintain a pending window that limits how many chunk tasks are scheduled locally at the same time.
4. The pending window is not a provider concurrency setting; it only avoids creating too many coroutines at once.
5. If there are other LLM tasks during initialization or step later, the global semaphore uniformly protects the provider's concurrency quota.

Recommended pending window:

```text
pending_window = max(current_llm_max_concurrent_requests * 2, 8)
```

If the total number of jobs is smaller than the pending window, all jobs can be scheduled at once. If the number of entities grows later, advance in batches by window.

## Timeout and Retry

World lore rewriting is a batch task whose failures can be handled with local fallback, so it should not reuse the generic LLM strategy of long waits and multiple retries.

Recommended default configuration:

```yaml
world_lore:
  total_timeout_seconds: 240
  task_timeout_seconds: 60
  min_retry_budget_seconds: 20
  max_parse_retries: 1
  max_transport_retries: 0
```

Tighter configuration:

```yaml
world_lore:
  total_timeout_seconds: 180
  task_timeout_seconds: 45
  min_retry_budget_seconds: 15
  max_parse_retries: 1
  max_transport_retries: 0
```

Semantics:

1. `total_timeout_seconds`
   - The hard budget for the entire world lore rewrite.
   - When it is reached, unfinished jobs are cancelled.
   - Completed results are kept.
   - Unfinished jobs are filled in with fallback.
   - Initialization is not interrupted.
2. `task_timeout_seconds`
   - The total budget for a single chunk job from start to success, retry or fallback.
   - Not a per-request budget.
3. `min_retry_budget_seconds`
   - When the remaining budget is below this value, no more parse retries are issued.
4. `max_parse_retries`
   - At most one retry on JSON parse failure, missing ids, mismatched output count or invalid fields.
   - The second prompt should include the previous validation error.
5. `max_transport_retries`
   - Network timeouts, connection failures and HTTP errors are not retried by default.
   - Such failures go straight to fallback, to avoid dragging down initialization.

Not recommended:

```yaml
task_timeout_seconds: 120
max_parse_retries: 3
```

This would reproduce the current problem of waits over 300 seconds.

## Validation

LLM output must pass strict validation before entering the draft.

General validation:

1. The output must be a JSON object.
2. It must contain the agreed fields.
3. The output id set must equal the input id set.
4. The output count must equal the input count.
5. `name` must be non-empty.
6. `desc` must be non-empty.
7. The lengths of `name` and `desc` must be within a reasonable range.
8. Obvious game mechanics or numeric bonuses are not allowed.
9. Markdown code blocks are not allowed.
10. Extra fields should be discarded and not applied.

After a validation failure:

1. If there is parse retry budget left, retry once.
2. If the retry still fails, the job uses fallback.
3. Fallback results must also pass the basic non-empty and id validation.

## Fallback

The goal of fallback is not to produce the best copy, but to guarantee that the current run's world lore snapshot is complete.

Trigger scenarios:

1. The style guide fails.
2. A job times out.
3. A network or HTTP failure.
4. JSON parse failure with retries exhausted.
5. Missing output ids or wrong count with retries exhausted.
6. Jobs still unfinished when the total timeout is reached.

Fallback strategy:

1. Generate a lightweight rewrite using world lore keywords, the entity's old name and the entity type.
2. Do not keep the full original text as the primary fallback.
3. Do not write numbers or mechanics.
4. Preserve gameplay semantics such as id, type, grade, realm and weapon type.
5. Mark the result source as `fallback`, for logging and statistics.

The draft may keep the source:

```python
source: Literal["llm", "fallback"]
```

This field does not necessarily go into the save file, but should go into log statistics.

## Apply Semantics

LLM jobs should not directly modify the world or global registries.

First aggregate the draft:

```python
@dataclass
class WorldLoreRewriteDraft:
    regions: dict[int, EntityRewrite]
    sects: dict[int, EntityRewrite]
    techniques: dict[int, EntityRewrite]
    weapons: dict[int, EntityRewrite]
    auxiliaries: dict[int, EntityRewrite]
```

Then apply uniformly:

1. Update region `name/desc` in the current `world.map.regions`.
2. Update sect `name/desc` in `sects_by_id`.
3. Update `sects_by_name` after a sect is renamed.
4. Update technique `name/desc` in `techniques_by_id`.
5. Update `techniques_by_name` after a technique is renamed.
6. Update weapons and auxiliaries.
7. Update the corresponding by-name index after an item is renamed.
8. Update `ItemRegistry`.
9. Call `sync_world_sect_metadata(world)` to ensure sect and headquarters links are consistent.
10. Build the new `world_lore_snapshot`.

Before applying, verify that the draft covers all target entities. If anything is missing, fill it in with fallback first; applying a half-finished draft is not allowed.

## Snapshot

The new `world_lore_snapshot` is suggested to use schema v2.

Structure example:

```json
{
  "schema_version": 2,
  "lore_text": "World lore and history entered by the player",
  "map_id": "island_seas",
  "map_name": "Azure Isles",
  "preset_version": 2,
  "rewrite_config": {
    "rewrite_items": true,
    "chunk_size": {
      "regions": 10,
      "sect_groups": 6,
      "techniques": 10,
      "weapons": 10,
      "auxiliaries": 10
    }
  },
  "stats": {
    "llm_count": 142,
    "fallback_count": 10,
    "elapsed_seconds": 93.2
  },
  "regions": {
    "305": {
      "name": "New location name",
      "desc": "New location description"
    }
  },
  "sects": {},
  "techniques": {},
  "weapons": {},
  "auxiliaries": {}
}
```

On load, the current text only needs to be applied according to the v2 snapshot. During the development phase there is no need to add complex compatibility paths for old snapshots.

## Configuration

Suggested additions to `static/config.yml`:

```yaml
world_lore:
  rewrite_items: true
  total_timeout_seconds: 240
  task_timeout_seconds: 60
  min_retry_budget_seconds: 20
  max_parse_retries: 1
  max_transport_retries: 0
  chunk_size:
    regions: 10
    sect_groups: 6
    techniques: 10
    weapons: 10
    auxiliaries: 10
  desc_limits:
    region: [60, 120]
    sect: [80, 150]
    technique: [50, 110]
    weapon: [45, 100]
    auxiliary: [45, 100]
```

Also add to `llm.default_modes`:

```yaml
llm:
  default_modes:
    world_lore_style_guide: "fast"
    world_lore_region_rewrite: "fast"
    world_lore_sect_group_rewrite: "fast"
    world_lore_technique_rewrite: "fast"
    world_lore_weapon_rewrite: "fast"
    world_lore_auxiliary_rewrite: "fast"
```

`max_concurrent_requests` still comes from the LLM settings and is not duplicated in `world_lore`.

## Initialization Progress

The initialization phase can still keep `shaping_world_lore` as the overall phase, but the runtime should record finer-grained world lore progress.

Suggested status:

```json
{
  "phase": "shaping_world_lore",
  "world_lore": {
    "total_jobs": 24,
    "finished_jobs": 17,
    "failed_jobs": 1,
    "fallback_count": 3,
    "current": "rewriting techniques 30/62"
  }
}
```

At minimum, logs must include:

```text
[WorldLore] style guide done
[WorldLore] planned jobs: regions=4 sect_groups=2 techniques=7 weapons=5 auxiliaries=4
[WorldLore] job techniques#3 done in 12.4s
[WorldLore] job weapons#2 parse failed, retrying
[WorldLore] job auxiliaries#1 timeout, fallback applied
[WorldLore] rewrite complete: llm=142 fallback=10 elapsed=93.2s
```

## Relationship with Step

World lore rewriting runs during the start-of-run initialization phase, before generating the initial NPCs and avatar profiles.

Concurrency-wise:

1. All world lore jobs share the global LLM semaphore.
2. Under the current initialization order, the world lore phase usually does not compete for the LLM concurrently with the initial backstory / long-term objective.
3. Even if the initialization phase is parallelized in the future, the unified semaphore protects the provider's concurrency quota.
4. World lore rewriting should not be triggered in `Simulator.step()`.
5. On load, only the snapshot is applied; the LLM is not called again.

## Test Contract

The following tests need to be added or adjusted:

1. `test_world_lore_planner_uses_current_map`
   - Verify that the planner builds region input from `world.map.regions`.
   - Verify that the global region CSV is not read as the main input for the map prompt.
2. `test_world_lore_planner_includes_map_context`
   - Verify that `map_id`, `map_name`, `wilderness_tile`, `region_overrides` and `landmarks` enter the context.
3. `test_world_lore_chunks_all_entities`
   - Verify that every region, sect, technique, weapon and auxiliary is assigned to a job.
4. `test_world_lore_runner_uses_global_llm_entrypoint`
   - Mock `call_llm_with_task_name` and verify that jobs go through the unified LLM call entry point.
5. `test_world_lore_runner_limits_pending_window`
   - Verify that local pending tasks do not exceed the pending window.
6. `test_world_lore_validation_rejects_missing_ids`
   - Retry or fallback is triggered when the LLM returns fewer ids.
7. `test_world_lore_validation_rejects_mechanics_text`
   - Output containing obvious numeric bonuses or mechanics explanations is rejected.
8. `test_world_lore_runner_applies_fallback_on_timeout`
   - After a single job times out, the final draft still contains all entities of that job.
9. `test_world_lore_total_timeout_fills_unfinished_jobs`
   - After the total timeout is reached, unfinished jobs are filled in with fallback.
10. `test_world_lore_apply_updates_indexes`
    - After sects, techniques and weapons are renamed, by-name indexes are updated correctly.
11. `test_world_lore_snapshot_v2_roundtrip`
    - Text stays consistent after save and load.
12. `test_world_lore_multi_map_uses_overrides`
    - Region overrides for the island or mountain map enter the prompt and serve as the current text source.
13. `test_init_world_lore_timeout_does_not_abort_initialization`
    - A world lore timeout does not cause initialization to fail.

Where map context is involved, combine with the constraints in `docs/specs/region-first-map-system.md` to ensure the use of results derived from the current map's `region_rows`, `wilderness_tile`, `landmarks` and `region_overrides`.

## Completion Criteria

After implementation, the following should hold:

1. After entering world lore, locations, sects, techniques, weapons and auxiliary equipment all have text exclusive to the current run.
2. When a different map is selected, the world lore rewrite is based on the different map context.
3. The full region CSV is no longer used as the main input for map rewriting.
4. The LLM is no longer required to output detailed thinking.
5. Both single-chunk timeouts and the overall timeout are controllable.
6. JSON format errors are retried at most once.
7. Network failures and timeouts do not interrupt initialization.
8. Failed chunks are filled in with fallback, and the final draft is complete.
9. Indexes and ItemRegistry stay consistent before and after apply.
10. Save and load preserve the rewrite results via the v2 snapshot.
11. Logs can locate slow tasks, failed tasks and the fallback count.

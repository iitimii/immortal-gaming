---
name: external-control-api
description: Plan or implement a stable control API for external agents / Claw, prioritizing underlying layering, query/command consolidation, runtime serialization, and contract docs rather than patching in scattered endpoints
---

## When to Use

Use this skill when a task involves any of the following:

- Designing or refactoring the external control API
- Making the project easier to drive from Claw / agents / automation scripts
- Consolidating existing frontend-private endpoints into a stable public contract
- Planning query / command layering
- Planning runtime/session abstractions and mutation serialization

## Goals

The goal of this skill is not to "quickly add a few endpoints" but to make sure the API direction can evolve over the long term:

1. Clear Query vs. Command boundaries
2. Clear responsibilities for the Runtime / Service / API layers
3. A unified mutation serialization model
4. Stable DTOs, error codes, and documentation

## What to Check First

1. Does the capability already exist, just scattered across old endpoints?
2. Is this task "add an endpoint" or "lay groundwork for what comes next"?
3. Does it touch paths in `src/server/main.py` that read/write `game_instance` directly?
4. Does it risk concurrent world writes with `game_loop()` / `sim.step()`?
5. Does the frontend currently depend on the old JSON shape? Which stores / mappers would a refactor affect?

## Recommended Workflow

### 1. Map the current state first

Look at these first:

- `src/server/main.py`
- `src/server/services/*.py`
- `src/sim/simulator_engine/simulator.py`
- `web/src/api/**/*.ts`
- `web/src/types/api.ts`
- `docs/specs/external-control-api.md`
- `.cursor/rules/external-control-api.mdc`

Goals:

- List the existing Query APIs
- List the existing Command APIs
- Mark which endpoints are "frontend-private legacy endpoints"
- Mark which logic should be extracted into service/runtime

### 2. Then define the boundaries

Before changing code, settle:

- What the new endpoint namespace is
- Which operations are Queries and which are Commands
- Which old endpoints can be replaced outright this time, without compatibility
- Which fields go into the stable DTO

### 3. Build the foundation first, then the endpoints

If the task is large enough, the priority order should be:

1. runtime/session abstraction
2. mutation lock / serialization
3. service consolidation
4. public v1 query
5. public v1 command
6. frontend adaptation
7. docs and README

Do not do it the other way around, adding a pile of endpoints first and backfilling the foundation later.

### 4. Keep commands semantic

Prefer:

- `set_long_term_objective`
- `set_world_phenomenon`
- `create_avatar`
- `delete_avatar`
- `update_avatar_adjustment`

Avoid introducing:

- Generic patch on arbitrary objects
- Pass-through writes of arbitrary fields
- "Do-everything control endpoints" without clear side-effect boundaries

## Code Change Guidelines

### Route layer

- The route layer only parses parameters and wraps responses
- Do not write complex world logic directly in routes

### Service layer

- Keep avatar control, world control, and lifecycle control separate
- Reuse existing services; do not reimplement them
- For dependencies that may be patched in tests, reloaded at runtime, or split into further modules later, prefer injecting getters, for example:
  - `get_load_game`
  - `get_generate_custom_content_draft`
  - `get_generate_custom_goldfinger_draft`
  - `get_apply_runtime_content_locale`
  - `get_config`

### Runtime layer

- Any operation that modifies world/sim should go through the unified runtime
- If a new command bypasses the runtime, that usually signals a design problem

### Config and save directories

- The config source of truth may be reloaded or patched in tests; do not assume a module-level `CONFIG` is always the latest object.
- When reading/writing saves, prefer resolving the current saves dir at call time; for infrastructure-level helpers, consider supporting both `main.CONFIG` and the latest `CONFIG` in the current config module, to avoid reading the wrong directory during full test runs or data root switches.
- This kind of dynamic reading is mainly about "a stable foundation", not about preserving old public APIs.

## Documentation Requirements

When changing the external control API, sync these first:

- `docs/specs/external-control-api.md`
- `README.md` (the only README; there are no translated READMEs to sync)
- `AGENTS.md`

If you introduce new rules or new long-term constraints, remember to sync `.cursor/rules/*.mdc` and the repository root `AGENTS.md`.

## Testing Guidelines

At minimum, consider:

- query contract tests
- command contract tests
- state guard tests
- runtime serialization tests
- regression tests for initialization / loading saves / event queries

If the frontend is migrated alongside, also run:

```bash
pytest
cd web && npm run test
cd web && npm run type-check
```

## Minimal Claw Template

If the goal is to ship a usable Claw / agent control skill quickly, follow this pattern:

1. Each round, first query `GET /api/v1/query/runtime/status`
2. If not ready:
   - If no game has started, call `POST /api/v1/command/game/start`
   - If initializing, keep polling
   - If in an error state, read the error info and consider `reinit`
3. Once ready, query:
   - `GET /api/v1/query/world/state`
   - `GET /api/v1/query/events`
   - `GET /api/v1/query/detail` when needed
4. Only call "semantic commands", for example:
   - `avatar/set-long-term-objective`
   - `world/set-phenomenon`
   - `avatar/create`
   - `avatar/update-adjustment`
5. Query again after a command; do not assume the local cache is correct

## Where New Endpoints Go

- New query:
  - First check whether an existing service can be reused
  - Then wire it into `src/server/public_query_builders.py`
  - Finally mount it on `src/server/api/public_v1/query.py`
- New command:
  - Put business logic in a service first
  - Wire orchestration into `src/server/command_handlers.py`
  - Finally mount it on `src/server/api/public_v1/command.py`
- Endpoints that modify world / sim:
  - Must go through the unified runtime mutation entry point
